"""Hazardous-event scene files for Blender (assurance/sim/blender, step 1 of 3).

Builds out/<scene>/scene.json for each scene of scenes.yaml: the road as a cross-section along its centre line, the
props (overpass, intersection, cones, traffic lights), the environment, every road user's pose at the render frame
rate, the signals for the dashboard (speed, accelerations, lateral offset, gap and time to collision to the critical
road user), the events, and the HARA or SOTIF entry the scene pictures. hazard_scene.py (Blender) builds and renders
it; compose.py lays the renders out as a dashboard.

Two motion sources, named on every dashboard:
  plant      the ego (and, in longitudinal cases, the lead and follower) from a layer-1 plant run: the real panda
             safety code in the loop, under the plant's stated assumptions. A scene can vary the catalog case (speed,
             road, engagement, fault kind) and the assumptions (e.g. a driver who does not react)
  kinematic  where the plant cannot represent the situation (urban, rural, pedestrians, perception insufficiencies):
             piecewise-constant accelerations and a lateral law, with every time and acceleration written in
             scenes.yaml as a value or as a named assumption (ASSUMPTIONS below: the plant's own and WP-S-04 §3)
Road users not simulated by either are marked illustrative. Neither source models contact: at the first overlap of
two bodies the scene freezes the poses, records the relative speed and ends half a second later.

  python3 assurance/sim/blender/export_scene.py              # every scene
  python3 assurance/sim/blender/export_scene.py he-01-2-hardover-adjacent sh-06-stationary-not-lead
"""

from __future__ import annotations

import dataclasses
import json
import math
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
ASSURANCE = SIM.parent
sys.path.insert(0, str(SIM / "plant"))

import cases  # noqa: E402
import corolla  # noqa: E402
import simulate  # noqa: E402

OUT = HERE / "out"
FPS = 24
DT = 0.01                # s, kinematic integration step
END_AFTER_CONTACT = 0.5  # s shown after the first contact
DS_ROAD = 1.0            # m between exported road samples
SIZES = {"ego": (4.63, 1.781), "car": (4.63, 1.781), "truck": (9.5, 2.5), "pedestrian": (0.5, 0.5),
         "cyclist": (1.8, 0.6), "cone": (0.4, 0.4)}

# Named values a kinematic scene may use instead of a number. The plant's assumptions are read from simulate.py;
# the others are WP-S-04 §3 values (03-system/WP-S-04-timing-ftti-budget.md) or stated here with their source.
ASSUMPTIONS = {k: v[0] for k, v in simulate.ASSUMPTIONS.items()} | {
  "t_r": simulate.ASSUMPTIONS["driver_t_r_s"][0],       # driver reaction from the first cue (plant, WP-S-04 §3.2)
  "t_r_min": 0.75,          # lower end of the driver reaction range, WP-S-04 §3.2
  "a_item_max": 2.0,        # envelope acceleration bound, m/s² (WP-S-04 §3.4, SG-03)
  "a_item_min": -3.5,       # envelope deceleration bound, m/s² (WP-S-04 §3.4, SG-04)
  "a_driver_full": -6.0,    # driver adds braking to 6 m/s², WP-S-04 §3.8.2
  "a_driver": -simulate.ASSUMPTIONS["driver_brake"][0],  # braking driver of the plant, -3 m/s²
  "a_pcs": -simulate.ASSUMPTIONS["a_pcs"][0],           # stock PCS, A-PCS-1 of WP-S-04 §3.6
  "a_cruise": 1.0,          # PCM cruise resuming to its set speed, m/s² (no source; the plant's longitudinal cue)
  "ay_driver": simulate.ASSUMPTIONS["driver_ay_max"][0],  # driver's correction limit, m/s²
  "wn_driver": 1.5,         # driver's lateral loop, rad/s (plant driver_ay_max text)
  "ay_lka": 1.99,           # lateral acceleration of the full envelope torque, m/s² (WP-S-04 §3.8.1)
  "t_never": 1.0e3,         # a driver who does not react within the scene
}


