"""Where the render-only extras of a scene go: building rows along an urban street, parked and passing cars,
pedestrians walking the pavements and waiting at the corners, box trailers behind the traffic trucks, and which
traffic cars are drawn with the car pack. Pure Python (no Blender), so CI checks every scene's plan (test_scenes.py);
scenery_kits.py builds it from the CC-BY model slots of library/assets.yaml.

The extras are pictures only. export_scene.py never reads them, so every pose, contact, gap and event is the same
with or without them. Nor may they change what a scene shows: like the street furniture (street_layout.py), no extra
stands near the chase camera or on its line of sight to the ego at any frame, none comes within CLEAR_ROAD_USER_M of a
scene road user at the same frame (or within street_layout.CLEAR_M of a scene pedestrian or cyclist at any frame),
and none stands across an intersection, a traffic light or a crosswalk. The scene's critical road user keeps its
Corolla, and a truck gets a trailer only where nothing follows close behind it.

Road coordinates as in export_scene.py: s along the centre line (one point a metre), d lateral (left positive)."""

from __future__ import annotations

import math
import random

import street_layout as L

CLEAR_ROAD_USER_M = 8.0       # a passing car from every scene road user, at the same frame
CLEAR_PARKED_M = 6.0          # a parked car from every pose of every scene road user
CLEAR_WALKER_M = 2.5          # a pedestrian from every scene road user, at the same frame
CLEAR_FURNITURE_M = 0.35      # a pedestrian from a piece of street furniture, beyond its radius
CAR_HALF_M = 1.0              # half the width of a car: what can hide the ego from the side
WALKER_R_M = 0.4
TRAILER_M = (4.3, 13.0)       # a trailer reaches from this far behind a truck's centre to this far
TRAILER_CLEAR_M = (3.0, 0.7)  # and no road user's centre within this of it (along, across) at any frame
CORNER_M = 2.5                # people waiting at a corner stand this far from the edge of the cross street
BUILDING_LINE_M = 1.0         # the building line beyond the outer edge of the pavement (as the procedural boxes)
DENSITY = {"dense": {"parked": 0.85, "walk_m": 6.0, "pass_m": 40.0},
           "light": {"parked": 0.45, "walk_m": 16.0, "pass_m": 90.0}}
WIDTHS = (10.0, 13.4, 20.0, 21.3, 28.4, 30.0, 49.8)   # building widths for a plan without the kits (CI)


def _rng(sc: dict, what: str) -> random.Random:
  return random.Random(f"{sc.get('variant_of') or sc['id']}:{what}")   # a variant draws its base scene's extras


def _gaps(sc: dict, pad: float = 0.0) -> list[tuple[float, float]]:
  """s ranges no extra may stand in: across intersections, traffic lights and crosswalks."""
  return [(a - pad, b + pad) for a, b in L.clear_zone(sc)["s"]]


def _in_gap(gaps, s: float, r: float = 0.0) -> bool:
  return any(a - r <= s <= b + r for a, b in gaps)


def _lines_by_frame(sc: dict, step: int = 6) -> list[tuple[int, tuple]]:
  return list(zip(range(0, len(sc["t"]), step), L.sight_lines(sc, step), strict=True))


def _hidden_by(lines_by_frame, path, r: float) -> bool:
  """True when something on path ([(x, y)] a frame) would stand near the camera or between it and the ego at any
  frame the sight lines are checked at."""
  return any(L.in_view([line], *path[min(f, len(path) - 1)], r) for f, line in lines_by_frame)


def _near_road_users(sc: dict, path, clear: float, same_frame: bool = True) -> bool:
  for a in sc["actors"]:
    poses = a["poses"]
    if same_frame:
      if any(math.hypot(x - poses[f][0], y - poses[f][1]) < clear for f, (x, y) in enumerate(path)):
        return True
    elif any(math.hypot(x - q[0], y - q[1]) < clear for q in poses for x, y in path[:1]):
      return True
  return False


