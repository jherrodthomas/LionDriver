#!/usr/bin/env python3
"""Tests for fmeda_views.py: rows add up to fmea_lint's metrics, per-goal classes, SVGs current and valid, page current."""
import copy
import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fmea_lint  # noqa: E402
import fmeda_views as fv  # noqa: E402

NS = "{http://www.w3.org/2000/svg}"


class TestFmedaViews(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.out, cls.errs = fv.build()
    cls.docs = {n: fv.load(n) for n in fv.SOURCES}

  def test_rows_add_up_to_fmea_lint(self):
    self.assertEqual(self.errs, [])

  def test_committed_svgs_current_and_valid(self):
    for p, t in self.out.items():
      self.assertTrue(p.is_file(), p)
      self.assertEqual(p.read_text(encoding="utf-8"), t, f"{p.name} is stale; run fmeda_views.py")
      root = ET.fromstring(t)
      self.assertEqual(root.get("role"), "img")
      self.assertEqual(root.get("width"), str(fv.W))
      self.assertTrue(root.find(f"{NS}desc").text)
      self.assertIn("prefers-color-scheme: dark", t)

  def test_per_goal_classification(self):
    # FMD-001 and FMD-009 are single-point for SG-05 only (fmeda-sg001 per_goal entries)
    doc = self.docs["fmeda-sg001"]
    by = {g: {r["id"]: r for r in fv.split(doc, g)} for g in ("SG-01", "SG-05")}
    for fid in ("FMD-001", "FMD-009"):
      self.assertEqual(by["SG-01"][fid]["cls"], "MPF")
      self.assertEqual(by["SG-05"][fid]["cls"], "SPF")
      self.assertTrue(by["SG-05"][fid]["other_goal"])

  def test_goal_groups_share_metrics(self):
    doc = self.docs["fmeda-sg001"]
    gs = fv.groups(doc)
    self.assertEqual(len(gs), 2)
    self.assertIn("SG-05", [g for g, _a, _al in gs[1]["goals"]])
    for g in gs:
      self.assertIn(g["goal"], self.out[fv.FIGS / "fmeda-sg001-cards.svg"])

  def test_drift_is_caught(self):
    # a component rate the views would sum differently from fmea_lint is reported
    doc = copy.deepcopy(self.docs["fmeda-sg001"])
    doc["components"][0]["failure_modes"][0]["distribution"] += 0.1
    real = fv.fmea_lint.fmeda_metrics
    try:
      fv.fmea_lint.fmeda_metrics = lambda d, g=None: real(self.docs["fmeda-sg001"], g)
      self.assertTrue(fv.problems(doc, "SG-01"))
    finally:
      fv.fmea_lint.fmeda_metrics = real

  def test_page_data_and_fingerprint(self):
    page = fv.build_page()
    self.assertNotIn("__DATA__", page)
    data = json.loads(page.split('<script id="data" type="application/json">', 1)[1].split("</script>", 1)[0])
    self.assertEqual(sorted(data["files"]), sorted(fv.SOURCES))
    self.assertEqual(data["targets"]["C"], list(fmea_lint.FMEDA_TARGETS["C"]))
    stored = fv.FINGERPRINT.read_text(encoding="utf-8").split()[0]
    self.assertEqual(stored, fv.fingerprint(page), "page changed: rebuild with --html and republish to WORKSHEET_URL")

  def test_embedded_in_review_pages(self):
    for n in fv.SOURCES:
      md = (fv.FMEA / "exports/review" / f"{n}.md").read_text(encoding="utf-8")
      self.assertIn(f"](fmeda-views/{n}-cards.svg)", md)
      self.assertIn(f"](fmeda-views/{n}-sheet.svg)", md)
      self.assertIn(fv.WORKSHEET_URL, md)


if __name__ == "__main__":
  unittest.main()
