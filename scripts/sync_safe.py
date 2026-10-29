# -*- coding: utf-8 -*-
import sqlite3
import json
from pathlib import Path
from datetime import datetime

db_path = Path("data/review.db")
with sqlite3.connect(str(db_path)) as conn:
    cur = conn.cursor()

    # 1. Purane mock demo records delete karein
    cur.execute("DELETE FROM reviews WHERE record_id LIKE 'DEMO%' OR source_file LIKE '%demo%'")
    print(f"[*] Cleared dummy records: {cur.rowcount}")

    # 2. farmer_import_staging se saare real records uthayein
    cur.execute("SELECT id, source_file, row_json, status FROM farmer_import_staging")
    staged = cur.fetchall()

    inserted = 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for idx, (sid, src, r_json, stat) in enumerate(staged, 1):
        rec_id = f"WADGAON-{idx:03d}"
        
        # Ensure record_json is valid JSON string
        json_data = r_json if r_json else "{}"
        
        cur.execute("""
            INSERT OR REPLACE INTO reviews (
                source_file,
                record_id,
                record_json,
                original_status,
                decision,
                reviewer_note,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            src if src else "bhiya.pdf",
            rec_id,
            json_data,
            stat if stat else "needs_review",
            "needs_review",
            "Wadgaon Tandali auto-extracted record",
            now_str
        ))
        inserted += 1

    conn.commit()
    print(f"[SUCCESS] {inserted} actual farmer records synced into reviews table!")