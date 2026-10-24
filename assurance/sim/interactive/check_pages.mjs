#!/usr/bin/env node
// Open every interactive page headless and check it (CI, job "simulation interactive pages"):
//   - it loads and renders with no page error;
//   - it carries the synthetic stamp;
//   - the numbers it shows are the committed results: the page's own targets() at several settings equal an
//     independent interpolation of the results file done here.
//   npm i --no-save --prefix assurance/sim/interactive playwright@1.56.1 && node assurance/sim/interactive/check_pages.mjs
import { createServer } from 'node:http'
import { readFileSync } from 'node:fs'
import { dirname, join, normalize } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const here = dirname(fileURLToPath(import.meta.url))
const results = join(here, '..', 'results')
const interp = (xs, ys, x) => {
  if (x <= xs[0]) return ys[0]
  for (let i = 1; i < xs.length; i++) if (x <= xs[i]) return ys[i - 1] + (ys[i] - ys[i - 1]) * (x - xs[i - 1]) / (xs[i] - xs[i - 1])
  return ys[ys.length - 1]
}

// page -> settings to probe and what the results file says at each
const PAGES = {
  comma3x: () => {
    const r = JSON.parse(readFileSync(join(results, 'mcu-heat.json'), 'utf8'))
    const probe = []
    for (const broken of [false, true]) for (const a of [25, 37.5, 50, 63]) {
      const s = r.setups[broken ? 'fan_stalled' : 'as_built']
      probe.push({ args: [a, broken], want: { soc: interp(r.air, s.soc, a), mcu: interp(r.air, s.mcu_block, a) + r.junction_rise_k.nominal } })
    }
    return probe
  },
}

const server = createServer((req, res) => {
  const p = normalize(decodeURIComponent(new URL(req.url, 'http://x').pathname)).replace(/^(\.\.[/\\])+/, '')
  try { res.writeHead(200, { 'content-type': p.endsWith('.html') ? 'text/html' : 'application/octet-stream' }); res.end(readFileSync(join(here, p))) }
  catch { res.writeHead(404); res.end() }
}).listen(0, '127.0.0.1')
await new Promise((ok) => server.once('listening', ok))
const base = `http://127.0.0.1:${server.address().port}`

const browser = await chromium.launch({ headless: true, args: ['--enable-unsafe-swiftshader', '--use-angle=swiftshader'] })
let fails = 0
for (const [name, probes] of Object.entries(PAGES)) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } })
  const errors = []
  page.on('pageerror', (e) => errors.push(e.message.split('\n')[0]))
  await page.goto(`${base}/${name}.html`, { waitUntil: 'load', timeout: 120000 })
  await page.waitForFunction(() => window.__lab?.renderer && window.__ld, null, { timeout: 120000 })
  await page.waitForTimeout(3000)                                        // a few frames
  const stamp = await page.textContent('#ld-stamp')
  if (!stamp?.includes('SYNTHETIC (DSR-12)')) { console.log(`FAIL ${name}: no synthetic stamp`); fails++ }
  for (const { args, want } of probes()) {
    const got = await page.evaluate((a) => window.__ld.targets(...a), args)
    for (const k of Object.keys(want)) {
      if (Math.abs(got[k] - want[k]) > 1e-9) { console.log(`FAIL ${name}: ${k} at ${JSON.stringify(args)} is ${got[k]}, the results say ${want[k]}`); fails++ }
    }
  }
  const info = await page.evaluate(() => ({ parts: window.__lab.parts.length, calls: window.__lab.renderer.info.render.calls }))
  if (!info.calls) { console.log(`FAIL ${name}: nothing rendered`); fails++ }
  for (const e of errors) { console.log(`FAIL ${name}: page error: ${e}`); fails++ }
  console.log(`${name}: ${info.parts} parts, ${errors.length} page errors, ${probes().length} settings checked`)
  await page.close()
}
await browser.close()
server.close()
console.log('interactive pages (browser):', fails ? `${fails} problem(s)` : 'OK')
process.exit(fails ? 1 : 0)
