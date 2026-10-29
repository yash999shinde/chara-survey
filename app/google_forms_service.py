# -*- coding: utf-8 -*-
"""Dynamic Google Form Inspection, Auto-Mapping, and Automatic Submission Service."""
from __future__ import annotations

import re
import json
import difflib
import datetime
import urllib.request
import urllib.parse
from typing import Any, Optional
from pathlib import Path

# Semantic keyword rules for Marathi and English Google Form questions
FIELD_SEMANTIC_PATTERNS = [
    # Admin fields
    ("taluka", ["तालुका", "taluka"]),
    ("veterinary_hospital", ["पशुवैद्यकीय चिकित्सालय", "पशुवैद्यकीय दवाखाना", "चिकित्सालय", "दवाखाना", "hospital", "dispensary"]),
    ("revenue_circle", ["महसूल मंडळ", "मंडळ", "circle", "revenue_circle"]),
    ("village_name", ["गावाचे नाव", "गावाचे", "गाव", "village"]),
    
    # Farmer personal
    ("farmer_name", ["पशुपालकाचे नाव", "पशुपालकाचे पूर्ण नाव", "पशुपालक", "शेतकऱ्याचे नाव", "शेतकऱ्याचे पूर्ण नाव", "शेतकरी नाव", "नाव", "farmer_name", "farmer"]),
    ("mobile", ["मोबाईल नंबर", "मोबाईल", "फोन नंबर", "फोन", "संपर्क नंबर", "mobile", "phone"]),

    # Cattle (Cows)
    ("cow_small", ["गाय वर्ग - लहान", "गाय - लहान", "गाय लहान", "1 वर्षा खालचे", "cow small", "cow_small"]),
    ("cow_large", ["गाय वर्ग - मोठे", "गाय - मोठे", "गाय मोठे", "1 वर्षा वरचे", "गाईंची संख्या", "cow large", "cow_large"]),

    # Buffaloes
    ("buffalo_small", ["म्हैस वर्ग - लहान", "म्हैस - लहान", "म्हैस लहान", "buffalo small", "buffalo_small"]),
    ("buffalo_large", ["म्हैस वर्ग - मोठे", "म्हैस - मोठे", "म्हैस मोठे", "म्हशींची संख्या", "buffalo large", "buffalo_large"]),

    # Production & Animals
    ("milch_animals", ["पैकी दुभती जनावरे", "दुभती जनावरे", "दुभती", "दुधाळ", "milch"]),
    ("dry_animals", ["भाकड जनावरे", "भाकड", "dry animals", "dry_animals"]),
    ("daily_milk_litres", ["दैनंदिन दूध उत्पादन", "दूध उत्पादन", "दैनंदिन दूध", "दूध (लिटर)", "दूध", "milk"]),
    ("goats", ["शेळ्या", "शेळी", "goats", "goat"]),
    ("sheep_migratory", ["मेंढ्या - स्थलांतरित", "मेंढ्या (स्थलांतरित)", "स्थलांतरित मेंढ्या", "sheep migratory"]),
    ("sheep_confined", ["मेंढ्या - बंधिस्त", "मेंढ्या (बंधिस्त)", "बंधिस्त मेंढ्या", "sheep confined"]),

    # Water & Fodder types
    ("water_availability", ["जनावरांकरिता पाणी उपलब्धता", "पाणी उपलब्धता", "पाणी", "water"]),
    ("fodder_types", ["उपलब्ध चाऱ्याचा प्रकार", "चाऱ्याचा प्रकार", "fodder type"]),
    
    # Fodder quantities
    ("green_fodder_tonnes", ["हिरवा चारा - मे.टन", "हिरवा चारा", "हिरवा", "green fodder"]),
    ("silage_tonnes", ["उपलब्ध मुरघास - मे.टन", "मुरघास - मे.टन", "मुरघास", "silage"]),
    ("dry_fodder_tonnes", ["वाळलेला चारा - मे.टन", "वाळलेला चारा", "वाळलेला", "dry fodder"]),
    ("fodder_for_sale_tonnes", ["सध्या विक्रीकरिता उपलब्ध चारा", "विक्रीकरिता उपलब्ध चारा", "विक्री चारा", "fodder for sale"]),
    ("rabi_area_hectares", ["रबी हंगामात चारा लागवडी योग्य क्षेत्र", "चारा लागवडी योग्य क्षेत्र", "रबी क्षेत्र", "rabi area"]),

    # Irrigation
    ("irrigation_available", ["सिंचन सुविधा उपलब्ध आहे का", "सिंचन सुविधा उपलब्ध", "सिंचन उपलब्धता", "irrigation available"]),
    ("irrigation_types", ["कोणती सिंचन सुविधा उपलब्ध आहे", "सिंचन सुविधा", "सिंचनाचा प्रकार", "irrigation types"]),
    ("irrigation_other", ["इतर सिंचन सुविधा", "इतर सिंचन", "irrigation other"])
]

