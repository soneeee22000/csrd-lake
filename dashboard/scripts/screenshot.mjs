/**
 * Screenshot runner for the CSRD-Lake dashboard.
 *
 * Captures all primary routes to public/screenshots/ at 1440x900 @2x for
 * crisp embedding in the project README and GitHub social preview.
 *
 * Usage (with dev server already running on :3000):
 *   pnpm dev &              # in another shell
 *   node scripts/screenshot.mjs
 */

import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(__dirname, "..", "public", "screenshots");

const ROUTES = [
  { url: "http://localhost:3000/", name: "home" },
  { url: "http://localhost:3000/company/MC.PA", name: "company-lvmh" },
  { url: "http://localhost:3000/company/TTE.PA", name: "company-totalenergies" },
  { url: "http://localhost:3000/portfolio", name: "portfolio" },
];

mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2, // retina-quality PNGs for the README
});
const page = await context.newPage();

for (const { url, name } of ROUTES) {
  await page.goto(url, { waitUntil: "networkidle", timeout: 15000 });
  // Hide the Next.js dev-tools indicator before snapshotting
  await page.addStyleTag({
    content: "[data-nextjs-toast], #__next-build-watcher, nextjs-portal { display: none !important; }",
  });
  const path = resolve(OUT, `${name}.png`);
  await page.screenshot({ path, fullPage: true, type: "png" });
  console.log(`Saved ${path}`);
}

await browser.close();
