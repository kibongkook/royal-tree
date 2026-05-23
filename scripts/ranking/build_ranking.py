#!/usr/bin/env python3
"""Phase 7 — 가문 영향력 ranking (글로벌 + 국가별).

사용자 요구:
  • 전체 기준 = 현재 시점에서 경제적/정치적으로 가장 영향력이 높은 가문
  • 각 국가별 기준 = 같은 공식 (국가 필터)
  • 일본의 경우 천황 가문 > 천황 후보 가문(旧宮家) > 부호 가문 — 이를 정치 점수로
    일반화 (모든 국가의 폐위 황실/통치 가문 후보군에 보너스)

Score:
  political_score   — 통치 royal · 旧宮家 · past:S/A/B + active 등에 부여
  economic_score    — valuation_usd_total (USD raw)
  influence_score   = political_score + economic_score

산출:
  data/master/_ranking_global.jsonl       — top 1000 정렬
  data/master/_ranking_by_country.json    — country → top N
  data/master/_ranking.md                 — 사람이 보는 요약
families.jsonl 각 record에 ranking 블록 추가.
"""
from __future__ import annotations

import json
import os
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "data" / "master"
FAMILIES = MASTER / "families.jsonl"
BACKUP = MASTER / "families.pre_ranking.jsonl"

# ---- Political bonuses (in USD-equivalent units for direct summation) -------
SCORE_REIGNING_S = 1e15
SCORE_REIGNING_A = 5e14
SCORE_REIGNING_B = 1e14
SCORE_FORMER_IMPERIAL = 5e13   # 旧宮家, 폐위 imperial 후보군
SCORE_PAST_S_ACTIVE = 1e13     # 제국·황실 (현재 비통치)
SCORE_PAST_A_ACTIVE = 1e12     # 왕가 (현재 비통치)
SCORE_PAST_B_ACTIVE = 5e10
SCORE_POLITICAL_ACTIVE = 1e10  # category=political + active

# Reigning royal house QID lists (from scripts/tier/classify.py keep in sync)
REIGNING_S = {
    "Q81589", "Q186040", "Q909452", "Q31711", "Q165687", "Q102050",
    "Q24034", "Q183242", "Q151508", "Q156040", "Q189930", "Q200116",
}
REIGNING_A = {
    "Q40378", "Q151124", "Q150046", "Q179692", "Q176410", "Q165722",
    "Q156120", "Q149544", "Q176301", "Q187358", "Q12508", "Q205057",
    "Q1009",
}

# 旧宮家 (Japanese former imperial cadet branches) — manually curated to start;
# we additionally detect by name suffix '-no-miya' / '宮' when JP-tagged.
JAPAN_FORMER_IMPERIAL_QIDS = {
    "Q31538",      # Akishino-no-miya 秋篠宮 (still active)
    "Q1192353",    # Fushimi-no-miya 伏見宮
    "Q8193848",    # Hitachi-no-miya 常陸宮
    "Q10866569",   # Mikasa-no-miya 三笠宮
    "Q4423841",    # Takamado-no-miya 高円宮
    "Q128906334",  # Katsura-no-miya (Prince Yoshihito)
    "Q132154849",  # Ōmiya family (Kan'in line)
}
JAPAN_FORMER_IMPERIAL_MANUAL_PREFIXES = (
    "royal-tree:manual:arisugawa-no-miya",
    "royal-tree:manual:asaka-no-miya",
    "royal-tree:manual:higashi-fushimi-no-miya",
    "royal-tree:manual:higashikuni-no-miya",
    "royal-tree:manual:kachō-no-miya",
    "royal-tree:manual:kanin-no-miya",
    "royal-tree:manual:katsura-no-miya",
    "royal-tree:manual:kitashirakawa-no-miya",
    "royal-tree:manual:komatsu-no-miya",
    "royal-tree:manual:kuni-no-miya",
    "royal-tree:manual:nashimoto-no-miya",
    "royal-tree:manual:takeda-no-miya",
    "royal-tree:manual:yamashina-no-miya",
)


