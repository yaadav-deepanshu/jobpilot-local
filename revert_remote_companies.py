#!/usr/bin/env python3
"""
Rollback script: Reverts Remote Companies Feature
Restores config.yaml, web/routes.py, and db/models.py from .remote_companies_backup files.
"""

import os
import shutil
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

FILES_TO_RESTORE = [
    (
        os.path.join(PROJECT_ROOT, "config.yaml.remote_companies_backup"),
        os.path.join(PROJECT_ROOT, "config.yaml"),
    ),
    (
        os.path.join(PROJECT_ROOT, "web", "routes.py.remote_companies_backup"),
        os.path.join(PROJECT_ROOT, "web", "routes.py"),
    ),
    (
        os.path.join(PROJECT_ROOT, "db", "models.py.remote_companies_backup"),
        os.path.join(PROJECT_ROOT, "db", "models.py"),
    ),
]


def revert():
    """Restore all files from backup"""
    logger.info("Starting rollback of Remote Companies feature...")
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
        logger.info("✓ Successfully reverted Remote Companies feature!")
    else:
        logger.error("✗ Rollback completed with errors.")
    return success


if __name__ == "__main__":
    revert()
