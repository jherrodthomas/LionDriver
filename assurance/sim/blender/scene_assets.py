"""Blender building blocks of the hazardous-event scenes: materials, the road from its cross-section, scenery, the
environment and weather (sky, sun, overcast, night, wet road, rain, snow, fog, low-sun glare), the reference car from
the purchased mesh (instanced, repainted per road user), and simple procedural road users (truck, pedestrian,
cyclist) and the silhouette stand-in car.

Ground materials and skies use the CC0 assets of library/assets.yaml when fetch_assets.py has put them on disk
(library/assets.lock.json names the files), and a procedural look otherwise: noise-varied asphalt with grain, stones,
bump and polished wheel tracks; varied grass with dry patches; gravel; concrete slabs; Nishita or overcast skies.
Every condition (wet, puddles, snow, slush, ice) is layered on either.

Imported by hazard_scene.py; runs in Blender (bpy). Units are metres; a road user's origin is on the ground under
its body centre, forward +X. Road surfaces carry a UV map "road" in metres: u is the lateral offset from the ego
lane's centre (left positive), v the arc length.
"""

from __future__ import annotations

import json
import math
import os
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

HERE = Path(__file__).resolve().parent
SILHOUETTE = HERE.parent / "figures" / "corolla-e210-silhouette.json"
ASSET_LOCK = HERE / "library" / "assets.lock.json"
ASSET_DIR = HERE.parents[2] / "assurance" / "sim" / "assets" / "library"
SNOW_RGB = (0.80, 0.82, 0.86)
MOON_AZ = 2.2                                   # moonlight from behind and to the left of the road heading (rad)


# ------------------------------------------------------------------------------------------------- assets
class Assets:
  """The CC0 slots fetched by fetch_assets.py. A slot is used only when every file the lock names is on disk;
  otherwise the scene falls back to the procedural look for that slot."""

  def __init__(self, lock: Path | None = None, root: Path | None = None):
    lock = lock or Path(os.environ.get("LIONDRIVER_ASSET_LOCK") or ASSET_LOCK)
    root = root or Path(os.environ.get("LIONDRIVER_ASSET_LIBRARY") or ASSET_DIR)
    self.slots = {}
    if lock.exists():
      for name, s in json.loads(lock.read_text()).get("slots", {}).items():
        files = {m: root / f["path"] for m, f in s["files"].items()}
        if all(p.exists() for p in files.values()):
          self.slots[name] = {**s, "files": files}
    print("assets: " + (", ".join(f"{k} ({v['id']})" for k, v in sorted(self.slots.items())) or "none (procedural)"))

  def get(self, name: str):
    return self.slots.get(name)

  def image(self, path: Path, colour: bool):
    im = bpy.data.images.load(str(path), check_existing=True)
    if not colour:
      im.colorspace_settings.name = "Non-Color"
    return im


NO_ASSETS = None


def no_assets() -> Assets:
  global NO_ASSETS
  if NO_ASSETS is None:
    NO_ASSETS = Assets(lock=Path("/nonexistent"))
  return NO_ASSETS


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
  nt.links.new(br.outputs[0], b.inputs["Base Color"])
  nt.links.new(br.outputs[1], b.inputs["Roughness"])
  if lit:                                       # some windows lit at night: a twin brick texture gives each window
    pick = nt.nodes.new("ShaderNodeTexBrick")   # a random grey; those above the threshold glow at strength lit / 4
    pick.offset = 0.0
    for k in ("Scale", "Mortar Size", "Brick Width", "Row Height"):
      pick.inputs[k].default_value = br.inputs[k].default_value
    pick.inputs["Color1"].default_value, pick.inputs["Color2"].default_value = (0, 0, 0, 1), (1, 1, 1, 1)
    nt.links.new(tc.outputs["Object"], pick.inputs["Vector"])
    on = nt.nodes.new("ShaderNodeMath")
    on.operation = "GREATER_THAN"
    on.inputs[1].default_value = 0.6
    nt.links.new(pick.outputs[0], on.inputs[0])
    glass_only = nt.nodes.new("ShaderNodeMath")
    glass_only.operation = "SUBTRACT"
    glass_only.inputs[0].default_value = 1.0
    nt.links.new(br.outputs[1], glass_only.inputs[1])
    mask = nt.nodes.new("ShaderNodeMath")
    mask.operation = "MULTIPLY"
    nt.links.new(on.outputs[0], mask.inputs[0])
    nt.links.new(glass_only.outputs[0], mask.inputs[1])
    strength = nt.nodes.new("ShaderNodeMath")
    strength.operation = "MULTIPLY"
    strength.inputs[1].default_value = lit / 4
    nt.links.new(mask.outputs[0], strength.inputs[0])
    nt.links.new(strength.outputs[0], b.inputs["Emission Strength"])
    b.inputs["Emission Color"].default_value = (1.0, 0.8, 0.5, 1)
  return m


