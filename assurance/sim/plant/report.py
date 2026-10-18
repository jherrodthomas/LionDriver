#!/usr/bin/env python3
"""Run every case of the fault-injection plant model and write its results table and figures.

    python3 assurance/sim/plant/report.py            # run the cases, write results/plant-results.md and the SVGs
    python3 assurance/sim/plant/report.py --check    # fail if the committed table or a figure differs from a fresh run

Synthetic data (DSR-12): simulation of models around the real panda safety code. No evidence credit until the
WP-V-02 §5.3 fidelity case is approved for the scenario family (DQ-139). Deterministic: no random numbers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import corolla  # noqa: E402
import kinematics as kin  # noqa: E402
from cases import all_cases  # noqa: E402
from panda_loop import Panda  # noqa: E402
from roads import lane_line_threshold  # noqa: E402
from simulate import ASSUMPTIONS, Result, make_road, simulate  # noqa: E402

SIM = HERE.parent
TABLE = SIM / "results" / "plant-results.md"
FIGDIR = SIM / "figures"
SILHOUETTE = FIGDIR / "corolla-e210-silhouette.json"   # top-down outline of the reference car (vehicle-3d-model.md §6)


def ego_outline() -> list[tuple[float, float]] | None:
  """The reference car's top-down outline with mirrors as (along, across) in metres, front at along = 0, rear
  negative, left positive. From the silhouette the vehicle-3d-model.md tools extract from the purchased mesh
  (rendered output; the mesh itself stays out of the repository). None when the file is absent."""
  if not SILHOUETTE.is_file():
    print(f"warning: {SILHOUETTE.relative_to(SIM)} missing; drawing the ego as a rectangle", file=sys.stderr)
    return None
  o = json.loads(SILHOUETTE.read_text(encoding="utf-8"))["top_outline_with_mirrors"]
  front = -min(y for y, _ in o["left"])            # the file's -y is the front
  left = [(-y - front, x) for y, x in o["left"]]
  right = [(-y - front, x) for y, x in o["right"]]
  return left + list(reversed(right))


# ------------------------------------------------------------------------------------------------ formatting
def f2(v, unit=""):
  return "—" if v is None else f"{v + 0.0:.2f}{unit}".replace("-0.00", "0.00")


def ev(m: dict, *names: str):
  for n in names:
    for k, v in m["events"].items():
      if k.startswith(n):
        return v
  return None


def panda_reaction(m: dict) -> str:
  parts = []
  for name, label in (("relay malfunction", "relay malfunction"), ("authority revoked", "revoked"),
                      ("panda refuses", "frames refused"), ("MCU hung", "no frames (hang)"), ("IWDG reset", "IWDG reset")):
    v = ev(m, name)
    if v is not None:
      parts.append(f"{label} {v:.3f}")
  return "; ".join(parts) if parts else "none"


def estimate(case) -> str:
  d = corolla.as_dict()
  thr, thr_n = lane_line_threshold(3.7, d["width"]), lane_line_threshold(3.0, d["width"])
  if case.longitudinal:
    if case.fault == "accel_max":
      return f"§3.3: {kin.gap_loss(2.0, 1.0):.2f} m gap loss in 1 s at 2.0 m/s²"
    if case.fault == "decel_min":
      return "§3.4: collision if follower t_r ≥ time gap with equal deceleration"
    return "—"
  if case.fault == "hardover":
    a = d["lat_accel_factor"]
    return f"§3.1 1 s ramp at {a:.2f} m/s²: {kin.t_ramp(thr_n, a):.2f} / {kin.t_ramp(thr, a):.2f} s"
  if (case.road.startswith("curve") or case.road.startswith("KS-")) and case.fault not in ("none", "not_engaged"):
    # the lateral acceleration the lost assist was holding: v^2 times the steady curvature of the lane
    v = case.speed_kph / 3.6
    road = make_road(case.road, v)
    a = round(v * v * road.curvature(road.curve_start + 2000.0), 2)
    return f"§3.1 step at {a:g} m/s²: {kin.t_step(thr_n, a):.2f} / {kin.t_step(thr, a):.2f} s"
  return "—"


def lateral_rows(results: list[Result]) -> list[str]:
  rows = ["| Case | Fault (FMEA; WP-V-05) | Road | EPS | Panda reaction (s) | EPS torque < 5 % (s) | Siren (s) | "
          "Driver cue → correction (s) | Deviation at 0.5 s (m) | To lane line, 3.0 / 3.7 m lane (s) | "
          "WP-S-04 estimate, 3.0 / 3.7 m lane | Max deviation (m) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
  for r in results:
    c, m = r.case, r.metrics
    if c.longitudinal or c.pcs:
      continue
    cue = next((k for k in m["events"] if k.startswith("driver cue")), None)
    drv = "none" if cue is None else f"{cue[12:-1]} {m['events'][cue]:.2f} → {ev(m, 'driver correction'):.2f}"
    rows.append(
      f"| {c.id} | {c.title} ({c.fmea}; {c.wpv05 or '—'}) | {c.road} | {c.eps} | {panda_reaction(m)} | "
      f"{f2(ev(m, 'EPS LKA torque'))} | {f2(ev(m, 'panda siren'))} | {drv} | {f2(m.get('dev_at_ftti'))} | "
      f"{f2(m['t_narrow'])} / {f2(m['t_line'])} | {estimate(c)} | {f2(m['max_dev'])} |")
  return rows


def longitudinal_rows(results: list[Result]) -> list[str]:
  rows = ["| Case | Fault (FMEA; WP-V-05) | Panda reaction (s) | Driver cue → correction (s) | Gap to lead: onset / min / "
          "lost in 1 s (m) | Gap to follower: onset / min (m) | WP-S-04 estimate |",
          "|---|---|---|---|---|---|---|"]
  for r in results:
    c, m = r.case, r.metrics
    if not c.longitudinal:
      continue
    cue = next((k for k in m["events"] if k.startswith("driver cue")), None)
    drv = "none" if cue is None else f"{cue[12:-1]} {m['events'][cue]:.2f} → {ev(m, 'driver correction'):.2f}"
    rows.append(f"| {c.id} | {c.title} ({c.fmea}; {c.wpv05}) | {panda_reaction(m)} | {drv} | "
                f"{m['gap0_lead']:.1f} / {m['min_gap_lead']:.1f} / {f2(m['gap_loss_1s'])} | "
                f"{m['gap0_follow']:.1f} / {m['min_gap_follow']:.1f} | {estimate(c)} |")
  return rows


def pcs_rows(results: list[Result]) -> list[str]:
  a_pcs = ASSUMPTIONS["a_pcs"][0]
  rows = ["| Case | Fault (FMEA; WP-V-05) | TSR | Panda reaction (s) | PCS request reaches the car (s) | "
          f"Speed reduction lost at {a_pcs:g} m/s² (km/h) | Against SG-07 FTTI 0.2 s (WP-S-04 §3.6) |",
          "|---|---|---|---|---|---|---|"]
  for r in results:
    c, m = r.case, r.metrics
    if not c.pcs:
      continue
    d = ev(m, "PCS request reaches")
    lost = "never reaches" if d is None else f"{a_pcs * d * 3.6:.1f}"
    verdict = "not reached in the run" if d is None else ("within" if d <= 0.2 else "exceeds")
    rows.append(f"| {c.id} | {c.title} ({c.fmea}; {c.wpv05}) | {c.tsr} | {panda_reaction(m)} | {f2(d)} | {lost} | {verdict} |")
  return rows


def submodule_commit(name: str) -> str:
  """The commit of the panda or opendbc code the run compiled (the checked-out submodule)."""
  import subprocess
  out = subprocess.run(["git", "-C", str(corolla.ROOT / name), "rev-parse", "--short=7", "HEAD"], capture_output=True,
                       text=True, check=True)
  return out.stdout.strip()


def labels() -> list[str]:
  """WP-V-02 §5.3.5 labels for synthetic data (DSR-12)."""
  import importlib.metadata as md
  return [
    "| Label (WP-V-02 §5.3.5) | Value |",
    "|---|---|",
    "| data_kind | synthetic |",
    f"| simulator | LionDriver fault-injection plant model, fidelity L1 (`assurance/sim/plant`): CommonRoad vehicle models "
    f"{md.version('commonroad-vehicle-models')}; panda safety code compiled from panda `{submodule_commit('panda')}` and "
    f"opendbc `{submodule_commit('opendbc_repo')}` (reference build) |",
    "| asset archive hash | none (nothing is rendered) |",
    "| scenario ID and family | F-07-KS01 and N-4 run on the road of scenario KS-01 (family SF-1); L-01…L-04 take the "
    "KS-08 time gap (SF-2). The other cases use generic highway roads, not WP-V-03 scenarios |",
    "| fidelity-case status | none |",
    "| credit | none |",
    "| camera frame rate | not applicable (no camera) |",
  ]


def table(results: list[Result], iwdg: float) -> str:
  d = corolla.as_dict()
  thr, thr_n = lane_line_threshold(3.7, d["width"]), lane_line_threshold(3.0, d["width"])
  out = [
    "# Fault-injection plant model: results",
    "",
    "> **Synthetic data (DSR-12).** Generated by [`plant/report.py`](../plant/report.py); do not edit by hand. "
    "Models around the real panda safety code; nothing here is measured. **No evidence credit**: simulation earns "
    "credit only once the WP-V-02 §5.3 fidelity case is approved for the scenario family (DQ-139). Results "
    "rank risks and guide tests only, until the model is validated against Corolla logs. Timing results "
    "go to the safety-concept session for WP-S-04; they are not entered in the MSR rating tables, which allow "
    "`measured | code_derived | unknown` only. Method and limits: [README](../README.md).",
    "",
    "Times are seconds from fault onset. Deviation is the lateral offset from the offset at fault onset; negative is "
    "to the right (outside of the left curve). Lane-line thresholds: body edge on the line, (lane width − "
    f"{d['width']:.3f} m) / 2 = **{thr_n:.2f} m** in a 3.0 m lane (narrowest ODD-H lane) and **{thr:.2f} m** in a "
    "3.7 m lane. Speed 110 km/h (the ODD-H bound, DQ-260) unless the case names another; rows ending -OS repeat the "
    "first case of each fault family at 120 km/h, outside the ODD, as margin cases. Curve: a clothoid over 100 m into a left arc with R = v²/1.5 m/s² "
    "(inside the ODD); N-3 uses R_ODD = v²/2.5 m/s²; a road named KS-xx is read from that scenario's OpenDRIVE file "
    "(ego lane −2, [`scenarios/xodr`](../scenarios/xodr/)). Panda: reference build (`LIONDRIVER_REFERENCE`, safety "
    f"parameter 73); IWDG nominal timeout from the values the firmware writes: {iwdg * 1000:.0f} ms. For safety "
    "parameter 73 the release build and this build (`ALLOW_DEBUG`) differ only in the SecOC flag, which the reference "
    "car does not set.",
    "",
    *labels(),
    "",
    "## Lateral cases (SG-01, SG-02, SG-07)",
    "",
    *lateral_rows(results),
    "",
    "## Longitudinal cases (SG-03, SG-04)",
    "",
    "Straight road, 110 km/h (rows ending -OS: 120 km/h); lead at a 1.5 s gap (KS-08) at constant speed; follower at a 1.0 s gap that brakes at "
    "−3.5 m/s² after the follower's reaction time, until it is no faster than the ego (WP-S-04 §3.4).",
    "",
    *longitudinal_rows(results),
    "",
    "## Stock PCS path (SG-07)",
    "",
    "The stock camera sends a PCS braking request at the fault onset. It reaches the car directly when the harness "
    "switches pass it through, or through the panda when the panda's forwarding hook allows it (real code, "
    "`safety_fwd_hook`). Cases P-01…P-03 come from the safety-concept session's handover (branch "
    "`claude/fault-sim-plant`, 3b6936b). The lost speed reduction is a_PCS × delay, as in WP-S-04 §3.6.",
    "",
    *pcs_rows(results),
    "",
    "## Event log per case",
    "",
    "| Case | Events (s from fault onset) |",
    "|---|---|",
  ]
  for r in results:
    evs = "; ".join(f"{k} {v:.3f}" for k, v in r.metrics["events"].items())
    out.append(f"| {r.case.id} | {escape(evs)} |")
  out += ["", "## Model inputs", "", "| Parameter | Value | Unit | Status | Source |", "|---|---|---|---|---|"]
  for p in corolla.corolla_params():
    out.append(f"| {p.name} | {p.value:.5g} | {p.unit} | {p.status} | {p.source} |")
  out += ["", "| Assumption | Value | Meaning |", "|---|---|---|"]
  for k, (v, text) in ASSUMPTIONS.items():
    out.append(f"| {k} | {v:g} | {text} |")
  return "\n".join(out) + "\n"


# ------------------------------------------------------------------------------------------------ figures
STYLE = """<style>
svg { --bg:#ffffff; --ink:#0b0b0b; --ink2:#52514e; --ink3:#8a8984; --grid:#e3e2de; --lane:#3d3c39; --band:#fbe3d6;
      --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#c98500; --s5:#6250d6; --s8:#e34948; }
@media (prefers-color-scheme: dark) {
  svg { --bg:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --ink3:#8d8c85; --grid:#33322f; --lane:#c3c2b7; --band:#4a2a1c;
        --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#eda100; --s5:#9085e9; --s8:#e66767; }
}
.bg { fill:var(--bg); } .t { font:12px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.t2 { font:11px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink2); }
.th { font:600 15px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.tb { font:600 12.5px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.grid { stroke:var(--grid); stroke-width:1; } .axis { stroke:var(--ink3); stroke-width:1; }
.lane { stroke:var(--lane); stroke-width:1.5; } .laned { stroke:var(--lane); stroke-width:1.2; stroke-dasharray:8 6; }
.thr { stroke:var(--s8); stroke-width:1.3; stroke-dasharray:6 4; } .thrn { stroke:var(--s4); stroke-width:1.3; stroke-dasharray:2 3; }
.band { fill:var(--band); } .path { fill:none; stroke:var(--s1); stroke-width:2.2; }
.car { fill:none; stroke:var(--ink2); stroke-width:1.2; } .fault { stroke:var(--s2); stroke-width:1.5; }
.m1 { fill:var(--s2); } .m2 { fill:var(--s5); } .m3 { fill:var(--s3); } .m4 { fill:var(--s4); } .m5 { fill:var(--s1); } .m6 { fill:var(--s8); }
</style>"""

W, H = 1100, 800


def _t(x, y, s, cls="t", anchor=None, extra=""):
  a = f' text-anchor="{anchor}"' if anchor else ""
  return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}"{a}{extra}>{escape(s)}</text>'


TIMELINE = [  # (row label, event prefixes, marker class)
  ("Panda refusal / revocation", ("panda refuses", "authority revoked", "relay malfunction"), "m1"),
  ("MCU hang, IWDG reset", ("MCU hung", "IWDG reset"), "m2"),
  ("EPS LKA torque < 5 %", ("EPS LKA torque",), "m3"),
  ("Panda siren", ("panda siren",), "m4"),
  ("Driver cue", ("driver cue",), "m5"),
  ("Driver correction", ("driver correction",), "m6"),
]


def figure(r: Result, iwdg: float) -> str:
  c, m = r.case, r.metrics
  thr, thr_n = m["lane_threshold"], m["narrow_threshold"]
  t0 = r.t0
  T0, T1 = -0.5, 4.0
  out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
         f'aria-labelledby="t d">',
         f'<title id="t">Plant model case {c.id}: {escape(c.title)}</title>',
         f'<desc id="d">Synthetic data (DSR-12), no evidence credit. Top-down lane view with the ego path, lateral '
         f'deviation against time with the 0.5 s SG-01 FTTI band and the lane-line thresholds {thr_n:.2f} m and '
         f'{thr:.2f} m, and the event timeline from fault onset.</desc>', STYLE,
         f'<rect class="bg" width="{W}" height="{H}"/>',
         _t(40, 36, f"{c.id} · {c.title}", "th"),
         _t(40, 56, f"{c.road} road, {c.speed_kph:g} km/h, EPS-{c.eps} assumption, driver t_r = {ASSUMPTIONS['driver_t_r_s'][0]:g} s. "
                    f"FMEA {c.fmea}; WP-V-05 {c.wpv05 or '—'}.", "t2"),
         _t(W - 40, 36, "Synthetic data (DSR-12) · no evidence credit", "t2", "end"),
         _t(W - 40, 56, "generated by assurance/sim/plant/report.py", "t2", "end")]

  # ---------------- panel A: top-down lane view in road coordinates (s along, offset across; road straightened)
  ax0, ax1, ay0, ay1 = 70, W - 40, 90, 250
  s_lo = next(s for t, s in zip(r.t, r.s) if t >= t0 + T0)
  s_hi = next((s for t, s in zip(r.t, r.s) if t >= t0 + T1), r.s[-1])
  ymax = 2.0 * 1.85 + 0.4
  lim = max(ymax, max(abs(e) for t, e in zip(r.t, r.e_y) if t0 + T0 <= t <= t0 + T1) + 0.3)

  def PX(s):
    return ax0 + (s - s_lo) / (s_hi - s_lo) * (ax1 - ax0)

  def PY(e):
    return (ay0 + ay1) / 2 - e / lim * (ay1 - ay0) / 2

  out.append(_t(ax0, ay0 - 10, "A · Top-down lane view (road straightened, lateral scale exaggerated)", "tb"))
  for e, cls in ((1.85, "lane"), (-1.85, "laned"), (-1.85 - 3.7, "lane")):
    if abs(e) <= lim:
      out.append(f'<line x1="{ax0}" y1="{PY(e):.1f}" x2="{ax1}" y2="{PY(e):.1f}" class="{cls}"/>')
  out.append(f'<line x1="{ax0}" y1="{PY(-thr):.1f}" x2="{ax1}" y2="{PY(-thr):.1f}" class="thr"/>')
  out.append(_t(ax1 - 4, PY(1.85) - 5, "ego lane, 3.7 m", "t2", "end"))
  out.append(_t(ax1 - 4, PY(-1.85) + 14, "adjacent lane (right)", "t2", "end"))
  out.append(_t(ax1 - 4, PY(-thr) - 5, f"car centre with the body edge on the lane line ({thr:.2f} m)", "t2", "end"))
  pts = " ".join(f"{PX(s):.1f},{PY(e):.1f}" for t, s, e in zip(r.t, r.s, r.e_y) if t0 + T0 <= t <= t0 + T1)
  out.append(f'<polyline class="path" points="{pts}"/>')
  sf = next(s for t, s in zip(r.t, r.s) if t >= t0)
  out.append(f'<line x1="{PX(sf):.1f}" y1="{ay0}" x2="{PX(sf):.1f}" y2="{ay1}" class="fault"/>')
  out.append(_t(PX(sf) + 4, ay1 - 4, "fault onset", "t2"))
  outline = ego_outline()
  if outline:
    # the car at fault onset, front at the onset station; the same anisotropic scales as the lane view
    pts = " ".join(f"{PX(sf + along):.1f},{PY(r.e0 + across):.1f}" for along, across in outline)
    out.append(f'<polygon class="car" points="{pts}"/>')
    out.append(_t(ax1 - 4, ay0 - 10, "ego outline from the purchased mesh (18-inch wheels: sport trim)", "t2", "end"))
  else:
    carw = 1.781 / lim * (ay1 - ay0) / 2
    carl = 4.6 / (s_hi - s_lo) * (ax1 - ax0)
    out.append(f'<rect class="car" x="{PX(sf) - carl:.1f}" y="{PY(r.e0) - carw / 2:.1f}" width="{carl:.1f}" height="{carw:.1f}" rx="2"/>')

  # ---------------- panel B: deviation against time
  bx0, bx1, by0, by1 = 70, W - 40, 300, 520
  dev = [(t - t0, e - r.e0) for t, e in zip(r.t, r.e_y) if t0 + T0 <= t <= t0 + T1]
  dlim = 2.0   # deviations beyond are clipped: the figure is about the first seconds and the thresholds

  def TX(t):
    return bx0 + (t - T0) / (T1 - T0) * (bx1 - bx0)

  def DY(v):
    return by0 + (dlim - v) / (2 * dlim) * (by1 - by0)

  out.append(_t(bx0, by0 - 10, "B · Lateral deviation from the offset at fault onset (m) against time from fault onset (s)", "tb"))
  out.append(f'<rect class="band" x="{TX(0):.1f}" y="{by0}" width="{TX(0.5) - TX(0):.1f}" height="{by1 - by0}"/>')
  out.append(_t(TX(0.25), by0 + 14, "SG-01 FTTI 0.5 s", "t2", "middle"))
  for tt in range(0, 5):
    out.append(f'<line x1="{TX(tt):.1f}" y1="{by0}" x2="{TX(tt):.1f}" y2="{by1}" class="grid"/>')
    out.append(_t(TX(tt), by1 + 16, f"{tt}", "t2", "middle"))
  for v in (-dlim, 0.0, dlim):
    out.append(f'<line x1="{bx0}" y1="{DY(v):.1f}" x2="{bx1}" y2="{DY(v):.1f}" class="grid"/>')
    out.append(_t(bx0 - 6, DY(v) + 4, f"{v:+.1f}", "t2", "end"))
  out.append(f'<line x1="{bx0}" y1="{DY(-thr):.1f}" x2="{bx1}" y2="{DY(-thr):.1f}" class="thr"/>')
  out.append(_t(bx1 - 4, DY(-thr) + 14, f"lane line, 3.7 m lane: −{thr:.2f} m", "t2", "end"))
  out.append(f'<line x1="{bx0}" y1="{DY(-thr_n):.1f}" x2="{bx1}" y2="{DY(-thr_n):.1f}" class="thrn"/>')
  out.append(_t(bx1 - 4, DY(-thr_n) - 5, f"lane line, 3.0 m lane: −{thr_n:.2f} m", "t2", "end"))
  clip = [(t, max(-dlim, min(dlim, v))) for t, v in dev]
  out.append('<polyline class="path" points="' + " ".join(f"{TX(t):.1f},{DY(v):.1f}" for t, v in clip) + '"/>')
  if any(abs(v) > dlim for _, v in dev):
    out.append(_t(bx0 + 6, by1 - 6, f"clipped at ±{dlim:g} m; maximum {m['max_dev']:+.2f} m at {m['t_max_dev']:.2f} s", "t2"))
  for key, level, cls in (("t_narrow", thr_n, "m4"), ("t_line", thr, "m6")):
    tc = m.get(key)
    if tc is not None and tc <= T1:
      out.append(f'<circle cx="{TX(tc):.1f}" cy="{DY(-level):.1f}" r="4.5" class="{cls}"/>')
      out.append(_t(TX(tc) + 7, DY(-level) - 6 if key == "t_narrow" else DY(-level) + 16, f"{tc:.2f} s", "t"))

  # ---------------- panel C: event timeline
  cx0, cx1, cy0 = 70, W - 40, 575
  out.append(_t(cx0, cy0 - 10, "C · Events from fault onset (s)", "tb"))
  row_h = 26
  for i, (label, prefixes, cls) in enumerate(TIMELINE):
    y = cy0 + 14 + i * row_h
    out.append(f'<line x1="{TX(T0):.1f}" y1="{y}" x2="{TX(T1):.1f}" y2="{y}" class="grid"/>')
    out.append(_t(TX(T0) + 2, y - 6, label, "t2"))
    hits = [(v, k) for k, v in m["events"].items() if any(k.startswith(p) for p in prefixes) and T0 <= v <= T1]
    for v, k in hits:
      out.append(f'<circle cx="{TX(v):.1f}" cy="{y}" r="5" class="{cls}"><title>{escape(k)} at {v:.3f} s</title></circle>')
    if hits:
      text = " · ".join(f"{k} {v:.2f} s" for v, k in sorted(hits))
      out.append(_t(TX(max(v for v, _ in hits)) + 9, y + 4, text, "t"))
  yb = cy0 + 14 + len(TIMELINE) * row_h
  out.append(f'<line x1="{TX(0):.1f}" y1="{cy0}" x2="{TX(0):.1f}" y2="{yb - row_h / 2:.1f}" class="fault"/>')
  for tt in range(0, 5):
    out.append(_t(TX(tt), yb, f"{tt}", "t2", "middle"))
  out.append("</svg>")
  return "\n".join(out) + "\n"


# ------------------------------------------------------------------------------------------------ build / check
def build() -> dict[Path, str]:
  results = [simulate(c) for c in all_cases()]
  iwdg = Panda().iwdg_timeout()
  files = {TABLE: table(results, iwdg)}
  for r in results:
    if r.case.figure:
      files[FIGDIR / f"fig-sim-{r.case.id.lower()}.svg"] = figure(r, iwdg)
  return files


def main(argv: list[str]) -> int:
  files = build()
  if "--check" in argv:
    stale = [p for p, c in files.items() if not p.exists() or p.read_text(encoding="utf-8") != c]
    for p in stale:
      print(f"stale: {p.relative_to(SIM)}", file=sys.stderr)
    if stale:
      print("run: python3 assurance/sim/plant/report.py", file=sys.stderr)
      return 1
    print(f"plant model: {len(files)} file(s) current")
    return 0
  for p, c in files.items():
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(c, encoding="utf-8")
  print(f"plant model: wrote {len(files)} file(s)")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
