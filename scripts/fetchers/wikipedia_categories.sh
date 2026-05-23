#!/usr/bin/env bash
# Wikipedia category crawler for the Royal-Tree project.
#
# - Walks a list of seed categories per language Wikipedia.
# - Recurses subcategories ONE level deep (seed level 0 + subcats level 1).
# - For each leaf page (ns=0) it records title, Wikidata QID (via prop=pageprops),
#   the source category, a country_hint derived from the category name, etc.
# - Writes JSONL to data/raw/wikipedia/families.jsonl (one row per page+lang).
#
# Usage: bash scripts/fetchers/wikipedia_categories.sh
#
# Reqs: bash, curl, jq.

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_DIR="$ROOT/data/raw/wikipedia"
OUT_FILE="$OUT_DIR/families.jsonl"
CAT_STATS="$OUT_DIR/_category_stats.tsv"
TMP_DIR="$OUT_DIR/_tmp"
LOG_FILE="$OUT_DIR/_crawl.log"

mkdir -p "$OUT_DIR" "$TMP_DIR"
: > "$OUT_FILE"
: > "$CAT_STATS"
: > "$LOG_FILE"

UA='RoyalTree-research/0.1 (kibongkook@gmail.com)'

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$LOG_FILE" >&2; }

# ----- country hint table (substring match against the category name) -----
country_hint() {
  local cat="$1"
  case "$cat" in
    *Korean*|*한국*|*조선*) echo "KR" ;;
    *Japanese*|*日本*)      echo "JP" ;;
    *Chinese*|*中國*|*中国*) echo "CN" ;;
    *Scottish*)             echo "GB-SCT" ;;
    *Irish*)                echo "IE" ;;
    *English*)              echo "GB-ENG" ;;
    *Welsh*)                echo "GB-WLS" ;;
    *British*)              echo "GB" ;;
    *Italian*)              echo "IT" ;;
    *French*)               echo "FR" ;;
    *German*)               echo "DE" ;;
    *Austrian*)             echo "AT" ;;
    *Spanish*)              echo "ES" ;;
    *Portuguese*)           echo "PT" ;;
    *Russian*|*России*|*Россия*) echo "RU" ;;
    *Polish*)               echo "PL" ;;
    *Dutch*|*Netherlands*)  echo "NL" ;;
    *Belgian*)              echo "BE" ;;
    *Swedish*)              echo "SE" ;;
    *Norwegian*)            echo "NO" ;;
    *Danish*)               echo "DK" ;;
    *Finnish*)              echo "FI" ;;
    *Hungarian*)            echo "HU" ;;
    *Czech*|*Bohemian*)     echo "CZ" ;;
    *Romanian*)             echo "RO" ;;
    *Bulgarian*)            echo "BG" ;;
    *Serbian*)              echo "RS" ;;
    *Croatian*)             echo "HR" ;;
    *Greek*)                echo "GR" ;;
    *Turkish*|*Ottoman*)    echo "TR" ;;
    *Iranian*|*Persian*)    echo "IR" ;;
    *Indian*)               echo "IN" ;;
    *Pakistani*)            echo "PK" ;;
    *Thai*)                 echo "TH" ;;
    *Vietnamese*)           echo "VN" ;;
    *Filipino*|*Philippine*) echo "PH" ;;
    *Indonesian*)           echo "ID" ;;
    *Malay*)                echo "MY" ;;
    *Mongol*)               echo "MN" ;;
    *Saudi*)                echo "SA" ;;
    *Egyptian*)             echo "EG" ;;
    *Moroccan*)             echo "MA" ;;
    *Ethiopian*)            echo "ET" ;;
    *Nigerian*)             echo "NG" ;;
    *American*)             echo "US" ;;
    *Canadian*)             echo "CA" ;;
    *Mexican*)              echo "MX" ;;
    *Brazilian*)            echo "BR" ;;
    *Argentine*)            echo "AR" ;;
    *عائلات_عربية*|*Arab*)  echo "AR-region" ;;
    *) echo "" ;;
  esac
}

# Encode a category title for URL (handles spaces, unicode, etc.)
urlenc() {
  jq -rn --arg s "$1" '$s|@uri'
}

