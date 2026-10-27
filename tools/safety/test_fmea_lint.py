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
  text = (REPO / "assurance/08-analyses/fmea/rating-tables.md").read_text()
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


SFM = yaml.safe_load(yaml.safe_dump(SWF).replace("SWF-", "SFM-").replace("value_high", "excessive"))
SFM["analysis"].update(id="SFM", type="system_fmea")

HARA = {
  "schema_version": 1,
  "analysis": {"id": "HARA", "type": "hara", "title": "test", "revision": "0.1", "status": "draft", "baseline": "BL-001", "scope": "test"},
  "assumptions": [{"id": "HA-001", "text": "L2"}],
  "operational_situations": [{
    "id": "OS-001", "description": "highway", "road": "highway", "speed": "80-130 km/h", "item_state": "engaged",
    "exposure": "E4", "exposure_rationale": "common",
  }],
  "hazards": [{"id": "HZ-001", "description": "excessive steering", "guidewords": ["M05"], "functions": ["SFM-FN-001"], "sfm_refs": ["SFM-001"]}],
  "hazardous_events": [{
    "id": "HE-001", "hazard": "HZ-001", "situation": "OS-001", "consequence": "lane departure",
    "severity": "S3", "severity_rationale": "speed", "exposure_override": None,
    "controllability": "C3", "controllability_rationale": "fast", "asil": "D",
  }],
  "safety_goals": [{"id": "SG-001", "statement": "avoid", "hazards": ["HZ-001"], "asil": "D", "safe_state": "off", "ftti_ms": None}],
  "open_items": [{"id": "OI-001", "text": "x", "affects": ["HE-001"], "status": "open"}],
  "guideword_analysis": [
    {"function": "SFM-FN-001", "guideword": f"M{i:02d}", "classification": "SC" if i == 5 else "NSC",
     **({"hazards": ["HZ-001"]} if i == 5 else {}), "rationale": "x"}
    for i in range(1, 15)
  ],
  "situation_coverage": [{"hazard": "HZ-001", "situation": "OS-001", "status": "rated", "he": "HE-001", "rationale": "x"}],
}

def _fsr(id_, asil, alloc, **kw):
  return {"id": id_, "safety_goal": "SG-001", "asil": asil, "kind": "limitation", "statement": "x", "allocated_to": alloc,
          "safe_state": "off", "implementation": {"status": "existing"}, "verification": [{"method": "review"}], **kw}


FSC = {
  "schema_version": 1,
  "analysis": {"id": "FSC", "type": "fsc", "title": "test", "revision": "0.1", "status": "draft", "baseline": "BL-001",
               "hara_revision": "0.1", "scope": "test"},
  "elements": [
    {"id": "EL-01", "name": "soc", "type": "software", "asil_capability": "QM", "capability_status": "not_applicable",
     "sfm_elements": ["SFM-SE-001"], "description": "x"},
    {"id": "EL-02", "name": "panda", "type": "processor", "asil_capability": "D", "capability_status": "unproven",
     "sfm_elements": ["SFM-SE-001"], "description": "x"},
    {"id": "EL-03", "name": "eps", "type": "external", "asil_capability": "QM", "capability_status": "not_applicable",
     "sfm_elements": ["SFM-SE-001"], "description": "x"},
  ],
  "external_measures": [],
  "timing": [{"safety_goal": "SG-001", "ftti_ms": 900, "ftti_status": "preliminary", "basis": "x"}],
  "operating_modes": [],
  "warning_degradation": [],
  "fsrs": [
    _fsr("FSR-001", "D", ["EL-01", "EL-02"], decomposition={"into": ["FSR-002", "FSR-003"], "independence": "x"}),
    _fsr("FSR-002", "D(D)", ["EL-02"]),
    _fsr("FSR-003", "QM(D)", ["EL-01"]),
  ],
  "open_items": [],
}

DFA = {
  "schema_version": 1,
  "analysis": {"id": "DFA", "type": "dfa", "title": "test", "revision": "0.1", "status": "draft", "baseline": "BL-001",
               "fsc_revision": "0.1", "scope": "test"},
  "categories": [
    {"id": "CAT-01", "name": "power", "applicable": True, "rationale": "x"},
    {"id": "CAT-02", "name": "memory", "applicable": False, "rationale": "x"},
  ],
  "decompositions": [{"fsr": "FSR-001", "channels": [{"fsr": "FSR-002", "elements": ["EL-02"]}, {"fsr": "FSR-003", "elements": ["EL-01"]}],
                      "status": "accepted", "rationale": "x"}],
  "dfis": [{"id": "DFI-01", "category": "CAT-01", "kind": "common_cause", "description": "x", "decompositions": ["FSR-001"],
            "effect": "x", "measures": ["DM-01"], "assessment": "sufficient", "rationale": "x"}],
  "measures": [{"id": "DM-01", "description": "x", "status": "existing"}],
  "open_items": [],
}

# ISO 26262-3 Table 4, written out: rows S1..S3 x E1..E4, columns C1..C3.
ISO_TABLE_4 = {
  ("S1", "E1"): ("QM", "QM", "QM"), ("S1", "E2"): ("QM", "QM", "QM"), ("S1", "E3"): ("QM", "QM", "A"), ("S1", "E4"): ("QM", "A", "B"),
  ("S2", "E1"): ("QM", "QM", "QM"), ("S2", "E2"): ("QM", "QM", "A"), ("S2", "E3"): ("QM", "A", "B"), ("S2", "E4"): ("A", "B", "C"),
  ("S3", "E1"): ("QM", "QM", "A"), ("S3", "E2"): ("QM", "A", "B"), ("S3", "E3"): ("A", "B", "C"), ("S3", "E4"): ("B", "C", "D"),
}


class TestAsil(unittest.TestCase):
  def test_iso_table_4(self):
    for (s, e), row in ISO_TABLE_4.items():
      for c, asil in zip(("C1", "C2", "C3"), row, strict=True):
        self.assertEqual(fmea_lint.compute_asil(s, e, c), asil, f"{s} {e} {c}")

  def test_zero_classes_are_qm(self):
    for s, e, c in (("S0", "E4", "C3"), ("S3", "E0", "C3"), ("S3", "E4", "C0")):
      self.assertEqual(fmea_lint.compute_asil(s, e, c), "QM")


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
    for rel in ("assurance/08-analyses/fmea/schema", "assurance/08-analyses/fmea/rating-tables.md", "assurance/08-analyses/fmea/baseline.yaml"):
      src, dst = REPO / rel, self.tmp / rel
      dst.parent.mkdir(parents=True, exist_ok=True)
      (shutil.copytree if src.is_dir() else shutil.copy)(src, dst)
    (self.tmp / "assurance/08-analyses/fmea/analyses").mkdir()
    test = self.tmp / "openpilot/selfdrive/controls/tests/test_latcontrol.py"
    test.parent.mkdir(parents=True)
    test.touch()
    (self.tmp / "openpilot/selfdrive/controls/controlsd.py").touch()
    (self.tmp / "panda").mkdir()
    (self.tmp / ".gitmodules").write_text('[submodule "panda"]\n  path = panda\n  url = x\n')

  def write(self, name, doc):
    (self.tmp / "assurance/08-analyses/fmea/analyses" / name).write_text(yaml.safe_dump(doc, sort_keys=False))

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

  def test_inherited_rating_out_of_range(self):
    sfm = yaml.safe_load(yaml.safe_dump(SWF).replace("SWF-", "SFM-").replace("value_high", "excessive"))
    sfm["analysis"].update(id="SFM", type="system_fmea")
    sfm["failure_modes"][0]["causes"][0]["linked_failure_mode"] = "SWF-001"
    swf = copy.deepcopy(SWF)
    self.assertFalse(any("re-inherit" in w for w in self.lint(swf=swf, sfm=sfm).warnings))
    swf["failure_modes"][0]["causes"][0]["occurrence"] = 6  # source re-rated worse; S10 O6 D4 stays AP H
    res = self.lint(swf=swf, sfm=sfm)
    self.assertEqual(res.errors, [])
    self.assertTrue(any("SFM-001.C1" in w and "O 5 is outside SWF-001" in w for w in res.warnings))

  def test_unquoted_date_is_accepted(self):
    text = yaml.safe_dump(SWF, sort_keys=False).replace("analysis:\n", "analysis:\n  updated: 2026-10-09\n", 1)
    (self.tmp / "assurance/08-analyses/fmea/analyses/swf.yaml").write_text(text)
    self.assertEqual(fmea_lint.lint(self.tmp).errors, [])

  def test_rating_tables_version(self):
    doc = copy.deepcopy(SWF)
    doc["analysis"]["rating_tables"] = "RT-0"
    self.assertError(self.lint(swf=doc), "re-rate")


