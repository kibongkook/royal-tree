#!/usr/bin/env python3
"""
Parse data/raw/github/public-gedcoms/files/royal92.ged into:
  - data/raw/github/_royal92_families.jsonl       (family-level records, surname clusters ≥3)
  - data/raw/github/_royal92_individuals.jsonl    (every INDI for Phase 2 person graph)

GEDCOM is a flat line-prefixed format:
  0 @I1@ INDI                ← top-level record opens
  1 NAME Victoria  /Hanover/  ← surname is inside slashes
  1 BIRT
  2 DATE 24 MAY 1819
  2 PLAC ...
  1 DEAT
  2 DATE 22 JAN 1901
  1 FAMS @F1@                 ← spouse-in family pointer
  1 FAMC @F42@                ← child-in family pointer
  0 @F1@ FAM
  1 HUSB @I2@
  1 WIFE @I1@
  1 CHIL @I3@
  ...

We parse INDI + FAM records, then cluster individuals by surname (everything between
the slashes in NAME). Surnames with ≥3 members emit a family record.

Surname canonicalization: lowercased, dashed slug used as id.
"""
from __future__ import annotations

import json, re, sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
GED  = ROOT / "data" / "raw" / "github" / "public-gedcoms" / "files" / "royal92.ged"
OUT_DIR = ROOT / "data" / "raw" / "github"
OUT_FAM = OUT_DIR / "_royal92_families.jsonl"
OUT_IND = OUT_DIR / "_royal92_individuals.jsonl"

NAME_SLASH_RE = re.compile(r"/([^/]*)/")
YEAR_RE = re.compile(r"(\d{3,4})")

def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", (s or "").strip().lower(), flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:80] or "unknown"

def parse_year(date_str: str) -> int | None:
    if not date_str:
        return None
    m = YEAR_RE.search(date_str)
    return int(m.group(1)) if m else None


def parse_gedcom(path: Path):
    """Yield (record_id, record_type, lines) tuples. Each record's lines are (level, tag, value)."""
    current_id = None
    current_type = None
    current_lines: list[tuple[int, str, str]] = []
    with path.open(encoding="latin-1") as f:   # GEDCOM is ANSEL/latin-1 in legacy files
        for raw in f:
            raw = raw.rstrip("\r\n")
            if not raw:
                continue
            # split: "level [@ID@] tag [value]"
            parts = raw.split(" ", 2)
            try:
                level = int(parts[0])
            except (ValueError, IndexError):
                continue
            if level == 0:
                # flush prior
                if current_id is not None:
                    yield current_id, current_type, current_lines
                current_id = None
                current_type = None
                current_lines = []
                # new top-level record
                if len(parts) >= 3 and parts[1].startswith("@"):
                    current_id = parts[1].strip("@")
                    current_type = parts[2].split(" ", 1)[0]
                elif len(parts) >= 2:
                    current_type = parts[1]
                continue
            # sub-line
            if len(parts) == 1:
                continue
            tag = parts[1]
            value = parts[2] if len(parts) >= 3 else ""
            current_lines.append((level, tag, value))
        if current_id is not None:
            yield current_id, current_type, current_lines