def _near_vulnerable(sc: dict, path) -> bool:
  """Within street_layout.CLEAR_M of any pose of a scene pedestrian or cyclist."""
  vul = [q for a in sc["actors"] if a["kind"] in ("pedestrian", "cyclist") for q in a["poses"]]
  return any(math.hypot(x - q[0], y - q[1]) < L.CLEAR_M for x, y in path[::6] for q in vul)


def _path(sc: dict, s0: float, d: float, v: float, frames: int) -> list[tuple[float, float]]:
  centre, fps = sc["road"]["centre"], sc["fps"]
  return [L.offset(L.at(centre, s0 + v * f / fps), d) for f in range(frames)]


# ------------------------------------------------------------------------------------------------- city
def blocks(sc: dict, widths=WIDTHS) -> list[dict]:
  """Buildings shoulder to shoulder on both sides of an urban street: [{side, s, d, yaw, k, mirror}], s the middle
  of building k (an index into widths), its facade on the building line facing the carriageway. The rows break for
  the cross streets and crosswalks."""
  road, centre = sc["road"], sc["road"]["centre"]
  gaps = _gaps(sc, 3.0)
  lo, hi = centre[0][3], centre[-1][3]
  rnd = _rng(sc, "blocks")
  out = []
  for side, _, back in L.pavements(road):
    d = back + side * BUILDING_LINE_M
    s = lo
    while s < hi:
      nxt = min([a for a, b in gaps if a > s] + [hi])
      g = next(((a, b) for a, b in gaps if a <= s <= b), None)
      if g:
        s = g[1] + rnd.uniform(0.0, 0.4)
        continue
      fit = [k for k, w in enumerate(widths) if s + w <= nxt]
      if not fit:
        s = nxt + 1e-6
        continue
      k = rnd.choice(fit)
      w = widths[k]
      c = L.at(centre, s + w / 2)
      out.append({"side": side, "s": s + w / 2, "d": d, "x": L.offset(c, d)[0], "y": L.offset(c, d)[1],
                  "yaw": c[2] + (0.0 if side > 0 else math.pi), "k": k, "w": w, "mirror": rnd.random() < 0.4})
      s += w + rnd.uniform(0.0, 0.5)
  return out


def parked(sc: dict, density: str) -> list[dict]:
  """Cars parked in the parking lanes: [{s, d, x, y, yaw, pick}], nose with the traffic (one in ten the other way)."""
  road, centre = sc["road"], sc["road"]["centre"]
  zone, gaps = L.clear_zone(sc), _gaps(sc, 6.0)
  lines = _lines_by_frame(sc)
  rnd = _rng(sc, "parked")
  frames = len(sc["t"])
  out = []
  for sfc in road["surfaces"]:
    if sfc["kind"] != "parking":
      continue
    d = (sfc["d0"] + sfc["d1"]) / 2
    s = centre[0][3] + 8.0
    while s < centre[-1][3] - 8.0:
      c = L.at(centre, s)
      x, y = L.offset(c, d)
      if (rnd.random() < DENSITY[density]["parked"] and not _in_gap(gaps, s, 2.5)
          and L.is_clear(zone, centre, s, d, 2.4)
          and not _near_road_users(sc, [(x, y)], CLEAR_PARKED_M, same_frame=False)
          and not _hidden_by(lines, [(x, y)] * frames, CAR_HALF_M)):
        out.append({"s": s, "d": d, "x": x, "y": y, "yaw": c[2] + (math.pi if rnd.random() < 0.1 else 0.0),
                    "pick": rnd.random()})
      s += rnd.uniform(5.8, 7.5)
  return out


