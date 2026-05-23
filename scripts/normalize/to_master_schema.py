#!/usr/bin/env python3
"""
Normalize every raw source into the common Royals master schema:

  {
    "id": "Q44613",                        # Wikidata QID (canonical) | royals:<src>:<slug>
    "names": {"en": "...", "ko": "...", ...},
    "country": ["AT", "ES", ...],          # ISO 3166-1 alpha-2
    "category": "royal|noble|clan|business|religious|tribal|political|unknown",
    "period": {"founded": int|None, "extinct": int|None},
    "status": "active|extinct|deposed|merged|unknown",
    "head_current": "...",
    "sources": ["wikidata", "ck3:dyn:Q...", "wikipedia:en:Category:..."],
    "raw": {...}                           # bag of source-specific fields for traceability
  }

Reads every JSONL under data/raw/ and emits one normalized line per record into
data/master/_normalized.jsonl. Downstream dedup.py merges by id.
"""
from __future__ import annotations
import json, re, sys, os, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "master"
OUT.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT / "_normalized.jsonl"

# Load CK3 culture -> ISO country mapping (for entries without iso_country_hint)
CK3_CULTURE_ISO: dict[str, str] = {}
_culture_csv = ROOT / "scripts" / "normalize" / "ck3_culture_to_country.csv"
if _culture_csv.exists():
    import csv as _csv
    with _culture_csv.open(encoding="utf-8") as _f:
        for row in _csv.DictReader(_f):
            iso = (row.get("iso_country") or "").strip()
            cul = (row.get("culture") or "").strip().lower()
            if cul and iso and re.fullmatch(r"[A-Z]{2}", iso):
                CK3_CULTURE_ISO[cul] = iso

# ---- Country mapping: Wikidata QID -> ISO 3166-1 alpha-2 ----
# Common historical / political-entity QIDs seen in our Wikidata harvest.
# Modern countries already arrive as alpha-2; only historical QIDs need mapping.
QID_TO_ISO = {
    "Q1747689": "AT",  # Archduchy of Austria -> AT
    "Q186096":  "DE",  # German Confederation -> DE
    "Q172579":  "DE",  # Holy Roman Empire -> DE (closest modern successor)
    "Q172107":  "AT",  # Austria-Hungary -> AT
    "Q170770":  "RU",  # Russian Empire -> RU
    "Q34266":   "RU",  # Russian Empire alt
    "Q49683":   "DE",  # Prussia
    "Q156199":  "DE",  # Kingdom of Prussia
    "Q201705":  "PL",  # Polish-Lithuanian Commonwealth -> PL (primary)
    "Q15864":   "UA",  # Cossack Hetmanate -> UA
    "Q12060881": "RO", # Wallachia -> RO
    "Q3332217": "RO",  # Moldavia
    "Q810":     "IR",  # Persia (modern Iran)
    "Q756617":  "DK",  # Kingdom of Denmark and Norway? best guess DK
    "Q229":     "CY",  # Cyprus
    "Q762943":  "DE",  # Holy Roman Empire territory variant
    "Q878":     "AE",  # UAE
    "Q702224":  "GR",  # First Hellenic Republic? -> GR
    "Q3845763": "RO",  # Transylvania
    "Q235":     "MC",  # Monaco
    "Q854415":  "ME",  # Montenegro? approx
    "Q655621":  "IT",  # Papal States -> IT/VA closest
    "Q884":     "KR",  # South Korea
    "Q18097":   "RU",  # Caucasus / Imeretia variants -> RU/GE — default RU
    "Q3399982": "ES",  # Crown of Castile -> ES
    "Q175276":  "ES",  # Crown of Aragon -> ES
    "Q195972":  "FR",  # Kingdom of France (medieval) -> FR
    "Q163268":  "FR",  # Carolingian Empire / Frankish -> FR
    "Q499247":  "IT",  # Kingdom of Italy (medieval) -> IT
    "Q1156073": "IT",  # Kingdom of the Two Sicilies -> IT
    "Q188784":  "US",  # Some royal-house qid mapped to fictional houses (House of El) -> mark for filter
    "Q938560":  "BY",  # Grand Duchy of Lithuania? -> BY/LT/UA, default BY
    "Q56488093": "RU", # generic historical
    "Q1747689": "AT",  # dup
    "Q3918404": "DE",
    "Q6071413": "DE",
    "Q1332544": "DE",
    "Q840178":  "DE",
}

