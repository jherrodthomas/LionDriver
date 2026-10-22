"""Blender side of the render-only extras (street_life.py plans them): the CC-BY model kits of library/assets.yaml as
templates, and what the scene's env asks of them. city_blocks: brownstone, Chicago and office rows on the building
lines of an urban street (in place of the procedural boxes) and towers beyond it; street_life: parked and passing
cars and people on the pavements; farmstead: a farm with grain bins and a roadside diner beside a rural road;
traffic_skins: the traffic cars drawn with the car pack, scaled to the analysis' car length (street_life.skin_scale);
trailers: a box trailer behind each truck street_life.trailers allows; bodies: a road user with a body (fire_truck,
police_sedan) drawn with the civil service vehicles pack, its beacons on the model's roof. A kit that is not fetched is left out (the
procedural look stays), so CI and offline runs need none of them.

Pictures only: export_scene.py reads none of this, and the scene's road users keep their poses (a skin or a trailer
is drawn on a road user's own animated root). Every kit is CC-BY 4.0: a published render credits it
(library/README.md section 5)."""

from __future__ import annotations

import math
import random
import re
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

import scene_assets as A
import street_layout as L
import street_life

BUILDING_USES = ("city_block", "skyline", "farm", "roadside", "bins")
NIGHT_DIM = (0.25, 0.25, 0.28)   # the scans' colour maps carry daylight: multiplied down at night
DINER_CARS = 3


# ------------------------------------------------------------------------------------------------- kits
def _fix_images(root: Path):
  """Point every image the model could not find at the file of the same name under root, else at its albedo for a
  baked-light map (the civil service vehicles' base colour; the download leaves the bakes out), else at another
  colour of the same model (the car pack's FBX names colours its download leaves out)."""
  files = {f.name.lower(): f for f in root.rglob("*") if f.is_file()}
  for img in bpy.data.images:
    if img.source != "FILE":
      continue
    p = Path(bpy.path.abspath(img.filepath))
    if p.exists():
      continue
    f = files.get(p.name.lower()) or next((files[n] for n in (p.stem.lower() + e for e in (".png", ".jpg", ".jpeg"))
                                           if n in files), None)
    if f is None and p.stem.lower().endswith("_baked"):
      f = files.get(p.stem.lower().removesuffix("_baked") + "_albedo.png")
    if f is None:
      stem = p.stem.lower()
      pre = "wheel_" if stem.startswith("wheel_") else p.parent.name.lower()
      tail = "_diffuse" if stem.endswith("_diffuse") else ""
      cands = sorted(n for n in files if n.startswith(pre) and Path(n).suffix in (".png", ".jpg", ".jpeg") and
                     (n.split(".")[0].endswith(tail) if tail else not re.search(r"gloss|metal|_ao|normal|rough", n)))
      f = files[cands[0]] if cands else None
    if f is not None:
      img.filepath = str(f)
      img.reload()


def _top(zs):
  """The 98th-percentile height of some vertices (their roof line, ignoring an aerial)."""
  return sorted(zs)[int(0.98 * (len(zs) - 1))] if zs else 0.0


def _bbox(objs):
  pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
  return (Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)]))


