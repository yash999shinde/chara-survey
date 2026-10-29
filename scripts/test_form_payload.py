# -*- coding: utf-8 -*-
import sqlite3
import json

con = sqlite3.connect("data/review.db")
con.row_factory = sqlite3.Row
cur = con.cursor()

# Get latest record
cur.execute("SELECT id, row_json FROM farmer_import_staging ORDER BY id DESC LIMIT 1")
row = cur.fetchone()

if row:
    print("[*] Staged ID:", row["id"])
    data = json.loads(row["row_json"])
    print("[+] Ready for Google Form entry:")
    print(f"    - Village: {data.get('village_name')}")
    print(f"    - Farmer: {data.get('farmer_name')}")
    print(f"    - Mobile: {data.get('mobile')}")
    print(f"    - Cow: {data.get('cow_small')}, Buffalo: {data.get('buffalo_small')}")
    print(f"    - Milk: {data.get('daily_milk_litres')} Litres")
con.close()