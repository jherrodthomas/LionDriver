#!/usr/bin/env python3
"""Draw WP-V-02 Figure 4-1: the validation targets VT-01…VT-15 on a log scale of the exposure they need.

The source of record is `../WP-V-02-sotif-vv-strategy.md`:
  * the §4 table gives the rows (ID, SH, "Achievable?"); it is parsed, so a VT added or removed there
    changes the figure or fails the check;
  * the exposure each target needs is in prose cells (§4 "Proposed target", §3.1 cases), and the
    capacity bands are in §3.2. Those values are listed in MARKS, CONTEXT and BANDS below, and every one
    carries the exact text it was read from (`src`). `--check` fails when such a text is no longer in
    WP-V-02, so a changed number forces the figure to be reviewed.

Two panels, because the targets come in two units that the document does not convert into each other:
  * driving exposure in km (with hours at the 64 km/h of §3.1; miles converted with the same 64 km/h =
    40 mph of §3.1), and
  * a count per scenario, input type or stratum (trials, instances, subjects).
Where a row gives a rate and no exposure, the zero-failure exposure is computed with §3 step 3
(n = −ln(1 − C) / λ, −ln(0.05) ≈ 3.0) and drawn as computed. §4 calls every numeric value a placeholder
for the assessor review (OI-3), so no target is drawn as a solid value.

    python3 fig_v02_validation_targets.py            # regenerate the SVG
    python3 fig_v02_validation_targets.py --check    # fail if a source text changed or the SVG is stale

Standard library only. Output is deterministic.
"""

from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "WP-V-02-sotif-vv-strategy.md"
OUTPUT = "fig-v02-4-1-validation-targets.svg"

# ---------------------------------------------------------------- palette (assurance figure style)
FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SFMono-Regular', Menlo, Consolas, monospace"
INK, MUTED, FAINT, LINE, HAIR = "#0F172A", "#475569", "#94A3B8", "#CBD5E1", "#E2E8F0"
CHIP = "#F8FAFC"
SAFETY, SAFETY_BG = "#C2410C", "#FFF7ED"
SW, SW_BG = "#0F766E", "#F0FDFA"
HW, HW_BG = "#4F46E5", "#EEF2FF"
AMBER, AMBER_BG = "#D97706", "#FFFBEB"
GREY_BG = "#F1F5F9"

# ---------------------------------------------------------------- data (hand-listed, each with its source text)
# 64 km/h = 40 mph (§3.1): used for km <-> h and mi -> km, as the document does.
KMH = 64.0
KM_PER_MI = 64.0 / 40.0
CONVERSION_SRC = ["Average engaged speed is assumed to be 64 km/h (40 mph) to convert distance to time.",
                  "`−ln(1 − 0.95) ≈ 3.0`"]
LN20 = 3.0  # −ln(1 − 0.95), as rounded in §3.1

