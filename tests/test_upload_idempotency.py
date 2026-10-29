# -*- coding: utf-8 -*-
"""Comprehensive tests for Upload Idempotency, Overlapping Surveys, and Security Controls."""
import os
import sys
import io
import json
import sqlite3
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.app import app
from app.db import (
    init_db,
    get_connection,
    insert_farmer,
    get_all_farmers,
    get_dashboard_counts,
    is_file_already_imported,
    get_upload_audit_logs,
    log_upload_audit,
)

@pytest.fixture
def isolated_app(tmp_path):
    """Set up an isolated test SQLite database for full workflow testing."""
    test_db = tmp_path / "test_idempotency.db"
    app.config["TESTING"] = True

    init_db(test_db)

    import app.db as db_mod
    original_db = db_mod.DB_PATH
    db_mod.DB_PATH = test_db

    with app.test_client() as client:
        yield client, test_db

    db_mod.DB_PATH = original_db

def test_identical_file_upload_is_idempotent(isolated_app):
    """
    Rule: Uploading the exact same PDF must not create duplicate records.
    It must record an audit event, return success message, and link to existing batch.
    """
    client, test_db = isolated_app

    csv_data = "गावाचे नाव,शेतकऱ्याचे नाव,मोबाईल क्रमांक,गायींची संख्या,दूध (लिटर/दिवस)\nवडगाव,रमेश शिंदे,9823001122,2,10.0\n"
    file_bytes = csv_data.encode("utf-8")

    # 1. First upload -> creates 1 record in new batch
    data1 = {"files": (io.BytesIO(file_bytes), "sample_survey.csv")}
    res1 = client.post("/upload", data=data1, content_type="multipart/form-data", follow_redirects=True)
    assert res1.status_code == 200
    assert "यशस्वी!" in res1.text

    recs_after_1 = get_all_farmers(conn=get_connection(test_db))
    assert len(recs_after_1) == 1
    batch_1 = recs_after_1[0]["upload_batch_id"]

    # 2. Second upload of exact same file -> must NOT create a new record
    data2 = {"files": (io.BytesIO(file_bytes), "sample_survey.csv")}
    res2 = client.post("/upload", data=data2, content_type="multipart/form-data", follow_redirects=True)
    assert res2.status_code == 200
    assert "यशस्वी!" in res2.text
    assert "आधीच आयात केलेली आहे" in res2.text or "विद्यमान" in res2.text

    recs_after_2 = get_all_farmers(conn=get_connection(test_db))
    assert len(recs_after_2) == 1, "Duplicate file upload must not multiply database rows!"

    # 3. Check upload audit log
    logs = get_upload_audit_logs(conn=get_connection(test_db))
    actions = [l["action"] for l in logs]
    assert "duplicate_file_prevented" in actions
    assert "new_upload" in actions

def test_force_reimport_bypasses_idempotency_if_requested(isolated_app):
    """When force=true is provided, re-processing is permitted."""
    client, test_db = isolated_app

    csv_data = "गावाचे नाव,शेतकऱ्याचे नाव,मोबाईल क्रमांक,गायींची संख्या,दूध (लिटर/दिवस)\nवडगाव,अनिल कदम,9823003344,1,8.0\n"
    file_bytes = csv_data.encode("utf-8")

    # First upload
    client.post("/upload", data={"files": (io.BytesIO(file_bytes), "forced_survey.csv")}, content_type="multipart/form-data")
    assert len(get_all_farmers(conn=get_connection(test_db))) == 1

    # Second upload with force=true
    res = client.post("/upload", data={
        "files": (io.BytesIO(file_bytes), "forced_survey.csv"),
        "force": "true"
    }, content_type="multipart/form-data", follow_redirects=True)
    assert res.status_code == 200

    recs = get_all_farmers(conn=get_connection(test_db))
    assert len(recs) == 2, "Force re-import must create new batch entries"

def test_overlapping_survey_farmers_flagged_not_dropped(isolated_app):
    """
    Rule: Different PDF containing the same farmer (same mobile number):
    - Must create a new upload batch.
    - Farmer record must be inserted under the new batch.
    - Must be flagged with is_duplicate = 1 and status = 'needs_review'.
    - Both source records and source files must be preserved.
    """
    client, test_db = isolated_app

    # Survey 1 from Wadgaon
    csv1 = "गावाचे नाव,शेतकऱ्याचे नाव,मोबाईल क्रमांक,गायींची संख्या,दूध (लिटर/दिवस)\nवडगाव तांदळी,दत्तात्रय पाटील,9890123456,2,12.0\n"
    client.post("/upload", data={"files": (io.BytesIO(csv1.encode("utf-8")), "survey_village_1.csv")}, content_type="multipart/form-data")

    recs1 = get_all_farmers(conn=get_connection(test_db))
    assert len(recs1) == 1
    assert recs1[0]["is_duplicate"] == 0
    batch_1 = recs1[0]["upload_batch_id"]

    # Survey 2 (different file and content, but shares farmer mobile 9890123456)
    csv2 = "गावाचे नाव,शेतकऱ्याचे नाव,मोबाईल क्रमांक,गायींची संख्या,दूध (लिटर/दिवस)\nवाळकी,दत्तात्रय पाटील,9890123456,3,15.0\n"
    res2 = client.post("/upload", data={"files": (io.BytesIO(csv2.encode("utf-8")), "survey_village_2.csv")}, content_type="multipart/form-data", follow_redirects=True)
    assert res2.status_code == 200

    recs2 = get_all_farmers(conn=get_connection(test_db))
    assert len(recs2) == 2, "Both records must exist in the database!"

    # The second record must have a distinct batch, be flagged duplicate, and need review
    rec_new = [r for r in recs2 if r["source_file"].endswith("survey_village_2.csv")][0]
    assert rec_new["upload_batch_id"] != batch_1
    assert rec_new["is_duplicate"] == 1
    assert "9890123456" in rec_new["duplicate_reason"]
    assert rec_new["status"] == "needs_review"

def test_external_form_submission_safety_guard(isolated_app):
    """
    Safety Rule: External form submission must be disabled unless ENABLE_EXTERNAL_FORM_SUBMISSION=true.
    No automatic outbound requests to Google Forms.
    """
    client, test_db = isolated_app

    # Insert a verified record
    with get_connection(test_db) as conn:
        fid = insert_farmer({
            "farmer_name": "Verified Farmer Test",
            "village_name": "सुरक्षित गाव",
            "mobile": "9988776655",
            "status": "verified"
        }, conn=conn)
        conn.commit()

    # Ensure env var is disabled
    os.environ["ENABLE_EXTERNAL_FORM_SUBMISSION"] = "false"

    res = client.post(f"/farmers/{fid}/submit_form", follow_redirects=True)
    assert res.status_code == 200
    assert "सुरक्षा सूचना" in res.text
    assert "अक्षम (Disabled)" in res.text

    # Record should still not be marked submitted
    farmer = get_all_farmers(search_query="Verified Farmer Test", conn=get_connection(test_db))[0]
    assert farmer["status"] == "verified"
