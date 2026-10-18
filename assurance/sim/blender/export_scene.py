"""Hazardous-event scene files for Blender (assurance/sim/blender, step 1 of 3).

Runs the layer-1 plant case named by each scene in scenes.yaml and writes out/<scene>/scene.json: the road, the ego
pose at the render frame rate, the other road users, the panda and driver events, and the HARA text of the hazardous
event. hazard_scene.py (Blender) builds and renders the scene from that file; compose.py adds the HUD and storyboard.

The ego motion, the events and, in longitudinal cases, the lead and follower are the plant's output; actors marked
`illustrative` are drawn at constant speed in a lane and are not simulated. The plant does not model contact: a scene
with illustrative actors ends shortly after the first overlap of the body boxes, which is marked as such.

  python3 assurance/sim/blender/export_scene.py              # every scene
  python3 assurance/sim/blender/export_scene.py he-01-2-hardover-adjacent
"""

from __future__ import annotations

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
LENGTH = 4.63          # m, body length of the reference car (figures/corolla-e210-silhouette.json extent)
END_AFTER_CONTACT = 0.4  # s shown after the first contact with an illustrative actor
DS_ROAD = 1.0          # m between exported road samples


def load_scenes() -> list[dict]:
  return yaml.safe_load((HERE / "scenes.yaml").read_text())["scenes"]


def hazardous_events() -> dict[str, dict]:
  items = yaml.safe_load((ASSURANCE / "trace" / "items" / "hazards.yaml").read_text())
  return {h["id"]: h for h in items}


def _interp(ts: list[float], vs: list[float], t: float) -> float:
  if t <= ts[0]:
    return vs[0]
  if t >= ts[-1]:
    return vs[-1]
  i = min(int((t - ts[0]) / (ts[1] - ts[0])), len(ts) - 2)
  f = (t - ts[i]) / (ts[i + 1] - ts[i])
  return vs[i] + f * (vs[i + 1] - vs[i])


def _road_pose(road, s: float, d: float) -> tuple[float, float, float]:
  """World x, y and heading of the point d metres left of the reference line at arc length s."""
  j = min(max(int(s / road.ds), 0), len(road.s) - 2)
  f = (s - road.s[j]) / road.ds
  x = road.x[j] + f * (road.x[j + 1] - road.x[j])
  y = road.y[j] + f * (road.y[j + 1] - road.y[j])
  h = road.h[j] + f * (road.h[j + 1] - road.h[j])
  return x - d * math.sin(h), y + d * math.cos(h), h


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


