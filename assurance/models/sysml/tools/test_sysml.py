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
import gen_tables
import render_se
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
      sysml_lite.parse_text("package X { flow def S; }")

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
    svgs = [f for f in files if f.endswith(".svg")]
    for vid in m.views:  # every view drawn; V-06 once per function or function group
      self.assertTrue(any(f.startswith(f"fig-sysml-{vid.lower().replace('-', '')}-") for f in svgs), vid)
    self.assertEqual(len([f for f in svgs if f.startswith("fig-sysml-v06-")]), 8)
    layout = render_views.tomllib.loads(render_views.LAYOUT.read_text(encoding="utf-8"))["views"]
    per_view = sum(len(s.get("functions") or s.get("blocks") or [1]) for s in layout.values())
    self.assertEqual(len(svgs), per_view)
    v03 = files["fig-sysml-v03-system-interconnection.svg"]
    for iid in ("IF-01", "IF-03", "IF-04", "IF-04b", "IF-07", "IF-08", "IF-09", "IF-10"):
      self.assertIn(iid, v03)

  def test_n2_rolls_up_to_components(self):
    m = sysml_lite.load()
    order, cells = render_se.n2_cells(m)
    shorts = [e.short for e in order]
    self.assertEqual(shorts[:4], ["E-01", "E-03", "E-04", "E-05"])
    e01, e03 = m.find("E-01").path, m.find("E-03").path
    self.assertIn("IF-04", {lab for lab, _ in cells[(e01, e03)]})
    # a bus attachment reads both ways
    for (a, b), entries in cells.items():
      if ("CAN", "bus") in entries:
        self.assertIn(("CAN", "bus"), cells[(b, a)])

  def test_vcrm_methods_and_levels(self):
    req = lambda v: sysml_lite.Requirement.__new__(sysml_lite.Requirement)
    cases = {"UT, HIL": ["T-SIL", "T-HIL"], "R-SW, BA": ["R"], "HIL (option-byte read), PR": ["T-HIL", "R"],
             "BA, R, FZ": ["R", "PT"], "maintenance log": ["Rec"], "T-SIL (replay), T-VEH": ["T-SIL", "T-VEH"]}
    for text, want in cases.items():
      r = req(text)
      r.values = {"verifMethod": text}
      self.assertEqual(render_se.methods_of(r), want, text)
    self.assertEqual(render_se.level_of("VS-SQ-12"), "SYS.5")
    self.assertEqual(render_se.level_of("VS-FI-03"), "SYS.4")
    self.assertEqual(render_se.level_of("VS-VAL-01"), "VAL.1")
    self.assertEqual(render_se.level_of("SWV-07"), "below")
    m = sysml_lite.load()
    page = render_se.vcrm_page(m)
    rows = [ln for ln in page.splitlines() if ln.startswith(("| SYS-", "| TSR-", "| CSR-"))]
    self.assertEqual(len(rows), len(render_se.vcrm_rows(m)))
    self.assertNotIn("Rec", "".join(ln for ln in rows if ln.startswith("| CSR-")))

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


