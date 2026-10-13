#!/usr/bin/env python3
"""Tests for hara_model.py (WP-P-07 TL-34, OI-12).

The ASIL table is checked exhaustively against check_trace.py's risk graph, a second implementation written
separately. The rating rules are checked as properties over every generated hazardous event. --check must pass on
the committed outputs and fail on a stale one.

Run from the repository root:  python3 -m unittest discover -s assurance/02-concept/hara -p 'test_*.py' -v
Standard library only (openpyxl is not needed).
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1] / "trace" / "tools"


def _load(name, path):
  spec = importlib.util.spec_from_file_location(name, path)
  mod = importlib.util.module_from_spec(spec)
  sys.modules[name] = mod
  spec.loader.exec_module(mod)
  return mod


sys.path.insert(0, str(TOOLS))
hm = _load("hara_model", HERE / "hara_model.py")
ct = _load("check_trace", TOOLS / "check_trace.py")

ROWS = {False: hm.build(False)[1], True: hm.build(True)[1]}
OS_E = {s[0]: s[4] for s in hm.SITUATIONS}
W_E = {w[0]: w[2] for w in hm.WEATHER}


class TestAsil(unittest.TestCase):
  def test_table_matches_independent_risk_graph(self):
    for s in (1, 2, 3):
      for e in (1, 2, 3, 4):
        for c in (1, 2, 3):
          self.assertEqual(hm.asil(f"S{s}", f"E{e}", f"C{c}"), ct.risk_graph(s, e, c), (s, e, c))

  def test_zero_classes(self):
    self.assertEqual(hm.asil("S0", "E4", "C3"), "—")
    for s in ("S1", "S2", "S3"):
      self.assertEqual(hm.asil(s, "E0", "C3"), "QM")
      self.assertEqual(hm.asil(s, "E4", "C0"), "QM")

  def test_only_iso_combinations_in_table(self):
    for (s, e, c), a in hm.ASIL.items():
      self.assertEqual(a, ct.risk_graph(int(s[1]), int(e[1]), int(c[1])))
    self.assertEqual(len(hm.ASIL), 18)  # ISO 26262-3 Table 4: 18 non-QM cells


class TestRatingProperties(unittest.TestCase):
  def test_exposure_is_rarer_of_situation_and_weather(self):
    for exp, rows in ROWS.items():
      for r in rows:
        want = min(OS_E[r["os"]], W_E[r["w"]], key=lambda x: hm.E_RANK[x])
        self.assertEqual(r["E"], want, (exp, r["f"], r["m"], r["os"], r["w"]))

  def test_asil_columns_consistent(self):
    for rows in ROWS.values():
      for r in rows:
        self.assertEqual(r["asil"], hm.asil(r["S"], r["E"], r["C"]))
        if "⚠" in r["c_rat"]:
          self.assertEqual(r["asil_aou_fail"], hm.asil(r["S"], r["E"], hm.C_UP[r["C"]]))
          self.assertGreaterEqual(hm.ORDER.index(r["asil_aou_fail"]), hm.ORDER.index(r["asil"]))
        else:
          self.assertEqual(r["asil_aou_fail"], r["asil"])

  def test_not_engaged_situation(self):
    for rows in ROWS.values():
      for r in rows:
        if r["os"] in hm.NOT_ENGAGED and r["f"] in hm.ENGAGED_ONLY:
          self.assertEqual((r["S"], r["C"]), ("S0", "C0"), r)

  def test_weather_never_lowers_severity_or_raises_controllability_class_down(self):
    # for the same (f, m, os), a non-dry weather never gives a lower S or C than dry weather W01,
    # except the documented wet-curve rule for H-04 (C1 with VSC, HE-04.2)
    for rows in ROWS.values():
      dry = {(r["f"], r["m"], r["os"]): r for r in rows if r["w"] == "W01"}
      for r in rows:
        d = dry[(r["f"], r["m"], r["os"])]
        if r["h"] == "H-04" and r["w"] in ("W02", "W04") and r["os"] in ("OS-02", "OS-14", "OS-16"):
          continue
        self.assertGreaterEqual(r["S"], d["S"], r)
        self.assertGreaterEqual(r["C"], d["C"], r)

  def test_snow_raises_c_for_lateral_hazards(self):
    for rows in ROWS.values():
      dry = {(r["f"], r["m"], r["os"]): r for r in rows if r["w"] == "W01"}
      for r in rows:
        if r["w"] == "W05" and r["h"] == "H-01" and r["S"] != "S0":
          self.assertEqual(r["C"], hm.C_UP[dry[(r["f"], r["m"], r["os"])]["C"]], r)


class TestCheck(unittest.TestCase):
  def _main(self, argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      return hm.main(argv), out.getvalue()

  def test_check_passes_on_committed_outputs(self):
    rc, out = self._main(["hara_model.py", "--check"])
    self.assertEqual(rc, 0, out)

  def test_check_fails_on_stale_output(self):
    name = "hara-function-guideword.csv"
    orig = hm.OUTPUTS[name]
    try:
      hm.OUTPUTS[name] = lambda: orig() + "stale\n"
      rc, out = self._main(["hara_model.py", "--check"])
    finally:
      hm.OUTPUTS[name] = orig
    self.assertEqual(rc, 1)
    self.assertIn(name, out)


if __name__ == "__main__":
  unittest.main()
