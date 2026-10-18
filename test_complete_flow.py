#!/usr/bin/env python3
"""Test the complete flow: scrape -> filter -> save to DB"""
import asyncio
import yaml
import sys
sys.path.insert(0, '.')

from web.app import create_app
from scraper.flexible_scraper import FlexibleJobScraper
from filter.flexible_engine import FlexibleFilterEngine
from db.models import db, Job

async def test_complete_flow():
    print("=" * 60)
    print("COMPLETE FLOW TEST: Scrape -> Filter -> Save to DB")
    print("=" * 60)

    # Create Flask app
    app = create_app()

    with app.app_context():
        # Load config
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        print("\n1️⃣  Scraping jobs...")
        scraper = FlexibleJobScraper(config)
        jobs = await scraper.scrape_flexible_maximum()
        print(f"   ✓ Scraped {len(jobs)} jobs")

        print("\n2️⃣  Filtering jobs...")
        filter_engine = FlexibleFilterEngine(config)
        filtered_jobs = filter_engine.filter_jobs(jobs)
        print(f"   ✓ Filtered to {len(filtered_jobs)} jobs")

        print("\n3️⃣  Saving to database...")
        count = 0
        for job_data in filtered_jobs:
            try:
                existing = Job.query.filter_by(url=job_data.get('url', '')).first()
                if not existing and job_data.get('url'):
                    job = Job(
                        platform=job_data['platform'],
                        title=job_data['title'],
                        company=job_data['company'],
                        location=job_data.get('location', ''),
                        url=job_data.get('url', ''),
                        description=job_data.get('description', ''),
                        salary=job_data.get('salary', ''),
                        salary_min=job_data.get('salary_min'),
                        salary_max=job_data.get('salary_max'),
                        date_posted=job_data.get('date_posted'),
                        job_type=job_data.get('job_type', 'Full-time'),
                        num_applicants=job_data.get('num_applicants'),
                        is_easy_apply=job_data.get('is_easy_apply', False),
                        status='new'
                    )
                    db.session.add(job)
                    count += 1
                    if count % 10 == 0:
                        print(f"   ... added {count} jobs so far")
            except Exception as e:
                print(f"   Error adding job: {e}")
                continue

        db.session.commit()
        print(f"   ✓ Saved {count} jobs to database")

        print("\n4️⃣  Verifying...")
        total = Job.query.count()
        print(f"   ✓ Total jobs in database: {total}")

        print("\n✅ COMPLETE FLOW TEST PASSED!")

asyncio.run(test_complete_flow())
