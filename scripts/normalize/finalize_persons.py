#!/usr/bin/env python3
"""finalize_persons.py — re-run head_current + summary over the merged persons.jsonl.

Idempotent. Safe to re-run.

Outputs:
  data/master/families.jsonl       (head_current potentially updated)
  data/master/_persons_summary.json
"""
import json
import re
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "data" / "master"
FAMILIES = MASTER / "families.jsonl"
PERSONS = MASTER / "persons.jsonl"
SUMMARY = MASTER / "_persons_summary.json"


def parse_year(v):
    if v is None or v == "":
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        m = re.match(r"^(-?\d{1,5})", v)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                return None
    return None


def main():
    print("[fin] loading families ...", flush=True)
    families: dict[str, dict] = {}
    with FAMILIES.open() as f:
        for line in f:
            r = json.loads(line)
            families[r["id"]] = r
    print(f"[fin] families: {len(families):,}", flush=True)

    print("[fin] loading persons ...", flush=True)
    persons: list[dict] = []
    with PERSONS.open() as f:
        for line in f:
            try:
                persons.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    print(f"[fin] persons: {len(persons):,}", flush=True)

    # Group by family
    by_fam: dict[str, list[dict]] = defaultdict(list)
    for p in persons:
        fid = p.get("family_id")
        if fid:
            by_fam[fid].append(p)

    # head_current heuristic - restrict to genuine family categories only,
    # and to families with a non-extinct status. This avoids polluting
    # head_current for political organizations / articles / non-families.
    VALID_FAMILY_CATEGORIES = {"royal", "noble", "clan", "business", "religious", "tribal"}
    VALID_STATUSES = {"active", "unknown", None}

    n_filled = 0
    n_cleared = 0
    for fid, ms in by_fam.items():
        fam = families.get(fid)
        if not fam:
            continue
        cat = fam.get("category")
        status = fam.get("status")
        # Skip non-family categories
        if cat not in VALID_FAMILY_CATEGORIES:
            continue
        if status not in VALID_STATUSES:
            continue
        if fam.get("head_current"):
            continue
        # Living-ish: no death recorded
        living = [m for m in ms if not m.get("death")]

        def by_birth(p):
            b = parse_year(p.get("birth"))
            return b if b is not None else -10**9

        pool = living if living else ms
        pool_sorted = sorted(pool, key=by_birth, reverse=True)
        head = pool_sorted[0] if pool_sorted else None
        if head and (not living or by_birth(head) >= 1900):
            fam["head_current"] = head["id"]
            n_filled += 1
    print(f"[fin] head_current newly filled: {n_filled:,}", flush=True)

    # Clear head_current that was previously filled for non-family categories
    for fid, fam in families.items():
        cat = fam.get("category")
        if cat in VALID_FAMILY_CATEGORIES:
            continue
        if fam.get("head_current"):
            # Only clear if it's a QID we just generated (looks like Wikidata)
            # Be conservative: don't clear anything pre-existing in master
            pass

    # Rewrite families.jsonl
    tmp = FAMILIES.with_suffix(".jsonl.tmp")
    with tmp.open("w") as out:
        for fid, fam in families.items():
            out.write(json.dumps(fam, ensure_ascii=False) + "\n")
    tmp.replace(FAMILIES)

    # Summary
    by_source: Counter[str] = Counter()
    for p in persons:
        srcs = p.get("sources") or []
        for s in srcs:
            kind = s.split(":")[0] if isinstance(s, str) else "unknown"
            by_source[kind] += 1
    by_role: Counter[str] = Counter(p.get("family_role") or "member" for p in persons)
    by_gender: Counter[str] = Counter((p.get("gender") or "unknown") for p in persons)
    fam_member_count: Counter[str] = Counter(p["family_id"] for p in persons if p.get("family_id"))
    fams_with_member = len(fam_member_count)

    top30 = []
    for fid, c in fam_member_count.most_common(30):
        fam = families.get(fid) or {}
        top30.append({
            "family_id": fid,
            "name_en": (fam.get("names") or {}).get("en") or fid,
            "person_count": c,
            "head_current": fam.get("head_current"),
        })

    families_with_head = sum(1 for f in families.values() if f.get("head_current"))

    summary = {
        "persons_total": len(persons),
        "by_source": dict(by_source),
        "by_role": dict(by_role),
        "by_gender": dict(by_gender),
        "families_total": len(families),
        "families_with_member": fams_with_member,
        "families_with_head_current": families_with_head,
        "head_current_filled_this_run": n_filled,
        "top30_families_by_member_count": top30,
    }
    with SUMMARY.open("w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"[fin] families with member: {fams_with_member:,}", flush=True)
    print(f"[fin] families with head_current: {families_with_head:,}", flush=True)
    print("[fin] top 10 families:")
    for x in top30[:10]:
        print(f"   {x['person_count']:>5}  {x['family_id']:>15}  {x['name_en']}")


if __name__ == "__main__":
    main()
