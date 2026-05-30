# Royal-Tree 사이트 QA 리스트

**Audit 일자**: 2026-05-30
**검사 범위**: `web/index.html`, `web/app.js`, `web/style.css`, `data/master/_web_overlay.json`, `web/legacy.*`

상태: H = High (즉시 fix), M = Medium, L = Low (검토)

## 1. 언어 일관성 — 한글이 메인, 한자 제거

| ID | 위치 | 문제 | 우선순위 |
|---|---|---|---|
| L-01 | [web/index.html:123](web/index.html#L123) | `政權` 헤딩 → "정권" | H |
| L-02 | [web/index.html:193](web/index.html#L193) | `9,840家` → "9,840가문" | H |
| L-03 | [web/index.html:210](web/index.html#L210) | footer `名門誌` → "명문지" | H |
| L-04 | [web/app.js:274](web/app.js#L274) | sector chip: `政權` → "정권" | H |
| L-05 | [web/app.js:439-444](web/app.js#L439-L444) | era 라벨 `中世/近世/現代` → "중세/근세/현대" | H |
| L-06 | [web/app.js:560-1090](web/app.js#L560) | path-count/region-count "家" → "가문" (8곳) | H |
| L-07 | [web/app.js:661](web/app.js#L661) | search empty hint `삼성 · 霍` → "삼성 · 록펠러" 등 한글 가문 | H |
| L-08 | [web/app.js:949](web/app.js#L949) | browseTitle `政權` → "정권" | H |
| L-09 | [web/legacy.html, legacy-app.js](web/legacy.html) | 동일 패턴 한자 다수 | M |
| L-10 | [data/master/_web_overlay.json](data/master/_web_overlay.json) | narrative 내 `美/帝國/中/兄弟/超人/故鄕/代` 등 | M |
| L-11 | "Anno MMXXVI" / "Nomen est omen" 라틴어 | 디자인 의도지만 한글 사용자에겐 노이즈 — 검토 | L |

## 2. 키보드 단축키 / 운영체제 감지

| ID | 문제 | 우선순위 |
|---|---|---|
| K-01 | [web/index.html:27](web/index.html#L27) `<kbd>⌘ K</kbd>` 하드코딩 — Mac만. Windows/Linux 사용자에겐 무의미, 모바일에는 표시 자체가 노이즈 | H |

**fix**: `navigator.platform` 감지해 `⌘ K`(Mac) / `Ctrl K`(Win·Linux) 자동 변환. 모바일(touch)은 hide.

## 3. 캐시 버스팅 일관성

| ID | 문제 | 우선순위 |
|---|---|---|
| C-01 | `legacy.html` style/script `?v=5`로 정지, `index.html`은 `?v=16` | M |

## 4. SEO / 소셜 카드

| ID | 문제 | 우선순위 |
|---|---|---|
| S-01 | `og:image`, `og:title`, `og:description`, `twitter:card` meta 없음 — SNS 공유 시 카드 안 뜸 | M |
| S-02 | `<link rel="canonical">` 없음 | L |

## 5. 데이터 / 정확성

| ID | 문제 | 우선순위 |
|---|---|---|
| D-01 | 일부 가문이 cap=$400B에 걸려 실제 자산보다 부풀려짐 (forbes-2019 noise) | M (Phase 7c 일부 정정됨, 추가 정제 필요) |
| D-02 | head_current가 "Charles III" 같은 문자열인 경우 fallback 적용됨 | L |
| D-03 | spouses_lineage가 117가문만 채워짐 (전체 8,557 중) | L (Phase 6에서 23배 개선됨, 추가 fetch 필요 시 진행) |

## 6. 성능

| ID | 문제 | 우선순위 |
|---|---|---|
| P-01 | `families.detail.json` 9.1MB — 첫 가문 클릭 시 lazy load (이미 분리). 현재 합리적 | OK |
| P-02 | `families.index.json` 4.9MB — 홈 진입 시 즉시 fetch. gzip으로 ~1.2MB | OK |

## 7. 접근성

| ID | 문제 | 우선순위 |
|---|---|---|
| A-01 | hero crest SVG에 aria-hidden="true" 있음 ✓ | OK |
| A-02 | aria-label 5개, alt 0개 (img 없음). 적정 | OK |
| A-03 | 키보드 focus 흐름 점검 (Tab 순서) | L |

## 8. legacy 파일 / 정리

| ID | 문제 | 우선순위 |
|---|---|---|
| O-01 | `web/legacy.html` + `legacy-app.js` + `legacy-style.css` 70KB+ 옛 UI. main에서 "전체" 링크로 연결. 유지 결정 시 캐시 버스팅 동기화 | M |

## 9. README / 문서

| ID | 문제 | 우선순위 |
|---|---|---|
| R-01 | `web/README.md`에 옛 도메인 정보 — `royal-tree.pages.dev` 안내로 업데이트 | L |
