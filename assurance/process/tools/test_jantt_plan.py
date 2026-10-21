#!/usr/bin/env python3
"""Self-tests for jantt_plan.py: the committed plan is current and complete, and each rule rejects a broken copy."""
from __future__ import annotations

import copy
import datetime as dt
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jantt_plan as jp
import process_model as pm


class JanttPlanTest(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.plan = jp.build()
    cls.tasks = {t["id"]: t for t in cls.plan["tasks"]}
    cls.model = pm.load_model()

  def test_check_passes_and_out_writes_both_files(self):
    self.assertEqual(jp.main(["jantt_plan.py", "--check"]), 0)
    with tempfile.TemporaryDirectory() as d:
      self.assertEqual(jp.main(["jantt_plan.py", "--out", d]), 0)
      written = json.loads((Path(d) / "liondriver.jantt.json").read_text(encoding="utf-8"))
      self.assertEqual(len(written["tasks"]), len(self.plan["tasks"]))
      self.assertIn("Jantt.mount", (Path(d) / "index.html").read_text(encoding="utf-8"))

  def test_build_is_deterministic(self):
    self.assertEqual(jp.build(), self.plan)

  def test_plan_follows_the_jantt_rules(self):
    self.assertEqual(jp.problems(self.plan), [])

  def test_every_activity_review_and_gate_is_a_task(self):
    for item in list(self.model.activities) + list(self.model.reviews):
      self.assertIn(item, self.tasks)
    for gate in pm.GATES:
      self.assertTrue(self.tasks[f"GATE-{gate}"].get("milestone"))

  def test_every_unapplied_lead_decision_is_a_task(self):
    for d in jp.lead_decisions():
      self.assertEqual(self.tasks[d["id"]]["category"], "decision")

  def test_links_stay_inside_a_phase_or_go_through_its_gate(self):
    """An activity waits on activities of its own phase, the previous gate, or a decision; never directly on an earlier phase."""
    for tid, t in self.tasks.items():
      if not jp.ACTIVITY_ID.match(tid):
        continue
      for d in t.get("dependsOn") or []:
        dep = self.tasks[d]
        self.assertTrue(dep["phase"] == t["phase"] or dep["category"] in ("gate", "decision"), f"{tid} -> {d}")

  def test_gate_dates_match_wp_m03(self):
    """Each gate sits on the first day of the month WP-M-03 §5 gives as its earliest date."""
    md = (jp.ASSURANCE_DIR / "01-management" / "WP-M-03-project-plan.md").read_text(encoding="utf-8")
    for gate, month in re.findall(r"^\| (G[0-5]) \| (\w{3} \d{4}) \|", md, re.M):
      want = dt.datetime.strptime(month, "%b %Y").date().isoformat()
      self.assertEqual(self.tasks[f"GATE-{gate}"]["start"], want, gate)

  def test_progress_comes_from_the_register(self):
    ctx = pm.load_context()
    act = self.model.activities["CON-06"]
    status = jp.least_status(pm.outputs(act), ctx.register)
    self.assertEqual(self.tasks["CON-06"]["progress"], jp.STATUS[status][1])

  def broken(self, mutate) -> list[str]:
    plan = copy.deepcopy(self.plan)
    mutate({t["id"]: t for t in plan["tasks"]}, plan)
    return jp.problems(plan)

  def test_rejects_a_dangling_dependency(self):
    errs = self.broken(lambda t, p: t["CON-06"].update(dependsOn=["NOPE-01"]))
    self.assertTrue(any("unknown NOPE-01" in e for e in errs), errs)

  def test_rejects_a_cycle(self):
    errs = self.broken(lambda t, p: t["CON-04"].update(dependsOn=["CON-06"]))
    self.assertTrue(any("cycle" in e or "before" in e for e in errs), errs)

  def test_rejects_a_start_before_its_predecessor_ends(self):
    errs = self.broken(lambda t, p: t["CON-06"].update(start=t["CON-04"]["start"]))
    self.assertTrue(any("CON-06: starts" in e for e in errs), errs)

  def test_rejects_an_unknown_category_and_bad_dates(self):
    errs = self.broken(lambda t, p: (t["CON-06"].update(category="nope"), t["CON-05"].update(end="2027-13-01")))
    self.assertTrue(any("unknown category nope" in e for e in errs), errs)
    self.assertTrue(any("CON-05: date" in e for e in errs), errs)

  def test_rejects_an_altered_bundle(self):
    saved = dict(jp.BUNDLE)
    try:
      jp.BUNDLE["style.css"] = "0" * 64
      self.assertTrue(any("differs from the pinned" in e for e in jp.bundle_problems()))
    finally:
      jp.BUNDLE.clear()
      jp.BUNDLE.update(saved)

  def test_self_contained_page_has_no_external_script(self):
    page = jp.page(self.plan)
    self.assertNotIn('<script src=', page)
    self.assertNotIn('<link rel="stylesheet" href=', page)
    self.assertEqual(page.count("</script>"), 2)   # the inlined bundle and the mount call


if __name__ == "__main__":
  unittest.main()
