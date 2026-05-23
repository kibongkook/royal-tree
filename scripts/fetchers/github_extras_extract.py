#!/usr/bin/env python3
"""
Extract family-level + person-level records from two GitHub datasets and
write them as JSONL into data/raw/github/ for the downstream pipeline:

  * alicetinkaya76/islamic-civilization-atlas
      data/all_dynasties_enriched.csv  (186 rows)  → _islamic_atlas_dynasties.jsonl
      data/all_rulers_merged.csv       (831 rows)  → _islamic_atlas_rulers.jsonl    (Phase 2)

  * Linking-ai/ctm_bench
      data/figure_zh.json   (1652 figures, dynasty-tagged) → grouped:
        - per-dynasty family-level summary → _ctm_bench_dynasties.jsonl
        - individuals → _ctm_bench_figures.jsonl                                     (Phase 2)

This script is idempotent: re-running overwrites the outputs.
"""
from __future__ import annotations
import csv, json, re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
ATLAS_DIR = ROOT / "data" / "raw" / "github" / "islamic-civilization-atlas" / "data"
CTM_DIR   = ROOT / "data" / "raw" / "github" / "ctm_bench" / "data"
OUT_DIR   = ROOT / "data" / "raw" / "github"

ATLAS_DYN_CSV  = ATLAS_DIR / "all_dynasties_enriched.csv"
ATLAS_RUL_CSV  = ATLAS_DIR / "all_rulers_merged.csv"
CTM_FIG_JSON   = CTM_DIR / "figure_zh.json"
CTM_DYN_JSON   = CTM_DIR / "dynasty_zh.json"

OUT_ATLAS_DYN  = OUT_DIR / "_islamic_atlas_dynasties.jsonl"
OUT_ATLAS_RUL  = OUT_DIR / "_islamic_atlas_rulers.jsonl"
OUT_CTM_DYN    = OUT_DIR / "_ctm_bench_dynasties.jsonl"
OUT_CTM_FIG    = OUT_DIR / "_ctm_bench_figures.jsonl"

# -------------- Islamic Atlas region mapping --------------

REGION_CSV = ROOT / "scripts" / "normalize" / "islamic_region_to_iso.csv"
QID_HINTS_CSV = ROOT / "scripts" / "normalize" / "islamic_atlas_qid_hints.csv"

# dynasty_id -> wikidata QID (curated hints for well-known Islamic dynasties)
ATLAS_DYNID_TO_QID: dict[str, str] = {}
ATLAS_DYNID_TO_EN_CANON: dict[str, str] = {}
if QID_HINTS_CSV.exists():
    with QID_HINTS_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            did = (row.get("dynasty_id") or "").strip()
            qid = (row.get("wikidata_qid") or "").strip()
            en  = (row.get("en_canonical") or "").strip()
            if did and qid.startswith("Q"):
                ATLAS_DYNID_TO_QID[did] = qid
            if did and en:
                ATLAS_DYNID_TO_EN_CANON[did] = en

GEO_ZONE_TO_ISO: dict[str, tuple[str, list[str]]] = {}
if REGION_CSV.exists():
    with REGION_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            z = (row.get("geographic_zone") or "").strip()
            p = (row.get("iso_primary") or "").strip()
            a = [x.strip() for x in (row.get("iso_all") or "").split(",") if x.strip()]
            if z and p:
                GEO_ZONE_TO_ISO[z] = (p, a)

