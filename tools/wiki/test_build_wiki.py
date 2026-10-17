#!/usr/bin/env python3
"""Unit tests for build_wiki.py and a check of the real wiki/ folder."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_wiki

VALUES = {"REPO": "o/r", "BRANCH": "b", "SYNC_COMMIT": "abc1234", "SYNC_DATE": "2026-10-17"}


def make_wiki(tmp: Path, files: dict[str, str]) -> tuple[Path, Path]:
  root = tmp / "repo"
  src = root / "wiki"
  src.mkdir(parents=True)
  (root / "README.md").write_text("# repo\n", encoding="utf-8")
  (root / "assurance").mkdir()
  (root / "assurance" / "README.md").write_text("# assurance\n", encoding="utf-8")
  for name, text in files.items():
    (src / name).write_text(text, encoding="utf-8")
  return root, src


class RewriteTests(unittest.TestCase):
  def test_page_links_lose_their_extension(self):
    with tempfile.TemporaryDirectory() as d:
      root, src = make_wiki(Path(d), {"Home.md": "", "Glossary.md": "", "_Sidebar.md": ""})
      problems: list[str] = []
      out = build_wiki.rewrite("see [the glossary](Glossary.md#codes)", src / "Home.md", src, root, VALUES, problems)
      self.assertEqual(out, "see [the glossary](Glossary#codes)")
      self.assertEqual(problems, [])

  def test_repository_links_become_absolute(self):
    with tempfile.TemporaryDirectory() as d:
      root, src = make_wiki(Path(d), {"Home.md": "", "_Sidebar.md": ""})
      problems: list[str] = []
      out = build_wiki.rewrite("[a](../assurance/README.md#x) [d](../assurance)", src / "Home.md", src, root, VALUES, problems)
      self.assertEqual(out, "[a](https://github.com/o/r/blob/b/assurance/README.md#x) [d](https://github.com/o/r/tree/b/assurance)")
      self.assertEqual(problems, [])

  def test_missing_targets_are_reported(self):
    with tempfile.TemporaryDirectory() as d:
      root, src = make_wiki(Path(d), {"Home.md": "", "_Sidebar.md": ""})
      problems: list[str] = []
      build_wiki.rewrite("[p](Nope.md) [r](../nope.md) [x](nope)", src / "Home.md", src, root, VALUES, problems)
      self.assertEqual(len(problems), 3)
      self.assertIn("page link target does not exist: Nope.md", problems[0])
      self.assertIn("repository link target does not exist: nope.md", problems[1])
      self.assertIn("neither a page", problems[2])

  def test_urls_anchors_and_placeholders(self):
    with tempfile.TemporaryDirectory() as d:
      root, src = make_wiki(Path(d), {"Home.md": "", "_Sidebar.md": ""})
      problems: list[str] = []
      out = build_wiki.rewrite("[u](https://example.org/a.md) [s](#top) {{REPO}}@{{SYNC_COMMIT}} {{SYNC_DATE}} {{BRANCH}}",
                               src / "Home.md", src, root, VALUES, problems)
      self.assertEqual(out, "[u](https://example.org/a.md) [s](#top) o/r@abc1234 2026-10-17 b")
      self.assertEqual(problems, [])


class BuildTests(unittest.TestCase):
  def test_build_writes_pages_and_skips_readme(self):
    with tempfile.TemporaryDirectory() as d:
      root, src = make_wiki(Path(d), {
        "Home.md": "[g](Glossary.md) [r](../README.md)",
        "Glossary.md": "{{SYNC_COMMIT}}",
        "_Sidebar.md": "[Home](Home.md)\n[Glossary](Glossary.md)",
        "_Footer.md": "{{SYNC_DATE}}",
        "README.md": "folder notes",
      })
      out = Path(d) / "out"
      problems = build_wiki.build(src, out, root, repo="o/r", branch="b", commit="abc1234def", date="2026-10-17")
      self.assertEqual(problems, [])
      self.assertEqual(sorted(p.name for p in out.iterdir()), ["Glossary.md", "Home.md", "_Footer.md", "_Sidebar.md"])
      self.assertEqual((out / "Home.md").read_text(), "[g](Glossary) [r](https://github.com/o/r/blob/b/README.md)")
      self.assertEqual((out / "Glossary.md").read_text(), "abc1234")
      self.assertEqual((out / "_Footer.md").read_text(), "2026-10-17")

  def test_unlinked_page_and_missing_home_are_problems(self):
    with tempfile.TemporaryDirectory() as d:
      root, src = make_wiki(Path(d), {"Orphan.md": "", "_Sidebar.md": ""})
      out = Path(d) / "out"
      problems = build_wiki.build(src, out, root)
      self.assertIn("Home.md is missing", problems)
      self.assertIn("Orphan.md: not linked from _Sidebar.md", problems)
      self.assertFalse(out.exists(), "nothing is written when a check fails")


class RealWikiTests(unittest.TestCase):
  def test_the_wiki_folder_checks_clean(self):
    self.assertEqual(build_wiki.build(), [])


if __name__ == "__main__":
  unittest.main()
