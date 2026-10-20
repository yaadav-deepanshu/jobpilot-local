#!/usr/bin/env python3
"""
Rollback script: Reverts Portal Jobs Scanner Feature
Restores web/routes.py, db/models.py, and templates from .portal_jobs_backup files.
"""

import os
import shutil
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

FILES_TO_RESTORE = [
    (
        os.path.join(PROJECT_ROOT, "web", "routes.py.portal_jobs_backup"),
        os.path.join(PROJECT_ROOT, "web", "routes.py"),
    ),
    (
        os.path.join(PROJECT_ROOT, "db", "models.py.portal_jobs_backup"),
        os.path.join(PROJECT_ROOT, "db", "models.py"),
    ),
    (
        os.path.join(PROJECT_ROOT, "web", "templates", "base.html.portal_jobs_backup"),
        os.path.join(PROJECT_ROOT, "web", "templates", "base.html"),
    ),
    (
        os.path.join(PROJECT_ROOT, "web", "templates", "portals.html.portal_jobs_backup"),
        os.path.join(PROJECT_ROOT, "web", "templates", "portals.html"),
    ),
    (
        os.path.join(PROJECT_ROOT, "web", "templates", "index.html.portal_jobs_backup"),
        os.path.join(PROJECT_ROOT, "web", "templates", "index.html"),
    ),
    (
        os.path.join(PROJECT_ROOT, "web", "templates", "jobs.html.portal_jobs_backup"),
        os.path.join(PROJECT_ROOT, "web", "templates", "jobs.html"),
    ),
]

OPTIONAL_FILES_TO_REMOVE = [
    os.path.join(PROJECT_ROOT, "web", "templates", "portal_jobs.html"),
    os.path.join(PROJECT_ROOT, "scraper", "portal_jobs_scanner.py"),
]


def revert():
    logger.info("Starting rollback of Portal Jobs Scanner changes...")
    success = True

    for backup_path, target_path in FILES_TO_RESTORE:
        if os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, target_path)
                logger.info(f"✓ Restored: {target_path} from {backup_path}")
            except Exception as e:
                logger.error(f"✗ Failed to restore {target_path}: {e}")
                success = False
        else:
            logger.warning(f"⚠ Backup not found: {backup_path}")
            success = False

    if success:
        logger.info("✓ Successfully reverted Portal Jobs Scanner feature!")
    else:
        logger.error("✗ Rollback completed with errors.")
    return success


if __name__ == "__main__":
    revert()
