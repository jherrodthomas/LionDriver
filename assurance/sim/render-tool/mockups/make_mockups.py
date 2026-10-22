"""Mockups of Hazard Scene Studio, the risk-scene renderer as a Windows desktop app (for review; nothing here is
the app).

Writes one HTML page per screen and screenshots it with headless Chromium to <name>.png, 1600 x 1000. The rows,
outcomes and pictures are the real ones of ../examples/demo.xlsx.

  python3 assurance/sim/render-tool/mockups/make_mockups.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell")
W, H = 1600, 1000

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1600px;height:1000px;background:#c9d3de;font:13px/1.4 Inter,'Segoe UI',sans-serif;color:#1b1b1b;
  -webkit-font-smoothing:antialiased;overflow:hidden}
.win{position:absolute;inset:14px;background:#f3f3f3;border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,.28);
  overflow:hidden;display:flex;flex-direction:column;border:1px solid #b9b9b9}
.title{height:36px;display:flex;align-items:center;padding-left:14px;gap:10px;background:#ebebeb;font-size:12px}
.title .logo{width:16px;height:16px;border-radius:4px;background:linear-gradient(135deg,#e8743b,#c4402a)}
.title .name{flex:1}
.title .ctl{width:46px;height:36px;display:flex;align-items:center;justify-content:center;font-size:14px;color:#333}
.title .ctl.x:hover{background:#c42b1c}
.cmd{height:48px;display:flex;align-items:center;gap:4px;padding:0 12px;background:#f9f9f9;border-bottom:1px solid #e3e3e3}
.btn{display:flex;align-items:center;gap:7px;padding:6px 11px;border-radius:5px;font-size:13px;color:#1b1b1b}
.btn svg{width:16px;height:16px;stroke:#333;fill:none;stroke-width:1.6}
.btn.primary{background:#c4402a;color:#fff}.btn.primary svg{stroke:#fff}
.btn.ghost{border:1px solid #d6d6d6;background:#fff}
.sep{width:1px;height:24px;background:#e0e0e0;margin:0 6px}
.spacer{flex:1}
.body{flex:1;display:flex;min-height:0}
.nav{width:220px;background:#f3f3f3;padding:12px 8px;border-right:1px solid #e3e3e3}
.nav h4{font-size:11px;font-weight:600;color:#666;text-transform:uppercase;letter-spacing:.05em;margin:10px 10px 6px}
.nav .item{display:flex;justify-content:space-between;padding:8px 10px;border-radius:5px;color:#1b1b1b}
.nav .item.on{background:#e5e5e5;position:relative;font-weight:600}
.nav .item.on:before{content:'';position:absolute;left:0;top:9px;bottom:9px;width:3px;border-radius:2px;background:#c4402a}
.nav .item .n{color:#777;font-weight:400}
.nav .item.soon{color:#999}
.main{flex:1;display:flex;flex-direction:column;min-width:0;background:#fff;overflow:hidden}
.sheetbar{display:flex;align-items:center;gap:10px;padding:12px 16px;border-bottom:1px solid #eee}
.sheetbar .file{font-weight:600;font-size:15px}
.sheetbar .muted{color:#777}
table{border-collapse:collapse;width:100%;font-size:12px;table-layout:fixed}
th{position:sticky;top:0;background:#fafafa;text-align:left;font-weight:600;color:#444;padding:8px 10px;
  border-bottom:1px solid #e3e3e3;white-space:nowrap}
th .k{display:block;font-size:10px;font-weight:600;letter-spacing:.04em;text-transform:uppercase}
td{padding:10px 8px;border-bottom:1px solid #f0f0f0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
th{padding:8px}
tr.pick td{background:#fdf0ec}
tr.pick td:first-child{box-shadow:inset 3px 0 #c4402a}
.k.scene{color:#b05a10}.k.look{color:#2c7a43}.k.motion{color:#2a59b8}.k.rating{color:#8a6d00}.k.result{color:#6b3fa0}
.pill{display:inline-flex;align-items:center;gap:5px;padding:2px 8px;border-radius:10px;font-size:11.5px;font-weight:500}
.pill.ok{background:#e3f4e8;color:#1e6b34}.pill.bad{background:#fde7e4;color:#a1281a}.pill.run{background:#e4ecfb;color:#24489a}
.pill.wait{background:#f0f0f0;color:#555}
.dot{width:7px;height:7px;border-radius:50%;background:currentColor}
.asil{font-weight:700;color:#c4402a}
.detail{width:400px;border-left:1px solid #e3e3e3;background:#fbfbfb;overflow:hidden;display:flex;flex-direction:column}
.detail .hd{padding:14px 18px 10px;border-bottom:1px solid #eee}
.detail .hd .id{font-weight:700;font-size:15px}
.detail .hd .sub{color:#666;font-size:12px}
.grp{padding:10px 18px 4px}
.grp h5{font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;margin-bottom:6px;display:flex;align-items:center;gap:6px}
.field{display:grid;grid-template-columns:110px 1fr;align-items:center;gap:8px;margin-bottom:7px}
.field label{color:#555;font-size:12px}
.sel{height:30px;border:1px solid #d1d1d1;border-bottom-color:#a9a9a9;border-radius:4px;background:#fff;display:flex;
  align-items:center;justify-content:space-between;padding:0 9px;font-size:12.5px}
.sel:after{content:'⌄';color:#555;font-size:13px;margin-top:-5px}
.sel.ro{background:#f5f5f5;color:#333}.sel.ro:after{content:''}
.note{font-size:11.5px;color:#8a5a14;background:#fff6e5;border-radius:4px;padding:6px 8px;margin:2px 0 8px}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{border:1px solid #e2d9a8;background:#fffbe6;border-radius:4px;padding:3px 8px;font-size:12px}
.chip b{color:#8a6d00;font-weight:600;margin-right:3px}
.res{margin:6px 18px 0;border:1px solid #e6e6e6;border-radius:6px;background:#fff;overflow:hidden}
.res img{display:block;width:100%}
.res .rows{padding:8px 10px;display:grid;grid-template-columns:auto 1fr;gap:3px 10px;font-size:12px}
.res .rows span:nth-child(odd){color:#666}
.status{height:28px;display:flex;align-items:center;gap:16px;padding:0 14px;background:#f3f3f3;border-top:1px solid #e3e3e3;
  font-size:11.5px;color:#555}
.status .syn{margin-left:auto;color:#a1281a;font-weight:600}
.dim{position:absolute;inset:50px 0 28px 0;background:rgba(0,0,0,.28)}
.dialog{position:absolute;left:50%;top:52%;transform:translate(-50%,-50%);width:760px;background:#fff;border-radius:8px;
  box-shadow:0 16px 48px rgba(0,0,0,.35);overflow:hidden;border:1px solid #c8c8c8}
.dialog .dh{padding:20px 24px 6px;font-size:19px;font-weight:600}
.dialog .dd{padding:0 24px 14px;color:#555}
.dialog .search{margin:0 24px 12px;height:34px;border:1px solid #c8c8c8;border-bottom:2px solid #c4402a;border-radius:4px;
  display:flex;align-items:center;padding:0 10px;gap:8px;font-size:13.5px}
.list{margin:0 24px;border:1px solid #e3e3e3;border-radius:6px;overflow:hidden}
.li{display:grid;grid-template-columns:22px 210px 1fr 60px;gap:10px;align-items:center;padding:9px 12px;border-bottom:1px solid #f0f0f0;font-size:12.5px}
.li:last-child{border-bottom:0}
.li.on{background:#fdf0ec}
.cb{width:16px;height:16px;border-radius:3px;border:1.5px solid #888;display:flex;align-items:center;justify-content:center;font-size:11px;color:#fff}
.cb.on{background:#c4402a;border-color:#c4402a}
.mono{font-family:'JetBrains Mono',monospace;font-size:12px}
.preview{margin:14px 24px 0;border-radius:6px;background:#f7f7f7;padding:12px 14px;display:grid;grid-template-columns:130px 1fr;gap:6px 12px;font-size:12.5px}
.preview span:nth-child(odd){color:#666}
.df{display:flex;justify-content:flex-end;gap:8px;padding:16px 24px;background:#f3f3f3;margin-top:16px;border-top:1px solid #e3e3e3}
.df .btn{border:1px solid #d1d1d1;background:#fff;min-width:110px;justify-content:center}
.df .btn.primary{border-color:#c4402a;background:#c4402a}
.bar{height:6px;background:#e6e6e6;border-radius:3px;overflow:hidden}.bar i{display:block;height:100%;background:#c4402a}
.card{background:#fff;border:1px solid #e6e6e6;border-radius:8px}
"""

