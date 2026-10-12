#!/usr/bin/env python3
"""P(severity class) from an injury-risk curve, for SH-06 (LionDriver WP-V-02 §3.5 item 3).

SH-06 is a rear-end collision into slow or stationary traffic with no braking before
impact. That is more severe than the average rear-end crash in FARS/CRSS, so the ratio of
severity_ratio.py does not apply. Instead the fatality probability is read from an
injury-risk curve at the change of velocity (delta-v) of each vehicle.

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


def delta_v(closing_kmh: float, m_self: float, m_other: float, e: float = RESTITUTION) -> float:
  """Delta-v of the vehicle with mass m_self, in km/h."""
  return (1 + e) * closing_kmh * m_other / (m_self + m_other)


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
  ap.add_argument("--speed", type=float, action="append", help="closing speed in km/h (repeatable); default: ODD bounds")
  ap.add_argument("--restitution", type=float, default=RESTITUTION)
  a = ap.parse_args(argv)
  speeds = [(f"{v:g} km/h", v) for v in a.speed] if a.speed else list(ODD_SPEEDS_KMH.items())
  print("| Case | Closing (km/h) | Lead | Δv ego (km/h) | Δv lead (km/h) | p driver ego | p driver lead | P(fatal crash) UB |")
  print("|---|---|---|---|---|---|---|---|")
  worst = {}
  for label, v in speeds:
    for lead in LEADS:
      r = crash_fatal_ub(v, EGO, lead, a.restitution)
      worst[label] = max(worst.get(label, 0.0), r["p_fatal_crash_ub"])
      cols = [label, f"{v:g}", lead["name"], f"{r['dv_ego_kmh']:.0f}", f"{r['dv_lead_kmh']:.0f}",
              f"{r['p_driver_ego']:.3f}", f"{r['p_driver_lead']:.3f}", f"{r['p_fatal_crash_ub']:.3f}"]
      print("| " + " | ".join(cols) + " |")
  print("\nSH-06 P(severity class), worst credible lead: " + ", ".join(f"{k} {w:.3f}" for k, w in worst.items()))
  print("Injury-crash budget: 1 (no injury curve; injury near certain at these delta-v).")
  return 0


if __name__ == "__main__":
  sys.exit(main())
