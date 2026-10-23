"""Blender building blocks of the hazardous-event scenes: materials, the road from its cross-section, scenery, the
environment and weather (sky, sun, overcast, night, wet road, rain, snow, fog, low-sun glare), the reference car from
the purchased mesh (instanced, repainted per road user), and simple procedural road users (truck, pedestrian,
cyclist) and the silhouette stand-in car.

Ground materials, skies and plants use the CC0 assets of library/assets.yaml when fetch_assets.py has put them on
disk (library/assets.lock.json names the files), and a procedural look otherwise: noise-varied asphalt with grain,
stones, bump and polished wheel tracks; varied grass with dry patches; gravel; concrete slabs; Nishita or overcast
skies; lumpy-crowned trees and stacked-cone conifers, and no verge grass. Every condition (wet, puddles, snow, slush,
ice) is layered on either. The kerbs, walkways and street lights at the road edges are visual only (edge_features):
they stand outside the carriageway and beyond the barrier line, so they never change a contact or an event.

Imported by hazard_scene.py; runs in Blender (bpy). Units are metres; a road user's origin is on the ground under
its body centre, forward +X. Road surfaces carry a UV map "road" in metres: u is the lateral offset from the ego
lane's centre (left positive), v the arc length.
"""

from __future__ import annotations

import json
import math
import os
import random
import zlib
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
PEOPLE_DIR = HERE / "library" / "people"        # CC0 pedestrians built by library/people/build_people.py
PEOPLE = (("pedestrian_male.glb", 1.78), ("pedestrian_female.glb", 1.66))   # file, standing height (m)
SHIRTS = ((0.13, 0.22, 0.42), (0.45, 0.08, 0.08), (0.22, 0.30, 0.18), (0.55, 0.50, 0.42), (0.30, 0.18, 0.40))


# ------------------------------------------------------------------------------------------------- assets
class Assets:
  """The CC0 slots fetched by fetch_assets.py. A slot is used only when every file the lock names is on disk;
  otherwise the scene falls back to the procedural look for that slot."""

  def __init__(self, lock: Path | None = None, root: Path | None = None):
    lock = lock or Path(os.environ.get("LIONDRIVER_ASSET_LOCK") or ASSET_LOCK)
    root = root or Path(os.environ.get("LIONDRIVER_ASSET_LIBRARY") or ASSET_DIR)
    self.slots, self.root = {}, root
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
    # a water film shows early: sheen and darkening follow sqrt(wet) and the roughness is capped, so W02 (0.75)
    # reads wet while W04 (1.0) stays the wettest; puddles start at 0.4 and reach their W04 extent at 1.0
    e = math.sqrt(w)
    col = g.mix(e * 0.7, col, g.mix(1.0, col, (0.38, 0.38, 0.40), "MULTIPLY"))
    rough = g.math("MINIMUM", g.math("MULTIPLY", rough, 1.0 - 0.7 * e), 0.45 - 0.33 * e)
    if normal is not None:                       # the film fills the texture's pores: flatter, so the sky reflects
      flat = g.node("ShaderNodeNewGeometry").outputs["Normal"]
      normal = g.node("ShaderNodeMix", {0: 0.6 * e, 4: normal, 5: flat}, data_type="VECTOR").outputs[1]
    if puddles and w > 0.4:
      t0 = 0.66 - 0.16 * ((w - 0.4) / 0.6) ** 0.6
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


WET_SHEEN = 0.75     # from this wetness on, the road is a water film: streaky, mirror-like reflections


def _wet_sheen(g: Graph, rough, normal, env: dict, tracks=None):
  """A standing water film (wet >= WET_SHEEN, W02 and W04): the reflections of lamps, lights and sky stretch along
  the road, as on a real wet carriageway. Anisotropic roughness with its tangent along the road (the road UV's v),
  a lower roughness floor in the wheel tracks, where the water is smoothest, and a fine ripple of the normal under
  rain. Wetter roads (W04) get more stretch and a lower floor; dry and damp roads are unchanged."""
  w = float(env.get("wet", 0.0) or 0.0)
  if w < WET_SHEEN:
    return rough, normal
  f = (w - WET_SHEEN) / (1.0 - WET_SHEEN)          # 0 at W02, 1 at W04
  b = g.bsdf
  if "Anisotropic" in b.inputs:                  # with the road UV's tangent, the highlights stretch along v
    b.inputs["Anisotropic"].default_value = 0.8 + 0.15 * f
    b.inputs["Anisotropic Rotation"].default_value = 0.0
    g.set(b.inputs["Tangent"], g.node("ShaderNodeTangent", direction_type="UV_MAP", uv_map="road").outputs[0])
  rough = g.math("MINIMUM", rough, 0.13 - 0.05 * f)
  if tracks is not None:
    floor = 0.07 - 0.04 * f
    rough = g.node("ShaderNodeMix", {0: g.math("MULTIPLY", tracks, 0.85), 2: rough, 3: floor},
                   data_type="FLOAT").outputs[0]
  rain = float(env.get("rain", 0.0) or 0.0)
  if rain > 0 and normal is not None:
    ripple = g.noise(g.node("ShaderNodeMapping", {"Vector": g.uv(), "Scale": (1.0, 0.35, 1.0)}).outputs[0], 9.0, 3)
    normal = g.bump(ripple.outputs[0], 0.04 + 0.05 * rain, 0.002, normal)
  return rough, normal


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
  rough, normal = _wet_sheen(g, rough, normal, env, tr)
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
    u = g.math("ABSOLUTE", g.node("ShaderNodeSeparateXYZ", {0: uv}).outputs[0])
    dry = g.remap(g.noise(uv, 0.012, 3).outputs[0], 0.44, 0.6, 0.0, 0.75)                # 50-100 m dry patches
    col = g.mix(dry, col, g.mix(1.0, col, (1.35, 1.05, 0.55), "MULTIPLY"))
    col = g.mix(1.0, col, g.remap(g.noise(uv, 0.05, 2).outputs[0], 0.35, 0.65, 0.72, 1.15), "MULTIPLY")
    rows = g.math("SINE", g.math("MULTIPLY", g.math("ADD", u, g.math("MULTIPLY", n2, 1.5)), 6.283 / 6.0))
    field = g.remap(u, 10.0, 16.0, 0.0, 1.0)                                         # mowing rows along the road
    col = g.mix(field, col, g.mix(1.0, col, g.remap(rows, -1.0, 1.0, 0.82, 1.1), "MULTIPLY"))
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


def concrete_material(name: str, env: dict, assets: Assets, slab: float = 1.5, tint: float = 1.0, joints: float = 0.0):
  """Concrete: the fetched scan, or procedural slabs `slab` metres square; tint scales its albedo, and joints > 0
  cuts paving joints every `slab` metres into the scan too (a walkway of flags)."""
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
    if joints:
      jt = g.node("ShaderNodeTexBrick", {"Vector": uv, "Scale": 1.0 / slab, "Mortar Size": 0.01, "Brick Width": 1.0,
                                          "Row Height": 1.0, "Color1": (1, 1, 1), "Color2": (1, 1, 1),
                                          "Mortar": (0, 0, 0)}, offset=0.5)
      col = g.mix(1.0, col, g.remap(jt.outputs[1], 0.0, 1.0, 1.0, 1.0 - joints), "MULTIPLY")
      normal = g.bump(g.math("SUBTRACT", 1.0, jt.outputs[1]), 0.4, 0.004, normal)
  else:
    br = g.node("ShaderNodeTexBrick", {"Vector": uv, "Scale": 1.0 / slab, "Mortar Size": 0.012,
                                        "Brick Width": 1.0, "Row Height": 1.0, "Color1": (0.44, 0.43, 0.41),
                                        "Color2": (0.40, 0.39, 0.37), "Mortar": (0.22, 0.22, 0.21)}, offset=0.0)
    n = g.noise(uv, 3.0, 4).outputs[0]
    col = g.mix(1.0, br.outputs[0], g.remap(n, 0.3, 0.7, 0.85, 1.12), "MULTIPLY")
    rough = 0.88
    normal = g.bump(g.math("ADD", g.math("MULTIPLY", br.outputs[1], -0.6), g.math("MULTIPLY", n, 0.2)), 0.3, 0.01)
  if tint != 1.0:
    col = g.mix(1.0, col, (tint,) * 3, "MULTIPLY")
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


KERB_W, KERB_H, KERB_BEVEL = 0.25, 0.15, 0.04   # concrete kerb: width, height above the road, top chamfer (m)


def sweep(name, centre, profile, mat, coll, s_ranges=None):
  """A cross-section [(d, z), ...] swept along the centre line, with UVs in metres (u along the profile, v along the
  road); s_ranges limits it to stretches of the road."""
  plen = [0.0]
  for (d0, z0), (d1, z1) in zip(profile, profile[1:]):
    plen.append(plen[-1] + math.hypot(d1 - d0, z1 - z0))
  verts, faces, uvs = [], [], []
  m = len(profile)
  prev = None
  for i, p in enumerate(centre):
    if s_ranges is not None and not any(lo <= p[3] <= hi for lo, hi in s_ranges):
      prev = None
      continue
    k = len(verts)
    verts += [offset(p, d, z) for d, z in profile]
    uvs += [(u, p[3]) for u in plen]
    if prev is not None:
      faces += [(prev + j, prev + j + 1, k + j + 1, k + j) for j in range(m - 1)]
    prev = k
  return mesh_object(name, verts, faces, mat, coll, uvs=uvs)


def kerb_profile(d_face: float, side: int, z0: float = -0.05, top: float = KERB_H, width: float = KERB_W,
                 bevel: float = KERB_BEVEL):
  """A kerb's cross-section: its face toward the road at d_face, its back `width` further out (side +1 left, -1
  right), the road-side top edge chamfered in two steps."""
  b = bevel
  return [(d_face, z0), (d_face, top - b), (d_face + side * 0.3 * b, top - 0.3 * b), (d_face + side * b, top),
          (d_face + side * width, top), (d_face + side * width, z0)]


def edge_features(r: dict, env: dict) -> dict:
  """The kerbs and walkways the render adds at the road edges, and how far past the road's outer edge the verge
  starts on each side. Visual only: export_scene.py's cross-section (carriageway, barrier, outer edges) is unchanged,
  and everything here lies outside the carriageway and beyond the barrier line.

  Highway: a kerb at the left verge (the outer edge of the paved strip) and on the right at the shoulder's outer
  edge, or, where the barrier stands on that edge, just behind the barrier's posts; with env walkway_m, a paved
  walkway that width behind the right kerb (where the lamp row stands). Urban: a kerb stone at the road edge of each
  sidewalk. Rural roads keep their gravel shoulders."""
  out = {"kerbs": [], "walkways": [], "verge": [0.0, 0.0]}
  left_out, right_out = r["outer"]
  if r["type"] == "highway":
    out["kerbs"].append((left_out, 1, -0.05))
    out["verge"][0] = KERB_W
    b = r.get("barrier")
    face = right_out if b is None else b - 0.25          # posts stand from b - 0.09 to b - 0.21
    out["kerbs"].append((face, -1, -0.05))
    back = face - KERB_W
    w = float(env.get("walkway_m", 0.0) or 0.0)
    if w:
      out["walkways"].append((back, back - w))
      back -= w
    out["verge"][1] = right_out - back
  elif r["type"] == "urban":
    for sfc in r["surfaces"]:
      if sfc["kind"] == "sidewalk":
        side = 1 if sfc["d0"] + sfc["d1"] > 0 else -1
        out["kerbs"].append((min(sfc["d0"], sfc["d1"], key=abs), side, -0.02))
  return out


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
  kerb = concrete_material("kerb_stone", env, assets, slab=1.0, tint=1.18)
  walkway = concrete_material("walkway", env, assets, slab=0.6, joints=0.6)
  steel = material("barrier", (0.55, 0.57, 0.6), rough=0.35, metal=0.8)

  for k, sfc in enumerate(r["surfaces"]):
    z = sfc.get("z", 0.0)
    strip(f"{sfc['kind']}_{k}", c, sfc["d0"], sfc["d1"], z, mats[sfc["kind"]], coll)
  edges = edge_features(r, env)
  for k, (d, side, z0) in enumerate(edges["kerbs"]):
    top = KERB_H + (0.004 if r["type"] == "urban" else 0.0)   # just proud of the sidewalk beside it
    sweep(f"kerb_{k}", c, kerb_profile(d, side, z0, top), kerb, coll)
  for k, (d0, d1) in enumerate(edges["walkways"]):
    strip(f"walkway_{k}", c, d0, d1, KERB_H - 0.01, walkway, coll)
    sweep(f"walkway_edge_{k}", c, [(d1, KERB_H - 0.01), (d1, -0.05)], kerb, coll)
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


