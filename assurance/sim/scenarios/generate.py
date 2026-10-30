#!/usr/bin/env python3
"""Write the WP-V-03 known scenarios that simulation can represent as ASAM OpenSCENARIO 1.3 (XOSC) and OpenDRIVE 1.5
(XODR) files named by scenario ID, with the Python library scenariogeneration (MPL-2.0).

    python3 assurance/sim/scenarios/generate.py           # write xosc/ and xodr/
    python3 assurance/sim/scenarios/generate.py --check   # fail if a committed file differs

Each scenario fixes the road and the other road users. The ego vehicle is the item under test: in the files it only
gets its initial position and speed, and a harness (the plant model, MetaDrive) or esmini's default controller drives
it. Parameters carry the WP-V-03 values as defaults; the sweep values are listed in SCENARIOS and in README.md.
Highway only (ODD-H; DQ-023 answered B): 3 lanes, lane IDs -1 (left) to -3 (right), ego in -2 unless stated; KS-27 is
a one-lane ramp (lane -1) with a wall on the inside of its curve.
"""

from __future__ import annotations

import datetime
import math
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from scenariogeneration import xodr, xosc

HERE = Path(__file__).resolve().parent
FIXED_DATE = datetime.datetime(2026, 10, 16)   # header date, so that the files are reproducible
AUTHOR = "LionDriver simulation track (synthetic scenario, DSR-12)"
LANE_W = 3.7
EGO_S = 50.0


@dataclass
class Scenario:
  id: str
  title: str
  road: dict                      # {"length": m} or {"straight": m, "clothoid": m, "radius": m, "arc": m}; "lane_width",
                                  # "lanes" (default 3), "wall": {"t": m, "height": m} along the curve
  params: dict                    # name -> (default, sweep values, unit, meaning)
  build: callable = None
  checks: list = field(default_factory=list)   # descriptions; replay.py implements them
  duration: float = 20.0
  variants: dict = field(default_factory=dict)  # file suffix -> road overrides: the same scenario on other roads


def files_of(sc: Scenario) -> list[tuple[str, dict]]:
  """(file ID, road) for the scenario's own road and each road variant, e.g. KS-27 and KS-27-R400."""
  return [(sc.id, sc.road)] + [(f"{sc.id}-{k}", {**sc.road, **v}) for k, v in sc.variants.items()]


# ------------------------------------------------------------------------------------------------ entities
def corolla() -> xosc.Vehicle:
  # body width confirmed (WP-V-02 §3.5); wheelbase from opendbc; length and height for drawing only (unconfirmed)
  bb = xosc.BoundingBox(1.781, 4.63, 1.43, 1.3, 0, 0.72)
  return xosc.Vehicle("corolla_e210", xosc.VehicleCategory.car, bb, xosc.Axle(0.5, 0.65, 1.53, 2.67, 0.3),
                      xosc.Axle(0, 0.65, 1.53, 0, 0.3), 69, 4, 9)


def car(name="car") -> xosc.Vehicle:
  bb = xosc.BoundingBox(1.85, 4.8, 1.5, 1.4, 0, 0.75)
  return xosc.Vehicle(name, xosc.VehicleCategory.car, bb, xosc.Axle(0.5, 0.65, 1.6, 2.8, 0.3),
                      xosc.Axle(0, 0.65, 1.6, 0, 0.3), 69, 4, 9)


def truck() -> xosc.Vehicle:
  bb = xosc.BoundingBox(2.55, 16.5, 4.0, 7.0, 0, 2.0)
  return xosc.Vehicle("truck", xosc.VehicleCategory.truck, bb, xosc.Axle(0.5, 1.0, 2.1, 12.0, 0.5),
                      xosc.Axle(0, 1.0, 2.1, 0, 0.5), 35, 1.5, 6)


def step(value):
  return xosc.TransitionDynamics(xosc.DynamicsShapes.step, xosc.DynamicsDimension.time, value)


