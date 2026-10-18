"""Test the actual export error"""
import sys
sys.path.insert(0, r"G:\Geonix\vscode\ai\job-finder")

from db.models import Job
import pandas as pd

# Simulate what to_dict() returns
jobs_data = []

# Create DataFrame
df = pd.DataFrame(jobs_data)
print(f"Empty DataFrame columns: {list(df.columns)}")
print(f"Empty DataFrame shape: {df.shape}")

# Try to access columns like the code does
try:
    cols = df[[col for col in ['platform', 'title', 'company'] if col in df.columns]]
    print(f"Selected columns: {list(cols.columns)}")
except Exception as e:
    print(f"Error selecting columns: {e}")

# The issue is likely in groupby with empty data
try:
    if len(df) > 0:
        platform_summary = df.groupby('platform').agg({
            'url': 'count',
            'status': lambda x: (x == 'applied').sum()
        })
        print(f"Platform summary: {platform_summary}")
    else:
        print("DataFrame is empty, skipping groupby")
except Exception as e:
    print(f"Error in groupby: {e}")