# QIDs that are NOT real noble houses (filter on instance_of)
FICTIONAL_INSTANCE_OF_QIDS = {
    # Q188784 in our data corresponds to the QID "House of El" (Superman family)
    # NOT a real royal house. We tag entries that are PURELY this instance.
    # Heuristic: if instance_of == ['Q188784'] AND country == [], drop.
}

# Names of obvious fictional characters / superhero families
FICTIONAL_NAME_PATTERNS = [
    r"\bHal Jordan\b",
    r"\bElastigirl\b",
    r"\bSpider-?Man\b",
    r"\bSuperman\b",
    r"\bBatman\b",
    r"\bGreen Lantern\b",
    r"\bX-Men\b",
    r"\bAvengers\b",
    r"\bIron Man\b",
    r"\bAnt-Man\b",
    r"\bWonder Woman\b",
    r"\bCaptain America\b",
    r"\bDarth\b",
    r"\bJedi\b",
    r"\bSith\b",
    r"\bHogwarts\b",
    r"\bHobbit\b",
    r"\bHal Jordan\b",
    r"\bSilver Surfer\b",
    r"\bDoctor Strange\b",
    r"\bKe'Haan\b",
    r"\bThanos\b",
    r"^House of El$",
    r"^House of Stark$",
    r"^House of Targaryen$",
    r"^House of Lannister$",  # GoT
    r"^House Atreides$",      # Dune
    r"^House Harkonnen$",
]
FICTIONAL_NAME_RE = re.compile("|".join(FICTIONAL_NAME_PATTERNS), re.IGNORECASE)

# Category inference from category names / instance_of QIDs
INSTANCE_OF_TO_CATEGORY = {
    "Q8436":     "noble",      # noble family
    "Q164950":   "royal",      # dynasty
    "Q13417114": "noble",      # noble house
    "Q188784":   "royal",      # royal house (but also fictional risk — see above)
    "Q4438121":  "royal",      # royal family
    "Q5621421":  "clan",       # Scottish clan
    "Q56236697": "clan",       # Chinese clan
    "Q3024240":  "clan",       # historical clan
    "Q7210356":  "political",  # political family
    "Q1755673":  "royal",      # reigning dynasty
}

def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE).strip().lower()
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:80] if s else "unknown"

def resolve_country(c) -> list[str]:
    """Normalize country values to ISO alpha-2 strings; drop unknown QIDs."""
    if not c:
        return []
    if isinstance(c, str):
        c = [c]
    out = []
    for x in c:
        if not x:
            continue
        if re.fullmatch(r"[A-Z]{2}", x):
            out.append(x)
        elif x.startswith("Q") and x in QID_TO_ISO:
            out.append(QID_TO_ISO[x])
        elif x.startswith("Q"):
            # unmapped historical QID — keep with prefix so we can audit later
            out.append(f"q:{x}")
        elif len(x) == 2 and x.isupper():
            out.append(x)
        else:
            # free-form (e.g. "GB-SCT") — keep as-is
            out.append(x)
    return sorted(set(out))

def is_fictional(name: str | None) -> bool:
    if not name:
        return False
    return bool(FICTIONAL_NAME_RE.search(name))

def infer_category(instance_of: list[str], default: str = "unknown") -> str:
    for q in (instance_of or []):
        if q in INSTANCE_OF_TO_CATEGORY:
            return INSTANCE_OF_TO_CATEGORY[q]
    return default

def emit(out, rec):
    out.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")

# ---------- per-source readers ----------

def from_wikidata(out, fp):
    """data/raw/wikidata/families.jsonl"""
    n = nf = 0
    with fp.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            name_en = r.get("name_en") or ""
            aliases = r.get("aliases") or {}
            if is_fictional(name_en) or is_fictional(aliases.get("en")):
                nf += 1
                continue
            instance_of = r.get("instance_of") or []
            country = resolve_country(r.get("country"))
            # filter the H-of-El bucket: Q188784 + no country usually means fictional char
            if instance_of == ["Q188784"] and not country:
                nf += 1
                continue
            cat = infer_category(instance_of)
            rec = {
                "id": r["id"],
                "names": {**({"en": name_en} if name_en else {}), **aliases},
                "country": country,
                "category": cat,
                "period": {"founded": r.get("inception"), "extinct": r.get("dissolved")},
                "status": "active" if not r.get("dissolved") else "extinct",
                "head_current": None,
                "sources": [f"wikidata:{r['id']}"],
                "raw": {"instance_of": instance_of},
            }
            emit(out, rec); n += 1
    return n, nf

