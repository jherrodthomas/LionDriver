#!/usr/bin/env python3
"""Checks of the device heat model (TE-04 §5 T3): what would catch a solver, mesh or set-up error.

V1  Analytic slab: FEniCSx and FiPy each against the exact solution of a slab with a source and Robin ends.
V2  Lumped transient: a well-mixed box against the exact exponential (time stepping and heat capacity).
V3  Cross-check: FEniCSx and FiPy on the same 2D section of the device; two methods, no shared code.
V4  Energy balance: on the device model the heat in equals the heat out at steady state.
V5  Mesh study: the hottest SoC point changes by less than the tolerance between the two finest meshes.
V6  Limits: the overheat bands are read from hardwared.py, and the pilot reports the comma 3X one.
V7  The cabin-driven runner (phases, time-varying references) equals the pilot's runner when nothing varies.

Runs in the environment of `thermal-linux-64.lock`. Synthetic (DSR-12), design aid, no evidence credit (DQ-413).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import section_fipy  # noqa: E402
import thermal_pilot as tp  # noqa: E402
from heat import Box, Face, Model  # noqa: E402

P = yaml.safe_load((HERE / "params.yaml").read_text(encoding="utf-8"))


class Checks(unittest.TestCase):
  def test_v1_analytic_slab(self):
    L, k, h, q, Tinf = 0.1, 5.0, 10.0, 1000.0, 30.0
    exact = lambda x: Tinf + q * L / (2 * h) + q / (2 * k) * x * (L - x)  # noqa: E731
    m = Model(Box(size=(L,), cells=(40,), k=k, rho_c=1.0, faces=[Face("a", 0, 0, h, "air"), Face("b", 0, 1, h, "air")],
                  uniform_power=q * L))
    T = m.steady({"air": Tinf})
    x = m.V.tabulate_dof_coordinates()[:, 0]
    self.assertLess(np.abs(T - exact(x)).max(), 1e-8)   # P1 is nodally exact in 1D
    _, Tf, _, xc = section_fipy.solve((L,), (40,), k, [(0, 0, h, "air", 0.0), (0, 1, h, "air", 0.0)], {"air": Tinf},
                                      {}, uniform_power=q * L)
    self.assertLess(np.abs(Tf - exact(xc[0])).max(), 1e-3)

  def test_v2_lumped_transient(self):
    size, h, rho_c, power, T0, Tinf = (0.12, 0.06, 0.025), 10.0, 1.6e6, 7.0, 40.0, 30.0
    faces = [Face(f"{a}{s}", a, s, h, "air") for a in range(3) for s in (0, 1)]
    m = Model(Box(size=size, cells=(12, 6, 3), k=1e4, rho_c=rho_c, faces=faces, uniform_power=power))
    A = 2 * (size[0] * size[1] + size[0] * size[2] + size[1] * size[2])
    V = size[0] * size[1] * size[2]
    tau = rho_c * V / (h * A)
    t, y, _ = m.transient({"air": Tinf}, 3 * tau, tau / 200, T0, [lambda a: float(a.mean())])
    exact = Tinf + power / (h * A) + (T0 - Tinf - power / (h * A)) * np.exp(-t / tau)
    rise = power / (h * A)
    self.assertLess(np.abs(y[:, 0] - exact).max() / rise, 0.01)

  def test_v3_fipy_cross_check(self):
    # the device's rear face as a 2D section: SoC and MCU sources, the six faces' h folded onto four edges
    size, cells, k = (0.12, 0.06), (120, 60), 8.0
    src = {"soc": ((0.052, 0.034), (0.015, 0.015), 200.0), "mcu": ((0.092, 0.016), (0.008, 0.008), 16.0)}
    edges = [(0, 0, 8.0, "air", 0.0), (0, 1, 160.0, "air", 0.0), (1, 0, 8.0, "air", 0.0), (1, 1, 20.0, "glass", 500.0)]
    refs = {"air": 45.0, "glass": 60.0}
    m = Model(Box(size=size, cells=cells, k=k, rho_c=1.0,
                  faces=[Face(f"e{i}", a, s, h, r, fl) for i, (a, s, h, r, fl) in enumerate(edges)],
                  sources=src, uniform_power=64.0))
    T = m.steady(refs)
    fe_soc, fe_mean = float(T[m.region["soc"]].mean()), m.mean()
    mesh, Tf, reg, _ = section_fipy.solve(size, cells, k, edges, refs, src, uniform_power=64.0)
    vol = np.array(mesh.cellVolumes)
    fv_soc, fv_mean = float(Tf[reg["soc"]].mean()), float((Tf * vol).sum() / vol.sum())
    rise = fe_mean - refs["air"]
    self.assertLess(abs(fe_mean - fv_mean) / rise, 0.005, (fe_mean, fv_mean))
    self.assertLess(abs(fe_soc - fv_soc) / (fe_soc - refs["air"]), 0.01, (fe_soc, fv_soc))

  def test_v4_energy_balance(self):
    m = tp.build(P)
    r = tp.refs(P, 45.0)
    m.steady(r)
    self.assertAlmostEqual(m.source_power(), 7.0, places=9)
    self.assertLess(abs(m.boundary_loss(r) - m.source_power()) / m.source_power(), 1e-8)

  def test_v5_mesh_study(self):
    r = tp.refs(P, 45.0)
    peaks = []
    for cells in ((48, 24, 10), (72, 36, 15), (96, 48, 20)):
      m = tp.build(P, cells=cells)
      T = m.steady(r)
      peaks.append(float(T[m.region["soc"]].max()))
    self.assertLess(abs(peaks[2] - peaks[1]), 1.0, peaks)   # K, against a 96 °C limit read to the degree
    self.assertLess(abs(peaks[0] - peaks[2]), 2.0, peaks)   # the pilot's mesh is within 2 K of the finest

  def test_v7_phases_match_transient(self):
    # The cabin-driven runner (time-varying references, phases) gives the pilot's result when nothing varies
    m = tp.build(P, cells=(24, 12, 5))
    r = tp.refs(P, 40.0)
    probes = [m.region_max("soc")]
    _, y1, _ = m.transient(r, 1800.0, 60.0, 50.0, probes)
    _, y2, _ = m.transient_phases([{"duration": 900.0, "refs": lambda t: r}, {"duration": 900.0, "refs": lambda t: r}],
                                  60.0, 50.0, probes)
    self.assertLess(float(np.abs(y1[:, 0] - y2[:, 0]).max()), 1e-9)

  def test_v6_limits_from_the_code(self):
    b = tp.bands()
    self.assertEqual(b["comma 3X"], {"overheated_above": 96.0, "ok_again_below": 88.0})
    self.assertEqual(b["comma four"], {"overheated_above": 100.0, "ok_again_below": 92.0})


if __name__ == "__main__":
  unittest.main(verbosity=2)
