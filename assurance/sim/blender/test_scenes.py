"""Checks of the hazardous-event scene list (CI; no Blender needed): every scene names an existing hazardous event
and plant case, exports, and its contact and event times fall inside its window."""

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

  def test_illustrative_actors_are_marked(self):
    for s in self.scenes:
      for a in s.get("actors", []):
        self.assertEqual(a["source"], "illustrative", f"{s['id']}: {a['name']}")

  def test_export(self):
    for sid, sc in self.built.items():
      n = len(sc["t"])
      self.assertGreater(n, 24, sid)
      for a in sc["actors"]:
        self.assertEqual(len(a["poses"]), n, f"{sid}: {a['name']}")
      for key in ("speed", "lateral", "ax", "ay", "eps_torque"):
        self.assertEqual(len(sc[key]), n, f"{sid}: {key}")
      self.assertTrue(any(e["label"] == "fault" for e in sc["events"]), sid)
      for e in sc["events"]:
        self.assertTrue(sc["t"][0] - 1e-6 <= e["t"] <= sc["t"][-1] + 1e-6, f"{sid}: {e}")

  def test_hardover_reaches_adjacent_car(self):
    sc = self.built["he-01-2-hardover-adjacent"]
    contact = [e for e in sc["events"] if e["label"].startswith("contact")]
    self.assertEqual(len(contact), 1)
    self.assertAlmostEqual(sc["t"][-1], contact[0]["t"] + export_scene.END_AFTER_CONTACT, delta=0.05)


if __name__ == "__main__":
  sys.exit(unittest.main())
