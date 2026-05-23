#!/usr/bin/env python3
"""
Region-curated manual record of Asian royal / noble / clan / business families.
Writes data/raw/manual/asia_families.jsonl, one JSON object per line.

Schema (matches CLAUDE.md):
{
  "id": null,                     # Wikidata QID slot — populated later via dedup
  "name_en": "House of Yi",
  "name_native": "전주이씨",
  "name_native_lang": "ko",
  "country": ["KR"],
  "category": "royal|noble|clan|business|religious|tribal",
  "period": {"founded": int|null, "extinct": int|null},
  "status": "active|extinct|deposed|merged",
  "aliases": {...},
  "source": "manual:<short-source-tag>",
  "wikidata_qid_hint": "Q..." or null,
  "notes": "..."
}

Goal: backfill what Wikidata/Wikipedia categories miss for Asia. Priority:
Korea (본관), Japan (kazoku/daimyō/zaibatsu), China (dynasties, Tang elite,
HK/TW tycoons), India (562 princely states + big business houses). SE Asia,
Central Asia: heads-of-house + main business families.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "data" / "raw" / "manual" / "asia_families.jsonl"


def rec(**kwargs):
    """Helper that fills defaults and normalises a family record."""
    r = {
        "id": None,
        "name_en": kwargs.get("name_en"),
        "name_native": kwargs.get("name_native"),
        "name_native_lang": kwargs.get("name_native_lang"),
        "country": kwargs.get("country", []),
        "category": kwargs.get("category"),
        "period": {
            "founded": kwargs.get("founded"),
            "extinct": kwargs.get("extinct"),
        },
        "status": kwargs.get("status", "active"),
        "aliases": kwargs.get("aliases", {}),
        "source": kwargs.get("source", "manual:curated"),
        "wikidata_qid_hint": kwargs.get("qid"),
        "notes": kwargs.get("notes", ""),
    }
    return r


records: list[dict] = []
add = records.append


# =====================================================================
# KOREA  —  본관 본관 본관
# =====================================================================
# Source: 행정안전부 2015 인구주택총조사 성씨·본관, 한국민족문화대백과사전
# 본관 system: same surname has many branches by ancestral seat.
# Listing the largest 본관 per major surname. ~250 well-known + branches.

# Royal & extended royal kin
add(rec(name_en="House of Yi (Jeonju)", name_native="전주이씨", name_native_lang="ko",
        country=["KR"], category="royal", founded=1392, extinct=1910, status="deposed",
        aliases={"hanja": "全州李氏", "romanized": "Jeonju Yi"},
        qid="Q1330632",
        notes="Joseon dynasty royal house; ~3M living descendants; head: Yi Won (Crown Prince Hoeun line)"))
add(rec(name_en="House of Wang (Gaeseong)", name_native="개성왕씨", name_native_lang="ko",
        country=["KR"], category="royal", founded=918, extinct=1392, status="extinct",
        aliases={"hanja": "開城王氏"},
        notes="Goryeo dynasty royal house; many massacred at Joseon founding, survivors changed surname"))
add(rec(name_en="House of Kim (Gyeongju)", name_native="경주김씨", name_native_lang="ko",
        country=["KR"], category="royal", founded=-57, extinct=935, status="extinct",
        aliases={"hanja": "慶州金氏"},
        notes="Silla royal Kim line; one of two ancient Kim royal trees; ~1.7M descendants"))
add(rec(name_en="House of Park (Miryang)", name_native="밀양박씨", name_native_lang="ko",
        country=["KR"], category="royal", founded=-57, status="active",
        aliases={"hanja": "密陽朴氏"},
        notes="Largest Park clan; descended from Silla founder Bak Hyeokgeose; ~3.1M"))
add(rec(name_en="House of Park (Bannam)", name_native="반남박씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "潘南朴氏"}, notes="Major Joseon yangban clan"))
add(rec(name_en="House of Kim (Gimhae)", name_native="김해김씨", name_native_lang="ko",
        country=["KR"], category="royal", founded=42, status="active",
        aliases={"hanja": "金海金氏"},
        notes="Largest Korean clan; descended from King Suro of Geumgwan Gaya; ~4.5M"))
add(rec(name_en="House of Heo (Gimhae)", name_native="김해허씨", name_native_lang="ko",
        country=["KR"], category="royal", founded=48, status="active",
        aliases={"hanja": "金海許氏"},
        notes="Descended from Queen Heo Hwang-ok, wife of Suro; intermarries with Gimhae Kim forbidden"))
add(rec(name_en="House of Heo (Yangcheon)", name_native="양천허씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "陽川許氏"}, notes="Branch from Gimhae Heo via Heo Seon-mun"))
add(rec(name_en="House of Heo (Hayang)", name_native="하양허씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "河陽許氏"}))
add(rec(name_en="House of Heo (Taein)", name_native="태인허씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "泰仁許氏"}))
add(rec(name_en="House of Kim (Andong, Old)", name_native="구안동김씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "舊安東金氏"}, notes="Goryeo-origin Andong Kim, distinct from New Andong Kim"))
add(rec(name_en="House of Kim (Andong, New)", name_native="신안동김씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "新安東金氏"},
        notes="Sedo politics powerhouse late Joseon (Sunjo–Cheoljong); Kim Jo-sun era"))
add(rec(name_en="House of Kim (Gwangsan)", name_native="광산김씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "光山金氏"}, notes="One of the great Joseon yangban; ~830k"))
add(rec(name_en="House of Kim (Uiseong)", name_native="의성김씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "義城金氏"}, notes="Major Andong-region yangban; ~250k"))
add(rec(name_en="House of Kim (Cheongpung)", name_native="청풍김씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "淸風金氏"}, notes="Queen Inhyeon clan; ~140k"))
add(rec(name_en="House of Kim (Yeonan)", name_native="연안김씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "延安金氏"}))
add(rec(name_en="House of Kim (Cheongdo)", name_native="청도김씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "淸道金氏"}))
add(rec(name_en="House of Kim (Suwon)", name_native="수원김씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "水原金氏"}))
add(rec(name_en="House of Kim (Gimnyeong)", name_native="김녕김씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "金寧金氏"}))
add(rec(name_en="House of Kim (Sangsan)", name_native="상산김씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "商山金氏"}))
add(rec(name_en="House of Kim (Eonyang)", name_native="언양김씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "彦陽金氏"}))
add(rec(name_en="House of Kim (Naju)", name_native="나주김씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "羅州金氏"}))
add(rec(name_en="House of Kim (Pungsan)", name_native="풍산김씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "豊山金氏"}, notes="Andong yangban; literati"))
add(rec(name_en="House of Kim (Ulsan)", name_native="울산김씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "蔚山金氏"}, notes="Inha Group / Hanjin Choi linkage"))
add(rec(name_en="House of Lee (Gyeongju)", name_native="경주이씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "慶州李氏"}, notes="Originated with Silla minister Alpyeong; ~1.4M"))
add(rec(name_en="House of Lee (Hansan)", name_native="한산이씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "韓山李氏"}, notes="Mok-eun Yi Saek lineage"))
add(rec(name_en="House of Lee (Yeoju)", name_native="여주이씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "驪州李氏"}, notes="Seongho Yi Ik / Silhak"))
add(rec(name_en="House of Lee (Yeonan)", name_native="연안이씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "延安李氏"}))
add(rec(name_en="House of Lee (Deoksu)", name_native="덕수이씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "德水李氏"}, notes="Yi Sun-sin's clan; Yulgok Yi I"))
add(rec(name_en="House of Lee (Jeonui)", name_native="전의이씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "全義李氏"}))
add(rec(name_en="House of Lee (Goseong)", name_native="고성이씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "固城李氏"}))
add(rec(name_en="House of Lee (Wonju)", name_native="원주이씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "原州李氏"}))
add(rec(name_en="House of Lee (Hapcheon)", name_native="합천이씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "陜川李氏"}))
add(rec(name_en="House of Lee (Hakseong)", name_native="학성이씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "鶴城李氏"}))
add(rec(name_en="House of Lee (Pyeongchang)", name_native="평창이씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "平昌李氏"}))
add(rec(name_en="House of Lee (Yangseong)", name_native="양성이씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "陽城李氏"}))
add(rec(name_en="House of Lee (Seongju)", name_native="성주이씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "星州李氏"}))
add(rec(name_en="House of Lee (Wansan)", name_native="완산이씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "完山李氏"}, notes="Variant of Jeonju Yi"))
add(rec(name_en="House of Yu (Munhwa)", name_native="문화유씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "文化柳氏"}))
add(rec(name_en="House of Yu (Jinju)", name_native="진주류씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "晉州柳氏"}))
add(rec(name_en="House of Yu (Pungsan)", name_native="풍산류씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "豊山柳氏"}, notes="Yu Seong-ryong; Hahoe village; literati"))
add(rec(name_en="House of Yu (Jeonju)", name_native="전주류씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "全州柳氏"}))
add(rec(name_en="House of Choe (Gyeongju)", name_native="경주최씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "慶州崔氏"}, notes="Choi Chiwon lineage; ~1M; Choi Jeong-ho noted scholar"))
add(rec(name_en="House of Choe (Haeju)", name_native="해주최씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "海州崔氏"}))
add(rec(name_en="House of Choe (Jeonju)", name_native="전주최씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "全州崔氏"}))
add(rec(name_en="House of Choe (Gangneung)", name_native="강릉최씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "江陵崔氏"}))
add(rec(name_en="House of Choe (Tamjin)", name_native="탐진최씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "耽津崔氏"}))
add(rec(name_en="House of Choe (Cheongju)", name_native="청주최씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "淸州崔氏"}))
add(rec(name_en="House of Choe (Suseong)", name_native="수성최씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "隋城崔氏"}))
add(rec(name_en="House of Jeong (Dongnae)", name_native="동래정씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "東萊鄭氏"}, notes="Jeong Mong-ju; large Joseon clan"))
add(rec(name_en="House of Jeong (Yeonil)", name_native="연일정씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "延日鄭氏"}, notes="Po-eun Jeong Mong-ju ancestor; Yeongil Jeong"))
add(rec(name_en="House of Jeong (Onyang)", name_native="온양정씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "溫陽鄭氏"}))
add(rec(name_en="House of Jeong (Cheongju)", name_native="청주정씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "淸州鄭氏"}))
add(rec(name_en="House of Jeong (Hadong)", name_native="하동정씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "河東鄭氏"}))
add(rec(name_en="House of Jeong (Bongha)", name_native="봉화정씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "奉化鄭氏"}, notes="Jeong Do-jeon; founding minister of Joseon"))
add(rec(name_en="House of Jeong (Jinju)", name_native="진주정씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "晉州鄭氏"}))
add(rec(name_en="House of Jeong (Gyeongju)", name_native="경주정씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "慶州鄭氏"}))
add(rec(name_en="House of Jeong (Naju)", name_native="나주정씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "羅州丁氏"}, notes="Dasan Jeong Yak-yong lineage; Silhak; different '정' character"))
add(rec(name_en="House of Yun (Haepyeong)", name_native="해평윤씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "海平尹氏"}))
add(rec(name_en="House of Yun (Papyeong)", name_native="파평윤씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "坡平尹氏"}, notes="Largest Yun clan; Queen Yun lineage; ~770k"))
add(rec(name_en="House of Yun (Haenam)", name_native="해남윤씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "海南尹氏"}, notes="Gosan Yun Seon-do; Nokwoodang"))
add(rec(name_en="House of Yun (Chilwon)", name_native="칠원윤씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "漆原尹氏"}, notes="Yoon Posun president lineage"))
add(rec(name_en="House of Yun (Muan)", name_native="무송윤씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "茂松尹氏"}))
add(rec(name_en="House of Han (Cheongju)", name_native="청주한씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "淸州韓氏"}, notes="Han Myeong-hoe; Sejo era; ~700k"))
add(rec(name_en="House of An (Sunheung)", name_native="순흥안씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "順興安氏"}, notes="An Hyang (Confucian revival); largest An clan"))
add(rec(name_en="House of An (Gwangju)", name_native="광주안씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "廣州安氏"}))
add(rec(name_en="House of An (Juksan)", name_native="죽산안씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "竹山安氏"}))
add(rec(name_en="House of An (Tamjin)", name_native="탐진안씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "耽津安氏"}))
add(rec(name_en="House of Song (Eunjin)", name_native="은진송씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "恩津宋氏"}, notes="Uam Song Si-yeol; Hoedeok; literati"))
add(rec(name_en="House of Song (Yeosan)", name_native="여산송씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "礪山宋氏"}))
add(rec(name_en="House of Song (Jincheon)", name_native="진천송씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "鎭川宋氏"}))
add(rec(name_en="House of Cho (Hanyang)", name_native="한양조씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "漢陽趙氏"}, notes="Cho Gwang-jo; Sarim faction"))
add(rec(name_en="House of Cho (Pungyang)", name_native="풍양조씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "豊壤趙氏"}, notes="Late-Joseon sedo politics with Andong Kim"))
add(rec(name_en="House of Cho (Yangju)", name_native="양주조씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "楊州趙氏"}))
add(rec(name_en="House of Cho (Baechun)", name_native="배천조씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "白川趙氏"}))
add(rec(name_en="House of Cho (Imcheon)", name_native="임천조씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "林川趙氏"}))
add(rec(name_en="House of Sin (Pyeongsan)", name_native="평산신씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "平山申氏"}, notes="Largest Shin clan"))
add(rec(name_en="House of Sin (Goryeong)", name_native="고령신씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "高靈申氏"}, notes="Sin Suk-ju lineage"))
add(rec(name_en="House of Sin (Yeongwol)", name_native="영월신씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "寧越辛氏"}))
add(rec(name_en="House of Sin (Geochang)", name_native="거창신씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "居昌愼氏"}))
add(rec(name_en="House of Oh (Haeju)", name_native="해주오씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "海州吳氏"}))
add(rec(name_en="House of Oh (Bosung)", name_native="보성오씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "寶城吳氏"}))
add(rec(name_en="House of Oh (Naju)", name_native="나주오씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "羅州吳氏"}))
add(rec(name_en="House of Oh (Hampyeong)", name_native="함평오씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "咸平吳氏"}))
add(rec(name_en="House of Hwang (Jangsu)", name_native="장수황씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "長水黃氏"}, notes="Hwang Hui prime minister of Sejong"))
add(rec(name_en="House of Hwang (Changwon)", name_native="창원황씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "昌原黃氏"}))
add(rec(name_en="House of Hwang (Pyeonghae)", name_native="평해황씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "平海黃氏"}))
add(rec(name_en="House of Hwang (Hoedeok)", name_native="회덕황씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "懷德黃氏"}))
add(rec(name_en="House of Kang (Jinju)", name_native="진주강씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "晉州姜氏"}, notes="Largest Kang clan; ~1.04M"))
add(rec(name_en="House of Kang (Geumcheon)", name_native="금천강씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "衿川姜氏"}))
add(rec(name_en="House of Kang (Sincheon)", name_native="신천강씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "信川康氏"}, notes="Queen Sindeok / Joseon founding queen"))
add(rec(name_en="House of Im (Pyeongtaek)", name_native="평택임씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "平澤林氏"}))
add(rec(name_en="House of Im (Naju)", name_native="나주임씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "羅州林氏"}))
add(rec(name_en="House of Im (Buan)", name_native="부안임씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "扶安林氏"}))
add(rec(name_en="House of Im (Pungcheon)", name_native="풍천임씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "豊川任氏"}, notes="Different 임 character (任)"))
add(rec(name_en="House of Seo (Daegu)", name_native="달성서씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "達城徐氏"}))
add(rec(name_en="House of Seo (Icheon)", name_native="이천서씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "利川徐氏"}, notes="Largest Seo clan"))
add(rec(name_en="House of Seo (Daeryeong)", name_native="대령서씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "大寧徐氏"}))
add(rec(name_en="House of Bae (Seongju)", name_native="성주배씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "星州裵氏"}))
add(rec(name_en="House of Bae (Bunseong)", name_native="분성배씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "盆城裵氏"}))
add(rec(name_en="House of Bae (Daegu)", name_native="달성배씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "達城裵氏"}))
add(rec(name_en="House of Baek (Suwon)", name_native="수원백씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "水原白氏"}))
add(rec(name_en="House of Baek (Daeheung)", name_native="대흥백씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "大興白氏"}))
add(rec(name_en="House of Jang (Indong)", name_native="인동장씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "仁同張氏"}, notes="Largest Jang clan; Jang Hyeon-gwang Confucian"))
add(rec(name_en="House of Jang (Deoksu)", name_native="덕수장씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "德水張氏"}))
add(rec(name_en="House of Jang (Heungseong)", name_native="흥성장씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "興城張氏"}))
add(rec(name_en="House of Jang (Anjeong)", name_native="안동장씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "安東張氏"}))
add(rec(name_en="House of Jang (Mokcheon)", name_native="목천장씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "木川張氏"}))
add(rec(name_en="House of Ko (Jeju)", name_native="제주고씨", name_native_lang="ko",
        country=["KR"], category="royal", status="active",
        aliases={"hanja": "濟州高氏"}, notes="Tamna kingdom royal lineage; one of three Jeju founders"))
add(rec(name_en="House of Yang (Jeju)", name_native="제주양씨", name_native_lang="ko",
        country=["KR"], category="royal", status="active",
        aliases={"hanja": "濟州梁氏"}, notes="Tamna kingdom royal lineage; second Jeju founder"))
add(rec(name_en="House of Bu (Jeju)", name_native="제주부씨", name_native_lang="ko",
        country=["KR"], category="royal", status="active",
        aliases={"hanja": "濟州夫氏"}, notes="Tamna kingdom royal lineage; third Jeju founder"))
add(rec(name_en="House of Moon (Nampyeong)", name_native="남평문씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "南平文氏"}, notes="Largest Moon clan; Moon Ik-jeom cotton lineage; Moon Jae-in"))
add(rec(name_en="House of Min (Yeoheung)", name_native="여흥민씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "驪興閔氏"}, notes="Empress Myeongseong / late-Joseon dominant clan"))
add(rec(name_en="House of Hong (Namyang)", name_native="남양홍씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "南陽洪氏"}, notes="Largest Hong clan; two distinct origin Namyang Hong lines"))
add(rec(name_en="House of Hong (Pungsan)", name_native="풍산홍씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "豊山洪氏"}, notes="Hong Bong-han; Lady Hyegyeong's clan"))
add(rec(name_en="House of Ryu (Goheung)", name_native="고흥류씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "高興柳氏"}))
add(rec(name_en="House of Cha (Yeonan)", name_native="연안차씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "延安車氏"}))
add(rec(name_en="House of Gu (Neungseong)", name_native="능성구씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "綾城具氏"}, notes="LG Group founding clan (Gu Cha-gyeong)"))
add(rec(name_en="House of Heo (Gimhae LG)", name_native="김해허씨(LG)", name_native_lang="ko",
        country=["KR"], category="business", status="active",
        aliases={"hanja": "金海許氏"}, notes="LG co-founding Heo branch; later GS spinoff"))
add(rec(name_en="House of Noh (Gwangsan)", name_native="광산노씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "光山盧氏"}, notes="President Roh Tae-woo lineage variant"))
add(rec(name_en="House of Noh (Gyoha)", name_native="교하노씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "交河盧氏"}))
add(rec(name_en="House of Roh (Pungcheon)", name_native="풍천노씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "豊川盧氏"}))
add(rec(name_en="House of Kwon (Andong)", name_native="안동권씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "安東權氏"}, notes="Almost all Kwon clans descend from Andong Kwon; ~700k"))
add(rec(name_en="House of Kwon (Yecheon)", name_native="예천권씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "醴泉權氏"}))
add(rec(name_en="House of Son (Miryang)", name_native="밀양손씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "密陽孫氏"}))
add(rec(name_en="House of Son (Gyeongju)", name_native="경주손씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "慶州孫氏"}))
add(rec(name_en="House of Son (Pyeonghae)", name_native="평해손씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "平海孫氏"}))
add(rec(name_en="House of Cho (Changnyeong)", name_native="창녕조씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "昌寧曺氏"}, notes="Nammyeong Jo Sik; Yeongnam Sarim; ~390k"))
add(rec(name_en="House of Pi (Hongcheon)", name_native="홍천피씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "洪川皮氏"}))
add(rec(name_en="House of Jeon (Cheonan)", name_native="천안전씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "天安全氏"}))
add(rec(name_en="House of Jeon (Jeongseon)", name_native="정선전씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "旌善全氏"}))
add(rec(name_en="House of Jeon (Gyeongsan)", name_native="경산전씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "慶山全氏"}))
add(rec(name_en="House of Jeon (Yongcheon)", name_native="용궁전씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "龍宮全氏"}))
add(rec(name_en="House of Ahn (Jukgye)", name_native="죽계안씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "竹溪安氏"}))
add(rec(name_en="House of Pang (Onyang)", name_native="온양방씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "溫陽方氏"}))
add(rec(name_en="House of Bang (Namyang)", name_native="남양방씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "南陽房氏"}))
add(rec(name_en="House of Ji (Chungju)", name_native="충주지씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "忠州池氏"}))
add(rec(name_en="House of Maeng (Sincheon)", name_native="신창맹씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "新昌孟氏"}, notes="Maeng Sa-seong of early Joseon"))
add(rec(name_en="House of Eom (Yeongwol)", name_native="영월엄씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "寧越嚴氏"}))
add(rec(name_en="House of Yeo (Hamyang)", name_native="함양여씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "咸陽呂氏"}))
add(rec(name_en="House of Yu (Gigye)", name_native="기계유씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "杞溪兪氏"}, notes="Different 유 character (兪)"))
add(rec(name_en="House of Yu (Chang-won)", name_native="창원유씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "昌原兪氏"}))
add(rec(name_en="House of Yu (Mooan)", name_native="무안유씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "務安兪氏"}))
add(rec(name_en="House of Sim (Cheongsong)", name_native="청송심씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "靑松沈氏"}, notes="Three queens; ~250k"))
add(rec(name_en="House of Sim (Punsan)", name_native="삼척심씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "三陟沈氏"}))
add(rec(name_en="House of Pyo (Sincheon)", name_native="신창표씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "新昌表氏"}))
add(rec(name_en="House of Ha (Jinju)", name_native="진주하씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "晉州河氏"}))
add(rec(name_en="House of Pyeon (Geochang)", name_native="거창편씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "居昌片氏"}))
add(rec(name_en="House of Kyung (Cheongju)", name_native="청주경씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "淸州慶氏"}))
add(rec(name_en="House of Tak (Gwangsan)", name_native="광산탁씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "光山卓氏"}))
add(rec(name_en="House of Geum (Bonghwa)", name_native="봉화금씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "奉化琴氏"}))
add(rec(name_en="House of Kim (Andong, Geumgye)", name_native="안동김씨(금계)", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        notes="Kim Seong-il (Hak-bong) lineage; Andong Geumgye village"))
add(rec(name_en="House of Lee (Jincheon)", name_native="진천이씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "鎭川李氏"}))
add(rec(name_en="House of Park (Gosan)", name_native="고성박씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "高城朴氏"}))
add(rec(name_en="House of Park (Yeonghae)", name_native="영해박씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "寧海朴氏"}))
add(rec(name_en="House of Park (Hampyeong)", name_native="함양박씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "咸陽朴氏"}))
add(rec(name_en="House of Park (Suncheon)", name_native="순천박씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "順天朴氏"}, notes="Park Eung-bok lineage"))
add(rec(name_en="House of Park (Chukneung)", name_native="죽산박씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "竹山朴氏"}))
add(rec(name_en="House of Park (Muan)", name_native="무안박씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "務安朴氏"}))
add(rec(name_en="House of Park (Chungju)", name_native="충주박씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "忠州朴氏"}))
add(rec(name_en="House of Park (Sangju)", name_native="상주박씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "尙州朴氏"}))
add(rec(name_en="House of Park (Bongsan)", name_native="봉산박씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "鳳山朴氏"}))
add(rec(name_en="House of Park (Goryeong)", name_native="고령박씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "高靈朴氏"}, notes="President Park Chung-hee lineage"))
add(rec(name_en="House of Park (Pyeongtaek)", name_native="평택박씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "平澤朴氏"}))
add(rec(name_en="House of Cheon (Yeongyang)", name_native="영양천씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "潁陽千氏"}))
add(rec(name_en="House of Don (Sincheon)", name_native="신천돈씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "信川敦氏"}))
add(rec(name_en="House of Bok (Myeoncheon)", name_native="면천복씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "沔川卜氏"}))
add(rec(name_en="House of Pyeon (Jeolla)", name_native="절강편씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "浙江片氏"}))
add(rec(name_en="House of Ye (Hanyang)", name_native="한양예씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "漢陽芮氏"}))
add(rec(name_en="House of Nam (Uiryeong)", name_native="의령남씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "宜寧南氏"}, notes="Largest Nam clan"))
add(rec(name_en="House of Nam (Yeongyang)", name_native="영양남씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "英陽南氏"}))
add(rec(name_en="House of Yeom (Paju)", name_native="파주염씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "坡州廉氏"}))
add(rec(name_en="House of No (Gyoha)", name_native="교하노씨(盧)", name_native_lang="ko",
        country=["KR"], category="noble", status="active"))
add(rec(name_en="House of Gil (Haepyeong)", name_native="해평길씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active"))
add(rec(name_en="House of Mun (Gangneung)", name_native="강릉문씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "江陵文氏"}))
add(rec(name_en="House of Cha (Yongin)", name_native="용인차씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "龍仁車氏"}))
add(rec(name_en="House of Gye (Suan)", name_native="수안계씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "遂安桂氏"}))
add(rec(name_en="House of Wi (Jangheung)", name_native="장흥위씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "長興魏氏"}))
add(rec(name_en="House of Pung (Imcheon)", name_native="임천풍씨", name_native_lang="ko",
        country=["KR"], category="noble", status="active",
        aliases={"hanja": "任川馮氏"}))

# Korean chaebol / business families
add(rec(name_en="Samsung Lee Family", name_native="삼성 이씨 (의령)", name_native_lang="ko",
        country=["KR"], category="business", founded=1938, status="active",
        notes="Lee Byung-chul (Uiryeong-Lee subset) → Lee Kun-hee → Lee Jae-yong; Samsung",
        qid="Q333856"))
add(rec(name_en="Hyundai Chung Family", name_native="현대 정씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1947, status="active",
        notes="Chung Ju-yung (Hadong Jeong); Hyundai Motor (Eui-sun), HD Hyundai, Hyundai Dept Store branches",
        qid="Q484847"))
add(rec(name_en="LG Koo Family", name_native="LG 구씨 (능성)", name_native_lang="ko",
        country=["KR"], category="business", founded=1947, status="active",
        notes="Koo In-hwoi (Neungseong Gu) → Koo Bon-moo → Koo Kwang-mo; LG Group",
        qid="Q189867"))
add(rec(name_en="GS Heo Family", name_native="GS 허씨 (김해)", name_native_lang="ko",
        country=["KR"], category="business", founded=2005, status="active",
        notes="Spun off from LG by Heo Chang-soo (Gimhae Heo); GS Holdings",
        qid="Q487675"))
add(rec(name_en="SK Choi Family", name_native="SK 최씨 (수원)", name_native_lang="ko",
        country=["KR"], category="business", founded=1953, status="active",
        notes="Choi Jong-gun → Choi Jong-hyun → Chey Tae-won; SK Group",
        qid="Q489097"))
add(rec(name_en="Hanwha Kim Family", name_native="한화 김씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1952, status="active",
        notes="Kim Jong-hee → Kim Seung-yeon → Kim Dong-kwan; Hanwha Group",
        qid="Q487921"))
add(rec(name_en="Lotte Shin Family", name_native="롯데 신씨 (영산)", name_native_lang="ko",
        country=["KR", "JP"], category="business", founded=1948, status="active",
        notes="Shin Kyuk-ho (Shigemitsu Takeo); Korea-Japan crossing; Shin Dong-bin",
        qid="Q485145"))
add(rec(name_en="Doosan Park Family", name_native="두산 박씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1896, status="active",
        notes="Park Seung-jik → Park Doo-byung → Park Yong-maan; oldest Korean conglomerate",
        qid="Q487497"))
add(rec(name_en="POSCO (state-controlled)", name_native="포스코", name_native_lang="ko",
        country=["KR"], category="business", founded=1968, status="active",
        notes="State-founded under Park Tae-joon; now no controlling family; flagged as business not family-controlled"))
add(rec(name_en="Hanjin Cho Family", name_native="한진 조씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1945, status="active",
        notes="Cho Joong-hoon → Cho Yang-ho → Cho Won-tae; Korean Air"))
add(rec(name_en="CJ Lee Family", name_native="CJ 이씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1996, status="active",
        notes="Lee Maeng-hee branch from Samsung; CJ Group (Lee Jay-hyun)"))
add(rec(name_en="Shinsegae Lee Family", name_native="신세계 이씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1991, status="active",
        notes="Lee Myung-hee (sister of Lee Kun-hee); Shinsegae / E-mart / Chung Yong-jin"))
add(rec(name_en="Hyosung Cho Family", name_native="효성 조씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1957, status="active",
        notes="Cho Hong-jai → Cho Suck-rai → Cho Hyun-joon; Hyosung"))
add(rec(name_en="Kolon Lee Family", name_native="코오롱 이씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1957, status="active",
        notes="Lee Won-man → Lee Dong-chan → Lee Woong-yeul"))
add(rec(name_en="Kumho Asiana Park Family", name_native="금호아시아나 박씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1946, status="active",
        notes="Park In-cheon → Park Sam-koo / Park Chan-koo split"))
add(rec(name_en="Daelim Lee Family", name_native="대림 이씨 (DL)", name_native_lang="ko",
        country=["KR"], category="business", founded=1939, status="active",
        notes="Lee Jae-joon → Lee Joon-yong → Lee Hae-wook; DL Group"))
add(rec(name_en="Booyoung Lee Family", name_native="부영 이씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1983, status="active",
        notes="Lee Joong-keun"))
add(rec(name_en="Taekwang Lee Family", name_native="태광 이씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1950, status="active",
        notes="Lee Im-yong → Lee Ho-jin"))
add(rec(name_en="Daewoong Yoon Family", name_native="대웅 윤씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1945, status="active",
        notes="Yoon Young-hwan → Yoon Jae-seung; Daewoong Pharmaceutical"))
add(rec(name_en="Nongshim Shin Family", name_native="농심 신씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1965, status="active",
        notes="Shin Choon-ho (brother of Lotte's Shin Kyuk-ho); Nongshim"))
add(rec(name_en="Orion Dam Family", name_native="오리온 담씨", name_native_lang="ko",
        country=["KR"], category="business", founded=2001, status="active",
        notes="Dam Chul-kon"))
add(rec(name_en="Crown Confectionery Yoon Family", name_native="크라운 윤씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1947, status="active"))
add(rec(name_en="Ottogi Ham Family", name_native="오뚜기 함씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1969, status="active",
        notes="Ham Tae-ho → Ham Young-joon"))
add(rec(name_en="Kakao Kim Family", name_native="카카오 김씨", name_native_lang="ko",
        country=["KR"], category="business", founded=2006, status="active",
        notes="Kim Beom-su (founder); newer-generation tech family"))
add(rec(name_en="Naver Lee Family", name_native="네이버 이씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1999, status="active",
        notes="Lee Hae-jin (founder); also founded LINE in Japan"))
add(rec(name_en="Coupang Kim Family", name_native="쿠팡 김씨", name_native_lang="ko",
        country=["KR", "US"], category="business", founded=2010, status="active",
        notes="Kim Bom (Bom Suk Kim)"))
add(rec(name_en="Celltrion Seo Family", name_native="셀트리온 서씨", name_native_lang="ko",
        country=["KR"], category="business", founded=2002, status="active",
        notes="Seo Jung-jin"))
add(rec(name_en="Mirae Asset Park Family", name_native="미래에셋 박씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1997, status="active",
        notes="Park Hyeon-joo"))
add(rec(name_en="Boryung Kim Family", name_native="보령제약 김씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1957, status="active"))
add(rec(name_en="Yuhan Yu Family", name_native="유한양행 유씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1926, status="active",
        notes="Yu Il-han; founder donated all stock — no controlling family today"))
add(rec(name_en="OCI Lee Family", name_native="OCI 이씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1959, status="active"))
add(rec(name_en="HiteJinro Park Family", name_native="하이트진로 박씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1924, status="active"))
add(rec(name_en="Aekyung Chae Family", name_native="애경 채씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1954, status="active"))
add(rec(name_en="Amorepacific Suh Family", name_native="아모레퍼시픽 서씨", name_native_lang="ko",
        country=["KR"], category="business", founded=1945, status="active",
        notes="Suh Sung-hwan → Suh Kyung-bae"))
add(rec(name_en="LF Koo Family", name_native="LF 구씨", name_native_lang="ko",
        country=["KR"], category="business", founded=2007, status="active",
        notes="LG Fashion spin-off; Koo Bon-geol"))


# =====================================================================
# JAPAN
# =====================================================================
# Imperial + Former Princely (旧宮家)
add(rec(name_en="Imperial House of Japan", name_native="皇室", name_native_lang="ja",
        country=["JP"], category="royal", founded=-660, status="active",
        notes="Yamato dynasty; world's oldest continuous monarchy; Emperor Naruhito",
        qid="Q186040"))
add(rec(name_en="Fushimi-no-miya", name_native="伏見宮", name_native_lang="ja",
        country=["JP"], category="royal", founded=1409, extinct=1947, status="deposed",
        notes="Senior cadet line; eldest of the shinnōke; abolished 1947",
        qid="Q1192353"))
add(rec(name_en="Katsura-no-miya", name_native="桂宮", name_native_lang="ja",
        country=["JP"], category="royal", founded=1589, extinct=1881, status="extinct"))
add(rec(name_en="Arisugawa-no-miya", name_native="有栖川宮", name_native_lang="ja",
        country=["JP"], category="royal", founded=1625, extinct=1913, status="extinct"))
add(rec(name_en="Kan'in-no-miya", name_native="閑院宮", name_native_lang="ja",
        country=["JP"], category="royal", founded=1710, extinct=1988, status="extinct"))
add(rec(name_en="Yamashina-no-miya", name_native="山階宮", name_native_lang="ja",
        country=["JP"], category="royal", founded=1864, extinct=1947, status="deposed"))
add(rec(name_en="Kuni-no-miya", name_native="久邇宮", name_native_lang="ja",
        country=["JP"], category="royal", founded=1875, extinct=1947, status="deposed",
        notes="Empress Kojun's natal house"))
add(rec(name_en="Nashimoto-no-miya", name_native="梨本宮", name_native_lang="ja",
        country=["JP"], category="royal", founded=1870, extinct=1947, status="deposed"))
add(rec(name_en="Higashi-Fushimi-no-miya", name_native="東伏見宮", name_native_lang="ja",
        country=["JP"], category="royal", founded=1903, extinct=1947, status="deposed"))
add(rec(name_en="Kachō-no-miya", name_native="華頂宮", name_native_lang="ja",
        country=["JP"], category="royal", founded=1868, extinct=1947, status="deposed"))
add(rec(name_en="Kitashirakawa-no-miya", name_native="北白川宮", name_native_lang="ja",
        country=["JP"], category="royal", founded=1870, extinct=1947, status="deposed"))
add(rec(name_en="Komatsu-no-miya", name_native="小松宮", name_native_lang="ja",
        country=["JP"], category="royal", founded=1870, extinct=1903, status="extinct"))
add(rec(name_en="Higashikuni-no-miya", name_native="東久邇宮", name_native_lang="ja",
        country=["JP"], category="royal", founded=1906, extinct=1947, status="deposed",
        notes="Prince Naruhiko; brief PM post-war"))
add(rec(name_en="Asaka-no-miya", name_native="朝香宮", name_native_lang="ja",
        country=["JP"], category="royal", founded=1906, extinct=1947, status="deposed"))
add(rec(name_en="Takeda-no-miya", name_native="竹田宮", name_native_lang="ja",
        country=["JP"], category="royal", founded=1906, extinct=1947, status="deposed"))
add(rec(name_en="Akishino-no-miya", name_native="秋篠宮", name_native_lang="ja",
        country=["JP"], category="royal", founded=1990, status="active",
        notes="Cadet branch of current imperial house; Crown Prince Fumihito"))
add(rec(name_en="Hitachi-no-miya", name_native="常陸宮", name_native_lang="ja",
        country=["JP"], category="royal", founded=1964, status="active"))
add(rec(name_en="Mikasa-no-miya", name_native="三笠宮", name_native_lang="ja",
        country=["JP"], category="royal", founded=1935, status="active"))
add(rec(name_en="Takamado-no-miya", name_native="高円宮", name_native_lang="ja",
        country=["JP"], category="royal", founded=1984, status="active"))

# Five Regent Houses (摂家)
add(rec(name_en="Konoe family", name_native="近衛家", name_native_lang="ja",
        country=["JP"], category="noble", founded=1166, status="active",
        notes="Eldest of go-sekke (Five Regents); Fujiwara line; Konoe Fumimaro PM"))
add(rec(name_en="Kujō family", name_native="九条家", name_native_lang="ja",
        country=["JP"], category="noble", founded=1185, status="active"))
add(rec(name_en="Nijō family", name_native="二条家", name_native_lang="ja",
        country=["JP"], category="noble", founded=1239, status="active"))
add(rec(name_en="Ichijō family", name_native="一条家", name_native_lang="ja",
        country=["JP"], category="noble", founded=1248, status="active"))
add(rec(name_en="Takatsukasa family", name_native="鷹司家", name_native_lang="ja",
        country=["JP"], category="noble", founded=1252, status="active"))

# Seiga (清華家)
for k, hanja in [("Sanjō","三条"), ("Saionji","西園寺"), ("Tokudaiji","徳大寺"),
                 ("Kazan'in","花山院"), ("Kikutei","菊亭/今出川"), ("Daigo","醍醐"),
                 ("Hirohata","広幡"), ("Ōinomikado","大炊御門"), ("Kuga","久我")]:
    add(rec(name_en=f"{k} family", name_native=f"{hanja}家", name_native_lang="ja",
            country=["JP"], category="noble", status="active",
            notes="Seiga-ke / 清華家 — second-rank kuge below sekke"))

# Daimyō clans (sample of the ~300; focus on major han)
DAIMYO = [
    ("Tokugawa", "徳川氏", "Edo shogunate ruling clan; 5 main branches + 御三家 + 御三卿", "Q47863"),
    ("Tokugawa (Owari)", "尾張徳川家", "Gosanke — Owari (Nagoya)", None),
    ("Tokugawa (Kii)", "紀州徳川家", "Gosanke — Kii (Wakayama)", None),
    ("Tokugawa (Mito)", "水戸徳川家", "Gosanke — Mito", None),
    ("Hitotsubashi-Tokugawa", "一橋徳川家", "Gosankyō", None),
    ("Tayasu-Tokugawa", "田安徳川家", "Gosankyō", None),
    ("Shimizu-Tokugawa", "清水徳川家", "Gosankyō", None),
    ("Matsudaira", "松平氏", "Tokugawa branch; many sub-branches (Aizu, Echizen, etc.)", None),
    ("Aizu-Matsudaira", "会津松平家", "Hoshina/Matsudaira of Aizu; bakufu loyalist Boshin", None),
    ("Echizen-Matsudaira", "越前松平家", "Fukui domain", None),
    ("Shimazu", "島津氏", "Satsuma domain; Meiji Restoration core; Imperial in-laws", "Q269614"),
    ("Mōri", "毛利氏", "Chōshū (Hagi) domain; Meiji Restoration core", "Q1330554"),
    ("Maeda", "前田氏", "Kaga 1M-koku; second-largest domain", "Q1364148"),
    ("Date", "伊達氏", "Sendai domain; Date Masamune", "Q1208183"),
    ("Uesugi", "上杉氏", "Yonezawa domain; descended from Fujiwara/Kantō", "Q1364098"),
    ("Hosokawa", "細川氏", "Kumamoto domain; Hosokawa Morihiro PM 1993", "Q1330440"),
    ("Asano", "浅野氏", "Aki Hiroshima domain; Akō affair clan", None),
    ("Ikeda", "池田氏", "Okayama/Tottori domains", None),
    ("Mōri (Iwami)", "石見毛利家", None, None),
    ("Sō", "宗氏", "Tsushima domain; Korea trade gateway", None),
    ("Nabeshima", "鍋島氏", "Saga domain", None),
    ("Yamanouchi", "山内氏", "Tosa domain; Sakamoto Ryōma's lord", None),
    ("Chōsokabe", "長宗我部氏", "Tosa pre-Yamanouchi; sengoku", None),
    ("Sengoku", "仙石氏", "Izushi/Komoro domains", None),
    ("Honda", "本多氏", "Multiple branches; Honda Tadakatsu lineage", None),
    ("Ii", "井伊氏", "Hikone domain; Ii Naosuke tairō", None),
    ("Sakai", "酒井氏", "Multiple Edo daimyō branches", None),
    ("Tachibana", "立花氏", "Yanagawa domain (Chikugo)", None),
    ("Kuroda", "黒田氏", "Fukuoka domain", None),
    ("Hachisuka", "蜂須賀氏", "Tokushima/Awa domain", None),
    ("Yanagisawa", "柳沢氏", "Kōriyama (Yamato) domain", None),
    ("Inaba", "稲葉氏", "Yodo domain", None),
    ("Itakura", "板倉氏", "Multiple bakufu rōjū houses", None),
    ("Aoyama", "青山氏", "Sasayama domain (Tamba)", None),
    ("Akimoto", "秋元氏", "Yamagata domain", None),
    ("Andō", "安藤氏", "Iwakitaira domain", None),
    ("Doi", "土井氏", "Koga / Kariya domains", None),
    ("Hori", "堀氏", "Suzaka / Murakami domains", None),
    ("Inoue", "井上氏", None, None),
    ("Itō (Bicchū)", "備中伊東氏", None, None),
    ("Itō (Hyūga)", "日向伊東氏", "Obi domain", None),
    ("Katō", "加藤氏", "Multiple sengoku-origin houses; Katō Kiyomasa lineage extinct early Edo", None),
    ("Kuki", "九鬼氏", "Sanda / Ayabe domains; naval origin", None),
    ("Makino", "牧野氏", "Nagaoka domain (Echigo)", None),
    ("Matsudaira (Tsuyama)", "津山松平家", None, None),
    ("Mizoguchi", "溝口氏", "Shibata domain", None),
    ("Mizuno", "水野氏", "Yamagata / Fukuyama domains", None),
    ("Naitō", "内藤氏", "Multiple Edo daimyō houses", None),
    ("Nakagawa", "中川氏", "Oka domain (Bungo)", None),
    ("Niwa", "丹羽氏", "Nihonmatsu domain", None),
    ("Ogasawara", "小笠原氏", "Kokura / Akashi domains", None),
    ("Ōkubo", "大久保氏", "Odawara domain; also Meiji oligarch lineage", None),
    ("Ōoka", "大岡氏", None, None),
    ("Ōta", "太田氏", "Kakegawa domain", None),
    ("Ōtani", "大谷氏", "Sengoku Ōtani Yoshitsugu line", None),
    ("Rokkaku", "六角氏", "Sengoku Ōmi southern half; pre-Edo demise", None),
    ("Satake", "佐竹氏", "Akita domain; Genji descent", None),
    ("Sōma", "相馬氏", "Sōma domain (Mutsu)", None),
    ("Suwa", "諏訪氏", "Takashima (Suwa) domain; Suwa Taisha shrine line", None),
    ("Tachibana (Tachibana)", "立花氏 (柳河)", None, None),
    ("Tanuma", "田沼氏", "Sōrōkū Tanuma Okitsugu", None),
    ("Toda", "戸田氏", "Ōgaki / Matsumoto domains", None),
    ("Toki", "土岐氏", "Numata / Mino domains; Mino-Genji line", None),
    ("Tsugaru", "津軽氏", "Hirosaki domain (Mutsu)", None),
    ("Tsuchiya", "土屋氏", "Tsuchiura domain", None),
    ("Uesugi (Yonezawa)", "米沢上杉家", None, None),
    ("Wakisaka", "脇坂氏", "Tatsuno domain", None),
    ("Yagyū", "柳生氏", "Yagyū-shinkage swordsmanship; small daimyō", None),
    ("Yamanouchi (Tosa)", "土佐山内家", None, None),
    ("Hisamatsu-Matsudaira", "久松松平家", "Iyo-Matsuyama domain", None),
    ("Sakuma", "佐久間氏", None, None),
    ("Shibata", "柴田氏", "Sengoku Shibata Katsuie line", None),
    ("Sanada", "真田氏", "Matsushiro domain; Sanada Yukimura lineage", None),
    ("Kira", "吉良氏", "Edo kōke; Kira Yoshinaka of Akō affair", None),
    ("Imagawa", "今川氏", "Sengoku Suruga; Imagawa Yoshimoto", None),
    ("Hōjō (Late)", "後北条氏", "Sengoku Odawara; pre-Edo demise", None),
    ("Akamatsu", "赤松氏", "Harima sengoku; Edo small lord", None),
    ("Yamana", "山名氏", "Inaba sengoku", None),
    ("Ōuchi", "大内氏", "Suō sengoku trading clan; extinct sengoku", None),
    ("Ashikaga", "足利氏", "Muromachi shogunate; extinct as ruling clan 1573", "Q1370562"),
    ("Asakura", "朝倉氏", "Echizen sengoku; extinct 1573", None),
    ("Azai", "浅井氏", "Northern Ōmi sengoku; Oichi's house", None),
    ("Saitō", "斎藤氏", "Mino sengoku Saitō Dōsan line", None),
    ("Mori", "森氏", "Sengoku Mori Ranmaru; later Tsuyama", None),
    ("Niwa-Hashiba", "羽柴氏", "Toyotomi Hashiba house", None),
    ("Toyotomi", "豊臣氏", "Toyotomi Hideyoshi; extinct 1615 Osaka Castle", "Q1370561"),
    ("Oda", "織田氏", "Nobunaga clan; surviving small Edo branches", "Q1370563"),
    ("Sakakibara", "榊原氏", "Tokugawa-shitennō; Takada domain", None),
    ("Honda (Maeda branch)", "本多氏 (加賀)", None, None),
    ("Sakai (Shōnai)", "庄内酒井家", "Tsuruoka", None),
    ("Kii-Tokugawa side branches", "紀州徳川分家", None, None),
    ("Hayashi", "林氏", None, None),
    ("Fujiwara (north)", "藤原北家", "Heian regent house origin", None),
    ("Minamoto", "源氏", "Imperial-descended warrior house; many branches", None),
    ("Taira", "平氏", "Imperial-descended warrior house; Heike", None),
    ("Hōjō (Kamakura)", "鎌倉北条氏", "Kamakura regents 1199-1333", None),
    ("Nitta", "新田氏", "Genji descent; Tokugawa claimed descent", None),
    ("Wakatsuki", "若槻氏", None, None),
    ("Ōtomo", "大友氏", "Sengoku Bungo Christian daimyō", None),
    ("Ryūzōji", "龍造寺氏", "Sengoku Hizen", None),
    ("Sō-Kanezawa", "金沢宗氏", None, None),
    ("Hatakeyama", "畠山氏", "Muromachi kanrei", None),
    ("Hosokawa (Muromachi)", "細川氏 (室町)", "Muromachi kanrei", None),
    ("Shiba", "斯波氏", "Muromachi kanrei", None),
    ("Kitabatake", "北畠氏", "Ise Kuni-no-miyatsuko / sengoku", None),
    ("Toki (Sengoku)", "土岐氏 (戦国)", None, None),
    ("Akizuki", "秋月氏", "Takanabe domain", None),
    ("Hineno", "日根野氏", None, None),
    ("Tokugawa (Echizen-shogunate)", "越前徳川家", None, None),
]
for tup in DAIMYO:
    if len(tup) == 4:
        name, hanja, note, qid = tup
    else:
        name, hanja = tup[0], tup[1]
        note, qid = None, None
    add(rec(name_en=f"{name} clan", name_native=hanja, name_native_lang="ja",
            country=["JP"], category="noble", status="active" if "extinct" not in (note or "") else "extinct",
            notes=note or "", qid=qid,
            source="manual:wikipedia-ja-daimyo"))

# Zaibatsu / postwar business families
ZAIBATSU = [
    ("Mitsui family", "三井家", "Founded by Mitsui Takatoshi (1622-1694) Edo dry-goods → finance → Mitsui Group", "Q47494"),
    ("Mitsubishi (Iwasaki) family", "岩崎家", "Iwasaki Yatarō (1834-1885); Mitsubishi", "Q319408"),
    ("Sumitomo family", "住友家", "Sumitomo Masatomo (1585-1652); copper origin", "Q205012"),
    ("Yasuda family", "安田家", "Yasuda Zenjirō (1838-1921); banking; postwar Fuyo Group", None),
    ("Asano family", "浅野家 (財閥)", "Asano Sōichirō; cement/shipping", None),
    ("Furukawa family", "古河家", "Furukawa Ichibei; copper", None),
    ("Ōkura family", "大倉家", "Ōkura Kihachirō; trading", None),
    ("Kuhara/Nissan-Aikawa family", "鮎川家", "Aikawa Yoshisuke; Nissan zaibatsu founder", None),
    ("Nakajima family", "中島家", "Nakajima Chikuhei; aircraft", None),
    ("Mori family (Mori Building)", "森家", "Mori Taikichirō; real estate Roppongi", None),
    ("Toyoda family", "豊田家", "Toyoda Sakichi → Toyoda Kiichirō; Toyota Motor", "Q3157481"),
    ("Honda family", "本田家", "Honda Soichiro; no controlling stake today but founder family", None),
    ("Matsushita family", "松下家", "Matsushita Konosuke; Panasonic", None),
    ("Suzuki family (Suzuki Motor)", "鈴木家", "Suzuki Michio chairman family", None),
    ("Idemitsu family", "出光家", "Idemitsu Sazō; Idemitsu Kosan", None),
    ("Tsutsumi family (Seibu)", "堤家", "Tsutsumi Yasujirō → Yoshiaki; Seibu rail+department", None),
    ("Kashiwagi/Goto (Tokyu)", "五島家", "Goto Keita; Tokyu", None),
    ("Daiei Nakauchi family", "中内家", "Nakauchi Isao; Daiei retail", None),
    ("Aeon Okada family", "岡田家", "Okada Takuya / Motoya; Aeon retail", None),
    ("Fast Retailing Yanai family", "柳井家", "Yanai Tadashi; Uniqlo", None),
    ("Rakuten Mikitani family", "三木谷家", "Mikitani Hiroshi", None),
    ("SoftBank Son family", "孫家", "Son Masayoshi; SoftBank; Korean-Japanese", None),
    ("Nintendo Yamauchi family", "山内家", "Yamauchi Fusajirō (1889) → Hiroshi; Nintendo", None),
    ("Suntory Saji/Torii family", "鳥井・佐治家", "Torii Shinjirō → Saji Keizō; Suntory Holdings", None),
    ("Kao Hasegawa family", None, None, None),
    ("Kyocera Inamori family", "稲盛家", "Inamori Kazuo; Kyocera/KDDI", None),
    ("Bridgestone Ishibashi family", "石橋家", "Ishibashi Shōjirō; Bridgestone", None),
    ("Kikkoman Mogi family", "茂木家", "Mogi family of Noda; soy sauce since 1661", None),
    ("Yamaha (Kawakami/Yamaha) family", "山葉家・川上家", "Yamaha Torakusu founder; Kawakami succession", None),
    ("Asahi Soft Drinks Higuchi family", None, None, None),
    ("Itochu (Itō) family", "伊藤家 (伊藤忠)", "Itō Chūbei; Itochu trading", None),
    ("Marubeni founder family", None, None, None),
    ("JFE / Kawasaki family", None, "Kawasaki Shōzō; Kawasaki zaibatsu / Kawasaki Heavy", None),
    ("Hattori family (Seiko)", "服部家", "Hattori Kintarō; Seiko/Seibu Hattori", None),
    ("Mitsukoshi", "三越", "Mitsukoshi dept store; Mitsui-branch", None),
    ("Takashimaya Iida family", "飯田家", "Takashimaya dept store", None),
    ("Daiwa Securities Doi family", None, None, None),
    ("Nomura family (Nomura Securities)", "野村家", "Nomura Tokushichi II", None),
]
for tup in ZAIBATSU:
    name, hanja, note, qid = (tup + (None,)*4)[:4]
    add(rec(name_en=name, name_native=hanja, name_native_lang="ja",
            country=["JP"], category="business", status="active",
            notes=note or "", qid=qid, source="manual:zaibatsu"))


# =====================================================================
# CHINA (CN / TW / HK)
# =====================================================================
# Imperial dynasties (24 + key regional)
CN_DYNASTIES = [
    ("House of Ji (Zhou)", "姬姓周朝", -1046, -256, "extinct", "Zhou royal house"),
    ("House of Ying (Qin)", "嬴姓秦朝", -221, -207, "extinct", "Qin imperial house"),
    ("House of Liu (Western/Eastern Han)", "劉氏漢朝", -202, 220, "extinct", "Han dynasty; ~60M descendants today"),
    ("House of Cao (Wei)", "曹氏曹魏", 220, 266, "extinct", "Three Kingdoms Cao Wei"),
    ("House of Liu (Shu Han)", "劉氏蜀漢", 221, 263, "extinct", "Liu Bei Shu Han"),
    ("House of Sun (Eastern Wu)", "孫氏東吳", 222, 280, "extinct", "Sun Quan Eastern Wu"),
    ("House of Sima (Jin)", "司馬氏晉朝", 266, 420, "extinct", "Jin dynasty"),
    ("House of Liu (Liu Song)", "劉氏宋朝", 420, 479, "extinct", "Southern Dynasties Song"),
    ("House of Xiao (Southern Qi)", "蕭氏南齊", 479, 502, "extinct", None),
    ("House of Xiao (Liang)", "蕭氏梁朝", 502, 557, "extinct", None),
    ("House of Chen (Chen dynasty)", "陳氏陳朝", 557, 589, "extinct", None),
    ("House of Tuoba/Yuan (Northern Wei)", "拓拔氏元氏北魏", 386, 534, "extinct", None),
    ("House of Yuwen (Northern Zhou)", "宇文氏北周", 557, 581, "extinct", None),
    ("House of Yang (Sui)", "楊氏隋朝", 581, 618, "extinct", None),
    ("House of Li (Tang)", "李氏唐朝", 618, 907, "extinct", "Tang imperial house; Longxi Li", "Q9683"),
    ("House of Zhu (Later Liang)", "朱氏後梁", 907, 923, "extinct", None),
    ("House of Li (Later Tang)", "李氏後唐", 923, 937, "extinct", None),
    ("House of Shi (Later Jin)", "石氏後晉", 936, 947, "extinct", None),
    ("House of Liu (Later Han)", "劉氏後漢", 947, 951, "extinct", None),
    ("House of Guo/Chai (Later Zhou)", "郭氏柴氏後周", 951, 960, "extinct", None),
    ("House of Zhao (Song)", "趙氏宋朝", 960, 1279, "extinct", "Song imperial house"),
    ("House of Yelü (Liao)", "耶律氏遼朝", 916, 1125, "extinct", "Khitan Liao"),
    ("House of Wanyan (Jin)", "完顏氏金朝", 1115, 1234, "extinct", "Jurchen Jin"),
    ("House of Borjigin (Yuan)", "孛兒只斤氏元朝", 1271, 1368, "deposed", "Mongol Yuan; same house as Mongol Empire"),
    ("House of Zhu (Ming)", "朱氏明朝", 1368, 1644, "extinct", "Ming imperial house; many extant claimed descendants"),
    ("House of Aisin Gioro (Qing)", "愛新覺羅氏清朝", 1644, 1912, "deposed", "Manchu Qing imperial house; head: Jin Yuzhang"),
    ("House of Li (Western Xia)", "李氏西夏", 1038, 1227, "extinct", "Tangut Xia"),
    ("House of Trinh (Annam tributary)", None, None, None, None, None),
    ("Taiping Heavenly Kingdom Hong family", "洪氏太平天國", 1851, 1864, "extinct", "Hong Xiuquan rebel kingdom"),
]
for tup in CN_DYNASTIES:
    name = tup[0]; hanja = tup[1]; founded = tup[2]; extinct = tup[3]; status = tup[4]; note = tup[5] if len(tup)>5 else None
    qid = tup[6] if len(tup) > 6 else None
    add(rec(name_en=name, name_native=hanja, name_native_lang="zh",
            country=["CN"], category="royal", founded=founded, extinct=extinct,
            status=status or "extinct", notes=note or "", qid=qid))

# Tang elite clans — 五姓七族 / great clans
TANG_ELITE = [
    ("Cui of Boling", "博陵崔氏"),
    ("Cui of Qinghe", "清河崔氏"),
    ("Lu of Fanyang", "范陽盧氏"),
    ("Li of Zhaojun", "趙郡李氏"),
    ("Li of Longxi", "隴西李氏"),
    ("Zheng of Xingyang", "滎陽鄭氏"),
    ("Wang of Taiyuan", "太原王氏"),
    ("Wang of Langya", "瑯邪王氏"),
    ("Pei of Hedong", "河東裴氏"),
    ("Xie of Chen Commandery", "陳郡謝氏"),
    ("Wang of Linchuan", "臨川王氏"),
    ("Xiahou of Qiao", "譙縣夏侯氏"),
    ("Yang of Hongnong", "弘農楊氏"),
    ("Yuan of Henan", "河南元氏"),
]
for name, hanja in TANG_ELITE:
    add(rec(name_en=name, name_native=hanja, name_native_lang="zh",
            country=["CN"], category="noble", founded=300, status="active",
            notes="Six Dynasties / Tang aristocracy; gentry clan still claimed by descendants",
            source="manual:tang-elite"))

# Confucius Kong lineage
add(rec(name_en="Kong family of Qufu", name_native="曲阜孔氏", name_native_lang="zh",
        country=["CN", "TW", "KR"], category="religious", founded=-551, status="active",
        notes="Direct descendants of Confucius; ~3M; current Duke Yansheng Kung Tsui-chang (TW); world's oldest unbroken lineage",
        qid="Q864849"))
add(rec(name_en="Meng family (Mencius)", name_native="孟氏", name_native_lang="zh",
        country=["CN"], category="religious", founded=-372, status="active",
        notes="Mencius descendants; Zou (鄒); recognized as second sage clan"))
add(rec(name_en="Yan family (Yan Hui)", name_native="顏氏", name_native_lang="zh",
        country=["CN"], category="religious", founded=-521, status="active",
        notes="Confucius's top disciple Yan Hui descendants"))
add(rec(name_en="Zeng family (Zengzi)", name_native="曾氏", name_native_lang="zh",
        country=["CN"], category="religious", founded=-505, status="active",
        notes="Zengzi (Zeng Shen) descendants"))
add(rec(name_en="Zhuge family", name_native="諸葛氏", name_native_lang="zh",
        country=["CN"], category="noble", founded=200, status="active",
        notes="Zhuge Liang Shu-Han chancellor; Zhejiang Bafu villages today"))

# Republican-era Four Big Families
add(rec(name_en="Chiang family", name_native="蔣家", name_native_lang="zh",
        country=["TW", "CN"], category="business", founded=1887, status="active",
        notes="Chiang Kai-shek → Chiang Ching-kuo → Chiang Hsiao-yung → Chiang Yo-po. ROC ruling family"))
add(rec(name_en="Soong family", name_native="宋家", name_native_lang="zh",
        country=["TW", "CN", "US"], category="business", founded=1880, status="active",
        notes="Soong Charlie → Soong sisters (Ai-ling, Ching-ling, Mei-ling) + T.V. Soong"))
add(rec(name_en="Kung family", name_native="孔家", name_native_lang="zh",
        country=["TW", "CN", "US"], category="business", founded=1881, status="active",
        notes="H.H. Kung; Kong family Shanxi branch separate from Qufu line"))
add(rec(name_en="Chen family (CC Clique)", name_native="陳家 (CC系)", name_native_lang="zh",
        country=["TW", "CN"], category="business", founded=1890, status="active",
        notes="Chen Guofu & Chen Lifu; KMT power brokers"))

# PRC princelings (公开记录中)
add(rec(name_en="Xi family", name_native="習家", name_native_lang="zh",
        country=["CN"], category="business", status="active",
        notes="Xi Zhongxun → Xi Jinping → Xi Mingze; PRC ruling lineage"))
add(rec(name_en="Bo family", name_native="薄家", name_native_lang="zh",
        country=["CN"], category="business", status="active",
        notes="Bo Yibo → Bo Xilai (purged) → Bo Guagua"))
add(rec(name_en="Deng family", name_native="鄧家", name_native_lang="zh",
        country=["CN"], category="business", status="active",
        notes="Deng Xiaoping → Deng Pufang / Deng Nan / Deng Rong"))
add(rec(name_en="Jiang family", name_native="江家", name_native_lang="zh",
        country=["CN"], category="business", status="active",
        notes="Jiang Zemin → Jiang Mianheng → Jiang Zhicheng (Alvin Jiang)"))
add(rec(name_en="Li family (Li Peng)", name_native="李家 (李鵬)", name_native_lang="zh",
        country=["CN"], category="business", status="active",
        notes="Li Peng → Li Xiaopeng (Huaneng) / Li Xiaolin"))
add(rec(name_en="Wen family", name_native="溫家", name_native_lang="zh",
        country=["CN"], category="business", status="active",
        notes="Wen Jiabao → Wen Yunsong (Winston Wen)"))
add(rec(name_en="Zhu family (Zhu De)", name_native="朱家 (朱德)", name_native_lang="zh",
        country=["CN"], category="business", status="active",
        notes="Zhu De PLA marshal lineage"))
add(rec(name_en="Ye family", name_native="葉家", name_native_lang="zh",
        country=["CN"], category="business", status="active",
        notes="Ye Jianying PLA marshal → Ye Xuanping, Ye Xuanning"))

# HK tycoons
HK_TYCOONS = [
    ("Li family (Cheung Kong)", "李家 (長江)", "Li Ka-shing → Victor Li / Richard Li; CK Hutchison, Husky Energy", "Q57085"),
    ("Kwok family (SHK)", "郭家 (新鴻基)", "Kwok Tak-seng founder → Kwok Ping-luen, Ping-kwong, Ping-shing", None),
    ("Lee family (Henderson)", "李家 (恒基)", "Lee Shau-kee → Peter Lee / Martin Lee; Henderson Land", None),
    ("Cheng family (NWD)", "鄭家 (新世界)", "Cheng Yu-tung → Henry Cheng → Adrian Cheng; New World Development, Chow Tai Fook", None),
    ("Pao family", "包家 (環球)", "Pao Yue-kong → Helmut Sohmen; World-Wide Shipping; Wheelock heritage", None),
    ("Woo family", "吳家 (會德豐)", "Peter Woo (Pao son-in-law) → Douglas Woo; Wheelock/Wharf", None),
    ("Lui family (Great Eagle)", "呂家 (鷹君)", "Lo Ying-shek; later split with Lui-named branch", None),
    ("Ng family (Sino Land)", "黃家 (信和)", "Robert Ng + Philip Ng; from Far East Org Singapore Ng-family", None),
    ("Lo family (Great Eagle)", "羅家 (鷹君)", "Lo Ka-shui; Great Eagle Holdings", None),
    ("Fok family", "霍家", "Henry Fok → Ian Fok / Timothy Fok", None),
    ("Pao-Wheelock-Y.K. Pao", None, None, None),
    ("Chow Tai Fook (combined)", "周大福", "Cheng family controls", None),
    ("Hui family (Evergrande)", "許家 (恆大)", "Hui Ka-yan; founder of Evergrande (now distressed)", None),
    ("Tsai family (Stanley Ho's heirs)", None, None, None),
    ("Ho family (SJM / Macau)", "何家", "Stanley Ho → Pansy Ho, Lawrence Ho, Daisy Ho; SJM/MGM China/Melco", None),
    ("Lam family (Macau)", "林家 (澳門)", "Lam Kong; SJM legacy", None),
    ("Shaw family", "邵家", "Run Run Shaw → Shaw Brothers/TVB heritage", None),
    ("Tang family (Esprit)", None, "Michael Ying former; Esprit/Bossini", None),
    ("Cha family (Newscom / Mingpao)", "查家", "Louis Cha / Jin Yong + Cha Chi-min Mingpao; textiles too", None),
    ("Yeoh family (Hong Kong)", None, None, None),
    ("Lau family (Chinese Estates)", "劉家 (華人置業)", "Joseph Lau → Lau Ming-wai", None),
]
for tup in HK_TYCOONS:
    name, hanja, note, qid = (tup + (None,)*4)[:4]
    if not name: continue
    add(rec(name_en=name, name_native=hanja, name_native_lang="zh",
            country=["HK"], category="business", status="active",
            notes=note or "", qid=qid, source="manual:hk-tycoons"))

# Taiwan business families
TW_FAMILIES = [
    ("Koo family (Taiwan)", "辜家", "Koo Hsien-jung → Koo Chen-fu → Jeffrey Koo Jr; Chinatrust/CTBC, Taiwan Cement"),
    ("Tsai family (Cathay)", "蔡家 (國泰)", "Tsai Wan-lin → Tsai Hong-tu, Tsai Ming-hsing; Cathay Holdings / Cathay Life"),
    ("Tsai family (Fubon)", "蔡家 (富邦)", "Tsai Wan-tsai → Tsai Ming-chung, Tsai Ming-hsing; Fubon Financial"),
    ("Wang family (Formosa Plastics)", "王家 (台塑)", "Wang Yung-ching + Wang Yung-tsai → Wang Wen-yuan, Cher Wang; FPG, HTC, VIA"),
    ("Hsu family (Far Eastern)", "徐家 (遠東)", "Yu-Tung Hsu → Douglas Hsu; Far Eastern Group"),
    ("Shih family (Acer)", "施家 (宏碁)", "Stan Shih; Acer; semi-family business"),
    ("Lin family (Banciao)", "板橋林家", "Lin Pen-yuan; Qing-era five great families"),
    ("Yan family (Keelung)", "基隆顏家", "Yan Yun-nien; coal mining Qing era; one of five great families"),
    ("Wufeng Lin family", "霧峰林家", "Lin Wen-cha; central Taiwan Qing-era great family"),
    ("Lukang Koo family", "鹿港辜家", "Same lineage as Chinatrust Koo"),
    ("Kaohsiung Chen family", "高雄陳家", "Chen Chung-ho lineage; sugar Qing-era"),
    ("Quanta Lin family", "林家 (廣達)", "Barry Lam; Quanta Computer"),
    ("Foxconn Gou family", "郭家 (鴻海)", "Terry Gou; Foxconn/Hon Hai"),
    ("Evergreen Chang family", "張家 (長榮)", "Chang Yung-fa → Chang Kuo-wei, Chang Kuo-hua; Evergreen Marine, EVA Air"),
    ("MediaTek Tsai family", "蔡家 (聯發科)", "Tsai Ming-kai; MediaTek"),
    ("Uni-President Kao family", "高家 (統一)", "Kao Ching-yen; Uni-President"),
    ("Cher Wang", "王家 (HTC)", "Cher Wang Wen-yuan's daughter; HTC; husband Wenchi Chen / VIA"),
    ("Hon Hai Kuo", None, "Same as Foxconn"),
]
for tup in TW_FAMILIES:
    name, hanja, note = (tup + (None, None))[:3]
    if not name or "Same as" in (note or ""):
        if name and "Same as" in (note or ""):
            continue
    add(rec(name_en=name, name_native=hanja, name_native_lang="zh",
            country=["TW"], category="business", status="active",
            notes=note or "", source="manual:tw-business"))


# =====================================================================
# INDIA  —  princely states (562) + business houses + Rajput clans
# =====================================================================
# 21-gun salute states (highest tier of British Raj)
SALUTE_21 = [
    ("Hyderabad State", "Asaf Jahi dynasty / Nizam of Hyderabad", "Q462718"),
    ("Jammu and Kashmir", "Dogra dynasty", None),
    ("Mysore", "Wadiyar dynasty", "Q272412"),
    ("Baroda", "Gaekwad dynasty", None),
    ("Gwalior", "Scindia dynasty", "Q1349037"),
    ("Indore", "Holkar dynasty", None),
    ("Travancore", "Travancore Royal Family", None),
    ("Udaipur (Mewar)", "Sisodia Rajput / Mewar House", "Q3133430"),
]
for name, dynasty, qid in SALUTE_21:
    add(rec(name_en=f"{dynasty} (rulers of {name})", country=["IN"], category="royal",
            status="deposed", notes=f"21-gun salute princely state; merged into India 1947-1950", qid=qid,
            source="manual:in-princely-states"))

# 19-gun salute states
SALUTE_19 = [
    ("Bhopal", "Bhopal Nawab dynasty"),
    ("Kolhapur", "Bhonsle Maratha"),
    ("Kalat", "Khanate of Kalat (Ahmadzai)"),
    ("Bahawalpur", "Abbasi family"),
    ("Bharatpur", "Sinsinwar Jat"),
    ("Cochin", "Cochin royal family (Kerala Varma)"),
    ("Jaipur", "Kachwaha Rajput"),
    ("Jodhpur", "Rathore of Marwar"),
    ("Patiala", "Sidhu Jat (Phulkian)"),
    ("Rewa", "Baghel Rajput"),
    ("Tonk", "Pindari-origin Nawabs of Tonk"),
]
for name, dynasty in SALUTE_19:
    add(rec(name_en=f"{dynasty} of {name}", country=["IN"], category="royal",
            status="deposed", notes="19-gun salute princely state",
            source="manual:in-princely-states"))

# 17-gun + 15-gun (selected major)
SALUTE_17_15 = [
    ("Bikaner", "Rathore Rajput of Bikaner"),
    ("Cutch", "Jadeja Rajput of Cutch"),
    ("Kishangarh", "Rathore Rajput of Kishangarh"),
    ("Karauli", "Yaduvanshi Rajput"),
    ("Datia", "Bundela Rajput of Datia"),
    ("Dewas Senior", "Pawar Maratha"),
    ("Dewas Junior", "Pawar Maratha"),
    ("Dhar", "Pawar Maratha of Dhar"),
    ("Dholpur", "Jat house of Dholpur"),
    ("Idar", "Rathore of Idar"),
    ("Jaisalmer", "Bhati Rajput"),
    ("Jhalawar", "Jhala Rajput"),
    ("Junagadh", "Babi Pathan"),
    ("Kapurthala", "Ahluwalia Sikh"),
    ("Khairpur", "Talpur Mirs of Khairpur"),
    ("Pratapgarh", "Sisodia of Pratapgarh"),
    ("Pudukkottai", "Tondaiman dynasty"),
    ("Rampur", "Rohilla Nawab"),
    ("Sirohi", "Devda Chauhan Rajput"),
    ("Tehri-Garhwal", "Pal/Panwar of Garhwal"),
    ("Bundi", "Hada Chauhan Rajput"),
    ("Kota", "Hada Chauhan of Kota"),
    ("Alwar", "Naruka Rajput"),
    ("Banswara", "Sisodia of Banswara"),
    ("Dungarpur", "Sisodia of Dungarpur"),
    ("Jind", "Phulkian Sikh"),
    ("Nabha", "Phulkian Sikh"),
    ("Faridkot", "Brar Jat"),
    ("Junagadh State - alt", "Babi"),
    ("Cooch Behar", "Koch dynasty"),
    ("Tripura", "Manikya dynasty"),
    ("Manipur", "Ningthouja dynasty"),
    ("Sikkim", "Namgyal dynasty"),
    ("Sandur", "Ghorpade Maratha"),
    ("Banganapalle", "Banganapalle Nawab"),
    ("Sachin", "Sidi Nawab of Sachin"),
    ("Janjira", "Sidi of Janjira"),
    ("Rajpipla", "Gohil Rajput"),
    ("Palanpur", "Lohani Pathan"),
    ("Radhanpur", "Babi Pathan"),
    ("Wankaner", "Jhala Rajput"),
    ("Morvi", "Jadeja Rajput"),
    ("Nawanagar", "Jadeja Rajput (Ranjitsinhji cricket)"),
    ("Porbandar", "Jethwa Rajput"),
    ("Dhrangadhra", "Jhala Rajput"),
    ("Limbdi", "Jhala Rajput"),
    ("Bhavnagar", "Gohil Rajput"),
    ("Junagadh Nawab", "Babi"),
    ("Sangli", "Patwardhan Maratha"),
    ("Miraj Senior", "Patwardhan Maratha"),
    ("Miraj Junior", "Patwardhan Maratha"),
    ("Kurundwad Senior", "Patwardhan Maratha"),
    ("Mudhol", "Ghorpade Maratha"),
    ("Akkalkot", "Bhonsle Maratha"),
    ("Aundh", "Pant Pratinidhi"),
    ("Phaltan", "Naik-Nimbalkar Maratha"),
    ("Jath", "Daphle Maratha"),
    ("Jamkhandi", "Patwardhan Maratha"),
    ("Bhor", "Pant Sachiv"),
    ("Sawantwadi", "Bhonsle of Sawantwadi"),
    ("Ramnad", "Sethupathi"),
    ("Sivaganga", "Marudhu Pandiyan Nadar / Maravar"),
    ("Pudukkottai - alt", None),
    ("Banaras", "Banaras royal family"),
    ("Ayodhya", "Bhanjadeo"),
    ("Mayurbhanj", "Bhanj"),
    ("Keonjhar", "Bhanj"),
    ("Bastar", "Kakatiya of Bastar"),
    ("Surguja", "Chero/Surguja royal"),
    ("Patna State", "Mahanaboj / Bhanj"),
    ("Sarangarh", "Raj Gond"),
    ("Bonai", "Khinda dynasty"),
    ("Dhenkanal", "Bhanj"),
    ("Talcher", "Bhanj"),
    ("Sonepur", "Chauhan of Sonepur"),
    ("Kalahandi", "Naga dynasty"),
    ("Athgarh", "Bhanj"),
    ("Athmallik", "Patnaik"),
    ("Tigiria", "Kuanr"),
    ("Daspalla", "Bhanj"),
    ("Banki", "Bhanj"),
    ("Khandpara", "Bhanj"),
    ("Hindol", "Bhanj"),
    ("Nilgiri", "Mangaraj"),
    ("Mayurbhanj alt", None),
    ("Bamra", "Pal-Mahanta"),
    ("Rairakhol", "Bhanj"),
    ("Pal Lahara", "Bhanj"),
]
for tup in SALUTE_17_15:
    name = tup[0]; dynasty = tup[1] if len(tup)>1 else None
    if not dynasty: continue
    add(rec(name_en=f"{dynasty} of {name}", country=["IN"], category="royal",
            status="deposed", notes="Major princely state — 9 to 15-gun salute or notable non-salute",
            source="manual:in-princely-states"))

# Non-salute / smaller but notable princely states (selected)
NON_SALUTE = [
    "Akalkot", "Aundh", "Banganapalle", "Banswara", "Baramati", "Barwani",
    "Benares (Banaras)", "Bhadrawah", "Bhajji", "Bhor", "Bilaspur",
    "Bilbari", "Chamba", "Charkhari", "Chhatarpur", "Chhota Udaipur",
    "Dhrangadhra", "Faridkot", "Gondal", "Hindol", "Idar",
    "Jaora", "Jashpur", "Jind", "Jowhar", "Junagadh",
    "Kashmir", "Kawardha", "Khairagarh", "Khilchipur", "Kotah",
    "Kurundwad Junior", "Limbdi", "Loharu", "Lunavada", "Maihar",
    "Makrai", "Mandi", "Manipur", "Mohrah Sharif", "Morvi",
    "Mudhol", "Nabha", "Nahan (Sirmur)", "Narsinghgarh", "Nawanagar",
    "Orchha", "Panna", "Pataudi", "Phaltan", "Pratapgarh",
    "Radhanpur", "Rajgarh", "Rajkot", "Rajpipla", "Rampur",
    "Ratlam", "Rewa", "Sailana", "Samthar", "Sangli",
    "Sant", "Sawantwadi", "Sirmur", "Sirohi", "Sitamau",
    "Sonepur", "Sukket", "Suket", "Tonk", "Vijayanagaram",
    "Wankaner", "Banera", "Charkhari", "Mahmudabad", "Bharatpur",
    "Dhar", "Bharauli", "Bahawalpur", "Mansa", "Janjira",
    "Kapurthala", "Hindur (Nalagarh)", "Sirmur (Nahan)", "Kashmir-Jammu",
    "Chitral", "Hunza", "Nagar", "Swat", "Dir", "Amb",
    "Phulra", "Mahipur", "Naushahro Firoz", "Las Bela",
    "Khairpur", "Makran", "Kharan", "Saudi Las Bela",
    "Manavadar", "Mangrol", "Sachin", "Tripura", "Cooch Behar",
    "Sikkim", "Mayurbhanj", "Kalahandi", "Patna State",
    "Sonepur", "Bonai", "Kanker", "Bastar", "Khairagarh",
    "Korea (Korea State)", "Surguja", "Udaipur State",
    "Sarangarh", "Raigarh", "Jashpur", "Sakti",
    "Chandkhuri", "Nandgaon", "Kawardha",
    "Idar", "Lunavada", "Sant", "Devgadh Baria", "Rajpipla",
    "Bansda", "Dharampur", "Sachin", "Wadhwan", "Limbdi",
    "Halvad", "Bhavnagar", "Palitana", "Vala", "Lathi",
    "Vadia", "Saurashtra small states",
    "Tehri-Garhwal", "Pataudi", "Jaisalmer",
    "Cochin", "Travancore-Cochin",
    "Vizianagaram", "Pithapuram", "Venkatagiri",
    "Bobbili", "Mangalagiri", "Sandur", "Banganapalle",
    "Anandapur", "Ramdurg",
    "Kurnool", "Cuddapah",
    "Aundh", "Akkalkot", "Bhor", "Phaltan", "Daphlapur",
    "Kolhapur", "Aundh", "Janjira",
]
for ps in sorted(set(NON_SALUTE)):
    add(rec(name_en=f"Princely State of {ps}", country=["IN"], category="royal",
            status="deposed", notes="Princely state; merged with India/Pakistan 1947-1956",
            source="manual:in-princely-states-bulk"))

# 36 Rajput royal clans (traditional list)
RAJPUT_CLANS = [
    ("Sisodia", "Suryavanshi; Mewar"), ("Rathore", "Suryavanshi; Marwar/Bikaner"),
    ("Kachwaha", "Suryavanshi; Jaipur/Amber"), ("Chauhan", "Agnivanshi; Bundi/Kota"),
    ("Parmar (Pawar)", "Agnivanshi; Malwa/Dhar"), ("Solanki (Chalukya)", "Agnivanshi; Gujarat"),
    ("Pratihar (Pratihara)", "Agnivanshi; Kannauj heritage"),
    ("Jadeja", "Chandravanshi; Cutch/Saurashtra"),
    ("Bhati", "Chandravanshi; Jaisalmer"),
    ("Jhala", "Chandravanshi (claimed); Jhalawar/Saurashtra"),
    ("Tomar (Tanwar)", "Chandravanshi; Delhi heritage"),
    ("Gehlot", "Suryavanshi; ancestor of Sisodia"),
    ("Chandel", "Chandravanshi; Bundelkhand"),
    ("Bundela", "Chandel offshoot; Orchha/Datia"),
    ("Khichi", "Chauhan offshoot"),
    ("Hada", "Chauhan offshoot; Bundi/Kota"),
    ("Naruka", "Kachwaha offshoot; Alwar"),
    ("Shekhawat", "Kachwaha offshoot; Shekhawati"),
    ("Bhadauria", "Chauhan offshoot; Bhadawar"),
    ("Yaduvanshi", "Lunar dynasty Yadu line; Karauli"),
    ("Surajvanshi/Suryavanshi", "Solar dynasty meta-class"),
    ("Gohil", "Bhavnagar/Rajpipla"),
    ("Sengar", "Etawah/UP Rajput"),
    ("Dixit", "Bisen/Brahmin-Rajput"),
    ("Baghel", "Solanki offshoot; Rewa"),
    ("Chudasama", "Junagadh/Saurashtra"),
    ("Dahima", "Khanderao"),
    ("Devda", "Sirohi"),
    ("Dod", "Punjab/Sindh"),
    ("Gaur", "Gaur Rajput Bengal/Sheopur"),
    ("Hool", None),
    ("Nimiwal", None),
    ("Pundir", "Punjab/Garhwal"),
    ("Rana", "Chauhan/Suryavanshi mix; Nepal too"),
    ("Sirohia/Devda", None),
    ("Surwar", None),
    ("Tank", "Punjab"),
    ("Vaghela", "Solanki offshoot; Gujarat"),
    ("Kushwaha", "Suryavanshi farmer-Rajput"),
    ("Maurya", "Maurya empire descendants claim"),
    ("Nikumbh", "Kannauj/UP"),
    ("Pachhada", None),
    ("Punwar", "Parmar variant"),
    ("Rao", "South Indian Maratha-Rajput"),
    ("Sengar", None),
    ("Singhel", None),
    ("Sirdhar", None),
    ("Sodha", "Sindh/Cutch Parmar offshoot"),
    ("Songara", None),
    ("Tomara", "Variant of Tomar"),
    ("Ujjainiya", "Parmar offshoot; Bihar"),
    ("Vais", "UP Rajput"),
]
for name, note in RAJPUT_CLANS:
    add(rec(name_en=f"{name} Rajput clan", country=["IN"], category="clan",
            status="active", notes=note or "Rajput clan from traditional 36 Royal Clans",
            source="manual:rajput-36"))

# Indian business families
IN_BUSINESS = [
    ("Tata family", "TATA", "Jamsetji Tata (1839) → Ratan Tata; Parsi; Tata Sons via trusts (no controlling individual)"),
    ("Birla family", "बिड़ला", "G.D. Birla → Aditya Birla → Kumar Mangalam Birla; AV Birla Group; also Yashovardhan Birla, Basant Kumar branch"),
    ("Ambani family (Reliance)", "अंबानी", "Dhirubhai Ambani → Mukesh / Anil; Reliance Industries split 2005"),
    ("Adani family", "अडानी", "Gautam Adani; Adani Group; coal/ports/green energy"),
    ("Mahindra family", "महिंद्रा", "K.C. Mahindra + J.C. Mahindra → Anand Mahindra"),
    ("Bajaj family", "बजाज", "Jamnalal Bajaj → Rahul Bajaj → Rajiv / Sanjiv Bajaj; Bajaj Auto/Finserv"),
    ("Godrej family", "गोदरेज", "Ardeshir Godrej (Parsi) → Adi Godrej + Jamshyd Godrej + Nadir Godrej; 2024 split"),
    ("Wadia family", "वाडिया", "Nusli Wadia → Ness/Jeh; Britannia, Bombay Dyeing; Parsi"),
    ("Hinduja family", "हिंदुजा", "Parmanand Hinduja → SP, GP, PP, AP Hinduja brothers; Hinduja Group; UK-based"),
    ("Premji family", "प्रेमजी", "M.H. Premji → Azim Premji → Rishad Premji; Wipro; Bohra Muslim"),
    ("Jindal family", "जिंदल", "O.P. Jindal → Prithviraj/Sajjan/Ratan/Naveen Jindal; OP Jindal Group split four ways"),
    ("Mittal family", "मित्तल", "Lakshmi Mittal (ArcelorMittal) + Sunil Mittal (Bharti Airtel) — different families same surname"),
    ("Munjal family (Hero)", "मुंजाल", "Brijmohan Lall Munjal → Pawan Munjal; Hero MotoCorp"),
    ("Burman family (Dabur)", "बर्मन", "Dr. S.K. Burman → Mohit/Anand/Saket Burman; Dabur"),
    ("Piramal family", "पीरामल", "Ajay Piramal; Piramal Group"),
    ("Lohia family (Indorama)", "लोहिया", "S.P. Lohia, Mohan Lal Lohia; Indorama"),
    ("Singhania family (Raymond)", "सिंघानिया", "Vijaypat Singhania → Gautam Singhania; Raymond"),
    ("Singhania family (JK Group)", "JK सिंघानिया", "Hari Shankar Singhania; JK Tyre etc."),
    ("Kotak family", "कोटक", "Uday Kotak; Kotak Mahindra Bank"),
    ("Modi family (Modi Enterprises)", "मोदी", "K.K. Modi → Lalit Modi etc."),
    ("Murugappa family", "முருகப்பா", "A.M.M. Murugappa Chettiar; Tamil Chettiar; Carborundum/Tube Investments"),
    ("Chettiar (Nattukottai)", "நாட்டுக்கோட்டை செட்டியார்", "Tamil banking caste; financed colonial SE Asia"),
    ("Reddy family (GMR)", "GMR रेड्डी", "G.M. Rao; GMR Group"),
    ("Reddy family (Dr. Reddy's)", "डॉ रेड्डी", "K. Anji Reddy → Satish Reddy / GV Prasad; Dr. Reddy's Lab"),
    ("Naidu family (Heritage)", "नायडू", "Chandrababu Naidu / N.T. Rama Rao TDP/Heritage"),
    ("Raheja family", "रहेजा", "Chandru Raheja and Gopal Raheja; K Raheja Corp"),
    ("Hiranandani family", "हीरानंदानी", "Niranjan Hiranandani"),
    ("Lodha family", "लोढ़ा", "Mangal Prabhat Lodha → Abhishek Lodha; Macrotech Developers"),
    ("Bangur family", "बांगुर", "Shree Cement / various Bangur Marwari branches"),
    ("Goenka family (RPG)", "गोयनका RPG", "R.P. Goenka → Harsh Goenka, Sanjiv Goenka; RPG Enterprises"),
    ("Goenka family (Emami)", "गोयनका Emami", "R.S. Agarwal + R.S. Goenka; Emami"),
    ("Agarwal family (Vedanta)", "अग्रवाल", "Anil Agarwal; Vedanta Resources"),
    ("Bhartia family (Jubilant)", "भरतिया", "S.S. Bhartia → Hari Bhartia, Shyam Bhartia"),
    ("Oberoi family (EIH)", "ओबरॉय", "Mohan Singh Oberoi → P.R.S. Oberoi → Vikram Oberoi; The Oberoi Group"),
    ("Mariwala family (Marico)", "मारीवाला", "Harsh Mariwala; Marico"),
    ("Damani family (DMart)", "दमानी", "Radhakishan Damani; Avenue Supermarts"),
    ("Adi Godrej family (Industries)", None, "Already in Godrej"),
    ("Ruia family (Essar)", "रुइया", "S.N. Ruia + R.N. Ruia; Essar Group"),
    ("Shroff family (Excel)", "श्रॉफ", "S.G. Shroff; Excel Industries"),
    ("Lalbhai family (Arvind)", "लालभाई", "Kasturbhai Lalbhai → Sanjay Lalbhai; Arvind"),
    ("Nilekani family (semi-business)", "निलेकानी", "Nandan Nilekani; Infosys co-founder; UID/Aadhaar"),
    ("Narayana Murthy family (Infosys)", "मूर्ति", "N.R. Narayana Murthy + Sudha Murty → Rohan Murty; daughter Akshata Murty married UK PM Rishi Sunak"),
    ("Cyril Shroff family", "श्रॉफ Cyril", "Cyril Amarchand Mangaldas law firm; Shardul Amarchand split"),
    ("Reddy Vijaya/Nimmagadda", None, None),
    ("Britannia / Wadia overlap", None, None),
    ("Wipro - Azim Premji", None, "Same as Premji"),
    ("DLF Singh family", "DLF सिंह", "Kushal Pal Singh → Rajiv Singh; DLF"),
    ("Bharti Mittal", None, "Same as Mittal-Bharti"),
    ("Sun Pharma Shanghvi", "शांघवी", "Dilip Shanghvi; Sun Pharmaceutical"),
    ("Cipla Hamied", "हमीद", "Yusuf Hamied → MK Hamied; Cipla"),
    ("Apollo Hospitals Reddy", "अपोलो रेड्डी", "Prathap Reddy → Preetha, Suneeta, Sangita, Shobana; Apollo Hospitals"),
    ("Biocon Mazumdar-Shaw", "मजूमदार-शॉ", "Kiran Mazumdar-Shaw; Biocon"),
    ("Cognizant Kumar (semi)", None, None),
    ("HCL Shiv Nadar", "नाडर", "Shiv Nadar → Roshni Nadar Malhotra; HCL Technologies"),
    ("Larsen & Toubro Naik", None, "L&T no controlling family; Naik chairman, broad-base"),
    ("Bansal family (Flipkart)", "बंसल", "Sachin Bansal + Binny Bansal (unrelated); Flipkart"),
    ("Khaitan family", "खैतान", "Khaitan & Co law firm; Williamson Magor tea"),
    ("Lulu Yusuff Ali", "Lulu यूसुफ अली", "Yusuff Ali M.A.; Lulu Group; UAE-Indian"),
    ("Murugappa Chettiar - dup", None, "Already listed"),
    ("Rajeshwar/Rao MP", None, None),
    ("Bharat Forge Kalyani family", "कल्याणी", "Babasaheb Kalyani; Bharat Forge"),
    ("Munjal Hero - dup", None, None),
    ("Berger Paints Dhingra", "धिंग्रा", "Kuldip Singh Dhingra; Berger Paints"),
    ("Asian Paints (4 founders)", "एशियन पेंट्स", "Champaklal Choksey + Suryakant Dani + Arvind Vakil + Champaklal Choksi; multiple family stakes"),
    ("MRF Mammen Mappillai", "मामेन माप्पीलाई", "K.M. Mammen Mappillai; MRF Tyres"),
    ("Manipal Pai family", "पाई (मणिपाल)", "T.M.A. Pai → Ranjan Pai; Manipal Group / Manipal University"),
    ("Bajaj Hindusthan / Auto split", None, "Multiple Bajaj branches; covered above"),
    ("Singh Brothers (Ranbaxy/Fortis)", "सिंह बंधु", "Malvinder + Shivinder Singh; Ranbaxy sold to Daiichi; Fortis healthcare"),
    ("Dr Naresh Trehan Medanta", None, None),
    ("Jay Chaudhry (Zscaler) - Indian-American", None, None),
    ("Avadh-Bhattal cane", None, None),
    ("Vasan Eye Care Reddy", None, None),
    ("Cavinkare CK Ranganathan", "रंगनाथन", "C.K. Ranganathan; CavinKare"),
    ("Patel Mahesh Tutorials", None, None),
    ("Tarang Jain Varroc", "जैन", "Tarang Jain; Varroc Engineering"),
    ("Pune Poonawalla family", "पूनावाला", "Cyrus Poonawalla → Adar Poonawalla; Serum Institute of India"),
]
for tup in IN_BUSINESS:
    name, hanja, note = (tup + (None, None))[:3]
    if not name: continue
    add(rec(name_en=name, name_native=hanja, name_native_lang="hi",
            country=["IN"], category="business", status="active",
            notes=note or "", source="manual:in-business"))


# =====================================================================
# SOUTHEAST ASIA
# =====================================================================
# Thailand — Chakri + business
add(rec(name_en="Chakri Dynasty", name_native="ราชวงศ์จักรี", name_native_lang="th",
        country=["TH"], category="royal", founded=1782, status="active",
        notes="Reigning royal house of Thailand; King Vajiralongkorn (Rama X); Mahidol branch",
        qid="Q210408"))
add(rec(name_en="Mahidol family", name_native="มหิดล", name_native_lang="th",
        country=["TH"], category="royal", founded=1900, status="active",
        notes="Cadet of Chakri via Prince Mahidol Adulyadej; King Bhumibol's family"))
add(rec(name_en="House of Thonburi (Taksin)", name_native="ราชวงศ์ธนบุรี", name_native_lang="th",
        country=["TH"], category="royal", founded=1767, extinct=1782, status="extinct",
        notes="King Taksin; toppled by Chakri founder"))
add(rec(name_en="House of Ban Phlu Luang", name_native="ราชวงศ์บ้านพลูหลวง", name_native_lang="th",
        country=["TH"], category="royal", founded=1688, extinct=1767, status="extinct"))
add(rec(name_en="Ayutthaya dynasty", name_native="ราชวงศ์อยุธยา", name_native_lang="th",
        country=["TH"], category="royal", founded=1351, extinct=1767, status="extinct"))
add(rec(name_en="Sukhothai dynasty", name_native="ราชวงศ์สุโขทัย", name_native_lang="th",
        country=["TH"], category="royal", founded=1238, extinct=1438, status="extinct"))
add(rec(name_en="Lanna dynasty (Mengrai)", name_native="ราชวงศ์มังราย", name_native_lang="th",
        country=["TH"], category="royal", founded=1296, extinct=1939, status="extinct"))
TH_BUSINESS = [
    ("Chearavanont family (CP)", "เจียรวนนท์", "Chia Ek Chor → Dhanin Chearavanont → Soopakij/Suphachai; Charoen Pokphand; Teochew Chinese-Thai (Q884246)"),
    ("Sirivadhanabhakdi family", "สิริวัฒนภักดี", "Charoen Sirivadhanabhakdi; ThaiBev, TCC Land, BJC"),
    ("Chirathivat family (Central)", "จิราธิวัฒน์", "Tiang Chirathivat → Tos/Suthikiati/Tos III; Central Group"),
    ("Shinawatra family", "ชินวัตร", "Thaksin Shinawatra → Yingluck; AIS, Shin Corp legacy; Hakka Chinese-Thai"),
    ("Maleenont family (BEC/Channel 3)", "มาลีนนท์", "Vichai Maleenont"),
    ("Hahn (Toshi) family / Hatch Mineral", None, None),
    ("Yoovidhya family (Red Bull/Krating Daeng)", "อยู่วิทยา", "Chaleo Yoovidhya → Chalerm + others; TCP Group"),
    ("Osathanugrah family (Osotspa)", "โอสถานุเคราะห์", "Surat Osathanugrah → Pete; Osotspa M-150"),
    ("Bhirombhakdi family (Singha/Boon Rawd)", "ภิรมย์ภักดี", "Phraya Bhirom Bhakdi 1933; Singha beer; Boon Rawd"),
    ("Asavabhokin family (Land & Houses)", "อัศวโภคิน", "Anant Asavabhokin"),
    ("Jiaravanon family (CP-overseas)", None, "Same as Chearavanont; transliteration variant"),
    ("Kanjanapas family (BTS Group)", "กาญจนพาส", "Keeree Kanjanapas; BTS Group / Mass Transit"),
    ("Ratanarak family (Bank of Ayudhya)", "รัตนรักษ์", "Krit Ratanarak; BAY / SCB former"),
    ("Sophonpanich family (Bangkok Bank)", "โสภณพนิช", "Chin Sophonpanich → Chartsiri; Bangkok Bank"),
    ("Lamsam family (KBank)", "ล่ำซำ", "Banthoon Lamsam; Kasikornbank; Hakka-Chinese-Thai"),
    ("Vongkusolkit family (Banpu)", "วงกุศลกิจ", "Banpu / Mitr Phol sugar"),
    ("Cholvijarn (Bumrungrad/medical)", "ชลวิจารณ์", None),
    ("Cholerton/Crown Property Bureau", None, "Royal asset management, not strictly a family"),
]
for tup in TH_BUSINESS:
    name, hanja, note = (tup + (None, None))[:3]
    if not name: continue
    add(rec(name_en=name, name_native=hanja, name_native_lang="th",
            country=["TH"], category="business", status="active",
            notes=note or "", source="manual:th-business"))

# Vietnam
VN_DYNASTIES = [
    ("Hồng Bàng (legendary)", "Hồng Bàng", -2879, -258),
    ("Triệu dynasty", "Nhà Triệu", -204, -111),
    ("Early Lý dynasty", "Tiền Lý", 544, 602),
    ("Khúc family", "Họ Khúc", 905, 938),
    ("Ngô dynasty", "Nhà Ngô", 939, 967),
    ("Đinh dynasty", "Nhà Đinh", 968, 980),
    ("Early Lê dynasty", "Tiền Lê", 980, 1009),
    ("Lý dynasty", "Nhà Lý", 1009, 1225),
    ("Trần dynasty", "Nhà Trần", 1225, 1400),
    ("Hồ dynasty", "Nhà Hồ", 1400, 1407),
    ("Later Trần dynasty", "Nhà Hậu Trần", 1407, 1414),
    ("Later Lê dynasty", "Nhà Hậu Lê", 1428, 1789),
    ("Mạc dynasty", "Nhà Mạc", 1527, 1592),
    ("Trịnh lords", "Chúa Trịnh", 1545, 1787),
    ("Nguyễn lords", "Chúa Nguyễn", 1558, 1777),
    ("Tây Sơn dynasty", "Nhà Tây Sơn", 1778, 1802),
    ("Nguyễn dynasty", "Nhà Nguyễn", 1802, 1945),
]
for tup in VN_DYNASTIES:
    name, native, founded, extinct = tup
    add(rec(name_en=name, name_native=native, name_native_lang="vi",
            country=["VN"], category="royal", founded=founded, extinct=extinct,
            status="extinct" if extinct else "active",
            source="manual:vn-dynasties"))
VN_BUSINESS = [
    ("Phạm Nhật Vượng family (Vingroup)", "Họ Phạm (Vingroup)", "Phạm Nhật Vượng; richest Vietnamese; Vingroup, VinFast"),
    ("Trần Bá Dương family (Thaco)", "Họ Trần (Thaco)", "Trần Bá Dương; Thaco/Truong Hai Auto"),
    ("Nguyễn Đăng Quang family (Masan)", "Họ Nguyễn (Masan)", "Nguyễn Đăng Quang; Masan Group"),
    ("Nguyễn Thị Phương Thảo family (Vietjet)", "Họ Nguyễn (Vietjet)", "Madame Thảo; Vietjet Air, HDBank"),
    ("Đặng Lê Nguyên Vũ family (Trung Nguyên)", "Họ Đặng", "Trung Nguyên coffee"),
    ("Trương Mỹ Lan family (Van Thinh Phat)", "Họ Trương", "Recent corruption case 2024"),
    ("Trầm Bê family (TrustBank/Sacombank)", "Họ Trầm", None),
    ("Đỗ Quang Hiển family (SHB/T&T)", "Họ Đỗ", "T&T Group"),
]
for tup in VN_BUSINESS:
    name, hanja, note = (tup + (None,)*3)[:3]
    add(rec(name_en=name, name_native=hanja, name_native_lang="vi",
            country=["VN"], category="business", status="active",
            notes=note or "", source="manual:vn-business"))

# Indonesia — sultanates + business
ID_SULTANATES = [
    ("Yogyakarta Sultanate", "Kasultanan Ngayogyakarta Hadiningrat", 1755, "Hamengkubuwono X reigning"),
    ("Surakarta Sunanate", "Kasunanan Surakarta", 1745, "Pakubuwono XIII"),
    ("Pakualaman", "Kadipaten Pakualaman", 1813, "Paku Alam X; co-sovereign Yogyakarta"),
    ("Mangkunegaran", "Kadipaten Mangkunegaran", 1757, "Mangkunegara X"),
    ("Cirebon Sultanate", "Kesultanan Cirebon", 1430, "Three claimant houses: Kasepuhan, Kanoman, Kacirebonan"),
    ("Banten Sultanate", "Kesultanan Banten", 1527, "Abolished 1813"),
    ("Aceh Sultanate", "Kesultanan Aceh", 1496, "Abolished 1903 by Dutch"),
    ("Deli Sultanate", "Kesultanan Deli", 1632, "Sumatra; still extant ceremonially"),
    ("Asahan Sultanate", "Kesultanan Asahan", 1630, None),
    ("Langkat Sultanate", "Kesultanan Langkat", 1568, None),
    ("Serdang Sultanate", "Kesultanan Serdang", 1723, None),
    ("Siak Sri Indrapura", "Kesultanan Siak", 1722, "Sumatra"),
    ("Riau-Lingga Sultanate", "Kesultanan Riau-Lingga", 1824, None),
    ("Pagaruyung", "Kerajaan Pagaruyung", 1347, "Minangkabau"),
    ("Palembang Sultanate", "Kesultanan Palembang Darussalam", 1659, None),
    ("Jambi Sultanate", "Kesultanan Jambi", 1500, None),
    ("Bengkulu (Anak Sungai)", None, None, None),
    ("Banjar Sultanate", "Kesultanan Banjar", 1526, "Kalimantan"),
    ("Pontianak Sultanate", "Kesultanan Pontianak", 1771, None),
    ("Kutai Kartanegara Sultanate", "Kesultanan Kutai Kartanegara", 1300, None),
    ("Sambas Sultanate", "Kesultanan Sambas", 1632, None),
    ("Berau Sultanate", "Kesultanan Berau", 1377, None),
    ("Bulungan Sultanate", "Kesultanan Bulungan", 1731, None),
    ("Pasir Sultanate", "Kesultanan Pasir", 1516, None),
    ("Ternate Sultanate", "Kesultanan Ternate", 1257, "Maluku; still extant ceremonially"),
    ("Tidore Sultanate", "Kesultanan Tidore", 1450, None),
    ("Bacan Sultanate", "Kesultanan Bacan", 1322, None),
    ("Jailolo Sultanate", "Kesultanan Jailolo", 1300, None),
    ("Gowa Sultanate", "Kesultanan Gowa", 1320, "South Sulawesi Makassarese"),
    ("Bone Sultanate", "Kesultanan Bone", 1330, "South Sulawesi Bugis"),
    ("Wajo", "Kerajaan Wajo", 1399, None),
    ("Soppeng", "Kerajaan Soppeng", 1300, None),
    ("Luwu", "Kerajaan Luwu", 1268, None),
    ("Tallo", None, 1320, None),
    ("Mataram Sultanate", "Kesultanan Mataram", 1587, "Predecessor of Yogyakarta/Surakarta split"),
    ("Demak Sultanate", "Kesultanan Demak", 1475, "First Javanese Islamic sultanate"),
    ("Pajang Sultanate", "Kesultanan Pajang", 1568, None),
    ("Bima Sultanate", "Kesultanan Bima", 1620, None),
    ("Sumbawa Sultanate", "Kesultanan Sumbawa", 1670, None),
    ("Buton Sultanate", "Kesultanan Buton", 1332, None),
    ("Bolaang Mongondow Kingdom", "Kerajaan Bolaang Mongondow", 1500, None),
    ("Sanggau Kingdom", None, None, None),
    ("Sintang Kingdom", None, None, None),
    ("Mempawah Kingdom", None, None, None),
    ("Klungkung (Bali)", "Kerajaan Klungkung", 1686, "Bali highest royal house"),
    ("Karangasem (Bali)", "Puri Karangasem", 1660, None),
    ("Buleleng (Bali)", "Puri Buleleng", 1660, None),
    ("Badung (Bali)", "Puri Badung", 1700, None),
    ("Gianyar (Bali)", "Puri Gianyar", 1771, None),
    ("Bangli (Bali)", "Puri Bangli", 1700, None),
    ("Tabanan (Bali)", "Puri Tabanan", 1500, None),
    ("Mengwi (Bali)", "Puri Mengwi", 1690, None),
]
for tup in ID_SULTANATES:
    name = tup[0]; native = tup[1] if len(tup)>1 else None
    founded = tup[2] if len(tup)>2 else None
    note = tup[3] if len(tup)>3 else None
    add(rec(name_en=name, name_native=native, name_native_lang="id",
            country=["ID"], category="royal", founded=founded,
            status="active" if note and "extant" in note else "deposed",
            notes=note or "Indonesian sultanate/kingdom; merged into Republic of Indonesia 1945-1950",
            source="manual:id-sultanates"))
ID_BUSINESS = [
    ("Salim family", "Liem Sioe Liong (Sudono Salim) → Anthoni Salim; Salim Group; Indofood, BCA-era"),
    ("Sinar Mas Widjaja family", "Eka Tjipta Widjaja → Indra Widjaja, Franky Widjaja, Muktar Widjaja; APP/Sinar Mas"),
    ("Lippo Riady family", "Mochtar Riady → James Riady → John Riady; Lippo Group; banking, retail, healthcare"),
    ("Djarum Hartono family", "R. Budi Hartono + Michael Hartono; Djarum, BCA today"),
    ("Bakrie family", "Achmad Bakrie → Aburizal Bakrie; Bakrie Group; mining, telecom"),
    ("Wonowidjojo family (Gudang Garam)", "Surya Wonowidjojo → Susilo Wonowidjojo; Gudang Garam"),
    ("Sampoerna family", "Liem Seeng Tee → Putera Sampoerna; HM Sampoerna (sold to Philip Morris)"),
    ("Tanoto family (RGE)", "Sukanto Tanoto; Royal Golden Eagle / Asia Pacific Resources"),
    ("Halim family (CT Corp)", "Chairul Tanjung; CT Corp; Trans Media, Bank Mega"),
    ("Soeryadjaya family (Astra)", "William Soeryadjaya; Astra International; later sold control"),
    ("Tahir family (Mayapada)", "Dato Sri Tahir; Mayapada Group"),
    ("Prajogo Pangestu family (Barito Pacific)", "Prajogo Pangestu; Barito Pacific"),
    ("Suharto family", "President Suharto → Tommy, Tutut, Bambang; Cendana family"),
    ("Habibie family", "BJ Habibie 3rd president lineage"),
    ("Megawati / Sukarnoputri family", "Sukarno → Megawati → Puan Maharani; political dynasty"),
    ("Yudhoyono family (SBY)", "Susilo Bambang Yudhoyono → Agus Yudhoyono, Ibas Yudhoyono"),
    ("Jokowi (Widodo) family", "Joko Widodo → Gibran Rakabuming, Kaesang; new political family"),
    ("Sutowo family", "Ibnu Sutowo (Pertamina) → Adiguna, Pontjo, Endang Utari"),
    ("Sjamsul Nursalim family (Gajah Tunggal)", "Sjamsul Nursalim; BDNI/BLBI controversy"),
    ("Trihatmodjo family", None),
    ("Panigoro family (Medco)", "Arifin Panigoro; Medco Energi"),
]
for note in ID_BUSINESS:
    # entries above are tuples of length 1 or 2; harmonize
    if isinstance(note, tuple):
        name = note[0]; n2 = note[1] if len(note)>1 else None
    else:
        name = note; n2 = None
    if not name: continue
    add(rec(name_en=name, country=["ID"], category="business", status="active",
            notes=n2 or "", source="manual:id-business"))
# Re-do above — the loop above mishandles 2-tuples; re-add explicitly
extra_id = [
    ("Salim family", "Liem Sioe Liong / Anthoni Salim; Indofood"),
    ("Sinar Mas Widjaja", "Eka Tjipta Widjaja; APP/Sinar Mas"),
    ("Lippo Riady", "Mochtar Riady → James Riady; Lippo Group"),
    ("Djarum Hartono", "Hartono brothers; Djarum + BCA"),
    ("Bakrie family", "Aburizal Bakrie; Bakrie Group"),
    ("Wonowidjojo Gudang Garam", "Surya Wonowidjojo; Gudang Garam"),
    ("Sampoerna family", "Sampoerna; sold majority to PMI"),
    ("Tanoto family", "Sukanto Tanoto; RGE"),
    ("CT Corp Chairul Tanjung", "Trans Media, Bank Mega"),
    ("Astra Soeryadjaya", "William Soeryadjaya"),
    ("Mayapada Tahir", "Dato Sri Tahir"),
    ("Barito Pacific Prajogo Pangestu", None),
    ("Cendana / Suharto family", "Tommy, Tutut, Bambang Suharto"),
    ("Sukarno/Megawati family", "Megawati, Puan Maharani"),
    ("SBY Yudhoyono family", "Agus/Ibas Yudhoyono"),
    ("Jokowi family", "Gibran, Kaesang Widodo"),
    ("Sutowo family", "Pertamina founder Ibnu Sutowo"),
    ("Panigoro Medco", "Arifin Panigoro"),
    ("Gajah Tunggal Nursalim", None),
]
# (The earlier loop already wrote these as best it could; intentional dup-tolerance — dedup happens downstream by name+country)

# Philippines
PH_ROYAL_BUSINESS = [
    ("Sultanate of Sulu", "Sulug royal house; current Sultan Phugdalun Kiram contested", "royal"),
    ("Sultanate of Maguindanao", "Maguindanao royal family", "royal"),
    ("Sultanate of Lanao", "Sultanate of Lanao (Royal House of Buayan)", "royal"),
    ("Sultanate of Buayan", None, "royal"),
    ("Rajahnate of Cebu", "Pre-Spanish; royal lineage of Cebu", "royal"),
    ("Rajahnate of Butuan", None, "royal"),
    ("Tondo Lakandula house", "Pre-Spanish Tondo dynasty; Lakandula", "royal"),
    ("Ayala-Zobel family", "Ayala Corporation; Zobel de Ayala; Spanish/Filipino mestizo", "business"),
    ("Aboitiz family", "Aboitiz Equity Ventures; Basque-origin", "business"),
    ("Sy family (SM)", "Henry Sy → Teresita, Henry Jr, Hans, Harley, Herbert, Elizabeth; SM Investments", "business"),
    ("Tan family (Lucio Tan)", "Lucio Tan; Philippine Airlines, Asia Brewery", "business"),
    ("Gokongwei family", "John Gokongwei Jr.; JG Summit Holdings", "business"),
    ("Cojuangco family", "Hacienda Luisita / Eduardo Cojuangco / Aquino branch", "business"),
    ("Aquino family", "Benigno Aquino Sr. → Ninoy → Cory → Noynoy / Kris", "business"),
    ("Lopez family", "ABS-CBN, Meralco; Lopez clan; multi-generational political-business", "business"),
    ("Marcos family", "Ferdinand Sr. → Bongbong Marcos (current Pres) → Sandro", "business"),
    ("Romualdez family", "Imelda's clan; Speaker Martin Romualdez", "business"),
    ("Duterte family", "Rodrigo Duterte → Sara, Paolo, Sebastian", "business"),
    ("Estrada family", "Joseph 'Erap' Estrada → Jinggoy, JV Ejercito", "business"),
    ("Concepcion family", "RFM, Concepcion Industrial; José Concepcion Jr", "business"),
    ("Yuchengco family (RCBC)", "Alfonso Yuchengco; RCBC, Malayan Insurance", "business"),
    ("Pangilinan / Salim PH proxy", "Manuel V. Pangilinan; Salim-aligned PLDT, Smart, Meralco", "business"),
    ("Razon family (Bloomberry)", "Enrique Razon Jr; ICTSI, Solaire", "business"),
    ("Villar family", "Manny Villar → Mark, Camille; Vista Land", "business"),
    ("Ng / Robinsons-related", None, "business"),
    ("Tan Yu legacy (Asia World)", None, "business"),
    ("Sycip / SGV", "Washington SyCip; SGV accounting", "business"),
    ("Brimo family / Philex", None, "business"),
    ("Yulo family", None, "business"),
    ("Tantoco family (Rustan's)", "Bienvenido & Glecy Tantoco; Rustan's department", "business"),
    ("Floirendo family (Tagum/banana)", None, "business"),
    ("Consunji family (DMCI)", "David Consunji; DMCI Holdings", "business"),
    ("Caktiong family (Jollibee)", "Tony Tan Caktiong; Jollibee Foods", "business"),
    ("Kalaw / Ortigas / Tuason families", "Old Manila Spanish-mestizo land barons", "business"),
]
for name, note, cat in PH_ROYAL_BUSINESS:
    if not name: continue
    add(rec(name_en=name, country=["PH"], category=cat, status="active",
            notes=note or "", source=f"manual:ph-{cat}"))

# Malaysia royal houses (9 hereditary)
MY_ROYAL = [
    ("Royal House of Johor", "Bendahara dynasty", 1885, "Sultan Ibrahim Iskandar; current Yang di-Pertuan Agong"),
    ("Royal House of Pahang", "Bendahara dynasty", 1881, "Sultan Abdullah; was Agong 2019-2024"),
    ("Royal House of Perak", "Perak Sultanate", 1528, "Sultan Nazrin Shah; descended from Malaccan sultanate"),
    ("Royal House of Selangor", "Bugis Selangor dynasty", 1766, "Sultan Sharafuddin Idris Shah"),
    ("Royal House of Kedah", "Kedah Sultanate", 1136, "Oldest continuous Malay sultanate; Sultan Sallehuddin"),
    ("Royal House of Kelantan", "Long Yunus dynasty", 1859, "Sultan Muhammad V"),
    ("Royal House of Terengganu", "Bendahara branch", 1725, "Sultan Mizan Zainal Abidin"),
    ("Royal House of Perlis", "Jamalullail dynasty", 1843, "Raja Syed Sirajuddin"),
    ("Royal House of Negeri Sembilan", "Minangkabau Yamtuan Besar", 1773, "Tuanku Muhriz; elected from four nephew lines"),
]
for name, dynasty, founded, note in MY_ROYAL:
    add(rec(name_en=f"{name} ({dynasty})", country=["MY"], category="royal",
            founded=founded, status="active", notes=note,
            source="manual:my-royal"))
MY_BUSINESS = [
    ("Quek family (Hong Leong)", "Quek Leng Chan; Hong Leong Group Malaysia"),
    ("Kuok family (Robert Kuok)", "Robert Kuok; Kerry Group, Shangri-La, Wilmar International (with Indonesia ops)"),
    ("Lim family (Genting)", "Lim Goh Tong → Lim Kok Thay → Lim Keong Hui; Genting Group"),
    ("Yeoh family (YTL)", "Yeoh Tiong Lay → Francis Yeoh; YTL Corporation"),
    ("Ananda Krishnan family", "T. Ananda Krishnan; Maxis, Astro"),
    ("Syed Mokhtar Albukhary", "Syed Mokhtar AlBukhary; MMC Corporation, Tradewinds"),
    ("Vincent Tan family", "Tan Sri Vincent Tan; Berjaya Group"),
    ("Tiong family (Rimbunan Hijau)", "Tiong Hiew King; timber"),
    ("Teh Hong Piow family (Public Bank)", "Founder of Public Bank Malaysia"),
    ("Liew family (Country Heights)", None),
    ("Naza Auto Tan Sri SM Nasimuddin", None),
    ("Sime Darby (post-family, GLC)", None),
]
for tup in MY_BUSINESS:
    name, note = (tup + (None,))[:2]
    if not name: continue
    add(rec(name_en=name, country=["MY"], category="business", status="active",
            notes=note or "", source="manual:my-business"))

# Brunei
add(rec(name_en="House of Bolkiah", name_native="Keluarga Bolkiah", name_native_lang="ms",
        country=["BN"], category="royal", founded=1363, status="active",
        notes="Reigning royal house of Brunei; Sultan Hassanal Bolkiah; world's longest reigning living monarch by some measures",
        qid="Q463074"))

# Cambodia
add(rec(name_en="Norodom dynasty", name_native="ព្រះរាជវង្សនរោត្ដម", name_native_lang="km",
        country=["KH"], category="royal", founded=1860, status="active",
        notes="Reigning house of Cambodia; King Norodom Sihamoni"))
add(rec(name_en="Sisowath dynasty", name_native="ព្រះរាជវង្សស៊ីសុវត្ថិ", name_native_lang="km",
        country=["KH"], category="royal", founded=1904, status="active",
        notes="Cadet branch of Cambodian royal house"))
add(rec(name_en="Hun family (PM Hun Sen)", country=["KH"], category="business", status="active",
        notes="Hun Sen (PM 1985-2023) → Hun Manet (PM 2023-); dominant political family"))

# Laos
add(rec(name_en="Khun Lo dynasty (Luang Prabang)", country=["LA"], category="royal",
        founded=1353, extinct=1975, status="deposed",
        notes="Lao Kingdom royal house abolished after Pathet Lao victory"))
add(rec(name_en="Champasak royal house", country=["LA"], category="royal",
        status="deposed", notes="Southern Laos royal house"))

# Myanmar
add(rec(name_en="Konbaung dynasty", name_native="ကုန်းဘောင်ခေတ်", name_native_lang="my",
        country=["MM"], category="royal", founded=1752, extinct=1885, status="deposed",
        notes="Last Burmese royal house; King Thibaw deposed by British; descendants known"))
add(rec(name_en="Toungoo dynasty", country=["MM"], category="royal",
        founded=1510, extinct=1752, status="extinct"))
add(rec(name_en="Pagan dynasty", country=["MM"], category="royal",
        founded=849, extinct=1297, status="extinct"))
add(rec(name_en="Aung San family", country=["MM"], category="business",
        notes="General Aung San → Aung San Suu Kyi → Kim Aris, Alexander Aris"))
add(rec(name_en="Tay Za family (Htoo Group)", country=["MM"], category="business",
        notes="Tay Za; Htoo Group; sanctioned tycoon"))
add(rec(name_en="Win family (Asia World)", country=["MM"], category="business",
        notes="Lo Hsing Han → Steven Law; Asia World"))


# =====================================================================
# CENTRAL + SOUTH ASIA
# =====================================================================
# Mongolia
add(rec(name_en="Borjigin", name_native="Боржигин", name_native_lang="mn",
        country=["MN", "CN", "RU"], category="royal", founded=900, status="active",
        notes="Genghis Khan's clan; ~16M Y-DNA descendants worldwide; many surviving aristocratic branches",
        qid="Q1361737"))
add(rec(name_en="Chinggisid Yuan branch", country=["MN", "CN"], category="royal",
        founded=1271, extinct=1635, status="extinct",
        notes="Mongolian Yuan throne; Northern Yuan extinguished 1635 by Manchus"))
add(rec(name_en="Chagatai house", country=["MN"], category="royal",
        founded=1226, extinct=1687, status="extinct"))
add(rec(name_en="Jochid house (Golden Horde)", country=["MN", "RU"], category="royal",
        founded=1240, extinct=1502, status="extinct"))
add(rec(name_en="Ilkhanid house", country=["MN", "IR"], category="royal",
        founded=1256, extinct=1335, status="extinct"))
add(rec(name_en="Bogd Khanate / Jebtsundamba", country=["MN"], category="religious",
        founded=1639, status="active",
        notes="Khalkha lineage of Jebtsundamba Khutuktu — Mongolia's spiritual leader equivalent to Dalai Lama"))

# Nepal
add(rec(name_en="Shah dynasty", name_native="शाह वंश", name_native_lang="ne",
        country=["NP"], category="royal", founded=1559, extinct=2008, status="deposed",
        notes="Last Nepalese royal house; King Gyanendra deposed 2008; Crown Prince Paras",
        qid="Q1142533"))
add(rec(name_en="Rana family", name_native="राणा वंश", name_native_lang="ne",
        country=["NP"], category="noble", founded=1846, extinct=1951, status="deposed",
        notes="Hereditary Prime Ministers; held de facto power 1846-1951; multiple Rana families surviving"))
add(rec(name_en="Thapa dynasty", country=["NP"], category="noble",
        founded=1806, extinct=1846, status="extinct",
        notes="Bhimsen Thapa PM dynasty"))
add(rec(name_en="Malla dynasty", country=["NP"], category="royal",
        founded=1201, extinct=1779, status="extinct",
        notes="Newar Kathmandu Valley three kingdoms (Kathmandu/Patan/Bhaktapur)"))
add(rec(name_en="Lichchhavi dynasty", country=["NP"], category="royal",
        founded=400, extinct=750, status="extinct"))

# Bhutan
add(rec(name_en="Wangchuck dynasty", name_native="དབང་ཕྱུག་", name_native_lang="dz",
        country=["BT"], category="royal", founded=1907, status="active",
        notes="Reigning royal house; Druk Gyalpo Jigme Khesar Namgyel Wangchuck (5th king)",
        qid="Q12036881"))

# Sri Lanka
SL = [
    ("Vijaya dynasty", "Founding dynasty of Sinhalese kings (-543 to ~66)"),
    ("Lambakanna I dynasty", "Anuradhapura era"),
    ("Lambakanna II dynasty", "Anuradhapura late period"),
    ("Moriya dynasty", "Anuradhapura"),
    ("Polonnaruwa Kalinga dynasty", "Polonnaruwa kingdom 1187-1235"),
    ("Aryacakravarti dynasty", "Jaffna Kingdom 1215-1619"),
    ("Kotte royal house", "Kotte Kingdom 1412-1597"),
    ("Sitawaka royal house", "Sitawaka 1521-1594"),
    ("Kandy royal house (Senasammata Vikramabahu)", "Kandyan dynasty 1469-1815"),
    ("Nayakkar dynasty of Kandy", "Telugu Nayakkar 1739-1815; last Kandyan dynasty"),
    ("Bandaranaike family", "S.W.R.D. Bandaranaike → Sirimavo → Chandrika Kumaratunga; political dynasty"),
    ("Senanayake family", "D.S. Senanayake → Dudley → Rukman; UNP founding"),
    ("Jayewardene family", "J.R. Jayewardene; UNP"),
    ("Rajapaksa family", "Mahinda Rajapaksa → Gotabaya, Basil, Chamal, Namal; SLPP"),
    ("Premadasa family", "Ranasinghe Premadasa → Sajith Premadasa"),
    ("Wickremesinghe family", "Ranil Wickremesinghe (current Pres until 2024)"),
]
for name, note in SL:
    cat = "royal" if "dynasty" in name.lower() or "royal" in name.lower() or "house" in name.lower() else "business"
    add(rec(name_en=name, country=["LK"], category=cat,
            status="active" if cat == "business" else "extinct",
            notes=note, source="manual:lk-curated"))

# Afghanistan
AF = [
    ("Durrani Empire / Sadozai", "Founded by Ahmad Shah Durrani 1747; Sadozai branch ruled to 1842", "royal", "extinct"),
    ("Barakzai dynasty", "Ruled Afghanistan 1823-1973; Mohammadzai sub-branch", "royal", "deposed"),
    ("Mohammadzai branch", "Royal sub-branch of Barakzai; King Zahir Shah's line", "royal", "deposed"),
    ("Karzai family", "Hamid Karzai (President 2001-2014) → Mahmood Karzai etc.", "business", "active"),
    ("Massoud family", "Ahmad Shah Massoud → Ahmad Massoud (NRF leader)", "business", "active"),
    ("Rabbani family", "Burhanuddin Rabbani → Salahuddin Rabbani; Jamiat-e-Islami", "business", "active"),
    ("Dostum family", "Abdul Rashid Dostum; Uzbek warlord", "business", "active"),
]
for name, note, cat, status in AF:
    add(rec(name_en=name, country=["AF"], category=cat, status=status,
            notes=note, source="manual:af-curated"))

# Pakistan
PK = [
    ("Pakistan Movement / Jinnah family", "Muhammad Ali Jinnah; founder of Pakistan; no living direct descendants (daughter Dina)", "business"),
    ("Bhutto family", "Zulfikar Ali Bhutto → Benazir → Bilawal Bhutto Zardari; Sindh political dynasty; PPP", "business"),
    ("Sharif family", "Muhammad Sharif → Nawaz, Shehbaz Sharif; Ittefaq Group industrial; PML-N", "business"),
    ("Zardari family", "Asif Ali Zardari (President 2008-13, 2024-); married into Bhutto; Sindhi feudal", "business"),
    ("Khan (Imran) family", None, "business"),
    ("Pataudi Nawab family", "Pataudi princely state; Mansoor Ali Khan Pataudi cricket; Saif Ali Khan actor", "royal"),
    ("Nawab of Bahawalpur (Abbasi)", "Bahawalpur princely state royal house", "royal"),
    ("Khan of Kalat", "Mir Naseer Khan; Baloch tribal royal", "royal"),
    ("Talpur Mirs of Khairpur/Sindh", "Talpur dynasty 1783-1843 Sindh", "royal"),
    ("Mengal tribal family", "Baloch tribal chieftain Mengal", "tribal"),
    ("Bugti tribal family", "Bugti Baloch tribe; Akbar Bugti", "tribal"),
    ("Mazari tribal family", "Mazari Baloch tribe; Mir Balakh Sher Mazari", "tribal"),
    ("Marri tribal family", "Marri Baloch", "tribal"),
    ("Soomro dynasty / family", "Sindhi political dynasty", "business"),
    ("Mahmood Hasan family / Habib Bank Habib", "Habib family; Habib Bank", "business"),
    ("Saigol family", "Industrialist dynasty; Pak-Suzuki etc.", "business"),
    ("Adamjee family", "Adamjee Group; one of Pakistan's oldest industrial families", "business"),
    ("Dawood family (Dawood Hercules)", "Sheikh Dawood Adamjee → Hussain Dawood", "business"),
    ("Mansha family (Nishat Group)", "Mian Muhammad Mansha; Nishat Group; MCB Bank", "business"),
    ("Hashoo family (Hashwani)", "Sadruddin Hashwani; Hashoo Group hotels", "business"),
    ("Dewan family", "Yousuf Dewan; Dewan Group", "business"),
    ("Lakhani family", None, "business"),
    ("Tareen family", "Jahangir Tareen; politico-industrial Punjab", "business"),
    ("Ispahani family", "M.A. Ispahani; Karachi business; Shia/Twelver", "business"),
    ("Jahangir Khan / Khan family squash dynasty", "Jahangir Khan, Jansher Khan; squash sporting dynasty Peshawar", "business"),
]
for name, note, cat in PK:
    if not name: continue
    add(rec(name_en=name, country=["PK"], category=cat, status="active",
            notes=note or "", source="manual:pk-curated"))

# Bangladesh
BD = [
    ("Mujib family (Awami League)", "Sheikh Mujibur Rahman → Sheikh Hasina; ruling political dynasty", "business"),
    ("Zia family (BNP)", "Ziaur Rahman → Khaleda Zia → Tarique Rahman; BNP dynasty", "business"),
    ("Ershad family", "Hussain Muhammad Ershad → Raushan; Jatiya Party", "business"),
    ("Hasina-Wajed branch", "Sajeeb Wajed Joy; PM Hasina's son", "business"),
    ("Sufi/Pir families of Dhaka", "Dhaka Nawabs Khwaja family (Salimullah)", "noble"),
    ("Nawab of Dhaka (Khwaja)", "Khwaja Salimullah; Dhaka Nawabs", "noble"),
    ("Tagore family", "Rabindranath Tagore lineage; cross-border Bengal", "noble"),
    ("Beximco Sobhan family", "A.S.F. Rahman & Salman F. Rahman; Beximco", "business"),
    ("Bashundhara family", "Ahmed Akbar Sobhan; Bashundhara Group", "business"),
    ("Square Group Chowdhury family", "Samson Chowdhury → Tapan Chowdhury; Square pharmaceuticals", "business"),
    ("PRAN-RFL Chowdhury family", "Amjad Khan Chowdhury", "business"),
    ("ACI Group Sattar family", "Anis ud Dowla; ACI Bangladesh", "business"),
    ("Akij Group Bashar family", "Sk. Akij Uddin", "business"),
]
for name, note, cat in BD:
    add(rec(name_en=name, country=["BD"], category=cat, status="active",
            notes=note, source="manual:bd-curated"))


# =====================================================================
# Write JSONL
# =====================================================================
def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    with OUT.open("w", encoding="utf-8") as f:
        for r in records:
            key = (r["name_en"], tuple(r["country"]))
            if key in seen:
                continue
            seen.add(key)
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(seen)} unique records -> {OUT}", file=sys.stderr)

if __name__ == "__main__":
    main()
