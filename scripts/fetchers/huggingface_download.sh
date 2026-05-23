#!/usr/bin/env bash
# Hugging Face dataset fetcher for the Royal-Tree project.
#
# Discovers and downloads genealogy / royalty / nobility / world-leader datasets
# from Hugging Face into data/raw/huggingface/<dataset-name>/ and writes a
# JSONL catalog at data/raw/huggingface/catalog.jsonl.
#
# Usage:
#   scripts/fetchers/huggingface_download.sh
#
# Requirements:
#   - python3, pip3 (auto-installs huggingface_hub if missing)
#   - curl, jq
#
# Notes:
#   - Skips datasets > MAX_SIZE_MB (default 2048) — those are flagged in the catalog
#     with `"downloaded": false, "reason": "size-skip"`.
#   - Skips gated datasets (require login/agreement) — flagged as `gated-skip`.
#   - Parallelism: downloads run with xargs -P 4.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RAW_DIR="$ROOT/data/raw/huggingface"
CATALOG="$RAW_DIR/catalog.jsonl"
mkdir -p "$RAW_DIR"

MAX_SIZE_MB="${MAX_SIZE_MB:-2048}"
PARALLEL="${PARALLEL:-4}"

# Ensure `hf` CLI (huggingface_hub >= 0.24) is on PATH.
# Old `huggingface-cli` is deprecated.
export PATH="$HOME/Library/Python/3.14/bin:$HOME/.local/bin:$PATH"
if ! command -v hf >/dev/null 2>&1; then
  pip3 install --user huggingface_hub >/dev/null 2>&1 || true
fi
HF_BIN="$(command -v hf || command -v huggingface-cli)"

# Curated list of relevant datasets discovered via HF search API across queries:
# royal, royalty, monarchy, dynasty, nobility, noble, genealogy, family-tree,
# historical-figures, kings, queens, peerage, wikidata-people, world-leaders,
# aristocracy, clan, lineage, pedigree, gedcom, samurai, daimyo, pharaoh,
# caliphate, tsar, emperor, joseon, mughal, habsburg, bourbon, ottoman, popes,
# saints, warlord, prime-minister, wikipedia-people, biography, etc.
DATASETS=(
  # --- Wikidata structured people data (top priority) ---
  "yale-cultural-heritage/wikidata-people"          # 225k people, train/test parquet, ~60MB
  "willpowers/Wikidata-celebrity-parent"            # celebrity parent relations, 180KB TSV
  "starship006/wikidatapeople"                      # placeholder repo (no files)
  "philippesaade/wikidata"                          # FULL wikidata 4.8TB — meta only, skip download
  "rayliuca/WikidataLabels"                         # multi-lang labels — huge, skip download
  "Wikimedians/wikidata-all"                        # 2.5MB sample parquet + conversion script
  "intfloat/wikidata5m"                             # ~1.6GB — borderline, attempt
  "derenrich/wikidata-en-descriptions"              # ~4GB parquet — skip download
  "derenrich/wikidata-en-descriptions-small"        # smaller variant
  "derenrich/wikidata-enwiki-categories-and-statements"
  "Mitsua/wikidata-parallel-descriptions-en-ja"     # 127MB JSONL en-ja labels
  "Jarbas/WikidataMediaEntities"                    # 103MB CSV media entities
  "aiintelligentsystems/vel_commons_wikidata"       # wikidata + commons mapping

  # --- Genealogy / family trees ---
  "gabrielwu/genealogy_synthetic"                   # synthetic genealogy QA, 1.9MB
  "adzcai/genealogy_synthetic_v2"                   # synthetic genealogy QA parquet
  "adzcai/genealogy_synthetic_v3"
  "mmhzlrj/Genealogy"                               # Chinese genealogy materials
  "Reesimo/Chinese__genealogy"                      # Chinese genealogy JSONL
  "bubl-ai/williams_family_tree"                    # synthetic family tree, 7z
  "hopeahilton/bible-english-translations-genealogy" # Bible genealogy passages+QA
  "DavidRottensteiner/Palomino_Genealogy_VS"        # Spanish/Peruvian genealogy PDFs
  "ask81070307/lineage-name-mapper"
  "yhc465399/lineage-name-mapper"

  # --- Kings / dynasties / historical figures ---
  "QingYuYunTu/Chinese_Historical_Figures_Dialogue" # 56MB Chinese figures
  "jungypark/joseon-5-kings-qa"                     # 351KB Korean Joseon kings QA
  "zhengr/Yellow-Emperors-Inner-Canon"              # 1.3MB Chinese imperial canon
  "TrueHistory/The_True_History_of_Secrets_in_the_Ming_Dynasty" # Ming dynasty mixed
  "huggingartists/pharaoh"                          # rapper "Pharaoh" lyrics — not relevant but tagged

  # --- Heads of state / presidents ---
  "LeroyDyer/presidents"                            # 240KB JSON US presidents
  "Tuana/presidents"                                # 5MB parquet presidents docs
  "illuin-conteb/us-presidents"                     # RAG corpus on US presidents
  "fdaudens/us-presidential-elections"              # 500KB CSV 1976-2020
  "fdaudens/us-presidential-elections-with-electoral-college"
  "rajeshbenarjee01/Presidents-Of-India"            # 2.6KB CSV
  "Mina-Rajaei-Moghadam/US-Presidents-Spoken-and-Written-Sentences" # 446MB CSV — large
  "maleselalegodi/South-Africa-Presidential-Speeches-Text-and-NLP-Dataset" # 167MB zip

  # --- Religious / cultural figures ---
  "WatsonOverHere/Catholic_Saints"                  # 1.9MB JSONL catholic saints

  # --- Biographies (general but useful for figures) ---
  "alex-karev/biographies"                          # synthetic biographies
  "Flamgrise/Biographies"                           # English biographies CSV
  "Flamgrise/DE-Biographies-Lol"
  "Flamgrise/FR-biographies-LoL"
  "BetterHF/wikipedia-biography-dataset"            # Wikipedia biography (empty splits)
  "Pclanglais/wiki-dataset"                         # wiki dataset metadata
  "maywell/ko_wikidata_QA"                          # 144MB Korean wikidata QA

  # --- Gated (expected to be flagged in catalog) ---
  "adzcai/genealogy_synthetic"                      # gated:auto
  "RonyOliveira/JK-RAG-Biography"                   # gated:auto
)

