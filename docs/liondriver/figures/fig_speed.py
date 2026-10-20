#!/usr/bin/env python3
"""Draw the figures of docs/liondriver/speed-planning.md (pipeline, follow distance, limits, lead prediction, FCW timing).

Sources of record:
  - The MPC, planner and radard constants are read from the openpilot code with regular expressions
    (`long_mpc.py`, `longitudinal_planner.py`, `radard.py`, `drive_helpers.py`); a constant that changes form stops the
    generator.
  - Numbers that live in work products (envelope bounds, the 0x343 rate, the final-rate limit, the FCW budget of
    WP-S-04 §3.8.2) and the SH/FM labels are hand-listed, each with the exact text it is read from; `--check` fails when
    a text is gone.
  - opendbc is not checked out in CI, so the SoC clip ACCEL_MIN … ACCEL_MAX is taken from the FMEA item definition
    (PF-03), which states it for the reference car.

    python3 fig_speed.py            # write the SVGs into docs/assets/liondriver/
    python3 fig_speed.py --check    # fail if a source changed form or an SVG is stale

Standard library only. Output is deterministic.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fig_driving as fd  # noqa: E402
from fig_driving import (AMBER, AMBER_BG, CHIP, GREY_BG, HAIR, INK, LINE, MONO, MUTED, RED, REPO, SAFETY,  # noqa: E402
                         SAFETY_BG, SW, SW_BG, SourceError, el, fit, fmt_, header, legend, line, path, pill, rect, svg,
                         text, text_w)

OUT_DIR = REPO / "docs" / "assets" / "liondriver"
OUTS = {"pipeline": "speed-1-pipeline.svg", "follow": "speed-2-follow-distance.svg", "limits": "speed-3-limits.svg",
        "lead": "speed-4-lead-prediction.svg", "fcw": "speed-5-fcw-timing.svg"}
OP = REPO / "openpilot" / "selfdrive"
CODE = {
  "mpc": OP / "controls" / "lib" / "longitudinal_mpc_lib" / "long_mpc.py",
  "planner": OP / "controls" / "lib" / "longitudinal_planner.py",
  "radard": OP / "controls" / "radard.py",
  "helpers": OP / "controls" / "lib" / "drive_helpers.py",
  "longcontrol": OP / "controls" / "lib" / "longcontrol.py",
  "selfdrived": OP / "selfdrived" / "selfdrived.py",
}
AS = REPO / "assurance"
C05 = AS / "02-concept" / "WP-C-05-sotif-hazard-identification.md"
C07 = AS / "02-concept" / "WP-C-07-sotif-functional-modifications.md"
S04 = AS / "03-system" / "WP-S-04-timing-ftti-budget.md"
TEXTS = [
  (AS / "02-concept" / "WP-C-01-item-definition.md", "| Acceleration command | −3.5 … +2.0 m/s² |"),
  (AS / "08-analyses" / "fmea" / "item-definition.md",
   "Commanded longitudinal acceleration within −3.5 … +2.0 m/s² (platform); VF-001 SoC also uses +2.0 m/s² (`RAISED_ACCEL_LIMIT`"),
  (AS / "05-software" / "design-notes" / "DN-01-tx-rate-supervision.md", "| `0x343` | ACC_CONTROL | 33 Hz |"),
  (AS / "07-supporting" / "impact" / "change-2026-10-19-pin-e233362.md", "`ACCEL_FINAL_RATE_LIMIT` of 4.5 m/s³"),
  (AS / "07-supporting" / "impact" / "change-2026-10-12-opendbc-toyota-tx-arrival.md", "| `0x343` ACC_CONTROL | 30 ms | 100 ms (TSR-408) |"),
  (AS / "02-concept" / "WP-C-01-item-definition.md", "| AOU-04 | The stock PCS/AEB keeps full function"),
  (AS / "02-concept" / "WP-C-01-item-definition.md", "| AOU-05 | The PCM bounds ACC acceleration and deceleration requests"),
  (S04, "| 20 m/s | 1.68 s | 3.77 s |"),
  (S04, "| 30 m/s | 1.61 s | 3.20 s |"),
  (S04, "the FCW must sound within about 0.6 s of the lead's braking onset at a 1.0 s gap, and within 2.2 s at 1.5 s"),
  (S04, "lead braking at 6 m/s², the item braking at 3.5 m/s² from 0.3 s, actuator lag 0.2 s"),
  (S04, "| model `hardBrakePredicted` or planner FCW | not derived; measure (M-12) |"),
  (C05, "| SH-03 | Unintended acceleration: lead lost or misassociated"),
  (C05, "| SH-04 | Unintended deceleration (\"phantom braking\")"),
  (C05, "| SH-06 | Insufficient deceleration: stationary or slow vehicle not treated as lead"),
  (C05, "| SH-09 | Traffic-control non-compliance with over-trust"),
  (C05, "| SH-11 | No reaction to a VRU in or entering the path"),
  (C07, "| FM-01 | Experimental Mode off and locked in the reference configuration |"),
  (C07, "| FM-09 | ML action plausibility and uncertainty monitor |"),
  (C07, "| FM-11 | Restrict auto-resume from standstill |"),
]
ENV = {"a_min": -3.5, "a_max": 2.0, "rate_hz": 33, "final_rate": 4.5, "arrival_ms": 100}
FCW_CASES = [  # WP-S-04 §3.8.2: speed, time to contact at 1.0 s and 1.5 s gaps
  {"v": 20, "gap": 1.0, "contact": 1.68, "deadline": None}, {"v": 30, "gap": 1.0, "contact": 1.61, "deadline": 0.6},
  {"v": 20, "gap": 1.5, "contact": 3.77, "deadline": None}, {"v": 30, "gap": 1.5, "contact": 3.20, "deadline": 2.2},
]


def problems() -> list[str]:
  out, cache = [], {}
  for p, s in TEXTS:
    cache.setdefault(p, p.read_text(encoding="utf-8"))
    if s not in cache[p]:
      out.append(f"{p.relative_to(REPO)}: text gone: {s}")
  return out


def facts() -> dict:
  src = {k: p.read_text(encoding="utf-8") for k, p in CODE.items()}

  def num(key: str, name: str) -> float:
    m = re.search(rf"^{name}\s*=\s*(-?[\d.]+)", src[key], re.M)
    if not m:
      raise SourceError(f"{CODE[key].relative_to(REPO)}: {name} changed form; update fig_speed.py")
    return float(m.group(1))

  def lst(key: str, name: str) -> list[float]:
    m = re.search(rf"^{name}\s*=\s*\[([^\]]+)\]", src[key], re.M)
    if not m:
      raise SourceError(f"{CODE[key].relative_to(REPO)}: {name} changed form; update fig_speed.py")
    return [float(v) for v in m.group(1).split(",")]

  def need(key: str, pattern: str, what: str) -> re.Match:
    m = re.search(pattern, src[key], re.M)
    if not m:
      raise SourceError(f"{CODE[key].relative_to(REPO)}: {what} changed form; update fig_speed.py")
    return m

  f = {k: num("mpc", n) for k, n in [("n", "N"), ("max_t", "MAX_T"), ("comfort", "COMFORT_BRAKE"),
                                       ("stop", "STOP_DISTANCE"), ("crash", "CRASH_DISTANCE"),
                                       ("danger", "LEAD_DANGER_FACTOR")]}
  f["fcw_t"] = float(need("mpc", r"^FCW_IDXS = T_IDXS < ([\d.]+)", "FCW_IDXS").group(1))
  t = re.findall(r"if personality==log\.LongitudinalPersonality\.(\w+):\n\s*return ([\d.]+)",
                 src["mpc"][src["mpc"].index("def get_T_FOLLOW"):src["mpc"].index("def get_T_FOLLOW") + 600])
  if len(t) != 3:
    raise SourceError("long_mpc.py: get_T_FOLLOW changed form; update fig_speed.py")
  f["t_follow"] = {k: float(v) for k, v in t}
  need("mpc", r"return \(v_ego\*\*2\) / \(2 \* COMFORT_BRAKE\) \+ t_follow \* v_ego \+ STOP_DISTANCE", "safe distance")
  need("mpc", r"return \(v_lead\*\*2\) / \(2 \* COMFORT_BRAKE\)", "stopped equivalence")
  need("mpc", r"a_lead_traj = a_lead \* np\.exp\(-a_lead_tau \* \(T_IDXS\*\*2\)/2\.\)", "lead extrapolation")
  need("mpc", r"self\.crash_cnt \+= 1", "crash counter")
  need("mpc", r"radarstate\.leadOne\.modelProb > ([\d.]+)", "FCW model prob")
  f["fcw_prob"] = float(need("mpc", r"radarstate\.leadOne\.modelProb > ([\d.]+)", "FCW prob").group(1))
  f["fcw_cnt"] = int(need("planner", r"self\.fcw = self\.mpc\.crash_cnt > (\d+)", "planner FCW").group(1))
  f["cruise_max"], f["cruise_bp"] = lst("planner", "A_CRUISE_MAX_VALS"), lst("planner", "A_CRUISE_MAX_BP")
  f["cruise_min"] = num("planner", "A_CRUISE_MIN")
  f["turn_v"], f["turn_bp"] = lst("planner", "_A_TOTAL_MAX_V"), lst("planner", "_A_TOTAL_MAX_BP")
  f["tau_radar"] = num("radard", "_LEAD_ACCEL_TAU")
  f["tau_vision"] = float(need("radard", r'"aLeadTau": ([\d.]+),', "vision aLeadTau").group(1))
  f["v_stationary"] = num("radard", "V_EGO_STATIONARY")
  f["tau_rc"] = float(need("radard", r"self\.aLeadTau = FirstOrderFilter\(_LEAD_ACCEL_TAU, ([\d.]+), DT_MDL\)", "tau filter").group(1))
  f["tau_reset"] = float(need("radard", r"if abs\(self\.aLeadK\) < ([\d.]+):\n\s*self\.aLeadTau\.x = _LEAD_ACCEL_TAU", "tau reset").group(1))
  need("radard", r"self\.aLeadTau\.update\(0\.0\)", "tau decay")
  alpha = 0.05 / (f["tau_rc"] + 0.05)                  # FirstOrderFilter at DT_MDL
  f["tau_1s"] = f["tau_radar"] * (1 - alpha) ** 20     # after 1 s (20 radard steps) of braking above the reset
  need("planner", r"output_a_target, self\.mpc\.source, _ = min\(candidates", "min() arbitration")
  need("selfdrived", r"planner_fcw = self\.sm\['longitudinalPlan'\]\.fcw and self\.enabled", "planner FCW use")
  need("selfdrived", r"model_fcw = self\.sm\['modelV2'\]\.meta\.hardBrakePredicted", "model FCW use")
  need("longcontrol", r"def stock_aeb_stand_down", "stock AEB stand-down")
  n = int(f["n"])
  f["t_idxs"] = [f["max_t"] * (i / n) ** 2 for i in range(n + 1)]
  return f


# ---------------------------------------------------------------- shared drawing

def arrow(x1, y1, x2, y2, color=MUTED, dash="", label="", lx=None, ly=None, anchor="middle") -> list[str]:
  a = math.atan2(y2 - y1, x2 - x1)
  p1 = (x2 - 8 * math.cos(a - 0.4), y2 - 8 * math.sin(a - 0.4))
  p2 = (x2 - 8 * math.cos(a + 0.4), y2 - 8 * math.sin(a + 0.4))
  out = [line(x1, y1, x2, y2, stroke=color, sw=1.5, dash=dash),
         path(f"M{x2:.1f},{y2:.1f} L{p1[0]:.1f},{p1[1]:.1f} L{p2[0]:.1f},{p2[1]:.1f} Z", stroke=color, sw=1, fill=color)]
  if label:
    out.append(text(lx if lx is not None else (x1 + x2) / 2, ly if ly is not None else (y1 + y2) / 2 - 6, label,
                    size=9.5, fill=INK, anchor=anchor, family=MONO))
  return out


KIND = {"sw": ("#FFFFFF", SW), "model": (GREY_BG, INK), "off": (CHIP, MUTED), "safety": (SAFETY_BG, SAFETY),
        "car": (GREY_BG, INK), "ld": ("#FFFFFF", SAFETY)}


def box(x, y, w, h, title, lines_, kind="sw", chips=()) -> list[str]:
  fill, stroke = KIND[kind]
  out = [rect(x, y, w, h, fill=fill, stroke=stroke, sw=1.4, dash="5 4" if kind == "off" else "")]
  out.append(text(x + 10, y + 20, fit(title, w - 18, 12.5, True), size=12.5, weight=700, fill=MUTED if kind == "off" else INK))
  for i, s in enumerate(lines_):
    out.append(text(x + 10, y + 37 + i * 14.5, fit(s, w - 18, 10.5), size=10.5, fill=MUTED))
  cx = x + 10
  for label_, fill_ in chips:
    p, cw = pill(cx, y + h - 24, label_, fill_, size=9.5)
    out += p
    cx += cw + 5
  return out


def axes(x0, y0, w, h, xmax, ymin, ymax, xstep, ystep, xlabel, ylabel, xfmt="{:g}", yfmt="{:g}"):
  """Plot frame; returns (svg, X, Y) with X, Y mapping data to figure coordinates."""
  def X(v):
    return x0 + w * v / xmax

  def Y(v):
    return y0 + h - h * (v - ymin) / (ymax - ymin)
  out = [rect(x0, y0, w, h, fill="#FFFFFF", stroke=LINE, rx=0, sw=1)]
  v = 0.0
  while v <= xmax + 1e-9:
    out.append(line(X(v), y0, X(v), y0 + h, stroke=HAIR, sw=1))
    out.append(text(X(v), y0 + h + 15, xfmt.format(v), size=9.5, fill=MUTED, anchor="middle"))
    v += xstep
  v = ymin
  while v <= ymax + 1e-9:
    out.append(line(x0, Y(v), x0 + w, Y(v), stroke=HAIR, sw=1))
    out.append(text(x0 - 6, Y(v) + 3.5, yfmt.format(v), size=9.5, fill=MUTED, anchor="end"))
    v += ystep
  out.append(text(x0 + w / 2, y0 + h + 32, xlabel, size=10.5, fill=MUTED, anchor="middle"))
  out.append(el("text", ylabel, x=fmt_(x0 - 40), y=fmt_(y0 + h / 2), font_size=10.5, fill=MUTED, text_anchor="middle",
                transform=f"rotate(-90 {fmt_(x0 - 40)} {fmt_(y0 + h / 2)})"))
  return out, X, Y


def polyline(pts, color, sw=2.0, dash="") -> str:
  return path("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts), stroke=color, sw=sw, dash=dash)


# ---------------------------------------------------------------- Figure 1: pipeline

def build_pipeline(f: dict) -> str:
  W = 1320
  body = header(W, "1", "Speed planning, from leads to the brake",
                "Three candidate accelerations, the lowest wins; then clips, the controller, and the panda's bounds. "
                "Chips mark the SOTIF hazards (red) and modifications (amber) at each step.", "WP-C-05 · WP-C-07 · long_mpc.py")
  y1, h1, y2 = 110, 112, 270
  body += box(40, y1, 200, h1, "Leads (radard)", ["stock radar track matched", "to the model's lead, or",
                                                  "vision-only if prob > 0.5"], "sw", [("SH-03", RED), ("SH-04", RED), ("SH-06", RED)])
  body += box(290, y1, 230, h1, "MPC (acados, SQP_RTI)", [f"{int(f['n'])} steps to {f['max_t']:g} s, jerk input",
                                                          "keeps the follow distance", "of Figure 2"], "sw", [("FM-09", AMBER)])
  body += box(290, y1 + h1 + 16, 230, 74, "Cruise target", [f"toward set speed, {f['cruise_min']:g} … "
                                                            f"{f['cruise_max'][0]:g} m/s²", "less with speed (Figure 3)"], "sw")
  body += box(290, y1 + 2 * h1 - 6, 230, 96, "Model's own acceleration", ["Experimental Mode only;",
                                                                           "off by default"], "off", [("SH-09", RED), ("FM-01", AMBER)])
  body += box(570, y1 + h1 - 30, 130, 70, "min()", ["lowest wins"], "sw")
  body += box(750, y1 + h1 - 40, 180, 90, "Clip", [f"{ENV['a_min']:g} … +{ENV['a_max']:g} m/s²",
                                                   "longitudinalPlan, 20 Hz"], "sw")
  body += box(980, y1, 300, 112, "Controller (controlsd)", ["longcontrol: off / pid / stopping;",
                                                            "feedforward + integral, 100 Hz;",
                                                            "stock-AEB stand-down (LionDriver)"], "ld", [("SH-11", RED), ("FM-11", AMBER)])
  body += box(980, y1 + 136, 300, 76, "card → 0x343 ACC_CONTROL", [f"{ENV['rate_hz']} Hz; final rate ≤ {ENV['final_rate']:g} m/s³",
                                                                  "(carcontroller)"], "sw")
  body += box(980, y1 + 232, 300, 76, "Panda envelope", [f"{ENV['a_min']:g} … +{ENV['a_max']:g} m/s²; revoke if no frame",
                                                         f"for {ENV['arrival_ms']} ms; only while engaged"], "safety")
  body += box(980, y1 + 328, 300, 66, "PCM and stock PCS/AEB", ["own ACC envelope (AOU-05);", "AEB kept (AOU-04)"], "car")
  body += arrow(242, y1 + 56, 288, y1 + 56, label="radarState", ly=y1 + 49)
  for yy in (y1 + 56, y1 + h1 + 53, y1 + 2 * h1 + 42):
    body += arrow(522, yy, 568, y1 + h1 + 5, dash="5 4" if yy > y1 + 2 * h1 else "")
  body += arrow(702, y1 + h1 + 5, 748, y1 + h1 + 5)
  body += arrow(932, y1 + h1 + 5, 978, y1 + 56, label="aTarget", lx=938, ly=y1 + h1 - 22, anchor="start")
  for a_, b_ in ((y1 + 112, y1 + 136), (y1 + 212, y1 + 232), (y1 + 308, y1 + 328)):
    body += arrow(1130, a_ + 2, 1130, b_ - 2)
  ny = y1 + 420
  body.append(text(40, ny, "The MPC brakes for the lead it is given. A lead that radard drops, invents or places wrongly "
                   "(SH-03, SH-04, SH-06) is a perception problem, not a planner one.", size=11.5, fill=MUTED))
  lg, _ = legend(40, ny + 28, [("#FFFFFF", SW, "inherited openpilot code"), ("#FFFFFF", SAFETY, "has a LionDriver change"),
                               (SAFETY_BG, SAFETY, "safety envelope"), (CHIP, MUTED + " dashed", "off in the reference build")])
  body += lg
  desc = ("Leads from radard feed the MPC; the MPC, the cruise target and, in Experimental Mode only, the model's own "
          "acceleration go into min(); the result is clipped to −3.5 … +2.0 m/s², then the controller, card (0x343 at "
          "33 Hz), the panda envelope and the PCM. SOTIF hazards SH-03, SH-04 and SH-06 sit at the leads, SH-09 at the "
          "model's acceleration and SH-11 at the controller; FM-09, FM-01 and FM-11 at the MPC, the model's acceleration "
          "and the controller.")
  return svg(W, int(ny + 46), "Figure 1. Speed planning, from leads to the brake", desc, body)


# ---------------------------------------------------------------- Figure 2: follow distance

def build_follow(f: dict) -> str:
  W = 1320
  body = header(W, "2", "How far back the MPC wants to be",
                "From long_mpc.py: the gap it steers toward when following, and the distance it plans with when the "
                "lead is stopped.", "long_mpc.py get_safe_obstacle_distance, get_T_FOLLOW")
  vmax = 40
  # Left: steady following at the lead's speed. x_obstacle - x_ego = gap + v²/2b and desired = v²/2b + T·v + d0,
  # so the cost is zero at gap = T·v + d0; the soft danger-zone constraint is gap ≥ danger·desired − v²/2b.
  p, X, Y = axes(110, 110, 520, 300, vmax, 0, 80, 5, 10, "ego speed = lead speed (m/s)", "gap to lead (m)")
  body += p
  body.append(text(110, 100, "Following a lead at the same speed", size=13, weight=700))
  cols = {"relaxed": AMBER, "standard": SW, "aggressive": RED}
  for k, t in f["t_follow"].items():
    pts = [(X(v), Y(t * v + f["stop"])) for v in range(0, vmax + 1)]
    body.append(polyline(pts, cols[k]))
    body.append(text(X(vmax) + 6, Y(t * vmax + f["stop"]) + 4, f"{k} {t:g} s", size=10, fill=cols[k], weight=600))
  t_std = f["t_follow"]["standard"]
  body.append(text(110, 466, f"gap = T_follow · v + {f['stop']:g} m. At 30 m/s (108 km/h), standard: "
                   f"{t_std * 30 + f['stop']:.1f} m.", size=11, fill=INK))
  # Right: lead stopped. The MPC plans to stop STOP_DISTANCE short with COMFORT_BRAKE.
  p, X2, Y2 = axes(760, 110, 520, 300, vmax, 0, 400, 5, 50, "ego speed (m/s), lead stopped", "distance it plans with (m)")
  body += p
  body.append(text(760, 100, "Approaching a stopped car", size=13, weight=700))
  comfort = [(X2(v), Y2(v * v / (2 * f["comfort"]) + t_std * v + f["stop"])) for v in range(0, vmax + 1)]
  body.append(polyline(comfort, SW))
  body.append(text(X2(17), Y2(330), f"v²/(2·{f['comfort']:g}) + {t_std:g}·v + {f['stop']:g}", size=10.5, fill=SW,
                   family=MONO))
  hard = [(X2(v), Y2(v * v / (2 * -ENV["a_min"]))) for v in range(0, vmax + 1)]
  body.append(polyline(hard, RED, dash="5 4"))
  body.append(text(X2(24), Y2(40), f"stopping at the {ENV['a_min']:g} m/s² bound", size=10.5, fill=RED))
  v30 = 30
  body.append(text(760, 466, f"At 30 m/s it plans with {v30 ** 2 / (2 * f['comfort']) + t_std * v30 + f['stop']:.0f} m; the "
                   f"hardest stop the envelope allows takes {v30 ** 2 / (2 * -ENV['a_min']):.0f} m.", size=11, fill=INK))
  body.append(text(40, 494, f"Comfort brake {f['comfort']:g} m/s², stop {f['stop']:g} m short. The cost is soft: the MPC "
                   f"can end up closer than the line (a soft limit at {f['danger']:g} × the distance is weighted more), and the "
                   "item can never brake harder than the envelope.", size=11,
                   fill=MUTED))
  desc = ("Left: the gap the MPC steers toward when following a lead at the same speed, T_follow × v + 6 m, for relaxed "
          f"({f['t_follow']['relaxed']:g} s), standard ({t_std:g} s) and aggressive ({f['t_follow']['aggressive']:g} s), "
          f"and the soft danger-zone limit. Right: approaching a stopped car, the distance the MPC plans with, "
          f"v²/(2·{f['comfort']:g}) + {t_std:g}·v + {f['stop']:g}, against the distance to stop at {ENV['a_min']:g} m/s².")
  return svg(W, 512, "Figure 2. How far back the MPC wants to be", desc, body)


# ---------------------------------------------------------------- Figure 3: acceleration limits by speed

def interp(x: float, xp: list[float], fp: list[float]) -> float:
  if x <= xp[0]:
    return fp[0]
  for i in range(1, len(xp)):
    if x <= xp[i]:
      return fp[i - 1] + (fp[i] - fp[i - 1]) * (x - xp[i - 1]) / (xp[i] - xp[i - 1])
  return fp[-1]


def build_limits(f: dict) -> str:
  W = 1320
  body = header(W, "3", "Acceleration limits by speed",
                "Each layer can only narrow the one outside it. The cruise limits apply when no lead is closer; the "
                "MPC uses the outer clip.", "longitudinal_planner.py · WP-C-01 §8 · FMEA PF-03")
  vmax = 40
  p, X, Y = axes(110, 104, 820, 340, vmax, -4, 3, 5, 0.5, "speed (m/s)", "acceleration (m/s²)", yfmt="{:+g}")
  body += p
  body.append(rect(X(0), Y(ENV["a_max"]), X(vmax) - X(0), Y(ENV["a_min"]) - Y(ENV["a_max"]), fill=SAFETY_BG,
                   stroke="none", rx=0, opacity="0.6"))
  body.append(line(X(0), Y(0), X(vmax), Y(0), stroke=INK, sw=1))
  for v_, lab in ((ENV["a_max"], f"panda and planner clip +{ENV['a_max']:g}"), (ENV["a_min"], f"panda and planner clip {ENV['a_min']:g}")):
    body.append(line(X(0), Y(v_), X(vmax), Y(v_), stroke=SAFETY, sw=2))
    body.append(text(X(vmax) - 6, Y(v_) - 6 if v_ > 0 else Y(v_) + 16, lab, size=10.5, fill=SAFETY, anchor="end", weight=600))
  cruise = [(X(v / 2), Y(interp(v / 2, f["cruise_bp"], f["cruise_max"]))) for v in range(0, 2 * vmax + 1)]
  body.append(polyline(cruise, SW, sw=2.4))
  body.append(text(X(3), Y(f["cruise_max"][0]) - 8, "cruise acceleration max", size=10.5, fill=SW, weight=600))
  body.append(line(X(0), Y(f["cruise_min"]), X(vmax), Y(f["cruise_min"]), stroke=SW, sw=2.4))
  body.append(text(X(3), Y(f["cruise_min"]) + 16, f"cruise deceleration max {f['cruise_min']:g} (no lead)", size=10.5,
                   fill=SW, weight=600))
  # Right panel: notes.
  rx = 980
  notes = [
    ("Panda envelope", f"{ENV['a_min']:g} … +{ENV['a_max']:g} m/s², every frame, only while engaged (WP-C-01 §8)"),
    ("Planner clip", "ACCEL_MIN … ACCEL_MAX, the same values on the reference car (FMEA PF-03)"),
    ("Cruise target", f"to set speed: {', '.join(f'{a:g}' for a in f['cruise_max'])} m/s² at "
                      f"{', '.join(f'{b:g}' for b in f['cruise_bp'])} m/s; down to {f['cruise_min']:g}"),
    ("In a turn", f"total acceleration ≤ {f['turn_v'][0]:g}…{f['turn_v'][1]:g} m/s² ({f['turn_bp'][0]:g}…"
                  f"{f['turn_bp'][1]:g} m/s), so less forward pull while cornering"),
    ("Final rate", f"≤ {ENV['final_rate']:g} m/s³ on the 0x343 command (carcontroller)"),
  ]
  yy = 112
  for t_, s_ in notes:
    body.append(text(rx, yy, t_, size=12, weight=700))
    words, cur, rows = s_.split(), "", []
    for w_ in words:
      if text_w(cur + " " + w_, 10.5) > W - 40 - rx:
        rows.append(cur)
        cur = w_
      else:
        cur = (cur + " " + w_).strip()
    rows.append(cur)
    for i, r in enumerate(rows):
      body.append(text(rx, yy + 16 + i * 14, r, size=10.5, fill=MUTED))
    yy += 30 + 14 * len(rows)
  body.append(text(40, 496, "A lead needing more than 3.5 m/s² of braking is beyond what the item can do (SH-06); that "
                   "is what the stock AEB (AOU-04) and the FCW (Figure 5) are for.", size=11, fill=MUTED))
  lg, _ = legend(40, 522, [(SAFETY_BG, SAFETY, "envelope and clip"), ("#FFFFFF", SW, "cruise target limits")])
  body += lg
  desc = (f"Acceleration against speed: the panda envelope and planner clip at {ENV['a_min']:g} and +{ENV['a_max']:g} m/s²; "
          f"inside them the cruise limits, a maximum falling from {f['cruise_max'][0]:g} to {f['cruise_max'][-1]:g} m/s² "
          f"with speed and a minimum of {f['cruise_min']:g} m/s². Notes give the turn limit and the 4.5 m/s³ final rate.")
  return svg(W, 540, "Figure 3. Acceleration limits by speed", desc, body)


# ---------------------------------------------------------------- Figure 4: lead prediction

def lead_traj(f: dict, v0: float, a0: float, tau: float) -> list[float]:
  """long_mpc.extrapolate_lead: speed at the MPC's T_IDXS for a lead with acceleration a0 decaying at tau."""
  t, v, out, prev = f["t_idxs"], v0, [], 0.0
  for ti in t:
    a = a0 * math.exp(-tau * ti * ti / 2.0)
    v = max(0.0, v + (ti - prev) * a)
    prev = ti
    out.append(v)
  return out


