#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COMPREHENSIVE FUNCTIONAL TEST SUITE
Job Finder System - Complete Testing
"""
import requests
import json
import time
import sys
import os
from datetime import datetime

# Force UTF-8 output
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:5000"
TEST_RESULTS = []

def log_test(test_name, status, message, details=""):
    """Log test result"""
    result = {
        "test": test_name,
        "status": status,
        "message": message,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    TEST_RESULTS.append(result)

    icon = "✅" if status == "PASS" else "❌"
    print(f"\n{icon} {test_name}")
    print(f"   Status: {status}")
    print(f"   Message: {message}")
    if details:
        print(f"   Details: {details}")

def test_server_connectivity():
    """Test 1: Server is running"""
    print("\n" + "="*60)
    print("TEST 1: SERVER CONNECTIVITY")
    print("="*60)

    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            log_test("Server Running", "PASS", f"Server responding on {BASE_URL}", f"Status Code: {response.status_code}")
            return True
        else:
            log_test("Server Running", "FAIL", f"Unexpected status code", f"Got {response.status_code}")
            return False
    except Exception as e:
        log_test("Server Running", "FAIL", "Server not responding", str(e))
        return False

def test_dashboard_loads():
    """Test 2: Dashboard loads correctly"""
    print("\n" + "="*60)
    print("TEST 2: DASHBOARD LOADING")
    print("="*60)

    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if "Job Finder Dashboard" in response.text:
            log_test("Dashboard HTML", "PASS", "Dashboard contains expected content", "Found 'Job Finder Dashboard'")
        else:
            log_test("Dashboard HTML", "FAIL", "Dashboard missing content", "No 'Job Finder Dashboard' found")

        if "FLEXIBLE SCRAPE" in response.text:
            log_test("Scrape Button", "PASS", "Scrape button present in HTML", "Found FLEXIBLE SCRAPE button")
        else:
            log_test("Scrape Button", "FAIL", "Scrape button missing", "Button not found in HTML")

        if "scrape-status-section" in response.text:
            log_test("Status Section", "PASS", "Status section HTML present", "Found scrape-status-section")
        else:
            log_test("Status Section", "FAIL", "Status section missing", "scrape-status-section not found")

        return True
    except Exception as e:
        log_test("Dashboard Loading", "FAIL", "Error loading dashboard", str(e))
        return False

def test_stats_api():
    """Test 3: Stats API endpoint"""
    print("\n" + "="*60)
    print("TEST 3: STATS API")
    print("="*60)

    try:
        response = requests.get(f"{BASE_URL}/api/stats", timeout=5)

        if response.status_code != 200:
            log_test("Stats API Response", "FAIL", f"Bad status code", f"Got {response.status_code}")
            return False

        data = response.json()
        log_test("Stats API Response", "PASS", "API returns JSON", "Status 200 OK")

        required_fields = ['total_jobs', 'new', 'applied', 'by_platform']
        missing = [f for f in required_fields if f not in data]

        if not missing:
            log_test("Stats Fields", "PASS", "All required fields present", f"Fields: {', '.join(required_fields)}")
        else:
            log_test("Stats Fields", "FAIL", "Missing fields", f"Missing: {missing}")
            return False

        print(f"\n   Current Stats:")
        print(f"   - Total Jobs: {data.get('total_jobs', 0)}")
        print(f"   - New Jobs: {data.get('new', 0)}")
        print(f"   - Applied: {data.get('applied', 0)}")
        print(f"   - Platforms: {len(data.get('by_platform', {}))}")

        return True
    except json.JSONDecodeError as e:
        log_test("Stats API JSON", "FAIL", "Invalid JSON response", str(e))
        return False
    except Exception as e:
        log_test("Stats API", "FAIL", "Error calling API", str(e))
        return False

def test_flexible_scrape_api():
    """Test 4: Flexible Scrape API"""
    print("\n" + "="*60)
    print("TEST 4: FLEXIBLE SCRAPE API")
    print("="*60)

    try:
        response = requests.post(f"{BASE_URL}/api/flexible-scrape", timeout=5)

        if response.status_code != 200:
            log_test("Scrape API Response", "FAIL", f"Bad status code", f"Got {response.status_code}")
            return False

        data = response.json()
        log_test("Scrape API Response", "PASS", "API returns JSON", "Status 200 OK")

        if data.get('status') == 'success':
            log_test("Scrape Status", "PASS", "Scrape started successfully", data.get('message', 'N/A'))
        else:
            log_test("Scrape Status", "FAIL", "Scrape did not start", f"Status: {data.get('status')}")
            return False

        return True
    except Exception as e:
        log_test("Flexible Scrape API", "FAIL", "Error calling API", str(e))
        return False

def test_bulk_scrape_api():
    """Test 5: Bulk Scrape API"""
    print("\n" + "="*60)
    print("TEST 5: BULK SCRAPE API")
    print("="*60)

    try:
        response = requests.post(f"{BASE_URL}/api/bulk-scrape", timeout=5)

        if response.status_code != 200:
            log_test("Bulk Scrape Response", "FAIL", f"Bad status code", f"Got {response.status_code}")
            return False

        data = response.json()
        log_test("Bulk Scrape Response", "PASS", "API returns JSON", "Status 200 OK")

        if data.get('status') == 'success':
            log_test("Bulk Scrape Status", "PASS", "Bulk scrape started successfully", data.get('message', 'N/A'))
        else:
            log_test("Bulk Scrape Status", "FAIL", "Bulk scrape did not start", f"Status: {data.get('status')}")
            return False

        return True
    except Exception as e:
        log_test("Bulk Scrape API", "FAIL", "Error calling API", str(e))
        return False

def test_export_endpoints():
    """Test 6: Export endpoints"""
    print("\n" + "="*60)
    print("TEST 6: EXPORT ENDPOINTS")
    print("="*60)

    endpoints = [
        ("/export/download/excel", "Excel Export"),
        ("/export/download/pdf", "PDF Export"),
        ("/export/download/html", "HTML Export"),
    ]

    all_pass = True
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)

            if response.status_code == 200:
                log_test(f"{name} Endpoint", "PASS", f"Endpoint {endpoint} responding", f"Status: {response.status_code}, Size: {len(response.content)} bytes")
            else:
                log_test(f"{name} Endpoint", "FAIL", f"Bad status code", f"Got {response.status_code}")
                all_pass = False
        except Exception as e:
            log_test(f"{name} Endpoint", "FAIL", "Error calling endpoint", str(e))
            all_pass = False

    return all_pass

def test_scrape_with_polling():
    """Test 7: Scrape with polling for jobs"""
    print("\n" + "="*60)
    print("TEST 7: SCRAPE WITH JOB POLLING")
    print("="*60)

    print("   🔄 Starting flexible scrape...")
    try:
        response = requests.post(f"{BASE_URL}/api/flexible-scrape", timeout=5)
        data = response.json()

        if data.get('status') != 'success':
            log_test("Scrape Start", "FAIL", "Could not start scrape", data.get('message'))
            return False

        log_test("Scrape Start", "PASS", "Scrape started", "Background scraping initiated")

        print("   ⏳ Polling for job results (checking every 5 seconds for 2 minutes)...")

        start_time = time.time()
        max_wait = 120  # 2 minutes
        initial_count = 0
        final_count = 0

        # Get initial count
        response = requests.get(f"{BASE_URL}/api/stats", timeout=5)
        initial_count = response.json().get('total_jobs', 0)
        print(f"   Initial job count: {initial_count}")

        # Poll for changes
        poll_count = 0
        while time.time() - start_time < max_wait:
            time.sleep(5)
            poll_count += 1

            try:
                response = requests.get(f"{BASE_URL}/api/stats", timeout=5)
                current_count = response.json().get('total_jobs', 0)
                elapsed = int(time.time() - start_time)

                if current_count > initial_count:
                    print(f"   [{elapsed}s] Jobs found: {current_count}")
                    final_count = current_count
                    break
                else:
                    print(f"   [{elapsed}s] Still waiting... (current: {current_count})")
            except Exception as e:
                print(f"   Poll error: {e}")

        elapsed_total = int(time.time() - start_time)

        if final_count > initial_count:
            log_test("Jobs Scraped", "PASS", f"Jobs found and added to database", f"Found {final_count - initial_count} new jobs in {elapsed_total}s")
            return True
        else:
            log_test("Jobs Scraped", "FAIL", "No jobs found after 2 minutes", f"Total polls: {poll_count}, Elapsed: {elapsed_total}s")
            return False

    except Exception as e:
        log_test("Scrape Polling", "FAIL", "Error during polling", str(e))
        return False

def generate_report():
    """Generate final test report"""
    print("\n" + "="*60)
    print("FINAL TEST REPORT")
    print("="*60)

    passed = sum(1 for t in TEST_RESULTS if t['status'] == 'PASS')
    failed = sum(1 for t in TEST_RESULTS if t['status'] == 'FAIL')
    total = len(TEST_RESULTS)

    print(f"\n📊 SUMMARY")
    print(f"   Total Tests: {total}")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   Pass Rate: {(passed/total*100):.1f}%")

    print(f"\n📋 DETAILED RESULTS")
    for test in TEST_RESULTS:
        status_icon = "✅" if test['status'] == 'PASS' else "❌"
        print(f"\n{status_icon} {test['test']}")
        print(f"   Status: {test['status']}")
        print(f"   Message: {test['message']}")
        if test['details']:
            print(f"   Details: {test['details']}")

    print(f"\n" + "="*60)
    print("ISSUES FOUND")
    print("="*60)

    issues = [t for t in TEST_RESULTS if t['status'] == 'FAIL']
    if issues:
        for i, issue in enumerate(issues, 1):
            print(f"\n{i}. {issue['test']}")
            print(f"   Problem: {issue['message']}")
            print(f"   Details: {issue['details']}")
    else:
        print("\n✅ No issues found!")

    # Save report to file
    with open("test_report.txt", "w") as f:
        f.write("="*60 + "\n")
        f.write("JOB FINDER FUNCTIONAL TEST REPORT\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("="*60 + "\n\n")

        f.write(f"SUMMARY\n")
        f.write(f"Total Tests: {total}\n")
        f.write(f"Passed: {passed}\n")
        f.write(f"Failed: {failed}\n")
        f.write(f"Pass Rate: {(passed/total*100):.1f}%\n\n")

        f.write("DETAILED RESULTS\n")
        for test in TEST_RESULTS:
            f.write(f"\nTest: {test['test']}\n")
            f.write(f"Status: {test['status']}\n")
            f.write(f"Message: {test['message']}\n")
            if test['details']:
                f.write(f"Details: {test['details']}\n")

    print("\n📄 Report saved to: test_report.txt")

if __name__ == "__main__":
    print("🚀 JOB FINDER FUNCTIONAL TEST SUITE")
    print(f"Testing: {BASE_URL}")
    print(f"Started: {datetime.now().isoformat()}\n")

    # Run tests
    test_server_connectivity()
    test_dashboard_loads()
    test_stats_api()
    test_flexible_scrape_api()
    test_bulk_scrape_api()
    test_export_endpoints()
    test_scrape_with_polling()

    # Generate report
    generate_report()

    print("\n✅ Testing Complete!")
