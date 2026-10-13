#!/usr/bin/env python3
"""Tests for check_state_machines.py (proposed TL-28, TE-01 §5: known-bad records and golden output).

Each check S1-S6 has a record that must trigger it and a minimal change that must clear it, so that a check which
stops firing, or fires on a correct record, fails here. The generated WP-W-05 §5 table and diagram are compared with
fixed expected text. The PyYAML-free loader is compared with PyYAML on the real records when PyYAML is installed.

Run from the repository root:  python3 -m unittest discover -s assurance/trace/tools -p 'test_*.py' -v
Standard library only.
"""
from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("check_state_machines", HERE / "check_state_machines.py")
csm = importlib.util.module_from_spec(_spec)
sys.modules["check_state_machines"] = csm
_spec.loader.exec_module(csm)

# WP-W-02 records as swsr_records() returns them (text, baseline, withdrawn)
SW = {
  "SWSR-1": {"text": "The envelope shall set authority on a rising edge.", "baseline": "Impl: a.h:1", "withdrawn": False},
  "SWSR-2": {"text": "The envelope shall clear authority on X.", "baseline": "Partial: a.h:2", "withdrawn": False},
  "SWSR-3": {"text": "The envelope shall clear authority on Y.", "baseline": "Not impl", "withdrawn": False},
  "SWSR-4": {"text": "The envelope shall revoke authority on Z.", "baseline": "Not impl", "withdrawn": False},
  "SWSR-5": {"text": "The envelope shall clear authority on W.", "baseline": "Impl", "withdrawn": True},
}

GOOD = {
  "machine": "SM-TEST",
  "initial": "NOT_ALLOWED",
  "states": ["NOT_ALLOWED", "ALLOWED"],
  "transitions": [
    {"id": "T1", "from": "NOT_ALLOWED", "event": "e1", "guard": "g and h", "action": "set", "to": "ALLOWED",
     "build": "all", "swsr": ["SWSR-1"], "exclusive_with": ["T8"], "code": "a.h:1"},
    {"id": "T8", "from": "NOT_ALLOWED", "event": "e1", "guard": "not g | h", "action": "none", "to": "NOT_ALLOWED",
     "build": "all", "swsr": ["SWSR-1"], "exclusive_with": ["T1"], "code": "a.h:1"},
    {"id": "T2", "from": "ALLOWED", "event": "e2", "guard": "", "action": "clear", "to": "NOT_ALLOWED",
     "build": "all", "swsr": ["SWSR-2"], "code": "a.h:2"},
    {"id": "T3", "from": "ALLOWED", "event": "e3", "guard": "", "action": "clear", "to": "NOT_ALLOWED",
     "build": "all", "swsr": ["SWSR-3"], "code": "not implemented"},
    {"id": "T7", "from": "any", "event": "reset", "guard": "", "action": "clear", "to": "NOT_ALLOWED",
     "build": "all", "swsr": ["SWSR-1"], "code": "a.h:3"},
  ],
  "s6_exempt": [{"swsr": "SWSR-4", "reason": "acts after revocation"}],
}


def run(sm, sw=SW):
  return csm.check(sm, sw)


def ids(msgs, prefix):
  return [m for m in msgs if m.startswith(prefix)]