def build_lead(f: dict) -> str:
  W = 1320
  v0, a0 = 25.0, -3.0
  body = header(W, "4", "What the MPC assumes the lead will do",
                f"A lead at {v0:g} m/s braking at {-a0:g} m/s² now: the MPC lets that braking fade, at a rate "
                "radard sets (tau).", "long_mpc.py extrapolate_lead · radard.py")
  p, X, Y = axes(110, 104, 820, 330, f["max_t"], 0, 30, 1, 5, "time ahead (s)", "predicted lead speed (m/s)")
  body += p
  series = [(f"radar, braking just seen (tau {f['tau_radar']:g})", f["tau_radar"], SW, ""),
            (f"vision-only (tau {f['tau_vision']:g})", f["tau_vision"], AMBER, ""),
            (f"radar, after 1 s of braking (tau {f['tau_1s']:.2f})", f["tau_1s"], RED, ""),
            ("constant braking", 0.0, MUTED, "5 4")]
  for i, (lab, tau, col, dash) in enumerate(series):
    vs = lead_traj(f, v0, a0, tau)
    pts = [(X(t), Y(v)) for t, v in zip(f["t_idxs"], vs)]
    body.append(polyline(pts, col, dash=dash))
    for x_, y_ in pts:
      body.append(el("circle", None, cx=fmt_(x_), cy=fmt_(y_), r=2.6, fill=col))
    if i < 3:
      body.append(text(X(f["max_t"]) - 8, Y(vs[-1]) - 8, f"{lab}: {vs[-1]:.1f} m/s at {f['max_t']:g} s", size=10.5,
                       fill=col, weight=600, anchor="end"))
    else:
      body.append(text(X(5.2), Y(13), lab, size=10.5, fill=col, weight=600))
  rx = 980
  rows = [("The formula", "a(t) = a₀ · exp(−tau · t² / 2)"), ("", "speed and position summed over the steps"),
          ("The steps", f"{int(f['n']) + 1} points at {f['max_t']:g}·(i/{int(f['n'])})² s"),
          ("Radar track", f"tau = {f['tau_radar']:g} while |a| < {f['tau_reset']:g} m/s²;"),
          ("", f"braking harder, tau falls toward 0 ({f['tau_rc']:g} s filter):"),
          ("", "the longer it brakes, the longer it is assumed to"),
          ("Vision-only", f"tau fixed at {f['tau_vision']:g}"),
          ("No lead", "a phantom lead 50 m ahead, 10 m/s faster")]
  yy = 112
  for t_, s_ in rows:
    if t_:
      body.append(text(rx, yy, t_, size=12, weight=700))
      yy += 16
    body.append(text(rx, yy, s_, size=10.5, fill=MUTED, family=MONO if "exp" in s_ else ""))
    yy += 22
  body.append(text(40, 486, "Just after a radar lead starts braking, the MPC expects most of it to fade; each new plan, "
                   "20 times a second, sees the new measurement and a smaller tau.", size=11, fill=MUTED))
  desc = (f"Predicted speed of a lead at {v0:g} m/s braking at {-a0:g} m/s², over the MPC's {int(f['n']) + 1} time steps to "
          f"{f['max_t']:g} s: with tau {f['tau_radar']:g} (radar, braking just seen) most of the braking fades; with "
          f"the vision-only tau {f['tau_vision']:g} less fades; after 1 s of radar braking tau is about {f['tau_1s']:.2f} "
          "and the prediction approaches constant braking, also shown.")
  return svg(W, 504, "Figure 4. What the MPC assumes the lead will do", desc, body)


