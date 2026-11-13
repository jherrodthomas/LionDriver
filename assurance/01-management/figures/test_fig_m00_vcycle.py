#!/usr/bin/env python3
"""Tests for fig_m00_vcycle.py: current output, every register row placed once, loud failures, agreed counts."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_m00_vcycle as v  # noqa: E402
from figkit import FigureError  # noqa: E402


def patched(text: str):
  """Make read_register see `text` as the register."""
  real = Path.read_text

  def fake(self, *a, **k):
    return text if self == v.REGISTER else real(self, *a, **k)
  return mock.patch.object(Path, "read_text", fake)


class VCycle(unittest.TestCase):
  REG = v.REGISTER.read_text(encoding="utf-8")

  def test_committed_output_is_current(self):
    self.assertEqual(v.main(["--check"]), 0)

  def test_every_register_row_placed_exactly_once(self):
    m = v.build_model()
    placed = [w for side in m["boxes"].values() for b in side for w in b["ids"]] + \
             [w for b in m["band"] for w in b["ids"]]
    self.assertEqual(sorted(placed), sorted(m["wps"]))
    self.assertEqual(len(placed), len(set(placed)))
    ids = set(re.findall(r"^\| \[(WP-[A-Z]-\d\d)\]", self.REG, re.M))
    self.assertEqual(ids, set(m["wps"]))

  def test_unknown_status_fails(self):
    row = next(ln for ln in self.REG.splitlines() if ln.startswith("| [WP-C-03]"))
    bad = self.REG.replace(row, row.rsplit("|", 2)[0] + "| Q |")
    with patched(bad), self.assertRaises(FigureError):
      v.read_register()

  def test_new_register_row_must_be_placed(self):
    row = next(ln for ln in self.REG.splitlines() if ln.startswith("| [WP-C-12]"))
    extra = row.replace("WP-C-12", "WP-C-13")
    with patched(self.REG.replace(row, row + "\n" + extra)), self.assertRaises(FigureError) as e:
      v.build_model()
    self.assertIn("WP-C-13", str(e.exception))

  def test_counts_agree_with_the_register(self):
    m = v.build_model()
    rows = [ln for ln in self.REG.splitlines() if re.match(r"^\| \[WP-", ln)]
    drafts = sum(1 for r in rows if r.rstrip().endswith("| D |"))
    self.assertEqual(sum(1 for w in m["wps"].values() if w["status"] == "D"), drafts)
    main = v.README_MAIN.read_text(encoding="utf-8")
    self.assertIn(f"{len(rows)} work products", main)

  def test_readme_links_open_existing_folders(self):
    s = v.README_A.read_text(encoding="utf-8")
    block = s[s.index(v.BEGIN):s.index(v.END)]
    links = re.findall(r'<a href="([^"]+)"', block)
    self.assertEqual(len(links), 2 * len(v.BOXES["define"]) + 1 + len(v.BAND))
    for ln in links:
      self.assertTrue((v.A / ln).exists(), ln)

  def test_current_phase_is_first_gate_not_passed(self):
    m = v.build_model()
    first = next(p for p in m["phases"] if not p["passed"])
    self.assertIs(m["now"], first)

  def test_every_box_has_an_exploded_page_listing_each_work_product_once(self):
    import vcycle_explode as x
    m = v.build_model()
    boxes = x.all_boxes(m)
    self.assertEqual(len(boxes), 2 * len(v.BOXES["define"]) + 1 + len(v.BAND))
    seen = []
    for _, _, b in boxes:
      page = (x.PAGES / f"{x.slug(b['title'])}.md").read_text(encoding="utf-8")
      rows = re.findall(r"^\| \[(WP-[A-Z]-\d\d) ", page, re.M)
      self.assertEqual(sorted(rows), sorted(b["ids"]), b["title"])
      seen += rows
    self.assertEqual(sorted(seen), sorted(m["wps"]))

  def test_work_product_without_producing_activity_fails(self):
    import vcycle_explode as x
    m = v.build_model()
    producer, lanes, reviews, ctx = x.process_facts()
    del producer["WP-C-03"]
    where = {w: b["title"] for _, _, b in x.all_boxes(m) for w in b["ids"]}
    with self.assertRaises(FigureError):
      x.explode(m, m["boxes"]["define"][0], where, (producer, lanes, reviews, ctx))

  def test_measure_planned_at_two_gates_is_listed_once(self):
    import vcycle_explode as x
    self.assertEqual(x.dedupe([("CR-03", "a", False), ("CR-03", "b", True)]), [("CR-03", "a", True)])

  def test_time_view_freshness_matches_its_page_and_the_records(self):
    import vcycle_time as tv
    m = v.build_model()
    d = tv.model(m)
    page = (tv.vx.PAGES / tv.PAGE).read_text(encoding="utf-8")
    rows = re.findall(r"^\| (WP-[A-Z]-\d\d) \| (\S+) \| (WP-[A-Z]-\d\d) \| (\S+) \|$", page, re.M)
    self.assertEqual(len(rows), len(d["newer"]))
    for w, own, i, later in rows:
      self.assertGreater(later, own, w)
      self.assertEqual(own, d["last"][w])
    self.assertFalse(set(d["undated"]) & set(d["last"]))
    self.assertEqual(set(d["undated"]) | set(d["last"]), set(m["wps"]))
    self.assertEqual(d["asof"], max(d["last"].values()))

  def test_time_view_unreadable_gate_date_fails(self):
    import vcycle_time as tv
    with self.assertRaises(FigureError):
      tv.month("Spring 2027")
    self.assertEqual(tv.month("Mar 2027").month, 3)

  def test_time_view_has_one_row_per_box_in_v_order(self):
    import vcycle_time as tv
    m = v.build_model()
    rows = tv.rows(m)
    self.assertEqual([r["box"]["title"] for r in rows][0], m["boxes"]["define"][0]["title"])
    self.assertEqual([r["box"]["title"] for r in rows][-1], m["boxes"]["verify"][0]["title"])
    self.assertEqual(len(rows), 2 * len(v.BOXES["define"]) + 1)

  def test_each_standard_overlay_counts_the_register_column(self):
    import vcycle_standards as vs
    m = v.build_model()
    _, _, _, ctx = vs.vx.process_facts()
    for key, label, col, needle in vs.STANDARDS:
      with self.subTest(standard=label):
        ov = vs.overlay(m, key, col, needle, ctx.register)
        want = sum(1 for r in ctx.register.values()
                   if r.clauses.get(col, "").strip() not in ("", "—", "-") and (not needle or needle in r.clauses[col]))
        self.assertEqual(ov["total"], want)
        page = (vs.vx.PAGES / vs.page_name(key)).read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"^\| \[[^]]+\]\([^)]+\.md\) \| \[WP-", page, re.M)), want)
        self.assertIn(f"**{label}**", page)

  def test_toggle_row_links_every_overlay_from_the_readme(self):
    import vcycle_standards as vs
    block = v.README_A.read_text(encoding="utf-8")
    for key, _, _, _ in vs.STANDARDS:
      self.assertIn(f"01-management/vcycle/{vs.page_name(key)}", block)
    self.assertIn("View by standard: **All**", block)

  def test_clause_summaries(self):
    import vcycle_standards as vs
    self.assertEqual(vs.summary("iso26262", ["9 §5, 4 §6", "6 §5–11, Annex C; 8 §6–12", "3 §6 (controllability)"]),
                     "26262-3 §6 · 26262-4 §6 · 26262-6 §5–11, Annex C · 26262-8 §6–12 · 26262-9 §5")
    self.assertEqual(vs.summary("aspice", ["MLE.1–4, SUP.11", "SEC.*", "MAN.3"]), "MLE.1–4, SEC.*, SUP.11, MAN.3")

  def test_a_standard_no_work_product_cites_fails(self):
    import vcycle_standards as vs
    m = v.build_model()
    _, _, _, ctx = vs.vx.process_facts()
    with self.assertRaises(FigureError):
      vs.overlay(m, "x", "other", "no such standard", ctx.register)

  def test_crosswalk_has_every_box_once_and_matches_the_overlays(self):
    import vcycle_crosswalk as xw
    import vcycle_standards as vs
    m = v.build_model()
    gs, c = xw.groups(m), xw.cells(m)
    titles = [b["title"] for _, _, boxes in gs for b in boxes]
    self.assertEqual(sorted(titles), sorted(b["title"] for _, _, b in vs.vx.all_boxes(m)))
    page = (vs.vx.PAGES / xw.PAGE).read_text(encoding="utf-8")
    rows = [ln for ln in page.splitlines() if ln.startswith("| ") and "](" in ln.split("|")[2]]
    self.assertEqual(len(rows), len(titles))
    for key, _, _, _ in vs.STANDARDS:
      self.assertEqual(sum(len(cl["hit"]) for cl in c["cells"][key].values()), c["totals"][key])
    self.assertIn("**Crosswalk**", page)

  def test_clauses_are_sorted_numerically(self):
    import vcycle_standards as vs
    self.assertEqual(vs.summary("iso21434", ["§15, §9.4", "§9.5"]), "§9.4, §9.5, §15")
    self.assertEqual(vs.summary("iso26262", ["9 §7, 2 §6", "2 §5"]), "26262-2 §5, §6 · 26262-9 §7")
    self.assertEqual(vs.summary("aspice", ["MAN.3", "SWE.10, SWE.2", "SYS.2"]), "SYS.2, SWE.2, SWE.10, MAN.3")

  def test_impact_downstream_follows_the_process_model(self):
    import vcycle_impact as vi
    down = {"A": {"B"}, "B": {"C", "D"}, "D": {"A"}}
    self.assertEqual(vi.steps_from("A", down), {"A": 0, "B": 1, "C": 2, "D": 2})
    self.assertEqual(vi.state("C", "A", "2026-11-07", {"A": 0, "C": 2}, {"C": "2026-11-07"}), "ok")
    self.assertEqual(vi.state("C", "A", "2026-11-07", {"A": 0, "C": 2}, {"C": "2026-11-06"}), "look")
    self.assertEqual(vi.state("C", "A", "2026-11-07", {"A": 0, "C": 2}, {}), "undated")
    self.assertEqual(vi.state("E", "A", "2026-11-07", {"A": 0}, {"E": "2026-11-01"}), "none")

  def test_impact_pages_for_the_recent_changes_and_counts_agree(self):
    import vcycle_impact as vi
    m = v.build_model()
    d = vi.model(m)
    self.assertEqual(len(d["recent"]), min(vi.RECENT, len(d["changes"])))
    dates = [c["when"] for c in d["changes"]]
    self.assertEqual(dates, sorted(dates, reverse=True))
    for c in d["recent"]:
      page = (vi.vx.PAGES / vi.page_name(c["wp"])).read_text(encoding="utf-8")
      rows = [ln for ln in page.splitlines() if ln.startswith("| [WP-")]
      self.assertEqual(len(rows), len(c["hop"]) - 1, c["wp"])
      self.assertEqual(sum(c["counts"].values()), len(c["hop"]) - 1)
      self.assertEqual(page.count("worth a look |"), c["counts"]["look"])
    index = (vi.vx.PAGES / vi.INDEX).read_text(encoding="utf-8")
    self.assertEqual(len([ln for ln in index.splitlines() if ln.startswith("| [WP-")]), len(d["changes"]))

  def test_gate_board_reads_every_skeleton(self):
    import vcycle_gates as vg
    m = v.build_model()
    d = vg.model(m)
    self.assertEqual([g["gate"] for g in d["gates"]], [f"G{n}" for n in range(7)])
    self.assertIs(d["next"], next(g for g in d["gates"] if not g["passed"]))
    reg = m["wps"]
    for g in d["gates"]:
      for p in g["wps"]:
        if p["id"] in reg:
          self.assertEqual(p["status"], vg.vx.pm.STATUS_NAMES[reg[p["id"]]["status"]], p["id"])
    page = (vg.vx.PAGES / vg.PAGE).read_text(encoding="utf-8")
    self.assertEqual(len([ln for ln in page.splitlines() if re.match(r"^\| \[G\d ", ln)]), 7)

  def test_gate_board_rejects_an_unexpected_agreed_cell(self):
    import vcycle_gates as vg
    real = Path.read_text
    g0 = vg.SKELETONS / "G0-skeleton.md"

    def fake(self, *a, **k):
      t = real(self, *a, **k)
      return re.sub(r"(\| IFR-31 \|.*\| )none \|  \|", r"\1none | maybe |", t) if self == g0 else t
    with mock.patch.object(Path, "read_text", fake), self.assertRaises(FigureError):
      vg.read_gate(0)

  def test_evidence_ladder_follows_the_records(self):
    import vcycle_evidence as ve
    self.assertEqual(ve.level({"id": "x", "evidence_status": "missing", "review_state": "not-reviewed"}), 0)
    self.assertEqual(ve.level({"id": "x", "evidence_status": "partial"}), 1)
    self.assertEqual(ve.level({"id": "x", "evidence_status": "available", "review_state": "not-reviewed"}), 2)
    self.assertEqual(ve.level({"id": "x", "evidence_status": "available", "review_state": "rejected"}), 3)
    self.assertEqual(ve.level({"id": "x", "evidence_status": "available", "review_state": "accepted"}), 4)
    for bad in ({"id": "x", "evidence_status": "done"}, {"id": "x", "evidence_status": "partial", "review_state": "ok"}):
      with self.assertRaises(FigureError):
        ve.level(bad)

  def test_every_evidence_item_is_placed_once_or_listed(self):
    import vcycle_evidence as ve
    m = v.build_model()
    d = ve.model(m)
    placed = [e["id"] for es in d["per"].values() for e in es]
    self.assertEqual(sorted(placed + [e["id"] for e in d["unplaced"]]), sorted(e["id"] for e in d["evidence"]))
    self.assertEqual(len(placed), len(set(placed)))
    page = (ve.vx.PAGES / ve.PAGE).read_text(encoding="utf-8")
    self.assertEqual(len([ln for ln in page.splitlines() if re.match(r"^\| \[[^]]+\]\([^)]+\.md\) \| ", ln)]),
                     len(placed))

  def test_conflict_lag_has_a_grace_period(self):
    import vcycle_conflicts as vc
    d = {"title": "Def", "ids": ["A"]}
    vb = {"title": "Ver", "ids": ["B"]}
    edge = (vc.date("2026-11-01") + vc.dt.timedelta(days=vc.GRACE_DAYS)).isoformat()
    self.assertIsNone(vc.lag(d, vb, {"A": edge, "B": "2026-11-01"}))
    hit = vc.lag(d, vb, {"A": "2026-12-20", "B": "2026-11-01"})
    self.assertEqual((hit["box"], hit["checks"], hit["days"]), ("Ver", "Def", 49))
    self.assertIsNone(vc.lag(d, vb, {"A": "2026-11-01", "B": "2026-11-20"}))
    self.assertIsNone(vc.lag(d, vb, {"B": "2026-11-20"}))

  def test_every_conflict_is_on_one_box_and_on_the_page(self):
    import vcycle_conflicts as vc
    m = v.build_model()
    d = vc.model(m)
    for key in ("stale", "orphan", "gate"):
      on_boxes = [w for _, _, b in vc.vx.all_boxes(m) for w in vc.per_box(d, b)[key]]
      self.assertEqual(sorted(on_boxes), sorted(d[key]), key)
    for wp, newer in d["stale"].items():
      self.assertTrue(all(when > d["last"][wp] for when, _ in newer), wp)
    page = (vc.vx.PAGES / vc.PAGE).read_text(encoding="utf-8")
    for wp in [*d["stale"], *d["orphan"], *d["gate"]]:
      self.assertIn(f"[{wp}]", page)
    for g in d["lag"].values():
      self.assertGreater(g["days"], vc.GRACE_DAYS)


if __name__ == "__main__":
  unittest.main()
