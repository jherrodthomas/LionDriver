#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path

from tools.sync.sync_report import Commit, classify, glob_to_regex, highest, load_rules, render


class TestGlob(unittest.TestCase):
  def test_double_star_spans_segments(self):
    r = glob_to_regex("panda/board/**")
    self.assertTrue(r.match("panda/board/main.c"))
    self.assertTrue(r.match("panda/board/drivers/spi.h"))
    self.assertFalse(r.match("panda/boardx/main.c"))
    self.assertFalse(r.match("panda/SConscript"))

  def test_single_star_stays_in_segment(self):
    r = glob_to_regex("opendbc_repo/opendbc/dbc/toyota_*.dbc")
    self.assertTrue(r.match("opendbc_repo/opendbc/dbc/toyota_nodsu_pt_generated.dbc"))
    self.assertFalse(r.match("opendbc_repo/opendbc/dbc/sub/toyota_x.dbc"))
    self.assertFalse(r.match("opendbc_repo/opendbc/dbc/honda_x.dbc"))

  def test_exact_path(self):
    r = glob_to_regex(".gitmodules")
    self.assertTrue(r.match(".gitmodules"))
    self.assertFalse(r.match("x.gitmodules"))
    self.assertFalse(r.match(".gitmodules.bak"))


class TestClassify(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.rules = load_rules()

  def test_envelope_is_sr_a(self):
    self.assertEqual(classify("opendbc_repo/opendbc/safety/modes/toyota.h", self.rules), "SR-A")
    self.assertEqual(classify("panda/board/main.c", self.rules), "SR-A")

  def test_most_specific_pattern_wins(self):
    # panda/board/body/** (SR-T) is more specific than panda/board/** (SR-A)
    self.assertEqual(classify("panda/board/body/main.c", self.rules), "SR-T")

  def test_toyota_port_and_stack_are_sr_q(self):
    self.assertEqual(classify("opendbc_repo/opendbc/car/toyota/carcontroller.py", self.rules), "SR-Q")
    self.assertEqual(classify("openpilot/selfdrive/selfdrived/selfdrived.py", self.rules), "SR-Q")
    self.assertEqual(classify("msgq_repo/msgq/ipc.cc", self.rules), "SR-Q")
    self.assertEqual(classify("rednose_repo/rednose/helpers/ekf_sym.py", self.rules), "SR-Q")

  def test_gitlinks_and_tooling_are_sr_t(self):
    self.assertEqual(classify("tinygrad_repo", self.rules), "SR-T")
    self.assertEqual(classify("tinygrad_repo/tinygrad/tensor.py", self.rules), "SR-T")
    self.assertEqual(classify(".github/workflows/tests.yaml", self.rules), "SR-T")

  def test_unlisted_is_nsr(self):
    self.assertEqual(classify("opendbc_repo/opendbc/car/honda/carcontroller.py", self.rules), "NSR")
    self.assertEqual(classify("docs/README.md", self.rules), "NSR")
    self.assertEqual(classify("msgq_repo/README.md", self.rules), "NSR")
    self.assertEqual(classify("msgq_repo/examples/publisher.py", self.rules), "NSR")

  def test_highest(self):
    self.assertEqual(highest(["NSR", "SR-T", "SR-A", "SR-Q"]), "SR-A")
    self.assertEqual(highest([]), "NSR")


class TestRulesFile(unittest.TestCase):
  def test_bad_line_rejected(self):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
      f.write("SR-X some/path\n")
    with self.assertRaises(ValueError):
      load_rules(Path(f.name))


class TestRender(unittest.TestCase):
  def contains(self, text, fragment):
    self.assertTrue(fragment in text, f"missing from report: {fragment!r}")

  def test_report_flags_highest_class_and_gitlinks(self):
    rules = load_rules()
    commits = [
      Commit("a" * 40, "safety: tweak | limits", ["opendbc_repo/opendbc/safety/lateral.h"], {}),
      Commit("b" * 40, "bump tinygrad", ["tinygrad_repo"], {"tinygrad_repo": "c" * 40}),
      Commit("d" * 40, "honda: docs", ["opendbc_repo/opendbc/car/honda/values.py"], {}),
    ]
    md = render("openpilot", "https://example/upstream.git", "1" * 40, "master", "2" * 40, commits, True, rules, "2026-10-10")
    self.contains(md, "| Highest class touched | **SR-A** |")
    self.contains(md, "`opendbc_repo/opendbc/safety/lateral.h`")
    self.contains(md, "| `tinygrad_repo` | `cccccccccccc` |")
    self.contains(md, "safety: tweak \\| limits")  # pipes escaped in table cells
    self.contains(md, "| `dddddddddd` | honda: docs | NSR | — |")


if __name__ == "__main__":
  unittest.main()
