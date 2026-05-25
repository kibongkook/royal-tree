#!/usr/bin/env python3
"""Export web data: split into a lightweight search index and a rich detail bundle.

- web/families.index.json  — slim per-family fields used for cards/search (~1-2 MB)
- web/families.detail.json — full payloads (recent persons, businesses, relations,
  spouses_lineage), lazy-loaded once user opens detail / runs deep search.
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "data" / "master"
OUT_DIR = ROOT / "web"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TIER_RANK = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4, "X": 5}


def load_relations():
    by_family = defaultdict(list)
    with open(MASTER / "relations.jsonl") as f:
        for line in f:
            d = json.loads(line)
            rec = {
                "src": d.get("source_family"),
                "tgt": d.get("target_family"),
                "src_name": d.get("source_family_name"),
                "tgt_name": d.get("target_family_name"),
                "type": d.get("type"),
                "subtype": d.get("subtype"),
                "weight": d.get("weight"),
                "year": (d.get("recency") or {}).get("latest_year"),
                "active": (d.get("recency") or {}).get("active_today"),
                "summary": (d.get("recency") or {}).get("summary_recent"),
            }
            by_family[rec["src"]].append(rec)
            if rec["tgt"] != rec["src"]:
                by_family[rec["tgt"]].append(rec)
    return by_family


def _name_list(items, limit):
    out = []
    for it in (items or []):
        if isinstance(it, str):
            if it:
                out.append(it)
        elif isinstance(it, dict) and it.get("name"):
            out.append(it["name"])
        if len(out) >= limit:
            break
    return out


def slim_person(p):
    if not p:
        return None
    return {
        "id": p.get("id"),
        "name": p.get("name"),
        "birth": p.get("birth"),
        "death": p.get("death"),
        "titles": (p.get("titles") or [])[:3],
        "spouses": _name_list(p.get("spouses"), 4),
        "children": _name_list(p.get("children"), 6),
        "country": p.get("country") or [],
    }


def slim_business(b):
    if not b:
        return None
    return {
        "name": b.get("name"),
        "industry": b.get("industry"),
        "country_hq": b.get("country_hq") or [],
        "valuation_usd": b.get("valuation_usd"),
        "control_type": b.get("control_type"),
    }


def keep(d):
    tier = d.get("tier") or {}
    tier_cur = tier.get("current") or "X"
    tier_past = tier.get("past") or "X"
    if TIER_RANK.get(tier_cur, 9) <= 2 or TIER_RANK.get(tier_past, 9) <= 1:
        return True
    if (d.get("display") or {}).get("recent") or (d.get("display") or {}).get("origin"):
        return True
    if d.get("head_current"):
        return True
    if tier.get("valuation_usd_total"):
        return True
    return False


def load_overlay():
    """Returns (overlay_records, pantheon_map).

    overlay_records: {id: family_record}  — patches/adds to base families.jsonl
    pantheon_map:    {id: {"pantheon": "sovereign|capital|quiet",
                            "pantheon_rank": int (display order),
                            "headline": str, "narrative": str}}
    """
    p = MASTER / "_web_overlay.json"
    if not p.exists():
        return {}, {}
    blob = json.loads(p.read_text(encoding="utf-8"))
    fams = {f["id"]: f for f in blob.get("families", [])}
    pantheons = {}
    for kind, items in (blob.get("pantheons") or {}).items():
        for rank, it in enumerate(items, start=1):
            pantheons[it["id"]] = {
                "pantheon": kind,
                "pantheon_rank": rank,
                "headline": it.get("headline") or "",
                "narrative": it.get("narrative") or "",
                "founded": it.get("founded"),
                "peak_era": it.get("peak_era"),
            }
    return fams, pantheons


def merge_overlay(base, ov):
    """Shallow-merge overlay fields into base record. Lists/dicts are replaced
    wholesale (not deep-merged) because overlays are intentionally curated."""
    out = dict(base) if base else {}
    for k, v in ov.items():
        out[k] = v
    if ov.get("notes"):
        raw = dict(out.get("raw") or {})
        raw["notes"] = ov["notes"]
        out["raw"] = raw
    if ov.get("relations"):
        out["_overlay_relations"] = ov["relations"]
    return out


def main():
    by_family = load_relations()
    overlays, pantheons = load_overlay()

    index_rows = []
    detail_map = {}

    seen_ids = set()
    base_records = {}
    with open(MASTER / "families.jsonl") as f:
        for line in f:
            d = json.loads(line)
            base_records[d.get("id")] = d

    # Apply overlays: patch existing, add new
    for oid, ov in overlays.items():
        base_records[oid] = merge_overlay(base_records.get(oid), ov)

    records = list(base_records.values())

    for d in records:
        rid = d.get("id")
        in_pantheon = rid in pantheons
        if not in_pantheon and rid not in overlays and not keep(d):
            continue
        # Patch period.founded from pantheon overlay if provided
        if in_pantheon and pantheons[rid].get("founded"):
            period = dict(d.get("period") or {})
            if not period.get("founded"):
                period["founded"] = pantheons[rid]["founded"]
                d["period"] = period
        tier = d.get("tier") or {}
        disp = d.get("display") or {}
        head = (disp.get("head_card") or {})
        biz = (head.get("business") or {})
        rels_for = by_family.get(d.get("id"), [])

        related_names = sorted({
            (r["tgt_name"] if r["src"] == d.get("id") else r["src_name"])
            for r in rels_for if r.get("src_name") and r.get("tgt_name")
        })
        industries = biz.get("industries") or []
        top_biz = [slim_business(b) for b in (biz.get("top") or [])][:5]
        head_name = head.get("name") or d.get("head_current")
        primary_name = (d.get("names") or {}).get("en") \
            or (d.get("names") or {}).get("zh") \
            or (d.get("names") or {}).get("ko") \
            or (d.get("names") or {}).get("ja") \
            or d.get("id")

        sources = d.get("sources") or []
        political = "political" if d.get("category") == "political" else None
        if not political:
            joined = " ".join(sources + [d.get("raw", {}).get("notes") or ""]).lower()
            if any(k in joined for k in ["communist", "ccp", "kuomintang", "kmt", "labour", "conservative", "republican", "democrat", "socialist", "정협"]):
                political = "ideology-mentioned"

        # combine overlay relations (curated) with data-driven relations
        overlay_rels = d.get("_overlay_relations") or []
        data_rels = [
            {
                "with": r["tgt_name"] if r["src"] == d.get("id") else r["src_name"],
                "with_id": r["tgt"] if r["src"] == d.get("id") else r["src"],
                "type": r["type"],
                "subtype": r["subtype"],
                "year": r["year"],
                "active": r["active"],
                "summary": r["summary"],
            }
            for r in sorted(rels_for, key=lambda x: -(x.get("year") or 0))
        ]
        # merge: overlay first, then data; dedupe on (with_id, type)
        seen = set()
        merged_rels = []
        for r in overlay_rels + data_rels:
            key = (r.get("with_id"), r.get("type"))
            if key in seen:
                continue
            seen.add(key)
            merged_rels.append(r)
        merged_rels = merged_rels[:12]

        # related names for the index include overlay rels too
        for r in overlay_rels:
            if r.get("with"):
                related_names.append(r["with"])
        related_names = sorted(set(related_names))

        # Key person names for full-text search (origin + recent + head + spouses/children)
        person_names = set()
        for p in (disp.get("origin") or []) + (disp.get("recent") or []):
            if not p:
                continue
            if p.get("name"):
                person_names.add(p["name"])
            for s in _name_list(p.get("spouses"), 8):
                person_names.add(s)
            for c in _name_list(p.get("children"), 8):
                person_names.add(c)
        if head.get("name"):
            person_names.add(head["name"])
        for s in _name_list(head.get("spouses"), 8):
            person_names.add(s)
        for c in _name_list(head.get("children"), 8):
            person_names.add(c)
        for s in (d.get("spouses_lineage") or []):
            if s.get("name"):
                person_names.add(s["name"])

        pan = pantheons.get(d.get("id")) or {}

        # HOT score — 최근 영향력 (UI에서 "최근 HOT" 정렬용)
        #   post-1950 인물 수 + 활성 relations 수 × 5 + tier_current bonus + biz cap bonus
        post1950 = tier.get("person_count_post1950") or 0
        active_rels = sum(1 for r in rels_for if r.get("active"))
        tier_now = tier.get("current") or "X"
        tier_bonus = {"S": 30, "A": 15, "B": 5, "C": 1, "D": 0, "X": 0}.get(tier_now, 0)
        biz_total = (biz.get("total_valuation_usd") or 0)
        biz_bonus = 0
        if biz_total >= 1e11: biz_bonus = 25  # ≥ $100B
        elif biz_total >= 1e10: biz_bonus = 10  # ≥ $10B
        elif biz_total >= 1e9: biz_bonus = 3   # ≥ $1B
        hot = post1950 + active_rels * 5 + tier_bonus + biz_bonus

        idx = {
            "id": d.get("id"),
            "n": primary_name,
            "names": d.get("names") or {},
            "c": d.get("country") or [],
            "cat": d.get("category"),
            "st": d.get("status"),
            "tp": tier.get("past"),
            "tc": tier.get("current"),
            "v": tier.get("valuation_usd_total"),
            "yr": tier.get("person_max_birth"),
            "head": head_name,
            "inds": industries,
            "biz_names": [b["name"] for b in top_biz if b and b.get("name")],
            "rel": related_names[:20],
            "ppl": sorted(person_names)[:30],
            "pol": political,
            "founded": (d.get("period") or {}).get("founded"),
            "extinct": (d.get("period") or {}).get("extinct"),
            "pantheon": pan.get("pantheon"),
            "pantheon_rank": pan.get("pantheon_rank"),
            "headline": pan.get("headline"),
            "narrative": pan.get("narrative"),
            "peak_era": pan.get("peak_era"),
            "hot": hot,
            "rank_global": (d.get("ranking") or {}).get("rank_global"),
        }
        index_rows.append(idx)

        detail_map[d.get("id")] = {
            "notes": d.get("notes") or (d.get("raw") or {}).get("notes"),
            "sources": sources[:6],
            "tier_reasons_past": tier.get("past_reasons") or [],
            "tier_reasons_current": tier.get("current_reasons") or [],
            "origin": [slim_person(p) for p in (disp.get("origin") or [])][:2],
            "middle_summary": disp.get("middle_summary") or "",
            "recent": [slim_person(p) for p in (disp.get("recent") or [])][:3],
            "head_card": {
                "name": head.get("name"),
                "birth": head.get("birth"),
                "death": head.get("death"),
                "titles": (head.get("titles") or [])[:5],
                "spouses": _name_list(head.get("spouses"), 4),
                "children": _name_list(head.get("children"), 8),
                "country": head.get("country") or [],
                "note": head.get("note"),
                "business": {
                    "count": biz.get("count") or 0,
                    "total_valuation_usd": biz.get("total_valuation_usd"),
                    "industries": industries,
                    "top": top_biz,
                },
            },
            "spouses_lineage": [
                {
                    "person_id": s.get("person_id"),
                    "name": s.get("name"),
                    "family_of_origin": s.get("family_of_origin"),
                    "family_name": s.get("family_name"),
                    "summary": s.get("summary"),
                }
                for s in (d.get("spouses_lineage") or [])
            ][:6],
            "relations": merged_rels,
        }

    index_rows.sort(key=lambda x: (
        TIER_RANK.get(x["tc"] or "X", 9),
        -(x["v"] or 0),
        TIER_RANK.get(x["tp"] or "X", 9),
    ))

    index_out = {
        "generated_at": "2026-05-24",
        "total_in_dataset": 100108,
        "exported": len(index_rows),
        "families": index_rows,
    }
    (OUT_DIR / "families.index.json").write_text(
        json.dumps(index_out, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (OUT_DIR / "families.detail.json").write_text(
        json.dumps(detail_map, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    by_country = defaultdict(int)
    by_cat_country = defaultdict(lambda: defaultdict(list))
    for f in index_rows:
        for c in f["c"]:
            by_country[c] += 1
        cat = f.get("cat") or "unknown"
        for c in f["c"] or [None]:
            cc = c or "_unknown"
            by_cat_country[cat][cc].append(f["id"])
    countries_sorted = sorted(by_country.items(), key=lambda x: -x[1])

    # Pre-built cross-index: category × country × sort_option (top 50 each)
    # 정렬 옵션: wealth (자산순), hot (최근 HOT), name (가나다)
    by_id = {f["id"]: f for f in index_rows}
    cross_index = {}
    for cat, by_c in by_cat_country.items():
        cross_index[cat] = {}
        for cc, ids in by_c.items():
            fams = [by_id[i] for i in ids]
            wealth = sorted(fams, key=lambda f: -(f.get("v") or 0))[:50]
            hot = sorted(fams, key=lambda f: -(f.get("hot") or 0))[:50]
            name = sorted(fams, key=lambda f: (f.get("n") or "").lower())[:50]
            cross_index[cat][cc] = {
                "count": len(fams),
                "wealth": [f["id"] for f in wealth],
                "hot": [f["id"] for f in hot],
                "name": [f["id"] for f in name],
            }
    (OUT_DIR / "indexes.cross.json").write_text(
        json.dumps(cross_index, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    print(f"index  {(OUT_DIR/'families.index.json').stat().st_size/1024/1024:.2f} MB")
    print(f"detail {(OUT_DIR/'families.detail.json').stat().st_size/1024/1024:.2f} MB")
    print(f"cross  {(OUT_DIR/'indexes.cross.json').stat().st_size/1024/1024:.2f} MB")
    print(f"categories indexed: {sorted(cross_index.keys())}")
    print("top countries:", countries_sorted[:15])


if __name__ == "__main__":
    main()
