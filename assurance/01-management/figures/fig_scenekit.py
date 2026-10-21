#!/usr/bin/env python3
"""Draw the two figures of the scene style page (scene-style.md), with the scene kit itself.

- `fig-scenekit-1-anatomy.svg`: one full scene with every element of the style, numbered, and what each one means.
- `fig-scenekit-2-sizes.svg`: the three scene sizes (full, strip, large) side by side, with their lane geometry and
  the figures that use each.

Drawing them with scenekit.py means the page cannot show a style the figures do not use: change the kit and these
figures go stale with the others.

    python3 fig_scenekit.py            # write the SVGs next to this file
    python3 fig_scenekit.py --check    # fail if one is stale

Standard library only. Output is deterministic. The scenes are drawn at their end state (the still frame), without
animation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scenekit as sk  # noqa: E402
from figkit import HAIR, INK, MUTED, header, svg, text, text_w  # noqa: E402

W = 1200
STILL = re.compile(r"<animate[^>]*/>")


def still(parts):
  """The scene without animation: what a viewer that does not animate shows."""
  return STILL.sub("", "".join(parts))


def num(x, y, n):
  return (f'<circle cx="{x:g}" cy="{y:g}" r="9" fill="{INK}" stroke="#FFFFFF" stroke-width="1.5"/>' +
          text(x, y + 3.8, str(n), size=10.5, fill="#FFFFFF", weight=700, anchor="middle"))


# ---------------------------------------------------------------- figure 1: anatomy

PATH = [(14, 84), (60, 84), (90, 83), (120, 78), (150, 70), (180, 62), (210, 57), (240, 55)]
INTENDED = [(14, 84), (262, 84)]

# element: (number position in scene units, name, what it means)
PARTS = [
  ((272, 118), "Road", "grass, verge, asphalt, white edge lines, dashed centre line; one lane is 30 units (about 3.6 m)"),
  ((26, 66), "Direction of travel", "faded arrow; traffic drives left to right"),
  ((258, 44), "The item's car", "red; the only red car in a scene"),
  ((184, 44), "Other traffic", "grey; a stopped car is paler and shows its hazard lights"),
  ((14, 100), "Start", "where the item's car began, faded"),
  ((105, 98), "What should happen", "dashed green: the intended path (required, needed)"),
  ((262, 100), "Where it should be", "dashed green outline of the car at the same moment"),
  ((168, 50), "What does happen", "solid red: the performed path, drawn in as the car drives"),
  ((205, 73), "The gap", "red shading between intended and performed"),
  ((56, 70), "Fault starts", "amber marker with a bolt: the failure, or the triggering condition"),
  ((120, 52), "The moment it matters", "yellow ring and label: the first harm-relevant event"),
  ((84, 14), "Status pills", "top-left, in order; numbered when they key to marks on the card's chart"),
]


def anatomy() -> str:
  k, x0, y0 = 2.4, 40, 112
  scene = still(sk.straight_road() + [
    sk.car_at(200, sk.OTHER_LANE, sk.OTHER, sk.OTHER_EDGE),
    *sk.gap_band(sk.d(PATH + [(240, 84), (14, 84)]) + " Z", "a", 0, sk.W),
    sk.intended_path(INTENDED), sk.performed_path(sk.d(PATH), ""),
    sk.start_marker("translate(14.0 84.0) rotate(0.0)"),
    f'<g transform="translate(262 84)">{sk.ghost_body()}</g>',
    f'<g transform="translate(240 55) rotate(-4)">{sk.ego_body()}</g>',
    sk.fault_marker(60, 84, 0), sk.callout(130, 75, 6, "into the next lane", 64, 0),
    sk.pill(6, 6, "lead brakes", "drv", num=1), sk.pill(6, 22, "stays engaged", "bad")])
  sw, sh = sk.W * k, sk.H * k
  body = header(W, "S-1", "Anatomy of a top-down scene",
                "Every scene figure uses these elements, drawn by scenekit.py (SVG) or scenekit.js (canvas).",
                "scenekit.py · fig_scenekit.py")
  body.append(f'<svg x="{x0}" y="{y0}" width="{sw:g}" height="{sh:g}" viewBox="0 0 {sk.W} {sk.H}">'
              f'<clipPath id="ka"><rect width="{sk.W}" height="{sk.H}" rx="6"/></clipPath><g clip-path="url(#ka)">{scene}</g></svg>')
  for i, ((px, py), _, _) in enumerate(PARTS, 1):
    body.append(num(x0 + px * k, y0 + py * k, i))
  lx, ly = x0 + sw + 36, y0 + 4
  for i, (_, name, what) in enumerate(PARTS, 1):
    body.append(num(lx + 9, ly + 9, i))
    body.append(text(lx + 26, ly + 8, name, size=12.5, weight=700))
    words, line, yy = what.split(), "", ly + 24
    for wd in words:                                   # wrap the meaning to the column
      cand = (line + " " + wd).strip()
      if text_w(cand, 11) > W - 40 - lx - 26 and line:
        body.append(text(lx + 26, yy, line, size=11, fill=MUTED))
        line, yy = wd, yy + 14
      else:
        line = cand
    body.append(text(lx + 26, yy, line, size=11, fill=MUTED))
    ly = yy + 13
  h = max(y0 + sh, ly) + 30
  body.append(text(40, h - 12, "Charts above a scene use the same pair on white: dashed green #16A34A for what is needed, solid red "
                   "#DC2626 for what happens.", size=11, fill=MUTED))
  desc = "A top-down scene with its twelve elements numbered: " + "; ".join(f"{i} {n}: {w}" for i, (_, n, w) in enumerate(PARTS, 1)) + "."
  return svg(W, int(h), "Figure S-1. Anatomy of a top-down scene", desc, body)


# ---------------------------------------------------------------- figure 2: the three sizes

SIZES = [
  ("Full scene", f"{sk.W} × {sk.H}", "lanes 30, lines at 39 / 69 / 99",
   "HARA guide-word sheets, SOTIF scenes", sk.W, sk.H,
   lambda: sk.straight_road() + [sk.car_at(200, sk.OTHER_LANE, sk.OTHER, sk.OTHER_EDGE), sk.car_at(120, sk.EGO_LANE, sk.EGO, sk.EGO_EDGE)]),
  ("Strip", f"{sk.W} × {sk.STRIP_H}", "the full scene cropped to its lanes (lanes at 25 / 55)",
   "FM cards, hazard log, loss scenarios, FMEA cards", sk.W, sk.STRIP_H,
   lambda: sk.strip_road() + [f'<g transform="translate(200 {sk.STRIP_OTHER})">{sk.other_body(stopped=True)}</g>',
                              sk.car_at(120, sk.STRIP_EGO, sk.EGO, sk.EGO_EDGE), sk.pill(6, 6, "TODAY", "bad")]),
  ("Large scene", f"{sk.LARGE_W} × {sk.LARGE_H}", f"the full scene × {sk.LARGE_K:g}, lines at 62 / 125 / 188",
   "STPA scene cards, TARA threat scenes, FTTI scenes", sk.LARGE_W, sk.LARGE_H,
   lambda: sk.large_road() + [f'<g transform="translate(230 157) scale({sk.LARGE_K})">{sk.ego_body()}</g>',
                              sk.pill(8, 8, "Driver swerves around debris", "drv", 11, 18, 1, 600)]),
]


def sizes() -> str:
  body = header(W, "S-2", "Three scene sizes, one road",
                "The same lane geometry at every size, so a car, a line and a lane look the same in every figure.",
                "scenekit.py · fig_scenekit.py")
  x, y0, scale = 40, 128, 0.95
  for name, dims, geo, users, sw, sh, draw in SIZES:
    w, h = sw * scale, sh * scale
    body.append(f'<svg x="{x:g}" y="{y0}" width="{w:g}" height="{h:g}" viewBox="0 0 {sw} {sh}">'
                f'<clipPath id="ks{sw}{sh}"><rect width="{sw}" height="{sh}" rx="6"/></clipPath>'
                f'<g clip-path="url(#ks{sw}{sh})">{still(draw())}</g></svg>')
    ty = y0 + h + 22
    body.append(text(x, ty, f"{name} · {dims}", size=13, weight=700))
    body.append(text(x, ty + 17, geo, size=11, fill=MUTED))
    body.append(text(x, ty + 33, users, size=11, fill=INK))
    x += w + 36
  hmax = y0 + SIZES[2][5] * scale + 70
  body.append(f'<line x1="40" y1="{hmax:g}" x2="{W - 40}" y2="{hmax:g}" stroke="{HAIR}"/>')
  body.append(text(40, hmax + 22, "Text and pills are not scaled with the large scene: they keep the size the card needs for reading. "
                   "The kit car is 22 × 10 units at 1×, 46 × 21 in the large scene.", size=11, fill=MUTED))
  desc = "The three scene sizes of the scene kit: " + "; ".join(f"{n} {d}, {g}, used by {u}" for n, d, g, u, *_ in SIZES) + "."
  return svg(W, int(hmax + 44), "Figure S-2. Three scene sizes, one road", desc, body)


def build() -> dict[str, str]:
  return {"fig-scenekit-1-anatomy.svg": anatomy(), "fig-scenekit-2-sizes.svg": sizes()}


def main(argv: list[str]) -> int:
  out = build()
  if "--check" in argv:
    stale = [n for n, s in out.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != s]
    if stale:
      print("fig_scenekit: stale " + ", ".join(stale) + "; run python3 fig_scenekit.py")
      return 1
    print(f"fig_scenekit: {len(out)} figure(s) current")
    return 0
  for n, s in out.items():
    (HERE / n).write_text(s, encoding="utf-8")
  print(f"fig_scenekit: wrote {len(out)} figure(s)")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
