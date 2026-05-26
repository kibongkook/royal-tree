/* RoyalTree — new homepage app
 *
 * Scenarios optimised:
 *   A) Land → see 9 most-famous family cards immediately
 *   B) Type into search → live autocomplete dropdown (up to 8 results)
 *   C) Click a 3-path or 6-region tile → drill into a list
 *   D) Click any card → drawer with relationships (tree traversal)
 */

const COUNTRY_NAMES = {
  KR:"대한민국", JP:"일본", CN:"중국", US:"미국", GB:"영국", DE:"독일", FR:"프랑스",
  IT:"이탈리아", ES:"스페인", RU:"러시아", IN:"인도", CH:"스위스", AT:"오스트리아",
  SE:"스웨덴", PL:"폴란드", NL:"네덜란드", BE:"벨기에", IE:"아일랜드", NO:"노르웨이",
  DK:"덴마크", FI:"핀란드", PT:"포르투갈", GR:"그리스", TR:"튀르키예", SA:"사우디아라비아",
  AE:"아랍에미리트", IL:"이스라엘", IR:"이란", EG:"이집트", ZA:"남아공", BR:"브라질",
  MX:"멕시코", AR:"아르헨티나", CL:"칠레", CO:"콜롬비아", CA:"캐나다", AU:"호주",
  NZ:"뉴질랜드", TH:"태국", VN:"베트남", MY:"말레이시아", SG:"싱가포르", ID:"인도네시아",
  PH:"필리핀", HK:"홍콩", TW:"대만", MO:"마카오", LU:"룩셈부르크", MC:"모나코",
  LI:"리히텐슈타인", BT:"부탄", BN:"브루나이", MA:"모로코", KW:"쿠웨이트", QA:"카타르",
  BH:"바레인", OM:"오만", JO:"요르단", LB:"레바논", IQ:"이라크", YE:"예멘",
  AF:"아프가니스탄", PK:"파키스탄", BD:"방글라데시", LK:"스리랑카", NP:"네팔",
  MM:"미얀마", KH:"캄보디아", LA:"라오스", MN:"몽골", KZ:"카자흐스탄", UZ:"우즈베키스탄",
  GE:"조지아", AM:"아르메니아", AZ:"아제르바이잔", DZ:"알제리", TN:"튀니지", LY:"리비아",
  SN:"세네갈", NG:"나이지리아", KE:"케냐", ET:"에티오피아", GH:"가나",
  "GB-SCT":"스코틀랜드", CZ:"체코", SK:"슬로바키아", HU:"헝가리", RO:"루마니아",
  BG:"불가리아", RS:"세르비아", HR:"크로아티아", UA:"우크라이나", BY:"벨라루스",
  LT:"리투아니아", LV:"라트비아", EE:"에스토니아", IS:"아이슬란드", MT:"몰타", CY:"키프로스",
};

// Blacklist — historical-figure families that absorbed modern same-surname
// billionaire data via faulty dedup. Hidden from web until source dedup is fixed.
// (See memory/feedback_data_quality.md)
const BLACKLIST_IDS = new Set([
  "royal-tree:manual:zhang-juzheng-family",   // 张居正 (Ming politician) ← ByteDance/TAL/Weiqiao Zhang
]);

const CAT_LABEL = { royal:"왕가", noble:"귀족", clan:"씨족", business:"기업", political:"정치", religious:"종교", tribal:"부족", unknown:"불명" };
const STATUS_LABEL = { active:"현존", extinct:"단절", deposed:"폐위", merged:"합방", unknown:"불명" };
const PANTHEON_LABEL = {
  sovereign: "통치 · Reigning Houses",
  capital:   "자본 · Houses of Capital",
  quiet:     "조용한 부 · Quiet Wealth",
  rule:      "政權 · Political Dynasties",
};
const TIER_ORDER = ["S","A","B","C","D","X"];

const REGIONS = {
  europe:  { ko:"유럽", en:"Europe", codes:["GB","FR","DE","ES","IT","CH","AT","SE","PL","NL","BE","IE","NO","DK","FI","PT","GR","RU","LU","MC","LI","CZ","SK","HU","RO","BG","RS","HR","UA","BY","LT","LV","EE","IS","MT","CY","GB-SCT","GB-WLS","GB-NIR","VA"] },
  asia:    { ko:"아시아", en:"Asia",   codes:["CN","JP","KR","IN","TH","VN","MY","SG","ID","PH","HK","TW","MO","PK","BD","LK","NP","BT","MM","KH","LA","MN","KZ","UZ","BN"] },
  americas:{ ko:"아메리카", en:"Americas", codes:["US","CA","MX","BR","AR","CL","CO"] },
  mideast: { ko:"중동", en:"Middle East", codes:["SA","AE","IL","IR","TR","KW","QA","BH","OM","JO","LB","IQ","YE","SY","AF","GE","AM","AZ"] },
  africa:  { ko:"아프리카", en:"Africa", codes:["EG","ZA","MA","DZ","TN","LY","SN","NG","KE","ET","GH"] },
  oceania: { ko:"오세아니아", en:"Oceania", codes:["AU","NZ"] },
};

