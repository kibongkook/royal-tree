#!/usr/bin/env python3
"""
Europe + Americas + Global Business Dynasties — manual curated list.

Scope:
  - Currently reigning European royal houses
  - Deposed European royal houses (pretender lines still active)
  - Major noble houses by country (UK, FR, DE, IT, ES, RU, PL, HU, Scandinavia, ...)
  - Americas: USA political+business dynasties, Latin American criollo + business,
    Canadian business dynasties
  - Global business dynasties (multinational)

Output: data/raw/manual/europe_americas_business_families.jsonl
Schema matches project master schema (CLAUDE.md). Each family record:
{
  "id": "Q...",                       # Wikidata QID if found, else royals:<slug>
  "names": {"en": "..."},             # English label (others added if returned by search)
  "country": ["GB", "..."],           # ISO 3166-1 alpha-2 codes
  "category": "royal|noble|business|political|religious",
  "subcategory": "reigning|deposed|pretender|hereditary-peerage|black-nobility|criollo|tycoon|...",
  "status": "active|extinct|deposed|merged",
  "period": {"founded": <int|null>, "extinct": <int|null>},
  "head_current": <str|null>,         # name; QID lookup deferred
  "notes": "...",
  "sources": ["manual:europe_americas_business"],
  "search_query": "...",              # query used for Wikidata search
  "wikidata_search": {                # raw search result snippet
    "qid": "Q...",
    "label": "...",
    "description": "..."
  }
}

QIDs are filled via Wikidata's wbsearchentities API, run in parallel.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "raw" / "manual"
OUT_FILE = OUT_DIR / "europe_americas_business_families.jsonl"
STATS_FILE = OUT_DIR / "europe_americas_business_stats.tsv"

UA = "Royals-research/0.1 (kibongkook@gmail.com)"

# ---------------------------------------------------------------------------
# Family list. Format: tuples of
#   (search_query, [country_codes], category, subcategory, status,
#    founded, extinct, head_current, notes)
# search_query is what we hand to Wikidata wbsearchentities.
# We deliberately use the English Wikipedia-style name to maximise hit rate.
# ---------------------------------------------------------------------------

FAMILIES: list[tuple] = []


def add(query, countries, category, subcategory, status,
        founded=None, extinct=None, head=None, notes=""):
    FAMILIES.append((query, countries, category, subcategory, status,
                     founded, extinct, head, notes))


# ===========================================================================
# 1. Currently reigning European royal houses
# ===========================================================================
add("House of Windsor", ["GB"], "royal", "reigning", "active",
    1917, None, "Charles III",
    "UK + Commonwealth realms; renamed from Saxe-Coburg-Gotha 1917.")
add("Glücksburg dynasty Norway", ["NO"], "royal", "reigning", "active",
    1905, None, "Harald V",
    "Norwegian branch of Glücksburg (Schleswig-Holstein-Sonderburg-Glücksburg).")
add("House of Bernadotte", ["SE"], "royal", "reigning", "active",
    1818, None, "Carl XVI Gustaf",
    "Sweden; founded by Jean-Baptiste Bernadotte (Napoleonic marshal).")
add("Glücksburg dynasty Denmark", ["DK"], "royal", "reigning", "active",
    1863, None, "Frederik X",
    "Danish branch of Glücksburg.")
add("House of Orange-Nassau", ["NL"], "royal", "reigning", "active",
    1544, None, "Willem-Alexander",
    "Netherlands; descended from William the Silent.")
add("House of Belgium", ["BE"], "royal", "reigning", "active",
    1831, None, "Philippe",
    "Belgian branch of Saxe-Coburg-Gotha (renamed 'of Belgium' WWI).")
add("House of Nassau-Weilburg", ["LU"], "royal", "reigning", "active",
    1255, None, "Henri",
    "Luxembourg.")
add("House of Liechtenstein", ["LI"], "royal", "reigning", "active",
    1140, None, "Hans-Adam II",
    "Princely house of Liechtenstein; Hans-Adam II nominal, Alois regent.")
add("House of Grimaldi", ["MC"], "royal", "reigning", "active",
    1297, None, "Albert II",
    "Monaco; Genoese-origin family.")
add("House of Bourbon-Anjou", ["ES"], "royal", "reigning", "active",
    1700, None, "Felipe VI",
    "Spain; current Spanish Bourbon branch.")
# Andorra co-princes (not a family, but document slots)
add("Roman Catholic Diocese of Urgell", ["AD", "ES"], "religious", "co-prince-andorra", "active",
    1133, None, "Joan-Enric Vives Sicília",
    "Andorran co-prince: Bishop of Urgell (Spanish side).")
add("President of France", ["AD", "FR"], "political", "co-prince-andorra", "active",
    1278, None, "Emmanuel Macron",
    "Andorran co-prince: French head of state (institutional, not a family).")

# Vatican papal-noble Roman families (Black Nobility)
add("House of Borghese", ["IT", "VA"], "noble", "black-nobility", "active",
    1530, None, "Scipione Borghese",
    "Papal nobility; Pope Paul V's family.")
add("Pamphili family", ["IT", "VA"], "noble", "black-nobility", "active",
    1461, None, "Jonathan Doria Pamphilj",
    "Papal nobility; Pope Innocent X's family; merged with Doria as Doria Pamphilj Landi.")
add("House of Colonna", ["IT", "VA"], "noble", "black-nobility", "active",
    1100, None, "Prospero Colonna di Paliano",
    "Roman dynasty; Pope Martin V.")
add("House of Orsini", ["IT", "VA"], "noble", "black-nobility", "active",
    1100, None, "Domenico Napoleone Orsini",
    "Roman dynasty; multiple popes including Celestine III, Nicholas III, Benedict XIII.")
add("Barberini family", ["IT", "VA"], "noble", "black-nobility", "active",
    1530, None, None,
    "Pope Urban VIII; merged with Colonna-Sciarra.")
add("Chigi family", ["IT", "VA"], "noble", "black-nobility", "active",
    1377, None, "Mario Chigi-Albani della Rovere",
    "Pope Alexander VII; Chigi Albani della Rovere line.")
add("Aldobrandini family", ["IT", "VA"], "noble", "black-nobility", "active",
    1500, None, None, "Pope Clement VIII.")
add("Ludovisi family", ["IT", "VA"], "noble", "black-nobility", "active",
    1500, None, "Nicolò Boncompagni Ludovisi",
    "Pope Gregory XV; merged with Boncompagni.")
add("Boncompagni family", ["IT", "VA"], "noble", "black-nobility", "active",
    1500, None, None, "Pope Gregory XIII.")
add("Rospigliosi family", ["IT", "VA"], "noble", "black-nobility", "active",
    1300, None, None, "Pope Clement IX.")
add("Pallavicini family", ["IT"], "noble", "black-nobility", "active",
    900, None, None, "Pallavicini marquesses; survives via Pallavicini-Rospigliosi.")
add("Caetani family", ["IT", "VA"], "noble", "black-nobility", "active",
    1100, None, None, "Pope Boniface VIII; Sermoneta dukes.")
add("House of Massimo", ["IT", "VA"], "noble", "black-nobility", "active",
    1000, None, "Fabrizio Massimo-Brancaccio",
    "One of the oldest Roman families.")
add("Torlonia family", ["IT"], "noble", "papal-finance", "active",
    1750, None, "Alessandro Torlonia",
    "Banking family; Princes of Civitella-Cesi.")
add("Ruspoli family", ["IT"], "noble", "black-nobility", "active",
    1400, None, "Francesco Ruspoli", "Princes of Cerveteri.")

# ===========================================================================
# 2. Deposed / pretender European royal houses (still active claimants)
# ===========================================================================
add("House of Orléans", ["FR"], "royal", "deposed-pretender", "deposed",
    1830, None, "Jean d'Orléans",
    "Orléanist claimant to French throne ('Comte de Paris').")
add("House of Bourbon (French Legitimist)", ["FR", "ES"], "royal", "deposed-pretender", "deposed",
    987, None, "Louis Alphonse de Bourbon",
    "Legitimist (Carlist-derived) claimant; Duke of Anjou.")
add("House of Bonaparte", ["FR"], "royal", "deposed-pretender", "deposed",
    1804, None, "Jean-Christophe Napoléon",
    "Bonapartist claimant.")
add("House of Hohenzollern", ["DE"], "royal", "deposed-pretender", "deposed",
    1061, None, "Georg Friedrich, Prince of Prussia",
    "Prussian Hohenzollern; head since 1994.")
add("House of Habsburg-Lorraine", ["AT", "HU"], "royal", "deposed-pretender", "deposed",
    1736, None, "Karl von Habsburg",
    "Austria-Hungary; Karl von Habsburg is current head.")
add("House of Romanov", ["RU"], "royal", "deposed-pretender", "deposed",
    1613, 1918, "Maria Vladimirovna",
    "Romanov; Kirillovich claim. Disputed by Romanov Family Association (Andrew Andreevich line, now Alexis Andreevich).")
add("Romanov Family Association", ["RU"], "royal", "deposed-pretender", "deposed",
    1979, None, "Alexis Andreevich Romanov",
    "Rival pretender body to Maria Vladimirovna's Kirillovich line.")
add("House of Savoy", ["IT"], "royal", "deposed-pretender", "deposed",
    1003, None, "Vittorio Emanuele / Aimone",
    "Italy main line; succession disputed between Vittorio Emanuele and Aimone Duke of Aosta.")
add("House of Bourbon-Two Sicilies", ["IT"], "royal", "deposed-pretender", "deposed",
    1734, None, "Pedro, Duke of Calabria / Carlo, Duke of Castro",
    "Disputed: Spanish (Pedro) vs. Franco-Neapolitan (Carlo) branches.")
add("House of Saxe-Coburg and Gotha Bulgaria", ["BG"], "royal", "deposed-pretender", "deposed",
    1887, None, "Simeon II",
    "Bulgaria; Simeon Sakskoburggotski, alive as of 2026; later served as PM 2001-05.")
add("House of Hohenzollern-Sigmaringen Romania", ["RO"], "royal", "deposed-pretender", "deposed",
    1866, None, "Margareta",
    "Romania; Margareta of Romania is Custodian of the Crown.")
add("Glücksburg dynasty Greece", ["GR"], "royal", "deposed-pretender", "deposed",
    1863, 1973, "Pavlos, Crown Prince of Greece",
    "Greece abolished monarchy 1973; Constantine II died 2023; son Pavlos.")
add("House of Karađorđević", ["RS"], "royal", "deposed-pretender", "deposed",
    1842, None, "Alexander, Crown Prince of Serbia",
    "Serbia / Yugoslavia.")
add("House of Petrović-Njegoš", ["ME"], "royal", "deposed-pretender", "deposed",
    1696, None, "Nikola II Petrović-Njegoš",
    "Montenegro.")
add("House of Braganza", ["PT", "BR"], "royal", "deposed-pretender", "deposed",
    1442, None, "Duarte Pio, Duke of Braganza",
    "Portuguese pretender; Brazilian branch separate (Orléans-Braganza).")
add("Orléans-Braganza", ["BR"], "royal", "deposed-pretender", "deposed",
    1864, None, "Bertrand of Orléans-Braganza / Luiz Gastão",
    "Brazilian imperial pretenders; Vassouras vs. Petrópolis branches.")
add("House of Zogu", ["AL"], "royal", "deposed-pretender", "deposed",
    1928, 1946, "Leka II",
    "Albania; Leka II Crown Prince.")
add("Habsburg-Lorraine Hungary", ["HU"], "royal", "deposed-pretender", "deposed",
    1867, 1918, "Karl von Habsburg",
    "Hungarian crown (shared head with Austrian line).")
add("House of Lubomirski", ["PL"], "noble", "polish-magnate-pretender", "active",
    1300, None, None,
    "Polish magnate; sometimes mooted as a constitutional-monarchy candidate house.")
add("House of Wittelsbach", ["DE"], "royal", "deposed-pretender", "deposed",
    1180, None, "Franz, Duke of Bavaria",
    "Bavarian crown; also Jacobite claimant to UK throne.")
add("House of Wettin (Saxe)", ["DE"], "royal", "deposed-pretender", "deposed",
    1089, None, "Daniel, Margrave of Meissen / Alexander, Margrave",
    "Saxon Wettin; succession disputed.")
add("Albertine Wettin Saxony", ["DE"], "royal", "deposed-pretender", "deposed",
    1485, None, None, "Albertine line, Kingdom of Saxony.")
add("House of Welf", ["DE"], "royal", "deposed-pretender", "deposed",
    819, None, "Ernst August, Prince of Hanover",
    "Hannover/Brunswick; also UK claim via House of Hanover (pre-1901).")
add("House of Hesse", ["DE"], "royal", "deposed-pretender", "deposed",
    1264, None, "Donatus, Landgrave of Hesse",
    "Hesse-Kassel + Hesse-Darmstadt merged 1968.")
add("House of Baden", ["DE"], "royal", "deposed-pretender", "deposed",
    1112, None, "Bernhard, Margrave of Baden",
    "Grand Duchy of Baden.")
add("House of Württemberg", ["DE"], "royal", "deposed-pretender", "deposed",
    1083, None, "Carl, Duke of Württemberg",
    "Kingdom of Württemberg.")
add("House of Thurn und Taxis", ["DE"], "noble", "mediatized", "active",
    1248, None, "Albert, 12th Prince of Thurn and Taxis",
    "Founders of European postal system; Regensburg-based.")
add("House of Fürstenberg", ["DE"], "noble", "mediatized", "active",
    1080, None, "Heinrich, Prince of Fürstenberg", None)
add("House of Saxe-Coburg and Gotha", ["DE", "GB", "BE", "BG"], "royal", "multinational-royal", "active",
    1826, None, "Andreas, Prince of Saxe-Coburg and Gotha",
    "Parent house of UK Windsors (pre-1917), Belgian royals, Bulgarian royals, Portuguese kings.")
add("Princely House of Solms", ["DE"], "noble", "mediatized", "active",
    1129, None, None, "Multiple branches: Solms-Hohensolms-Lich, Solms-Braunfels, etc.")
add("House of Stolberg", ["DE"], "noble", "mediatized", "active",
    1210, None, None, "Stolberg-Stolberg, Stolberg-Wernigerode, etc.")
add("House of Reuss", ["DE"], "noble", "mediatized", "active",
    1010, None, "Heinrich XIV, Prince Reuss",
    "Notable for naming every male 'Heinrich' numbered cyclically.")

# ===========================================================================
# 3. UK noble houses (major peerage families — focus on Dukedoms + Marquessates
#    and the politically/historically prominent families).
# ===========================================================================
add("Howard family", ["GB"], "noble", "uk-ducal", "active",
    1300, None, "Edward Fitzalan-Howard, 18th Duke of Norfolk",
    "Duke of Norfolk (premier duke + Earl Marshal); also Earls of Suffolk, Carlisle, Effingham.")
add("Cavendish family", ["GB"], "noble", "uk-ducal", "active",
    1500, None, "Peregrine Cavendish, 12th Duke of Devonshire",
    "Duke of Devonshire; Chatsworth.")
add("Russell family", ["GB"], "noble", "uk-ducal", "active",
    1500, None, "Andrew Russell, 15th Duke of Bedford",
    "Duke of Bedford; Woburn Abbey. Bertrand Russell was a member of cadet line.")
add("Cecil family", ["GB"], "noble", "uk-marquessal", "active",
    1500, None, "Robert Cecil, 7th Marquess of Salisbury",
    "Marquess of Salisbury (Hatfield) + Marquess of Exeter (Burghley). Two PMs in 19c.")
add("Spencer family", ["GB"], "noble", "uk-earldom", "active",
    1500, None, "Charles Spencer, 9th Earl Spencer",
    "Earl Spencer; family of Princess Diana; ancestral seat Althorp.")
add("Spencer-Churchill family", ["GB"], "noble", "uk-ducal", "active",
    1700, None, "Jamie Spencer-Churchill, 12th Duke of Marlborough",
    "Duke of Marlborough; Blenheim Palace; Sir Winston Churchill's family.")
add("Stanley family", ["GB"], "noble", "uk-earldom", "active",
    1300, None, "Edward Stanley, 19th Earl of Derby",
    "Earl of Derby; Knowsley.")
add("Percy family", ["GB"], "noble", "uk-ducal", "active",
    1067, None, "Ralph Percy, 12th Duke of Northumberland",
    "Duke of Northumberland; Alnwick Castle.")
add("Grosvenor family", ["GB"], "noble", "uk-ducal", "active",
    1066, None, "Hugh Grosvenor, 7th Duke of Westminster",
    "Duke of Westminster; one of the wealthiest UK landholders (Mayfair, Belgravia).")
add("Sackville-West family", ["GB"], "noble", "uk-barony", "active",
    1500, None, "Robert Sackville-West, 7th Baron Sackville",
    "Knole; Vita Sackville-West literary.")
add("Lascelles family", ["GB"], "noble", "uk-earldom", "active",
    1700, None, "David Lascelles, 8th Earl of Harewood",
    "Earl of Harewood; royal cadet via Princess Mary.")
add("Mountbatten-Windsor", ["GB"], "royal", "reigning-cadet", "active",
    1960, None, None,
    "Cadet branch surname of UK royal family.")
add("Bowes-Lyon family", ["GB"], "noble", "uk-earldom", "active",
    1600, None, "Simon Bowes-Lyon, 19th Earl of Strathmore and Kinghorne",
    "Family of the late Queen Mother Elizabeth.")
add("FitzRoy family", ["GB"], "noble", "uk-ducal", "active",
    1663, None, "Henry FitzRoy, 12th Duke of Grafton",
    "Duke of Grafton; Charles II illegitimate descent.")
add("Lennox family", ["GB"], "noble", "uk-ducal", "active",
    1675, None, "Charles Gordon-Lennox, 11th Duke of Richmond",
    "Duke of Richmond, Lennox & Gordon; Goodwood.")
add("Manners family", ["GB"], "noble", "uk-ducal", "active",
    1500, None, "David Manners, 11th Duke of Rutland",
    "Duke of Rutland; Belvoir Castle.")
add("Seymour family", ["GB"], "noble", "uk-ducal", "active",
    1500, None, "John Seymour, 19th Duke of Somerset",
    "Duke of Somerset; Jane Seymour's family.")
add("Hamilton family", ["GB"], "noble", "uk-ducal", "active",
    1300, None, "Alexander Douglas-Hamilton, 16th Duke of Hamilton",
    "Premier peer of Scotland.")
add("Campbell family of Argyll", ["GB"], "noble", "uk-ducal", "active",
    1200, None, "Torquhil Campbell, 13th Duke of Argyll",
    "Inveraray; Scottish premier ducal house.")
add("Gordon family", ["GB"], "noble", "uk-ducal", "active",
    1300, None, "Granville Gordon, 13th Marquess of Huntly",
    "Marquess of Huntly (premier marquess of Scotland).")
add("Murray family of Atholl", ["GB"], "noble", "uk-ducal", "active",
    1600, None, "Bruce Murray, 12th Duke of Atholl",
    "Blair Castle; private army (Atholl Highlanders).")
add("Bruce family of Elgin", ["GB"], "noble", "uk-earldom", "active",
    1300, None, "Andrew Bruce, 11th Earl of Elgin",
    "Earls of Elgin & Kincardine; Robert the Bruce descent.")
add("Wellesley family", ["GB"], "noble", "uk-ducal", "active",
    1700, None, "Charles Wellesley, 9th Duke of Wellington",
    "Wellington's family.")
add("Stuart family of Bute", ["GB"], "noble", "uk-marquessal", "active",
    1300, None, "John Crichton-Stuart, 8th Marquess of Bute",
    "Mount Stuart; royal Stuart cadet.")
add("Compton family", ["GB"], "noble", "uk-marquessal", "active",
    1500, None, "Spencer Compton, 7th Marquess of Northampton", None)
add("Curzon family", ["GB"], "noble", "uk-marquessal", "active",
    1200, None, "Richard Curzon, 8th Earl Howe",
    "Lord Curzon Viceroy of India was head.")
add("Lygon family", ["GB"], "noble", "uk-earldom", "active",
    1700, None, None, "Earls Beauchamp.")
add("Marquess of Bath", ["GB"], "noble", "uk-marquessal", "active",
    1700, None, "Ceawlin Thynn, 8th Marquess of Bath",
    "Thynne family; Longleat.")
add("Compton-Burnett family", ["GB"], "noble", "uk-literary", "extinct",
    1800, None, None, "Notable line, mainly literary.")

# UK 24 Dukedoms — cover the remaining ones not yet listed
add("Duke of Cornwall", ["GB"], "royal", "uk-ducal", "active",
    1337, None, "William, Prince of Wales", "Held by heir apparent.")
add("Duke of Lancaster", ["GB"], "royal", "uk-ducal", "active",
    1351, None, "Charles III", "Held by the sovereign.")
add("Duke of Rothesay", ["GB"], "royal", "uk-ducal", "active",
    1398, None, "William, Prince of Wales", "Scottish heir apparent title.")
add("Duke of Buccleuch", ["GB"], "noble", "uk-ducal", "active",
    1663, None, "Richard Scott, 10th Duke of Buccleuch",
    "Scott family; largest private landowner in Scotland.")
add("Duke of St Albans", ["GB"], "noble", "uk-ducal", "active",
    1684, None, "Murray Beauclerk, 14th Duke of St Albans",
    "Beauclerk family; Charles II illegitimate descent (Nell Gwynne).")
add("Duke of Leinster", ["IE", "GB"], "noble", "irish-ducal", "active",
    1766, None, "Maurice FitzGerald, 9th Duke of Leinster",
    "Premier duke of Ireland.")
add("Duke of Abercorn", ["GB", "IE"], "noble", "uk-ducal", "active",
    1868, None, "James Hamilton, 5th Duke of Abercorn", None)
add("Duke of Sutherland", ["GB"], "noble", "uk-ducal", "active",
    1833, None, "Francis Egerton, 7th Duke of Sutherland", None)
add("Duke of Westminster", ["GB"], "noble", "uk-ducal", "active",
    1874, None, "Hugh Grosvenor", "Redundant w/ Grosvenor entry.")
add("Duke of Fife", ["GB"], "noble", "uk-ducal", "active",
    1900, None, "David Carnegie, 4th Duke of Fife",
    "Carnegie family; royal descent via Princess Louise.")

# Scottish clan chiefs (chiefs of Name and Arms)
add("Clan MacLeod", ["GB-SCT"], "clan", "scottish-clan", "active",
    1200, None, "Hugh MacLeod of MacLeod", "Dunvegan; clan chief.")
add("Clan Donald", ["GB-SCT"], "clan", "scottish-clan", "active",
    1100, None, "Godfrey MacDonald of MacDonald, High Chief",
    "Largest Scottish clan; Lord MacDonald of Sleat / Clanranald branches.")
add("Clan Mackenzie", ["GB-SCT"], "clan", "scottish-clan", "active",
    1200, None, "John Mackenzie, Earl of Cromartie", None)
add("Clan Fraser", ["GB-SCT"], "clan", "scottish-clan", "active",
    1100, None, "Simon Fraser, 25th Lord Lovat",
    "Fraser of Lovat; Highland clan.")
add("Clan Sinclair", ["GB-SCT"], "clan", "scottish-clan", "active",
    1100, None, "Malcolm Sinclair, 20th Earl of Caithness", None)

# ===========================================================================
# 4. France — Almanach de Gotha houses
# ===========================================================================
add("House of La Rochefoucauld", ["FR"], "noble", "french-ducal", "active",
    1019, None, None, "Dukes of La Rochefoucauld; Princes of Marcillac.")
add("House of Noailles", ["FR"], "noble", "french-ducal", "active",
    1230, None, "Hélie de Noailles, 9th Duke of Mouchy",
    "Dukes of Mouchy, of Noailles, of Ayen.")
add("House of Polignac", ["FR", "MC"], "noble", "french-ducal", "active",
    860, None, "Armand de Polignac",
    "Princes of Polignac; closely linked to Grimaldis of Monaco.")
add("House of Cossé-Brissac", ["FR"], "noble", "french-ducal", "active",
    1100, None, "Charles-André de Cossé-Brissac, 13th Duke of Brissac", None)
add("House of La Croix de Castries", ["FR"], "noble", "french-ducal", "active",
    1200, None, "Henri de La Croix de Castries", "Dukes of Castries.")
add("House of Choiseul", ["FR"], "noble", "french-ducal", "active",
    1060, None, None, "Dukes of Choiseul-Praslin etc.")
add("House of Crussol d'Uzès", ["FR"], "noble", "french-ducal", "active",
    1000, None, "Jacques de Crussol, 17th Duke of Uzès",
    "Premier duke of France.")
add("House of Gramont", ["FR"], "noble", "french-ducal", "active",
    1200, None, "Antoine de Gramont, 14th Duke of Gramont", None)
add("House of Harcourt", ["FR"], "noble", "french-ducal", "active",
    1000, None, None, "Norman ducal family; British Harcourt cadets.")
add("House of Montmorency", ["FR", "BE"], "noble", "french-ducal", "active",
    1000, None, None, "Dukes of Montmorency; Belgian branch survives.")
add("House of Rochechouart-Mortemart", ["FR"], "noble", "french-ducal", "active",
    1000, None, "Jean de Rochechouart-Mortemart, 14th Duke of Mortemart", None)
add("House of Talleyrand-Périgord", ["FR"], "noble", "french-ducal", "active",
    900, None, None, "Périgord-Talleyrand; Dukes of Dino, of Talleyrand.")
add("House of Rochechouart", ["FR"], "noble", "french-ducal", "active",
    1000, None, None, None)
add("House of Sully", ["FR"], "noble", "french-ducal", "extinct",
    1500, 1807, None, "Sully ducal title extinct 1807.")
add("House of Beauharnais", ["FR"], "noble", "napoleonic", "active",
    1390, None, None,
    "Imperial in-laws; via Empress Joséphine; survives in Leuchtenberg branch.")
add("House of Murat", ["FR", "IT"], "noble", "napoleonic", "active",
    1767, None, "Joachim, Prince Murat",
    "Joachim Murat King of Naples; descendants extant.")
add("House of Bauffremont", ["FR"], "noble", "french-ducal", "active",
    1100, None, "Charles-Emmanuel de Bauffremont", None)
add("House of Clermont-Tonnerre", ["FR"], "noble", "french-ducal", "active",
    1100, None, None, None)
add("House of La Tour d'Auvergne", ["FR"], "noble", "french-ducal", "active",
    1000, None, None, None)
add("House of Lévis-Mirepoix", ["FR"], "noble", "french-ducal", "active",
    1000, None, None, None)
add("House of Lorraine (Vaudémont)", ["FR", "DE", "AT"], "royal", "deposed-noble", "active",
    1048, None, None, "Lorraine merged with Habsburgs 1736 as Habsburg-Lorraine.")
add("House of Bourbon-Parma", ["IT", "FR", "LU"], "royal", "deposed-pretender", "deposed",
    1748, None, "Carlos, Duke of Parma",
    "Duchy of Parma; Luxembourg consort line through Felix.")

# ===========================================================================
# 5. Germany — Hochadel + mediatized houses
# ===========================================================================
add("Princely House of Hohenlohe", ["DE"], "noble", "mediatized", "active",
    1153, None, None, "Multiple branches.")
add("Princely House of Schwarzenberg", ["DE", "AT", "CZ"], "noble", "mediatized", "active",
    1429, None, "Karel Schwarzenberg's heirs",
    "Karel Schwarzenberg (d. 2023) was Czech politician.")
add("Princely House of Liechtenstein (broader)", ["LI", "AT"], "noble", "mediatized", "active",
    1140, None, None, "Same as ruling LI house (cross-listed).")
add("Princely House of Auersperg", ["AT"], "noble", "mediatized", "active",
    1067, None, None, None)
add("House of Trauttmansdorff", ["AT"], "noble", "mediatized", "active",
    1146, None, None, None)
add("Princely House of Lobkowicz", ["CZ", "AT"], "noble", "mediatized", "active",
    1400, None, "William Lobkowicz", "Bohemian noble family.")
add("Princely House of Salm", ["BE", "DE"], "noble", "mediatized", "active",
    1019, None, None, None)
add("Princely House of Croÿ", ["BE", "FR"], "noble", "mediatized", "active",
    1280, None, None, None)
add("Princely House of Ligne", ["BE"], "noble", "mediatized", "active",
    1100, None, "Michel, 14th Prince of Ligne",
    "Belgian princely house; Beloeil castle.")
add("Princely House of Arenberg", ["BE", "DE"], "noble", "mediatized", "active",
    1100, None, None, None)
add("Princely House of Sayn-Wittgenstein", ["DE"], "noble", "mediatized", "active",
    1200, None, None,
    "Princess Gloria von Thurn und Taxis is a Sayn-Wittgenstein-Jettenbach.")
add("Princely House of Sayn-Wittgenstein-Berleburg", ["DE", "DK"], "noble", "mediatized", "active",
    1605, None, None,
    "Late Princess Benedikte of Denmark married into Sayn-Wittgenstein-Berleburg.")
add("Princely House of Waldburg", ["DE"], "noble", "mediatized", "active",
    1100, None, None, None)
add("Princely House of Quadt", ["DE"], "noble", "mediatized", "active",
    1200, None, None, None)
add("Princely House of Wied", ["DE"], "noble", "mediatized", "active",
    1100, None, None, "Princes of Wied; gave Albania a king (Wilhelm) briefly 1914.")
add("Princely House of Leiningen", ["DE", "GB"], "noble", "mediatized", "active",
    1100, None, "Karl-Emich, 8th Prince of Leiningen",
    "Half-brother lineage to Queen Victoria; UK Romanov pretender claim.")
add("Princely House of Isenburg", ["DE"], "noble", "mediatized", "active",
    1100, None, None, None)
add("Princely House of Pless", ["DE", "PL"], "noble", "mediatized", "active",
    1289, None, None, "Hochberg family.")
add("Princely House of Bismarck", ["DE"], "noble", "german-noble", "active",
    1270, None, "Carl-Eduard von Bismarck",
    "Otto von Bismarck's family.")
add("Counts von Moltke", ["DE", "DK"], "noble", "german-noble", "active",
    1254, None, None, "Helmuth von Moltke (Chief of General Staff).")
add("House of Stauffenberg", ["DE"], "noble", "german-noble", "active",
    1262, None, None, "Claus von Stauffenberg (anti-Hitler plotter).")
add("Counts of Görtz", ["DE"], "noble", "german-noble", "active",
    1100, None, None, "Schlitz genannt von Görtz.")
add("Counts of Königsegg", ["DE"], "noble", "mediatized", "active",
    1100, None, None, None)
add("Counts of Castell", ["DE"], "noble", "mediatized", "active",
    1057, None, None, None)
add("Counts of Erbach", ["DE"], "noble", "mediatized", "active",
    1100, None, None, None)
add("Counts of Leiningen-Westerburg", ["DE"], "noble", "mediatized", "active",
    1200, None, None, None)

# ===========================================================================
# 6. Italy — Princely / ducal / black nobility (beyond papal Roman families)
# ===========================================================================
add("House of Medici", ["IT"], "noble", "italian-princely", "extinct-main",
    1230, 1737, None, "Senior line extinct 1737; Medici Tornaquinci and other cadets.")
add("House of Este", ["IT"], "noble", "italian-princely", "active",
    950, None, None, "Modena/Ferrara; merged with Habsburg via Austria-Este.")
add("House of Visconti", ["IT"], "noble", "italian-princely", "extinct",
    1100, 1447, None, "Milan; succeeded by Sforza.")
add("House of Sforza", ["IT"], "noble", "italian-princely", "active",
    1400, None, None, "Sforza-Cesarini cadet survives.")
add("Della Rovere family", ["IT"], "noble", "italian-princely", "extinct",
    1300, 1631, None, "Dukes of Urbino; Pope Julius II.")
add("House of Doria", ["IT"], "noble", "italian-princely", "active",
    1100, None, "Jonathan Doria Pamphilj",
    "Genoese; merged with Pamphili as Doria Pamphilj Landi.")
add("Pallavicini-Rospigliosi family", ["IT"], "noble", "italian-princely", "active",
    900, None, None, "Cross-listed merger.")
add("House of Gonzaga", ["IT"], "noble", "italian-princely", "extinct",
    1100, 1708, None, "Mantua; cadet Vespasiano-Gonzaga and Castiglione branches.")
add("House of Farnese", ["IT"], "noble", "italian-princely", "extinct",
    1300, 1731, None, "Parma; merged into Bourbon via Elisabeth Farnese.")
add("House of Della Scala", ["IT"], "noble", "italian-princely", "extinct",
    1262, 1387, None, "Verona; Scaligeri.")
add("House of Malatesta", ["IT"], "noble", "italian-princely", "extinct",
    1100, 1500, None, "Rimini.")
add("House of Montefeltro", ["IT"], "noble", "italian-princely", "extinct",
    1100, 1508, None, "Urbino.")
add("House of Bentivoglio", ["IT"], "noble", "italian-princely", "extinct",
    1300, 1512, None, "Bologna.")
add("House of Visconti di Modrone", ["IT"], "noble", "italian-noble", "active",
    1800, None, None, "Cadet line; Luchino Visconti director.")
add("House of Caracciolo", ["IT"], "noble", "italian-princely", "active",
    1000, None, None, "Neapolitan; Marella Caracciolo Agnelli.")
add("House of Pignatelli", ["IT"], "noble", "italian-princely", "active",
    1000, None, None, "Neapolitan ducal.")
add("House of Borromeo", ["IT"], "noble", "italian-princely", "active",
    1300, None, None, "Lake Maggiore; Cardinal Charles Borromeo.")
add("House of Cybo-Malaspina", ["IT"], "noble", "italian-princely", "active",
    1500, None, None, None)
add("House of Acquaviva", ["IT"], "noble", "italian-princely", "active",
    1000, None, None, "Dukes of Atri.")
add("House of Carafa", ["IT"], "noble", "italian-princely", "active",
    1300, None, None, "Pope Paul IV.")
add("House of d'Avalos", ["IT"], "noble", "italian-princely", "active",
    1400, None, None, None)
add("House of Cantelmo-Stuart", ["IT"], "noble", "italian-princely", "active",
    1100, None, None, None)
add("House of Sanseverino", ["IT"], "noble", "italian-princely", "active",
    1000, None, None, None)
add("House of Spinola", ["IT"], "noble", "italian-princely", "active",
    1100, None, None, "Genoese.")
add("House of Grimaldi (Genoese line)", ["IT"], "noble", "italian-princely", "active",
    1100, None, None, "Original Genoese stock.")
add("House of Pico della Mirandola", ["IT"], "noble", "italian-princely", "extinct",
    1200, 1711, None, "Pico = humanist.")
add("House of Odescalchi", ["IT"], "noble", "italian-princely", "active",
    1500, None, None, "Pope Innocent XI.")

# ===========================================================================
# 7. Spain — Grandee houses
# ===========================================================================
add("House of Alba", ["ES"], "noble", "spanish-grandee", "active",
    1400, None, "Carlos Fitz-James Stuart, 19th Duke of Alba",
    "Most-titled noble in the world per Guinness (Cayetana, his mother).")
add("House of Medinaceli", ["ES"], "noble", "spanish-grandee", "active",
    1300, None, "Marco de Hoyos y Carvajal-Urquijo, 20th Duke of Medinaceli", None)
add("House of Osuna", ["ES"], "noble", "spanish-grandee", "active",
    1400, None, "Ángela Téllez-Girón, 19th Duchess of Osuna", None)
add("House of Infantado", ["ES"], "noble", "spanish-grandee", "active",
    1475, None, "Íñigo de Arteaga y Martín", None)
add("House of Frías", ["ES"], "noble", "spanish-grandee", "active",
    1492, None, None, "Velasco family.")
add("House of Béjar", ["ES"], "noble", "spanish-grandee", "active",
    1485, None, None, "Zúñiga family.")
add("House of Híjar", ["ES"], "noble", "spanish-grandee", "active",
    1322, None, None, "Silva-Fernández de Híjar.")
add("House of Liria y Jérica", ["ES"], "noble", "spanish-grandee", "active",
    1707, None, None, "Stuart cadets via James FitzJames, Duke of Berwick.")
add("House of Mendoza", ["ES"], "noble", "spanish-grandee", "active",
    1100, None, None, "Foundational Castilian house.")
add("House of Toledo", ["ES"], "noble", "spanish-grandee", "active",
    1100, None, None, "Álvarez de Toledo; ancestors of Alba.")
add("House of Cardona", ["ES"], "noble", "spanish-grandee", "active",
    1064, None, None, "Catalan ducal.")
add("House of Borja (Borgia)", ["ES", "IT"], "noble", "spanish-papal", "active",
    1100, None, None, "Two popes; Italian Borgia line distinct.")
add("House of Bourbon-Carlist", ["ES"], "royal", "deposed-pretender", "deposed",
    1833, None, "Pedro de Borbón-Dos Sicilias",
    "Carlist claimants merged into Bourbon-Two Sicilies / Bourbon-Parma branches.")
add("House of Maura", ["ES"], "noble", "spanish-political", "active",
    1850, None, None, "PM Antonio Maura.")
add("House of Romanones", ["ES"], "noble", "spanish-political", "active",
    1900, None, None, "Counts of Romanones; PM Álvaro de Figueroa.")
add("House of Galiana", ["ES"], "noble", "spanish-grandee", "active",
    1700, None, None, None)
add("House of Silva", ["ES"], "noble", "spanish-grandee", "active",
    1300, None, None, "Marquesses of Santillana; Counts of Cifuentes.")

# ===========================================================================
# 8. Russia — Rurikid princely houses + non-princely magnate families
# ===========================================================================
add("Volkonsky family", ["RU"], "noble", "rurikid-princely", "active",
    1200, None, None, "Rurikid princes of Volkonsk.")
add("Obolensky family", ["RU"], "noble", "rurikid-princely", "active",
    1200, None, None, None)
add("Shcherbatov family", ["RU"], "noble", "rurikid-princely", "active",
    1300, None, None, None)
add("Trubetskoy family", ["RU"], "noble", "lithuanian-rurikid", "active",
    1500, None, None, "Lithuanian-derived princely.")
add("Gagarin family", ["RU"], "noble", "rurikid-princely", "active",
    1500, None, None, "Yuri Gagarin (cosmonaut) NOT of this princely line.")
add("Lobanov-Rostovsky family", ["RU"], "noble", "rurikid-princely", "active",
    1300, None, None, None)
add("Cherkassky family", ["RU"], "noble", "circassian-russian", "active",
    1500, None, None, "Originally Caucasian (Cherkess) princes.")
add("Khilkov family", ["RU"], "noble", "rurikid-princely", "active",
    1400, None, None, None)
add("Vyazemsky family", ["RU"], "noble", "rurikid-princely", "active",
    1200, None, None, None)
add("Golitsyn family", ["RU"], "noble", "gediminid-russian", "active",
    1500, None, "Andrei Kirillovich Golitsyn",
    "Gediminid-descent; head of Russian Noble Assembly.")
add("Kurakin family", ["RU"], "noble", "gediminid-russian", "active",
    1500, None, None, None)
add("Bariatinsky family", ["RU"], "noble", "rurikid-princely", "active",
    1500, None, None, None)
add("Dolgorukov family", ["RU"], "noble", "rurikid-princely", "active",
    1500, None, None, None)
add("Sheremetev family", ["RU"], "noble", "russian-magnate", "active",
    1500, None, "Pyotr Sheremetev",
    "Counts; major arts patrons.")
add("Stroganov family", ["RU"], "noble", "russian-magnate", "active",
    1400, None, None, "Industrialists/merchants ennobled.")
add("Demidov family", ["RU", "IT"], "noble", "russian-magnate", "active",
    1700, None, None, "Industrialists; Italian branch (Princes of San Donato).")
add("Yusupov family", ["RU"], "noble", "russian-magnate", "extinct-male",
    1500, None, None, "Felix Yusupov killed Rasputin; male line extinct.")
add("Bobrinsky family", ["RU"], "noble", "russian-imperial-illegitimate", "active",
    1762, None, None, "Catherine the Great's son's line.")
add("Naryshkin family", ["RU"], "noble", "russian-magnate", "active",
    1500, None, None, "Peter the Great's mother's family.")
add("Vorontsov family", ["RU", "GB"], "noble", "russian-magnate", "active",
    1500, None, None, "Pembroke (UK) cadet via marriage.")
add("Saltykov family", ["RU"], "noble", "russian-magnate", "active",
    1400, None, None, None)
add("Tatishchev family", ["RU"], "noble", "russian-magnate", "active",
    1400, None, None, None)
add("Sumarokov family", ["RU"], "noble", "russian-magnate", "active",
    1400, None, None, None)
add("Razumovsky family", ["RU", "UA"], "noble", "ukrainian-russian", "active",
    1700, None, None, "Cossack-origin ennobled under Elizabeth.")
add("Bagration family", ["GE", "RU"], "royal", "georgian-russian", "active",
    885, None, None, "Georgian royal house; Russian Imperial counts.")

# ===========================================================================
# 9. Poland — Polish-Lithuanian magnate families (Szlachta upper tier)
# ===========================================================================
add("House of Radziwiłł", ["PL", "LT", "BY"], "noble", "polish-lithuanian-magnate", "active",
    1400, None, "Maciej Radziwiłł",
    "Princely; closest thing to Polish royalty.")
add("House of Czartoryski", ["PL", "LT"], "noble", "polish-lithuanian-magnate", "active",
    1400, None, "Adam Karol Czartoryski",
    "Gediminid; museum founders.")
add("House of Sapieha", ["PL", "LT"], "noble", "polish-lithuanian-magnate", "active",
    1450, None, None, "Princely; major Lithuanian-Polish family.")
add("House of Potocki", ["PL", "UA"], "noble", "polish-magnate", "active",
    1300, None, None, "Multiple branches: Tulczyn, Krzeszowice, etc.")
add("House of Lubomirski", ["PL"], "noble", "polish-magnate", "active",
    1300, None, "Stanisław Lubomirski",
    "Princely; one of richest pre-partition families.")
add("House of Tarnowski", ["PL"], "noble", "polish-magnate", "active",
    1300, None, None, None)
add("House of Zamoyski", ["PL"], "noble", "polish-magnate", "active",
    1500, None, "Marcin Zamoyski",
    "Hetman Jan Zamoyski; Zamość.")
add("House of Wiśniowiecki", ["PL"], "noble", "polish-magnate", "extinct",
    1400, 1744, None, "Gave Poland King Michael Korybut.")
add("House of Ostrogski", ["PL", "UA"], "noble", "rurikid-polish", "extinct",
    1376, 1620, None, "Rurikid-derived Ruthenian princes.")
add("House of Lanckoroński", ["PL", "AT"], "noble", "polish-magnate", "active",
    1300, None, None, None)
add("House of Branicki", ["PL"], "noble", "polish-magnate", "active",
    1400, None, None, "Two unrelated Branicki houses.")
add("House of Mniszech", ["PL"], "noble", "polish-magnate", "active",
    1400, None, None, "Marina Mniszech, Tsaritsa of Russia 1606.")
add("House of Mielżyński", ["PL"], "noble", "polish-magnate", "active",
    1400, None, None, None)
add("House of Sanguszko", ["PL", "LT"], "noble", "rurikid-polish", "active",
    1400, None, None, None)
add("House of Zasław", ["PL"], "noble", "rurikid-polish", "extinct",
    1300, 1673, None, None)
add("House of Pac", ["LT", "PL"], "noble", "lithuanian-magnate", "active",
    1400, None, None, None)
add("House of Tyszkiewicz", ["LT", "PL"], "noble", "lithuanian-magnate", "active",
    1500, None, None, None)
add("House of Sołtan", ["BY", "LT", "PL"], "noble", "lithuanian-magnate", "active",
    1400, None, None, None)
add("House of Krasiński", ["PL"], "noble", "polish-magnate", "active",
    1400, None, None, "Poet Zygmunt Krasiński.")

# ===========================================================================
# 10. Hungary — magnate houses
# ===========================================================================
add("House of Esterházy", ["HU", "AT"], "noble", "hungarian-magnate", "active",
    1238, None, "Pál Esterházy",
    "Princely; Eisenstadt; Haydn patrons.")
add("House of Batthyány", ["HU", "AT"], "noble", "hungarian-magnate", "active",
    1392, None, None, "PM Lajos Batthyány (executed 1849).")
add("House of Andrássy", ["HU"], "noble", "hungarian-magnate", "active",
    1500, None, None, "PM Gyula Andrássy.")
add("House of Pálffy", ["HU", "SK", "AT"], "noble", "hungarian-magnate", "active",
    1300, None, None, None)
add("House of Festetics", ["HU"], "noble", "hungarian-magnate", "active",
    1500, None, None, "Princes of Tolna.")
add("House of Apponyi", ["HU"], "noble", "hungarian-magnate", "active",
    1300, None, None, None)
add("House of Károlyi", ["HU"], "noble", "hungarian-magnate", "active",
    1300, None, None, "President Mihály Károlyi (1918-19).")
add("House of Széchenyi", ["HU"], "noble", "hungarian-magnate", "active",
    1500, None, None, "Reformer István Széchenyi.")
add("House of Teleki", ["HU", "RO"], "noble", "hungarian-magnate", "active",
    1400, None, None, "PM Pál Teleki.")
add("House of Wesselényi", ["HU", "RO"], "noble", "hungarian-magnate", "active",
    1400, None, None, None)
add("House of Nádasdy", ["HU"], "noble", "hungarian-magnate", "active",
    1300, None, None, "Ferenc Nádasdy.")
add("House of Erdődy", ["HU", "AT"], "noble", "hungarian-magnate", "active",
    1500, None, None, None)
add("House of Zichy", ["HU"], "noble", "hungarian-magnate", "active",
    1300, None, None, None)
add("House of Hunyadi", ["HU", "RO"], "royal", "hungarian-royal", "extinct",
    1409, 1505, None, "King Matthias Corvinus.")
add("House of Rákóczi", ["HU"], "noble", "hungarian-princely", "extinct",
    1500, 1780, None, "Prince Ferenc II Rákóczi; Transylvania.")
add("House of Bethlen", ["HU", "RO"], "noble", "transylvanian-princely", "active",
    1200, None, None, "Prince Gábor Bethlen.")
add("Báthory family", ["HU", "PL", "RO"], "noble", "transylvanian-princely", "extinct",
    1200, 1658, None, "King Stephen Báthory of Poland; Elizabeth Báthory.")

# ===========================================================================
# 11. Scandinavia — Bonde, Brahe, etc.
# ===========================================================================
add("House of Bonde", ["SE"], "noble", "swedish-noble", "active",
    1400, None, None, "Swedish 'svenska adel'; King Karl Knutsson Bonde.")
add("House of Brahe", ["SE", "DK"], "noble", "swedish-danish-noble", "active",
    1300, None, None, "Tycho Brahe; Per Brahe the Younger.")
add("House of Sparre", ["SE"], "noble", "swedish-noble", "active",
    1300, None, None, None)
add("House of Oxenstierna", ["SE"], "noble", "swedish-noble", "active",
    1300, None, None, "Chancellor Axel Oxenstierna.")
add("House of Trolle", ["SE"], "noble", "swedish-noble", "active",
    1300, None, None, None)
add("House of Bielke", ["SE"], "noble", "swedish-noble", "active",
    1300, None, None, None)
add("House of Krag", ["DK", "NO"], "noble", "danish-noble", "active",
    1300, None, None, None)
add("House of Reedtz-Thott", ["DK"], "noble", "danish-noble", "active",
    1500, None, None, "PM Tage Reedtz-Thott.")
add("House of Gyllenstierna", ["SE"], "noble", "swedish-noble", "active",
    1300, None, None, None)
add("House of Wachtmeister", ["SE"], "noble", "swedish-noble", "active",
    1500, None, None, "Counts and barons; admiral Hans Wachtmeister.")
add("House of De la Gardie", ["SE"], "noble", "swedish-noble", "active",
    1500, None, None, "Magnus Gabriel De la Gardie.")
add("House of Banér", ["SE"], "noble", "swedish-noble", "active",
    1300, None, None, "Field marshal Johan Banér.")
add("House of Horn", ["SE", "FI"], "noble", "swedish-finnish-noble", "active",
    1300, None, None, "Multiple Horn lines.")
add("House of Lewenhaupt", ["SE"], "noble", "swedish-noble", "active",
    1500, None, None, "Counts; descended from Vasa.")
add("House of Stenbock", ["SE"], "noble", "swedish-noble", "active",
    1300, None, None, "Magnus Stenbock.")
add("House of Piper", ["SE"], "noble", "swedish-noble", "active",
    1700, None, None, None)
add("House of Ahlefeldt", ["DK", "DE"], "noble", "danish-noble", "active",
    1100, None, None, None)
add("House of Danneskiold-Samsøe", ["DK"], "noble", "danish-noble", "active",
    1670, None, None, "Royal cadet; Christian V's illegitimate descent.")
add("House of Moltke", ["DK", "DE"], "noble", "danish-german-noble", "active",
    1100, None, None, None)
add("House of Schimmelmann", ["DK"], "noble", "danish-noble", "active",
    1700, None, None, None)
add("House of Holstein-Ledreborg", ["DK"], "noble", "danish-noble", "active",
    1700, None, None, None)
add("House of Wedel-Jarlsberg", ["NO"], "noble", "norwegian-noble", "active",
    1500, None, None, "Count Herman Wedel-Jarlsberg.")
add("House of Løvenskiold", ["NO", "DK"], "noble", "norwegian-noble", "active",
    1600, None, None, None)
add("House of Anker", ["NO"], "noble", "norwegian-noble", "active",
    1700, None, None, "Carsten Anker; Eidsvoll.")

# ===========================================================================
# 12. USA — political dynasties
# ===========================================================================
add("Adams family", ["US"], "political", "us-political-dynasty", "active",
    1700, None, None, "Two presidents (John, John Quincy); descendants ongoing.")
add("Roosevelt family", ["US"], "political", "us-political-dynasty", "active",
    1640, None, None,
    "Hyde Park branch (Franklin D.) + Oyster Bay branch (Theodore).")
add("Kennedy family", ["US"], "political", "us-political-dynasty", "active",
    1850, None, "Joseph P. Kennedy III / Robert F. Kennedy Jr.",
    "John, Robert, Edward Kennedy.")
add("Bush family", ["US"], "political", "us-political-dynasty", "active",
    1840, None, None,
    "Two presidents (George H.W., George W.); Sen. Prescott Bush; Gov. Jeb Bush.")
add("Clinton family", ["US"], "political", "us-political-dynasty", "active",
    1980, None, None, "Bill, Hillary, Chelsea Clinton.")
add("Taft family", ["US"], "political", "us-political-dynasty", "active",
    1800, None, None, "President William Howard Taft; Sen. Robert Taft.")
add("Harrison family", ["US"], "political", "us-political-dynasty", "active",
    1700, None, None,
    "Benjamin Harrison V (signer), Pres. William Henry Harrison, Pres. Benjamin Harrison.")
add("Rockefeller family", ["US"], "business", "us-political-business", "active",
    1860, None, "David Rockefeller Jr.",
    "Standard Oil; Gov. Nelson Rockefeller; many billionaires.")
add("Du Pont family", ["US"], "business", "us-political-business", "active",
    1800, None, None, "DuPont chemicals; Gov. Pierre du Pont.")
add("Cabot family", ["US"], "political", "boston-brahmin", "active",
    1700, None, None, "Boston Brahmin.")
add("Lodge family", ["US"], "political", "boston-brahmin", "active",
    1750, None, None,
    "Sen. Henry Cabot Lodge Sr. & Jr.; Boston Brahmin.")
add("Lowell family", ["US"], "political", "boston-brahmin", "active",
    1639, None, None, "Boston Brahmin; poet Robert Lowell; Pres. Harvard Abbott Lowell.")
add("Astor family", ["US", "GB"], "business", "us-uk-business", "active",
    1763, None, "William Astor, 4th Viscount Astor",
    "John Jacob Astor; UK Viscount Astor branch.")
add("Vanderbilt family", ["US"], "business", "us-business-dynasty", "active",
    1830, None, "Anderson Cooper",
    "Cornelius Vanderbilt; The Breakers; Anderson Cooper descendant.")
add("Carnegie family", ["US"], "business", "us-business-dynasty", "active",
    1850, None, None,
    "Andrew Carnegie steel; foundations.")
add("Mellon family", ["US"], "business", "us-business-dynasty", "active",
    1860, None, None, "Andrew Mellon; banking.")

# ===========================================================================
# 13. USA — business dynasties
# ===========================================================================
add("Walton family", ["US"], "business", "us-business-dynasty", "active",
    1962, None, "Rob Walton / Jim Walton / Alice Walton",
    "Walmart; richest family in US by Forbes.")
add("Koch family", ["US"], "business", "us-business-dynasty", "active",
    1940, None, "Charles Koch",
    "Koch Industries; David Koch d. 2019.")
add("Mars family", ["US"], "business", "us-business-dynasty", "active",
    1911, None, None, "Mars Inc. confectionery; privately held.")
add("Cargill-MacMillan family", ["US"], "business", "us-business-dynasty", "active",
    1865, None, None, "Cargill agribusiness; largest US private company.")
add("S. C. Johnson family", ["US"], "business", "us-business-dynasty", "active",
    1886, None, "Fisk Johnson",
    "SC Johnson; Racine, WI.")
add("Pritzker family", ["US"], "business", "us-business-dynasty", "active",
    1900, None, "Tom Pritzker",
    "Hyatt; Gov. JB Pritzker.")
add("Newhouse family", ["US"], "business", "us-business-dynasty", "active",
    1922, None, None, "Advance Publications; Condé Nast.")
add("Ziff family", ["US"], "business", "us-business-dynasty", "active",
    1927, None, None, "Ziff Davis publishing.")
add("Lauder family", ["US"], "business", "us-business-dynasty", "active",
    1946, None, "William Lauder",
    "Estée Lauder cosmetics.")
add("Tisch family", ["US"], "business", "us-business-dynasty", "active",
    1946, None, "James Tisch / Jonathan Tisch",
    "Loews Corporation; NY Giants.")
add("Wrigley family", ["US"], "business", "us-business-dynasty", "active",
    1891, None, None, "Wrigley chewing gum; Chicago Cubs.")
add("Bechtel family", ["US"], "business", "us-business-dynasty", "active",
    1898, None, "Riley Bechtel",
    "Bechtel Corporation engineering; private.")
add("Hearst family", ["US"], "business", "us-business-dynasty", "active",
    1880, None, "William Randolph Hearst III",
    "Hearst Communications media.")
add("Pulitzer family", ["US"], "business", "us-business-dynasty", "active",
    1880, None, None, "Pulitzer Publishing; Pulitzer Prize.")
add("Sulzberger family", ["US"], "business", "us-business-dynasty", "active",
    1896, None, "A. G. Sulzberger",
    "New York Times since 1896.")
add("Heinz family", ["US"], "business", "us-business-dynasty", "active",
    1869, None, None, "H.J. Heinz; Sen. John Heinz.")
add("Disney family", ["US"], "business", "us-business-dynasty", "active",
    1923, None, "Abigail Disney",
    "Walt Disney; family active in philanthropy.")
add("Hilton family", ["US"], "business", "us-business-dynasty", "active",
    1919, None, "Barron Hilton heirs",
    "Hilton Hotels.")
add("Marriott family", ["US"], "business", "us-business-dynasty", "active",
    1927, None, "David Marriott",
    "Marriott International; Mormon family.")
add("Ford family", ["US"], "business", "us-business-dynasty", "active",
    1903, None, "William Clay Ford Jr.",
    "Ford Motor Company.")
add("Coors family", ["US"], "business", "us-business-dynasty", "active",
    1873, None, "Pete Coors",
    "Molson Coors brewing.")
add("Busch family", ["US"], "business", "us-business-dynasty", "active",
    1852, None, "August Busch IV",
    "Anheuser-Busch (now AB InBev).")
add("DeVos family", ["US"], "business", "us-business-dynasty", "active",
    1959, None, "Doug DeVos / Dick DeVos",
    "Amway; Sec. Betsy DeVos.")
add("Field family", ["US"], "business", "us-business-dynasty", "active",
    1856, None, None, "Marshall Field's; Field Museum; Sun-Times publisher.")
add("Phipps family", ["US"], "business", "us-business-dynasty", "active",
    1880, None, None, "Carnegie Steel partner Henry Phipps.")
add("Bass family", ["US"], "business", "us-business-dynasty", "active",
    1930, None, None, "Fort Worth oil; Sid R. Bass.")
add("Hunt family", ["US"], "business", "us-business-dynasty", "active",
    1934, None, None, "H.L. Hunt; Hunt Oil; Dallas Cowboys not, but Kansas City Chiefs (Lamar Hunt).")
add("Murchison family", ["US"], "business", "us-business-dynasty", "active",
    1920, None, None, "Texas oil.")
add("Cox family", ["US"], "business", "us-business-dynasty", "active",
    1898, None, None, "Cox Enterprises; James M. Cox (1920 D. nominee).")
add("Helmsley family", ["US"], "business", "us-business-dynasty", "active",
    1925, None, None, "Helmsley hotels; Leona Helmsley.")
add("Soros family", ["US", "HU"], "business", "us-finance-dynasty", "active",
    1969, None, "Alex Soros",
    "George Soros; Open Society Foundations.")

# ===========================================================================
# 14. Latin America
# ===========================================================================
# Argentina
add("Anchorena family", ["AR"], "noble", "argentine-criollo", "active",
    1800, None, None, "Cattle barons; Aarón Anchorena.")
add("Alvear family", ["AR"], "political", "argentine-political", "active",
    1800, None, None, "Pres. Marcelo T. de Alvear.")
add("Pereyra Iraola family", ["AR"], "noble", "argentine-criollo", "active",
    1800, None, None, "Estancia barons; Pereyra Iraola Park.")
add("Martínez de Hoz family", ["AR"], "noble", "argentine-criollo", "active",
    1800, None, None, None)
add("Roca family", ["AR"], "political", "argentine-political", "active",
    1850, None, None, "Pres. Julio A. Roca.")
add("Macri family", ["AR"], "business", "argentine-political-business", "active",
    1900, None, "Mauricio Macri", "President 2015-19; SOCMA.")
add("Kirchner family", ["AR"], "political", "argentine-political", "active",
    2003, None, "Cristina Fernández de Kirchner",
    "Presidents Néstor + Cristina Kirchner.")
add("Perón family", ["AR"], "political", "argentine-political", "active",
    1946, None, None, "Pres. Juan Perón; Eva and Isabel Perón.")
add("Bulgheroni family", ["AR"], "business", "argentine-business", "active",
    1948, None, "Alejandro Bulgheroni", "Bridas oil.")
add("Roggio family", ["AR"], "business", "argentine-business", "active",
    1908, None, None, "Roggio construction conglomerate.")
add("Pescarmona family", ["AR"], "business", "argentine-business", "active",
    1907, None, None, "IMPSA.")
add("Galperin family", ["AR"], "business", "argentine-tech", "active",
    1999, None, "Marcos Galperin",
    "MercadoLibre founder; first major LatAm tech.")
add("Bagó family", ["AR"], "business", "argentine-business", "active",
    1934, None, None, "Laboratorios Bagó (pharma).")

# Brazil
add("Marinho family", ["BR"], "business", "brazilian-media", "active",
    1925, None, "João Roberto Marinho",
    "Grupo Globo; Brazilian media.")
add("Safra family", ["BR", "LB"], "business", "brazilian-banking", "active",
    1955, None, "Alberto Safra and brothers",
    "Banco Safra; Lebanese-Sephardic origin.")
add("Camargo family", ["BR"], "business", "brazilian-construction", "active",
    1939, None, None, "Camargo Corrêa.")
add("Batista family", ["BR"], "business", "brazilian-meat", "active",
    1953, None, "Joesley Batista / Wesley Batista",
    "JBS / J&F; largest meatpacker.")
add("Moreira Salles family", ["BR"], "business", "brazilian-banking", "active",
    1924, None, "Pedro Moreira Salles",
    "Itaú Unibanco; controlling family with Setubal.")
add("Setubal family", ["BR"], "business", "brazilian-banking", "active",
    1920, None, "Roberto Setubal",
    "Itaú; Olavo Setubal political.")
add("Villela family", ["BR"], "business", "brazilian-banking", "active",
    1920, None, None, "Itaú co-control.")
add("Diniz family", ["BR"], "business", "brazilian-retail", "active",
    1948, None, "Abilio Diniz",
    "Grupo Pão de Açúcar.")
add("Ermírio de Moraes family", ["BR"], "business", "brazilian-industrial", "active",
    1918, None, None, "Votorantim.")
add("Klabin family", ["BR"], "business", "brazilian-industrial", "active",
    1899, None, None, "Pulp/paper; Lithuanian-Jewish origin.")
add("Gerdau Johannpeter family", ["BR"], "business", "brazilian-industrial", "active",
    1901, None, "Jorge Gerdau Johannpeter",
    "Gerdau steel; German-Brazilian.")
add("Odebrecht family", ["BR"], "business", "brazilian-construction", "active",
    1944, None, None, "Odebrecht (renamed Novonor post-Lava Jato).")
add("Cutrale family", ["BR"], "business", "brazilian-agri", "active",
    1960, None, "Jose Luis Cutrale", "Sucocítrico Cutrale; world's largest OJ.")
add("Civita family", ["BR"], "business", "brazilian-media", "active",
    1950, None, None, "Editora Abril.")

# Mexico
add("Slim family", ["MX", "LB"], "business", "mexican-tycoon", "active",
    1965, None, "Carlos Slim Helú",
    "América Móvil, Grupo Carso; Lebanese-Maronite origin.")
add("Salinas Pliego family", ["MX"], "business", "mexican-tycoon", "active",
    1906, None, "Ricardo Salinas Pliego",
    "Grupo Salinas; TV Azteca.")
add("Larrea family", ["MX"], "business", "mexican-mining", "active",
    1965, None, "Germán Larrea",
    "Grupo México (Southern Copper).")
add("Servitje family", ["MX"], "business", "mexican-food", "active",
    1945, None, None, "Grupo Bimbo (largest bakery worldwide).")
add("Bailleres family", ["MX"], "business", "mexican-industrial", "active",
    1900, None, "Alejandro Bailleres",
    "Industrias Peñoles.")
add("Hank family", ["MX"], "business", "mexican-political-business", "active",
    1940, None, "Carlos Hank Rhon / Jorge Hank Rhon",
    "Hank González political dynasty.")
add("Beltrones family", ["MX"], "political", "mexican-political", "active",
    1980, None, "Manlio Fabio Beltrones", None)
add("Salinas de Gortari family", ["MX"], "political", "mexican-political", "active",
    1988, None, "Carlos Salinas de Gortari",
    "Pres. Carlos Salinas; brother Raúl.")
add("Echeverría family", ["MX"], "political", "mexican-political", "active",
    1970, None, None, "Pres. Luis Echeverría.")
add("Madero family", ["MX"], "political", "mexican-political", "active",
    1850, None, None, "Pres. Francisco I. Madero.")
add("Azcárraga family", ["MX"], "business", "mexican-media", "active",
    1930, None, "Emilio Azcárraga Jean",
    "Televisa.")

# Chile
add("Matte family", ["CL"], "business", "chilean-tycoon", "active",
    1841, None, "Bernardo Matte / Eliodoro Matte",
    "Grupo Matte; CMPC.")
add("Luksic family", ["CL", "HR"], "business", "chilean-tycoon", "active",
    1954, None, "Iris Fontbona heirs (Andronico Luksic Jr., etc.)",
    "Quiñenco/Banco de Chile, Antofagasta plc.")
add("Angelini family", ["CL", "IT"], "business", "chilean-tycoon", "active",
    1923, None, "Roberto Angelini Rossi",
    "Empresas Copec.")
add("Paulmann family", ["CL", "DE"], "business", "chilean-retail", "active",
    1976, None, "Horst Paulmann",
    "Cencosud.")
add("Saieh family", ["CL"], "business", "chilean-banking", "active",
    1980, None, "Álvaro Saieh",
    "CorpBanca, La Tercera.")
add("Yarur family", ["CL", "PS"], "business", "chilean-banking", "active",
    1940, None, "Luis Enrique Yarur",
    "BCI; Palestinian-Chilean origin.")
add("Solari family", ["CL"], "business", "chilean-retail", "active",
    1880, None, None, "Falabella retail.")
add("Piñera family", ["CL"], "political", "chilean-political-business", "active",
    1990, None, "Sebastián Piñera heirs",
    "Pres. Sebastián Piñera (d. 2024); brother José.")
add("Errázuriz family", ["CL"], "noble", "chilean-criollo", "active",
    1700, None, None, "Pres. Federico Errázuriz; criollo Basque-origin.")
add("Edwards family", ["CL"], "business", "chilean-media", "active",
    1880, None, "Andrónico Luksic Craig / Cristián Edwards heirs",
    "El Mercurio; British-origin.")

# Colombia
add("Santo Domingo family", ["CO"], "business", "colombian-tycoon", "active",
    1969, None, "Alejandro Santo Domingo",
    "Bavaria (sold to SABMiller), now stake in AB InBev.")
add("Sarmiento Angulo family", ["CO"], "business", "colombian-tycoon", "active",
    1956, None, "Luis Carlos Sarmiento Gutiérrez",
    "Grupo Aval banking.")
add("Echavarría family", ["CO"], "business", "colombian-industrial", "active",
    1900, None, None, "Founders of Coltejer, Bancolombia (GEA).")
add("Carvajal family", ["CO"], "business", "colombian-industrial", "active",
    1904, None, None, "Carvajal SA.")
add("Ardila Lülle family", ["CO"], "business", "colombian-tycoon", "active",
    1950, None, "Antonio Ardila Lülle heirs",
    "Postobón, RCN.")
add("Ospina family", ["CO"], "political", "colombian-political", "active",
    1800, None, None, "Three Colombian presidents.")
add("Lleras family", ["CO"], "political", "colombian-political", "active",
    1900, None, None, "Pres. Alberto Lleras Camargo, Carlos Lleras Restrepo.")

# Peru
add("Romero family", ["PE"], "business", "peruvian-tycoon", "active",
    1888, None, "Dionisio Romero Paoletti",
    "Credicorp / BCP.")
add("Brescia family", ["PE", "IT"], "business", "peruvian-tycoon", "active",
    1889, None, "Mario Brescia Cafferata heirs",
    "Breca Group.")
add("Rodríguez Pastor family", ["PE"], "business", "peruvian-tycoon", "active",
    1994, None, "Carlos Rodríguez-Pastor",
    "Intercorp.")
add("Fujimori family", ["PE", "JP"], "political", "peruvian-political", "active",
    1990, None, "Keiko Fujimori",
    "Pres. Alberto Fujimori; daughter Keiko.")
add("García family", ["PE"], "political", "peruvian-political", "active",
    1980, None, None, "Pres. Alan García (suicide 2019).")

# Venezuela
add("Cisneros family", ["VE", "US"], "business", "venezuelan-tycoon", "active",
    1929, None, "Adriana Cisneros",
    "Organización Cisneros; Venevisión.")
add("Mendoza family", ["VE"], "business", "venezuelan-tycoon", "active",
    1941, None, "Lorenzo Mendoza",
    "Empresas Polar (beer).")
add("Vollmer family", ["VE", "DE"], "business", "venezuelan-tycoon", "active",
    1827, None, None, "Sugar / rum (Santa Teresa).")
add("Boulton family", ["VE", "GB"], "business", "venezuelan-tycoon", "active",
    1826, None, None, "Pre-Chávez shipping/finance.")
add("Phelps family", ["VE", "US"], "business", "venezuelan-tycoon", "active",
    1893, None, None, "Once owned RCTV.")

# ===========================================================================
# 15. Canada
# ===========================================================================
add("Thomson family", ["CA", "GB"], "business", "canadian-tycoon", "active",
    1934, None, "David Thomson, 3rd Baron Thomson of Fleet",
    "Thomson Reuters; richest Canadian family.")
add("Weston family", ["CA", "GB"], "business", "canadian-tycoon", "active",
    1882, None, "Galen G. Weston",
    "George Weston Ltd. / Loblaws / Selfridges (UK).")
add("Irving family", ["CA"], "business", "canadian-tycoon", "active",
    1924, None, "Jim Irving / Arthur Irving heirs",
    "J.D. Irving / Irving Oil; New Brunswick.")
add("Desmarais family", ["CA"], "business", "canadian-tycoon", "active",
    1968, None, "Paul Desmarais Jr. / André Desmarais",
    "Power Corporation of Canada.")
add("McCain family", ["CA"], "business", "canadian-tycoon", "active",
    1957, None, "Harrison McCain heirs",
    "McCain Foods (frozen potatoes).")
add("Bronfman family", ["CA", "US"], "business", "canadian-tycoon", "active",
    1924, None, "Edgar Bronfman Jr. / Stephen Bronfman",
    "Seagram heirs; Charles Bronfman Olympics.")
add("Rogers family", ["CA"], "business", "canadian-tycoon", "active",
    1925, None, "Edward Rogers III",
    "Rogers Communications.")
add("Saputo family", ["CA", "IT"], "business", "canadian-tycoon", "active",
    1954, None, "Lino Saputo Jr.",
    "Saputo Dairy.")
add("Pattison family", ["CA"], "business", "canadian-tycoon", "active",
    1961, None, "Jim Pattison",
    "Jim Pattison Group.")
add("Stronach family", ["CA", "AT"], "business", "canadian-tycoon", "active",
    1957, None, "Frank Stronach / Belinda Stronach",
    "Magna International.")
add("Reichmann family", ["CA"], "business", "canadian-tycoon", "active",
    1960, None, None, "Olympia & York; Canary Wharf.")
add("Eaton family", ["CA"], "business", "canadian-business-historical", "active",
    1869, None, None, "Eaton's department stores (defunct 1999).")

# ===========================================================================
# 16. Global business dynasties (multinational)
# ===========================================================================
add("Rothschild family", ["GB", "FR", "AT", "DE"], "business", "global-finance-dynasty", "active",
    1760, None, "Jacob Rothschild heirs / Benjamin de Rothschild heirs / David René de Rothschild",
    "Mayer Amschel; five sons sent to London/Paris/Vienna/Naples/Frankfurt.")
add("Agnelli family", ["IT"], "business", "global-business-dynasty", "active",
    1899, None, "John Elkann",
    "Fiat / Stellantis / Ferrari / Juventus / Exor.")
add("Wallenberg family", ["SE"], "business", "global-business-dynasty", "active",
    1856, None, "Marcus Wallenberg / Jacob Wallenberg",
    "Investor AB; SEB, Ericsson, AstraZeneca, Saab.")
add("Hermès / Dumas family", ["FR"], "business", "global-luxury", "active",
    1837, None, "Axel Dumas",
    "Hermès International.")
add("Arnault family", ["FR"], "business", "global-luxury", "active",
    1989, None, "Bernard Arnault",
    "LVMH.")
add("Bettencourt-Meyers family", ["FR"], "business", "global-luxury", "active",
    1909, None, "Françoise Bettencourt-Meyers",
    "L'Oréal heir.")
add("Mulliez family", ["FR"], "business", "global-retail", "active",
    1961, None, None, "Auchan, Decathlon, Leroy Merlin; 'Association familiale Mulliez'.")
add("Pinault family", ["FR"], "business", "global-luxury", "active",
    1962, None, "François-Henri Pinault",
    "Kering (Gucci, Saint Laurent, Balenciaga); Artémis.")
add("Wertheimer family", ["FR"], "business", "global-luxury", "active",
    1924, None, "Alain Wertheimer / Gérard Wertheimer",
    "Chanel SA.")
add("Albrecht family", ["DE"], "business", "global-retail", "active",
    1946, None, None, "Aldi Nord (Theo) + Aldi Süd (Karl) split.")
add("Quandt family", ["DE"], "business", "global-business-dynasty", "active",
    1922, None, "Stefan Quandt / Susanne Klatten",
    "BMW.")
add("Reimann family", ["DE"], "business", "global-consumer", "active",
    1828, None, None, "JAB Holdings; Keurig Dr Pepper, Peet's, Pret a Manger.")
add("Henkel family", ["DE"], "business", "global-consumer", "active",
    1876, None, "Simone Bagel-Trah", "Henkel AG; Persil.")
add("Porsche-Piëch family", ["DE", "AT"], "business", "global-business-dynasty", "active",
    1931, None, "Wolfgang Porsche / Hans Michel Piëch",
    "VW / Porsche / Audi.")
add("Rausing family", ["SE", "GB"], "business", "global-consumer", "active",
    1944, None, "Hans Rausing heirs / Kirsten Rausing / Jörn Rausing",
    "Tetra Pak (Tetra Laval).")
add("Oeri / Hoffmann family", ["CH"], "business", "global-pharma", "active",
    1896, None, "André Hoffmann",
    "Roche pharmaceutical.")
add("Schmidheiny family", ["CH"], "business", "global-cement", "active",
    1912, None, "Thomas Schmidheiny",
    "Holcim / LafargeHolcim.")
add("Blocher family", ["CH"], "business", "swiss-political-business", "active",
    1950, None, "Magdalena Martullo-Blocher",
    "Ems-Chemie; SVP politics.")
add("Bertarelli family", ["CH", "IT"], "business", "global-pharma", "active",
    1978, None, None, "Serono; America's Cup.")
add("Ortega family", ["ES"], "business", "global-retail", "active",
    1975, None, "Amancio Ortega / Sandra Ortega Mera / Marta Ortega",
    "Inditex/Zara; Pontegadea.")
add("Botín family", ["ES"], "business", "global-finance-dynasty", "active",
    1857, None, "Ana Botín",
    "Banco Santander.")
add("Benetton family", ["IT"], "business", "global-business-dynasty", "active",
    1965, None, "Alessandro Benetton",
    "Benetton Group; Edizione (Autogrill, Atlantia, Mundys).")
add("Della Valle family", ["IT"], "business", "global-luxury", "active",
    1900, None, "Diego Della Valle",
    "Tod's, Hogan; stake in Saks.")
add("Ferrero family", ["IT", "LU"], "business", "global-consumer", "active",
    1946, None, "Giovanni Ferrero",
    "Ferrero (Nutella, Kinder, Tic Tac).")
add("Lavazza family", ["IT"], "business", "global-consumer", "active",
    1895, None, "Giuseppe Lavazza heirs",
    "Lavazza coffee.")
add("Barilla family", ["IT"], "business", "global-consumer", "active",
    1877, None, "Guido Barilla",
    "Barilla pasta.")
add("Berlusconi family", ["IT"], "business", "italian-political-business", "active",
    1975, None, "Marina Berlusconi / Pier Silvio Berlusconi",
    "Fininvest, Mediaset; Silvio Berlusconi PM.")
add("De Benedetti family", ["IT"], "business", "italian-business", "active",
    1976, None, "Carlo De Benedetti", "CIR Group; La Repubblica historically.")
add("Caprotti family", ["IT"], "business", "italian-retail", "active",
    1957, None, None, "Esselunga.")
add("Del Vecchio family", ["IT"], "business", "global-luxury", "active",
    1961, None, "Leonardo Del Vecchio heirs",
    "Luxottica/EssilorLuxottica.")
add("Branson family", ["GB"], "business", "global-business-dynasty", "active",
    1970, None, "Richard Branson",
    "Virgin Group.")
add("Sainsbury family", ["GB"], "business", "uk-retail", "active",
    1869, None, None, "J Sainsbury plc.")
add("Cadbury family", ["GB"], "business", "uk-consumer-historical", "active",
    1824, None, None, "Cadbury chocolate (now Mondelez).")
add("Hinduja family", ["GB", "IN"], "business", "global-business-dynasty", "active",
    1914, None, "Gopichand Hinduja / Prakash Hinduja heirs",
    "Hinduja Group.")
add("Mittal family", ["GB", "IN"], "business", "global-business-dynasty", "active",
    1976, None, "Lakshmi Mittal",
    "ArcelorMittal.")
add("Reuben family", ["GB", "IQ"], "business", "uk-finance-dynasty", "active",
    1990, None, "David Reuben / Simon Reuben",
    "Reuben Brothers; Iraqi-Jewish origin.")
add("Sawiris family", ["EG", "AT"], "business", "global-business-dynasty", "active",
    1950, None, "Naguib Sawiris / Nassef Sawiris / Samih Sawiris",
    "Orascom; OCI; Aston Villa stake.")
add("Schwarz family", ["DE"], "business", "global-retail", "active",
    1930, None, "Dieter Schwarz",
    "Lidl & Kaufland (Schwarz Gruppe).")
add("Otto family", ["DE"], "business", "global-retail", "active",
    1949, None, "Michael Otto / Alexander Otto",
    "Otto Group / ECE.")
add("Knauf family", ["DE"], "business", "global-industrial", "active",
    1932, None, None, "Knauf gypsum.")
add("Würth family", ["DE"], "business", "global-industrial", "active",
    1945, None, "Reinhold Würth",
    "Würth Group (fasteners).")
add("Heineken / Heineken-de Carvalho family", ["NL"], "business", "global-consumer", "active",
    1864, None, "Charlene de Carvalho-Heineken",
    "Heineken NV.")
add("Brenninkmeijer family", ["NL", "DE"], "business", "global-retail", "active",
    1841, None, None, "C&A; Cofra Holding.")
add("Van der Vorm family", ["NL"], "business", "dutch-business", "active",
    1873, None, None, "HAL Holding.")
add("Heinekens / Frères Lhoist", ["BE"], "business", "global-industrial", "active",
    1889, None, "Jean-Pierre Berghmans / Olivier Lhoist",
    "Lhoist lime.")
add("Boël family", ["BE"], "business", "belgian-industrial", "active",
    1880, None, None, "Sofina holding.")
add("Frère family", ["BE"], "business", "belgian-finance", "active",
    1970, None, "Gérald Frère / Ségolène Frère",
    "Groupe Bruxelles Lambert (GBL).")
add("Solvay family", ["BE"], "business", "belgian-industrial", "active",
    1863, None, None, "Solvay SA.")

# Switzerland additions
add("Sandoz family", ["CH"], "business", "global-pharma", "extinct-control",
    1886, None, None, "Sandoz pharma (merged 1996 to form Novartis).")
add("Liebherr family", ["DE", "CH"], "business", "global-industrial", "active",
    1949, None, None, "Liebherr cranes.")

# India (cross-listed since Royals project covers Asia too, but these are global)
add("Tata family", ["IN", "GB"], "business", "global-business-dynasty", "active",
    1868, None, "Ratan Tata heirs (Noel Tata)",
    "Tata Sons; Jaguar Land Rover.")
add("Birla family", ["IN"], "business", "indian-tycoon", "active",
    1857, None, "Kumar Mangalam Birla",
    "Aditya Birla Group.")
add("Ambani family", ["IN"], "business", "indian-tycoon", "active",
    1966, None, "Mukesh Ambani / Anil Ambani",
    "Reliance Industries.")
add("Adani family", ["IN"], "business", "indian-tycoon", "active",
    1988, None, "Gautam Adani",
    "Adani Group.")
add("Godrej family", ["IN"], "business", "indian-tycoon", "active",
    1897, None, "Adi Godrej / Jamshyd Godrej",
    "Godrej Group.")
add("Wadia family", ["IN"], "business", "indian-tycoon", "active",
    1736, None, "Nusli Wadia",
    "Wadia Group; Bombay Dyeing.")
add("Bajaj family", ["IN"], "business", "indian-tycoon", "active",
    1926, None, "Rahul Bajaj heirs",
    "Bajaj Auto/Finserv.")
add("Mahindra family", ["IN"], "business", "indian-tycoon", "active",
    1945, None, "Anand Mahindra",
    "Mahindra & Mahindra.")
add("Premji family", ["IN"], "business", "indian-tycoon", "active",
    1945, None, "Azim Premji / Rishad Premji",
    "Wipro.")

# Indonesia / Asia tycoons that are global
add("Hartono family", ["ID"], "business", "indonesian-tycoon", "active",
    1951, None, "Robert Budi Hartono / Michael Bambang Hartono",
    "Djarum / Bank Central Asia.")
add("Widjaja family", ["ID"], "business", "indonesian-tycoon", "active",
    1962, None, "Eka Tjipta Widjaja heirs",
    "Sinar Mas Group.")
add("Salim family", ["ID"], "business", "indonesian-tycoon", "active",
    1957, None, "Anthoni Salim",
    "Salim Group; Indofood.")
add("Riady family", ["ID"], "business", "indonesian-tycoon", "active",
    1959, None, "Mochtar Riady / James Riady",
    "Lippo Group.")
add("Kuok family", ["MY", "SG", "HK"], "business", "global-business-dynasty", "active",
    1949, None, "Robert Kuok",
    "Kerry Group; Shangri-La; SCMP historically.")
add("Lee Kum Kee / Lee family", ["HK", "CN"], "business", "global-consumer", "active",
    1888, None, "Lee Man-Tat heirs",
    "Lee Kum Kee sauce empire.")
add("Lee family of Hong Kong (Henderson Land)", ["HK"], "business", "hk-tycoon", "active",
    1976, None, "Peter Lee Ka-Kit / Martin Lee Ka-Shing",
    "Henderson Land (Lee Shau-kee).")
add("Kwok family", ["HK"], "business", "hk-tycoon", "active",
    1972, None, "Raymond Kwok / Thomas Kwok",
    "Sun Hung Kai Properties.")
add("Cheng family", ["HK"], "business", "hk-tycoon", "active",
    1971, None, "Henry Cheng / Adrian Cheng",
    "New World Development / Chow Tai Fook.")
add("Pao / Woo family", ["HK"], "business", "hk-tycoon", "active",
    1955, None, "Peter Woo",
    "Wheelock; Y.K. Pao shipping.")
add("Murdoch family", ["US", "GB", "AU"], "business", "global-media", "active",
    1952, None, "Lachlan Murdoch / James Murdoch / Elisabeth Murdoch",
    "News Corp; Fox Corp.")
add("Packer family", ["AU"], "business", "australian-media", "active",
    1933, None, "James Packer",
    "Crown Resorts; PBL (sold).")
add("Lowy family", ["AU", "IL"], "business", "global-business-dynasty", "active",
    1960, None, "Steven Lowy / Peter Lowy",
    "Westfield (sold to Unibail-Rodamco-Westfield).")
add("Forrest family", ["AU"], "business", "australian-mining", "active",
    2003, None, "Andrew Forrest",
    "Fortescue Metals.")
add("Rinehart family", ["AU"], "business", "australian-mining", "active",
    1955, None, "Gina Rinehart",
    "Hancock Prospecting.")
add("Pratt family", ["AU", "US"], "business", "australian-business-dynasty", "active",
    1948, None, "Anthony Pratt",
    "Visy Industries / Pratt Industries.")
add("Stokes family", ["AU"], "business", "australian-media", "active",
    1970, None, "Kerry Stokes",
    "Seven Network.")

# Japan
add("Mori family (Mori Building)", ["JP"], "business", "japanese-tycoon", "active",
    1959, None, "Shingo Mori heirs",
    "Mori Building (Roppongi Hills).")
add("Otsuka family", ["JP"], "business", "japanese-tycoon", "active",
    1921, None, "Tatsuo Otsuka",
    "Otsuka Holdings; Pocari Sweat.")
add("Suntory / Saji-Torii family", ["JP"], "business", "japanese-tycoon", "active",
    1899, None, "Nobutada Saji",
    "Suntory Holdings; Torii Shinjiro founder, renamed Saji.")

# ===========================================================================
# 17. Misc European royals/nobles still to cover
# ===========================================================================
add("House of Glücksburg", ["DK", "NO", "GR"], "royal", "multinational-royal", "active",
    1825, None, None,
    "Parent house of Danish, Norwegian, Greek royals; also Mountbatten consort line UK.")
add("House of Mecklenburg", ["DE"], "royal", "deposed-pretender", "deposed",
    1131, None, "Borwin, Duke of Mecklenburg",
    "Mecklenburg-Schwerin + Mecklenburg-Strelitz now merged.")
add("House of Oldenburg", ["DK", "DE", "GR", "NO", "RU"], "royal", "multinational-royal", "active",
    1100, None, None,
    "Parent house of Glücksburgs, Romanovs (House of Holstein-Gottorp-Romanov).")
add("House of Bourbon-Naples", ["IT"], "royal", "deposed-pretender", "deposed",
    1735, None, None, "Same as Two Sicilies (cross-listed).")
add("House of Schaumburg-Lippe", ["DE"], "royal", "deposed-pretender", "deposed",
    1640, None, None, "Principality of Schaumburg-Lippe.")
add("House of Lippe", ["DE"], "royal", "deposed-pretender", "deposed",
    1100, None, None, "Principality of Lippe-Detmold.")
add("House of Anhalt", ["DE"], "royal", "deposed-pretender", "deposed",
    1100, None, "Eduard, Prince of Anhalt", None)
add("House of Hohenzollern-Hechingen", ["DE"], "royal", "extinct", "extinct",
    1576, 1869, None, "Senior Hohenzollern princely cadet.")
add("House of Mountbatten", ["GB"], "noble", "uk-royal-consort", "active",
    1917, None, "Norton Knatchbull, 3rd Earl Mountbatten of Burma",
    "Battenberg renamed 1917; royal consort line.")
add("Battenberg family", ["DE"], "noble", "german-noble-historical", "active",
    1858, None, None, "Pre-1917 name of Mountbatten.")
add("House of Württemberg-Teck", ["DE", "GB"], "noble", "german-uk", "active",
    1863, None, None, "Queen Mary's father's house; cadet of Württemberg.")
add("House of Sigmaringen", ["DE", "RO"], "royal", "deposed-pretender", "deposed",
    1576, None, None, "Same as Hohenzollern-Sigmaringen (cross-listed).")
add("House of Württemberg-Urach", ["DE"], "royal", "deposed-pretender", "deposed",
    1867, None, None, "Briefly offered Lithuanian throne 1918.")

# ===========================================================================
# 18. Eastern Orthodox / Greek nobility
# ===========================================================================
add("House of Komnenos", ["GR", "TR"], "royal", "byzantine-extinct", "extinct",
    1057, 1461, None, "Byzantine + Trebizond emperors.")
add("House of Palaiologos", ["GR"], "royal", "byzantine-extinct", "extinct",
    1259, 1502, None, "Last Byzantine dynasty.")
add("House of Cantacuzene", ["GR", "RO", "RU"], "noble", "phanariote", "active",
    1342, None, None, "Byzantine-origin Phanariote house.")
add("House of Mavrokordatos", ["GR", "RO"], "noble", "phanariote", "active",
    1600, None, None, None)
add("House of Ypsilantis", ["GR", "RO"], "noble", "phanariote", "active",
    1600, None, None, "Alexandros Ypsilantis revolutionary.")

# ===========================================================================
# Sanity: dedup by query
# ===========================================================================
seen_q = set()
deduped = []
for row in FAMILIES:
    q = row[0]
    if q in seen_q:
        continue
    seen_q.add(q)
    deduped.append(row)
FAMILIES = deduped


# ---------------------------------------------------------------------------
# Manual QID overrides — for queries where wbsearchentities returns wrong
# top result or composite/disambiguation names. Verified Wikidata items.
# ---------------------------------------------------------------------------
QID_OVERRIDES: dict[str, str] = {
    # Reigning royal house geographic specifiers — all Glücksburg branches
    "Glücksburg dynasty Norway": "Q155616",          # House of Glücksburg
    "Glücksburg dynasty Denmark": "Q111201485",      # House of Glücksburg (Denmark)
    "Glücksburg dynasty Greece": "Q2559223",         # House of Glücksburg (Greece)
    "House of Saxe-Coburg and Gotha Bulgaria": "Q1753846",  # SCG German parent
    "Habsburg-Lorraine Hungary": "Q645719",          # House of Habsburg-Lorraine
    "Albertine Wettin Saxony": "Q152909",            # House of Wettin
    # UK specifics
    "Bruce family of Elgin": "Q1297073",
    # French
    "House of La Croix de Castries": "Q104537855",   # Castries family name
    "House of Crussol d'Uzès": "Q3145099",
    # German/Austrian princely (broader cross-listed)
    "Princely House of Liechtenstein (broader)": "Q47133",
    # Italian
    "House of Cantelmo-Stuart": "Q3995907",
    "House of Bourbon-Naples": "Q895188",            # Bourbon-Two Sicilies
    # Spanish
    "House of Liria y Jérica": "Q1572886",
    "House of Bourbon-Carlist": "Q679189",           # Carlism
    # Russian
    "Bariatinsky family": "Q1532929",
    # Brazilian
    "Ermírio de Moraes family": "Q4032057",
    "Gerdau Johannpeter family": "Q1525818",
    # Mexican
    "Salinas Pliego family": "Q1377946",
    "Beltrones family": "Q5985330",
    # Colombian / Peruvian
    "Ardila Lülle family": "Q5915030",
    "Rodríguez Pastor family": "Q5751609",       # Carlos Rodriguez-Pastor (founder proxy)
    # German auto
    "Porsche-Piëch family": "Q4373505",              # Porsche family
    # Indonesian / HK
    "Riady family": "Q6555568",
    "Lee family of Hong Kong (Henderson Land)": "Q3208127",
    # German cadet
    "House of Württemberg-Teck": "Q1057793",
    "House of Württemberg-Urach": "Q1057792",
    # Albrecht (Aldi) — wbsearch picked a cemetery; anchor on Aldi brand
    # (no separate "Albrecht family" item exists on Wikidata)
    "Albrecht family": "Q125054",                    # Aldi (proxy)
    # President of France
    "President of France": "Q191954",

    # Stricter-match misses — anchor on best canonical Wikidata item we have
    "Grosvenor family": "Q103929441",            # Grosvenor family (encyclopedia)
    "Compton-Burnett family": "Q432322",         # Ivy Compton-Burnett (proxy)
    "House of Rochechouart-Mortemart": "Q4398784",  # Rochechouart-Mortemart (disambig)
    "Princely House of Pless": "Q430524",        # House of Hochberg (Pless princes)
    "House of Béjar": "Q36659240",               # Béjar surname proxy
    "House of Borja (Borgia)": "Q237599",        # House of Borgia
    "Golitsyn family": "Q387559",                # Galitzine noble family
    "Tatishchev family": "Q4452623",             # Tatischev family
    "Bagration family": "Q187525",               # Bagrationi dynasty
    "House of Bonde": "Q892217",                 # Bonde family
    "House of Trolle": "Q4992340",               # Trolle family
    "House of Krag": "Q12322796",                # Krag family
    "Pulitzer family": "Q173417",                # Joseph Pulitzer (founder proxy)
    "Soros family": "Q12908",                    # George Soros (founder proxy)
    "Alvear family": "Q16148228",                # Alvear family
    "Diniz family": "Q199613",                   # Abilio Diniz (founder proxy)
    "Servitje family": "Q5979100",               # Lorenzo Servitje (founder proxy)
    "Hank family": "Q2395368",                   # Carlos Hank González (founder proxy)
    "Yarur family": "Q28407508",                 # Yarur family name
    "García family": "Q167211",                  # Alan García (founder proxy)
    "Phelps family": "Q984130",                  # Phelps Dodge (proxy)
    "Ambani family": "Q298547",                  # Mukesh Ambani (founder proxy)
    "Premji family": "Q380152",                  # Azim Premji (founder proxy)
    "Cheng family": "Q1069911",                  # Cheng Yu-tung (founder proxy)
    "Marinho family": "Q1752623",                # Roberto Marinho (founder proxy)
    "Batista family": "Q1676554",                # JBS SA (company proxy)
    "Sarmiento Angulo family": "Q6700417",       # Luis Carlos Sarmiento
    "Bruce family of Elgin": "Q845196",          # Clan Bruce
    "Compton-Burnett family": "Q432322",         # Ivy Compton-Burnett (proxy — only family member with Wikidata entry)
    "Pao / Woo family": "Q7177779",              # Peter Woo (proxy)
    "House of Cantacuzene": "Q21666100",         # Cantacuzène surname
    "House of Mavrokordatos": "Q645578",         # Mavrocordatos family
}


# ---------------------------------------------------------------------------
# Wikidata search helper
# ---------------------------------------------------------------------------

def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s


def wbsearch(query: str, retries: int = 3) -> Optional[dict]:
    """Return first wbsearchentities result or None. Uses curl (macOS SSL friendly)."""
    params = {
        "action": "wbsearchentities",
        "search": query,
        "language": "en",
        "format": "json",
        "limit": 5,
        "type": "item",
    }
    url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(params)
    # Significant tokens from query: words >= 3 chars not in stopword set
    stopwords = {"the", "of", "and", "family", "house", "clan", "princely",
                 "counts", "von", "dynasty", "royal", "noble", "branch",
                 "older", "younger", "elder"}
    asciied = unicodedata.normalize("NFKD", query).encode("ascii", "ignore").decode().lower()
    q_tokens = {t for t in re.split(r"[^a-z0-9]+", asciied)
                if len(t) >= 3 and t not in stopwords}

    def label_matches(label: str) -> bool:
        if not label:
            return False
        l_ascii = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode().lower()
        l_tokens = set(re.split(r"[^a-z0-9]+", l_ascii))
        # at least one significant token must appear in the label
        return bool(q_tokens & l_tokens) if q_tokens else True

    for attempt in range(retries):
        try:
            cp = subprocess.run(
                ["curl", "-sS", "--max-time", "30", "--retry", "2",
                 "--retry-delay", "1",
                 "-A", UA, url],
                check=False, capture_output=True, text=True,
            )
            body = cp.stdout
            if not body.strip():
                raise ValueError(f"empty response (stderr={cp.stderr.strip()[:120]})")
            data = json.loads(body)
            results = data.get("search", [])
            if not results:
                return None
            preferred_kw = ("family", "house", "dynasty", "clan", "noble",
                            "royal", "lineage", "company", "group", "corporation",
                            "holding", "bank", "industrialist", "conglomerate",
                            "tycoon", "billionaire", "magnate", "empire",
                            "nobility", "peerage", "principality", "kingdom",
                            "duke", "marquess", "earl", "count", "baron",
                            "ducal", "merchant", "patrician", "brahmin",
                            "szlachta", "boyar")
            # exclude obvious-wrong matches
            exclude_kw = (
                "village", "comune", "municipality", "settlement", "city",
                "town", "river", "mountain", "park", "cemetery", "museum",
                "battleship", "ship", "warship", "documentary", "film",
                "album", "song", "novel", "actor", "actress", "athlete",
                "footballer", "basketball", "tennis", "boxer", "musician",
                "singer", "painter", "sculptor", "writer", "poet", "journalist",
                "scientist", "physicist", "biologist", "chemist", "mathematician",
                "school", "university", "newspaper", "article", "encyclopedia article",
                "wikimedia disambiguation", "wikimedia category", "category:",
                "given name", "family name", "surname", "language", "dialect",
                "species", "genus", "superorder", "order of", "constellation",
                "asteroid", "moon", "crater", "valley", "lake", "island",
                "award", "prize", "ceremony", "quartet", "symphony", "opera",
            )
            best = None
            for r in results:
                lbl = ((r.get("display", {}).get("label", {}) or {}).get("value")
                       or r.get("label") or "")
                desc = ((r.get("display", {}).get("description", {}) or {}).get("value")
                        or r.get("description") or "").lower()
                if any(k in desc for k in exclude_kw):
                    continue
                if not label_matches(lbl):
                    continue
                if any(k in desc for k in preferred_kw):
                    return r
                if best is None:
                    best = r
            return best
        except Exception as e:
            if attempt == retries - 1:
                sys.stderr.write(f"[warn] wbsearch failed for {query!r}: {e}\n")
                return None
            time.sleep(1.5 * (attempt + 1))
    return None


def alt_queries(query: str) -> list[str]:
    """Generate fallback queries if the primary search misses."""
    qs = []
    base = query

    # Strip noisy prefixes / suffixes
    prefixes = [
        "Princely House of ", "House of ", "Counts of ", "Counts von ",
        "Clan ", "Princely ",
    ]
    bare = base
    for p in prefixes:
        if bare.startswith(p):
            bare = bare[len(p):]
            break

    if bare != base:
        qs.append(bare)
        qs.append("House of " + bare)
        qs.append(bare + " family")

    if base.endswith(" family"):
        bare2 = base[:-len(" family")]
        qs.append(bare2)
        qs.append("House of " + bare2)

    if " family" not in base and not any(base.startswith(p) for p in prefixes):
        qs.append(base + " family")
        qs.append("House of " + base)

    # split slashes
    if "/" in base:
        qs.extend(p.strip() for p in base.split("/"))

    # drop parenthetical clarifiers
    if "(" in base:
        qs.append(re.sub(r"\s*\(.*?\)\s*", " ", base).strip())

    # ñ/special-char fallback (transliterate)
    asciied = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    if asciied and asciied != base:
        qs.append(asciied)

    # "X family of Y" -> "Y X" or "X of Y"
    m = re.match(r"^(.+) family of (.+)$", base)
    if m:
        qs.append(f"{m.group(1)} of {m.group(2)}")
        qs.append(f"{m.group(2)} {m.group(1)}")

    # "X family" without "House of" specific words
    qs.append(base.replace("family", "dynasty").strip())

    # dedup, preserve order
    seen = set()
    out = []
    for q in qs:
        q = q.strip()
        if q and q != query and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def wbget_entity(qid: str, retries: int = 3) -> Optional[dict]:
    """Fetch entity label+description for a known QID (for overrides)."""
    url = (
        "https://www.wikidata.org/w/api.php?"
        + urllib.parse.urlencode({
            "action": "wbgetentities",
            "ids": qid,
            "props": "labels|descriptions",
            "languages": "en",
            "format": "json",
        })
    )
    for attempt in range(retries):
        try:
            cp = subprocess.run(
                ["curl", "-sS", "--max-time", "30", "--retry", "2",
                 "--retry-delay", "1", "-A", UA, url],
                check=False, capture_output=True, text=True,
            )
            if not cp.stdout.strip():
                raise ValueError("empty response")
            data = json.loads(cp.stdout)
            ent = data["entities"][qid]
            label = ent.get("labels", {}).get("en", {}).get("value")
            desc = ent.get("descriptions", {}).get("en", {}).get("value")
            return {"id": qid, "label": label, "description": desc,
                    "display": {"label": {"value": label, "language": "en"},
                                "description": {"value": desc, "language": "en"}}}
        except Exception as e:
            if attempt == retries - 1:
                sys.stderr.write(f"[warn] wbgetentities({qid}): {e}\n")
                return None
            time.sleep(1.5 * (attempt + 1))
    return None


def build_record(row: tuple) -> dict:
    (query, countries, category, subcategory, status,
     founded, extinct, head, notes) = row

    # Manual override path
    if query in QID_OVERRIDES:
        wd = wbget_entity(QID_OVERRIDES[query])
    else:
        wd = wbsearch(query)
        if wd is None:
            for alt in alt_queries(query):
                wd = wbsearch(alt)
                if wd is not None:
                    break
    qid = wd["id"] if wd else None
    label = (wd.get("display", {}).get("label", {}) or {}).get("value") if wd else None
    if not label and wd:
        label = wd.get("label")
    desc = None
    if wd:
        desc = (wd.get("display", {}).get("description", {}) or {}).get("value") \
            or wd.get("description")

    rec = {
        "id": qid or f"royals:{countries[0].lower()}:{slugify(query)}",
        "names": {"en": label or query},
        "country": countries,
        "category": category,
        "subcategory": subcategory,
        "status": status,
        "period": {"founded": founded, "extinct": extinct},
        "head_current": head,
        "notes": notes,
        "sources": ["manual:europe_americas_business"],
        "search_query": query,
        "wikidata_search": {
            "qid": qid,
            "label": label,
            "description": desc,
        },
    }
    return rec


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Processing {len(FAMILIES)} family entries via Wikidata wbsearchentities...",
          file=sys.stderr)

    records: list[dict] = [None] * len(FAMILIES)
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(build_record, row): i for i, row in enumerate(FAMILIES)}
        done = 0
        for fut in as_completed(futures):
            i = futures[fut]
            try:
                records[i] = fut.result()
            except Exception as e:
                row = FAMILIES[i]
                sys.stderr.write(f"[error] {row[0]}: {e}\n")
                # fallback minimal record
                records[i] = {
                    "id": f"royals:{row[1][0].lower()}:{slugify(row[0])}",
                    "names": {"en": row[0]},
                    "country": row[1],
                    "category": row[2],
                    "subcategory": row[3],
                    "status": row[4],
                    "period": {"founded": row[5], "extinct": row[6]},
                    "head_current": row[7],
                    "notes": row[8],
                    "sources": ["manual:europe_americas_business"],
                    "search_query": row[0],
                    "wikidata_search": {"qid": None, "label": None, "description": None},
                }
            done += 1
            if done % 25 == 0:
                print(f"  {done}/{len(FAMILIES)}", file=sys.stderr)

    with OUT_FILE.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Stats
    by_country: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_subcat: dict[str, int] = {}
    qid_hits = 0
    for rec in records:
        for c in rec["country"]:
            by_country[c] = by_country.get(c, 0) + 1
        by_category[rec["category"]] = by_category.get(rec["category"], 0) + 1
        by_subcat[rec["subcategory"]] = by_subcat.get(rec["subcategory"], 0) + 1
        if rec["wikidata_search"]["qid"]:
            qid_hits += 1

    with STATS_FILE.open("w", encoding="utf-8") as f:
        f.write("# Europe + Americas + Global Business families — coverage stats\n")
        f.write(f"# total\t{len(records)}\n")
        f.write(f"# qid_hits\t{qid_hits}\n")
        f.write(f"# qid_miss\t{len(records) - qid_hits}\n")
        f.write("\n# by_country\n")
        for c, n in sorted(by_country.items(), key=lambda x: -x[1]):
            f.write(f"country\t{c}\t{n}\n")
        f.write("\n# by_category\n")
        for c, n in sorted(by_category.items(), key=lambda x: -x[1]):
            f.write(f"category\t{c}\t{n}\n")
        f.write("\n# by_subcategory\n")
        for c, n in sorted(by_subcat.items(), key=lambda x: -x[1]):
            f.write(f"subcategory\t{c}\t{n}\n")

    print(f"\nWrote {len(records)} records to {OUT_FILE}", file=sys.stderr)
    print(f"QID hit rate: {qid_hits}/{len(records)} ({qid_hits*100//len(records)}%)",
          file=sys.stderr)
    print(f"Stats: {STATS_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()
