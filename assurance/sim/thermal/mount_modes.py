#!/usr/bin/env python3
"""The mount's vibration modes and the road camera's jitter (physics plan study 7; WP-C-06 TC-19, WP-V-03 KS-16,
WP-H-07 QE-08).

The comma device hangs from its mount, which an adhesive foam pad holds to the windshield. Linear elasticity in
FEniCSx (DOLFINx 0.10, quadratic hexahedra) on the pad, the mount and the device as blocks (`params.yaml`,
`vibration:`) in the pad's frame, fixed where the pad meets the glass; SLEPc finds the lowest modes (shift and invert). Each mode's
rotation of the device is the mean of half the curl of its shape over the device.

The road shakes the car's body through its suspension: ISO 8608 roads of class A and B at 110 km/h through a
quarter-car give the body's vertical acceleration. The mount's modes, driven by that acceleration at their base,
turn the device relative to the car; with the road camera's focal length from openpilot's `camera.py` that is the
jitter in pixels. The wheel and engine orders are compared with the mode frequencies. Writes `../results/mount-modes.json`
and `.md`.

    python3 mount_modes.py --figures
    python3 mount_modes.py --check

Not modelled: the windshield's and the roof's own panel modes (the glass is a rigid base); the device's real hang
(it stands off the glass square to it here); fore-aft and lateral body motion; the engine's shaking (only its
frequencies); the pad's frequency- and temperature-dependence beyond its band; the hinge's play. Every size and material
is an estimate until T1. Runs in the environment of `thermal-linux-64.lock`.
Synthetic (DSR-12), design aid, no evidence credit (DQ-413).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import basix.ufl
import numpy as np
import ufl
import yaml
from dolfinx import fem, mesh
from dolfinx.fem import petsc as fpetsc
from mpi4py import MPI
from petsc4py import PETSc
from slepc4py import SLEPc

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CAMERA = ROOT / "openpilot" / "common" / "transformations" / "camera.py"
OUT_JSON = HERE.parent / "results" / "mount-modes.json"
OUT_MD = HERE.parent / "results" / "mount-modes.md"
REFINE = (1.0, 1.5, 2.0)        # the mesh study: the coarse mesh and two finer ones
REL_TOL = 0.01                  # --check: a fresh run within 1 % of the committed results


def focal_px() -> float:
  """The road camera's focal length in pixels (comma 3X, AR0231/OX03C10) from camera.py."""
  m = re.search(r"_ar_ox_config = DeviceCameraConfig\(CameraConfig\((\d+), (\d+), ([\d.]+)\)",
                CAMERA.read_text(encoding="utf-8"))
  if not m:
    raise SystemExit(f"road camera intrinsics not found in {CAMERA}")
  return float(m.group(3))


def grid_lines(lo: float, hi: float, cuts: list, step: float, min_cells: dict) -> np.ndarray:
  """Grid lines through every block boundary, no wider apart than `step`; a thin layer gets at least its minimum."""
  b = sorted(set(round(c, 9) for c in cuts if lo - 1e-12 <= c <= hi + 1e-12))
  out = [b[0]]
  for a, c in zip(b[:-1], b[1:], strict=True):
    n = max(int(math.ceil((c - a) / step - 1e-9)), min_cells.get((a, c), 1))
    out += list(np.linspace(a, c, n + 1)[1:])
  return np.array(out)


