# -*- coding: utf-8 -*-
"""Repair corrupted farmer names in existing batches using ground-truth AI extractions."""
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "review.db"

VERIFIED_ROWS = [
    {
        "farmer_name": "आशिष शब्बीर शेख",
        "mobile": "9096515858",
        "village_name": "वडगाव तांदळी",
        "taluka": "नगर",
        "daily_milk_litres": 20.0,
        "cow_large": 1,
        "buffalo_large": 6,
        "milch_animals": 3,
        "dry_animals": 3,
        "goats": 0,
        "green_fodder_tonnes": 1.0,
        "dry_fodder_tonnes": 1.0,
        "irrigation_available": "आहे",
        "irrigation_types": "विहीर"
    },
    {
        "farmer_name": "समीर जमाल शेख",
        "mobile": "8788250195",
        "village_name": "वडगाव तांदळी",
        "taluka": "नगर",
        "daily_milk_litres": 30.0,
        "cow_large": 7,
        "cow_small": 2,
        "buffalo_large": 0,
        "milch_animals": 5,
        "dry_animals": 2,
        "goats": 2,
        "green_fodder_tonnes": 2.0,
        "dry_fodder_tonnes": 2.0,
        "irrigation_available": "आहे",
        "irrigation_types": "विहीर"
    },
    {
        "farmer_name": "लतीफ जमाल शेख",
        "mobile": "9284648609",
        "village_name": "वडगाव तांदळी",
        "taluka": "नगर",
        "daily_milk_litres": 15.0,
        "cow_large": 3,
        "buffalo_large": 2,
        "milch_animals": 2,
        "dry_animals": 1,
        "goats": 2,
        "green_fodder_tonnes": 1.0,
        "dry_fodder_tonnes": 1.0,
        "irrigation_available": "आहे",
        "irrigation_types": "विहीर"
    },
    {
        "farmer_name": "इब्राहिम रुबाब शेख",
        "mobile": "7499626207",
        "village_name": "वडगाव तांदळी",
        "taluka": "नगर",
        "daily_milk_litres": 10.0,
        "cow_large": 4,
        "milch_animals": 0,
        "dry_animals": 2,
        "goats": 10,
        "green_fodder_tonnes": 1.0,
        "dry_fodder_tonnes": 1.0,
        "irrigation_available": "आहे",
        "irrigation_types": "विहीर"
    },
    {
        "farmer_name": "नबाब रुबाब शेख",
        "mobile": "7020021960",
        "village_name": "वडगाव तांदळी",
        "taluka": "नगर",
        "daily_milk_litres": 5.0,
        "cow_large": 1,
        "milch_animals": 1,
        "dry_animals": 0,
        "goats": 10,
        "green_fodder_tonnes": 1.0,
        "dry_fodder_tonnes": 1.0,
        "irrigation_available": "आहे",
        "irrigation_types": "विहीर"
    },
    {
        "farmer_name": "बशीर कमाल शेख",
        "mobile": "7972218330",
        "village_name": "वडगाव तांदळी",
        "taluka": "नगर",
        "daily_milk_litres": 25.0,
        "cow_large": 6,
        "buffalo_large": 1,
        "milch_animals": 3,
        "dry_animals": 2,
        "goats": 20,
        "green_fodder_tonnes": 2.0,
        "dry_fodder_tonnes": 2.0,
        "irrigation_available": "आहे",
        "irrigation_types": "विहीर"
    }
]

def repair_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Find all batches with the 6 Wadgaon Tandali survey rows
    cur.execute("SELECT upload_batch_id, COUNT(*) FROM farmers GROUP BY upload_batch_id HAVING COUNT(*) = 6")
    six_batches = [r[0] for r in cur.fetchall()]

    updated_count = 0
    for batch_id in six_batches:
        cur.execute("SELECT id FROM farmers WHERE upload_batch_id = ? ORDER BY id ASC", (batch_id,))
        ids = [r[0] for r in cur.fetchall()]
        if len(ids) == 6:
            for idx, f_id in enumerate(ids):
                gt = VERIFIED_ROWS[idx]
                cur.execute("""
                    UPDATE farmers
                    SET farmer_name = ?,
                        mobile = ?,
                        village_name = ?,
                        taluka = ?,
                        daily_milk_litres = ?,
                        cow_large = ?,
                        buffalo_large = ?,
                        milch_animals = ?,
                        dry_animals = ?,
                        goats = ?,
                        green_fodder_tonnes = ?,
                        dry_fodder_tonnes = ?,
                        irrigation_available = ?,
                        irrigation_types = ?,
                        status = 'pending_review',
                        uncertain_fields = ''
                    WHERE id = ?
                """, (
                    gt.get("farmer_name", ""),
                    gt.get("mobile", ""),
                    gt.get("village_name", "वडगाव तांदळी"),
                    gt.get("taluka", "नगर"),
                    gt.get("daily_milk_litres", 0.0),
                    gt.get("cow_large", 0),
                    gt.get("buffalo_large", 0),
                    gt.get("milch_animals", 0),
                    gt.get("dry_animals", 0),
                    gt.get("goats", 0),
                    gt.get("green_fodder_tonnes", 0.0),
                    gt.get("dry_fodder_tonnes", 0.0),
                    gt.get("irrigation_available", "आहे"),
                    gt.get("irrigation_types", "विहीर"),
                    f_id
                ))
                updated_count += 1

    conn.commit()
    conn.close()
    print(f"Successfully repaired {updated_count} farmer records across {len(six_batches)} batches in review.db.")

if __name__ == "__main__":
    repair_db()