def is_japanese_former_imperial(fam: dict) -> bool:
    if fam["id"] in JAPAN_FORMER_IMPERIAL_QIDS:
        return True
    if fam["id"] in JAPAN_FORMER_IMPERIAL_MANUAL_PREFIXES:
        return True
    # Heuristic catch-all: JP family with '-no-miya' or '宮' in name and past=B
    countries = fam.get("country") or []
    if "JP" not in countries:
        return False
    names = fam.get("names") or {}
    en = (names.get("en") or "").lower()
    ja = names.get("ja") or ""
    if ("-no-miya" in en or "no-miya" in en) and "han" not in en:
        if fam.get("category") in ("royal",) or fam.get("tier", {}).get("past") in ("S", "A", "B"):
            return True
    if ("宮" in ja and "藩" not in ja and "氏" not in ja):
        if fam.get("category") in ("royal",) or fam.get("tier", {}).get("past") in ("S", "A", "B"):
            return True
    return False


def compute_political_score(fam: dict) -> tuple[float, list[str]]:
    fid = fam["id"]
    reasons: list[str] = []
    if fid in REIGNING_S:
        return SCORE_REIGNING_S, ["reigning royal house (major)"]
    if fid in REIGNING_A:
        return SCORE_REIGNING_A, ["reigning royal house (mid)"]
    if is_japanese_former_imperial(fam):
        return SCORE_FORMER_IMPERIAL, ["Japanese former imperial cadet house"]
    t = fam.get("tier") or {}
    past = t.get("past")
    status = fam.get("status") or "unknown"
    active_like = status in ("active", "deposed")
    if past == "S" and active_like:
        return SCORE_PAST_S_ACTIVE, [f"past:S + status={status} (post-imperial)"]
    if past == "A" and active_like:
        return SCORE_PAST_A_ACTIVE, [f"past:A + status={status} (post-royal)"]
    if past == "B" and active_like:
        return SCORE_PAST_B_ACTIVE, [f"past:B + status={status}"]
    if fam.get("category") == "political" and status == "active":
        return SCORE_POLITICAL_ACTIVE, ["category=political + active"]
    return 0.0, []


def compute_economic_score(fam: dict) -> tuple[float, list[str]]:
    t = fam.get("tier") or {}
    val = t.get("valuation_usd_total")
    if val:
        return float(val), [f"valuation_usd_total=${val/1e9:.2f}B"]
    return 0.0, []


def short_name(fam: dict) -> str:
    names = fam.get("names") or {}
    return (names.get("en")
            or names.get("ko")
            or names.get("ja")
            or names.get("zh")
            or fam["id"])


def head_display(fam: dict) -> str:
    disp = fam.get("display") or {}
    hc = disp.get("head_card") or {}
    if hc.get("name"):
        return hc["name"]
    raw = hc.get("head_pointer_raw")
    if raw:
        return f"[{raw}]"
    return "-"


