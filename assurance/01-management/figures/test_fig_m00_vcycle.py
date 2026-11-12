#!/usr/bin/env python3
"""Tests for fig_m00_vcycle.py: current output, every register row placed once, loud failures, agreed counts."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_m00_vcycle as v  # noqa: E402
from figkit import FigureError  # noqa: E402


def patched(text: str):
  """Make read_register see `text` as the register."""
  real = Path.read_text

  def fake(self, *a, **k):
    return text if self == v.REGISTER else real(self, *a, **k)
  return mock.patch.object(Path, "read_text", fake)


class VCycle(unittest.TestCase):
  REG = v.REGISTER.read_text(encoding="utf-8")

  def test_committed_output_is_current(self):
    self.assertEqual(v.main(["--check"]), 0)

  def test_every_register_row_placed_exactly_once(self):
    m = v.build_model()
    placed = [w for side in m["boxes"].values() for b in side for w in b["ids"]] + \
             [w for b in m["band"] for w in b["ids"]]
    self.assertEqual(sorted(placed), sorted(m["wps"]))
    self.assertEqual(len(placed), len(set(placed)))
    ids = set(re.findall(r"^\| \[(WP-[A-Z]-\d\d)\]", self.REG, re.M))
    self.assertEqual(ids, set(m["wps"]))

  def test_unknown_status_fails(self):
    row = next(ln for ln in self.REG.splitlines() if ln.startswith("| [WP-C-03]"))
    bad = self.REG.replace(row, row.rsplit("|", 2)[0] + "| Q |")
    with patched(bad), self.assertRaises(FigureError):
      v.read_register()

  def test_new_register_row_must_be_placed(self):
    row = next(ln for ln in self.REG.splitlines() if ln.startswith("| [WP-C-12]"))
    extra = row.replace("WP-C-12", "WP-C-13")
    with patched(self.REG.replace(row, row + "\n" + extra)), self.assertRaises(FigureError) as e:
      v.build_model()
    self.assertIn("WP-C-13", str(e.exception))

  def test_counts_agree_with_the_register(self):
    m = v.build_model()
    rows = [ln for ln in self.REG.splitlines() if re.match(r"^\| \[WP-", ln)]
    drafts = sum(1 for r in rows if r.rstrip().endswith("| D |"))
    self.assertEqual(sum(1 for w in m["wps"].values() if w["status"] == "D"), drafts)
    main = v.README_MAIN.read_text(encoding="utf-8")
    self.assertIn(f"{len(rows)} work products", main)

  def test_readme_links_open_existing_folders(self):
    s = v.README_A.read_text(encoding="utf-8")
    block = s[s.index(v.BEGIN):s.index(v.END)]
    links = re.findall(r'<a href="([^"]+)"', block)
    self.assertEqual(len(links), 2 * len(v.BOXES["define"]) + 1 + len(v.BAND))
    for ln in links:
      self.assertTrue((v.A / ln).exists(), ln)

  def test_current_phase_is_first_gate_not_passed(self):
    m = v.build_model()
    first = next(p for p in m["phases"] if not p["passed"])
    self.assertIs(m["now"], first)

  def test_every_box_has_an_exploded_page_listing_each_work_product_once(self):
    import vcycle_explode as x
    m = v.build_model()
    boxes = x.all_boxes(m)
    self.assertEqual(len(boxes), 2 * len(v.BOXES["define"]) + 1 + len(v.BAND))
    seen = []
    for _, _, b in boxes:
      page = (x.PAGES / f"{x.slug(b['title'])}.md").read_text(encoding="utf-8")
      rows = re.findall(r"^\| \[(WP-[A-Z]-\d\d) ", page, re.M)
      self.assertEqual(sorted(rows), sorted(b["ids"]), b["title"])
      seen += rows
    self.assertEqual(sorted(seen), sorted(m["wps"]))

  def test_work_product_without_producing_activity_fails(self):
    import vcycle_explode as x
    m = v.build_model()
    producer, lanes, reviews, ctx = x.process_facts()
    del producer["WP-C-03"]
    where = {w: b["title"] for _, _, b in x.all_boxes(m) for w in b["ids"]}
    with self.assertRaises(FigureError):
      x.explode(m, m["boxes"]["define"][0], where, (producer, lanes, reviews, ctx))

  def test_measure_planned_at_two_gates_is_listed_once(self):
    import vcycle_explode as x
    self.assertEqual(x.dedupe([("CR-03", "a", False), ("CR-03", "b", True)]), [("CR-03", "a", True)])


if __name__ == "__main__":
  unittest.main()
