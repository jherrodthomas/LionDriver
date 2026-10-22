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
    enum def Integrity { enum QM; enum BDagger; enum C; }
    metadata def Safety { attribute integrity : Integrity; attribute label : String; }
    port def P;
    interface def Link { end port source : P; end port target : P; }
    part def A { port p : P; }
    part def Item {
        doc /* The item. */
        part <'E-01'> a : A { @Safety { integrity = Integrity::QM; label = "QM"; } }
        part <'E-03'> b : A { @Safety { integrity = Integrity::C; label = "C"; } }
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
    self.assertEqual(e.integrity(), "C")
    self.assertEqual(e.meta["Unit"]["id"], "U-SAF-TOY")
    self.assertEqual(m.elements["context.driver"].scope(), "outside")
    self.assertIn("context.ldsda.deviceHardware.safetyMcu", m.mechanisms["SM-15"].performers)


class Checks(unittest.TestCase):
  def test_integrity_of_text(self):
    f = check_model.integrity_of_text
    self.assertEqual(f("B‡"), "BDagger")
    self.assertEqual(f("B (PCS restore), B‡ (blocking)"), "BDagger")
    self.assertEqual(f("C"), "C")
    self.assertEqual(f("ASIL C"), "C")
    self.assertEqual(f("B (PCS restore), C (blocking)"), "C")
    self.assertEqual(f("C (blocking) / B (PCS restore)"), "C")
    self.assertEqual(f("C/B"), "C")
    self.assertEqual(f("C + CS"), "C")
    self.assertEqual(f("C (B‡ before DQ-341)"), "C")
    self.assertEqual(f("B‡ (FFI, CS)"), "BDagger")
    self.assertEqual(f("B(C)"), "B")
    self.assertEqual(f("QM (C-sup)"), "QM")
    self.assertEqual(f("B (feeds heartbeat timeout choice, TSR-510)"), "B")
    self.assertEqual(f("QM (B-sup); FFI interface"), "QMBsup")
    self.assertEqual(f("Mixed: siren B, rest QM"), "B")
    self.assertEqual(f("QM (SOTIF/PAS 8800)"), "QM")
    self.assertEqual(f("Interference source"), "QM")

  def test_integrity_rank_and_asil(self):
    rank = check_model.INTEGRITY_RANK
    self.assertGreater(rank["C"], rank["BDagger"])
    self.assertGreater(rank["BDagger"], rank["B"])
    self.assertIn("C", check_model.ASIL)

  def test_envelope_is_asil_c(self):
    m = sysml_lite.load()
    for ident in ("E-03", "E-03a", "E-03b", "E-04a", "E-05"):
      self.assertEqual(m.find(ident).integrity(), "C", ident)
    self.assertEqual(m.find("E-04b").integrity(), "QM")
    self.assertEqual(m.find("panda.drivers.harness").integrity(), "C")
    self.assertEqual(m.find("panda.safety.longitudinal").integrity(), "B")
    self.assertFalse([e.path for e in m.elements.values() if e.meta.get("Safety", {}).get("integrity") == "Integrity::BDagger"])

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
    # a grouped part named in backticks resolves by its unique part name, as R2 resolves WP-S-01 §10.1
    _, res, unres = check_model.resolve_allocation(m, "`remoteAndLogging`, `hardwared`", units)
    self.assertEqual((sorted(t for t, _ in res), unres), (["hardwared", "remoteAndLogging"], []))


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

  def test_envelope_drawn_as_asil_c(self):
    m = sysml_lite.load()
    self.assertIs(render_views.style_of(m.find("E-03a")), svgkit.ENVELOPE)
    self.assertIs(render_views.style_of(m.find("panda.safety.longitudinal")), svgkit.ASIL_B)
    files = render_views.render_all(m)
    self.assertIn("ASIL C safety envelope", files["fig-sysml-v03-system-interconnection.svg"])
    self.assertIn("ASIL C", files["fig-sysml-v02-element-hierarchy.svg"])
    self.assertIn("by an ASIL C element", files["fig-sysml-v04-mechanism-allocation.svg"])
    for name, svg in files.items():
      self.assertNotIn("B‡ safety envelope", svg, name)

  def test_layout_must_name_model_elements(self):
    m = sysml_lite.load()
    cv = render_views.Canvas(m, "V-03", {"node": [{"el": "noSuchElement", "box": [0, 0, 10, 10]}]})
    with self.assertRaisesRegex(sysml_lite.ModelError, "not an element of the model"):
      cv.place()


REQ_TEXT = """
package R {
    private import ScalarValues::*;
    requirement def Req { attribute asil : String; }
    requirement <'SG-01'> sg_01 : Req { doc /* goal */ :>> asil = "C"; }
    requirement <'TSR-001'> tsr_001 : Req { doc /* derived */ :>> asil = "B"; }
    #derivation connection {
        end #original ::> sg_01;
        end #derive ::> tsr_001;
    }
    verification def Case;
    verification <'VS-SI-01'> vs_si_01 : Case {
        doc /* a case */
        objective { verify R::tsr_001; }
    }
}
"""


class Requirements(unittest.TestCase):
  def test_parses_requirements_derivation_and_verification(self):
    pkgs = {d.name: d for d in sysml_lite.parse_text(REQ_TEXT)}
    reqs, vers = sysml_lite._requirements(pkgs, {})
    self.assertEqual(reqs["TSR-001"].derived_from, ["SG-01"])
    self.assertEqual(reqs["TSR-001"].verified_by, ["VS-SI-01"])
    self.assertEqual(vers["VS-SI-01"].verifies, ["TSR-001"])
    self.assertEqual(reqs["SG-01"].values["asil"], "C")

  def test_satisfy_must_name_an_element(self):
    pkgs = {d.name: d for d in sysml_lite.parse_text(REQ_TEXT + "package S { satisfy R::tsr_001 by context.nothing; }")}
    with self.assertRaisesRegex(sysml_lite.ModelError, "not an element"):
      sysml_lite._requirements(pkgs, {})

  def test_verify_must_name_a_requirement(self):
    bad = REQ_TEXT.replace("verify R::tsr_001;", "verify R::tsr_999;")
    with self.assertRaisesRegex(sysml_lite.ModelError, "does not name a requirement"):
      sysml_lite._requirements({d.name: d for d in sysml_lite.parse_text(bad)}, {})

  def test_model_thread_tsr_407(self):
    m = sysml_lite.load()
    r = m.requirements["TSR-407"]
    self.assertEqual(r.derived_from, ["FSR-01.07"])
    self.assertIn("context.ldsda.safetyFirmware", r.satisfied_by)
    self.assertIn("VS-SI-05", r.verified_by)
    self.assertEqual(set(m.requirements["FSR-01.07"].derived_from), {"SG-01", "SG-02", "SG-03", "SG-04", "SG-06"})

  def test_every_system_requirement_is_satisfied_and_counted(self):
    m = sysml_lite.load()
    sys_reqs = [r for r in m.requirements.values() if r.short.startswith("SYS-")]
    self.assertEqual(len(sys_reqs), 39)
    self.assertTrue(all(r.satisfied_by for r in sys_reqs))
    self.assertEqual(m.requirements["SYS-102"].satisfied_by, ["context.ldsda.socSoftware.plannerd"])

  def test_ranges_are_expanded_but_notes_are_not_references(self):
    m = sysml_lite.load()
    self.assertIn("VS-SQ-16", m.requirements["SYS-007"].verified_by)
    self.assertNotIn("VS-SQ-16", m.requirements["SYS-005"].verified_by)

  def test_generated_files_and_reports_are_current(self):
    import gen_requirements
    self.assertEqual(gen_requirements.main(["--check"]), 0)
    self.assertEqual(check_model.main([]), 0)


if __name__ == "__main__":
  unittest.main()
