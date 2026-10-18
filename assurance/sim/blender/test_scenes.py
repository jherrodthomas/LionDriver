"""Checks of the hazardous-event scene list (CI; no Blender needed): every scene names an existing hazardous event
(or a SOTIF hazard) and plant case, exports, keeps its events inside its window, and every HARA hazardous event has a
scene. Every scene is built from the library (environment, condition, traffic) with a condition its environment
allows, a plant case drives the geometry its environment has, the library's codes match the HARA, and a variant
shows its base scene's motion and outcome under another condition. The street furniture of an urban scene stays on
its pavement and clear of every pedestrian and cyclist, intersection, traffic light and crosswalk."""

from __future__ import annotations

import copy
import math
import sys
import unittest

import export_scene
import street_layout

sys.path.insert(0, str(export_scene.ASSURANCE / "02-concept" / "hara"))
import hara_model  # noqa: E402


class TestScenes(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.hes = export_scene.hazardous_events()
    cls.lib = export_scene.load_library()
    cls.raw = export_scene.load_raw_scenes()
    cls.scenes = export_scene.load_scenes()
    cls.built = {s["id"]: export_scene.build(s, cls.hes, cls.lib) for s in cls.scenes}

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

  def test_every_scene_uses_the_library(self):
    for s in self.raw:
      self.assertIn(s.get("environment"), self.lib["environments"], s["id"])
      self.assertNotIn("type", s.get("road", {}), f"{s['id']}: the road type comes from the environment")

  def test_conditions_allowed_by_the_environment(self):
    for s in self.scenes:
      env = self.lib["environments"][s["environment"]]
      self.assertIn(s["conditions"], env["conditions"], s["id"])
    bad = copy.deepcopy(next(s for s in self.raw if s["environment"] == "highway-worn-markings"))
    bad["conditions"] = "W05"
    with self.assertRaises(SystemExit):
      export_scene.resolve(bad, self.lib)
    bad["variants"] = ["W05"]
    del bad["conditions"]
    with self.assertRaises(SystemExit):
      [export_scene.resolve(v, self.lib) for v in export_scene.expand(bad)]

  def test_plant_geometry_matches_the_environment(self):
    for s in self.scenes:
      want = self.lib["environments"][s["environment"]]["geometry"]
      if s.get("motion", "plant") == "plant":
        road = export_scene.plant_case(s)[1].road
      else:
        road = s["road"].get("geometry", "straight")
      curved = road != "straight"
      if want != "any":
        self.assertEqual(curved, want == "curve", f"{s['id']}: {road} on a {want} environment")

  def test_library_matches_the_hara(self):
    weather = {w[0]: w[2] for w in hara_model.WEATHER}
    situations = {o[0] for o in hara_model.SITUATIONS}
    for code, c in self.lib["conditions"].items():
      if code.startswith("W"):
        self.assertEqual(c["exposure"], weather.get(code), code)
        self.assertEqual(c["odd"], "in" if code in ("W01", "W02", "W03") else "outside", code)
    self.assertLessEqual({k for k in weather}, set(self.lib["conditions"]))
    for name, e in self.lib["environments"].items():
      self.assertLessEqual(set(e["os"]), situations, name)
      self.assertLessEqual(set(e["conditions"]), set(self.lib["conditions"]), name)
      self.assertIn(e.get("traffic", "none"), self.lib["traffic"], name)

  def test_traffic_is_never_critical_or_the_contact(self):
    for sid, sc in self.built.items():
      names = {a["name"] for a in sc["actors"] if a.get("traffic")}
      self.assertNotIn(sc["critical"], names, sid)
      if sc["contact"]:
        self.assertNotIn(sc["contact"]["who"], names, sid)

  def test_variants_keep_the_base_motion_and_outcome(self):
    variants = [s for s in self.scenes if s.get("variant_of")]
    self.assertGreater(len(variants), 0)
    for v in variants:
      a, b = self.built[v["variant_of"]], self.built[v["id"]]
      self.assertNotEqual(a["condition"]["code"], b["condition"]["code"], v["id"])
      for k in ("t", "speed", "lateral", "events", "contact", "gap", "ttc", "critical"):
        self.assertEqual(a[k], b[k], f"{v['id']}: {k}")
      own = lambda sc: {x["name"]: x["poses"] for x in sc["actors"] if not x.get("traffic")}
      self.assertEqual(own(a), own(b), v["id"])

  def test_street_furniture_keeps_clear(self):
    urban = [sc for sc in self.built.values() if sc["road"]["scenery"] == "urban"]
    self.assertTrue(urban)
    for sc in urban:
      items = street_layout.layout(sc)
      kinds = {it["kind"] for it in items}
      self.assertTrue({"lamp", "tree", "shelter"} <= kinds, sc["id"])
      walks = {side: (kerb, back) for side, kerb, back in street_layout.pavements(sc["road"])}
      users = [q for a in sc["actors"] if a["kind"] in ("pedestrian", "cyclist") for q in a["poses"]]
      junctions = [(p["s"], p.get("width", 14.0) / 2) for p in sc["props"] if p["kind"] == "intersection"]
      for it in items:
        kerb, back = walks[it["side"]]
        self.assertTrue(min(kerb, back) < it["d"] < max(kerb, back), (sc["id"], it))         # on the pavement
        near = min((math.hypot(it["x"] - q[0], it["y"] - q[1]) for q in users), default=math.inf)
        self.assertGreaterEqual(near, street_layout.CLEAR_M, (sc["id"], it))                   # nobody hidden
        for s0, half in junctions:
          self.assertGreater(abs(it["s"] - s0), half, (sc["id"], it))                         # not in the junction
        for cs in sc["road"].get("crosswalks") or []:
          self.assertGreater(abs(it["s"] - cs), street_layout.CLEAR_CROSSWALK_M, (sc["id"], it))

  def test_kinematic_values_resolve(self):
    self.assertEqual(export_scene.value("t_r"), 1.5)
    self.assertEqual(export_scene.value("a_driver_full + a_item_max"), -4.0)


if __name__ == "__main__":
  sys.exit(unittest.main())
