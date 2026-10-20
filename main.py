#!/usr/bin/env python3
"""
Job Finder — Hybrid Job Discovery + One-Click Apply Tool
Main entry point
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from web.app import create_app
from db.models import db, init_db
from scheduler import setup_scheduler

# Ensure UTF-8 output on Windows consoles
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('job_finder.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Initialize and run the Job Finder app"""
    logger.info("🎯 Starting Job Finder...")

    # Create Flask app
    app = create_app()

    # Initialize database and enforce 0-4y experience / <=100 applicant limits
    with app.app_context():
        init_db()
        try:
            from web.routes import purge_unqualified_jobs
            purged = purge_unqualified_jobs()
            if purged > 0:
                logger.info(f"✓ Cleaned {purged} legacy jobs violating 0-4y experience or >100 applicant limits")
        except Exception as e:
            logger.warning(f"Note during startup purge: {e}")
        logger.info("✓ Database initialized")

    # Setup scheduler for background scraping
    try:
        setup_scheduler(app)
        logger.info("✓ Scheduler configured")
    except Exception as e:
        logger.warning(f"Scheduler setup skipped or encountered: {e}")

    # Load server configuration (default to port 5050)
    import yaml
    config = {}
    if os.path.exists('config.yaml'):
        try:
            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Could not read config.yaml: {e}")

    app_cfg = config.get('app', {})
    default_port = app_cfg.get('port', 5050)
    default_host = app_cfg.get('host', '127.0.0.1')

    port = int(os.environ.get('PORT', default_port))
    host = os.environ.get('HOST', default_host)
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() in ('true', '1', 'yes')

    # Start companion listener on port 5000 if primary is 5050 (or 5050 if primary is 5000)
    alt_port = 5000 if port == 5050 else (5050 if port == 5000 else None)
    if alt_port:
        try:
            from werkzeug.serving import make_server
            import threading
            alt_server = make_server(host, alt_port, app)
            t_alt = threading.Thread(target=alt_server.serve_forever, daemon=True)
            t_alt.start()
            logger.info(f"✓ Also listening on companion port: http://{host}:{alt_port}")
        except Exception as e:
            logger.info(f"Note: Companion port {alt_port} skipped ({e}); running on primary http://{host}:{port}")

    # Print startup info
    logger.info("=" * 60)
    logger.info("Job Finder is running!")
    logger.info("=" * 60)
    logger.info(f"📱 Primary Dashboard:     http://{host}:{port}")
    if alt_port:
        logger.info(f"📱 Companion Port:        http://{host}:{alt_port}")
    logger.info(f"🌐 Portals & Sites:       http://{host}:{port}/portals")
    logger.info(f"🏢 Portal Jobs (<4y):     http://{host}:{port}/portal-jobs")
    logger.info("=" * 60)

    # Run the app
    app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=False
    )

if __name__ == '__main__':
    main()