def value(x, extra: dict | None = None) -> float:
  """A number, or an expression over the named assumptions (e.g. "t_r + 0.3", "-a_item_max")."""
  if isinstance(x, (int, float)):
    return float(x)
  return float(eval(str(x), {"__builtins__": {}, "math": math}, ASSUMPTIONS | (extra or {})))


def load_scenes() -> list[dict]:
  return yaml.safe_load((HERE / "scenes.yaml").read_text())["scenes"]


def hazardous_events() -> dict[str, dict]:
  items = yaml.safe_load((ASSURANCE / "trace" / "items" / "hazards.yaml").read_text())
  return {h["id"]: h for h in items}


# ------------------------------------------------------------------------------------------------- road
def _interp(ts: list[float], vs: list[float], t: float) -> float:
  if t <= ts[0]:
    return vs[0]
  if t >= ts[-1]:
    return vs[-1]
  i = min(int((t - ts[0]) / (ts[1] - ts[0])), len(ts) - 2)
  f = (t - ts[i]) / (ts[i + 1] - ts[i])
  return vs[i] + f * (vs[i + 1] - vs[i])


def road_pose(road, s: float, d: float) -> tuple[float, float, float]:
  """World x, y and heading of the point d metres left of the reference line at arc length s."""
  j = min(max(int(s / road.ds), 0), len(road.s) - 2)
  f = (s - road.s[j]) / road.ds
  x = road.x[j] + f * (road.x[j + 1] - road.x[j])
  y = road.y[j] + f * (road.y[j + 1] - road.y[j])
  h = road.h[j] + f * (road.h[j + 1] - road.h[j])
  return x - d * math.sin(h), y + d * math.cos(h), h


