# Coverage — Royals Phase 1 + 1.5 + 2 + 3 + 4

> 자동 생성 가능: `python3 scripts/normalize/split_indexes.py` 가 `data/master/_summary.json`을 갱신.

## Phase 2/3/4 — 인물·관계·사업 그래프 (2026-05-23 신규)

| Phase | 산출물 | 규모 |
|---|---|---:|
| **Phase 2** | `data/master/persons.jsonl` | 8,291 persons / 327 families |
| **Phase 2** | family.head_current 자동 채움 | 53 |
| **Phase 3** | `data/master/relations.jsonl` | 447 edges / 181 families |
| **Phase 3** | marriage 174 · blood 142 · succession 131 | — |
| **Phase 4** | `data/master/businesses.jsonl` | 1,071 records / 338 families |
| **Phase 4** | manual canonical + Forbes/Bloomberg matches | 50 + 1,021 |

## Phase 2/3/4 빌더

```bash
python3 scripts/normalize/build_persons.py       # persons.jsonl
python3 scripts/normalize/build_relations.py     # relations.jsonl + _relations_graph.json
python3 scripts/normalize/build_businesses.py    # businesses.jsonl + families.jsonl update
python3 scripts/normalize/filter_non_families.py # (no-op until raw.instance_of contamination)
python3 scripts/normalize/split_indexes.py       # regen by_country/by_category
```

Phase 2-4는 모두 banked raw files + manual curation만 사용. Wikidata API 호출 없는 데이터 변환 단계. 후속 enrichment(yale wikidata-people 225k, willpowers parent-child, Wikidata P26/P53 traversal)는 Phase 2b/3b/4b로 분리.

---


## 최종 마스터 통계 (2026-05-23)

| 지표 | Phase 1 baseline | Phase 1.5 최종 |
|---|---:|---:|
| **마스터 레코드 (deduped)** | 97,648 | **98,835** |
| 정규화 입력 (raw, 중복 포함) | 119,631 | 121,113 |
| Wikidata QID로 canonical 머지된 entries | 80,140 | ~80,500 |
| 가상 인물 필터링 (Wikidata) | 68 | 68 |
| 국가 없음 (`(none)`) | 47,738 | **39,231** (-8,507) |

## 카테고리 (Phase 1 → 1.5)

| Category | Phase 1 | Phase 1.5 | Δ |
|---|---:|---:|---:|
| noble | 45,841 | 46,170 | +329 |
| unknown | 23,952 | 23,853 | -99 |
| royal | 16,282 | **16,893** | +611 |
| clan | 6,524 | 6,524 | 0 |
| political | 4,376 | 4,376 | 0 |
| business | 598 | **945** | +347 |
| religious | 39 | 38 | -1 |
| tribal | 36 | 36 | 0 |

## 국가별 — 상위 30 (Phase 1.5)

| ISO | Phase 1 | Phase 1.5 | Δ |
|---|---:|---:|---:|
| (none) | 47,738 | 39,231 | **-8,507** |
| KR | 10,918 | 10,930 | +12 |
| JP | 6,254 | 6,990 | +736 |
| DE | 3,695 | **4,979** | +1,284 |
| RU | 4,077 | 4,184 | +107 |
| FR | 1,825 | **3,391** | +1,566 |
| IT | 1,815 | **2,911** | +1,096 |
| US | 2,480 | 2,847 | +367 |
| CH | 2,242 | 2,297 | +55 |
| GB | 973 | **2,145** | +1,172 |
| IN | 1,021 | **1,901** | +880 |
| SE | 1,723 | 1,829 | +106 |
| AT | 1,720 | 1,787 | +67 |
| CN | 699 | **1,236** | +537 |
| ES | 941 | 1,174 | +233 |
| GR | 804 | 826 | +22 |
| BE | 646 | 775 | +129 |
| IE | 537 | 693 | +156 |
| PL | 544 | 595 | +51 |
| NO | 454 | 482 | +28 |
| GB-SCT | 411 | 411 | 0 |
| UG | 395 | 398 | +3 |
| TR | 287 | 378 | +91 |
| IR | 285 | 372 | +87 |
| SA | 277 | 360 | +83 |
| HU | 272 | 290 | +18 |
| NL | — | 272 | — |
| MA | 215 | 249 | +34 |
| DK | — | 245 | — |
| CA | 196 | 245 | +49 |

## Phase 1.5 변경 요약

| 작업 | 결과 |
|---|---|
| **royal92 + royalconstellations 통합** | +282 families, 17 QID 자동 cross-link (Windsor→Q81589, Romanov→Q112707, Hohenzollern→Q83969 등) |
| **Islamic Atlas + ctm_bench 통합** | 186 이슬람 왕조 + 10 중국 왕조, 26 QID merges (Umayyad→Q45646, Abbasid→Q4437641, Almoravid→Q132922 등) |
| **Wikidata country enrichment** | 44,256 QID 쿼리 → 8,596 country 획득 (19.4%). P27 5,241 · P19 1,656 · P17 1,592 · P495 359 · P276 211 · P131 46 |
| **CN/IN 갭 fill** | CN 510 entries (五代十国 10, 五胡十六国 20, Zhou 30, 八旗 37, 唐 51, 본관 52, A-share 220 등). IN 558 entries (worldstatesmen 123 + Rajasthan 140 + Saurashtra 97 + MP/Bundelkhand 57 + 비즈니스 141) |

## 핵심 갭 (Phase 2 이후)

| 갭 | 규모 | 해결책 |
|---|---|---|
| `(none)` 39,231개 | 큼 | SPARQL traversal `wdt:P53 family ▶ wdt:P17`; Wikipedia 본문 추출 |
| `unknown` 카테고리 23,853개 | 큼 | Wikidata `P31 instance_of` 재조회 매핑 확장 |
| Phase 2 인물 그래프 | 7,461 banked + 225k yale-cultural-heritage/wikidata-people 미통합 | 별도 person graph 빌드 단계 |
| Phase 3 친족 관계 | 4,601 banked + willpowers/celebrity-parent | 별도 relation graph |
| Phase 4 사업 매핑 | 945 business families만; Forbes 실시간 미연동 | komed3/rtb-api sparse-checkout |

## 산출물 인덱스

```
data/master/families.jsonl       # 마스터 98,835 lines
data/master/_alias_map.tsv       # 원본 ID → canonical ID
data/master/_summary.json        # 통계 (이 문서의 소스)
data/master/_country_enrichment.jsonl  # 44,256 audit rows
data/by_country/<ISO>.jsonl      # 881 files
data/by_category/<cat>.jsonl     # 8 files
data/raw/github/_*_individuals.jsonl   # Phase 2 banks (7,461 people)
data/raw/github/_*_relations.jsonl     # Phase 3 banks (4,601 edges)
```
