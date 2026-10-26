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


SOTIF = [
  {"id": "SH-01", "kind": "sotif-hazard", "text": "t", "functions": ["F-01"], "function_text": "F-01", "situations": "x",
   "shares_event": ["H-01"], "linked_text": "H-01", "status": "proposed", "source": "WP-C-05"},
  {"id": "SH-07", "kind": "sotif-hazard", "text": "not used", "functions": [], "function_text": "—", "situations": "—",
   "shares_event": [], "linked_text": "—", "status": "withdrawn", "source": "WP-C-05"},
  {"id": "FI-01", "kind": "functional-insufficiency", "text": "t", "fi_type": "P", "component": "x",
   "parents": ["SH-01"], "status": "proposed", "source": "WP-C-06"},
  {"id": "TC-01", "kind": "triggering-condition", "text": "t", "category": "x", "parents": ["SH-01"],
   "insufficiencies": ["FI-01"], "evaluation": "x", "status": "proposed", "source": "WP-C-06"},
  {"id": "FM-01", "kind": "functional-modification", "title": "t", "addresses": ["SH-01"], "parents": ["TC-01", "FI-01"],
   "gap_text": "—", "priority": "P1", "status": "proposed", "source": "WP-C-07"},
]


class TestSotifChecks(unittest.TestCase):
  def setUp(self):
    self.items = copy.deepcopy(GOOD + SOTIF)

  def test_good_set_is_clean(self):
    self.assertEqual(run(self.items), [])

  def test_k3_sotif_link_kinds(self):
    find(self.items, "FI-01")["parents"] = ["H-01"]
    self.assertIn("[K3] FI-01: parent H-01 is a hazard, not one of ['sotif-hazard']", run(self.items))
    self.items = copy.deepcopy(GOOD + SOTIF)
    find(self.items, "SH-01")["shares_event"] = ["SG-01"]
    self.assertIn("[K3] SH-01: shares_event SG-01 is a safety-goal, not one of ['hazard', 'hazardous-event']",
                  run(self.items))
    self.items = copy.deepcopy(GOOD + SOTIF)
    find(self.items, "TC-01")["insufficiencies"] = ["FI-09"]
    self.assertIn("[K3] TC-01: insufficiencies reference FI-09 does not resolve", run(self.items))

  def test_s1_hazard_without_insufficiency_or_condition(self):
    self.items.append(dict(find(self.items, "SH-01"), id="SH-02"))
    self.assertEqual(tags(run(self.items), "S1"),
                     ["[S1] SH-02: no functional insufficiency", "[S1] SH-02: no triggering condition"])

  def test_s1_withdrawn_hazard_needs_nothing(self):
    self.assertEqual(tags(run(self.items), "S1"), [])

  def test_s1_insufficiency_not_evaluated(self):
    find(self.items, "TC-01")["insufficiencies"] = []
    errs = tags(run(self.items), "S1")
    self.assertIn("[S1] FI-01: not evaluated with a triggering condition (WP-C-06 §5)", errs)
    self.assertIn("[S1] TC-01: SH-01 is not a parent of any of its insufficiencies []", errs)

  def test_s1_modification_named_by_no_row(self):
    find(self.items, "FM-01")["parents"] = []
    self.assertEqual(tags(run(self.items), "S1"), ["[S1] FM-01: named by no evaluation row of WP-C-06 §5"])


TSR = {"id": "TSR-603", "kind": "tsr", "text": "t", "asil": "QM", "parents": [], "parent_text": "x",
       "other_parents": True, "allocated_to": "SoC", "verification": "x", "baseline_impl": "see AIR-30",
       "status": "proposed", "source": "WP-S-02"}
AI = [
  {"id": "AIR-30", "kind": "ai-requirement", "text": "t", "category": "c", "component": "x", "parents": ["FM-01"],
   "parent_text": "FM-01; refined by TSR-603", "other_parents": False, "related_tsr": ["TSR-603"], "verification": "x",
   "baseline_impl": "x", "status": "proposed", "source": "WP-C-11"},
  {"id": "DSR-01", "kind": "dataset-requirement", "text": "t", "parents": ["AIR-30"], "parent_text": "AIR-30",
   "other_parents": False, "verification": "x", "baseline_impl": "x", "status": "proposed", "source": "WP-C-11"},
]


class TestAiChecks(unittest.TestCase):
  def setUp(self):
    self.items = copy.deepcopy(GOOD + SOTIF + [TSR] + AI)

  def test_good_set_is_clean(self):
    self.assertEqual(tags(run(self.items), "A1") + tags(run(self.items), "K3"), [])

  def test_k3_ai_link_kinds(self):
    find(self.items, "DSR-01")["parents"] = ["SH-01"]
    self.assertIn("[K3] DSR-01: parent SH-01 is a sotif-hazard, not one of ['ai-requirement', 'dataset-requirement']",
                  run(self.items))
    self.items = copy.deepcopy(GOOD + SOTIF + [TSR] + AI)
    find(self.items, "AIR-30")["related_tsr"] = ["FM-01"]
    self.assertIn("[K3] AIR-30: related_tsr FM-01 is a functional-modification, not one of ['tsr']", run(self.items))

  def test_a1_no_parent(self):
    find(self.items, "DSR-01")["parents"] = []
    self.assertEqual(tags(run(self.items), "A1"), ["[A1] DSR-01: no parent and names nothing it rests on"])
    find(self.items, "DSR-01")["other_parents"] = True
    self.assertEqual(tags(run(self.items), "A1"), [])

  def test_a1_tsr_names_an_air_that_does_not_name_it(self):
    find(self.items, "AIR-30")["related_tsr"] = []
    self.assertEqual(tags(run(self.items), "A1"),
                     ["[A1] TSR-603 names AIR-30, but AIR-30 does not list TSR-603 in related_tsr (WP-C-11 Parent column)"])


