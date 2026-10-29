# -*- coding: utf-8 -*-
from pathlib import Path
import pytest
import io
from app.app import app
from app.db import get_all_farmers, delete_farmer, get_farmer_by_id

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_root_redirect(client):
    res = client.get("/")
    assert res.status_code == 302
    assert "/farmers" in res.location

def test_farmers_dashboard(client):
    res = client.get("/farmers")
    assert res.status_code == 200
    assert "शेतकरी" in res.text or "Dr. Prathmesh" in res.text
    assert "डॅशबोर्ड" in res.text
    # Should display existing farmers
    assert "Demo Farmer Three" in res.text

def test_farmers_dashboard_filter_and_search(client):
    # Filter status
    res = client.get("/farmers?status=verified")
    assert res.status_code == 200
    assert "Verified" in res.text

    # Search query
    res_search = client.get("/farmers?q=Demo")
    assert res_search.status_code == 200
    assert "Demo Farmer Three" in res_search.text

def test_edit_farmer_workflow(client):
    # 1. Open edit form for ID 1
    res_get = client.get("/farmers/1/edit")
    assert res_get.status_code == 200
    assert "शेतकरी नोंद तपशील संपादन" in res_get.text

    # 2. Submit edit form
    res_post = client.post("/farmers/1/edit", data={
        "taluka": "Demo Taluka",
        "veterinary_hospital": "Demo Veterinary Hospital",
        "revenue_circle": "Demo Revenue Circle",
        "village_name": "Demo Village",
        "farmer_name": "Demo Farmer Three (Verified Test)",
        "mobile": "7777777777",
        "cow_small": "0",
        "cow_large": "1",
        "buffalo_small": "2",
        "buffalo_large": "1",
        "milch_animals": "4",
        "dry_animals": "0",
        "daily_milk_litres": "16.0",
        "green_fodder_tonnes": "2.25",
        "silage_tonnes": "1.5",
        "dry_fodder_tonnes": "3.0",
        "status": "verified",
        "review_notes": "Automated verification test"
    }, follow_redirects=True)
    assert res_post.status_code == 200

    f = get_farmer_by_id(1)
    assert f["farmer_name"] == "Demo Farmer Three (Verified Test)"
    assert f["status"] == "verified"

    # Revert name back
    client.post("/farmers/1/edit", data={
        "taluka": "Demo Taluka",
        "veterinary_hospital": "Demo Veterinary Hospital",
        "revenue_circle": "Demo Revenue Circle",
        "village_name": "Demo Village",
        "farmer_name": "Demo Farmer Three",
        "mobile": "7777777777",
        "cow_small": "0",
        "cow_large": "1",
        "buffalo_small": "2",
        "buffalo_large": "1",
        "milch_animals": "4",
        "dry_animals": "0",
        "daily_milk_litres": "16.0",
        "status": "verified"
    })

def test_verify_and_bulk_verify_routes(client):
    # Verify single farmer
    res = client.post("/farmers/2/verify", follow_redirects=True)
    assert res.status_code == 200
    f2 = get_farmer_by_id(2)
    assert f2["status"] == "verified"

    # Bulk verify
    res_bulk = client.post("/farmers/bulk_verify", data={"farmer_ids": ["2", "3"]}, follow_redirects=True)
    assert res_bulk.status_code == 200
    f3 = get_farmer_by_id(3)
    assert f3["status"] == "verified"

def test_excel_export_route(client):
    res = client.get("/farmers/export_excel")
    assert res.status_code == 200
    assert res.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert len(res.data) > 1000

def test_bulk_upload_tabular(client):
    csv_content = """गावाचे नाव,शेतकऱ्याचे नाव,मोबाईल क्रमांक,गायींची संख्या,दूध (लिटर/दिवस)
नमुना गाव,चाचणी शेतकरी युनिक,9123456789,2,12.0
"""
    data = {
        "files": (io.BytesIO(csv_content.encode("utf-8")), "test_bulk_input.csv")
    }
    res = client.post("/upload", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert res.status_code == 200
    assert "यशस्वी!" in res.text

    # Verify newly imported farmer exists
    farmers = get_all_farmers(search_query="चाचणी शेतकरी युनिक")
    assert len(farmers) >= 1
    new_farmer = farmers[0]
    assert new_farmer["farmer_name"] == "चाचणी शेतकरी युनिक"
    assert new_farmer["mobile"] == "9123456789"
    assert new_farmer["daily_milk_litres"] == 12.0

    # Cleanup
    delete_farmer(new_farmer["id"])

def test_bulk_upload_real_pdf(client):
    real_pdf = ROOT / "data" / "uploads" / "20261028_070119_bhiya.pdf"
    if real_pdf.exists():
        pdf_bytes = real_pdf.read_bytes()
        data = {
            "files": (io.BytesIO(pdf_bytes), "test_upload_survey.pdf")
        }
        res = client.post("/upload", data=data, content_type="multipart/form-data", follow_redirects=True)
        assert res.status_code == 200
        assert "यशस्वी!" in res.text
