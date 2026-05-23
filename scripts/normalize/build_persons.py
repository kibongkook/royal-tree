#!/usr/bin/env python3
"""
Phase 2 — Build the person graph.

Ingests the 4 banked individual files into a unified `persons.jsonl`:
  - royal92 individuals (3,010)
  - royalconstellations individuals (2,799)
  - Islamic Atlas rulers (830)
  - ctm_bench figures (1,652)

Each person record is linked to a family via the master alias map. Where the
family record has empty `head_current`, we attempt to fill it from the eldest
living male in the relevant family.

This is a Phase-2 MINIMAL build: no Wikidata API calls. The yale-wikidata-people
ingest (with API calls) will be a separate follow-up pass.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "data" / "master" / "families.jsonl"
ALIAS  = ROOT / "data" / "master" / "_alias_map.tsv"
RAW    = ROOT / "data" / "raw" / "github"

OUT_PERSONS = ROOT / "data" / "master" / "persons.jsonl"
OUT_SUMMARY = ROOT / "data" / "master" / "_persons_summary.json"
OUT_BY_FAM  = ROOT / "data" / "master" / "persons_by_family"


def load_alias_map() -> dict[str, str]:
    """original_id -> canonical_id (QID or royal-tree:... slug)"""
    m = {}
    if not ALIAS.exists():
        return m
    with ALIAS.open(encoding="utf-8") as f:
        next(f, None)  # header
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == 2:
                m[parts[0]] = parts[1]
    return m


def load_families() -> dict[str, dict]:
    fams = {}
    if not MASTER.exists():
        return fams
    with MASTER.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            fams[r["id"]] = r
    return fams


def normalize_year(v) -> int | None:
    if v is None or v == "":
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        m = re.match(r"^(-?\d{1,4})", v)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                return None
    return None


def canon_family_id(raw_id: str, alias: dict[str, str], known_fams: set) -> str:
    """Resolve a raw family pointer to its canonical id (QID-merged)."""
    if not raw_id:
        return raw_id
    # alias map gives canonical id
    canonical = alias.get(raw_id, raw_id)
    return canonical


def from_royal92(records: list, alias: dict, known: set):
    fp = RAW / "_royal92_individuals.jsonl"
    if not fp.exists():
        return 0
    n = 0
    with fp.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            fam = canon_family_id(r.get("family") or "", alias, known)
            rec = {
                "id": r["id"],
                "names": {"en": r.get("name") or ""},
                "family_id": fam,
                "family_role": "member",
                "birth": normalize_year(r.get("birth")),
                "death": normalize_year(r.get("death")),
                "gender": r.get("sex"),
                "father_id": r.get("father"),
                "mother_id": r.get("mother"),
                "spouse_ids": r.get("spouse") or [],
                "child_ids": [],
                "predecessor_id": None,
                "successor_id": None,
                "country": [],
                "titles": [r["title"]] if r.get("title") else [],
                "sources": ["github:arbre-app/public-gedcoms:royal92.ged"],
                "raw": {
                    "given": r.get("given"),
                    "surname": r.get("surname"),
                    "birth_place": r.get("birth_place"),
                    "death_place": r.get("death_place"),
                },
            }
            records.append(rec)
            n += 1
    return n


def from_royalconstellations(records: list, alias: dict, known: set):
    fp = RAW / "_royalconstellations_individuals.jsonl"
    if not fp.exists():
        return 0
    n = 0
    with fp.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            fam = canon_family_id(r.get("family") or "", alias, known)
            rec = {
                "id": r["id"],
                "names": {"en": (r.get("name") or "").strip()},
                "family_id": fam,
                "family_role": "member",
                "birth": normalize_year(r.get("birth")),
                "death": normalize_year(r.get("death")),
                "gender": r.get("gender"),
                "father_id": r.get("father"),
                "mother_id": r.get("mother"),
                "spouse_ids": r.get("spouse") or [],
                "child_ids": [],
                "predecessor_id": None,
                "successor_id": None,
                "country": [],
                "titles": [r["title"]] if r.get("title") else [],
                "sources": ["github:nbremer/royalconstellations"],
                "raw": {
                    "surname": r.get("surname"),
                    "min_dist_to_royal": r.get("min_dist_to_royal"),
                },
            }
            records.append(rec)
            n += 1
    return n


def from_islamic_atlas(records: list, alias: dict, known: set):
    fp = RAW / "_islamic_atlas_rulers.jsonl"
    if not fp.exists():
        return 0
    n = 0
    with fp.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            fam = canon_family_id(r.get("dynasty_id_link") or "", alias, known)
            is_founder = (r.get("is_founder") or "").strip().lower() in ("evet", "yes", "true")
            is_last    = (r.get("is_last_ruler") or "").strip().lower() in ("evet", "yes", "true")
            role = "founder" if is_founder else ("current_head" if is_last and not r.get("death_ce") else "member")
            rec = {
                "id": r["id"],
                "names": {
                    "en": r.get("short_name") or r.get("full_name_original") or "",
                    "tr": r.get("full_name_original") or "",
                },
                "family_id": fam,
                "family_role": role,
                "birth": None,
                "death": normalize_year(r.get("death_ce")),
                "gender": "M",  # historical Islamic rulers — male assumption (correct in nearly all cases)
                "father_id": None,
                "mother_id": None,
                "spouse_ids": [],
                "child_ids": [],
                "predecessor_id": r.get("predecessor_ruler"),
                "successor_id": r.get("successor_ruler"),
                "country": [],
                "titles": [r["title"]] if r.get("title") else [],
                "sources": r.get("sources") or [],
                "raw": {
                    "dynasty_name": r.get("dynasty_name"),
                    "kunya": r.get("kunya"),
                    "nasab": r.get("nasab"),
                    "laqab": r.get("laqab"),
                    "reign_start_ce": r.get("reign_start_ce"),
                    "reign_end_ce": r.get("reign_end_ce"),
                    "death_type": r.get("death_type"),
                    "relationship_to_prev": r.get("relationship_to_prev"),
                    "succession_type": r.get("succession_type"),
                    "reign_order": r.get("reign_order"),
                },
            }
            records.append(rec)
            n += 1
    return n


CTM_DYNASTY_TO_SLUG = {
    "先秦": "royal-tree:ctm-bench:pre-qin",
    "汉":   "royal-tree:ctm-bench:han",
    "六朝": "royal-tree:ctm-bench:six-dynasties",
    "隋":   "royal-tree:ctm-bench:sui",
    "唐":   "royal-tree:ctm-bench:tang",
    "五代": "royal-tree:ctm-bench:five-dynasties",
    "宋":   "royal-tree:ctm-bench:song",
    "元":   "royal-tree:ctm-bench:yuan",
    "明":   "royal-tree:ctm-bench:ming",
    "清":   "royal-tree:ctm-bench:qing",
}


def from_ctm_bench(records: list, alias: dict, known: set):
    fp = RAW / "_ctm_bench_figures.jsonl"
    if not fp.exists():
        return 0
    n = 0
    with fp.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            slug = CTM_DYNASTY_TO_SLUG.get(r.get("dynasty_zh") or "", "")
            fam = canon_family_id(slug, alias, known) if slug else ""
            rec = {
                "id": r["id"],
                "names": {"zh": r.get("name_zh") or ""},
                "family_id": fam,
                "family_role": "member",
                "birth": normalize_year(r.get("year_birth")),
                "death": normalize_year(r.get("year_death")),
                "gender": None,
                "father_id": None,
                "mother_id": None,
                "spouse_ids": [],
                "child_ids": [],
                "predecessor_id": None,
                "successor_id": None,
                "country": ["CN"],
                "titles": [],
                "sources": r.get("sources") or [],
                "raw": {
                    "dynasty_zh": r.get("dynasty_zh"),
                    "dynasty_en": r.get("dynasty_en"),
                    "address": r.get("address"),
                },
            }
            records.append(rec)
            n += 1
    return n


def populate_child_ids(records: list[dict]):
    """For each person with father/mother, register the child in those parents' child_ids."""
    by_id = {r["id"]: r for r in records}
    for r in records:
        for pkey in ("father_id", "mother_id"):
            pid = r.get(pkey)
            if pid and pid in by_id:
                if r["id"] not in by_id[pid]["child_ids"]:
                    by_id[pid]["child_ids"].append(r["id"])