class Extension(unittest.TestCase):
  """Functions, security zones, integration steps and system modes (V-10 to V-13)."""

  @classmethod
  def setUpClass(cls):
    cls.m = sysml_lite.load()

  def test_every_function_step_runs_somewhere(self):
    self.assertEqual(sorted(self.m.functions), [f"F-0{i}" for i in range(1, 10)])
    lat = self.m.functions["F-01"]
    self.assertEqual([s.stage for s in lat.steps][-2:], ["envelope", "act"])
    env = next(s for s in lat.steps if s.stage == "envelope")
    self.assertEqual([self.m.elements[p].short for p in env.performers], ["E-03a"])
    for f in self.m.functions.values():
      for st in f.steps:
        self.assertTrue(st.performers, st.short)

  def test_function_steps_are_not_mechanisms(self):
    self.assertNotIn("F-01", self.m.mechanisms)
    self.assertEqual(len(self.m.mechanisms), 43)

  def test_zones_inherit_and_boundaries_join_zones(self):
    self.assertEqual(self.m.find("host.pandad").zone(), "Z2")
    self.assertEqual(self.m.find("host.hmi").zone(), "Z3")
    self.assertEqual(self.m.find("E-03a").zone(), "Z1")
    self.assertEqual(sysml_lite._as_list(self.m.boundaries["TB-1"].values["zones"]), ["Z2", "Z1"])
    import render_arch
    self.assertEqual(render_arch.csr_count("CSR-011…CSR-016, CSR-021…CSR-024, CSR-061"), 11)

  def test_integration_steps_and_cases(self):
    self.assertEqual(sorted(self.m.integration), ["I-1", "I-2", "I-3", "I-4"])
    vs = self.m.verifications["VS-SI-03"]
    self.assertEqual(sysml_lite._as_list(vs.values.get("steps")), ["I-1", "I-3"])

  def test_system_modes(self):
    sm = self.m.state_machines["SM-SYS"]
    self.assertEqual(sm.initial, "off")
    self.assertEqual(sm.states["engaged"].initial, "engaged.enabled")
    names = {t.name: t for t in sm.transitions}
    self.assertEqual((names["softDisable"].source, names["softDisable"].target),
                     ("engaged.enabled", "engaged.softDisabling"))
    self.assertEqual(str(names["softDisable"].meta["Enforcement"]["kind"]).split("::")[-1], "gap16")

  def test_reader_parses_states_and_transitions(self):
    decls = sysml_lite.parse_text("""package P {
        state def <'S'> M { entry; then a; state a; state b { entry; then c; state c; } transition go first a then b.c; }
    }""")
    sm = sysml_lite._state_machine(decls[0].members[0])
    self.assertEqual((sm.initial, sm.states["b"].initial), ("a", "b.c"))
    self.assertEqual([(t.source, t.target) for t in sm.transitions], [("a", "b.c")])
    bad = sysml_lite.parse_text("package P { state def M { entry; then a; state a; transition x first a then z; } }")
    with self.assertRaises(sysml_lite.ModelError):
      sysml_lite._state_machine(bad[0].members[0])


class Needs(unittest.TestCase):
  """Stakeholder needs and use cases of WP-S-01 §1.2-§1.4 (V-14, V-15)."""

  @classmethod
  def setUpClass(cls):
    cls.m = sysml_lite.load()

  def test_reader_parses_use_cases(self):
    decls = sysml_lite.parse_text("""package P {
        requirement def N { subject s : S; }
        requirement <'SN-01'> n : N { subject :>> s; stakeholder driver : Driver; }
        use case def U { subject s : S; }
        use case <'UC-01'> u : U { subject :>> s; actor driver : Driver; objective { doc /* goal */ require n; } perform f; }
    }""")
    uc = decls[0].member("u")
    self.assertEqual(uc.kind, "use case")
    self.assertEqual([(x.kind, x.name, x.type) for x in uc.members if x.kind == "actor"], [("actor", "driver", "Driver")])
    obj = next(x for x in uc.members if x.kind == "objective")
    self.assertEqual((obj.doc, [x.target for x in obj.members]), ("goal", ["n"]))
    self.assertEqual(decls[0].member("n").members[0].target, "s")

  def test_needs_trace_to_requirements_and_use_cases(self):
    n = self.m.requirements["SN-01"]
    self.assertEqual((n.definition, n.stakeholders), ("StakeholderNeed", [("driver", "Driver")]))
    self.assertIn("SN-01", self.m.requirements["SYS-001"].derived_from)
    self.assertIn("SN-04", self.m.requirements["SG-05"].derived_from)
    uc = self.m.use_cases["UC-01"]
    self.assertEqual((uc.needs, uc.functions), (["SN-01"], ["F-01", "F-05", "F-08"]))
    self.assertEqual(sorted(self.m.use_cases), [f"UC-{i:02d}" for i in range(1, 12)])

  def test_checks_catch_a_need_without_a_use_case_and_an_unused_function(self):
    rep = check_model.Report()
    check_model.check_needs(self.m, rep)
    self.assertEqual(rep.errors, [])
    saved = self.m.use_cases.pop("UC-08")
    try:
      rep = check_model.Report()
      check_model.check_needs(self.m, rep)
      text = "\n".join(rep.errors)
      self.assertIn("SN-07 is served by no use case", text)
      self.assertIn("F-06 is performed by no use case", text)
    finally:
      self.m.use_cases["UC-08"] = saved

  def test_every_system_requirement_and_goal_refines_a_need(self):
    needs = {s for s, r in self.m.requirements.items() if r.definition == "StakeholderNeed"}
    for r in self.m.requirements.values():
      if r.short.split("-")[0] in ("SYS", "SG"):
        self.assertTrue(needs & set(r.derived_from), r.short)


