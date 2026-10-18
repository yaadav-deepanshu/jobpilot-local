#!/usr/bin/env python3
"""Test JobSpy directly"""
from jobspy import scrape_jobs

print("Test 1: JobSpy with hours_old=24")
try:
    jobs = scrape_jobs(
        site_name=['indeed'],
        search_term='DevOps',
        location='Bengaluru',
        results_wanted=5,
        hours_old=24
    )
    print(f"  Result: {len(jobs)} jobs")
except Exception as e:
    print(f"  Error: {e}")

print("\nTest 2: JobSpy without hours_old")
try:
    jobs = scrape_jobs(
        site_name=['indeed'],
        search_term='DevOps Engineer',
        location='India',
        results_wanted=5
    )
    print(f"  Result: {len(jobs)} jobs")
    if len(jobs) > 0:
        print("  Sample jobs:")
        for idx, job in jobs.iterrows():
            print(f"    - {job['title']} at {job['company']}")
except Exception as e:
    print(f"  Error: {e}")

print("\nTest 3: JobSpy LinkedIn")
try:
    jobs = scrape_jobs(
        site_name=['linkedin'],
        search_term='DevOps',
        location='India',
        results_wanted=5
    )
    print(f"  Result: {len(jobs)} jobs")
except Exception as e:
    print(f"  Error: {e}")
