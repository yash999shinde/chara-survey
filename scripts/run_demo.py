from __future__ import annotations
import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ingestion.tabular import read_tabular
from mapping.fields import load_mapping, map_columns
from validation.engine import load_rules, validate_records
from reporting.dry_run import write_dry_run_report

def main() -> int:
    parser = argparse.ArgumentParser(description="Import and validate survey records in dry-run mode; no form submissions are performed.")
    parser.add_argument("input", nargs="?", default=str(ROOT / "data" / "input" / "sample_farmers.csv"))
    parser.add_argument("--mapping", default=str(ROOT / "config" / "field_mapping.json"))
    parser.add_argument("--rules", default=str(ROOT / "config" / "validation.json"))
    parser.add_argument("--output-dir", default=str(ROOT / "data" / "reports"))
    args = parser.parse_args()
    try:
        source = Path(args.input)
        raw = read_tabular(source)
        canonical = map_columns(raw, load_mapping(args.mapping))
        validated = validate_records(canonical, load_rules(args.rules))
        detail, summary = write_dry_run_report(validated, args.output_dir, source.name)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Imported records: {len(validated)}")
    print(f"Ready for human review: {(validated['status'] == 'ready').sum()}")
    print(f"Needs review: {(validated['status'] == 'needs_review').sum()}")
    print("Mode: DRY RUN ONLY — no Google Form submissions are implemented.")
    print(f"Detail report: {detail}")
    print(f"Summary report: {summary}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