# Free-text keyword refinements (region_primary / regions_all / capital_city).
# Each key is a lowercase Turkish keyword; value is the ISO it implies (additive).
REGION_KEYWORD_TO_ISO: list[tuple[str, str]] = [
    ("endülüs", "ES"), ("al-andalus", "ES"), ("ispanya", "ES"), ("kurtuba", "ES"),
    ("gırnata", "ES"), ("granada", "ES"), ("mayorka", "ES"), ("balear", "ES"),
    ("portekiz", "PT"),
    ("fas", "MA"), ("mağrib", "MA"), ("magrib", "MA"), ("rabat", "MA"), ("marakeş", "MA"),
    ("tunus", "TN"), ("ifrîkıye", "TN"), ("ifrikiye", "TN"), ("kayrevan", "TN"),
    ("cezayir", "DZ"), ("tlemsen", "DZ"), ("tahert", "DZ"),
    ("libya", "LY"), ("trablusgarb", "LY"),
    ("mısır", "EG"), ("kahire", "EG"), ("fustat", "EG"), ("iskenderiye", "EG"),
    ("sudan", "SD"),
    ("suriye", "SY"), ("şam", "SY"), ("damaskos", "SY"), ("damascus", "SY"), ("halep", "SY"),
    ("lübnan", "LB"),
    ("filistin", "PS"), ("kudüs", "PS"),
    ("ürdün", "JO"),
    ("israil", "IL"),
    ("irak", "IQ"), ("bağdat", "IQ"), ("kûfe", "IQ"), ("basra", "IQ"), ("musul", "IQ"),
    ("hille", "IQ"),
    ("cezire", "IQ"),
    ("anadolu", "TR"), ("konya", "TR"), ("istanbul", "TR"), ("bursa", "TR"),
    ("urfa", "TR"), ("edessa", "TR"), ("diyâr-ı bekr", "TR"), ("diyar-i bekr", "TR"),
    ("iran", "IR"), ("ran", "IR"), ("fars", "IR"), ("isfahan", "IR"), ("tahran", "IR"),
    ("kirmân", "IR"), ("kirman", "IR"), ("horasan", "IR"), ("hemedan", "IR"),
    ("tebriz", "IR"), ("rey", "IR"), ("şiraz", "IR"), ("siraz", "IR"),
    ("azerbaycan", "AZ"),
    ("gürcistan", "GE"),
    ("ermenistan", "AM"),
    ("afganistan", "AF"), ("kâbil", "AF"), ("herat", "AF"), ("gazneliler", "AF"),
    ("pakistan", "PK"), ("sind", "PK"), ("multan", "PK"),
    ("hindistan", "IN"), ("hint", "IN"), ("delhi", "IN"), ("bengal", "IN"),
    ("bangladeş", "BD"), ("bangladesh", "BD"),
    ("özbekistan", "UZ"), ("mâverâünnehir", "UZ"), ("maverannehir", "UZ"),
    ("buhara", "UZ"), ("semerkand", "UZ"), ("ferganâ", "UZ"),
    ("türkmenistan", "TM"), ("merv", "TM"),
    ("tacikistan", "TJ"),
    ("kazakistan", "KZ"),
    ("kırgızistan", "KG"), ("kirgizistan", "KG"),
    ("hicaz", "SA"), ("medine", "SA"), ("mekke", "SA"), ("riyad", "SA"),
    ("arap yarımadası", "SA"), ("arabistan", "SA"), ("necd", "SA"),
    ("yemen", "YE"), ("aden", "YE"), ("san'a", "YE"), ("zabid", "YE"),
    ("umân", "OM"), ("uman", "OM"), ("oman", "OM"),
    ("birleşik arap", "AE"),
    ("katar", "QA"),
    ("kuveyt", "KW"),
    ("bahreyn", "BH"), ("ahsā", "SA"), ("ahsa", "SA"),
    ("sicilya", "IT"),
    ("mali", "ML"), ("timbuktu", "ML"),
    ("nijer", "NE"),
    ("nijerya", "NG"), ("kano", "NG"), ("sokoto", "NG"),
    ("somali", "SO"), ("etiyopya", "ET"),
    ("endonezya", "ID"), ("açe", "ID"), ("ace", "ID"), ("java", "ID"),
    ("malezya", "MY"), ("malacca", "MY"), ("malaka", "MY"),
    ("brunei", "BN"),
    ("filipinler", "PH"),
    ("moğol", "MN"), ("kıpçak", "RU"), ("kipchak", "RU"),
    ("kazan", "RU"), ("kırım", "UA"), ("kirim", "UA"),
]

