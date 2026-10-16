#!/usr/bin/env python3
"""Reachability pilot: compare the Julia reach-set bounds with the sampled fault runs and exact references.

    python3 assurance/sim/reach/reach_compare.py --bounds FRESH.json           # commit FRESH as bounds.json, write results
    python3 assurance/sim/reach/reach_compare.py --bounds FRESH.json --check   # fail if anything committed is stale

FRESH.json is what reach.jl writes: the set "dt" (inputs held per plant step, the plant's own input structure) and one
set "ct" per GLGM06 discretisation model (any input within the envelope). Checks, reported in results/reach.md:
  linear      every sampled run of the linear model (the model Julia bounds, driven by the commands the EPS applied,
              held per 10 ms grid step) lies inside dt. This checks the reachability computation; it must hold, up to
              TOL for the 9-digit rounding of the JSON files.
  nonlinear   every sampled run of the nonlinear L1 plant lies inside dt widened by the largest linearisation error
              measured on the same runs. The set bounds the linear model only; this widening is measured on these
              samples, not proven, so this check says the linearisation is adequate here, nothing more.
Exact references, computed here independently of Julia (one bounded input, so the reachable set's support function
in the direction of y or psi is a closed sum or integral of |impulse response| x envelope):
  exact dt    the sum over plant steps of |c exp(A h)^m Phi1 B| e_j: exact for inputs held per step;
  exact ct    the integral of |c exp(A s) B| env(t - s) over [0, t], by trapezoid quadrature on a 0.1 ms grid (no
              quadrature error bound); also with |u| <= u_max throughout (no panda ramp), for comparison.
Synthetic data (DSR-12), no evidence credit (WP-V-02 §5.3).
"""

from __future__ import annotations

import json
import math
import sys
from html import escape
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BOUNDS = HERE / "bounds.json"
SAMPLES = HERE / "samples.json"
MODEL = HERE / "model.json"
RESULTS = HERE / "results"
TABLE = RESULTS / "reach.md"
FIGURE = RESULTS / "reach-y.svg"
TOL = 1e-7                      # absolute, m or rad: JSON rounding to 9 significant digits
REL = 1e-6                      # fresh bounds against the committed ones
TIMES = (0.1, 0.2, 0.5, 1.0, 1.5, 2.0, 2.5)
QUAD_S = 1e-4                   # quadrature step of the exact ct reference
OUT = ("y", "psi")


def load(path: Path) -> dict:
  return json.loads(path.read_text(encoding="utf-8"))


def _env(m: dict, tau: np.ndarray) -> np.ndarray:
  return np.minimum(m["u_max"], m["u_step"] * (np.floor(tau / m["frame_s"] + 1e-9) + 1))


def exact(m: dict, n_grid: int) -> dict:
  """Exact bounds of |y| and |psi| of the linear model at each grid time: 'dt' for inputs held per plant step,
  'ct' for any input within the per-frame envelope, 'amp' for any input with |u| <= u_max."""
  sys.path.insert(0, str(HERE))
  from reach_inputs import expm  # noqa: PLC0415

  A, B = np.array(m["A"]), np.array(m["B"])[:, 0]
  n = len(A)
  out = {k: {v: [0.0] for v in OUT} for k in ("dt", "ct", "amp")}

  # dt: X_N = sum_j Phi^(N-1-j) Phi1 B [-e_j, e_j]
  h = m["plant_step_s"]
  M = np.zeros((n + 1, n + 1))
  M[:n, :n], M[:n, n] = A, B
  E = expm(M * h)
  Phi, Phi1B = E[:n, :n], E[:n, n]
  per = round(m["grid_s"] / h)
  N = per * (n_grid - 1)
  G = np.empty((N, 2))
  z = Phi1B.copy()
  for k in range(N):
    G[k] = z[:2]
    z = Phi @ z
  e = _env(m, np.arange(N) * h)
  for i in range(1, n_grid):
    k = i * per
    for j, v in enumerate(OUT):
      out["dt"][v].append(float((np.abs(G[:k, j])[::-1] * e[:k]).sum()))

  # ct and amp: integral over s of |c exp(A s) B| env(t - s)
  per = round(m["grid_s"] / QUAD_S)
  K = per * (n_grid - 1)
  Eq = expm(A * QUAD_S)
  g = np.empty((K + 1, 2))
  z = B.copy()
  for k in range(K + 1):
    g[k] = z[:2]
    z = Eq @ z
  s = np.arange(K + 1) * QUAD_S
  for i in range(1, n_grid):
    kk = i * per
    w = np.full(kk + 1, QUAD_S)
    w[0] = w[-1] = QUAD_S / 2
    env = _env(m, i * m["grid_s"] - s[:kk + 1])
    for j, v in enumerate(OUT):
      a = np.abs(g[:kk + 1, j]) * w
      out["ct"][v].append(float((a * env).sum()))
      out["amp"][v].append(float(a.sum() * m["u_max"]))
  return out


