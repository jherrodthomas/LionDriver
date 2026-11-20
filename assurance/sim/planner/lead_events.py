#!/usr/bin/env python3
"""openpilot's planner through a cut-in, a cut-out and a hard-braking lead (physics plan round 4, studies 28–30;
WP-C-06 TC-07, TC-09, TC-08, TC-33).

openpilot's own longitudinal MPC (`long_mpc.py`, built by `mpc_build.py`) runs in a closed loop (`loop.py`) with a
point-mass car and scripted leads, at 20 Hz as the planner does. The item's braking is clipped at ACCEL_MIN, −3.5 m/s².
- **28. A close cut-in:** at 110 km/h a car enters our lane 0.5–1.5 s ahead, 0–30 km/h slower; the model takes it as
  the lead after a latency.
- **29. A cut-out:** we follow a lead at the planner's gap; it swerves out, uncovering a stopped car it would have
  reached 1–3 s later; the model takes the stopped car after a latency.
- **30. A lead braking hard:** we follow at the planner's gap; the lead brakes at 4–9 m/s² to a stop. With the item
  alone, and with a driver who brakes fully 1.5 s after openpilot's forward-collision warning.
Each run reports the braking the planner asked for, whether it hit the −3.5 m/s² clip, the closest gap and any impact
speed. The stock PCS is not modelled. Writes `../results/lead-events.json` and `.md`.

    python3 lead_events.py --figures
    python3 lead_events.py --check

Synthetic (DSR-12), design aid, no evidence credit (DQ-413). The solver is openpilot's; the car, the leads and the
model's latency are not.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import loop  # noqa: E402

SIM = HERE.parent
OUT_JSON = SIM / "results" / "lead-events.json"
OUT_MD = SIM / "results" / "lead-events.md"
P = loop.PERSONALITY
PERS = {"aggressive": P.aggressive, "standard": P.standard, "relaxed": P.relaxed}
CAR = 4.5


def t_follow(name: str) -> float:
  return float(loop.LM.get_T_FOLLOW(PERS[name]))


def follow_gap(v: float, name: str) -> float:
  return t_follow(name) * v + loop.LM.STOP_DISTANCE


def summary(r: loop.Result, extra: dict | None = None) -> dict:
  gaps = [g for g in r.gap if g is not None]
  out = {"min_gap_m": round(min(gaps), 2) if gaps else None, "max_brake": round(-min(r.a_cmd), 3),
         "at_clip_s": round(sum(1 for a in r.a_cmd if a <= loop.LM.ACCEL_MIN + 1e-6) * loop.DT, 2),
         "impact_kph": round(r.impact_v * 3.6, 1) if r.impact_v is not None else None,
         "fcw_s": r.fcw_t,
         "first_clip_s": next((t for t, a in zip(r.t, r.a_cmd) if a <= loop.LM.ACCEL_MIN + 0.05), None)}
  out.update(extra or {})
  return out


def cut_in(p: dict) -> list:
  c = p["cut_in"]
  v = c["ego_kph"] / 3.6
  rows = []
  for g in c["gap_s"]["value"]:
    for dv in c["slower_kph"]["value"]:
      vl = v - dv / 3.6
      for lat in p["latency_s"]["value"]:
        x0 = g * v + CAR
        def lead(t, x, x0=x0, vl=vl, lat=lat):
          return (t >= lat, x0 + vl * t, vl, 0.0)
        r = loop.run(v, lead, 25.0)
        rows.append(summary(r, {"gap_s": g, "slower_kph": dv, "latency_s": lat}))
  return rows


def cut_out(p: dict) -> list:
  rows = []
  for vk in p["speed_kph"]["value"]:
    v = vk / 3.6
    for name in PERS:
      for rv in p["cut_out"]["reveal_s"]["value"]:
        for lat in p["latency_s"]["value"]:
          gap = follow_gap(v, name)
          xs = gap + CAR + v * rv                 # the stopped car, from our front at the moment the lead clears
          # before it clears: the lead ahead at the gap; after: the stopped car, once the model has it
          def lead(t, x, gap=gap, v=v, xs=xs, lat=lat):
            if t < 0:
              return (True, gap + CAR + v * t, v, 0.0)
            return (t >= lat, xs, 0.0, 0.0)
          r = loop.run(v, lead, 20.0, personality=PERS[name])
          need = v * v / (2 * max(xs - CAR - v * lat, 0.1))   # constant braking from when the model has it
          rows.append(summary(r, {"speed_kph": vk, "personality": name, "reveal_s": rv, "latency_s": lat,
                                  "distance_m": round(xs - CAR, 1), "needed_brake": round(need, 2)}))
  return rows


def hard_brake(p: dict) -> list:
  rows = []
  d = p["driver"]
  for vk in p["hard_brake"]["speeds_kph"]:
    v = vk / 3.6
    for name in PERS:
      for al in p["hard_brake"]["lead_decel"]["value"]:
        gap = follow_gap(v, name)
        def lead(t, x, gap=gap, v=v, al=al):
          tb = 1.0                                 # the lead brakes 1 s in
          if t < tb:
            return (True, gap + CAR + v * t, v, 0.0)
          ts = v / al
          tt = min(t - tb, ts)
          return (True, gap + CAR + v * tb + v * tt - al * tt * tt / 2, max(v - al * tt, 0.0), -al if tt < ts else 0.0)
        alone = loop.run(v, lead, 20.0, personality=PERS[name])
        def driver(t, fcw, rt=d["reaction_s"]["value"], dec=d["decel"]["value"]):
          return dec if fcw is not None and t >= fcw + rt else None
        helped = loop.run(v, lead, 20.0, personality=PERS[name], driver=driver)
        rows.append({"speed_kph": vk, "personality": name, "lead_decel": al, "gap_m": round(gap, 1),
                     "alone": summary(alone), "with_driver": summary(helped)})
  return rows


def run(p: dict) -> dict:
  return {"about": "Synthetic (DSR-12), design aid, no evidence credit. openpilot's long_mpc.py solver in a closed loop "
                   "with a point-mass car; scripted leads; model latency assumed.",
          "accel_min": loop.LM.ACCEL_MIN, "actuator_delay_s": loop.H["actuator_delay"],
          "t_follow_s": {k: t_follow(k) for k in PERS}, "stop_distance_m": loop.LM.STOP_DISTANCE,
          "cut_in": cut_in(p), "cut_out": cut_out(p), "hard_brake": hard_brake(p)}


def compare(new, old, path="", tol=0.05):
  errs = []
  if isinstance(new, dict):
    if not isinstance(old, dict) or set(new) != set(old):
      return [f"{path}: keys differ"]
    for k in new:
      errs += compare(new[k], old[k], f"{path}/{k}", tol)
  elif isinstance(new, list):
    if not isinstance(old, list) or len(new) != len(old):
      return [f"{path}: length differs"]
    for i, (a, b) in enumerate(zip(new, old)):
      errs += compare(a, b, f"{path}[{i}]", tol)
  elif isinstance(new, (int, float)) and isinstance(old, (int, float)) and not isinstance(new, bool):
    if abs(new - old) > tol * max(1.0, abs(old)):
      errs.append(f"{path}: {old} -> {new}")
  elif new != old:
    errs.append(f"{path}: {old!r} -> {new!r}")
  return errs


def markdown(r: dict, p: dict) -> str:
  amin = -r["accel_min"]
  tf = r["t_follow_s"]
  L = [
    "# openpilot's planner through a cut-in, a cut-out and a hard-braking lead",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`planner/lead_events.py`](../planner/lead_events.py) with openpilot's own longitudinal MPC (`long_mpc.py`, built "
    "by [`mpc_build.py`](../planner/mpc_build.py)) in a closed loop with a point-mass car; do not edit by hand. The "
    "leads are scripted and the model's latency in taking a new lead is assumed (0.2–1 s). The stock PCS is not modelled.",
    "",
    f"The item brakes at most at {amin:.1f} m/s² (ACCEL_MIN). The planner follows at v·T + "
    f"{r['stop_distance_m']:.0f} m with T = {tf['aggressive']:g} / {tf['standard']:g} / {tf['relaxed']:g} s "
    f"(aggressive / standard / relaxed). The car follows the target after {r['actuator_delay_s']:.2f} s.",
    "",
    "## 28. A close cut-in at 110 km/h",
    "",
    "| Gap when it cuts in | Slower by | Most braking asked (latency 0.2 / 0.5 / 1 s) | Closest gap | Impact |",
    "|---|---|---|---|---|",
  ]
  ci = r["cut_in"]
  for g in p["cut_in"]["gap_s"]["value"]:
    for dv in p["cut_in"]["slower_kph"]["value"]:
      rs = [x for x in ci if x["gap_s"] == g and x["slower_kph"] == dv]
      imp = [x["impact_kph"] for x in rs if x["impact_kph"] is not None]
      L.append(f"| {g:g} s | {dv} km/h | " + " / ".join(f"{x['max_brake']:.1f}" for x in rs) + " m/s² | "
               f"{min(x['min_gap_m'] for x in rs):.1f} m | " + (f"up to {max(imp):.0f} km/h" if imp else "none") + " |")
  co = r["cut_out"]
  L += ["", "## 29. A cut-out uncovers a stopped car (standard personality, latency 0.5 s)", "",
        "| Speed | Reveal: lead 1 / 1.5 / 2 / 3 s from the stopped car | Braking needed | Impact speed, item alone |",
        "|---|---|---|---|"]
  for vk in p["speed_kph"]["value"]:
    rs = [x for x in co if x["speed_kph"] == vk and x["personality"] == "standard" and x["latency_s"] == 0.5]
    L.append(f"| {vk} km/h | " + " / ".join(f"{x['distance_m']:.0f} m" for x in rs) + " | " +
             " / ".join(f"{x['needed_brake']:.1f}" for x in rs) + " m/s² | " +
             " / ".join("none" if x["impact_kph"] is None else f"{x['impact_kph']:.0f} km/h" for x in rs) + " |")
  hb = r["hard_brake"]
  L += ["", "## 30. A lead braking hard (standard personality)", "",
        "| Speed | Lead brakes at | Gap before | Item alone: impact | FCW after the lead brakes | With a driver 1.5 s after FCW |",
        "|---|---|---|---|---|---|"]
  for x in [x for x in hb if x["personality"] == "standard"]:
    a, w = x["alone"], x["with_driver"]
    L.append(f"| {x['speed_kph']} km/h | {x['lead_decel']:g} m/s² | {x['gap_m']:.0f} m | "
             + ("none" if a["impact_kph"] is None else f"{a['impact_kph']:.0f} km/h") + " | "
             + ("none" if a["fcw_s"] is None else f"{a['fcw_s'] - 1.0:.1f} s") + " | "
             + ("no impact" if w["impact_kph"] is None else f"{w['impact_kph']:.0f} km/h") + " |")
  # generated findings
  ci_imp = [x for x in ci if x["impact_kph"] is not None]
  ci_clip = [x for x in ci if x["at_clip_s"] > 0]
  co110 = [x for x in co if x["speed_kph"] == 110 and x["latency_s"] == 0.5]
  co_ok = [x for x in co if x["impact_kph"] is None]
  slowest_hit = min((x["speed_kph"] for x in co if x["impact_kph"] is not None), default=None)
  hb_alone = [x for x in hb if x["alone"]["impact_kph"] is not None]
  hb_help = [x for x in hb if x["with_driver"]["impact_kph"] is not None]
  ramps = [x["alone"]["first_clip_s"] - 1.0 for x in hb if x["alone"]["first_clip_s"] is not None]
  fcws = [x["alone"]["fcw_s"] - 1.0 for x in hb if x["alone"]["fcw_s"] is not None]
  L += ["", "## What this shows (generated)", "",
        f"- **A cut-in:** the planner ramps its braking up rather than braking hard at once (its jerk and "
        f"acceleration-change costs); it reaches the {amin:.1f} m/s² clip in {len(ci_clip)} of {len(ci)} runs and hits "
        f"the car in {len(ci_imp)}" +
        (f" (up to {max(x['impact_kph'] for x in ci_imp):.0f} km/h: cut-ins half a second ahead and 20–30 km/h slower)."
         if ci_imp else "."),
        f"- **A cut-out is the planner's hard case.** At 110 km/h the uncovered car is "
        f"{min(x['distance_m'] for x in co110):.0f}–{max(x['distance_m'] for x in co110):.0f} m away and the item alone hits it "
        f"in {sum(1 for x in co110 if x['impact_kph'] is not None)} of {len(co110)} runs. "
        + (f"Below {slowest_hit} km/h no run hits it." if slowest_hit and slowest_hit > min(p['speed_kph']['value'])
           else "Impacts happen at every speed studied when the lead swerves late.")
        + " The stopping is the driver's and the stock PCS's (WP-C-02 F-02).",
        f"- **A lead braking hard:** the planner takes {min(ramps):.1f}–{max(ramps):.1f} s after the lead starts braking "
        f"to reach its {amin:.1f} m/s² clip, and the item alone hits the lead in {len(hb_alone)} of {len(hb)} runs, even "
        f"at 4 m/s². openpilot's FCW comes {min(fcws):.1f}–{max(fcws):.1f} s after the lead starts braking; a driver who "
        f"brakes fully 1.5 s after it " + ("avoids every impact." if not hb_help else
        f"still hits in {len(hb_help)} of {len(hb)}: the stock PCS, not modelled here, has to act first."),
        "- For KS tests: cut-outs uncovering a stopped car are where the item's braking bound stops covering the "
        "scenario; the stock PCS (not modelled) is the backstop. A drive log with the model's lead latency would turn "
        "the latency band into a line.",
        ""]
  return "\n".join(L)


def main(argv):
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("--check", action="store_true")
  ap.add_argument("--figures", action="store_true")
  a = ap.parse_args(argv[1:])
  p = yaml.safe_load((HERE / "params.yaml").read_text(encoding="utf-8"))
  r = run(p)
  md = markdown(r, p)
  if a.check:
    errs = compare(r, json.loads(OUT_JSON.read_text(encoding="utf-8")))
    if not errs and OUT_MD.read_text(encoding="utf-8") != md:
      errs.append(f"{OUT_MD.name} is stale")
    for e in errs[:20]:
      print("FAIL", e)
    print("lead events:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, indent=1) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name)
  if a.figures:
    import fig_planner
    fig_planner.figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