def snow_on(m, snow: float):
  """Snow on the upward-facing parts of an existing material (a scanned plant's), broken up by noise."""
  g = Graph.__new__(Graph)
  g.nt = m.node_tree
  g.bsdf = next(n for n in g.nt.nodes if n.type == "BSDF_PRINCIPLED")
  sock = g.bsdf.inputs["Base Color"]
  col = sock.links[0].from_socket if sock.is_linked else tuple(sock.default_value)[:3]
  pos = g.node("ShaderNodeNewGeometry")
  n = g.noise(pos.outputs["Position"], 1.4, 4).outputs[0]
  up = g.node("ShaderNodeSeparateXYZ", {0: pos.outputs["Normal"]}).outputs[2]
  cover = g.remap(g.math("ADD", up, g.math("MULTIPLY", n, 0.4)), 0.55, 0.9, 0.0, 0.9 * snow)
  g.set(sock, g.mix(cover, col, SNOW_RGB))


class ScannedModel:
  """A scanned plant or piece of street furniture (a model slot of library/assets.yaml), kept out of the scene as a
  template; instances share its mesh data, as the road users share CarModel's. Each variant is one mesh of the glTF,
  or one of the slot's groups of meshes, centred on the origin with its base at Z = 0. Under snow its own materials
  get snow on top."""

  def __init__(self, slot: dict, env: dict):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(slot["files"]["gltf"]))
    new = [o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()
    meshes = {o.name: o for o in new if o.type == "MESH" and not any(x in o.name for x in slot.get("exclude", []))}
    self.slot, self.variants = slot, []
    for names in slot.get("groups") or [[n] for n in meshes]:
      objs = [meshes[n] for n in names if n in meshes]
      if len(objs) < len(names):                # a fallback asset without the slot's meshes: not this variant
        print(f"model: {slot['id']} has no {', '.join(n for n in names if n not in meshes)}")
        continue
      bb = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
      lo = [min(v[i] for v in bb) for i in range(3)]
      hi = [max(v[i] for v in bb) for i in range(3)]
      t = Matrix.Translation((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -max(lo[2], 0.0) - 0.02))
      self.variants.append(([(o.data, t @ o.matrix_world) for o in objs], hi[2] - lo[2]))
    for parts, _ in self.variants:
      for me, _ in parts:
        me.use_fake_user = True
    for o in new:
      bpy.data.objects.remove(o, do_unlink=True)
    if env.get("snow"):
      for m in {m for parts, _ in self.variants for me, _ in parts for m in me.materials if m and m.use_nodes}:
        snow_on(m, float(env["snow"]))
    print(f"model: {slot['id']} ({slot['role']}), {len(self.variants)} variant(s)")

  def place(self, rnd, name: str, coll, parent, loc, sc: float = 1.0, yaw: float | None = None):
    """An instance at loc: a plant as tall as the slot's height_m times sc and turned at random, furniture at its
    scanned size and turned to yaw."""
    parts, h = rnd.choice(self.variants)
    k = sc * rnd.uniform(*self.slot["height_m"]) / h if "height_m" in self.slot else 1.0
    yaw = rnd.uniform(0, 6.28) if yaw is None else yaw
    m0 = Matrix.Translation(loc) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Scale(k, 4)
    for j, (me, t) in enumerate(parts):
      ob = bpy.data.objects.new(name if len(parts) == 1 else f"{name}.{j:02d}", me)
      ob.parent = parent
      ob.matrix_basis = m0 @ t
      coll.objects.link(ob)

  def template(self) -> bpy.types.Collection:
    """The variants (one mesh each) as a collection outside the scene, for geometry-node instancing."""
    c = bpy.data.collections.new(f"{self.slot['id']}_variants")
    c.use_fake_user = True
    for parts, _ in self.variants:
      me, t = parts[0]
      ob = bpy.data.objects.new(me.name, me)
      ob.matrix_basis = t
      c.objects.link(ob)
    return c


def scanned_models(assets: Assets, env: dict, roles) -> dict[str, list[ScannedModel]]:
  """{role: [ScannedModel]} of the fetched model slots in roles."""
  out = {}
  for _, s in sorted(assets.slots.items()):
    if s.get("kind") == "model" and s.get("role") in roles:
      m = ScannedModel(s, env)
      if m.variants:
        out.setdefault(s["role"], []).append(m)
  return out


# the verge: (role, from, to metres beyond the road's outer edge, clumps per m², scale factor); the meadow thins out
# over the outer bands so it fades into the mown field instead of ending in a line
VERGE_BANDS = (("verge_short", 0.0, 1.0, 30.0, 1.0), ("verge_meadow", 0.5, 3.0, 24.0, 1.0),
               ("verge_meadow", 3.0, 4.0, 14.0, 0.9), ("verge_meadow", 4.0, 5.0, 7.0, 0.8),
               ("verge_meadow", 5.0, 6.5, 2.5, 0.68))


def _random_value(ng, typ: str, lo, hi):
  """The output of a Random Value node (FLOAT or INT) between lo and hi; its sockets share names across types."""
  n = ng.nodes.new("FunctionNodeRandomValue")
  n.data_type = typ
  t = "VALUE" if typ == "FLOAT" else typ
  sock = {(x.name, x.type): x for x in n.inputs}
  sock["Min", t].default_value, sock["Max", t].default_value = lo, hi
  return next(x for x in n.outputs if x.name == "Value" and x.type == t)


def verge_grass(r: dict, plants: dict, coll, env: dict | None = None):
  """Grass clumps beside both road edges (past the kerbs and walkways of edge_features), scattered by geometry nodes
  over a ribbon per band (only the instances render), each clump picked, turned and scaled at random."""
  margin = edge_features(r, env or {})["verge"]
  left_out, right_out = r["outer"][0] + margin[0], r["outer"][1] - margin[1]
  templates = {}
  for k, (role, a, b, density, f) in enumerate(VERGE_BANDS):
    if not plants.get(role):
      continue
    model = plants[role][0]
    if role not in templates:
      templates[role] = model.template()
    s0, s1 = model.slot["scale"]
    ng = bpy.data.node_groups.new(f"verge_{k}", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nodes, link = ng.nodes.new, ng.links.new
    gi, go = nodes("NodeGroupInput"), nodes("NodeGroupOutput")
    dist = nodes("GeometryNodeDistributePointsOnFaces")
    dist.inputs["Density"].default_value = density
    info = nodes("GeometryNodeCollectionInfo")
    info.inputs["Collection"].default_value = templates[role]
    info.inputs["Separate Children"].default_value = True
    info.inputs["Reset Children"].default_value = True
    inst = nodes("GeometryNodeInstanceOnPoints")
    inst.inputs["Pick Instance"].default_value = True
    rot = nodes("ShaderNodeCombineXYZ")
    link(gi.outputs[0], dist.inputs["Mesh"])
    link(dist.outputs["Points"], inst.inputs["Points"])
    link(info.outputs[0], inst.inputs["Instance"])
    link(_random_value(ng, "FLOAT", 0.0, 6.283), rot.inputs["Z"])
    link(rot.outputs[0], inst.inputs["Rotation"])
    link(_random_value(ng, "FLOAT", s0 * f, s1 * f), inst.inputs["Scale"])
    link(_random_value(ng, "INT", 0, 99), inst.inputs["Instance Index"])
    link(inst.outputs[0], go.inputs[0])
    for side, edge in ((1, left_out), (-1, right_out)):
      ob = strip(f"verge_{k}_{side}", r["centre"], edge + side * a, edge + side * b, 0.0, None, coll)
      ob.modifiers.new("verge", "NODES").node_group = ng


def lamp_mesh(name: str, height: float, reach: float, mat, bend: float = 1.3, r0: float = 0.12, r1: float = 0.055):
  """A tapered pole that bends out over the road: up the local Z axis, then a curve of radius `bend` into an arm that
  reaches `reach` metres toward -Y at `height`, rising a little toward its tip. One mesh, swept as rings along that
  path (the radius tapers from r0 at the foot to r1 at the tip)."""
  me = bpy.data.meshes.get(name)
  if me:
    return me
  path = [(0.0, 0.0, z) for z in [i * (height - bend) / 12 for i in range(13)]]
  for k in range(1, 9):                          # the bend: a quarter circle from vertical into the arm
    a = k / 8 * math.pi / 2
    path.append((0.0, -bend * (1 - math.cos(a)), height - bend + bend * math.sin(a)))
  arm = reach - bend
  for k in range(1, 7):                          # the arm, with a 3 degree upsweep
    path.append((0.0, -bend - arm * k / 6, height + math.tan(math.radians(3.0)) * arm * k / 6))
  segs = 10
  lengths = [0.0]
  for a, b in zip(path, path[1:]):
    lengths.append(lengths[-1] + math.dist(a, b))
  verts, faces = [], []
  for i, pt in enumerate(path):
    a, b = path[max(i - 1, 0)], path[min(i + 1, len(path) - 1)]
    t = Vector(b) - Vector(a)
    t.normalize()
    x = Vector((1.0, 0.0, 0.0))                  # the path lies in the YZ plane: X is normal to it throughout
    bi = t.cross(x)
    r = r0 + (r1 - r0) * lengths[i] / lengths[-1]
    for j in range(segs):
      q = 2 * math.pi * j / segs
      verts.append(Vector(pt) + r * (math.cos(q) * x + math.sin(q) * bi))
    if i:
      k0, k1 = (i - 1) * segs, i * segs
      faces += [(k0 + j, k0 + (j + 1) % segs, k1 + (j + 1) % segs, k1 + j) for j in range(segs)]
  n = len(path) - 1
  faces += [tuple(range(segs))[::-1], tuple(n * segs + j for j in range(segs))]
  me = bpy.data.meshes.new(name)
  me.from_pydata([tuple(v) for v in verts], [], faces)
  for p in me.polygons:
    p.use_smooth = True
  me.materials.append(mat)
  return me


def lamp_post(name: str, coll, parent, loc, yaw: float, night: bool, height: float = 10.0, reach: float = 2.4,
              light: str = "POINT", energy: float = 2000.0):
  """A street light: a tapered pole about `height` tall whose arm curves out over the carriageway (toward -Y in its
  own frame) to a slim luminaire; at night a lamp under the luminaire (a point light for streets, a downward spot for
  highways) and the luminaire's lens glowing. Procedural: Poly Haven has only short heritage posts."""
  steel = material("lamp_steel", (0.36, 0.37, 0.39), rough=0.4, metal=0.75)
  lens = material("luminaire_on" if night else "luminaire", (1.0, 0.86, 0.65) if night else (0.72, 0.73, 0.72),
                  rough=0.25, emit=35.0 if night else 0.0)
  tip_z = height + math.tan(math.radians(3.0)) * (reach - 1.3)
  meshes = bpy.data.meshes                       # one mesh of each part for every post of that size
  key = f"{height:.1f}_{reach:.1f}"
  parts = ((lamp_mesh(f"lamp_post_{key}", height, reach, steel), (0, 0, 0), 0.0),
           (meshes.get("lamp_head") or box_mesh("lamp_head", 0.26, 0.78, 0.07, 0.0, steel), (0, -reach + 0.12,
                                                                                               tip_z - 0.07), 0.05),
           (meshes.get(lens.name) or box_mesh(lens.name, 0.2, 0.62, 0.012, 0.0, lens), (0, -reach + 0.12,
                                                                                       tip_z - 0.08), 0.05))
  m0 = Matrix.Translation(loc) @ Matrix.Rotation(yaw, 4, "Z")
  for k, (me, xyz, tilt) in enumerate(parts):
    ob = bpy.data.objects.new(f"{name}.{k}", me)
    ob.parent = parent
    ob.matrix_basis = m0 @ Matrix.Translation(xyz) @ Matrix.Rotation(tilt, 4, "X")
    coll.objects.link(ob)
  if night:
    lt = bpy.data.objects.new(f"{name}_light", bpy.data.lights.new(f"{name}_light", light))
    lt.data.energy, lt.data.color, lt.data.shadow_soft_size = energy, (1.0, 0.82, 0.6), 0.3
    if light == "SPOT":
      lt.data.spot_size = math.radians(120)
    lt.location = m0 @ Vector((0, -reach + 0.12, tip_z - 0.25))
    coll.objects.link(lt)


def lamp_column(name: str, coll, parent, loc, yaw: float, night: bool):
  """An urban street light: a 10 m tapered pole with a 2 m curved arm over the carriageway (toward -Y)."""
  lamp_post(name, coll, parent, loc, yaw, night, height=10.0, reach=2.0, light="POINT", energy=2200.0)


def bus_shelter(name: str, coll, parent, loc, yaw: float, night: bool):
  """A glass bus shelter 3.6 m long and 1.4 m deep, open toward -Y (the carriageway), with a bench, a lit advert at
  one end and the stop sign at the kerb ahead of it. Procedural: Poly Haven has none."""
  glass = material("shelter_glass", (0.55, 0.62, 0.65), rough=0.05, alpha=0.3)
  frame = material("shelter_frame", (0.12, 0.13, 0.14), rough=0.4, metal=0.7)
  advert = material("shelter_advert_on" if night else "shelter_advert", (0.85, 0.82, 0.7), emit=2.5 if night else 0.8)
  pole = material("pole", (0.2, 0.2, 0.22), rough=0.5, metal=0.6)
  plate = material("bus_sign", (0.08, 0.32, 0.18), rough=0.4)
  parts = [("back", (3.6, 0.03, 2.0, 0.3), (0, 0.65), glass), ("roof", (3.9, 1.6, 0.08, 2.45), (0, 0.05), frame),
           ("advert", (0.12, 1.2, 1.9, 0.35), (1.8, 0.05), advert),
           ("side", (0.03, 1.2, 2.0, 0.3), (-1.8, 0.05), glass), ("bench", (2.0, 0.4, 0.06, 0.45), (0, 0.4), frame),
           ("sign", (0.04, 0.55, 0.55, 2.35), (2.6, -0.9), plate)]
  parts += [("post", (0.07, 0.07, 2.45, 0.0), xy, frame) for xy in ((-1.8, 0.65), (1.8, 0.65), (-1.8, -0.55),
                                                                    (1.8, -0.55))]
  m0 = Matrix.Translation(loc) @ Matrix.Rotation(yaw, 4, "Z")
  meshes = [(f"{n}{k}", box_mesh(f"{name}_{n}{k}", *dims, mat), Matrix.Translation((*xy, 0)))
            for k, (n, dims, xy, mat) in enumerate(parts)]
  meshes.append(("sign_pole", cyl_mesh(f"{name}_sign_pole", 0.035, 2.9, mat=pole),
                 Matrix.Translation((2.6, -0.9, 1.45))))
  for n, me, m in meshes:
    ob = bpy.data.objects.new(f"{name}_{n}", me)
    ob.parent = parent
    ob.matrix_basis = m0 @ m
    coll.objects.link(ob)


def street_furniture(items: list, r: dict, env: dict, coll, models: dict, trunk, crowns, rnd):
  """Build the items street_layout.layout lists: lamp columns and bus shelters (procedural), street trees (scanned or
  procedural), and bins, benches, hydrants and utility boxes where their model slots are fetched."""
  night = env.get("night", False)
  root = empty("street_furniture", coll)
  for k, it in enumerate(items):
    loc, kind = (it["x"], it["y"], 0.0), it["kind"]
    if kind == "lamp":
      lamp_column(f"lamp_{k}", coll, root, loc, it["yaw"], night)
    elif kind == "shelter":
      bus_shelter(f"shelter_{k}", coll, root, loc, it["yaw"], night)
    elif kind == "tree" and models.get("broadleaf"):
      rnd.choice(models["broadleaf"]).place(rnd, "tree", coll, root, loc, 0.75, it["yaw"])
    elif kind == "tree":
      sc = rnd.uniform(0.8, 1.3) * 0.55
      part("tree", trunk, root, coll, (loc[0], loc[1], 1.5 * sc)).scale = (sc, sc, sc)
      part("crown", rnd.choice(crowns), root, coll, (loc[0], loc[1], 4.6 * sc), (0, 0, it["yaw"])).scale = (
        sc, sc, sc * 1.15)
    elif models.get(kind):
      rnd.choice(models[kind]).place(rnd, kind, coll, root, loc, yaw=it["yaw"])


def build_scenery(r: dict, env: dict, assets: Assets | None = None, seed: int = 7, furniture: list | None = None,
                  buildings: bool = True):
  """Trees (broadleaf and conifer), shrubs, verge grass, buildings and street furniture beside the road, as the road's
  scenery asks: trees (a row either side, shrubs under them), open (sparse trees in fields), urban (buildings and the
  street furniture street_layout.layout lists); grass on rural and highway verges except under snow. Scanned plants
  and furniture where their model slots are fetched, procedural trees otherwise; the trees stand in the same places
  either way. buildings False leaves out the procedural boxes (scenery_kits.py draws the street's rows instead)."""
  assets = assets or no_assets()
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
    verge = kind in ("trees", "open") and not env.get("snow")
    roles = {"urban": {"broadleaf", "bin", "bench", "hydrant", "utility_box"}, "open": {"broadleaf", "conifer"},
             "trees": {"broadleaf", "conifer", "shrub"}}
    plants = scanned_models(assets, env, roles[kind] | ({"verge_short", "verge_meadow"} if verge else set()))
    prnd = random.Random(seed + 1)               # the scanned plants' own draws: the trees keep their places
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
          me, turn, stretch = rnd.choice(conifers), rnd.uniform(0, 6.28), rnd.uniform(1.0, 1.4)
          if plants.get("conifer"):
            prnd.choice(plants["conifer"]).place(prnd, "conifer", coll, root, (x, y, 0.0), sc)
          else:
            t = part("conifer", me, root, coll, (x, y, 0.0), (0, 0, turn))
            t.scale = (sc, sc, sc * stretch)
        else:
          me, turn = rnd.choice(crowns), rnd.uniform(0, 6.28)
          if kind == "urban":
            pass                                 # street trees come from street_layout; the draws keep the buildings
          elif plants.get("broadleaf"):
            prnd.choice(plants["broadleaf"]).place(prnd, "tree", coll, root, (x, y, 0.0), sc)
          else:
            t = part("tree", trunk, root, coll, (x, y, 1.5 * sc))
            t.scale = (sc, sc, sc)
            cr = part("crown", me, root, coll, (x, y, 3.0 * sc + 1.6 * sc), (0, 0, turn))
            cr.scale = (sc, sc, sc * 1.15)
        if kind == "trees" and plants.get("shrub") and prnd.random() < 0.6:
          sx, sy, _ = offset(p, d - side * prnd.uniform(1.5, 3.0))
          prnd.choice(plants["shrub"]).place(prnd, "shrub", coll, root, (sx, sy, 0.0))
        s += step * rnd.uniform(0.6, 1.4)
    if verge:
      verge_grass(r, plants, coll, env)
  if kind == "urban":
    night = env.get("night", False)
    walls = [(0.55, 0.5, 0.45), (0.45, 0.42, 0.4), (0.62, 0.58, 0.5), (0.35, 0.33, 0.33), (0.5, 0.38, 0.3)]
    facades = [facade_material(f"facade_{k}", w, lit=1.5 if night else 0.0) for k, w in enumerate(walls)]
    roof = material("roof", SNOW_RGB if env.get("snow") else (0.2, 0.2, 0.21), rough=0.8)
    root = empty("buildings", coll)
    for side, d_face in ((1, left_out + 1.0), (-1, right_out - 1.0)) if buildings else ():
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
    street_furniture(furniture or [], r, env, coll, plants, trunk, crowns, random.Random(seed + 3))
  return coll


# ------------------------------------------------------------------------------------------------- environment
def sun_colour(elev_deg: float):
  """Warm near the horizon, near white high up."""
  f = max(0.0, min(1.0, (elev_deg - 3.0) / 35.0))
  return (1.0, 0.7 + 0.24 * f, 0.45 + 0.42 * f)


def build_environment(env: dict, heading: float, assets: Assets | None = None):
  """Sky and sun. env (library/conditions.yaml): sky (clear, partly, overcast, night), sun ('behind', 'ahead': low sun
  in the driver's eyes, 'side'), sun_offset (degrees from the direction of travel, negative = left; replaces the
  preset's), sun_elevation (degrees, raised to sun_elevation_min), sun_strength, night,
  sky_strength (an overcast sky's brightness relative to the default: below 1 for a heavier, moodier sky).
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
  if "sun_offset" in env:                       # degrees from the direction of travel, negative = left (sun_glare.py)
    az = heading - math.radians(env["sun_offset"])
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
    bg.inputs["Strength"].default_value *= env.get("sky_strength", 1.0)   # a heavier, moodier overcast
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
CLEAR_LENS_M = 3.0            # no rain or snow falls within this distance (on the ground plane) of a camera


def snowflake_material():
  """A soft, round flake: white, with alpha falling off from the middle of its quad to the rim (UV radius)."""
  m = bpy.data.materials.get("snowflake")
  if m:
    return m
  m = material("snowflake", (0.95, 0.96, 1.0), rough=0.7, emit=0.2)
  nt = m.node_tree
  uv = nt.nodes.new("ShaderNodeTexCoord")
  dist = nt.nodes.new("ShaderNodeVectorMath")
  dist.operation = "DISTANCE"
  dist.inputs[1].default_value = (0.5, 0.5, 0.0)
  fall = nt.nodes.new("ShaderNodeMapRange")
  fall.interpolation_type = "SMOOTHSTEP"
  fall.inputs["From Min"].default_value, fall.inputs["From Max"].default_value = 0.1, 0.5
  fall.inputs["To Min"].default_value, fall.inputs["To Max"].default_value = 0.9, 0.0
  nt.links.new(uv.outputs["UV"], dist.inputs[0])
  nt.links.new(dist.outputs["Value"], fall.inputs["Value"])
  nt.links.new(fall.outputs["Result"], nt.nodes["Principled BSDF"].inputs["Alpha"])
  return m


def lens_zones(follow, cams, frames: int, step: int = 6) -> list[tuple[float, float]]:
  """Where each camera stands in `follow`'s frame (x, y), sampled every `step` frames."""
  scene, out = bpy.context.scene, []
  for f in range(1, frames + 1, step):
    scene.frame_set(f)
    inv = follow.matrix_world.inverted()
    out += [tuple((inv @ c.matrix_world.translation)[:2]) for c in cams]
  scene.frame_set(1)
  return out


def build_weather(env: dict, follow, centre, frames: int, fps: int, cams=(), seed: int = 11):
  """Fog or haze (a volume layer over the scene with extinction 3 / visibility, from visibility_m), and falling rain
  or snow in a box that travels with `follow` (the ego), kept CLEAR_LENS_M from every camera in `cams` so that no
  drop or flake fills a corner of a view. Snow is soft round flakes, a little longer than wide as if blurred by the
  fall. Returns the collection (hidden from the top camera, which shows the layout)."""
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
  lenses = lens_zones(follow, cams, frames) if cams else []
  for kind, amount in (("rain", env.get("rain", 0.0)), ("snow", env.get("snow", 0.0) * 0.8)):
    if not amount:
      continue
    period = 14.0
    speed = 9.0 if kind == "rain" else 1.1
    n = int((4500 if kind == "rain" else 6000) * amount)
    verts, faces, uvs = [], [], []
    for i in range(n):
      x, y, z = rnd.uniform(-18, 70), rnd.uniform(-16, 16), rnd.uniform(0, period)
      if any(math.hypot(x - lx, y - ly) < CLEAR_LENS_M for lx, ly in lenses):
        continue
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
          # a quad facing along the road (the chase and driver views), turned a little at random, 1.6 times as tall
          # as wide; the material makes it a soft disc, the height a short blur of the fall
          r = rnd.uniform(0.015, 0.03)
          a, hz = rnd.uniform(-0.5, 0.5), 1.6 * r
          dx, dy = r * math.sin(a), r * math.cos(a)
          verts += [(x + dx, y - dy, zz - hz), (x - dx, y + dy, zz - hz), (x - dx, y + dy, zz + hz),
                    (x + dx, y - dy, zz + hz)]
          faces.append((k, k + 1, k + 2, k + 3))
      uvs += [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)] * 2
    mat = (material("rain_streak", (0.75, 0.78, 0.82), rough=0.1, alpha=0.18, emit=0.15) if kind == "rain"
           else snowflake_material())
    ob = mesh_object(kind, verts, faces, mat, coll, uvs=uvs if kind == "snow" else None)
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


# ------------------------------------------------------------------------------------------------- surroundings
# What the picture adds around the road (environments.yaml and conditions.yaml env, library/README.md §5): far hills
# and haze, rolling ground, 3D verge plants, distant objects, cloud shadows, wheel spray, road wear and a camera
# look. Visual only, like edge_features: the ground and objects stand beyond the verges (the terrain changes height
# only from 7 m past the verge start), the wear is flat texture on the asphalt under the markings, and nothing here
# is read by export_scene.py, so every contact, event, gap and TTC is the same with or without it.

TERRAINS = ("rolling", "ditch", "embankment")
DISTANT = ("pylons", "billboard", "farm", "flyover")
LOOK_FRAC = 0.4               # the far scenery is laid out around the chase camera at this fraction of the clip


def _centre_at(centre, s: float):
  i = min(max(int(round(s - centre[0][3])), 0), len(centre) - 1)
  return centre[i]


def _linear(ob):
  ad = ob.animation_data
  bags = []
  try:
    bags = list(ad.action.fcurves)
  except AttributeError:                        # Blender 5: layered actions
    bags = [fc for layer in ad.action.layers for st in layer.strips for bag in st.channelbags for fc in bag.fcurves]
  for fc in bags:
    for kp in fc.keyframe_points:
      kp.interpolation = "LINEAR"


def _smooth01(u: float) -> float:
  u = min(max(u, 0.0), 1.0)
  return u * u * (3 - 2 * u)


class Frame:
  """Road coordinates of a scene: (s, d) to the world and back, where each verge starts, and the ground height the
  environment's `terrain` gives beyond it (0 on and beside the road)."""

  def __init__(self, sc: dict, env: dict, rear: bool = False):
    self.sc, self.r = sc, sc["road"]
    self.rear = rear                            # the chase camera looks back past the ego (street_layout.rear_view)
    self.c = self.r["centre"]
    self.env = env
    left_out, right_out = self.r["outer"]
    m = edge_features(self.r, env)["verge"]
    self.edge = {1: left_out + m[0], -1: right_out - m[1]}
    self.grass_z = next((s.get("z", 0.0) for s in self.r["surfaces"] if s["kind"] == "grass"), -0.03)
    self.kind = self.r["type"]
    self.terrain = env.get("terrain") if env.get("terrain") in TERRAINS else None
    self.seed = random.Random(sc.get("variant_of") or sc["id"]).random() * 100

  def at(self, s):
    return _centre_at(self.c, s)

  def world(self, s, d, z=0.0):
    return offset(self.at(s), d, z)

  def sd(self, x, y):
    p = min(self.c, key=lambda q: (q[0] - x) ** 2 + (q[1] - y) ** 2)
    d = -(x - p[0]) * math.sin(p[2]) + (y - p[1]) * math.cos(p[2])
    along = (x - p[0]) * math.cos(p[2]) + (y - p[1]) * math.sin(p[2])
    return p[3] + along, d

  def rel(self, d):
    """(side, metres beyond that side's verge start) of a lateral offset; None on the road."""
    if d >= self.edge[1]:
      return 1, d - self.edge[1]
    if d <= self.edge[-1]:
      return -1, self.edge[-1] - d
    return None

  def near_profile(self, side, dr):
    """Height change within 18 m of the verge start: a shallow drainage ditch (ditch), or an embankment on the left
    with a ditch at its foot and a cutting on the right (embankment)."""
    if self.terrain == "ditch":
      return -0.5 * math.sin(math.pi * min(max((dr - 7.0) / 3.2, 0.0), 1.0)) ** 2
    if self.terrain == "embankment":
      if side == 1:
        return -3.0 * _smooth01((dr - 7.5) / 7.5) - 0.35 * math.sin(math.pi * min(max((dr - 15.0) / 3.0, 0.0), 1.0)) ** 2
      return 4.5 * _smooth01((dr - 9.0) / 8.0)
    return 0.0

  def hills(self, x, y, dr):
    """Rolling ground from 15 m past the verge start, growing with the distance."""
    if self.terrain is None or dr <= 15.0:
      return 0.0
    n = noise.fractal(Vector((x / 170.0 + self.seed, y / 170.0, 0.3)), 0.6, 2.1, 4)
    return _smooth01((dr - 15.0) / 35.0) * (3.0 + 0.025 * dr) * n

  def ground(self, x, y, d):
    rd = self.rel(d)
    if rd is None:
      return 0.0
    side, dr = rd
    return self.near_profile(side, dr) + self.hills(x, y, dr)

  def ego_s(self, frame):
    x, y, _ = self.sc["actors"][0]["poses"][frame - 1]
    return self.sd(x, y)[0]

  def camera_span(self, behind: float, ahead: float):
    """The stretch of road the chase camera sees over the clip: from `behind` metres before the ego's start to
    `ahead` past its end (the other way round for a rear view)."""
    a, b = self.ego_s(1), self.ego_s(len(self.sc["t"]))
    return (min(a, b) - ahead, max(a, b) + behind) if self.rear else (min(a, b) - behind, max(a, b) + ahead)


def grid(name, F: Frame, side, d_rel_list, s_step, zoff, mat, coll, s_range=None):
  """A ribbon over the given offsets beyond one verge, following the ground height; road UVs in metres."""
  c = F.c
  s0, s1 = (c[0][3], c[-1][3]) if s_range is None else s_range
  s0, s1 = max(s0, c[0][3]), min(s1, c[-1][3])
  ss = [s0 + s_step * i for i in range(int((s1 - s0) / s_step) + 1)]
  verts, faces, uvs = [], [], []
  n = len(d_rel_list)
  for i, s in enumerate(ss):
    p = F.at(s)
    for dr in d_rel_list:
      d = F.edge[side] + side * dr
      x, y, _ = offset(p, d)
      verts.append((x, y, F.grass_z + zoff + F.near_profile(side, dr) + F.hills(x, y, dr)))
      uvs.append((d, p[3]))
    if i:
      a, b = (i - 1) * n, i * n
      for j in range(n - 1):
        faces.append((a + j, a + j + 1, b + j + 1, b + j) if side == 1 else (a + j, b + j, b + j + 1, a + j + 1))
  ob = mesh_object(name, verts, faces, mat, coll, uvs=uvs)
  for poly in ob.data.polygons:
    poly.use_smooth = True
  return ob


# ------------------------------------------------------------------------------------------------- materials
def node_mat(name):
  m = bpy.data.materials.new(name)
  m.use_nodes = True
  return m, Graph(m)


def far_field_material(env: dict):
  """Fields seen from afar: a patchwork of crop colours (Voronoi cells), hedges darker; white under snow."""
  m, g = node_mat("far_fields")
  tc = g.node("ShaderNodeTexCoord").outputs["Object"]
  vor = g.node("ShaderNodeTexVoronoi", {"Vector": tc, "Scale": 0.006})
  ramp = g.node("ShaderNodeValToRGB", {0: vor.outputs[2] if len(vor.outputs) > 2 else vor.outputs[1]})
  els = ramp.color_ramp.elements
  els[0].color, els[1].color = (0.04, 0.075, 0.02, 1), (0.11, 0.1, 0.045, 1)
  e = els.new(0.45)
  e.color = (0.06, 0.1, 0.028, 1)
  e = els.new(0.75)
  e.color = (0.075, 0.085, 0.03, 1)
  edge = g.node("ShaderNodeTexVoronoi", {"Vector": tc, "Scale": 0.006}, feature="DISTANCE_TO_EDGE")
  hedge = g.remap(edge.outputs[0], 0.0, 0.03, 1.0, 0.0)
  col = g.mix(hedge, ramp.outputs[0], (0.025, 0.04, 0.02))
  col = g.mix(1.0, col, g.remap(g.noise(tc, 0.02, 3).outputs[0], 0.3, 0.7, 0.8, 1.15), "MULTIPLY")
  if env.get("snow"):
    col = g.mix(0.85 * float(env["snow"]), col, SNOW_RGB)
  g.finish(col, 0.9)
  return m


def far_tree_material():
  """Woods seen from a kilometre or more: dark, slightly varied green."""
  m, g = node_mat("far_trees")
  tc = g.node("ShaderNodeTexCoord").outputs["Object"]
  n = g.noise(tc, 0.08, 4).outputs[0]
  col = g.mix(g.remap(n, 0.35, 0.65, 0.0, 1.0), (0.018, 0.032, 0.016), (0.04, 0.06, 0.025))
  g.finish(col, 0.95)
  return m


def build_horizon(F: Frame, coll, cam_xy):
  """env horizon: far fields to 2 km under the road's own ground, a tree line ringing the view at about 1 to 1.6 km
  and hills from 2 to 5.6 km, centred on the chase camera."""
  cx, cy = cam_xy
  fields = far_field_material(F.env)
  segs = 900
  # far fields: a disk under everything (the road's grass covers it near by)
  rings = [0, 350, 600, 1000, 1500, 2100]
  verts, faces = [], []
  for k, r in enumerate(rings):
    for i in range(segs):
      a = 2 * math.pi * i / segs
      verts.append((cx + r * math.cos(a), cy + r * math.sin(a), -0.25 - (0 if r < 500 else 0.002 * (r - 500))))
      if k:
        faces.append(((k - 1) * segs + i, (k - 1) * segs + (i + 1) % segs, k * segs + (i + 1) % segs, k * segs + i))
  mesh_object("far_fields", verts, faces, fields, coll)
  # hills: an annulus, its height a smooth noise of the angle, rising with the distance
  radial = [2000, 2400, 2900, 3500, 4200, 5000, 5600]
  verts, faces = [], []
  segs = 1440
  for k, r in enumerate(radial):
    rise = min((r - 2000) / 2200.0, 1.0)
    for i in range(segs):
      a = 2 * math.pi * i / segs
      x, y = cx + r * math.cos(a), cy + r * math.sin(a)
      h = 60 + 110 * (0.5 + 0.5 * noise.fractal(Vector((x / 1800.0, y / 1800.0, 1.7)), 0.55, 2.0, 4))
      verts.append((x, y, -3.0 + h * rise ** 1.3))
      if k:
        faces.append(((k - 1) * segs + i, (k - 1) * segs + (i + 1) % segs, k * segs + (i + 1) % segs, k * segs + i))
  ob = mesh_object("hills", verts, faces, fields, coll)
  for p in ob.data.polygons:
    p.use_smooth = True
  # tree line: a vertical band, its top bumpy like crowns, its radius wandering
  trees = far_tree_material()
  verts, faces = [], []
  segs = 3600
  for i in range(segs):
    a = 2 * math.pi * i / segs
    rr = 1300 + 350 * noise.noise(Vector((math.cos(a) * 5.0, math.sin(a) * 5.0, 4.2)))
    x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
    top = 10 + 5 * noise.noise(Vector((x / 60.0, y / 60.0, 0.5))) + 4 * abs(noise.noise(Vector((x / 7.0, y / 7.0, 2.0))))
    gap = noise.noise(Vector((x / 250.0, y / 250.0, 9.0)))
    if gap < -0.15:                             # open stretches between woods
      top = 0.5
    verts += [(x, y, -2.0), (x, y, top)]
    j = 2 * i
    faces.append((j, (j + 2) % (2 * segs), (j + 3) % (2 * segs), j + 1))
  mesh_object("tree_line", verts, faces, trees, coll)


def build_haze(coll, cam_xy, km: float):
  """env haze_km (with horizon): aerial perspective, a homogeneous slightly blue volume 160 m deep for a
  meteorological visibility of km, so the distance fades bluish while the sky above stays clear."""
  cx, cy = cam_xy
  ob = bpy.data.objects.new("aerial_haze", box_mesh("aerial_haze_box", 12000.0, 12000.0, 160.0, -5.0))
  ob.location = (cx, cy, 0.0)
  coll.objects.link(ob)
  m = bpy.data.materials.new("aerial_haze")
  m.use_nodes = True
  nt = m.node_tree
  nt.nodes.remove(nt.nodes["Principled BSDF"])
  vol = nt.nodes.new("ShaderNodeVolumePrincipled")
  vol.inputs["Density"].default_value = 3.0 / (1000.0 * km)
  vol.inputs["Color"].default_value = (0.7, 0.82, 1.0, 1.0)
  vol.inputs["Anisotropy"].default_value = 0.5
  nt.links.new(vol.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
  ob.data.materials.append(m)


def build_terrain(F: Frame, coll):
  """env terrain: the two flat 400 m grass strips of the cross-section give way to ground that follows F.ground (the
  ditch, embankment or cutting near by, rolling from 15 m past the verge start), and the scenery stands on it."""
  grass = bpy.data.materials.get("grass")
  for ob in list(bpy.data.collections["road"].objects):
    if ob.name.startswith("grass_") and max(abs(v.co.x) + abs(v.co.y) for v in ob.data.vertices) > 0:
      dims = ob.dimensions
      if max(dims.x, dims.y) > 300:
        bpy.data.objects.remove(ob, do_unlink=True)
  outer = {1: F.r["outer"][0], -1: F.r["outer"][1]}
  drs = [x * 0.5 for x in range(0, 41)] + list(range(22, 60, 2)) + list(range(60, 401, 8))
  for side in (1, -1):
    start = side * (outer[side] - F.edge[side])           # the grass begins at the road's outer edge
    grid(f"terrain_{side}", F, side, [start] + [d for d in drs if d > start], 2.0, 0.0, grass, coll)
  snap_scenery(F)


def snap_scenery(F: Frame):
  """Stand trees, shrubs, lamps and posts on the new ground."""
  moved = 0
  for cname in ("scenery", "props"):
    cl = bpy.data.collections.get(cname)
    if not cl:
      continue
    for ob in cl.objects:
      if ob.type not in ("MESH", "EMPTY") or ob.name.startswith(("verge_", "terrain", "far_", "hills", "tree_line")):
        continue
      if ob.parent is not None and ob.parent.parent is not None:
        continue
      if ob.type == "EMPTY" and ob.children:
        continue
      x, y = ob.matrix_world.translation[:2]
      s, d = F.sd(x, y)
      dz = F.ground(x, y, d)
      if abs(dz) > 1e-4:
        ob.location.z += dz
        moved += 1
  print(f"terrain: {F.terrain}, {moved} objects stood on the new ground")


def blade_meshes():
  """Clumps of grass blades, a weed rosette with a stalk, three wildflowers."""
  rnd = random.Random(5)
  out = {}

  def clump(name, n, hmin, hmax, wid):
    verts, faces = [], []
    for b in range(n):
      a = rnd.uniform(0, 2 * math.pi)
      r0 = rnd.uniform(0, 0.05)
      bx, by = r0 * math.cos(a), r0 * math.sin(a)
      h = rnd.uniform(hmin, hmax)
      lean = rnd.uniform(0.15, 0.6)
      la = rnd.uniform(0, 2 * math.pi)
      w = wid * rnd.uniform(0.7, 1.3)
      seg = 4
      k0 = len(verts)
      for i in range(seg + 1):
        t = i / seg
        off = lean * h * t * t
        cx, cy, cz = bx + off * math.cos(la), by + off * math.sin(la), h * t * (1 - 0.25 * lean * t)
        ww = w * (1 - t) + 0.0005
        px, py = -math.sin(la) * ww, math.cos(la) * ww
        verts += [(cx - px, cy - py, cz), (cx + px, cy + py, cz)]
        if i:
          j = k0 + 2 * i
          faces.append((j - 2, j - 1, j + 1, j))
    return verts, faces

  for k in range(3):
    v, f = clump(f"blades{k}", 9, 0.12, 0.42 if k < 2 else 0.6, 0.006)
    out[f"blades{k}"] = (v, f, "grass_blade")
  # weed: a rosette of broad leaves and a seed stalk
  verts, faces = [], []
  for i in range(7):
    a = 2 * math.pi * i / 7 + rnd.uniform(-0.2, 0.2)
    L, W = rnd.uniform(0.12, 0.2), 0.03
    ca, sa = math.cos(a), math.sin(a)
    k0 = len(verts)
    verts += [(0, 0, 0.01), (L * 0.5 * ca - W * sa, L * 0.5 * sa + W * ca, 0.04), (L * ca, L * sa, 0.05),
              (L * 0.5 * ca + W * sa, L * 0.5 * sa - W * ca, 0.04)]
    faces.append((k0, k0 + 1, k0 + 2, k0 + 3))
  k0 = len(verts)
  verts += [(-0.004, 0, 0), (0.004, 0, 0), (0.01, 0.004, 0.55), (0.0, 0.004, 0.55)]
  faces.append((k0, k0 + 1, k0 + 2, k0 + 3))
  out["weed"] = (verts, faces, "weed_leaf")
  return out


def flower_mesh(name, petal_mat, stem_mat):
  """A thin stem with a flattened round flower head."""
  me = bpy.data.meshes.new(name)
  bm = bmesh.new()
  stem = bmesh.ops.create_cone(bm, cap_ends=False, segments=4, radius1=0.003, radius2=0.002, depth=0.45)
  bmesh.ops.translate(bm, vec=(0, 0, 0.225), verts=stem["verts"])
  for f in bm.faces:
    f.material_index = 1
  head = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.022)
  bmesh.ops.scale(bm, vec=(1, 1, 0.45), verts=head["verts"])
  bmesh.ops.translate(bm, vec=(0, 0, 0.46), verts=head["verts"])
  bm.to_mesh(me)
  bm.free()
  me.materials.append(petal_mat)
  me.materials.append(stem_mat)
  return me


def plant_material(name, rgb, var=0.35):
  """Leaves and blades: a green that dries toward straw at random per instance, letting some light through."""
  m, g = node_mat(name)
  rnd = g.node("ShaderNodeObjectInfo").outputs["Random"]
  dry = g.mix(g.remap(rnd, 0.0, 1.0, 0.0, var), rgb, (0.32, 0.27, 0.12))
  b = g.bsdf
  for k, v in (("Subsurface Weight", 0.0), ("Transmission Weight", 0.0)):
    if k in b.inputs:
      b.inputs[k].default_value = v
  g.finish(dry, 0.6)
  b.inputs["Specular IOR Level"].default_value = 0.3
  # thin leaves: some light through (translucent mix)
  out = m.node_tree.nodes["Material Output"]
  tr = m.node_tree.nodes.new("ShaderNodeBsdfTranslucent")
  g.set(tr.inputs["Color"], dry)
  mix = m.node_tree.nodes.new("ShaderNodeMixShader")
  mix.inputs[0].default_value = 0.3
  m.node_tree.links.new(b.outputs[0], mix.inputs[1])
  m.node_tree.links.new(tr.outputs[0], mix.inputs[2])
  m.node_tree.links.new(mix.outputs[0], out.inputs["Surface"])
  return m


# (from, to metres past the verge start, clumps per m²): dense by the road, thinning into the ground texture by 40 m
VERGE_PLANT_BANDS = ((0.0, 6.0, 80.0), (6.0, 12.0, 50.0), (12.0, 20.0, 24.0), (20.0, 30.0, 9.0), (30.0, 40.0, 3.0))


def build_verge_plants(F: Frame, coll):
  """env verge_plants: instanced grass blades, weeds and a few wildflowers over both verges, within 40 m of the road
  edge along the stretch the chase camera sees (none under snow, like the scanned verge grass)."""
  if F.kind == "urban" or F.env.get("snow"):
    return
  meshes = blade_meshes()
  mats = {"grass_blade": plant_material("grass_blade", (0.07, 0.16, 0.035)),
          "weed_leaf": plant_material("weed_leaf", (0.06, 0.13, 0.03), 0.2)}
  tmpl = bpy.data.collections.new("grass_templates")
  tmpl.use_fake_user = True
  for name, (v, f, mat) in meshes.items():
    mesh_object(name, v, f, mats[mat], tmpl)
  stem = plant_material("flower_stem", (0.06, 0.14, 0.03), 0.1)
  for k, rgb in enumerate(((0.9, 0.7, 0.05), (0.9, 0.9, 0.85), (0.45, 0.2, 0.6))):
    me = flower_mesh(f"flower{k}", material(f"petal{k}", rgb, rough=0.5), stem)
    ob = bpy.data.objects.new(f"flower{k}", me)
    tmpl.objects.link(ob)
  # pick weights: blades most, a few weeds and flowers (Pick Instance takes an index; repeat blades)
  pick = bpy.data.collections.new("grass_pick")
  pick.use_fake_user = True
  order = ["blades0"] * 10 + ["blades1"] * 10 + ["blades2"] * 4 + ["weed"] * 2 + ["flower0", "flower1", "flower2"]
  for j, n in enumerate(order):
    src = bpy.data.objects[n]
    ob = bpy.data.objects.new(f"pick{j:02d}_{n}", src.data)
    pick.objects.link(ob)

  ng = bpy.data.node_groups.new("verge_plants", "GeometryNodeTree")
  ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
  ng.interface.new_socket("Density", in_out="INPUT", socket_type="NodeSocketFloat")
  ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
  nodes, link = ng.nodes.new, ng.links.new
  gi, go = nodes("NodeGroupInput"), nodes("NodeGroupOutput")
  dist = nodes("GeometryNodeDistributePointsOnFaces")
  info = nodes("GeometryNodeCollectionInfo")
  info.inputs["Collection"].default_value = pick
  info.inputs["Separate Children"].default_value = True
  info.inputs["Reset Children"].default_value = True
  inst = nodes("GeometryNodeInstanceOnPoints")
  inst.inputs["Pick Instance"].default_value = True
  rot = nodes("ShaderNodeCombineXYZ")
  link(gi.outputs[0], dist.inputs["Mesh"])
  link(gi.outputs[1], dist.inputs["Density"])
  link(dist.outputs["Points"], inst.inputs["Points"])
  link(info.outputs[0], inst.inputs["Instance"])
  link(_random_value(ng, "FLOAT", 0.0, 6.283), rot.inputs["Z"])
  link(rot.outputs[0], inst.inputs["Rotation"])
  link(_random_value(ng, "FLOAT", 0.6, 1.4), inst.inputs["Scale"])
  link(_random_value(ng, "INT", 0, len(order) - 1), inst.inputs["Instance Index"])
  link(inst.outputs[0], go.inputs[0])

  rng = F.camera_span(25.0, 130.0)
  for k, (a, b, dens) in enumerate(VERGE_PLANT_BANDS):
    n = max(int(b - a), 1)
    drs = [a + (b - a) * i / n for i in range(n + 1)]
    for side in (1, -1):
      ob = grid(f"verge_plants_{k}_{side}", F, side, drs, 2.0, 0.005, None, coll, rng)
      mod = ob.modifiers.new("grass", "NODES")
      band = bpy.data.node_groups.get(f"verge_plants_{k}") or ng.copy()
      band.name = f"verge_plants_{k}"
      sock = next(i for i in band.interface.items_tree if getattr(i, "name", "") == "Density")
      sock.default_value = dens
      mod.node_group = band


def lattice_pylon(name, coll, loc, yaw, h=32.0):
  steel = material("pylon_steel", (0.42, 0.43, 0.45), rough=0.5, metal=0.6)
  root = empty(name, coll)
  root.location, root.rotation_euler = loc, (0, 0, yaw)
  me = bpy.data.meshes.new(name)
  bm = bmesh.new()

  def beam(p, q, r=0.09):
    p, q = Vector(p), Vector(q)
    d = q - p
    geo = bmesh.ops.create_cone(bm, cap_ends=False, segments=4, radius1=r, radius2=r, depth=d.length)
    rot = d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=rot, verts=geo["verts"])
    bmesh.ops.translate(bm, vec=(p + q) / 2, verts=geo["verts"])

  base, top = 3.2, 0.9
  lv = [0, 0.35 * h, 0.6 * h, 0.8 * h, h]
  wid = [base + (top - base) * z / h for z in lv]
  for sx in (-1, 1):
    for sy in (-1, 1):
      for z0, z1, w0, w1 in zip(lv, lv[1:], wid, wid[1:]):
        beam((sx * w0, sy * w0, z0), (sx * w1, sy * w1, z1), 0.12)
  for z0, z1, w0, w1 in zip(lv, lv[1:], wid, wid[1:]):          # cross bracing on the four faces
    for a, b in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
      beam((a[0] * w0, a[1] * w0, z0), (b[0] * w1, b[1] * w1, z1), 0.05)
      beam((b[0] * w0, b[1] * w0, z0), (a[0] * w1, a[1] * w1, z1), 0.05)
  arms = (0.62 * h, 0.82 * h)
  for z, span in zip(arms, (9.0, 7.0)):
    beam((-span, 0, z), (span, 0, z), 0.14)
    beam((-span, 0, z), (-1.2, 0, z + 2.0), 0.06)
    beam((span, 0, z), (1.2, 0, z + 2.0), 0.06)
  beam((0, 0, h), (0, 0, h + 3.0), 0.08)
  bm.to_mesh(me)
  bm.free()
  me.materials.append(steel)
  ob = bpy.data.objects.new(name + "_frame", me)
  ob.parent = root
  coll.objects.link(ob)
  return root, [(x, 0.0, z - 1.6) for z, span in zip(arms, (9.0, 7.0)) for x in (-span + 0.4, span - 0.4)]


