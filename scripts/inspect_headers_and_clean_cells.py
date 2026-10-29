import os
import json
import cv2
import numpy as np
import pymupdf
import pytesseract
from PIL import Image

TESSERACT_EXE = r"D:\chara-survey-automation-phase1-2\tesseract.exe"
TESSDATA_DIR = r"D:\chara-survey-automation-phase1-2\tessdata"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
os.environ["TESSDATA_PREFIX"] = TESSDATA_DIR

PDF_PATH = r"data\uploads\4c6d29186a5840f3b14bc5f17240642c.pdf"
GRID_JSON_PATH = r"data\processed\detected_grid_structure.json"
DEBUG_CELL_DIR = r"data\processed\debug_cells"
os.makedirs(DEBUG_CELL_DIR, exist_ok=True)

MARATHI_TO_ENG = str.maketrans({'०':'0','१':'1','२':'2','३':'3','४':'4','५':'5','६':'6','७':'7','८':'8','९':'9'})

def render_page(pdf_path, rotation=90, zoom=2.0):
    doc = pymupdf.open(pdf_path)
    page = doc[0]
    mat = pymupdf.Matrix(zoom, zoom).prerotate(rotation)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if pix.n == 3 else img
    doc.close()
    return gray

def clean_cell_image(cell_crop):
    """Remove outer grid line residue and clean contrast."""
    h, w = cell_crop.shape
    if h <= 8 or w <= 8:
        return cell_crop

    # Shave 4px inside borders to drop table lines
    inner = cell_crop[4:h-4, 4:w-4]
    
    # Contrast adjustment via CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(inner)

    # Otsu thresholding
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 8px white border padding
    padded = cv2.copyMakeBorder(thresh, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=255)
    return padded

def main():
    with open(GRID_JSON_PATH, "r", encoding="utf-8") as f:
        grid = json.load(f)

    gray = render_page(PDF_PATH, rotation=90, zoom=2.0)

    # 1. OCR Headers (Row 00 and 01) to verify columns
    print("=== TABLE HEADER RECOGNITION (Row 0 & 1) ===")
    for header_row_idx in [0, 1]:
        h_row = [r for r in grid if r["row_index"] == header_row_idx]
        if not h_row:
            continue
        print(f"\n--- Header Band {header_row_idx} ---")
        for c in h_row[0]["cells"]:
            x1, y1, x2, y2 = c["bbox"]
            crop = gray[y1+2:y2-2, x1+2:x2-2]
            if crop.size == 0:
                continue
            cleaned = clean_cell_image(crop)
            txt = pytesseract.image_to_string(cleaned, lang="mar+eng", config="--psm 6").strip().replace("\n", " ")
            print(f"Col {c['col_index']} (X: {x1}-{x2}): '{txt}'")

    # 2. Extract and save test cells for Row 1 of data (Grid Row index 2)
    row_2 = [r for r in grid if r["row_index"] == 2][0]
    print("\n=== SAVING CLEANED CELL SAMPLES FOR FIRST FARMER ROW ===")
    for c in row_2["cells"]:
        x1, y1, x2, y2 = c["bbox"]
        crop = gray[y1:y2, x1:x2]
        cleaned = clean_cell_image(crop)
        
        filename = f"row2_col{c['col_index']}.png"
        out_path = os.path.join(DEBUG_CELL_DIR, filename)
        cv2.imwrite(out_path, cleaned)

        # Run OCR test on cleaned crop
        txt_mar = pytesseract.image_to_string(cleaned, lang="mar", config="--psm 6").strip()
        txt_eng = pytesseract.image_to_string(cleaned, lang="eng", config="--psm 6 -c tessedit_char_whitelist=0123456789.-").strip()
        print(f"Col {c['col_index']}: mar='{txt_mar}', num='{txt_eng}' -> saved to {filename}")

if __name__ == "__main__":
    main()
