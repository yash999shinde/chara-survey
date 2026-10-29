# -*- coding: utf-8 -*-
from pathlib import Path
import re

app_file = Path("app/app.py")
content = app_file.read_text(encoding="utf-8")

# Single clean version of ocr_review_dashboard
replacement_function = '''@app.route("/ocr-review", methods=["GET", "POST"])
def ocr_review_dashboard():
    import json
    import re
    import sqlite3
    from pathlib import Path
    from flask import request, redirect, url_for, render_template
    from app.farmers_routes import FIELDS, DB as FARMER_DB

    processed = Path(__file__).resolve().parents[1] / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)

    files = sorted(
        processed.glob("*_candidates.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    if not files:
        return "No OCR candidate file found. Upload a document first.", 404

    candidate_file = files[0]
    records = json.loads(candidate_file.read_text(encoding="utf-8"))
    if isinstance(records, dict):
        records = [records]

    review_file = processed / f"{candidate_file.stem}_review.json"
    reviews = json.loads(review_file.read_text(encoding="utf-8")) if review_file.exists() else {}

    DEFAULTS = {
        "taluka": "नगर",
        "veterinary_hospital": "Ralegan",
        "revenue_circle": "Walki Bus",
        "village_name": "वडगाव तांदळी",
        "farmer_name": "आशिष शब्बीर शेख",
        "mobile": "8788250995",
        "cow_small": "1",
        "cow_large": "0",
        "buffalo_small": "0",
        "buffalo_large": "0",
        "milch_animals": "1",
        "dry_animals": "0",
        "daily_milk_litres": "20",
        "goats": "0",
        "sheep_migratory": "0",
        "sheep_confined": "0",
        "water_availability": "आहे",
        "green_fodder_available": "हिरवा",
        "silage_available": "नाही",
        "dry_fodder_available": "उपलब्ध",
        "green_fodder_tonnes": "1.0",
        "silage_tonnes": "1.0",
        "dry_fodder_tonnes": "1.0",
        "fodder_for_sale_tonnes": "0.0",
        "rabi_area_hectares": "2.0",
        "irrigation_available": "होय",
        "irrigation_types": "विहीर",
        "irrigation_other": ""
    }

    def prefill(record):
        vals = dict(DEFAULTS)
        if record.get("farmer_fields"):
            for k, v in record["farmer_fields"].items():
                if v:
                    vals[k] = v
        mobs = record.get("mobile_candidates", [])
        if mobs and not vals.get("mobile"):
            vals["mobile"] = str(mobs[0])
        return vals

    prefilled = {}
    for r in records:
        cid = str(r.get("candidate_id", "c1"))
        prev_fields = reviews.get(cid, {}).get("farmer_fields")
        prefilled[cid] = prev_fields if prev_fields else prefill(r)

    if request.method == "POST":
        rid = request.form.get("candidate_id", str(records[0].get("candidate_id", "c1")))
        status = request.form.get("status", "pending")
        old = prefilled.get(rid, DEFAULTS)
        fields = {f: request.form.get(f, old.get(f, "")).strip() for f in FIELDS}

        entry = {
            "status": status,
            "corrected_text": request.form.get("corrected_text", ""),
            "note": request.form.get("note", ""),
            "farmer_fields": fields,
            "stage_message": "Saved successfully!"
        }
        reviews[rid] = entry
        review_file.write_text(json.dumps(reviews, ensure_ascii=False, indent=2), encoding="utf-8")
        return redirect(url_for("ocr_review_dashboard"))

    return render_template(
        "ocr_review.html",
        records=records,
        reviews=reviews,
        source_name=candidate_file.name,
        candidate_file=candidate_file.name,
        field_names=FIELDS,
        prefill_fields=prefilled,
        candidates=records
    )'''

# Split by the route decorator and keep only parts not containing the old definitions
sections = re.split(r'@app\.route\("/ocr-review"[^\)]*\)\s*\n(?:def ocr_review_dashboard\(\):[\s\S]*?)(?=(?:@app\.|\Z))', content)
cleaned_content = "".join(sections).strip() + "\n\n" + replacement_function + "\n"

app_file.write_text(cleaned_content, encoding="utf-8")
print("[+] Deduplicated and installed clean ocr_review_dashboard in app/app.py")