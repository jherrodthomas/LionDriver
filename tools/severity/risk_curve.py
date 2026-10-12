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
to 0 at 0 mph. `--low-speed` checks that segment against a logistic fit to the Tefft anchors
and the Hussain et al. (2019) meta-analysis: the linear risk is the higher of the three from
2 mph to 23 mph, and below 2 mph it is at most 0.006 under the logistic fit, whose non-zero
risk at 0 mph is an artefact of the logistic form. `--age` shifts the curve for the struck
person's age (AGE_SHIFT_MPH_PER_YEAR). One VRU is struck. The same curve is used for cyclists. This is
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
  rises from 0.41 to 0.73 and SH-04 from 0.053 to 0.094; the values of 1 are unchanged
  (`--joksch-mph 61.54`).
- Still to check against the full text: the constant, and which impact directions the curve
  was fitted to (the summaries say car-car collisions without naming a direction). `--curve
  richards` bounds the direction question with a frontal curve (see RICHARDS_FRONTAL_POINTS_MPH).
- Rear impacts (checked 2026-10-12, search summaries): the curve is applied to rear-struck
  occupants (the ego in SH-04, which dominates its bound, and the lead in SH-06/SH-03). At the
  same delta-v, rear impacts are less injurious than frontal ones: MAIS3+ risk at 30 mph delta-v
  is 19.9 % rear against 38.9 % frontal (NASS-CDS/CIREN regression, PMC3217552), and Jurewicz et
  al. (2016) put the 10 % MAIS3+ impact speed at 55 km/h for rear-end against 30 km/h for
  head-on and right-angle crashes. A car-car or frontal curve therefore overstates the
  rear-struck risk, and no credit is taken for that. Not covered: rear-seat occupants with
  intrusion from a heavy follower.
- The masses, occupancies and restitution below are checked by `--vehicles` (see VEHICLE_GRID):
  the defaults are the worst corner of the credible range.

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

