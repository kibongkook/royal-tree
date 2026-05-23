#!/usr/bin/env python3
"""Phase 5 — tier classifier.

Derives `tier.past` (historical peak rank) and `tier.current` (present-day
power/wealth/activity) for every family in data/master/families.jsonl.

Signals used (all from local data, no network):
  * past — titles of all persons attached to the family (persons_by_family/)
           + family.category as fallback when no persons attached.
  * current — reigning-monarch QID whitelist, aggregate business valuation,
              presence of head_current, presence of post-1900 persons,
              period.extinct flag.

Output: data/master/families.jsonl is rewritten in place with a new `tier`
        block appended to each record. A backup is written next to it.

Tier scale:
  S — apex (emperors/caliphs/holy roman emperors  ·  reigning major monarchy
      ·  $50B+ active dynasty)
  A — top kingdoms / great houses  ·  reigning mid monarchy  ·  $10-50B
  B — secondary kingdoms / grand-ducal  ·  reigning micro-state  ·  $1-10B
  C — counties / marquessates  ·  active business gentry under $1B
  D — local gentry / clans  ·  dormant noble lines
  X — extinct (period.extinct set or no persons born past 1700 and no current
      head and no businesses)
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
PERSONS_BY_FAM = MASTER / "persons_by_family"
BUSINESSES = MASTER / "businesses.jsonl"
BACKUP = MASTER / "families.pre_tier.jsonl"

# -- past-tier title weights ---------------------------------------------------
# Higher weight wins; emperor-class titles → S, mere knights → D.
TITLE_RANK = {
    # S — imperial / supranational
    "Emperor": "S",
    "Empress": "S",
    "Holy Roman Emperor": "S",
    "Holy Roman Emper": "S",  # truncated in source
    "Tsar": "S",
    "Czar": "S",
    "Khalīfa": "S",
    "Khalīfa / Amīr al-Mu'minīn": "S",
    "Caliph": "S",
    "Great Khan": "S",
    "Khagan": "S",
    "Khan of Khans": "S",
    "Pharaoh": "S",
    "Pope": "S",
    "Augustus": "S",
    # A — kingdoms / sultanates
    "King": "A",
    "Queen": "A",
    "King of France": "A",
    "King of England": "A",
    "King of Scotland": "A",
    "King of Spain": "A",
    "King of Castile": "A",
    "King of Denmark": "A",
    "King of Sweden": "A",
    "King of Norway": "A",
    "King of Wessex": "A",
    "King of Thomond": "A",
    "King of Hungary": "A",
    "King of Bohemia": "A",
    "King of Poland": "A",
    "King of Portugal": "A",
    "King of Italy": "A",
    "King of Saudi Arabia": "A",
    "Sultān": "A",
    "Sultan": "A",
    "Sultana": "A",
    "Shah": "A",
    "Shahanshah": "S",  # king of kings
    "Han": "A",
    "İmâm": "A",
    "Imam": "A",
    "Atabeg": "B",
    "Vali": "B",
    "Bey": "B",
    "Amīr": "B",
    "Amir": "B",
    "Emir": "B",
    "Princely Ruler": "B",
    # B — princely / grand-ducal
    "Grand Duke": "B",
    "Grand Duchess": "B",
    "Grand Prince": "B",
    "Archduke": "B",
    "Archduchess": "B",
    "Prince": "B",
    "Princess": "B",
    "Prince of Wales": "B",
    "Doge": "B",
    "Tsesarevich": "B",
    "Crown Prince": "B",
    "Crown Princess": "B",
    # C — ducal / county
    "Duke": "C",
    "Duchess": "C",
    "Duke of York": "C",
    "Marquess": "C",
    "Marquis": "C",
    "Marchioness": "C",
    "Margrave": "C",
    "Landgrave": "C",
    "Count": "C",
    "Countess": "C",
    "Earl": "C",
    "Count Palatine": "C",
    "Viscount": "C",
    "Viscountess": "C",
    # D — local gentry / honorific
    "Baron": "D",
    "Baroness": "D",
    "Baronet": "D",
    "Lord": "D",
    "Lady": "D",
    "Sir": "D",
    "Hon.": "D",
    "Knight": "D",
    "Chieftain": "D",
    "Sheikh": "D",
    "Shaykh": "D",
}

# Strict tier ordering — lower index = higher rank.
TIER_ORDER = ["S", "A", "B", "C", "D", "X"]


def best_tier(tiers: list[str]) -> str:
    """Return the highest-ranked tier from the list (S beats A beats B …)."""
    if not tiers:
        return "D"
    for t in TIER_ORDER:
        if t in tiers:
            return t
    return "D"


def rank_for_title(title: str) -> str | None:
    if title in TITLE_RANK:
        return TITLE_RANK[title]
    # fuzzy contains — many titles are compound ("Duke of X", "King of Y")
    lower = title.lower()
    if "emperor" in lower or "caliph" in lower or "pharaoh" in lower:
        return "S"
    if "king " in lower or lower.startswith("king") or "sultan" in lower or "shah" in lower:
        return "A"
    if "grand duke" in lower or "archduke" in lower or "prince " in lower:
        return "B"
    if "duke" in lower or "count" in lower or "earl" in lower or "marquess" in lower or "marquis" in lower:
        return "C"
    if "baron" in lower or "lord" in lower or "lady" in lower or "knight" in lower:
        return "D"
    return None


# -- reigning monarchies (current S/A signal) ---------------------------------
# Major reigning houses (S). Hand-curated QID list.
REIGNING_S = {
    "Q81589",   # House of Windsor (UK)
    "Q186040",  # Imperial House of Japan
    "Q909452",  # Imperial House of Japan (alt)
    "Q31711",   # House of Saud
    "Q165687",  # House of Saud (alt)
    "Q102050",  # House of Bourbon-Spain
    "Q24034",   # House of Bernadotte (Sweden)
    "Q183242",  # House of Glücksburg (Denmark)
    "Q151508",  # House of Glücksburg (Norway)
    "Q156040",  # House of Orange-Nassau (Netherlands)
    "Q189930",  # Hashemites (Jordan)
    "Q200116",  # Alaouites (Morocco)
}

# Mid reigning houses (A).
REIGNING_A = {
    "Q40378",   # House of Nassau-Weilburg (Luxembourg)
    "Q151124",  # House of Liechtenstein
    "Q150046",  # House of Grimaldi (Monaco)
    "Q179692",  # Al-Thani (Qatar)
    "Q176410",  # Al-Sabah (Kuwait)
    "Q165722",  # Al-Khalifa (Bahrain)
    "Q156120",  # House of Said (Oman)
    "Q149544",  # Al-Nahyan (UAE)
    "Q176301",  # Al-Maktoum (Dubai)
    "Q187358",  # Chakri dynasty (Thailand)
    "Q12508",   # Wangchuck (Bhutan)
    "Q205057",  # Tupou (Tonga)
    "Q1009",    # Dlamini (Eswatini)
}

# Reigning at sub-national level (Malaysian sultanates, German princely
# houses now in fed-state ceremonial role, etc.) — default B.
REIGNING_B = set()


# -- main ---------------------------------------------------------------------
def load_family_titles() -> dict[str, list[str]]:
    """Build {family_id -> list of titles seen across attached persons}."""
    out: dict[str, list[str]] = defaultdict(list)
    if not PERSONS_BY_FAM.exists():
        return out
    for fp in PERSONS_BY_FAM.iterdir():
        if not fp.name.endswith(".jsonl"):
            continue
        fam_id = fp.stem
        with fp.open() as f:
            for line in f:
                try:
                    p = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for t in p.get("titles") or []:
                    if t:
                        out[fam_id].append(t)
    return out


def load_family_recent_persons() -> dict[str, dict]:
    """For each family: max birth year of any attached person + count post-1900."""
    out: dict[str, dict] = defaultdict(lambda: {"max_birth": None, "post1900": 0, "post1950": 0, "total": 0})
    if not PERSONS_BY_FAM.exists():
        return out
    for fp in PERSONS_BY_FAM.iterdir():
        if not fp.name.endswith(".jsonl"):
            continue
        fam_id = fp.stem
        rec = out[fam_id]
        with fp.open() as f:
            for line in f:
                try:
                    p = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rec["total"] += 1
                birth = p.get("birth")
                if isinstance(birth, int):
                    if rec["max_birth"] is None or birth > rec["max_birth"]:
                        rec["max_birth"] = birth
                    if birth >= 1900:
                        rec["post1900"] += 1
                    if birth >= 1950:
                        rec["post1950"] += 1
    return out


def load_family_valuations() -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    if not BUSINESSES.exists():
        return out
    with BUSINESSES.open() as f:
        for line in f:
            try:
                b = json.loads(line)
            except json.JSONDecodeError:
                continue
            fid = b.get("family_id")
            v = b.get("valuation_usd") or 0
            if fid and v:
                out[fid] += float(v)
    return out


# Keyword → rank scan on the family English name (used when no person titles).
NAME_KEYWORD_RANK = [
    # S — imperial / supranational
    (("imperial house", "imperial dynasty", "imperial family"), "S"),
    (("holy roman", "byzantine emperor", "caliphate", "caliphal", "khaganate",
      "pharaoh", "first emperor", "shahanshah", "empire of "), "S"),
    # A — kingdoms / sultanates
    (("kingdom of", "king of ", "kings of ", "royal house of", "house of saud",
      "house of bourbon", "house of habsburg", "house of romanov",
      "house of windsor", "house of orange", "house of bernadotte",
      "house of glücksburg", "house of grimaldi", "house of liechtenstein",
      "house of nassau", "house of saxe-coburg", "house of hohenzollern",
      "house of wittelsbach", "house of plantagenet", "house of tudor",
      "house of stuart", "house of valois", "house of capet", "house of york",
      "house of lancaster", "house of trastámara", "sultanate of",
      "sultan of ", "shahdom of", "tsardom"), "A"),
    # B — princely / grand-ducal / lesser royal
    (("grand duchy of", "grand prince of", "archduchy of", "principality of",
      "prince of ", "house of medici", "house of este", "house of savoy",
      "house of orleans", "duchy of "), "B"),
    # C — ducal / county
    (("county of", "earldom of", "marquessate of", "margraviate of",
      "duke of ", "earl of ", "count of ", "marquess of ", "marquis of "), "C"),
    # D — local / honorific
    (("baronet of", "baron of ", "barony of", "knight of "), "D"),
]


def rank_from_name(name: str) -> tuple[str | None, str | None]:
    """Return (rank, matched keyword) or (None, None)."""
    if not name:
        return None, None
    lower = name.lower()
    for keywords, rank in NAME_KEYWORD_RANK:
        for kw in keywords:
            if kw in lower:
                return rank, kw
    return None, None


def classify_past(fam: dict, titles: list[str]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    tiers_seen: list[str] = []

    # Strong signal: known reigning royal QID
    fam_id = fam["id"]
    if fam_id in REIGNING_S:
        tiers_seen.append("S")
        reasons.append("major reigning royal house (QID whitelist)")
    elif fam_id in REIGNING_A:
        tiers_seen.append("A")
        reasons.append("mid reigning royal house (QID whitelist)")

    # Person titles
    if titles:
        ranks = []
        rank_to_examples: dict[str, list[str]] = defaultdict(list)
        for t in titles:
            r = rank_for_title(t)
            if r:
                ranks.append(r)
                if len(rank_to_examples[r]) < 3:
                    rank_to_examples[r].append(t)
        tiers_seen.extend(ranks)
        if ranks:
            best = best_tier(ranks)
            ex = rank_to_examples[best]
            reasons.append(
                f"persons hold {best}-class titles: {', '.join(sorted(set(ex)))}"
            )

    # Family-name keyword scan — catches the 99k without person titles
    name = (fam.get("names") or {}).get("en", "")
    name_rank, matched_kw = rank_from_name(name)
    if name_rank:
        tiers_seen.append(name_rank)
        reasons.append(f"name match '{matched_kw}' → {name_rank}")

    # Fall back to category if still nothing
    if not tiers_seen:
        cat = fam.get("category")
        if cat == "royal":
            tiers_seen.append("B")
            reasons.append("category=royal (no person titles, no name match)")
        elif cat == "noble":
            tiers_seen.append("C")
            reasons.append("category=noble (no person titles, no name match)")
        elif cat == "religious":
            tiers_seen.append("B")
            reasons.append("category=religious")
        elif cat == "tribal":
            tiers_seen.append("C")
            reasons.append("category=tribal")
        elif cat == "political":
            tiers_seen.append("C")
            reasons.append("category=political")
        elif cat in ("clan", "business"):
            tiers_seen.append("D")
            reasons.append(f"category={cat}")
        else:
            tiers_seen.append("D")
            reasons.append("category=unknown")
    return best_tier(tiers_seen), reasons


def classify_current(
    fam: dict,
    valuation_usd: float,
    person_recency: dict,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    fam_id = fam["id"]
    status = fam.get("status") or "unknown"
    cat = fam.get("category")

    # Hard X: explicitly extinct
    if status == "extinct" or status == "extinct-male":
        # but still might have current wealth if business descendant
        if valuation_usd < 1e8 and not fam.get("head_current"):
            reasons.append(f"status={status}")
            return "X", reasons

    # Reigning royal house overrides — highest current tier
    if fam_id in REIGNING_S:
        reasons.append("reigning royal house (major)")
        return "S", reasons
    if fam_id in REIGNING_A:
        reasons.append("reigning royal house (mid)")
        return "A", reasons
    if fam_id in REIGNING_B:
        reasons.append("reigning royal house (small)")
        return "B", reasons

    # Wealth-driven
    if valuation_usd >= 50e9:
        reasons.append(f"aggregate valuation ${valuation_usd/1e9:.1f}B (≥$50B)")
        return "S", reasons
    if valuation_usd >= 10e9:
        reasons.append(f"aggregate valuation ${valuation_usd/1e9:.1f}B ($10-50B)")
        return "A", reasons
    if valuation_usd >= 1e9:
        reasons.append(f"aggregate valuation ${valuation_usd/1e9:.1f}B ($1-10B)")
        return "B", reasons
    if valuation_usd > 0:
        reasons.append(f"aggregate valuation ${valuation_usd/1e6:.0f}M (<$1B)")
        # active business but small
        return "C", reasons

    # Activity-driven
    has_head = bool(fam.get("head_current"))
    post1900 = person_recency.get("post1900", 0)
    post1950 = person_recency.get("post1950", 0)
    max_birth = person_recency.get("max_birth")

    if has_head and (post1950 or status == "active"):
        reasons.append("has current head + recent persons or active status")
        return "C", reasons
    if has_head:
        reasons.append("has current head")
        return "C", reasons
    if post1950:
        reasons.append(f"{post1950} persons born ≥1950")
        return "C", reasons
    if post1900:
        reasons.append(f"{post1900} persons born ≥1900")
        return "D", reasons

    # Has persons but all old → dormant
    if person_recency.get("total"):
        if max_birth and max_birth >= 1700:
            reasons.append(f"latest person born {max_birth} — dormant")
            return "D", reasons
        reasons.append(f"latest person born {max_birth or '<1700'} — extinct/dormant")
        return "X", reasons

    # No persons at all, no businesses, no head
    if status == "deposed":
        reasons.append("status=deposed, no current activity")
        return "D", reasons
    if cat == "royal" and status == "active":
        # Probably a non-reigning still-extant royal house
        reasons.append("royal house, active but no public head")
        return "C", reasons
    reasons.append("no persons, no businesses, no current head")
    return "D", reasons


def main() -> None:
    if not FAMILIES.exists():
        raise SystemExit(f"missing {FAMILIES}")

    print("loading per-family titles…")
    title_map = load_family_titles()
    print(f"  {len(title_map):,} families have at least one titled person")

    print("loading per-family person recency…")
    recency_map = load_family_recent_persons()
    print(f"  {len(recency_map):,} families have ≥1 attached person")

    print("loading per-family aggregate valuations…")
    val_map = load_family_valuations()
    print(f"  {len(val_map):,} families have ≥1 valued business")

    # Backup once.
    if not BACKUP.exists():
        shutil.copy(FAMILIES, BACKUP)
        print(f"backup → {BACKUP}")

    tmp = FAMILIES.with_suffix(".jsonl.tmp")
    counts = defaultdict(int)
    with FAMILIES.open() as src, tmp.open("w") as dst:
        for line in src:
            fam = json.loads(line)
            titles = title_map.get(fam["id"], [])
            valuation = val_map.get(fam["id"], 0.0)
            recency = recency_map.get(fam["id"], {"max_birth": None, "post1900": 0, "post1950": 0, "total": 0})

            past, past_reasons = classify_past(fam, titles)
            current, current_reasons = classify_current(fam, valuation, recency)

            fam["tier"] = {
                "past": past,
                "current": current,
                "past_reasons": past_reasons,
                "current_reasons": current_reasons,
                "valuation_usd_total": valuation if valuation else None,
                "person_max_birth": recency["max_birth"],
                "person_count_post1900": recency["post1900"],
                "person_count_post1950": recency["post1950"],
            }
            counts[f"past:{past}"] += 1
            counts[f"current:{current}"] += 1
            dst.write(json.dumps(fam, ensure_ascii=False) + "\n")

    os.replace(tmp, FAMILIES)
    print("\ntier distribution:")
    for k in sorted(counts):
        print(f"  {k:<12} {counts[k]:>8,}")
    print(f"\nrewritten: {FAMILIES}")


if __name__ == "__main__":
    main()
