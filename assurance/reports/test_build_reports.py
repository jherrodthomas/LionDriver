#!/usr/bin/env python3
"""Tests of the LaTeX report generator (build_reports.py): the FSC and the harness box FMEDA. The PDF build itself runs in the CI job that has TeX."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_reports as br  # noqa: E402


class TestTex(unittest.TestCase):
  def test_escaping(self):
    self.assertEqual(br.tex("a_b & 50 % #1"), r"a\_b \& 50 \% \#1")
    self.assertEqual(br.tex("`x_y`"), r"\texttt{x\_y}")
    self.assertEqual(br.tex("**bold** ≤ 0.5 s"), r"\textbf{bold} $\le$ 0.5 s")
    self.assertEqual(br.tex("[WP-C-03](WP-C-03-hara.md)"), "WP-C-03")

  def test_unknown_character_fails(self):
    with self.assertRaises(br.ReportError):
      br.tex("snowman ☃", "test")

  def test_table_with_renamed_column_fails(self):
    body = "| A | B |\n|---|---|\n| 1 | 2 |\n"
    self.assertEqual(br.md_table(body, ["A", "B"], "t"), [{"A": "1", "B": "2"}])
    with self.assertRaises(br.ReportError):
      br.md_table(body, ["A", "C"], "t")


class TestFsc(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.files, cls.figures = br.fsc()
    cls.doc = cls.files["fsc/fsc.tex"]
    cls.md = br.FSC_MD.read_text(encoding="utf-8")

  def test_numbers_match_the_record(self):
    n = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", self.files["fsc/numbers.tex"]))
    fsr_ids = re.findall(r"^\| (FSR-\d\d\.\d\d) \|", br.section(self.md, "## 5. Functional safety requirements"), re.M)
    self.assertEqual(int(n["FsrCount"]), len(fsr_ids))
    cats = [k for k in n if k.startswith("Fsr") and k != "FsrCount"]
    self.assertEqual(sum(int(n[k]) for k in cats), len(fsr_ids))
    self.assertEqual(int(n["GoalCount"]), 8)
    self.assertEqual(n["FscVersion"], br.version_of(self.md, "t")[0])

  def test_every_fsr_once_and_every_goal_a_section(self):
    fsr_ids = re.findall(r"^\| (FSR-\d\d\.\d\d) \|", self.md, re.M)
    for f in set(fsr_ids):
      self.assertEqual(self.doc.count(f"\n{f} &"), 1, f)
    self.assertEqual(self.doc.count(r"\section{SG-"), 8)

  def test_prose_numbers_are_macros(self):
    intro = self.doc[self.doc.index(r"\chapter{Introduction}"):self.doc.index(r"\chapter{Safety goals}")]
    self.assertNotRegex(intro, r"(?<![\w.-])\d{2,}(?![\w.-])")  # no bare multi-digit number in the prose

  def test_figures_and_citations_resolve(self):
    for fig in self.figures:
      self.assertTrue(fig.exists(), fig)
      self.assertIn(fig.stem + ".pdf", self.doc)
    self.assertIn(r"\bibitem{iso26262-3}", self.doc)

  def test_unknown_citation_fails(self):
    with self.assertRaises(br.ReportError):
      br.bibliography(r"\cite{no-such-ref}")

  def test_committed_outputs_current(self):
    self.assertEqual(br.main(["--check"]), 0)


class TestHarnessBox(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.files, cls.figures = br.harness_box()
    cls.doc = cls.files["harness-box/harness-box.tex"]
    cls.n = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", cls.files["harness-box/numbers.tex"]))
    import harness_box_fmeda as hb
    cls.hb = hb
    cls.r = hb.build()

  def test_numbers_match_the_record(self):
    parts = self.r["parts"]
    self.assertEqual(int(self.n["PartCount"]), len(parts))
    self.assertEqual(int(self.n["ModeCount"]), sum(len(p["modes"]) for p in parts))
    self.assertEqual(self.n["SgSevenSpf"], self.hb.fit(self.r["cat"]["SG-07"]["SPF"]))
    self.assertEqual(self.n["SpfmNow"], f"{self.r['whatif'][0]['spfm'] * 100:.2f}")
    self.assertEqual(self.n["HbVersion"], self.r["data"]["revisions"][-1]["version"])

  def test_every_part_and_mode_once(self):
    table = self.doc[self.doc.index(r"\label{tab:parts}"):]
    table = table[:table.index(r"\end{longtable}")]
    for p in self.r["parts"]:
      self.assertEqual(len(re.findall(rf"^{p['ref']} &", table, re.M)), 1, p["ref"])
    self.assertEqual(table.count(r"\\ \midrule") - 2, int(self.n["ModeCount"]))  # two header rows

  def test_prose_numbers_are_macros(self):
    intro = self.doc[self.doc.index(r"\chapter{Introduction}"):self.doc.index(r"\chapter{The box and its blocks}")]
    self.assertNotRegex(intro, r"(?<![\w.-])\d{2,}(?![\w.-])")

  def test_figures_findings_and_citation(self):
    for fig in self.figures:
      self.assertTrue(fig.exists(), fig)
      self.assertIn(fig.stem + ".pdf", self.doc)
    for d in self.r["diffs"]:
      self.assertIn(d["row"], self.doc)
    self.assertIn(r"\bibitem{iso26262-5}", self.doc)


if __name__ == "__main__":
  unittest.main()
