#!/usr/bin/env bash
# Deep Wikipedia category crawler for Asia families.
#
# Differs from wikipedia_categories.sh:
#  - Recurses up to MAX_DEPTH=3 levels of subcategories.
#  - Targets Asia-specific seed categories across en/ko/ja/zh/vi/th/id/hi.
#  - Emits per-row country_hint derived from the seed (more reliable than per-subcat).
#
# Usage: bash scripts/fetchers/wikipedia_asia_deep.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_DIR="$ROOT/data/raw/wikipedia"
OUT_FILE="$OUT_DIR/families_asia.jsonl"
CAT_STATS="$OUT_DIR/_category_stats_asia.tsv"
TMP_DIR="$OUT_DIR/_tmp/asia"
LOG_FILE="$OUT_DIR/_crawl_asia.log"

mkdir -p "$OUT_DIR" "$TMP_DIR"
: > "$OUT_FILE"
: > "$CAT_STATS"
: > "$LOG_FILE"

UA='RoyalTree-research/0.1 (kibongkook@gmail.com)'
MAX_DEPTH=${MAX_DEPTH:-3}

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$LOG_FILE" >&2; }

urlenc() { jq -rn --arg s "$1" '$s|@uri'; }

# Args: lang category cmtype (page|subcat)
fetch_members() {
  local lang="$1" cat="$2" cmtype="$3"
  local host="https://${lang}.wikipedia.org/w/api.php"
  local cont=""
  local all="[]"
  while : ; do
    local url="${host}?action=query&list=categorymembers&cmtitle=$(urlenc "$cat")&cmlimit=500&cmtype=${cmtype}&format=json&formatversion=2"
    [[ -n "$cont" ]] && url="${url}&cmcontinue=$(urlenc "$cont")"
    local resp
    resp=$(curl -sS --max-time 60 -A "$UA" "$url" 2>>"$LOG_FILE")
    [[ -z "$resp" ]] && break
    local chunk
    chunk=$(printf '%s' "$resp" | jq -c '.query.categorymembers // []')
    if [[ -n "$chunk" && "$chunk" != "null" ]]; then
      all=$(jq -c -n --argjson a "$all" --argjson b "$chunk" '$a + $b')
    fi
    cont=$(printf '%s' "$resp" | jq -r '.continue.cmcontinue // empty')
    [[ -z "$cont" ]] && break
    sleep 0.05
  done
  printf '%s' "$all"
}

fetch_qids() {
  local lang="$1" ids="$2"
  local host="https://${lang}.wikipedia.org/w/api.php"
  local url="${host}?action=query&prop=pageprops&ppprop=wikibase_item&pageids=$(urlenc "$ids")&format=json&formatversion=2"
  curl -sS --max-time 60 -A "$UA" "$url" 2>>"$LOG_FILE" \
    | jq -c '[(.query.pages // [])[] | {pageid:.pageid, qid:(.pageprops.wikibase_item // null), title:.title}]'
}

# Recurse into a seed category up to MAX_DEPTH
# Args: lang seed_cat depth current_cat country_hint
walk() {
  local lang="$1" seed="$2" depth="$3" cur="$4" hint="$5"
  local visited_file="$TMP_DIR/visited_${lang}_$(printf '%s' "$seed" | tr -c 'A-Za-z0-9' '_').txt"
  touch "$visited_file"
  if grep -qxF "$cur" "$visited_file"; then return 0; fi
  echo "$cur" >> "$visited_file"

  # 1) ns=0 pages in this category
  local pages_json
  pages_json=$(fetch_members "$lang" "$cur" "page")
  pages_json=$(printf '%s' "$pages_json" | jq -c '[.[] | select(.ns == 0)]')
  local n_pages
  n_pages=$(printf '%s' "$pages_json" | jq 'length')

  if (( n_pages > 0 )); then
    local pageids
    pageids=$(printf '%s' "$pages_json" | jq -r '.[].pageid')
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
      printf '%s' "$qid_json" | jq -c \
          --arg lang "$lang" \
          --arg cat "$cur" \
          --arg seed "$seed" \
          --arg hint "$hint" \
          --argjson depth "$depth" \
          '.[] | {
              qid: .qid,
              title: .title,
              wikipedia_lang: $lang,
              wikipedia_url: ("https://" + $lang + ".wikipedia.org/wiki/" + (.title|gsub(" ";"_"))),
              category: $cat,
              seed: $seed,
              depth: $depth,
              country_hint: $hint
          }' >> "$OUT_FILE"
      i=$(( i + 50 ))
      sleep 0.05
    done
    printf '%s\t%s\t%s\t%d\t%d\n' "$lang" "$cur" "$seed" "$depth" "$n_pages" >> "$CAT_STATS"
  fi

  # 2) recurse into subcategories
  if (( depth < MAX_DEPTH )); then
    local subcats_json
    subcats_json=$(fetch_members "$lang" "$cur" "subcat")
    local subs
    subs=$(printf '%s' "$subcats_json" | jq -r '.[].title')
    while IFS= read -r sub; do
      [[ -z "$sub" ]] && continue
      walk "$lang" "$seed" $((depth+1)) "$sub" "$hint"
    done <<< "$subs"
  fi
}