// Sector classification — derive from family's `inds` (industries) via keyword rules.
const SECTORS = {
  tech: {
    ko: "테크", en: "Technology",
    kw: ["technology","tech","software","internet","e-commerce","ecommerce","cloud","ai","social","mobile games","semiconductor","반도체","ai/data","platform","electronics","computer services","computer hardware","display","display panels","internet media","online services","online games","video games","online gaming","biometrics","enterprise software","business software","drones","telecom services","telecommunications"],
  },
  finance: {
    ko: "금융", en: "Finance",
    kw: ["finance","banking","investment","investments","asset","private equity","hedge","fund","trading","insurance","payments","fintech","sovereign wealth fund"],
  },
  realestate: {
    ko: "부동산", en: "Real Estate",
    kw: ["real estate","real-estate","property","construction","부동산","real estate development","infrastructure","인프라"],
  },
  luxury: {
    ko: "럭셔리·패션", en: "Luxury & Fashion",
    kw: ["luxury","fashion","cosmetics","jewelry","watches","leather","perfume","apparel","패션","cosmetic","beauty","men's leather"],
  },
  media: {
    ko: "미디어", en: "Media",
    kw: ["media","publishing","broadcasting","newspaper","entertainment","studio","music","film","streaming"],
  },
  energy: {
    ko: "에너지·자원", en: "Energy & Resources",
    kw: ["oil","gas","energy","mining","metals","coal","petrochemical","lng","oil & gas","oil-and-gas","aluminum","steel"],
  },
  auto: {
    ko: "자동차·운송", en: "Auto & Transport",
    kw: ["auto","automotive","car","shipping","logistics","airline","transport","rail","auto services","ports"],
  },
  consumer: {
    ko: "소비재·식품", en: "Consumer & Food",
    kw: ["consumer","food","beverage","retail","supermarket","qsr","grocery","candy","chocolate","brewery","양조","sporting goods","음료","fashion retail","electronics retail","home improvement","wines & spirits"],
  },
  pharma: {
    ko: "제약·헬스", en: "Pharma & Health",
    kw: ["pharma","pharmaceutical","biotech","health","medical","hospital","pharmaceuticals"],
  },
  industrial: {
    ko: "산업·제조", en: "Industrial",
    kw: ["industrial","manufacturing","machinery","chemical","chemicals","cement","conglomerate","conglomerates","luxury conglomerate","conglomerate / various","industrial conglomerate","diversified","electronics","semiconductor","반도체","electronics components","precision machinery","hydraulic machinery","industrial machines","industrial machinery","appliance","appliances","home appliances","appliance retailer","display panels","shipbuilding","valves","aluminum","aluminum products","tires","steel","steel smelting","paper","paper & related products","electrical equipment","lighting","auto parts","heavy industry","batteries","batteries, automobiles"],
  },
  hospitality: {
    ko: "관광·호텔", en: "Hospitality",
    kw: ["hotel","hotels","hospitality","tourism","관광","tourism·hotel","관광·호텔"],
  },
  sports: {
    ko: "스포츠", en: "Sports",
    kw: ["sports","esports","sport","football","baseball","stadium","스포츠","체육"],
  },
};

function sectorsOf(f) {
  // Tokenize each industry into normalized tokens to avoid bogus substring
  // matches like "ai" inside "retail" or "tech" inside "biotech".
  const rawInds = (f.inds || []).map(s => (s || "").toLowerCase());
  const tokens = new Set();
  for (const ind of rawInds) {
    tokens.add(ind);                  // full string
    for (const t of ind.split(/[\s,./|()\-&]+/)) {
      if (t) tokens.add(t);
    }
  }
  const out = new Set();
  for (const [k, def] of Object.entries(SECTORS)) {
    for (const w of def.kw) {
      // For short ASCII keywords (≤4) require exact token match;
      // for longer keywords or non-ASCII allow substring on full ind string.
      const isShortAscii = w.length <= 4 && /^[a-z0-9+-]+$/.test(w);
      const hit = isShortAscii
        ? tokens.has(w)
        : rawInds.some(i => i.includes(w));
      if (hit) { out.add(k); break; }
    }
  }
  return [...out];
}

// Famous-9 — hand-picked most globally recognised families.
const FEATURED_IDS = [
  "Q81589",                                                         // House of Windsor
  "royal-tree:manual:bezos-family-jeff-bezos",                      // Bezos
  "Q165687",                                                        // House of Saud
  "royal-tree:overlay:arnault-lvmh",                                // LVMH Arnault
  "Q186040",                                                        // Imperial House of Japan
  "Q298547",                                                        // Mukesh Ambani
  "Q17343056",                                                      // Walton
  "royal-tree:manual:zuckerberg-family-mark-zuckerberg",            // Zuckerberg
  "royal-tree:manual:mars-family-jacqueline-mars",                  // Mars
];

const STATE = {
  index: null,
  detail: null,
  detailPromise: null,
  byId: new Map(),
  byCountry: new Map(),
  bySector: new Map(),     // sector key -> [family,…] sorted by valuation
  byRegion: new Map(),     // region key -> [family,…]
  byPantheon: new Map(),
  byCategory: new Map(),   // category (business/royal/...) -> [family,…]
  crossIndex: null,        // {category: {country: {wealth:[ids], hot:[ids], name:[ids], count}}}
};

const $ = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));

