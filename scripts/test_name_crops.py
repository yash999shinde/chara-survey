# -*- coding: utf-8 -*-
import cv2
import json
from pathlib import Path
import pytesseract
import unicodedata
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TESS_CMD = r"D:\chara-survey-automation-phase1-2\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESS_CMD

img_path = PROJECT_ROOT / "data" / "processed" / "page_270_full.png"
img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)

rows = [
    (1, 282, 318),
    (2, 318, 354),
    (3, 354, 391),
    (4, 391, 427),
    (5, 427, 464),
    (6, 464, 500),
]

out_dir = PROJECT_ROOT / "data" / "processed" / "name_investigation"
out_dir.mkdir(parents=True, exist_ok=True)

diagnostics = []

for row_idx, y1, y2 in rows:
    # 1. Full row segment (from left table border X=75 to Col 3 right border X=615)
    row_crop = img[y1:y2, 75:615]
    cv2.imwrite(str(out_dir / f"row_{row_idx}_full.png"), row_crop)
    
    # 2. Serial no (75 to 131)
    sr_crop = img[y1:y2, 75:131]
    cv2.imwrite(str(out_dir / f"row_{row_idx}_sr.png"), sr_crop)

    # 3. Name col (131 to 398)
    name_crop = img[y1:y2, 131:398]
    cv2.imwrite(str(out_dir / f"row_{row_idx}_name_col.png"), name_crop)

    # 4. Mobile col (398 to 615)
    mob_crop = img[y1:y2, 398:615]
    cv2.imwrite(str(out_dir / f"row_{row_idx}_mob_col.png"), mob_crop)

    # 5. Combined Sr + Name (75 to 398)
    sr_name_crop = img[y1:y2, 75:398]
    cv2.imwrite(str(out_dir / f"row_{row_idx}_sr_name.png"), sr_name_crop)

    # Let's test different pre-processing on the Name Col
    # A. Raw
    t_raw = pytesseract.image_to_string(name_crop, lang="mar+eng", config="--psm 6").strip()
    t_raw_psm7 = pytesseract.image_to_string(name_crop, lang="mar+eng", config="--psm 7").strip()
    t_raw_mar = pytesseract.image_to_string(name_crop, lang="mar", config="--psm 6").strip()

    # B. Otsu
    norm = cv2.normalize(name_crop, None, 0, 255, cv2.NORM_MINMAX)
    _, th_otsu = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite(str(out_dir / f"row_{row_idx}_name_otsu.png"), th_otsu)
    t_otsu = pytesseract.image_to_string(th_otsu, lang="mar+eng", config="--psm 6").strip()
    t_otsu_mar = pytesseract.image_to_string(th_otsu, lang="mar", config="--psm 6").strip()
    t_otsu_psm7 = pytesseract.image_to_string(th_otsu, lang="mar+eng", config="--psm 7").strip()

    # C. Rescaled (2x) Otsu
    scaled = cv2.resize(name_crop, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    norm2 = cv2.normalize(scaled, None, 0, 255, cv2.NORM_MINMAX)
    _, th_scaled = cv2.threshold(norm2, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite(str(out_dir / f"row_{row_idx}_name_scaled.png"), th_scaled)
    t_scaled = pytesseract.image_to_string(th_scaled, lang="mar+eng", config="--psm 6").strip()
    t_scaled_mar = pytesseract.image_to_string(th_scaled, lang="mar", config="--psm 6").strip()
    t_scaled_psm7 = pytesseract.image_to_string(th_scaled, lang="mar+eng", config="--psm 7").strip()

    # D. Also OCR Sr + Name combined
    t_sr_name = pytesseract.image_to_string(sr_name_crop, lang="mar+eng", config="--psm 6").strip()

    # E. Full row OCR
    t_full_row = pytesseract.image_to_string(row_crop, lang="mar+eng", config="--psm 6").strip()

    diagnostics.append({
        "row": row_idx,
        "y_range": [y1, y2],
        "ocr_name_raw_psm6": t_raw,
        "ocr_name_raw_psm7": t_raw_psm7,
        "ocr_name_raw_mar": t_raw_mar,
        "ocr_name_otsu_psm6": t_otsu,
        "ocr_name_otsu_mar": t_otsu_mar,
        "ocr_name_otsu_psm7": t_otsu_psm7,
        "ocr_name_scaled_psm6": t_scaled,
        "ocr_name_scaled_mar": t_scaled_mar,
        "ocr_name_scaled_psm7": t_scaled_psm7,
        "ocr_sr_name_crop": t_sr_name,
        "ocr_full_row": t_full_row
    })

out_json = out_dir / "name_diagnostics.json"
out_json.write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8")
print("Diagnostics saved to data/processed/name_investigation/name_diagnostics.json")
