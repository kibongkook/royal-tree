#!/usr/bin/env bash
# github_search.sh — discover GitHub repos with royalty/dynasty/genealogy data.
#
# Strategy:
#   1) GitHub repo search across 40 targeted natural-language queries.
#   2) GitHub code search across known filename patterns (royals.json,
#      monarchs.csv, dynasties.json, kings.json, billionaires.csv, etc.)
#   3) Merge by full_name, dedupe, rank by stars + match strength.
#
# Outputs (all under /tmp/royals_search/):
#   q_*.json        — original repo-search responses
#   s_*.json        — second-pass repo-search responses
#   code_*.json     — code-search responses keyed by filename
#   codex_*.json    — code-search responses for content patterns
#   all_repos.json  — deduped repo objects with stars>=5
#   candidates.json — repos passing the relevance filter
#   master_candidates.json — union of repo + code-search hits
#   shortlist.json  — final human-curated list (input to github_clone.sh)
#
# Auth:
#   Requires `gh auth login` for the 5000/hr core API and 30/min search API.
#   Sequential calls with ~2.2s sleep to stay under search rate.
#
# Usage:
#   bash scripts/fetchers/github_search.sh
#
# This is the canonical replay of the scout pass on 2026-05-23.

set -u
WORKDIR="${WORKDIR:-/tmp/royals_search}"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

REPO_QUERIES=(
  "royal family"
  "dynasty data"
  "monarchy"
  "nobility"
  "genealogy"
  "gedcom"
  "royal lineage"
  "royal houses"
  "monarch list"
  "monarchs"
  "dynasties"
  "peerage"
  "billionaires"
  "wealthy families"
  "world leaders"
  "heads of state"
  "presidents list"
  "ck3 mod dynasty"
  "tudor stuart"
  "korean clan"
  "chinese clan"
  "samurai clan"
  "mughal dynasty"
  "ottoman sultans"
  "popes list"
  "house of windsor"
  "house of saud"
  "japan imperial"
  "qing dynasty"
  "russian tsars"
  "byzantine emperors"
  "egyptian pharaohs"
  "scottish clans"
  "aristocratic families"
  "elite families"
  "old world dynasties"
  "rulers dataset"
)

echo "[github_search] running ${#REPO_QUERIES[@]} repo queries"
for i in "${!REPO_QUERIES[@]}"; do
  q="${REPO_QUERIES[$i]}"
  enc=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$q")
  fn="s_$(printf %02d $i).json"
  gh api "search/repositories?q=${enc}&sort=stars&order=desc&per_page=100" >"$fn" 2>/dev/null
  echo "  $i: $q -> $(python3 -c "import json; d=json.load(open('$fn')); print(d.get('total_count','ERR'))" 2>/dev/null)"
  sleep 2.2
done

CODE_FILES=(
  "royals.json"
  "dynasties.json"
  "monarchs.csv"
  "noble_families.json"
  "peerage.csv"
  "billionaires.csv"
  "rulers.json"
  "kings.json"
)

echo "[github_search] code-searching filenames"
for filename in "${CODE_FILES[@]}"; do
  enc=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "filename:$filename")
  gh api "search/code?q=${enc}&per_page=50" >"code_${filename}.json" 2>/dev/null
  echo "  $filename: $(python3 -c "import json; d=json.load(open('code_${filename}.json')); print(d.get('total_count','ERR'))" 2>/dev/null)"
  sleep 2.5
done

echo "[github_search] complete. raw JSON in $WORKDIR"
echo "                 see scripts/audit/build_catalog.py to merge + catalog."
