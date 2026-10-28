#!/usr/bin/env python3
"""Tests for build_snapshot.py and the release status rule (caselib.release_status)."""
from __future__ import annotations

import base64
import hashlib
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_snapshot as bs
import distribution as dist
from caselib import release_status

ORDER = ["approval", "control", "contents", "documents", "distribution", "roles", "raci", "contributors", "status", "traceability",
         "coverage", "lifecycle", "vv", "freshness", "scope", "hierarchy", "argument",
         "claims", "evidence", "defeaters", "gates", "config", "annex-a", "annex-b", "annex-c", "annex-d"]


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

  def _section(self, sid: str) -> str:
    if sid == "cover":
      return self.html.split('class="cover"', 1)[1].split("</section>", 1)[0]
    return self.html.split(f'id="{sid}"', 1)[1].split("</section>", 1)[0]

  @staticmethod
  def _vs(html: str) -> list[str]:
    """The system-V SVGs inlined in a piece of the snapshot (base64 data URIs, like every figure)."""
    out = [base64.b64decode(b).decode() for b in re.findall(r'src="data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)"', html)]
    return [s for s in out if "<title>System V" in s]

  def test_system_v_is_embedded_where_expected(self):
    expected = {"cover": ["System V · status lens"], "status": ["System V · status lens"],
                "traceability": ["System V · trace lens", "System V per safety goal"], "gates": ["System V · gate lens"]}
    for sid, titles in expected.items():
      found = [re.search(r"<title>(.*?)</title>", s).group(1) for s in self._vs(self._section(sid))]
      self.assertEqual(found, titles, sid)
    self.assertIn('href="#traceability"', self._section("contents"))
    self.assertIn("1.1 Traceability on the V", self._section("traceability"))

  def test_cover_signature_follows_the_data(self):
    vd = bs.vmodel.load()
    self.assertIn(bs.e(bs.v_signature(vd)), self._section("cover"))
    if not any(vd.executed.values()) and not any(st in ("A", "B") for st, _ in vd.register.values()):
      self.assertIn("status signature · nothing verified yet", self.html)

  def test_nothing_green_in_any_v(self):
    vd = bs.vmodel.load()
    earned = (any(st in ("A", "B") for st, _ in vd.register.values()) or "passed" in vd.gate_status.values()
              or any(vd.passed.values()))
    vs = self._vs(self.html)
    self.assertEqual(len(vs), 5)
    for svg in vs:
      self.assertIn('role="img"', svg)
      if not earned:
        self.assertNotIn(bs.vmodel.GREEN, svg)
        self.assertNotIn(bs.vmodel.GREEN_BG, svg)

  def test_baseline_tag(self):
    _, manifest = bs.build("bl-002", None)
    self.assertEqual(manifest["snapshot"]["kind"], "baseline release")
    self.assertTrue(manifest["snapshot"]["id"].startswith("BL-002-"))
    with self.assertRaises(SystemExit):
      bs.build("v1.0", None)

  def test_running_header_and_footer(self):
    h, snap = self.manifest["header"], self.manifest["snapshot"]
    self.assertEqual(h["left"], f"WP-K-01 Safety case · v{bs.wp_version(bs.WP_K_01)} · {snap['id']}")
    self.assertEqual(h["right"], "DRAFT · PUBLIC · UNCONTROLLED")
    for part in ("CFG-001", "LIONDRIVER_REFERENCE=1", snap["commit"][:7], *snap["pins"].values(), "baseline BL-"):
      self.assertIn(part, h["footer"])
    self.assertIn(snap["issued"], h["footer2"])
    self.assertIn(bs.retention("living snapshot"), h["footer2"])
    self.assertTrue(h["footer3"].startswith("Uncontrolled"))
    self.assertEqual(h["verify"], bs.RELEASES_URL)

  def test_retention_follows_wp_p_04(self):
    self.assertIn("5 years", bs.retention("living snapshot"))
    self.assertIn("15 years", bs.retention("baseline release"))

  def test_document_control_fields(self):
    control = self.html[self.html.find('id="control"'):self.html.find('id="contents"')]
    for field in ("Version", "Status", "Issued", "Configuration", "Classification", "Copy", "Distribution record", "Retention"):
      self.assertIn(f"<td>{field}</td>", control)
    self.assertIn("Uncontrolled", control)

  def test_controlled_copy(self):
    entry = {"id": "CC-2026-007", "issued_at": "2026-10-14T09:30Z", "issued_by": "someone", "recipient": "Assessor <A&B>",
             "purpose": "G1 review", "based_on": "0" * 40, "run": "", "status": "issued"}
    real = dist.load
    dist.load = lambda path=dist.PATH: [entry]
    try:
      html, manifest = bs.build(None, None, "CC-2026-007")
      with self.assertRaises(SystemExit):
        bs.build(None, None, "CC-2026-008")
    finally:
      dist.load = real
    self.assertEqual(manifest["header"]["right"], "DRAFT · PUBLIC · CONTROLLED COPY CC-2026-007")
    self.assertIn("for Assessor <A&B> (G1 review)", manifest["header"]["footer3"])
    self.assertIn("Assessor &lt;A&amp;B&gt;", html)
    self.assertNotIn("Assessor <A&B>", html)
    self.assertEqual(manifest["snapshot"]["copy"]["id"], "CC-2026-007")

  def test_new_pages_follow_their_sources(self):
    import snapshot_pages as sp
    import trace_map as tm
    m = tm.build()
    rtm = self.html[self.html.find('id="annex-d"'):]
    for iid in m.items:
      if iid.split("-")[0] in sp.RTM_KINDS:
        self.assertIn(f">{iid}<", rtm)
    cov = self.html[self.html.find('id="coverage"'):self.html.find('id="lifecycle"')]
    for parent, child, _, alloc in tm.DERIVATIONS:
      done, total, _ = tm.derivation(m, parent, child, alloc)
      self.assertIn(f">{done}/{total}<", cov)
    life = self.html[self.html.find('id="lifecycle"'):self.html.find('id="vv"')]
    for aid in sp.pm.load_model().activities:
      self.assertIn(f">{aid}<", life)
    docs = self.html[self.html.find('id="documents"'):self.html.find('id="distribution"')]
    for r in sp.register_rows():
      self.assertIn(f">{r['wp']}<", docs)

  def test_nothing_green_without_a_pass_or_approval(self):
    import snapshot_pages as sp
    green_bg = sp.TONE["ok"][0]
    part = self.html[self.html.find('id="coverage"'):self.html.find('id="scope"')] + self.html[self.html.find('id="annex-d"'):]
    approved = any(r["status"] in ("A", "B") for r in sp.register_rows())
    if not approved:
      self.assertNotIn(f"background:{green_bg}", part)

  def test_freshness_counts_every_evidence_record(self):
    from caselib import load_case
    fresh = self.html[self.html.find('id="freshness"'):self.html.find('id="scope"')]
    n = len(load_case().of_kind("evidence"))
    m = re.search(r"(\d+) of (\d+) unchanged since recorded · (\d+) changed since · (\d+) without", fresh)
    self.assertIsNotNone(m)
    self.assertEqual(int(m.group(2)), n)
    self.assertLessEqual(int(m.group(1)) + int(m.group(3)) + int(m.group(4)), n)


