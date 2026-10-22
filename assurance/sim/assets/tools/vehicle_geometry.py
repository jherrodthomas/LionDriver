#!/usr/bin/env python3
"""Corolla E210 geometry for the physics models, measured on the purchased mesh: glass areas and rakes, and a side
elevation (body, each window, wheels) as polygons in metres.

Writes `assurance/sim/figures/corolla-e210-geometry.json`. Numbers and outlines derived from the model are rendered
output and may be published; the model files may not (assurance/sim/assets/README.md). The mesh is an artist's model,
so every value is labelled mesh-derived: good to a few per cent for shape, not a source for vehicle facts
(vehicle-3d-model.md §1); the reference car's measurement wins where they differ.

    python3 assurance/sim/assets/tools/vehicle_geometry.py            # needs assets/1450755-gltf-extended.glb
    python3 assurance/sim/assets/tools/vehicle_geometry.py --check    # CI without the model: the JSON is well formed

Frame of the output: x along the car (+ forward, 0 at mid-length), y up (0 at the ground), z to the left.
"""

from __future__ import annotations

import io
import json
import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[1]
GLB = SIM / "assets" / "1450755-gltf-extended.glb"
OUT = SIM / "figures" / "corolla-e210-geometry.json"
SHA256 = "1dc000e51624482d7c27eafacfe858b87e5cd12a5524cc2431717b62ff028216"
CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
RES = 0.005   # m per pixel of the side elevation raster
OPAQUE_SKIP = ("interier", "glass", "window", "felt", "steering", "wiper", "lenses", "schilds")
WHEEL = ("wheel", "tire", "brake")


def load(path: Path = GLB) -> dict:
  """Triangles of every named node, in metres, in the output frame."""
  with path.open("rb") as f:
    f.read(12)
    cl, _ = struct.unpack("<II", f.read(8))
    g = json.loads(f.read(cl))
    bl, _ = struct.unpack("<II", f.read(8))
    blob = f.read(bl)

  def acc(i):
    a = g["accessors"][i]
    v = g["bufferViews"][a["bufferView"]]
    off = v.get("byteOffset", 0) + a.get("byteOffset", 0)
    n, dt = NC[a["type"]], np.dtype(CT[a["componentType"]])
    stride = v.get("byteStride", 0)
    if stride and stride != n * dt.itemsize:
      raw = np.frombuffer(blob, dtype=np.uint8, count=stride * a["count"], offset=off).reshape(a["count"], stride)
      return np.frombuffer(raw[:, : n * dt.itemsize].tobytes(), dtype=dt).reshape(a["count"], n)
    return np.frombuffer(blob, dtype=dt, count=a["count"] * n, offset=off).reshape(a["count"], n)

  def mat(node):
    return np.array(node.get("matrix", np.eye(4).flatten(order="F").tolist()), float).reshape(4, 4, order="F")

  root = mat(g["nodes"][0]) @ mat(g["nodes"][1])
  # glTF frame after the root: x right, y up, z forward (the front doors sit ahead of the rear doors at +z)
  to_out = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)   # out x = forward, y = up, z = left
  parts = {}
  for node in g["nodes"][2:]:
    T = root @ mat(node)
    tris = []
    for pr in g["meshes"][node["mesh"]]["primitives"]:
      pos = acc(pr["attributes"]["POSITION"]).astype(float)
      idx = acc(pr["indices"]).reshape(-1, 3)
      pw = (np.c_[pos, np.ones(len(pos))] @ T.T)[:, :3] @ to_out.T
      tris.append(pw[idx])
    parts[node["name"]] = np.concatenate(tris)
  return parts


def surface(t: np.ndarray) -> dict:
  """One side of a thin glass part (the mesh models both faces), its plane's tilt from horizontal and its facing."""
  n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
  area = 0.5 * np.linalg.norm(n, axis=1).sum() / 2
  v = t.reshape(-1, 3)
  _, _, vt = np.linalg.svd(v - v.mean(0))
  nrm = vt[2] if vt[2][1] >= 0 else -vt[2]
  return {"area_m2": round(float(area), 3), "tilt_from_horizontal_deg": round(float(np.degrees(np.arccos(abs(nrm[1])))), 1),
          "normal": [round(float(x), 3) for x in nrm], "x_range_m": [round(float(v[:, 0].min()), 3), round(float(v[:, 0].max()), 3)],
          "y_range_m": [round(float(v[:, 1].min()), 3), round(float(v[:, 1].max()), 3)]}


