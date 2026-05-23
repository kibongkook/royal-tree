#!/usr/bin/env python3
"""
Phase 4 — Family business / wealth mapping.

Combines:
  - Forbes top-1000 billionaires snapshot (rank/name/net-worth/age/source/country)
  - Bloomberg billionaires snapshot (industry-tagged)
  - Forbes World 2019 + Forbes China snapshots (from fuzzy_pandas)
  - Davos 2019 attendees (corporate position info)
  - Hand-curated chaebol/zaibatsu/Indian-conglomerate company maps

Outputs:
  - data/master/businesses.jsonl       (company-level records, linked to family_id)
  - data/master/_forbes_unmatched.tsv  (Forbes individuals not confidently matched)
  - data/master/_businesses_summary.json
  - Updates families.jsonl in place: each business family gains businesses: [...]
"""
from __future__ import annotations
import csv, json, re, sys
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "github"
MASTER = ROOT / "data" / "master" / "families.jsonl"
OUT_BIZ = ROOT / "data" / "master" / "businesses.jsonl"
OUT_UNMATCHED = ROOT / "data" / "master" / "_forbes_unmatched.tsv"
OUT_SUMMARY = ROOT / "data" / "master" / "_businesses_summary.json"


def load_families() -> dict[str, dict]:
    fams = {}
    if not MASTER.exists():
        return fams
    with MASTER.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            fams[r["id"]] = r
    return fams


def parse_money(s: str) -> int | None:
    """Parse '79200000000', '$136B', '$1.2T', '500M' → int USD."""
    if not s:
        return None
    s = str(s).strip()
    if s.isdigit():
        return int(s)
    m = re.match(r"^\$?\s*([\d,.]+)\s*([BMTK])?$", s, re.IGNORECASE)
    if not m:
        return None
    try:
        n = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    mult = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}.get((m.group(2) or "").upper(), 1)
    return int(n * mult)


COUNTRY_TO_ISO = {
    "United States": "US", "United Kingdom": "GB", "Hong Kong": "HK",
    "China": "CN", "Russia": "RU", "Germany": "DE", "France": "FR",
    "India": "IN", "Brazil": "BR", "Italy": "IT", "Spain": "ES",
    "Japan": "JP", "Korea": "KR", "South Korea": "KR", "Sweden": "SE",
    "Canada": "CA", "Australia": "AU", "Mexico": "MX", "Switzerland": "CH",
    "Saudi Arabia": "SA", "UAE": "AE", "Taiwan": "TW", "Indonesia": "ID",
    "Singapore": "SG", "Malaysia": "MY", "Philippines": "PH", "Thailand": "TH",
    "Israel": "IL", "Turkey": "TR", "Egypt": "EG", "South Africa": "ZA",
    "Nigeria": "NG", "Argentina": "AR", "Chile": "CL", "Colombia": "CO",
    "Venezuela": "VE", "Peru": "PE", "Norway": "NO", "Denmark": "DK",
    "Finland": "FI", "Netherlands": "NL", "Belgium": "BE", "Austria": "AT",
    "Greece": "GR", "Czech Republic": "CZ", "Poland": "PL", "Ireland": "IE",
    "Portugal": "PT", "Hungary": "HU", "Ukraine": "UA", "Lebanon": "LB",
    "Cyprus": "CY", "Romania": "RO", "Vietnam": "VN", "Kazakhstan": "KZ",
    "Algeria": "DZ", "Morocco": "MA", "Pakistan": "PK", "Bangladesh": "BD",
    "Iran": "IR", "Iraq": "IQ", "Qatar": "QA", "Kuwait": "KW", "Bahrain": "BH",
    "Oman": "OM", "Jordan": "JO", "Syria": "SY", "Yemen": "YE", "Sudan": "SD",
    "Ethiopia": "ET", "Kenya": "KE", "Tanzania": "TZ", "Uganda": "UG",
    "Ghana": "GH", "Senegal": "SN",
}


def iso_of(country: str) -> str | None:
    if not country:
        return None
    return COUNTRY_TO_ISO.get(country.strip()) or (country.strip().upper() if len(country.strip()) == 2 else None)


