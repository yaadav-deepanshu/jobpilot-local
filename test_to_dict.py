"""Test what to_dict() returns"""
import sys
sys.path.insert(0, r"G:\Geonix\vscode\ai\job-finder")

from web.app import create_app
from db.models import db, Job

app = create_app()

with app.app_context():
    # Get jobs from database
    jobs = Job.query.all()
    print(f"Total jobs: {len(jobs)}")

    if jobs:
        print(f"\nFirst job to_dict():")
        print(jobs[0].to_dict())
        print(f"\nKeys: {list(jobs[0].to_dict().keys())}")
    else:
        print("\nNo jobs in database - testing with empty list")
        jobs_data = []
        import pandas as pd
        df = pd.DataFrame(jobs_data)
        print(f"DataFrame from empty list:")
        print(f"  Columns: {list(df.columns)}")
        print(f"  Shape: {df.shape}")