def place(init: xosc.Init, name: str, s, lane: int, speed, offset=0.0):
  init.add_init_action(name, xosc.TeleportAction(xosc.LanePosition(s, offset, lane, 0)))
  init.add_init_action(name, xosc.AbsoluteSpeedAction(speed, step(0)))


def at_time(t: float):
  label = t.strip("$") if isinstance(t, str) else f"{t:g}s"
  return xosc.ValueTrigger(f"at_{label}", 0, xosc.ConditionEdge.none, xosc.SimulationTimeCondition(t, xosc.Rule.greaterThan))


def story(name: str, actor: str, action, trigger) -> xosc.Story:
  ev = xosc.Event(name, xosc.Priority.override)
  ev.add_action(name, action)
  ev.add_trigger(trigger)
  man = xosc.Maneuver(name)
  man.add_event(ev)
  mg = xosc.ManeuverGroup(name)
  mg.add_actor(actor)
  mg.add_maneuver(man)
  act = xosc.Act(name, at_time(0))
  act.add_maneuver_group(mg)
  st = xosc.Story(name)
  st.add_act(act)
  return st


# ------------------------------------------------------------------------------------------------ roads
def road_xodr(fid: str, r: dict) -> xodr.OpenDrive:
  w = r.get("lane_width", LANE_W)
  if "radius" in r:
    k = 1.0 / r["radius"]
    geoms = [xodr.Line(r["straight"]), xodr.Spiral(1e-9, k, r["clothoid"]), xodr.Arc(k, r["arc"])]
  else:
    geoms = [xodr.Line(r["length"])]
  road = xodr.create_road(geoms, 0, left_lanes=0, right_lanes=r.get("lanes", 3), lane_width=w)
  if "wall" in r:
    # a continuous wall from the start of the clothoid to the end of the arc, t > 0: left of the reference line,
    # which is the inside of the left curve
    s0, wl = r["straight"], r["clothoid"] + r["arc"]
    wall = xodr.Object(s0, r["wall"]["t"], Type=xodr.ObjectType.soundBarrier, subtype="wall", name="sight_wall",
                       height=r["wall"]["height"], length=0.3,
                       width=0.3)
    wall.repeat(wl, 0, sStart=s0, tStart=r["wall"]["t"], tEnd=r["wall"]["t"], heightStart=r["wall"]["height"],
                heightEnd=r["wall"]["height"], widthStart=0.3, widthEnd=0.3)
    road.add_object(wall)
  odr = xodr.OpenDrive(fid)
  odr.add_road(road)
  odr.adjust_roads_and_lanes()
  return odr


# ------------------------------------------------------------------------------------------------ scenarios
def ks01(sb_init, ent):
  ent.add_scenario_object("ego", corolla())
  place(sb_init, "ego", EGO_S, -2, "$EgoSpeed")
  return []


def ks05(sb_init, ent):
  ent.add_scenario_object("ego", corolla())
  ent.add_scenario_object("stopped", car("stopped_car"))
  place(sb_init, "ego", EGO_S, -2, "$EgoSpeed")
  place(sb_init, "stopped", "$TargetS", -2, 0, "$TargetOffset")
  return []


def ks06(sb_init, ent):
  ent.add_scenario_object("ego", corolla())
  ent.add_scenario_object("truck", truck())
  place(sb_init, "ego", EGO_S, -2, "$EgoSpeed")
  place(sb_init, "truck", EGO_S, -3, "$EgoSpeed")
  return []


def ks07(sb_init, ent):
  ent.add_scenario_object("ego", corolla())
  ent.add_scenario_object("cutin", car("cut_in_car"))
  place(sb_init, "ego", EGO_S, -2, "$EgoSpeed")
  # the gap closes at $ClosingSpeed; it equals $CutInDistance (centre to centre) when the lane change starts at 2 s
  place(sb_init, "cutin", "${$CutInDistance + 2 * $ClosingSpeed + %g}" % EGO_S, -1, "${$EgoSpeed - $ClosingSpeed}")
  lc = xosc.AbsoluteLaneChangeAction(-2, xosc.TransitionDynamics(xosc.DynamicsShapes.sinusoidal,
                                                                 xosc.DynamicsDimension.time, "$LaneChangeTime"))
  return [story("cut_in", "cutin", lc, at_time(2.0))]


