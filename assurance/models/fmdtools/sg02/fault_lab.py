#!/usr/bin/env python3
"""Fault Lab: one page that shows an SG-02 run the way a reviewer would watch it (TE-02 step P5).

Left, the replay: plant case F-07 (EPS fault in a curve) drawn with the scene kit, its events read from
../../../sim/results/plant-results.md. Right, the sweep: the P3 minimal sets against the WP-A-04 tree
(p3-minimal-sets.json), the P4 time to the first cue for every set, a pair matrix of the order-2 sets, and the findings
that follow from those numbers. Nothing on the page is typed in: every figure comes from a generated record, and the page
is rebuilt and compared in CI.

    python3 fault_lab.py            # writes fault-lab.html
    python3 fault_lab.py --check    # fails if the page differs from a fresh build

Synthetic (DSR-12): no evidence credit. Decided by the lead on 2026-10-21 (DQ-409).
"""

import html
import json
import re
import sys
from multiprocessing import Pool
from pathlib import Path

import model as m
import sweep as sw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = HERE / "fault-lab.html"
PLANT = ROOT / "assurance/sim/results/plant-results.md"
CASE = "F-07"
sys.path.insert(0, str(ROOT / "assurance/01-management/figures"))
import scenekit as sk  # noqa: E402
sys.path.insert(0, str(HERE.parent))
import faultlab_kit as kit  # noqa: E402

STILL = re.compile(r"<animate[^>]*/>|<animateTransform[^>]*/>")
esc = html.escape


# ------------------------------------------------------------------------------------------------------- data

def _table(text: str, first: str) -> dict[str, dict[str, str]]:
  """Rows of the markdown table whose header starts with `first`, keyed by their first cell."""
  lines = text.splitlines()
  for i, line in enumerate(lines):
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if cells and cells[0] == "Case" and len(cells) > 1 and cells[1].startswith(first):
      rows = {}
      for row in lines[i + 2:]:
        if not row.startswith("|"):
          break
        vals = [c.strip() for c in row.strip().strip("|").split("|")]
        rows[vals[0]] = dict(zip(cells, vals))
      return rows
  raise SystemExit(f"{PLANT.relative_to(ROOT)}: no table starting with 'Case | {first}'")


def plant_case(case: str = CASE) -> dict:
  text = PLANT.read_text(encoding="utf-8")
  lat = _table(text, "Fault")[case]
  ev = _table(text, "Events")[case]["Events (s from fault onset)"]
  events = {}
  for part in ev.split(";"):
    name, _, t = part.strip().rpartition(" ")
    events[name] = float(t)
  cross = lat["To lane line, 3.0 / 3.7 m lane (s)"].split("/")[0].strip()
  return {
    "case": case,
    "fault": lat["Fault (FMEA; WP-V-05)"],
    "events": events,
    "torque": float(lat["EPS torque < 5 % (s)"]),
    "siren": float(lat["Siren (s)"]),
    "correction": events["driver correction"],
    "cross": float(cross),
    "max_dev": abs(float(lat["Max deviation (m)"])),
  }


def sweep_data() -> dict:
  data = json.loads(sw.P3_JSON.read_text(encoding="utf-8"))
  solver, cut_sets = sw.solve(m.EVENTS["goal"])
  latent = solver.latent
  sirens = {e for e, (fxn, _) in m.MODE_OF.items() if fxn == "siren"}
  model = [frozenset(c) for c in data["sets"]]
  tree = [c for c in sw.fc.minimise([frozenset(c - latent) for c in cut_sets]) if len(c) <= data["order"]]
  tree_only = [c for c in tree if c not in model]
  covered = [c for c in tree_only if any(c < f and (f - c) <= sirens for f in model)]
  sets, label, tree_set = sw.timing_sets()
  budget = m.EVENTS["budget_s"]
  with Pool() as pool:
    outcomes = pool.map(sw._timed, [tuple(sorted(c)) for c in sets], chunksize=4)
  timing = []
  for c, o in zip(sets, outcomes):
    gap = None if o.t_cue is None else round(o.t_cue - (o.t_lost or 0), 3)
    timing.append({"set": sorted(c), "row": label[c], "gap": gap, "cue": o.cue})
  within = [t for t in timing if t["gap"] is not None and t["gap"] <= budget]
  late = [t for t in timing if t["gap"] is not None and t["gap"] > budget]
  tight = max(within, key=lambda t: (t["gap"], t["set"])) if within else None
  return {
    "order": data["order"], "runs": sum(data["runs"]), "modes": len(m.MODE_OF), "model": model, "tree": tree,
    "agree": [c for c in model if c in tree], "tree_only": tree_only, "covered": covered,
    "gaps": sw.tree_gaps(model, cut_sets, latent), "timing": timing, "within": within, "late": late,
    "none": [t for t in timing if t["gap"] is None], "tight": tight, "budget": budget,
  }


