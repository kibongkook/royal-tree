#!/usr/bin/env python3
"""정적 가문 SEO 페이지 생성 — web/f/<slug>.html

SPA hash route(#family/<id>)는 구글·네이버가 색인하지 못한다. Top 가문에 대해
별도 정적 HTML stub을 만들어 검색엔진이 본문을 직접 읽도록 한다. 클라이언트가
열면 stub 안의 작은 부트 스크립트가 SPA로 전환한다.

페이지 1개당 ~3-6KB. Top 500 가문 → 약 2MB. 사이트 크롤링 가능 페이지 폭증.

대상 선정:
  • rank_global ≤ 500 가문 (자산 상위)
  • pantheon 가문 전부 (통치·자본·조용한 부·정권)
  • head_current 있는 royal 가문 추가
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
OUT_DIR = WEB / "f"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROD_BASE = "https://royal-tree.pages.dev"


def slugify(s: str, max_len: int = 64) -> str:
    """English-ish ASCII slug. Falls back to id for Han/Kana/Hangul."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:max_len] or "x"


def short_country_label(code: str) -> str:
    table = {
        "US": "미국", "GB": "영국", "FR": "프랑스", "DE": "독일", "IT": "이탈리아",
        "ES": "스페인", "NL": "네덜란드", "BE": "벨기에", "CH": "스위스", "SE": "스웨덴",
        "NO": "노르웨이", "DK": "덴마크", "FI": "핀란드", "AT": "오스트리아", "RU": "러시아",
        "PL": "폴란드", "JP": "일본", "KR": "한국", "CN": "중국", "HK": "홍콩",
        "TW": "대만", "IN": "인도", "TH": "태국", "VN": "베트남", "ID": "인도네시아",
        "PH": "필리핀", "MY": "말레이시아", "SG": "싱가포르", "SA": "사우디아라비아",
        "AE": "UAE", "QA": "카타르", "KW": "쿠웨이트", "OM": "오만", "BH": "바레인",
        "IR": "이란", "IQ": "이라크", "IL": "이스라엘", "TR": "튀르키예", "EG": "이집트",
        "MA": "모로코", "NG": "나이지리아", "ZA": "남아공", "AU": "호주", "NZ": "뉴질랜드",
        "CA": "캐나다", "BR": "브라질", "MX": "멕시코", "AR": "아르헨티나", "CL": "칠레",
        "JO": "요르단", "MC": "모나코", "LI": "리히텐슈타인", "BT": "부탄", "BN": "브루나이",
    }
    return table.get(code, code)


def cat_label_ko(cat: str | None) -> str:
    return {
        "royal": "왕가", "noble": "귀족가문", "clan": "씨족",
        "business": "기업가문", "political": "정치가문",
        "religious": "종교가문", "tribal": "부족", "unknown": "가문",
    }.get(cat or "unknown", "가문")


def pantheon_label_ko(p: str | None) -> str:
    return {
        "sovereign": "통치 殿 (Reigning Houses)",
        "capital": "자본 殿 (Houses of Capital)",
        "quiet": "조용한 부 殿 (Quiet Wealth)",
        "rule": "政權 殿 (Political Dynasties)",
    }.get(p or "", "")


def fmt_usd(v) -> str:
    if not v:
        return ""
    v = float(v)
    if v >= 1e9:
        return f"${v/1e9:.1f}B"
    if v >= 1e6:
        return f"${v/1e6:.0f}M"
    return f"${v:,.0f}"


