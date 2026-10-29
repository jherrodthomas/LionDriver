#!/usr/bin/env python3
"""Review pages for the FMEAs that read in GitHub's web view: Markdown plus SVG, no download.

For each of the System FMEA, SW FMEA, DFMEA and PFMEA this writes
  assurance/08-analyses/fmea/exports/review/<analysis>.md          the review page
  assurance/08-analyses/fmea/exports/review/figures/<analysis>-*.svg  its figures
and an index, exports/review/README.md.

A page has: document control and a summary chart; the block/boundary diagram (a process flow for the PFMEA) with
its interface matrix; the P-diagram; structure and functions; the AIAG-VDA worksheet, one table per failure mode,
grouped by structure element; the actions; and a list of the causes that still have action priority H without a
completed action.

The analyses (analyses/<analysis>.yaml) and their diagram data (diagrams/<analysis>.yaml) are the sources of truth.
Regenerate, never edit the output. The SVGs carry their own light and dark palettes and switch with the viewer's
theme. Each figure comes twice: the original drawing (GitHub Primer colours), which the pages embed and which is the
figure of record, and an easier-to-read card version (`-cards.svg`, the neutrals and status tints of the fault tree
and FMEA card views).

Usage:
  tools/safety/fmea_review_md.py            write all pages and figures
  tools/safety/fmea_review_md.py --check    exit 1 if a committed file differs from a fresh build

Requires PyYAML.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fmea_lint

ROOT = fmea_lint.ROOT
FMEA = ROOT / fmea_lint.SAFETY_DIR
ANALYSES = FMEA / "analyses"
DIAGRAMS = FMEA / "diagrams"
OUT = FMEA / "exports" / "review"
FIG = OUT / "figures"
GENERATOR = "tools/safety/fmea_review_md.py"
SOURCES = ["system-fmea", "sw-fmea", "dfmea", "pfmea"]
SHORT = {"system-fmea": "System FMEA", "sw-fmea": "SW FMEA", "dfmea": "DFMEA", "pfmea": "PFMEA"}
STRUCTURE_FIG = {"system-fmea": "fig-3-1-sfm-structure.svg", "dfmea": "fig-3-3-dfm-structure.svg",
                 "sw-fmea": "fig-3-5-swf-structure.svg", "pfmea": "fig-3-8-pfm-structure.svg"}  # drawn by fmea_diagrams.py
AP_BADGE = {"H": "🔴 **H**", "M": "🟠 M", "L": "🟢 L"}
DONE = ("completed", "closed")
NOISE = [("piece_to_piece", "Piece to piece"), ("change_over_time", "Change over time"),
         ("customer_usage", "Customer usage"), ("external_environment", "External environment"),
         ("system_interaction", "System interaction")]

# --------------------------------------------------------------------------------------------------------------------
# SVG

# Two styles. The original figures are the record (figures/<analysis>-*.svg, embedded in the pages); the card style of
# the FMEA and fault tree card views is a second version of each (…-cards.svg). build_all() draws both.
CARDS = False   # the style svg() and rect() draw in; build_all() sets it per figure
STYLE_ORIGINAL = """<style>
.bg{fill:#ffffff}.ink{fill:#1f2328}.mut{fill:#59636e}.acc{fill:#0969da}.surf{fill:#f6f8fa}.box{fill:#ffffff;stroke:#d1d9e0}
.in{fill:#ddf4ff;stroke:#54aeff}.out{fill:#f6f8fa;stroke:#d1d9e0}.bd{fill:none;stroke:#0969da;stroke-dasharray:6 4}.frame{fill:none;stroke:#d1d9e0}
.hS{fill:#ffebe9}.h{fill:#cf222e}.mS{fill:#fff8c5}.m{fill:#9a6700}.lS{fill:#dafbe1}.l{fill:#1a7f37}
.hB{fill:#ffebe9;stroke:#ff8182}.lB{fill:#dafbe1;stroke:#4ac26b}.nB{fill:#fbefff;stroke:#c297ff}.n{fill:#8250df}
.ln{stroke:#59636e;fill:none}.data{stroke:#0969da;fill:none}.energy{stroke:#bc4c00;fill:none;stroke-width:2.2}
.physical{stroke:#59636e;fill:none;stroke-dasharray:5 3}.material{stroke:#1a7f37;fill:none;stroke-dasharray:1.5 3}
.ah{fill:#59636e}.lbl{fill:#ffffff}.lane{fill:#f6f8fa}.laneT{fill:#59636e}
text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",Helvetica,Arial,sans-serif}
.mono{font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace}
@media (prefers-color-scheme: dark){
.bg{fill:#0d1117}.ink{fill:#e6edf3}.mut{fill:#9198a1}.acc{fill:#4493f8}.surf{fill:#151b23}.box{fill:#0d1117;stroke:#3d444d}
.in{fill:#0c2d6b;stroke:#1f6feb}.out{fill:#151b23;stroke:#3d444d}.bd{stroke:#4493f8}.frame{stroke:#3d444d}
.hS{fill:#3c1618}.h{fill:#ff7b72}.mS{fill:#3a2a0c}.m{fill:#d29922}.lS{fill:#12261a}.l{fill:#3fb950}
.hB{fill:#3c1618;stroke:#da3633}.lB{fill:#12261a;stroke:#238636}.nB{fill:#271052;stroke:#8957e5}.n{fill:#ab7df8}
.ln{stroke:#9198a1}.data{stroke:#4493f8}.energy{stroke:#f0883e}.physical{stroke:#9198a1}.material{stroke:#3fb950}
.ah{fill:#9198a1}.lbl{fill:#0d1117}.lane{fill:#151b23}.laneT{fill:#9198a1}}
</style>"""

STYLE_CARDS = """<style>
.bg{fill:#fcfcfb}.dot{fill:#e7e6e0}.ink{fill:#0b0b0b}.mut{fill:#52514e}.acc{fill:#2a78d6}.surf{fill:#f3f2ee}.box{fill:#ffffff;stroke:#e1e0d9}
.in{fill:#eef4fc;stroke:#2a78d6}.out{fill:#f3f2ee;stroke:#e1e0d9}.bd{fill:none;stroke:#2a78d6;stroke-dasharray:6 4}.frame{fill:none;stroke:#e1e0d9}
.hS{fill:#fbe9e9}.h{fill:#9e2424}.mS{fill:#fff5dc}.m{fill:#7a5600}.lS{fill:#e6f5e6}.l{fill:#0a6a0a}
.hB{fill:#fbe9e9;stroke:#d03b3b}.lB{fill:#e6f5e6;stroke:#0ca30c}.nB{fill:#f1eefc;stroke:#6250d6}.n{fill:#6250d6}
.ln{stroke:#898781;fill:none}.data{stroke:#2a78d6;fill:none}.energy{stroke:#eb6834;fill:none;stroke-width:2.2}
.physical{stroke:#898781;fill:none;stroke-dasharray:5 3}.material{stroke:#008300;fill:none;stroke-dasharray:1.5 3}
.ah{fill:#898781}.lbl{fill:#fcfcfb}.lane{fill:#f3f2ee}.laneT{fill:#52514e}
text{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",Helvetica,Arial,sans-serif}
.mono{font-family:"JetBrains Mono",ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace}
@media (prefers-color-scheme: dark){
.bg{fill:#1a1a19}.dot{fill:#262624}.ink{fill:#f2f1ec}.mut{fill:#b5b3ab}.acc{fill:#6aa5ec}.surf{fill:#242422}.box{fill:#242422;stroke:#3a3936}
.in{fill:#1b2a3d;stroke:#4f8fe0}.out{fill:#242422;stroke:#3a3936}.bd{stroke:#6aa5ec}.frame{stroke:#3a3936}
.hS{fill:#4a1f1f}.h{fill:#ffb3b3}.mS{fill:#43361a}.m{fill:#ffd98a}.lS{fill:#1d3a1d}.l{fill:#9fe09f}
.hB{fill:#4a1f1f;stroke:#d03b3b}.lB{fill:#1d3a1d;stroke:#0ca30c}.nB{fill:#2a2347;stroke:#8f80e8}.n{fill:#b0a6f0}
.ln{stroke:#8a8880}.data{stroke:#6aa5ec}.energy{stroke:#f08a5d}.physical{stroke:#8a8880}.material{stroke:#5cc45c}
.ah{fill:#8a8880}.lbl{fill:#1a1a19}.lane{fill:#242422}.laneT{fill:#b5b3ab}}
</style>"""


def svg(w: int, h: int, title: str, body: str) -> str:
  return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">\n' +
          f"<title>{escape(title)}</title>\n{STYLE_CARDS if CARDS else STYLE_ORIGINAL}\n" +
          ('<defs><pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">'
           '<circle class="dot" cx="1.2" cy="1.2" r="1.2"/></pattern></defs>\n'
           f'<rect class="bg" x="0" y="0" width="{w}" height="{h}" rx="12"/>\n'
           f'<rect x="0" y="0" width="{w}" height="{h}" rx="12" fill="url(#dots)"/>\n' if CARDS else
           f'<rect class="bg" x="0" y="0" width="{w}" height="{h}" rx="8"/>\n') + f"{body}</svg>\n")


def wrap(text: str, width: int, max_lines: int = 4) -> list[str]:
  words, lines, cur = " ".join(str(text).split()).split(" "), [], ""
  for w in words:
    if cur and len(cur) + 1 + len(w) > width:
      lines.append(cur)
      cur = w
    else:
      cur = f"{cur} {w}".strip()
  if cur:
    lines.append(cur)
  if len(lines) > max_lines:
    lines = lines[:max_lines]
    lines[-1] = lines[-1][: max(0, width - 1)].rstrip() + "…"
  return lines


def text(x, y, s, cls="ink", size=12, weight=None, anchor="start", mono=False) -> str:
  w = f' font-weight="{weight}"' if weight else ""
  c = f"{cls} mono" if mono else cls
  return f'<text x="{x:.1f}" y="{y:.1f}" class="{c}" font-size="{size}"{w} text-anchor="{anchor}">{escape(str(s))}</text>\n'


def lines_at(x, y, lines, cls="ink", size=12, weight=None, anchor="start", lh=None) -> str:
  lh = lh or size * 1.3
  return "".join(text(x, y + i * lh, s, cls, size, weight, anchor) for i, s in enumerate(lines))


def rect(x, y, w, h, cls, rx=None) -> str:
  rx = (10 if CARDS else 6) if rx is None else rx
  return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" class="{cls}"/>\n'


def link(x1, y1, x2, y2) -> str:
  return f'<path d="M{x1:.1f} {y1:.1f} L{x2:.1f} {y2:.1f}" class="ln" stroke-width="2"/>' + arrow(x1, y1, x2, y2)


def arrow(x1, y1, x2, y2, cls="ah", size=7) -> str:
  a = math.atan2(y2 - y1, x2 - x1)
  p1 = (x2 - size * math.cos(a - 0.4), y2 - size * math.sin(a - 0.4))
  p2 = (x2 - size * math.cos(a + 0.4), y2 - size * math.sin(a + 0.4))
  return f'<path d="M{x2:.1f} {y2:.1f} L{p1[0]:.1f} {p1[1]:.1f} L{p2[0]:.1f} {p2[1]:.1f} Z" class="{cls}"/>\n'


# --------------------------------------------------------------------------------------------------------------------
# Figures


def summary_svg(name: str, doc: dict, c: dict) -> str:
  w, h = 880, 168
  b = text(24, 34, f"{SHORT[name]}: action priority of its {c['causes']} causes ({c['fm']} failure modes)", "ink", 15, 600)
  x0, bw, y = 24, w - 48, 52
  total = max(1, c["causes"])
  x = x0
  for k, cls in (("H", "h"), ("M", "m"), ("L", "l")):
    seg = bw * c["ap"][k] / total
    if seg > 0:
      b += f'<rect x="{x:.1f}" y="{y}" width="{seg:.1f}" height="30" class="{cls}S"/>\n'
      if seg > 64:
        b += text(x + 10, y + 20, f"{k}  {c['ap'][k]}", cls, 13, 700)
      x += seg
  b += f'<rect x="{x0}" y="{y}" width="{bw}" height="30" rx="4" class="frame"/>\n'
  tiles = [(f"{c['ap']['H']}", "causes with priority H", "h"), (f"{c['h_open']}", "H without a completed action", "h"),
           (f"{c['open']} of {c['actions']}", "actions still open", "acc"), (f"S {c['max_s']}", "highest severity", "ink")]
  tw = bw / len(tiles)
  for i, (num, lab, cls) in enumerate(tiles):
    tx = x0 + i * tw
    b += text(tx, y + 72, num, cls, 24, 700) + text(tx, y + 94, lab, "mut", 12)
  return svg(w, h, f"{SHORT[name]} summary: action priority of {c['causes']} causes", b)


def msr_rows(doc) -> list[tuple[dict, dict]]:
  return [(fm, cz) for fm in doc["failure_modes"] for cz in fm["causes"] if cz.get("msr")]


def msr_coverage(name: str, doc: dict) -> dict:
  kind = doc["analysis"]["type"]
  scope = [cz for fm in doc["failure_modes"] for cz in fm["causes"] if fmea_lint.msr_in_scope(kind, fm)]
  rated = msr_rows(doc)
  return {"in_scope": len(scope), "rated": len(rated), "exempt": sum(1 for cz in scope if cz.get("msr_exempt")),
          "applies": kind in fmea_lint.MSR_TYPES}


def msr_svg(name: str, doc: dict) -> str:
  """Frequency x monitoring grid of the MSR rows; cell colour = MSR AP at S 10, number = causes in the cell."""
  rows = msr_rows(doc)
  cell_w, cell_h, x0, y0 = 58, 26, 92, 74
  w, h = x0 + 10 * cell_w + 196, y0 + 10 * cell_h + 66
  b = text(24, 32, f"{SHORT[name]}: {len(rows)} monitoring and system response ratings by frequency and monitoring", "ink", 15, 600)
  b += text(24, 52, "Cell colour: MSR action priority at S 10 (handbook table, RT-3). Number: causes rated in that cell.", "mut", 12)
  grid: dict = {}
  for _fm, cz in rows:
    m = cz["msr"]
    grid[(m["frequency"], m["monitoring"])] = grid.get((m["frequency"], m["monitoring"]), 0) + 1
  cls = {"H": "h", "M": "m", "L": "l"}
  for fi, f in enumerate(range(10, 0, -1)):
    y = y0 + fi * cell_h
    b += text(x0 - 10, y + 17, f"F {f}", "mut", 11, anchor="end")
    for m in range(1, 11):
      x = x0 + (m - 1) * cell_w
      ap = fmea_lint.compute_ap_msr(10, 10, f, m)
      b += f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_w - 2}" height="{cell_h - 2}" rx="3" class="{cls[ap]}S"/>\n'
      n = grid.get((f, m))
      if n:
        b += text(x + (cell_w - 2) / 2, y + 17, n, cls[ap], 13, 700, anchor="middle")
  for m in range(1, 11):
    b += text(x0 + (m - 1) * cell_w + (cell_w - 2) / 2, y0 + 10 * cell_h + 16, f"M {m}", "mut", 11, anchor="middle")
  bands = [(1, 4, "measured timing"), (5, 6, "code-derived timing"), (7, 8, "not shown or too slow"), (9, 10, "no monitor")]
  for lo, hi, lab in bands:
    xa, xb = x0 + (lo - 1) * cell_w, x0 + hi * cell_w - 2
    yb = y0 + 10 * cell_h + 26
    b += f'<path d="M{xa:.1f} {yb} L{xb:.1f} {yb}" class="ln" stroke-width="1.5"/>\n'
    b += text((xa + xb) / 2, yb + 16, lab, "mut", 11, anchor="middle")
  lx = x0 + 10 * cell_w + 22
  b += text(lx, y0 + 12, "Reads left to right:", "ink", 12, 600)
  b += lines_at(lx, y0 + 32, wrap("better monitoring moves a cause left; at S 10 only F 1–4 can leave H.", 26, 4),
                "mut", 11)
  for i, (k, lab) in enumerate((("H", "priority H"), ("M", "priority M"), ("L", "priority L"))):
    yy = y0 + 112 + i * 24
    b += f'<rect x="{lx}" y="{yy}" width="16" height="16" rx="3" class="{cls[k]}S"/>\n' + text(lx + 24, yy + 13, lab, "ink", 12)
  return svg(w, h, f"{SHORT[name]} FMEA-MSR: frequency by monitoring", b)


def msr_timing(t: dict) -> str:
  basis = {"measured": "measured", "code_derived": "code-derived", "unknown": "unknown"}[t["basis"]]
  if t.get("ftti_ref") and t.get("ftti_ms") is None:
    return f"per frame; reaction {t.get('frti_ms', '?'):g} ms ({basis})"
  if t.get("fdti_ms") is not None and t.get("frti_ms") is not None:
    total = t["fdti_ms"] + t["frti_ms"]
    vs = ""
    if t.get("ftti_ms") is not None:
      vs = f" vs FTTI {t['ftti_ms']:g} ms " + ("✅" if total <= t["ftti_ms"] else "❌")
    return f"{t['fdti_ms']:g} + {t['frti_ms']:g} ms{vs} ({basis})"
  return basis


def block_svg(name: str, bd: dict) -> str:
  blocks = {b["id"]: b for b in bd["blocks"]}
  cols = max(b["column"] for b in blocks.values()) + 1
  rows = max(b["row"] for b in blocks.values()) + 1
  bw, bh, gx, gy, mx, my = 168, 58, 48, 46, 30, 70
  w = mx * 2 + cols * bw + (cols - 1) * gx
  h = my + rows * bh + (rows - 1) * gy + 110
  pos = {i: (mx + b["column"] * (bw + gx), my + b["row"] * (bh + gy)) for i, b in blocks.items()}
  out = text(mx, 30, bd["title"], "ink", 15, 600)
  ins = [pos[i] for i, b in blocks.items() if b.get("inside")]
  if ins:
    x1, y1 = min(p[0] for p in ins) - 14, min(p[1] for p in ins) - 22
    x2, y2 = max(p[0] for p in ins) + bw + 14, max(p[1] for p in ins) + bh + 14
    out += f'<rect x="{x1}" y="{y1}" width="{x2 - x1}" height="{y2 - y1}" rx="10" class="bd"/>\n'
    out += text(x1 + 10, y1 + 14, bd["boundary"], "acc", 11, 600)
  # interfaces under the blocks
  pair_n: dict = {}
  chan_n: dict = {}
  taken = [(x - 2, y - 2, x + bw + 2, y + bh + 2) for x, y in pos.values()]
  lines = ""
  labels = ""
  for itf in bd["interfaces"]:
    a, z = itf["from"], itf["to"]
    key = tuple(sorted((a, z)))
    k = pair_n.get(key, 0)
    pair_n[key] = k + 1
    off = (k - 0.5) * 12 if k else 0
    (ax, ay), (zx, zy) = pos[a], pos[z]
    acx, acy, zcx, zcy = ax + bw / 2, ay + bh / 2, zx + bw / 2, zy + bh / 2
    if abs(acy - zcy) < 1:  # same row
      sx, ex = (ax + bw, zx) if zcx > acx else (ax, zx + bw)
      pts = [(sx, acy + off), (ex, zcy + off)]
    elif abs(acx - zcx) < 1:  # same column
      sy, ey = (ay + bh, zy) if zcy > acy else (ay, zy + bh)
      pts = [(acx + off, sy), (zcx + off, ey)]
    else:
      sx, ex = (ax + bw, zx) if zcx > acx else (ax, zx + bw)
      ch = round((sx + ex) / 2)
      n = chan_n.get(ch, 0)
      chan_n[ch] = n + 1
      midx = ch + (n // 2 + 1) * 7 * (1 if n % 2 else -1) * (1 if n else 0)
      pts = [(sx, acy + off), (midx, acy + off), (midx, zcy + off), (ex, zcy + off)]
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    lines += f'<path d="{d}" class="{itf["type"]}"/>\n'
    lines += arrow(*pts[-2], *pts[-1])
    if itf.get("both_ways"):
      lines += arrow(*pts[1], *pts[0])
    tw = 7 + 6.1 * len(itf["id"])
    segs = sorted(zip(pts, pts[1:], strict=False), key=lambda s: -(abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1])))
    spot = None
    for (p0, p1) in segs:
      for t in (0.5, 0.35, 0.65, 0.22, 0.78, 0.12, 0.88):
        lx, ly = p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t
        box = (lx - tw / 2 - 2, ly - 9, lx + tw / 2 + 2, ly + 8)
        if not any(box[0] < b[2] and b[0] < box[2] and box[1] < b[3] and b[1] < box[3] for b in taken):
          spot = (lx, ly, box)
          break
      if spot:
        break
    if not spot:
      p0, p1 = segs[0]
      lx, ly = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
      spot = (lx, ly, (lx - tw / 2, ly - 8, lx + tw / 2, ly + 7))
    lx, ly, box = spot
    taken.append(box)
    labels += rect(lx - tw / 2, ly - 8, tw, 15, "lbl", 3) + text(lx, ly + 3.5, itf["id"], "mut", 10, 600, "middle", True)
  out += lines
  for i, b in blocks.items():
    x, y = pos[i]
    out += rect(x, y, bw, bh, "in" if b.get("inside") else "out")
    out += lines_at(x + 10, y + 21, wrap(b["name"], 24, 2), "ink", 12, 600, lh=14)
    det = b.get("detail") or ""
    nl = len(wrap(b["name"], 24, 2))
    out += lines_at(x + 10, y + 21 + nl * 14, wrap(det, 28, 3 - nl), "mut", 10.5, lh=12.5)
  out += labels
  ly = h - 30
  lx = mx
  for t, lab in (("data", "data / signal"), ("energy", "energy"), ("physical", "physical / mechanical"), ("material", "material")):
    out += f'<path d="M{lx} {ly} L{lx + 34} {ly}" class="{t}"/>\n' + text(lx + 40, ly + 4, lab, "mut", 11)
    lx += 60 + 6.5 * len(lab)
  out += rect(lx + 10, ly - 9, 28, 18, "in", 3) + text(lx + 44, ly + 4, "analysed element", "mut", 11)
  out += rect(lx + 160, ly - 9, 28, 18, "out", 3) + text(lx + 194, ly + 4, "outside the boundary", "mut", 11)
  return svg(w, h, bd["title"], out)


def flow_svg(name: str, pf: dict) -> str:
  steps, lanes = pf["steps"], pf["lanes"]
  row_in_lane: dict = {}
  pos = {}
  sw, sh, gy, cw, top = 190, 46, 26, 250, 74
  for s in steps:
    li = lanes.index(s["lane"])
    r = row_in_lane.get(li, 0)
    row_in_lane[li] = r + 1
    pos[s["id"]] = (24 + li * cw + (cw - sw) / 2, top + r * (sh + gy))
  rows = max(row_in_lane.values())
  w = 48 + len(lanes) * cw
  h = top + rows * (sh + gy) + 80
  out = text(24, 30, pf["title"], "ink", 15, 600)
  for li, lane in enumerate(lanes):
    x = 24 + li * cw
    out += rect(x + 6, 44, cw - 12, h - 44 - 46, "lane", 8) + text(x + cw / 2, 62, lane.upper(), "laneT", 11, 700, "middle")
  back = 0
  for s in steps:
    x, y = pos[s["id"]]
    for n in s.get("next", []):
      if n not in pos:
        continue
      nx, ny = pos[n]
      if abs(nx - x) < 1 and ny > y:  # down the same lane
        pts = [(x + sw / 2, y + sh), (x + sw / 2, ny)]
      elif abs(nx - x) < 1:  # back up the same lane: along its right edge
        back += 1
        rx = x + sw + 10 + 6 * back
        pts = [(x + sw, y + sh / 2), (rx, y + sh / 2), (rx, ny + sh / 2), (nx + sw, ny + sh / 2)]
      elif nx > x:  # into a later lane
        mx = x + sw + (nx - x - sw) / 2
        pts = [(x + sw, y + sh / 2), (mx, y + sh / 2), (mx, ny + sh / 2), (nx, ny + sh / 2)]
      else:  # back to an earlier lane: along the bottom, then up the target lane's left edge
        back += 1
        yb = h - 52 - 5 * back
        lxe = nx - 14 - 5 * back
        pts = [(x + sw / 2, y + sh), (x + sw / 2, yb), (lxe, yb), (lxe, ny + sh / 2), (nx, ny + sh / 2)]
      out += f'<path d="M{" L".join(f"{a:.1f} {b:.1f}" for a, b in pts)}" class="ln"/>\n' + arrow(*pts[-2], *pts[-1])
  for s in steps:
    x, y = pos[s["id"]]
    kind = s.get("kind", "operation")
    cls = {"operation": "in", "inspection": "lB", "decision": "nB", "handover": "out"}[kind]
    if kind == "decision":
      cx, cy = x + sw / 2, y + sh / 2
      out += f'<path d="M{cx} {y - 5} L{x + sw} {cy} L{cx} {y + sh + 5} L{x} {cy} Z" class="{cls}"/>\n'
    else:
      out += rect(x, y, sw, sh, cls, 18 if kind == "handover" else 6)
    lines = wrap(s["name"], 22 if kind != "decision" else 18, 2)
    out += lines_at(x + sw / 2, y + sh / 2 - (len(lines) - 1) * 7 + 4, lines, "ink", 11.5, 600, "middle", 14)
    out += text(x + 5, y - 3, s["id"], "mut", 9, 600, mono=True)
  ly = h - 14
  lx = 24
  for cls, lab in (("in", "operation"), ("lB", "inspection / check"), ("nB", "decision / gate"), ("out", "handover")):
    out += rect(lx, ly - 10, 22, 13, cls, 3) + text(lx + 28, ly + 1, lab, "mut", 11)
    lx += 46 + 6.3 * len(lab)
  return svg(int(w), int(h), pf["title"], out)


def p_svg(name: str, pd: dict, fm_titles: dict) -> str:
  w = 980
  col_w, gap = 176, 12
  # noise row
  noise_lines = []
  for key, lab in NOISE:
    items = []
    for t in pd["noise_factors"].get(key, []):
      items += wrap("• " + t, 27, 3)
    noise_lines.append((lab, items))
  nh = 34 + max(len(i) for _, i in noise_lines) * 14
  y0 = 50
  out = text(24, 30, pd["title"], "ink", 15, 600)
  nx0 = (w - (5 * col_w + 4 * gap)) / 2
  for i, (lab, items) in enumerate(noise_lines):
    x = nx0 + i * (col_w + gap)
    out += rect(x, y0, col_w, nh, "nB") + text(x + 10, y0 + 19, lab, "n", 12, 700)
    out += lines_at(x + 10, y0 + 38, items, "ink", 11, lh=14)
  out += text(w / 2, y0 + nh + 20, "NOISE FACTORS", "n", 11, 700, "middle")
  # middle row
  my = y0 + nh + 40
  inp = [ln for t in pd["inputs"] for ln in wrap("• " + t, 30, 2)]
  outs = [ln for t in pd["ideal_outputs"] for ln in wrap("• " + t, 30, 2)]
  errs = []
  for e in pd["error_states"]:
    errs += wrap("• " + e["text"], 30, 2)
    errs += ["   " + ln for ln in wrap(", ".join(e["failure_modes"]), 28, 3)]
  focus = wrap(pd["focus"], 26, 3)
  fns = (["Functions covered:"] + wrap(", ".join(pd.get("functions", [])), 38, 6)) if pd.get("functions") else []
  side_w, mid_w = 230, 290
  ih = 34 + len(inp) * 14
  oh = 34 + len(outs) * 14
  eh = 34 + len(errs) * 14
  ch = max(ih, oh + eh + 14, 60 + len(focus) * 17 + len(fns) * 13)
  lx, cx, rx = 24, 24 + side_w + 46, 24 + side_w + 46 + mid_w + 46
  out += rect(lx, my + (ch - ih) / 2, side_w, ih, "box") + text(lx + 12, my + (ch - ih) / 2 + 20, "INPUTS", "acc", 11, 700)
  out += lines_at(lx + 12, my + (ch - ih) / 2 + 38, inp, "ink", 11, lh=14)
  out += rect(cx, my, mid_w, ch, "in", 10)
  inner = len(focus) * 17 + 14 + len(fns) * 13
  fy = my + max(30, (ch - inner) / 2 + 12)
  out += lines_at(cx + mid_w / 2, fy, focus, "ink", 14, 700, "middle", 17)
  out += lines_at(cx + 16, fy + len(focus) * 17 + 8, fns, "mut", 10.5, lh=13)
  out += rect(rx, my, side_w, oh, "lB") + text(rx + 12, my + 20, "IDEAL FUNCTION (OUTPUTS)", "l", 11, 700)
  out += lines_at(rx + 12, my + 38, outs, "ink", 11, lh=14)
  ey = my + oh + 14
  out += rect(rx, ey, side_w, eh, "hB") + text(rx + 12, ey + 20, "ERROR STATES → FAILURE MODES", "h", 11, 700)
  for i, ln in enumerate(errs):
    out += text(rx + 12, ey + 38 + i * 14, ln, "mut" if ln.startswith("   ") else "ink", 10.5 if ln.startswith("   ") else 11,
                mono=ln.startswith("   "))
  # arrows
  out += link(lx + side_w, my + ch / 2, cx, my + ch / 2)
  out += link(cx + mid_w, my + oh / 2, rx, my + oh / 2)
  out += link(cx + mid_w, ey + eh / 2, rx, ey + eh / 2)
  out += link(cx + mid_w / 2, y0 + nh + 28, cx + mid_w / 2, my)
  # control factors
  cy = my + ch + 34
  ctl = [ln for c in pd["control_factors"] for ln in wrap("• " + c["text"], 52, 2)]
  half = (len(ctl) + 1) // 2
  chh = 34 + half * 14
  cw = 2 * side_w + mid_w + 92
  out += link(cx + mid_w / 2, cy, cx + mid_w / 2, my + ch)
  out += rect(lx, cy, cw, chh, "surf") + text(lx + 12, cy + 20, "CONTROL FACTORS (WHAT THE DESIGN SETS)", "acc", 11, 700)
  out += lines_at(lx + 12, cy + 38, ctl[:half], "ink", 11, lh=14) + lines_at(lx + cw / 2 + 6, cy + 38, ctl[half:], "ink", 11, lh=14)
  h = cy + chh + 20
  return svg(w, int(h), pd["title"], out)


# --------------------------------------------------------------------------------------------------------------------
# Page


def one(s) -> str:
  return " ".join(str(s).split()).replace("|", "\\|")


def counts(doc) -> dict:
  ap = {"H": 0, "M": 0, "L": 0}
  causes = h_open = 0
  acts = {a["id"]: a for a in doc.get("actions", [])}
  for fm in doc["failure_modes"]:
    for c in fm["causes"]:
      causes += 1
      ap[c.get("ap")] = ap.get(c.get("ap"), 0) + 1
      if c.get("ap") == "H" and not any(acts.get(a, {}).get("status") in DONE for a in c.get("actions", [])):
        h_open += 1
  open_n = sum(1 for a in doc.get("actions", []) if a.get("status") not in DONE)
  return {"fm": len(doc["failure_modes"]), "causes": causes, "ap": ap, "actions": len(doc.get("actions", [])),
          "open": open_n, "h_open": h_open, "max_s": max((fm["severity"] for fm in doc["failure_modes"]), default=0)}


def anchor(s: str) -> str:
  s = re.sub(r"[^\w\- ]", "", s.lower()).strip().replace(" ", "-")
  return s


def controls_md(lst) -> str:
  out = []
  for c in lst or []:
    ref = c.get("test") or c.get("ref")
    out.append("• " + one(c["description"]) + (f" <sub>{one(ref)}</sub>" if ref else ""))
  return "<br>".join(out) or "—"


def page(name: str, doc: dict, dg: dict | None, c: dict) -> str:
  a = doc["analysis"]
  els = {e["id"]: e for e in doc["structure"]}
  fns = {f["id"]: f for f in doc["functions"]}
  acts = {x["id"]: x for x in doc.get("actions", [])}
  L = [f"# {SHORT[name]} review: {one(a['title']).split('—', 1)[-1].strip()}", "",
       f"> Generated from [`analyses/{name}.yaml`](../../analyses/{name}.yaml)"
       + (f" and [`diagrams/{name}.yaml`](../../diagrams/{name}.yaml)" if dg else "")
       + f" by `{GENERATOR}`. Edit the YAML and regenerate; never edit this page. " +
       f"A styled workbook of the same data is [`{name}-review.xlsx`]({name}-review.xlsx).", "",
       "| Revision | Status | Baseline | Rating tables | Updated |", "|---|---|---|---|---|",
       f"| {a.get('revision', '')} | {a.get('status', '')} | {a.get('baseline', '')} | {a.get('rating_tables', '')} | {a.get('updated', '')} |", "",
       f"**Scope.** {one(a.get('scope', ''))}", "",
       "**Team.** " + "; ".join(f"{one(t['name'])} ({one(t['role'])})" for t in a.get("team", [])), "",
       f"![Summary](figures/{name}-summary.svg)", "",
       "## How to review", "",
       "Read the diagrams first, then the worksheet. Comment on this page's lines in a pull request, or open an issue " +
       "that names the failure mode or cause ID. For a rating, say which value you would give and why; the scales are in " +
       "[rating-tables.md](../../rating-tables.md). Action priority follows the AIAG-VDA table and is checked by " +
       "`fmea_lint.py`, so challenge S, O or D, not the AP.", "",
       "## Contents", ""]
  sections = []
  if dg and dg.get("block_diagram"):
    sections.append("1. Block and boundary diagram")
  if dg and dg.get("process_flow"):
    sections.append("1. Process flow")
  if dg and dg.get("p_diagram"):
    sections.append("2. P-diagram")
  sections += ["3. Structure and functions", "4. Worksheet", "5. Actions", "6. Priority H causes without a completed action"]
  mc = msr_coverage(name, doc)
  if mc["applies"]:
    sections.append("7. Monitoring and system response")
  for s in sections:
    title = s.split(". ", 1)[1]
    L.append(f"- [{title}](#{anchor(s)})")
  L.append("")
  if dg and dg.get("block_diagram"):
    bd = dg["block_diagram"]
    blocks = {b["id"]: b for b in bd["blocks"]}
    L += ["## 1. Block and boundary diagram", "", f"![{one(bd['title'])}](figures/{name}-block.svg)", "",
          "**Interface matrix.** Each line in the diagram, with what crosses it.", "",
          "| ID | From | To | Type | What crosses | Source |", "|---|---|---|---|---|---|"]
    for i in bd["interfaces"]:
      arrow_s = " ⇄ " if i.get("both_ways") else ""
      L.append(f"| {i['id']} | {one(blocks[i['from']]['name'])} | {one(blocks[i['to']]['name'])} | {i['type']}{arrow_s} | " +
               f"{one(i['label'])} | <sub>{one(i.get('ref', ''))}</sub> |")
    L.append("")
  if dg and dg.get("process_flow"):
    pf = dg["process_flow"]
    L += ["## 1. Process flow", "", f"![{one(pf['title'])}](figures/{name}-flow.svg)", "",
          "| Step | Name | Lane | Kind | Process element |", "|---|---|---|---|---|"]
    for s in pf["steps"]:
      el = els.get(s.get("element"), {}).get("name", "")
      L.append(f"| {s['id']} | {one(s['name'])} | {s['lane']} | {s.get('kind', 'operation')} | {s.get('element', '')} {one(el)} |")
    L.append("")
  if dg and dg.get("p_diagram"):
    pd = dg["p_diagram"]
    L += ["## 2. P-diagram", "", f"![{one(pd['title'])}](figures/{name}-p-diagram.svg)", ""]
    if pd.get("functions"):
      L += ["| Function covered | Description |", "|---|---|"]
      L += [f"| `{f}` | {one(fns.get(f, {}).get('description', ''))} |" for f in pd["functions"]]
      L.append("")
    L += ["| Control factor | Source |", "|---|---|"]
    L += [f"| {one(cf['text'])} | <sub>{one(cf.get('ref', ''))}</sub> |" for cf in pd["control_factors"]]
    L.append("")
  L += ["## 3. Structure and functions", ""]
  sf = STRUCTURE_FIG.get(name)
  if sf and (FMEA / "figures" / "generated" / sf).is_file():
    L += [f"![Structure tree](../../figures/generated/{sf})", "",
          "The failure chains (element → function → failure mode → causes) are drawn in " +
          "[figures/generated](../../figures/generated/README.md).", ""]
  L += ["| Element | Kind | Functions |", "|---|---|---|"]
  for e in doc["structure"]:
    depth = 0
    p = e.get("parent")
    while p:
      depth += 1
      p = els.get(p, {}).get("parent")
    f_list = "<br>".join(f"`{f['id']}` {one(f['description'])}" for f in doc["functions"] if f["element"] == e["id"]) or "—"
    L.append(f"| {'&nbsp;&nbsp;&nbsp;' * depth}`{e['id']}` {one(e['name'])} | {e['kind']} | {f_list} |")
  L += ["", "## 4. Worksheet", "",
        "One table per failure mode, grouped by structure element. S is the failure mode's severity (its worst end " +
        "effect); each cause has its own occurrence (O), detection (D) and action priority (AP).", ""]
  by_el: dict = {}
  for fm in doc["failure_modes"]:
    by_el.setdefault(fm["element"], []).append(fm)
  for eid in [e["id"] for e in doc["structure"] if e["id"] in by_el]:
    L += [f"### `{eid}` {one(els[eid]['name'])}", ""]
    for fm in by_el[eid]:
      aps = [cz.get("ap") for cz in fm["causes"]]
      worst = "H" if "H" in aps else "M" if "M" in aps else "L"
      L += [f"#### {fm['id']} · {one(fm['failure_mode'])}", "",
            f"{AP_BADGE[worst]} · **S {fm['severity']}** · guideword *{fm.get('guideword', '')}* · function " +
            f"`{fm['function']}` {one(fns.get(fm['function'], {}).get('description', ''))}", ""]
      order = {"end": 0, "next_higher": 1, "local": 2}
      lab = {"end": "End", "next_higher": "Next higher", "local": "Local"}
      eff = []
      for e in sorted(fm["effects"], key=lambda e: order.get(e["level"], 3)):
        hz = f" ({e['hazard']}, S {e.get('severity', '')})" if e.get("hazard") else ""
        eff.append(f"**{lab.get(e['level'], e['level'])}:** {one(e['description'])}{hz}")
      L += ["Effects:", ""] + [f"- {x}" for x in eff] + ["",
            "| Cause | Prevention | Detection | O | D | AP | Actions |", "|---|---|---|:-:|:-:|:-:|---|"]
      for cz in fm["causes"]:
        al = ", ".join(cz.get("actions", [])) or "—"
        L.append(f"| `{cz['id']}` {one(cz['description'])} | {controls_md(cz.get('prevention_controls'))} | " +
                 f"{controls_md(cz.get('detection_controls'))} | {cz.get('occurrence', '')} | {cz.get('detection', '')} | " +
                 f"{AP_BADGE.get(cz.get('ap'), cz.get('ap', ''))} | {al} |")
      sm = fm.get("safety_mechanisms") or []
      if sm:
        L += ["", "Safety mechanisms: " + " · ".join(f"({i}) {one(s['description'])}" for i, s in enumerate(sm, 1))]
      msr_lines = []
      for cz in fm["causes"]:
        if cz.get("msr"):
          m = cz["msr"]
          msr_lines.append(f"`{cz['id']}` mechanism {', '.join(str(i) for i in m['mechanisms'])}: M {m['monitoring']} · " +
                           f"F {m['frequency']} · S after response {m['severity_after']} → {AP_BADGE.get(m['ap'], m['ap'])}")
        elif cz.get("msr_exempt"):
          msr_lines.append(f"`{cz['id']}` not rated here: {one(cz['msr_exempt'])}")
      if msr_lines:
        L += ["", f"[Monitoring and system response](#{anchor('7. Monitoring and system response')}): " + "<br>".join(msr_lines)]
      if fm.get("notes"):
        L += ["", f"<sub>Note: {one(fm['notes'])}</sub>"]
      L.append("")
  L += ["## 5. Actions", "", "| ID | Kind | Action | Owner | Status | Causes | Revised S/O/D → AP |", "|---|---|---|---|---|---|---|"]
  cause_of: dict = {}
  for fm in doc["failure_modes"]:
    for cz in fm["causes"]:
      for x in cz.get("actions", []):
        cause_of.setdefault(x, []).append(cz["id"])
  for x in doc.get("actions", []):
    rv = x.get("revised")
    rvs = f"{rv['severity']}/{rv['occurrence']}/{rv['detection']} → {AP_BADGE.get(rv.get('ap'), rv.get('ap'))}" if rv else "—"
    L.append(f"| {x['id']} | {x.get('kind', '')} | {one(x['description'])} | {one(x.get('owner', ''))} | {x.get('status', '')} | " +
             f"{', '.join(cause_of.get(x['id'], [])) or '—'} | {rvs} |")
  L += ["", "## 6. Priority H causes without a completed action", ""]
  rows = []
  for fm in doc["failure_modes"]:
    for cz in fm["causes"]:
      if cz.get("ap") == "H" and not any(acts.get(x, {}).get("status") in DONE for x in cz.get("actions", [])):
        rows.append(f"| `{cz['id']}` | {one(fm['failure_mode'])} | {fm['severity']}/{cz.get('occurrence')}/{cz.get('detection')} | " +
                    f"{', '.join(cz.get('actions', [])) or '**none**'} |")
  if rows:
    L += ["| Cause | Failure mode | S/O/D | Open actions |", "|---|---|---|---|"] + rows
  else:
    L.append("None.")
  L.append("")
  if mc["applies"]:
    L += ["## 7. Monitoring and system response", "",
          "FMEA-MSR rates what happens in the car when a cause occurs: does a diagnostic catch it, and does the system reach a " +
          "safe state within the fault-tolerant time interval (FTTI)? It adds frequency (F), monitoring (M) and the severity " +
          "after the response, with its own action priority; S, O, D and AP above are unchanged. Scales: " +
          "[rating-tables.md §7](../../rating-tables.md#7-fmea-msr--monitoring-and-system-response-added-in-rt-2); scope and " +
          "plan: [msr-plan.md](../../msr-plan.md); FTTI rows: " +
          "[WP-S-04 §3.7](../../../../03-system/WP-S-04-timing-ftti-budget.md#37-summary-of-fttis-and-budgets).", "",
          f"**Coverage:** {mc['rated']} of {mc['in_scope']} in-scope causes rated, {mc['exempt']} rated elsewhere " +
          f"(`msr: {doc['analysis'].get('msr', 'none')}`).", ""]
    if any(fmea_lint.msr_ap_provisional(fm["severity"]) for fm, cz in msr_rows(doc)):
      L += ["> [!WARNING]", "> Rows with S 1–8 use a provisional MSR AP stand-in until those AIAG-VDA handbook pages are " +
            "transcribed (rating-tables §7.4); their AP will be re-rated. S 9–10 use the handbook table.", ""]
    rated = msr_rows(doc)
    if rated:
      L += [f"![Frequency by monitoring](figures/{name}-msr.svg)", "",
            "Sorted by monitoring, weakest first. Timing is detection + reaction time against the FTTI of the cited WP-S-04 row.", "",
            "| Cause | Diagnostic → system response | Timing | S after | F | M | MSR AP | Actions |",
            "|---|---|---|:-:|:-:|:-:|:-:|---|"]
      for _fm, cz in sorted(rated, key=lambda r: (-r[1]["msr"]["monitoring"], -r[1]["msr"]["frequency"], r[1]["id"])):
        m = cz["msr"]
        act = ", ".join(m.get("actions", [])) or (f"<sub>{one(m['rationale'])}</sub>" if m.get("rationale") else "—")
        L.append(f"| `{cz['id']}` {one(cz['description'])} | {one(m['diagnostic'])} → {one(m['system_response'])} | " +
                 f"{msr_timing(m['timing'])} | {m['severity_after']} | {m['frequency']} | **{m['monitoring']}** | " +
                 f"{AP_BADGE.get(m['ap'], m['ap'])} | {act} |")
      L.append("")
    else:
      L += ["No cause is rated yet.", ""]
  return "\n".join(L)


def index(all_counts: dict, docs: dict) -> str:
  L = ["# FMEA review pages", "",
       f"Generated by `{GENERATOR}` from the analyses in [`../../analyses/`](../../analyses/). Each page reads in " +
       "GitHub's web view: diagrams, then the AIAG-VDA worksheet, then actions. The `.xlsx` files hold the same data " +
       "as styled workbooks for offline review.", "",
       "| Analysis | Revision | Failure modes | Causes | AP H | H without completed action | Actions open | MSR rated | Workbook |",
       "|---|---|---:|---:|---:|---:|---:|---:|---|"]
  for n in SOURCES:
    c, a = all_counts[n], docs[n]["analysis"]
    L.append(f"| [{SHORT[n]}]({n}.md) | {a.get('revision', '')} ({a.get('status', '')}) | {c['fm']} | {c['causes']} | {c['ap']['H']} | " +
             f"{c['h_open']} | {c['open']}/{c['actions']} | {c['msr']} | [xlsx]({n}-review.xlsx) |")
  L += ["", "## Hardware metrics (FMEDA)", "",
        "Written by `tools/safety/fmeda_review_md.py` and `tools/safety/export_fmeda_xlsx.py --all`.", "",
        "| FMEDA | Revision | Goals and ASIL targets | Workbook |", "|---|---|---|---|"]
  for n in ("fmeda-sg001", "fmeda-sg009"):
    a = fmea_lint.load_yaml((ANALYSES / f"{n}.yaml").read_text())["analysis"]
    goals = ", ".join(f"{t['goal']} {t['asil']}" for t in a.get("targets", [])) or f"{a['safety_goal']} {a['asil_target']}"
    L.append(f"| [{a['title'].split(',')[0]}]({n}.md) | {a['revision']} ({a['status']}) | {goals} | [xlsx]({n}-review.xlsx) |")
  L += ["", "Ratings and the action-priority table: [rating-tables.md](../../rating-tables.md). The plan and method: " +
        "[fmea-plan.md](../../fmea-plan.md).", ""]
  return "\n".join(L)


# --------------------------------------------------------------------------------------------------------------------
# Diagram data checks


def check_diagram(name: str, doc: dict, dg: dict) -> list[str]:
  errs = []
  els = {e["id"] for e in doc["structure"]}
  fns = {f["id"] for f in doc["functions"]}
  fms = {f["id"] for f in doc["failure_modes"]}
  where = f"diagrams/{name}.yaml"
  if dg.get("schema_version") != 1:
    errs.append(f"{where}: schema_version must be 1")
  bd = dg.get("block_diagram")
  if bd:
    ids = set()
    for b in bd["blocks"]:
      ids.add(b["id"])
      if b.get("element") and b["element"] not in els:
        errs.append(f"{where}: block {b['id']} names unknown element {b['element']}")
      for k in ("column", "row"):
        if not isinstance(b.get(k), int):
          errs.append(f"{where}: block {b['id']} needs an integer {k}")
    seen = set()
    for b in bd["blocks"]:
      p = (b.get("column"), b.get("row"))
      if p in seen:
        errs.append(f"{where}: block {b['id']} overlaps another at column/row {p}")
      seen.add(p)
    for i in bd["interfaces"]:
      if i["from"] not in ids or i["to"] not in ids:
        errs.append(f"{where}: interface {i['id']} joins an unknown block")
      if i["type"] not in ("data", "energy", "physical", "material"):
        errs.append(f"{where}: interface {i['id']} has unknown type {i['type']}")
  pf = dg.get("process_flow")
  if pf:
    sids = {s["id"] for s in pf["steps"]}
    for s in pf["steps"]:
      if s["lane"] not in pf["lanes"]:
        errs.append(f"{where}: step {s['id']} is in unknown lane {s['lane']}")
      if s.get("element") and s["element"] not in els:
        errs.append(f"{where}: step {s['id']} names unknown element {s['element']}")
      for n in s.get("next", []):
        if n not in sids:
          errs.append(f"{where}: step {s['id']} links to unknown step {n}")
      if s.get("kind", "operation") not in ("operation", "inspection", "decision", "handover"):
        errs.append(f"{where}: step {s['id']} has unknown kind")
  pd = dg.get("p_diagram")
  if pd:
    for f in pd.get("functions", []):
      if f not in fns:
        errs.append(f"{where}: P-diagram names unknown function {f}")
    for e in pd["error_states"]:
      for f in e["failure_modes"]:
        if f not in fms:
          errs.append(f"{where}: error state names unknown failure mode {f}")
    for key, _ in NOISE:
      if not pd["noise_factors"].get(key):
        errs.append(f"{where}: P-diagram needs at least one {key} noise factor")
  return errs


# --------------------------------------------------------------------------------------------------------------------


def figure(files: dict[Path, str], stem: str, render, *args) -> None:
  """A figure of record (original style, embedded in the page) and its card version."""
  global CARDS
  for cards, suffix in ((False, ""), (True, "-cards")):
    CARDS = cards
    try:
      files[FIG / f"{stem}{suffix}.svg"] = render(*args)
    finally:
      CARDS = False


def build_all() -> tuple[dict[Path, str], list[str]]:
  files: dict[Path, str] = {}
  errs: list[str] = []
  docs, allc = {}, {}
  for name in SOURCES:
    doc = fmea_lint.load_yaml((ANALYSES / f"{name}.yaml").read_text())
    docs[name] = doc
    dpath = DIAGRAMS / f"{name}.yaml"
    dg = yaml.safe_load(dpath.read_text()) if dpath.is_file() else None
    if dg:
      errs += check_diagram(name, doc, dg)
    c = counts(doc)
    mc = msr_coverage(name, doc)
    c["msr"] = f"{mc['rated']} of {mc['in_scope']}" if mc["applies"] else "—"
    allc[name] = c
    figure(files, f"{name}-summary", summary_svg, name, doc, c)
    if msr_rows(doc):
      figure(files, f"{name}-msr", msr_svg, name, doc)
    if dg and not errs:
      fn_titles = {f["id"]: one(f["description"]) for f in doc["functions"]}
      if dg.get("block_diagram"):
        figure(files, f"{name}-block", block_svg, name, dg["block_diagram"])
      if dg.get("process_flow"):
        figure(files, f"{name}-flow", flow_svg, name, dg["process_flow"])
      if dg.get("p_diagram"):
        figure(files, f"{name}-p-diagram", p_svg, name, dg["p_diagram"], fn_titles)
    files[OUT / f"{name}.md"] = page(name, doc, dg, c)
  files[OUT / "README.md"] = index(allc, docs)
  return files, errs


def main(argv=None) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--check", action="store_true")
  args = ap.parse_args(argv)
  files, errs = build_all()
  if errs:
    print("\n".join(errs), file=sys.stderr)
    return 1
  if args.check:
    stale = [p for p, t in files.items() if not p.is_file() or p.read_text(encoding="utf-8") != t]
    stale += [p for p in FIG.glob("*.svg") if p not in files]
    for p in stale:
      print(f"stale: {p.relative_to(ROOT)}", file=sys.stderr)
    if stale:
      print(f"run {GENERATOR}", file=sys.stderr)
      return 1
    print(f"FMEA review pages current ({len(files)} files)")
    return 0
  FIG.mkdir(parents=True, exist_ok=True)
  for p in FIG.glob("*.svg"):
    if p not in files:
      p.unlink()
  for p, t in files.items():
    p.write_text(t, encoding="utf-8")
  print(f"wrote {len(files)} files under {OUT.relative_to(ROOT)}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
