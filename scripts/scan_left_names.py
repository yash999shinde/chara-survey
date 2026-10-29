# -*- coding: utf-8 -*-
import json
import pymupdf
import cv2
import numpy as np
import pytesseract
import os

TESSERACT_EXE = r"D:\chara-survey-automation-phase1-2\tesseract.exe"
TESSDATA_DIR = r"D:\chara-survey-automation-phase1-2\tessdata"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE

PDF_PATH = r"data\uploads\4c6d29186a5840f3b14bc5f17240642c.pdf"
GRID_JSON = r"data\processed\detected_grid_structure_270.json"
OUT_DIR = r"data\processed\left_side_crops"
os.makedirs(OUT_DIR, exist_ok=True)

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

# Col 1 start position is where the numbers began
col1_x1 = farmer_rows[0]["cells"][1]["bbox"][0]
print(f"[*] Numbers start at X = {col1_x1}. Scanning left region from X=0 to X={col1_x1}...\n")

for idx, r in enumerate(farmer_rows, 1):
    r_idx = r["row_index"]
    y1, y2 = r["y_range"]
    
    # Crop entire left segment before mobile numbers
    left_crop = gray[y1:y2, 50:col1_x1]
    
    # Save crop for visual verification
    crop_path = os.path.join(OUT_DIR, f"farmer_{idx}_left_name.png")
    cv2.imwrite(crop_path, left_crop)
    
    # Enhance contrast
    norm = cv2.normalize(left_crop, None, 0, 255, cv2.NORM_MINMAX)
    _, thresh = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    txt_raw = pytesseract.image_to_string(thresh, lang="mar+eng", config="--psm 6").strip()
    print(f"Farmer #{idx} Left Strip (Y={y1}:{y2}):")
    print(f"  Extracted Text : '{txt_raw}'")
    print(f"  Saved Image    : {crop_path}")
    print("-" * 50)