class TestStudyFields(LintFixture):
  """Optional fields for the baseline delta, reaction time by layer and the SOTIF boundary (fmea-plan section 3.3)."""

  def doc(self):
    doc = copy.deepcopy(SWF)
    doc["analysis"]["baseline"] = "BL-005"
    return doc

  def test_all_fields_valid(self):
    doc = self.doc()
    doc["structure"][0]["sotif"] = {"boundary": "split", "sotif_part": "model accuracy", "ref": "WP-C-05 SH-01"}
    doc["failure_modes"][0]["safety_mechanisms"] = [
      {"description": "panda torque limit", "layer": "envelope", "reaction_s": 0.0, "timing_basis": "code_derived",
       "timing_ref": "opendbc safety.h:1"},
      {"description": "alert", "layer": "alert", "reaction_s": 0.5, "timing_basis": "requirement"}]
    doc["failure_modes"][0]["causes"][0]["previous"] = {"baseline": "BL-004", "occurrence": 8, "detection": 8, "ap": "H",
                                                         "change": "PR #95"}
    self.assertEqual(self.lint(swf=doc).errors, [])

  def test_previous_ap_checked(self):
    doc = self.doc()
    doc["failure_modes"][0]["causes"][0]["previous"] = {"baseline": "BL-004", "occurrence": 8, "detection": 8, "ap": "L"}
    self.assertError(self.lint(swf=doc), "previous ap is L")

  def test_previous_must_be_earlier(self):
    doc = self.doc()
    doc["failure_modes"][0]["causes"][0]["previous"] = {"baseline": "BL-005", "occurrence": 8, "detection": 8, "ap": "H"}
    self.assertError(self.lint(swf=doc), "not earlier")

  def test_previous_equal_warns(self):
    doc = self.doc()
    doc["failure_modes"][0]["causes"][0]["previous"] = {"baseline": "BL-004", "occurrence": 5, "detection": 4, "ap": "H"}
    res = self.lint(swf=doc)
    self.assertEqual(res.errors, [])
    self.assertTrue(any("equals the current one" in w for w in res.warnings))

  def test_reaction_needs_layer_and_basis(self):
    doc = self.doc()
    doc["failure_modes"][0]["safety_mechanisms"] = [{"description": "x", "reaction_s": 1.0}]
    res = self.lint(swf=doc)
    self.assertError(res, "must name its layer")
    self.assertError(res, "timing_basis")

  def test_code_derived_needs_ref(self):
    doc = self.doc()
    doc["failure_modes"][0]["safety_mechanisms"] = [{"description": "x", "layer": "host", "reaction_s": 1.0,
                                                     "timing_basis": "code_derived"}]
    self.assertError(self.lint(swf=doc), "needs a timing_ref")

  def test_sotif_split_needs_part(self):
    doc = self.doc()
    doc["structure"][0]["sotif"] = {"boundary": "split"}
    self.assertError(self.lint(swf=doc), "sotif_part")

  def test_unknown_layer_is_schema_error(self):
    doc = self.doc()
    doc["failure_modes"][0]["safety_mechanisms"] = [{"description": "x", "layer": "driver"}]
    self.assertError(self.lint(swf=doc), "schema")


class TestHara(LintFixture):
  def lint_hara(self, hara=None, sfm=None):
    return self.lint(sfm=sfm or SFM, hara=hara or HARA)

  def test_valid(self):
    res = self.lint_hara()
    self.assertEqual(res.errors, [])
    self.assertTrue(any("SG-001 ASIL D" in r for r in res.report))

  def test_wrong_asil(self):
    doc = copy.deepcopy(HARA)
    doc["hazardous_events"][0]["asil"] = "C"
    self.assertError(self.lint_hara(doc), "Table 4 gives D")

  def test_exposure_override(self):
    doc = copy.deepcopy(HARA)
    doc["hazardous_events"][0]["exposure_override"] = {"exposure": "E2", "rationale": "subset"}
    self.assertError(self.lint_hara(doc), "Table 4 gives B")

  def test_safety_goal_asil_is_max(self):
    doc = copy.deepcopy(HARA)
    doc["safety_goals"][0]["asil"] = "B"
    self.assertError(self.lint_hara(doc), "highest hazardous event of its hazards is D")

  def test_uncovered_hazard(self):
    doc = copy.deepcopy(HARA)
    doc["safety_goals"] = []
    self.assertError(self.lint_hara(doc), "not covered by any safety goal")

  def test_back_link_required(self):
    sfm = copy.deepcopy(SFM)
    del sfm["failure_modes"][0]["effects"][0]["hazard"]
    self.assertError(self.lint_hara(sfm=sfm), "SFM-001 has no effect linked to HZ-001")

  def test_forward_link_required(self):
    doc = copy.deepcopy(HARA)
    doc["hazards"][0]["sfm_refs"] = []
    self.assertError(self.lint_hara(doc), "not in its sfm_refs")

  def test_fmea_hazard_must_exist(self):
    sfm = copy.deepcopy(SFM)
    sfm["failure_modes"][0]["effects"][0]["hazard"] = "HZ-999"
    self.assertError(self.lint_hara(sfm=sfm), "HZ-999 not found in the HARA")

  def test_lower_level_fmea_hazard_not_traced_by_hara(self):
    swf = copy.deepcopy(SWF)
    for fm in swf["failure_modes"]:
      for e in fm["effects"]:
        e.update(hazard="HZ-001", severity=10)
    self.assertEqual(self.lint(sfm=SFM, hara=HARA, swf=swf).errors, [])

  def test_guideword_matrix_complete(self):
    doc = copy.deepcopy(HARA)
    doc["guideword_analysis"].pop()
    self.assertError(self.lint_hara(doc), "guide-word matrix missing SFM-FN-001 x M14")

  def test_guideword_matrix_matches_hazard(self):
    doc = copy.deepcopy(HARA)
    doc["guideword_analysis"][2].update(classification="SC", hazards=["HZ-001"])
    self.assertError(self.lint_hara(doc), "guidewords ['M05'] != guide-word matrix ['M03', 'M05']")

  def test_sc_needs_hazard(self):
    doc = copy.deepcopy(HARA)
    del doc["guideword_analysis"][4]["hazards"]
    self.assertError(self.lint_hara(doc), "SC entry must name at least one hazard")

  def _two_situations(self):
    doc = copy.deepcopy(HARA)
    doc["operational_situations"].append(dict(doc["operational_situations"][0], id="OS-002", exposure="E2"))
    return doc

  def test_coverage_complete(self):
    self.assertError(self.lint_hara(self._two_situations()), "situation coverage missing 1 pair(s): HZ-001/OS-002")

  def test_dominated_estimate_checked(self):
    doc = self._two_situations()
    doc["hazardous_events"][0].update(controllability="C2", asil="C")
    doc["safety_goals"][0]["asil"] = "C"
    entry = {"hazard": "HZ-001", "situation": "OS-002", "status": "dominated", "by": "HE-001", "rationale": "x"}
    doc["situation_coverage"].append(dict(entry, estimate=["S3", "E2", "C3"]))
    self.assertEqual(self.lint_hara(doc).errors, [])
    doc["situation_coverage"][-1]["estimate"] = ["S3", "E4", "C3"]
    self.assertError(self.lint_hara(doc), "gives ASIL D, above HE-001 (C)")

  def test_rated_entry_must_match_event(self):
    doc = copy.deepcopy(HARA)
    doc["situation_coverage"][0]["status"] = "not_relevant"
    del doc["situation_coverage"][0]["he"]
    self.assertError(self.lint_hara(doc), "appears 0 times as a rated coverage entry")

  def test_closed_item_needs_resolution(self):
    doc = copy.deepcopy(HARA)
    doc["open_items"][0]["status"] = "closed"
    self.assertError(self.lint_hara(doc), "needs a resolution")

  def test_released_requires_ftti(self):
    doc = copy.deepcopy(HARA)
    doc["analysis"]["status"] = "released"
    self.assertError(self.lint_hara(doc), "requires an FTTI")