class Behaviour(unittest.TestCase):
  """State-machine records and the start-up sequence (V-16, V-17)."""

  @classmethod
  def setUpClass(cls):
    cls.m = sysml_lite.load()

  def test_reader_parses_messages_in_order(self):
    decls = sysml_lite.parse_text("""package P {
        occurrence def <'Q'> Q { part a : L; part b : L; message <'S-02'> s2 from b to a; message <'S-01'> s1 from a to b;
            first s1 then s2; }
    }""")
    q = sysml_lite._sequence(decls[0].members[0])
    self.assertEqual([(x.short, x.source, x.target) for x in q.messages], [("S-01", "a", "b"), ("S-02", "b", "a")])
    bad = sysml_lite.parse_text("package P { occurrence def <'Q'> Q { part a : L; message s1 from a to z; } }")
    with self.assertRaises(sysml_lite.ModelError):
      sysml_lite._sequence(bad[0].members[0])

  def test_record_transitions_expand(self):
    import gen_behaviour
    rec = {"machine": "SM-X", "states": ["A", "B", "C"]}
    self.assertEqual(gen_behaviour.expand(rec, {"id": "1", "from": "any", "to": "A"}), [("A", "A"), ("B", "A"), ("C", "A")])
    self.assertEqual(gen_behaviour.expand(rec, {"id": "2", "from": "A, B", "to": "same"}), [("A", "A"), ("B", "B")])
    self.assertEqual(gen_behaviour.expand(rec, {"id": "3", "from": "C", "to": "m", "guard": "m in {A, B}"}), [("C", "A"), ("C", "B")])
    self.assertEqual(len(gen_behaviour.expand(rec, {"id": "4", "from": "A", "to": "m", "guard": "registry"})), 3)
    with self.assertRaises(gen_behaviour.BehaviourError):
      gen_behaviour.expand(rec, {"id": "5", "from": "D", "to": "A"})

  def test_records_and_sequence_in_the_model(self):
    auth = self.m.state_machines["SM-TOY-AUTH"]
    self.assertEqual((auth.initial, sorted(auth.states)), ("NOT_ALLOWED", ["ALLOWED", "ENGAGE_PENDING", "NOT_ALLOWED"]))
    self.assertIn("T1a", check_model.record_ids(auth))
    self.assertTrue(check_model.known_record(self.m, "SM-SELFDRIVED D3", "transition"))
    self.assertFalse(check_model.known_record(self.m, "SM-SYS engage", "transition"))  # SM-SYS is not a record
    q = self.m.sequences["SEQ-START"]
    self.assertEqual((q.messages[0].short, q.messages[-1].short), ("ST-01", "ST-21"))
    self.assertEqual(dict(q.lifelines)["safety_mcu"], "E-03")

  def test_checks_catch_a_wrong_record_and_state(self):
    rep = check_model.Report()
    check_model.check_behaviour(self.m, rep)
    self.assertEqual(rep.errors, [])
    msg = self.m.sequences["SEQ-START"].messages[13]
    saved = dict(msg.meta["SequenceStep"])
    try:
      msg.meta["SequenceStep"].update(records="SM-TOY-AUTH T99", stateAfter="Safety MCU: NOWHERE")
      rep = check_model.Report()
      check_model.check_behaviour(self.m, rep)
      text = "\n".join(rep.errors)
      self.assertIn("'SM-TOY-AUTH T99' is not a transition", text)
      self.assertIn("state after 'NOWHERE'", text)
    finally:
      msg.meta["SequenceStep"] = saved

  def test_lifecycle_carries_every_production_requirement_once(self):
    a = self.m.activities["InstalledItemLifecycle"]
    self.assertEqual([p.short for p in a.phases], ["3.1", "3.2", "3.3", "3.4", "3.5"])
    self.assertIn(("start", "installationAndProvisioning"), a.flows)
    carried = sorted(str(st.values["tsr"]) for v in a.steps.values() for st in v)
    self.assertEqual(carried, sorted(r for r in self.m.requirements if r.startswith("TSR-8")))
    rep = check_model.Report()
    check_model.check_lifecycle(self.m, rep)
    self.assertEqual(rep.errors, [])
    saved = list(a.flows)
    try:
      a.flows[:] = [f for f in a.flows if f[1] != "softwareUpdates"]
      rep = check_model.Report()
      check_model.check_lifecycle(self.m, rep)
      self.assertIn("phase softwareUpdates is not reached from start", "\n".join(rep.errors))
    finally:
      a.flows[:] = saved


