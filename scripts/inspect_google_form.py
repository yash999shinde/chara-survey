# -*- coding: utf-8 -*-
import urllib.request
import re
import json

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfh73QStzk0cZ6gvqRHZWG9V4yGsBv3tx2Z6P3WroXS97XxHQ/viewform"

req = urllib.request.Request(
    FORM_URL, 
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
)

try:
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8')
        
    match = re.search(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(.*?);\s*</script>', html)
    if not match:
        print("[ERROR] Could not extract form configuration data.")
    else:
        raw_json = match.group(1)
        data = json.loads(raw_json)
        questions = data[1][1]
        
        form_schema = []
        print("=== AUTHORIZED GOOGLE FORM FIELDS & ENTRIES ===\n")
        for q in questions:
            title = q[1]
            entry_id = None
            options = []
            
            if q[4] and len(q[4]) > 0:
                entry_id = f"entry.{q[4][0][0]}"
                if len(q[4][0]) > 1 and q[4][0][1]:
                    options = [opt[0] for opt in q[4][0][1]]
                    
            print(f"Title   : {title}")
            print(f"Entry ID: {entry_id}")
            if options:
                print(f"Options : {options}")
            print("-" * 50)
            
            form_schema.append({
                "title": title,
                "entry_id": entry_id,
                "options": options
            })
            
        with open(r"config\google_form_schema.json", "w", encoding="utf-8") as f:
            json.dump(form_schema, f, ensure_ascii=False, indent=2)
        print("[+] Saved detected Google Form schema to: config/google_form_schema.json")
except Exception as e:
    print(f"[ERROR] Failed to fetch or parse form: {e}")