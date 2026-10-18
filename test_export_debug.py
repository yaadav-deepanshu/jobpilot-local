"""Debug export endpoints"""
import sys
sys.path.insert(0, r"G:\Geonix\vscode\ai\job-finder")

from web.app import create_app
from db.models import db, Job
import requests
import json

app = create_app()

# Start the app in a thread for testing
import threading
import time

def run_server():
    with app.app_context():
        app.run(debug=False, port=5000, use_reloader=False)

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
time.sleep(2)

# Test the endpoints
print("Testing export endpoints...")

try:
    # Test Excel
    print("\n1. Testing Excel export...")
    resp = requests.get("http://127.0.0.1:5000/export/download/excel", timeout=5)
    print(f"   Status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"   Error: {resp.text}")
    else:
        print(f"   Size: {len(resp.content)} bytes")
except Exception as e:
    print(f"   Exception: {e}")

try:
    # Test HTML
    print("\n2. Testing HTML export...")
    resp = requests.get("http://127.0.0.1:5000/export/download/html", timeout=5)
    print(f"   Status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"   Error: {resp.text}")
    else:
        print(f"   Size: {len(resp.content)} bytes")
except Exception as e:
    print(f"   Exception: {e}")

try:
    # Test PDF
    print("\n3. Testing PDF export...")
    resp = requests.get("http://127.0.0.1:5000/export/download/pdf", timeout=5)
    print(f"   Status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"   Error: {resp.text}")
    else:
        print(f"   Size: {len(resp.content)} bytes")
except Exception as e:
    print(f"   Exception: {e}")
