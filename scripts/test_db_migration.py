# -*- coding: utf-8 -*-
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import (
    init_db,
    get_distinct_source_files,
    get_distinct_upload_batches,
    get_latest_batch_id,
    get_all_farmers,
    get_dashboard_counts
)

init_db()

batches = get_distinct_upload_batches()
files = get_distinct_source_files()
latest_batch = get_latest_batch_id()
all_farmers = get_all_farmers()
latest_farmers = get_all_farmers(latest_only=True)
counts = get_dashboard_counts()

print(f"Total Batches: {len(batches)}")
for b in batches[:3]:
    print(f"  Batch: {b['batch_id']} | Source: {b['source_file']} | Records: {b['record_count']}")

print(f"Total Source Files: {len(files)}")
for f in files[:3]:
    print(f"  File: {f['source_file']} | Records: {f['record_count']}")

print(f"Latest Batch ID: {latest_batch}")
print(f"Total Farmers: {len(all_farmers)}")
print(f"Latest Batch Farmers: {len(latest_farmers)}")
print(f"Dashboard Counts: {counts}")
