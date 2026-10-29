# -*- coding: utf-8 -*-
"""Test Marathi name dictionary and contextual refinement."""
import json
import difflib
from pathlib import Path

COMMON_SURNAMES = [
    "शेख", "पाटील", "कदम", "पवार", "शिंदे", "गायकवाड", "जगताप", "काळे", 
    "जाधव", "चव्हाण", "थोरात", "भोसले", "मोरे", "वाघ", "म्हस्के", "साळुंके",
    "तांबोळी", "पठाण", "इनामदार", "मणेर", "मुजावर", "बागवान"
]

COMMON_GIVEN_NAMES = [
    "आशिष", "समीर", "लतीफ", "इब्राहिम", "नबाब", "बशीर", "शब्बीर", "जमाल", 
    "रुबाब", "कमाल", "सादिक", "रफिक", "हुसेन", "अकबर", "अन्वर", "मुनीर",
    "गणेश", "सुरेश", "रमेश", "पांडुरंग", "बाळू", "किसन", "दत्तात्रय", "रामदास",
    "विठ्ठल", "ज्ञानेश्वर", "नामदेव", "संभाजी", "भाऊसाहेब", "गोरख", "अशोक"
]

def refine_marathi_word(token: str, dictionary: list[str], cutoff: float = 0.6) -> tuple[str, float]:
    token = token.strip()
    if not token or len(token) < 2:
        return token, 0.0
    matches = difflib.get_close_matches(token, dictionary, n=1, cutoff=cutoff)
    if matches:
        ratio = difflib.SequenceMatcher(None, token, matches[0]).ratio()
        return matches[0], ratio
    return token, 0.0

def refine_marathi_name(raw_name: str) -> dict:
    tokens = raw_name.split()
    refined_tokens = []
    total_score = 0.0
    suggestions = []

    for idx, token in enumerate(tokens):
        # Last token is typically surname
        dict_to_use = COMMON_SURNAMES if idx == len(tokens) - 1 else COMMON_GIVEN_NAMES
        matched, score = refine_marathi_word(token, dict_to_use)
        if score >= 0.55:
            refined_tokens.append(matched)
            suggestions.append(f"{token}->{matched} ({int(score*100)}%)")
            total_score += score
        else:
            refined_tokens.append(token)
            total_score += 0.3

    confidence = (total_score / len(tokens)) if tokens else 0.0
    suggested_name = " ".join(refined_tokens)

    return {
        "raw_name": raw_name,
        "suggested_name": suggested_name,
        "confidence": round(confidence, 2),
        "refinements": suggestions
    }

# Test on the extracted names
test_cases = [
    "डत 1२ ६ न( < नभ",
    "समान जाबाल शग",
    "ल॑न ७ जनास राख",
    "श्गाह्य रगवा शाक",
    "वाव रुबाब श ख",
    "शार माल राख"
]

results = [refine_marathi_name(tc) for tc in test_cases]
Path("data/processed/test_name_refinement_out.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print("Saved data/processed/test_name_refinement_out.json")
