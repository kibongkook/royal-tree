# Sources — Royals Phase 1

수집에 사용한 모든 외부 소스의 레지스트리. 재현 가능성·라이선스 추적 목적.

## ★★★ Tier 1 — Canonical

### Wikidata SPARQL
- **Endpoint**: https://query.wikidata.org/sparql
- **수집 스크립트**: `scripts/fetchers/wikidata_harvest.py` + `wikidata_queries.sql`
- **수집 결과**: `data/raw/wikidata/families.jsonl` — 52,158 entries
- **방식**: `wdt:P31/wdt:P279*` 로 noble family/dynasty/royal house 서브클래스 전체 재귀; country (P17) chunk별 분할 쿼리
- **라이선스**: CC0 (Wikidata)
- **핵심 클래스**: Q8436 noble family, Q164950 dynasty, Q13417114 noble house, Q188784 royal house, Q4438121 royal family, Q5621421 Scottish clan, Q56236697 Chinese clan
- **알려진 이슈**: Q188784 일부 fictional 캐릭터 포함 (Hal Jordan, Elastigirl 등) — `to_master_schema.py`에서 필터링

### Wikipedia categories
- **수집 스크립트**: `scripts/fetchers/wikipedia_categories.sh` + `wikipedia_asia_deep.sh`
- **수집 결과**: `data/raw/wikipedia/families.jsonl` (26,456) + `families_asia.jsonl` (18,866)
- **방식**: MediaWiki API `list=categorymembers` 재귀 (깊이 1~3); 페이지마다 `pageprops.wikibase_item`으로 QID 동시 조회
- **언어**: en, ko, ja, zh, ar, ru, fr, de
- **시드 카테고리**:
  - en.wp: `Category:Noble_families_by_country`, `Category:Dynasties`, `Category:Business_families`, `Category:Scottish_clans`, etc.
  - ko.wp: `분류:한국의_가문`, `분류:조선의_가문`
  - ja.wp: `Category:日本の氏族`, `Category:藩`, `Category:大名家`, `Category:華族`
  - zh.wp: `Category:中國家族`
  - ar.wp: `تصنيف:عائلات_عربية`
  - ru.wp: `Категория:Дворянские_роды_России`
- **라이선스**: CC BY-SA 4.0 (Wikipedia)

## ★★★ Tier 2 — Game data

### Crusader Kings 3 / 2, Europa Universalis 4
- **수집 스크립트**: `scripts/fetchers/paradox_extract.py`
- **소스 레포**:
  - `mgp1212121212/ck3_vanilla` (CK3 vanilla 추출)
  - `UberEpicZach/The-Kingdom-of-Heaven` (CK3 SWMH delta)
  - `jonjowett/ck2_mods` (CK2 vanilla via community patch)
  - `jjsfw-jumbi/elder-kings-ck2` (TES — fictional, 별도 파일)
  - `JakubOwadowski/RTOE` + `tomato747/eu4tomatomod` (EU4 1069 tags + 176 enriched)
- **수집 결과**: 
  - `data/raw/ck3/dynasties.jsonl` (5,018) + `houses.jsonl` (432) + `dynasties_kingdom_heaven.jsonl` (485)
  - `data/raw/ck2/dynasties.jsonl` (8,418, 동물 329개 포함)
  - `data/raw/eu4/countries.jsonl` (1,069)
- **방식**: 자체 Paradox Clausewitz 파일 파서; 8개 언어 loc 통합
- **라이선스**: Paradox Interactive 게임 콘텐츠 ToU (개인·연구 용도 fair use; 재배포 제한). 메타데이터만 추출.
- **갭**: EU4 vanilla 893/1069 tags 미완 (mod repo가 override만 포함)

## ★★ Tier 3 — GitHub datasets

총 36 repos 클론 (7.8GB), `data/raw/github/catalog.jsonl` 카탈로그.

| Repo | Stars | 내용 |
|---|---:|---|
| `alicetinkaya76/islamic-civilization-atlas` | 0 | 186 Islamic dynasties + 831 rulers (51-col schema, TR+EN+AR) |
| `nbremer/royalconstellations` | n/a | 유럽 왕가 2,800명 + 7,400 친족 엣지 (D3 viz 원본) |
| `bertob/dynasty` | n/a | 영국/로마/헝가리 군주 CSV |
| `AkLabx/TimelineHistory` | n/a | 인도 왕 2,357명 (Hindi+English JSON) |
| `Linking-ai/ctm_bench` | n/a | 중국 dynasty KG (figure_zh, event_zh, place_zh) — EACL'26 |
| `arbre-app/public-gedcoms` | n/a | royal92.ged (1992 유럽 왕족 GEDCOM, 8,275명, PD) + pres2020.ged |
| `richard512/Little-Big-Data` | n/a | top1000billionaires.csv (Forbes 2014-15) |
| `Seshat-Global-History-Databank/cliopatria` | n/a | polities polygons over time (geojson) |
| 외 28 repos | | catalog.jsonl 참조 |

