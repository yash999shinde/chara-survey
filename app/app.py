# -*- coding: utf-8 -*-
"""Main Flask Application for Chara Survey Automation."""
from __future__ import annotations

import os
import sys
import io
import csv
import json
import uuid
import hashlib
import datetime
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import (
    Flask,
    request,
    redirect,
    url_for,
    render_template,
    flash,
    send_file,
    Response,
    abort
)
import openpyxl

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.ocr_config import configure_tesseract, is_tesseract_available
from pipeline.extractor import extract_document
from ingestion.tabular import read_tabular
from mapping.fields import load_mapping, map_columns, canonical_to_db_record
from validation.engine import load_rules, validate_records
from app.db import (
    init_db,
    get_connection,
    insert_farmer,
    get_all_farmers,
    get_dashboard_counts,
    is_file_already_imported,
    get_latest_batch_id,
    log_upload_audit,
    DB_PATH
)
from app.farmers_routes import farmers_bp
from app.google_forms_routes import google_forms_bp

UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CONFIG_DIR = PROJECT_ROOT / "config"

for d in [UPLOAD_DIR, PROCESSED_DIR]:
    d.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chara-survey-secret-key-2026")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB max bulk upload

# Register blueprints
app.register_blueprint(farmers_bp)
app.register_blueprint(google_forms_bp)

# Auto-initialize DB and OCR
init_db()
configure_tesseract()

@app.route("/")
def index():
    return redirect(url_for("farmers.list_farmers"))

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "GET":
        return render_template("upload.html")

    files = request.files.getlist("files")
    if not files or all(not f.filename for f in files):
        # Fallback to single 'file' or 'document'
        single = request.files.get("file") or request.files.get("document")
        if single and single.filename:
            files = [single]
        else:
            flash("कृपया किमान एक फाईल निवडा.", "danger")
            return redirect(request.url)

    total_files = 0
    total_records = 0
    duplicate_count = 0
    errors = []
    latest_batch_to_show = None
    force_reimport = request.form.get("force", "").lower() in ("true", "1", "yes")
    duplicate_files_prevented = 0

    for f in files:
        if not f or not f.filename:
            continue

        try:
            # Preserve extension safely even for Marathi / non-ASCII Unicode names
            orig_name = f.filename or "uploaded_file"
            orig_ext = Path(orig_name).suffix.lower()
            clean_base = secure_filename(Path(orig_name).stem) or "survey_doc"
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = f"{timestamp}_{clean_base}{orig_ext}"
            ext = orig_ext
            raw_filename = orig_name

            saved_path = UPLOAD_DIR / safe_name
            f.save(saved_path)

            # Compute file hash to detect identical duplicate re-uploads
            content = saved_path.read_bytes()
            sha256_hash = hashlib.sha256(content).hexdigest()
            md5_hash = hashlib.md5(content).hexdigest()
            file_hash = sha256_hash

            is_dup_file, existing_cnt, existing_batch = is_file_already_imported(
                file_hash=sha256_hash,
                alt_hash=md5_hash,
                filename=raw_filename
            )

            if is_dup_file and not force_reimport:
                # Idempotent upload: prevent duplicate rows in database
                log_upload_audit(
                    upload_batch_id=existing_batch,
                    file_name=raw_filename,
                    file_hash=file_hash,
                    action="duplicate_file_prevented",
                    record_count=existing_cnt,
                    message=f"Duplicate file upload prevented for '{raw_filename}'. Showing existing batch {existing_batch} ({existing_cnt} records)."
                )
                flash(
                    f"यशस्वी! ही फाईल ('{raw_filename}') आधीच आयात केलेली आहे (बॅच: {existing_batch}). विद्यमान {existing_cnt} नोंदी खाली दाखवत आहे. (नव्याने वाचण्यासाठी वर 'पुन्हा AI ने वाचा' बटण वापरा किंवा अपलोड करताना 'सक्तीने पुन्हा AI द्वारे प्रोसेस करा' निवडा).",
                    "info"
                )
                latest_batch_to_show = existing_batch
                duplicate_files_prevented += 1
                total_files += 1
                continue

            total_files += 1
            batch_id = f"BATCH-{timestamp}-{uuid.uuid4().hex[:6]}"
            file_new_records = 0
            file_dup_records = 0

            # 1. OCR Process for PDF and Images
            if ext in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
                try:
                    extract_res = extract_document(saved_path, out_dir=PROCESSED_DIR)
                    extracted_records = extract_res.get("records", [])

                    with get_connection() as conn:
                        for rec in extracted_records:
                            rec["source_file"] = safe_name
                            rec["upload_batch_id"] = batch_id
                            rec["file_hash"] = file_hash
                            farmer_id = insert_farmer(rec, conn=conn)
                            total_records += 1
                            file_new_records += 1
                            if rec.get("is_duplicate"):
                                duplicate_count += 1
                                file_dup_records += 1
                        conn.commit()

                    if file_new_records > 0:
                        latest_batch_to_show = batch_id

                    log_upload_audit(
                        upload_batch_id=batch_id,
                        file_name=safe_name,
                        file_hash=file_hash,
                        action="new_upload",
                        record_count=file_new_records,
                        message=f"Successfully extracted and imported {file_new_records} farmer records ({file_dup_records} overlapping/suspected duplicates) into batch {batch_id}."
                    )

                except Exception as exc:
                    errors.append(f"{raw_filename}: OCR प्रक्रिया करताना त्रुटी आली ({str(exc)})")

            # 2. Tabular Process for CSV and Excel
            elif ext in {".csv", ".xlsx", ".xlsm"}:
                try:
                    df_raw = read_tabular(saved_path)
                    mapping_path = CONFIG_DIR / "field_mapping.json"
                    rules_path = CONFIG_DIR / "validation.json"

                    mapping = load_mapping(mapping_path)
                    rules = load_rules(rules_path)

                    df_mapped = map_columns(df_raw, mapping)
                    df_validated = validate_records(df_mapped, rules, check_db_duplicates=True)

                    with get_connection() as conn:
                        for _, row in df_validated.iterrows():
                            row_dict = dict(row)
                            row_dict["source_file"] = safe_name
                            row_dict["upload_batch_id"] = batch_id
                            row_dict["file_hash"] = file_hash
                            db_record = canonical_to_db_record(row_dict)
                            db_record["source_file"] = safe_name
                            db_record["upload_batch_id"] = batch_id
                            db_record["file_hash"] = file_hash
                            farmer_id = insert_farmer(db_record, conn=conn)
                            total_records += 1
                            file_new_records += 1
                            if db_record.get("is_duplicate"):
                                duplicate_count += 1
                                file_dup_records += 1
                        conn.commit()

                    if file_new_records > 0:
                        latest_batch_to_show = batch_id

                    log_upload_audit(
                        upload_batch_id=batch_id,
                        file_name=safe_name,
                        file_hash=file_hash,
                        action="new_upload",
                        record_count=file_new_records,
                        message=f"Successfully imported {file_new_records} tabular farmer records into batch {batch_id}."
                    )

                except Exception as exc:
                    errors.append(f"{raw_filename}: डेटा वाचताना त्रुटी आली ({str(exc)})")

            else:
                errors.append(f"{raw_filename}: असमर्थित फाईल प्रकार ({ext}).")

        except Exception as exc:
            errors.append(f"{getattr(f, 'filename', 'फाईल')}: फाईल हाताळताना त्रुटी आली ({str(exc)})")

    if errors:
        for err in errors:
            flash(err, "warning")

    if total_records > 0:
        dup_msg = f" (ज्यापैकी {duplicate_count} संभाव्य डुप्लिकेट म्हणून ध्वजांकित केले गेले आहेत)" if duplicate_count > 0 else ""
        flash(f"यशस्वी! {total_files - duplicate_files_prevented} नवीन फाईल्स प्रक्रिया केल्या आणि एकूण {total_records} शेतकरी नोंदी सुरक्षितपणे डेटाबेसमध्ये साठवल्या{dup_msg}.", "success")
    elif not errors and total_files > 0 and duplicate_files_prevented == 0:
        flash("कोणत्याही नोंदी आढळल्या नाहीत.", "info")

    if latest_batch_to_show:
        if total_records > 0:
            return redirect(url_for(
                "farmers.list_farmers",
                batch=latest_batch_to_show,
                upload_status="success",
                new_records=total_records,
                new_files=(total_files - duplicate_files_prevented),
                dup_records=duplicate_count
            ))
        elif duplicate_files_prevented > 0:
            return redirect(url_for(
                "farmers.list_farmers",
                batch=latest_batch_to_show,
                upload_status="duplicate"
            ))
        return redirect(url_for("farmers.list_farmers", batch=latest_batch_to_show))
    return redirect(url_for("farmers.list_farmers"))

