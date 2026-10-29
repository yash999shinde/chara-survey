# -*- coding: utf-8 -*-
from pathlib import Path
import re

extractor_path = Path("pipeline/extractor.py")
content = extractor_path.read_text(encoding="utf-8")

# Naya robust parse_row logic jo garbage filter karega aur numbers accurately map karega
new_parse_row = '''
def parse_row(words, page_no, row_no):
    tokens = [w["t"] for w in words]
    joined = " ".join(tokens)
    
    # 1. Header rows drop karo
    if sum(1 for h in HEADER_WORDS if h in joined) >= 3:
        return None

    # 2. Extract mobile number (10 digits)
    mobile, mob_idx = find_mobile(tokens)

    # 3. Clean Marathi Farmer Name (Strict Devanagari only, ignore English noise/single chars)
    name_tokens = []
    number_tokens = []
    
    for idx, t in enumerate(tokens):
        if idx in mob_idx:
            continue
        
        # Check if it is a number
        num_val = _num(t)
        if num_val is not None:
            number_tokens.append(num_val)
            continue
            
        # Ignore irrigation and water keywords from name
        if _irrigation(t) or t in WATER_NO or t in WATER_YES:
            continue
            
        # Only accept genuine Marathi words (Devanagari length >= 2, no English junk)
        dev_chars = len(re.findall(r"[\u0900-\u097F]", t))
        if dev_chars >= 2 and not re.search(r"[A-Za-z]", t):
            name_tokens.append(t)

    farmer_name = clean_text(" ".join(name_tokens)).strip(" .,:;|_-")

    # Agar valid Devnagari name nahi mila to ye row survey row nahi hai
    if len(re.findall(r"[\u0900-\u097F]", farmer_name)) < 3:
        return None

    # Agar mobile number missing tha to raw text me dobara 10 digit dhundo
    if not mobile:
        m = re.search(r"[6-9]\d{9}", to_ascii_digits(joined))
        if m:
            mobile = m.group(0)

    # Build Record
    rec = {k: "" for k in RECORD_KEYS}
    rec["farmer_name"] = farmer_name
    rec["mobile"] = mobile

    # Assign numbers in order to numeric columns (Cow, Buffalo, Milk, etc.)
    for key, val in zip(NUMERIC_COLUMNS, number_tokens):
        if key:
            rec[key] = val

    # Irrigation and water availability
    for t in tokens:
        irr = _irrigation(t)
        if irr and not rec["irrigation_type"]:
            rec["irrigation_type"] = irr
        elif t in WATER_NO:
            rec["water_availability"] = "नाही"
        elif t in WATER_YES:
            rec["water_availability"] = "उपलब्ध"

    confs = [w["c"] for w in words]
    rec["candidate_id"] = ""
    rec["source_page"] = page_no
    rec["confidence"] = round(sum(confs) / len(confs), 1) if confs else ""
    rec["raw_text"] = clean_text(joined)
    return rec
'''

# Replace parse_row function cleanly
pattern = r"def parse_row\(words, page_no, row_no\):[\s\S]*?(?=\n# ---|\ndef extract_labeled|\Z)"
if re.search(pattern, content):
    updated = re.sub(pattern, new_parse_row.strip() + "\n\n", content, count=1)
    extractor_path.write_text(updated, encoding="utf-8")
    print("[SUCCESS] pipeline/extractor.py me parse_row update ho gaya!")
else:
    print("[!] parse_row pattern match nahi hua, check extractor.py structure.")