# Fetch all member pages of a category, paginated, returning JSON array
# Args: lang api_host category cmtype (page|subcat)
fetch_category_members() {
  local lang="$1" cat="$2" cmtype="$3"
  local host="https://${lang}.wikipedia.org/w/api.php"
  local cont=""
  local all="[]"
  local page=1
  while : ; do
    local url="${host}?action=query&list=categorymembers&cmtitle=$(urlenc "$cat")&cmlimit=500&cmtype=${cmtype}&format=json&formatversion=2"
    if [[ -n "$cont" ]]; then
      url="${url}&cmcontinue=$(urlenc "$cont")"
    fi
    local resp=""
    local try
    for try in 1 2 3 4 5 6 7 8; do
      resp=$(curl -sS --max-time 60 -A "$UA" "$url" 2>>"$LOG_FILE")
      # Empty body? treat as transient
      if [[ -z "$resp" ]]; then
        log "  empty response for $lang $cat ($cmtype) page=$page try=$try"
        sleep $((try * 5))
        continue
      fi
      # HTML response = rate-limit / error page
      case "$resp" in
        "<!DOCTYPE"*|"<html"*|"<HTML"*|"<!doctype"*)
          log "  HTML rate-limit response for $lang $cat ($cmtype) try=$try → backoff"
          sleep $((try * 15))
          continue
          ;;
      esac
      # ratelimit / maxlag / serverror?
      local errcode
      errcode=$(printf '%s' "$resp" | jq -r '.error.code // empty' 2>/dev/null)
      if [[ -n "$errcode" ]]; then
        log "  api error ($errcode) for $lang $cat ($cmtype) try=$try"
        sleep $((try * 5))
        continue
      fi
      # Verify response actually parses as JSON
      if ! printf '%s' "$resp" | jq -e . >/dev/null 2>&1; then
        log "  non-JSON response for $lang $cat ($cmtype) try=$try"
        sleep $((try * 10))
        resp=""
        continue
      fi
      break
    done
    if [[ -z "$resp" ]]; then
      log "  GIVING UP on $lang $cat ($cmtype) page=$page after retries"
      break
    fi
    # Append members
    local chunk
    chunk=$(printf '%s' "$resp" | jq -c '.query.categorymembers // []')
    if [[ -n "$chunk" && "$chunk" != "null" ]]; then
      all=$(jq -c -n --argjson a "$all" --argjson b "$chunk" '$a + $b')
    fi
    cont=$(printf '%s' "$resp" | jq -r '.continue.cmcontinue // empty')
    if [[ -z "$cont" ]]; then
      break
    fi
    page=$((page+1))
    # be polite
    sleep 0.5
  done
  printf '%s' "$all"
}

# Resolve Wikidata QIDs for a batch of pageids
# Args: lang pageids_csv (max ~50)
fetch_qids() {
  local lang="$1" ids="$2"
  local host="https://${lang}.wikipedia.org/w/api.php"
  local url="${host}?action=query&prop=pageprops&ppprop=wikibase_item&pageids=$(urlenc "$ids")&format=json&formatversion=2"
  local resp=""
  local try
  for try in 1 2 3 4 5 6 7 8; do
    resp=$(curl -sS --max-time 60 -A "$UA" "$url" 2>>"$LOG_FILE")
    if [[ -z "$resp" ]]; then
      sleep $((try * 5)); continue
    fi
    case "$resp" in
      "<!DOCTYPE"*|"<html"*|"<HTML"*|"<!doctype"*)
        log "  HTML rate-limit in fetch_qids ($lang) try=$try → backoff"
        sleep $((try * 15)); continue ;;
    esac
    if ! printf '%s' "$resp" | jq -e . >/dev/null 2>&1; then
      sleep $((try * 10)); continue
    fi
    break
  done
  if [[ -z "$resp" ]]; then
    echo "[]"
    return
  fi
  printf '%s' "$resp" \
    | jq -c '[(.query.pages // [])[] | {pageid:.pageid, qid:(.pageprops.wikibase_item // null), title:.title}]'
}

