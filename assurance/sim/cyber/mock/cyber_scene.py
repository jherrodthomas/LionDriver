"""Mock cyber scene, step 1 of 2: hardware cutaway of the item inside a ghosted Corolla, with the TS-14 path and its gate.

Render-only mock for review (synthetic, DSR-12; no evidence credit). The parts are generic CC-BY stand-ins from the
private LionDriver-assets repository (sketchfab/), not the real hardware; the car is the purchased Corolla mesh.

  python3 assurance/sim/cyber/mock/cyber_scene.py            # Python 3.13 with `pip install bpy` (Blender 5.x)

The assets repository is LIONDRIVER_ASSETS_REPO, else a liondriver-assets or LionDriver-assets folder beside this
repository (as in ../../blender/fetch_assets.py). Each zip is checked against its SHA256SUMS and unpacked under out/.
Writes out/cutaway.png and out/anchors.json: pixel positions of the labelled points (compose.py), and of the TS-14 path
centre line and the gate ring sampled along their length (animate.py). With --anchors-only it writes the JSON and skips
the render (a few seconds).
"""
import bpy, bmesh, hashlib, json, math, os, sys, zipfile
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = HERE / "out"; OUT.mkdir(parents=True, exist_ok=True)
RES = (1840, 1040)
PARTS = ("saphyroo-adasdms-device", "electronics-enclosure", "automotive-relay", "raspberry-pi-cam-v21",
         "intelligent-motor-control-module-imcu", "engine-control-unit-simplified", "raspberry-pi-4-compute-module-cm4",
         "3d-pcb--wired-stm32-game-controller-2026-05-26")


def assets_repo() -> Path:
  if os.environ.get("LIONDRIVER_ASSETS_REPO"):
    return Path(os.environ["LIONDRIVER_ASSETS_REPO"])
  for name in ("liondriver-assets", "LionDriver-assets"):
    if (ROOT.parent / name).is_dir():
      return ROOT.parent / name
  sys.exit("LionDriver-assets not found: set LIONDRIVER_ASSETS_REPO")


def sums(folder: Path) -> dict:
  return {ln.split()[1].lstrip("*"): ln.split()[0] for ln in (folder / "SHA256SUMS").read_text().splitlines() if ln.strip()}


def unpack(repo: Path) -> Path:
  """Unpack each part zip (and the zip inside its source/ folder, where the author nested one) under out/assets."""
  dest = OUT / "assets"; ok = sums(repo / "sketchfab")
  for name in PARTS:
    z = repo / "sketchfab" / f"{name}.zip"
    if hashlib.sha256(z.read_bytes()).hexdigest() != ok[z.name]:
      sys.exit(f"{z.name}: SHA-256 differs from SHA256SUMS")
    with zipfile.ZipFile(z) as f: f.extractall(dest / name)
    for inner in (dest / name / "source").glob("*.zip"):
      with zipfile.ZipFile(inner) as f: f.extractall(inner.parent / "x")
  return dest


REPO = assets_repo()
A = unpack(REPO)
CAR = REPO / "corolla-e210-3dmolier-1450755" / "1450755-gltf-extended.glb"
if CAR.read_bytes()[:4] != b"glTF":
  sys.exit(f"{CAR}: not a glb (an unfetched Git LFS pointer?): run git lfs pull in the assets repository")

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def mat(name, color, emit=0.0, alpha=1.0, rough=0.5, metal=0.0):
  m = bpy.data.materials.new(name); m.use_nodes = True
  b = m.node_tree.nodes["Principled BSDF"]
  b.inputs["Base Color"].default_value = (*color, 1)
  b.inputs["Roughness"].default_value = rough
  b.inputs["Metallic"].default_value = metal
  if emit:
    b.inputs["Emission Color"].default_value = (*color, 1); b.inputs["Emission Strength"].default_value = emit
  if alpha < 1:
    b.inputs["Alpha"].default_value = alpha
    m.blend_method = "BLEND" if hasattr(m, "blend_method") else None
  return m