def road_layout(spec: dict, lw: float) -> dict:
  """The cross-section: surfaces (d0 > d1, left positive), markings, outer edges, as the road type asks.
  The reference line is the ego lane's centre."""
  kind = spec.get("type", "highway")
  nl, nr = spec.get("lanes_left", 1), spec.get("lanes_right", 1)
  left, right = lw / 2 + nl * lw, -lw / 2 - nr * lw
  surf, marks = [], []
  worn = spec.get("worn_markings", False)
  barrier = None
  if kind == "highway":
    sh = spec.get("shoulder_m", 3.0)
    surf += [{"kind": "asphalt", "d0": left + 0.75, "d1": right}, {"kind": "shoulder", "d0": right, "d1": right - sh}]
    marks += [{"d": left - 0.175, "style": "solid", "colour": "white", "worn": worn},
              {"d": right + 0.175, "style": "solid", "colour": "white", "worn": worn}]
    for k in range(1, nl + nr + 1):
      marks.append({"d": left - k * lw, "style": "dashed", "colour": "white", "worn": worn})
    outer_l, outer_r = left + 0.75, right - sh
    if spec.get("barrier", True):
      barrier = right - sh
      outer_r = barrier - 0.4
    surf += [{"kind": "grass", "d0": outer_l + 400, "d1": outer_l, "z": -0.03},
             {"kind": "grass", "d0": outer_r, "d1": outer_r - 400, "z": -0.03}]
    scenery = spec.get("scenery", "trees")
  elif kind == "rural":
    sh = spec.get("shoulder_m", 1.0)
    surf += [{"kind": "asphalt", "d0": left, "d1": right}, {"kind": "gravel", "d0": left + sh, "d1": left},
             {"kind": "gravel", "d0": right, "d1": right - sh}]
    marks += [{"d": left - 0.15, "style": "solid", "colour": "white", "worn": worn},
              {"d": right + 0.15, "style": "solid", "colour": "white", "worn": worn},
              {"d": lw / 2 + 0.1, "style": spec.get("centre", "solid"), "colour": "yellow", "width": 0.12},
              {"d": lw / 2 - 0.1, "style": spec.get("centre", "solid"), "colour": "yellow", "width": 0.12}]
    for k in range(1, nl):
      marks.append({"d": lw / 2 + k * lw, "style": "dashed", "colour": "white"})
    for k in range(1, nr + 1):
      marks.append({"d": -lw / 2 - (k - 1) * lw, "style": "dashed", "colour": "white"})
    outer_l, outer_r = left + sh, right - sh
    surf += [{"kind": "grass", "d0": outer_l + 400, "d1": outer_l, "z": -0.05},
             {"kind": "grass", "d0": outer_r, "d1": outer_r - 400, "z": -0.05}]
    scenery = spec.get("scenery", "trees")
  elif kind == "urban":
    park = spec.get("parking_m", 2.4)
    walk = spec.get("sidewalk_m", 3.5)
    right_c = right - park
    surf += [{"kind": "asphalt", "d0": left, "d1": right}, {"kind": "parking", "d0": right, "d1": right_c}]
    marks += [{"d": lw / 2 + 0.1, "style": "solid", "colour": "yellow", "width": 0.12},
              {"d": lw / 2 - 0.1, "style": "solid", "colour": "yellow", "width": 0.12},
              {"d": right, "style": "solid", "colour": "white", "worn": worn}]
    for k in range(1, nl):
      marks.append({"d": lw / 2 + k * lw, "style": "dashed", "colour": "white", "worn": worn})
    for k in range(1, nr + 1):
      marks.append({"d": -lw / 2 - (k - 1) * lw, "style": "dashed", "colour": "white", "worn": worn})
    surf += [{"kind": "sidewalk", "d0": left + walk, "d1": left, "z": 0.15},
             {"kind": "sidewalk", "d0": right_c, "d1": right_c - walk, "z": 0.15}]
    outer_l, outer_r = left + walk, right_c - walk
    right = right_c
    scenery = "urban"
  else:
    raise SystemExit(f"road type {kind} not known")
  for g in spec.get("ghost_lines", []):          # tar seams or old markings the camera may follow (TC-05)
    marks.append({"d": g["d"], "style": "solid", "colour": "white", "worn": True, "width": 0.25, "from": g.get("from"),
                  "to_d": g.get("to_d"), "len": g.get("len")})
  return {"type": kind, "lane_width": lw, "lanes_left": nl, "lanes_right": nr, "left_edge": left,
          "right_edge": right, "barrier": barrier, "surfaces": surf, "markings": marks, "outer": [outer_l, outer_r],
          "carriageway": [left, right], "scenery": scenery, "shoulder_m": spec.get("shoulder_m", 0.0),
          "oncoming_left": kind in ("rural", "urban")}


# ------------------------------------------------------------------------------------------------- kinematics
def kinematic_track(spec: dict, times: list[float], s0: float, d0: float) -> tuple[list, list, list]:
  """s(t), d(t) and speed for a road user moving along the road: piecewise accelerations (optionally toward a target
  speed) and a lateral law per segment: hold (no lateral motion), drift (constant lateral acceleration; ay 0 keeps the
  lateral speed: steering lost), track (critically damped toward a lateral target, limited acceleration), walk
  (constant lateral speed to a target). Times are relative to the trigger (t = 0)."""
  v = value(spec.get("speed_kph", 0.0)) / 3.6
  accel = sorted([{**a, "t": value(a["t"])} for a in spec.get("accel", [])], key=lambda a: a["t"])
  lat = sorted([{**a, "t": value(a["t"])} for a in spec.get("lateral", [])], key=lambda a: a["t"])
  forward = v >= 0
  s, d, vd = s0, d0, 0.0
  out_s, out_d, out_v = [], [], []
  t = times[0]
  k = 0
  stop = spec.get("stop_at_s")
  while k < len(times):
    if t >= times[k] - 1e-9:
      out_s.append(s)
      out_d.append(d)
      out_v.append(v)
      k += 1
      continue
    a, target = 0.0, None
    for seg in accel:
      if seg["t"] <= t:
        a, target = value(seg["a"]), (value(seg["v_to_kph"]) / 3.6 if "v_to_kph" in seg else None)
    if target is not None and ((a > 0 and v >= target) or (a < 0 and v <= target)):
      a = 0.0
    law = {"law": "hold"}
    for seg in lat:
      if seg["t"] <= t:
        law = seg
    if law["law"] == "hold":
      ad = -vd / 0.15
    elif law["law"] == "drift":
      ad = value(law.get("ay", 0.0))
    elif law["law"] == "track":
      wn = value(law.get("wn", "wn_driver"))
      ad = wn * wn * (value(law["to"]) - d) - 2 * wn * vd
      lim = value(law.get("ay_max", "ay_driver"))
      ad = max(-lim, min(lim, ad))
    elif law["law"] == "walk":
      vt = value(law["v"])
      to = value(law["to"])
      vd = 0.0 if abs(to - d) < vt * DT else math.copysign(vt, to - d)
      ad = 0.0
    else:
      raise ValueError(law["law"])
    v_new = v + a * DT
    if forward and v_new < 0 or not forward and v_new > 0:   # braking stops a road user; it does not reverse it
      v_new = 0.0
    s += 0.5 * (v + v_new) * DT
    v = v_new
    if stop is not None and s >= value(stop):
      s, v = value(stop), 0.0
    vd += ad * DT
    d += vd * DT
    t += DT
  return out_s, out_d, out_v


