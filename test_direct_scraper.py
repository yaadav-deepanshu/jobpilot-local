#!/usr/bin/env python3
"""Direct test of scraper without Flask"""
import asyncio
import logging
from scraper.flexible_scraper import FlexibleJobScraper
import yaml

logging.basicConfig(level=logging.INFO, format='%(message)s')

async def test():
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    print("=" * 60)
    print("DIRECT SCRAPER TEST (No Flask)")
    print("=" * 60)

    scraper = FlexibleJobScraper(config)

    print("\nRunning scraper.scrape_flexible_maximum()...")
    jobs = await scraper.scrape_flexible_maximum()

    print(f"\n✓ Scraper returned {len(jobs)} jobs total")

    if len(jobs) > 0:
        print("\nFirst 5 jobs:")
        for job in jobs[:5]:
            print(f"  - {job.get('title', 'N/A')} @ {job.get('company', 'N/A')}")
            print(f"    Platform: {job.get('platform', 'N/A')}")
            print(f"    URL: {job.get('url', 'N/A')}")
    else:
        print("\n⚠️  No jobs returned by scraper!")

asyncio.run(test())