def iso_from_region(zone: str, region_primary: str, regions_all: str, capital: str) -> list[str]:
    """Combine geographic_zone mapping + Turkish keyword refinement.

    Strategy:
      1. Scan region_primary/regions_all/capital_city for ISO-bearing keywords
         (Turkish placenames). These are the most precise.
      2. If no keyword hits, fall back to the geographic_zone's primary ISO +
         the full multi-ISO zone list.
      3. If keyword hits exist, only add the zone's *primary* ISO as additional
         context (skip the broad multi-zone list to avoid noise).
    """
    iso_kw: list[str] = []
    blob = " ".join([region_primary or "", regions_all or "", capital or ""]).lower()
    for kw, code in REGION_KEYWORD_TO_ISO:
        if kw in blob and code not in iso_kw:
            iso_kw.append(code)

    iso_zone_primary = None
    iso_zone_all: list[str] = []
    if zone and zone in GEO_ZONE_TO_ISO:
        iso_zone_primary, iso_zone_all = GEO_ZONE_TO_ISO[zone]

    if iso_kw:
        out = list(iso_kw)
        if iso_zone_primary and iso_zone_primary not in out:
            out.append(iso_zone_primary)
        return out
    out: list[str] = []
    if iso_zone_primary:
        out.append(iso_zone_primary)
    for c in iso_zone_all:
        if c not in out:
            out.append(c)
    return out

def clean_atlas_en(name: str) -> str:
    """Strip 'The ' prefix and parenthetical/alias clutter so that the resulting
    name has a chance to match Wikidata's canonical 'X dynasty' form.

    'The Umayyad Caliphs'                  -> 'Umayyad'
    "The Nasrids or Banū 'l-Ahmar"         -> 'Nasrid'
    'The Almoravids or al-Murābitūn'       -> 'Almoravid'
    """
    if not name:
        return name
    s = name.strip()
    s = re.sub(r"^The\s+", "", s, flags=re.IGNORECASE)
    # Cut anything from " or " onward (alternate-name)
    s = re.split(r"\s+or\s+", s, maxsplit=1)[0]
    # Strip plural-s: "Umayyads" -> "Umayyad", "Hafsids" -> "Hafsid"
    s = re.sub(r"(?<=[a-zāīūḍḥṣṭẓ])s$", "", s)
    # Drop trailing role words
    s = re.sub(r"\s+(Caliphs?|Sharifs?|Sharīfs?|Sultans?|Amīrs?|Amirs?|Imāms?|Imams?|Beys?|Chiefs?|Rulers?|Kings?|Khans?)\s*(of\s+\w+)?$", "", s, flags=re.IGNORECASE)
    return s.strip()

def parse_int(s) -> int | None:
    if s is None:
        return None
    if isinstance(s, int):
        return s
    s = str(s).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        # year could be BCE prefixed with "-"
        m = re.match(r"-?\d+", s)
        return int(m.group(0)) if m else None

# -------------- Islamic Atlas extraction --------------

