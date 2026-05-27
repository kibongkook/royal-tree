/* Royal-Tree — 3-pantheon homepage + tree-traversal drawer.
 * Loads families.index.json (slim, all-search) up-front, families.detail.json on demand. */

const COUNTRY_NAMES = {
  KR:"대한민국", JP:"일본", CN:"중국", US:"미국", GB:"영국", DE:"독일", FR:"프랑스",
  IT:"이탈리아", ES:"스페인", RU:"러시아", IN:"인도", CH:"스위스", AT:"오스트리아",
  SE:"스웨덴", PL:"폴란드", NL:"네덜란드", BE:"벨기에", IE:"아일랜드", NO:"노르웨이",
  DK:"덴마크", FI:"핀란드", PT:"포르투갈", GR:"그리스", TR:"튀르키예", SA:"사우디아라비아",
  AE:"아랍에미리트", IL:"이스라엘", IR:"이란", EG:"이집트", ZA:"남아공", BR:"브라질",
  MX:"멕시코", AR:"아르헨티나", CL:"칠레", CO:"콜롬비아", CA:"캐나다", AU:"호주",
  NZ:"뉴질랜드", TH:"태국", VN:"베트남", MY:"말레이시아", SG:"싱가포르", ID:"인도네시아",
  PH:"필리핀", HK:"홍콩", TW:"대만", MO:"마카오", LU:"룩셈부르크", MC:"모나코",
  LI:"리히텐슈타인", VA:"교황령", BT:"부탄", BN:"브루나이", MA:"모로코", KW:"쿠웨이트",
  QA:"카타르", BH:"바레인", OM:"오만", JO:"요르단", LB:"레바논", SY:"시리아",
  IQ:"이라크", YE:"예멘", AF:"아프가니스탄", PK:"파키스탄", BD:"방글라데시", LK:"스리랑카",
  NP:"네팔", MM:"미얀마", KH:"캄보디아", LA:"라오스", MN:"몽골", KZ:"카자흐스탄",
  UZ:"우즈베키스탄", GE:"조지아", AM:"아르메니아", AZ:"아제르바이잔", DZ:"알제리",
  TN:"튀니지", LY:"리비아", SN:"세네갈", NG:"나이지리아", KE:"케냐", ET:"에티오피아",
  GH:"가나", "GB-SCT":"스코틀랜드", "GB-WLS":"웨일스", "GB-NIR":"북아일랜드",
  CZ:"체코", SK:"슬로바키아", HU:"헝가리", RO:"루마니아", BG:"불가리아", RS:"세르비아",
  HR:"크로아티아", UA:"우크라이나", BY:"벨라루스", LT:"리투아니아", LV:"라트비아",
  EE:"에스토니아", IS:"아이슬란드", MT:"몰타", CY:"키프로스",
};

const CAT_LABEL = {
  royal:"왕가", noble:"귀족", clan:"씨족", business:"기업", political:"정치", religious:"종교", tribal:"부족", unknown:"불명",
};
const STATUS_LABEL = {active:"현존", extinct:"단절", deposed:"폐위", merged:"합방", unknown:"불명"};
const PANTHEON_LABEL = {sovereign:"통치 · Reigning Houses", capital:"자본 · Houses of Capital", quiet:"조용한 부 · Quiet Wealth"};
const TIER_ORDER = ["S","A","B","C","D","X"];

const STATE = {
  index: null,
  detail: null,
  detailPromise: null,
  byCountry: new Map(),
  byId: new Map(),
  facets: new Set(),
  countryFilter: "",
  query: "",
  shown: {},
};

const $ = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));