# ------------------------------------------------------------------------------------------------- shader nodes
class Graph:
  """A small helper over a material's node tree: nodes from a type and inputs (values or sockets), outputs by index
  (socket names differ between Blender 4.2 and 5.x)."""

  def __init__(self, mat):
    self.nt = mat.node_tree
    self.bsdf = self.nt.nodes["Principled BSDF"]

  def node(self, kind: str, inputs: dict | None = None, **props):
    n = self.nt.nodes.new(kind)
    for k, v in props.items():
      setattr(n, k, v)
    for k, v in (inputs or {}).items():
      self.set(n.inputs[k], v)
    return n

  def set(self, sock, v):
    if isinstance(v, bpy.types.NodeSocket):
      self.nt.links.new(v, sock)
    elif sock.type == "RGBA" and isinstance(v, (tuple, list)) and len(v) == 3:
      sock.default_value = (*v, 1.0)
    else:
      sock.default_value = v

  def uv(self):
    return self.node("ShaderNodeUVMap", uv_map="road").outputs[0]

  def noise(self, vec, scale: float, detail: float = 2.0, rough: float = 0.5):
    return self.node("ShaderNodeTexNoise", {"Vector": vec, "Scale": scale, "Detail": detail, "Roughness": rough})

  def mix(self, fac, a, b, blend: str = "MIX"):
    return self.node("ShaderNodeMixRGB", {0: fac, 1: a, 2: b}, blend_type=blend).outputs[0]

  def remap(self, v, a0: float, a1: float, b0: float, b1: float):
    return self.node("ShaderNodeMapRange", {0: v, 1: a0, 2: a1, 3: b0, 4: b1}, clamp=True).outputs[0]

  def math(self, op: str, a, b=0.0):
    return self.node("ShaderNodeMath", {0: a, 1: b}, operation=op).outputs[0]

  def bump(self, height, strength: float, distance: float, normal=None):
    n = self.node("ShaderNodeBump", {"Strength": strength, "Distance": distance, "Height": height})
    if normal is not None:
      self.set(n.inputs["Normal"], normal)
    return n.outputs[0]

  def finish(self, col, rough, normal=None):
    self.set(self.bsdf.inputs["Base Color"], col)
    self.set(self.bsdf.inputs["Roughness"], rough)
    if normal is not None:
      self.set(self.bsdf.inputs["Normal"], normal)


def _pbr(g: Graph, slot: dict, assets: Assets):
  """(colour, roughness, normal) sockets of a fetched texture set on the road UVs, with a large-scale tint variation
  so the tiling does not show."""
  sx, sy = slot["size_m"] if isinstance(slot["size_m"], list) else (slot["size_m"],) * 2   # [x, y]: a non-square tile
  vec = g.node("ShaderNodeMapping", {"Vector": g.uv(), "Scale": (1 / sx, 1 / sy, 1.0)}).outputs[0]
  img = lambda m, colour: g.node("ShaderNodeTexImage", {"Vector": vec}, image=assets.image(slot["files"][m], colour))
  macro = g.remap(g.noise(g.uv(), 0.04, 3).outputs[0], 0.3, 0.7, 0.82, 1.12)
  col = g.mix(1.0, img("color", True).outputs[0], macro, "MULTIPLY")
  if slot.get("tint", 1.0) != 1.0:              # bring a bright scan to the albedo of the real surface
    col = g.mix(1.0, col, (slot["tint"],) * 3, "MULTIPLY")
  rough = img("roughness", False).outputs[0]
  if slot.get("roughness_min"):                 # no sheen at grazing angles from a glossy scan
    rough = g.math("MAXIMUM", rough, slot["roughness_min"])
  normal = g.node("ShaderNodeNormalMap", {"Color": img("normal", False).outputs[0], "Strength": 1.0},
                  space="TANGENT", uv_map="road").outputs[0]
  return col, rough, normal


def _weather_layer(g: Graph, col, rough, normal, env: dict, tracks=None, puddles: bool = True):
  """Wet darkening and gloss, puddles in low spots, snow or slush cover (off the wheel tracks), ice gloss."""
  w = float(env.get("wet", 0.0) or 0.0)
  s = float(env.get("snow", 0.0) or 0.0)
  if w > 0:
    col = g.mix(w * 0.55, col, g.mix(1.0, col, (0.42, 0.42, 0.44), "MULTIPLY"))
    rough = g.math("MULTIPLY", rough, 1.0 - 0.7 * w)
    if puddles and w > 0.5:
      t0 = 0.66 - 0.16 * (w - 0.5) * 2
      pud = g.remap(g.noise(g.uv(), 0.18, 3).outputs[0], t0, t0 + 0.03, 0.0, 1.0)
      if tracks is not None:
        pud = g.math("MAXIMUM", pud, g.math("MULTIPLY", tracks, 0.8 * w))
      rough = g.node("ShaderNodeMix", {0: pud, 2: rough, 3: 0.02}, data_type="FLOAT").outputs[0]
      col = g.mix(pud, col, g.mix(1.0, col, (0.6, 0.6, 0.62), "MULTIPLY"))
  if s > 0:
    lo, hi = (0.62 - 0.22 * s, 0.7 - 0.15 * s) if tracks is not None else (0.62 - 0.35 * s, 0.7 - 0.25 * s)
    cover = g.remap(g.noise(g.uv(), 1.6, 3).outputs[0], lo, hi, 0.0, 1.0)
    if tracks is not None:                       # slush beside and between the wheel tracks, dark wet tracks
      cover = g.math("MULTIPLY", cover, g.math("SUBTRACT", 1.0, tracks))
      cover = g.math("MULTIPLY", cover, 0.85)
    col = g.mix(cover, col, SNOW_RGB)
    rough = g.node("ShaderNodeMix", {0: cover, 2: rough, 3: 0.55}, data_type="FLOAT").outputs[0]
  if env.get("ice") and tracks is not None:
    rough = g.node("ShaderNodeMix", {0: g.math("MULTIPLY", tracks, 0.7), 2: rough, 3: 0.04},
                   data_type="FLOAT").outputs[0]
  return col, rough, normal


