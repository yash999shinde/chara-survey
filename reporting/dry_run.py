from __future__ import annotations
from pathlib import Path
import pandas as pd

SENSITIVE_FIELDS = {"mobile_number", "phone", "phone_number"}

def write_dry_run_report(records: pd.DataFrame, output_dir: str | Path, source_name: str) -> tuple[Path, Path]:
    """Write a per-record review CSV and aggregate summary; never submits records."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c for c in Path(source_name).stem if c.isalnum() or c in "-_ ").strip().replace(" ", "_") or "import"
    detail_path = out / f"{safe_name}_dry_run.csv"
    summary_path = out / f"{safe_name}_summary.csv"
    export = records.copy()
    for field in SENSITIVE_FIELDS.intersection(export.columns):
        export[field] = export[field].map(lambda x: ("******" + str(x)[-2:]) if str(x).strip() else "")
    export.to_csv(detail_path, index=False, encoding="utf-8-sig")
    statuses = records.get("status", pd.Series(dtype=str)).fillna("")
    summary = pd.DataFrame([
        {"metric": "total_records", "count": int(len(records))},
        {"metric": "needs_review", "count": int((statuses == "needs_review").sum())},
        {"metric": "ready_for_human_approval", "count": int((statuses == "ready").sum())},
        {"metric": "submitted", "count": int((statuses == "submitted").sum())},
        {"metric": "failed", "count": int((statuses == "failed").sum())},
        {"metric": "needs_check", "count": int((statuses == "needs_check").sum())},
        {"metric": "potential_duplicate_records", "count": int(records.get("validation_warnings", pd.Series(dtype=str)).astype(str).str.contains("potential_duplicate_mobile").sum())}
    ])
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    return detail_path, summary_path
