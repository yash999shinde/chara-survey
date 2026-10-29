# -*- coding: utf-8 -*-
import re

MARATHI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

def extract_best_mobile(text: str) -> tuple[str, bool]:
    if not text:
        return ("", False)
    # 1. Translate Marathi digits
    s = text.translate(MARATHI_DIGITS)
    # 2. Fix letter substitutions
    s = s.replace("O", "0").replace("o", "0").replace("D", "0")
    s = s.replace("l", "1").replace("I", "1")
    s = s.replace("Z", "2").replace("z", "2")
    s = s.replace("S", "5").replace("s", "5")
    s = s.replace("B", "8")
    
    # Check for direct 10-digit number starting with 6-9
    m = re.search(r"\b([6-9]\d{9})\b", s)
    if m:
        return (m.group(1), True)
    
    # Check if prefixed by 1 or 91
    m1 = re.search(r"(?:^|[^\d])(?:1|91)?([6-9]\d{9})(?:$|[^\d])", s)
    if m1:
        return (m1.group(1), True)
        
    # Extract all digits
    digits = re.sub(r"\D", "", s)
    if len(digits) == 11 and digits[0] == "1" and digits[1] in "6789":
        return (digits[1:], True)
    if len(digits) == 12 and digits[:2] == "91" and digits[2] in "6789":
        return (digits[2:], True)
    if len(digits) == 10 and digits[0] in "6789":
        return (digits, True)
    if len(digits) >= 10:
        for i in range(len(digits) - 9):
            if digits[i] in "6789":
                return (digits[i:i+10], True)
        return (digits[:10], False)
    if len(digits) >= 6:
        return (digits, False)
    return ("", False)

test_strings = [
    "ATR २५/५< \"अ OFESISESEl— fy |॥१॥-॥६८॥८1॥३ 2०0-|- | —|3 lawu| ij) -|। |- | 11 | s",
    "22 RAK slo ART 8788250995 ।|2_7 9|-|-|-।॥5 ४० ०८- |- |2 ब्रि | ८- 2-|- |2-|-। | |- 6?",
    "[3) [eid stele] ART ५2५५८4९८८५ -'।|।|-|2-2 2 ॥5|2- —| -|t मो! ८! 1! | 1|-! [।_- (अ",
    "श््राध्य रग्ष AR 1749962 6207 | -[4।14|॥-|-।-| —| —lto] —| —| 2 आध HE | ci ml (|_--",
    "5) नबावष रख्बाब AW 7०220 21960 |-|।|॥|-॥-|-|।|। |5 ||७| —|- |- jae] el | -| oa oye",
    "[C) BRU कमावला 2 17972278S30-le le} ili ls ।25(20। —| —|2 श्रोद | --| | Ae) 7 |e) 7"
]

for idx, ts in enumerate(test_strings, 1):
    mob, valid = extract_best_mobile(ts)
    print(f"Row {idx}: Extracted Mobile = {mob} (valid={valid})")