def mag(d: dict, v: str, i: int) -> float:
  return max(d[f"{v}_hi"][i], -d[f"{v}_lo"][i])


def containment(b: dict, s: dict) -> dict:
  """Worst excess of the sampled envelopes over the dt bounds (<= 0 means inside), per check and output."""
  dt = b["dt"]
  wide = {"y": s["max_linearisation_error_y_m"], "psi": s["max_linearisation_error_psi_rad"]}
  out = {}
  for name, pre, widen in (("linear", "lin_", False), ("nonlinear", "", True)):
    for v in OUT:
      w = wide[v] if widen else 0.0
      hi = max(x - h - w for x, h in zip(s[f"{pre}{v}_max"], dt[f"{v}_hi"], strict=True))
      lo = max(lb - w - x for x, lb in zip(s[f"{pre}{v}_min"], dt[f"{v}_lo"], strict=True))
      out[(name, v)] = max(hi, lo)
  return out


def idx(s: dict, t: float) -> int:
  return round(t / (s["t"][1] - s["t"][0]))


def g(x: float) -> str:
  return "∞" if math.isinf(x) else f"{x:.4g}"


def table(b: dict, s: dict, m: dict, ex: dict) -> str:
  c = containment(b, s)
  tk = s["takeover_s"]
  times = sorted(set(TIMES) | {tk, m["horizon_s"]})
  verdict = {k: ("inside" if x <= TOL else f"OUTSIDE by {x:.3g}") for k, x in c.items()}
  models = sorted(b["ct"])
  lines = [
    "# Reachability pilot: reach-set bounds against sampled fault runs",
    "",
    "Synthetic data (DSR-12), no evidence credit (WP-V-02 §5.3). Generated by "
    "[`reach_compare.py`](../reach_compare.py) from [`bounds.json`](../bounds.json) (Julia "
    f"{b['julia']}, [`reach.jl`](../reach.jl)) and [`samples.json`](../samples.json) "
    f"({s['runs']} runs, seed {s['seed']}). Case: straight road, {m['speed_kph']:g} km/h, any LKA command the panda "
    f"passes from t = 0; the driver's correction in the hard-over run (drift cue plus reaction time, plant model) is "
    f"at {tk:g} s.",
    "",
    "## Containment (Julia dt set)",
    "",
    "| Check | y | ψ |",
    "|---|---|---|",
    f"| Linear model runs inside the set (tolerance {TOL:g}) | {verdict[('linear', 'y')]} | {verdict[('linear', 'psi')]} |",
    f"| Nonlinear plant runs inside the set widened by the measured linearisation error "
    f"({s['max_linearisation_error_y_m']:.3g} m, {s['max_linearisation_error_psi_rad']:.3g} rad) "
    f"| {verdict[('nonlinear', 'y')]} | {verdict[('nonlinear', 'psi')]} |",
    "",
    "The set bounds the linear model. The widening is measured on these runs, not proven.",
    "",
    "## Continuous-time sets (ReachabilityAnalysis.jl GLGM06)",
    "",
    f"δ = {b['delta_ct']:g} s, envelope segments of {b['segment_s']:g} s, zonotope order {b['order_ct']} between "
    "segments.",
    "",
    "| Discretisation model | Result |",
    "|---|---|",
  ]
  i_tk = idx(s, tk)
  for k in models:
    r = b["ct"][k]
    if "error" in r:
      lines.append(f"| `{k}` | failed: {r['error'].splitlines()[0].replace('|', '/')} |")
    else:
      y = mag(r, "y", i_tk)
      lines.append(f"| `{k}` | y bound at the takeover {g(y)} m, {g(y / ex['ct']['y'][i_tk])}× the exact value |")
  lines.append("")
  ok = [k for k in models if "error" not in b["ct"][k]]
  for v, unit, name in (("y", "m", "Lateral offset |y|"), ("psi", "rad", "Heading |ψ|")):
    head = ["t (s)", "Sampled, plant", "Sampled, linear", "Exact dt", "Julia dt", "Julia dt / exact", "Exact ct",
            *[f"Julia ct `{k}` / exact" for k in ok], "Exact, no panda ramp"]
    lines += [f"## {name} ({unit}), from fault onset", "", "| " + " | ".join(head) + " |",
              "|" + "---|" * len(head)]
    for t in times:
      i = idx(s, t)
      nl = max(s[f"{v}_max"][i], -s[f"{v}_min"][i])
      li = max(s[f"lin_{v}_max"][i], -s[f"lin_{v}_min"][i])
      ed, ec, ea = ex["dt"][v][i], ex["ct"][v][i], ex["amp"][v][i]
      jd = mag(b["dt"], v, i)
      cts = [g(mag(b["ct"][k], v, i) / ec) for k in ok]
      tag = " (takeover)" if t == tk else ""
      row = [f"{t:g}{tag}", g(nl), g(li), g(ed), g(jd), g(jd / ed), g(ec), *cts, g(ea)]
      lines.append("| " + " | ".join(row) + " |")
    lines.append("")
  lines += [
    "Julia dt: the zonotope recursion for commands held per plant step (5 ms), exact up to rounding. Exact dt and "
    "exact ct: computed in Python, independently of Julia (support function: sum per plant step, or integral by "
    "quadrature). Exact, no panda ramp: |u| ≤ STEER_MAX from t = 0. Sampled columns: the largest value over all "
    "runs.",
    "",
  ]
  return "\n".join(lines)


