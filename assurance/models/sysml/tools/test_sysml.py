#!/usr/bin/env python3
"""Tests for the SysML model tooling: reader, checks, renderer and explorer."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_model
import explorer
import render_views
import svgkit
import sysml_lite

MINI = """
package L {
    private import ScalarValues::*;
    enum def Integrity { enum QM; enum BDagger; }
    metadata def Safety { attribute integrity : Integrity; attribute label : String; }
    port def P;
    interface def Link { end port source : P; end port target : P; }
    part def A { port p : P; }
    part def Item {
        doc /* The item. */
        part <'E-01'> a : A { @Safety { integrity = Integrity::QM; label = "QM"; } }
        part <'E-03'> b : A { @Safety { integrity = Integrity::BDagger; label = "B‡"; } }
        interface ab : Link connect source ::> a.p to target ::> b.p;
    }
    part ctx : Item;
}
"""


class Reader(unittest.TestCase):
  def test_parses_subset(self):
    pkgs = sysml_lite.parse_text(MINI)
    item = pkgs[0].member("Item")
    self.assertEqual(item.doc, "The item.")
    a = item.member("E-01")
    self.assertEqual((a.name, a.short, a.type), ("a", "E-01", "A"))
    self.assertEqual(a.meta["Safety"]["integrity"], "Integrity::QM")
    conn = item.member("ab")
    self.assertEqual(conn.ends, [("source", "a.p"), ("target", "b.p")])

  def test_refuses_unknown_construct(self):
    with self.assertRaisesRegex(sysml_lite.ModelError, r"<text>:1: construct not supported"):
      sysml_lite.parse_text("package X { state def S; }")

  def test_refuses_unbalanced(self):
    with self.assertRaises(sysml_lite.ModelError):
      sysml_lite.parse_text("package X { part def A {")

  def test_model_loads(self):
    m = sysml_lite.load()
    self.assertEqual(len(m.mechanisms), 43)
    self.assertEqual(m.find("P-SW").short, "E-03")
    e = m.find("panda.safety.toyota.eps_fault")
    self.assertEqual(e.integrity(), "BDagger")
    self.assertEqual(e.meta["Unit"]["id"], "U-SAF-TOY")
    self.assertEqual(m.elements["context.driver"].scope(), "outside")
    self.assertIn("context.ldsda.deviceHardware.safetyMcu", m.mechanisms["SM-15"].performers)


class Checks(unittest.TestCase):
  def test_integrity_of_text(self):
    f = check_model.integrity_of_text
    self.assertEqual(f("B‡"), "BDagger")
    self.assertEqual(f("B (PCS restore), B‡ (blocking)"), "BDagger")
    self.assertEqual(f("B (feeds heartbeat timeout choice, TSR-510)"), "B")
    self.assertEqual(f("QM (B-sup); FFI interface"), "QMBsup")
    self.assertEqual(f("Mixed: siren B, rest QM"), "B")
    self.assertEqual(f("QM (SOTIF/PAS 8800)"), "QM")
    self.assertEqual(f("Interference source"), "QM")

  def test_expand_tsr(self):
    self.assertEqual(check_model.expand_tsr("105–107, 203"), ["TSR-105", "TSR-106", "TSR-107", "TSR-203"])
    self.assertEqual(check_model.expand_tsr("307(a), 309"), ["TSR-307(a)", "TSR-309"])

  def test_all_checks_pass(self):
    self.assertEqual(check_model.main([]), 0)

  def test_ffi_rule_catches_undeclared_crossing(self):
    m = sysml_lite.load()
    spi = next(c for c in m.connections if c.interface_id == "IF-04")
    spi.meta.pop("FfiClaim")
    rep = check_model.Report()
    check_model.check_integrity_rules(m, rep)
    self.assertTrue(any("crosses the integrity boundary" in e for e in rep.errors), rep.errors)

  def test_allocation_resolution(self):
    m = sysml_lite.load()
    units = {"U-SAF-TOY": ["panda.safety.toyota"]}
    _, res, unres = check_model.resolve_allocation(m, "`panda.safety.lateral` (U-SAF-LAT), U-SAF-TOY", units)
    self.assertEqual(unres, ["U-SAF-LAT"])
    self.assertEqual({t for t, _ in res}, {"panda.safety.lateral", "U-SAF-TOY"})
    _, res, unres = check_model.resolve_allocation(m, "Firmware + IWDG", units)
    self.assertEqual((res, unres), ([], []))


class Rendering(unittest.TestCase):
  def test_orthogonal_inserts_corners(self):
    pts = render_views.orthogonal([(0, 0), (10, 5), (20, 5)], True)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:], strict=False):
      self.assertTrue(x0 == x1 or y0 == y1, pts)

  def test_text_width_uses_metrics(self):
    self.assertGreater(svgkit.text_w("WWW", 12), svgkit.text_w("iii", 12))
    self.assertEqual(svgkit.clip("short", 500, 12), "short")
    self.assertTrue(svgkit.clip("a long label that will not fit", 60, 12).endswith("…"))

  def test_figures_deterministic_and_current(self):
    m = sysml_lite.load()
    a, b = render_views.render_all(m), render_views.render_all(m)
    self.assertEqual(a, b)
    self.assertEqual(render_views.main(["--check"]), 0)
    self.assertEqual(explorer.main(["--check"]), 0)

  def test_every_view_is_drawn(self):
    m = sysml_lite.load()
    files = render_views.render_all(m)
    self.assertEqual(len(files), len(m.views))
    v03 = files["fig-sysml-v03-system-interconnection.svg"]
    for iid in ("IF-01", "IF-03", "IF-04", "IF-04b", "IF-07", "IF-08", "IF-09", "IF-10"):
      self.assertIn(iid, v03)

  def test_layout_must_name_model_elements(self):
    m = sysml_lite.load()
    cv = render_views.Canvas(m, "V-03", {"node": [{"el": "noSuchElement", "box": [0, 0, 10, 10]}]})
    with self.assertRaisesRegex(sysml_lite.ModelError, "not an element of the model"):
      cv.place()


if __name__ == "__main__":
  unittest.main()
