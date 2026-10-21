#!/usr/bin/env python3
"""Search for unknown failure regions (WP-V-04 U-4; roadmap S5) in the fault-injection plant model.

    python3 assurance/sim/search/search.py              # run every family; write ../results/search-*.md, the figure
                                                        # and the edge-case catalogue ../results/edge-cases.md
    python3 assurance/sim/search/search.py --check      # fail if the committed outputs differ from a fresh run
    python3 assurance/sim/search/search.py --jobs 4     # worker processes (default: every CPU; results do not depend on it)

A family is data (families.yaml): the plant fault, the road, the case and assumptions, the search box and the
robustness measure. The first family, loss of lateral assistance in a highway curve, is the EPS fault of case F-07
(the panda refuses LKA at once; the modelled host keeps commanding, so the arrival check revokes after 50 ms and the
siren sounds about 0.25 s after the fault, TSR-516(b), DQ-404 A; the 0.7 s EPS-fault persistence, DQ-048, comes later)
over the road (speed, curve lateral acceleration, lane width) and the driver assumptions (reaction time, drift cue);
its page and figure are the ones this script wrote before families were data. Robustness is the margin from the body
edge to the lane line, rho = (lane width - vehicle width) / 2 - max |lateral offset|; rho < 0 is a departure from the
lane. The longitudinal and hand-over families measure the smallest bumper gap to the lead or the follower instead;
rho < 0 is contact.

Two methods, both seeded and deterministic:
  - Monte Carlo: uniform samples over the box, to map where departures happen;
  - cross-entropy falsification: a Gaussian over the box is refitted to the lowest-rho fifth of each round, to find
    the worst cases.
The catalogue takes the worst cases of every family, re-runs each with its parameters rounded as a scene would write
them, without the fault, and under assumption probes (which assumption decides the outcome), and maps each to the
HARA hazardous event or SOTIF hazard it falls under.

Scenic and VerifAI were the intended tools; they are not used because Scenic 3.x requires rv-ltl, which is published
without a licence (README §5). The share of departing samples is a property of the sampled box, not a probability
of anything on the road: the box is uniform by construction, not an exposure distribution. Synthetic data (DSR-12);
no evidence credit.
"""

from __future__ import annotations

import dataclasses
import math
import multiprocessing as mp
import os
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
sys.path.insert(0, str(SIM / "plant"))

import cases  # noqa: E402
import corolla  # noqa: E402
import simulate as plant_sim  # noqa: E402
from simulate import Case, simulate  # noqa: E402

RESULTS = SIM / "results"
CATALOGUE = RESULTS / "edge-cases.md"
SCENES = SIM / "blender" / "scenes.yaml"
FAMILY_FILE = HERE / "families.yaml"
SPEC = yaml.safe_load(FAMILY_FILE.read_text(encoding="utf-8"))
FAMILIES = {f["id"]: f for f in SPEC["families"]}
WIDTH = corolla.as_dict()["width"]

# the catalog case each fault kind's scene starts from (faults.yaml); hardover_left is F-01b mirrored
CATALOG_CASE = {"hardover": "F-01b", "hardover_left": "F-01b", "frozen": "F-03", "soc_stall": "F-04b",
                "eps_fault": "F-07", "none": "N-1"}
FAULT_TEXT = {"hardover": "F-01b hard-over (right)", "hardover_left": "F-01b mirrored (left)",
              "frozen": "F-03 frozen command", "soc_stall": "F-04b SoC stall", "eps_fault": "F-07 EPS fault",
              "decel_lost": "deceleration silently lost (F-02 M01)", "accel_max": "L-01 acceleration +2.0 m/s²",
              "accel_overlimit": "L-02 acceleration +4.0 m/s²", "decel_min": "L-03 deceleration step −3.5 m/s²",
              "decel_overlimit": "L-04 deceleration −6.0 m/s²", "soft_disable": "fault soft disable",
              "dm_stop": "DM no-response stop"}
# a longitudinal family's scene starts from the L case of its fault kind (else L-03, the follower case)
CATALOG_CASE_LONG = {"accel_max": "L-01", "accel_overlimit": "L-02", "decel_min": "L-03", "decel_overlimit": "L-04"}
LATERAL, LONGITUDINAL = ("lane", "corridor"), ("lead", "follower", "gaps")


def longitudinal(fam: dict) -> bool:
  return fam["robustness"] in LONGITUDINAL


# ------------------------------------------------------------------------------------------------ families
def space(fam: dict) -> dict:
  return fam["space"]


def names(fam: dict) -> list[str]:
  return list(fam["space"])


def bounds(fam: dict) -> tuple[np.ndarray, np.ndarray]:
  lo, hi = [], []
  for spec in fam["space"].values():
    if isinstance(spec, dict):            # a choice: sampled as an index in [0, n)
      lo.append(0.0)
      hi.append(float(len(spec["choice"])))
    else:
      lo.append(float(spec[0]))
      hi.append(float(spec[1]))
  return np.array(lo), np.array(hi)


def params_of(fam: dict, x) -> dict:
  p = {}
  for n, v in zip(names(fam), x):
    spec = fam["space"][n]
    if isinstance(spec, dict):
      p[n] = spec["choice"][min(int(v), len(spec["choice"]) - 1)]
    else:
      p[n] = float(v)
  return p


def value(v, p: dict):
  """A value of families.yaml: "=expr" is a Python expression over the parameters; anything else is literal."""
  if isinstance(v, str) and v.startswith("="):
    return eval(v[1:], {"__builtins__": {}, "math": math, "min": min, "max": max}, dict(p))
  return v


