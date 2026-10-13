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
  "SM-TOY-AUTH": {"size": (900, 330), "states": {"NOT_ALLOWED": (220, 175), "ALLOWED": (680, 175)}},
  "SM-SAFETY-MODE": {"size": (900, 510), "junction": (450, 285), "bend": {("ELM327", "SILENT"): -24},
                     "states": {"SILENT": (150, 150), "NOOUTPUT": (450, 130), "ELM327": (750, 150),
                                "TOYOTA": (270, 430), "OTHER_CAR": (630, 430)}},
  "SM-SELFDRIVED": {"size": (900, 520),
                    "states": {"disabled": (140, 300), "preEnabled": (310, 110), "enabled": (520, 300),
                               "overriding": (770, 130), "softDisabling": (770, 450)}},
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
      cls = "edge" if impl else "edge target"
      body.append(f'<path class="{cls}" d="M{p0[0]:.1f},{p0[1]:.1f} Q{ctrl[0]:.1f},{ctrl[1]:.1f} {p1[0]:.1f},{p1[1]:.1f}"/>')
      e = quad(p0, ctrl, p1, 0.97)
      body.append(K.arrowhead(p1[0], p1[1], p1[0] - e[0], p1[1] - e[1], "arrow" if impl else "arrow target"))
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
      cls = "edge" if impl else "edge target"
      body.append(f'<path class="{cls}" d="M{x0:.1f},{top:.1f} C{x0:.1f},{top - 2.2 * r:.1f} {x1:.1f},{top - 2.2 * r:.1f} {x1:.1f},{top:.1f}"/>')
      body.append(K.arrowhead(x1, top, 0, 1, "arrow" if impl else "arrow target"))
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

  # states and default transition
  for st in sm["states"]:
    cx, cy = pos[st]
    w, h = size[st]
    body.append(f'<rect class="shadow" x="{cx - w / 2 + 3:.1f}" y="{cy - h / 2 + 3:.1f}" width="{w:.1f}" height="{h:.1f}" rx="12"/>')
    body.append(f'<rect class="box" x="{cx - w / 2:.1f}" y="{cy - h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="12"/>')
    body.append(K.text(cx - w / 2 + 10, cy - h / 2 + 18, st, "tb"))
  ix, iy = pos[sm["initial"]]
  w, h = size[sm["initial"]]
  sx = ix - w / 2 - 46
  body.append(f'<circle class="dot" cx="{sx:.1f}" cy="{iy:.1f}" r="4"/>')
  body.append(f'<path class="edge" d="M{sx:.1f},{iy:.1f} L{ix - w / 2:.1f},{iy:.1f}"/>')
  body.append(K.arrowhead(ix - w / 2, iy, 1, 0))

  # header
  head = [K.text(20, 26, f"{name}: {sm['title']}", "th"),
          K.text(20, 44, f"Stateflow-style chart generated from state-machines/{record} by diagrams/make_diagrams.py.", "ts"),
          K.text(20, 58, "Solid: in the code. Dashed: not in the code (target state). "
                 "Status column: WP-W-02 Baseline of the cited SWSRs.", "ts")]

  # transition table
  y = H0 + 10
  rows = [K.text(20, y, "Transitions (Stateflow label notation: event [guard] / {action})", "tb")]
  y += 10
  col = (20, 70, 640, 720)
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
  "TICK": (440, 280, 210, 60, "safety_tick (100 Hz)", "UN-05, UN-37: RX timeout 5 periods, invalid check", "block"),
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
  ([(650, 310), (800, 310)], ("lagging: T5", 725, 304, "middle")),
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


def simulink() -> str:
  W, H = 1180, 660
  body = [K.text(20, 26, "Safety envelope signal flow (reference build)", "th"),
          K.text(20, 44, "Simulink-style block diagram generated by diagrams/make_diagrams.py; blocks cite the "
                 "WP-W-05 units at the WP-W-05 baseline. * reference build only (LIONDRIVER_REFERENCE=1).", "ts"),
          K.text(20, 642, "Design description, not verified. The authority chart is WP-W-05 §5.2 "
                 "(stateflow-sm-toy-auth.svg); transition IDs on the lines refer to it.", "ts")]
  lines_svg = []
  for pts, (lab, lx, ly, anchor) in LINES:
    d = "M" + " L".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
    lines_svg.append(f'<path class="edge" d="{d}"/>')
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    lines_svg.append(K.arrowhead(x1, y1, x1 - x0, y1 - y0))
    lines_svg.append(K.text(lx, ly, lab, "tm", anchor))
  for bx, by in BRANCHES:
    lines_svg.append(f'<circle class="dot" cx="{bx}" cy="{by}" r="3"/>')
  blocks_svg = []
  for bid, (x, y, w, h, title, sub, kind) in BLOCKS.items():
    if kind in ("in", "out"):
      blocks_svg.append(f'<rect class="box" x="{x}" y="{y}" width="{w}" height="{h}" rx="14"/>')
      blocks_svg.append(K.text(x + w / 2, y + h / 2 + 4, title, "t", "middle"))
      continue
    dash = ' stroke-dasharray="5 3"' if kind == "ref" else ""
    blocks_svg.append(f'<rect class="shadow" x="{x + 3}" y="{y + 3}" width="{w}" height="{h}"/>')
    blocks_svg.append(f'<rect class="box" x="{x}" y="{y}" width="{w}" height="{h}"{dash}/>')
    ty = y + h / 2 - 8 if kind == "chart" else y + 18
    blocks_svg.append(K.text(x + w / 2, ty, title, "tb", "middle"))
    for i, ln in enumerate(K.wrap(sub, w - 16)):
      blocks_svg.append(K.text(x + w / 2, ty + 16 + 13 * i, ln, "ts", "middle"))
    if kind == "chart":  # small Stateflow glyph
      gx, gy = x + w / 2 - 34, ty + 50
      blocks_svg += [f'<rect class="box" x="{gx}" y="{gy}" width="26" height="16" rx="5"/>',
                     f'<rect class="box" x="{gx + 42}" y="{gy}" width="26" height="16" rx="5"/>',
                     f'<path class="edge" d="M{gx + 26},{gy + 8} L{gx + 42},{gy + 8}"/>',
                     K.arrowhead(gx + 42, gy + 8, 1, 0, size=5)]
  desc = ("Block diagram: CAN RX frames pass the RX checks and the Toyota RX hook; decoded signals, the 100 Hz safety "
          "tick, the heartbeat monitor and mode changes drive the authority chart; SoC TX frames pass the whitelist, "
          "the rate check and the Toyota TX limits, which also need controls_allowed, before CAN TX.")
  return K.doc(W, H, "Safety envelope block diagram", desc, body + lines_svg + blocks_svg)


# ------------------------------------------------------------------ main

def outputs() -> dict[str, str]:
  sw = csm.swsr_records()
  out = {}
  for p in sorted(csm.SM_DIR.glob("*.yaml")):
    sm = csm.load(p)
    out[f"stateflow-{p.stem}.svg"] = stateflow(sm, sw, p.name)
  out["simulink-envelope.svg"] = simulink()
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