def catenary(name, coll, p, q, sag, mat):
  cu = bpy.data.curves.new(name, "CURVE")
  cu.dimensions = "3D"
  cu.bevel_depth = 0.035
  sp = cu.splines.new("POLY")
  n = 24
  sp.points.add(n)
  for i in range(n + 1):
    t = i / n
    x = p[0] + (q[0] - p[0]) * t
    y = p[1] + (q[1] - p[1]) * t
    z = p[2] + (q[2] - p[2]) * t - sag * 4 * t * (1 - t)
    sp.points[i].co = (x, y, z, 1.0)
  ob = bpy.data.objects.new(name, cu)
  cu.materials.append(mat)
  coll.objects.link(ob)


def billboard(F: Frame, coll, s, d, facing):
  x, y, _ = F.world(s, d)
  z0 = F.ground(x, y, d)
  h = F.at(s)[2]
  root = empty("billboard", coll)
  root.location, root.rotation_euler = (x, y, z0), (0, 0, h + facing)
  grey = material("bb_steel", (0.35, 0.36, 0.38), rough=0.5, metal=0.6)
  for yy in (-3.5, 3.5):
    part("bb_post", cyl_mesh(f"bbpost{yy}", 0.25, 7.0, mat=grey), root, coll, (0, yy, 3.5))
  part("bb_back", box_mesh("bbback", 0.3, 12.4, 4.4, 6.0, grey), root, coll, (0.2, 0, 0))
  m, g = node_mat("bb_face")
  gen = g.node("ShaderNodeTexCoord").outputs["Generated"]
  sep = g.node("ShaderNodeSeparateXYZ", {0: gen})
  col = g.mix(g.remap(sep.outputs[2], 0.45, 0.5, 0.0, 1.0), (0.55, 0.12, 0.04), (0.85, 0.8, 0.7))
  g.finish(col, 0.45)
  g.set(g.bsdf.inputs["Emission Color"], col)
  g.bsdf.inputs["Emission Strength"].default_value = 0.1
  part("bb_face", box_mesh("bbface", 0.05, 12.0, 4.0, 6.2, m), root, coll, (0.0, 0, 0))
  white = material("bb_ink", (0.95, 0.95, 0.92), rough=0.5)
  for text, z, size in (("DINER  ·  NEXT EXIT", 8.7, 0.95), ("OPEN 24 HOURS", 7.2, 0.7)):
    cu = bpy.data.curves.new("bb_text", "FONT")
    cu.body, cu.align_x, cu.align_y, cu.size, cu.extrude = text, "CENTER", "CENTER", size, 0.01
    ob = bpy.data.objects.new("bb_text", cu)
    ob.parent = root
    ob.location = (-0.06, 0, z)
    ob.rotation_euler = (math.pi / 2, 0, -math.pi / 2)
    cu.materials.append(white)
    coll.objects.link(ob)


