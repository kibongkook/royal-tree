# Royal-Tree · Web (國際家門誌)

전세계 9,840 가문(전체 100,108 중 정보가 풍부한 우선 노출분)의 럭셔리 클래식 디자인 웹 인터페이스.

## 띄우기

```bash
cd web
python3 -m http.server 8765
# 브라우저로 http://localhost:8765/
```

## 데이터 재생성

가문 마스터 데이터(`data/master/families.jsonl`, `relations.jsonl`)가 갱신되면:

```bash
python3 scripts/web/export_web_data.py
# → web/families.index.json (≈3 MB, 검색용 lightweight)
# → web/families.detail.json (≈9 MB, 드로어 lazy-load)
```

## 구성

| 파일 | 역할 |
|---|---|
| `index.html` | 마스트헤드·검색바·중국 스포트라이트·국가·위계·서지 섹션 |
| `style.css` | 양피지 크림+클라렛+골드 팔레트, Cinzel/Garamond/Noto Serif KR 타이포 |
| `app.js` | 데이터 로드, 카드 렌더, 검색·패싯, 드로어, 점진 로드("추가로 보기") |
| `families.index.json` | 9,840 가문 검색 인덱스 |
| `families.detail.json` | 가주·사업·인물·관계·혼인 상세 페이로드 (필요 시 로드) |

## 검색 차원

- 가문 이름 (ko/zh/ja/en 다국어)
- 인물 이름 (현 가주·관계 인물)
- 사업체·산업 (`Tencent`, `반도체`, `e-commerce` 등)
- 국가 (코드 또는 한글)
- 카테고리 (왕가·귀족·기업·씨족·정치·종교)
- 자산 임계 (≥$1B / $10B / $50B)
- 위계 (S/A/B)
- 상태 (현존·폐위·단절)
- 부상(rising) — 과거보다 현재 위계가 높은 가문
- 관계 활성 — 가문 간 다리 인물이 존재
