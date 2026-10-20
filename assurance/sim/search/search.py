#!/usr/bin/env python3
"""Search for unknown failure regions (WP-V-04 U-4; roadmap S5) in the fault-injection plant model.

    python3 assurance/sim/search/search.py            # run, write ../results/search-curve-assist-loss.md and a figure
    python3 assurance/sim/search/search.py --check    # fail if the committed outputs differ from a fresh run

Family searched: loss of lateral assistance in a highway curve, injected as the EPS fault of case F-07 (the panda
refuses LKA at once; the modelled host keeps commanding, so the arrival check revokes after 50 ms and the siren sounds
about 0.25 s after the fault, TSR-516(b), DQ-404 A; the 0.7 s EPS-fault persistence, DQ-048, comes later). The parameters are the road (speed, curve lateral acceleration,
lane width) and the driver assumptions (reaction time, drift cue). Robustness is the margin from the body edge to the
lane line, rho = (lane width - vehicle width) / 2 - max |lateral offset|; rho < 0 is a departure from the lane.

Two methods, both seeded and deterministic:
  - Monte Carlo: uniform samples over the box, to map where departures happen;
  - cross-entropy falsification: a Gaussian over the box is refitted to the lowest-rho fifth of each round, to find
    the worst cases.

Scenic and VerifAI were the intended tools; they are not used because Scenic 3.x requires rv-ltl, which is published
without a licence (README §5). The share of departing samples is a property of the sampled box, not a probability
of anything on the road: the box is uniform by construction, not an exposure distribution. Synthetic data (DSR-12);
no evidence credit.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
sys.path.insert(0, str(SIM / "plant"))

import corolla  # noqa: E402
from roads import lane_line_threshold  # noqa: E402
from simulate import Case, simulate  # noqa: E402

TABLE = SIM / "results" / "search-curve-assist-loss.md"
FIGURE = SIM / "figures" / "fig-search-curve-assist-loss.svg"
SEED = 20261016
MC_SAMPLES = 120
CE_ROUNDS, CE_PER_ROUND, CE_ELITE = 4, 30, 0.2

# name: (low, high, unit, meaning)
SPACE = {
  "speed_kph": (80.0, 110.0, "km/h", "ego speed (ODD-H up to 110 km/h, DQ-260)"),
  "a_y": (0.0, 1.8, "m/s²", "steady lateral acceleration of the curve, from straight to 1.8 m/s²: above LAT_ACCEL_FACTOR "
          "(1.99 m/s²) the item cannot hold the curve even without a fault (plant case N-3), so the band to the ODD bound "
          "2.5 m/s² is left out"),
  "lane_width": (3.0, 3.9, "m", "lane width (ODD-H 3.0–3.9 m)"),
  "t_r": (0.75, 1.5, "s", "driver reaction time from the first cue (WP-S-04 §3.2 range)"),
  "cue": (0.1, 0.3, "m", "drift at which the driver notices (assumption, WP-C-08 to replace)"),
}
NAMES = list(SPACE)
LOW = np.array([SPACE[n][0] for n in NAMES])
HIGH = np.array([SPACE[n][1] for n in NAMES])


def evaluate(x: np.ndarray) -> dict:
  p = dict(zip(NAMES, (float(v) for v in x)))
  road = f"curve@{p['a_y']:.6f}" if p["a_y"] > 1e-3 else "straight"
  case = Case("S", "search", "eps_fault", road, "SG-02", "SFM-005", t_fault=7.0, duration=6.0,
              speed_kph=p["speed_kph"], lane_width=p["lane_width"])
  r = simulate(case, {"driver_t_r_s": p["t_r"], "driver_lat_cue_m": p["cue"]})
  thr = lane_line_threshold(p["lane_width"], corolla.as_dict()["width"])
  m = r.metrics
  return {**p, "rho": thr - m["max_offset"],
          "t_edge": next((t - r.t0 for t, e in zip(r.t, r.e_y) if t >= r.t0 and abs(e) >= thr), None)}


def monte_carlo(rng) -> list[dict]:
  xs = LOW + (HIGH - LOW) * rng.random((MC_SAMPLES, len(NAMES)))
  return [evaluate(x) for x in xs]


def cross_entropy(rng) -> list[dict]:
  mean, std = (LOW + HIGH) / 2, (HIGH - LOW) / 2
  out = []
  for k in range(CE_ROUNDS):
    xs = np.clip(mean + std * rng.standard_normal((CE_PER_ROUND, len(NAMES))), LOW, HIGH)
    rnd = [{**evaluate(x), "round": k + 1} for x in xs]
    out += rnd
    elite = sorted(rnd, key=lambda r: r["rho"])[:max(2, int(CE_ELITE * CE_PER_ROUND))]
    ex = np.array([[e[n] for n in NAMES] for e in elite])
    mean, std = ex.mean(axis=0), np.maximum(ex.std(axis=0), 0.02 * (HIGH - LOW))
  return out


# ------------------------------------------------------------------------------------------------ outputs
def f(v, nd=2):
  return "—" if v is None else f"{v:.{nd}f}".replace("-0.00", "0.00")


def band_table(mc: list[dict], key: str, edges: list[float], label: str) -> list[str]:
  rows = [f"| {label} | Samples | Departures | Share | Smallest margin rho (m) |", "|---|---|---|---|---|"]
  for lo, hi in zip(edges, edges[1:]):
    sel = [r for r in mc if lo <= r[key] < hi or (hi == edges[-1] and r[key] == hi)]
    dep = [r for r in sel if r["rho"] < 0]
    share = f"{len(dep) / len(sel):.0%}" if sel else "—"
    rows.append(f"| {lo:g}–{hi:g} | {len(sel)} | {len(dep)} | {share} | {f(min((r['rho'] for r in sel), default=None))} |")
  return rows


def table(mc: list[dict], ce: list[dict]) -> str:
  dep = [r for r in mc if r["rho"] < 0]
  worst = sorted(ce, key=lambda r: r["rho"])[:5]
  # the mildest curve that still departs, and the sharpest that does not, among Monte Carlo samples
  hold = [r for r in mc if r["rho"] >= 0]
  out = [
    "# Search: loss of lateral assistance in a highway curve",
    "",
    "> **Synthetic data (DSR-12).** Generated by [`search/search.py`](../search/search.py); do not edit by hand. "
    "Fault-injection plant model with the real panda safety code; EPS, driver and vehicle are models with stated "
    "assumptions ([plant results](plant-results.md), Model inputs). **No evidence credit.** The share of departing "
    "samples is a property of the uniform box below, not a probability of anything on the road.",
    "",
    "| Label (WP-V-02 §5.3.5) | Value |",
    "|---|---|",
    "| data_kind | synthetic |",
    "| simulator | LionDriver fault-injection plant model, fidelity L1 (`assurance/sim/plant`), case kind `eps_fault` (F-07) |",
    "| asset archive hash | none (nothing is rendered) |",
    "| scenario ID and family | generic highway curve; closest WP-V-03 scenario KS-01, family SF-1 |",
    "| fidelity-case status | none |",
    "| credit | none |",
    "| camera frame rate | not applicable (no camera) |",
    "",
    "Fault: EPS fault with loss of assist (LKA_STATE 9) in the steady part of a left curve; the panda refuses LKA from "
    "the first fault frame. The modelled host keeps commanding, so its frames are refused and the arrival check revokes "
    "authority after 50 ms; that revocation sounds the siren about 0.25 s after the fault (T-34, TSR-516(b), DQ-404 A), "
    "before the 0.7 s EPS-fault persistence would (T-28, DQ-048). The driver reacts t_r after the first cue (the "
    "siren or a drift of `cue` metres) and corrects with up to 4 m/s². Robustness rho = (lane width − 1.781 m) / 2 − "
    "max |lateral offset| from the fault to the end of the run (6 s); rho < 0 means the body edge crossed the lane "
    "line. Beyond about −2 m the car is in the next lane and the magnitude means little; the sign and the time to the "
    "line are what count.",
    "",
    "## Search space",
    "",
    "| Parameter | Range | Meaning |",
    "|---|---|---|",
    *[f"| `{n}` | {lo:g}–{hi:g} {u} | {m} |" for n, (lo, hi, u, m) in SPACE.items()],
    "",
    f"Monte Carlo: {MC_SAMPLES} uniform samples. Cross-entropy: {CE_ROUNDS} rounds of {CE_PER_ROUND}, elite fifth. "
    f"Seed {SEED}.",
    "",
    "## Monte Carlo: where departures happen",
    "",
    f"{len(dep)} of {len(mc)} samples depart from the lane ({len(dep) / len(mc):.0%}). By curve lateral acceleration "
    "and by driver reaction time:",
    "",
    *band_table(mc, "a_y", [0.0, 0.3, 0.6, 0.9, 1.2, 1.5, 1.8], "Curve a_y (m/s²)"),
    "",
    *band_table(mc, "t_r", [0.75, 1.0, 1.25, 1.5], "Driver t_r (s)"),
    "",
    f"Mildest departing curve among the samples: a_y = {f(min((r['a_y'] for r in dep), default=None))} m/s². "
    f"Sharpest curve held in lane: a_y = {f(max((r['a_y'] for r in hold), default=None))} m/s².",
    "",
    "## Cross-entropy falsification: worst cases found",
    "",
    "| Round | Speed (km/h) | a_y (m/s²) | Lane (m) | t_r (s) | Cue (m) | rho (m) | Body edge on the line (s) |",
    "|---|---|---|---|---|---|---|---|",
    *[f"| {r['round']} | {r['speed_kph']:.1f} | {r['a_y']:.2f} | {r['lane_width']:.2f} | {r['t_r']:.2f} | "
      f"{r['cue']:.2f} | {f(r['rho'])} | {f(r['t_edge'])} |" for r in worst],
    "",
    "Use: these points rank where a closed-course or bench test should look first (WP-V-04 U-4, WP-V-05 VS-FI-31). They "
    "do not show that the item departs on the road: the EPS response to the fault, the driver and the steering "
    "authority are assumptions until measured (M-01, M-02, WP-C-08).",
  ]
  return "\n".join(out) + "\n"


STYLE = """<style>
svg { --bg:#ffffff; --ink:#0b0b0b; --ink2:#52514e; --grid:#e3e2de; --ok:#2a78d6; --bad:#e34948; --ce:#eda100; }
@media (prefers-color-scheme: dark) {
  svg { --bg:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --grid:#33322f; --ok:#3987e5; --bad:#e66767; --ce:#c98500; }
}
.bg { fill:var(--bg); } .t { font:12px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.t2 { font:11px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink2); }
.th { font:600 15px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.grid { stroke:var(--grid); stroke-width:1; } .ok { fill:var(--ok); } .bad { fill:var(--bad); }
.ce { fill:none; stroke:var(--ce); stroke-width:1.6; }
</style>"""


def figure(mc: list[dict], ce: list[dict]) -> str:
  W, H, x0, x1, y0, y1 = 900, 520, 80, 860, 80, 460
  lo_a, hi_a, lo_t, hi_t = SPACE["a_y"][0], SPACE["a_y"][1], SPACE["t_r"][0], SPACE["t_r"][1]

  def X(a):
    return x0 + (a - lo_a) / (hi_a - lo_a) * (x1 - x0)

  def Y(t):
    return y1 - (t - lo_t) / (hi_t - lo_t) * (y1 - y0)

  out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">',
         '<title id="t">Search: loss of lateral assistance in a highway curve, departures by curve lateral acceleration and driver reaction time</title>',
         '<desc id="d">Synthetic data (DSR-12), no evidence credit. Monte Carlo samples of the plant model, filled red when '
         'the body edge crossed the lane line and blue when it stayed in the lane, against the curve lateral acceleration '
         '(horizontal) and the driver reaction time (vertical); rings are the cross-entropy worst cases.</desc>', STYLE,
         f'<rect class="bg" width="{W}" height="{H}"/>',
         f'<text x="40" y="36" class="th">{escape("Loss of lateral assistance in a curve: where the body edge crosses the lane line")}</text>',
         f'<text x="40" y="56" class="t2">{escape("Synthetic data (DSR-12) · no evidence credit · EPS fault (F-07), plant model L1 · speed, lane width and cue also vary")}</text>']
  for a in np.arange(0.0, 1.81, 0.3):
    out.append(f'<line x1="{X(a):.1f}" y1="{y0}" x2="{X(a):.1f}" y2="{y1}" class="grid"/>')
    out.append(f'<text x="{X(a):.1f}" y="{y1 + 18}" class="t2" text-anchor="middle">{a:.1f}</text>')
  for t in (0.75, 1.0, 1.25, 1.5):
    out.append(f'<line x1="{x0}" y1="{Y(t):.1f}" x2="{x1}" y2="{Y(t):.1f}" class="grid"/>')
    out.append(f'<text x="{x0 - 8}" y="{Y(t) + 4:.1f}" class="t2" text-anchor="end">{t:g}</text>')
  out.append(f'<text x="{(x0 + x1) / 2}" y="{y1 + 40}" class="t" text-anchor="middle">Curve lateral acceleration a_y (m/s²)</text>')
  out.append(f'<text x="24" y="{(y0 + y1) / 2}" class="t" text-anchor="middle" transform="rotate(-90 24 {(y0 + y1) / 2})">Driver reaction time t_r (s)</text>')
  for r in mc:
    cls = "bad" if r["rho"] < 0 else "ok"
    out.append(f'<circle cx="{X(r["a_y"]):.1f}" cy="{Y(r["t_r"]):.1f}" r="4" class="{cls}"><title>rho {r["rho"]:.2f} m, '
               f'{r["speed_kph"]:.0f} km/h, lane {r["lane_width"]:.2f} m</title></circle>')
  for r in sorted(ce, key=lambda r: r["rho"])[:5]:
    out.append(f'<circle cx="{X(r["a_y"]):.1f}" cy="{Y(r["t_r"]):.1f}" r="8" class="ce"/>')
  lx = x1 - 210
  out += [f'<circle cx="{lx}" cy="72" r="4" class="bad"/><text x="{lx + 10}" y="76" class="t2">departs (rho &lt; 0)</text>',
          f'<circle cx="{lx + 110}" cy="72" r="4" class="ok"/><text x="{lx + 120}" y="76" class="t2">stays in lane</text>',
          "</svg>"]
  return "\n".join(out) + "\n"


def build() -> dict[Path, str]:
  rng = np.random.default_rng(SEED)
  mc = monte_carlo(rng)
  ce = cross_entropy(rng)
  return {TABLE: table(mc, ce), FIGURE: figure(mc, ce)}


def main(argv) -> int:
  files = build()
  if "--check" in argv:
    stale = [p for p, c in files.items() if not p.exists() or p.read_text(encoding="utf-8") != c]
    for p in stale:
      print(f"stale: {p.relative_to(SIM)}", file=sys.stderr)
    if stale:
      print("run: python3 assurance/sim/search/search.py", file=sys.stderr)
      return 1
    print(f"search: {len(files)} file(s) current")
    return 0
  for p, c in files.items():
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(c, encoding="utf-8")
  print(f"search: wrote {len(files)} file(s)")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
