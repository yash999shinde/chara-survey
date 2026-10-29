# -*- coding: utf-8 -*-
"""OCR Engine for Marathi & English Text Extraction."""
from pathlib import Path
import os
import re
import cv2
import numpy as np
import pymupdf
import pytesseract
from PIL import Image, ImageOps

from pipeline.ocr_config import configure_tesseract, is_tesseract_available

SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
SUPPORTED_DOCUMENTS = SUPPORTED_IMAGES | {".pdf"}
MARATHI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

def clean_ocr_text(text: str) -> str:
    if not text:
        return ""
    text = text.translate(MARATHI_DIGITS)
    return text.strip()

def detect_best_page_rotation(gray: np.ndarray, language: str = "mar+eng") -> tuple[int, np.ndarray]:
    """Test rotations (0, 90, 180, 270) and choose the one with highest Marathi/English readability."""
    rotations = [
        (0, gray),
        (90, cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE)),
        (180, cv2.rotate(gray, cv2.ROTATE_180)),
        (270, cv2.rotate(gray, cv2.ROTATE_90_COUNTERCLOCKWISE))
    ]
    best_deg = 0
    best_score = -1
    best_img = gray

    for deg, rot_img in rotations:
        rh, rw = rot_img.shape
        # Sample center region
        sample = rot_img[int(rh * 0.1):int(rh * 0.7), int(rw * 0.1):int(rw * 0.8)]
        if sample.shape[0] > 600:
            scale = 600.0 / sample.shape[0]
            sample = cv2.resize(sample, (int(sample.shape[1] * scale), 600))

        try:
            txt = pytesseract.image_to_string(sample, lang=language, config="--psm 6")
            dev_chars = len(re.findall(r"[\u0900-\u097F]", txt))
            keywords = sum(6 for kw in ["शेतकरी", "पशुपालक", "गाव", "तालुका", "दूध", "चारा", "मोबाईल", "संख्या", "म्हशी", "गायी"] if kw in txt)
            mobiles = len(re.findall(r"[6-9][0-9]{9}", txt.translate(MARATHI_DIGITS))) * 12
            score = dev_chars + keywords + mobiles
            if score > best_score:
                best_score = score
                best_deg = deg
                best_img = rot_img
        except Exception:
            continue

    return best_deg, best_img

def extract_text(file_path: str | Path, language: str = "mar+eng") -> dict:
    """Extract text from PDF or image using Tesseract OCR with automatic orientation detection."""
    path = Path(file_path)
    configure_tesseract()

    if not is_tesseract_available():
        raise RuntimeError(f"Tesseract OCR executable not found. Please install Tesseract or configure TESSERACT_CMD.")
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix.lower() not in SUPPORTED_DOCUMENTS:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    pages = []

    if path.suffix.lower() == ".pdf":
        with pymupdf.open(path) as document:
            if document.page_count == 0:
                raise ValueError("PDF contains no pages.")

            for page_idx, page in enumerate(document, start=1):
                # Try high-res pixmap
                pix = page.get_pixmap(dpi=200, alpha=False)
                img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
                if pix.n == 4:
                    img_np = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
                gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY) if pix.n >= 3 else img_np

                deg, rotated_gray = detect_best_page_rotation(gray, language=language)
                text = pytesseract.image_to_string(rotated_gray, lang=language, config="--psm 3")
                pages.append({
                    "page": page_idx,
                    "rotation": deg,
                    "text": clean_ocr_text(text),
                })
    else:
        pil_img = Image.open(path)
        pil_img = ImageOps.exif_transpose(pil_img).convert("RGB")
        img_np = np.array(pil_img)
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        deg, rotated_gray = detect_best_page_rotation(gray, language=language)
        text = pytesseract.image_to_string(rotated_gray, lang=language, config="--psm 3")
        pages.append({
            "page": 1,
            "rotation": deg,
            "text": clean_ocr_text(text),
        })

    full_text = "\n\n".join(
        f"--- Page {p['page']} ---\n{p['text']}" for p in pages
    )

    return {
        "source_file": path.name,
        "language": language,
        "page_count": len(pages),
        "pages": pages,
        "full_text": full_text,
    }
