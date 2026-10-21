#!/usr/bin/env python3
"""Render the figures of the wiki page "Building a fault tree" as SVG.

  fta-symbols.svg       the symbols of the WP-A-04 tree diagrams (drawn by the same code, fta_diagrams._symbol), each
                        with an SG-02 example; static;
  fta-item-to-tree.svg  the item boundary diagram reduced to eight blocks; the SG-02 top event; the control path traced
                        back from the EPS and the two warning paths; OR over each block's failures, AND over the two
                        warning channels; the cut sets MCS-02.5 and MCS-02.1, and the requirements that break them;
  fta-and-or.svg        one umbrella (OR) against an umbrella under an awning (AND), then the same question in SG-02;
  fta-traps.svg         a common cause counted twice (order 3 as drawn, 2 in fact: MCS-02.5) and a latent failure
                        (BE-2.14: effective order 1).

The three animations loop with CSS and need no script; a viewer who asks for reduced motion sees the final frame.
Every ID, cut set, order and commit drawn is checked against its source at render time (`problems()`): WP-A-04, the
item definition WP-C-01 and the TSC. When the tree changes, the wiki build fails here instead of drawing the old one.
build_wiki.py renders them next to the pages at each sync (nothing is committed), as it does for animations.py.

Usage: python3 tools/wiki/fta_animations.py [--out DIR] [--check]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "assurance" / "08-analyses" / "fta"))
from animations import BG, GRN, LIGHT, MID, NAVY, RED, RED_BG, W, Timeline, g, norm, stick, svg, t  # noqa: E402
import fta_diagrams  # noqa: E402

FTA = Path("assurance") / "08-analyses" / "WP-A-04-system-fta-fmea.md"
ITEM = Path("assurance") / "02-concept" / "WP-C-01-item-definition.md"
TSC = Path("assurance") / "03-system" / "WP-S-02-technical-safety-requirements.md"

NAMES = ("fta-symbols.svg", "fta-item-to-tree.svg", "fta-and-or.svg", "fta-traps.svg")

CTRL, WARN, BOUND, AMBER, BLUE = "#c2410c", "#6250d6", "#b45309", "#b7791f", "#2a78d6"

# ---------------------------------------------------------------- what is drawn, and where it comes from
SOURCES = [
  (ITEM, "Figure 3-2: item boundary"), (ITEM, "E-01 Application SoC software"), (ITEM, "E-03 Safety MCU firmware"),
  (ITEM, "E-04 Device hardware"), (ITEM, "E-05 Harness"),
  (FTA, "Top event **TE-02**"), (FTA, "BE-2.01 EPS drops LKA assistance"), (FTA, "BE-2.05 SoC crash or hang"),
  (FTA, "BE-2.08 EPS fault warned only by the host"), (FTA, "UE-2.19 EPS stops accepting LKA requests"),
  (FTA, "| MCS-02.5 | 1 (effective) | {BE-2.05} |"), (FTA, "One cause removes control and the SoC warning"),
  (FTA, "the siren comes after 5 s"), (FTA, "{BE-2.05, BE-2.15 or another siren failure}"), (FTA, "TSR-407, TSR-516"),
  (FTA, "| MCS-02.1 | 2 (effective 1 + latent at the baseline) | {BE-2.01, BE-2.08, BE-2.14 or BE-2.15 or BE-2.22} |"),
  (FTA, "TSR-110 and TSR-516(b)"), (FTA, "OI-11"), (FTA, "BE-2.14 is latent at the baseline"), (FTA, "DFM-ACT-011"),
  (FTA, "8a69ccf"), (TSC, "TSR-407"), (TSC, "TSR-516"), (TSC, "TSR-110"),
]


def problems(root: Path = ROOT) -> list[str]:
  errs, cache = [], {}
  for path, phrase in SOURCES:
    if path not in cache:
      p = root / path
      cache[path] = norm(p.read_text(encoding="utf-8")) if p.exists() else ""
    if norm(phrase) not in cache[path]:
      errs.append(f"{path}: drawn fact no longer in the source: {phrase!r}")
  return errs


# ---------------------------------------------------------------- pieces

def blk(x, y, w, h, l1, l2="", fill="#fff", stroke=LIGHT, sw=1.5) -> list[str]:
  o = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>',
       t(x + w / 2, y + (h / 2 + 5 if not l2 else h / 2 - 2), l1, 12.5, NAVY, 700, "middle")]
  if l2:
    o.append(t(x + w / 2, y + h / 2 + 12, l2, 10.5, MID, 400, "middle"))
  return o


def wire(pts, col=MID, sw=2, dash=None) -> str:
  d = f' stroke-dasharray="{dash}"' if dash else ""
  return f'<polyline points="{" ".join(f"{x},{y}" for x, y in pts)}" fill="none" stroke="{col}" stroke-width="{sw}"{d}/>'


def gate(kind, x, y, col=NAVY) -> list[str]:
  """An IEC 61025 gate as the WP-A-04 diagrams draw it, scaled to 0.6, its top at (x, y)."""
  return [f'<g transform="translate({x},{y}) scale(0.6) translate({-x},{-y})">'
          + fta_diagrams._symbol(kind, x, y, col).replace('class="gl"', 'font-size="13" font-weight="700" text-anchor="middle"')
          + "</g>"]


def edge(x1, y1, x2, y2, col=LIGHT) -> str:
  return f'<path d="M{x1},{y1} V{(y1 + y2) / 2} H{x2} V{y2}" fill="none" stroke="{col}" stroke-width="1.6"/>'


def chip(x, y, label, fill, w, size=11.5, ink="#fff") -> list[str]:
  return [f'<rect x="{x}" y="{y - 15}" width="{w}" height="22" rx="11" fill="{fill}"/>', t(x + w / 2, y, label, size, ink, 700, "middle")]


def tree_node(x, y, w, label, col):    # an event box with its gate (OR/AND) right below, top at y
  return blk(x - w / 2, y, w, 30, label, "", "#fff", col, 2)


# ---------------------------------------------------------------- the symbol card

def symbols() -> str:
  h = 500
  b = [t(24, 36, "Fault tree symbols", 23, NAVY, 700),
       t(24, 58, "As the WP-A-04 tree diagrams draw them (IEC 61025), each with an SG-02 example", 14, MID)]
  rows = [
    ("rect", "Top event", "What must not happen: a goal violated.", "TE-02: steering lost, no warning within 1 s"),
    ("rect", "Intermediate event", "A cause that is broken down further.", "“no warning in 1 s”"),
    ("or", "OR gate", "Any one input alone causes the event.", "steering lost: SoC stall, EPS fault, …"),
    ("and", "AND gate", "Only all inputs together cause it.", "no warning: SoC alert AND siren fail"),
    ("basic", "Basic event", "A failure not broken down further.", "BE-2.05 SoC crash or hang"),
    ("undeveloped", "Undeveloped event", "Outside the item, or not developed.", "UE-2.19 EPS stops accepting LKA requests"),
    ("transfer_in", "Transfer", "Continues on another sheet or tree.", "BE-2.05 (as SG-02) in the SG-06 tree"),
    ("cut", "Minimal cut set", "The fewest failures that cause the top event.", "{BE-2.05, siren failure}: order 2"),
  ]
  for i, (kind, name, what, ex) in enumerate(rows):
    col, r = i % 2, i // 2
    x, y = 24 + col * 340, 82 + r * 94
    b.append(f'<rect x="{x}" y="{y}" width="332" height="84" rx="10" fill="#fff" stroke="{LIGHT}"/>')
    cx = x + 40
    if kind == "rect":
      sw = 3 if name == "Top event" else 1.7
      b.append(f'<rect x="{cx - 26}" y="{y + 24}" width="52" height="30" rx="3" fill="#fff" stroke="{NAVY}" stroke-width="{sw}"/>')
    elif kind == "cut":
      b += chip(cx - 28, y + 46, "{ , }", NAVY, 56)
    else:
      b.append(fta_diagrams._symbol(kind, cx, y + 22, NAVY).replace('class="gl"', 'font-size="7.5" font-weight="700" text-anchor="middle"'))
    b += [t(x + 82, y + 26, name, 14, NAVY, 700), t(x + 82, y + 46, what, 11.5, NAVY), t(x + 82, y + 66, ex, 11, MID, 400, "start", True)]
  b.append(t(24, h - 16, "Order: how many failures the cut set needs. Effective order: the same, not counting failures already "
             "present (latent).", 12, MID))
  return svg(h, "Fault tree symbols", "Top event, intermediate event, OR gate, AND gate, basic event (circle), undeveloped "
             "event (diamond), transfer (triangle) and minimal cut set, each with an example from the SG-02 tree of WP-A-04.",
             Timeline(1.0), b)


# ---------------------------------------------------------------- from the item diagram to a tree

def item_to_tree() -> str:
  tl, h = Timeline(26.0), 750
  b = [t(24, 36, "From the item diagram to a fault tree", 23, NAVY, 700),
       t(24, 58, "SG-02, and how the tree checks the requirements", 14, MID)]
  steps = [(0.4, "1 · Start from the item boundary diagram (WP-C-01 Figure 3-2)"),
           (3.4, "2 · Pick a safety goal and write its top event"),
           (6.0, "3 · Trace the function back from the actuator, block by block"),
           (9.4, "4 · For each block on the path: its input, process or output fails → OR"),
           (13.0, "5 · A second, independent channel (the siren) → AND"),
           (16.4, "6 · Read off the minimal cut sets"),
           (20.0, "7 · Each cut set needs a requirement that breaks it, and a test that injects it")]
  for i, (t0, cap) in enumerate(steps):
    t1 = steps[i + 1][0] - 0.2 if i + 1 < len(steps) else None
    b.append(g(f"{tl.show(t0, t1)} {'fin' if t1 is None else 'tr'}",
               [f'<rect x="24" y="70" width="{W - 48}" height="28" rx="6" fill="{NAVY}"/>', t(36, 89, cap, 13, "#fff", 600)]))
  dy = 112
  d = [f'<rect x="128" y="{dy}" width="440" height="200" rx="12" fill="#fffaf2" stroke="{BOUND}" stroke-width="1.8" stroke-dasharray="7 5"/>',
       t(140, dy + 16, "ITEM BOUNDARY", 10.5, BOUND, 700)]
  d += blk(24, dy + 30, 88, 150, "Driver", "outside", "#f1f3f7")
  d += blk(146, dy + 28, 92, 44, "Cameras", "E-04")
  d += blk(260, dy + 24, 140, 56, "E-01 SoC", "openpilot · QM")
  d += blk(422, dy + 24, 130, 56, "E-03 panda MCU", "envelope · ASIL C", "#fff6ef", CTRL)
  d += blk(146, dy + 120, 112, 44, "Display", "SoC alerts")
  d += blk(280, dy + 120, 120, 44, "Speaker", "panda siren")
  d += blk(422, dy + 120, 130, 44, "E-05 harness", "switch · CAN")
  d += blk(590, dy + 112, 106, 60, "EPS", "vehicle · outside", "#f1f3f7")
  d += [wire([(238, dy + 50), (260, dy + 50)]), wire([(400, dy + 52), (422, dy + 52)]), wire([(487, dy + 80), (487, dy + 120)]),
        wire([(552, dy + 142), (590, dy + 142)]), wire([(300, dy + 80), (300, dy + 100), (202, dy + 100), (202, dy + 120)]),
        wire([(470, dy + 80), (470, dy + 100), (380, dy + 100), (380, dy + 120)]), wire([(146, dy + 142), (112, dy + 142)]),
        wire([(280, dy + 160), (270, dy + 180), (112, dy + 170)], MID, 1.5, "4 3"),
        wire([(68, dy + 180), (68, dy + 195), (643, dy + 195), (643, dy + 172)], MID, 1.5, "4 3"),
        t(356, dy + 191, "the driver steers when warned", 10.5, MID, 400, "middle", True)]
  b.append(g(f"{tl.show(0.4)} fin", d))
  b.append(g(f"{tl.show(6.3)} fin", [f'<rect x="588" y="{dy + 110}" width="110" height="64" rx="8" fill="none" stroke="{CTRL}" stroke-width="3"/>']))
  for i, (x, y, w, hh) in enumerate([(420, dy + 118, 134, 48), (420, dy + 22, 134, 60), (258, dy + 22, 144, 60), (144, dy + 26, 96, 48)]):
    b.append(g(f"{tl.show(6.8 + i * 0.5)} fin", [f'<rect x="{x}" y="{y}" width="{w}" height="{hh}" rx="8" fill="none" stroke="{CTRL}" stroke-width="3"/>']))
  b.append(g(f"{tl.show(8.6)} fin", [
    f'<rect x="144" y="{dy + 118}" width="116" height="48" rx="8" fill="none" stroke="{WARN}" stroke-width="3"/>',
    f'<rect x="278" y="{dy + 118}" width="124" height="48" rx="8" fill="none" stroke="{WARN}" stroke-width="3"/>',
    t(570, dy + 228, "orange: control path · violet: warning paths", 11, MID, 600, "end")]))
  ty = 360
  b.append(g(f"{tl.show(3.6)} fin", [f'<rect x="210" y="{ty}" width="300" height="40" rx="8" fill="#f1f3f7" stroke="{NAVY}" stroke-width="2.5"/>',
                                      t(360, ty + 17, "TE-02 · steering lost and", 12.5, NAVY, 700, "middle"),
                                      t(360, ty + 32, "the driver not warned within 1 s", 11, MID, 400, "middle")]))
  tr = [edge(360, ty + 40, 360, ty + 46)] + gate("and", 360, ty + 46) + [edge(360, ty + 69, 180, ty + 90), edge(360, ty + 69, 540, ty + 90)]
  tr += tree_node(180, ty + 90, 140, "steering lost", CTRL) + tree_node(540, ty + 90, 140, "no warning in 1 s", WARN)
  tr += [edge(180, ty + 120, 180, ty + 128)] + gate("or", 180, ty + 128, CTRL)
  b.append(g(f"{tl.show(9.6)} fin", tr))
  for i, (x, l1, l2) in enumerate([(70, "SoC stalls", "E-01 process"), (180, "EPS fault", "EPS output"), (290, "camera wrong", "E-04 input")]):
    b.append(g(f"{tl.show(10.3 + i * 0.6)} fin", [edge(180, ty + 151, x, ty + 172)] + blk(x - 52, ty + 172, 104, 40, l1, l2)))
  w = [edge(540, ty + 120, 540, ty + 128)] + gate("and", 540, ty + 128, WARN)
  w += [edge(540, ty + 151, 480, ty + 172), edge(540, ty + 151, 612, ty + 172)]
  w += blk(424, ty + 172, 112, 40, "SoC alert fails", "Display") + blk(556, ty + 172, 112, 40, "siren fails", "E-03 · speaker", "#fff6ef", CTRL)
  b.append(g(f"{tl.show(13.2)} fin", w))
  b.append(g(f"{tl.show(14.4)} fin", [f'<path d="M70,{ty + 212} q0,30 120,30 h230 q60,0 60,-30" fill="none" stroke="{RED}" stroke-width="2" stroke-dasharray="5 4"/>',
                                       t(260, ty + 236, "a stalled SoC cannot alert: same cause", 11, RED, 700, "middle", True)]))
  cy = ty + 278
  b.append(g(f"{tl.show(16.6)} fin", [t(24, cy, "Cut sets", 12.5, MID, 700)] + chip(96, cy, "{SoC stalls, siren fails}", NAVY, 200)
             + chip(304, cy, "{EPS fault, SoC alert fails, siren fails}", NAVY, 280)))
  b.append(g(f"{tl.show(18.0)} fin", [t(96, cy + 24, "MCS-02.5 · order 2 by design", 10.5, MID), t(304, cy + 24, "MCS-02.1 · order 3", 10.5, MID)]))
  b.append(g(f"{tl.show(20.4)} fin", chip(96, cy + 52, "TSR-407 · TSR-516 → plant run", GRN, 200, 10.5)))
  b.append(g(f"{tl.show(21.4)} fin", chip(304, cy + 52, "TSR-110 · TSR-516(b) → HIL timing (OI-11)", AMBER, 280, 10.5)))
  b.append(g(f"{tl.show(22.6)} fin", [t(24, cy + 82, "A cut set with no requirement is a gap; a requirement with no cut set may not be needed.", 12, NAVY, 600)]))
  b.append(stick(W - 40, h - 8, "point"))
  return svg(h, "From the item diagram to a fault tree (animated)",
             "The item boundary diagram reduced to eight blocks; the SG-02 top event TE-02; the control path traced from the EPS "
             "back to the cameras, and the two warning paths; an OR over the failures of each block on the control path and an AND "
             "over the two warning channels; the SoC stall also removes the SoC alert; the cut sets {SoC stalls, siren fails} "
             "(MCS-02.5) and {EPS fault, SoC alert fails, siren fails} (MCS-02.1); each broken by TSRs and shown by a test.", tl, b)


# ---------------------------------------------------------------- AND or OR?

def person(x, y) -> list[str]:
  return [f'<g stroke="{NAVY}" stroke-width="3" stroke-linecap="round" fill="none">',
          f'<circle cx="{x}" cy="{y - 62}" r="9" fill="{BG}"/>', f'<line x1="{x}" y1="{y - 53}" x2="{x}" y2="{y - 22}"/>',
          f'<line x1="{x}" y1="{y - 22}" x2="{x - 10}" y2="{y}"/>', f'<line x1="{x}" y1="{y - 22}" x2="{x + 10}" y2="{y}"/>',
          f'<line x1="{x}" y1="{y - 45}" x2="{x + 14}" y2="{y - 76}"/>', f'<line x1="{x}" y1="{y - 45}" x2="{x - 12}" y2="{y - 30}"/></g>']


def umbrella(x, y, col=NAVY) -> list[str]:
  return [f'<path d="M{x - 46},{y + 4} q46,-46 92,0 z" fill="{col}" opacity="0.9"/>',
          f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + 30}" stroke="{NAVY}" stroke-width="2.5"/>']


def torn(x, y, label_x, label_y) -> list[str]:
  return umbrella(x + 14, y - 108, "#c9d1df") + [f'<path d="M{x - 2},{y - 140} l10,16 l-12,8 l12,10" fill="none" stroke="{RED}" stroke-width="3"/>',
                                                 t(label_x, label_y, "torn", 13, RED, 700)]


def rain(x0, x1, y0, y1) -> list[str]:
  return [f'<line x1="{x0 + i * 16 + (j % 2) * 8}" y1="{y0 + j * 26}" x2="{x0 + i * 16 + (j % 2) * 8 - 4}" y2="{y0 + j * 26 + 10}" '
          f'stroke="{BLUE}" stroke-width="2" stroke-linecap="round" opacity="0.6"/>'
          for i in range(int((x1 - x0) / 16)) for j in range(int((y1 - y0) / 26))]


def drops(x, y) -> list[str]:
  return [f'<line x1="{x + dx}" y1="{y + dy}" x2="{x + dx - 3}" y2="{y + dy + 9}" stroke="{BLUE}" stroke-width="2.4" stroke-linecap="round"/>'
          for dx, dy in ((-16, 0), (14, 6), (-6, 18), (20, 26), (-20, 32))]


def mini_tree(x, y, top, kind, col, leaves) -> list[str]:
  """A top box at (x, y), its gate, and two leaves."""
  o = blk(x, y, 110, 30, top, "", RED_BG, RED) + [edge(x + 55, y + 30, x + 55, y + 36)] + gate(kind, x + 55, y + 36, col)
  o += [edge(x + 55, y + 59, x + 21, y + 78), edge(x + 55, y + 59, x + 91, y + 78)]
  return o + blk(x - 12, y + 78, 66, 30, leaves[0]) + blk(x + 58, y + 78, 66, 30, leaves[1])


def and_or() -> str:
  tl, h = Timeline(18.0), 640
  b = [t(24, 36, "AND or OR?", 23, NAVY, 700), t(24, 58, "One question decides every gate", 14, MID)]
  L, R, top = 24, 368, 78
  for x0, head, col in ((L, "One umbrella", CTRL), (R, "Umbrella under an awning", WARN)):
    b += [f'<rect x="{x0}" y="{top}" width="328" height="300" rx="12" fill="#fff" stroke="{LIGHT}"/>', t(x0 + 16, top + 24, head, 15, col, 700)]
  b.append(g(f"{tl.show(0.6)} fin", rain(L + 30, L + 320, top + 40, top + 120) + rain(R + 30, R + 320, top + 40, top + 80)))
  px, py = L + 120, top + 236
  b += person(px, py)
  b.append(g(f"{tl.show(0.4, 2.4)} tr", umbrella(px + 14, py - 108)))
  b.append(g(f"{tl.show(2.6)} fin", torn(px, py, px - 92, py - 104)))
  b.append(g(f"{tl.show(3.4)} fin", drops(px, py - 96) + [t(px - 92, py - 30, "wet", 16, RED, 700)]))
  b.append(g(f"{tl.show(4.2)} fin", mini_tree(L + 196, top + 120, "wet", "or", CTRL, ("torn", "forgot it"))
             + [t(L + 196, top + 252, "either one alone → wet", 12.5, CTRL, 700), t(L + 196, top + 270, "nothing else covers you", 12, MID)]))
  qx, qy = R + 120, top + 236
  b += person(qx, qy)
  b.append(g(f"{tl.show(0.4, 9.4)} tr", [f'<path d="M{R + 40},{top + 92} h170 l20,22 h-210 z" fill="{WARN}" opacity="0.85"/>',
                                          f'<line x1="{R + 46}" y1="{top + 114}" x2="{R + 46}" y2="{qy}" stroke="{NAVY}" stroke-width="2"/>']))
  b.append(g(f"{tl.show(9.6)} fin", [f'<path d="M{R + 40},{top + 92} l80,40 l20,-14 l70,40" fill="none" stroke="#c9d1df" stroke-width="6"/>',
                                      t(R + 220, top + 150, "collapsed", 13, RED, 700)]))
  b.append(g(f"{tl.show(0.4, 6.4)} tr", umbrella(qx + 14, qy - 108)))
  b.append(g(f"{tl.show(6.6)} fin", torn(qx, qy, qx + 22, qy - 84)))
  b.append(g(f"{tl.show(7.2, 9.4)} tr", [t(qx + 22, qy - 30, "dry ✓", 15, GRN, 700)]))
  b.append(g(f"{tl.show(10.4)} fin", drops(qx, qy - 96) + [t(qx + 22, qy - 30, "wet", 16, RED, 700)]))
  b.append(g(f"{tl.show(11.0)} fin", mini_tree(R + 196, top + 170, "wet", "and", WARN, ("umbrella", "awning"))
             + [t(R + 16, top + 290, "only both together → wet: an independent backup", 12.5, WARN, 700)]))
  by = top + 330
  b.append(g(f"{tl.show(12.4)} fin", [t(24, by, "The same question in SG-02", 15, NAVY, 700)]
             + tree_node(104, by + 14, 160, "steering lost", CTRL) + [edge(104, by + 44, 104, by + 50)] + gate("or", 104, by + 50, CTRL)
             + [edge(104, by + 73, 62, by + 90), edge(104, by + 73, 153, by + 90), edge(104, by + 73, 250, by + 90)]
             + blk(16, by + 90, 92, 32, "SoC stalls") + blk(112, by + 90, 82, 32, "EPS fault") + blk(198, by + 90, 104, 32, "camera wrong")
             + [t(24, by + 146, "a chain: one broken link stops steering", 12.5, CTRL, 700)]))
  b.append(g(f"{tl.show(13.6)} fin", tree_node(480, by + 14, 160, "no warning in 1 s", WARN) + [edge(480, by + 44, 480, by + 50)]
             + gate("and", 480, by + 50, WARN) + [edge(480, by + 73, 430, by + 90), edge(480, by + 73, 544, by + 90)]
             + blk(374, by + 90, 112, 32, "SoC alert fails") + blk(492, by + 90, 104, 32, "siren fails")
             + [t(380, by + 146, "two channels: both must fail", 12.5, WARN, 700)]))
  b.append(g(f"{tl.show(14.8)} fin", [f'<rect x="24" y="{by + 166}" width="{W - 48}" height="52" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
                                       t(40, by + 188, "Ask of each input: if this fails alone, does the event above happen?", 14, NAVY, 700),
                                       t(40, by + 208, "Yes → OR.   No, something else still covers it → AND.", 14, NAVY, 600)]))
  return svg(h, "AND or OR? (animated)", "One umbrella: torn or forgotten, either alone gets you wet, an OR gate. An umbrella under "
             "an awning: the torn umbrella leaves you dry until the awning also collapses, an AND gate. In SG-02, steering lost is an "
             "OR of SoC stall, EPS fault and wrong camera; no warning is an AND of the SoC alert and the siren failing.", tl, b)


# ---------------------------------------------------------------- two traps

def meter(x, y, n, col, label) -> list[str]:
  return [f'<rect x="{x}" y="{y}" width="150" height="74" rx="10" fill="#fff" stroke="{col}" stroke-width="2"/>',
          t(x + 75, y + 20, label, 11.5, MID, 700, "middle"), t(x + 75, y + 60, str(n), 36, col, 700, "middle")]


def traps() -> str:
  tl, h = Timeline(22.0), 690
  b = [t(24, 36, "Two traps that make a tree look safer than it is", 22, NAVY, 700),
       t(24, 58, "Both are in SG-02 · the order is how many failures it takes", 14, MID)]
  y1 = 80
  b += [f'<rect x="24" y="{y1}" width="{W - 48}" height="270" rx="12" fill="#fff" stroke="{LIGHT}"/>',
        t(40, y1 + 26, "Trap 1 · a common cause counted twice", 15, RED, 700)]
  tr = [f'<rect x="170" y="{y1 + 44}" width="200" height="30" rx="7" fill="#f1f3f7" stroke="{NAVY}" stroke-width="2.5"/>',
        t(270, y1 + 64, "TE-02", 12.5, NAVY, 700, "middle"), edge(270, y1 + 74, 270, y1 + 80)] + gate("and", 270, y1 + 80)
  tr += [edge(270, y1 + 103, 150, y1 + 118), edge(270, y1 + 103, 390, y1 + 118)]
  tr += tree_node(150, y1 + 118, 120, "steering lost", CTRL) + tree_node(390, y1 + 118, 120, "no warning", WARN)
  tr += [edge(150, y1 + 148, 150, y1 + 168), edge(390, y1 + 148, 335, y1 + 168), edge(390, y1 + 148, 445, y1 + 168)]
  tr += blk(96, y1 + 168, 108, 32, "SoC stalls") + blk(282, y1 + 168, 106, 32, "SoC alert fails") + blk(394, y1 + 168, 100, 32, "siren fails")
  b.append(g(f"{tl.show(0.5)} fin", tr))
  b.append(g(f"{tl.show(1.6, 6.0)} tr", chip(40, y1 + 238, "{SoC stalls, SoC alert fails, siren fails}", NAVY, 300)
             + meter(530, y1 + 60, 3, NAVY, "ORDER, AS DRAWN")))
  b.append(g(f"{tl.show(3.6)} fin", [f'<path d="M150,{y1 + 200} q0,22 80,22 h50 q55,0 55,-22" fill="none" stroke="{RED}" stroke-width="2.2" stroke-dasharray="5 4"/>',
                                      t(250, y1 + 216, "a stalled SoC cannot alert", 11.5, RED, 700, "middle", True)]))
  b.append(g(f"{tl.show(4.8)} fin", [f'<rect x="282" y="{y1 + 168}" width="106" height="32" rx="7" fill="{RED_BG}" stroke="{RED}"/>',
                                      t(335, y1 + 189, "= SoC stalls", 12, RED, 700, "middle")]))
  b.append(g(f"{tl.show(6.2)} fin", chip(40, y1 + 238, "{SoC stalls, siren fails}", RED, 200) + meter(530, y1 + 60, 2, RED, "ORDER, IN FACT")
             + [t(250, y1 + 243, "MCS-02.5", 12, MID, 700), t(530, y1 + 160, "Merge events that share", 12, NAVY, 600),
                t(530, y1 + 176, "a cause, and tag them", 12, NAVY, 600), t(530, y1 + 192, "(C, the DFA of WP-A-03).", 12, NAVY, 600)]))
  y2 = 366
  b += [f'<rect x="24" y="{y2}" width="{W - 48}" height="300" rx="12" fill="#fff" stroke="{LIGHT}"/>',
        t(40, y2 + 26, "Trap 2 · a failure that has already happened, unseen (latent)", 15, RED, 700)]
  b.append(g(f"{tl.show(9.0)} fin", chip(40, y2 + 62, "{SoC stalls, siren fails}", NAVY, 200) + meter(530, y2 + 40, 2, NAVY, "ORDER")
             + blk(60, y2 + 92, 120, 40, "SoC stalls", "random, any day") + blk(220, y2 + 92, 150, 40, "siren fails", "needs a trigger…")))
  hatch = " ".join(f"M{226 + 20 * i},{y2 + 128} l30,-32" for i in range(6))
  b.append(g(f"{tl.show(11.0)} fin", [f'<rect x="220" y="{y2 + 92}" width="150" height="40" rx="7" fill="#e9ebf0"/>',
             f'<path d="{hatch} M346,{y2 + 128} l20,-22" stroke="#c9d1df" stroke-width="2"/>',
             t(295, y2 + 110, "siren fails", 12.5, NAVY, 700, "middle"), t(295, y2 + 125, "already true", 10.5, RED, 700, "middle"),
             t(40, y2 + 160, "At the baseline the siren came only after 5 s, past the 1 s budget", 12.5, NAVY),
             t(40, y2 + 178, "(BE-2.14, latent): the failure was always there, and nothing showed it.", 12.5, NAVY)]))
  b.append(g(f"{tl.show(13.0)} fin", meter(530, y2 + 124, 1, RED, "EFFECTIVE ORDER") + [t(500, y2 + 172, "→", 26, RED, 700)]))
  b.append(g(f"{tl.show(15.2)} fin", [f'<rect x="40" y="{y2 + 212}" width="{W - 80}" height="58" rx="10" fill="#eaf6ef" stroke="{GRN}"/>',
             t(56, y2 + 234, "Tag latent events. Then add a check that finds them (the start-up siren self-test,", 12.5, NAVY, 600),
             t(56, y2 + 252, "DFM-ACT-011), or make the trigger real (panda 8a69ccf: siren on the stall).", 12.5, NAVY, 600)]))
  return svg(h, "Two traps in a fault tree (animated)", "Trap 1: the SoC stall also removes the SoC alert, so the cut set of "
             "order 3 as drawn is in fact {SoC stalls, siren fails}, order 2 (MCS-02.5). Trap 2: at the baseline the siren came "
             "only after 5 s, a latent failure (BE-2.14), so the effective order is 1; tag latent events, then add a check that "
             "finds them or make the trigger real.", tl, b)


def render() -> dict[str, str]:
  return {"fta-symbols.svg": symbols(), "fta-item-to-tree.svg": item_to_tree(), "fta-and-or.svg": and_or(), "fta-traps.svg": traps()}


def write_all(out: Path, root: Path = ROOT) -> None:
  out.mkdir(parents=True, exist_ok=True)
  for name, text in render().items():
    (out / name).write_text(text, encoding="utf-8")


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--out", type=Path, default=None, help="write the SVGs here")
  ap.add_argument("--check", action="store_true", help="fail if a drawn fact is no longer in its source")
  args = ap.parse_args(argv)
  errs = problems()
  for e in errs:
    print(e, file=sys.stderr)
  if args.out is not None and not errs:
    write_all(args.out)
    print(f"wrote {len(NAMES)} figures to {args.out}")
  return 1 if errs else 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
