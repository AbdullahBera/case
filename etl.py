import pandas as pd
import numpy as np

# EXTRACT: Load structured & unstructured data
def extract_data():
    df = pd.DataFrame({
        "Category": ["A", "B", "C", "D", "E"],
        "Value": np.random.randint(10, 100, 5),
        "Growth": np.random.uniform(1.1, 2.0, 5),
    })
    return df

# TRANSFORM: Clean & Process Data
def transform_data(df):
    df["Value"] = df["Value"].astype(float)
    df["Growth"] = df["Growth"].round(2)
    df["Performance"] = df["Growth"].apply(lambda x: "High" if x > 1.5 else "Low")
    return df

# LOAD: Save processed data for analysis
def load_data(df):
    df.to_csv("data/processed_data.csv", index=False)
    return df

def run_etl():
    raw_df = extract_data()
    cleaned_df = transform_data(raw_df)
    return load_data(cleaned_df)
