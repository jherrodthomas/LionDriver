"""Blender building blocks of the hazardous-event scenes: materials, the road from its cross-section, scenery, the
environment (sun, sky, wet road, night), the reference car from the purchased mesh (instanced, repainted per road
user), and simple procedural road users (truck, pedestrian, cyclist) and the silhouette stand-in car.

Imported by hazard_scene.py; runs in Blender (bpy). Units are metres; a road user's origin is on the ground under
its body centre, forward +X.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
SILHOUETTE = HERE.parent / "figures" / "corolla-e210-silhouette.json"


# ------------------------------------------------------------------------------------------------- materials
def material(name: str, rgb, rough: float = 0.5, metal: float = 0.0, alpha: float = 1.0, emit: float = 0.0,
             coat: float = 0.0):
  m = bpy.data.materials.get(name)
  if m:
    return m
  m = bpy.data.materials.new(name)
  m.use_nodes = True
  b = m.node_tree.nodes.get("Principled BSDF")
  b.inputs["Base Color"].default_value = (*rgb, 1.0)
  b.inputs["Roughness"].default_value = rough
  b.inputs["Metallic"].default_value = metal
  b.inputs["Alpha"].default_value = alpha
  if coat and "Coat Weight" in b.inputs:
    b.inputs["Coat Weight"].default_value = coat
  if emit:
    b.inputs["Emission Color"].default_value = (*rgb, 1.0)
    b.inputs["Emission Strength"].default_value = emit
  m.diffuse_color = (*rgb, alpha)
  return m


def paint(rgb) -> bpy.types.Material:
  return material("paint_%02x%02x%02x" % tuple(int(255 * c) for c in rgb), rgb, rough=0.22, metal=0.55, coat=1.0)


def ghost_material(rgb):
  return material("ghost", rgb, rough=0.4, alpha=0.25)


def facade_material(name: str, wall, glass=(0.05, 0.07, 0.09), lit: float = 0.0):
  """A wall with a grid of windows (brick texture: bricks are windows, mortar is wall), in object space."""
  m = bpy.data.materials.get(name)
  if m:
    return m
  m = bpy.data.materials.new(name)
  m.use_nodes = True
  nt = m.node_tree
  b = nt.nodes["Principled BSDF"]
  tc = nt.nodes.new("ShaderNodeTexCoord")
  br = nt.nodes.new("ShaderNodeTexBrick")
  br.offset = 0.0
  br.inputs["Scale"].default_value = 1.0
  br.inputs["Mortar Size"].default_value = 0.6
  br.inputs["Brick Width"].default_value = 2.6
  br.inputs["Row Height"].default_value = 3.2
  br.inputs["Color1"].default_value = (*glass, 1)
  br.inputs["Color2"].default_value = (*glass, 1)
  br.inputs["Mortar"].default_value = (*wall, 1)
  nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
  nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
  nt.links.new(br.outputs["Fac"], b.inputs["Roughness"])
  if lit:
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(br.outputs["Fac"], inv.inputs[1])
    nt.links.new(inv.outputs[0], b.inputs["Emission Strength"])
    b.inputs["Emission Color"].default_value = (1.0, 0.8, 0.5, 1)
  return m


# ------------------------------------------------------------------------------------------------- meshes
def mesh_object(name: str, verts, faces, mat=None, coll=None, smooth=False):
  me = bpy.data.meshes.new(name)
  me.from_pydata(verts, [], faces)
  me.update()
  if smooth:
    for p in me.polygons:
      p.use_smooth = True
  ob = bpy.data.objects.new(name, me)
  (coll or bpy.context.scene.collection).objects.link(ob)
  if mat:
    me.materials.append(mat)
  return ob


def box_mesh(name: str, sx: float, sy: float, sz: float, z0: float = 0.0, mat=None):
  """A box mesh centred on X and Y, from z0 to z0 + sz."""
  me = bpy.data.meshes.new(name)
  bm = bmesh.new()
  bmesh.ops.create_cube(bm, size=1.0)
  bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
  bmesh.ops.translate(bm, vec=(0, 0, z0 + sz / 2), verts=bm.verts)
  bm.to_mesh(me)
  bm.free()
  if mat:
    me.materials.append(mat)
  return me


def cyl_mesh(name: str, r: float, length: float, axis: str = "Z", segs: int = 16, mat=None):
  me = bpy.data.meshes.new(name)
  bm = bmesh.new()
  bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r, depth=length)
  rot = {"Z": Matrix.Identity(3), "X": Matrix.Rotation(math.pi / 2, 3, "Y"), "Y": Matrix.Rotation(math.pi / 2, 3, "X")}
  bmesh.ops.rotate(bm, matrix=rot[axis], verts=bm.verts)
  for f in bm.faces:
    f.smooth = True
  bm.to_mesh(me)
  bm.free()
  if mat:
    me.materials.append(mat)
  return me


def sphere_mesh(name: str, r: float, subdiv: int = 2, mat=None):
  me = bpy.data.meshes.new(name)
  bm = bmesh.new()
  bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=r)
  for f in bm.faces:
    f.smooth = True
  bm.to_mesh(me)
  bm.free()
  if mat:
    me.materials.append(mat)
  return me


def part(name: str, me, parent, coll, loc=(0, 0, 0), rot=(0, 0, 0)):
  ob = bpy.data.objects.new(name, me)
  ob.parent = parent
  ob.location, ob.rotation_euler = loc, rot
  coll.objects.link(ob)
  return ob


def empty(name: str, coll):
  ob = bpy.data.objects.new(name, None)
  coll.objects.link(ob)
  return ob


# ------------------------------------------------------------------------------------------------- road
def offset(c, d: float, z: float = 0.0):
  x, y, h = c[0], c[1], c[2]
  return (x - d * math.sin(h), y + d * math.cos(h), z)


def strip(name, centre, d0: float, d1: float, z: float, mat, coll, s_ranges=None, z1: float | None = None):
  """A ribbon between lateral offsets d0 and d1 (left positive) at height z (sloping to z1 at d1 if given);
  s_ranges limits it to dashes."""
  verts, faces = [], []
  z1 = z if z1 is None else z1
  for i in range(len(centre) - 1):
    a, b = centre[i], centre[i + 1]
    if s_ranges is not None and not any(lo <= a[3] < hi for lo, hi in s_ranges):
      continue
    k = len(verts)
    verts += [offset(a, d0, z), offset(a, d1, z1), offset(b, d1, z1), offset(b, d0, z)]
    faces.append((k, k + 1, k + 2, k + 3))
  return mesh_object(name, verts, faces, mat, coll)


def wall(name, centre, d: float, z0: float, z1: float, mat, coll, thick: float = 0.0):
  verts, faces = [], []
  for i, p in enumerate(centre):
    verts += [offset(p, d, z0), offset(p, d, z1), offset(p, d - thick, z1), offset(p, d - thick, z0)]
    if i:
      k = 4 * i
      for j in range(4 if thick else 1):
        faces.append((k - 4 + j, k - 4 + (j + 1) % 4, k + (j + 1) % 4, k + j))
  return mesh_object(name, verts, faces, mat, coll)


def dash_ranges(c, dash: float, gap: float):
  s0, s1 = c[0][3], c[-1][3]
  return [(s, s + dash) for s in [s0 + (dash + gap) * i for i in range(int((s1 - s0) / (dash + gap)) + 1)]]


def build_road(r: dict, env: dict):
  """The road from its cross-section (export_scene.py road_layout): surfaces, markings, kerbs, barrier, crossings."""
  c = r["centre"]
  coll = bpy.data.collections.new("road")
  bpy.context.scene.collection.children.link(coll)
  wet = env.get("wet", False)
  asphalt = material("asphalt_wet" if wet else "asphalt", (0.03, 0.03, 0.035) if wet else (0.05, 0.05, 0.055),
                     rough=0.12 if wet else 0.85)
  mats = {
    "asphalt": asphalt,
    "shoulder": material("shoulder", (0.08, 0.08, 0.085), rough=0.12 if wet else 0.9),
    "gravel": material("gravel", (0.22, 0.2, 0.17), rough=1.0),
    "parking": asphalt,
    "sidewalk": material("sidewalk", (0.42, 0.41, 0.39), rough=0.9),
    "grass": material("grass", (0.08, 0.15, 0.05), rough=1.0),
    "median": material("median", (0.08, 0.15, 0.05), rough=1.0),
  }
  white = material("paint_white", (0.85, 0.85, 0.82), rough=0.5)
  yellow = material("paint_yellow", (0.85, 0.6, 0.05), rough=0.5)
  worn = material("paint_worn", (0.3, 0.3, 0.29), rough=0.8)
  kerb = material("kerb", (0.55, 0.55, 0.52), rough=0.8)
  steel = material("barrier", (0.55, 0.57, 0.6), rough=0.35, metal=0.8)

  for k, sfc in enumerate(r["surfaces"]):
    z = sfc.get("z", 0.0)
    strip(f"{sfc['kind']}_{k}", c, sfc["d0"], sfc["d1"], z, mats[sfc["kind"]], coll)
    if sfc["kind"] == "sidewalk":                # kerb face toward the road
      wall(f"kerb_{k}", c, min(sfc["d0"], sfc["d1"], key=abs), 0.0, z, kerb, coll)
  for k, mk in enumerate(r["markings"]):
    col = {"white": white, "yellow": yellow}[mk["colour"]]
    if mk.get("worn"):
      col = worn
    rng = None if mk["style"] == "solid" else dash_ranges(c, *mk.get("dash", (3.0, 9.0)))
    w = mk.get("width", 0.15)
    strip(f"line_{k}", c, mk["d"] + w / 2, mk["d"] - w / 2, 0.006, col, coll, rng)
  for k, s in enumerate(r.get("crosswalks", [])):
    near = [p for p in c if s - 2.0 <= p[3] <= s + 2.0]
    if len(near) < 2:
      continue
    d0, d1 = r["carriageway"]
    d = d1
    while d < d0 - 0.3:
      strip(f"zebra_{k}_{d:.1f}", near, d + 0.5, d, 0.006, white, coll)
      d += 1.0
    stop = [p for p in c if s - 4.0 <= p[3] <= s - 3.6]
    if len(stop) >= 2:
      strip(f"stop_line_{k}", stop, 0.0 + r["lane_width"] / 2, -r["lane_width"] / 2, 0.006, white, coll)
  b = r.get("barrier")
  if b is not None:
    wall("barrier_rail", c, b, 0.5, 0.82, steel, coll, thick=0.06)
    me = box_mesh("post", 0.12, 0.12, 0.7, mat=steel)
    posts = empty("barrier_posts", coll)
    for p in c[::2]:
      x, y, _ = offset(p, b - 0.15)
      part("post", me, posts, coll, (x, y, 0))
  return coll


def build_scenery(r: dict, env: dict, seed: int = 7):
  """Trees, buildings and street lights beside the road, as the road type asks."""
  rnd = random.Random(seed)
  c = r["centre"]
  coll = bpy.data.collections.new("scenery")
  bpy.context.scene.collection.children.link(coll)
  kind = r["scenery"]
  left_out, right_out = r["outer"]
  if kind in ("trees", "urban"):
    trunk = cyl_mesh("trunk", 0.18, 3.0, mat=material("bark", (0.12, 0.08, 0.05), rough=1.0))
    crowns = [sphere_mesh(f"crown_{k}", 2.2 + 0.4 * k, 2, material(f"leaves_{k}", g, rough=1.0))
              for k, g in enumerate([(0.06, 0.14, 0.04), (0.08, 0.17, 0.05), (0.05, 0.11, 0.035)])]
    root = empty("trees", coll)
    step = 14.0 if kind == "trees" else 18.0
    for side, d_base in ((1, left_out + (3.5 if kind == "trees" else -1.2)),
                         (-1, right_out - (3.5 if kind == "trees" else -1.2))):
      s = c[0][3] + rnd.uniform(0, step)
      while s < c[-1][3]:
        p = c[min(int((s - c[0][3]) / (c[1][3] - c[0][3])), len(c) - 1)]
        d = d_base + side * rnd.uniform(0, 6.0 if kind == "trees" else 0.3)
        x, y, _ = offset(p, d)
        sc = rnd.uniform(0.8, 1.3) * (0.55 if kind == "urban" else 1.0)
        t = part("tree", trunk, root, coll, (x, y, 1.5 * sc))
        t.scale = (sc, sc, sc)
        cr = part("crown", rnd.choice(crowns), root, coll, (x, y, 3.0 * sc + 1.6 * sc))
        cr.scale = (sc, sc, sc * 1.15)
        s += step * rnd.uniform(0.6, 1.4)
  if kind == "urban":
    night = env.get("night", False)
    walls = [(0.55, 0.5, 0.45), (0.45, 0.42, 0.4), (0.62, 0.58, 0.5), (0.35, 0.33, 0.33), (0.5, 0.38, 0.3)]
    facades = [facade_material(f"facade_{k}", w, lit=1.5 if night else 0.0) for k, w in enumerate(walls)]
    root = empty("buildings", coll)
    for side, d_face in ((1, left_out + 1.0), (-1, right_out - 1.0)):
      s = c[0][3]
      while s < c[-1][3]:
        wdt = rnd.uniform(14, 26)
        hgt = rnd.choice([9, 12, 15, 18, 24, 30])
        dep = 16.0
        mid = s + wdt / 2
        p = c[min(int((mid - c[0][3]) / (c[1][3] - c[0][3])), len(c) - 1)]
        x, y, _ = offset(p, d_face + side * dep / 2)
        me = box_mesh(f"bld_{side}_{s:.0f}", wdt - 1.5, dep, hgt, mat=rnd.choice(facades))
        ob = part("building", me, root, coll, (x, y, 0), (0, 0, p[2]))
        s += wdt + (12.0 if r.get("crosswalks") and any(abs(mid - cs) < 14 for cs in r["crosswalks"]) else 0.0)
    pole = cyl_mesh("lamp_pole", 0.08, 7.0, mat=material("pole", (0.2, 0.2, 0.22), rough=0.5, metal=0.6))
    lroot = empty("street_lights", coll)
    for s in range(int(c[0][3]) + 10, int(c[-1][3]), 30):
      p = c[min(int((s - c[0][3]) / (c[1][3] - c[0][3])), len(c) - 1)]
      for d in (left_out - 0.6, right_out + 0.6):
        x, y, _ = offset(p, d)
        part("lamp", pole, lroot, coll, (x, y, 3.5))
        if night:
          lt = bpy.data.objects.new("street_light", bpy.data.lights.new("street_light", "POINT"))
          lt.data.energy, lt.data.color, lt.data.shadow_soft_size = 1500, (1.0, 0.82, 0.6), 0.3
          lt.location = offset(p, d - 1.0 if d > 0 else d + 1.0, 7.0)
          coll.objects.link(lt)
  return coll


# ------------------------------------------------------------------------------------------------- environment
def build_environment(env: dict, heading: float):
  """Sky and sun. env['sun']: 'behind' (default), 'ahead' (low sun in the driver's eyes: glare) or 'side';
  env['night']: no sun, dim sky; env['fog']: volumetric haze. heading: road heading at the ego's start."""
  scene = bpy.context.scene
  world = bpy.data.worlds.new("sky")
  world.use_nodes = True
  nodes, links = world.node_tree.nodes, world.node_tree.links
  bg = nodes["Background"]
  night = env.get("night", False)
  where = env.get("sun", "behind")
  elev = math.radians(env.get("sun_elevation", (12.0 if env.get("urban") else 4.0) if where == "ahead" else
                               (25.0 if env.get("urban") else 9.0)))
  az = heading + {"behind": math.radians(150), "ahead": math.radians(-6), "side": math.radians(80)}[where]
  # the sun lamp points from the sun toward the scene: from direction (az, elev)
  sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
  scene.collection.objects.link(sun)
  d = (math.cos(elev) * math.cos(az), math.cos(elev) * math.sin(az), math.sin(elev))
  sun.rotation_euler = _track(d)
  sun.data.angle = math.radians(1.0)
  if night:                                     # moonlit sky: dark blue ambient and a faint cool key light
    bg.inputs["Color"].default_value = (0.02, 0.03, 0.07, 1.0)
    bg.inputs["Strength"].default_value = 1.5
    sun.data.energy = 0.25
    sun.data.color = (0.6, 0.7, 1.0)
    sun.rotation_euler = _track((math.cos(heading + 2.2), math.sin(heading + 2.2), 0.6))
  else:
    try:
      sky = nodes.new("ShaderNodeTexSky")
      try:
        sky.sky_type = "NISHITA"
      except TypeError:
        pass
      sky.sun_elevation = elev
      # Nishita sun_rotation: azimuth measured from +Y toward -X (Blender's sky convention)
      sky.sun_rotation = (math.pi / 2 - az) % (2 * math.pi)
      sky.sun_disc = where == "ahead"
      sky.sun_intensity = 0.6
      links.new(sky.outputs["Color"], bg.inputs["Color"])
      bg.inputs["Strength"].default_value = 0.3 if env.get("urban") else 0.15
    except (RuntimeError, AttributeError, KeyError):
      bg.inputs["Color"].default_value = (0.55, 0.68, 0.85, 1.0)
      bg.inputs["Strength"].default_value = 0.8
    sun.data.energy = 2.6 if where != "ahead" else 3.2
    sun.data.color = (1.0, 0.78, 0.55)
  if env.get("fog"):
    vol = nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = env["fog"]
    vol.inputs["Color"].default_value = (0.8, 0.8, 0.82, 1.0)
    links.new(vol.outputs["Volume"], nodes["World Output"].inputs["Volume"])
  scene.world = world
  try:
    scene.view_settings.look = "AgX - Medium High Contrast"
  except TypeError:
    pass
  return sun


def _track(direction):
  """Euler rotation that points a lamp's -Z along -direction (toward the scene)."""
  from mathutils import Vector
  return Vector(direction).to_track_quat("Z", "Y").to_euler()


# ------------------------------------------------------------------------------------------------- road users
class CarModel:
  """The purchased mesh, centred on the ground and facing +X, kept out of the scene as a template; each road user is
  a set of objects sharing its mesh data, with the body paint swapped per object."""

  def __init__(self, path: Path, front: str | None):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()
    meshes = [o for o in new if o.type == "MESH"]
    pts = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    ext = [hi[i] - lo[i] for i in range(3)]
    along = 0 if ext[0] >= ext[1] else 1
    if front is None:
      # the bonnet end is lower than the boot end (silhouette: 0.87 m against 1.15 m over the outer quarters)
      q = 0.25 * ext[along]
      def top(zs):
        zs = sorted(zs)
        return zs[int(0.98 * (len(zs) - 1))] if zs else 0.0
      near = top([p[2] for p in pts if p[along] < lo[along] + q])
      far = top([p[2] for p in pts if p[along] > hi[along] - q])
      front = ("-" if near < far else "+") + "xy"[along]
    yaw = {"+x": 0.0, "-x": math.pi, "+y": -math.pi / 2, "-y": math.pi / 2}[front]
    t = Matrix.Rotation(yaw, 4, "Z") @ Matrix.Translation((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))
    self.parts = [(o.data, t @ o.matrix_world) for o in meshes]
    for _, m in self.parts:
      pass
    for o in new:
      bpy.data.objects.remove(o, do_unlink=True)
    for me, _ in self.parts:
      me.use_fake_user = True
    self.front, self.extent = front, ext
    print(f"vehicle: {path.name}, front {front}, extent {ext[0]:.2f} x {ext[1]:.2f} x {ext[2]:.2f} m")

  def instance(self, name: str, coll, body=None, override=None):
    root = empty(name, coll)
    for k, (me, m) in enumerate(self.parts):
      ob = bpy.data.objects.new(f"{name}.{k:02d}", me)
      ob.parent = root
      ob.matrix_basis = m
      coll.objects.link(ob)
      for slot in ob.material_slots:
        if override is not None or (body is not None and slot.material and slot.material.name.startswith("body")):
          slot.link = "OBJECT"
          slot.material = override if override is not None else body
    return root


def standin_mesh():
  """A car body lofted from the reference car's top and side outlines: forward +X, ground at Z = 0."""
  me = bpy.data.meshes.get("standin_body")
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
  for first, sign in ((0, -1), (ring, 1)):      # end caps as fans round their centre
    cidx = len(verts)
    verts.append(tuple(sum(verts[first + j][i] for j in range(n)) / n for i in range(3)))
    for j in range(n):
      a, b = first + j, first + (j + 1) % n
      faces.append((cidx, a, b) if sign > 0 else (cidx, b, a))
      mats.append(0)
  me = bpy.data.meshes.new("standin_body")
  me.from_pydata(verts, [], faces)
  for p, m in zip(me.polygons, mats):
    p.material_index = m
    p.use_smooth = True
  me.update()
  me.materials.append(material("standin_paint", (0.5, 0.5, 0.5), rough=0.25, metal=0.4))
  me.materials.append(material("standin_glass", (0.03, 0.04, 0.05), rough=0.05))
  return me


def standin_car(name: str, coll, body=None, override=None):
  root = empty(name, coll)
  ob = part(f"{name}_body", standin_mesh(), root, coll)
  for k, slot in enumerate(ob.material_slots):
    if override is not None or (body is not None and k == 0):
      slot.link = "OBJECT"
      slot.material = override if override is not None else body
  sil = json.loads(SILHOUETTE.read_text())
  tyre = material("tyre", (0.02, 0.02, 0.02), rough=0.9)
  wm = bpy.data.meshes.get("standin_wheel") or cyl_mesh("standin_wheel", sil["r_tire"], 0.22, "Y", 24, tyre)
  for wh in sil["wheels"]:
    w = part(f"{name}_{wh['name']}", wm, root, coll, (-wh["y"], wh["x"] * 1.04, sil["r_tire"]))
    if override is not None:
      w.material_slots[0].link = "OBJECT"
      w.material_slots[0].material = override
  return root


def truck(name: str, coll, colour=(0.85, 0.85, 0.83), length: float = 9.5):
  """A rigid box truck: cab at +X, cargo box behind."""
  root = empty(name, coll)
  body = material("truck_box", colour, rough=0.6)
  cab = material("truck_cab", (0.75, 0.75, 0.78), rough=0.3, metal=0.3)
  dark = material("truck_dark", (0.03, 0.03, 0.035), rough=0.6)
  glass = material("truck_glass", (0.02, 0.03, 0.04), rough=0.05)
  box_len = length - 2.4
  part(f"{name}_box", box_mesh(f"{name}_boxm", box_len, 2.5, 2.7, 1.05, body), root, coll, (-length / 2 + box_len / 2, 0, 0))
  part(f"{name}_cab", box_mesh(f"{name}_cabm", 2.2, 2.4, 1.9, 1.0, cab), root, coll, (length / 2 - 1.2, 0, 0))
  part(f"{name}_ws", box_mesh(f"{name}_wsm", 0.05, 2.2, 0.8, 2.0, glass), root, coll, (length / 2 - 0.08, 0, 0))
  part(f"{name}_chassis", box_mesh(f"{name}_chm", length - 0.4, 2.0, 0.35, 0.65, dark), root, coll)
  wm = cyl_mesh(f"{name}_wheel", 0.5, 0.35, "Y", 20, dark)
  for x in (length / 2 - 1.3, -length / 2 + 2.0, -length / 2 + 3.3):
    for y in (1.05, -1.05):
      part(f"{name}_w", wm, root, coll, (x, y, 0.5))
  return root


def pedestrian(name: str, coll, shirt=(0.15, 0.25, 0.45), trousers=(0.08, 0.08, 0.1)):
  """A walking figure 1.75 m tall facing +X; returns the root and its legs and arms for the walk cycle."""
  root = empty(name, coll)
  skin = material("skin", (0.55, 0.38, 0.28), rough=0.6)
  top = material(f"shirt_{name}", shirt, rough=0.8)
  bottom = material(f"trousers_{name}", trousers, rough=0.8)
  part(f"{name}_torso", cyl_mesh(f"{name}_torsom", 0.19, 0.62, mat=top), root, coll, (0, 0, 1.2))
  part(f"{name}_head", sphere_mesh(f"{name}_headm", 0.12, 2, skin), root, coll, (0, 0, 1.63))
  limbs = []
  for k, y in enumerate((0.1, -0.1)):
    hip = empty(f"{name}_hip{k}", coll)
    hip.parent, hip.location = root, (0, y, 0.9)
    part(f"{name}_leg{k}", cyl_mesh(f"{name}_legm{k}", 0.075, 0.88, mat=bottom), hip, coll, (0, 0, -0.44))
    sh = empty(f"{name}_shoulder{k}", coll)
    sh.parent, sh.location = root, (0, y * 2.3, 1.48)
    part(f"{name}_arm{k}", cyl_mesh(f"{name}_armm{k}", 0.05, 0.62, mat=top), sh, coll, (0, 0, -0.31))
    limbs.append((hip, sh))
  return root, limbs


def cyclist(name: str, coll, shirt=(0.6, 0.1, 0.1)):
  """A bicycle 1.8 m long with its rider, facing +X."""
  root = empty(name, coll)
  frame = material("bike_frame", (0.1, 0.3, 0.6), rough=0.4, metal=0.5)
  tyre = material("tyre", (0.02, 0.02, 0.02), rough=0.9)
  for x in (0.55, -0.55):
    w = bpy.data.meshes.new(f"{name}_wm")
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=False, segments=24, radius=0.34)
    geom = bmesh.ops.extrude_edge_only(bm, edges=bm.edges)
    bmesh.ops.translate(bm, vec=(0, 0, 0.04), verts=[v for v in geom["geom"] if isinstance(v, bmesh.types.BMVert)])
    bmesh.ops.rotate(bm, matrix=Matrix.Rotation(math.pi / 2, 3, "X"), verts=bm.verts)
    bm.to_mesh(w)
    bm.free()
    w.materials.append(tyre)
    part(f"{name}_wheel", w, root, coll, (x, 0, 0.35))
  part(f"{name}_tube", cyl_mesh(f"{name}_tm", 0.025, 1.1, "X", 8, frame), root, coll, (0, 0, 0.62))
  part(f"{name}_seat", cyl_mesh(f"{name}_sm", 0.025, 0.5, "Z", 8, frame), root, coll, (-0.2, 0, 0.75))
  top = material(f"shirt_{name}", shirt, rough=0.8)
  skin = material("skin", (0.55, 0.38, 0.28), rough=0.6)
  t = part(f"{name}_torso", cyl_mesh(f"{name}_torsom", 0.17, 0.6, mat=top), root, coll, (-0.05, 0, 1.25),
           (0, math.radians(35), 0))
  part(f"{name}_head", sphere_mesh(f"{name}_headm", 0.12, 2, skin), root, coll, (0.15, 0, 1.62))
  part(f"{name}_legs", cyl_mesh(f"{name}_legm", 0.07, 0.7, mat=material("trousers", (0.08, 0.08, 0.1), rough=0.8)),
       root, coll, (-0.1, 0, 0.75))
  return root
