# -*- coding: utf-8 -*-
import json
from pathlib import Path
import cv2
import numpy as np
import pytesseract
import re

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

def clean_name(raw: str) -> str:
    if not raw:
        return ""
    name = re.sub(r"^[\[\(]?\s*[0-9०-९ivxlcdmABCDEFabcdef]+\s*[\)\.\-\]]\s*", "", raw)
    name = re.sub(r"[\|\[\]_\-—~\\/]+", " ", name)
    name = " ".join(name.split()).strip()
    return name

w = img.shape[1]
w_scale = w / 1684.0
def col_range(x_start: int, x_end: int):
    return int(x_start * w_scale), int(x_end * w_scale)

x_name_start, x_name_end = col_range(135, 395)

records = []
for idx, y1, y2, expected in rows:
    name_crop = img[y1+4:y2-3, x_name_start+2:x_name_end-2]
    h_nc, w_nc = name_crop.shape
    scaled_name = cv2.resize(name_crop, (w_nc * 2, h_nc * 2), interpolation=cv2.INTER_CUBIC)
    norm_name = cv2.normalize(scaled_name, None, 0, 255, cv2.NORM_MINMAX)
    padded_name = cv2.copyMakeBorder(norm_name, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)

    name_raw = pytesseract.image_to_string(padded_name, lang="mar", config="--psm 7").strip()
    if not name_raw:
        name_raw = pytesseract.image_to_string(padded_name, lang="mar+eng", config="--psm 7").strip()

    farmer_name = clean_name(name_raw)
    exact_match = (farmer_name == expected)

    records.append({
        "row": idx,
        "expected": expected,
        "name_raw": name_raw,
        "farmer_name": farmer_name,
        "exact_match": exact_match
    })

Path("data/processed/new_extractor_names.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
print("Saved data/processed/new_extractor_names.json")
