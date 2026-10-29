import os
import pymupdf
import cv2
import pytesseract
from PIL import Image

TESSERACT_EXE = r"D:\chara-survey-automation-phase1-2\tesseract.exe"
TESSDATA_DIR = r"D:\chara-survey-automation-phase1-2\tessdata"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
os.environ["TESSDATA_PREFIX"] = TESSDATA_DIR

PDF_PATH = r"data\uploads\4c6d29186a5840f3b14bc5f17240642c.pdf"
DEBUG_DIR = r"data\processed\orientation_check"
os.makedirs(DEBUG_DIR, exist_ok=True)

doc = pymupdf.open(PDF_PATH)
page = doc[0]
print(f"[*] Raw PDF Page Rect: {page.rect}, Native Rotation: {page.rotation}")

rotations = [0, 90, 180, 270]
best_rot = None
max_mar_chars = -1

for rot in rotations:
    mat = pymupdf.Matrix(2.0, 2.0).prerotate(rot)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img_path = os.path.join(DEBUG_DIR, f"page_rot_{rot}.png")
    pix.save(img_path)
    
    # Run test OCR on center crop of each orientation to check readable Marathi text
    pil_img = Image.open(img_path)
    w, h = pil_img.size
    # Crop central region where table lives
    sample = pil_img.crop((w * 0.15, h * 0.15, w * 0.85, h * 0.85))
    
    text = pytesseract.image_to_string(sample, lang="mar+eng", config="--psm 11")
    # Count Devanagari Unicode characters (U+0900 to U+097F)
    dev_count = sum(1 for ch in text if '\u0900' <= ch <= '\u097f')
    print(f"Rotation {rot:3d}deg: Image size = {w}x{h} | Detected Devanagari chars = {dev_count}")
    
    if dev_count > max_mar_chars:
        max_mar_chars = dev_count
        best_rot = rot

print(f"\n[+] Recommended rotation with maximum Marathi text: {best_rot}deg ({max_mar_chars} chars)")
doc.close()
