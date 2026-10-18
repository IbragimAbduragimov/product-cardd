// Готовит templates/selftest: кладёт локальную копию GSAP и генерирует тестовое исходное видео.
import { copyFileSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const assets = join(root, "templates", "selftest", "assets");

const gsapSrc = join(root, "node_modules", "gsap", "dist", "gsap.min.js");
if (!existsSync(gsapSrc)) {
  console.error("gsap не найден — сначала выполните `npm install` в папке shorts-studio.");
  process.exit(1);
}
copyFileSync(gsapSrc, join(assets, "gsap.min.js"));

const source = join(assets, "source.mp4");
if (!existsSync(source)) {
  execFileSync(
    "ffmpeg",
    [
      "-hide_banner", "-loglevel", "error",
      "-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=30:duration=6",
      "-f", "lavfi", "-i", "sine=frequency=330:duration=6",
      "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
      source,
    ],
    { stdio: "inherit" },
  );
}
console.log("selftest готов:", assets);