# kind: "stated" = the count/exposure is written in the §4 row; "case" = read from the §3.1 case the row
# names; "computed" = the row gives a rate only, exposure computed with §3 step 3 at C = 95 %.
# panel: "km" or "count". hi_km: the C = 99 % value from §3.1, drawn as a tick.
MARKS = [
  {"vt": "VT-01", "panel": "km", "value": 6e5 * KM_PER_MI, "kind": "case", "hi": 9e5 * KM_PER_MI,
   "label": "case D: ≈ 6 × 10⁵ mi (1.5 × 10⁴ h), C 95 %",
   "src": ["Rate-level: ≤ 5 × 10⁻⁶ /mi (case D)",
           "| 5 × 10⁻⁶ /mi | ≈ 6 × 10⁵ mi | ≈ 1.5 × 10⁴ h | ≈ 9 × 10⁵ mi |"]},
  {"vt": "VT-01", "panel": "count", "value": 299, "kind": "case",
   "label": "299 trials / scenario (case E), C 95 %",
   "src": ["p_s ≤ 1 % per scenario in KS-01…KS-06, KS-14 at 95 %",
           "| E. Per-scenario: stationary-lead approach, p_max = 1 % | — | 299 trials |"]},
  {"vt": "VT-02", "panel": "count", "value": 299, "kind": "case", "no_c": True,
   "label": "p_s ≤ 1 %, C not stated: 299 at 95 %",
   "src": ["p_s ≤ 1 % per curve/marking scenario; zero occurrences in all CC trials"]},
  {"vt": "VT-03", "panel": "count", "value": 59, "kind": "stated",
   "label": "≥ 59 trials / scenario (case F, C 95 %)",
   "src": ["Zero occurrences in KS-07…KS-09 trials (≥ 59 per scenario)", "| §3 step 5, case F |",
           "| F. Per-scenario: p_max = 5 % | — | 59 trials |"]},
  {"vt": "VT-04", "panel": "km", "value": LN20 * 1000, "kind": "computed",
   "label": "≤ 1 / 1000 km: ≥ 3 × 10³ km with none",
   "src": ["Surrogate on public road: ≤ 1 per 1000 km with 95 % upper bound reported"]},
  {"vt": "VT-04", "panel": "count", "value": 299, "kind": "case", "no_c": True,
   "label": "p_s ≤ 1 %, C not stated: 299 at 95 %",
   "src": ["scenario-level p_s ≤ 1 % for bridges/overpasses, metal plates, shadows (KS-10, KS-11)"]},
  {"vt": "VT-05", "panel": "count", "value": 299, "kind": "stated",
   "label": "≥ 299 trials / input type, speed band",
   "src": ["100 % release within SG-05 budget in ≥ 299 trials per input type and speed band (p ≤ 1 % at 95 %)"]},
  {"vt": "VT-06", "panel": "count", "value": 299, "kind": "case",
   "label": "p_s ≤ 1 % / speed band: 299 (case E)",
   "src": ["p_s ≤ 1 % per approach-speed band in the ODD (KS-05, KS-08)", "| §3 step 5, case E; B2 comparison |"]},
  {"vt": "VT-12", "panel": "count", "value": 59, "kind": "stated",
   "label": "≥ 59 trials / speed threshold",
   "src": ["100 % prevention/disengagement in ≥ 59 trials per speed threshold"]},
  {"vt": "VT-13", "panel": "count", "value": 20, "kind": "stated",
   "label": "20/20 subjects controllable",
   "src": ["Abort controllable in ≥ 20/20 subjects (CA-01 logic)"]},
  {"vt": "VT-14", "panel": "count", "value": 299, "kind": "stated",
   "label": "≥ 299 instances / ODD stratum, C 95 %",
   "src": ["p_s ≤ 1 % per steady-scene instance at 95 % (≥ 299 instances per ODD stratum)"]},
  {"vt": "VT-15", "panel": "count", "value": 14, "kind": "stated",
   "label": "(a) ≥ 14 failing instances, no miss, C 95 %",
   "src": ["(a) ≥ 80 % per KS of the known-triggering-condition set (KS-12, KS-13, KS-16) at 95 %: ≥ 14 failing instances with no miss"]},
  {"vt": "VT-15", "panel": "km", "value": LN20 * KMH, "kind": "computed",
   "label": "(b) ≤ 1 false flag / h: ≥ 3 h with none",
   "src": ["(b) ≤ 1 false flag per hour at 95 % (χ² bound of §3 step 3)"]},
]

# Rows with no exposure figure: what the target is measured against instead.
NO_COUNT = {
  "VT-07": ("equivalent activation in every PCS soft-target test", ["in every PCS soft-target test"]),
  "VT-08": ("AIR-07/AIR-08 thresholds per DM stratum", ["AIR-07/AIR-08 thresholds per DM stratum"]),
  "VT-09": ("not worse than stock in any KS scenario run with both",
            ["LD-SDA not worse than stock in any KS scenario run with both"]),
  "VT-10": ("discovery rate decreasing over the last 3 exploration blocks",
            ["decreasing over the last 3 exploration blocks"]),
  "VT-11": ("zero injury crashes in the field (long term)", ["Zero injury crashes; trigger thresholds"]),
}