ICON = {
  "open": '<svg viewBox="0 0 16 16"><path d="M1.5 4.5v8h11l2-5.5h-11L1.5 12.5M1.5 4.5v-2h4l1.5 1.5h5.5v3"/></svg>',
  "save": '<svg viewBox="0 0 16 16"><path d="M2.5 2.5h9l2 2v9h-11z M5 2.5v3.5h5v-3.5 M4.5 13.5v-4h7v4"/></svg>',
  "hara": '<svg viewBox="0 0 16 16"><path d="M2.5 2.5h11v11h-11z M2.5 6h11 M6 6v7.5 M9 9.5h3 M10.5 8v3"/></svg>',
  "plus": '<svg viewBox="0 0 16 16"><path d="M8 3v10M3 8h10"/></svg>',
  "play": '<svg viewBox="0 0 16 16"><path d="M4.5 3l8 5-8 5z"/></svg>',
  "all": '<svg viewBox="0 0 16 16"><path d="M2.5 3l6 5-6 5z M8.5 3l6 5-6 5z"/></svg>',
  "gear": '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="2.2"/><path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4"/></svg>',
  "img": '<svg viewBox="0 0 16 16"><path d="M2 3h12v10H2z M2 11l4-4 3 3 2-2 3 3"/></svg>',
  "folder": '<svg viewBox="0 0 16 16"><path d="M1.5 3.5h4.5l1.5 1.5h7v8h-13z"/></svg>',
  "copy": '<svg viewBox="0 0 16 16"><path d="M5.5 5.5h8v8h-8z M2.5 10.5v-8h8"/></svg>',
  "cmp": '<svg viewBox="0 0 16 16"><path d="M2 3h5v10H2z M9 3h5v10H9z"/></svg>',
  "stop": '<svg viewBox="0 0 16 16"><path d="M4 4h8v8H4z"/></svg>',
  "back": '<svg viewBox="0 0 16 16"><path d="M10 3L5 8l5 5"/></svg>',
  "fwd": '<svg viewBox="0 0 16 16"><path d="M6 3l5 5-5 5"/></svg>',
}

