from pathlib import Path
import cv2

folder = Path("data/processed/ocr_results")
src = folder / "survey_rotated_ccw.png"
image = cv2.imread(str(src))

if image is None:
    raise FileNotFoundError(f"Cannot read {src}")

h, w = image.shape[:2]

# Include the column headings and all populated rows.
crop = image[int(h * 0.04):int(h * 0.44), int(w * 0.025):int(w * 0.97)]

crop = cv2.resize(crop, None, fx=1.5, fy=1.5,
                   interpolation=cv2.INTER_CUBIC)

out = folder / "survey_headers_and_rows.png"
cv2.imwrite(str(out), crop)
print("Saved:", out)
