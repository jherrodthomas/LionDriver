#!/usr/bin/env python3
"""Fault Lab for SG-06: one page that shows an SG-06 run the way a reviewer would watch it (tool evaluation TE-02
step P5, DQ-409; extended to SG-06 by DQ-417).

Left, the replay. No plant case covers a loss of deceleration yet (the plant's longitudinal cases L-01 to L-04 are
for SG-03 and SG-04), so the replay is the model's own run of the case the sweep turns on: the plan input is lost
while the HMI hangs, and the take-over cue is the cluster cruise change after the host's ACC cancel. Right, the sweep:
the P3 minimal sets against the WP-A-04 tree (p3-minimal-sets.json), the P4 time to the first cue for every set, a
pair matrix of the order-2 sets, and the findings that follow from those numbers. Nothing on the page is typed in:
every figure comes from a generated record or a model run, and the page is rebuilt and compared in CI.

    python3 fault_lab.py            # writes fault-lab.html
    python3 fault_lab.py --check    # fails if the page differs from a fresh build

Synthetic (DSR-12): no evidence credit.
"""

import json
import sys
from multiprocessing import Pool
from pathlib import Path

import model as m
import sweep as sw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = HERE / "fault-lab.html"
REPLAY = ("BE-2.12", "BE-6.01")      # plan input lost (MCS-06.1 cause) while the HMI hangs (MCS-06.8)
sys.path.insert(0, str(HERE.parent))
import faultlab_kit as kit  # noqa: E402
import treediff as td  # noqa: E402

esc = kit.esc


# ------------------------------------------------------------------------------------------------------- data

def replay(events: tuple[str, ...] = REPLAY) -> dict:
  """The model's run of `events`, each event at its model time, and the same set with the cancel failed too."""
  t = m.times(events)
  without = m.run(events + ("BE-6.06",))
  rows = sorted((x for x in m.EVENTS["modes"] if x["event"] in events), key=lambda x: x["kind"] != "cause")
  low = lambda s: s if s[:2].isupper() else s[0].lower() + s[1:]     # keep acronyms such as HMI
  text = rows[0]["text"] + "".join(f", with the {low(x['text'])}" for x in rows[1:])
  return {"events": events, "t": t, "outcome": m.run(events), "without_cancel": without, "text": text}


def sweep_data() -> dict:
  data = json.loads(sw.P3_JSON.read_text(encoding="utf-8"))
  solver, cut_sets = td.solve(sw.GOAL)
  latent = solver.latent
  model = [frozenset(c) for c in data["sets"]]
  tree = td.effective(cut_sets, latent, data["order"])
  tree_only = [c for c in tree if c not in model]
  by_siren = [c for c in tree_only if any(c < f and (f - c) <= sw.SIRENS for f in model)]
  by_cancel = [c for c in tree_only if c not in by_siren and sw.covering(c, model)]
  sets, label, _ = sw.timing_sets()
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
    "agree": [c for c in model if c in tree], "tree_only": tree_only, "by_siren": by_siren, "by_cancel": by_cancel,
    "gaps": td.tree_gaps(model, cut_sets, latent), "timing": timing, "within": within, "late": late,
    "none": [t for t in timing if t["gap"] is None], "tight": tight, "budget": budget,
  }


# ------------------------------------------------------------------------------------------------------- replay

