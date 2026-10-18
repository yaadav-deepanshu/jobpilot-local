#!/usr/bin/env python3
"""
Quick test to verify the Job Finder system is working
"""
import requests
import json
import time
import sys

BASE_URL = "http://127.0.0.1:5000"

print("=" * 60)
print("JOB FINDER SYSTEM TEST")
print("=" * 60)

# Test 1: Check if server is running
print("\n1️⃣ Testing if server is running...")
try:
    response = requests.get(f"{BASE_URL}/", timeout=5)
    print(f"   ✅ Server is responding (Status: {response.status_code})")
except Exception as e:
    print(f"   ❌ Server not responding: {e}")
    sys.exit(1)

# Test 2: Check if stats endpoint works
print("\n2️⃣ Testing stats endpoint...")
try:
    response = requests.get(f"{BASE_URL}/api/stats", timeout=5)
    stats = response.json()
    print(f"   ✅ Stats API working")
    print(f"      - Total jobs: {stats.get('total_jobs', 0)}")
    print(f"      - New jobs: {stats.get('new', 0)}")
    print(f"      - Applied: {stats.get('applied', 0)}")
    print(f"      - Platforms: {len(stats.get('by_platform', {}))}")
except Exception as e:
    print(f"   ❌ Stats API error: {e}")

# Test 3: Trigger flexible scrape
print("\n3️⃣ Testing flexible scrape endpoint...")
try:
    print("   ⏳ Starting scrape (this will run in background)...")
    response = requests.post(f"{BASE_URL}/api/flexible-scrape", timeout=5)
    result = response.json()
    print(f"   ✅ Scrape API response:")
    print(f"      - Status: {result.get('status', 'unknown')}")
    print(f"      - Message: {result.get('message', 'N/A')}")
except Exception as e:
    print(f"   ❌ Scrape API error: {e}")

# Test 4: Wait and check if jobs are being added
print("\n4️⃣ Waiting for jobs to be scraped...")
for i in range(5):
    time.sleep(3)
    try:
        response = requests.get(f"{BASE_URL}/api/stats", timeout=5)
        stats = response.json()
        total = stats.get('total_jobs', 0)
        print(f"   [{i+1}/5] Total jobs: {total}")
        if total > 0:
            print(f"   ✅ Jobs are being scraped! Current count: {total}")
            break
    except:
        pass

print("\n" + "=" * 60)
print("✅ SYSTEM TEST COMPLETE")
print("=" * 60)
print("\nTo view dashboard: http://127.0.0.1:5000")
print("To download results: Click 'Download Excel' button")
