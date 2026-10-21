"""Heat conduction with Robin faces in FEniCSx (DOLFINx 0.10): the solver core of the device heat model.

    rho_c dT/dt = div(k grad T) + q    in the box (or rectangle, or interval)
    -k dT/dn   = h (T - T_ref)         on each tagged face

One function for 1D, 2D and 3D, so the checks in `test_thermal.py` exercise the same code as the device model.
Backward Euler in time. Serial only. Synthetic (DSR-12), design aid, no evidence credit (DQ-413).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import ufl
from dolfinx import fem, mesh
from dolfinx.fem import petsc as fpetsc
from mpi4py import MPI
from petsc4py import PETSc

TOL = 1e-9


@dataclass
class Face:
  name: str
  axis: int        # 0, 1, 2
  side: int        # 0 = low end, 1 = high end
  h: float         # W/m²K (W/mK in 2D, W/K in 1D)
  ref: str         # key into the reference temperatures, e.g. "air" or "glass"
  flux: float = 0.0  # imposed inward flux, W/m² (sun)


@dataclass
class Box:
  size: tuple
  cells: tuple
  k: float
  rho_c: float
  faces: list
  sources: dict = field(default_factory=dict)   # name -> (centre, size, power); power in W (W/m in 2D)
  uniform_power: float = 0.0


class Model:
  def __init__(self, box: Box):
    self.box = box
    dim = len(box.size)
    lo, hi = np.zeros(dim), np.array(box.size, dtype=float)
    if dim == 1:
      self.mesh = mesh.create_interval(MPI.COMM_SELF, box.cells[0], [0.0, hi[0]])
    elif dim == 2:
      self.mesh = mesh.create_rectangle(MPI.COMM_SELF, [lo, hi], list(box.cells), mesh.CellType.quadrilateral)
    else:
      self.mesh = mesh.create_box(MPI.COMM_SELF, [lo, hi], list(box.cells), mesh.CellType.hexahedron)
    self.dim = dim
    self.V = fem.functionspace(self.mesh, ("Lagrange", 1))
    fdim = dim - 1
    idx, vals = [], []
    for tag, f in enumerate(box.faces, start=1):
      at = 0.0 if f.side == 0 else hi[f.axis]
      ents = mesh.locate_entities_boundary(self.mesh, fdim, lambda x, a=f.axis, v=at: np.isclose(x[a], v, atol=TOL))
      idx.append(ents)
      vals.append(np.full(len(ents), tag, dtype=np.int32))
    idx, vals = np.concatenate(idx), np.concatenate(vals)
    order = np.argsort(idx)
    self.ft = mesh.meshtags(self.mesh, fdim, idx[order], vals[order])
    self.ds = ufl.Measure("ds", domain=self.mesh, subdomain_data=self.ft)
    self.dx = ufl.Measure("dx", domain=self.mesh)
    self.region = {}
    W = fem.functionspace(self.mesh, ("DG", 0))
    self.q = fem.Function(W)
    vol = fem.assemble_scalar(fem.form(fem.Constant(self.mesh, 1.0) * self.dx))
    self.volume = vol
    q = np.full(self.q.x.array.shape, box.uniform_power / vol)
    for name, (centre, size, power) in box.sources.items():
      chi = fem.Function(W)
      chi.interpolate(lambda x, c=centre, s=size: np.all(
        [np.abs(x[i] - c[i]) <= s[i] / 2 + TOL for i in range(dim)], axis=0).astype(float))
      v = fem.assemble_scalar(fem.form(chi * self.dx))
      if v <= 0:
        raise ValueError(f"source {name} holds no cell: refine the mesh")
      q += power / v * chi.x.array
      xs = self.V.tabulate_dof_coordinates()[:, :dim]
      self.region[name] = np.all([np.abs(xs[:, i] - centre[i]) <= size[i] / 2 + TOL for i in range(dim)], axis=0)
    self.q.x.array[:] = q
    self.T = fem.Function(self.V)

  def _c(self, v):
    # Constants, not literals: the form compiles once for every temperature and variant
    return fem.Constant(self.mesh, PETSc.ScalarType(v))

  def _forms(self, refs: dict, dt: float | None, q_scale: float = 1.0):
    u, v = ufl.TrialFunction(self.V), ufl.TestFunction(self.V)
    b, c = self.box, self._c
    a = c(b.k) * ufl.inner(ufl.grad(u), ufl.grad(v)) * self.dx
    L = c(q_scale) * self.q * v * self.dx
    for tag, f in enumerate(b.faces, start=1):
      a += c(f.h) * u * v * self.ds(tag)
      L += (c(f.h) * c(refs[f.ref]) + c(f.flux)) * v * self.ds(tag)
    if dt is not None:
      self.T_old = fem.Function(self.V)
      a += c(b.rho_c / dt) * u * v * self.dx
      L += c(b.rho_c / dt) * self.T_old * v * self.dx
    return fem.form(a), fem.form(L)

  def _solver(self, a):
    A = fpetsc.assemble_matrix(a)
    A.assemble()
    ksp = PETSc.KSP().create(MPI.COMM_SELF)
    ksp.setOperators(A)
    # One LU factorisation per run; each time step is then a back-substitution
    ksp.setType("preonly")
    ksp.getPC().setType("lu")
    return ksp, A

  def _solve(self, ksp, L):
    bvec = fpetsc.assemble_vector(L)
    bvec.ghostUpdate(addv=PETSc.InsertMode.ADD, mode=PETSc.ScatterMode.REVERSE)
    ksp.solve(bvec, self.T.x.petsc_vec)
    if ksp.getConvergedReason() <= 0:
      raise RuntimeError(f"linear solver did not converge ({ksp.getConvergedReason()})")
    self.T.x.scatter_forward()
    bvec.destroy()

  def steady(self, refs: dict, q_scale: float = 1.0) -> np.ndarray:
    a, L = self._forms(refs, None, q_scale)
    ksp, A = self._solver(a)
    self._solve(ksp, L)
    ksp.destroy(); A.destroy()
    return self.T.x.array.copy()

  def transient(self, refs: dict, t_end: float, dt: float, T0: float, probes, every: int = 1):
    """Run from a uniform T0; return times and, per probe callback, its value at each kept step."""
    a, L = self._forms(refs, dt)
    ksp, A = self._solver(a)
    self.T_old.x.array[:] = T0
    self.T.x.array[:] = T0
    times, out = [0.0], [[p(self.T.x.array) for p in probes]]
    snaps = [self.T.x.array.copy()]
    n = int(round(t_end / dt))
    for i in range(1, n + 1):
      self._solve(ksp, L)
      self.T_old.x.array[:] = self.T.x.array
      if i % every == 0 or i == n:
        times.append(i * dt)
        out.append([p(self.T.x.array) for p in probes])
        snaps.append(self.T.x.array.copy())
    ksp.destroy(); A.destroy()
    return np.array(times), np.array(out), snaps

  def transient_phases(self, phases, dt: float, T0: float, probes):
    """Run phases in turn from a uniform T0. Each phase: duration (s), refs(t) -> {name: °C} for t in s from the
    phase start, q_scale (board power on 1 / off 0), flux_scale (sun on the device), h (face name -> h override).
    The reference temperatures change every step; the matrix only between phases."""
    times, out, snaps, t0 = [0.0], [], [], 0.0
    self.T.x.array[:] = T0
    out.append([p(self.T.x.array) for p in probes])
    snaps.append(self.T.x.array.copy())
    for ph in phases:
      faces = self.box.faces
      saved = [(f.h, f.flux) for f in faces]
      for f in faces:
        f.h = ph.get("h", {}).get(f.name, f.h)
        f.flux = f.flux * ph.get("flux_scale", 1.0)
      refc = {k: self._c(v) for k, v in ph["refs"](0.0).items()}
      u, v = ufl.TrialFunction(self.V), ufl.TestFunction(self.V)
      c = self._c
      a = c(self.box.k) * ufl.inner(ufl.grad(u), ufl.grad(v)) * self.dx + c(self.box.rho_c / dt) * u * v * self.dx
      self.T_old = fem.Function(self.V)
      L = c(ph.get("q_scale", 1.0)) * self.q * v * self.dx + c(self.box.rho_c / dt) * self.T_old * v * self.dx
      for tag, f in enumerate(faces, start=1):
        a += c(f.h) * u * v * self.ds(tag)
        L += (c(f.h) * refc[f.ref] + c(f.flux)) * v * self.ds(tag)
      for f, (h, fl) in zip(faces, saved, strict=True):
        f.h, f.flux = h, fl
      ksp, A = self._solver(fem.form(a))
      Lf = fem.form(L)
      n = int(round(ph["duration"] / dt))
      for i in range(1, n + 1):
        for k, val in ph["refs"](i * dt).items():
          refc[k].value = val
        self.T_old.x.array[:] = self.T.x.array
        self._solve(ksp, Lf)
        times.append(t0 + i * dt)
        out.append([p(self.T.x.array) for p in probes])
        snaps.append(self.T.x.array.copy())
      ksp.destroy(); A.destroy()
      t0 += n * dt
    return np.array(times), np.array(out), snaps

  def boundary_loss(self, refs: dict) -> float:
    """Heat leaving through all faces at the current T, minus the imposed flux (W): the energy balance."""
    total = 0.0
    for tag, f in enumerate(self.box.faces, start=1):
      total += fem.assemble_scalar(fem.form((self._c(f.h) * (self.T - self._c(refs[f.ref])) - self._c(f.flux)) * self.ds(tag)))
    return total

  def source_power(self) -> float:
    return fem.assemble_scalar(fem.form(self.q * self.dx))

  def mean(self) -> float:
    return fem.assemble_scalar(fem.form(self.T * self.dx)) / self.volume

  def region_max(self, name):
    return lambda arr: float(arr[self.region[name]].max())

  def region_mean(self, name):
    return lambda arr: float(arr[self.region[name]].mean())