def farm_at(F: Frame, coll, x, y, z0, heading):
  h = heading + 0.4
  z0 -= 0.2
  red = material("barn_red", (0.32, 0.05, 0.03), rough=0.8)
  white = material("house_white", (0.75, 0.74, 0.7), rough=0.8)
  roof = material("barn_roof", (0.12, 0.12, 0.13), rough=0.6, metal=0.3)
  silo = material("silo", (0.6, 0.62, 0.64), rough=0.4, metal=0.5)

  def gabled(name, L, W, wall_h, ridge, wmat, at):
    me = bpy.data.meshes.new(name)
    L2, W2 = L / 2, W / 2
    v = [(-L2, -W2, 0), (L2, -W2, 0), (L2, W2, 0), (-L2, W2, 0), (-L2, -W2, wall_h), (L2, -W2, wall_h),
         (L2, W2, wall_h), (-L2, W2, wall_h), (-L2, 0, ridge), (L2, 0, ridge)]
    f = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 9, 8), (6, 7, 8, 9), (0, 4, 8), (1, 9, 5),
         (2, 6, 9), (3, 8, 7)]
    me.from_pydata(v, [], f)
    me.materials.append(wmat)
    me.materials.append(roof)
    for i, p in enumerate(me.polygons):
      p.material_index = 1 if i in (4, 5) else 0
    ob = bpy.data.objects.new(name, me)
    ob.location = at
    ob.rotation_euler = (0, 0, h)
    coll.objects.link(ob)

  ca, sa = math.cos(h), math.sin(h)
  gabled("barn", 22, 12, 6.0, 11.0, red, (x, y, z0))
  gabled("farmhouse", 12, 9, 6.0, 9.5, white, (x + 30 * ca - 20 * sa, y + 30 * sa + 20 * ca, z0))
  part("silo", cyl_mesh("silo", 3.0, 16.0, mat=silo), None, coll, (x - 16 * ca, y - 16 * sa, z0 + 8.0))
  part("silo_cap", sphere_mesh("silocap", 3.0, 2, silo), None, coll, (x - 16 * ca, y - 16 * sa, z0 + 16.0))
  for k in range(5):
    tx, ty = x + (-30 + 14 * k) * ca + 18 * sa, y + (-30 + 14 * k) * sa - 18 * ca
    part("farm_tree", sphere_mesh(f"ftree{k}", 4.5, 2, leaves_material("farm_leaves", (0.035, 0.07, 0.025), {}),
                                      0.25, k), None, coll, (tx, ty, z0 + 5.5))


