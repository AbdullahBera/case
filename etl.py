import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

# Load PostgreSQL credentials from .env file
load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# PostgreSQL Connection
def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# Load CSV file
df = pd.read_csv("/Users/bera/Desktop/data/hotel_bookings.csv")

# Clean Data
df = df.copy() 
df["children"] = df["children"].fillna(0)  
df["country"] = df["country"].fillna("Unknown")  
df["agent"] = df["agent"].fillna(0)  
df.drop("company", axis=1, inplace=True) 
df["reservation_status_date"] = pd.to_datetime(df["reservation_status_date"]) 

# Remove duplicate rows if any
df.drop_duplicates(inplace=True)

# Function to insert data into PostgreSQL with column mapping
def insert_data(table_name, df, db_column_names=None, df_column_names=None, key_columns=None):
    """
    Inserts or updates data in PostgreSQL with optional column mapping.
    
    Args:
        table_name: Name of the target table
        df: DataFrame containing the data
        db_column_names: Column names in the database table
        df_column_names: Column names in the DataFrame
        key_columns: List of columns that form a unique key
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if df_column_names is None:
        df_column_names = db_column_names
    
    data_tuples = [tuple(x) for x in df[df_column_names].to_numpy()]
    
    # Create SQL Upsert Query
    query = f"INSERT INTO {table_name} ({', '.join(db_column_names)}) VALUES %s"
    
    if key_columns:
        # Add ON CONFLICT clause for upsert
        conflict_cols = ', '.join(key_columns)
        update_cols = ', '.join([f"{col} = EXCLUDED.{col}" for col in db_column_names if col not in key_columns])
        query += f" ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_cols}"
    
    try:
        execute_values(cursor, query, data_tuples)
        conn.commit()
        print(f"✅ Data inserted/updated in {table_name} successfully!")
    except Exception as e:
        print(f"❌ Error with {table_name}: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

# Insert Data into Dimension Tables
insert_data("dim_hotels", df[["hotel", "market_segment", "distribution_channel"]].drop_duplicates(), 
            db_column_names=["hotel_name", "market_segment", "distribution_channel"],
            df_column_names=["hotel", "market_segment", "distribution_channel"])

date_df = df[["reservation_status_date", "arrival_date_year", "arrival_date_month", 
              "arrival_date_week_number", "arrival_date_day_of_month"]].drop_duplicates()
insert_data("dim_dates", date_df,
            db_column_names=["arrival_date", "arrival_year", "arrival_month", 
                             "arrival_week_number", "arrival_day_of_month"],
            df_column_names=["reservation_status_date", "arrival_date_year", "arrival_date_month", 
                             "arrival_date_week_number", "arrival_date_day_of_month"])

insert_data("dim_customers", df[["adults", "children", "babies", "customer_type", "country"]].drop_duplicates(),
            db_column_names=["adults", "children", "babies", "customer_type", "country"])

agent_df = df[["agent"]].drop_duplicates()
agent_df["agent"] = agent_df["agent"].astype(float).astype(str)  # Convert to string
insert_data("dim_agents", agent_df,
            db_column_names=["agent_name"],
            df_column_names=["agent"])

def create_mapping_table(table_name, key_column, value_column):
    """Create a dictionary mapping dimension values to their IDs"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT {key_column}, {value_column} FROM {table_name}")
    mapping = {row[1]: row[0] for row in cursor.fetchall()}
    cursor.close()
    conn.close()
    return mapping

# Create mapping dictionaries for each dimension
hotel_mapping = create_mapping_table("dim_hotels", "hotel_id", "hotel_name")

# Fix the date mapping - convert between datetime.date and pandas.Timestamp
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT date_id, arrival_date FROM dim_dates")
date_mapping = {}
for row in cursor.fetchall():
    date_id, db_date = row
    # Convert database date to string in YYYY-MM-DD format for comparison
    date_str = db_date.strftime('%Y-%m-%d')
    date_mapping[date_str] = date_id
cursor.close()
conn.close()

