Set-Location "D:\chara-survey-automation-phase1-2\chara-survey-automation"

$code = @'
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
OUTPUT_JSON = r"data\processed\extracted_farmers_270.json"
CROP_DEBUG_DIR = r"data\processed\farmer_cell_crops"
os.makedirs(CROP_DEBUG_DIR, exist_ok=True)

MARATHI_DIGITS = str.maketrans({'०':'0','१':'1','२':'2','३':'3','४':'4','५':'5','६':'6','७':'7','८':'8','९':'9'})

def render_page(pdf_path, rotation=270, zoom=2.0):
    doc = pymupdf.open(pdf_path)
    page = doc[0]
    mat = pymupdf.Matrix(zoom, zoom).prerotate(rotation)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR) if pix.n == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    doc.close()
    return gray

def preprocess_cell(crop, is_number=False):
    h, w = crop.shape
    if h <= 6 or w <= 6:
        return crop

    shave_y = max(2, int(h * 0.08))
    shave_x = max(2, int(w * 0.06))
    inner = crop[shave_y:h-shave_y, shave_x:w-shave_x]

    ih, iw = inner.shape
    if ih < 40 or iw < 40:
        inner = cv2.resize(inner, (max(iw * 2, 40), max(ih * 2, 40)), interpolation=cv2.INTER_CUBIC)

    norm = cv2.normalize(inner, None, 0, 255, cv2.NORM_MINMAX)
    _, thresh = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    padded = cv2.copyMakeBorder(thresh, 6, 6, 6, 6, cv2.BORDER_CONSTANT, value=255)
    return padded

def run_cell_ocr(crop, is_number=False):
    prep = preprocess_cell(crop, is_number=is_number)
    pil = Image.fromarray(prep)

    if is_number:
        cfg = r'--psm 6 -c tessedit_char_whitelist=0123456789.०१२३४५६७८९'
        txt = pytesseract.image_to_string(pil, lang="eng+mar", config=cfg)
        txt = txt.translate(MARATHI_DIGITS).strip()
        txt = re.sub(r'[^0-9.]', '', txt)
        return txt
    else:
        cfg = r'--psm 6'
        txt = pytesseract.image_to_string(pil, lang="mar+eng", config=cfg)
        return txt.strip().replace('\n', ' ')

def main():
    if not os.path.exists(GRID_JSON):
        print(f"[ERROR] Missing grid structure JSON: {GRID_JSON}")
        return

    with open(GRID_JSON, "r", encoding="utf-8") as f:
        rows = json.load(f)

    gray = render_page(PDF_PATH, rotation=270, zoom=2.0)

    print("=== INSPECTING TABLE COLUMNS (HEADER ROWS 00 & 01) ===")
    header_rows = [r for r in rows if r["row_index"] in (0, 1)]
    for hr in header_rows:
        print(f"\n--- Header Row {hr['row_index']} ---")
        for cell in hr["cells"]:
            x1, y1, x2, y2 = cell["bbox"]
            crop = gray[y1:y2, x1:x2]
            if crop.size == 0 or cell["ink_pixels"] < 30:
                continue
            txt = run_cell_ocr(crop, is_number=False)
            if txt:
                print(f"  Col {cell['col_index']:02d} (w={cell['width']}): '{txt}'")

    data_rows = [r for r in rows if 2 <= r["row_index"] <= 11]
    extracted = []
    print("\n=== EXTRACTING DATA ROWS (TOP 6 FARMERS) ===")
    for r in data_rows:
        r_idx = r["row_index"]
        cells = r["cells"]
        row_dict = {}

        for c in cells:
            c_idx = c["col_index"]
            x1, y1, x2, y2 = c["bbox"]
            crop = gray[y1:y2, x1:x2]
            if crop.size == 0:
                row_dict[f"col_{c_idx}"] = ""
                continue

            if r_idx in (2, 4) and c["ink_pixels"] > 30:
                crop_path = os.path.join(CROP_DEBUG_DIR, f"R{r_idx}_C{c_idx}.png")
                cv2.imwrite(crop_path, crop)

            val_mar = run_cell_ocr(crop, is_number=False)
            val_num = run_cell_ocr(crop, is_number=True)

            row_dict[f"col_{c_idx}"] = {
                "text": val_mar,
                "numeric": val_num,
                "ink": c["ink_pixels"],
                "width": c["width"]
            }

        extracted.append({
            "row_index": r_idx,
            "columns": row_dict
        })

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(extracted, f, ensure_ascii=False, indent=2)

    print(f"\n[+] Saved extracted cell data to: {OUTPUT_JSON}")
    print(f"[+] Saved cell debug crops to: {CROP_DEBUG_DIR}")

if __name__ == "__main__":
    main()
'@

# Safe file writing using .NET to prevent PowerShell encoding or quote issues
[System.IO.File]::WriteAllText("$PWD\scripts\extract_cells_270.py", $code, [System.Text.Encoding]::UTF8)

