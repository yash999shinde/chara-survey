# -*- coding: utf-8 -*-
"""Centralized Tesseract OCR detection and configuration."""
import os
import shutil
import logging
from pathlib import Path
import pytesseract

log = logging.getLogger("ocr_config")

_TESSERACT_CMD = None
_TESSDATA_DIR = None

def configure_tesseract() -> tuple[str | None, str | None]:
    """Detect and configure Tesseract executable and tessdata prefix."""
    global _TESSERACT_CMD, _TESSDATA_DIR

    candidate_exes = []
    
    # 1. Environment variable
    if os.environ.get("TESSERACT_CMD"):
        candidate_exes.append(Path(os.environ["TESSERACT_CMD"]))

    # 2. Local project roots & parent directories
    current_file = Path(__file__).resolve()
    for parent in [current_file.parent, current_file.parents[1], current_file.parents[2]]:
        candidate_exes.append(parent / "tesseract.exe")
        candidate_exes.append(parent / "Tesseract-OCR" / "tesseract.exe")

    # 3. Known workspace path
    candidate_exes.append(Path(r"D:\chara-survey-automation-phase1-2\tesseract.exe"))

    # 4. PATH lookup
    which_tess = shutil.which("tesseract")
    if which_tess:
        candidate_exes.append(Path(which_tess))

    # 5. Standard Windows Program Files
    candidate_exes.extend([
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        Path(os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe")),
    ])

    found_exe = None
    for cand in candidate_exes:
        try:
            if cand and cand.is_file():
                found_exe = cand.resolve()
                break
        except Exception:
            continue

    if found_exe:
        _TESSERACT_CMD = str(found_exe)
        pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD
    else:
        log.warning("Tesseract binary not found in candidate paths.")

    # Locate tessdata
    candidate_data = []
    if os.environ.get("TESSDATA_PREFIX"):
        candidate_data.append(Path(os.environ["TESSDATA_PREFIX"]))

    if found_exe:
        candidate_data.append(found_exe.parent / "tessdata")
        candidate_data.append(found_exe.parent.parent / "tessdata")

    current_file = Path(__file__).resolve()
    for parent in [current_file.parent, current_file.parents[1], current_file.parents[2]]:
        candidate_data.append(parent / "tessdata")

    candidate_data.extend([
        Path(r"D:\chara-survey-automation-phase1-2\tessdata"),
        Path(r"C:\Program Files\Tesseract-OCR\tessdata"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tessdata"),
    ])

    found_data = None
    for cand in candidate_data:
        try:
            if cand and cand.is_dir() and ((cand / "eng.traineddata").exists() or (cand / "mar.traineddata").exists()):
                found_data = cand.resolve()
                break
        except Exception:
            continue

    if found_data:
        _TESSDATA_DIR = str(found_data)
        os.environ["TESSDATA_PREFIX"] = _TESSDATA_DIR
    else:
        log.warning("Tessdata directory not found in candidate paths.")

    return _TESSERACT_CMD, _TESSDATA_DIR

def is_tesseract_available() -> bool:
    cmd, _ = configure_tesseract()
    return cmd is not None and os.path.isfile(cmd)

# Auto-configure on import
configure_tesseract()
