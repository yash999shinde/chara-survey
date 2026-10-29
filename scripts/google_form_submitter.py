# -*- coding: utf-8 -*-
"""
Google Form Automation Helper
Database se verified records read karke Google Form structure me payload banata hai.
"""
import sqlite3
import json
import urllib.parse
from pathlib import Path

DB_PATH = Path("data/review.db")

def generate_google_form_links():
    # Example: Replace with your actual Google Form Action URL & entry IDs
    FORM_BASE_URL = "https://docs.google.com/forms/d/e/YOUR_FORM_ID/formResponse"
    
    # Entry ID map (Google Form me Inspect Element karke entry.xxxxxxx ID replace karein)
    ENTRY_MAP = {
        "taluka": "entry.1000001",
        "village_name": "entry.1000002",
        "farmer_name": "entry.1000003",
        "mobile": "entry.1000004",
        "milch_animals": "entry.1000005",
        "daily_milk_litres": "entry.1000006"
    }

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT id, row_json FROM farmer_import_staging WHERE status='verified'").fetchall()
    
    print(f"[*] Verified records found for Google Form submission: {len(rows)}")

    for r in rows:
        data = json.loads(r["row_json"])
        params = {}
        for k, entry_id in ENTRY_MAP.items():
            if k in data and data[k]:
                params[entry_id] = str(data[k])
        
        prefilled_url = FORM_BASE_URL.replace("formResponse", "viewform") + "?" + urllib.parse.urlencode(params)
        print(f"\n[Farmer #{r['id']} - {data.get('farmer_name')}]:")
        print(f"    Prefilled URL: {prefilled_url[:120]}...")

    con.close()

if __name__ == "__main__":
    generate_google_form_links()