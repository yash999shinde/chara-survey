# -*- coding: utf-8 -*-
import os
import re
import json
import sqlite3
import pymupdf
import cv2
import numpy as np
import pytesseract
from PIL import Image

TESSERACT_EXE = r"D:\chara-survey-automation-phase1-2\tesseract.exe"
TESSDATA_DIR = r"D:\chara-survey-automation-phase1-2\tessdata"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
os.environ["TESSDATA_PREFIX"] = TESSDATA_DIR

PDF_PATH = r"data\uploads\4c6d29186a5840f3b14bc5f17240642c.pdf"
GRID_JSON = r"data\processed\detected_grid_structure_270.json"
DB_PATH = r"data\review.db"

MARATHI_DIGITS = str.maketrans({'०':'0','१':'1','२':'2','३':'3','४':'4','५':'5','६':'6','७':'7','८':'8','९':'9'})

def clean_digits(val):
    if not val:
        return ""
    val = val.translate(MARATHI_DIGITS)
    nums = re.findall(r'[0-9]+', val)
    return "".join(nums)

def clean_name(raw):
    # Remove leading index numbers like '1)', '2.', '[3)'
    name = re.sub(r'^[\[\(]?\s*[0-9०-९ivxlcdm]+\s*[\)\.\-\]]\s*', '', raw)
    # Remove grid borders and punctuation artifacts
    name = re.sub(r'[\|\[\]_\-—~\\/]+', ' ', name)
    return name.strip()

def extract_mobile(raw_col1):
    cleaned = clean_digits(raw_col1)
    # If starting with known OCR error for 8/9/7
    if len(cleaned) == 9 and cleaned[0] in '789':
        # Flag as incomplete 9-digit
        return cleaned
    if len(cleaned) >= 10:
        # Take valid 10-digit candidate starting with 6-9
        for m in re.finditer(r'[6-9][0-9]{9}', cleaned):
            return m.group(0)
    return cleaned

def run_staging():
    doc = pymupdf.open(PDF_PATH)
    page = doc[0]
    mat = pymupdf.Matrix(2.0, 2.0).prerotate(270)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if pix.n == 3 else img
    doc.close()

    with open(GRID_JSON, "r", encoding="utf-8") as f:
        grid = json.load(f)

    farmer_rows = [r for r in grid if 6 <= r["row_index"] <= 11]
    col1_x1 = farmer_rows[0]["cells"][1]["bbox"][0]

    staged_records = []

    print("\n=== EXTRACTING AND REFINING 6 REAL FARMERS ===")
    for idx, r in enumerate(farmer_rows, 1):
        y1, y2 = r["y_range"]
        cells = {c["col_index"]: c for c in r["cells"]}

        # 1. Left Name Strip
        left_crop = gray[y1+2:y2-2, 60:col1_x1]
        norm = cv2.normalize(left_crop, None, 0, 255, cv2.NORM_MINMAX)
        _, thresh = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        raw_name = pytesseract.image_to_string(thresh, lang="mar+eng", config="--psm 6").strip()
        farmer_name = clean_name(raw_name)

        # 2. Mobile Column
        col1 = cells.get(1)
        raw_mob = ""
        if col1:
            cx1, cy1, cx2, cy2 = col1["bbox"]
            m_crop = gray[cy1+2:cy2-2, cx1+2:cx2-2]
            raw_mob = pytesseract.image_to_string(m_crop, lang="eng+mar", config="--psm 6").strip()
        mobile_no = extract_mobile(raw_mob)

        # 3. Quantities
        def get_int_cell(c_idx):
            cell = cells.get(c_idx)
            if not cell or cell["ink_pixels"] < 35:
                return 0
            x1, y1_c, x2, y2_c = cell["bbox"]
            crop = gray[y1_c+2:y2_c-2, x1+2:x2-2]
            h, w = crop.shape
            if h < 30 or w < 30:
                crop = cv2.resize(crop, (max(w*2, 30), max(h*2, 30)), interpolation=cv2.INTER_CUBIC)
            norm = cv2.normalize(crop, None, 0, 255, cv2.NORM_MINMAX)
            _, th = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            t = pytesseract.image_to_string(th, lang="eng+mar", config="--psm 6 -c tessedit_char_whitelist=0123456789.०१२३४५६७८९")
            d = clean_digits(t)
            try:
                return int(d) if d else 0
            except:
                return 0

        cattle = get_int_cell(8)
        daily_milk = get_int_cell(9)
        buffalo = get_int_cell(10)
        fodder = get_int_cell(13)

        # Flag for human review if mobile is not exactly 10 digits or name is short
        needs_review = False
        review_reasons = []

        if not re.match(r'^[6-9][0-9]{9}$', mobile_no):
            needs_review = True
            review_reasons.append("Invalid or partial mobile number")
        if len(farmer_name) < 3:
            needs_review = True
            review_reasons.append("Unclear farmer name")

        rec = {
            "record_id": f"SRV-2026-{idx:03d}",
            "sr_no": idx,
            "village_name": "वाळकी",
            "farmer_name": farmer_name,
            "mobile_number": mobile_no,
            "taluka": "नगर",
            "veterinary_hospital": "Ralegun",
            "revenue_circle": "Walki",
            "cattle_count": cattle,
            "buffalo_count": buffalo,
            "daily_milk_litres": daily_milk,
            "green_fodder_tonnes": fodder,
            "silage_tonnes": 0,
            "dry_fodder_tonnes": 0,
            "water_availability": "उपलब्ध",
            "irrigation_availability": "आहे",
            "status": "pending_review",
            "review_reasons": "; ".join(review_reasons)
        }
        staged_records.append(rec)
        print(f"Record #{idx} [{rec['record_id']}]:")
        print(f"  Farmer  : {rec['farmer_name']}")
        print(f"  Mobile  : {rec['mobile_number']} {'[FLAGGED FOR REVIEW]' if needs_review else '[OK]'}")
        print(f"  Cattle  : {rec['cattle_count']}, Buffalo: {rec['buffalo_count']}, Milk: {rec['daily_milk_litres']}")
        print(f"  Reasons : {rec['review_reasons'] if needs_review else 'Clean'}")
        print("-" * 50)

    # 4. Save to JSON and SQLite Database
    with open(r"data\processed\staged_farmers.json", "w", encoding="utf-8") as f:
        json.dump(staged_records, f, ensure_ascii=False, indent=2)

    # Inspect SQLite review.db schema and update
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cur.fetchall()]
    print(f"\n[+] Existing SQLite tables in review.db: {tables}")

    target_table = "farmers" if "farmers" in tables else ("staging_farmers" if "staging_farmers" in tables else tables[0])
    cur.execute(f"PRAGMA table_info({target_table})")
    cols = [c[1] for c in cur.fetchall()]
    print(f"[+] Table '{target_table}' columns: {cols}")

    # Insert/replace records safely
    for rec in staged_records:
        valid_keys = [k for k in rec.keys() if k in cols]
        placeholders = ", ".join(["?"] * len(valid_keys))
        col_names = ", ".join(valid_keys)
        values = [rec[k] for k in valid_keys]
        
        query = f"INSERT OR REPLACE INTO {target_table} ({col_names}) VALUES ({placeholders})"
        cur.execute(query, values)

    conn.commit()
    conn.close()
    print(f"\n[SUCCESS] 6 real survey farmers successfully staged into '{target_table}' in data/review.db!")

if __name__ == "__main__":
    run_staging()