def build_family_index(fams: dict[str, dict]) -> dict[str, list[str]]:
    """surname_lc → [family_id, ...] for fast match lookup, plus full-name keys for exact match."""
    idx = defaultdict(list)
    for fid, f in fams.items():
        if f.get("category") != "business":
            continue
        names = f.get("names") or {}
        # Try every name token (e.g. "Samsung Lee family" → samsung, lee, samsunglee)
        for lang, nm in names.items():
            if not nm:
                continue
            for token in re.findall(r"[A-Za-z][\w'-]+", nm):
                tl = token.lower()
                if len(tl) >= 3 and tl not in ("family", "group", "houses", "house"):
                    if fid not in idx[tl]:
                        idx[tl].append(fid)
    return idx


# Hand-curated known company → family mappings (the canonical ones).
# These are emitted even without Forbes matches.
MANUAL_COMPANIES = [
    # Korean chaebol
    {"id":"Q20716","names":{"en":"Samsung","ko":"삼성"},"family_id":"royals:manual:samsung-lee","industry":"electronics","country_hq":["KR"],"founded":1938,"is_public":True,"control_type":"founder-family","sources":["manual:chaebol"]},
    {"id":"Q173144","names":{"en":"LG Corporation","ko":"LG"},"family_id":"royals:manual:lg-koo","industry":"electronics","country_hq":["KR"],"founded":1947,"is_public":True,"control_type":"founder-family","sources":["manual:chaebol"]},
    {"id":"Q179807","names":{"en":"Hyundai Motor Company","ko":"현대자동차"},"family_id":"royals:manual:hyundai-chung","industry":"automotive","country_hq":["KR"],"founded":1967,"is_public":True,"control_type":"founder-family","sources":["manual:chaebol"]},
    {"id":"Q484000","names":{"en":"SK Group","ko":"SK"},"family_id":"royals:manual:sk-chey","industry":"conglomerate","country_hq":["KR"],"founded":1953,"is_public":True,"control_type":"founder-family","sources":["manual:chaebol"]},
    {"id":"Q706316","names":{"en":"Hanwha Group","ko":"한화"},"family_id":"royals:manual:hanwha-kim","industry":"conglomerate","country_hq":["KR"],"founded":1952,"is_public":True,"control_type":"founder-family","sources":["manual:chaebol"]},
    {"id":"Q487418","names":{"en":"Lotte Group","ko":"롯데"},"family_id":"royals:manual:lotte-shin","industry":"conglomerate","country_hq":["KR","JP"],"founded":1948,"is_public":True,"control_type":"founder-family","sources":["manual:chaebol"]},
    {"id":"Q310754","names":{"en":"Doosan Group","ko":"두산"},"family_id":"royals:manual:doosan-park","industry":"conglomerate","country_hq":["KR"],"founded":1896,"is_public":True,"control_type":"founder-family","sources":["manual:chaebol"]},
    {"id":"Q1135237","names":{"en":"Hyosung","ko":"효성"},"family_id":"royals:manual:hyosung-cho-family","industry":"chemicals","country_hq":["KR"],"founded":1957,"is_public":True,"control_type":"founder-family","sources":["manual:chaebol"]},

    # Japanese zaibatsu / keiretsu (founder families)
    {"id":"Q1056720","names":{"en":"Mitsubishi","ja":"三菱"},"family_id":"royals:manual:iwasaki-mitsubishi","industry":"conglomerate","country_hq":["JP"],"founded":1870,"is_public":True,"control_type":"founder-family","sources":["manual:zaibatsu"]},
    {"id":"Q220657","names":{"en":"Mitsui","ja":"三井"},"family_id":"royals:manual:mitsui-family","industry":"conglomerate","country_hq":["JP"],"founded":1673,"is_public":True,"control_type":"founder-family","sources":["manual:zaibatsu"]},
    {"id":"Q220656","names":{"en":"Sumitomo","ja":"住友"},"family_id":"royals:manual:sumitomo-family","industry":"conglomerate","country_hq":["JP"],"founded":1615,"is_public":True,"control_type":"founder-family","sources":["manual:zaibatsu"]},
    {"id":"Q53268","names":{"en":"Toyota","ja":"トヨタ"},"family_id":"royals:manual:toyota-toyoda","industry":"automotive","country_hq":["JP"],"founded":1937,"is_public":True,"control_type":"founder-family","sources":["manual:zaibatsu"]},
    {"id":"Q44392","names":{"en":"Honda","ja":"ホンダ"},"family_id":"royals:manual:honda-soichiro","industry":"automotive","country_hq":["JP"],"founded":1948,"is_public":True,"control_type":"founder-family","sources":["manual:keiretsu"]},
    {"id":"Q23368","names":{"en":"Suntory","ja":"サントリー"},"family_id":"royals:manual:saji-torii-family","industry":"beverages","country_hq":["JP"],"founded":1899,"is_public":False,"control_type":"founder-family","sources":["manual:keiretsu"]},

    # US Walton/Koch/Mars/Pritzker (the big four privately-held US dynasties)
    {"id":"Q483551","names":{"en":"Walmart"},"family_id":"royals:manual:walton-family","industry":"retail","country_hq":["US"],"founded":1962,"is_public":True,"control_type":"majority","stake_pct":48,"sources":["manual:us-dynasty","forbes"]},
    {"id":"Q1257826","names":{"en":"Koch Industries"},"family_id":"royals:manual:koch-family","industry":"conglomerate","country_hq":["US"],"founded":1940,"is_public":False,"control_type":"majority","sources":["manual:us-dynasty","forbes"]},
    {"id":"Q201840","names":{"en":"Mars, Incorporated"},"family_id":"royals:manual:mars-family","industry":"food","country_hq":["US"],"founded":1911,"is_public":False,"control_type":"majority","sources":["manual:us-dynasty","forbes"]},
    {"id":"Q828015","names":{"en":"Hyatt"},"family_id":"royals:manual:pritzker-family","industry":"hospitality","country_hq":["US"],"founded":1957,"is_public":True,"control_type":"founder-family","sources":["manual:us-dynasty"]},
    {"id":"Q221523","names":{"en":"Cargill"},"family_id":"royals:manual:cargill-macmillan","industry":"agribusiness","country_hq":["US"],"founded":1865,"is_public":False,"control_type":"majority","stake_pct":88,"sources":["manual:us-dynasty"]},
    {"id":"Q486438","names":{"en":"Berkshire Hathaway"},"family_id":"Q303","industry":"conglomerate","country_hq":["US"],"founded":1839,"is_public":True,"control_type":"controlling","sources":["manual:us-dynasty","forbes"]},

    # Europe dynasties
    {"id":"Q49581","names":{"en":"LVMH","fr":"LVMH Moët Hennessy Louis Vuitton"},"family_id":"royals:manual:arnault-family","industry":"luxury","country_hq":["FR"],"founded":1987,"is_public":True,"control_type":"majority","stake_pct":48,"sources":["manual:europe-dynasty","forbes"]},
    {"id":"Q170468","names":{"en":"Hermès","fr":"Hermès International"},"family_id":"royals:manual:dumas-hermes","industry":"luxury","country_hq":["FR"],"founded":1837,"is_public":True,"control_type":"controlling","stake_pct":67,"sources":["manual:europe-dynasty"]},
    {"id":"Q145914","names":{"en":"L'Oréal"},"family_id":"royals:manual:bettencourt-meyers","industry":"cosmetics","country_hq":["FR"],"founded":1909,"is_public":True,"control_type":"controlling","stake_pct":33,"sources":["manual:europe-dynasty"]},
    {"id":"Q186284","names":{"en":"Auchan"},"family_id":"royals:manual:mulliez-family","industry":"retail","country_hq":["FR"],"founded":1961,"is_public":False,"control_type":"majority","sources":["manual:europe-dynasty"]},
    {"id":"Q153417","names":{"en":"Kering"},"family_id":"royals:manual:pinault-family","industry":"luxury","country_hq":["FR"],"founded":1963,"is_public":True,"control_type":"controlling","stake_pct":40,"sources":["manual:europe-dynasty"]},
    {"id":"Q41171","names":{"en":"Aldi"},"family_id":"royals:manual:albrecht-family","industry":"retail","country_hq":["DE"],"founded":1946,"is_public":False,"control_type":"majority","sources":["manual:europe-dynasty"]},
    {"id":"Q26678","names":{"en":"BMW"},"family_id":"royals:manual:quandt-klatten","industry":"automotive","country_hq":["DE"],"founded":1916,"is_public":True,"control_type":"controlling","stake_pct":47,"sources":["manual:europe-dynasty"]},
    {"id":"Q190718","names":{"en":"Volkswagen Group"},"family_id":"royals:manual:porsche-piech","industry":"automotive","country_hq":["DE"],"founded":1937,"is_public":True,"control_type":"controlling","stake_pct":53,"sources":["manual:europe-dynasty"]},
    {"id":"Q170474","names":{"en":"Tetra Pak"},"family_id":"royals:manual:rausing-family","industry":"packaging","country_hq":["SE"],"founded":1951,"is_public":False,"control_type":"majority","sources":["manual:europe-dynasty"]},
    {"id":"Q57476","names":{"en":"Inditex","es":"Inditex (Zara)"},"family_id":"royals:manual:ortega-family","industry":"fashion","country_hq":["ES"],"founded":1985,"is_public":True,"control_type":"controlling","stake_pct":59,"sources":["manual:europe-dynasty"]},
    {"id":"Q189722","names":{"en":"Stellantis"},"family_id":"royals:manual:agnelli-elkann","industry":"automotive","country_hq":["NL","IT","FR"],"founded":2021,"is_public":True,"control_type":"controlling","stake_pct":14,"sources":["manual:europe-dynasty"]},
    {"id":"Q150913","names":{"en":"Wallenberg sphere (Investor AB / SEB)","sv":"Wallenberg"},"family_id":"royals:manual:wallenberg-family","industry":"finance","country_hq":["SE"],"founded":1916,"is_public":True,"control_type":"controlling","sources":["manual:europe-dynasty"]},

    # Indian conglomerates
    {"id":"Q193514","names":{"en":"Tata Group","hi":"टाटा"},"family_id":"royals:manual:tata-family","industry":"conglomerate","country_hq":["IN"],"founded":1868,"is_public":True,"control_type":"controlling","sources":["manual:indian-dynasty"]},
    {"id":"Q199386","names":{"en":"Reliance Industries"},"family_id":"royals:manual:ambani-family","industry":"conglomerate","country_hq":["IN"],"founded":1958,"is_public":True,"control_type":"controlling","stake_pct":51,"sources":["manual:indian-dynasty","forbes"]},
    {"id":"Q4737195","names":{"en":"Adani Group"},"family_id":"royals:manual:adani-family","industry":"conglomerate","country_hq":["IN"],"founded":1988,"is_public":True,"control_type":"controlling","sources":["manual:indian-dynasty","forbes"]},
    {"id":"Q620510","names":{"en":"Aditya Birla Group"},"family_id":"royals:manual:birla-family","industry":"conglomerate","country_hq":["IN"],"founded":1857,"is_public":True,"control_type":"controlling","sources":["manual:indian-dynasty"]},
    {"id":"Q1893329","names":{"en":"Mahindra Group"},"family_id":"royals:manual:mahindra-family","industry":"automotive","country_hq":["IN"],"founded":1945,"is_public":True,"control_type":"controlling","sources":["manual:indian-dynasty"]},
    {"id":"Q11189","names":{"en":"Wipro"},"family_id":"royals:manual:premji-wipro","industry":"tech","country_hq":["IN"],"founded":1945,"is_public":True,"control_type":"controlling","stake_pct":73,"sources":["manual:indian-dynasty"]},

    # Hong Kong tycoons
    {"id":"Q1124251","names":{"en":"CK Hutchison Holdings"},"family_id":"royals:manual:li-ka-shing","industry":"conglomerate","country_hq":["HK"],"founded":2015,"is_public":True,"control_type":"controlling","sources":["manual:hk-tycoon"]},
    {"id":"Q838948","names":{"en":"Sun Hung Kai Properties"},"family_id":"royals:manual:kwok-family","industry":"real-estate","country_hq":["HK"],"founded":1972,"is_public":True,"control_type":"controlling","sources":["manual:hk-tycoon"]},
    {"id":"Q707283","names":{"en":"New World Development"},"family_id":"royals:manual:cheng-family","industry":"real-estate","country_hq":["HK"],"founded":1970,"is_public":True,"control_type":"controlling","sources":["manual:hk-tycoon"]},
    {"id":"Q707288","names":{"en":"Henderson Land Development"},"family_id":"royals:manual:lee-shau-kee","industry":"real-estate","country_hq":["HK"],"founded":1973,"is_public":True,"control_type":"controlling","sources":["manual:hk-tycoon"]},

    # Other Asia
    {"id":"Q204711","names":{"en":"Charoen Pokphand Group","th":"เครือเจริญโภคภัณฑ์"},"family_id":"royals:manual:chearavanont-cp","industry":"conglomerate","country_hq":["TH"],"founded":1921,"is_public":False,"control_type":"founder-family","sources":["manual:asia-tycoon"]},
    {"id":"Q1788108","names":{"en":"Salim Group"},"family_id":"royals:manual:salim-family","industry":"conglomerate","country_hq":["ID"],"founded":1972,"is_public":False,"control_type":"founder-family","sources":["manual:asia-tycoon"]},

    # Latin America
    {"id":"Q4994","names":{"en":"América Móvil","es":"América Móvil"},"family_id":"royals:manual:slim-family","industry":"telecom","country_hq":["MX"],"founded":2000,"is_public":True,"control_type":"controlling","stake_pct":51,"sources":["manual:latam","forbes"]},
    {"id":"Q189108","names":{"en":"JBS S.A."},"family_id":"royals:manual:batista-jbs","industry":"food","country_hq":["BR"],"founded":1953,"is_public":True,"control_type":"controlling","sources":["manual:latam"]},
    {"id":"Q1247215","names":{"en":"Grupo Globo"},"family_id":"royals:manual:marinho-globo","industry":"media","country_hq":["BR"],"founded":1925,"is_public":False,"control_type":"founder-family","sources":["manual:latam"]},

    # Murdoch / News Corp / Fox
    {"id":"Q193972","names":{"en":"News Corp"},"family_id":"royals:manual:murdoch-family","industry":"media","country_hq":["US","AU"],"founded":1979,"is_public":True,"control_type":"controlling","sources":["manual:media-dynasty"]},

    # Famous royal-house holdings — Crown Estate as a proxy
    {"id":"Q1140804","names":{"en":"Crown Estate"},"family_id":"Q81589","industry":"real-estate","country_hq":["GB"],"founded":1760,"is_public":False,"control_type":"sovereign","sources":["manual:royal-estate"]},
    {"id":"Q1377388","names":{"en":"Imperial Household Agency","ja":"宮内庁"},"family_id":"royals:manual:imperial-house-japan","industry":"sovereign","country_hq":["JP"],"founded":1869,"is_public":False,"control_type":"sovereign","sources":["manual:royal-estate"]},
    {"id":"Q11704","names":{"en":"Saudi Aramco"},"family_id":"Q165687","industry":"energy","country_hq":["SA"],"founded":1933,"is_public":True,"control_type":"sovereign","stake_pct":98,"sources":["manual:royal-estate"]},
]


