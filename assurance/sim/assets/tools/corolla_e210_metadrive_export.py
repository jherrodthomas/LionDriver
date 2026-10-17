"""Turn the purchased Corolla E210 mesh into the files MetaDrive's vehicle loader expects.

Run headless with Blender 4.x (no add-ons needed; the glTF importer/exporter ships with Blender):

    blender --background --python assurance/sim/assets/tools/corolla_e210_metadrive_export.py -- \\
        --input assurance/sim/assets/1450755-gltf-extended.glb \\
        --output-dir assurance/sim/assets/corolla_e210

Input: the full GLB delivered by TurboSquid for product 1450755 (3d_molier "Toyota Corolla 2020 Simple
Interior"). Licensed, editorial use only: the input and every output stay out of the public repository
(assurance/sim/assets/ is git-ignored except README.md and this tools/ folder).

What it does, in order (each step logs to stdout):

  1. imports the GLB and bakes every node transform, so the scene is in metres, Z up (the GLB's root node
     carries the cm-to-m scale and the Y-up rotation; the receipt check in vehicle-3d-model.md section 4 quoted
     the raw child coordinates in cm)
  2. makes the car face +Y, the forward axis of a MetaDrive vehicle node (metadrive/component/vehicle/
     base_vehicle.py `_create_wheel`: front wheels at +FRONT_WHEELBASE on Y, lateral offsets on X, Z up);
     which end is the front is read from the front/rear tyre meshes, not assumed
  3. splits the fused front-wheel meshes (wheels_forward, tires_forward, brake_discs_3) into loose parts and
     regroups the parts by side, so each of the four wheels is its own rim, tyre and disc
  4. finds the four hub centres from the tyre bounding boxes, moves the ground plane (tyre bottom) to Z = 0
     and the body's bounding-box centre to X = Y = 0
  5. drops the interior (interier, interier_glass, felt, steering_wheel) and decimates the rest to about
     --target-triangles (default 70 000) with Blender's collapse decimator, leaving small parts untouched
  6. exports
       vehicle.gltf             body only, origin at the ground under the body centre, forward +Y
       right_tire_front.gltf    right-front rim + tyre + disc, origin at the hub centre
       right_tire_back.gltf     right-rear rim + tyre + disc, origin at the hub centre
       vehicle_full.gltf        body plus all four wheels, each parented to an empty at its hub (for figures)
       geometry.json            hub positions, tyre radius, body box and counts, read by the vehicle class
       SHA256SUMS               checksums of everything above, for the private assets repository
     Textures go to --output-dir/textures (PNG, resized to --texture-size, default 2048).

MetaDrive loads vehicle.gltf as the chassis and `right_tire_front.gltf` / `right_tire_back.gltf` for the wheels;
the left wheels are the same files mirrored by the engine (scale -1). It positions the chassis model at
Z = -(TIRE_RADIUS + CHASSIS_TO_WHEEL_AXIS) under the vehicle origin, which is why the body's origin is put at the
ground plane here, and the wheels at its own FRONT_WHEELBASE / REAR_WHEELBASE / LATERAL_TIRE_TO_CENTER, which is
why geometry.json records where the hubs are relative to the body centre: the vehicle class copies them.

Nothing here is evidence. The mesh changes no plant or safety result (vehicle-3d-model.md section 1).

Draft. AI-drafted (Claude, AI assistant; I0 under WP-M-02 section 3.3); not reviewed. Written on a machine
without Blender, so the first run is the test: read the log, and if a step fails, send the traceback back.
"""

import argparse
import hashlib
import json
import math
import os
import sys
from collections import defaultdict

import bpy
from mathutils import Matrix, Vector

SCRIPT_VERSION = "0.1"

# Mesh names in the delivered GLB (receipt check, vehicle-3d-model.md section 4).
FRONT_FUSED = {"wheel": "wheels_forward", "tire": "tires_forward", "disc": "brake_discs_3"}
REAR = {
    # name -> kind ; which rear mesh is left or right is decided from the geometry, not the name
    "wheel_1": "wheel", "wheel_2": "wheel",
    "tire_1": "tire", "tire_2": "tire",
    "brake_discs_1": "disc", "brake_discs_2": "disc",
}
INTERIOR = ("interier", "interier_glass", "felt", "steering_wheel")
# Parts below this many triangles are not decimated (badges, mirrors, wipers lose their shape otherwise).
MIN_DECIMATE_TRIS = 400
MIN_RATIO = 0.08