class TestFsc(LintFixture):
  def lint_fsc(self, fsc=None):
    return self.lint(sfm=SFM, hara=HARA, fsc=fsc or FSC)

  def test_valid(self):
    res = self.lint_fsc()
    self.assertEqual(res.errors, [])
    self.assertEqual(res.warnings, [])

  def test_parse_asil(self):
    self.assertEqual(fmea_lint.parse_asil("B(D)"), ("B", "D"))
    self.assertEqual(fmea_lint.parse_asil("QM"), ("QM", None))

  def test_inheritance(self):
    doc = copy.deepcopy(FSC)
    doc["fsrs"].append(_fsr("FSR-004", "B", ["EL-02"]))
    self.assertError(self.lint_fsc(doc), "must be inherited from SG-001 (D)")

  def test_decomposition_scheme(self):
    doc = copy.deepcopy(FSC)
    doc["fsrs"][2]["asil"] = "A(D)"
    self.assertError(self.lint_fsc(doc), "is not an ISO 26262-9 scheme")

  def test_decomposed_asil_names_parent(self):
    doc = copy.deepcopy(FSC)
    doc["fsrs"][1]["asil"] = "D(C)"
    self.assertError(self.lint_fsc(doc), "must be written X(D)")

  def test_allocation_union(self):
    doc = copy.deepcopy(FSC)
    doc["fsrs"][0]["allocated_to"] = ["EL-02"]
    self.assertError(self.lint_fsc(doc), "must equal the union")

  def test_no_external_allocation(self):
    doc = copy.deepcopy(FSC)
    doc["fsrs"][1]["allocated_to"] = ["EL-03"]
    self.assertError(self.lint_fsc(doc), "cannot be allocated to external element EL-03")

  def test_capability_gap(self):
    doc = copy.deepcopy(FSC)
    doc["fsrs"][2]["allocated_to"] = ["EL-01", "EL-02"]
    doc["fsrs"][1]["allocated_to"] = ["EL-01"]
    res = self.lint_fsc(doc)
    self.assertTrue(any("capability gap: FSR-002 (D(D)) on EL-01" in w for w in res.warnings), res.warnings)
    doc["analysis"]["status"] = "released"
    self.assertError(self.lint_fsc(doc), "capability gap")

  def test_hara_revision_must_match(self):
    doc = copy.deepcopy(FSC)
    doc["analysis"]["hara_revision"] = "0.0"
    self.assertError(self.lint_fsc(doc), "update the FSC")

  def test_every_goal_needs_fsr_and_timing(self):
    doc = copy.deepcopy(FSC)
    doc["fsrs"], doc["timing"] = [], []
    res = self.lint_fsc(doc)
    self.assertError(res, "no FSR derived from SG-001")
    self.assertError(res, "no timing entry for SG-001")

  def test_fhti_within_ftti(self):
    doc = copy.deepcopy(FSC)
    doc["fsrs"][1]["fhti_ms"] = 1000
    self.assertError(self.lint_fsc(doc), "exceeds SG-001 FTTI 900 ms")


class TestDfa(LintFixture):
  def lint_dfa(self, dfa=None):
    return self.lint(sfm=SFM, hara=HARA, fsc=FSC, dfa=dfa or DFA)

  def test_valid(self):
    self.assertEqual(self.lint_dfa().errors, [])

  def test_status_derived_from_dfis(self):
    doc = copy.deepcopy(DFA)
    doc["dfis"][0]["assessment"] = "open"
    self.assertError(self.lint_dfa(doc), "status accepted but its DFIs give conditional")
    doc["dfis"][0]["assessment"] = "insufficient"
    self.assertError(self.lint_dfa(doc), "its DFIs give not_accepted")

  def test_sufficient_needs_verified_measure(self):
    doc = copy.deepcopy(DFA)
    doc["measures"][0]["status"] = "existing_unverified"
    self.assertError(self.lint_dfa(doc), "requires at least one existing (verified) measure")

  def test_every_fsc_decomposition_analyzed(self):
    doc = copy.deepcopy(DFA)
    doc["decompositions"], doc["dfis"] = [], []
    self.assertError(self.lint_dfa(doc), "FSC decomposition FSR-001 not analyzed")

  def test_channels_match_fsc(self):
    doc = copy.deepcopy(DFA)
    doc["decompositions"][0]["channels"][0]["elements"] = ["EL-01"]
    self.assertError(self.lint_dfa(doc), "!= FSC allocation")

  def test_category_coverage(self):
    doc = copy.deepcopy(DFA)
    doc["categories"][1]["applicable"] = True
    self.assertError(self.lint_dfa(doc), "CAT-02: applicable category has no DFI")
    doc = copy.deepcopy(DFA)
    doc["dfis"][0]["category"] = "CAT-02"
    self.assertError(self.lint_dfa(doc), "declared not applicable")

  def test_fsc_revision_pinned(self):
    doc = copy.deepcopy(DFA)
    doc["analysis"]["fsc_revision"] = "0.0"
    self.assertError(self.lint_dfa(doc), "update the DFA")


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

  def test_targets_replace_asil_target(self):
    doc = copy.deepcopy(FMEDA)
    doc["analysis"]["asil_target"] = "D"
    doc["analysis"]["targets"] = [{"goal": "SG-01", "asil": "B", "basis": "test"}]
    res = self.lint(fmd=doc)
    self.assertFalse(any("ASIL D" in w for w in res.warnings))
    self.assertTrue(any("fmd.yaml SG-01: λ=" in r for r in res.report), res.report)

  def test_per_goal_classification(self):
    doc = copy.deepcopy(FMEDA)
    doc["analysis"]["targets"] = [{"goal": "SG-01", "asil": "B", "basis": "t"}, {"goal": "SG-05", "asil": "B", "basis": "t"}]
    doc["components"][0]["failure_modes"][1]["per_goal"] = [{"goal": "SG-05", "violates_sg_directly": True, "reason": "t"}]
    self.assertAlmostEqual(fmea_lint.fmeda_metrics(doc, "SG-01")["spf_fit"], 0.0)
    m = fmea_lint.fmeda_metrics(doc, "SG-05")
    self.assertAlmostEqual(m["spf_fit"], 30.0)  # FMD-002 counts as single-point for SG-05, its lf mechanism ignored
    self.assertAlmostEqual(m["spfm"], 1 - 30.5 / 100)
    self.assertEqual(self.lint(fmd=doc).errors, [])

  def test_per_goal_must_name_a_target(self):
    doc = copy.deepcopy(FMEDA)
    doc["components"][0]["failure_modes"][1]["per_goal"] = [{"goal": "SG-05", "violates_sg_directly": True, "reason": "t"}]
    self.assertError(self.lint(fmd=doc), "per_goal SG-05 is not in analysis.targets")


class TestHaraExport(unittest.TestCase):
  def test_export_matches_yaml(self):
    import export_hara_xlsx
    wb = export_hara_xlsx.build(REPO)
    hara = fmea_lint.load_yaml((REPO / "assurance/08-analyses/fmea/analyses/hara.yaml").read_text())
    self.assertIn("12_HARA_Worksheet", wb.sheetnames)
    self.assertIn("13_Safety_Goals", wb.sheetnames)
    ws = wb["12_HARA_Worksheet"]
    header_row = next(r for r in range(1, 10) if ws.cell(r, 1).value == "HARA ID")
    headers = [c.value for c in ws[header_row]]
    rows = [r for r in ws.iter_rows(min_row=header_row + 1, values_only=True) if r[0]]
    self.assertEqual([r[0] for r in rows], [he["id"] for he in hara["hazardous_events"]])
    for row, he in zip(rows, hara["hazardous_events"], strict=True):
      self.assertEqual(row[headers.index("ASIL")], he["asil"])
      self.assertEqual(row[headers.index("S")], he["severity"])


