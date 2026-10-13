// Print the safety case snapshot HTML (build_snapshot.py) to PDF with headless Chromium.
//
// Usage: node assurance/case/tools/render_snapshot.cjs <dir>
//   reads <dir>/LionDriver-safety-case.html and <dir>/manifest.json, writes <dir>/LionDriver-safety-case.pdf
//
// Every page carries the snapshot ID and status in the header, and the verification URL and
// "page x / y" in the footer, taken from manifest.json. Needs the `playwright` package and its Chromium.
const { chromium } = require('playwright');
const { readFileSync } = require('node:fs');
const { join, resolve } = require('node:path');
const { pathToFileURL } = require('node:url');

const dir = resolve(process.argv[2] ?? 'build/snapshot');
const manifest = JSON.parse(readFileSync(join(dir, 'manifest.json'), 'utf8'));
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const style = 'font-family:Inter,Helvetica,Arial,sans-serif;font-size:7px;color:#475569;width:100%;padding:0 16mm;display:flex;justify-content:space-between';
const h = manifest.header;

(async () => {
const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(pathToFileURL(join(dir, 'LionDriver-safety-case.html')).href, { waitUntil: 'load' });
await page.pdf({
  path: join(dir, 'LionDriver-safety-case.pdf'),
  format: 'A4',
  printBackground: true,
  preferCSSPageSize: true,
  displayHeaderFooter: true,
  headerTemplate: `<div style="${style}"><span><b style="color:#0F172A">${esc(h.left)}</b></span><span>${esc(h.right)}</span></div>`,
  footerTemplate: `<div style="${style}"><span>${esc(h.footer)}</span><span><b style="color:#0F172A"><span class="pageNumber"></span></b> / <span class="totalPages"></span></span></div>`,
  tagged: true,
  outline: true,
});
await browser.close();
console.log(`OK: wrote ${join(dir, 'LionDriver-safety-case.pdf')}`);
})().catch((err) => { console.error(err); process.exit(1); });
