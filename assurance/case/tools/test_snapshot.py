#!/usr/bin/env python3
"""Tests for build_snapshot.py and the release status rule (caselib.release_status)."""
from __future__ import annotations

import hashlib
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_snapshot as bs
from caselib import release_status

ORDER = ["approval", "control", "contents", "roles", "raci", "contributors", "status", "scope", "hierarchy", "argument",
         "claims", "evidence", "defeaters", "gates", "config", "annex-a", "annex-b", "annex-c"]


def _status(gates=(), lifecycle="under-development", tag=None):
  return {"gates": {"records": [{"gate": g, "date": "2026-01-01", "record": f"{g}.md", "outcome": o} for g, o in gates]},
          "baseline": {"id": "BL-009", "lifecycle_status": lifecycle, "tag": tag, "source_revision": "abcdef0"}}


class ReleaseStatus(unittest.TestCase):
  def test_no_gate_is_draft(self):
    rs = release_status(_status())
    self.assertFalse(rs["approved"])
    self.assertEqual((rs["label"], rs["detail"]), ("DRAFT", "no gate passed"))

  def test_passed_gate_without_frozen_baseline_is_draft(self):
    rs = release_status(_status([("G0", "pass")]))
    self.assertFalse(rs["approved"])
    self.assertIn("G0 passed", rs["detail"])

  def test_failed_gate_is_draft(self):
    self.assertFalse(release_status(_status([("G0", "fail")], "frozen", "bl-009"))["approved"])

  def test_passed_gate_and_frozen_tagged_baseline_is_approved(self):
    rs = release_status(_status([("G0", "pass"), ("G1", "pass with conditions")], "frozen", "bl-009"))
    self.assertTrue(rs["approved"])
    self.assertEqual(rs["detail"], "G1 passed")

  def test_frozen_baseline_needs_a_tag(self):
    self.assertFalse(release_status(_status([("G0", "pass")], "frozen", None))["approved"])


class Snapshot(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.html, cls.manifest = bs.build(None, None)

  def test_deterministic(self):
    html2, manifest2 = bs.build(None, None)
    self.assertEqual(self.html, html2)
    self.assertEqual(self.manifest, manifest2)

  def test_manifest_hash_matches_html(self):
    self.assertEqual(self.manifest["files"][bs.HTML_NAME], hashlib.sha256(self.html.encode()).hexdigest())

  def test_identity(self):
    snap = self.manifest["snapshot"]
    self.assertRegex(snap["id"], r"^SC-[0-9]{4}\.[0-9]{2}\.[0-9]{2}-[0-9a-f]{7}$")
    self.assertTrue(snap["id"].endswith(snap["commit"][:7]))
    self.assertEqual(snap["kind"], "living snapshot")
    self.assertIn(snap["id"], self.html)

  def test_sections_in_order(self):
    pos = [self.html.find(f'id="{s}"') for s in ORDER]
    self.assertNotIn(-1, pos, [s for s, p in zip(ORDER, pos, strict=True) if p < 0])
    self.assertEqual(pos, sorted(pos))
    self.assertLess(self.html.find('class="cover"'), pos[0])

  def test_status_shown_matches_rule(self):
    rs = self.manifest["release_status"]
    self.assertIn(f'<span class="pill">{rs["label"]}</span>', self.html)
    if not rs["approved"]:
      self.assertIn('class="wm"', self.html)
      self.assertNotIn('<span class="pill">APPROVED</span>', self.html)

  def test_no_signature_lines(self):
    self.assertIn("a signature added to a downloaded copy is not valid", self.html)
    self.assertNotRegex(self.html, r"_{6,}")

  def test_roles_and_raci_follow_the_safety_plan(self):
    roles = bs.md_table(bs.WP_M_02, "### 3.1")
    raci = bs.md_table(bs.WP_M_02, "### 3.2")
    section = lambda sid: self.html.split(f'id="{sid}"', 1)[1].split("</section>", 1)[0]  # noqa: E731
    self.assertEqual(section("roles").count("<tr>") - 1, len(roles))
    self.assertEqual(section("raci").count("<tr>") - 1, len(raci))
    for r in raci:
      self.assertIn(bs.e(bs.plain(r["Activity"])), section("raci"))

  def test_ai_is_never_a_reviewer(self):
    approval = self.html.split('id="approval"', 1)[1].split("</section>", 1)[0]
    self.assertNotRegex(approval, r"(?i)claude[^<]*</td><td>I[1-3]")
    self.assertIn("never a reviewer", self.html)

  def test_every_registered_record_is_listed(self):
    case = bs.load_case()
    for kind, sid in (("claim", "claims"), ("evidence", "evidence")):
      sec = self.html.split(f'id="{sid}"', 1)[1].split("</section>", 1)[0]
      for r in case.of_kind(kind):
        self.assertIn(f">{bs.e(r['id'])}<", sec, f"{kind} {r['id']} missing")
    open_df = [d for d in case.of_kind("defeater") if d["lifecycle_status"] == "open"]
    sec = self.html.split('id="defeaters"', 1)[1].split("</section>", 1)[0]
    self.assertEqual(len(re.findall(r"<tr><td><span class='mono'>DF-", sec)), len(open_df))

  def test_previous_snapshot_delta(self):
    prev = {"snapshot": {"id": "SC-2000.01.01-0000000", "commit": self.manifest["snapshot"]["commit"]}, "status": self.manifest["status"]}
    html, manifest = bs.build(None, prev)
    self.assertEqual(manifest["snapshot"]["previous"], "SC-2000.01.01-0000000")
    self.assertIn("no status change", html)
    self.assertIn("no change to assurance/", html)

  def test_baseline_tag(self):
    _, manifest = bs.build("bl-002", None)
    self.assertEqual(manifest["snapshot"]["kind"], "baseline release")
    self.assertTrue(manifest["snapshot"]["id"].startswith("BL-002-"))
    with self.assertRaises(SystemExit):
      bs.build("v1.0", None)


if __name__ == "__main__":
  unittest.main()
