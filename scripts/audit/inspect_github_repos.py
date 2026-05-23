#!/usr/bin/env python3
"""inspect_github_repos.py

Walk every cloned repo in data/raw/github/, identify data files that look
relevant to royalty/dynasty/genealogy, and emit data/raw/github/catalog.jsonl
plus a per-repo NOTES.md summary table.

Heuristics for "relevant data file":
  - extension in {.csv, .tsv, .json, .jsonl, .ndjson, .gedcom, .ged}
  - filename or parent path matches keywords (royal, monarch, king, queen,
    dynasty, dynasti, noble, peer, billion, ruler, emperor, sultan,
    tsar, shogun, clan, genealog, lineage, ancestor, head_of_state,
    president, peerage, aristocrat, papal, pope, sotu, ...)
  - excludes obvious sports/anime/franchise false-positives in path

Outputs:
  data/raw/github/catalog.jsonl  (one line per repo)
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GH = ROOT / "data" / "raw" / "github"
OUT = GH / "catalog.jsonl"

DATA_EXTS = {".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".gedcom", ".ged", ".txt"}
RELEVANT_KW = [
    "royal", "monarch", "king", "queen", "dynast", "noble", "peer",
    "billion", "rich_list", "rich-list", "ruler", "emperor", "tsar",
    "sultan", "shogun", "samurai", "clan", "genealog", "lineage",
    "ancestor", "ancestr", "head_of_state", "head-of-state",
    "president", "aristocrat", "papal", "pope", "sotu", "speech",
    "succession", "house_of", "house-of", "windsor", "tudor", "stuart",
    "habsburg", "ottoman", "mughal", "qing", "ming", "song", "tang",
    "samurai", "shogun", "byzant", "pharao", "polit", "polity",
    "danish_monarch", "uk_monarch", "english_monarch", "kassite",
    "elite", "wealth", "forbes",
]
EXCLUDE_KW = [
    "ipl", "mlb", "ncaa", "nfl", "espn", "cricket", "baseball",
    "basket", "soccer", "rugby", "fantasy", "yu-gi", "anime",
    "manga", "fortnite", "minecraft", "balatro", "battletech",
    "balatro", "kc-royals", "kansas-city", "rajasthan-", "paarl-",
    "mumbai-", "joburg-", "duel", "wnba", "frozen-potato",
    "currency", "anm-db", "lego", "barbie", "lorde",
]
# Per-repo target keywords — when the entire repo is on-topic, accept all data files
ALL_DATA_REPOS = {
    "dynasty", "RomanEmperorsScraper", "royalconstellations",
    "islamic-civilization-atlas", "monarchs", "Book_of_the_Dead_Sources",
    "iran-constitutional-monarchy", "Song-Dynasty-Paintings-Database",
    "ctm_bench", "Forbes400", "rtb", "billionaires-scraper",
    "datasets-sotu", "discursos-de-navidad", "CorporateGenealogy",
    "public-gedcoms", "ancestory", "SrilankanMonarchsSE",
    "TimelineHistory", "EmbedNewConcept-20260305",
}


def relevant_path(rel_path: str, repo_name: str) -> bool:
    rp = rel_path.lower()
    if any(x in rp for x in EXCLUDE_KW):
        return False
    if repo_name in ALL_DATA_REPOS:
        return True
    return any(kw in rp for kw in RELEVANT_KW)


def estimate_rows(p: Path, ext: str) -> int:
    try:
        if ext in {".csv", ".tsv", ".jsonl", ".ndjson"}:
            n = 0
            with p.open("r", encoding="utf-8", errors="ignore") as f:
                for _ in f:
                    n += 1
            return max(0, n - 1) if ext in {".csv", ".tsv"} else n
        elif ext == ".json":
            txt = p.read_text(encoding="utf-8", errors="ignore")
            if len(txt) > 4_000_000:
                # too big to parse — approximate by counting brackets
                return txt.count('{"') + txt.count('": [')
            data = json.loads(txt)
            if isinstance(data, list):
                return len(data)
            elif isinstance(data, dict):
                # try common patterns
                for k in ("items", "data", "rows", "records", "results"):
                    if k in data and isinstance(data[k], list):
                        return len(data[k])
                return len(data)
        elif ext in {".gedcom", ".ged"}:
            with p.open("r", encoding="utf-8", errors="ignore") as f:
                return sum(1 for ln in f if ln.startswith("0 @"))
    except Exception:
        pass
    return 0


def main():
    out_lines = []
    total_repos = 0
    total_data_files = 0
    total_rows = 0

    for repo_dir in sorted(GH.iterdir()):
        if not repo_dir.is_dir() or repo_dir.name.startswith("."):
            continue
        # Skip non-repo files like catalog.jsonl
        if not (repo_dir / ".git").exists():
            continue
        total_repos += 1
        name = repo_dir.name

        data_files = []
        for path in repo_dir.rglob("*"):
            if not path.is_file():
                continue
            if ".git/" in str(path):
                continue
            ext = path.suffix.lower()
            if ext not in DATA_EXTS:
                continue
            rel = str(path.relative_to(repo_dir))
            if not relevant_path(rel, name):
                continue
            size = path.stat().st_size
            # skip empty or huge (>40MB)
            if size == 0 or size > 40_000_000:
                continue
            rows = estimate_rows(path, ext)
            data_files.append({
                "path": rel,
                "size_bytes": size,
                "rows_est": rows,
            })

        # sort by rows desc, then size
        data_files.sort(key=lambda d: (-d["rows_est"], -d["size_bytes"]))

        # Quick license detection
        license_name = None
        for cand in ("LICENSE", "LICENSE.md", "LICENSE.txt", "license", "COPYING"):
            p = repo_dir / cand
            if p.exists():
                txt = p.read_text(encoding="utf-8", errors="ignore")[:1500].lower()
                for tag, key in [
                    ("MIT", "mit license"),
                    ("Apache-2.0", "apache license"),
                    ("BSD-3-Clause", "bsd 3-clause"),
                    ("BSD-2-Clause", "bsd 2-clause"),
                    ("BSD", "bsd license"),
                    ("GPL-3.0", "gnu general public license"),
                    ("CC-BY", "creative commons attribution"),
                    ("CC0", "cc0"),
                    ("Unlicense", "this is free and unencumbered"),
                    ("ISC", "isc license"),
                    ("MPL-2.0", "mozilla public license"),
                ]:
                    if key in txt:
                        license_name = tag
                        break
                if license_name:
                    break
                license_name = "Custom"

        row_count_estimate = sum(d["rows_est"] for d in data_files)
        total_data_files += len(data_files)
        total_rows += row_count_estimate

        record = {
            "repo": name,
            "url": f"https://github.com/<see master_candidates.json>/{name}",
            "cloned": True,
            "path": f"data/raw/github/{name}",
            "data_files": [d["path"] for d in data_files[:25]],
            "data_files_full": data_files[:50],
            "row_count_estimate": row_count_estimate,
            "license": license_name,
        }
        out_lines.append(record)

    # Match URLs from master_candidates.json
    try:
        master = json.load(open("/tmp/royals_search/master_candidates.json"))
        url_by_name = {r["full_name"].split("/")[-1]: r["full_name"] for r in master}
        url_full_by_name = {r["full_name"].split("/")[-1]: r["url"] for r in master}
        stars_by_name = {r["full_name"].split("/")[-1]: r.get("stars", 0) for r in master}
        desc_by_name = {r["full_name"].split("/")[-1]: r.get("description") for r in master}
    except Exception:
        url_by_name = {}
        url_full_by_name = {}
        stars_by_name = {}
        desc_by_name = {}

    for rec in out_lines:
        n = rec["repo"]
        if n in url_full_by_name:
            rec["url"] = url_full_by_name[n]
            rec["full_name"] = url_by_name[n]
            rec["stars"] = stars_by_name[n]
            rec["description"] = (desc_by_name[n] or "")[:240]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for rec in out_lines:
            # Trim out the verbose full file list for the JSONL
            line = {
                "repo": rec.get("full_name", rec["repo"]),
                "stars": rec.get("stars", 0),
                "url": rec.get("url"),
                "cloned": True,
                "path": rec["path"],
                "data_files": rec["data_files"],
                "row_count_estimate": rec["row_count_estimate"],
                "license": rec["license"],
                "description": rec.get("description", ""),
                "data_files_count": len(rec.get("data_files_full", [])),
            }
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    print(f"[catalog] repos catalogued: {total_repos}")
    print(f"[catalog] total relevant data files: {total_data_files}")
    print(f"[catalog] approx total rows: {total_rows:,}")
    print(f"[catalog] saved -> {OUT}")

    # Also: a concise summary table to stdout
    print("\nREPO                                  STARS  FILES  ROWS_EST  LIC        TOP_FILE")
    for rec in sorted(out_lines, key=lambda r: -r["row_count_estimate"]):
        top_file = rec["data_files"][0] if rec["data_files"] else "-"
        print(f"  {rec['repo'][:36]:<36}  {rec.get('stars',0):>5}  {len(rec.get('data_files_full',[])):>5}  {rec['row_count_estimate']:>8}  {(rec['license'] or '-'):<9}  {top_file[:55]}")


if __name__ == "__main__":
    main()
