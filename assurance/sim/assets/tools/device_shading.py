#!/usr/bin/env python3
"""How much of the comma device's windshield-side face the sun reaches through the Corolla, by direction (physics plan
study 6, TC-21, DFI-04).

Rays from points on the device's face toward each sun direction in the car's frame are cast through the purchased mesh
(Möller–Trumbore): a ray that hits an opaque part is shaded; one that passes only glass reaches the face, and the
glass it crossed is recorded (windshield, roof glass or side glass), so the study can apply each glass's transmittance.
The mesh has a glass roof panel and the reference car may not, so a second table treats the roof panel as metal.

Writes `assurance/sim/figures/corolla-e210-device-shading.json`: derived numbers only, labelled mesh-derived; the mesh
itself stays out of git (assurance/sim/assets/README.md). The device's place on the windshield is an estimate until T1
measures it (`weather/params.yaml`, `device_sun:`).

    python3 assurance/sim/assets/tools/device_shading.py            # needs assets/1450755-gltf-extended.glb
    python3 assurance/sim/assets/tools/device_shading.py --check    # CI without the model: the table is well formed

Frame: x forward, y up, z left (as `vehicle_geometry.py`). A direction is (elevation above the car's horizontal plane,
relative azimuth clockwise from straight ahead, so +90° is the car's right). Synthetic (DSR-12), design aid, no
evidence credit.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[1]
OUT = SIM / "figures" / "corolla-e210-device-shading.json"
PARAMS = SIM / "weather" / "params.yaml"
GLASS = ("windows", "window_1", "window_2", "window_3", "window_4")
EPS = 1e-3          # m: hits closer than this to the face are the face's own surroundings, not a shadow


def direction(elev_deg, relaz_deg):
  """Unit vectors in the car frame for elevation and relative azimuth (clockwise from ahead), broadcast."""
  e, a = np.radians(elev_deg), np.radians(relaz_deg)
  return np.stack(np.broadcast_arrays(np.cos(e) * np.cos(a), np.sin(e), -np.cos(e) * np.sin(a)), axis=-1)


def hits(origin: np.ndarray, dirs: np.ndarray, tris: np.ndarray, chunk: int = 4096) -> np.ndarray:
  """For one origin and D directions: does each ray hit any of the T triangles (Möller–Trumbore, t > EPS)?"""
  hit = np.zeros(len(dirs), bool)
  for i in range(0, len(tris), chunk):
    t = tris[i:i + chunk]
    e1, e2 = t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]                 # (C, 3)
    s = origin - t[:, 0]                                            # (C, 3)
    q = np.cross(s, e1)                                             # (C, 3)
    pv = np.cross(dirs[:, None, :], e2[None, :, :])                 # (D, C, 3)
    det = np.einsum("dcj,cj->dc", pv, e1)
    with np.errstate(divide="ignore", invalid="ignore"):
      inv = 1.0 / det
      u = np.einsum("dcj,cj->dc", pv, s) * inv
      v = np.einsum("dj,cj->dc", dirs, q) * inv
      tt = np.einsum("cj,cj->c", e2, q)[None, :] * inv
      ok = (np.abs(det) > 1e-12) & (u >= 0) & (v >= 0) & (u + v <= 1) & (tt > EPS)
    hit |= ok.any(axis=1)
  return hit


def ahead_above(tris: np.ndarray, origin: np.ndarray, normal: np.ndarray) -> np.ndarray:
  """Triangles that could shade a direction with elevation >= 0 in front of the face: some vertex is above the
  origin and some vertex is in front of the face's plane (a superset, so pruning never loses a shadow)."""
  rel = tris - origin
  return tris[(rel[..., 1].max(1) > 0) & ((rel @ normal).max(1) > 0)]


FACES = {"front": [1.0, 0.0, 0.0], "screen": [-1.0, 0.0, 0.0], "left": [0.0, 0.0, 1.0], "right": [0.0, 0.0, -1.0]}
GLASS_CODE = {"windshield": 1, "roof_glass": 2, "side": 3, "rear": 4}


