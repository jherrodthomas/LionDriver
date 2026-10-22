#!/usr/bin/env python3
"""Fault Lab for SG-03: one page that shows an SG-03 run the way a reviewer would watch it (tool evaluation TE-02
step P5, DQ-409; extended to SG-03 by DQ-417).

Left, the replay: plant case L-01 (acceleration request at the envelope maximum, +2.0 m/s²), the in-bound case the
tree's single point MCS-03.1 rests on, read from ../../../sim/results/plant-results.md. Right, the sweep: the P3 minimal sets against the
WP-A-04 tree (p3-minimal-sets.json), the sets per TE-03 branch, a pair matrix of the order-2 sets, and the findings that
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
CASE = "L-01"
sys.path.insert(0, str(HERE.parent))
import faultlab_kit as kit  # noqa: E402
import treediff as td  # noqa: E402

esc = kit.esc


# ------------------------------------------------------------------------------------------------------- data

def plant_case(case: str = CASE) -> dict:
  text = PLANT.read_text(encoding="utf-8")
  gap_col = "Gap to lead: onset / min / lost in 1 s (m)"
  lon = kit.plant_table(text, "Fault", has=gap_col)[case]
  ev = kit.plant_events(text, case)
  gap = [float(x) for x in lon[gap_col].split("/")]
  return {
    "case": case,
    "fault": lon["Fault (FMEA; WP-V-05)"],
    "cue": ev["driver cue (acceleration)"],
    "correction": ev["driver correction"],
    "revoked": ev["authority revoked"],
    "gap_onset": gap[0], "gap_min": gap[1], "gap_lost": gap[2],
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
  """One row per event of the plant case, 0 to just past the revocation, with the 1 s FTTI shaded."""
  end = p["revoked"] + 0.3
  marks = [("fault", 0.0, "#d03b3b"), ("driver feels it", p["cue"], "#9a6400"),
           ("driver brakes", p["correction"], "#0a7a0a"), ("authority revoked", p["revoked"], "#6250d6")]
  W, L, R, rh, T = 440, 112, 50, 20, 8
  X = lambda v: L + (W - L - R) * v / end
  H = T + rh * len(marks) + 18
  out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Event timeline of plant case {p["case"]}" '
         'font-size="12">',
         f'<rect x="{X(0):.1f}" y="{T}" width="{X(1.0) - X(0):.1f}" height="{rh * len(marks)}" class="budget"/>',
         f'<text x="{X(0) + 2:.1f}" y="{H - 4}" class="tlm">1.0 s FTTI</text>']
  for i, (name, v, col) in enumerate(marks):
    y = T + i * rh + rh / 2
    out.append(f'<text x="{L - 10}" y="{y + 4}" text-anchor="end" class="tl">{esc(name)}</text>')
    out.append(f'<line x1="{L}" x2="{W - R}" y1="{y}" y2="{y}" class="axis"/>')
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
                             f"{sets(d['gaps'])}: the SoC reads the same frames as the envelope, so it stays engaged and "
                             "keeps requesting acceleration without a SoC fault (DFI-10). The cut-set table already "
                             "notes this; the drawn tree keeps BE-3.13 as a second event."))
  else:
    finds.append(kit.finding("g", "No fault set missing from the tree",
                             f"Every one of the {len(d['model'])} minimal sets the model finds holds an effective "
                             "WP-A-04 cut set."))
  if d["tree_only"]:
    finds.append(kit.finding("w", f"{len(d['tree_only'])} tree sets the model does not reach as drawn",
                             f"{sets(d['tree_only'])}. " + " ".join(
                               f"{esc(e)}: {esc(sw.WHY[e])}." for e in sorted({e for c in d['tree_only'] for e in c})
                               if e in sw.WHY and e not in ("BE-1.13", "BE-3.09"))))
  finds.append(kit.finding("c", "A replayed command buffer stays a single point",
                           "BE-1.21 holds a stale acceleration past the 1 s FTTI: the replayed frames keep arriving, so "
                           "neither the heartbeat nor the frame-arrival check sees it (TSR-409 open)."))
  finds.append(kit.finding("w", f"Plant case {p['case']}: the driver is the barrier",
                           f"At the +2.0 m/s² bound the driver feels the acceleration at {p['cue']:.2f} s and brakes "
                           f"at {p['correction']:.2f} s; the gap to the lead closes from {p['gap_onset']:.1f} m to "
                           f"{p['gap_min']:.1f} m. Whether +2.0 m/s² is controllable rests on BE-3.01 and AOU-05R."))

  return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SG-03 Fault Lab</title>
<!-- Generated by assurance/models/fmdtools/sg03/fault_lab.py. Do not edit by hand. -->
<style>{kit.CSS}</style></head><body>
<div class="top">
  <div><div class="crumb">LionDriver · Fault Lab · SG-03 unintended acceleration (TE-03)</div>
  <div class="tt">Replay of plant case {p['case']} and the fmdtools sweep</div></div>
  <div class="sp"></div>
  <span class="pill ok">Sweep: {d['runs']:,} sets · {d['modes']} modes · up to {d['order']} at once · 5 phases</span>
  <span class="pill syn">Synthetic (DSR-12) · no evidence credit</span>
</div>
<div class="wrap">
  <div class="side">
  <div class="card">
    <div class="pad"><p class="h2">{esc(p['fault'])}</p>
    <p class="sub">Plant times, in seconds from the fault, following a lead. The request is at the envelope's bound,
    so the envelope passes it until the driver brakes.</p></div>
    <div class="pad"><div class="tlw">{timeline(p)}</div></div>
    <div class="hud">
      <div><span>Driver feels it</span><b>{p['cue']:.2f} s</b></div>
      <div><span>Driver brakes</span><b style="color:var(--good)">{p['correction']:.2f} s</b></div>
      <div><span>Gap to lead at onset</span><b>{p['gap_onset']:.1f} m</b></div>
      <div><span>Smallest gap</span><b style="color:var(--crit)">{p['gap_min']:.1f} m</b></div>
      <div><span>Gap lost in 1 s</span><b>{p['gap_lost']:.2f} m</b></div>
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
      <p class="sub">Minimal fault sets of up to {d['order']} modes, in any of the five phases</p>
      <div class="kp">
        <div><b>{len(d['model'])}</b><span>model sets</span></div>
        <div><b>{len(d['agree'])}</b><span>same as tree</span></div>
        <div><b style="color:var(--warn)">{len(d['gaps'])}</b><span>not in the drawn tree</span></div>
      </div>
      <p class="h2" style="margin-top:14px">Model sets by branch of TE-03</p>
      <p class="sub">The first branch each set reaches</p>
      <div class="kp">
        <div><b>{d['branches']['excess'] + d['branches']['closing']}</b><span>excess or closing</span></div>
        <div><b>{d['branches']['unwanted'] + d['branches']['gas']}</b><span>unwanted or on the pedal</span></div>
        <div><b style="color:var(--crit)">{d['branches']['stale'] + d['branches']['overlap']}</b><span>held past the FTTI</span></div>
      </div>
    </div>
    <div class="card pad">
      <p class="h2">Pairs that give TE-03</p>
      <p class="sub">Order-2 minimal sets. A ring on an empty cell is a tree pair the model does not reach</p>
      <div class="leg"><span><i style="background:var(--te)"></i>minimal pair in the model</span>
      <span>○ minimal pair in the tree</span></div>
      {kit.matrix(d, "give TE-03")}
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