def ghost(name, color, alpha, edge):
  """X-ray look: almost clear face-on, brighter at grazing angles (layer weight drives the alpha)."""
  m = bpy.data.materials.new(name); m.use_nodes = True
  nt = m.node_tree; n = nt.nodes; l = nt.links
  n.clear()
  out = n.new("ShaderNodeOutputMaterial")
  em = n.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*color, 1); em.inputs["Strength"].default_value = 0.22
  tr = n.new("ShaderNodeBsdfTransparent")
  lw = n.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = edge
  mp = n.new("ShaderNodeMapRange"); mp.inputs["To Min"].default_value = alpha * 0.25; mp.inputs["To Max"].default_value = alpha
  mx = n.new("ShaderNodeMixShader")
  l.new(lw.outputs["Facing"], mp.inputs["Value"])
  l.new(mp.outputs["Result"], mx.inputs["Fac"])
  l.new(tr.outputs[0], mx.inputs[1]); l.new(em.outputs[0], mx.inputs[2])
  l.new(mx.outputs[0], out.inputs["Surface"])
  return m


# ------------------------------------------------------------------ the car, ghosted
bpy.ops.import_scene.gltf(filepath=str(CAR))
KEEP_SOLIDISH = {"interier": 0.55, "steering_wheel": 0.9}
g_body = ghost("ghost_body", (0.45, 0.6, 0.85), 0.5, 0.3)
g_glass = ghost("ghost_glass", (0.45, 0.6, 0.85), 0.25, 0.2)
g_int = ghost("ghost_int", (0.6, 0.62, 0.66), 0.55, 0.4)
g_wheel = ghost("ghost_wheel", (0.85, 0.85, 0.82), 0.95, 0.6)
DROP = ("felt", "chassis", "bottom", "exhaust", "brake", "chassis_detail", "schilds", "reflectors", "lenses",
        "door_metal", "door_plastic", "rubber", "molding", "plastic_1", "headlights_7", "headlights_8")
for o in list(bpy.data.objects):
  if o.type != "MESH":
    continue
  if o.name.startswith(DROP):
    bpy.data.objects.remove(o, do_unlink=True); continue
  m = g_body
  if o.name.startswith(("window", "windows", "interier_glass")): m = g_glass
  elif o.name.startswith("interier"): m = g_int
  elif o.name.startswith("steering_wheel"): m = g_wheel
  o.data.materials.clear(); o.data.materials.append(m)
  o.visible_shadow = False


# ------------------------------------------------------------------ parts
def import_part(kind, path, **kw):
  before = set(bpy.data.objects)
  if kind == "obj": bpy.ops.wm.obj_import(filepath=str(path))
  elif kind == "fbx": bpy.ops.import_scene.fbx(filepath=str(path))
  elif kind == "stl": bpy.ops.wm.stl_import(filepath=str(path))
  elif kind == "blend":
    with bpy.data.libraries.load(str(path)) as (src, dst):
      dst.objects = [n for n in src.objects]
    for o in dst.objects:
      if o is not None and o.type == "MESH": sc.collection.objects.link(o)
  return [o for o in set(bpy.data.objects) - before if o.type == "MESH"]


def place(objs, size, loc, rot=(0, 0, 0), material=None):
  """Scale the group so its largest extent is `size` m, centre it at `loc`, then rotate (degrees) about that centre."""
  root = bpy.data.objects.new("grp", None); sc.collection.objects.link(root)
  pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
  mn = Vector([min(p[i] for p in pts) for i in range(3)]); mx = Vector([max(p[i] for p in pts) for i in range(3)])
  c = (mn + mx) / 2; s = size / max(mx - mn)
  for o in objs:
    mw = o.matrix_world.copy(); o.parent = root; o.matrix_world = mw
    o.location -= c * 0  # keep
  root.location = -c
  bpy.context.view_layer.update()
  top = bpy.data.objects.new("place", None); sc.collection.objects.link(top)
  root.parent = top; top.scale = (s, s, s); top.rotation_euler = [math.radians(a) for a in rot]; top.location = loc
  if material:
    for o in objs:
      o.data.materials.clear(); o.data.materials.append(material)
  return top


