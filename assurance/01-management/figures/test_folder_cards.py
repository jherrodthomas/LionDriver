#!/usr/bin/env python3
"""Tests for folder_cards.py: cards current, only on READMEs without a picture, numbers read from the records."""

import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import folder_cards as fc  # noqa: E402


class TestFolderCards(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.out = fc.build()

  def test_committed_output_current(self):
    for p, s in self.out.items():
      self.assertEqual(p.read_text(encoding="utf-8"), s, p)

  def test_card_sits_under_the_title_and_the_rest_is_untouched(self):
    for key in fc.CARDS:
      new = self.out[fc.A / key / "README.md"]
      lines = new.splitlines()
      self.assertTrue(lines[0].startswith("# "), key)
      self.assertEqual(lines[2], fc.START, key)
      stripped = re.sub(r"\n" + re.escape(fc.START) + r".*?" + re.escape(fc.END) + r"\n", "", new, flags=re.S)
      self.assertFalse(fc.IMG.search(stripped), key)  # the card is the only picture
      self.assertEqual(new.count(fc.START), 1)

  def test_refuses_a_readme_that_has_its_own_picture(self):
    real = Path.read_text

    def fake(p, *a, **k):
      s = real(p, *a, **k)
      return s + "\n![a figure](x.svg)\n" if p.name == "README.md" and p.parent.name == "test-sites" else s
    with mock.patch.object(Path, "read_text", fake):
      with self.assertRaisesRegex(fc.FigureError, "picture of its own"):
        fc.build()

  def test_test_sites_numbers_come_from_the_page(self):
    d = fc.test_sites()
    md = (fc.A / "06-validation/test-sites/README.md").read_text(encoding="utf-8")
    n_sites = len(re.findall(r"^\| TS-\d\d \|", md, re.M))
    self.assertEqual(d["tiles"][0][0], n_sites)
    self.assertIn(f"{n_sites} candidate sites", d["alt"])

  def test_unknown_status_word_fails(self):
    with mock.patch.dict(fc.IMPACT_STATUS, clear=True):
      with self.assertRaisesRegex(fc.FigureError, "has no colour"):
        fc.impact()

  def test_missing_feed_fails(self):
    bad = dict(fc.CARDS["models/fret"], ins=[("Nowhere", "x", "no/such/file.md")])
    with self.assertRaisesRegex(fc.FigureError, "does not exist"):
      fc.overview("models/fret", bad)

  def test_impact_counts_every_record_once(self):
    d = fc.impact()
    recs = [p for p in (fc.A / "07-supporting/impact").glob("*.md") if p.name != "README.md"]
    self.assertEqual(d["tiles"][0][0], len(recs))
    self.assertEqual(sum(v for _, v, _ in d["picture"][1]), len(recs))

  def test_stacks_add_up_to_their_totals(self):
    a = fc.autosar()
    n_frames = a["tiles"][1][0]
    for lab, segs, _, _ in a["picture"][1]:
      self.assertEqual(sum(v for _, v, _ in segs), n_frames, lab)
    c = fc.clauses()
    self.assertEqual(sum(v for _, segs, _, _ in c["picture"][1] for _, v, _ in segs), c["tiles"][0][0])
    s = fc.spice()
    self.assertEqual(sum(v for _, segs, _, _ in s["picture"][1] for _, v, _ in segs), s["tiles"][0][0])
    f = fc.fmdtools()
    agree, total = map(int, f["tiles"][1][0].split("/"))
    self.assertEqual(sum(segs[0][1] for _, segs, _, _ in f["picture"][1]), agree)
    self.assertEqual(sum(segs[0][1] + segs[1][1] for _, segs, _, _ in f["picture"][1]), total)

  def test_batch3_numbers_come_from_their_records(self):
    import json
    base = json.loads((fc.A / "05-software/coverage/structural-baseline.json").read_text(encoding="utf-8"))["units"]
    cov = fc.coverage()
    self.assertEqual(sum(segs[0][1] + segs[1][1] for _, segs, _, _ in cov["picture"][1]), sum(u["branches_total"] for u in base.values()))
    conf = fc.confirmation()
    self.assertEqual(sum(v for _, segs, _, _ in conf["picture"][1] for _, v, _ in segs), conf["tiles"][0][0])
    dn = fc.design_notes()
    self.assertEqual(len(dn["picture"][1]), len(list((fc.A / "05-software/design-notes").glob("DN-*.md"))))

  def test_confirmation_readme_must_agree_with_the_records(self):
    real = Path.glob

    def fake(p, pattern):
      out = list(real(p, pattern))
      if p.name == "confirmation" and pattern == "*.md":
        out.append(p / "CR-01-WP-C-01-v1.0.md")
      return iter(out)
    with mock.patch.object(Path, "glob", fake):
      with self.assertRaisesRegex(fc.FigureError, "disagrees"):
        fc.confirmation()

  def test_unknown_spice_verdict_fails(self):
    with mock.patch.object(fc, "SPICE_OK", ()), mock.patch.object(fc, "SPICE_BAD", ()):
      with self.assertRaisesRegex(fc.FigureError, "neither a known pass"):
        fc.spice()

  def test_deterministic(self):
    self.assertEqual(self.out, fc.build())


if __name__ == "__main__":
  unittest.main()
