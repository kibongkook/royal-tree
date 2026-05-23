#!/usr/bin/env python3
"""
Phase 1.5 cleanup — filter records that are clearly NOT families.

Looks at `raw.instance_of` for Wikidata-sourced records and moves entries
where the only signal is one of:
  - Q5         human (single person)
  - Q748       surname (just the surname, not the family)
  - Q1190554   noble title (title, not family)
  - Q4830453   business (the company itself, not the family owning it)
  - Q207320    historical state/dynasty position (rare; usually wrong tag)
  - Q11424     film, Q571 book, Q47461344 written work — pure misclassifications
  - Q5398426   TV series, Q1466410 software — Wikidata noise
to a separate `data/master/_filtered_non_families.jsonl` so the master only
contains genuine family entities.

Run AFTER all the build_* scripts so we filter the final master.
"""
from __future__ import annotations
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "data" / "master" / "families.jsonl"
NON_FAM = ROOT / "data" / "master" / "_filtered_non_families.jsonl"

NON_FAMILY_INSTANCE_OF = {
    "Q5":          "human",
    "Q748":        "surname",
    "Q1190554":    "noble-title",
    "Q4830453":    "business",
    "Q11424":      "film",
    "Q571":        "book",
    "Q47461344":   "written-work",
    "Q5398426":    "tv-series",
    "Q1466410":    "software",
    "Q3624078":    "sovereign-state",
    "Q34770":      "language-family",
    "Q41710":      "ethnic-group",     # ambiguous — keep if also tagged as clan
    "Q11173":      "chemical-compound",
    "Q35120":      "entity",            # too generic
    "Q83214":      "given-name",
    "Q1196129":    "fictional-character",
    "Q14756018":   "fictional-organization",
    "Q15632617":   "fictional-human",
    "Q15773347":   "film-character",
    "Q95074":      "fictional-character-2",
    "Q3658341":    "literary-character",
}

# We do NOT filter if the record has multiple instance_of values where ANY of them is in this allowlist:
FAMILY_INSTANCE_OF = {
    "Q8436",      # noble family
    "Q164950",    # dynasty
    "Q13417114",  # noble house
    "Q188784",    # royal house
    "Q4438121",   # royal family
    "Q5621421",   # Scottish clan
    "Q56236697",  # Chinese clan
    "Q3024240",   # historical clan
    "Q7210356",   # political family
    "Q1755673",   # reigning dynasty
    "Q207320",    # dynasty alt
}


def main():
    keep = []
    drop = []
    stats = Counter()

    with MASTER.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            inst = (r.get("raw") or {}).get("instance_of") or []
            inst_set = set(inst) if isinstance(inst, list) else set()

            # If record has any family-instance-of, keep it
            if inst_set & FAMILY_INSTANCE_OF:
                keep.append(r); continue

            # If all instance_of values are in the non-family list, drop
            if inst_set and inst_set.issubset(NON_FAMILY_INSTANCE_OF.keys()):
                # tag drop reason
                reason = "+".join(NON_FAMILY_INSTANCE_OF.get(q, q) for q in sorted(inst_set))
                drop.append((r, reason))
                stats[reason] += 1
                continue

            # No instance_of info → keep (manual, CK3, Wikipedia category records)
            keep.append(r)

    print(f"Records kept:    {len(keep):,}")
    print(f"Records dropped: {len(drop):,}")
    print()
    print("Drop reasons (top 15):")
    for reason, n in stats.most_common(15):
        print(f"  {n:>6,}  {reason}")

    # Write outputs
    print(f"\nWriting {MASTER}...")
    with MASTER.open("w", encoding="utf-8") as f:
        for r in keep:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

    print(f"Writing {NON_FAM}...")
    with NON_FAM.open("w", encoding="utf-8") as f:
        for r, reason in drop:
            r2 = dict(r)
            r2["_filter_reason"] = reason
            f.write(json.dumps(r2, ensure_ascii=False, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