class TestFscExport(unittest.TestCase):
  def test_export_matches_yaml(self):
    import export_fsc_xlsx
    wb = export_fsc_xlsx.build(REPO)
    fsc = fmea_lint.load_yaml((REPO / "assurance/08-analyses/fmea/analyses/fsc.yaml").read_text())
    ws = wb["05_FSR_Catalog"]
    header_row = next(r for r in range(1, 10) if ws.cell(r, 1).value == "FSR_ID")
    rows = [r for r in ws.iter_rows(min_row=header_row + 1, values_only=True) if r[0]]
    self.assertEqual([(r[0], r[2]) for r in rows], [(f["id"], f["asil"]) for f in fsc["fsrs"]])
    nodes = wb["03_System_Block_Diagram"]
    ids = [r[0] for r in nodes.iter_rows(min_row=header_row + 1, values_only=True) if r[0]]
    self.assertTrue(all(i.startswith("N") for i in ids))


class TestVehicleCatalog(unittest.TestCase):
  def test_catalog_up_to_date(self):
    import gen_vehicle_catalog
    self.assertEqual(gen_vehicle_catalog.main(["--check"]), 0)

  def test_counts(self):
    import gen_vehicle_catalog
    cars = gen_vehicle_catalog.parse_cars((REPO / "docs/CARS.md").read_text())
    self.assertEqual(len(cars), 334)  # 335 table rows minus the comma body robot
    self.assertTrue(all(c["harness"] for c in cars))


class TestItemExport(unittest.TestCase):
  def test_export_reads_item_definition(self):
    import export_item_xlsx
    wb = export_item_xlsx.build(REPO)
    ids = [r[0] for r in wb["03_Functions"].iter_rows(min_row=2, values_only=True) if r[0]]
    self.assertEqual(ids, [f"F{i}" for i in range(1, 9)])
    sfm = fmea_lint.load_yaml((REPO / "assurance/08-analyses/fmea/analyses/system-fmea.yaml").read_text())
    self.assertEqual(len(ids), len(sfm["functions"]))  # item functions F1-F8 = System FMEA SFM-FN-001..008
    modes = [r[0] for r in wb["07_Operating_Modes"].iter_rows(min_row=2, values_only=True) if r[0]]
    fsc = fmea_lint.load_yaml((REPO / "assurance/08-analyses/fmea/analyses/fsc.yaml").read_text())
    self.assertEqual(modes, [m["id"] for m in fsc["operating_modes"]])
    self.assertEqual(wb["13_Vehicle_Catalog"].max_row - 1, 334)


class TestFmeaExport(unittest.TestCase):
  def _doc(self, name):
    return fmea_lint.load_yaml((REPO / f"assurance/08-analyses/fmea/analyses/{name}.yaml").read_text())

  def test_one_row_per_cause(self):
    import export_fmea_xlsx
    fsc = self._doc("fsc")
    for kind, name, elem_key in (("sw", "sw-fmea", "element_id"), ("dfmea", "dfmea", "focus_element_id")):
      doc = self._doc(name)
      data = export_fmea_xlsx.to_builder_json(kind, doc, fsc)
      causes = {c["id"]: c for fm in doc["failure_modes"] for c in fm["causes"]}
      self.assertEqual([r["id"] for r in data["failure_modes"]], list(causes))
      for r in data["failure_modes"]:
        self.assertEqual((r["occurrence"], r["detection"]), (causes[r["id"]]["occurrence"], causes[r["id"]]["detection"]))
        self.assertTrue(r[elem_key])

  def test_builder_uses_rating_table_ap(self):
    import export_fmea_xlsx
    gen = Path(tempfile.mkdtemp()) / "fake_generator.py"
    self.addCleanup(shutil.rmtree, gen.parent)
    gen.write_text("\n".join(["def compute_ap(s, o, d):", "  return 'H' if s >= 9 else 'L'",
                              "def generate(i, o):", "  return compute_ap(10, 3, 4)",
                              "def build_catalog(wb):", "  pass", ""]))
    mod = export_fmea_xlsx.load_generator(gen, [], {"refs": [], "crossref": [], "sc": None})
    self.assertEqual(mod.generate("in.json", "out.xlsx"), "L")  # AIAG-VDA table, not the builders' S>=9 rule


class TestPfmeaAndSystemExport(unittest.TestCase):
  def _doc(self, name):
    return fmea_lint.load_yaml((REPO / f"assurance/08-analyses/fmea/analyses/{name}.yaml").read_text())

  def test_pfmea_rows(self):
    import export_pfmea_xlsx
    doc = self._doc("pfmea")
    data = export_pfmea_xlsx.to_pfmea_json(doc, None)
    causes = [c["id"] for fm in doc["failure_modes"] for c in fm["causes"]]
    self.assertEqual([r["failure_cause"].split("]")[0][1:] for r in data["failure_modes"]], causes)
    steps = {e["id"] for e in doc["structure"] if e["kind"] == "process_step"}
    self.assertEqual({f["step_id"] for f in data["process_flow"]}, steps)
    self.assertEqual(set(export_pfmea_xlsx.CONTROL_STEPS), {fm["id"] for fm in doc["failure_modes"]})

  def test_system_fmea_unrated_rows_have_no_ap(self):
    import export_fmea_xlsx
    gen = Path(tempfile.mkdtemp()) / "fake_generator.py"
    self.addCleanup(shutil.rmtree, gen.parent)
    gen.write_text("\n".join(["def compute_ap(s, o, d):", "  return 'H'", "def generate(i, o):", "  return compute_ap(10, None, None)",
                              "def build_catalog(wb):", "  pass", ""]))
    mod = export_fmea_xlsx.load_generator(gen, [], {"refs": [], "crossref": [], "sc": None})
    self.assertEqual(mod.generate("in.json", "out.xlsx"), export_fmea_xlsx.NOT_RATED)


class TestPfmeaDetectionRule(LintFixture):
  def test_pfmea_detection_accepts_procedure_ref(self):
    doc = fmea_lint.load_yaml((REPO / "assurance/08-analyses/fmea/analyses/pfmea.yaml").read_text())
    doc["analysis"]["baseline"] = "BL-001"
    for fm in doc["failure_modes"]:
      for e in fm["effects"]:
        e.pop("hazard", None)
      for c in fm["causes"]:
        c.pop("linked_failure_mode", None)
        for ctl in c["prevention_controls"] + c["detection_controls"]:
          ctl.pop("test", None)
    res = self.lint(pfm=doc)
    self.assertFalse([e for e in res.errors if "detection" in e], res.errors)
    c = doc["failure_modes"][0]["causes"][0]
    c["detection_controls"] = [{"description": "inspection"}]
    self.assertError(self.lint(pfm=doc), "must name a `test` path or a `ref`")


