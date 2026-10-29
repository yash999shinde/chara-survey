import json
import re
from pathlib import Path

OCR_DIR = Path("data/ocr_output")
OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_candidate_records(text):
    # Split on blank lines; each block is an unverified candidate.
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    records = []

    for index, block in enumerate(blocks, start=1):
        mobile_candidates = re.findall(r"(?<!\d)[6-9]\d{9}(?!\d)", block)
        records.append({
            "candidate_id": f"OCR-{index:04d}",
            "raw_text": block,
            "mobile_candidates": mobile_candidates,
            "review_status": "pending_human_review",
            "verified": False,
        })

    return records

def main():
    text_files = sorted(OCR_DIR.glob("*.txt"))
    if not text_files:
        raise SystemExit(
            "No OCR text files found in data/ocr_output. Run OCR first."
        )

    for text_file in text_files:
        text = text_file.read_text(encoding="utf-8")
        records = extract_candidate_records(text)

        output_file = OUTPUT_DIR / f"{text_file.stem}_candidates.json"
        output_file.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"Source: {text_file.name}")
        print(f"Candidate blocks: {len(records)}")
        print(f"Saved: {output_file}")

if __name__ == "__main__":
    main()
