#!/usr/bin/env python3
"""
One-shot migration: change all 'royal-tree:' ID prefix → 'royal-tree:' across the
project. Run once after the project rename.

Affects:
  - data/master/*.jsonl, *.tsv, *.json
  - data/master/persons_by_family/*.jsonl (file CONTENTS only;
    we also rename files whose basename starts with 'royals_')
  - data/by_country/*.jsonl
  - data/by_category/*.jsonl
  - data/raw/manual/*.jsonl
  - data/raw/github/_*.jsonl
  - scripts/**/*.py (literal strings inside Python code)
  - scripts/**/*.sh

We use a token-safe replacement of "royal-tree:" (with the colon) — this avoids
hitting other "royals" occurrences (e.g. in prose comments).

Idempotent: running twice is safe (second pass finds no matches).
"""
from __future__ import annotations
import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

OLD = "royal-tree:"
NEW = "royal-tree:"

# Files to scan
GLOB_PATTERNS = [
    "data/master/families.jsonl",
    "data/master/persons.jsonl",
    "data/master/relations.jsonl",
    "data/master/businesses.jsonl",
    "data/master/_alias_map.tsv",
    "data/master/_normalized.jsonl",
    "data/master/_normalized.pre_enrich.jsonl",
    "data/master/_country_enrichment.jsonl",
    "data/master/_hf_candidates.jsonl",
    "data/master/_summary.json",
    "data/master/_persons_summary.json",
    "data/master/_relations_summary.json",
    "data/master/_businesses_summary.json",
    "data/master/_relations_graph.json",
    "data/master/_forbes_unmatched.tsv",
    "data/master/_filtered_non_families.jsonl",
    "data/master/_persons_wikidata.jsonl",
    "data/master/_persons_fetched.txt",
]
DIR_GLOBS = [
    ("data/master/persons_by_family", "*.jsonl"),
    ("data/by_country", "*.jsonl"),
    ("data/by_category", "*.jsonl"),
    ("data/raw/manual", "*.jsonl"),
    ("data/raw/github", "_*.jsonl"),
    ("scripts", "*.py"),
    ("scripts", "*.sh"),
]


def rewrite(path: Path) -> tuple[bool, int]:
    """Replace OLD → NEW in file contents. Returns (changed, occurrences)."""
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return (False, 0)
    if OLD.encode() not in data:
        return (False, 0)
    n = data.count(OLD.encode())
    new_data = data.replace(OLD.encode(), NEW.encode())
    path.write_bytes(new_data)
    return (True, n)


def rename_royals_files(dir_path: Path) -> int:
    """Rename files whose basename starts with 'royals_' → 'royal-tree_'."""
    if not dir_path.exists():
        return 0
    n = 0
    for p in dir_path.iterdir():
        if not p.is_file():
            continue
        if p.name.startswith("royals_"):
            new_name = "royal-tree_" + p.name[len("royals_"):]
            p.rename(p.with_name(new_name))
            n += 1
    return n


def main():
    total_files = 0
    total_occ = 0
    print("=== Rewriting top-level files ===")
    for rel in GLOB_PATTERNS:
        p = ROOT / rel
        ok, n = rewrite(p)
        if ok:
            total_files += 1
            total_occ += n
            print(f"  {n:>7} occ → {rel}")

    print("\n=== Rewriting directory globs ===")
    for dir_rel, pat in DIR_GLOBS:
        dpath = ROOT / dir_rel
        if not dpath.exists():
            continue
        scanned = 0
        rewritten = 0
        occ = 0
        for p in dpath.rglob(pat):
            scanned += 1
            ok, n = rewrite(p)
            if ok:
                rewritten += 1
                occ += n
        if rewritten:
            print(f"  {dir_rel}/{pat}: scanned {scanned}, rewritten {rewritten}, total {occ:,} occurrences")
        total_files += rewritten
        total_occ += occ

    print("\n=== Renaming files with 'royals_' basename ===")
    renamed = 0
    for dir_rel in ["data/master/persons_by_family"]:
        n = rename_royals_files(ROOT / dir_rel)
        if n:
            print(f"  {dir_rel}: renamed {n} files")
        renamed += n

    print(f"\n--- Migration complete ---")
    print(f"  files modified: {total_files:,}")
    print(f"  occurrences replaced: {total_occ:,}")
    print(f"  files renamed: {renamed:,}")


if __name__ == "__main__":
    main()
