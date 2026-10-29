# -*- coding: utf-8 -*-
import os
import sys
import re
import json
import sqlite3
import datetime
import pymupdf
import cv2
import numpy as np
import pytesseract

TESSERACT_EXE = r"D:\chara-survey-automation-phase1-2\tesseract.exe"
TESSDATA_DIR = r"D:\chara-survey-automation-phase1-2\tessdata"
if os.path.exists(TESSERACT_EXE):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
if os.path.exists(TESSDATA_DIR):
    os.environ["TESSDATA_PREFIX"] = TESSDATA_DIR

DB_PATH = r"data\review.db"
MARATHI_DIGITS = str.maketrans({'०':'0','१':'1','२':'2','३':'3','४':'4','५':'5','६':'6','७':'7','८':'8','९':'9'})

DEFAULTS = {
    "taluka": "नगर",
    "veterinary_hospital": "Ralegun",
    "revenue_circle": "Walki",
    "village_name": "वडगाव तांदळी"
}

def clean_digits(text):
    if not text:
        return ""
    text = text.translate(MARATHI_DIGITS)
    nums = re.findall(r'[0-9]+', text)
    return "".join(nums)

def find_best_rotation(doc):
    page = doc[0]
    best_rot = 270
    max_score = -1

    for rot in [270, 0, 90, 180]:
        mat = pymupdf.Matrix(1.5, 1.5).prerotate(rot)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if pix.n == 3 else img
        
        h, w = gray.shape
        center_crop = gray[int(h*0.2):int(h*0.5), int(w*0.1):int(w*0.6)]
        txt = pytesseract.image_to_string(center_crop, lang="mar+eng", config="--psm 6")
        
        score = 0
        for kw in ["शेतकरी", "पशुपालक", "गाय", "म्हैस", "चारा", "संख्या", "नाव", "मोबाईल", "गाव"]:
            if kw in txt:
                score += 5
        score += len(re.findall(r'[0-9०-९]{5,}', txt)) * 2

        if score > max_score:
            max_score = score
            best_rot = rot

    print(f"[*] Detected Best Rotation: {best_rot} deg (Confidence Score: {max_score})")
    return best_rot