def poses_from_track(road, ss, ds, yaw_mode: str = "path", sign: float = 1.0) -> list[list[float]]:
  poses = []
  n = len(ss)
  for i in range(n):
    x, y, h = road_pose(road, ss[i], ds[i])
    a, b = max(i - 1, 0), min(i + 1, n - 1)
    dsv, ddv = ss[b] - ss[a], ds[b] - ds[a]
    if yaw_mode == "path" and abs(dsv) + abs(ddv) > 1e-4:
      yaw = h + math.atan2(ddv, dsv)
    elif yaw_mode == "path" and poses:
      yaw = poses[-1][2]
    elif yaw_mode == "walk" and abs(ddv) > 1e-4:
      yaw = h + math.copysign(math.pi / 2, ddv)
    elif yaw_mode == "walk" and poses:
      yaw = poses[-1][2]
    else:
      yaw = h + (0.0 if sign >= 0 else math.pi)
    poses.append([x, y, yaw])
  return poses


# ------------------------------------------------------------------------------------------------- geometry
def _box(x: float, y: float, yaw: float, length: float, width: float) -> list[tuple[float, float]]:
  c, s = math.cos(yaw), math.sin(yaw)
  return [(x + c * a - s * b, y + s * a + c * b) for a, b in
          ((length / 2, width / 2), (-length / 2, width / 2), (-length / 2, -width / 2), (length / 2, -width / 2))]


def _overlap(p: list, q: list) -> bool:
  """Separating-axis test of two convex quadrilaterals."""
  for poly in (p, q):
    for i in range(4):
      (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % 4]
      nx, ny = y0 - y1, x1 - x0
      a = [nx * x + ny * y for x, y in p]
      b = [nx * x + ny * y for x, y in q]
      if max(a) < min(b) or max(b) < min(a):
        return False
  return True


def _gap(p, q, sp, sq) -> float:
  """Clearance between two bodies: the least distance between their outlines (0 when they overlap)."""
  a, b = _box(*p, *sp), _box(*q, *sq)
  if _overlap(a, b):
    return 0.0
  def seg(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    u = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - x0 - u * dx, py - y0 - u * dy)
  return min(seg(*pt, *poly[i], *poly[(i + 1) % 4]) for poly, other in ((a, b), (b, a)) for pt in other
             for i in range(4))


