#!/usr/bin/env python3
"""Draw a loop diagram and a looping animation for each ASIL C hazardous event the layer-1 plant can run.

The ASIL C events are read from WP-C-03 §5 (and their rating if an assumption fails from §5.12). Four of them have a
plant run behind their scene; for each, this script runs that case of the plant (the real panda safety code in the
loop, `../plant/simulate.py`) and draws two SVGs from the run:

  fig-sim-he-<id>-loop.svg   the §3.1 loop with this run's path: where the fault enters, what each part does with it
                             and when, and who stops it
  fig-sim-he-<id>-anim.svg   a looping top-down animation (SMIL, no script): the car's lateral offset over time on a
                             straightened road, the offset plot with a moving cursor, and the events lighting up

The other ASIL C events have only a kinematic scene (no panda code ran), so they get no loop; the README links their
dashboards. `--check` fails when the set of ASIL C events in WP-C-03 changes, when a run no longer shows the reaction
the diagram's wording assumes, or when a committed SVG differs from a fresh run. Needs the track's packages and the
opendbc_repo and panda submodules (CI: the 'simulation plant model' job).

    python3 fig_sim_he.py            # run the four cases (about 3 s) and write the SVGs
    python3 fig_sim_he.py --check
"""

from __future__ import annotations

import dataclasses
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
REPO = HERE.parents[2]
HARA = REPO / "assurance" / "02-concept" / "WP-C-03-hara.md"
sys.path.insert(0, str(SIM / "plant"))
sys.path.insert(0, str(HERE))

import fig_sim_readme as fs  # noqa: E402  (style and SVG helpers)
from fig_sim_readme import P, R, T, chip, el, fmt, para, wrap, W  # noqa: E402

# ---------------------------------------------------------------- the events

# hazardous event -> the plant run behind its scene (catalog case with the same overrides as its Blender scene)
RUNS = {
  "HE-01.2": ("F-01b", {}, "straight highway"),
  "HE-01.4": ("F-02", {}, "straight highway, not engaged"),
  "HE-02.1": ("F-07", {"road": "curve-odd-bound", "t_fault": None}, "left curve at R_ODD, fault at curve entry"),
  "HE-02.2": ("F-07", {"speed_kph": 80, "road": "rcurve@2.0", "lane_width": 3.5, "t_fault": None},
              "rural right curve (2.0 m/s²) at 80 km/h, outside the ODD, fault at curve entry"),
  "HE-07.1": ("F-04b", {"road": "curve-odd-bound", "t_fault": None}, "left curve at R_ODD, fault at curve entry"),
}
# ASIL C events whose scene is kinematic: no panda code ran, so no loop is drawn
KINEMATIC = ("HE-03.3", "HE-06.1", "HE-07.3")

STEER_MAX = 1500