def _tracks(g: Graph, lane_width: float):
  """1 on the wheel tracks of every lane (0.8 m either side of its centre), 0 between them."""
  u = g.node("ShaderNodeSeparateXYZ", {0: g.uv()}).outputs[0]
  p = g.math("FRACT", g.math("DIVIDE", g.math("ADD", u, lane_width / 2), lane_width))
  centre = g.math("MULTIPLY", g.math("ABSOLUTE", g.math("SUBTRACT", p, 0.5)), lane_width)
  return g.remap(g.math("ABSOLUTE", g.math("SUBTRACT", centre, 0.8)), 0.0, 0.45, 1.0, 0.0)


def asphalt_material(name: str, env: dict, assets: Assets, lane_width: float = 3.7, tracks: bool = True,
                     tint: float = 1.0):
  m = bpy.data.materials.get(name)
  if m:
    return m
  m = bpy.data.materials.new(name)
  m.use_nodes = True
  g = Graph(m)
  uv = g.uv()
  slot = assets.get("asphalt")
  if slot:
    col, rough, normal = _pbr(g, slot, assets)
    col = g.mix(1.0, col, (tint,) * 3, "MULTIPLY")
  else:
    big = g.noise(uv, 0.06, 3).outputs[0]                       # resurfacing patches
    mid = g.noise(uv, 0.7, 4).outputs[0]
    grain = g.noise(uv, 22.0, 2).outputs[0]
    cells = g.node("ShaderNodeTexVoronoi", {"Vector": uv, "Scale": 75.0})
    stones = g.node("ShaderNodeValToRGB", {0: cells.outputs[1]})
    stones.color_ramp.elements[0].position, stones.color_ramp.elements[1].position = 0.86, 0.9
    base = g.mix(big, tuple(tint * v for v in (0.032, 0.032, 0.034)), tuple(tint * v for v in (0.064, 0.061, 0.058)))
    base = g.mix(g.remap(mid, 0.3, 0.7, 0.0, 0.5), base, tuple(tint * v for v in (0.024, 0.024, 0.025)))
    base = g.mix(1.0, base, g.remap(grain, 0.25, 0.75, 0.7, 1.3), "MULTIPLY")
    col = g.mix(g.math("MULTIPLY", stones.outputs[0], 0.6), base, (0.24, 0.235, 0.22))
    rough = g.remap(mid, 0.2, 0.8, 0.8, 0.92)
    normal = g.bump(g.math("ADD", grain, g.math("MULTIPLY", stones.outputs[0], 0.5)), 0.22, 0.008)
  tr = _tracks(g, lane_width) if tracks else None
  if tr is not None:                             # polished, darker wheel tracks
    col = g.mix(g.math("MULTIPLY", tr, 0.45), col, g.mix(1.0, col, (0.68, 0.68, 0.68), "MULTIPLY"))
    rough = g.math("SUBTRACT", rough, g.math("MULTIPLY", tr, 0.12))
  col, rough, normal = _weather_layer(g, col, rough, normal, env, tr)
  g.finish(col, rough, normal)
  m.diffuse_color = (0.05, 0.05, 0.055, 1)
  return m


def grass_material(name: str, env: dict, assets: Assets):
  m = bpy.data.materials.get(name)
  if m:
    return m
  m = bpy.data.materials.new(name)
  m.use_nodes = True
  g = Graph(m)
  uv = g.uv()
  slot = assets.get("grass")
  n2 = g.noise(uv, 0.6, 4).outputs[0]
  n3 = g.noise(uv, 9.0, 3).outputs[0]
  if slot:
    col, rough, normal = _pbr(g, slot, assets)
  else:
    n1 = g.noise(uv, 0.04, 3).outputs[0]
    col = g.mix(n1, (0.055, 0.12, 0.03), (0.11, 0.155, 0.045))
    col = g.mix(g.remap(n2, 0.56, 0.72, 0.0, 0.65), col, (0.2, 0.17, 0.07))             # dry patches
    col = g.mix(1.0, col, g.remap(n3, 0.2, 0.8, 0.65, 1.25), "MULTIPLY")
    u = g.math("ABSOLUTE", g.node("ShaderNodeSeparateXYZ", {0: uv}).outputs[0])
    far = g.remap(g.math("ADD", u, g.math("MULTIPLY", n2, 8.0)), 14.0, 26.0, 0.0, 1.0)  # mown verge, then meadow
    col = g.mix(g.math("MULTIPLY", far, 0.55), col, g.mix(n1, (0.05, 0.085, 0.03), (0.16, 0.15, 0.06)))
    rough = 0.95
    normal = g.bump(n3, 0.5, 0.03)
  w = float(env.get("wet", 0.0) or 0.0)
  if w:
    col = g.mix(w * 0.4, col, g.mix(1.0, col, (0.6, 0.62, 0.6), "MULTIPLY"))
    rough = g.math("MULTIPLY", rough, 1.0 - 0.35 * w)
  s = float(env.get("snow", 0.0) or 0.0)
  if s:                                          # snow cover with grass showing through in places
    cover = g.remap(g.math("ADD", g.math("MULTIPLY", n2, 0.6), g.math("MULTIPLY", n3, 0.4)), 0.62 - 0.27 * s,
                    0.7 - 0.18 * s, 0.0, 1.0)
    col = g.mix(cover, col, SNOW_RGB)
    rough = g.node("ShaderNodeMix", {0: cover, 2: rough, 3: 0.6}, data_type="FLOAT").outputs[0]
  g.finish(col, rough, normal)
  m.diffuse_color = (0.08, 0.15, 0.05, 1)
  return m