# Walk one (lang, category): seed -> subcats one level deep -> emit pages.
# Visited set is per-lang to avoid cycles.
process_seed() {
  local lang="$1" seed="$2"
  local visited_file="$TMP_DIR/visited_${lang}.txt"
  touch "$visited_file"

  log "[$lang] SEED $seed"

  # Collect category list = seed + its subcats (one level)
  local subcats_json
  subcats_json=$(fetch_category_members "$lang" "$seed" "subcat")
  local n_sub
  n_sub=$(printf '%s' "$subcats_json" | jq 'length')
  log "[$lang]   subcats under $seed: $n_sub"

  # Build category list as TSV: title<TAB>source_seed
  local catlist_file="$TMP_DIR/cats_$(printf '%s' "${lang}_${seed}" | tr '/: ' '___').txt"
  : > "$catlist_file"
  printf '%s\t%s\n' "$seed" "$seed" >> "$catlist_file"
  printf '%s' "$subcats_json" | jq -r '.[] | .title' | while IFS= read -r sub; do
    printf '%s\t%s\n' "$sub" "$seed" >> "$catlist_file"
  done

  # For each category, fetch ns=0 page members
  while IFS=$'\t' read -r cat seed_of; do
    if grep -qxF "$cat" "$visited_file"; then
      continue
    fi
    echo "$cat" >> "$visited_file"

    local pages_json
    pages_json=$(fetch_category_members "$lang" "$cat" "page")
    # keep only ns=0
    pages_json=$(printf '%s' "$pages_json" | jq -c '[.[] | select(.ns == 0)]')
    local n_pages
    n_pages=$(printf '%s' "$pages_json" | jq 'length')
    if (( n_pages == 0 )); then
      printf '%s\t%s\t%s\t0\n' "$lang" "$cat" "$seed_of" >> "$CAT_STATS"
      continue
    fi

    local hint
    hint=$(country_hint "$cat")

    # Batch pageids 50 at a time for pageprops lookup
    local pageids
    pageids=$(printf '%s' "$pages_json" | jq -r '.[].pageid')
    local count_emitted=0
    # write pages to a tmp file keyed by pageid for join
    local pages_tmp="$TMP_DIR/pages_$$.json"
    printf '%s' "$pages_json" > "$pages_tmp"

    # join with QIDs in batches
    # shellcheck disable=SC2207
    local id_arr=($pageids)
    local i=0
    local total=${#id_arr[@]}
    while (( i < total )); do
      local batch=("${id_arr[@]:i:50}")
      local ids_csv
      ids_csv=$(IFS=\| ; echo "${batch[*]}")
      local qid_json
      qid_json=$(fetch_qids "$lang" "$ids_csv")
      # Emit one JSONL row per pageid in this batch
      printf '%s' "$qid_json" | jq -c \
          --arg lang "$lang" \
          --arg cat "$cat" \
          --arg hint "$hint" \
          '.[] | {
              qid: .qid,
              title: .title,
              wikipedia_lang: $lang,
              wikipedia_url: ("https://" + $lang + ".wikipedia.org/wiki/" + (.title|gsub(" ";"_"))),
              category: $cat,
              country_hint: $hint
          }' >> "$OUT_FILE"
      count_emitted=$(( count_emitted + ${#batch[@]} ))
      i=$(( i + 50 ))
      sleep 0.5
    done
    rm -f "$pages_tmp"

    printf '%s\t%s\t%s\t%d\n' "$lang" "$cat" "$seed_of" "$count_emitted" >> "$CAT_STATS"
    log "[$lang]   $cat → $count_emitted pages (hint=$hint)"
  done < "$catlist_file"
}

# ----- Seed lists per language -----
EN_SEEDS=(
  "Category:Noble_families_by_country"
  "Category:Royal_families"
  "Category:Dynasties"
  "Category:Family_businesses_by_country"
  "Category:Business_families"
  "Category:Scottish_clans"
  "Category:Irish_families"
  "Category:Italian_noble_families"
  "Category:French_noble_families"
  "Category:German_noble_families"
  "Category:Russian_noble_families"
  "Category:Japanese_clans"
  "Category:Korean_clans"
  "Category:Chinese_families"
  "Category:Indian_royal_families"
  "Category:Princely_states_of_India"
  "Category:Arab_dynasties"
  "Category:African_royal_families"
  "Category:Latin_American_political_families"
  "Category:American_political_families"
  "Category:Mafia_families"
  "Category:Yakuza_families"
)
KO_SEEDS=(
  "분류:한국의_가문"
  "분류:한국의_성씨_및_본관"
  "분류:조선의_가문"
)
JA_SEEDS=(
  "Category:日本の氏族"
  "Category:日本の家"
)
ZH_SEEDS=(
  "Category:中國家族"
  "Category:中国姓氏"
  "Category:朝代"
)
AR_SEEDS=(
  "تصنيف:عائلات_عربية"
)
RU_SEEDS=(
  "Категория:Дворянские_роды_России"
)

run_lang() {
  local lang="$1"; shift
  for seed in "$@"; do
    process_seed "$lang" "$seed"
  done
  log "[$lang] DONE"
}

# Each language has its own host, but Wikimedia rate-limits per source IP, so we run
# at most 2 languages in parallel and let each language process its seeds sequentially.
# Pair the heaviest (en, ru) with smaller ones to even out wall-clock.
run_lang en "${EN_SEEDS[@]}" 2>&1 &
PID_EN=$!
run_lang ko "${KO_SEEDS[@]}" 2>&1 &
PID_KO=$!
wait $PID_EN $PID_KO

run_lang ru "${RU_SEEDS[@]}" 2>&1 &
PID_RU=$!
run_lang ja "${JA_SEEDS[@]}" 2>&1 &
PID_JA=$!
wait $PID_RU $PID_JA

run_lang zh "${ZH_SEEDS[@]}" 2>&1 &
PID_ZH=$!
run_lang ar "${AR_SEEDS[@]}" 2>&1 &
PID_AR=$!
wait $PID_ZH $PID_AR

log "ALL DONE"
log "JSONL: $OUT_FILE"
log "Stats: $CAT_STATS"
wc -l "$OUT_FILE" "$CAT_STATS" | tee -a "$LOG_FILE"