def timeline(r: dict) -> str:
  """One row per event of the model run, 0 to 1.5 s, with the 1 s budget shaded. The alert row shows the request; the
  hung HMI never delivers it."""
  t = r["t"]
  marks = [("fault", 0.0, "#d03b3b"), ("alert requested", t.get("t_alert_request"), "#2a78d6"),
           ("alert shown", t.get("t_alert"), "#2a78d6"), ("host disengages", t.get("t_disengage"), "#55565c"),
           ("cluster cruise off", t.get("t_cluster"), "#c27a12"), ("panda siren", t.get("t_siren"), "#6250d6")]
  end = 1.5
  W, L, R, rh, T = 440, 112, 60, 20, 8
  X = lambda v: L + (W - L - R) * v / end
  H = T + rh * len(marks) + 18
  out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Event timeline of the model run '
         f'{esc(td.fset(r["events"]))}" font-size="12">',
         f'<rect x="{X(0):.1f}" y="{T}" width="{X(1.0) - X(0):.1f}" height="{rh * len(marks)}" class="budget"/>',
         f'<text x="{X(1.0) - 4:.1f}" y="{H - 4}" text-anchor="end" class="tlm">1.0 s budget</text>']
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
  r, d = replay(), sweep_data()
  b = d["budget"]
  o, wo = r["outcome"], r["without_cancel"]
  tight = d["tight"]
  sets = lambda cs: ", ".join(f"<code>{esc(td.fset(c))}</code>" for c in cs[:4]) + (" and others" if len(cs) > 4 else "")
  finds = [
    kit.finding("g" if not d["gaps"] else "c",
                "No fault set missing from the tree" if not d["gaps"] else f"{len(d['gaps'])} sets missing from the tree",
                f"Every one of the {len(d['model'])} minimal sets the model finds holds an effective WP-A-04 cut set."
                if not d["gaps"] else "Sets: " + ", ".join(esc(td.fset(c)) for c in d["gaps"])),
  ]
  if d["by_siren"]:
    finds.append(kit.finding("w", f"{len(d['by_siren'])} tree sets need a siren failure too",
                             f"{sets(d['by_siren'])}: the siren sounds on a heartbeat loss and on the engaged mismatch "
                             "after a selfdrived stop (TSR-516), so the tree's latent BE-2.14 is out of date for them."))
  if d["by_cancel"]:
    finds.append(kit.finding("w", f"{len(d['by_cancel'])} tree sets need a failed ACC cancel too",
                             f"{sets(d['by_cancel'])}: an immediate disable sends the ACC cancel (TSR-303), so the "
                             "cluster cruise indicator changes in time, and a cancel without effect gets the cancel-lag "
                             "siren (TSR-516(c)). The tree holds BE-6.06 latent; it holds only during a soft disable."))
  if tight:
    finds.append(kit.finding("w", f"Tightest cue in budget: {tight['gap']:.2f} s",
                             f"<code>{esc(td.fset(tight['set']))}</code> ({esc(tight['row'])}) is cued by the "
                             f"{esc(tight['cue'])} {b - tight['gap']:.2f} s inside the {b:g} s budget."))
  if d["late"]:
    worst = max(d["late"], key=lambda t: (t["gap"], t["set"]))
    finds.append(kit.finding("c", f"{len(d['late'])} sets cued after the budget",
                             f"Latest: <code>{esc(td.fset(worst['set']))}</code> ({esc(worst['row'])}), "
                             f"{worst['gap']:.2f} s by the {esc(worst['cue'])}."))
  finds.append(kit.finding("w", f"{len(d['none'])} sets with no cue within {sw.HORIZON_S:g} s",
                           "The silent losses of the tree (non-finite or stale accel, a missed lead) and the warning "
                           "failures: the HMI fails with no cancel and no siren."))
  finds.append(kit.finding("w", "No plant case for a loss of deceleration",
                           "The replay is the model's run, not the plant's: the plant has no SG-06 case yet (its "
                           "longitudinal cases L-01 to L-04 are for SG-03 and SG-04). The cancel lag it rests on is not "
                           "measured either (WP-W-02 OI-18)."))

  cue = f"{o.t_cue:.2f} s {o.cue}" if o.t_cue is not None else "none"
  wo_cue = f"{wo.t_cue:.2f} s {wo.cue}" if wo.t_cue is not None else "none"
  return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SG-06 Fault Lab</title>
<!-- Generated by assurance/models/fmdtools/sg06/fault_lab.py. Do not edit by hand. -->
<style>{kit.CSS}</style></head><body>
<div class="top">
  <div><div class="crumb">LionDriver · Fault Lab · SG-06 longitudinal deceleration (TE-06)</div>
  <div class="tt">Model run of {esc(td.fset(r['events']))} and the fmdtools sweep</div></div>
  <div class="sp"></div>
  <span class="pill ok">Sweep: {d['runs']:,} runs · {d['modes']} modes · up to {d['order']} at once</span>
  <span class="pill syn">Synthetic (DSR-12) · no evidence credit</span>
</div>
<div class="wrap">
  <div class="side">
  <div class="card">
    <div class="pad"><p class="h2">{esc(r['text'])}</p>
    <p class="sub">Model run while approaching a slower lead; times in seconds from the fault. The HMI hangs, so the
    take-over alert is requested but never shown.</p></div>
    <div class="pad"><div class="tlw">{timeline(r)}</div></div>
    <div class="hud">
      <div><span>Deceleration lost</span><b>{o.t_lost:.2f} s</b></div>
      <div><span>First cue</span><b style="color:var(--good)">{esc(cue)}</b></div>
      <div><span>Margin to the budget</span><b>{b - (o.t_cue - o.t_lost):.2f} s</b></div>
      <div><span>Cancel fails too (BE-6.06)</span><b style="color:var(--violet)">{esc(wo_cue)}</b></div>
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
      <p class="sub">Minimal fault sets of up to {d['order']} modes, approaching a lead</p>
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
      <p class="h2">Pairs that lose deceleration without a cue in time</p>
      <p class="sub">Order-2 minimal sets, approaching a lead. A ring on an empty cell is a tree pair that the model
      only loses with a siren or cancel failure as well</p>
      <div class="leg"><span><i style="background:var(--te)"></i>minimal pair in the model</span>
      <span>○ minimal pair in the tree</span></div>
      {kit.matrix(d, "lose deceleration without a cue in time")}
    </div>
  </div>
</div>
<p class="foot">Sources: <code>p3-minimal-sets.json</code>, a fresh P4 run of the model (<code>sweep.py</code>), and the
model's run of {esc(td.fset(r['events']))}. Generated by <code>fault_lab.py</code>; CI rebuilds and compares it.</p>
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
