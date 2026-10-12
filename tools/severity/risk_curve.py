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

VERIFY BEFORE USE. The curve's form and its 71 mph constant are quoted from memory of the
paper, and the masses, occupancies and restitution below are assumptions. Check the curve
against the paper (including which impact directions and occupants it covers) and the
masses against the reference vehicle record, and record the check with the result.

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
JOKSCH_MPH = 71.0  # verify against the paper
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


def cases() -> list[tuple[str, str, float]]:
  """(SH and situation, case label, closing speed in km/h) for the ODD speed bounds."""
  out = []
  for odd, v in ODD_SPEEDS_KMH.items():
    out.append(("SH-06; SH-03 OS-07", f"{odd} stationary lead at {v} km/h", v))
    for name, t in T_FOLLOW_S.items():
      out.append(("SH-03 OS-05", f"{odd} following at {v} km/h, {name} gap", following_impact_kmh(v, t)))
    for h in OS08_GAPS_S:
      out.append(("SH-04 OS-08", f"{odd} struck from behind at {v} km/h, follower gap {h} s", rear_impact_kmh(v, h)))
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
  ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
  ap.add_argument("--speed", type=float, action="append", help="closing speed in km/h (repeatable); default: the SH-06 and SH-03 cases")
  ap.add_argument("--restitution", type=float, default=RESTITUTION)
  ap.add_argument("--sensitivity", action="store_true", help="SH-04: print impact speed over follower reaction and braking")
  a = ap.parse_args(argv)
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
  print("\nP(severity class), worst credible lead and gap:")
  for (sh, odd), w in worst.items():
    print(f"- {sh}, {odd}: {w:.3f}")
  print("Injury-crash budget: 1 (no injury curve; injury near certain at these delta-v).")
  return 0


if __name__ == "__main__":
  sys.exit(main())