class TestFmedaExport(unittest.TestCase):
  def test_repo_fmedas_compute_metrics(self):
    for name in ("fmeda-sg001", "fmeda-sg009"):
      doc = fmea_lint.load_yaml((REPO / f"assurance/08-analyses/fmea/analyses/{name}.yaml").read_text())
      m = fmea_lint.fmeda_metrics(doc)
      self.assertIsNotNone(m, name)
      self.assertTrue(0 < m["spfm"] <= 1 and 0 < m["lfm"] <= 1)

  def test_workbook_rows_and_labels(self):
    import export_fmeda_xlsx
    doc = fmea_lint.load_yaml((REPO / "assurance/08-analyses/fmea/analyses/fmeda-sg009.yaml").read_text())
    ws = export_fmeda_xlsx.build(doc, "x.yaml")["06_FMEDA_Worksheet"]
    ids = [ws.cell(r, export_fmeda_xlsx.C["Row ID"]).value for r in range(2, ws.max_row + 1)]
    self.assertEqual(ids, [fm["id"] for c in doc["components"] for fm in c["failure_modes"]])
    dist = [ws.cell(r, export_fmeda_xlsx.C["Distribution %"]).value for r in range(2, ws.max_row + 1)]
    self.assertAlmostEqual(sum(dist), 100 * len(doc["components"]))
    headers = [ws.cell(1, c).value.lower() for c in range(1, ws.max_column + 1)]
    self.assertLess(headers.index("lambda s"), headers.index("lambda spf"))  # reviewer partial-match order

  def test_workbook_has_one_metric_row_per_target(self):
    import export_fmeda_xlsx
    doc = fmea_lint.load_yaml((REPO / "assurance/08-analyses/fmea/analyses/fmeda-sg001.yaml").read_text())
    wb = export_fmeda_xlsx.build(doc, "x.yaml")
    goals = [r[0] for r in wb["07_SPFM_Calculation"].iter_rows(min_row=2, values_only=True)]
    self.assertEqual(goals, [g for g, _, _ in export_fmeda_xlsx.target_rows(doc)])
    self.assertNotIn("ASIL D", " ".join(str(r) for r in wb["07_SPFM_Calculation"].iter_rows(values_only=True)))
    history = [r[0] for r in wb["01_Document_Control"].iter_rows(min_row=2, values_only=True)]
    self.assertEqual(history, [h["revision"] for h in doc["analysis"]["history"]])

  def test_whatif_scenarios_reproduce_wp_h_03(self):
    import fmeda_whatif
    docs = {n: fmea_lint.load_yaml((REPO / f"assurance/08-analyses/fmea/analyses/{n}.yaml").read_text()) for n in fmeda_whatif.SOURCES}
    sets = {}
    for sc in fmeda_whatif.SCENARIOS:
      sets.setdefault(sc["file"], {}).update(sc["sets"])
    m = fmea_lint.fmeda_metrics(fmeda_whatif.scenario_doc(docs["fmeda-sg001"], sets["fmeda-sg001"]), "SG-01")
    self.assertAlmostEqual(m["spfm"], 0.991, places=3)  # WP-H-03 §6.3: 99.1 %, LFM 95.4 %
    self.assertAlmostEqual(m["lfm"], 0.954, places=3)
    m = fmea_lint.fmeda_metrics(fmeda_whatif.scenario_doc(docs["fmeda-sg009"], sets["fmeda-sg009"]), "SG-07")
    self.assertAlmostEqual(m["spfm"], 0.945, places=3)  # WP-H-03 §6.3: 94.5 %

  def test_committed_review_workbooks_current(self):
    import export_fmeda_xlsx
    self.assertEqual(export_fmeda_xlsx.main(["--check", "--root", str(REPO)]), 0)



class TestFtaFmeaMap(unittest.TestCase):
  """FTA <-> FMEA cross-mapping (fta-fmea-map.yaml), on a two-event tree."""
  FTA = "\n".join([
    "## 2. FTA — SG-01: test goal",
    "",
    "```",
    "TE-01 Top                                                   [OR]",
    "├── G1.1 Both                                               [AND]",
    "│   ├── BE-1.01 Software defect",
    "│   └── UE-1.02 Outside the item",
    "└── BE-1.03 Random fault                                     (SPF, random HW)",
    "```",
    "",
  ])
  WP = "| **SG-01** | No lateral motion | **C** | HE-01.1–01.2 |\n"

  def fm(self, fid, hazard="HZ-001", detection=8):
    return {"id": fid, "effects": [{"level": "end", "description": "x", "hazard": hazard}],
            "causes": [{"id": fid + ".C1", "detection": detection}]}

  def doc(self, **over):
    d = {"schema_version": 1, "source": "fta.md", "scope": ["SG-01"],
         "events": [{"id": "BE-1.01", "class": "systematic_sw", "fmea": ["SWF-001"]},
                    {"id": "UE-1.02", "class": "external", "ref": "AOU-01"},
                    {"id": "BE-1.03", "class": "random_hw", "fmeda": ["fmeda-x:FMD-001"]}],
         "gates": [], "not_in_fta": []}
    d.update(over)
    return d

  def check(self, doc, fms=None):
    with tempfile.TemporaryDirectory() as d:
      root = Path(d)
      fta_dir = root / "assurance" / "08-analyses" / "fta"
      fta_dir.mkdir(parents=True)
      shutil.copy(fmea_lint.ROOT / "assurance" / "08-analyses" / "fta" / "fta_diagrams.py", fta_dir)
      (root / "fta.md").write_text(self.FTA)
      (root / "wp.md").write_text(self.WP)
      (root / fmea_lint.SAFETY_DIR).mkdir(parents=True)
      (root / fmea_lint.SAFETY_DIR / "hara-mapping.yaml").write_text(yaml.safe_dump(
        {"target": "wp.md", "hazards": [{"second": "HZ-001", "wp_c03": ["H-01"], "events": ["HE-01.1"]},
                                        {"second": "HZ-002", "wp_c03": ["H-02"], "events": ["HE-02.1"]}]}))
      ctx = fmea_lint.Context(root)
      for f in fms if fms is not None else [self.fm("SWF-001")]:
        ctx.fm_index[f["id"]] = f
      ctx.fmeda_ids["fmeda-x"] = {"FMD-001"}
      res = fmea_lint.Result()
      sys.modules.pop("fta_diagrams", None)
      fmea_lint.check_fta_fmea_map("map", doc, ctx, res)
      sys.modules.pop("fta_diagrams", None)
      return res

  def test_goal_events_ranges(self):
    self.assertEqual(fmea_lint.goal_events(self.WP), {"SG-01": {"HE-01.1", "HE-01.2"}})

  def test_valid(self):
    res = self.check(self.doc())
    self.assertEqual(res.errors, [])
    self.assertTrue(any("FTA-FMEA map SG-01: 3 events" in r for r in res.report))

  def test_unmapped_event(self):
    doc = self.doc()
    doc["events"] = doc["events"][:2]
    self.assertTrue(any("BE-1.03 is in the SG-01 tree but not mapped" in e for e in self.check(doc).errors))

  def test_unknown_references(self):
    doc = self.doc()
    doc["events"][0]["fmea"] = ["SWF-999"]
    doc["events"][2]["fmeda"] = ["fmeda-x:FMD-404"]
    errors = " ".join(self.check(doc).errors)
    self.assertIn("SWF-999 not found", errors)
    self.assertIn("fmeda-x:FMD-404 not found", errors)

  def test_class_needs_matching_analysis(self):
    doc = self.doc()
    doc["events"][2] = {"id": "BE-1.03", "class": "random_hw", "fmea": ["SWF-001"]}
    self.assertTrue(any("random_hw event needs one of DFM, FMEDA" in e for e in self.check(doc).errors))

  def test_unbacked_event_needs_gap(self):
    doc = self.doc()
    doc["events"][0]["fmea"] = []
    self.assertTrue(any("no FMEA backing and no gap" in e for e in self.check(doc, []).errors))
    doc["events"][0]["gap"] = "no FMEA row yet"
    res = self.check(doc, [])
    self.assertEqual(res.errors, [])
    self.assertTrue(any("no FMEA backing: no FMEA row yet" in w for w in res.warnings))

  def test_fmea_mode_reaching_the_goal_must_be_in_the_tree(self):
    fms = [self.fm("SWF-001"), self.fm("SWF-002")]
    errors = self.check(self.doc(), fms).errors
    self.assertTrue(any("SWF-002 cites HZ-001 but no SG-01 event or gate cites it" in e for e in errors))
    doc = self.doc(not_in_fta=[{"fm": "SWF-002", "goal": "SG-01", "kind": "tree_gap", "reason": "branch missing"}])
    res = self.check(doc, fms)
    self.assertEqual(res.errors, [])
    self.assertTrue(any("tree gaps 1" in r for r in res.report))
    # a mode reaching another goal's hazard only is not required here
    self.assertEqual(self.check(self.doc(), [self.fm("SWF-001"), self.fm("SWF-003", "HZ-002")]).errors, [])

  def test_gate_mapping_counts_as_cited(self):
    fms = [self.fm("SWF-001"), self.fm("SFM-001")]
    self.assertEqual(self.check(self.doc(gates=[{"id": "G1.1", "fmea": ["SFM-001"]}]), fms).errors, [])

  def test_cited_mode_without_the_goal_hazard_warns(self):
    res = self.check(self.doc(), [self.fm("SWF-001", "HZ-002")])
    self.assertTrue(any("SWF-001 is cited in the SG-01 tree but its effects cite none of HZ-001" in w for w in res.warnings))

  def test_single_point_with_claimed_detection_warns(self):
    doc = self.doc()
    doc["events"][2] = {"id": "BE-1.03", "class": "random_hw", "fmea": ["DFM-001"]}
    res = self.check(doc, [self.fm("SWF-001"), self.fm("DFM-001", detection=3)])
    self.assertTrue(any("BE-1.03" in w and "single point" in w for w in res.warnings))

  def test_not_in_fta_row_for_a_cited_mode(self):
    doc = self.doc(not_in_fta=[{"fm": "SWF-001", "goal": "SG-01", "kind": "tree_gap", "reason": "branch missing"}])
    self.assertTrue(any("SWF-001 is in not_in_fta for SG-01 but an event or gate of the tree cites it" in e
                        for e in self.check(doc).errors))

  def test_event_outside_the_scoped_trees_warns(self):
    doc = self.doc()
    doc["events"].append({"id": "BE-9.01", "class": "systematic_sw", "fmea": ["SWF-001"]})
    res = self.check(doc)
    self.assertEqual(res.errors, [])
    self.assertTrue(any("BE-9.01" in w and "not in the tree of any goal in scope" in w for w in res.warnings))

  def test_real_map_is_clean(self):
    res = fmea_lint.lint()
    self.assertEqual([e for e in res.errors if "fta-fmea-map" in e], [])


