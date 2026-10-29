#!/usr/bin/env python3
"""Tests for fmea_diagrams.py: the stdlib YAML loader, the figure content and that the committed figures are current.

Run: python3 tools/safety/test_fmea_diagrams.py   (or python3 -m unittest discover -s tools/safety)
Standard library only; the cross-checks against PyYAML and fmea_lint run only when those are importable.
"""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fmea_diagrams as fd  # noqa: E402

try:
  import fmea_lint  # needs PyYAML and jsonschema
except ImportError:
  fmea_lint = None

SVG_NS = "{http://www.w3.org/2000/svg}"

SAMPLE = """# comment
schema_version: 1
analysis:
  id: SWF   # trailing comment
  rev: '0.2'
  updated: 2026-10-13
  scope: >-
    first line
    second line
  flag: true
  none:
items:
- id: A-1
  vals: [1, 2.5, "x, y", 'it''s']
  ctl: &c1
    - description: plain text
        continued here
      test: a/b.py
- id: A-2
  ctl: *c1
  effect: {level: end, hazard: HZ-001, severity: 10}
  quoted: 'one
    two'
"""


class TestYamlLoader(unittest.TestCase):
  def test_sample(self):
    d = fd.load_yaml(SAMPLE)
    self.assertEqual(d["schema_version"], 1)
    self.assertEqual(d["analysis"]["id"], "SWF")
    self.assertEqual(d["analysis"]["rev"], "0.2")
    self.assertEqual(d["analysis"]["updated"], "2026-10-13")   # dates stay strings, as in fmea_lint
    self.assertEqual(d["analysis"]["scope"], "first line second line")
    self.assertIs(d["analysis"]["flag"], True)
    self.assertIsNone(d["analysis"]["none"])
    self.assertEqual(d["items"][0]["vals"], [1, 2.5, "x, y", "it's"])
    self.assertEqual(d["items"][0]["ctl"], [{"description": "plain text continued here", "test": "a/b.py"}])
    self.assertEqual(d["items"][1]["ctl"], d["items"][0]["ctl"])
    self.assertEqual(d["items"][1]["effect"], {"level": "end", "hazard": "HZ-001", "severity": 10})
    self.assertEqual(d["items"][1]["quoted"], "one two")

  def test_rejects_unsupported(self):
    for bad in ("a: 0x10\n", "a: 1:30\n", "a:\n\t- x\n", "a: 1\na: 2\n"):
      with self.assertRaises(fd.FigError, msg=bad):
        fd.load_yaml(bad)

  @unittest.skipIf(fmea_lint is None, "PyYAML/jsonschema not installed")
  def test_matches_pyyaml_on_every_analysis(self):
    for path in sorted(fd.FMEA_DIR.rglob("*.yaml")):
      text = path.read_text(encoding="utf-8")
      self.assertEqual(fd.load_yaml(text), fmea_lint.load_yaml(text), path.name)