def far_overpass(F: Frame, coll, cam_xy, heading, dist):
  """A concrete flyover crossing the view far ahead, past the end of the modelled road."""
  conc = material("far_concrete", (0.3, 0.29, 0.27), rough=0.9)
  cx, cy = cam_xy
  x, y = cx + dist * math.cos(heading), cy + dist * math.sin(heading)
  yaw = heading + math.pi / 2 + 0.25
  root = empty("far_overpass", coll)
  root.location, root.rotation_euler = (x, y, 0), (0, 0, yaw)
  part("fo_deck", box_mesh("fodeck", 600.0, 14.0, 1.6, 7.0, conc), root, coll)
  part("fo_parapet", box_mesh("fopar", 600.0, 0.4, 1.0, 8.6, conc), root, coll, (0, 6.8, 0))
  part("fo_parapet", box_mesh("fopar2", 600.0, 0.4, 1.0, 8.6, conc), root, coll, (0, -6.8, 0))
  for k in range(-6, 7):
    part("fo_pier", box_mesh(f"fopier{k}", 1.6, 8.0, 7.5, -0.5, conc), root, coll, (k * 45.0, 0, 0))


def build_distant(F: Frame, coll, cam_xy, heading, frame, kinds):
  """env distant: objects laid out in the chase view at `frame` (forward and left of the camera's heading), each
  checked to stand at least 20 m past the verge or beyond the modelled road: a line of pylons with sagging wires on
  the outside of the view, a billboard 22 m past the verge, a farm 150 m out, a flyover about 380 m ahead (past the
  modelled road's end)."""
  s_cam = F.ego_s(frame)
  ahead = 1 if math.cos(heading - F.at(s_cam)[2]) > 0 else -1     # -1: a rear view, looking back along the road
  cx, cy = cam_xy
  ch, sh = math.cos(heading), math.sin(heading)
  view = lambda fw, lat: (cx + fw * ch - lat * sh, cy + fw * sh + lat * ch)
  # which side of the view stays clear of the road: the outside of the curve ahead
  far = F.at(min(max(s_cam + ahead * 250, F.c[0][3]), F.c[-1][3]))
  lat_far = -(far[0] - cx) * sh + (far[1] - cy) * ch
  out_side = -1 if lat_far > 0 else 1

  def ground(x, y):
    s, d = F.sd(x, y)
    if s < F.c[0][3] or s > F.c[-1][3]:
      return -0.25, s, d
    return F.ground(x, y, d), s, d

  def clear(x, y, m=20.0):
    s, d = F.sd(x, y)
    return not (F.c[0][3] <= s <= F.c[-1][3]) or d > F.edge[1] + m or d < F.edge[-1] - m

  wire = material("wire", (0.08, 0.08, 0.08), rough=0.4, metal=0.8)
  towers = []
  for k in range(7 if "pylons" in kinds else 0):
    fw = 260 + 230 * k
    x, y = view(fw, out_side * (55 + 0.06 * fw))
    if not clear(x, y):
      continue
    z = ground(x, y)[0]
    root, att = lattice_pylon(f"pylon{k}", coll, (x, y, z - 0.3), heading + math.pi / 2 + out_side * 0.06)
    bpy.context.view_layer.update()
    towers.append([root.matrix_world @ Vector(a) for a in att])
  for k, (a, b) in enumerate(zip(towers, towers[1:])):
    for j, (p, q) in enumerate(zip(a, b)):
      catenary(f"wire{k}_{j}", coll, p, q, 7.0, wire)
  # billboard 22 m past the verge on the outside of the view, angled toward the traffic
  sb = s_cam + ahead * 95
  if "billboard" in kinds and F.c[0][3] < sb < F.c[-1][3]:
    side = out_side * ahead                     # out_side is to the view's left or right; the road's side flips
    billboard(F, coll, sb, F.edge[side] + side * 22.0, side * 0.45 + (0 if ahead > 0 else math.pi))
  fx, fy = view(300, -out_side * 150)            # a farm on the other side, far out
  if "farm" in kinds and clear(fx, fy, 60):
    farm_at(F, coll, fx, fy, ground(fx, fy)[0], heading)
  fo = view(380, 0)
  if "flyover" in kinds and not F.c[0][3] - 20 <= F.sd(*fo)[0] <= F.c[-1][3] + 20:
    far_overpass(F, coll, cam_xy, heading + 0.12, 380.0)