# ------------------------------------------------------------------------------------------------- scene
def card(scene: dict, hes: dict) -> dict:
  if "he" in scene:
    he = hes.get(scene["he"])
    if he is None or he["kind"] != "hazardous-event":
      raise SystemExit(f"{scene['id']}: {scene['he']} is not a hazardous event in trace/items/hazards.yaml")
    hz = hes[he["parents"][0]]
    return {"kind": "HARA", "id": he["id"], "badge": f"{he['id']}  ASIL {he['asil']}",
            "title": f"{hz['id']}: {hz['title']}", "situation": he["situation"], "effect": he["effect"],
            "rows": [["Severity", f"S{he['s']}"], ["Exposure", f"E{he['e']}"], ["Controllability", f"C{he['c']}"],
                     ["ASIL", he["asil"]]],
            "note": "Ratings are WP-C-03 proposals, not approved",
            "tc": scene.get("tc", []), "ks": scene.get("ks", [])}
  sh = scene["sotif"]
  return {"kind": "SOTIF", "id": sh["id"], "badge": f"{sh['id']}  SOTIF  S{sh['s']} C{sh['c']}",
          "title": sh["title"], "situation": sh["situation"], "effect": sh["effect"],
          "rows": [["Severity", f"S{sh['s']}"], ["Controllability", f"C{sh['c']}"],
                   ["Triggering condition", ", ".join(scene.get("tc", [])) or "—"],
                   ["Known scenario", ", ".join(scene.get("ks", [])) or "—"]],
          "note": "WP-C-05 rates S and C only; triggering conditions WP-C-06, scenarios WP-V-03",
          "tc": scene.get("tc", []), "ks": scene.get("ks", [])}


def plant_case(scene: dict):
  base = {c.id: c for c in cases.all_cases()}.get(scene["case"])
  if base is None:
    raise SystemExit(f"{scene['id']}: plant case {scene['case']} not found (plant/cases.py)")
  ov = scene.get("case_overrides", {})
  case = dataclasses.replace(base, **ov) if ov else base
  if ov:
    case = dataclasses.replace(case, id=f"{base.id}*")
  return base, case