def block_mesh(blocks: dict, cells_per_m: float, refine: float = 1.0):
  """A hexahedral mesh of the union of axis-aligned blocks on one tensor grid; cell tags number the blocks."""
  names = list(blocks)
  lo = np.array([blocks[k]["lo"] for k in names])
  hi = np.array([blocks[k]["hi"] for k in names])
  step = 1.0 / (cells_per_m * refine)
  axes = []
  for ax in range(3):
    cuts = list(lo[:, ax]) + list(hi[:, ax])
    thin = {}
    if ax == 1:      # through the thickness of the pad: at least two cells, more as the mesh refines
      thin = {(round(lo[i, 1], 9), round(hi[i, 1], 9)): int(math.ceil(2 * refine)) for i in range(len(names))}
    axes.append(grid_lines(min(cuts), max(cuts), cuts, step, thin))
  X, Y, Z = axes
  nx, ny, nz = len(X), len(Y), len(Z)
  cx, cy, cz = (X[:-1] + X[1:]) / 2, (Y[:-1] + Y[1:]) / 2, (Z[:-1] + Z[1:]) / 2
  I, J, K = np.meshgrid(np.arange(nx - 1), np.arange(ny - 1), np.arange(nz - 1), indexing="ij")
  I, J, K = I.ravel(), J.ravel(), K.ravel()
  tag = np.zeros(len(I), int)
  for b in range(len(names)):
    inside = ((cx[I] > lo[b, 0]) & (cx[I] < hi[b, 0]) & (cy[J] > lo[b, 1]) & (cy[J] < hi[b, 1])
              & (cz[K] > lo[b, 2]) & (cz[K] < hi[b, 2]))
    tag[inside] = b + 1
  keep = tag > 0
  I, J, K, tag = I[keep], J[keep], K[keep], tag[keep]
  vid = lambda i, j, k: (i * ny + j) * nz + k  # noqa: E731
  # DOLFINx hexahedron: tensor-product vertex order (x fastest, then y, then z)
  cells = np.stack([vid(I, J, K), vid(I + 1, J, K), vid(I, J + 1, K), vid(I + 1, J + 1, K),
                    vid(I, J, K + 1), vid(I + 1, J, K + 1), vid(I, J + 1, K + 1), vid(I + 1, J + 1, K + 1)], axis=1)
  used, inv = np.unique(cells, return_inverse=True)
  cells = inv.reshape(cells.shape).astype(np.int64)
  gi, gj, gk = used // (ny * nz), (used // nz) % ny, used % nz
  x = np.stack([X[gi], Y[gj], Z[gk]], axis=1)
  domain = ufl.Mesh(basix.ufl.element("Lagrange", "hexahedron", 1, shape=(3,)))
  msh = mesh.create_mesh(MPI.COMM_SELF, cells, domain, x)
  # the cells may be reordered: map the tags through the original cell index
  orig = msh.topology.original_cell_index
  ct = mesh.meshtags(msh, 3, np.arange(len(orig), dtype=np.int32), tag[orig].astype(np.int32))
  return msh, ct, names


