#!/usr/bin/env python3
"""The FMU of the L1 plant, run by FMPy, gives the same trajectory as the plant run in-process (same code, same
inputs). Skipped when pythonfmu or FMPy is not installed; the sim-plant CI job installs both."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import corolla  # noqa: E402
from plant import CorollaPlant  # noqa: E402

HAVE = all(importlib.util.find_spec(m) for m in ("pythonfmu", "fmpy"))


def inputs(k: int) -> dict:
  """10 ms master steps: a torque ramp at 15/frame to 900, held, then frames stop; an acceleration step."""
  return {"lka_torque": float(min(15 * k, 900)), "lka_request": True, "lka_frames": k if k < 300 else 299,
          "accel_cmd": 1.0 if k >= 100 else 0.0, "acc_frames": k // 3, "eps_fault": False,
          "driver_ay": 0.0, "driver_ax": 0.0}


@unittest.skipUnless(HAVE, "pythonfmu and FMPy not installed")
class TestFmu(unittest.TestCase):
  def test_fmu_matches_in_process_plant(self):
    from fmpy import extract, read_model_description
    from fmpy.fmi2 import FMU2Slave
    from build_fmu import build

    with tempfile.TemporaryDirectory() as tmp:
      fmu = build(Path(tmp))
      md = read_model_description(fmu)
      vr = {v.name: v.valueReference for v in md.modelVariables}
      unzipdir = extract(fmu, unzipdir=str(Path(tmp) / "x"))
      slave = FMU2Slave(guid=md.guid, unzipDirectory=unzipdir, modelIdentifier=md.coSimulation.modelIdentifier,
                        instanceName="plant")
      slave.instantiate()
      slave.setupExperiment(startTime=0.0)
      slave.enterInitializationMode()
      slave.setReal([vr["v0"], vr["eps_timeout"], vr["pcm_timeout"]], [30.0, 0.03, 0.10])
      slave.exitInitializationMode()

      d = corolla.as_dict()
      ref = CorollaPlant(30.0, 0.03, 0.10, d, corolla.commonroad_parameters(d))
      seen = (-1, -1)
      for k in range(400):
        t, u = k * 0.01, inputs(k)
        slave.setReal([vr[n] for n in ("lka_torque", "accel_cmd", "driver_ay", "driver_ax")],
                      [u["lka_torque"], u["accel_cmd"], 0.0, 0.0])
        slave.setInteger([vr["lka_frames"], vr["acc_frames"]], [u["lka_frames"], u["acc_frames"]])
        slave.setBoolean([vr["lka_request"], vr["eps_fault"]], [True, False])
        slave.doStep(currentCommunicationPoint=t, communicationStepSize=0.01)
        if u["lka_frames"] != seen[0]:
          ref.lka_frame(t, u["lka_torque"], 1)
        if u["acc_frames"] != seen[1]:
          ref.acc_frame(t, u["accel_cmd"])
        seen = (u["lka_frames"], u["acc_frames"])
        for i in range(2):
          ref.step(t + i * 0.005, 0.005)
      out = slave.getReal([vr[n] for n in ("sy", "v", "eps_torque")])
      slave.terminate()
      slave.freeInstance()

    self.assertAlmostEqual(out[0], ref.x[1], places=9)
    self.assertAlmostEqual(out[1], ref.x[3], places=9)
    self.assertAlmostEqual(out[2], ref.eps_torque, places=9)
    self.assertGreater(abs(ref.x[1]), 1.0)   # the run did move the car sideways


if __name__ == "__main__":
  unittest.main()