def device_box(d: dict, windshield: dict) -> tuple[np.ndarray, np.ndarray]:
  """The device's box (low and high corners) from the mount's place on the glass (params `device_sun`): it hangs
  under the pad, upright, its windshield-side face ("front") facing forward just behind the glass."""
  top = np.array(windshield["top_centre"], float)
  tilt = math.radians(windshield["tilt_deg"])
  down = np.array([math.cos(tilt), -math.sin(tilt), 0.0])           # down the glass, toward the hood
  pad = top + d["mount_down_glass_m"]["value"] * down
  w, h, depth = d["box_m"]["value"]
  y_top = pad[1] - d["mount_drop_m"]["value"]
  x_front = pad[0] - d["mount_drop_m"]["value"] / math.tan(tilt) - d["gap_m"]["value"]
  z = d["lateral_m"]["value"]
  return np.array([x_front - depth, y_top - h, z - w / 2]), np.array([x_front, y_top, z + w / 2])


def face_points(lo: np.ndarray, hi: np.ndarray, face: str, n: tuple) -> np.ndarray:
  """A grid of n[0] x n[1] points on one face of the box, inset from its edges."""
  nrm = np.array(FACES[face])
  ax = int(np.argmax(np.abs(nrm)))
  fixed = hi[ax] if nrm[ax] > 0 else lo[ax]
  others = [i for i in range(3) if i != ax and i != 1]
  a = others[0]
  ua = lo[a] + (hi[a] - lo[a]) * np.linspace(0.1, 0.9, n[0])
  uy = lo[1] + (hi[1] - lo[1]) * np.linspace(0.1, 0.9, n[1])
  pts = []
  for y in uy:
    for u in ua:
      q = np.zeros(3); q[ax] = fixed; q[a] = u; q[1] = y
      pts.append(q)
  return np.array(pts)


def table(parts: dict, d: dict, windshield: dict, elev: np.ndarray, relaz: np.ndarray) -> dict:
  """Per face and roof case: the lit fraction of the face's points per direction, and the glass the light came
  through (GLASS_CODE; 0 where none is lit)."""
  w = parts["windows"]
  cx = w.mean(1)[:, 0]
  glass = {"windshield": w[cx > 0.6], "roof_glass": w[(cx <= 0.6) & (cx >= -1.0)],
           "side": np.concatenate([parts[k] for k in GLASS[1:]]), "rear": w[cx < -1.0]}
  opaque = np.concatenate([t for k, t in parts.items() if k not in GLASS])
  lo, hi = device_box(d, windshield)
  E, A = np.meshgrid(elev, relaz, indexing="ij")
  dirs = direction(E, A).reshape(-1, 3)
  out = {}
  for case in ("glass_roof", "metal_roof"):
    occl = opaque if case == "glass_roof" else np.concatenate([opaque, glass["roof_glass"]])
    out[case] = {}
    for face, nrm in FACES.items():
      nrm = np.array(nrm)
      pts = face_points(lo, hi, face, (d["points"]["across"], d["points"]["up"]))
      front = np.where(dirs @ nrm > 1e-9)[0]
      dd = dirs[front]
      lit = np.zeros(len(dirs))
      votes = np.zeros((len(dirs), len(GLASS_CODE) + 1))
      for p in pts:
        rest = ~hits(p, dd, ahead_above(occl, p, nrm))
        lit[front[rest]] += 1.0 / len(pts)
        # a lit ray is put to the first-listed glass it crosses
        for k, code in GLASS_CODE.items():
          if case == "metal_roof" and k == "roof_glass":
            continue
          sel = rest & hits(p, dd, ahead_above(glass[k], p, nrm))
          votes[front[sel], code] += 1
          rest &= ~sel
        if rest.any():
          raise SystemExit(f"{face}: a ray leaves the car through no glass at {dd[rest][0]}: check the mesh parts")
      via = np.where(lit > 0, votes.argmax(1), 0)
      out[case][face] = {"lit": np.round(lit.reshape(E.shape), 3).tolist(), "glass": via.reshape(E.shape).tolist()}
  return {"box": {"lo": np.round(lo, 4).tolist(), "hi": np.round(hi, 4).tolist()}, "faces": FACES,
          "glass_code": GLASS_CODE, "cases": out}


