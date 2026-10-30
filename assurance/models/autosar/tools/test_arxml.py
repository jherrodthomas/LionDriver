#!/usr/bin/env python3
"""Tests of the AUTOSAR description: the readers, the layout arithmetic, the generator and the structural check.

    python3 tools/test_arxml.py
"""
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_arxml  # noqa: E402
import gen_arxml  # noqa: E402
import sources as src  # noqa: E402


class Layout(unittest.TestCase):
  def sig(self, start, length, little=False):
    return src.Signal("X", start, length, little, False, 1, 0, 0, 0, "")

  def test_intel_start_is_lsb(self):
    self.assertEqual(self.sig(48, 16, little=True).lsb_position(), 48)

  def test_motorola_within_one_byte(self):
    # COUNTER 6|6@0+ of STEERING_LKA: bits 6..1 of byte 0
    self.assertEqual(self.sig(6, 6).lsb_position(), 1)

  def test_motorola_across_bytes(self):
    # STEER_TORQUE_CMD 15|16@0- : MSB bit 7 of byte 1, LSB bit 0 of byte 2
    self.assertEqual(self.sig(15, 16).lsb_position(), 16)

  def test_wheel_speed_layout_matches_wp_s05(self):
    # WP-S-05 §11.1 S-06: wheel k in bytes 2k (bits 0-6, high) and 2k+1 (low): LSB at bit 8 * (2k + 1)
    dbc = src.read_dbc(src.reference().dbc)
    for k, w in enumerate(("FR", "FL", "RR", "RL")):
      s = dbc[0xAA].signal(f"WHEEL_SPEED_{w}")
      self.assertEqual((s.lsb_position(), s.length), (8 * (2 * k + 1), 15), w)


class Readers(unittest.TestCase):
  def test_reference_platform_and_dbc(self):
    r = src.reference()
    self.assertEqual((r.config_id, r.platform, r.dbc), ("CFG-001", "TOYOTA_COROLLA_TSS2", "toyota_nodsu_pt"))

  def test_safety_mode_reference_sets(self):
    m = src.safety_mode(**gen_arxml.CONFIG_FLAGS)
    self.assertEqual(sorted({r.address for r in m.rx}), [0xAA, 0x1D2, 0x1D3, 0x226, 0x260, 0x262])
    self.assertEqual(m.blocked_from_camera(), [0x191, 0x2E4, 0x343, 0x412])
    self.assertNotIn(0x411, {t.address for t in m.tx}, "the reference build refuses PCS_HUD (TSR-705 D-1)")
    self.assertEqual(m.rx_timeout_periods, 5)
    self.assertEqual(m.tx_arrival, {0x2E4: 50000, 0x343: 100000})

  def test_other_configurations_refused(self):
    with self.assertRaises(src.SourceError):
      src.safety_mode(secoc=True)

  def test_control_requests_expand_rows(self):
    codes = {r.code for r in src.control_requests()}
    self.assertTrue({0xb1, 0xb2, 0xf9, 0xfc, 0xdc, 0xf3} <= codes)

  def test_names_and_codes(self):
    self.assertEqual(gen_arxml.expand_names("WHEEL_SPEED_FR/FL, 0xAA"), "WHEEL_SPEED_FR WHEEL_SPEED_FL, 0xAA")
    self.assertEqual(gen_arxml.request_codes("(0xc5, 0xe5…0xe8, 0xf1)"), {0xc5, 0xe5, 0xe6, 0xe7, 0xe8, 0xf1})


class Generated(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.xml, cls.summary = gen_arxml.Builder().build()

  def test_committed_files_are_current(self):
    self.assertEqual(gen_arxml.OUT.read_text(encoding="utf-8"), self.xml)
    self.assertEqual(gen_arxml.SUMMARY.read_text(encoding="utf-8"), self.summary)

  def test_deterministic(self):
    self.assertEqual(gen_arxml.Builder().build()[0], self.xml)

  def test_says_what_it_is(self):
    self.assertIn("not an AUTOSAR implementation", self.xml)
    self.assertIn("LIONDRIVER_TOYOTA_CHECKSUM8", self.xml)
    self.assertNotIn("PROFILE_02", self.xml.replace("profile 2", ""))

  def test_every_hsi_signal_placed(self):
    for n in range(1, 30):
      self.assertIn(f"| S-{n:02d} |", self.summary)


class Check(unittest.TestCase):
  def run_check(self, text: str) -> list[str]:
    with tempfile.TemporaryDirectory() as d:
      p = Path(d) / "x.arxml"
      p.write_text(text, encoding="utf-8")
      return check_arxml.check(p)

  @classmethod
  def setUpClass(cls):
    cls.xml = gen_arxml.OUT.read_text(encoding="utf-8")

  def test_committed_file_passes(self):
    self.assertEqual(check_arxml.check(gen_arxml.OUT), [])

  def broken(self, old: str, new: str, count: int = 1) -> list[str]:
    self.assertIn(old, self.xml)
    return self.run_check(self.xml.replace(old, new, count))

  def codes(self, problems):
    return {p[:2] for p in problems}

  def test_a1(self):
    self.assertEqual(self.codes(self.run_check(self.xml[:-200])), {"A1"})

  def test_a2(self):
    self.assertIn("A2", self.codes(self.broken("<SHORT-NAME>BaseTypes<", "<SHORT-NAME>1BaseTypes<")))

  def test_a3(self):
    self.assertIn("A3", self.codes(self.broken("<SHORT-NAME>uint16<", "<SHORT-NAME>uint8<")))

  def test_a4(self):
    self.assertIn("A4", self.codes(self.broken('DEST="SW-BASE-TYPE">/LionDriver/BaseTypes/uint8<',
                                               'DEST="SW-BASE-TYPE">/LionDriver/BaseTypes/nope<')))
    self.assertIn("A4", self.codes(self.broken('DEST="SW-BASE-TYPE">/LionDriver/BaseTypes/uint8<',
                                               'DEST="SW-BASE-TYPE">/LionDriver/ImplementationDataTypes/uint8<')))

  def test_a5(self):
    m = re.search(r"<TARGET-R-PORT-REF DEST=\"R-PORT-PROTOTYPE\">(/LionDriver/SwComponentTypes/Ext_EPS/Rx_STEERING_LKA)<",
                  self.xml)
    self.assertIsNotNone(m)
    p = self.broken(f">{m.group(1)}<", ">/LionDriver/SwComponentTypes/Ext_EPS/Rx_STEERING_LTA<")
    self.assertIn("A5", self.codes(p))

  def test_a6(self):
    p = self.broken("<TARGET-COMPONENT-REF DEST=\"SW-COMPONENT-PROTOTYPE\">/LionDriver/SwComponentTypes/VehicleContext/Ext_EPS<",
                    "<TARGET-COMPONENT-REF DEST=\"SW-COMPONENT-PROTOTYPE\">/LionDriver/SwComponentTypes/VehicleContext/Ext_PCM<")
    self.assertIn("A6", self.codes(p))

  def test_a7(self):
    p = self.broken("<COMMUNICATION-DIRECTION>OUT</COMMUNICATION-DIRECTION>",
                    "<COMMUNICATION-DIRECTION>IN</COMMUNICATION-DIRECTION>")
    self.assertIn("A7", self.codes(p))

  def test_a8(self):
    self.assertIn("A8", self.codes(self.broken('GID="LionDriver.Nature"', 'GID="Other"')))


if __name__ == "__main__":
  unittest.main(verbosity=2)
