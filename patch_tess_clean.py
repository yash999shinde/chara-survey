from pathlib import Path
import os

ext_path = Path("pipeline/extractor.py")
content = ext_path.read_text(encoding="utf-8")

# Possible locations
tess_locations = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")
]

found = None
for loc in tess_locations:
    if os.path.isfile(loc):
        found = loc.replace("\\", "/")
        break

if not found:
    found = "C:/Program Files/Tesseract-OCR/tesseract.exe"

lines = content.splitlines()
new_lines = []
inserted = False

for line in lines:
    if "tesseract_cmd" in line:
        new_lines.append(f'pytesseract.pytesseract.tesseract_cmd = r"{found}"')
        inserted = True
    else:
        new_lines.append(line)

if not inserted:
    # Top par add karein import ke baad
    final_code = f'import pytesseract\npytesseract.pytesseract.tesseract_cmd = r"{found}"\n' + "\n".join(new_lines)
else:
    final_code = "\n".join(new_lines)

ext_path.write_text(final_code, encoding="utf-8")
print(f"[SUCCESS] Tesseract binary locked to: {found}")