class Kit:
  """A kit slot's pieces as templates kept out of the scene ({use: [piece]}): a piece is {name, parts [(mesh,
  matrix)], w, d, h}. Buildings are centred in X with their facade (-Y in the file) at Y = 0 and the base at Z = 0;
  cars are centred and face +X (the bonnet end is the lower one), and so are vehicles (the slot's fronts name the
file's front, its lights the roof points of the beacons as fractions of the length from the centre); a trailer has its kingpin end at the origin and
  reaches along -X, scaled to the slot's width_m."""

  def __init__(self, slot: dict, root: Path):
    self.slot = slot
    path = root / slot["file"]
    before, imgs = set(bpy.data.objects), set(bpy.data.images)
    if path.suffix == ".fbx":
      bpy.ops.import_scene.fbx(filepath=str(path))
    elif path.suffix in (".gltf", ".glb"):
      bpy.ops.import_scene.gltf(filepath=str(path))
    else:                                       # objects only: no scripts, no scene settings
      with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if not any(n.startswith(s) for s in slot.get("skip", []))]
      for o in dst.objects:
        if o:
          bpy.context.scene.collection.objects.link(o)
    new = [o for o in bpy.data.objects if o not in before]
    _fix_images(root / slot.get("textures", "")) if slot.get("textures") else _fix_images(root)
    bpy.context.view_layer.update()
    meshes = [o for o in new if o.type == "MESH" and not any(o.name.startswith(s) for s in slot.get("skip", []))]
    k = float(slot.get("scale", 1.0))
    self.pieces = {}
    for use, names in slot["pieces"].items():
      if use == "cars":
        self.pieces[use] = self._cars(meshes, names)
      elif use == "vehicles":
        self.pieces[use] = [self._vehicle(o) for n in names for o in meshes if o.name.split(".")[0] == n]
      elif names == ["all"]:
        self.pieces[use] = [self._trailer(meshes) if use == "trailer" else self._building("all", meshes, k)]
      else:
        tops = {o.name: o for o in meshes if o.parent is None or o.parent not in meshes}
        self.pieces[use] = [self._building(n, [tops[n]] + [c for c in tops[n].children_recursive if c.type == "MESH"],
                                           k) for n in names if n in tops]
    for p in (q for v in self.pieces.values() for q in v):
      for me, _ in p["parts"]:
        me.use_fake_user = True
    for o in new:
      bpy.data.objects.remove(o, do_unlink=True)
    self.materials = {m for v in self.pieces.values() for p in v for me, _ in p["parts"] for m in me.materials if m}
    self.images = set(bpy.data.images) - imgs
    print(f"kit: {slot.get('title')} ({slot.get('author')}, {slot.get('licence')}): "
          + ", ".join(f"{len(v)} {u}" for u, v in self.pieces.items()))

  @staticmethod
  def _building(name, objs, k):
    lo, hi = _bbox(objs)
    t = Matrix.Scale(k, 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -lo.y, -lo.z))
    return {"name": name, "parts": [(o.data, t @ o.matrix_world) for o in objs],
            "w": (hi.x - lo.x) * k, "d": (hi.y - lo.y) * k, "h": (hi.z - lo.z) * k}

  def _trailer(self, objs):
    lo, hi = _bbox(objs)
    k = float(self.slot.get("width_m", 2.59)) / (hi.x - lo.x)
    t = (Matrix.Rotation(math.pi / 2, 4, "Z") @ Matrix.Scale(k, 4)
         @ Matrix.Translation((-(lo.x + hi.x) / 2, -lo.y, -lo.z)))      # kingpin end (low Y) to +X, at the origin
    return {"name": "trailer", "parts": [(o.data, t @ o.matrix_world) for o in objs],
            "w": (hi.y - lo.y) * k, "d": (hi.x - lo.x) * k, "h": (hi.z - lo.z) * k}

  def _vehicle(self, ob):
    name = ob.name.split(".")[0]
    lo, hi = _bbox([ob])
    turn = math.pi / 2 if self.slot["fronts"][name] == "-y" else -math.pi / 2
    m = Matrix.Rotation(turn, 4, "Z") @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)) @ ob.matrix_world
    vs = [m @ v.co for v in ob.data.vertices]
    length = hi.y - lo.y
    lights = []
    for f in self.slot.get("lights", {}).get(name, []):
      zs = sorted(v.z for v in vs if abs(v.x - f * length) < 0.06 * length)
      lights.append((f * length, zs[int(0.95 * (len(zs) - 1))]))    # the roof there, not an aerial
    return {"name": name, "parts": [(ob.data, m)], "w": length, "d": hi.x - lo.x, "h": hi.z - lo.z, "lights": lights}

  @staticmethod
  def _cars(meshes, names):
    bodies = [o for o in meshes if "body" in o.name.lower() and any(o.name.lower().startswith(n.lower()) for n in names)]
    wheels = [o for o in meshes if o.name.lower().startswith("wheel")]
    out = []
    for b in bodies:
      vs = [b.matrix_world @ v.co for v in b.data.vertices]
      mx, my = sum(v.x for v in vs) / len(vs), sum(v.y for v in vs) / len(vs)
      sxx = sum((v.x - mx) ** 2 for v in vs)
      syy = sum((v.y - my) ** 2 for v in vs)
      sxy = sum((v.x - mx) * (v.y - my) for v in vs)
      ang = 0.5 * math.atan2(2 * sxy, sxx - syy)             # the long axis
      ca, sa = math.cos(ang), math.sin(ang)
      along = [(v.x - mx) * ca + (v.y - my) * sa for v in vs]
      a0, a1 = min(along), max(along)
      q = 0.25 * (a1 - a0)
      near = _top([v.z for v, a in zip(vs, along, strict=True) if a < a0 + q])
      far = _top([v.z for v, a in zip(vs, along, strict=True) if a > a1 - q])
      if far >= near:                                       # the bonnet is the lower end: make it +X
        ang += math.pi
      lo, hi = _bbox([b])
      mine = [w for w in wheels if math.hypot(*(sum((w.matrix_world @ Vector(c) for c in w.bound_box), Vector()) / 8
                                                - Vector((mx, my, 0)))[:2]) < 0.6 * (a1 - a0)]
      t = Matrix.Rotation(-ang, 4, "Z") @ Matrix.Translation((-mx, -my, -lo.z))
      out.append({"name": b.name.split(" ")[0].lower(), "parts": [(o.data, t @ o.matrix_world) for o in [b] + mine],
                  "w": a1 - a0, "d": 0.0, "h": hi.z - lo.z})
    return out


