# -*- coding: utf-8 -*-
import pymupdf
import cv2
import numpy as np
import pytesseract
from pathlib import Path
import json

BASE_DIR = Path(r"D:\chara-survey-automation-phase1-2\chara-survey-automation")
PDF_PATH = BASE_DIR / "data" / "uploads" / "4c6d29186a5840f3b14bc5f17240642c.pdf"

TESSERACT_EXE = r"D:\chara-survey-automation-phase1-2\tesseract.exe"
TESSDATA_DIR = r"D:\chara-survey-automation-phase1-2\tessdata"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE

doc = pymupdf.open(str(PDF_PATH))
page = doc[0]
mat = pymupdf.Matrix(2.0, 2.0).prerotate(270)
pix = page.get_pixmap(matrix=mat, alpha=False)
img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if pix.n == 3 else img
doc.close()

# Let's inspect the top header text across the table (Y from 50 to 280)
header_crop = gray[50:280, :]
header_txt = pytesseract.image_to_string(header_crop, lang="mar+eng", config="--psm 6")
(BASE_DIR / "data" / "processed" / "header_ocr.txt").write_text(header_txt, encoding="utf-8")

# Now let's crop horizontal strips for the 6 data rows:
# Rows 6 to 11 are between Y=281 and Y=500
# Let's check each data row from Y=281 to Y=500
row_ys = [
    (281, 317), # Row 1
    (317, 353), # Row 2
    (353, 389), # Row 3
    (389, 425), # Row 4
    (425, 461), # Row 5
    (461, 497), # Row 6
]

print("\n=== DATA ROWS OCR ===")
rows_data = []
for idx, (y1, y2) in enumerate(row_ys, 1):
    row_img = gray[y1:y2, :]
    
    # 1. Serial No & Farmer Name: X=60 to 395
    name_crop = gray[y1:y2, 60:395]
    name_txt = pytesseract.image_to_string(name_crop, lang="mar+eng", config="--psm 6").strip()
    
    # 2. Mobile Number: X=395 to 611
    mob_crop = gray[y1:y2, 395:611]
    mob_txt = pytesseract.image_to_string(mob_crop, lang="mar+eng", config="--psm 6").strip()
    
    # 3. Rest of columns:
    # Let's take horizontal slices
    # Let's check each segment:
    # x: 611-653 (Cow large?)
    # x: 653-697 (Cow small?)
    # x: 697-741 (Buffalo large?)
    # x: 741-781 (Buffalo small?)
    # x: 781-817 (Milch?)
    # x: 817-858 (Dry?)
    # x: 858-911 (Milk litres?)
    # x: 911-958 (Goats?)
    # x: 958-1065 (Green fodder?)
    # x: 1065-1179 (Silage?)
    # x: 1179-1260 (Dry fodder?)
    # x: 1260-1550 (Irrigation?)
    
    full_row_txt = pytesseract.image_to_string(row_img, lang="mar+eng", config="--psm 6").strip()
    
    rows_data.append({
        "row_num": idx,
        "y1": y1,
        "y2": y2,
        "name_raw": name_txt,
        "mob_raw": mob_txt,
        "full_row": full_row_txt
    })

with open(BASE_DIR / "data" / "processed" / "rows_ocr_debug.json", "w", encoding="utf-8") as f:
    json.dump(rows_data, f, ensure_ascii=False, indent=2)

print("Saved rows_ocr_debug.json")
