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
import street_layout  # noqa: E402

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


def walk_rig(rig, poses, cycle_m: float = 1.45):
  """Play the rig's walk loop by the distance walked: one loop (two steps) every cycle_m metres, still when standing."""
  walk = bpy.data.actions[rig["walk_action"]]
  f0, f1 = walk.frame_range
  rig.animation_data_create()
  strip = rig.animation_data.nla_tracks.new().strips.new("walk", int(f0), walk)
  strip.use_animated_time = True
  dist = 0.0
  for f, p in enumerate(poses, start=1):
    if f > 1:
      dist += math.hypot(p[0] - poses[f - 2][0], p[1] - poses[f - 2][1])
    strip.strip_time = f0 + ((dist / cycle_m) % 1.0) * (f1 - f0)
    strip.keyframe_insert("strip_time", frame=f)
  for fc in fcurves(rig):
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


def centre_at(centre, s: float):
  i = min(max(int(round(s - centre[0][3])), 0), len(centre) - 1)
  return centre[i]


# ------------------------------------------------------------------------------------------------- road users
def headlights(root, coll, front: float = 2.25, energy: float = 4000):
  for y in (0.62, -0.62):
    lt = bpy.data.objects.new("headlight", bpy.data.lights.new("headlight", "SPOT"))
    lt.data.energy, lt.data.spot_size, lt.data.spot_blend = energy, math.radians(60), 0.5
    lt.data.color = (1.0, 0.95, 0.85)
    lt.parent = root
    lt.location = (front, y, 0.7)
    lt.rotation_euler = (0, math.radians(-88), 0)       # the spot points along +X, a little down
    coll.objects.link(lt)


def taillights(root, coll, rear: float, half: float = 0.62, z: float = 0.85):
  red = A.material("tail_lamp", (1.0, 0.04, 0.02), rough=0.3, emit=12.0)
  me = bpy.data.meshes.get("tail_lamp") or A.box_mesh("tail_lamp", 0.05, 0.28, 0.1, mat=red)
  for y in (half, -half):
    A.part("tail_lamp", me, root, coll, (rear, y, z))


def make_actor(a: dict, model, coll, lights: bool, night: bool = False, seed: str = ""):
  """A road user; lights: headlights and tail lamps (night, or poor visibility by day: dipped, dimmer)."""
  kind = a["kind"]
  name = a["name"].replace(" ", "_")
  limbs = None
  if kind in ("ego", "car"):
    rgb = EGO_RGB if kind == "ego" else tuple(a.get("paint") or (PLANT_RGB if a["source"] == "plant" else OTHER_RGB))
    body = A.paint(rgb)
    ob = model.instance(name, coll, body=body) if model else A.standin_car(name, coll, body=body)
    if lights and a["poses"][0] != a["poses"][-1]:      # parked cars stay dark
      headlights(ob, coll, energy=4000 if night else 1200)
      taillights(ob, coll, -2.32)
  elif kind == "truck":
    ob = A.truck(name, coll)
    if lights:
      headlights(ob, coll, 4.8, 4000 if night else 1200)
      taillights(ob, coll, -4.76, 1.05, 1.0)
  elif kind == "pedestrian":
    scanned = A.scanned_pedestrian(name, coll, seed, a.get("figure"))
    ob, limbs = scanned if scanned else A.pedestrian(name, coll)
  elif kind == "cyclist":
    ob = A.cyclist(name, coll)
  else:
    raise ValueError(kind)
  keyframe_poses(ob, a["poses"])
  if isinstance(limbs, bpy.types.Object):       # a scanned figure: its rig
    walk_rig(limbs, a["poses"])
  elif limbs:
    walk_cycle(limbs, a["poses"])
  return ob


# ------------------------------------------------------------------------------------------------- props
def sign_text(text: str, coll, loc, heading: float, size: float, rgb):
  """Text standing upright at loc, facing the ego's direction of travel, reading left to right."""
  cu = bpy.data.curves.new("sign_text", "FONT")
  cu.body = text
  cu.align_x, cu.align_y = "CENTER", "CENTER"
  cu.size = size
  cu.extrude = 0.005
  ob = bpy.data.objects.new("sign_text", cu)
  ob.location = loc
  ob.rotation_euler = (math.pi / 2, 0.0, heading - math.pi / 2)
  cu.materials.append(A.material(f"sign_ink_{'%02x%02x%02x' % tuple(int(255 * v) for v in rgb)}", rgb, rough=0.6))
  coll.objects.link(ob)
  return ob


