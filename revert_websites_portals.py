#!/usr/bin/env python3
"""
Rollback script: Reverts 100 Big Companies Portals & 24 Specialized Job Websites integration
Restores config.yaml, web/routes.py, and related template/scraper additions.
"""

import os
import shutil
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

FILES_TO_RESTORE = [
    (
        os.path.join(PROJECT_ROOT, "config.yaml.websites_portals_backup"),
        os.path.join(PROJECT_ROOT, "config.yaml"),
    ),
    (
        os.path.join(PROJECT_ROOT, "web", "routes.py.websites_portals_backup"),
        os.path.join(PROJECT_ROOT, "web", "routes.py"),
    ),
    (
        os.path.join(PROJECT_ROOT, "main.py.portals_fix_backup"),
        os.path.join(PROJECT_ROOT, "main.py"),
    ),
]

OPTIONAL_FILES_TO_REMOVE = [
    os.path.join(PROJECT_ROOT, "web", "templates", "portals.html"),
    os.path.join(PROJECT_ROOT, "scraper", "company_portals.py"),
    os.path.join(PROJECT_ROOT, "scraper", "websites_scraper.py"),
]


def revert():
    logger.info("Starting rollback of Websites and Company Portals changes...")
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
        logger.info("✓ Successfully reverted websites and portals integration!")
    else:
        logger.error("✗ Rollback completed with errors.")
    return success


if __name__ == "__main__":
    if revert():
        sys.exit(0)
    else:
        sys.exit(1)