def gravel_material(name: str, env: dict, assets: Assets):
  m = bpy.data.materials.get(name)
  if m:
    return m
  m = bpy.data.materials.new(name)
  m.use_nodes = True
  g = Graph(m)
  uv = g.uv()
  slot = assets.get("gravel")
  if slot:
    col, rough, normal = _pbr(g, slot, assets)
  else:
    cells = g.node("ShaderNodeTexVoronoi", {"Vector": uv, "Scale": 28.0})
    ramp = g.node("ShaderNodeValToRGB", {0: cells.outputs[1]})
    ramp.color_ramp.elements[0].color = (0.075, 0.07, 0.06, 1)
    ramp.color_ramp.elements[1].color = (0.2, 0.18, 0.15, 1)
    col = g.mix(g.remap(g.noise(uv, 0.3, 2).outputs[0], 0.3, 0.7, 0.0, 0.4), ramp.outputs[0], (0.11, 0.1, 0.08))
    rough = 0.95
    normal = g.bump(g.math("SUBTRACT", 1.0, cells.outputs[0]), 0.6, 0.02)
  col, rough, normal = _weather_layer(g, col, rough, normal, env, None, puddles=False)
  g.finish(col, rough, normal)
  m.diffuse_color = (0.22, 0.2, 0.17, 1)
  return m


def concrete_material(name: str, env: dict, assets: Assets, slab: float = 1.5):
  m = bpy.data.materials.get(name)
  if m:
    return m
  m = bpy.data.materials.new(name)
  m.use_nodes = True
  g = Graph(m)
  uv = g.uv()
  slot = assets.get("concrete")
  if slot:
    col, rough, normal = _pbr(g, slot, assets)
  else:
    br = g.node("ShaderNodeTexBrick", {"Vector": uv, "Scale": 1.0 / slab, "Mortar Size": 0.012,
                                        "Brick Width": 1.0, "Row Height": 1.0, "Color1": (0.44, 0.43, 0.41),
                                        "Color2": (0.40, 0.39, 0.37), "Mortar": (0.22, 0.22, 0.21)}, offset=0.0)
    n = g.noise(uv, 3.0, 4).outputs[0]
    col = g.mix(1.0, br.outputs[0], g.remap(n, 0.3, 0.7, 0.85, 1.12), "MULTIPLY")
    rough = 0.88
    normal = g.bump(g.math("ADD", g.math("MULTIPLY", br.outputs[1], -0.6), g.math("MULTIPLY", n, 0.2)), 0.3, 0.01)
  col, rough, normal = _weather_layer(g, col, rough, normal, env, None, puddles=False)
  g.finish(col, rough, normal)
  m.diffuse_color = (0.42, 0.41, 0.39, 1)
  return m


def marking_material(name: str, rgb, env: dict, rough: float = 0.5):
  """Lane paint: glossier when wet, partly under snow."""
  m = bpy.data.materials.get(name)
  if m:
    return m
  m = bpy.data.materials.new(name)
  m.use_nodes = True
  g = Graph(m)
  w = float(env.get("wet", 0.0) or 0.0)
  col, r = rgb, rough * (1.0 - 0.6 * w)
  if env.get("snow"):
    cover = g.remap(g.noise(g.uv(), 1.6, 3).outputs[0], 0.62 - 0.22 * env["snow"], 0.7 - 0.15 * env["snow"], 0, 0.7)
    col = g.mix(cover, rgb, SNOW_RGB)
  g.finish(col, r)
  m.diffuse_color = (*rgb, 1)
  return m


# ------------------------------------------------------------------------------------------------- meshes
def mesh_object(name: str, verts, faces, mat=None, coll=None, smooth=False, uvs=None):
  me = bpy.data.meshes.new(name)
  me.from_pydata(verts, [], faces)
  me.update()
  if uvs is not None:
    layer = me.uv_layers.new(name="road")
    for loop in me.loops:
      layer.data[loop.index].uv = uvs[loop.vertex_index]
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


def cyl_mesh(name: str, r: float, length: float, axis: str = "Z", segs: int = 16, mat=None, r2: float | None = None):
  me = bpy.data.meshes.new(name)
  bm = bmesh.new()
  bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r if r2 is None else r2, depth=length)
  rot = {"Z": Matrix.Identity(3), "X": Matrix.Rotation(math.pi / 2, 3, "Y"), "Y": Matrix.Rotation(math.pi / 2, 3, "X")}
  bmesh.ops.rotate(bm, matrix=rot[axis], verts=bm.verts)
  for f in bm.faces:
    f.smooth = True
  bm.to_mesh(me)
  bm.free()
  if mat:
    me.materials.append(mat)
  return me


