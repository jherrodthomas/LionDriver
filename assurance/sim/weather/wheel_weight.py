#!/usr/bin/env python3
"""A weight on the steering wheel (physics plan round 4, study 25; WP-C-06 TC-25; WP-C-08 MC-06; WP-C-07 FM-05).

A mass m hung on the rim at radius r, at an angle φ from the top of the wheel, puts a steady torque m·g·r·sin φ on the
column. The Toyota port reads the column's torque sensor as STEER_TORQUE_DRIVER and sets `steeringPressed` when it
passes STEER_THRESHOLD; the car controller drops lateral control when it reaches MAX_USER_TORQUE. Those counts have no
published scale: the override study (`plant/override.py`) assumes MAX_USER_TORQUE is 2.0–5.0 N·m at the wheel and full
LKA torque 1.5–3.0 N·m at the column, and this study takes the same band (M-08 measures it).

Driver monitoring counts `steeringPressed` as the driver engaged. In the wheel-touch policy, used as soon as the driver
camera finds no face (or its model has been uncertain for 10 s) unless the alert has already reached orange, an engaged
driver resets awareness on every frame, distance bound (TSR-634) included; in the vision policy it resets only while
the driver also looks attentive. These lines are read and pinned here. Writes
`../results/wheel-weight.json` and `.md`.

    python3 wheel_weight.py --figures
    python3 wheel_weight.py --check

Synthetic (DSR-12), design aid, no evidence credit (DQ-413).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
ROOT = SIM.parents[1]
OPENDBC = ROOT / "opendbc_repo" / "opendbc" / "car" / "toyota"
POLICY = ROOT / "openpilot" / "selfdrive" / "monitoring" / "policy.py"
OVERRIDE = SIM / "plant" / "override.py"
AUTHORITY = SIM / "results" / "steer-authority.json"
OUT_JSON = SIM / "results" / "wheel-weight.json"
OUT_MD = SIM / "results" / "wheel-weight.md"
G = 9.81

PINS = (   # (file, pattern) the study rests on
  (OPENDBC / "carstate.py", r"ret\.steeringTorque = cp\.vl\[\"STEER_TORQUE_SENSOR\"\]\[\"STEER_TORQUE_DRIVER\"\]"),
  (OPENDBC / "carstate.py", r"ret\.steeringPressed = abs\(ret\.steeringTorque\) > STEER_THRESHOLD"),
  (POLICY, r"driver_engaged = sm\['carState'\]\.steeringPressed or sm\['carState'\]\.gasPressed"),
  (POLICY, r"if \(self\.driver_interacting and self\.awareness > 0 and self\.active_policy == MonitoringPolicy\.wheeltouch\) or"),
  (POLICY, r"def _reset_awareness\(self\):\n    self\.awareness = 1\.\n(?:    .*\n)*?    self\.wheeltouch_distance = 0\."),
  (POLICY, r"self\._HI_STD_FALLBACK_TIME = int\(10  / DT_DMON\)"),
  (POLICY, r"self\._set_policy\(MonitoringPolicy\.vision if self\.face_detected and not self\.is_model_uncertain else MonitoringPolicy\.wheeltouch\)"),
  (POLICY, r"if self\.active_policy == MonitoringPolicy\.vision and self\.awareness <= self\.threshold_alert_2:"),
)


def code() -> dict:
  for f, pat in PINS:
    if not re.search(pat, f.read_text(encoding="utf-8")):
      raise SystemExit(f"{f.name} changed: {pat!r} not found; review wheel_weight.py")
  def num(f, pat):
    m = re.search(pat, f.read_text(encoding="utf-8"), re.M)
    if not m:
      raise SystemExit(f"{f.name} changed: {pat!r} not found; review wheel_weight.py")
    return m.group(1)
  host = [float(x) for x in num(OVERRIDE, r"^HOST_THRESHOLD_NM = \(([^)]*)\)").split(",")]
  lka = [float(x) for x in num(OVERRIDE, r"^LKA_FULL_NM = \(([^)]*)\)").split(",")]
  return {"steer_threshold": int(num(OPENDBC / "values.py", r"^STEER_THRESHOLD = (\d+)")),
          "max_user_torque": int(num(OPENDBC / "carcontroller.py", r"^MAX_USER_TORQUE = (\d+)")),
          "host_threshold_nm": host, "lka_full_nm": lka, "fallback_s": 10.0, "pins": len(PINS)}  # fallback_s: the uncertain-model route; no face switches at once


def mass(torque_nm: float, r: float, angle_deg: float) -> float:
  """Mass on the rim that gives this torque: T / (g r sin φ)."""
  return torque_nm / (G * r * math.sin(math.radians(angle_deg)))


def run(p: dict) -> dict:
  w = p["wheel_weight"]
  c = code()
  r = w["rim_radius_m"]["value"]
  per_unit = [h / c["max_user_torque"] for h in c["host_threshold_nm"]]          # N·m per driver-torque count
  press_nm = [u * c["steer_threshold"] for u in per_unit]
  over_nm = c["host_threshold_nm"]
  laf = json.loads(AUTHORITY.read_text(encoding="utf-8"))["ceiling_m_s2"]["fit"]
  out = {"about": "Synthetic (DSR-12), design aid, no evidence credit. The override study's torque-scale band; "
                  "driver monitoring read from openpilot.",
         "code": c, "rim_radius_m": r, "press_nm": [round(x, 3) for x in press_nm], "override_nm": over_nm,
         "by_angle": {}, "authority": []}
  for ang in w["rim_angle_deg"]["value"]:
    out["by_angle"][f"{ang:g}"] = {
      "press_kg": [round(mass(t, r, ang), 3) for t in press_nm],
      "override_kg": [round(mass(t, r, ang), 3) for t in over_nm],
      "hold_kg": [round(mass(t, r, ang), 3) for t in c["lka_full_nm"]]}
  for t in press_nm:
    for lk in c["lka_full_nm"]:
      f = t / lk
      out["authority"].append({"weight_nm": round(t, 3), "lka_full_nm": lk, "share_used": round(f, 3),
                               "lateral_left_m_s2": round(laf * (1 - f), 3)})
  out["ceiling_m_s2"] = laf
  rlo, rhi = w["rim_radius_m"]["low"], w["rim_radius_m"]["high"]
  out["press_kg_radius_band"] = [round(mass(min(press_nm), rhi, 90), 3), round(mass(max(press_nm), rlo, 90), 3)]
  return out


def markdown(r: dict, p: dict) -> str:
  c = r["code"]
  a90 = r["by_angle"]["90"]
  a45 = r["by_angle"]["45"]
  au = r["authority"]
  most = max(au, key=lambda x: x["share_used"])
  least = min(au, key=lambda x: x["share_used"])
  L = [
    "# A weight on the steering wheel: what it does to driver monitoring and the steering",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`weather/wheel_weight.py`](../weather/wheel_weight.py) with the Toyota port and driver monitoring read and pinned "
    "from opendbc and openpilot; do not edit by hand. The torque counts have no published scale: the band is the "
    "override study's ([`override-l2.md`](override-l2.md)), until M-08 measures it.",
    "",
    f"`steeringPressed` is set above {c['steer_threshold']} counts of driver torque; the car controller drops lateral "
    f"control at {c['max_user_torque']}. With {c['max_user_torque']} counts taken as "
    f"{c['host_threshold_nm'][0]:g}–{c['host_threshold_nm'][-1]:g} N·m, the press threshold is "
    f"{r['press_nm'][0]:.1f}–{r['press_nm'][-1]:.1f} N·m. A weight on a {100 * r['rim_radius_m']:.1f} cm rim:",
    "",
    "| Where it hangs | Reads as the driver steering | Steering still holds the lane against it | Lateral control drops |",
    "|---|---|---|---|",
    f"| 3 or 9 o'clock | {a90['press_kg'][0]:.2f}–{a90['press_kg'][-1]:.2f} kg | up to {a90['hold_kg'][0]:.2f}–"
    f"{a90['hold_kg'][-1]:.2f} kg | {a90['override_kg'][0]:.1f}–{a90['override_kg'][-1]:.1f} kg |",
    f"| halfway up (45°) | {a45['press_kg'][0]:.2f}–{a45['press_kg'][-1]:.2f} kg | up to {a45['hold_kg'][0]:.2f}–"
    f"{a45['hold_kg'][-1]:.2f} kg | {a45['override_kg'][0]:.1f}–{a45['override_kg'][-1]:.1f} kg |",
    "",
    "## What this shows (generated)",
    "",
    f"- **A few hundred grams reads as a driver's hand.** {a90['press_kg'][0]:.2f}–{a90['press_kg'][-1]:.2f} kg at the "
    "side of the rim sets `steeringPressed` for as long as it hangs there.",
    f"- **With the driver camera blind, that switches driver monitoring off.** As soon as the camera finds no face "
    f"(covered, dark) monitoring falls back to the wheel-touch policy, unless its alert is already orange; there a "
    "steady `steeringPressed` resets awareness on every frame, the TSR-634 distance bound with it, so no alert ever "
    "comes. In the vision policy the same weight does nothing unless the driver also looks attentive.",
    "- **The planned fix does not catch it as worded.** FM-05(b) would restore awareness only for torque \"above a "
    "threshold for a minimum time\": a weight is both, all the time. A test for a change in the torque or the wheel's "
    "angle, or FM-05's cap on how often wheel-touch may restore awareness, would.",
    f"- **The weight also uses steering authority.** At the press threshold it takes {100 * least['share_used']:.0f}–"
    f"{100 * most['share_used']:.0f} % of full LKA torque, leaving {most['lateral_left_m_s2']:.2f}–"
    f"{least['lateral_left_m_s2']:.2f} m/s² of the controller's {r['ceiling_m_s2']:.2f} (study 26) for the road. Heavier "
    f"than {a90['hold_kg'][0]:.2f}–{a90['hold_kg'][-1]:.2f} kg the car drifts toward it; from "
    f"{a90['override_kg'][0]:.1f}–{a90['override_kg'][-1]:.1f} kg lateral control drops, which the driver would notice.",
    "- For the DM clinic (WP-C-08 V-5): a weight of about half a kilogram at the side of the rim with the driver camera "
    "covered. For FM-05: add a variation test to (b). The torque scale (M-08) turns the bands into numbers.",
    "",
  ]
  return "\n".join(L)


def main(argv):
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("--check", action="store_true")
  ap.add_argument("--figures", action="store_true")
  a = ap.parse_args(argv[1:])
  p = yaml.safe_load((HERE / "params.yaml").read_text(encoding="utf-8"))
  r = run(p)
  md = markdown(r, p)
  sys.path.insert(0, str(HERE))
  if a.check:
    from sun_glare import compare
    errs = compare(r, json.loads(OUT_JSON.read_text(encoding="utf-8")))
    if not errs and OUT_MD.read_text(encoding="utf-8") != md:
      errs.append(f"{OUT_MD.name} is stale")
    for e in errs[:20]:
      print("FAIL", e)
    print("wheel weight:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, indent=1) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name)
  if a.figures:
    import fig_weather
    fig_weather.wheel_weight_figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
