import os
import sys
from pathlib import Path

# Common Windows install locations
candidates = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    r"C:\tools\tesseract\tesseract.exe"
]

tess_path = None
for p in candidates:
    if os.path.isfile(p):
        tess_path = p
        break

if not tess_path:
    print("[!] Tesseract binary automatically nahi mili. Check karein ki Tesseract Windows par installed hai ya nahi.")
else:
    print(f"[+] Found Tesseract at: {tess_path}")
    
    # 1. Update pipeline/extractor.py
    ext_file = Path("pipeline/extractor.py")
    if ext_file.exists():
        txt = ext_file.read_text(encoding="utf-8")
        prefix = f'import pytesseract\npytesseract.pytesseract.tesseract_cmd = r"{tess_path}"\n'
        if "tesseract_cmd" not in txt:
            txt = prefix + txt
        else:
            import re
            txt = re.sub(r'pytesseract\.pytesseract\.tesseract_cmd\s*=.*', f'pytesseract.pytesseract.tesseract_cmd = r"{tess_path}"', txt)
        ext_file.write_text(txt, encoding="utf-8")
        print("[+] Updated pipeline/extractor.py with Tesseract path.")

    # 2. Update app/app.py
    app_file = Path("app/app.py")
    if app_file.exists():
        txt = app_file.read_text(encoding="utf-8")
        prefix = f'import pytesseract\npytesseract.pytesseract.tesseract_cmd = r"{tess_path}"\n'
        if "tesseract_cmd" not in txt:
            txt = prefix + txt
        else:
            import re
            txt = re.sub(r'pytesseract\.pytesseract\.tesseract_cmd\s*=.*', f'pytesseract.pytesseract.tesseract_cmd = r"{tess_path}"', txt)
        app_file.write_text(txt, encoding="utf-8")
        print("[+] Updated app/app.py with Tesseract path.")