# CLAUDE.md — Royals

> 전세계 각 국가의 **모든 가문(왕가·귀족·씨족·기업가문)**을 빠짐없이 수집하고, 가문 간 혈연·혼인·사업 연결 관계를 매핑해 현재까지의 연결고리와 사업 현황을 추적하는 데이터 프로젝트.

## 프로젝트 목적

| 단계 | 산출물 |
|------|--------|
| **Phase 1 (현재)** | 국가별 트래킹 가능한 모든 가문 마스터 리스트 (중복 0, 누락 최소화) |
| Phase 2 | 가문 내부 인물·세대 그래프 (creator → current head) |
| Phase 3 | 가문 ↔ 가문 관계 그래프 (혼인·혈연·사업·정치) |
| Phase 4 | 가문 보유/지배 사업체 매핑 (지분·이사회·재단) |

## 수집 범위 (Phase 1)

| 카테고리 | 포함 |
|----------|------|
| 현존 왕가 | 영국·일본·태국·사우디·모로코·스페인 등 27개 군주국 |
| 폐위·망명 왕가 | Bourbon, Romanov, Habsburg, Hohenzollern, Qing, Joseon, Ottoman, Pahlavi 등 |
| 귀족 가문 | 영국 Peerage, 프랑스 Almanach de Gotha, 독일 Hochadel, 폴란드 Szlachta 등 |
| 부족·씨족 | 스코틀랜드 Clans, 한국 본관·종가, 중국 家族, 일본 氏族, 아랍 부족, 아프리카 chieftaincy |
| 기업 가문 | Rothschild, Rockefeller, Walton, Koch, Mars, 삼성 이씨, 현대 정씨, LG 구씨, Hermès, LVMH Arnault, Agnelli, Wallenberg, Tata, Ambani 등 |
| 종교 가문 | 교황령 귀족, 시아파 sayyid, 티베트 lineage, 정교회 hierarch 가문 |
| 식민지 후예 | Latin American criollo 가문, 인도 princely state, Philippine mestizo 가문 |

## 데이터 소스 (수단 가리지 않음)

| 우선순위 | 소스 | 비고 |
|---------|------|------|
| ★★★ | Wikidata SPARQL | QID = 가문 canonical ID, 모든 위키피디아 cross-lang 연결 |
| ★★★ | Wikipedia categories | "House of X", "Noble families of Y", "Dynasties of Z" |
| ★★ | GitHub 데이터셋 | GEDCOM dumps, royal-family JSON, geneanet exports |
| ★★ | Hugging Face | royalty/nobility/genealogy 데이터셋 |
| ★★ | Paradox 게임 | CK3 dynasties.txt (역대 최대 가문 DB), EU4, Vic3 |
| ★ | Burke's Peerage / Almanach de Gotha | 페어드 (수동 매핑) |
| ★ | Geni.com / FamilySearch / WikiTree | API or scrape |
| ★ | 한국 족보 (성씨별 본관) | 행정안전부 통계 + 종친회 |
| ★ | Forbes 가족 부 / Bloomberg Billionaires | 기업 가문 |

## 마스터 스키마

```jsonc
{
  "id": "Q44613",                    // Wikidata QID (canonical)
  "names": {
    "en": "House of Habsburg",
    "ko": "합스부르크가",
    "de": "Haus Habsburg",
    "ja": "ハプスブルク家"
  },
  "country": ["AT", "ES", "HU", "..."],  // ISO 3166-1
  "category": "royal|noble|clan|business|religious|tribal",
  "period": {"founded": 1020, "extinct": null},
  "status": "active|extinct|deposed|merged",
  "head_current": "Q...",             // Wikidata QID of current head
  "sources": ["wikidata", "ck3", "github:repo/file"],
  "businesses": [],                   // Phase 4
  "relations": []                     // Phase 3
}
```

## 디렉토리 구조

```
Royals/
├── CLAUDE.md
├── data/
│   ├── raw/                # 소스별 원본 덤프
│   │   ├── wikidata/
│   │   ├── wikipedia/
│   │   ├── github/
│   │   ├── huggingface/
│   │   ├── ck3/            # Crusader Kings 3 dynasties
│   │   └── manual/
│   ├── by_country/         # 국가코드별 정규화 (KR.jsonl, JP.jsonl, …)
│   ├── by_category/        # royal/noble/clan/business/…
│   └── master/             # 전체 통합 + 중복 제거 (families.jsonl)
├── scripts/
│   ├── fetchers/           # 소스별 수집 스크립트
│   ├── normalize/          # 스키마 정규화
│   ├── dedup/              # Wikidata QID 기반 중복 제거
│   └── audit/              # 누락·중복 검증
├── docs/
│   ├── sources.md          # 소스 레지스트리 + 라이선스
│   ├── coverage.md         # 국가별·카테고리별 진행도
│   └── decisions.md        # 스키마/스코프 결정 기록
└── .gitignore
```

## 자율 실행 원칙 (이 프로젝트 특수)

- **누락 < 중복** — 의심스러우면 일단 포함, 나중에 Wikidata QID로 자동 dedup
- **canonical ID는 Wikidata QID** — QID 없으면 임시 ID `royals:<country>:<slug>` 부여 후 나중에 QID 발견 시 머지
- **국가 코드는 ISO 3166-1 alpha-2**, 다국적 가문은 배열로
- **수집 결과는 JSONL** (스트리밍·머지 용이), 사람이 보는 요약은 Markdown 별도

## 글로벌 규칙 적용

자율 실행, Chrome 자동화 표준, "커밋" 단축 워크플로우(MD→stage→commit→push), 시크릿 자동 거부 — 글로벌 `~/.claude/CLAUDE.md` 그대로 적용.

