#!/usr/bin/env python3
"""Tests for hatara_model.py and hatara_figures.py: IDs checked, gaps derived from WP-C-09 §3, outputs current."""

import copy
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hatara_figures as hf
import hatara_model as hm


class TestModel(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.m = hm.Model()
    cls.ids = hm.known_ids()

  def model(self, ix):
    return hm.Model(self.m.tara, self.m.goals, ix, self.ids)

  def test_every_hazard_and_threat_is_read(self):
    self.assertEqual(sorted(self.m.hz), [f"H-{n:02d}" for n in range(1, 10)])
    self.assertEqual(len(self.m.tara.ts), 14)

  def test_unknown_id_fails(self):
    ix = copy.deepcopy(hm.INTERACTIONS)
    ix[0]["ties"].append("TS-99")
    with self.assertRaisesRegex(hm.ParseError, "TS-99"):
      self.model(ix)

  def test_unmarked_gap_fails_and_marked_gap_is_derived(self):
    ix = copy.deepcopy(hm.INTERACTIONS)
    i = next(k for k, x in enumerate(ix) if x.get("gap"))
    del ix[i]["gap"]
    ix[i]["status"] = "x"
    with self.assertRaisesRegex(hm.ParseError, "mark it as a gap"):
      self.model(ix)
    self.assertEqual(self.m.gaps(hm.INTERACTIONS[i]), [("H-07", "TS-04"), ("H-09", "TS-04")])
    self.assertTrue(self.m.status(hm.INTERACTIONS[i])[0][0].startswith("Open"))

  def test_gap_closes_without_an_edit_when_the_tara_links_it(self):
    m = hm.Model(self.m.tara, self.m.goals, hm.INTERACTIONS, self.ids)
    m.links = m.links | {("H-07", "TS-04"), ("H-09", "TS-04")}
    ix = next(x for x in hm.INTERACTIONS if x.get("gap"))
    self.assertEqual(m.status(ix), [("Closed: WP-C-09 §3 links them now", "done")])

  def test_status_comes_from_wp_c10(self):
    ix = next(x for x in hm.INTERACTIONS if x["id"] == "IX-04")
    self.assertEqual(self.m.status(ix), [("CSR-C-01 implemented, not verified", "unverified")])

  def test_row_without_requirement_or_status_fails(self):
    ix = copy.deepcopy(hm.INTERACTIONS)
    del ix[6]["status"]
    with self.assertRaisesRegex(hm.ParseError, "needs its own status"):
      self.model(ix)

  def test_bad_type_or_duplicate_id_fails(self):
    ix = copy.deepcopy(hm.INTERACTIONS)
    ix[1]["kind"] = "independence"
    with self.assertRaisesRegex(hm.ParseError, "type must be"):
      self.model(ix)
    ix = copy.deepcopy(hm.INTERACTIONS)
    ix[1]["id"] = ix[0]["id"]
    with self.assertRaisesRegex(hm.ParseError, "unique"):
      self.model(ix)

  def test_table_current(self):
    self.assertEqual(hm.TABLE.read_text(encoding="utf-8"), self.m.table())


class TestFigures(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.m = hm.Model()
    cls.out = hf.build(cls.m)

  def test_committed_figures_current(self):
    for name, svg in self.out.items():
      self.assertEqual((hf.OUT / name).read_text(encoding="utf-8"), svg, name)

  def test_one_card_per_interaction(self):
    svg = self.out["fig-hatara-2-interactions.svg"]
    self.assertEqual(re.findall(r"<title>(IX-\d+): ", svg), [ix["id"] for ix in hm.INTERACTIONS])

  def test_gap_cells_drawn(self):
    desc = re.search(r"<desc[^>]*>(.*?)</desc>", self.out["fig-hatara-1-matrix.svg"], re.S).group(1)
    self.assertIn("H-07/TS-04 (IX-11)", desc)
    self.assertIn("Hazards with no damage scenario: H-09.", desc)

  def test_overlong_text_fails(self):
    ix = copy.deepcopy(hm.INTERACTIONS)
    ix[0]["safety"] = "x " * 200
    m = hm.Model(self.m.tara, self.m.goals, ix, hm.known_ids())
    with self.assertRaisesRegex(hm.ParseError, "three lines"):
      hf.build(m)

  def test_too_many_ties_fail(self):
    ix = copy.deepcopy(hm.INTERACTIONS)
    ix[0]["ties"] = ix[0]["ties"] * 8
    m = hm.Model(self.m.tara, self.m.goals, ix, hm.known_ids())
    with self.assertRaisesRegex(hm.ParseError, "ties run over two lines"):
      hf.build(m)

  def test_loops_and_deterministic(self):
    for svg in self.out.values():
      self.assertEqual(svg.count('repeatCount="indefinite"'), svg.count("<animate"))
    self.assertEqual(self.out, hf.build(self.m))

  def test_readme_embeds_both_figures(self):
    readme = (hf.HERE / "README.md").read_text(encoding="utf-8")
    for name in self.out:
      self.assertIn(f"figures/{name}", readme)


if __name__ == "__main__":
  unittest.main()
