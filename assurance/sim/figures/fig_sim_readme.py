#!/usr/bin/env python3
"""Draw the figures of the simulation track's method page (`../README.md`) and its hero strip.

Every figure restates the page's own text in a picture, at phone width (640 px wide, 13–16 px text):

  fig-sim-r1-overview.svg   §1  the four layers, what feeds what, and where the Blender scenes sit
  fig-sim-r2-layers.svg     §2  what each layer can and cannot show
  fig-sim-r3-loop.svg       §3.1 the layer-1 loop: real code, models and assumptions, and where faults go in
  fig-sim-r4-column.svg     §3.5 the L2 steering column and the driver-override path
  fig-sim-r5-credit.svg     §4  the evidence gate and where results are handed back
  fig-sim-r6-deps.svg       §5  packages by use, coloured by licence
  fig-sim-r7-open.svg       §6  open items by what closes them

Each figure lists the README texts it was drawn from (`SRC`); `--check` fails when one of them no longer appears in
the README (whitespace-normalised), when the §6 open items and Figure r7 differ, or when a committed SVG is stale.
The hero strip (`sim-hero-dashboards.jpg`) crops the 3D view out of three committed Blender dashboards; it needs
Pillow to rebuild, so `--check` only requires that it and its sources exist and that it stays under 300 KB.

    python3 fig_sim_readme.py            # regenerate the SVGs (and the hero strip if Pillow is installed)
    python3 fig_sim_readme.py --check    # fail if a source text changed or an SVG is stale

Standard library only for the SVGs. Output is deterministic.
"""

from __future__ import annotations

import re
import struct
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
README = SIM / "README.md"
W = 640

# ---------------------------------------------------------------- style (tokens of the sim figures, with dark variant)

STYLE = """<style>
svg { --bg:#ffffff; --ink:#0b0b0b; --ink2:#52514e; --ink3:#8a8984; --grid:#e3e2de; --card:#f7f7f5;
      --real:#2a78d6; --real-bg:#e9f1fb; --amb:#c98500; --amb-bg:#fdf4dc; --bad:#e34948; --bad-bg:#fdecec;
      --pic:#6250d6; --pic-bg:#efedfb; --flt:#eb6834; --cop:#eb6834; --cop-bg:#fde9df; }
@media (prefers-color-scheme: dark) {
  svg { --bg:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --ink3:#8d8c85; --grid:#33322f; --card:#232321;
        --real:#3987e5; --real-bg:#16273c; --amb:#eda100; --amb-bg:#3a2f12; --bad:#e66767; --bad-bg:#3d1e1e;
        --pic:#9085e9; --pic-bg:#26223f; --flt:#d95926; --cop:#d95926; --cop-bg:#3f2417; }
}
.bg { fill:var(--bg); }
.h { font:600 21px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.t { font:15px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.tb { font:600 15px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.tl { font:600 17px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.t2 { font:13px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink2); }
.t2b { font:600 13px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink2); }
.chip { font:600 12px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:#ffffff; }
.tbad { font:600 13px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--bad); }
.hair { stroke:var(--grid); stroke-width:1; }
.card { fill:var(--card); stroke:var(--grid); stroke-width:1.2; }
.real { fill:var(--real-bg); stroke:var(--real); stroke-width:2.4; }
.model { fill:var(--card); stroke:var(--ink3); stroke-width:1.4; }
.amb { fill:var(--amb-bg); stroke:var(--amb); stroke-width:1.6; stroke-dasharray:6 4; }
.plan { fill:var(--bg); stroke:var(--ink3); stroke-width:1.4; stroke-dasharray:6 4; }
.pic { fill:var(--pic-bg); stroke:var(--pic); stroke-width:1.4; }
.picbox { fill:var(--bg); stroke:var(--pic); stroke-width:1.2; }
.badbox { fill:var(--bad-bg); stroke:var(--bad); stroke-width:1.4; }
.copbox { fill:var(--cop-bg); stroke:var(--cop); stroke-width:1.4; }
.f-real { fill:var(--real); } .f-model { fill:var(--ink3); } .f-amb { fill:var(--amb); } .f-bad { fill:var(--bad); }
.f-pic { fill:var(--pic); } .f-flt { fill:var(--flt); } .f-cop { fill:var(--cop); } .f-ink2 { fill:var(--ink2); }
.arr { stroke:var(--ink2); stroke-width:1.6; fill:none; }
.arrd { stroke:var(--ink3); stroke-width:1.6; fill:none; stroke-dasharray:5 4; }
.arrb { stroke:var(--bad); stroke-width:1.6; fill:none; stroke-dasharray:5 4; }
.spring { stroke:var(--ink2); stroke-width:1.8; fill:none; stroke-linejoin:round; }
.strike { stroke:var(--bad); stroke-width:1.6; }
</style>"""

MARKERS = ('<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
           'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="f-ink2"/></marker>'
           '<marker id="ab" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
           'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="f-bad"/></marker>')

# approximate advance per character as a share of the font size (system sans)
CHAR = {"t": 0.53, "tb": 0.6, "tl": 0.58, "t2": 0.53, "t2b": 0.56, "chip": 0.58, "tbad": 0.56, "h": 0.56}
SIZE = {"t": 15, "tb": 15, "tl": 17, "t2": 13, "t2b": 13, "chip": 12, "tbad": 13, "h": 21}


def fmt(v: float) -> str:
  return f"{v:.1f}".rstrip("0").rstrip(".")


def el(tag: str, content: str | None = None, **attrs) -> str:
  a = "".join(f' {k.rstrip("_").replace("_", "-")}="{v}"' for k, v in attrs.items() if v not in ("", None))
  return f"<{tag}{a}/>" if content is None else f"<{tag}{a}>{escape(content)}</{tag}>"


def T(x, y, s, cls="t", anchor="", rotate=None) -> str:
  tr = f"rotate({rotate} {fmt(x)} {fmt(y)})" if rotate is not None else ""
  return el("text", s, x=fmt(x), y=fmt(y), class_=cls, text_anchor=anchor, transform=tr)


