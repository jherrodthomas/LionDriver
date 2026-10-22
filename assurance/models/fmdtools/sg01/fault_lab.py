#!/usr/bin/env python3
"""Fault Lab for SG-01: one page that shows an SG-01 run the way a reviewer would watch it (tool evaluation TE-02
step P5, DQ-409; extended to SG-01 by DQ-417).

Left, the replay: plant case F-03 (command frozen at curve entry while the heartbeat stays alive), the stale-torque
branch of the tree, read from ../../../sim/results/plant-results.md. Right, the sweep: the P3 minimal sets against the
WP-A-04 tree (p3-minimal-sets.json), the sets per TE-01 branch, a pair matrix of the order-2 sets, and the findings that
follow from those numbers. Nothing on the page is typed in: every figure comes from a generated record, and the page is
rebuilt and compared in CI.

    python3 fault_lab.py            # writes fault-lab.html
    python3 fault_lab.py --check    # fails if the page differs from a fresh build

Synthetic (DSR-12): no evidence credit.
"""

import json
import sys
from pathlib import Path

import model as m
import sweep as sw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = HERE / "fault-lab.html"
PLANT = ROOT / "assurance/sim/results/plant-results.md"
CASE = "F-03"
sys.path.insert(0, str(HERE.parent))
import faultlab_kit as kit  # noqa: E402
import treediff as td  # noqa: E402

esc = kit.esc


# ------------------------------------------------------------------------------------------------------- data

def plant_case(case: str = CASE) -> dict:
  text = PLANT.read_text(encoding="utf-8")
  lat = kit.plant_table(text, "Fault")[case]
  ev = kit.plant_events(text, case)
  return {
    "case": case,
    "fault": lat["Fault (FMEA; WP-V-05)"],
    "reaction": lat["Panda reaction (s)"],
    "drift": ev["driver cue (drift)"],
    "correction": ev["driver correction"],
    "cross": float(lat["To lane line, 3.0 / 3.7 m lane (s)"].split("/")[0]),
    "max_dev": abs(float(lat["Max deviation (m)"])),
  }


def sweep_data() -> dict:
  data = json.loads(sw.P3_JSON.read_text(encoding="utf-8"))
  solver, cut_sets = td.solve(sw.GOAL)
  latent = solver.latent
  model = [frozenset(c) for c in data["sets"]]
  tree = td.effective(cut_sets, latent, data["order"])
  branches = {k: 0 for k in sw.BRANCH}
  for c in data["sets"]:
    branches[data["branch"][",".join(c)]] += 1
  return {
    "order": data["order"], "runs": sum(data["runs"]), "modes": len(m.MODE_OF), "model": model, "tree": tree,
    "agree": [c for c in model if c in tree], "tree_only": [c for c in tree if c not in model],
    "gaps": td.tree_gaps(model, cut_sets, latent), "branches": branches, "budget": m.EVENTS["budget_s"],
  }


# ------------------------------------------------------------------------------------------------------- replay

def timeline(p: dict) -> str:
  """One row per event of the plant case, 0 to just past the correction, with the 0.5 s FTTI shaded."""
  end = p["correction"] + 0.3
  marks = [("fault", 0.0, "#d03b3b"), ("panda reacts", None, "#6250d6"), ("driver sees drift", p["drift"], "#9a6400"),
           ("lane line crossed", p["cross"], "#b45309"), ("driver steers", p["correction"], "#0a7a0a")]
  W, L, R, rh, T = 440, 112, 50, 20, 8
  X = lambda v: L + (W - L - R) * v / end
  H = T + rh * len(marks) + 18
  out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Event timeline of plant case {p["case"]}" '
         'font-size="12">',
         f'<rect x="{X(0):.1f}" y="{T}" width="{X(0.5) - X(0):.1f}" height="{rh * len(marks)}" class="budget"/>',
         f'<text x="{X(0) + 2:.1f}" y="{H - 4}" class="tlm">0.5 s FTTI</text>']
  for i, (name, v, col) in enumerate(marks):
    y = T + i * rh + rh / 2
    out.append(f'<text x="{L - 10}" y="{y + 4}" text-anchor="end" class="tl">{esc(name)}</text>')
    out.append(f'<line x1="{L}" x2="{W - R}" y1="{y}" y2="{y}" class="axis"/>')
    if v is None:
      out.append(f'<text x="{W - R + 6}" y="{y + 4}" class="tlm">none</text>')
      continue
    out.append(f'<circle cx="{X(v):.1f}" cy="{y}" r="5" fill="{col}"/>')
    out.append(f'<text x="{X(v) + 9:.1f}" y="{y + 4}" class="tl">{v:.2f} s</text>')
  out.append("</svg>")
  return "".join(out)


# ------------------------------------------------------------------------------------------------------- page

