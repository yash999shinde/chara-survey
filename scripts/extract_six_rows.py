from pathlib import Path
import os, sys
import pymupdf
import pytesseract
from PIL import Image, ImageOps

root = Path.cwd()
tess = Path(r"D:\chara-survey-automation-phase1-2\tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = str(tess)
os.environ["TESSDATA_PREFIX"] = str(tess.parent / "tessdata")

pdfs = []
for folder in [root / "data" / "uploads", root / "data" / "input", root]:
    if folder.exists():
        pdfs.extend(folder.glob("*.pdf"))

if not pdfs:
    sys.exit("ERROR: PDF nahi mila.")

pdf = max(pdfs, key=lambda p: p.stat().st_mtime)
out = root / "data" / "processed"
out.mkdir(parents=True, exist_ok=True)

with pymupdf.open(pdf) as doc:
    page = doc[0]
    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

image = image.rotate(90, expand=True)
w, h = image.size
print("PDF:", pdf.name, "| rotated image:", w, "x", h)

# Based on the visible preview: six handwritten rows below the header.
# If dimensions differ, stop rather than silently crop the wrong area.
if not (1600 <= w <= 1800 and 1100 <= h <= 1300):
    sys.exit("Image dimensions differ from preview. Need recalibrate crop.")

row_edges = [282, 317, 353, 389, 426, 462, 498]
# Save six individual row images and print whole-row OCR for inspection.
for i, (y0, y1) in enumerate(zip(row_edges, row_edges[1:]), start=1):
    crop = image.crop((35, y0, w - 35, y1))
    crop_path = out / f"farmer_row_{i}.png"
    crop.save(crop_path)

    enlarged = crop.resize((crop.width * 3, crop.height * 3))
    text = pytesseract.image_to_string(
        ImageOps.autocontrast(enlarged),
        lang="mar+eng",
        config="--psm 7"
    ).strip()

    print(f"\n--- ROW {i} ---")
    print(text if text else "[OCR could not read this row]")
    print("Image:", crop_path)

print("\nDiagnostic only: verify each row against the original PDF before importing.")
