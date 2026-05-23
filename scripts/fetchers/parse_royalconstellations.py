#!/usr/bin/env python3
"""
Parse nbremer/royalconstellations data into:
  - data/raw/github/_royalconstellations_families.jsonl       (family-level)
  - data/raw/github/_royalconstellations_individuals.jsonl    (every person)
  - data/raw/github/_royalconstellations_relations.jsonl      (every edge)

Family clustering strategy:
  1. Parse "name" column for surname inside parentheses, e.g. "Victoria (Hanover)" → "Hanover".
  2. Where no parenthetical surname exists, fall back to connected-component analysis
     on the father-child / mother-child edges (NOT marriage edges) — kin groups.
  3. Cluster ≥3 members emits a family record.
"""
from __future__ import annotations

import csv, json, re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "data" / "raw" / "github" / "royalconstellations" / "data"
MEMBERS_CSV = SRC_DIR / "royal-families-members-force.csv"
LINKS_JSON  = SRC_DIR / "royal-families-links-force.json"

OUT_DIR = ROOT / "data" / "raw" / "github"
OUT_FAM = OUT_DIR / "_royalconstellations_families.jsonl"
OUT_IND = OUT_DIR / "_royalconstellations_individuals.jsonl"
OUT_REL = OUT_DIR / "_royalconstellations_relations.jsonl"

PAREN_RE = re.compile(r"\(([^)]+)\)")

def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", (s or "").strip().lower(), flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:80] or "unknown"

