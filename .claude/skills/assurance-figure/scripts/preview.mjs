#!/usr/bin/env node
// Render SVG figures to PNG so you can look at them before committing (Read the PNG to see it).
//
//   node .claude/skills/assurance-figure/scripts/preview.mjs <out-dir> fig-a.svg [fig-b.svg ...] [--width 390] [--at 6]
//
// --width  also renders at this CSS width (a phone is 390), scaled like an <img width="100%"> on a page
// --at     for animated SVGs (SMIL or CSS), the second of the loop to capture. Without it, SMIL animate elements are
//          removed first, so the PNG is the still frame a viewer that does not animate shows (it must be the end state)
// Uses the pre-installed Playwright Chromium. Writes <out-dir>/<name>.png (and <name>@<width>.png).
import { createRequire } from "node:module";
import { readFileSync, mkdirSync } from "node:fs";
import { basename, resolve } from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(name); if (i < 0) return null; const v = args[i + 1]; args.splice(i, 2); return v; };
const phone = opt("--width");
const at = opt("--at");
const [outDir, ...files] = args;
if (!outDir || !files.length) { console.error("usage: preview.mjs <out-dir> file.svg ... [--width 390] [--at s]"); process.exit(2); }
mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ deviceScaleFactor: 2 });
for (const f of files) {
  let src = readFileSync(resolve(f), "utf8");
  if (at === null) src = src.replace(/<animate(Transform|Motion)?\b[^>]*\/>/g, "");
  const m = src.match(/<svg[^>]*\bwidth="([\d.]+)"[^>]*\bheight="([\d.]+)"/) || src.match(/viewBox="0 0 ([\d.]+) ([\d.]+)"/);
  const [w, h] = m ? [Math.ceil(+m[1]), Math.ceil(+m[2])] : [1200, 800];
  for (const width of [w, phone ? +phone : null].filter(Boolean)) {
    const height = Math.ceil(h * width / w);
    await page.setViewportSize({ width, height });
    await page.setContent(`<!doctype html><html><body style="margin:0;background:#fff">` +
      `<div style="width:${width}px">${src.replace(/<svg/, '<svg style="width:100%;height:auto;display:block"')}</div></body></html>`);
    await page.evaluate((t) => {
      // every <svg>, nested ones included, keeps its own SMIL clock in an HTML page
      document.querySelectorAll("svg").forEach((s) => { if (s.pauseAnimations) { s.pauseAnimations(); if (t !== null) s.setCurrentTime(+t); } });
      if (t !== null) document.getAnimations().forEach((a) => { a.pause(); a.currentTime = +t * 1000; });
    }, at);
    const name = basename(f).replace(/\.svg$/, "") + (width === w ? "" : `@${width}`) + (at !== null ? `-t${at}` : "");
    await page.screenshot({ path: `${outDir}/${name}.png`, fullPage: true });
    console.log(`${outDir}/${name}.png  (${width} x ${height})`);
  }
}
await browser.close();
