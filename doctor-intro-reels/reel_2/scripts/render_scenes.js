// Покадровый рендер HTML/SVG-сцен в Chromium (Playwright) → видео без потерь (FFV1).
// Время каждого кадра задаётся явно: render(t), t = i · 1001/60000 — анимация детерминирована.
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const cues = JSON.parse(fs.readFileSync(path.join(ROOT, "build", "cues.json"), "utf8")).scenes;
const only = process.argv.slice(2);
const stillsAt = (process.env.STILLS || "").split(",").filter(Boolean).map(Number);

(async () => {
  const browser = await chromium.launch();
  for (const [name, c] of Object.entries(cues)) {
    if (only.length && !only.includes(name)) continue;
    const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
    await page.addInitScript((c) => { window.CUES = c; }, c);
    await page.goto("file://" + path.join(ROOT, "scenes", `${name}.html`));
    await page.evaluate(() => document.fonts.ready);
    if (stillsAt.length) {
      for (const t of stillsAt) {
        await page.evaluate((t) => window.renderAt(t), t);
        await page.screenshot({ path: path.join(ROOT, "build", `scene_${name}_${t.toFixed(2)}.png`) });
      }
      await page.close();
      continue;
    }
    const n = Math.round(c.dur * 60000 / 1001) + 2;
    const out = path.join(ROOT, "build", `scene_${name}.mkv`);
    const ff = spawn("ffmpeg", ["-v", "error", "-y", "-f", "image2pipe", "-framerate", "60000/1001", "-i", "-",
      "-c:v", "ffv1", "-pix_fmt", "bgr0", out], { stdio: ["pipe", "inherit", "inherit"] });
    for (let i = 0; i < n; i++) {
      await page.evaluate((t) => window.renderAt(t), i * 1001 / 60000);
      const buf = await page.screenshot({ type: "png" });
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
    }
    ff.stdin.end();
    await new Promise((r) => ff.on("close", r));
    console.log(`${name}: ${n} кадров → ${out}`);
    await page.close();
  }
  await browser.close();
})();