def place(piece, name: str, coll, loc, yaw: float = 0.0, mirror: bool = False, parent=None):
  root = A.empty(name, coll)
  root.parent = parent
  root.location, root.rotation_euler = loc, (0.0, 0.0, yaw)
  if mirror:
    root.scale = (-1.0, 1.0, 1.0)
  for j, (me, m) in enumerate(piece["parts"]):
    ob = bpy.data.objects.new(f"{name}.{j:02d}", me)
    ob.parent, ob.matrix_basis = root, m
    coll.objects.link(ob)
  return root


class People:
  """The repo's CC0 Quaternius figures (library/people/), imported once each and cloned per pedestrian: a clone has
  its own rig (so its own walk) and shirt, and shares the meshes."""

  def __init__(self, coll, seed: str):
    self.coll, self.rnd = coll, random.Random(seed)
    self.templates = []
    for figure in ("male", "female"):
      got = A.scanned_pedestrian(f"_tmpl_{figure}", coll, seed, figure)
      if got:
        root, rig = got
        root.hide_render = rig.hide_render = True
        for o in rig.children_recursive:
          o.hide_render = True
        self.templates.append((root, rig))
    self.n = 0

  def clone(self, name: str):
    if not self.templates:
      return None
    root0, rig0 = self.rnd.choice(self.templates)
    root = A.empty(name, self.coll)
    rig = rig0.copy()
    rig.animation_data_clear()
    rig.parent = root
    rig.hide_render = False
    self.coll.objects.link(rig)
    shirt = A.material(f"shirt_{name}", self.rnd.choice(A.SHIRTS), rough=0.85)
    for m0 in rig0.children:
      if m0.type != "MESH":
        continue
      m = m0.copy()
      m.parent, m.hide_render = rig, False
      for mod in m.modifiers:
        if mod.type == "ARMATURE":
          mod.object = rig
      for slot in m.material_slots:
        if slot.material and slot.material.name.startswith("shirt"):
          slot.link = "OBJECT"
          slot.material = shirt
      self.coll.objects.link(m)
    self.n += 1
    return root, rig


# ------------------------------------------------------------------------------------------------- what env asks
def _kits(assets, names) -> dict[str, Kit]:
  out = {}
  for n in names:
    s = assets.get(n)
    if s and s.get("kind") == "kit":
      out[n] = Kit(s, assets.root / n)
  return out