# ------------------------------------------------------------------------------------------------------- scene

def scene(p: dict) -> str:
  """Plant case F-07 on the scene-kit curve: the car drifts out once the EPS torque is gone and its body edge reaches
  the lane line at the plant's crossing time. Schematic along the road; times are the plant's."""
  def cy(x):
    return 84 if x < 60 else 84 - 0.0016 * (x - 60) ** 2

  def edge(k):
    return [(x, cy(x) + k) for x in [sk.W * i / 80 for i in range(81)]]

  def drift(t):
    return max(0.0, t - p["torque"]) ** 2

  k = 10 / drift(p["cross"])
  t0, t1 = -0.4, p["cross"]
  X = lambda t: 20 + 160 * (t - t0) / (t1 - t0)
  ts = [t0 + (t1 - t0) * i / 50 for i in range(51)]
  perf = [(X(t), cy(X(t)) + k * drift(t)) for t in ts]
  req = [(X(t), cy(X(t))) for t in [t0 + 1.4 * (t1 - t0) * i / 50 for i in range(51)]]
  band = sk.d([(X(t), cy(X(t))) for t in ts] + perf[::-1]) + " Z"
  fi = min(range(len(ts)), key=lambda i: abs(ts[i]))
  inner = [*sk.curved_road(edge),
           f'<path d="{band}" fill="{sk.PERF_S}" opacity="0.22"/>',
           sk.intended_path(req), sk.performed_path(sk.d(perf), ""), sk.start_marker(sk.pose(perf, 1)),
           sk.car(sk.pose(perf, len(perf) - 1), sk.EGO, 1, sk.EGO_EDGE),
           sk.fault_marker(*perf[fi], 0),
           f'<circle cx="{perf[-1][0]:.1f}" cy="{perf[-1][1]:.1f}" r="7" fill="none" stroke="{sk.CALLOUT}" '
           'stroke-width="1.6"/>']
  out = (f'<rect width="{sk.LARGE_W}" height="{sk.LARGE_H}" fill="{sk.GRASS}"/>'
         f'<g transform="translate(0 {sk.LARGE_DY}) scale({sk.LARGE_K})">' + STILL.sub("", "".join(inner)) + "</g>")
  xr, yr = perf[-1][0] * sk.LARGE_K, perf[-1][1] * sk.LARGE_K + sk.LARGE_DY
  out += sk.road_label(xr, yr + 30, f"lane line crossed · {p['cross']:.2f} s", sk.CALLOUT, 7, halo=True)
  xf, yf = perf[fi][0] * sk.LARGE_K, perf[fi][1] * sk.LARGE_K + sk.LARGE_DY
  out += sk.road_label(xf + 10, yf + 22, "fault · 0.00 s", sk.FAULT, 7, halo=True, anchor="start")
  pills = [(f"EPS torque gone · {p['torque']:.2f} s", "bad"), (f"panda siren · {p['siren']:.2f} s", "ok"),
           (f"driver steers · {p['correction']:.2f} s", "drv"), (f"plant case {p['case']}", "info")]
  out += "".join(sk.pill(10, 36 + 16 * i, s, style, size=6.5, h=12) for i, (s, style) in enumerate(pills))
  return (f'<svg viewBox="0 30 {sk.LARGE_W} 190" width="100%" role="img" aria-label="Top view of plant case '
          f'{p["case"]}: the car drifts across the lane line after the EPS fault" style="display:block" '
          f'font-family="system-ui,sans-serif">{out}</svg>')