def build(scene: dict, hes: dict[str, dict]) -> dict:
  he = hes.get(scene["he"])
  if he is None or he["kind"] != "hazardous-event":
    raise SystemExit(f"{scene['id']}: {scene['he']} is not a hazardous event in trace/items/hazards.yaml")
  case = {c.id: c for c in cases.all_cases()}.get(scene["case"])
  if case is None:
    raise SystemExit(f"{scene['id']}: plant case {scene['case']} not found (plant/cases.py)")
  hazard = hes[he["parents"][0]]

  res = simulate.simulate(case)
  width = corolla.as_dict()["width"]
  v0 = case.speed_kph / 3.6
  road = simulate.make_road(case.road, v0, case.lane_width)
  lw = road.lane_width
  t_fault = res.t0
  t_start = max(res.t[0], t_fault + scene["window"][0])
  t_end = min(res.t[-1], t_fault + scene["window"][1])

  # ego, at the render frame rate; heading from the path (the slip angle of the single-track model is not drawn)
  n = int(round((t_end - t_start) * FPS)) + 1
  times = [t_start + i / FPS for i in range(n)]
  ex = [_interp(res.t, res.x, t) for t in times]
  ey = [_interp(res.t, res.y, t) for t in times]
  es = [_interp(res.t, res.s, t) for t in times]
  e_lat = [_interp(res.t, res.e_y, t) for t in times]
  ax = [_interp(res.t, res.ax, t) for t in times]
  ay = [_interp(res.t, res.ay, t) for t in times]
  torque = [_interp(res.t, res.torque, t) for t in times]
  gap_lead = [_interp(res.t, [g[0] for g in res.gap], t) for t in times]
  gap_follow = [_interp(res.t, [g[1] for g in res.gap], t) for t in times]
  eyaw = []
  for i in range(n):
    a, b = max(i - 1, 0), min(i + 1, n - 1)
    eyaw.append(math.atan2(ey[b] - ey[a], ex[b] - ex[a]))
  speed = [math.hypot(ex[min(i + 1, n - 1)] - ex[max(i - 1, 0)], ey[min(i + 1, n - 1)] - ey[max(i - 1, 0)])
           / ((min(i + 1, n - 1) - max(i - 1, 0)) / FPS) for i in range(n)]

  actors = [{"name": "ego", "kind": "ego", "source": "plant", "poses": [[x, y, h] for x, y, h in zip(ex, ey, eyaw)]}]
  if case.longitudinal:
    for name, sign, gaps in (("lead", 1, gap_lead), ("follower", -1, gap_follow)):
      poses = [list(_road_pose(road, s + sign * (g + LENGTH), 0.0)) for s, g in zip(es, gaps)]
      actors.append({"name": name, "kind": "car", "source": "plant", "poses": poses})
  s_ego0 = es[0]
  for a in scene.get("actors", []):
    v = a["speed_kph"] / 3.6
    poses = [list(_road_pose(road, s_ego0 + a["ds_m"] + v * (t - t_start), a["lane"] * lw)) for t in times]
    actors.append({"name": a["name"], "kind": a["kind"], "source": a["source"], "poses": poses})

  # road layout across the reference line (the ego lane centre); d is positive to the left
  rd = scene["road"]
  left_edge = lw / 2 + rd["lanes_left"] * lw
  right_edge = -lw / 2 - rd["lanes_right"] * lw
  barrier = right_edge - rd["shoulder_m"] if rd.get("barrier") else None

  # contact: an illustrative actor's body box, or the barrier line; the plant models neither
  events = [{"t": t - t_fault, "label": k} for k, t in sorted(res.events.items(), key=lambda kv: kv[1])]
  if res.metrics.get("t_line") is not None:
    events.append({"t": res.metrics["t_line"], "label": "body reaches the lane line"})
  contact = None
  for i, t in enumerate(times):
    ego_box = _box(ex[i], ey[i], eyaw[i], LENGTH, width)
    for a in actors[1:]:
      if a["source"] == "illustrative":
        x, y, h = a["poses"][i]
        if _overlap(ego_box, _box(x, y, h, LENGTH, width)):
          contact = (t, f"contact with the {a['name']} (not modelled)")
          break
    if contact is None and barrier is not None:
      rel = eyaw[i] - _road_pose(road, es[i], 0.0)[2]
      corners = [e_lat[i] + math.sin(rel) * a + math.cos(rel) * b
                 for a in (LENGTH / 2, -LENGTH / 2) for b in (width / 2, -width / 2)]
      if min(corners) < barrier:
        contact = (t, "body reaches the barrier (not modelled)")
    if contact:
      break
  if contact:
    events.append({"t": contact[0] - t_fault, "label": contact[1]})
    cut = min(n, int(round((contact[0] + END_AFTER_CONTACT - t_start) * FPS)) + 1)
    times, speed, e_lat = times[:cut], speed[:cut], e_lat[:cut]
    ax, ay, torque = ax[:cut], ay[:cut], torque[:cut]
    gap_lead, gap_follow = gap_lead[:cut], gap_follow[:cut]
    for a in actors:
      a["poses"] = a["poses"][:cut]
    t_end = times[-1]
  # the plant reports an event once; keep those inside the window
  events = sorted((e for e in events if t_start - t_fault <= e["t"] <= t_end - t_fault + 1e-9), key=lambda e: e["t"])
  if not any(e["label"] == "fault" for e in events):
    events.insert(0, {"t": 0.0, "label": "fault"})

  s_lo = min(es) - 120.0
  s_hi = max(es) + 250.0
  centre = []
  s = max(0.0, s_lo)
  while s <= min(s_hi, road.s[-1]):
    centre.append(list(_road_pose(road, s, 0.0)) + [s])
    s += DS_ROAD

  thr = res.metrics["lane_threshold"]
  return {
    "schema_version": 1,
    "id": scene["id"],
    "caption": " ".join(scene["caption"].split()),
    "he": {k: he.get(k) for k in ("id", "situation", "effect", "s", "e", "c", "asil")},
    "hazard": {"id": hazard["id"], "title": hazard["title"]},
    "case": {"id": case.id, "title": case.title, "sg": case.sg, "speed_kph": case.speed_kph,
             "road": road.name, "longitudinal": case.longitudinal, "eps": case.eps},
    "provenance": "Layer-1 plant model (assurance/sim/plant), synthetic (DSR-12): pictures only, no evidence credit",
    "fps": FPS,
    "t_fault": t_fault,
    "t": [t - t_fault for t in times],
    "speed": speed,
    "lateral": e_lat,
    "ax": ax,
    "ay": ay,
    "eps_torque": torque,
    "lane_threshold": thr,
    "gap": {"lead": gap_lead, "follower": gap_follow} if case.longitudinal else None,
    "car": {"length": LENGTH, "width": width},
    "road": {"lane_width": lw, "lanes_left": rd["lanes_left"], "lanes_right": rd["lanes_right"],
             "left_edge": left_edge, "right_edge": right_edge, "shoulder_m": rd["shoulder_m"], "barrier": barrier,
             "centre": centre},
    "actors": actors,
    "events": events,
    "metrics": {k: v for k, v in res.metrics.items() if k != "events"},
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
    print(f"{sc['id']}: {len(data['t'])} frames, {len(data['events'])} events -> {out / 'scene.json'}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
