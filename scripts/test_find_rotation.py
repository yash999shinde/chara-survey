# -*- coding: utf-8 -*-
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pymupdf
from pipeline.extractor import find_best_rotation

pdf_path = PROJECT_ROOT / "data" / "uploads" / "4c6d29186a5840f3b14bc5f17240642c.pdf"
doc = pymupdf.open(str(pdf_path))
rot, gray = find_best_rotation(doc)
print(f"Detected rotation: {rot}, Shape: {gray.shape}")