if __name__ == "__main__":
  unittest.main()


class TestStpaMap(unittest.TestCase):
  """STPA loss scenarios <-> fault trees, FMEA and TSRs (stpa-map.yaml)."""
  STPA = "\n".join([
    "| H-01 | Lateral motion | L-1 | SG-01 |",
    "| H-STPA-1 | Unsupervised | L-1 | none |",
    "| UCA-01 | P | Engages badly | H-01 |",
    "| UCA-40 | C4 EPS | Overpowers | H-01 | AOU-01 |",
    "| LS-01 | UCA-01 | Scenario | Type | x | y |",
  ])
  FTA = TestFtaFmeaMap.FTA
  TSR = "| TSR-101 | limit |\n"

  def doc(self, **over):
    d = {"schema_version": 1, "source": "stpa.md", "fta_source": "fta.md", "tsr_source": "tsr.md",
         "hazards": {"H-01": ["SG-01"], "H-STPA-1": []},
         "external_ucas": [{"uca": "UCA-40", "assumption": "AOU-01"}],
         "scenarios": [{"id": "LS-01", "ucas": ["UCA-01"], "hazards": ["H-01"], "status": "covered",
                        "fta": ["BE-1.01"], "fmea": ["SWF-001"], "requirements": ["TSR-101"]}]}
    d.update(over)
    return d

  def check(self, doc):
    with tempfile.TemporaryDirectory() as d:
      root = Path(d)
      fta_dir = root / "assurance" / "08-analyses" / "fta"
      fta_dir.mkdir(parents=True)
      shutil.copy(fmea_lint.ROOT / "assurance" / "08-analyses" / "fta" / "fta_diagrams.py", fta_dir)
      (root / "stpa.md").write_text(self.STPA)
      (root / "fta.md").write_text(self.FTA)
      (root / "tsr.md").write_text(self.TSR)
      ctx = fmea_lint.Context(root)
      ctx.fm_index["SWF-001"] = {"id": "SWF-001", "effects": [], "causes": []}
      res = fmea_lint.Result()
      sys.modules.pop("fta_diagrams", None)
      fmea_lint.check_stpa_map("map", doc, ctx, res)
      sys.modules.pop("fta_diagrams", None)
      return res

  def test_valid(self):
    res = self.check(self.doc())
    self.assertEqual(res.errors, [])
    self.assertTrue(any("STPA map: 2 UCAs (1 with a loss scenario, 1 external); 1 loss scenarios" in r for r in res.report))

  def test_uca_without_scenario(self):
    errors = " ".join(self.check(self.doc(external_ucas=[])).errors)
    self.assertIn("UCA-40", errors)
    self.assertIn("no loss scenario", errors)

  def test_scenario_sets_match_the_document(self):
    doc = self.doc()
    doc["scenarios"].append(dict(doc["scenarios"][0], id="LS-99"))
    self.assertTrue(any("LS-99" in e and "no such loss scenario" in e for e in self.check(doc).errors))
    self.assertTrue(any("LS-01" in e and "not in the map" in e for e in self.check(self.doc(scenarios=[])).errors))

  def test_unknown_references(self):
    doc = self.doc()
    doc["scenarios"][0].update(fta=["BE-9.99"], fmea=["SWF-999"], requirements=["TSR-999"])
    errors = " ".join(self.check(doc).errors)
    for ref in ("BE-9.99", "SWF-999", "TSR-999"):
      self.assertIn(ref, errors)

  def test_status_rules(self):
    doc = self.doc()
    doc["scenarios"][0].update(fta=[], fmea=[])
    self.assertTrue(any("needs at least one" in e for e in self.check(doc).errors))
    doc["scenarios"][0].update(status="new")
    self.assertTrue(any("needs a finding" in e for e in self.check(doc).errors))
    doc["scenarios"][0]["finding"] = "no row anywhere"
    self.assertEqual(self.check(doc).errors, [])

  def test_event_outside_the_hazards_tree_warns(self):
    second = "\n".join(["## 3. FTA — SG-02: other goal", "", "```",
                         "TE-02 Top                                                   [OR]",
                         "├── BE-2.01 One", "└── BE-2.02 Two", "```", ""])
    self.FTA = TestFtaFmeaMap.FTA + second
    self.STPA = TestStpaMap.STPA + "\n| H-02 | Other | L-1 | SG-02 |"
    doc = self.doc(hazards={"H-01": ["SG-01"], "H-02": ["SG-02"], "H-STPA-1": []})
    self.assertEqual(self.check(doc).warnings, [])
    doc["scenarios"][0]["hazards"] = ["H-02"]
    res = self.check(doc)
    self.assertEqual(res.errors, [])
    self.assertTrue(any("BE-1.01 is in no fault tree of SG-02" in w for w in res.warnings))

  def test_real_map_is_clean(self):
    res = fmea_lint.lint()
    self.assertEqual([e for e in res.errors if "stpa-map" in e], [])


class TestHaraMapping(unittest.TestCase):
  WP = "\n".join([
    "### 5.1 H-01 Unintended lateral motion",
    "| HE-01.1 | OS-01 | x | S3 | E4 | C2 | **C** | r |",
    "### 5.2 H-02 Loss of lateral control",
    "| **SG-01** | No lateral motion | **C** ⚠ (D if AOU-01 fails) | HE-01.1 |",
    "| **SG-02** | No silent loss | **B** | HE-02.1 |",
  ])

  def mapping(self, **goal):
    row = {"second": "SG-001", "second_asil": "D", "wp_c03": ["SG-01"], "wp_c03_asil": "C", "agreement": "second_higher",
           "decision": "RD-1"}
    row.update(goal)
    return {"schema_version": 1, "target": "wp.md", "decisions": ["RD-1"],
            "hazards": [{"second": "HZ-001", "wp_c03": ["H-01"], "events": ["HE-01.1"]}], "goals": [row]}

  def check(self, doc, hazards=("HZ-001",), goals=None):
    with tempfile.TemporaryDirectory() as d:
      (Path(d) / "wp.md").write_text(self.WP)
      ctx = fmea_lint.Context(Path(d))
      ctx.hazards = set(hazards)
      ctx.safety_goals = goals or {"SG-001": {"asil": "D"}}
      res = fmea_lint.Result()
      fmea_lint.check_hara_mapping("map", doc, ctx, res)
      return res.errors

  def test_parse(self):
    self.assertEqual(fmea_lint.parse_wp_c03(self.WP), ({"H-01", "H-02"}, {"HE-01.1"}, {"SG-01": "C", "SG-02": "B"}))

  def test_valid(self):
    self.assertEqual(self.check(self.mapping()), [])

  def test_unmapped_hazard_and_goal(self):
    errors = self.check(self.mapping(), hazards=("HZ-001", "HZ-002"), goals={"SG-001": {"asil": "D"}, "SG-002": {"asil": "B"}})
    self.assertTrue(any("HZ-002 is not mapped" in e for e in errors))
    self.assertTrue(any("SG-002 is not mapped" in e for e in errors))

  def test_unknown_wp_c03_ids(self):
    doc = self.mapping(wp_c03=["SG-09"])
    doc["hazards"][0]["events"] = ["HE-09.9"]
    errors = " ".join(self.check(doc))
    self.assertIn("SG-09 not found", errors)
    self.assertIn("HE-09.9 not found", errors)

  def test_asils_must_match_sources(self):
    self.assertTrue(any("second_asil C != D" in e for e in self.check(self.mapping(second_asil="C"))))
    self.assertTrue(any("wp_c03_asil B != C" in e for e in self.check(self.mapping(wp_c03_asil="B"))))

  def test_agreement_follows_asils(self):
    self.assertTrue(any("the ASILs give second_higher" in e for e in self.check(self.mapping(agreement="same"))))
    doc = self.mapping(wp_c03=["SG-01", "SG-02"])  # max of the targets
    self.assertEqual(self.check(doc), [])

  def test_difference_needs_listed_decision(self):
    self.assertTrue(any("needs a reconciliation decision" in e for e in self.check(self.mapping(decision=None))))
    self.assertTrue(any("RD-9 not listed" in e for e in self.check(self.mapping(decision="RD-9"))))

  def test_no_counterpart(self):
    doc = self.mapping(wp_c03=[], wp_c03_asil=None, agreement="no_counterpart")
    self.assertEqual(self.check(doc), [])
    doc["hazards"][0] = {"second": "HZ-001", "wp_c03": [], "events": []}
    self.assertTrue(any("needs a note" in e for e in self.check(doc)))