EGO = {"name": "Corolla (reference vehicle)", "mass_kg": 1320, "occupants": 5}  # lowest 2020 LE curb weight (see VEHICLE_GRID)
LEADS = [
  {"name": "passenger car", "mass_kg": 1500, "occupants": 5},
  {"name": "heavy truck", "mass_kg": 36300, "occupants": 2},  # US 80,000 lb gross limit (see VEHICLE_GRID)
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


def pedestrian_fatality(speed_kmh: float, age_shift_mph: float = 0.0) -> float:
  """Risk of death of a pedestrian struck at this impact speed (Tefft 2011 anchors, linear between).

  age_shift_mph adds the speed by which an older person's risk curve leads the reference curve
  (see AGE_SHIFT_MPH_PER_YEAR)."""
  mph = speed_kmh * MPH_PER_KMH + age_shift_mph
  if mph > PEDESTRIAN_ANCHORS_MPH[-1][0] + 1e-9:
    return 1.0
  for (x0, y0), (x1, y1) in zip(PEDESTRIAN_ANCHORS_MPH, PEDESTRIAN_ANCHORS_MPH[1:], strict=False):
    if mph <= x1:
      return y0 + (y1 - y0) * (mph - x0) / (x1 - x0)
  return 1.0


# Age (`--age`). Tefft (2013, journal version): the risk of death of a 70-year-old struck at any
# speed is about that of a 30-year-old struck 11.8 mph faster (the 2011 report's 25 vs 35 mph
# example is for severe injury or death). With logit p = a + b * speed + c * age that is a constant speed shift
# of 11.8 / 40 mph per year of age. The Tefft anchors are for the average struck pedestrian, so
# the shift is taken from age 30, which overstates it while that average is older than 30.
# Age mix (checked 2026-10-12, search summaries): the sample is 422 pedestrians aged 15 and over
# with a mean age of 45 (the 2011 report adjusts its risks to "age = 45 years (mean age in
# sample)"); the published curve is standardised to the age mix of all US pedestrians struck in
# 2007-2009, whose mean was not found. The shift from 45 is printed as a central estimate; the
# bound from 30 stays the reported value until that mean is known.
# The 2011 report's own offset for death, the version of the anchors used here, is 10.4 mph
# (95 % CI 5.4-15.4 mph); its age-by-speed tables were not reachable (checked 2026-10-12). The
# journal's 11.8 mph is kept as the default because it is the larger point estimate;
# `--age-offset-mph 15.4` gives the upper confidence limit.
AGE_OFFSET_70_30_MPH = 11.8
AGE_OFFSET_70_30_2011_MPH, AGE_OFFSET_70_30_2011_CI_MPH = 10.4, (5.4, 15.4)
AGE_SHIFT_MPH_PER_YEAR = AGE_OFFSET_70_30_MPH / 40
AGE_REFERENCE_YEARS = 30
AGE_SAMPLE_MEAN_YEARS = 45
AGES_YEARS = (50, 70, 80)


# Elderly check (`--age`). Richards (2010) section 2.2.1.2, Ashton and Mackay data (GB, 1970s):
# at 30 mph the risk of death is 47 % for pedestrians aged 60+ and 5 % for 15-59; table 4.1 gives
# 14 % for all aged 15+. The odds ratio of 60+ against 15+ at 30 mph is applied to the Tefft
# average (an age effect from Ashton and Mackay, a level from Tefft), assuming the ratio holds at
# other speeds (age additive in the logit). It is set against the age-70 shift, as the 60+ group
# centres on about 70 (assumed; the report gives no mean age).
ASHTON_30MPH_ELDERLY, ASHTON_30MPH_ADULT, ASHTON_30MPH_15PLUS = 0.47, 0.05, 0.14


def odds(p: float) -> float:
  return p / (1 - p)


def from_odds(o: float) -> float:
  return o / (1 + o)


def ashton_elderly_odds_ratio() -> float:
  return odds(ASHTON_30MPH_ELDERLY) / odds(ASHTON_30MPH_15PLUS)


# Child check (`--age`). Same source: 4 % at 30 mph for children (0-14). Tefft's sample is 15 and
# over, so children are outside it; the report finds the child risk at or below the adult risk
# at the same impact speed in every dataset that has children. Its odds ratio against 15+ is
# applied to the Tefft average as for the elderly. The reference vehicle is a passenger car; a
# high-fronted SUV or light truck raises a child's odds of death by about 1.8 times (2.3 under
# age 10; LSHTM and Imperial College meta-analysis, Injury Prevention 2025, search summary),
# which this does not cover.
ASHTON_30MPH_CHILD = 0.04
LTV_CHILD_ODDS_RATIO = 1.82


def ashton_child_odds_ratio() -> float:
  return odds(ASHTON_30MPH_CHILD) / odds(ASHTON_30MPH_15PLUS)


def age_shift_mph(age_years: float, reference_years: float = AGE_REFERENCE_YEARS,
                  offset_70_30_mph: float = AGE_OFFSET_70_30_MPH) -> float:
  return max(0.0, (age_years - reference_years) * offset_70_30_mph / 40)


# Low-speed check of the linear segment from 0 to 23 mph (`--low-speed`). Two logistic curves,
# p = 1 / (1 + exp(-(a + b * v))), stand in for the risk below the first anchor:
# - the least-squares fit of logit(p) to the five Tefft anchors (fitted here, not Tefft's own
#   coefficients, which were not reachable);
# - Hussain et al. (2019), Accident Analysis and Prevention 129, 241-249, a meta-analysis of 20
#   studies: odds ratio 1.11 per km/h and 50 % at 59 km/h (5 % at 30 km/h, 10 % at 37 km/h).
TEFFT_LOGIT_A, TEFFT_LOGIT_B_PER_MPH = -5.108, 0.1246
HUSSAIN_OR_PER_KMH, HUSSAIN_P50_KMH = 1.11, 59.0
LOW_SPEED_MPH = tuple(range(24))


def logistic(x: float, a: float, b: float) -> float:
  import math
  return 1 / (1 + math.exp(-(a + b * x)))


def low_speed_check(speed_kmh: float) -> dict:
  """Linear segment against the two logistic curves at an impact speed below 23 mph."""
  import math
  b = math.log(HUSSAIN_OR_PER_KMH)
  return {"linear": pedestrian_fatality(speed_kmh),
          "tefft_logistic": logistic(speed_kmh * MPH_PER_KMH, TEFFT_LOGIT_A, TEFFT_LOGIT_B_PER_MPH),
          "hussain_logistic": logistic(speed_kmh, -b * HUSSAIN_P50_KMH, b)}


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


# Impact directions (`--curve richards`). The Joksch summaries say car-car collisions without
# naming the directions. Richards (2010), "Relationship between speed and risk of fatal injury:
# pedestrians and car occupants", DfT Road Safety Web Publication 16, fits belted drivers by
# direction on UK data: frontal 3/17/60 % at 30/40/50 mph delta-v, side 25/85 % at 30/40 mph.
# Checked 2026-10-12 against the report's text (section 3): the values are read off its fitted
# curves ("approximately"); the driver-curve coefficients are not published, so the logistic
# fit below goes through the three frontal points (within 0.005). Sample: belted drivers, one
# significant impact with another car, no rollover; OTS 2000-09 and CCIS 1983-2010 (cars under
# eight years old); 620 frontal (66 fatal) and 118 side (21 fatal); weighted to STATS19, which
# the report says is likely to overestimate the risk. Its delta-v is the momentum delta-v used
# here (two identical cars, one stationary, struck at 30 mph: 15 mph each). Half of the frontal
# deaths had a delta-v of 34 mph or less. The fit is above Joksch from about 33 mph delta-v, so
# it is a sensitivity for the frontal struck occupants of SH-03 and SH-06; applied to every
# occupant it also overstates the rear-struck ones. No case here has a side impact.
RICHARDS_FRONTAL_POINTS_MPH = ((30.0, 0.03), (40.0, 0.17), (50.0, 0.60))
RICHARDS_FRONTAL_A, RICHARDS_FRONTAL_B_PER_MPH = -9.315, 0.19408
OCCUPANT_CURVE = "joksch"


def richards_frontal(dv_kmh: float) -> float:
  return logistic(dv_kmh * MPH_PER_KMH, RICHARDS_FRONTAL_A, RICHARDS_FRONTAL_B_PER_MPH)


# Side impacts (checked 2026-10-12 against the report's text): belted drivers on the struck
# side, one significant side impact from another car; about 25 % at 30 mph and 85 % at 40 mph
# delta-v, and half of the drivers killed had a delta-v of 24 mph or less. The logistic below
# goes through the two points; below 30 mph it is an extrapolation. It is printed next to the
# primary-contact lateral delta-v of `--sh10` and `--sh02` to show why those collisions stay on
# the FARS/CRSS ratio: the primary contact is far below the side curve's lethal range, and the
# harm comes from the secondary impacts the ratio includes.
RICHARDS_SIDE_POINTS_MPH = ((30.0, 0.25), (40.0, 0.85))
RICHARDS_SIDE_A, RICHARDS_SIDE_B_PER_MPH = -9.598, 0.28332
RICHARDS_SIDE_MEDIAN_FATAL_DV_MPH = 24.0
RICHARDS_FRONTAL_MEDIAN_FATAL_DV_MPH = 34.0


def richards_side(dv_kmh: float) -> float:
  return logistic(dv_kmh * MPH_PER_KMH, RICHARDS_SIDE_A, RICHARDS_SIDE_B_PER_MPH)


# Pedestrian curves of Richards (2010), section 2 and table 4.1 (checked 2026-10-12 against the
# report's text), for comparison with Tefft (`--pedestrian-compare`). Risk of death at 30 and
# 40 mph impact speed, pedestrians aged 15 and over (Tefft's sample is also 15 and over); each
# is weighted to national casualties, which the report says is likely to overestimate the risk.
# A logistic through the two points stands in for each curve; outside 30-40 mph it extrapolates.
RICHARDS_PEDESTRIAN_15PLUS = {
  "Ashton and Mackay (GB, 1970s)": (0.14, 0.60),
  "OTS and police fatal files (GB, 2000-09)": (0.09, 0.33),
  "GIDAS, Rosén and Sander (DE, 1999-2007)": (0.07, 0.25),
}


def two_point_logistic_mph(mph: float, p30: float, p40: float) -> float:
  import math
  l30, l40 = math.log(p30 / (1 - p30)), math.log(p40 / (1 - p40))
  return logistic(mph - 30.0, l30, (l40 - l30) / 10.0)


def barrier_lateral_dv_kmh(speed_kmh: float, e: float = RESTITUTION) -> float:
  """Lateral delta-v of a departure into a barrier at the curve-departure angle (rigid barrier)."""
  import math
  return (1 + e) * speed_kmh * math.sin(math.radians(curve_departure_angle_deg(speed_kmh)))


def occupant_fatality(dv_kmh: float) -> float:
  return richards_frontal(dv_kmh) if OCCUPANT_CURVE == "richards" else joksch(dv_kmh)


def crash_fatal_ub(closing_kmh: float, ego: dict, lead: dict, e: float = RESTITUTION) -> dict:
  dv_e = delta_v(closing_kmh, ego["mass_kg"], lead["mass_kg"], e)
  dv_l = delta_v(closing_kmh, lead["mass_kg"], ego["mass_kg"], e)
  p_e, p_l = occupant_fatality(dv_e), occupant_fatality(dv_l)
  return {"closing_kmh": closing_kmh, "lead": lead["name"], "dv_ego_kmh": dv_e, "dv_lead_kmh": dv_l,
          "p_driver_ego": p_e, "p_driver_lead": p_l,
          "p_fatal_crash_ub": min(1.0, ego["occupants"] * p_e + lead["occupants"] * p_l)}


# Reference-vehicle check (`--vehicles`, 2026-10-12). Ego mass: 2020 Corolla LE curb weight
# 2,910-2,955 lb (1,320-1,340 kg; TrueDelta and AutoPadre listings, search summaries; Toyota's
# own sheet not reached); opendbc's TOYOTA_COROLLA_TSS2 CarSpecs gives 3,060 lb (1,388 kg) for
# the whole platform, hybrids included; with five 80 kg occupants about 1,720 kg. Seats: 5.
# Width 1,781 mm (the 1.78 m used in WP-S-04). Other vehicles: a small car of 1,100 kg and a
# large pickup of 2,700 kg around the 1,500 kg car; a truck of 15 t and one at the US 80,000 lb
# gross limit (36.3 t). Restitution: about 0.1 at closing speeds of 15 mph and above (low-speed
# test fits, search summary), so 0.1 holds for every case here (SH-04 closes at 27-35 km/h).
VEHICLE_GRID = {
  "ego_kg": (1320, 1388, 1400, 1720),
  "car_kg": (1100, 1500, 2700),
  "truck_kg": (15000, 36300),
}


def worst_vehicle_cases(ego_kg: float, car_kg: float, truck_kg: float, e: float = RESTITUTION) -> dict:
  """Worst P(fatal crash) bound per vehicle case for one set of masses."""
  ego = dict(EGO, mass_kg=ego_kg)
  others = [dict(LEADS[0], mass_kg=car_kg), dict(LEADS[1], mass_kg=truck_kg)]
  worst: dict = {}
  for sh, label, v in cases():
    key = (sh, label.split()[0])
    for other in others:
      worst[key] = max(worst.get(key, 0.0), crash_fatal_ub(v, ego, other, e)["p_fatal_crash_ub"])
  return worst


def main(argv: list[str] | None = None) -> int:
  global JOKSCH_MPH, OCCUPANT_CURVE
  ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
  ap.add_argument("--speed", type=float, action="append", help="closing speed in km/h (repeatable); default: the SH-06 and SH-03 cases")
  ap.add_argument("--restitution", type=float, default=RESTITUTION)
  ap.add_argument("--joksch-mph", type=float, default=JOKSCH_MPH_DEFAULT, help="Joksch reference delta-v in mph (sensitivity)")
  ap.add_argument("--curve", choices=("joksch", "richards"), default="joksch",
                  help="occupant curve: Joksch (default) or the Richards (2010) frontal fit (sensitivity)")
  ap.add_argument("--sensitivity", action="store_true", help="SH-04: print impact speed over follower reaction and braking")
  ap.add_argument("--sh10", action="store_true",
                  help="SH-10 (and the SH-01/02 sideswipe): print the contact angle and lateral speed")
  ap.add_argument("--sh02", "--sh01", dest="sh02", action="store_true",
                  help="SH-01/SH-02: print the barrier impact angle of a lane departure at the controller limit")
  ap.add_argument("--low-speed", action="store_true",
                  help="SH-11: compare the linear pedestrian risk below 23 mph with two logistic curves")
  ap.add_argument("--pedestrian-compare", action="store_true",
                  help="SH-11: compare the Tefft curve with the Richards (2010) pedestrian curves")
  ap.add_argument("--vehicles", action="store_true",
                  help="print the vehicle cases over the reference-vehicle and other-vehicle mass grid")
  ap.add_argument("--age", action="store_true",
                  help="SH-11: print the VRU cases with the risk curve shifted for the struck person's age")
  ap.add_argument("--age-offset-mph", type=float, default=AGE_OFFSET_70_30_MPH,
                  help="speed offset between ages 70 and 30 for --age (sensitivity; 2011 report: 10.4, CI 5.4-15.4)")
  a = ap.parse_args(argv)
  JOKSCH_MPH = a.joksch_mph
  OCCUPANT_CURVE = a.curve
  if a.vehicles:
    import itertools
    keys = [k for k in worst_vehicle_cases(1400, 1500, 15000) if not k[0].startswith("SH-06") and not k[0].startswith("SH-01")]
    print("| Ego (kg) | Car (kg) | Truck (t) | " + " | ".join(f"{sh} {odd}" for sh, odd in keys) + " |")
    print("|---|---|---|" + "---|" * len(keys))
    top = dict.fromkeys(keys, 0.0)
    for ego_kg, car_kg, truck_kg in itertools.product(*VEHICLE_GRID.values()):
      w = worst_vehicle_cases(ego_kg, car_kg, truck_kg, a.restitution)
      for k in keys:
        top[k] = max(top[k], w[k])
      print(f"| {ego_kg} | {car_kg} | {truck_kg / 1000:g} | " + " | ".join(f"{w[k]:.3f}" for k in keys) + " |")
    print("| **max** | | | " + " | ".join(f"**{top[k]:.3f}**" for k in keys) + " |")
    print("\nSH-06, SH-03 OS-07 and the SH-01/02 head-on are 1 at every point of the grid.")
    return 0
  if a.pedestrian_compare:
    rows = [("30 mph", 30 / MPH_PER_KMH), ("40 mph", 40 / MPH_PER_KMH)] + [(sh, v) for sh, _label, v in vru_cases()]
    print("| Impact | km/h | Tefft (used) | " + " | ".join(RICHARDS_PEDESTRIAN_15PLUS) + " |")
    print("|---|---|---|" + "---|" * len(RICHARDS_PEDESTRIAN_15PLUS))
    for name, v in rows:
      cols = [name, f"{v:.0f}", f"{pedestrian_fatality(v):.3f}"]
      cols += [f"{two_point_logistic_mph(v * MPH_PER_KMH, *pts):.3f}" for pts in RICHARDS_PEDESTRIAN_15PLUS.values()]
      print("| " + " | ".join(cols) + " |")
    print("\nRichards (2010) table 4.1, ages 15+; logistic through the 30 and 40 mph values, extrapolated outside them.")
    return 0
  if a.age:
    for ref, kind in ((AGE_REFERENCE_YEARS, "bound"), (AGE_SAMPLE_MEAN_YEARS, "central, sample mean")):
      ages = " | ".join(f"Age {y} (+{age_shift_mph(y, ref, a.age_offset_mph):.1f} mph)" for y in AGES_YEARS)
      print(f"\nShift from age {ref} ({kind}):\n")
      print("| SH / situation | Impact (km/h) | Average | " + ages + " |")
      print("|---|---|---|" + "---|" * len(AGES_YEARS))
      for sh, _label, v in vru_cases():
        cols = [sh, f"{v:.0f}", f"{pedestrian_fatality(v):.3f}"]
        cols += [f"{pedestrian_fatality(v, age_shift_mph(y, ref, a.age_offset_mph)):.3f}" for y in AGES_YEARS]
        print("| " + " | ".join(cols) + " |")
    ratio = ashton_elderly_odds_ratio()
    print(f"\nAshton and Mackay (Richards 2010), 60+ against 15+ at 30 mph: odds ratio {ratio:.2f}, applied to the average:\n")
    print("| SH / situation | Average | 60+ (on the curve used) | 60+ (on the logistic fit) | Age 70 bound |")
    print("|---|---|---|---|---|")
    for sh, _label, v in vru_cases():
      low = v * MPH_PER_KMH < PEDESTRIAN_ANCHORS_MPH[1][0]
      base_fit = low_speed_check(v)["tefft_logistic"] if low else pedestrian_fatality(v)
      bound = pedestrian_fatality(v, age_shift_mph(70, AGE_REFERENCE_YEARS, a.age_offset_mph))
      cols = [sh, f"{pedestrian_fatality(v):.3f}", f"{from_odds(odds(pedestrian_fatality(v)) * ratio):.3f}",
              f"{from_odds(odds(base_fit) * ratio):.3f}", f"{bound:.3f}"]
      print("| " + " | ".join(cols) + " |")
    child = ashton_child_odds_ratio()
    print(f"\nAshton and Mackay (Richards 2010), children (0-14) against 15+ at 30 mph: odds ratio {child:.2f}, applied to the average:\n")
    print(f"| SH / situation | Average | Child (passenger car) | Child, SUV or light truck (x {LTV_CHILD_ODDS_RATIO} odds) |")
    print("|---|---|---|---|")
    for sh, _label, v in vru_cases():
      p_child = from_odds(odds(pedestrian_fatality(v)) * child)
      p_ltv = from_odds(odds(p_child) * LTV_CHILD_ODDS_RATIO)
      print(f"| {sh} | {pedestrian_fatality(v):.3f} | {p_child:.3f} | {p_ltv:.3f} |")
    print("\nThe bound holds while the mean age of the standardisation population is above 30; the sample mean is 45.")
    print("Age 80 is extrapolated beyond the 30-70 comparison.")
    return 0
  if a.low_speed:
    print("| Impact (mph) | Impact (km/h) | Linear | Tefft logistic fit | Hussain 2019 | Linear covers both |\n|---|---|---|---|---|---|")
    for mph in LOW_SPEED_MPH:
      c = low_speed_check(mph / MPH_PER_KMH)
      ok = c["linear"] >= max(c["tefft_logistic"], c["hussain_logistic"])
      cols = [f"{mph}", f"{mph / MPH_PER_KMH:.0f}", f"{c['linear']:.4f}", f"{c['tefft_logistic']:.4f}",
              f"{c['hussain_logistic']:.4f}", "yes" if ok else "no"]
      print("| " + " | ".join(cols) + " |")
    for sh, label, v in vru_cases():
      if v * MPH_PER_KMH < PEDESTRIAN_ANCHORS_MPH[1][0]:
        c = low_speed_check(v)
        values = f"linear {c['linear']:.3f}, Tefft logistic fit {c['tefft_logistic']:.3f}, Hussain 2019 {c['hussain_logistic']:.3f}"
        print(f"\n{sh} ({label}, {v:.0f} km/h): {values}.")
    return 0
  if a.sh10:
    print("| Ego speed (km/h) | Lateral speed (km/h) | Contact angle (deg) | Lateral Δv per car (km/h) | Side curve |")
    print("|---|---|---|---|---|")
    for v in SH10_SPEEDS_KMH:
      c = lane_change_contact(v)
      cols = [f"{v:.0f}", f"{c['v_lat_kmh']:.1f}", f"{c['angle_deg']:.1f}", f"{c['dv_lateral_kmh']:.1f}",
              f"{richards_side(c['dv_lateral_kmh']):.5f}"]
      print("| " + " | ".join(cols) + " |")
    print("\nSide curve: Richards (2010), belted driver on the struck side, extrapolated below 30 mph.")
    return 0
  if a.sh02:
    print("| Speed (km/h) | Radius at 3.0 m/s² (m) | Angle at 4 m (deg) | Below 25° test angle | Lateral Δv (km/h) | Side curve |")
    print("|---|---|---|---|---|---|")
    for v in DEPARTURE_SPEEDS_KMH:
      ang = curve_departure_angle_deg(v)
      dv = barrier_lateral_dv_kmh(v)
      cols = [f"{v}", f"{(v / 3.6) ** 2 / A_Y_CTRL:.0f}", f"{ang:.1f}", "yes" if ang < BARRIER_TEST_ANGLE_DEG else "no",
              f"{dv:.1f}", f"{richards_side(dv):.4f}"]
      print("| " + " | ".join(cols) + " |")
    print("\nSide curve: Richards (2010), belted driver on the struck side (car-to-car data), extrapolated below 30 mph.")
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