def tex_mat(name, base, rough=0.5, metal=0.0, normal=None):
  m = bpy.data.materials.new(name); m.use_nodes = True
  nt = m.node_tree; b = nt.nodes["Principled BSDF"]
  t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(str(base))
  nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
  b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
  return m


housing = mat("housing", (0.06, 0.06, 0.065), rough=0.45)
alu = mat("alu", (0.62, 0.63, 0.66), rough=0.35, metal=1.0)
pcb_green = mat("pcb", (0.05, 0.28, 0.12), rough=0.4)
relay_m = mat("relay", (0.12, 0.12, 0.13), rough=0.5)

# SoC: comma device stand-in on the windshield, below the interior mirror
cam = import_part("fbx", A / "saphyroo-adasdms-device/source/Cam_1.fbx")
dev = place(cam, 0.17, (0.0, -0.56, 1.17), (0, 0, 180),
            tex_mat("dev", A / "saphyroo-adasdms-device/textures/CAM_1_Base_color.png", 0.45))
# harness box with its relay, behind the mirror beside the forward camera
enc = place(import_part("stl", A / "electronics-enclosure/source/x/Electronics_Enclosure.stl"), 0.12,
            (-0.2, -0.5, 1.28), (0, 0, 15), housing)
rel = place(import_part("stl", A / "automotive-relay/source/12VDC_30A_relay.stl"), 0.05, (-0.2, -0.5, 1.36), (0, 0, 15), relay_m)
# forward camera (stock PCS), top of the windshield
fcam = place(import_part("blend", A / "raspberry-pi-cam-v21/source/Pi_Cam_Avecjointure.blend"), 0.08,
             (0.08, -0.47, 1.36), (70, 0, 180))
# EPS motor and ECU on the steering column
imcu = import_part("obj", A / "intelligent-motor-control-module-imcu/source/x/Intelligent Motor Control Module .obj")
eps = place(imcu, 0.30, (0.42, -0.95, 0.66), (0, 25, 90),
            tex_mat("imcu", next((A / "intelligent-motor-control-module-imcu/textures").glob("*.jpeg")), 0.4, 0.8))
# two car-side ECUs (engine/ACC and brakes): generic boxes
ecu_fbx = A / "engine-control-unit-simplified/source/ECU.fbx"
pcm = place(import_part("fbx", ecu_fbx), 0.22, (-0.35, -1.75, 0.78), (0, 0, 10), housing)
abs_ = place(import_part("fbx", ecu_fbx), 0.18, (0.48, -1.7, 0.72), (0, 0, -10), housing)

# exploded internals, floated above the roof with leader lines: SoC board and the panda safety MCU board
EXP_SOC = Vector((0.36, -0.75, 1.95)); EXP_PANDA = Vector((-0.30, -0.75, 1.95))
soc_b = place(import_part("blend", A / "raspberry-pi-4-compute-module-cm4/source/untitled.blend"), 0.30, EXP_SOC, (62, 0, 180))
for o in soc_b.children_recursive:
  if o.type == "MESH" and not o.data.materials:
    o.data.materials.append(pcb_green)
stm = import_part("obj", A / "3d-pcb--wired-stm32-game-controller-2026-05-26/source/x/3D_PCB_Wired stm32 game controller_2026-05-26.obj")
# drop the two joysticks of this game-controller board so it reads as a plain MCU board
for o in stm:
  me = o.data; bm = bmesh.new(); bm.from_mesh(me)
  ax = min(range(3), key=lambda i: max(v.co[i] for v in bm.verts) - min(v.co[i] for v in bm.verts))
  hist = {}
  for v in bm.verts:
    k = round(v.co[ax]); hist[k] = hist.get(k, 0) + 1
  plane = max(hist, key=hist.get)                      # the board surface holds the most vertices
  bmesh.ops.delete(bm, geom=[v for v in bm.verts if abs(v.co[ax] - plane) > 6.0], context="VERTS")
  bm.to_mesh(me); bm.free()
panda_b = place(stm, 0.30, EXP_PANDA, (62, 0, 180))

# steering column (procedural) and the OBD-II port
def cyl(a, b, r, m, name="cyl"):
  a, b = Vector(a), Vector(b); d = b - a
  bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, location=(a + b) / 2, vertices=24)
  o = bpy.context.object; o.name = name
  o.rotation_euler = d.to_track_quat("Z", "Y").to_euler(); o.data.materials.append(m); return o
