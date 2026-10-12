#!/usr/bin/env python3
"""Tests for the RX inter-frame gap scan (synthetic logs with known gaps)."""
from __future__ import annotations

import io
import json
import os
import re
import tempfile
import unittest
from contextlib import redirect_stdout

from tools.can_gaps import can_gap_scan as cgs

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TOYOTA_H = os.path.join(ROOT, "opendbc_repo", "opendbc", "safety", "modes", "toyota.h")


def periodic(addr, hz, start_s=0.0, dur_s=2.0, bus=0, drop=()):
  """Frames of one message at hz; indices in drop are left out (to make a gap)."""
  n = int(dur_s * hz)
  return [(start_s + i / hz, bus, addr) for i in range(n) if i not in drop]


def write_csv(rows, d, name="frames.csv"):
  path = os.path.join(d, name)
  with open(path, "w") as f:
    f.write("time_s,bus,address\n")
    for t, b, a in sorted(rows):
      f.write(f"{t:.6f},{b},0x{a:X}\n")
  return path


def lka_drive(drop_aa=()):
  rows = []
  for addr, hz in cgs.VARIANTS["lka"]:
    rows += periodic(addr, hz, drop=drop_aa if addr == 0xAA else ())
  return rows


def read_rows(path):
  with open(path) as f:
    return {r["address"]: r for r in json.load(f)["rows"]}


def run(argv):
  out = io.StringIO()
  with redirect_stdout(out):
    rc = cgs.main(argv)
  return rc, out.getvalue()


class TestTimeout(unittest.TestCase):
  def test_matches_safety_tick_arithmetic(self):
    # 5 * (uint32_t)(1e6 / f) us
    self.assertEqual(cgs.timeout_us(83), 60240)
    self.assertEqual(cgs.timeout_us(33), 151515)
    self.assertEqual(cgs.timeout_us(50), 100000)


class TestScan(unittest.TestCase):
  def test_clean_drive_passes(self):
    with tempfile.TemporaryDirectory() as d:
      rc, out = run([write_csv(lka_drive(), d)])
    self.assertEqual(rc, 0, out)
    self.assertEqual(out.count("| PASS |"), 4, out)

  def test_gap_over_timeout_fails(self):
    # 5 missing frames of 0xAA at 83 Hz: a 6-period gap (72 ms) > 60.24 ms
    with tempfile.TemporaryDirectory() as d:
      path = write_csv(lka_drive(drop_aa=range(50, 55)), d)
      rc, out = run([path, "--json", os.path.join(d, "r.json")])
      rows = read_rows(os.path.join(d, "r.json"))
    self.assertEqual(rc, 1)
    self.assertEqual(rows["0xAA"]["verdict"], "FAIL")
    self.assertEqual(rows["0xAA"]["gaps_over_timeout"], 1)
    self.assertAlmostEqual(rows["0xAA"]["max_gap_ms"], 6000 / 83, places=0)
    self.assertEqual(rows["0x260"]["verdict"], "PASS")

  def test_gap_under_timeout_is_low_margin(self):
    # 3 missing frames: 4-period gap (48.2 ms) < 60.24 ms timeout, above a 70 % margin (42.2 ms)
    with tempfile.TemporaryDirectory() as d:
      path = write_csv(lka_drive(drop_aa=range(50, 53)), d)
      rc, out = run([path, "--margin", "0.7", "--json", os.path.join(d, "r.json")])
      rows = read_rows(os.path.join(d, "r.json"))
      rc_strict, _ = run([path, "--margin", "0.7", "--strict"])
    self.assertEqual(rows["0xAA"]["verdict"], "LOW MARGIN")
    self.assertEqual(rows["0xAA"]["gaps_over_timeout"], 0)
    self.assertEqual(rc, 0)
    self.assertEqual(rc_strict, 1)

  def test_exactly_five_periods_is_over_the_integer_timeout(self):
    # a true 5-period gap at 83 Hz is 60.241 ms; safety_tick's timeout truncates to 60.240 ms
    with tempfile.TemporaryDirectory() as d:
      rc, out = run([write_csv(lka_drive(drop_aa=range(50, 54)), d)])
    self.assertEqual(rc, 1)
    self.assertRegex(out, r"\| 0xAA \|.*\| FAIL \|")

  def test_uncertainty_counts_against_margin(self):
    # 2 missing frames: 36.1 ms gap; with 10 ms uncertainty above a 70 % margin (42.2 ms)
    with tempfile.TemporaryDirectory() as d:
      path = write_csv(lka_drive(drop_aa=range(50, 52)), d)
      _, out0 = run([path, "--margin", "0.7"])
      _, out10 = run([path, "--margin", "0.7", "--uncertainty-ms", "10"])
    self.assertRegex(out0, r"\| 0xAA \|.*\| PASS \|")
    self.assertRegex(out10, r"\| 0xAA \|.*\| LOW MARGIN \|")

  def test_missing_message(self):
    rows = [r for r in lka_drive() if r[2] != 0x226]
    with tempfile.TemporaryDirectory() as d:
      rc, out = run([write_csv(rows, d)])
    self.assertEqual(rc, 1)
    self.assertRegex(out, r"\| 0x226 \|.*\| MISSING \|")

  def test_other_bus_ignored(self):
    # 0xAA only on bus 2: the RX check on bus 0 sees nothing
    rows = [r for r in lka_drive() if r[2] != 0xAA] + periodic(0xAA, 83, bus=2)
    with tempfile.TemporaryDirectory() as d:
      _, out = run([write_csv(rows, d)])
    self.assertRegex(out, r"\| 0xAA \|.*\| MISSING \|")

  def test_file_boundary_not_counted(self):
    # two files 10 s apart: the gap between them is not a bus gap
    with tempfile.TemporaryDirectory() as d:
      a = write_csv(lka_drive(), d, "a.csv")
      b = write_csv([(t + 12.0, bus, addr) for t, bus, addr in lka_drive()], d, "b.csv")
      rc, out = run([a, b])
    self.assertEqual(rc, 0, out)

  def test_observed_rate(self):
    st = cgs.new_stats([(0xAA, 83)])
    cgs.scan([(round(t * 1e6), b, a) for t, b, a in periodic(0xAA, 80)], st)
    self.assertAlmostEqual(st[0xAA].observed_hz, 80, delta=0.5)

  def test_candump(self):
    with tempfile.TemporaryDirectory() as d:
      path = os.path.join(d, "drive.log")
      with open(path, "w") as f:
        for t, _, addr in sorted(lka_drive(drop_aa=range(50, 55))):
          f.write(f"({t + 1690000000:.6f}) can0 {addr:03X}#0011223344556677\n")
        f.write("(1690000001.000000) can1 0AA#00\n")  # other interface, ignored
      rc, out = run([path])
    self.assertEqual(rc, 1)
    self.assertRegex(out, r"\| 0xAA \|.*\| FAIL \|")

  def test_qlog_refused(self):
    with self.assertRaises(ValueError):
      list(cgs.read_rlog("/tmp/qlog.zst"))

  def test_custom_messages(self):
    rows = periodic(0x262, 33)
    with tempfile.TemporaryDirectory() as d:
      rc, out = run([write_csv(rows, d), "--msg", "0x262:33"])
    self.assertEqual(rc, 0)
    self.assertRegex(out, r"\| 0x262 \| 33 \|.*\| PASS \|")


