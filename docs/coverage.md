# Coverage — Royals Phase 1 baseline

> 자동 생성 가능: `python3 scripts/normalize/split_indexes.py` 가 `data/master/_summary.json`을 갱신하면 이 문서도 같이 재생성하는 것을 권장.

## 최종 마스터 통계 (2026-05-23)

| 지표 | 값 |
|---|---:|
| **마스터 레코드 (deduped)** | **97,648** |
| 정규화 입력 (raw, 중복 포함) | 119,631 |
| Wikidata QID로 canonical 머지된 entries | 80,140 |
| QID 없는 잔여 (manual·CK3·Wikipedia) | 17,508 |
| 가상 인물 필터링 (Wikidata) | 68 |

## 카테고리

| Category | Count |
|---|---:|
| noble | 45,841 |
| unknown | 23,952 |
| royal | 16,282 |
| clan | 6,524 |
| political | 4,376 |
| business | 598 |
| religious | 39 |
| tribal | 36 |

**개선 필요 카테고리:**
- `unknown` 23,952 — 대부분 Wikipedia 크롤에서 카테고리 힌트 없이 들어온 페이지. 2차 패스에서 위키데이터 instance_of로 재분류.
- `business` 598, `religious` 39, `tribal` 36 — 절대 수치 낮음. 다음 단계 수집 우선순위.

## 국가별 — 상위 30 (ISO 3166-1 alpha-2)

| ISO | Count |
|---|---:|
| (none) | 47,738 |
| KR | 10,918 |
| JP | 6,254 |
| RU | 4,077 |
| DE | 3,695 |
| US | 2,480 |
| CH | 2,242 |
| FR | 1,825 |
| IT | 1,815 |
| SE | 1,723 |
| AT | 1,720 |
| IN | 1,021 |
| GB | 973 |
| ES | 941 |
| GR | 804 |
| CN | 699 |
| BE | 646 |
| PL | 544 |
| IE | 537 |
| NO | 454 |
| GB-SCT | 411 |
| UG | 395 |
| TR | 287 |
| IR | 285 |
| SA | 277 |
| HU | 272 |
| MA | 215 |
| FI | 205 |
| CA | 196 |
| BR | 166 |

## 핵심 갭

| 갭 | 규모 | 해결책 |
|---|---|---|
| `(none)` 47,738개 | 매우 큼 | (a) Wikidata `P495 country of origin` + `P276 location` 으로 2차 enrichment, (b) Wikipedia 페이지 본문에서 country 추출 |
| `unknown` 카테고리 23,952개 | 큼 | Wikidata `P31 instance_of` 재조회 후 매핑 확장 |
| `q:Q...` 미해석 ISO | ~수십 | `QID_TO_ISO` 테이블 확장 (현재 30개 매핑) |
| 중국 가문 | 699개 (저평가) | zh.wp `中国家族列表` + 청대 八旗 + 唐 五姓七族 깊이 확장 |
| 인도 thikana | 1,021개 (목표 562+ princely states 도달했으나 작은 thikana 누락) | worldstatesmen.org 스크레이프 |
| 사하라이남 아프리카 | UG 395 외 모두 100 이하 | List_of_current_traditional_African_leaders 본문 파싱 |
| 기업 가문 | 598 (저조) | Forbes Billionaires API + Bloomberg 가문 트래커 |

## 산출물 인덱스

```
data/master/families.jsonl       # 마스터 (97,648 lines)
data/master/_alias_map.tsv       # 원본 ID → canonical ID
data/master/_summary.json        # 통계 (이 문서의 소스)
data/by_country/<ISO>.jsonl      # 870 files
data/by_category/<cat>.jsonl     # 8 files
```