WP_S04_TEXT = """# WP-S-04

### 3.7 Summary of FTTIs and budgets

| SG / fault class | FTTI | FDTI budget | FRTI budget | Margin |
|---|---|---|---|---|
| SG-01 continuous limits | per frame | 0 | ≤ 10 ms | — |
| SG-01 MCU execution fault | 0.5 s | ≤ 0.1 s | ≤ 0.1 s | ≥ 0.3 s |
| SG-05 brake/cancel | 200 ms | ≤ 30 ms | ≤ 10 ms | TBD |

## 4. Current detection and reaction times
"""


def msr_sfm(**msr_overrides):
  """System FMEA fixture whose cause carries an MSR row rated M 6 on code-derived timing (S10 F5 M6 -> H, with an action)."""
  doc = copy.deepcopy(SFM)
  doc["analysis"]["rating_tables"] = "RT-3"
  fm = doc["failure_modes"][0]
  fm["safety_mechanisms"] = [{"description": "IWDG resets the MCU; relay releases", "ref": "openpilot/selfdrive/controls/controlsd.py"}]
  msr = {
    "mechanisms": [1], "diagnostic": "IWDG expires", "system_response": "MCU reset and relay release",
    "effect_after_response": "Assist lost with alert", "severity_after": 8, "frequency": 5, "monitoring": 6, "ap": "H",
    "timing": {"ftti_ref": "SG-01 MCU execution fault", "ftti_ms": 500, "fdti_ms": 90, "frti_ms": 100, "basis": "code_derived"},
    "evidence": [{"description": "watchdog test", "test": "openpilot/selfdrive/controls/tests/test_latcontrol.py"}],
    "actions": ["SFM-ACT-002"],
  }
  msr.update(msr_overrides)
  fm["causes"][0]["msr"] = msr
  doc["actions"].append({"id": "SFM-ACT-002", "kind": "monitoring", "description": "Measure IWDG reaction on HIL", "status": "open"})
  return doc


class TestMsrActionPriority(unittest.TestCase):
  # rating-tables.md section 7.4, AIAG-VDA FMEA-MSR handbook table for S 9-10 (RT-3, DQ-207 A): F -> AP for M = 1..10
  HANDBOOK = {
    10: {10: "HHHHHHHHHH", 9: "HHHHHHHHHH", 8: "HHHHHHHHHH", 7: "HHHHHHHHHH", 6: "HHHHHHHHHH", 5: "HHHHHHHHHH",
         4: "MHHHHHHHHH", 3: "LMMHHHHHHH", 2: "LLLMMMMMMM", 1: "LLLLLLLLLL"},
    9: {10: "HHHHHHHHHH", 9: "HHHHHHHHHH", 8: "HHHHHHHHHH", 7: "HHHHHHHHHH", 6: "HHHHHHHHHH", 5: "HHHHHHHHHH",
        4: "HHHHHHHHHH", 3: "LHHHHHHHHH", 2: "LHHHHHHHHH", 1: "LLLLLLLLLL"},
  }

  def test_handbook_table_s9_s10_every_cell(self):
    for s, rows in self.HANDBOOK.items():
      self.assertFalse(fmea_lint.msr_ap_provisional(s))
      for f, cells in rows.items():
        for m in range(1, 11):
          self.assertEqual(fmea_lint.compute_ap_msr(s, 1, f, m), cells[m - 1], f"S{s} F{f} M{m}")

  def test_handbook_rates_original_severity_at_m1(self):
    self.assertEqual(fmea_lint.compute_ap_msr(10, 4, 4, 1), "M")  # not the S 4 row
    self.assertEqual(fmea_lint.compute_ap_msr(9, 2, 3, 1), "L")

  def test_provisional_stand_in_below_s9_is_section_5_with_f_and_m(self):
    self.assertTrue(fmea_lint.AP_MSR_PROVISIONAL)
    for s in range(1, 9):
      self.assertTrue(fmea_lint.msr_ap_provisional(s))
      for f in range(1, 11):
        for m in range(2, 11):
          self.assertEqual(fmea_lint.compute_ap_msr(s, 1, f, m), fmea_lint.compute_ap(s, f, m), f"S{s} F{f} M{m}")

  def test_stand_in_m1_rates_severity_after_response(self):
    self.assertEqual(fmea_lint.compute_ap_msr(8, 3, 9, 1), fmea_lint.compute_ap(3, 9, 1))
    self.assertEqual(fmea_lint.compute_ap_msr(8, 3, 9, 2), fmea_lint.compute_ap(8, 9, 2))

  def test_rt_version_between(self):
    self.assertTrue(fmea_lint.rt_version_between("RT-2", "RT-1", "RT-3"))
    self.assertFalse(fmea_lint.rt_version_between("RT-4", "RT-1", "RT-3"))
    self.assertFalse(fmea_lint.rt_version_between("RT-x", "RT-1", "RT-3"))

  def test_out_of_range(self):
    with self.assertRaises(ValueError):
      fmea_lint.compute_ap_msr(10, 0, 5, 5)

  def test_ftti_rows(self):
    rows = fmea_lint.parse_ftti_rows(WP_S04_TEXT)
    self.assertEqual(rows, {"SG-01 continuous limits": None, "SG-01 MCU execution fault": 500.0, "SG-05 brake/cancel": 200.0})

  def test_repository_wp_s04_parses(self):
    rows = fmea_lint.parse_ftti_rows((REPO / fmea_lint.WP_S04).read_text())
    self.assertEqual(rows.get("SG-01 MCU execution fault"), 500.0)

  def test_rating_tables_document_section_7(self):
    text = (REPO / "assurance/08-analyses/fmea/rating-tables.md").read_text()
    self.assertIn("## 7. FMEA-MSR", text)
    self.assertEqual(fmea_lint.sod_unchanged_since(REPO), "RT-1")