def main():
    individuals: dict[str, dict] = {}
    families_fam: dict[str, dict] = {}  # GEDCOM FAM records (parent units)

    print(f"Parsing {GED} ...")
    n_indi = n_fam = 0
    for rid, rtype, lines in parse_gedcom(GED):
        if rtype == "INDI":
            n_indi += 1
            person = {
                "id": f"royal92:I{rid.lstrip('I')}" if rid.startswith("I") else f"royal92:{rid}",
                "gedcom_id": rid,
                "name": None,
                "surname": None,
                "given": None,
                "title": None,
                "sex": None,
                "birth": None,
                "death": None,
                "birth_place": None,
                "death_place": None,
                "fams": [],   # families they are spouse-in
                "famc": None, # family they are child-in
            }
            # parse sub-lines; track current top-level tag for DATE under BIRT/DEAT etc.
            in_event = None
            for lvl, tag, val in lines:
                if lvl == 1:
                    in_event = tag
                    if tag == "NAME":
                        # extract surname inside slashes; given is text before
                        m = NAME_SLASH_RE.search(val)
                        surname = (m.group(1) or "").strip() if m else ""
                        given_str = NAME_SLASH_RE.sub("", val).strip()
                        given_str = re.sub(r"\s+", " ", given_str)
                        person["name"] = re.sub(r"\s+", " ", val.replace("/", "").strip())
                        person["given"] = given_str or None
                        person["surname"] = surname or None
                    elif tag == "TITL":
                        person["title"] = val or None
                    elif tag == "SEX":
                        person["sex"] = val.strip() or None
                    elif tag == "FAMS":
                        person["fams"].append(val.strip("@"))
                    elif tag == "FAMC":
                        person["famc"] = val.strip("@")
                elif lvl == 2:
                    if tag == "DATE":
                        if in_event == "BIRT":
                            person["birth"] = parse_year(val)
                        elif in_event == "DEAT":
                            person["death"] = parse_year(val)
                    elif tag == "PLAC":
                        if in_event == "BIRT":
                            person["birth_place"] = val
                        elif in_event == "DEAT":
                            person["death_place"] = val
            individuals[rid] = person
        elif rtype == "FAM":
            n_fam += 1
            husb = wife = None
            chil = []
            for lvl, tag, val in lines:
                if lvl == 1:
                    if tag == "HUSB":
                        husb = val.strip("@")
                    elif tag == "WIFE":
                        wife = val.strip("@")
                    elif tag == "CHIL":
                        chil.append(val.strip("@"))
            families_fam[rid] = {"husb": husb, "wife": wife, "chil": chil}

    print(f"  parsed {n_indi:,} individuals, {n_fam:,} GEDCOM family units (couples)")

    # ---- Enrich individuals with parents/spouses derived from FAM records ----
    parents_of: dict[str, dict] = {}  # iid -> {"father": iid, "mother": iid}
    spouses_of: dict[str, set] = defaultdict(set)
    for fid, fam in families_fam.items():
        h = fam["husb"]; w = fam["wife"]
        if h and w:
            spouses_of[h].add(w)
            spouses_of[w].add(h)
        for cid in fam["chil"]:
            parents_of.setdefault(cid, {})
            if h:
                parents_of[cid]["father"] = h
            if w:
                parents_of[cid]["mother"] = w

    # ---- Cluster individuals by surname ----
    by_surname: dict[str, list[dict]] = defaultdict(list)
    for iid, p in individuals.items():
        sn = (p.get("surname") or "").strip()
        if not sn:
            continue
        # normalize: trim, collapse spaces
        key = re.sub(r"\s+", " ", sn).strip()
        by_surname[key].append(p)

    print(f"  surname clusters: {len(by_surname):,}")

    # ---- Emit individuals.jsonl ----
    print(f"Writing {OUT_IND} ...")
    n_out_indi = 0
    with OUT_IND.open("w", encoding="utf-8") as f:
        for iid, p in individuals.items():
            sn_key = (p.get("surname") or "").strip()
            family_slug = f"royal-tree:royal92:{slugify(sn_key)}" if sn_key and len(by_surname.get(sn_key, [])) >= 3 else None
            par = parents_of.get(iid, {})
            rec = {
                "id": p["id"],
                "gedcom_id": iid,
                "name": p["name"],
                "given": p["given"],
                "surname": p["surname"],
                "title": p["title"],
                "sex": p["sex"],
                "birth": p["birth"],
                "death": p["death"],
                "birth_place": p["birth_place"],
                "death_place": p["death_place"],
                "family": family_slug,
                "father": f"royal92:{par['father']}" if par.get("father") else None,
                "mother": f"royal92:{par['mother']}" if par.get("mother") else None,
                "spouse": sorted([f"royal92:{s}" for s in spouses_of.get(iid, set())]),
            }
            f.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
            n_out_indi += 1
    print(f"  wrote {n_out_indi:,} individuals")

    # ---- Emit family-level records (clusters ≥3) ----
    print(f"Writing {OUT_FAM} ...")
    n_out_fam = 0
    examples = []
    with OUT_FAM.open("w", encoding="utf-8") as f:
        # sort surnames for deterministic output
        for surname, members in sorted(by_surname.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            if len(members) < 3:
                continue
            births = [m["birth"] for m in members if m.get("birth")]
            deaths = [m["death"] for m in members if m.get("death")]
            founded = min(births) if births else None
            extinct_latest = max(deaths) if deaths else None
            # heuristic: if any member has no death year and is born after 1900, treat family as active
            has_living = any((not m.get("death")) and (m.get("birth") or 0) >= 1900 for m in members)
            status = "active" if has_living else ("extinct" if extinct_latest else "unknown")
            # pick first/last members by birth year for raw context
            with_birth = [m for m in members if m.get("birth")]
            with_birth.sort(key=lambda m: m["birth"])
            first_member = with_birth[0]["name"] if with_birth else members[0]["name"]
            last_member = with_birth[-1]["name"] if with_birth else members[-1]["name"]
            slug = slugify(surname)
            # Emit name as "House of <surname>" so name-key cross-link in merge_by_qid
            # catches Wikidata "House of X" records. Also keep raw surname in `raw`.
            rec = {
                "id": f"royal-tree:royal92:{slug}",
                "names": {"en": f"House of {surname}"},
                "country": [],
                "category": "royal",
                "period": {"founded": founded, "extinct": None if status == "active" else extinct_latest},
                "status": status,
                "head_current": None,
                "sources": ["github:arbre-app/public-gedcoms:royal92.ged"],
                "raw": {
                    "member_count": len(members),
                    "first_member": first_member,
                    "last_member": last_member,
                    "surname_raw": surname,
                },
            }
            f.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
            n_out_fam += 1
            if len(examples) < 10:
                examples.append((surname, len(members), founded, extinct_latest))
    print(f"  wrote {n_out_fam:,} family clusters (≥3 members)")
    print("  examples:")
    for s, c, fnd, ext in examples:
        print(f"    {s:30s} {c:>4d} members  founded={fnd}  extinct={ext}")

if __name__ == "__main__":
    main()