# §3.1 cases A–C and E–F: illustrative, not targets (case D is VT-01's rate-level value).
CONTEXT = [
  {"case": "A", "panel": "km", "value": 3.7e8, "src": ["≈ 2.3 × 10⁸ mi (3.7 × 10⁸ km)"]},
  {"case": "B", "panel": "km", "value": 2.3e9 * KM_PER_MI, "src": ["| 1.3 × 10⁻⁹ /mi | ≈ 2.3 × 10⁹ mi |"]},
  {"case": "C", "panel": "km", "value": 6e6 * KM_PER_MI, "src": ["| 5 × 10⁻⁷ /mi | ≈ 6 × 10⁶ mi |"]},
  {"case": "F", "panel": "count", "value": 59, "src": ["p_max = 5 % | — | 59 trials"]},
  {"case": "E", "panel": "count", "value": 299, "src": ["p_max = 1 % | — | 299 trials"]},
]

# §3.2: what LionDriver can achieve per year. "words": True marks a band whose edges are read from words.
BANDS = [
  {"panel": "km", "lo": 1e4, "hi": 2e4, "colour": SW, "bg": SW_BG,
   "title": "Public road, safety driver", "sub": "10⁴–2 × 10⁴ km/yr (≈ 150–300 h)",
   "src": ["| 10⁴ – 2 × 10⁴ km engaged (≈ 150–300 h) |"]},
  {"panel": "count", "lo": 10, "hi": 300, "colour": SW, "bg": SW_BG, "words": True,
   "title": "Closed course", "sub": "tens to low hundreds / scenario / campaign",
   "src": ["| Tens to low hundreds of trials per scenario per campaign |"]},
  {"panel": "count", "lo": 1e3, "hi": 1e5, "colour": HW, "bg": HW_BG,
   "title": "Simulation (no credit yet, §5.3)", "sub": "10³–10⁵ runs / scenario family",
   "src": ["| 10³ – 10⁵ runs per scenario family (compute-bound) |",
           "**No credit until the fidelity case of §5.3 is approved for the scenario family**"]},
]
NOT_DRAWN_SRC = ["Cases A–C are out of reach of LionDriver driving by roughly three to five orders of magnitude",
                 "| All recorded data, repeatedly, per software change |",
                 "| Grows with the LionDriver fleet (initially one vehicle) |"]
PLACEHOLDER_SRC = ["Targets are **proposals** until they are frozen (OI-3)"]


# ---------------------------------------------------------------- parsing

class ParseError(Exception):
  pass


def split_row(line: str) -> list[str]:
  """Cells of a Markdown table row (as trace_map.split_row)."""
  cells = re.split(r"(?<!\\)\|", line.strip())
  return [c.strip() for c in cells[1:-1]]


@dataclass
class Target:
  ident: str
  sh: str
  achievable: str


def parse(md: str) -> list[Target]:
  """The §4 table: one Target per VT-nn row."""
  body = md.split("\n## 4. Validation targets", 1)
  if len(body) != 2:
    raise ParseError("§4 'Validation targets' not found")
  section = body[1].split("\n### ", 1)[0]
  out = []
  for line in section.splitlines():
    if re.match(r"^\|\s*VT-\d{2}\s*\|", line):
      c = split_row(line)
      if len(c) != 7:
        raise ParseError(f"{c[0]}: expected 7 columns, got {len(c)}")
      out.append(Target(c[0], c[1], c[6]))
  if not out:
    raise ParseError("no VT rows in §4")
  return out


def sources() -> list[str]:
  found = CONVERSION_SRC + NOT_DRAWN_SRC + PLACEHOLDER_SRC
  for group in (MARKS, CONTEXT, BANDS):
    for m in group:
      found = found + m["src"]
  for _, src in NO_COUNT.values():
    found = found + src
  return found


def missing_sources(md: str) -> list[str]:
  return [s for s in sources() if s not in md]


# ---------------------------------------------------------------- SVG helpers (as trace_figures.py)

def el(tag: str, text: str | None = None, **attrs) -> str:
  a = "".join(f' {k.rstrip("_").replace("_", "-")}="{v}"' for k, v in attrs.items() if v not in ("", None))
  return f"<{tag}{a}/>" if text is None else f"<{tag}{a}>{escape(text)}</{tag}>"