def make_case(fam: dict, p: dict, case_over: dict | None = None) -> tuple[Case, dict]:
  fault = p[fam["fault_param"]] if "fault_param" in fam else value(fam["fault"], p)
  fields = {k: value(v, p) for k, v in fam.get("case", {}).items()}
  if isinstance(fields.get("t_fault"), float):     # a derived onset to the millisecond, as a scene writes it
    fields["t_fault"] = round(fields["t_fault"], 3)
  if longitudinal(fam):                            # and every derived longitudinal field to three places
    fields = {k: round(v, 3) if isinstance(v, float) else v for k, v in fields.items()}
  fields.update(case_over or {})
  fault = fields.pop("fault", fault)
  case = Case("S", "search", fault, value(fam["road"], p), "", "", **fields)
  assume = {k: value(v, p) for k, v in fam.get("assumptions", {}).items()}
  return case, assume


def robustness(fam: dict, case: Case, r) -> dict:
  """rho and the time from the fault to the first line crossing, and the side of the worst excursion."""
  thr = r.metrics["lane_threshold"]
  lw = 2 * thr + WIDTH
  after = [(t - r.t0, e) for t, e in zip(r.t, r.e_y) if t >= r.t0]
  if fam["robustness"] == "lane":
    rho = thr - r.metrics["max_offset"]
    t_edge = next((t - r.t0 for t, e in zip(r.t, r.e_y) if t >= r.t0 and abs(e) >= thr), None)
    worst = max(after, key=lambda te: abs(te[1]))[1]
    side = "left" if worst > 0 else "right"
  elif fam["robustness"] == "corridor":       # the ego lane and the lane to its left
    lo = min(e for _, e in after) + thr
    hi = lw + thr - max(e for _, e in after)
    rho, side = (lo, "right") if lo < hi else (hi, "left")
    t_edge = next((t for t, e in after if e <= -thr or e >= lw + thr), None)
  elif fam["robustness"] in LONGITUDINAL:     # bumper gaps to the lead and the follower
    rho, side, t_edge, impact = math.inf, None, None, None
    for k, name in enumerate(("lead", "follower")):
      if fam["robustness"] not in (name, "gaps"):
        continue
      g = [(t - r.t0, gg[k]) for t, gg in zip(r.t, r.gap) if t >= r.t0]
      m = min(x for _, x in g)
      if m < rho:
        rho, side = m, name
        i = next((i for i, (_, x) in enumerate(g) if x <= 0), None)
        t_edge = g[i][0] if i is not None else None
        impact = 3.6 * (g[i - 1][1] - g[i][1]) / (g[i][0] - g[i - 1][0]) if i else None
  else:
    raise ValueError(fam["robustness"])
  ev = r.metrics["events"]
  out = {"rho": rho, "t_edge": t_edge, "side": side, "cue_kind": next((k[12:-1] for k in ev if k.startswith("driver cue")), None),
         "t_correction": ev.get("driver correction"), "revoked": "authority revoked" in ev}
  if fam["robustness"] in LONGITUDINAL:
    out["impact_kph"] = impact
  return out


def run(fam: dict, p: dict, assume_over: dict | None = None, case_over: dict | None = None) -> dict:
  case, assume = make_case(fam, p, case_over)
  r = simulate(case, {**assume, **(assume_over or {})})
  return robustness(fam, case, r)


def _run_job(job) -> dict:
  fid, p, assume_over, case_over = job
  return run(FAMILIES[fid], p, assume_over, case_over)


def _evaluate(job) -> dict:
  fid, x = job
  fam = FAMILIES[fid]
  p = params_of(fam, x)
  out = run(fam, p)
  if fam.get("layout") == "legacy-curve":     # the keys the first family's page has always used
    return {**p, "rho": out["rho"], "t_edge": out["t_edge"], "_x": list(x)}
  return {**p, **out, "_x": list(x)}


_POOL = None


def evaluate_many(fid: str, xs) -> list[dict]:
  jobs = [(fid, tuple(float(v) for v in x)) for x in xs]
  if _POOL is None:
    return [_evaluate(j) for j in jobs]
  return _POOL.map(_evaluate, jobs, chunksize=1)


def monte_carlo(fam: dict, rng) -> list[dict]:
  lo, hi = bounds(fam)
  xs = lo + (hi - lo) * rng.random((fam["mc"], len(lo)))
  return evaluate_many(fam["id"], xs)


def cross_entropy(fam: dict, rng) -> list[dict]:
  lo, hi = bounds(fam)
  rounds, per, elite_share = fam["ce"]["rounds"], fam["ce"]["per_round"], fam["ce"]["elite"]
  mean, std = (lo + hi) / 2, (hi - lo) / 2
  out = []
  for k in range(rounds):
    xs = np.clip(mean + std * rng.standard_normal((per, len(lo))), lo, hi)
    rnd = [{**r, "round": k + 1} for r in evaluate_many(fam["id"], xs)]
    out += rnd
    elite = sorted(rnd, key=lambda r: r["rho"])[:max(2, int(elite_share * per))]
    ex = np.array([e["_x"] for e in elite])
    mean, std = ex.mean(axis=0), np.maximum(ex.std(axis=0), 0.02 * (hi - lo))
  return out


def search(fam: dict) -> tuple[list[dict], list[dict]]:
  rng = np.random.default_rng(fam["seed"])
  return monte_carlo(fam, rng), cross_entropy(fam, rng)


# the first family under the names this module has always had (test_search.py and the legacy page use them)
LEGACY = FAMILIES["curve-assist-loss"]
TABLE = RESULTS / LEGACY["page"]
FIGURE = SIM / "figures" / LEGACY["figure"]
SEED = LEGACY["seed"]
MC_SAMPLES = LEGACY["mc"]
CE_ROUNDS, CE_PER_ROUND, CE_ELITE = LEGACY["ce"]["rounds"], LEGACY["ce"]["per_round"], LEGACY["ce"]["elite"]
SPACE = {n: tuple(v) for n, v in LEGACY["space"].items()}   # name: (low, high, unit, meaning)
NAMES = list(SPACE)
LOW, HIGH = bounds(LEGACY)


