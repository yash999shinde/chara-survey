# -*- coding: utf-8 -*-
"""Safe SQLite Database Storage and Operations for Chara Survey Automation."""
import os
import sqlite3
import json
import datetime
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "review.db"

# Canonical schema definition for 'farmers' table
FARMER_COLUMNS = [
    ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
    ("taluka", "TEXT DEFAULT ''"),
    ("veterinary_hospital", "TEXT DEFAULT ''"),
    ("revenue_circle", "TEXT DEFAULT ''"),
    ("village_name", "TEXT DEFAULT ''"),
    ("farmer_name", "TEXT NOT NULL DEFAULT ''"),
    ("mobile", "TEXT DEFAULT ''"),
    ("cow_small", "INTEGER DEFAULT 0"),
    ("cow_large", "INTEGER DEFAULT 0"),
    ("buffalo_small", "INTEGER DEFAULT 0"),
    ("buffalo_large", "INTEGER DEFAULT 0"),
    ("milch_animals", "INTEGER DEFAULT 0"),
    ("dry_animals", "INTEGER DEFAULT 0"),
    ("daily_milk_litres", "REAL DEFAULT 0.0"),
    ("goats", "INTEGER DEFAULT 0"),
    ("sheep_migratory", "INTEGER DEFAULT 0"),
    ("sheep_confined", "INTEGER DEFAULT 0"),
    ("water_availability", "TEXT DEFAULT ''"),
    ("green_fodder_available", "TEXT DEFAULT ''"),
    ("silage_available", "TEXT DEFAULT ''"),
    ("dry_fodder_available", "TEXT DEFAULT ''"),
    ("green_fodder_tonnes", "REAL DEFAULT 0.0"),
    ("silage_tonnes", "REAL DEFAULT 0.0"),
    ("dry_fodder_tonnes", "REAL DEFAULT 0.0"),
    ("fodder_for_sale_tonnes", "REAL DEFAULT 0.0"),
    ("rabi_area_hectares", "REAL DEFAULT 0.0"),
    ("irrigation_available", "TEXT DEFAULT ''"),
    ("irrigation_types", "TEXT DEFAULT ''"),
    ("irrigation_other", "TEXT DEFAULT ''"),
    ("source_file", "TEXT DEFAULT ''"),
    ("upload_batch_id", "TEXT DEFAULT ''"),
    ("file_hash", "TEXT DEFAULT ''"),
    ("raw_ocr_text", "TEXT DEFAULT ''"),
    ("uncertain_fields", "TEXT DEFAULT ''"),
    ("status", "TEXT DEFAULT 'pending_review'"),
    ("review_notes", "TEXT DEFAULT ''"),
    ("is_duplicate", "INTEGER DEFAULT 0"),
    ("duplicate_reason", "TEXT DEFAULT ''"),
    ("created_at", "TEXT DEFAULT ''"),
    ("updated_at", "TEXT DEFAULT ''")
]

