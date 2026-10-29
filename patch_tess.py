from pathlib import Path
import os

ext_path = Path("pipeline/extractor.py")
content = ext_path.read_text(encoding="utf-8")

# Common windows paths
tess_locations = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")
]

found = None
for loc in tess_locations:
    if os.path.isfile(loc):
        found = loc
        break

if not found:
    found = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

patch = f"""import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"{found}"
"""

if 'pytesseract.pytesseract.tesseract_cmd' not in content:
    content = patch + content
    ext_path.write_text(content, encoding="utf-8")
    print(f"[SUCCESS] Tesseract path set to: {found}")
else:
    import re
    content = re.sub(r'pytesseract\.pytesseract\.tesseract_cmd\s*=.*', f'pytesseract.pytesseract.tesseract_cmd = r"{found}"', content)
    ext_path.write_text(content, encoding="utf-8")
    print(f"[SUCCESS] Tesseract path updated to: {found}")