def outline(tris_list, x0, y0, nx, ny):
  """Side elevation of triangles (x, y): raster them, then trace the boundary; the largest closed polygons, in metres."""
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  from matplotlib.collections import PolyCollection
  fig = plt.figure(figsize=(nx / 100, ny / 100), dpi=100)
  ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(x0, x0 + nx * RES); ax.set_ylim(y0, y0 + ny * RES); ax.axis("off")
  for t in tris_list:
    ax.add_collection(PolyCollection(t[:, :, :2], facecolors="k", edgecolors="k", linewidths=0.3, antialiased=False))
  buf = io.BytesIO(); fig.savefig(buf, format="raw", dpi=100); plt.close(fig)
  img = np.frombuffer(buf.getvalue(), dtype=np.uint8).reshape(ny, nx, 4)[::-1, :, 0] < 128
  import contourpy
  gen = contourpy.contour_generator(np.arange(nx) * RES + x0 + RES / 2, np.arange(ny) * RES + y0 + RES / 2,
                                    img.astype(float))
  polys = [p for p in gen.lines(0.5) if len(p) > 8]
  polys.sort(key=lambda p: -abs(_area(p)))
  return [[[round(float(x), 3), round(float(y), 3)] for x, y in p[:: max(1, len(p) // 400)]] for p in polys]


def _area(p):
  x, y = p[:, 0], p[:, 1]
  return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def build(parts: dict) -> dict:
  w = parts["windows"]
  cx = w.mean(1)[:, 0]
  glass = {
    "windshield": surface(w[cx > 0.6]),
    "rear_window": surface(w[cx < -1.0]),
    "roof_glass": surface(w[(cx <= 0.6) & (cx >= -1.0)]),
    "side_front_each": surface(parts["window_1"]),
    "side_rear_each": surface(parts["window_2"]),
  }
  allv = np.concatenate([t.reshape(-1, 3) for t in parts.values()])
  lo, hi = allv.min(0), allv.max(0)
  x0, y0 = float(lo[0]) - 0.05, -0.02
  nx, ny = int((hi[0] - lo[0] + 0.1) / RES), int((hi[1] + 0.05) / RES)
  opaque = [t for k, t in parts.items() if not any(s in k for s in OPAQUE_SKIP + WHEEL)]
  wheels = [t for k, t in parts.items() if any(s in k for s in WHEEL)]
  left = lambda t: t[t.mean(1)[:, 2] > 0]  # noqa: E731  (the car's left side, facing the viewer of the elevation)
  side = {
    "body": outline(opaque + wheels, x0, y0, nx, ny)[:1],
    "wheels": outline([left(t) for t in wheels], x0, y0, nx, ny)[:2],
    "windshield": outline([w[cx > 0.6]], x0, y0, nx, ny)[:1],
    "rear_window": outline([w[cx < -1.0]], x0, y0, nx, ny)[:1],
    "side_front": outline([left(parts["window_3"])], x0, y0, nx, ny)[:1],
    "side_rear": outline([left(parts["window_4"])], x0, y0, nx, ny)[:1],
  }
  # front elevation (z, y): everything outside the cabin; the frontal area includes the mirrors, as published data do
  front = [t[:, :, [2, 1, 0]] for name, t in parts.items() if not any(k in name for k in ("interier", "felt", "steering"))]
  zlo, zhi = float(lo[2]) - 0.05, float(hi[2]) + 0.05
  front_poly = outline(front, zlo, y0, int((zhi - zlo) / RES), ny)[:1]
  frontal = abs(_area(np.array(front_poly[0]))) if front_poly else 0.0
  b = parts["body"]
  n = np.cross(b[:, 1] - b[:, 0], b[:, 2] - b[:, 0])
  a = 0.5 * np.linalg.norm(n, axis=1)
  u = n / np.maximum(2 * a, 1e-12)[:, None]
  roof = (b.mean(1)[:, 1] > 1.35) & (u[:, 1] > 0.9)
  body_px = np.array(side["body"][0]) if side["body"] else np.zeros((3, 2))
  return {
    "source": "3d_molier Toyota Corolla 2020 Simple Interior (TurboSquid 1450755), 1450755-gltf-extended.glb, sha256 "
              + SHA256 + "; measured by assurance/sim/assets/tools/vehicle_geometry.py",
    "status": "mesh-derived: an artist's model, good to a few per cent for shape; the reference car's measurement wins",
    "frame": "x forward (0 at mid-length), y up (0 at the ground), z left; metres",
    "extent_m": {"length": round(float(hi[0] - lo[0]), 3), "width": round(float(hi[2] - lo[2]), 3),
                 "height": round(float(hi[1]), 3)},
    "glass": glass,
    "glass_note": "Areas are one face of each part (the mesh models both). The mesh has a glass roof panel; the reference car may not.",
    "roof_metal_up_m2": round(float(a[roof].sum()), 3),
    "frontal_area_m2": round(float(frontal), 3),
    "side_projected_area_m2": round(abs(_area(body_px)), 3),
    "side_centroid_m": [round(float(v), 3) for v in _centroid(body_px)],
    "side_elevation": side,
  }


def _centroid(p):
  x, y = p[:, 0], p[:, 1]
  cr = x * np.roll(y, -1) - np.roll(x, -1) * y
  A = cr.sum() / 2
  return [float(((x + np.roll(x, -1)) * cr).sum() / (6 * A)), float(((y + np.roll(y, -1)) * cr).sum() / (6 * A))]


def check(d: dict) -> list[str]:
  errs = []
  for k in ("windshield", "rear_window", "side_front_each", "side_rear_each"):
    g = d["glass"][k]
    if not 0.2 < g["area_m2"] < 2.0:
      errs.append(f"{k} area {g['area_m2']} out of range")
  if not 15 < d["glass"]["windshield"]["tilt_from_horizontal_deg"] < 45:
    errs.append("windshield tilt out of range")
  if not 4.4 < d["extent_m"]["length"] < 4.8:
    errs.append("length is not a Corolla's")
  for k in ("body", "windshield", "rear_window", "side_front", "side_rear", "wheels"):
    if not d["side_elevation"].get(k):
      errs.append(f"side elevation {k} missing")
  return errs


def main(argv):
  if "--check" in argv:
    errs = check(json.loads(OUT.read_text(encoding="utf-8")))
    for e in errs:
      print("FAIL", e)
    print("vehicle geometry:", "OK" if not errs else f"{len(errs)} problem(s)")
    return 1 if errs else 0
  if not GLB.is_file():
    print(f"{GLB} not found: the licensed model is in the private assets repository (assets/README.md)")
    return 1
  d = build(load())
  errs = check(d)
  if errs:
    print("\n".join(errs))
    return 1
  OUT.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
  print("wrote", OUT.name, json.dumps({k: (v["area_m2"], v["tilt_from_horizontal_deg"]) for k, v in d["glass"].items()}),
        "side area", d["side_projected_area_m2"])
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
