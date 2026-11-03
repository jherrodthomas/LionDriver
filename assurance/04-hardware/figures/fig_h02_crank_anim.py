#!/usr/bin/env python3
"""Draw WP-H-02 Figure 3-8, the cranking dip through the device's power path as an animated circuit
(fig-h02-3-8-crank-anim.svg).

Top, the power path of the 12 V supply study: the car's supply, the harness, the reverse-polarity Schottky with the
hold-up capacitance, the buck to 5 V with its under-voltage lockout, the regulator to 3.3 V, and the panda MCU with
its reset thresholds. Each node shows its voltage, stepping with the cursor. Middle, the ngspice traces of ISO 16750-2
starting profile level II for the nominal circuit: the car, the device input, the 5 V rail and the MCU rail against
the MCU's thresholds, with a cursor sweeping 0 to 120 ms. Bottom, every level and circuit variant of the study with its
outcome.

Where each part comes from:
  traces, thresholds   assurance/sim/results/crank-dip.json (supply/crank.py, ngspice 41): levels.II.trace and
                       thresholds; the trace must reach the nominal variant's minima
  outcome grid         the table of assurance/sim/results/crank-dip.md: Level, Circuit and Outcome per row
  MCU state            from the MCU rail against the thresholds: above BOR3 running; between the rated minimum and
                       BOR3 it would reset if BOR were configured (it is not, HWSR-505); below the rated minimum it is
                       not specified; below PDR the power-down reset holds it
The build fails if a level, a threshold, a column or an outcome word is missing. CSS animation only; with reduced
motion the cursor rests at the bottom of the dip. Synthetic data, no evidence credit (DQ-413).

    python3 fig_h02_crank_anim.py            # write the SVG
    python3 fig_h02_crank_anim.py --check    # fail if the sources changed shape or the SVG is stale

Standard library only. Output is deterministic.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSURANCE = HERE.parents[1]
sys.path.insert(0, str(ASSURANCE / "01-management" / "figures"))
from figkit import (INK, MUTED, FAINT, LINE, HAIR, SAFETY, HW, HW_BG, GREEN, GREEN_BG, AMBER, AMBER_BG, RED,  # noqa: E402
                    RED_BG, GREY_BG, FigureError, text, rect, line, path, svg, header, pill, fit, section, table, col,
                    plain)
sys.path.insert(0, str(ASSURANCE / "trace" / "tools"))
import terms  # noqa: E402

RESULTS = ASSURANCE / "sim" / "results" / "crank-dip.json"
TABLE = ASSURANCE / "sim" / "results" / "crank-dip.md"
OUT = "fig-h02-3-8-crank-anim.svg"
W = 1280
LEVEL = "II"
T_END = 0.12                      # seconds shown
STEPS = 24                        # value steps along the sweep
LOOP = 9.0                        # seconds per sweep
OUTCOME = {"rides through": (GREEN, GREEN_BG), "resets, restarts at US": (RED, RED_BG)}
SERIES = [("car", "car supply", MUTED), ("vin", "device input", HW), ("v5", "5 V rail", SAFETY), ("v33", "MCU rail", INK)]


def load() -> tuple[dict, dict, list[tuple[str, str, str]]]:
  d = json.loads(RESULTS.read_text(encoding="utf-8"))
  th = d.get("thresholds") or {}
  for k in ("pdr", "bor1", "bor2", "bor3", "vdd_min"):
    if k not in th:
      raise FigureError(f"crank-dip.json: no threshold {k}")
  lv = d["levels"].get(LEVEL)
  if lv is None:
    raise FigureError(f"crank-dip.json: no level {LEVEL}")
  tr, nom = lv["trace"], lv["variants"]["nominal"]
  for k, *_ in SERIES:
    if len(tr.get(k, [])) != len(tr["t"]):
      raise FigureError(f"crank-dip.json level {LEVEL}: trace {k} missing or of the wrong length")
  for k, m in (("vin", "vin_min"), ("v5", "v5_min"), ("v33", "v33_min")):
    if abs(min(tr[k]) - nom[m]) > 0.01:
      raise FigureError(f"level {LEVEL} trace {k} reaches {min(tr[k])}, not the nominal {m} {nom[m]}")
  head, rows = table(section(TABLE.read_text(encoding="utf-8"), "# 12 V cranking dip"), "Level (US6 → US)")
  li, ci, oi = col(head, "Level (US6 → US)"), col(head, "Circuit"), col(head, "Outcome")
  grid = []
  for r in rows:
    o = plain(r[oi])
    if o not in OUTCOME:
      raise FigureError(f"crank-dip.md: outcome {o!r} is not one of {list(OUTCOME)}")
    grid.append((plain(r[li]), plain(r[ci]), o))
  if not grid:
    raise FigureError("crank-dip.md: empty table")
  return {"tr": tr, "nom": nom, "about": d["about"]}, th, grid


def at(tr: dict, t: float) -> int:
  return min(range(len(tr["t"])), key=lambda i: abs(tr["t"][i] - t))


def mcu_state(v: float, th: dict) -> tuple[str, str, str]:
  if v >= th["bor3"]:
    return "running", GREEN, GREEN_BG
  if v >= th["vdd_min"]:
    return "below BOR3: no reset, BOR not set", AMBER, AMBER_BG
  if v >= th["pdr"]:
    return "below rated minimum: not specified", RED, RED_BG
  return "power-down reset", RED, RED_BG


def figure(data: dict, th: dict, grid: list[tuple[str, str, str]]) -> str:
  tr = data["tr"]
  out = header(W, "3-8", "Cranking dip through the power path, animated",
               f"ngspice, ISO 16750-2 starting profile level {LEVEL}, nominal generic circuit: each node's voltage and "
               "the MCU's state as the car's supply dips", "WP-H-02 §3.4 · HWSR-505")
  # the sweep: cursor and stepped values
  ts = [T_END * k / STEPS for k in range(STEPS + 1)]
  low = min(range(len(tr["t"])), key=lambda i: (tr["v33"][i], tr["t"][i]))
  keep = min(range(len(ts)), key=lambda k: abs(ts[k] - tr["t"][low]))
  css = [f".st{{opacity:0;animation:{LOOP:g}s steps(1,end) infinite}}"]
  for k in range(len(ts)):
    a, b = 100 * k / len(ts), 100 * (k + 1) / len(ts)
    css.append(f"@keyframes s{k}{{0%{{opacity:{1 if k == 0 else 0}}}{a:.2f}%{{opacity:1}}{b:.2f}%{{opacity:0}}"
               f"100%{{opacity:{1 if k == 0 else 0}}}}}.s{k}{{animation-name:s{k}}}")
  x0, x1 = 120, W - 60
  css.append(f"@keyframes cur{{0%{{transform:translateX(0)}}{100 * STEPS / (STEPS + 1):.2f}%{{transform:translateX("
             f"{x1 - x0}px)}}100%{{transform:translateX({x1 - x0}px)}}}}"
             f".cur{{animation:cur {LOOP:g}s linear infinite}}")
  css.append(f"@media (prefers-reduced-motion:reduce){{.st{{animation:none}}.s{keep}{{opacity:1}}"
             f".cur{{animation:none;transform:translateX({(x1 - x0) * ts[keep] / T_END:.1f}px)}}}}")
  out.append(f"<style>{''.join(css)}</style>")

  # ---------------------------------------------------------------- power path chain
  y = 104
  nodes = [("car 12 V", "ISO 16750-2", "car"), ("harness", "wiring, fuse", None), ("Schottky + hold-up C", "device input",
           "vin"), ("buck to 5 V", "under-voltage lockout", "v5"), ("regulator 3.3 V", "MCU rail", "v33"),
           ("STM32H725", "BOR, PDR thresholds", None)]
  bw, gap = 170, 26
  bx = [40 + i * (bw + gap) for i in range(len(nodes))]
  for i, (name, sub, key) in enumerate(nodes):
    hw = name.startswith("STM32")
    out.append(rect(bx[i], y, bw, 74, fill=HW_BG if hw else "#FFFFFF", stroke=HW if hw else LINE, rx=8))
    out.append(text(bx[i] + 10, y + 20, name, size=11.5, weight=700))
    out.append(text(bx[i] + 10, y + 35, sub, size=9.5, fill=MUTED))
    if i < len(nodes) - 1:
      ax = bx[i] + bw
      out.append(line(ax, y + 37, ax + gap - 4, y + 37, stroke=MUTED, sw=1.6))
      out.append(path(f"M{ax + gap - 4} {y + 33} l5 4 -5 4z", stroke="none", fill=MUTED))
  for k, t in enumerate(ts):
    i = at(tr, t)
    g = [f'<g class="st s{k}">']
    for j, (_, _, key) in enumerate(nodes):
      if key:
        c = next(cl for kk, _, cl in SERIES if kk == key)
        g.append(text(bx[j] + 10, y + 62, f"{tr[key][i]:.2f} V", size=16, weight=700, fill=c))
    state, c, bg = mcu_state(tr["v33"][i], th)
    g += pill(bx[-1] + 10, y + 46, fit(state, bw - 20, 9.5, True), c, h=18, size=9.5)[0]
    g.append(text(W - 40, y + 98, f"t = {t * 1000:.0f} ms", size=11, weight=700, anchor="end"))
    g.append("</g>")
    out += g

  # ---------------------------------------------------------------- traces
  panels = [("car supply and device input", ("car", "vin"), 15.0), ("5 V rail", ("v5",), 6.0),
            ("MCU rail and its thresholds", ("v33",), 4.0)]
  py, ph = 248, 110
  xs = lambda t: x0 + (x1 - x0) * t / T_END  # noqa: E731
  n = at(tr, T_END) + 1
  for title, keys, vmax in panels:
    ys = lambda v, py=py, vmax=vmax: py + ph - ph * max(0.0, min(v, vmax)) / vmax  # noqa: E731
    out.append(rect(x0, py, x1 - x0, ph, fill="#FFFFFF", stroke=HAIR, rx=0))
    out.append(text(x0, py - 6, title, size=11, weight=700))
    for v in (0, vmax / 2, vmax):
      out.append(text(x0 - 8, ys(v) + 4, f"{v:g} V", size=9.5, fill=FAINT, anchor="end"))
    if "v33" in keys:
      for k, lab, lx, dy in (("bor3", "BOR3", x1 - 4, -3), ("bor1", "BOR1", x1 - 4, -3), ("vdd_min", "rated min", x0 + 760, -3),
                             ("pdr", "PDR", x0 + 760, 10)):
        out.append(line(x0, ys(th[k]), x1, ys(th[k]), stroke=RED if k in ("vdd_min", "pdr") else AMBER, sw=1, dash="4 3"))
        out.append(text(lx, ys(th[k]) + dy, f"{lab} {th[k]:g} V", size=9, fill=MUTED, anchor="end" if lx == x1 - 4 else "start"))
    for j, key in enumerate(keys):
      c, lab = next((cl, lb) for kk, lb, cl in SERIES if kk == key)
      d = "M" + " L".join(f"{xs(tr['t'][i]):.1f} {ys(tr[key][i]):.1f}" for i in range(n))
      out.append(path(d, stroke=c, sw=2))
      out.append(text(xs(0.1), ys(tr[key][at(tr, 0.1)]) + (-6 if j == 0 else 14), lab, size=10, weight=700, fill=c))
    py += ph + 30
  for t in (0, 0.02, 0.04, 0.06, 0.08, 0.1, 0.12):
    out.append(text(xs(t), py - 12, f"{t * 1000:.0f} ms", size=9.5, fill=FAINT, anchor="middle"))
  out.append(f'<g class="cur"><line x1="{x0}" y1="248" x2="{x0}" y2="{py - 30}" stroke="{INK}" stroke-width="1.4"/></g>')

  # ---------------------------------------------------------------- every level and circuit
  y = py + 14
  levels = list(dict.fromkeys(lv for lv, _, _ in grid))
  circuits = list(dict.fromkeys(c for _, c, _ in grid))
  out.append(text(40, y, f"All {len(grid)} runs: outcome by starting-profile level and circuit variant", size=12, weight=700))
  cw = (W - 80 - 200) / len(levels)
  y += 20
  for j, lv in enumerate(levels):
    out.append(text(240 + j * cw + cw / 2, y + 4, lv, size=10.5, weight=700, anchor="middle"))
  for i, c in enumerate(circuits):
    yy = y + 14 + i * 22
    out.append(text(40, yy + 13, c, size=10.5))
    for j, lv in enumerate(levels):
      o = next((oo for l2, c2, oo in grid if l2 == lv and c2 == c), None)
      if o is None:
        raise FigureError(f"crank-dip.md: no row for level {lv}, circuit {c}")
      fg, bg = OUTCOME[o]
      out.append(rect(240 + j * cw + 4, yy, cw - 8, 18, fill=bg, stroke=fg, rx=9))
      out.append(text(240 + j * cw + cw / 2, yy + 13, o, size=10, weight=700, fill=fg, anchor="middle"))
  y += 14 + len(circuits) * 22 + 18
  resets = sum(o != "rides through" for _, _, o in grid)
  out.append(text(40, y, f"{resets} of the {len(grid)} runs reset the device; it restarts once the supply recovers to US. "
                  "BOR and PVD are not configured today (HWSR-505, HWSR-505a).", size=11, fill=INK))
  y += 18
  out.append(text(40, y, fit(data["about"] + " (DQ-413)", W - 80, 10.5), size=10.5,
                  fill=MUTED))
  y += 18
  out.append(text(40, y, "Generated by fig_h02_crank_anim.py from sim/results/crank-dip.json and crank-dip.md; nothing "
                  "is hand-listed but the node names of the power path.", size=10.5, fill=MUTED))
  extra, y = terms.svg_footer(out, 40, y + 22, W - 80)
  out += extra
  nom = data["nom"]
  desc = (f"Level {LEVEL}, nominal circuit: the device input falls to {nom['vin_min']} V, the 5 V rail to {nom['v5_min']} V "
          f"and the MCU rail to {nom['v33_min']} V; outcome {nom['outcome']}. {resets} of {len(grid)} runs reset.")
  return svg(W, int(y + 12), "Figure 3-8. Cranking dip through the power path, animated (WP-H-02)", desc, out)


def build() -> dict[str, str]:
  return {OUT: figure(*load())}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except FigureError as e:
    print(f"fig_h02_crank_anim: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n_ for n_, c in outputs.items() if not (HERE / n_).exists() or (HERE / n_).read_text(encoding="utf-8") != c]
    for n_ in stale:
      print(f"assurance/04-hardware/figures/{n_} is stale; run fig_h02_crank_anim.py", file=sys.stderr)
    if not stale:
      print(f"fig_h02_crank_anim: {len(outputs)} figure current")
    return 1 if stale else 0
  for n_, c in outputs.items():
    (HERE / n_).write_text(c, encoding="utf-8")
    print(f"wrote assurance/04-hardware/figures/{n_}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
