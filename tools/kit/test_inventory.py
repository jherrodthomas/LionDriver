#!/usr/bin/env python3
"""Tests for the kit inventory's sorting rules (tools/kit/inventory.py)"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inventory as inv


def item(path, kind, lines=100, proj=0, pack=0):
  it = inv.Item(path, inv.area_of(path), kind, lines, proj, pack)
  inv.classify(it)
  return it


class TestKind(unittest.TestCase):
  def test_kinds(self):
    self.assertEqual(inv.kind_of("assurance/02-concept/figures/fig-c01.svg"), "generated")
    self.assertEqual(inv.kind_of("assurance/02-concept/figures/fig_c01_modes.py"), "code")
    self.assertEqual(inv.kind_of("assurance/01-management/figures/scene-style.md"), "record")
    self.assertEqual(inv.kind_of("assurance/sim/results/plant.json"), "generated")
    self.assertEqual(inv.kind_of("tools/safety/test_fmea_lint.py"), "test")
    self.assertEqual(inv.kind_of(".claude/skills/road-scene/SKILL.md"), "skill")
    self.assertEqual(inv.kind_of(".github/workflows/tests.yaml"), "workflow")


class TestOwnership(unittest.TestCase):
  def test_own_roots_and_upstream(self):
    self.assertTrue(inv.is_own("assurance/README.md", ""))
    self.assertTrue(inv.is_own("CLAUDE.md", None))
    self.assertFalse(inv.is_own("openpilot/selfdrive/car/card.py", "import os\n"))
    self.assertTrue(inv.is_own("openpilot/selfdrive/car/card.py", "# LionDriver TSR-629\n"))
    self.assertFalse(inv.is_own("panda/board/main.c", "LionDriver"))


class TestLayers(unittest.TestCase):
  def test_code(self):
    self.assertEqual(item("tools/x/tool.py", "code").layer, "method")
    self.assertEqual(item("tools/x/tool.py", "code", proj=10).layer, "project")
    self.assertEqual(item("tools/x/tool.py", "code", pack=5).layer, "pack")

  def test_upstream_change_and_outputs_are_project(self):
    self.assertEqual(item("openpilot/selfdrive/x.py", "code").layer, "project")
    self.assertEqual(item("assurance/x/figures/a.svg", "generated").layer, "project")

  def test_records(self):
    self.assertEqual(item("assurance/02-concept/hara.md", "record", pack=5).layer, "pack")
    self.assertEqual(item("assurance/process/README.md", "record").layer, "method")

  def test_hand_corrections_win(self):
    for path, (layer, _) in inv.HAND.items():
      self.assertEqual(item(path, "code", proj=100, pack=100).layer, layer, path)

  def test_project_name_is_a_setting_not_a_product_term(self):
    self.assertFalse(inv.PROJECT_TERMS.search("LionDriver review workbook"))
    self.assertTrue(inv.HARDCODE["project name"].search("LionDriver review workbook"))


class TestScan(unittest.TestCase):
  def test_scan_covers_the_must_carry_files(self):
    items = {it.path: it for it in inv.scan()}
    for _, *paths in inv.MUST_CARRY:
      for p in paths:
        assert p in items, p
    self.assertEqual(items["assurance/sim/blender/hazard_scene.py"].layer, "method")


if __name__ == "__main__":
  unittest.main()
