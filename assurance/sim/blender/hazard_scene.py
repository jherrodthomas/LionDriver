"""Build and render a hazardous-event scene in Blender (assurance/sim/blender, step 2 of 3).

Reads out/<scene>/scene.json from export_scene.py and builds an animated Blender scene: the road from its
cross-section, scenery and props, the sky and sun (or night), every road user keyframed frame by frame, a
translucent ego "ghost" left at each event, the ego's path drawn on the road as it goes, and three cameras that follow
the ego (chase, forward, orthographic top). Saves scene.blend (open it in Blender to scrub, re-light or re-frame),
writes where each road user appears in the chase view (screen.json, for the dashboard tags), then renders the
key-event stills and, if asked, the frames of a clip. compose.py adds the dashboard.

Every car is the purchased Corolla E210 mesh when the GLB is present (assets/1450755-gltf-extended.glb, or --vehicle,
or LIONDRIVER_VEHICLE_GLB), instanced and repainted per road user; otherwise a stand-in lofted from the committed
silhouette. Trucks, pedestrians and cyclists are simple procedural models. A scene.blend made with the purchased mesh
holds licensed content: its renders may be published, the .blend may not (assets/README.md).

Runs in Blender 4.2 or later, or in Python 3.13 with the bpy module (pip install bpy):

  blender -b -P assurance/sim/blender/hazard_scene.py -- assurance/sim/blender/out/<scene>/scene.json --stills
  python3 assurance/sim/blender/hazard_scene.py assurance/sim/blender/out/<scene>/scene.json --stills --video

Rendering uses Cycles on the CPU, so it runs headless without a GPU (EEVEE needs OpenGL).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scene_assets as A  # noqa: E402

SIM = HERE.parent
DEFAULT_GLB = SIM / "assets" / "1450755-gltf-extended.glb"

EGO_RGB = (0.62, 0.12, 0.03)            # ego body paint (the dashboard's ego colour, darkened for metallic paint)
GHOST_RGB = (0.85, 0.22, 0.05)
PLANT_RGB = (0.12, 0.22, 0.45)          # road users the plant models (lead, follower)
OTHER_RGB = (0.72, 0.73, 0.75)          # other cars, unless the scene gives a paint


# ------------------------------------------------------------------------------------------------- animation
def unwrap(angles):
  out, prev = [], None
  for a in angles:
    if prev is not None:
      while a - prev > math.pi:
        a -= 2 * math.pi
      while a - prev < -math.pi:
        a += 2 * math.pi
    out.append(a)
    prev = a
  return out


def fcurves(ob):
  ad = ob.animation_data
  if not ad or not ad.action:
    return []
  try:
    return list(ad.action.fcurves)
  except AttributeError:                        # Blender 5: layered actions
    return [fc for layer in ad.action.layers for st in layer.strips for bag in st.channelbags for fc in bag.fcurves]


def linear(ob):
  for fc in fcurves(ob):
    for kp in fc.keyframe_points:
      kp.interpolation = "LINEAR"


def keyframe_poses(ob, poses, z: float = 0.0):
  yaws = unwrap([p[2] for p in poses])
  for f, (p, yaw) in enumerate(zip(poses, yaws), start=1):
    ob.location = (p[0], p[1], z)
    ob.rotation_euler = (0.0, 0.0, yaw)
    ob.keyframe_insert("location", frame=f)
    ob.keyframe_insert("rotation_euler", frame=f)
  linear(ob)


def walk_cycle(limbs, poses, stride: float = 0.75):
  """Swing legs and arms with the distance walked (a step every `stride` metres)."""
  dist = 0.0
  for f, p in enumerate(poses, start=1):
    if f > 1:
      dist += math.hypot(p[0] - poses[f - 2][0], p[1] - poses[f - 2][1])
    sw = 0.45 * math.sin(math.pi * dist / stride)
    for k, (hip, sh) in enumerate(limbs):
      sgn = 1 if k == 0 else -1
      hip.rotation_euler = (0, sgn * sw, 0)
      sh.rotation_euler = (0, -sgn * sw * 0.8, 0)
      hip.keyframe_insert("rotation_euler", frame=f)
      sh.keyframe_insert("rotation_euler", frame=f)
  for hip, sh in limbs:
    linear(hip)
    linear(sh)


def show_from(ob, frame: int):
  for o in [ob] + list(ob.children_recursive):
    o.hide_render = o.hide_viewport = True
    o.keyframe_insert("hide_render", frame=1)
    o.keyframe_insert("hide_viewport", frame=1)
    o.hide_render = o.hide_viewport = False
    o.keyframe_insert("hide_render", frame=frame)
    o.keyframe_insert("hide_viewport", frame=frame)


def smooth(vals, k: int):
  return [sum(vals[max(0, i - k):i + k + 1]) / len(vals[max(0, i - k):i + k + 1]) for i in range(len(vals))]


def nearest_centre(centre, x, y, hint=0):
  best, j = None, hint
  for i in range(max(0, hint - 5), len(centre)):
    d = (centre[i][0] - x) ** 2 + (centre[i][1] - y) ** 2
    if best is None or d < best:
      best, j = d, i
    elif d > best + 400:
      break
  return j


def centre_at(centre, s: float):
  i = min(max(int(round(s - centre[0][3])), 0), len(centre) - 1)
  return centre[i]


# ------------------------------------------------------------------------------------------------- road users
def headlights(root, coll, front: float = 2.25):
  for y in (0.62, -0.62):
    lt = bpy.data.objects.new("headlight", bpy.data.lights.new("headlight", "SPOT"))
    lt.data.energy, lt.data.spot_size, lt.data.spot_blend = 4000, math.radians(60), 0.5
    lt.data.color = (1.0, 0.95, 0.85)
    lt.parent = root
    lt.location = (front, y, 0.7)
    lt.rotation_euler = (0, math.radians(-88), 0)       # the spot points along +X, a little down
    coll.objects.link(lt)


def make_actor(a: dict, model, coll, night: bool):
  kind = a["kind"]
  name = a["name"].replace(" ", "_")
  limbs = None
  if kind in ("ego", "car"):
    rgb = EGO_RGB if kind == "ego" else tuple(a.get("paint") or (PLANT_RGB if a["source"] == "plant" else OTHER_RGB))
    body = A.paint(rgb)
    ob = model.instance(name, coll, body=body) if model else A.standin_car(name, coll, body=body)
    if night:
      headlights(ob, coll)
  elif kind == "truck":
    ob = A.truck(name, coll)
    if night:
      headlights(ob, coll, 4.8)
  elif kind == "pedestrian":
    ob, limbs = A.pedestrian(name, coll)
  elif kind == "cyclist":
    ob = A.cyclist(name, coll)
  else:
    raise ValueError(kind)
  keyframe_poses(ob, a["poses"])
  if limbs:
    walk_cycle(limbs, a["poses"])
  return ob


# ------------------------------------------------------------------------------------------------- props
def build_props(sc: dict, coll):
  c = sc["road"]["centre"]
  r = sc["road"]
  left, right = r["outer"]
  concrete = A.material("concrete", (0.5, 0.49, 0.47), rough=0.85)
  for k, p in enumerate(sc["props"]):
    kind = p["kind"]
    if kind == "overpass":
      x, y, h = centre_at(c, p["s"])[:3]
      span = (left - right) + 16
      mx, my, _ = A.offset(centre_at(c, p["s"]), 0.5 * (left + right))
      A.part("overpass_deck", A.box_mesh(f"deck{k}", 12.0, span, 1.2, 5.6, concrete), None, coll, (mx, my, 0), (0, 0, h))
      A.part("overpass_rail", A.box_mesh(f"rail{k}", 0.3, span, 1.0, 6.8, concrete), None, coll,
             A.offset(centre_at(c, p["s"] - 5.8), 0.5 * (left + right)), (0, 0, h))
      for d in (left + 2.0, right - 2.0):
        px, py, _ = A.offset(centre_at(c, p["s"]), d)
        A.part("overpass_pier", A.box_mesh(f"pier{k}{d:.0f}", 2.0, 1.2, 5.6, 0.0, concrete), None, coll, (px, py, 0),
               (0, 0, h))
    elif kind == "intersection":
      cc = centre_at(c, p["s"])
      x, y, h = cc[:3]
      w = p.get("width", 14.0)
      asphalt = bpy.data.materials.get("asphalt") or A.material("asphalt", (0.05, 0.05, 0.055), rough=0.85)
      A.part("cross_road", A.box_mesh(f"cross{k}", w, 160.0, 0.16, -0.005, asphalt), None, coll, (x, y, 0), (0, 0, h))
      white = A.material("paint_white", (0.85, 0.85, 0.82), rough=0.5)
      for side in (-1, 1):                      # zebra crossings either side of the junction
        cz = centre_at(c, p["s"] + side * (w / 2 + 2.5))
        d = right
        while d < left:
          zx, zy, _ = A.offset(cz, d + 0.25)
          A.part("zebra", A.box_mesh(f"zebra{k}{side}{d:.1f}", 3.0, 0.5, 0.01, 0.158, white), None, coll, (zx, zy, 0),
                 (0, 0, cz[2]))
          d += 1.0
    elif kind == "traffic_light":
      cc = centre_at(c, p["s"])
      x, y, _ = A.offset(cc, p.get("d", 0.0))
      pole = A.part("signal_pole", A.cyl_mesh(f"sigpole{k}", 0.09, 4.2, mat=A.material("pole", (0.15, 0.15, 0.16))),
                    None, coll, (x, y, 2.1))
      head = A.part("signal_head", A.box_mesh(f"sighead{k}", 0.35, 0.4, 1.1, 0.0,
                                               A.material("signal_box", (0.05, 0.05, 0.05), rough=0.5)),
                    None, coll, (x, y, 4.2), (0, 0, cc[2]))
      on = {"red": (1.0, 0.05, 0.02), "amber": (1.0, 0.6, 0.0), "green": (0.1, 1.0, 0.3)}[p.get("state", "red")]
      lz = {"red": 4.95, "amber": 4.6, "green": 4.25}[p.get("state", "red")]
      lx, ly, _ = A.offset(cc, p.get("d", 0.0))
      lx -= 0.19 * math.cos(cc[2])
      ly -= 0.19 * math.sin(cc[2])
      A.part("signal_lamp", A.sphere_mesh(f"siglamp{k}", 0.12, 2, A.material(f"lamp_{p.get('state')}", on, emit=25.0)),
             None, coll, (lx, ly, lz))
    elif kind == "cones":
      cone = bpy.data.meshes.get("cone")
      if cone is None:
        import bmesh
        cone = bpy.data.meshes.new("cone")
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.2, radius2=0.03, depth=0.75)
        bmesh.ops.translate(bm, vec=(0, 0, 0.375), verts=bm.verts)
        bm.to_mesh(cone)
        bm.free()
        cone.materials.append(A.material("cone_orange", (0.95, 0.25, 0.02), rough=0.5, emit=0.3))
      for s, d in p["points"]:
        x, y, _ = A.offset(centre_at(c, s), d)
        A.part("cone", cone, None, coll, (x, y, 0))
    elif kind == "seam":
      tar = A.material("tar", (0.008, 0.008, 0.01), rough=0.25)
      n = int(p["len"])
      verts, faces = [], []
      for i in range(n + 1):
        cc = centre_at(c, p["s"] + i)
        d = p["d0"] + (p["d1"] - p["d0"]) * i / n
        verts += [A.offset(cc, d + 0.14, 0.005), A.offset(cc, d - 0.14, 0.005)]
        if i:
          faces.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
      A.mesh_object("seam", verts, faces, tar, coll)
    else:
      raise ValueError(kind)


# ------------------------------------------------------------------------------------------------- cameras, path
def rear_view(sc: dict) -> bool:
  """True when the critical road user starts more than 8 m behind the ego (a follower, an overtaking car)."""
  crit = next((a for a in sc["actors"] if a["name"] == sc.get("critical")), None)
  if crit is None:
    return False
  (ex, ey, h), (cx, cy, _) = sc["actors"][0]["poses"][0], crit["poses"][0]
  return (cx - ex) * math.cos(h) + (cy - ey) * math.sin(h) < -8.0


def build_cameras(sc: dict):
  ego = sc["actors"][0]["poses"]
  c = sc["road"]["centre"]
  r = sc["road"]
  heads, idx, j = [], [], 0
  for x, y, _ in ego:
    j = nearest_centre(c, x, y, j)
    idx.append(j)
    heads.append(c[j][2])
  heads = smooth(unwrap(heads), 12)
  ex, ey = smooth([p[0] for p in ego], 6), smooth([p[1] for p in ego], 6)
  urban = r["type"] == "urban"
  back, up, side, ahead = (12.0, 5.0, 2.5, 12.0) if urban else (15.0, 6.5, 4.0, 14.0)
  if rear_view(sc):                             # the critical road user comes from behind: look back past the ego
    back, ahead, up = -18.0, -16.0, 7.0

  cams = {}
  chase = bpy.data.objects.new("cam_chase", bpy.data.cameras.new("cam_chase"))
  chase.data.lens = 30
  target = bpy.data.objects.new("cam_chase_target", None)
  bpy.context.scene.collection.objects.link(chase)
  bpy.context.scene.collection.objects.link(target)
  tc = chase.constraints.new("TRACK_TO")
  tc.target, tc.track_axis, tc.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
  for f, (x, y, h) in enumerate(zip(ex, ey, heads), start=1):
    chase.location = (x - back * math.cos(h) - side * math.sin(h), y - back * math.sin(h) + side * math.cos(h), up)
    target.location = (x + ahead * math.cos(h), y + ahead * math.sin(h), 0.0)
    chase.keyframe_insert("location", frame=f)
    target.keyframe_insert("location", frame=f)
  linear(chase)
  linear(target)
  cams["chase"] = chase

  top = bpy.data.objects.new("cam_top", bpy.data.cameras.new("cam_top"))
  top.data.type = "ORTHO"
  left = r["left_edge"] + 1.0
  rightb = (r["barrier"] if r.get("barrier") is not None else r["right_edge"]) - 1.5
  top.data.ortho_scale = max(48.0, (left - rightb) * 16 / 9 * 1.1)
  mid = 0.5 * (left + rightb)
  bpy.context.scene.collection.objects.link(top)
  for f, (j, h) in enumerate(zip(idx, heads), start=1):
    p = c[min(j + 6, len(c) - 1)]
    x, y, _ = A.offset(p, mid)
    top.location = (x, y, 60.0)
    top.rotation_euler = (0.0, 0.0, h)
    top.keyframe_insert("location", frame=f)
    top.keyframe_insert("rotation_euler", frame=f)
  linear(top)
  cams["top"] = top

  # forward view from just ahead of the windscreen, 1.2 m up, along the ego's own heading (bonnet in view)
  front = bpy.data.objects.new("cam_driver", bpy.data.cameras.new("cam_driver"))
  front.data.lens = 24
  bpy.context.scene.collection.objects.link(front)
  yaws = unwrap([p[2] for p in ego])
  for f, (p, h) in enumerate(zip(ego, yaws), start=1):
    front.location = (p[0] + 1.2 * math.cos(h), p[1] + 1.2 * math.sin(h), 1.2)
    front.rotation_euler = (math.radians(86), 0.0, h - math.pi / 2)
    front.keyframe_insert("location", frame=f)
    front.keyframe_insert("rotation_euler", frame=f)
  linear(front)
  cams["driver"] = front
  return cams


def build_path(sc: dict, frames: int):
  """The ego's path on the road, revealed as the ego drives it."""
  poses = sc["actors"][0]["poses"]
  cu = bpy.data.curves.new("ego_path", "CURVE")
  cu.dimensions = "3D"
  cu.bevel_depth = 0.07
  cu.bevel_factor_mapping_end = "SPLINE"
  sp = cu.splines.new("POLY")
  sp.points.add(len(poses) - 1)
  for p, (x, y, _) in zip(sp.points, poses):
    p.co = (x, y, 0.03, 1.0)
  ob = bpy.data.objects.new("ego_path", cu)
  cu.materials.append(A.material("path", GHOST_RGB, emit=2.0))
  bpy.context.scene.collection.objects.link(ob)
  lengths = [0.0]
  for a, b in zip(poses, poses[1:]):
    lengths.append(lengths[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
  total = lengths[-1] or 1.0
  for f in range(1, frames + 1):
    cu.bevel_factor_end = lengths[f - 1] / total if total > 0.5 else 0.0
    cu.keyframe_insert("bevel_factor_end", frame=f)
  return ob


def key_frames(sc: dict) -> list[dict]:
  """One still per distinct event (closer than 0.15 s merges), plus the first and the last frame."""
  t = sc["t"]
  out = [{"frame": 1, "t": t[0], "label": "start"}]
  for e in sc["events"]:
    f = min(range(len(t)), key=lambda i: abs(t[i] - e["t"])) + 1
    if abs(out[-1]["t"] - e["t"]) < 0.15:
      out[-1]["label"] = e["label"] if out[-1]["label"] == "start" else out[-1]["label"] + "; " + e["label"]
      continue
    out.append({"frame": f, "t": e["t"], "label": e["label"]})
  if out[-1]["frame"] != len(t):
    out.append({"frame": len(t), "t": t[-1], "label": "end"})
  return out


# ------------------------------------------------------------------------------------------------- scene
def build(sc: dict, vehicle: Path | None, front: str | None) -> dict:
  bpy.ops.wm.read_factory_settings(use_empty=True)
  scene = bpy.context.scene
  scene.unit_settings.system = "METRIC"
  frames = len(sc["t"])
  scene.render.fps = sc["fps"]
  scene.frame_start, scene.frame_end = 1, frames
  env = dict(sc.get("env", {}), urban=sc["road"]["type"] == "urban")
  A.build_environment(env, sc["actors"][0]["poses"][0][2])
  A.build_road(sc["road"], env)
  A.build_scenery(sc["road"], env)
  props = bpy.data.collections.new("props")
  scene.collection.children.link(props)
  build_props(sc, props)

  model = A.CarModel(vehicle, front) if vehicle else None
  users = bpy.data.collections.new("road_users")
  scene.collection.children.link(users)
  for a in sc["actors"]:
    make_actor(a, model, users, env.get("night", False))

  ghosts = bpy.data.collections.new("event_ghosts")
  scene.collection.children.link(ghosts)
  keys = key_frames(sc)
  ghost = A.ghost_material(GHOST_RGB)
  for k in keys[1:]:
    if k["label"] == "end":
      continue
    g = A.standin_car(f"ghost_{k['frame']:04d}", ghosts, override=ghost)
    x, y, h = sc["actors"][0]["poses"][k["frame"] - 1]
    g.location, g.rotation_euler = (x, y, 0.0), (0.0, 0.0, h)
    show_from(g, k["frame"] + 1)
  build_path(sc, frames)
  cams = build_cameras(sc)
  scene.camera = cams["chase"]
  return {"keys": keys, "cams": cams}


def screen_positions(sc: dict, cam) -> dict:
  """Where each road user's roof appears in the chase view, per frame (0..1 from the top left; null if behind)."""
  from bpy_extras.object_utils import world_to_camera_view
  from mathutils import Vector
  s = bpy.context.scene
  heights = {"pedestrian": 1.9, "cyclist": 1.8, "truck": 3.9}
  out = {}
  for f in range(1, len(sc["t"]) + 1):
    s.frame_set(f)
    for a in sc["actors"]:
      x, y, _ = a["poses"][f - 1]
      p = world_to_camera_view(s, cam, Vector((x, y, heights.get(a["kind"], 1.6))))
      out.setdefault(a["name"], []).append([round(p.x, 4), round(1 - p.y, 4)] if p.z > 0 else None)
  return out


def render_setup(res: tuple[int, int], samples: int):
  s = bpy.context.scene
  s.render.engine = "CYCLES"
  s.cycles.device = "CPU"
  s.cycles.samples = samples
  s.cycles.use_denoising = True
  s.cycles.max_bounces = 4
  s.cycles.transparent_max_bounces = 8
  s.render.use_persistent_data = True
  s.render.resolution_x, s.render.resolution_y = res
  s.render.resolution_percentage = 100
  s.render.image_settings.file_format = "PNG"
  s.render.film_transparent = False


def render_frame(cam, frame: int, path: Path):
  s = bpy.context.scene
  s.camera = cam
  ghosts = bpy.data.collections.get("event_ghosts")
  if ghosts:                                    # the ghosts and the path read from above; from the road they block the view
    ghosts.hide_render = cam.name != "cam_top"
  s.frame_set(frame)
  s.render.filepath = str(path)
  bpy.ops.render.render(write_still=True)


def main(argv: list[str]) -> int:
  argv = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("scene", type=Path, help="scene.json written by export_scene.py")
  ap.add_argument("--vehicle", type=Path, help="GLB of the reference car (default: the purchased mesh if present)")
  ap.add_argument("--standin", action="store_true", help="use the silhouette stand-in even if the GLB is present")
  ap.add_argument("--front", choices=["+x", "-x", "+y", "-y"], help="front of the GLB after import (default: found)")
  ap.add_argument("--stills", action="store_true", help="render the key-event frames from the three cameras")
  ap.add_argument("--video", action="store_true", help="render every frame from the three cameras")
  ap.add_argument("--res", default="1280x720", help="chase still resolution, WxH (side views at half)")
  ap.add_argument("--video-res", default="960x540", help="chase clip resolution, WxH (side views at half)")
  ap.add_argument("--samples", type=int, default=16, help="Cycles samples for stills (clip: half)")
  ap.add_argument("--no-blend", action="store_true", help="do not save scene.blend")
  args = ap.parse_args(argv)

  sc = json.loads(args.scene.read_text())
  out = args.scene.parent
  vehicle = None
  if not args.standin:
    cand = args.vehicle or (Path(os.environ["LIONDRIVER_VEHICLE_GLB"]) if os.environ.get("LIONDRIVER_VEHICLE_GLB")
                            else DEFAULT_GLB)
    if cand.exists():
      vehicle = cand
    elif args.vehicle:
      print(f"{cand}: not found", file=sys.stderr)
      return 1
  built = build(sc, vehicle, args.front)
  if not args.no_blend:
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "scene.blend"))
  (out / "screen.json").write_text(json.dumps(screen_positions(sc, built["cams"]["chase"])))
  manifest = {"scene": sc["id"], "vehicle": "purchased mesh" if vehicle else "stand-in", "stills": [], "video": {}}

  def sized(name, w, h):
    d = 1 if name == "chase" else 2             # the side views are drawn at half size
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = w // d, h // d

  if args.stills:
    w, h = (int(v) for v in args.res.split("x"))
    render_setup((w, h), args.samples)
    for k in built["keys"]:
      for name, cam in built["cams"].items():
        sized(name, w, h)
        p = out / "stills" / f"f{k['frame']:04d}_{name}.png"
        render_frame(cam, k["frame"], p)
        manifest["stills"].append({**k, "camera": name, "file": str(p.relative_to(out))})
  if args.video:
    w, h = (int(v) for v in args.video_res.split("x"))
    render_setup((w, h), max(4, args.samples // 2))
    for name, cam in built["cams"].items():
      sized(name, w, h)
      for f in range(1, len(sc["t"]) + 1):
        render_frame(cam, f, out / "frames" / name / f"{f:04d}.png")
      manifest["video"][name] = f"frames/{name}/%04d.png"
  (out / "render.json").write_text(json.dumps(manifest, indent=1))
  print(f"{sc['id']}: {len(manifest['stills'])} stills ({manifest['vehicle']}); clip cameras {list(manifest['video'])}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
