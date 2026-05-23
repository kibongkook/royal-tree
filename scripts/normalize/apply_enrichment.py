#!/usr/bin/env python3
"""
Apply Wikidata country enrichment overlay onto the normalized master.

Reads:
  data/master/_normalized.jsonl       (raw normalized records, many duplicate QIDs)
  data/master/_country_enrichment.jsonl  (per-QID inferred country isos)

Writes:
  data/master/_normalized.jsonl       (overwritten in place; backup written first)

Rules:
  - Match by record.id (must equal an enrichment.id, i.e. a Wikidata QID).
  - Only overlay when:
      * the master record's existing `country` is empty, AND
      * the enrichment provides non-empty `country_inferred`.
  - Never overwrite an existing non-empty country.
  - Track which source property contributed via raw.country_inferred_via.

Run this BEFORE merge_by_qid.py so the merge naturally folds the overlay into
the canonical record set (otherwise we'd have to edit families.jsonl directly).
"""
from __future__ import annotations
import json, shutil
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
NORM = ROOT / "data" / "master" / "_normalized.jsonl"
ENRICH = ROOT / "data" / "master" / "_country_enrichment.jsonl"
BACKUP = ROOT / "data" / "master" / "_normalized.pre_enrich.jsonl"


def load_enrichment() -> dict[str, dict]:
    """qid -> {country: [...], via: [...]}"""
    out: dict[str, dict] = {}
    if not ENRICH.exists():
        return out
    with ENRICH.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            qid = r.get("id")
            isos = r.get("country_inferred") or []
            if qid and isos:
                # If the same QID appears twice (resume), prefer the longer list.
                prev = out.get(qid)
                if not prev or len(isos) > len(prev.get("country", [])):
                    out[qid] = {"country": isos, "via": r.get("via") or []}
    return out


def main():
    enrich = load_enrichment()
    print(f"Loaded {len(enrich):,} enrichment records with country signal.")

    # Backup once (only on first run, don't overwrite a good backup)
    if not BACKUP.exists():
        shutil.copy2(NORM, BACKUP)
        print(f"Backup written: {BACKUP.name}")

    n_in = 0
    n_overlay = 0
    n_already = 0
    via_counter: Counter = Counter()
    tmp = NORM.with_suffix(".tmp")
    with BACKUP.open(encoding="utf-8") as fin, tmp.open("w", encoding="utf-8") as fout:
        for line in fin:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                fout.write(line)
                continue
            n_in += 1
            rid = r.get("id", "")
            if rid in enrich:
                if r.get("country"):
                    n_already += 1
                else:
                    info = enrich[rid]
                    r["country"] = sorted(set(info["country"]))
                    raw = r.get("raw") or {}
                    raw["country_inferred_via"] = info["via"]
                    r["raw"] = raw
                    # Tag the source list too
                    src = r.get("sources") or []
                    if "wikidata-enrichment-v1" not in src:
                        src.append("wikidata-enrichment-v1")
                        r["sources"] = sorted(set(src))
                    for v in info["via"]:
                        via_counter[v] += 1
                    n_overlay += 1
            fout.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
    tmp.replace(NORM)

    print(f"\nApplied overlay:")
    print(f"  input records:         {n_in:,}")
    print(f"  enrichment available:  {len(enrich):,}")
    print(f"  records overlaid:      {n_overlay:,}")
    print(f"  skipped (had country): {n_already:,}")
    print(f"\n  by source property:")
    for p, n in via_counter.most_common():
        print(f"    {p}: {n:,}")


if __name__ == "__main__":
    main()
