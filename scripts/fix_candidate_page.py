# -*- coding: utf-8 -*-
import json
import glob
import os

matched = glob.glob(r"data\processed\*candidates.json")
if not matched:
    print("[!] Koi candidates.json nahi mila!")
else:
    for fpath in matched:
        with open(fpath, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        fields = {
            "taluka": "नगर",
            "veterinary_hospital": "Ralegun",
            "revenue_circle": "Walki",
            "village_name": "वडगाव तांदळी",
            "farmer_name": "आशिष शब्बीर शेख",
            "mobile": "9096515858",
            "cow_small": "1",
            "cow_large": "0",
            "buffalo_small": "0",
            "buffalo_large": "0",
            "milch_animals": "1",
            "dry_animals": "0",
            "daily_milk_litres": "20",
            "goats": "0",
            "sheep_migratory": "0",
            "sheep_confined": "0",
            "water_availability": "आहे",
            "green_fodder_available": "हिरवा",
            "silage_available": "नाही",
            "dry_fodder_available": "उपलब्ध",
            "green_fodder_tonnes": "1.0",
            "silage_tonnes": "1.0",
            "dry_fodder_tonnes": "1.0",
            "fodder_for_sale_tonnes": "0.0",
            "rabi_area_hectares": "2.0",
            "irrigation_available": "होय",
            "irrigation_types": "विहीर",
            "irrigation_other": ""
        }

        # Agar data list hai to har element ko update karo
        if isinstance(raw_data, list):
            if len(raw_data) == 0:
                raw_data.append({"farmer_fields": fields})
            else:
                for item in raw_data:
                    if isinstance(item, dict):
                        item["farmer_fields"] = fields
        elif isinstance(raw_data, dict):
            raw_data["farmer_fields"] = fields

        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)

        print(f"[SUCCESS] Updated list candidates in: {os.path.basename(fpath)}")