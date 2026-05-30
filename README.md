# 로열트리 · RoyalTree

> 오늘 세상을 움직이는 가문 — 통치 왕가, 자본 가문, 조용한 부, 정치 가문을 한 권의 색인으로 정리한 명문지(名門誌).

**라이브 사이트**: [royal-tree.pages.dev](https://royal-tree.pages.dev)

---

## 개요

로열트리는 전세계 가문(왕가·귀족·씨족·기업가문·정치가문·종교가문·부족)을 빠짐없이 수집하고, 가문 간 혈연·혼인·사업 연결 관계를 매핑해 현재까지의 연결고리와 사업 현황을 추적하는 데이터·웹 프로젝트입니다.

**검색 키워드**: 로열트리 · 가문 정보 · 가문 순위 · 명문가 · 재벌가문 · 세계 부자 가문 · 왕가 · 귀족가문 · 정치가문 · 부자 순위 · 한국 재벌 · 일본 황실 · 영국 왕실 · 사우디 왕가 · 가계도 · 족보

---

## 데이터 규모 (2026년 5월 현재)

| 항목 | 규모 |
|---|---:|
| 마스터 가문 | 100,108 |
| 인물 (persons) | 49,344 |
| 가문↔가문 관계 (relations) | 922 |
| 사업체 (businesses) | 3,769+ |
| 큐레이션 4 殿 (pantheon) | 70 가문 |
| 정적 SEO 페이지 (`/f/*.html`) | 547 |

---

## 4 殿 (Pantheon)

| 殿 | 내용 |
|---|---|
| **I. 통치** (Reigning Houses) | 영국 윈저, 일본 황실, 사우디 사우드, 스페인 부르봉, 스웨덴 베르나도테, 덴마크 글뤽스부르크, 네덜란드 오라녀, 요르단 하셈, 모나코·리히텐슈타인·UAE·Qatar·Bahrain·Oman·태국·부탄·모로코·쿠웨이트·브루나이 등 17가문 |
| **II. 자본** (Houses of Capital) | Walton·Bezos·Gates·Buffett·Ortega·Koch·Ellison·Zuckerberg·Page·Brin·Soros·Ambani·Li Ka-shing·Mars·Adani·Arnault(LVMH)·Trump·Vingroup·Salim·Ng(Far East)·Quek/Kwek 등 21가문 |
| **III. 조용한 부** (Quiet Wealth) | Wallenberg·Reimann·Wertheimer·Hermès·Rothschild·Cargill·Mulliez·Heineken·Kadoorie·Cheng Yu-tung·Kwok·Fok·Tata·Birla·Agnelli·Newhouse + 일본 旧宮家 4家(東久邇·賀陽·竹田·久邇) + 동남아 화교 부호 등 24가문 |
| **IV. 政權** (Political Dynasties) | Lee SG·Hun KH·Marcos PH·Duterte PH·Aquino PH·Shinawatra TH·Suharto ID·Widodo ID 등 8가문 |

---

## 주요 페이지

- **메인**: [royal-tree.pages.dev](https://royal-tree.pages.dev)
- **가문 색인 (Top 500+)**: [royal-tree.pages.dev/f/](https://royal-tree.pages.dev/f/)
- **분야별·지역별·분류별 탐색**: 메인 페이지 내비게이션

---

## 기술 스택

- 프론트엔드: Vanilla JavaScript (no framework), Instrument Serif + Inter + Noto Serif KR
- 데이터: 정적 JSON (`families.index.json`, `families.detail.json`)
- 호스팅: Cloudflare Pages (무료, 무제한 대역폭)
- 추가 도메인: `royal-tree.js.org` (PR pending), `royal-tree.eu.org` (예정)
- 데이터 파이프라인: Python 3 (Wikidata SPARQL + Wikipedia + GitHub datasets + Hugging Face + CK3 + Forbes + Bloomberg)

---

## 데이터 소스

| 우선순위 | 소스 |
|---|---|
| ★★★ | Wikidata SPARQL (QID = canonical ID) |
| ★★★ | Wikipedia categories |
| ★★ | GitHub 데이터셋 (GEDCOM, 가문 JSON) |
| ★★ | Hugging Face (royalty/nobility 데이터셋) |
| ★★ | Paradox CK3 dynasties (역대 최대 가문 DB) |
| ★ | Forbes 가족 부 / Bloomberg Billionaires |
| ★ | Burke's Peerage / Almanach de Gotha |
| ★ | Geni.com / FamilySearch / WikiTree |
| ★ | 한국 족보 (성씨별 본관·종친회) |

---

## 라이선스 · 출처

본 프로젝트는 공개된 가문 정보(Wikipedia·Wikidata·Forbes·Bloomberg 등)를 정리·색인한 것입니다. 각 가문 항목의 출처는 데이터에 함께 기록됩니다. 콘텐츠 인용 시 출처 표기를 권장합니다.

**문의 / 정정 제안**: GitHub Issues로 알려주시면 검토 후 반영합니다.
