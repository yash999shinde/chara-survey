# -*- coding: utf-8 -*-
import os
import json
import pymupdf
import cv2
import numpy as np

PDF_PATH = r"data\uploads\4c6d29186a5840f3b14bc5f17240642c.pdf"
OUTPUT_IMG = r"data\processed\annotated_grid_270.png"
OUTPUT_JSON = r"data\processed\detected_grid_structure_270.json"

def render_page(pdf_path, rotation=270, zoom=2.0):
    doc = pymupdf.open(pdf_path)
    page = doc[0]
    mat = pymupdf.Matrix(zoom, zoom).prerotate(rotation)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR) if pix.n == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    doc.close()
    return bgr, gray

def extract_grid(gray):
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    # Horizontal lines (rows)
    h_len = max(gray.shape[1] // 30, 25)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_len, 1))
    h_lines = cv2.erode(thresh, h_kernel, iterations=1)
    h_lines = cv2.dilate(h_lines, h_kernel, iterations=2)

    # Vertical lines (columns)
    v_len = max(gray.shape[0] // 30, 25)
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_len))
    v_lines = cv2.erode(thresh, v_kernel, iterations=1)
    v_lines = cv2.dilate(v_lines, v_kernel, iterations=2)

    return h_lines, v_lines, thresh

def find_cluster_positions(line_mask, axis, min_gap=15):
    proj = np.sum(line_mask, axis=axis)
    thresh = np.max(proj) * 0.18
    indices = np.where(proj > thresh)[0]
    if len(indices) == 0:
        return []
    lines = []
    cluster = [indices[0]]
    for idx in indices[1:]:
        if idx - cluster[-1] <= min_gap:
            cluster.append(idx)
        else:
            lines.append(int(np.mean(cluster)))
            cluster = [idx]
    if cluster:
        lines.append(int(np.mean(cluster)))
    return lines

def main():
    if not os.path.exists(PDF_PATH):
        print(f"[ERROR] PDF not found: {PDF_PATH}")
        return

    bgr, gray = render_page(PDF_PATH, rotation=270, zoom=2.0)
    h_lines, v_lines, thresh = extract_grid(gray)

    y_lines = find_cluster_positions(h_lines, axis=1, min_gap=16)
    x_lines = find_cluster_positions(v_lines, axis=0, min_gap=16)

    print(f"[*] Detected {len(y_lines)} horizontal grid rows and {len(x_lines)} vertical column dividers at 270 deg")

    annotated = bgr.copy()
    candidate_rows = []

    for r in range(len(y_lines) - 1):
        y1, y2 = y_lines[r], y_lines[r + 1]
        row_h = y2 - y1
        if row_h < 15:
            continue

        row_cells = []
        total_ink = 0
        for c in range(len(x_lines) - 1):
            x1, x2 = x_lines[c], x_lines[c + 1]
            col_w = x2 - x1
            if col_w < 15:
                continue

            cell_roi = thresh[y1+2:y2-2, x1+2:x2-2]
            ink_count = int(cv2.countNonZero(cell_roi))
            total_ink += ink_count

            row_cells.append({
                "col_index": len(row_cells),
                "bbox": [x1, y1, x2, y2],
                "width": col_w,
                "height": row_h,
                "ink_pixels": ink_count
            })

        candidate_rows.append({
            "row_index": len(candidate_rows),
            "y_range": [y1, y2],
            "total_ink": total_ink,
            "cells": row_cells
        })

    for r in candidate_rows:
        y1, y2 = r["y_range"]
        for c in r["cells"]:
            x1, y1_c, x2, y2_c = c["bbox"]
            color = (0, 255, 0) if c["ink_pixels"] > 35 else (255, 120, 0)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 1)

        cv2.putText(annotated, f"R{r['row_index']}", 
                    (max(5, x_lines[0] - 60), int((y1 + y2) / 2)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)

    print("\n=== TOP ROWS INK DISTRIBUTION ===")
    for r in candidate_rows[:12]:
        print(f"Row {r['row_index']:02d}: Y=[{r['y_range'][0]}, {r['y_range'][1]}], Cells={len(r['cells'])}, Ink={r['total_ink']}")

    cv2.imwrite(OUTPUT_IMG, annotated)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(candidate_rows, f, indent=2)

    print(f"\n[+] Saved annotated preview: {OUTPUT_IMG}")
    print(f"[+] Saved 270 deg grid structure: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
    