def fill_family_country(records: list[dict], families: dict):
    """Pre-fill person.country from their family.country if person.country is empty."""
    for r in records:
        if r.get("country"):
            continue
        fam = families.get(r.get("family_id"))
        if fam and fam.get("country"):
            r["country"] = list(fam["country"])


def stitch_head_current(records: list[dict], families: dict) -> int:
    """Fill family.head_current for families with no head and ≥1 living member.

    "Living" = death is None AND (birth >= 1900 OR family.status == 'active').
    Pick the eldest living person; tie-break by source priority royal92 > islamic-atlas > ctm-bench.
    """
    members_by_fam: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r.get("family_id"):
            members_by_fam[r["family_id"]].append(r)

    n_filled = 0
    for fid, fam in families.items():
        if fam.get("head_current"):
            continue
        members = members_by_fam.get(fid, [])
        if not members:
            continue
        living = [m for m in members
                  if m.get("death") is None and (m.get("birth") is None or m["birth"] >= 1900)
                  and fam.get("status") in ("active", "unknown", None)]
        if not living:
            # Try last ruler if explicitly flagged (Islamic atlas)
            last_rulers = [m for m in members if m.get("family_role") == "current_head"]
            if last_rulers and fam.get("status") in ("active", "unknown", None):
                fam["head_current"] = last_rulers[0]["id"]
                n_filled += 1
            continue
        # Pick the eldest living member
        living.sort(key=lambda m: (m.get("birth") or 9999))
        fam["head_current"] = living[0]["id"]
        n_filled += 1
    return n_filled


