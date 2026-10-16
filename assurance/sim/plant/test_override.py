#!/usr/bin/env python3
"""Tests of the driver-override study's --scales option (M-08 torque scales, SIM-OI-8).

The parsing tests run anywhere the plant runs. The table test needs the column FMU (build/sim-column, built by
modelica/test_column.py in the 'simulation L2 column' job) and is skipped without it. The scale values used here
are placeholders, not measurements, and nothing is written to the results directory.
"""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "modelica"))
import override  # noqa: E402
from build_column_fmu import BUILD  # noqa: E402

FMU = BUILD / "SteeringColumn.fmu"


class TestParseScales(unittest.TestCase):
  def test_valid(self):
    self.assertEqual(override.parse_scales("driver=0.007,lka=0.002"), (0.007, 0.002))
    self.assertEqual(override.parse_scales(" lka = 0.002 , driver = 0.007 "), (0.007, 0.002))

  def test_rejected(self):
    for bad in ("driver=0.01", "lka=0.002", "driver=-1,lka=0.002", "driver=0,lka=0.002", "driver=x,lka=1",
                "driver=nan,lka=1", "driver=inf,lka=1", "driver=1,lka=1,foo=2", "driver=1,driver=2", "0.007,0.002"):
      with self.assertRaises(ValueError, msg=bad):
        override.parse_scales(bad)

  def test_source_required(self):
    # refused before anything runs or is written
    self.assertEqual(override.main(["--fmu", str(FMU), "--scales", "driver=0.007,lka=0.002"]), 2)
    self.assertEqual(override.main(["--fmu", str(FMU), "--scales", "driver=0.007,lka=0.002", "--source", " "]), 2)


@unittest.skipUnless(FMU.exists(), "column FMU not built (modelica/test_column.py builds it)")
class TestMeasuredTable(unittest.TestCase):
  def test_measured_scales_run_and_label(self):
    driver, lka = 0.007, 0.002      # placeholders: 3.5 N·m host threshold, 3 N·m full LKA torque
    runs = override.sweep(str(FMU), (lka * override.STEER_MAX,), (driver * override.MAX_USER_TORQUE,))
    self.assertEqual(len(runs), len(override.DRIVER_PEAK_NM) * len(override.DRIVER_RISE_S))
    self.assertTrue(all(r.lka_nm == 3.0 and r.host_nm == 3.5 for r in runs))
    text = override.table(runs, (driver, lka), "test placeholder")
    self.assertIn("measured torque scales", text.splitlines()[0])
    self.assertIn("**Torque scales measured** (test placeholder)", text)
    self.assertNotIn("both CAN torque scales are assumptions", text)
    self.assertIn("| data_kind | synthetic |", text)
    # scales equal to a swept point reproduce that point's rows of the committed swept table
    rows = [ln for ln in text.splitlines() if ln.startswith("| 3 | 3.5 |")]
    committed = override.TABLE.read_text(encoding="utf-8").splitlines()
    self.assertEqual(rows, [ln for ln in committed if ln.startswith("| 3 | 3.5 |")])
    self.assertEqual(len(rows), len(runs))


if __name__ == "__main__":
  unittest.main()
