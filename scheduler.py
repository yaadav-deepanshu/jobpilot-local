"""
Background job scheduling
Runs scraper periodically in background
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from db.models import db, Job
from scraper.multi_platform import RealJobScraper
from filter.engine import FilterEngine
import yaml

logger = logging.getLogger(__name__)

scheduler = None

def setup_scheduler(app):
    """Setup APScheduler for background jobs"""
    global scheduler

    scheduler = BackgroundScheduler()

    # Load config
    config = {}
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Could not load config.yaml: {e}")

    scrape_interval = config.get('scheduler', {}).get('scrape_interval_hours', 6)

    # Schedule scraping job
    scheduler.add_job(
        func=scrape_jobs_background,
        trigger="interval",
        hours=scrape_interval,
        id='scrape_jobs',
        name='Scrape jobs from all platforms',
        replace_existing=True,
        args=[app, config]
    )

    scheduler.start()
    logger.info(f"✓ Scheduler started (scrapes every {scrape_interval} hours)")

def scrape_jobs_background(app=None, config=None):
    """Background scrape job"""
    if not config:
        try:
            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f) or {}
        except Exception:
            config = {}

    logger.info("📍 Background scheduled scrape started...")

    try:
        scraper = RealJobScraper(config)
        jobs = scraper.scrape_all(today_only=True, results_per_query=10)

        filter_engine = FilterEngine(config)
        filtered_jobs = filter_engine.filter_jobs(jobs, today_only=True)

        count = 0
        ctx = app.app_context() if app else db.app.app_context()
        with ctx:
            for job_data in filtered_jobs:
                url = job_data.get('url', '').strip()
                if not url:
                    continue

                existing = Job.query.filter_by(url=url).first()
                if not existing:
                    job = Job(
                        platform=job_data['platform'],
                        title=job_data['title'],
                        company=job_data['company'],
                        location=job_data.get('location', ''),
                        url=url,
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

            db.session.commit()

        logger.info(f"✓ Added {count} new jobs to database from scheduled run")
        return count

    except Exception as e:
        logger.error(f"Background scrape error: {e}", exc_info=True)
        return 0
