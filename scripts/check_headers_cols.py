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

col_splits = [
    ("sr_no", 60, 110),
    ("farmer_name", 110, 399),
    ("mobile", 399, 611),
    ("c1_cow_large", 611, 653),
    ("c2_cow_small", 653, 697),
    ("c3_buff_large", 697, 741),
    ("c4_buff_small", 741, 781),
    ("c5_milch", 781, 817),
    ("c6_dry", 817, 858),
    ("c7_total", 858, 911),
    ("c8_milk", 911, 958),
    ("c9_goats", 958, 1004),
    ("c10_sheep", 1004, 1065),
    ("c11_water", 1065, 1125),
    ("c12_green_fodder", 1125, 1179),
    ("c13_silage", 1179, 1238),
    ("c14_dry_fodder", 1238, 1320),
    ("c15_area", 1320, 1450),
    ("c16_irrigation", 1450, 1600),
]

# Let's crop header rows (Y from 80 to 280) for each column
header_dump = {}
for name, x1, x2 in col_splits:
    crop = gray[120:280, x1:x2]
    txt = pytesseract.image_to_string(crop, lang="mar+eng", config="--psm 6").strip()
    header_dump[name] = {"x1": x1, "x2": x2, "header_ocr": txt}

with open(BASE_DIR / "data" / "processed" / "header_columns_dump.json", "w", encoding="utf-8") as f:
    json.dump(header_dump, f, ensure_ascii=False, indent=2)

print("Saved header_columns_dump.json")