def windshield_line(parts: dict) -> dict:
  """The windshield's top edge on the device's line and its rake, from the mesh."""
  w = parts["windows"]
  ws = w[w.mean(1)[:, 0] > 0.6].reshape(-1, 3)
  near = ws[np.abs(ws[:, 2]) < 0.05]
  top = near[np.argmax(near[:, 1])]
  lo = near[np.argmin(near[:, 1])]
  return {"top_centre": [round(float(top[0]), 4), round(float(top[1]), 4), 0.0],
          "tilt_deg": round(math.degrees(math.atan2(top[1] - lo[1], lo[0] - top[0])), 2)}


def check(t: dict) -> list[str]:
  errs = []
  E, A = np.array(t["elev_deg"]), np.array(t["relaz_deg"])
  dirs = direction(*np.meshgrid(E, A, indexing="ij"))
  for case, faces in t["cases"].items():
    for face, f in faces.items():
      lit, via = np.array(f["lit"]), np.array(f["glass"])
      if lit.shape != (len(E), len(A)) or via.shape != lit.shape:
        errs.append(f"{case} {face}: table shape {lit.shape}")
        continue
      if lit.min() < 0 or lit.max() > 1 + 1e-9:
        errs.append(f"{case} {face}: a lit fraction is outside 0..1")
      if lit[dirs @ np.array(t["faces"][face]) <= 1e-9].max() > 0:
        errs.append(f"{case} {face}: lit from behind the face")
      if ((lit > 0) != (via > 0)).any():
        errs.append(f"{case} {face}: a lit direction without its glass")
  return errs


def main(argv):
  if "--check" in argv:
    errs = check(json.loads(OUT.read_text(encoding="utf-8")))
    for e in errs:
      print("FAIL", e)
    print("device shading:", "OK" if not errs else f"{len(errs)} problem(s)")
    return 1 if errs else 0
  sys.path.insert(0, str(HERE))
  import vehicle_geometry as vg
  if not vg.GLB.is_file():
    print(f"{vg.GLB} not found: the licensed model is in the private assets repository (assets/README.md)")
    return 1
  d = yaml.safe_load(PARAMS.read_text(encoding="utf-8"))["device_sun"]
  parts = vg.load()
  ws = windshield_line(parts)
  g = d["grid"]
  elev = np.arange(0.0, 90.0 + 1e-9, g["elev_step_deg"])
  relaz = np.arange(-180.0, 180.0 + 1e-9, g["relaz_step_deg"])
  t = {"source": f"3d_molier Toyota Corolla 2020 (TurboSquid 1450755), sha256 {vg.SHA256}; cast by "
                 "assurance/sim/assets/tools/device_shading.py",
       "status": "mesh-derived: an artist's model; the device's place on the glass is an estimate until T1",
       "frame": "x forward, y up, z left; elevation above the car's horizontal plane, relative azimuth clockwise from ahead",
       "windshield": ws, "device": {k: d[k]["value"] for k in ("mount_down_glass_m", "mount_drop_m", "gap_m", "lateral_m", "box_m")},
       "elev_deg": elev.tolist(), "relaz_deg": relaz.tolist()}
  t |= table(parts, d, ws, elev, relaz)
  errs = check(t)
  if errs:
    print("\n".join(errs))
    return 1
  OUT.write_text(json.dumps(t, separators=(",", ":")) + "\n", encoding="utf-8")
  print("wrote", OUT.name, ws, {f"{c} {k}": round(float(np.mean(v["lit"])), 3) for c, fs in t["cases"].items() for k, v in fs.items()})
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