def ks08(sb_init, ent):
  ent.add_scenario_object("ego", corolla())
  ent.add_scenario_object("lead", car("lead_car"))
  place(sb_init, "ego", EGO_S, -2, "$EgoSpeed")
  place(sb_init, "lead", "${$EgoSpeed * $TimeGap + %g}" % EGO_S, -2, "$EgoSpeed")
  brake = xosc.AbsoluteSpeedAction(0, xosc.TransitionDynamics(xosc.DynamicsShapes.linear, xosc.DynamicsDimension.rate,
                                                              "$LeadDecel"))
  return [story("lead_brakes", "lead", brake, at_time(3.0))]


def ks09(sb_init, ent):
  ent.add_scenario_object("ego", corolla())
  ent.add_scenario_object("lead", car("lead_car"))
  ent.add_scenario_object("stopped", car("stopped_car"))
  place(sb_init, "ego", EGO_S, -2, "$EgoSpeed")
  place(sb_init, "lead", EGO_S + 25.0, -2, "$EgoSpeed")
  place(sb_init, "stopped", 400.0, -2, 0)
  trig = xosc.EntityTrigger("lead_near_stopped", 0, xosc.ConditionEdge.rising,
                            xosc.RelativeDistanceCondition("$CutOutDistance", xosc.Rule.lessThan,
                                                           xosc.RelativeDistanceType.longitudinal, "stopped"), "lead")
  lc = xosc.AbsoluteLaneChangeAction(-1, xosc.TransitionDynamics(xosc.DynamicsShapes.sinusoidal,
                                                                 xosc.DynamicsDimension.time, 2.0))
  return [story("cut_out", "lead", lc, trig)]


def ks14(sb_init, ent):
  ent.add_scenario_object("ego", corolla())
  ent.add_scenario_object("target", car("adjacent_car"))
  place(sb_init, "ego", 600.0, -2, "$EgoSpeed")
  place(sb_init, "target", "${600 - $EgoSpeed * $TargetGap}", -3, "$EgoSpeed")
  lc = xosc.AbsoluteLaneChangeAction(-3, xosc.TransitionDynamics(xosc.DynamicsShapes.sinusoidal,
                                                                 xosc.DynamicsDimension.time, 4.0))
  return [story("driver_lane_change", "ego", lc, at_time(3.0))]


def ks23(sb_init, ent):
  ent.add_scenario_object("ego", corolla())
  ent.add_scenario_object("lead", car("lead_car"))
  place(sb_init, "ego", EGO_S, -2, 0)
  place(sb_init, "lead", EGO_S + 8.0, -2, 0)
  go = xosc.AbsoluteSpeedAction(10.0, xosc.TransitionDynamics(xosc.DynamicsShapes.linear, xosc.DynamicsDimension.rate, 1.5))
  return [story("lead_leaves", "lead", go, at_time("$StandTime"))]


def ks25(sb_init, ent):
  ent.add_scenario_object("ego", corolla())
  place(sb_init, "ego", EGO_S, -2, "$StartSpeed")
  acc = xosc.AbsoluteSpeedAction("$EndSpeed", xosc.TransitionDynamics(xosc.DynamicsShapes.linear,
                                                                      xosc.DynamicsDimension.rate, 0.5))
  return [story("speed_up", "ego", acc, at_time(1.0))]


