import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import os
from dotenv import load_dotenv
import numpy as np
from prophet import Prophet
from prophet.plot import plot_plotly
import plotly.graph_objs as go

# Load environment variables
load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# Function to connect to PostgreSQL
def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# Fetch data from database
def fetch_data(query):
    conn = get_connection()
    try:
        df = pd.read_sql(query, conn)
        return df
    finally:
        conn.close()

# Get booking trends data
booking_trends_query = """
SELECT d.arrival_year, d.arrival_month, COUNT(*) AS total_bookings
FROM fact_bookings f
JOIN dim_dates d ON f.date_id = d.date_id
GROUP BY d.arrival_year, d.arrival_month
ORDER BY d.arrival_year, d.arrival_month;
"""

# Get cancellation rates
cancellation_query = """
SELECT d.arrival_year, d.arrival_month, 
       SUM(CASE WHEN f.is_canceled = 1 THEN 1 ELSE 0 END) AS canceled,
       COUNT(*) AS total_bookings,
       ROUND(100.0 * SUM(CASE WHEN f.is_canceled = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS cancel_rate
FROM fact_bookings f
JOIN dim_dates d ON f.date_id = d.date_id
GROUP BY d.arrival_year, d.arrival_month
ORDER BY d.arrival_year, d.arrival_month;
"""

# Get revenue trends
revenue_query = """
SELECT d.arrival_year, d.arrival_month, SUM(f.adr) AS total_revenue
FROM fact_bookings f
JOIN dim_dates d ON f.date_id = d.date_id
WHERE f.is_canceled = 0
GROUP BY d.arrival_year, d.arrival_month
ORDER BY d.arrival_year, d.arrival_month;
"""

# Get country data for filtering - only countries with revenue > $10,000
country_query = """
SELECT DISTINCT c.country
FROM fact_bookings f
JOIN dim_customers c ON f.customer_id = c.customer_id
WHERE f.is_canceled = 0
GROUP BY c.country
HAVING SUM(f.adr) > 10000
ORDER BY c.country;
"""

# Get hotel types for filtering
hotel_type_query = """
SELECT DISTINCT hotel_name
FROM dim_hotels
ORDER BY hotel_name;
"""

# Fetching Data
df_bookings = fetch_data(booking_trends_query)
df_cancellations = fetch_data(cancellation_query)
df_revenue = fetch_data(revenue_query)
df_countries = fetch_data(country_query)
df_hotel_types = fetch_data(hotel_type_query)

# Streamlit App Title
st.title("🏨 Hotel Booking Dashboard")

# Add tabs for different views
tab1, tab2 = st.tabs(["Dashboard", "Forecast"])

