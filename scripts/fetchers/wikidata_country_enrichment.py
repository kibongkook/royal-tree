#!/usr/bin/env python3
"""
Wikidata country enrichment for Royal-Tree master file.

Reads:  data/master/families.jsonl
Finds:  every entry with empty country AND a real Wikidata QID
Writes: data/master/_country_enrichment.jsonl  (one record per queried QID)

Strategy per entity:
  Try properties in priority order, taking the first hit:
    1. P17  country
    2. P495 country of origin
    3. P27  country of citizenship
    4. P276 location              -> resolve via P17 of that location
    5. P131 located in admin entity -> recurse until P17 found
    6. P19  place of birth        -> resolve via P17

For the resolved country QID, look up P297 (ISO 3166-1 alpha-2).
Country QIDs are cached -> only ~250 unique countries to resolve.

Output schema:
  {"id":"Q12345","country_inferred":["DE"],"via":["P495"],"source":"wikidata-enrichment-v1"}
Entries with no signal still get a record with empty arrays so we can audit.
"""
from __future__ import annotations
import json, sys, time, os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
try:
    from urllib3.util.retry import Retry
except ImportError:
    from requests.packages.urllib3.util.retry import Retry  # type: ignore

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "data" / "master" / "families.jsonl"
OUT    = ROOT / "data" / "master" / "_country_enrichment.jsonl"
CHECKPOINT = ROOT / "data" / "master" / "_country_enrichment.checkpoint.json"

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "RoyalTree-research/0.2 (kibongkook@gmail.com)"

BATCH_SIZE = 50
MAX_WORKERS = 5
# Order in which we try to infer country from a family entity's claims.
PROPERTY_ORDER = ["P17", "P495", "P27", "P276", "P131", "P19"]
# Properties whose target needs a second lookup to get country.
RESOLVE_VIA_P17 = {"P276", "P131", "P19"}

# Cache shared across threads. dict ops are GIL-protected for simple set/get on str keys.
COUNTRY_ISO_CACHE: dict[str, list[str]] = {}      # country QID -> [ISO codes]
LOCATION_COUNTRY_CACHE: dict[str, list[str]] = {} # location QID -> [country QIDs]


import threading
_SESSION_LOCAL = threading.local()

def _session() -> requests.Session:
    s = getattr(_SESSION_LOCAL, "s", None)
    if s is None:
        s = requests.Session()
        s.headers.update({"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"})
        retry = Retry(total=4, backoff_factor=1.0,
                      status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=frozenset(["GET"]))
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        _SESSION_LOCAL.s = s
    return s

def http_get(params: dict, retries: int = 4) -> dict:
    params = dict(params)
    params.setdefault("format", "json")
    s = _session()
    backoff = 1.0
    last_exc = None
    for attempt in range(retries):
        try:
            resp = s.get(WIKIDATA_API, params=params, timeout=60)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(backoff); backoff *= 2
                continue
            resp.raise_for_status()
        except Exception as e:
            last_exc = e
            if attempt == retries - 1:
                raise
            time.sleep(backoff); backoff *= 2
    if last_exc:
        raise last_exc
    return {}


def extract_qid_targets(claims: dict, prop: str) -> list[str]:
    """Return list of QID strings for a given property from a claims dict."""
    out = []
    for stmt in claims.get(prop, []):
        try:
            mainsnak = stmt.get("mainsnak", {})
            if mainsnak.get("snaktype") != "value":
                continue
            dv = mainsnak.get("datavalue", {})
            val = dv.get("value", {})
            qid = val.get("id")
            if qid and qid.startswith("Q"):
                out.append(qid)
        except Exception:
            continue
    return out


def extract_first_string(claims: dict, prop: str) -> str | None:
    for stmt in claims.get(prop, []):
        try:
            ms = stmt.get("mainsnak", {})
            if ms.get("snaktype") != "value":
                continue
            dv = ms.get("datavalue", {})
            v = dv.get("value")
            if isinstance(v, str):
                return v
        except Exception:
            continue
    return None


