#!/usr/bin/env python3
"""Draw WP-H-02 Figure 3-7, the harness box intercept switch as an animated circuit (fig-h02-3-7-box-switch-anim.svg).

Left, the switch drive (HE-08): the device's 5 V drive through its output resistance into SBU1, the 240 ohm pull-down
R2/R3, and the DG419LE input, which switches when SBU1 is above its threshold VTH (a fraction of VIN). Right, the CAN
switch path of comma's harness box v3: U1 on CAN_H and U2 on CAN_L, each with its COM, NC and NO nets, the camera-side
terminations, and the device taps at J3 (bus 2 on the camera side, bus 0 on the car side). The figure loops through
four ngspice scenarios: the stock path, intercept, and the two DFMEA faults that leave the box in the wrong state.

Where each part comes from:
  CAN switch path   assurance/04-hardware/spice/box-v3-nominal.cir (box_model.py): the U1/U2 COM, NC and NO nets, the
                    terminations R6, R7, R8 with their values, and the node citations (wire-end IDs)
  switch drive      the Falstad circuit of assurance/sim/results/harness-box.json (harness_box.py), the element list
                    ngspice also runs: the drive resistance and the pull-down value
  each frame        the scenario of harness-box.json with its switch states, node voltages (SBU1, VTH, VIN) and verdict;
                    the box is in intercept when SBU1 > VTH, the rule harness_box.py applies
The build fails if a scenario, a netlist element or a Falstad element is missing, or the rule disagrees with the verdict.
The animation is CSS only; with reduced motion the intercept frame stays. Synthetic data, no evidence credit (DQ-413).

    python3 fig_h02_box_anim.py            # write the SVG
    python3 fig_h02_box_anim.py --check    # fail if the sources changed shape or the SVG is stale

Standard library only. Output is deterministic.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSURANCE = HERE.parents[1]
sys.path.insert(0, str(ASSURANCE / "01-management" / "figures"))
from figkit import (INK, MUTED, FAINT, LINE, HAIR, SAFETY, SAFETY_BG, HW, HW_BG, GREEN, GREEN_BG, RED, RED_BG,  # noqa: E402
                    GREY_BG, FigureError, text, rect, line, path, svg, header, pill, fit, text_w)
sys.path.insert(0, str(ASSURANCE / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)

NETLIST = ASSURANCE / "04-hardware" / "spice" / "box-v3-nominal.cir"
RESULTS = ASSURANCE / "sim" / "results" / "harness-box.json"
OUT = "fig-h02-3-7-box-switch-anim.svg"
W = 1280
PERIOD = 4.0                       # seconds per frame
# The frames, in order: scenario ID of harness-box.json -> what the frame shows the reader.
FRAMES = [
  ("pass_through", "SBU1 is not driven, so the box rests in the stock path: the camera's CAN reaches the car "
                   "directly and the device only listens on both buses."),
  ("intercept", "The device drives SBU1 above the threshold: U1 and U2 change over. The camera now talks only to "
                "device bus 2, terminated in the box, and device bus 0 drives the car."),
  ("pulldown_open_leak_up", "With R2/R3 open and SBU1 undriven, IN floats up on its leakage: the box sits in intercept "
                            "with the device off, so the stock camera stays cut off from the car."),
  ("threshold_high_vin_high", "At high VIN with a high threshold and a weak drive, SBU1 stays below VTH: the device "
                              "asks for intercept but the box stays in the stock path."),
]
NETS = ("can0h", "can0l", "can2h", "can2l", "can2hp", "can0lp", "can2lpp")


def load_netlist() -> dict:
  """The CAN switch path: switch channels, terminations and the cited name of each node."""
  src = NETLIST.read_text(encoding="utf-8")
  names = {m.group(1): (m.group(2).strip(), m.group(3)) for m in
           re.finditer(r"^\*\s+(\w+)\s{2,}(.+?)\s+\[(.+?)\]\s*$", src, re.M)}
  els = {m.group(1): (m.group(2), m.group(3), m.group(4)) for m in
         re.finditer(r"^(R\w+)\s+(\w+)\s+(\w+)\s+(\S+)", src, re.M)}
  for n in NETS:
    if n not in names:
      raise FigureError(f"{NETLIST.name}: no citation for node {n}")
  for e in ("RU1NC", "RU1NO", "RU2NC", "RU2NO", "R6", "R7", "R8"):
    if e not in els:
      raise FigureError(f"{NETLIST.name}: no element {e}")
  sw = {}
  for u in ("U1", "U2"):
    nc, no = els[f"R{u}NC"], els[f"R{u}NO"]
    if nc[0] != no[0]:
      raise FigureError(f"{NETLIST.name}: {u} NC and NO do not share a COM node")
    sw[u] = {"com": nc[0], "nc": nc[1], "no": no[1], "r_on": float(nc[2])}
  term = {r: (els[r][0], els[r][1], float(els[r][2])) for r in ("R6", "R7", "R8")}
  return {"names": names, "sw": sw, "term": term, "diodes": len(re.findall(r"^D\w+\s", src, re.M))}


def falstad_value(cct: str, p1: tuple[int, int], p2: tuple[int, int], kind: str = "r") -> float:
  for ln in cct.splitlines():
    f = ln.split()
    if f and f[0] == kind and tuple(map(int, f[1:5])) == (*p1, *p2):
      return float(f[6])
  raise FigureError(f"harness-box.json Falstad circuit: no {kind} element from {p1} to {p2}")


def load() -> tuple[dict, list[dict], dict]:
  net = load_netlist()
  res = json.loads(RESULTS.read_text(encoding="utf-8"))
  by_id = {s["id"]: s for s in res["scenarios"]}
  frames = []
  for sid, says in FRAMES:
    s = by_id.get(sid)
    if s is None:
      raise FigureError(f"harness-box.json has no scenario {sid!r}")
    v = s["nodes"]
    intercept = v["SBU1"] > v["VTH"]
    if ("intercept" in s["verdict"]) != intercept:
      raise FigureError(f"{sid}: SBU1 {v['SBU1']} V against VTH {v['VTH']} V disagrees with its verdict {s['verdict']!r}")
    frames.append({**s, "says": says, "intercept": intercept, "drive": s["switches"].get("drive", True),
                   "pulldown": s["switches"].get("pulldown", True)})
  cct = urllib.parse.unquote(res["link"].split("cct=", 1)[1])
  vals = {"drive_r": falstad_value(cct, (192, 96), (192, 160)), "pull_down": falstad_value(cct, (192, 288), (192, 384))}
  return net, frames, vals


def ohm(v: float) -> str:
  return f"{v:g} Ω"


def resistor(x1, y1, x2, y2, stroke=MUTED) -> str:
  """A zig-zag resistor between two points on a vertical or horizontal line."""
  if x1 == x2:
    n, h = 6, (y2 - y1) / 6
    d = f"M{x1} {y1} " + " ".join(f"L{x1 + (7 if i % 2 == 0 else -7)} {y1 + h * (i + 0.5):.1f}" for i in range(n))
    return path(d + f" L{x2} {y2}", stroke=stroke, sw=1.6)
  n, h = 6, (x2 - x1) / 6
  d = f"M{x1} {y1} " + " ".join(f"L{x1 + h * (i + 0.5):.1f} {y1 + (7 if i % 2 == 0 else -7)}" for i in range(n))
  return path(d + f" L{x2} {y2}", stroke=stroke, sw=1.6)


def ground(x, y) -> list[str]:
  return [line(x, y, x, y + 8, stroke=MUTED), line(x - 10, y + 8, x + 10, y + 8, stroke=MUTED, sw=1.6),
          line(x - 6, y + 12, x + 6, y + 12, stroke=MUTED, sw=1.4), line(x - 2, y + 16, x + 2, y + 16, stroke=MUTED)]


def dot(x, y, fill=INK) -> str:
  return f'<circle cx="{x}" cy="{y}" r="3.2" fill="{fill}"/>'


def figure(net: dict, frames: list[dict], vals: dict) -> str:
  n = len(frames)
  total = PERIOD * n
  names, sw, term = net["names"], net["sw"], net["term"]
  out = header(W, "3-7", "Harness box intercept switch, animated",
               f"ngspice scenarios of the harness box v3 switch path, {n} frames of {PERIOD:g} s: the stock path, intercept, "
               "and two DFMEA faults that leave the box in the wrong state", "WP-H-02 §3.6 · HE-08")
  # CSS: one window per frame; with reduced motion the intercept frame stays.
  keep = next(i for i, f in enumerate(frames) if f["id"] == "intercept")
  css = [f".fr{{opacity:0;animation:{total:g}s steps(1,end) infinite}}"]
  for i in range(n):
    a, b = 100 * i / n, 100 * (i + 1) / n
    css.append(f"@keyframes k{i}{{0%{{opacity:{1 if i == 0 else 0}}}{a:.2f}%{{opacity:1}}{b:.2f}%{{opacity:0}}"
               f"100%{{opacity:{1 if i == 0 else 0}}}}}.f{i}{{animation-name:k{i}}}")
  css.append(f"@media (prefers-reduced-motion:reduce){{.fr{{animation:none}}.f{keep}{{opacity:1}}}}")
  out.append(f"<style>{''.join(css)}</style>")

  # ---------------------------------------------------------------- left: switch drive (static parts)
  out.append(rect(30, 100, 420, 420, fill="#FFFFFF", stroke=LINE, rx=12))
  out.append(text(46, 124, "Switch drive · HE-08", size=13, weight=700))
  out.append(text(46, 141, "SBU1 against the DG419LE input threshold; VIN is the box supply", size=10.5, fill=MUTED))
  sx, top = 110, 175
  out.append(f'<circle cx="{sx}" cy="{top}" r="16" fill="#FFFFFF" stroke="{MUTED}" stroke-width="1.6"/>')
  out.append(text(sx, top + 4, "5 V", size=10, weight=700, anchor="middle"))
  out.append(text(sx - 26, top + 4, "device", size=9.5, fill=MUTED, anchor="end"))
  out.append(line(sx, top + 16, sx, top + 30))
  out.append(resistor(sx, top + 30, sx, top + 74))
  out.append(text(sx + 14, top + 56, f"R out {ohm(vals['drive_r'])}", size=9.5, fill=MUTED))
  out.append(line(sx, top + 74, sx, top + 84))
  sbu = (sx, top + 120)
  out.append(text(sx - 14, sbu[1] + 4, "SBU1", size=10.5, weight=700, anchor="end"))
  out.append(dot(*sbu))
  out.append(line(sx, sbu[1] + 20, sx, sbu[1] + 34))
  out.append(resistor(sx, sbu[1] + 34, sx, sbu[1] + 84))
  out.append(text(sx + 14, sbu[1] + 64, f"R2/R3 {ohm(vals['pull_down'])}", size=9.5, fill=MUTED))
  out += ground(sx, sbu[1] + 84)
  # comparator: + SBU1, - VTH, output IN
  cx, cy = 300, sbu[1]
  out.append(path(f"M{cx} {cy - 34} L{cx} {cy + 34} L{cx + 58} {cy} Z", stroke=INK, sw=1.6, fill="#FFFFFF"))
  out.append(text(cx + 6, cy - 12, "+", size=12, weight=700))
  out.append(text(cx + 6, cy + 22, "−", size=12, weight=700))
  out.append(line(sx, cy, cx, cy - 16, stroke=INK))
  out.append(line(cx - 30, cy + 18, cx, cy + 18, stroke=INK))
  out.append(text(cx - 34, cy + 22, "VTH", size=10.5, weight=700, anchor="end"))
  out.append(text(cx - 34, cy + 36, "= k × VIN", size=9.5, fill=MUTED, anchor="end"))
  out.append(line(cx + 58, cy, cx + 90, cy, stroke=INK))
  out.append(text(cx + 30, cy + 54, "DG419LE IN", size=9.5, fill=MUTED, anchor="middle"))
  out.append(text(cx + 94, cy - 8, "IN", size=10.5, weight=700))

  # ---------------------------------------------------------------- right: CAN switch path (static parts)
  X0 = 470
  out.append(rect(X0, 100, W - 30 - X0, 420, fill="#FFFFFF", stroke=LINE, rx=12))
  out.append(text(X0 + 16, 124, "CAN switch path · harness box v3", size=13, weight=700))
  out.append(text(X0 + 16, 141, f"U1 on CAN_H, U2 on CAN_L (DG419LE, R on {ohm(sw['U1']['r_on'])}); "
                  f"{net['diodes']} clamp diodes to VIN and GND not drawn", size=10.5, fill=MUTED))
  yh, yl = 210, 350
  xcam, xcar = X0 + 60, W - 90
  # camera and car connectors
  for x, title, sub in ((xcam - 40, "camera", "CAN2"), (xcar + 10, "car", "CAN0")):
    out.append(rect(x, yh - 34, 50, yl - yh + 68, fill=GREY_BG, stroke=LINE, rx=6))
    out.append(text(x + 25, yh - 42, title, size=10.5, weight=700, anchor="middle"))
    out.append(text(x + 25, yl + 52, sub, size=9.5, fill=MUTED, anchor="middle"))
  u1x, u2x = X0 + 330, X0 + 420
  # U1: COM on the camera's CAN_H, NC towards the car, NO down to the camera-side termination
  def lbl(node):  # the cited name; a node the netlist does not cite (R6's far end) by its netlist name
    return names[node][0].split(" (")[0] if node in names else node
  wires = [
    ("cam_h", [(xcam + 10, yh), (u1x, yh)]),
    ("u1_nc", [(u1x + 46, yh), (xcar + 10, yh)]),
    ("u1_no", [(u1x + 46, yh + 34), (u1x + 120, yh + 34), (u1x + 120, yh + 70)]),
    ("cam_l", [(xcam + 10, yl), (u2x - 46, yl)]),
    ("u2_com", [(u2x, yl), (xcar + 10, yl)]),
    ("u2_no", [(u2x - 46, yl + 34), (u2x - 120, yl + 34), (u2x - 120, yl + 64)]),
  ]
  for _, pts in wires:
    out.append(path("M" + " L".join(f"{x} {y}" for x, y in pts), stroke=LINE, sw=2))
  for x, y in ((u1x, yh), (u1x + 46, yh), (u1x + 46, yh + 34), (u2x, yl), (u2x - 46, yl), (u2x - 46, yl + 34)):
    out.append(f'<circle cx="{x}" cy="{y}" r="3.6" fill="#FFFFFF" stroke="{INK}" stroke-width="1.4"/>')
  out.append(text(u1x + 23, yh - 26, "U1", size=11, weight=700, anchor="middle"))
  out.append(text(u2x - 23, yl - 26, "U2", size=11, weight=700, anchor="middle"))
  for x, y, t, a in ((u1x - 4, yh - 8, "COM", "end"), (u1x + 50, yh - 8, "NC", "start"), (u1x + 50, yh + 48, "NO", "start"),
                     (u2x + 4, yl - 8, "COM", "start"), (u2x - 50, yl - 8, "NC", "end"), (u2x - 50, yl + 48, "NO", "end")):
    out.append(text(x, y, t, size=8.5, fill=MUTED, anchor=a))
  # net names from the netlist citations
  for x, y, node, a in ((xcam + 18, yh - 8, sw["U1"]["com"], "start"), (xcar - 4, yh - 8, sw["U1"]["nc"], "end"),
                        (xcam + 18, yl - 8, sw["U2"]["nc"], "start"), (xcar - 4, yl - 8, sw["U2"]["com"], "end")):
    out.append(text(x, y, lbl(node), size=9.5, fill=MUTED, anchor=a))
  # terminations
  r7a, r7b, r7v = term["R7"]
  out.append(resistor(u1x + 120, yh + 70, u1x + 120, yh + 112))
  out.append(text(u1x + 134, yh + 92, f"R7 {ohm(r7v)}, R8 {ohm(term['R8'][2])}", size=9.5, fill=MUTED))
  out.append(text(u1x + 134, yh + 106, f"{lbl(r7b)} to {lbl(r7a)}", size=9, fill=FAINT))
  out.append(path(f"M{u1x + 120} {yh + 112} L{u1x + 120} {yl - 20} L{u2x - 70} {yl - 20} L{u2x - 70} {yl}", stroke=LINE, sw=1.4))
  out.append(dot(u2x - 70, yl, MUTED))
  out.append(resistor(u2x - 120, yl + 64, u2x - 120, yl + 104))
  r6a, r6b, r6v = term["R6"]
  out.append(text(u2x - 134, yl + 86, f"R6 {ohm(r6v)}", size=9.5, fill=MUTED, anchor="end"))
  out.append(text(u2x - 134, yl + 100, f"{lbl(r6a)} to {lbl(r6b)}", size=9, fill=FAINT, anchor="end"))
  # device taps at J3: bus 2 on the camera side, bus 0 on the car side
  jy = 488
  out.append(rect(X0 + 40, jy - 4, W - 70 - X0 - 40, 24, fill=HW_BG, stroke=HW, rx=6))
  out.append(text(X0 + 52, jy + 12, "J3 · device (panda safety MCU)", size=10, weight=700, fill=HW))
  taps = [(xcam + 40, yh, "bus 2"), (xcam + 64, yl, ""), (xcar - 50, yh, "bus 0"), (xcar - 26, yl, "")]
  for x, y, t in taps:
    out.append(line(x, y, x, jy - 4, stroke=HW, sw=1.4, dash="4 3"))
    out.append(dot(x, y, HW))
    if t:
      out.append(text(x + 8, jy - 12, t, size=9.5, weight=700, fill=HW))

  # ---------------------------------------------------------------- the frames
  for i, f in enumerate(frames):
    g = [f'<g class="fr f{i}">']
    v = f["nodes"]
    col = SAFETY if f["intercept"] else GREEN
    fault = f["fmea"] != "nominal"
    # drive switch and pull-down in the left panel
    dy = top + 84
    if f["drive"]:
      g.append(line(sx, dy, sx, dy + 36, stroke=INK, sw=2))
    else:
      g.append(line(sx, dy, sx - 18, dy + 30, stroke=INK, sw=2))
      g.append(text(sx - 24, dy + 20, "not driven", size=9.5, fill=MUTED, anchor="end"))
    g.append(dot(sx, dy))
    if not f["pulldown"]:
      py = sbu[1] + 52
      g.append(line(sx - 10, py - 10, sx + 10, py + 10, stroke=RED, sw=2.4))
      g.append(line(sx - 10, py + 10, sx + 10, py - 10, stroke=RED, sw=2.4))
      g.append(text(sx - 16, py + 4, "open", size=10, weight=700, fill=RED, anchor="end"))
    g.append(text(sx + 16, sbu[1] - 8, f"{v['SBU1']:.2f} V", size=12, weight=700, fill=col))
    g.append(text(cx - 34, cy + 52, f"{v['VTH']:.2f} V at VIN {v['VIN']:g} V", size=10, weight=700, fill=INK, anchor="end"))
    state = "intercept" if f["intercept"] else "stock path"
    g += pill(cx + 94, cy + 4, state, col, h=18, size=10)[0]
    # the CAN path in the right panel
    if f["intercept"]:
      blades = [(u1x, yh, u1x + 44, yh + 32), (u2x, yl, u2x - 44, yl + 32)]
      hot = [[(xcam + 10, yh), (u1x, yh)], [(u1x + 46, yh + 34), (u1x + 120, yh + 34), (u1x + 120, yh + 70)],
             [(xcam + 10, yl), (u2x - 46, yl)], [(u1x + 46, yh), (xcar + 10, yh)], [(u2x, yl), (xcar + 10, yl)],
             [(u2x - 46, yl + 34), (u2x - 120, yl + 34), (u2x - 120, yl + 64)]]
      g.append(text(xcam + 140, yh + 64, "camera ⇄ device bus 2", size=10.5, weight=700, fill=col))
      g.append(text(xcar - 30, yl + 82, "device bus 0 ⇄ car", size=10.5, weight=700, fill=col, anchor="end"))
    else:
      blades = [(u1x, yh, u1x + 46, yh), (u2x, yl, u2x - 46, yl)]
      hot = [[(xcam + 10, yh), (xcar + 10, yh)], [(xcam + 10, yl), (xcar + 10, yl)]]
      g.append(text((xcam + xcar) / 2, yh + 64, "camera ⇄ car: stock path", size=10.5, weight=700, fill=col,
                    anchor="middle"))
    for pts in hot:
      g.append(path("M" + " L".join(f"{x} {y}" for x, y in pts), stroke=col, sw=3.2))
    for x1, y1, x2, y2 in blades:
      g.append(line(x1, y1, x2, y2, stroke=INK, sw=2.6))
    # caption of the frame
    by = 540
    g.append(rect(30, by, W - 60, 96, fill=RED_BG if fault else (SAFETY_BG if f["intercept"] else GREEN_BG),
                  stroke=RED if fault else col, rx=10))
    g += pill(46, by + 14, f"{i + 1} / {n}", INK, h=18, size=10)[0]
    g.append(text(96, by + 27, f["title"], size=13, weight=700))
    g += pill(W - 46 - text_w(f["fmea"], 10, True) - 12, by + 14, f["fmea"], RED if fault else GREEN, h=18, size=10)[0]
    g.append(text(46, by + 52, fit(f["says"], W - 92, 11.5), size=11.5))
    g.append(text(46, by + 74, fit(f"ngspice: {f['verdict']}", W - 92, 10.5), size=10.5, fill=MUTED))
    g.append("</g>")
    out += g

  # ---------------------------------------------------------------- the four scenarios at a glance (static)
  y = 664
  out.append(text(40, y, "All frames", size=12, weight=700))
  cols = [(40, "Scenario"), (520, "DFMEA"), (640, "SBU1"), (730, "VTH"), (830, "VIN"), (920, "Box state")]
  for x, t in cols:
    out.append(text(x, y + 22, t, size=10, fill=MUTED, weight=700))
  for i, f in enumerate(frames):
    yy = y + 42 + i * 20
    v = f["nodes"]
    out.append(text(40, yy, f"{i + 1}. {fit(f['title'], 470, 10.5)}", size=10.5))
    out.append(text(520, yy, f["fmea"], size=10.5, fill=RED if f["fmea"] != "nominal" else MUTED))
    for x, k in ((640, "SBU1"), (730, "VTH"), (830, "VIN")):
      out.append(text(x, yy, f"{v[k]:.2f} V", size=10.5))
    out.append(text(920, yy, "intercept" if f["intercept"] else "stock path", size=10.5, weight=700,
                    fill=SAFETY if f["intercept"] else GREEN))
  y += 42 + n * 20 + 12
  out.append(text(40, y, "Synthetic data, no evidence credit (DQ-413). Idealised switches; the DG419LE threshold at "
                  "VL = VIN and the device's SBU1 driver are bands, not published values.", size=10.5, fill=MUTED))
  y += 18
  out.append(text(40, y, f"Generated by fig_h02_box_anim.py from spice/{NETLIST.name} and sim/results/{RESULTS.name}; "
                  "nothing is hand-listed but the frame order and each frame's sentence.", size=10.5, fill=MUTED))
  extra, y = terms.svg_footer(out, 40, y + 22, W - 80)
  out += extra
  desc = (f"Animated circuit, {n} frames: " + " ".join(
    f"{i + 1}. {f['title']} ({f['fmea']}): SBU1 {f['nodes']['SBU1']:.2f} V, VTH {f['nodes']['VTH']:.2f} V, "
    f"{'intercept' if f['intercept'] else 'stock path'}." for i, f in enumerate(frames)))
  return svg(W, int(y + 12), "Figure 3-7. Harness box intercept switch, animated (WP-H-02)", desc, out)


def build() -> dict[str, str]:
  return {OUT: figure(*load())}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except FigureError as e:
    print(f"fig_h02_box_anim: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n_ for n_, c in outputs.items() if not (HERE / n_).exists() or (HERE / n_).read_text(encoding="utf-8") != c]
    for n_ in stale:
      print(f"assurance/04-hardware/figures/{n_} is stale; run fig_h02_box_anim.py", file=sys.stderr)
    if not stale:
      print(f"fig_h02_box_anim: {len(outputs)} figure current")
    return 1 if stale else 0
  for n_, c in outputs.items():
    (HERE / n_).write_text(c, encoding="utf-8")
    print(f"wrote assurance/04-hardware/figures/{n_}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
