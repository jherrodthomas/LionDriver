#!/usr/bin/env python3
"""Tests for check_trace.py (WP-P-07 OI-9, TE-01-D4: known-bad inputs and fixed expected results).

Each check that works on item data has a minimal correct item set that must pass and a one-field change that must
fail it. The PyYAML-free loader is checked against PyYAML on the real item files when PyYAML is installed.

Run from the repository root:  python3 -m unittest discover -s assurance/trace/tools -p 'test_*.py' -v
Standard library only.
"""
from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # check_trace imports sync_requirements by name
_spec = importlib.util.spec_from_file_location("check_trace", HERE / "check_trace.py")
ct = importlib.util.module_from_spec(_spec)
sys.modules["check_trace"] = ct
_spec.loader.exec_module(ct)

GOOD = [
  {"id": "H-01", "kind": "hazard", "title": "t", "functions": ["F-01"], "status": "proposed", "source": "WP-C-03"},
  {"id": "HE-01.1", "kind": "hazardous-event", "parents": ["H-01"], "situation": "s", "effect": "e", "s": 3, "e": 4,
   "c": 3, "asil": "D", "aou_flag": False, "aou_dependency": [], "asil_if_aou_fails": None, "status": "proposed",
   "source": "WP-C-03"},
  {"id": "HE-01.2", "kind": "hazardous-event", "parents": ["H-01"], "situation": "s", "effect": "e", "s": 2, "e": 3,
   "c": 2, "asil": "A", "aou_flag": True, "aou_dependency": ["AOU-01"], "asil_if_aou_fails": "B",
   "status": "proposed", "source": "WP-C-03"},
  {"id": "SG-01", "kind": "safety-goal", "text": "t", "type": "x", "asil": "D", "asil_if_aou_fails": None,
   "aou_dependency": [], "parents": ["HE-01.1", "HE-01.2"], "safe_state": "x", "ftti_ms": 100, "ftti_text": "x",
   "status": "proposed", "source": "WP-C-03"},
  {"id": "AOU-01", "kind": "aou", "text": "t", "credited_in": "x", "verification_approach": "x", "aou_status": "x",
   "status": "proposed", "source": "WP-C-01"},
]


def run(items):
  rep = ct.Report()
  by_id = ct.check_items(items, rep)
  ct.check_links(by_id, rep)
  return rep.errors


def tags(errors, tag):
  return [e for e in errors if e.startswith(f"[{tag}]")]


def find(items, iid):
  return next(x for x in items if x["id"] == iid)


class TestHelpers(unittest.TestCase):
  def test_risk_graph(self):
    for (s, e, c), want in {(3, 4, 3): "D", (3, 4, 2): "C", (3, 3, 2): "B", (2, 3, 2): "A", (1, 2, 3): "QM",
                            (0, 4, 3): "QM", (3, 0, 3): "QM", (3, 4, 0): "QM"}.items():
      self.assertEqual(ct.risk_graph(s, e, c), want, (s, e, c))

  def test_expand_he_list(self):
    self.assertEqual(ct.expand_he_list("HE-01.1–01.3, HE-02.2"), ["HE-01.1", "HE-01.2", "HE-01.3", "HE-02.2"])
    self.assertEqual(ct.expand_he_list("HE-03.2-03.3"), ["HE-03.2", "HE-03.3"])
    with self.assertRaises(ValueError):
      ct.expand_he_list("HE-01.1–02.2")

  def test_expand_fsr_refs(self):
    # WP-C-04 writes ranges as "FSR-02.06…02.09"
    self.assertEqual(ct.expand_fsr_refs("see FSR-02.06…02.08 and FSR-07.09"),
                     ["FSR-02.06", "FSR-02.07", "FSR-02.08", "FSR-07.09"])
    self.assertEqual(ct.expand_fsr_refs("FSR-01.05 … 01.06"), ["FSR-01.05", "FSR-01.06"])


class TestLoader(unittest.TestCase):
  def test_subset_scalars(self):
    text = ('# c\n- id: "X-1"\n  n: 3\n  neg: -2\n  t: true\n  f: false\n  z: null\n  l: [A, B]\n  e: []\n'
            '  q: "a \\"b\\" c"\n  bare: word\n- id: Y\n')
    items = ct._load_subset(text)
    self.assertEqual(items[0], {"id": "X-1", "n": 3, "neg": -2, "t": True, "f": False, "z": None, "l": ["A", "B"],
                                "e": [], "q": 'a "b" c', "bare": "word"})
    self.assertEqual(items[1], {"id": "Y"})

  def test_subset_rejects(self):
    for bad in ("  key: before item\n", "- id: X\n    nested: 1\n", '- id: "unterminated\n', "- l: [a, b\n"):
      with self.assertRaises(ValueError, msg=bad):
        ct._load_subset(bad)

  def test_subset_matches_pyyaml_on_items(self):
    try:
      import yaml
    except ImportError:
      self.skipTest("PyYAML not installed")
    paths = sorted(ct.ITEMS_DIR.glob("*.yaml"))
    self.assertTrue(paths)
    for p in paths:
      text = p.read_text(encoding="utf-8")
      self.assertEqual(ct._load_subset(text), yaml.safe_load(text) or [], p.name)


