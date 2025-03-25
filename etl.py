import os
import pandas as pd
from dotenv import load_dotenv
import httpx
from datetime import datetime

# Load environment variables
load_dotenv()
print("Environment variables loaded")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print(f"SUPABASE_URL exists: {'Yes' if SUPABASE_URL else 'No'}")
print(f"SUPABASE_KEY exists: {'Yes' if SUPABASE_KEY else 'No'}")

# Set up headers for Supabase REST API
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# Load and clean data
df = pd.read_csv("/Users/bera/Desktop/data/hotel_bookings.csv")

# Clean Data
df = df.copy() 
df["children"] = df["children"].fillna(0)  
df["country"] = df["country"].fillna("Unknown")  
df["agent"] = df["agent"].fillna(0)  
df.drop("company", axis=1, inplace=True) 
df["reservation_status_date"] = pd.to_datetime(df["reservation_status_date"]) 

# Remove duplicate rows
df.drop_duplicates(inplace=True)

def insert_data(table_name, records, unique_columns=None):
    """
    Insert data into Supabase table with upsert support
    
    Args:
        table_name: Name of the table
        records: List of records to insert
        unique_columns: List of columns that form a unique constraint
    """
    try:
        # Add Prefer header for upsert if unique_columns are specified
        request_headers = headers.copy()
        if unique_columns:
            request_headers["Prefer"] = "resolution=merge-duplicates"
            
        with httpx.Client() as client:
            response = client.post(
                f"{SUPABASE_URL}/rest/v1/{table_name}",
                headers=request_headers,
                params={"on_conflict": ",".join(unique_columns)} if unique_columns else None,
                json=records
            )
            if response.status_code in [200, 201]:
                print(f"✅ Data inserted/updated in {table_name} successfully!")
                return True
            else:
                print(f"❌ Error with {table_name}: {response.text}")
                return False
    except Exception as e:
        print(f"❌ Error with {table_name}: {e}")
        return False

