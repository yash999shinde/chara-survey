# -*- coding: utf-8 -*-
import json
import pymupdf
import cv2
import numpy as np
import pytesseract

TESSERACT_EXE = r"D:\chara-survey-automation-phase1-2\tesseract.exe"
TESSDATA_DIR = r"D:\chara-survey-automation-phase1-2\tessdata"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE

PDF_PATH = r"data\uploads\4c6d29186a5840f3b14bc5f17240642c.pdf"
GRID_JSON = r"data\processed\detected_grid_structure_270.json"

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

print("=== CHECKING COLUMNS 0 TO 7 ACROSS ALL 6 FARMER ROWS ===\n")
for idx, r in enumerate(farmer_rows, 1):
    r_idx = r["row_index"]
    cells = {c["col_index"]: c for c in r["cells"]}
    print(f"--- Farmer #{idx} (Grid Row {r_idx}) ---")
    for c_i in range(0, 8):
        c = cells.get(c_i)
        if not c:
            continue
        x1, y1, x2, y2 = c["bbox"]
        crop = gray[y1+2:y2-2, x1+2:x2-2]
        if crop.size == 0:
            continue
        txt = pytesseract.image_to_string(crop, lang="mar+eng", config="--psm 6").strip()
        print(f"  Col {c_i:02d} (w={c['width']:3d}, ink={c['ink_pixels']:4d}): '{txt}'")
    print()