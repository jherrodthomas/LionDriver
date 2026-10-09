#!/usr/bin/env python3
"""Tests for fmea_lint. Run: python3 -m unittest discover -s tools/safety"""
import copy
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fmea_lint

REPO = fmea_lint.ROOT


def ap_table_from_markdown():
  """Parse the AP table in rating-tables.md section 5 into {(s_band, o_band): 'HHHM'}."""
  text = (REPO / "docs/safety/rating-tables.md").read_text()
  section = text.split("## 5. Action Priority")[1].split("\n## ")[0]
  rows = {}
  for m in re.finditer(r"^\| *([0-9–]+) *\| *([0-9–]+) *\| *([HML]) *\| *([HML]) *\| *([HML]) *\| *([HML]) *\|$", section, re.M):
    s, o = (tuple(int(x) for x in g.split("–")) if "–" in g else (int(g), int(g)) for g in m.group(1, 2))
    rows[(s, o)] = "".join(m.group(3, 4, 5, 6))
  return rows


SWF = {
  "schema_version": 1,
  "analysis": {
    "id": "SWF", "type": "sw_fmea", "title": "test", "revision": "0.1", "status": "draft",
    "baseline": "BL-001", "rating_tables": "RT-1", "scope": "test",
  },
  "structure": [
    {"id": "SWF-SE-001", "name": "controlsd", "kind": "sw_element", "paths": ["openpilot/selfdrive/controls/controlsd.py"]},
  ],
  "functions": [
    {"id": "SWF-FN-001", "element": "SWF-SE-001", "description": "Compute steering torque request"},
  ],
  "failure_modes": [{
    "id": "SWF-001", "element": "SWF-SE-001", "function": "SWF-FN-001",
    "failure_mode": "Torque request too high", "guideword": "value_high",
    "effects": [{"level": "end", "description": "Unintended lateral motion", "hazard": "HZ-001", "severity": 10}],
    "severity": 10,
    "causes": [{
      "id": "SWF-001.C1", "description": "Controller gain misconfigured",
      "prevention_controls": [{"description": "Code review"}],
      "detection_controls": [{"description": "Lateral control unit test", "test": "openpilot/selfdrive/controls/tests/test_latcontrol.py"}],
      "occurrence": 5, "detection": 4, "ap": "H", "actions": ["SWF-ACT-001"],
    }],
  }],
  "actions": [{"id": "SWF-ACT-001", "kind": "detection", "description": "Add torque limit fault-injection test", "status": "open"}],
}

FMEDA = {
  "schema_version": 1,
  "analysis": {
    "id": "FMD", "type": "fmeda", "title": "test", "revision": "0.1", "status": "draft",
    "baseline": "BL-001", "rating_tables": "RT-1", "scope": "test", "safety_goal": "SG-001", "asil_target": "B",
  },
  "safety_mechanisms": [{"id": "FMD-SM-001", "description": "CAN TX limit check", "dc_basis": "ISO 26262-5 D.2"}],
  "components": [{
    "id": "FMD-C-001", "part": "MCU", "failure_rate_fit": 100.0, "failure_rate_source": "IEC 61709", "safety_related": True,
    "failure_modes": [
      {"id": "FMD-001", "mode": "wrong output", "distribution": 0.5, "violates_sg_directly": True, "mpf_potential": False,
       "safety_mechanism_spf": "FMD-SM-001", "dc_spf": 0.99},
      {"id": "FMD-002", "mode": "monitor stuck", "distribution": 0.3, "violates_sg_directly": False, "mpf_potential": True,
       "safety_mechanism_lf": "FMD-SM-001", "dc_lf": 0.9},
      {"id": "FMD-003", "mode": "benign", "distribution": 0.2, "violates_sg_directly": False, "mpf_potential": False},
    ],
  }],
}


