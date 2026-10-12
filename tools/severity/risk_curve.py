#!/usr/bin/env python3
"""P(severity class) from an injury-risk curve, for SH-06 and SH-03 (LionDriver WP-V-02 §3.5 item 3).

SH-06 is a rear-end collision into slow or stationary traffic with no braking before
impact. SH-03 is unintended acceleration into the lead: from a following gap (OS-05,
HE-03.1), or instead of braking while approaching slower traffic (OS-07, HE-03.3). Both are
more severe than the average rear-end crash in FARS/CRSS, so the ratio of severity_ratio.py
does not apply. Instead the fatality probability is read from an injury-risk curve at the
change of velocity (delta-v) of each vehicle.

Impact (closing) speed:
  SH-06, and SH-03 approaching (OS-07): the ODD speed bound against a stationary lead. For
    SH-03 the acceleration only adds to it, so this is a lower bound and the SH-06 value
    applies.
  SH-03 following (OS-05): the lead holds its speed; the ego starts at the same speed and
    accelerates at the envelope maximum a over the planner's following gap d:
      v_impact = sqrt(2 * a * d),  d = t_follow * v + STOP_DISTANCE
  SH-04 (OS-08, struck from behind): the ego brakes at the envelope minimum to a stop (not
    controlled); a follower at the same speed and time gap h holds its speed for its reaction
    time, then brakes. The relative speed at contact is the closing speed. The worst credible
    follower reacts after FOLLOWER_REACTION_S and brakes at FOLLOWER_DECEL; a follower that
    never brakes is outside this bound. `--sensitivity` prints the grid around it.

SH-11 (no reaction to a pedestrian or cyclist, OS-04 and OS-06) uses a pedestrian curve, not
Joksch: the person struck is unprotected and the ego's delta-v is irrelevant. Impact speed
is the travel speed with no braking: the OS-04 bound (60 km/h), and for OS-06 a launch from a
queue at the envelope maximum over the standstill gap, v = sqrt(2 * a * STOP_DISTANCE).
Curve: Tefft, B. C. (2011), "Impact Speed and a Pedestrian's Risk of Severe Injury or
Death", AAA Foundation for Traffic Safety, September 2011. Risk of death 10/25/50/75/90 % at
23/32/42/50/58 mph impact speed. These anchors were checked against search summaries of the
report (2026-10-12); the full text was not reachable from this environment. The data are US
pedestrians struck by a forward-moving car, light truck, van or SUV, 1994-1998, weighted for
oversampling. The journal version (Tefft 2013, Accident Analysis and Prevention 50, 871-878,
doi:10.1016/j.aap.2012.07.022) gives about 10 % near 24 mph and 50 % near 41 mph. At the
OS-04 bound of 37 mph that is about 0.40 instead of 0.38. Between anchors
the risk is interpolated linearly; above 58 mph it is 1, and below 23 mph it falls linearly
to 0 at 0 mph (an assumption). One VRU is struck. The same curve is used for cyclists. This is
conservative: cyclist curves put the risk at or below the pedestrian's at the same speed (Nie,
Li and Yang 2015: 50 % at 67.6 km/h for cyclists and 65.4 km/h for pedestrians; Lubbe, Wu and
Jeppsson 2022: 10 % serious injury at 44 and 29 km/h), checked from search summaries
(2026-10-12). See WP-V-02 section 3.5.

SH-01 and SH-02 (lane departure) are split by collision. A head-on in ODD-A (OS-03, HE-01.1,
HE-02.2) is a drift into the oncoming lane with no reaction, so the closing speed is the sum
of both vehicles' speeds at the ODD-A bound (90 + 90 km/h). That is worse than the average
head-on crash, so it is on the curve. Sideswipes and barrier impacts from a drift meet the
other vehicle or the barrier at a shallow angle, no worse than the average crash of their
type, so they stay on the FARS/CRSS ratio of severity_ratio.py. ODD-H is divided, so it has no
head-on case.
SH-02 departs in a curve (the car goes straight while the road bends, HE-02.1), so its
barrier impact is steeper than a drift. A car leaving a curve of radius R is at an angle
theta = sqrt(2 * d / R) by the time it is d metres off the curve (`--sh02`). With R at the
controller's 3.0 m/s^2 limit and d = 4 m (lane margin plus shoulder, assumed), theta is about
9-14 degrees at the OS-02 speeds of 70-110 km/h. That is below the 25 degrees at which barriers
are crash-tested (MASH test level 3, 100 km/h), so the impact is redirecting and the barrier
ratio still applies. Its head-on in a rural curve (OS-16, HE-02.2) is the head-on case above.
The same angle holds for an SH-01 departure on a straight road: with lateral acceleration a,
theta = sqrt(2 * d * a) / v, which equals sqrt(2 * d / R) for R = v^2 / a. At SH-01's 120 km/h
it is 8 degrees (`--sh01`). The SH-01 barrier impact is not put on a curve either: its primary
delta-v is a few km/h sideways, and its harm comes from the rebound, spin or rollover that
follows, which the barrier ratio includes and a delta-v curve does not.

`--sh10` checks that an SH-10 contact belongs to the sideswipe class. The lane change
accelerates sideways at the controller's 3.0 m/s^2 limit over the whole distance to contact,
with no S-curve easing. That distance is the two widest lane margins, 2 x 1.06 m (WP-S-04). Speeds
run from openpilot's lane-change minimum (20 mph, desire_helper.py) to 120 km/h. The lateral
closing speed stays at or below 13 km/h, about 7 km/h of delta-v per car. The contact angle is
6-12 degrees at 60-120 km/h and 22 degrees at the 20 mph minimum. That is the low-angle,
low-lateral-speed contact of a same-direction sideswipe, not the near-perpendicular impact of
an angle crash. The same bound covers an SH-01/02 drift into a vehicle in the adjacent lane.

SH-10 (lane change into an occupied lane) is deliberately not mapped to a curve. Its primary
contact is a same-direction sideswipe with a delta-v of a few km/h, so a delta-v curve would
give almost no risk. Its S3 rating (HE-02.5) comes from what follows: loss of control, or a
spin into traffic or a barrier. The curve does not model that, and would overstate the credit.
SH-10 uses the FARS/CRSS sideswipe-same-direction ratio of severity_ratio.py instead. That
crash type is typically caused by a lane change, and its statistics include the secondary
outcomes.

Delta-v from the closing speed v, by conservation of momentum with restitution e:
  dv_ego   = (1 + e) * v * m_other / (m_ego + m_other)
  dv_other = (1 + e) * v * m_ego   / (m_ego + m_other)

Curve (driver fatality risk): Joksch, H. C. (1993), "Velocity change and fatality risk in a
crash - a rule of thumb", Accident Analysis and Prevention 25(1), 103-104:
  p(dv) = min(1, (dv / 71 mph) ** 4)

The curve gives the risk per occupant. FARS counts a crash as fatal if anyone dies, so the
crash-level probability is bounded with the union bound, which holds whatever the
correlation between occupants:
  P(fatal crash) <= min(1, n_ego * p(dv_ego) + n_other * p(dv_other))

Check status (2026-10-12, from search summaries; the full text was not reachable):
- The citation is confirmed.
- The data are car-car collisions with the risk of occupant death; summaries name NASS
  1980-1986, and one names its predecessor NCSS.
- The fourth power is confirmed.
- One secondary source states the constant as 31.74 m/s, which is 71.0 mph, matching the value
  here. Another quotes it in a garbled form that reads like 61.54. With 61.54, SH-03 following
  rises from 0.33 to 0.59 and SH-04 from 0.043 to 0.076; the values of 1 are unchanged
  (`--joksch-mph 61.54`).
- Still to check against the full text: the constant, and whether the curve covers rear
  impacts (SH-04).
- The masses, occupancies and restitution below are assumptions. Check the masses against the
  reference vehicle record.

There is no injury curve here. At the delta-v of SH-06, a police-reported injury is near
certain, so for an injury-crash budget P(severity class) = 1.

Usage:
  tools/severity/risk_curve.py               # SH-06 table for the ODD speed bounds
  tools/severity/risk_curve.py --speed 70    # one closing speed in km/h
"""
from __future__ import annotations