STYLE = """<style>
svg { --bg:#ffffff; --ink:#0b0b0b; --ink2:#52514e; --ink3:#8a8984; --grid:#e3e2de; --band:#d6e6fb;
      --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s5:#6250d6; }
@media (prefers-color-scheme: dark) {
  svg { --bg:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --ink3:#8d8c85; --grid:#33322f; --band:#1d3352;
        --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s5:#9085e9; }
}
.bg { fill:var(--bg); } .t { font:12px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.t2 { font:11px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink2); }
.th { font:600 15px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.tb { font:600 12.5px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.grid { stroke:var(--grid); stroke-width:1; } .axis { stroke:var(--ink3); stroke-width:1; }
.band { fill:var(--band); } .bound { fill:none; stroke:var(--s1); stroke-width:1.8; }
.amp { fill:none; stroke:var(--s5); stroke-width:1.3; stroke-dasharray:6 4; }
.exact { fill:none; stroke:var(--ink); stroke-width:1.2; stroke-dasharray:1 3; }
.samp { fill:none; stroke:var(--s2); stroke-width:2.2; } .take { stroke:var(--s3); stroke-width:1.5; stroke-dasharray:3 3; }
</style>"""

W, H = 1000, 640


def _t(x, y, s, cls="t", anchor=None):
  a = f' text-anchor="{anchor}"' if anchor else ""
  return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}"{a}>{escape(s)}</text>'


