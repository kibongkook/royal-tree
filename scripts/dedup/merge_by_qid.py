#!/usr/bin/env python3
"""
Merge data/master/_normalized.jsonl by Wikidata QID.

Strategy:
- Records with id starting with "Q" → canonical group; merge all into one entry.
- Records with non-QID id → kept separate, but if their English name matches an
  existing QID record's English name (case-insensitive, with country overlap),
  merge their `sources` into that QID record (lossless cross-link).
- Output: data/master/families.jsonl (deduped) + data/master/_alias_map.tsv
  (every alternate id we saw, mapped to its canonical id, for audit).

Merging rules:
- names: union of dicts; on conflict prefer non-null longer string.
- country: union (sorted set).
- category: vote (most-common non-"unknown"); break ties by source priority
  manual > wikidata > ck3 > eu4 > wikipedia.
- period: pick earliest non-null founded, latest non-null extinct.
- status: vote (priority: deposed > active > extinct > merged > unknown).
- head_current: first non-null encountered.
- sources: union (sorted).
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[2]
IN  = ROOT / "data" / "master" / "_normalized.jsonl"
OUT = ROOT / "data" / "master" / "families.jsonl"
ALIAS = ROOT / "data" / "master" / "_alias_map.tsv"

SOURCE_PRIORITY = {  # higher wins
    "manual": 5, "wikidata": 4, "ck3": 3, "ck2": 3, "eu4": 2, "wikipedia": 1
}

def source_kind(s: str) -> str:
    return s.split(":", 1)[0] if ":" in s else s

STATUS_PRIORITY = ["deposed", "active", "extinct", "merged", "unknown"]

def merge_names(a: dict, b: dict) -> dict:
    out = dict(a or {})
    for k, v in (b or {}).items():
        if not v:
            continue
        cur = out.get(k)
        if not cur or (isinstance(cur, str) and isinstance(v, str) and len(v) > len(cur)):
            out[k] = v
    return out

def merge_country(a, b):
    return sorted(set((a or []) + (b or [])))

def vote_category(values):
    """Pick most-common non-unknown category, weighted by source priority of the record."""
    counter = Counter(v for v in values if v and v != "unknown")
    if not counter:
        return "unknown"
    return counter.most_common(1)[0][0]

def vote_status(values):
    counter = Counter(v for v in values if v)
    for s in STATUS_PRIORITY:
        if counter.get(s, 0) > 0:
            return s
    return "unknown"

def merge_period(a, b):
    def pick(x, y, mode):
        if x is None: return y
        if y is None: return x
        try:
            xi, yi = int(x), int(y)
        except (TypeError, ValueError):
            return x or y
        return min(xi, yi) if mode == "min" else max(xi, yi)
    return {
        "founded": pick(a.get("founded"), b.get("founded"), "min"),
        "extinct": pick(a.get("extinct"), b.get("extinct"), "max"),
    }

def is_qid(s: str) -> bool:
    return bool(s) and s.startswith("Q") and s[1:].isdigit()

def name_key(rec: dict) -> str | None:
    n = (rec.get("names") or {}).get("en")
    if not n:
        return None
    return re.sub(r"\W+", "", n.lower())[:60]

def main():
    by_qid = {}                    # canonical_qid -> merged record
    by_name_country = {}           # (name_key, country_tuple) -> qid (for cross-linking non-qid recs)
    non_qid = []
    aliases = []                   # (original_id, canonical_id)

    print("Pass 1: load QID records into canonical map...")
    n_in = 0
    with IN.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            n_in += 1
            rid = r.get("id")
            if not rid:
                continue
            if is_qid(rid):
                if rid in by_qid:
                    prev = by_qid[rid]
                    merged = {
                        "id": rid,
                        "names":  merge_names(prev["names"], r["names"]),
                        "country": merge_country(prev["country"], r["country"]),
                        "category": vote_category([prev["category"], r["category"]]),
                        "period":  merge_period(prev["period"], r["period"]),
                        "status":  vote_status([prev["status"], r["status"]]),
                        "head_current": prev["head_current"] or r.get("head_current"),
                        "sources": sorted(set(prev["sources"] + r["sources"])),
                        "raw": {**(prev.get("raw") or {}), **(r.get("raw") or {})},
                    }
                    by_qid[rid] = merged
                else:
                    by_qid[rid] = r
            else:
                non_qid.append(r)

    print(f"  loaded {n_in:,} records → {len(by_qid):,} unique QIDs, {len(non_qid):,} non-QID")

    # Build name->qid index for cross-link
    for qid, r in by_qid.items():
        nk = name_key(r)
        if not nk:
            continue
        for c in (r["country"] or [None]):
            by_name_country[(nk, c)] = qid

    print("Pass 2: cross-link non-QID records by name+country...")
    linked = 0
    survived = []
    for r in non_qid:
        nk = name_key(r)
        cs = r["country"] or [None]
        matched_qid = None
        if nk:
            for c in cs:
                if (nk, c) in by_name_country:
                    matched_qid = by_name_country[(nk, c)]
                    break
        if matched_qid:
            # merge sources + alt names into the canonical QID record
            tgt = by_qid[matched_qid]
            tgt["sources"] = sorted(set(tgt["sources"] + r["sources"]))
            tgt["names"]   = merge_names(tgt["names"], r["names"])
            tgt["country"] = merge_country(tgt["country"], r["country"])
            tgt["status"]  = vote_status([tgt["status"], r["status"]])
            tgt["period"]  = merge_period(tgt["period"], r["period"])
            if tgt["category"] == "unknown" and r.get("category") != "unknown":
                tgt["category"] = r["category"]
            tgt["head_current"] = tgt.get("head_current") or r.get("head_current")
            aliases.append((r["id"], matched_qid))
            linked += 1
        else:
            survived.append(r)
            aliases.append((r["id"], r["id"]))

    print(f"  cross-linked {linked:,} → remaining non-QID: {len(survived):,}")

    print("Pass 3: dedup non-QID by (name+country) within themselves...")
    grouped = defaultdict(list)
    leftovers = []
    for r in survived:
        nk = name_key(r)
        if not nk:
            leftovers.append(r)
            continue
        cs = tuple(r["country"] or [])
        grouped[(nk, cs)].append(r)
    coalesced = []
    for k, recs in grouped.items():
        if len(recs) == 1:
            coalesced.append(recs[0]); continue
        merged = recs[0]
        for r in recs[1:]:
            merged = {
                "id": merged["id"],   # keep first id
                "names":  merge_names(merged["names"], r["names"]),
                "country": merge_country(merged["country"], r["country"]),
                "category": vote_category([merged["category"], r["category"]]),
                "period":  merge_period(merged["period"], r["period"]),
                "status":  vote_status([merged["status"], r["status"]]),
                "head_current": merged.get("head_current") or r.get("head_current"),
                "sources": sorted(set(merged["sources"] + r["sources"])),
                "raw":    {**(merged.get("raw") or {}), **(r.get("raw") or {})},
            }
            aliases.append((r["id"], merged["id"]))
        coalesced.append(merged)
    coalesced.extend(leftovers)
    print(f"  coalesced same-name same-country → {len(coalesced):,} non-QID entries")

    final = list(by_qid.values()) + coalesced
    print(f"\nFinal master records: {len(final):,}")

    print(f"Writing {OUT}...")
    with OUT.open("w", encoding="utf-8") as f:
        for r in sorted(final, key=lambda x: (x["category"], x.get("country", []), (x.get("names") or {}).get("en", ""))):
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

    print(f"Writing {ALIAS}...")
    with ALIAS.open("w", encoding="utf-8") as f:
        f.write("original_id\tcanonical_id\n")
        for a, b in aliases:
            f.write(f"{a}\t{b}\n")

    # quick stats
    print("\n--- Category breakdown ---")
    cat = Counter(r["category"] for r in final)
    for c, n in cat.most_common():
        print(f"  {c:12s} {n:>8,}")

    print("\n--- Top 30 countries ---")
    cc = Counter()
    for r in final:
        for c in (r["country"] or ["(none)"]):
            cc[c] += 1
    for c, n in cc.most_common(30):
        print(f"  {c:12s} {n:>8,}")

if __name__ == "__main__":
    main()
