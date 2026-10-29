# -*- coding: utf-8 -*-
from pathlib import Path
import pytest
import sqlite3
from app.db import (
    get_connection,
    get_all_farmers,
    get_farmer_by_id,
    insert_farmer,
    update_farmer,
    verify_farmer,
    delete_farmer,
    get_dashboard_counts,
    check_duplicate_in_db
)

def test_existing_records_preserved():
    # Existing database must have at least 19 records preserved
    farmers = get_all_farmers()
    assert len(farmers) >= 19
    # Check that Demo Farmer Three exists
    farmer_names = [f["farmer_name"] for f in farmers]
    assert "Demo Farmer Three" in farmer_names

def test_insert_and_duplicate_detection_mobile():
    unique_mobile = "9988776655"
    rec1 = {
        "taluka": "नगर",
        "village_name": "चाचणी गाव अ",
        "farmer_name": "चाचणी शेतकरी एक",
        "mobile": unique_mobile,
        "cow_large": 2,
        "daily_milk_litres": 15.0,
        "status": "pending_review",
        "source_file": "test_batch.csv"
    }

    id1 = insert_farmer(rec1)
    f1 = get_farmer_by_id(id1)
    assert f1["farmer_name"] == "चाचणी शेतकरी एक"
    assert f1["is_duplicate"] == 0

    # Insert second farmer with SAME mobile number
    rec2 = {
        "taluka": "नगर",
        "village_name": "चाचणी गाव ब",
        "farmer_name": "चाचणी शेतकरी दोन",
        "mobile": unique_mobile,
        "cow_large": 1,
        "daily_milk_litres": 8.0,
        "status": "pending_review",
        "source_file": "test_batch.csv"
    }
    id2 = insert_farmer(rec2)
    f2 = get_farmer_by_id(id2)
    assert f2["is_duplicate"] == 1
    assert "मोबाईल क्रमांक 9988776655" in f2["duplicate_reason"]

    # Clean up test rows
    delete_farmer(id1)
    delete_farmer(id2)

def test_duplicate_detection_name_and_village():
    rec1 = {
        "taluka": "नगर",
        "village_name": "चाचणी गाव क",
        "farmer_name": "गणेश पांडुरंग शिंदे",
        "mobile": "9811223344",
        "status": "pending_review"
    }
    id1 = insert_farmer(rec1)

    rec2 = {
        "taluka": "नगर",
        "village_name": "चाचणी गाव क",
        "farmer_name": "गणेश पांडुरंग शिंदे",
        "mobile": "9811223355",  # different phone but same name and village
        "status": "pending_review"
    }
    id2 = insert_farmer(rec2)
    f2 = get_farmer_by_id(id2)
    assert f2["is_duplicate"] == 1
    assert "गणेश पांडुरंग शिंदे" in f2["duplicate_reason"]

    delete_farmer(id1)
    delete_farmer(id2)

def test_update_and_verify_farmer():
    rec = {
        "taluka": "नगर",
        "village_name": "वाळकी",
        "farmer_name": "संपादन चाचणी शेतकरी",
        "mobile": "9766554433",
        "cow_large": 2,
        "daily_milk_litres": 10.0,
        "status": "pending_review"
    }
    f_id = insert_farmer(rec)

    # 1. Update fields
    success = update_farmer(f_id, {
        "farmer_name": "संपादन चाचणी शेतकरी (अद्यतनित)",
        "daily_milk_litres": 22.5,
        "green_fodder_tonnes": 3.0,
        "review_notes": "मॅन्युअली तपासले"
    })
    assert success is True

    updated = get_farmer_by_id(f_id)
    assert updated["farmer_name"] == "संपादन चाचणी शेतकरी (अद्यतनित)"
    assert updated["daily_milk_litres"] == 22.5
    assert updated["green_fodder_tonnes"] == 3.0
    assert updated["review_notes"] == "मॅन्युअली तपासले"

    # 2. Manual Verification
    v_success = verify_farmer(f_id, note="पडताळणी पूर्ण")
    assert v_success is True

    verified = get_farmer_by_id(f_id)
    assert verified["status"] == "verified"

    delete_farmer(f_id)

def test_dashboard_counts():
    counts = get_dashboard_counts()
    assert isinstance(counts, dict)
    assert "total" in counts
    assert "verified" in counts
    assert "pending" in counts
    assert "duplicates" in counts
    assert counts["total"] >= 19
