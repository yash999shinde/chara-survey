import os
import pytesseract
from PIL import Image

TESSERACT_EXE = r"D:\chara-survey-automation-phase1-2\tesseract.exe"
TESSDATA_DIR = r"D:\chara-survey-automation-phase1-2\tessdata"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
os.environ["TESSDATA_PREFIX"] = TESSDATA_DIR

for rot in [0, 180, 90, 270]:
    img_path = os.path.join(r"data\processed\orientation_check", f"page_rot_{rot}.png")
    if not os.path.exists(img_path):
        continue
    img = Image.open(img_path)
    txt = pytesseract.image_to_string(img, lang="mar+eng", config="--psm 3")
    print(f"\n==================== ROTATION {rot} DEGREE TEXT ====================")
    lines = [line.strip() for line in txt.split("\n") if line.strip()]
    for l in lines[:15]:
        print("  ", l)