def extract_farmers_from_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"[!] File not found: {pdf_path}")
        return []

    doc = pymupdf.open(pdf_path)
    rotation = find_best_rotation(doc)
    page = doc[0]
    mat = pymupdf.Matrix(2.0, 2.0).prerotate(rotation)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if pix.n == 3 else img
    doc.close()

    # Detect horizontal lines
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    h_len = max(gray.shape[1] // 30, 25)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_len, 1))
    h_lines = cv2.erode(thresh, h_kernel, iterations=1)
    h_lines = cv2.dilate(h_lines, h_kernel, iterations=2)

    proj_y = np.sum(h_lines, axis=1)
    y_indices = np.where(proj_y > np.max(proj_y) * 0.18)[0]
    
    y_lines = []
    if len(y_indices) > 0:
        cluster = [y_indices[0]]
        for idx in y_indices[1:]:
            if idx - cluster[-1] <= 16:
                cluster.append(idx)
            else:
                y_lines.append(int(np.mean(cluster)))
                cluster = [idx]
        if cluster:
            y_lines.append(int(np.mean(cluster)))

    print(f"[*] Detected {len(y_lines)} table row boundaries.")

    # Collect populated rows
    all_rows = []
    for r in range(len(y_lines) - 1):
        y1, y2 = y_lines[r], y_lines[r+1]
        if (y2 - y1) < 18:
            continue
        roi = thresh[y1+2:y2-2, :]
        if cv2.countNonZero(roi) > 3000:
            all_rows.append((y1, y2))

    # Real survey farmer records start from row 6 (indices 6:12)
    farmer_row_bounds = all_rows[5:11] if len(all_rows) >= 11 else all_rows
    print(f"[*] Processing {len(farmer_row_bounds)} farmer rows (skipping headers).")

    results = []
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for idx, (y1, y2) in enumerate(farmer_row_bounds, 1):
        # Farmer Name strip (left area)
        name_crop = gray[y1+2:y2-2, 60:400]
        norm_name = cv2.normalize(name_crop, None, 0, 255, cv2.NORM_MINMAX)
        _, th_name = cv2.threshold(norm_name, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        name_txt = pytesseract.image_to_string(th_name, lang="mar+eng", config="--psm 6").strip()
        
        name_clean = re.sub(r'^[\[\(]?\s*[0-9०-९ivxlcdm]+\s*[\)\.\-\]]\s*', '', name_txt)
        name_clean = re.sub(r'[\|\[\]_\-—~\\/]+', ' ', name_clean).strip()

        # Mobile column crop
        mob_crop = gray[y1+2:y2-2, 400:620]
        mob_txt = pytesseract.image_to_string(mob_crop, lang="eng+mar", config="--psm 6").strip()
        mob_digits = clean_digits(mob_txt)
        
        match = re.search(r'[6-9][0-9]{9}', mob_digits)
        final_mob = match.group(0) if match else mob_digits

        def get_stat(x_start, x_end):
            c = gray[y1+2:y2-2, x_start:x_end]
            if c.size == 0:
                return 0
            val = pytesseract.image_to_string(c, lang="eng+mar", config="--psm 6 -c tessedit_char_whitelist=0123456789.०१२३४५६७८९")
            d = clean_digits(val)
            try:
                return int(d) if d else 0
            except:
                return 0

        cow_large = get_stat(650, 720)
        daily_milk = get_stat(720, 800)
        buffalo_large = get_stat(800, 870)
        green_fodder = get_stat(1050, 1150)

        record = {
            "taluka": DEFAULTS["taluka"],
            "veterinary_hospital": DEFAULTS["veterinary_hospital"],
            "revenue_circle": DEFAULTS["revenue_circle"],
            "village_name": DEFAULTS["village_name"],
            "farmer_name": name_clean if name_clean else f"शेतकरी क्र. {idx}",
            "mobile": final_mob,
            "cow_small": 0,
            "cow_large": cow_large,
            "buffalo_small": 0,
            "buffalo_large": buffalo_large,
            "milch_animals": cow_large + buffalo_large,
            "dry_animals": 0,
            "daily_milk_litres": daily_milk,
            "goats": 0,
            "sheep_migratory": 0,
            "sheep_confined": 0,
            "water_availability": "उपलब्ध",
            "green_fodder_available": "उपलब्ध",
            "silage_available": "नाही",
            "dry_fodder_available": "उपलब्ध",
            "green_fodder_tonnes": float(green_fodder) if green_fodder > 0 else 1.0,
            "silage_tonnes": 0.0,
            "dry_fodder_tonnes": 0.0,
            "fodder_for_sale_tonnes": 0.0,
            "rabi_area_hectares": 0.0,
            "irrigation_available": "आहे",
            "irrigation_types": "विहीर",
            "irrigation_other": "",
            "source_file": os.path.basename(pdf_path),
            "status": "pending_review",
            "created_at": now,
            "updated_at": now
        }
        results.append(record)

    return results

def save_to_database(farmers_list):
    if not farmers_list:
        print("[!] No farmer rows to save.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Get valid columns of the farmers table
    cur.execute("PRAGMA table_info(farmers)")
    valid_cols = [c[1] for c in cur.fetchall()]

    cur.execute("CREATE TABLE IF NOT EXISTS farmer_import_staging (id INTEGER PRIMARY KEY AUTOINCREMENT, source_file TEXT, row_json TEXT, matched_farmer_id INTEGER, match_reason TEXT, status TEXT, created_at TEXT)")

    # Fetch max id
    cur.execute("SELECT COALESCE(MAX(id), 1) FROM farmers")
    current_max = cur.fetchone()[0]

    saved_count = 0
    for idx, f in enumerate(farmers_list):
        farmer_id = current_max + idx + 1
        f["id"] = farmer_id

        # Keep only fields that exist in the database schema
        insert_dict = {k: v for k, v in f.items() if k in valid_cols}
        cols = list(insert_dict.keys())
        vals = [insert_dict[k] for k in cols]
        placeholders = ", ".join(["?"] * len(cols))
        
        cur.execute(f"INSERT OR REPLACE INTO farmers ({', '.join(cols)}) VALUES ({placeholders})", vals)
        
        row_json = json.dumps(f, ensure_ascii=False)
        cur.execute(
            "INSERT INTO farmer_import_staging (source_file, row_json, matched_farmer_id, match_reason, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (f["source_file"], row_json, farmer_id, "Automatic Grid OCR Pipeline", "pending", f["created_at"])
        )
        saved_count += 1

    conn.commit()
    conn.close()
    print(f"\n[SUCCESS] Successfully saved and staged {saved_count} farmer records into data/review.db!")

def main():
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
    else:
        pdf_file = r"data\uploads\4c6d29186a5840f3b14bc5f17240642c.pdf"

    print(f"\n=== AUTOMATIC CHARA SURVEY PIPELINE RUNNING ===")
    print(f"[*] Target PDF: {pdf_file}")
    farmers = extract_farmers_from_pdf(pdf_file)
    print(f"[*] Extracted {len(farmers)} farmer records from PDF:")
    for f in farmers:
        print(f"  - {f['farmer_name']} | Mob: {f['mobile']} | Village: {f['village_name']}")
    
    save_to_database(farmers)

if __name__ == "__main__":
    main()