def evaluate(x: np.ndarray) -> dict:
  """One sample of the first family (speed, a_y, lane width, t_r, cue)."""
  r = _evaluate(("curve-assist-loss", tuple(float(v) for v in x)))
  return {k: v for k, v in r.items() if k != "_x"}


# ------------------------------------------------------------------------------------------------ outputs
def f(v, nd=2):
  return "—" if v is None else f"{v:.{nd}f}".replace("-0.00", "0.00")


def band_table(mc: list[dict], key: str, edges: list[float], label: str, what: str = "Departures",
               rho: str = "Smallest margin rho (m)") -> list[str]:
  rows = [f"| {label} | Samples | {what} | Share | {rho} |", "|---|---|---|---|---|"]
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


def build_legacy() -> dict[Path, str]:
  mc, ce = search(LEGACY)
  return {TABLE: table(mc, ce), FIGURE: figure(mc, ce)}, (mc, ce)


# ------------------------------------------------------------------------------------------------ generic pages
BANNER = ("> **Synthetic data (DSR-12).** Generated by [`search/search.py`](../search/search.py) from "
          "[`search/families.yaml`](../search/families.yaml); do not edit by hand. Fault-injection plant model with the "
          "real panda safety code; EPS, driver and vehicle are models with stated assumptions ([plant results]"
          "(plant-results.md), Model inputs). **No evidence credit.** The share of departing samples is a property of "
          "the uniform box below, not a probability of anything on the road.")

LIMITS_LONG = ("What the plant cannot show: it has **no tyre friction limit** (the driver's braking of up to 8 m/s² and "
               "the lead's are taken as given on any road; on a wet road (W02) about 5 m/s² is what the tyres give, so a "
               "row that needs more is worse there) and **no perception** (the ACC sees its lead at once, exactly and at "
               "any range, so a lead detected late, a stopped vehicle not taken as a lead (SH-06) or a cut-in is not "
               "searched; low visibility acts only through the driver). The ACC is a model, not openpilot's MPC; the "
               "lead brakes at a constant rate; the following driver brakes after a reaction time to the ego's brake "
               "lights (on above 1 m/s²) at a set deceleration until no faster than the ego, and does not steer round "
               "it. The driver is a model with stated cues and reactions; the PCM response is assumed (M-03).")

LIMITS = ("What the plant cannot show: it has **no tyre friction limit** (a linear tyre: a wet or icy road, a "
          "braking driver in a curve and a correction of 4 m/s² all behave as on a dry road, so nothing here says "
          "whether the car would slide) and **no perception** (the lane-keeping controller sees its lane exactly, so "
          "no perception insufficiency, wrong line or late detection is searched; the faults are injected at the "
          "actuator side). The driver is a model with stated reactions, the EPS response to each fault is assumed "
          "(M-01, M-02), and road users beside the ego are not modelled: the time to the lane line is how soon an "
          "adjacent vehicle or barrier would be reached, not whether it is hit.")


def fmt_param(fam: dict, n: str, v) -> str:
  spec = fam["space"][n]
  if isinstance(spec, dict):
    return str(v)
  return f"{v:.1f}" if spec[1] >= 100 else f"{v:.2f}"


def page_name(fam: dict) -> str:
  return fam.get("page", f"search-{fam['id']}.md")


