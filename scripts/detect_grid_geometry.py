import os
import json
import fitz  # PyMuPDF
import cv2
import numpy as np

PDF_PATH = r"data\uploads\4c6d29186a5840f3b14bc5f17240642c.pdf"
OUTPUT_IMG = r"data\processed\annotated_grid_preview.png"
OUTPUT_JSON = r"data\processed\detected_grid_structure.json"

def render_pdf_page(pdf_path, page_num=0, rotation=90, zoom=2.0):
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    mat = fitz.Matrix(zoom, zoom).prerotate(rotation)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    if pix.n == 3:
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    else:
        img_gray = img
        img_bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    doc.close()
    return img_bgr, img_gray

def extract_grid_lines(gray_img):
    _, thresh = cv2.threshold(gray_img, 200, 255, cv2.THRESH_BINARY_INV)

    h_kernel_len = max(gray_img.shape[1] // 40, 20)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_len, 1))
    h_lines = cv2.erode(thresh, h_kernel, iterations=1)
    h_lines = cv2.dilate(h_lines, h_kernel, iterations=2)

    v_kernel_len = max(gray_img.shape[0] // 40, 20)
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_kernel_len))
    v_lines = cv2.erode(thresh, v_kernel, iterations=1)
    v_lines = cv2.dilate(v_lines, v_kernel, iterations=2)

    return h_lines, v_lines, thresh

def find_line_positions(line_mask, axis=0, min_gap=15):
    proj = np.sum(line_mask, axis=axis)
    threshold = np.max(proj) * 0.20
    indices = np.where(proj > threshold)[0]
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
        print(f"[ERROR] PDF not found at {PDF_PATH}")
        return

    bgr, gray = render_pdf_page(PDF_PATH, rotation=90, zoom=2.0)
    h_lines, v_lines, thresh = extract_grid_lines(gray)

    y_lines = find_line_positions(h_lines, axis=1, min_gap=18)
    x_lines = find_line_positions(v_lines, axis=0, min_gap=18)

    print(f"[+] Table Lines Detected: {len(y_lines)} horizontal rows, {len(x_lines)} vertical columns")

    annotated = bgr.copy()
    candidate_rows = []

    for r in range(len(y_lines) - 1):
        y1, y2 = y_lines[r], y_lines[r + 1]
        row_height = y2 - y1
        if row_height < 15:
            continue

        row_cells = []
        total_ink = 0
        for c in range(len(x_lines) - 1):
            x1, x2 = x_lines[c], x_lines[c + 1]
            col_width = x2 - x1
            if col_width < 15:
                continue

            pad_y = max(2, int(row_height * 0.08))
            pad_x = max(2, int(col_width * 0.08))
            cell_roi = thresh[y1 + pad_y : y2 - pad_y, x1 + pad_x : x2 - pad_x]
            ink_count = int(cv2.countNonZero(cell_roi))
            total_ink += ink_count

            row_cells.append({
                "col_index": len(row_cells),
                "bbox": [x1, y1, x2, y2],
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

        cv2.putText(annotated, f"R{r['row_index']} ({r['total_ink']})", 
                    (max(5, x_lines[0] - 120), int((y1 + y2) / 2)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)

    for r in candidate_rows[:12]:
        print(f"Row {r['row_index']:02d}: Y=[{r['y_range'][0]}, {r['y_range'][1]}], Ink Pixels = {r['total_ink']}")

    cv2.imwrite(OUTPUT_IMG, annotated)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(candidate_rows, f, indent=2)
    print(f"[SUCCESS] Preview saved to: {OUTPUT_IMG}")
    print(f"[SUCCESS] Grid JSON saved to: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
