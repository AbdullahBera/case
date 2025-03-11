import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

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
    with st.expander("📌 Summary Statistics", expanded=True):
        st.write(df.describe())

# Card 2: Bar Chart Visualization
with col2:
    with st.expander("📊 Bar Chart"):
        fig = px.bar(df, x="Category", y="Value", title="Category Value Distribution")
        st.plotly_chart(fig)

# Card 3: Growth Rate
with col3:
    with st.expander("📈 Growth Rate Analysis"):
        category = st.selectbox("Select a Category", df["Category"])
        growth = df[df["Category"] == category]["Growth"].values[0]
        st.metric(label=f"Growth Rate of {category}", value=f"{growth:.2f}x")

# Card 4: Data Filtering
with col4:
    with st.expander("🔍 Filter Data"):
        threshold = st.slider("Filter values greater than:", 0, 100, 50)
        filtered_df = df[df["Value"] > threshold]
        st.dataframe(filtered_df)

# Card 5: Download Processed Data
with col5:
    with st.expander("💾 Download Data"):
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "data.csv", "text/csv")

