from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional
import sqlite3

import pandas as pd

STATUSES = {
    "needs_review",
    "verified",
    "ready",
    "submitted",
    "failed",
    "needs_check",
}

def load_rules(path: str | Path) -> dict[str, Any]:
    try:
        rules = json.loads(
            Path(path).read_text(encoding="utf-8-sig")
        )

        required_keys = {
            "required_fields",
            "mobile_regex",
            "numeric_fields",
            "integer_fields",
            "allowed_values",
        }

        if not required_keys.issubset(rules):
            raise ValueError("Missing validation configuration keys.")

        return rules

    except Exception as exc:
        raise ValueError(
            "Validation configuration is invalid."
        ) from exc


def validate_records(
    frame: pd.DataFrame,
    rules: dict[str, Any],
    check_db_duplicates: bool = False,
    db_conn: Optional[sqlite3.Connection] = None,
) -> pd.DataFrame:
    result = frame.copy()

    errors: list[str] = []
    warnings: list[str] = []
    statuses: list[str] = []

    seen_ids: set[str] = set()
    seen_mobile: set[str] = set()

    for _, row in result.iterrows():
        row_errors: list[str] = []
        row_warnings: list[str] = []

        # 1. Check required fields
        for field in rules.get("required_fields", []):
            value = row.get(field)

            if (
                field not in result.columns
                or pd.isna(value)
                or str(value).strip() == ""
            ):
                row_errors.append(f"missing_required:{field}")

        # 2. Check duplicate record IDs within the batch
        record_id_value = row.get("record_id")
        record_id = (
            ""
            if pd.isna(record_id_value)
            else str(record_id_value).strip()
        )

        if record_id:
            if record_id in seen_ids:
                row_errors.append("duplicate_record_id")
            seen_ids.add(record_id)

        # 3. Validate mobile numbers and flag duplicates within batch
        mobile_value = row.get("mobile_number") if "mobile_number" in row else row.get("mobile")
        mobile = (
            ""
            if pd.isna(mobile_value)
            else str(mobile_value).strip()
        )

        if mobile:
            if not re.fullmatch(rules.get("mobile_regex", r"^[6-9][0-9]{9}$"), mobile):
                row_errors.append("invalid_mobile_format")

            if mobile in seen_mobile:
                row_warnings.append("potential_duplicate_mobile")

            seen_mobile.add(mobile)

        # 4. Check duplicates against existing database if requested
        if check_db_duplicates:
            farmer_n = str(row.get("farmer_name", "")).strip()
            village_n = str(row.get("village_name", "")).strip()
            try:
                from app.db import check_duplicate_in_db
                is_dup, dup_reasons = check_duplicate_in_db(mobile, farmer_n, village_n, conn=db_conn)
                if is_dup:
                    for r in dup_reasons:
                        row_warnings.append(f"db_duplicate:{r}")
            except Exception:
                pass

        # 5. Validate numeric fields
        for field in rules.get("numeric_fields", []):
            if field not in result.columns:
                continue

            value = row.get(field)

            # Missing data stays missing; never replace it with zero.
            if pd.isna(value) or str(value).strip() == "":
                row_warnings.append(f"missing_numeric:{field}")
                continue

            raw = str(value).strip()

            try:
                number = float(raw)

                if number < 0:
                    row_errors.append(f"negative_value:{field}")

                if (
                    field in rules.get("integer_fields", [])
                    and not number.is_integer()
                ):
                    row_errors.append(f"not_integer:{field}")

            except (TypeError, ValueError):
                row_errors.append(f"invalid_number:{field}")

        # 6. Validate configured dropdown/options
        for field, allowed in rules.get("allowed_values", {}).items():
            if field not in result.columns:
                continue

            value = row.get(field)

            if pd.isna(value) or str(value).strip() == "":
                continue

            if str(value).strip() not in allowed:
                row_errors.append(f"invalid_option:{field}")

        # 7. Determine review status
        errors.append(";".join(row_errors))
        warnings.append(";".join(row_warnings))

        if row_errors or row_warnings:
            statuses.append("needs_review")
        else:
            statuses.append("ready")

    result["validation_errors"] = errors
    result["validation_warnings"] = warnings
    result["status"] = statuses

    return result
