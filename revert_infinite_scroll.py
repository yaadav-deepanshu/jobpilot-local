#!/usr/bin/env python3
"""
Rollback Script for Infinite Scroll Feature.
Reverts web/templates/index.html back to the classic Previous/Next pagination layout.
Usage:
    python revert_infinite_scroll.py
"""

import os
import shutil
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKUP_PATH = os.path.join(PROJECT_ROOT, 'web', 'templates', 'index.html.classic_backup')
TARGET_PATH = os.path.join(PROJECT_ROOT, 'web', 'templates', 'index.html')

def revert():
    if not os.path.exists(BACKUP_PATH):
        print(f"✗ Backup file not found at {BACKUP_PATH}")
        sys.exit(1)

    print("🔄 Reverting index.html to classic pagination...")
    shutil.copy2(BACKUP_PATH, TARGET_PATH)
    print("✅ Successfully restored web/templates/index.html from classic backup.")
    print("   Classic Previous/Next pagination is now active.")

if __name__ == '__main__':
    revert()
