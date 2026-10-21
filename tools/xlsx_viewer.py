#!/usr/bin/env python3
"""One-page spreadsheet viewer for every assurance workbook: tabs, frozen header and ID column, filters, search, detail.

GitHub shows an .xlsx only as a download. This reads every workbook under assurance/ (the cached values of their
formulas, so a workbook must be recalculated before it is committed, as its builder already does) and writes one
self-contained HTML page with the values embedded. The page is published as a private claude.ai page (URL below) and
opened from a phone or a laptop.

The published page has to follow the workbooks. xlsx_viewer.sha256 holds a fingerprint of the page as last built;
CI runs --check, which fails when a workbook or this tool changed and the page was not rebuilt. The fix is to rebuild
(which rewrites the fingerprint) and republish the page to the same URL.

Usage:
  tools/xlsx_viewer.py --out <file.html>     write the page and its fingerprint; then republish it to VIEWER_URL
  tools/xlsx_viewer.py --check               exit 1 if the fingerprint does not match a fresh build
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
FINGERPRINT = Path(__file__).with_name("xlsx_viewer.sha256")
VIEWER_URL = "https://claude.ai/artifact/WHMhKBZQywWzDetcTKaDe3"
# A readable name where the file name alone is not one; the others are named from their file.
TITLES = {
  "assurance/02-concept/hara/WP-C-03-hara-cartesian.xlsx": "WP-C-03 HARA (reference scope, Chill mode)",
  "assurance/02-concept/hara/WP-C-03-hara-cartesian_experimental.xlsx": "WP-C-03 HARA (Experimental Mode variant)",
  "assurance/00-assessment/iso26262-2018/LionDriver_ISO26262_Audit.xlsx": "ISO 26262:2018 audit workbook",
  "assurance/02-concept/fsc/WP-C-04-fsc-completeness.xlsx": "WP-C-04 FSC completeness",
  "assurance/08-analyses/fmea/exports/review/dfmea-review.xlsx": "DFMEA review workbook",
  "assurance/08-analyses/fmea/exports/review/pfmea-review.xlsx": "PFMEA review workbook",
  "assurance/08-analyses/fmea/exports/review/sw-fmea-review.xlsx": "SW FMEA review workbook",
  "assurance/08-analyses/fmea/exports/review/system-fmea-review.xlsx": "System FMEA review workbook",
  "assurance/08-analyses/fmea/exports/review/fmeda-sg001-review.xlsx": "FMEDA SG-001 (SG-01…06) review workbook",
  "assurance/08-analyses/fmea/exports/review/fmeda-sg009-review.xlsx": "FMEDA SG-009 (SG-07) review workbook",
}
FIRST = "assurance/02-concept/hara/WP-C-03-hara-cartesian.xlsx"   # opens first
# Columns offered as filter chips when a sheet has them, in this order (a column with 2-24 values only).
FILTERS = ["Function", "Malfunction", "ASIL", "S", "E", "C", "Location", "Weather", "Section", "Assessment",
           "Obligation", "Worst-case ASIL", "Consolidated into", "AP", "Status", "Severity", "Occurrence", "Detection"]
# Columns kept in the grid on a phone, in this order; everything else is in the row detail.
NARROW = ["HARA ID", "SG_ID", "ID", "ASIL", "Worst-case ASIL", "Assessment", "AP", "S", "E", "C", "O", "D",
          "Malfunction", "Location", "Requirement", "Hazard", "Failure mode", "Status"]
LONG = 60   # a column whose cells average more characters than this is clamped to two lines in the grid


def text(v) -> str:
  if v is None:
    return ""
  if isinstance(v, float) and v.is_integer():
    v = int(v)
  return str(v).strip()


def label_line(cells: list[str]) -> str:
  """A key/value row outside a table: "**Key.** value"; a single cell stays as it is."""
  if len(cells) < 2:
    return cells[0] if cells else ""
  return f"**{cells[0].rstrip('.:')}.** " + " · ".join(cells[1:])


def read_sheet(ws) -> tuple[list[str], list[str], list[list[str]], list[str]]:
  """(lines above the table, header, data rows, lines below it). The header is the first row with as many filled
  cells as the widest row; columns that are empty all the way down are dropped."""
  rows = [[text(c) for c in r] for r in ws.iter_rows(values_only=True)]
  width = max((sum(1 for c in r if c) for r in rows), default=0)
  if width == 0:
    return [], [], [], []
  hi = next(i for i, r in enumerate(rows) if sum(1 for c in r if c) == width)
  above = [label_line([c for c in r if c]) for r in rows[:hi] if any(r)]
  cols = [j for j in range(len(rows[hi])) if any(r[j] for r in rows[hi:] if j < len(r))]
  header = [rows[hi][j] for j in cols]
  body, below = [], []
  for r in rows[hi + 1:]:
    cells = [r[j] if j < len(r) else "" for j in cols]
    filled = sum(1 for c in cells if c)
    if filled == 0:
      if body:
        below.append("")
      continue
    if below or (filled == 1 and cells[0] and len(cells) > 2 and len(cells[0]) > 60):
      below.append(label_line([c for c in cells if c]))   # a note under the table
    else:
      body.append(cells)
  return above, header, body, [b for b in below if b]


def workbooks(root: Path = ROOT) -> list[str]:
  out = subprocess.run(["git", "-C", str(root), "ls-files", "assurance/*.xlsx"], capture_output=True, text=True,
                       check=True).stdout.split()
  return sorted(out, key=lambda p: (p != FIRST, p))


def title(path: str) -> str:
  if path in TITLES:
    return TITLES[path]
  stem = Path(path).stem
  stem = stem.replace("-review", "").replace("_", " ")
  parts = stem.split("-")
  if parts[0] == "RR":   # RR-2026-003-hara-checklist -> RR-2026-003 HARA checklist
    rest = " ".join(parts[3:])
    return f"{'-'.join(parts[:3])} {rest.replace('hara', 'HARA').replace('fsc', 'FSC').replace('hsi', 'HSI').replace('tsc', 'TSC').replace('hwsr', 'HWSR')}"
  return stem.replace("-", " ")


def group(path: str) -> str:
  part = Path(path).parts[1]   # 02-concept -> 02 Concept
  num, _, name = part.partition("-")
  return f"{num} {name.capitalize()}" if name else part


def collect(root: Path = ROOT) -> dict:
  strings: dict[str, int] = {}

  def s(v: str) -> int:
    if v not in strings:
      strings[v] = len(strings)
    return strings[v]

  books = []
  for path in workbooks(root):
    book = openpyxl.load_workbook(root / path, data_only=True)
    sheets = []
    for ws in book.worksheets:
      above, header, body, below = read_sheet(ws)
      widths = [sum(len(r[j]) for r in body) / max(len(body), 1) for j in range(len(header))]
      sheets.append({"name": ws.title, "above": above, "below": below, "header": header,
                     "long": [w > LONG for w in widths],
                     "filters": [header.index(f) for f in FILTERS if f in header and any(header)],
                     "narrow": [header.index(h) for h in NARROW if h in header],
                     "rows": [[s(c) for c in r] for r in body]})
    books.append({"title": title(path), "group": group(path), "src": path, "sheets": sheets})
  return {"strings": list(strings), "books": books}


PAGE = r"""<title>Assurance Workbook Viewer</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=IBM+Plex+Mono:wght@500&family=IBM+Plex+Sans+Condensed:wght@600&display=swap">
<style>
/* Layout: a sticky control band (workbook, sheet tabs, filters) over one scrolling grid; row detail slides in as a
   drawer. Colour is spent on the ASIL scale only, everything else stays in a cool steel neutral. */