def passing(sc: dict, density: str) -> list[dict]:
  """Cars driving the oncoming lanes through the clip: [{d, path [(x, y, yaw)] a frame, pick}], each clear of every
  scene road user at every frame and never in the chase camera's view of the ego."""
  road, centre = sc["road"], sc["road"]["centre"]
  if not road.get("oncoming_left") or not road.get("lanes_left"):
    return []
  frames, fps = len(sc["t"]), sc["fps"]
  lines = _lines_by_frame(sc)
  rnd = _rng(sc, "passing")
  lo, hi = centre[0][3] + 5.0, centre[-1][3] - 5.0
  out = []
  for k in range(1, road["lanes_left"] + 1):
    d = k * road["lane_width"]
    for _ in range(int((hi - lo) / DENSITY[density]["pass_m"]) + 1):
      v = rnd.uniform(9.0, 12.0)
      span = v * frames / fps
      if hi - lo <= span:
        continue
      s0 = rnd.uniform(lo + span, hi)                       # stays on the modelled road for the whole clip
      xy = _path(sc, s0, d, -v, frames)
      if _near_road_users(sc, xy, CLEAR_ROAD_USER_M) or _hidden_by(lines, xy, CAR_HALF_M):
        continue
      if any(math.hypot(xy[0][0] - o["path"][0][0], xy[0][1] - o["path"][0][1]) < 14.0 for o in out):
        continue
      heads = [L.at(centre, s0 - v * f / fps)[2] + math.pi for f in range(frames)]
      out.append({"d": d, "path": [(x, y, h) for (x, y), h in zip(xy, heads, strict=True)], "pick": rnd.random()})
  return out


def walkers(sc: dict, density: str, furniture: list[dict] | None = None) -> list[dict]:
  """Pedestrians on the pavements: [{path [(x, y, yaw)] a frame, standing}], walking either way at 1.1 to 1.5 m/s
  or waiting at a corner of a cross street, each clear of the street furniture, of every scene road user and of the
  chase camera's view of the ego."""
  road, centre = sc["road"], sc["road"]["centre"]
  furniture = L.layout(sc) if furniture is None else furniture
  frames, fps = len(sc["t"]), sc["fps"]
  gaps = _gaps(sc)
  lines = _lines_by_frame(sc)
  rnd = _rng(sc, "walkers")
  lo, hi = centre[0][3] + 5.0, centre[-1][3] - 5.0
  out = []

  def ok(path):
    pts = [(x, y) for x, y, _ in path]
    if any(math.hypot(x - it["x"], y - it["y"]) < L.PLACE[it["kind"]][1] + CLEAR_FURNITURE_M + WALKER_R_M
           for it in furniture for x, y in pts[::3]):
      return False
    if _near_road_users(sc, pts, CLEAR_WALKER_M) or _near_vulnerable(sc, pts) or _hidden_by(lines, pts, WALKER_R_M):
      return False
    return not any(math.hypot(pts[0][0] - o["path"][0][0], pts[0][1] - o["path"][0][1]) < 1.2 for o in out)

  for side, kerb, back in L.pavements(road):
    inner, outer = kerb + side * 0.9, back - side * 0.7
    s = lo + rnd.uniform(0.0, DENSITY[density]["walk_m"])
    while s < hi:
      v = rnd.uniform(1.1, 1.5) * rnd.choice((1, -1))
      end = s + v * frames / fps
      if not _in_gap(gaps, s, 1.0) and not _in_gap(gaps, end, 1.0) and lo <= end <= hi and \
         not any(min(s, end) <= a <= max(s, end) for a, _ in gaps):
        d = rnd.uniform(min(inner, outer), max(inner, outer))
        xy = _path(sc, s, d, v, frames)
        heads = [L.at(centre, s + v * f / fps)[2] + (0.0 if v > 0 else math.pi) for f in range(frames)]
        path = [(x, y, h) for (x, y), h in zip(xy, heads, strict=True)]
        if ok(path):
          out.append({"path": path, "standing": False})
      s += rnd.uniform(0.6, 1.4) * DENSITY[density]["walk_m"]
    for p in sc.get("props", []):                  # waiting at the corners of each cross street
      if p["kind"] != "intersection" or density != "dense":
        continue
      for edge in (-1, 1):
        sc_s = p["s"] + edge * (p.get("width", 14.0) / 2 + CORNER_M)
        for _ in range(rnd.randint(2, 4)):
          s1 = sc_s + edge * rnd.uniform(0.0, 2.0)
          d = rnd.uniform(min(inner, outer), max(inner, outer))
          c = L.at(centre, s1)
          x, y = L.offset(c, d)
          yaw = c[2] + (0.0 if edge < 0 else math.pi) + rnd.uniform(-0.4, 0.4)   # facing the cross street
          path = [(x, y, yaw)] * frames
          if lo <= s1 <= hi and ok(path):
            out.append({"path": path, "standing": True})
  return out