def from_wikipedia(out, fp):
    """data/raw/wikipedia/families.jsonl & families_asia.jsonl"""
    n = nf = 0
    with fp.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            title = r.get("title") or ""
            if is_fictional(title):
                nf += 1; continue
            qid = r.get("qid")
            country = resolve_country([r.get("country_hint")] if r.get("country_hint") else [])
            wpid = qid or f"royals:wp:{r.get('wikipedia_lang','x')}:{slugify(title)}"
            cat_hint = (r.get("category") or "").lower()
            cat = (
                "clan" if "clan" in cat_hint or "氏" in cat_hint or "성씨" in cat_hint or "본관" in cat_hint
                else "noble" if "noble" in cat_hint or "公家" in cat_hint or "武家" in cat_hint or "華族" in cat_hint
                else "royal" if "royal" in cat_hint or "dynasty" in cat_hint or "monarch" in cat_hint or "藩" in cat_hint
                else "business" if "business" in cat_hint or "財閥" in cat_hint or "chaebol" in cat_hint
                else "unknown"
            )
            rec = {
                "id": wpid,
                "names": {r.get("wikipedia_lang","en"): title},
                "country": country,
                "category": cat,
                "period": {"founded": None, "extinct": None},
                "status": "unknown",
                "head_current": None,
                "sources": [f"wikipedia:{r.get('wikipedia_lang','en')}:{r.get('category','?')}"],
                "raw": {"wikipedia_url": r.get("wikipedia_url")},
            }
            emit(out, rec); n += 1
    return n, nf

def from_ck3(out, fp, game="ck3"):
    """data/raw/ck3/dynasties.jsonl & houses.jsonl"""
    n = 0
    with fp.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            iso = r.get("iso_country_hint")
            if not iso:
                cul = (r.get("culture") or "").lower()
                iso = CK3_CULTURE_ISO.get(cul)
            country = [iso] if iso else []
            names = {}
            for k, v in r.items():
                if k.startswith("name_") and v:
                    lang = k[5:]
                    names[lang] = v
            if not names and r.get("key"):
                names["en"] = r["key"]
            rid = f"royals:{game}:{r.get('id') or r.get('key')}"
            rec = {
                "id": rid,
                "names": names,
                "country": country,
                "category": "noble" if game in ("ck3","ck2") and "house" in str(fp.name) else "royal",
                "period": {"founded": None, "extinct": None},
                "status": "unknown",
                "head_current": None,
                "sources": [f"{game}:{fp.name}:{r.get('id') or r.get('key')}"],
                "raw": {"culture": r.get("culture"), "prefix": r.get("prefix"), "religion": r.get("religion")},
            }
            emit(out, rec); n += 1
    return n, 0

def from_eu4(out, fp):
    n = 0
    with fp.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            tag = r.get("tag")
            if not tag:
                continue
            rid = f"royals:eu4:{tag}"
            rec = {
                "id": rid,
                "names": {"en": r.get("name_file","").replace("countries/","").replace(".txt","") or tag},
                "country": [],
                "category": "royal",
                "period": {"founded": None, "extinct": None},
                "status": "unknown",
                "head_current": None,
                "sources": [f"eu4:tag:{tag}"],
                "raw": {"graphical_culture": r.get("graphical_culture")},
            }
            emit(out, rec); n += 1
    return n, 0

def from_github_extra(out, fp):
    """data/raw/github/_*.jsonl — pre-clustered family-level records emitted by
    parse_royal92_gedcom.py and parse_royalconstellations.py. They already conform
    to the master schema; we just pass them through with light validation.
    """
    n = 0
    with fp.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            rid = r.get("id")
            if not rid:
                continue
            # Normalize names/country/period fields defensively
            names = r.get("names") or {}
            if not isinstance(names, dict):
                names = {}
            country = resolve_country(r.get("country") or [])
            period = r.get("period") or {}
            rec = {
                "id": rid,
                "names": names,
                "country": country,
                "category": r.get("category") or "royal",
                "period": {"founded": period.get("founded"), "extinct": period.get("extinct")},
                "status": r.get("status") or "unknown",
                "head_current": r.get("head_current"),
                "sources": r.get("sources") or [f"github:{fp.name}"],
                "raw": r.get("raw") or {},
            }
            emit(out, rec); n += 1
    return n, 0