def timeline(p: dict) -> str:
  """Event strip under the scene: one row per event, 0 to just past the correction, with the 1 s budget shaded."""
  end = max(p["correction"], p["cross"]) + 0.25
  marks = [("fault", 0.0, "#d03b3b"), ("panda siren", p["siren"], "#6250d6"), ("EPS torque gone", p["torque"], "#9a6400"),
           ("lane line crossed", p["cross"], "#b45309"), ("driver steers", p["correction"], "#0a7a0a")]
  W, L, R, rh, T = 440, 112, 40, 20, 8
  X = lambda t: L + (W - L - R) * t / end
  H = T + rh * len(marks) + 18
  out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Event timeline of plant case {p["case"]}" '
         'font-size="12">',
         f'<rect x="{X(0):.1f}" y="{T}" width="{X(1.0) - X(0):.1f}" height="{rh * len(marks)}" class="budget"/>',
         f'<text x="{X(1.0) - 4:.1f}" y="{H - 4}" text-anchor="end" class="tlm">1.0 s budget</text>']
  for i, (name, t, col) in enumerate(marks):
    y = T + i * rh + rh / 2
    out.append(f'<text x="{L - 10}" y="{y + 4}" text-anchor="end" class="tl">{esc(name)}</text>')
    out.append(f'<line x1="{L}" x2="{W - R}" y1="{y}" y2="{y}" class="axis"/>')
    out.append(f'<circle cx="{X(t):.1f}" cy="{y}" r="5" fill="{col}"/>')
    out.append(f'<text x="{X(t) + 9:.1f}" y="{y + 4}" class="tl">{t:.2f} s</text>')
  out.append("</svg>")
  return "".join(out)


# ------------------------------------------------------------------------------------------------------- page

CSS, matrix, finding = kit.CSS, kit.matrix, kit.finding


def build() -> str:
  p, d = plant_case(), sweep_data()
  b = d["budget"]
  tight = d["tight"]
  finds = [
    finding("g" if not d["gaps"] else "c",
            "No fault set missing from the tree" if not d["gaps"] else f"{len(d['gaps'])} sets missing from the tree",
            f"Every one of the {len(d['model'])} minimal sets the model finds holds an effective WP-A-04 cut set."
            if not d["gaps"] else "Sets: " + ", ".join(esc(sw.fset(c)) for c in d["gaps"])),
    finding("w", f"{len(d['covered'])} tree sets need a siren failure too",
            "The model needs one more event (BE-2.14, BE-2.15 or BE-2.22) for "
            + ", ".join(f"<code>{esc(sw.fset(c))}</code>" for c in d["covered"][:4])
            + (" and others" if len(d["covered"]) > 4 else "") + ": the panda siren now covers them (TSR-516)."),
  ]
  if tight:
    finds.append(finding("w", f"Tightest cue in budget: {tight['gap']:.2f} s",
                         f"<code>{esc(sw.fset(tight['set']))}</code> ({esc(tight['row'])}) is cued by the "
                         f"{esc(tight['cue'])} {b - tight['gap']:.2f} s inside the {b:g} s budget."))
  if d["late"]:
    worst = max(d["late"], key=lambda t: t["gap"])
    finds.append(finding("c", f"{len(d['late'])} sets cued after the budget",
                         f"Latest: <code>{esc(sw.fset(worst['set']))}</code> ({esc(worst['row'])}), "
                         f"{worst['gap']:.2f} s by the {esc(worst['cue'])}."))
  finds.append(finding("w", f"{len(d['none'])} sets with no cue within {sw.HORIZON_S:g} s",
                       "The warning failures of the tree, as expected: the HMI or both the alert and the siren fail."))

  return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SG-02 Fault Lab</title>