def R(x, y, w, h, cls="card", rx=8) -> str:
  return el("rect", None, x=fmt(x), y=fmt(y), width=fmt(w), height=fmt(h), rx=rx, class_=cls)


def P(d, cls="arr", end="a", start="") -> str:
  return el("path", None, d=d, class_=cls, marker_end=f"url(#{end})" if end else "",
            marker_start=f"url(#{start})" if start else "")


def width(s: str, cls="t") -> float:
  return len(s) * CHAR[cls] * SIZE[cls]


def wrap(s: str, w: float, cls="t") -> list[str]:
  out, cur = [], ""
  for word in s.split():
    nxt = f"{cur} {word}".strip()
    if cur and width(nxt, cls) > w:
      out.append(cur)
      cur = word
    else:
      cur = nxt
  return out + ([cur] if cur else [])


def para(x, y, s, w, cls="t", lh=None, anchor="") -> tuple[list[str], float]:
  """Wrapped text; y is the first baseline. Returns the elements and the baseline after the last line."""
  lh = lh or round(SIZE[cls] * 1.35)
  lines = wrap(s, w, cls)
  return [T(x, y + i * lh, ln, cls, anchor) for i, ln in enumerate(lines)], y + len(lines) * lh


def chip(x, y, s, fill="f-real", right=False) -> tuple[list[str], float]:
  """A status chip of height 20; x is its left edge (right edge if right=True), y its top."""
  w = width(s, "chip") + 16
  x0 = x - w if right else x
  return [R(x0, y, w, 20, fill, rx=10), T(x0 + w / 2, y + 14, s, "chip", "middle")], w


def svg(h: int, title: str, desc: str, body: list[str]) -> str:
  head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" '
          'aria-labelledby="t d">')
  return "\n".join([head, el("title", title, id="t"), el("desc", desc, id="d"), STYLE, f"<defs>{MARKERS}</defs>",
                    f'<rect class="bg" width="{W}" height="{h}"/>', *body, "</svg>"]) + "\n"


def header(title: str, sub: str) -> list[str]:
  return [T(24, 34, title, "h"), T(24, 56, sub, "t2"),
          T(24, 76, "Synthetic (DSR-12) · no evidence credit · generated by fig_sim_readme.py", "tbad"),
          el("line", None, x1=24, y1=90, x2=W - 24, y2=90, class_="hair")]


def legend(y, entries: list[tuple[str, str]]) -> tuple[list[str], float]:
  """entries: (rect class, label), laid out left to right and wrapped at the figure width. Returns the last row's y."""
  out, x = [], 24
  for cls, label in entries:
    w = 26 + width(label, "t2") + 18
    if x + w > W - 16:
      x, y = 24, y + 24
    out += [R(x, y - 11, 18, 14, cls, rx=3), T(x + 24, y, label, "t2")]
    x += w
  return out, y


# ---------------------------------------------------------------- source texts (each figure's facts, from the README)

SRC: dict[str, list[str]] = {}


def norm(s: str) -> str:
  return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------- r1 overview

SRC["fig-sim-r1-overview.svg"] = [
  "fault-injection plant model (layer 1), known scenarios as OpenSCENARIO (layer 2), MetaDrive closed loop (layer 3), unknown-scenario search (layer 4)",
  "Fault catalog: each fault with its FMEA causes, TSRs",
  "What the **real panda safety code** of the reference build does with each injected fault",
  "Built for 10 of the 27 WP-V-03 scenarios",
  "replays headless",
  "esmini plays the scenario with its own simple controllers",
  "Planned (backlog item 3)",
  "The full openpilot stack driving on rendered images",
  "Prototype over the plant model: seeded Monte Carlo and cross-entropy falsification",
  "Reachability bound (exact, numpy)",
  "the motion of a layer-1 plant run, or a kinematic motion where the plant cannot represent the situation",
  "`scene.json`",
  "rendered in Blender",
  "a review dashboard and, for some, a clip",
  "one scene per HARA hazardous event and SOTIF hazard",
  "Until then the results only rank risks and guide which tests to run on the bench and the car.",
  "Timing results go to the safety-concept session",
  "Scenario results go to the SOTIF session for WP-V-03/04",
  "no family has an approved fidelity case yet",
]


