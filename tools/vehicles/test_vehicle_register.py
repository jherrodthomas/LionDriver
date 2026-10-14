#!/usr/bin/env python3
"""Tests for vehicle_register.py."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vehicle_register as vr


class TestRegister(unittest.TestCase):
  def setUp(self):
    self.reg = vr.load()

  def test_alias_resolves_to_configuration(self):
    self.assertEqual(vr.config(self.reg, "AC-001")["id"], "CFG-001")

  def test_years_range_and_single(self):
    self.assertEqual(vr.years({"model_years": {"first": 2020, "last": 2022}}), "2020–2022")
    self.assertEqual(vr.years({"model_years": {"first": 2021, "last": 2021}}), "2021")

  def test_reference_label_names_codename_ids_and_years(self):
    label = vr.reference_label()
    for need in ("Corolla E210 · ZRE212 · US", "CFG-001", "AC-001", "2020–2022"):
      self.assertIn(need, label)

  def test_unconfirmed_value_is_marked(self):
    self.assertEqual(vr.val({"value": "L, LE", "confirmed": False}), "L, LE *(to confirm)*")
    self.assertEqual(vr.val({"min": 1, "max": 2, "confirmed": True}), "1–2")

  def test_old_name_pattern(self):
    for s in ("2020 Corolla LE", "2020 Toyota Corolla", "a 2020 Corolla."):
      self.assertRegex(s, vr.OLD_NAME)
    for s in ("Corolla E210 · ZRE212 · US", "2020 LE listing curb weight", "Toyota Corolla 2020-22"):
      self.assertNotRegex(s, vr.OLD_NAME)

  def test_committed_page_is_current_and_documents_agree(self):
    self.assertEqual((vr.ROOT / vr.PAGE).read_text(encoding="utf-8"), vr.render(self.reg))
    self.assertEqual(vr.check(vr.ROOT, self.reg), [])


if __name__ == "__main__":
  unittest.main()
