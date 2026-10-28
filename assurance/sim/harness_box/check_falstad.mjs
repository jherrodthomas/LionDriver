// Harness box switch path: run every scenario's circuit in Falstad (CircuitJS) headless and compare its node voltages
// with the ngspice results committed in ../results/harness-box.json. Two solvers, one circuit (harness_box.py).
// Falstad is loaded from falstad.com; the page must serve the bundle named in BUNDLE, so a new Falstad release fails
// this check until it is reviewed. Presentation tool, no evidence credit (DSR-12, DQ-413).
//
//   node check_falstad.mjs            (needs playwright and Chromium)
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const HERE = dirname(fileURLToPath(import.meta.url));
const PAGE = 'https://www.falstad.com/circuit/circuitjs.html';
const BUNDLE = 'circuitjs114/circuitjs-DvPgaX9z.js';
const TOL_V = 0.005;

const results = JSON.parse(readFileSync(join(HERE, '../results/harness-box.json'), 'utf8'));
const browser = await chromium.launch();
const probe = await browser.newPage();
await probe.goto(PAGE, { waitUntil: 'domcontentloaded' });
const scripts = await probe.evaluate(() => [...document.scripts].map(s => s.getAttribute('src') || ''));
await probe.close();
if (!scripts.some(src => src.endsWith(BUNDLE))) {
  console.error(`check_falstad: ${PAGE} no longer serves ${BUNDLE}; review the new Falstad release and update BUNDLE`);
  await browser.close();
  process.exit(1);
}
const failures = [];
for (const s of results.scenarios) {
  const text = readFileSync(join(HERE, 'falstad', `${s.id}.txt`), 'utf8');
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(`${PAGE}?running=true&cct=${encodeURIComponent(text)}`, { waitUntil: 'load' });
  await page.waitForFunction(() => window.CircuitJS1 && window.CircuitJS1.getElements().length > 0, null, { timeout: 60000 });
  await page.waitForTimeout(1500);      // a resistive circuit settles on the first step; leave a margin
  const got = await page.evaluate(names => Object.fromEntries(names.map(n => [n, window.CircuitJS1.getNodeVoltage(n)])),
                                  Object.keys(s.nodes));
  for (const [n, want] of Object.entries(s.nodes)) {
    const ok = Math.abs(got[n] - want) <= TOL_V;
    if (!ok) failures.push(`${s.id} ${n}: Falstad ${got[n].toFixed(4)} V, ngspice ${want.toFixed(4)} V`);
  }
  if (errors.length) failures.push(`${s.id}: page error ${errors[0]}`);
  console.log(`${failures.some(f => f.startsWith(s.id)) ? 'DIFFERS' : 'agrees '} ${s.id}`);
  await page.close();
}
await browser.close();
if (failures.length) {
  console.error('check_falstad: Falstad and ngspice differ:\n  ' + failures.join('\n  '));
  process.exit(1);
}
console.log(`check_falstad: ${results.scenarios.length} scenarios agree within ${TOL_V * 1000} mV`);
