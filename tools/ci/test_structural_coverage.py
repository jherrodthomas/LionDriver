#!/usr/bin/env python3
"""Tests for coverage/structural_coverage.py: the cross-check, the report and the baseline ratchet (no compilers needed)."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent / "coverage"))
import structural_coverage as sc  # noqa: E402


def llvm(unc_br=0, unc_mc=0, lines=(10,), pin="aaaaaaa"):
  units = {}
  for u, f in sc.UNITS.items():
    units[u] = {"file": f, "branches": {"total": 20, "covered": 20 - unc_br, "uncovered_lines": []},
                "mcdc": {"total": 8, "covered": 8 - unc_mc, "uncovered_lines": list(lines) if unc_mc else []}}
  return {"tool": "llvm", "versions": {"clang-18": "x"}, "opendbc": pin, "tests": sc.TEST_MODULES,
          "variant": "LIONDRIVER_REFERENCE=1", "units": units}


def gcc(lines=(10,)):
  return {"tool": "gcc", "versions": {"gcc-14": "y"}, "units": {
    u: {"file": f, "conditions": {"outcomes": 30, "covered": 28},
        "multi_conditions": {"outcomes": 16, "covered": 14, "uncovered_lines": list(lines)}} for u, f in sc.UNITS.items()}}


class TestStructuralCoverage(unittest.TestCase):
  def setUp(self):
    self.tmp = Path(tempfile.mkdtemp())
    self.baseline = self.tmp / "baseline.json"
    self.patch = mock.patch.object(sc, "BASELINE", self.baseline)
    self.patch.start()
    self.addCleanup(self.patch.stop)

  def write(self, l, g=None):
    (self.tmp / "llvm.json").write_text(json.dumps(l))
    if g:
      (self.tmp / "gcc.json").write_text(json.dumps(g))

  def report(self, **kw):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
      return sc.cmd_report(self.tmp, kw.get("check", False), kw.get("write", False), None)

  def test_cross_check_agreement_and_disagreement(self):
    cc = sc.cross_check(llvm(unc_mc=1, lines=(10, 12)), gcc(lines=(10, 14)))
    for c in cc.values():
      self.assertEqual(c, {"both": [10], "llvm_only": [12], "gcc_only": [14]})

  def test_report_lists_every_unit(self):
    md = sc.render_md(llvm(unc_mc=1), gcc())
    for u in sc.UNITS:
      self.assertIn(u, md)
    self.assertIn("7/8 (87.5 %)", md)

  def test_ratchet_passes_at_baseline_and_fails_when_a_gap_grows(self):
    self.write(llvm(unc_br=1, unc_mc=1), gcc())
    self.assertEqual(self.report(write=True), 0)
    self.assertEqual(self.report(check=True), 0)
    self.write(llvm(unc_br=1, unc_mc=2), gcc())
    self.assertEqual(self.report(check=True), 1)
    self.write(llvm(unc_br=0, unc_mc=0), gcc())
    self.assertEqual(self.report(check=True), 0, "fewer gaps than the baseline is allowed")

  def test_pin_change_with_different_counts_needs_a_new_baseline(self):
    self.write(llvm(pin="aaaaaaa"), gcc())
    self.report(write=True)
    self.write(llvm(pin="bbbbbbb"), gcc())
    self.assertEqual(self.report(check=True), 0, "same counts at a new pin")
    d = llvm(pin="bbbbbbb")
    d["units"]["U-SAF-TOY"]["mcdc"]["total"] = 9
    d["units"]["U-SAF-TOY"]["mcdc"]["covered"] = 9
    self.write(d, gcc())
    self.assertEqual(self.report(check=True), 1)

  def test_unit_mapping(self):
    self.assertEqual(sc.unit_of("/x/opendbc_repo/opendbc/safety/modes/toyota.h"), "U-SAF-TOY")
    self.assertIsNone(sc.unit_of("/x/opendbc_repo/opendbc/safety/modes/hyundai.h"))

  def test_committed_baseline_covers_every_unit(self):
    base = json.loads((Path(__file__).resolve().parents[2] / "assurance/05-software/coverage/structural-baseline.json")
                      .read_text())
    self.assertEqual(sorted(base["units"]), sorted(sc.UNITS))

  def test_gap_matching(self):
    j = self.tmp / "j.md"
    j.write_text("| ID | Unit | Function | Decision | Class | Rationale |\n|---|---|---|---|---|---|\n"
                 "| CJ-01 | U-SAF-TOY | f | * | N | not called |\n"
                 "| CJ-02 | U-SAF-TOY | g | if (a \\|\\| b) { | C | constant |\n"
                 "| CJ-03 | U-SAF-TOY | h | * | N | stale |\n")
    rows = sc.load_justifications(j)
    self.assertEqual(rows[1]["decision"], "if (a || b) {")
    d = llvm()
    d["units"]["U-SAF-TOY"]["gaps"] = [{"function": "f", "decision": "*"},
                                       {"function": "g", "decision": "if (a ||   b) {", "line": 3},
                                       {"function": "k", "decision": "x;", "line": 9}]
    matched, missing, stale = sc.match_gaps(d, rows)
    self.assertEqual([r["id"] for _, _, r in matched], ["CJ-01", "CJ-02"])
    self.assertEqual([g["function"] for _, g in missing], ["k"])
    self.assertEqual([r["id"] for r in stale], ["CJ-03"])

  def test_malformed_justification_row_is_refused(self):
    j = self.tmp / "j.md"
    j.write_text("| CJ-01 | U-SAF-TOY | f | * | X | bad class |\n")
    with self.assertRaises(sc.CoverageError):
      sc.load_justifications(j)

  def test_committed_justifications_parse(self):
    rows = sc.load_justifications()
    self.assertEqual(len(rows), len({r["id"] for r in rows}))
    self.assertTrue(all(r["unit"] in sc.UNITS for r in rows))


if __name__ == "__main__":
  unittest.main()
