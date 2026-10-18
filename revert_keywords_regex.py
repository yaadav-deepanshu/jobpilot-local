#!/usr/bin/env python3
"""
Rollback Script for Keywords Regex & Title Wildcard Matching Features.
Restores filter/engine.py back to its exact version prior to the regex updates.

Usage:
    python revert_keywords_regex.py
"""

import os
import shutil
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ENGINE_BACKUP = os.path.join(PROJECT_ROOT, 'filter', 'engine.py.keywords_regex_backup')
ENGINE_TARGET = os.path.join(PROJECT_ROOT, 'filter', 'engine.py')

def revert():
    print("🔄 Starting rollback of Keywords Regex & Title Wildcard Matching...")

    if not os.path.exists(ENGINE_BACKUP):
        print(f"  ❌ Backup missing: {ENGINE_BACKUP}", file=sys.stderr)
        return False

    shutil.copy2(ENGINE_BACKUP, ENGINE_TARGET)
    print("  ✅ Restored filter/engine.py from pre-regex backup")
    print("\n🎉 Successfully restored filter/engine.py to previous state.")
    return True

if __name__ == '__main__':
    success = revert()
    sys.exit(0 if success else 1)
