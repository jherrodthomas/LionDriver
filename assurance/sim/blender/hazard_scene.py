"""Build and render a hazardous-event scene in Blender (assurance/sim/blender, step 2 of 3).

Reads out/<scene>/scene.json from export_scene.py and builds an animated Blender scene: the road with its lanes,
markings, shoulder and barrier; the ego car and the other road users keyframed frame by frame from the plant output;
a translucent ego "ghost" left at each panda or driver event; the ego's path drawn on the road as it goes; a chase
camera and an orthographic top camera that follow the ego. Saves scene.blend (open it in Blender to scrub, re-light
or re-frame), then renders the key-event stills and, if asked, the frames of a clip. compose.py adds the HUD.

The ego is the purchased Corolla E210 mesh when the GLB is present (assets/1450755-gltf-extended.glb, or --vehicle,
or LIONDRIVER_VEHICLE_GLB), and otherwise a stand-in lofted from the committed silhouette
(figures/corolla-e210-silhouette.json). Other cars are always the stand-in. A scene.blend or a render made with the
purchased mesh holds licensed content: renders may be published, the .blend may not (assets/README.md).

Runs in Blender 4.2 or later, or in Python with the bpy module (pip install bpy; Blender 5.x needs Python 3.13):

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
SIM = HERE.parent
SILHOUETTE = SIM / "figures" / "corolla-e210-silhouette.json"
DEFAULT_GLB = SIM / "assets" / "1450755-gltf-extended.glb"

EGO_RGB = (0.85, 0.22, 0.05)           # ego body
PLANT_RGB = (0.16, 0.30, 0.55)         # road users the plant models (lead, follower)
ILLUSTRATIVE_RGB = (0.62, 0.64, 0.68)  # road users drawn but not simulated


# ------------------------------------------------------------------------------------------------- materials
def material(name: str, rgb, rough: float = 0.5, metal: float = 0.0, alpha: float = 1.0, emit: float = 0.0):
  m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
  m.use_nodes = True
  b = m.node_tree.nodes.get("Principled BSDF")
  b.inputs["Base Color"].default_value = (*rgb, 1.0)
  b.inputs["Roughness"].default_value = rough
  b.inputs["Metallic"].default_value = metal
  b.inputs["Alpha"].default_value = alpha
  if emit:
    b.inputs["Emission Color"].default_value = (*rgb, 1.0)
    b.inputs["Emission Strength"].default_value = emit
  m.diffuse_color = (*rgb, alpha)
  return m


def mesh_object(name: str, verts, faces, mat=None, collection=None, smooth=False):
  me = bpy.data.meshes.new(name)
  me.from_pydata(verts, [], faces)
  me.update()
  if smooth:
    for p in me.polygons:
      p.use_smooth = True
  ob = bpy.data.objects.new(name, me)
  (collection or bpy.context.scene.collection).objects.link(ob)
  if mat:
    me.materials.append(mat)
  return ob


def collection(name: str):
  c = bpy.data.collections.new(name)
  bpy.context.scene.collection.children.link(c)
  return c


# ------------------------------------------------------------------------------------------------- road
def offset(c, d: float, z: float = 0.0):
  x, y, h = c[0], c[1], c[2]
  return (x - d * math.sin(h), y + d * math.cos(h), z)


def strip(name, centre, d0: float, d1: float, z: float, mat, coll, s_ranges=None):
  """A flat ribbon between lateral offsets d0 and d1 (left positive); s_ranges limits it to dashes."""
  verts, faces = [], []
  for i in range(len(centre) - 1):
    a, b = centre[i], centre[i + 1]
    if s_ranges is not None and not any(lo <= a[3] < hi for lo, hi in s_ranges):
      continue
    k = len(verts)
    verts += [offset(a, d0, z), offset(a, d1, z), offset(b, d1, z), offset(b, d0, z)]
    faces.append((k, k + 1, k + 2, k + 3))
  return mesh_object(name, verts, faces, mat, coll)


def build_road(sc: dict):
  r = sc["road"]
  c = r["centre"]
  coll = collection("road")
  asphalt = material("asphalt", (0.045, 0.045, 0.05), rough=0.85)
  shoulder = material("shoulder", (0.075, 0.075, 0.08), rough=0.9)
  paint = material("paint", (0.85, 0.85, 0.82), rough=0.6)
  grass = material("grass", (0.10, 0.17, 0.06), rough=1.0)
  steel = material("barrier", (0.55, 0.57, 0.6), rough=0.35, metal=0.8)

  lw = r["lane_width"]
  left, right = r["left_edge"], r["right_edge"]
  outer = r["barrier"] if r["barrier"] is not None else right - r["shoulder_m"]
  strip("carriageway", c, left + 0.6, right, 0.0, asphalt, coll)
  strip("shoulder", c, right, outer - 0.4, -0.002, shoulder, coll)
  strip("verge_left", c, left + 60, left + 0.6, -0.03, grass, coll)
  strip("verge_right", c, outer - 0.4, outer - 60, -0.03, grass, coll)
  # markings: solid edge lines, dashed lane lines (3 m dash, 9 m gap)
  strip("edge_left", c, left - 0.1, left - 0.25, 0.004, paint, coll)
  strip("edge_right", c, right + 0.25, right + 0.1, 0.004, paint, coll)
  s0, s1 = c[0][3], c[-1][3]
  dashes = [(s, s + 3.0) for s in [s0 + 12.0 * i for i in range(int((s1 - s0) / 12.0) + 1)]]
  for k in range(1, r["lanes_left"] + r["lanes_right"] + 1):
    d = left - k * lw
    strip(f"lane_line_{k}", c, d + 0.075, d - 0.075, 0.004, paint, coll, dashes)
  if r["barrier"] is not None:
    b = r["barrier"]
    verts, faces = [], []
    for i, p in enumerate(c):
      verts += [offset(p, b, 0.5), offset(p, b, 0.82), offset(p, b - 0.06, 0.82), offset(p, b - 0.06, 0.5)]
      if i:
        k = 4 * i
        for j in range(4):
          faces.append((k - 4 + j, k - 4 + (j + 1) % 4, k + (j + 1) % 4, k + j))
    mesh_object("barrier_rail", verts, faces, steel, coll)
    verts, faces = [], []
    for p in c[::2]:
      k = len(verts)
      x, y, _ = offset(p, b - 0.15, 0)
      for dz in (0.0, 0.7):
        verts += [(x - 0.06, y - 0.06, dz), (x + 0.06, y - 0.06, dz), (x + 0.06, y + 0.06, dz), (x - 0.06, y + 0.06, dz)]
      faces += [(k, k + 1, k + 5, k + 4), (k + 1, k + 2, k + 6, k + 5), (k + 2, k + 3, k + 7, k + 6),
                (k + 3, k, k + 4, k + 7), (k + 4, k + 5, k + 6, k + 7)]
    mesh_object("barrier_posts", verts, faces, steel, coll)


# ------------------------------------------------------------------------------------------------- cars
def standin_mesh(name: str):
  """A car body lofted from the reference car's top and side outlines: forward +X, ground at Z = 0."""
  me = bpy.data.meshes.get(name)
  if me:
    return me
  sil = json.loads(SILHOUETTE.read_text())
  top = sil["side_outline"]["top"]
  half = sil["top_outline_body"]["right"]
  verts, faces, mats = [], [], []
  ring = None
  for (along, zt), (_, w) in zip(top[::2], half[::2]):
    x = -along                                  # the file's -y is the front
    zb = 0.2
    zt = max(zt, zb + 0.12)
    w = max(w, 0.15)
    belt = min(zt - 0.04, 0.95)
    cabin = zt > 1.05
    if cabin:                                   # cabin: glasshouse tapers above the belt line
      prof = [(0.9 * w, zb), (w, 0.5), (0.97 * w, belt), (0.72 * w, zt - 0.06), (0.5 * w, zt)]
    else:                                       # bonnet or boot
      zm = zb + 0.55 * (zt - zb)
      prof = [(0.9 * w, zb), (w, zm), (0.97 * w, zt - 0.06), (0.85 * w, zt - 0.01), (0.5 * w, zt)]
    pts = [(x, -y, z) for y, z in prof] + [(x, y, z) for y, z in reversed(prof)]
    k = len(verts)
    verts += pts
    if ring is not None:
      n = len(pts)
      for j in range(n):
        faces.append((ring + j, ring + (j + 1) % n, k + (j + 1) % n, k + j))
        mats.append(1 if cabin and j in (2, 3, 5, 6) else 0)
    ring = k
  n = 10
  faces.append(tuple(range(0, n)))
  mats.append(0)
  faces.append(tuple(range(ring + n - 1, ring - 1, -1)))
  mats.append(0)
  me = bpy.data.meshes.new(name)
  me.from_pydata(verts, [], faces)
  for p, m in zip(me.polygons, mats):
    p.material_index = m
    p.use_smooth = True
  me.update()
  return me


