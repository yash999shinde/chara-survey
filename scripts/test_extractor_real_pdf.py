# -*- coding: utf-8 -*-
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.extractor import extract_document

pdf_path = PROJECT_ROOT / "data" / "uploads" / "4c6d29186a5840f3b14bc5f17240642c.pdf"

res = extract_document(pdf_path)
records = res.get("records", [])

output_path = PROJECT_ROOT / "data" / "processed" / "real_pdf_extraction_results.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

# Write human-readable comparison report with UTF-8 encoding
report_path = PROJECT_ROOT / "data" / "processed" / "extraction_report.txt"
with open(report_path, "w", encoding="utf-8") as rf:
    rf.write(f"EXTRACTED {len(records)} RECORDS FROM {pdf_path.name}:\n\n")
    for i, r in enumerate(records, 1):
        rf.write(f"--- ROW {i} ---\n")
        rf.write(f"  Farmer Name      : {r['farmer_name']}\n")
        rf.write(f"  Mobile           : {r['mobile']}\n")
        rf.write(f"  Cow (L/S)        : {r['cow_large']} / {r['cow_small']}\n")
        rf.write(f"  Buffalo (L/S)    : {r['buffalo_large']} / {r['buffalo_small']}\n")
        rf.write(f"  Milch / Dry      : {r['milch_animals']} / {r['dry_animals']}\n")
        rf.write(f"  Milk (L/day)     : {r['daily_milk_litres']}\n")
        rf.write(f"  Goats            : {r['goats']}\n")
        rf.write(f"  Fodder (Gr/Sil/Dr): {r['green_fodder_tonnes']} / {r['silage_tonnes']} / {r['dry_fodder_tonnes']}\n")
        rf.write(f"  Irrigation       : {r['irrigation_types']}\n")
        rf.write(f"  Status           : {r['status']}\n")
        rf.write(f"  Uncertain Fields : {r['uncertain_fields']}\n")
        rf.write(f"  Review Notes     : {r['review_notes']}\n")
        rf.write(f"  Raw OCR Text     : {r['raw_ocr_text']}\n\n")

print(f"SUCCESS: Extracted {len(records)} records. Saved report to {report_path}")
