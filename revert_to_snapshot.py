#!/usr/bin/env python3
"""
Rollback Script: Restores the application to the exact pre-update snapshot.
Usage: python revert_to_snapshot.py
"""

import os
import shutil
import sys

SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), 'backup_snapshot')

def rollback():
    if not os.path.exists(SNAPSHOT_DIR):
        print("✗ No backup snapshot found at backup_snapshot/")
        sys.exit(1)

    print("🔄 Rolling back to backup snapshot...")
    for root, dirs, files in os.walk(SNAPSHOT_DIR):
        for f in files:
            src = os.path.join(root, f)
            rel_path = os.path.relpath(src, SNAPSHOT_DIR)
            dest = os.path.join(os.path.dirname(__file__), rel_path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(src, dest)
            print(f"  Restored {rel_path}")

    print("✅ Rollback complete. Project restored to original working state.")

if __name__ == '__main__':
    rollback()
