#!/usr/bin/env python3
"""Tests for fig_h07_onchip_dfa.py and for the evidence references of the STM32H725 dossier."""
import copy
import os
import re
import unittest
from pathlib import Path

import fig_h07_onchip_dfa as F

REPO = Path(__file__).resolve().parents[5]


class OnchipDfa(unittest.TestCase):
  def setUp(self):
    self.rec, self.fids = F.load()

  def test_committed_output_is_current(self):
    self.assertEqual(F.OUT.read_text(encoding="utf-8"), F.build())

  def test_every_cause_and_check_drawn_once(self):
    out = F.build()
    for c in self.rec["causes"] + self.rec["checks"]:
      self.assertEqual(len(re.findall(rf">{re.escape(c['label'])}<", out)), 1, c["label"])

  def test_unknown_rating_missing_cell_or_bad_basis_fails(self):
    bad = copy.deepcopy(self.rec)
    bad["causes"][0]["cells"]["IWDG"]["rating"] = "maybe"
    with self.assertRaises(F.FigureError):
      F.validate(bad, self.fids)
    bad = copy.deepcopy(self.rec)
    del bad["causes"][1]["cells"]["CSS"]
    with self.assertRaises(F.FigureError):
      F.validate(bad, self.fids)
    bad = copy.deepcopy(self.rec)
    bad["causes"][0]["cells"]["IWDG"]["basis"] = "MF-99"
    with self.assertRaises(F.FigureError):
      F.validate(bad, self.fids)

  def test_readme_states_the_cell_counts(self):
    counts = {k: 0 for k in F.RATING}
    for c in self.rec["causes"]:
      for cell in c["cells"].values():
        counts[cell["rating"]] += 1
    readme = (F.DOSSIER / "README.md").read_text(encoding="utf-8")
    self.assertIn(f"{counts['common']} common-cause cells", readme)

  @unittest.skipUnless((REPO / "panda" / "board").is_dir() or os.environ.get("REQUIRE_PANDA"), "panda submodule not checked out")
  def test_every_evidence_reference_exists_in_the_pinned_firmware(self):
    import yaml
    feats = yaml.safe_load((F.DOSSIER / "features.yaml").read_text(encoding="utf-8"))
    for f in feats["features"]:
      for ref in f["evidence"]:
        path, _, lines = ref.partition(":")
        p = REPO / "panda" / path
        self.assertTrue(p.exists(), f"{f['id']}: {path} not in panda")
        last = int(lines.split("-")[-1])
        self.assertLessEqual(last, len(p.read_text(encoding="utf-8", errors="replace").splitlines()), f"{f['id']}: {ref} past the end")


if __name__ == "__main__":
  unittest.main()