function fmtUSD(v) {
  if (!v) return "";
  if (v >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
  return `$${v.toLocaleString()}`;
}
function altOf(f) {
  return f.names?.zh || f.names?.ja || (f.names?.ko && f.names.ko !== f.n ? f.names.ko : null) || null;
}
function countryLabel(c) {
  if (!c) return "";
  if (c.startsWith("q:")) return "";
  if (c === "AR-region") return "";
  if (COUNTRY_NAMES[c]) return COUNTRY_NAMES[c];
  if (/^[A-Z]{2}(-[A-Z]{2,4})?$/.test(c)) return c;
  return "";
}
function lifeSpan(p) {
  const b = p.birth ? String(p.birth).slice(0,4) : "?";
  const d = p.death ? String(p.death).slice(0,4) : (p.birth ? "" : "?");
  if (b === "?" && d === "") return "";
  return d ? `${b}–${d}` : `${b}–현존`;
}
function era(p) {
  const y = p.birth ? parseInt(String(p.birth).slice(0,4)) : null;
  if (!y) return "·";
  if (y < 1500) return "中世";
  if (y < 1800) return "近世";
  if (y < 1900) return "19c";
  if (y < 1945) return "20c前";
  if (y < 1980) return "20c中";
  return "現代";
}

/* ============ load ============ */

async function loadIndex() {
  const res = await fetch("families.index.json?v=5");
  STATE.index = await res.json();
  STATE.index.families.forEach(f => {
    STATE.byId.set(f.id, f);
    (f.c || []).forEach(c => {
      if (c.startsWith("q:")) return;
      if (!STATE.byCountry.has(c)) STATE.byCountry.set(c, []);
      STATE.byCountry.get(c).push(f);
    });
  });
}
async function loadDetail() {
  if (STATE.detail) return STATE.detail;
  if (STATE.detailPromise) return STATE.detailPromise;
  STATE.detailPromise = fetch("families.detail.json?v=5").then(r => r.json()).then(d => { STATE.detail = d; return d; });
  return STATE.detailPromise;
}

/* ============ pantheon rendering ============ */

function pantheonItemHTML(f) {
  const alt = altOf(f);
  const countries = (f.c || []).map(countryLabel).filter(Boolean).slice(0, 3).join(" · ");
  const cat = CAT_LABEL[f.cat] || f.cat || "";
  const status = STATUS_LABEL[f.st] || "";
  const val = f.v ? `<span class="v">${fmtUSD(f.v)}</span>` : "";
  const tierBit = f.tc ? `<span>현 ${f.tc}${f.tp && f.tp !== f.tc ? ` · 과 ${f.tp}` : ""}</span>` : "";
  const sep = `<span class="sep">·</span>`;
  const metaParts = [countries, cat + (status ? " " + status : ""), tierBit, val].filter(Boolean);
  const foundedYear = f.founded ? String(f.founded).slice(0,4) : null;
  const stamp = foundedYear
    ? `<div class="founded-stamp">est<span class="year">${foundedYear}</span></div>`
    : `<div class="founded-stamp" style="visibility:hidden">est<span class="year">—</span></div>`;

  return `
    <article class="pantheon-item" data-id="${f.id}">
      <div class="rank-col">
        <div class="rank">${String(f.pantheon_rank).padStart(2, "0")}</div>
        ${stamp}
      </div>
      <div class="body">
        <div class="name-line">
          <span class="name">${f.n}</span>
          ${alt ? `<span class="alt">${alt}</span>` : ""}
        </div>
        ${f.headline ? `<div class="headline">${f.headline}</div>` : ""}
        ${f.narrative ? `<div class="narrative">${f.narrative}</div>` : ""}
        <div class="meta">${metaParts.join(sep)}</div>
      </div>
      <div class="arrow">→</div>
    </article>
  `;
}

function renderPantheon(kind) {
  const fams = STATE.index.families
    .filter(f => f.pantheon === kind)
    .sort((a,b) => (a.pantheon_rank || 99) - (b.pantheon_rank || 99));
  const el = $("#pantheon-" + kind);
  if (!fams.length) { el.innerHTML = `<div class="empty">큐레이션 자료가 없습니다.</div>`; return; }
  el.innerHTML = fams.map(pantheonItemHTML).join("");
}

/* ============ small cards (browse + search) ============ */

function cardHTML(f) {
  const alt = altOf(f);
  const countries = (f.c || []).map(countryLabel).filter(Boolean).slice(0, 2).join(" · ");
  const cat = CAT_LABEL[f.cat] || f.cat || "";
  const val = f.v ? `<span class="v">${fmtUSD(f.v)}</span>` : "";
  const tierBit = f.tc ? `<span>현 ${f.tc}</span>` : "";
  const inds = (f.inds || []).slice(0, 3);

  return `
    <article class="card" data-id="${f.id}">
      <h3 class="card-name">${f.n}</h3>
      ${alt ? `<div class="card-alt">${alt}</div>` : ""}
      <div class="card-sub">
        ${countries ? `<span>${countries}</span>` : ""}
        ${cat ? `<span>${cat}</span>` : ""}
        ${tierBit}
        ${val}
      </div>
      ${f.head ? `<div class="card-head-name">현 가주 — ${f.head}</div>` : ""}
      ${inds.length ? `<div class="card-inds">${inds.map(i => `<span>${i}</span>`).join("")}</div>` : ""}
    </article>
  `;
}

function renderCards(container, families, limit) {
  if (!families.length) {
    container.innerHTML = `<div class="empty" style="grid-column:1/-1">해당하는 가문이 없습니다.</div>`;
    return;
  }
  container.innerHTML = families.slice(0, limit).map(cardHTML).join("");
}

/* ============ tiers ============ */

function renderTiers() {
  const fams = STATE.index.families;
  ["S","A","B"].forEach(t => {
    const list = fams.filter(f => (f.tc || "X") === t)
      .sort((a,b) => (b.v || 0) - (a.v || 0));
    const containerId = `tier-${t}`;
    const limit = STATE.shown[containerId] || 12;
    STATE.shown[containerId] = limit;
    renderCards($("#" + containerId), list, limit);
    const lbl = $(`#tier-${t}-count`);
    if (lbl) lbl.textContent = `· ${list.length.toLocaleString()}가문`;
    const btn = $(`button[data-more="${t}"]`);
    if (btn) {
      if (limit >= list.length) {
        btn.disabled = true;
        btn.textContent = `모두 표시됨 (${list.length})`;
      } else {
        btn.disabled = false;
        btn.textContent = `→ 다음 ${Math.min(12, list.length - limit)}가문 (총 ${list.length})`;
      }
    }
  });
}

/* ============ country picker ============ */

function renderCountryChips() {
  const sorted = [...STATE.byCountry.entries()].sort((a,b) => b[1].length - a[1].length);
  const top = sorted.slice(0, 24);
  $("#country-chips").innerHTML = top.map(([c, list]) =>
    `<button class="country-chip" data-c="${c}">${countryLabel(c)}<span class="count">${list.length}</span></button>`
  ).join("");
  $$("#country-chips .country-chip").forEach(el => {
    el.addEventListener("click", () => {
      const c = el.dataset.c;
      const active = el.classList.contains("active");
      $$("#country-chips .country-chip").forEach(x => x.classList.remove("active"));
      const section = $("#country-section");
      if (active) { section.innerHTML = ""; STATE.shown.country = 0; return; }
      el.classList.add("active");
      STATE.shown.country = 12;
      renderCountrySection(c);
    });
  });

  const sel = $("#country-filter");
  sel.innerHTML = `<option value="">전체 국가</option>` + sorted.map(([c, list]) =>
    `<option value="${c}">${countryLabel(c)} (${list.length})</option>`).join("");
}

function renderCountrySection(c) {
  const fams = (STATE.byCountry.get(c) || []).slice().sort((a,b) =>
    TIER_ORDER.indexOf(a.tc || "X") - TIER_ORDER.indexOf(b.tc || "X")
    || (b.v || 0) - (a.v || 0));
  const limit = STATE.shown.country || 12;
  const section = $("#country-section");
  section.innerHTML = `
    <div class="tier-block">
      <div class="tier-label">${countryLabel(c)} <em>· ${fams.length}가문</em></div>
      <div class="cards" id="country-grid"></div>
      <div class="more-row"><button class="more-btn" id="country-more">→ 다음 12가문</button></div>
    </div>
  `;
  renderCards($("#country-grid"), fams, limit);
  const btn = $("#country-more");
  if (limit >= fams.length) {
    btn.disabled = true; btn.textContent = `모두 표시됨 (${fams.length})`;
  } else {
    btn.textContent = `→ 다음 ${Math.min(12, fams.length - limit)}가문 (총 ${fams.length})`;
  }
  btn.addEventListener("click", () => {
    STATE.shown.country = (STATE.shown.country || 12) + 12;
    renderCountrySection(c);
  });
  section.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ============ search ============ */

function searchOne(f, q) {
  if (!q) return true;
  const tokens = q.toLowerCase().split(/\s+/).filter(Boolean);
  const hay = (
    (f.n || "") + " | " + Object.values(f.names || {}).join(" | ") + " | " +
    (f.head || "") + " | " + (f.headline || "") + " | " + (f.narrative || "") + " | " +
    (f.inds || []).join(" | ") + " | " + (f.biz_names || []).join(" | ") + " | " +
    (f.rel || []).join(" | ") + " | " + (f.ppl || []).join(" | ") + " | " +
    (f.c || []).map(c => `${c} ${countryLabel(c)}`).join(" | ") + " | " +
    (f.cat || "") + " " + (CAT_LABEL[f.cat] || "") + " | " +
    (f.st || "") + " " + (STATUS_LABEL[f.st] || "") + " | " +
    (f.pol || "") + " | " + (f.pantheon || "")
  ).toLowerCase();
  return tokens.every(t => hay.includes(t));
}

const MONEY_RANGES = {
  "1-10b":   [1e9,  1e10],
  "10-50b":  [1e10, 5e10],
  "50-100b": [5e10, 1e11],
  "100b+":   [1e11, Infinity],
};

function applyFacets(f) {
  for (const fac of STATE.facets) {
    const [k, v] = fac.split(":");
    if (k === "money") {
      const r = MONEY_RANGES[v];
      if (!r) continue;
      if (!(f.v && f.v >= r[0] && f.v < r[1])) return false;
    } else if (k === "cat") {
      if (f.cat !== v) return false;
    } else if (k === "status") {
      if (f.st !== v) return false;
    } else if (k === "pantheon") {
      if (f.pantheon !== v) return false;
    }
  }
  return true;
}

function runSearch() {
  const q = STATE.query.trim();
  const country = STATE.countryFilter;
  const hasFilter = q || country || STATE.facets.size;
  const browse = [$("#sovereign"), $("#capital"), $("#quiet"), $("#browse")];
  const results = $("#results");

  if (!hasFilter) {
    browse.forEach(s => s && (s.hidden = false));
    results.hidden = true;
    $("#searchmeta").textContent = "";
    return;
  }
  browse.forEach(s => s && (s.hidden = true));
  results.hidden = false;

  let list = STATE.index.families;
  if (country) list = list.filter(f => (f.c || []).includes(country));
  if (q) list = list.filter(f => searchOne(f, q));
  list = list.filter(applyFacets);
  list = list.slice().sort((a,b) =>
    TIER_ORDER.indexOf(a.tc || "X") - TIER_ORDER.indexOf(b.tc || "X")
    || (b.v || 0) - (a.v || 0));

  STATE.results = list;
  STATE.shown.results = 24;
  const bits = [];
  if (q) bits.push(`“${q}”`);
  if (country) bits.push(countryLabel(country));
  if (STATE.facets.size) bits.push([...STATE.facets].join(" · "));
  $("#results-title").textContent = bits.join(" / ") || "검색 결과";
  $("#searchmeta").textContent = `${list.length.toLocaleString()}가문 발견`;
  renderResults();
  // scroll into view if user has scrolled past the search bar
  setTimeout(() => results.scrollIntoView({behavior:"smooth", block:"start"}), 50);
}

function renderResults() {
  const list = STATE.results || [];
  renderCards($("#results-grid"), list, STATE.shown.results);
  const btn = $("#more-results");
  if (STATE.shown.results >= list.length) {
    btn.disabled = true;
    btn.textContent = list.length ? `모두 표시됨 (${list.length})` : "결과 없음";
  } else {
    btn.disabled = false;
    btn.textContent = `→ 다음 ${Math.min(24, list.length - STATE.shown.results)}가문 (총 ${list.length})`;
  }
}

/* ============ drawer — tree traversal ============ */

async function openDetail(id) {
  const drawer = $("#drawer");
  const content = $("#drawer-content");
  drawer.hidden = false;
  drawer.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";

  const idxF = STATE.byId.get(id);
  if (!idxF) { content.innerHTML = `<div class="empty">자료를 찾지 못했습니다.</div>`; return; }
  content.innerHTML = `<div class="empty">族譜를 펴는 중…</div>`;
  drawer.querySelector(".drawer-panel").scrollTop = 0;

  const detail = await loadDetail();
  const d = detail[id] || {};
  content.innerHTML = renderDetail(idxF, d);
  drawer.querySelector(".drawer-panel").scrollTop = 0;
  wireTraverse();
}

function wireTraverse() {
  $$('#drawer-content [data-jump]').forEach(el => {
    el.addEventListener("click", e => {
      e.preventDefault();
      const id = el.dataset.jump;
      if (STATE.byId.has(id)) openDetail(id);
    });
  });
}

function traverseCard({type, target, summary, id, active, year}) {
  const known = id && STATE.byId.has(id);
  const cls = known ? "traverse-card" : "traverse-card muted";
  const attr = known ? `data-jump="${id}"` : "";
  const yearBit = year ? `· ${year}년경` : "";
  const activeBit = active ? `<span class="active-pill">활성</span>` : "";
  return `
    <a href="#" class="${cls}" ${attr}>
      <div class="body">
        <div class="type-tag">${type}${yearBit ? " " + yearBit : ""}</div>
        <div class="target">${target} ${activeBit}</div>
        ${summary ? `<div class="summary">${summary}</div>` : ""}
      </div>
      <div class="arrow">→</div>
    </a>
  `;
}

function renderDetail(f, d) {
  const alt = altOf(f);
  const head = d.head_card || {};
  const biz = head.business || {};
  const pantheonLabel = f.pantheon ? PANTHEON_LABEL[f.pantheon] : (CAT_LABEL[f.cat] + (f.st && f.st !== "active" ? ` · ${STATUS_LABEL[f.st]}` : ""));
  const countries = (f.c || []).map(countryLabel).filter(Boolean).join(" · ");
  const valuation = biz.total_valuation_usd ? `<span class="v">${fmtUSD(biz.total_valuation_usd)}</span>` : "";

  const tierLine = f.tc ? `<span>현 ${f.tc}${f.tp && f.tp !== f.tc ? " · 과 " + f.tp : ""}</span>` : "";
  const founded = f.founded ? `<span>창건 ${String(f.founded).slice(0,4)}</span>` : "";
  const extinct = f.extinct ? `<span>단절 ${String(f.extinct).slice(0,4)}</span>` : "";

  // ---------- Head card ----------
  let headSec = "";
  if (head.name) {
    const titles = (head.titles || []).join(" · ");
    headSec = `
      <div class="head-card">
        <div class="head-card-name">${head.name}</div>
        ${titles ? `<div class="head-card-titles">${titles}</div>` : ""}
        ${head.birth || head.death ? `<div class="head-card-row"><span class="label">생몰</span>${head.birth || "?"}${head.death ? ` – ${head.death}` : " – 현존"}</div>` : ""}
        ${head.spouses?.length ? `<div class="head-card-row"><span class="label">배우자</span>${head.spouses.join(", ")}</div>` : ""}
        ${head.children?.length ? `<div class="head-card-row"><span class="label">자녀</span>${head.children.join(", ")}</div>` : ""}
        ${head.country?.length ? `<div class="head-card-row"><span class="label">활동국</span>${head.country.map(countryLabel).filter(Boolean).join(", ")}</div>` : ""}
      </div>
    `;
  } else if (head.note) {
    headSec = `<div class="head-card"><div class="head-card-row" style="font-style:italic">${head.note}</div></div>`;
  }

  // ---------- Business ----------
  let bizSec = "";
  if (biz.top && biz.top.length) {
    bizSec = biz.top.map(b => `
      <div class="biz-row">
        <div>
          <div class="biz-name">${b.name || b.industry || "(이름 미상)"}</div>
          <div class="biz-meta">
            ${b.industry ? `<span>${b.industry}</span>` : ""}
            ${b.country_hq?.length ? ` · <span>${b.country_hq.map(countryLabel).filter(Boolean).join(", ")}</span>` : ""}
            ${b.control_type ? ` · <span>${b.control_type}</span>` : ""}
          </div>
        </div>
        ${b.valuation_usd ? `<div class="biz-val">${fmtUSD(b.valuation_usd)}</div>` : ""}
      </div>
    `).join("");
    if (biz.industries?.length) {
      bizSec += `<div class="industries-row">${biz.industries.map(i => `<span>${i}</span>`).join("")}</div>`;
    }
  }

  // ---------- People (origin / recent) ----------
  function personItem(p) {
    return `
      <div class="person-row">
        <div class="person-era">${era(p)}</div>
        <div>
          <div class="person-name">${p.name || "(이름 미상)"} <span class="person-life">${lifeSpan(p)}</span></div>
          ${p.titles?.length ? `<div class="person-titles">${p.titles.join(" · ")}</div>` : ""}
          ${p.spouses?.length ? `<div class="person-link-row"><span class="label">배우자</span>${p.spouses.join(", ")}</div>` : ""}
          ${p.children?.length ? `<div class="person-link-row"><span class="label">자녀</span>${p.children.join(", ")}</div>` : ""}
        </div>
      </div>
    `;
  }
  const origin = (d.origin || []).filter(Boolean);
  const recent = (d.recent || []).filter(Boolean);
  let personSec = "";
  if (origin.length) {
    personSec += `<div style="margin-bottom:10px"><div class="head-card-row" style="font-family:var(--caps);font-size:9px;letter-spacing:.25em;text-transform:uppercase;color:var(--gold)">시조 · Origin</div></div>`;
    personSec += origin.map(personItem).join("");
  }
  if (d.middle_summary) {
    personSec += `<div style="padding:14px 0;font-family:var(--serif-display);font-style:italic;color:var(--ink-soft);font-size:14px;border-bottom:1px solid var(--rule-soft)">중간 세대 — ${d.middle_summary}</div>`;
  }
  if (recent.length) {
    personSec += `<div style="margin-top:18px;margin-bottom:10px"><div class="head-card-row" style="font-family:var(--caps);font-size:9px;letter-spacing:.25em;text-transform:uppercase;color:var(--gold)">최근 세대 · Recent</div></div>`;
    personSec += recent.map(personItem).join("");
  }

  // ---------- Tree traversal: spouses, relations ----------
  let spouseSec = "";
  if (d.spouses_lineage?.length) {
    spouseSec = d.spouses_lineage.map(s => {
      // try to find matching family id by name fuzzy match
      const guessId = findFamilyByName(s.family_name || s.family_of_origin || s.name);
      return traverseCard({
        type: "혼인 · 본가",
        target: s.family_name || s.family_of_origin || s.name,
        summary: `${s.name ? "<strong>" + s.name + "</strong> — " : ""}${s.summary || ""}`,
        id: guessId,
      });
    }).join("");
  }

  let relSec = "";
  if (d.relations?.length) {
    relSec = d.relations.map(r => traverseCard({
      type: `${r.type === "marriage" ? "혼인" : r.type === "blood" ? "혈연" : r.type === "succession" ? "계승" : r.type === "business" ? "사업" : r.type}${r.subtype ? "·" + r.subtype : ""}`,
      target: r.with || r.with_id,
      summary: r.summary,
      id: r.with_id,
      active: r.active,
      year: r.year,
    })).join("");
  }

  // ---------- Tier reasons ----------
  let tierSec = "";
  if (d.tier_reasons_current?.length || d.tier_reasons_past?.length) {
    const partsCur = (d.tier_reasons_current || []).map(r => `<li>${r}</li>`).join("");
    const partsPast = (d.tier_reasons_past || []).map(r => `<li>${r}</li>`).join("");
    tierSec = `
      ${partsCur ? `<div class="head-card-row"><span class="label">현 ${f.tc || "·"} 사유</span><ul style="margin:6px 0 14px 0;padding-left:18px;line-height:1.6">${partsCur}</ul></div>` : ""}
      ${partsPast ? `<div class="head-card-row"><span class="label">과 ${f.tp || "·"} 사유</span><ul style="margin:6px 0 0 0;padding-left:18px;line-height:1.6">${partsPast}</ul></div>` : ""}
    `;
  }

  // ---------- Compose ----------
  return `
    <div class="detail-head">
      <div class="detail-pantheon">${pantheonLabel}</div>
      ${alt ? `<div class="detail-alt">${alt}</div>` : ""}
      <div class="detail-name">${f.n}</div>
      ${f.headline ? `<div class="detail-headline">${f.headline}</div>` : ""}
      <div class="detail-meta">
        ${tierLine}
        ${countries ? `<span>${countries}</span>` : ""}
        ${founded}${extinct}
        ${valuation ? `· ${valuation}` : ""}
      </div>
      ${f.peak_era ? `<div class="detail-meta" style="margin-top:10px"><span style="text-transform:none;letter-spacing:0;font-family:var(--serif);font-style:italic;color:var(--accent);font-size:14px">절정기 — ${f.peak_era}</span></div>` : ""}
      ${f.narrative ? `<div class="detail-narrative">${f.narrative}</div>` : ""}
    </div>

    ${headSec ? `<div class="detail-section"><h3>지금의 가주</h3>${headSec}</div>` : ""}

    ${bizSec ? `<div class="detail-section"><h3>사업체 <span class="count">${biz.count || biz.top?.length || ""}</span></h3>${bizSec}</div>` : ""}

    ${spouseSec ? `<div class="detail-section"><h3>혼인으로 이어진 가문 — 부인 본가</h3>${spouseSec}</div>` : ""}

    ${relSec ? `<div class="detail-section"><h3>가문 간 관계 — 혈연 · 혼인 · 사업</h3>${relSec}</div>` : ""}

    ${personSec ? `<div class="detail-section"><h3>혈맥 — 시조에서 현 세대까지</h3>${personSec}</div>` : ""}

    ${tierSec ? `<div class="detail-section"><h3>위계 사유</h3>${tierSec}</div>` : ""}

    ${d.notes ? `<div class="detail-section"><h3>비고</h3><div style="font-family:var(--serif-kr);font-weight:300;color:var(--ink-2);line-height:1.75">${d.notes}</div></div>` : ""}

    ${d.sources?.length ? `<div class="detail-foot">출처 — ${d.sources.map(s => `<code>${s}</code>`).join(" · ")}</div>` : ""}
  `;
}

// Fuzzy lookup: try to map a free-form spouse family name to a known family id
function findFamilyByName(name) {
  if (!name) return null;
  const n = name.toLowerCase();
  // exact name match
  for (const f of STATE.index.families) {
    if ((f.n || "").toLowerCase() === n) return f.id;
  }
  // contains match — pick the shortest match
  let best = null;
  let bestLen = Infinity;
  for (const f of STATE.index.families) {
    const allNames = [f.n, ...(Object.values(f.names || {}))].filter(Boolean).map(x => x.toLowerCase());
    for (const an of allNames) {
      if (n.includes(an) || an.includes(n)) {
        if (an.length < bestLen) { best = f.id; bestLen = an.length; }
      }
    }
  }
  return best;
}

function closeDetail() {
  const drawer = $("#drawer");
  drawer.hidden = true;
  drawer.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
}

/* ============ events ============ */

function wireEvents() {
  document.body.addEventListener("click", e => {
    const item = e.target.closest("[data-id]");
    if (item) openDetail(item.dataset.id);
    if (e.target.dataset && e.target.dataset.close !== undefined) closeDetail();
  });
  document.addEventListener("keydown", e => { if (e.key === "Escape") closeDetail(); });

  const debounce = (fn, ms) => {
    let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
  };
  const onSearch = debounce(() => { STATE.query = $("#q").value; runSearch(); }, 130);
  $("#q").addEventListener("input", onSearch);
  $("#clearq").addEventListener("click", () => { $("#q").value = ""; STATE.query = ""; runSearch(); });
  $("#country-filter").addEventListener("change", e => { STATE.countryFilter = e.target.value; runSearch(); });

  $$(".facet").forEach(b => {
    b.addEventListener("click", () => {
      const k = b.dataset.facet;
      const kind = k.split(":")[0];
      if (["cat","status","money","pantheon"].includes(kind)) {
        [...STATE.facets].forEach(x => {
          if (x.startsWith(kind + ":")) {
            STATE.facets.delete(x);
            $$(`.facet[data-facet="${x}"]`).forEach(el => el.classList.remove("active"));
          }
        });
      }
      if (STATE.facets.has(k)) {
        STATE.facets.delete(k); b.classList.remove("active");
      } else {
        STATE.facets.add(k); b.classList.add("active");
      }
      runSearch();
    });
  });

  $$('button[data-more]').forEach(b => {
    b.addEventListener("click", () => {
      const t = b.dataset.more;
      const key = `tier-${t}`;
      STATE.shown[key] = (STATE.shown[key] || 12) + 12;
      renderTiers();
    });
  });
  $("#more-results").addEventListener("click", () => {
    STATE.shown.results = (STATE.shown.results || 24) + 24;
    renderResults();
  });
}

/* ============ boot ============ */

function showSkeletons() {
  ["pantheon-sovereign","pantheon-capital","pantheon-quiet"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = Array.from({ length: 4 }, () => `
      <div class="skeleton-row">
        <div class="skeleton-rank"></div>
        <div>
          <div class="skeleton-line long"></div>
          <div class="skeleton-line short"></div>
        </div>
      </div>`).join("");
  });
}

async function boot() {
  showSkeletons();
  await loadIndex();
  $("#exported-count").textContent = STATE.index.exported.toLocaleString();
  renderPantheon("sovereign");
  renderPantheon("capital");
  renderPantheon("quiet");
  renderCountryChips();
  renderTiers();
  wireEvents();
}

boot().catch(err => {
  console.error(err);
  $("#pantheon-sovereign").innerHTML = `<div class="empty">자료를 불러오지 못했습니다.</div>`;
});