def generic_page(fam: dict, mc: list[dict], ce: list[dict]) -> str:
  ns = names(fam)
  dep = [r for r in mc if r["rho"] < 0]
  lng = longitudinal(fam)
  what = "Contacts" if lng else "Departures"
  kinds = sorted({FAULT_TEXT.get(r[fam["fault_param"]], r[fam["fault_param"]]) for r in mc}) if "fault_param" in fam \
    else [fam["fault"]]
  out = [
    f"# Search: {fam['title']}",
    "",
    BANNER,
    "",
    "| Label (WP-V-02 §5.3.5) | Value |",
    "|---|---|",
    "| data_kind | synthetic |",
    f"| simulator | LionDriver fault-injection plant model, fidelity L1 (`assurance/sim/plant`), family `{fam['id']}` |",
    "| asset archive hash | none (nothing is rendered) |",
    f"| scenario ID and family | generic highway; {'longitudinal' if lng else 'lateral'} family of the [edge-case "
    "catalogue](edge-cases.md) |",
    "| fidelity-case status | none |",
    "| credit | none |",
    "| camera frame rate | not applicable (no camera) |",
    "",
    " ".join(fam["about"].split()),
    "",
    f"Faults: {', '.join(kinds)}. Robustness: "
    + ({"lane": "rho = (lane width − 1.781 m) / 2 − max |lateral offset| after the fault; rho < 0 means the body edge "
                "crossed a lane line.",
        "corridor": "rho is the margin of the body edge to the outer lines of the ego lane and the lane to its left "
                    "after the fault; rho < 0 means it crossed one.",
        "lead": "rho = the smallest bumper gap to the lead after the fault; rho < 0 means contact.",
        "follower": "rho = the smallest bumper gap to the following vehicle after the fault; rho < 0 means contact.",
        "gaps": "rho = the smaller of the smallest bumper gaps to the lead and to the follower after the fault; rho < 0 "
                "means contact (Side says with which)."}[fam["robustness"]])
    + (" Past contact the plant lets the vehicles overlap, so a negative magnitude means little; the sign, the time "
       "to contact and the closing speed at contact are what count." if lng else
       " Beyond about −2 m the car is in the next lane and the magnitude means little; the sign and the time to the "
       "line are what count."),
    "",
    LIMITS_LONG if lng else LIMITS,
    "",
    "## Search space",
    "",
    "| Parameter | Range | Meaning |",
    "|---|---|---|",
  ]
  for n in ns:
    spec = fam["space"][n]
    if isinstance(spec, dict):
      out.append(f"| `{n}` | {', '.join(spec['choice'])} | {spec['meaning']} |")
    else:
      out.append(f"| `{n}` | {spec[0]:g}–{spec[1]:g}{'' if spec[2] == '—' else ' ' + spec[2]} | {spec[3]} |")
  out += ["", f"Monte Carlo: {fam['mc']} uniform samples. Cross-entropy: {fam['ce']['rounds']} rounds of "
          f"{fam['ce']['per_round']}, elite share {fam['ce']['elite']:g}. Seed {fam['seed']}.", "",
          f"## Monte Carlo: where {what.lower()} happen", "",
          f"{len(dep)} of {len(mc)} samples {'end in contact' if lng else 'depart'} ({len(dep) / len(mc):.0%}).", ""]
  for n in ns:
    spec = fam["space"][n]
    if not isinstance(spec, dict):
      continue
    out += [f"| `{n}` | Samples | {what} | Share | Smallest rho (m) | Median time to "
            f"{'contact' if lng else 'the line'} (s) |",
            "|---|---|---|---|---|---|"]
    for c in spec["choice"]:
      sel = [r for r in mc if r[n] == c]
      d = [r for r in sel if r["rho"] < 0]
      tl = sorted(r["t_edge"] for r in d if r["t_edge"] is not None)
      out.append(f"| {c} | {len(sel)} | {len(d)} | {f'{len(d) / len(sel):.0%}' if sel else '—'} | "
                 f"{f(min((r['rho'] for r in sel), default=None))} | {f(tl[len(tl) // 2] if tl else None)} |")
    out.append("")
  for n, edges in fam.get("bands", {}).items():
    out += band_table(mc, n, edges, f"`{n}`", what, "Smallest gap rho (m)" if lng else "Smallest margin rho (m)") + [""]
  worst = sorted(ce, key=lambda r: r["rho"])[:5]
  out += ["## Cross-entropy falsification: worst cases found", "",
          "| Round | " + " | ".join(f"`{n}`" for n in ns) + " | rho (m) | "
          + ("Contact (s) | Closing at contact (km/h) | With |" if lng else "Line crossed (s) | Side |"),
          "|---|" + "---|" * len(ns) + "---|---|---|" + ("---|" if lng else "")]
  for r in worst:
    out.append(f"| {r['round']} | " + " | ".join(fmt_param(fam, n, r[n]) for n in ns)
               + f" | {f(r['rho'])} | {f(r['t_edge'])} | " + (f"{f(r['impact_kph'], 1)} | " if lng else "")
               + f"{r['side']} |")
  out += ["", "The worst case of each fault (or behaviour), re-run with rounded parameters, without the fault and under "
          "assumption probes, is in the [edge-case catalogue](edge-cases.md).", "",
          "Use: these points rank where a closed-course or bench test should look first (WP-V-04 U-4, WP-V-05). They do "
          + ("not show that the item collides on the road: the PCM response, the ACC, the drivers of the ego and of "
             "the following vehicle are assumptions until measured (M-03, WP-C-08)." if lng else
             "not show that the item departs on the road: the EPS response to the fault, the driver and the steering "
             "authority are assumptions until measured (M-01, M-02, WP-C-08).")]
  return "\n".join(out) + "\n"


# ------------------------------------------------------------------------------------------------ catalogue
DYNAMIC_FIELDS = [f.name for f in dataclasses.fields(Case) if f.name not in
                  ("id", "title", "sg", "fmea", "wpv05", "figure", "note", "tsr")]


def rounded(fam: dict, p: dict) -> dict:
  return {n: v if isinstance(fam["space"][n], dict) else round(v, 1 if fam["space"][n][1] >= 100 else 2)
          for n, v in p.items() if n in fam["space"]}


def reproduce(fam: dict, p: dict) -> dict:
  """The scene fields that reproduce a row: catalog case, case_overrides and assumptions (blender/scenes.yaml)."""
  case, assume = make_case(fam, p)
  base_id = CATALOG_CASE_LONG.get(case.fault, "L-03") if longitudinal(fam) else CATALOG_CASE[case.fault]
  base = {c.id: c for c in cases.all_cases()}[base_id]
  ov = {k: getattr(case, k) for k in DYNAMIC_FIELDS if getattr(case, k) != getattr(base, k)}
  defaults = {k: v[0] for k, v in {**plant_sim.ASSUMPTIONS, **plant_sim.DRIVER_OPTIONS}.items()}
  return {"case": base_id, "case_overrides": ov, "assumptions": {k: v for k, v in assume.items() if v != defaults[k]}}


def classify(fam: dict, row: dict) -> dict:
  if row["rho"] >= 0:
    return {"he": None, "fit": "no contact" if longitudinal(fam) else "stays in the lane"}
  env = {**row["p"], "fault": row["fault"], "side": row["side"], "t_line": row["t_edge"], "rho": row["rho"],
         "rho_nofault": row["rho_nofault"], "impact_kph": row.get("impact_kph")}
  for rule in fam["hara"]:
    if eval(rule["when"], {"__builtins__": {}}, env):
      return rule
  raise SystemExit(f"{fam['id']}: no HARA rule matches {env}")


def catalogue_rows(fam: dict, mc: list[dict], ce: list[dict], start: int) -> list[dict]:
  pool = sorted(mc + ce, key=lambda r: r["rho"])
  spec = fam.get("catalogue", {})
  if "by" in spec:
    picks = [next(r for r in pool if r[spec["by"]] == c) for c in fam["space"][spec["by"]]["choice"]
             if any(r[spec["by"]] == c for r in pool)]
  else:
    picks = pool[:spec.get("per", 1)]
  picks = picks[:spec.get("max", len(picks))]
  prs = SPEC["probes_longitudinal" if longitudinal(fam) else "probes_default"] + fam.get("probes", [])
  nf = {"fault": "none", "fault2": "", "fault_clear": None, "clear_after_correction": None}
  ps = [rounded(fam, pick) for pick in picks]
  jobs = [(fam["id"], p, a, c) for p in ps for a, c in [(None, None), (None, nf)] + [(pr.get("assume"), pr.get("case"))
                                                                                     for pr in prs]]
  outs = _POOL.map(_run_job, jobs, chunksize=1) if _POOL is not None else [_run_job(j) for j in jobs]
  rows = []
  for i, p in enumerate(ps):
    case, _ = make_case(fam, p)
    base, nofault, *po = outs[i * (len(prs) + 2):(i + 1) * (len(prs) + 2)]
    probes = [{"label": pr["label"], "rho": o["rho"], "delta": o["rho"] - base["rho"]} for pr, o in zip(prs, po)]
    row = {"id": f"EC-{start + i:02d}", "family": fam["id"], "fault": case.fault, "p": p, **base,
           "rho_nofault": nofault["rho"], "probes": probes, "reproduce": reproduce(fam, p)}
    row["hara"] = classify(fam, row)
    rows.append(row)
  return rows