class TestChecks(unittest.TestCase):
  def setUp(self):
    self.sm = copy.deepcopy(GOOD)

  def test_good_record_is_clean(self):
    errors, warnings = run(self.sm)
    self.assertEqual(errors, [])
    self.assertEqual(warnings, [])

  def test_s1_undeclared_state(self):
    self.sm["transitions"][2]["to"] = "LIMBO"
    errors, _ = run(self.sm)
    self.assertEqual(len(ids(errors, "S1")), 1)
    self.assertIn("LIMBO", errors[0])

  def test_s1_undeclared_source_in_list(self):
    self.sm["transitions"][2]["from"] = "ALLOWED, LIMBO"
    self.assertEqual(len(ids(run(self.sm)[0], "S1")), 1)

  def test_s1_placeholders_allowed(self):
    self.sm["transitions"].append({"id": "T9", "from": "any", "event": "e9", "action": "none", "to": "same",
                                   "build": "all", "swsr": ["SWSR-1"], "code": "a.h:9"})
    self.assertEqual(run(self.sm)[0], [])

  def test_s2_unreachable_state(self):
    self.sm["states"].append("ISLAND")
    errors, _ = run(self.sm)
    self.assertEqual(ids(errors, "S2"), ["S2 SM-TEST: state ISLAND unreachable from NOT_ALLOWED"])

  def test_s2_reachable_only_through_placeholder_m(self):
    self.sm["states"].append("ISLAND")
    self.sm["transitions"].append({"id": "T9", "from": "NOT_ALLOWED", "event": "e9", "action": "set", "to": "m",
                                   "build": "all", "swsr": ["SWSR-1"], "code": "a.h:9"})
    self.assertEqual(ids(run(self.sm)[0], "S2"), [])

  def test_s3_overlap_without_exclusive(self):
    for t in self.sm["transitions"][:2]:
      del t["exclusive_with"]
    errors, _ = run(self.sm)
    self.assertEqual(len(ids(errors, "S3")), 1)
    self.assertIn("T1 and T8", errors[0])

  def test_s3_exclusive_declared_one_way_only(self):
    del self.sm["transitions"][1]["exclusive_with"]
    self.assertEqual(len(ids(run(self.sm)[0], "S3")), 1)

  def test_s3_overlap_via_any_source(self):
    self.sm["transitions"][4]["event"] = "e2"  # T7 from any shares source ALLOWED and event e2 with T2
    errors, _ = run(self.sm)
    self.assertEqual(len(ids(errors, "S3")), 1)
    self.assertIn("T2 and T7", errors[0])

  def test_s3_disjoint_builds_not_flagged(self):
    for t, b in zip(self.sm["transitions"][:2], ("reference", "upstream")):
      del t["exclusive_with"]
      t["build"] = b
    self.assertEqual(ids(run(self.sm)[0], "S3"), [])

  def test_s3_build_all_overlaps_reference(self):
    del self.sm["transitions"][0]["exclusive_with"]
    del self.sm["transitions"][1]["exclusive_with"]
    self.sm["transitions"][1]["build"] = "reference"
    self.assertEqual(len(ids(run(self.sm)[0], "S3")), 1)

  def test_s4_no_swsr(self):
    self.sm["transitions"][2]["swsr"] = []
    self.assertEqual(ids(run(self.sm)[0], "S4"), ["S4 SM-TEST T2: no SWSR reference"])

  def test_s7_gap_recorded_is_finding_not_error(self):
    self.sm["transitions"][2]["swsr"] = []
    self.sm["transitions"][2]["gap"] = "no host SWSR"
    errors, warnings = run(self.sm)
    self.assertEqual(ids(errors, "S4"), [])
    self.assertEqual(ids(warnings, "S7"), ["S7 SM-TEST T2: no SWSR (gap: no host SWSR)"])

  def test_s7_empty_gap_is_still_s4(self):
    self.sm["transitions"][2]["swsr"] = []
    self.sm["transitions"][2]["gap"] = ""
    errors, warnings = run(self.sm)
    self.assertEqual(ids(errors, "S4"), ["S4 SM-TEST T2: no SWSR reference"])
    self.assertEqual(ids(warnings, "S7"), [])

  def test_s4_unknown_swsr(self):
    self.sm["transitions"][2]["swsr"] = ["SWSR-99"]
    self.assertEqual(ids(run(self.sm)[0], "S4"), ["S4 SM-TEST T2: SWSR-99 not in swsr.yaml"])

  def test_s5_not_implemented_but_baseline_implemented(self):
    self.sm["transitions"][2]["code"] = "not implemented"  # T2 cites SWSR-2 (Partial)
    _, warnings = run(self.sm)
    self.assertEqual(len(ids(warnings, "S5")), 1)
    self.assertIn("T2: code says not implemented, WP-W-02 says Partial", warnings[0])

  def test_s5_code_cited_but_baseline_not_implemented(self):
    self.sm["transitions"][3]["code"] = "a.h:3"  # T3 cites SWSR-3 (Not impl)
    _, warnings = run(self.sm)
    self.assertEqual(len(ids(warnings, "S5")), 1)
    self.assertIn("T3: code cited", warnings[0])

  def test_s5_is_a_finding_not_an_error(self):
    self.sm["transitions"][3]["code"] = "a.h:3"
    self.assertEqual(run(self.sm)[0], [])

  def test_s6_revoking_swsr_without_transition(self):
    self.sm["transitions"].pop(3)  # T3 was the only transition for SWSR-3
    _, warnings = run(self.sm)
    self.assertEqual(ids(warnings, "S6"), ["S6 SM-TEST: SWSR-3 requires clearing authority but no transition "
                                           "realises it"])

  def test_s6_revoke_wording_and_exemption(self):
    self.sm["s6_exempt"] = []
    _, warnings = run(self.sm)
    self.assertEqual(ids(warnings, "S6"), ["S6 SM-TEST: SWSR-4 requires clearing authority but no transition "
                                           "realises it"])

  def test_s6_reports_non_revoking_reaction(self):
    self.sm["s6_exempt"] = []
    self.sm["non_revoking"] = [{"event": "ev", "reaction": "frames refused; authority kept", "swsr": ["SWSR-4"]}]
    _, warnings = run(self.sm)
    self.assertIn("(the code only does: frames refused; authority kept)", ids(warnings, "S6")[0])

  def test_s6_withdrawn_ignored(self):
    self.assertNotIn("SWSR-5", " ".join(run(self.sm)[1]))

  def test_s6_only_for_authority_machines(self):
    self.sm["states"] = ["IDLE", "ACTIVE"]
    self.sm["initial"] = "IDLE"
    for t in self.sm["transitions"]:
      t["from"] = {"NOT_ALLOWED": "IDLE", "ALLOWED": "ACTIVE"}.get(t["from"], t["from"])
      t["to"] = {"NOT_ALLOWED": "IDLE", "ALLOWED": "ACTIVE"}.get(t["to"], t["to"])
    self.sm["transitions"].pop(3)
    self.assertEqual(ids(run(self.sm)[1], "S6"), [])