CS = [
  {"id": "TS-01", "kind": "threat-scenario", "text": "t", "stride": "S", "assets": "AS-01", "violated_property": "I",
   "damage_text": "DS-01", "gap_text": "GAP-01", "risk": 4, "treatment": "Reduce", "status": "proposed",
   "source": "WP-C-09"},
  {"id": "TS-02", "kind": "threat-scenario", "text": "t", "stride": "S", "assets": "AS-01", "violated_property": "I",
   "damage_text": "DS-01", "gap_text": "—", "risk": 2, "treatment": "Retain", "status": "proposed", "source": "WP-C-09"},
  {"id": "CSG-01", "kind": "cybersecurity-goal", "text": "t", "parents": ["TS-01"], "parent_text": "TS-01 (4)",
   "cal": "CAL 3", "protects": ["SG-01"], "rationale": "x", "status": "proposed", "source": "WP-C-10"},
  {"id": "CSR-011", "kind": "cybersecurity-requirement", "text": "t", "parents": ["CSG-01"],
   "concept_requirement": "CSR-C-01", "cal": "CAL 3", "other_parents": False, "allocated_to": "FW",
   "safety_relation": "TSR-603", "related_tsr": ["TSR-603"], "verification": "UT", "baseline_impl": "x",
   "status": "proposed", "source": "WP-S-07"},
]


class TestCsChecks(unittest.TestCase):
  def setUp(self):
    self.items = copy.deepcopy(GOOD + [TSR] + CS)

  def test_good_set_is_clean(self):
    self.assertEqual(tags(run(self.items), "C1") + tags(run(self.items), "K3"), [])

  def test_k3_cs_link_kinds(self):
    find(self.items, "CSG-01")["protects"] = ["HE-01.1"]
    self.assertIn("[K3] CSG-01: protects HE-01.1 is a hazardous-event, not one of ['safety-goal']", run(self.items))
    self.items = copy.deepcopy(GOOD + [TSR] + CS)
    find(self.items, "CSR-011")["parents"] = ["TS-01"]
    self.assertIn("[K3] CSR-011: parent TS-01 is a threat-scenario, not one of ['cybersecurity-goal']", run(self.items))

  def test_c1_reduced_threat_without_goal(self):
    find(self.items, "TS-02")["treatment"] = "Reduce / Retain"
    self.assertEqual(tags(run(self.items), "C1"),
                     ["[C1] TS-02: treated by 'Reduce / Retain' but no cybersecurity goal addresses it"])

  def test_c1_goal_without_requirement(self):
    find(self.items, "CSR-011")["parents"] = []
    errs = tags(run(self.items), "C1")
    self.assertIn("[C1] CSG-01: no cybersecurity requirement", errs)
    self.assertIn("[C1] CSR-011: no parent goal and names nothing it rests on", errs)

  def test_c1_unprotected_safety_goal(self):
    find(self.items, "CSG-01")["protects"] = []
    self.assertEqual(tags(run(self.items), "C1"), ["[C1] SG-01: protected by no cybersecurity goal (WP-C-10 §8)"])


SYS = {"id": "SYS-001", "kind": "system-requirement", "text": "t", "type": "P", "functions": ["F-01"], "criterion": "x",
       "verification": "LOG", "baseline_impl": "x", "allocated_to": "`host.controlsd`", "related_text": "TSR-603; SH-01",
       "related_tsr": ["TSR-603"], "related_items": ["SH-01"], "status": "proposed", "source": "WP-S-01"}


class TestSysChecks(unittest.TestCase):
  def setUp(self):
    self.items = copy.deepcopy(GOOD + SOTIF + [TSR, SYS])

  def test_good_set_is_clean(self):
    self.assertEqual(tags(run(self.items), "Q1") + tags(run(self.items), "K3"), [])

  def test_k3_related_items_kind(self):
    find(self.items, "SYS-001")["related_items"] = ["FM-01"]
    self.assertIn("[K3] SYS-001: related_items FM-01 is a functional-modification, not one of "
                  "['ai-requirement', 'sotif-hazard']", run(self.items))

  def test_q1_missing_attributes(self):
    it = find(self.items, "SYS-001")
    it["functions"], it["allocated_to"] = [], ""
    self.assertEqual(tags(run(self.items), "Q1"), ["[Q1] SYS-001: no function",
                                                   "[Q1] SYS-001: no allocation (WP-S-01 §10.1)"])


