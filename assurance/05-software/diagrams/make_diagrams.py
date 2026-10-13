#!/usr/bin/env python3
"""Generate the MATLAB-style design diagrams of the software work products (SVG, deterministic).

  stateflow-<record>.svg   Stateflow-style chart of each state-machine record in ../state-machines/*.yaml:
                           states as rounded boxes, default transition, transitions grouped per state pair and
                           labelled with their IDs, and a transition table in Stateflow label notation
                           "event [guard] / {action}". Solid: implemented or partial; dashed: not implemented
                           (target state, code field "not implemented"); the table gives the WP-W-02 Baseline status
                           of the cited SWSRs, which the checker uses (a transition can exist and still not meet them).
  simulink-envelope.svg    Simulink-style block diagram of the safety envelope signal flow (reference build),
                           each block citing its WP-W-05 unit; the authority chart is drawn as a chart block.

The charts are generated from the records, so they cannot drift from WP-W-05 §5. The block diagram is defined
below as data and describes the code at the baseline of WP-W-05 (a design description, not verified).

Usage:  python3 assurance/05-software/diagrams/make_diagrams.py [--check]
Standard library only (PyYAML used by the record loader if installed).
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import svgkit as K  # noqa: E402

_spec = importlib.util.spec_from_file_location("check_state_machines",
                                               HERE.parents[1] / "trace" / "tools" / "check_state_machines.py")
csm = importlib.util.module_from_spec(_spec)
sys.modules["check_state_machines"] = csm
_spec.loader.exec_module(csm)

# State positions (centre x, y) per record; a state without a position is an error, so a new state forces a layout
LAYOUT = {
  "SM-TOY-AUTH": {"size": (900, 330), "states": {"NOT_ALLOWED": (220, 175), "ALLOWED": (680, 175)},
                  "roles": [(None, "no authority"), (1, "authority on the car (controls_allowed = 1)", "ALLOWED")]},
  "SM-SAFETY-MODE": {"size": (900, 520), "junction": (450, 285), "bend": {("ELM327", "SILENT"): -24},
                     "states": {"SILENT": (150, 150), "NOOUTPUT": (450, 130), "ELM327": (750, 150),
                                "TOYOTA": (270, 430), "OTHER_CAR": (630, 430)},
                     "roles": [(None, "no actuation output"), (3, "diagnostic", "ELM327"),
                               (1, "car mode: actuation possible with authority", "TOYOTA", "OTHER_CAR")]},
  "SM-SELFDRIVED": {"size": (900, 530),
                    "states": {"disabled": (140, 300), "preEnabled": (310, 110), "enabled": (520, 300),
                               "overriding": (770, 130), "softDisabling": (770, 450)},
                    "roles": [(None, "not engaged"), (4, "engagement pending", "preEnabled"),
                              (1, "engaged", "enabled"), (7, "engaged, driver overriding", "overriding"),
                              (8, "disengaging (3 s timer)", "softDisabling")]},
}
BOX_H = 52
LEGEND_W = 860


# ------------------------------------------------------------------ geometry

def box_w(name: str) -> float:
  return max(130.0, len(name) * 8.2 + 40)


def border_point(c, w, h, toward):
  """Point where the ray from the box centre c toward `toward` leaves the box (w x h)."""
  dx, dy = toward[0] - c[0], toward[1] - c[1]
  if dx == 0 and dy == 0:
    return c
  tx = (w / 2) / abs(dx) if dx else math.inf
  ty = (h / 2) / abs(dy) if dy else math.inf
  t = min(tx, ty)
  return (c[0] + dx * t, c[1] + dy * t)


def quad(p0, c, p1, t):
  return ((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
          (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1])


def label(x, y, lines, cls="tm"):
  w = max(len(s) for s in lines) * K.CHAR_W * 0.95 + 8
  h = 13 * len(lines) + 4
  out = [f'<rect class="lbl" x="{x - w / 2:.1f}" y="{y - h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="3"/>']
  for i, s in enumerate(lines):
    out.append(K.text(x, y - h / 2 + 13 + 13 * i - 2, s, cls, "middle"))
  return out


# ------------------------------------------------------------------ Stateflow-style charts

def stateflow(sm: dict, sw: dict, record: str) -> str:
  name = sm["machine"]
  lay = LAYOUT[name]
  W, H0 = lay["size"]
  pos = lay["states"]
  missing = [s for s in sm["states"] if s not in pos]
  if missing:
    raise SystemExit(f"{name}: no layout position for {missing}")
  size = {s: (box_w(s), BOX_H) for s in sm["states"]}
  body = []

  # group transitions per (source, target, implemented?)
  groups: dict[tuple, list[str]] = {}
  for t in sm["transitions"]:
    impl = not t.get("code", "").startswith("not implemented")  # drawn solid if the code exists
    for s in csm._sources(t, sm["states"]):
      dst = s if t["to"] == "same" else t["to"]
      groups.setdefault((s, dst, impl), []).append(t["id"])

  # edges between distinct nodes, spread by pair
  pairs: dict[frozenset, list[tuple]] = {}
  for key in groups:
    s, d, _ = key
    if s != d:
      pairs.setdefault(frozenset((s, d)), []).append(key)
  for pair, keys in pairs.items():
    keys.sort(key=lambda k: (k[0], k[2] is False))
    n = len(keys)
    u, v = sorted(pair)  # fixed frame per pair, so both directions bend in one consistent sense
    pu = pos[u] if u != "m" else lay["junction"]
    pv = pos[v] if v != "m" else lay["junction"]
    fx, fy = pv[0] - pu[0], pv[1] - pu[1]
    fl = math.hypot(fx, fy) or 1
    px, py = -fy / fl, fx / fl
    for i, (s, d, impl) in enumerate(keys):
      a = pos[s]
      b = lay["junction"] if d == "m" else pos[d]
      wb, hb = (14, 14) if d == "m" else size[d]
      off = (i - (n - 1) / 2) * 58 + lay.get("bend", {}).get((s, d), 0)
      mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
      ctrl = (mx + px * off * 2, my + py * off * 2)
      p0 = border_point(a, *size[s], ctrl)
      p1 = border_point(b, wb, hb, ctrl)
      cls = "edge" if impl else "edge todo"
      body.append(f'<path class="{cls}" d="M{p0[0]:.1f},{p0[1]:.1f} Q{ctrl[0]:.1f},{ctrl[1]:.1f} {p1[0]:.1f},{p1[1]:.1f}"/>')
      e = quad(p0, ctrl, p1, 0.97)
      body.append(K.arrowhead(p1[0], p1[1], p1[0] - e[0], p1[1] - e[1], "arrow" if impl else "arrow todo"))
      lx, ly = quad(p0, ctrl, p1, 0.5)
      body += label(lx, ly, K.wrap(", ".join(groups[(s, d, impl)]), 150))

  # self loops, stacked above each state
  loops: dict[str, list[tuple]] = {}
  for key in groups:
    if key[0] == key[1]:
      loops.setdefault(key[0], []).append(key)
  for s, keys in loops.items():
    cx, cy = pos[s]
    w, h = size[s]
    for i, key in enumerate(sorted(keys, key=lambda k: k[2] is False)):
      impl = key[2]
      r = 18 + 16 * i
      x0, x1 = cx - w / 4 - 6 * i, cx + w / 4 + 6 * i
      top = cy - h / 2
      cls = "edge" if impl else "edge todo"
      body.append(f'<path class="{cls}" d="M{x0:.1f},{top:.1f} C{x0:.1f},{top - 2.2 * r:.1f} {x1:.1f},{top - 2.2 * r:.1f} {x1:.1f},{top:.1f}"/>')
      body.append(K.arrowhead(x1, top, 0, 1, "arrow" if impl else "arrow todo"))
      body += label(cx, top - 1.65 * r, [", ".join(groups[key])])

  # junction for "requested mode m"
  if "junction" in lay:
    jx, jy = lay["junction"]
    for st in sm["states"]:
      p1 = border_point(pos[st], *size[st], (jx, jy))
      body.append(f'<path class="edge thin" d="M{jx:.1f},{jy:.1f} L{p1[0]:.1f},{p1[1]:.1f}"/>')
      body.append(K.arrowhead(p1[0], p1[1], p1[0] - jx, p1[1] - jy, "arrow", size=5))
    body.append(f'<circle class="box" cx="{jx}" cy="{jy}" r="7"/>')
    body += label(jx + 52, jy + 2, ["[mode = m]"])

  # states (filled by role) and default transition
  role = {st: f"k{r[0]}" for r in lay["roles"] if r[0] for st in r[2:]}
  unknown = set(role) - set(sm["states"])
  if unknown:
    raise SystemExit(f"{name}: roles name unknown states {sorted(unknown)}")
  for st in sm["states"]:
    cx, cy = pos[st]
    w, h = size[st]
    body.append(f'<rect class="shadow" x="{cx - w / 2 + 3:.1f}" y="{cy - h / 2 + 3:.1f}" width="{w:.1f}" height="{h:.1f}" rx="12"/>')
    body.append(f'<rect class="{role.get(st, 'box')}" x="{cx - w / 2:.1f}" y="{cy - h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="12"/>')
    body.append(K.text(cx - w / 2 + 10, cy - h / 2 + 18, st, "tb"))
  ix, iy = pos[sm["initial"]]
  w, h = size[sm["initial"]]
  sx = ix - w / 2 - 46
  body.append(f'<circle class="dot" cx="{sx:.1f}" cy="{iy:.1f}" r="4"/>')
  body.append(f'<path class="edge" d="M{sx:.1f},{iy:.1f} L{ix - w / 2:.1f},{iy:.1f}"/>')
  body.append(K.arrowhead(ix - w / 2, iy, 1, 0))

  # legend: state roles, then the two edge styles
  lx, ly = 20, H0 - 18
  for r in lay["roles"]:
    body.append(f'<rect class="{f"k{r[0]}" if r[0] else "box"}" x="{lx}" y="{ly - 10}" width="22" height="14" rx="4"/>')
    body.append(K.text(lx + 28, ly + 1, r[1], "t2"))
    lx += 28 + len(r[1]) * K.CHAR_W + 22
  ly += 20
  body += [f'<path class="edge" d="M20,{ly - 4} L46,{ly - 4}"/>', K.text(52, ly, "in the code", "t2"),
           f'<path class="edge todo" d="M150,{ly - 4} L176,{ly - 4}"/>',
           K.text(182, ly, "not in the code (target state)", "t2")]

  # header
  head = [K.text(20, 26, f"{name}: {sm['title']}", "th"),
          K.text(20, 44, f"Stateflow-style chart generated from state-machines/{record} by diagrams/make_diagrams.py.", "ts"),
          K.text(20, 58, "Solid grey: in the code. Dashed orange: not in the code. Fill: state role (legend). "
                 "Status: WP-W-02 Baseline of the cited SWSRs.", "ts")]

  # transition table
  y = H0 + 32
  rows = [K.text(20, y, "Transitions (Stateflow label notation: event [guard] / {action})", "tb")]
  y += 10
  col = (20, 70, 620, 690)
  rows.append(f'<line class="grid" x1="20" y1="{y + 4}" x2="{20 + LEGEND_W}" y2="{y + 4}"/>')
  y += 18
  for c, hdr in zip(col, ("ID", "Transition", "Build", "WP-W-02 status")):
    rows.append(K.text(c, y, hdr, "t2"))
  y += 6
  for t in sm["transitions"]:
    guard = f" [{t['guard']}]" if t.get("guard") else ""
    act = t.get("action") or "none"
    src = t["from"]
    dst = t["to"]
    lab = f"{src} → {dst}: {t['event']}{guard} / {{{act}}}"
    lines = K.wrap(lab, col[2] - col[1] - 14)
    st = csm.LABEL[csm.transition_state(t, sw)]
    if t.get("code", "").startswith("not implemented"):
      st += " (not in code)"
    rows.append(f'<line class="grid" x1="20" y1="{y + 4}" x2="{20 + LEGEND_W}" y2="{y + 4}"/>')
    if "not in code" in st:  # same orange as the dashed edge
      rows.append(f'<rect class="k2" style="stroke:none" x="20" y="{y + 5}" width="{LEGEND_W}" '
                  f'height="{14 * len(lines) + 2}"/>')
    y += 17
    rows.append(K.text(col[0], y, t["id"], "tb"))
    for i, ln in enumerate(lines):
      rows.append(K.text(col[1], y + 14 * i, ln, "t"))
    rows.append(K.text(col[2], y, t.get("build", "all"), "t2"))
    rows.append(K.text(col[3], y, st, "t2"))
    y += 14 * (len(lines) - 1) + 3
  H = int(y + 24)
  desc = (f"Stateflow-style chart of {name} with {len(sm['states'])} states and {len(sm['transitions'])} transitions, "
          f"generated from {record}; the table below the chart lists every transition.")
  return K.doc(W, H, f"{name} state chart", desc, head + body + rows)


# ------------------------------------------------------------------ Simulink-style block diagram

# id: (x, y, w, h, title, subtitle, kind)   kind: in | out | block | ref (reference build only) | chart
BLOCKS = {
  "IN1": (24, 109, 100, 30, "CAN RX bus 0", "", "in"),
  "RXC": (175, 88, 200, 72, "RX checks", "UN-02: ID/bus/DLC match, checksum, quality flag, time stamp", "block"),
  "HOOK": (440, 88, 210, 72, "toyota_rx_hook", "UN-14: CRUISE_ACTIVE, GAS_RELEASED, BRAKE_PRESSED, wheel speeds, MAIN_ON*", "block"),
  "GEN": (440, 190, 210, 60, "generic_rx_checks", "UN-01 (3): brake rising, or pressed while moving", "block"),
  "TICK": (440, 280, 210, 60, "safety_tick (100 Hz)", "UN-05, UN-37: RX timeout, invalid check; TX arrival*", "block"),
  "HB": (440, 370, 210, 60, "Heartbeat monitor", "panda main.c (UN-N1): SoC heartbeat lost > 0.3 s", "block"),
  "MODE": (440, 455, 210, 60, "set_safety_hooks", "UN-07: safety-mode change resets all state", "block"),
  "CHART": (800, 52, 190, 480, "SM-TOY-AUTH", "Stateflow chart (§5.2): controls_allowed", "chart"),
  "IN2": (24, 578, 100, 30, "SoC TX (SPI)", "", "in"),
  "TXW": (175, 563, 200, 60, "TX whitelist", "UN-03: (addr, bus, DLC) allowed", "block"),
  "RATE": (440, 563, 210, 60, "tx_rate_check*", "UN-36: per-ID budget in a 250 ms window", "ref"),
  "LIM": (800, 563, 210, 60, "toyota_tx_hook", "UN-15: torque and accel limits; needs authority", "block"),
  "OUT1": (1060, 578, 100, 30, "CAN TX bus 0", "", "out"),
}
# polyline points, label (x, y, anchor)
LINES = [
  ([(124, 124), (175, 124)], ("frame", 150, 118, "middle")),
  ([(375, 124), (440, 124)], ("valid", 420, 118, "middle")),
  ([(400, 124), (400, 310), (440, 310)], ("time stamps", 396, 300, "end")),
  ([(390, 124), (390, 70), (800, 70)], ("invalid frame: T4 (clear)", 595, 64, "middle")),
  ([(650, 124), (800, 124)], ("cruise edge, MAIN_ON*", 731, 118, "middle")),
  ([(668, 124), (668, 175), (425, 175), (425, 220), (440, 220)], ("brake, moving", 546, 169, "middle")),
  ([(650, 220), (800, 220)], ("brake: T3", 725, 214, "middle")),
  ([(650, 310), (800, 310)], ("T5, T10b*", 725, 304, "middle")),
  ([(650, 400), (800, 400)], ("T6, T10a", 725, 394, "middle")),
  ([(650, 485), (800, 485)], ("reset: T7", 725, 479, "middle")),
  ([(124, 593), (175, 593)], ("frame", 150, 587, "middle")),
  ([(375, 593), (440, 593)], ("allowed", 407, 587, "middle")),
  ([(650, 593), (684, 593), (684, 608), (800, 608)], ("within budget", 742, 622, "middle")),
  ([(700, 593), (700, 515), (800, 515)], ("excess: T11", 706, 509, "start")),
  ([(990, 292), (1028, 292), (1028, 548), (780, 548), (780, 578), (800, 578)], ("controls_allowed", 904, 542, "middle")),
  ([(1010, 593), (1060, 593)], ("accepted", 1035, 587, "middle")),
]
BRANCHES = [(400, 124), (390, 124), (668, 124), (700, 593)]


# block kind: (palette slot or None, legend text). Simulink-like colouring by role; the shape and glyph carry the kind too
KIND = {"in": (3, "input port"), "out": (2, "output port"), "block": (1, "function"), "ref": (None, "reference build only"),
        "chart": (7, "Stateflow chart"), "store": (4, "Data Store Memory"), "subsys": (6, "subsystem")}


def render_blocks(spec: dict) -> str:
  """Simulink-style block diagram from a spec: blocks, groups (interrupt contexts / areas), lines, branch points."""
  W, H = spec["size"]
  H += 24  # legend row
  body = [K.text(20, 26, spec["title"], "th")]
  for i, ln in enumerate(spec["sub"]):
    body.append(K.text(20, 44 + 14 * i, ln, "ts"))
  body.append(K.text(20, H - 14, spec["foot"], "ts"))
  lx, ly = 20, H - 36
  body.append(K.text(lx, ly, "Block colour:", "t2"))
  lx += 86
  used = {b[6] for b in spec["blocks"].values()}
  for kind, (slot, lab) in KIND.items():
    if kind in used:
      dash = ' stroke-dasharray="5 3"' if kind == "ref" else ""
      body.append(f'<rect class="{f"k{slot}" if slot else "box"}" x="{lx}" y="{ly - 10}" width="22" height="14" '
                  f'rx="{7 if kind in ("in", "out") else 0}"{dash}/>')
      body.append(K.text(lx + 28, ly + 1, lab, "t2"))
      lx += 28 + len(lab) * K.CHAR_W + 22
  for (x, y, w, h, title) in spec.get("groups", []):
    body.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="edge target"/>')
    body.append(K.text(x + 10, y + 15, title, "t2"))
  lines_svg = []
  for line in spec["lines"]:
    pts, lab = line[0], line[1]
    style = line[2] if len(line) > 2 else "edge"
    d = "M" + " L".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
    lines_svg.append(f'<path class="{style}" d="{d}"/>')
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    lines_svg.append(K.arrowhead(x1, y1, x1 - x0, y1 - y0, "arrow target" if "target" in style else "arrow"))
    if lab:
      t, lx, ly, anchor = lab
      lines_svg.append(K.text(lx, ly, t, "tm", anchor))
  for bx, by in spec.get("branches", []):
    lines_svg.append(f'<circle class="dot" cx="{bx}" cy="{by}" r="3"/>')
  blocks_svg = []
  for bid, (x, y, w, h, title, sub, kind) in spec["blocks"].items():
    fill = f"k{KIND[kind][0]}" if KIND[kind][0] else "box"
    if kind in ("in", "out"):
      blocks_svg.append(f'<rect class="{fill}" x="{x}" y="{y}" width="{w}" height="{h}" rx="14"/>')
      for i, ln in enumerate(K.wrap(title, w - 12)):
        blocks_svg.append(K.text(x + w / 2, y + h / 2 + 4 - 7 * (len(K.wrap(title, w - 12)) - 1) + 14 * i, ln, "t",
                                 "middle"))
      continue
    dash = ' stroke-dasharray="5 3"' if kind == "ref" else ""
    blocks_svg.append(f'<rect class="shadow" x="{x + 3}" y="{y + 3}" width="{w}" height="{h}"/>')
    blocks_svg.append(f'<rect class="{fill}" x="{x}" y="{y}" width="{w}" height="{h}"{dash}/>')
    if kind == "store":  # Simulink Data Store Memory: double top rule
      blocks_svg.append(f'<path class="edge" d="M{x},{y + 6} L{x + w},{y + 6}"/>')
    if kind == "subsys":  # subsystem: small inner frame glyph
      blocks_svg.append(f'<rect class="edge" x="{x + w - 22}" y="{y + h - 16}" width="14" height="10"/>')
    ty = y + h / 2 - 8 if kind in ("chart", "store") else y + 18
    blocks_svg.append(K.text(x + w / 2, ty, title, "tb", "middle"))
    for i, ln in enumerate(K.wrap(sub, w - 16)):
      blocks_svg.append(K.text(x + w / 2, ty + 16 + 13 * i, ln, "ts", "middle"))
    if kind == "chart":  # small Stateflow glyph
      gx, gy = x + w / 2 - 34, ty + 16 + 13 * len(K.wrap(sub, w - 16)) + 8
      blocks_svg += [f'<rect class="box" x="{gx}" y="{gy}" width="26" height="16" rx="5"/>',
                     f'<rect class="box" x="{gx + 42}" y="{gy}" width="26" height="16" rx="5"/>',
                     f'<path class="edge" d="M{gx + 26},{gy + 8} L{gx + 42},{gy + 8}"/>',
                     K.arrowhead(gx + 42, gy + 8, 1, 0, size=5)]
  return K.doc(W, H, spec["name"], spec["desc"], body + lines_svg + blocks_svg)


ENVELOPE = {
  "name": "Safety envelope block diagram", "size": (1180, 660),
  "title": "Safety envelope signal flow (reference build)",
  "sub": ["Simulink-style block diagram generated by diagrams/make_diagrams.py; blocks cite the WP-W-05 units at the "
          "WP-W-05 baseline. * reference build only (LIONDRIVER_REFERENCE=1)."],
  "foot": "Design description, not verified. The authority chart is WP-W-05 §5.2 (stateflow-sm-toy-auth.svg); "
          "transition IDs on the lines refer to it.",
  "blocks": BLOCKS, "lines": LINES, "branches": BRANCHES,
  "desc": ("Block diagram: CAN RX frames pass the RX checks and the Toyota RX hook; decoded signals, the 100 Hz safety "
           "tick, the heartbeat monitor and mode changes drive the authority chart; SoC TX frames pass the whitelist, "
           "the rate check and the Toyota TX limits, which also need controls_allowed, before CAN TX."),
}

# panda firmware (WP-W-03 §3.1, §3.2, §5.1), grouped by interrupt context
PANDA = {
  "name": "Panda firmware block diagram", "size": (1290, 830),
  "title": "Panda firmware: components by execution context (panda 8aa8671, opendbc 7993399)",
  "sub": ["Simulink-style block diagram generated by diagrams/make_diagrams.py from WP-W-03 §3.1, §3.2 and §5.1. "
          "Dashed frames: interrupt contexts (all at NVIC level 8, run to completion).",
          "Dashed blocks: reference build only. Thin dashed lines: writes (W) and reads (R) of the shared authority "
          "flag controls_allowed (Data Store Memory)."],
  "foot": "Design description, not verified. All envelope processing runs in interrupt context; the main loop only "
          "marks progress for the hardware watchdog (WP-W-03 §5.1).",
  "groups": [
    (150, 82, 970, 250, "DMA2 Stream2 IRQ: SPI RX done (U-PND-SPI → U-PND-COMMS)"),
    (150, 350, 970, 250, "FDCAN IRQs: RX (IT0) and TX (IT1)"),
    (150, 618, 470, 92, "TIM4 safety task, 100 Hz"),
    (640, 618, 480, 92, "TIM12 tick, 8 Hz (every 8th: 1 Hz)"),
    (150, 724, 470, 66, "Thread mode: main loop"),
  ],
  "blocks": {
    "SOCIN": (20, 140, 110, 44, "SoC SPI4 transfers", "", "in"),
    "SPI": (170, 132, 170, 60, "spi_rx_done", "header and data XOR, DMA", "block"),
    "CTRL": (390, 112, 180, 60, "comms_control_handler", "control requests (main_comms.h)", "block"),
    "LOCK": (610, 112, 190, 60, "reference_request_allowed", "refuses other requests, counts them", "ref"),
    "MODE": (850, 100, 250, 50, "0xdc set_safety_mode", "critical section → set_safety_hooks", "block"),
    "HBR": (850, 162, 250, 46, "0xf3 heartbeat", "counters, heartbeat_monitor_reset", "block"),
    "RELAY": (850, 220, 250, 46, "0xc5 relay (U-PND-HARN)", "set_intercept_relay, starts IWDG", "block"),
    "CANW": (390, 252, 180, 60, "comms_can_write", "→ can_send (U-PND-FDCAN)", "block"),
    "TXH": (610, 238, 220, 84, "safety_tx_hook", "whitelist → tx_rate_check* → toyota_tx_hook (EPS gate*) → lateral / longitudinal limits", "block"),
    "QUE": (870, 372, 230, 60, "can_queues → process_can", "packet XOR check, FDCAN TX FIFO", "block"),
    "BUSOUT": (1160, 380, 110, 44, "CAN TX bus 0 (car)", "", "out"),
    "BUSIN": (20, 460, 110, 44, "CAN RX bus 0 and 2", "", "in"),
    "CANRX": (170, 452, 170, 60, "can_rx", "per received frame", "block"),
    "FWD": (390, 382, 180, 56, "safety_fwd_hook", "bus 0 ↔ 2, static block of TX IDs", "block"),
    "RXH": (390, 462, 180, 56, "safety_rx_hook", "RX checks, generic edges", "block"),
    "TOY": (610, 452, 220, 66, "toyota_rx_hook", "decode; EPS fault*, cruise-main*; grant gated by RX checks", "block"),
    "RXQ": (390, 538, 180, 52, "can_push(rx_q)", "→ comms_can_read", "block"),
    "SOCOUT": (1160, 545, 110, 44, "SPI to SoC (CAN stream, health)", "", "out"),
    "STORE": (1160, 230, 110, 70, "controls_allowed", "U-SAF-CORE", "store"),
    "TASK": (170, 645, 430, 52, "safety_task_handler", "safety_tick (RX timeout) · heartbeat monitor (0.3 s → revoke) · IWDG feed", "block"),
    "TICK": (660, 645, 440, 52, "tick_handler", "harness, software watchdog, siren; 1 Hz: heartbeat counter → SILENT, engaged mismatch, check_registers", "block"),
    "LOOP": (170, 748, 430, 34, "hw_watchdog_main_loop_alive, LED fade / WFI", "", "block"),
  },
  "lines": [
    ([(130, 162), (170, 162)], None),
    ([(340, 152), (365, 152), (365, 142), (390, 142)], ("ctrl", 352, 136, "middle")),
    ([(570, 142), (610, 142)], None),
    ([(800, 142), (838, 142), (838, 125), (850, 125)], None),
    ([(838, 142), (838, 185), (850, 185)], None),
    ([(838, 185), (838, 243), (850, 243)], None),
    ([(365, 152), (365, 282), (390, 282)], ("can write", 360, 230, "end")),
    ([(570, 282), (610, 282)], None),
    ([(830, 270), (850, 270), (850, 402), (870, 402)], ("accept", 855, 340, "start")),
    ([(1100, 402), (1160, 402)], None),
    ([(130, 482), (170, 482)], None),
    ([(340, 482), (365, 482), (365, 410), (390, 410)], None),
    ([(570, 410), (590, 410), (590, 392), (870, 392)], ("forward: can_send, hook skipped", 730, 386, "middle")),
    ([(365, 482), (365, 490), (390, 490)], None),
    ([(570, 490), (610, 490)], None),
    ([(365, 490), (365, 564), (390, 564)], None),
    ([(570, 564), (1160, 564)], ("received frames to the SoC", 860, 558, "middle")),
    ([(830, 300), (845, 300), (845, 580), (1140, 580), (1140, 570), (1160, 570)], ("reject: rejected = 1 echo", 990, 594, "middle")),
    ([(1100, 125), (1130, 125), (1130, 245), (1160, 245)], ("W reset", 1135, 160, "start"), "edge thin target"),
    ([(830, 300), (1120, 300), (1120, 260), (1160, 260)], ("W* T11, R", 1000, 294, "middle"), "edge thin target"),
    ([(830, 470), (1150, 470), (1150, 285), (1160, 285)], ("W grant / clear", 1000, 464, "middle"), "edge thin target"),
    ([(600, 671), (625, 671), (625, 612), (1215, 612), (1215, 300)], ("W clear: T5, T10a", 1060, 627, "middle"), "edge thin target"),
    ([(1100, 671), (1240, 671), (1240, 300)], ("W clear: T6", 1180, 665, "middle"), "edge thin target"),
  ],
  "branches": [(365, 152), (838, 142), (838, 185), (365, 482), (365, 490), (830, 300)],
  "desc": ("Panda firmware by execution context: the SPI DMA interrupt handles control requests (mode set, heartbeat, "
           "relay) and SoC CAN frames through the TX hook; the FDCAN interrupts forward frames, run the RX hook and "
           "transmit; the 100 Hz safety task and the 8 Hz tick supervise; the main loop only marks progress. "
           "controls_allowed is shown as a data store with its writers."),
}

# host data flow per control frame (WP-W-03 §4.1, §4.2), superproject 682f184
HOST = {
  "name": "Host engagement data flow", "size": (1420, 540),
  "title": "Host engagement and control data flow (openpilot, superproject 682f184)",
  "sub": ["Simulink-style block diagram generated by diagrams/make_diagrams.py from WP-W-03 §4.1 and §4.2 (rates "
          "from cereal/services.py). Host processes are QM / QM (B-sup); authority on the car is the panda envelope."],
  "foot": "Design description, not verified. Freshness limits at the baseline are in WP-W-03 §4.2; targets in §10.",
  "blocks": {
    "MODELD": (40, 92, 170, 56, "modeld", "driving model (SOTIF / PAS 8800)", "block"),
    "PLANNERD": (340, 92, 170, 56, "plannerd", "longitudinal plan", "block"),
    "CONTROLSD": (600, 190, 180, 70, "controlsd", "lateral and longitudinal control law", "block"),
    "SELFDRIVED": (600, 330, 180, 120, "selfdrived", "Stateflow chart (WP-W-05 §5.3)", "chart"),
    "CARD": (920, 190, 180, 70, "card", "CAN parse → carState; carControl → sendcan", "block"),
    "PANDAD": (920, 330, 180, 76, "pandad", "SPI link, heartbeat, safety-mode set", "block"),
    "PANDA": (1220, 310, 180, 116, "panda safety envelope", "SPI in: CAN frames, 0xf3 heartbeat, 0xdc mode. Subsystem: simulink-envelope.svg, simulink-panda-firmware.svg", "subsys"),
  },
  "lines": [
    ([(210, 120), (340, 120)], ("modelV2 20 Hz", 296, 114, "middle")),
    ([(250, 120), (250, 212), (600, 212)], ("modelV2", 430, 206, "middle")),
    ([(230, 120), (230, 360), (600, 360)], ("modelV2", 430, 354, "middle")),
    ([(510, 120), (560, 120), (560, 230), (600, 230)], ("longitudinalPlan 20 Hz", 516, 112, "start")),
    ([(780, 225), (920, 225)], ("carControl 100 Hz", 850, 219, "middle")),
    ([(1100, 210), (1130, 210), (1130, 168), (580, 168), (580, 246), (600, 246)], ("carState 100 Hz", 855, 162, "middle")),
    ([(1130, 210), (1140, 210), (1140, 300), (575, 300), (575, 380), (600, 380)], ("carState", 855, 294, "middle")),
    ([(780, 380), (810, 380), (810, 285), (565, 285), (565, 254), (600, 254)], ("selfdriveState 100 Hz", 690, 279, "middle")),
    ([(810, 380), (830, 380), (830, 350), (920, 350)], ("selfdriveState", 875, 366, "middle")),
    ([(1100, 240), (1115, 240), (1115, 318), (900, 318), (900, 340), (920, 340)], ("sendcan 100 Hz", 1010, 312, "middle")),
    ([(1100, 350), (1220, 350)], ("SPI", 1160, 344, "middle")),
    ([(1400, 395), (1410, 395), (1410, 470), (905, 470), (905, 385), (920, 385)], ("health 10 Hz", 1160, 464, "middle")),
    ([(1100, 395), (1120, 395), (1120, 490), (570, 490), (570, 430), (600, 430)], ("pandaStates 10 Hz", 845, 484, "middle")),
  ],
  "branches": [(250, 120), (230, 120), (1130, 210), (810, 380)],
  "desc": ("Host data flow: modeld feeds plannerd, controlsd and selfdrived; card publishes carState and turns "
           "carControl into sendcan; selfdrived publishes selfdriveState to controlsd and pandad; pandad talks to the "
           "panda over SPI and returns pandaStates to selfdrived."),
}


# ------------------------------------------------------------------ main

def outputs() -> dict[str, str]:
  sw = csm.swsr_records()
  out = {}
  for p in sorted(csm.SM_DIR.glob("*.yaml")):
    sm = csm.load(p)
    out[f"stateflow-{p.stem}.svg"] = stateflow(sm, sw, p.name)
  out["simulink-envelope.svg"] = render_blocks(ENVELOPE)
  out["simulink-panda-firmware.svg"] = render_blocks(PANDA)
  out["simulink-host.svg"] = render_blocks(HOST)
  return out


def main(argv: list[str]) -> int:
  stale = []
  for name, content in outputs().items():
    path = HERE / name
    if "--check" in argv:
      if not path.exists() or path.read_text(encoding="utf-8") != content:
        stale.append(name)
    else:
      path.write_text(content, encoding="utf-8")
      print(f"wrote {path.relative_to(HERE.parents[2])}")
  if stale:
    print("FAIL: out of date: " + ", ".join(stale) + "; run assurance/05-software/diagrams/make_diagrams.py")
    return 1
  if "--check" in argv:
    print("OK: diagrams current")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
