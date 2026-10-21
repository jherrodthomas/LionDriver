#!/usr/bin/env python3
"""Write the FMEDA what-if page: a phone page that recomputes SPFM, LFM and λSPF+λRF per goal while rates and DC change.

Usage: tools/safety/fmeda_whatif.py --out <file.html>

The page embeds a snapshot of analyses/fmeda-*.yaml and computes the metrics in the browser with the same rules as
fmea_lint.fmeda_metrics (rating-tables §6.1, per_goal classification). It changes nothing in the repository: a value
worth keeping goes into the YAML through a pull request. The page is published as a private claude.ai page (URL in
fmeda_review_md.WHAT_IF, https://claude.ai/artifact/6btZjojvGtcyZdYrhzsR8Z); rebuild and republish it to that URL when an FMEDA file changes.

The scenarios are the planned measures of WP-H-03 §6.3 with the DC values stated there. test_fmea_lint checks that
they reproduce the §6.3 results through fmea_lint.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fmea_lint  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ANALYSES = ROOT / "assurance/08-analyses/fmea/analyses"
SOURCES = ("fmeda-sg001", "fmeda-sg009")

# Planned measures of WP-H-03 §6.3: row -> DC. Assumed values for the estimate, not claims.
SCENARIOS = [
  {"file": "fmeda-sg001", "id": "bor", "label": "Brown-out / PVD reaction", "ref": "DFM-ACT-005", "sets": {"FMD-015": 0.9}},
  {"file": "fmeda-sg001", "id": "ramecc", "label": "RAM ECC double-error reaction", "ref": "DFM-ACT-002", "sets": {"FMD-009": 0.9}},
  {"file": "fmeda-sg001", "id": "clock", "label": "Clock cross-check", "ref": "DFM-ACT-004", "sets": {"FMD-013": 0.9}},
  {"file": "fmeda-sg001", "id": "cpu", "label": "Low-coverage CPU self-test", "ref": "DFM-ACT-001, DQ-069", "sets": {"FMD-001": 0.6}},
  {"file": "fmeda-sg001", "id": "txrb", "label": "TX read-back", "ref": "TSR-517", "sets": {"FMD-002": 0.99, "FMD-010": 0.99}},
  {"file": "fmeda-sg009", "id": "readback", "label": "Switch position readback", "ref": "DFM-ACT-007, DC-03",
   "sets": {"FMD-019": 0.9, "FMD-020": 0.9}},
  {"file": "fmeda-sg009", "id": "xcvr", "label": "Release the switch on a transceiver fault", "ref": "DFM-ACT-006",
   "sets": {"FMD-016": 0.9, "FMD-017": 0.9}},
  {"file": "fmeda-sg009", "id": "continuity", "label": "Stock-path continuity check", "ref": "WP-H-03 §6.3",
   "sets": {"FMD-022": 0.9, "FMD-023": 0.9}},
]


def scenario_doc(doc: dict, sets: dict[str, float]) -> dict:
  """doc with the given rows covered at the given DC (a planned mechanism where the row has none)."""
  out = json.loads(json.dumps(doc))
  for c in out["components"]:
    for fm in c["failure_modes"]:
      if fm["id"] in sets:
        key, dck = ("safety_mechanism_spf", "dc_spf") if fm["violates_sg_directly"] else ("safety_mechanism_lf", "dc_lf")
        fm[key], fm[dck] = fm.get(key) or "planned", sets[fm["id"]]
  return out


def snapshot() -> dict:
  files = {}
  for name in SOURCES:
    doc = fmea_lint.load_yaml((ANALYSES / f"{name}.yaml").read_text())
    a = doc["analysis"]
    comps = []
    for c in doc["components"]:
      rows = []
      for fm in c["failure_modes"]:
        rows.append({"id": fm["id"], "mode": " ".join(fm["mode"].split()), "dist": fm["distribution"],
                     "vd": fm["violates_sg_directly"], "mpf": fm["mpf_potential"],
                     "smS": fm.get("safety_mechanism_spf"), "dcS": fm.get("dc_spf", 0.0),
                     "smL": fm.get("safety_mechanism_lf"), "dcL": fm.get("dc_lf", 0.0),
                     "pg": [{k: v for k, v in pg.items()} for pg in fm.get("per_goal", [])]})
      comps.append({"id": c["id"], "part": " ".join(c["part"].split()), "lam": c["failure_rate_fit"], "sr": c["safety_related"],
                    "kind": c.get("rate_kind", ""), "rows": rows})
    files[name] = {"title": a["title"], "revision": a["revision"], "updated": str(a.get("updated", "")),
                   "targets": [{"goal": g, "asil": s, "also": list(also)} for g, s, also in fmea_lint.fmeda_targets(doc)],
                   "components": comps}
  return {"files": files, "targets": {k: list(v) for k, v in fmea_lint.FMEDA_TARGETS.items()},
          "scenarios": SCENARIOS}


PAGE = r"""<title>FMEDA What-If</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans+Condensed:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
/* Layout: one column instrument panel; goal selector, three meters, then levers (measures, rates, rows). */
:root{
  --bg:#F3F5F7; --panel:#FFFFFF; --ink:#14202B; --muted:#5A6B7A; --line:#D9E0E6; --track:#E7ECF0;
  --accent:#1F6F8B; --accent-ink:#FFFFFF; --ok:#B86A00; --ok-soft:#FFF3E0; --bad:#C2412F; --bad-soft:#FBE9E6;
  --base:#7C8C99; --chip:#EEF2F5;
  --f-display:"IBM Plex Sans Condensed","Arial Narrow",Arial,sans-serif;
  --f-body:"IBM Plex Sans","Segoe UI",Helvetica,Arial,sans-serif;
  --f-mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#0F161C; --panel:#162029; --ink:#E6EDF2; --muted:#93A4B2; --line:#26333E; --track:#22303B;
  --accent:#5DB4D1; --accent-ink:#0B1318; --ok:#F0A43A; --ok-soft:#2B2213; --bad:#F07A66; --bad-soft:#331C18;
  --base:#8798A6; --chip:#1E2A34; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0F161C; --panel:#162029; --ink:#E6EDF2; --muted:#93A4B2; --line:#26333E; --track:#22303B;
  --accent:#5DB4D1; --accent-ink:#0B1318; --ok:#F0A43A; --ok-soft:#2B2213; --bad:#F07A66; --bad-soft:#331C18;
  --base:#8798A6; --chip:#1E2A34; color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font:15px/1.5 var(--f-body);margin:0}
.wrap{max-width:860px;margin:0 auto;padding-block:20px 48px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:18px}
h1{font:700 26px/1.15 var(--f-display);margin:0;letter-spacing:.01em;text-wrap:balance}
h2{font:600 13px/1.2 var(--f-display);text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:0 0 10px}
.sub{color:var(--muted);font-size:13px;margin-top:4px}
.warn{border:1px dashed var(--ok);background:var(--ok-soft);color:var(--ink);border-radius:8px;padding:10px 12px;font-size:13px}
.goals{display:flex;flex-wrap:wrap;gap:8px}
.goal{font:600 14px var(--f-mono);border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:999px;padding:7px 12px;cursor:pointer;min-height:40px}
.goal small{font:500 12px var(--f-body);color:var(--muted);margin-left:4px}
.goal[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.goal[aria-pressed="true"] small{color:var(--accent-ink)}
.goal:focus-visible,button:focus-visible,input:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
.verdicts{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.pill{font:600 12px var(--f-body);border-radius:999px;padding:4px 10px;border:1px solid transparent}
.pill.ok{color:var(--ok);background:var(--ok-soft);border-color:var(--ok)}
.pill.bad{color:var(--bad);background:var(--bad-soft);border-color:var(--bad)}
.meters{display:grid;gap:14px}
.meter{display:grid;grid-template-columns:110px 1fr;gap:4px 12px;align-items:center}
.meter .name{font:700 15px var(--f-display)}
.meter .def{grid-column:1;font-size:11px;color:var(--muted);line-height:1.3}
.meter .val{font:600 20px var(--f-mono);font-variant-numeric:tabular-nums}
.meter .delta{font:500 12px var(--f-mono);color:var(--muted);margin-left:8px}
.bar{position:relative;height:16px;background:var(--track);border-radius:4px;margin:22px 0 18px}
.bar .fill{position:absolute;inset:0 auto 0 0;border-radius:4px}
.bar .base{position:absolute;top:-4px;bottom:-4px;width:0;border-left:2px solid var(--base)}
.bar .tick{position:absolute;top:-6px;bottom:-6px;width:0;border-left:2px dashed var(--ink)}
.bar .tl{position:absolute;top:-22px;transform:translateX(-50%);font:600 11px var(--f-mono);white-space:nowrap}
.bar .ax{position:absolute;bottom:-17px;font:400 10px var(--f-mono);color:var(--muted)}
.legend{font-size:12px;color:var(--muted)}
.legend i{display:inline-block;width:10px;height:10px;border-left:2px solid var(--base);margin-right:4px;vertical-align:-1px}
.toggles{display:grid;gap:8px}
.toggle{display:flex;gap:10px;align-items:flex-start;padding:8px;border-radius:8px;border:1px solid var(--line);cursor:pointer}
.toggle input{width:20px;height:20px;margin-top:1px;accent-color:var(--accent);flex:none}
.toggle b{font-weight:600}
.toggle .rf{color:var(--muted);font-size:12px;display:block}
.sliders{display:grid;gap:14px}
.slider label{display:flex;justify-content:space-between;gap:8px;font-size:14px}
.slider output{font:600 14px var(--f-mono)}
.slider input{width:100%;accent-color:var(--accent)}
details.comp{border-top:1px solid var(--line);padding:8px 0}
details.comp summary{cursor:pointer;display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;list-style:none;min-height:32px}
details.comp summary::-webkit-details-marker{display:none}
summary .cid{font:600 13px var(--f-mono)}
summary .cl{color:var(--muted);font-size:13px;flex:1;min-width:0}
summary .lam{font:600 13px var(--f-mono)}
.lamrow{display:flex;gap:8px;align-items:center;margin:6px 0 8px;font-size:13px;color:var(--muted)}
input[type=number]{font:600 14px var(--f-mono);width:92px;padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--ink)}
.rows{display:grid;gap:6px}
.row{display:grid;grid-template-columns:72px 1fr auto;gap:4px 10px;align-items:center;font-size:13px;padding:6px 8px;border-radius:6px;background:var(--chip)}
.row .rid{font:600 12px var(--f-mono)}
.row .mode{min-width:0}
.row .cls{font:600 11px var(--f-mono);border-radius:4px;padding:2px 6px;white-space:nowrap}
.cls.SPF{background:var(--bad);color:var(--panel)} .cls.RF{background:var(--bad-soft);color:var(--bad)}
.cls.latent{background:var(--ok-soft);color:var(--ok)} .cls.safe{color:var(--muted)}
.row .dc{grid-column:2 / 4;display:flex;gap:6px;align-items:center;color:var(--muted);font-size:12px}
.row .dc input{width:74px;font-size:13px;padding:4px 6px}
.row.changed{outline:2px solid var(--accent)}
.changes{font:13px/1.45 var(--f-mono);white-space:pre-wrap;background:var(--chip);border-radius:8px;padding:10px;margin:0;min-height:40px;overflow-x:auto}
.btns{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
button.b{font:600 14px var(--f-body);border-radius:8px;padding:9px 14px;border:1px solid var(--accent);background:var(--accent);color:var(--accent-ink);cursor:pointer;min-height:40px}
button.b.ghost{background:transparent;color:var(--accent)}
.note{font-size:12px;color:var(--muted)}
@media (max-width:520px){.meter{grid-template-columns:1fr}.meter .def{grid-column:1}}
@media (prefers-reduced-motion: no-preference){.bar .fill{transition:width .25s ease}}
</style>
<div class="wrap">
  <header>
    <h1>FMEDA What-If</h1>
    <div class="sub" id="snap"></div>
  </header>
  <div class="warn">Generic order-of-magnitude rates for most parts. Numbers here show direction, not compliance, and nothing you change is saved to the analysis. To keep a value, copy the changes below into a request.</div>
  <section>
    <h2>Safety goal</h2>
    <div class="goals" id="goals" role="group" aria-label="Safety goal"></div>
  </section>
  <section class="panel" aria-live="polite">
    <h2 id="mtitle">Metrics</h2>
    <div class="verdicts" id="verdicts"></div>
    <div class="meters" id="meters"></div>
    <div class="legend"><i></i>grey mark: value in the committed analysis · dashed: ASIL targets for this goal</div>
  </section>
  <section class="panel">
    <h2>Planned measures (WP-H-03 §6.3)</h2>
    <div class="toggles" id="toggles"></div>
    <p class="note">Each adds the DC stated in §6.3 to its rows. They are assumptions for the estimate, not claims.</p>
  </section>
  <section class="panel">
    <h2>Failure rates</h2>
    <div class="sliders" id="sliders"></div>
  </section>
  <section class="panel">
    <h2>Every row</h2>
    <p class="note">Change a component's λ or a row's DC. A DC on a row without a mechanism stands for a planned one.</p>
    <div id="comps"></div>
  </section>
  <section class="panel">
    <h2>Your changes</h2>
    <pre class="changes" id="changes"></pre>
    <div class="btns"><button class="b" id="copy" type="button">Copy changes</button><button class="b ghost" id="reset" type="button">Reset to the analysis</button></div>
    <p class="note" id="copied" hidden>Copied. Paste it into a message or a pull request comment.</p>
  </section>
  <p class="note">Same rules as <code>tools/safety/fmea_lint.py</code> (rating-tables §6.1, per-goal classification). λSPF + λRF is the single-point and residual part of PMHF only; the dual-point term is not computed. Built by <code>tools/safety/fmeda_whatif.py</code>.</p>
</div>
<script>
const DATA = __DATA__;
const KEY = "fmeda-whatif:" + Object.values(DATA.files).map(f => f.revision).join("/");
const T = DATA.targets;
const goals = [];
for (const [file, f] of Object.entries(DATA.files)) for (const t of f.targets) goals.push({...t, file});
let st = {goal: goals[0].goal, lam: {}, dc: {}, on: {}};
try { const s = JSON.parse(localStorage.getItem(KEY) || "null"); if (s && s.lam) st = {...st, ...s}; } catch (e) {}
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) {} };
const $ = id => document.getElementById(id);
const cur = () => goals.find(g => g.goal === st.goal) || goals[0];
const k = (file, id) => file + ":" + id;

function classified(r, goal) {
  const p = (r.pg || []).find(x => x.goal === goal);
  if (!p) return r;
  const o = {...r};
  if ("violates_sg_directly" in p) o.vd = p.violates_sg_directly;
  if ("mpf_potential" in p) o.mpf = p.mpf_potential;
  if ("safety_mechanism_spf" in p) o.smS = p.safety_mechanism_spf;
  if ("dc_spf" in p) o.dcS = p.dc_spf;
  if ("safety_mechanism_lf" in p) o.smL = p.safety_mechanism_lf;
  if ("dc_lf" in p) o.dcL = p.dc_lf;
  return o;
}
function scenarioDc(file, id) {
  let v;
  for (const s of DATA.scenarios) if (s.file === file && st.on[s.id] && id in s.sets) v = s.sets[id];
  return v;
}
// effective DC of a row as classified for the goal: your edit, else a planned measure, else the analysis
function dcOf(file, r, edits) {
  const own = r.vd ? (r.smS ? r.dcS : 0) : (r.mpf ? (r.smL ? r.dcL : 0) : 0);
  if (!edits) return own;
  const e = st.dc[k(file, r.id)];
  if (e !== undefined) return e;
  const s = scenarioDc(file, r.id);
  return s !== undefined ? s : own;
}
function lamOf(file, c, edits) {
  const e = edits ? st.lam[k(file, c.id)] : undefined;
  return e !== undefined ? e : c.lam;
}
function metrics(file, goal, edits) {
  let total = 0, spf = 0, rf = 0, lat = 0;
  for (const c of DATA.files[file].components) {
    if (!c.sr) continue;
    const lam = lamOf(file, c, edits);
    total += lam;
    for (const row of c.rows) {
      const r = classified(row, goal), l = lam * r.dist, dc = dcOf(file, r, edits);
      if (r.vd) { if (dc === 0) spf += l; else rf += l * (1 - dc); }
      else if (r.mpf) lat += l * (1 - dc);
    }
  }
  const rem = total - spf - rf;
  return {spfm: 1 - (spf + rf) / total, lfm: rem > 0 ? 1 - lat / rem : 1, pm: spf + rf, total};
}
function cls(file, row, goal) {
  const r = classified(row, goal), dc = dcOf(file, r, true);
  if (r.vd) return dc === 0 ? "SPF" : "RF";
  if (r.mpf) return "latent";
  return "safe";
}
const pct = v => (v * 100).toFixed(2) + " %";
const fit = v => v < 10 ? v.toFixed(2) : v.toFixed(1);

function renderGoals() {
  $("goals").innerHTML = goals.map(g =>
    `<button class="goal" type="button" aria-pressed="${g.goal === st.goal}" data-g="${g.goal}">${g.goal}<small>${g.asil}${g.also.length ? "/" + g.also.join("/") : ""}</small></button>`).join("");
}
function bar(v, base, lo, hi, ticks, fmt, worse, afmt) {
  const x = t => Math.max(0, Math.min(100, (t - lo) / (hi - lo) * 100));
  const ok = ticks.every(t => worse ? v < t.v : v >= t.v);
  const col = ok ? "var(--ok)" : "var(--bad)";
  const byV = {};
  for (const t of ticks) (byV[t.v] = byV[t.v] || []).push(t.a);
  const tk = Object.entries(byV).filter(([t]) => t >= lo && t <= hi).map(([t, a]) =>
    `<span class="tick" style="left:${x(+t)}%"></span><span class="tl" style="left:${x(+t)}%">${a.join("/")} ${fmt(+t)}</span>`).join("");
  return {html: `<div class="bar"><span class="fill" style="width:${x(v)}%;background:${col}"></span>${tk}` +
    `<span class="base" style="left:${x(base)}%"></span><span class="ax" style="left:0">${afmt(lo)}</span>` +
    `<span class="ax" style="right:0">${afmt(hi)}</span></div>`, col};
}
function render() {
  const g = cur(), f = DATA.files[g.file];
  const m = metrics(g.file, g.goal, true), b = metrics(g.file, g.goal, false);
  const asils = [g.asil, ...g.also];
  $("snap").textContent = `Snapshot of ${g.file}.yaml rev ${f.revision} (${f.updated}) · ${f.title}`;
  $("mtitle").textContent = `Metrics for ${g.goal}`;
  $("verdicts").innerHTML = asils.map(a => {
    const [s, l, p] = T[a];
    const miss = [];
    if (m.spfm < s) miss.push("SPFM"); if (m.lfm < l) miss.push("LFM"); if (m.pm >= p) miss.push("λSPF+λRF");
    return `<span class="pill ${miss.length ? "bad" : "ok"}">ASIL ${a}: ${miss.length ? "missed on " + miss.join(", ") : "met on this estimate"}</span>`;
  }).join("");
  const rows = [
    ["SPFM", "1 − (λSPF + λRF) / λ", m.spfm, b.spfm, 0.5, 1, asils.map(a => ({a, v: T[a][0]})), v => (v * 100).toFixed(0) + "%", false, pct],
    ["LFM", "1 − λlatent / (λ − λSPF − λRF)", m.lfm, b.lfm, 0.5, 1, asils.map(a => ({a, v: T[a][1]})), v => (v * 100).toFixed(0) + "%", false, pct],
    ["λSPF + λRF", "FIT; part of PMHF", m.pm, b.pm, 0, Math.max(...asils.map(a => T[a][2])) * 1.2, asils.map(a => ({a, v: T[a][2]})), v => "<" + v.toFixed(0), true, v => fit(v) + " FIT"],
  ];
  $("meters").innerHTML = rows.map(([n, d, v, bv, lo, hi, ticks, tf, worse, vf]) => {
    const r = bar(v, bv, lo, hi, ticks, tf, worse, n === "λSPF + λRF" ? (t => t.toFixed(0) + " FIT") : tf);
    const dl = v - bv, ds = Math.abs(dl) < 1e-9 ? "" : `<span class="delta">${dl > 0 ? "+" : "−"}${n === "λSPF + λRF" ? fit(Math.abs(dl)) : (Math.abs(dl) * 100).toFixed(2) + " pt"}</span>`;
    return `<div class="meter"><div class="name">${n}</div><div><span class="val" style="color:${r.col}">${vf(v)}</span>${ds}</div>` +
      `<div class="def">${d}</div><div>${r.html}</div></div>`;
  }).join("");
  $("toggles").innerHTML = DATA.scenarios.filter(s => s.file === g.file).map(s =>
    `<label class="toggle"><input type="checkbox" id="sc-${s.id}" data-s="${s.id}" ${st.on[s.id] ? "checked" : ""}>` +
    `<span><b>${s.label}</b><span class="rf">${s.ref} · ${Object.entries(s.sets).map(([r, d]) => r + " DC " + (d * 100) + " %").join(", ")}</span></span></label>`).join("");
  const big = f.components.filter(c => c.sr).sort((a, b2) => b2.lam - a.lam).slice(0, 3);
  const sw = f.components.find(c => /DG419|switch/i.test(c.part));
  const sl = [...big]; if (sw && !sl.includes(sw)) sl.push(sw);
  $("sliders").innerHTML = sl.map(c => {
    const v = lamOf(g.file, c, true), max = Math.max(c.lam * 5, 20);
    return `<div class="slider"><label for="sl-${c.id}"><span>${c.id} ${c.part.split(/[(:]/)[0]}</span><output>${fit(v)} FIT</output></label>` +
      `<input type="range" id="sl-${c.id}" data-c="${c.id}" min="${Math.min(c.lam / 10, 1)}" max="${max}" step="${max / 200}" value="${v}"></div>`;
  }).join("");
  $("comps").innerHTML = f.components.map(c => {
    const lam = lamOf(g.file, c, true);
    return `<details class="comp" data-c="${c.id}" ${openSet.has(c.id) ? "open" : ""}><summary><span class="cid">${c.id}</span><span class="cl">${c.part}${c.sr ? "" : " (not safety-related)"}</span><span class="lam">${fit(lam)} FIT</span></summary>` +
      `<div class="lamrow"><label for="lam-${c.id}">λ (FIT)</label><input type="number" id="lam-${c.id}" data-lam="${c.id}" min="0" step="any" value="${+lam.toFixed(4)}"><span>${c.kind || ""} rate</span></div>` +
      `<div class="rows">${c.rows.map(row => {
        const r = classified(row, g.goal), cl = cls(g.file, row, g.goal), dc = dcOf(g.file, r, true);
        const can = r.vd || r.mpf, changed = st.dc[k(g.file, row.id)] !== undefined;
        const mech = r.vd ? r.smS : r.smL;
        return `<div class="row${changed ? " changed" : ""}"><span class="rid">${row.id}</span><span class="mode">${row.mode}</span><span class="cls ${cl}">${cl}</span>` +
          (can ? `<span class="dc"><label for="dc-${row.id}">DC %</label><input type="number" id="dc-${row.id}" data-dc="${row.id}" min="0" max="100" step="any" value="${+(dc * 100).toFixed(2)}"><span>${mech || "no mechanism"}${(row.pg || []).some(p => p.goal === g.goal) ? " · classified for " + g.goal : ""}</span></span>` : "") + `</div>`;
      }).join("")}</div></details>`;
  }).join("");
  renderChanges();
}
const openSet = new Set();
function renderChanges() {
  const L = [];
  for (const s of DATA.scenarios) if (st.on[s.id]) L.push(`measure: ${s.label} (${s.ref}) on ${s.file}`);
  for (const [kk, v] of Object.entries(st.lam)) L.push(`rate: ${kk} = ${+v.toFixed(4)} FIT`);
  for (const [kk, v] of Object.entries(st.dc)) L.push(`DC: ${kk} = ${+(v * 100).toFixed(2)} %`);
  if (L.length) {
    const g = cur(), m = metrics(g.file, g.goal, true);
    L.push(`result for ${g.goal}: SPFM ${pct(m.spfm)}, LFM ${pct(m.lfm)}, λSPF+λRF ${fit(m.pm)} FIT`);
  }
  $("changes").textContent = L.length ? L.join("\n") : "No changes. The numbers above are those of the analysis.";
}
document.addEventListener("click", e => {
  const b = e.target.closest(".goal");
  if (b) { st.goal = b.dataset.g; save(); renderGoals(); render(); }
});
document.addEventListener("toggle", e => {
  if (e.target.matches("details.comp")) (e.target.open ? openSet.add : openSet.delete).call(openSet, e.target.dataset.c);
}, true);
document.addEventListener("change", e => {
  const t = e.target, g = cur();
  if (t.dataset.s) { st.on[t.dataset.s] = t.checked; }
  else if (t.dataset.lam) { const v = parseFloat(t.value); if (isFinite(v) && v >= 0) st.lam[k(g.file, t.dataset.lam)] = v; }
  else if (t.dataset.dc) { const v = parseFloat(t.value); if (isFinite(v) && v >= 0 && v <= 100) st.dc[k(g.file, t.dataset.dc)] = v / 100; }
  else return;
  save(); render();
});
document.addEventListener("input", e => {
  const t = e.target;
  if (!t.matches('input[type=range]')) return;
  st.lam[k(cur().file, t.dataset.c)] = parseFloat(t.value);
  save(); render();
  const n = document.getElementById(t.id); if (n) n.focus();
});
$("reset").addEventListener("click", () => { st = {goal: st.goal, lam: {}, dc: {}, on: {}}; save(); render(); });
$("copy").addEventListener("click", async () => {
  const text = $("changes").textContent;
  try { await navigator.clipboard.writeText(text); $("copied").hidden = false; }
  catch (e) { const r = document.createRange(); r.selectNodeContents($("changes")); const s = getSelection(); s.removeAllRanges(); s.addRange(r); }
});
renderGoals(); render();
</script>
"""


def main(argv=None) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--out", type=Path, required=True)
  args = ap.parse_args(argv)
  args.out.write_text(PAGE.replace("__DATA__", json.dumps(snapshot(), ensure_ascii=False)), encoding="utf-8")
  print(f"wrote {args.out}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
