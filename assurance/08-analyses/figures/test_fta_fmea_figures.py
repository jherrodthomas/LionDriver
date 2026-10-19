#!/usr/bin/env python3
"""Tests for fta_fmea_figures.py: counts as fmea_lint.py computes them, one row per event, outputs current."""

import copy
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fta_fmea_figures as ff  # noqa: E402

MAPPING_DOC = ff.ROOT / "assurance" / "08-analyses" / "fta-fmea-mapping.md"


class TestFigures(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.data = ff.Data()
    cls.out = ff.build(cls.data)

  def test_committed_figures_current_and_embedded(self):
    doc = MAPPING_DOC.read_text(encoding="utf-8")
    for name, svg in self.out.items():
      self.assertEqual((ff.OUT / name).read_text(encoding="utf-8"), svg, name)
      self.assertIn(f"figures/{name}", doc)
    self.assertEqual({p.name for p in ff.OUT.glob("fig-map-*.svg")}, set(self.out))

  def test_counts_match_fmea_lint(self):
    try:
      import fmea_lint  # needs PyYAML and jsonschema, installed in CI
    except ImportError:
      self.skipTest("fmea_lint needs PyYAML")
    res = fmea_lint.lint()
    lint = [line for line in res.report if line.startswith("FTA-FMEA map ")]
    self.assertEqual([ff.report_line(g, self.data.goals[g]) for g in self.data.scope], lint)
    warned = {re.search(r"(BE-\d+\.\d+|UE-\d+\.\d+)", w).group(1) for w in map(str, res.warnings)
              if "every FMEA cause claims a detection rating <= 4" in w}
    svg = "".join(v for k, v in self.out.items() if k.startswith("fig-map-3-"))
    flagged = set(re.findall(r"(BE-\d+\.\d+): [^;]*every cause D ≤ 4", svg))
    self.assertEqual(flagged, warned)

  def test_one_row_per_event_on_the_goal_sheets(self):
    for g in self.data.scope:
      sheets = "".join(v for k, v in self.out.items() if k.startswith(f"fig-map-3-{g.lower()}-"))
      shown = re.findall(r">[●◆] ((?:BE|UE)-\d+\.\d+)", sheets)
      self.assertEqual(len(shown), len(set(shown)), g)  # once each
      self.assertEqual(len(shown), self.data.goals[g]["events"], g)

  def test_single_points_come_from_the_tree_logic(self):
    s = self.data.goals["SG-04"]
    self.assertEqual(s["spf"], ["BE-4.01", "BE-4.03", "BE-4.11", "BE-4.14", "BE-4.24"])
    first = self.out["fig-map-3-sg-04-1.svg"]
    desc = re.search(r"<desc[^>]*>(.*?)</desc>", first, re.S).group(1)
    for ev in s["spf"]:
      self.assertIn(f">{ev}</text>", first)
      self.assertIn(f"{ev}: ", desc.split("Single points: ")[1])

  def test_rows_group_under_the_gate_they_feed(self):
    rows = {r["node"].ident: r["group"] for r in self.data.goals["SG-04"]["rows"]}
    self.assertEqual(rows["BE-4.01"][:2], ("G4.1.1", "OR gate"))
    self.assertEqual(rows["BE-4.01"][2], ("TE-04", "G4.1"))
    self.assertEqual(rows["BE-4.16"][:2], ("G-LENV", "from SG-03"))  # borrowed through the transfer

  def test_unknown_fmea_mode_fails(self):
    doc = ff.fmd.load_yaml(ff.MAP.read_text(encoding="utf-8"))
    doc = copy.deepcopy(doc)
    doc["events"][0]["fmea"] = ["SWF-999"]
    with self.assertRaisesRegex(ff.FigureError, "SWF-999"):
      ff.Data(map_doc=doc)

  def test_chain_must_exist(self):
    old = ff.CHAIN
    try:
      ff.CHAIN = ("SG-04", "BE-9.99")
      with self.assertRaisesRegex(ff.FigureError, "BE-9.99"):
        ff.ladders(self.data)
      ff.CHAIN = ("SG-04", "UE-4.04")  # no FMEA row
      with self.assertRaisesRegex(ff.FigureError, "no FMEA row"):
        ff.ladders(self.data)
    finally:
      ff.CHAIN = old

  def test_backlinks(self):
    links = ff.backlinks(self.data)
    self.assertIn(("SG-04", [("BE-4.02", False), ("BE-4.06", False), ("BE-4.11", True), ("G4.1", False), ("G4.3", False)], None),
                  links["SFM-009"])
    self.assertTrue(any(kind == "tree_gap" for v in links.values() for _, _, kind in v))

  def test_loops_and_deterministic(self):
    for svg in self.out.values():
      self.assertEqual(svg.count('repeatCount="indefinite"'), svg.count("<animate"))
    self.assertEqual(self.out, ff.build(self.data))


if __name__ == "__main__":
  unittest.main()
