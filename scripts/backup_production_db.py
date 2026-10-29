# -*- coding: utf-8 -*-
"""Timestamped Database Backup and Verification Script."""
import shutil
import sqlite3
import datetime
from pathlib import Path

BASE_DIR = Path(r"D:\chara-survey-automation-phase1-2\chara-survey-automation")
DB_PATH = BASE_DIR / "data" / "review.db"
TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_PATH = BASE_DIR / "data" / f"review_backup_master_{TIMESTAMP}.db"

print(f"Backing up {DB_PATH} to {BACKUP_PATH}...")
shutil.copy2(DB_PATH, BACKUP_PATH)

if not BACKUP_PATH.exists():
    raise RuntimeError(f"Backup file was not created: {BACKUP_PATH}")

size_bytes = BACKUP_PATH.stat().st_size
print(f"Verified backup file exists: {BACKUP_PATH} ({size_bytes} bytes)")

conn = sqlite3.connect(str(BACKUP_PATH))
cur = conn.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f"Tables in backup ({len(tables)}): {tables}")
for t in tables:
    count = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  - Table '{t}': {count} rows")

cur.execute("PRAGMA foreign_key_check")
fk_errors = cur.fetchall()
print(f"Foreign key check errors: {len(fk_errors)}")

conn.close()
print("Backup and verification complete successfully.")