ROWS = [
  # id, title, env, cond, preset, speed, asil, status, contact, render
  ("F-01/M03/OS-01/W02", "Lane centring, unrequested function", "highway-free-flow", "W02", "he-01-2-hardover-adjacent",
   "", "B", ("ok", "Drawn"), "Adjacent car, +2.21 s, 10 km/h"),
  ("F-01/M03/OS-01/W02 at night", "Same row, condition W03", "highway-free-flow", "W03", "he-01-2-hardover-adjacent", "",
   "B", ("ok", "Drawn"), "Adjacent car, +2.21 s, 10 km/h"),
  ("F-01/M03/OS-01/W02 at 90 km/h", "Same row, 90 km/h", "highway-free-flow", "W02", "he-01-2-hardover-adjacent", "90",
   "B", ("ok", "Drawn"), "Barrier, +3.88 s, 90 km/h"),
  ("F-01/M01/OS-19/W01", "Lane centring, no function", "—", "W01", "—", "", "A",
   ("bad", "Cannot draw yet"), "No environment for OS-19 (roundabout)"),
]


def window(title: str, inner: str, extra: str = "") -> str:
  return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="win"><div class="title"><div class="logo"></div><div class="name">{title}</div>
<div class="ctl">&#8211;</div><div class="ctl">&#9633;</div><div class="ctl x">&#10005;</div></div>
{inner}</div>{extra}</body></html>"""


def btn(icon: str, text: str, cls: str = "") -> str:
  return f'<div class="btn {cls}">{ICON[icon]}{text}</div>'


def cmdbar(rendering: bool = False) -> str:
  run = (btn("stop", "Stop", "ghost") if rendering else btn("play", "Render selected", "primary"))
  return f"""<div class="cmd">{btn('open', 'Open sheet')}{btn('save', 'Save')}<div class="sep"></div>
{btn('hara', 'Add from HARA…')}{btn('plus', 'Add row')}<div class="sep"></div>{run}{btn('all', 'Render all')}
<div class="spacer"></div>{btn('img', 'Gallery')}{btn('gear', 'Settings')}</div>"""


def nav() -> str:
  return """<div class="nav"><h4>Methods</h4>