import argparse
import sys

MPH_PER_KMH = 1 / 1.609344
JOKSCH_MPH_DEFAULT = 71.0  # 31.74 m/s per a secondary source; full text not yet checked
JOKSCH_MPH = JOKSCH_MPH_DEFAULT
RESTITUTION = 0.1  # assumed; small at high impact speed

EGO = {"name": "Corolla (reference vehicle)", "mass_kg": 1400, "occupants": 5}  # mass to confirm (WP-C-01)
LEADS = [
  {"name": "passenger car", "mass_kg": 1500, "occupants": 5},
  {"name": "heavy truck", "mass_kg": 15000, "occupants": 2},
]
ODD_SPEEDS_KMH = {"ODD-H": 120, "ODD-A": 90}  # speed bounds of WP-C-02 §3.1; closing speed for a stationary lead
ACCEL_MAX = 2.0  # m/s^2, envelope maximum (WP-C-02 §2, ACCEL_MAX)
T_FOLLOW_S = {"standard": 1.45, "relaxed": 1.75}  # long_mpc.py get_T_FOLLOW
STOP_DISTANCE_M = 6.0  # long_mpc.py
ACCEL_MIN = 3.5  # m/s^2, envelope minimum magnitude (WP-C-02 §2, ACCEL_MIN)
OS08_GAPS_S = (0.5, 1.0, 1.5)  # follower time gaps inside OS-08 (< 1.5 s)
FOLLOWER_REACTION_S = 2.0  # assumed worst credible follower reaction time
FOLLOWER_DECEL = 3.0  # m/s^2, assumed worst credible follower braking (below the ego's 3.5)