def render_page(f: dict, detail: dict | None) -> str:
    fid = f["id"]
    name = f.get("n") or fid
    names = f.get("names") or {}
    name_en = names.get("en") or name
    name_ko = names.get("ko") or ""

    countries = f.get("c") or []
    primary_cc = next((c for c in countries if c and not c.startswith("q:")), None)
    cc_label = short_country_label(primary_cc) if primary_cc else ""

    cat = cat_label_ko(f.get("cat"))
    pn = pantheon_label_ko(f.get("pantheon"))
    rank = f.get("rank_global")
    val_s = fmt_usd(f.get("v"))
    inds = f.get("inds") or []
    biz = f.get("biz_names") or []
    ppl = f.get("ppl") or []
    headline = f.get("headline") or ""
    narrative = f.get("narrative") or ""
    head = f.get("head") or ""

    # Build title — Korean keywords first
    title_bits = [name]
    if name_ko and name_ko != name:
        title_bits.insert(0, name_ko)
    if cc_label:
        title_bits.append(cc_label)
    title_bits.append(cat)
    title = " · ".join(title_bits) + " | 로열트리"
    if rank:
        title = f"#{rank} {title}"

    desc_bits = []
    if rank:
        desc_bits.append(f"전세계 가문 영향력 #{rank}")
    if val_s:
        desc_bits.append(f"자산 {val_s}")
    if cc_label:
        desc_bits.append(cc_label)
    desc_bits.append(cat)
    if headline:
        desc_bits.append(headline)
    elif narrative:
        desc_bits.append(narrative[:120])
    desc = " · ".join(desc_bits)[:300]

    # Keywords — pack Korean-first
    kw = {name, name_ko, name_en, "로열트리", "RoyalTree", "Royal Tree",
          "가문", "가문 정보", "가문 순위", "가문 계보", "가계도", "족보",
          "명문가", "세계 명문가", cat, f"{cat} 순위", f"{cat} 정보"}
    if cc_label:
        kw.update({
            cc_label, f"{cc_label} {cat}", f"{cc_label} 부자",
            f"{cc_label} 명문가", f"{cc_label} 가문", f"{cc_label} 재벌",
            f"{cc_label} 부호",
        })
    if rank:
        if rank <= 50:
            kw.update({"세계 부자 가문", "세계 부자 순위", "글로벌 부자",
                       "글로벌 가문 순위", "세계 가문"})
        if rank <= 200:
            kw.update({"부자 순위", "세계 부호"})
        kw.add(f"세계 #{rank} 가문")
    if name:
        # 한국어 검색어 "<name> 가족", "<name> 가문" 직접 매칭
        kw.update({f"{name} 가문", f"{name} 가족", f"{name} 자산",
                   f"{name} 순위", f"{name} 회사"})
    if name_ko and name_ko != name:
        kw.update({f"{name_ko} 가문", f"{name_ko} 가족",
                   f"{name_ko} 자산", f"{name_ko} 순위"})
    if head:
        kw.update({f"{head}", f"{head} 가족", f"{head} 가문",
                   f"{head} 자산", f"{head} 부인", f"{head} 자녀"})
    if f.get("pantheon") == "sovereign":
        kw.update({"왕실", "왕가", "현존 왕가", "왕가 순위", "왕실 가계도"})
    if f.get("pantheon") == "capital":
        kw.update({"재벌", "재벌가문", "재벌 순위", "기업 가문 순위"})
    if f.get("pantheon") == "quiet":
        kw.update({"숨은 부자", "조용한 부자", "비공개 자산가"})
    if f.get("pantheon") == "rule":
        kw.update({"정치 가문", "정치 왕조", "세습 정권", "정권 가문"})
    for ind in inds[:8]:
        kw.add(ind)
    # Drop blanks/duplicates and cap length (Google ignores keywords meta but
    # other engines / on-page text matching still benefits)
    kw_str = ", ".join(k for k in kw if k)[:1000]

    canonical_url = f"{PROD_BASE}/f/{slugify(fid)}.html"

    # Body content - rich for SEO
    body_parts = []
    body_parts.append(f'<h1>{html_escape(name)}</h1>')
    if name_ko and name_ko != name:
        body_parts.append(f'<p class="ko-name">{html_escape(name_ko)}</p>')
    body_parts.append('<dl class="meta">')
    if rank:
        body_parts.append(f'<dt>전세계 가문 영향력 순위</dt><dd>#{rank}</dd>')
    if val_s:
        body_parts.append(f'<dt>가족 합산 자산</dt><dd>{val_s}</dd>')
    if cc_label:
        body_parts.append(f'<dt>국가</dt><dd>{cc_label}</dd>')
    body_parts.append(f'<dt>분류</dt><dd>{cat}</dd>')
    if pn:
        body_parts.append(f'<dt>전당</dt><dd>{html_escape(pn)}</dd>')
    if f.get("founded"):
        body_parts.append(f'<dt>설립</dt><dd>{f["founded"]}</dd>')
    if head:
        body_parts.append(f'<dt>현 가주</dt><dd>{html_escape(head)}</dd>')
    body_parts.append('</dl>')
    if headline:
        body_parts.append(f'<p class="headline">{html_escape(headline)}</p>')
    if narrative:
        body_parts.append(f'<p class="narrative">{html_escape(narrative)}</p>')

    # 자연어 한 문장 — 검색엔진 본문 일치도에 결정적 (Google·Naver)
    natural_bits = []
    if rank and cc_label:
        natural_bits.append(f"{name}은(는) {cc_label}을(를) 대표하는 {cat} 가운데 하나로, "
                            f"전세계 가문 영향력 순위 #{rank}위에 자리합니다.")
    elif cc_label:
        natural_bits.append(f"{name}은(는) {cc_label}의 {cat}입니다.")
    if val_s and cc_label:
        natural_bits.append(f"가족 합산 자산은 약 {val_s} 규모로 추정되며, "
                            f"{cc_label} 내에서도 손꼽히는 명문가로 분류됩니다.")
    if head:
        natural_bits.append(f"현재 가주는 {head}이며, 가문의 사업과 영향력을 이어가고 있습니다.")
    if pn:
        natural_bits.append(f"로열트리의 {pn} 전당에 등재된 가문입니다.")
    if natural_bits:
        body_parts.append('<section class="ko-natural">')
        for s in natural_bits:
            body_parts.append(f'<p>{html_escape(s)}</p>')
        body_parts.append('</section>')

    if biz:
        body_parts.append('<h2>주요 사업체</h2><ul class="biz">')
        for b in biz[:10]:
            body_parts.append(f'<li>{html_escape(str(b))}</li>')
        body_parts.append('</ul>')

    if ppl:
        body_parts.append('<h2>주요 인물</h2><ul class="ppl">')
        for p in ppl[:20]:
            body_parts.append(f'<li>{html_escape(str(p))}</li>')
        body_parts.append('</ul>')

    if inds:
        body_parts.append('<h2>분야</h2><ul class="inds">')
        for i in inds[:10]:
            body_parts.append(f'<li>{html_escape(str(i))}</li>')
        body_parts.append('</ul>')

    # JSON-LD
    ld = {
        "@context": "https://schema.org",
        "@type": "Organization" if (f.get("cat") in ("business", "political")) else "Person",
        "name": name,
        "alternateName": [v for v in [name_ko, name_en] if v and v != name],
        "url": canonical_url,
        "description": desc,
    }
    if cc_label:
        ld["nationality"] = cc_label
    if head and ld["@type"] == "Organization":
        ld["founder"] = head
    if f.get("founded") and ld["@type"] == "Organization":
        ld["foundingDate"] = str(f["founded"])
    breadcrumbs = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "로열트리",
             "item": PROD_BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": cat,
             "item": f"{PROD_BASE}/#cat/{f.get('cat') or 'unknown'}"},
            {"@type": "ListItem", "position": 3, "name": name,
             "item": canonical_url},
        ],
    }

    body_html = "\n      ".join(body_parts)

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{html_escape(title)}</title>
  <meta name="description" content="{html_escape(desc)}" />
  <meta name="keywords" content="{html_escape(kw_str)}" />
  <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1" />
  <link rel="canonical" href="{canonical_url}" />
  <link rel="alternate" hreflang="ko" href="{canonical_url}" />
  <link rel="alternate" hreflang="x-default" href="{canonical_url}" />

  <meta property="og:type" content="article" />
  <meta property="og:site_name" content="로열트리 · RoyalTree" />
  <meta property="og:title" content="{html_escape(title)}" />
  <meta property="og:description" content="{html_escape(desc)}" />
  <meta property="og:url" content="{canonical_url}" />
  <meta property="og:image" content="{PROD_BASE}/og-image.png" />
  <meta property="og:locale" content="ko_KR" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{html_escape(title)}" />
  <meta name="twitter:description" content="{html_escape(desc)}" />
  <meta name="twitter:image" content="{PROD_BASE}/og-image.png" />

  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
  <script type="application/ld+json">{json.dumps(breadcrumbs, ensure_ascii=False)}</script>

  <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
  <link rel="manifest" href="/site.webmanifest" />
  <link rel="stylesheet" href="/style.css?v=18" />
  <style>
    /* Lightweight stub typography; main app.js may take over */
    .stub-page {{ max-width: 760px; margin: 56px auto; padding: 0 24px; font-family: var(--kr, "Noto Serif KR", serif); line-height: 1.7; }}
    .stub-page h1 {{ font-family: var(--display, "Instrument Serif", serif); font-size: 44px; margin: 0 0 4px; }}
    .stub-page .ko-name {{ color: var(--sub, #666); margin-top: 0; }}
    .stub-page dl.meta {{ display: grid; grid-template-columns: 130px 1fr; gap: 6px 12px; margin: 24px 0; padding: 16px 20px; border: 1px solid #e7e2d6; border-radius: 8px; }}
    .stub-page dt {{ color: var(--sub, #666); font-size: 13px; }}
    .stub-page dd {{ margin: 0; font-weight: 500; }}
    .stub-page h2 {{ font-family: var(--display, "Instrument Serif", serif); font-size: 24px; margin: 36px 0 10px; }}
    .stub-page ul {{ padding-left: 22px; }}
    .stub-page .headline {{ font-style: italic; color: var(--bordeaux, #6b0a1a); font-family: var(--display, serif); font-size: 20px; }}
    .stub-back {{ display: inline-block; margin-top: 36px; color: var(--sub, #666); text-decoration: underline; }}
  </style>
</head>
<body>
  <main class="stub-page">
    <p><a href="/" class="stub-back">← 로열트리 홈</a></p>
    <article>
      {body_html}
    </article>
    <p><a href="/#cat/{f.get('cat') or 'unknown'}" class="stub-back">← {cat} 색인</a></p>
  </main>
  <script>
    // SPA enrichment: when the main app loads, route to this family's drawer.
    // The stub HTML remains crawlable by search engines.
    (function() {{
      var id = {json.dumps(fid)};
      // Show details inside the SPA when JS-enabled clients visit
      if (window.history && window.history.replaceState) {{
        // No-op: leave URL as-is so canonical stays stable
      }}
    }})();
  </script>
</body>
</html>
"""


def html_escape(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


def main():
    print("loading families.index.json…")
    d = json.load(open(WEB / "families.index.json"))
    fams = d["families"]
    by_id = {f["id"]: f for f in fams}

    detail = {}
    detail_path = WEB / "families.detail.json"
    if detail_path.exists():
        try:
            detail = json.load(open(detail_path))
        except Exception:
            detail = {}

    # Target set
    targets = []
    seen = set()

    # 1. Top 2,000 by rank_global (long-tail SEO 폭 확장)
    ranked = sorted(
        (f for f in fams if f.get("rank_global")),
        key=lambda f: f["rank_global"],
    )[:2000]
    for f in ranked:
        if f["id"] not in seen:
            targets.append(f)
            seen.add(f["id"])

    # 2. All pantheon members
    for f in fams:
        if f.get("pantheon") and f["id"] not in seen:
            targets.append(f)
            seen.add(f["id"])

    # 3. Top 100 royals (any tier_current S/A/B)
    royals = [f for f in fams
              if f.get("cat") == "royal" and f.get("tc") in ("S", "A", "B")]
    for f in royals[:100]:
        if f["id"] not in seen:
            targets.append(f)
            seen.add(f["id"])

    print(f"target pages: {len(targets):,}")

    n_written = 0
    written_slugs = []
    for f in targets:
        slug = slugify(f["id"])
        html = render_page(f, detail.get(f["id"]))
        path = OUT_DIR / f"{slug}.html"
        path.write_text(html, encoding="utf-8")
        written_slugs.append((slug, f))
        n_written += 1

    # Index file for /f/
    index_html = ["<!doctype html><html lang=\"ko\"><head>",
                  '<meta charset="utf-8"/>',
                  '<title>가문 색인 — 로열트리</title>',
                  '<meta name="description" content="로열트리의 정적 가문 색인. Top 500+ 영향력 가문 페이지 진입점." />',
                  '<link rel="canonical" href="', PROD_BASE, '/f/" />',
                  '</head><body><main style="max-width:900px;margin:48px auto;padding:0 24px;font-family:sans-serif">',
                  '<h1>가문 색인</h1>',
                  '<p>전세계 가문을 영향력 순으로 정리한 정적 색인입니다. 검색은 <a href="/">홈</a>에서.</p>',
                  '<ul>']
    for slug, f in sorted(written_slugs, key=lambda x: x[1].get("rank_global") or 99999):
        rk = f.get("rank_global") or "-"
        nm = html_escape(f.get("n") or f["id"])
        cc = (f.get("c") or [""])[0]
        index_html.append(f'<li>#{rk} · <a href="/f/{slug}.html">{nm}</a> · {cc}</li>')
    index_html.append('</ul></main></body></html>')
    (OUT_DIR / "index.html").write_text("".join(index_html), encoding="utf-8")

    print(f"wrote {n_written:,} static pages to {OUT_DIR.relative_to(ROOT)}")
    print(f"wrote {OUT_DIR.relative_to(ROOT)}/index.html")

    # ── Write extended sitemap.xml ────────────────────────────────────────
    print("\nwriting sitemap.xml (extended)…")
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    today = "2026-05-30"

    def url(loc, prio="0.5", freq="weekly"):
        sitemap.append(f'  <url><loc>{loc}</loc><lastmod>{today}</lastmod>'
                       f'<changefreq>{freq}</changefreq><priority>{prio}</priority></url>')

    url(f"{PROD_BASE}/", "1.0", "weekly")
    url(f"{PROD_BASE}/legacy.html", "0.6", "monthly")
    url(f"{PROD_BASE}/f/", "0.8", "weekly")
    # NOTE: hash URLs (#pantheon/…, #cat/…) intentionally excluded.
    # Google ignores fragments and treats them as the bare URL → would mark
    # the whole sitemap as “couldn't fetch” (가져올 수 없음). Use static /f/
    # pages + the home page as the indexable surface instead.
    # Static family pages
    for slug, f in written_slugs:
        rk = f.get("rank_global") or 9999
        # Higher priority for top ranks
        prio = "0.9" if rk <= 50 else ("0.7" if rk <= 200 else "0.5")
        url(f"{PROD_BASE}/f/{slug}.html", prio, "weekly")
    sitemap.append('</urlset>')
    (WEB / "sitemap.xml").write_text("\n".join(sitemap), encoding="utf-8")
    print(f"  sitemap entries: {len(written_slugs) + 14:,}")


if __name__ == "__main__":
    main()