def fig_overview() -> str:
  b = header("Simulation track at a glance", "Four layers, what feeds what, and where the Blender scenes sit")
  L, Rx, cw = 24, 332, 284

  def layer(x, y, h, cls, num, name, status, chip_cls, lines):
    out = [R(x, y, cw, h, cls)]
    c, _ = chip(x + cw - 10, y + 10, status, chip_cls, right=True)
    out += c + [T(x + 14, y + 26, num, "t2b"), T(x + 14, y + 48, name, "tl")]
    yy = y + 72
    for ln in lines:
      p, yy = para(x + 14, yy, ln, cw - 28, "t")
      out += p
    return out

  # inputs
  b += [R(L, 106, cw, 56, "card"), T(L + 14, 129, "faults.yaml", "tb"), T(L + 14, 149, "fault catalog: FMEA causes, TSRs", "t2"),
        R(Rx, 106, cw, 56, "card"), T(Rx + 14, 129, "WP-V-03", "tb"), T(Rx + 14, 149, "known scenarios (26)", "t2")]
  b += [P(f"M{L + cw / 2},162 V186"), P(f"M{Rx + cw / 2},162 V186")]
  # layer 1 and 2
  b += layer(L, 190, 140, "real", "LAYER 1", "Plant model", "Built", "f-real",
             ["real panda safety code", "+ Corolla single-track plant", "EPS, PCM, driver: assumed"])
  b += layer(Rx, 190, 140, "card", "LAYER 2", "Known scenarios", "Built · 10 of 27", "f-model",
             ["OpenSCENARIO + OpenDRIVE", "replayed headless in esmini", "(its own simple drivers)"])
  # layer 4 and 3
  b += [P(f"M{L + cw / 2},330 V370"), P(f"M{Rx + cw / 2},330 V370", "arrd")]
  b += [T(Rx + cw / 2 + 8, 356, "scenarios", "t2")]
  b += layer(L, 374, 118, "card", "LAYER 4", "Failure search", "Prototype", "f-amb",
             ["Monte Carlo + cross-entropy", "+ reachability bound (§3.6)"])
  b += layer(Rx, 374, 118, "plan", "LAYER 3", "MetaDrive closed loop", "Planned", "f-model",
             ["full openpilot stack on", "rendered images, panda code"])
  b += [P(f"M{L + cw},300 C{L + cw + 24},300 {Rx - 24},400 {Rx},404", "arrd")]
  # Blender lane
  by = 532
  b += [R(L, by, W - 48, 160, "pic"), T(L + 14, by + 26, "Review pictures (Blender)", "tl"),
        T(W - 38, by + 26, "pictures only", "t2b", "end")]
  steps = [("plant run", "or kinematic"), ("scene.json", "poses, events"), ("Blender", "render"), ("dashboard", "+ clip")]
  sw, gap, sx = 118, 26, L + 14
  for i, (a, c) in enumerate(steps):
    x = sx + i * (sw + gap)
    b += [R(x, by + 46, sw, 64, "picbox"), T(x + sw / 2, by + 74, a, "tb", "middle"), T(x + sw / 2, by + 96, c, "t2", "middle")]
    if i:
      b += [P(f"M{x - gap + 2},{by + 78} H{x - 2}")]
  p, _ = para(L + 14, by + 138, "One scene per HARA hazardous event and SOTIF hazard. Gallery: blender/dashboards.",
              W - 76, "t2")
  b += p
  b += [P(f"M{L},260 H12 V{by + 78} H{sx - 2}")]
  # outputs
  oy = by + 184
  b += [R(L, oy, W - 48, 116, "badbox"), T(L + 14, oy + 26, "What results are for today", "tl")]
  yy = oy + 50
  for s in ["Rank risks; choose bench and car tests.",
            "Timing → safety-concept session. Scenarios → SOTIF session.",
            "Evidence only after an approved fidelity case: none yet."]:
    p, yy = para(L + 14, yy, s, W - 76, "t")
    b += p
  h = oy + 116 + 24
  return svg(h, "Simulation track at a glance: four layers and the Blender scenes",
             "Synthetic (DSR-12), no evidence credit. Inputs faults.yaml and WP-V-03 feed layer 1 (plant model with the "
             "real panda safety code, built) and layer 2 (known scenarios as OpenSCENARIO, 10 of 27 built). Layer 1 feeds "
             "layer 4 (failure search and reachability bound, prototype); layer 2 and the panda code feed layer 3 "
             "(MetaDrive closed loop, planned). Plant runs or kinematic motions become scene.json, are rendered in "
             "Blender and composed into review dashboards and clips. Results rank risks and guide tests; no evidence "
             "until an approved fidelity case.", b)


# ---------------------------------------------------------------- r2 layers

LAYERS = [
  ("LAYER 1", "Fault-injection plant model", "Built", "f-real", "real",
   ["What the real panda code does with each injected fault, frame by frame",
    "How far the car moves meanwhile, under stated assumptions",
    "Which assumptions decide the outcome"],
   ["The real EPS, PCM and driver: they are assumptions",
    "openpilot itself: no SoC alerts, model or planner faults",
    "MCU latency, bus load, tyre limits"]),
  ("LAYER 2", "Known scenarios as data", "Built · 10 of 27", "f-model", "card",
   ["Each representable WP-V-03 scenario, written down unambiguously",
    "It parses and replays headless; same road and traffic as layers 1 and 3"],
   ["Any behaviour of the item: esmini drives with its own simple controllers"]),
  ("LAYER 3", "MetaDrive closed loop", "Planned", "f-model", "plan",
   ["Full openpilot stack on rendered images, panda code in the loop",
    "Lateral and longitudinal behaviour, alert timing, outcome class"],
   ["Camera realism, sensor faults, the real EPS and PCM",
    "Credit only per scenario family after a fidelity case"]),
  ("LAYER 4", "Unknown-scenario search", "Prototype", "f-amb", "card",
   ["Parameter regions where the item fails, to direct closed-course tests"],
   ["That no other failure exists",
    "A failure rate in the real ODD"]),
]
SRC["fig-sim-r2-layers.svg"] = [
  "What the **real panda safety code** of the reference build does with each injected fault, frame by frame",
  "How far the car moves meanwhile under stated EPS, PCM and driver assumptions",
  "Which assumptions decide the outcome",
  "Anything the assumptions decide: the EPS reaction to lost frames, the torque-to-lateral-acceleration gain, the driver",
  "no SoC alert, no model or planner fault",
  "Interrupt latency and bus load on the real MCU. Tyre limits",
  "Built for 10 of the 27 WP-V-03 scenarios",
  "is written down unambiguously, parses and replays headless; the same road and traffic used by layers 1 and 3",
  "Any behaviour of the item: esmini plays the scenario with its own simple controllers",
  "Planned (backlog item 3)",
  "The full openpilot stack driving on rendered images, with the Corolla CarParams and the panda safety code in the loop",
  "lateral and longitudinal behaviour, alert timing, outcome class",
  "Camera realism, sensor faults, the real EPS and PCM; credit only per scenario family after the WP-V-02 §5.3 fidelity case",
  "Prototype over the plant model",
  "Parameter regions of layer 2/3 scenarios where the item fails, to direct closed-course tests",
  "That no other failure exists; a rate of failure in the real ODD",
]