def clean_google_form_url(url: str) -> tuple[str, str]:
    """
    Normalizes any Google Form URL.
    Returns (view_url, form_response_url).
    """
    url = url.strip()
    if not url:
        raise ValueError("Google Form URL रिकामी असू शकत नाही.")

    # Follow redirects (e.g. for short forms.gle links)
    if "forms.gle/" in url:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            url = resp.geturl()

    # Extract base form ID
    # Patterns: /forms/d/e/<FORM_ID>/viewform or /forms/d/<FORM_ID>/viewform
    m = re.search(r"(https?://docs\.google\.com/forms/d/(?:e/)?[\w\-]+)", url)
    if not m:
        # Fallback to standard replace
        base = re.sub(r"/(?:viewform|formResponse|edit|responses).*$", "", url)
    else:
        base = m.group(1)

    view_url = f"{base}/viewform"
    response_url = f"{base}/formResponse"
    return view_url, response_url

def inspect_google_form(form_url: str) -> dict[str, Any]:
    """
    Fetches the live Google Form, parses FB_PUBLIC_LOAD_DATA_,
    and extracts question metadata with automatic field mapping.
    """
    view_url, response_url = clean_google_form_url(form_url)

    req = urllib.request.Request(
        view_url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8")

    match = re.search(r"FB_PUBLIC_LOAD_DATA_\s*=\s*(.*?);\s*</script>", html)
    if not match:
        raise ValueError("Google Form कॉन्फिगरेशन डेटा (FB_PUBLIC_LOAD_DATA_) सापडला नाही. लिंक तपासा.")

    data = json.loads(match.group(1))
    
    # Form title
    title = ""
    try:
        title = data[1][8] or data[1][0] or "Google Form"
    except Exception:
        title = "Google Form"

    questions_raw = data[1][1] if len(data) > 1 and len(data[1]) > 1 else []
    
    schema = []
    auto_mapping = {}

    for q in questions_raw:
        if not q or len(q) < 5:
            continue
        
        q_title = (q[1] or "").strip()
        entry_id = None
        options = []
        is_required = bool(q[4] and len(q[4]) > 0 and len(q[4][0]) > 2 and q[4][0][2] == 1)

        if q[4] and len(q[4]) > 0:
            entry_id = f"entry.{q[4][0][0]}"
            if len(q[4][0]) > 1 and q[4][0][1]:
                options = [opt[0] for opt in q[4][0][1] if opt and opt[0]]

        if entry_id:
            # Semantic matching to database fields
            mapped_field = match_question_to_field(q_title, options)
            if mapped_field:
                auto_mapping[mapped_field] = entry_id

            schema.append({
                "title": q_title,
                "entry_id": entry_id,
                "options": options,
                "required": is_required,
                "mapped_field": mapped_field or ""
            })

    return {
        "title": title,
        "view_url": view_url,
        "response_url": response_url,
        "questions": schema,
        "mapping": auto_mapping,
        "total_fields": len(schema),
        "mapped_count": len(auto_mapping)
    }

def match_question_to_field(title: str, options: list[str]) -> Optional[str]:
    """Find the best farmer database field for a Google Form question title."""
    title_clean = title.strip()
    title_lower = title_clean.lower()

    # Irrigation section
    if "सिंचन" in title_lower:
        if "इतर" in title_lower:
            return "irrigation_other"
        if "कोणती" in title_lower or "प्रकार" in title_lower:
            return "irrigation_types"
        if "उपलब्ध आहे का" in title_lower or "उपलब्ध" in title_lower:
            return "irrigation_available"
        return "irrigation_types"

    # Farmer Personal Info
    if "पशुपालक" in title_lower or "शेतकऱ्याचे नाव" in title_lower or "पशुपालकाचे नाव" in title_lower or "शेतकरी" in title_lower:
        return "farmer_name"

    if "गावाचे नाव" in title_lower or title_lower == "गाव":
        return "village_name"

    if "मोबाईल" in title_lower or "फोन" in title_lower or "संपर्क" in title_lower:
        return "mobile"

    # Cattle (Cows)
    if "गाय" in title_lower:
        if "लहान" in title_lower or "1 वर्षा खालचे" in title_lower:
            return "cow_small"
        if "मोठे" in title_lower or "1 वर्षा वरचे" in title_lower:
            return "cow_large"
        return "cow_large"

    # Buffaloes
    if "म्हैस" in title_lower:
        if "लहान" in title_lower or "1 वर्षा खालचे" in title_lower:
            return "buffalo_small"
        if "मोठे" in title_lower or "1 वर्षा वरचे" in title_lower:
            return "buffalo_large"
        return "buffalo_large"

    # Milk & small ruminants
    if "दुभती" in title_lower or "दुधाळ" in title_lower:
        return "milch_animals"

    if "भाकड" in title_lower:
        return "dry_animals"

    if "दूध" in title_lower:
        return "daily_milk_litres"

    if "शेळ्या" in title_lower or "शेळी" in title_lower:
        return "goats"

    if "मेंढ्या" in title_lower:
        if "स्थलांतरित" in title_lower:
            return "sheep_migratory"
        if "बंधिस्त" in title_lower:
            return "sheep_confined"
        return "sheep_migratory"

    if "पाणी" in title_lower:
        return "water_availability"

    if "चाऱ्याचा प्रकार" in title_lower:
        return "fodder_types"

    if "हिरवा चारा" in title_lower or ("हिरवा" in title_lower and "मे.टन" in title_lower):
        return "green_fodder_tonnes"

    if "मुरघास" in title_lower:
        return "silage_tonnes"

    if "वाळलेला चारा" in title_lower or ("वाळलेला" in title_lower and "मे.टन" in title_lower):
        return "dry_fodder_tonnes"

    if "विक्री" in title_lower and "चारा" in title_lower:
        return "fodder_for_sale_tonnes"

    if "रबी" in title_lower or "लागवडी योग्य क्षेत्र" in title_lower:
        return "rabi_area_hectares"

    # Administrative
    if "तालुका" in title_lower:
        return "taluka"

    if "पशुवैद्यकीय" in title_lower or "दवाखाना" in title_lower or "चिकित्सालय" in title_lower:
        return "veterinary_hospital"

    if "महसूल" in title_lower:
        return "revenue_circle"

    if "गाव" in title_lower:
        return "village_name"

    if "नाव" in title_lower and "गाव" not in title_lower and "सिंचन" not in title_lower:
        return "farmer_name"

    return None

def build_farmer_payload(farmer: dict[str, Any], schema: list[dict[str, Any]], mapping: dict[str, str]) -> dict[str, Any]:
    """
    Constructs the exact HTTP POST payload for a single farmer record.
    Ensures required fields have valid non-empty values so form submission passes.
    """
    payload = {}
    
    # Reverse map: entry_id -> field_name
    entry_to_field = {v: k for k, v in mapping.items()}

    for item in schema:
        entry_id = item.get("entry_id")
        if not entry_id:
            continue
        
        field_name = entry_to_field.get(entry_id) or item.get("mapped_field")
        val = ""

        if field_name:
            raw_val = farmer.get(field_name)
            if raw_val is not None:
                val = str(raw_val).strip()

        # Handle specific field types and options
        if field_name in ("cow_small", "cow_large", "buffalo_small", "buffalo_large", 
                          "milch_animals", "dry_animals", "goats", "sheep_migratory", "sheep_confined"):
            if not val or val == "None":
                val = "0"
            else:
                try:
                    val = str(int(float(val)))
                except Exception:
                    val = "0"

        elif field_name in ("daily_milk_litres", "green_fodder_tonnes", "silage_tonnes", 
                            "dry_fodder_tonnes", "fodder_for_sale_tonnes", "rabi_area_hectares"):
            if not val or val == "None":
                val = "0"
            else:
                try:
                    num = float(val)
                    val = f"{num:.2f}" if num % 1 != 0 else str(int(num))
                except Exception:
                    val = "0"

        elif field_name == "water_availability":
            val = val if val in ("उपलब्ध", "टंचाई", "नाही") else "उपलब्ध"

        elif field_name == "irrigation_available":
            val = "आहे" if val in ("आहे", "होय", "yes", "true", "1") or farmer.get("irrigation_types") else "नाही"

        elif field_name == "irrigation_types":
            if not val:
                val = "विहीर" if farmer.get("irrigation_available") == "आहे" else ""

        # Default for required fields if still empty
        if not val and item.get("required"):
            if item.get("options"):
                val = item["options"][0]
            else:
                val = "0"

        payload[entry_id] = val

    return payload

def submit_farmer_to_google_form(response_url: str, payload: dict[str, Any]) -> tuple[bool, int, str]:
    """
    Submits a single farmer's payload to the Google Form response endpoint.
    Returns (success, http_code, message).
    """
    try:
        # Handle multi-value fields like checkboxes if list
        encoded_data = urllib.parse.urlencode(payload, doseq=True).encode("utf-8")
        req = urllib.request.Request(
            response_url,
            data=encoded_data,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": response_url.replace("formResponse", "viewform")
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = resp.getcode()
            body = resp.read()[:300].decode("utf-8", errors="ignore")
            # Google Forms typically returns 200 with 'Your response has been recorded'
            is_success = (code == 200)
            return is_success, code, "यशस्वी (200 OK)" if is_success else f"HTTP {code}"

    except urllib.error.HTTPError as he:
        # Some forms redirect (302/303) on submit or return 200
        if he.code in (200, 302, 303):
            return True, he.code, f"यशस्वी (Redirect {he.code})"
        return False, he.code, f"HTTP त्रुटी: {he.code}"
    except Exception as e:
        return False, 500, f"त्रुटी: {str(e)}"

def generate_prefilled_url(view_url: str, payload: dict[str, Any]) -> str:
    """Generates a shareable prefilled Google Form link."""
    # Filter non-empty values
    filtered = {k: v for k, v in payload.items() if v != ""}
    query_str = urllib.parse.urlencode(filtered, doseq=True)
    return f"{view_url}?{query_str}"