# Datasets that are too large to download fully; we still catalog them with metadata.
SIZE_SKIP=(
  "philippesaade/wikidata"          # 1.8TB compressed
  "rayliuca/WikidataLabels"         # hundreds of GB across languages
  "derenrich/wikidata-en-descriptions"  # ~4GB
  "intfloat/wikidata5m"             # 1.6GB
  "Mina-Rajaei-Moghadam/US-Presidents-Spoken-and-Written-Sentences" # 446MB CSV (borderline; skip default)
)

is_size_skip() {
  local id="$1"
  for s in "${SIZE_SKIP[@]}"; do
    [[ "$s" == "$id" ]] && return 0
  done
  return 1
}

api_meta() {
  curl -fsS "https://huggingface.co/api/datasets/$1" 2>/dev/null || echo "{}"
}

api_tree() {
  curl -fsS "https://huggingface.co/api/datasets/$1/tree/main?recursive=true" 2>/dev/null || echo "[]"
}

# ---------- download worker ----------
process_one() {
  local id="$1"
  local safe; safe=$(echo "$id" | tr "/" "_")
  local out_dir="$RAW_DIR/$safe"
  mkdir -p "$out_dir"

  local meta tree
  meta=$(api_meta "$id")
  tree=$(api_tree "$id")

  local downloads likes gated license
  downloads=$(echo "$meta" | jq -r '.downloads // 0')
  likes=$(echo "$meta" | jq -r '.likes // 0')
  gated=$(echo "$meta" | jq -r '.gated // false')
  license=$(echo "$meta" | jq -r '.cardData.license // ""')

  # schema from cardData.dataset_info.features (best effort).
  # `dataset_info` may be an object or an array (multi-config datasets).
  local schema
  schema=$(echo "$meta" | jq -c '
    [ (.cardData.dataset_info // empty)
      | if type=="array" then .[0] else . end
      | .features[]?.name
    ] | unique' 2>/dev/null || echo '[]')
  [[ "$schema" == "null" || -z "$schema" ]] && schema='[]'

  # total size in bytes from tree
  local size_b
  size_b=$(echo "$tree" | jq '[.[]? | .size // 0] | add // 0' 2>/dev/null || echo 0)
  local size_mb=$(( size_b / 1024 / 1024 ))

  local reason=""
  local downloaded=false
  local files_json="[]"

  if [[ "$gated" != "false" && "$gated" != "null" && "$gated" != "" ]]; then
    reason="gated-skip"
  elif is_size_skip "$id"; then
    reason="size-skip"
  elif (( size_mb > MAX_SIZE_MB )); then
    reason="size-skip"
  else
    # download
    if "$HF_BIN" download "$id" --repo-type dataset --local-dir "$out_dir" \
         >"$out_dir/.hf_download.log" 2>&1; then
      downloaded=true
      files_json=$(find "$out_dir" -type f ! -name ".hf_download.log" ! -path "*/.cache/*" \
        | sed "s|$out_dir/||" | jq -R . | jq -s -c .)
    else
      reason="download-failed"
    fi
  fi

  # If we didn't download, still list files known from the API tree (paths only).
  if [[ "$downloaded" != "true" ]]; then
    files_json=$(echo "$tree" | jq -c '[.[]? | select(.type=="file") | .path] // []')
  fi

  local url="https://huggingface.co/datasets/$id"

  # pretty_name / first line of description as `notes`
  local notes
  notes=$(echo "$meta" | jq -r '
    .cardData.pretty_name //
    (.description // "" | split("\n") | map(select(length>0 and (test("^---")|not))) | .[0] // "")
  ' 2>/dev/null | head -c 200)

  jq -nc \
    --arg id "$id" \
    --arg url "$url" \
    --argjson downloads "${downloads:-0}" \
    --argjson likes "${likes:-0}" \
    --argjson downloaded "$downloaded" \
    --arg path "data/raw/huggingface/$safe" \
    --argjson files "$files_json" \
    --argjson size_mb "$size_mb" \
    --argjson schema "$schema" \
    --arg license "$license" \
    --arg gated "$(echo "$gated")" \
    --arg reason "$reason" \
    --arg notes "$notes" \
    '{id:$id, url:$url, downloads_30d:$downloads, likes:$likes,
      downloaded:$downloaded, path:$path, files:$files, size_mb:$size_mb,
      schema:$schema, license:$license, gated:$gated, reason:$reason, notes:$notes}'
}
export -f process_one api_meta api_tree is_size_skip
export RAW_DIR MAX_SIZE_MB HF_BIN
export SIZE_SKIP_STR="${SIZE_SKIP[*]}"

# Re-export is_size_skip to use the env var
is_size_skip() {
  local id="$1"
  for s in $SIZE_SKIP_STR; do
    [[ "$s" == "$id" ]] && return 0
  done
  return 1
}
export -f is_size_skip

: > "$CATALOG"

export CATALOG
printf '%s\n' "${DATASETS[@]}" | \
  xargs -I {} -P "$PARALLEL" bash -c 'process_one "{}" >> "$CATALOG"'

# Post-process: enrich schemas by inspecting downloaded CSV/JSONL/parquet files.
python3 - "$CATALOG" <<'PY'
import csv, glob, gzip, io, json, os, sys

cat_path = sys.argv[1]
rows = []
with open(cat_path) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))

def schema_from_csv(path):
    try:
        opener = gzip.open if path.endswith(".gz") else open
        with opener(path, "rt", encoding="utf-8", errors="ignore", newline="") as f:
            r = csv.reader(f)
            return next(r)
    except Exception:
        return None

def schema_from_jsonl(path):
    try:
        opener = gzip.open if path.endswith(".gz") else open
        with opener(path, "rt", encoding="utf-8", errors="ignore") as f:
            line = f.readline()
            if not line:
                return None
            obj = json.loads(line)
            if isinstance(obj, dict):
                return list(obj.keys())
    except Exception:
        return None
    return None

def schema_from_json(path):
    try:
        with open(path, "rt", encoding="utf-8", errors="ignore") as f:
            obj = json.load(f)
        if isinstance(obj, list) and obj and isinstance(obj[0], dict):
            return list(obj[0].keys())
        if isinstance(obj, dict):
            for v in obj.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    return list(v[0].keys())
            return list(obj.keys())[:25]
    except Exception:
        return None
    return None

def schema_from_parquet(path):
    try:
        import pyarrow.parquet as pq  # type: ignore
        return [f.name for f in pq.ParquetFile(path).schema_arrow]
    except Exception:
        return None

PROJECT_ROOT = os.path.dirname(os.path.dirname(cat_path))
ROOT = os.path.dirname(PROJECT_ROOT) if PROJECT_ROOT.endswith("data/raw") else None

for row in rows:
    if row.get("schema"):
        continue
    if not row.get("downloaded"):
        continue
    out_dir = os.path.join(os.path.dirname(cat_path), os.path.basename(row["path"]))
    if not os.path.isdir(out_dir):
        continue
    cand = []
    # Prefer canonical names
    for pat in ("*.csv", "*.tsv", "*.jsonl", "*.json", "*.parquet"):
        cand.extend(glob.glob(os.path.join(out_dir, "**", pat), recursive=True))
    cand = [p for p in cand if "/.cache/" not in p and not p.endswith(".hf_download.log")]
    cand.sort(key=lambda p: os.path.getsize(p) if os.path.exists(p) else 0)
    schema = []
    for p in cand:
        if p.endswith(".csv") or p.endswith(".tsv"):
            s = schema_from_csv(p)
        elif p.endswith(".jsonl"):
            s = schema_from_jsonl(p)
        elif p.endswith(".json"):
            s = schema_from_json(p)
        elif p.endswith(".parquet"):
            s = schema_from_parquet(p)
        else:
            s = None
        if s:
            schema = s
            break
    if schema:
        row["schema"] = schema[:30]

with open(cat_path, "w") as f:
    for row in rows:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
PY

echo
echo "Catalog written: $CATALOG"
echo "Total entries:   $(wc -l < "$CATALOG" | tr -d ' ')"
echo "Downloaded:      $(jq -s '[.[] | select(.downloaded==true)] | length' "$CATALOG")"
echo "Size-skipped:    $(jq -s '[.[] | select(.reason=="size-skip")] | length' "$CATALOG")"
echo "Gated-skipped:   $(jq -s '[.[] | select(.reason=="gated-skip")] | length' "$CATALOG")"
echo "Failed:          $(jq -s '[.[] | select(.reason=="download-failed")] | length' "$CATALOG")"