def build_cloud_shadows(F: Frame, coll, env, sun, frames, fps):
  """env cloud_shadows (clear or partly cloudy days): a shadow-only plane 450 m up, offset toward the sun, a soft
  noise mask cutting cloud shapes out of it (about 40 % cover); it drifts at 6 m/s over the clip."""
  if env.get("sky") in ("overcast", "night") or env.get("night"):
    return
  alt = 450.0
  sdir = sun.matrix_world.to_quaternion() @ Vector((0, 0, 1))     # toward the sun
  sdir.normalize()
  mid = F.c[len(F.c) // 2]
  k = alt / max(sdir.z, 0.05)
  cx, cy = mid[0] + sdir.x * k, mid[1] + sdir.y * k
  size = 8000.0
  ob = mesh_object("cloud_shadows", [(-size / 2, -size / 2, 0), (size / 2, -size / 2, 0), (size / 2, size / 2, 0),
                                       (-size / 2, size / 2, 0)], [(0, 1, 2, 3)], None, coll)
  ob.location = (cx, cy, alt)
  for attr in ("visible_camera", "visible_diffuse", "visible_glossy", "visible_transmission", "visible_volume_scatter"):
    setattr(ob, attr, False)
  ob.visible_shadow = True
  m = bpy.data.materials.new("cloud_mask")
  m.use_nodes = True
  nt = m.node_tree
  nt.nodes.remove(nt.nodes["Principled BSDF"])
  tc = nt.nodes.new("ShaderNodeTexCoord")
  mp = nt.nodes.new("ShaderNodeMapping")
  mp.inputs["Scale"].default_value = (1 / 240.0, 1 / 170.0, 1.0)
  nz = nt.nodes.new("ShaderNodeTexNoise")
  nz.inputs["Scale"].default_value = 1.0
  nz.inputs["Detail"].default_value = 5.0
  nz.inputs["Roughness"].default_value = 0.55
  rm = nt.nodes.new("ShaderNodeMapRange")
  rm.inputs[1].default_value, rm.inputs[2].default_value = 0.49, 0.55      # coverage about 40 %, soft edges
  rm.inputs[3].default_value, rm.inputs[4].default_value = 1.0, 0.15       # 1 = clear, 0.15 = 85 % of the sun blocked
  tr = nt.nodes.new("ShaderNodeBsdfTransparent")
  dif = nt.nodes.new("ShaderNodeBsdfDiffuse")
  dif.inputs["Color"].default_value = (0, 0, 0, 1)
  mix = nt.nodes.new("ShaderNodeMixShader")
  nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
  nt.links.new(mp.outputs[0], nz.inputs["Vector"])
  nt.links.new(nz.outputs["Fac"], rm.inputs[0])
  nt.links.new(rm.outputs[0], mix.inputs[0])
  nt.links.new(dif.outputs[0], mix.inputs[1])
  nt.links.new(tr.outputs[0], mix.inputs[2])
  nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
  ob.data.materials.append(m)
  # drift with the wind, about 6 m/s, across the road
  h = mid[2] + 0.9
  for f in (1, frames):
    t = (f - 1) / fps
    ob.location = (cx + 6.0 * t * math.cos(h), cy + 6.0 * t * math.sin(h), alt)
    ob.keyframe_insert("location", frame=f)
  _linear(ob)


def spray_material(name, strength):
  """Spray: a lopsided soft ellipsoid of mist in the volume's box, broken up by noise; strength scales its density."""
  m = bpy.data.materials.new(name)
  m.use_nodes = True
  nt = m.node_tree
  nt.nodes.remove(nt.nodes["Principled BSDF"])
  gen = nt.nodes.new("ShaderNodeTexCoord")
  sep = nt.nodes.new("ShaderNodeSeparateXYZ")
  nt.links.new(gen.outputs["Generated"], sep.inputs[0])

  def math_node(op, a, b=None):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, v in enumerate((a, b)):
      if v is None:
        continue
      if isinstance(v, bpy.types.NodeSocket):
        nt.links.new(v, n.inputs[i])
      else:
        n.inputs[i].default_value = v
    return n.outputs[0]

  # generated x: 0 at the far end of the plume, 1 at the wheels; z: 0 road, 1 top; y: 0..1 across. The density is a
  # soft lopsided ellipsoid: thickest just behind the wheels, low over the road, thinning to nothing at every face
  def half(v, c, lo, hi):
    dv = math_node("SUBTRACT", v, c)
    pos = math_node("GREATER_THAN", dv, 0.0)
    a_ = math_node("DIVIDE", dv, lo)
    b_ = math_node("DIVIDE", dv, hi)
    return math_node("ADD", a_, math_node("MULTIPLY", pos, math_node("SUBTRACT", b_, a_)))

  sx = half(sep.outputs[0], 0.8, 0.8, 0.2)
  sy = half(sep.outputs[1], 0.5, 0.5, 0.5)
  sz = half(sep.outputs[2], 0.18, 0.18, 0.82)
  r2 = math_node("ADD", math_node("ADD", math_node("MULTIPLY", sx, sx), math_node("MULTIPLY", sy, sy)),
                 math_node("MULTIPLY", sz, sz))
  shell = math_node("MAXIMUM", math_node("SUBTRACT", 1.0, math_node("SQRT", r2)), 0.0)
  shape = math_node("MULTIPLY", shell, shell)
  nz = nt.nodes.new("ShaderNodeTexNoise")
  nz.inputs["Scale"].default_value = 2.5
  nz.inputs["Detail"].default_value = 4.0
  objc = nt.nodes.new("ShaderNodeTexCoord")
  nt.links.new(objc.outputs["Object"], nz.inputs["Vector"])
  billow = nt.nodes.new("ShaderNodeMapRange")
  billow.inputs[1].default_value, billow.inputs[2].default_value = 0.35, 0.7
  nt.links.new(nz.outputs["Fac"], billow.inputs[0])
  dens = math_node("MULTIPLY", shape, billow.outputs[0])
  dens = math_node("MULTIPLY", dens, strength)
  vol = nt.nodes.new("ShaderNodeVolumePrincipled")
  vol.inputs["Color"].default_value = (0.82, 0.84, 0.87, 1.0)
  vol.inputs["Anisotropy"].default_value = 0.4
  nt.links.new(dens, vol.inputs["Density"])
  nt.links.new(vol.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
  return m


def build_spray(sc, env):
  """env spray (0..1, with rain): a plume of mist thrown up behind the wheels of every moving car and truck, parented
  to it; thinner behind the ego, which the chase camera looks past."""
  amount = float(env.get("spray", 0) or 0)
  if amount <= 0:
    return 0
  users = bpy.data.collections["road_users"]
  n = 0
  for a in sc["actors"]:
    if a["kind"] not in ("ego", "car", "truck") or a["poses"][0] == a["poses"][-1]:
      continue
    root = bpy.data.objects.get(a["name"].replace(" ", "_"))
    if root is None:
      continue
    truck = a["kind"] == "truck"
    rear, L, W, Hh = (-4.75, 16.0, 3.0, 3.2) if truck else (-2.2, 9.0, 2.2, 1.5)
    strength = amount * (9.0 if truck else (3.5 if a["kind"] == "ego" else 5.0))
    me = box_mesh(f"spray_{n}", L, W, Hh, 0.04)   # clear of the road: no coplanar boundary
    ob = bpy.data.objects.new(f"spray_{a['name']}", me)
    ob.parent = root
    ob.location = (rear - L / 2 + 0.6, 0.0, 0.0)
    me.materials.append(spray_material(f"spray_mat_{n}", strength))
    users.objects.link(ob)
    n += 1
  return n


def decal_material(name, rgb, rough, alpha, edge=0.25, noise_scale=1.5):
  """A flat decal: colour and roughness, its alpha softened at the rim and broken by noise."""
  m, g = node_mat(name)
  gen = g.node("ShaderNodeTexCoord").outputs["UV"]
  sep = g.node("ShaderNodeSeparateXYZ", {0: gen})
  fx = g.math("MINIMUM", sep.outputs[0], g.math("SUBTRACT", 1.0, sep.outputs[0]))
  fy = g.math("MINIMUM", sep.outputs[1], g.math("SUBTRACT", 1.0, sep.outputs[1]))
  rim = g.remap(g.math("MINIMUM", fx, fy), 0.0, edge, 0.0, 1.0)
  objc = g.node("ShaderNodeTexCoord").outputs["Object"]
  nz = g.noise(objc, noise_scale, 4).outputs[0]
  a = g.math("MULTIPLY", rim, g.remap(nz, 0.3, 0.55, 0.4, 1.0))
  g.finish(rgb, rough)
  g.set(g.bsdf.inputs["Alpha"], g.math("MULTIPLY", a, alpha))
  return m


def quad(name, F: Frame, s0, s1, d0, d1, z, mat, coll, n=None):
  """A decal on the road between s0..s1 and d0..d1, following the centre line; UV 0..1."""
  n = n or max(int(abs(s1 - s0)), 1)
  verts, faces, uvs = [], [], []
  for i in range(n + 1):
    s = s0 + (s1 - s0) * i / n
    p = F.at(s)
    verts += [offset(p, d0, z), offset(p, d1, z)]
    uvs += [(0.0, i / n), (1.0, i / n)]
    if i:
      faces.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
  return mesh_object(name, verts, faces, mat, coll, uvs=uvs)


def build_road_wear(F: Frame, coll, env):
  """env road_wear: repair patches, cracks, a sealed transverse joint, faint skid marks in another lane and road studs
  on the lines (cast-iron covers on an urban street) over the stretch the chase camera sees. Flat decals between 2.5
  and 4.5 mm above the asphalt, under the markings (6 mm); the studs are 18 mm high on the lines."""
  rnd = random.Random(23)
  r = F.r
  s_a, s_b = F.camera_span(10.0, 170.0)
  lines = sorted(m["d"] for m in r["markings"])
  lo, hi = r["carriageway"][1], r["carriageway"][0]
  lanes = [(a + 0.25, b - 0.25) for a, b in zip([lo] + lines, lines + [hi]) if b - a > 1.5]
  wet = float(env.get("wet", 0) or 0)
  patch = decal_material("wear_patch", (0.05, 0.049, 0.05), 0.8 - 0.5 * wet, 0.75, 0.04, 3.0)
  patch2 = decal_material("wear_patch2", (0.085, 0.082, 0.078), 0.85 - 0.5 * wet, 0.6, 0.05, 3.0)
  crack = material("wear_crack", (0.012, 0.012, 0.013), rough=0.9)
  sealant = material("wear_sealant", (0.02, 0.02, 0.022), rough=0.25)
  skid = decal_material("wear_skid", (0.006, 0.006, 0.006), 0.5, 0.8, 0.12, 0.8)
  # repair patches, mostly in the wheel tracks
  s = s_a
  while s < s_b:
    a, b = rnd.choice(lanes)
    w = rnd.uniform(1.0, min(2.8, b - a))
    d0 = rnd.uniform(a, b - w)
    ln = rnd.uniform(1.5, 6.0)
    quad("patch", F, s, s + ln, d0 + w, d0, 0.0025, rnd.choice((patch, patch, patch2)), coll, max(int(ln), 1))
    s += rnd.uniform(14, 38)
  # cracks: thin wandering strips, longitudinal along the lane joints and a few across the lane
  for k in range(int(0.15 * (s_b - s_a))):
    s0 = rnd.uniform(s_a, s_b - 10)
    a, b = rnd.choice(lanes)
    d = rnd.uniform(a, b)
    longit = rnd.random() < 0.6
    verts, faces = [], []
    n = rnd.randint(10, 30)
    ang = 0.0 if longit else math.pi / 2
    x_s, x_d = s0, d
    for i in range(n + 1):
      p = F.at(x_s)
      w = 0.02 * (1 - abs(2 * i / n - 1)) + 0.008
      ny = math.cos(ang)
      verts += [offset(p, x_d + w * ny, 0.003), offset(p, x_d - w * ny, 0.003)]
      if i:
        faces.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
      ang += rnd.uniform(-0.5, 0.5)
      if longit:
        ang = max(min(ang, 0.6), -0.6)
      step = rnd.uniform(0.15, 0.35)
      x_s += step * math.cos(ang)
      x_d = min(max(x_d + step * math.sin(ang), a), b)
    mesh_object("crack", verts, faces, crack, coll)
  # sealed transverse joints across the whole carriageway (under the lines, which stay on top), one every 120 m
  sj = s_a + 42
  while sj < s_b:
    quad("sealed_joint", F, sj, sj + 0.14, hi, lo, 0.004, sealant, coll, 1)
    sj += 120.0
  # faint skid marks in the next lane, curving a little
  other = lanes[0] if len(lanes) > 1 else lanes[-1]
  dm = 0.5 * (other[0] + other[1])
  s0 = min(F.ego_s(max(1, round(LOOK_FRAC * len(F.sc["t"])))) + 55, s_b - 30)
  for off in (-0.78, 0.78):
    verts, faces, uvs = [], [], []
    n = 30
    for i in range(n + 1):
      s = s0 + 28 * i / n
      dd = dm + off + 0.35 * (i / n) ** 2
      p = F.at(s)
      verts += [offset(p, dd + 0.11, 0.0045), offset(p, dd - 0.11, 0.0045)]
      uvs += [(0.0, i / n), (1.0, i / n)]
      if i:
        faces.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
    mesh_object("skid", verts, faces, skid, coll, uvs=uvs)
  # road studs on the lane lines (and the edge lines on the highway), every 18 m
  stud_w = material("stud_white", (0.9, 0.9, 0.85), rough=0.2, emit=0.6 if env.get("night") else 0.0)
  stud_r = material("stud_red", (0.8, 0.05, 0.03), rough=0.2, emit=0.6 if env.get("night") else 0.0)
  stud_a = material("stud_amber", (0.95, 0.55, 0.05), rough=0.2, emit=0.6 if env.get("night") else 0.0)
  me = bpy.data.meshes.new("stud")
  bm = bmesh.new()
  bmesh.ops.create_cube(bm, size=1.0)
  bmesh.ops.scale(bm, vec=(0.1, 0.1, 0.018), verts=bm.verts)
  bmesh.ops.translate(bm, vec=(0, 0, 0.009), verts=bm.verts)
  bm.to_mesh(me)
  bm.free()
  for mk in r["markings"]:
    if F.kind == "urban":
      break
    col = {"white": stud_w, "yellow": stud_a}[mk["colour"]]
    if mk["style"] == "solid" and mk["colour"] == "white":
      col = stud_r if mk["d"] < 0 else stud_a
    m2 = me.copy()
    m2.materials.append(col)
    s = s_a
    while s < s_b:
      p = F.at(s)
      x, y, _ = offset(p, mk["d"])
      part("stud", m2, None, coll, (x, y, 0.0), (0, 0, p[2]))
      s += 18.0
  if F.kind == "urban":                          # a manhole cover and a gully grate instead
    iron = material("cast_iron", (0.05, 0.05, 0.05), rough=0.4, metal=0.8)
    s, k = s_a + 18, 0
    while s < s_b:
      x, y, _ = F.world(s, (0.2, -1.0, 2.8)[k % 3])
      k += 1
      part("manhole", cyl_mesh(f"manhole{s:.0f}", 0.32, 0.01, mat=iron, segs=24), None, coll, (x, y, 0.004))
      s += 29.0


def build_camera_feel(cam, ego_ob):
  """env camera_feel: mild depth of field on the chase camera (f/2, focused on the ego), and a vignette and film grain
  in the compositor (CPU), chained after the glare when there is one. Off for the top view (surroundings_for)."""
  cam.data.dof.use_dof = True
  cam.data.dof.focus_object = ego_ob
  cam.data.dof.aperture_fstop = 2.0
  scene = bpy.context.scene
  scene.render.compositor_device = "CPU"
  ng = scene.compositing_node_group
  if ng is None:
    ng = bpy.data.node_groups.new("look", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    scene.compositing_node_group = ng
    rl, out = ng.nodes.new("CompositorNodeRLayers"), ng.nodes.new("NodeGroupOutput")
    src = rl.outputs["Image"]
  else:
    out = next(n for n in ng.nodes if n.bl_idname == "NodeGroupOutput")
    src = out.inputs[0].links[0].from_socket
  ell = ng.nodes.new("CompositorNodeEllipseMask")
  ell.inputs["Size"].default_value = (1.15, 1.15) if len(ell.inputs["Size"].default_value) == 2 else (1.15, 1.15, 0)
  blur = ng.nodes.new("CompositorNodeBlur")
  try:
    blur.inputs["Size"].default_value = (260, 260) if len(blur.inputs["Size"].default_value) == 2 else (260, 260, 0)
  except TypeError:
    pass
  ng.links.new(ell.outputs["Mask"], blur.inputs["Image"])
  vig = ng.nodes.new("ShaderNodeMapRange")
  vig.inputs[3].default_value, vig.inputs[4].default_value = 0.72, 1.0
  ng.links.new(blur.outputs[0], vig.inputs[0])
  mul = ng.nodes.new("ShaderNodeMix")
  mul.name = "look_vignette"
  mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
  mul.inputs[0].default_value = 1.0
  ng.links.new(src, mul.inputs[6])
  ng.links.new(vig.outputs[0], mul.inputs[7])
  # grain: per-pixel white noise, centred on 0, added in proportion to the brightness (overlay-like)
  coords = ng.nodes.new("CompositorNodeImageCoordinates")
  ng.links.new(src, coords.inputs[0])
  wn = ng.nodes.new("ShaderNodeTexWhiteNoise")
  wn.noise_dimensions = "2D"
  ng.links.new(coords.outputs[1] if len(coords.outputs) > 1 else coords.outputs[0], wn.inputs["Vector"])
  cen = ng.nodes.new("ShaderNodeMapRange")
  cen.inputs[3].default_value, cen.inputs[4].default_value = 0.94, 1.06
  ng.links.new(wn.outputs["Value"], cen.inputs[0])
  gr = ng.nodes.new("ShaderNodeMix")
  gr.name = "look_grain"
  gr.data_type, gr.blend_type = "RGBA", "MULTIPLY"
  gr.inputs[0].default_value = 1.0
  ng.links.new(mul.outputs[2], gr.inputs[6])
  ng.links.new(cen.outputs[0], gr.inputs[7])
  ng.links.new(gr.outputs[2], out.inputs[0])


def surroundings_for(cam_name: str):
  """The vignette, grain and spray are for the views from the road: switch them off for the orthographic top view,
  which shows the layout."""
  for ob in bpy.data.objects:
    if ob.name.startswith("spray_"):
      ob.hide_render = cam_name == "cam_top"
  ng = bpy.context.scene.compositing_node_group
  if ng is None:
    return
  for k in ("look_vignette", "look_grain"):
    n = ng.nodes.get(k)
    if n is not None:
      n.inputs[0].default_value = 0.0 if cam_name == "cam_top" else 1.0


def build_surroundings(sc: dict, env: dict, cam, ego_ob, frames: int, fps: int, rear: bool = False):
  """Everything env asks of the surroundings (see the section comment), in the order the parts depend on: the ground
  first, so that plants and objects stand on it."""
  coll = bpy.data.collections.new("surroundings")
  bpy.context.scene.collection.children.link(coll)
  F = Frame(sc, env, rear)
  frame = max(1, round(LOOK_FRAC * frames))
  bpy.context.scene.frame_set(frame)
  cam_xy = tuple(cam.matrix_world.translation[:2])
  look = cam.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
  heading = math.atan2(look.y, look.x)
  done = []
  if F.terrain:
    build_terrain(F, coll)
    done.append(f"terrain {F.terrain}")
  if env.get("horizon"):
    build_horizon(F, coll, cam_xy)
    done.append("horizon")
    if env.get("haze_km") and not env.get("visibility_m") and not env.get("night"):
      build_haze(coll, cam_xy, float(env["haze_km"]))
      done.append("haze")
  if env.get("verge_plants"):
    build_verge_plants(F, coll)
    done.append("verge plants")
  kinds = [k for k in env.get("distant") or [] if k in DISTANT]
  if kinds:
    build_distant(F, coll, cam_xy, heading, frame, kinds)
    done.append("distant " + "+".join(kinds))
  if env.get("cloud_shadows"):
    build_cloud_shadows(F, coll, env, bpy.data.objects["sun"], frames, fps)
    done.append("cloud shadows")
  if build_spray(sc, env):
    done.append("spray")
  if env.get("road_wear"):
    build_road_wear(F, coll, env)
    done.append("road wear")
  if env.get("horizon") or kinds:
    for ob in bpy.data.objects:
      if ob.type == "CAMERA":
        ob.data.clip_end = 9000.0
  if env.get("camera_feel"):
    build_camera_feel(cam, ego_ob)
    done.append("camera feel")
  bpy.context.scene.frame_set(1)
  print("surroundings: " + (", ".join(done) or "none"))
  return coll


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


def scanned_pedestrian(name: str, coll, seed: str = "", figure: str | None = None, root_dir: Path | None = None):
  """A Quaternius CC0 figure (library/people/) facing +X with its rig and Walk_Loop, or None when the file is missing.
  Which figure and shirt colour follow from the name and seed (the base scene's ID, so a condition variant shows the
  same person), unless the scene names the figure (male, female). Returns the root and the rig, whose walk
  hazard_scene.py drives by the distance walked."""
  pick = zlib.crc32((name + seed).encode())
  fname, height = next((p for p in PEOPLE if figure and p[0] == f"pedestrian_{figure}.glb"),
                       PEOPLE[pick % len(PEOPLE)])
  path = (root_dir or PEOPLE_DIR) / fname
  if not path.exists():
    return None
  objs_before, acts_before = set(bpy.data.objects), set(bpy.data.actions)
  bpy.ops.import_scene.gltf(filepath=str(path))
  new = [o for o in bpy.data.objects if o not in objs_before]
  rig = next(o for o in new if o.type == "ARMATURE")
  walk = next(a for a in bpy.data.actions if a not in acts_before)
  if rig.animation_data:                        # the importer's own action and NLA; the walk is re-added by distance
    rig.animation_data.action = None
    for t in list(rig.animation_data.nla_tracks):
      rig.animation_data.nla_tracks.remove(t)
  rig["walk_action"] = walk.name
  for o in new:
    for c in list(o.users_collection):
      c.objects.unlink(o)
    coll.objects.link(o)
  bpy.context.view_layer.update()
  meshes = [o for o in new if o.type == "MESH"]
  eyes = next((o for o in meshes if o.name.startswith("Eyes")), None)
  fwd = (eyes.matrix_world.translation if eyes else Vector((1, 0, 0))) - rig.matrix_world.translation
  top = max((o.matrix_world @ Vector(c)).z for o in meshes for c in o.bound_box)
  root = empty(name, coll)
  rig.parent = root
  rig.location = (0, 0, 0)
  rig.rotation_euler.z -= math.atan2(fwd.y, fwd.x)
  rig.scale = tuple(v * height / top for v in rig.scale)
  shirt = material(f"shirt_{name}", SHIRTS[pick // len(PEOPLE) % len(SHIRTS)], rough=0.85)
  for o in meshes:
    for k, m in enumerate(o.data.materials):
      if m and m.name.split(".")[0] == "shirt":
        o.data.materials[k] = shirt
  return root, rig


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