# What enters where, per run. Each part: (role, text). Roles: fault (the fault enters here), passes (carries the
# hazard on), stops (ends it), warns (reacts but cannot end it), silent (reacts without a warning), idle (not
# involved). Texts are formatted with the run's event times; check_run() asserts that the run shows these reactions.
SPEC = {
  "HE-01.2": {
    "fault": "hard-over: torque ramped 15 per frame to 1500",
    "SoC": ("fault", "commands a hard-over within the envelope"),
    "Host": ("passes", "inside the host torque limits"),
    "Panda": ("passes", "passes every frame: the ramp stays inside the envelope; no siren"),
    "Switch": ("passes", "intercept: the frames reach the car"),
    "EPS": ("passes", "steers with full LKA torque"),
    "Vehicle": ("passes", "{line}"),
    "Driver": ("stops", "cue: 0.2 m drift at {cue:.2f} s; corrects from {corr:.2f} s"),
    "verdict": "Only the driver stops it: correction from {corr:.2f} s.",
  },
  "HE-01.4": {
    "fault": "torque request while not engaged",
    "SoC": ("fault", "not engaged, yet sends a torque request"),
    "Host": ("passes", "packs the frame"),
    "Panda": ("stops", "refuses STEERING_LKA from {refuse:.3f} s: not engaged"),
    "Switch": ("idle", "nothing to pass"),
    "EPS": ("idle", "no LKA torque arrives"),
    "Vehicle": ("idle", "stays in lane: largest offset {maxdev:.2f} m"),
    "Driver": ("idle", "drives manually; nothing to correct"),
    "verdict": "The panda stops it at {refuse:.3f} s; nothing reaches the car.",
  },
  "HE-02.1": {
    "fault": "EPS fault: LKA_STATE 9, assist lost",
    "SoC": ("idle", "keeps commanding; its frames are refused"),
    "Host": ("idle", "packs the frames"),
    "Panda": ("warns", "reads LKA_STATE 9: refuses LKA {refuse:.3f} s, revokes {revoke:.3f} s, siren {siren:.2f} s"),
    "Switch": ("idle", "intercept"),
    "EPS": ("fault", "fault: steering assist lost"),
    "Vehicle": ("passes", "{line}"),
    "Driver": ("stops", "cue: siren at {siren:.2f} s; corrects from {corr:.2f} s"),
    "verdict": "The panda warns at {siren:.2f} s; the driver stops it from {corr:.2f} s.",
  },
  "HE-02.2": {
    "fault": "EPS fault: LKA_STATE 9, assist lost",
    "SoC": ("idle", "keeps commanding; its frames are refused"),
    "Host": ("idle", "packs the frames"),
    "Panda": ("warns", "reads LKA_STATE 9: refuses LKA {refuse:.3f} s, revokes {revoke:.3f} s, siren {siren:.2f} s"),
    "Switch": ("idle", "intercept"),
    "EPS": ("fault", "fault: steering assist lost"),
    "Vehicle": ("idle", "stays in lane: largest offset {maxdev:.2f} m"),
    "Driver": ("stops", "cue: siren at {siren:.2f} s; corrects from {corr:.2f} s"),
    "verdict": "The panda warns at {siren:.2f} s; the driver corrects from {corr:.2f} s and the car stays in its lane.",
  },
  "HE-07.1": {
    "fault": "SoC stall: heartbeat and commands stop",
    "SoC": ("fault", "stalls: heartbeat and commands stop"),
    "Host": ("idle", "sends nothing"),
    "Panda": ("warns", "commands lost: revokes at {revoke:.3f} s, siren {siren:.2f} s (DQ-404 A)"),
    "Switch": ("idle", "intercept"),
    "EPS": ("passes", "no LKA torque: the car stops steering"),
    "Vehicle": ("passes", "{line}"),
    "Driver": ("stops", "cue: siren at {siren:.2f} s; corrects from {corr:.2f} s"),
    "verdict": "The panda warns at {siren:.2f} s; the driver corrects from {corr:.2f} s.",
  },
}
ROLE = {"fault": ("FAULT ENTERS", "f-flt"), "passes": ("PASSES IT ON", "f-bad"), "stops": ("STOPS IT", "f-real"),
        "warns": ("WARNS", "f-real"), "silent": ("NO WARNING", "f-bad"), "idle": ("NOT INVOLVED", "f-model")}


def hara() -> dict[str, dict]:
  """WP-C-03: HE id -> {asil, effect, fallback (ASIL if the credited AoU fails, or None), aou}."""
  md = HARA.read_text(encoding="utf-8")
  out = {}
  for m in re.finditer(r"^\| (HE-\d\d\.\d) \| ([^|]*) \| ([^|]*) \| (S\d) \| (E\d) \| ([^|]*) \| \*\*([A-DQM]+)\*\* \|",
                       md, re.M):
    out[m.group(1)] = {"asil": m.group(7), "effect": m.group(3).strip(), "fallback": None, "aou": ""}
  sec = md.split("### 5.12", 1)[1]
  for m in re.finditer(r"^\| (HE-\d\d\.\d) \| ([^|]*) \| ([A-D]) \| ([A-D]) \|", sec, re.M):
    if m.group(1) in out:
      out[m.group(1)].update(fallback=m.group(4), aou=m.group(2).strip())
  return out


def asil_c() -> list[str]:
  return sorted(k for k, v in hara().items() if v["asil"] == "C")


# ---------------------------------------------------------------- runs


def run(he: str):
  import cases
  import simulate
  cid, ov, _road = RUNS[he]
  base = {c.id: c for c in cases.all_cases()}[cid]
  return simulate.simulate(dataclasses.replace(base, **ov) if ov else base)


