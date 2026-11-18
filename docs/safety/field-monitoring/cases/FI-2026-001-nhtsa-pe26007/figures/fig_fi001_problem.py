#!/usr/bin/env python3
"""Draw the three figures of the FI-2026-001 problem statement (NHTSA PE26007): the crash pattern, the three barriers
that must all fail, and the distance openpilot needs to stop.

- fig-fi001-2-1-crash-pattern.svg: three top-down scenes of the pattern the NHTSA ODI resume describes ("stopped or
  slowly moving vehicles within the same travel lane", REPORT §2 fact 3) and the cut-out reveal of RCA §2. Each scene
  quotes its source phrase; the scenes explain the pattern and are not a reconstruction of any one crash.
- fig-fi001-3-1-barriers.svg: the three protection layers of RCA §3 (L1 openpilot, L2 driver, L3 stock AEB/PCS), each
  with its intended function and its weaknesses. A weakness is drawn only when its phrase is still in the layer's
  cell (HOLES), and the common-cause note only while RCA §4 still says it.
- fig-fi001-3-2-stopping-distance.svg: the stopping distances of RCA §3.1 at the openpilot cap (-3.5 m/s²) and at
  about full braking (-8 m/s²), one pair of bars per speed.

    python3 fig_fi001_problem.py            # write the SVGs next to this file
    python3 fig_fi001_problem.py --check    # fail if a source moved or an SVG is stale

Standard library only. Output is deterministic. A viewer that does not animate shows each scene's end state.
Fails (FigureError) on a missing section or column, a layer that is not L1/L2/L3, a phrase no longer in its cell, a
distance row that does not parse or a scene quote that is no longer in its source.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASE = HERE.parent
REPO = next(p for p in HERE.parents if (p / "assurance" / "trace").is_dir())
sys.path.insert(0, str(REPO / "assurance" / "01-management" / "figures"))
import scenekit as sk
from figkit import (AMBER, AMBER_BG, FAINT, GREEN, GREEN_BG, GREY_BG, HAIR, INK, LINE, MUTED, RED, RED_BG, SAFETY,
                    col, header, line, path, plain, rect, section, svg, table, text, text_w)
sys.path.insert(0, str(REPO / "assurance" / "trace" / "tools"))
import terms

REPORT, RCA = CASE / "REPORT.md", CASE / "RCA.md"
REF = "NHTSA PE26007 · problem statement"
W = 960


class FigureError(Exception):
  """A figure no longer matches its source."""


def wrap(s: str, width: float, size: float) -> list[str]:
  lines, cur = [], ""
  for word in s.split():
    cand = (cur + " " + word).strip()
    if text_w(cand, size) > width and cur:
      lines.append(cur)
      cur = word
    else:
      cur = cand
  return lines + [cur]


def footer(body: list[str], y: float, note: str) -> tuple[list[str], float]:
  for ln in wrap(note, W - 80, 11):
    body.append(text(40, y, ln, size=11, fill=MUTED))
    y += 16
  foot, y = terms.svg_footer(body, 40, y + 6, W - 80)
  body += foot
  body.append(text(40, y + 6, f"Drawn by {Path(__file__).name} from the case files; CI fails if it is stale.",
                   size=10, fill=FAINT))
  return body, y + 24


# ---------------------------------------------------------------- Figure 2-1: the crash pattern (scenes)

STOP_X = 232                       # the stopped vehicle's centre; the item car touches it at STOP_X - CAR_L
HIT_X = STOP_X - sk.CAR_L
SCENES = [
  {"title": "A stopped vehicle in the lane",
   "say": "The vehicle ahead is stopped in the item car's lane: a queue tail, a crash, an emergency scene. The car "
          "keeps its speed and strikes it. What should happen: brake and stop behind it.",
   "source": REPORT, "quote": "struck stopped or slowly moving vehicles within the same travel lane",
   "stopped": STOP_X, "ghost": 168, "fault_x": 96, "moment": (HIT_X, "struck"),
   "pills": [("stopped vehicle ahead", 0.0, "info"), ("no braking in time", 0.42, "bad"),
             ("driver does not take over", 0.62, "bad")]},
  {"title": "A slow vehicle in the lane",
   "say": "The vehicle ahead is moving, but much slower. The car closes on it and strikes it. What should happen: "
          "slow down and follow at a safe gap.",
   "source": REPORT, "quote": "Crashes involving stopped or slow moving in-lane vehicles",
   "slow": [(0.0, 120, sk.EGO_LANE), (1.0, STOP_X, sk.EGO_LANE)], "ghost": 168, "fault_x": 96,
   "moment": (HIT_X, "struck"),
   "pills": [("slow vehicle ahead", 0.0, "info"), ("closes without slowing", 0.42, "bad"),
             ("driver does not take over", 0.62, "bad")]},
  {"title": "Revealed late by a cut-out",
   "say": "A lead car hides the stopped vehicle, then changes lane. The stopped vehicle is revealed closer than "
          "openpilot can stop from at -3.5 m/s² (Figure 3-2). One explanation the RCA examines, not a known cause.",
   "source": RCA, "quote": "often hidden behind a lead vehicle until that vehicle **cuts out**",
   "stopped": STOP_X, "ghost": 196, "fault_x": 150, "moment": (HIT_X, "struck"),
   "lead": [(0.0, 64, sk.EGO_LANE), (0.5, 150, sk.EGO_LANE), (0.68, 182, 60), (1.0, 222, sk.OTHER_LANE)],
   "pills": [("lead car changes lane", 0.4, "info"), ("stopped vehicle revealed late", 0.6, "bad")]},
]


def key_for(x0: float, x1: float):
  return lambda x: sk.DRIVE * (x - x0) / (x1 - x0)


def scene(s: dict, uid: str) -> str:
  p = [(14, sk.EGO_LANE), (HIT_X, sk.EGO_LANE)]
  key = key_for(p[0][0], p[-1][0])
  mx, label = s["moment"]
  parts = [*sk.straight_road()]
  if "stopped" in s:
    parts.append(sk.car_at(s["stopped"], sk.EGO_LANE, sk.other_body(stopped=True)))
  if "slow" in s:
    parts.append(sk.drive_t(s["slow"], sk.other_body()))
  if "lead" in s:
    parts.append(sk.drive_turning(s["lead"], sk.other_body()))
  parts += [sk.intended_path([(14, sk.EGO_LANE), (s["ghost"], sk.EGO_LANE)]),
            f'<g transform="translate({s["ghost"]} {sk.EGO_LANE})">{sk.ghost_body()}</g>',
            sk.performed_path(sk.d(p), sk.draw_on(p, [key(x) for x, _ in p])),
            sk.driving(p, sk.ego_body(), key),
            sk.fault_marker(s["fault_x"], sk.EGO_LANE, key(s["fault_x"])),
            sk.callout(mx, sk.EGO_LANE, 8, label, sk.EGO_LANE - 14, key(mx)),
            *sk.badges([(t, f, None, st) for t, f, st in s["pills"]], lambda f: sk.DRIVE * f)]
  return "".join(parts)


def fig_scenes() -> str:
  for s in SCENES:
    if s["quote"] not in s["source"].read_text(encoding="utf-8"):
      raise FigureError(f"{s['title']}: {s['quote']!r} is no longer in {s['source'].name}")
    if s["pills"] != sorted(s["pills"], key=lambda q: q[1]):
      raise FigureError(f"{s['title']}: pills must stack in the order they appear")
  k = 1.5
  body = header(W, "2-1", "The crash pattern", "What NHTSA describes, and the reveal the root cause analysis examines.",
                REF)
  y, sw, sh = 104, sk.W * k, sk.H * k
  for i, s in enumerate(SCENES):
    body.append(rect(40, y, W - 80, sh + 24, fill="#FFFFFF", rx=10))
    body.append(f'<svg x="52" y="{y + 12}" width="{sw:g}" height="{sh:g}" viewBox="0 0 {sk.W} {sk.H}">' +
                f'<clipPath id="c{i}"><rect width="{sk.W}" height="{sk.H}" rx="6"/></clipPath>' +
                f'<g clip-path="url(#c{i})">{scene(s, str(i))}</g></svg>')
    tx = 52 + sw + 24
    body.append(text(tx, y + 38, s["title"], size=16, weight=700))
    for j, ln in enumerate(wrap(s["say"], W - 64 - tx, 12.5)):
      body.append(text(tx, y + 64 + j * 18, ln, size=12.5, fill=MUTED))
    src = "NHTSA ODI resume, quoted in the case report §2" if s["source"] == REPORT else "Root cause analysis §2"
    body.append(text(tx, y + sh + 6, f"Source: {src}", size=10.5, fill=FAINT))
    y += sh + 24 + 14
  body, y = footer(body, y + 8, "Scenes explain the pattern; they are not a reconstruction of any crash. Red car: the "
                   "item's car; dashed green: where it should stop; solid red: what it does; amber: the vehicle "
                   "ahead should have been handled from here; yellow ring: impact.")
  desc = "Three top-down scenes: " + "; ".join(f"{s['title']}: {s['say']}" for s in SCENES)
  return svg(W, int(y), "Figure 2-1 · The crash pattern", desc, body)


# ---------------------------------------------------------------- Figure 3-1: three barriers

LAYERS = {"L1": "Layer 1", "L2": "Layer 2", "L3": "Layer 3"}   # drawn as "Layer n": "L1" is a degradation level elsewhere
# (phrase that must be in the layer's weakness cell, short label drawn on the figure)
HOLES = {
  "L1": [("stationary objects depend on the", "At speed, stopped objects need the camera to see them"),
         ("V_EGO_STATIONARY", "Radar alone is trusted only below 4 m/s"),
         ("capped at **-3.5 m/s²**", "Braking capped at -3.5 m/s²"),
         ("has no AEB function of its own", "No emergency braking of its own")],
  "L2": [("tolerates **5 s**", "5 s eyes-off before the first alert"),
         ("tied to the same perception", "Warning tied to the same perception as layer 1"),
         ("automation complacency", "Over-trust after long good drives")],
  "L3": [("**silences the radar ECU**", "Alpha longitudinal silences the radar ECU"),
         ("`PCS_OFF = 1`", "Sends PCS_OFF = 1: stock PCS turned off"),
         ("leaves the radar ECU and PCS in place", "On camera-ACC cars (our Corolla) PCS stays on")],
}
KEEPS = {"leaves the radar ECU and PCS in place"}          # drawn green: what holds
COMMON = "L1 and L2-warning are not independent"


def barriers() -> list[dict]:
  md = RCA.read_text(encoding="utf-8")
  head, rows = table(section(md, "## 3. Protection-layer"), "Layer")
  cl, cf, cw = col(head, "Layer"), col(head, "Intended function"), col(head, "Weakness found in our inherited baseline")
  out = []
  for r in rows:
    m = re.match(r"(L\d) — (.+)", plain(r[cl]))
    if not m or m.group(1) not in LAYERS:
      raise FigureError(f"unknown layer {r[cl]!r}")
    lid = m.group(1)
    holes = []
    for phrase, label in HOLES[lid]:
      if phrase not in r[cw]:
        raise FigureError(f"{lid}: {phrase!r} is no longer in its weakness cell")
      holes.append((label, phrase in KEEPS))
    out.append({"id": lid, "name": m.group(2), "function": plain(r[cf]), "holes": holes})
  if [b["id"] for b in out] != list(LAYERS):
    raise FigureError(f"layers {[b['id'] for b in out]}, expected {list(LAYERS)}")
  if COMMON not in md:
    raise FigureError(f"{COMMON!r} is no longer in RCA §4")
  return out


def fig_barriers() -> str:
  bs = barriers()
  body = header(W, "3-1", "Three barriers, all of them failed",
                "A collision needs every layer to fail. The weaknesses the root cause analysis found in each.", REF)
  top, h = 150, 390
  cw, gap, x0 = 222, 30, 96
  # the hazard arrow runs through a hole in every layer to the collision
  ay = top + 92
  body.append(text(40, top - 26, "Stopped or slow vehicle ahead", size=12.5, weight=700, fill=SAFETY))
  body.append(path(f"M40 {ay} L{W - 70} {ay}", stroke=SAFETY, sw=3.2))
  body.append(path(f"M{W - 70} {ay - 7} L{W - 56} {ay} L{W - 70} {ay + 7} Z", stroke=SAFETY, sw=1, fill=SAFETY))
  for i, b in enumerate(bs):
    x = x0 + i * (cw + gap)
    body.append(rect(x, top, cw, h, fill=GREY_BG, stroke=LINE, rx=12))
    body.append(rect(x + cw / 2 - 26, ay - 15, 52, 30, fill="#FFFFFF", stroke=RED, sw=1.6, rx=15, dash="4 3"))
    body.append(text(x + 16, top + 22, LAYERS[b["id"]], size=11, weight=700, fill=MUTED))
    nm = wrap(b["name"], cw - 40, 14)
    if len(nm) > 2:
      raise FigureError(f"{b['id']}: name {b['name']!r} is too long for the card")
    for j, ln in enumerate(nm):
      body.append(text(x + 16, top + 42 + j * 18, ln, size=14, weight=700))
    yy = ay + 42
    body.append(text(x + 16, yy, "Meant to:", size=10.5, fill=FAINT, weight=700))
    for ln in wrap(b["function"], cw - 32, 12):
      yy += 17
      body.append(text(x + 16, yy, ln, size=12))
    yy += 18
    body.append(line(x + 16, yy, x + cw - 16, yy, stroke=HAIR, sw=1))
    yy += 20
    body.append(text(x + 16, yy, "Weaknesses found:", size=10.5, fill=FAINT, weight=700))
    yy += 10
    for label, keeps in b["holes"]:
      lines = wrap(label, cw - 44, 11.5)
      hh = 10 + 15 * len(lines)
      fill, stroke = (GREEN_BG, GREEN) if keeps else (RED_BG, RED)
      body.append(rect(x + 12, yy, cw - 24, hh, fill=fill, stroke=stroke, sw=1, rx=6))
      for j, ln in enumerate(lines):
        body.append(text(x + 22, yy + 17 + j * 15, ln, size=11.5))
      yy += hh + 6
    if yy > top + h - 8:
      raise FigureError(f"{b['id']}: weaknesses overflow the card")
  body.append(text(W - 40, ay + 26, "Collision", size=12.5, weight=700, fill=RED, anchor="end"))
  y = top + h + 24
  body.append(rect(40, y, W - 80, 44, fill=AMBER_BG, stroke=AMBER, sw=1, rx=8))
  body.append(text(56, y + 27, "Common cause: the forward collision warning (layer 2) uses the same perception that missed "
                   "the vehicle (layer 1), so both fail together.", size=12))
  legend = [(RED_BG, RED, "weakness: a hole in the layer"), (GREEN_BG, GREEN, "what holds on our reference car")]
  y += 70
  lx = 40
  for fill, stroke, label in legend:
    body.append(rect(lx, y - 10, 14, 12, fill=fill, stroke=stroke, rx=3))
    body.append(text(lx + 20, y, label, size=11, fill=MUTED))
    lx += 40 + text_w(label, 11)
  body, y = footer(body, y + 26, "From RCA §3 (barrier analysis) and §4 (fault tree). A weakness is in our inherited "
                   "baseline; whether it acted in a given crash is not known.")
  desc = ("Three protection layers, each with a hole the hazard passes through: " +
          "; ".join(f"{b['id']} {b['name']}, meant to {b['function'].lower()}: " +
                    ", ".join(lbl for lbl, _ in b["holes"]) for b in bs) + ". Common cause: " + COMMON + ".")
  return svg(W, int(y), "Figure 3-1 · Three barriers, all of them failed", desc, body)


# ---------------------------------------------------------------- Figure 3-2: stopping distance

def distances() -> list[tuple[int, int, int, float]]:
  head, rows = table(section(RCA.read_text(encoding="utf-8"), "### 3.1"), "Ego speed")
  cs = col(head, "Ego speed")
  cc, cf = col(head, "Distance at -3.5 m/s² (openpilot cap)"), col(head, "Distance at -8 m/s² (≈ full braking)")
  ct = col(head, "Time to impact at constant speed from the -3.5 distance")
  out = []
  for r in rows:
    m = [re.fullmatch(p, plain(c)) for p, c in ((r"(\d+) km/h \(\d+ m/s\)", r[cs]), (r"(\d+) m", r[cc]),
                                                 (r"(\d+) m", r[cf]), (r"([\d.]+) s", r[ct]))]
    if not all(m):
      raise FigureError(f"distance row does not parse: {r}")
    out.append((int(m[0].group(1)), int(m[1].group(1)), int(m[2].group(1)), float(m[3].group(1))))
  if len(out) < 2:
    raise FigureError("fewer than two speeds in RCA §3.1")
  return out


RANGE = "140–190 m"                # RCA §3.1 implication: the confirmation range openpilot alone needs at highway speed


def fig_distance() -> str:
  rows = distances()
  if f"**≥ {RANGE}**" not in RCA.read_text(encoding="utf-8"):
    raise FigureError(f"the implication {RANGE!r} is no longer in RCA §3.1")
  body = header(W, "3-2", "The distance openpilot needs to stop",
                "From the moment the stopped vehicle is confirmed, at openpilot's braking cap and at full braking.", REF)
  lx, rx, top = 130, W - 250, 124
  top_m = 50 * ((max(r[1] for r in rows) + 49) // 50)
  sx = lambda m: lx + (rx - lx) * m / top_m
  bh, step = 18, 66
  y_end = top + step * len(rows)
  for m in range(0, top_m + 1, 50):
    body.append(line(sx(m), top - 12, sx(m), y_end - 14, stroke=HAIR, sw=1))
    body.append(text(sx(m), y_end + 4, f"{m} m", size=11, fill=MUTED, anchor="middle"))
  for i, (kmh, cap, full, tti) in enumerate(rows):
    y = top + i * step
    body.append(text(lx - 14, y + bh + 4, f"{kmh} km/h", size=13, weight=700, anchor="end"))
    body.append(rect(lx, y, sx(cap) - lx, bh, fill=RED, stroke="none", rx=3))
    body.append(text(sx(cap) + 8, y + 13, f"{cap} m · {tti:g} s at constant speed", size=11.5, weight=700, fill=RED))
    body.append(rect(lx, y + bh + 4, sx(full) - lx, bh, fill=LINE, stroke="none", rx=3))
    body.append(text(sx(full) + 8, y + bh + 17, f"{full} m", size=11.5, fill=MUTED))
  y = y_end + 36
  for fill, label in ((RED, "at the openpilot cap, -3.5 m/s²"), (LINE, "at about full braking, -8 m/s²")):
    body.append(rect(40 if fill == RED else 330, y - 10, 14, 12, fill=fill, stroke="none", rx=3))
    body.append(text((40 if fill == RED else 330) + 20, y, label, size=11, fill=MUTED))
  y += 30
  for ln in wrap(f"At highway speed openpilot alone avoids a stopped vehicle only if it has confirmed it {RANGE} "
                 "ahead, about twice the distance full braking needs. Anything seen later needs the driver or stock "
                 "emergency braking.", W - 80, 13):
    body.append(text(40, y, ln, size=13, weight=600))
    y += 19
  body, y = footer(body, y + 10, "Idealized, as in RCA §3.1: 0.5 s latency, constant deceleration once reached, jerk "
                   "ignored; real distances are longer. Computed, not measured.")
  desc = ("Stopping distance from confirmation, at the openpilot cap and at full braking: " +
          "; ".join(f"{k} km/h: {c} m against {f} m" for k, c, f, _ in rows) + ".")
  return svg(W, int(y), "Figure 3-2 · The distance openpilot needs to stop", desc, body)


OUTPUTS = {"fig-fi001-2-1-crash-pattern.svg": fig_scenes, "fig-fi001-3-1-barriers.svg": fig_barriers,
           "fig-fi001-3-2-stopping-distance.svg": fig_distance}


def build() -> dict[str, str]:
  return {name: f() for name, f in OUTPUTS.items()}


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