<div class="item on">ISO 26262 HARA <span class="n">4</span></div>
<div class="item soon">ISO 21448 SOTIF <span class="n">soon</span></div>
<div class="item soon">MIL-STD-882E <span class="n">soon</span></div>
<div class="item soon">Custom matrix <span class="n">soon</span></div>
<h4>Recent sheets</h4>
<div class="item">demo.xlsx</div><div class="item">hara-review-oct.xlsx</div>
<h4>Library</h4>
<div class="item">Environments <span class="n">14</span></div><div class="item">Conditions <span class="n">8</span></div>
<div class="item">Motion presets <span class="n">64</span></div><div class="item">Vehicles <span class="n">1</span></div></div>"""


def table(sel: int = 0, states: dict | None = None) -> str:
  head = """<tr><th>Row ID</th><th><span class="k scene">Scene</span>Environment</th>
<th><span class="k look">Look</span>Condition</th><th><span class="k motion">Motion</span>Preset</th>
<th><span class="k motion">Motion</span>Speed</th><th><span class="k rating">Rating</span>ASIL</th>
<th><span class="k result">Result</span>Status</th><th><span class="k result">Result</span>Contact</th></tr>"""
  body = ""
  for i, r in enumerate(ROWS):
    st = (states or {}).get(i, r[7])
    body += (f'<tr class="{"pick" if i == sel else ""}"><td class="mono">{r[0]}</td><td>{r[2]}</td>'
             f'<td>{r[3]}</td><td>{r[4]}</td><td>{r[5] or "<span style=color:#999>preset</span>"}</td>'
             f'<td class="asil">{r[6]}</td><td><span class="pill {st[0]}"><span class="dot"></span>{st[1]}</span></td>'
             f'<td>{r[8]}</td></tr>')
  cols = "".join(f'<col style="width:{w}px">' for w in (175, 125, 72, 150, 55, 58, 140)) + "<col>"
  return f"<table><colgroup>{cols}</colgroup>{head}{body}</table>"


def sheetbar() -> str:
  return """<div class="sheetbar"><div class="file">demo.xlsx</div><div class="muted">ISO 26262 HARA · 4 rows · saved 16:42</div>
<div class="spacer"></div><div class="btn ghost" style="font-size:12px">Open in Excel</div></div>"""


def statusbar(msg: str = "Ready") -> str:
  return f"""<div class="status"><span>{msg}</span><span>Plant: panda safety code (bundled)</span><span>Blender 5.2 (bundled)</span>
<span>Ego model: Corolla E210 (your folder)</span><span class="syn">Synthetic pictures · no evidence credit</span></div>"""


def detail_row(img: str) -> str:
  return f"""<div class="detail"><div class="hd"><div class="id mono">F-01/M03/OS-01/W02</div>