# Print some sample dates from the mapping to debug
print("Sample dates from mapping:")
sample_dates = list(date_mapping.keys())[:5]
for date in sample_dates:
    print(f"Date: {date}, Type: {type(date)}")

# Print some sample dates from the dataframe to debug
print("\nSample dates from dataframe:")
sample_df_dates = df["reservation_status_date"].head(5)
for date in sample_df_dates:
    print(f"Date: {date}, Type: {type(date)}")

customer_mapping = {}  # This is more complex - we'll handle it differently
agent_mapping = create_mapping_table("dim_agents", "agent_id", "agent_name")

# For customers, we need to create a composite key
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT customer_id, adults, children, babies, customer_type, country FROM dim_customers")
for row in cursor.fetchall():
    # Create a composite key from the customer attributes
    customer_key = (row[1], row[2], row[3], row[4], row[5])  # (adults, children, babies, customer_type, country)
    customer_mapping[customer_key] = row[0]  # customer_id
cursor.close()
conn.close()

# Now prepare data for fact_bookings
fact_data = []
for _, row in df.iterrows():
    # Get dimension IDs
    hotel_id = hotel_mapping.get(row["hotel"])
    
    # For date, convert Timestamp to string in YYYY-MM-DD format
    date_str = row["reservation_status_date"].strftime('%Y-%m-%d')
    date_id = date_mapping.get(date_str)
    
    # For customer, create the composite key
    customer_key = (row["adults"], row["children"], row["babies"], row["customer_type"], row["country"])
    customer_id = customer_mapping.get(customer_key)
    
    # For agent
    agent_id = agent_mapping.get(str(float(row["agent"])))
    
    # Only add rows where we have all required foreign keys
    if hotel_id and date_id and customer_id:
        fact_data.append({
            "hotel_id": hotel_id,
            "date_id": date_id,
            "customer_id": customer_id,
            "agent_id": agent_id,
            "is_canceled": row["is_canceled"],
            "lead_time": row["lead_time"],
            "stays_in_weekend_nights": row["stays_in_weekend_nights"],
            "stays_in_week_nights": row["stays_in_week_nights"],
            "adr": row["adr"],
            "booking_changes": row["booking_changes"],
            "deposit_type": row["deposit_type"],
            "days_in_waiting_list": row["days_in_waiting_list"],
            "required_car_parking_spaces": row["required_car_parking_spaces"],
            "total_of_special_requests": row["total_of_special_requests"],
            "reservation_status": row["reservation_status"],
            "reservation_status_date": row["reservation_status_date"]
        })

# Add debugging information
print(f"Number of rows in original dataframe: {len(df)}")
print(f"Number of rows prepared for fact table: {len(fact_data)}")

# Check if fact_data is empty
if not fact_data:
    print("⚠️ No data prepared for fact_bookings! Checking dimension mappings...")
    print(f"Hotel mapping entries: {len(hotel_mapping)}")
    print(f"Date mapping entries: {len(date_mapping)}")
    print(f"Customer mapping entries: {len(customer_mapping)}")
    print(f"Agent mapping entries: {len(agent_mapping)}")
    
    # Sample a few rows to debug
    sample_rows = df.head(5)
    for i, row in sample_rows.iterrows():
        print(f"\nSample row {i}:")
        hotel = row["hotel"]
        res_date = row["reservation_status_date"]
        customer_key = (row["adults"], row["children"], row["babies"], row["customer_type"], row["country"])
        agent = str(float(row["agent"]))
        
        print(f"Hotel: {hotel} -> ID: {hotel_mapping.get(hotel)}")
        print(f"Date: {res_date} -> ID: {date_mapping.get(res_date.strftime('%Y-%m-%d'))}")
        print(f"Customer key: {customer_key} -> ID: {customer_mapping.get(customer_key)}")
        print(f"Agent: {agent} -> ID: {agent_mapping.get(agent)}")

# Convert to DataFrame and insert
if fact_data:
    fact_df = pd.DataFrame(fact_data)
    insert_data("fact_bookings", fact_df, fact_df.columns.tolist())
    print("🎉 Data pipeline completed successfully!")
else:
    print("❌ No data to insert into fact_bookings table!")