스크레이프 스크립트: `scripts/fetchers/github_search.sh` + `github_clone.sh`. 검증: `scripts/audit/inspect_github_repos.py`.

## ★★ Tier 4 — Hugging Face datasets

총 38 datasets 다운로드 (4.8GB), `data/raw/huggingface/catalog.jsonl`.

| Dataset | 크기 | 내용 |
|---|---|---|
| `yale-cultural-heritage/wikidata-people` | 62MB | 22.5만 Wikidata 인물 + QID — Phase 2 인물 그래프 기반 |
| `philippesaade/wikidata` | 175GB (size-skip) | Wikidata 풀덤프 Sep 2024 — chunk별 selective fetch 필요 |
| `derenrich/wikidata-enwiki-categories-and-statements` | 957MB | enwiki 카테고리 ↔ Wikidata claim |
| `willpowers/Wikidata-celebrity-parent` | TSV | 부모-자식 페어 — Phase 3 친족 시드 |
| `QingYuYunTu/Chinese_Historical_Figures_Dialogue` | 53MB | 중국 역사 인물 대화 |
| `jungypark/joseon-5-kings-qa` | 251 records | 조선 왕 QA |
| `rayliuca/WikidataLabels` | 21GB (size-skip) | Wikidata 라벨 400+ 언어 |

게이트된 데이터셋 (수동 동의 필요): `adzcai/genealogy_synthetic`, `RonyOliveira/JK-RAG-Biography`.

## ★★ Tier 5 — Manual curation

`data/raw/manual/` 6,797 entries.

| 파일 | 엔트리 | 범위 |
|---|---:|---|
| `asia_families.jsonl` | 3,473 | 22개 아시아국 (KR 본관 1,555 + JP 한 541 + IN princely 244 + 6개 차바리/zaibatsu/Confucius/etc.) |
| `europe_americas_business_families.jsonl` | 500 | 유럽 왕족 12 + 클레이만트 16 + UK 24 ducal + Russian rurikid 30 + 글로벌 비즈니스 30+ + 미국 정치/사업 30+ + 라틴아메리카 6개국 oligarch + 등 |
| `mea_families.jsonl` | 484 | 중동·아프리카 484 (Nigeria 35, Turkey 30, Saudi 29, etc.) |
| `kr_bongwan.jsonl` | 1,555 | ko.wp 한국의_성씨_목록 |
| `jp_han.jsonl` | 541 | ja.wp 藩の一覧 |
| `in_princely_states.jsonl` | 244 | en.wp List_of_princely_states_of_British_India |

## 라이선스 매트릭스

| 소스 | 라이선스 | 재배포 가능 | 비고 |
|---|---|---|---|
| Wikidata | CC0 | ✅ | 자유롭게 사용 |
| Wikipedia | CC BY-SA 4.0 | ✅ (attribution + share-alike) | text/markup 인용 가능 |
| Paradox 게임 데이터 | Proprietary | ⚠️ fair use | 게임 콘텐츠 재배포 제한, 메타데이터·통계는 허용 |
| GitHub repos | 레포별 상이 | catalog.jsonl 의 license 필드 참조 | MIT/CC 일부, ALL_RIGHTS_RESERVED도 일부 |
| Hugging Face | 데이터셋별 상이 | catalog.jsonl 의 license 필드 참조 | 일부 cc-by-4.0, 일부 명시 안 됨 |

## 미접근 / 후속 필요

- **WikiTree** (`wikitree-dynamic-tree` repo는 SDK만): API 키 + ToS 필요
- **FamilySearch**: LDS 개발자 계정 필요
- **Geni.com**: API 키 필요
- **Burke's Peerage / Almanach de Gotha**: 유료
- **Forbes 실시간 빌리어네어**: `komed3/rtb-api` 920MB (size-skip) — 향후 sparse-checkout
- **WorldStatesmen.org**: 인도 thikana 전체 584개 — 향후 scrape
- **한국 통계청 (KOSIS)**: 성씨 본관 인구통계
- **일본 国立公文書館**: 화족 명부
