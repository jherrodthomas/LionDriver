#!/usr/bin/env python3
"""Tests for sync_requirements.py (WP-P-07 OI-9, TE-01-D4: fixed expected results for the parsing helpers).

The helpers that turn work-product table cells into trace items are tested on fixed inputs. The generated YAML must
stay inside the subset that check_trace.py's PyYAML-free loader reads. The generated files must equal a fresh
extraction (as --check does).

Run from the repository root:  python3 -m unittest discover -s assurance/trace/tools -p 'test_*.py' -v
Standard library only.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _load(name):
  spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
  mod = importlib.util.module_from_spec(spec)
  sys.modules[name] = mod
  spec.loader.exec_module(mod)
  return mod


sr = _load("sync_requirements")
ct = _load("check_trace")


class TestCells(unittest.TestCase):
  def test_cells_and_escaped_pipe(self):
    self.assertEqual(sr.cells("| a | b \\| c |  d  |"), ["a", "b \\| c", "d"])

  def test_quote(self):
    self.assertEqual(sr.quote('a  "b"\n c\\d'), '"a \\"b\\" c\\\\d"')

  def test_flow(self):
    self.assertEqual(sr.flow(["A", "B-1"]), "[A, B-1]")
    self.assertEqual(sr.flow([]), "[]")
    for bad in (["a b"], ["a,b"]):
      with self.assertRaises(ValueError):
        sr.flow(bad)


class TestExpandRefs(unittest.TestCase):
  def test_cases(self):
    cases = {
      "FSR-07.01, 07.03": (["FSR-07.01", "FSR-07.03"], []),
      "SG-01…03": (["SG-01", "SG-02", "SG-03"], []),
      "AOU-01…03, 09": (["AOU-01", "AOU-02", "AOU-03", "AOU-09"], []),
      "FSR-01.08–01.10": (["FSR-01.08", "FSR-01.09", "FSR-01.10"], []),
      "TSR-101; TSR-101": (["TSR-101"], []),
      "ISO 26262-8 §6, 07": ([], ["ISO 26262-8 §6", "07"]),
      "TSR-110, T-03, 2": (["TSR-110"], ["T-03", "2"]),
      "GAP-01, H-02": (["GAP-01", "H-02"], []),
    }
    for text, want in cases.items():
      self.assertEqual(sr.expand_refs(text), want, text)

  def test_range_padding(self):
    self.assertEqual(sr._range("SG", "08", "10"), ["SG-08", "SG-09", "SG-10"])
    self.assertEqual(sr._range("FSR", "02.08", "10"), ["FSR-02.08", "FSR-02.09", "FSR-02.10"])

  def test_parent_cell(self):
    self.assertEqual(sr._parent_cell("FSR-01.09 / TSR-501 (note)"), "FSR-01.09, TSR-501")
    self.assertEqual(sr._parent_cell("TSR-307(a), TSR-308"), "TSR-307, TSR-308")

  def test_swsr_status(self):
    self.assertEqual(sr._swsr_status("**Withdrawn** (2026)"), "withdrawn")
    self.assertEqual(sr._swsr_status("The envelope shall"), "proposed")


class TestSotif(unittest.TestCase):
  def test_ids(self):
    self.assertEqual(sr._ids("SH-01, SH-04", "SH"), ["SH-01", "SH-04"])
    self.assertEqual(sr._ids("Increases probability of SH-01…SH-03", "SH"), ["SH-01", "SH-02", "SH-03"])
    self.assertEqual(sr._ids("TC-10, TC-11", "TC"), ["TC-10", "TC-11"])
    self.assertEqual(sr._ids("SH-01", "H"), [])  # SH-01 is not H-01

  def test_rating(self):
    self.assertEqual(sr._rating("S3", "S"), 3)
    self.assertIsNone(sr._rating("—", "S"))
    self.assertIsNone(sr._rating("as linked SH", "C"))

  def test_items_from_the_work_products(self):
    items = {i["id"]: i for i in sr.sotif_items()}
    self.assertEqual(items["SH-01"]["shares_event"], ["H-01"])
    self.assertEqual(items["SH-09"]["shares_event"], [])  # a new hazard "with an effect like H-03/H-06"
    self.assertEqual(items["SH-07"]["status"], "withdrawn")
    self.assertNotIn("s", items["SH-12"])
    self.assertEqual(items["FI-14"]["parents"], ["SH-02", "SH-06"])
    self.assertEqual(items["TC-23"]["insufficiencies"], ["FI-14"])
    self.assertIn("FI-14", items["FM-03"]["parents"])
    self.assertEqual(items["FM-03"]["addresses"], ["SH-02", "SH-06"])
    evaluated = {t for r in sr.evaluation_rows() for t in r["tc"]}
    self.assertEqual({i for i in items if i.startswith("TC-")}, evaluated)  # every TC of §4 has a §5 row


class TestDelink(unittest.TestCase):
  def test_relative_link_becomes_repo_path(self):
    out = sr.delink("see [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md#3-x)", sr.SWSR_MD)
    self.assertEqual(out, "see WP-S-02 (assurance/03-system/WP-S-02-technical-safety-requirements.md#3-x)")

  def test_url_and_no_source(self):
    self.assertEqual(sr.delink("[gh](https://github.com/x)", sr.SWSR_MD), "gh (https://github.com/x)")
    self.assertEqual(sr.delink("[a](b.md)", None), "a (b.md)")


class TestRender(unittest.TestCase):
  def test_render_round_trips_through_subset_loader(self):
    items = [{"id": "SWSR-999", "kind": "swsr", "text": 'say "x" and [l](../03-system/a.md)', "asil": "B",
              "parents": ["TSR-101", "TSR-102"], "other_parents": False, "status": "proposed", "source": "WP-W-02",
              "ignored_key": "not in FIELD_ORDER"}]
    out = sr.render(items, "# header")
    self.assertTrue(out.startswith("# header\n\n- id: SWSR-999\n  kind: swsr\n"))
    back = ct._load_subset(out)
    self.assertEqual(back, [{"id": "SWSR-999", "kind": "swsr", "text": 'say "x" and l (assurance/03-system/a.md)',
                             "asil": "B", "parents": ["TSR-101", "TSR-102"], "other_parents": False,
                             "status": "proposed", "source": "WP-W-02"}])

  def test_generated_files_current_and_in_subset(self):
    for name, content in sr.expected_outputs().items():
      path = sr.ITEMS_DIR / name
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{name} out of date; run sync_requirements.py")
      self.assertTrue(ct._load_subset(content), name)


if __name__ == "__main__":
  unittest.main()
