from pathlib import Path
import cv2
import numpy as np

folder = Path("data/processed/ocr_results/farmer_rows")
files = sorted(folder.glob("farmer_row_*.png"))

if len(files) != 6:
    raise RuntimeError(f"Expected 6 crops, found {len(files)}")

tiles = []
for path in files:
    img = cv2.imread(str(path))
    if img is None:
        continue

    target_width = 1200
    scale = target_width / img.shape[1]
    img = cv2.resize(
        img, (target_width, int(img.shape[0] * scale))
    )
    tiles.append(img)

sheet = cv2.vconcat(tiles)
out = Path("data/processed/ocr_results/farmer_rows_contact_sheet.png")
cv2.imwrite(str(out), sheet)
print("Saved:", out)
