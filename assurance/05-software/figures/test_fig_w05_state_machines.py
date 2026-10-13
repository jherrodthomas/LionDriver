#!/usr/bin/env python3
"""Tests for fig_w05_state_machines.py: committed SVGs current, deterministic, well-formed, and drawn from the record."""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_w05_state_machines as fw

csm = fw.csm
NS = "{http://www.w3.org/2000/svg}"


def records() -> dict[str, dict]:
  return {csm.BLOCKS[sm["machine"]]: sm for sm in (csm.load(p) for p in sorted(csm.SM_DIR.glob("*.yaml")))}


class TestStateMachineFigures(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.figs = fw.outputs()
    cls.sms = records()
    cls.sw = csm.swsr_records()
    cls.doc = csm.WP_W05.read_text(encoding="utf-8")

  def svg_for(self, tag: str) -> str:
    return self.figs[Path(csm.figure_file(tag, csm.figure_number(tag, self.doc))).name]

  def test_committed_outputs_current(self):
    for name, content in self.figs.items():
      path = fw.HERE / name
      self.assertTrue(path.exists(), name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{name} is stale; run fig_w05_state_machines.py")

  def test_build_is_deterministic(self):
    self.assertEqual(fw.outputs(), self.figs)

  def test_one_figure_per_record_and_embedded(self):
    self.assertEqual(len(self.figs), len(self.sms))
    for tag in self.sms:
      fig = csm.figure_file(tag, csm.figure_number(tag, self.doc))
      self.assertIn(f"]({fig})", self.doc, f"WP-W-05 does not embed {fig}")

  def test_svgs_parse_with_role_title_desc(self):
    for name, content in self.figs.items():
      root = ET.fromstring(content)
      self.assertEqual(root.get("role"), "img", name)
      self.assertTrue(root.find(f"{NS}title").text.startswith("Figure 5-"), name)
      self.assertTrue(root.find(f"{NS}desc").text, name)

  def test_every_state_and_transition_drawn(self):
    for tag, sm in self.sms.items():
      content = self.svg_for(tag)
      texts = [t.text for t in ET.fromstring(content).iter(f"{NS}text")]
      for s in sm["states"]:
        self.assertIn(s, texts, f"{tag}: state {s}")
      for t in sm["transitions"]:
        self.assertIn(t["id"], texts, f"{tag}: transition {t['id']}")

  def test_pill_colour_is_the_checker_status(self):
    """Each transition pill has the colour of the status check_state_machines derives (the §5 table Status)."""
    for tag, sm in self.sms.items():
      content = self.svg_for(tag)
      for t in sm["transitions"]:
        colour = fw.STATUS[csm.transition_state(t, self.sw)][0]
        pat = rf'<rect [^>]*fill="{colour}"[^>]*/>\n<text [^>]*>{re.escape(t["id"])}</text>'
        self.assertRegex(content, pat, f"{tag} {t['id']}")

  def test_nothing_green(self):
    for name, content in self.figs.items():
      self.assertNotIn("#2E9E6A", content.upper(), f"{name}: green is reserved for verified; nothing is verified")

  def test_layout_has_no_collisions(self):
    for sm in self.sms.values():
      fw.render_figure(sm, self.sw, "5-9", "x")  # raises LayoutError when the geometric check fails


if __name__ == "__main__":
  unittest.main()