def fig_layers() -> str:
  b = header("What each layer can and cannot show", "Short form of the §2 table; the table has the full wording")
  y = 106
  colw = (W - 48 - 28 - 16) / 2
  for num, name, status, chip_cls, cls, can, cannot in LAYERS:
    body, ya, yb = [], y + 98, y + 98
    for s in can:
      body.append(T(24 + 14, ya, "✓", "tb"))
      p, ya = para(24 + 14 + 18, ya, s, colw - 18, "t")
      body += p
      ya += 6
    xb = 24 + 14 + colw + 16
    for s in cannot:
      body.append(T(xb, yb, "✗", "tbad"))
      p, yb = para(xb + 18, yb, s, colw - 18, "t")
      body += p
      yb += 6
    h = max(ya, yb) - y + 4
    b += [R(24, y, W - 48, h, cls)]
    c, _ = chip(W - 34, y + 12, status, chip_cls, right=True)
    b += c + [T(38, y + 28, num, "t2b"), T(38, y + 50, name, "tl"),
              T(38, y + 72, "CAN SHOW", "t2b"), T(xb, y + 72, "CANNOT SHOW", "t2b")]
    b += body
    y += h + 14
  b += legend(y + 16, [("real", "built, real code in it"), ("card", "built"), ("plan", "planned")])[0]
  return svg(int(y + 40), "What each simulation layer can and cannot show",
             "Synthetic (DSR-12), no evidence credit. Four cards, one per layer, with its status and what it can and "
             "cannot show: layer 1 plant model (built), layer 2 known scenarios (built for 10 of 27), layer 3 MetaDrive "
             "closed loop (planned), layer 4 unknown-scenario search (prototype).", b)


# ---------------------------------------------------------------- r3 loop

SRC["fig-sim-r3-loop.svg"] = [
  "SoC stand-in ── STEERING_LKA 100 Hz, ACC_CONTROL 33 Hz, heartbeat 10 Hz ──▶ panda safety code (real)",
  "Perfect-perception lane keeping and speed holding",
  "Not openpilot: no SoC alerts",
  "opendbc `toyotacan.create_steer_command` and `create_accel_command`",
  "opendbc `libsafety` compiled with `LIONDRIVER_REFERENCE`, Toyota mode",
  "every RX and TX frame goes through its hooks",
  "`heartbeat_siren.h`, `eps_fault_siren.h`, `hw_watchdog.h` compiled unchanged",
  "Counts down at f_LSI / (4 · 2^PR)",
  "pass-through whenever the MCU does not drive them",
  "release after 30 ms, or hold 2 s",
  "request taken as 0 after 100 ms without a frame",
  "CommonRoad single-track model (`commonroad-vehicle-models` 3.0.2, `vehicle_dynamics_st`), RK4 at 5 ms",
  "Reacts 1.5 s (WP-S-04 §3.2 upper value) after the first cue: the panda siren, a 0.2 m drift or a 1 m/s² change of acceleration; corrects with up to 4 m/s²",
  "car bus RX at the nominal rates (0xAA, 0x260, 0x262, 0x1D2, 0x1D3, 0x226) ──▶ panda RX hook",
  "over-limit torque and rate (F-01a, F-01b), torque while not engaged (F-02), frozen command (F-03), SoC heartbeat loss and SoC stall (F-04a, F-04b), MCU hang until the IWDG reset (F-05), harness switch stuck in pass-through or intercept (F-06a, F-06b), EPS fault (F-07), RX loss (F-08), the longitudinal equivalents for SG-03/SG-04 (L-01…L-04)",
]


def fig_loop() -> str:
  b = header("Layer 1 loop: the real panda code in the loop", "What is real code, what is a model, what is assumed")
  x0, nw = 96, 448  # node column
  xr = x0 + nw

  def node(y, h, cls, name, kind, lines=(), flt=None):
    out = [R(x0, y, nw, h, cls), T(x0 + 14, y + 24, name, "tl"), T(x0 + 14, y + 44, kind, "t2b")]
    yy = y + 66
    for ln in lines:
      p, yy = para(x0 + 14, yy, ln, nw - 28, "t", lh=20)
      out += p
    if flt:
      c, _ = chip(xr - 10, y + 10, flt, "f-flt", right=True)
      out += c
    return out

  b += node(106, 92, "model", "SoC stand-in", "MODEL · not openpilot",
            ["perfect-perception lane keeping, speed holding"], "F-01…F-04 · L-01…L-04")
  b += [P(f"M{W / 2},198 V236"), T(W / 2 + 8, 222, "LKA 100 Hz · ACC 33 Hz · heartbeat 10 Hz", "t2")]
  b += node(240, 72, "real", "Host frames", "REAL CODE · opendbc toyotacan")
  b += [P(f"M{W / 2},312 V340")]
  b += node(344, 134, "real", "Panda safety code", "REAL CODE · reference build",
            ["TX hook passes or blocks every frame", "100 Hz task: heartbeat, sirens, watchdog",
             "IWDG: a model of the peripheral"], "F-05 hang")
  b += [P(f"M{W / 2},478 V506"), T(W / 2 + 8, 497, "frames the TX hook allows", "t2")]
  b += node(510, 76, "model", "Harness switch", "MODEL", ["pass-through when the MCU does not drive it"], "F-06")
  b += [P(f"M{W / 2},586 V600 H{x0 + 108} V614"), P(f"M{W / 2},600 H{xr - 108} V614")]
  half = (nw - 16) / 2
  for i, (name, sub, lines, flt) in enumerate([
      ("EPS", "ASSUMED", ["lag; lost frames:", "release 30 ms or hold 2 s"], "F-07"),
      ("PCM", "ASSUMED", ["lag; request 0", "after 100 ms"], None)]):
    x = x0 + i * (half + 16)
    b += [R(x, 618, half, 104, "amb"), T(x + 14, 642, name, "tl"), T(x + 14, 662, sub, "t2b")]
    b += [T(x + 14, 686 + j * 20, ln, "t") for j, ln in enumerate(lines)]
    if flt:
      c, _ = chip(x + half - 10, 628, flt, "f-flt", right=True)
      b += c
  b += [P(f"M{x0 + 108},722 V750"), P(f"M{xr - 108},722 V750")]
  b += node(754, 72, "model", "Vehicle", "MODEL · CommonRoad single-track Corolla, RK4 5 ms")
  b += [R(x0 + 60, 868, nw - 120, 76, "amb"), T(x0 + 74, 892, "Driver", "tl"), T(x0 + 74, 912, "ASSUMED", "t2b"),
        T(x0 + 74, 934, "reacts 1.5 s after the first cue", "t")]
  b += [P(f"M{x0 + 150},826 V864"), P(f"M{xr - 150},868 V830"),
        T(x0 + 142, 852, "cue: siren, drift", "t2", "end"), T(xr - 142, 852, "correction ≤ 4 m/s²", "t2")]
  # return paths
  b += [P(f"M{x0},790 H52 V150 H{x0 - 2}"), T(44, 470, "perfect perception", "t2", "middle", rotate=-90)]
  b += [P(f"M{xr},790 H588 V410 H{xr + 2}"), T(600, 600, "car bus RX → panda RX hook", "t2", "middle", rotate=90)]
  c, _ = chip(566, 436, "F-08", "f-flt")
  b += c
  b += legend(980, [("real", "real code"), ("model", "model"), ("amb", "assumption"), ("f-flt", "fault injected")])[0]
  return svg(1004, "Layer 1 fault-injection loop with the real panda safety code in the loop",
             "Synthetic (DSR-12), no evidence credit. A perfect-perception SoC stand-in (model) sends LKA, ACC and "
             "heartbeat frames built by the real opendbc host code to the real panda safety code (reference build, TX "
             "hook, 100 Hz task, IWDG model). Frames it allows pass the harness switch (model) to the EPS and PCM "
             "(assumptions), which move the CommonRoad single-track Corolla (model). Perfect perception feeds back to "
             "the SoC, car-bus RX frames back to the panda; the driver (assumption) reacts 1.5 s after a cue. Fault "
             "injection points: F-01 to F-04 and L- at the SoC, F-05 panda hang, F-06 switch, F-07 EPS, F-08 RX.", b)