def times(r) -> dict:
  m, ev = r.metrics, r.metrics["events"]

  def first(prefix):
    return next((v for k, v in ev.items() if k.startswith(prefix)), None)

  t = {"refuse": first("panda refuses"), "revoke": first("authority revoked"), "siren": first("panda siren"),
       "cue": first("driver cue"), "corr": first("driver correction"), "t_line": m["t_line"],
       "maxdev": abs(m["max_dev"]), "t_maxdev": m["t_max_dev"]}
  if m["t_line"] is None:
    t["line"] = f"stays in lane: largest offset {t['maxdev']:.2f} m"
  else:
    t["line"] = (f"runs out of lane: body on the 3.7 m lane line at {m['t_line']:.2f} s; "
                 f"largest offset {t['maxdev']:.2f} m at {m['t_max_dev']:.2f} s")
  return t


def check_run(he: str, t: dict) -> list[str]:
  """The run must show the reactions the wording of SPEC assumes."""
  roles = {k: v[0] for k, v in SPEC[he].items() if isinstance(v, tuple)}
  errs = []
  blocked = t["refuse"] is not None or t["revoke"] is not None
  want = {"passes": not blocked and t["siren"] is None, "stops": t["refuse"] is not None and t["t_line"] is None,
          "warns": blocked and t["siren"] is not None, "silent": t["revoke"] is not None and t["siren"] is None}
  if not want[roles["Panda"]]:
    errs.append(f"{he}: the panda's reaction in the run ({t}) no longer matches '{roles['Panda']}'")
  driver_stops = roles["Driver"] == "stops"
  if driver_stops != (t["corr"] is not None):
    errs.append(f"{he}: driver correction {t['corr']} does not match the driver's role '{roles['Driver']}'")
  if (roles["Vehicle"] == "idle") != (t["t_line"] is None):
    errs.append(f"{he}: lane-line time {t['t_line']} does not match the vehicle's role '{roles['Vehicle']}'")
  if roles["Driver"] == "stops" and "drift" in SPEC[he]["Driver"][1] and t["siren"] is not None:
    errs.append(f"{he}: the driver's cue is written as the drift, but the run has a siren")
  return errs


def head(he: str, h: dict, sub: str) -> list[str]:
  asil = f"ASIL {h['asil']}" + (f" (D if {h['aou']} fail)" if h["fallback"] == "D" else "")
  return [T(24, 34, f"{he} · {asil}", "h"), *para(24, 58, h["effect"], W - 48, "t2", lh=17)[0],
          T(24, 80, "Synthetic (DSR-12) · no evidence credit", "tbad"), T(24, 99, sub, "t2b"),
          el("line", None, x1=24, y1=110, x2=W - 24, y2=110, class_="hair")]


# ---------------------------------------------------------------- loop diagram


