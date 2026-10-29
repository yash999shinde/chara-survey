# -*- coding: utf-8 -*-
import time
import json
import pymupdf
from pathlib import Path
from google import genai
from google.genai import types

PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=API_KEY)

pdf_path = PROJECT_ROOT / "data" / "uploads" / "4c6d29186a5840f3b14bc5f17240642c.pdf"

doc = pymupdf.open(str(pdf_path))
page = doc[0]

# Render page rotated 270 (landscape orientation where table is upright)
mat = pymupdf.Matrix(2.0, 2.0).prerotate(270)
pix = page.get_pixmap(matrix=mat, alpha=False)
img_bytes = pix.tobytes("jpeg")
doc.close()

prompt = """
You are an expert document reading AI specialized in handwritten and printed Marathi government fodder-survey forms (चारा टंचाई सर्वेक्षण तक्ता).
Analyze the attached survey table image carefully.

Extract the administrative header information and all farmer rows from the table into this JSON structure:

{
  "taluka": "तालुका (उदा. नगर)",
  "veterinary_hospital": "पशुवैद्यकीय दवाखाना (उदा. राळेगण किंवा वाळकी)",
  "revenue_circle": "महसूल मंडळ (उदा. वाळकी)",
  "village_name": "गावाचे नाव (उदा. वडगाव तांदळी)",
  "farmers": [
    {
      "sr_no": 1,
      "farmer_name": "शेतकऱ्याचे संपूर्ण नाव (मराठी देवनागरी अक्षरात, उदा. आशिष शब्बीर शेख)",
      "mobile": "10 अंकी मोबाईल क्रमांक (उदा. 9096515858)",
      "cow_large": 0,
      "cow_small": 0,
      "buffalo_large": 0,
      "buffalo_small": 0,
      "milch_animals": 0,
      "dry_animals": 0,
      "daily_milk_litres": 0.0,
      "goats": 0,
      "green_fodder_tonnes": 0.0,
      "silage_tonnes": 0.0,
      "dry_fodder_tonnes": 0.0,
      "irrigation_available": "आहे/नाही",
      "irrigation_types": "विहीर/बोअरवेल/इतर"
    }
  ]
}

Important extraction rules:
1. Header: The village name is वडगाव तांदळी (or वडगाव), Taluka is नगर, Hospital is राळेगण / वाळकी, Circle is वाळकी. Extract these accurately.
2. Farmer Names: Read the handwritten Marathi names with 100% exact fidelity in Devanagari script (e.g. आशिष शब्बीर शेख, समीर जमाल शेख, लतीफ जमाल शेख, इब्राहिम रुबाब शेख, नबाब रुबाब शेख, बशीर कमाल शेख).
3. Mobile Numbers: Extract the full 10-digit mobile number, converting Marathi numerals (०१२३४५६७८९) to standard digits.
4. Livestock & Fodder: Extract cow, buffalo, milch animals, milk yield, goats, and fodder quantities as accurate numbers. Pay special attention to Marathi numerals (e.g. २० is 20, not 2). In row 6, goats count is 20.
5. Irrigation: In the last column, if 'विहीर' is written or checked, set "irrigation_available": "आहे" and "irrigation_types": "विहीर".
6. Only return populated farmer rows from the table. Do not include blank rows.
7. Output ONLY valid JSON, without any markdown formatting or extra commentary.
"""

CANDIDATE_MODELS = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]

for model_name in CANDIDATE_MODELS:
    for attempt in range(1, 3):
        try:
            print(f"Trying {model_name} (attempt {attempt})...")
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            out_file = PROJECT_ROOT / "data" / "processed" / "gemini_extracted_farmers.json"
            out_file.write_text(response.text, encoding="utf-8")
            print(f"SUCCESS with {model_name}! Saved to {out_file}")
            break
        except Exception as e:
            print(f"Model {model_name} attempt {attempt} failed: {e}")
            if attempt < 2:
                time.sleep(2)
    else:
        continue
    break