def sphere_mesh(name: str, r: float, subdiv: int = 2, mat=None, lumpy: float = 0.0, seed: int = 0):
  """An icosphere; lumpy > 0 pushes its surface in and out with smooth noise (tree crowns)."""
  me = bpy.data.meshes.new(name)
  bm = bmesh.new()
  bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=r)
  if lumpy:
    off = Vector((seed * 7.1, seed * 3.3, seed * 1.7))
    for v in bm.verts:
      n = v.co.normalized()
      v.co += n * r * lumpy * noise.noise(v.co * (1.6 / r) + off)
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
  """A ribbon between lateral offsets d0 and d1 (left positive) at height z (sloping to z1 at d1 if given), with UVs
  in metres (u lateral, v along); s_ranges limits it to dashes."""
  verts, faces, uvs = [], [], []
  z1 = z if z1 is None else z1
  for i in range(len(centre) - 1):
    a, b = centre[i], centre[i + 1]
    if s_ranges is not None and not any(lo <= a[3] < hi for lo, hi in s_ranges):
      continue
    k = len(verts)
    verts += [offset(a, d0, z), offset(a, d1, z1), offset(b, d1, z1), offset(b, d0, z)]
    uvs += [(d0, a[3]), (d1, a[3]), (d1, b[3]), (d0, b[3])]
    faces.append((k, k + 1, k + 2, k + 3))
  return mesh_object(name, verts, faces, mat, coll, uvs=uvs)


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


def build_road(r: dict, env: dict, assets: Assets | None = None):
  """The road from its cross-section (export_scene.py road_layout): surfaces, markings, kerbs, barrier, crossings."""
  assets = assets or no_assets()
  c = r["centre"]
  coll = bpy.data.collections.new("road")
  bpy.context.scene.collection.children.link(coll)
  lw = r["lane_width"]
  asphalt = asphalt_material("asphalt", env, assets, lw)
  mats = {
    "asphalt": asphalt,
    "shoulder": asphalt_material("shoulder", env, assets, lw, tracks=False, tint=1.25),
    "gravel": gravel_material("gravel", env, assets),
    "parking": asphalt_material("parking", env, assets, lw, tracks=False, tint=1.1),
    "sidewalk": concrete_material("sidewalk", env, assets),
    "grass": grass_material("grass", env, assets),
    "median": grass_material("grass", env, assets),
  }
  white = marking_material("paint_white", (0.85, 0.85, 0.82), env)
  yellow = marking_material("paint_yellow", (0.85, 0.6, 0.05), env)
  worn = marking_material("paint_worn", (0.3, 0.3, 0.29), env, rough=0.8)
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


def leaves_material(name: str, rgb, env: dict):
  """Foliage with a little colour variation; snow on the upward-facing parts under W05."""
  m = bpy.data.materials.get(name)
  if m:
    return m
  m = bpy.data.materials.new(name)
  m.use_nodes = True
  g = Graph(m)
  pos = g.node("ShaderNodeNewGeometry")
  n = g.noise(pos.outputs["Position"], 1.4, 4).outputs[0]
  col = g.mix(1.0, rgb, g.remap(n, 0.3, 0.7, 0.65, 1.3), "MULTIPLY")
  rough = 0.9
  if env.get("snow"):
    up = g.node("ShaderNodeSeparateXYZ", {0: pos.outputs["Normal"]}).outputs[2]
    col = g.mix(g.remap(g.math("ADD", up, g.math("MULTIPLY", n, 0.4)), 0.55, 0.85, 0.0, env["snow"]), col, SNOW_RGB)
  normal = g.bump(n, 0.6, 0.15)
  g.finish(col, rough, normal)
  m.diffuse_color = (*rgb, 1)
  return m


def build_scenery(r: dict, env: dict, seed: int = 7):
  """Trees (broadleaf and conifer), buildings and street lights beside the road, as the road's scenery asks:
  trees (a row either side), open (sparse trees in fields), urban (buildings, street trees, street lights)."""
  rnd = random.Random(seed)
  c = r["centre"]
  coll = bpy.data.collections.new("scenery")
  bpy.context.scene.collection.children.link(coll)
  kind = r["scenery"]
  left_out, right_out = r["outer"]
  if kind in ("trees", "urban", "open"):
    bark = material("bark", (0.12, 0.08, 0.05), rough=1.0)
    trunk = cyl_mesh("trunk", 0.18, 3.0, mat=bark, r2=0.12)
    greens = [(0.06, 0.14, 0.04), (0.08, 0.17, 0.05), (0.05, 0.11, 0.035), (0.1, 0.16, 0.04)]
    crowns = [sphere_mesh(f"crown_{k}", 2.2 + 0.4 * (k % 3), 3, leaves_material(f"leaves_{k}", g, env), 0.22, k)
              for k, g in enumerate(greens)]
    conifer_mat = leaves_material("needles", (0.03, 0.08, 0.04), env)
    conifers = []
    for k in range(2):
      me = bpy.data.meshes.new(f"conifer_{k}")
      bm = bmesh.new()
      for j, (rad, z) in enumerate(((2.0, 1.2), (1.6, 2.6), (1.15, 3.9), (0.7, 5.0))):
        geo = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=rad * (1 + 0.1 * k), radius2=0.05,
                                    depth=2.4)
        bmesh.ops.translate(bm, vec=(0, 0, z + 1.2), verts=geo["verts"])
      bm.to_mesh(me)
      bm.free()
      me.materials.append(conifer_mat)
      conifers.append(me)
    root = empty("trees", coll)
    step = {"trees": 14.0, "urban": 18.0, "open": 38.0}[kind]
    for side, d_base in ((1, left_out + (3.5 if kind != "urban" else -1.2)),
                         (-1, right_out - (3.5 if kind != "urban" else -1.2))):
      s = c[0][3] + rnd.uniform(0, step)
      while s < c[-1][3]:
        p = c[min(int((s - c[0][3]) / (c[1][3] - c[0][3])), len(c) - 1)]
        d = d_base + side * rnd.uniform(0, {"trees": 6.0, "urban": 0.3, "open": 40.0}[kind])
        x, y, _ = offset(p, d)
        sc = rnd.uniform(0.8, 1.3) * (0.55 if kind == "urban" else 1.0)
        if kind != "urban" and rnd.random() < (0.55 if env.get("snow") else 0.3):
          t = part("conifer", rnd.choice(conifers), root, coll, (x, y, 0.0), (0, 0, rnd.uniform(0, 6.28)))
          t.scale = (sc, sc, sc * rnd.uniform(1.0, 1.4))
        else:
          t = part("tree", trunk, root, coll, (x, y, 1.5 * sc))
          t.scale = (sc, sc, sc)
          cr = part("crown", rnd.choice(crowns), root, coll, (x, y, 3.0 * sc + 1.6 * sc),
                    (0, 0, rnd.uniform(0, 6.28)))
          cr.scale = (sc, sc, sc * 1.15)
        s += step * rnd.uniform(0.6, 1.4)
  if kind == "urban":
    night = env.get("night", False)
    walls = [(0.55, 0.5, 0.45), (0.45, 0.42, 0.4), (0.62, 0.58, 0.5), (0.35, 0.33, 0.33), (0.5, 0.38, 0.3)]
    facades = [facade_material(f"facade_{k}", w, lit=1.5 if night else 0.0) for k, w in enumerate(walls)]
    roof = material("roof", SNOW_RGB if env.get("snow") else (0.2, 0.2, 0.21), rough=0.8)
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
        part("building", me, root, coll, (x, y, 0), (0, 0, p[2]))
        part("roof", box_mesh(f"roof_{side}_{s:.0f}", wdt - 1.3, dep + 0.2, 0.3, hgt, roof), root, coll, (x, y, 0),
             (0, 0, p[2]))
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
def sun_colour(elev_deg: float):
  """Warm near the horizon, near white high up."""
  f = max(0.0, min(1.0, (elev_deg - 3.0) / 35.0))
  return (1.0, 0.7 + 0.24 * f, 0.45 + 0.42 * f)