class TestItemChecks(unittest.TestCase):
  def setUp(self):
    self.items = copy.deepcopy(GOOD)

  def test_good_set_is_clean(self):
    self.assertEqual(run(self.items), [])

  def test_k1_unknown_kind_and_missing_key(self):
    find(self.items, "H-01")["kind"] = "risk"
    self.assertTrue(any("unknown kind" in e for e in tags(run(self.items), "K1")))
    self.items = copy.deepcopy(GOOD)
    del find(self.items, "SG-01")["safe_state"]
    self.assertEqual(tags(run(self.items), "K1"), ["[K1] SG-01: missing key 'safe_state'"])

  def test_k1_status(self):
    find(self.items, "SG-01")["status"] = "approved"
    self.assertEqual(len(tags(run(self.items), "K1")), 1)

  def test_k2_bad_and_duplicate_id(self):
    self.items.append(dict(find(self.items, "AOU-01"), id="AOU-1"))
    self.assertEqual(tags(run(self.items), "K2"), ["[K2] bad ID 'AOU-1'"])
    self.items[-1]["id"] = "AOU-01"
    self.assertEqual(tags(run(self.items), "K2"), ["[K2] duplicate ID AOU-01"])

  def test_k3_unresolved_and_wrong_kind_parent(self):
    find(self.items, "HE-01.1")["parents"] = ["H-09"]
    self.assertIn("[K3] HE-01.1: parents reference H-09 does not resolve", run(self.items))
    self.items = copy.deepcopy(GOOD)
    find(self.items, "HE-01.1")["parents"] = ["H-01", "AOU-01"]
    self.assertIn("[K3] HE-01.1: parent AOU-01 is not a hazard", run(self.items))

  def test_k3_aou_dependency_kind(self):
    find(self.items, "HE-01.2")["aou_dependency"] = ["H-01"]
    self.assertIn("[K3] HE-01.2: aou_dependency H-01 is not an AOU", run(self.items))

  def test_k3_bad_function_and_unknown_gap(self):
    find(self.items, "H-01")["functions"] = ["F-1"]
    self.assertIn("[K3] H-01: bad function ID F-1", run(self.items))
    self.items = copy.deepcopy(GOOD)
    find(self.items, "HE-01.1")["parents"] = ["H-01", "GAP-99"]
    self.assertIn("[K3] HE-01.1: parent GAP-99 is not in the gap assessment", run(self.items))

  def test_r1_asil_against_risk_graph(self):
    find(self.items, "HE-01.1")["asil"] = "C"
    self.assertEqual(tags(run(self.items), "R1"), ["[R1] HE-01.1: asil C but S3 E4 C3 gives D"])

  def test_r2_goal_asil_is_highest_source(self):
    find(self.items, "SG-01")["asil"] = "C"
    self.assertEqual(tags(run(self.items), "R2"), ["[R2] SG-01: asil C but highest source HE ASIL is D"])

  def test_r3_asil_if_aou_fails(self):
    find(self.items, "HE-01.2")["asil_if_aou_fails"] = "QM"
    self.assertEqual(len(tags(run(self.items), "R3")), 1)
    self.items = copy.deepcopy(GOOD)
    find(self.items, "HE-01.2")["aou_dependency"] = []
    self.assertIn("[R3] HE-01.2: asil_if_aou_fails without aou_dependency", run(self.items))

  def test_r4_hazard_without_event(self):
    self.items.append(dict(find(self.items, "H-01"), id="H-02"))
    self.assertEqual(tags(run(self.items), "R4"), ["[R4] H-02: no hazardous event"])

  def test_k12_event_without_goal(self):
    find(self.items, "SG-01")["parents"] = ["HE-01.1"]
    self.assertEqual(tags(run(self.items), "K12"),
                     ["[K12] HE-01.2: not linked to a safety goal and no sg_exempt_reason"])
    find(self.items, "HE-01.2")["sg_exempt_reason"] = "covered elsewhere"
    self.assertEqual(tags(run(self.items), "K12"), [])


class TestRepository(unittest.TestCase):
  def test_main_passes_on_repository(self):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      rc = ct.main([])
    self.assertEqual(rc, 0, out.getvalue()[-2000:])


if __name__ == "__main__":
  unittest.main()
