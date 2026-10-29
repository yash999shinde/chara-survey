from pathlib import Path
import json
import cv2
import easyocr

root = Path.cwd()
folder = root / "data" / "processed" / "ocr_results"
image_path = folder / "survey_headers_and_rows.png"

if not image_path.exists():
    raise FileNotFoundError(f"Missing image: {image_path}")

image = cv2.imread(str(image_path))
if image is None:
    raise RuntimeError("Could not open survey image")

reader = easyocr.Reader(["hi", "en"], gpu=False)
detections = reader.readtext(image, detail=1, paragraph=False)

result = []
for box, text, confidence in detections:
    confidence = float(confidence)
    result.append({
        "text": text,
        "confidence": round(confidence, 3),
        "needs_review": confidence < 0.65,
        "box": [[int(x), int(y)] for x, y in box]
    })

output = folder / "survey_headers_ocr.json"
output.write_text(
    json.dumps(result, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("Detected text regions:", len(result))
print("Saved:", output)
print("\nFirst 40 detections:")
for item in result[:40]:
    print(repr(item["text"]), item["confidence"])
