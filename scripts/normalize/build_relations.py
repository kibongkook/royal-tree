#!/usr/bin/env python3
"""
Phase 3 — Build the family ↔ family relation graph.

Inputs:
  - data/master/persons.jsonl    (8,291 persons from Phase 2)
  - data/raw/github/_royalconstellations_relations.jsonl  (4,601 person→person edges)
  - data/raw/github/_islamic_atlas_rulers.jsonl  (predecessor/successor — succession edges)
  - data/master/families.jsonl  (98,835 families, for context)

Outputs:
  - data/master/relations.jsonl  (family → family edges)
  - data/master/_relations_summary.json
  - data/master/_relations_graph.json  (D3-compatible node-link format)
"""
from __future__ import annotations
import json, re
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[2]
PERSONS = ROOT / "data" / "master" / "persons.jsonl"
FAMS    = ROOT / "data" / "master" / "families.jsonl"
RC_REL  = ROOT / "data" / "raw" / "github" / "_royalconstellations_relations.jsonl"
ISLAM   = ROOT / "data" / "raw" / "github" / "_islamic_atlas_rulers.jsonl"

OUT_REL = ROOT / "data" / "master" / "relations.jsonl"
OUT_SUMMARY = ROOT / "data" / "master" / "_relations_summary.json"
OUT_GRAPH = ROOT / "data" / "master" / "_relations_graph.json"


def load_persons() -> dict[str, dict]:
    persons = {}
    if not PERSONS.exists():
        return persons
    with PERSONS.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            persons[r["id"]] = r
    return persons


def load_families() -> dict[str, dict]:
    fams = {}
    if not FAMS.exists():
        return fams
    with FAMS.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            fams[r["id"]] = r
    return fams


def edge_id(a, b, typ, year=None) -> str:
    pair = sorted([a, b]) if typ in ("marriage", "blood") else [a, b]
    return f"rel:{pair[0]}:{pair[1]}:{typ}" + (f":{year}" if year else "")


def emit_edge(edges, source_fam, target_fam, typ, subtype=None, date=None,
              via_persons=None, weight=1, sources=None, notes=None):
    if not source_fam or not target_fam:
        return
    if source_fam == target_fam:
        return  # intra-family
    year = None
    if isinstance(date, int):
        year = date
    elif isinstance(date, str):
        m = re.match(r"(-?\d{1,4})", date)
        if m:
            try:
                year = int(m.group(1))
            except ValueError:
                pass
    eid = edge_id(source_fam, target_fam, typ, year)
    if eid in edges:
        e = edges[eid]
        if sources:
            for s in sources:
                if s not in e["sources"]:
                    e["sources"].append(s)
        if via_persons:
            for vp in via_persons:
                if vp not in e["via_persons"]:
                    e["via_persons"].append(vp)
        e["weight"] += weight
    else:
        edges[eid] = {
            "id": eid,
            "source_family": source_fam,
            "target_family": target_fam,
            "type": typ,
            "subtype": subtype,
            "date": date,
            "via_persons": list(via_persons or []),
            "weight": weight,
            "sources": list(sources or []),
            "notes": notes,
        }


