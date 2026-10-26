"""Tests of check_schema.py: the committed items pass, and the schema rejects what it is meant to."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_schema

GOOD = """- id: H-99
  kind: hazard
  title: "Test hazard"
  functions: [F-01]
  status: proposed
  source: WP-C-03
"""


class TestSchema(unittest.TestCase):
  def run_items(self, text):
    with tempfile.TemporaryDirectory() as d:
      (Path(d) / "x.yaml").write_text(text, encoding="utf-8")
      return check_schema.problems(Path(d))

  def test_committed_items_valid(self):
    n, errs = check_schema.problems()
    self.assertGreater(n, 400)
    self.assertEqual(errs, [])

  def test_schema_is_valid_2020_12(self):
    schema = json.loads(check_schema.SCHEMA.read_text(encoding="utf-8"))
    check_schema.jsonschema.Draft202012Validator.check_schema(schema)

  def test_good_item(self):
    self.assertEqual(self.run_items(GOOD), (1, []))

  def test_missing_required_field_of_its_kind(self):
    _, errs = self.run_items(GOOD.replace('  title: "Test hazard"\n', ""))
    self.assertTrue(any("'title' is a required property" in e for e in errs), errs)

  def test_bad_status_and_id(self):
    _, errs = self.run_items(GOOD.replace("status: proposed", "status: done").replace("H-99", "HAZ-1"))
    self.assertEqual(len(errs), 2, errs)

  def test_event_asil_and_classes(self):
    he = """- id: HE-99.1
  kind: hazardous-event
  parents: [H-01]
  situation: "s"
  effect: "e"
  s: 4
  e: 3
  c: 2
  asil: "B (proposed)"
  aou_flag: false
  aou_dependency: []
  asil_if_aou_fails: null
  status: proposed
  source: WP-C-03
"""
    _, errs = self.run_items(he)
    self.assertEqual(len(errs), 2, errs)  # s above 3, asil not one of QM, A to D

  def test_interface_item_agreed_only_with_review(self):
    ifr = """- id: IFR-99
  kind: interface-requirement
  interface: IX-99
  title: "t"
  owners: ["Safety manager", "SOTIF lead"]
  open_item: null
  review_ref: null
  status: proposed
  source: WP-P-11
"""
    self.assertEqual(self.run_items(ifr), (1, []))
    self.assertEqual(self.run_items(ifr.replace("review_ref: null", "review_ref: REV-001")
                                    .replace("status: proposed", "status: agreed")), (1, []))
    _, errs = self.run_items(ifr.replace("status: proposed", "status: agreed"))
    self.assertEqual(len(errs), 1, errs)  # agreed without a review record
    _, errs = self.run_items(ifr.replace("status: proposed", "status: verified")
                             .replace('"SOTIF lead"]', '"Safety manager"]'))
    self.assertEqual(len(errs), 2, errs)  # not an interface status; the same owner twice


if __name__ == "__main__":
  unittest.main()