<div class="sub">H-01 Unintended or excessive lateral motion</div></div>
<div class="grp"><h5 class="k scene">Scene</h5>
<div class="field"><label>Environment</label><div class="sel">highway-free-flow</div></div>
<div class="note">The road sets lanes and the barrier, so changing it can change the outcome.</div></div>
<div class="grp"><h5 class="k look">Look · picture only</h5>
<div class="field"><label>Condition</label><div class="sel">W02 · Wet road or light rain</div></div>
<div class="field"><label>Traffic</label><div class="sel">default (free-flow)</div></div></div>
<div class="grp"><h5 class="k motion">Motion</h5>
<div class="field"><label>Preset</label><div class="sel">he-01-2 · plant F-01b hard-over</div></div>
<div class="field"><label>Speed</label><div class="sel">110 km/h (preset)</div></div></div>
<div class="grp"><h5 class="k rating">Rating · as the HARA writes it</h5>
<div class="chips"><span class="chip"><b>S</b>3</span><span class="chip"><b>E</b>3</span><span class="chip"><b>C</b>2</span>
<span class="chip"><b>ASIL</b>B</span><span class="chip"><b>SG</b>01</span><span class="chip"><b>OS</b>01</span></div></div>
<div class="grp" style="padding-bottom:0"><h5 class="k result">Result</h5></div>
<div class="res"><img src="{img}"><div class="rows"><span>Contact</span><span><b>Yes</b>, adjacent car at +2.21 s, 10 km/h</span>
<span>Smallest gap</span><span>0.0 m</span><span>Smallest TTC</span><span>none in path</span>
<span>Motion source</span><span>Plant, case F-01b</span></div></div></div>"""


def main_window() -> str:
  inner = f"""{cmdbar()}<div class="body">{nav()}<div class="main">{sheetbar()}{table(0)}</div>
{detail_row('img/thumb-demo.jpg')}</div>{statusbar('4 rows · 3 drawn · 1 cannot be drawn yet')}"""
  return window("Hazard Scene Studio — demo.xlsx", inner)


def add_from_hara() -> str:
  items = [
    (True, "F-01/M03/OS-01/W05", "H-01 · Lane centring, unrequested · snow or ice", "B", ""),
    (True, "F-01/M03/OS-03/W02", "H-01 · Lane centring, unrequested · undivided rural", "C", ""),
    (False, "F-01/M03/OS-19/W01", "H-01 · Lane centring, unrequested · roundabout", "B", "cannot draw yet"),
    (False, "F-01/M03/OS-20/W01", "H-01 · Lane centring, unrequested · road works", "B", "cannot draw yet"),
    (False, "F-01/M03/OS-07/W01", "H-01 · Lane centring, unrequested · slower traffic ahead", "B", ""),
  ]
  li = ""
  for on, k, t, a, warn in items:
    w = f' <span class="pill bad" style="margin-left:6px">{warn}</span>' if warn else ""
    li += (f'<div class="li {"on" if on else ""}"><div class="cb {"on" if on else ""}">{"✓" if on else ""}</div>'
           f'<div class="mono">{k}</div><div>{t}{w}</div><div class="asil">ASIL {a}</div></div>')
  dlg = f"""<div class="dim"></div><div class="dialog"><div class="dh">Add rows from the HARA</div>
<div class="dd">Pick rows of WP-C-03 (hara-events.csv). Their rating is copied as written; the app picks an environment
and a motion preset that can draw them, and you can change those after.</div>
<div class="search">🔍 <span>F-01/M03</span><span style="color:#999;margin-left:auto">38 of 3,840 rows</span></div>
<div class="list">{li}</div>
<div class="preview"><span>Selected</span><span><b>2 rows</b></span>
<span>Environment</span><span>highway-free-flow · rural-undivided</span>
<span>Motion preset</span><span>he-01-2-hardover-adjacent · he-01-1-rural-hardover-oncoming (plant F-01b)</span>
<span>Condition</span><span>W05 snow or ice (outside the ODD) · W02 wet</span></div>
<div class="df"><div class="btn">Cancel</div><div class="btn primary">Add 2 rows</div></div></div>"""
  inner = f"""{cmdbar()}<div class="body">{nav()}<div class="main">{sheetbar()}{table(0)}</div>
{detail_row('img/thumb-demo.jpg')}</div>{statusbar()}"""
  return window("Hazard Scene Studio — demo.xlsx", inner, dlg)


def rendering() -> str:
  states = {0: ("ok", "Drawn"), 1: ("wait", "Waiting"), 2: ("run", "Rendering 6/21"),
            3: ("bad", "Cannot draw yet")}
  panel = """<div class="detail"><div class="hd"><div class="id mono">F-01/M03/OS-01/W02 at 90 km/h</div>