def decides(row: dict) -> str:
  lng = longitudinal(FAMILIES[row["family"]])
  top = max(row["probes"], key=lambda q: abs(q["delta"]))
  flips = [q for q in row["probes"] if (q["rho"] < 0) != (row["rho"] < 0)]
  road = ((f"the traffic ends in contact by itself (rho {f(row['rho_nofault'])} m without the fault); " if lng else
           f"the curve departs by itself (rho {f(row['rho_nofault'])} m without the fault); ")
          if row["rho"] < 0 and row["rho_nofault"] < 0 else "")
  if road and row["rho_nofault"] - row["rho"] < 0.5:
    return (f"the traffic: contact without the fault too (rho {f(row['rho_nofault'])} m)" if lng else
            f"the road: departs without the fault too (rho {f(row['rho_nofault'])} m)")
  if flips:
    q = max(flips, key=lambda q: abs(q["delta"]))
    lead = (f"**{q['label']}** turns it "
            + (('into contact' if q['rho'] < 0 else 'to no contact') if lng else
               ('into a departure' if q['rho'] < 0 else 'to in-lane')) + f" (rho {f(q['rho'])} m)")
  elif abs(top["delta"]) >= 0.05:
    lead = f"no probe flips it; {top['label']} moves rho most ({top['delta']:+.2f} m)"
  else:
    lead = "no probed assumption: the fault and the road decide"
  return road + lead


def params_text(fam: dict, row: dict) -> str:
  skip = {fam.get("fault_param")}
  parts = []
  for n in names(fam):
    if n in skip:
      continue
    unit = "" if isinstance(fam["space"][n], dict) else fam["space"][n][2]
    parts.append(f"{n} {fmt_param(fam, n, row['p'][n])}{'' if unit in ('—', '') else ' ' + unit}")
  return ", ".join(parts)


def scenes_by_row() -> dict[str, list[str]]:
  out: dict[str, list[str]] = {}
  for s in yaml.safe_load(SCENES.read_text(encoding="utf-8"))["scenes"]:
    if s.get("edge_case"):
      out.setdefault(s["edge_case"], []).append(s["id"])
  return out


def flow(d: dict) -> str:
  return yaml.safe_dump(d, default_flow_style=True, sort_keys=False, width=10_000).strip()


def hz_text(r: dict) -> str:
  h = r["hara"]
  if h.get("he") is None:
    return "— (no contact)" if longitudinal(FAMILIES[r["family"]]) else "— (in lane)"
  if h.get("new"):
    return f"**none: new** ({h['new']}); nearest {h['he']}"
  return h["he"] + (f", {h['sh']}" if h.get("sh") else "")


def by_road(rows: list[dict]) -> list[dict]:
  """Rows that the road or the traffic decides: they leave or touch by nearly as much without the fault."""
  return [r for r in rows if r["rho"] < 0 and r["rho_nofault"] < 0 and r["rho_nofault"] - r["rho"] < 0.5]


def probe(r: dict, prefix: str) -> dict:
  return next(q for q in r["probes"] if q["label"].startswith(prefix))


def lateral_findings(rows: list[dict]) -> list[str]:
  dep = [r for r in rows if r["rho"] < 0]
  road = by_road(rows)
  flipped = [r for r in rows if any((q["rho"] < 0) != (r["rho"] < 0) for q in r["probes"])]
  fastest = sorted((r for r in dep if r["t_edge"] is not None and r not in road), key=lambda r: r["t_edge"])[:3]
  out = [f"- {len(dep)} of {len(rows)} lateral rows leave the lane. "
         + (f"{len(road)} of them leave it by nearly as much without the fault (the curve at or near R_ODD is beyond "
            "the item's lateral authority, plant case N-3), so the road decides those, not the fault." if road else
            "In every one the fault decides: where the curve departs by itself as well (at R_ODD), the fault adds more "
            "than 0.5 m.")]
  if fastest:
    out.append("- Soonest at the lane line among the rows the fault decides: " + "; ".join(
      f"{r['id']} ({FAULT_TEXT.get(r['fault'], r['fault'])}, {r['family']}) after {r['t_edge']:.2f} s" for r in fastest)
      + ". The driver's reaction time alone is 0.75–1.5 s after the cue.")
  if flipped:
    out.append("- An assumption decides " + ", ".join(r["id"] for r in flipped) + ": one probe turns the outcome "
               "round (Decides column).")
  return out + [low_visibility(rows)]


def low_visibility(rows: list[dict]) -> str:
  late = [(r, probe(r, "drift noticed late")) for r in rows]
  worse = [(r, q) for r, q in late if q["delta"] < -0.05]
  same = [r for r, q in late if abs(q["delta"]) <= 0.05 and r["cue_kind"] == "siren"]
  late_flips = [r for r, q in late if (q["rho"] < 0) != (r["rho"] < 0)]
  return (f"- Low visibility, as a drift noticed at 0.4 m instead of 0.2 m (the plant has no perception, so fog acts "
          f"only through the driver): {len(worse)} rows depart further, by up to "
          f"{max((-q['delta'] for _, q in worse), default=0):.1f} m; "
          + (f"it turns {', '.join(r['id'] for r in late_flips)} round. " if late_flips else "it turns none round. ")
          + (f"Rows the siren cues are unchanged ({', '.join(r['id'] for r in same)}): a silent fault is where poor "
             "visibility costs the driver." if same else ""))