# ---------------------------------------------------------------- r4 column

SRC["fig-sim-r4-column.svg"] = [
  "the steering wheel inertia (driver torque in), the torsion bar (its torque is what the EPS reports as STEER_TORQUE_DRIVER), and the lower column, motor and rack as one inertia held by a rack stiffness",
  "The motor follows the LKA command through the same lag as L1, up to a torque limit",
  "LKA is dropped when |STEER_TORQUE_DRIVER| reaches `MAX_USER_TORQUE` (500 units)",
  "The panda does not act on driver torque on the LKA path (TSR-304 not implemented, GAP-02)",
  "what 1500 LKA units and 500 driver-torque units are in N·m",
  "the host drops LKA within 0.2 s of the driver's input only where the driver's torque passes the host threshold quickly",
  "where the driver's peak stays below the threshold, LKA is never dropped and keeps steering against the driver",
  "after the drop, the motor torque falls below 5 % after a further ≈ 0.36 s",
  "both scales are measurement items (SIM-OI-8)",
]


def spring(x1, x2, y, n=6, a=9) -> str:
  step = (x2 - x1 - 16) / (2 * n)
  d = f"M{fmt(x1)},{y} H{fmt(x1 + 8)}"
  for i in range(2 * n):
    d += f" L{fmt(x1 + 8 + step * (i + 0.5))},{y + (a if i % 2 == 0 else -a)}"
  return el("path", None, d=d + f" L{fmt(x2 - 8)},{y} H{fmt(x2)}", class_="spring")


def fig_column() -> str:
  b = header("L2 steering column and the driver override", "§3.5: who can stop LKA steering against the driver")
  y = 170
  b += [T(24, 114, "COLUMN (Modelica FMU, every parameter assumed)", "t2b")]
  b += [P(f"M24,{y} H86"), T(24, y - 12, "driver", "t2"), T(24, y + 26, "torque", "t2")]
  b += [R(90, y - 30, 120, 60, "model"), T(150, y - 4, "steering", "tb", "middle"), T(150, y + 16, "wheel", "tb", "middle")]
  b += [spring(210, 300, y), T(255, y - 18, "torsion bar", "t2", "middle")]
  b += [R(300, y - 30, 170, 60, "model"), T(385, y - 4, "column, motor", "tb", "middle"),
        T(385, y + 16, "and rack", "tb", "middle")]
  b += [spring(470, 570, y), T(520, y - 18, "rack stiffness", "t2", "middle")]
  b += [el("line", None, x1=574, y1=y - 26, x2=574, y2=y + 26, class_="arr")]
  b += [el("path", None, d="".join(f"M574,{y - 24 + 10 * i} l10,-8 " for i in range(6)), class_="hair")]
  # torsion bar torque out, LKA command in
  b += [P(f"M255,{y + 10} V268"), T(247, 232, "torsion-bar torque =", "t2", "end"),
        T(247, 250, "STEER_TORQUE_DRIVER", "t2b", "end")]
  b += [R(360, 254, 256, 92, "amb"), T(374, 278, "LKA command → lag → limit", "tb"),
        T(374, 300, "same lag as L1, up to a", "t"), T(374, 320, "torque limit", "t")]
  b += [P(f"M474,254 V{y + 34}"), T(482, 232, "motor", "t2")]
  # host rule
  b += [R(24, 270, 290, 120, "real"), T(38, 294, "Host (Toyota car controller)", "tb"),
        T(38, 316, "drops LKA when", "t"), T(38, 336, "|STEER_TORQUE_DRIVER|", "t"),
        T(38, 356, "reaches MAX_USER_TORQUE (500)", "t"), T(38, 376, "the only override path", "t2b")]
  b += [P(f"M314,310 H{360 - 2}"), T(337, 302, "drop", "t2", "middle")]
  b += [R(24, 404, W - 48, 68, "badbox"), T(38, 428, "Panda: does not act on driver torque on the LKA path", "tb"),
        T(38, 452, "TSR-304 not implemented (GAP-02)", "t")]
  # results
  b += [T(24, 504, "UNDER THESE ASSUMPTIONS (swept)", "t2b")]
  yy = 530
  for mark, cls, s in [("✓", "tb", "Strong, fast driver: the host drops LKA within 0.2 s."),
                       ("✗", "tbad", "Driver below the threshold: LKA is never dropped and keeps steering against "
                                     "the driver."),
                       ("•", "tb", "After the drop: motor torque under 5 % about 0.36 s later.")]:
    p, y2 = para(48, yy, s, W - 72, "t", lh=20)
    b += [T(26, yy, mark, cls)] + p
    yy = y2 + 8
  b += [R(24, yy + 4, W - 48, 70, "amb"), T(38, yy + 28, "Unknown: two scales in N·m", "tb")]
  p, _ = para(38, yy + 50, "1500 LKA units and 500 driver-torque units; to be measured (M-08, SIM-OI-8).", W - 76, "t")
  b += p
  return svg(int(yy + 96), "L2 steering column and the driver-override path (SG-05)",
             "Synthetic (DSR-12), no evidence credit. Driver torque on the steering wheel inertia, a torsion bar whose "
             "torque is STEER_TORQUE_DRIVER, the column, motor and rack as one inertia held by a rack stiffness; the "
             "motor follows the LKA command through a lag up to a torque limit. The host drops LKA when "
             "|STEER_TORQUE_DRIVER| reaches MAX_USER_TORQUE (500); the panda does not act on driver torque (GAP-02). "
             "Under the swept assumptions a strong fast driver gets LKA dropped within 0.2 s, a driver below the "
             "threshold never does, and the motor torque falls below 5 % about 0.36 s after the drop. The two N·m "
             "scales are unknown (M-08).", b)


