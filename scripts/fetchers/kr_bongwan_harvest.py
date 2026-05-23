#!/usr/bin/env python3
"""
Harvest the complete list of Korean 본관 from ko.wikipedia 한국의_성씨_목록.

Output: data/raw/manual/kr_bongwan.jsonl  (~1500 본관)

Each record:
{
  "id": null,
  "name_en": "Gyeongju Kim",
  "name_native": "경주 김씨",
  "name_native_lang": "ko",
  "country": ["KR"],
  "category": "clan",
  "surname": "김",
  "bon": "경주",
  "source": "manual:kowiki-bongwan-list",
  "wikidata_qid_hint": null,
  "notes": "Bongwan from 한국의_성씨_목록"
}
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

URL = ("https://ko.wikipedia.org/w/api.php?action=parse&"
       "page=%ED%95%9C%EA%B5%AD%EC%9D%98_%EC%84%B1%EC%94%A8_%EB%AA%A9%EB%A1%9D&"
       "format=json&prop=wikitext")

OUT = Path(__file__).resolve().parents[2] / "data" / "raw" / "manual" / "kr_bongwan.jsonl"

# Hepburn-ish romanization stubs of common surnames
SUR_ROM = {
    "가": "Ga", "간": "Gan", "갈": "Gal", "감": "Gam", "강": "Kang",
    "개": "Gae", "견": "Gyeon", "경": "Kyung", "계": "Gye", "고": "Ko",
    "곡": "Gok", "골": "Gol", "공": "Gong", "곽": "Kwak", "관": "Gwan",
    "교": "Gyo", "구": "Koo", "국": "Kuk", "군": "Gun", "굴": "Gul",
    "궁": "Gung", "궉": "Gwok", "권": "Kwon", "근": "Geun", "금": "Geum",
    "기": "Ki", "길": "Kil", "김": "Kim", "나": "Na", "남": "Nam",
    "낭": "Nang", "내": "Nae", "노": "Noh", "녹": "Nok", "뇌": "Noe",
    "누": "Nu", "단": "Dan", "담": "Dam", "당": "Dang", "대": "Dae",
    "도": "Do", "독고": "Dokgo", "돈": "Don", "동": "Dong", "동방": "Dongbang",
    "두": "Du", "라": "Ra", "류": "Ryu", "마": "Ma", "만": "Man",
    "매": "Mae", "맹": "Maeng", "명": "Myung", "모": "Mo", "목": "Mok",
    "묘": "Myo", "묵": "Muk", "문": "Moon", "미": "Mi", "민": "Min",
    "박": "Park", "반": "Ban", "방": "Bang", "배": "Bae", "백": "Baek",
    "범": "Beom", "변": "Byun", "복": "Bok", "봉": "Bong", "부": "Boo",
    "비": "Bi", "빈": "Bin", "빙": "Bing", "사": "Sa", "사공": "Sagong",
    "산": "San", "삼": "Sam", "상": "Sang", "서": "Seo", "서문": "Seomun",
    "석": "Seok", "선": "Seon", "선우": "Seonwoo", "설": "Seol", "섭": "Seop",
    "성": "Sung", "소": "So", "손": "Son", "송": "Song", "수": "Su",
    "순": "Soon", "승": "Seung", "시": "Si", "신": "Shin", "심": "Sim",
    "아": "A", "안": "An", "애": "Ae", "야": "Ya", "양": "Yang",
    "어": "Eo", "엄": "Eom", "여": "Yeo", "연": "Yeon", "염": "Yeom",
    "엽": "Yeop", "영": "Young", "예": "Ye", "오": "Oh", "옥": "Ok",
    "온": "On", "옹": "Ong", "왕": "Wang", "요": "Yo", "용": "Yong",
    "우": "Woo", "운": "Woon", "원": "Won", "위": "Wi", "유": "Yoo",
    "육": "Yook", "윤": "Yoon", "을": "Eul", "음": "Eum", "응": "Eung",
    "이": "Lee", "인": "In", "임": "Im", "자": "Ja", "장": "Jang",
    "장곡": "Janggok", "재": "Jae", "전": "Jeon", "점": "Jeom", "정": "Jung",
    "제": "Je", "제갈": "Jegal", "조": "Cho", "종": "Jong", "좌": "Jwa",
    "주": "Joo", "준": "Jun", "지": "Ji", "진": "Jin", "차": "Cha",
    "창": "Chang", "채": "Chae", "천": "Cheon", "초": "Cho", "최": "Choi",
    "추": "Choo", "춘": "Chun", "탁": "Tak", "탄": "Tan", "탈": "Tal",
    "탕": "Tang", "태": "Tae", "판": "Pan", "팽": "Paeng", "편": "Pyeon",
    "평": "Pyung", "포": "Po", "표": "Pyo", "풍": "Pung", "피": "Pi",
    "필": "Pil", "하": "Ha", "학": "Hak", "한": "Han", "함": "Ham",
    "해": "Hae", "허": "Heo", "현": "Hyun", "형": "Hyung", "호": "Ho",
    "홍": "Hong", "화": "Hwa", "환": "Hwan", "황": "Hwang", "황보": "Hwangbo",
    "회": "Hoe", "후": "Hu", "흥": "Heung",
}


def fetch():
    req = urllib.request.Request(URL, headers={
        "User-Agent": "RoyalTree-research/0.1 (kibongkook@gmail.com)"
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def parse_bongwan(wt: str) -> list[tuple[str, str]]:
    """Returns list of (bon, surname_hangul) tuples."""
    out = []
    pat = re.compile(r'\[\[([^\[\]\|]+?씨[^\[\]\|]*?)(?:\|[^\[\]]+)?\]\]')
    seen = set()
    for raw in pat.findall(wt):
        s = raw.strip()
        if not s.endswith('씨'):
            continue
        if s in seen:
            continue
        seen.add(s)
        # Drop disambiguation suffix like " (康)"
        s_clean = re.sub(r'\s*\(.+\)$', '', s).strip()
        m = re.match(r'^(.+?)\s+([가-힣])씨$', s_clean)
        if not m:
            continue
        bon, sur = m.group(1).strip(), m.group(2).strip()
        # filter weird ones
        if len(bon) < 1 or len(bon) > 6:
            continue
        out.append((bon, sur))
    return out


def main():
    data = fetch()
    wt = data["parse"]["wikitext"]["*"]
    pairs = parse_bongwan(wt)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with OUT.open("w", encoding="utf-8") as f:
        for bon, sur in pairs:
            sur_rom = SUR_ROM.get(sur, sur)
            name_en = f"{bon} {sur_rom}"
            rec = {
                "id": None,
                "name_en": name_en,
                "name_native": f"{bon} {sur}씨",
                "name_native_lang": "ko",
                "country": ["KR"],
                "category": "clan",
                "surname": sur,
                "bon": bon,
                "period": {"founded": None, "extinct": None},
                "status": "active",
                "aliases": {"hangul": f"{bon}{sur}씨"},
                "source": "manual:kowiki-bongwan-list",
                "wikidata_qid_hint": None,
                "notes": "본관 from ko.wikipedia 한국의_성씨_목록"
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"wrote {n} 본관 records -> {OUT}")


if __name__ == "__main__":
    main()
