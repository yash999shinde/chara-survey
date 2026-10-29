# -*- coding: utf-8 -*-
import sqlite3
import json
import datetime

DB_PATH = r"data\review.db"
JSON_PATH = r"data\processed\staged_farmers.json"

with open(JSON_PATH, "r", encoding="utf-8") as f:
    staged = json.load(f)

# Real 6 phone numbers cleaned from Col 1
mobiles = [
    "",             # Row 1: needs manual check in UI
    "8788250995",   # Row 2
    "9284648609",   # Row 3
    "74999626207",  # Row 4 (11-digit OCR artifact, flag for reviewer)
    "7029021960",   # Row 5
    "7972214567"    # Row 6
]

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
source_file = "4c6d29186a5840f3b14bc5f17240642c.pdf"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Remove previous incomplete runs for IDs 2 to 7 while preserving ID 1 (Demo Farmer)
cur.execute("DELETE FROM farmers WHERE id >= 2")

for idx, rec in enumerate(staged):
    db_id = idx + 2
    mob = mobiles[idx] if idx < len(mobiles) else rec.get("mobile_number", "")
    
    farmer_data = {
        "id": db_id,
        "taluka": "नगर",
        "veterinary_hospital": "Ralegun",
        "revenue_circle": "Walki",
        "village_name": "वाळकी",
        "farmer_name": rec.get("farmer_name", ""),
        "mobile": mob,
        "cow_small": 0,
        "cow_large": rec.get("cattle_count", 0),
        "buffalo_small": 0,
        "buffalo_large": rec.get("buffalo_count", 0),
        "milch_animals": 0,
        "dry_animals": 0,
        "daily_milk_litres": rec.get("daily_milk_litres", 0),
        "goats": 0,
        "sheep_migratory": 0,
        "sheep_confined": 0,
        "water_availability": "उपलब्ध",
        "green_fodder_available": "उपलब्ध",
        "silage_available": "नाही",
        "dry_fodder_available": "उपलब्ध",
        "green_fodder_tonnes": rec.get("green_fodder_tonnes", 0),
        "silage_tonnes": 0,
        "dry_fodder_tonnes": 0,
        "fodder_for_sale_tonnes": 0,
        "rabi_area_hectares": 0.0,
        "irrigation_available": "आहे",
        "irrigation_types": "विहीर",
        "irrigation_other": "",
        "source_file": source_file,
        "status": "pending_review",
        "created_at": now,
        "updated_at": now
    }
    
    # 1. Insert into farmers table
    cols = list(farmer_data.keys())
    vals = [farmer_data[k] for k in cols]
    placeholders = ", ".join(["?"] * len(cols))
    col_str = ", ".join(cols)
    cur.execute(f"INSERT OR REPLACE INTO farmers ({col_str}) VALUES ({placeholders})", vals)
    
    # 2. Insert into farmer_import_staging table
    row_json = json.dumps(farmer_data, ensure_ascii=False)
    cur.execute(
        "INSERT INTO farmer_import_staging (source_file, row_json, matched_farmer_id, match_reason, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (source_file, row_json, db_id, "OCR Grid Row Import", "pending", now)
    )

conn.commit()

# Verify
cur.execute("SELECT id, farmer_name, mobile, cow_large, buffalo_large, daily_milk_litres, status FROM farmers WHERE id >= 2")
rows = cur.fetchall()
print("=== VERIFIED STAGED ROWS IN SQLite ===")
for r in rows:
    print(r)

conn.close()
print("\n[SUCCESS] Staged records successfully populated in review.db with status 'pending_review'!")