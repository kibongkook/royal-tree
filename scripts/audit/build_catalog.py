#!/usr/bin/env python3
"""build_catalog.py — produce the final data/raw/github/catalog.jsonl.

Merges inspect_github_repos.py output with hand-curated coverage/notes
per repo. Each repo gets:
  - repo (owner/name)
  - stars
  - url
  - cloned
  - path
  - data_files (top relevant files)
  - row_count_estimate
  - coverage_hint (region/category)
  - license
  - notes (ingestion guidance)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GH = ROOT / "data" / "raw" / "github"
OUT = GH / "catalog.jsonl"

# Hand-curated notes per repo. Key = directory name in data/raw/github/.
NOTES = {
    "islamic-civilization-atlas": {
        "coverage_hint": "Islamic dynasties 632-1924 CE — 186 dynasties, 831 rulers across 7 CSVs; Turkish + English narratives + Hijri+CE dates + lat/lon",
        "notes": "GOLD MINE. data/all_dynasties_enriched.csv has 51-col schema with bilingual names, capitals, parents, allies, rivals. data/all_rulers_merged.csv has full ruler chronology with succession_type, death_category. Also: scholars.csv, monuments.csv, battles.csv, major_cities.csv. Trivially ingest into our schema.",
        "priority": 1,
    },
    "royalconstellations": {
        "coverage_hint": "European royal families ~900-2000 CE — 2,800 individuals + 7,400 family-tree edges",
        "notes": "royal-families-members-force.csv (id,name,title,gender,birth_date,death_date) + royal-families-links-force.json (graph edges with father-child/mother-child/wife-husband). Built by Nadieh Bremer (visualcinnamon). Ingest both: members → person table, links → relationship table.",
        "priority": 2,
    },
    "dynasty": {
        "coverage_hint": "British monarchs, Roman emperors, Hungarian + Julian dynasties — 11 CSV files, ~250 rows total",
        "notes": "Schema: name,birth,death,ascension,abdication,c_ascension,c_abdication. Note the `#` prefix for BCE dates and `d` flag for died-in-office. Small but clean.",
        "priority": 3,
    },
    "TimelineHistory": {
        "coverage_hint": "Indian dynasties + 2,357 individual kings (Maurya, Gupta, Chola, Pandya, Pallava, Chera, Tripartite, Delhi Sultanate, Mughal, Vijayanagara)",
        "notes": "src/content/kings/*.json — one JSON per king with hindi+english names, reign dates, dynasty, summary HTML. src/content/dynasties/*.json mirrors. kings.json + dynasty.json are aggregated. Mixed Hindi/English.",
        "priority": 4,
    },
    "ctm_bench": {
        "coverage_hint": "Chinese dynasties knowledge graph — figures, events, places, ingredients with dynasty assignments (EACL26 benchmark)",
        "notes": "data/figure_zh.json (historical figures + dynasty + birth/death), data/event_zh.json (events + dynasty + main_figures), data/place_zh.json, data/ingredient_zh.json. Chinese-language. Good for cross-referencing temporal facts.",
        "priority": 5,
    },
    "public-gedcoms": {
        "coverage_hint": "Curated public GEDCOMs — royal92.ged (European royalty 92'er), pres2020.ged (US presidents)",
        "notes": "royal92.ged is THE classic 1992 European royal-family GEDCOM (Denis R. Reid). 8,275 entries. Use a GEDCOM parser. Public domain.",
        "priority": 6,
    },
    "ancestory": {
        "coverage_hint": "Private GEDCOM export with ~96 ruler-flagged individuals + 7,489 row tree-export TSV",
        "notes": "docs/tree-export/individuals_all.tsv has id,name,sex,birth,death,country,family,birthplace,deathplace. rulers.json has 96 heuristically-identified rulers. Mostly Welsh/Irish/Scottish family.",
        "priority": 8,
    },
    "Little-Big-Data": {
        "coverage_hint": "Forbes top-1000 billionaires snapshot (2014/2015) + smaller datasets",
        "notes": "top1000billionaires.csv — Rank,Name,Net Worth,Age,Source,Country of Citizenship. 1,000 rows. Older snapshot but clean.",
        "priority": 7,
    },
    "fuzzy_pandas": {
        "coverage_hint": "Forbes World + Forbes China + Bloomberg billionaires snapshots (~2018/2019)",
        "notes": "examples/data/forbes-billionaires.csv (2,316 rows), forbes-china-billionaires.csv, bloomberg-billionaires.csv. Forbes file has wealth, industry, country, gender, realTimeRank.",
        "priority": 9,
    },
    "datasets-sotu": {
        "coverage_hint": "US State of the Union speeches 1790-2018 — one JSON+txt per year per president",
        "notes": "Each JSON in data/ is a speech transcript with metadata. Useful for cross-referencing presidents and dates.",
        "priority": 10,
    },
    "discursos-de-navidad": {
        "coverage_hint": "Spanish head-of-state Christmas speeches 1937-2020 (Franco, Juan Carlos I, Felipe VI)",
        "notes": "data/metadata.csv (year,file_name,head_of_state,url_text) + data/*.txt full speeches.",
        "priority": 11,
    },
    "uk_monarchs": {
        "coverage_hint": "UK monarchs (Stuart→present) — 17 rows with full reign metadata",
        "notes": "personal-work/uk-leaders/data/uk_monarchs.csv — regal_name,house,reign_start,reign_end,reign_length,reason_for_end,birthdate,deathdate,lifespan_days,age_at_start,age_at_end,age_at_death,sex,claim,issue,full_name. Very clean — ideal schema reference.",
        "priority": 12,
    },
    "personal-work": {
        "coverage_hint": "UK monarchs (Stuart→present) — 17 rows with full reign metadata",
        "notes": "uk-leaders/data/uk_monarchs.csv — clean reign metadata: house, dates, reason_for_end, age_at_*, issue. Use as schema reference.",
        "priority": 12,
    },
    "SrilankanMonarchsSE": {
        "coverage_hint": "Sri Lankan monarchs (Vijaya Dynasty → modern) — 189 rows in Sinhala",
        "notes": "corpus/srilankanMonarchs.csv: name,detail,spouse,kingdom,dynasty,reign_start,reign_end,predecessor,successor. Native Sinhala script. Excellent quality.",
        "priority": 13,
    },
    "AU681035_Sejersen_Karoline": {
        "coverage_hint": "Danish monarchs Gorm den Gamle (936) → present — 54 rows",
        "notes": "danish_monarchs.csv with id,name,date+month+year birth/death, reign_start/end/duration. Semicolon-delimited. CC0.",
        "priority": 14,
    },
    "AU736876_Damborg_Michal": {"coverage_hint": "Danish monarchs (academic copy)", "notes": "week11-kings/Danish_monarchs.csv — duplicate of Sejersen.", "priority": 50},
    "au593509_Eithz_Mathias": {"coverage_hint": "Danish monarchs (academic copy)", "notes": "duplicate.", "priority": 50},
    "au754371_Lambaek_Julie_exam": {"coverage_hint": "Danish monarchs (academic copy)", "notes": "duplicate.", "priority": 50},
    "CultDat_LauraWPaaby": {"coverage_hint": "Danish monarchs (academic copy)", "notes": "duplicate.", "priority": 50},
    "20240122mastering": {
        "coverage_hint": "English monarchs from Offa (757) onwards — 175 rows",
        "notes": "DATA/english_monarchs.csv (no header) — year_start,year_end,name,sex.",
        "priority": 15,
    },
    "Song-Dynasty-Paintings-Database": {
        "coverage_hint": "Song Dynasty (China) paintings — 1,463 rows of art works with artists",
        "notes": "Useful for cross-referencing Song-era cultural figures/artists.",
        "priority": 20,
    },
    "Book_of_the_Dead_Sources": {
        "coverage_hint": "Egyptian 21st Dynasty — Book of the Dead spell sources (markdown only, no structured data)",
        "notes": "Just spell-by-spell markdown directories; no CSV/JSON. Skip for tabular ingest.",
        "priority": 40,
    },
    "iran-constitutional-monarchy": {
        "coverage_hint": "Iranian constitutional monarchy political project — no royal data",
        "notes": "DAO/contract code. NOT a dataset. Skip for ingest.",
        "priority": 99,
    },
    "RomanEmperorsScraper": {
        "coverage_hint": "Roman emperor family trees scraper (Java) — minimal pre-built data",
        "notes": "Mostly scraper code. Run to regenerate, but matypist/dynasty already has rom_emp_ext.csv.",
        "priority": 25,
    },
    "rtb": {
        "coverage_hint": "Real-time billionaires tracker (Forbes-derived) — Node app, no static data",
        "notes": "Data lives on @komed3/rtb-api (skipped due to 900MB size). Could be subset-cloned with sparse-checkout for json snapshots.",
        "priority": 30,
    },
    "billionaires-scraper": {
        "coverage_hint": "Bloomberg billionaires scraper script (Playwright)",
        "notes": "main.py only. Run to scrape. No static data.",
        "priority": 35,
    },
    "Forbes400": {
        "coverage_hint": "Forbes 400 live API — scrapes Forbes; no static data committed",
        "notes": "Node service. Run server.js to expose /api/forbes400. Or repurpose lib/scrape/scrape.js for our own pipeline.",
        "priority": 32,
    },
    "CorporateGenealogy": {
        "coverage_hint": "Chinese corporate family tree tool (academic) — code + images, no public data",
        "notes": "Java project with images of corporate trees. No structured data.",
        "priority": 90,
    },
    "freetalk-dictionary-v1": {
        "coverage_hint": "English dictionary with 50 word-list files including dynasties.json, kings.json, corulers.json",
        "notes": "words/dynasties.json, kings.json, corulers.json, surroyals.json — short vocabulary lists (~50-200 each). Useful for name normalization.",
        "priority": 22,
    },
    "BNC_COCA_EN2CN": {
        "coverage_hint": "Chinese-English BNC/COCA vocabulary — has royals.json, dynasties.json, rulers.json word lists",
        "notes": "data/royals.json, dynasties.json, rulers.json are word-frequency lists, not biographical data. Useful for lexicon only.",
        "priority": 70,
    },
    "EmbedNewConcept-20260305": {
        "coverage_hint": "Wikipedia/DBpedia page dumps — includes Early_Kassite_rulers.json, Southern_dynasties.json, lots of unrelated pages",
        "notes": "Big repo with general-purpose wiki page dumps. Targeted files: wiki_pages/Early_Kassite_rulers.json, Southern_dynasties.json. Most files are unrelated.",
        "priority": 60,
    },
    "Rdatasets": {
        "coverage_hint": "R Datasets archive — HistData/Wheat.monarchs.csv (English wheat prices by monarch reign) + 1000s of unrelated csvs",
        "notes": "Only csv/HistData/Wheat.monarchs.csv is relevant. Wheat prices keyed by English monarch reign-windows.",
        "priority": 55,
    },
    "r-datasets": {
        "coverage_hint": "MySQL version of Rdatasets — same Wheat.monarchs subset",
        "notes": "datasets/HistData/Wheat.monarchs.csv only. Duplicate of Rdatasets.",
        "priority": 56,
    },
    "tabfact": {
        "coverage_hint": "TabFact dataset — has 'shortest-reigning monarchs' table among 1000s of other tables",
        "notes": "Wikipedia-derived tables. Specific monarch tables are sparse.",
        "priority": 80,
    },
    "DataCamp": {
        "coverage_hint": "DataCamp course materials — SQL leaders/monarchs.csv tutorial dataset",
        "notes": "Single small CSV inside `SQL Courses/Joining Data in SQL/DataSets/leaders/monarchs.csv`. Tutorial-grade only.",
        "priority": 85,
    },
    "monarchs": {
        "coverage_hint": "European monarchs timeline d3 viz — single dataset.json with dates+events (catastrophes, wars)",
        "notes": "Not actually about monarchs per se — it's a Black-Death-style timeline of European events. Useful as auxiliary context.",
        "priority": 33,
    },
    "cliopatria": {
        "coverage_hint": "Seshat Global History Databank — worldwide polities geospatial dataset (geojson)",
        "notes": "cliopatria.geojson.zip (44MB) is a comprehensive polygons-by-polity-over-time geodataset, ideal for placing dynasties on a map. CC-BY.",
        "priority": 18,
    },
}


def _load_inspect():
    """Load the JSONL written by inspect_github_repos.py."""
    cat = GH / "catalog.jsonl"
    if not cat.exists():
        return []
    out = []
    with cat.open() as f:
        for ln in f:
            ln = ln.strip()
            if not ln: continue
            out.append(json.loads(ln))
    return out


def main():
    rows = _load_inspect()
    by_repo = {}
    for r in rows:
        repo_name = r["repo"].split("/")[-1] if "/" in r["repo"] else r["repo"]
        # path-derived dirname
        dir_name = r["path"].split("/")[-1]
        by_repo[dir_name] = r

    # Merge in notes; produce final JSONL
    final = []
    for dir_name, base in by_repo.items():
        meta = NOTES.get(dir_name, {})
        merged = dict(base)
        merged["coverage_hint"] = meta.get("coverage_hint", "")
        merged["notes"] = meta.get("notes", "")
        merged["priority"] = meta.get("priority", 99)
        final.append(merged)

    final.sort(key=lambda r: (r["priority"], -r["row_count_estimate"]))

    # Save with priority-sorted order
    out_path = GH / "catalog.jsonl"
    with out_path.open("w") as f:
        for rec in final:
            slim = {
                "repo": rec["repo"],
                "stars": rec.get("stars", 0),
                "url": rec.get("url"),
                "cloned": True,
                "path": rec["path"],
                "data_files": rec["data_files"],
                "row_count_estimate": rec["row_count_estimate"],
                "coverage_hint": rec["coverage_hint"],
                "license": rec.get("license"),
                "notes": rec["notes"],
                "priority": rec["priority"],
            }
            f.write(json.dumps(slim, ensure_ascii=False) + "\n")
    print(f"[catalog] wrote {len(final)} repos to {out_path}")


if __name__ == "__main__":
    main()
