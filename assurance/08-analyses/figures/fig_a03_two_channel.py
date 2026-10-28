#!/usr/bin/env python3
"""Draw WP-A-03 Figure 4-1: what can make both decomposition channels fail together.

The source of record is `../fmea/analyses/dfa.yaml` (the DFA of the FSC decompositions). This script reads
  * every DFI (assessment and measures), every measure (status) and every decomposition (status),
and draws them on the two channels each decomposition relies on: Channel A, the SoC (EL-03), and Channel B,
the panda envelope (EL-07). Cascading initiators cross the wall from A to B; common causes reach both
channels from one root, inside or outside the item boundary.

The only content kept here is the layout: which group each DFI sits in and its short label (PLACE). A DFI
added to or removed from dfa.yaml without a PLACE entry stops the script, so the figure cannot drop one.

    python3 fig_a03_two_channel.py            # regenerate the SVG
    python3 fig_a03_two_channel.py --check    # fail if the committed SVG is stale

Output is deterministic. Needs PyYAML, as tools/safety/fmea_lint.py does.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "fmea" / "analyses" / "dfa.yaml"
OUTPUT = "fig-a03-4-1-two-channel.svg"
FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"

INK, MUTED, HAIR, LINE = "#0F172A", "#475569", "#CBD5E1", "#94A3B8"
RED, AMBER, GREEN, BOUNDARY = "#D2553F", "#D97706", "#2E9E6A", "#C2410C"
COLOUR = {"insufficient": RED, "open": AMBER, "sufficient": GREEN, "safe_by_design": GREEN}
WORD = {"insufficient": "insufficient", "open": "open", "sufficient": "sufficient", "safe_by_design": "safe by design"}

# Groups in drawing order. "cascade" crosses the wall; the others are common-cause roots.
GROUPS = [
  ("cascade", "Cascading · A makes B fail", None),
  ("board", "Shared board", "inside"),
  ("supply", "Shared device supply", "inside"),
  ("harness", "Harness and EMC", "inside"),
  ("box", "Harness-box supply", "inside"),
  ("vehicle", "Vehicle", "outside"),
  ("development", "Development", "outside"),
  ("field", "Field", "outside"),
]

PLACE = {
  "DFI-13a": ("cascade", "holds reset / BOOT0"),
  "DFI-34": ("cascade", "floods or garbles SPI"),
  "DFI-13b": ("cascade", "sets the safety mode"),
  "DFI-13c": ("cascade", "switches to diagnostic mode"),
  "DFI-13d": ("cascade", "reflashes panda firmware"),
  "DFI-35": ("cascade", "sends stale commands"),
  "DFI-02": ("board", "one clock source"),
  "DFI-04": ("board", "heat at the windshield"),
  "DFI-03": ("board", "board manufacturing defect"),
  "DFI-01a": ("supply", "supply lost"),
  "DFI-01b": ("supply", "brown-out, erratic run"),
  "DFI-07": ("harness", "EMC or ESD at the harness"),
  "DFI-05": ("harness", "loose connector, vibration"),
  "DFI-27a": ("box", "box VIN lost, car on"),
  "DFI-27b": ("box", "box VIN lost, HMI side"),
  "DFI-10": ("vehicle", "same CAN signals to both"),
  "DFI-15": ("vehicle", "SoC drives cluster lamps"),
  "DFI-08": ("development", "one spec, one repository"),
  "DFI-16": ("development", "same people and practice"),
  "DFI-20": ("field", "wrong or half-seated harness"),
  "DFI-36": ("field", "one OTA updates both"),
}

W, H = 1600, 1150


class SourceError(Exception):
  pass


def load(text: str) -> dict:
  data = yaml.safe_load(text)
  dfis = {d["id"]: d for d in data["dfis"]}
  missing = sorted(set(dfis) - set(PLACE))
  extra = sorted(set(PLACE) - set(dfis))
  if missing or extra:
    raise SourceError(f"PLACE out of step with dfa.yaml: not placed {missing}, placed but absent {extra}")
  for i, d in dfis.items():
    if d["assessment"] not in COLOUR:
      raise SourceError(f"{i}: unknown assessment {d['assessment']!r}")
  return data


def needs(dfi: dict, status: dict) -> str:
  """What still closes the DFI: missing measures by ID, then how many exist but are unverified."""
  ms = dfi.get("measures", [])
  required = [m for m in ms if status.get(m) == "required"]
  unverified = [m for m in ms if status.get(m) == "existing_unverified"]
  parts = []
  if required:
    parts.append("needs " + ", ".join(required))
  if unverified:
    parts.append(f"{len(unverified)} unverified")
  if not ms:
    parts.append("no measure yet")
  if not parts:
    parts.append("measures in place")
  return " · ".join(parts)


def draw(data: dict) -> str:
  dfis = {d["id"]: d for d in data["dfis"]}
  status = {m["id"]: m["status"] for m in data["measures"]}
  rev = data["analysis"]["revision"]
  dec = data["decompositions"]
  out: list[str] = []

  def text(x, y, s, size=13, weight="normal", fill=INK, anchor="start"):
    out.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
               f'text-anchor="{anchor}">{escape(s)}</text>')

  def rect(x, y, w, h, stroke=INK, fill="#FFFFFF", dash=None, r=10, sw=1.5):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" '
               f'stroke-width="{sw}"{da}/>')

  def line(x1, y1, x2, y2, stroke=LINE, sw=1.6, dash=None, arrow=None):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    me = f' marker-end="url(#{arrow})"' if arrow else ""
    out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"{da}{me}/>')

  def pill(cx, cy, i, w=72):
    c = COLOUR[dfis[i]["assessment"]]
    rect(cx - w / 2, cy - 12, w, 24, stroke=c, r=12, sw=2.2)
    text(cx, cy + 4.5, i, 12, "bold", c, "middle")

  def members(key):
    return [(i, label) for i, (g, label) in PLACE.items() if g == key]

  def group(x, y, w, title, rows, fill):
    rect(x, y, w, 38 + 44 * len(rows), stroke=HAIR, fill=fill, r=10)
    text(x + 14, y + 22, title, 13, "bold")
    for k, (i, label) in enumerate(rows):
      cy = y + 46 + 44 * k
      pill(x + 50, cy, i)
      text(x + 96, cy - 1, label, 13)
      text(x + 96, cy + 15, needs(dfis[i], status), 11, fill=MUTED)

  na = sum(1 for x in dec if x["status"] == "not_accepted")
  counts = Counter(d["assessment"] for d in data["dfis"])
  title = "Figure 4-1 · What can make both channels fail together"
  desc = (f"Dependent failure initiators of dfa.yaml rev {rev} on the two channels of the FSC decompositions: "
          f"cascading initiators from the SoC to the panda envelope, and common causes reaching both; "
          f"{na} of {len(dec)} decompositions not accepted.")

  out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
             f'font-family="{FONT}" role="img" aria-labelledby="t d">')
  out.append(f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>')
  out.append("<defs>")
  for name, c in [("aR", RED), ("aA", AMBER), ("aG", GREEN), ("aL", LINE)]:
    out.append(f'<marker id="{name}" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto" '
               f'markerUnits="userSpaceOnUse"><path d="M0,0 L12,6 L0,12 z" fill="{c}"/></marker>')
  out.append('</defs><rect width="100%" height="100%" fill="#FFFFFF"/>')

  text(60, 50, title, 24, "bold")
  text(60, 76, f"Dependent failure initiators of dfa.yaml rev {rev} on the two channels every ASIL decomposition "
               "of the FSC relies on, coloured by their DFA assessment", 14, fill=MUTED)
  text(1540, 50, "IDs as in WP-A-03 §4", 12, "bold", MUTED, "end")
  text(1540, 68, "(a letter marks one part of a §4 initiator)", 11, fill=MUTED, anchor="end")

  # item boundary
  bx, by, bw, bh = 70, 104, 1460, 700
  rect(bx, by, bw, bh, stroke=BOUNDARY, fill="#FFFAF4", dash="9,6", r=18, sw=2)
  rect(bx + 22, by - 13, 300, 26, stroke=BOUNDARY, fill=BOUNDARY, r=13)
  text(bx + 172, by + 5, "ITEM BOUNDARY · comma device + harness", 12, "bold", "#FFFFFF", "middle")

  # channels and wall
  ay, ah = 140, 330
  rect(110, ay, 520, ah, sw=2.2, r=12)
  text(132, ay + 32, "Channel A · SoC", 19, "bold")
  text(132, ay + 54, "EL-03 openpilot driving software · QM(x) side of each decomposition", 12, fill=MUTED)
  rect(970, ay, 520, ah, sw=2.2, r=12)
  text(992, ay + 32, "Channel B · panda envelope", 19, "bold")
  text(992, ay + 54, "EL-07 panda safety model · ASIL(x) side of each decomposition", 12, fill=MUTED)
  line(800, ay - 14, 800, ay + ah + 14, stroke=INK, sw=5, dash="16,9")
  rect(670, ay + ah + 22, 260, 44, stroke=RED, r=8, sw=1.5)
  text(800, ay + ah + 40, "claimed independence", 12, "bold", INK, "middle")
  text(800, ay + ah + 57, f"{na} of {len(dec)} decompositions not accepted", 12, "bold", RED, "middle")

  # cascading: A makes B fail
  marker = {RED: "aR", AMBER: "aA", GREEN: "aG"}
  for k, (i, label) in enumerate(members("cascade")):
    cy = ay + 116 + 36 * k
    c = COLOUR[dfis[i]["assessment"]]
    line(615, cy, 968, cy, stroke=c, sw=2.6, arrow=marker[c])
    text(600, cy + 4.5, label, 13, anchor="end")
    pill(800, cy, i, 78)
    text(992, cy + 4.5, needs(dfis[i], status), 12, fill=MUTED)

  # common-cause manifold into both channels
  my = ay + ah + 100
  line(250, my, 1350, my, sw=2.2)
  line(370, my, 370, ay + ah + 4, sw=2.2, arrow="aL")
  line(1230, my, 1230, ay + ah + 4, sw=2.2, arrow="aL")
  text(380, my - 10, "into A", 11, "bold", MUTED)
  text(1220, my - 10, "into B", 11, "bold", MUTED, "end")

  # roots inside the item, then outside it (routed up through the gaps between the inside groups)
  iy = my + 40
  inside = [g for g in GROUPS if g[2] == "inside"]
  for k, (key, name, _) in enumerate(inside):
    x = 90 + 360 * k
    group(x, iy, 340, name, members(key), "#F4F5F7")
    line(x + 170, iy, x + 170, my)
  oy = by + bh + 44
  outside = [g for g in GROUPS if g[2] == "outside"]
  for k, (key, name, _) in enumerate(outside):
    gx = 440 + 360 * k
    group(gx - 170, oy, 340, name + " · outside the item", members(key), "#EDF2F8")
    line(gx, oy, gx, my, dash="5,4")

  # legend
  ly = oy + 168
  text(60, ly, "DFA assessment", 13, "bold")
  lx = 60
  for a in ("insufficient", "open", "safe_by_design"):
    rect(lx, ly + 12, 40, 20, stroke=COLOUR[a], r=10, sw=2.2)
    text(lx + 52, ly + 27, f"{WORD[a]} ({counts[a]})", 13)
    lx += 210
  blocking = sorted(i for i, d in dfis.items() if d["assessment"] == "insufficient")
  text(60, ly + 66, "Blocking acceptance: " + ", ".join(blocking), 13, "bold", RED)
  text(700, ly, "How to read it", 13, "bold")
  text(700, ly + 26, "Arrows across the wall: one channel corrupts the other. Lines from below: one root "
                     "reaches both.", 13, fill=MUTED)
  text(700, ly + 46, "Dashed lines cross the item boundary from outside. Grey text under each ID: the "
                     "measure still missing (needs DM-nn),", 13, fill=MUTED)
  text(700, ly + 66, "and how many measures exist but are not verified yet. Generated from dfa.yaml by "
                     "fig_a03_two_channel.py.", 13, fill=MUTED)

  # section labels last, on top of the wall and the connectors
  rect(705, ay + 72, 190, 22, stroke="none", fill="#FFFAF4", r=4)
  text(800, ay + 88, "CASCADING · A makes B fail", 12, "bold", INK, "middle")
  rect(640, my + 8, 320, 22, stroke="none", fill="#FFFAF4", r=4)
  text(800, my + 24, "COMMON CAUSE · one root reaches both channels", 12, "bold", INK, "middle")

  out.append("</svg>")
  return "\n".join(out) + "\n"


def build() -> str:
  return draw(load(SOURCE.read_text(encoding="utf-8")))


def main(argv: list[str]) -> int:
  try:
    content = build()
  except SourceError as e:
    print(f"fig_a03_two_channel: {e}", file=sys.stderr)
    return 1
  path = HERE / OUTPUT
  if "--check" in argv:
    if not path.exists() or path.read_text(encoding="utf-8") != content:
      print(f"stale: {OUTPUT}", file=sys.stderr)
      print("run: python3 assurance/08-analyses/figures/fig_a03_two_channel.py", file=sys.stderr)
      return 1
    print("fig_a03_two_channel: figure current")
    return 0
  path.write_text(content, encoding="utf-8")
  print(f"wrote {OUTPUT}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
