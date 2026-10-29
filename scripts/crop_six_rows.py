from pathlib import Path
import cv2

folder = Path("data/processed/ocr_results")
src = folder / "survey_rotated_ccw.png"
out = folder / "farmer_rows"
out.mkdir(parents=True, exist_ok=True)

image = cv2.imread(str(src))
if image is None:
    raise FileNotFoundError(f"Image not found: {src}")

h, w = image.shape[:2]

# The visible populated records occupy approximately this area.
# These are initial crops; verify them visually before using their data.
left = int(w * 0.025)
right = int(w * 0.97)
top = int(h * 0.19)
bottom = int(h * 0.43)

table = image[top:bottom, left:right]
if table.size == 0:
    raise RuntimeError("Table crop is empty")

# Approximate row boundaries for this six-row sample.
# Adjust after inspecting the generated preview.
row_edges = [0, 1/6, 2/6, 3/6, 4/6, 5/6, 1]

for i in range(6):
    y1 = int(table.shape[0] * row_edges[i])
    y2 = int(table.shape[0] * row_edges[i + 1])
    row = table[y1:y2, :]

    row = cv2.resize(
        row, None, fx=2, fy=2,
        interpolation=cv2.INTER_CUBIC
    )

    path = out / f"farmer_row_{i+1}.png"
    cv2.imwrite(str(path), row)
    print(path)

print("Done. Inspect all six crops before extracting values.")
