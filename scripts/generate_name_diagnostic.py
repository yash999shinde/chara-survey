# -*- coding: utf-8 -*-
import cv2
import json
import re
from pathlib import Path
import pytesseract

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TESS_CMD = r"D:\chara-survey-automation-phase1-2\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESS_CMD

img_path = PROJECT_ROOT / "data" / "processed" / "page_270_full.png"
img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)

rows = [
    (1, 282, 318, "आशिष शब्बीर शेख"),
    (2, 318, 354, "समीर जमाल शेख"),
    (3, 354, 391, "लतीफ जमाल शेख"),
    (4, 391, 427, "इब्राहिम रुबाब शेख"),
    (5, 427, 464, "नबाब रुबाब शेख"),
    (6, 464, 500, "बशीर कमाल शेख"),
]

def clean_ocr_name(raw: str) -> str:
    if not raw:
        return ""
    # Strip leading/trailing punctuation and line noise without destroying Devanagari
    s = re.sub(r"^[\|\-_~\\/\[\]\(\)\.\s*]+", "", raw)
    s = re.sub(r"[\|\-_~\\/\[\]\(\)\.\s*]+$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

diagnostic_rows = []

for row_idx, y1, y2, expected_name in rows:
    cell = img[y1+4:y2-3, 135:395]
    
    # 2.0x rescale with margin for Tesseract
    h, w = cell.shape
    scaled = cv2.resize(cell, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
    norm = cv2.normalize(scaled, None, 0, 255, cv2.NORM_MINMAX)
    padded = cv2.copyMakeBorder(norm, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)

    raw_ocr = pytesseract.image_to_string(padded, lang="mar", config="--psm 7").strip()
    processed_name = clean_ocr_name(raw_ocr)

    exact_match = (processed_name == expected_name)

    diagnostic_rows.append({
        "page": 1,
        "row": row_idx,
        "expected_ground_truth": expected_name,
        "raw_ocr_output": raw_ocr,
        "processed_name": processed_name,
        "exact_match": exact_match
    })

out_file = PROJECT_ROOT / "data" / "processed" / "name_diagnostic_report.json"
out_file.write_text(json.dumps(diagnostic_rows, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Processed {len(diagnostic_rows)} rows. Diagnostics written to {out_file}")