# ---------------------------------------------------------------- r5 credit

SRC["fig-sim-r5-credit.svg"] = [
  "No result of this track is evidence until the model is validated against Corolla logs",
  "system identification of EPS lag, steer ratio and tyre stiffness, and the WP-V-02 §5.3 fidelity case",
  "Simulation earns credit only once the WP-V-02 §5.3 fidelity case is approved for the scenario family",
  "DQ-139, option A",
  "no family has an approved fidelity case yet",
  "Every output is labelled synthetic data under DSR-12 and is kept apart from real-world data",
  "Timing results go to the safety-concept session, which decides what enters WP-S-04",
  "Scenario results go to the SOTIF session for WP-V-03/04",
  "The simulation track does not edit those documents",
  "allow `measured | code_derived | unknown` timing only",
  "only if the System FMEA session accepts a proposal to add a category",
]


def fig_credit() -> str:
  b = header("When a simulation result counts", "§4: the evidence gate, and where results are handed back")
  cx = W / 2
  b += [R(150, 106, 340, 50, "card"), T(cx, 137, "Result from layers 1–4", "tb", "middle")]
  b += [P(f"M{cx},156 V178")]
  # gate (diamond)
  b += [el("path", None, d=f"M{cx},182 L{cx + 200},242 L{cx},302 L{cx - 200},242 Z", class_="card")]
  b += [T(cx, 230, "Fidelity case approved", "tb", "middle"), T(cx, 250, "for this scenario family?", "tb", "middle"),
        T(cx, 272, "WP-V-02 §5.3 · DQ-139", "t2", "middle")]
  # needs
  b += [R(84, 318, W - 168, 54, "amb")]
  p, _ = para(98, 340, "Needs the model validated against Corolla logs: EPS lag, steer ratio, tyre stiffness (S7).",
              W - 196, "t2", lh=17)
  b += p
  # branches
  b += [P(f"M{cx - 200},242 H60 V392"), T(70, 232, "NO · every family today", "tbad")]
  b += [P(f"M{cx + 200},242 H580 V392", "arrd"), T(570, 232, "YES · none yet", "t2b", "end")]
  b += [R(24, 396, 360, 132, "badbox"), T(38, 420, "Ranks risks, guides tests", "tb")]
  yy = 444
  for s in ["Chooses the bench and car tests.", "Labelled synthetic (DSR-12), kept apart from real data."]:
    p, yy = para(38, yy, s, 332, "t", lh=20)
    b += p
  b += [R(400, 396, 216, 132, "plan"), T(414, 420, "Evidence credit", "tb")]
  p, _ = para(414, 444, "for that scenario family only", 190, "t", lh=20)
  b += p
  # hand-back
  b += [T(24, 566, "NOT SELF-CREDITED: HANDED BACK", "t2b")]
  rows = [("Timing", "safety-concept session", "decides what enters WP-S-04"),
          ("Scenario results", "SOTIF session", "WP-V-03 / WP-V-04"),
          ("Simulated times", "System FMEA session", "rating tables allow measured, code-derived or unknown only; a new "
                                                     "category needs its acceptance")]
  y = 580
  for what, who, note in rows:
    lines = wrap(note, W - 48 - 28 - 190, "t2")
    h = max(58, 32 + len(lines) * 17)
    b += [R(24, y, W - 48, h, "card"), T(38, y + 24, what, "tb"), T(38, y + 44, "→ " + who, "t")]
    b += [T(240, y + 24 + i * 17, ln, "t2") for i, ln in enumerate(lines)]
    y += h + 8
  b += [T(24, y + 18, "The track does not edit those documents.", "t2")]
  return svg(int(y + 40), "When a simulation result counts: evidence gate and hand-back",
             "Synthetic (DSR-12), no evidence credit. A result from layers 1 to 4 meets the gate: is a WP-V-02 §5.3 "
             "fidelity case approved for its scenario family (DQ-139)? It needs the model validated against Corolla "
             "logs. No, for every family today: the result ranks risks and guides bench and car tests, labelled "
             "synthetic. Yes, for none yet: evidence credit for that family only. Results are handed back: timing to "
             "the safety-concept session (WP-S-04), scenario results to the SOTIF session (WP-V-03/04), simulated times "
             "to the System FMEA session.", b)


# ---------------------------------------------------------------- r6 dependencies