SIGN_STYLES = {           # panel colour, ink colour, shape (MUTCD-like)
  "speed": ((0.92, 0.92, 0.9), (0.02, 0.02, 0.02), "rect"),
  "warning": ((0.95, 0.75, 0.05), (0.02, 0.02, 0.02), "diamond"),
  "works": ((0.95, 0.42, 0.05), (0.02, 0.02, 0.02), "diamond"),
  "guide": ((0.02, 0.35, 0.18), (0.95, 0.95, 0.95), "rect"),
}


def build_sign(p: dict, c, coll, k: int):
  cc = centre_at(c, p["s"])
  h = cc[2]
  x, y, _ = A.offset(cc, p.get("d", -10.0))
  panel_rgb, ink, shape = SIGN_STYLES[p.get("style", "warning")]
  grey = A.material("pole", (0.2, 0.2, 0.22), rough=0.5, metal=0.6)
  A.part("sign_post", A.cyl_mesh(f"signpost{k}", 0.04, 2.6, mat=grey), None, coll, (x, y, 1.3))
  panel = A.material(f"sign_{p.get('style')}", panel_rgb, rough=0.35, emit=0.15)
  size = 1.1 if shape == "diamond" else 1.0
  A.part("sign_panel", A.box_mesh(f"signpanel{k}", 0.04, size, size * (1.0 if shape == "diamond" else 1.25), 0.0,
                                  panel), None, coll, (x, y, 2.6 - (0 if shape == "rect" else size * 0.2)),
         (math.pi / 4, 0, h) if shape == "diamond" else (0, 0, h))
  zc = 2.6 + (size * 1.25 / 2 if shape == "rect" else size * 0.5)
  front = (x - 0.04 * math.cos(h), y - 0.04 * math.sin(h), zc)
  text = {"speed": f"SPEED\nLIMIT\n{p.get('text', '65')}", "works": "ROAD\nWORK"}.get(p.get("style"),
                                                                                      p.get("text", "").upper())
  if p.get("style") == "warning" and p.get("text") == "curve":   # a bent arrow instead of words
    black = A.material("sign_ink_050505", ink, rough=0.6)
    A.part("arrow_a", A.box_mesh(f"arrowa{k}", 0.02, 0.1, 0.45, 0.0, black), None, coll,
           (front[0], front[1], zc - 0.3), (0, 0, h))
    A.part("arrow_b", A.box_mesh(f"arrowb{k}", 0.02, 0.1, 0.4, 0.0, black), None, coll,
           (front[0], front[1], zc + 0.1), (math.radians(-35), 0, h))
  elif text:
    sign_text(text, coll, front, h, 0.22 if "\n" in text else 0.3, ink)


