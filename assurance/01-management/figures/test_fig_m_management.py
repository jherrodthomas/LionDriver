#!/usr/bin/env python3
"""Tests for fig_m_management.py: source texts present, committed SVGs current, valid, and drawn from the tables."""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_m_management as fm

NS = "{http://www.w3.org/2000/svg}"


class TestManagementFigures(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.outputs = fm.build()
    cls.reg = fm.load_register()
    cls.risks = fm.load_risks()
    cls.profile = fm.load_profile()

  def test_source_texts_present(self):
    self.assertEqual(fm.missing_sources(), [])

  def test_committed_outputs_current(self):
    for name, content in self.outputs.items():
      path = fm.HERE / name
      self.assertTrue(path.exists(), name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{name} is stale; run fig_m_management.py")

  def test_deterministic(self):
    self.assertEqual(fm.build(), self.outputs)

  def test_svgs_valid_with_role_title_desc(self):
    for name, content in self.outputs.items():
      root = ET.fromstring(content)
      self.assertEqual(root.get("role"), "img", name)
      self.assertEqual(root.get("width"), "1280", name)
      self.assertTrue(root.find(f"{NS}title").text.startswith("Figure "), name)
      self.assertTrue(root.find(f"{NS}desc").text, name)

  def test_m00_every_register_row_drawn(self):
    md = fm.WP_M_00.read_text(encoding="utf-8")
    rows = re.findall(r"^\| \[(WP-[A-Z]-\d+)\]\(.*\| (\S+) \|$", md, re.M)
    self.assertEqual([w.wid for w in self.reg.products], [r[0] for r in rows])
    self.assertEqual(Counter(w.status for w in self.reg.products), Counter(r[1] for r in rows))
    svg = self.outputs["fig-m00-3-1-wp-status.svg"]
    for w in self.reg.products:
      self.assertIn(f">{w.wid}<", svg)
    totals = Counter(w.status for w in self.reg.products)
    self.assertIn(f"Draft {totals['D']}", svg)

  def test_m00_no_green_without_approved_status(self):
    statuses = {w.status for w in self.reg.products}
    if not statuses & {"A", "B"}:
      self.assertNotIn(fm.GREEN, self.outputs["fig-m00-3-1-wp-status.svg"])

  def test_m07_exposure_and_bands_match_register(self):
    risks = self.risks.risks
    self.assertEqual(len(risks), len({r.rid for r in risks}))
    for r in risks:
      self.assertEqual(r.e, r.p * r.i, r.rid)
    by_band = {b: sorted(r.rid for r in risks if not r.closed and fm.band(r.e) == b) for b in ("High", "Medium", "Low")}
    for b, ids in by_band.items():
      self.assertEqual(sorted(self.risks.summary[b]), ids, f"§4.1 {b}")
    self.assertEqual(sorted(self.risks.summary["Closed"]), sorted(r.rid for r in risks if r.closed))
    svg = self.outputs["fig-m07-4-1-risk-heat-map.svg"]
    for r in risks:
      self.assertIn(f">{r.rid}<", svg)

  def test_m13_ratings_and_cl_consistent(self):
    procs = self.profile.processes
    md = fm.WP_M_13.read_text(encoding="utf-8")
    s4 = fm.section(md, "## 4. Capability level 1")
    self.assertEqual(len(procs), len(re.findall(r"^\| [A-Z]{3}\.\d+ ", s4, re.M)))
    split = [p.code for p in procs if len(p.ratings) > 1]
    self.assertIn("SWE.3", split)
    for p in procs:
      # §4 CL column agrees with the §2 rule applied to the PA 1.1 rating(s) (PA 2.x is N, so at most CL1)
      if p.cl:
        derived = " / ".join("1" if r in "LF" else "0" for r, _ in p.ratings)
        self.assertEqual(re.sub(r"\s*\([^)]*\)", "", p.cl), derived, p.code)
      self.assertIn(p.target, fm.CL_NEEDS, p.code)   # every group has a target since DQ-019 (group C at CL1)
    svg = self.outputs["fig-m13-6-1-capability-profile.svg"]
    self.assertEqual(svg.count(">safety code<"), len(split))

  # ---------------------------------------------------------------- WP-M-03 planning figures (fig_m_plans.py)

  def test_m03_roadmap_draws_every_phase_and_backlog_item(self):
    pl = fm.fig_m_plans.load_plan()
    svg = self.outputs["fig-m03-5-1-gate-roadmap.svg"]
    md = fm.fig_m_plans.WP_M_03.read_text(encoding="utf-8")
    ids = re.findall(r"^\| (B-\d+) \|", md, re.M)
    self.assertEqual([b.bid for b in pl.backlog], ids)
    for b in pl.backlog:
      self.assertIn(f">{b.bid}<", svg)
    self.assertEqual([p.pid for p in pl.phases], [f"P{i}" for i in range(len(pl.phases))])
    for p in pl.phases:
      self.assertIn(f">{p.pid}<", svg)
      self.assertIn(f">{p.gate}<", svg)
    done = sum(b.status == "done" for b in pl.backlog)
    self.assertIn(f">Done ({done})<", svg)

  def test_m03_no_green_gate_without_a_pass_record(self):
    pl = fm.fig_m_plans.load_plan()
    if not pl.passed:
      self.assertIn("no gate passed yet", self.outputs["fig-m03-5-1-gate-roadmap.svg"])
      self.assertNotIn(f'stroke="{fm.GREEN}" stroke-width="1.5"', self.outputs["fig-m03-5-1-gate-roadmap.svg"])

  def test_m03_schedule_sums_match_section_5(self):
    pl = fm.fig_m_plans.load_plan()
    lo = sum(p.months[0] for p in pl.phases if p.months) * pl.stretch
    hi = sum(p.months[1] for p in pl.phases if p.months) * pl.stretch
    if pl.start:
      want = f"between {fm.fig_m_plans.cal_month(pl, lo)} and {fm.fig_m_plans.cal_month(pl, hi)}"
    else:
      want = f"between month {fm.fmt(lo)} and month {fm.fmt(hi)}"
    self.assertIn(want, self.outputs["fig-m03-5-2-schedule.svg"])

  def test_m03_long_lead_items_resolve(self):
    pl = fm.fig_m_plans.load_plan()
    self.assertEqual(len(pl.long_lead), len(fm.fig_m_plans.LONG_LEAD))
    phases = {p.pid for p in pl.phases}
    for item, start, status, needed in pl.long_lead:
      self.assertIn(start, phases, item)
      self.assertIn(needed, phases, item)
      self.assertTrue(status, item)

  def test_decision_status_words(self):
    w = fm.fig_m_plans.decision_word
    self.assertEqual(w("**Done** 2026-10-10: forked"), "done")
    self.assertEqual(w("**Mostly done** 2026-10-10"), "mostly done")
    self.assertEqual(w("answered 2026-10-14: defer"), "answered")
    self.assertEqual(w("Open (de facto in use)"), "open")
    self.assertEqual(fm.fig_m_plans.decision_mismatches(), [])

  def test_pinned_figures_current(self):
    self.assertEqual(fm.fig_m_plans.pin_problems(), [])

  # ---------------------------------------------------------------- WP-M-02 safety plan figures (fig_m_safety.py)

  def test_m02_raci_every_cell_drawn(self):
    md = fm.fig_m_safety.doc()
    roles, head, rows = fm.fig_m_safety.load_roles(md)
    self.assertEqual(sorted(roles), sorted(head[1:]))
    svg = self.outputs["fig-m02-3-1-raci.svg"]
    for r in rows:
      self.assertEqual(len(r), len(head))
    self.assertIn(f"of {len(rows)} activities", svg)

  def test_m02_at_risk_rows_and_no_unearned_credit(self):
    md = fm.fig_m_safety.doc()
    items = fm.fig_m_safety.load_at_risk(md)
    _, rows = fm.table(fm.section(md, "### 4.1 Early implementation (at-risk work)"), "Change")
    self.assertEqual(len(items), len(rows))
    svg = self.outputs["fig-m02-4-2-at-risk.svg"]
    for it in items:
      self.assertTrue(it.reqs, it.change)
      if "not reviewed independently" in it.status:
        self.assertFalse(it.reviewed, it.change)
    earned = sum(it.approved and it.reviewed and it.hil for it in items)
    self.assertIn(f"{earned} of {len(items)} changes have earned credit", svg)
    if not earned:
      self.assertNotIn(">earned<", svg)

  def test_m02_lifecycle_and_anomaly_steps(self):
    md = fm.fig_m_safety.doc()
    _, phases = fm.table(fm.section(md, "## 4. Lifecycle activities per phase"), "Phase")
    svg = self.outputs["fig-m02-4-1-lifecycle.svg"]
    for r in phases:
      self.assertIn(f">{fm.plain(r[0]).split()[0]}<", svg)
    _, steps = fm.table(fm.section(md, "## 9. Safety anomaly handling"), "Step")
    svg = self.outputs["fig-m02-9-1-anomaly.svg"]
    for r in steps:
      if fm.plain(r[0]) != "Gate rule":
        self.assertIn(fm.plain(r[0]), svg)

  # ---------------------------------------------------------------- WP-M-03 WBS and effort

  def test_m03_wbs_and_effort(self):
    md = fm.fig_m_plans.WP_M_03.read_text(encoding="utf-8")
    _, rows = fm.table(fm.section(md, "## 3. Work breakdown structure"), "WBS")
    svg = self.outputs["fig-m03-3-1-wbs.svg"]
    for r in rows:
      self.assertIn(fm.plain(r[0]), svg)
    _, est = fm.table(fm.section(md, "### 4.2 Estimate"), "Phase")
    lo = sum(int(fm.plain(r[1])) for r in est if re.match(r"P\d ", fm.plain(r[0])) and fm.plain(r[1]).isdigit())
    hi = sum(int(fm.plain(r[2])) for r in est if re.match(r"P\d ", fm.plain(r[0])) and fm.plain(r[2]).isdigit())
    self.assertIn(f"Total P0–P5: {lo}–{hi} pw summed", self.outputs["fig-m03-4-1-effort.svg"])


if __name__ == "__main__":
  unittest.main()