def main():
    print("Loading families + alias map...")
    families = load_families()
    alias = load_alias_map()
    known = set(families.keys())
    print(f"  {len(families):,} families, {len(alias):,} aliases")

    records: list[dict] = []
    print("\nIngesting banked individuals:")
    n1 = from_royal92(records, alias, known)
    print(f"  royal92                 +{n1:,}")
    n2 = from_royalconstellations(records, alias, known)
    print(f"  royalconstellations     +{n2:,}")
    n3 = from_islamic_atlas(records, alias, known)
    print(f"  islamic_atlas_rulers    +{n3:,}")
    n4 = from_ctm_bench(records, alias, known)
    print(f"  ctm_bench_figures       +{n4:,}")
    print(f"  Total: {len(records):,}")

    print("\nPopulating child_ids from parent links...")
    populate_child_ids(records)

    print("Filling person.country from family.country...")
    fill_family_country(records, families)

    print("Stitching family.head_current...")
    n_filled = stitch_head_current(records, families)
    print(f"  head_current newly filled: {n_filled:,}")

    # ---- write outputs ----
    print(f"\nWriting {OUT_PERSONS.name}...")
    with OUT_PERSONS.open("w", encoding="utf-8") as f:
        for r in sorted(records, key=lambda x: (x.get("family_id",""), x.get("birth") or 99999)):
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

    print(f"Re-writing families.jsonl with head_current updates...")
    with MASTER.open("w", encoding="utf-8") as f:
        for r in sorted(families.values(), key=lambda x: (x.get("category","zzz"), x.get("country",[]), (x.get("names") or {}).get("en",""))):
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

    # ---- stats ----
    fam_member_count = Counter(r["family_id"] for r in records if r.get("family_id"))
    fams_with_members = len(fam_member_count)
    top_fams = []
    for fid, cnt in fam_member_count.most_common(30):
        fname = (families.get(fid, {}).get("names") or {}).get("en", fid)
        top_fams.append({"family_id": fid, "name_en": fname, "members": cnt})

    by_role = Counter(r.get("family_role") for r in records)
    by_gender = Counter(r.get("gender") or "unknown" for r in records)
    by_source = Counter()
    for r in records:
        for s in r.get("sources", []):
            kind = s.split(":")[0]
            by_source[kind] += 1

    summary = {
        "total_persons": len(records),
        "families_with_members": fams_with_members,
        "head_current_filled": n_filled,
        "by_role": dict(by_role),
        "by_gender": dict(by_gender),
        "by_source": dict(by_source),
        "top_30_families_by_member_count": top_fams,
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    # ---- persons_by_family ----
    OUT_BY_FAM.mkdir(parents=True, exist_ok=True)
    for p in list(OUT_BY_FAM.glob("*.jsonl")):
        p.unlink()
    by_fam: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r.get("family_id"):
            by_fam[r["family_id"]].append(r)
    for fid, ms in by_fam.items():
        safe = re.sub(r"[^\w-]+", "_", fid)[:80]
        with (OUT_BY_FAM / f"{safe}.jsonl").open("w", encoding="utf-8") as f:
            for r in sorted(ms, key=lambda x: (x.get("birth") or 99999)):
                f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

    print(f"\n--- Summary ---")
    print(f"  Total persons:           {len(records):,}")
    print(f"  Families with members:   {fams_with_members:,}")
    print(f"  head_current filled:     {n_filled:,}")
    print(f"  persons_by_family files: {len(by_fam):,}")
    print(f"\nTop 10 families by member count:")
    for x in top_fams[:10]:
        print(f"  {x['members']:>5}  {x['family_id']}  ({x['name_en']})")


if __name__ == "__main__":
    main()