def fig_loop(he: str, h: dict, t: dict) -> str:
  spec = SPEC[he]
  cid, _ov, road = RUNS[he]
  b = head(he, h, f"Plant run {cid}: {road}")
  x0, nw = 96, 448
  xr = x0 + nw
  y = 128
  b += [T(24, y + 4, f"FAULT: {spec['fault'].upper()}", "t2b")]
  y += 18

  def node(y, name, kind, cls, key, h_min=64):
    role, s = spec[key]
    label, ccls = ROLE[role]
    lines = wrap(s.format(**t), nw - 28, "t")
    hh = max(h_min, 52 + 20 * len(lines))
    rc = "plan" if role == "idle" else cls
    out = [R(x0, y, nw, hh, rc), T(x0 + 14, y + 24, name, "tl"), T(x0 + 14, y + 42, kind, "t2b")]
    out += [T(x0 + 14, y + 64 + 20 * i, ln, "t") for i, ln in enumerate(lines)]
    c, _ = chip(xr - 10, y + 10, label, ccls, right=True)
    return out + c, hh

  def down(y1, y2, hot):
    return P(f"M{W / 2},{y1} V{y2}", "arr" if hot else "arrd")

  parts = [("SoC stand-in", "MODEL · not openpilot", "model", "SoC"),
           ("Host frames", "REAL CODE · opendbc toyotacan", "real", "Host"),
           ("Panda safety code", "REAL CODE · reference build", "real", "Panda"),
           ("Harness switch", "MODEL", "model", "Switch"),
           ("EPS", "ASSUMED · release on lost frames", "amb", "EPS"),
           ("Vehicle", "MODEL · single-track Corolla", "model", "Vehicle"),
           ("Driver", "ASSUMED · reacts 1.5 s after the cue", "amb", "Driver")]
  ys = {}
  for i, (name, kind, cls, key) in enumerate(parts):
    e, hh = node(y, name, kind, cls, key)
    ys[key] = (y, hh)
    b += e
    y += hh
    if i < len(parts) - 1:
      nxt = parts[i + 1][3]
      hot = spec[key][0] != "idle" and spec[nxt][0] != "idle"
      b += [down(y, y + 26, hot)]
      y += 30
  # return paths: perception to the SoC, car-bus RX (EPS state) to the panda
  vy = ys["Vehicle"][0] + 30
  b += [P(f"M{x0},{vy} H52 V{ys['SoC'][0] + 30} H{x0 - 2}", "arrd"),
        T(44, (vy + ys["SoC"][0]) / 2, "perfect perception", "t2", "middle", rotate=-90)]
  ey = ys["EPS"][0] + 30
  hot_rx = spec["EPS"][0] == "fault"
  b += [P(f"M{xr},{ey} H588 V{ys['Panda'][0] + 30} H{xr + 2}", "arr" if hot_rx else "arrd"),
        T(600, (ey + ys["Panda"][0]) / 2, "EPS state on the car bus (RX)", "t2", "middle", rotate=90)]
  # verdict
  y += 18
  v = spec["verdict"].format(**t)
  lines = wrap(v, W - 76, "tb")
  b += [R(24, y, W - 48, 22 + 20 * len(lines), "badbox" if spec["Driver"][0] == "stops" else "real")]
  b += [T(38, y + 24 + 20 * i, ln, "tb") for i, ln in enumerate(lines)]
  y += 22 + 20 * len(lines) + 16
  b += fs.legend(y + 6, [("f-flt", "fault enters"), ("f-bad", "passes it on"), ("f-real", "stops or warns"),
                         ("plan", "not involved")])[0]
  return fs.svg(int(y + 28), f"{he} in the layer-1 loop: plant run {cid}",
                f"Synthetic (DSR-12), no evidence credit. {he} (ASIL {h['asil']}), {h['effect']}. The layer-1 loop with "
                f"plant run {cid} ({road}): fault {spec['fault']}. " +
                " ".join(f"{k}: {spec[k][1].format(**t)}." for _n, _k2, _c, k in parts) + f" {v}", b)


# ---------------------------------------------------------------- animation

PX_M = 14.0          # road panel: pixels per metre
HOLD = 1.5           # s held at the end before the loop restarts
STEP = 0.05          # s between keyframes


