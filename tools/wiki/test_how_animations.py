#!/usr/bin/env python3
"""Unit tests for how_animations.py: the records each figure stands on, the values read from them, the figures and the build."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_wiki
import how_animations as H


def copy_records(root: Path) -> None:
  for path in {p for p, _ in H.SOURCES} | {H.S02, H.S04, H.W09, H.TSR_LIST}:
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(H.ROOT / path, root / path)


class RecordTests(unittest.TestCase):
  def test_every_figure_stands_on_its_records(self):
    self.assertEqual(H.problems(), [])

  def test_values_are_read_from_the_records(self):
    d = H.data()
    self.assertEqual((d["cap"], d["up"], d["down"], d["err"]), (1500, 15, 25, 350))
    self.assertEqual((d["gap_ms"], d["rate_hz"], d["hb_s"], d["ftti"]), (50, 100, 0.3, 0.5))
    self.assertEqual(d["blocked"], ["0x2E4", "0x191", "0x412", "0x343"])
    self.assertEqual(set(d["status"]), set(H.TSRS))

  def test_a_changed_limit_is_drawn(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      copy_records(root)
      f = root / H.W09
      f.write_text(f.read_text(encoding="utf-8").replace("| `max_torque` | 1500 raw |", "| `max_torque` | 1200 raw |"), encoding="utf-8")
      self.assertIn("|torque| ≤ 1200", H.render(root)["how-envelope.svg"])

  def test_a_record_out_of_step_with_the_code_is_a_problem(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      copy_records(root)
      f = root / H.W09
      f.write_text(f.read_text(encoding="utf-8").replace("| `max_torque_error` | 350 raw |", "| `max_torque_error` | 300 raw |"), encoding="utf-8")
      (root / H.TOYOTA_H).parent.mkdir(parents=True)
      (root / H.TOYOTA_H).write_text("TOYOTA_TORQUE_STEERING_LIMITS = {.max_torque = 1500, .max_rate_up = 15, .max_rate_down = 25, "
                                     ".max_torque_error = 350, };\n{.addr = 0x2E4U, .bus = 0U, .frequency = 100U,\n"
                                     "{.addr = 0x2E4U, .bus = 0U, .timeout_us = 50000U,\n{0x2E4, 0, 8, .check_relay = true}\n", encoding="utf-8")
      errs = H.problems(root)
      self.assertTrue(any("max_torque_error is 350" in e for e in errs), errs)
      self.assertTrue(any("no longer blocked" in e for e in errs), errs)

  def test_an_implemented_requirement_leaves_the_open_note(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      copy_records(root)
      f = root / H.TSR_LIST
      lines = [ln.replace("| not implemented |", "| implemented |") if ln.startswith("| [TSR-108]") else ln
               for ln in f.read_text(encoding="utf-8").splitlines()]
      f.write_text("\n".join(lines) + "\n", encoding="utf-8")
      svg = H.render(root)["how-envelope.svg"]
      self.assertNotIn("(TSR-108)", svg.split("never reaches the car")[1])
      self.assertIn("(TSR-102)", svg)

  def test_a_lost_phrase_is_a_problem(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      copy_records(root)
      f = root / H.S03
      f.write_text(f.read_text(encoding="utf-8").replace("(relay released: direct link)", ""), encoding="utf-8")
      self.assertTrue(any("relay released" in e for e in H.problems(root)))


class RenderTests(unittest.TestCase):
  def test_all_render_to_well_formed_accessible_svg(self):
    out = H.render()
    self.assertEqual(tuple(out), H.NAMES)
    for name, text in out.items():
      doc = xml.dom.minidom.parseString(text.encode("utf-8"))
      self.assertTrue(doc.getElementsByTagName("title")[0].firstChild.data, name)
      self.assertTrue(doc.getElementsByTagName("desc")[0].firstChild.data, name)
      self.assertIn("prefers-reduced-motion: reduce", text)
      self.assertNotIn("mock-up", text.lower())

  def test_the_wiki_build_writes_all_and_accepts_the_embeds(self):
    with tempfile.TemporaryDirectory() as d:
      out = Path(d) / "wiki"
      self.assertEqual(build_wiki.build(out=out), [])
      page = (out / "How-LionDriver-works.md").read_text(encoding="utf-8")
      for name in H.NAMES:
        self.assertTrue((out / name).exists(), name)
        self.assertIn(f"]({name})", page)


if __name__ == "__main__":
  unittest.main()
