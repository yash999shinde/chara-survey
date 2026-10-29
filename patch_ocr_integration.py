from pathlib import Path
from datetime import datetime
import shutil
import sys

app_path = Path("app/app.py")

if not app_path.is_file():
    sys.exit("ERROR: app/app.py nahi mila. Project folder check karein.")

source = app_path.read_text(encoding="utf-8")

start_marker = '        text_path.write_text(result["full_text"], encoding="utf-8")'
end_marker = "    except Exception as exc:"

if start_marker not in source:
    sys.exit("ERROR: Expected OCR code nahi mila. File modify nahi hui.")

start = source.index(start_marker)
end = source.find(end_marker, start)

if end == -1:
    sys.exit("ERROR: OCR exception handler nahi mila. File modify nahi hui.")

backup = app_path.with_name(
    f"app.py.bak_ocr_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)
shutil.copy2(app_path, backup)

replacement = '''        text_path.write_text(result["full_text"], encoding="utf-8")

        # Connect OCR output to the existing human-review queue.
        import json
        import re

        processed_dir = Path(__file__).resolve().parents[1] / "data" / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)

        candidate_id = Path(stored_name).stem
        mobile_candidates = sorted(set(re.findall(
            r"(?<!\\\\d)(?:\\\\+91[\\\\s-]?)?[6-9]\\\\d{9}(?!\\\\d)",
            result["full_text"],
        )))

        candidate_records = [{
            "candidate_id": candidate_id,
            "source_file": safe_name,
            "page_count": result["page_count"],
            "mobile_candidates": mobile_candidates,
            "raw_text": result["full_text"],
        }]

        candidate_path = processed_dir / f"{candidate_id}_candidates.json"
        candidate_path.write_text(
            json.dumps(candidate_records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return redirect(url_for("ocr_review_dashboard"))

'''

app_path.write_text(source[:start] + replacement + source[end:], encoding="utf-8")
print("SUCCESS: OCR output ab human-review queue se connected hai.")
print(f"Backup: {backup}")