<div class="sub">Rendering · plant run done in 2 s</div></div>
<div style="padding:14px 18px"><img src="img/still-rendering.jpg" style="width:100%;border-radius:6px;display:block">
<div style="display:flex;justify-content:space-between;margin:10px 0 6px;font-size:12px"><span>Still 6 of 21 · chase camera, +1.8 s</span>
<span style="color:#666">about 5 min left</span></div><div class="bar"><i style="width:29%"></i></div></div>
<div class="grp"><h5 class="k result">Outcome (known before the picture)</h5>
<div class="res" style="margin:0"><div class="rows"><span>Contact</span><span><b>Yes</b>, barrier at +3.88 s, 90 km/h</span>
<span>Smallest gap</span><span>1.5 m to the adjacent car</span><span>Motion source</span><span>Plant, case F-01b at 90 km/h</span></div></div></div>
<div class="grp"><h5 style="color:#555">Queue</h5>
<div class="field"><label>Next</label><div class="sel ro">… at night · new picture, ~7 min</div></div>
<div class="field"><label>Reused</label><div class="sel ro">F-01/M03/OS-01/W02 · picture already made</div></div></div></div>"""
  inner = f"""{cmdbar(True)}<div class="body">{nav()}<div class="main">{sheetbar()}{table(2, states)}</div>{panel}</div>
{statusbar('Rendering 1 of 2 · the sheet stays editable · results are written back when each row finishes')}"""
  return window("Hazard Scene Studio — demo.xlsx", inner)


def viewer() -> str:
  inner = f"""<div class="cmd">{btn('back', '')}{btn('fwd', '')}<div class="sep"></div>
<div style="font-weight:600">F-01/M03/OS-01/W02</div><div style="color:#777;margin-left:8px">1 of 3 drawn rows</div>
<div class="spacer"></div>{btn('cmp', 'Compare with…')}{btn('copy', 'Copy image')}{btn('folder', 'Show in folder')}
{btn('play', 'Make clip (1–4 h)', 'ghost')}</div>
<div style="flex:1;background:#202020;display:flex;align-items:center;justify-content:center;padding:18px">
<img src="img/row-f-01-m03-os-01-w02.jpg" style="max-width:100%;max-height:100%;box-shadow:0 4px 18px rgba(0,0,0,.5)"></div>
<div style="display:flex;gap:10px;padding:10px 14px;background:#f9f9f9;border-top:1px solid #e3e3e3;align-items:center">
<img src="img/row-f-01-m03-os-01-w02.jpg" style="height:56px;border:2px solid #c4402a;border-radius:3px">
<img src="img/row-f-01-m03-os-01-w02-at-night.jpg" style="height:56px;border-radius:3px;opacity:.85">
<img src="img/row-f-01-m03-os-01-w02-at-90-km-h.jpg" style="height:56px;border-radius:3px;opacity:.85">
<div class="spacer"></div><span class="pill ok"><span class="dot"></span>Contact: adjacent car, +2.21 s, 10 km/h</span>
<span class="pill wait">Plant, case F-01b</span><span class="pill bad">Synthetic · no evidence credit</span></div>"""
  return window("Dashboard — F-01/M03/OS-01/W02", inner)


def compare() -> str:
  def side(img, title, tag, cls, outcome):
    return f"""<div style="flex:1;display:flex;flex-direction:column;gap:8px"><div style="display:flex;gap:8px;align-items:center">
<b class="mono" style="color:#eee">{title}</b><span class="pill {cls}">{tag}</span></div><img src="{img}" style="width:100%;border-radius:4px;box-shadow:0 2px 10px rgba(0,0,0,.4)">
<div style="color:#ddd;font-size:12.5px">{outcome}</div></div>"""
  inner = f"""<div class="cmd">{btn('cmp', 'Compare')}<div style="color:#777">two rows side by side; what differs is highlighted</div>
