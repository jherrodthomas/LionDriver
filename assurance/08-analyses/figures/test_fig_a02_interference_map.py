#!/usr/bin/env python3
"""Tests for fig_a02_interference_map.py: parse WP-A-02 §2/§4–§8, committed SVG current, parser rejects drift."""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_a02_interference_map as fm


class TestRealDocument(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fm.SOURCE.read_text(encoding="utf-8")
    cls.model = fm.parse(cls.md)
    cls.groups = fm.groups(cls.model)

  def test_all_channels(self):
    ids = sorted(i for v in self.model.sections.values() for i in v)
    want = ([f"FFI-SP-{i:02d}" for i in range(1, 6)] + [f"FFI-TM-{i:02d}" for i in range(1, 8)]
            + [f"FFI-CM-{i:02d}" for i in range(1, 20)])
    self.assertEqual(ids, sorted(want))

  def test_groups(self):
    g = {k: fm.compress(v) for k, v in self.groups.items()}
    self.assertEqual(g["cmds"], "CM-06…11, 13, 14")
    self.assertEqual(g["boot"], "CM-12")
    self.assertEqual(g["tm_dev"], "TM-06, -07")

  def test_verdicts(self):
    got = {v.level: (v.base, v.base_at, v.latest) for v in self.model.verdicts}
    self.assertEqual(got["L-MCU temporal"], ("not shown", "8b8c6ae", "partially shown"))
    self.assertEqual(got["L-DEV boot control"], ("not shown", None, "not shown"))

  def test_committed_output_current(self):
    path = fm.HERE / fm.OUTPUT
    self.assertTrue(path.exists())
    self.assertEqual(path.read_text(encoding="utf-8"), fm.build(), "stale; run fig_a02_interference_map.py")

  def test_svg_parses_and_has_title(self):
    root = ET.fromstring(fm.build())
    self.assertIsNotNone(root.find("{http://www.w3.org/2000/svg}title"))

  def test_changed_verdict_row_rejected(self):
    md = self.md.replace("| L-DEV boot control | **Not shown** |", "| L-DEV boot control | **Partially shown** |")
    with self.assertRaisesRegex(fm.ParseError, "boot control"):
      fm.parse(md)

  def test_unknown_partition_row_rejected(self):
    md = self.md.replace("| Fan, sound, LED", "| Watchdog kicker | x | y | **QM** | z |\n| Fan, sound, LED", 1)
    with self.assertRaisesRegex(fm.ParseError, "PARTITIONS"):
      fm.parse(md)


class TestHelpers(unittest.TestCase):
  def test_id_list(self):
    self.assertEqual(fm.id_list("FFI-CM-01, -02, -11, FFI-TM-06"),
                     ["FFI-CM-01", "FFI-CM-02", "FFI-CM-11", "FFI-TM-06"])
    self.assertEqual(fm.id_list("FFI-CM-06…10"), [f"FFI-CM-{i:02d}" for i in range(6, 11)])
    self.assertEqual(fm.id_list("FFI-CM-17…-19"), ["FFI-CM-17", "FFI-CM-18", "FFI-CM-19"])

  def test_compress(self):
    self.assertEqual(fm.compress(["FFI-SP-01", "FFI-SP-04"]), "SP-01, -04")
    self.assertEqual(fm.compress([f"FFI-CM-{i:02d}" for i in (1, 2, 3, 4, 5)]), "CM-01…05")
    with self.assertRaises(fm.ParseError):
      fm.compress([])

  def test_unknown_verdict_rejected(self):
    with self.assertRaises(fm.ParseError):
      fm.verdict_key("**Probably fine**")


if __name__ == "__main__":
  unittest.main()
