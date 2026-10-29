from pathlib import Path
import cv2
import numpy as np
import pymupdf

root = Path(__file__).resolve().parents[1]
pdf_dir = root / "data" / "processed"
out_dir = pdf_dir / "ocr_results"
out_dir.mkdir(parents=True, exist_ok=True)

pdf = pdf_dir / "20261028_070119_bhiya.pdf"
if not pdf.exists():
    pdf = root / "data" / "uploads" / "20261028_070119_bhiya.pdf"

if not pdf.exists():
    candidates = list((root / "data" / "processed").glob("*.pdf"))
    if not candidates:
        candidates = list((root / "data" / "uploads").glob("*.pdf"))
    if not candidates:
        raise FileNotFoundError("No PDF found in uploads or processed")
    pdf = candidates[0]

print("Using PDF:", pdf.name)

with pymupdf.open(pdf) as doc:
    page = doc[0]
    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    image = np.frombuffer(pix.samples, dtype=np.uint8)
    image = image.reshape(pix.height, pix.width, pix.n)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

original_path = out_dir / "table_debug_page1.png"
cv2.imwrite(str(original_path), image)

gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
gray = cv2.GaussianBlur(gray, (3, 3), 0)
binary = cv2.adaptiveThreshold(
    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY_INV, 31, 10
)

horizontal_kernel = cv2.getStructuringElement(
    cv2.MORPH_RECT, (max(20, image.shape[1] // 30), 1)
)
vertical_kernel = cv2.getStructuringElement(
    cv2.MORPH_RECT, (1, max(20, image.shape[0] // 30))
)

horizontal = cv2.morphologyEx(
    binary, cv2.MORPH_OPEN, horizontal_kernel
)
vertical = cv2.morphologyEx(
    binary, cv2.MORPH_OPEN, vertical_kernel
)

lines = cv2.bitwise_or(horizontal, vertical)
overlay = image.copy()
overlay[horizontal > 0] = (0, 0, 255)
overlay[vertical > 0] = (0, 255, 0)

overlay_path = out_dir / "table_lines_overlay.png"
cv2.imwrite(str(overlay_path), overlay)

print("Page preview:", original_path)
print("Detected lines preview:", overlay_path)
print("Image dimensions:", image.shape[1], "x", image.shape[0])
