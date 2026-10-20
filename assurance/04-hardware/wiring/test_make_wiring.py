#!/usr/bin/env python3
"""Tests for make_wiring.py: sources keep their rules, outputs current, pinouts agree across drawings and with the
v3 drawings as transcribed in README section 3."""

import csv
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_wiring as mw


def load(name: str) -> dict:
  return yaml.safe_load((mw.HERE / f"{name}.yaml").read_text(encoding="utf-8"))


def labels(conn: dict) -> dict:
  pins = conn.get("pins") or list(range(1, len(conn["pinlabels"]) + 1))
  return {str(p): lab for p, lab in zip(pins, conn["pinlabels"])}


class TestSources(unittest.TestCase):
  def test_no_source_problems(self):
    for p in mw.sources():
      self.assertEqual(mw.problems(p), [], p.name)

  def test_drawing_codes_unique(self):
    codes = [load(p.stem)["metadata"]["drawing"] for p in mw.sources()]
    self.assertEqual(len(codes), len(set(codes)))

  def test_problems_catches_angle_brackets_and_pin_mismatch(self):
    bad = mw.HERE / "_bad_test_source.yaml"
    try:
      bad.write_text("metadata: {title: t}\nconnectors:\n  X: {pins: [1, 2], pinlabels: [a<b]}\n", encoding="utf-8")
      errs = mw.problems(bad)
    finally:
      bad.unlink()
    self.assertEqual(len(errs), 3, errs)


class TestPinouts(unittest.TestCase):
  """The same signal sits on the same pin in every drawing that shows it."""

  @classmethod
  def setUpClass(cls):
    cls.ta = load("e05-toyota-a-harness")
    cls.hb = load("e05-harness-box")
    cls.oc = load("e05-obdc-device")

  def test_camera_and_car_connectors_mirror(self):
    # the harness is inserted in line: same pin positions on both TE connectors, camera CAN2 in place of car CAN0
    cam, car = labels(self.ta["connectors"]["X1"]), labels(self.ta["connectors"]["X2"])
    for pin in cam:
      self.assertEqual(cam[pin].replace("CAN2", "CAN0").replace("camera", "car"), car[pin], pin)

  def test_plug_x3_matches_box_header_j1(self):
    x3, j1 = labels(self.ta["connectors"]["X3"]), labels(self.hb["connectors"]["J1"])
    for pin in map(str, range(1, 19)):
      net = j1[pin].split(" ")[0]
      self.assertIn(net.replace("_12", ""), x3[pin].replace("12VIN", "VIN"), pin)

  def test_cable_branches_land_on_matching_signals(self):
    rows = list(csv.DictReader(mw.wire_ends([mw.HERE / "e05-toyota-a-harness.yaml"]).splitlines(), delimiter="\t"))
    for r in rows:
      self.assertTrue(r["end A label"].startswith(r["signal"]), r)
      self.assertTrue(r["end B label"].startswith(r["signal"]), r)

  def test_box_receptacle_same_in_both_drawings(self):
    j3a, j3b = labels(self.hb["connectors"]["J3"]), labels(self.oc["connectors"]["J3"])
    for pin, lab in j3b.items():
      self.assertIn(pin, j3a)
      self.assertEqual(lab.split(" ")[0], j3a[pin].split(" ")[0], pin)

  def test_obdc_cable_is_usb_c_full_featured_wiring(self):
    # USB Type-C full-featured cable: TX/RX pairs and SBU cross between the rows, VBUS and GND straight
    cross = {"A2": "B11", "A3": "B10", "B2": "A11", "B3": "A10", "A11": "B2", "A10": "B3",
             "B11": "A2", "B10": "A3", "A8": "B8", "B8": "A8", "A4": "A4", "A1": "A1"}
    a, _, b = self.oc["connections"][0]
    self.assertEqual(dict(zip(a["J3"], b["P1"])), cross)

  def test_switch_drive_reaches_device_relay_pin(self):
    # NORMAL orientation (panda harness.h): the device drives the relay on its SBU2, which is the box SBU1
    p1 = labels(self.oc["connectors"]["P1"])
    self.assertIn("relay drive", p1["B8"])
    self.assertIn("ignition", p1["A8"])


class TestOutputs(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.out = mw.build()
    cls.dot_ok = mw.dot_version() == mw.DOT_VERSION

  def test_committed_outputs_current(self):
    self.assertEqual(mw.check(self.out, self.dot_ok), [])

  def test_build_is_deterministic(self):
    self.assertEqual(mw.build(), self.out)

  def test_svgs_parse(self):
    for name, text in self.out.items():
      if name.endswith(".svg"):
        ET.fromstring(text)

  def test_wire_ids_unique_and_prefixed(self):
    rows = list(csv.DictReader(self.out[mw.WIRE_ENDS.name].splitlines(), delimiter="\t"))
    ids = [r["id"] for r in rows]
    self.assertEqual(len(ids), len(set(ids)))
    for r in rows:
      self.assertTrue(r["id"].startswith(r["drawing"] + "."), r["id"])

  def test_every_drawing_embedded_or_listed(self):
    readme = (mw.HERE / "README.md").read_text(encoding="utf-8")
    for p in mw.sources():
      self.assertIn(f"{p.stem}.svg", readme, p.stem)


if __name__ == "__main__":
  unittest.main()
