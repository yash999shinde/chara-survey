import sys
import json
from pathlib import Path

import fitz
import easyocr
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SEARCH_DIRS = [
    ROOT / "data" / "uploads",
    ROOT / "data" / "processed",
]
OUTPUT_DIR = ROOT / "data" / "processed" / "ocr_results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def find_pdf():
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        if not p.is_absolute():
            p = ROOT / p
        if p.is_file() and p.suffix.lower() == ".pdf":
            return p
        raise FileNotFoundError(f"PDF not found: {p}")

    preferred = "20261028_070119_bhiya.pdf"
    for folder in SEARCH_DIRS:
        candidate = folder / preferred
        if candidate.is_file():
            return candidate

    for folder in SEARCH_DIRS:
        files = sorted(folder.glob("*.pdf"))
        if files:
            return files[0]

    raise FileNotFoundError(
        "No PDF found in data/uploads or data/processed"
    )

def main():
    pdf_path = find_pdf()
    print(f"PDF: {pdf_path}")

    print("Loading local EasyOCR model...")
    reader = easyocr.Reader(["hi", "en"], gpu=False)

    pages_out = []
    with fitz.open(pdf_path) as pdf:
        for page_no, page in enumerate(pdf, start=1):
            print(f"Processing page {page_no}/{len(pdf)}...")
            pix = page.get_pixmap(dpi=250, alpha=False)
            image = np.frombuffer(
                pix.samples, dtype=np.uint8
            ).reshape(pix.height, pix.width, pix.n)

            detections = reader.readtext(
                image, detail=1, paragraph=False
            )

            lines = []
            for box, text, confidence in detections:
                confidence = float(confidence)
                lines.append({
                    "text": text,
                    "confidence": round(confidence, 3),
                    "needs_review": confidence < 0.65,
                    "box": [
                        [int(x), int(y)] for x, y in box
                    ]
                })

            pages_out.append({
                "page": page_no,
                "lines": lines
            })

    output = OUTPUT_DIR / f"{pdf_path.stem}_ocr.json"
    output.write_text(
        json.dumps(pages_out, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Saved: {output}")
    print("OCR text is unverified; check it against the source PDF.")

if __name__ == "__main__":
    main()
