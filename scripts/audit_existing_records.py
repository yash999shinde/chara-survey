# -*- coding: utf-8 -*-
"""Complete Audit of 91 existing records in review.db with UTF-8 file logging."""
import sqlite3
import json
from pathlib import Path
from collections import Counter

DB_PATH = Path(r"D:\chara-survey-automation-phase1-2\chara-survey-automation\data\review.db")
OUT_FILE = Path(r"D:\chara-survey-automation-phase1-2\chara-survey-automation\data\processed\database_audit_report.txt")

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

rows = [dict(r) for r in cur.execute("SELECT * FROM farmers ORDER BY id ASC").fetchall()]

with open(OUT_FILE, "w", encoding="utf-8") as out:
    out.write(f"TOTAL FARMERS IN DB: {len(rows)}\n\n")

    # 1. Source file distribution
    source_files = Counter(r["source_file"] for r in rows)
    out.write("--- 1. DISTRIBUTION BY SOURCE FILE ---\n")
    for sf, cnt in source_files.most_common():
        sample = [r for r in rows if r["source_file"] == sf][0]
        out.write(f"  {sf or '[EMPTY]'}: {cnt} records | Batch: {sample['upload_batch_id']} | Created: {sample['created_at']}\n")

    # 2. Batch distribution
    batches = Counter(r["upload_batch_id"] for r in rows)
    out.write("\n--- 2. DISTRIBUTION BY UPLOAD BATCH ---\n")
    for b, cnt in batches.most_common():
        sample = [r for r in rows if r["upload_batch_id"] == b][0]
        out.write(f"  {b or '[EMPTY]'}: {cnt} records | Source: {sample['source_file']}\n")

    # 3. Status distribution
    statuses = Counter(r["status"] for r in rows)
    out.write("\n--- 3. STATUS DISTRIBUTION ---\n")
    for s, cnt in statuses.most_common():
        out.write(f"  {s}: {cnt} records\n")

    # 4. Duplicate distribution
    dup_rows = [r for r in rows if r["is_duplicate"] == 1]
    out.write(f"\n--- 4. DUPLICATE RECORDS ({len(dup_rows)}) ---\n")
    dup_reasons = Counter(r["duplicate_reason"] for r in dup_rows)
    for reason, cnt in dup_reasons.most_common(10):
        out.write(f"  - Count: {cnt} | Reason: {reason}\n")

    # 5. Mobile number duplicates
    mobiles = [r["mobile"] for r in rows if r["mobile"] and len(r["mobile"]) == 10]
    mobile_counts = Counter(mobiles)
    out.write("\n--- 5. FARMER MOBILE CLUSTERING ---\n")
    for mob, cnt in mobile_counts.most_common():
        if cnt > 1:
            cluster_farmers = [(r["id"], r["farmer_name"], r["source_file"], r["upload_batch_id"]) for r in rows if r["mobile"] == mob]
            out.write(f"  Mobile {mob}: appears {cnt} times across files:\n")
            for fid, fname, fs, fb in cluster_farmers:
                out.write(f"    - ID #{fid}: {fname} (File: {fs[:30]}..., Batch: {fb[:30]}...)\n")

    # 6. Sample of first 15 records
    out.write("\n--- 6. SAMPLE OF FIRST 15 RECORDS (IDs 1-15) ---\n")
    for r in rows[:15]:
        out.write(f"  ID #{r['id']}: {r['farmer_name']} | Mob: {r['mobile']} | Village: {r['village_name']} | File: {r['source_file']} | Status: {r['status']}\n")

    # 7. Sample of latest 15 records
    out.write("\n--- 7. SAMPLE OF LATEST 15 RECORDS ---\n")
    for r in rows[-15:]:
        out.write(f"  ID #{r['id']}: {r['farmer_name']} | Mob: {r['mobile']} | Village: {r['village_name']} | File: {r['source_file']} | Status: {r['status']} | Dup: {r['is_duplicate']}\n")

conn.close()
print("Audit complete! Saved to database_audit_report.txt")
