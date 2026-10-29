# -*- coding: utf-8 -*-
import os
import json
import re
import cv2
import numpy as np
import pymupdf
import pytesseract
from PIL import Image

TESSERACT_EXE = r"D:\chara-survey-automation-phase1-2\tesseract.exe"
TESSDATA_DIR = r"D:\chara-survey-automation-phase1-2\tessdata"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
os.environ["TESSDATA_PREFIX"] = TESSDATA_DIR

PDF_PATH = r"data\uploads\4c6d29186a5840f3b14bc5f17240642c.pdf"
GRID_JSON = r"data\processed\detected_grid_structure_270.json"
MARATHI_DIGITS = str.maketrans({'०':'0','१':'1','२':'2','३':'3','४':'4','५':'5','६':'6','७':'7','८':'8','९':'9'})

doc = pymupdf.open(PDF_PATH)
page = doc[0]
mat = pymupdf.Matrix(2.0, 2.0).prerotate(270)
pix = page.get_pixmap(matrix=mat, alpha=False)
img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if pix.n == 3 else img
doc.close()

with open(GRID_JSON, "r", encoding="utf-8") as f:
    grid = json.load(f)

# Real farmer rows are Row 6 to Row 11
farmer_rows = [r for r in grid if 6 <= r["row_index"] <= 11]

print("=== 6 REAL FARMER RECORDS (EXTRACTED) ===\n")

extracted_farmers = []

for idx, r in enumerate(farmer_rows, 1):
    r_idx = r["row_index"]
    cells = {c["col_index"]: c for c in r["cells"]}
    
    col1 = cells.get(1)
    name_text = ""
    mobile_text = ""
    raw_text = ""
    
    if col1:
        x1, y1, x2, y2 = col1["bbox"]
        c_crop = gray[y1+2:y2-2, x1+2:x2-2]
        
        raw_text = pytesseract.image_to_string(c_crop, lang="mar+eng", config="--psm 6").strip()
        
        digits_found = re.findall(r'[0-9०-९]{8,11}', raw_text)
        if digits_found:
            mobile_text = digits_found[0].translate(MARATHI_DIGITS)
        
        name_clean = re.sub(r'[0-9०-९\-_|\\/()\[\]]', '', raw_text).strip()
        name_text = name_clean if name_clean else raw_text
    
    def get_num(c_idx):
        cell = cells.get(c_idx)
        if not cell or cell["ink_pixels"] < 35:
            return ""
        x1, y1, x2, y2 = cell["bbox"]
        crop = gray[y1+2:y2-2, x1+2:x2-2]
        h, w = crop.shape
        if h < 30 or w < 30:
            crop = cv2.resize(crop, (max(w*2, 30), max(h*2, 30)), interpolation=cv2.INTER_CUBIC)
        norm = cv2.normalize(crop, None, 0, 255, cv2.NORM_MINMAX)
        _, thresh = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        t = pytesseract.image_to_string(thresh, lang="eng+mar", config="--psm 6 -c tessedit_char_whitelist=0123456789.०१२३४५६७८९")
        t = t.translate(MARATHI_DIGITS).strip()
        return re.sub(r'[^0-9.]', '', t)

    record = {
        "farmer_no": idx,
        "grid_row": r_idx,
        "raw_col1": raw_text,
        "extracted_name": name_text,
        "extracted_mobile": mobile_text,
        "col_8": get_num(8),
        "col_9": get_num(9),
        "col_10": get_num(10),
        "col_13": get_num(13),
        "col_14": get_num(14),
        "default_taluka": "नगर",
        "default_vet_hospital": "Ralegun",
        "default_revenue_circle": "Walki"
    }
    extracted_farmers.append(record)
    
    print(f"Farmer #{idx} (Grid Row {r_idx}):")
    print(f"  Raw Col 1    : '{record['raw_col1']}'")
    print(f"  Farmer Name  : '{record['extracted_name']}'")
    print(f"  Mobile No    : '{record['extracted_mobile']}'")
    print(f"  Col 8, 9, 10 : [{record['col_8']}], [{record['col_9']}], [{record['col_10']}]")
    print(f"  Col 13, 14   : [{record['col_13']}], [{record['col_14']}]")
    print("-" * 50)

with open(r"data\processed\preview_six_farmers.json", "w", encoding="utf-8") as f:
    json.dump(extracted_farmers, f, ensure_ascii=False, indent=2)

print("\n[+] Saved parsed farmers to: data\\processed\\preview_six_farmers.json")