PERM, MPL, AGPL, NONE = "real", "copbox", "badbox", "plan"
DEPS = [
  ("Layer 1 plant", [("commonroad-vehicle-models", "BSD-3", PERM), ("omegaconf", "BSD-3", PERM),
                     ("PyYAML", "MIT", PERM), ("cffi", "MIT-0", PERM), ("pycparser", "BSD-3", PERM),
                     ("pycapnp", "BSD-2", PERM), ("numpy", "BSD-3", PERM)]),
  ("Plant as an FMU", [("pythonfmu", "MIT", PERM), ("fmpy", "BSD-2", PERM)]),
  ("L2 column (TL-44)", [("OpenModelica", "OSMC-PL · AGPL-3 option", AGPL), ("micromamba", "BSD-3", PERM)]),
  ("Chrono pilot (TL-52)", [("Project Chrono 9.0.1", "BSD-3, built from source", PERM),
                            ("build tools (lock)", "permissive · GPL build-only", PERM)]),
  ("Layer 2 scenarios", [("scenariogeneration", "MPL-2.0", MPL), ("esmini", "MPL-2.0", MPL)]),
  ("Layer 4 search, §3.6 bound", [("numpy", "BSD-3", PERM)]),
  ("Not used", [("Scenic", "needs rv-ltl", NONE), ("VerifAI", "needs Scenic", NONE),
                ("rv-ltl 0.1.1", "no licence", AGPL)]),
]
SRC["fig-sim-r6-deps.svg"] = [
  "| commonroad-vehicle-models | 3.0.2 | BSD-3-Clause (TUM)", "| omegaconf, PyYAML | 2.4.0, 6.0.3 | BSD-3-Clause, MIT",
  "| cffi, pycparser | 2.1.1, 3.11 | MIT-0, BSD-3-Clause", "| pycapnp | 2.1.0 | BSD-2-Clause", "| numpy | 2.5.4 | BSD-3-Clause",
  "| pythonfmu | 0.7.0 | MIT", "| fmpy | 0.3.32 | BSD-2-Clause", "OSMC-PL 1.8, used under its AGPL-3 option",
  "| micromamba | 2.3.2-0", "| Project Chrono (core, Chrono::Vehicle, PyChrono) | 9.0.1",
  "the rest of the lock is open source", "| scenariogeneration | 0.16.7 | MPL-2.0", "| MPL-2.0 | replaying the scenario files headless",
  "exporting the L2 column FMU (TL-44)", "The search uses numpy instead (§3.4)",
  "Scenic 3.0.0–3.1.1 (BSD-3) requires `rv-ltl ~= 0.1`", "VerifAI 2.2 (BSD-3) requires and imports Scenic",
  "rv-ltl 0.1.1 is published on PyPI without a licence", "MPL-2.0 is a file-level copyleft",
]


def fig_deps() -> str:
  b = header("What the track runs on, by licence", "§5: packages by use; colour is the licence family")
  y = 110
  for group, pkgs in DEPS:
    b += [T(24, y + 4, group.upper(), "t2b")]
    x, yy = 24, y + 14
    for name, lic, cls in pkgs:
      w = max(width(name, "tb"), width(lic, "t2")) + 24
      if x + w > W - 24:
        x, yy = 24, yy + 56
      b += [R(x, yy, w, 48, cls, rx=6), T(x + 12, yy + 21, name, "tb"), T(x + 12, yy + 39, lic, "t2")]
      if cls == NONE or lic == "no licence":
        b += [el("line", None, x1=fmt(x + 8), y1=fmt(yy + 16), x2=fmt(x + 12 + width(name, "tb")), y2=fmt(yy + 16),
                 class_="strike")]
      x += w + 8
    y = yy + 48 + 28
  lg, y = legend(y, [(PERM, "permissive"), (MPL, "file-level copyleft (MPL-2.0)"),
                      (AGPL, "AGPL option or no licence"), (NONE, "not used")])
  b += lg
  y += 22
  p, y = para(24, y + 8, "MPL-2.0 covers changes to those files only; the track changes none. Scenic and VerifAI are "
              "out because rv-ltl has no licence.", W - 48, "t2", lh=17)
  b += p
  return svg(int(y + 14), "Simulation track dependencies by use and licence",
             "Layer 1 plant: commonroad-vehicle-models, omegaconf, PyYAML, cffi, pycparser, pycapnp, numpy, all "
             "permissive. Plant FMU: pythonfmu and fmpy, permissive. L2 column: OpenModelica under its AGPL-3 option "
             "and micromamba. Layer 2: scenariogeneration and esmini, MPL-2.0. Layer 4 and the bound: numpy. Not used: "
             "Scenic and VerifAI, because rv-ltl is published without a licence.", b)


# ---------------------------------------------------------------- r7 open items

OPEN = [
  ("Needs a measurement on the reference Corolla", "amb", [
    ("SIM-OI-1", "EPS reaction to lost LKA frames (M-02): decides most layer-1 results"),
    ("SIM-OI-7", "L2 column parameters (M-02)"),
    ("SIM-OI-8", "N·m of driver torque and LKA command (M-08): decide the SG-05 override")]),
  ("Needs another work product", "card", [
    ("SIM-OI-2", "Driver values from WP-C-08 §8; the SoC take-over alert with layer 3")]),
  ("Simulation-track work", "card", [
    ("SIM-OI-3", "LSI tolerance and the other hang types (VS-FI-17)"),
    ("SIM-OI-4", "Layer 3 end to end; the search over MetaDrive"),
    ("SIM-OI-5", "KS-04 lane split and merge")]),
  ("Outside the project", "plan", [
    ("SIM-OI-6", "Scenic and VerifAI, if rv-ltl gets a licence")]),
  ("Closed", "plan", [("SIM-OI-9", "Reachability pilot done; bound kept in numpy")]),
]
SRC["fig-sim-r7-open.svg"] = [
  "The EPS reaction to lost STEERING_LKA frames decides most layer-1 results", "Replace both cases with M-02",
  "L2 column parameters (§3.5) are assumed", "replace them with M-02 measurements",
  "on the reference Corolla (now in WP-S-04 M-08); they decide whether the host's `MAX_USER_TORQUE` rule meets SG-05",
  "Replace the driver assumptions with WP-C-08 §8 values; add the SoC take-over alert",
  "Model the LSI tolerance and the other hang types of WP-V-05 VS-FI-17", "Layer 3 end to end",
  "the search over MetaDrive", "KS-04 (lane split and merge)", "Scenic and VerifAI if rv-ltl is published with a licence",
  "**Closed 2026-10-17:** reachability pilot (§3.6) done",
]


