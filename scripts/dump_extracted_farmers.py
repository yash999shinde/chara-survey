# -*- coding: utf-8 -*-
import json

with open(r"data\processed\extracted_farmers_270.json", "r", encoding="utf-8") as f:
    records = json.load(f)

print(f"Total Rows Extracted: {len(records)}\n")

for row in records[:6]:
    r_idx = row["row_index"]
    cols = row["columns"]
    print(f"==================== FARMER RECORD ROW {r_idx} ====================")
    for c_key, c_val in cols.items():
        if isinstance(c_val, dict):
            txt = c_val.get("text", "").strip()
            num = c_val.get("numeric", "").strip()
            ink = c_val.get("ink", 0)
            if txt or num or ink > 40:
                print(f"  {c_key:6s} (ink={ink:3d}) | text: '{txt}' | numeric: '{num}'")
    print()