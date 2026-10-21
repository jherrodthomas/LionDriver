#!/usr/bin/env python3
"""Tests for check_fretish.py: the real file passes, the page is current, and each check catches its drift."""

import copy
import json
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_fretish as cf


class TestRealFile(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.data = yaml.safe_load(cf.SOURCE.read_text(encoding="utf-8"))
    cls.wp = cf.WP_S_02.read_text(encoding="utf-8")
    cls.formulas = json.loads(cf.FORMULAS.read_text(encoding="utf-8"))

  def errors(self, data=None, wp=None):
    return cf.check(data if data is not None else self.data, wp if wp is not None else self.wp)

  def mutated(self, rid, **changes):
    data = copy.deepcopy(self.data)
    req = next(r for r in data["requirements"] if r["id"] == rid)
    req.update(changes)
    return data

  def test_passes(self):
    self.assertEqual(self.errors(), [])

  def test_committed_page_current(self):
    self.assertEqual(cf.OUTPUT.read_text(encoding="utf-8"), cf.build(self.data, self.formulas), "stale; run check_fretish.py")

  def test_formulas_current(self):
    self.assertEqual(cf.check_formulas(self.data, self.formulas), [])

  def test_changed_sentence_needs_new_formula(self):
    data = self.mutated("FR-307a", fretish="upon authority_granted & !hb_engaged the envelope shall within 20 ticks satisfy !authority_granted")
    self.assertTrue(any("FR-307a" in e and "fret_formalize" in e for e in cf.check_formulas(data, self.formulas)))

  def test_reworded_tsr_fails(self):
    wp = self.wp.replace("continuously for 0.3 s while authority is granted", "continuously for 0.2 s while authority is granted", 1)
    self.assertTrue(any("FR-307a" in e and "no longer" in e for e in self.errors(wp=wp)))

  def test_unknown_variable_fails(self):
    data = self.mutated("FR-101", fretish="whenever lka_frame_rx the envelope shall immediately satisfy dropped")
    self.assertTrue(any("dropped is not in the glossary" in e for e in self.errors(data)))

  def test_unused_glossary_entry_fails(self):
    data = copy.deepcopy(self.data)
    data["glossary"].append({"name": "spare", "type": "bool", "meaning": "x", "code": "x"})
    self.assertIn("glossary: spare is not used", self.errors(data))

  def test_keyword_variable_fails(self):
    data = copy.deepcopy(self.data)
    data["glossary"].append({"name": "next", "type": "bool", "meaning": "x", "code": "x"})
    self.assertTrue(any("next is a FRET keyword" in e for e in self.errors(data)))

  def test_bad_timing_fails(self):
    data = self.mutated("FR-110", fretish="whenever lat_authority the envelope shall within 10 frames satisfy !lat_authority")
    self.assertTrue(any("FR-110" in e and "timing" in e for e in self.errors(data)))

  def test_unbalanced_expression_fails(self):
    data = self.mutated("FR-101", fretish="whenever (lka_frame_rx the envelope shall immediately satisfy lka_frame_rejected")
    self.assertTrue(any(e.startswith("FR-101:") for e in self.errors(data)))

  def test_missing_finding_fails(self):
    data = self.mutated("FR-101", findings=["FF-99"])
    self.assertTrue(any("FF-99 does not exist" in e for e in self.errors(data)))


class TestParser(unittest.TestCase):
  def test_scope_condition_timing(self):
    names, modes = cf.parse_fretish("in car_safety_mode mode, whenever persisted(31, !heartbeat_rx) "
                                    "the envelope shall within 10 ticks satisfy !authority_any")
    self.assertEqual(names, {"heartbeat_rx", "authority_any"})
    self.assertEqual(modes, {"car_safety_mode"})

  def test_unknown_function_rejected(self):
    with self.assertRaisesRegex(cf.CheckError, "unknown function"):
      cf.parse_fretish("upon spike(x) the envelope shall immediately satisfy y")

  def test_component_required(self):
    with self.assertRaisesRegex(cf.CheckError, "shall"):
      cf.parse_fretish("upon x the eps shall immediately satisfy y")


if __name__ == "__main__":
  unittest.main()
