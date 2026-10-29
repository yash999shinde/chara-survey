# -*- coding: utf-8 -*-
"""Tests for Dynamic Google Forms Inspection, Field Mapping, and Auto-Fill."""
import pytest
from app.app import app
from app.google_forms_service import (
    clean_google_form_url,
    match_question_to_field,
    build_farmer_payload
)

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_clean_google_form_url():
    raw_1 = "https://docs.google.com/forms/d/e/1FAIpQLSfh73QStzk0cZ6gvqRHZWG9V4yGsBv3tx2Z6P3WroXS97XxHQ/viewform?usp=sf_link"
    view_1, resp_1 = clean_google_form_url(raw_1)
    assert view_1 == "https://docs.google.com/forms/d/e/1FAIpQLSfh73QStzk0cZ6gvqRHZWG9V4yGsBv3tx2Z6P3WroXS97XxHQ/viewform"
    assert resp_1 == "https://docs.google.com/forms/d/e/1FAIpQLSfh73QStzk0cZ6gvqRHZWG9V4yGsBv3tx2Z6P3WroXS97XxHQ/formResponse"

def test_match_all_user_screenshot_questions():
    """Verify semantic mapping on all questions seen in user screenshots."""
    test_cases = [
        ("गावाचे नाव", "village_name"),
        ("पशुपालकाचे नाव", "farmer_name"),
        ("मोबाईल नंबर", "mobile"),
        ("गाय वर्ग - लहान (1 वर्षा खालचे)", "cow_small"),
        ("गाय वर्ग - मोठे (1 वर्षा वरचे)", "cow_large"),
        ("म्हैस वर्ग - लहान (1 वर्षा खालचे)", "buffalo_small"),
        ("म्हैस वर्ग - मोठे (1 वर्षा वरचे)", "buffalo_large"),
        ("पैकी दुभती जनावरे", "milch_animals"),
        ("भाकड जनावरे", "dry_animals"),
        ("दैनंदिन दूध उत्पादन - लिटर", "daily_milk_litres"),
        ("शेळ्या", "goats"),
        ("मेंढ्या - स्थलांतरित", "sheep_migratory"),
        ("मेंढ्या - बंधिस्त", "sheep_confined"),
        ("जनावरांकरिता पाणी उपलब्धता", "water_availability"),
        ("उपलब्ध चाऱ्याचा प्रकार", "fodder_types"),
        ("हिरवा चारा - मे.टन", "green_fodder_tonnes"),
        ("उपलब्ध मुरघास - मे.टन", "silage_tonnes"),
        ("वाळलेला चारा - मे.टन", "dry_fodder_tonnes"),
        ("सध्या विक्रीकरिता उपलब्ध चारा - मे.टन", "fodder_for_sale_tonnes"),
        ("रबी हंगामात चारा लागवडी योग्य क्षेत्र - हेक्टर", "rabi_area_hectares"),
        ("सिंचन सुविधा उपलब्ध आहे का?", "irrigation_available"),
        ("असल्यास कोणती सिंचन सुविधा उपलब्ध आहे?", "irrigation_types"),
        ("इतर सिंचन सुविधा असल्यास तिचे नाव लिहा", "irrigation_other")
    ]
    for title, expected_field in test_cases:
        matched = match_question_to_field(title, [])
        assert matched == expected_field, f"Question '{title}' mapped to '{matched}', expected '{expected_field}'"

def test_build_farmer_payload():
    farmer = {
        "farmer_name": "आशिष शब्बीर शेख",
        "village_name": "वडगाव तांदळी",
        "mobile": "9096515858",
        "cow_large": 1,
        "daily_milk_litres": 20.0,
        "irrigation_available": "आहे",
        "irrigation_types": "विहीर"
    }
    schema = [
        {"title": "पशुपालकाचे नाव", "entry_id": "entry.744608837", "required": True},
        {"title": "मोबाईल नंबर", "entry_id": "entry.1412319850", "required": True},
        {"title": "दैनंदिन दूध उत्पादन - लिटर", "entry_id": "entry.1725598946", "required": True},
        {"title": "गाय वर्ग - लहान (1 वर्षा खालचे)", "entry_id": "entry.169726096", "required": True}
    ]
    mapping = {
        "farmer_name": "entry.744608837",
        "mobile": "entry.1412319850",
        "daily_milk_litres": "entry.1725598946",
        "cow_small": "entry.169726096"
    }
    payload = build_farmer_payload(farmer, schema, mapping)
    assert payload["entry.744608837"] == "आशिष शब्बीर शेख"
    assert payload["entry.1412319850"] == "9096515858"
    assert payload["entry.1725598946"] == "20"
    assert payload["entry.169726096"] == "0"  # Safe default 0 for missing required count

def test_google_forms_dashboard_route(client):
    res = client.get("/google_forms")
    assert res.status_code == 200
    assert "Google Form" in res.text
    assert "ऑटो-सबमिशन" in res.text

def test_prefilled_links_route(client):
    res = client.get("/google_forms/prefilled_links")
    assert res.status_code == 200
    assert "प्री-फिल्ड लिंक्स" in res.text
