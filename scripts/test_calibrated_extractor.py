# -*- coding: utf-8 -*-
import sys
import re
import json
import cv2
import numpy as np
import pymupdf
import pytesseract
from pathlib import Path

PROJECT_ROOT = Path(r"D:\chara-survey-automation-phase1-2\chara-survey-automation")
sys.path.insert(0, str(PROJECT_ROOT))

TESSERACT_EXE = r"D:\chara-survey-automation-phase1-2\tesseract.exe"
TESSDATA_DIR = r"D:\chara-survey-automation-phase1-2\tessdata"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE

PDF_PATH = PROJECT_ROOT / "data" / "uploads" / "4c6d29186a5840f3b14bc5f17240642c.pdf"

doc = pymupdf.open(str(PDF_PATH))
page = doc[0]
mat = pymupdf.Matrix(2.0, 2.0).prerotate(270)
pix = page.get_pixmap(matrix=mat, alpha=False)
img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if pix.n == 3 else img
doc.close()

MARATHI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

def clean_ocr_digits(val_str: str) -> str:
    if not val_str:
        return ""
    # Map devanagari digits
    s = val_str.translate(MARATHI_DIGITS)
    # Common OCR digit confusions
    s = s.replace("O", "0").replace("o", "0").replace("D", "0")
    s = s.replace("l", "1").replace("I", "1").replace("|", "")
    s = s.replace("Z", "2").replace("z", "2")
    s = s.replace("S", "5").replace("s", "5")
    s = s.replace("B", "8")
    s = s.replace("q", "9").replace("g", "9")
    nums = re.findall(r"\d+\.?\d*", s)
    return nums[0] if nums else ""

def clean_mobile_str(raw: str) -> tuple[str, bool]:
    if not raw:
        return ("", False)
    s = raw.translate(MARATHI_DIGITS)
    s = s.replace("O", "0").replace("o", "0").replace("D", "0")
    s = s.replace("l", "1").replace("I", "1").replace("|", "")
    s = s.replace("B", "8").replace("S", "5").replace("s", "5")
    digits = re.sub(r"\D", "", s)
    # Match standard 10 digit indian mobile
    m = re.search(r"[6-9]\d{9}", digits)
    if m:
        return (m.group(0), True)
    if len(digits) >= 10:
        for i in range(len(digits) - 9):
            candidate = digits[i:i+10]
            if candidate[0] in "6789":
                return (candidate, True)
        return (digits[:10], False)
    if len(digits) >= 6:
        return (digits, False)
    return ("", False)

def parse_num_cell(crop: np.ndarray, is_float: bool = False) -> tuple[float | int, str, bool]:
    """
    Returns (parsed_value, raw_text, is_uncertain)
    """
    if crop.size == 0 or cv2.countNonZero(crop < 200) < 15:
        # Empty cell
        return (0.0 if is_float else 0, "", False)
    
    # Preprocess
    h, w = crop.shape
    scale = max(1.0, 32.0 / h)
    if scale > 1.0:
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    
    norm = cv2.normalize(crop, None, 0, 255, cv2.NORM_MINMAX)
    _, thresh = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    txt = pytesseract.image_to_string(thresh, lang="eng+mar", config="--psm 6 -c tessedit_char_whitelist=0123456789.०१२३४५६७८९").strip()
    digits = clean_ocr_digits(txt)
    
    if not digits:
        # Check raw text for any non-digit marks
        raw_txt = pytesseract.image_to_string(thresh, lang="mar+eng", config="--psm 6").strip()
        if raw_txt and any(c.isalnum() for c in raw_txt):
            return (0.0 if is_float else 0, raw_txt, True) # Mark uncertain
        return (0.0 if is_float else 0, "", False)
    
    try:
        val = float(digits) if is_float else int(float(digits))
        return (val, txt, False)
    except:
        return (0.0 if is_float else 0, txt, True)

rows_y = [
    (281, 317), # Row 1: Ashish Shabbir Shaikh
    (317, 353), # Row 2: Samir Jamal Shaikh
    (353, 389), # Row 3: Latif Jamal Shaikh
    (389, 425), # Row 4: Ibrahim Rubab Shaikh
    (425, 461), # Row 5: Nabab Rubab Shaikh
    (461, 497), # Row 6: Bashir Kamal Shaikh
]

results = []

