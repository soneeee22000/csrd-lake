/**
 * Record a navigation walkthrough GIF of the CSRD-Lake dashboard.
 *
 * Pipeline: Playwright records webm video → ffmpeg-static converts to a
 * palette-optimized GIF. No system ffmpeg install needed.
 *
 * Usage (with dev server already running on :3000):
 *   pnpm dev &
 *   node scripts/record-gif.mjs
 *
 * Output: public/screenshots/csrd-lake-dashboard.gif
 */

import { chromium } from "playwright";
import { spawnSync } from "node:child_process";
import { mkdirSync, existsSync, rmSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import ffmpegPath from "ffmpeg-static";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = resolve(__dirname, "..", "public", "screenshots");
const VIDEO_DIR = resolve(__dirname, "..", ".video-tmp");

mkdirSync(OUT_DIR, { recursive: true });
if (existsSync(VIDEO_DIR)) rmSync(VIDEO_DIR, { recursive: true });
mkdirSync(VIDEO_DIR, { recursive: true });

const VIEWPORT = { width: 1280, height: 800 };
const FPS = 10;          // 10 → smooth-enough nav at <5MB target
const GIF_WIDTH = 720;   // README sidebar friendly; -1 height auto-scales

console.log("→ Launching headless chromium…");
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: VIEWPORT,
  recordVideo: { dir: VIDEO_DIR, size: VIEWPORT },
});
const page = await context.newPage();

console.log("→ Recording navigation…");

// Hide Next.js dev-tools indicator throughout
const HIDE_DEV_TOOLS = `
  [data-nextjs-toast], #__next-build-watcher, nextjs-portal,
  [data-nextjs-toast-wrapper] { display: none !important; }
`;

async function gotoAndStyle(url) {
  await page.goto(url, { waitUntil: "networkidle" });
  await page.addStyleTag({ content: HIDE_DEV_TOOLS });
  await page.waitForTimeout(800);
}

async function smoothScroll(distance, durationMs) {
  await page.evaluate(
    ([dist, dur]) =>
      new Promise((finish) => {
        const start = window.scrollY;
        const startTime = performance.now();
        const step = (now) => {
          const t = Math.min(1, (now - startTime) / dur);
          // ease-in-out cubic
          const eased =
            t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
          window.scrollTo(0, start + dist * eased);
          if (t < 1) requestAnimationFrame(step);
          else finish();
        };
        requestAnimationFrame(step);
      }),
    [distance, durationMs],
  );
}

// Home — quick pause, scroll through company grid
await gotoAndStyle("http://localhost:3000/");
await page.waitForTimeout(900);
await smoothScroll(600, 1500);
await page.waitForTimeout(500);

// Company page — pause, scroll through ESRS topic tables
await gotoAndStyle("http://localhost:3000/company/MC.PA");
await page.waitForTimeout(900);
await smoothScroll(800, 1700);
await page.waitForTimeout(500);

// Portfolio page — pause, scroll through breakdown table
await gotoAndStyle("http://localhost:3000/portfolio");
await page.waitForTimeout(900);
await smoothScroll(600, 1500);
await page.waitForTimeout(700);

console.log("→ Closing browser, saving webm…");
await context.close();
await browser.close();

// Find the recorded webm file
const { readdirSync } = await import("node:fs");
const webms = readdirSync(VIDEO_DIR).filter((f) => f.endsWith(".webm"));
if (webms.length === 0) {
  throw new Error(`No webm produced in ${VIDEO_DIR}`);
}
const webmPath = resolve(VIDEO_DIR, webms[0]);
console.log(`→ Webm ready: ${webmPath}`);

// Convert with ffmpeg-static, two-pass for palette optimization
const gifPath = resolve(OUT_DIR, "csrd-lake-dashboard.gif");
const palettePath = resolve(VIDEO_DIR, "palette.png");

console.log("→ ffmpeg pass 1 — generate optimized palette…");
const passOne = spawnSync(
  ffmpegPath,
  [
    "-y",
    "-i",
    webmPath,
    "-vf",
    `fps=${FPS},scale=${GIF_WIDTH}:-1:flags=lanczos,palettegen=stats_mode=diff`,
    palettePath,
  ],
  { stdio: "inherit" },
);
if (passOne.status !== 0) {
  throw new Error(`ffmpeg palette pass failed (exit ${passOne.status})`);
}

console.log("→ ffmpeg pass 2 — encode GIF using palette…");
const passTwo = spawnSync(
  ffmpegPath,
  [
    "-y",
    "-i",
    webmPath,
    "-i",
    palettePath,
    "-lavfi",
    `fps=${FPS},scale=${GIF_WIDTH}:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle`,
    gifPath,
  ],
  { stdio: "inherit" },
);
if (passTwo.status !== 0) {
  throw new Error(`ffmpeg gif pass failed (exit ${passTwo.status})`);
}

// Cleanup the webm tmp dir
rmSync(VIDEO_DIR, { recursive: true });

const { statSync } = await import("node:fs");
const sizeMb = (statSync(gifPath).size / 1024 / 1024).toFixed(2);
console.log(`✓ GIF ready: ${gifPath} (${sizeMb} MB)`);
