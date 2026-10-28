// Print the safety case snapshot HTML (build_snapshot.py) to PDF with headless Chromium.
//
// Usage: node assurance/case-records/tools/render_snapshot.cjs <dir>
//   reads <dir>/LionDriver-safety-case.html and <dir>/manifest.json, writes <dir>/LionDriver-safety-case.pdf
//
// Every page carries the running header and footer from manifest.json (build_snapshot.running_header):
// document, version, snapshot ID and status at the top; configuration, commit, pins, baseline, issue
// time, copy and retention at the bottom, with a QR code of the verification URL and "page x / y".
// Needs the `playwright` package and its Chromium; the QR code needs the `qrcode` package and is left
// out, with the URL printed instead, when that package is missing.
const { chromium } = require('playwright');
const { readFileSync } = require('node:fs');
const { join, resolve } = require('node:path');
const { pathToFileURL } = require('node:url');

const dir = resolve(process.argv[2] ?? 'build/snapshot');
const manifest = JSON.parse(readFileSync(join(dir, 'manifest.json'), 'utf8'));
const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const font = 'font-family:Inter,Helvetica,Arial,sans-serif;color:#475569;width:100%;padding:0 16mm;';
const h = manifest.header;
const ink = (text) => `<b style="color:#0F172A">${esc(text)}</b>`;
const statusColor = manifest.release_status && manifest.release_status.approved ? '#2E9E6A' : '#C2410C';

async function qrDataUri(url) {
  let QR;
  try { QR = require('qrcode'); } catch { return null; }
  const svg = await QR.toString(url, { type: 'svg', margin: 0, errorCorrectionLevel: 'M', color: { dark: '#0F172A', light: '#FFFFFF' } });
  return 'data:image/svg+xml;base64,' + Buffer.from(svg).toString('base64');
}

(async () => {
const qr = await qrDataUri(h.verify);
const [status, ...rest] = String(h.right).split(' · ');
const header = `<div style="${font}font-size:7px;display:flex;justify-content:space-between;gap:8px">
  <span>${ink(h.left)}</span><span><b style="color:${statusColor}">${esc(status)}</b> · ${esc(rest.join(' · '))}</span></div>`;
const footer = `<div style="${font}font-size:6.5px;display:flex;justify-content:space-between;align-items:flex-end;gap:10px">
  <div style="line-height:1.45">${esc(h.footer)}<br>${esc(h.footer2)}<br>${esc(h.footer3)} · ${qr ? 'Scan to verify and check currency' : 'Verify and check currency at ' + esc(h.verify)}</div>
  <div style="display:flex;align-items:flex-end;gap:6px;white-space:nowrap">
    ${qr ? `<img src="${qr}" style="width:11mm;height:11mm" alt="">` : ''}
    <span><b style="color:#0F172A"><span class="pageNumber"></span></b> / <span class="totalPages"></span></span></div></div>`;
const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(pathToFileURL(join(dir, 'LionDriver-safety-case.html')).href, { waitUntil: 'load' });
await page.pdf({
  path: join(dir, 'LionDriver-safety-case.pdf'),
  format: 'A4',
  printBackground: true,
  preferCSSPageSize: true,
  displayHeaderFooter: true,
  headerTemplate: header,
  footerTemplate: footer,
  tagged: true,
  outline: true,
});
await browser.close();
console.log(`OK: wrote ${join(dir, 'LionDriver-safety-case.pdf')}${qr ? '' : ' (no qrcode package: URL printed instead of a QR code)'}`);
})().catch((err) => { console.error(err); process.exit(1); });