def fmt(v: float) -> str:
  return f"{v:.1f}".rstrip("0").rstrip(".")


def text(x, y, s, size=11, fill=INK, weight="", anchor="", family="", style="", halo=False) -> str:
  """Text; halo=True paints a white outline under it so that grid and band lines never run through it."""
  return el("text", s, x=fmt(x), y=fmt(y), font_size=size, fill=fill, font_weight=weight, text_anchor=anchor,
            font_family=family, font_style=style, stroke="#FFFFFF" if halo else "", stroke_width=3 if halo else "",
            stroke_linejoin="round" if halo else "", paint_order="stroke" if halo else "")


def rect(x, y, w, h, fill="#FFFFFF", stroke=LINE, sw=1.2, rx=8, dash="", opacity="") -> str:
  return el("rect", None, x=fmt(x), y=fmt(y), width=fmt(w), height=fmt(h), rx=rx, fill=fill, stroke=stroke,
            stroke_width=sw, stroke_dasharray=dash, opacity=opacity)


def line(x1, y1, x2, y2, stroke=MUTED, sw=1.4, dash="") -> str:
  return el("line", None, x1=fmt(x1), y1=fmt(y1), x2=fmt(x2), y2=fmt(y2), stroke=stroke, stroke_width=sw,
            stroke_dasharray=dash)


def header(width: int, number: str, title: str, subtitle: str, ref: str) -> list[str]:
  return [text(40, 44, f"Figure {number} · {title}", size=20, weight=700),
          text(40, 66, subtitle, size=12.5, fill=MUTED),
          text(width - 40, 44, ref, size=11, fill=MUTED, anchor="end"),
          line(40, 82, width - 40, 82, stroke=HAIR, sw=1)]


def svg(width: int, height: int, title: str, desc: str, body: list[str]) -> str:
  head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" ' +
          f'viewBox="0 0 {width} {height}" font-family="{FONT}" role="img">')
  return "\n".join([head, el("title", title), el("desc", desc),
                    rect(0, 0, width, height, fill="#FFFFFF", stroke="none", rx=0, sw=0), *body, "</svg>"]) + "\n"


def wrap(s: str, n: int) -> list[str]:
  lines, cur = [], ""
  for w in s.split():
    if cur and len(cur) + 1 + len(w) > n:
      lines.append(cur)
      cur = w
    else:
      cur = f"{cur} {w}" if cur else w
  return lines + ([cur] if cur else [])


def text_width(s: str, size: float) -> float:
  return len(s) * size * 0.5


def sci(v: float) -> str:
  """10^n as a label with superscripts."""
  sup = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
  return "10" + str(int(round(math.log10(v)))).translate(sup)


# ---------------------------------------------------------------- layout

W = 1280
LABEL_X = 40
PANELS = {
  "km": {"x0": 330, "x1": 655, "lo": 2, "hi": 10, "title": "Driving exposure (km, log scale)",
         "unit": "km"},
  "count": {"x0": 705, "x1": 1062, "lo": 1, "hi": 5, "title": "Count per scenario, input or stratum (log)",
            "unit": "count"},
}
ACH_X = 1080
ROW_H = 42
TOP = 100


def xpos(panel: str, v: float) -> float:
  p = PANELS[panel]
  return p["x0"] + (math.log10(v) - p["lo"]) / (p["hi"] - p["lo"]) * (p["x1"] - p["x0"])


def marker(kind: str, x: float, y: float, no_c: bool = False) -> list[str]:
  """Every target is a placeholder (§4): hollow, dashed outline. Shape tells where the number comes from."""
  dash = "3 2"
  if kind == "stated":
    pts = f"{fmt(x)},{fmt(y - 7)} {fmt(x + 7)},{fmt(y)} {fmt(x)},{fmt(y + 7)} {fmt(x - 7)},{fmt(y)}"
    return [el("polygon", None, points=pts, fill=SAFETY_BG, stroke=SAFETY, stroke_width=1.6, stroke_dasharray=dash)]
  if kind == "case":
    out = [el("circle", None, cx=fmt(x), cy=fmt(y), r=6, fill=SAFETY_BG, stroke=SAFETY, stroke_width=1.6,
              stroke_dasharray=dash)]
    if no_c:
      out.append(text(x, y + 3.5, "?", size=9, fill=SAFETY, weight=700, anchor="middle"))
    return out
  return [rect(x - 5.5, y - 5.5, 11, 11, fill="#FFFFFF", stroke=SAFETY, sw=1.6, rx=1.5, dash=dash)]


