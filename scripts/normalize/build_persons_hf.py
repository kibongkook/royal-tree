#!/usr/bin/env python3
"""
build_persons_hf.py — Phase 2, step 3+4+5: HF Wikidata-people pass.

Runs after the banked-source pass (build_persons.py). Resumable.

Steps:
  3  String-match 250k HF bios against family-name tokens -> _hf_candidates.jsonl
  4  Batched wbgetentities for matched candidate QIDs (50 ids/call)
  5  Merge fetched Wikidata claims into persons.jsonl (append-only, idempotent)

Persistent state (data/master/):
  _hf_candidates.jsonl     step3 output
  _persons_fetched.txt     QIDs already pulled via wbgetentities
  _persons_wikidata.jsonl  raw fetched claims (one entity per line)
  persons.jsonl            final output (appended to in step5)

Usage:
  python3 scripts/normalize/build_persons_hf.py --step 3
  python3 scripts/normalize/build_persons_hf.py --step 4 --max-batches 20
  python3 scripts/normalize/build_persons_hf.py --step 5
"""

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
MASTER = DATA / "master"
RAW = DATA / "raw"

FAMILIES_JSONL = MASTER / "families.jsonl"
ALIAS_MAP_TSV = MASTER / "_alias_map.tsv"
PERSONS_FINAL = MASTER / "persons.jsonl"
HF_CANDIDATES = MASTER / "_hf_candidates.jsonl"
PERSONS_FETCHED = MASTER / "_persons_fetched.txt"
PERSONS_WIKIDATA = MASTER / "_persons_wikidata.jsonl"
PERSONS_SUMMARY = MASTER / "_persons_summary.json"

HF_TRAIN = RAW / "huggingface" / "yale-cultural-heritage_wikidata-people" / "data" / "train-00000-of-00001.parquet"
HF_TEST = RAW / "huggingface" / "yale-cultural-heritage_wikidata-people" / "data" / "test-00000-of-00001.parquet"

# Tokens too common to be useful family discriminators
STOPWORDS = {
    "family", "house", "of", "the", "von", "van", "de", "la", "le", "del",
    "der", "den", "di", "da", "y", "el", "al", "ibn", "bin", "and",
    "dynasty", "clan", "tribe", "lineage", "company", "ltd", "inc", "co",
    "corp", "group", "holdings", "limited", "ben", "son", "sons",
    "saints", "kings", "princes", "queens", "lords", "ladies", "nobles",
    "royal", "imperial", "kingdom", "empire", "republic", "state",
    "first", "second", "third", "great", "good", "elder", "younger",
    "branch", "main", "junior", "senior", "old", "new", "north", "south",
    "east", "west", "central", "people", "nation", "country", "land",
    "members", "descendants", "ancestors", "founder", "ruler",
}

# Surnames/words so common they'd hit any English bio
SUPER_COMMON = {
    "john", "smith", "williams", "jones", "brown", "miller", "davis",
    "wilson", "moore", "taylor", "anderson", "thomas", "jackson",
    "white", "harris", "martin", "thompson", "garcia", "martinez",
    "robinson", "clark", "lewis", "lee", "walker", "hall", "allen",
    "young", "king", "wright", "hill", "green", "adams", "baker",
    "nelson", "carter", "mitchell", "perez", "roberts", "turner",
    "phillips", "campbell", "parker", "evans", "edwards", "collins",
    "stewart", "morris", "rogers", "reed", "cook", "morgan", "bell",
    "murphy", "bailey", "rivera", "cooper", "richardson", "cox",
    "howard", "ward", "torres", "peterson", "gray", "ramirez", "watson",
    "kim", "park", "lee", "choi", "kang", "wang", "li", "chen",
    "zhang", "liu", "yang", "huang", "zhao", "wu", "zhou", "xu",
    "sun", "ma", "zhu", "hu", "guo", "he", "lin", "luo", "tang",
    "song", "han", "tan", "feng", "ding", "yu", "shen", "shi",
    "satō", "suzuki", "takahashi", "tanaka", "watanabe", "ito",
    "yamamoto", "nakamura", "kobayashi", "kato", "yoshida", "yamada",
    "sasaki", "yamaguchi", "matsumoto", "inoue", "kimura", "hayashi",
}