def normalize_company_record(c: dict) -> dict:
    return {
        "id": c["id"],
        "names": c.get("names") or {"en": c.get("id")},
        "family_id": c.get("family_id"),
        "control_type": c.get("control_type"),
        "stake_pct": c.get("stake_pct"),
        "industry": c.get("industry"),
        "country_hq": c.get("country_hq") or [],
        "country_ops": c.get("country_ops") or c.get("country_hq") or [],
        "founded": c.get("founded"),
        "head_count_employees": c.get("head_count_employees"),
        "revenue_usd": c.get("revenue_usd"),
        "valuation_usd": c.get("valuation_usd"),
        "is_public": c.get("is_public"),
        "ticker": c.get("ticker") or [],
        "foundations": c.get("foundations") or [],
        "sources": c.get("sources") or [],
        "raw": c.get("raw") or {},
    }


def match_forbes_to_family(name: str, country: str, fam_idx: dict[str, list[str]], fams: dict[str, dict]) -> str | None:
    """Heuristic match: scan billionaire's name tokens, look up each in fam_idx,
    pick the family whose country includes Forbes's country."""
    iso = iso_of(country) or ""
    name_tokens = [t.lower() for t in re.findall(r"[A-Za-z][\w'-]+", name) if len(t) >= 3]
    candidates: dict[str, int] = {}
    for tok in name_tokens:
        for fid in fam_idx.get(tok, []):
            candidates[fid] = candidates.get(fid, 0) + 1
    # Filter by country match
    best = None
    best_score = 0
    for fid, score in candidates.items():
        f = fams.get(fid, {})
        if iso and iso in (f.get("country") or []):
            score += 5  # country match bonus
        if score > best_score:
            best_score = score
            best = fid
    return best if best_score >= 6 else None  # require at least one name token + country match


