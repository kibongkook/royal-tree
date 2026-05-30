// Headless QA — exercise live site and report any errors, broken links, or
// usability issues we can detect programmatically.
import { chromium } from "playwright";

const BASE = "https://royal-tree.pages.dev";
const issues = [];
const log = (s) => process.stdout.write(s + "\n");
const fail = (id, desc) => { issues.push({ id, desc }); log(`  ❌ ${id}: ${desc}`); };
const ok = (id, desc) => log(`  ✓ ${id}: ${desc}`);

async function main() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    userAgent: "RoyalTree-QA/1.0",
  });
  const page = await ctx.newPage();

  const consoleErrors = [];
  const failedRequests = [];
  page.on("console", m => { if (m.type() === "error") consoleErrors.push(m.text()); });
  page.on("pageerror", e => consoleErrors.push("pageerror: " + e.message));
  page.on("requestfailed", req => {
    const u = req.url();
    // Ignore third-party tracking / extension noise
    if (/google-analytics|facebook|chrome-extension/.test(u)) return;
    failedRequests.push(`${u} (${req.failure()?.errorText})`);
  });

  // ── T1: home ──
  log("\n[1] Homepage");
  const t0 = Date.now();
  const resp = await page.goto(BASE, { waitUntil: "networkidle", timeout: 30000 });
  if (resp?.status() === 200) ok("T1.1", `home 200 in ${Date.now()-t0}ms`);
  else fail("T1.1", `home returned ${resp?.status()}`);
  const title = await page.title();
  if (title.includes("로열트리")) ok("T1.2", `title: ${title}`);
  else fail("T1.2", `title missing 로열트리: ${title}`);

  // ── T2: featured 9 cards (.feat-card not .featured-card) ──
  log("\n[2] Featured 9 cards");
  await page.waitForSelector("#featured-grid", { timeout: 10000 });
  const cards = await page.locator("#featured-grid .feat-card").count();
  if (cards >= 9) ok("T2.1", `${cards} featured cards`);
  else fail("T2.1", `only ${cards} featured cards (expected ≥9)`);

  // ── T3: 카테고리 그리드 ──
  log("\n[3] Categories grid");
  const catCards = await page.locator(".cat-grid .cat-card").count();
  if (catCards === 8) ok("T3.1", "8 category cards");
  else fail("T3.1", `${catCards} category cards (expected 8)`);
  const catCounts = await page.$$eval(".cat-card span", spans => spans.map(s => s.textContent.trim()));
  log(`  cat counts: ${JSON.stringify(catCounts)}`);

  // ── T4: Browse #cat/business ──
  log("\n[4] Browse business");
  await page.goto(BASE + "/#cat/business", { waitUntil: "networkidle" });
  await page.waitForSelector(".browse-view", { timeout: 10000 });
  await page.waitForTimeout(800);
  const browseCards = await page.locator(".browse-grid .feat-card").count();
  if (browseCards > 0) ok("T4.1", `${browseCards} browse cards visible`);
  else fail("T4.1", `0 browse cards in business category`);

  // List all country chips visible
  const allChips = await page.locator(".sf-country").allTextContents();
  log(`  country chips visible: ${JSON.stringify(allChips.slice(0, 12))}`);
  const krChip = page.locator(".sf-country", { hasText: "대한민국" }).first();
  if (await krChip.count() > 0) {
    await krChip.click();
    await page.waitForTimeout(500);
    const krCards = await page.locator(".browse-grid .feat-card").count();
    if (krCards > 0 && krCards <= 25) ok("T4.2", `KR filter → ${krCards} cards`);
    else fail("T4.2", `KR filter showed ${krCards} cards`);

    const text = await page.locator(".browse-grid").textContent() || "";
    if (/(Hyundai|현대)/.test(text)) ok("T4.3", "Hyundai 보임");
    else fail("T4.3", "Hyundai 누락");
    if (/(Samsung|삼성)/.test(text)) ok("T4.4", "Samsung 보임");
    else fail("T4.4", "Samsung 누락");
    if (/\bLG\b/.test(text)) ok("T4.5", "LG 보임");
    else fail("T4.5", "LG 누락");
  } else {
    fail("T4.2", "country chip for 대한민국 not found");
  }

  // ── T5: HOT sort ──
  log("\n[5] HOT sort");
  const hotBtn = page.locator(".sf-chip[data-sort='hot']").first();
  if (await hotBtn.count() > 0) {
    await hotBtn.click();
    await page.waitForTimeout(300);
    const first = await page.locator(".browse-grid .feat-card").first().textContent({ timeout: 5000 });
    log(`  HOT sort 1st card: ${(first||'').slice(0, 100)}`);
    ok("T5.1", "HOT sort applied");
  } else fail("T5.1", "HOT sort button not found");

  // ── T6: Detail drawer (#drawer not [role=dialog]) ──
  log("\n[6] Detail drawer");
  await page.goto(BASE + "/#cat/business", { waitUntil: "networkidle" });
  await page.waitForTimeout(800);
  // Click first card
  const firstCard = page.locator(".browse-grid .feat-card").first();
  if (await firstCard.count() > 0) {
    await firstCard.click();
    await page.waitForTimeout(1500);
    const drawer = page.locator("#drawer");
    const drawerHidden = await drawer.getAttribute("hidden");
    if (drawerHidden === null) {
      ok("T6.1", "drawer opened (hidden attr removed)");
      const body = await page.locator("#drawer-content").textContent({ timeout: 3000 });
      log(`  drawer body length: ${(body||'').length}`);
    } else fail("T6.1", "drawer still hidden after click");
  } else fail("T6.1", "no card to click");

  // ── T7: Search ──
  log("\n[7] Search");
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.locator("#q").fill("Bezos");
  await page.waitForTimeout(500);
  const popHidden = await page.locator("#search-pop").getAttribute("hidden");
  if (popHidden === null) ok("T7.1", "search popup visible");
  else fail("T7.1", "search popup not visible");
  const sugCount = await page.locator("#search-pop li").count();
  if (sugCount > 0) ok("T7.2", `${sugCount} suggestions for 'Bezos'`);
  else fail("T7.2", "0 suggestions for 'Bezos'");

  // Try 삼성 (Korean search)
  await page.locator("#q").fill("삼성");
  await page.waitForTimeout(500);
  const sug2 = await page.locator("#search-pop li").count();
  if (sug2 > 0) ok("T7.3", `${sug2} suggestions for '삼성'`);
  else fail("T7.3", "0 suggestions for '삼성'");

  // ── T8: /f/ ──
  log("\n[8] /f/ static SEO");
  const r1 = await page.goto(BASE + "/f/", { waitUntil: "domcontentloaded" });
  if (r1?.status() === 200) ok("T8.1", "/f/ index 200");
  else fail("T8.1", `/f/ returned ${r1?.status()}`);
  // Pick a known QID
  const r2 = await page.goto(BASE + "/f/q165687.html");
  if (r2?.status() === 200 || r2?.status() === 308) ok("T8.2", `/f/q165687.html → ${r2?.status()}`);
  else fail("T8.2", `/f/q165687.html → ${r2?.status()}`);

  // ── T9: Mobile ──
  log("\n[9] Mobile viewport");
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.waitForTimeout(500);
  const docWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  if (docWidth <= 380) ok("T9.1", `no horizontal scroll (${docWidth}px)`);
  else fail("T9.1", `horizontal scroll on home: width=${docWidth}px`);

  // Also test mobile browse page
  await page.goto(BASE + "/#cat/business");
  await page.waitForTimeout(800);
  const browseW = await page.evaluate(() => document.documentElement.scrollWidth);
  if (browseW <= 380) ok("T9.2", `mobile browse no overflow (${browseW}px)`);
  else fail("T9.2", `mobile browse overflow! width=${browseW}px`);

  // ── T10: 모든 카테고리 browse 확인 ──
  log("\n[10] 모든 카테고리 browse");
  await page.setViewportSize({ width: 1280, height: 800 });
  for (const cat of ["business","royal","noble","clan","political","religious","tribal","unknown"]) {
    await page.goto(BASE + "/#cat/" + cat, { waitUntil: "networkidle" });
    await page.waitForTimeout(400);
    const count = await page.locator(".browse-grid .feat-card").count();
    if (count > 0) ok(`T10.${cat}`, `${count} cards`);
    else fail(`T10.${cat}`, "0 cards");
  }

  // ── XX ──
  log("\n[X] Console / network");
  if (consoleErrors.length === 0) ok("XX.1", "no console errors");
  else for (const e of consoleErrors.slice(0, 5)) fail("XX.console", e.slice(0, 100));
  if (failedRequests.length === 0) ok("XX.2", "no failed requests");
  else for (const r of failedRequests.slice(0, 5)) fail("XX.req", r.slice(0, 120));

  log("\n=========================================");
  log(`Total issues: ${issues.length}`);
  if (issues.length) {
    log("\n❌ FAILED:");
    for (const i of issues) log(`  • ${i.id}: ${i.desc}`);
  } else {
    log("\n✅ ALL PASS");
  }
  await browser.close();
  process.exit(issues.length ? 1 : 0);
}
main().catch(e => { console.error("\n💥 FATAL:", e.message); process.exit(2); });
