"""Checks of the hazardous-event scene list (CI; no Blender needed): every scene names an existing hazardous event
(or a SOTIF hazard) and plant case, exports, keeps its events inside its window, and every HARA hazardous event has a
scene."""

from __future__ import annotations

import sys
import unittest

import export_scene


class TestScenes(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.hes = export_scene.hazardous_events()
    cls.scenes = export_scene.load_scenes()
    cls.built = {s["id"]: export_scene.build(s, cls.hes) for s in cls.scenes}

  def test_ids_unique(self):
    ids = [s["id"] for s in self.scenes]
    self.assertEqual(len(ids), len(set(ids)))

  def test_every_hazardous_event_has_a_scene(self):
    want = {k for k, v in self.hes.items() if v["kind"] == "hazardous-event"}
    have = {s["he"] for s in self.scenes if "he" in s}
    self.assertEqual(want - have, set())

  def test_export(self):
    for sid, sc in self.built.items():
      n = len(sc["t"])
      self.assertGreater(n, 24, sid)
      for a in sc["actors"]:
        self.assertEqual(len(a["poses"]), n, f"{sid}: {a['name']}")
      for key in ("speed", "lateral", "ax", "ay"):
        self.assertEqual(len(sc[key]), n, f"{sid}: {key}")
      self.assertTrue(any(e["t"] == 0.0 for e in sc["events"]), sid)
      for e in sc["events"]:
        self.assertTrue(sc["t"][0] - 1e-6 <= e["t"] <= sc["t"][-1] + 1e-6, f"{sid}: {e}")

  def test_hardover_reaches_adjacent_car(self):
    sc = self.built["he-01-2-hardover-adjacent"]
    self.assertIsNotNone(sc["contact"])
    self.assertEqual(sc["contact"]["who"], "adjacent car")
    self.assertAlmostEqual(sc["t"][-1], sc["contact"]["t"] + export_scene.END_AFTER_CONTACT, delta=0.05)

  def test_not_engaged_requests_are_refused(self):
    for sid in ("he-01-4-not-engaged-torque", "he-04-4-manual-braking-command"):
      sc = self.built[sid]
      self.assertLess(max(abs(v) for v in sc["lateral"]), 0.01, sid)
      self.assertLess(max(sc["speed"]) - min(sc["speed"]), 0.1, sid)

  def test_kinematic_values_resolve(self):
    self.assertEqual(export_scene.value("t_r"), 1.5)
    self.assertEqual(export_scene.value("a_driver_full + a_item_max"), -4.0)


if __name__ == "__main__":
  sys.exit(unittest.main())