def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Return an open SQLite connection with Row factory."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize database tables and safely add any missing columns."""
    with get_connection(db_path) as conn:
        # 1. Create farmers table if not exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS farmers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                taluka TEXT DEFAULT '',
                veterinary_hospital TEXT DEFAULT '',
                revenue_circle TEXT DEFAULT '',
                village_name TEXT DEFAULT '',
                farmer_name TEXT NOT NULL DEFAULT '',
                mobile TEXT DEFAULT '',
                cow_small INTEGER DEFAULT 0,
                cow_large INTEGER DEFAULT 0,
                buffalo_small INTEGER DEFAULT 0,
                buffalo_large INTEGER DEFAULT 0,
                milch_animals INTEGER DEFAULT 0,
                dry_animals INTEGER DEFAULT 0,
                daily_milk_litres REAL DEFAULT 0.0,
                goats INTEGER DEFAULT 0,
                sheep_migratory INTEGER DEFAULT 0,
                sheep_confined INTEGER DEFAULT 0,
                water_availability TEXT DEFAULT '',
                green_fodder_available TEXT DEFAULT '',
                silage_available TEXT DEFAULT '',
                dry_fodder_available TEXT DEFAULT '',
                green_fodder_tonnes REAL DEFAULT 0.0,
                silage_tonnes REAL DEFAULT 0.0,
                dry_fodder_tonnes REAL DEFAULT 0.0,
                fodder_for_sale_tonnes REAL DEFAULT 0.0,
                rabi_area_hectares REAL DEFAULT 0.0,
                irrigation_available TEXT DEFAULT '',
                irrigation_types TEXT DEFAULT '',
                irrigation_other TEXT DEFAULT '',
                source_file TEXT DEFAULT '',
                status TEXT DEFAULT 'pending_review',
                review_notes TEXT DEFAULT '',
                is_duplicate INTEGER DEFAULT 0,
                duplicate_reason TEXT DEFAULT '',
                created_at TEXT DEFAULT '',
                updated_at TEXT DEFAULT ''
            );
        """)

        # Safely migrate existing farmers table to have any missing columns
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(farmers)")
        existing_cols = {row["name"] for row in cur.fetchall()}
        
        for col_name, col_def in FARMER_COLUMNS:
            if col_name not in existing_cols:
                # Add missing column
                cur.execute(f"ALTER TABLE farmers ADD COLUMN {col_name} {col_def}")

        # 2. Reviews table for review lifecycle
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                source_file TEXT,
                record_id TEXT,
                record_json TEXT NOT NULL,
                original_status TEXT,
                decision TEXT,
                reviewer_note TEXT DEFAULT '',
                updated_at TEXT,
                PRIMARY KEY (source_file, record_id)
            );
        """)

        # 3. Farmer import staging table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS farmer_import_staging (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT,
                upload_batch_id TEXT DEFAULT '',
                file_hash TEXT DEFAULT '',
                row_json TEXT NOT NULL,
                matched_farmer_id INTEGER,
                match_reason TEXT DEFAULT '',
                status TEXT DEFAULT 'pending_review',
                created_at TEXT
            );
        """)

        # Safely migrate staging table to have upload_batch_id and file_hash
        cur.execute("PRAGMA table_info(farmer_import_staging)")
        staging_cols = {row["name"] for row in cur.fetchall()}
        if "upload_batch_id" not in staging_cols:
            cur.execute("ALTER TABLE farmer_import_staging ADD COLUMN upload_batch_id TEXT DEFAULT ''")
        if "file_hash" not in staging_cols:
            cur.execute("ALTER TABLE farmer_import_staging ADD COLUMN file_hash TEXT DEFAULT ''")

        # Safely backfill upload_batch_id for legacy records
        cur.execute("""
            UPDATE farmers
            SET upload_batch_id = 'BATCH-LEGACY-' || substr(replace(source_file, ' ', '_'), 1, 20)
            WHERE upload_batch_id IS NULL OR upload_batch_id = ''
        """)
        cur.execute("""
            UPDATE farmer_import_staging
            SET upload_batch_id = 'BATCH-LEGACY-' || substr(replace(source_file, ' ', '_'), 1, 20)
            WHERE upload_batch_id IS NULL OR upload_batch_id = ''
        """)

        # 4. Form submissions audit log
        conn.execute("""
            CREATE TABLE IF NOT EXISTS form_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farmer_id INTEGER,
                farmer_name TEXT,
                mobile TEXT,
                submitted_at TEXT,
                http_status INTEGER,
                response_snippet TEXT
            );
        """)

        # 5. Upload audit log table for tracking file uploads and idempotency events
        conn.execute("""
            CREATE TABLE IF NOT EXISTS upload_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_batch_id TEXT DEFAULT '',
                file_name TEXT DEFAULT '',
                file_hash TEXT DEFAULT '',
                action TEXT DEFAULT '',
                record_count INTEGER DEFAULT 0,
                message TEXT DEFAULT '',
                created_at TEXT DEFAULT ''
            );
        """)
        conn.commit()

def check_duplicate_in_db(mobile: str, farmer_name: str, village_name: str, exclude_id: Optional[int] = None, conn: Optional[sqlite3.Connection] = None) -> tuple[bool, list[str]]:
    """
    Check if a record is a duplicate against the database.
    Checks:
    1. Duplicate mobile number (if 10 digits).
    2. Same farmer name in the same village.
    """
    reasons = []
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        clean_mob = str(mobile).strip()
        clean_name = str(farmer_name).strip()
        clean_village = str(village_name).strip()

        # Check mobile (must be at least 10 digits to be a firm match)
        if len(clean_mob) == 10 and clean_mob.isdigit():
            query = "SELECT id, farmer_name, village_name FROM farmers WHERE mobile = ?"
            params = [clean_mob]
            if exclude_id is not None:
                query += " AND id != ?"
                params.append(exclude_id)
            match = conn.execute(query, params).fetchone()
            if match:
                reasons.append(f"मोबाईल क्रमांक {clean_mob} आधीच नोंद #{match['id']} ({match['farmer_name'] or 'शेतकरी'}, {match['village_name'] or 'गाव'}) मध्ये अस्तित्वात आहे.")

        # Check name and village
        if len(clean_name) >= 3 and len(clean_village) >= 2:
            query = "SELECT id, mobile FROM farmers WHERE LOWER(TRIM(farmer_name)) = LOWER(TRIM(?)) AND LOWER(TRIM(village_name)) = LOWER(TRIM(?))"
            params = [clean_name, clean_village]
            if exclude_id is not None:
                query += " AND id != ?"
                params.append(exclude_id)
            match = conn.execute(query, params).fetchone()
            if match:
                reasons.append(f"शेतकऱ्याचे नाव '{clean_name}' आणि गाव '{clean_village}' आधीच नोंद #{match['id']} मध्ये अस्तित्वात आहे.")

        return (len(reasons) > 0, reasons)
    finally:
        if should_close:
            conn.close()

def insert_farmer(record: dict[str, Any], conn: Optional[sqlite3.Connection] = None) -> int:
    """Insert a new farmer record safely, checking for duplicates and updating staging."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_dup, dup_reasons = check_duplicate_in_db(
            record.get("mobile", ""),
            record.get("farmer_name", ""),
            record.get("village_name", ""),
            conn=conn
        )

        cur = conn.cursor()
        cur.execute("PRAGMA table_info(farmers)")
        valid_cols = [r["name"] for r in cur.fetchall()]

        data = dict(record)
        data.setdefault("status", "needs_review" if is_dup else record.get("status", "pending_review"))
        data.setdefault("created_at", now_str)
        data.setdefault("updated_at", now_str)
        data["is_duplicate"] = 1 if is_dup else 0
        data["duplicate_reason"] = "; ".join(dup_reasons) if dup_reasons else ""

        insert_keys = [k for k in data.keys() if k in valid_cols and k != "id"]
        placeholders = ", ".join(["?"] * len(insert_keys))
        col_names = ", ".join(insert_keys)
        values = [data[k] for k in insert_keys]

        cur.execute(f"INSERT INTO farmers ({col_names}) VALUES ({placeholders})", values)
        new_id = cur.lastrowid

        # Update staging
        row_json = json.dumps(data, ensure_ascii=False)
        cur.execute("""
            INSERT INTO farmer_import_staging (source_file, upload_batch_id, file_hash, row_json, matched_farmer_id, match_reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (data.get("source_file", "unknown"), data.get("upload_batch_id", ""), data.get("file_hash", ""), row_json, new_id, "Duplicate: " + data["duplicate_reason"] if is_dup else "Clean Import", data["status"], now_str))

        # Update reviews table
        rec_id = f"FARMER-{new_id:04d}"
        cur.execute("""
            INSERT OR REPLACE INTO reviews (source_file, record_id, record_json, original_status, decision, reviewer_note, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (data.get("source_file", "unknown"), rec_id, row_json, data["status"], None if data["status"] != "verified" else "verified", data.get("review_notes", ""), now_str))

        if should_close:
            conn.commit()

        return new_id
    finally:
        if should_close:
            conn.close()

def update_farmer(farmer_id: int, fields: dict[str, Any], conn: Optional[sqlite3.Connection] = None) -> bool:
    """Update an existing farmer record with edit data and re-evaluate duplicate status."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_dup, dup_reasons = check_duplicate_in_db(
            fields.get("mobile", ""),
            fields.get("farmer_name", ""),
            fields.get("village_name", ""),
            exclude_id=farmer_id,
            conn=conn
        )

        cur = conn.cursor()
        cur.execute("PRAGMA table_info(farmers)")
        valid_cols = [r["name"] for r in cur.fetchall()]

        data = dict(fields)
        data["updated_at"] = now_str
        data["is_duplicate"] = 1 if is_dup else 0
        data["duplicate_reason"] = "; ".join(dup_reasons) if dup_reasons else ""

        update_keys = [k for k in data.keys() if k in valid_cols and k != "id"]
        set_clause = ", ".join([f"{k} = ?" for k in update_keys])
        values = [data[k] for k in update_keys]
        values.append(farmer_id)

        cur.execute(f"UPDATE farmers SET {set_clause} WHERE id = ?", values)
        success = cur.rowcount > 0

        if success:
            # Also update reviews table
            cur.execute("SELECT * FROM farmers WHERE id = ?", (farmer_id,))
            updated_row = dict(cur.fetchone())
            row_json = json.dumps(updated_row, ensure_ascii=False)
            rec_id = f"FARMER-{farmer_id:04d}"
            cur.execute("""
                INSERT OR REPLACE INTO reviews (source_file, record_id, record_json, original_status, decision, reviewer_note, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (updated_row.get("source_file", "manual"), rec_id, row_json, updated_row["status"], "verified" if updated_row["status"] == "verified" else updated_row["status"], updated_row.get("review_notes", ""), now_str))

        if should_close:
            conn.commit()

        return success
    finally:
        if should_close:
            conn.close()

def verify_farmer(farmer_id: int, note: str = "", conn: Optional[sqlite3.Connection] = None) -> bool:
    """Mark a farmer record as manually verified."""
    return update_farmer(farmer_id, {"status": "verified", "review_notes": note}, conn=conn)

def delete_farmer(farmer_id: int, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Delete a farmer record and related staging entries."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM farmers WHERE id = ?", (farmer_id,))
        success = cur.rowcount > 0
        cur.execute("DELETE FROM farmer_import_staging WHERE matched_farmer_id = ?", (farmer_id,))
        cur.execute("DELETE FROM reviews WHERE record_id = ?", (f"FARMER-{farmer_id:04d}",))
        if should_close:
            conn.commit()
        return success
    finally:
        if should_close:
            conn.close()

def get_farmer_by_id(farmer_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[dict[str, Any]]:
    """Retrieve a single farmer record as a dictionary."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM farmers WHERE id = ?", (farmer_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        if should_close:
            conn.close()

def is_file_already_imported(file_hash: str = "", filename: str = "", alt_hash: str = "", conn: Optional[sqlite3.Connection] = None) -> tuple[bool, int, str]:
    """
    Check if a file has already been imported into the database by file hash or filename.
    Returns (is_imported, record_count, existing_batch_id).
    """
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        cur = conn.cursor()
        hashes = [h for h in [file_hash, alt_hash] if h]
        if hashes:
            placeholders = ", ".join(["?"] * len(hashes))
            cur.execute(f"""
                SELECT upload_batch_id, COUNT(*) as cnt
                FROM farmers
                WHERE file_hash IN ({placeholders}) AND file_hash != ''
                GROUP BY upload_batch_id
                ORDER BY id DESC LIMIT 1
            """, hashes)
            row = cur.fetchone()
            if row and row["cnt"] > 0:
                return (True, row["cnt"], row["upload_batch_id"] or "")

        if filename:
            cur.execute("""
                SELECT upload_batch_id, COUNT(*) as cnt
                FROM farmers
                WHERE (source_file = ? OR source_file LIKE ?) AND source_file != ''
                GROUP BY upload_batch_id
                ORDER BY id DESC LIMIT 1
            """, (filename, f"%_{filename}"))
            row = cur.fetchone()
            if row and row["cnt"] > 0:
                return (True, row["cnt"], row["upload_batch_id"] or "")

        return (False, 0, "")
    finally:
        if should_close:
            conn.close()

def log_upload_audit(
    upload_batch_id: str,
    file_name: str,
    file_hash: str,
    action: str,
    record_count: int = 0,
    message: str = "",
    conn: Optional[sqlite3.Connection] = None
) -> int:
    """Record an upload audit event (e.g. 'new_upload', 'duplicate_file_prevented')."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO upload_audit_log (upload_batch_id, file_name, file_hash, action, record_count, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (upload_batch_id, file_name, file_hash, action, record_count, message, now_str))
        audit_id = cur.lastrowid
        if should_close:
            conn.commit()
        return audit_id
    finally:
        if should_close:
            conn.close()

def get_upload_audit_logs(limit: int = 50, conn: Optional[sqlite3.Connection] = None) -> list[dict[str, Any]]:
    """Retrieve recent upload audit log entries."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM upload_audit_log ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        if should_close:
            conn.close()

def get_distinct_source_files(conn: Optional[sqlite3.Connection] = None) -> list[dict[str, Any]]:
    """Return all unique source files with record counts and latest batch."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT source_file, COUNT(*) as record_count, MAX(created_at) as last_created, MAX(upload_batch_id) as batch_id
            FROM farmers
            WHERE source_file != ''
            GROUP BY source_file
            ORDER BY MAX(id) DESC
        """)
        return [dict(r) for r in cur.fetchall()]
    finally:
        if should_close:
            conn.close()

def get_distinct_upload_batches(conn: Optional[sqlite3.Connection] = None) -> list[dict[str, Any]]:
    """Return all unique upload batches with file names and record counts."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT upload_batch_id as batch_id, source_file, COUNT(*) as record_count, MAX(created_at) as created_at
            FROM farmers
            WHERE upload_batch_id != ''
            GROUP BY upload_batch_id
            ORDER BY MAX(id) DESC
        """)
        return [dict(r) for r in cur.fetchall()]
    finally:
        if should_close:
            conn.close()

def get_latest_batch_id(conn: Optional[sqlite3.Connection] = None) -> Optional[str]:
    """Return the most recently created upload_batch_id."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        cur = conn.cursor()
        cur.execute("SELECT upload_batch_id FROM farmers WHERE upload_batch_id != '' ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        return row["upload_batch_id"] if row else None
    finally:
        if should_close:
            conn.close()

def get_latest_source_file(conn: Optional[sqlite3.Connection] = None) -> Optional[str]:
    """Return the source_file from the most recent import."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        cur = conn.cursor()
        cur.execute("SELECT source_file FROM farmers WHERE source_file != '' ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        return row["source_file"] if row else None
    finally:
        if should_close:
            conn.close()

def get_all_farmers(
    status_filter: Optional[str] = None,
    search_query: Optional[str] = None,
    source_file: Optional[str] = None,
    upload_batch_id: Optional[str] = None,
    latest_only: bool = False,
    conn: Optional[sqlite3.Connection] = None
) -> list[dict[str, Any]]:
    """Retrieve farmer records with status, batch, source_file filtering, and search."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        cur = conn.cursor()
        query = "SELECT * FROM farmers"
        clauses = []
        params = []

        # Latest batch filter
        if latest_only or upload_batch_id == "latest":
            latest_batch = get_latest_batch_id(conn=conn)
            if latest_batch:
                clauses.append("upload_batch_id = ?")
                params.append(latest_batch)
        elif upload_batch_id and upload_batch_id != "all":
            clauses.append("upload_batch_id = ?")
            params.append(upload_batch_id)

        # Source file filter
        if source_file and source_file != "all":
            clauses.append("source_file = ?")
            params.append(source_file)

        # Status filter
        if status_filter and status_filter != "all":
            if status_filter == "duplicate":
                clauses.append("is_duplicate = 1")
            else:
                clauses.append("status = ?")
                params.append(status_filter)

        # Search query
        if search_query:
            term = f"%{search_query.strip()}%"
            clauses.append("(farmer_name LIKE ? OR village_name LIKE ? OR mobile LIKE ? OR taluka LIKE ? OR source_file LIKE ?)")
            params.extend([term, term, term, term, term])

        if clauses:
            query += " WHERE " + " AND ".join(clauses)

        query += " ORDER BY id DESC"
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        if should_close:
            conn.close()

def get_dashboard_counts(
    source_file: Optional[str] = None,
    upload_batch_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None
) -> dict[str, int]:
    """Return dashboard summary metrics, optionally scoped to a batch or source_file."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        cur = conn.cursor()
        base_where = []
        params = []

        if upload_batch_id and upload_batch_id != "all":
            if upload_batch_id == "latest":
                latest = get_latest_batch_id(conn=conn)
                if latest:
                    base_where.append("upload_batch_id = ?")
                    params.append(latest)
            else:
                base_where.append("upload_batch_id = ?")
                params.append(upload_batch_id)

        if source_file and source_file != "all":
            base_where.append("source_file = ?")
            params.append(source_file)

        where_sql = (" WHERE " + " AND ".join(base_where)) if base_where else ""

        def query_count(condition: str = "") -> int:
            sql = f"SELECT COUNT(*) FROM farmers"
            c_params = list(params)
            if where_sql:
                if condition:
                    sql += f"{where_sql} AND {condition}"
                else:
                    sql += where_sql
            elif condition:
                sql += f" WHERE {condition}"
            cur.execute(sql, c_params)
            return cur.fetchone()[0]

        return {
            "total": query_count(),
            "verified": query_count("status = 'verified'"),
            "pending": query_count("status IN ('pending_review', 'pending', 'needs_review')"),
            "submitted": query_count("status = 'submitted'"),
            "duplicates": query_count("is_duplicate = 1")
        }
    finally:
        if should_close:
            conn.close()

# Auto-initialize on import
init_db()