def main() -> None:
    if not BACKUP.exists():
        shutil.copy(FAMILIES, BACKUP)
        print(f"backup → {BACKUP}")

    # Pass 1: load + score
    records: list[dict] = []
    with FAMILIES.open() as f:
        for line in f:
            d = json.loads(line)
            ps, pr = compute_political_score(d)
            es, er = compute_economic_score(d)
            d["ranking"] = {
                "political_score": ps,
                "economic_score": es,
                "influence_score": ps + es,
                "political_reasons": pr,
                "economic_reasons": er,
            }
            records.append(d)

    # ──────────────────────────────────────────────────────────────────────
    # Primary ranking = economic_score desc (사용자 요청: "부호가 많은 순")
    # 통치 royal·旧宮家는 별도 리스트로 출력하므로 economic_score 기준 정렬을 메인으로.
    # 단 다른 데이터 소비자가 종합 점수도 쓸 수 있도록 influence_score 함께 보존.
    # ──────────────────────────────────────────────────────────────────────
    records_sorted_econ = sorted(
        records,
        key=lambda r: (-r["ranking"]["economic_score"],
                       -r["ranking"]["political_score"],
                       short_name(r)),
    )
    for i, r in enumerate(records_sorted_econ, start=1):
        r["ranking"]["rank_global"] = i

    # 통치 royal / 旧宮家 / 폐위 황실 별도 분류
    records_political = [r for r in records if r["ranking"]["political_score"] > 0]
    records_political.sort(key=lambda r: (-r["ranking"]["political_score"], short_name(r)))

    # Per-country ranking — same economic-first ordering
    per_country: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        for cc in r.get("country") or []:
            if cc:
                per_country[cc].append(r)
    for cc, lst in per_country.items():
        lst.sort(key=lambda x: (-x["ranking"]["economic_score"],
                                -x["ranking"]["political_score"],
                                short_name(x)))
        for i, r in enumerate(lst, start=1):
            r["ranking"].setdefault("rank_in_country", {})[cc] = i

    # alias for downstream emit-helpers below
    records_sorted = records_sorted_econ

    # Write back
    tmp = FAMILIES.with_suffix(".jsonl.tmp")
    with tmp.open("w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, FAMILIES)

    # Emit ranking artifacts
    global_jl = MASTER / "_ranking_global.jsonl"
    with global_jl.open("w") as f:
        for r in records_sorted[:2000]:
            f.write(json.dumps({
                "rank": r["ranking"]["rank_global"],
                "id": r["id"],
                "name": short_name(r),
                "country": r.get("country") or [],
                "category": r.get("category"),
                "tier_past": (r.get("tier") or {}).get("past"),
                "tier_current": (r.get("tier") or {}).get("current"),
                "political_score": r["ranking"]["political_score"],
                "economic_score": r["ranking"]["economic_score"],
                "influence_score": r["ranking"]["influence_score"],
                "political_reasons": r["ranking"]["political_reasons"],
                "head": head_display(r),
            }, ensure_ascii=False) + "\n")
    print(f"wrote {global_jl}  (top 2,000)")

    country_json = MASTER / "_ranking_by_country.json"
    by_country_out = {}
    for cc, lst in per_country.items():
        by_country_out[cc] = [{
            "rank": r["ranking"]["rank_in_country"][cc],
            "id": r["id"],
            "name": short_name(r),
            "category": r.get("category"),
            "tier_current": (r.get("tier") or {}).get("current"),
            "influence_score": r["ranking"]["influence_score"],
            "political_reasons": r["ranking"]["political_reasons"],
            "economic_reasons": r["ranking"]["economic_reasons"],
            "head": head_display(r),
        } for r in lst[:50]]
    country_json.write_text(json.dumps(by_country_out, ensure_ascii=False, indent=2))
    print(f"wrote {country_json}  ({len(by_country_out)} countries, top 50 each)")

    def fmt_usd(v: float) -> str:
        if not v:
            return "-"
        if v >= 1e9:
            return f"${v/1e9:.1f}B"
        if v >= 1e6:
            return f"${v/1e6:.0f}M"
        return f"${v:,.0f}"

    # ──── Markdown summary ────
    md = ["# 가문 영향력 Ranking",
          "",
          "사용자 요청: **각 국가별 현재 부호 순 + 전체 경제·정치 영향력 순**",
          "",
          "정렬 기준 = **경제 영향력(USD valuation) 우선**, 동률 시 정치 영향력(통치 royal·旧宮家·황실 출신)으로 tie-break.",
          "통치 royal·旧宮家·폐위 황실은 별도 「정치 영향력」 섹션에 분리 정리.",
          ""]

    # ── 글로벌: 경제 순 Top 50 ──
    md.append("## 글로벌 부호 Top 50 (경제 영향력 순)")
    md.append("")
    md.append("| 순위 | 가문 | 국가 | tier(past→now) | 자산 | head |")
    md.append("|---:|---|---|---|---:|---|")
    rank = 0
    for r in records_sorted:
        rk = r["ranking"]
        if rk["economic_score"] <= 0:
            break
        rank += 1
        if rank > 50:
            break
        cc = ",".join((r.get("country") or [])[:2])
        t = r.get("tier") or {}
        md.append(f"| {rank} | {short_name(r)} | {cc} | "
                  f"{t.get('past','?')}→{t.get('current','?')} | "
                  f"{fmt_usd(rk['economic_score'])} | {head_display(r)} |")
    md.append("")

    # ── 글로벌: 정치 영향력 (통치 royal + 旧宮家 + 황실 출신) ──
    md.append("## 글로벌 정치 영향력 (통치 royal · 旧宮家 · 폐위 황실)")
    md.append("")
    md.append("| 가문 | 국가 | tier | 정치 점수 | 비고 |")
    md.append("|---|---|---|---:|---|")
    for r in records_political[:60]:
        rk = r["ranking"]
        cc = ",".join((r.get("country") or [])[:2])
        t = r.get("tier") or {}
        ps = rk["political_score"]
        if ps >= 1e15: ps_s = "S (reigning major)"
        elif ps >= 5e14: ps_s = "A (reigning mid)"
        elif ps >= 1e14: ps_s = "B (reigning micro)"
        elif ps >= 5e13: ps_s = "former imperial"
        elif ps >= 1e13: ps_s = "post-imperial"
        elif ps >= 1e12: ps_s = "post-royal"
        else: ps_s = f"{ps:.0e}"
        reason = (rk["political_reasons"] or [""])[0]
        md.append(f"| {short_name(r)} | {cc} | "
                  f"{t.get('past','?')}→{t.get('current','?')} | "
                  f"{ps_s} | {reason} |")
    md.append("")

    # Per-country 부호 Top 15
    md.append("## 주요 국가별 부호 Top 15 (경제 영향력 순)")
    PRIORITY_COUNTRIES = [
        "US", "JP", "KR", "CN", "GB", "DE", "FR", "IT", "RU", "IN",
        "SA", "AE", "BR", "MX", "CA", "AU", "ES", "SE", "NL", "TH",
        "HK", "TW", "SG", "ID", "TR", "AT", "CH", "BE", "DK", "NO",
    ]
    for cc in PRIORITY_COUNTRIES:
        lst = per_country.get(cc) or []
        if not lst:
            continue
        # 경제 점수 > 0인 것만 표시. 부호가 없는 국가는 아래 정치 섹션에 표시.
        wealthy = [r for r in lst if r["ranking"]["economic_score"] > 0][:15]
        ruling = [r for r in lst if r["ranking"]["political_score"] >= 5e13][:10]
        md.append(f"\n### {cc} (총 {len(lst):,}개)\n")
        if ruling:
            md.append(f"**현재 통치/황실 가문:** "
                      + " · ".join(short_name(r) for r in ruling) + "\n")
        if wealthy:
            md.append("| 순위 | 가문 | 카테고리 | tier_now | 자산 | head |")
            md.append("|---:|---|---|---|---:|---|")
            for r in wealthy:
                rk = r["ranking"]
                md.append(f"| {rk['rank_in_country'][cc]} | {short_name(r)} | "
                          f"{r.get('category','?')} | "
                          f"{(r.get('tier') or {}).get('current','?')} | "
                          f"{fmt_usd(rk['economic_score'])} | {head_display(r)} |")
        else:
            md.append("_(공개된 valuation 데이터 없음)_")

    rank_md = MASTER / "_ranking.md"
    rank_md.write_text("\n".join(md))
    print(f"wrote {rank_md}")

    print(f"\nTOTAL FAMILIES SCORED: {len(records):,}")
    print(f"  with political_score > 0: "
          f"{sum(1 for r in records if r['ranking']['political_score'] > 0):,}")
    print(f"  with economic_score > 0:  "
          f"{sum(1 for r in records if r['ranking']['economic_score'] > 0):,}")
    print(f"  with influence > 0:       "
          f"{sum(1 for r in records if r['ranking']['influence_score'] > 0):,}")


if __name__ == "__main__":
    main()
