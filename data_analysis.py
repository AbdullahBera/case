import pandas as pd
import numpy as np
import os
from typing import Dict, Any, Optional

def load_sample_data() -> pd.DataFrame:
    """Load sample data - replace with your own data loading function"""
    return pd.DataFrame({
        "Category": ["A", "B", "C", "D", "E"],
        "Value": np.random.randint(10, 100, 5),
        "Growth": np.random.uniform(1.1, 2.0, 5),
    })

def load_data(file_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load dataset from data directory
    
    Args:
        file_path: Optional path to data file relative to data directory
        
    Returns:
        Pandas DataFrame with loaded data
    """
    if file_path:
        # Check if file exists in data directory
        full_path = os.path.join('data', file_path)
        if os.path.exists(full_path):
            # Determine file type and load accordingly
            if file_path.endswith('.csv'):
                return pd.read_csv(full_path)
            elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                return pd.read_excel(full_path)
            elif file_path.endswith('.json'):
                return pd.read_json(full_path)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")
    
    # If no file_path or file doesn't exist, return sample data
    return load_sample_data()

def get_summary_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Get summary statistics for the dataframe"""
    return df.describe()

def filter_data(df: pd.DataFrame, column: str, threshold: float) -> pd.DataFrame:
    """Filter dataframe based on threshold value"""
    return df[df[column] > threshold]

def analyze_growth(df: pd.DataFrame, category_col: str, growth_col: str, selected_category: str) -> float:
    """Calculate growth for a specific category"""
    return df[df[category_col] == selected_category][growth_col].values[0]

# Add more data analysis functions as needed