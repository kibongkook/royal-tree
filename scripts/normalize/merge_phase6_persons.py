#!/usr/bin/env python3
"""Phase 6 — merge fetched Wikidata claim rows into persons.jsonl
and persons_by_family/<fam>.jsonl.

Reuses the same shape as build_persons_hf.py step 5, but consults
`_kin_membership.jsonl` as a primary family-linking source (it carries
SPARQL P53 results + BFS-discovered family edges that may pre-date the
in-claim P53 link).

Idempotent: existing persons.jsonl entries are kept; family links are
filled in if currently null.
"""
from __future__ import annotations

import json
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "data" / "master"
FAMILIES = MASTER / "families.jsonl"
PERSONS = MASTER / "persons.jsonl"
PERSONS_BY_FAM = MASTER / "persons_by_family"
PERSONS_WIKIDATA = MASTER / "_persons_wikidata.jsonl"
KIN_MEMBERSHIP = MASTER / "_kin_membership.jsonl"
BACKUP = MASTER / "persons.pre_phase6.jsonl"


def wd_qid(value):
    if isinstance(value, dict):
        v = value.get("id") or value.get("numeric-id")
        if isinstance(v, str) and v.startswith("Q"):
            return v
        if isinstance(v, int):
            return f"Q{v}"
    if isinstance(value, str) and value.startswith("Q"):
        return value
    return None


def wd_date(val):
    if not isinstance(val, dict):
        return None
    t = val.get("time")
    if not t:
        return None
    # Wikidata time: '+YYYY-MM-DDT00:00:00Z' or '-YYYY-MM-DDT...'
    s = t[1:] if t.startswith("+") else t
    return s.split("T", 1)[0] if "T" in s else s


def load_family_ids() -> set[str]:
    out: set[str] = set()
    with FAMILIES.open() as f:
        for line in f:
            d = json.loads(line)
            if d.get("id"):
                out.add(d["id"])
    return out


def load_membership() -> dict[str, str]:
    """person_qid -> family_id (first family wins)."""
    out: dict[str, str] = {}
    if not KIN_MEMBERSHIP.exists():
        return out
    with KIN_MEMBERSHIP.open() as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            pq = r.get("person_qid")
            fid = r.get("family_id")
            if pq and fid and pq not in out:
                out[pq] = fid
    return out


def load_membership_multi() -> dict[str, list[str]]:
    """person_qid -> [family_ids] (all)."""
    out: dict[str, list[str]] = defaultdict(list)
    if not KIN_MEMBERSHIP.exists():
        return out
    with KIN_MEMBERSHIP.open() as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            pq = r.get("person_qid")
            fid = r.get("family_id")
            if pq and fid and fid not in out[pq]:
                out[pq].append(fid)
    return out


def load_existing_persons() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not PERSONS.exists():
        return out
    with PERSONS.open() as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("id"):
                out[r["id"]] = r
    return out


def build_record(qid: str, labels: dict, claims: dict, family_id: str | None) -> dict:
    birth = next((wd_date(c) for c in claims.get("P569", []) if wd_date(c)), None)
    death = next((wd_date(c) for c in claims.get("P570", []) if wd_date(c)), None)
    gender = None
    for c in claims.get("P21", []):
        g = wd_qid(c)
        if g == "Q6581097":
            gender = "M"
        elif g == "Q6581072":
            gender = "F"
        elif g:
            gender = "other"
        break
    father = next((wd_qid(c) for c in claims.get("P22", []) if wd_qid(c)), None)
    mother = next((wd_qid(c) for c in claims.get("P25", []) if wd_qid(c)), None)
    spouses = [wd_qid(c) for c in claims.get("P26", []) if wd_qid(c)]
    children = [wd_qid(c) for c in claims.get("P40", []) if wd_qid(c)]
    return {
        "id": qid,
        "names": labels,
        "family_id": family_id or "",
        "family_role": "member",
        "birth": birth,
        "death": death,
        "gender": gender,
        "father_id": father,
        "mother_id": mother,
        "spouse_ids": spouses,
        "child_ids": children,
        "predecessor_id": None,
        "successor_id": None,
        "country": [],
        "titles": [],
        "sources": ["wikidata:phase6-bfs"],
    }


