import os
import json
from pathlib import Path
import pymupdf
from google import genai
from google.genai import types

API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=API_KEY)

upload_dir = Path("data/uploads")
pdfs = sorted(upload_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)

if not pdfs:
    print("[!] No PDF found in data/uploads")
    exit(1)

target_pdf = pdfs[0]
print(f"[*] Processing file: {target_pdf.name}")

doc = pymupdf.open(str(target_pdf))
all_farmers = []

prompt = """
You are an expert OCR specialist for Marathi government survey forms.
The provided image is a page from a handwritten survey table of cattle owners/farmers.
Extract all valid data rows into a JSON array following this exact schema:
[
  {
    "farmer_name": "शेतकऱ्याचे नाव (Devanagari text only, no English artifacts)",
    "mobile": "10-digit mobile number string (empty string if missing)",
    "cow_small": 0,
    "cow_large": 0,
    "buffalo_small": 0,
    "buffalo_large": 0,
    "milch_animals": 0,
    "daily_milk_litres": 0,
    "goats": 0,
    "green_fodder_tonnes": 0.0,
    "dry_fodder_tonnes": 0.0
  }
]
Ignore scanner logos, watermarks (e.g. OKENScanner), and headers.
Ensure numbers are integer/float and text is valid Marathi Devanagari.
Output ONLY the raw JSON array.
"""

for page_idx, page in enumerate(doc, 1):
    print(f"[*] Scanning Page {page_idx}...")
    pix = page.get_pixmap(dpi=200)
    img_bytes = pix.tobytes("jpeg")

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[
            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
            prompt
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )

    try:
        data = json.loads(response.text)
        if isinstance(data, list):
            all_farmers.extend(data)
        else:
            all_farmers.append(data)
    except Exception as e:
        print(f"[!] JSON parsing error on page {page_idx}: {e}")

out_path = Path("data/processed") / f"{target_pdf.stem}_gemini_clean.json"
out_path.parent.mkdir(parents=True, exist_ok=True)

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(all_farmers, f, ensure_ascii=False, indent=2)

print(f"\n[+] Successfully extracted {len(all_farmers)} records!")
print(f"[+] Saved to: {out_path}\n")
print(json.dumps(all_farmers[:3], ensure_ascii=False, indent=2))