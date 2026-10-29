# -*- coding: utf-8 -*-
import cv2
import json
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

out_dir = PROJECT_ROOT / "data" / "processed" / "inner_cell_tests"
out_dir.mkdir(parents=True, exist_ok=True)

results = []

for row_idx, y1, y2, expected_name in rows:
    # Strict inner cell crop: avoid top/bottom and left/right border lines
    cell = img[y1+5:y2-4, 138:392]
    cv2.imwrite(str(out_dir / f"row_{row_idx}_clean_inner.png"), cell)

    # 1. Raw grayscale PSM 6
    t1 = pytesseract.image_to_string(cell, lang="mar", config="--psm 6").strip()
    t1_me = pytesseract.image_to_string(cell, lang="mar+eng", config="--psm 6").strip()

    # 2. Raw grayscale PSM 7 (treat as single text line)
    t2 = pytesseract.image_to_string(cell, lang="mar", config="--psm 7").strip()
    t2_me = pytesseract.image_to_string(cell, lang="mar+eng", config="--psm 7").strip()

    # 3. Normalized + Otsu
    norm = cv2.normalize(cell, None, 0, 255, cv2.NORM_MINMAX)
    _, th_otsu = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite(str(out_dir / f"row_{row_idx}_otsu.png"), th_otsu)
    t3 = pytesseract.image_to_string(th_otsu, lang="mar", config="--psm 7").strip()
    t3_me = pytesseract.image_to_string(th_otsu, lang="mar+eng", config="--psm 7").strip()

    # 4. Rescaled (2.5x) with border padding
    h, w = cell.shape
    scaled = cv2.resize(cell, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
    padded = cv2.copyMakeBorder(scaled, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255)
    cv2.imwrite(str(out_dir / f"row_{row_idx}_padded.png"), padded)
    t4 = pytesseract.image_to_string(padded, lang="mar", config="--psm 7").strip()
    t4_me = pytesseract.image_to_string(padded, lang="mar+eng", config="--psm 7").strip()

    # 5. Scaled + Otsu + padding
    norm_sc = cv2.normalize(padded, None, 0, 255, cv2.NORM_MINMAX)
    _, th_sc = cv2.threshold(norm_sc, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite(str(out_dir / f"row_{row_idx}_sc_otsu.png"), th_sc)
    t5 = pytesseract.image_to_string(th_sc, lang="mar", config="--psm 7").strip()
    t5_me = pytesseract.image_to_string(th_sc, lang="mar+eng", config="--psm 7").strip()

    results.append({
        "row": row_idx,
        "expected_name": expected_name,
        "raw_mar_psm6": t1,
        "raw_mareng_psm6": t1_me,
        "raw_mar_psm7": t2,
        "raw_mareng_psm7": t2_me,
        "otsu_mar_psm7": t3,
        "otsu_mareng_psm7": t3_me,
        "padded_mar_psm7": t4,
        "padded_mareng_psm7": t4_me,
        "sc_otsu_mar_psm7": t5,
        "sc_otsu_mareng_psm7": t5_me
    })

out_json = out_dir / "inner_cell_results.json"
out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print("Saved inner_cell_results.json")
