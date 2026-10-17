#!/usr/bin/env python3
"""Reachability bound: the drift the linearised L1 plant can reach under any LKA command the panda passes, computed
exactly, and checked against the sampled fault runs.

    python3 assurance/sim/reach/reach_compare.py            # write results/reach.md and results/reach-y.svg
    python3 assurance/sim/reach/reach_compare.py --check    # fail if a sample lies outside, or the results are stale

With one bounded input and a linear model the reachable set's support function in the direction of y or psi is a
closed sum or integral of |impulse response| x input envelope (README §3.6):
  dt   the sum over plant steps of |c exp(A h)^m Phi1 B| e_j: exact for commands held per plant step, the plant's own
       input structure. This is the bound.
  ct   the integral of |c exp(A s) B| env(t - s) over [0, t], by trapezoid quadrature on a 0.1 ms grid (no quadrature
       error bound): any command within the envelope, also between plant steps.
  amp  the same with |u| <= u_max from t = 0 (no panda ramp), for comparison.
Checks, reported in results/reach.md:
  linear      every sampled run of the linear model (driven by the commands the EPS applied, held per 10 ms grid step)
              lies inside dt, up to TOL for the 9-digit rounding of samples.json;
  nonlinear   every sampled run of the nonlinear L1 plant lies inside dt widened by the largest linearisation error
              measured on the same runs. The bound covers the linear model only; this widening is measured on these
              samples, not proven, so this check says the linearisation is adequate here, nothing more.
The Julia pilot that first computed dt (JuliaReach, #155) gave the same values to rounding and was retired (§3.6).
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
SAMPLES = HERE / "samples.json"
MODEL = HERE / "model.json"
RESULTS = HERE / "results"
TABLE = RESULTS / "reach.md"
FIGURE = RESULTS / "reach-y.svg"
TOL = 1e-7                      # absolute, m or rad: rounding of samples.json to 9 significant digits
TIMES = (0.1, 0.2, 0.5, 1.0, 1.5, 2.0, 2.5)
QUAD_S = 1e-4                   # quadrature step of the ct reference
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


def containment(ex: dict, s: dict) -> dict:
  """Worst excess of the sampled envelopes over the dt bound (<= 0 means inside), per check and output."""
  wide = {"y": s["max_linearisation_error_y_m"], "psi": s["max_linearisation_error_psi_rad"]}
  out = {}
  for name, pre, widen in (("linear", "lin_", False), ("nonlinear", "", True)):
    for v in OUT:
      w = wide[v] if widen else 0.0
      b = ex["dt"][v]
      hi = max(x - h - w for x, h in zip(s[f"{pre}{v}_max"], b, strict=True))
      lo = max(-h - w - x for x, h in zip(s[f"{pre}{v}_min"], b, strict=True))
      out[(name, v)] = max(hi, lo)
  return out


def idx(s: dict, t: float) -> int:
  return round(t / (s["t"][1] - s["t"][0]))


def g(x: float) -> str:
  return "∞" if math.isinf(x) else f"{x:.4g}"


def table(s: dict, m: dict, ex: dict) -> str:
  c = containment(ex, s)
  tk = s["takeover_s"]
  times = sorted(set(TIMES) | {tk, m["horizon_s"]})
  verdict = {k: ("inside" if x <= TOL else f"OUTSIDE by {x:.3g}") for k, x in c.items()}
  lines = [
    "# Reachability bound against sampled fault runs",
    "",
    "Synthetic data (DSR-12), no evidence credit (WP-V-02 §5.3). Generated by "
    "[`reach_compare.py`](../reach_compare.py) from [`model.json`](../model.json) and "
    f"[`samples.json`](../samples.json) ({s['runs']} runs, seed {s['seed']}). Case: straight road, "
    f"{m['speed_kph']:g} km/h, any LKA command the panda passes from t = 0; the driver's correction in the hard-over "
    f"run (drift cue plus reaction time, plant model) is at {tk:g} s.",
    "",
    "## Containment (exact bound for commands held per plant step)",
    "",
    "| Check | y | ψ |",
    "|---|---|---|",
    f"| Linear model runs inside the bound (tolerance {TOL:g}) | {verdict[('linear', 'y')]} | {verdict[('linear', 'psi')]} |",
    f"| Nonlinear plant runs inside the bound widened by the measured linearisation error "
    f"({s['max_linearisation_error_y_m']:.3g} m, {s['max_linearisation_error_psi_rad']:.3g} rad) "
    f"| {verdict[('nonlinear', 'y')]} | {verdict[('nonlinear', 'psi')]} |",
    "",
    "The bound covers the linear model. The widening is measured on these runs, not proven.",
    "",
  ]
  for v, unit, name in (("y", "m", "Lateral offset |y|"), ("psi", "rad", "Heading |ψ|")):
    head = ["t (s)", "Sampled, plant", "Sampled, linear", "Bound (held per step)", "Sampled linear / bound",
            "Any input in envelope", "No panda ramp"]
    lines += [f"## {name} ({unit}), from fault onset", "", "| " + " | ".join(head) + " |",
              "|" + "---|" * len(head)]
    for t in times:
      i = idx(s, t)
      nl = max(s[f"{v}_max"][i], -s[f"{v}_min"][i])
      li = max(s[f"lin_{v}_max"][i], -s[f"lin_{v}_min"][i])
      ed, ec, ea = ex["dt"][v][i], ex["ct"][v][i], ex["amp"][v][i]
      tag = " (takeover)" if t == tk else ""
      row = [f"{t:g}{tag}", g(nl), g(li), g(ed), g(li / ed) if ed > 0 else "—", g(ec), g(ea)]
      lines.append("| " + " | ".join(row) + " |")
    lines.append("")
  lines += [
    "Bound: commands held per plant step (5 ms), exact (support function summed per step). Any input in envelope: "
    "commands may also change between plant steps (integral by quadrature). No panda ramp: |u| ≤ STEER_MAX from "
    "t = 0. Sampled columns: the largest value over all runs.",
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

W, H = 1000, 660


def _t(x, y, s, cls="t", anchor=None):
  a = f' text-anchor="{anchor}"' if anchor else ""
  return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}"{a}>{escape(s)}</text>'


def figure(s: dict, m: dict, ex: dict) -> str:
  t = s["t"]
  T = m["horizon_s"]
  tk = s["takeover_s"]
  out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
         'aria-labelledby="t d">',
         '<title id="t">Reachability bound: lateral offset and heading against sampled fault runs</title>',
         '<desc id="d">Synthetic data (DSR-12), no evidence credit. Upper bound of the reachable lateral offset and '
         'heading under any LKA command the panda passes, from fault onset: the exact bound for commands held per '
         'plant step, for any command within the panda envelope and without the panda ramp, the largest value over '
         'the sampled runs of the nonlinear plant, and the driver correction time of the hard-over run.</desc>', STYLE,
         f'<rect class="bg" width="{W}" height="{H}"/>',
         _t(40, 36, f"Reachability bound vs sampled LKA torque faults · {m['speed_kph']:g} km/h, straight road", "th"),
         _t(40, 56, f"exact support function of the linearised L1 plant; {s['runs']} sampled runs, real panda code, "
                    "nonlinear L1 plant", "t2"),
         _t(W - 40, 36, "Synthetic data (DSR-12) · no evidence credit", "t2", "end"),
         _t(W - 40, 56, "generated by assurance/sim/reach/reach_compare.py", "t2", "end")]
  panels = (("y", "A · Lateral offset |y| (m)", 1.0, 90, 330), ("psi", "B · Heading |ψ| (deg)", 180 / math.pi, 390, 600))
  x0, x1 = 80, W - 40

  def X(tt):
    return x0 + tt / T * (x1 - x0)

  for v, title, k, y0, y1 in panels:
    hi = [a * k for a in ex["dt"][v]]
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
  for i, (cls, label) in enumerate((("bound", "bound (held per 5 ms step)"), ("exact", "any input in envelope"),
                                    ("amp", "without the panda ramp"), ("samp", "largest sampled run, plant"))):
    lx = x0 + i * 225
    out.append(f'<line x1="{lx}" y1="{ly - 4}" x2="{lx + 28}" y2="{ly - 4}" class="{cls}"/>')
    out.append(_t(lx + 34, ly, label, "t2"))
  out.append("</svg>")
  return "\n".join(out) + "\n"


def main(argv) -> int:
  s, m = load(SAMPLES), load(MODEL)
  ex = exact(m, len(s["t"]))
  c = containment(ex, s)
  for (name, v), x in sorted(c.items()):
    print(f"reach: {name:9s} {v:3s} worst excess {x:.3g} ({'inside' if x <= TOL else 'OUTSIDE'})")
  outside = [k for k, x in c.items() if x > TOL]
  files = {TABLE: table(s, m, ex), FIGURE: figure(s, m, ex)}
  if "--check" in argv:
    stale = [p.name for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    if stale:
      print(f"stale: {', '.join(stale)}; run: python3 assurance/sim/reach/reach_compare.py", file=sys.stderr)
    if outside:
      print(f"outside the bound: {outside}", file=sys.stderr)
    if stale or outside:
      return 1
    print("reach: current, every sample inside")
    return 0
  RESULTS.mkdir(exist_ok=True)
  for p, text in files.items():
    p.write_text(text, encoding="utf-8")
  print(f"reach: wrote {TABLE.relative_to(HERE)}, {FIGURE.relative_to(HERE)}")
  return 1 if outside else 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
