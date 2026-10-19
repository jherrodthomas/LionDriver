#!/usr/bin/env python3
"""Tests for stpa_scenes.py: one card per UCA of WP-A-05 §4.1–§4.3, IDs checked, scenes loop, no second copy of fig_a05_stpa."""

import copy
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_a05_stpa as fs
import stpa_scenes as ss


class TestScenes(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.S = fs.load()
    cls.out = ss.sheets(cls.S, fs)

  def test_one_card_per_uca_of_each_controller(self):
    counts = {}
    for name, (ctrl, num, _) in ss.SHEETS.items():
      ucas = ss.card_ucas(self.S, ctrl)
      counts[ctrl] = len(ucas)
      cards = re.findall(r"<title>(UCA-\d+): ", self.out[name])
      self.assertEqual(cards, ucas, name)
      self.assertIn(f"Figure {num}.", self.out[name])
    self.assertEqual(counts, {"C1 Driver": 7, "C2 openpilot": 12, "C3 panda": 7})
    self.assertEqual(set(ss.MODEL), {u for c, _, _ in ss.SHEETS.values() for u in ss.card_ucas(self.S, c)})

  def test_card_shows_the_type_from_wp_a05(self):
    for name in ss.SHEETS:
      for uid, typ in re.findall(r"(UCA-\d+) · [^<]* · TYPE ([NPTD]),", self.out[name]):
        self.assertEqual(typ, self.S.ucas[uid]["type"], uid)

  def test_footer_status_comes_from_the_map(self):
    svg = self.out["fig-a05-4-4-scenes-panda.svg"]
    self.assertIn("LS-05 · covered · component failure", svg)
    self.assertIn("LS-33 · known gap · actuator failure", svg)

  def test_uca_without_a_card_fails(self):
    model = dict(ss.MODEL)
    del model["UCA-04"]
    with mock.patch.object(ss, "MODEL", model):
      with self.assertRaisesRegex(fs.ParseError, "no scene card for UCA-04"):
        ss.sheets(self.S, fs)

  def test_card_for_a_uca_not_in_the_tables_fails(self):
    S = copy.copy(self.S)
    S.ucas = {u: v for u, v in self.S.ucas.items() if u != "UCA-36"}
    with self.assertRaisesRegex(fs.ParseError, "not in WP-A-05 §4.1–§4.3: UCA-36"):
      ss.sheets(S, fs)

  def test_unknown_id_on_a_card_fails(self):
    for bad, msg in (("LS-999", "LS-999"), ("DQ-999", "DQ-999"), ("FB-99", "FB-99")):
      model = copy.deepcopy(ss.MODEL)
      model["UCA-10"]["true"] += f" ({bad})"
      with mock.patch.object(ss, "MODEL", model):
        with self.assertRaisesRegex(fs.ParseError, msg):
          ss.sheets(self.S, fs)

  def test_scenario_not_linked_to_the_uca_fails(self):
    model = copy.deepcopy(ss.MODEL)
    model["UCA-10"]["ls"] = ["LS-02"]
    with mock.patch.object(ss, "MODEL", model):
      with self.assertRaisesRegex(fs.ParseError, "does not link"):
        ss.sheets(self.S, fs)

  def test_scenes_loop_and_still_pose_is_the_key_moment(self):
    for svg in self.out.values():
      self.assertEqual(svg.count('repeatCount="indefinite"'), svg.count("<animate"))
    m = ss.MODEL["UCA-10"]["scene"]
    (x, y), _ = ss.pose_at(ss.samples(m["act"]), m["still"])
    self.assertIn(f'translate({x:.1f} {y:.1f})', self.out["fig-a05-4-3-scenes-openpilot.svg"])

  def test_output_is_deterministic(self):
    self.assertEqual(self.out, ss.sheets(self.S, fs))

  def test_does_not_import_fig_a05_stpa(self):
    # fig_a05_stpa runs as __main__; importing it here would load a second copy whose ParseError main() does not catch
    src = Path(ss.__file__).read_text(encoding="utf-8")
    self.assertNotRegex(src, r"(?m)^\s*(import|from)\s+fig_a05_stpa")
    self.assertNotIn("fig_a05_stpa", {m.split(".")[0] for m in re.findall(r"^\s*import (\S+)", src, re.M)})


if __name__ == "__main__":
  unittest.main()