cyl((0.39, -0.52, 0.86), (0.39, -1.05, 0.55), 0.028, alu, "column")
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.45, -0.98, 0.42)); obd = bpy.context.object
obd.scale = (0.05, 0.03, 0.02); obd.data.materials.append(housing)

# ------------------------------------------------------------------ wiring and the attack path
def tube(points, r, m, name):
  cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = r; cu.bevel_resolution = 4
  sp = cu.splines.new("BEZIER"); sp.bezier_points.add(len(points) - 1)
  for p, q in zip(sp.bezier_points, points):
    p.co = q; p.handle_left_type = p.handle_right_type = "AUTO"
  o = bpy.data.objects.new(name, cu); sc.collection.objects.link(o); cu.materials.append(m); return o

wire = mat("wire", (0.75, 0.75, 0.72), rough=0.6)
can = mat("can", (0.2, 0.5, 1.0), emit=1.5, rough=0.5)
path = mat("path", (0.85, 0.15, 0.95), emit=3.2)
lead = mat("lead", (0.8, 0.8, 0.8), emit=0.6)
HB = Vector((-0.2, -0.5, 1.28)); DEV = Vector((0.0, -0.56, 1.17)); FC = Vector((0.08, -0.47, 1.36))
BUS = [HB, Vector((-0.55, -0.85, 1.05)), Vector((-0.45, -1.15, 0.62)), Vector((0.0, -1.25, 0.55)),
       Vector((0.39, -1.0, 0.58))]
tube([DEV, Vector((-0.1, -0.5, 1.26)), HB], 0.007, wire, "dev_cable")
tube([HB, Vector((-0.05, -0.45, 1.36)), FC], 0.006, can, "bus2_camera")
tube(BUS, 0.008, can, "bus0_car")
tube([Vector((-0.45, -1.15, 0.62)), Vector((-0.4, -1.5, 0.7)), Vector((-0.35, -1.75, 0.78))], 0.007, can, "bus0_pcm")
tube([Vector((0.0, -1.25, 0.55)), Vector((0.3, -1.45, 0.62)), Vector((0.48, -1.7, 0.72))], 0.007, can, "bus0_abs")
tube([Vector((0.0, -1.25, 0.55)), Vector((0.3, -1.1, 0.45)), Vector((0.45, -0.98, 0.42))], 0.006, can, "bus0_obd")
# leader lines from the device to its exploded boards
tube([DEV, EXP_SOC + Vector((0, 0, -0.12))], 0.0025, lead, "lead_soc")
tube([DEV, EXP_PANDA + Vector((0, 0, -0.12))], 0.0025, lead, "lead_panda")
# TS-14: SoC -> panda (through its gate) -> harness relay -> car bus -> EPS
P = [EXP_SOC + Vector((-0.12, 0, 0.02)), (EXP_SOC + EXP_PANDA) / 2 + Vector((0, 0, 0.08)), EXP_PANDA + Vector((0.1, 0, 0.0)),
     EXP_PANDA + Vector((0.05, 0.05, -0.35)), HB + Vector((0, 0, 0.06))]
PATH_UP = P
PATH_LO = [HB + Vector((0, 0, 0.0))] + [b + Vector((0, 0, 0.012)) for b in BUS[1:]] + [Vector((0.39, -0.86, 0.66))]
tube(PATH_UP, 0.011, path, "ts14_upper")
tube(PATH_LO, 0.011, path, "ts14_lower")

# the gate at the panda: dashed amber ring (partial: built in the reference build only, not verified)
amber = mat("amber", (0.98, 0.62, 0.05), emit=3.5)
R, N = 0.2, 22
for i in range(N):
  if i % 2: continue
  a0, a1 = 2 * math.pi * i / N, 2 * math.pi * (i + 1) / N
  pts = [EXP_PANDA + Vector((R * math.cos(a), 0.0, R * math.sin(a))) for a in (a0, (a0 + a1) / 2, a1)]
  bpy.ops.mesh.primitive_cube_add(size=1)
  o = bpy.context.object; mid = pts[1]; o.location = mid
  o.scale = (0.012, 0.012, (pts[2] - pts[0]).length / 2 * 1.9)
  o.rotation_euler = (pts[2] - pts[0]).to_track_quat("Z", "Y").to_euler(); o.data.materials.append(amber)