def delta_v(closing_kmh: float, m_self: float, m_other: float, e: float = RESTITUTION) -> float:
  """Delta-v of the vehicle with mass m_self, in km/h."""
  return (1 + e) * closing_kmh * m_other / (m_self + m_other)


def following_impact_kmh(speed_kmh: float, t_follow_s: float, accel: float = ACCEL_MAX) -> float:
  """SH-03 from a following gap: closing speed at impact after accelerating over the gap."""
  gap_m = t_follow_s * speed_kmh / 3.6 + STOP_DISTANCE_M
  return (2 * accel * gap_m) ** 0.5 * 3.6


def rear_impact_kmh(speed_kmh: float, gap_s: float, reaction_s: float = FOLLOWER_REACTION_S,
                    follower_decel: float = FOLLOWER_DECEL, ego_decel: float = ACCEL_MIN, dt: float = 0.001) -> float:
  """SH-04: relative speed (km/h) at which the follower strikes the braking ego; 0 if it stops short."""
  v = speed_kmh / 3.6
  x_ego, v_ego, x_f, v_f, t = v * gap_s, v, 0.0, v, 0.0
  while v_f > 0:
    v_ego = max(0.0, v_ego - ego_decel * dt)
    if t >= reaction_s:
      v_f = max(0.0, v_f - follower_decel * dt)
    x_ego += v_ego * dt
    x_f += v_f * dt
    t += dt
    if x_f >= x_ego:
      return (v_f - v_ego) * 3.6
  return 0.0


PEDESTRIAN_ANCHORS_MPH = [(0.0, 0.0), (23.0, 0.10), (32.0, 0.25), (42.0, 0.50), (50.0, 0.75), (58.0, 0.90)]  # Tefft 2011 (AAA Foundation)
OS04_SPEED_KMH = 60  # HARA OS-04 upper bound


def pedestrian_fatality(speed_kmh: float) -> float:
  """Risk of death of a pedestrian struck at this impact speed (Tefft 2011 anchors, linear between)."""
  mph = speed_kmh * MPH_PER_KMH
  if mph > PEDESTRIAN_ANCHORS_MPH[-1][0] + 1e-9:
    return 1.0
  for (x0, y0), (x1, y1) in zip(PEDESTRIAN_ANCHORS_MPH, PEDESTRIAN_ANCHORS_MPH[1:], strict=False):
    if mph <= x1:
      return y0 + (y1 - y0) * (mph - x0) / (x1 - x0)
  return 1.0


def vru_cases() -> list[tuple[str, str, float]]:
  """(SH and situation, case label, impact speed in km/h) for SH-11."""
  launch = (2 * ACCEL_MAX * STOP_DISTANCE_M) ** 0.5 * 3.6
  return [("SH-11 OS-04", f"VRU struck at {OS04_SPEED_KMH} km/h (OS-04 bound)", OS04_SPEED_KMH),
          ("SH-11 OS-06", f"VRU struck after launch from a queue over {STOP_DISTANCE_M:g} m", launch)]


