#!/usr/bin/env python3
"""Phase 6 — BFS-expand kin graph for tier-S/A/B families via Wikidata.

For every QID-bearing family with tier.past ∈ {S,A,B} or tier.current ∈ {S,A,B},
we walk:

  * head_current (if it is a QID)
  * any QIDs in family.raw / family.head_current that match Q\\d+
  * P509/P509 claim of the family itself (best-effort)

…up `up_depth` generations via P22 (father) / P25 (mother),
…and down `down_depth` generations via P40 (child),
…and laterally via P26 (spouse).

Every fetched entity is written to:
  data/master/_persons_wikidata.jsonl   (append; raw claim row)
  data/master/_persons_fetched.txt      (append; resume marker)
  data/master/_family_seed_log.jsonl    (per-family BFS stats)

Membership: every QID discovered while walking a family's seed graph is
written to:
  data/master/_kin_membership.jsonl     (family_id, person_qid) rows.

Subsequent merge step (scripts/normalize/finalize_persons.py — already
exists) will fold these into persons.jsonl + persons_by_family/.

Usage:
  python3 scripts/fetchers/wikidata_kin_expand.py            # default 1 batch
  python3 scripts/fetchers/wikidata_kin_expand.py --max-batches 200
  python3 scripts/fetchers/wikidata_kin_expand.py --up-depth 3 --down-depth 3
  python3 scripts/fetchers/wikidata_kin_expand.py --tiers SAB
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict, deque
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "data" / "master"
FAMILIES = MASTER / "families.jsonl"
PERSONS_WIKIDATA = MASTER / "_persons_wikidata.jsonl"
PERSONS_FETCHED = MASTER / "_persons_fetched.txt"
KIN_MEMBERSHIP = MASTER / "_kin_membership.jsonl"
SEED_LOG = MASTER / "_family_seed_log.jsonl"

QID_RE = re.compile(r"\bQ\d+\b")

# Relations we follow for the BFS
UP_PROPS = ("P22", "P25")   # father, mother
DOWN_PROPS = ("P40",)        # child
LATERAL_PROPS = ("P26",)     # spouse

# Slim claim set we keep on every fetched entity
KEEP_PROPS = {
    "P22", "P25", "P26", "P40", "P53",
    "P569", "P570", "P21", "P27", "P39",
    "P1365", "P1366", "P31",
}

UA = "RoyalTreeBot/0.6 (kibongkook@gmail.com; Phase 6 kin expander)"


def select_target_families(tiers_chars: str) -> list[dict]:
    """Pick QID families whose tier.past or tier.current is in tiers_chars."""
    allowed = set(tiers_chars.upper())
    out = []
    with FAMILIES.open() as f:
        for line in f:
            d = json.loads(line)
            fid = d["id"]
            if not (isinstance(fid, str) and fid.startswith("Q")):
                continue
            t = d.get("tier") or {}
            past, cur = t.get("past"), t.get("current")
            if past in allowed or cur in allowed:
                out.append(d)
    return out


def load_membership_index() -> dict[str, list[str]]:
    """Load _kin_membership.jsonl (built by wikidata_sparql_seeds.py)
    into family_id -> [person_qid]."""
    idx: dict[str, list[str]] = defaultdict(list)
    if not KIN_MEMBERSHIP.exists():
        return idx
    with KIN_MEMBERSHIP.open() as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            fid = r.get("family_id")
            pq = r.get("person_qid")
            if fid and pq and pq not in idx[fid]:
                idx[fid].append(pq)
    return idx


def extract_seed_qids(fam: dict, membership_idx: dict[str, list[str]] | None = None) -> list[str]:
    """Find person-like QIDs to seed BFS for this family.

    Order of preference:
      1. SPARQL membership (P53) — discovered by wikidata_sparql_seeds.py
      2. head_current (if it is a QID)
      3. QIDs found in family.raw
    """
    seeds: list[str] = []
    if membership_idx:
        for q in membership_idx.get(fam["id"], []):
            if q not in seeds:
                seeds.append(q)
    head = fam.get("head_current")
    if isinstance(head, str) and QID_RE.fullmatch(head) and head not in seeds:
        seeds.append(head)
    raw_blob = json.dumps(fam.get("raw") or {}, ensure_ascii=False)
    for q in QID_RE.findall(raw_blob):
        if q != fam["id"] and q not in seeds:
            seeds.append(q)
    # Cap per-family seeds — extremely large families (Habsburg etc) can have
    # hundreds of members; the BFS will discover the rest from those.
    return seeds[:50]


def load_fetched() -> set[str]:
    s: set[str] = set()
    if PERSONS_FETCHED.exists():
        with PERSONS_FETCHED.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    s.add(line)
    return s


def load_existing_persons_qids() -> set[str]:
    """Persons we already minted in persons.jsonl — skip re-fetching their core,
    but still record family membership."""
    out: set[str] = set()
    p = MASTER / "persons.jsonl"
    if not p.exists():
        return out
    with p.open() as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            pid = rec.get("id")
            if isinstance(pid, str) and pid.startswith("Q"):
                out.add(pid)
    return out


def wb_get(batch: list[str], session: requests.Session) -> dict:
    url = ("https://www.wikidata.org/w/api.php?action=wbgetentities"
           "&format=json&props=labels|claims"
           "&languages=en|ko|ja|zh|de|fr|es|ru|ar"
           "&ids=" + "|".join(batch))
    r = session.get(url, headers={"User-Agent": UA}, timeout=30)
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


def extract_qid(value) -> str | None:
    if isinstance(value, dict):
        v = value.get("id") or value.get("numeric-id")
        if isinstance(v, str) and v.startswith("Q"):
            return v
        if isinstance(v, int):
            return f"Q{v}"
    if isinstance(value, str) and QID_RE.fullmatch(value):
        return value
    return None


def neighbors(slim: dict, props: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for p in props:
        for v in slim.get(p) or []:
            q = extract_qid(v)
            if q:
                out.append(q)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers", default="SAB", help="tiers to enrich (default SAB)")
    ap.add_argument("--up-depth", type=int, default=3)
    ap.add_argument("--down-depth", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=50)
    ap.add_argument("--sleep", type=float, default=0.4)
    ap.add_argument("--max-batches", type=int, default=0, help="0 = unlimited")
    ap.add_argument("--max-families", type=int, default=0, help="0 = unlimited")
    ap.add_argument("--per-family-cap", type=int, default=120,
                    help="cap on new QIDs explored per family BFS")
    args = ap.parse_args()

    fams = select_target_families(args.tiers)
    print(f"target families (tier in {set(args.tiers)}, QID id): {len(fams):,}", flush=True)
    if args.max_families:
        fams = fams[: args.max_families]
        print(f"capped to {len(fams):,}")

    fetched = load_fetched()
    existing_persons = load_existing_persons_qids()
    membership_idx = load_membership_index()
    print(f"already-fetched QIDs: {len(fetched):,}")
    print(f"already-minted persons (skip re-fetch core): {len(existing_persons):,}")
    print(f"SPARQL membership index: {sum(len(v) for v in membership_idx.values()):,} pairs"
          f" across {len(membership_idx):,} families")

    # Build initial frontier: (qid, family_id, depth_dir) — but we just track qid → family_id
    # for membership; depth tracking is per-family local during processing.
    # We process families one-by-one to keep per-family cap honest.

    session = requests.Session()
    n_batches = 0
    n_new_qids = 0
    n_new_entities = 0
    n_family_with_seed = 0

    f_pwd = PERSONS_WIKIDATA.open("a")
    f_done = PERSONS_FETCHED.open("a")
    f_member = KIN_MEMBERSHIP.open("a")
    f_seed_log = SEED_LOG.open("a")

    # Per-process cache: qid -> slim_claims (so we don't re-fetch within session)
    cache: dict[str, dict] = {}

    def fetch_many(qids: list[str]) -> dict[str, dict]:
        nonlocal n_batches, n_new_entities
        need = [q for q in qids if q not in cache and q not in fetched]
        results: dict[str, dict] = {}
        if not need:
            return {q: cache[q] for q in qids if q in cache}
        # Chunk into batch_size
        for i in range(0, len(need), args.batch_size):
            if args.max_batches and n_batches >= args.max_batches:
                break
            chunk = need[i:i + args.batch_size]
            try:
                data = wb_get(chunk, session)
            except Exception as e:
                print(f"  batch error: {e!r}, sleep 3s", flush=True)
                time.sleep(3.0)
                continue
            ents = data.get("entities", {}) or {}
            for q in chunk:
                ent = ents.get(q)
                if ent is None:
                    fetched.add(q)
                    f_done.write(q + "\n")
                    continue
                labels = {lang: v.get("value")
                          for lang, v in (ent.get("labels") or {}).items()}
                slim = slim_claims(ent.get("claims") or {})
                row = {"qid": q, "labels": labels, "claims": slim}
                f_pwd.write(json.dumps(row, ensure_ascii=False) + "\n")
                f_done.write(q + "\n")
                fetched.add(q)
                cache[q] = slim
                results[q] = slim
                n_new_entities += 1
            f_pwd.flush()
            f_done.flush()
            n_batches += 1
            if n_batches % 5 == 0:
                print(f"  …batches={n_batches}  new_entities={n_new_entities}", flush=True)
            time.sleep(args.sleep)
        # Fill from cache for already-known
        for q in qids:
            if q in cache and q not in results:
                results[q] = cache[q]
        return results

    try:
        for idx, fam in enumerate(fams):
            if args.max_batches and n_batches >= args.max_batches:
                print("max-batches hit; stopping")
                break
            seeds = extract_seed_qids(fam, membership_idx)
            if not seeds:
                continue
            n_family_with_seed += 1
            # BFS with depth tracking per direction
            # up: walk P22/P25 from any node
            # down: walk P40 from any node
            # lateral: walk P26 once
            visited: set[str] = set()
            members: set[str] = set()
            queue: deque[tuple[str, int, int]] = deque()  # (qid, up_left, down_left)
            for s in seeds:
                queue.append((s, args.up_depth, args.down_depth))
            while queue and len(members) < args.per_family_cap:
                if args.max_batches and n_batches >= args.max_batches:
                    break
                # Drain one BFS layer
                layer: list[tuple[str, int, int]] = []
                while queue and len(layer) < args.batch_size:
                    layer.append(queue.popleft())
                layer_qids = [q for q, _, _ in layer if q not in visited]
                if not layer_qids:
                    continue
                results = fetch_many(layer_qids)
                for q, up_left, down_left in layer:
                    if q in visited:
                        continue
                    visited.add(q)
                    members.add(q)
                    if len(members) > args.per_family_cap:
                        break
                    slim = results.get(q) or cache.get(q) or {}
                    if not slim:
                        continue
                    # Lateral: add spouse(s) once at current depth
                    for n in neighbors(slim, LATERAL_PROPS):
                        if n not in visited:
                            queue.append((n, 0, 0))
                    if up_left > 0:
                        for n in neighbors(slim, UP_PROPS):
                            if n not in visited:
                                queue.append((n, up_left - 1, 0))
                    if down_left > 0:
                        for n in neighbors(slim, DOWN_PROPS):
                            if n not in visited:
                                queue.append((n, 0, down_left - 1))
            # Persist family membership
            for qid in members:
                f_member.write(json.dumps({"family_id": fam["id"], "person_qid": qid},
                                         ensure_ascii=False) + "\n")
            n_new_qids += len(members)
            f_seed_log.write(json.dumps({
                "family_id": fam["id"],
                "name": (fam.get("names") or {}).get("en"),
                "seeds": seeds,
                "members": len(members),
            }, ensure_ascii=False) + "\n")
            f_member.flush()
            f_seed_log.flush()
            if (idx + 1) % 50 == 0:
                print(f"families={idx+1}  with_seeds={n_family_with_seed}  "
                      f"new_qids={n_new_qids}  batches={n_batches}  "
                      f"entities={n_new_entities}", flush=True)
    finally:
        f_pwd.close()
        f_done.close()
        f_member.close()
        f_seed_log.close()

    print(f"\nDONE  families_processed={idx+1 if fams else 0}  "
          f"with_seeds={n_family_with_seed}  new_qids={n_new_qids}  "
          f"batches={n_batches}  entities={n_new_entities}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