class TestFigures(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.docs = fd.load_analyses()
    cls.out = fd.build(cls.docs)
    cls.svgs = {k: v for k, v in cls.out.items() if k.endswith(".svg")}

  def test_committed_outputs_are_current(self):
    for name, content in self.out.items():
      path = fd.OUT_DIR / name
      self.assertTrue(path.exists(), f"{name} missing; run python3 {fd.GENERATOR}")
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{name} stale; run python3 {fd.GENERATOR}")
    cards = fd.build_cards()
    for name, content in cards.items():
      self.assertEqual((fd.OUT_DIR / name).read_text(encoding="utf-8"), content, f"{name} stale; run python3 {fd.GENERATOR}")
    extra = {p.name for p in fd.OUT_DIR.glob("*.svg") if fd.OWNED_RE.match(p.name)} - set(self.out) - set(cards)
    self.assertFalse(extra, f"no longer generated: {sorted(extra)}")

  def test_original_style_is_the_record(self):
    # The original drawing is the figure of record; the card style comes in addition (fig-*-cards.svg), never instead.
    self.assertFalse(fd.CARDS)
    cards = fd.build_cards()
    for name in self.svgs:
      self.assertIn(fd.cards_name(name), cards, name)
      self.assertNotIn('id="dots"', self.svgs[name], name)
      self.assertIn('id="dots"', cards[fd.cards_name(name)], name)
    chain = self.svgs["fig-3-6-swf-failure-chains-1.svg"]
    self.assertIn('marker-end="url(#aS)"', chain)   # the original arrows between the columns
    self.assertIn(f'fill="{fd.BG}"', chain)
    self.assertIn("Card version", self.out["README.md"])

  def test_deterministic(self):
    self.assertEqual(fd.build(self.docs), self.out)

  def test_svgs_are_well_formed_and_accessible(self):
    for name, content in self.svgs.items():
      root = ET.fromstring(content)
      self.assertEqual(root.tag, SVG_NS + "svg", name)
      self.assertIsNotNone(root.find(SVG_NS + "title"), name)
      desc = root.find(SVG_NS + "desc")
      self.assertTrue(desc is not None and len(desc.text) > 40, name)
      self.assertEqual(root.get("role"), "img", name)

  def test_sheets_are_bounded(self):
    for name, content in self.svgs.items():
      if "failure-chains" in name:
        h = int(re.search(r'height="(\d+)"', content).group(1))
        self.assertLess(h, fd.MAX_SHEET_H + 600, name)

  def test_every_fmea_id_is_drawn(self):
    for key, _, _, slug in fd.FMEA_FILES:
      doc = self.docs[key]
      text = "\n".join(v for k, v in self.svgs.items() if f"-{slug}-" in k)
      ids = [x["id"] for x in doc["structure"]] + [x["id"] for x in doc["functions"]]
      for fm in doc["failure_modes"]:
        ids.append(fm["id"])
        ids += [ef["hazard"] for ef in fm["effects"] if ef.get("hazard")]
        for c in fm["causes"]:
          ids.append(c["id"])
          ids += c.get("actions", [])
          if c.get("linked_failure_mode"):
            ids.append(c["linked_failure_mode"])
      for fn in doc["functions"]:
        ids += fn.get("requirements", [])
      for i in ids:
        self.assertRegex(text, rf"(?<![\w.-]){re.escape(i)}(?![\w-]|\.C)", f"{key}: {i} not drawn")

  def test_failure_mode_sheets_cover_each_fm_once(self):
    for key, _, _, slug in fd.FMEA_FILES:
      sheets = [v for k, v in sorted(self.svgs.items()) if f"-{slug}-failure-chains-" in k]
      for fm in self.docs[key]["failure_modes"]:
        hits = sum(1 for s in sheets if re.search(rf">{re.escape(fm['id'])}</text>", s))
        self.assertEqual(hits, 1, f"{fm['id']} drawn on {hits} sheets")

  def test_fmeda_ids_and_status(self):
    for key in ("fmeda-sg001", "fmeda-sg009"):
      doc = self.docs[key]
      svg = next(v for k, v in self.svgs.items() if key in k)
      ids = [s["id"] for s in doc["safety_mechanisms"]] + [c["id"] for c in doc["components"]]
      ids += [fm["id"] for c in doc["components"] for fm in c["failure_modes"]]
      for i in ids:
        self.assertIn(i, svg, f"{key}: {i} not drawn")
      self.assertIn("not verified", svg)
      self.assertIn("ESTIMATE", svg)
      # a target met on generic estimates is never drawn as green (verified)
      metric_part = svg.split("FAILURE-RATE SPLIT")[0]
      self.assertNotIn(fd.GREEN, metric_part)

  @unittest.skipIf(fmea_lint is None, "PyYAML/jsonschema not installed")
  def test_fmeda_metrics_match_lint(self):
    for key in ("fmeda-sg001", "fmeda-sg009"):
      ours, lint = fd.fmeda_metrics(self.docs[key]), fmea_lint.fmeda_metrics(self.docs[key])
      for k, v in lint.items():
        self.assertAlmostEqual(ours[k], v, places=9, msg=f"{key} {k}")

  def test_ap_table_matches_lint(self):
    if fmea_lint is None:
      self.skipTest("fmea_lint not importable")
    for s in range(1, 11):
      for o in range(1, 11):
        for d in range(1, 11):
          self.assertEqual(fd.compute_ap(s, o, d), fmea_lint.compute_ap(s, o, d))

  def test_dfa_ids_drawn(self):
    doc = self.docs["dfa"]
    svg = next(v for k, v in self.svgs.items() if "dfa" in k)
    ids = [c["id"] for c in doc["categories"]] + [d["id"] for d in doc["dfis"]] + [m["id"] for m in doc["measures"]]
    ids += [o["id"] for o in doc["open_items"]] + [d["fsr"] for d in doc["decompositions"]]
    ids += [c["fsr"] for d in doc["decompositions"] for c in d["channels"]]
    for i in ids:
      self.assertIn(i, svg, f"dfa: {i} not drawn")

  def test_predicted_ratings_drawn_as_not_achieved(self):
    svg = self.svgs["fig-3-7-swf-action-effect.svg"]
    for a in self.docs["sw-fmea"]["actions"]:
      if a.get("revised"):
        self.assertIn(a["id"], svg)
    self.assertIn("not achieved", svg)

  def test_msr_overview_counts_and_ids(self):
    # Figure 4-2: per FMEA with msr rows, the counts in the description match the YAML, every action named in an MSR
    # row is drawn, and every cause at M <= 6 is listed by id
    svg = self.svgs["fig-4-2-msr-overview.svg"]
    desc = ET.fromstring(svg).find(f"{SVG_NS}desc").text
    for key in ("system-fmea", "dfmea"):
      doc = self.docs[key]
      rated = [c for fm in doc["failure_modes"] for c in fm["causes"] if c.get("msr")]
      exempt = [c for fm in doc["failure_modes"] for c in fm["causes"] if c.get("msr_exempt")]
      self.assertIn(f"{doc['analysis']['id']} rev {doc['analysis']['revision']} at {doc['analysis']['baseline']}: "
                    f"{len(rated)} causes rated, {len(exempt)} exempt", desc)
      bands = [sum(1 for c in rated if lo <= c["msr"]["monitoring"] <= hi) for lo, hi, _, _ in fd.M_BANDS_MSR]
      self.assertIn(f"monitoring M 1-4 {bands[0]}, M 5-6 {bands[1]}, M 7-8 {bands[2]}, M 9-10 {bands[3]}", desc)
      for c in rated:
        for a in c["msr"].get("actions") or []:
          self.assertIn(a, svg)
        if c["msr"]["monitoring"] <= 6:
          self.assertIn(c["id"], svg)
    self.assertIn("handbook", svg)

  def test_msr_ap_table_matches_lint(self):
    if fmea_lint is None:
      self.skipTest("fmea_lint not importable")
    # the grid background uses the S 10 handbook table; the linter's MSR table must be the same table
    for f in range(1, 11):
      for m in range(1, 11):
        self.assertEqual(fd.compute_ap_msr_s10(f, m), fmea_lint.compute_ap_msr(10, 10, f, m))

  def test_never_owns_hand_drawn_figures(self):
    for name in self.out:
      self.assertTrue(name == "README.md" or fd.OWNED_RE.match(name), name)
    for p in fd.OUT_DIR.parent.glob("*.svg"):   # hand-drawn figures one level up are not ours
      self.assertNotIn(p.name, self.out)
    self.assertEqual(fd.OUT_DIR.name, "generated")

  def test_readme_lists_every_figure(self):
    readme = self.out["README.md"]
    for name in self.svgs:
      self.assertIn(f"({name})", readme)


class TestStudyFigures(unittest.TestCase):
  """Figures 3-14..3-16 draw the `previous`, timed safety-mechanism and `sotif` fields of the SW FMEA."""

  @classmethod
  def setUpClass(cls):
    cls.doc = fd.load_analyses()["sw-fmea"]
    cls.f = fd.Fmea("sw-fmea", cls.doc, "3-5", "3-6", "swf")

  def test_baseline_delta_draws_each_rerated_cause_once(self):
    svg = fd.render_baseline_delta(self.f, "3-14")
    ids = [c["id"] for fm in self.doc["failure_modes"] for c in fm["causes"] if c.get("previous")]
    self.assertTrue(ids)
    for i in ids:
      self.assertEqual(len(re.findall(rf">{re.escape(i)}(?: · S\d+→\d+)?</text>", svg)), 1, i)
    out_h = sum(1 for fm in self.doc["failure_modes"] for c in fm["causes"]
                if c.get("previous", {}).get("ap") == "H" and c["ap"] != "H")
    self.assertIn(f"{out_h} left AP H", svg)

  def test_reaction_layers_rows_and_untimed_warning(self):
    svg = fd.render_reaction_layers(self.f, "3-15")
    rows = [fm for fm in self.doc["failure_modes"] if any("reaction_s" in m for m in fm.get("safety_mechanisms", []))]
    for fm in rows:
      self.assertIn(f">{fm['id']}</text>", svg)
    no_warn = [fm for fm in rows if not any(m.get("layer") in fd.WARN_LAYERS and "reaction_s" in m
                                            for m in fm["safety_mechanisms"])]
    self.assertEqual(svg.count(">none timed</text>"), len(no_warn))

  def test_time_labels(self):
    self.assertEqual(fd.fmt_s(0.05), "50 ms")
    self.assertEqual(fd.fmt_s(5.0), "5 s")

  def test_sotif_boundary_counts_every_cause_once(self):
    svg = fd.render_sotif_boundary(self.f, "3-16")
    tops = [x for x in self.doc["structure"] if not x.get("parent")]
    for x in tops:
      self.assertIn(f">{x['id'].replace('SWF-SE-', 'SE-')}</text>", svg)
    drawn = sum(int(m) for m in re.findall(r"FM · (\d+) causes", svg))
    self.assertEqual(drawn, sum(1 for fm in self.doc["failure_modes"] for c in fm["causes"] if c.get("ap")))
    for x in tops:
      if x.get("sotif", {}).get("ref"):
        self.assertIn(fd.e(x["sotif"]["ref"]), svg)


class TestDetectionEvidence(unittest.TestCase):
  """Figure 3-13 classifies cited tests from the repository; check the rules on known files."""

  @classmethod
  def setUpClass(cls):
    cls.idx = fd.TestIndex(workflows="run: openpilot/selfdrive/test/process_replay/test_processes.py",
                           ignored=["openpilot/tools/sim"], native="", panda_suites={"reference_lock"})

  def test_submodule_paths_by_rule(self):
    c = self.idx.classify
    self.assertEqual(c("opendbc_repo/opendbc/safety/tests/test_toyota.py")[0], "ci")
    self.assertEqual(c("panda/tests/reference_lock/test_reference_lock.py")[0], "ci")
    self.assertEqual(c("panda/tests/heartbeat_monitor/test_heartbeat_monitor.py")[0], "not_run")
    self.assertEqual(c("panda/tests/hitl/test_6_safety.py")[0], "hardware")
    self.assertEqual(c("msgq_repo/msgq/tests/test_fake.py")[0], "not_run")

  def test_openpilot_files_read_from_the_repository(self):
    c = self.idx.classify
    self.assertEqual(c("openpilot/selfdrive/test/process_replay/test_processes.py")[0], "ci")   # named in a workflow
    self.assertEqual(c("openpilot/selfdrive/selfdrived/tests/test_state_machine.py")[0], "ci")  # TestCase
    self.assertEqual(c("openpilot/selfdrive/pandad/tests/test_pandad_spi.py")[0], "hardware")  # COMMA_HARDWARE_TEST
    self.assertEqual(c("openpilot/selfdrive/no_such_test.py")[0], "missing")

  def test_cause_class_uses_detection_rating(self):
    ci = {"detection_controls": [{"test": "opendbc_repo/opendbc/safety/tests/test_toyota.py"}]}
    self.assertEqual(fd.cause_evidence({**ci, "detection": 3}, self.idx), "proven")
    self.assertEqual(fd.cause_evidence({**ci, "detection": 7}, self.idx), "targeted")
    self.assertEqual(fd.cause_evidence({**ci, "detection": 9}, self.idx), "generic")
    self.assertEqual(fd.cause_evidence({"detection_controls": [{"description": "x"}], "detection": 10}, self.idx), "none")

  def test_suites_and_ignores_parsed_from_ci(self):
    idx = fd.TestIndex.load()
    self.assertIn("reference_lock", idx.panda_suites)
    self.assertIn("openpilot/selfdrive/test/process_replay/test_processes.py", idx.ignored)


if __name__ == "__main__":
  unittest.main()