def build_environment(env: dict, heading: float, assets: Assets | None = None):
  """Sky and sun. env (library/conditions.yaml): sky (clear, partly, overcast, night), sun ('behind', 'ahead': low sun
  in the driver's eyes, 'side'), sun_elevation (degrees, raised to sun_elevation_min), sun_strength, night.
  heading: road heading at the ego's start."""
  assets = assets or no_assets()
  scene = bpy.context.scene
  world = bpy.data.worlds.new("sky")
  world.use_nodes = True
  nodes, links = world.node_tree.nodes, world.node_tree.links
  bg = nodes["Background"]
  night = bool(env.get("night")) or env.get("sky") == "night"
  sky = "night" if night else env.get("sky", "clear")
  where = env.get("sun", "behind")
  default_elev = (12.0 if env.get("urban") else 4.0) if where == "ahead" else (25.0 if env.get("urban") else 9.0)
  elev_deg = max(env.get("sun_elevation", default_elev), env.get("sun_elevation_min", -90.0))
  elev = math.radians(elev_deg)
  az = heading + {"behind": math.radians(150), "ahead": math.radians(-6), "side": math.radians(80)}[where]
  # the sun lamp points from the sun toward the scene: from direction (az, elev)
  sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
  scene.collection.objects.link(sun)
  d = (math.cos(elev) * math.cos(az), math.cos(elev) * math.sin(az), math.sin(elev))
  sun.rotation_euler = _track(d)
  sun.data.angle = math.radians(1.0)
  slot = assets.get({"clear": "hdri_clear", "partly": "hdri_clear", "overcast": "hdri_overcast",
                     "night": "hdri_night"}[sky] if not (where == "ahead" and sky == "clear")
                    else "hdri_low_sun")
  image = assets.image(slot["files"]["hdri"], True) if slot else None
  h_az, h_elev = hdri_sun(image) if image else (0.0, 0.0)
  if slot and where == "ahead" and elev > h_elev + math.radians(1.0):
    # the sun in the driver's eyes is the triggering condition: an HDRI only turns about the vertical, so where the
    # environment lifts the sun above the HDRI's own (buildings, sun_elevation_min) the procedural sky draws it
    slot = None
  if slot:
    tex = nodes.new("ShaderNodeTexEnvironment")
    tex.image = image
    mp = nodes.new("ShaderNodeMapping")
    # the mapping rotates the lookup direction: the HDRI's sun appears at its own azimuth minus this rotation
    # (at night its brightest spot is a light on the horizon, not a sun: it goes with the moonlight, off to the side)
    mp.inputs["Rotation"].default_value = (0.0, 0.0, h_az - (heading + MOON_AZ if night else az))
    links.new(nodes.new("ShaderNodeTexCoord").outputs["Generated"], mp.inputs["Vector"])
    links.new(mp.outputs[0], tex.inputs["Vector"])
    links.new(tex.outputs[0], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = slot.get("strength", 1.0)
  if night:                                     # moonlit sky: dark blue ambient and a faint cool key light
    if not slot:
      bg.inputs["Color"].default_value = (0.02, 0.03, 0.07, 1.0)
      bg.inputs["Strength"].default_value = 1.5
    sun.data.energy = 0.25
    sun.data.color = (0.6, 0.7, 1.0)
    sun.rotation_euler = _track((math.cos(heading + MOON_AZ), math.sin(heading + MOON_AZ), 0.6))
  elif sky == "overcast":                       # soft light from a bright grey dome; a weak, diffuse sun
    if not slot:
      grad = nodes.new("ShaderNodeTexGradient")
      ramp = nodes.new("ShaderNodeValToRGB")
      sep = nodes.new("ShaderNodeSeparateXYZ")
      links.new(nodes.new("ShaderNodeTexCoord").outputs["Generated"], sep.inputs[0])
      links.new(sep.outputs[2], ramp.inputs[0])
      ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.5, 0.75
      ramp.color_ramp.elements[0].color = (0.62, 0.64, 0.67, 1)
      ramp.color_ramp.elements[1].color = (0.42, 0.45, 0.5, 1)
      links.new(ramp.outputs[0], bg.inputs["Color"])
      bg.inputs["Strength"].default_value = 2.8 if env.get("urban") else 2.4
      nodes.remove(grad)
    sun.data.energy = 3.0 * env.get("sun_strength", 0.35)
    sun.data.angle = math.radians(25.0)
    sun.data.color = (0.95, 0.96, 1.0)
  else:
    if not slot:
      try:
        sky_tex = nodes.new("ShaderNodeTexSky")
        try:
          sky_tex.sky_type = "NISHITA"
        except TypeError:
          pass
        sky_tex.sun_elevation = elev
        # Nishita sun_rotation: azimuth measured from +Y toward -X (Blender's sky convention)
        sky_tex.sun_rotation = (math.pi / 2 - az) % (2 * math.pi)
        sky_tex.sun_disc = where == "ahead"
        sky_tex.sun_intensity = 0.6
        links.new(sky_tex.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = 0.3 if env.get("urban") else 0.15
      except (RuntimeError, AttributeError, KeyError):
        bg.inputs["Color"].default_value = (0.55, 0.68, 0.85, 1.0)
        bg.inputs["Strength"].default_value = 0.8
    sun.data.energy = (2.6 if where != "ahead" else 3.2) * env.get("sun_strength", 1.0)
    sun.data.color = sun_colour(elev_deg)
  scene.world = world
  try:
    scene.view_settings.look = "AgX - Medium High Contrast"
  except TypeError:
    pass
  return sun


def hdri_sun(image) -> tuple[float, float]:
  """(azimuth, elevation) of the brightest pixel of an equirectangular image's upper half, in Blender's world frame
  (azimuth 0 along +X); (0, 0) when it cannot be read."""
  try:
    import numpy as np
    w, h = image.size
    px = np.empty(w * h * 4, dtype=np.float32)
    image.pixels.foreach_get(px)
    lum = px.reshape(h, w, 4)[h // 2:, :, :3].sum(axis=2)          # upper half (rows run bottom to top)
    row, col = (int(v) for v in np.unravel_index(np.argmax(lum), lum.shape))
  except Exception:                             # numpy missing or the image not loaded: no alignment
    return 0.0, 0.0
  # Blender's equirectangular lookup: u = -atan2(dir.y, dir.x) / (2 pi) + 0.5 (the image centre faces +X; checked with
  # a panoramic render), so the column's azimuth is -2 pi (u - 0.5)
  return (-2 * math.pi * ((col + 0.5) / w - 0.5), math.pi * ((h // 2 + row + 0.5) / h - 0.5))


def _track(direction):
  """Euler rotation that points a lamp's -Z along -direction (toward the scene)."""
  return Vector(direction).to_track_quat("Z", "Y").to_euler()


# ------------------------------------------------------------------------------------------------- weather
def build_weather(env: dict, follow, centre, frames: int, fps: int, seed: int = 11):
  """Fog or haze (a volume layer over the scene with extinction 3 / visibility, from visibility_m), and falling rain
  or snow in a box that travels with `follow` (the ego). Returns the collection (hidden from the top camera, which
  shows the layout)."""
  coll = bpy.data.collections.new("weather")
  bpy.context.scene.collection.children.link(coll)
  vis = env.get("visibility_m")
  if vis and vis < 2500:
    mid = centre[len(centre) // 2]
    span = max(800.0, 1.4 * math.hypot(centre[-1][0] - centre[0][0], centre[-1][1] - centre[0][1]))
    # a layer 50 m deep: deep enough for every view along the road, shallow enough to let the sky light through
    dome = bpy.data.objects.new("fog", box_mesh("fog_box", span, span, 50.0, -5.0))
    dome.location = (mid[0], mid[1], 0.0)
    coll.objects.link(dome)
    m = bpy.data.materials.new("fog")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = 3.0 / vis
    vol.inputs["Color"].default_value = (0.88, 0.89, 0.91, 1.0)
    vol.inputs["Anisotropy"].default_value = 0.3
    nt.links.new(vol.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    dome.data.materials.append(m)
  rnd = random.Random(seed)
  for kind, amount in (("rain", env.get("rain", 0.0)), ("snow", env.get("snow", 0.0) * 0.8)):
    if not amount:
      continue
    period = 14.0
    speed = 9.0 if kind == "rain" else 1.1
    n = int((4500 if kind == "rain" else 6000) * amount)
    verts, faces = [], []
    for i in range(n):
      x, y, z = rnd.uniform(-18, 70), rnd.uniform(-16, 16), rnd.uniform(0, period)
      for zz in (z, z + period):                 # two copies one period apart: the fall loops without a gap
        k = len(verts)
        if kind == "rain":
          ln, w = rnd.uniform(0.4, 0.75), 0.006
          a = rnd.uniform(0, math.pi)
          dx, dy = w * math.cos(a), w * math.sin(a)
          verts += [(x - dx, y - dy, zz), (x + dx, y + dy, zz), (x + dx + 0.04, y + dy, zz + ln),
                    (x - dx + 0.04, y - dy, zz + ln)]
          faces.append((k, k + 1, k + 2, k + 3))
        else:
          r = rnd.uniform(0.025, 0.045)
          verts += [(x + r, y, zz), (x - r, y, zz), (x, y + r, zz), (x, y - r, zz), (x, y, zz + r), (x, y, zz - r)]
          faces += [(k, k + 2, k + 4), (k + 2, k + 1, k + 4), (k + 1, k + 3, k + 4), (k + 3, k, k + 4),
                    (k + 2, k, k + 5), (k + 1, k + 2, k + 5), (k + 3, k + 1, k + 5), (k, k + 3, k + 5)]
    mat = (material("rain_streak", (0.75, 0.78, 0.82), rough=0.1, alpha=0.18, emit=0.15) if kind == "rain"
           else material("snowflake", (0.95, 0.96, 1.0), rough=0.7, emit=0.2))
    ob = mesh_object(kind, verts, faces, mat, coll)
    holder = empty(f"{kind}_fall", coll)
    holder.parent = follow
    ob.parent = holder
    for f in range(1, frames + 1):
      holder.location = (0.0, 0.0, -((f / fps * speed) % period))
      holder.keyframe_insert("location", frame=f)
  return coll


def setup_glare(env: dict):
  """Bloom round the sun and bright reflections (low sun, night lights), in the compositor (Blender 5.x or 4.x)."""
  if not env.get("glare"):
    return
  scene = bpy.context.scene
  try:
    if hasattr(scene.render, "compositor_device"):                 # headless: no GPU compositor (EGL)
      scene.render.compositor_device = "CPU"
    if hasattr(scene, "compositing_node_group"):                    # Blender 5: compositor node groups
      ng = bpy.data.node_groups.new("glare", "CompositorNodeTree")
      ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
      scene.compositing_node_group = ng
      rl, gl, out = (ng.nodes.new(k) for k in ("CompositorNodeRLayers", "CompositorNodeGlare", "NodeGroupOutput"))
      for k, v in (("Type", "Bloom"), ("Quality", "High"), ("Threshold", 1.2), ("Strength", 0.6), ("Size", 0.6)):
        try:
          gl.inputs[k].default_value = v
        except (KeyError, TypeError):
          pass
      ng.links.new(rl.outputs["Image"], gl.inputs["Image"])
      ng.links.new(gl.outputs[0], out.inputs[0])
    else:                                                            # Blender 4.x
      scene.use_nodes = True
      nt = scene.node_tree
      rl, comp = nt.nodes["Render Layers"], nt.nodes["Composite"]
      gl = nt.nodes.new("CompositorNodeGlare")
      gl.glare_type, gl.threshold, gl.size = "FOG_GLOW", 1.2, 7
      nt.links.new(rl.outputs["Image"], gl.inputs["Image"])
      nt.links.new(gl.outputs["Image"], comp.inputs["Image"])
  except (AttributeError, KeyError, RuntimeError, TypeError) as e:
    print(f"glare not set up: {e}")


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
  stripe = material("truck_stripe", (0.08, 0.22, 0.45), rough=0.5)
  steel = material("truck_steel", (0.5, 0.5, 0.52), rough=0.4, metal=0.8)
  amber = material("truck_marker", (1.0, 0.55, 0.05), rough=0.3, emit=3.0)
  bx = -length / 2 + box_len / 2
  part(f"{name}_stripe", box_mesh(f"{name}_stm", box_len - 0.1, 2.52, 0.28, 1.45, stripe), root, coll, (bx, 0, 0))
  for y in (1.27, -1.27):                       # rear door frame, cab side windows, side markers
    part(f"{name}_door", box_mesh(f"{name}_drm{y}", 0.04, 0.08, 2.6, 1.1, steel), root, coll,
         (-length / 2 - 0.01, y * 0.98, 0))
    part(f"{name}_sidewin", box_mesh(f"{name}_swm{y}", 0.9, 0.04, 0.6, 2.05, glass), root, coll,
         (length / 2 - 0.9, y * 0.95, 0))
    for x in (bx - box_len / 3, bx, bx + box_len / 3):
      part(f"{name}_marker", box_mesh(f"{name}_mk", 0.12, 0.03, 0.06, 1.15, amber), root, coll, (x, y * 0.995, 0))
  part(f"{name}_doorgap", box_mesh(f"{name}_dgm", 0.04, 0.05, 2.5, 1.12, steel), root, coll, (-length / 2 - 0.01, 0, 0))
  part(f"{name}_grille", box_mesh(f"{name}_grm", 0.05, 1.6, 0.6, 1.15, dark), root, coll, (length / 2 - 0.08, 0, 0))
  part(f"{name}_bumper", box_mesh(f"{name}_bpm", 0.25, 2.4, 0.3, 0.55, steel), root, coll, (length / 2 - 0.05, 0, 0))
  part(f"{name}_underrun", box_mesh(f"{name}_urm", 0.12, 2.3, 0.15, 0.55, steel), root, coll, (-length / 2 + 0.1, 0, 0))
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
