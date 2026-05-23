#!/usr/bin/env python3
"""Phase 5 — annotate relations.jsonl with recency metadata.

For each edge we add a `recency` block:

  recency = {
    latest_year:        int | null,    # max birth year of any via_person
    latest_persons:     [pid, ...],    # up to 3 youngest connecting persons
    active_today:       bool,          # latest_year >= 1950 (heuristic)
    summary_recent:     str,           # one-line readable summary
  }

Also writes `source_family_name` / `target_family_name` for UI convenience.
"""
from __future__ import annotations

import json
import os
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "data" / "master"
RELATIONS = MASTER / "relations.jsonl"
PERSONS = MASTER / "persons.jsonl"
PERSONS_BY_FAM = MASTER / "persons_by_family"
FAMILIES = MASTER / "families.jsonl"
BACKUP = MASTER / "relations.pre_recency.jsonl"


def parse_year(value) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value:
        s = value.strip()
        neg = False
        if s.startswith("-"):
            neg = True
            s = s[1:]
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


def load_persons() -> dict[str, dict]:
    out: dict[str, dict] = {}
    with PERSONS.open() as f:
        for line in f:
            try:
                p = json.loads(line)
            except json.JSONDecodeError:
                continue
            out[p["id"]] = p
    # Also load persons_by_family/* (some persons live only there)
    if PERSONS_BY_FAM.exists():
        for fp in PERSONS_BY_FAM.iterdir():
            if not fp.name.endswith(".jsonl"):
                continue
            with fp.open() as f:
                for line in f:
                    try:
                        p = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if p["id"] not in out:
                        out[p["id"]] = p
    return out


def load_family_names() -> dict[str, str]:
    out: dict[str, str] = {}
    with FAMILIES.open() as f:
        for line in f:
            d = json.loads(line)
            names = d.get("names") or {}
            out[d["id"]] = names.get("en") or names.get("ko") or d["id"]
    return out


def person_label(p: dict | None) -> str:
    if not p:
        return "?"
    name = (p.get("names") or {}).get("en") or (p.get("names") or {}).get("ko")
    if name:
        return name
    raw = p.get("raw") or {}
    given = raw.get("given") or ""
    surname = raw.get("surname") or ""
    return f"{given} {surname}".strip() or p.get("id", "?")


def annotate(edge: dict, persons: dict[str, dict], family_names: dict[str, str]) -> dict:
    via = edge.get("via_persons") or []
    pairs: list[tuple[int, str]] = []
    for pid in via:
        p = persons.get(pid)
        if not p:
            continue
        y = parse_year(p.get("birth"))
        if y is not None:
            pairs.append((y, pid))
    pairs.sort()
    latest_year = pairs[-1][0] if pairs else None
    latest_persons = [pid for _, pid in pairs[-3:][::-1]] if pairs else []

    active_today = latest_year is not None and latest_year >= 1950
    rel_type = edge.get("type")
    subtype = edge.get("subtype")
    src_name = family_names.get(edge.get("source_family"), edge.get("source_family"))
    tgt_name = family_names.get(edge.get("target_family"), edge.get("target_family"))

    if latest_year is None:
        when = "(date unknown)"
    elif latest_year >= 1950:
        when = f"latest link c. {latest_year} — likely active"
    elif latest_year >= 1800:
        when = f"latest link c. {latest_year} — modern era"
    else:
        when = f"latest link c. {latest_year} — historical"

    bridge = ""
    if latest_persons:
        bridge_names = [person_label(persons.get(pid)) for pid in latest_persons[:2]]
        bridge = " via " + ", ".join(bridge_names)

    summary = f"{src_name} ↔ {tgt_name} [{rel_type}/{subtype or '-'}] · {when}{bridge}"

    edge["source_family_name"] = src_name
    edge["target_family_name"] = tgt_name
    edge["recency"] = {
        "latest_year": latest_year,
        "latest_persons": latest_persons,
        "active_today": active_today,
        "summary_recent": summary,
    }
    return edge


def main() -> None:
    print("loading persons…")
    persons = load_persons()
    print(f"  {len(persons):,} persons (combined)")

    print("loading family names…")
    family_names = load_family_names()
    print(f"  {len(family_names):,} families")

    if not BACKUP.exists():
        shutil.copy(RELATIONS, BACKUP)
        print(f"backup → {BACKUP}")

    tmp = RELATIONS.with_suffix(".jsonl.tmp")
    active = 0
    historical = 0
    no_date = 0
    with RELATIONS.open() as src, tmp.open("w") as dst:
        for line in src:
            edge = json.loads(line)
            annotate(edge, persons, family_names)
            rec = edge["recency"]
            if rec["active_today"]:
                active += 1
            elif rec["latest_year"] is None:
                no_date += 1
            else:
                historical += 1
            dst.write(json.dumps(edge, ensure_ascii=False) + "\n")
    os.replace(tmp, RELATIONS)

    print(f"\nactive_today:       {active:>5,}")
    print(f"historical (<1950): {historical:>5,}")
    print(f"date unknown:       {no_date:>5,}")
    print(f"\nrewritten: {RELATIONS}")


if __name__ == "__main__":
    main()