def fetch_entities(qids: list[str]) -> dict:
    """Batch wbgetentities for up to 50 QIDs, claims only."""
    params = {
        "action": "wbgetentities",
        "ids": "|".join(qids),
        "props": "claims",
    }
    data = http_get(params)
    return (data or {}).get("entities", {}) or {}


def fetch_country_isos(country_qids: list[str]) -> dict[str, list[str]]:
    """Given a batch of country-QIDs, return mapping QID -> ISO alpha-2 list."""
    out = {}
    todo = [q for q in country_qids if q not in COUNTRY_ISO_CACHE]
    todo = list(set(todo))
    for i in range(0, len(todo), BATCH_SIZE):
        chunk = todo[i:i + BATCH_SIZE]
        try:
            ents = fetch_entities(chunk)
        except Exception:
            ents = {}
        for qid in chunk:
            ent = ents.get(qid) or {}
            claims = ent.get("claims") or {}
            iso = extract_first_string(claims, "P297")
            if iso:
                COUNTRY_ISO_CACHE[qid] = [iso.upper()]
            else:
                # Some "countries" in Wikidata sense have no P297 (e.g. supranational, historical).
                # Try to walk P17 once (rare case where input was actually a region).
                country_targets = extract_qid_targets(claims, "P17")
                if country_targets and country_targets[0] != qid:
                    sub = fetch_country_isos([country_targets[0]])
                    COUNTRY_ISO_CACHE[qid] = sub.get(country_targets[0], [])
                else:
                    COUNTRY_ISO_CACHE[qid] = []
    for q in country_qids:
        out[q] = COUNTRY_ISO_CACHE.get(q, [])
    return out


def fetch_location_country(loc_qids: list[str]) -> dict[str, list[str]]:
    """Given location/admin entities, return their P17 country QIDs (recursing via P131 up to 4 levels)."""
    out = {}
    todo = [q for q in loc_qids if q not in LOCATION_COUNTRY_CACHE]
    todo = list(set(todo))

    # Iterative resolution: walk up P131 chain looking for P17.
    pending = {q: 0 for q in todo}
    MAX_DEPTH = 4

    while pending:
        # Resolve current level
        cur_qids = list(pending.keys())
        resolved_this_round = {}
        for i in range(0, len(cur_qids), BATCH_SIZE):
            chunk = cur_qids[i:i + BATCH_SIZE]
            try:
                ents = fetch_entities(chunk)
            except Exception:
                ents = {}
            for q in chunk:
                ent = ents.get(q) or {}
                claims = ent.get("claims") or {}
                resolved_this_round[q] = claims

        next_pending = {}
        for q, claims in resolved_this_round.items():
            country = extract_qid_targets(claims, "P17")
            if country:
                LOCATION_COUNTRY_CACHE[q] = country
                continue
            depth = pending[q]
            if depth >= MAX_DEPTH:
                LOCATION_COUNTRY_CACHE[q] = []
                continue
            parents = extract_qid_targets(claims, "P131")
            if not parents:
                LOCATION_COUNTRY_CACHE[q] = []
                continue
            parent = parents[0]
            if parent in LOCATION_COUNTRY_CACHE:
                LOCATION_COUNTRY_CACHE[q] = LOCATION_COUNTRY_CACHE[parent]
                continue
            # Recurse: mark this q's answer as parent's eventual answer.
            # We'll process parent in the next round, then re-emit q.
            next_pending[parent] = depth + 1
            # Also keep q so we can copy parent's answer afterwards.
            # We track parent linkage via a side dict.
            _parent_link.setdefault(parent, set()).add(q)
        pending = {k: v for k, v in next_pending.items() if k not in LOCATION_COUNTRY_CACHE}

    # Backfill via parent links
    changed = True
    while changed:
        changed = False
        for parent, kids in list(_parent_link.items()):
            if parent in LOCATION_COUNTRY_CACHE:
                ans = LOCATION_COUNTRY_CACHE[parent]
                for k in kids:
                    if k not in LOCATION_COUNTRY_CACHE:
                        LOCATION_COUNTRY_CACHE[k] = ans
                        changed = True
                del _parent_link[parent]

    for q in loc_qids:
        out[q] = LOCATION_COUNTRY_CACHE.get(q, [])
    return out


