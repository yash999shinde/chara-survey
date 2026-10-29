# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect(r"data\review.db")
cur = conn.cursor()

print("=== STAGING TABLE COLUMNS ===")
cur.execute("PRAGMA table_info(farmer_import_staging);")
staging_cols = [c[1] for c in cur.fetchall()]
print("farmer_import_staging:", staging_cols)

print("\n=== CURRENT ROWS IN FARMERS ===")
cur.execute("SELECT id, farmer_name, mobile, status FROM farmers LIMIT 5;")
print(cur.fetchall())

print("\n=== CURRENT ROWS IN STAGING ===")
cur.execute("SELECT * FROM farmer_import_staging LIMIT 5;")
print(cur.fetchall())
conn.close()