function fmtUSD(v) {
  if (!v) return "";
  if (v >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (v >= 1e9)  return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6)  return `$${(v / 1e6).toFixed(0)}M`;
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
// Country code → regional-indicator emoji flag. Returns "" if not 2-letter.
function flagEmoji(c) {
  if (!c) return "";
  if (c === "GB-SCT") return "🏴󠁧󠁢󠁳󠁣󠁴󠁿"; // 🏴󠁧󠁢󠁳󠁣󠁴󠁿
  if (c === "GB-WLS") return "🏴󠁧󠁢󠁷󠁬󠁳󠁿"; // 🏴󠁧󠁢󠁷󠁬󠁳󠁿
  if (c === "GB-ENG") return "🏴󠁧󠁢󠁥󠁮󠁧󠁿";
  if (c === "VA") return "🇻🇦";
  if (!/^[A-Z]{2}$/.test(c)) return "";
  const A = 0x1F1E6, a = "A".charCodeAt(0);
  return String.fromCodePoint(A + c.charCodeAt(0) - a) + String.fromCodePoint(A + c.charCodeAt(1) - a);
}
// First displayable country (skips q: pseudo-codes).
function primaryCountry(f) {
  for (const c of (f.c || [])) {
    if (c && !c.startsWith("q:") && c !== "AR-region") return c;
  }
  return null;
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
function regionOf(countries) {
  for (const c of countries || []) {
    for (const [key, def] of Object.entries(REGIONS)) {
      if (def.codes.includes(c)) return key;
    }
  }
  return null;
}

/* ============ load ============ */

async function loadIndex() {
  const res = await fetch("families.index.json?v=15");
  STATE.index = await res.json();
  // Drop blacklisted (data-pollution) families before any indexing.
  STATE.index.families = STATE.index.families.filter(f => !BLACKLIST_IDS.has(f.id));
  STATE.index.families.forEach(f => {
    STATE.byId.set(f.id, f);
    // country
    (f.c || []).forEach(c => {
      if (c.startsWith("q:")) return;
      if (!STATE.byCountry.has(c)) STATE.byCountry.set(c, []);
      STATE.byCountry.get(c).push(f);
    });
    // region
    const r = regionOf(f.c);
    if (r) {
      if (!STATE.byRegion.has(r)) STATE.byRegion.set(r, []);
      STATE.byRegion.get(r).push(f);
    }
    // sectors
    for (const s of sectorsOf(f)) {
      if (!STATE.bySector.has(s)) STATE.bySector.set(s, []);
      STATE.bySector.get(s).push(f);
    }
    // pantheon
    if (f.pantheon) {
      if (!STATE.byPantheon.has(f.pantheon)) STATE.byPantheon.set(f.pantheon, []);
      STATE.byPantheon.get(f.pantheon).push(f);
    }
    // category (royal/noble/business/clan/political/religious/tribal/unknown)
    const cat = f.cat || "unknown";
    if (!STATE.byCategory.has(cat)) STATE.byCategory.set(cat, []);
    STATE.byCategory.get(cat).push(f);
  });
  // sort all by tier, then valuation
  for (const map of [STATE.byCountry, STATE.byRegion, STATE.bySector, STATE.byPantheon, STATE.byCategory]) {
    for (const arr of map.values()) {
      arr.sort((a,b) =>
        TIER_ORDER.indexOf(a.tc || "X") - TIER_ORDER.indexOf(b.tc || "X")
        || (b.v || 0) - (a.v || 0));
    }
  }
  // For sector showcases, prefer curated pantheon families first.
  // We keep the full sector lists as-is (for the browse view) but compute
  // a separate "leaders" ordering used by the homepage sector tiles.
  STATE.sectorLeaders = new Map();
  for (const [key, list] of STATE.bySector.entries()) {
    const leaders = list.slice().sort((a, b) => {
      const ap = a.pantheon ? 0 : 1;
      const bp = b.pantheon ? 0 : 1;
      if (ap !== bp) return ap - bp;
      return TIER_ORDER.indexOf(a.tc || "X") - TIER_ORDER.indexOf(b.tc || "X")
        || (b.v || 0) - (a.v || 0);
    });
    STATE.sectorLeaders.set(key, leaders);
  }
}
async function loadDetail() {
  if (STATE.detail) return STATE.detail;
  if (STATE.detailPromise) return STATE.detailPromise;
  STATE.detailPromise = fetch("families.detail.json?v=15").then(r => r.json()).then(d => { STATE.detail = d; return d; });
  return STATE.detailPromise;
}

/* ============ featured grid ============ */

function featCardHTML(f, n) {
  const alt = altOf(f);
  const pc = primaryCountry(f);
  const flag = pc ? flagEmoji(pc) : "";
  const country = pc ? countryLabel(pc) : ((f.c || []).map(countryLabel).filter(Boolean)[0] || "");
  const founded = f.founded ? `est ${String(f.founded).slice(0,4)}` : "";
  const countryHtml = country ? `<span class="fc-country">${flag ? `<span class="fc-flag" aria-hidden="true">${flag}</span>` : ""}${escapeHtml(country)}</span>` : "";
  const meta = founded ? `${countryHtml}${countryHtml ? ' · ' : ''}<span>${founded}</span>` : countryHtml;
  const val = f.v ? `<span class="v">${fmtUSD(f.v)}</span>` : "";
  return `
    <article class="feat-card" data-id="${f.id}">
      <div class="fc-rank">${String(n).padStart(2,"0")}.</div>
      <div class="fc-body">
        <h3 class="fc-name">${f.n}</h3>
        ${alt ? `<div class="fc-alt">${alt}</div>` : ""}
        <p class="fc-headline">${f.headline || ""}</p>
      </div>
      <div class="fc-meta">
        <span>${meta}</span>${val}
      </div>
    </article>
  `;
}
function renderFeatured() {
  const el = $("#featured-grid");
  const cards = FEATURED_IDS
    .map(id => STATE.byId.get(id))
    .filter(Boolean);
  el.innerHTML = cards.map((f, i) => featCardHTML(f, i + 1)).join("");
}

/* ============ paths ============ */

function renderPathCounts() {
  for (const p of ["sovereign", "capital", "quiet", "rule"]) {
    const n = STATE.index.families.filter(f => f.pantheon === p).length;
    const el = document.querySelector(`[data-count="${p}"]`);
    if (el) el.textContent = `${n}家 →`;
  }
}

function renderCategoryCounts() {
  for (const cat of ["business","royal","noble","clan","political","religious","tribal","unknown"]) {
    const n = (STATE.byCategory.get(cat) || []).length;
    const el = document.querySelector(`[data-cat-count="${cat}"]`);
    if (el) el.textContent = n ? `${n.toLocaleString()}家` : "";
  }
}

/* ============ regions ============ */

function renderRegions() {
  const order = ["europe", "asia", "americas", "mideast", "africa", "oceania"];
  const html = order.map(k => {
    const list = STATE.byRegion.get(k) || [];
    return `
    <a class="region-tile" href="#region/${k}">
      <div class="rt-label">${REGIONS[k].en}</div>
      <h3 class="rt-name">${REGIONS[k].ko.split('').map((c,i)=>i===1?`<em>${c}</em>`:c).join('')}</h3>
      <div class="rt-meta">
        <span>${REGIONS[k].codes.length} 국가</span>
        <span class="rt-count">${list.length.toLocaleString()}家</span>
      </div>
    </a>`;
  }).join("");
  $("#region-grid").innerHTML = html;
}

function renderSectors() {
  const order = ["tech", "luxury", "finance", "realestate", "energy", "auto", "media", "consumer", "pharma", "industrial", "hospitality", "sports"];
  const html = order.map(k => {
    const list = STATE.bySector.get(k) || [];
    const leaders = STATE.sectorLeaders.get(k) || list;
    const top = leaders.slice(0, 3).map(f => f.n).join(" · ");
    return `
      <a class="sector-tile" href="#sector/${k}">
        <div class="st-label">${SECTORS[k].en}</div>
        <h3 class="st-name">${SECTORS[k].ko}</h3>
        ${top ? `<p class="st-top">${top}</p>` : `<p class="st-top muted">—</p>`}
        <div class="st-meta">
          <span class="st-count">${list.length.toLocaleString()}家</span>
          <span class="st-arrow">→</span>
        </div>
      </a>`;
  }).join("");
  $("#sector-grid").innerHTML = html;
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
    (f.st || "") + " " + (STATUS_LABEL[f.st] || "")
  ).toLowerCase();
  return tokens.every(t => hay.includes(t));
}

function scoreMatch(f, q) {
  // higher score = better. Pantheon families and exact name matches rank higher.
  let s = 0;
  const ql = q.toLowerCase();
  const n = (f.n || "").toLowerCase();
  if (n === ql) s += 1000;
  if (n.startsWith(ql)) s += 200;
  if (n.includes(ql)) s += 50;
  if (f.pantheon) s += 30;
  if (f.tc === "S") s += 20;
  else if (f.tc === "A") s += 12;
  else if (f.tc === "B") s += 6;
  s += Math.min(20, Math.floor(Math.log10((f.v || 1)) - 8)); // mild log bonus
  return s;
}

function runAutocomplete(q) {
  const pop = $("#search-pop");
  if (!q.trim()) {
    pop.hidden = true;
    pop.innerHTML = "";
    return;
  }
  const list = STATE.index.families
    .filter(f => searchOne(f, q))
    .map(f => ({ f, s: scoreMatch(f, q) }))
    .sort((a, b) => b.s - a.s)
    .slice(0, 8);

  if (!list.length) {
    pop.innerHTML = `
      <li class="sp-empty">
        <strong>“${escapeHtml(q)}”</strong>에 일치하는 가문이 없습니다.<br>
        시도: <em>Windsor · Bezos · 사우디 · LVMH · 삼성 · 霍 · Rothschild · Mars</em>
      </li>`;
    pop.hidden = false;
    return;
  }
  pop.innerHTML = list.map(({f}) => {
    const alt = altOf(f);
    const country = (f.c || []).map(countryLabel).filter(Boolean)[0] || "";
    const tier = f.tc ? `현 ${f.tc}` : "";
    const v = f.v ? fmtUSD(f.v) : "";
    const meta = [country, tier, v].filter(Boolean).join(" · ");
    return `
      <li data-id="${f.id}" role="option">
        <span>
          <span class="sp-name">${escapeHtml(f.n)}</span>
          ${alt ? `<span class="sp-alt">${escapeHtml(alt)}</span>` : ""}
        </span>
        <span class="sp-meta">${escapeHtml(meta)}</span>
      </li>`;
  }).join("");
  pop.hidden = false;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}

/* ============ drawer ============ */

async function openDetail(id) {
  const drawer = $("#drawer");
  const content = $("#drawer-content");
  drawer.hidden = false;
  drawer.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";

  const idxF = STATE.byId.get(id);
  if (!idxF) { content.innerHTML = `<div class="empty">자료를 찾지 못했습니다.</div>`; return; }
  content.innerHTML = `<div class="empty">두루마리를 펴는 중…</div>`;
  $(".drawer-panel").scrollTop = 0;

  const detail = await loadDetail();
  const d = detail[id] || {};
  content.innerHTML = renderDetail(idxF, d);
  $(".drawer-panel").scrollTop = 0;
  $$('#drawer-content [data-jump]').forEach(el => {
    el.addEventListener("click", e => {
      e.preventDefault();
      const tid = el.dataset.jump;
      if (STATE.byId.has(tid)) openDetail(tid);
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
      <div>
        <div class="type-tag">${escapeHtml(type)}${yearBit ? " " + yearBit : ""}</div>
        <div class="target">${escapeHtml(target)} ${activeBit}</div>
        ${summary ? `<div class="summary">${escapeHtml(summary)}</div>` : ""}
      </div>
      <div class="arrow">→</div>
    </a>
  `;
}

function findFamilyByName(name) {
  if (!name) return null;
  const n = name.toLowerCase();
  for (const f of STATE.index.families) if ((f.n || "").toLowerCase() === n) return f.id;
  let best = null, bestLen = Infinity;
  for (const f of STATE.index.families) {
    const all = [f.n, ...(Object.values(f.names || {}))].filter(Boolean).map(x => x.toLowerCase());
    for (const an of all) if (n.includes(an) || an.includes(n)) {
      if (an.length < bestLen) { best = f.id; bestLen = an.length; }
    }
  }
  return best;
}

function renderDetail(f, d) {
  const alt = altOf(f);
  const head = d.head_card || {};
  const biz = head.business || {};
  const tag = f.pantheon ? PANTHEON_LABEL[f.pantheon] : `${CAT_LABEL[f.cat]||f.cat||""}${f.st && f.st!=="active"?` · ${STATUS_LABEL[f.st]||""}`:""}`;
  const countries = (f.c || []).map(countryLabel).filter(Boolean).join(" · ");
  const valuation = biz.total_valuation_usd ? `<span class="v">${fmtUSD(biz.total_valuation_usd)}</span>` : "";
  const tierLine = f.tc ? `<span>현 ${f.tc}${f.tp && f.tp !== f.tc ? " · 과 " + f.tp : ""}</span>` : "";
  const founded = f.founded ? `<span>est ${String(f.founded).slice(0,4)}</span>` : "";

  // head card
  let headSec = "";
  if (head.name) {
    const titles = (head.titles || []).join(" · ");
    headSec = `
      <div>
        <div class="dd-head-name">${escapeHtml(head.name)}</div>
        ${titles ? `<div class="dd-titles">${escapeHtml(titles)}</div>` : ""}
        ${head.birth || head.death ? `<div class="dd-row"><span class="lbl">생몰</span>${head.birth || "?"}${head.death ? ` – ${head.death}` : " – 현존"}</div>` : ""}
        ${head.spouses?.length ? `<div class="dd-row"><span class="lbl">배우자</span>${head.spouses.join(", ")}</div>` : ""}
        ${head.children?.length ? `<div class="dd-row"><span class="lbl">자녀</span>${head.children.join(", ")}</div>` : ""}
      </div>`;
  } else if (head.note) {
    headSec = `<div class="dd-row" style="font-style:italic">${escapeHtml(head.note)}</div>`;
  }

  // business
  let bizSec = "";
  if (biz.top && biz.top.length) {
    bizSec = biz.top.map(b => `
      <div class="biz-row">
        <div>
          <div class="biz-name">${escapeHtml(b.name || b.industry || "(이름 미상)")}</div>
          <div class="biz-meta">
            ${b.industry ? `<span>${escapeHtml(b.industry)}</span>` : ""}
            ${b.country_hq?.length ? ` · <span>${b.country_hq.map(countryLabel).filter(Boolean).join(", ")}</span>` : ""}
            ${b.control_type ? ` · <span>${escapeHtml(b.control_type)}</span>` : ""}
          </div>
        </div>
        ${b.valuation_usd ? `<div class="biz-val">${fmtUSD(b.valuation_usd)}</div>` : ""}
      </div>`).join("");
    if (biz.industries?.length) {
      bizSec += `<div class="industries-row">${biz.industries.map(i => `<span>${escapeHtml(i)}</span>`).join("")}</div>`;
    }
  }

  // people
  const personItem = (p) => `
    <div class="person-row">
      <div class="person-era">${era(p)}</div>
      <div>
        <div class="person-name">${escapeHtml(p.name || "(이름 미상)")} <span class="person-life">${lifeSpan(p)}</span></div>
        ${p.titles?.length ? `<div class="person-titles">${escapeHtml(p.titles.join(" · "))}</div>` : ""}
        ${p.spouses?.length ? `<div class="dd-row"><span class="lbl">배우자</span>${escapeHtml(p.spouses.join(", "))}</div>` : ""}
        ${p.children?.length ? `<div class="dd-row"><span class="lbl">자녀</span>${escapeHtml(p.children.join(", "))}</div>` : ""}
      </div>
    </div>`;
  const origin = (d.origin || []).filter(Boolean);
  const recent = (d.recent || []).filter(Boolean);
  let personSec = "";
  if (origin.length) {
    personSec += origin.map(personItem).join("");
  }
  if (d.middle_summary) {
    personSec += `<div style="padding:14px 0;font-family:var(--display);font-style:italic;color:var(--sub);font-size:14px;border-bottom:1px solid var(--hair)">${escapeHtml(d.middle_summary)}</div>`;
  }
  if (recent.length) {
    personSec += recent.map(personItem).join("");
  }

  // spouses + relations as traverse cards
  let spouseSec = "";
  if (d.spouses_lineage?.length) {
    spouseSec = d.spouses_lineage.map(s => {
      const guessId = findFamilyByName(s.family_name || s.family_of_origin || s.name);
      return traverseCard({
        type: "혼인 · 본가",
        target: s.family_name || s.family_of_origin || s.name,
        summary: `${s.name ? s.name + " — " : ""}${s.summary || ""}`,
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

  return `
    <div class="dd-head">
      <div class="dd-tag">${escapeHtml(tag)}</div>
      ${alt ? `<div class="dd-alt">${escapeHtml(alt)}</div>` : ""}
      <h2 class="dd-name">${escapeHtml(f.n)}</h2>
      ${f.headline ? `<div class="dd-headline">${escapeHtml(f.headline)}</div>` : ""}
      <div class="dd-meta">
        ${tierLine}
        ${countries ? `<span>${countries}</span>` : ""}
        ${founded}
        ${valuation ? `· ${valuation}` : ""}
      </div>
      ${f.peak_era ? `<div class="dd-meta" style="margin-top:8px"><span style="text-transform:none;letter-spacing:0;font-family:var(--display);font-style:italic;color:var(--bordeaux);font-size:14px">절정기 — ${escapeHtml(f.peak_era)}</span></div>` : ""}
      ${f.narrative ? `<div class="dd-narrative">${escapeHtml(f.narrative)}</div>` : ""}
    </div>

    ${headSec ? `<div class="dd-section"><h3>지금의 가주</h3>${headSec}</div>` : ""}
    ${bizSec ? `<div class="dd-section"><h3>사업체 <span class="count">${biz.count || biz.top?.length || ""}</span></h3>${bizSec}</div>` : ""}
    ${spouseSec ? `<div class="dd-section"><h3>혼인으로 이어진 가문</h3>${spouseSec}</div>` : ""}
    ${relSec ? `<div class="dd-section"><h3>가문 간 관계</h3>${relSec}</div>` : ""}
    ${personSec ? `<div class="dd-section"><h3>혈맥</h3>${personSec}</div>` : ""}
    ${d.notes ? `<div class="dd-section"><h3>비고</h3><div style="font-family:var(--kr);font-weight:300;color:var(--ink-2);line-height:1.75">${escapeHtml(d.notes)}</div></div>` : ""}
    ${d.sources?.length ? `<div class="dd-foot">출처 — ${d.sources.map(s => `<code>${escapeHtml(s)}</code>`).join(" · ")}</div>` : ""}
  `;
}

function closeDetail() {
  const drawer = $("#drawer");
  drawer.hidden = true;
  drawer.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
}

/* ============ browse / router ============ */

const BROWSE_LIMIT_STEP = 36;
let BROWSE_STATE = null;

function browseCardHTML(f) {
  const alt = altOf(f);
  const pc = primaryCountry(f);
  const flag = pc ? flagEmoji(pc) : "";
  const country = pc ? countryLabel(pc) : ((f.c || []).map(countryLabel).filter(Boolean)[0] || "");
  const founded = f.founded ? `est ${String(f.founded).slice(0,4)}` : "";
  const countryHtml = country ? `<span class="fc-country">${flag ? `<span class="fc-flag" aria-hidden="true">${flag}</span>` : ""}${escapeHtml(country)}</span>` : "";
  const meta = founded ? `${countryHtml}${countryHtml ? ' · ' : ''}<span>${founded}</span>` : countryHtml;
  const val = f.v ? `<span class="v">${fmtUSD(f.v)}</span>` : "";
  const inds = (f.inds || []).slice(0, 2).join(" · ");
  return `
    <article class="feat-card" data-id="${f.id}">
      <div class="fc-rank">${alt ? `<span style="font-style:normal;color:var(--sub);font-size:13px">${escapeHtml(alt)}</span>` : "·"}</div>
      <div class="fc-body">
        <h3 class="fc-name">${escapeHtml(f.n)}</h3>
        ${f.headline ? `<p class="fc-headline" style="color:var(--bordeaux);font-family:var(--display);font-style:italic">${escapeHtml(f.headline)}</p>` : (inds ? `<p class="fc-headline">${escapeHtml(inds)}</p>` : "")}
      </div>
      <div class="fc-meta">
        <span>${meta}</span>${val}
      </div>
    </article>`;
}

function browseTitle(type, value) {
  if (type === "region") {
    const def = REGIONS[value];
    return def ? { eyebrow: def.en, title: def.ko, sub: `${def.codes.length}개국` } : null;
  }
  if (type === "sector") {
    const def = SECTORS[value];
    return def ? { eyebrow: def.en, title: def.ko, sub: "분야별 리더" } : null;
  }
  if (type === "pantheon") {
    const labels = {
      sovereign: { ko:"통치", en:"Reigning Houses" },
      capital:   { ko:"자본", en:"Houses of Capital" },
      quiet:     { ko:"조용한 부", en:"Quiet Wealth" },
      rule:      { ko:"政權", en:"Political Dynasties" },
    };
    const def = labels[value];
    return def ? { eyebrow: def.en, title: def.ko, sub: "세 가지 길" } : null;
  }
  if (type === "tier") {
    return { eyebrow: "Tier", title: `현 ${value}위계`, sub: "현재 영향력 등급" };
  }
  if (type === "cat") {
    const labels = {
      business: { ko:"기업가문", en:"Business Houses" },
      royal:    { ko:"왕가",     en:"Royal Houses" },
      noble:    { ko:"귀족가문", en:"Noble Houses" },
      clan:     { ko:"씨족",     en:"Clans" },
      political:{ ko:"정치가문", en:"Political Dynasties" },
      religious:{ ko:"종교가문", en:"Religious Houses" },
      tribal:   { ko:"부족",     en:"Tribal Houses" },
      unknown:  { ko:"기타",     en:"Other" },
    };
    const def = labels[value];
    return def ? { eyebrow: def.en, title: def.ko, sub: "분류별 인덱스" } : null;
  }
  if (type === "country") {
    const lbl = countryLabel(value) || value;
    return { eyebrow: "Country", title: lbl, sub: "국가별 가문" };
  }
  return null;
}

function browseDataset(type, value) {
  if (type === "region") return STATE.byRegion.get(value) || [];
  if (type === "sector") return STATE.bySector.get(value) || [];
  if (type === "pantheon") return STATE.byPantheon.get(value) || [];
  if (type === "tier") return STATE.index.families.filter(f => (f.tc || "X") === value);
  if (type === "cat") return STATE.byCategory.get(value) || [];
  if (type === "country") return STATE.byCountry.get(value) || [];
  return [];
}

function renderBrowse(type, value) {
  const view = $("#browse-view");
  const home = $("#home-view");
  const title = browseTitle(type, value);
  const data = browseDataset(type, value);
  if (!title || !data) {
    view.hidden = true; home.hidden = false; return;
  }
  home.hidden = true; view.hidden = false;

  BROWSE_STATE = { type, value, all: data, sub: null, shown: BROWSE_LIMIT_STEP,
                   sortBy: "wealth", countryFilter: null };
  renderBrowseInner();
  window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });
}

function renderBrowseInner() {
  if (!BROWSE_STATE) return;
  const { type, value, all, sub, shown, sortBy, countryFilter } = BROWSE_STATE;
  const title = browseTitle(type, value);
  let list = all;
  if (countryFilter) list = list.filter(f => (f.c || []).includes(countryFilter));
  if (sub) {
    if (sub.kind === "tier") list = list.filter(f => (f.tc || "X") === sub.value);
    else if (sub.kind === "money") {
      const r = MONEY_RANGES[sub.value];
      list = list.filter(f => f.v && f.v >= r[0] && f.v < r[1]);
    } else if (sub.kind === "region") {
      list = list.filter(f => regionOf(f.c) === sub.value);
    }
  }
  // sort
  list = list.slice();
  if (sortBy === "hot") {
    // "최근 HOT" = recently-active families: latest known person birth desc,
    // then valuation desc (covers both modern billionaires and active dynasties).
    list.sort((a,b) =>
      (b.yr || 0) - (a.yr || 0)
      || (b.v || 0) - (a.v || 0)
      || TIER_ORDER.indexOf(a.tc || "X") - TIER_ORDER.indexOf(b.tc || "X"));
  } else if (sortBy === "name") {
    list.sort((a,b) => (a.n || "").localeCompare(b.n || "", "ko"));
  } else { // wealth (default)
    list.sort((a,b) => (b.v || 0) - (a.v || 0)
      || TIER_ORDER.indexOf(a.tc || "X") - TIER_ORDER.indexOf(b.tc || "X"));
  }
  const slice = list.slice(0, shown);
  // country chip top-10 (within current list)
  const countryCounts = new Map();
  for (const f of all) {
    for (const c of f.c || []) {
      if (c && !c.startsWith("q:")) countryCounts.set(c, (countryCounts.get(c) || 0) + 1);
    }
  }
  const topCountries = [...countryCounts.entries()].sort((a,b) => b[1]-a[1]).slice(0, 10);
  const view = $("#browse-view");
  view.innerHTML = `
    <div class="browse-inner">
      <nav class="breadcrumb">
        <a href="#" data-go="home">홈</a>
        <span class="bc-sep">/</span>
        <span>${escapeHtml(title.eyebrow)}</span>
      </nav>
      <header class="browse-head">
        <div>
          <p class="kicker" style="text-align:left;margin-bottom:10px">${escapeHtml(title.sub)} · ${escapeHtml(title.eyebrow)}</p>
          <h1 class="browse-title">${escapeHtml(title.title)}</h1>
        </div>
        <div class="browse-count"><strong>${list.length.toLocaleString()}</strong>家</div>
      </header>

      <div class="browse-subfilter">
        <span class="sf-label">정렬</span>
        <button class="sf-chip ${sortBy==='wealth'?'active':''}" data-sort="wealth">💰 자산순</button>
        <button class="sf-chip ${sortBy==='hot'?'active':''}" data-sort="hot">🔥 최근 HOT</button>
        <button class="sf-chip ${sortBy==='name'?'active':''}" data-sort="name">가나다순</button>
        <span class="sf-sep"></span>
        <span class="sf-label">자산</span>
        <button class="sf-chip ${sub?.kind==='money'&&sub.value==='100b+'?'active':''}" data-sub="money:100b+">$100B+</button>
        <button class="sf-chip ${sub?.kind==='money'&&sub.value==='50-100b'?'active':''}" data-sub="money:50-100b">$50–100B</button>
        <button class="sf-chip ${sub?.kind==='money'&&sub.value==='10-50b'?'active':''}" data-sub="money:10-50b">$10–50B</button>
        <button class="sf-chip ${sub?.kind==='money'&&sub.value==='1-10b'?'active':''}" data-sub="money:1-10b">$1–10B</button>
        <span class="sf-sep"></span>
        <span class="sf-label">위계</span>
        <button class="sf-chip ${sub?.kind==='tier'&&sub.value==='S'?'active':''}" data-sub="tier:S">S</button>
        <button class="sf-chip ${sub?.kind==='tier'&&sub.value==='A'?'active':''}" data-sub="tier:A">A</button>
        <button class="sf-chip ${sub?.kind==='tier'&&sub.value==='B'?'active':''}" data-sub="tier:B">B</button>
        ${sub || countryFilter ? `<button class="sf-chip sf-clear" data-sub="clear">× 필터 지우기</button>` : ""}
      </div>
      ${topCountries.length > 1 ? `
      <div class="browse-subfilter browse-countrybar">
        <span class="sf-label">국가</span>
        ${topCountries.map(([cc, n]) => {
          const fe = flagEmoji(cc);
          return `<button class="sf-chip sf-country ${countryFilter===cc?'active':''}" data-country="${cc}">${fe ? `<span class="sf-flag" aria-hidden="true">${fe}</span>` : ""}${escapeHtml(countryLabel(cc) || cc)} <span class="sf-count">${n}</span></button>`;
        }).join("")}
      </div>` : ""}

      ${list.length === 0
        ? `<div class="empty" style="padding:80px 0">조건에 맞는 가문이 없습니다.</div>`
        : `<div class="featured-grid browse-grid">${slice.map(browseCardHTML).join("")}</div>`}

      ${shown < list.length ? `<div style="text-align:center;margin-top:40px"><button id="browse-more" class="archive-btn">→ 다음 ${Math.min(BROWSE_LIMIT_STEP, list.length-shown)}家 (총 ${list.length})</button></div>` : ""}
    </div>
  `;
  $$(".sf-chip").forEach(b => b.addEventListener("click", () => {
    if (b.dataset.sort) {
      BROWSE_STATE.sortBy = b.dataset.sort;
      BROWSE_STATE.shown = BROWSE_LIMIT_STEP;
      renderBrowseInner();
      return;
    }
    if (b.dataset.country) {
      const cc = b.dataset.country;
      BROWSE_STATE.countryFilter = BROWSE_STATE.countryFilter === cc ? null : cc;
      BROWSE_STATE.shown = BROWSE_LIMIT_STEP;
      renderBrowseInner();
      return;
    }
    const v = b.dataset.sub;
    if (v === "clear") {
      BROWSE_STATE.sub = null;
      BROWSE_STATE.countryFilter = null;
    } else {
      const [k, val] = v.split(":");
      BROWSE_STATE.sub = (BROWSE_STATE.sub?.kind===k && BROWSE_STATE.sub?.value===val) ? null : { kind:k, value:val };
    }
    BROWSE_STATE.shown = BROWSE_LIMIT_STEP;
    renderBrowseInner();
  }));
  $("#browse-more")?.addEventListener("click", () => {
    BROWSE_STATE.shown += BROWSE_LIMIT_STEP;
    renderBrowseInner();
  });
}

const MONEY_RANGES = {
  "1-10b":   [1e9,  1e10],
  "10-50b":  [1e10, 5e10],
  "50-100b": [5e10, 1e11],
  "100b+":   [1e11, Infinity],
};

function showHome() {
  $("#browse-view").hidden = true;
  $("#home-view").hidden = false;
  BROWSE_STATE = null;
}

function route() {
  const h = (location.hash || "").replace(/^#/, "");
  if (!h || h === "/" || h === "home") { showHome(); return; }
  // patterns: region/X, sector/X, pantheon/X, tier/X
  const parts = h.split("/");
  const type = parts[0], value = parts[1];
  if (["region","sector","pantheon","tier","cat","country"].includes(type) && value) {
    renderBrowse(type, value);
  } else {
    showHome();
  }
}

/* ============ events ============ */

function wire() {
  // open drawer on any data-id click
  document.body.addEventListener("click", e => {
    const item = e.target.closest("[data-id]");
    if (item) {
      openDetail(item.dataset.id);
      $("#search-pop").hidden = true;
    }
    if (e.target.dataset && e.target.dataset.close !== undefined) closeDetail();
  });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") {
      closeDetail();
      $("#search-pop").hidden = true;
    }
    // Cmd+K / Ctrl+K → focus search
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      $("#q").focus();
    }
  });

  const q = $("#q");
  const clear = $("#clear-q");
  const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(()=>fn(...a), ms); }; };
  const onInput = debounce(() => {
    clear.hidden = !q.value;
    runAutocomplete(q.value);
  }, 110);
  q.addEventListener("input", onInput);
  q.addEventListener("focus", () => { if (q.value) runAutocomplete(q.value); });
  clear.addEventListener("click", () => {
    q.value = "";
    clear.hidden = true;
    $("#search-pop").hidden = true;
    q.focus();
  });
  document.addEventListener("click", e => {
    if (!e.target.closest(".topbar-search")) $("#search-pop").hidden = true;
  });
  q.addEventListener("keydown", e => {
    if (e.key === "Enter") {
      e.preventDefault();
      const first = $("#search-pop li[data-id]");
      if (first) {
        openDetail(first.dataset.id);
        $("#search-pop").hidden = true;
      }
    }
  });

  // focus-search button
  $("#focus-search")?.addEventListener("click", () => {
    q.focus();
    q.scrollIntoView({behavior:"smooth", block:"start"});
  });

  // 'home' nav anchor
  $$('[data-go="home"]').forEach(el => {
    el.addEventListener("click", e => {
      e.preventDefault();
      location.hash = "";
      showHome();
    });
  });

  // hash routing
  window.addEventListener("hashchange", route);
}

/* ============ boot ============ */

async function boot() {
  try {
    await loadIndex();
    renderFeatured();
    renderSectors();
    renderPathCounts();
    renderCategoryCounts();
    renderRegions();
    wire();
    route();
  } catch (err) {
    console.error(err);
    $("#featured-grid").innerHTML = `<div class="empty">자료를 불러오지 못했습니다.</div>`;
  }
}

boot();
