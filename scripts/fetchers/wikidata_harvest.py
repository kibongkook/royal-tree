#!/usr/bin/env python3
"""
Wikidata harvest for Royal-Tree project.

Pulls every family / dynasty / noble house / clan-like entity from Wikidata's
SPARQL endpoint into data/raw/wikidata/families.jsonl.

Strategy:
  * Small classes (<10k rows): single direct-P31 (or +subc) query.
  * Q8436 noble family (+subc, ~44k rows): chunk by country (P17),
    then a separate "no country" query for items lacking P17.
  * Each SPARQL call has User-Agent + retries; we run up to 5 in parallel.
  * Output is appended JSONL; final pass dedups by QID.

Run: python3 scripts/fetchers/wikidata_harvest.py
"""

from __future__ import annotations

import concurrent.futures as futures
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001
    SSL_CTX = ssl.create_default_context()

ROOT = Path("/Users/sidewalkai2/Claude/royal-tree")
OUT_PATH = ROOT / "data/raw/wikidata/families.jsonl"
LOG_PATH = ROOT / "data/raw/wikidata/_harvest.log"
ENDPOINT = "https://query.wikidata.org/sparql"
UA = "RoyalTree-research/0.1 (kibongkook@gmail.com)"
TIMEOUT_S = 75
MAX_PARALLEL = 5

# ----------------------------------------------------------------------------
# Class roster: (qid, label, mode) — mode is 'direct' (wdt:P31) or 'subc' (P279*)
# ----------------------------------------------------------------------------
CLASSES: list[tuple[str, str, str]] = [
    # Big one — handled separately via country chunking
    # ("Q8436",     "noble family",        "subc"),
    ("Q4438121",  "royal family",        "direct"),
    ("Q7210356",  "political family",    "direct"),
    ("Q188784",   "royal house",         "subc"),
    ("Q1156073",  "royal house (alt)",   "direct"),
    ("Q499247",   "Scottish clan",       "direct"),
    ("Q846706",   "bon-gwan (Korean)",   "direct"),
    ("Q2575910",  "uji (Japanese)",      "direct"),
    ("Q2503193",  "Japanese clans",      "subc"),
    ("Q6071413",  "Irish clan",          "direct"),
    ("Q3918404",  "Pashtun tribe",       "subc"),
    ("Q133311",   "tribe (human)",       "direct"),
    ("Q938560",   "tribus (Roman)",      "direct"),
    ("Q24074280", "noble family name",   "direct"),
    ("Q56488093", "Jewish family",       "direct"),
    ("Q1332544",  "gotra (Hindu clan)",  "direct"),
    ("Q840178",   "Chinese kin",         "direct"),
    ("Q207320",   "ruling dynasty",      "direct"),
]

LANGS = ("en", "ko", "ja", "zh", "de", "fr", "es", "it", "ru", "ar")

# ----------------------------------------------------------------------------
def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sparql_call(query: str, attempts: int = 4) -> dict | None:
    """POST the SPARQL query; return parsed JSON or None on failure."""
    data = urllib.parse.urlencode({"query": query}).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": UA,
        },
    )
    last_err = None
    for i in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=SSL_CTX) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(3 * (i + 1))
    log(f"  SPARQL failed: {last_err}")
    return None


# ----------------------------------------------------------------------------
# Query templates
# ----------------------------------------------------------------------------
def _label_optionals() -> str:
    return "\n  ".join(
        f'OPTIONAL {{ ?item rdfs:label ?label_{lg} FILTER(lang(?label_{lg}) = "{lg}") }}'
        for lg in LANGS
    )


def q_class(qid: str, mode: str) -> str:
    """Query for a small class (no country chunking)."""
    inst = "?item wdt:P31 wd:{q} ." if mode == "direct" else "?item wdt:P31/wdt:P279* wd:{q} ."
    inst = inst.format(q=qid)
    return f"""SELECT ?item ?itemLabel ?countryQid ?inception ?dissolved
       {' '.join(f'?label_{lg}' for lg in LANGS)}
WHERE {{
  {inst}
  OPTIONAL {{ ?item wdt:P17 ?countryQid }}
  OPTIONAL {{ ?item wdt:P571 ?inception }}
  OPTIONAL {{ ?item wdt:P576 ?dissolved }}
  {_label_optionals()}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}"""