def main() -> None:
    if not PERSONS_WIKIDATA.exists():
        raise SystemExit("missing _persons_wikidata.jsonl")

    fam_ids = load_family_ids()
    print(f"family ids: {len(fam_ids):,}")
    membership = load_membership()
    membership_multi = load_membership_multi()
    print(f"membership pairs: {sum(len(v) for v in membership_multi.values()):,}"
          f" (unique persons {len(membership_multi):,})")

    existing = load_existing_persons()
    print(f"existing persons: {len(existing):,}")

    if not BACKUP.exists():
        shutil.copy(PERSONS, BACKUP)
        print(f"backup → {BACKUP}")

    emitted = 0
    relinked = 0
    skipped_nonhuman = 0
    new_records: list[dict] = []
    updated_count = 0

    with PERSONS_WIKIDATA.open() as f:
        for line in f:
            try:
                ent = json.loads(line)
            except json.JSONDecodeError:
                continue
            qid = ent.get("qid")
            if not qid:
                continue
            claims = ent.get("claims") or {}
            labels = ent.get("labels") or {}
            inst_of = [wd_qid(c) for c in claims.get("P31", []) if wd_qid(c)]
            if inst_of and "Q5" not in inst_of:
                skipped_nonhuman += 1
                continue

            # Family linking — priority: in-claim P53, then SPARQL/BFS membership
            fam_id = None
            for c in claims.get("P53", []):
                fq = wd_qid(c)
                if fq and fq in fam_ids:
                    fam_id = fq
                    break
            if not fam_id:
                fid = membership.get(qid)
                if fid and fid in fam_ids:
                    fam_id = fid

            if qid in existing:
                # Update existing record's family_id only if currently empty
                rec = existing[qid]
                changed = False
                if not rec.get("family_id") and fam_id:
                    rec["family_id"] = fam_id
                    relinked += 1
                    changed = True
                # Augment father/mother/spouse/child lists from new claims
                father_new = next((wd_qid(c) for c in claims.get("P22", []) if wd_qid(c)), None)
                if father_new and not rec.get("father_id"):
                    rec["father_id"] = father_new
                    changed = True
                mother_new = next((wd_qid(c) for c in claims.get("P25", []) if wd_qid(c)), None)
                if mother_new and not rec.get("mother_id"):
                    rec["mother_id"] = mother_new
                    changed = True
                cur_spouses = set(rec.get("spouse_ids") or [])
                for s in claims.get("P26", []):
                    sq = wd_qid(s)
                    if sq and sq not in cur_spouses:
                        rec.setdefault("spouse_ids", []).append(sq)
                        cur_spouses.add(sq)
                        changed = True
                cur_children = set(rec.get("child_ids") or [])
                for s in claims.get("P40", []):
                    sq = wd_qid(s)
                    if sq and sq not in cur_children:
                        rec.setdefault("child_ids", []).append(sq)
                        cur_children.add(sq)
                        changed = True
                if changed:
                    updated_count += 1
                continue

            rec = build_record(qid, labels, claims, fam_id)
            new_records.append(rec)
            existing[qid] = rec
            emitted += 1
            if fam_id:
                relinked += 1

    # Write merged persons.jsonl
    print(f"emitting {emitted:,} new + updating {updated_count:,} existing")
    tmp = PERSONS.with_suffix(".jsonl.tmp")
    with tmp.open("w") as out:
        for rec in existing.values():
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(PERSONS)

    # Rebuild persons_by_family/<fam>.jsonl from scratch — based on
    # membership_multi (SPARQL + BFS) plus each person's recorded family_id.
    PERSONS_BY_FAM.mkdir(exist_ok=True, parents=True)
    by_fam: dict[str, list[dict]] = defaultdict(list)
    for rec in existing.values():
        pid = rec["id"]
        attached = set()
        if rec.get("family_id"):
            attached.add(rec["family_id"])
        for fid in membership_multi.get(pid, []):
            attached.add(fid)
        for fid in attached:
            by_fam[fid].append(rec)

    # Preserve any non-QID-keyed family files from a previous pass (manual: etc).
    # We only touch files we have data for, leaving others untouched.
    n_written = 0
    for fid, recs in by_fam.items():
        # Safe filename — replace : / with _
        safe = fid.replace(":", "_").replace("/", "_")
        fp = PERSONS_BY_FAM / f"{fid}.jsonl"
        # Use raw fid if it has no problematic chars (Q\d+ and royal-tree:...)
        if any(c in fid for c in "?\n"):
            fp = PERSONS_BY_FAM / f"{safe}.jsonl"
        with fp.open("w") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        n_written += 1

    print(f"\nMERGE DONE:")
    print(f"  new persons emitted: {emitted:,}")
    print(f"  existing persons updated: {updated_count:,}")
    print(f"  relinked to family: {relinked:,}")
    print(f"  skipped non-human:  {skipped_nonhuman:,}")
    print(f"  persons.jsonl size: {len(existing):,}")
    print(f"  persons_by_family files written: {n_written:,}")


if __name__ == "__main__":
    main()
