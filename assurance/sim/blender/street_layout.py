"""Where the street furniture of an urban scene goes: street trees in kerbside pits, lamp columns, bins, benches,
hydrants, utility boxes and bus stops on both pavements. Pure Python (no Blender), so CI checks the layout of every
urban scene (test_scenes.py); scene_assets.py builds what it lists.

Nothing goes in the clear zone: within CLEAR_M of any pose of a pedestrian or cyclist, or across an intersection, a
traffic light or a crosswalk. Furniture must not hide a road user the scene does not already hide: in
SH-11 the parked truck is the occluder, and a bench or bus shelter beside it would change what the scene shows.

Road coordinates as in export_scene.py: s along the centre line (one point a metre), d lateral (left positive). An
item's yaw is the road heading at s, turned so that the item's front (-Y in its own frame) faces the carriageway.
"""

from __future__ import annotations

import math
import random

CLEAR_M = 6.0                 # around every pedestrian or cyclist pose
CLEAR_JUNCTION_M = 6.0        # beyond each side of an intersection
CLEAR_SIGNAL_M = 3.0          # either side of a traffic light
CLEAR_CROSSWALK_M = 6.0       # either side of a crosswalk

# kind: (metres from the kerb, or from the building line if negative; clearance radius, m)
PLACE = {"lamp": (0.6, 1.0), "tree": (0.9, 2.5), "bin": (0.6, 0.5), "bench": (1.4, 1.5), "hydrant": (0.45, 0.5),
         "utility_box": (-0.45, 0.6), "shelter": (1.3, 3.0)}


def at(centre, s: float):
  return centre[min(max(int(round(s - centre[0][3])), 0), len(centre) - 1)]


def offset(c, d: float):
  return c[0] - d * math.sin(c[2]), c[1] + d * math.cos(c[2])


def nearest_s(centre, x: float, y: float) -> float:
  return min(centre, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)[3]


def clear_zone(sc: dict) -> dict:
  """{"s": [(s0, s1)], "xy": [(x, y, r)]}: where no furniture may stand."""
  zone = {"s": [], "xy": []}
  for a in sc["actors"]:
    if a["kind"] in ("pedestrian", "cyclist"):
      zone["xy"] += [(q[0], q[1], CLEAR_M) for q in a["poses"]]
  for p in sc.get("props", []):
    if p["kind"] == "intersection":
      w = p.get("width", 14.0) / 2 + CLEAR_JUNCTION_M
      zone["s"].append((p["s"] - w, p["s"] + w))
    elif p["kind"] == "traffic_light":
      zone["s"].append((p["s"] - CLEAR_SIGNAL_M, p["s"] + CLEAR_SIGNAL_M))
  for cs in sc["road"].get("crosswalks") or []:
    zone["s"].append((cs - CLEAR_CROSSWALK_M, cs + CLEAR_CROSSWALK_M))
  return zone


def is_clear(zone: dict, centre, s: float, d: float, r: float) -> bool:
  x, y = offset(at(centre, s), d)
  return (not any(a - r <= s <= b + r for a, b in zone["s"]) and
          not any(math.hypot(x - px, y - py) < pr + r for px, py, pr in zone["xy"]))


def pavements(road: dict) -> list[tuple[int, float, float]]:
  """(side, kerb d, building-side d) of each sidewalk; side +1 left, -1 right."""
  out = []
  for sfc in road["surfaces"]:
    if sfc["kind"] == "sidewalk":
      side = 1 if sfc["d0"] + sfc["d1"] > 0 else -1
      lo, hi = sorted((sfc["d0"], sfc["d1"]), key=abs)
      out.append((side, lo, hi))
  return out


def layout(sc: dict, seed: int = 21) -> list[dict]:
  """The furniture of an urban scene: [{kind, s, d, side, yaw, x, y}], every item outside clear_zone(sc).

  Lamps every 30 m and street trees every 36 m on each side, the two sides staggered; a bin by most lamps; benches,
  hydrants and utility boxes at random intervals; a bus stop on each side 45 and 95 m ahead of the ego's start (where
  the cameras see it) and every 180 m from there."""
  road, centre = sc["road"], sc["road"]["centre"]
  zone = clear_zone(sc)
  rnd = random.Random(seed)
  ego = sc["actors"][0]["poses"][0]
  s_ego = nearest_s(centre, ego[0], ego[1])
  lo, hi = centre[0][3] + 5.0, centre[-1][3] - 5.0
  items = []

  def put(kind, s, side, kerb, back, turn=0.0):
    if not lo <= s <= hi:
      return
    gap, r = PLACE[kind]
    d = kerb + side * gap if gap >= 0 else back + side * gap
    if not is_clear(zone, centre, s, d, r):
      return
    c = at(centre, s)
    x, y = offset(c, d)
    items.append({"kind": kind, "s": s, "d": d, "side": side, "x": x, "y": y,
                  "yaw": c[2] + (0.0 if side > 0 else math.pi) + turn})

  for side, kerb, back in pavements(road):
    s = lo + (0.0 if side > 0 else 15.0)
    while s <= hi:
      put("lamp", s, side, kerb, back)
      if rnd.random() < 0.6:
        put("bin", s + 2.0, side, kerb, back, rnd.uniform(0, 2 * math.pi))
      s += 30.0
    s = lo + (7.5 if side > 0 else 25.5)
    while s <= hi:
      put("tree", s, side, kerb, back, rnd.uniform(0, 2 * math.pi))
      s += 36.0
    for k in range(int((hi - lo) / 70) + 1):
      put("bench", lo + rnd.uniform(20, 60) + 70 * k, side, kerb, back)
    for k in range(int((hi - lo) / 85) + 1):
      put("hydrant", lo + rnd.uniform(0, 40) + 85 * k, side, kerb, back, rnd.uniform(0, 2 * math.pi))
    for k in range(int((hi - lo) / 95) + 1):
      put("utility_box", lo + rnd.uniform(10, 50) + 95 * k, side, kerb, back)
    first = s_ego + (45.0 if side > 0 else 95.0)
    for k in range(-3, 4):
      put("shelter", first + 180 * k, side, kerb, back)
  return items