def log(msg):
    print(f"[corolla_e210] {msg}", flush=True)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--input", required=True, help="full GLB from TurboSquid (1450755-gltf-extended.glb)")
    p.add_argument("--output-dir", required=True, help="folder for vehicle.gltf and friends (git-ignored)")
    p.add_argument("--target-triangles", type=int, default=70_000,
                   help="triangle budget for body + four wheels after decimation (default 70000)")
    p.add_argument("--texture-size", type=int, default=2048, help="max texture edge in pixels (default 2048)")
    p.add_argument("--keep-interior", action="store_true", help="keep the interior meshes (figures only)")
    return p.parse_args(argv)


# ----------------------------------------------------------------------------------------------------------------
# scene helpers
# ----------------------------------------------------------------------------------------------------------------

def mesh_objects():
    return [o for o in bpy.data.objects if o.type == "MESH"]


def select_only(objs, active=None):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or (objs[0] if objs else None)


def tri_count(obj):
    return sum(len(poly.vertices) - 2 for poly in obj.data.polygons)


def world_bbox(objs):
    lo = Vector((math.inf,) * 3)
    hi = Vector((-math.inf,) * 3)
    for o in objs:
        for corner in o.bound_box:
            w = o.matrix_world @ Vector(corner)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def bbox_centre(objs):
    lo, hi = world_bbox(objs)
    return (lo + hi) / 2, hi - lo


def apply_all_transforms():
    """Clear parents keeping world transforms, then bake rotation/scale/location into the mesh data."""
    objs = list(bpy.data.objects)
    select_only(objs)
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    meshes = mesh_objects()
    select_only(meshes)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in objs:
        if o.type == "EMPTY":
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()


def transform_scene(matrix):
    for o in mesh_objects():
        o.data.transform(matrix)
        o.data.update()
    bpy.context.view_layer.update()


def set_origin(obj, point):
    """Move obj's origin to world point without moving its geometry (obj must have an identity transform)."""
    obj.data.transform(Matrix.Translation(-Vector(point)))
    obj.data.update()
    obj.location = Vector(point)
    bpy.context.view_layer.update()


def separate_loose(obj):
    """Split obj into loose parts; returns the list of resulting objects (obj included)."""
    before = set(bpy.data.objects)
    select_only([obj], active=obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    return [obj] + [o for o in bpy.data.objects if o not in before]


def join(objs, name):
    if len(objs) > 1:
        select_only(objs, active=objs[0])
        bpy.ops.object.join()
    joined = objs[0]
    joined.name = name
    joined.data.name = name
    return joined


def split_by_side(obj, kind):
    """Separate a fused left+right mesh into one object per side, named f'{kind}_front_{side}'."""
    parts = separate_loose(obj)
    log(f"  {obj.name}: {len(parts)} loose part(s)")
    if len(parts) < 2:
        raise RuntimeError(f"{obj.name} did not split into two sides; check the mesh by hand")
    sides = defaultdict(list)
    for p in parts:
        c, _ = bbox_centre([p])
        sides["right" if c.x > 0 else "left"].append(p)
    if not sides["left"] or not sides["right"]:
        raise RuntimeError(f"{obj.name}: all loose parts fell on one side (x centres: "
                           f"{[round(bbox_centre([p])[0].x, 3) for p in parts]})")
    return {side: join(group, f"{kind}_front_{side}") for side, group in sides.items()}


def decimate(obj, ratio):
    mod = obj.modifiers.new("decimate", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj]):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def shrink_textures(max_edge):
    for img in bpy.data.images:
        w, h = img.size
        if w and h and max(w, h) > max_edge:
            s = max_edge / max(w, h)
            img.scale(max(1, int(w * s)), max(1, int(h * s)))
            log(f"  texture {img.name}: {w}x{h} -> {img.size[0]}x{img.size[1]}")


