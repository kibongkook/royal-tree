#!/usr/bin/env python3
"""Generate summary stats for data/raw/wikidata/families.jsonl."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

PATH = Path("/Users/sidewalkai2/Claude/royal-tree/data/raw/wikidata/families.jsonl")


def main() -> None:
    total = 0
    by_class: Counter[str] = Counter()
    by_country: Counter[str] = Counter()
    no_country = 0
    no_inception = 0
    has_ko = 0
    has_zh = 0
    has_ja = 0
    has_ar = 0
    has_ru = 0

    with PATH.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            total += 1
            for c in r.get("instance_of") or []:
                by_class[c] += 1
            countries = r.get("country") or []
            if not countries:
                no_country += 1
            for c in countries:
                by_country[c] += 1
            if not r.get("inception"):
                no_inception += 1
            aliases = r.get("aliases") or {}
            if aliases.get("ko"):
                has_ko += 1
            if aliases.get("zh"):
                has_zh += 1
            if aliases.get("ja"):
                has_ja += 1
            if aliases.get("ar"):
                has_ar += 1
            if aliases.get("ru"):
                has_ru += 1

    print(f"Total unique QIDs:        {total}")
    print(f"Without country (P17):    {no_country}")
    print(f"Without inception (P571): {no_inception}")
    print(f"With Korean label:        {has_ko}")
    print(f"With Japanese label:      {has_ja}")
    print(f"With Chinese label:       {has_zh}")
    print(f"With Russian label:       {has_ru}")
    print(f"With Arabic label:        {has_ar}")
    print()
    print("Breakdown by instance_of:")
    for k, v in by_class.most_common():
        print(f"  {k:<14} {v}")
    print()
    print("Top 30 countries (ISO 3166-1 or QID):")
    for k, v in by_country.most_common(30):
        print(f"  {k:<14} {v}")


if __name__ == "__main__":
    main()