:root{
  --bg:#f2f4f6; --panel:#ffffff; --ink:#16202b; --muted:#5b6876; --line:#d5dbe2; --head:#e8ecf1;
  --accent:#1f5fa8; --accent-soft:#e2ecf8; --sel:#fff6d6;
  --qm:#e6e9ed; --qm-ink:#4b5561; --a:#d8efdf; --a-ink:#14633a; --b:#fbf0c2; --b-ink:#7a5600;
  --c:#fbdcc4; --c-ink:#9a3d00; --d:#f9d0cd; --d-ink:#a3201a; --s0:#eef0f3; --s0-ink:#7a8592;
  --f-ui:"Atkinson Hyperlegible","Segoe UI",system-ui,sans-serif;
  --f-head:"IBM Plex Sans Condensed","Arial Narrow",system-ui,sans-serif;
  --f-mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#0f141a; --panel:#161d25; --ink:#e4eaf0; --muted:#94a2b1; --line:#2a3440; --head:#1c252f;
  --accent:#7fb0ec; --accent-soft:#1d2c40; --sel:#3a3318;
  --qm:#252e38; --qm-ink:#a9b4bf; --a:#173527; --a-ink:#79d6a0; --b:#3a3214; --b-ink:#f0cf6a;
  --c:#40260f; --c-ink:#f7a467; --d:#431b19; --d-ink:#ff8f86; --s0:#1b222b; --s0-ink:#7d8996; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0f141a; --panel:#161d25; --ink:#e4eaf0; --muted:#94a2b1; --line:#2a3440; --head:#1c252f;
  --accent:#7fb0ec; --accent-soft:#1d2c40; --sel:#3a3318;
  --qm:#252e38; --qm-ink:#a9b4bf; --a:#173527; --a-ink:#79d6a0; --b:#3a3214; --b-ink:#f0cf6a;
  --c:#40260f; --c-ink:#f7a467; --d:#431b19; --d-ink:#ff8f86; --s0:#1b222b; --s0-ink:#7d8996; color-scheme:dark}
*{box-sizing:border-box}
html,body{height:100%}
body{background:var(--bg);color:var(--ink);font:400 15px/1.45 var(--f-ui);display:flex;flex-direction:column;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:10;background:var(--bg)}
header{display:flex;flex-direction:column;gap:10px;padding-block:14px 10px;min-width:0;max-width:100%}
header>*,main>*{min-width:0;max-width:100%}
[hidden]{display:none!important}
.top{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:baseline;justify-content:space-between}
h1{font:600 21px/1.15 var(--f-head);margin:0;letter-spacing:.01em;text-wrap:balance}
.src{font:500 12px var(--f-mono);color:var(--muted);display:flex;gap:6px;align-items:center;min-width:0;max-width:100%}
.src select{flex:1 1 auto;min-width:0;max-width:100%;text-overflow:ellipsis}
select,input[type=search]{font:inherit;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:7px 10px;min-width:0}
select:focus-visible,input:focus-visible,button:focus-visible,.tab:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.tt{display:flex;flex-direction:column;gap:2px;min-width:0}
#path{overflow-wrap:anywhere}
.tabs{display:flex;gap:6px;overflow-x:auto;padding-bottom:4px;scrollbar-width:thin}
.tab{flex:none;font:600 13px var(--f-head);letter-spacing:.02em;border:1px solid var(--line);background:var(--panel);color:var(--muted);
  border-radius:6px;padding:6px 10px;cursor:pointer;white-space:nowrap}
.tab[aria-selected=true]{background:var(--accent);border-color:var(--accent);color:var(--panel)}
.tab .n{font:500 11px var(--f-mono);opacity:.8;margin-left:6px}
.tools{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.tools input[type=search]{flex:1 1 220px}
.count{font:500 12.5px var(--f-mono);color:var(--muted);font-variant-numeric:tabular-nums}
.chips{display:flex;flex-direction:column;gap:6px}
.frow{display:flex;gap:6px;align-items:center;overflow-x:auto;scrollbar-width:thin;padding-bottom:2px}
.flabel{flex:none;font:600 11.5px var(--f-head);text-transform:uppercase;letter-spacing:.07em;color:var(--muted);width:88px}
.chip{flex:none;font:400 13px var(--f-ui);border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:999px;padding:3px 10px;cursor:pointer;white-space:nowrap}
.chip[aria-pressed=true]{border-color:var(--accent);background:var(--accent-soft);color:var(--accent);font-weight:700}
.chip .k{font:500 11px var(--f-mono);color:var(--muted);margin-left:5px}
.ftoggle{display:none;font:700 13px var(--f-ui);border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:6px;padding:6px 12px;cursor:pointer}
.ftoggle.act{border-color:var(--accent);color:var(--accent);background:var(--accent-soft)}
@media (max-width:640px){.ftoggle{display:inline-block}.chips:not(.open){display:none}}
.clear{border:0;background:none;color:var(--accent);font:700 13px var(--f-ui);cursor:pointer;padding:4px 2px}
main{flex:1;min-height:0;min-width:0;max-width:100%;display:flex;flex-direction:column;gap:10px;padding-bottom:max(12px,env(safe-area-inset-bottom,0px))}
.notes{font-size:13.5px;color:var(--muted);display:flex;flex-direction:column;gap:4px;max-width:90ch}
.notes b{color:var(--ink)}
.grid{flex:1;min-height:260px;overflow:auto;background:var(--panel);border:1px solid var(--line);border-radius:8px}
table{border-collapse:separate;border-spacing:0;font-size:13.5px;min-width:100%}
th,td{border-bottom:1px solid var(--line);border-right:1px solid var(--line);padding:6px 9px;text-align:left;vertical-align:top}
th{position:sticky;top:0;z-index:2;background:var(--head);font:600 12.5px var(--f-head);letter-spacing:.02em;white-space:nowrap}
td:first-child,th:first-child{position:sticky;left:0;z-index:1;background:var(--panel);font:500 12.5px var(--f-mono);white-space:nowrap}
th:first-child{z-index:3;background:var(--head)}
tbody tr{cursor:pointer}
tbody tr:hover td{background:var(--accent-soft)}
tbody tr.on td{background:var(--sel)}
td.long{min-width:260px;max-width:420px}
td.long div{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
td.short{white-space:nowrap}
.r{display:inline-block;min-width:34px;text-align:center;border-radius:4px;padding:1px 6px;font:500 12.5px var(--f-mono)}
.r.QM{background:var(--qm);color:var(--qm-ink)} .r.A{background:var(--a);color:var(--a-ink)} .r.B{background:var(--b);color:var(--b-ink)}
.r.C{background:var(--c);color:var(--c-ink)} .r.D{background:var(--d);color:var(--d-ink)} .r.S0{background:var(--s0);color:var(--s0-ink)}
.more{margin:10px auto;display:block;font:700 14px var(--f-ui);color:var(--accent);background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:8px 14px;cursor:pointer}
.kv td:first-child{font:600 13px var(--f-head);white-space:normal;width:30%}
.empty{padding:24px;color:var(--muted)}
.drawer{position:fixed;z-index:20;background:var(--panel);border:1px solid var(--line);box-shadow:0 10px 40px rgb(0 0 0 / .18);
  display:flex;flex-direction:column;inset:auto 0 0 0;max-height:78%;border-radius:12px 12px 0 0;
  padding:14px max(16px,env(safe-area-inset-right,0px)) max(16px,env(safe-area-inset-bottom,0px)) max(16px,env(safe-area-inset-left,0px))}
@media (min-width:900px){.drawer{inset:max(16px,env(safe-area-inset-top,0px)) max(16px,env(safe-area-inset-right,0px)) 16px auto;width:440px;max-height:none;border-radius:10px}}
.dhead{display:flex;justify-content:space-between;align-items:center;gap:10px;border-bottom:1px solid var(--line);padding-bottom:8px}
.dhead h2{font:600 18px var(--f-head);margin:0}
.dhead button{font:700 14px var(--f-ui);border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:6px;padding:5px 12px;cursor:pointer}
.dbody{overflow:auto;padding-top:8px;display:flex;flex-direction:column;gap:10px}
.field{display:flex;flex-direction:column;gap:2px}
.field .l{font:600 11.5px var(--f-head);text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}
.field .v{font-size:14.5px;white-space:pre-wrap;overflow-wrap:anywhere}
.legend{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:12.5px;color:var(--muted)}
@media (max-width:640px){.wide{display:none}.flabel{width:auto}}
@media (prefers-reduced-motion:no-preference){.drawer{animation:up .16s ease-out}@keyframes up{from{transform:translateY(12px);opacity:.6}}}
</style>
<header>
  <div class="top">
    <div class="tt"><h1 id="title"></h1><span class="src" id="path"></span></div>
    <label class="src">Workbook <select id="book" aria-label="Workbook"></select></label>
  </div>
  <div class="tabs" id="tabs" role="tablist" aria-label="Sheets"></div>
  <div class="tools" id="tools">
    <input type="search" id="q" placeholder="Search this sheet" aria-label="Search this sheet">
    <span class="count" id="count"></span>
    <label class="count"><input type="checkbox" id="all"> all columns</label>
    <button class="ftoggle" id="ftoggle" aria-expanded="false">Filters</button>
    <button class="clear" id="clear" hidden>Clear filters</button>
  </div>
  <div class="chips" id="chips"></div>
</header>
<main>
  <div class="notes" id="notes"></div>
  <div class="grid" id="grid"></div>
  <div class="legend">ASIL <span class="r QM">QM</span><span class="r A">A</span><span class="r B">B</span><span class="r C">C</span><span class="r D">D</span><span class="r S0">—</span> S0, no requirement · Tap a row for every field, rationale included.</div>
</main>
<aside class="drawer" id="drawer" hidden aria-label="Row detail"><div class="dhead"><h2 id="dtitle"></h2><button id="dclose">Close</button></div><div class="dbody" id="dbody"></div></aside>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent), S=D.strings;
const RATED=new Set(['ASIL','Worst-case ASIL','S','E','C','Assessment','AP']);
const AP={H:'D',M:'B',L:'A'};
const PAGE=200;
let st={b:0,s:0,q:'',f:{},shown:PAGE,all:false,sel:-1};
const $=id=>document.getElementById(id);
function save(){try{localStorage.setItem('hv',JSON.stringify({b:st.b,s:st.s,all:st.all}))}catch(e){}}
try{Object.assign(st,JSON.parse(localStorage.getItem('hv')||'{}'))}catch(e){}
const book=()=>D.books[st.b], sheet=()=>book().sheets[st.s];
function esc(t){return t.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function badge(h,v){
  if(!RATED.has(h)||!v) return esc(v);
  const k=v==='—'?'S0':(h==='AP'&&AP[v])?AP[v]:(/^(QM|A|B|C|D)$/.test(v)?v:(/^[SEC]\d$/.test(v)?({0:'QM',1:'A',2:'B',3:'C',4:'D'}[v[1]]):null));
  return k?`<span class="r ${k}">${esc(v)}</span>`:esc(v);
}
function init(){
  const groups=[...new Set(D.books.map(b=>b.group))].sort();
  $('book').innerHTML=groups.map(g=>`<optgroup label="${esc(g)}">`+D.books.map((b,i)=>b.group===g?`<option value="${i}">${esc(b.title)}</option>`:'').join('')+'</optgroup>').join('');
  $('book').onchange=e=>{st.b=+e.target.value;st.s=0;reset();render()};
  $('q').oninput=e=>{st.q=e.target.value.toLowerCase();st.shown=PAGE;grid()};
  $('all').onchange=e=>{st.all=e.target.checked;save();grid()};
  $('clear').onclick=()=>{st.f={};st.q='';$('q').value='';st.shown=PAGE;chips();grid()};
  $('dclose').onclick=close;
  $('ftoggle').onclick=()=>{const o=$('chips').classList.toggle('open');$('ftoggle').setAttribute('aria-expanded',o)};
  document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});
  if(st.b>=D.books.length)st.b=0;
  render();
}
function reset(){st.f={};st.q='';st.shown=PAGE;st.sel=-1;$('q').value='';close()}
function render(){
  if(st.s>=book().sheets.length)st.s=0;
  $('book').value=st.b; $('title').textContent=book().title; $('path').textContent=book().src; $('all').checked=st.all;
  $('tabs').innerHTML=book().sheets.map((s,i)=>`<button class="tab" role="tab" aria-selected="${i===st.s}" data-i="${i}">${esc(s.name.replace(/^\d+_/,'').replace(/_/g,' '))}<span class="n">${s.rows.length}</span></button>`).join('');
  $('tabs').querySelectorAll('.tab').forEach(t=>t.onclick=()=>{st.s=+t.dataset.i;reset();save();render();t.scrollIntoView({inline:'nearest',block:'nearest'})});
  const sh=sheet();
  $('notes').innerHTML=[...sh.above,...sh.below].map(l=>`<div>${esc(l).replace(/\*\*(.+?)\*\*/g,'<b>$1</b>')}</div>`).join('');
  $('tools').hidden=!sh.header.some(Boolean)||sh.rows.length<12;
  chips(); grid(); save();
}
function chips(){
  const sh=sheet(); const box=$('chips'); box.innerHTML='';
  if(sh.rows.length<12){$('clear').hidden=true;return}
  for(const j of sh.filters){
    const counts=new Map(); for(const r of match(j)) counts.set(r[j],(counts.get(r[j])||0)+1);
    const all=[...new Set(sh.rows.map(r=>r[j]))];
    if(all.length<2||all.length>24) continue;
    const order=['D','C','B','A','QM','—']; all.sort((a,b)=>{const x=order.indexOf(S[a]),y=order.indexOf(S[b]);return (x<0?99:x)-(y<0?99:y)||S[a].localeCompare(S[b],undefined,{numeric:true})});
    const row=document.createElement('div'); row.className='frow';
    row.innerHTML=`<span class="flabel">${esc(sh.header[j])}</span>`+all.map(v=>`<button class="chip" aria-pressed="${!!(st.f[j]&&st.f[j].has(v))}" data-j="${j}" data-v="${v}">${badge(sh.header[j],S[v])}<span class="k">${counts.get(v)||0}</span></button>`).join('');
    box.appendChild(row);
  }
  box.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{const j=+c.dataset.j,v=+c.dataset.v;const s=st.f[j]||(st.f[j]=new Set());s.has(v)?s.delete(v):s.add(v);if(!s.size)delete st.f[j];st.shown=PAGE;chips();grid()});
  $('clear').hidden=!Object.keys(st.f).length&&!st.q;
  const n=Object.values(st.f).reduce((a,s)=>a+s.size,0);
  $('ftoggle').textContent=n?`Filters · ${n}`:'Filters'; $('ftoggle').classList.toggle('act',!!n);
  $('ftoggle').hidden=!box.children.length;
}
function match(skip){
  const sh=sheet(), q=st.q, fs=Object.entries(st.f).filter(([j])=>+j!==skip);
  return sh.rows.filter(r=>fs.every(([j,s])=>s.has(r[+j]))&&(!q||r.some(i=>S[i].toLowerCase().includes(q))));
}
function cols(){const sh=sheet();const narrow=window.matchMedia('(max-width:640px)').matches&&!st.all&&sh.narrow.length>=3;return narrow?sh.narrow:sh.header.map((_,j)=>j)}
function grid(){
  const sh=sheet(), g=$('grid');
  if(!sh.rows.length&&!sh.header.length){g.innerHTML='<div class="empty">This sheet is empty.</div>';$('count').textContent='';return}
  const rows=match(-1), cs=cols(), kv=!sh.header.some(Boolean);
  $('count').textContent=rows.length===sh.rows.length?`${rows.length} rows`:`${rows.length} of ${sh.rows.length} rows`;
  $('clear').hidden=!Object.keys(st.f).length&&!st.q;
  const head=kv?'':`<thead><tr>${cs.map(j=>`<th>${esc(sh.header[j])}</th>`).join('')}</tr></thead>`;
  const body=rows.slice(0,st.shown).map(r=>{const i=sh.rows.indexOf(r);return `<tr data-i="${i}" class="${i===st.sel?'on':''}">${cs.map(j=>{const v=S[r[j]];return sh.long[j]?`<td class="long"><div>${badge(sh.header[j],v)}</div></td>`:`<td class="short">${badge(sh.header[j],v)}</td>`}).join('')}</tr>`}).join('');
  g.innerHTML=rows.length?`<table class="${kv?'kv':''}">${head}<tbody>${body}</tbody></table>`+(rows.length>st.shown?`<button class="more" id="more">Show ${Math.min(PAGE,rows.length-st.shown)} more of ${rows.length-st.shown}</button>`:''):'<div class="empty">No rows match. Clear a filter or the search.</div>';
  g.querySelectorAll('tbody tr').forEach(tr=>tr.onclick=()=>open(+tr.dataset.i));
  const m=$('more'); if(m)m.onclick=()=>{st.shown+=PAGE;grid()};
}
function open(i){
  const sh=sheet(), r=sh.rows[i]; st.sel=i;
  document.querySelectorAll('tbody tr').forEach(tr=>tr.classList.toggle('on',+tr.dataset.i===i));
  $('dtitle').textContent=S[r[0]]||'Row';
  $('dbody').innerHTML=sh.header.map((h,j)=>S[r[j]]?`<div class="field"><span class="l">${esc(h||'Value')}</span><span class="v">${badge(h,S[r[j]])}</span></div>`:'').join('');
  $('drawer').hidden=false; $('dclose').focus();
}
function close(){$('drawer').hidden=true;st.sel=-1;document.querySelectorAll('tbody tr.on').forEach(t=>t.classList.remove('on'))}
init();
</script>
"""


def build(root: Path = ROOT) -> str:
  data = json.dumps(collect(root), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
  return PAGE.replace("__DATA__", data)


def fingerprint(page: str) -> str:
  return hashlib.sha256(page.encode()).hexdigest()


def main() -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--out", help="write the page here and update the fingerprint")
  ap.add_argument("--check", action="store_true", help="fail if the fingerprint does not match a fresh build")
  args = ap.parse_args()
  page = build()
  fp = fingerprint(page)
  if args.check:
    stored = FINGERPRINT.read_text(encoding="utf-8").split()[0] if FINGERPRINT.exists() else ""
    if stored != fp:
      print("xlsx_viewer: a workbook or the viewer changed since the page was last built. Run\n"
            "  python3 tools/xlsx_viewer.py --out <scratch>/workbook-viewer.html\n"
            f"and republish that file to {VIEWER_URL}", file=sys.stderr)
      return 1
    print(f"xlsx_viewer: page current ({len(collect()['books'])} workbooks)")
    return 0
  if not args.out:
    ap.error("give --out or --check")
  Path(args.out).write_text(page, encoding="utf-8")
  FINGERPRINT.write_text(f"{fp}  published at {VIEWER_URL}\n", encoding="utf-8")
  print(f"xlsx_viewer: wrote {args.out}; republish it to {VIEWER_URL}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
