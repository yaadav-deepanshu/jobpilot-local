import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import create_app
from db.models import db, PortalJob
from scraper.portal_jobs_scanner import PortalJobsScanner
from scraper.company_portals import BIG_COMPANY_PORTALS

app = create_app()

with app.app_context():
    print("="*60)
    print("REPOPULATING PORTAL JOBS DATABASE WITH VERIFIED LIVE REQUISITIONS")
    print("="*60)

    scanner = PortalJobsScanner()

    # 1. First, inspect current jobs in DB
    existing_count = PortalJob.query.count()
    print(f"Current portal jobs in DB: {existing_count}")

    # Run full portal discovery with ATS scrapers and verified URLs
    print("Discovering and qualifying jobs from all company portals...")
    discovered = scanner.scan(mode='all', max_jobs_per_company=15)
    print(f"Total qualified (< 4y) jobs discovered: {len(discovered)}")

    # Check sample URLs
    print("\nSample discovered jobs:")
    for j in discovered[:10]:
        print(f"  [{j['company']}] ({j['ats_type']}) - Score: {j.get('match_score')}%")
        print(f"    Title: {j['title']}")
        print(f"    URL:   {j['url']}")

    # Delete old portal jobs and insert new verified jobs
    print("\nUpdating database...")
    PortalJob.query.delete()
    db.session.commit()

    saved = scanner.save_jobs_to_db(discovered, app=app)
    print(f"✓ Saved {saved} verified portal jobs into database!")

    # Verify DB state
    total_db = PortalJob.query.count()
    print(f"✓ Verified total jobs in DB: {total_db}")

    # Check how many are direct requisition vs portal
    direct_reqs = PortalJob.query.filter(
        (PortalJob.ats_type.in_(['workday', 'greenhouse', 'lever', 'smartrecruiters', 'amazon_jobs'])) |
        (PortalJob.url.like('%/job/%')) |
        (PortalJob.url.like('%/jobs/%'))
    ).count()
    print(f"✓ Direct requisition jobs: {direct_reqs} / {total_db}")