# Args: lang country_hint seed_cat
process() {
  local lang="$1" hint="$2" seed="$3"
  log "[$lang/$hint] SEED $seed (max_depth=$MAX_DEPTH)"
  walk "$lang" "$seed" 0 "$seed" "$hint"
  log "[$lang/$hint] DONE $seed"
}

# ============================================================
# Asia seed list — language, country_hint, category title
# ============================================================
# Korean
process ko KR "분류:한국의_성씨"   &
process ko KR "분류:한국의_본관"   &
process ko KR "분류:한국의_씨족"   &
process ko KR "분류:조선의_가문"   &
process ko KR "분류:한국의_가문"   &
process ko KR "분류:한국의_정치_가문" &
process ko KR "분류:한국의_기업인_가문" &
process en KR "Category:Korean_clans" &
process en KR "Category:Korean_royal_consorts" &
wait

# Japanese
process ja JP "Category:日本の氏族" &
process ja JP "Category:大名"       &
process ja JP "Category:武家"       &
process ja JP "Category:華族"       &
process ja JP "Category:公家"       &
process ja JP "Category:藩"         &
process ja JP "Category:財閥"       &
process en JP "Category:Japanese_clans" &
process en JP "Category:Kazoku" &
process en JP "Category:Daimyo_clans" &
wait

# Chinese + Taiwan
process zh CN "Category:中國家族" &
process zh CN "Category:中国姓氏" &
process zh CN "Category:中国朝代" &
process zh CN "Category:中国宗族" &
process zh CN "Category:中華民國家族" &
process zh CN "Category:香港家族" &
process zh TW "Category:臺灣家族" &
process en CN "Category:Chinese_families" &
process en CN "Category:Dynasties_of_China" &
process en HK "Category:Hong_Kong_families" &
wait

# Indian + South Asia
process en IN "Category:Indian_royal_families" &
process en IN "Category:Princely_states_of_India" &
process en IN "Category:Rajput_clans" &
process en IN "Category:Indian_business_families" &
process en IN "Category:Maratha_clans" &
process hi IN "श्रेणी:भारत_के_राज_परिवार" &
process en PK "Category:Pakistani_political_families" &
process en BD "Category:Bangladeshi_dynasties" &
process en LK "Category:Sri_Lankan_royal_families" &
process en NP "Category:Nepalese_royal_families" &
process en BT "Category:Bhutanese_royal_family" &
process en AF "Category:Afghan_royal_families" &
wait

# Southeast Asia
process en TH "Category:Thai_royal_family" &
process en TH "Category:Chakri_dynasty" &
process th TH "หมวดหมู่:ราชวงศ์ไทย" &
process en VN "Category:Vietnamese_dynasties" &
process vi VN "Thể_loại:Triều_đại_Việt_Nam" &
process vi VN "Thể_loại:Gia_tộc_Việt_Nam" &
process en ID "Category:Indonesian_royal_families" &
process id ID "Kategori:Kesultanan_di_Indonesia" &
process id ID "Kategori:Wangsa_di_Indonesia" &
process en MY "Category:Malaysian_royal_families" &
process en MY "Category:Malay_royal_houses" &
process en PH "Category:Filipino_dynasties" &
process en PH "Category:Sultanate_of_Sulu" &
process en BN "Category:Bruneian_royal_family" &
process en KH "Category:Cambodian_royal_family" &
process en LA "Category:Laotian_royal_family" &
process en MM "Category:Burmese_royal_family" &
wait

# Central Asia + Mongolia
process en MN "Category:Mongol_dynasties" &
process en MN "Category:Borjigin" &
wait

log "ALL ASIA DONE"
wc -l "$OUT_FILE" | tee -a "$LOG_FILE"