def figure(b: dict, s: dict, m: dict, ex: dict) -> str:
  t = s["t"]
  T = m["horizon_s"]
  tk = s["takeover_s"]
  out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
         'aria-labelledby="t d">',
         '<title id="t">Reachability pilot: lateral offset and heading bounds against sampled fault runs</title>',
         '<desc id="d">Synthetic data (DSR-12), no evidence credit. Upper bound of the reachable lateral offset and '
         'heading under any LKA command the panda passes, from fault onset: the Julia set for commands held per plant '
         'step, the exact bound for any command within the panda envelope and without the panda ramp, the largest '
         'value over the sampled runs of the nonlinear plant, and the driver correction time of the hard-over '
         'run.</desc>', STYLE,
         f'<rect class="bg" width="{W}" height="{H}"/>',
         _t(40, 36, f"Reach-set bound vs sampled LKA torque faults · {m['speed_kph']:g} km/h, straight road", "th"),
         _t(40, 56, f"Julia {b['julia']} with LazySets; {s['runs']} sampled runs, real panda code, nonlinear L1 plant",
            "t2"),
         _t(W - 40, 36, "Synthetic data (DSR-12) · no evidence credit", "t2", "end"),
         _t(W - 40, 56, "generated by assurance/sim/reach/reach_compare.py", "t2", "end")]
  panels = (("y", "A · Lateral offset |y| (m)", 1.0, 90, 330), ("psi", "B · Heading |ψ| (deg)", 180 / math.pi, 390, 600))
  x0, x1 = 80, W - 40

  def X(tt):
    return x0 + tt / T * (x1 - x0)

  for v, title, k, y0, y1 in panels:
    hi = [mag(b["dt"], v, i) * k for i in range(len(t))]
    amp = [a * k for a in ex["amp"][v]]
    exa = [a * k for a in ex["ct"][v]]
    smp = [max(a, -c) * k for a, c in zip(s[f"{v}_max"], s[f"{v}_min"], strict=True)]
    top = max(max(hi), max(smp), max(amp)) * 1.08
    step = 10 ** math.floor(math.log10(top / 4))
    step *= 5 if top / step > 20 else 2 if top / step > 8 else 1

    def Y(val, y0=y0, y1=y1, top=top):
      return y1 - min(val, top) / top * (y1 - y0)

    def line(vals, cls, Y=Y):
      pts = " ".join(f"{X(tt):.1f},{Y(a):.1f}" for tt, a in zip(t, vals, strict=True))
      return f'<polyline class="{cls}" points="{pts}"/>'

    out.append(_t(x0, y0 - 12, title, "tb"))
    gv = 0.0
    while gv <= top:
      out.append(f'<line x1="{x0}" y1="{Y(gv):.1f}" x2="{x1}" y2="{Y(gv):.1f}" class="grid"/>')
      out.append(_t(x0 - 6, Y(gv) + 4, f"{gv:g}", "t2", "end"))
      gv = round(gv + step, 9)
    for tt in [i * 0.5 for i in range(int(T / 0.5) + 1)]:
      out.append(_t(X(tt), y1 + 16, f"{tt:g} s", "t2", "middle"))
    out.append(f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" class="axis"/>')
    band = " ".join(f"{X(tt):.1f},{Y(h):.1f}" for tt, h in zip(t, hi, strict=True))
    out.append(f'<polygon class="band" points="{X(0):.1f},{Y(0):.1f} {band} {X(T):.1f},{Y(0):.1f}"/>')
    out.append(line(amp, "amp"))
    out.append(f'<polyline class="bound" points="{band}"/>')
    out.append(line(exa, "exact"))
    out.append(line(smp, "samp"))
    out.append(f'<line x1="{X(tk):.1f}" y1="{y0}" x2="{X(tk):.1f}" y2="{y1}" class="take"/>')
    out.append(_t(X(tk) - 4, y0 + 12, f"driver correction, hard-over ({tk:g} s)", "t2", "end"))
  ly = H - 14
  for i, (cls, label) in enumerate((("bound", "Julia set (held per 5 ms step)"), ("exact", "exact, any input in envelope"),
                                    ("amp", "exact, without the panda ramp"), ("samp", "largest sampled run, plant"))):
    lx = x0 + i * 225
    out.append(f'<line x1="{lx}" y1="{ly - 4}" x2="{lx + 28}" y2="{ly - 4}" class="{cls}"/>')
    out.append(_t(lx + 34, ly, label, "t2"))
  out.append("</svg>")
  return "\n".join(out) + "\n"


def same(a, b) -> bool:
  if isinstance(a, dict):
    return isinstance(b, dict) and a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
  if isinstance(a, list):
    return isinstance(b, list) and len(a) == len(b) and all(same(x, y) for x, y in zip(a, b, strict=True))
  if isinstance(a, float) or isinstance(b, float):
    return abs(a - b) <= REL * max(abs(a), abs(b)) + 1e-12
  return a == b


def comparable(b: dict) -> dict:
  """The bounds without run times (they differ run to run)."""
  c = json.loads(json.dumps(b))
  for r in c.get("ct", {}).values():
    r.pop("seconds", None)
  return c


def main(argv) -> int:
  if "--bounds" not in argv:
    print(__doc__, file=sys.stderr)
    return 2
  fresh_path = Path(argv[argv.index("--bounds") + 1])
  fresh, s, m = load(fresh_path), load(SAMPLES), load(MODEL)
  ex = exact(m, len(s["t"]))
  c = containment(fresh, s)
  for (name, v), x in sorted(c.items()):
    print(f"reach compare: {name:9s} {v:3s} worst excess {x:.3g} ({'inside' if x <= TOL else 'OUTSIDE'})")
  if "--check" in argv:
    stale = []
    if not BOUNDS.exists() or not same(comparable(fresh), comparable(load(BOUNDS))):
      stale.append(BOUNDS.name)
    else:
      b = load(BOUNDS)
      for p, text in ((TABLE, table(b, s, m, ex)), (FIGURE, figure(b, s, m, ex))):
        if not p.exists() or p.read_text(encoding="utf-8") != text:
          stale.append(p.name)
    if stale:
      print(f"stale: {', '.join(stale)}; run: python3 assurance/sim/reach/reach_compare.py --bounds <reach.jl output>",
            file=sys.stderr)
      return 1
    print("reach compare: current")
    return 0
  BOUNDS.write_text(json.dumps(fresh, indent=1, sort_keys=True) + "\n", encoding="utf-8")
  RESULTS.mkdir(exist_ok=True)
  TABLE.write_text(table(fresh, s, m, ex), encoding="utf-8")
  FIGURE.write_text(figure(fresh, s, m, ex), encoding="utf-8")
  print(f"reach compare: wrote {BOUNDS.name}, {TABLE.relative_to(HERE)}, {FIGURE.relative_to(HERE)}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
