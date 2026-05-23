#!/usr/bin/env python3
"""Phase 5 — display payload + spouse lineage builder.

For every family with attached persons, appends two blocks:

  family.display = {
    origin:           [persons 0-1]           # founder + first descendant
    middle_summary:   str                     # 1-line collapsed view
    middle_persons:   [person_id, ...]        # expandable IDs
    recent:           [last 2-3 generations]  # rich (titles + businesses + wealth + notes)
    head_card:        {head + spouse + children + business + wealth}
  }

  family.spouses_lineage = [
    { person_id, name, family_of_origin, ancestors[], summary }, ...
  ]

All data is derived locally from data/master/{persons.jsonl,businesses.jsonl,
families.jsonl}. No network calls.
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
PERSONS = MASTER / "persons.jsonl"
PERSONS_BY_FAM = MASTER / "persons_by_family"
BUSINESSES = MASTER / "businesses.jsonl"
BACKUP = MASTER / "families.pre_display.jsonl"

RECENT_GEN = 3      # how many youngest persons go into display.recent
ORIGIN_GEN = 2      # how many oldest persons go into display.origin
SPOUSE_ANC_DEPTH = 4  # ancestor levels to chase for each spouse


def load_all_persons() -> dict[str, dict]:
    out: dict[str, dict] = {}
    with PERSONS.open() as f:
        for line in f:
            try:
                p = json.loads(line)
            except json.JSONDecodeError:
                continue
            out[p["id"]] = p
    return out


def load_family_index(persons: dict[str, dict]) -> dict[str, list[str]]:
    """Map family_id -> list of person_ids. Built from persons_by_family/."""
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
                # Persons in persons_by_family/ may not all be in persons.jsonl;
                # cache them too.
                if p["id"] not in persons:
                    persons[p["id"]] = p
                out[fam_id].append(p["id"])
    return out


def load_businesses() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    if not BUSINESSES.exists():
        return out
    with BUSINESSES.open() as f:
        for line in f:
            try:
                b = json.loads(line)
            except json.JSONDecodeError:
                continue
            fid = b.get("family_id")
            if fid:
                out[fid].append(b)
    return out


def person_label(p: dict) -> str:
    if not p:
        return "(unknown)"
    name = (p.get("names") or {}).get("en") or (p.get("names") or {}).get("ko") or ""
    if name:
        return name
    raw = p.get("raw") or {}
    given = raw.get("given") or ""
    surname = raw.get("surname") or ""
    return f"{given} {surname}".strip() or p.get("id", "?")


def person_summary(p: dict) -> dict:
    """Compact display struct for a single person."""
    if not p:
        return {}
    return {
        "id": p["id"],
        "name": person_label(p),
        "birth": p.get("birth"),
        "death": p.get("death"),
        "gender": p.get("gender"),
        "titles": p.get("titles") or [],
        "father_id": p.get("father_id"),
        "mother_id": p.get("mother_id"),
        "spouse_ids": p.get("spouse_ids") or [],
        "child_ids": p.get("child_ids") or [],
    }


def parse_year(value) -> int | None:
    """Coerce birth/death values (int year, 'YYYY', 'YYYY-MM-DD', '-0044') to int year."""
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value:
        s = value.strip()
        neg = False
        if s.startswith("-"):
            neg = True
            s = s[1:]
        # Take leading digits up to first non-digit
        i = 0
        while i < len(s) and s[i].isdigit():
            i += 1
        if i > 0:
            try:
                y = int(s[:i])
                return -y if neg else y
            except ValueError:
                return None
    return None


def sort_by_birth(pids: list[str], persons: dict[str, dict]) -> list[str]:
    def key(pid: str) -> tuple[int, int]:
        p = persons.get(pid) or {}
        y = parse_year(p.get("birth"))
        # Persons with unknown birth go to the end (large key)
        return (0 if y is not None else 1, y if y is not None else 9999)

    return sorted(pids, key=key)


def title_summary(pids: list[str], persons: dict[str, dict]) -> str:
    """Count notable titles in a list of person IDs."""
    counter: dict[str, int] = defaultdict(int)
    for pid in pids:
        p = persons.get(pid)
        if not p:
            continue
        for t in p.get("titles") or []:
            if t:
                counter[t] += 1
    if not counter:
        return ""
    top = sorted(counter.items(), key=lambda x: -x[1])[:4]
    return ", ".join(f"{n}× {t}" for t, n in top)


def birth_range(pids: list[str], persons: dict[str, dict]) -> tuple[int | None, int | None]:
    mn, mx = None, None
    for pid in pids:
        p = persons.get(pid) or {}
        y = parse_year(p.get("birth"))
        if y is not None:
            mn = y if mn is None else min(mn, y)
            mx = y if mx is None else max(mx, y)
    return mn, mx


def build_recent_entry(p: dict, persons: dict[str, dict], biz: list[dict]) -> dict:
    """Rich entry for a member of the recent 2-3 generations."""
    entry = person_summary(p)
    # Father/mother/spouse labels for readability
    entry["father"] = person_label(persons.get(p.get("father_id"))) if p.get("father_id") else None
    entry["mother"] = person_label(persons.get(p.get("mother_id"))) if p.get("mother_id") else None
    entry["spouses"] = [
        {"id": sid, "name": person_label(persons.get(sid))}
        for sid in (p.get("spouse_ids") or [])
    ]
    entry["children"] = [
        {"id": cid, "name": person_label(persons.get(cid)), "birth": (persons.get(cid) or {}).get("birth")}
        for cid in (p.get("child_ids") or [])
    ]
    # Business / wealth notes — at the *family* level (we can't attribute per-person)
    # The caller picks them up at head_card. For recent entries we just list relevant
    # role keywords from titles + any country.
    entry["country"] = p.get("country") or []
    return entry


def trace_ancestors(pid: str | None, persons: dict[str, dict], depth: int) -> list[dict]:
    """Walk father_id then mother_id up to depth levels (alternating father preferred)."""
    chain: list[dict] = []
    cur = pid
    visited: set[str] = set()
    for _ in range(depth):
        if not cur or cur in visited:
            break
        visited.add(cur)
        p = persons.get(cur)
        if not p:
            break
        chain.append(person_summary(p))
        cur = p.get("father_id") or p.get("mother_id")
    return chain


def find_family_for_person(pid: str, person_to_fam: dict[str, str]) -> str | None:
    return person_to_fam.get(pid)


def build_spouse_lineages(
    head_pid: str | None,
    persons: dict[str, dict],
    person_to_fam: dict[str, str],
    families_index: dict[str, dict],
) -> list[dict]:
    if not head_pid:
        return []
    head = persons.get(head_pid)
    if not head:
        return []
    out = []
    for sid in head.get("spouse_ids") or []:
        sp = persons.get(sid)
        if not sp:
            out.append({"person_id": sid, "name": None, "family_of_origin": None,
                        "ancestors": [], "summary": "(spouse not in local persons index)"})
            continue
        ancestors = trace_ancestors(sp.get("father_id") or sp.get("mother_id"), persons, SPOUSE_ANC_DEPTH)
        family_of_origin = find_family_for_person(sid, person_to_fam)
        family_name = None
        if family_of_origin:
            fam = families_index.get(family_of_origin)
            if fam:
                family_name = (fam.get("names") or {}).get("en") or (fam.get("names") or {}).get("ko")
        summary_parts = []
        if family_name:
            summary_parts.append(f"from {family_name}")
        if ancestors:
            top = ancestors[-1] if ancestors else None
            if top:
                summary_parts.append(f"descended from {top.get('name')}")
        summary = "; ".join(summary_parts) or "(no traceable lineage in local data)"
        out.append({
            "person_id": sid,
            "name": person_label(sp),
            "family_of_origin": family_of_origin,
            "family_name": family_name,
            "ancestors": ancestors,
            "summary": summary,
        })
    return out


def summarize_businesses(biz: list[dict]) -> dict:
    if not biz:
        return {"count": 0, "total_valuation_usd": None, "top": [], "industries": []}
    total = sum((b.get("valuation_usd") or 0) for b in biz)
    top = sorted(biz, key=lambda b: -(b.get("valuation_usd") or 0))[:5]
    industries = sorted({b.get("industry") for b in biz if b.get("industry")})
    return {
        "count": len(biz),
        "total_valuation_usd": total or None,
        "top": [
            {
                "name": (b.get("names") or {}).get("en") or b.get("id"),
                "industry": b.get("industry"),
                "country_hq": b.get("country_hq"),
                "valuation_usd": b.get("valuation_usd"),
                "control_type": b.get("control_type"),
                "is_public": b.get("is_public"),
                "ticker": b.get("ticker"),
            }
            for b in top
        ],
        "industries": industries,
    }


def build_display(
    fam: dict,
    persons: dict[str, dict],
    families_index: dict[str, dict],
    family_persons: dict[str, list[str]],
    biz_by_fam: dict[str, list[dict]],
    person_to_fam: dict[str, str],
) -> tuple[dict, list[dict]] | None:
    pids = family_persons.get(fam["id"], [])
    biz = biz_by_fam.get(fam["id"], [])
    if not pids and not biz:
        return None  # nothing to show beyond what families.jsonl already has

    pids_sorted = sort_by_birth(pids, persons)

    origin_ids = pids_sorted[:ORIGIN_GEN]
    # Pick recent: youngest 3, excluding origin
    recent_pool = [pid for pid in pids_sorted if pid not in origin_ids]
    recent_ids = recent_pool[-RECENT_GEN:] if recent_pool else []
    middle_ids = [pid for pid in pids_sorted if pid not in origin_ids and pid not in recent_ids]

    # Origin block — light summary
    origin = [person_summary(persons.get(pid)) for pid in origin_ids]

    # Recent block — rich
    recent = [build_recent_entry(persons.get(pid) or {}, persons, biz) for pid in recent_ids]

    # Middle block — summary + expandable IDs
    mn, mx = birth_range(middle_ids, persons)
    titles_blurb = title_summary(middle_ids, persons)
    middle_summary = (
        f"{len(middle_ids)} persons"
        + (f" · b. {mn}–{mx}" if mn and mx else "")
        + (f" · {titles_blurb}" if titles_blurb else "")
    ) if middle_ids else ""

    # Head card
    head_pid_raw = fam.get("head_current")
    head_card: dict | None = None
    resolved_head_pid: str | None = None
    if head_pid_raw and head_pid_raw in persons:
        resolved_head_pid = head_pid_raw
        hp = persons[head_pid_raw]
        head_card = build_recent_entry(hp, persons, biz)
        head_card["business"] = summarize_businesses(biz)
        head_card["head_pointer_raw"] = head_pid_raw
    elif head_pid_raw and recent_ids:
        # Head pointer is a free-form label (e.g. "Charles III") — fall through to
        # the latest known person but keep the raw pointer for the UI.
        best_pid = recent_ids[-1]
        resolved_head_pid = best_pid
        head_card = build_recent_entry(persons.get(best_pid) or {}, persons, biz)
        head_card["business"] = summarize_businesses(biz)
        head_card["head_pointer_raw"] = head_pid_raw
        head_card["note"] = f"head_current='{head_pid_raw}' not a known person id; showing latest known"
    elif head_pid_raw:
        head_card = {
            "id": head_pid_raw,
            "name": None,
            "head_pointer_raw": head_pid_raw,
            "note": "head pointer exists but not in local persons index",
            "business": summarize_businesses(biz),
        }
    else:
        if recent_ids:
            best_pid = recent_ids[-1]
            resolved_head_pid = best_pid
            head_card = build_recent_entry(persons.get(best_pid) or {}, persons, biz)
            head_card["note"] = "head_current not set; showing latest known person"
            head_card["business"] = summarize_businesses(biz)
        elif biz:
            head_card = {
                "id": None,
                "name": None,
                "note": "no persons in local data; family known only via business records",
                "business": summarize_businesses(biz),
            }

    display = {
        "origin": origin,
        "middle_summary": middle_summary,
        "middle_persons": middle_ids,
        "recent": recent,
        "head_card": head_card,
    }

    spouses_lineage = build_spouse_lineages(
        resolved_head_pid, persons, person_to_fam, families_index
    ) if resolved_head_pid else []

    return display, spouses_lineage


def main() -> None:
    print("loading persons…")
    persons = load_all_persons()
    print(f"  {len(persons):,} from persons.jsonl")

    print("loading per-family person index…")
    family_persons = load_family_index(persons)
    print(f"  {len(family_persons):,} families with attached persons (post-load: {len(persons):,} persons)")

    # Reverse map: person_id → family_id (first family wins; some persons sit in multiple)
    person_to_fam: dict[str, str] = {}
    for fid, pids in family_persons.items():
        for pid in pids:
            person_to_fam.setdefault(pid, fid)

    print("loading businesses…")
    biz_by_fam = load_businesses()
    print(f"  {len(biz_by_fam):,} families have ≥1 business record")

    print("indexing families…")
    families_index: dict[str, dict] = {}
    with FAMILIES.open() as f:
        for line in f:
            d = json.loads(line)
            families_index[d["id"]] = d
    print(f"  {len(families_index):,} families")

    if not BACKUP.exists():
        shutil.copy(FAMILIES, BACKUP)
        print(f"backup → {BACKUP}")

    tmp = FAMILIES.with_suffix(".jsonl.tmp")
    built = 0
    with FAMILIES.open() as src, tmp.open("w") as dst:
        for line in src:
            fam = json.loads(line)
            result = build_display(
                fam, persons, families_index, family_persons, biz_by_fam, person_to_fam
            )
            if result:
                display, spouses_lineage = result
                fam["display"] = display
                fam["spouses_lineage"] = spouses_lineage
                built += 1
            dst.write(json.dumps(fam, ensure_ascii=False) + "\n")
    os.replace(tmp, FAMILIES)
    print(f"\ndisplay payload added to {built:,} families")
    print(f"rewritten: {FAMILIES}")


if __name__ == "__main__":
    main()