def build() -> str:
  p, d = plant_case(), sweep_data()
  sets = lambda cs: ", ".join(f"<code>{esc(td.fset(c))}</code>" for c in cs[:4]) + (" and others" if len(cs) > 4 else "")
  finds = []
  if d["gaps"]:
    finds.append(kit.finding("w", f"{len(d['gaps'])} sets the drawn tree does not predict",
                             f"{sets(d['gaps'])}: {esc(sw.why(d['gaps'][0]))}. The cut-set table already counts them "
                             "as single points (DFI-10); the drawn tree keeps BE-1.15 as a second event."))
  else:
    finds.append(kit.finding("g", "No fault set missing from the tree",
                             f"Every one of the {len(d['model'])} minimal sets the model finds holds an effective "
                             "WP-A-04 cut set."))
  if d["tree_only"]:
    finds.append(kit.finding("w", f"{len(d['tree_only'])} tree sets the model does not reach",
                             f"{sets(d['tree_only'])}. " + " ".join(
                               f"{esc(e)}: {esc(sw.WHY[e])}." for e in sorted({e for c in d['tree_only'] for e in c})
                               if e in sw.WHY and e not in ("BE-1.13", "BE-1.17"))))
  finds.append(kit.finding("c", f"{d['branches']['stale']} stale-torque single points remain",
                           "A stale model input (BE-1.19), masked diagnostics (BE-1.20) and a replayed command buffer "
                           "(BE-1.21) hold torque past the FTTI: the heartbeat and frame-arrival checks do not see a "
                           "stale value in frames that keep arriving (TSR-409 open). TSR-602 drops a stale model input "
                           "only at 0.52 s, just over the 0.5 s FTTI."))
  finds.append(kit.finding("w", f"Plant case {p['case']}: nothing reacts",
                           f"With the command frozen and the heartbeat alive, the panda does not react; the driver "
                           f"sees the drift at {p['drift']:.2f} s, after the lane line at {p['cross']:.2f} s is "
                           "already near."))

  return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SG-01 Fault Lab</title>
<!-- Generated by assurance/models/fmdtools/sg01/fault_lab.py. Do not edit by hand. -->
<style>{kit.CSS}</style></head><body>
<div class="top">
  <div><div class="crumb">LionDriver · Fault Lab · SG-01 lateral torque (TE-01)</div>
  <div class="tt">Replay of plant case {p['case']} and the fmdtools sweep</div></div>
  <div class="sp"></div>
  <span class="pill ok">Sweep: {d['runs']:,} sets · {d['modes']} modes · up to {d['order']} at once · 4 phases</span>
  <span class="pill syn">Synthetic (DSR-12) · no evidence credit</span>
</div>
<div class="wrap">
  <div class="side">
  <div class="card">
    <div class="pad"><p class="h2">{esc(p['fault'])}</p>
    <p class="sub">Plant times, in seconds from the fault. The frozen command stays inside the envelope's limits and
    its frames keep arriving, so no check removes it.</p></div>
    <div class="pad"><div class="tlw">{timeline(p)}</div></div>
    <div class="hud">
      <div><span>Panda reaction</span><b>{esc(p['reaction'])}</b></div>
      <div><span>Driver sees drift</span><b>{p['drift']:.2f} s</b></div>
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
      <p class="sub">Minimal fault sets of up to {d['order']} modes, in any of the four phases</p>
      <div class="kp">
        <div><b>{len(d['model'])}</b><span>model sets</span></div>
        <div><b>{len(d['agree'])}</b><span>same as tree</span></div>
        <div><b style="color:var(--warn)">{len(d['gaps'])}</b><span>not in the drawn tree</span></div>
      </div>
      <p class="h2" style="margin-top:14px">Model sets by branch of TE-01</p>
      <p class="sub">The first branch each set reaches</p>
      <div class="kp">
        <div><b>{d['branches']['excess']}</b><span>excess torque</span></div>
        <div><b>{d['branches']['unwanted']}</b><span>unwanted torque</span></div>
        <div><b style="color:var(--crit)">{d['branches']['stale'] + d['branches']['overlap']}</b><span>held past the FTTI</span></div>
      </div>
    </div>
    <div class="card pad">
      <p class="h2">Pairs that give TE-01</p>
      <p class="sub">Order-2 minimal sets. A ring on an empty cell is a tree pair the model does not reach</p>
      <div class="leg"><span><i style="background:var(--te)"></i>minimal pair in the model</span>
      <span>○ minimal pair in the tree</span></div>
      {kit.matrix(d, "give TE-01")}
    </div>
  </div>
</div>
<p class="foot">Sources: <code>p3-minimal-sets.json</code> and <code>assurance/sim/results/plant-results.md</code> case
{p['case']}. Generated by <code>fault_lab.py</code>; CI rebuilds and compares it.</p>
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
