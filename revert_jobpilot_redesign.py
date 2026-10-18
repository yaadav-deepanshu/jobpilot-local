#!/usr/bin/env python3
"""
Rollback Script for JobPilot Redesign.
Restores web/templates/index.html and web/templates/jobs.html back to their
exact pre-redesign versions.

Usage:
    python revert_jobpilot_redesign.py
"""

import os
import shutil
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, 'web', 'templates')

INDEX_BACKUP = os.path.join(TEMPLATES_DIR, 'index.html.jobpilot_backup')
INDEX_TARGET = os.path.join(TEMPLATES_DIR, 'index.html')

JOBS_BACKUP = os.path.join(TEMPLATES_DIR, 'jobs.html.jobpilot_backup')
JOBS_TARGET = os.path.join(TEMPLATES_DIR, 'jobs.html')

BASE_BACKUP = os.path.join(TEMPLATES_DIR, 'base.html.jobpilot_backup')
BASE_TARGET = os.path.join(TEMPLATES_DIR, 'base.html')

def revert():
    print("🔄 Starting JobPilot redesign rollback...")
    restored = 0

    if os.path.exists(INDEX_BACKUP):
        shutil.copy2(INDEX_BACKUP, INDEX_TARGET)
        print("  ✅ Restored web/templates/index.html from pre-redesign backup")
        restored += 1
    else:
        print(f"  ⚠️ Index backup not found at {INDEX_BACKUP}")

    if os.path.exists(JOBS_BACKUP):
        shutil.copy2(JOBS_BACKUP, JOBS_TARGET)
        print("  ✅ Restored web/templates/jobs.html from pre-redesign backup")
        restored += 1
    else:
        print(f"  ⚠️ Jobs table backup not found at {JOBS_BACKUP}")

    if os.path.exists(BASE_BACKUP):
        shutil.copy2(BASE_BACKUP, BASE_TARGET)
        print("  ✅ Restored web/templates/base.html from pre-redesign backup")
        restored += 1

    if restored > 0:
        print(f"\n🎉 Successfully restored {restored} template(s) to previous state.")
        print("   Previous design is now restored and active.")
    else:
        print("\n❌ Rollback failed: No backup files were found.")
        sys.exit(1)

if __name__ == '__main__':
    revert()