class Distribution(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    self.path = Path(self.tmp.name) / "distribution.yaml"

  def tearDown(self):
    self.tmp.cleanup()

  def test_record_is_valid(self):
    self.assertEqual(dist.check(dist.load()), [])

  def test_issue_appends_numbered_entries(self):
    a = dist.issue("Jane Doe, assessor", "G1  review", "lead", "a" * 40, at="2026-10-14T09:30Z", path=self.path)
    b = dist.issue("Supplier: \"X\"", "audit", "lead", "b" * 40, at="2026-11-01T10:00Z", path=self.path)
    c = dist.issue("Next year", "audit", "lead", "c" * 40, at="2027-01-02T08:00Z", path=self.path)
    self.assertEqual((a, b, c), ("CC-2026-001", "CC-2026-002", "CC-2027-001"))
    copies = dist.load(self.path)
    self.assertEqual(dist.check(copies), [])
    self.assertEqual(copies[0]["purpose"], "G1 review")
    self.assertEqual(copies[1]["recipient"], 'Supplier: "X"')

  def test_rules(self):
    ok = {"id": "CC-2026-001", "issued_at": "2026-10-14T09:30Z", "issued_by": "x", "recipient": "r", "purpose": "p",
          "based_on": "a" * 40, "run": "", "status": "issued"}
    self.assertEqual(dist.check([ok]), [])
    self.assertTrue(dist.check([{**ok, "id": "CC-2025-001"}]))
    self.assertTrue(dist.check([{**ok, "status": "withdrawn"}]))
    self.assertEqual(dist.check([{**ok, "status": "withdrawn", "withdrawn_at": "2026-10-15T00:00Z", "reason": "superseded"}]), [])
    self.assertTrue(dist.check([ok, ok]))
    self.assertTrue(dist.check([{**ok, "based_on": "abc"}]))
    with self.assertRaises(SystemExit):
      dist.clean("x" * (dist.MAX_TEXT + 1))
    with self.assertRaises(SystemExit):
      dist.clean("   ")

  def test_withdrawn_copy_cannot_be_printed(self):
    with self.assertRaises(SystemExit):
      dist.find("CC-2026-001", [{"id": "CC-2026-001", "status": "withdrawn"}])


if __name__ == "__main__":
  unittest.main()
