#!/usr/bin/env python3
"""Draw <WP-ID> Figure <N-n>, <what the scenes show> (<fig-xx-n-n-slug>.svg), as top-down scenes from scenekit.py.

<Two or three lines: which hazardous event, fault, triggering condition or mechanism each scene explains, and the
source of every number and phrase on it (the HE-/SH-/FM- row, the FTTI, the requirement). Say that the scenes explain
a mechanism and are not test or simulation output, unless a scene replays a named run.>

Template from .claude/skills/road-scene; replace every <...> and SCENES, then delete this line. Each scene is data:
the car's path in scene units (280 x 130, lanes 30 wide, traffic left to right, ego lane centre y = 84), where the
fault starts, the moment that matters, and the pills. The drawing is the kit's.

    python3 fig_xx_scenes.py            # write the SVG next to this file
    python3 fig_xx_scenes.py --check    # fail if a source phrase moved or the SVG is stale

Standard library only. Output is deterministic. A viewer that does not animate shows each scene's end state.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p / "assurance" / "trace").is_dir())
sys.path.insert(0, str(REPO / "assurance" / "01-management" / "figures"))
import scenekit as sk
from figkit import FAINT, INK, MUTED, header, rect, svg, text, text_w
sys.path.insert(0, str(REPO / "assurance" / "trace" / "tools"))
import terms

OUT = "fig-xx-1-1-scenes.svg"                       # <fig-<wp>-<section>-<n>-<slug>.svg>
NUMBER, TITLE, REF = "X-1", "<Title>", "<WP-ID §n>"
SUBTITLE = "<One line: what to compare across the scenes.>"
SOURCE = REPO / "assurance" / "02-concept" / "WP-C-03-hara.md"   # <the record the phrases are quoted from>
W, K = 1200, 2.0                                    # sheet width; scene scale on the sheet (280 x 130 -> 560 x 260)

# One entry per scene. path: the item car's track (x, y) in scene units; fault_x: where the amber marker goes (on the
# path); moment: (x on the path, label) for the yellow ring; pills: (text, from share of the drive 0..1, style);
# quote: a phrase that must appear in SOURCE (the build fails if it is reworded or removed).
SCENES = [
  {"title": "<Today: the fault, nothing catches it>",
   "say": "<Two lines on what happens and why, in plain words, with the number that matters.>",
   "path": [(14, 84), (60, 84), (90, 83), (120, 78), (150, 70), (180, 62), (210, 57), (240, 55)],
   "fault_x": 60, "moment": (150, "into the next lane"),
   "pills": [("steering offset", 0.2, "bad"), ("stays engaged", 0.45, "bad")],
   "other": [(200, sk.OTHER_LANE)],
   "quote": "HE-01"},
  {"title": "<With the mechanism: the fault is caught in time>",
   "say": "<Two lines: which mechanism, how fast, and where the car ends up.>",
   "path": [(14, 84), (60, 84), (90, 83), (120, 80), (150, 79), (180, 81), (210, 83), (240, 84)],
   "fault_x": 60, "moment": (120, "limit holds"),
   "pills": [("steering offset", 0.2, "bad"), ("torque limit holds", 0.45, "ok")],
   "other": [(200, sk.OTHER_LANE)],
   "quote": "HE-01"},
]
INTENDED = [(14, sk.EGO_LANE), (262, sk.EGO_LANE)]


class FigureError(Exception):
  """A scene no longer matches its source, or breaks the scene style."""


def key_for(path):
  """Loop time at which the car passes x: the car drives the path in DRIVE share of the loop at constant x-speed."""
  x0, x1 = path[0][0], path[-1][0]
  return lambda x: sk.DRIVE * (x - x0) / (x1 - x0)


def y_at(path, x):
  for (xa, ya), (xb, yb) in zip(path, path[1:], strict=False):
    if xa <= x <= xb:
      return ya + (yb - ya) * (x - xa) / (xb - xa or 1)
  raise FigureError(f"x = {x} is not on the path")


def scene(s: dict, uid: str) -> str:
  p, key = s["path"], key_for(s["path"])
  band = sk.d(p + [(p[-1][0], sk.EGO_LANE), (p[0][0], sk.EGO_LANE)]) + " Z"
  mx, label = s["moment"]
  parts = [*sk.straight_road(),
           *[sk.car_at(x, y, sk.other_body()) for x, y in s.get("other", [])],
           *sk.gap_band(band, uid, p[0][0], p[-1][0]),
           sk.intended_path(INTENDED),
           sk.start_marker(sk.pose(p, 1).replace(f"translate({p[1][0]:.1f}", f"translate({p[0][0]:.1f}")),
           sk.performed_path(sk.d(p), sk.draw_on(p, [key(x) for x, _ in p])),
           sk.driving(p, sk.ego_body(), key),
           sk.fault_marker(s["fault_x"], y_at(p, s["fault_x"]), key(s["fault_x"])),
           sk.callout(mx, y_at(p, mx), 6, label, y_at(p, mx) - 11, key(mx)),
           *sk.badges([(t, f, None, st) for t, f, st in s["pills"]], lambda f: sk.DRIVE * f)]
  return "".join(parts)


def wrap(s: str, width: float, size: float) -> list[str]:
  lines, line = [], ""
  for word in s.split():
    cand = (line + " " + word).strip()
    if text_w(cand, size) > width and line:
      lines.append(line)
      line = word
    else:
      line = cand
  return lines + [line]


def build() -> dict[str, str]:
  src = SOURCE.read_text(encoding="utf-8")
  for s in SCENES:
    if s["quote"] not in src:
      raise FigureError(f"{s['title']}: {s['quote']!r} is no longer in {SOURCE.name}")
    if s["pills"] != sorted(s["pills"], key=lambda p: p[1]):
      raise FigureError(f"{s['title']}: pills must stack in the order they appear")
  body = header(W, NUMBER, TITLE, SUBTITLE, REF)
  y, sw, sh = 104, sk.W * K, sk.H * K
  for i, s in enumerate(SCENES):
    body.append(rect(40, y, W - 80, sh + 24, fill="#FFFFFF", rx=10))
    body.append(f'<svg x="52" y="{y + 12}" width="{sw:g}" height="{sh:g}" viewBox="0 0 {sk.W} {sk.H}">' +
                f'<clipPath id="c{i}"><rect width="{sk.W}" height="{sk.H}" rx="6"/></clipPath>' +
                f'<g clip-path="url(#c{i})">{scene(s, str(i))}</g></svg>')
    tx = 52 + sw + 28
    body.append(text(tx, y + 40, s["title"], size=15, weight=700, fill=INK))
    for j, ln in enumerate(wrap(s["say"], W - 52 - tx, 12)):
      body.append(text(tx, y + 66 + j * 17, ln, size=12, fill=MUTED))
    y += sh + 24 + 16
  body.append(text(40, y + 8, "Scenes explain a mechanism; they are not test or simulation output. Dashed green: what " +
                   "should happen; solid red: what does; amber: the fault starts; yellow ring: the moment it matters.",
                   size=11, fill=MUTED))
  foot, y = terms.svg_footer(body, 40, y + 30, W - 80)
  body += foot
  body.append(text(40, y + 6, f"Drawn with scenekit.py by {Path(__file__).name}; CI fails if it is stale.", size=10, fill=FAINT))
  desc = f"{len(SCENES)} top-down scenes: " + "; ".join(f"{s['title']}: {s['say']}" for s in SCENES)
  return {OUT: svg(W, int(y + 24), f"Figure {NUMBER} · {TITLE}", desc, body)}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except FigureError as e:
    print(f"{Path(__file__).stem}: {e}", file=sys.stderr)
    return 1
  rel = HERE.relative_to(REPO).as_posix()
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"{rel}/{n} is stale; run {Path(__file__).name}", file=sys.stderr)
    if not stale:
      print(f"{Path(__file__).stem}: {len(outputs)} figure(s) current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote {rel}/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