IFR = {"id": "IFR-01", "kind": "interface-requirement", "interface": "IX-01", "title": "t",
       "owners": ["Safety manager", "Cybersecurity manager"], "open_item": None, "review_ref": None,
       "status": "proposed", "source": "WP-P-11"}
REV = {"id": "REV-001", "kind": "review", "reviewed_objects": ["IFR-01"], "outcome": "accepted"}


class TestInterfaceChecks(unittest.TestCase):
  def errors(self, ifr, reviews=(), interfaces=frozenset({"IX-01"})):
    rep = ct.Report()
    by_id = ct.check_items(copy.deepcopy(GOOD) + [ifr], rep)
    ct.check_interfaces(by_id, list(reviews), set(interfaces), rep)
    return rep.errors

  def test_proposed_without_review_is_clean(self):
    self.assertEqual(self.errors(dict(IFR)), [])
    self.assertEqual(self.errors(dict(IFR, open_item="WP-V-02 OI-3")), [])

  def test_agreed_with_accepted_review_that_lists_it(self):
    self.assertEqual(self.errors(dict(IFR, status="agreed", review_ref="REV-001"), [REV]), [])

  def test_i1_agreed_without_review(self):
    self.assertEqual(self.errors(dict(IFR, status="agreed")),
                     ["[I1] IFR-01: agreed without a review_ref; an interface is agreed only through a recorded review"])

  def test_i1_agreed_with_review_that_is_missing_rejected_or_silent(self):
    self.assertEqual(self.errors(dict(IFR, status="agreed", review_ref="REV-002"), [REV]),
                     ["[I1] IFR-01: review_ref REV-002 is not a review record in case/reviews/reviews.yaml"])
    for rv in (dict(REV, outcome="rejected"), dict(REV, reviewed_objects=["G0"])):
      self.assertEqual(self.errors(dict(IFR, status="agreed", review_ref="REV-001"), [rv]),
                       ["[I1] IFR-01: agreed, but review REV-001 is not accepted or does not list IFR-01"])

  def test_i1_agreed_with_open_item(self):
    self.assertEqual(self.errors(dict(IFR, status="agreed", review_ref="REV-001", open_item="WP-V-02 OI-3"), [REV]),
                     ["[I1] IFR-01: agreed while open item WP-V-02 OI-3 is open"])

  def test_i1_interface_owners_and_status(self):
    self.assertEqual(self.errors(dict(IFR, interface="IX-99")), ["[I1] IFR-01: interface IX-99 is not in the process model"])
    self.assertEqual(self.errors(dict(IFR, interface="CON-01")), ["[I1] IFR-01: interface 'CON-01' is not an IX-nn"])
    self.assertEqual(self.errors(dict(IFR, owners=["Safety manager", "Safety manager"])),
                     ["[I1] IFR-01: owners must name two different roles"])
    self.assertEqual(self.errors(dict(IFR, status="verified")),
                     ["[I1] IFR-01: status 'verified' not in ['agreed', 'proposed', 'withdrawn']"])

  def test_i1_one_item_per_interface(self):
    rep = ct.Report()
    by_id = ct.check_items(copy.deepcopy(GOOD) + [dict(IFR), dict(IFR, id="IFR-02")], rep)
    ct.check_interfaces(by_id, [], {"IX-01"}, rep)
    self.assertEqual(rep.errors, ["[I1] IFR-02: interface IX-01 already has IFR-01"])

  def test_committed_items_match_the_process_model(self):
    ifrs = ct.load_yaml(ct.ITEMS_DIR / "ifr.yaml")
    self.assertEqual({x["interface"] for x in ifrs}, ct.interface_ids())


class TestVerificationLinks(unittest.TestCase):
  def setUp(self):
    self.items = copy.deepcopy(GOOD + SOTIF + [TSR])
    self.by_id = ct.check_items(self.items, ct.Report())

  def errors(self, links):
    rep = ct.Report()
    ct.check_verification_links(self.by_id, links, rep)
    return rep.errors

  def test_a_requirement_link_is_clean(self):
    self.assertEqual(self.errors([{"test": "t.py::C::test_a", "reqs": ["TSR-603", "FM-01"]}]), [])

  def test_k6_unknown_goal_withdrawn_and_empty(self):
    find(self.items, "TSR-603")["status"] = "withdrawn"
    errs = self.errors([{"test": "t", "reqs": ["TSR-999", "SG-01", "TSR-603"]}, {"test": "u", "reqs": []}])
    self.assertEqual(errs, ["[K6] t: links TSR-999, which does not exist",
                            "[K6] t: links SG-01, a safety-goal; only requirements may be linked (README §5)",
                            "[K6] t: links TSR-603, which is withdrawn", "[K6] u: links no requirement"])


class TestRepository(unittest.TestCase):
  def test_main_passes_on_repository(self):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      rc = ct.main([])
    self.assertEqual(rc, 0, out.getvalue()[-2000:])


if __name__ == "__main__":
  unittest.main()