def main():
    print("Loading families...")
    fams = load_families()
    print(f"  {len(fams):,} families ({sum(1 for f in fams.values() if f.get('category') == 'business'):,} business)")

    fam_idx = build_family_index(fams)
    print(f"  built family-name token index: {len(fam_idx):,} tokens")

    companies: dict[str, dict] = {}

    # ---- 1. Manual canonical companies ----
    print("\nIngesting hand-curated canonical companies...")
    for c in MANUAL_COMPANIES:
        rec = normalize_company_record(c)
        companies[rec["id"]] = rec
    print(f"  loaded {len(MANUAL_COMPANIES)} manual companies")

    # ---- 2. Forbes top-1000 ----
    print("\nIngesting Forbes top-1000 billionaires...")
    forbes_path = RAW / "Little-Big-Data" / "top1000billionaires.csv"
    matched = unmatched = 0
    unmatched_rows = []
    if forbes_path.exists():
        with forbes_path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                name = row.get("Name", "")
                country = row.get("Country of Citizenship", "")
                source = row.get("Source", "")
                worth = parse_money(row.get("Net Worth", ""))
                age = row.get("Age", "")
                fid = match_forbes_to_family(name, country, fam_idx, fams)
                if fid:
                    matched += 1
                    # Add a person-level wealth annotation as a "company-like" record
                    bid = f"forbes:billionaire:{row.get('Rank')}:{name.lower().replace(' ', '-')}"
                    rec = normalize_company_record({
                        "id": bid,
                        "names": {"en": source or name},
                        "family_id": fid,
                        "control_type": "founder-or-heir",
                        "industry": source.lower() if source else None,
                        "country_hq": [iso_of(country)] if iso_of(country) else [],
                        "is_public": None,
                        "valuation_usd": worth,
                        "sources": ["forbes-2014-15"],
                        "raw": {"forbes_rank": row.get("Rank"), "owner_name": name, "owner_age": age},
                    })
                    companies.setdefault(rec["id"], rec)
                else:
                    unmatched += 1
                    unmatched_rows.append((row.get("Rank"), name, country, source, str(worth or "")))
    print(f"  Forbes-1000: matched {matched}, unmatched {unmatched}")

    # ---- 3. Bloomberg billionaires ----
    print("\nIngesting Bloomberg billionaires...")
    bl_path = RAW / "fuzzy_pandas" / "examples" / "data" / "bloomberg-billionaires.csv"
    bl_matched = 0
    if bl_path.exists():
        with bl_path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                name = row.get("Name", "")
                country = row.get("Country", "")
                industry = row.get("Industry", "")
                worth = parse_money(row.get("Total_net_worth", ""))
                fid = match_forbes_to_family(name, country, fam_idx, fams)
                if fid:
                    bl_matched += 1
                    bid = f"bloomberg:billionaire:{row.get('Rank')}:{name.lower().replace(' ', '-')}"
                    rec = normalize_company_record({
                        "id": bid,
                        "names": {"en": name},
                        "family_id": fid,
                        "control_type": "founder-or-heir",
                        "industry": industry.lower() if industry else None,
                        "country_hq": [iso_of(country)] if iso_of(country) else [],
                        "is_public": None,
                        "valuation_usd": worth,
                        "sources": ["bloomberg-2018-19"],
                        "raw": {"bloomberg_rank": row.get("Rank"), "owner_name": name},
                    })
                    companies.setdefault(rec["id"], rec)
                else:
                    unmatched_rows.append((row.get("Rank"), name, country, industry, "bloomberg"))
    print(f"  Bloomberg: matched {bl_matched}")

    # ---- 4. Forbes World 2019 ----
    print("\nIngesting Forbes World 2019...")
    fw_path = RAW / "fuzzy_pandas" / "examples" / "data" / "forbes-billionaires.csv"
    fw_matched = 0
    if fw_path.exists():
        with fw_path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                name = (row.get("name") or row.get("Name") or "")
                country = (row.get("country") or row.get("Country") or "")
                source = (row.get("source") or row.get("Source") or row.get("industry") or "")
                worth = parse_money(row.get("worth") or row.get("Net Worth") or row.get("worthChange") or "")
                fid = match_forbes_to_family(name, country, fam_idx, fams)
                if fid:
                    fw_matched += 1
                    bid = f"forbes2019:billionaire:{name.lower().replace(' ', '-')}"
                    rec = normalize_company_record({
                        "id": bid,
                        "names": {"en": source or name},
                        "family_id": fid,
                        "control_type": "founder-or-heir",
                        "industry": source.lower() if source else None,
                        "country_hq": [iso_of(country)] if iso_of(country) else [],
                        "is_public": None,
                        "valuation_usd": worth,
                        "sources": ["forbes-2019"],
                        "raw": {"owner_name": name},
                    })
                    companies.setdefault(rec["id"], rec)
                else:
                    unmatched_rows.append((row.get("rank") or row.get("Rank") or "", name, country, source, "forbes2019"))
    print(f"  Forbes 2019: matched {fw_matched}")

    # ---- Write businesses.jsonl ----
    print(f"\nWriting {OUT_BIZ}...")
    biz_records = sorted(companies.values(), key=lambda x: (x.get("family_id") or "", -((x.get("valuation_usd") or 0))))
    with OUT_BIZ.open("w", encoding="utf-8") as f:
        for r in biz_records:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

    # ---- Update families.jsonl: add businesses array ----
    print(f"Updating families.jsonl with businesses arrays...")
    biz_by_fam: dict[str, list[str]] = defaultdict(list)
    for r in biz_records:
        if r.get("family_id"):
            biz_by_fam[r["family_id"]].append(r["id"])
    for fid, f in fams.items():
        bs = biz_by_fam.get(fid, [])
        if bs:
            f["businesses"] = bs
    with MASTER.open("w", encoding="utf-8") as fout:
        for r in sorted(fams.values(), key=lambda x: (x.get("category","zzz"), x.get("country",[]), (x.get("names") or {}).get("en",""))):
            fout.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

    # ---- Unmatched TSV ----
    print(f"Writing {OUT_UNMATCHED}...")
    with OUT_UNMATCHED.open("w", encoding="utf-8") as f:
        f.write("rank\tname\tcountry\tsource_industry\tnote\n")
        for row in unmatched_rows[:5000]:  # cap
            f.write("\t".join(str(x) for x in row) + "\n")

    # ---- Summary ----
    by_industry = Counter(r.get("industry") or "unknown" for r in biz_records)
    by_country = Counter()
    for r in biz_records:
        for c in r.get("country_hq", []):
            by_country[c] += 1
    by_family = Counter(r.get("family_id") for r in biz_records if r.get("family_id"))
    top_fams = []
    for fid, n in by_family.most_common(30):
        fname = (fams.get(fid, {}).get("names") or {}).get("en", fid)
        top_fams.append({"family_id": fid, "name_en": fname, "company_count": n})

    summary = {
        "total_business_records": len(biz_records),
        "families_with_businesses": len(biz_by_fam),
        "manual_companies": len(MANUAL_COMPANIES),
        "forbes_matched": matched,
        "forbes_unmatched": unmatched,
        "bloomberg_matched": bl_matched,
        "forbes_2019_matched": fw_matched,
        "by_industry": dict(by_industry.most_common(30)),
        "by_country_hq": dict(by_country.most_common(30)),
        "top_30_families_by_company_count": top_fams,
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    print(f"\n--- Summary ---")
    print(f"  Total business records:     {len(biz_records):,}")
    print(f"  Families with businesses:   {len(biz_by_fam):,}")
    print(f"  Forbes-1000 matched:        {matched} / {matched + unmatched}")
    print(f"  Bloomberg matched:          {bl_matched}")
    print(f"  Forbes 2019 matched:        {fw_matched}")
    print(f"\nTop 10 families by company-count:")
    for x in top_fams[:10]:
        print(f"  {x['company_count']:>3}  {x['family_id']}  ({x['name_en']})")


if __name__ == "__main__":
    main()