def safe_year(v):
    if v in (None, "", "NA", "?"):
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def main():
    # ---- Load members ----
    individuals: dict[str, dict] = {}
    with MEMBERS_CSV.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            iid = row["id"]
            name = (row.get("name") or "").strip()
            surname = None
            m = PAREN_RE.search(name)
            if m:
                surname = m.group(1).strip()
            individuals[iid] = {
                "id": f"rc:{iid}",
                "rc_id": iid,
                "name": name,
                "surname": surname,
                "title": (row.get("title") or "").strip() or None,
                "gender": (row.get("gender") or "").strip() or None,
                "birth": safe_year(row.get("birth_date")),
                "death": safe_year(row.get("death_date")),
                "min_offset_to_royal": row.get("min_offset_to_royal"),
                "min_dist_to_royal": row.get("min_dist_to_royal"),
            }
    print(f"  loaded {len(individuals):,} individuals")

    # ---- Load links ----
    with LINKS_JSON.open(encoding="utf-8") as f:
        links = json.load(f)
    print(f"  loaded {len(links):,} edges")

    # ---- Build parent-child adjacency (for connected components) and write relations ----
    parents_of: dict[str, dict] = {}
    spouses_of: dict[str, set] = defaultdict(set)
    parent_adj: dict[str, set] = defaultdict(set)  # for connected-comp by kin
    relation_records = []
    for ln in links:
        src = ln["source"]["id"] if isinstance(ln["source"], dict) else ln["source"]
        tgt = ln["target"]["id"] if isinstance(ln["target"], dict) else ln["target"]
        typ = ln.get("type")
        relation_records.append({
            "source": f"rc:{src}",
            "target": f"rc:{tgt}",
            "type": typ,
            "min_dist_to_royal": ln.get("min_dist_to_royal"),
        })
        if typ == "father-child":
            parents_of.setdefault(tgt, {})["father"] = src
            parent_adj[src].add(tgt); parent_adj[tgt].add(src)
        elif typ == "mother-child":
            parents_of.setdefault(tgt, {})["mother"] = src
            parent_adj[src].add(tgt); parent_adj[tgt].add(src)
        elif typ == "wife-husband":
            spouses_of[src].add(tgt); spouses_of[tgt].add(src)
            # don't union spouses for kin-component analysis

    # ---- Emit relations ----
    print(f"Writing {OUT_REL} ...")
    with OUT_REL.open("w", encoding="utf-8") as f:
        for r in relation_records:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"  wrote {len(relation_records):,} relations")

    # ---- Emit individuals (with family assignment after clustering) ----
    # First cluster by surname (parenthetical)
    by_surname: dict[str, list[str]] = defaultdict(list)
    for iid, p in individuals.items():
        if p.get("surname"):
            by_surname[p["surname"]].append(iid)

    # For individuals without surname → connected-component analysis (kin-only)
    no_surname = [iid for iid, p in individuals.items() if not p.get("surname")]
    seen: set[str] = set()
    components: list[list[str]] = []
    # We restrict component traversal to nodes without a surname so kin without explicit
    # family labels still get grouped, but we don't accidentally merge cross-house lineages.
    no_surname_set = set(no_surname)
    for iid in no_surname:
        if iid in seen:
            continue
        # BFS
        stack = [iid]
        comp = []
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            if cur in no_surname_set:
                comp.append(cur)
                for nb in parent_adj.get(cur, ()):
                    if nb in no_surname_set and nb not in seen:
                        stack.append(nb)
        if comp:
            components.append(comp)

    # Build family slug for each individual
    family_of: dict[str, str] = {}
    family_clusters: list[tuple[str, str, list[str]]] = []  # (slug, label, members_ids)

    for sn, members in by_surname.items():
        if len(members) < 3:
            continue
        slug = f"royal-tree:royalconstellations:{slugify(sn)}"
        for iid in members:
            family_of[iid] = slug
        family_clusters.append((slug, sn, members))

    # For connected components ≥3 with no surname, label by oldest known birth + slug
    cc_idx = 0
    for comp in components:
        if len(comp) < 3:
            continue
        # produce a synthetic label from the oldest member's given name
        comp_members = [individuals[i] for i in comp]
        named = [m for m in comp_members if m.get("name")]
        named.sort(key=lambda m: (m.get("birth") or 9999))
        label_src = named[0]["name"] if named else f"rc_cluster_{cc_idx}"
        # strip parentheses (none expected here) and take first word as label root
        label_root = re.sub(r"\s+", " ", label_src).strip()
        first_token = label_root.split(" ")[0] if label_root else f"cluster{cc_idx}"
        # build a unique slug: "<first-token>-rc<idx>"
        slug = f"royal-tree:royalconstellations:cc-{slugify(first_token)}-{cc_idx}"
        for iid in comp:
            family_of[iid] = slug
        family_clusters.append((slug, f"(kin-group: {label_root})", comp))
        cc_idx += 1

    # ---- Write individuals ----
    print(f"Writing {OUT_IND} ...")
    with OUT_IND.open("w", encoding="utf-8") as f:
        for iid, p in individuals.items():
            par = parents_of.get(iid, {})
            rec = {
                "id": p["id"],
                "rc_id": iid,
                "name": p["name"],
                "surname": p["surname"],
                "title": p["title"],
                "gender": p["gender"],
                "birth": p["birth"],
                "death": p["death"],
                "family": family_of.get(iid),
                "father": f"rc:{par['father']}" if par.get("father") else None,
                "mother": f"rc:{par['mother']}" if par.get("mother") else None,
                "spouse": sorted([f"rc:{s}" for s in spouses_of.get(iid, set())]),
            }
            f.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"  wrote {len(individuals):,} individuals")

    # ---- Emit family-level records ----
    print(f"Writing {OUT_FAM} ...")
    n_out_fam = 0
    examples = []
    with OUT_FAM.open("w", encoding="utf-8") as f:
        # sort by member_count desc
        family_clusters.sort(key=lambda t: -len(t[2]))
        for slug, label, member_ids in family_clusters:
            members = [individuals[i] for i in member_ids]
            births = [m["birth"] for m in members if m.get("birth")]
            deaths = [m["death"] for m in members if m.get("death")]
            founded = min(births) if births else None
            extinct_latest = max(deaths) if deaths else None
            has_living = any((not m.get("death")) and (m.get("birth") or 0) >= 1920 for m in members)
            status = "active" if has_living else ("extinct" if extinct_latest else "unknown")
            with_birth = [m for m in members if m.get("birth")]
            with_birth.sort(key=lambda m: m["birth"])
            first_member = with_birth[0]["name"] if with_birth else members[0]["name"]
            last_member = with_birth[-1]["name"] if with_birth else members[-1]["name"]
            # display name: if parenthetical surname, prefix "House of " for
            # cross-linking with Wikidata "House of X" canonical entries.
            is_kin_comp = label.startswith("(kin-group:")
            display_en = label if is_kin_comp else f"House of {label}"
            rec = {
                "id": slug,
                "names": {"en": display_en},
                "country": [],
                "category": "royal",
                "period": {"founded": founded, "extinct": None if status == "active" else extinct_latest},
                "status": status,
                "head_current": None,
                "sources": ["github:nbremer/royalconstellations"],
                "raw": {
                    "member_count": len(members),
                    "first_member": first_member,
                    "last_member": last_member,
                    "cluster_method": "kin-component" if is_kin_comp else "surname",
                },
            }
            f.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
            n_out_fam += 1
            if len(examples) < 10 and not is_kin_comp:
                examples.append((label, len(members), founded, extinct_latest))
    print(f"  wrote {n_out_fam:,} family clusters")
    print("  examples (surname clusters):")
    for s, c, fnd, ext in examples:
        print(f"    {s:30s} {c:>4d} members  founded={fnd}  extinct={ext}")

if __name__ == "__main__":
    main()