def fig_anim(he: str, h: dict, t: dict, r) -> str:
  import report
  spec = SPEC[he]
  cid, _ov, road = RUNS[he]
  ts = [ti - r.t0 for ti in r.t]
  es = [e - r.e0 for e in r.e_y]
  v = r.case.speed_kph / 3.6
  t_end = max(3.0, (t["corr"] or 0.0) + 2.0)
  t_end = min(t_end, ts[-1])
  t0 = -1.0
  span = t_end - t0
  dur = span + HOLD

  def at(tt):
    i = min(range(len(ts)), key=lambda k: abs(ts[k] - tt))
    return es[i]

  frames = [round(t0 + STEP * k, 3) for k in range(int(round(span / STEP)) + 1)]
  e_f = [at(f) for f in frames]
  e_min = min(min(e_f), -1.0)
  b = head(he, h, f"Plant run {cid}: {road}")

  # road panel
  lw = 3.7
  top_e, bot_e = lw * 1.5, e_min - 2.5
  ry = 122
  rh = (top_e - bot_e) * PX_M
  yc = ry + top_e * PX_M          # screen y of the lane centre (e = 0)

  def Y(e):
    return yc - e * PX_M

  b += [el("rect", None, x=24, y=fmt(ry), width=W - 48, height=fmt(rh), rx=8, class_="card")]
  lines = []
  k = 0
  while True:
    e_line = lw / 2 - k * lw
    if e_line < bot_e:
      break
    if e_line <= top_e:
      lines.append(e_line)
    k += 1
  dash, gap = 3.0 * PX_M, 9.0 * PX_M
  period = (dash + gap) / (v * PX_M)
  for e_line in lines:
    b += [el("line", None, x1=24, y1=fmt(Y(e_line)), x2=W - 24, y2=fmt(Y(e_line)), class_="laned",
             stroke_dasharray=f"{fmt(dash)} {fmt(gap)}")
          .replace("/>", f'><animate attributeName="stroke-dashoffset" from="0" to="{fmt(dash + gap)}" '
                         f'dur="{period:.3f}s" repeatCount="indefinite"/></line>')]
  b += [T(W - 30, Y(-lw / 2) - 5, "lane line", "t2", "end"), T(36, Y(0) + 5, "ego lane", "t2b")]
  # the car: outer group moves laterally, inner group yaws
  outline = report.ego_outline() or [(0, 0.9), (0, -0.9), (-4.6, -0.9), (-4.6, 0.9)]
  cx = 230
  pts = " ".join(f"{fmt(cx + a * PX_M)},{fmt(-c * PX_M)}" for a, c in outline)
  kt = ";".join(f"{(f - t0) / dur:.4f}" for f in frames) + ";1"
  tr = ";".join(f"0,{fmt(Y(e))}" for e in e_f) + f";0,{fmt(Y(e_f[-1]))}"
  yaw = []
  for i, f in enumerate(frames):
    j = min(i + 1, len(frames) - 1)
    i0 = max(j - 1, 0)
    de = e_f[j] - e_f[i0]
    yaw.append(-math.degrees(math.atan2(de, v * STEP * (j - i0) or 1)))
  rot = ";".join(f"{a:.2f} {cx - 2.3 * PX_M:.1f} 0" for a in yaw) + f";{yaw[-1]:.2f} {cx - 2.3 * PX_M:.1f} 0"
  b += [f'<g><animateTransform attributeName="transform" type="translate" values="{tr}" keyTimes="{kt}" '
        f'dur="{dur:.2f}s" repeatCount="indefinite"/>'
        f'<g><animateTransform attributeName="transform" type="rotate" values="{rot}" keyTimes="{kt}" '
        f'dur="{dur:.2f}s" repeatCount="indefinite"/>'
        f'<polygon points="{pts}" class="egocar"/></g></g>']
  b += [T(36, ry + 20, "road straightened; the car keeps its place, the road moves", "t2")]

  # offset plot
  py = ry + rh + 26
  ph = 150
  px0, px1 = 64, W - 32

  def TX(tt):
    return px0 + (tt - t0) / span * (px1 - px0)

  lo, hi = e_min - 0.5, 1.0

  def DY(e):
    return py + (hi - e) / (hi - lo) * ph

  b += [T(24, py - 8, "LATERAL OFFSET (m) AGAINST TIME (s)", "t2b")]
  b += [el("rect", None, x=fmt(TX(0)), y=fmt(py), width=fmt(TX(0.5) - TX(0)), height=ph, class_="ftti")]
  for e_g in range(int(math.floor(lo)), int(math.ceil(hi)) + 1):
    if lo <= e_g <= hi and e_g % (2 if hi - lo > 6 else 1) == 0:
      b += [el("line", None, x1=px0, y1=fmt(DY(e_g)), x2=px1, y2=fmt(DY(e_g)), class_="hair"),
            T(px0 - 6, DY(e_g) + 4, f"{e_g}", "t2", "end")]
  for tg in range(int(math.ceil(t0)), int(math.floor(t_end)) + 1):
    b += [T(TX(tg), py + ph + 16, f"{tg}", "t2", "middle")]
  thr = r.metrics["lane_threshold"]
  b += [el("line", None, x1=px0, y1=fmt(DY(-thr)), x2=px1, y2=fmt(DY(-thr)), class_="thr"),
        T(px1, DY(-thr) - 4, f"body on the 3.7 m lane line ({thr:.2f} m)", "t2", "end")]
  path = "M" + " L".join(f"{fmt(TX(f))},{fmt(DY(e))}" for f, e in zip(frames, e_f))
  b += [el("path", None, d=path, class_="trace")]
  cur = ";".join(f"{fmt(TX(f) - px0)},0" for f in frames) + f";{fmt(TX(frames[-1]) - px0)},0"
  b += [f'<g><animateTransform attributeName="transform" type="translate" values="{cur}" keyTimes="{kt}" '
        f'dur="{dur:.2f}s" repeatCount="indefinite"/>'
        f'<line x1="{px0}" y1="{fmt(py)}" x2="{px0}" y2="{fmt(py + ph)}" class="cursor"/></g>']

  # events, lit as they happen
  ev = [(0.0, f"fault: {spec['fault']}")]
  for key, label in (("refuse", "panda refuses LKA frames"), ("revoke", "panda revokes steering authority"),
                     ("siren", "panda siren (the driver's cue)")):
    if t[key] is not None:
      ev.append((t[key], label))
  if t["cue"] is not None and t["siren"] is None:
    ev.append((t["cue"], "driver cue: 0.2 m drift"))
  if t["t_line"] is not None:
    ev.append((t["t_line"], "body on the 3.7 m lane line"))
  if t["corr"] is not None:
    ev.append((t["corr"], "driver starts to correct"))
  ev.sort(key=lambda x: x[0])
  y = py + ph + 46
  b += [T(24, y - 6, "EVENTS (light up as they happen)", "t2b")]
  y += 14
  for te, label in ev:
    k0 = max(0.0, (te - t0) / dur)
    b += [f'<g opacity="0.25"><animate attributeName="opacity" values="0.25;1" keyTimes="0;{k0:.4f}" '
          f'calcMode="discrete" dur="{dur:.2f}s" repeatCount="indefinite"/>' +
          T(24, y, f"{te:.2f} s", "tb") + T(96, y, label, "t") + "</g>"]
    y += 22
  style_extra = ("<style>.laned { stroke:var(--ink3); stroke-width:2; } .egocar { fill:var(--flt); stroke:var(--ink); "
                 "stroke-width:1; } .trace { fill:none; stroke:var(--real); stroke-width:2.2; } .thr { stroke:var(--bad); "
                 "stroke-width:1.3; stroke-dasharray:6 4; } .ftti { fill:var(--amb-bg); } .cursor { stroke:var(--ink); "
                 "stroke-width:1.6; }</style>")
  out = fs.svg(int(y + 6), f"{he} animated: plant run {cid}",
               f"Synthetic (DSR-12), no evidence credit. Looping animation of plant run {cid} for {he}: the Corolla's "
               f"lateral offset on a straightened road from 1 s before the fault to {t_end:.1f} s after it, the offset "
               f"plot with a moving cursor and the 0.5 s FTTI band, and the events: " +
               "; ".join(f"{label} at {te:.2f} s" for te, label in ev) + ".", b)
  return out.replace("</style>", "</style>" + style_extra, 1)


