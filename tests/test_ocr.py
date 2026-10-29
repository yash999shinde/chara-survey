# -*- coding: utf-8 -*-
from pathlib import Path
import pytest
from pipeline.ocr_config import configure_tesseract, is_tesseract_available
from pipeline.extractor import (
    clean_marathi_name,
    extract_mobile_number,
    extract_document,
    clean_str
)

ROOT = Path(__file__).resolve().parents[1]

def test_tesseract_configured():
    cmd, tessdata = configure_tesseract()
    assert is_tesseract_available()
    assert cmd is not None
    assert Path(cmd).is_file()

def test_clean_marathi_name():
    raw_1 = "1) अमोल विठ्ठल पाटील"
    assert clean_marathi_name(raw_1) == "अमोल विठ्ठल पाटील"

    raw_2 = "[2] | समीर जमाल शेख |"
    assert clean_marathi_name(raw_2) == "समीर जमाल शेख"

    raw_3 = "   "
    assert clean_marathi_name(raw_3) == ""

def test_extract_mobile_number():
    # Valid 10-digit
    mob, valid = extract_mobile_number("फोन 9876543210")
    assert mob == "9876543210"
    assert valid is True

    # Marathi digits
    mob_mar, valid_mar = extract_mobile_number("९०९६५१५८५८")
    assert mob_mar == "9096515858"
    assert valid_mar is True

    # OCR letters substitution (O -> 0, I -> 1, B -> 8)
    mob_sub, _ = extract_mobile_number("B788250995")
    assert mob_sub == "8788250995"

    # Empty
    mob_empty, valid_empty = extract_mobile_number("कोणताही नंबर नाही")
    assert mob_empty == ""
    assert valid_empty is False

def test_no_fabricated_default_values(tmp_path):
    # Test on a real survey PDF if exists
    real_pdf = ROOT / "data" / "uploads" / "20261028_070119_bhiya.pdf"
    if real_pdf.exists():
        result = extract_document(real_pdf)
        records = result.get("records", [])
        assert len(records) > 0
        for r in records:
            # Must NOT fabricate fake hardcoded names for all rows
            assert "आशिष शब्बीर शेख" not in r["farmer_name"] or r["farmer_name"] != records[-1]["farmer_name"]
            # Must be valid dictionary
            assert "farmer_name" in r
            assert "mobile" in r
            assert "status" in r