# rotate the ring into the board's tilted plane
# (left in the XZ plane facing the camera: reads as a ring around the board in the view)

# ------------------------------------------------------------------ world, light, camera
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.012, 0.013, 0.016, 1); bg.inputs["Strength"].default_value = 1
bpy.ops.object.light_add(type="AREA", location=(-2.5, -4.0, 4.0)); L = bpy.context.object
L.data.energy = 600; L.data.size = 4; L.rotation_euler = (math.radians(50), 0, math.radians(-30))
bpy.ops.object.light_add(type="AREA", location=(3.0, -1.0, 3.0)); L2 = bpy.context.object
L2.data.energy = 300; L2.data.size = 3; L2.rotation_euler = (math.radians(40), 0, math.radians(60))
# ground grid hint
bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, 0)); gp = bpy.context.object
gp.data.materials.append(mat("ground", (0.006, 0.007, 0.009), rough=0.9))

bpy.ops.object.camera_add(location=(-1.85, -2.85, 2.05)); camo = bpy.context.object; sc.camera = camo
camo.data.lens = 30
tgt = Vector((0.0, -0.95, 1.36))
camo.rotation_euler = (tgt - camo.location).to_track_quat("-Z", "Y").to_euler()

sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 96
try: sc.cycles.use_denoising = True
except Exception: pass
sc.render.resolution_x, sc.render.resolution_y = RES; sc.render.resolution_percentage = 100
sc.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in sc.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
sc.view_settings.look = "None"
sc.render.film_transparent = False
sc.render.filepath = str(OUT / "cutaway.png")

anchors = {"device": DEV, "harness": HB, "fcam": FC, "eps": Vector((0.39, -0.86, 0.62)), "pcm": Vector((-0.35, -1.75, 0.78)),
           "abs": Vector((0.48, -1.7, 0.72)), "obd": Vector((0.45, -0.98, 0.42)), "soc": EXP_SOC, "panda": EXP_PANDA,
           "gate": EXP_PANDA + Vector((-R * 0.7, 0, R * 0.7)), "wheel": Vector((0.39, -0.48, 0.9)), "bus": BUS[2]}
bpy.context.view_layer.update()
px = {}
for k, v in anchors.items():
  p = world_to_camera_view(sc, camo, v); px[k] = [round(p.x * RES[0]), round((1 - p.y) * RES[1])]


def centre_line(points, name):
  """The same Bezier as tube() without a bevel, evaluated to its centre-line vertices, in order."""
  cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.resolution_u = 24
  sp = cu.splines.new("BEZIER"); sp.bezier_points.add(len(points) - 1)
  for p_, q in zip(sp.bezier_points, points):
    p_.co = q; p_.handle_left_type = p_.handle_right_type = "AUTO"
  o = bpy.data.objects.new(name, cu); sc.collection.objects.link(o); bpy.context.view_layer.update()
  me = o.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
  pts = [o.matrix_world @ v.co for v in me.vertices]; o.hide_render = True
  return pts


def to_px(v):
  p_ = world_to_camera_view(sc, camo, v); return [round(p_.x * RES[0], 1), round((1 - p_.y) * RES[1], 1)]


ring = [EXP_PANDA + Vector((R * math.cos(a), 0.0, R * math.sin(a))) for a in (2 * math.pi * k / 48 for k in range(48))]
geo = {"path_upper": [to_px(v) for v in centre_line(PATH_UP, "cl_up")],
       "path_lower": [to_px(v) for v in centre_line(PATH_LO, "cl_lo")], "ring": [to_px(v) for v in ring]}
json.dump({"res": RES, "px": px, **geo}, open(OUT / "anchors.json", "w"), indent=1)
if "--anchors-only" in sys.argv:
  sys.exit(0)
bpy.ops.render.render(write_still=True)
print("rendered", OUT / "cutaway.png")
