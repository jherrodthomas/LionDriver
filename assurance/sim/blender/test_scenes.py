"""Checks of the hazardous-event scene list (CI; no Blender needed): every scene names an existing hazardous event
(or a SOTIF hazard) and plant case, exports, keeps its events inside its window, and every HARA hazardous event has a
scene. Every scene is built from the library (environment, condition, traffic) with a condition its environment
allows, a plant case drives the geometry its environment has, the library's codes match the HARA, and a variant
shows its base scene's motion and outcome under another condition. The street furniture of an urban scene stays on
its pavement and clear of every pedestrian and cyclist, intersection, traffic light and crosswalk. The committed
pedestrian figures carry their walk and clothes slots. The look of the surroundings never changes the analysis."""

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

  def test_lamp_rows_keep_clear(self):
    """Every post of a `lamps` row stands outside the carriageway and beyond the barrier line, and never near the
    chase camera or on its line of sight to the ego."""
    rows = [(sc, p) for sc in self.built.values() for p in sc["props"] if p["kind"] == "lamps"]
    self.assertTrue({sc["environment"]["id"] for sc, _ in rows} >= {"highway-free-flow", "highway-curve"})
    for sc, p in rows:
      left, right = sc["road"]["carriageway"]
      b = sc["road"]["barrier"]
      self.assertFalse(right <= p["d"] <= left, sc["id"])
      if b is not None and p["d"] < 0:
        self.assertLess(p["d"], b, sc["id"])
      lines = street_layout.sight_lines(sc)
      for q in street_layout.lamp_row(sc, p):
        self.assertFalse(street_layout.in_view(lines, q["x"], q["y"], street_layout.PLACE["lamp"][1]),
                         (sc["id"], q))

  def test_pedestrian_figures(self):
    """The committed CC0 figures carry the walk, the rig and the clothes slots hazard_scene.py recolours."""
    import json
    import struct
    people = export_scene.HERE / "library" / "people"
    for name in ("pedestrian_male.glb", "pedestrian_female.glb"):
      blob = (people / name).read_bytes()
      self.assertEqual(blob[:4], b"glTF", name)
      gltf = json.loads(blob[20:20 + struct.unpack("<I", blob[12:16])[0]])
      self.assertIn("Walk_Loop", [a.get("name") for a in gltf.get("animations", [])], name)
      self.assertEqual(len(gltf.get("skins", [])), 1, name)
      self.assertLessEqual({"shirt", "trousers", "shoes"}, {m["name"] for m in gltf["materials"]}, name)
      self.assertLess(len(blob), 3_000_000, name)
    for s in self.raw:
      for a in s.get("actors", []):
        if "figure" in a:
          self.assertIn(a["figure"], ("male", "female"), s["id"])

  def test_surroundings_never_reach_the_analysis(self):
    """The look keys of the surroundings (scene_assets.build_surroundings) take valid values, and every scene exports
    the same motion, events, contact, gap, TTC, poses, cross-section and props with all of them removed."""
    look = {"horizon", "haze_km", "terrain", "verge_plants", "distant", "cloud_shadows", "spray", "road_wear",
            "camera_feel"}
    for kind in ("environments", "conditions"):
      for name, e in self.lib[kind].items():
        env = e.get("env", {})
        self.assertIn(env.get("terrain", "rolling"), ("rolling", "ditch", "embankment"), name)
        self.assertLessEqual(set(env.get("distant", [])), {"pylons", "billboard", "farm", "flyover"}, name)
        self.assertTrue(0.0 <= env.get("spray", 0.0) <= 1.0, name)
        self.assertGreater(env.get("haze_km", 1.0), 0.0, name)
    bare = copy.deepcopy(self.lib)
    for kind in ("environments", "conditions"):
      for e in bare[kind].values():
        e["env"] = {k: v for k, v in e.get("env", {}).items() if k not in look}
    keys = ("t", "speed", "lateral", "lane_threshold", "ax", "ay", "eps_torque", "events", "contact", "gap", "ttc",
            "critical", "road", "props", "actors")
    self.assertTrue(any(self.built[s["id"]]["env"].get("horizon") for s in self.scenes))
    for s in (export_scene.resolve(v, bare) for r in self.raw for v in export_scene.expand(r)):
      self.assertFalse(look & set(s["env"]), s["id"])
      plain = export_scene.build(s, self.hes, bare)
      for k in keys:
        self.assertEqual(plain[k], self.built[s["id"]][k], f"{s['id']}: {k}")

  def test_kinematic_values_resolve(self):
    self.assertEqual(export_scene.value("t_r"), 1.5)
    self.assertEqual(export_scene.value("a_driver_full + a_item_max"), -4.0)


if __name__ == "__main__":
  sys.exit(unittest.main())