_parent_link: dict[str, set] = {}


def infer_country_from_claims(claims: dict) -> tuple[list[str], list[str], list[str]]:
    """Return (country_qids, via_props, location_qids_to_resolve)."""
    for prop in PROPERTY_ORDER:
        targets = extract_qid_targets(claims, prop)
        if not targets:
            continue
        if prop in RESOLVE_VIA_P17:
            # Defer location->country resolution
            return ([], [prop], targets)
        return (targets, [prop], [])
    return ([], [], [])


def process_batch(qids: list[str]) -> list[dict]:
    """Process one batch of QIDs -> list of enrichment records (one per input QID)."""
    try:
        ents = fetch_entities(qids)
    except Exception as e:
        # On total batch failure, return empty signals for these
        return [{"id": q, "country_inferred": [], "via": [], "source": "wikidata-enrichment-v1",
                 "error": f"fetch_failed:{e.__class__.__name__}"} for q in qids]

    # First pass: collect direct country hits and queue location resolutions
    results: list[dict] = []
    pending_loc: dict[str, list[str]] = {}  # qid -> [location qids]
    pending_via: dict[str, list[str]] = {}  # qid -> [prop]

    for qid in qids:
        ent = ents.get(qid) or {}
        if not ent or "missing" in ent:
            results.append({"id": qid, "country_inferred": [], "via": [],
                            "source": "wikidata-enrichment-v1", "note": "missing"})
            continue
        claims = ent.get("claims") or {}
        country_qids, via, locs = infer_country_from_claims(claims)
        if country_qids:
            # Need ISO codes
            results.append({"id": qid, "_country_qids": country_qids, "via": via})
        elif locs:
            pending_loc[qid] = locs
            pending_via[qid] = via
            results.append({"id": qid, "_pending": True})
        else:
            results.append({"id": qid, "country_inferred": [], "via": [],
                            "source": "wikidata-enrichment-v1"})

    # Resolve locations -> countries
    if pending_loc:
        all_locs = []
        for v in pending_loc.values():
            all_locs.extend(v)
        loc_to_country = fetch_location_country(list(set(all_locs)))
        for i, rec in enumerate(results):
            if not rec.get("_pending"):
                continue
            qid = rec["id"]
            locs = pending_loc.get(qid, [])
            cqids = []
            for l in locs:
                cqids.extend(loc_to_country.get(l, []))
            results[i] = {"id": qid, "_country_qids": list(dict.fromkeys(cqids)),
                          "via": pending_via.get(qid, [])}

    # Resolve country QIDs -> ISO
    all_country_qids = []
    for rec in results:
        all_country_qids.extend(rec.get("_country_qids", []) or [])
    if all_country_qids:
        fetch_country_isos(list(set(all_country_qids)))

    # Finalize
    final: list[dict] = []
    for rec in results:
        if "_country_qids" in rec:
            isos = []
            for cq in rec["_country_qids"]:
                isos.extend(COUNTRY_ISO_CACHE.get(cq, []))
            isos = sorted(set(isos))
            via = rec.get("via", [])
            final.append({
                "id": rec["id"],
                "country_inferred": isos,
                "via": via if isos else [],
                "source": "wikidata-enrichment-v1",
            })
        else:
            final.append({k: v for k, v in rec.items() if not k.startswith("_")})
    return final


