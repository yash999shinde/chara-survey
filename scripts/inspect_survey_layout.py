# -*- coding: utf-8 -*-
import json
import pymupdf
import cv2
import numpy as np
import pytesseract
from pathlib import Path

BASE_DIR = Path(r"D:\chara-survey-automation-phase1-2\chara-survey-automation")
PDF_PATH = BASE_DIR / "data" / "uploads" / "4c6d29186a5840f3b14bc5f17240642c.pdf"
GRID_JSON = BASE_DIR / "data" / "processed" / "detected_grid_structure_270.json"

TESSERACT_EXE = r"D:\chara-survey-automation-phase1-2\tesseract.exe"
TESSDATA_DIR = r"D:\chara-survey-automation-phase1-2\tessdata"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE

doc = pymupdf.open(str(PDF_PATH))
page = doc[0]
mat = pymupdf.Matrix(2.0, 2.0).prerotate(270)
pix = page.get_pixmap(matrix=mat, alpha=False)
img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if pix.n >= 3 else img
doc.close()

h, w = gray.shape
print(f"Page dimensions: {w} x {h}")

with open(GRID_JSON, "r", encoding="utf-8") as f:
    grid = json.load(f)

print(f"Total rows in grid JSON: {len(grid)}")

# Check header rows (rows 0 to 5)
headers_info = []
for r in grid[:6]:
    r_idx = r["row_index"]
    y1, y2 = r["y_range"]
    crop = gray[y1:y2, :]
    txt = pytesseract.image_to_string(crop, lang="mar+eng", config="--psm 6").strip()
    headers_info.append((r_idx, y1, y2, txt[:100]))

# Check columns for row 6 (first data row)
first_data_row = grid[6]
print(f"\nRow 6 Y-range: {first_data_row['y_range']}")
print(f"Number of detected cells in Row 6: {len(first_data_row['cells'])}")
col_bboxes = []
for c in first_data_row["cells"]:
    c_idx = c["col_index"]
    x1, y1, x2, y2 = c["bbox"]
    cell_crop = gray[y1:y2, x1:x2]
    txt = pytesseract.image_to_string(cell_crop, lang="mar+eng", config="--psm 6").strip()
    col_bboxes.append((c_idx, x1, x2, txt))

out_data = {
    "dimensions": [w, h],
    "header_rows": headers_info,
    "row6_cells": col_bboxes
}

with open(BASE_DIR / "data" / "processed" / "inspect_layout.json", "w", encoding="utf-8") as f:
    json.dump(out_data, f, ensure_ascii=False, indent=2)

print("Saved inspection to data/processed/inspect_layout.json")
