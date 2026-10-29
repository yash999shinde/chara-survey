# -*- coding: utf-8 -*-
import sqlite3
import json
import datetime

DB_PATH = r"data\review.db"
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
source_file = "bhiya_2.pdf"

# 6 verified farmer records directly parsed from Wadgaon Tandali survey sheet
real_farmers = [
    {
        "id": 2,
        "taluka": "नगर",
        "veterinary_hospital": "Ralegun",
        "revenue_circle": "Walki",
        "village_name": "वडगाव तांदळी",
        "farmer_name": "आशिष शब्बीर शेख",
        "mobile": "9096515858",
        "cow_small": 1,
        "cow_large": 0,
        "buffalo_small": 0,
        "buffalo_large": 0,
        "milch_animals": 0,
        "dry_animals": 0,
        "daily_milk_litres": 20,
        "goats": 0,
        "sheep_migratory": 0,
        "sheep_confined": 0,
        "water_availability": "उपलब्ध",
        "green_fodder_available": "उपलब्ध",
        "silage_available": "नाही",
        "dry_fodder_available": "उपलब्ध",
        "green_fodder_tonnes": 1.0,
        "silage_tonnes": 1.0,
        "dry_fodder_tonnes": 1.0,
        "fodder_for_sale_tonnes": 0.0,
        "rabi_area_hectares": 2.0,
        "irrigation_available": "आहे",
        "irrigation_types": "विहीर",
        "irrigation_other": "",
        "source_file": source_file,
        "status": "pending_review",
        "created_at": now,
        "updated_at": now
    },
    {
        "id": 3,
        "taluka": "नगर",
        "veterinary_hospital": "Ralegun",
        "revenue_circle": "Walki",
        "village_name": "वडगाव तांदळी",
        "farmer_name": "समीर जमाल शेख",
        "mobile": "8788250995",
        "cow_small": 0,
        "cow_large": 3,
        "buffalo_small": 0,
        "buffalo_large": 2,
        "milch_animals": 3,
        "dry_animals": 2,
        "daily_milk_litres": 30,
        "goats": 0,
        "sheep_migratory": 0,
        "sheep_confined": 0,
        "water_availability": "उपलब्ध",
        "green_fodder_available": "उपलब्ध",
        "silage_available": "नाही",
        "dry_fodder_available": "उपलब्ध",
        "green_fodder_tonnes": 2.0,
        "silage_tonnes": 0.0,
        "dry_fodder_tonnes": 2.0,
        "fodder_for_sale_tonnes": 0.0,
        "rabi_area_hectares": 0.0,
        "irrigation_available": "आहे",
        "irrigation_types": "विहीर",
        "irrigation_other": "",
        "source_file": source_file,
        "status": "pending_review",
        "created_at": now,
        "updated_at": now
    },
    {
        "id": 4,
        "taluka": "नगर",
        "veterinary_hospital": "Ralegun",
        "revenue_circle": "Walki",
        "village_name": "वडगाव तांदळी",
        "farmer_name": "लतीफ जमाल शेख",
        "mobile": "9284648609",
        "cow_small": 0,
        "cow_large": 2,
        "buffalo_small": 0,
        "buffalo_large": 2,
        "milch_animals": 2,
        "dry_animals": 1,
        "daily_milk_litres": 15,
        "goats": 0,
        "sheep_migratory": 0,
        "sheep_confined": 0,
        "water_availability": "उपलब्ध",
        "green_fodder_available": "उपलब्ध",
        "silage_available": "नाही",
        "dry_fodder_available": "उपलब्ध",
        "green_fodder_tonnes": 1.0,
        "silage_tonnes": 1.0,
        "dry_fodder_tonnes": 0.0,
        "fodder_for_sale_tonnes": 0.0,
        "rabi_area_hectares": 0.0,
        "irrigation_available": "आहे",
        "irrigation_types": "विहीर",
        "irrigation_other": "",
        "source_file": source_file,
        "status": "pending_review",
        "created_at": now,
        "updated_at": now
    },
    {
        "id": 5,
        "taluka": "नगर",
        "veterinary_hospital": "Ralegun",
        "revenue_circle": "Walki",
        "village_name": "वडगाव तांदळी",
        "farmer_name": "इब्राहिम रुबाब शेख",
        "mobile": "7499626207",
        "cow_small": 0,
        "cow_large": 0,
        "buffalo_small": 0,
        "buffalo_large": 2,
        "milch_animals": 0,
        "dry_animals": 2,
        "daily_milk_litres": 10,
        "goats": 0,
        "sheep_migratory": 0,
        "sheep_confined": 0,
        "water_availability": "उपलब्ध",
        "green_fodder_available": "उपलब्ध",
        "silage_available": "नाही",
        "dry_fodder_available": "उपलब्ध",
        "green_fodder_tonnes": 1.0,
        "silage_tonnes": 0.0,
        "dry_fodder_tonnes": 0.0,
        "fodder_for_sale_tonnes": 0.0,
        "rabi_area_hectares": 0.0,
        "irrigation_available": "आहे",
        "irrigation_types": "विहीर",
        "irrigation_other": "",
        "source_file": source_file,
        "status": "pending_review",
        "created_at": now,
        "updated_at": now
    },
    {
        "id": 6,
        "taluka": "नगर",
        "veterinary_hospital": "Ralegun",
        "revenue_circle": "Walki",
        "village_name": "वडगाव तांदळी",
        "farmer_name": "नबाब रुबाब शेख",
        "mobile": "7020021960",
        "cow_small": 0,
        "cow_large": 4,
        "buffalo_small": 0,
        "buffalo_large": 0,
        "milch_animals": 0,
        "dry_animals": 0,
        "daily_milk_litres": 15,
        "goats": 10,
        "sheep_migratory": 0,
        "sheep_confined": 0,
        "water_availability": "उपलब्ध",
        "green_fodder_available": "उपलब्ध",
        "silage_available": "नाही",
        "dry_fodder_available": "उपलब्ध",
        "green_fodder_tonnes": 1.0,
        "silage_tonnes": 1.0,
        "dry_fodder_tonnes": 0.0,
        "fodder_for_sale_tonnes": 0.0,
        "rabi_area_hectares": 0.0,
        "irrigation_available": "आहे",
        "irrigation_types": "विहीर",
        "irrigation_other": "",
        "source_file": source_file,
        "status": "pending_review",
        "created_at": now,
        "updated_at": now
    },
    {
        "id": 7,
        "taluka": "नगर",
        "veterinary_hospital": "Ralegun",
        "revenue_circle": "Walki",
        "village_name": "वडगाव तांदळी",
        "farmer_name": "बशीर कमाल शेख",
        "mobile": "7972218330",
        "cow_small": 0,
        "cow_large": 0,
        "buffalo_small": 0,
        "buffalo_large": 2,
        "milch_animals": 0,
        "dry_animals": 2,
        "daily_milk_litres": 25,
        "goats": 20,
        "sheep_migratory": 0,
        "sheep_confined": 0,
        "water_availability": "उपलब्ध",
        "green_fodder_available": "उपलब्ध",
        "silage_available": "नाही",
        "dry_fodder_available": "उपलब्ध",
        "green_fodder_tonnes": 2.0,
        "silage_tonnes": 2.0,
        "dry_fodder_tonnes": 2.0,
        "fodder_for_sale_tonnes": 0.0,
        "rabi_area_hectares": 0.0,
        "irrigation_available": "आहे",
        "irrigation_types": "विहीर",
        "irrigation_other": "",
        "source_file": source_file,
        "status": "pending_review",
        "created_at": now,
        "updated_at": now
    }
]

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Clean previous unverified records from ID 2 to 7
cur.execute("DELETE FROM farmers WHERE id >= 2")
cur.execute("DELETE FROM farmer_import_staging WHERE source_file = ?", (source_file,))

for f in real_farmers:
    cols = list(f.keys())
    vals = [f[k] for k in cols]
    placeholders = ", ".join(["?"] * len(cols))
    cur.execute(f"INSERT OR REPLACE INTO farmers ({', '.join(cols)}) VALUES ({placeholders})", vals)
    
    row_json = json.dumps(f, ensure_ascii=False)
    cur.execute(
        "INSERT INTO farmer_import_staging (source_file, row_json, matched_farmer_id, match_reason, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (source_file, row_json, f["id"], "Verified PDF Survey Sheet", "pending", now)
    )

conn.commit()

print("=== SUCCESSFULLY IMPORTED ALL 6 FARMERS FOR WADGAON TANDALI ===")
cur.execute("SELECT id, village_name, farmer_name, mobile, cow_large, buffalo_large, daily_milk_litres, status FROM farmers WHERE id >= 2")
for row in cur.fetchall():
    print(f"ID {row[0]}: {row[1]} | {row[2]} | Mob: {row[3]} | Cow: {row[4]} | Buff: {row[5]} | Milk: {row[6]}L | Status: {row[7]}")

conn.close()