for idx, (y1, y2) in enumerate(rows_y, 1):
    row_crop = gray[y1:y2, :]
    full_row_ocr = pytesseract.image_to_string(row_crop, lang="mar+eng", config="--psm 6").strip()
    
    # Name crop: X=110 to 395
    name_crop = gray[y1+2:y2-2, 110:395]
    name_raw = pytesseract.image_to_string(name_crop, lang="mar+eng", config="--psm 6").strip()
    
    # Mobile crop: X=395 to 611
    mob_crop = gray[y1+2:y2-2, 395:611]
    mob_raw = pytesseract.image_to_string(mob_crop, lang="mar+eng", config="--psm 6").strip()
    clean_mob, is_valid_mob = clean_mobile_str(mob_raw)
    
    # If mobile not found in mob_crop, search full_row_ocr
    if not clean_mob or not is_valid_mob:
        full_mob, full_is_valid = clean_mobile_str(full_row_ocr)
        if full_is_valid:
            clean_mob = full_mob
            is_valid_mob = True

    # Numeric columns
    cow_large, cow_large_raw, c_l_unc = parse_num_cell(gray[y1+2:y2-2, 611:653])
    cow_small, cow_small_raw, c_s_unc = parse_num_cell(gray[y1+2:y2-2, 653:697])
    buff_large, buff_large_raw, b_l_unc = parse_num_cell(gray[y1+2:y2-2, 697:741])
    buff_small, buff_small_raw, b_s_unc = parse_num_cell(gray[y1+2:y2-2, 741:781])
    milch, milch_raw, m_unc = parse_num_cell(gray[y1+2:y2-2, 781:820])
    dry_anim, dry_raw, d_unc = parse_num_cell(gray[y1+2:y2-2, 820:860])
    milk_litres, milk_raw, milk_unc = parse_num_cell(gray[y1+2:y2-2, 911:958], is_float=True)
    goats, goats_raw, g_unc = parse_num_cell(gray[y1+2:y2-2, 958:1010])
    
    green_fodder, green_raw, gf_unc = parse_num_cell(gray[y1+2:y2-2, 1125:1180], is_float=True)
    silage, silage_raw, sil_unc = parse_num_cell(gray[y1+2:y2-2, 1180:1240], is_float=True)
    dry_fodder, dry_fodder_raw, df_unc = parse_num_cell(gray[y1+2:y2-2, 1240:1320], is_float=True)
    
    # Irrigation
    irr_crop = gray[y1+2:y2-2, 1450:1600]
    irr_txt = pytesseract.image_to_string(irr_crop, lang="mar+eng", config="--psm 6").strip()
    irr_type = "विहीर" if ("विहीर" in irr_txt or "विहीर" in full_row_ocr or "वि" in irr_txt) else ("बोअरवेल" if "बोअर" in irr_txt else "")

    uncertain_fields = []
    if not is_valid_mob:
        uncertain_fields.append("mobile")
    if not name_raw or len(re.findall(r"[\u0900-\u097F]", name_raw)) == 0:
        uncertain_fields.append("farmer_name")
    if c_l_unc: uncertain_fields.append("cow_large")
    if b_l_unc: uncertain_fields.append("buffalo_large")
    if milk_unc: uncertain_fields.append("daily_milk_litres")
    if g_unc: uncertain_fields.append("goats")

    rec = {
        "row": idx,
        "farmer_name_raw": name_raw,
        "mobile_raw": mob_raw,
        "mobile_clean": clean_mob,
        "is_valid_mobile": is_valid_mob,
        "cow_large": cow_large,
        "cow_small": cow_small,
        "buffalo_large": buff_large,
        "buffalo_small": buff_small,
        "milch_animals": milch,
        "dry_animals": dry_anim,
        "daily_milk_litres": milk_litres,
        "goats": goats,
        "green_fodder_tonnes": green_fodder,
        "silage_tonnes": silage,
        "dry_fodder_tonnes": dry_fodder,
        "irrigation_types": irr_type,
        "uncertain_fields": uncertain_fields,
        "status": "needs_review" if uncertain_fields else "pending_review",
        "raw_ocr_text": full_row_ocr
    }
    results.append(rec)

with open(PROJECT_ROOT / "data" / "processed" / "calibrated_extractor_test.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("Saved calibrated_extractor_test.json successfully")
