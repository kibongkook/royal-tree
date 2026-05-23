-- ============================================================================
-- Royals project — Wikidata SPARQL harvest queries
-- Target endpoint:  https://query.wikidata.org/sparql
-- Required headers:
--   Accept: application/sparql-results+json
--   User-Agent: Royals-research/0.1 (kibongkook@gmail.com)
--
-- All queries use the LIMIT/country-chunk pattern so each call stays under
-- the 60s endpoint timeout. The harvest driver is
-- scripts/fetchers/wikidata_harvest.py.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Target classes (instance-of, P31). "+subc" = also walks wdt:P279* subclasses.
-- Counts captured at harvest time (2026-05-22):
--
--   Q8436        noble family                  16,114 direct / 43,682 +subc
--   Q4438121     royal family                   1,533 direct
--   Q7210356     political family               4,362 direct
--   Q188784      royal house                       70 +subc
--   Q1156073     royal house (alt)                108 direct
--   Q499247      Scottish clan                    211 direct
--   Q846706      bon-gwan (Korean clan)         1,182 direct
--   Q2575910     uji (Japanese clan)              308 direct
--   Q2503193     Japanese clans                   366 +subc
--   Q6071413     Irish clan                         9 direct
--   Q3918404     Pashtun tribe                     14 +subc
--   Q133311      tribe (human social group)     1,817 direct
--   Q938560      tribus (Roman)                    38 direct
--   Q24074280    noble family name                224 direct
--   Q56488093    Jewish family                     29 direct
--   Q1332544     gotra (Hindu clan)                 5 direct
--   Q840178      Chinese kin                        2 direct
--   Q207320      ruling dynasty                   457 direct
--
-- DROPPED after investigation:
--   Q5621421  — actually "company" in Wikidata, not Scottish clan (use Q499247)
--   Q3024240  — historical clan = historical state/admin division, not family
--   Q1755673  — 0 instances
--   Q1190554  — "occurrence", explodes to 4M via subclass; not useful
--   Q874405   — social class, explodes to 145k via subclass; not useful
-- ---------------------------------------------------------------------------


-- ============================================================================
-- Q01. Base shape — used for all small classes (direct P31, no chunking)
--      Substitute {CLASS} for the target QID.
-- ============================================================================
-- :class-direct
SELECT ?item ?itemLabel ?countryQid ?inception ?dissolved
       ?label_en ?label_ko ?label_ja ?label_zh ?label_de ?label_fr ?label_es ?label_it ?label_ru ?label_ar
WHERE {
  ?item wdt:P31 wd:{CLASS} .
  OPTIONAL { ?item wdt:P17 ?countryQid }
  OPTIONAL { ?item wdt:P571 ?inception }
  OPTIONAL { ?item wdt:P576 ?dissolved }
  OPTIONAL { ?item rdfs:label ?label_en FILTER(lang(?label_en) = "en") }
  OPTIONAL { ?item rdfs:label ?label_ko FILTER(lang(?label_ko) = "ko") }
  OPTIONAL { ?item rdfs:label ?label_ja FILTER(lang(?label_ja) = "ja") }
  OPTIONAL { ?item rdfs:label ?label_zh FILTER(lang(?label_zh) = "zh") }
  OPTIONAL { ?item rdfs:label ?label_de FILTER(lang(?label_de) = "de") }
  OPTIONAL { ?item rdfs:label ?label_fr FILTER(lang(?label_fr) = "fr") }
  OPTIONAL { ?item rdfs:label ?label_es FILTER(lang(?label_es) = "es") }
  OPTIONAL { ?item rdfs:label ?label_it FILTER(lang(?label_it) = "it") }
  OPTIONAL { ?item rdfs:label ?label_ru FILTER(lang(?label_ru) = "ru") }
  OPTIONAL { ?item rdfs:label ?label_ar FILTER(lang(?label_ar) = "ar") }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}


-- ============================================================================
-- Q02. Base shape with subclass walk — for Q188784, Q2503193, Q3918404
--      Note: avoid for Q8436 (too many results, see Q03 instead).
-- ============================================================================
-- :class-subc
SELECT ?item ?itemLabel ?countryQid ?inception ?dissolved
       ?label_en ?label_ko ?label_ja ?label_zh ?label_de ?label_fr ?label_es ?label_it ?label_ru ?label_ar
WHERE {
  ?item wdt:P31/wdt:P279* wd:{CLASS} .
  OPTIONAL { ?item wdt:P17 ?countryQid }
  OPTIONAL { ?item wdt:P571 ?inception }
  OPTIONAL { ?item wdt:P576 ?dissolved }
  OPTIONAL { ?item rdfs:label ?label_en FILTER(lang(?label_en) = "en") }
  OPTIONAL { ?item rdfs:label ?label_ko FILTER(lang(?label_ko) = "ko") }
  OPTIONAL { ?item rdfs:label ?label_ja FILTER(lang(?label_ja) = "ja") }
  OPTIONAL { ?item rdfs:label ?label_zh FILTER(lang(?label_zh) = "zh") }
  OPTIONAL { ?item rdfs:label ?label_de FILTER(lang(?label_de) = "de") }
  OPTIONAL { ?item rdfs:label ?label_fr FILTER(lang(?label_fr) = "fr") }
  OPTIONAL { ?item rdfs:label ?label_es FILTER(lang(?label_es) = "es") }
  OPTIONAL { ?item rdfs:label ?label_it FILTER(lang(?label_it) = "it") }
  OPTIONAL { ?item rdfs:label ?label_ru FILTER(lang(?label_ru) = "ru") }
  OPTIONAL { ?item rdfs:label ?label_ar FILTER(lang(?label_ar) = "ar") }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}


