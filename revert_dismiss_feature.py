#!/usr/bin/env python3
"""
Rollback Script for Dismiss Confirmation & Search Exclusion Feature.
Restores web/routes.py and web/templates/index.html back to their exact versions
prior to the dismiss confirmation modal and search exclusion updates.

Usage:
    python revert_dismiss_feature.py
"""

import os
import shutil
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ROUTES_BACKUP = os.path.join(PROJECT_ROOT, 'web', 'routes.py.dismiss_backup')
ROUTES_TARGET = os.path.join(PROJECT_ROOT, 'web', 'routes.py')
INDEX_BACKUP = os.path.join(PROJECT_ROOT, 'web', 'templates', 'index.html.dismiss_backup')
INDEX_TARGET = os.path.join(PROJECT_ROOT, 'web', 'templates', 'index.html')

def revert():
    print("🔄 Starting Dismiss Confirmation & Search Exclusion rollback...")
    restored = 0

    if os.path.exists(ROUTES_BACKUP):
        shutil.copy2(ROUTES_BACKUP, ROUTES_TARGET)
        print("  ✅ Restored web/routes.py from pre-dismiss backup")
        restored += 1
    else:
        print(f"  ❌ Backup missing: {ROUTES_BACKUP}", file=sys.stderr)

    if os.path.exists(INDEX_BACKUP):
        shutil.copy2(INDEX_BACKUP, INDEX_TARGET)
        print("  ✅ Restored web/templates/index.html from pre-dismiss backup")
        restored += 1
    else:
        print(f"  ❌ Backup missing: {INDEX_BACKUP}", file=sys.stderr)

    if restored == 2:
        print("\n🎉 Successfully restored files to previous state.")
        print("   Dismiss confirmation and search exclusion changes have been reverted.")
        return 0
    else:
        print(f"\n⚠️ Only {restored}/2 files restored. Check error messages above.", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(revert())