class TimingHsi(unittest.TestCase):
  """Timing budgets of WP-S-04 §3.7, HSI signals of WP-S-05 §11 and HSI responsibilities of §11.4 (V-18, V-19, V-20)."""

  @classmethod
  def setUpClass(cls):
    cls.m = sysml_lite.load()

  def test_cells_that_are_times(self):
    import gen_timing_hsi as g
    self.assertEqual(g.seconds("≤ 0.2 s (TSR-401)"), 0.2)
    self.assertEqual(g.seconds("≤ 30 ms"), 0.03)
    self.assertIsNone(g.seconds("≤ 10 ms (+ TSR-109)"))
    self.assertIsNone(g.seconds("≤ 40 ms + t_ovr"))
    self.assertIsNone(g.seconds("per frame"))
    self.assertEqual(g.goals_of("SG-01 / SG-03 unintended engagement (System FMEA SG-008, §3.8.3)"), ["SG-01", "SG-03"])
    self.assertEqual(g.goals_of("SG-02/06 loss without warning"), ["SG-02", "SG-06"])
    self.assertEqual(g.expand_numbers("101…104, 108, 109", "TSR"), ["TSR-101", "TSR-102", "TSR-103", "TSR-104", "TSR-108", "TSR-109"])
    self.assertEqual(g.tests_of("VS-HW-01…04, VS-SI-18"), ["VS-HW-01", "VS-HW-02", "VS-HW-03", "VS-HW-04", "VS-SI-18"])
    self.assertEqual(g.owners_of("SW: host `controlsd`/`card` (E-01)"), ["E-01", "host.controlsd", "host.card"])

  def test_budget_arithmetic_is_checked(self):
    rep = check_model.Report()
    check_model.check_timing_hsi(self.m, rep)
    self.assertEqual(rep.errors, [])
    b = self.m.budgets["SG-01 RX loss/corruption"]
    saved = dict(b.values)
    try:
      b.values["frti" + "Seconds"] = 0.4
      rep = check_model.Report()
      check_model.check_timing_hsi(self.m, rep)
      text = "\n".join(rep.errors)
      self.assertIn("exceeds the FTTI 0.5 s", text)
      self.assertIn("is not FDTI + FRTI", text)
    finally:
      b.values = saved

  def test_signals_and_protection(self):
    import render_arch
    self.assertEqual(len(self.m.signals), 29)
    self.assertEqual(sysml_lite._as_list(self.m.signals["S-25"].values["owners"]), ["host.pandad"])
    self.assertTrue(render_arch.protection(self.m, "S-02", "validity"))       # "as S-01": the EPS checks the counter
    self.assertFalse(render_arch.protection(self.m, "S-08", "validity"))      # "as S-07": none
    self.assertFalse(render_arch.protection(self.m, "S-27", "validity"))      # "required start-up test"
    self.assertFalse(render_arch.protection(self.m, "S-11", "integrity"))     # "none (..., checksum ignored)"

  def test_responsibilities_cover_every_interface(self):
    import gen_timing_hsi as g
    self.assertEqual(sorted(self.m.responsibilities), sorted(g.interfaces()))
    r = self.m.responsibilities["HSI-05"].values
    self.assertEqual(sysml_lite._as_list(r["hwOwners"]), ["E-04a", "E-05"])
    self.assertEqual(sysml_lite._as_list(r["swOwners"]), ["E-03b"])
    self.assertEqual(sysml_lite._as_list(r["tsr"]), ["TSR-506", "TSR-706"])   # "TSR-506, 706": the bare number too
    self.assertEqual(sysml_lite._as_list(self.m.responsibilities["HSI-04"].values["tsr"])[:6],
                     [f"TSR-40{n}" for n in range(1, 7)])                        # "TSR-401…406" expanded
    self.assertEqual(self.m.responsibilities["HSI-14"].values["status"], "missing")

  def test_responsibility_owner_on_the_wrong_side_is_reported(self):
    r = self.m.responsibilities["HSI-09"]
    saved = dict(r.values)
    try:
      r.values["hwOwners"] = ["E-03b"]          # firmware named as the hardware owner
      r.values["swOwners"] = ["E-99"]           # not an element
      r.values["status"] = "done"
      rep = check_model.Report()
      check_model.check_timing_hsi(self.m, rep)
      text = "\n".join(rep.errors)
      self.assertIn("HSI-09: hardware owner E-03b is not hardware", text)
      self.assertIn("HSI-09: software owner 'E-99' is not an element of the model", text)
      self.assertIn("HSI-09: status 'done'", text)
    finally:
      r.values = saved

  def test_interface_without_responsibility_is_reported(self):
    saved = self.m.responsibilities.pop("HSI-13")
    try:
      rep = check_model.Report()
      check_model.check_timing_hsi(self.m, rep)
      self.assertIn("HSI-13 has no hardware/software responsibility in WP-S-05 §11.4", "\n".join(rep.errors))
    finally:
      self.m.responsibilities["HSI-13"] = saved

  def test_hardware_parts_of_each_interface(self):
    v = self.m.responsibilities
    self.assertEqual(sysml_lite._as_list(v["HSI-04"].values["hwParts"]), ["fdcanPeripherals", "gpio"])  # FDCAN first
    self.assertEqual(sysml_lite._as_list(v["HSI-13"].values["hwParts"]), ["adc", "supply"])  # supply from the name
    r = v["HSI-09"]
    saved = dict(r.values)
    try:
      r.values["hwParts"] = ["watchdogTimer"]          # not a part of E-04a; iwdg1 is then behind no interface
      rep = check_model.Report()
      check_model.check_timing_hsi(self.m, rep)
      text = "\n".join(rep.errors)
      self.assertIn("HSI-09 uses 'watchdogTimer', which is not a part of the safety MCU hardware E-04a", text)
      self.assertIn("E-04a part iwdg1 is behind no hardware-software interface", text)
    finally:
      r.values = saved


