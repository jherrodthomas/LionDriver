"""The independent cross-check: the same steady problem solved with FiPy (NIST finite volumes), in 1D or 2D.

    0 = div(k grad T) + q,    -k dT/dn = h (T - T_ref) on each edge

Each Robin edge is a sink on its boundary cells, with the half-cell conduction in series with h:
h' = 1 / (1/h + d/k), d the distance from the cell centre to the face. Shares no code with heat.py.
Synthetic (DSR-12), design aid, no evidence credit (DQ-413).
"""

from __future__ import annotations

import numpy as np
from fipy import CellVariable, DiffusionTerm, Grid1D, Grid2D, ImplicitSourceTerm
from fipy.solvers.scipy import LinearLUSolver


def solve(size, cells, k, faces, refs, sources, uniform_power=0.0):
  """faces: (axis, side, h, ref, flux) tuples; sources: name -> (centre, size, power). Returns (mesh, T, regions)."""
  dim = len(size)
  d = [size[i] / cells[i] for i in range(dim)]
  m = Grid1D(dx=d[0], nx=cells[0]) if dim == 1 else Grid2D(dx=d[0], dy=d[1], nx=cells[0], ny=cells[1])
  xc = np.array(m.cellCenters.value).reshape(dim, -1)
  vol = np.array(m.cellVolumes)
  q = np.full(m.numberOfCells, uniform_power / vol.sum())
  regions = {}
  for name, (centre, sz, power) in sources.items():
    inside = np.all([np.abs(xc[i] - centre[i]) <= sz[i] / 2 + 1e-12 for i in range(dim)], axis=0)
    q[inside] += power / vol[inside].sum()
    regions[name] = inside
  beta = np.zeros(m.numberOfCells)
  rhs = np.zeros(m.numberOfCells)
  fc = np.array(m.faceCenters.value).reshape(dim, -1)
  area = np.array(m._faceAreas)
  owner = np.array(m.faceCellIDs.data[0])
  ext = np.array(m.exteriorFaces.value)
  for axis, side, h, ref, flux in faces:
    at = 0.0 if side == 0 else size[axis]
    on = ext & np.isclose(fc[axis], at, atol=1e-12)
    hp = 1.0 / (1.0 / h + (d[axis] / 2) / k)
    cells_on = owner[on]
    np.add.at(beta, cells_on, hp * area[on] / vol[cells_on])
    # an imposed flux enters through the half cell too; with the series resistance it splits as h'/h
    np.add.at(rhs, cells_on, (hp * refs[ref] + flux * hp / h) * area[on] / vol[cells_on])
  T = CellVariable(mesh=m, value=0.0)
  B = CellVariable(mesh=m, value=beta)
  S = CellVariable(mesh=m, value=q + rhs)
  eq = DiffusionTerm(coeff=k) - ImplicitSourceTerm(coeff=B) + S == 0
  eq.solve(var=T, solver=LinearLUSolver())
  return m, np.array(T.value), regions, xc