with tab1:
    # Sidebar Filters
    st.sidebar.header("Filter Data")

    # Add "All Years" option to year filter
    year_options = ["All Years"] + sorted(df_bookings["arrival_year"].unique().tolist())
    selected_year = st.sidebar.selectbox("Select Year", year_options)

    # Add country filter with only high-revenue countries
    country_options = ["All Countries"] + df_countries["country"].tolist()
    selected_country = st.sidebar.selectbox("Select Country (Revenue > $10,000)", country_options)

    # Add hotel type filter
    hotel_options = ["All Hotels"] + df_hotel_types["hotel_name"].tolist()
    selected_hotel = st.sidebar.selectbox("Select Hotel Type", hotel_options)

    # Modify queries to include all filters
    year_filter = ""
    if selected_year != "All Years":
        year_filter = f" AND d.arrival_year = {selected_year}"

    country_filter = ""
    if selected_country != "All Countries":
        country_filter = f" AND c.country = '{selected_country}'"

    hotel_filter = ""
    if selected_hotel != "All Hotels":
        hotel_filter = f" AND h.hotel_name = '{selected_hotel}'"
    
    # Apply filters based on selections
    if selected_year != "All Years" or selected_country != "All Countries" or selected_hotel != "All Hotels":
        # Build filtered queries
        booking_trends_filtered_query = f"""
        SELECT d.arrival_year, d.arrival_month, COUNT(*) AS total_bookings
        FROM fact_bookings f
        JOIN dim_dates d ON f.date_id = d.date_id
        JOIN dim_customers c ON f.customer_id = c.customer_id
        JOIN dim_hotels h ON f.hotel_id = h.hotel_id
        WHERE 1=1{year_filter}{country_filter}{hotel_filter}
        GROUP BY d.arrival_year, d.arrival_month
        ORDER BY d.arrival_year, d.arrival_month;
        """
        
        cancellation_filtered_query = f"""
        SELECT d.arrival_year, d.arrival_month, 
               SUM(CASE WHEN f.is_canceled = 1 THEN 1 ELSE 0 END) AS canceled,
               COUNT(*) AS total_bookings,
               ROUND(100.0 * SUM(CASE WHEN f.is_canceled = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS cancel_rate
        FROM fact_bookings f
        JOIN dim_dates d ON f.date_id = d.date_id
        JOIN dim_customers c ON f.customer_id = c.customer_id
        JOIN dim_hotels h ON f.hotel_id = h.hotel_id
        WHERE 1=1{year_filter}{country_filter}{hotel_filter}
        GROUP BY d.arrival_year, d.arrival_month
        ORDER BY d.arrival_year, d.arrival_month;
        """
        
        revenue_filtered_query = f"""
        SELECT d.arrival_year, d.arrival_month, SUM(f.adr) AS total_revenue
        FROM fact_bookings f
        JOIN dim_dates d ON f.date_id = d.date_id
        JOIN dim_customers c ON f.customer_id = c.customer_id
        JOIN dim_hotels h ON f.hotel_id = h.hotel_id
        WHERE f.is_canceled = 0{year_filter}{country_filter}{hotel_filter}
        GROUP BY d.arrival_year, d.arrival_month
        ORDER BY d.arrival_year, d.arrival_month;
        """
        
        # Fetch filtered data
        df_bookings_filtered = fetch_data(booking_trends_filtered_query)
        df_cancellations_filtered = fetch_data(cancellation_filtered_query)
        df_revenue_filtered = fetch_data(revenue_filtered_query)
    else:
        # Use original unfiltered data
        df_bookings_filtered = df_bookings
        df_cancellations_filtered = df_cancellations
        df_revenue_filtered = df_revenue

    # Create a 2-column layout for the top row
    row1_col1, row1_col2 = st.columns(2)

    # Update chart titles to include filter information
    year_title = f"({selected_year})" if selected_year != "All Years" else "(All Years)"
    country_title = f" - {selected_country}" if selected_country != "All Countries" else ""
    hotel_title = f" - {selected_hotel}" if selected_hotel != "All Hotels" else ""

    with row1_col1:
        st.subheader("📊 Booking Trends")
        # Create a month order mapping
        month_order = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
            'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        
        # If dataframe is not empty, sort by month
        if not df_bookings_filtered.empty:
            # Add a month_num column for sorting
            df_bookings_filtered['month_num'] = df_bookings_filtered['arrival_month'].map(month_order)
            df_bookings_filtered = df_bookings_filtered.sort_values(['arrival_year', 'month_num'])
            
            # Convert arrival_year to string to avoid decimal display in legend
            df_bookings_filtered['arrival_year'] = df_bookings_filtered['arrival_year'].astype(int).astype(str)
            
            fig_bookings = px.line(
                df_bookings_filtered,
                x="arrival_month",
                y="total_bookings",
                color="arrival_year" if selected_year == "All Years" else None,
                title=f"Monthly Booking Trends {year_title}{country_title}{hotel_title}",
                markers=True,
                category_orders={"arrival_month": list(month_order.keys())},
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            st.plotly_chart(fig_bookings, use_container_width=True)
            
            # Booking metrics below the chart
            st.metric("Total Bookings", df_bookings_filtered["total_bookings"].sum())
        else:
            st.write("No booking data available for the selected filters.")

    with row1_col2:
        st.subheader("❌ Cancellation Rates")
        # If dataframe is not empty, sort by month
        if not df_cancellations_filtered.empty:
            # Add a month_num column for sorting
            df_cancellations_filtered['month_num'] = df_cancellations_filtered['arrival_month'].map(month_order)
            df_cancellations_filtered = df_cancellations_filtered.sort_values(['arrival_year', 'month_num'])
            
            # Convert arrival_year to string to avoid decimal display in legend
            df_cancellations_filtered['arrival_year'] = df_cancellations_filtered['arrival_year'].astype(int).astype(str)
            
            fig_cancellations = px.bar(
                df_cancellations_filtered,
                x="arrival_month",
                y="cancel_rate",
                color="arrival_year" if selected_year == "All Years" else None,
                title=f"Monthly Cancellation Rates {year_title}{country_title}{hotel_title}",
                text="cancel_rate",
                category_orders={"arrival_month": list(month_order.keys())},
                color_discrete_sequence=px.colors.qualitative.Bold  # Use a discrete color sequence
            )
            
            # Update color axis to use discrete values
            if selected_year == "All Years":
                fig_cancellations.update_layout(
                    coloraxis_showscale=False,
                    legend_title_text="Year"
                )
                
            st.plotly_chart(fig_cancellations, use_container_width=True)
            
            # Cancellation metrics below the chart
            avg_cancel_rate = df_cancellations_filtered["cancel_rate"].mean()
            st.metric("Average Cancellation Rate", f"{avg_cancel_rate:.2f}%")
        else:
            st.write("No cancellation data available for the selected filters.")

    # Revenue Trends in a full-width row at the bottom
    st.subheader("💰 Revenue Trends")
    # If dataframe is not empty, sort by month
    if not df_revenue_filtered.empty:
        # Add a month_num column for sorting
        df_revenue_filtered['month_num'] = df_revenue_filtered['arrival_month'].map(month_order)
        df_revenue_filtered = df_revenue_filtered.sort_values(['arrival_year', 'month_num'])
        
        # Convert arrival_year to string to avoid decimal display in legend
        df_revenue_filtered['arrival_year'] = df_revenue_filtered['arrival_year'].astype(int).astype(str)
        
        fig_revenue = px.area(
            df_revenue_filtered,
            x="arrival_month",
            y="total_revenue",
            color="arrival_year" if selected_year == "All Years" else None,
            title=f"Monthly Revenue Trends {year_title}{country_title}{hotel_title}",
            markers=True,
            category_orders={"arrival_month": list(month_order.keys())},
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        st.plotly_chart(fig_revenue, use_container_width=True)
        
        # Revenue metrics below the chart
        total_revenue = df_revenue_filtered["total_revenue"].sum()
        st.metric("Total Revenue", f"${total_revenue:,.2f}")
    else:
        st.write("No revenue data available for the selected filters.")


### Time Series Forecasting

with tab2:
    st.header("📈 Booking Forecast")
    
    # Fetch historical bookings for forecasting
    forecast_query = """
    SELECT d.arrival_year, d.arrival_month, COUNT(*) AS total_bookings
    FROM fact_bookings f
    JOIN dim_dates d ON f.date_id = d.date_id
    GROUP BY d.arrival_year, d.arrival_month
    ORDER BY d.arrival_year, d.arrival_month;
    """
    
    df_forecast_data = fetch_data(forecast_query)
    
    # Create month order mapping
    month_order = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
        'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    
    # Add month number for proper date conversion
    df_forecast_data['month_num'] = df_forecast_data['arrival_month'].map(month_order)
    
    # Create date column
    df_forecast_data["ds"] = pd.to_datetime(
        df_forecast_data["arrival_year"].astype(str) + "-" + 
        df_forecast_data["month_num"].astype(str) + "-01"
    )
    
    # Rename for Prophet
    df_prophet = df_forecast_data[["ds", "total_bookings"]].rename(columns={"total_bookings": "y"})
    
    # Set fixed forecast period to 12 months
    forecast_periods = 12
    
    # Train Prophet Model
    with st.spinner("Training forecasting model..."):
        model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        model.fit(df_prophet)
        
        # Forecast future periods
        future = model.make_future_dataframe(periods=forecast_periods, freq="M")
        forecast = model.predict(future)
    
    # Plot the forecast
    st.subheader("📈 Forecast for the Next 12 Months")
    
    # Create a custom plot instead of using plot_plotly
    fig = go.Figure()
    
    # Add the forecast line
    fig.add_trace(go.Scatter(
        x=forecast['ds'],
        y=forecast['yhat'],
        mode='lines',
        line=dict(color='#0072B2'),
        name='Forecast'
    ))
    
    # Add the uncertainty interval
    fig.add_trace(go.Scatter(
        x=forecast['ds'].tolist() + forecast['ds'].tolist()[::-1],
        y=forecast['yhat_upper'].tolist() + forecast['yhat_lower'].tolist()[::-1],
        fill='toself',
        fillcolor='rgba(0, 114, 178, 0.2)',
        line=dict(color='rgba(255, 255, 255, 0)'),
        name='Uncertainty Interval'
    ))
    
    # Add the actual data points as red points
    fig.add_trace(go.Scatter(
        x=df_prophet['ds'],
        y=df_prophet['y'],
        mode='markers',
        marker=dict(color='red', size=8),
        name='Actual Data'
    ))
    
    # Add a vertical line to show where forecast begins
    last_historical_date = df_prophet['ds'].max()
    
    # Instead of add_vline, use add_shape for more control
    fig.add_shape(
        type="line",
        x0=last_historical_date,
        x1=last_historical_date,
        y0=0,
        y1=1,
        yref="paper",
        line=dict(color="red", width=2, dash="dash")
    )
    
    # Add annotation separately
    fig.add_annotation(
        x=last_historical_date,
        y=1,
        yref="paper",
        text="Forecast Start",
        showarrow=False,
        xanchor="left",
        yanchor="bottom",
        xshift=10
    )
    
    # Update layout
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Number of Bookings",
        legend_title="Legend",
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show forecast components
    st.subheader("🔍 Forecast Components")
    fig_comp = model.plot_components(forecast)
    st.pyplot(fig_comp)
    
    # Show forecasted values in a table
    st.subheader("📋 Forecast Data")
    forecast_table = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(forecast_periods).copy()
    forecast_table["ds"] = forecast_table["ds"].dt.strftime("%Y-%m")
    forecast_table.columns = ["Month", "Predicted Bookings", "Lower Bound", "Upper Bound"]
    forecast_table["Predicted Bookings"] = forecast_table["Predicted Bookings"].round().astype(int)
    forecast_table["Lower Bound"] = forecast_table["Lower Bound"].round().astype(int)
    forecast_table["Upper Bound"] = forecast_table["Upper Bound"].round().astype(int)
    st.dataframe(forecast_table, use_container_width=True)
