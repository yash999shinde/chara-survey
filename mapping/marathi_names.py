# -*- coding: utf-8 -*-
"""Marathi Name Recognition & Fuzzy Disambiguation Dictionary for Maharashtra Farmers."""
from __future__ import annotations
import difflib
import re

COMMON_SURNAMES = [
    "शेख", "पाटील", "कदम", "पवार", "शिंदे", "गायकवाड", "जगताप", "काळे", 
    "जाधव", "चव्हाण", "थोरात", "भोसले", "मोरे", "वाघ", "म्हस्के", "साळुंके",
    "तांबोळी", "पठाण", "इनामदार", "मणेर", "मुजावर", "बागवान", "सय्यद", "कुरेशी",
    "लोखंडे", "कुलकर्णी", "देशमुख", "गांधी", "गव्हाणे", "बोंद्रे", "वाळके"
]

COMMON_GIVEN_NAMES = [
    "आशिष", "समीर", "लतीफ", "इब्राहिम", "नबाब", "बशीर", "शब्बीर", "जमाल", 
    "रुबाब", "कमाल", "सादिक", "रफिक", "हुसेन", "अकबर", "अन्वर", "मुनीर",
    "गणेश", "सुरेश", "रमेश", "पांडुरंग", "बाळू", "किसन", "दत्तात्रय", "रामदास",
    "विठ्ठल", "ज्ञानेश्वर", "नामदेव", "संभाजी", "भाऊसाहेब", "गोरख", "अशोक",
    "प्रकाश", "सुनील", "संजय", "सचिन", "अमोल", "संदीप", "दीपक", "योगेश"
]

def refine_marathi_word(token: str, dictionary: list[str], cutoff: float = 0.55) -> tuple[str, float]:
    """Find the best fuzzy match for an OCR token in a Marathi name dictionary."""
    token = token.strip()
    if not token or len(token) < 2:
        return token, 0.0
    matches = difflib.get_close_matches(token, dictionary, n=1, cutoff=cutoff)
    if matches:
        ratio = difflib.SequenceMatcher(None, token, matches[0]).ratio()
        return matches[0], ratio
    return token, 0.0

def refine_marathi_name(raw_name: str) -> dict:
    """
    Suggest spelling corrections for noisy OCR Marathi farmer names.
    Does not invent names; only refines words with strong phonetic or visual similarity.
    """
    clean_tokens = [t for t in re.split(r"[\s\|\.,\-_]+", raw_name.strip()) if t]
    if not clean_tokens:
        return {
            "raw_name": raw_name,
            "suggested_name": raw_name,
            "confidence": 0.0,
            "refinements": []
        }

    refined_tokens = []
    total_score = 0.0
    suggestions = []

    for idx, token in enumerate(clean_tokens):
        # Last token is typically surname
        dict_to_use = COMMON_SURNAMES if idx == len(clean_tokens) - 1 else COMMON_GIVEN_NAMES
        matched, score = refine_marathi_word(token, dict_to_use)
        if score >= 0.55:
            refined_tokens.append(matched)
            if matched != token:
                suggestions.append(f"{token}->{matched} ({int(score*100)}%)")
            total_score += score
        else:
            refined_tokens.append(token)
            total_score += 0.3

    confidence = round(total_score / len(clean_tokens), 2)
    suggested_name = " ".join(refined_tokens)

    return {
        "raw_name": raw_name,
        "suggested_name": suggested_name,
        "confidence": confidence,
        "refinements": suggestions
    }