def wheel_mesh():
  me = bpy.data.meshes.get("standin_wheel")
  if me:
    return me
  sil = json.loads(SILHOUETTE.read_text())
  r, w, n = sil["r_tire"], 0.22, 24
  verts, faces = [], []
  for side in (-w / 2, w / 2):
    for i in range(n):
      a = 2 * math.pi * i / n
      verts.append((r * math.cos(a), side, r * math.sin(a) + r))
  for i in range(n):
    faces.append((i, (i + 1) % n, n + (i + 1) % n, n + i))
  faces += [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
  me = bpy.data.meshes.new("standin_wheel")
  me.from_pydata(verts, [], faces)
  me.update()
  me.materials.append(material("tyre", (0.02, 0.02, 0.02), rough=0.9))
  return me


def standin_car(name: str, rgb, coll, alpha: float = 1.0):
  """Empty at the body centre on the ground, forward +X, with the lofted body and four wheels."""
  root = bpy.data.objects.new(name, None)
  coll.objects.link(root)
  tag = f"{name}_paint"
  body = bpy.data.objects.new(f"{name}_body", standin_mesh("standin_body").copy())
  body.data.materials.append(material(tag, rgb, rough=0.25, metal=0.4, alpha=alpha))
  body.data.materials.append(material(f"glass_{alpha:g}", (0.03, 0.04, 0.05), rough=0.05, alpha=min(alpha, 0.9)))
  body.parent = root
  coll.objects.link(body)
  sil = json.loads(SILHOUETTE.read_text())
  for wh in sil["wheels"]:
    ob = bpy.data.objects.new(f"{name}_{wh['name']}", wheel_mesh())
    ob.location = (-wh["y"], wh["x"] * 1.04, 0.0)
    ob.parent = root
    coll.objects.link(ob)
  return root


def glb_car(path: Path, front: str | None, coll):
  """The purchased mesh, centred on the ground and turned to face +X, under an empty named ego."""
  before = set(bpy.data.objects)
  bpy.ops.import_scene.gltf(filepath=str(path))
  new = [o for o in bpy.data.objects if o not in before]
  for o in new:
    for c in o.users_collection:
      c.objects.unlink(o)
    coll.objects.link(o)
  meshes = [o for o in new if o.type == "MESH"]
  bpy.context.view_layer.update()
  pts = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
  lo = [min(p[i] for p in pts) for i in range(3)]
  hi = [max(p[i] for p in pts) for i in range(3)]
  ext = [hi[i] - lo[i] for i in range(3)]
  along = 0 if ext[0] >= ext[1] else 1
  if front is None:
    # the bonnet end is lower than the boot end (silhouette: 0.87 m against 1.15 m over the outer quarters)
    q = 0.25 * ext[along]
    near = [p[2] for p in pts if p[along] < lo[along] + q]
    far = [p[2] for p in pts if p[along] > hi[along] - q]
    def top(zs):
      zs = sorted(zs)
      return zs[int(0.98 * (len(zs) - 1))] if zs else 0.0
    sign = -1 if top(near) < top(far) else 1
    front = ("-" if sign < 0 else "+") + "xy"[along]
  yaw = {"+x": 0.0, "-x": math.pi, "+y": -math.pi / 2, "-y": math.pi / 2}[front]
  holder = bpy.data.objects.new("ego_mesh", None)
  coll.objects.link(holder)
  cx, cy = 0.5 * (lo[0] + hi[0]), 0.5 * (lo[1] + hi[1])
  for o in new:
    if o.parent is None:
      o.parent = holder
      o.matrix_parent_inverse.identity()
  holder.location = (0, 0, 0)
  holder.rotation_euler = (0, 0, yaw)
  # shift so the bounding-box centre is at the origin and the lowest point on the ground, before the turn
  for o in new:
    if o.parent is holder:
      o.location = (o.location[0] - cx, o.location[1] - cy, o.location[2] - lo[2])
  root = bpy.data.objects.new("ego", None)
  coll.objects.link(root)
  holder.parent = root
  print(f"vehicle: {path.name}, front {front}, extent {ext[0]:.2f} x {ext[1]:.2f} x {ext[2]:.2f} m")
  return root


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


def keyframe_poses(ob, poses, z: float = 0.0):
  yaws = unwrap([p[2] for p in poses])
  for f, (p, yaw) in enumerate(zip(poses, yaws), start=1):
    ob.location = (p[0], p[1], z)
    ob.rotation_euler = (0.0, 0.0, yaw)
    ob.keyframe_insert("location", frame=f)
    ob.keyframe_insert("rotation_euler", frame=f)
  linear(ob)


def linear(ob):
  ad = ob.animation_data
  if not ad or not ad.action:
    return
  try:
    curves = ad.action.fcurves
  except AttributeError:                        # Blender 5: layered actions
    curves = [fc for layer in ad.action.layers for strip_ in layer.strips
              for bag in strip_.channelbags for fc in bag.fcurves]
  for fc in curves:
    for kp in fc.keyframe_points:
      kp.interpolation = "LINEAR"


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

  cams = {}
  chase = bpy.data.objects.new("cam_chase", bpy.data.cameras.new("cam_chase"))
  chase.data.lens = 30
  target = bpy.data.objects.new("cam_chase_target", None)
  bpy.context.scene.collection.objects.link(chase)
  bpy.context.scene.collection.objects.link(target)
  tc = chase.constraints.new("TRACK_TO")
  tc.target, tc.track_axis, tc.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
  for f, (x, y, h) in enumerate(zip(ex, ey, heads), start=1):
    chase.location = (x - 15 * math.cos(h) - 4 * math.sin(h), y - 15 * math.sin(h) + 4 * math.cos(h), 6.5)
    target.location = (x + 14 * math.cos(h), y + 14 * math.sin(h), 0.0)
    chase.keyframe_insert("location", frame=f)
    target.keyframe_insert("location", frame=f)
  linear(chase)
  linear(target)
  cams["chase"] = chase

  top = bpy.data.objects.new("cam_top", bpy.data.cameras.new("cam_top"))
  top.data.type = "ORTHO"
  span = (r["left_edge"] + 1.0) - ((r["barrier"] if r["barrier"] is not None else r["right_edge"]) - 1.5)
  top.data.ortho_scale = max(48.0, span * 16 / 9 * 1.1)
  mid = 0.5 * ((r["left_edge"] + 1.0) + ((r["barrier"] if r["barrier"] is not None else r["right_edge"]) - 1.5))
  bpy.context.scene.collection.objects.link(top)
  for f, (j, h) in enumerate(zip(idx, heads), start=1):
    p = c[min(j + 6, len(c) - 1)]
    x, y, _ = offset(p, mid)
    top.location = (x, y, 60.0)
    top.rotation_euler = (0.0, 0.0, h)
    top.keyframe_insert("location", frame=f)
    top.keyframe_insert("rotation_euler", frame=f)
  linear(top)
  cams["top"] = top
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
  cu.materials.append(material("path", EGO_RGB, emit=2.0))
  bpy.context.scene.collection.objects.link(ob)
  lengths = [0.0]
  for a, b in zip(poses, poses[1:]):
    lengths.append(lengths[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
  total = lengths[-1] or 1.0
  for f in range(1, frames + 1):
    cu.bevel_factor_end = lengths[f - 1] / total
    cu.keyframe_insert("bevel_factor_end", frame=f)
  return ob


def key_frames(sc: dict) -> list[dict]:
  """One still per distinct event (closer than 0.15 s merges), plus the first and the last frame."""
  t = sc["t"]
  out = [{"frame": 1, "t": t[0], "label": "start"}]
  for e in sc["events"]:
    f = min(range(len(t)), key=lambda i: abs(t[i] - e["t"])) + 1
    if out and abs(out[-1]["t"] - e["t"]) < 0.15:
      out[-1]["label"] += "; " + e["label"]
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

  world = bpy.data.worlds.new("sky")
  world.use_nodes = True
  bg = world.node_tree.nodes["Background"]
  bg.inputs["Color"].default_value = (0.55, 0.68, 0.85, 1.0)
  bg.inputs["Strength"].default_value = 0.8
  scene.world = world
  sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
  sun.data.energy = 3.5
  sun.data.angle = math.radians(3)
  sun.rotation_euler = (math.radians(40), math.radians(10), math.radians(-35))
  scene.collection.objects.link(sun)

  build_road(sc)
  cars = collection("road_users")
  ghosts = collection("event_ghosts")
  ego_actor, others = sc["actors"][0], sc["actors"][1:]
  if vehicle is not None:
    ego = glb_car(vehicle, front, cars)
  else:
    ego = standin_car("ego", EGO_RGB, cars)
  keyframe_poses(ego, ego_actor["poses"])
  for a in others:
    rgb = PLANT_RGB if a["source"] == "plant" else ILLUSTRATIVE_RGB
    ob = standin_car(a["name"].replace(" ", "_"), rgb, cars)
    keyframe_poses(ob, a["poses"])

  keys = key_frames(sc)
  for k in keys[1:]:
    if k["label"] == "end":
      continue
    g = standin_car(f"ghost_{k['frame']:04d}", EGO_RGB, ghosts, alpha=0.28)
    x, y, h = ego_actor["poses"][k["frame"] - 1]
    g.location, g.rotation_euler = (x, y, 0.0), (0.0, 0.0, h)
    show_from(g, k["frame"] + 1)
  build_path(sc, frames)
  cams = build_cameras(sc)
  scene.camera = cams["chase"]
  return {"keys": keys, "cams": cams}


def render_setup(res: tuple[int, int], samples: int):
  s = bpy.context.scene
  s.render.engine = "CYCLES"
  s.cycles.device = "CPU"
  s.cycles.samples = samples
  s.cycles.use_denoising = True
  s.cycles.max_bounces = 4
  s.render.use_persistent_data = True
  s.render.resolution_x, s.render.resolution_y = res
  s.render.resolution_percentage = 100
  s.render.image_settings.file_format = "PNG"
  s.render.film_transparent = False


def render_frame(cam, frame: int, path: Path):
  s = bpy.context.scene
  s.camera = cam
  s.frame_set(frame)
  s.render.filepath = str(path)
  bpy.ops.render.render(write_still=True)


def main(argv: list[str]) -> int:
  argv = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("scene", type=Path, help="scene.json written by export_scene.py")
  ap.add_argument("--vehicle", type=Path, help="GLB of the ego car (default: the purchased mesh if present)")
  ap.add_argument("--standin", action="store_true", help="use the silhouette stand-in even if the GLB is present")
  ap.add_argument("--front", choices=["+x", "-x", "+y", "-y"], help="front of the GLB after import (default: found)")
  ap.add_argument("--stills", action="store_true", help="render the key-event frames from both cameras")
  ap.add_argument("--video", action="store_true", help="render every frame of the chase camera (and the top camera)")
  ap.add_argument("--res", default="1280x720", help="still resolution, WxH (default 1280x720)")
  ap.add_argument("--video-res", default="960x540", help="clip resolution, WxH (default 960x540)")
  ap.add_argument("--samples", type=int, default=24, help="Cycles samples for stills (clip: half)")
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
  bpy.ops.wm.save_as_mainfile(filepath=str(out / "scene.blend"))
  manifest = {"scene": sc["id"], "vehicle": "purchased mesh" if vehicle else "stand-in", "stills": [], "video": {}}

  if args.stills:
    render_setup(tuple(int(v) for v in args.res.split("x")), args.samples)
    for k in built["keys"]:
      for name, cam in built["cams"].items():
        p = out / "stills" / f"f{k['frame']:04d}_{name}.png"
        render_frame(cam, k["frame"], p)
        manifest["stills"].append({**k, "camera": name, "file": str(p.relative_to(out))})
  if args.video:
    render_setup(tuple(int(v) for v in args.video_res.split("x")), max(4, args.samples // 2))
    for name, cam in built["cams"].items():
      if name == "top":
        bpy.context.scene.render.resolution_x //= 2
        bpy.context.scene.render.resolution_y //= 2
      for f in range(1, len(sc["t"]) + 1):
        render_frame(cam, f, out / "frames" / name / f"{f:04d}.png")
      manifest["video"][name] = f"frames/{name}/%04d.png"
  (out / "render.json").write_text(json.dumps(manifest, indent=1))
  print(f"{sc['id']}: {out / 'scene.blend'}; {len(manifest['stills'])} stills; clip cameras {list(manifest['video'])}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
