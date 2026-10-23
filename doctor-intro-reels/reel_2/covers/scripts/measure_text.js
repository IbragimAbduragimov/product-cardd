// Замер текста обложек: каждый слой (за фигурой / перед ней) отдельно, на прозрачном фоне.
// node scripts/measure_text.js <папка> [номера] → <папка>/text_NN_{behind,front}.png
const { chromium } = require("playwright");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const [dir, ...nums] = process.argv.slice(2);
const only = nums.map(Number);

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto("file://" + path.join(ROOT, "cover.html"));
  const variants = await page.evaluate(() => window.VARIANTS);
  for (const n of variants) {
    if (only.length && !only.includes(n)) continue;
    await page.evaluate((n) => window.setVariant(n), n);
    for (const layer of ["behind", "front"]) {
      await page.evaluate((l) => window.measure(l), layer);
      await page.screenshot({ path: path.join(dir, `text_${String(n).padStart(2, "0")}_${layer}.png`), omitBackground: true });
    }
    await page.evaluate(() => window.unmeasure());
  }
  await browser.close();
})();