def city_ready(env: dict, assets) -> bool:
  """True when the street rows will be drawn from the kits (so build_scenery leaves out its procedural boxes)."""
  return bool(env.get("city_blocks")) and assets.get("city_brownstones") is not None


def _night(env, mats):
  if not env.get("night"):
    return
  for m in mats:
    if not m.use_nodes:
      continue
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
      continue
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
    mix.inputs[0].default_value = 1.0
    mix.inputs[7].default_value = (*NIGHT_DIM, 1.0)
    sock = bsdf.inputs["Base Color"]
    if sock.links:
      nt.links.new(sock.links[0].from_socket, mix.inputs[6])
    else:
      mix.inputs[6].default_value = sock.default_value
    nt.links.new(mix.outputs[2], sock)


def _snow(env, mats):
  if env.get("snow"):
    for m in mats:
      if m.use_nodes and any(n.type == "BSDF_PRINCIPLED" for n in m.node_tree.nodes):
        A.snow_on(m, float(env["snow"]))


def build(sc: dict, env: dict, assets, keyframe, walk, lamps=None, rear: bool = False, beacon=None) -> str:
  """Everything env asks of the kits; keyframe, walk and lamps are hazard_scene's keyframe_poses, walk_rig and
  (headlights, taillights), the lamps lit on the passing cars at night or in poor visibility; beacon(root, coll, x, z)
  puts an emergency light bar on a body's roof."""
  want = set()
  urban = sc["road"]["type"] == "urban"
  if env.get("city_blocks") and urban:
    want |= {"city_brownstones", "city_chicago", "city_downtown"}
  if env.get("street_life") and urban or env.get("traffic_skins") or env.get("farmstead"):
    want.add("car_pack")
  if env.get("farmstead"):
    want |= {"rural_buildings", "grain_bins"}
  if env.get("trailers"):
    want.add("box_trailer")
  if any(a.get("body") for a in sc["actors"]):
    want.add("civil_vehicles")
  kits = _kits(assets, sorted(want))
  if not kits:
    return "none"
  coll = bpy.data.collections.new("extras")
  bpy.context.scene.collection.children.link(coll)
  rnd = random.Random(sc.get("variant_of") or sc["id"])
  cars = kits["car_pack"].pieces["cars"] if "car_pack" in kits else []
  done = []

  def pick(u):
    return cars[min(int(u * len(cars)), len(cars) - 1)]

  street = [p for n in ("city_brownstones", "city_chicago", "city_downtown") if n in kits
            for p in kits[n].pieces.get("city_block", [])]
  if street and env.get("city_blocks") and urban:
    rows = street_life.blocks(sc, [p["w"] for p in street])
    for k, b in enumerate(rows):
      place(street[b["k"]], f"block{k}", coll, (b["x"], b["y"], 0.0), b["yaw"], b["mirror"])
    towers = kits["city_downtown"].pieces.get("skyline", []) if "city_downtown" in kits else []
    if towers:
      c = sc["road"]["centre"]
      end = c[0] if rear else c[-1]
      h = end[2] + (math.pi if rear else 0.0)
      spots = [(40, 30), (65, -38), (95, 8), (130, 55), (150, -70), (-60, 75), (-110, -85), (-160, 70)]
      for k, (fw, lat) in enumerate(spots):
        x = end[0] + fw * math.cos(h) - lat * math.sin(h)
        y = end[1] + fw * math.sin(h) + lat * math.cos(h)
        s, d = L.nearest_s(c, x, y), None
        p = L.at(c, s)
        d = -(x - p[0]) * math.sin(p[2]) + (y - p[1]) * math.cos(p[2])
        if c[0][3] + 1 < s < c[-1][3] - 1 and abs(d) < 45:      # beside the modelled street: behind the rows only
          continue
        place(rnd.choice(towers), f"tower{k}", coll, (x, y, 0.0), h + rnd.choice((0.0, 0.5, 1.0, 1.5)) * math.pi)
    done.append(f"{len(rows)} buildings")

  life = env.get("street_life")
  if life and urban and cars:
    for k, p in enumerate(street_life.parked(sc, life)):
      place(pick(p["pick"]), f"parked{k}", coll, (p["x"], p["y"], 0.0), p["yaw"])
    moving = street_life.passing(sc, life)
    for k, p in enumerate(moving):
      root = place(pick(p["pick"]), f"passing{k}", coll, (0, 0, 0))
      keyframe(root, p["path"])
      if lamps and (env.get("night") or (env.get("visibility_m") or 1e9) < 1000):
        lamps[0](root, coll, energy=4000 if env.get("night") else 1200)
        lamps[1](root, coll, -2.3)
    people = People(coll, sc.get("variant_of") or sc["id"])
    walkers = street_life.walkers(sc, life)
    for k, w in enumerate(walkers):
      got = people.clone(f"walker{k}")
      if got:
        root, rig = got
        keyframe(root, w["path"])
        walk(rig, w["path"])
    done.append(f"street life: {len(moving)} passing, {people.n} people")

  if env.get("traffic_skins") and cars:
    n = 0
    for name, u in street_life.skins(sc).items():
      root = bpy.data.objects.get(name.replace(" ", "_"))
      if root is None:
        continue
      for o in root.children_recursive:
        if o.type == "MESH":
          o.hide_render = True
      car = pick(u)
      skin = place(car, f"{root.name}_skin", coll, (0, 0, 0), parent=root)
      k = street_life.skin_scale(sc, car["w"])
      skin.scale = (k, k, k)
      n += 1
    done.append(f"{n} skins")

  if env.get("trailers") and "box_trailer" in kits:
    trailer = kits["box_trailer"].pieces["trailer"][0]
    names = street_life.trailers(sc)
    for name in names:
      root = bpy.data.objects.get(name.replace(" ", "_"))
      if root is None:
        continue
      for o in root.children_recursive:              # the cab stays; the box, its frame and rear axles go
        base = o.name.split(".")[0]
        keep = base.endswith(("_cab", "_ws", "_sidewin", "_grille", "_bumper")) or (base.endswith("_w") and
                                                                                   o.location.x > 0)
        if o.type == "MESH" and not keep:
          o.hide_render = True
      place(trailer, f"{root.name}_trailer", coll, (2.45, 0.0, 0.0), parent=root)
      for o in root.children_recursive:              # tail lamps to the trailer's end
        if o.type == "LIGHT" and o.location.x < 0:
          o.location.x = 2.45 - trailer["w"]
    done.append(f"{len(names)} trailers")

  if "civil_vehicles" in kits:
    bodies = {p["name"]: p for p in kits["civil_vehicles"].pieces["vehicles"]}
    n = 0
    for a in sc["actors"]:
      b = bodies.get(a.get("body"))
      root = bpy.data.objects.get(a["name"].replace(" ", "_"))
      if b is None or root is None:
        continue
      for o in root.children_recursive:              # the procedural body and its beacons go; the lamps stay
        if o.type == "MESH" or o.name.startswith("beacon"):
          o.hide_render = True
      k = street_life.body_scale(a, b["w"])
      place(b, f"{root.name}_body", coll, (0, 0, 0), parent=root).scale = (k, k, k)
      if beacon and a.get("beacons"):
        for x, z in b["lights"]:
          beacon(root, coll, x * k, z * k)
      n += 1
    done.append(f"{n} bodies")

  if env.get("farmstead") and "rural_buildings" in kits:
    done.append(farmstead(sc, env, kits, coll, cars, rnd, rear))

  mats = {m for k in kits.values() if k is not kits.get("car_pack") for m in k.materials}
  _night(env, mats)
  _snow(env, mats)
  return ", ".join(done)


