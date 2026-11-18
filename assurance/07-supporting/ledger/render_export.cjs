// Print exported work products (export_wp.py --format pdf) to PDF with headless Chromium.
//
// Usage: node assurance/07-supporting/ledger/render_export.cjs <file.html> [...]
//   reads <name>.html and <name>.footer.txt, writes <name>.pdf, then removes the .footer.txt
//
// Every page carries the running footer from export_wp.py (ID, version, status, commit, copy) and "Page n of N",
// so a single printed page still says which document, version and copy it belongs to (WP-P-04 OI-7).
// Needs the `playwright` package and its Chromium.
const { chromium } = require('playwright');
const { readFileSync, unlinkSync } = require('node:fs');
const { resolve } = require('node:path');
const { pathToFileURL } = require('node:url');

const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const font = 'font-family:Inter,Helvetica,Arial,sans-serif;color:#475569;width:100%;padding:0 16mm;font-size:7px;';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (const arg of process.argv.slice(2)) {
    const html = resolve(arg);
    const footerFile = html.replace(/\.html$/, '.footer.txt');
    const [left, right] = readFileSync(footerFile, 'utf8').trim().split(' | ');
    const footer = `<div style="${font}display:flex;justify-content:space-between;gap:10px;border-top:0.5px solid #CBD5E1;padding-top:3px">
      <span><b style="color:#0F172A">${esc(left)}</b></span><span>${esc(right)}</span>
      <span style="white-space:nowrap">Page <b style="color:#0F172A"><span class="pageNumber"></span></b> of <span class="totalPages"></span></span></div>`;
    await page.goto(pathToFileURL(html).href, { waitUntil: 'load' });
    await page.pdf({
      path: html.replace(/\.html$/, '.pdf'), format: 'A4', printBackground: true, preferCSSPageSize: true,
      displayHeaderFooter: true, headerTemplate: '<span></span>', footerTemplate: footer, tagged: true, outline: true,
    });
    unlinkSync(footerFile);
    console.log(`OK: wrote ${html.replace(/\.html$/, '.pdf')}`);
  }
  await browser.close();
})().catch((err) => { console.error(err); process.exit(1); });