def longitudinal_findings(rows: list[dict]) -> list[str]:
  dep = [r for r in rows if r["rho"] < 0]
  road = by_road(rows)
  out = [f"- {len(dep)} of {len(rows)} longitudinal and hand-over rows end in contact"
         + (": " + "; ".join(f"{r['id']} ({FAULT_TEXT.get(r['fault'], r['fault'])}, with the {r['side']}, at "
                             f"{f(r['impact_kph'], 0)} km/h closing speed)" for r in dep) if dep else "")
         + ". " + (f"{', '.join(r['id'] for r in road)} end in contact by nearly as much without the fault (the "
                   "traffic is beyond what the ACC's −3.5 m/s² and the driver give), so the traffic decides those."
                   if road else "The fault decides each of them: without it there is no contact, or much less.")]
  for prefix, what in (("driver brakes with 8", "Braking hard"), ("driver brakes with 3", "Braking at the plant's "
                                                                  "default 3 m/s²")):
    flips = [r for r in rows if (probe(r, prefix)["rho"] < 0) != (r["rho"] < 0)]
    if flips:
      out.append(f"- {what} turns {', '.join(r['id'] for r in flips)} round: there the driver's braking decides, "
                 "and the plant does not limit it by tyre friction. On a wet road (W02) about 5 m/s² is what the tyres "
                 "give.")
  late = [(r, probe(r, "closing noticed late")) for r in rows]
  worse = [(r, q) for r, q in late if q["delta"] < -0.05]
  late_flips = [r for r, q in late if (q["rho"] < 0) != (r["rho"] < 0)]
  out.append("- Low visibility, as a closing noticed only at a time to collision of 1.5 s (the ACC still sees the lead: "
             "the plant has no perception): "
             + (f"{len(worse)} rows end closer, by up to {max(-q['delta'] for _, q in worse):.1f} m; " if worse else
                "no row ends closer: the change of acceleration or the siren cues the driver first.")
             + (f"it turns {', '.join(r['id'] for r in late_flips)} into contact." if late_flips else
                "it turns none round." if worse else ""))
  blind = [(r, probe(r, "change of acceleration not noticed")) for r in rows]
  blind_flips = [r for r, q in blind if (q["rho"] < 0) != (r["rho"] < 0)]
  if blind_flips:
    out.append(f"- A driver who does not notice the change of acceleration, and is cued only by the closing at a time "
               f"to collision of 2 s, turns {', '.join(r['id'] for r in blind_flips)} into contact: the 1 m/s² cue "
               "(driver_long_cue, no source; WP-C-08 to replace) is what keeps those rows clear.")
  mute = [(r, probe(r, "panda siren muted")) for r in rows]
  mute_flips = [r for r, q in mute if (q["rho"] < 0) != (r["rho"] < 0)]
  if mute_flips:
    out.append(f"- With the panda siren muted (as before DQ-404) {', '.join(r['id'] for r in mute_flips)} end in "
               "contact: there the siren is the driver's cue.")
  ho = [r for r in rows if r["family"].startswith("handover")]
  if ho:
    timed = [(r, q) for r in ho for q in r["probes"] if q["label"].startswith(("as built", "DQ-407"))]
    sd = [(r, q) for r, q in timed if r["fault"] == "soft_disable"]
    spread = max(max(q["rho"] for rr, q in sd if rr is r) - min(q["rho"] for rr, q in sd if rr is r)
                 for r in {id(r): r for r, _ in sd}.values()) if sd else 0.0
    contact = [r for r in ho if r["rho"] < 0] + [r for r, q in timed if q["rho"] < 0]
    out.append("- Hand-over timing (register DQ-407): "
               + ("no hand-over row ends in contact under any order of alert and slow-down. " if not contact else
                  f"{', '.join(sorted({r['id'] for r in contact}))} end in contact under at least one order. ")
               + f"Re-run as built, as DQ-407 B and as DQ-407 C, each soft-disable row's smallest gap changes by at "
               f"most {spread:.1f} m (probe table): the slow-down is −1.2 m/s² at most, the ACC keeps braking for the "
               "lead until the hand-back, and a following driver answers the brake lights. Within this box the order "
               "of alert and slow-down does not decide the outcome.")
  return out


CATALOGUE_HEAD = "| Row | Family | Fault | Parameters | rho (m) | {} | rho without the fault (m) | Decides | HARA / SOTIF | Scene |"