# ------------------------------------------------------------------------------------------------- traffic
def skins(sc: dict) -> dict[str, float]:
  """{actor name: pick} of the traffic cars drawn with the car pack: every car but the ego and the critical road
  user, each scaled by skin_scale so the picture keeps the outline the analysis uses."""
  rnd = _rng(sc, "skins")
  return {a["name"]: rnd.random() for a in sc["actors"][1:]
          if a["kind"] == "car" and a["name"] != sc.get("critical") and not a.get("critical") and not a.get("beacons")
          and not a.get("body")}


def skin_scale(sc: dict, length: float) -> float:
  """The uniform scale that gives a car-pack body (length m) the length of the car the analysis draws every road
  user as (export_scene's car outline, which decides contact): a skin never reaches beyond its road user."""
  return sc["car"]["length"] / length


TRUCK_LENGTH_M = 9.5      # export_scene.SIZES: the truck outline the analysis uses


def body_scale(sc: dict, kind: str, length: float) -> float:
  """The uniform scale that gives a civil service vehicle (length m) the length of the outline the analysis draws its
  road user as (a car's or a truck's), like skin_scale."""
  return (sc["car"]["length"] if kind == "car" else TRUCK_LENGTH_M) / length


def trailers(sc: dict) -> list[str]:
  """Names of the trucks that get a box trailer: not the critical road user, and no other road user comes within
  TRAILER_CLEAR_M of where the trailer would be at any frame."""
  out = []
  for a in sc["actors"]:
    if a["kind"] != "truck" or a["name"] == sc.get("critical") or a.get("critical"):
      continue
    clear = True
    for f, (x, y, h) in enumerate(a["poses"]):
      ch, sh = math.cos(h), math.sin(h)
      for b in sc["actors"]:
        if b is a:
          continue
        bx, by, _ = b["poses"][f]
        along = (bx - x) * ch + (by - y) * sh
        lat = -(bx - x) * sh + (by - y) * ch
        if (-TRAILER_M[1] - TRAILER_CLEAR_M[0] < along < -TRAILER_M[0] + TRAILER_CLEAR_M[0]
            and abs(lat) < 1.3 + 0.9 + TRAILER_CLEAR_M[1]):          # half a trailer, half a car
          clear = False
          break
      if not clear:
        break
    if clear:
      out.append(a["name"])
  return out


def plan(sc: dict, widths=WIDTHS) -> dict:
  """Everything the scene's env asks for: city_blocks, street_life (dense or light), traffic_skins, trailers."""
  env = sc.get("env", {})
  urban = sc["road"]["type"] == "urban"
  life = env.get("street_life")
  return {"blocks": blocks(sc, widths) if env.get("city_blocks") and urban else [],
          "parked": parked(sc, life) if life and urban else [],
          "passing": passing(sc, life) if life and urban else [],
          "walkers": walkers(sc, life) if life and urban else [],
          "skins": skins(sc) if env.get("traffic_skins") else {},
          "trailers": trailers(sc) if env.get("trailers") else []}