def modes(blocks: dict, materials: dict, cells_per_m: float, nev: int, refine: float = 1.0, degree: int = 2,
          fixed=lambda x: np.isclose(x[1], 0.0), rotation_block: str = "device", keep: bool = False) -> dict:
  """The lowest `nev` modes: frequencies, effective masses for base motion along x, y, z, and each mode's rotation
  of `rotation_block` (rad per unit modal coordinate; modes mass-normalised)."""
  msh, ct, names = block_mesh(blocks, cells_per_m, refine)
  Q = fem.functionspace(msh, ("DG", 0))
  E, nu, rho = fem.Function(Q), fem.Function(Q), fem.Function(Q)
  for b, k in enumerate(names, start=1):
    c = ct.find(b)
    mat = materials[blocks[k]["material"]]
    E.x.array[c], nu.x.array[c], rho.x.array[c] = mat["E"], mat["nu"], mat["rho"]
  V = fem.functionspace(msh, ("Lagrange", degree, (3,)))
  u, v = ufl.TrialFunction(V), ufl.TestFunction(V)
  mu = E / (2 * (1 + nu))
  lmbda = E * nu / ((1 + nu) * (1 - 2 * nu))
  eps = lambda w: ufl.sym(ufl.grad(w))  # noqa: E731
  sigma = lambda w: 2 * mu * eps(w) + lmbda * ufl.tr(eps(w)) * ufl.Identity(3)  # noqa: E731
  dofs = fem.locate_dofs_geometrical(V, fixed)
  bc = fem.dirichletbc(np.zeros(3, dtype=PETSc.ScalarType), dofs, V)
  A = fpetsc.assemble_matrix(fem.form(ufl.inner(sigma(u), eps(v)) * ufl.dx), bcs=[bc], diag=1.0)
  A.assemble()
  M = fpetsc.assemble_matrix(fem.form(rho * ufl.inner(u, v) * ufl.dx), bcs=[bc], diag=0.0)
  M.assemble()
  es = SLEPc.EPS().create(MPI.COMM_SELF)
  es.setOperators(A, M)
  es.setProblemType(SLEPc.EPS.ProblemType.GHEP)
  es.setDimensions(nev)
  es.setWhichEigenpairs(SLEPc.EPS.Which.TARGET_MAGNITUDE)
  es.setTarget(0.0)
  st = es.getST()
  st.setType("sinvert")
  # a direct solve: MUMPS through PETSc, one process, ordered by METIS (Apache-2.0); one process never calls ParMETIS
  # (TL-53, TE-04 OI-4). PETSc's own LU and its multigrid were tried: too slow, as the soft, nearly incompressible pad
  # is ill-conditioned; MUMPS's AMD ordering runs out of memory on the finest mesh.
  ksp = st.getKSP()
  ksp.setType("preonly")
  pc = ksp.getPC()
  pc.setType("lu")
  pc.setFactorSolverType("mumps")
  PETSc.Options()["st_mat_mumps_icntl_7"] = 5    # METIS; read by the spectral transform's factor (prefix st_)
  es.setTolerances(1e-10, 200)
  es.setFromOptions()
  es.solve()
  if pc.getFactorMatrix().getMumpsIcntl(7) != 5:
    raise SystemExit("MUMPS did not take the METIS ordering")
  nconv = es.getConverged()
  if nconv < nev:
    raise SystemExit(f"SLEPc found {nconv} of {nev} modes")
  dx = ufl.Measure("dx", domain=msh, subdomain_data=ct)
  rb = names.index(rotation_block) + 1
  vol = fem.assemble_scalar(fem.form(fem.Constant(msh, 1.0) * dx(rb)))
  total_mass = fem.assemble_scalar(fem.form(rho * ufl.dx))
  phi = fem.Function(V)
  Mphi = M.createVecLeft()
  r = fem.Function(V)
  pairs = []
  for i in range(nconv):
    lam = es.getEigenpair(i, phi.x.petsc_vec)
    pairs.append((lam.real, i))
  pairs.sort()
  out = {"freq_hz": [], "gamma": [], "rotation": [], "dofs": V.dofmap.index_map.size_global * 3,
         "cells": int(len(ct.values)), "total_mass_kg": total_mass}
  for lam, i in pairs[:nev]:
    es.getEigenpair(i, phi.x.petsc_vec)
    phi.x.scatter_forward()
    M.mult(phi.x.petsc_vec, Mphi)
    norm = math.sqrt(phi.x.petsc_vec.dot(Mphi))
    phi.x.array[:] /= norm
    M.mult(phi.x.petsc_vec, Mphi)
    gam = []
    for ax in range(3):
      r.x.array[:] = 0.0
      r.x.array[ax::3] = 1.0
      gam.append(float(r.x.petsc_vec.dot(Mphi)))
    rot = [float(fem.assemble_scalar(fem.form(0.5 * ufl.curl(phi)[k] * dx(rb))) / vol) for k in range(3)]
    out["freq_hz"].append(math.sqrt(max(lam, 0.0)) / (2 * math.pi))
    out["gamma"].append(gam)
    out["rotation"].append(rot)
    if keep:                       # the mode shapes, for the figure (not written to the results)
      out.setdefault("shapes", []).append(phi.x.array.copy())
  if keep:
    out["V"] = V
  return out


