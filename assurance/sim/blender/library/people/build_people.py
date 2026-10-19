"""Build the pedestrian models of the hazardous-event scenes from two Quaternius CC0 packs (library/people/README.md).

Reads the free "Universal Base Characters [Standard]" and "Universal Animation Library [Standard]" zips (quaternius.com,
CC0 1.0) and writes one GLB per figure next to this script: the base body with a hairstyle, eyes and eyebrows on the
pack's 65-bone rig, its textures cut to 1024 px JPEG, clothes assigned from the bone each polygon follows (material
slots "shirt", "trousers" and "shoes", which hazard_scene.py recolours per pedestrian; the head and hands keep the
skin), and the library's Walk_Loop animation. Runs in Python 3.13 with bpy (pip install bpy) or Blender 4.2+:

  python3 assurance/sim/blender/library/people/build_people.py UBC.zip UAL.zip
"""

from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
BASE = "Universal Base Characters[Standard]"
HAIR = f"{BASE}/Hairstyles/Rigged to Head Bone/glTF (Godot -Unreal)"
FIGURES = {   # output -> body glTF, hairstyle, extra eyebrows (each body already has a pair), hair colour
  "pedestrian_male.glb": (f"{BASE}/Base Characters/Godot - UE/Superhero_Male_FullBody.gltf", "Hair_SimpleParted",
                          None, (0.10, 0.06, 0.035)),
  "pedestrian_female.glb": (f"{BASE}/Base Characters/Godot - UE/Superhero_Female_FullBody.gltf", "Hair_Buns",
                            None, (0.22, 0.11, 0.05)),
}
ANIMS = "Universal Animation Library[Standard]/Unreal-Godot/UAL1_Standard.glb"
WALK = "Walk_Loop"
TEXTURE_PX = 1024

# the bone a polygon follows decides what it wears (bone names of the pack's rig, lower case)
SKIN = ("head", "neck", "hand", "thumb", "index", "middle", "ring", "pinky")
LEGS = ("thigh", "calf", "pelvis")
FEET = ("foot", "ball")
CLOTHES = {"shirt": (0.13, 0.22, 0.42), "trousers": (0.07, 0.07, 0.08), "shoes": (0.03, 0.03, 0.03)}


def imported(path: Path) -> list:
  before = set(bpy.data.objects)
  bpy.ops.import_scene.gltf(filepath=str(path))
  new = [o for o in bpy.data.objects if o not in before]
  helpers = [o for o in new if o.name.startswith("Icosphere")]     # a light probe the pack ships with every model
  for o in helpers:
    bpy.data.objects.remove(o)
  return [o for o in new if o not in helpers]


def onto(meshes, arm) -> None:
  """Move meshes skinned to another copy of the same rig onto arm, and drop that copy."""
  for o in meshes:
    old = o.parent
    o.parent = arm
    for m in o.modifiers:
      if m.type == "ARMATURE":
        m.object = arm
    if old is not None and old.type == "ARMATURE" and old is not arm and not old.children:
      bpy.data.objects.remove(old)


def dress(body) -> dict[str, int]:
  names = {g.index: g.name.lower() for g in body.vertex_groups}
  slots = {}
  for k, rgb in CLOTHES.items():
    m = bpy.data.materials.new(k)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.85 if k != "shoes" else 0.55
    body.data.materials.append(m)
    slots[k] = len(body.data.materials) - 1
  count = {k: 0 for k in ("skin", *CLOTHES)}
  for p in body.data.polygons:
    score: dict[str, float] = {}
    for vi in p.vertices:
      for g in body.data.vertices[vi].groups:
        score[names[g.group]] = score.get(names[g.group], 0.0) + g.weight
    top = max(score, key=score.get) if score else ""
    if any(top.startswith(s) for s in FEET):
      k = "shoes"
    elif any(top.startswith(s) for s in SKIN):
      count["skin"] += 1
      continue
    elif any(top.startswith(s) for s in LEGS):
      k = "trousers"
    else:
      k = "shirt"
    p.material_index = slots[k]
    count[k] += 1
  return count


def tint_hair(rgb) -> None:
  """The pack's hair textures are grey, tinted by an engine shader: bake the colour into the base-colour image (glTF
  has no tint node, and the image is used by the hair and the eyebrows only)."""
  import numpy as np
  done = set()
  for m in bpy.data.materials:
    if not (m.use_nodes and m.name.startswith("MI_Hair")):
      continue
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    link = next((l for l in m.node_tree.links if l.to_socket == bsdf.inputs["Base Color"]), None)
    im = getattr(link.from_node, "image", None) if link else None
    if im is None or im.name in done:
      continue
    px = np.empty(im.size[0] * im.size[1] * 4, dtype=np.float32)
    im.pixels.foreach_get(px)
    px = px.reshape(-1, 4)
    px[:, :3] *= np.array([min(1.0, 2.2 * v) for v in rgb], dtype=np.float32)
    im.pixels.foreach_set(px.ravel())
    im.update()
    done.add(im.name)


def shrink_images() -> None:
  for im in bpy.data.images:
    if im.size[0] > TEXTURE_PX:
      im.scale(TEXTURE_PX, TEXTURE_PX * im.size[1] // im.size[0])


def build(src: Path, out: Path, body_path: str, hair: str, brows: str | None, hair_rgb) -> None:
  bpy.ops.wm.read_factory_settings(use_empty=True)
  objs = imported(src / body_path)
  arm = next(o for o in objs if o.type == "ARMATURE")
  body = max((o for o in objs if o.type == "MESH"), key=lambda o: len(o.data.polygons))
  for extra in (hair, brows):
    if extra:
      onto([o for o in imported(src / HAIR / f"{extra}.gltf") if o.type == "MESH"], arm)
  for o in [o for o in bpy.data.objects if o.type == "ARMATURE" and o is not arm]:
    bpy.data.objects.remove(o)
  count = dress(body)
  tint_hair(hair_rgb)
  for o in imported(src / ANIMS):
    bpy.data.objects.remove(o)
  walk = next(a for a in bpy.data.actions if a.name.startswith(WALK))
  for a in [a for a in bpy.data.actions if a is not walk]:
    bpy.data.actions.remove(a)
  walk.name = WALK
  arm.animation_data_create()
  arm.animation_data.action = walk
  if hasattr(walk, "slots") and walk.slots:     # Blender 4.4+: an action plays through one of its slots
    arm.animation_data.action_slot = walk.slots[0]
  shrink_images()
  bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB", export_image_format="JPEG",
                            export_image_quality=85, export_animations=True, export_animation_mode="ACTIONS",
                            export_apply=False, export_skins=True, export_yup=True)
  kb = out.stat().st_size // 1024
  print(f"{out.name}: {kb} KB; polygons {count}; animation {walk.name} {tuple(walk.frame_range)}")


def main(argv: list[str]) -> int:
  argv = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
  if len(argv) != 2:
    print(__doc__, file=sys.stderr)
    return 2
  with tempfile.TemporaryDirectory() as tmp:
    src = Path(tmp)
    for z in argv:
      zipfile.ZipFile(z).extractall(src)
    for name, (body, hair, brows, hair_rgb) in FIGURES.items():
      build(src, HERE / name, body, hair, brows, hair_rgb)
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