def load_candidates() -> list[str]:
    qids: list[str] = []
    with MASTER.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("country"):
                continue
            rid = r.get("id", "")
            if rid.startswith("Q") and rid[1:].isdigit():
                qids.append(rid)
    return qids


def load_done_ids() -> set[str]:
    done = set()
    if OUT.exists():
        with OUT.open(encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    if r.get("id"):
                        done.add(r["id"])
                except json.JSONDecodeError:
                    continue
    return done


def chunked(seq: list, n: int):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]


def main():
    qids = load_candidates()
    print(f"Found {len(qids):,} candidate QIDs (empty country, QID id).")

    done = load_done_ids()
    if done:
        print(f"  resume: {len(done):,} already in {OUT.name}")
    todo = [q for q in qids if q not in done]
    print(f"  to fetch: {len(todo):,}")

    if not todo:
        print("Nothing to do.")
        return

    batches = list(chunked(todo, BATCH_SIZE))
    print(f"  batches: {len(batches)} (size {BATCH_SIZE}, workers {MAX_WORKERS})")

    mode = "a" if OUT.exists() else "w"
    fout = OUT.open(mode, encoding="utf-8")
    n_done = 0
    n_hit = 0
    n_miss = 0
    via_counter: dict[str, int] = {}
    iso_counter: dict[str, int] = {}
    t0 = time.time()

    def write_records(recs: list[dict]):
        nonlocal n_hit, n_miss
        for r in recs:
            fout.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
            if r.get("country_inferred"):
                n_hit += 1
                for v in r.get("via", []):
                    via_counter[v] = via_counter.get(v, 0) + 1
                for iso in r["country_inferred"]:
                    iso_counter[iso] = iso_counter.get(iso, 0) + 1
            else:
                n_miss += 1

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        # Submit a small rolling window to bound memory
        futures = {}
        batch_iter = iter(batches)
        # Prime
        for _ in range(MAX_WORKERS * 2):
            try:
                b = next(batch_iter)
            except StopIteration:
                break
            futures[ex.submit(process_batch, b)] = b

        while futures:
            for fut in as_completed(list(futures.keys()), timeout=None):
                b = futures.pop(fut)
                try:
                    recs = fut.result()
                except Exception as e:
                    recs = [{"id": q, "country_inferred": [], "via": [],
                             "source": "wikidata-enrichment-v1",
                             "error": f"batch_exc:{e.__class__.__name__}"} for q in b]
                write_records(recs)
                n_done += len(b)
                # progress
                if n_done % (BATCH_SIZE * 20) < BATCH_SIZE:
                    dt = time.time() - t0
                    rate = n_done / dt if dt > 0 else 0
                    eta = (len(todo) - n_done) / rate if rate > 0 else 0
                    print(f"  [{n_done:>6,}/{len(todo):,}] hits={n_hit:,} misses={n_miss:,} "
                          f"rate={rate:.0f}/s eta={eta:.0f}s "
                          f"cache(iso={len(COUNTRY_ISO_CACHE)},loc={len(LOCATION_COUNTRY_CACHE)})")
                    fout.flush()
                # refill
                try:
                    nb = next(batch_iter)
                    futures[ex.submit(process_batch, nb)] = nb
                except StopIteration:
                    pass
                # break out of as_completed to refresh keys
                break

    fout.close()
    dt = time.time() - t0
    print(f"\nDone in {dt:.1f}s.")
    print(f"  queried: {n_done:,}")
    print(f"  with country: {n_hit:,}  ({n_hit/max(n_done,1)*100:.1f}%)")
    print(f"  no signal:   {n_miss:,}")
    print(f"\n  by property:")
    for p, n in sorted(via_counter.items(), key=lambda x: -x[1]):
        print(f"    {p}: {n:,}")
    print(f"\n  top 15 inferred ISO codes:")
    for iso, n in sorted(iso_counter.items(), key=lambda x: -x[1])[:15]:
        print(f"    {iso}: {n:,}")


if __name__ == "__main__":
    main()