def emit_islamic_atlas():
    n_dyn = 0
    n_rul = 0
    if not ATLAS_DYN_CSV.exists():
        print(f"  [skip] {ATLAS_DYN_CSV} missing")
        return 0, 0

    with ATLAS_DYN_CSV.open(encoding="utf-8-sig") as f, OUT_ATLAS_DYN.open("w", encoding="utf-8") as out:
        reader = csv.DictReader(f)
        for row in reader:
            did = (row.get("dynasty_id") or "").strip()
            name_en = (row.get("dynasty_name_en") or "").strip()
            name_tr = (row.get("dynasty_name_tr") or "").strip()
            name_ar = (row.get("dynasty_name_ar") or "").strip()
            if not did or not (name_en or name_tr or name_ar):
                continue
            country = iso_from_region(
                row.get("geographic_zone") or "",
                row.get("region_primary") or "",
                row.get("regions_all") or "",
                row.get("capital_city") or "",
            )
            founded = parse_int(row.get("date_start_ce"))
            extinct = parse_int(row.get("date_end_ce"))
            # Prefer canonical Wikidata QID when known so the dedup step can merge.
            canonical_id = ATLAS_DYNID_TO_QID.get(did) or f"royal-tree:islamic-atlas:{did}"
            canonical_en = (
                ATLAS_DYNID_TO_EN_CANON.get(did)
                or clean_atlas_en(name_en)
                or name_en
            )
            rec = {
                "id": canonical_id,
                "names": {k: v for k, v in [("en", canonical_en), ("tr", name_tr), ("ar", name_ar)] if v},
                "country": country,
                "category": "royal",
                "period": {"founded": founded, "extinct": extinct},
                "status": "extinct",
                "head_current": None,
                "sources": ["github:alicetinkaya76/islamic-civilization-atlas:all_dynasties_enriched.csv"],
                "raw": {
                    "atlas_dynasty_id": did,
                    "atlas_name_en_original": name_en,
                    "parent_tribe": (row.get("parent_tribe_or_clan") or "").strip() or None,
                    "ethnic_origin": (row.get("ethnic_origin") or "").strip() or None,
                    "capital": (row.get("capital_city") or "").strip() or None,
                    "region_primary": (row.get("region_primary") or "").strip() or None,
                    "regions_all": (row.get("regions_all") or "").strip() or None,
                    "geographic_zone": (row.get("geographic_zone") or "").strip() or None,
                    "predecessor": (row.get("predecessor") or "").strip() or None,
                    "successor": (row.get("successor") or "").strip() or None,
                    "government_type": (row.get("government_type") or "").strip() or None,
                    "religious_orientation": (row.get("religious_orientation") or "").strip() or None,
                    "narrative_en": (row.get("narrative_en") or "").strip() or None,
                    "importance_level": (row.get("importance_level") or "").strip() or None,
                    "capital_lat": (row.get("capital_lat") or "").strip() or None,
                    "capital_lon": (row.get("capital_lon") or "").strip() or None,
                    "century_start": parse_int(row.get("century_start")),
                    "century_end": parse_int(row.get("century_end")),
                },
            }
            out.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
            n_dyn += 1

    if ATLAS_RUL_CSV.exists():
        with ATLAS_RUL_CSV.open(encoding="utf-8-sig") as f, OUT_ATLAS_RUL.open("w", encoding="utf-8") as out:
            reader = csv.DictReader(f)
            for row in reader:
                pid = (row.get("person_id") or "").strip()
                did = (row.get("dynasty_id") or "").strip()
                if not pid:
                    continue
                rec = {
                    "id": f"royal-tree:islamic-atlas:person:{pid}",
                    "dynasty_id_link": f"royal-tree:islamic-atlas:{did}" if did else None,
                    "dynasty_name": (row.get("dynasty_name") or "").strip() or None,
                    "sub_branch": (row.get("sub_branch") or "").strip() or None,
                    "full_name_original": (row.get("full_name_original") or "").strip() or None,
                    "short_name": (row.get("short_name") or "").strip() or None,
                    "kunya": (row.get("kunya") or "").strip() or None,
                    "nasab": (row.get("nasab") or "").strip() or None,
                    "laqab": (row.get("laqab") or "").strip() or None,
                    "title": (row.get("title") or "").strip() or None,
                    "role": (row.get("role") or "").strip() or None,
                    "reign_start_ce": parse_int(row.get("reign_start_ce")),
                    "reign_end_ce": parse_int(row.get("reign_end_ce")),
                    "death_ce": parse_int(row.get("death_date_ce")),
                    "death_type": (row.get("death_type") or "").strip() or None,
                    "predecessor_ruler": (row.get("predecessor_ruler") or "").strip() or None,
                    "successor_ruler": (row.get("successor_ruler") or "").strip() or None,
                    "relationship_to_prev": (row.get("relationship_to_prev") or "").strip() or None,
                    "is_founder": (row.get("is_founder") or "").strip() or None,
                    "is_last_ruler": (row.get("is_last_ruler") or "").strip() or None,
                    "succession_type": (row.get("succession_type") or "").strip() or None,
                    "reign_order": parse_int(row.get("reign_order")),
                    "sources": ["github:alicetinkaya76/islamic-civilization-atlas:all_rulers_merged.csv"],
                }
                out.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
                n_rul += 1
    return n_dyn, n_rul

# -------------- ctm_bench extraction --------------

CTM_DYN_EN = {
    "夏": "Xia",
    "商": "Shang",
    "周": "Zhou",
    "秦": "Qin",
    "汉": "Han",
    "三国": "Three Kingdoms",
    "六朝": "Six Dynasties",
    "晋": "Jin",
    "南北朝": "Northern and Southern Dynasties",
    "隋": "Sui",
    "唐": "Tang",
    "五代": "Five Dynasties",
    "宋": "Song",
    "辽": "Liao",
    "金": "Jin (Jurchen)",
    "元": "Yuan",
    "明": "Ming",
    "清": "Qing",
    "民国": "Republic of China",
    "先秦": "Pre-Qin",
}

