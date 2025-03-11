import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Add custom CSS for card styling
st.markdown("""
<style>
    div.stContainer {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    h3 {
        color: #262730;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Sample Data
df = pd.DataFrame({
    "Category": ["A", "B", "C", "D", "E"],
    "Value": np.random.randint(10, 100, 5),
    "Growth": np.random.uniform(1.1, 2.0, 5),
})

# Page title
st.title("📊 Interactive Data Analysis Dashboard")

# Create 5 columns (for 5 cards)
col1, col2, col3 = st.columns(3)
col4, col5 = st.columns(2)

# Card 1: Summary Statistics
with col1:
    st.markdown("<h3>📌 Summary Statistics</h3>", unsafe_allow_html=True)
    with st.container():
        st.write(df.describe())

# Card 2: Bar Chart Visualization
with col2:
    st.markdown("<h3>📊 Bar Chart</h3>", unsafe_allow_html=True)
    with st.container():
        fig = px.bar(df, x="Category", y="Value", title="Category Value Distribution")
        st.plotly_chart(fig)

# Card 3: Growth Rate
with col3:
    st.markdown("<h3>📈 Growth Rate Analysis</h3>", unsafe_allow_html=True)
    with st.container():
        category = st.selectbox("Select a Category", df["Category"])
        growth = df[df["Category"] == category]["Growth"].values[0]
        st.metric(label=f"Growth Rate of {category}", value=f"{growth:.2f}x")

# Card 4: Data Filtering
with col4:
    st.markdown("<h3>🔍 Filter Data</h3>", unsafe_allow_html=True)
    with st.container():
        threshold = st.slider("Filter values greater than:", 0, 100, 50)
        filtered_df = df[df["Value"] > threshold]
        st.dataframe(filtered_df)

# Card 5: Download Processed Data
with col5:
    st.markdown("<h3>💾 Download Data</h3>", unsafe_allow_html=True)
    with st.container():
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "data.csv", "text/csv")

