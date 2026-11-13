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

  def test_repository_images_use_the_raw_address(self):
    with tempfile.TemporaryDirectory() as d:
      root, src = make_wiki(Path(d), {"Home.md": "", "_Sidebar.md": ""})
      (root / "docs").mkdir()
      (root / "docs" / "fig.svg").write_text("<svg/>", encoding="utf-8")
      problems: list[str] = []
      out = build_wiki.rewrite("![A figure](../docs/fig.svg) and [the file](../docs/fig.svg)", src / "Home.md", src, root, VALUES, problems)
      self.assertEqual(out, "![A figure](https://raw.githubusercontent.com/o/r/b/docs/fig.svg) and [the file](https://github.com/o/r/blob/b/docs/fig.svg)")
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


class VersionStampTests(unittest.TestCase):
  """The ledger version next to the first link to a work product (WP-P-04 §5, OI-7; DQ-441)."""

  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    self.root, self.src = make_wiki(Path(self.tmp.name), {"Home.md": "", "_Sidebar.md": ""})
    (self.root / "assurance" / "WP-S-02-tsr.md").write_text("# WP-S-02\n", encoding="utf-8")
    self.values = dict(VALUES, WP_STAMP={"WP-S-02": "0.68.0"})

  def tearDown(self):
    self.tmp.cleanup()

  def test_first_link_to_a_work_product_gets_its_version(self):
    out = build_wiki.rewrite("[WP-S-02](../assurance/WP-S-02-tsr.md) and [again](../assurance/WP-S-02-tsr.md#x)",
                             self.src / "Home.md", self.src, self.root, self.values, [])
    self.assertEqual(out, "[WP-S-02](https://github.com/o/r/blob/b/assurance/WP-S-02-tsr.md) <sub>v0.68.0</sub> and "
                          "[again](https://github.com/o/r/blob/b/assurance/WP-S-02-tsr.md#x)")

  def test_sidebar_footer_and_other_files_are_not_stamped(self):
    text = "[WP-S-02](../assurance/WP-S-02-tsr.md) [r](../assurance/README.md)"
    out = build_wiki.rewrite(text, self.src / "_Sidebar.md", self.src, self.root, self.values, [])
    self.assertNotIn("<sub>", out)
    out = build_wiki.rewrite("[r](../assurance/README.md)", self.src / "Home.md", self.src, self.root, self.values, [])
    self.assertNotIn("<sub>", out)

  def test_versions_table(self):
    table = build_wiki.render_wp_versions([{"doc": "WP-S-02", "title": "TSR | spec", "path": "assurance/WP-S-02-tsr.md",
                                            "version": "0.68.0+1", "status": "Draft", "changed": "2026-11-07"}], "o/r", "b")
    self.assertIn("| [WP-S-02](https://github.com/o/r/blob/b/assurance/WP-S-02-tsr.md) TSR / spec | 0.68.0+1 | Draft | "
                  "2026-11-07 |", table)
    self.assertEqual(build_wiki.render_wp_versions([], "o/r", "b"), build_wiki.NO_VERSIONS)

  def test_a_checkout_without_the_ledger_tools_builds_without_versions(self):
    files = {"Home.md": "{{WP_VERSIONS}} / {{LEDGER_SOURCE}}", "_Sidebar.md": "[Home](Home.md)"}
    with tempfile.TemporaryDirectory() as d:
      root, src = make_wiki(Path(d), files)
      out = Path(d) / "out"
      self.assertEqual(build_wiki.build(src, out, root), [])
      self.assertEqual((out / "Home.md").read_text(), build_wiki.NO_VERSIONS + " / not available in this checkout")

  def test_the_real_checkout_stamps_versions(self):
    entries, source = build_wiki.wp_versions(build_wiki.ROOT, "HEAD")
    self.assertGreater(len(entries), 50)
    self.assertTrue(source)
    self.assertTrue(all(e["version"][0].isdigit() for e in entries))


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


class MergeLogTests(unittest.TestCase):
  def test_no_git_checkout_gives_the_fallback_text(self):
    with tempfile.TemporaryDirectory() as d:
      self.assertEqual(build_wiki.git_merges(Path(d)), [])
      self.assertEqual(build_wiki.render_merge_log([], "o/r"), build_wiki.NO_MERGE_LOG)

  def test_entries_render_grouped_by_date_newest_first(self):
    entries = [("2026-10-17", 213, "HARA fallback ASILs", "7c00aa4"), ("2026-10-17", 211, "Add the wiki", "4d3fdac"),
               ("2026-10-16", 190, "Baseline BL-006 proposed", "abc1234")]
    out = build_wiki.render_merge_log(entries, "o/r")
    self.assertEqual(out.splitlines(), [
      "### 2026-10-17", "",
      "- [#213](https://github.com/o/r/pull/213) HARA fallback ASILs",
      "- [#211](https://github.com/o/r/pull/211) Add the wiki", "",
      "### 2026-10-16", "",
      "- [#190](https://github.com/o/r/pull/190) Baseline BL-006 proposed",
    ])

  def test_only_pull_request_merges_are_listed(self):
    """A temporary repository with a PR merge, a plain branch merge and the synthetic merge CI checks a PR out at."""
    import subprocess
    with tempfile.TemporaryDirectory() as d:
      root = Path(d)
      env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x",
             "GIT_AUTHOR_DATE": "2026-10-17T00:00:00Z", "GIT_COMMITTER_DATE": "2026-10-17T00:00:00Z", "PATH": "/usr/bin:/bin"}

      def git(*args):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, env=env)

      def commit(msg):
        (root / "f").write_text(msg)
        git("add", "f")
        git("commit", "-q", "-m", msg)

      git("init", "-q", "-b", "main")
      commit("base")
      git("checkout", "-q", "-b", "feature")
      commit("work")
      git("checkout", "-q", "main")
      git("merge", "--no-ff", "-q", "-m", "Merge pull request #7 from o/feature\n\nThe PR title", "feature")
      git("checkout", "-q", "-b", "other")
      commit("other work")
      git("checkout", "-q", "main")
      git("merge", "--no-ff", "-q", "-m", "Merge branch 'other' into main", "other")
      git("checkout", "-q", "-b", "pr-head")
      commit("pr work")
      git("checkout", "-q", "main")
      git("merge", "--no-ff", "-q", "-m", "Merge abc123 into def456", "pr-head")   # what CI checks a PR out at
      self.assertEqual(build_wiki.git_merges(root), [("2026-10-17", 7, "The PR title", build_wiki.git_merges(root)[0][3])])

  def test_merge_log_placeholder_is_filled_from_the_checkout(self):
    with tempfile.TemporaryDirectory() as d:
      root, src = make_wiki(Path(d), {"Home.md": "{{MERGE_LOG}}", "_Sidebar.md": "[Home](Home.md)"})
      out = Path(d) / "out"
      self.assertEqual(build_wiki.build(src, out, root, repo="o/r"), [])
      self.assertEqual((out / "Home.md").read_text(), build_wiki.NO_MERGE_LOG)

  def test_the_real_checkout_has_merge_history(self):
    entries = build_wiki.git_merges(build_wiki.ROOT)
    if not entries:
      self.skipTest("no merge history in this checkout (shallow clone)")
    self.assertTrue(all(n > 0 for _, n, _, _ in entries[:5]), "recent merges are pull request merges")


class RealWikiTests(unittest.TestCase):
  def test_the_wiki_folder_checks_clean(self):
    self.assertEqual(build_wiki.build(), [])


if __name__ == "__main__":
  unittest.main()