def catalogue_page(rows: list[dict]) -> str:
  scenes = scenes_by_row()
  findings = SPEC.get("findings", {})
  lat = [r for r in rows if not longitudinal(FAMILIES[r["family"]])]
  lon = [r for r in rows if longitudinal(FAMILIES[r["family"]])]
  new = [r for r in rows if r["rho"] < 0 and r["hara"].get("new")]

  def scene_cell(r):                 # a scene without a rendered dashboard yet is named, not linked
    return ", ".join(f"[{s}](../blender/dashboards/{s}.jpg)" if (SIM / "blender" / "dashboards" / f"{s}.jpg").exists()
                     else f"{s} (not rendered)" for s in scenes.get(r["id"], [])) or "—"

  out = [
    "# Edge-case catalogue: lateral departures and longitudinal contacts",
    "",
    BANNER.replace("The share of departing samples is a property of the uniform box below, not a probability of "
                   "anything on the road.", "A row is the worst case a seeded search found in its box, not a likely "
                   "event: nothing here is an exposure or a probability."),
    "",
    "The worst cases of every search family of [`families.yaml`](../search/families.yaml) (WP-V-04 U-4), each re-run "
    "with its parameters rounded as a scene writes them, without its fault (is it the fault or the road and the "
    "traffic?), and under assumption probes (which stated assumption decides the outcome). Each row is mapped to the "
    "HARA hazardous event (HE-, [WP-C-03](../../02-concept/WP-C-03-hara.md)) or SOTIF hazard (SH-, "
    "[WP-C-05](../../02-concept/WP-C-05-sotif-hazard-identification.md)) it falls under. A departure or contact that "
    "matches no hazardous event is a finding for the HARA: it is listed under [New-hazard findings]"
    "(#new-hazard-findings) and queued in the [decision register](../../01-management/decisions/register.yaml); the "
    "HARA itself is not edited here.",
    "",
    "Lateral families: rho is the margin of the body edge to the lane line (rho < 0: a departure). Longitudinal and "
    "hand-over families: rho is the smallest bumper gap to the lead or the follower (rho < 0: contact).",
    "",
    LIMITS,
    "",
    LIMITS_LONG,
    "",
    "## Top findings",
    "",
    *lateral_findings(lat),
    *longitudinal_findings(lon),
  ]
  for fid in sorted({r["hara"]["new"] for r in new}):
    ids = [r["id"] for r in new if r["hara"]["new"] == fid]
    out.append(f"- {', '.join(ids)} match{'es' if len(ids) == 1 else ''} no HARA hazardous event: "
               f"{findings[fid]['title']} ({fid}, queued as {findings[fid]['dq']}).")
  out += ["", "## Catalogue: lateral", "", CATALOGUE_HEAD.format("Line crossed (s) | Side"),
          "|---|---|---|---|---|---|---|---|---|---|---|"]
  for r in lat:
    fam = FAMILIES[r["family"]]
    out.append(f"| {r['id']} | [{r['family']}]({page_name(fam)}) | {FAULT_TEXT.get(r['fault'], r['fault'])} | "
               f"{params_text(fam, r)} | {f(r['rho'])} | {f(r['t_edge'])} | {r['side']} | {f(r['rho_nofault'])} | "
               f"{decides(r)} | {hz_text(r)} | {scene_cell(r)} |")
  out += ["", "## Catalogue: longitudinal and hand-over", "",
          CATALOGUE_HEAD.format("Contact (s) | Closing at contact (km/h) | With"),
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
  for r in lon:
    fam = FAMILIES[r["family"]]
    out.append(f"| {r['id']} | [{r['family']}]({page_name(fam)}) | {FAULT_TEXT.get(r['fault'], r['fault'])} | "
               f"{params_text(fam, r)} | {f(r['rho'])} | {f(r['t_edge'])} | {f(r['impact_kph'], 1)} | {r['side']} | "
               f"{f(r['rho_nofault'])} | {decides(r)} | {hz_text(r)} | {scene_cell(r)} |")
  out += ["", "How each row maps: " + " ".join(
    f"{r['id']}: {r['hara']['fit']}." for r in rows if r["hara"].get("he")), ""]
  out += ["## New-hazard findings", ""]
  if not new:
    out += ["None: every departing or contact row falls under a HARA hazardous event.", ""]
  for fid in sorted({r["hara"]["new"] for r in new}):
    fd = findings[fid]
    ids = ", ".join(r["id"] for r in new if r["hara"]["new"] == fid)
    out += [f"### {fid}: {fd['title']}", "", " ".join(fd["text"].split()), "",
            f"Rows: {ids}. Queued for the project lead as {fd['dq']} in the decision register.", ""]
  out += ["## Assumption probes", "",
          "Each row re-run with one assumption changed (rho in metres; the row's own rho first). Lateral rows:", ""]
  for group, key in ((lat, "probes_default"), (lon, "probes_longitudinal")):
    if group is lon:
      out += ["", "Longitudinal and hand-over rows:", ""]
    n = len(SPEC[key])
    out += ["| Row | rho | " + " | ".join(q["label"] for q in group[0]["probes"][:n]) + " | Family probe |",
            "|---|---|" + "---|" * (n + 1)]
    for r in group:
      q = r["probes"]
      extra = q[n:]
      out.append(f"| {r['id']} | {f(r['rho'])} | " + " | ".join(f(x["rho"]) for x in q[:n])
                 + " | " + ("; ".join(f"{x['label']}: {f(x['rho'])}" for x in extra) or "—") + " |")
  out += ["", "## Reproducing a row", "",
          "The fields a plant scene of [`blender/scenes.yaml`](../blender/scenes.yaml) needs to reproduce each row "
          "(its `case`, `case_overrides` and `assumptions`); `test_search.py` checks that every scene naming a row "
          "reproduces its rho.", ""]
  for r in rows:
    rp = r["reproduce"]
    out.append(f"- **{r['id']}** `case: {rp['case']}`, `case_overrides: {flow(rp['case_overrides'])}`"
               + (f", `assumptions: {flow(rp['assumptions'])}`" if rp["assumptions"] else ""))
  out += ["", "## Families", ""]
  out += [f"- [{fam['title']}]({page_name(fam)})" for fam in SPEC["families"]]
  out.append("")
  out += [f"<!-- edge-case {r['id']} family={r['family']} rho={r['rho']:.4f} -->" for r in rows]
  return "\n".join(out) + "\n"


DQ_FIGURE = SIM.parent / "01-management" / "decisions" / "figures" / "dq-406.svg"


def dq_figure(rows: list[dict]) -> str:
  """Decision register figure for finding EC-N1: the lane change as planned, as HE-02.5 rates it, and as found."""
  fam = FAMILIES["fault-timing-lane-change"]
  found = [r for r in rows if r["family"] == fam["id"] and r["hara"].get("new") == "EC-N1"]
  traces = []
  for r in found[:2]:
    case, assume = make_case(fam, r["p"])
    res = simulate(case, assume)
    traces.append((r, case, [(t - case.lane_change, e) for t, e in zip(res.t, res.e_y)], res.metrics["events"]))
  case = dataclasses.replace(traces[0][1], fault="none")
  res = simulate(case)
  plan = [(t - case.lane_change, e) for t, e in zip(res.t, res.e_y)]
  lw = case.lane_width
  thr = lane_line(lw)
  W, H, x0, x1, y0, y1 = 640, 340, 80, 616, 34, 232
  t_min, t_max, lo = -0.5, 7.0, -lw / 2 - 0.4
  hi = max(max(e for _, e in tr) for _, _, tr, _ in traces) + 0.5

  def X(t):
    return x0 + (t - t_min) / (t_max - t_min) * (x1 - x0)

  def Y(e):
    return y0 + (hi - e) / (hi - lo) * (y1 - y0)

  def path(tr):
    pts = [(t, e) for t, e in tr if t_min <= t <= t_max][::5]
    return "M" + " L".join(f"{X(t):.1f},{Y(e):.1f}" for t, e in pts)

  out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="dq406t">',
         '<title id="dq406t">Assisted lane change to the left: planned path, the stop between the lanes HE-02.5 rates, '
         'and the plant runs of the rows that cross the target lane\'s far line</title>',
         '<text x="0" y="14" class="s-muted" font-size="12" font-weight="600" letter-spacing=".06em">'
         'FAULT DURING AN ASSISTED LANE CHANGE · SYNTHETIC, NO EVIDENCE CREDIT</text>']
  for k in range(0, int(hi // lw) + 2):          # lane lines of the ego lane, the target lane and those beyond
    e = -lw / 2 + k * lw
    if lo <= e <= hi:
      out.append(f'<line x1="{x0}" y1="{Y(e):.1f}" x2="{x1}" y2="{Y(e):.1f}" stroke="var(--line)" stroke-width="1"/>')
  for k, label in ((0, "ego lane"), (1, "target lane"), (2, "lane beyond")):
    if lo <= k * lw <= hi:
      out.append(f'<text x="{x0 - 6}" y="{Y(k * lw) + 4:.1f}" text-anchor="end" class="s-muted" font-size="10.5">'
                 f'{label}</text>')
  for t in range(0, int(t_max) + 1):
    out.append(f'<text x="{X(t):.1f}" y="{y1 + 16}" text-anchor="middle" class="s-muted" font-size="11">{t} s</text>')
  far = lw + thr
  out.append(f'<line x1="{x0}" y1="{Y(far):.1f}" x2="{x1}" y2="{Y(far):.1f}" stroke="var(--bad)" stroke-width="1.2" '
             'stroke-dasharray="5 4"/>')
  out.append(f'<text x="{x1 - 4}" y="{Y(far) - 5:.1f}" text-anchor="end" class="s-bad" font-size="11">body on the '
             "target lane's far line</text>")
  out.append(f'<path d="{path(plan)}" fill="none" stroke="var(--muted)" stroke-width="2" stroke-dasharray="2 3"/>')
  mid = lw / 2
  t0 = found[0]["p"]["phase"] * found[0]["p"]["lc_s"]
  out.append(f'<line x1="{X(t0):.1f}" y1="{Y(mid):.1f}" x2="{x1}" y2="{Y(mid):.1f}" stroke="var(--accent)" '
             'stroke-width="2.4"/>')
  cols = ["var(--bad)", "var(--ink)"]
  for (r, _, tr, ev), col in zip(traces, cols):
    out.append(f'<path d="{path(tr)}" fill="none" stroke="{col}" stroke-width="2.4"/>')
  ly = y1 + 38
  out.append(f'<line x1="{x0}" y1="{ly - 4}" x2="{x0 + 24}" y2="{ly - 4}" stroke="var(--accent)" stroke-width="3"/>')
  out.append(f'<text x="{x0 + 32}" y="{ly}" class="s-ink" font-size="12.5">HE-02.5 as rated: the car stops between '
             'the lanes and straddles them</text>')
  for i, ((r, case, tr, ev), col) in enumerate(zip(traces, cols)):
    yy = ly + 20 * (i + 1)
    what = {"frozen": "Frozen command (F-03)", "soc_stall": "SoC stall, no siren (F-04b)",
            "eps_fault": "EPS fault (F-07)", "hardover": "Hard-over (F-01b)"}[case.fault]
    out.append(f'<line x1="{x0}" y1="{yy - 4}" x2="{x0 + 24}" y2="{yy - 4}" stroke="{col}" stroke-width="3"/>')
    out.append(f'<text x="{x0 + 32}" y="{yy}" class="s-ink" font-size="12.5">{what} at {r["p"]["phase"]:.0%} of the '
               f'change ({r["id"]}): runs past the target lane, rho {r["rho"]:.2f} m</text>')
  out.append(f'<text x="{x0 + 32}" y="{ly + 62}" class="s-muted" font-size="11">Dotted: the planned change, no '
             'fault. Plant runs with the real panda code; time from the start of the change.</text>')
  out.append("</svg>")
  return "\n".join(out) + "\n"


def lane_line(lw: float) -> float:
  return (lw - WIDTH) / 2


def build() -> dict[Path, str]:
  files, (mc, ce) = build_legacy()
  rows = catalogue_rows(LEGACY, mc, ce, 1)
  for fam in SPEC["families"][1:]:
    mc, ce = search(fam)
    files[RESULTS / page_name(fam)] = generic_page(fam, mc, ce)
    rows += catalogue_rows(fam, mc, ce, len(rows) + 1)
  files[CATALOGUE] = catalogue_page(rows)
  files[DQ_FIGURE] = dq_figure(rows)
  return files


def main(argv) -> int:
  global _POOL
  jobs = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else (os.cpu_count() or 1)
  if jobs > 1:
    _POOL = mp.get_context("fork").Pool(jobs)
  try:
    files = build()
  finally:
    if _POOL is not None:
      _POOL.close()
      _POOL = None
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