def load_alias_map() -> dict[str, str]:
    m: dict[str, str] = {}
    if not ALIAS_MAP_TSV.exists():
        return m
    with ALIAS_MAP_TSV.open() as f:
        next(f, None)
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                m[parts[0]] = parts[1]
    return m


def tokenize_family_name(name: str) -> list[str]:
    if not name:
        return []
    name = re.sub(r"\([^)]*\)", " ", name)
    toks = re.findall(r"[A-Za-zÀ-ɏ]+", name)
    out = []
    for t in toks:
        tl = t.lower()
        if len(tl) >= 4 and tl not in STOPWORDS and tl not in SUPER_COMMON:
            out.append(tl)
    return out


def build_family_index() -> tuple[dict, dict]:
    """Return (families_by_id, token_to_ids)."""
    families_by_id: dict[str, dict] = {}
    token_to_ids: dict[str, list[str]] = defaultdict(list)
    with FAMILIES_JSONL.open() as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            fid = r.get("id")
            if not fid:
                continue
            families_by_id[fid] = r
            for lang in ("en", "ko", "ja", "zh", "de", "fr", "es"):
                nm = (r.get("names") or {}).get(lang)
                if not nm:
                    continue
                for tok in tokenize_family_name(nm):
                    token_to_ids[tok].append(fid)
    for k in list(token_to_ids):
        token_to_ids[k] = list(dict.fromkeys(token_to_ids[k]))
    return families_by_id, dict(token_to_ids)


def step3(min_token_len: int = 7, max_fams_per_token: int = 5,
          generic_threshold_pct: float = 0.0004,
          require_min_matches: int = 1):
    """String-match HF bios against DISTINCTIVE family-name tokens.

    Two-pass:
      Pass A: sample bios to discover generic English tokens (appearing in
              >= generic_threshold_pct of bios). Discard these from the family
              token set.
      Pass B: full scan; emit candidate only if any bio word intersects the
              filtered family tokens.
    """
    try:
        import pyarrow.parquet as pq
    except ImportError:
        print("[step3] pyarrow required", file=sys.stderr)
        sys.exit(1)

    print("[step3] building family index ...", flush=True)
    fams_by_id, token_to_ids = build_family_index()
    print(f"[step3] families={len(fams_by_id):,}  tokens={len(token_to_ids):,}", flush=True)

    word_re = re.compile(r"[A-Za-zÀ-ɏ]+")

    # ---- Pass A: discover generic tokens ----
    print("[step3] pass A: sampling 50k bios for generic words ...", flush=True)
    from collections import Counter
    bio_freq = Counter()
    sampled = 0
    if HF_TRAIN.exists():
        pf = pq.ParquetFile(HF_TRAIN)
        for batch in pf.iter_batches(batch_size=5000, columns=["input"]):
            for inp in batch.column("input").to_pylist():
                if inp is None:
                    continue
                for w in word_re.findall(inp):
                    wl = w.lower()
                    if len(wl) >= min_token_len:
                        bio_freq[wl] += 1
            sampled += batch.num_rows
            if sampled >= 50000:
                break
    thresh = max(50, int(sampled * generic_threshold_pct))
    generic = {t for t, c in bio_freq.items() if c >= thresh}
    print(f"[step3] sampled={sampled:,}  generic tokens (>= {thresh} occurrences): {len(generic):,}", flush=True)

    # ---- Build keep_tokens ----
    keep_tokens: set[str] = set()
    for tok, ids in token_to_ids.items():
        if len(tok) < min_token_len:
            continue
        if len(ids) > max_fams_per_token:
            continue
        if tok in generic:
            continue
        keep_tokens.add(tok)
    print(f"[step3] usable tokens (>= {min_token_len} chars, <= {max_fams_per_token} fams, not generic): {len(keep_tokens):,}", flush=True)

    # ---- Pass B: full scan ----
    n_total, n_kept = 0, 0
    HF_CANDIDATES.unlink(missing_ok=True)
    with HF_CANDIDATES.open("w") as fout:
        for src_path in [HF_TRAIN, HF_TEST]:
            if not src_path.exists():
                continue
            print(f"[step3] scanning {src_path.name} ...", flush=True)
            pf = pq.ParquetFile(src_path)
            for batch in pf.iter_batches(batch_size=5000, columns=["input", "output"]):
                inputs = batch.column("input").to_pylist()
                outputs = batch.column("output").to_pylist()
                for inp, qid in zip(inputs, outputs):
                    n_total += 1
                    if not inp or not qid:
                        continue
                    bio_words = {w.lower() for w in word_re.findall(inp)}
                    matches = bio_words & keep_tokens
                    if len(matches) < require_min_matches:
                        continue
                    fam_ids: list[str] = []
                    for tok in matches:
                        fam_ids.extend(token_to_ids.get(tok, []))
                    fam_ids = list(dict.fromkeys(fam_ids))[:30]
                    fout.write(json.dumps({
                        "qid": qid,
                        "input": inp[:500],
                        "matched_tokens": sorted(matches),
                        "candidate_family_ids": fam_ids,
                        "n_matches": len(matches),
                    }, ensure_ascii=False) + "\n")
                    n_kept += 1
                if n_total % 25000 < 5000:
                    print(f"[step3] scanned={n_total:,} kept={n_kept:,}", flush=True)
    print(f"[step3] DONE scanned={n_total:,} kept={n_kept:,}", flush=True)
    return {"scanned": n_total, "kept": n_kept}