class TestMsrRules(LintFixture):
  def setUp(self):
    super().setUp()
    wp = self.tmp / fmea_lint.WP_S04
    wp.parent.mkdir(parents=True, exist_ok=True)
    wp.write_text(WP_S04_TEXT)
    rt = self.tmp / "assurance/08-analyses/fmea/rating-tables.md"
    self.assertIn("RT-3", rt.read_text())

  def errors(self, doc, **more):
    return self.lint(sfm=doc, **more).errors

  def test_valid_row(self):
    res = self.lint(sfm=msr_sfm())
    self.assertEqual(res.errors, [])
    self.assertIn("FMEA-MSR: 1 of 1 in-scope causes rated (H=1 M=0 L=0)", res.report[1])

  def test_wrong_ap(self):
    self.assertError(self.lint(sfm=msr_sfm(ap="L")), "msr ap is L, table gives H")

  def test_ap_h_needs_action_or_rationale(self):
    doc = msr_sfm(actions=[])
    doc["actions"].pop()
    self.assertError(self.lint(sfm=doc), "MSR AP=H requires")
    doc["failure_modes"][0]["causes"][0]["msr"]["rationale"] = "Bounded by the relay release"
    self.assertEqual(self.errors(doc), [])

  def test_unknown_timing_caps_monitoring(self):
    self.assertError(self.lint(sfm=msr_sfm(timing={"basis": "unknown"})), "timing basis unknown")
    self.assertEqual(self.errors(msr_sfm(timing={"basis": "unknown"}, monitoring=7, ap="H")), [])

  def test_timing_must_fit_ftti(self):
    t = {"ftti_ref": "SG-01 MCU execution fault", "ftti_ms": 500, "fdti_ms": 400, "frti_ms": 200, "basis": "code_derived"}
    self.assertError(self.lint(sfm=msr_sfm(timing=t)), "exceeds the FTTI")

  def test_ftti_must_match_wp_s04(self):
    t = {"ftti_ref": "SG-01 MCU execution fault", "ftti_ms": 1000, "fdti_ms": 90, "frti_ms": 100, "basis": "code_derived"}
    self.assertError(self.lint(sfm=msr_sfm(timing=t)), "!= 500 ms in WP-S-04")
    t["ftti_ref"] = "SG-09 nothing"
    self.assertError(self.lint(sfm=msr_sfm(timing=t)), "is not a row of WP-S-04")
    t.update(ftti_ref="SG-01 continuous limits", ftti_ms=500)
    self.assertError(self.lint(sfm=msr_sfm(timing=t)), "no FTTI in time units")

  def test_per_frame_row(self):
    t = {"ftti_ref": "SG-01 continuous limits", "fdti_ms": 0, "frti_ms": 10, "basis": "code_derived"}
    self.assertEqual(self.errors(msr_sfm(timing=t)), [])
    t["fdti_ms"] = 20
    self.assertError(self.lint(sfm=msr_sfm(timing=t)), "per-frame WP-S-04 row needs fdti_ms 0")

  def test_good_monitoring_needs_timing_and_test(self):
    self.assertError(self.lint(sfm=msr_sfm(timing={"basis": "code_derived"})), "needs timing ftti_ref, ftti_ms, fdti_ms, frti_ms")
    self.assertError(self.lint(sfm=msr_sfm(evidence=[])), "needs an evidence entry with a `test` path")

  def test_m4_needs_measurement(self):
    res = self.lint(sfm=msr_sfm(monitoring=4, ap="H"))
    self.assertError(res, "needs measured timing")
    self.assertError(res, "evidence `ref` to the timing measurement")
    t = {"ftti_ref": "SG-01 MCU execution fault", "ftti_ms": 500, "fdti_ms": 90, "frti_ms": 100, "basis": "measured"}
    ev = [{"description": "HIL run", "ref": "WP-V-05 run 1", "test": "openpilot/selfdrive/controls/tests/test_latcontrol.py"}]
    self.assertEqual(self.errors(msr_sfm(monitoring=4, ap="H", timing=t, evidence=ev)), [])

  def test_simulation_is_not_a_measurement(self):
    # msr-plan 4.2: a plant-model run may be cited as evidence, but it never earns M <= 4 on its own
    t = {"ftti_ref": "SG-01 MCU execution fault", "ftti_ms": 500, "fdti_ms": 90, "frti_ms": 100, "basis": "measured"}
    sim = {"description": "plant model F-05", "ref": "assurance/sim/results/plant-results.md F-05",
           "test": "openpilot/selfdrive/controls/tests/test_latcontrol.py"}
    self.assertError(self.lint(sfm=msr_sfm(monitoring=4, ap="H", timing=t, evidence=[sim])), "cites only simulation results")
    hil = {"description": "HIL run", "ref": "WP-V-05 run 1"}
    self.assertEqual(self.errors(msr_sfm(monitoring=4, ap="H", timing=t, evidence=[sim, hil])), [])
    # as a cross-check of code-derived timing it is accepted and changes nothing
    m6 = msr_sfm()
    m6["failure_modes"][0]["causes"][0]["msr"]["evidence"].append({"description": "plant model F-05", "ref": sim["ref"]})
    self.assertEqual(self.errors(m6), [])

  def test_severity_after_bounded(self):
    doc = msr_sfm()
    doc["failure_modes"][0]["causes"][0]["msr"]["severity_after"] = 10
    self.assertEqual(self.errors(doc), [])
    doc["failure_modes"][0]["effects"][0].update(hazard=None, severity=9)
    del doc["failure_modes"][0]["effects"][0]["hazard"]
    doc["failure_modes"][0]["severity"] = 9
    self.assertError(self.lint(sfm=doc), "exceeds the failure mode severity 9")

  def test_mechanism_must_exist_and_be_cited(self):
    self.assertError(self.lint(sfm=msr_sfm(mechanisms=[2])), "not in the failure mode's safety_mechanisms")
    doc = msr_sfm()
    del doc["failure_modes"][0]["safety_mechanisms"][0]["ref"]
    self.assertError(self.lint(sfm=doc), "has no ref or test")

  def test_not_in_sw_fmea(self):
    doc = copy.deepcopy(SWF)
    doc["analysis"]["rating_tables"] = "RT-2"
    doc["failure_modes"][0]["safety_mechanisms"] = [{"description": "x", "ref": "y"}]
    doc["failure_modes"][0]["causes"][0]["msr"] = msr_sfm()["failure_modes"][0]["causes"][0]["msr"]
    self.assertError(self.lint(swf=doc), "msr rows belong in the System FMEA or DFMEA")

  def test_msr_needs_current_rating_tables(self):
    doc = msr_sfm()
    doc["analysis"]["rating_tables"] = "RT-1"
    self.assertError(self.lint(sfm=doc), "re-rate")
    self.assertEqual(self.errors(copy.deepcopy(SFM)), [])  # RT-1 without MSR rows is still current for S/O/D
    doc = copy.deepcopy(SFM)
    doc["analysis"]["rating_tables"] = "RT-2"
    self.assertEqual(self.errors(doc), [])  # so is any later version without MSR rows

  def test_complete_requires_every_in_scope_cause(self):
    doc = copy.deepcopy(SFM)
    doc["analysis"].update(rating_tables="RT-3", msr="complete")
    doc["failure_modes"][0]["safety_mechanisms"] = [{"description": "x", "ref": "y"}]
    self.assertError(self.lint(sfm=doc), "needs an msr row or msr_exempt")
    doc["failure_modes"][0]["causes"][0]["msr_exempt"] = "Mechanism acts on a different cause"
    res = self.lint(sfm=doc)
    self.assertEqual(res.errors, [])
    self.assertIn("1 exempt", res.report[1])

  def test_msr_and_exempt_are_exclusive(self):
    doc = msr_sfm()
    doc["failure_modes"][0]["causes"][0]["msr_exempt"] = "x"
    self.assertError(self.lint(sfm=doc), "schema")

  def test_dfmea_good_monitoring_checks_fmeda(self):
    dfm = yaml.safe_load(yaml.safe_dump(msr_sfm()).replace("SFM-", "DFM-").replace("excessive", "stuck"))
    dfm["analysis"].update(id="DFM", type="dfmea")
    msr = dfm["failure_modes"][0]["causes"][0]["msr"]
    msr.update(monitoring=4, timing={**msr["timing"], "basis": "measured"},
               evidence=[{"description": "HIL", "ref": "WP-V-05 run 1", "test": "openpilot/selfdrive/controls/tests/test_latcontrol.py"}])
    res = self.lint(dfm=dfm)
    self.assertEqual(res.errors, [])
    self.assertTrue(any("no msr.fmeda link" in w for w in res.warnings))
    msr["fmeda"] = "fmeda-x/FMD-001"  # dc_spf 0.99
    res = self.lint(dfm=dfm, **{"fmeda-x": FMEDA})
    self.assertEqual(res.errors, [])
    self.assertFalse(any("FMEDA failure mode with DC" in w for w in res.warnings))
    msr["fmeda"] = "fmeda-x/FMD-404"
    self.assertError(self.lint(dfm=dfm, **{"fmeda-x": FMEDA}), "msr fmeda fmeda-x/FMD-404 not found")