def road_accel_psd(p: dict, f: np.ndarray, cls: str) -> np.ndarray:
  """The body's vertical acceleration PSD, (m/s²)²/Hz, on an ISO 8608 road at the set speed (quarter-car)."""
  vb = p["vibration"]
  v = vb["speed_kph"] / 3.6
  rd = vb["road"]
  Gz = rd[cls] * rd["n0"] ** rd["waviness"] * v ** (rd["waviness"] - 1) / f ** rd["waviness"]   # m²/Hz in time
  q = vb["quarter_car"]
  w = 2 * np.pi * f
  ms, mu, ks, cs, kt = q["m_body"], q["m_wheel"], q["k_spring"], q["c_damper"], q["k_tyre"]
  # [ -w²ms + iwcs + ks,  -(iwcs + ks) ; -(iwcs + ks), -w²mu + iwcs + ks + kt ] [zs; zu] = [0; kt zr]
  a11 = -w ** 2 * ms + 1j * w * cs + ks
  a12 = -(1j * w * cs + ks)
  a22 = -w ** 2 * mu + 1j * w * cs + ks + kt
  zs = -a12 * kt / (a11 * a22 - a12 * a12)       # body displacement per unit road displacement
  return np.abs(-(w ** 2) * zs) ** 2 * Gz


def jitter(m: dict, zeta: float, f: np.ndarray, Sa: np.ndarray, direction) -> dict:
  """RMS rotation of the device relative to the car (rad) about each axis, for base acceleration along the unit
  vector `direction` (model frame) with PSD Sa."""
  w = 2 * np.pi * f
  H = np.zeros((3, len(f)), complex)
  for fn, g, rot in zip(m["freq_hz"], m["gamma"], m["rotation"], strict=True):
    wn = 2 * np.pi * fn
    q = -float(np.dot(g, direction)) / (wn ** 2 - w ** 2 + 2j * zeta * wn * w)
    H += np.outer(rot, q)
  psd = np.abs(H) ** 2 * Sa
  return {"rms_rad": [float(math.sqrt(np.trapezoid(psd[k], f))) for k in range(3)], "psd": psd}


def run(p: dict, refine=REFINE) -> dict:
  vb = p["vibration"]
  blocks, mats, nev = vb["blocks"], vb["materials"], vb["modes"]
  study = [modes(blocks, mats, vb["cells_per_m"], nev, rf, keep=rf == refine[-1]) for rf in refine]
  m = study[-1]
  band = {}
  for k, E in zip(("soft", "stiff"), mats["pad"]["E_band"], strict=True):
    mm = {**mats, "pad": {**mats["pad"], "E": E}}
    band[k] = modes(blocks, mm, vb["cells_per_m"], nev, refine[0])["freq_hz"]
  fpx = focal_px()
  # the model's frame is the pad's: y along the glass's normal, z up the glass. The car's vertical is tilted from the
  # glass's normal by the glass's rake from horizontal, so it also shakes the pad along the glass.
  tilt = math.radians(vb["glass_tilt_deg"]["value"])
  up = np.array([0.0, math.cos(tilt), math.sin(tilt)])
  f = np.geomspace(0.5, 1000.0, 6000)
  out = {"about": "Synthetic (DSR-12), design aid, no evidence credit. Estimated sizes and materials until T1; "
                  "ISO 8608 roads through a quarter-car.",
         "focal_px": fpx, "total_mass_kg": round(m["total_mass_kg"], 4),
         "mesh_study": [{"refine": rf, "cells": s["cells"], "dofs": s["dofs"], "f1_hz": round(s["freq_hz"][0], 3)}
                        for rf, s in zip(refine, study, strict=True)],
         "modes": [], "pad_band_hz": {k: [round(x, 2) for x in v] for k, v in band.items()},
         "orders_hz": {k: v["value"] for k, v in vb["orders"].items()}, "roads": {}}
  for fn, g, rot in zip(m["freq_hz"], m["gamma"], m["rotation"], strict=True):
    tot = m["total_mass_kg"]
    out["modes"].append({"freq_hz": round(fn, 2), "eff_mass_share": [round(x * x / tot, 4) for x in g],
                         "rotation_axis": int(np.argmax(np.abs(rot))),
                         "kind": describe(g, rot, tot)})
  for cls in ("A", "B"):
    Sa = road_accel_psd(p, f, cls)
    body_rms = float(math.sqrt(np.trapezoid(Sa, f)))
    road = {"body_rms_m_s2": round(body_rms, 4)}
    for zk in ("value", "low", "high"):
      j = jitter(m, vb["damping"][zk], f, Sa, up)
      road[f"zeta_{zk}"] = {"pitch_px": round(j["rms_rad"][0] * fpx, 6), "yaw_px": round(j["rms_rad"][1] * fpx, 6),
                            "roll_mrad": round(j["rms_rad"][2] * 1e3, 6)}
    if cls == "B":                 # the pitch spectrum for the figure, thinned
      ft = np.geomspace(1.0, 1000.0, 500)
      St = road_accel_psd(p, ft, cls)
      j = jitter(m, vb["damping"]["value"], ft, St, up)
      road["trace"] = {"f_hz": [round(float(x), 3) for x in ft],
                       "pitch_psd_px2": [float(f"{x:.4g}") for x in j["psd"][0] * fpx ** 2]}
    out["roads"][cls] = road
  first = out["modes"][0]["freq_hz"]
  out["clearance"] = {k: round(first / v["value"][1], 2) for k, v in vb["orders"].items()}
  return out, m