def place_label(panel: str, x: float, y: float, label: str, size: float = 10) -> str:
  p = PANELS[panel]
  w = text_width(label, size)
  if x + 11 + w <= p["x1"] - 2:
    return text(x + 11, y + 3.5, label, size=size, fill=INK, halo=True)
  if x - 11 - w >= p["x0"] + 2:
    return text(x - 11, y + 3.5, label, size=size, fill=INK, anchor="end", halo=True)
  raise ValueError(f"label does not fit in panel {panel}: {label}")


def figure(targets: list[Target]) -> str:
  body: list[str] = []
  n = len(targets)
  body += header(W, "4-1", "Validation targets on a log scale",
                 f"Exposure each of the {n} proposed targets VT-xx needs, against what §3.2 says LionDriver " +
                 "can achieve in a year. Placeholders until the assessor approves them (OI-3).",
                 "WP-V-02 §3.1, §3.2, §4")

  # band titles above the panels
  y_band_title = TOP + 18
  band_titles_y = {"km": [y_band_title], "count": [y_band_title, y_band_title + 26]}
  plot_top = TOP + 66
  ctx_y = plot_top + 18
  rows_top = plot_top + 40
  plot_bottom = rows_top + n * ROW_H
  axis_y = plot_bottom + 4

  # panel frames and titles
  for p in PANELS.values():
    body.append(text(p["x0"], TOP + 2, p["title"], size=12, weight=700))
    body.append(rect(p["x0"], plot_top, p["x1"] - p["x0"], plot_bottom - plot_top, fill="#FFFFFF", stroke=LINE,
                     sw=1, rx=0))
  body.append(text(LABEL_X, TOP + 2, "Target · SH", size=12, weight=700))
  body.append(text(ACH_X, TOP + 2, "Achievable? (§4)", size=12, weight=700))

  # reference bands (§3.2)
  for key in PANELS:
    bands = [b for b in BANDS if b["panel"] == key]
    for i, b in enumerate(bands):
      x0, x1 = xpos(key, b["lo"]), xpos(key, b["hi"])
      body.append(rect(x0, plot_top, x1 - x0, plot_bottom - plot_top, fill=b["bg"], stroke="none", rx=0, sw=0))
      for xe in (x0, x1):
        body.append(line(xe, plot_top, xe, plot_bottom, stroke=b["colour"], sw=1,
                         dash="2 3" if b.get("words") else ""))
      ty = band_titles_y[key][i]
      tx = x0 if key == "km" else (x0 if i == 0 else x0)
      anchor = "end" if key == "km" else ""
      if key == "km":
        tx = x1
      body.append(text(tx, ty, b["title"], size=10.5, fill=b["colour"], weight=700, anchor=anchor))
      body.append(text(tx, ty + 13, b["sub"], size=10, fill=b["colour"], anchor=anchor))
      body.append(line(x0 if key != "km" else x1, ty + 17, x0 if key != "km" else x1, plot_top,
                       stroke=b["colour"], sw=1))

  # decade grid
  for key, p in PANELS.items():
    for d in range(p["lo"], p["hi"] + 1):
      x = xpos(key, 10 ** d)
      if p["lo"] < d < p["hi"]:
        body.append(line(x, plot_top, x, plot_bottom, stroke=HAIR, sw=1))
      body.append(line(x, plot_bottom, x, plot_bottom + 5, stroke=FAINT, sw=1))
      body.append(text(x, axis_y + 14, sci(10 ** d), size=10.5, fill=MUTED, anchor="middle"))
  body.append(text(PANELS["km"]["x0"] - 14, axis_y + 14, "km", size=10.5, fill=MUTED, weight=700, anchor="end"))
  # hours at 64 km/h
  for h in range(1, 8):
    km = 10 ** h * KMH
    if km > 10 ** PANELS["km"]["hi"]:
      break
    x = xpos("km", km)
    body.append(line(x, axis_y + 21, x, axis_y + 25, stroke=FAINT, sw=1))
    body.append(text(x, axis_y + 35, sci(10 ** h), size=10, fill=MUTED, anchor="middle"))
  body.append(text(PANELS["km"]["x0"] - 14, axis_y + 35, "hours at 64 km/h (§3.1)", size=10, fill=MUTED,
                   anchor="end"))
  body.append(text(PANELS["count"]["x0"], axis_y + 35,
                   "trials, instances or subjects (unit named on each mark)", size=10, fill=MUTED))

  # context row: §3.1 cases
  body.append(rect(LABEL_X, ctx_y - 13, W - 80, 26, fill=GREY_BG, stroke="none", rx=4, sw=0, opacity=0.6))
  body.append(text(LABEL_X + 8, ctx_y + 4, "§3.1 illustration, C = 95 % (not targets)", size=10.5, fill=MUTED,
                   style="italic"))
  for c in CONTEXT:
    x = xpos(c["panel"], c["value"])
    body.append(line(x, ctx_y - 8, x, ctx_y + 8, stroke=FAINT, sw=2))
    body.append(text(x + 5, ctx_y + 4, c["case"], size=10.5, fill=MUTED, weight=700))
  body.append(text(ACH_X, ctx_y + 4, "A–C: 10³–10⁵ out of reach (§3.2)", size=10, fill=MUTED, style="italic"))

  # rows
  marks_by_vt: dict[str, list[dict]] = {}
  for m in MARKS:
    marks_by_vt.setdefault(m["vt"], []).append(m)
  for i, t in enumerate(targets):
    y0 = rows_top + i * ROW_H
    ym = y0 + ROW_H / 2
    if i % 2 == 1:
      body.append(rect(LABEL_X, y0, PANELS["km"]["x0"] - LABEL_X - 8, ROW_H, fill=CHIP, stroke="none", rx=0, sw=0))
      body.append(rect(ACH_X - 8, y0, W - 40 - ACH_X + 8, ROW_H, fill=CHIP, stroke="none", rx=0, sw=0))
    body.append(line(LABEL_X, y0 + ROW_H, W - 40, y0 + ROW_H, stroke=HAIR, sw=1))
    body.append(text(LABEL_X + 4, ym - 4, t.ident, size=11.5, weight=700, family=MONO))
    sh = wrap(t.sh, 40)
    if len(sh) > 2:
      sh = [sh[0], " ".join(sh[1:])]
    for k, s in enumerate(sh[:2]):
      body.append(text(LABEL_X + 52, ym - 4 + 13 * k, s, size=10, fill=MUTED))
    ach = wrap(t.achievable, 29)
    for k, s in enumerate(ach[:3]):
      body.append(text(ACH_X, ym + 4 - 6 * (len(ach[:3]) - 1) + 12 * k, s, size=10, fill=INK))
    for m in marks_by_vt.get(t.ident, []):
      x = xpos(m["panel"], m["value"])
      if "hi" in m:
        xh = xpos(m["panel"], m["hi"])
        body.append(line(x + 6, ym, xh, ym, stroke=SAFETY, sw=1.2, dash="3 2"))
        body.append(line(xh, ym - 5, xh, ym + 5, stroke=SAFETY, sw=1.4))
        body.append(text(xh + 4, ym - 6, "99 %", size=9, fill=SAFETY))
      body += marker(m["kind"], x, ym, m.get("no_c", False))
      label = m["label"]
      if "hi" in m:
        body.append(text(x - 10, ym + 3.5, label, size=10, fill=INK, anchor="end", halo=True))
      else:
        body.append(place_label(m["panel"], x, ym, label))
    if t.ident in NO_COUNT:
      body.append(text(PANELS["km"]["x0"] + 10, ym + 3.5, "no exposure figure: " + NO_COUNT[t.ident][0], size=10,
                       fill=MUTED, style="italic", halo=True))

  # legend
  ly = axis_y + 60
  body.append(line(40, ly - 18, W - 40, ly - 18, stroke=HAIR, sw=1))
  x = 40
  items = [("stated", False, "exposure written in the §4 row"),
           ("case", False, "read from the §3.1 case the row names"),
           ("case", True, "row gives no confidence; shown at 95 %"),
           ("computed", False, "rate only: n = −ln(1 − C)/λ at 95 % (§3 step 3)")]
  for kind, no_c, label in items:
    body += marker(kind, x + 7, ly - 4, no_c)
    body.append(text(x + 20, ly, label, size=10.5, fill=MUTED))
    x += 34 + text_width(label, 10.5)
  ly2 = ly + 22
  body.append(rect(40, ly2 - 10, 14, 12, fill=SW_BG, stroke=SW, rx=2))
  body.append(text(60, ly2, "§3.2 plausible capacity per year (one vehicle)", size=10.5, fill=MUTED))
  body.append(rect(330, ly2 - 10, 14, 12, fill=HW_BG, stroke=HW, rx=2))
  body.append(text(350, ly2, "simulation capacity (no credit until §5.3)", size=10.5, fill=MUTED))
  body.append(line(590, ly2 - 4, 604, ly2 - 4, stroke=SW, sw=1, dash="2 3"))
  body.append(text(610, ly2, "band edge read from words (\"tens to low hundreds\")", size=10.5, fill=MUTED))
  ly3 = ly2 + 20
  body.append(text(40, ly3, "All marks are dashed: §4 calls every numeric target a placeholder until the " +
                   "project lead freezes it (OI-3); none is demonstrated. Replay and field monitoring have no " +
                   "number in §3.2 and are not drawn.", size=10.5, fill=MUTED))
  height = int(ly3 + 22)
  desc = (f"Two log-scale panels with one row per validation target VT-01 to VT-{n:02d}. Left: driving exposure " +
          "in km (hours at 64 km/h); VT-01 rate-level needs about 6 × 10^5 mi (case D), VT-04 and VT-15(b) need " +
          "about 3 × 10^3 km and 3 h. The public-road band of 10^4 to 2 × 10^4 km per year is below case D and " +
          "far below cases A to C. Right: counts per scenario, from 14 to 299, inside or near the closed-course " +
          "band (tens to low hundreds) and below the simulation band (10^3 to 10^5 runs, no credit yet). " +
          "VT-07 to VT-11 have no exposure figure. All values are placeholders until the project lead freezes them (OI-3).")
  return svg(W, height, "Figure 4-1 · Validation targets on a log scale", desc, body)


