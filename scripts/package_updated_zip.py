# -*- coding: utf-8 -*-
"""Create clean updated project ZIP excluding virtualenvs and temporary caches."""
import os
import shutil
import zipfile
from pathlib import Path

SOURCE_DIR = Path(r"D:\chara-survey-automation-phase1-2\chara-survey-automation")
OUTPUT_ZIP = Path(r"D:\chara-survey-automation-phase1-2\chara-survey-automation-updated.zip")
ARTIFACT_DIR = Path(r"C:\Users\user\.gemini\antigravity\brain\65a51e8d-118a-41f0-ac28-79f7640bbaf2")
ARTIFACT_ZIP = ARTIFACT_DIR / "chara-survey-automation-updated.zip"

EXCLUDE_DIRS = {
    ".venv",
    ".pytest_cache",
    "__pycache__",
    ".git",
}

EXCLUDE_EXTS = {
    ".pyc",
    ".pyo",
}

print(f"Packaging {SOURCE_DIR} into {OUTPUT_ZIP}...")

if OUTPUT_ZIP.exists():
    OUTPUT_ZIP.unlink()

file_count = 0
with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(SOURCE_DIR):
        # Modify dirs in-place to skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".venv")]

        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() in EXCLUDE_EXTS:
                continue

            rel_path = file_path.relative_to(SOURCE_DIR.parent)
            zipf.write(file_path, arcname=str(rel_path))
            file_count += 1

print(f"Packaged {file_count} files into {OUTPUT_ZIP} ({OUTPUT_ZIP.stat().st_size / (1024*1024):.2f} MB)")

# Copy to artifact dir
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
shutil.copy2(OUTPUT_ZIP, ARTIFACT_ZIP)
print(f"Copied updated ZIP to artifact directory: {ARTIFACT_ZIP}")
