#!/usr/bin/env python3
"""Tests for fmea_review_md.py: the committed pages are current, and the diagram checks catch bad data."""
import copy
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fmea_lint
import fmea_review_md as m


def load(name):
  doc = fmea_lint.load_yaml((m.ANALYSES / f"{name}.yaml").read_text())
  dg = yaml.safe_load((m.DIAGRAMS / f"{name}.yaml").read_text())
  return doc, dg


class Committed(unittest.TestCase):
  def test_pages_current(self):
    files, errs = m.build_all()
    self.assertEqual(errs, [])
    stale = [str(p) for p, t in files.items() if not p.is_file() or p.read_text(encoding="utf-8") != t]
    self.assertEqual(stale, [], "run tools/safety/fmea_review_md.py")

  def test_every_analysis_has_diagrams(self):
    for name in m.SOURCES:
      doc, dg = load(name)
      self.assertTrue(dg.get("p_diagram"), name)
      self.assertTrue(dg.get("block_diagram") or dg.get("process_flow"), name)
      self.assertEqual(m.check_diagram(name, doc, dg), [], name)



class TwoStyles(unittest.TestCase):
  def test_pages_embed_the_original_figures_and_each_has_a_card_version(self):
    files, _ = m.build_all()
    svgs = [p for p in files if p.suffix == ".svg" and not p.stem.endswith("-cards")]
    self.assertTrue(svgs)
    for p in svgs:
      self.assertIn(p.with_name(p.stem + "-cards.svg"), files, p.name)
      self.assertIn("#1f2328", files[p])   # the original (GitHub Primer) ink
    pages = "".join(t for p, t in files.items() if p.suffix == ".md")
    self.assertNotIn("-cards.svg", pages)

class Checks(unittest.TestCase):
  def test_unknown_failure_mode_in_error_state(self):
    doc, dg = load("dfmea")
    dg = copy.deepcopy(dg)
    dg["p_diagram"]["error_states"][0]["failure_modes"].append("DFM-999")
    self.assertTrue(any("DFM-999" in e for e in m.check_diagram("dfmea", doc, dg)))

  def test_interface_to_unknown_block_and_overlap(self):
    doc, dg = load("dfmea")
    dg = copy.deepcopy(dg)
    dg["block_diagram"]["interfaces"][0]["to"] = "B99"
    b0, b1 = dg["block_diagram"]["blocks"][:2]
    b1["column"], b1["row"] = b0["column"], b0["row"]
    errs = m.check_diagram("dfmea", doc, dg)
    self.assertTrue(any("unknown block" in e for e in errs))
    self.assertTrue(any("overlaps" in e for e in errs))

  def test_missing_noise_category(self):
    doc, dg = load("sw-fmea")
    dg = copy.deepcopy(dg)
    dg["p_diagram"]["noise_factors"]["customer_usage"] = []
    self.assertTrue(any("customer_usage" in e for e in m.check_diagram("sw-fmea", doc, dg)))

  def test_flow_link_to_unknown_step(self):
    doc, dg = load("pfmea")
    dg = copy.deepcopy(dg)
    dg["process_flow"]["steps"][0]["next"] = ["P99"]
    self.assertTrue(any("P99" in e for e in m.check_diagram("pfmea", doc, dg)))


class Rendering(unittest.TestCase):
  def test_svgs_are_well_formed_and_themed(self):
    import xml.etree.ElementTree as ET
    files, _ = m.build_all()
    svgs = [t for p, t in files.items() if p.suffix == ".svg"]
    self.assertGreaterEqual(len(svgs), 12)
    for t in svgs:
      ET.fromstring(t)
      self.assertIn("prefers-color-scheme: dark", t)

  def test_msr_section(self):
    doc, dg = load("dfmea")
    page = m.page("dfmea", doc, dg, m.counts(doc))
    self.assertIn("## 7. Monitoring and system response", page)
    self.assertIn("figures/dfmea-msr.svg", page)
    self.assertIn("`DFM-011.C1`", page.split("## 7.")[1])
    cov = m.msr_coverage("dfmea", doc)
    self.assertEqual(cov["rated"] + cov["exempt"], cov["in_scope"])  # msr: complete
    self.assertNotIn("## 7.", m.page("pfmea", *load("pfmea"), m.counts(load("pfmea")[0])))

  def test_msr_timing_text(self):
    self.assertEqual(m.msr_timing({"ftti_ms": 500, "fdti_ms": 90, "frti_ms": 100, "basis": "measured"}),
                     "90 + 100 ms vs FTTI 500 ms ✅ (measured)")
    self.assertIn("❌", m.msr_timing({"ftti_ms": 500, "fdti_ms": 2000, "frti_ms": 10, "basis": "code_derived"}))
    self.assertEqual(m.msr_timing({"ftti_ref": "x", "fdti_ms": 0, "frti_ms": 10, "basis": "code_derived"}),
                     "per frame; reaction 10 ms (code-derived)")
    self.assertEqual(m.msr_timing({"basis": "unknown"}), "unknown")

  def test_wrap_truncates(self):
    self.assertEqual(len(m.wrap("word " * 50, 20, 3)), 3)
    self.assertTrue(m.wrap("word " * 50, 20, 3)[-1].endswith("…"))


if __name__ == "__main__":
  unittest.main()
