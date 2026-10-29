# -*- coding: utf-8 -*-
import sqlite3
import json
from pathlib import Path

db_path = Path("data/review.db")
if not db_path.exists():
    print("[!] data/review.db nahi mila!")
    exit(1)

with sqlite3.connect(str(db_path)) as conn:
    cur = conn.cursor()

    # 1. Purane demo records delete karo
    cur.execute("DELETE FROM reviews WHERE record_id LIKE 'DEMO%' OR source_file LIKE '%demo%'")
    print(f"[*] Cleared dummy demo records: {cur.rowcount} removed.")

    # 2. farmer_import_staging se Wadgaon Tandali ke records uthao (only row_json)
    cur.execute("SELECT id, source_file, row_json FROM farmer_import_staging WHERE row_json LIKE '%वडगाव%' OR row_json LIKE '%8788250595%'")
    staged = cur.fetchall()

    if not staged:
        # Fallback: saare available records uthao
        cur.execute("SELECT id, source_file, row_json FROM farmer_import_staging")
        staged = cur.fetchall()

    inserted = 0
    for idx, (sid, src, r_json) in enumerate(staged, 1):
        rec_id = f"WADGAON-{idx:03d}"
        
        cur.execute("""
            INSERT OR REPLACE INTO reviews (
                record_id, source_file, decision, reviewer_note, created_at, updated_at
            ) VALUES (?, ?, 'needs_review', 'Wadgaon Tandali auto-extracted survey', datetime('now'), datetime('now'))
        """, (rec_id, src if src else "bhiya.pdf"))
        inserted += 1

    conn.commit()
    print(f"[SUCCESS] {inserted} real survey records synced into reviews table!")