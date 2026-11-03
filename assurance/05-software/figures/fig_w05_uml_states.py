#!/usr/bin/env python3
"""Draw WP-W-05 Figures 5-1 to 5-3: the record state machines as UML state machine diagrams, and one walk through
the Toyota authority machine as an animation.

  fig-w05-5-1-uml-sm-toy-auth.svg     SM-TOY-AUTH (controls_allowed), WP-W-05 §5.2
  fig-w05-5-2-uml-sm-selfdrived.svg   SM-SELFDRIVED (host engagement), WP-W-05 §5.3
  fig-w05-5-3-toy-auth-walk.svg       SM-TOY-AUTH, animated: engagement through the 1 s window, then a heartbeat loss

UML notation: each machine is a state machine frame (stm) holding its states; the initial pseudostate points at the
initial state; a transition from "any" state leaves the frame's border, which in UML applies to every substate; a
transition to the same state is a self-loop. Transitions between the same two states share one arrow, labelled with
their IDs; each ID chip is coloured by the status WP-W-05 §5 gives it (check_state_machines.transition_state, from the
WP-W-02 Baseline column of the SWSRs it realises), and dashed when only the reference build has it. The table under
each diagram gives every transition as event [guard] / action, clipped to one line; the record is normative.

Where each part comes from: assurance/05-software/state-machines/*.yaml (states, initial state, transitions), read
with check_state_machines.load; the statuses from trace/items/swsr.yaml through check_state_machines. Hand-placed:
the position of each state (POS) and the walk of the animation (WALK), whose transitions must chain from the initial
state. The build fails if a state has no position, a transition names an unknown state, or the walk does not chain.

    python3 fig_w05_uml_states.py            # write the SVGs
    python3 fig_w05_uml_states.py --check    # fail if the records changed shape or an SVG is stale

Standard library only (PyYAML if present, through check_state_machines). Output is deterministic.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSURANCE = HERE.parents[1]
sys.path.insert(0, str(ASSURANCE / "01-management" / "figures"))
from figkit import (INK, MUTED, FAINT, LINE, HAIR, SW, SW_BG, GREEN, GREEN_BG, AMBER, AMBER_BG, RED, RED_BG,  # noqa: E402
                    GREY_BG, FigureError, text, rect, line, path, svg, header, pill, fit, text_w)
sys.path.insert(0, str(ASSURANCE / "trace" / "tools"))
import terms  # noqa: E402
import check_state_machines as csm  # noqa: E402

W = 1280
SW_, SH = 200, 60
STATUS = {"impl": ("implemented", GREEN, GREEN_BG), "partial": ("partly", AMBER, AMBER_BG),
          "not": ("not implemented", RED, RED_BG), "unknown": ("not assessed", MUTED, GREY_BG)}
# Placement only: the centre of each state, per machine.
POS = {
  "SM-TOY-AUTH": {"NOT_ALLOWED": (300, 430), "ENGAGE_PENDING": (640, 196), "ALLOWED": (980, 430)},
  "SM-SELFDRIVED": {"disabled": (230, 360), "preEnabled": (590, 196), "enabled": (950, 360), "overriding": (590, 520),
                    "softDisabling": (1080, 560)},
}
FIGS = [("SM-TOY-AUTH", "5-1", "fig-w05-5-1-uml-sm-toy-auth.svg", "§5.2"),
        ("SM-SELFDRIVED", "5-2", "fig-w05-5-2-uml-sm-selfdrived.svg", "§5.3")]
ANIM = ("SM-TOY-AUTH", "5-3", "fig-w05-5-3-toy-auth-walk.svg", "§5.2")
# The walk of the animation: transition IDs in order, from the initial state.
WALK = ["T1a", "T1b", "T10a"]
PERIOD = 4.0


def machines() -> dict[str, dict]:
  sw = csm.swsr_records()
  out = {}
  for p in sorted(csm.SM_DIR.glob("*.yaml")):
    sm = csm.load(p)
    for t in sm["transitions"]:
      t["status"] = csm.transition_state(t, sw)
    sm["file"] = p.name
    out[sm["machine"]] = sm
  return out


def edges(sm: dict) -> list[dict]:
  """One edge per (source, target) pair: source/target a state, '*' for the frame (any state)."""
  states = sm["states"]
  pairs: dict[tuple[str, str], list[dict]] = {}
  for t in sm["transitions"]:
    src = str(t["from"])
    sources = ["*"] if src == "any" else [x.strip() for x in src.split(",")]
    dst = str(t["to"])
    for s in sources:
      if s != "*" and s not in states:
        raise FigureError(f"{sm['machine']} {t['id']}: source {s!r} is not a state")
      if dst == "same":
        targets = [s]
      elif dst == "m":
        named = [x for x in states if re.search(rf"\b{re.escape(x)}\b", str(t.get("guard", "")))]
        targets = named or ["*"]
      elif dst in states:
        targets = [dst]
      else:
        raise FigureError(f"{sm['machine']} {t['id']}: target {dst!r} is not a state")
      for d in targets:
        pairs.setdefault((s, d), []).append(t)
  return [{"src": s, "dst": d, "ts": ts} for (s, d), ts in pairs.items()]


def box_point(c, toward, w=SW_, h=SH):
  """Where the line from the centre c toward a point leaves the state box."""
  dx, dy = toward[0] - c[0], toward[1] - c[1]
  if dx == 0 and dy == 0:
    return c
  sx = (w / 2) / abs(dx) if dx else math.inf
  sy = (h / 2) / abs(dy) if dy else math.inf
  s = min(sx, sy)
  return (c[0] + dx * s, c[1] + dy * s)


def arrowhead(x, y, ang, col) -> str:
  a1, a2 = ang + math.radians(152), ang - math.radians(152)
  return path(f"M{x:.1f} {y:.1f} L{x + 9 * math.cos(a1):.1f} {y + 9 * math.sin(a1):.1f} "
              f"L{x + 9 * math.cos(a2):.1f} {y + 9 * math.sin(a2):.1f} Z", stroke="none", fill=col)


def chips(x, y, ts, per_row=6, center=True) -> list[str]:
  out = []
  rows = [ts[i:i + per_row] for i in range(0, len(ts), per_row)]
  for r_i, row in enumerate(rows):
    ws = [text_w(t["id"], 9, True) + 12 for t in row]
    xx = x - (sum(ws) + 3 * (len(row) - 1)) / 2 if center else x
    for t, w in zip(row, ws, strict=True):
      _, col, bg = STATUS[t["status"]]
      p, _ = pill(xx, y + r_i * 18, t["id"], bg, col, h=15, size=9, stroke=col,
                  dash="3 2" if t.get("build") == "reference" else "")
      out += p
      xx += w + 3
  return out


def diagram(sm: dict, frame: tuple[float, float, float, float], active: str | None = None,
            fired: str | None = None) -> list[str]:
  pos = POS[sm["machine"]]
  for s in sm["states"]:
    if s not in pos:
      raise FigureError(f"{sm['machine']}: no position for state {s}")
  fx, fy, fw, fh = frame
  out = [rect(fx, fy, fw, fh, fill="#FFFFFF", stroke=INK, rx=18, sw=1.4)]
  tab = f"stm {sm['machine']} · {sm['title']}"
  tw = text_w(tab, 11, True) + 24
  out.append(path(f"M{fx} {fy + 18} L{fx} {fy} L{fx + tw} {fy} L{fx + tw} {fy + 14} L{fx + tw - 12} {fy + 26} L{fx} {fy + 26}",
                  stroke=INK, sw=1.2, fill="#F8FAFC"))
  out.append(text(fx + 10, fy + 17, tab, size=11, weight=700))
  es = edges(sm)
  pairset = {(e["src"], e["dst"]) for e in es}
  hot = INK
  for e in es:
    s, d = e["src"], e["dst"]
    lit = fired is not None and any(t["id"] == fired for t in e["ts"])
    col, sw = (SW, 3) if lit else (MUTED, 1.4)
    if s == "*" and d == "*":                                   # frame to frame: any state to any state
      x, y = fx + fw - 30, fy
      out.append(path(f"M{x - 60} {y} C{x - 60} {y - 34} {x + 10} {y - 34} {x + 10} {y}", stroke=col, sw=sw))
      out.append(arrowhead(x + 10, y, math.pi / 2, col))
      out += chips(x - 25, y - 54, e["ts"])
      continue
    if s == "*":                                                # any state: from the frame's bottom border
      c = pos[d]
      x0 = c[0] - 40
      out.append(line(x0, fy + fh, x0, c[1] + SH / 2 + 2, stroke=col, sw=sw))
      out.append(arrowhead(x0, c[1] + SH / 2 + 2, -math.pi / 2, col))
      out += chips(x0 + 8, fy + fh - 24, e["ts"], center=False)
      continue
    if s == d:                                                  # self-loop above the state
      c = pos[s]
      x1, x2, y = c[0] - 30, c[0] + 30, c[1] - SH / 2
      out.append(path(f"M{x1} {y} C{x1 - 10} {y - 52} {x2 + 10} {y - 52} {x2} {y}", stroke=col, sw=sw))
      out.append(arrowhead(x2, y, math.radians(100), col))
      out += chips(c[0], y - 64, e["ts"])
      continue
    a, b = pos[s], pos[d]
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    off = 12 if (d, s) in pairset else 0
    nx, ny = -math.sin(ang) * off, math.cos(ang) * off
    p1 = box_point(a, b)
    p2 = box_point(b, a)
    p1, p2 = (p1[0] + nx, p1[1] + ny), (p2[0] + nx, p2[1] + ny)
    out.append(line(p1[0], p1[1], p2[0], p2[1], stroke=col, sw=sw))
    out.append(arrowhead(p2[0], p2[1], ang, col))
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    side = 1 if off >= 0 else -1
    lx, ly = mx + nx * 1.6 * side, my + ny * 1.6 * side
    rows = (len(e["ts"]) + 5) // 6
    ly += (8 if ny >= 0 else -10 - 18 * (rows - 1))
    out += chips(lx, ly - 8, e["ts"])
  # initial pseudostate
  c0 = pos[sm["initial"]]
  ix = c0[0] - SW_ / 2 - 70
  out.append(f'<circle cx="{ix}" cy="{c0[1]}" r="8" fill="{INK}"/>')
  out.append(line(ix + 8, c0[1], c0[0] - SW_ / 2 - 2, c0[1], stroke=INK, sw=1.4))
  out.append(arrowhead(c0[0] - SW_ / 2 - 2, c0[1], 0, INK))
  for s in sm["states"]:
    c = pos[s]
    on = active == s
    out.append(rect(c[0] - SW_ / 2, c[1] - SH / 2, SW_, SH, fill=SW_BG if on else "#FFFFFF", stroke=SW if on else INK,
                    rx=16, sw=2.6 if on else 1.5))
    out.append(text(c[0], c[1] + 5, s, size=12.5, weight=700, anchor="middle", fill=SW if on else INK))
  return out


def footer(out: list[str], sm: dict, y: float) -> tuple[list[str], float]:
  """The definitions line, read without the elements that show a transition ID: E1, P1, D1 are IDs of the record,
  not exposure classes or priorities."""
  ids = re.compile(r"(?<![\w-])(" + "|".join(re.escape(t["id"]) for t in sm["transitions"]) + r")(?![\w])")
  return terms.svg_footer([e for e in out if not ids.search(re.sub(r"<[^>]+>", " ", e))], 40, y, W - 80)


def legend_row(y: float) -> list[str]:
  out, x = [], 40
  for k, (label, col, bg) in STATUS.items():
    p, w = pill(x, y - 11, "T", bg, col, h=15, size=9, stroke=col)
    out += p
    out.append(text(x + w + 6, y, label, size=10.5, fill=MUTED))
    x += w + 16 + text_w(label, 10.5)
  p, w = pill(x, y - 11, "T", "#FFFFFF", MUTED, h=15, size=9, stroke=MUTED, dash="3 2")
  out += p
  out.append(text(x + w + 6, y, "reference build only", size=10.5, fill=MUTED))
  x += w + 26 + text_w("reference build only", 10.5)
  out.append(text(x, y, "status as WP-W-05 §5 gives it, from the SWSRs each transition realises", size=10.5, fill=FAINT))
  return out


def transition_table(sm: dict, y: float) -> tuple[list[str], float]:
  out = [text(40, y, "Transitions (the record is normative; WP-W-05 " + ("§5.2" if sm["machine"] == "SM-TOY-AUTH" else "§5.3")
              + " has them in full)", size=12, weight=700)]
  y += 20
  for x, h in ((40, "ID"), (100, "From → to"), (380, "Event [guard] / action"), (1110, "Build"), (1180, "Status")):
    out.append(text(x, y, h, size=10, weight=700, fill=MUTED))
  y += 6
  for t in sm["transitions"]:
    y += 17
    label, col, _ = STATUS[t["status"]]
    out.append(text(40, y, t["id"], size=10, weight=700, fill=col))
    out.append(text(100, y, fit(f"{t['from']} → {t['to']}", 270, 10), size=10))
    g = str(t.get("guard") or "").strip()
    a = str(t.get("action") or "").strip()
    desc = f"{t.get('event', '')}" + (f" [{g}]" if g else "") + (f" / {a}" if a and a != "none" else "")
    out.append(text(380, y, fit(desc, 720, 10), size=10))
    out.append(text(1110, y, str(t.get("build", "")), size=10, fill=MUTED))
    out.append(text(1180, y, label, size=10, fill=col))
  return out, y + 12


def static_figure(sm: dict, num: str, ref: str) -> str:
  counts = {k: sum(t["status"] == k for t in sm["transitions"]) for k in STATUS}
  out = header(W, num, f"{sm['machine']} as a UML state machine",
               f"{sm['title']}: {len(sm['states'])} states, {len(sm['transitions'])} transitions; {counts['impl']} "
               f"implemented, {counts['partial']} partly, {counts['not']} not implemented", f"WP-W-05 {ref}")
  fy = 120
  fh = (max(c[1] for c in POS[sm["machine"]].values()) + SH / 2 + 70) - fy
  out += diagram(sm, (40, fy, W - 80, fh))
  y = fy + fh + 30
  out += legend_row(y)
  tab, y = transition_table(sm, y + 30)
  out += tab
  out.append(text(40, y + 6, f"Generated by fig_w05_uml_states.py from state-machines/{sm['file']}; nothing is "
                  "hand-listed but the positions of the states.", size=10.5, fill=MUTED))
  extra, y = footer(out, sm, y + 28)
  out += extra
  desc = f"UML state machine of {sm['machine']}: " + " ".join(
    f"{t['id']} {t['from']} to {t['to']} ({STATUS[t['status']][0]})." for t in sm["transitions"])
  return svg(W, int(y + 12), f"Figure {num}. {sm['machine']} as a UML state machine (WP-W-05)", desc, out)


def walk(sm: dict) -> list[dict]:
  by = {t["id"]: t for t in sm["transitions"]}
  state, steps = sm["initial"], []
  for tid in WALK:
    t = by.get(tid)
    if t is None:
      raise FigureError(f"{sm['machine']}: the walk names {tid}, which is not a transition")
    srcs = sm["states"] if t["from"] == "any" else [x.strip() for x in str(t["from"]).split(",")]
    if state not in srcs:
      raise FigureError(f"{sm['machine']}: the walk fires {tid} from {state}, but it leaves {t['from']}")
    steps.append({"from": state, "t": t, "to": state if t["to"] == "same" else t["to"]})
    state = steps[-1]["to"]
  return steps


def anim_figure(sm: dict, num: str, ref: str) -> str:
  steps = walk(sm)
  n = len(steps) + 1
  total = PERIOD * n
  out = header(W, num, f"{sm['machine']}, animated: engage, then lose the heartbeat",
               f"A walk through the record: {' → '.join([sm['initial']] + [s['to'] for s in steps])}, firing "
               f"{', '.join(WALK)}; {PERIOD:g} s per step", f"WP-W-05 {ref}")
  css = [f".fr{{opacity:0;animation:{total:g}s steps(1,end) infinite}}"]
  for i in range(n):
    a, b = 100 * i / n, 100 * (i + 1) / n
    css.append(f"@keyframes k{i}{{0%{{opacity:{1 if i == 0 else 0}}}{a:.2f}%{{opacity:1}}{b:.2f}%{{opacity:0}}"
               f"100%{{opacity:{1 if i == 0 else 0}}}}}.f{i}{{animation-name:k{i}}}")
  css.append(f"@media (prefers-reduced-motion:reduce){{.fr{{animation:none}}.f{n - 1}{{opacity:1}}}}")
  out.append(f"<style>{''.join(css)}</style>")
  fy = 120
  fh = (max(c[1] for c in POS[sm["machine"]].values()) + SH / 2 + 70) - fy
  frames = [(sm["initial"], None, None)] + [(s["to"], s["t"]["id"], s) for s in steps]
  for i, (active, fired, st) in enumerate(frames):
    g = [f'<g class="fr f{i}">'] + diagram(sm, (40, fy, W - 80, fh), active, fired)
    by = fy + fh + 24
    g.append(rect(40, by, W - 80, 92, fill=SW_BG if fired else "#F8FAFC", stroke=SW if fired else LINE, rx=10))
    g += pill(56, by + 14, f"{i + 1} / {n}", INK, h=18, size=10)[0]
    if st is None:
      g.append(text(108, by + 27, f"Start: {active}", size=13, weight=700))
      g.append(text(56, by + 54, "After a safety mode is set, authority is not granted; the envelope waits for a cruise "
                    "edge from the car.", size=11.5))
    else:
      t = st["t"]
      g.append(text(108, by + 27, f"{t['id']}: {st['from']} → {st['to']} on {t.get('event', '')}", size=13, weight=700))
      g.append(text(56, by + 52, fit(f"[{t.get('guard') or 'no guard'}]", W - 112, 10.5), size=10.5))
      g.append(text(56, by + 72, fit(f"/ {t.get('action')} · build {t.get('build')} · {', '.join(t.get('swsr', []))} · "
                                     f"{STATUS[t['status']][0]}", W - 112, 10.5), size=10.5, fill=MUTED))
    g.append("</g>")
    out += g
  y = fy + fh + 24 + 92 + 26
  out += legend_row(y)
  y += 22
  out.append(text(40, y, f"Generated by fig_w05_uml_states.py from state-machines/{sm['file']}; the walk ({', '.join(WALK)}) "
                  "is chosen here and checked to chain from the initial state.", size=10.5, fill=MUTED))
  extra, y = footer(out, sm, y + 22)
  out += extra
  desc = f"Animated walk through {sm['machine']}: " + " ".join(
    f"{s['t']['id']} from {s['from']} to {s['to']} on {s['t'].get('event', '')}." for s in steps)
  return svg(W, int(y + 12), f"Figure {num}. {sm['machine']}, animated (WP-W-05)", desc, out)


def build() -> dict[str, str]:
  ms = machines()
  out = {}
  for machine, num, name, ref in FIGS:
    if machine not in ms:
      raise FigureError(f"no state-machine record {machine}")
    out[name] = static_figure(ms[machine], num, ref)
  machine, num, name, ref = ANIM
  out[name] = anim_figure(ms[machine], num, ref)
  return out


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except FigureError as e:
    print(f"fig_w05_uml_states: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n_ for n_, c in outputs.items() if not (HERE / n_).exists() or (HERE / n_).read_text(encoding="utf-8") != c]
    for n_ in stale:
      print(f"assurance/05-software/figures/{n_} is stale; run fig_w05_uml_states.py", file=sys.stderr)
    if not stale:
      print(f"fig_w05_uml_states: {len(outputs)} figures current")
    return 1 if stale else 0
  for n_, c in outputs.items():
    (HERE / n_).write_text(c, encoding="utf-8")
    print(f"wrote assurance/05-software/figures/{n_}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
