"""Direct test of export functions with real app context"""
import sys
sys.path.insert(0, r"G:\Geonix\vscode\ai\job-finder")

from web.app import create_app
from db.models import db, Job
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

app = create_app()

with app.app_context():
    # Get jobs (should be 0)
    jobs = Job.query.all()
    print(f"Total jobs in DB: {len(jobs)}")

    # Try the export routes directly
    from export.routes import download_excel, download_html, download_pdf

    # Simulate Flask test client
    from flask import Flask
    with app.test_client() as client:
        print("\n1. Testing Excel endpoint...")
        try:
            response = client.get('/export/download/excel')
            print(f"   Status: {response.status_code}")
            if response.status_code == 500:
                print(f"   Error body: {response.get_data(as_text=True)}")
        except Exception as e:
            print(f"   Exception: {e}")
            import traceback
            traceback.print_exc()

        print("\n2. Testing HTML endpoint...")
        try:
            response = client.get('/export/download/html')
            print(f"   Status: {response.status_code}")
            if response.status_code == 500:
                print(f"   Error body: {response.get_data(as_text=True)}")
        except Exception as e:
            print(f"   Exception: {e}")
            import traceback
            traceback.print_exc()

        print("\n3. Testing PDF endpoint...")
        try:
            response = client.get('/export/download/pdf')
            print(f"   Status: {response.status_code}")
            if response.status_code == 500:
                print(f"   Error body: {response.get_data(as_text=True)}")
        except Exception as e:
            print(f"   Exception: {e}")
            import traceback
            traceback.print_exc()