def ks27(sb_init, ent):
  ent.add_scenario_object("ego", corolla())
  ent.add_scenario_object("lead", car("lead_car"))
  place(sb_init, "ego", EGO_S, -1, "$EgoSpeed")
  place(sb_init, "lead", "$LeadS", -1, "$LeadSpeed")
  # scripted here: in a closed loop the item's longitudinal control accelerates toward the set speed
  acc = xosc.AbsoluteSpeedAction("${$EgoSpeed + $SetSpeedDelta}", xosc.TransitionDynamics(
    xosc.DynamicsShapes.linear, xosc.DynamicsDimension.rate, 1.5))
  return [story("accelerate_to_set_speed", "ego", acc, at_time(0.5))]


def kmh(v):
  return round(v / 3.6, 3)


ODD_SPEED = 110 / 3.6   # ODD-H speed bound, m/s (WP-C-02 §3, decision register DQ-260 A)
SWEEP_MAX = 120 / 3.6   # highest WP-V-03 sweep speed (KS-05 and KS-07 go to 120 km/h "by simulation only")
R01 = 300.0
# KS-27 ramp: the smallest radius of TC-35 (shortest sight distance); a 2 m wall 0.3 m inside the lane's left edge.
# The sight line from the lane centre clears the wall up to a gap of 2·sqrt(2·Rp·m) along the lane, Rp = R + w/2 and
# m = w/2 + t the clearance: about 66 m at R = 250 m, inside the 40–80 m of WP-V-03.
R27, WALL27_T = 250.0, 0.3
# 400 m and 600 m (WP-V-03 v0.9): the barrier's centreline on the lane edge, m = 1.85 m: about 77 m and 94 m.
# "reveal" is the band of the reveal gap along the lane that WP-V-03 asks for at that radius.
SCENARIOS = [
  Scenario("KS-01", "Curve at or beyond the lateral capability",
           {"straight": 200.0, "clothoid": 100.0, "radius": R01, "arc": 900.0},
           {"EgoSpeed": (round(math.sqrt(2.5 * R01), 3), [round(math.sqrt(a * R01), 3) for a in (2.0, 2.5, 3.0, 3.5)], "m/s",
                         f"speed for a required lateral acceleration of 2.0, 2.5, 3.0, 3.5 m/s² at R = {R01:g} m")},
           ks01, ["ego stays in lane -2", "steady-state lateral acceleration v²/R equals the parameter's within 5 %"], 25.0),
  Scenario("KS-05", "Stationary vehicle in lane at highway approach", {"length": 1500.0},
           {"EgoSpeed": (kmh(80), [kmh(40), kmh(60), kmh(80), kmh(120)], "m/s", "approach speed (CC 40/60/80 km/h; 120 km/h by simulation only)"),
            "TargetS": (500.0, [500.0], "m", "position of the stationary vehicle"),
            "TargetOffset": (0.0, [-0.5, 0.0, 0.5], "m", "lateral offset of the stationary vehicle in the lane")},
           ks05, ["stationary vehicle stays at speed 0 in lane -2 at its offset"], 30.0),
  Scenario("KS-06", "Narrow lane with an adjacent truck", {"length": 1500.0, "lane_width": 3.3},
           {"EgoSpeed": (kmh(100), [kmh(90), kmh(100), kmh(120)], "m/s", "ego and truck speed")},
           ks06, ["truck stays in lane -3 alongside the ego", "lane width 3.3 m"], 20.0),
  Scenario("KS-07", "Close cut-in", {"length": 1500.0},
           {"EgoSpeed": (kmh(100), [kmh(100), kmh(120)], "m/s", "ego speed"),
            "CutInDistance": (15.0, [10.0, 15.0, 20.0], "m", "centre-to-centre gap when the lane change starts"),
            "ClosingSpeed": (kmh(5), [0.0, kmh(5), kmh(10)], "m/s", "ego minus target speed (Δv −10…0 km/h)"),
            "LaneChangeTime": (2.0, [2.0], "s", "duration of the cut-in")},
           ks07, ["cut-in car is in lane -2 after the lane change", "gap at the start of the lane change equals CutInDistance within 0.5 m"], 15.0),
  Scenario("KS-08", "Lead decelerating hard", {"length": 1500.0},
           {"EgoSpeed": (kmh(80), [kmh(50), kmh(80)], "m/s", "ego and lead speed"),
            "TimeGap": (1.5, [1.5], "s", "time gap to the lead"),
            "LeadDecel": (5.0, [3.0, 5.0, 7.0], "m/s²", "lead deceleration from t = 3 s to standstill")},
           ks08, ["lead decelerates at LeadDecel within 5 % and stops in lane -2"], 15.0),
  Scenario("KS-09", "Cut-out revealing a stopped vehicle", {"length": 1500.0},
           {"EgoSpeed": (kmh(50), [kmh(50)], "m/s", "ego and lead speed"),
            "CutOutDistance": (45.0, [30.0, 45.0, 60.0], "m", "lead's distance to the stopped vehicle when it changes lane")},
           ks09, ["lead is in lane -1 after the cut-out", "stopped vehicle stays at speed 0 in lane -2"], 30.0),
  Scenario("KS-14", "Driver-initiated lane change", {"length": 1500.0},
           {"EgoSpeed": (kmh(100), [kmh(100)], "m/s", "ego and target speed"),
            "TargetGap": (2.5, [2.0, 2.5, 3.0, 20.0], "s", "time gap of the car in the target lane behind the ego (20 s: lane free)")},
           ks14, ["ego is in lane -3 after the lane change (scripted here: in a closed loop the driver's nudge starts it)"], 12.0),
  Scenario("KS-23", "Stop-and-go queue and resume", {"length": 600.0},
           {"StandTime": (5.0, [3.0, 5.0], "s", "time the lead stands before it leaves")},
           ks23, ["lead leaves at 1.5 m/s² after StandTime; ego starts at standstill"], 15.0),
  Scenario("KS-25", "Speed above the ODD bound", {"length": 2500.0},
           {"StartSpeed": (kmh(105), [kmh(105)], "m/s", "start speed, below the bound"),
            "EndSpeed": (kmh(120), [kmh(120)], "m/s", "end speed; crosses the 110 km/h ODD-H bound (DQ-260 A)")},
           ks25, ["ego speed crosses 110 km/h, the ODD-H bound"], 25.0),
  Scenario("KS-27", "Lead hidden in a ramp curve while accelerating to the set speed",
           {"straight": 100.0, "clothoid": 60.0, "radius": R27, "arc": 700.0, "lanes": 1,
            "wall": {"t": WALL27_T, "height": 2.0}, "reveal": (40.0, 80.0)},
           {"EgoSpeed": (kmh(70), [kmh(50), kmh(70), kmh(90)], "m/s", "ego speed entering the curve"),
            "SetSpeedDelta": (kmh(25), [kmh(20), kmh(25), kmh(30)], "m/s", "set speed above the ego speed"),
            "LeadSpeed": (0.0, [0.0, kmh(30)], "m/s", "lead speed: stopped or slow"),
            "LeadS": (360.0, [360.0], "m", "lead position, 200 m into the arc")},
           ks27, ["the inside wall hides the lead until the gap along the lane is 40–80 m",
                  "ego accelerates to EgoSpeed + SetSpeedDelta (scripted here: in a closed loop the item does it)",
                  "lead keeps LeadSpeed in lane -1"], 20.0,
           variants={"R400": {"radius": 400.0, "wall": {"t": 0.0, "height": 2.0}, "reveal": (40.0, 80.0)},
                     "R600": {"radius": 600.0, "wall": {"t": 0.0, "height": 2.0}, "reveal": (80.0, 100.0)}}),
]