class Tables(unittest.TestCase):
  def test_tsr_cell(self):
    self.assertEqual(gen_tables.tsr_cell(["TSR-1xx", "TSR-2xx", "TSR-705"]), "1xx, 2xx, 705")
    self.assertEqual(gen_tables.tsr_cell(["TSR-406", "TSR-401", "TSR-402", "TSR-403", "TSR-404", "TSR-405", "TSR-3xx"]),
                     "3xx, 401–406")
    self.assertEqual(gen_tables.tsr_cell(["TSR-101", "TSR-102"]), "101, 102")
    self.assertEqual(gen_tables.tsr_cell(["TSR-307(a)", "TSR-309"]), "307(a), 309")
    self.assertEqual(gen_tables.tsr_cell([]), "—")

  def test_tables_match_the_work_products(self):
    self.assertEqual(gen_tables.main([]), 0)

  def test_a_changed_cell_is_reported(self):
    m = sysml_lite.load()
    want = gen_tables.mechanisms_table(m)
    have = [ln.replace("| SM-02 | Torque rate", "| SM-02 | Torque speed") for ln in want]
    d = gen_tables.differences(have, want)
    self.assertEqual(len(d), 1)
    self.assertIn("row SM-02, Mechanism", d[0])
    self.assertIn("rows in a different order", gen_tables.differences(want[:2] + want[3:4] + want[2:3] + want[4:], want))

  def test_model_as_record_writes_the_same_tables(self):
    import shutil
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
      tmp = Path(tmp)
      saved = gen_tables.TABLES, gen_tables.RECORD
      try:
        copies = {}
        for wp, _h, _r in saved[0]:
          copies.setdefault(wp, shutil.copy(wp, tmp / wp.name))
        gen_tables.TABLES = [(Path(copies[wp]), h, r) for wp, h, r in saved[0]]
        gen_tables.RECORD = tmp / "record.toml"
        gen_tables.RECORD.write_text('record = "model"\n')
        self.assertEqual(gen_tables.main([]), 1)  # no markers yet
        self.assertEqual(gen_tables.main(["--write"]), 0)
        self.assertEqual(gen_tables.main([]), 0)
        for wp, copy in copies.items():
          before, after = wp.read_text(encoding="utf-8"), Path(copy).read_text(encoding="utf-8")
          self.assertEqual(after.replace(gen_tables.MARKER + "\n\n", ""), before)
        gen_tables.RECORD.write_text('record = "work-products"\n')
        self.assertEqual(gen_tables.main(["--write"]), 1)
      finally:
        gen_tables.TABLES, gen_tables.RECORD = saved


if __name__ == "__main__":
  unittest.main()
