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

# Let's inspect the vertical lines / column bounds
# In detect_grid_geometry_270:
# x_lines were detected around:
# [381, 399, 611, 653, 697, 741, 781, 817, 858, 911, 958, 1004, 1065, 1125, 1179, 1198, 1238, 1260, ...]
# What is between 60 and 399?
# Serial No: 60 - 110
# Farmer Name: 110 - 399
# Mobile No: 399 - 611

# What are the columns after 611?
# Let's test slicing at:
# 611 - 653
# 653 - 697
# 697 - 741
# 741 - 781
# 781 - 817
# 817 - 858
# 858 - 911
# 911 - 958
# 958 - 1004
# 1004 - 1065
# 1065 - 1125
# 1125 - 1179
# 1179 - 1238
# 1238 - 1260
# 1260 - 1350
# 1350 - 1450

col_splits = [
    ("sr_no", 60, 110),
    ("farmer_name", 110, 399),
    ("mobile", 399, 611),
    ("c1", 611, 653),
    ("c2", 653, 697),
    ("c3", 697, 741),
    ("c4", 741, 781),
    ("c5", 781, 817),
    ("c6", 817, 858),
    ("c7", 858, 911),
    ("c8", 911, 958),
    ("c9", 958, 1004),
    ("c10", 1004, 1065),
    ("c11", 1065, 1125),
    ("c12", 1125, 1179),
    ("c13", 1179, 1238),
    ("c14", 1238, 1320),
    ("c15", 1320, 1450),
    ("c16", 1450, 1600),
]

row_ys = [
    (281, 317), # Row 1
    (317, 353), # Row 2
    (353, 389), # Row 3
    (389, 425), # Row 4
    (425, 461), # Row 5
    (461, 497), # Row 6
]

table_dump = []

for r_idx, (y1, y2) in enumerate(row_ys, 1):
    row_data = {"row": r_idx}
    for col_name, x1, x2 in col_splits:
        cell = gray[y1+2:y2-2, x1+2:x2-2]
        txt = pytesseract.image_to_string(cell, lang="mar+eng", config="--psm 6").strip()
        row_data[col_name] = txt
    table_dump.append(row_data)

with open(BASE_DIR / "data" / "processed" / "col_dump.json", "w", encoding="utf-8") as f:
    json.dump(table_dump, f, ensure_ascii=False, indent=2)

print("Saved col_dump.json")