SCENARIOS_BY_ID = {sc.id: sc for sc in SCENARIOS}

# WP-V-03 scenarios not written as files, with the reason
NOT_REPRESENTED = {
  "KS-02": "bank and crosswind: OpenSCENARIO 1.x has no wind, and esmini does not use superelevation; plant model (layer 1) later",
  "KS-03": "lane-marking visibility is a perception condition: recorded data and the closed course (M3, M8)",
  "KS-04": "lane split and merge: representable with a junction or a lane-width polynomial; deferred (SIM-OI-5)",
  "KS-10": "overpass and shadow false braking is a perception condition (M3, M9)",
  "KS-11": "radar clutter and metal plates are perception conditions (M3, M8, M9)",
  "KS-12": "sun, headlights, tunnels are perception conditions (M3, M9)",
  "KS-13": "work zones are outside the ODD; procedure check (M3, M8, M9)",
  "KS-15": "rain and wet-road reflections are perception conditions (M3, M9)",
  "KS-16": "camera obstruction and calibration are perception conditions (M3, M8)",
  "KS-17": "driver-monitoring conditions (VS-ML-06, M8)",
  "KS-18": "driver-monitoring conditions (VS-ML-06, M8)",
  "KS-19": "driver override forces: plant model fidelity level L2 (Modelica steering), then M8",
  "KS-20": "stock PCS: plant model cases P-01…P-03 for the forwarding path; the braking itself only on the car (M8)",
  "KS-21": "internal degradation: plant model fault cases (layer 1) and M1/M8",
  "KS-22": "pedestrians and cyclists at the lane edge are outside the highway-only ODD (DQ-023 answered B)",
  "KS-24": "inspection",
  "KS-26": "PCM cruise after disengagement: HIL and closed course (M1, M8)",
  "KS-28": "emergency vehicles: beacons and sirens are perception conditions and the driver's response is a closed-course trial (M8); the Blender scenes sh-14-* picture the motion",
}


