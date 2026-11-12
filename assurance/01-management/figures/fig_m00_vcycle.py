#!/usr/bin/env python3
"""The LionDriver V-cycle: every work product placed on the V, with its gate and its status, as clickable tiles.

GitHub cannot make parts of one README image clickable, so the V is drawn as separate SVG tiles (a header, one tile
per side for each of the five levels, the implementation tile, one chip per cross-phase group and a legend). The
README places them in rows, each wrapped in a link to its folder README, so the rows read as one V. The same tiles
are also composed into one picture, `vcycle/fig-m00-vcycle.svg`, for pages that only need to look.

Where each value comes from:

- the work products, their titles, gates, statuses and folders: the register tables of WP-M-00 §3.1–§3.11 (the
  folder is the backticked path in each table's heading);
- the phase names: the gate table of WP-M-00 §2; the gate dates: the "Gate | Earliest | Latest" table of
  WP-M-03 §5;
- which gates are passed: a gate review record `G<n>-YYYY-MM-DD.md` in 10-safety-case/gates/ with its Pass (or Pass
  with conditions) box ticked. The current phase is the phase of the first gate not passed.

Only the grouping of work products into the boxes of the V is typed here (BOXES, BAND), because no record holds it.

The build fails (FigureError) when a register row is in no box or in two, a box names a work product the register
lacks, a status letter is unknown, a gate has no date, or a section or column moved. The animations (the "now"
marker and the outline of what is due at the next gate) are CSS and stop under reduced motion.

    python3 assurance/01-management/figures/fig_m00_vcycle.py            # write the tiles and the README blocks
    python3 assurance/01-management/figures/fig_m00_vcycle.py --check    # exit 1 if anything is stale

Standard library only; deterministic.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parents[1]
REPO = A.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(A / "trace" / "tools"))

import figkit as fk  # noqa: E402
from figkit import FigureError, el, fmt, rect, text, line, path  # noqa: E402
import terms  # noqa: E402

REGISTER = A / "01-management" / "WP-M-00-work-product-register.md"
PLAN = A / "01-management" / "WP-M-03-project-plan.md"
GATES = A / "10-safety-case" / "gates"
OUT = HERE / "vcycle"
README_A = A / "README.md"
README_MAIN = REPO / "README.md"

# ---------------------------------------------------------------- the only typed content: the shape of the V
# (title, what the box holds, folder README it opens, work products)
BOXES = {
  "define": [
    ("Concept and hazards", "Item definition, HARA, FSC, SOTIF, TARA, AI safety", "02-concept",
     ["WP-C-01", "WP-C-02", "WP-C-03", "WP-C-04", "WP-C-05", "WP-C-06", "WP-C-07", "WP-C-08", "WP-C-09", "WP-C-10",
      "WP-C-11", "WP-C-12"]),
    ("System requirements", "Functional, safety, cyber and production requirements", "03-system",
     ["WP-S-01", "WP-S-02", "WP-S-06", "WP-S-07"]),
    ("System architecture", "TSC, timing, HSI and the system safety analyses", "08-analyses",
     ["WP-S-03", "WP-S-04", "WP-S-05", "WP-A-01", "WP-A-02", "WP-A-03", "WP-A-04", "WP-A-05"]),
    ("Hardware and software requirements", "Hardware and software safety requirements", "04-hardware",
     ["WP-H-01", "WP-W-02"]),
    ("Detailed design", "SW architecture, HW design and their safety analyses", "05-software",
     ["WP-W-03", "WP-W-04", "WP-H-02", "WP-H-03", "WP-H-04", "WP-H-05"]),
  ],
  "verify": [
    ("Vehicle validation", "Safety, SOTIF and cyber validation, fault injection", "06-validation",
     ["WP-V-01", "WP-V-02", "WP-V-03", "WP-V-04", "WP-V-05", "WP-V-06", "WP-V-07"]),
    ("System verification", "System qualification against its requirements", "03-system", ["WP-S-09"]),
    ("System integration", "Integration and test of the item", "03-system", ["WP-S-08"]),
    ("Hardware and software integration", "SW integration, embedded SW on HIL, HW verification", "05-software",
     ["WP-W-07", "WP-W-08", "WP-H-06", "WP-H-07"]),
    ("Unit verification", "Static analysis, unit tests, MISRA, coverage", "05-software", ["WP-W-06"]),
  ],
  "build": [
    ("Implementation", "panda safety firmware, openpilot and opendbc code, calibration data, ML model", "05-software",
     ["WP-W-01", "WP-W-05", "WP-W-09", "WP-W-10", "WP-W-11"]),
  ],
}
# cross-phase groups: (title, folder README, work-product prefix)
BAND = [("Management plans", "01-management", "WP-M-"), ("Supporting processes", "07-supporting", "WP-P-"),
        ("Traceability", "trace", "WP-T-"), ("Safety case", "10-safety-case", "WP-K-"),
        ("Operation and field", "09-production-operation", "WP-O-")]

STATUS = {"S": ("Skeleton", fk.LINE), "D": ("Draft", fk.AMBER), "R": ("In review", fk.HW),
          "A": ("Approved", fk.GREEN), "B": ("Baselined", fk.GREEN_DARK), "N/A": ("Tailored out", fk.FAINT)}
ORDER = ["S", "D", "R", "A", "B", "N/A"]

W = 1400
HALF = W // 2
BW, BH, STEP, ROW_H = 400, 96, 36, 150
STYLE = ("<style>.pulse{animation:pulse 2.4s ease-in-out infinite}"
         "@keyframes pulse{50%{opacity:.25}}"
         "@media (prefers-reduced-motion: reduce){.pulse{animation:none}}</style>")


# ---------------------------------------------------------------- reading the records

def read_register() -> dict[str, dict]:
  md = REGISTER.read_text(encoding="utf-8")
  reg = fk.section(md, "## 3. Register")
  heads = list(re.finditer(r"^### (3\.\d+) .*?\(`([^`]+)/`\)\s*$", reg, re.M))
  if len(heads) != 11:
    raise FigureError(f"WP-M-00 §3: expected 11 sub-sections §3.1–§3.11 with a `folder/`, found {len(heads)}")
  wps: dict[str, dict] = {}
  for i, m in enumerate(heads):
    body = reg[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(reg)]
    head, rows = fk.table(body, "ID")
    ci, cw, cg, cs = (fk.col(head, c) for c in ("ID", "Work product", "Gate", "Status"))
    if not rows:
      raise FigureError(f"WP-M-00 §{m.group(1)}: empty table")
    for r in rows:
      wid = fk.plain(r[ci])
      if not re.fullmatch(r"WP-[A-Z]-\d\d", wid):
        raise FigureError(f"WP-M-00 §{m.group(1)}: bad ID {r[ci]!r}")
      if wid in wps:
        raise FigureError(f"WP-M-00: {wid} listed twice")
      st = fk.plain(r[cs])
      st = "N/A" if st.startswith("N/A") else st
      if st not in STATUS:
        raise FigureError(f"WP-M-00: {wid} has unknown status {r[cs]!r} (known: {', '.join(STATUS)})")
      gates = sorted(set(int(g) for g in re.findall(r"G(\d)", r[cg])))
      if not gates:
        raise FigureError(f"WP-M-00: {wid} names no gate in {r[cg]!r}")
      wps[wid] = {"title": fk.plain(r[cw]), "gates": gates, "status": st, "folder": m.group(2)}
  return wps


def read_phases() -> list[dict]:
  head, rows = fk.table(fk.section(REGISTER.read_text(encoding="utf-8"), "## 2. Gates"), "Gate")
  gi, ni = fk.col(head, "Gate"), fk.col(head, "Name")
  _, drows = fk.table(fk.section(PLAN.read_text(encoding="utf-8"), "## 5. Schedule"), "Gate")
  dates = {r[0]: (r[1], r[2]) for r in drows}
  phases = []
  for r in rows:
    g = r[gi]
    if not re.fullmatch(r"G\d", g):
      raise FigureError(f"WP-M-00 §2: bad gate {g!r}")
    n = int(g[1])
    if n < 6 and g not in dates:
      raise FigureError(f"WP-M-03 §5: no date for {g}")
    when = "continuous" if n == 6 else (dates[g][0] if dates[g][0] == dates[g][1] else f"{dates[g][0]}–{dates[g][1]}")
    phases.append({"gate": g, "n": n, "name": r[ni], "when": when, "passed": gate_passed(n)})
  if [p["n"] for p in phases] != list(range(7)):
    raise FigureError("WP-M-00 §2: gates must be G0…G6 in order")
  return phases


def gate_passed(n: int) -> bool:
  for f in sorted(GATES.glob(f"G{n}-????-??-??.md")):
    if re.search(r"^- \[[xX]\] Pass", f.read_text(encoding="utf-8"), re.M):
      return True
  return False


def build_model() -> dict:
  wps, phases = read_register(), read_phases()
  placed: dict[str, str] = {}

  def take(wid, where):
    if wid not in wps:
      raise FigureError(f"{where} names {wid}, which is not in the WP-M-00 register")
    if wid in placed:
      raise FigureError(f"{wid} is placed twice ({placed[wid]} and {where})")
    placed[wid] = where

  boxes = {}
  for side, items in BOXES.items():
    boxes[side] = []
    for title, sub, folder, ids in items:
      for w in ids:
        take(w, title)
      boxes[side].append({"title": title, "sub": sub, "folder": folder, "ids": ids})
  band = []
  for title, folder, prefix in BAND:
    ids = sorted(w for w in wps if w.startswith(prefix))
    if not ids:
      raise FigureError(f"band group {title}: no work product starts with {prefix}")
    for w in ids:
      take(w, title)
    band.append({"title": title, "sub": "", "folder": folder, "ids": ids})
  missing = sorted(set(wps) - set(placed))
  if missing:
    raise FigureError(f"not placed on the V or in the band: {', '.join(missing)}; add each to BOXES or BAND")
  now = next((p for p in phases if not p["passed"]), phases[-1])
  for b in [*boxes["define"], *boxes["verify"], *boxes["build"], *band]:
    b["status"] = [wps[w]["status"] for w in b["ids"]]
    b["gates"] = sorted(set(g for w in b["ids"] for g in wps[w]["gates"]))
    b["due_next"] = now["n"] in b["gates"] and not now["passed"]
    if not (A / b["folder"] / "README.md").exists():
      raise FigureError(f"{b['title']}: {b['folder']}/README.md does not exist")
  return {"wps": wps, "phases": phases, "boxes": boxes, "band": band, "now": now}


# ---------------------------------------------------------------- text helpers

def compress(ids: list[str]) -> str:
  """WP-C-01…12 for a consecutive run, WP-S-01, -02, -06 for a gappy one; prefixes in first-seen order."""
  groups: dict[str, list[int]] = {}
  for w in ids:
    groups.setdefault(w[:5], []).append(int(w[5:]))
  parts = []
  for pre, nums in groups.items():
    nums = sorted(nums)
    if len(nums) > 2 and nums == list(range(nums[0], nums[-1] + 1)):
      parts.append(f"{pre}{nums[0]:02d}…{nums[-1]:02d}")
    else:
      parts.append(pre + ", -".join(f"{n:02d}" for n in nums))
  return ", ".join(parts)


def gate_label(gates: list[int]) -> str:
  return f"G{gates[0]}" if len(gates) == 1 else f"G{gates[0]}–G{gates[-1]}"


def counts(status: list[str]) -> str:
  return " · ".join(f"{status.count(s)} {STATUS[s][0].lower()}" for s in ORDER if s in status)


def bar(x, y, width, status, h=9) -> list[str]:
  seg, out = width / len(status), []
  for k, s in enumerate(sorted(status, key=ORDER.index, reverse=True)):
    out.append(rect(x + k * seg + 1, y, max(seg - 2, 1), h, fill=STATUS[s][1], stroke="none", rx=2, sw=0))
  return out


# ---------------------------------------------------------------- tiles (each draws in its own 0,0 frame)

def box(x, y, b, col, bg, skew) -> list[str]:
  s = 14 * skew
  out = []
  if b["due_next"]:
    out.append(f'<path class="pulse" d="M{fmt(x + s)} {y - 5} h{BW} l{fmt(-2 * s)} {BH + 10} h{-BW} z" '
               f'fill="none" stroke="{fk.SAFETY}" stroke-width="3"/>')
  out.append(path(f"M{fmt(x + s)} {y} h{BW} l{fmt(-2 * s)} {BH} h{-BW} z", stroke=col, sw=1.6, fill=bg))
  tx = x + 28
  out.append(text(tx, y + 25, fk.fit(b["title"], BW - 110, 15, True), 15, col, 700))
  p, pw = fk.pill(0, 0, gate_label(b["gates"]), "#FFFFFF", col, h=20, size=11, stroke=col)
  out.append(f'<g transform="translate({fmt(x + BW - 30 - pw)},{y + 10})">' + "".join(p) + "</g>")
  out.append(text(tx, y + 45, fk.fit(b["sub"], BW - 50, 12.5), 12.5, fk.INK))
  out.append(text(tx, y + 63, fk.fit(f"{compress(b['ids'])} · {b['folder']}/", BW - 50, 11.5), 11.5, fk.MUTED))
  out += bar(tx, y + 73, 180, b["status"])
  out.append(text(tx + 190, y + 82, fk.fit(counts(b["status"]), BW - 240, 11), 11, fk.MUTED))
  return out


def tile_side(side: str, i: int, b: dict, last: bool) -> list[str]:
  y = 12
  if side == "define":
    col, bg, x, skew = fk.DEFINE, fk.DEFINE_BG, 60 + i * STEP, 1
    edge0, edge1 = x + BW + 4, HALF
    ax = x + BW / 2
    arrow = None if last else (ax, y + BH + 4, ax + STEP, ROW_H)
  else:
    col, bg, x, skew = fk.VERIFY, fk.VERIFY_BG, HALF - 60 - BW - i * STEP, -1
    edge0, edge1 = 0, x - 4
    ax = x + BW / 2
    arrow = None if last else (ax - STEP, ROW_H, ax, y + BH + 4)
  out = box(x, y, b, col, bg, skew)
  out.append(line(edge0, y + BH / 2, edge1, y + BH / 2, stroke=fk.FAINT, sw=1.4, dash="5 5"))
  if arrow:
    x1, y1, x2, y2 = arrow
    out.append(path(f"M{fmt(x1)} {fmt(y1)} L{fmt(x2)} {fmt(y2)}", stroke=col, sw=1.8))
    out.append(arrowhead(x1, y1, x2, y2, col))
  else:  # into / out of the implementation tile below
    if side == "define":
      out.append(path(f"M{fmt(ax)} {y + BH + 4} L{fmt(ax + STEP)} {ROW_H}", stroke=col, sw=1.8))
    else:
      out.append(path(f"M{fmt(ax - STEP)} {ROW_H} L{fmt(ax)} {y + BH + 4}", stroke=col, sw=1.8))
      out.append(arrowhead(ax - STEP, ROW_H, ax, y + BH + 4, col))
  return out


def arrowhead(x1, y1, x2, y2, col) -> str:
  import math
  a = math.atan2(y2 - y1, x2 - x1)
  p = [(x2, y2), (x2 - 11 * math.cos(a - .4), y2 - 11 * math.sin(a - .4)),
       (x2 - 11 * math.cos(a + .4), y2 - 11 * math.sin(a + .4))]
  return el("path", None, d="M" + " L".join(f"{fmt(px)} {fmt(py)}" for px, py in p) + " z", fill=col)


IMPL_H = 150


def tile_impl(b: dict) -> list[str]:
  bw, x, y = 640, (W - 640) / 2, 6
  out = []
  if b["due_next"]:
    out.append(rect(x - 5, y - 4, bw + 10, 108, fill="none", stroke=fk.SAFETY, sw=3, rx=12).replace(
      "<rect ", '<rect class="pulse" '))
  out.append(rect(x, y, bw, 100, fill=fk.GREY_BG, stroke=fk.INK, sw=1.6, rx=10))
  out.append(text(W / 2, y + 26, b["title"], 15, fk.INK, 700, "middle"))
  p, pw = fk.pill(0, 0, gate_label(b["gates"]), "#FFFFFF", fk.INK, h=20, size=11, stroke=fk.INK)
  out.append(f'<g transform="translate({fmt(x + bw - 20 - pw)},{y + 10})">' + "".join(p) + "</g>")
  out.append(text(W / 2, y + 46, b["sub"], 12.5, fk.INK, anchor="middle"))
  out.append(text(W / 2, y + 64, f"{compress(b['ids'])} · {b['folder']}/", 11.5, fk.MUTED, anchor="middle"))
  out += bar(W / 2 - 150, y + 74, 160, b["status"])
  out.append(text(W / 2 + 20, y + 83, counts(b["status"]), 11, fk.MUTED))
  last = len(BOXES["define"]) - 1
  dx = 60 + last * STEP + BW / 2 + STEP                      # where the left arrow leaves the last row
  vx = HALF + (HALF - 60 - BW - last * STEP) + BW / 2 - STEP  # where the right arrow enters it
  k = y / (ROW_H - BH - 16)                                   # same slope as the arrows above
  out.append(path(f"M{fmt(dx)} 0 L{fmt(dx + STEP * k)} {y}", stroke=fk.DEFINE, sw=1.8))
  out.append(arrowhead(dx, 0, dx + STEP * k, y, fk.DEFINE))
  out.append(path(f"M{fmt(vx - STEP * k)} {y} L{fmt(vx)} 0", stroke=fk.VERIFY, sw=1.8))
  out.append(text(60, IMPL_H - 12, "Runs across every phase", 12, fk.MUTED, 700))
  out.append(line(250, IMPL_H - 16, W - 60, IMPL_H - 16, stroke=fk.HAIR, sw=1))
  return out


CHIP_W, CHIP_H = W // len(BAND), 74


def tile_chip(b: dict) -> list[str]:
  x, y, w, h = 10, 6, CHIP_W - 20, CHIP_H - 12
  out = []
  if b["due_next"]:
    out.append(rect(x - 3, y - 3, w + 6, h + 6, fill="none", stroke=fk.SAFETY, sw=3, rx=14).replace(
      "<rect ", '<rect class="pulse" '))
  out.append(rect(x, y, w, h, fill="#FFFFFF", stroke=fk.LINE, sw=1.2, rx=12))
  out.append(text(x + 16, y + 22, b["title"], 13, fk.INK, 700))
  out.append(text(x + w - 14, y + 22, gate_label(b["gates"]), 11, fk.MUTED, 700, "end"))
  out.append(text(x + 16, y + 39, fk.fit(f"{compress(b['ids'])} · {len(b['ids'])} work products", w - 30, 11),
                  11, fk.MUTED))
  out += bar(x + 16, y + 47, w - 32, b["status"], h=7)
  return out


HEAD_H = 236


def tile_header(m: dict) -> list[str]:
  out = [text(40, 44, "LionDriver V-cycle", 28, fk.INK, 700),
         text(40, 70, "Where each work product sits on the V, which gate needs it, and how far it has matured. "
              "Generated from the work-product register (WP-M-00) and the schedule (WP-M-03).", 13.5, fk.MUTED)]
  x0, x1, ya = 60, W - 60, 140
  cw = (x1 - x0) / 7
  now = m["now"]
  out.append(rect(x0, 92, x1 - x0, 84, fill=fk.CHIP, stroke=fk.HAIR, rx=8))
  for p in m["phases"]:
    cx = x0 + cw * p["n"]
    if p is now:
      out.append(rect(cx + 2, 94, cw - 4, 80, fill=fk.SAFETY_BG, stroke="none", rx=6, sw=0))
    if p["n"]:
      out.append(line(cx, 96, cx, 172, stroke=fk.HAIR, sw=1))
    out.append(text(cx + cw / 2, 114, fk.fit(p["name"], cw - 10, 12.5, True), 12.5, fk.INK, 700,
                    "middle"))
  out.append(line(x0 + 8, ya + 10, x1 - 8, ya + 10, stroke=fk.LINE, sw=2))
  for p in m["phases"]:
    cx = x0 + cw * p["n"]
    gx = cx + cw - 10 if p["n"] < 6 else cx + cw / 2
    fill = fk.GREEN if p["passed"] else "#FFFFFF"
    out.append(f'<path d="M{fmt(gx)} {ya} l10 10 l-10 10 l-10 -10z" fill="{fill}" stroke="{fk.DEFINE}" '
               'stroke-width="2"/>')
    out.append(text(gx if p["n"] == 6 else gx + 10, ya + 32, f"{p['gate']} · {p['when']}", 11, fk.MUTED,
                    anchor="middle" if p["n"] == 6 else "end"))
  nx = x0 + cw * now["n"] + cw / 2
  passed = sum(p["passed"] for p in m["phases"])
  label = f"Now: {now['name']} phase"
  pw = fk.text_w(label, 12, True) + 24
  out.append(f'<circle class="pulse" cx="{fmt(nx)}" cy="{ya + 10}" r="7" fill="{fk.SAFETY}"/>')
  out.append(line(nx, 178, nx, 192, stroke=fk.SAFETY, sw=2))
  out.append(rect(nx - pw / 2, 192, pw, 24, fill=fk.SAFETY, stroke="none", rx=12, sw=0))
  out.append(text(nx, 208, label, 12, "#FFFFFF", 700, "middle"))
  done = "no gate passed yet" if not passed else f"{passed} of 7 gates passed"
  out.append(text(x1, 208, f"Filled diamond = gate passed in a recorded review · {done}", 11, fk.FAINT,
                  anchor="end", style="italic"))
  return out


def tile_legend(m: dict, all_bodies: list[str]) -> tuple[list[str], float]:
  y = 26
  out = [text(60, y, "Status of each work product (one block each):", 12, fk.INK, 700)]
  x = 340
  for s in ORDER[:-1]:
    name, c = STATUS[s]
    out.append(rect(x, y - 10, 22, 10, fill=c, stroke="none", rx=2, sw=0))
    out.append(text(x + 28, y, name, 12, fk.MUTED))
    x += 46 + fk.text_w(name, 12)
  y += 24
  out.append(rect(60, y - 11, 22, 12, fill="none", stroke=fk.SAFETY, sw=3, rx=3))
  out.append(text(88, y, f"Outline: due at the next gate, {m['now']['gate']}", 12, fk.MUTED))
  out.append(line(380, y - 5, 420, y - 5, stroke=fk.FAINT, sw=1.4, dash="5 5"))
  out.append(text(428, y, "Dashed line: the right-hand box verifies the left-hand box", 12, fk.MUTED))
  out.append(text(W - 60, y, "Each box opens its folder", 12, fk.MUTED, anchor="end"))
  y += 22
  out.append(text(60, y, "Work products are grouped by hand; their status, gates and dates are read from the "
                  "records on every build, so the V moves as they change. Status is not acceptance.", 11.5, fk.FAINT,
                  style="italic"))
  foot, y2 = terms.svg_footer(all_bodies + out, 60, y + 22, W - 120)
  return out + foot, y2


# ---------------------------------------------------------------- assembling

def tiles(m: dict) -> dict[str, tuple[int, int, list[str], str]]:
  """name -> (width, height, body, accessible description)."""
  t: dict[str, tuple[int, int, list[str], str]] = {}
  ph = m["phases"]
  t["header"] = (W, HEAD_H, tile_header(m),
                 "Time axis: " + "; ".join(f"{p['name']} phase, {p['gate']} {p['when']}"
                                           f"{' passed' if p['passed'] else ''}" for p in ph) +
                 f". Now in the {m['now']['name']} phase.")
  for side in ("define", "verify"):
    items = m["boxes"][side]
    for i, b in enumerate(items):
      t[f"{side}-{i + 1}"] = (HALF, ROW_H, tile_side(side, i, b, i == len(items) - 1), describe(b))
  b = m["boxes"]["build"][0]
  t["build"] = (W, IMPL_H, tile_impl(b), describe(b))
  for i, b in enumerate(m["band"]):
    t[f"band-{i + 1}"] = (CHIP_W, CHIP_H, tile_chip(b), describe(b))
  bodies = [s for v in t.values() for s in v[2]]
  leg, h = tile_legend(m, bodies)
  t["legend"] = (W, int(h + 8), leg, "Legend: status colours, the next-gate outline and the verifies line.")
  return t


def describe(b: dict) -> str:
  return (f"{b['title']} ({gate_label(b['gates'])}): {compress(b['ids'])}; {counts(b['status'])}. "
          f"Opens {b['folder']}/.")


def layout(t) -> list[tuple[str, int, int]]:
  """(tile, x, y) in the composed picture, in reading order."""
  pos, y = [("header", 0, 0)], HEAD_H
  for i in range(len(BOXES["define"])):
    pos += [(f"define-{i + 1}", 0, y), (f"verify-{i + 1}", HALF, y)]
    y += ROW_H
  pos.append(("build", 0, y))
  y += IMPL_H
  pos += [(f"band-{i + 1}", i * CHIP_W, y) for i in range(len(BAND))]
  y += CHIP_H
  pos.append(("legend", 0, y))
  return pos


def render(m: dict) -> dict[Path, str]:
  t = tiles(m)
  files = {}
  for name, (w, h, body, desc) in t.items():
    files[OUT / f"fig-m00-vcycle-{name}.svg"] = fk.svg(w, h, f"LionDriver V-cycle: {name}", desc, [STYLE, *body])
  pos = layout(t)
  height = pos[-1][2] + t["legend"][1]
  comp = [STYLE]
  for name, x, y in pos:
    comp.append(f'<g transform="translate({x},{y})">' + "\n".join(t[name][2]) + "</g>")
  desc = " ".join(t[name][3] for name, _, _ in pos)
  files[OUT / "fig-m00-vcycle.svg"] = fk.svg(W, height, "LionDriver V-cycle", desc, comp)
  files.update(readmes(m, t))
  return files


# ---------------------------------------------------------------- README blocks

BEGIN = "<!-- BEGIN GENERATED: vcycle (assurance/01-management/figures/fig_m00_vcycle.py) -->"
END = "<!-- END GENERATED: vcycle -->"


def block_assurance(m: dict, t) -> str:
  img = "01-management/figures/vcycle/fig-m00-vcycle-{}.svg"

  def a(name, folder, width):
    alt = t[name][3].replace('"', "'")
    return f'<a href="{folder}/README.md"><img src="{img.format(name)}" width="{width}" alt="{alt}"></a>'

  rows = [f'<img src="{img.format("header")}" width="98%" alt="{t["header"][3]}">']
  for i in range(len(BOXES["define"])):
    rows.append(a(f"define-{i + 1}", m["boxes"]["define"][i]["folder"], "49%") +
                a(f"verify-{i + 1}", m["boxes"]["verify"][i]["folder"], "49%"))
  rows.append(a("build", m["boxes"]["build"][0]["folder"], "98%"))
  rows.append("".join(a(f"band-{i + 1}", b["folder"], "19.6%") for i, b in enumerate(m["band"])))
  rows.append(f'<img src="{img.format("legend")}" width="98%" alt="{t["legend"][3]}">')
  folders = sorted({b["folder"] for side in m["boxes"].values() for b in side} | {b["folder"] for b in m["band"]})
  return "\n".join([
    BEGIN, "", '<p align="center">', "<br>\n".join(rows), "</p>", "",
    "Click a box to open its folder. Folders: " + " · ".join(f"[{f}/]({f}/README.md)" for f in folders) + ".", "",
    f"*The V-cycle.* Drawn from the [work-product register](01-management/WP-M-00-work-product-register.md) "
    f"§2–§3, the [schedule](01-management/WP-M-03-project-plan.md#5-schedule) and the "
    f"[gate records](10-safety-case/gates/README.md) by "
    f"[`fig_m00_vcycle.py`](01-management/figures/fig_m00_vcycle.py); CI fails if it is stale.", "", END])


def block_main(m: dict) -> str:
  n = len(m["wps"])
  by = {s: sum(1 for w in m["wps"].values() if w["status"] == s) for s in ORDER}
  st = ", ".join(f"{by[s]} {STATUS[s][0].lower()}" for s in ORDER if by[s])
  return "\n".join([
    BEGIN, "", '<p align="center">',
    '  <a href="assurance/README.md#the-v-cycle"><img src="assurance/01-management/figures/vcycle/fig-m00-vcycle.svg" '
    f'width="100%" alt="The LionDriver V-cycle: {n} work products placed on the V from concept down to implementation '
    f'and back up to vehicle validation, each with its gate; {st}. Now in the {m["now"]["name"]} phase.">'
    "</a>", "</p>", "",
    "**[Open the clickable V-cycle →](assurance/README.md#the-v-cycle)** each box opens its part of the assurance "
    "record.", "", END])


def splice(path_: Path, block: str) -> str:
  s = path_.read_text(encoding="utf-8")
  if s.count(BEGIN) != 1 or s.count(END) != 1:
    raise FigureError(f"{path_.relative_to(REPO)}: needs exactly one {BEGIN} … {END} block")
  i, j = s.index(BEGIN), s.index(END) + len(END)
  return s[:i] + block + s[j:]


def readmes(m: dict, t) -> dict[Path, str]:
  return {README_A: splice(README_A, block_assurance(m, t)), README_MAIN: splice(README_MAIN, block_main(m))}


def main(argv: list[str]) -> int:
  check = "--check" in argv
  try:
    files = render(build_model())
  except FigureError as e:
    print(f"fig_m00_vcycle: {e}", file=sys.stderr)
    return 1
  stale = [p for p, s in files.items() if not p.exists() or p.read_text(encoding="utf-8") != s]
  extra = sorted(set(OUT.glob("*.svg")) - set(files)) if OUT.exists() else []
  if check:
    for p in stale + extra:
      print(f"fig_m00_vcycle: stale or unexpected: {p.relative_to(REPO)}", file=sys.stderr)
    if stale or extra:
      print("run: python3 assurance/01-management/figures/fig_m00_vcycle.py", file=sys.stderr)
      return 1
    print(f"fig_m00_vcycle: {len(files)} files current")
    return 0
  OUT.mkdir(exist_ok=True)
  for p in extra:
    p.unlink()
  for p in stale:
    p.write_text(files[p], encoding="utf-8")
  print(f"fig_m00_vcycle: wrote {len(stale)} of {len(files)} files")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
