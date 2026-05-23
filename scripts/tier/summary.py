#!/usr/bin/env python3
"""Emit Phase-5 summary JSON + Markdown to data/master/_phase5_summary.{json,md}.

Aggregates tier distributions, top-tier families, tier-shift counts
(past≠current), and relation recency totals.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "data" / "master"


def main() -> None:
    past_dist: Counter = Counter()
    cur_dist: Counter = Counter()
    pair_dist: Counter = Counter()
    by_country_cur_S: Counter = Counter()
    top_current: dict[str, list] = {"S": [], "A": [], "B": []}
    rising: list[dict] = []  # current better than past
    falling: list[dict] = []  # past better than current
    TIER_RANK = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4, "X": 5}

    with (MASTER / "families.jsonl").open() as f:
        for line in f:
            d = json.loads(line)
            t = d.get("tier") or {}
            p, c = t.get("past"), t.get("current")
            if p:
                past_dist[p] += 1
            if c:
                cur_dist[c] += 1
            if p and c:
                pair_dist[(p, c)] += 1
                if TIER_RANK.get(c, 9) < TIER_RANK.get(p, 9):
                    rising.append({
                        "id": d["id"], "name": (d.get("names") or {}).get("en"),
                        "past": p, "current": c,
                        "reasons": (t.get("current_reasons") or [])[:1],
                    })
                if TIER_RANK.get(c, 9) > TIER_RANK.get(p, 9) + 1:
                    falling.append({
                        "id": d["id"], "name": (d.get("names") or {}).get("en"),
                        "past": p, "current": c,
                    })
            if c == "S":
                for cc in d.get("country") or []:
                    by_country_cur_S[cc] += 1
            if c in top_current:
                top_current[c].append({
                    "id": d["id"],
                    "name": (d.get("names") or {}).get("en"),
                    "past": p,
                    "valuation_usd_total": t.get("valuation_usd_total"),
                    "country": d.get("country") or [],
                })

    # Sort top-tier lists by valuation desc, fallback alpha
    for tier in top_current:
        top_current[tier].sort(key=lambda r: -(r.get("valuation_usd_total") or 0))

    rel_active = 0
    rel_hist = 0
    rel_unknown = 0
    top_active: list[dict] = []
    with (MASTER / "relations.jsonl").open() as f:
        for line in f:
            e = json.loads(line)
            r = e.get("recency") or {}
            if r.get("active_today"):
                rel_active += 1
                top_active.append({
                    "summary": r.get("summary_recent"),
                    "latest_year": r.get("latest_year"),
                })
            elif r.get("latest_year") is None:
                rel_unknown += 1
            else:
                rel_hist += 1
    top_active.sort(key=lambda r: -(r["latest_year"] or 0))

    summary = {
        "tier_distribution": {
            "past": dict(past_dist),
            "current": dict(cur_dist),
            "pair": {f"{p}->{c}": n for (p, c), n in sorted(pair_dist.items())},
        },
        "current_S_by_country": dict(by_country_cur_S.most_common()),
        "rising_count": len(rising),
        "falling_count": len(falling),
        "rising_examples": rising[:30],
        "falling_examples": falling[:30],
        "top_current": {k: v[:25] for k, v in top_current.items()},
        "relations": {
            "active_today": rel_active,
            "historical": rel_hist,
            "unknown_date": rel_unknown,
            "top_active": top_active[:30],
        },
    }

    out_json = MASTER / "_phase5_summary.json"
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"wrote {out_json}")

    # Compact Markdown
    md = []
    md.append("# Phase 5 Summary — Tier + Display + Recency\n")
    md.append("## Tier distribution\n")
    md.append("| Tier | past | current |\n|---|---:|---:|")
    for t in ("S", "A", "B", "C", "D", "X"):
        md.append(f"| {t} | {past_dist.get(t,0):,} | {cur_dist.get(t,0):,} |")
    md.append("\n## Current-S by country\n")
    for cc, n in by_country_cur_S.most_common(15):
        md.append(f"- {cc}: {n}")
    md.append(f"\n**Rising** (current > past): {len(rising):,}  ·  **Falling** (current << past): {len(falling):,}\n")
    md.append("\n## Top current-S families (by aggregate valuation)\n")
    for r in top_current["S"][:20]:
        v = r.get("valuation_usd_total") or 0
        vs = f"${v/1e9:.1f}B" if v else "—"
        md.append(f"- {r['name'] or r['id']}  ·  past={r['past']}  ·  {vs}  ·  {','.join(r['country'])}")
    md.append("\n## Relations recency\n")
    md.append(f"- active_today: {rel_active}")
    md.append(f"- historical:   {rel_hist}")
    md.append(f"- unknown date: {rel_unknown}")
    md.append("\n### Top-15 active edges\n")
    for e in top_active[:15]:
        md.append(f"- [{e['latest_year']}]  {e['summary']}")

    out_md = MASTER / "_phase5_summary.md"
    out_md.write_text("\n".join(md))
    print(f"wrote {out_md}")


if __name__ == "__main__":
    main()