def build() -> str:
  return figure(parse(SOURCE.read_text(encoding="utf-8")))


def main(argv: list[str]) -> int:
  check = "--check" in argv
  md = SOURCE.read_text(encoding="utf-8")
  missing = missing_sources(md)
  targets = parse(md)
  unknown = sorted(({m["vt"] for m in MARKS} | set(NO_COUNT)) - {t.ident for t in targets})
  uncovered = [t.ident for t in targets if t.ident not in NO_COUNT and t.ident not in {m["vt"] for m in MARKS}]
  if missing or unknown or uncovered:
    for s in missing:
      print(f"source text no longer in WP-V-02: {s}", file=sys.stderr)
    for s in unknown:
      print(f"figure data names {s}, which is not a §4 row", file=sys.stderr)
    for s in uncovered:
      print(f"§4 row {s} has no figure data (MARKS or NO_COUNT)", file=sys.stderr)
    print("review the figure data in fig_v02_validation_targets.py against WP-V-02 and regenerate", file=sys.stderr)
    return 1
  out = figure(targets)
  path = HERE / OUTPUT
  if check:
    if not path.exists() or path.read_text(encoding="utf-8") != out:
      print(f"stale: {OUTPUT}", file=sys.stderr)
      print("run: python3 assurance/06-validation/figures/fig_v02_validation_targets.py", file=sys.stderr)
      return 1
    print(f"fig_v02_validation_targets: {OUTPUT} current, {len(sources())} source texts found")
    return 0
  path.write_text(out, encoding="utf-8")
  print(f"fig_v02_validation_targets: wrote {OUTPUT}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