A_Y_CTRL = 3.0  # m/s^2, controller lateral limit (drive_helpers.py MAX_LATERAL_ACCEL_NO_ROLL)
BARRIER_OFFSET_M = 4.0  # assumed lateral distance from the curve path to the barrier
BARRIER_TEST_ANGLE_DEG = 25.0  # MASH test level 3 impact angle
DEPARTURE_SPEEDS_KMH = (70, 90, 110, 120)  # HARA OS-02 (SH-02) 70-110 and OS-01 (SH-01) 90-120 km/h


def curve_departure_angle_deg(speed_kmh: float, offset_m: float = BARRIER_OFFSET_M, a_y: float = A_Y_CTRL) -> float:
  """Angle to the road edge when a car leaving a curve (radius v^2 / a_y) reaches offset_m."""
  import math
  radius = (speed_kmh / 3.6) ** 2 / a_y
  return math.degrees(math.sqrt(2 * offset_m / radius))


LANE_CHANGE_SPEED_MIN_KMH = 20 * 1.609344  # desire_helper.py LANE_CHANGE_SPEED_MIN
LANE_CHANGE_GAP_M = 2 * 1.06  # widest lane margins of ego and target-lane vehicle (WP-S-04 §3.1)
SH10_SPEEDS_KMH = (LANE_CHANGE_SPEED_MIN_KMH, 60, 90, 120)


def lane_change_contact(speed_kmh: float, gap_m: float = LANE_CHANGE_GAP_M, a_y: float = A_Y_CTRL,
                        e: float = RESTITUTION) -> dict:
  """SH-10 primary contact: lateral speed, contact angle and lateral delta-v (equal masses)."""
  import math
  v_lat = math.sqrt(2 * a_y * gap_m)  # m/s, accelerating laterally all the way (upper bound)
  angle = math.degrees(math.atan2(v_lat, speed_kmh / 3.6))
  return {"speed_kmh": speed_kmh, "v_lat_kmh": v_lat * 3.6, "angle_deg": angle,
          "dv_lateral_kmh": (1 + e) * v_lat * 3.6 / 2}


def cases() -> list[tuple[str, str, float]]:
  """(SH and situation, case label, closing speed in km/h) for the ODD speed bounds."""
  out = []
  for odd, v in ODD_SPEEDS_KMH.items():
    out.append(("SH-06; SH-03 OS-07", f"{odd} stationary lead at {v} km/h", v))
    for name, t in T_FOLLOW_S.items():
      out.append(("SH-03 OS-05", f"{odd} following at {v} km/h, {name} gap", following_impact_kmh(v, t)))
    for h in OS08_GAPS_S:
      out.append(("SH-04 OS-08", f"{odd} struck from behind at {v} km/h, follower gap {h} s", rear_impact_kmh(v, h)))
  v_a = ODD_SPEEDS_KMH["ODD-A"]
  out.append(("SH-01/02 OS-03/OS-16", f"ODD-A head-on, both at {v_a} km/h", 2 * v_a))
  return out


def joksch(dv_kmh: float) -> float:
  return min(1.0, (dv_kmh * MPH_PER_KMH / JOKSCH_MPH) ** 4)


def crash_fatal_ub(closing_kmh: float, ego: dict, lead: dict, e: float = RESTITUTION) -> dict:
  dv_e = delta_v(closing_kmh, ego["mass_kg"], lead["mass_kg"], e)
  dv_l = delta_v(closing_kmh, lead["mass_kg"], ego["mass_kg"], e)
  p_e, p_l = joksch(dv_e), joksch(dv_l)
  return {"closing_kmh": closing_kmh, "lead": lead["name"], "dv_ego_kmh": dv_e, "dv_lead_kmh": dv_l,
          "p_driver_ego": p_e, "p_driver_lead": p_l,
          "p_fatal_crash_ub": min(1.0, ego["occupants"] * p_e + lead["occupants"] * p_l)}


