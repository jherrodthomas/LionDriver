#!/usr/bin/env python3
"""Export the purchased Corolla E210 GLB into the MetaDrive vehicle layout without Blender.

    python3 assurance/sim/assets/tools/corolla_e210_gltf_export.py \
        --glb assurance/sim/assets/1450755-gltf-extended.glb --output-dir assurance/sim/assets/corolla_e210

Same output layout as corolla_e210_metadrive_export.py (the Blender script), so the vehicle class in
openpilot/tools/sim/bridge/metadrive/corolla_vehicle.py reads either:

    vehicle.gltf           body, origin at the ground under the body centre, forward +Y
    right_tire_front.gltf  right-front rim + tyre + disc, origin at the hub centre
    right_tire_back.gltf   right-rear rim + tyre + disc, origin at the hub centre
    vehicle_full.gltf      body plus the four wheels, each under a node at its hub (for figures and load tests)
    geometry.json          hub positions, tyre radius, body box and counts, read by the vehicle class
    textures/*.png         the GLB's embedded images, written out unchanged
    SHA256SUMS

What this script does that the Blender one does: bakes the GLB's units and axes, turns the car to face +Y,
splits the fused wheel pair into left and right by connected components, tells front from rear by the tail lamps, puts each wheel's origin at
its hub, drops the interior, and drops the underbody detail meshes that are never seen from outside
(chassis, chassis_detail_*). What it does NOT do: decimate. The body keeps the mesh's own triangle count
(about 215 000 after the drops), which a desktop GPU draws without trouble but a laptop may not; run the Blender
script for a 70 000-triangle version when Blender is available.

Everything is read as data (JSON and typed arrays); nothing from the asset is executed. The input and every
output are licensed, editorial-use content and stay out of the public repository (assurance/sim/assets/README.md).

Draft. AI-drafted (Claude, AI assistant; I0 under WP-M-02 section 3.3); not reviewed. Not evidence: the mesh
changes no plant or safety result (vehicle-3d-model.md section 1).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np

INTERIOR = {"interier", "interier_glass", "felt", "steering_wheel", "door_plastic_1", "door_plastic_2",
            "door_plastic_3", "door_plastic_4", "headlights_plastic"}
UNDERBODY = {"chassis", "chassis_detail_1", "chassis_detail_2", "chassis_detail_3", "chassis_detail_4",
             "chassis_detail_5", "chassis_detail_6"}
FRONT_FUSED = {"wheels_forward": "rim", "tires_forward": "tyre", "brake_discs_3": "disc"}
REAR = {"wheel_1": "rim", "wheel_2": "rim", "tire_1": "tyre", "tire_2": "tyre", "brake_discs_1": "disc", "brake_discs_2": "disc"}
CT = {5120: "<i1", 5121: "<u1", 5122: "<i2", 5123: "<u2", 5125: "<u4", 5126: "<f4"}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def log(msg):
  print(f"[corolla_e210] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------ read
def read_glb(path: Path):
  with path.open("rb") as f:
    magic, _, _ = struct.unpack("<4sII", f.read(12))
    if magic != b"glTF":
      raise SystemExit(f"{path}: not a GLB")
    clen, ctype = struct.unpack("<II", f.read(8))
    g = json.loads(f.read(clen).decode("utf-8"))
    blen, btype = struct.unpack("<II", f.read(8))
    buf = f.read(blen)
  return g, buf


def accessor(g, buf, idx) -> np.ndarray:
  a = g["accessors"][idx]
  bv = g["bufferViews"][a["bufferView"]]
  n = NCOMP[a["type"]]
  dt = np.dtype(CT[a["componentType"]])
  off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
  stride = bv.get("byteStride", dt.itemsize * n)
  raw = np.frombuffer(buf, dtype=np.uint8, count=stride * a["count"], offset=off).reshape(a["count"], stride)
  return raw[:, : dt.itemsize * n].copy().view(dt).reshape(a["count"], n)


def primitives(g, buf, mesh_idx):
  out = []
  for pr in g["meshes"][mesh_idx]["primitives"]:
    at = pr["attributes"]
    out.append({
      "pos": accessor(g, buf, at["POSITION"]).astype(np.float32),
      "nrm": accessor(g, buf, at["NORMAL"]).astype(np.float32) if "NORMAL" in at else None,
      "uv": accessor(g, buf, at["TEXCOORD_0"]).astype(np.float32) if "TEXCOORD_0" in at else None,
      "idx": accessor(g, buf, pr["indices"]).astype(np.uint32).reshape(-1) if "indices" in pr else None,
      "material": pr.get("material"),
    })
  return out


# ------------------------------------------------------------------------------------------------ geometry ops
def connected_components(pr):
  """Split one primitive into its connected components (vertex-connectivity over triangles)."""
  idx = pr["idx"].reshape(-1, 3)
  nv = len(pr["pos"])
  parent = np.arange(nv)

  def find(i):
    while parent[i] != i:
      parent[i] = parent[parent[i]]
      i = parent[i]
    return i

  for a, b, c in idx:
    ra, rb, rc = find(a), find(b), find(c)
    parent[rb] = ra
    parent[rc] = ra
  roots = np.array([find(i) for i in range(nv)])
  comps = {}
  for r in np.unique(roots):
    comps[r] = roots == r
  parts = []
  for r, mask in comps.items():
    remap = -np.ones(nv, dtype=np.int64)
    sel = np.nonzero(mask)[0]
    remap[sel] = np.arange(len(sel))
    tri_mask = mask[idx[:, 0]]
    sub = {k: (v[sel] if v is not None and k in ("pos", "nrm", "uv") else v) for k, v in pr.items()}
    sub["idx"] = remap[idx[tri_mask]].reshape(-1).astype(np.uint32)
    parts.append(sub)
  return parts


def transform(pr, yaw180: bool, shift: np.ndarray):
  """Rotate 180 degrees about Z (x, y -> -x, -y) so the car faces +Y, then translate by `shift` (cm)."""
  p = pr["pos"].copy()
  n = pr["nrm"].copy() if pr["nrm"] is not None else None
  if yaw180:
    p[:, 0] *= -1
    p[:, 1] *= -1
    if n is not None:
      n[:, 0] *= -1
      n[:, 1] *= -1
  p += shift.astype(np.float32)
  out = dict(pr)
  out["pos"], out["nrm"] = p, n
  return out


def bbox(prims):
  allp = np.vstack([p["pos"] for p in prims])
  return allp.min(0), allp.max(0)


# ------------------------------------------------------------------------------------------------ write
class GltfWriter:
  def __init__(self, g_src, root_matrix, textures_rel: str):
    self.src = g_src
    self.bin = bytearray()
    self.g = {
      "asset": {"version": "2.0", "generator": "LionDriver corolla_e210_gltf_export.py (no decimation)"},
      "scene": 0, "scenes": [{"nodes": [0]}],
      "nodes": [{"name": "root", "matrix": root_matrix, "children": []}],
      "meshes": [], "accessors": [], "bufferViews": [], "buffers": [],
      "materials": g_src.get("materials", []), "textures": g_src.get("textures", []),
      "images": [{"uri": f"{textures_rel}/image_{i}.png", "mimeType": "image/png"} for i in range(len(g_src.get("images", [])))],
    }
    if "samplers" in g_src:
      self.g["samplers"] = g_src["samplers"]
    if "extensionsUsed" in g_src:
      self.g["extensionsUsed"] = g_src["extensionsUsed"]

  def _view(self, arr: np.ndarray, target: int) -> int:
    data = np.ascontiguousarray(arr).tobytes()
    while len(self.bin) % 4:
      self.bin.append(0)
    self.g["bufferViews"].append({"buffer": 0, "byteOffset": len(self.bin), "byteLength": len(data), "target": target})
    self.bin += data
    return len(self.g["bufferViews"]) - 1

  def _acc(self, arr: np.ndarray, ctype: int, atype: str, target: int, minmax=False) -> int:
    v = self._view(arr, target)
    a = {"bufferView": v, "componentType": ctype, "count": int(arr.shape[0]), "type": atype}
    if minmax:
      a["min"] = [float(x) for x in arr.min(0)]
      a["max"] = [float(x) for x in arr.max(0)]
    self.g["accessors"].append(a)
    return len(self.g["accessors"]) - 1

  def add_mesh(self, name: str, prims, parent: int = 0, translation=None) -> int:
    mprims = []
    for pr in prims:
      at = {"POSITION": self._acc(pr["pos"], 5126, "VEC3", 34962, True)}
      if pr["nrm"] is not None:
        at["NORMAL"] = self._acc(pr["nrm"], 5126, "VEC3", 34962)
      if pr["uv"] is not None:
        at["TEXCOORD_0"] = self._acc(pr["uv"], 5126, "VEC2", 34962)
      d = {"attributes": at, "mode": 4}
      if pr["idx"] is not None:
        d["indices"] = self._acc(pr["idx"].reshape(-1, 1), 5125, "SCALAR", 34963)
      if pr["material"] is not None:
        d["material"] = pr["material"]
      mprims.append(d)
    self.g["meshes"].append({"name": name, "primitives": mprims})
    node = {"name": name, "mesh": len(self.g["meshes"]) - 1}
    if translation is not None:
      node["translation"] = [float(x) for x in translation]
    self.g["nodes"].append(node)
    ni = len(self.g["nodes"]) - 1
    self.g["nodes"][parent].setdefault("children", []).append(ni)
    return ni

  def add_empty(self, name: str, translation, parent: int = 0) -> int:
    self.g["nodes"].append({"name": name, "translation": [float(x) for x in translation], "children": []})
    ni = len(self.g["nodes"]) - 1
    self.g["nodes"][parent].setdefault("children", []).append(ni)
    return ni

  def write(self, path: Path):
    binname = path.with_suffix(".bin").name
    self.g["buffers"] = [{"uri": binname, "byteLength": len(self.bin)}]
    path.with_suffix(".bin").write_bytes(bytes(self.bin))
    path.write_text(json.dumps(self.g, separators=(",", ":")), encoding="utf-8", newline="\n")
    tris = sum(self.g["accessors"][p["indices"]]["count"] // 3 for m in self.g["meshes"] for p in m["primitives"] if "indices" in p)
    log(f"wrote {path.name} ({len(self.g['meshes'])} meshes, {tris:,} triangles, {len(self.bin) / 1e6:.1f} MB bin)")
    return tris


def write_textures(g, buf, out_dir: Path):
  tdir = out_dir / "textures"
  tdir.mkdir(parents=True, exist_ok=True)
  for i, im in enumerate(g.get("images", [])):
    bv = g["bufferViews"][im["bufferView"]]
    data = buf[bv.get("byteOffset", 0): bv.get("byteOffset", 0) + bv["byteLength"]]
    (tdir / f"image_{i}.png").write_bytes(data)
  log(f"wrote {len(g.get('images', []))} textures to {tdir.name}/")


def write_checksums(out_dir: Path):
  lines = []
  for p in sorted(out_dir.rglob("*")):
    if p.is_file() and p.name != "SHA256SUMS":
      lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out_dir).as_posix()}")
  (out_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
  log(f"wrote SHA256SUMS ({len(lines)} files)")


# ------------------------------------------------------------------------------------------------ main
def main(argv=None) -> int:
  ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
  ap.add_argument("--glb", required=True, help="the delivered 1450755-gltf-extended.glb")
  ap.add_argument("--output-dir", required=True, help="folder for vehicle.gltf and friends (git-ignored)")
  args = ap.parse_args(argv)
  glb, out_dir = Path(args.glb), Path(args.output_dir)
  out_dir.mkdir(parents=True, exist_ok=True)

  g, buf = read_glb(glb)
  roots = g["scenes"][g.get("scene", 0)]["nodes"]
  root = g["nodes"][roots[0]]
  root_matrix = root.get("matrix")
  if root_matrix is None:
    # no matrix on the root: build one from its TRS, or identity
    root_matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
  log(f"root node {root.get('name')!r} carries the unit/axis matrix; child geometry is read as delivered (cm, Z up, front -Y)")
  byname = {}
  for n in g["nodes"]:
    if "mesh" in n:
      byname[n.get("name")] = primitives(g, buf, n["mesh"])

  # 1. which end is the front: the tail lamps (material glass_red) mark the rear; mesh names are not trusted
  #    (in the delivered file the pair named "wheels_forward" sits at the rear)
  mats = g.get("materials", [])
  red = [i for i, m in enumerate(mats) if m.get("name") == "glass_red"]
  red_y = np.vstack([pr["pos"] for prims in byname.values() for pr in prims if pr["material"] in red])[:, 1].mean()
  centre_y0 = np.vstack([pr["pos"] for prims in byname.values() for pr in prims])[:, 1].mean()
  rear_sign = 1.0 if red_y > centre_y0 else -1.0
  log(f"tail lamps at y {'+' if rear_sign > 0 else '-'}: the car faces {'-' if rear_sign > 0 else '+'}Y in the file")
  if rear_sign < 0:
    raise SystemExit("the car faces +Y in this file; the yaw below assumes -Y. Re-check the receipt and adjust.")

  # 2. wheel parts by position: side from x, end from y against the car's middle; fused meshes split by connectivity
  groups = {k: {"rim": [], "tyre": [], "disc": []} for k in ("front_L", "front_R", "rear_L", "rear_R")}
  for name, kind in {**FRONT_FUSED, **REAR}.items():
    for pr in byname[name]:
      parts = connected_components(pr) if name in FRONT_FUSED else [pr]
      for part in parts:
        side = "L" if part["pos"][:, 0].mean() > 0 else "R"          # +x is the car's left when it faces -Y
        end = "rear" if (part["pos"][:, 1].mean() - centre_y0) * rear_sign > 0 else "front"
        groups[f"{end}_{side}"][kind].append(part)
  log("wheel parts: " + ", ".join(f"{k} rim {len(v['rim'])}/tyre {len(v['tyre'])}/disc {len(v['disc'])}" for k, v in groups.items()))
  front = {"L": groups["front_L"], "R": groups["front_R"]}
  rear = {"L": groups["rear_L"], "R": groups["rear_R"]}

  # 3. hub centres (tyre bounding boxes), tyre radius and width, in the file frame (cm)
  def hub(group):
    lo, hi = bbox(group["tyre"])
    return (lo + hi) / 2, (hi[2] - lo[2]) / 2, hi[0] - lo[0]
  hubs = {f"{end}_{side}": hub(grp[side]) for end, grp in (("front", front), ("rear", rear)) for side in ("L", "R")}
  r_tire = float(np.mean([h[1] for h in hubs.values()])) / 100
  w_tire = float(np.mean([h[2] for h in hubs.values()])) / 100
  ground_z = min(h[0][2] - h[1] for h in hubs.values())

  # 4. body meshes: everything except wheels, interior and the underbody detail
  wheel_names = set(FRONT_FUSED) | set(REAR)
  body_names = [n for n in byname if n not in wheel_names and n not in INTERIOR and n not in UNDERBODY]
  body_prims = [p for n in body_names for p in byname[n]]
  blo, bhi = bbox(body_prims)
  centre = (blo + bhi) / 2
  log(f"body box (cm): {np.round(blo, 1)} .. {np.round(bhi, 1)}; dropped {sorted(INTERIOR & set(byname))} and {sorted(UNDERBODY & set(byname))}")

  # 5. frame: yaw 180 so the car faces +Y, body centre to x = y = 0, ground to z = 0  (all in cm, before the root matrix)
  shift = np.array([centre[0], centre[1], -ground_z], dtype=np.float32)   # the yaw maps centre to -centre; add it back
  def to_vehicle(p):
    return transform(p, True, shift)
  def hub_vehicle(h):
    c = h[0].copy()
    c[0] *= -1
    c[1] *= -1
    return c + shift

  textures_rel = "textures"
  write_textures(g, buf, out_dir)

  # vehicle.gltf: body only
  wv = GltfWriter(g, root_matrix, textures_rel)
  for n in body_names:
    wv.add_mesh(n, [to_vehicle(p) for p in byname[n]])
  body_tris = wv.write(out_dir / "vehicle.gltf")

  # right wheels: right is -x in the file (car faces -y), which the yaw turns into +x, MetaDrive's right
  counts = {}
  for fname, group, key in (("right_tire_front.gltf", front["R"], "front_R"), ("right_tire_back.gltf", rear["R"], "rear_R")):
    ww = GltfWriter(g, root_matrix, textures_rel)
    hc = hub_vehicle(hubs[key])
    for kind in ("rim", "tyre", "disc"):
      prims = [transform(p, True, shift - hc) for p in group[kind]]
      if prims:
        ww.add_mesh(f"{key}_{kind}", prims)
    counts[fname] = ww.write(out_dir / fname)

  # vehicle_full.gltf: body plus the four wheels under hub nodes (figures, load tests)
  wf = GltfWriter(g, root_matrix, textures_rel)
  for n in body_names:
    wf.add_mesh(n, [to_vehicle(p) for p in byname[n]])
  for key, grp in (("front_L", front["L"]), ("front_R", front["R"]), ("rear_L", rear["L"]), ("rear_R", rear["R"])):
    hc = hub_vehicle(hubs[key])
    e = wf.add_empty(f"hub_{key}", hc)
    for kind in ("rim", "tyre", "disc"):
      prims = [transform(p, True, shift - hc) for p in grp[kind]]
      if prims:
        wf.add_mesh(f"{key}_{kind}", prims, parent=e)
  full_tris = wf.write(out_dir / "vehicle_full.gltf")

  # geometry.json (metres, vehicle frame: origin at the body centre on the ground, +Y forward, +X right)
  hv = {k: hub_vehicle(v) / 100 for k, v in hubs.items()}
  geom = {
    "source": f"corolla_e210_gltf_export.py from {glb.name}, no decimation",
    "front_wheelbase": round(float(hv["front_R"][1]), 4),
    "rear_wheelbase": round(float(-hv["rear_R"][1]), 4),
    "lateral_tire_to_center": round(float(abs(hv["front_R"][0])), 4),
    "tire_radius": round(r_tire, 4),
    "tire_width": round(w_tire, 4),
    "hub_height": round(float(hv["front_R"][2]), 4),
    "body_box_m": {"min": [round(float(v) / 100, 4) for v in (blo - centre)], "max": [round(float(v) / 100, 4) for v in (bhi - centre)],
                   "note": "relative to the body centre before the ground shift; z of the ground is -hub_height - tire_radius"},
    "triangles": {"vehicle": body_tris, **counts, "vehicle_full": full_tris},
    "dropped_meshes": sorted((INTERIOR | UNDERBODY) & set(byname)),
  }
  (out_dir / "geometry.json").write_text(json.dumps(geom, indent=2) + "\n", encoding="utf-8", newline="\n")
  log(f"geometry: front {geom['front_wheelbase']} m, rear {geom['rear_wheelbase']} m, lateral {geom['lateral_tire_to_center']} m, "
      f"tyre r {geom['tire_radius']} m w {geom['tire_width']} m")
  write_checksums(out_dir)
  return 0


if __name__ == "__main__":
  sys.exit(main())
