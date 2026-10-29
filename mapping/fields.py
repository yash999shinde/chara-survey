from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import pandas as pd

class MappingError(ValueError):
    pass

def load_mapping(path: str | Path) -> dict[str, str]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        mapping = raw["source_to_canonical"]
        if not isinstance(mapping, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
            raise ValueError("mapping must be a string-to-string object")
        return mapping
    except Exception as exc:
        raise MappingError("Field mapping configuration is invalid.") from exc

def map_columns(frame: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    known = {source: target for source, target in mapping.items() if source in frame.columns}
    if not known:
        raise MappingError("None of the input columns matched the configured field mapping.")
    renamed = frame.rename(columns=known).copy()
    targets = list(renamed.columns)
    if len(set(targets)) != len(targets):
        raise MappingError("Mapping creates duplicate canonical columns; resolve the source mapping first.")
    # Normalize blanks, but do not turn absent quantities into zero.
    for column in renamed.columns:
        renamed[column] = renamed[column].map(lambda value: value.strip() if isinstance(value, str) else value)
    return renamed

def canonical_to_db_record(row: dict[str, Any]) -> dict[str, Any]:
    """Convert canonical mapped row fields to SQLite farmers table fields."""
    def to_float(val, default=0.0):
        try:
            return float(val) if val not in (None, "") else default
        except (ValueError, TypeError):
            return default

    def to_int(val, default=0):
        try:
            return int(float(val)) if val not in (None, "") else default
        except (ValueError, TypeError):
            return default

    mob = str(row.get("mobile", "") or row.get("mobile_number", "")).strip()

    return {
        "taluka": str(row.get("taluka", "")).strip(),
        "veterinary_hospital": str(row.get("veterinary_hospital", "")).strip(),
        "revenue_circle": str(row.get("revenue_circle", "")).strip(),
        "village_name": str(row.get("village_name", "")).strip(),
        "farmer_name": str(row.get("farmer_name", "")).strip(),
        "mobile": mob,
        "cow_small": to_int(row.get("cow_small", 0)),
        "cow_large": to_int(row.get("cow_large", row.get("cattle_count", 0))),
        "buffalo_small": to_int(row.get("buffalo_small", 0)),
        "buffalo_large": to_int(row.get("buffalo_large", row.get("buffalo_count", 0))),
        "milch_animals": to_int(row.get("milch_animals", 0)),
        "dry_animals": to_int(row.get("dry_animals", 0)),
        "daily_milk_litres": to_float(row.get("daily_milk_litres", 0.0)),
        "goats": to_int(row.get("goats", 0)),
        "sheep_migratory": to_int(row.get("sheep_migratory", 0)),
        "sheep_confined": to_int(row.get("sheep_confined", 0)),
        "water_availability": str(row.get("water_availability", "")).strip(),
        "green_fodder_available": str(row.get("green_fodder_available", "")).strip(),
        "silage_available": str(row.get("silage_available", "")).strip(),
        "dry_fodder_available": str(row.get("dry_fodder_available", "")).strip(),
        "green_fodder_tonnes": to_float(row.get("green_fodder_tonnes", 0.0)),
        "silage_tonnes": to_float(row.get("silage_tonnes", 0.0)),
        "dry_fodder_tonnes": to_float(row.get("dry_fodder_tonnes", 0.0)),
        "fodder_for_sale_tonnes": to_float(row.get("fodder_for_sale_tonnes", 0.0)),
        "rabi_area_hectares": to_float(row.get("rabi_area_hectares", 0.0)),
        "irrigation_available": str(row.get("irrigation_available", row.get("irrigation_availability", ""))).strip(),
        "irrigation_types": str(row.get("irrigation_types", "")).strip(),
        "irrigation_other": str(row.get("irrigation_other", "")).strip(),
        "source_file": str(row.get("source_file", "")).strip(),
        "upload_batch_id": str(row.get("upload_batch_id", "")).strip(),
        "file_hash": str(row.get("file_hash", "")).strip(),
        "status": str(row.get("status", "pending_review")).strip(),
        "review_notes": str(row.get("validation_warnings", "") or row.get("review_notes", "")).strip()
    }
