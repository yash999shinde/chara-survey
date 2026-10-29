# -*- coding: utf-8 -*-
import cv2
import json
from pathlib import Path
import pytesseract

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TESS_CMD = r"D:\chara-survey-automation-phase1-2\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESS_CMD

img_path = PROJECT_ROOT / "data" / "processed" / "left_region_headers_and_names.png"
img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)

cols = [
    (75, 131, "Col_1_Serial_No"),
    (131, 398, "Col_2_Farmer_Name"),
    (398, 615, "Col_3_Mobile_No")
]

results = {}
for x1, x2, name in cols:
    crop = img[50:280, x1:x2]
    crop_file = PROJECT_ROOT / "data" / "processed" / f"header_{name}.png"
    cv2.imwrite(str(crop_file), crop)
    txt = pytesseract.image_to_string(crop, lang="mar+eng", config="--psm 6").strip()
    results[name] = txt

out_file = PROJECT_ROOT / "data" / "processed" / "header_left_ocr.json"
out_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print("Saved header_left_ocr.json and header crop images")