-- ============================================================================
-- Q03. Q8436 noble family (+subc, ~43,682 rows) — chunked by country.
--      The chunker runs:
--        (a) one query per country in P17 (rare countries first, big last)
--        (b) one "no-country" query for items without P17.
--      Each chunk should be small enough (<10k) to clear under 60s.
--      Substitute {COUNTRY} for the country QID (e.g. wd:Q183 for Germany);
--      use 'NO_COUNTRY' marker to invert.
-- ============================================================================
-- :Q8436-by-country
SELECT ?item ?itemLabel ?countryQid ?inception ?dissolved
       ?label_en ?label_ko ?label_ja ?label_zh ?label_de ?label_fr ?label_es ?label_it ?label_ru ?label_ar
WHERE {
  ?item wdt:P31/wdt:P279* wd:Q8436 .
  ?item wdt:P17 wd:{COUNTRY} .
  BIND(wd:{COUNTRY} AS ?countryQid)
  OPTIONAL { ?item wdt:P571 ?inception }
  OPTIONAL { ?item wdt:P576 ?dissolved }
  OPTIONAL { ?item rdfs:label ?label_en FILTER(lang(?label_en) = "en") }
  OPTIONAL { ?item rdfs:label ?label_ko FILTER(lang(?label_ko) = "ko") }
  OPTIONAL { ?item rdfs:label ?label_ja FILTER(lang(?label_ja) = "ja") }
  OPTIONAL { ?item rdfs:label ?label_zh FILTER(lang(?label_zh) = "zh") }
  OPTIONAL { ?item rdfs:label ?label_de FILTER(lang(?label_de) = "de") }
  OPTIONAL { ?item rdfs:label ?label_fr FILTER(lang(?label_fr) = "fr") }
  OPTIONAL { ?item rdfs:label ?label_es FILTER(lang(?label_es) = "es") }
  OPTIONAL { ?item rdfs:label ?label_it FILTER(lang(?label_it) = "it") }
  OPTIONAL { ?item rdfs:label ?label_ru FILTER(lang(?label_ru) = "ru") }
  OPTIONAL { ?item rdfs:label ?label_ar FILTER(lang(?label_ar) = "ar") }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}

-- :Q8436-no-country
SELECT ?item ?itemLabel ?countryQid ?inception ?dissolved
       ?label_en ?label_ko ?label_ja ?label_zh ?label_de ?label_fr ?label_es ?label_it ?label_ru ?label_ar
WHERE {
  ?item wdt:P31/wdt:P279* wd:Q8436 .
  FILTER NOT EXISTS { ?item wdt:P17 ?anyCountry }
  OPTIONAL { ?item wdt:P571 ?inception }
  OPTIONAL { ?item wdt:P576 ?dissolved }
  OPTIONAL { ?item rdfs:label ?label_en FILTER(lang(?label_en) = "en") }
  OPTIONAL { ?item rdfs:label ?label_ko FILTER(lang(?label_ko) = "ko") }
  OPTIONAL { ?item rdfs:label ?label_ja FILTER(lang(?label_ja) = "ja") }
  OPTIONAL { ?item rdfs:label ?label_zh FILTER(lang(?label_zh) = "zh") }
  OPTIONAL { ?item rdfs:label ?label_de FILTER(lang(?label_de) = "de") }
  OPTIONAL { ?item rdfs:label ?label_fr FILTER(lang(?label_fr) = "fr") }
  OPTIONAL { ?item rdfs:label ?label_es FILTER(lang(?label_es) = "es") }
  OPTIONAL { ?item rdfs:label ?label_it FILTER(lang(?label_it) = "it") }
  OPTIONAL { ?item rdfs:label ?label_ru FILTER(lang(?label_ru) = "ru") }
  OPTIONAL { ?item rdfs:label ?label_ar FILTER(lang(?label_ar) = "ar") }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}

-- Discover countries used by Q8436 + count (to chunk in size order)
-- :Q8436-country-list
SELECT ?country (COUNT(DISTINCT ?item) AS ?c) WHERE {
  ?item wdt:P31/wdt:P279* wd:Q8436 .
  ?item wdt:P17 ?country .
} GROUP BY ?country ORDER BY DESC(?c)


-- ============================================================================
-- Q04. ISO 3166-1 alpha-2 lookup table — fetch once and reuse to map P17 QIDs
-- ============================================================================
-- :iso-map
SELECT ?country ?iso WHERE {
  ?country wdt:P297 ?iso .
}