<div class="spacer"></div>{btn('copy', 'Copy both')}</div>
<div style="padding:12px 18px;background:#fff;border-bottom:1px solid #eee;display:flex;gap:18px;font-size:12.5px">
<span><b>Same:</b> environment, motion preset, rating</span><span style="color:#2a59b8"><b>Different:</b> Speed 110 → 90 km/h (Motion)</span>
<span style="color:#a1281a;margin-left:auto"><b>Outcome changed:</b> adjacent car → barrier</span></div>
<div style="flex:1;background:#202020;display:flex;gap:18px;padding:22px;align-items:center">
{side('img/row-f-01-m03-os-01-w02.jpg', 'F-01/M03/OS-01/W02', 'as rated', 'wait', 'Contact with the adjacent car at +2.21 s, 10 km/h relative')}
{side('img/row-f-01-m03-os-01-w02-at-90-km-h.jpg', '… at 90 km/h', 'motion changed', 'run', 'Body reaches the barrier at +3.88 s, 90 km/h')}</div>"""
  return window("Compare — F-01/M03/OS-01/W02 vs at 90 km/h", inner)


def settings() -> str:
  def radio(on, title, sub):
    return (f'<div style="display:flex;gap:10px;padding:8px 0"><div style="width:16px;height:16px;border-radius:50%;'
            f'border:{"5px solid #c4402a" if on else "1.5px solid #888"};margin-top:2px"></div><div><div>{title}</div>'
            f'<div style="color:#666;font-size:12px">{sub}</div></div></div>')
  sec = lambda t, body: f'<div class="card" style="padding:16px 20px;margin-bottom:12px"><div style="font-weight:600;font-size:14px;margin-bottom:8px">{t}</div>{body}</div>'
  path = lambda p, b: (f'<div style="display:flex;gap:8px;align-items:center"><div class="sel ro" style="flex:1">{p}</div>'
                       f'<div class="btn ghost">{b}</div></div>')
  inner = f"""<div class="body"><div class="nav"><h4>Settings</h4><div class="item on">Vehicles</div><div class="item">Rendering</div>
<div class="item">Output</div><div class="item">Methods</div><div class="item">About</div></div>
<div class="main" style="background:#f3f3f3;padding:22px 28px;overflow:hidden"><div style="font-size:22px;font-weight:600;margin-bottom:14px">Vehicles and rendering</div>
{sec('Ego vehicle (your car)', path('C:\\Users\\you\\LionDriver-assets\\corolla-e210\\1450755-gltf-extended.glb', 'Browse…') +
     '<div class="note" style="margin-top:8px">Licensed model: it stays on this PC and is only rendered, never shared or exported. Without it the app draws the stand-in.</div>' +
     '<div style="display:flex;gap:12px;font-size:12.5px;color:#333"><span>✓ glTF/GLB only</span><span>✓ scaled to the plant size 4.63 × 1.78 m</span><span>✓ checksum matches</span></div>')}
{sec('Other road users', radio(True, 'Starter library (unbranded, CC BY)', '6 cars, a van, a truck, a bus; credits printed on each dashboard') +
     radio(False, 'Simple (Kenney CC0)', 'toy look, fastest') + radio(False, 'My own models…', 'GLB files you have the rights to; checked for size'))}
{sec('Quality', radio(False, 'Draft · about 3 min a dashboard', '8 samples, 960 × 540') +
     radio(True, 'Review · about 7 min a dashboard', '16 samples, 1280 × 720 (the gallery)') +
     radio(False, 'Clip · 1 to 4 h a row', 'every frame, MP4; runs in the background'))}
{sec('Where results go', path('beside the sheet: demo-dashboards\\', 'Change…'))}</div></div>
{statusbar('Settings are saved for this PC')}"""
  return window("Hazard Scene Studio — Settings", inner)


SCREENS = {"01-main-window": main_window, "02-add-from-hara": add_from_hara, "03-rendering": rendering,
           "04-dashboard-viewer": viewer, "05-compare": compare, "06-settings": settings}


def main() -> int:
  for name, fn in SCREENS.items():
    html = HERE / f"{name}.html"
    html.write_text(fn())
    subprocess.run([CHROME, "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                    f"--window-size={W},{H}", f"--screenshot={HERE / (name + '.png')}", html.as_uri()],
                   check=True, capture_output=True)
    print(f"{name}.png")
  return 0


if __name__ == "__main__":
  sys.exit(main())