# ---------------------------------------------------------------- build and check


def slug(he: str) -> str:
  return "he-" + he[3:].replace(".", "-")


def build() -> tuple[dict[str, str], list[str]]:
  h = hara()
  out, errs = {}, []
  for he in RUNS:
    r = run(he)
    t = times(r)
    errs += check_run(he, t)
    out[f"fig-sim-{slug(he)}-loop.svg"] = fig_loop(he, h[he], t)
    out[f"fig-sim-{slug(he)}-anim.svg"] = fig_anim(he, h[he], t, r)
  return out, errs


def problems() -> list[str]:
  errs = []
  c = asil_c()
  if c != sorted(list(RUNS) + list(KINEMATIC)):
    errs.append(f"ASIL C events in WP-C-03 are {c}; this script covers {sorted(list(RUNS) + list(KINEMATIC))}")
  return errs


def main(argv: list[str]) -> int:
  out, errs = build()
  errs = problems() + errs
  if "--check" in argv:
    errs += [f"{n} is stale; run fig_sim_he.py" for n, c in out.items()
             if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for e in errs:
      print(f"error: {e}", file=sys.stderr)
    if not errs:
      print(f"fig_sim_he: {len(out)} figures current; ASIL C events match WP-C-03")
    return 1 if errs else 0
  for n, c in out.items():
    (HERE / n).write_text(c, encoding="utf-8")
  for e in errs:
    print(f"warning: {e}", file=sys.stderr)
  print(f"wrote {len(out)} figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