def build_props(sc: dict, coll, env: dict | None = None):
  env = env or {}
  c = sc["road"]["centre"]
  r = sc["road"]
  left, right = r["outer"]
  night = bool(env.get("night"))
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
      cs, sn = math.cos(h), math.sin(h)                 # the cross road: a flat quad with road UVs, just above
      corners = [(-w / 2, -80.0), (w / 2, -80.0), (w / 2, 80.0), (-w / 2, 80.0)]
      A.mesh_object(f"cross_road{k}", [(x + a * cs - b * sn, y + a * sn + b * cs, 0.155) for a, b in corners],
                    [(0, 1, 2, 3)], asphalt, coll, uvs=[(b, a) for a, b in corners])
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
      tar = A.material("tar", (0.16, 0.16, 0.17), rough=0.12)   # glossy sealant strip, lighter than the asphalt
      n = int(p["len"])
      verts, faces = [], []
      for i in range(n + 1):
        cc = centre_at(c, p["s"] + i)
        d = p["d0"] + (p["d1"] - p["d0"]) * i / n
        verts += [A.offset(cc, d + 0.2, 0.005), A.offset(cc, d - 0.2, 0.005)]
        if i:
          faces.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
      A.mesh_object("seam", verts, faces, tar, coll)
    elif kind == "posts":                       # white delineator posts with a reflector
      white = A.material("delineator", (0.85, 0.85, 0.82), rough=0.6)
      refl = A.material("reflector", (1.0, 0.75, 0.2), rough=0.2, emit=2.0 if night else 0.3)
      post = A.box_mesh(f"delin{k}", 0.1, 0.12, 1.0, 0.0, white)
      cap = A.box_mesh(f"delinr{k}", 0.11, 0.08, 0.12, 0.8, refl)
      root = A.empty("delineators", coll)
      s = c[0][3]
      while s < c[-1][3]:
        cc = centre_at(c, s)
        x, y, _ = A.offset(cc, p["d"])
        A.part("delineator", post, root, coll, (x, y, 0), (0, 0, cc[2]))
        A.part("reflector", cap, root, coll, (x, y, 0), (0, 0, cc[2]))
        s += p.get("every_m", 50)
    elif kind == "lamps":                       # a row of street lights curving over the road, lit at night
      root = A.empty("lighting_columns", coll)
      for j, q in enumerate(street_layout.lamp_row(sc, p)):
        A.lamp_post(f"road_lamp_{k}_{j}", coll, root, (q["x"], q["y"], 0.0), q["yaw"], night, height=10.0,
                    reach=p.get("reach_m", 2.6), light="SPOT", energy=9000.0)
    elif kind == "sign":
      build_sign(p, c, coll, k)
    elif kind == "gantry":                      # an overhead guide sign on two posts across the carriageway
      cc = centre_at(c, p["s"])
      h = cc[2]
      grey = A.material("gantry", (0.55, 0.56, 0.58), rough=0.4, metal=0.7)
      lo, hi = (r["barrier"] if r.get("barrier") is not None else r["right_edge"]) - 0.8, r["left_edge"] + 1.2
      for d in (lo, hi):
        x, y, _ = A.offset(cc, d)
        A.part("gantry_post", A.cyl_mesh(f"gpost{k}{d:.0f}", 0.2, 7.2, mat=grey), None, coll, (x, y, 3.6))
      mx, my, _ = A.offset(cc, 0.5 * (lo + hi))
      A.part("gantry_beam", A.box_mesh(f"gbeam{k}", 0.6, hi - lo, 0.6, 6.6, grey), None, coll, (mx, my, 0), (0, 0, h))
      green, _, _ = SIGN_STYLES["guide"]
      px, py, _ = A.offset(cc, -r["lane_width"])
      A.part("gantry_panel", A.box_mesh(f"gpanel{k}", 0.08, 5.0, 2.2, 5.6, A.material("sign_guide", green, rough=0.35,
                                                                                        emit=0.15)),
             None, coll, (px - 0.4 * math.cos(h), py - 0.4 * math.sin(h), 0), (0, 0, h))
      sign_text(p.get("text", "EXIT"), coll, (px - 0.46 * math.cos(h), py - 0.46 * math.sin(h), 6.7), h, 0.6,
                (0.95, 0.95, 0.95))
    elif kind == "barrels":                     # orange and white channelising drums
      orange = A.material("drum_orange", (0.95, 0.3, 0.03), rough=0.5, emit=0.2)
      white = A.material("drum_white", (0.9, 0.9, 0.88), rough=0.4, emit=0.6 if night else 0.1)
      drum = A.cyl_mesh(f"drum{k}", 0.3, 0.95, mat=orange, segs=14)
      band = A.cyl_mesh(f"band{k}", 0.305, 0.12, mat=white, segs=14)
      s = p["from_s"]
      while s <= p["to_s"]:
        x, y, _ = A.offset(centre_at(c, s), p["d"])
        A.part("drum", drum, None, coll, (x, y, 0.475))
        for z in (0.35, 0.7):
          A.part("drum_band", band, None, coll, (x, y, z))
        s += p.get("every_m", 12)
    elif kind == "tunnel":                      # TC-18: walls, a roof and a portal over from_s..to_s, lit inside
      wall = A.material("tunnel_wall", (0.62, 0.61, 0.58), rough=0.7)
      lamp = A.material("tunnel_lamp", (1.0, 0.86, 0.6), rough=0.3, emit=30.0)
      lo, hi = (r["barrier"] if r.get("barrier") is not None else right) - 0.5, left + 0.5
      height = p.get("height", 8.0)                 # above the chase camera (street_layout.chase_rig: 6.5 m)
      n = max(int((p["to_s"] - p["from_s"]) / 2.0), 1)
      ss = [p["from_s"] + (p["to_s"] - p["from_s"]) * i / n for i in range(n + 1)]
      earth = A.material("tunnel_earth", (0.28, 0.4, 0.15), rough=0.95)
      overhead = bpy.data.collections.get("overhead")   # hidden from the top camera, which looks through the roof
      if overhead is None:
        overhead = bpy.data.collections.new("overhead")
        bpy.context.scene.collection.children.link(overhead)
      cover = height + 2.5                            # the hill the tunnel runs through: a cover and two slopes
      for name, d0, z0, d1, z1, mat in (("tunnel_wall_r", lo, 0.0, lo, height, wall),
                                        ("tunnel_wall_l", hi, 0.0, hi, height, wall),
                                        ("tunnel_roof", lo, height, hi, height, wall),
                                        ("tunnel_cover", lo - 1.0, cover, hi + 1.0, cover, earth),
                                        ("tunnel_slope_r", lo - 1.0, cover, lo - 40.0, -0.2, earth),
                                        ("tunnel_slope_l", hi + 40.0, -0.2, hi + 1.0, cover, earth)):
        verts, faces = [], []
        for i, s in enumerate(ss):
          cc = centre_at(c, s)
          verts += [A.offset(cc, d0, z0), A.offset(cc, d1, z1)]
          if i:
            faces.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
        A.mesh_object(f"{name}{k}", verts, faces, mat, overhead if name in ("tunnel_roof", "tunnel_cover") else coll)
      cc = centre_at(c, p["from_s"])                  # the portal: a face wall above and beside the opening
      mx, my, _ = A.offset(cc, 0.5 * (lo + hi))
      A.part("tunnel_portal", A.box_mesh(f"portal{k}", 1.5, hi - lo + 8.0, 3.0, height, concrete), None, coll,
             (mx, my, 0), (0, 0, cc[2]))
      for d in (lo - 2.0, hi + 2.0):
        px, py, _ = A.offset(cc, d)
        A.part("tunnel_portal", A.box_mesh(f"portalw{k}{d:.0f}", 1.5, 4.0, cover + 0.5, 0.0, concrete), None, coll,
               (px, py, 0), (0, 0, cc[2]))
      lum = A.box_mesh(f"tlum{k}", 1.2, 0.15, 0.1, -0.1, lamp)
      s = p["from_s"] + 4.0
      while s < p["to_s"]:                          # a line of luminaires on each wall, with a few real lights
        cc = centre_at(c, s)
        for d in (lo + 0.1, hi - 0.1):
          x, y, _ = A.offset(cc, d)
          A.part("tunnel_luminaire", lum, None, coll, (x, y, height - 0.6), (0, 0, cc[2]))
        if int((s - p["from_s"]) / 8.0) % 3 == 0:
          lt = bpy.data.objects.new("tunnel_light", bpy.data.lights.new("tunnel_light", "POINT"))
          lt.data.energy, lt.data.color, lt.data.shadow_soft_size = 2500, (1.0, 0.85, 0.6), 0.5
          lt.location = A.offset(cc, 0.5 * (lo + hi), height - 1.0)
          coll.objects.link(lt)
        s += 8.0
    elif kind == "gore":                        # TC-31: chevron hatching where a lane splits off at d, widening to width
      white = A.material("paint_white", (0.85, 0.85, 0.82), rough=0.5)
      side = 1 if p.get("side", "right") == "left" else -1
      length = p["to_s"] - p["from_s"]

      def edge(s):
        return side * p.get("width", 3.0) * min(max((s - p["from_s"]) / length, 0.0), 1.0)

      for which in (0, 1):                      # the two border lines of the hatched area
        verts, faces = [], []
        n = max(int(length), 1)
        for i in range(n + 1):
          s = p["from_s"] + length * i / n
          d = p["d"] + (edge(s) if which else 0.0)
          cc = centre_at(c, s)
          verts += [A.offset(cc, d + 0.1, 0.012), A.offset(cc, d - 0.1, 0.012)]
          if i:
            faces.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
        A.mesh_object(f"gore_line{k}{which}", verts, faces, white, coll)
      s = p["from_s"] + 8.0
      while s < p["to_s"]:                      # diagonal bars across the widening area
        w = abs(edge(s))
        if w > 0.4:
          cc = centre_at(c, s + 0.5 * w)
          x, y, _ = A.offset(cc, p["d"] + 0.5 * edge(s))
          bar = A.box_mesh(f"gore{k}{s:.0f}", 0.45, w * 1.35, 0.01, 0.012, white)
          A.part("gore_bar", bar, None, coll, (x, y, 0), (0, 0, cc[2] + side * math.radians(45)))
        s += 6.0
    elif kind == "windsock":                    # TC-15: an orange and white sock on a mast, blown across the road
      grey = A.material("pole", (0.2, 0.2, 0.22), rough=0.5, metal=0.6)
      orange = A.material("sock_orange", (0.95, 0.3, 0.03), rough=0.6, emit=0.15)
      whitem = A.material("sock_white", (0.92, 0.92, 0.9), rough=0.6)
      cc = centre_at(c, p["s"])
      x, y, _ = A.offset(cc, p["d"])
      A.part("windsock_mast", A.cyl_mesh(f"wmast{k}", 0.06, 6.0, mat=grey), None, coll, (x, y, 3.0))
      toward = cc[2] + (math.pi / 2 if p.get("toward", "left") == "left" else -math.pi / 2)
      for i in range(5):                        # five bands, tapering, pointing downwind
        rr = 0.38 - 0.05 * i
        bx, by = x + (0.35 + 0.5 * i) * math.cos(toward), y + (0.35 + 0.5 * i) * math.sin(toward)
        band = A.cyl_mesh(f"wband{k}{i}", rr, 0.5, axis="X", mat=orange if i % 2 == 0 else whitem, segs=12,
                          r2=rr - 0.05)
        A.part("windsock_band", band, None, coll, (bx, by, 5.75 - 0.06 * i), (0.0, 0.12, toward))
    else:
      raise ValueError(kind)