class TestActionPriority(unittest.TestCase):
  def test_matches_markdown_table(self):
    md = ap_table_from_markdown()
    self.assertEqual(len(md), 21, "expected 21 rows in rating-tables.md section 5")
    d_bands = [(7, 10), (5, 6), (2, 4), (1, 1)]
    checked = 0
    for (s_lo, s_hi), (o_lo, o_hi) in md:
      row = md[((s_lo, s_hi), (o_lo, o_hi))]
      for s in range(s_lo, s_hi + 1):
        for o in range(o_lo, o_hi + 1):
          for i, (d_lo, d_hi) in enumerate(d_bands):
            for d in range(d_lo, d_hi + 1):
              self.assertEqual(fmea_lint.compute_ap(s, o, d), row[i], f"S{s} O{o} D{d}")
              checked += 1
    self.assertEqual(checked, 1000)

  def test_out_of_range(self):
    with self.assertRaises(ValueError):
      fmea_lint.compute_ap(0, 5, 5)


class TestRepository(unittest.TestCase):
  def test_repo_analyses_are_clean(self):
    res = fmea_lint.lint(REPO)
    self.assertEqual(res.errors, [])


class LintFixture(unittest.TestCase):
  def setUp(self):
    self.tmp = Path(tempfile.mkdtemp())
    self.addCleanup(shutil.rmtree, self.tmp)
    for rel in ("docs/safety/schema", "docs/safety/rating-tables.md", "docs/safety/baseline.yaml"):
      src, dst = REPO / rel, self.tmp / rel
      dst.parent.mkdir(parents=True, exist_ok=True)
      (shutil.copytree if src.is_dir() else shutil.copy)(src, dst)
    (self.tmp / "docs/safety/analyses").mkdir()
    test = self.tmp / "openpilot/selfdrive/controls/tests/test_latcontrol.py"
    test.parent.mkdir(parents=True)
    test.touch()
    (self.tmp / "openpilot/selfdrive/controls/controlsd.py").touch()
    (self.tmp / "panda").mkdir()
    (self.tmp / ".gitmodules").write_text('[submodule "panda"]\n  path = panda\n  url = x\n')

  def write(self, name, doc):
    (self.tmp / "docs/safety/analyses" / name).write_text(yaml.safe_dump(doc, sort_keys=False))

  def lint(self, **docs):
    for name, doc in docs.items():
      self.write(f"{name}.yaml", doc)
    return fmea_lint.lint(self.tmp)

  def assertError(self, res, needle):
    self.assertTrue(any(needle in e for e in res.errors), f"no error containing {needle!r} in {res.errors}")