def load_fetched() -> set[str]:
    if not PERSONS_FETCHED.exists():
        return set()
    s = set()
    with PERSONS_FETCHED.open() as f:
        for line in f:
            line = line.strip()
            if line:
                s.add(line)
    return s


def step4(max_batches: int = 0, batch_size: int = 50, sleep_s: float = 0.5,
          priority_only: bool = True):
    """Batched wbgetentities fetch for candidate QIDs. Resumable.

    If priority_only, fetch only QIDs whose candidate_family_ids has a master
    family hit. This drastically reduces the API budget while still grabbing
    the highest-confidence rows.
    """
    import requests

    if not HF_CANDIDATES.exists():
        print("[step4] no _hf_candidates.jsonl; run step 3 first", file=sys.stderr)
        sys.exit(1)

    fams_by_id, _ = build_family_index()
    fams_set = set(fams_by_id.keys())
    aliases = load_alias_map()

    # Score each candidate by (n_matches, hit-master-family). Higher = better.
    scored: list[tuple[int, int, str]] = []  # (-score, idx_to_stabilize, qid)
    with HF_CANDIDATES.open() as f:
        idx = 0
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            q = r.get("qid")
            if not q or not isinstance(q, str) or not q.startswith("Q"):
                continue
            cand_fams = r.get("candidate_family_ids") or []
            hit = any(aliases.get(c, c) in fams_set for c in cand_fams)
            n_matches = r.get("n_matches", len(r.get("matched_tokens", [])))
            # Confidence score: prioritize hits + match count + fewer ambiguous candidates
            score = (1 if hit else 0) * 100 + n_matches * 10 + max(0, 30 - len(cand_fams))
            scored.append((-score, idx, q))
            idx += 1
    scored.sort()
    todo_order = [q for _, _, q in scored]
    if priority_only:
        # Drop very low-signal (n_matches=1 AND no high score)
        # Already sorted desc; keep top half
        todo_order = todo_order[: max(len(todo_order) // 2, 5000)]
    todo_order = list(dict.fromkeys(todo_order))
    fetched = load_fetched()
    todo = [q for q in todo_order if q not in fetched]
    print(f"[step4] candidates ranked: {len(todo_order):,}  fetched={len(fetched):,}", flush=True)
    print(f"[step4] todo this run: {len(todo):,}  max_batches={max_batches or 'unlimited'}", flush=True)

    n_batches = 0
    n_done = 0
    f_out = PERSONS_WIKIDATA.open("a")
    f_done = PERSONS_FETCHED.open("a")
    try:
        i = 0
        while i < len(todo):
            if max_batches and n_batches >= max_batches:
                break
            batch = todo[i:i + batch_size]
            i += batch_size
            url = ("https://www.wikidata.org/w/api.php?action=wbgetentities"
                   "&format=json&props=labels|claims&languages=en|ko|ja|zh|de|fr|es|ru|ar"
                   "&ids=" + "|".join(batch))
            try:
                r = requests.get(
                    url,
                    headers={"User-Agent": "RoyalsBot/0.2 (kibongkook@gmail.com)"},
                    timeout=30,
                )
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                print(f"[step4] batch {n_batches} error: {e!r}, sleep 3s", flush=True)
                time.sleep(3.0)
                continue
            ents = data.get("entities", {}) or {}
            keep_props = {"P22", "P25", "P26", "P40", "P53", "P569", "P570", "P21", "P27", "P1365", "P1366", "P31"}
            for q in batch:
                ent = ents.get(q)
                if ent is None:
                    continue
                labels = {lang: v.get("value") for lang, v in (ent.get("labels") or {}).items()}
                claims = ent.get("claims") or {}
                slim_claims = {}
                for p, snaks in claims.items():
                    if p not in keep_props:
                        continue
                    slim_claims[p] = []
                    for s in snaks:
                        try:
                            dv = s["mainsnak"]["datavalue"]
                            slim_claims[p].append(dv.get("value"))
                        except (KeyError, TypeError):
                            continue
                f_out.write(json.dumps({"qid": q, "labels": labels, "claims": slim_claims}, ensure_ascii=False) + "\n")
                f_done.write(q + "\n")
                n_done += 1
            f_out.flush()
            f_done.flush()
            n_batches += 1
            if n_batches % 5 == 0:
                print(f"[step4] batches={n_batches} done_this_run={n_done}", flush=True)
            time.sleep(sleep_s)
    finally:
        f_out.close()
        f_done.close()
    print(f"[step4] DONE batches={n_batches} done_this_run={n_done}", flush=True)
    return {"batches": n_batches, "fetched": n_done}


def _wd_date(val):
    if not isinstance(val, dict):
        return None
    t = val.get("time")
    if not t:
        return None
    sign = "-" if t.startswith("-") else ""
    m = re.match(r"^[+-](\d{1,4})(?:-(\d{2})-(\d{2}))?", t)
    if not m:
        return None
    y, mo, d = m.group(1), m.group(2), m.group(3)
    if mo and d and mo != "00" and d != "00":
        return f"{sign}{y}-{mo}-{d}"
    return f"{sign}{y}" if y else None


def _wd_qid(val):
    if isinstance(val, dict):
        return val.get("id")
    return None


def step5():
    """Merge fetched Wikidata claims into persons.jsonl. Append-only & idempotent.

    Loads existing persons.jsonl IDs and skips. Links to family via P53 first,
    then HF candidate_family_ids fallback.
    """
    if not PERSONS_WIKIDATA.exists():
        print("[step5] no _persons_wikidata.jsonl; nothing to do", flush=True)
        return {"emitted": 0}

    print("[step5] loading family index ...", flush=True)
    fams_by_id, token_to_ids = build_family_index()
    aliases = load_alias_map()

    # Already-emitted ids
    seen = set()
    if PERSONS_FINAL.exists():
        with PERSONS_FINAL.open() as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("id"):
                    seen.add(r["id"])
    print(f"[step5] existing persons: {len(seen):,}", flush=True)

    # Candidate token/family map for fallback linking
    cand_tokens: dict[str, list[str]] = {}
    cand_fams: dict[str, list[str]] = {}
    if HF_CANDIDATES.exists():
        with HF_CANDIDATES.open() as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                q = r.get("qid")
                if q and q not in cand_tokens:
                    cand_tokens[q] = r.get("matched_tokens") or []
                    cand_fams[q] = r.get("candidate_family_ids") or []

    n_emit = 0
    n_linked = 0
    by_fam = defaultdict(int)
    with PERSONS_FINAL.open("a") as fout, PERSONS_WIKIDATA.open() as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                ent = json.loads(line)
            except json.JSONDecodeError:
                continue
            qid = ent.get("qid")
            if not qid or qid in seen:
                continue
            labels = ent.get("labels") or {}
            claims = ent.get("claims") or {}

            # Skip non-humans if P31 says so
            inst_of = [_wd_qid(c) for c in claims.get("P31", []) if _wd_qid(c)]
            if inst_of and "Q5" not in inst_of:
                # Not a human — skip
                continue

            # Family linking
            fam_id = None
            for c in claims.get("P53", []):
                fq = _wd_qid(c)
                if fq and fq in fams_by_id:
                    fam_id = fq
                    break
            if not fam_id and cand_fams.get(qid):
                for c in cand_fams[qid]:
                    cc = aliases.get(c, c)
                    if cc in fams_by_id:
                        fam_id = cc
                        break
            if not fam_id and cand_tokens.get(qid):
                en_lbl = (labels.get("en") or "").lower()
                for tok in cand_tokens[qid]:
                    if tok in en_lbl:
                        fids = token_to_ids.get(tok) or []
                        for fid in fids:
                            if fid in fams_by_id:
                                fam_id = fid
                                break
                        if fam_id:
                            break

            birth = next((_wd_date(c) for c in claims.get("P569", []) if _wd_date(c)), None)
            death = next((_wd_date(c) for c in claims.get("P570", []) if _wd_date(c)), None)
            gender = None
            for c in claims.get("P21", []):
                g = _wd_qid(c)
                if g == "Q6581097":
                    gender = "M"
                elif g == "Q6581072":
                    gender = "F"
                elif g:
                    gender = "other"
                break
            father = next((_wd_qid(c) for c in claims.get("P22", []) if _wd_qid(c)), None)
            mother = next((_wd_qid(c) for c in claims.get("P25", []) if _wd_qid(c)), None)
            spouses = [_wd_qid(c) for c in claims.get("P26", []) if _wd_qid(c)]
            children = [_wd_qid(c) for c in claims.get("P40", []) if _wd_qid(c)]
            pred = next((_wd_qid(c) for c in claims.get("P1365", []) if _wd_qid(c)), None)
            succ = next((_wd_qid(c) for c in claims.get("P1366", []) if _wd_qid(c)), None)

            rec = {
                "id": qid,
                "names": labels,
                "family_id": fam_id,
                "family_role": "member",
                "birth": birth,
                "death": death,
                "gender": gender,
                "father_id": father,
                "mother_id": mother,
                "spouse_ids": spouses,
                "child_ids": children,
                "predecessor_id": pred,
                "successor_id": succ,
                "country": [],
                "titles": [],
                "sources": ["wikidata", "huggingface:yale-cultural-heritage/wikidata-people"],
            }
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            seen.add(qid)
            n_emit += 1
            if fam_id:
                n_linked += 1
                by_fam[fam_id] += 1
    print(f"[step5] emitted: {n_emit:,}  linked to family: {n_linked:,}", flush=True)
    return {"emitted": n_emit, "linked": n_linked, "by_fam": dict(by_fam)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=int, required=True, choices=[3, 4, 5])
    ap.add_argument("--max-batches", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=50)
    ap.add_argument("--sleep", type=float, default=0.5)
    ap.add_argument("--all-candidates", action="store_true",
                    help="step4: also fetch low-confidence candidates (no family hit)")
    args = ap.parse_args()

    if args.step == 3:
        step3()
    elif args.step == 4:
        step4(max_batches=args.max_batches, batch_size=args.batch_size,
              sleep_s=args.sleep, priority_only=not args.all_candidates)
    elif args.step == 5:
        step5()


if __name__ == "__main__":
    main()
