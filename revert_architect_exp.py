#!/usr/bin/env python3
"""
Rollback Script for Architect Experience Checking Feature.
Restores filter/engine.py, web/routes.py, and config.yaml to their state prior to the update.

Usage:
    python revert_architect_exp.py
"""

import os
import shutil
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

FILES_TO_RESTORE = [
    (
        os.path.join(PROJECT_ROOT, 'filter', 'engine.py.architect_exp_backup'),
        os.path.join(PROJECT_ROOT, 'filter', 'engine.py')
    ),
    (
        os.path.join(PROJECT_ROOT, 'web', 'routes.py.architect_exp_backup'),
        os.path.join(PROJECT_ROOT, 'web', 'routes.py')
    ),
    (
        os.path.join(PROJECT_ROOT, 'config.yaml.architect_exp_backup'),
        os.path.join(PROJECT_ROOT, 'config.yaml')
    ),
]

def revert():
    print("🔄 Starting rollback of Architect Experience Checking Feature...")
    all_ok = True

    for backup_path, target_path in FILES_TO_RESTORE:
        if not os.path.exists(backup_path):
            print(f"  ❌ Backup missing: {backup_path}", file=sys.stderr)
            all_ok = False
            continue
        shutil.copy2(backup_path, target_path)
        print(f"  ✅ Restored {os.path.relpath(target_path, PROJECT_ROOT)}")

    if all_ok:
        print("\n🎉 Successfully restored all files to pre-architect-update state.")
    else:
        print("\n⚠️ Rollback completed with errors.", file=sys.stderr)
    return all_ok

if __name__ == '__main__':
    success = revert()
    sys.exit(0 if success else 1)