<!-- Generated by assurance/models/fmdtools/sg02/fault_lab.py. Do not edit by hand. -->
<style>{CSS}</style></head><body>
<div class="top">
  <div><div class="crumb">LionDriver · Fault Lab · SG-02 lateral control (TE-02)</div>
  <div class="tt">Replay of plant case {p['case']} and the fmdtools sweep</div></div>
  <div class="sp"></div>
  <span class="pill ok">Sweep: {d['runs']:,} runs · {d['modes']} modes · up to {d['order']} at once</span>
  <span class="pill syn">Synthetic (DSR-12) · no evidence credit</span>
</div>
<div class="wrap">
  <div class="side">
  <div class="card">
    <div class="pad"><p class="h2">{esc(p['fault'])}</p>
    <p class="sub">Top view, schematic along the road; times are the plant's (seconds from the fault).</p></div>
    {scene(p)}
    <div class="pad"><div class="tlw">{timeline(p)}</div></div>
    <div class="hud">
      <div><span>EPS torque gone</span><b>{p['torque']:.2f} s</b></div>
      <div><span>Panda siren</span><b style="color:var(--violet)">{p['siren']:.2f} s</b></div>
      <div><span>Lane line (3.0 m lane)</span><b style="color:var(--crit)">{p['cross']:.2f} s</b></div>
      <div><span>Driver steers</span><b style="color:var(--good)">{p['correction']:.2f} s</b></div>
      <div><span>Max deviation</span><b>{p['max_dev']:.2f} m</b></div>
    </div>
  </div>
    <div class="card pad"><p class="h2">Findings for review</p>
      <p class="sub">Each goes to its owner; the tree changes only after a person reviews it</p>
      {''.join(finds)}
    </div>
  </div>
  <div class="side">
    <div class="card pad">
      <p class="h2">Sweep against the WP-A-04 tree (P3)</p>
      <p class="sub">Minimal fault sets of up to {d['order']} modes, mid-curve</p>
      <div class="kp">
        <div><b>{len(d['model'])}</b><span>model sets</span></div>
        <div><b>{len(d['agree'])}</b><span>same as tree</span></div>
        <div><b style="color:var(--good)">{len(d['gaps'])}</b><span>missing from tree</span></div>
      </div>
      <p class="h2" style="margin-top:14px">Time to the first cue (P4)</p>
      <p class="sub">{len(d['timing'])} sets, against the {b:g} s budget</p>
      <div class="kp">
        <div><b style="color:var(--good)">{len(d['within'])}</b><span>in budget</span></div>
        <div><b style="color:var(--warn)">{len(d['late'])}</b><span>late</span></div>
        <div><b style="color:var(--crit)">{len(d['none'])}</b><span>no cue</span></div>
      </div>
    </div>
    <div class="card pad">
      <p class="h2">Pairs that lose control without a cue in time</p>
      <p class="sub">Order-2 minimal sets, mid-curve. A ring on an empty cell is a tree pair that the model only loses with a siren failure as well</p>
      <div class="leg"><span><i style="background:var(--te)"></i>minimal pair in the model</span>
      <span>○ minimal pair in the tree</span></div>
      {matrix(d)}
    </div>
  </div>
</div>
<p class="foot">Sources: <code>p3-minimal-sets.json</code>, a fresh P4 run of the model (<code>sweep.py</code>), and
<code>assurance/sim/results/plant-results.md</code> case {p['case']}. Generated by <code>fault_lab.py</code>; CI rebuilds
and compares it.</p>
</body></html>
"""


def main(argv: list[str]) -> int:
  page = build()
  rel = OUT.relative_to(ROOT)
  if "--check" in argv:
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != page:
      print(f"{rel} is stale: run python3 {Path(__file__).relative_to(ROOT)}", file=sys.stderr)
      return 1
    print(f"{rel} current")
    return 0
  OUT.write_text(page, encoding="utf-8")
  print(f"wrote {rel}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
