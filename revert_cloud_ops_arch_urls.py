#!/usr/bin/env python3
"""
Rollback script: Reverts Cloud Operations Architect role matching, synonym expansion,
and Taleo/portal URL modernization back to their backup snapshots.
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
        os.path.join(PROJECT_ROOT, "config.yaml.cloud_ops_arch_backup"),
        os.path.join(PROJECT_ROOT, "config.yaml"),
    ),
    (
        os.path.join(PROJECT_ROOT, "filter", "engine.py.cloud_ops_arch_backup"),
        os.path.join(PROJECT_ROOT, "filter", "engine.py"),
    ),
    (
        os.path.join(PROJECT_ROOT, "web", "routes.py.cloud_ops_arch_backup"),
        os.path.join(PROJECT_ROOT, "web", "routes.py"),
    ),
    (
        os.path.join(PROJECT_ROOT, "scraper", "company_portals.py.cloud_ops_arch_backup"),
        os.path.join(PROJECT_ROOT, "scraper", "company_portals.py"),
    ),
    (
        os.path.join(PROJECT_ROOT, "scraper", "websites_scraper.py.cloud_ops_arch_backup"),
        os.path.join(PROJECT_ROOT, "scraper", "websites_scraper.py"),
    ),
]


def revert():
    logger.info("Starting rollback of Cloud Operations Architect and Portal URL changes...")
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
        logger.info("✓ Successfully reverted changes!")
    else:
        logger.error("✗ Rollback completed with errors.")
    return success


if __name__ == "__main__":
    if revert():
        sys.exit(0)
    else:
        sys.exit(1)
