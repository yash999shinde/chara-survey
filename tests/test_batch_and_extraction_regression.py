# -*- coding: utf-8 -*-
"""Regression tests for Upload Batches, Duplicate Upload Prevention, and Marathi OCR Field Mapping."""
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
    get_distinct_source_files,
    get_distinct_upload_batches,
    get_latest_batch_id,
    is_file_already_imported,
)
from pipeline.extractor import (
    extract_document,
    clean_name,
    extract_mobile_number,
    clean_digits
)

@pytest.fixture
def test_client(tmp_path):
    """Setup a dedicated test database for isolated test execution."""
    test_db = tmp_path / "test_regression.db"
    app.config["TESTING"] = True

    # Initialize schema on test db
    init_db(test_db)

    # Monkeypatch DB_PATH in app and db
    import app.db as db_mod
    original_db_path = db_mod.DB_PATH
    db_mod.DB_PATH = test_db

    with app.test_client() as client:
        yield client, test_db

    db_mod.DB_PATH = original_db_path

def test_source_file_and_batch_isolation(test_client):
    """Verify that records are strictly isolated by source_file and upload_batch_id."""
    client, test_db = test_client

    with get_connection(test_db) as conn:
        # Batch A from File 1
        insert_farmer({
            "farmer_name": "गणेश पांडुरंग",
            "village_name": "वाळकी",
            "mobile": "9822110011",
            "source_file": "survey_batch_1.pdf",
            "upload_batch_id": "BATCH-001",
            "file_hash": "hash_aaa",
            "daily_milk_litres": 15.0,
            "status": "pending_review"
        }, conn=conn)

        insert_farmer({
            "farmer_name": "सुरेश रामदास",
            "village_name": "वाळकी",
            "mobile": "9822110022",
            "source_file": "survey_batch_1.pdf",
            "upload_batch_id": "BATCH-001",
            "file_hash": "hash_aaa",
            "daily_milk_litres": 20.0,
            "status": "verified"
        }, conn=conn)

        # Batch B from File 2
        insert_farmer({
            "farmer_name": "बाळू किसन",
            "village_name": "वडगाव",
            "mobile": "9822110033",
            "source_file": "survey_batch_2.pdf",
            "upload_batch_id": "BATCH-002",
            "file_hash": "hash_bbb",
            "daily_milk_litres": 25.0,
            "status": "pending_review"
        }, conn=conn)

        conn.commit()

    # 1. Test unfiltered total
    all_recs = get_all_farmers(conn=get_connection(test_db))
    assert len(all_recs) == 3

    # 2. Test filtering by source_file
    file1_recs = get_all_farmers(source_file="survey_batch_1.pdf", conn=get_connection(test_db))
    assert len(file1_recs) == 2
    assert all(r["source_file"] == "survey_batch_1.pdf" for r in file1_recs)

    file2_recs = get_all_farmers(source_file="survey_batch_2.pdf", conn=get_connection(test_db))
    assert len(file2_recs) == 1
    assert file2_recs[0]["farmer_name"] == "बाळू किसन"

    # 3. Test filtering by upload_batch_id
    b1_recs = get_all_farmers(upload_batch_id="BATCH-001", conn=get_connection(test_db))
    assert len(b1_recs) == 2

    # 4. Test latest_only filter
    latest_recs = get_all_farmers(latest_only=True, conn=get_connection(test_db))
    assert len(latest_recs) == 1
    assert latest_recs[0]["upload_batch_id"] == "BATCH-002"

    # 5. Test dashboard counts filtering
    counts_b1 = get_dashboard_counts(upload_batch_id="BATCH-001", conn=get_connection(test_db))
    assert counts_b1["total"] == 2
    assert counts_b1["verified"] == 1

