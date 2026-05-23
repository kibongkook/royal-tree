#!/usr/bin/env python3
"""
Split data/master/families.jsonl into:
  data/by_country/<ISO>.jsonl
  data/by_category/<cat>.jsonl
Plus emit data/master/_summary.json for fast lookup of totals.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "master" / "families.jsonl"
BY_C = ROOT / "data" / "by_country"
BY_K = ROOT / "data" / "by_category"
SUM  = ROOT / "data" / "master" / "_summary.json"

def main():
    BY_C.mkdir(parents=True, exist_ok=True)
    BY_K.mkdir(parents=True, exist_ok=True)
    # wipe existing splits so re-running is clean
    for p in list(BY_C.glob("*.jsonl")) + list(BY_K.glob("*.jsonl")):
        p.unlink()

    by_country_files = {}
    by_cat_files = {}
    counts_country = Counter()
    counts_cat = Counter()
    counts_status = Counter()
    counts_cat_country = defaultdict(Counter)
    total = 0

    def fopen(d: dict, key: str, base: Path):
        if key not in d:
            d[key] = (base / f"{key}.jsonl").open("w", encoding="utf-8")
        return d[key]

    with SRC.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            total += 1
            cat = (r.get("category") or "unknown") or "unknown"
            cats = [cat]
            countries = r.get("country") or []
            counts_cat[cat] += 1
            counts_status[r.get("status") or "unknown"] += 1
            if not countries:
                countries = ["_none"]
            for c in countries:
                # only write each record to its country file once
                fopen(by_country_files, c, BY_C).write(line)
                counts_country[c] += 1
                counts_cat_country[c][cat] += 1
            fopen(by_cat_files, cat, BY_K).write(line)

    for fh in list(by_country_files.values()) + list(by_cat_files.values()):
        fh.close()

    print(f"Split {total:,} records into:")
    print(f"  {len(by_country_files):>4} country files in {BY_C}")
    print(f"  {len(by_cat_files):>4} category files in {BY_K}")

    summary = {
        "total_records": total,
        "by_category": dict(counts_cat),
        "by_country": dict(counts_country.most_common()),
        "by_status": dict(counts_status),
        "country_category_matrix": {
            c: dict(cs) for c, cs in counts_cat_country.items()
        },
    }
    SUM.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote summary: {SUM}")

if __name__ == "__main__":
    main()