# ------------------------------------------------------------------------------------------------- cameras, path
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
  back, up, side, ahead = street_layout.chase_rig(sc)      # street_layout keeps tall furniture out of this view

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
  assets = A.Assets()
  A.build_environment(env, sc["actors"][0]["poses"][0][2], assets)
  A.build_road(sc["road"], env, assets)
  furniture = street_layout.layout(sc) if sc["road"]["scenery"] == "urban" else None
  A.build_scenery(sc["road"], env, assets, furniture=furniture)
  props = bpy.data.collections.new("props")
  scene.collection.children.link(props)
  build_props(sc, props, env)

  model = A.CarModel(vehicle, front) if vehicle else None
  users = bpy.data.collections.new("road_users")
  scene.collection.children.link(users)
  lights = bool(env.get("night")) or (env.get("visibility_m") or 1e9) < 1000
  seed = sc.get("variant_of") or sc["id"]       # a condition variant draws the same people as its base scene
  obs = [make_actor(a, model, users, lights, bool(env.get("night")), seed) for a in sc["actors"]]
  A.setup_glare(env)

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
  A.build_weather(env, obs[0], sc["road"]["centre"], frames, sc["fps"], cams=(cams["chase"], cams["driver"]))
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
  overhead = bpy.data.collections.get("overhead")
  if overhead:                                  # a tunnel roof hides the road from above
    overhead.hide_render = cam.name == "cam_top"
  weather = bpy.data.collections.get("weather")
  if weather:                                   # weather reads from the road; from above it hides the layout
    weather.hide_render = cam.name == "cam_top"
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