class TestRlog(unittest.TestCase):
  def setUp(self):
    try:
      import capnp  # noqa: F401
      from opendbc.car.logreader import capnp_log
    except ImportError as e:
      self.skipTest(f"rlog support needs pycapnp and opendbc: {e}")
    self.capnp_log = capnp_log

  def test_rlog_batches(self):
    # pandad-style batches every 10 ms; 0xAA missing for 80 ms
    log = self.capnp_log
    with tempfile.TemporaryDirectory() as d:
      path = os.path.join(d, "rlog")
      with open(path, "wb") as f:
        for k in range(200):
          t_ms = k * 10
          frames = [(a, hz) for a, hz in cgs.VARIANTS["lka"] if not (a == 0xAA and 500 <= t_ms < 580)]
          ev = log.Event.new_message(logMonoTime=t_ms * 1_000_000)
          can = ev.init("can", len(frames))
          for i, (a, _) in enumerate(frames):
            can[i].address = a
            can[i].src = 0
            can[i].dat = b"\x00" * 8
          f.write(ev.to_bytes())
      rc, out = run([path])
    self.assertEqual(rc, 1)
    self.assertIn("uncertainty 10.0 ms", out)
    self.assertRegex(out, r"\| 0xAA \|.*\| 90\.0 \|.*\| FAIL \|")


class TestVariantsMatchOpendbc(unittest.TestCase):
  @unittest.skipUnless(os.path.exists(TOYOTA_H), "opendbc submodule not checked out")
  def test_frequencies(self):
    with open(TOYOTA_H) as f:
      src = f.read()
    declared = {int(a, 16): int(hz) for a, hz in re.findall(r"\{\s*(0x[0-9a-fA-F]+),\s*0,\s*8,\s*(\d+)U", src)}
    for variant, msgs in cgs.VARIANTS.items():
      for addr, hz in msgs:
        with self.subTest(variant=variant, addr=hex(addr)):
          self.assertEqual(declared.get(addr), hz)


if __name__ == "__main__":
  unittest.main()
