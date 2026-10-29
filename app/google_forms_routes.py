# -*- coding: utf-8 -*-
"""Flask Blueprint for Dynamic Google Form Inspection & Automatic Filling."""
import datetime
import sqlite3
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

from app.db import get_connection, get_farmer_by_id, update_farmer, get_distinct_upload_batches
from app.google_forms_service import (
    inspect_google_form,
    build_farmer_payload,
    submit_farmer_to_google_form,
    generate_prefilled_url,
    clean_google_form_url
)

google_forms_bp = Blueprint("google_forms", __name__)

DEFAULT_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfh73QStzk0cZ6gvqRHZWG9V4yGsBv3tx2Z6P3WroXS97XxHQ/viewform"

@google_forms_bp.route("/google_forms", methods=["GET"])
def google_forms_dashboard():
    """Main dashboard for Google Form automation."""
    form_url = request.args.get("form_url", "").strip() or DEFAULT_FORM_URL
    selected_batch = request.args.get("batch", "all")
    scope = request.args.get("scope", "verified")

    # Try inspecting the form
    form_meta = None
    inspect_error = None
    try:
        form_meta = inspect_google_form(form_url)
    except Exception as e:
        inspect_error = str(e)

    # Fetch batches and farmer counts
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        upload_batches = [dict(r) for r in conn.execute("""
            SELECT upload_batch_id as batch_id, source_file, COUNT(*) as record_count
            FROM farmers WHERE upload_batch_id != '' GROUP BY upload_batch_id ORDER BY MAX(id) DESC
        """).fetchall()]

        verified_count = conn.execute("SELECT COUNT(*) FROM farmers WHERE status = 'verified'").fetchone()[0]
        total_count = conn.execute("SELECT COUNT(*) FROM farmers").fetchone()[0]

        # Recent submissions
        recent_submissions = [dict(r) for r in conn.execute("""
            SELECT * FROM form_submissions ORDER BY id DESC LIMIT 20
        """).fetchall()]

    return render_template(
        "google_forms.html",
        form_url=form_url,
        form_meta=form_meta,
        inspect_error=inspect_error,
        upload_batches=upload_batches,
        selected_batch=selected_batch,
        scope=scope,
        verified_count=verified_count,
        total_count=total_count,
        recent_submissions=recent_submissions
    )

@google_forms_bp.route("/google_forms/inspect_api", methods=["POST"])
def inspect_form_api():
    """AJAX endpoint to inspect any Google Form URL dynamically."""
    data = request.get_json(silent=True) or request.form
    url = (data.get("form_url") or "").strip()
    if not url:
        return jsonify({"success": False, "error": "Google Form URL रिकामी असू शकत नाही."}), 400

    try:
        meta = inspect_google_form(url)
        return jsonify({"success": True, "meta": meta})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@google_forms_bp.route("/google_forms/submit_all", methods=["POST"])
def submit_all_farmers():
    """Auto-submits selected farmers to the inspected Google Form."""
    form_url = request.form.get("form_url", "").strip() or DEFAULT_FORM_URL
    scope = request.form.get("scope", "verified")
    batch_id = request.form.get("batch_id", "all")

    try:
        form_meta = inspect_google_form(form_url)
    except Exception as e:
        flash(f"Google Form तपासताना त्रुटी: {str(e)}", "danger")
        return redirect(url_for("google_forms.google_forms_dashboard", form_url=form_url))

    response_url = form_meta["response_url"]
    schema = form_meta["questions"]
    mapping = form_meta["mapping"]

    # Select target farmers
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        if scope == "verified":
            cur = conn.execute("SELECT * FROM farmers WHERE status = 'verified' ORDER BY id ASC")
        elif scope == "batch" and batch_id and batch_id != "all":
            cur = conn.execute("SELECT * FROM farmers WHERE upload_batch_id = ? ORDER BY id ASC", (batch_id,))
        else:
            cur = conn.execute("SELECT * FROM farmers ORDER BY id ASC")

        farmers = [dict(r) for r in cur.fetchall()]

    if not farmers:
        flash("सबमिशनसाठी कोणतेही शेतकरी रेकॉर्ड सापडले नाहीत.", "warning")
        return redirect(url_for("google_forms.google_forms_dashboard", form_url=form_url))

    success_count = 0
    fail_count = 0
    errors = []

    for f in farmers:
        payload = build_farmer_payload(f, schema, mapping)
        ok, code, msg = submit_farmer_to_google_form(response_url, payload)

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO form_submissions (farmer_id, farmer_name, mobile, submitted_at, http_status, response_snippet)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (f["id"], f["farmer_name"], f["mobile"], now_str, code, msg))
            conn.commit()

        if ok:
            update_farmer(f["id"], {"status": "submitted"})
            success_count += 1
        else:
            fail_count += 1
            errors.append(f"{f['farmer_name']} (#{f['id']}): {msg}")

    if success_count > 0:
        flash(f"यशस्वी! {success_count} शेतकऱ्यांची माहिती Google Form मध्ये ऑटोमॅटिक भरली गेली!", "success")
    if fail_count > 0:
        flash(f"{fail_count} फॉर्म सबमिशन करताना अडचणी आल्या: {'; '.join(errors[:3])}", "warning")

    return redirect(url_for("google_forms.google_forms_dashboard", form_url=form_url, scope=scope, batch=batch_id))

@google_forms_bp.route("/google_forms/prefilled_links", methods=["GET", "POST"])
def view_prefilled_links():
    """Generates a list of prefilled Google Form URLs for manual review & 1-click submission."""
    form_url = request.args.get("form_url", "").strip() or DEFAULT_FORM_URL
    scope = request.args.get("scope", "verified")
    batch_id = request.args.get("batch_id", "all")

    try:
        form_meta = inspect_google_form(form_url)
    except Exception as e:
        flash(f"Google Form तपासताना त्रुटी: {str(e)}", "danger")
        return redirect(url_for("google_forms.google_forms_dashboard", form_url=form_url))

    view_url = form_meta["view_url"]
    schema = form_meta["questions"]
    mapping = form_meta["mapping"]

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        if scope == "verified":
            cur = conn.execute("SELECT * FROM farmers WHERE status = 'verified' ORDER BY id ASC")
        elif scope == "batch" and batch_id and batch_id != "all":
            cur = conn.execute("SELECT * FROM farmers WHERE upload_batch_id = ? ORDER BY id ASC", (batch_id,))
        else:
            cur = conn.execute("SELECT * FROM farmers ORDER BY id ASC LIMIT 50")
        farmers = [dict(r) for r in cur.fetchall()]

    prefilled_items = []
    for f in farmers:
        payload = build_farmer_payload(f, schema, mapping)
        link = generate_prefilled_url(view_url, payload)
        prefilled_items.append({
            "farmer": f,
            "url": link
        })

    return render_template(
        "google_forms_prefilled.html",
        form_url=form_url,
        form_meta=form_meta,
        items=prefilled_items
    )
