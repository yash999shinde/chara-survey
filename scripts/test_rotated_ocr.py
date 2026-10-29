from pathlib import Path
import json
import cv2
import numpy as np
import pymupdf
import easyocr

root = Path.cwd()
pdf = root / "data" / "processed" / "20261028_070119_bhiya.pdf"
if not pdf.exists():
    pdf = root / "data" / "uploads" / "20261028_070119_bhiya.pdf"

if not pdf.exists():
    candidates = list((root / "data" / "processed").glob("*.pdf"))
    if not candidates:
        candidates = list((root / "data" / "uploads").glob("*.pdf"))
    if not candidates:
        raise FileNotFoundError("Survey PDF not found")
    pdf = candidates[0]

out = root / "data" / "processed" / "ocr_results"
out.mkdir(parents=True, exist_ok=True)

with pymupdf.open(pdf) as doc:
    pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    image = np.frombuffer(pix.samples, dtype=np.uint8)
    image = image.reshape(pix.height, pix.width, pix.n)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

rotations = {
    "ccw": cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE),
    "cw": cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE),
}

reader = easyocr.Reader(["hi", "en"], gpu=False)

for name, rotated in rotations.items():
    image_path = out / f"survey_rotated_{name}.png"
    cv2.imwrite(str(image_path), rotated)

    print(f"\nOCR on {name.upper()} rotation...")
    detections = reader.readtext(rotated, detail=1, paragraph=False)

    lines = [
        {
            "text": text,
            "confidence": round(float(confidence), 3),
            "needs_review": float(confidence) < 0.65,
            "box": [[int(x), int(y)] for x, y in box]
        }
        for box, text, confidence in detections
    ]

    json_path = out / f"survey_rotated_{name}.json"
    json_path.write_text(
        json.dumps(
            {"source_pdf": pdf.name, "rotation": name, "lines": lines},
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("Image:", image_path)
    print("JSON:", json_path)
    print("Detected text regions:", len(lines))
    print("First results:")
    for item in lines[:12]:
        print(repr(item["text"]), item["confidence"])

print("\nDone. Compare both rotated images and OCR results.")
