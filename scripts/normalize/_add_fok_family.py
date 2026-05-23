#!/usr/bin/env python3
"""One-off: enrich the Fok family (Q7195854) with its core members.

User reported the family record exists but is empty. We:
  1. wbgetentities fetch Henry Fok (Q3236818) + sons + grandchildren
  2. BFS P22/P25/P40 1 hop down + spouse (lateral)
  3. append claim rows to _persons_wikidata.jsonl
  4. append (Q7195854, member) pairs to _kin_membership.jsonl
  5. also tag (royal-tree:manual:fok-family) — same physical family — for cross-lookup

After this, run merge_phase6_persons.py + tier/display rebuild as usual.
"""
from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "data" / "master"
PERSONS_WIKIDATA = MASTER / "_persons_wikidata.jsonl"
PERSONS_FETCHED = MASTER / "_persons_fetched.txt"
KIN_MEMBERSHIP = MASTER / "_kin_membership.jsonl"

UA = "RoyalTreeBot/0.6 (kibongkook@gmail.com; Fok seed)"

# Canonical Fok family QID + manual alias
FAM_QIDS = ["Q7195854", "royal-tree:manual:fok-family"]

# Seed person QIDs — Henry Fok + descendants (founder generation, sons, grandsons,
# and key spouses).
SEEDS = [
    "Q3236818",    # Henry Fok 霍英東 (1923-2006) — founder
    "Q7807201",    # Timothy Fok 霍震霆 — eldest son, IOC
    "Q9372313",    # Ian Fok 霍震寰 — second son
    "Q8958593",    # Kenneth Fok 霍啟剛 — Timothy's son
    "Q55719009",   # Kenneth Fok (actor) — disambiguation hit, may not be family
    "Q111693435",  # Eric Fok 霍啟山 — Timothy's son
    "Q270693",     # Guo Jingjing 郭晶晶 — Kenneth's wife
]
KEEP_PROPS = {"P22", "P25", "P26", "P40", "P53", "P569", "P570", "P21", "P27", "P39",
              "P1365", "P1366", "P31"}


def wb_get(batch: list[str]) -> dict:
    url = ("https://www.wikidata.org/w/api.php?action=wbgetentities"
           "&format=json&props=labels|claims&languages=en|ko|ja|zh|de|fr|es|ru|ar"
           "&ids=" + "|".join(batch))
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return r.json()


def slim_claims(claims: dict) -> dict:
    out = {}
    for p, snaks in claims.items():
        if p not in KEEP_PROPS:
            continue
        out[p] = []
        for s in snaks:
            try:
                dv = s["mainsnak"]["datavalue"]
                out[p].append(dv.get("value"))
            except (KeyError, TypeError):
                continue
    return out


def extract_qid(value):
    if isinstance(value, dict):
        v = value.get("id") or value.get("numeric-id")
        if isinstance(v, str) and v.startswith("Q"):
            return v
        if isinstance(v, int):
            return f"Q{v}"
    return None


def load_fetched() -> set[str]:
    s = set()
    if PERSONS_FETCHED.exists():
        with PERSONS_FETCHED.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    s.add(line)
    return s


def load_membership_pairs() -> set[tuple[str, str]]:
    s = set()
    if KIN_MEMBERSHIP.exists():
        with KIN_MEMBERSHIP.open() as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("family_id") and r.get("person_qid"):
                    s.add((r["family_id"], r["person_qid"]))
    return s


def main():
    fetched = load_fetched()
    pairs = load_membership_pairs()
    fpwd = PERSONS_WIKIDATA.open("a")
    fdone = PERSONS_FETCHED.open("a")
    fmem = KIN_MEMBERSHIP.open("a")

    # BFS down 2 hops + spouses
    cache: dict[str, dict] = {}
    visited: set[str] = set()
    members: list[str] = []
    queue: deque = deque((s, 2) for s in SEEDS)  # (qid, down_left)

    while queue:
        layer = []
        while queue and len(layer) < 50:
            layer.append(queue.popleft())
        need = [q for q, _ in layer if q not in visited and q not in cache]
        new_to_fetch = [q for q in need if q not in fetched]
        if new_to_fetch:
            data = wb_get(new_to_fetch)
            ents = data.get("entities", {}) or {}
            for q in new_to_fetch:
                ent = ents.get(q)
                if ent is None:
                    fetched.add(q)
                    fdone.write(q + "\n")
                    continue
                labels = {lang: v.get("value")
                          for lang, v in (ent.get("labels") or {}).items()}
                slim = slim_claims(ent.get("claims") or {})
                fpwd.write(json.dumps({"qid": q, "labels": labels, "claims": slim},
                                      ensure_ascii=False) + "\n")
                fdone.write(q + "\n")
                fetched.add(q)
                cache[q] = slim
                print(f"  fetched {q} = {labels.get('en') or labels.get('zh') or '?'}")
            time.sleep(0.4)
        for q, down_left in layer:
            if q in visited:
                continue
            visited.add(q)
            members.append(q)
            slim = cache.get(q) or {}
            # spouses (one hop)
            for v in slim.get("P26") or []:
                sq = extract_qid(v)
                if sq and sq not in visited:
                    queue.append((sq, 0))
            # children
            if down_left > 0:
                for v in slim.get("P40") or []:
                    cq = extract_qid(v)
                    if cq and cq not in visited:
                        queue.append((cq, down_left - 1))
        fpwd.flush()
        fdone.flush()

    print(f"\nTotal Fok members discovered: {len(members)}")
    for m in members:
        for fid in FAM_QIDS:
            key = (fid, m)
            if key in pairs:
                continue
            pairs.add(key)
            fmem.write(json.dumps({"family_id": fid, "person_qid": m,
                                   "source": "manual:fok-family"},
                                  ensure_ascii=False) + "\n")
    fpwd.close()
    fdone.close()
    fmem.close()
    print(f"membership rows appended for {len(FAM_QIDS)} family aliases × {len(members)} members")


if __name__ == "__main__":
    main()