def get_mapping(table_name, key_field, value_field):
    """Get mapping with debug information"""
    with httpx.Client() as client:
        response = client.get(
            f"{SUPABASE_URL}/rest/v1/{table_name}?select={key_field},{value_field}",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            print(f"Retrieved {len(data)} mappings for {table_name}")
            if len(data) > 0:
                print(f"Sample mapping for {table_name}:", data[0])
            return {str(row[value_field]): row[key_field] for row in data}
        else:
            print(f"Error getting mappings for {table_name}: {response.text}")
        return {}

def get_customer_mapping(table_name):
    """Get customer mapping with composite key"""
    with httpx.Client() as client:
        response = client.get(
            f"{SUPABASE_URL}/rest/v1/{table_name}?select=customer_id,adults,children,babies,customer_type,country",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            print(f"Retrieved {len(data)} customer mappings")
            # Create composite key mapping
            mapping = {}
            for row in data:
                key = (
                    int(row['adults']), 
                    int(row['children']), 
                    int(row['babies']), 
                    row['customer_type'], 
                    row['country']
                )
                mapping[key] = row['customer_id']
            return mapping
        return {}

# Insert dimension tables
print("\nInserting dimension tables...")

# Hotels dimension
hotels_df = df[["hotel", "market_segment", "distribution_channel"]].drop_duplicates()
hotels_records = [
    {"hotel_name": row["hotel"], 
     "market_segment": row["market_segment"],
     "distribution_channel": row["distribution_channel"]}
    for _, row in hotels_df.iterrows()
]
print(f"\nInserting {len(hotels_records)} hotel records")
insert_data("dim_hotels", hotels_records, unique_columns=["hotel_name", "market_segment", "distribution_channel"])

# 2. Dates dimension
dates_df = df[["reservation_status_date", "arrival_date_year", "arrival_date_month", 
               "arrival_date_week_number", "arrival_date_day_of_month"]].drop_duplicates(
                   subset=["reservation_status_date"]  # Ensure uniqueness by date
               )

dates_records = [
    {"arrival_date": row["reservation_status_date"].strftime('%Y-%m-%d'),
     "arrival_year": int(row["arrival_date_year"]),  # Ensure integer
     "arrival_month": str(row["arrival_date_month"]),  # Ensure string
     "arrival_week_number": int(row["arrival_date_week_number"]),  # Ensure integer
     "arrival_day_of_month": int(row["arrival_date_day_of_month"])}  # Ensure integer
    for _, row in dates_df.iterrows()
]

# Insert with upsert
insert_data("dim_dates", dates_records, unique_columns=["arrival_date"])

# 3. Customers dimension
customers_df = df[["adults", "children", "babies", "customer_type", "country"]].drop_duplicates()
customers_records = [
    {
        "adults": int(row["adults"]),  # Convert to integer
        "children": int(row["children"]),  # Convert to integer
        "babies": int(row["babies"]),  # Convert to integer
        "customer_type": row["customer_type"],
        "country": row["country"]
    }
    for _, row in customers_df.iterrows()
]
insert_data("dim_customers", customers_records, unique_columns=["adults", "children", "babies", "customer_type", "country"])

# 4. Agents dimension
agents_df = df[["agent"]].drop_duplicates()
agents_records = [
    {"agent_name": str(int(row["agent"])) if pd.notnull(row["agent"]) else "Unknown"}
    for _, row in agents_df.iterrows()
]
insert_data("dim_agents", agents_records, unique_columns=["agent_name"])

# Get mappings with debug information
print("\nRetrieving mappings...")
hotel_mapping = get_mapping("dim_hotels", "hotel_id", "hotel_name")
date_mapping = get_mapping("dim_dates", "date_id", "arrival_date")
customer_mapping = get_customer_mapping("dim_customers")  # Use new function
agent_mapping = get_mapping("dim_agents", "agent_id", "agent_name")

print("\nMapping sizes:")
print(f"Hotels: {len(hotel_mapping)}")
print(f"Dates: {len(date_mapping)}")
print(f"Customers: {len(customer_mapping)}")
print(f"Agents: {len(agent_mapping)}")

# Prepare fact records with debugging
print("\nPreparing fact records...")
fact_records = []
missing_mappings = {
    'hotel': set(),
    'date': set(),
    'customer': set(),
    'agent': set()
}

for idx, row in df.iterrows():
    hotel_id = hotel_mapping.get(row["hotel"])
    date_str = row["reservation_status_date"].strftime('%Y-%m-%d')
    date_id = date_mapping.get(date_str)
    
    # Create customer key matching the mapping
    customer_key = (
        int(row["adults"]),
        int(row["children"]),
        int(row["babies"]),
        row["customer_type"],
        row["country"]
    )
    customer_id = customer_mapping.get(customer_key)
    
    agent_id = agent_mapping.get(str(float(row["agent"])) if pd.notnull(row["agent"]) else "Unknown")
    
    if not hotel_id:
        missing_mappings['hotel'].add(row["hotel"])
    if not date_id:
        missing_mappings['date'].add(date_str)
    if not customer_id:
        missing_mappings['customer'].add(customer_key)
    if not agent_id:
        missing_mappings['agent'].add(str(float(row["agent"])) if pd.notnull(row["agent"]) else "Unknown")
    
    if hotel_id and date_id and customer_id:
        fact_records.append({
            "hotel_id": hotel_id,
            "date_id": date_id,
            "customer_id": customer_id,
            "agent_id": agent_id,
            "is_canceled": bool(row["is_canceled"]),
            "lead_time": int(row["lead_time"]),
            "stays_in_weekend_nights": int(row["stays_in_weekend_nights"]),
            "stays_in_week_nights": int(row["stays_in_week_nights"]),
            "adr": float(row["adr"]),
            "booking_changes": int(row["booking_changes"]),
            "deposit_type": row["deposit_type"],
            "days_in_waiting_list": int(row["days_in_waiting_list"]),
            "required_car_parking_spaces": int(row["required_car_parking_spaces"]),
            "total_of_special_requests": int(row["total_of_special_requests"]),
            "reservation_status": row["reservation_status"],
            "reservation_status_date": row["reservation_status_date"].strftime('%Y-%m-%d')
        })

    if idx % 1000 == 0:
        print(f"Processed {idx} rows...")

print("\nMissing mappings summary:")
for key, values in missing_mappings.items():
    print(f"{key}: {len(values)} missing mappings")
    if len(values) > 0:
        print(f"Sample missing {key}:", list(values)[:3])

print(f"\nPrepared {len(fact_records)} fact records")

# Insert fact table in batches
BATCH_SIZE = 1000
for i in range(0, len(fact_records), BATCH_SIZE):
    batch = fact_records[i:i + BATCH_SIZE]
    print(f"Inserting batch {i//BATCH_SIZE + 1} of {len(fact_records)//BATCH_SIZE + 1}")
    insert_data("fact_bookings", batch)

print("\n🎉 Data pipeline completed!")