def export_gltf(path, objs, texture_dir):
    select_only(objs, active=objs[0])
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLTF_SEPARATE",
        use_selection=True,
        export_yup=True,
        export_apply=True,
        export_texture_dir=texture_dir,
        export_image_format="AUTO",
        export_materials="EXPORT",
        export_normals=True,
        export_texcoords=True,
        export_animations=False,
        export_skins=False,
        export_morph=False,
        export_lights=False,
        export_cameras=False,
    )
    log(f"  wrote {path}")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_checksums(out_dir):
    lines = []
    for root, _dirs, files in os.walk(out_dir):
        for fn in sorted(files):
            if fn == "SHA256SUMS":
                continue
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, out_dir).replace(os.sep, "/")
            lines.append(f"{sha256(p)} *{rel}")
    with open(os.path.join(out_dir, "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return len(lines)


# ----------------------------------------------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------------------------------------------

def main():
    args = parse_args()
    in_path = os.path.abspath(args.input)
    out_dir = os.path.abspath(args.output_dir)
    if not os.path.isfile(in_path):
        sys.exit(f"input not found: {in_path}")
    os.makedirs(out_dir, exist_ok=True)
    input_sha = sha256(in_path)
    log(f"Blender {bpy.app.version_string}, script {SCRIPT_VERSION}")
    log(f"input {in_path} sha256 {input_sha}")

    # 1. fresh scene, import, bake transforms -------------------------------------------------------------------
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=in_path)
    log(f"imported {len(mesh_objects())} mesh objects, {sum(map(tri_count, mesh_objects()))} triangles")
    apply_all_transforms()
    lo, hi = world_bbox(mesh_objects())
    size = hi - lo
    log(f"scene box after transform apply: {size.x:.3f} x {size.y:.3f} x {size.z:.3f} m "
        f"(expect about 1.77 x 4.66 x 1.46)")
    if not (4.0 < size.y < 5.5 and 1.5 < size.x < 2.1):
        raise RuntimeError("scene is not a car in metres with its length on Y; the GLB root transform changed")
    for name in list(FRONT_FUSED.values()) + list(REAR) + ["body"]:
        if name not in bpy.data.objects:
            raise RuntimeError(f"mesh {name!r} not found; objects: {sorted(o.name for o in bpy.data.objects)}")

    # 2. face +Y ------------------------------------------------------------------------------------------------
    body = bpy.data.objects["body"]
    front_y = bbox_centre([bpy.data.objects[FRONT_FUSED["tire"]]])[0].y
    rear_y = bbox_centre([bpy.data.objects["tire_1"], bpy.data.objects["tire_2"]])[0].y
    if front_y < rear_y:
        log("front tyres are at -Y: rotating the car 180 degrees about Z")
        transform_scene(Matrix.Rotation(math.pi, 4, "Z"))
    else:
        log("front tyres are already at +Y: no rotation")

    # 3. split the fused front wheel meshes ------------------------------------------------------------------------
    log("splitting fused front meshes by loose parts")
    front = {kind: split_by_side(bpy.data.objects[name], kind) for kind, name in FRONT_FUSED.items()}
    rear_by_side = defaultdict(dict)
    for name, kind in REAR.items():
        o = bpy.data.objects[name]
        side = "right" if bbox_centre([o])[0].x > 0 else "left"
        if kind in rear_by_side[side]:
            raise RuntimeError(f"two rear {kind} meshes on the {side} side; check names {list(REAR)}")
        rear_by_side[side][kind] = o
        o.name = f"{kind}_rear_{side}"
    wheels = {
        ("front", "left"): {kind: front[kind]["left"] for kind in front},
        ("front", "right"): {kind: front[kind]["right"] for kind in front},
        ("rear", "left"): rear_by_side["left"],
        ("rear", "right"): rear_by_side["right"],
    }
    for key, parts in wheels.items():
        if set(parts) != {"wheel", "tire", "disc"}:
            raise RuntimeError(f"wheel {key} is missing parts: have {sorted(parts)}")

    # 4. ground plane, body centre, hubs ---------------------------------------------------------------------------
    all_tyres = [parts["tire"] for parts in wheels.values()]
    ground_z = world_bbox(all_tyres)[0].z
    body_centre, body_size = bbox_centre([body])
    transform_scene(Matrix.Translation(Vector((-body_centre.x, -body_centre.y, -ground_z))))
    log(f"moved ground to Z=0 (was {ground_z:.4f}) and body centre to X=Y=0 "
        f"(was {body_centre.x:.4f}, {body_centre.y:.4f})")
    hubs = {}
    tyre_radii = []
    tyre_widths = []
    for key, parts in wheels.items():
        c, s = bbox_centre([parts["tire"]])
        hubs[key] = c
        tyre_radii.append(s.z / 2)
        tyre_widths.append(s.x)
        log(f"  hub {key[0]}-{key[1]}: x={c.x:+.4f} y={c.y:+.4f} z={c.z:.4f}  tyre d={s.z:.4f} w={s.x:.4f}")
    tyre_radius = sum(tyre_radii) / 4
    tyre_width = sum(tyre_widths) / 4
    front_wheelbase = (hubs[("front", "left")].y + hubs[("front", "right")].y) / 2
    rear_wheelbase = -(hubs[("rear", "left")].y + hubs[("rear", "right")].y) / 2
    lateral = sum(abs(h.x) for h in hubs.values()) / 4
    if front_wheelbase <= 0 or rear_wheelbase <= 0:
        raise RuntimeError("front hubs are not ahead of the body centre; orientation step failed")
    log(f"wheelbase {front_wheelbase + rear_wheelbase:.4f} m (opendbc 2.700), track {2 * lateral:.4f} m")

    # 5. interior out, decimate ------------------------------------------------------------------------------------
    removed = []
    if not args.keep_interior:
        for name in INTERIOR:
            o = bpy.data.objects.get(name)
            if o is not None:
                removed.append((name, tri_count(o)))
                bpy.data.objects.remove(o, do_unlink=True)
        log(f"dropped interior: {removed}")
    wheel_objs = [o for parts in wheels.values() for o in parts.values()]
    body_objs = [o for o in mesh_objects() if o not in wheel_objs]
    before = sum(map(tri_count, mesh_objects()))
    decimable = [o for o in mesh_objects() if tri_count(o) >= MIN_DECIMATE_TRIS]
    fixed = before - sum(map(tri_count, decimable))
    ratio = max(MIN_RATIO, min(1.0, (args.target_triangles - fixed) / max(1, sum(map(tri_count, decimable)))))
    log(f"{before} triangles before decimation; {len(decimable)} parts decimated at ratio {ratio:.3f}, "
        f"{len(mesh_objects()) - len(decimable)} small parts kept")
    for o in decimable:
        decimate(o, ratio)
    after = sum(map(tri_count, mesh_objects()))
    log(f"{after} triangles after decimation (body {sum(map(tri_count, body_objs))}, "
        f"wheels {sum(map(tri_count, wheel_objs))})")

    shrink_textures(args.texture_size)

    # 6. export ----------------------------------------------------------------------------------------------------
    tex_dir = "textures"
    outputs = {}

    # body: origin already at ground / body centre (every object has an identity transform)
    outputs["vehicle.gltf"] = os.path.join(out_dir, "vehicle.gltf")
    export_gltf(outputs["vehicle.gltf"], body_objs, tex_dir)

    # right wheels: origin at the hub, exported at the world origin
    for pos, fname in (("front", "right_tire_front.gltf"), ("rear", "right_tire_back.gltf")):
        parts = wheels[(pos, "right")]
        hub = hubs[(pos, "right")]
        for o in parts.values():
            set_origin(o, hub)
            o.location = Vector((0, 0, 0))
        bpy.context.view_layer.update()
        outputs[fname] = os.path.join(out_dir, fname)
        export_gltf(outputs[fname], list(parts.values()), tex_dir)
        for o in parts.values():
            o.location = hub
        bpy.context.view_layer.update()

    # full car for figures: four hub empties, wheels parented
    for (pos, side), parts in wheels.items():
        hub = hubs[(pos, side)]
        empty = bpy.data.objects.new(f"hub_{pos}_{side}", None)
        bpy.context.scene.collection.objects.link(empty)
        empty.location = hub
        bpy.context.view_layer.update()
        for o in parts.values():
            if side == "left":
                set_origin(o, hub)
            o.parent = empty
            o.matrix_parent_inverse = empty.matrix_world.inverted()
    bpy.context.view_layer.update()
    outputs["vehicle_full.gltf"] = os.path.join(out_dir, "vehicle_full.gltf")
    export_gltf(outputs["vehicle_full.gltf"], list(bpy.data.objects), tex_dir)

    geometry = {
        "source": {"file": os.path.basename(in_path), "sha256": input_sha,
                   "product": "TurboSquid 1450755 (3d_molier, Toyota Corolla 2020 Simple Interior)"},
        "tool": {"script": os.path.basename(__file__), "version": SCRIPT_VERSION,
                 "blender": bpy.app.version_string,
                 "target_triangles": args.target_triangles, "texture_size": args.texture_size},
        "units": "metres; vehicle frame: X right, Y forward, Z up; origin at ground under the body centre",
        "body": {"length": round(body_size.y, 4), "width": round(body_size.x, 4), "height": round(body_size.z, 4)},
        "hubs": {f"{pos}_{side}": [round(v, 4) for v in hub] for (pos, side), hub in hubs.items()},
        "front_wheelbase": round(front_wheelbase, 4),
        "rear_wheelbase": round(rear_wheelbase, 4),
        "lateral_tire_to_center": round(lateral, 4),
        "tire_radius": round(tyre_radius, 4),
        "tire_width": round(tyre_width, 4),
        "triangles": {"before": before, "after": after,
                      "body": sum(map(tri_count, body_objs)), "wheels": sum(map(tri_count, wheel_objs))},
        "dropped": [n for n, _ in removed],
        "note": "Cosmetic asset: 18-inch sport-trim wheels on the mesh; changes no plant or safety result "
                "(assurance/sim/vehicle-3d-model.md sections 1 and 4).",
    }
    outputs["geometry.json"] = os.path.join(out_dir, "geometry.json")
    with open(outputs["geometry.json"], "w", encoding="utf-8") as f:
        json.dump(geometry, f, indent=2)
        f.write("\n")
    log(f"  wrote {outputs['geometry.json']}")

    n = write_checksums(out_dir)
    log(f"wrote SHA256SUMS ({n} files)")
    log("done")


if __name__ == "__main__":
    main()