class TestFmeaRules(LintFixture):
  def test_valid_example(self):
    res = self.lint(swf=SWF)
    self.assertEqual(res.errors, [])
    self.assertIn("H=1", res.report[0])

  def test_schema_violation(self):
    doc = copy.deepcopy(SWF)
    doc["failure_modes"][0]["guideword"] = "short"  # hardware guideword in a SW FMEA
    self.assertError(self.lint(swf=doc), "schema")

  def test_wrong_ap(self):
    doc = copy.deepcopy(SWF)
    doc["failure_modes"][0]["causes"][0]["ap"] = "L"
    self.assertError(self.lint(swf=doc), "table gives H")

  def test_hazard_requires_severity_10(self):
    doc = copy.deepcopy(SWF)
    doc["failure_modes"][0]["effects"][0]["severity"] = 8
    doc["failure_modes"][0]["severity"] = 8
    self.assertError(self.lint(swf=doc), "must have severity 10")

  def test_severity_is_max_of_effects(self):
    doc = copy.deepcopy(SWF)
    doc["failure_modes"][0]["severity"] = 9
    self.assertError(self.lint(swf=doc), "max effect severity")

  def test_ap_h_needs_action_or_rationale(self):
    doc = copy.deepcopy(SWF)
    del doc["failure_modes"][0]["causes"][0]["actions"]
    self.assertError(self.lint(swf=doc), "AP=H requires")
    doc["failure_modes"][0]["causes"][0]["rationale"] = "Accepted: bounded by panda safety model"
    self.assertNotIn("AP=H", " ".join(self.lint(swf=doc).errors))

  def test_detection_claim_needs_test_path(self):
    doc = copy.deepcopy(SWF)
    del doc["failure_modes"][0]["causes"][0]["detection_controls"][0]["test"]
    self.assertError(self.lint(swf=doc), "must name a `test` path")

  def test_missing_test_path(self):
    doc = copy.deepcopy(SWF)
    doc["failure_modes"][0]["causes"][0]["detection_controls"][0]["test"] = "nope/test_x.py"
    self.assertError(self.lint(swf=doc), "does not exist")

  def test_uninitialized_submodule_path_warns(self):
    doc = copy.deepcopy(SWF)
    doc["failure_modes"][0]["causes"][0]["detection_controls"][0]["test"] = "panda/tests/test_x.py"
    res = self.lint(swf=doc)
    self.assertEqual(res.errors, [])
    self.assertTrue(any("uninitialized submodule panda" in w for w in res.warnings))

  def test_released_requires_ratings(self):
    doc = copy.deepcopy(SWF)
    doc["analysis"]["status"] = "released"
    c = doc["failure_modes"][0]["causes"][0]
    c["occurrence"] = c["ap"] = None
    self.assertError(self.lint(swf=doc), "released analysis requires")

  def test_dangling_links(self):
    doc = copy.deepcopy(SWF)
    doc["failure_modes"][0]["causes"][0]["linked_failure_mode"] = "DFM-999"
    doc["failure_modes"][0]["causes"][0]["actions"] = ["SWF-ACT-404"]
    res = self.lint(swf=doc)
    self.assertError(res, "DFM-999 not found")
    self.assertError(res, "SWF-ACT-404 not found")

  def test_cross_file_link_and_duplicate_ids(self):
    sfm = copy.deepcopy(SWF)
    sfm["analysis"].update(id="SFM", type="system_fmea")
    sfm_text = yaml.safe_dump(sfm).replace("SWF-", "SFM-").replace("value_high", "excessive")
    sfm = yaml.safe_load(sfm_text)
    sfm["failure_modes"][0]["causes"][0]["linked_failure_mode"] = "SWF-001"
    self.assertEqual(self.lint(swf=SWF, sfm=sfm).errors, [])
    self.assertError(self.lint(swf=SWF, swf2=SWF), "duplicate id SWF-001")

  def test_rating_tables_version(self):
    doc = copy.deepcopy(SWF)
    doc["analysis"]["rating_tables"] = "RT-0"
    self.assertError(self.lint(swf=doc), "re-rate")


class TestFmeda(LintFixture):
  def test_metrics(self):
    m = fmea_lint.fmeda_metrics(FMEDA)
    self.assertAlmostEqual(m["rf_fit"], 0.5)          # 100 * 0.5 * (1 - 0.99)
    self.assertAlmostEqual(m["spfm"], 0.995)
    self.assertAlmostEqual(m["mpf_latent_fit"], 3.0)  # 100 * 0.3 * (1 - 0.9)
    self.assertAlmostEqual(m["lfm"], 1 - 3.0 / 99.5)

  def test_unprotected_spf(self):
    doc = copy.deepcopy(FMEDA)
    fm = doc["components"][0]["failure_modes"][0]
    del fm["safety_mechanism_spf"], fm["dc_spf"]
    self.assertAlmostEqual(fmea_lint.fmeda_metrics(doc)["spf_fit"], 50.0)
    res = self.lint(fmd=doc)
    self.assertTrue(any("SPFM" in w for w in res.warnings))
    doc["analysis"]["status"] = "released"
    self.assertError(self.lint(fmd=doc), "ASIL B target missed")

  def test_distribution_sum(self):
    doc = copy.deepcopy(FMEDA)
    doc["components"][0]["failure_modes"][2]["distribution"] = 0.1
    self.assertError(self.lint(fmd=doc), "sums to 0.9000")

  def test_mechanism_requires_dc(self):
    doc = copy.deepcopy(FMEDA)
    del doc["components"][0]["failure_modes"][0]["dc_spf"]
    self.assertError(self.lint(fmd=doc), "without dc_spf")

  def test_fmeda_ids_are_per_file(self):
    self.assertEqual(self.lint(fmd1=FMEDA, fmd2=FMEDA).errors, [])


if __name__ == "__main__":
  unittest.main()
