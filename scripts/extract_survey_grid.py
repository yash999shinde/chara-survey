from pathlib import Path
import os, sys, csv
import cv2
import numpy as np
import pymupdf
import pytesseract
from PIL import Image, ImageOps

ROOT = Path.cwd()
TESS = Path(r"D:\chara-survey-automation-phase1-2\tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = str(TESS)
os.environ["TESSDATA_PREFIX"] = str(TESS.parent / "tessdata")

pdfs = []
for folder in [ROOT / "data" / "uploads", ROOT / "data" / "input", ROOT]:
    if folder.exists():
        pdfs.extend(p for p in folder.glob("*.pdf") if p.is_file())

if not pdfs:
    sys.exit("ERROR: PDF nahi mila. bhiya.pdf ko data\\input mein copy karo.")

pdf = max(pdfs, key=lambda p: p.stat().st_mtime)
out = ROOT / "data" / "processed"
out.mkdir(parents=True, exist_ok=True)

csv_path = out / "survey_table_cells.csv"
preview_path = out / "survey_table_preview.png"
results = []

def group_lines(values, gap=3):
    groups = []
    for v in values:
        if not groups or int(v) > groups[-1][-1] + gap:
            groups.append([int(v)])
        else:
            groups[-1].append(int(v))
    return [int(np.median(g)) for g in groups]

print("PDF:", pdf)

with pymupdf.open(pdf) as doc:
    for page_no, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

        # Try the two common orientations and keep the OCR with more recognized text.
        candidates = []
        for angle in (0, 90, 270):
            rotated = image.rotate(angle, expand=True) if angle else image.copy()
            gray = cv2.cvtColor(np.array(rotated), cv2.COLOR_RGB2GRAY)
            sample = pytesseract.image_to_string(
                gray, lang="mar+eng", config="--psm 11"
            )
            candidates.append((len(sample.strip()), angle, rotated, sample))

        _, angle, image, sample_text = max(candidates, key=lambda x: x[0])
        print(f"\nPage {page_no}: selected rotation={angle} degrees")
        print("OCR sample:")
        print(sample_text[:1500])

        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 31, 15
        )

        h, w = binary.shape
        hk = cv2.getStructuringElement(
            cv2.MORPH_RECT, (max(30, w // 35), 1)
        )
        horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, hk)
        projection = (horizontal > 0).sum(axis=1)
        ys = group_lines(
            np.where(projection > max(100, int(w * 0.20)))[0], 3
        )

        # Report detected horizontal lines before guessing the table's columns.
        print("Horizontal line positions:", ys[:100])
        preview = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        for y in ys:
            cv2.line(preview, (0, y), (w - 1, y), (0, 0, 255), 2)
        cv2.imwrite(str(preview_path), preview)

        # OCR each band between detected lines. These are candidate bands,
        # not confirmed farmer records yet.
        for row_no, (y0, y1) in enumerate(zip(ys, ys[1:]), start=1):
            if y1 - y0 < 12:
                continue
            crop = gray[y0:y1, :]
            text = pytesseract.image_to_string(
                Image.fromarray(crop), lang="mar+eng", config="--psm 6"
            ).strip()
            if text:
                results.append({
                    "page": page_no,
                    "candidate_band": row_no,
                    "top_px": y0,
                    "bottom_px": y1,
                    "ocr_text": text,
                    "needs_human_review": "YES"
                })

if not results:
    sys.exit(
        "No table bands confidently detected. Preview image may help diagnose "
        "the scan; no farmer data has been saved."
    )

with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
    writer.writeheader()
    writer.writerows(results)

print("\nCandidate bands:", len(results))
print("Diagnostic CSV:", csv_path)
print("Preview image:", preview_path)
print("These are OCR bands, NOT approved farmer records.")