def farmstead(sc, env, kits, coll, cars, rnd, rear) -> str:
  """A farm (house, barns, sheds, grain bins) 30 m past the verge on one side and a diner and stores 16 m past it
  (the other side where it has room), ahead of the chase camera at scene_assets' look frame; nothing within 22 m of a
  billboard or the distant farm, nothing in the chase camera's view of the ego. The pieces stand on the terrain."""
  F = A.Frame(sc, env, rear)
  frames = len(sc["t"])
  frame = max(1, round(A.LOOK_FRAC * frames))
  s_cam = F.ego_s(frame)
  ahead = -1 if rear else 1
  lines = L.sight_lines(sc)
  avoid = [tuple(o.matrix_world.translation[:2]) for o in bpy.data.objects
           if o.parent is None and o.name.split(".")[0] in ("billboard", "barn", "farmhouse", "silo")]
  bb_side = 0
  for x, y in avoid:
    s, d = F.sd(x, y)
    if F.c[0][3] <= s <= F.c[-1][3] and abs(s - s_cam) < 200:
      bb_side = 1 if d > 0 else -1
  farm_side = -bb_side if bb_side else rnd.choice((1, -1))
  rk = kits["rural_buildings"].pieces
  bins = kits["grain_bins"].pieces.get("bins", []) if "grain_bins" in kits else []
  placed, removed = [], 0

  def put(piece, name, s, side, out, turn):
    nonlocal removed
    if not F.c[0][3] <= s <= F.c[-1][3]:
      return False
    d = F.edge[side] + side * out
    x, y, _ = F.world(s, d)
    r = 0.5 * math.hypot(piece["w"], piece["d"])
    if any(math.hypot(x - ax, y - ay) < 22 + r for ax, ay in avoid) or L.in_view(lines, x, y, r):
      return False
    if any(math.hypot(x - px, y - py) < pr + r + 3 for px, py, pr in placed):
      return False
    h = F.at(s)[2]
    z = min(F.ground(x + dx, y + dy, F.sd(x + dx, y + dy)[1]) for dx in (-r, 0, r) for dy in (-r, 0, r)) - 0.15
    place(piece, name, coll, (x, y, z), h + (0.0 if side > 0 else math.pi) + turn)
    placed.append((x, y, r))
    for o in list(bpy.data.objects):                 # roadside trees under the building
      if o.name.split(".")[0] in ("tree", "crown", "conifer", "shrub") and o.type == "MESH":
        ox, oy = o.matrix_world.translation[:2]
        if math.hypot(ox - x, oy - y) < r + 2:
          bpy.data.objects.remove(o)
          removed += 1
    return True

  s0 = s_cam + ahead * rnd.uniform(125, 150)         # far enough ahead to stay in the chase camera's field
  yard = [(0, 0, 0.0), (28, 6, math.pi / 2), (-24, 10, 0.0), (8, 30, math.pi), (-40, 32, math.pi / 2)]
  farm = list(rk.get("farm", []))
  rnd.shuffle(farm)
  n = 0
  for (ds, dd, turn), piece in zip(yard, farm, strict=False):
    n += put(piece, f"farm{n}", s0 + ahead * ds, farm_side, 30 + dd, turn + rnd.uniform(-0.15, 0.15))
  if bins:
    n += put(bins[0], "grain_bins", s0 + ahead * 45, farm_side, 52, rnd.uniform(-0.2, 0.2))
  road = list(rk.get("roadside", []))
  rnd.shuffle(road)
  m = 0
  for side in (-farm_side, farm_side):          # the diner where it has room, its cars parked beside it
    s = s_cam + ahead * rnd.uniform(80, 95)
    for piece in road[:3]:
      if put(piece, f"roadside{m}", s, side, 16, 0.0):
        if m == 0 and cars:
          for j in range(DINER_CARS):
            car_s = s - ahead * (piece["w"] / 2 + 4.0 + 3.2 * j)
            d = F.edge[side] + side * (17.0 + 0.6 * j)
            x, y, _ = F.world(car_s, d)
            if not L.in_view(lines, x, y, 2.4):
              place(rnd.choice(cars), f"diner_car{j}", coll, (x, y, F.ground(x, y, d)),
                    F.at(car_s)[2] + math.pi / 2 * side)
        m += 1
      s += ahead * (piece["w"] + rnd.uniform(6, 14))
    if m:
      break
  return f"farmstead {n} pieces, roadside {m}, {removed} trees cleared"
