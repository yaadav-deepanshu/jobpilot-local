"""Debug export endpoint failures"""
import sys
sys.path.insert(0, r"G:\Geonix\vscode\ai\job-finder")

import requests
import logging

logging.basicConfig(level=logging.DEBUG)

BASE_URL = "http://127.0.0.1:5000"

print("Testing export endpoints with detailed error info...\n")

endpoints = [
    ("/export/download/excel", "Excel"),
    ("/export/download/html", "HTML"),
    ("/export/download/pdf", "PDF"),
]

for endpoint, name in endpoints:
    try:
        print(f"Testing {name}: {endpoint}")
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        print(f"  Status: {response.status_code}")

        if response.status_code != 200:
            print(f"  Error response:")
            print(f"  Headers: {dict(response.headers)}")
            print(f"  Body: {response.text[:500]}")
        else:
            print(f"  Success! Size: {len(response.content)} bytes")
        print()
    except Exception as e:
        print(f"  Exception: {e}\n")