def open_items(md: str) -> dict[str, bool]:
  """§6 table: ID -> closed."""
  sec = md.split("## 6. Open items", 1)[1]
  return {m.group(1): "**Closed" in m.group(2) for m in re.finditer(r"^\| (SIM-OI-\d+) \| (.*)\|\s*$", sec, re.M)}


def fig_open() -> str:
  b = header("Open items by what closes them", "§6: three of them need measurements on the car")
  y = 108
  for group, cls, items in OPEN:
    b += [T(24, y + 4, group.upper(), "t2b")]
    y += 14
    for oid, s in items:
      lines = wrap(s, W - 48 - 28 - 104, "t")
      h = 18 + len(lines) * 20
      b += [R(24, y, W - 48, h, cls), T(38, y + 24, oid, "tb")]
      b += [T(142, y + 24 + i * 20, ln, "t") for i, ln in enumerate(lines)]
      if group == "Closed":
        b += [el("line", None, x1=38, y1=y + 19, x2=fmt(38 + width(oid, "tb")), y2=y + 19, class_="strike")]
      y += h + 8
    y += 18
  return svg(int(y), "Simulation track open items grouped by what closes them",
             "Three open items need measurements on the reference Corolla: SIM-OI-1 EPS reaction to lost frames (M-02), "
             "SIM-OI-7 column parameters (M-02), SIM-OI-8 torque scales (M-08). SIM-OI-2 needs WP-C-08. SIM-OI-3, 4 and "
             "5 are simulation-track work. SIM-OI-6 waits on an outside licence. SIM-OI-9 is closed.", b)


FIGURES = {
  "fig-sim-r1-overview.svg": fig_overview, "fig-sim-r2-layers.svg": fig_layers, "fig-sim-r3-loop.svg": fig_loop,
  "fig-sim-r4-column.svg": fig_column, "fig-sim-r5-credit.svg": fig_credit, "fig-sim-r6-deps.svg": fig_deps,
  "fig-sim-r7-open.svg": fig_open,
}

# ---------------------------------------------------------------- hero strip (raster, Pillow)

HERO = HERE / "sim-hero-dashboards.jpg"
HERO_SOURCES = [SIM / "blender" / "dashboards" / f"{n}.jpg" for n in
                ("he-01-2-hardover-adjacent", "he-02-1-eps-loss-curve", "sh-11-pedestrian-occluded")]
HERO_CROP = (322, 55, 1232, 566)  # the 3D view of a 1600 x 900 dashboard
HERO_TILE = (600, 337)
HERO_GAP = 8
HERO_MAX_BYTES = 300_000


def hero_size() -> tuple[int, int]:
  return 3 * HERO_TILE[0] + 2 * HERO_GAP, HERO_TILE[1]


def build_hero() -> bool:
  try:
    from PIL import Image
  except ImportError:
    return False
  wh = hero_size()
  out = Image.new("RGB", wh, (26, 26, 25))
  for i, src in enumerate(HERO_SOURCES):
    with Image.open(src) as im:
      tile = im.convert("RGB").crop(HERO_CROP).resize(HERO_TILE, Image.LANCZOS)
    out.paste(tile, (i * (HERO_TILE[0] + HERO_GAP), 0))
  out.save(HERO, "JPEG", quality=78, optimize=True, progressive=True)
  return True


def jpeg_size(path: Path) -> tuple[int, int] | None:
  data = path.read_bytes()
  i = 2
  while i < len(data) - 9:
    if data[i] != 0xFF:
      return None
    marker, seg = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
    if marker in (0xC0, 0xC1, 0xC2):
      h, w = struct.unpack(">HH", data[i + 5:i + 9])
      return w, h
    i += 2 + seg
  return None


# ---------------------------------------------------------------- build and check


def build() -> dict[str, str]:
  return {name: f() for name, f in FIGURES.items()}


def problems(md: str) -> list[str]:
  out, text = [], norm(md)
  for name, srcs in SRC.items():
    out += [f"{name}: source text no longer in README.md: {s!r}" for s in srcs if norm(s) not in text]
  table = open_items(md)
  drawn = {oid: group == "Closed" for group, _c, items in OPEN for oid, _s in items}
  if table != drawn:
    out.append(f"fig-sim-r7-open.svg: §6 open items {sorted(table.items())} differ from the figure {sorted(drawn.items())}")
  for src in HERO_SOURCES:
    if not src.exists():
      out.append(f"hero strip source missing: {src.relative_to(SIM)}")
  if not HERO.exists():
    out.append(f"{HERO.name} missing; run fig_sim_readme.py with Pillow installed")
  else:
    if HERO.stat().st_size > HERO_MAX_BYTES:
      out.append(f"{HERO.name} is {HERO.stat().st_size} bytes, over {HERO_MAX_BYTES}")
    if jpeg_size(HERO) != hero_size():
      out.append(f"{HERO.name} is {jpeg_size(HERO)}, expected {hero_size()}")
  return out


def main(argv: list[str]) -> int:
  md = README.read_text(encoding="utf-8")
  out = build()
  if "--check" in argv:
    errs = problems(md)
    errs += [f"{n} is stale; run fig_sim_readme.py" for n, c in out.items()
             if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for e in errs:
      print(f"error: {e}", file=sys.stderr)
    if not errs:
      print(f"fig_sim_readme: {len(out)} figures current, sources found, hero strip present")
    return 1 if errs else 0
  for n, c in out.items():
    (HERE / n).write_text(c, encoding="utf-8")
  hero = build_hero()
  print(f"wrote {len(out)} figures" + (f" and {HERO.name}" if hero else f"; {HERO.name} not rebuilt (no Pillow)"))
  errs = problems(md)
  for e in errs:
    print(f"warning: {e}", file=sys.stderr)
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