@app.route("/reviews")
def reviews_table():
    """Phase 1 review dashboard preserving backwards compatibility."""
    selected_status = request.args.get("status", "all")
    with get_connection() as db:
        rows = db.execute("SELECT * FROM reviews ORDER BY updated_at DESC").fetchall()

    records = []
    for row in rows:
        record = dict(row)
        try:
            record["fields"] = json.loads(record["record_json"])
        except Exception:
            record["fields"] = {}
        record["display_status"] = record["decision"] or record["original_status"]
        if selected_status == "all" or record["display_status"] == selected_status:
            records.append(record)

    counts = {
        "total": len(rows),
        "pending": sum(r["decision"] is None for r in rows),
        "verified": sum(r["decision"] == "verified" for r in rows),
        "needs_review": sum(r["decision"] == "needs_review" or (r["decision"] is None and r["original_status"] == "needs_review") for r in rows)
    }

    return render_template(
        "index.html",
        records=records,
        counts=counts,
        selected_status=selected_status
    )

@app.route("/export")
def export_csv():
    with get_connection() as db:
        rows = db.execute("SELECT source_file, record_id, record_json, original_status, decision, reviewer_note, updated_at FROM reviews ORDER BY record_id").fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["source_file", "record_id", "original_status", "review_decision", "reviewer_note", "updated_at", "record_data_json"])
    for r in rows:
        writer.writerow([r["source_file"], r["record_id"], r["original_status"], r["decision"] or "", r["reviewer_note"], r["updated_at"] or "", r["record_json"]])

    return Response(
        "\ufeff" + output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=chara_survey_reviews.csv"}
    )

@app.route("/export.xlsx")
def export_phase1_excel():
    return redirect(url_for("farmers.export_excel"))

@app.errorhandler(413)
def request_entity_too_large(error):
    flash("अपलोड केलेली फाईल खूप मोठी आहे (कमाल मर्यादा 50 MB). कृपया लहान आकाराची फाईल अपलोड करा.", "danger")
    return redirect(url_for("upload"))

@app.errorhandler(500)
def internal_error(error):
    flash(f"सर्व्हरवर प्रक्रिया करताना त्रुटी आली. कृपया फाईल तपासा किंवा पुन्हा प्रयत्न करा.", "danger")
    return redirect(url_for("farmers.list_farmers"))

@app.errorhandler(Exception)
def unhandled_exception(error):
    flash(f"प्रक्रिया करताना त्रुटी आली: {str(error)}", "danger")
    return redirect(url_for("farmers.list_farmers"))

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    print(f"Server starting on http://{host}:{port} (Connect from Android mobile on same Wi-Fi at http://<IP>:{port})")
    app.run(host=host, port=port, debug=False)
