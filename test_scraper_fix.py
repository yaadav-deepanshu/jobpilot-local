#!/usr/bin/env python3
"""Quick test of fixed scraper"""
import asyncio
from scraper.flexible_scraper import FlexibleJobScraper
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

async def test():
    scraper = FlexibleJobScraper(config)
    jobs = await scraper.scrape_flexible_maximum()
    print(f"✓ Scraped {len(jobs)} jobs total")
    if len(jobs) > 0:
        print("Sample jobs:")
        for job in jobs[:3]:
            print(f"  - {job['title']} at {job['company']}")

asyncio.run(test())