class TestStatus(unittest.TestCase):
  def test_impl_state_prefixes(self):
    cases = {"Impl: x": "impl", "**Impl**": "impl", "Met for": "impl", "Not verified on": "impl",
             "Partial (x)": "partial", "Not impl": "not", "Not met": "not", "": "unknown", "TBD": "unknown"}
    for baseline, want in cases.items():
      self.assertEqual(csm.impl_state(baseline), want, baseline)

  def test_transition_state(self):
    t = {"swsr": ["SWSR-1", "SWSR-2"]}
    self.assertEqual(csm.transition_state(t, SW), "partial")
    self.assertEqual(csm.transition_state({"swsr": ["SWSR-1"]}, SW), "impl")
    self.assertEqual(csm.transition_state({"swsr": ["SWSR-3", "SWSR-4"]}, SW), "not")
    self.assertEqual(csm.transition_state({"swsr": []}, SW), "unknown")
    self.assertEqual(csm.transition_state({"swsr": ["SWSR-99"]}, SW), "unknown")


GOLDEN_TABLE = """\
| # | Current | Event | Guard | Action | Next | Build | SWSR | Status | Code |
|---|---|---|---|---|---|---|---|---|---|
| T1 | NOT_ALLOWED | e1 | g and h | set | ALLOWED | all | 1 | Implemented | a.h:1 |
| T8 | NOT_ALLOWED | e1 | not g \\| h | none | NOT_ALLOWED | all | 1 | Implemented | a.h:1 |
| T2 | ALLOWED | e2 | — | clear | NOT_ALLOWED | all | 2 | Partial | a.h:2 |
| T3 | ALLOWED | e3 | — | clear | NOT_ALLOWED | all | 3 | Not implemented | not implemented |
| T7 | any | reset | — | clear | NOT_ALLOWED | all | 1 | Implemented | a.h:3 |"""

