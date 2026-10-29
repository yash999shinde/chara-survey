"""Read CSV and Excel files while preserving Marathi text and phone numbers."""
from __future__ import annotations

from pathlib import Path
import pandas as pd

SUPPORTED_SUFFIXES = {".csv", ".xlsx", ".xlsm"}

class IngestionError(ValueError):
    """Raised when an input file cannot be safely ingested."""

def read_tabular(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.is_file():
        raise IngestionError("Input file does not exist.")
    if file_path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise IngestionError(f"Unsupported file type: {file_path.suffix or '(no extension)'}")
    try:
        if file_path.suffix.lower() == ".csv":
            # Read all cells as text to preserve leading zeroes and avoid type coercion.
            try:
                frame = pd.read_csv(file_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
            except UnicodeDecodeError:
                frame = pd.read_csv(file_path, dtype=str, keep_default_na=False, encoding="utf-8")
        else:
            frame = pd.read_excel(file_path, dtype=str, keep_default_na=False, engine="openpyxl")
    except Exception as exc:
        raise IngestionError(f"Could not read input file ({type(exc).__name__}).") from exc
    frame.columns = [str(c).strip() for c in frame.columns]
    if frame.empty:
        raise IngestionError("Input file has no data rows.")
    if any(not column for column in frame.columns):
        raise IngestionError("Input file contains an empty column name.")
    if len(set(frame.columns)) != len(frame.columns):
        raise IngestionError("Input file contains duplicate column names after trimming whitespace.")
    return frame