def q_q8436_country(country_qid: str) -> str:
    return f"""SELECT ?item ?itemLabel ?countryQid ?inception ?dissolved
       {' '.join(f'?label_{lg}' for lg in LANGS)}
WHERE {{
  ?item wdt:P31/wdt:P279* wd:Q8436 .
  ?item wdt:P17 wd:{country_qid} .
  BIND(wd:{country_qid} AS ?countryQid)
  OPTIONAL {{ ?item wdt:P571 ?inception }}
  OPTIONAL {{ ?item wdt:P576 ?dissolved }}
  {_label_optionals()}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}"""


def q_q8436_no_country() -> str:
    return f"""SELECT ?item ?itemLabel ?countryQid ?inception ?dissolved
       {' '.join(f'?label_{lg}' for lg in LANGS)}
WHERE {{
  ?item wdt:P31/wdt:P279* wd:Q8436 .
  FILTER NOT EXISTS {{ ?item wdt:P17 ?anyCountry }}
  OPTIONAL {{ ?item wdt:P571 ?inception }}
  OPTIONAL {{ ?item wdt:P576 ?dissolved }}
  {_label_optionals()}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}"""


def q_q8436_country_list() -> str:
    return """SELECT ?country (COUNT(DISTINCT ?item) AS ?c) WHERE {
  ?item wdt:P31/wdt:P279* wd:Q8436 .
  ?item wdt:P17 ?country .
} GROUP BY ?country ORDER BY DESC(?c)"""


def q_iso_map() -> str:
    return "SELECT ?country ?iso WHERE { ?country wdt:P297 ?iso }"


# ----------------------------------------------------------------------------
# Result -> JSONL row
# ----------------------------------------------------------------------------
QID_RE = re.compile(r"Q\d+$")


def qid_of(uri: str) -> str | None:
    if not uri:
        return None
    m = QID_RE.search(uri)
    return m.group(0) if m else None


def row_to_record(row: dict, instance_of: str, iso_map: dict[str, str]) -> dict | None:
    qid = qid_of(row.get("item", {}).get("value", ""))
    if not qid:
        return None
    aliases = {}
    for lg in LANGS:
        v = row.get(f"label_{lg}", {}).get("value")
        if v:
            aliases[lg] = v
    name_en = aliases.get("en") or row.get("itemLabel", {}).get("value") or qid
    country_qid = qid_of(row.get("countryQid", {}).get("value", "")) if row.get("countryQid") else None
    country = []
    if country_qid:
        iso = iso_map.get(country_qid)
        country.append(iso or country_qid)
    inception = row.get("inception", {}).get("value")
    dissolved = row.get("dissolved", {}).get("value")
    return {
        "id": qid,
        "name_en": name_en,
        "aliases": aliases,
        "country": country,
        "instance_of": [instance_of],
        "inception": inception,
        "dissolved": dissolved,
        "source": "wikidata",
    }