def main(argv: list[str] | None = None) -> int:
  global JOKSCH_MPH
  ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
  ap.add_argument("--speed", type=float, action="append", help="closing speed in km/h (repeatable); default: the SH-06 and SH-03 cases")
  ap.add_argument("--restitution", type=float, default=RESTITUTION)
  ap.add_argument("--joksch-mph", type=float, default=JOKSCH_MPH_DEFAULT, help="Joksch reference delta-v in mph (sensitivity)")
  ap.add_argument("--sensitivity", action="store_true", help="SH-04: print impact speed over follower reaction and braking")
  ap.add_argument("--sh10", action="store_true",
                  help="SH-10 (and the SH-01/02 sideswipe): print the contact angle and lateral speed")
  ap.add_argument("--sh02", "--sh01", dest="sh02", action="store_true",
                  help="SH-01/SH-02: print the barrier impact angle of a lane departure at the controller limit")
  a = ap.parse_args(argv)
  JOKSCH_MPH = a.joksch_mph
  if a.sh10:
    print("| Ego speed (km/h) | Lateral speed (km/h) | Contact angle (deg) | Lateral Δv per car (km/h) |\n|---|---|---|---|")
    for v in SH10_SPEEDS_KMH:
      c = lane_change_contact(v)
      print(f"| {v:.0f} | {c['v_lat_kmh']:.1f} | {c['angle_deg']:.1f} | {c['dv_lateral_kmh']:.1f} |")
    return 0
  if a.sh02:
    print("| Speed (km/h) | Radius at 3.0 m/s² (m) | Angle at 4 m (deg) | Below 25° test angle |\n|---|---|---|---|")
    for v in DEPARTURE_SPEEDS_KMH:
      ang = curve_departure_angle_deg(v)
      print(f"| {v} | {(v / 3.6) ** 2 / A_Y_CTRL:.0f} | {ang:.1f} | {'yes' if ang < BARRIER_TEST_ANGLE_DEG else 'no'} |")
    return 0
  if a.sensitivity:
    print("| Speed (km/h) | Gap (s) | " + " | ".join(f"t_r {tr} s, a_f {af}" for tr in (1.0, 1.5, 2.0) for af in (3.0, 4.0, 6.0)) + " |")
    print("|---|---|" + "---|" * 9)
    for v in ODD_SPEEDS_KMH.values():
      for h in OS08_GAPS_S:
        cells = [f"{rear_impact_kmh(v, h, tr, af):.0f}" for tr in (1.0, 1.5, 2.0) for af in (3.0, 4.0, 6.0)]
        print(f"| {v} | {h} | " + " | ".join(cells) + " |")
    print("\nRelative impact speed in km/h; 0 = the follower stops short.")
    return 0
  rows = [("custom", f"{v:g} km/h", v) for v in a.speed] if a.speed else cases()
  print("| SH / situation | Case | Closing (km/h) | Other vehicle | Δv ego (km/h) | Δv other (km/h) | p driver ego | p driver other | P(fatal crash) UB |")
  print("|---|---|---|---|---|---|---|---|---|")
  worst: dict = {}
  for sh, label, v in rows:
    for lead in LEADS:
      r = crash_fatal_ub(v, EGO, lead, a.restitution)
      key = (sh, label.split()[0])
      worst[key] = max(worst.get(key, 0.0), r["p_fatal_crash_ub"])
      cols = [sh, label, f"{v:.0f}", lead["name"], f"{r['dv_ego_kmh']:.0f}", f"{r['dv_lead_kmh']:.0f}",
              f"{r['p_driver_ego']:.3f}", f"{r['p_driver_lead']:.3f}", f"{r['p_fatal_crash_ub']:.3f}"]
      print("| " + " | ".join(cols) + " |")
  if not a.speed:
    print("\n| SH / situation | Case | Impact (km/h) | P(fatal), one VRU |\n|---|---|---|---|")
    for sh, label, v in vru_cases():
      p_vru = pedestrian_fatality(v)
      worst[(sh, "ODD-A")] = p_vru
      print(f"| {sh} | {label} | {v:.0f} | {p_vru:.3f} |")
  print("\nP(severity class), worst credible lead and gap:")
  for (sh, odd), w in worst.items():
    print(f"- {sh}, {odd}: {w:.3f}")
  print("Injury-crash budget: 1 (no injury curve; injury near certain at these delta-v).")
  return 0


if __name__ == "__main__":
  sys.exit(main())