def main():
    print("Loading persons + families...")
    persons = load_persons()
    fams = load_families()
    print(f"  {len(persons):,} persons, {len(fams):,} families")

    person_to_family = {pid: p.get("family_id") for pid, p in persons.items()}

    edges: dict[str, dict] = {}

    # ---- 1. Marriage + blood from royalconstellations relations ----
    print("\nLifting royalconstellations person-edges to family-edges...")
    n_rc = 0
    if RC_REL.exists():
        with RC_REL.open(encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                src = r["source"] if isinstance(r["source"], str) else r["source"].get("id")
                tgt = r["target"] if isinstance(r["target"], str) else r["target"].get("id")
                # Person ids in this file use "rc:I123" prefix
                fa = person_to_family.get(src)
                fb = person_to_family.get(tgt)
                if not fa or not fb or fa == fb:
                    continue
                t = r.get("type", "")
                if t == "wife-husband":
                    emit_edge(edges, fa, fb, "marriage", subtype="spouse",
                              via_persons=[src, tgt], sources=["royalconstellations"])
                elif t in ("father-child", "mother-child"):
                    # Inter-family parent-child = adoption / illegitimacy / marrying-out child counted twice
                    emit_edge(edges, fa, fb, "blood", subtype=t,
                              via_persons=[src, tgt], sources=["royalconstellations"])
                n_rc += 1
    print(f"  processed {n_rc:,} royalconstellations edges → {len(edges):,} unique family-family edges")

    # ---- 2. Marriage + blood from royal92 spouses + parents ----
    print("\nLifting royal92 spouse + parent edges to family-edges...")
    n_r92 = 0
    for pid, p in persons.items():
        if not pid.startswith("royal92:"):
            continue
        fa = p.get("family_id")
        if not fa:
            continue
        for sp in p.get("spouse_ids") or []:
            fb = person_to_family.get(sp)
            if fb and fb != fa:
                emit_edge(edges, fa, fb, "marriage", subtype="spouse",
                          via_persons=[pid, sp], sources=["royal92"])
                n_r92 += 1
        for parent_key in ("father_id", "mother_id"):
            par = p.get(parent_key)
            if par:
                fb = person_to_family.get(par)
                if fb and fb != fa:
                    emit_edge(edges, fb, fa, "blood",
                              subtype=parent_key.replace("_id", "-of"),
                              via_persons=[par, pid], sources=["royal92"])
                    n_r92 += 1
    print(f"  emitted {n_r92:,} royal92 person-edges → {len(edges):,} cumulative")

    # ---- 2b. Marriage + spouse edges from Wikidata-sourced persons ----
    # Phase 2b adds persons with `source: wikidata` and spouse_ids that are QIDs.
    print("\nLifting Wikidata person edges to family-edges...")
    n_wd = 0
    for pid, p in persons.items():
        if "wikidata" not in p.get("sources", []):
            continue
        fa = p.get("family_id")
        if not fa:
            continue
        for sp in p.get("spouse_ids") or []:
            fb = person_to_family.get(sp)
            if fb and fb != fa:
                emit_edge(edges, fa, fb, "marriage", subtype="spouse",
                          via_persons=[pid, sp], sources=["wikidata"])
                n_wd += 1
        for parent_key in ("father_id", "mother_id"):
            par = p.get(parent_key)
            if par:
                fb = person_to_family.get(par)
                if fb and fb != fa:
                    emit_edge(edges, fb, fa, "blood",
                              subtype=parent_key.replace("_id", "-of"),
                              via_persons=[par, pid], sources=["wikidata"])
                    n_wd += 1
        # Predecessor / successor in different families = succession edge
        for slot in ("predecessor_id", "successor_id"):
            ref = p.get(slot)
            if ref:
                fb = person_to_family.get(ref)
                if fb and fb != fa:
                    sub = "succeeded-by" if slot == "successor_id" else "succeeded"
                    emit_edge(edges, fa, fb, "succession", subtype=sub,
                              via_persons=[pid, ref], weight=2,
                              sources=["wikidata"])
                    n_wd += 1
    print(f"  emitted {n_wd:,} Wikidata person-edges → {len(edges):,} cumulative")

    # ---- 3. Succession edges between Islamic dynasties ----
    # If atlas#A succeeded atlas#B, both have explicit predecessor/successor strings;
    # cross-dynasty references are encoded as the relationship_to_prev mentioning another dynasty name.
    # For our minimal pass, we use the predecessor_ruler/successor_ruler in different dynasties:
    # if the predecessor's QID/slug points to a person in a different dynasty, that's a succession edge.
    print("\nExtracting Islamic-atlas inter-dynasty succession edges...")
    n_islam = 0
    # Build a name → atlas_person_id index
    atlas_name_to_pid: dict[str, str] = {}
    for pid, p in persons.items():
        if not pid.startswith("royal-tree:islamic-atlas:person:"):
            continue
        names = p.get("names") or {}
        for n in [names.get("en"), names.get("tr")]:
            if n:
                # short keys: last token
                key = n.lower().strip()
                atlas_name_to_pid.setdefault(key, pid)
    # Walk again: when predecessor_id is a string, see if it matches another dynasty's ruler
    for pid, p in persons.items():
        if not pid.startswith("royal-tree:islamic-atlas:person:"):
            continue
        fa = p.get("family_id")
        if not fa:
            continue
        for slot, edge_typ in [("predecessor_id", "succession"), ("successor_id", "succession")]:
            ref = p.get(slot)
            if not isinstance(ref, str):
                continue
            ref_clean = ref.strip().lower()
            # Skip dynastic-self references ("Hz. Muhammed", "—", etc.)
            if not ref_clean or ref_clean.startswith(("—", "?", "hz.", "n/a")):
                continue
            # Try to match a known ruler name token
            for tok in ref_clean.split(","):
                t = tok.strip().lower()
                if not t or len(t) < 2:
                    continue
                if t in atlas_name_to_pid:
                    other_pid = atlas_name_to_pid[t]
                    fb = persons[other_pid].get("family_id")
                    if fb and fb != fa:
                        sub = "succeeded-by" if slot == "successor_id" else "succeeded"
                        emit_edge(edges, fa, fb, "succession", subtype=sub,
                                  via_persons=[pid, other_pid], weight=2,
                                  sources=["islamic-atlas"])
                        n_islam += 1
                        break
    print(f"  emitted {n_islam:,} Islamic-atlas inter-dynasty edges")

    # ---- Sort + write ----
    print(f"\nWriting {OUT_REL}...")
    rels = sorted(edges.values(), key=lambda e: (-e["weight"], e["type"], e["source_family"], e["target_family"]))
    with OUT_REL.open("w", encoding="utf-8") as f:
        for r in rels:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

    # ---- Summary ----
    by_type = Counter(r["type"] for r in rels)
    by_subtype = Counter((r["type"], r["subtype"]) for r in rels)
    degree = Counter()
    for r in rels:
        degree[r["source_family"]] += 1
        degree[r["target_family"]] += 1
    top_connected = []
    for fid, deg in degree.most_common(30):
        fname = (fams.get(fid, {}).get("names") or {}).get("en", fid)
        top_connected.append({"family_id": fid, "name_en": fname, "degree": deg})

    summary = {
        "total_edges": len(rels),
        "by_type": dict(by_type),
        "by_subtype": {f"{t}|{s}": n for (t, s), n in by_subtype.most_common()},
        "unique_families_in_graph": len(degree),
        "top_30_most_connected": top_connected,
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    # ---- Graph (D3) ----
    fam_nodes = {}
    for fid in degree:
        f = fams.get(fid, {})
        fam_nodes[fid] = {
            "id": fid,
            "name": (f.get("names") or {}).get("en") or fid,
            "country": (f.get("country") or [None])[0],
            "category": f.get("category") or "unknown",
            "degree": degree[fid],
        }
    graph = {
        "nodes": list(fam_nodes.values()),
        "links": [
            {"source": r["source_family"], "target": r["target_family"],
             "type": r["type"], "weight": r["weight"]}
            for r in rels
        ],
    }
    OUT_GRAPH.write_text(json.dumps(graph, ensure_ascii=False, separators=(",", ":")))

    print(f"\n--- Summary ---")
    print(f"  Total edges:              {len(rels):,}")
    print(f"  Unique families in graph: {len(degree):,}")
    print(f"  By type:")
    for t, n in by_type.most_common():
        print(f"    {t:<14} {n:>5,}")
    print(f"\nTop 10 most-connected families:")
    for x in top_connected[:10]:
        print(f"  {x['degree']:>4}  {x['family_id']}  ({x['name_en']})")


if __name__ == "__main__":
    main()
