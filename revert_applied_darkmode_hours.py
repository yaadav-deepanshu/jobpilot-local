#!/usr/bin/env python3
"""
Rollback Script for Applied Red Badge, Action Button Relocation, Dark Mode Toggle,
and Strict Hours Window Filtering Features.
Restores web/routes.py, web/templates/index.html, and web/templates/jobs.html back to
their exact versions prior to these updates.

Usage:
    python revert_applied_darkmode_hours.py
"""

import os
import shutil
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ROUTES_BACKUP = os.path.join(PROJECT_ROOT, 'web', 'routes.py.hours_backup')
ROUTES_TARGET = os.path.join(PROJECT_ROOT, 'web', 'routes.py')
INDEX_BACKUP = os.path.join(PROJECT_ROOT, 'web', 'templates', 'index.html.hours_backup')
INDEX_TARGET = os.path.join(PROJECT_ROOT, 'web', 'templates', 'index.html')
JOBS_BACKUP = os.path.join(PROJECT_ROOT, 'web', 'templates', 'jobs.html.hours_backup')
JOBS_TARGET = os.path.join(PROJECT_ROOT, 'web', 'templates', 'jobs.html')

def revert():
    print("🔄 Starting rollback of Applied Red Badge, Action Buttons, Dark Mode & Hours Filtering...")
    restored = 0

    if os.path.exists(ROUTES_BACKUP):
        shutil.copy2(ROUTES_BACKUP, ROUTES_TARGET)
        print("  ✅ Restored web/routes.py from pre-hours backup")
        restored += 1
    else:
        print(f"  ❌ Backup missing: {ROUTES_BACKUP}", file=sys.stderr)

    if os.path.exists(INDEX_BACKUP):
        shutil.copy2(INDEX_BACKUP, INDEX_TARGET)
        print("  ✅ Restored web/templates/index.html from pre-hours backup")
        restored += 1
    else:
        print(f"  ❌ Backup missing: {INDEX_BACKUP}", file=sys.stderr)

    if os.path.exists(JOBS_BACKUP):
        shutil.copy2(JOBS_BACKUP, JOBS_TARGET)
        print("  ✅ Restored web/templates/jobs.html from pre-hours backup")
        restored += 1
    else:
        print(f"  ❌ Backup missing: {JOBS_BACKUP}", file=sys.stderr)

    if restored == 3:
        print("\n🎉 Successfully restored all 3 files to previous state.")
        print("   Applied badge, button positions, dark mode, and hours filtering have been reverted.")
        return 0
    else:
        print(f"\n⚠️ Only {restored}/3 files restored. Check error messages above.", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(revert())