# ---------------------------------------------------------------- Figure 5: FCW timing

def build_fcw(f: dict) -> str:
  W = 1320
  body = header(W, "5", "Forward collision warning: how late is too late",
                "A lead brakes at 6 m/s²; the item can brake at 3.5 m/s². WP-S-04 §3.8.2 gives the time to contact and "
                "when the warning must sound.", "WP-S-04 §3.8.2, T-31 · long_mpc.py · longitudinal_planner.py")
  x0, x1 = 300, W - 40
  span = 4.0

  def T(s: float) -> float:
    return x0 + (x1 - x0) * s / span

  y = 128
  for i, c in enumerate(FCW_CASES):
    yy = y + i * 50
    body.append(text(40, yy + 4, f"{c['v']} m/s, {c['gap']:g} s gap", size=12, weight=700))
    body.append(text(40, yy + 19, "WP-S-04 §3.8.2", size=10, fill=MUTED))
    body.append(rect(T(0), yy - 8, T(c["contact"]) - T(0), 14, fill=GREY_BG, stroke=MUTED, rx=3, sw=1))
    body.append(line(T(c["contact"]), yy - 14, T(c["contact"]), yy + 12, stroke=RED, sw=2))
    body.append(text(T(c["contact"]) + 6, yy + 3, f"contact at {c['contact']:g} s", size=10.5, fill=RED, weight=600))
    if c["deadline"] is not None:
      body.append(line(T(c["deadline"]), yy - 14, T(c["deadline"]), yy + 12, stroke=AMBER, sw=2))
      body.append(text(T(c["deadline"]) - 6, yy + 24, f"warning needed by ≈ {c['deadline']:g} s", size=10, fill=AMBER,
                       weight=600, anchor="end"))
  bottom = y + len(FCW_CASES) * 50 - 14
  for s in range(0, int(span) + 1):
    body.append(text(T(s), bottom + 14, f"{s} s", size=9.5, fill=MUTED, anchor="middle"))
    body.append(line(T(s), y - 20, T(s), bottom, stroke=HAIR, sw=1, dash="2 3"))
  body.append(text(T(0), y - 26, "lead starts braking", size=10, fill=MUTED))

  y2 = bottom + 50
  body.append(text(40, y2, "WHERE THE WARNING COMES FROM", size=12, weight=700, fill=SW))
  body += box(40, y2 + 14, 400, 92, "Planner FCW", [f"the MPC's plan meets the lead (gap < {f['crash']:g} m)",
                                                    f"within {f['fcw_t']:g} s, lead prob > {f['fcw_prob']:g}, on more than",
                                                    f"{f['fcw_cnt']} plans in a row: ≥ {(f['fcw_cnt'] + 1) * 0.05:.2f} s at 20 Hz"], "sw")
  body += box(470, y2 + 14, 400, 92, "Model FCW", ["the driving model's hardBrakePredicted", "(meta output, a learned guess",
                                                   "that hard braking is coming)"], "model")
  body += box(900, y2 + 14, 380, 92, "Status", ["onset after the lead brakes: not derived", "(T-31); to be measured (M-12)",
                                                "neither path is verified"], "ld")
  body.append(text(40, y2 + 136, "At a 1.0 s gap the driver gets well under a second; the earliest the planner path can "
                   "fire is a few plans after the MPC first sees the problem.", size=11, fill=MUTED))
  desc = ("Time from a lead's braking at 6 m/s² to contact, from WP-S-04 §3.8.2: 1.68 s at 20 m/s and 1.61 s at 30 m/s "
          "with a 1.0 s gap, 3.77 s and 3.20 s with a 1.5 s gap; the warning must sound within about 0.6 s and 2.2 s. "
          f"The planner FCW fires after more than {f['fcw_cnt']} consecutive plans predicting contact within "
          f"{f['fcw_t']:g} s; the model FCW is the learned hardBrakePredicted. The onset time is not derived (T-31).")
  return svg(W, int(y2 + 156), "Figure 5. Forward collision warning: how late is too late", desc, body)


# ---------------------------------------------------------------- main

def build_all() -> dict[str, str]:
  gone = problems()
  if gone:
    raise SourceError("speed figure sources changed:\n" + "\n".join(gone) + "\nreview fig_speed.py")
  f = facts()
  return {OUTS["pipeline"]: build_pipeline(f), OUTS["follow"]: build_follow(f), OUTS["limits"]: build_limits(f),
          OUTS["lead"]: build_lead(f), OUTS["fcw"]: build_fcw(f)}


def main(argv: list[str]) -> int:
  out = build_all()
  if "--check" in argv:
    stale = [n for n, s in out.items() if not (OUT_DIR / n).exists() or (OUT_DIR / n).read_text(encoding="utf-8") != s]
    if stale:
      print("stale: " + ", ".join(stale) + "\nrun: python3 docs/liondriver/figures/fig_speed.py", file=sys.stderr)
      return 1
    print(f"fig_speed: {len(out)} figures current")
    return 0
  for n, s in out.items():
    (OUT_DIR / n).write_text(s, encoding="utf-8")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
