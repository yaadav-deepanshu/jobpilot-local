"""
Rollback script: Revert company portals in config.yaml back to 150 baseline
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def revert():
    backup = ROOT / 'config.yaml.backup_150'
    target = ROOT / 'config.yaml'
    if backup.exists():
        shutil.copy2(backup, target)
        print(f"✓ Successfully restored {target} from {backup}")
    else:
        print(f"✗ Backup file {backup} not found!")

if __name__ == '__main__':
    revert()
