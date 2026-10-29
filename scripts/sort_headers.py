# -*- coding: utf-8 -*-
import json
from pathlib import Path

BASE_DIR = Path(r"D:\chara-survey-automation-phase1-2\chara-survey-automation")
JSON_PATH = BASE_DIR / "data" / "processed" / "ocr_results" / "survey_headers_ocr.json"

with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

# Sort by x coordinate
filtered = []
for item in data:
    box = item["box"]
    # box is [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
    min_x = min(pt[0] for pt in box)
    max_x = max(pt[0] for pt in box)
    min_y = min(pt[1] for pt in box)
    max_y = max(pt[1] for pt in box)
    
    filtered.append({
        "text": item["text"],
        "conf": item["confidence"],
        "bbox": [min_x, min_y, max_x, max_y]
    })

filtered.sort(key=lambda d: (d["bbox"][1] // 30, d["bbox"][0]))

with open(BASE_DIR / "data" / "processed" / "headers_sorted.json", "w", encoding="utf-8") as f:
    json.dump(filtered, f, ensure_ascii=False, indent=2)

print(f"Total detections: {len(filtered)}")