# ----------------------------------------------------------------------------
def write_rows(records: list[dict]) -> int:
    if not records:
        return 0
    with open(OUT_PATH, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(records)


def harvest_one(name: str, query: str, instance_of: str, iso_map: dict[str, str]) -> tuple[str, int, str]:
    res = sparql_call(query)
    if res is None:
        return (name, 0, "TIMEOUT")
    bindings = res.get("results", {}).get("bindings", [])
    records = []
    for b in bindings:
        rec = row_to_record(b, instance_of, iso_map)
        if rec:
            records.append(rec)
    n = write_rows(records)
    return (name, n, "OK")


# ----------------------------------------------------------------------------
def build_iso_map() -> dict[str, str]:
    log("Fetching ISO 3166-1 alpha-2 lookup...")
    res = sparql_call(q_iso_map())
    out: dict[str, str] = {}
    if not res:
        return out
    for b in res.get("results", {}).get("bindings", []):
        q = qid_of(b["country"]["value"])
        iso = b.get("iso", {}).get("value")
        if q and iso:
            out[q] = iso
    log(f"  ISO map: {len(out)} entries")
    return out


def fetch_q8436_country_list() -> list[tuple[str, int]]:
    log("Fetching Q8436 country distribution...")
    res = sparql_call(q_q8436_country_list())
    if not res:
        return []
    out: list[tuple[str, int]] = []
    for b in res.get("results", {}).get("bindings", []):
        q = qid_of(b["country"]["value"])
        c = int(b["c"]["value"])
        if q:
            out.append((q, c))
    log(f"  Q8436 spans {len(out)} countries")
    return out


# ----------------------------------------------------------------------------
def main() -> int:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    # fresh start
    if OUT_PATH.exists():
        OUT_PATH.unlink()
    if LOG_PATH.exists():
        LOG_PATH.unlink()

    iso_map = build_iso_map()

    # Phase 1: small classes
    log("\n=== Phase 1: small classes ===")
    tasks: list[tuple[str, str, str]] = []  # (name, query, instance_of)
    for qid, label, mode in CLASSES:
        tasks.append((f"{qid} {label}", q_class(qid, mode), qid))

    timeouts: list[str] = []
    totals: dict[str, int] = {}

    with futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL) as ex:
        future_map = {ex.submit(harvest_one, n, q, io_, iso_map): n for (n, q, io_) in tasks}
        for fut in futures.as_completed(future_map):
            name, n, status = fut.result()
            log(f"  {name:<40} {n:>6} rows  [{status}]")
            totals[name] = n
            if status == "TIMEOUT":
                timeouts.append(name)

    # Phase 2: Q8436 noble family — chunked by country
    log("\n=== Phase 2: Q8436 noble family by country ===")
    country_list = fetch_q8436_country_list()

    chunk_tasks: list[tuple[str, str, str]] = []
    big_countries: list[tuple[str, int]] = []
    for cq, n in country_list:
        # if any chunk has > 9500 rows the SPARQL would still complete but slow;
        # noted but not split further here (Wikidata seldom has >10k per country
        # for noble families; max known is Germany ~9k)
        if n > 9500:
            big_countries.append((cq, n))
        chunk_tasks.append((f"Q8436 @ {cq} ({n})", q_q8436_country(cq), "Q8436"))

    # plus the no-country tail
    chunk_tasks.append(("Q8436 @ NO_COUNTRY", q_q8436_no_country(), "Q8436"))

    log(f"  {len(chunk_tasks)} country chunks to run (potential big: {len(big_countries)})")

    with futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL) as ex:
        future_map = {ex.submit(harvest_one, n, q, io_, iso_map): n for (n, q, io_) in chunk_tasks}
        for fut in futures.as_completed(future_map):
            name, n, status = fut.result()
            if status != "OK" or n > 0:
                log(f"  {name:<40} {n:>6} rows  [{status}]")
            totals[name] = n
            if status == "TIMEOUT":
                timeouts.append(name)

    # ---- Dedup pass ----
    log("\n=== Phase 3: dedup pass ===")
    seen: dict[str, dict] = {}
    classes_for: dict[str, set] = {}
    countries_for: dict[str, set] = {}
    with open(OUT_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            qid = r["id"]
            if qid not in seen:
                seen[qid] = r
                classes_for[qid] = set(r.get("instance_of") or [])
                countries_for[qid] = set(r.get("country") or [])
            else:
                # merge aliases / instance_of / country
                base = seen[qid]
                for lg, v in (r.get("aliases") or {}).items():
                    base["aliases"].setdefault(lg, v)
                classes_for[qid].update(r.get("instance_of") or [])
                countries_for[qid].update(r.get("country") or [])
                # earliest inception / latest dissolved
                if not base.get("inception") and r.get("inception"):
                    base["inception"] = r["inception"]
                if not base.get("dissolved") and r.get("dissolved"):
                    base["dissolved"] = r["dissolved"]

    log(f"  unique QIDs: {len(seen)}")

    # rewrite deduped
    OUT_PATH.write_text("", encoding="utf-8")
    with open(OUT_PATH, "a", encoding="utf-8") as f:
        for qid, base in seen.items():
            base["instance_of"] = sorted(classes_for[qid])
            base["country"] = sorted(countries_for[qid])
            f.write(json.dumps(base, ensure_ascii=False) + "\n")

    # ---- Summary stats ----
    log("\n=== Summary ===")
    by_class: dict[str, int] = {}
    by_country: dict[str, int] = {}
    for qid, base in seen.items():
        for c in base["instance_of"]:
            by_class[c] = by_class.get(c, 0) + 1
        for c in base["country"]:
            by_country[c] = by_country.get(c, 0) + 1

    log(f"Total unique QIDs:  {len(seen)}")
    log("By instance_of:")
    for k, v in sorted(by_class.items(), key=lambda x: -x[1]):
        log(f"  {k:<12} {v}")
    log("Top 20 countries:")
    for k, v in sorted(by_country.items(), key=lambda x: -x[1])[:20]:
        log(f"  {k:<12} {v}")
    if timeouts:
        log("\nTIMEOUTS / failed queries:")
        for t in timeouts:
            log(f"  {t}")
    if big_countries:
        log("\nBig country chunks (>9.5k, may have hit endpoint cap):")
        for cq, n in big_countries:
            log(f"  {cq:<12} {n}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
