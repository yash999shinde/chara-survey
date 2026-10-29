import os
import json
import re
import cv2
import numpy as np
import pymupdf
import pytesseract
from PIL import Image

# Tesseract Configuration
TESSERACT_EXE = r"D:\chara-survey-automation-phase1-2\tesseract.exe"
TESSDATA_DIR = r"D:\chara-survey-automation-phase1-2\tessdata"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
os.environ["TESSDATA_PREFIX"] = TESSDATA_DIR

PDF_PATH = r"data\uploads\4c6d29186a5840f3b14bc5f17240642c.pdf"
GRID_JSON_PATH = r"data\processed\detected_grid_structure.json"
OUTPUT_JSON = r"data\processed\extracted_six_farmers.json"

MARATHI_TO_ENG_DIGITS = str.maketrans({
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
})

def render_page(pdf_path, rotation=90, zoom=2.0):
    doc = pymupdf.open(pdf_path)
    page = doc[0]
    mat = pymupdf.Matrix(zoom, zoom).prerotate(rotation)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    if pix.n == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img
    doc.close()
    return gray

def preprocess_cell(cell_img, is_numeric=False):
    """Binarize, de-noise, and pad cell images for OCR."""
    h, w = cell_img.shape
    if h == 0 or w == 0:
        return cell_img

    # Rescale small cells to ensure good stroke resolution
    if h < 40 or w < 40:
        cell_img = cv2.resize(cell_img, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

    # Adaptive binarization to clean paper artifacts
    norm = cv2.normalize(cell_img, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    blurred = cv2.GaussianBlur(norm, (3, 3), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
    )

    # Invert, clear tiny outer speckles, invert back
    inv = cv2.bitwise_not(thresh)
    # Add border padding so characters are not touching edge
    padded = cv2.copyMakeBorder(inv, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=0)
    final = cv2.bitwise_not(padded)
    return final

def normalize_digits(text):
    text = text.translate(MARATHI_TO_ENG_DIGITS)
    # Remove all non-numeric characters except decimal/hyphen
    return text.strip()

def run_cell_ocr(cell_img, is_numeric=False):
    prep = preprocess_cell(cell_img, is_numeric=is_numeric)
    pil_img = Image.fromarray(prep)

    if is_numeric:
        config = r'--psm 6 -c tessedit_char_whitelist=0123456789.०१२३४५६७८९-'
        text = pytesseract.image_to_string(pil_img, lang="eng+mar", config=config)
        clean = normalize_digits(text)
        return clean
    else:
        config = r'--psm 6'
        text = pytesseract.image_to_string(pil_img, lang="mar+eng", config=config)
        return text.strip().replace("\n", " ")

def main():
    if not os.path.exists(GRID_JSON_PATH):
        print(f"[ERROR] Run detect_grid_geometry.py first. Missing {GRID_JSON_PATH}")
        return

    with open(GRID_JSON_PATH, "r", encoding="utf-8") as f:
        grid = json.load(f)

    gray = render_page(PDF_PATH, rotation=90, zoom=2.0)

    # Header rows: Row 00, Row 01
    # Farmer data rows: Row 02 through Row 07 (6 populated rows)
    populated_rows = [r for r in grid if 2 <= r["row_index"] <= 7]

    extracted_records = []

    print(f"[*] Processing {len(populated_rows)} populated farmer rows at cell level...")

    for row_idx, r_data in enumerate(populated_rows, start=1):
        cells = r_data["cells"]
        row_values = {}

        # Scan row cells
        for c_idx, cell in enumerate(cells):
            x1, y1, x2, y2 = cell["bbox"]
            # Exclude 3px boundary to remove table border lines
            crop = gray[y1 + 3 : y2 - 3, x1 + 3 : x2 - 3]
            if crop.size == 0 or cell["ink_pixels"] < 30:
                row_values[f"col_{c_idx}"] = ""
                continue

            # Check if likely a numeric column (Cols 0 is index, cols >= 3 are counts/mobile)
            is_num = (c_idx == 0 or c_idx >= 3)
            val = run_cell_ocr(crop, is_numeric=is_num)
            row_values[f"col_{c_idx}"] = val

        record = {
            "row_index": row_idx,
            "raw_cells": row_values,
            # Defaults matching Google Form
            "taluka": "नगर",
            "veterinary_hospital": "Ralegun",
            "revenue_circle": "Walki",
            "needs_review": False,
            "review_reasons": []
        }
        extracted_records.append(record)

    # Print summary of extracted rows for inspection
    print("\n=== EXTRACTED CELL MATRIX PREVIEW ===")
    for rec in extracted_records:
        r = rec["row_index"]
        cells = rec["raw_cells"]
        print(f"\n--- Row {r} ---")
        for col_k, col_v in sorted(cells.items(), key=lambda x: int(x[0].split('_')[1])):
            if col_v:
                print(f"  {col_k}: '{col_v}'")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(extracted_records, f, ensure_ascii=False, indent=2)

    print(f"\n[+] Cell extraction complete. Saved to: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
