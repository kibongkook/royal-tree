#!/usr/bin/env python3
"""
Phase 4b — convert _forbes_unmatched.tsv into new business family records.

Each unique unmatched Forbes/Bloomberg billionaire is treated as the head of
a previously-unknown business family. Emits to data/raw/manual/forbes_unmatched_families_v3.jsonl
in the same shape as other manual files.

After this runs, re-run the pipeline:
  python3 scripts/normalize/to_master_schema.py
  python3 scripts/normalize/apply_enrichment.py
  python3 scripts/dedup/merge_by_qid.py
  python3 scripts/normalize/build_businesses.py
  python3 scripts/normalize/split_indexes.py
"""
from __future__ import annotations
import csv, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "master" / "_forbes_unmatched.tsv"
OUT = ROOT / "data" / "raw" / "manual" / "forbes_unmatched_families_v3.jsonl"

COUNTRY_TO_ISO = {
    "United States": "US", "United Kingdom": "GB", "Hong Kong": "HK",
    "China": "CN", "Russia": "RU", "Germany": "DE", "France": "FR",
    "India": "IN", "Brazil": "BR", "Italy": "IT", "Spain": "ES",
    "Japan": "JP", "Korea": "KR", "South Korea": "KR", "Sweden": "SE",
    "Canada": "CA", "Australia": "AU", "Mexico": "MX", "Switzerland": "CH",
    "Saudi Arabia": "SA", "UAE": "AE", "United Arab Emirates": "AE",
    "Taiwan": "TW", "Indonesia": "ID", "Singapore": "SG", "Malaysia": "MY",
    "Philippines": "PH", "Thailand": "TH", "Israel": "IL", "Turkey": "TR",
    "Egypt": "EG", "South Africa": "ZA", "Nigeria": "NG", "Argentina": "AR",
    "Chile": "CL", "Colombia": "CO", "Venezuela": "VE", "Peru": "PE",
    "Norway": "NO", "Denmark": "DK", "Finland": "FI", "Netherlands": "NL",
    "Belgium": "BE", "Austria": "AT", "Greece": "GR", "Czech Republic": "CZ",
    "Poland": "PL", "Ireland": "IE", "Portugal": "PT", "Hungary": "HU",
    "Ukraine": "UA", "Lebanon": "LB", "Cyprus": "CY", "Romania": "RO",
    "Vietnam": "VN", "Kazakhstan": "KZ", "Algeria": "DZ", "Morocco": "MA",
    "Pakistan": "PK", "Bangladesh": "BD", "Iran": "IR", "Iraq": "IQ",
    "Qatar": "QA", "Kuwait": "KW", "Bahrain": "BH", "Oman": "OM",
    "Jordan": "JO", "Syria": "SY", "Yemen": "YE", "Sudan": "SD",
    "Ethiopia": "ET", "Kenya": "KE", "Tanzania": "TZ", "Uganda": "UG",
    "Ghana": "GH", "Senegal": "SN", "New Zealand": "NZ", "Iceland": "IS",
    "Estonia": "EE", "Latvia": "LV", "Lithuania": "LT", "Slovakia": "SK",
    "Slovenia": "SI", "Croatia": "HR", "Serbia": "RS", "Bulgaria": "BG",
    "Georgia": "GE", "Armenia": "AM", "Azerbaijan": "AZ", "Uzbekistan": "UZ",
    "Sri Lanka": "LK",
}


def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE).strip().lower()
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:80] if s else "unknown"


def name_to_surname(name: str) -> str:
    """Extract surname from 'First Middle Last' or 'Last, First'."""
    if "," in name:
        return name.split(",")[0].strip()
    parts = name.split()
    if len(parts) >= 2:
        # Avoid suffixes like Jr., Sr., III
        suffixes = {"jr.", "jr", "sr.", "sr", "ii", "iii", "iv", "v"}
        while parts and parts[-1].lower().rstrip(".") in suffixes:
            parts.pop()
        if parts:
            return parts[-1]
    return name


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    out_records = []

    with SRC.open(encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader, None)
        for row in reader:
            if len(row) < 4:
                continue
            rank, name, country, source, note = (row + [""])[:5]
            name = name.strip()
            if not name or name.lower() in ("name", ""):
                continue
            country = country.strip()
            surname = name_to_surname(name)
            iso = COUNTRY_TO_ISO.get(country)
            key = (surname.lower(), iso or country.lower())
            if key in seen:
                continue
            seen.add(key)
            slug = f"royal-tree:forbes:{iso or 'xx'}-{slugify(surname)}"
            rec = {
                "id": None,
                "name_en": f"{surname} family ({name})",
                "name_native": None,
                "name_native_lang": None,
                "country": [iso] if iso else [],
                "category": "business",
                "period": {"founded": None, "extinct": None},
                "status": "active",
                "aliases": {},
                "source": "manual:forbes-unmatched-v3",
                "wikidata_qid_hint": None,
                "notes": f"Auto-derived from Forbes/Bloomberg unmatched billionaire {name} ({source}). To verify and enrich.",
                "raw_forbes": {
                    "rank": rank, "name": name, "country": country,
                    "source_industry": source, "note": note,
                },
            }
            out_records.append((slug, rec))

    with OUT.open("w", encoding="utf-8") as f:
        for slug, rec in out_records:
            f.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"Wrote {len(out_records):,} new business-family records to {OUT.name}")


if __name__ == "__main__":
    main()