def describe(g, rot, tot) -> str:
  share = [x * x / tot for x in g]
  ax = int(np.argmax(np.abs(rot)))
  names = {0: "nods (pitch)", 1: "twists about the axis off the glass (near yaw)", 2: "rocks side to side (roll)"}
  if max(share) > 0.3 and max(np.abs(rot)) < 1.0:
    return ["sways across the car", "bounces off the glass", "sways along the glass"][int(np.argmax(share))]
  return names[ax]


def compare(new, old, path=""):
  if isinstance(new, dict):
    return [e for k in set(new) | set(old) for e in
            ([f"{path}/{k}: missing"] if k not in new or k not in old else compare(new[k], old[k], f"{path}/{k}"))]
  if isinstance(new, list):
    if len(new) != len(old):
      return [f"{path}: length differs"]
    return [e for i, (a, b) in enumerate(zip(new, old, strict=True)) for e in compare(a, b, f"{path}[{i}]")]
  if isinstance(new, float) and isinstance(old, (int, float)):
    return [] if abs(new - old) <= 1e-6 + REL_TOL * abs(old) else [f"{path}: {new} != {old}"]
  return [] if new == old else [f"{path}: {new!r} != {old!r}"]


def markdown(r: dict, p: dict) -> str:
  vb = p["vibration"]
  L = [
    "# The mount's vibration modes and the road camera's jitter",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`thermal/mount_modes.py`](../thermal/mount_modes.py) (FEniCSx, SLEPc); do not edit by hand. The mount's sizes "
    "and materials are estimates until T1 measures them; the pad's stiffness is the least known and is given as a band.",
    "",
    f"The pad, the mount and the device ({r['total_mass_kg'] * 1000:.0f} g in all) as blocks of "
    "[`params.yaml`](../thermal/params.yaml), fixed at the glass, the device standing off it square; quadratic "
    "hexahedra. The road camera's focal length is "
    f"{r['focal_px']:.0f} px (openpilot `camera.py`), so 1 mrad of turn moves the image {r['focal_px'] / 1000:.2f} px.",
    "",
    "## Modes",
    "",
    "| Mode | Frequency | Pad soft – stiff | Shape | Share of the mass moved by base motion (across / off the glass / along it) |",
    "|---|---|---|---|---|",
  ]
  for i, md in enumerate(r["modes"]):
    s = md["eff_mass_share"]
    L.append(f"| {i + 1} | {md['freq_hz']:.0f} Hz | {r['pad_band_hz']['soft'][i]:.0f} – {r['pad_band_hz']['stiff'][i]:.0f} Hz "
             f"| {md['kind']} | {100 * s[0]:.0f} / {100 * s[1]:.0f} / {100 * s[2]:.0f} % |")
  ms = r["mesh_study"]
  L += ["", f"Mesh study, first mode: " + ", ".join(f"{s['f1_hz']:.2f} Hz ({s['dofs']:,} unknowns)" for s in ms) + ".",
        "", "## Against what shakes the car", "",
        "| Source | Frequencies | First mode / its top |", "|---|---|---|"]
  labels = {"wheel": "Wheel turning (first order)", "idle": "Engine at idle (second order)",
            "cruise": "Engine at cruise (second order)"}
  for k, v in r["orders_hz"].items():
    L.append(f"| {labels[k]} | {v[0]:.0f}–{v[1]:.0f} Hz | {r['clearance'][k]:.1f} |")
  L += ["", "## Road-driven jitter at 110 km/h", "",
        "RMS turn of the device relative to the car, driven by the body's vertical motion (quarter-car on an ISO 8608 "
        f"road); damping {100 * vb['damping']['value']:.0f} % ({100 * vb['damping']['low']:.0f}–"
        f"{100 * vb['damping']['high']:.0f} %):", "",
        "| Road | Body acceleration RMS | Pitch | Twist (near yaw) | Pitch at 2 % damping |", "|---|---|---|---|---|"]
  for cls, rd in r["roads"].items():
    z = rd["zeta_value"]
    L.append(f"| ISO 8608 class {cls} | {rd['body_rms_m_s2']:.2f} m/s² | {z['pitch_px']:.2g} px | {z['yaw_px']:.2g} px | "
             f"{rd['zeta_low']['pitch_px']:.2g} px |")
  m1 = r["modes"][0]
  worst = max(rd["zeta_low"]["pitch_px"] for rd in r["roads"].values())
  L += ["", "## What this shows (generated)", "",
        f"- The first mode is at {m1['freq_hz']:.0f} Hz ({r['pad_band_hz']['soft'][0]:.0f}–"
        f"{r['pad_band_hz']['stiff'][0]:.0f} Hz over the pad's band): the device {m1['kind']} on the pad. "
        f"It sits {r['clearance']['idle']:.1f} times above the top of the idle band and "
        f"{r['clearance']['wheel']:.1f} times above the wheel order; "
        + ("the engine's cruise order overlaps the band of the first mode, so a log at cruise should look for it."
           if r["pad_band_hz"]["soft"][0] <= r["orders_hz"]["cruise"][1] else
           f"{r['clearance']['cruise']:.1f} times above the engine's cruise order."),
        f"- The road's own shaking, filtered by the suspension, is small up there. The road-driven jitter is at most "
        f"{worst:.2g} px RMS even at 2 % damping, and most of it is the pad giving a little under the body's slow "
        "bounce, below the mode, so the damping hardly matters. Far below a pixel: a sound mount does not blur or "
        "shift the road camera's image through the road.",
        "- For KS-16 and calibration drift: the risk is a mount that is not sound (a soft or failing pad, play in the "
        "hinge), which this does not model. For WP-H-07 QE-08: the modes give comma's vibration qualification a "
        "frequency to look at, not a pass.",
        ""]
  return "\n".join(L)


def main(argv):
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("--check", action="store_true")
  ap.add_argument("--figures", action="store_true")
  a = ap.parse_args(argv[1:])
  p = yaml.safe_load((HERE / "params.yaml").read_text(encoding="utf-8"))
  r, m = run(p)
  md = markdown(r, p)
  if a.check:
    errs = compare(r, json.loads(OUT_JSON.read_text(encoding="utf-8")))
    if not errs and OUT_MD.read_text(encoding="utf-8") != md:
      errs.append(f"{OUT_MD.name} is stale")
    for e in errs[:20]:
      print("FAIL", e)
    print("mount modes:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, indent=1) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name, [m["freq_hz"] for m in r["modes"]], r["mesh_study"], r["roads"])
  if a.figures:
    import figures
    figures.mount_figure(p, r, m, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
