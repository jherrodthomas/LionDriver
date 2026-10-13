#!/usr/bin/env python3
"""Tests for trace_map.py."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trace_map as tm


def model(items: list[dict], specs: dict | None = None, docs: dict | None = None) -> tm.Model:
  by_id = {it["id"]: it for it in items}
  ids: dict[str, set[str]] = {}
  for it in items:
    ids.setdefault(tm.YAML_KIND[it["kind"]], set()).add(it["id"])
  in_trace = set(ids)
  for kind, found in (docs or {}).items():
    ids.setdefault(kind, set()).update(found)
  return tm.Model(by_id, ids, in_trace, specs or {})


class TestRefs(unittest.TestCase):
  KNOWN = {"TSR-101", "TSR-102", "TSR-103", "SWSR-101", "SWSR-102", "SWSR-103", "SWSR-103a", "FSR-01.01", "FSR-02.01",
           "FSR-03.01"}

  def test_prefixed_ids_and_ranges(self):
    self.assertEqual(tm.refs_in("FSR-01.01; TSR-101…103", None, self.KNOWN), {"FSR-01.01", "TSR-101", "TSR-102", "TSR-103"})

  def test_bare_numbers_in_typed_column(self):
    self.assertEqual(tm.refs_in("101–102, 103a", "SWSR", self.KNOWN), {"SWSR-101", "SWSR-102", "SWSR-103a"})

  def test_bare_numbers_ignored_without_typed_column(self):
    self.assertEqual(tm.refs_in("at 101 km/h", None, self.KNOWN), set())

  def test_fsr_wildcard_range(self):
    self.assertEqual(tm.refs_in("FSR-01.xx…02.xx", None, self.KNOWN), {"FSR-01.01", "FSR-02.01"})

  def test_hazardous_event_wildcard(self):
    known = {"HE-01.1", "HE-01.2", "HE-02.1"}
    self.assertEqual(tm.refs_in("sets the C-class for HE-01.x", None, known), {"HE-01.1", "HE-01.2"})

  def test_header_kind(self):
    self.assertEqual(tm.header_kind("SWSRs"), "SWSR")
    self.assertIsNone(tm.header_kind("Parent TSR (WP-S-02) / FSR"))  # prefixed IDs there; bare numbers not read


class TestCoverage(unittest.TestCase):
  ITEMS = [
    {"id": "SG-01", "kind": "safety-goal"},
    {"id": "SG-02", "kind": "safety-goal"},
    {"id": "FSR-01.01", "kind": "fsr", "parents": ["SG-01"], "text": ""},
    {"id": "TSR-101", "kind": "tsr", "parents": ["FSR-01.01"], "allocated_to": "P-SW"},
    {"id": "TSR-801", "kind": "tsr", "parents": ["FSR-01.01"], "allocated_to": "OPS"},
    {"id": "SWSR-101", "kind": "swsr", "parents": ["TSR-101"]},
  ]

  def test_derivation_counts_parents_with_a_child(self):
    done, total, missing = tm.derivation(model(self.ITEMS), "SG", "FSR", None)
    self.assertEqual((done, total, missing), (1, 2, ["SG-02"]))

  def test_derivation_only_over_allocated_parents(self):
    self.assertEqual(tm.derivation(model(self.ITEMS), "TSR", "SWSR", tm.ct.SW_ALLOC)[:2], (1, 1))

  def test_derivation_untraced_kind(self):
    self.assertEqual(tm.derivation(model(self.ITEMS), "SH", "FM", None), (0, 0, []))

  def test_verification_leaves_out_operation_tsrs(self):
    m = model(self.ITEMS, specs={"VS-SQ": {"VS-SQ-01": {"TSR-101"}}})
    self.assertEqual(tm.verified_by(m, "SYS5", "TSR"), (1, 1, []))

  def test_status(self):
    self.assertEqual([tm.status_of(*x) for x in ((2, 2), (1, 2), (0, 2), (0, 0))], ["full", "partial", "none", "untraced"])

  def test_dangling_reference(self):
    m = model(self.ITEMS, specs={"VS-VAL": {"VS-VAL-01": {"SG-01", "SG-09"}}})
    self.assertEqual(tm.dangling(m), {"VS-VAL-01": ["SG-09"]})

  def test_document_only_kind_counted_not_linked(self):
    m = model(self.ITEMS, docs={"SH": {"SH-01", "SH-02"}})
    self.assertEqual(tm.left_status(m, tm.level("SYS1")), "some")
    self.assertIn("SH 2*", tm.left_label(m, tm.level("SYS1")))


class TestCommittedMap(unittest.TestCase):
  def test_v_model_pairs_every_level(self):
    lefts = {lv.key for lv in tm.LEFT}
    rights = {lv.key for lv in tm.RIGHT}
    self.assertEqual({p[0] for p in tm.PAIRS}, lefts)
    self.assertEqual({p[1] for p in tm.PAIRS}, rights)

  def test_committed_map_is_current(self):
    m = tm.build()
    self.assertEqual(tm.OUT.read_text(encoding="utf-8"), tm.render(m))
    self.assertEqual(tm.FIG.read_text(encoding="utf-8"), tm.svg_v_model(m))

  def test_svg_has_every_level_once(self):
    svg = tm.svg_v_model(tm.build())
    for lv in tm.LEFT + tm.RIGHT:
      self.assertEqual(svg.count(f">{lv.process}</text>"), 1, lv.process)


if __name__ == "__main__":
  unittest.main()
