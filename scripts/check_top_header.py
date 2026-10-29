# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import cv2
import pymupdf
import pytesseract
import re

PROJECT_ROOT = Path(r"D:\chara-survey-automation-phase1-2\chara-survey-automation")
pdf_path = PROJECT_ROOT / "data" / "uploads" / "4c6d29186a5840f3b14bc5f17240642c.pdf"

TESSERACT_EXE = r"D:\chara-survey-automation-phase1-2\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE

doc = pymupdf.open(str(pdf_path))
page = doc[0]
mat = pymupdf.Matrix(2.0, 2.0).prerotate(270)
pix = page.get_pixmap(matrix=mat, alpha=False)
import numpy as np
img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if pix.n >= 3 else img
doc.close()

top_crop = gray[0:120, :]
txt = pytesseract.image_to_string(top_crop, lang="mar+eng", config="--psm 6")

print("Top 120px OCR:")
with open(PROJECT_ROOT / "data" / "processed" / "top_header_check.txt", "w", encoding="utf-8") as f:
    f.write(txt)

print("Saved to top_header_check.txt")