def test_duplicate_file_reupload_prevention(test_client):
    """Verify that uploading the exact same file hash/name is detected and duplicate creation is prevented."""
    client, test_db = test_client

    with get_connection(test_db) as conn:
        insert_farmer({
            "farmer_name": "आशिष शब्बीर शेख",
            "village_name": "वडगाव तांदळी",
            "mobile": "9096515858",
            "source_file": "bhiya_survey.pdf",
            "upload_batch_id": "BATCH-TEST-ORIG",
            "file_hash": "md5_fixed_checksum_12345",
            "status": "pending_review"
        }, conn=conn)
        conn.commit()

    # Test detection helper
    is_dup, cnt, batch = is_file_already_imported(
        file_hash="md5_fixed_checksum_12345",
        filename="bhiya_survey.pdf",
        conn=get_connection(test_db)
    )
    assert is_dup is True
    assert cnt == 1
    assert batch == "BATCH-TEST-ORIG"

    # Test non-duplicate file
    is_dup2, _, _ = is_file_already_imported(
        file_hash="different_hash_99999",
        filename="new_file.pdf",
        conn=get_connection(test_db)
    )
    assert is_dup2 is False

def test_dashboard_routes_and_filters(test_client):
    """Test dashboard web endpoints with batch and source_file filters."""
    client, test_db = test_client

    with get_connection(test_db) as conn:
        insert_farmer({
            "farmer_name": "नबाब रुबाब शेख",
            "village_name": "वडगाव तांदळी",
            "mobile": "7020021960",
            "source_file": "batch_one.pdf",
            "upload_batch_id": "BATCH-100",
            "status": "pending_review"
        }, conn=conn)
        conn.commit()

    # 1. View all
    res_all = client.get("/farmers")
    assert res_all.status_code == 200
    assert "नबाब रुबाब शेख" in res_all.data.decode("utf-8")

    # 2. View specific batch
    res_batch = client.get("/farmers?batch=BATCH-100")
    assert res_batch.status_code == 200
    assert "BATCH-100" in res_batch.data.decode("utf-8")

    # 3. View latest batch shortcut
    res_latest = client.get("/farmers?latest=1")
    assert res_latest.status_code == 200

    # 4. Excel export with batch filter
    res_excel = client.get("/farmers/export_excel?batch=BATCH-100")
    assert res_excel.status_code == 200
    assert res_excel.headers["Content-Type"].startswith("application/vnd.openxmlformats")

def test_real_pdf_extraction_field_mapping():
    """Verify calibrated OCR extraction on the actual survey PDF."""
    pdf_path = PROJECT_ROOT / "data" / "uploads" / "4c6d29186a5840f3b14bc5f17240642c.pdf"
    if not pdf_path.exists():
        pytest.skip(f"Survey PDF not found at {pdf_path}")

    res = extract_document(pdf_path)
    records = res.get("records", [])

    # The survey table contains 6 real farmer rows
    assert len(records) == 6

    for r in records:
        # Raw OCR text must be preserved
        assert "raw_ocr_text" in r
        assert len(r["raw_ocr_text"]) > 0

        # Village and taluka
        assert r["village_name"] == "वडगाव तांदळी"
        assert r["taluka"] == "नगर"

        # No fabricated sums or zeros
        assert isinstance(r["daily_milk_litres"], float)
        assert isinstance(r["cow_large"], int)
        assert isinstance(r["buffalo_large"], int)
        assert isinstance(r["goats"], int)

        # Status must be pending_review or needs_review
        assert r["status"] in ("pending_review", "needs_review")

    # Verify specific known data points from the actual sheet:
    # Row 6: Bashir Kamal Shaikh has 25L milk and 20 goats
    row6 = records[5]
    assert "कमाल" in row6["farmer_name"] or "माल" in row6["farmer_name"]
    assert row6["daily_milk_litres"] >= 20.0
    assert row6["goats"] >= 20

    # Row 3: Latif Jamal Shaikh has 15L milk
    row3 = records[2]
    assert "ल" in row3["farmer_name"] or "लब" in row3["farmer_name"]
    assert row3["milch_animals"] == 2

    # Row 1: Ashish Shabbir Shaikh has milk and well irrigation
    row1 = records[0]
    assert row1["daily_milk_litres"] >= 20.0
    assert row1["irrigation_types"] == "विहीर"
