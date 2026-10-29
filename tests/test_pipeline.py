from pathlib import Path
import pandas as pd
import pytest
from ingestion.tabular import read_tabular, IngestionError
from mapping.fields import map_columns
from validation.engine import validate_records
from reporting.dry_run import write_dry_run_report

ROOT = Path(__file__).resolve().parents[1]

def test_csv_marathi_and_mobile_preserved():
    df = read_tabular(ROOT / "data/input/sample_farmers.csv")
    assert df.iloc[0]["शेतकऱ्याचे नाव"] == "अमोल पाटील"
    assert df.iloc[0]["मोबाईल क्रमांक"] == "9876543210"

def test_excel_ingestion(tmp_path):
    source = tmp_path / "input.xlsx"
    pd.DataFrame({"record_id": ["X1"], "गाव": ["पुणे"]}).to_excel(source, index=False)
    result = read_tabular(source)
    assert result.iloc[0]["गाव"] == "पुणे"

def test_unsupported_file_rejected(tmp_path):
    source = tmp_path / "records.pdf"
    source.write_text("not a pdf")
    with pytest.raises(IngestionError):
        read_tabular(source)

def test_validation_flags_bad_data_and_duplicate_mobile():
    frame = pd.DataFrame([
        {"record_id":"1", "village_name":"गाव", "farmer_name":"नाव", "mobile_number":"9876543210", "cattle_count":"1", "daily_milk_litres":"1.5"},
        {"record_id":"2", "village_name":"गाव", "farmer_name":"नाव", "mobile_number":"9876543210", "cattle_count":"-1", "daily_milk_litres":"abc"}
    ])
    rules = {"required_fields":["record_id","village_name","farmer_name"], "mobile_regex":"^[6-9][0-9]{9}$", "numeric_fields":["cattle_count","daily_milk_litres"], "integer_fields":["cattle_count"], "allowed_values":{}}
    result = validate_records(frame, rules)
    assert result.iloc[0]["status"] == "ready"
    assert "potential_duplicate_mobile" in result.iloc[1]["validation_warnings"]
    assert "negative_value:cattle_count" in result.iloc[1]["validation_errors"]
    assert "invalid_number:daily_milk_litres" in result.iloc[1]["validation_errors"]

def test_missing_values_are_not_replaced_with_zero():
    frame = pd.DataFrame([{"record_id":"1", "village_name":"गाव", "farmer_name":"नाव", "green_fodder_tonnes":""}])
    rules = {"required_fields":["record_id","village_name","farmer_name"], "mobile_regex":"^[6-9][0-9]{9}$", "numeric_fields":["green_fodder_tonnes"], "integer_fields":[], "allowed_values":{}}
    result = validate_records(frame, rules)
    assert result.iloc[0]["green_fodder_tonnes"] == ""

def test_mapping_detects_collision():
    frame = pd.DataFrame({"गाव":["गाव"], "गावाचे नाव":["गाव"]})
    with pytest.raises(ValueError):
        map_columns(frame, {"गाव":"village_name", "गावाचे नाव":"village_name"})

def test_report_masks_mobile_and_is_dry_run(tmp_path):
    frame = pd.DataFrame([{"record_id":"1", "mobile_number":"9876543210", "status":"ready", "validation_warnings":"", "validation_errors":""}])
    detail, summary = write_dry_run_report(frame, tmp_path, "farmers.csv")
    assert "******10" in detail.read_text(encoding="utf-8-sig")
    assert "ready_for_human_approval,1" in summary.read_text(encoding="utf-8-sig")
