import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from typing import List, Dict, Any, Callable, Optional, Union

# --- STYLING ---
def setup_page_style():
    """Set up the page styling with custom CSS"""
    st.markdown("""
    <style>
        div.card {
            background-color: #f0f2f6;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        h3 {
            color: #262730;
            margin-bottom: 10px;
        }
        .card-title {
            font-weight: bold;
            margin-bottom: 12px;
        }
    </style>
    """, unsafe_allow_html=True)

# --- DATA HANDLING ---
def load_sample_data() -> pd.DataFrame:
    """Load sample data - replace with your own data loading function"""
    return pd.DataFrame({
        "Category": ["A", "B", "C", "D", "E"],
        "Value": np.random.randint(10, 100, 5),
        "Growth": np.random.uniform(1.1, 2.0, 5),
    })

def load_data() -> pd.DataFrame:
    """Load the dataset - customize this function for your own data sources"""
    # Replace this with your actual data loading logic
    return load_sample_data()

# --- CARD COMPONENTS ---
def create_card(container, title: str, icon: str, content_function: Callable, *args, **kwargs):
    """Create a card with a title and content"""
    with container:
        st.markdown(f"<h3>{icon} {title}</h3>", unsafe_allow_html=True)
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            content_function(*args, **kwargs)
            st.markdown('</div>', unsafe_allow_html=True)

# --- CARD CONTENT FUNCTIONS ---
def display_summary_stats(df: pd.DataFrame):
    """Display summary statistics"""
    st.write(df.describe())

def display_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str):
    """Display a bar chart"""
    fig = px.bar(df, x=x_col, y=y_col, title=title)
    st.plotly_chart(fig, use_container_width=True)

def display_line_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str):
    """Display a line chart"""
    fig = px.line(df, x=x_col, y=y_col, title=title)
    st.plotly_chart(fig, use_container_width=True)

def display_growth_analysis(df: pd.DataFrame, category_col: str, growth_col: str):
    """Display growth rate analysis with a dropdown selection"""
    category = st.selectbox("Select a Category", df[category_col])
    growth = df[df[category_col] == category][growth_col].values[0]
    st.metric(label=f"Growth Rate of {category}", value=f"{growth:.2f}x")

def display_data_filter(df: pd.DataFrame, filter_col: str, min_val: int, max_val: int, default: int):
    """Display data filtering controls"""
    threshold = st.slider(f"Filter {filter_col} greater than:", min_val, max_val, default)
    filtered_df = df[df[filter_col] > threshold]
    st.dataframe(filtered_df)

def display_download_option(df: pd.DataFrame, filename: str = "data.csv"):
    """Display download button for data"""
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", csv, filename, "text/csv")

def display_scatter_plot(df: pd.DataFrame, x_col: str, y_col: str, color_col: Optional[str] = None, title: str = "Scatter Plot"):
    """Display a scatter plot"""
    fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=title)
    st.plotly_chart(fig, use_container_width=True)

def display_pie_chart(df: pd.DataFrame, names_col: str, values_col: str, title: str = "Pie Chart"):
    """Display a pie chart"""
    fig = px.pie(df, names=names_col, values=values_col, title=title)
    st.plotly_chart(fig, use_container_width=True)

# --- MAIN APP ---
def main():
    # Setup page
    st.set_page_config(page_title="Data Analysis Dashboard", layout="wide")
    setup_page_style()
    
    # Page title
    st.title("📊 Interactive Data Analysis Dashboard")
    
    # Load data
    df = load_data()
    
    # Create layout - customize the number of columns and their arrangement as needed
    col1, col2, col3 = st.columns(3)
    col4, col5 = st.columns(2)
    
    # Add cards - easily add or remove cards as needed
    create_card(col1, "Summary Statistics", "📌", display_summary_stats, df)
    create_card(col2, "Bar Chart", "📊", display_bar_chart, df, "Category", "Value", "Category Value Distribution")
    create_card(col3, "Growth Rate Analysis", "📈", display_growth_analysis, df, "Category", "Growth")
    create_card(col4, "Filter Data", "🔍", display_data_filter, df, "Value", 0, 100, 50)
    create_card(col5, "Download Data", "💾", display_download_option, df)
    
    # Example of how to add more cards with different visualizations
    # Uncomment or add your own as needed
    # col6, col7 = st.columns(2)
    # create_card(col6, "Line Chart", "📉", display_line_chart, df, "Category", "Value", "Value Trend")
    # create_card(col7, "Scatter Plot", "🔵", display_scatter_plot, df, "Value", "Growth", "Category", "Value vs Growth")

if __name__ == "__main__":
    main()

