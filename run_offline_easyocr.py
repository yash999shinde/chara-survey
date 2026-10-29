import os
import re
import json
import numpy as np
from pathlib import Path
import pymupdf
import easyocr

print("[*] Initializing local Devanagari/Marathi OCR reader (No API needed)...")
# 'mr' = Marathi, 'en' = English
reader = easyocr.Reader(['mr', 'en'], gpu=False)

upload_dir = Path("data/uploads")
pdfs = sorted(upload_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)

if not pdfs:
    print("[!] No PDF found in data/uploads")
    exit(1)

target_pdf = pdfs[0]
print(f"[*] Processing file: {target_pdf.name}")

doc = pymupdf.open(str(target_pdf))
records = []

digit_map = str.maketrans("०१२३४५६७८९", "0123456789")

def clean_num(text):
    text = text.translate(digit_map)
    nums = re.findall(r"\d+(?:\.\d+)?", text)
    return nums[0] if nums else "0"

for page_idx, page in enumerate(doc, 1):
    print(f"[*] Reading Page {page_idx}...")
    pix = page.get_pixmap(dpi=200)
    img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
    if pix.n == 4:
        import cv2
        img_np = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)

    results = reader.readtext(img_np)

    # Line grouping based on vertical Y-coordinate
    rows = {}
    for (bbox, text, prob) in results:
        text = text.strip()
        if not text:
            continue
        # Y center
        y_center = (bbox[0][1] + bbox[2][1]) / 2.0
        line_idx = int(y_center // 40)
        rows.setdefault(line_idx, []).append((bbox[0][0], text))

    for line_idx in sorted(rows.keys()):
        # Sort items horizontally from left to right
        line_items = [t[1] for t in sorted(rows[line_idx], key=lambda x: x[0])]
        row_str = " ".join(line_items)

        # Ignore header/watermark lines
        if any(w in row_str.lower() for w in ["okenscanner", "नाव", "अ.क्र", "पशुपालक", "योजना"]):
            continue

        normalized_row = row_str.translate(digit_map)

        # Extract 10-digit mobile
        mobile_match = re.search(r"[6-9]\d{9}", normalized_row)
        mobile = mobile_match.group(0) if mobile_match else ""

        # Extract Marathi words
        words = row_str.split()
        marathi_words = [w for w in words if len(re.findall(r"[\u0900-\u097F]", w)) >= 2]
        farmer_name = " ".join(marathi_words)

        # Extract remaining numeric figures
        digit_line = normalized_row.replace(mobile, "") if mobile else normalized_row
        nums = re.findall(r"\b\d+(?:\.\d+)?\b", digit_line)

        if not farmer_name and not mobile:
            continue

        records.append({
            "farmer_name": farmer_name if farmer_name else "शेतकरी माहिती",
            "mobile": mobile,
            "cow_small": int(nums[0]) if len(nums) > 0 else 0,
            "cow_large": int(nums[1]) if len(nums) > 1 else 0,
            "buffalo_small": int(nums[2]) if len(nums) > 2 else 0,
            "buffalo_large": int(nums[3]) if len(nums) > 3 else 0,
            "milch_animals": int(nums[4]) if len(nums) > 4 else 0,
            "daily_milk_litres": float(nums[5]) if len(nums) > 5 else 0.0,
            "goats": int(nums[6]) if len(nums) > 6 else 0,
            "green_fodder_tonnes": float(nums[7]) if len(nums) > 7 else 0.0,
            "dry_fodder_tonnes": float(nums[8]) if len(nums) > 8 else 0.0,
            "raw_text": row_str
        })

out_path = Path("data/processed") / f"{target_pdf.stem}_offline_clean.json"
out_path.parent.mkdir(parents=True, exist_ok=True)

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

print(f"\n[+] Extraction Done! Total Records: {len(records)}")
print(f"[+] Output JSON saved at: {out_path}\n")
print(json.dumps(records[:3], ensure_ascii=False, indent=2))