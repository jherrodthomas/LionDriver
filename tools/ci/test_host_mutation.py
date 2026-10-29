#!/usr/bin/env python3
"""Tests for host_mutation.py: the mutant list is well formed and still matches the code; no openpilot build needed."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import host_mutation as hm


class TestMutantList(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.mutants = hm.load()

  def test_every_mutant_matches_its_file_once(self):
    for m in self.mutants:
      text = (hm.REPO / m.file).read_text(encoding="utf-8")
      self.assertEqual(text.count(m.find), 1, m.id)
      self.assertNotEqual(hm.mutate(text, m), text, m.id)

  def test_tests_exist(self):
    for m in self.mutants:
      for t in m.tests:
        self.assertTrue((hm.REPO / t).is_file(), f"{m.id}: {t}")

  def test_every_mutant_backs_a_cause(self):
    for m in self.mutants:
      self.assertTrue(all(c.startswith(("SWF-", "SFM-")) and ".C" in c for c in m.fmea), m.id)


class TestLoader(unittest.TestCase):
  def _load(self, body):
    with tempfile.TemporaryDirectory() as d:
      p = Path(d) / "m.toml"
      p.write_text("schema_version = 1\n" + body, encoding="utf-8")
      return hm.load(p)

  ENTRY = '[[mutants]]\nid = "X-1"\nfile = "f.py"\nfind = "a"\nreplace = "{r}"\ntests = ["t.py"]\nfmea = ["SWF-001.C1"]\nwhy = "w"\n'

  def test_duplicate_id_rejected(self):
    with self.assertRaisesRegex(hm.MutantError, "duplicate"):
      self._load(self.ENTRY.format(r="b") * 2)

  def test_no_op_mutant_rejected(self):
    with self.assertRaisesRegex(hm.MutantError, "replace equals find"):
      self._load(self.ENTRY.format(r="a"))

  def test_find_must_occur_once(self):
    m = self._load(self.ENTRY.format(r="b"))[0]
    with self.assertRaisesRegex(hm.MutantError, "0 times"):
      hm.mutate("xyz", m)
    with self.assertRaisesRegex(hm.MutantError, "2 times"):
      hm.mutate("a a", m)
    self.assertEqual(hm.mutate("xay", m), "xby")


if __name__ == "__main__":
  unittest.main()


class TestBytecode(unittest.TestCase):
  def test_same_length_mutant_is_not_masked_by_cached_bytecode(self):
    # the original is imported (and cached) and the mutant written within the same second: same size, same mtime
    import importlib
    with tempfile.TemporaryDirectory() as d:
      src = Path(d) / "hm_probe_mod.py"
      src.write_text("VALUE = 2\n", encoding="utf-8")
      sys.path.insert(0, d)
      try:
        mod = importlib.import_module("hm_probe_mod")
        self.assertEqual(mod.VALUE, 2)
        st = src.stat()
        hm.write_source(src, "VALUE = 3\n")
        os.utime(src, ns=(st.st_atime_ns, st.st_mtime_ns))
        del sys.modules["hm_probe_mod"]
        self.assertEqual(importlib.import_module("hm_probe_mod").VALUE, 3)
      finally:
        sys.path.remove(d)
        sys.modules.pop("hm_probe_mod", None)