GOLDEN_MERMAID = """\
```mermaid
stateDiagram-v2
  [*] --> NOT_ALLOWED
  NOT_ALLOWED --> ALLOWED: T1
  ALLOWED --> NOT_ALLOWED: T2
  ALLOWED --> NOT_ALLOWED: T3
  NOT_ALLOWED --> NOT_ALLOWED: T7
  ALLOWED --> NOT_ALLOWED: T7
```"""


class TestGeneration(unittest.TestCase):
  def setUp(self):
    self.blocks = dict(csm.BLOCKS)
    csm.BLOCKS["SM-TEST"] = "sm-test"

  def tearDown(self):
    csm.BLOCKS.clear()
    csm.BLOCKS.update(self.blocks)

  def test_render_golden(self):
    out = csm.render(GOOD, SW)
    self.assertIn(GOLDEN_TABLE, out)
    self.assertTrue(out.endswith(GOLDEN_MERMAID), out[-400:])

  def test_render_gap_table(self):
    sm = copy.deepcopy(GOOD)
    sm["transitions"][2]["swsr"] = []
    sm["transitions"][2]["gap"] = "none | yet"
    out = csm.render(sm, SW)
    self.assertIn("| T2 | ALLOWED | e2 | — | clear | NOT_ALLOWED | all | gap | Not assessed | a.h:2 |", out)
    self.assertIn("| # | Gap |\n|---|---|\n| T2 | none \\| yet |", out)

  def test_blocks_replace_and_idempotent(self):
    text = ("before\n<!-- BEGIN GENERATED: sm-test (assurance/trace/tools/check_state_machines.py) -->\nstale\n"
            "<!-- END GENERATED: sm-test -->\nafter\n")
    once = csm.blocks([GOOD], SW, text)
    self.assertNotIn("stale", once)
    self.assertTrue(once.startswith("before\n") and once.endswith("after\n"))
    self.assertEqual(csm.blocks([GOOD], SW, once), once)

  def test_blocks_missing_marker(self):
    with self.assertRaises(SystemExit):
      csm.blocks([GOOD], SW, "no markers here")


class TestLoader(unittest.TestCase):
  def test_subset_parser(self):
    text = ('machine: SM-X\n# comment\nstates: [A, B]\ntransitions:\n'
            '  - {id: T1, from: A, event: "x, y", guard: "a \\"q\\" b", to: B, swsr: [SWSR-1, SWSR-2]}  # trailing\n'
            '  - {id: T2, from: "A, B", event: e, to: A, swsr: []}\n')
    doc = csm._load_subset(text)
    self.assertEqual(doc["states"], ["A", "B"])
    self.assertEqual(doc["transitions"][0]["event"], "x, y")
    self.assertEqual(doc["transitions"][0]["guard"], 'a "q" b')
    self.assertEqual(doc["transitions"][0]["swsr"], ["SWSR-1", "SWSR-2"])
    self.assertEqual(doc["transitions"][1]["from"], "A, B")

  def test_subset_parser_matches_pyyaml_on_records(self):
    try:
      import yaml
    except ImportError:
      self.skipTest("PyYAML not installed")
    paths = sorted(csm.SM_DIR.glob("*.yaml"))
    self.assertTrue(paths)
    for p in paths:
      text = p.read_text(encoding="utf-8")
      self.assertEqual(csm._load_subset(text), yaml.safe_load(text), p.name)


class TestRepositoryRecords(unittest.TestCase):
  def test_records_have_no_errors_and_tables_current(self):
    sw = csm.swsr_records()
    sms = [csm.load(p) for p in sorted(csm.SM_DIR.glob("*.yaml"))]
    self.assertTrue(sms)
    for sm in sms:
      self.assertEqual(csm.check(sm, sw)[0], [], sm["machine"])
    current = csm.WP_W05.read_text(encoding="utf-8")
    self.assertEqual(csm.blocks(sms, sw, current), current, "WP-W-05 §5 out of date; run --write")


if __name__ == "__main__":
  unittest.main()
