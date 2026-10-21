#!/usr/bin/env python3
"""Draw the WP-C-04 safety goal -> FSR -> allocation figure from the document (generated, not hand-drawn).

Figure 5-1 (`figures/fig-c04-5-1-sg-fsr-allocation.svg`): for each safety goal of WP-C-04 §3 (ASIL,
safe state, preliminary FTTI), the FSRs of §5 with their ASIL, the other safety goals each FSR serves
according to the §9 trace, and the elements named in the FSR's Alloc column.

WP-C-04 is the source of record. Edit it and regenerate:

    python3 fsc_figures.py            # write figures/*.svg
    python3 fsc_figures.py --check    # fail if the committed figure is stale

Figures 8-1 … 8-3 (the FTTI scene sheets, one card per safety goal) are drawn by `fsc_scenes.py` from the same parse.

Standard library only. Drawing helpers and the ASIL colour scale are shared with ../hara/hara_figures.py.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "hara"))
import hara_figures as hf  # noqa: E402
from hara_figures import INK, MUTED, HAIR, ASIL_FILL, ASIL_TEXT, ASIL_STROKE, t, wrap, pill, header, svg_doc  # noqa: E402
sys.path.insert(0, str(HERE))
import fsc_scenes  # noqa: E402

SOURCE = HERE.parent / "WP-C-04-functional-safety-concept.md"
OUT_DIR = HERE / "figures"
NAME = "fig-c04-5-1-sg-fsr-allocation.svg"

ELEMENT_RE = re.compile(r"E-0\d(?:/(?:DM|HMI))?|EXT-[A-Z]+")
# Column order and short captions for the elements that WP-C-04 §5 allocates to (WP-C-04 §2).
ELEMENTS = [
  ("E-03", "envelope"), ("E-05", "relay"), ("E-01", "SoC SW"), ("E-01/DM", "DM chain"),
  ("E-01/HMI", "HMI"), ("E-02", "ML models"), ("EXT-EPS", "EPS"), ("EXT-PCM", "PCM / brake"), ("EXT-CLU", "cluster"),
]


class FigureError(Exception):
  pass


@dataclass
class Fsr:
  ident: str
  goal: str
  asil: str          # "C", "B", "A", "QM", "ext", "ref"
  asil_text: str
  alloc_text: str
  elements: list[str]
  serves: list[str] = field(default_factory=list)


@dataclass
class Goal:
  ident: str
  statement: str
  asil_text: str
  safe_state: str
  ftti: str
  fsrs: list[Fsr] = field(default_factory=list)


def _section(md: str, num: int) -> str:
  m = re.search(rf"^## {num}\. .*?$(.*?)(?=^## \d+\. )", md, re.M | re.S)
  if not m:
    raise FigureError(f"WP-C-04 §{num} not found")
  return m.group(1)


def _cells(line: str) -> list[str]:
  return [c.strip() for c in line.strip()[1:-1].split("|")]


def _expand(spec: str, known: list[str]) -> list[str]:
  """'FSR-03.01, 03.03–03.06' -> ids, using the defined FSR list for ranges."""
  out = []
  for part in spec.replace("FSR-", "").split(","):
    part = part.strip()
    if "–" in part:
      a, b = (p.strip() for p in part.split("–"))
      ia, ib = known.index(f"FSR-{a}"), known.index(f"FSR-{b}")
      out += known[ia:ib + 1]
    elif part:
      if f"FSR-{part}" not in known:
        raise FigureError(f"§9 trace names unknown FSR-{part}")
      out.append(f"FSR-{part}")
  return out


def parse(md: str) -> list[Goal]:
  goals: dict[str, Goal] = {}
  for line in _section(md, 3).splitlines():
    if re.match(r"^\| SG-\d\d \|", line):
      c = _cells(line)
      goals[c[0]] = Goal(c[0], c[1], c[2], c[3], c[4])
  fsrs: dict[str, Fsr] = {}
  order: list[str] = []
  for line in _section(md, 5).splitlines():
    if not line.startswith("| FSR-"):
      continue
    c = _cells(line)
    if len(c) != 6:
      raise FigureError(f"§5 row has {len(c)} cells: {line[:40]}")
    ident, _, asil_text, alloc = c[0], c[1], c[2], c[3]
    goal = f"SG-{ident[4:6]}"
    if goal not in goals:
      raise FigureError(f"{ident}: no safety goal {goal} in §3")
    if asil_text.startswith("—"):
      asil = "ext"
    elif asil_text.startswith("as ref"):
      asil = "ref"
    else:
      asil = asil_text.split()[0]
      if asil not in ASIL_FILL:
        raise FigureError(f"{ident}: unexpected ASIL {asil_text!r}")
    elements = []
    for e in ELEMENT_RE.findall(alloc):
      if e not in elements:
        elements.append(e)
    if not elements and not alloc.startswith("as ref"):
      raise FigureError(f"{ident}: no element in Alloc {alloc!r}")
    for e in elements:
      if e not in dict(ELEMENTS):
        raise FigureError(f"{ident}: element {e} has no column; add it to ELEMENTS")
    f = Fsr(ident, goal, asil, asil_text, alloc, elements)
    fsrs[ident] = f
    order.append(ident)
    goals[goal].fsrs.append(f)
  sgs = list(goals)
  for line in _section(md, 9).splitlines():
    if line.startswith("| FSR |"):
      # The header may name goals that have no FSR section of their own yet (SG-08, HARA v0.4); they are traced only.
      head = _cells(line)[1:]
      if head[:len(goals)] != list(goals):
        raise FigureError(f"§9 header {head} does not start with the §5 goals {list(goals)}")
      sgs = head
      continue
    if not line.startswith("| FSR-"):
      continue
    c = _cells(line)
    if len(c) != 1 + len(sgs):
      raise FigureError(f"§9 row has {len(c)} cells: {line[:40]}")
    for ident in _expand(c[0], order):
      fsrs[ident].serves += [sg for sg, mark in zip(sgs, c[1:], strict=True) if mark == "●" and sg not in fsrs[ident].serves]
  for f in fsrs.values():
    if not f.serves:
      raise FigureError(f"{f.ident}: not in the §9 trace")
    if f.goal not in f.serves:
      raise FigureError(f"{f.ident}: §9 trace does not mark its own goal {f.goal}")
  return list(goals.values())


def marker(cx, cy, asil):
  if asil == "ext":
    return f'<circle cx="{cx}" cy="{cy:g}" r="5.5" fill="#FFFFFF" stroke="#64748B" stroke-width="1.8"/>'
  key = asil if asil in ASIL_FILL else "QM"
  fill = ASIL_FILL[key] if key != "QM" else "#94A3B8"
  stroke = ASIL_STROKE[key] if key != "QM" else "#64748B"
  return f'<circle cx="{cx}" cy="{cy:g}" r="6" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>'


def figure() -> str:
  goals = parse(SOURCE.read_text(encoding="utf-8"))
  w = 1280
  CX, CW = 40, 300                 # goal card
  FX = 356                         # FSR id
  AX = 450                         # ASIL pill
  SX = 520                         # also serves
  EX0, EW = 664, 64                # element columns
  RH, BG = 21, 14                  # row height, band gap
  body = header(w, "Figure 5-1 · Safety goals, functional safety requirements and allocation",
                f"{len(goals)} safety goals (§3) → {sum(len(g.fsrs) for g in goals)} FSRs (§5) → allocated elements (§5 Alloc), with the §9 trace",
                "WP-C-04 §3, §5, §9", "safe states §6 · FTTI §8")
  y0 = 104
  body.append(t(CX, y0 + 30, "SAFETY GOAL · SAFE STATE · FTTI (§3)", 10.5, MUTED, 700, extra=' letter-spacing=".04em"'))
  body.append(t(FX, y0 + 30, "FSR", 10.5, MUTED, 700, extra=' letter-spacing=".04em"'))
  body.append(t(AX, y0 + 30, "ASIL", 10.5, MUTED, 700, extra=' letter-spacing=".04em"'))
  body.append(t(SX, y0 + 30, "ALSO SERVES (§9)", 10.5, MUTED, 700, extra=' letter-spacing=".04em"'))
  n_item = sum(1 for e, _ in ELEMENTS if not e.startswith("EXT"))
  body.append(t(EX0 + n_item * EW / 2, y0 + 2, "Item elements", 11, INK, 700, "middle"))
  body.append(f'<line x1="{EX0 + 6}" y1="{y0 + 8}" x2="{EX0 + n_item * EW - 6}" y2="{y0 + 8}" stroke="#94A3B8"/>')
  body.append(t(EX0 + n_item * EW + (len(ELEMENTS) - n_item) * EW / 2, y0 + 2, "External measures (AoU)", 11, INK, 700, "middle"))
  body.append(f'<line x1="{EX0 + n_item * EW + 6}" y1="{y0 + 8}" x2="{EX0 + len(ELEMENTS) * EW - 6}" y2="{y0 + 8}" stroke="#94A3B8"/>')
  for i, (e, cap) in enumerate(ELEMENTS):
    cx = EX0 + i * EW + EW / 2
    body.append(t(cx, y0 + 26, e, 10.5, INK, 700, "middle"))
    body.append(t(cx, y0 + 40, cap, 9.5, MUTED, None, "middle"))
  y = y0 + 54
  body.append(f'<line x1="{CX}" y1="{y - 6}" x2="{w - 40}" y2="{y - 6}" stroke="#CBD5E1"/>')
  guide_idx = len(body)       # band shading and column guides go here, under the bands' content
  bands: list[str] = []
  for gi, g in enumerate(goals):
    asil = g.asil_text.split()[0]
    stmt = wrap(g.statement, CW - 40, 11, True)
    ss = wrap("Safe state: " + g.safe_state, CW - 34, 10.5)
    ft = wrap("FTTI: " + g.ftti, CW - 34, 10.5)
    card_h = 34 + 14 * len(stmt) + 6 + 13.5 * (len(ss) + len(ft)) + 10
    rows_h = len(g.fsrs) * RH
    band_h = max(card_h, rows_h + 8)
    if gi % 2 == 0:
      bands.append(f'<rect x="{FX - 10}" y="{y}" width="{w - 40 - FX + 10}" height="{band_h}" rx="6" fill="#F8FAFC"/>')
    body.append(f'<rect x="{CX}" y="{y}" width="{CW}" height="{card_h:g}" rx="9" fill="#FFF7ED" stroke="#C2410C" stroke-width="1.5"/>')
    body.append(t(CX + 12, y + 21, g.ident, 13, INK, 700))
    p, _ = pill(CX + 66, y + 8, "ASIL " + g.asil_text, ASIL_FILL.get(asil, "#F8FAFC"), ASIL_TEXT.get(asil, INK), 18, 10,
                ASIL_STROKE.get(asil))
    body.append(p)
    ty = y + 34
    for ln in stmt:
      ty += 14
      body.append(t(CX + 12, ty - 3, ln, 11, INK, 600))
    ty += 6
    for ln in ss + ft:
      ty += 13.5
      body.append(t(CX + 12, ty - 3, ln, 10.5, MUTED))
    ry = y + (band_h - rows_h) / 2
    for f in g.fsrs:
      cy = ry + RH / 2
      body.append(t(FX, cy + 4, f.ident, 11, INK, 600))
      if f.asil == "ref":
        body.append(t(AX, cy + 4, f.asil_text, 10, MUTED, None, extra=' font-style="italic"'))
      elif f.asil == "ext":
        body.append(f'<rect x="{AX}" y="{cy - 8}" width="48" height="16" rx="8" fill="#FFFFFF" stroke="#64748B"/>')
        body.append(t(AX + 24, cy + 3.5, "ext.", 9.5, MUTED, 700, "middle"))
      else:
        key = f.asil
        body.append(f'<rect x="{AX}" y="{cy - 8}" width="34" height="16" rx="8" fill="{ASIL_FILL[key]}" stroke="{ASIL_STROKE[key]}"/>')
        body.append(t(AX + 17, cy + 3.5, key, 9.5, ASIL_TEXT[key], 700, "middle"))
      sx = SX
      for sg in f.serves:
        if sg == f.goal:
          continue
        body.append(f'<rect x="{sx}" y="{cy - 7.5}" width="24" height="15" rx="4" fill="#FFFFFF" stroke="#CBD5E1"/>')
        body.append(t(sx + 12, cy + 3.5, sg[3:], 9.5, INK, 600, "middle"))
        sx += 27
      if f.elements:
        for e in f.elements:
          i = [x for x, _ in ELEMENTS].index(e)
          body.append(marker(EX0 + i * EW + EW / 2, cy, f.asil))
      else:
        note = f"{f.alloc_text}: allocation as in the FSRs it references"
        body.append(f'<rect x="{EX0 + 2}" y="{cy - 8}" width="{hf.text_w(note, 10) + 14:.1f}" height="16" rx="3" fill="#FFFFFF"/>')
        body.append(t(EX0 + 8, cy + 4, note, 10, MUTED, None, extra=' font-style="italic"'))
      ry += RH
    y += band_h + BG
  # vertical guides for the element columns
  guides = [f'<line x1="{EX0 + i * EW + EW / 2}" y1="{y0 + 48}" x2="{EX0 + i * EW + EW / 2}" y2="{y - BG}" stroke="#E2E8F0" stroke-width="1"/>'
            for i in range(len(ELEMENTS))]
  sep = EX0 + n_item * EW
  guides.append(f'<line x1="{sep}" y1="{y0 + 10}" x2="{sep}" y2="{y - BG}" stroke="#CBD5E1" stroke-dasharray="4 3"/>')
  body[guide_idx:guide_idx] = bands + guides
  y += 12
  body.append(t(40, y, "Also serves: the other safety goals the §9 trace marks for the FSR (number = SG-0n). "
                "Roles stated in the Alloc column (detection, alert, backstop, ...) are not drawn; see §5 and the allocation summary in §10.", 11, MUTED))
  y += 16
  body.append(t(40, y, "All FSRs have status Proposed; a dot shows allocation, not implementation. SG-01 FSRs carry ASIL C until the "
                "controllability evidence of §4.2 exists. FTTIs are preliminary (§8, WP-S-04).", 11, MUTED))
  y += 22
  body.append(f'<line x1="40" y1="{y}" x2="{w - 40}" y2="{y}" stroke="{HAIR}"/>')
  y += 24
  lx = 40
  for a, lab in (("C", "ASIL C"), ("B", "ASIL B"), ("A", "ASIL A"), ("QM", "QM"), ("ext", "External measure (no ASIL, AoU)")):
    body.append(marker(lx + 6, y - 4, a))
    body.append(t(lx + 18, y, lab, 10.5))
    lx += 18 + hf.text_w(lab, 10.5) + 24
  body.append(t(lx, y, "Marker = FSR allocated to that element; colour = FSR ASIL", 10.5, MUTED))
  body.append(t(w - 40, y, "Generated by fsc_figures.py", 10, MUTED, None, "end"))
  h = int(y + 24)
  desc = ("Matrix of the WP-C-04 functional safety requirements grouped by safety goal. For each goal: ASIL, safe state and preliminary FTTI. "
          "For each FSR: its ASIL, the other goals it serves in the §9 trace, and a marker in the column of each element it is allocated to "
          "(E-03 envelope, E-05 harness relay, E-01 SoC software, E-01/DM, E-01/HMI, E-02, and the external measures EXT-EPS, EXT-PCM, EXT-CLU). "
          + " ".join(f"{g.ident}: {len(g.fsrs)} FSRs." for g in goals))
  return svg_doc(w, h, "Figure 5-1. Safety goals, FSRs and allocation (WP-C-04 §3, §5, §9)", desc, body)


def build() -> dict[str, str]:
  out = {NAME: figure()}
  md = SOURCE.read_text(encoding="utf-8")
  out.update(fsc_scenes.build(parse(md), md, sys.modules[__name__]))  # Figures 8-1 … 8-3, the FTTI scene sheets
  return out


def main(argv: list[str]) -> int:
  check = "--check" in argv
  try:
    outputs = build()
  except (FigureError, hf.FigureError, ValueError) as e:
    print(f"fsc_figures: {e}", file=sys.stderr)
    return 1
  existing = {p.name for p in OUT_DIR.glob("fig-c04-[0-9]*.svg")}  # fig-c04-r*: fsc_routes.py
  if check:
    stale = [n for n, c in outputs.items() if not (OUT_DIR / n).exists() or (OUT_DIR / n).read_text(encoding="utf-8") != c]
    extra = sorted(existing - set(outputs))
    for n in stale:
      print(f"stale: fsc/figures/{n}", file=sys.stderr)
    for n in extra:
      print(f"no longer generated: fsc/figures/{n}", file=sys.stderr)
    if stale or extra:
      print("run: python3 assurance/02-concept/fsc/fsc_figures.py", file=sys.stderr)
      return 1
    print(f"fsc_figures: {len(outputs)} figure(s) current")
    return 0
  OUT_DIR.mkdir(exist_ok=True)
  for n in sorted(existing - set(outputs)):
    (OUT_DIR / n).unlink()
  for n, c in outputs.items():
    (OUT_DIR / n).write_text(c, encoding="utf-8")
  print(f"fsc_figures: wrote {len(outputs)} figure(s) to fsc/figures/")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
