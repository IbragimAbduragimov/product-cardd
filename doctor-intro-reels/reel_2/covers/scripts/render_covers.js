// Рендер вариантов обложки (Playwright + Chromium) → PNG 1080×1920.
const { chromium } = require("playwright");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const only = process.argv.slice(2).map(Number);

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto("file://" + path.join(ROOT, "cover.html"));
  const variants = await page.evaluate(() => window.VARIANTS);
  for (const n of variants) {
    if (only.length && !only.includes(n)) continue;
    await page.evaluate((n) => window.setVariant(n), n);
    await page.waitForTimeout(80);
    await page.screenshot({ path: path.join(ROOT, "output", `cover_${String(n).padStart(2, "0")}.png`) });
    console.log("обложка", n);
  }
  await browser.close();
})();
