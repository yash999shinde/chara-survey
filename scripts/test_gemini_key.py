# -*- coding: utf-8 -*-
from google import genai
from google.genai import types

API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=API_KEY)

try:
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents="Say 'Hello Gemini Marathi OCR!'"
    )
    print("Response:", response.text)
except Exception as e:
    print("Error:", e)