def scenario_files(sc: Scenario, fid: str, road: dict) -> dict[str, str]:
  with tempfile.TemporaryDirectory() as tmp:
    xodr_path = Path(tmp) / f"{fid}.xodr"
    road_xodr(fid, road).write_xml(str(xodr_path))
    xodr_text = re.sub(r'date="[^"]*"', 'date="2026-10-16T00:00:00"', xodr_path.read_text(encoding="utf-8"))
    pd = xosc.ParameterDeclarations()
    for name, (default, *_rest) in sc.params.items():
      pd.add_parameter(xosc.Parameter(name, xosc.ParameterType.double, str(default)))
    init = xosc.Init()
    ent = xosc.Entities()
    stories = sc.build(init, ent)
    stop = xosc.ValueTrigger("end", 0, xosc.ConditionEdge.none, xosc.SimulationTimeCondition(sc.duration, xosc.Rule.greaterThan), "stop")
    sb = xosc.StoryBoard(init, stop)
    for st in stories:
      sb.add_story(st)
    title = sc.title if fid == sc.id else f"{sc.title}, R = {road['radius']:g} m"
    scen = xosc.Scenario(f"{sc.id} {title}", AUTHOR, pd, ent, sb, xosc.RoadNetwork(f"../xodr/{fid}.xodr"),
                         xosc.Catalog(), creation_date=FIXED_DATE)
    xosc_path = Path(tmp) / f"{fid}.xosc"
    scen.write_xml(str(xosc_path))
    return {f"xodr/{fid}.xodr": xodr_text, f"xosc/{fid}.xosc": xosc_path.read_text(encoding="utf-8")}


def build() -> dict[Path, str]:
  out = {}
  for sc in SCENARIOS:
    for fid, road in files_of(sc):
      for rel, text in scenario_files(sc, fid, road).items():
        out[HERE / rel] = text
  return out


def main(argv) -> int:
  files = build()
  if "--check" in argv:
    stale = [p for p, c in files.items() if not p.exists() or p.read_text(encoding="utf-8") != c]
    for p in stale:
      print(f"stale: {p.relative_to(HERE)}", file=sys.stderr)
    if stale:
      print("run: python3 assurance/sim/scenarios/generate.py", file=sys.stderr)
      return 1
    print(f"scenarios: {len(files)} file(s) current")
    return 0
  for p, c in files.items():
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(c, encoding="utf-8")
  print(f"scenarios: wrote {len(files)} file(s)")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