def from_manual(out, fp):
    """data/raw/manual/*.jsonl — multiple shapes"""
    n = 0
    with fp.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Two shapes observed:
            # (a) {"id": null|"Qxxx", "name_en":..., "name_native":..., "country":[..], "category":..}
            # (b) {"id": "Qxxx", "names": {"en":...}, "country":[..], "category":..}
            qid = r.get("id") or r.get("wikidata_qid_hint")
            names = r.get("names") if isinstance(r.get("names"), dict) else {}
            if "name_en" in r and r["name_en"]:
                names.setdefault("en", r["name_en"])
            if r.get("name_native"):
                nl = r.get("name_native_lang") or "und"
                names.setdefault(nl, r["name_native"])
            if "name_ar" in r and r["name_ar"]:
                names.setdefault("ar", r["name_ar"])
            for ak, av in (r.get("aliases") or {}).items():
                if isinstance(av, str) and av:
                    names.setdefault(ak, av)
            country = resolve_country(r.get("country"))
            rid = qid or f"royals:manual:{slugify((names.get('en') or names.get('ko') or names.get('ja') or 'x'))}"
            period = r.get("period") or {}
            rec = {
                "id": rid,
                "names": names,
                "country": country,
                "category": r.get("category") or "unknown",
                "period": {"founded": period.get("founded"), "extinct": period.get("extinct")},
                "status": r.get("status") or "unknown",
                "head_current": r.get("head_current"),
                "sources": [f"manual:{fp.name}"] + (r.get("sources") or []),
                "raw": {k: v for k, v in r.items() if k not in {"id","name_en","name_native","name_native_lang","country","category","period","status","head_current","sources","aliases","names"}},
            }
            emit(out, rec); n += 1
    return n, 0

# ---------- main ----------

def main():
    stats = {}
    with OUT_FILE.open("w", encoding="utf-8") as out:
        for src, paths, fn in [
            ("wikidata",        [RAW / "wikidata" / "families.jsonl"], from_wikidata),
            ("wikipedia",       sorted((RAW / "wikipedia").glob("families*.jsonl")), from_wikipedia),
            ("ck3_dynasties",   [RAW / "ck3" / "dynasties.jsonl"], lambda o,f: from_ck3(o,f,"ck3")),
            ("ck3_houses",      [RAW / "ck3" / "houses.jsonl"], lambda o,f: from_ck3(o,f,"ck3")),
            ("ck3_koh_delta",   [RAW / "ck3" / "dynasties_kingdom_heaven.jsonl"], lambda o,f: from_ck3(o,f,"ck3")),
            ("ck2_dynasties",   [RAW / "ck2" / "dynasties.jsonl"], lambda o,f: from_ck3(o,f,"ck2")),
            ("eu4_countries",   [RAW / "eu4" / "countries.jsonl"], from_eu4),
            ("github_royal92",  [RAW / "github" / "_royal92_families.jsonl"], from_github_extra),
            ("github_royalcons",[RAW / "github" / "_royalconstellations_families.jsonl"], from_github_extra),
            ("github_islamic_atlas", [RAW / "github" / "_islamic_atlas_dynasties.jsonl"], from_github_extra),
            ("github_ctm_bench",     [RAW / "github" / "_ctm_bench_dynasties.jsonl"], from_github_extra),
            ("manual",          sorted((RAW / "manual").glob("*.jsonl")), from_manual),
        ]:
            tot = filt = 0
            for fp in paths:
                if not fp.exists():
                    continue
                n, nf = fn(out, fp)
                tot += n; filt += nf
            stats[src] = (tot, filt)
            print(f"  {src:20s} +{tot:>8,} records   (filtered {filt})")
    total = sum(n for n,_ in stats.values())
    print(f"\nTotal normalized records: {total:,}")
    print(f"Output: {OUT_FILE}")

if __name__ == "__main__":
    main()