## 진행 현황

| 항목 | 상태 |
|------|------|
| 프로젝트 부트스트랩 | ✅ 2026-05-23 |
| Phase 1 병렬 수집 1차 (8개 소스 동시) | ✅ 2026-05-23 |
| Phase 1 통합·dedup | ✅ 2026-05-23 |
| Phase 1.x royal92 + royalconstellations (+282, 17 QID merges) | ✅ 2026-05-23 |
| Phase 1.x Islamic Atlas + ctm_bench (+277, 26 QID merges) | ✅ 2026-05-23 |
| Phase 1.5 country enrichment (8,596 'none' 해소) | ✅ 2026-05-23 |
| Phase 1.5 CN/IN 갭 fill (+1,068) | ✅ 2026-05-23 |
| **Phase 2 인물 그래프 (banked 8,291)** | ✅ 2026-05-23 |
| **Phase 2b Wikidata 인물 enrichment — 43,770 persons / 7,007 families / 6,127 head_current** | ✅ 2026-05-23 |
| **Phase 3 친족 그래프 (710 edges, 290+ families)** | ✅ 2026-05-23 |
| **Phase 4 사업 매핑 (3,769 records)** | ✅ 2026-05-23 |
| **Phase 4b Forbes-unmatched → +1,614 business families (master → 100,108)** | ✅ 2026-05-23 |
| Phase 1.5 non-family 필터링 (0 drop — 입력이 이미 family-class 제한) | ✅ 2026-05-23 |

### 최종 산출물 (Phase 1-4 + 후속)

| 산출물 | 규모 |
|---|---:|
| `data/master/families.jsonl` | **100,108** deduped |
| `data/master/persons.jsonl` | **43,770 persons** (banked 8,291 + Wikidata 35,479) |
| `data/master/relations.jsonl` | **710 family-family edges** |
| `data/master/businesses.jsonl` | **3,769 business records** |
| `data/master/persons_by_family/<id>.jsonl` | **7,007 files** |
| `data/master/_relations_graph.json` | D3-compatible node-link graph |
| `data/master/_persons_wikidata.jsonl` | 10,670 fetched Wikidata claim rows (Phase 2b cache) |
| `data/master/_persons_fetched.txt` | resume marker — list of fetched QIDs |
| `data/master/_hf_candidates.jsonl` | 6,568 HF Wikidata-people 후보 (Phase 2b step 3) |
| `data/by_country/<ISO>.jsonl` | 881 files |
| `data/by_category/<cat>.jsonl` | 8 files |
| `data/raw/*` | 121,113 raw entries (11 source channels) |
| `data/master/_country_enrichment.jsonl` | 44,256 audit rows |
| `data/master/_forbes_unmatched.tsv` | 733 Forbes 미매칭 (Phase 4 후속 leads) |
| `data/master/_filtered_non_families.jsonl` | (현재 빈 파일 — 입력 단계에서 이미 필터링) |
| 다운로드 데이터 (`data/raw/huggingface/`, `data/raw/github/`) | 12.6GB (gitignored) |

### Phase 2 + 2b 핵심: 인물

- **43,770 persons** across **7,007 families with members** (genuine kin-groups: 5,445)
- **6,127 family.head_current 자동 채움** (5,824 newly filled)
- Phase 2b: yale-cultural-heritage/wikidata-people 250,334 bios → 103,370 candidates → 35,670 wbgetentities calls → 35,479 persons emitted
- 가장 많은 인물: Robert II kin-group(827), Six Dynasties(392), Baldwin V(240), Tang/Song/Yuan/Ming/Qing(200 each), Hanover(146 + Charles III as head), Romanov(130 + Maria Vladimirovna as head), Han(111), Counts of Freiburg(99), 17th Dynasty Egypt(99), Guggenheim(75)

### Phase 3 + 3b 핵심: 가문 관계

- **710 edges across 290+ families**
- type 분포: blood 360 · marriage 217 · succession 133
- 상위 연결: Robert II kin-group(57), Tudor(25), Baldwin V(23), Midrārid(21), Windsor(21), Spencer(18), Hanover(17), Plantagenet(16), Beaufort(14)

### Phase 4 핵심: 사업

- 1,071 business records / 338 families
- 50 hand-curated canonical companies (Samsung/LG/Hyundai 등 한국 chaebol 8, 일본 zaibatsu 6, 미국 Walton/Koch/Mars 등 7, 유럽 LVMH/Hermès/L'Oréal 등 12, 인도 Tata/Reliance/Adani 6, HK/SE Asia 6, LatAm 3, 왕가 자산 3)
- Forbes top-1000 (1014-15) 매칭 267/1000
- Bloomberg billionaires (2018-19) 매칭 143
- Forbes World 2019 매칭 611

### 최종 상위 국가 (Phase 1.5)

KR 10,930 · JP 6,990 · DE 4,979 · RU 4,184 · FR 3,391 · IT 2,911 · US 2,847 · CH 2,297 · GB 2,145 · IN 1,901 · SE 1,829 · AT 1,787 · CN 1,236 · ES 1,174

### Phase 1.5 파이프라인 (재현용)

```bash
# raw 추가/변경 시 — 백업을 지운 후 fresh 통합
rm -f data/master/_normalized.pre_enrich.jsonl
python3 scripts/normalize/to_master_schema.py    # raw → _normalized.jsonl
python3 scripts/normalize/apply_enrichment.py    # P17/P27/P495 overlay
python3 scripts/dedup/merge_by_qid.py            # QID dedup → families.jsonl
python3 scripts/normalize/split_indexes.py       # by_country/ + by_category/
```

자세한 통계는 `docs/coverage.md`, 소스 레지스트리는 `docs/sources.md`.