def slugify_zh(s: str) -> str:
    """Make a deterministic ASCII-safe slug from a CN string by mapping known chars."""
    return CTM_DYN_EN.get(s, "").lower().replace(" ", "-") or s

def emit_ctm_bench():
    if not CTM_FIG_JSON.exists():
        print(f"  [skip] {CTM_FIG_JSON} missing")
        return 0, 0
    figures = json.loads(CTM_FIG_JSON.read_text(encoding="utf-8"))

    # dynasty period bounds from dynasty_zh.json (when present)
    dyn_bounds: dict[str, dict[str, int | None]] = {}
    if CTM_DYN_JSON.exists():
        try:
            dyn_zh = json.loads(CTM_DYN_JSON.read_text(encoding="utf-8"))
            for d, v in dyn_zh.items():
                dyn_bounds[d] = {
                    "founded": parse_int(v.get("begin")),
                    "extinct": parse_int(v.get("end")),
                }
        except json.JSONDecodeError:
            pass

    # group figures per dynasty
    grouped: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for name, v in figures.items():
        dyn = (v.get("dynasty") or "").strip() or "?"
        grouped[dyn].append((name, v))

    # write individuals
    n_fig = 0
    with OUT_CTM_FIG.open("w", encoding="utf-8") as out:
        for dyn, items in grouped.items():
            for name, v in items:
                rec = {
                    "id": f"royal-tree:ctm-bench:figure:{name}",
                    "name_zh": name,
                    "dynasty_zh": dyn,
                    "dynasty_en": CTM_DYN_EN.get(dyn),
                    "address": v.get("address"),
                    "year_birth": parse_int(v.get("year_birth")),
                    "year_death": parse_int(v.get("year_death")),
                    "sources": ["github:Linking-ai/ctm_bench:figure_zh.json"],
                }
                out.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
                n_fig += 1

    # write family-level summaries (≥3 figures only)
    n_dyn = 0
    with OUT_CTM_DYN.open("w", encoding="utf-8") as out:
        for dyn, items in grouped.items():
            if len(items) < 3:
                continue
            years = [parse_int(v.get("year_birth")) for _, v in items if v.get("year_birth")]
            years += [parse_int(v.get("year_death")) for _, v in items if v.get("year_death")]
            years = [y for y in years if y is not None]
            bounds = dyn_bounds.get(dyn, {})
            founded = bounds.get("founded") if bounds.get("founded") is not None else (min(years) if years else None)
            extinct = bounds.get("extinct") if bounds.get("extinct") is not None else (max(years) if years else None)
            en_name = CTM_DYN_EN.get(dyn)
            slug = slugify_zh(dyn) or dyn
            rec = {
                "id": f"royal-tree:ctm-bench:{slug}" if slug != dyn else f"royal-tree:ctm-bench:dyn-{n_dyn+1}",
                "names": {k: v for k, v in [("zh", dyn), ("en", en_name)] if v},
                "country": ["CN"],
                "category": "royal",
                "period": {"founded": founded, "extinct": extinct},
                "status": "extinct",
                "head_current": None,
                "sources": ["github:Linking-ai/ctm_bench:figure_zh.json"],
                "raw": {
                    "figure_count": len(items),
                    "ctm_dynasty_zh": dyn,
                    "dynasty_bounds_source": "dynasty_zh.json" if dyn in dyn_bounds else "figure_year_span",
                },
            }
            out.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
            n_dyn += 1
    return n_dyn, n_fig

# -------------- main --------------

def main():
    print(f"Region zone map: {len(GEO_ZONE_TO_ISO)} zones loaded from {REGION_CSV}")
    print()
    print("[1/2] Islamic Civilization Atlas")
    a_dyn, a_rul = emit_islamic_atlas()
    print(f"  + dynasties:  {a_dyn:>4}  → {OUT_ATLAS_DYN}")
    print(f"  + rulers:     {a_rul:>4}  → {OUT_ATLAS_RUL}")
    print()
    print("[2/2] ctm_bench (figure_zh.json)")
    c_dyn, c_fig = emit_ctm_bench()
    print(f"  + dynasties:  {c_dyn:>4}  → {OUT_CTM_DYN}")
    print(f"  + figures:    {c_fig:>4}  → {OUT_CTM_FIG}")

if __name__ == "__main__":
    main()
