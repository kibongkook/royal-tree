#!/usr/bin/env python3
"""
Paradox Clausewitz-format parser + extractor.

Extracts:
  - CK3 dynasties + dynasty_houses
  - CK2 dynasties (when available)
  - EU4 historical countries (when available)
  - Imperator: Rome dynasties (when available)

Output: one JSONL file per source under data/raw/<game>/.

The Clausewitz format is a custom KV-with-nested-braces syntax. We tokenize it
and build a tree.  Then we walk top-level entries and emit one JSONL row per
dynasty / house / country, joined with localization YAML and culture metadata.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Clausewitz tokenizer + parser
# ---------------------------------------------------------------------------

# Tokens: { } = "..." bareword  comments stripped
_TOKEN_RE = re.compile(
    r'"((?:[^"\\]|\\.)*)"'    # quoted string  (group 1)
    r'|(\{)'                   # open brace     (group 2)
    r'|(\})'                   # close brace    (group 3)
    r'|(=)'                    # equals         (group 4)
    r'|([^\s"{}=#]+)',         # bareword       (group 5)
)


def _strip_comments(text: str) -> str:
    out_lines = []
    for line in text.splitlines():
        # remove anything after a #, but keep # inside quotes
        in_q = False
        i = 0
        while i < len(line):
            c = line[i]
            if c == '"':
                in_q = not in_q
            elif c == "#" and not in_q:
                line = line[:i]
                break
            i += 1
        out_lines.append(line)
    return "\n".join(out_lines)


def _tokenize(text: str) -> Iterable[tuple[str, str]]:
    text = _strip_comments(text)
    # remove BOM
    if text.startswith("﻿"):
        text = text[1:]
    for m in _TOKEN_RE.finditer(text):
        if m.group(1) is not None:
            yield ("STR", m.group(1))
        elif m.group(2):
            yield ("LBRACE", "{")
        elif m.group(3):
            yield ("RBRACE", "}")
        elif m.group(4):
            yield ("EQ", "=")
        elif m.group(5):
            yield ("BARE", m.group(5))


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]]):
        self.toks = tokens
        self.i = 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def take(self):
        t = self.toks[self.i]
        self.i += 1
        return t

    def parse_block(self) -> Any:
        """Parse the body inside braces (or top level).

        A block can be either:
          - a list of values (e.g. { foo bar baz })
          - a map of key=value pairs (e.g. { foo = bar  baz = 3 })
        We return dict if any `=` is present, else a list.  Duplicate keys
        become a list under that key.
        """
        items = []
        pairs = []
        saw_eq = False
        while True:
            kind, val = self.peek()
            if kind is None or kind == "RBRACE":
                break
            # try to read key = value or a bare list element
            key_tok = self.take()
            kind2, val2 = self.peek()
            if kind2 == "EQ":
                saw_eq = True
                self.take()  # consume '='
                value = self.parse_value()
                pairs.append((self._tok_to_str(key_tok), value))
            else:
                items.append(self._tok_to_str(key_tok))
        if saw_eq:
            # dict with possible duplicates -> list
            out = {}
            for k, v in pairs:
                if k in out:
                    if not isinstance(out[k], list) or (out[k] and isinstance(out[k], list) and not all(isinstance(x, (dict, list)) for x in out[k])):
                        # Wrap previous as list if it isn't already a "duplicates" list
                        existing = out[k]
                        if isinstance(existing, list) and existing and isinstance(existing[0], (str, int, float)) and len(existing) == 1:
                            existing.append(v)
                        else:
                            out[k] = [existing, v]
                    else:
                        out[k].append(v)
                else:
                    out[k] = v
            return out
        else:
            return items

    @staticmethod
    def _tok_to_str(tok):
        return tok[1]

    def parse_value(self):
        kind, val = self.take()
        if kind == "LBRACE":
            block = self.parse_block()
            close = self.take()
            assert close[0] == "RBRACE", f"expected }} got {close}"
            return block
        elif kind in ("STR", "BARE"):
            return val
        else:
            raise ValueError(f"unexpected token {kind} {val}")


def parse_pdx(text: str) -> dict:
    """Parse a Paradox/Clausewitz top-level file -> dict."""
    tokens = list(_tokenize(text))
    p = _Parser(tokens)
    result = p.parse_block()
    if isinstance(result, list):
        # top-level had no equals - shouldn't happen for dynasty files
        return {"_list": result}
    return result


# ---------------------------------------------------------------------------
# Localization loader
# ---------------------------------------------------------------------------

# Paradox localization YAML is non-standard: `key:0 "value"`
_LOC_RE = re.compile(r'^\s*([A-Za-z0-9_\-\.]+)\s*:\s*\d*\s*"((?:[^"\\]|\\.)*)"', re.MULTILINE)


def load_loc_dir(loc_dir: Path) -> dict[str, str]:
    """Load all *.yml files in loc_dir and subdirs, return key->value map."""
    out: dict[str, str] = {}
    if not loc_dir.exists():
        return out
    for path in loc_dir.rglob("*.yml"):
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except Exception:
            continue
        for m in _LOC_RE.finditer(text):
            key, value = m.group(1), m.group(2)
            # un-escape \\" and \\n
            value = value.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
            out[key] = value
    return out


# ---------------------------------------------------------------------------
# Culture parser - extract culture -> region_hint
# ---------------------------------------------------------------------------

# Map CK3 culture-file basename -> region hint (matches our 00_*.txt files)
_CULTURE_FILE_REGION = {
    "akan": "west_africa",
    "arabic": "middle_east",
    "baltic": "northeast_europe",
    "balto_finnic": "northeast_europe",
    "berber": "north_africa",
    "brythonic": "british_isles",
    "burman": "southeast_asia",
    "byzantine": "balkans",
    "caucasian": "caucasus",
    "central_african": "central_africa",
    "central_germanic": "central_europe",
    "chinese": "east_asia",
    "dead": "ancient",
    "dravidian": "south_asia",
    "east_african": "east_africa",
    "east_slavic": "eastern_europe",
    "frankish": "western_europe",
    "goidelic": "british_isles",
    "iberian": "iberia",
    "indo_aryan": "south_asia",
    "iranian": "middle_east",
    "israelite": "middle_east",
    "latin": "southern_europe",
    "magyar": "central_europe",
    "mongolic": "central_asia",
    "north_germanic": "northern_europe",
    "qiangic": "tibet",
    "sahelian": "sahel",
    "sahelian_ibl": "sahel",
    "senegambian": "west_africa",
    "somalian": "horn_of_africa",
    "south_slavic": "balkans",
    "syriac": "middle_east",
    "tibetan": "tibet",
    "turkic": "central_asia",
    "ugro_permian": "northeast_europe",
    "vlach": "balkans",
    "volga_finnic": "northeast_europe",
    "west_african": "west_africa",
    "west_germanic": "central_europe",
    "west_slavic": "central_europe",
    "yoruba": "west_africa",
}


def load_cultures(cultures_dir: Path) -> dict[str, dict]:
    """Return culture_name -> {region_hint, group}."""
    out: dict[str, dict] = {}
    if not cultures_dir.exists():
        return out
    for path in cultures_dir.glob("*.txt"):
        stem = path.stem
        if stem.startswith("00_"):
            stem = stem[3:]
        region = _CULTURE_FILE_REGION.get(stem, "unknown")
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            tree = parse_pdx(text)
        except Exception as e:
            print(f"  ! failed to parse culture file {path}: {e}", file=sys.stderr)
            continue
        for culture_name, body in tree.items():
            if culture_name.startswith("_"):
                continue
            if isinstance(body, dict):
                out[culture_name] = {
                    "region_hint": region,
                    "group_file": stem,
                    "heritage": body.get("heritage"),
                    "language": body.get("language"),
                }
    return out


# ---------------------------------------------------------------------------
# CK3 culture -> primary modern country mapping
# ---------------------------------------------------------------------------

# Manually curated. Best-effort: maps the dominant medieval culture to a single
# ISO 3166-1 alpha-2 country code where the culture was historically rooted.
CK3_CULTURE_TO_COUNTRY = [
    # (culture, iso_country, region, note)
    # frankish group
    ("frankish", "FR", "western_europe", "early medieval Franks"),
    ("french", "FR", "western_europe", ""),
    ("occitan", "FR", "western_europe", ""),
    ("norman", "FR", "western_europe", "spread to England, S Italy"),
    ("breton", "FR", "western_europe", ""),
    ("flemish", "BE", "western_europe", ""),
    ("dutch", "NL", "western_europe", ""),
    ("frisian", "NL", "western_europe", ""),
    # german / central
    ("german", "DE", "central_europe", ""),
    ("franconian", "DE", "central_europe", ""),
    ("saxon", "DE", "central_europe", ""),
    ("bavarian", "DE", "central_europe", ""),
    ("swabian", "DE", "central_europe", ""),
    ("thuringian", "DE", "central_europe", ""),
    ("low_saxon", "DE", "central_europe", ""),
    ("low_frankish", "NL", "central_europe", ""),
    ("alemannic", "CH", "central_europe", ""),
    ("austrian", "AT", "central_europe", ""),
    ("swiss", "CH", "central_europe", ""),
    # iberian
    ("castilian", "ES", "iberia", ""),
    ("catalan", "ES", "iberia", ""),
    ("aragonese", "ES", "iberia", ""),
    ("asturleonese", "ES", "iberia", ""),
    ("galician", "ES", "iberia", ""),
    ("portuguese", "PT", "iberia", ""),
    ("basque", "ES", "iberia", ""),
    ("andalusian", "ES", "iberia", "Muslim Iberia, descends to Arabic"),
    ("visigothic", "ES", "iberia", "post-Roman"),
    ("suebi", "PT", "iberia", "post-Roman kingdom in Gallaecia"),
    # north germanic / scandinavia
    ("norse", "NO", "scandinavia", "pre-Christian Norse, spread broadly"),
    ("norwegian", "NO", "scandinavia", ""),
    ("swedish", "SE", "scandinavia", ""),
    ("danish", "DK", "scandinavia", ""),
    ("icelandic", "IS", "scandinavia", ""),
    # british isles
    ("english", "GB", "british_isles", ""),
    ("anglo_saxon", "GB", "british_isles", ""),
    ("welsh", "GB", "british_isles", ""),
    ("cumbrian", "GB", "british_isles", ""),
    ("pictish", "GB", "british_isles", ""),
    ("scottish", "GB", "british_isles", ""),
    ("highlander", "GB", "british_isles", ""),
    ("irish", "IE", "british_isles", ""),
    ("cornish", "GB", "british_isles", ""),
    # italy / latin
    ("italian", "IT", "southern_europe", ""),
    ("lombard", "IT", "southern_europe", ""),
    ("sardinian", "IT", "southern_europe", ""),
    ("cisalpine", "IT", "southern_europe", ""),
    ("sicilian", "IT", "southern_europe", ""),
    ("italian_norman", "IT", "southern_europe", ""),
    ("roman", "IT", "southern_europe", ""),
    ("dalmatian", "HR", "balkans", "extinct Romance language"),
    # balkans / byzantine
    ("greek", "GR", "balkans", ""),
    ("byzantine", "GR", "balkans", "Byzantine = medieval Greek state"),
    ("bulgarian", "BG", "balkans", ""),
    ("serbian", "RS", "balkans", ""),
    ("croatian", "HR", "balkans", ""),
    ("bosnian", "BA", "balkans", ""),
    ("vlach", "RO", "balkans", "Romanian ancestor"),
    ("romanian", "RO", "balkans", ""),
    ("albanian", "AL", "balkans", ""),
    ("arberian", "AL", "balkans", "medieval Albanian"),
    # eastern europe / slavic
    ("polish", "PL", "central_europe", ""),
    ("czech", "CZ", "central_europe", ""),
    ("slovak", "SK", "central_europe", ""),
    ("pomeranian", "PL", "central_europe", ""),
    ("polabian", "DE", "central_europe", "extinct West Slavic"),
    ("hungarian", "HU", "central_europe", ""),
    ("magyar", "HU", "central_europe", ""),
    ("russian", "RU", "eastern_europe", ""),
    ("muscovite", "RU", "eastern_europe", ""),
    ("ruthenian", "UA", "eastern_europe", ""),
    ("severian", "UA", "eastern_europe", ""),
    ("ilmenian", "RU", "eastern_europe", "Slavs of Novgorod"),
    ("ukrainian", "UA", "eastern_europe", ""),
    ("belarusian", "BY", "eastern_europe", ""),
    # baltic
    ("lithuanian", "LT", "northeast_europe", ""),
    ("latvian", "LV", "northeast_europe", ""),
    ("estonian", "EE", "northeast_europe", ""),
    ("prussian", "PL", "northeast_europe", "Old Prussian, extinct"),
    ("finnish", "FI", "northeast_europe", ""),
    ("karelian", "FI", "northeast_europe", ""),
    ("livonian", "LV", "northeast_europe", ""),
    ("sami", "NO", "northeast_europe", ""),
    ("permian", "RU", "northeast_europe", ""),
    ("komi", "RU", "northeast_europe", ""),
    # caucasus
    ("armenian", "AM", "caucasus", ""),
    ("georgian", "GE", "caucasus", ""),
    ("alan", "RU", "caucasus", "Ossetian ancestor"),
    ("circassian", "RU", "caucasus", ""),
    ("zikhi", "RU", "caucasus", "Adyghe ancestor"),
    ("svan", "GE", "caucasus", ""),
    ("laz", "GE", "caucasus", ""),
    ("vainakh", "RU", "caucasus", "Chechen/Ingush"),
    ("avar", "RU", "caucasus", "Dagestani Avar"),
    ("lak", "RU", "caucasus", ""),
    ("lezgin", "RU", "caucasus", ""),
    # arabic / middle east
    ("arabic", "SA", "middle_east", "broad pan-Arab"),
    ("levantine", "SY", "middle_east", ""),
    ("egyptian", "EG", "middle_east", ""),
    ("bedouin", "SA", "middle_east", ""),
    ("yemeni", "YE", "middle_east", ""),
    ("maghrebi", "MA", "north_africa", ""),
    ("hijazi", "SA", "middle_east", ""),
    ("najdi", "SA", "middle_east", ""),
    ("iraqi", "IQ", "middle_east", ""),
    # persian
    ("persian", "IR", "middle_east", ""),
    ("khorasani", "IR", "middle_east", ""),
    ("daylamite", "IR", "middle_east", ""),
    ("kurdish", "IQ", "middle_east", "Kurds across IQ/IR/TR/SY"),
    ("baloch", "PK", "middle_east", ""),
    ("sogdian", "UZ", "central_asia", ""),
    ("khwarezmian", "UZ", "central_asia", ""),
    ("afghan", "AF", "central_asia", ""),
    ("pashtun", "AF", "central_asia", ""),
    ("tajik", "TJ", "central_asia", ""),
    # turkic
    ("turkish", "TR", "middle_east", ""),
    ("oghuz", "TM", "central_asia", "ancestor of Turks/Turkmens"),
    ("turkmen", "TM", "central_asia", ""),
    ("kipchak", "KZ", "central_asia", ""),
    ("cuman", "UA", "eastern_europe", ""),
    ("pecheneg", "UA", "eastern_europe", ""),
    ("karluk", "UZ", "central_asia", ""),
    ("uyghur", "CN", "central_asia", ""),
    ("kyrgyz", "KG", "central_asia", ""),
    ("kazakh", "KZ", "central_asia", ""),
    ("tatar", "RU", "eastern_europe", ""),
    ("bashkir", "RU", "eastern_europe", ""),
    ("chuvash", "RU", "eastern_europe", ""),
    ("bolghar", "RU", "eastern_europe", ""),
    ("khazar", "RU", "eastern_europe", ""),
    ("azeri", "AZ", "caucasus", ""),
    # mongolic / steppe
    ("mongol", "MN", "central_asia", ""),
    ("khitan", "CN", "east_asia", ""),
    ("jurchen", "CN", "east_asia", ""),
    ("xianbei", "CN", "east_asia", ""),
    ("tangut", "CN", "east_asia", ""),
    # tibetan / qiangic
    ("tibetan", "CN", "tibet", ""),
    ("bodpa", "CN", "tibet", ""),
    ("zhangzhung", "CN", "tibet", ""),
    ("nepali", "NP", "south_asia", ""),
    ("bhotiya", "NP", "south_asia", ""),
    # india
    ("kannada", "IN", "south_asia", ""),
    ("tamil", "IN", "south_asia", ""),
    ("telugu", "IN", "south_asia", ""),
    ("malayalam", "IN", "south_asia", ""),
    ("sinhala", "LK", "south_asia", ""),
    ("hindustani", "IN", "south_asia", ""),
    ("rajput", "IN", "south_asia", ""),
    ("gujarati", "IN", "south_asia", ""),
    ("marathi", "IN", "south_asia", ""),
    ("bengali", "BD", "south_asia", ""),
    ("oriya", "IN", "south_asia", ""),
    ("assamese", "IN", "south_asia", ""),
    ("kashmiri", "IN", "south_asia", ""),
    ("punjabi", "IN", "south_asia", ""),
    ("sindhi", "PK", "south_asia", ""),
    ("vatadagi", "LK", "south_asia", ""),
    # east asia
    ("han", "CN", "east_asia", ""),
    ("zhao", "CN", "east_asia", ""),
    ("bai", "CN", "east_asia", ""),
    ("yi", "CN", "east_asia", ""),
    ("vietnamese", "VN", "southeast_asia", ""),
    ("khmer", "KH", "southeast_asia", ""),
    ("burmese", "MM", "southeast_asia", ""),
    ("mon", "MM", "southeast_asia", ""),
    ("thai", "TH", "southeast_asia", ""),
    ("malay", "MY", "southeast_asia", ""),
    ("javanese", "ID", "southeast_asia", ""),
    ("sundanese", "ID", "southeast_asia", ""),
    ("filipino", "PH", "southeast_asia", ""),
    ("korean", "KR", "east_asia", ""),
    ("japanese", "JP", "east_asia", ""),
    # africa
    ("nubian", "SD", "northeast_africa", ""),
    ("ethiopian", "ET", "east_africa", ""),
    ("amhara", "ET", "east_africa", ""),
    ("tigrayan", "ET", "east_africa", ""),
    ("oromo", "ET", "east_africa", ""),
    ("somali", "SO", "horn_of_africa", ""),
    ("afar", "ET", "horn_of_africa", ""),
    ("beja", "SD", "northeast_africa", ""),
    ("swahili", "KE", "east_africa", ""),
    ("malagasy", "MG", "east_africa", ""),
    ("luba_lunda", "CD", "central_africa", ""),
    ("kongolese", "CD", "central_africa", ""),
    ("bantu", "CD", "central_africa", ""),
    ("zulu", "ZA", "southern_africa", ""),
    # west africa
    ("songhai", "ML", "west_africa", ""),
    ("mande", "ML", "west_africa", ""),
    ("manden", "ML", "west_africa", ""),
    ("mandinka", "GM", "west_africa", ""),
    ("soninke", "ML", "west_africa", ""),
    ("hausa", "NG", "west_africa", ""),
    ("kanuri", "NG", "west_africa", ""),
    ("fulani", "NG", "west_africa", ""),
    ("akan", "GH", "west_africa", ""),
    ("yoruba", "NG", "west_africa", ""),
    ("igbo", "NG", "west_africa", ""),
    ("bambara", "ML", "west_africa", ""),
    ("wolof", "SN", "west_africa", ""),
    ("serer", "SN", "west_africa", ""),
    ("tukulor", "SN", "west_africa", ""),
    ("songhay", "ML", "west_africa", ""),
    # berber
    ("masmuda", "MA", "north_africa", ""),
    ("sanhaja", "MA", "north_africa", ""),
    ("zenati", "DZ", "north_africa", ""),
    ("zenata", "DZ", "north_africa", ""),
    ("guanche", "ES", "north_africa", "Canary Islands"),
    # judaic
    ("ashkenazi", "DE", "central_europe", "Jewish diaspora; primary in HRE"),
    ("sephardi", "ES", "iberia", "Jewish Iberia"),
    ("mizrahi", "IQ", "middle_east", "Jewish Mesopotamia"),
    ("karaite", "UA", "eastern_europe", ""),
    ("samaritan", "IL", "middle_east", ""),
    ("yemeni_jewish", "YE", "middle_east", ""),
    # additional / berber sub-groups
    ("butr", "DZ", "north_africa", "Berber Butr branch"),
    ("baranis", "MA", "north_africa", "Berber Baranis branch"),
    # additional west african
    ("malinke", "ML", "west_africa", ""),
    ("kru", "LR", "west_africa", ""),
    ("mel", "SL", "west_africa", ""),
    ("bobo", "BF", "west_africa", ""),
    ("bozo", "ML", "west_africa", ""),
    ("nupe", "NG", "west_africa", ""),
    ("gur", "BF", "west_africa", ""),
    ("ewe", "GH", "west_africa", ""),
    ("sao", "TD", "west_africa", "ancient Sao civilization"),
    ("guanches", "ES", "north_africa", "Canary Islands"),
    # ethiopian sub-groups
    ("welayta", "ET", "east_africa", ""),
    ("zaghawa", "TD", "northeast_africa", ""),
    # central asian / steppe
    ("kirghiz", "KG", "central_asia", ""),
    ("buryat", "RU", "central_asia", ""),
    ("naiman", "MN", "central_asia", ""),
    ("kimek", "KZ", "central_asia", ""),
    ("oirat", "MN", "central_asia", ""),
    ("uriankhai", "MN", "central_asia", ""),
    ("tuyuhun", "CN", "central_asia", ""),
    ("yughur", "CN", "central_asia", ""),
    ("saka", "TJ", "central_asia", ""),
    ("tocharian", "CN", "central_asia", "Tarim basin extinct IE"),
    # tibetan sub-groups
    ("tsangpa", "CN", "tibet", ""),
    ("sumpa", "CN", "tibet", ""),
    ("lhomon", "BT", "tibet", "Bhutanese ancestor"),
    ("kirati", "NP", "south_asia", "eastern Nepal"),
    # russian / northeast european
    ("khanty", "RU", "northeast_europe", "Ob-Ugric"),
    ("samoyed", "RU", "northeast_europe", ""),
    ("merya", "RU", "northeast_europe", "extinct Finno-Ugric"),
    ("mordvin", "RU", "northeast_europe", ""),
    ("vepsian", "RU", "northeast_europe", ""),
    # baltic / slavic sub-groups
    ("latgalian", "LV", "northeast_europe", ""),
    ("pommeranian", "PL", "central_europe", ""),
    ("slovien", "SK", "central_europe", "Old Slovak / Great Moravian"),
    ("volhynian", "UA", "eastern_europe", ""),
    ("old_saxon", "DE", "central_europe", "continental Saxons"),
    ("gaelic", "IE", "british_isles", "pre-split Goidelic"),
    ("guan", "GH", "west_africa", "Akan-related"),
]


def write_culture_csv(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["culture", "iso_country", "region", "note"])
        for row in CK3_CULTURE_TO_COUNTRY:
            w.writerow(row)


# ---------------------------------------------------------------------------
# Localization key resolver
# ---------------------------------------------------------------------------

def resolve_loc(key: str | None, loc: dict[str, str]) -> str | None:
    if not key:
        return None
    if key in loc:
        return loc[key]
    return None


def looks_fictional(name: str | None, culture: str | None) -> bool:
    """Heuristic flag for entries that are clearly fictional (TES, fantasy, etc.).

    For CK3 vanilla, we don't expect this to fire. For mods like Elder Kings or
    Warcraft GoA, it will flag everything via culture name.
    """
    if not culture:
        return False
    fictional_culture_markers = (
        "altmer", "bosmer", "dunmer", "ayleid", "khajiit", "orsimer",
        "akaviri", "atmoran", "imga", "argonian", "falmer", "dwemer",
        "tsaesci", "kamal", "sload", "potun", "maormer", "skaal", "reachmen",
        "redguard", "nibenean", "colovian", "nord", "tangmo", "islander",
        "elf", "dwarf", "orc", "draenei", "tauren", "naga", "troll", "goblin",
        "kobold", "ogre", "vrykul", "harpy", "satyr",
    )
    cl = culture.lower()
    return any(m in cl for m in fictional_culture_markers)


# ---------------------------------------------------------------------------
# CK3 extractors
# ---------------------------------------------------------------------------

def extract_ck3_dynasties(repo_root: Path, out_path: Path, source_repo: str,
                          langs: list[str]) -> dict:
    """Parse CK3 dynasty files and emit JSONL.

    Returns counts dict.
    """
    dyn_dir = repo_root / "common" / "dynasties"
    if not dyn_dir.exists():
        return {"error": "no dynasties dir"}

    # localization
    loc = {}
    for lang in langs:
        loc[lang] = load_loc_dir(repo_root / "localization" / lang)

    # cultures
    cultures = load_cultures(repo_root / "common" / "culture" / "cultures")
    culture_to_country = {c: (iso, region) for c, iso, region, _ in CK3_CULTURE_TO_COUNTRY}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    fictional = 0
    no_name_loc = 0
    loc_counts = defaultdict(int)
    with out_path.open("w", encoding="utf-8") as fp:
        for txt_path in sorted(dyn_dir.glob("*.txt")):
            # skip the RANGES.txt / info files
            if txt_path.stem.lower() in ("ranges", "_ranges"):
                continue
            try:
                text = txt_path.read_text(encoding="utf-8-sig", errors="replace")
                tree = parse_pdx(text)
            except Exception as e:
                print(f"  ! parse failed: {txt_path}: {e}", file=sys.stderr)
                continue
            for key, body in tree.items():
                if not isinstance(body, dict):
                    continue
                name_key = body.get("name")
                if isinstance(name_key, list):
                    name_key = name_key[0] if name_key else None
                prefix_key = body.get("prefix")
                if isinstance(prefix_key, list):
                    prefix_key = prefix_key[0] if prefix_key else None
                culture = body.get("culture")
                if isinstance(culture, list):
                    culture = culture[0] if culture else None

                names = {}
                for lang in langs:
                    n = resolve_loc(name_key, loc[lang])
                    if n is not None:
                        names[lang] = n
                        loc_counts[lang] += 1
                # If the name field doesn't look like a loc key (no dynn_ prefix),
                # treat it as a literal name and use it as the english fallback.
                if "english" not in names and name_key and not name_key.startswith("dynn"):
                    names["english"] = name_key
                if "english" not in names:
                    no_name_loc += 1

                iso, region = culture_to_country.get(culture or "", (None, None))
                if not region:
                    cm = cultures.get(culture or "", {})
                    region = cm.get("region_hint")

                prefix_val = None
                if prefix_key:
                    # use english loc if present, else strip dynnp_ marker
                    prefix_val = resolve_loc(prefix_key, loc.get("english", {})) or prefix_key.replace("dynnp_", "").rstrip("_")

                is_fictional = looks_fictional(name_key, culture)
                if is_fictional:
                    fictional += 1

                record = {
                    "game": "ck3",
                    "type": "dynasty",
                    "id": str(key),
                    "name_key": name_key,
                    "names": names,
                    "name_en": names.get("english"),
                    "name_ko": names.get("korean"),
                    "name_zh": names.get("simp_chinese"),
                    "name_ru": names.get("russian"),
                    "culture": culture,
                    "iso_country_hint": iso,
                    "region_hint": region,
                    "prefix": prefix_val,
                    "motto": body.get("motto") if isinstance(body.get("motto"), str) else None,
                    "fictional": is_fictional,
                    "source_repo": source_repo,
                    "source_file": str(txt_path.relative_to(repo_root)),
                }
                fp.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1

    return {
        "count": count,
        "fictional": fictional,
        "no_english_name": no_name_loc,
        "loc_coverage": dict(loc_counts),
    }


def extract_ck3_houses(repo_root: Path, out_path: Path, source_repo: str,
                       langs: list[str]) -> dict:
    """Parse CK3 dynasty_houses files and emit JSONL."""
    h_dir = repo_root / "common" / "dynasty_houses"
    if not h_dir.exists():
        return {"error": "no dynasty_houses dir"}

    loc = {}
    for lang in langs:
        loc[lang] = load_loc_dir(repo_root / "localization" / lang)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    loc_counts = defaultdict(int)
    with out_path.open("w", encoding="utf-8") as fp:
        for txt_path in sorted(h_dir.glob("*.txt")):
            try:
                text = txt_path.read_text(encoding="utf-8-sig", errors="replace")
                tree = parse_pdx(text)
            except Exception as e:
                print(f"  ! parse failed: {txt_path}: {e}", file=sys.stderr)
                continue
            for key, body in tree.items():
                if not isinstance(body, dict):
                    continue
                name_key = body.get("name")
                if isinstance(name_key, list):
                    name_key = name_key[0] if name_key else None
                prefix_key = body.get("prefix")
                if isinstance(prefix_key, list):
                    prefix_key = prefix_key[0] if prefix_key else None
                dynasty_id = body.get("dynasty")
                if isinstance(dynasty_id, list):
                    dynasty_id = dynasty_id[0] if dynasty_id else None

                names = {}
                for lang in langs:
                    n = resolve_loc(name_key, loc[lang])
                    if n is not None:
                        names[lang] = n
                        loc_counts[lang] += 1
                if "english" not in names and name_key and not name_key.startswith("dynn"):
                    names["english"] = name_key

                prefix_val = None
                if prefix_key:
                    prefix_val = resolve_loc(prefix_key, loc.get("english", {})) or prefix_key.replace("dynnp_", "").rstrip("_")

                record = {
                    "game": "ck3",
                    "type": "dynasty_house",
                    "id": str(key),
                    "name_key": name_key,
                    "names": names,
                    "name_en": names.get("english"),
                    "name_ko": names.get("korean"),
                    "name_zh": names.get("simp_chinese"),
                    "name_ru": names.get("russian"),
                    "dynasty_id": str(dynasty_id) if dynasty_id else None,
                    "prefix": prefix_val,
                    "source_repo": source_repo,
                    "source_file": str(txt_path.relative_to(repo_root)),
                }
                fp.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1

    return {"count": count, "loc_coverage": dict(loc_counts)}


# ---------------------------------------------------------------------------
# CK2 extractor
# ---------------------------------------------------------------------------

def extract_ck2_dynasties(repo_root: Path, out_path: Path, source_repo: str,
                          fictional_marker: bool = False,
                          dyn_subpath: str = "common/dynasties") -> dict:
    """CK2: dynasty files keyed by int, with `name="..."` literal.

    Localization is gettext-style CSV in localisation/ — we can join later if
    needed but CK2 vanilla stores the name directly in the dynasty record.

    CK2 files are encoded in Windows-1252 / latin-1, NOT UTF-8.
    """
    dyn_dir = repo_root / dyn_subpath
    if not dyn_dir.exists():
        return {"error": f"no {dyn_subpath} dir"}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    fict = 0
    # CK2 files are typically Windows-1252 encoded
    with out_path.open("w", encoding="utf-8") as fp:
        for txt_path in sorted(dyn_dir.glob("*.txt")):
            if txt_path.stem.upper() == "RANGES":
                continue
            try:
                raw = txt_path.read_bytes()
                # Try utf-8 first, fall back to cp1252
                try:
                    text = raw.decode("utf-8-sig")
                except UnicodeDecodeError:
                    text = raw.decode("cp1252", errors="replace")
                tree = parse_pdx(text)
            except Exception as e:
                print(f"  ! parse failed: {txt_path}: {e}", file=sys.stderr)
                continue
            file_marker = fictional_marker or (txt_path.stem.lower() not in ("00_dynasties",))
            for key, body in tree.items():
                if not isinstance(body, dict):
                    continue
                name = body.get("name")
                if isinstance(name, list):
                    name = name[0] if name else None
                culture = body.get("culture")
                if isinstance(culture, list):
                    culture = culture[0] if culture else None
                religion = body.get("religion")
                if isinstance(religion, list):
                    religion = religion[0] if religion else None
                if file_marker:
                    fict += 1
                record = {
                    "game": "ck2",
                    "type": "dynasty",
                    "id": str(key),
                    "name_en": name,
                    "culture": culture,
                    "religion": religion,
                    "fictional": file_marker,
                    "source_repo": source_repo,
                    "source_file": str(txt_path.relative_to(repo_root)),
                }
                fp.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
    return {"count": count, "fictional": fict}


# ---------------------------------------------------------------------------
# EU4 extractor
# ---------------------------------------------------------------------------

def extract_eu4_countries_multi(auth_root: Path, all_roots: list[Path], out_path: Path, sources: list[str]) -> dict:
    """Build the union: tag-table from auth_root, country-file data merged from all_roots."""
    tags_path = auth_root / "common" / "country_tags" / "00_countries.txt"
    if not tags_path.exists():
        return {"error": "no 00_countries.txt"}
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def _read(p: Path) -> str:
        raw = p.read_bytes()
        try:
            return raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            return raw.decode("cp1252", errors="replace")

    text = _read(tags_path)
    tag_re = re.compile(r'^\s*([A-Z0-9]{3})\s*=\s*"([^"]+)"', re.MULTILINE)
    count = 0
    enriched = 0
    with out_path.open("w", encoding="utf-8") as fp:
        for m in tag_re.finditer(text):
            tag = m.group(1)
            file_rel = m.group(2)
            data = {}
            data_source = None
            for root, src in zip(all_roots, sources):
                cf = root / "common" / file_rel
                if cf.exists():
                    try:
                        tree = parse_pdx(_read(cf))
                        if isinstance(tree, dict) and tree:
                            data = tree
                            data_source = src
                            break
                    except Exception:
                        pass
            if data:
                enriched += 1
            record = {
                "game": "eu4",
                "type": "country",
                "tag": tag,
                "name_file": file_rel,
                "graphical_culture": data.get("graphical_culture") if data else None,
                "color": data.get("color") if data else None,
                "historical_idea_groups": data.get("historical_idea_groups") if data else None,
                "monarch_names_keys": list(data.get("monarch_names", {}).keys()) if isinstance(data.get("monarch_names"), dict) else None,
                "country_data_source": data_source,
                "source_repo": sources[0],
                "source_file": "common/country_tags/00_countries.txt",
            }
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return {"count": count, "with_country_data": enriched}


def extract_eu4_countries(repo_root: Path, out_path: Path, source_repo: str) -> dict:
    """EU4 `common/country_tags/00_countries.txt` -> map tag -> file.

    Then `common/countries/<File>.txt` has per-country details.  We emit one
    JSONL row per tag with the file's metadata.
    """
    tags_path = repo_root / "common" / "country_tags" / "00_countries.txt"
    countries_dir = repo_root / "common" / "countries"
    if not tags_path.exists():
        return {"error": "no 00_countries.txt"}

    # Parse the tag table - it's tag = "file.txt" pairs
    out_path.parent.mkdir(parents=True, exist_ok=True)
    def _read(path):
        raw = path.read_bytes()
        try:
            return raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            return raw.decode("cp1252", errors="replace")
    text = _read(tags_path)
    tag_re = re.compile(r'^\s*([A-Z0-9]{3})\s*=\s*"([^"]+)"', re.MULTILINE)
    count = 0
    with out_path.open("w", encoding="utf-8") as fp:
        for m in tag_re.finditer(text):
            tag = m.group(1)
            file_rel = m.group(2)
            country_file = repo_root / "common" / file_rel
            data = {}
            if country_file.exists():
                try:
                    ctext = _read(country_file)
                    tree = parse_pdx(ctext)
                    data = tree if isinstance(tree, dict) else {}
                except Exception:
                    data = {}
            record = {
                "game": "eu4",
                "type": "country",
                "tag": tag,
                "name_file": file_rel,
                "graphical_culture": data.get("graphical_culture"),
                "color": data.get("color"),
                "historical_idea_groups": data.get("historical_idea_groups"),
                "monarch_names_keys": list(data.get("monarch_names", {}).keys()) if isinstance(data.get("monarch_names"), dict) else None,
                "source_repo": source_repo,
                "source_file": str(tags_path.relative_to(repo_root)),
            }
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return {"count": count}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    repos = {
        "ck3_vanilla": Path("/tmp/paradox_repos/ck3_vanilla"),
        "ck2_elder_kings": Path("/tmp/paradox_repos/ck2_elder_kings"),
        "ck3_kingdom_heaven": Path("/tmp/paradox_repos/kingdom_heaven"),
    }
    out_root = Path("/Users/sidewalkai2/Claude/royal-tree/data/raw")

    # Write the culture->country CSV
    csv_path = Path("/Users/sidewalkai2/Claude/royal-tree/scripts/normalize/ck3_culture_to_country.csv")
    write_culture_csv(csv_path)
    print(f"[normalize] wrote culture mapping CSV: {csv_path}")

    summary: dict = {}

    # CK3
    if repos["ck3_vanilla"].exists():
        print("[ck3] extracting dynasties ...")
        s = extract_ck3_dynasties(
            repos["ck3_vanilla"],
            out_root / "ck3" / "dynasties.jsonl",
            "mgp1212121212/ck3_vanilla",
            langs=["english", "korean", "simp_chinese", "russian", "french", "german", "spanish", "polish"],
        )
        summary["ck3_dynasties"] = s
        print(f"  -> {s}")

        print("[ck3] extracting dynasty_houses ...")
        s = extract_ck3_houses(
            repos["ck3_vanilla"],
            out_root / "ck3" / "houses.jsonl",
            "mgp1212121212/ck3_vanilla",
            langs=["english", "korean", "simp_chinese", "russian", "french", "german", "spanish", "polish"],
        )
        summary["ck3_houses"] = s
        print(f"  -> {s}")

    # CK3 Kingdom of Heaven enrichment (Mediterranean/Levantine focus, SWMH submods)
    if repos["ck3_kingdom_heaven"].exists():
        print("[ck3-KoH] extracting Kingdom of Heaven enrichment dynasties ...")
        s = extract_ck3_dynasties(
            repos["ck3_kingdom_heaven"],
            out_root / "ck3" / "dynasties_kingdom_heaven_all.jsonl",
            "UberEpicZach/The-Kingdom-of-Heaven",
            langs=["english"],
        )
        summary["ck3_kingdom_heaven_dynasties_all"] = s
        print(f"  -> all count={s.get('count')}, no_english_name={s.get('no_english_name')}")

        # Now write a filtered file: only entries that have a resolved English
        # name (i.e. new SWMH/KoH additions with literal names). The rest are
        # vanilla loc-key references that we already have in ck3 vanilla.
        all_path = out_root / "ck3" / "dynasties_kingdom_heaven_all.jsonl"
        delta_path = out_root / "ck3" / "dynasties_kingdom_heaven.jsonl"
        kept = 0
        with all_path.open() as src, delta_path.open("w", encoding="utf-8") as dst:
            for line in src:
                r = json.loads(line)
                if r.get("name_en"):
                    dst.write(line)
                    kept += 1
        all_path.unlink()  # remove the intermediate
        summary["ck3_kingdom_heaven_dynasties"] = {"count": kept, "note": "delta-only, vanilla refs filtered out"}
        print(f"  -> kept delta with English names: {kept}")

    # EU4 vanilla - merge from multiple mod sources for best coverage
    eu4_sources = [
        (Path("/tmp/paradox_repos/eu4_rtoe"), "JakubOwadowski/RTOE"),
        (Path("/tmp/paradox_repos/eu4_tomato"), "tomato747/eu4tomatomod"),
    ]
    # We use the source with the largest country_tags table as authoritative,
    # then enrich by trying all country_files dirs.
    best_root = None
    best_count = 0
    for root, _ in eu4_sources:
        tags = root / "common" / "country_tags" / "00_countries.txt"
        if tags.exists():
            n = sum(1 for _ in tags.read_bytes().splitlines() if _.strip() and not _.lstrip().startswith(b"#"))
            if n > best_count:
                best_count = n
                best_root = root
    if best_root is not None:
        print(f"[eu4] extracting EU4 historical countries (auth source: {best_root.name}) ...")
        s = extract_eu4_countries_multi(
            best_root,
            [r for r, _ in eu4_sources],
            out_root / "eu4" / "countries.jsonl",
            [src for _, src in eu4_sources],
        )
        summary["eu4_countries"] = s
        print(f"  -> {s}")

    # CK2 vanilla (via Community Patch reference files)
    ck2_vanilla_root = Path("/tmp/paradox_repos/ck2_jonjowett/community_patch_personalised/reference_files/community_patch")
    if ck2_vanilla_root.exists():
        print("[ck2] extracting Community Patch / CK2 vanilla dynasties ...")
        s = extract_ck2_dynasties(
            ck2_vanilla_root,
            out_root / "ck2" / "dynasties.jsonl",
            "jonjowett/ck2_mods (community_patch ref)",
            fictional_marker=False,
        )
        summary["ck2_vanilla_dynasties"] = s
        print(f"  -> {s}")

    # CK2 Elder Kings (fictional TES total conversion - flagged)
    if repos["ck2_elder_kings"].exists():
        print("[ck2] extracting Elder Kings dynasties (FICTIONAL TES total conversion) ...")
        s = extract_ck2_dynasties(
            repos["ck2_elder_kings"],
            out_root / "ck2" / "dynasties_elder_kings.jsonl",
            "jjsfw-jumbi/elder-kings-ck2",
            fictional_marker=True,
        )
        summary["ck2_elder_kings"] = s
        print(f"  -> {s}")

    print("\n========== SUMMARY ==========")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
