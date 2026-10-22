"""Checks of the risk-scene renderer (CI; no Blender): the template is current and its dropdowns follow the library,
a HARA row is pre-filled with its rating as written, the demo row's scene has exactly the motion and outcome of the
gallery scene it pictures, a look change keeps the outcome and a motion change does not, a row the library cannot
draw gets a plain reason, rows that look the same share a render, and run_sheet.py writes the results back."""

from __future__ import annotations

import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

import row_to_scene as rs  # first: puts ../blender on the path
import export_scene as ex  # noqa: E402
import prefill  # noqa: E402
import run_sheet  # noqa: E402
import template  # noqa: E402

DEMO = "F-01/M03/OS-01/W02"
REFERENCE = "he-01-2-hardover-adjacent--w02"      # the gallery scene the demo row pictures
ANALYSIS = ("t", "speed", "lateral", "lane_threshold", "ax", "ay", "eps_torque", "events", "contact", "gap", "ttc",
            "critical", "road", "props", "case", "motion", "provenance")


def own(data: dict) -> dict:
  return {a["name"]: a["poses"] for a in data["actors"] if not a.get("traffic")}


class TestRenderTool(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.ctx = rs.Context.load()
    cls.hara = next(a for a in rs.load_adapters() if a["id"] == "iso26262-hara")
    cls.src = rs.source_rows(cls.hara)
    cls.row = rs.prefill(cls.hara, DEMO, cls.ctx, cls.src)

  def scene(self, **change):
    row = {**self.row, **change}
    sc, notes = rs.row_to_scene(row, self.hara, self.ctx)
    return rs.export(sc, self.ctx), notes

  def test_template_current(self):
    self.assertEqual(template.cells(load_workbook(template.TEMPLATE)), template.cells(template.build(self.ctx)))

  def test_template_lists_follow_the_library(self):
    lst = template.lists(self.ctx)
    self.assertEqual([r[0] for r in lst["Environment"]], list(self.ctx.lib["environments"]))
    self.assertEqual([r[0] for r in lst["Condition"]], list(self.ctx.lib["conditions"]))
    self.assertEqual([r[0] for r in lst["Motion preset"]], list(self.ctx.presets))
    ws = template.build(self.ctx)[self.hara["method"]]
    self.assertEqual(list(template.header(ws)), [c[0] for c in rs.columns(self.hara)])
    self.assertEqual(len(ws.data_validations.dataValidation), 4)

  def test_adapter_columns_exist_in_the_source(self):
    cols = next(iter(self.src.values())).keys()
    for c in self.hara["rating"]:
      self.assertIn(c["source"], cols, c["column"])
    for k in ("key", "situation", "condition", "hazard"):
      self.assertIn(self.hara["prefill"][k], cols, k)

  def test_prefill_copies_the_rating_as_written(self):
    r = self.src[DEMO]
    self.assertEqual((self.row["S"], self.row["E"], self.row["C"], self.row["ASIL"]), (r["S"], r["E"], r["C"], r["ASIL"]))
    self.assertEqual((self.row["Motion preset"], self.row["Environment"], self.row["Condition"]),
                     ("he-01-2-hardover-adjacent", "highway-free-flow", "W02"))

  def test_demo_row_matches_the_gallery_scene(self):
    data, notes = self.scene()
    ref = ex.build(next(s for s in ex.load_scenes() if s["id"] == REFERENCE), self.ctx.hes, self.ctx.lib)
    self.assertEqual(notes, [])
    for k in ANALYSIS + ("actors", "env", "condition", "environment", "traffic"):
      self.assertEqual(data[k], ref[k], k)
    self.assertIsNotNone(data["contact"])

  def test_card_shows_the_row(self):
    data, _ = self.scene()
    cd = data["card"]
    self.assertEqual(cd["heading"], f"HARA row {DEMO}")
    self.assertIn(["ASIL", "B"], cd["rows"])
    self.assertIn(["Controllability", "C2"], cd["rows"])
    self.assertEqual(cd["title"], self.src[DEMO]["Hazard"])

  def test_look_keeps_the_outcome(self):
    base, _ = self.scene()
    for change in ({"Condition": "W03"}, {"Condition": "W05"}, {"Traffic": "dense"}, {"Condition": "TC-01"}):
      data, _ = self.scene(**change)
      for k in ANALYSIS:
        self.assertEqual(data[k], base[k], f"{change}: {k}")
      self.assertEqual(own(data), own(base), change)
      self.assertNotEqual(rs.render_key(data), rs.render_key(base), change)

  def test_motion_changes_the_outcome_and_says_so(self):
    base, _ = self.scene()
    data, _ = self.scene(**{"Speed km/h": 90})
    self.assertNotEqual(data["speed"], base["speed"])
    self.assertIn("90", data["provenance"])
    self.assertIn("90 km/h, set by the row", data["caption"])

  def test_same_picture_shares_a_render(self):
    a, _ = self.scene()
    b, _ = self.scene(**{"Row ID": "another row", "Title": "x", "ASIL": "C"})
    self.assertEqual(rs.render_key(a), rs.render_key(b))
    self.assertNotEqual(a["card"], b["card"])

  def test_plain_reasons(self):
    cases = [
      ({"Motion preset": "no-such-scene"}, "is not a scene of scenes.yaml"),
      ({"Motion preset": None}, "pick a motion preset"),
      ({"Environment": "moon"}, "not in the library"),
      ({"Condition": "W09"}, "not in the library"),
      ({"Environment": "highway-construction", "Condition": "W05"}, "is not drawn under W05"),
      ({"Environment": "highway-curve"}, "drives a straight road"),
      ({"Speed km/h": "fast"}, "is not a number"),
      ({"Speed km/h": 400}, "outside 5 to 160"),
      ({"Row ID": None}, "no Row ID"),
    ]
    for change, text in cases:
      with self.assertRaises(rs.RowError, msg=str(change)) as e:
        rs.row_to_scene({**self.row, **change}, self.hara, self.ctx)
      self.assertIn(text, str(e.exception), change)
    with self.assertRaises(rs.RowError) as e:
      rs.prefill(self.hara, "F-01/M01/OS-19/W01", self.ctx, self.src)
    self.assertEqual(str(e.exception), "no library environment draws OS-19 yet")

  def test_notes_on_a_changed_environment(self):
    _, notes = rs.row_to_scene({**self.row, "Environment": "highway-worn-markings"}, self.hara, self.ctx)
    self.assertTrue(any("can change the outcome" in n for n in notes), notes)

  def test_every_drawable_hara_row_exports(self):
    """One row per hazard, situation and condition the library draws: pre-filled, it exports with an outcome."""
    seen = set()
    for key, r in self.src.items():
      pair = (r["Hazard"].split()[0], r["Situation"])
      if pair in seen:
        continue
      seen.add(pair)
      try:
        row = rs.prefill(self.hara, key, self.ctx, self.src)
      except rs.RowError as e:
        self.assertRegex(str(e), r"^no (library environment draws OS-\d+|motion preset pictures H-\d+) yet$")
        continue
      sc, _ = rs.row_to_scene(row, self.hara, self.ctx)
      data = rs.export(sc, self.ctx)
      self.assertIn(set(rs.outcome(data)), [{"Contact", "Smallest gap m", "Smallest TTC s", "Motion source"}], key)

  def test_run_sheet_writes_the_results(self):
    with tempfile.TemporaryDirectory() as tmp:
      sheet = Path(tmp) / "s.xlsx"
      shutil.copy(template.TEMPLATE, sheet)
      with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        prefill.main([str(sheet), DEMO, "F-01/M01/OS-19/W01"])
        run_sheet.main([str(sheet), "--no-render"])
      got = {v["Row ID"]: v for _, v in template.rows(load_workbook(sheet)[self.hara["method"]])}
      self.assertTrue(got[DEMO]["Status"].startswith("exported"))
      self.assertTrue(got[DEMO]["Contact"].startswith("yes: adjacent car"))
      self.assertEqual(got[DEMO]["Motion source"], "plant, case F-01b (synthetic, no evidence credit)")
      self.assertEqual(got["F-01/M01/OS-19/W01"]["Status"], "cannot draw: no library environment draws OS-19 yet")


if __name__ == "__main__":
  unittest.main()