def build(scene: dict, hes: dict[str, dict]) -> dict:
  info = card(scene, hes)
  width = corolla.as_dict()["width"]
  SIZES["ego"] = SIZES["car"] = (SIZES["car"][0], width)
  rd = scene["road"]
  motion = scene.get("motion", "plant")
  win = [value(w) for w in scene["window"]]
  events = []
  signals = {}

  if motion == "plant":
    base, case = plant_case(scene)
    res = simulate.simulate(case, scene.get("assumptions"))
    v0 = case.speed_kph / 3.6
    road = simulate.make_road(case.road, v0, case.lane_width)
    lw = road.lane_width
    t_fault = res.t0
    t_start = max(res.t[0], t_fault + win[0])
    t_end = min(res.t[-1], t_fault + win[1])
    n = int(round((t_end - t_start) * FPS)) + 1
    times = [t_start + i / FPS for i in range(n)]
    rel = [t - t_fault for t in times]
    ex = [_interp(res.t, res.x, t) for t in times]
    ey = [_interp(res.t, res.y, t) for t in times]
    es = [_interp(res.t, res.s, t) for t in times]
    lat = [_interp(res.t, res.e_y, t) for t in times]
    signals["ax"] = [_interp(res.t, res.ax, t) for t in times]
    signals["ay"] = [_interp(res.t, res.ay, t) for t in times]
    signals["eps_torque"] = [_interp(res.t, res.torque, t) for t in times]
    eyaw = []
    for i in range(n):
      a, b = max(i - 1, 0), min(i + 1, n - 1)
      eyaw.append(math.atan2(ey[b] - ey[a], ex[b] - ex[a]))
    ego = {"name": "ego", "kind": "ego", "source": "plant", "poses": [[x, y, h] for x, y, h in zip(ex, ey, eyaw)]}
    speed = [math.hypot(ex[min(i + 1, n - 1)] - ex[max(i - 1, 0)], ey[min(i + 1, n - 1)] - ey[max(i - 1, 0)])
             / ((min(i + 1, n - 1) - max(i - 1, 0)) / FPS) for i in range(n)]
    actors = [ego]
    if case.longitudinal and not scene.get("hide_plant_traffic"):
      gl = [_interp(res.t, [g[0] for g in res.gap], t) for t in times]
      gf = [_interp(res.t, [g[1] for g in res.gap], t) for t in times]
      for name, sgn, g in (("lead", 1, gl), ("follower", -1, gf)):
        ss = [s + sgn * (gg + SIZES["car"][0]) for s, gg in zip(es, g)]
        actors.append({"name": name, "kind": "car", "source": "plant",
                       "poses": poses_from_track(road, ss, [0.0] * n)})
    events += [{"t": t - t_fault, "label": k} for k, t in res.events.items()]
    s_ego0 = _interp(rel, es, 0.0) if rel[0] <= 0 <= rel[-1] else es[0]
    thr = res.metrics["lane_threshold"]
    prov = (f"Layer-1 plant model, case {case.id}" + (f" (catalog {base.id} with {scene['case_overrides']})"
            if case.id != base.id else "") + (f", assumptions {scene['assumptions']}" if scene.get("assumptions")
            else "") + "; real panda safety code in the loop; synthetic (DSR-12), no evidence credit")
    geom = road.name.replace("straight highway", "straight")
    case_info = {"id": case.id, "title": scene.get("case_title", case.title), "sg": case.sg,
                 "speed_kph": case.speed_kph, "road": f"{rd.get('type', 'highway')}, {geom}", "eps": case.eps}
  else:
    eg = scene["ego"]
    v0 = value(eg["speed_kph"]) / 3.6
    lw = rd.get("lane_width", 3.7)
    road = simulate.make_road(rd.get("geometry", "straight"), max(v0, 8.0), lw)
    n = int(round((win[1] - win[0]) * FPS)) + 1
    rel = [win[0] + i / FPS for i in range(n)]
    s_ego0 = 250.0
    times = [win[0] + i * DT for i in range(int(round((win[1] - win[0]) / DT)) + 1)]
    es_f, ed_f, ev_f = kinematic_track(eg, times, s_ego0 + v0 * win[0], value(eg.get("d", 0.0)))
    es = [_interp(times, es_f, t) for t in rel]
    lat = [_interp(times, ed_f, t) for t in rel]
    speed = [_interp(times, ev_f, t) for t in rel]
    ego = {"name": "ego", "kind": "ego", "source": "kinematic", "poses": poses_from_track(road, es, lat)}
    actors = [ego]
    # accelerations from the motion: longitudinal from the speed, lateral from the path curvature
    signals["ax"] = [(speed[min(i + 1, n - 1)] - speed[max(i - 1, 0)]) / ((min(i + 1, n - 1) - max(i - 1, 0)) / FPS)
                     for i in range(n)]
    yaws = [p[2] for p in ego["poses"]]
    signals["ay"] = []
    for i in range(n):
      a, b = max(i - 1, 0), min(i + 1, n - 1)
      dy = math.atan2(math.sin(yaws[b] - yaws[a]), math.cos(yaws[b] - yaws[a]))
      signals["ay"].append(speed[i] * dy / ((b - a) / FPS))
    signals["eps_torque"] = None
    thr = (lw - width) / 2
    prov = ("Kinematic illustration: accelerations and times from the plant's driver assumptions and WP-S-04 §3 "
            "(scenes.yaml); not a plant run; synthetic (DSR-12), no evidence credit")
    case_info = {"id": "kinematic", "title": scene.get("case_title", ""), "sg": scene.get("sg", "—"),
                 "speed_kph": v0 * 3.6, "road": f"{rd.get('type', 'highway')}, {road.name.replace('straight highway', 'straight')}",
                 "eps": "—"}
  for e in scene.get("events", []):
    events.append({"t": value(e["t"]), "label": e["label"]})

  # other road users from the scene (kinematic or illustrative), relative to the ego at t = 0
  times = [rel[0] + i * DT for i in range(int(round((rel[-1] - rel[0]) / DT)) + 1)]
  for a in scene.get("actors", []):
    kind = a["kind"]
    d0 = value(a.get("d", value(a.get("lane", 0)) * lw))
    v = value(a.get("speed_kph", 0.0)) / 3.6
    s0 = s_ego0 + value(a.get("ds_m", 0.0)) + v * rel[0]
    ss, dd, _ = kinematic_track(a, times, s0, d0)
    ss = [_interp(times, ss, t) for t in rel]
    dd = [_interp(times, dd, t) for t in rel]
    mode = "walk" if kind == "pedestrian" else ("fixed" if v == 0 and not a.get("lateral") and not a.get("accel")
                                                else "path")
    if kind != "pedestrian" and a.get("lateral") and all(l["law"] == "walk" for l in a["lateral"]) and v == 0:
      mode = "walk"                              # crossing traffic moves across the road
    poses = poses_from_track(road, ss, dd, mode, -1 if v < 0 else 1)
    if a.get("yaw_deg") is not None:
      poses = [[x, y, h + math.radians(a["yaw_deg"])] for x, y, h in poses]
    actors.append({"name": a["name"], "kind": kind, "source": a.get("source", "kinematic"), "poses": poses,
                   "paint": a.get("paint"), "critical": bool(a.get("critical"))})

  # props in road coordinates (s relative to the ego at t = 0)
  props = []
  for p in scene.get("props", []):
    q = dict(p)
    if "ds_m" in q:
      q["s"] = s_ego0 + value(q.pop("ds_m"))
    if q["kind"] == "cones":
      q["points"] = [[s_ego0 + value(c[0]), value(c[1])] for c in q["points"]]
    props.append(q)

  # contact: ego against every other body and the barrier; the scene freezes there
  sizes = {i: SIZES.get(a["kind"], SIZES["car"]) for i, a in enumerate(actors)}
  layout = road_layout(rd, lw)
  barrier = layout["barrier"]
  cone_pts = [pt for p in props if p["kind"] == "cones" for pt in p["points"]]
  contact = None
  for i in range(n):
    ep = actors[0]["poses"][i]
    eb = _box(*ep, *sizes[0])
    for j, a in enumerate(actors[1:], start=1):
      if _overlap(eb, _box(*a["poses"][i], *sizes[j])):
        vrel = 0.0
        if i:
          pe, pa = actors[0]["poses"], a["poses"]
          vx = (pe[i][0] - pe[i - 1][0]) - (pa[i][0] - pa[i - 1][0])
          vy = (pe[i][1] - pe[i - 1][1]) - (pa[i][1] - pa[i - 1][1])
          vrel = math.hypot(vx, vy) * FPS * 3.6
        who = a["name"]
        contact = (i, f"contact with the {who} at {vrel:.0f} km/h relative (not modelled)", vrel, who)
        break
    if contact is None and barrier is not None:
      hr = road_pose(road, es[i], 0.0)[2]
      relyaw = ep[2] - hr
      corners = [lat[i] + math.sin(relyaw) * a + math.cos(relyaw) * b
                 for a in (sizes[0][0] / 2, -sizes[0][0] / 2) for b in (sizes[0][1] / 2, -sizes[0][1] / 2)]
      if min(corners) < barrier:
        contact = (i, f"body reaches the barrier at {speed[i] * 3.6:.0f} km/h (not modelled)", speed[i] * 3.6, "barrier")
    if contact is None and cone_pts:
      for s_c, d_c in cone_pts:
        if abs(es[i] - s_c) < sizes[0][0] / 2 + 0.2 and abs(lat[i] - d_c) < sizes[0][1] / 2 + 0.2:
          contact = (i, f"strikes the cones at {speed[i] * 3.6:.0f} km/h", speed[i] * 3.6, "cones")
          break
    if contact:
      break
  if contact:
    i_c = contact[0]
    events.append({"t": rel[i_c], "label": contact[1]})
    cut = min(n, i_c + int(END_AFTER_CONTACT * FPS) + 1)
    for a in actors:
      a["poses"] = a["poses"][:i_c + 1] + [a["poses"][i_c]] * (cut - i_c - 1)
    rel, speed, lat, es = rel[:cut], speed[:i_c + 1] + [0.0] * (cut - i_c - 1), lat[:i_c + 1] + [lat[i_c]] * (cut - i_c - 1), es[:cut]
    for k, v in signals.items():
      if v is not None:
        signals[k] = v[:i_c + 1] + [0.0] * (cut - i_c - 1)
    n = cut

  # body at the lane line, from the lateral offset (both sources)
  for i in range(1, n):
    if abs(lat[i]) >= thr > abs(lat[i - 1]) and rel[i] >= 0 and not scene.get("lane_change"):
      events.append({"t": rel[i], "label": "body reaches the lane line"})
      break

  # gap and time to collision to the critical road user (named in the scene, else the plant's lead, else none)
  crit = next((j for j, a in enumerate(actors) if a.get("critical")), None)
  if crit is None:
    crit = next((j for j, a in enumerate(actors) if a["name"] == scene.get("critical")), None)
  gap = ttc = None
  if crit is not None:
    gap, ttc = [], []
    for i in range(n):
      g = _gap(actors[0]["poses"][i], actors[crit]["poses"][i], sizes[0], sizes[crit])
      gap.append(max(g, 0.0))
    for i in range(n):
      a, b = max(i - 1, 0), min(i + 1, n - 1)
      closing = -(gap[b] - gap[a]) / ((b - a) / FPS) if b > a else 0.0
      ep, cp = actors[0]["poses"][i], actors[crit]["poses"][i]
      rel_lat = -(cp[0] - ep[0]) * math.sin(ep[2]) + (cp[1] - ep[1]) * math.cos(ep[2])
      in_path = abs(rel_lat) < (sizes[0][1] + sizes[crit][1]) / 2      # TTC only for a road user in the ego's path
      ttc.append(min(gap[i] / closing, 99.0) if in_path and closing > 0.1 and gap[i] > 0 else 99.0)

  trig = scene.get("trigger_label", "fault")
  if not any(e["label"] == "fault" for e in events) and rel[0] <= 0.0:
    events.append({"t": 0.0, "label": "fault"})
  events = sorted(({"t": e["t"], "label": trig if e["label"] == "fault" else e["label"]} for e in events
                   if rel[0] - 1e-6 <= e["t"] <= rel[-1] + 1e-6), key=lambda e: e["t"])

  # road samples around the scene
  s_lo = min(es) - 120.0
  s_hi = max(es) + 250.0
  centre = []
  s = max(0.0, s_lo)
  while s <= min(s_hi, road.s[-1]):
    centre.append(list(road_pose(road, s, 0.0)) + [s])
    s += DS_ROAD
  layout["centre"] = centre

  return {
    "schema_version": 2,
    "id": scene["id"],
    "caption": " ".join(scene["caption"].split()),
    "card": info,
    "case": case_info,
    "motion": motion,
    "provenance": prov,
    "trigger": trig,
    "fps": FPS,
    "t": rel,
    "speed": speed,
    "lateral": lat,
    "lane_threshold": thr,
    "ax": signals["ax"],
    "ay": signals["ay"],
    "eps_torque": signals["eps_torque"],
    "critical": actors[crit]["name"] if crit is not None else None,
    "gap": gap,
    "ttc": ttc,
    "contact": {"t": rel[contact[0]], "who": contact[3], "rel_kph": contact[2]} if contact else None,
    "car": {"length": SIZES["car"][0], "width": width},
    "road": layout,
    "env": scene.get("env", {}),
    "props": props,
    "actors": actors,
    "events": events,
  }


def main(argv: list[str]) -> int:
  hes = hazardous_events()
  scenes = load_scenes()
  want = set(argv)
  unknown = want - {s["id"] for s in scenes}
  if unknown:
    print(f"unknown scene(s): {', '.join(sorted(unknown))}", file=sys.stderr)
    return 2
  for sc in scenes:
    if want and sc["id"] not in want:
      continue
    data = build(sc, hes)
    out = OUT / sc["id"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "scene.json").write_text(json.dumps(data, indent=1))
    c = data["contact"]
    print(f"{sc['id']}: {len(data['t'])} frames, {len(data['events'])} events"
          + (f", contact {c['who']} at {c['t']:+.2f} s, {c['rel_kph']:.0f} km/h" if c else ""))
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
