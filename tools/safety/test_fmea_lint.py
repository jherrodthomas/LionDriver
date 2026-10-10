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

  def test_unquoted_date_is_accepted(self):
    text = yaml.safe_dump(SWF, sort_keys=False).replace("analysis:\n", "analysis:\n  updated: 2026-10-09\n", 1)
    (self.tmp / "assurance/08-analyses/fmea/analyses/swf.yaml").write_text(text)
    self.assertEqual(fmea_lint.lint(self.tmp).errors, [])

  def test_rating_tables_version(self):
    doc = copy.deepcopy(SWF)
    doc["analysis"]["rating_tables"] = "RT-0"
    self.assertError(self.lint(swf=doc), "re-rate")


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


if __name__ == "__main__":
  unittest.main()
