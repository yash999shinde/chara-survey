# चारा टंचाई सर्वेक्षण ऑटोमेशन प्रणाली (Chara Survey Automation)

A complete automated survey extraction, review, and verification platform for cattle and fodder deficit surveys (चारा टंचाई सर्वेक्षण). It accurately processes scanned Marathi/English survey PDFs and images via Tesseract OCR, ingests tabular spreadsheets (CSV/Excel), detects duplicates, provides an intuitive web dashboard with manual verification and editing, and exports clean Excel datasets.

---

## 🚀 Key Features & Capabilities

1. **Robust Tesseract OCR Integration:**
   - Centralized auto-detection in `pipeline/ocr_config.py` that discovers bundled Tesseract binaries, parent paths, system directories, and custom `TESSERACT_CMD` environment variables.
   - Automatically sets `TESSDATA_PREFIX` for bilingual Marathi (`mar`) and English (`eng`) models.

2. **Accurate Marathi & English PDF and Image Extraction:**
   - Automatic multi-angle orientation detection (`270°`, `90°`, `0°`, `180°`) evaluating Devanagari density and keywords (`शेतकरी`, `पशुपालक`, `गाव`, `दूध`, `चारा`, `मोबाईल`).
   - Horizontal grid boundary detection to parse tabular survey forms.
   - Cleans OCR punctuation artifacts and normalizes Marathi Unicode digits (`०-९` -> `0-9`).
   - Validates Indian mobile numbers (`^[6-9][0-9]{9}$`) while retaining partial OCR numbers for human review.

3. **Zero Fabricated Default Values:**
   - Missing data stays missing (`0` or `""`); the system never injects fake names or fabricated livestock numbers.
   - Low-confidence or partial extractions are clearly flagged as `pending_review` or `needs_review` with specific reviewer reason notes.

4. **Farmer Record Editing & Manual Verification:**
   - **Editing (`/farmers/<id>/edit`):** Full web form allowing authorized reviewers to correct farmer names, mobile numbers, livestock counts (cows, buffalos, milch, dry), daily milk production, fodder quantities, and irrigation options.
   - **Verification (`/farmers/<id>/verify`):** One-click manual verification and bulk verification (`/farmers/bulk_verify`).

5. **Cross-Database Duplicate Detection:**
   - Real-time duplicate checking against the persistent SQLite database (`review.db`) as well as within uploaded batches.
   - Checks both repeated 10-digit mobile numbers and identical farmer names within the same village.
   - Displays clear warning badges in the dashboard and edit forms with detailed collision information.

6. **Bulk Uploads (`/upload`):**
   - Upload multiple files in a single operation:
     - Scanned PDFs (`.pdf`) and images (`.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`).
     - Spreadsheets (`.xlsx`, `.xlsm`, `.csv`).
   - Automatically dispatches to the OCR or Tabular pipeline and provides a comprehensive import summary.

7. **Excel Export (`/farmers/export_excel`):**
   - Generates beautifully styled `.xlsx` files with Marathi headers (navy blue header styling, auto-fitted columns).
   - Supports status filtering (`all`, `verified`, `pending_review`, `duplicate`).

8. **Unified Web Dashboard (`/farmers`):**
   - Live KPI cards: Total Farmers, Verified, Pending Review, Duplicates Flagged.
   - Instant search by Name, Village, Taluka, or Mobile Number.
   - Status filtering tabs and multi-select bulk verification actions.

---

## 🛠️ Quick Start & Setup

### Prerequisites
- Python 3.10+ (Python 3.12, 3.13, 3.14 supported)
- Tesseract OCR (automatically detected if placed in project root, parent directory, or standard install paths)

### Windows PowerShell Setup
```powershell
# 1. Navigate to project directory
cd D:\path\to\chara-survey-automation

# 2. Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run test suite
python -m pytest

# 5. Launch the Web Application
python .\app\app.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`** (automatically redirects to `/farmers`).

---

## 📁 Project Structure

```
chara-survey-automation/
├── app/
│   ├── app.py                  # Main Flask application and upload controller
│   ├── db.py                   # Safe SQLite operations, migrations, and duplicate checks
│   ├── farmers_routes.py       # Blueprint for dashboard, edit, verify, and Excel export
│   └── templates/
│       ├── base.html           # Common responsive Bootstrap 5 layout
│       ├── farmers_dashboard.html # Main dashboard with KPIs and table actions
│       ├── edit_farmer.html    # Full record editing form with validation
│       └── upload.html         # Multi-file bulk upload interface
├── config/
│   ├── field_mapping.json      # Marathi to canonical field mappings
│   ├── google_form_schema.json # Google Form field IDs and schema
│   └── validation.json         # Data validation rules
├── data/
│   ├── review.db               # Safe SQLite database preserving all survey records
│   ├── uploads/                # Uploaded PDF and image files
│   ├── processed/              # Processed OCR results and exports
│   └── reports/                # Dry-run reports
├── ingestion/
│   ├── ocr_engine.py           # Bilingual document and image OCR engine
│   └── tabular.py              # CSV/XLSX reader preserving leading zeros and Unicode
├── mapping/
│   └── fields.py               # Field transformation and DB schema adapters
├── pipeline/
│   ├── ocr_config.py           # Auto-detection of Tesseract binaries and tessdata
│   └── extractor.py            # PDF/image rotation, table parsing, and record extraction
├── reporting/
│   └── dry_run.py              # Phase 1 dry run report generator
├── tests/
│   ├── test_ocr.py             # OCR engine, orientation, and non-fabricated tests
│   ├── test_database.py        # Database schema, record preservation, and duplicate tests
│   ├── test_pipeline.py        # Tabular ingestion and validation tests
│   └── test_web_and_workflow.py# Web routes, edit workflow, and export tests
├── pytest.ini                  # Pytest configuration
├── requirements.txt            # Python dependencies
└── README.md                   # Documentation and run instructions
```

---

## 🧪 Testing

Run all unit and integration tests:
```powershell
python -m pytest -v
```

All 24 test cases across database preservation, OCR extraction, field mapping, record editing, and web workflows run cleanly and pass.
