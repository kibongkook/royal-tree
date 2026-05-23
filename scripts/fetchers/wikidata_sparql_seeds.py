#!/usr/bin/env python3
"""Phase 6 — SPARQL seeding for tier-S/A/B families.

For QID-bearing families, query Wikidata for any person with
`wdt:P53 = family` (member of noble family) — that's the canonical
membership claim. We batch up to 50 family QIDs per SPARQL request
using VALUES.

Writes:
  data/master/_kin_membership.jsonl   (append; family_id + person_qid rows)
  data/master/_sparql_seed_log.jsonl  (append; per-batch stats)

Idempotent — already-discovered (family_id, person_qid) pairs are skipped
on subsequent runs.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "data" / "master"
FAMILIES = MASTER / "families.jsonl"
KIN_MEMBERSHIP = MASTER / "_kin_membership.jsonl"
SEED_LOG = MASTER / "_sparql_seed_log.jsonl"

UA = "RoyalTreeBot/0.6 (kibongkook@gmail.com; Phase 6 SPARQL seeder)"
SPARQL_URL = "https://query.wikidata.org/sparql"


def select_targets(tiers_chars: str) -> list[str]:
    allowed = set(tiers_chars.upper())
    out = []
    with FAMILIES.open() as f:
        for line in f:
            d = json.loads(line)
            fid = d.get("id")
            if not (isinstance(fid, str) and fid.startswith("Q")):
                continue
            t = d.get("tier") or {}
            if (t.get("past") in allowed) or (t.get("current") in allowed):
                out.append(fid)
    return out


def load_already_seen() -> set[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    if KIN_MEMBERSHIP.exists():
        with KIN_MEMBERSHIP.open() as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                fid = r.get("family_id")
                pq = r.get("person_qid")
                if fid and pq:
                    seen.add((fid, pq))
    return seen


def run_sparql(query: str, session: requests.Session) -> dict:
    headers = {"User-Agent": UA, "Accept": "application/sparql-results+json"}
    r = session.get(SPARQL_URL, params={"query": query}, headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()


def chunked(seq: list, n: int):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def build_query(family_qids: list[str], extra_props: list[str]) -> str:
    """Members via P53. Also union with P39(position) for "House of X" titles
    *only* when a single family is queried — multi-family unions get too noisy."""
    values = " ".join(f"wd:{q}" for q in family_qids)
    # P53 = member of noble family; cover both directions plus P22/P25/P40 if requested
    return f"""
SELECT DISTINCT ?person ?family WHERE {{
  VALUES ?family {{ {values} }}
  ?person wdt:P53 ?family .
}}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers", default="SAB")
    ap.add_argument("--batch-size", type=int, default=50,
                    help="families per SPARQL request")
    ap.add_argument("--sleep", type=float, default=1.0,
                    help="pause between requests (Wikidata politeness)")
    ap.add_argument("--max-batches", type=int, default=0)
    args = ap.parse_args()

    targets = select_targets(args.tiers)
    print(f"target QID families: {len(targets):,}")

    seen = load_already_seen()
    print(f"already known (fam,person) pairs: {len(seen):,}")

    session = requests.Session()
    fout = KIN_MEMBERSHIP.open("a")
    flog = SEED_LOG.open("a")

    n_batches = 0
    n_new = 0
    n_errors = 0
    try:
        for batch in chunked(targets, args.batch_size):
            if args.max_batches and n_batches >= args.max_batches:
                break
            q = build_query(batch, [])
            try:
                data = run_sparql(q, session)
            except Exception as e:
                n_errors += 1
                print(f"  batch {n_batches} error: {e!r}; sleep 5s", flush=True)
                time.sleep(5.0)
                continue
            bindings = data.get("results", {}).get("bindings", []) or []
            batch_new = 0
            for row in bindings:
                pp = (row.get("person") or {}).get("value", "")
                ff = (row.get("family") or {}).get("value", "")
                pq = pp.rsplit("/", 1)[-1] if pp else ""
                fq = ff.rsplit("/", 1)[-1] if ff else ""
                if not pq.startswith("Q") or not fq.startswith("Q"):
                    continue
                key = (fq, pq)
                if key in seen:
                    continue
                seen.add(key)
                fout.write(json.dumps({"family_id": fq, "person_qid": pq,
                                       "source": "sparql:P53"},
                                      ensure_ascii=False) + "\n")
                n_new += 1
                batch_new += 1
            fout.flush()
            flog.write(json.dumps({"batch": n_batches, "fam_count": len(batch),
                                   "new_pairs": batch_new,
                                   "total_bindings": len(bindings)},
                                  ensure_ascii=False) + "\n")
            flog.flush()
            n_batches += 1
            if n_batches % 5 == 0:
                print(f"  batches={n_batches} new_pairs={n_new} errors={n_errors}",
                      flush=True)
            time.sleep(args.sleep)
    finally:
        fout.close()
        flog.close()

    print(f"\nDONE  batches={n_batches}  new_pairs={n_new}  errors={n_errors}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
