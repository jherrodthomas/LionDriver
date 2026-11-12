#!/usr/bin/env python3
"""Tests for export_wp.py: the stamped document control, the +N mark for changes the ledger has not recorded, the
version of an older commit, the revision history, and the completeness guard."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_wp  # noqa: E402
import ledger  # noqa: E402
from test_ledger import Repo, WP_A  # noqa: E402

SOURCE = """# WP-C-01 Item definition

| Field | Value |
|---|---|
| Work product | WP-C-01 Item definition |
| Version | 0.68 (TSR-513 added (DQ-439 A (lead, 2026-11-11)); 2026-11-11). 0.67 (typo). 0.1 |
| Status | Draft (since G0) |
| Author | Assurance team |

## 1. Purpose

The item steers the car within the envelope ![fig](figures/f.svg) and **never** exceeds 0x344.

```mermaid
graph LR
```
"""


class ExportTest(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    root = Path(self.tmp.name) / "r"
    root.mkdir()
    self.repo = Repo(root)
    self.repo.write(WP_A, SOURCE)
    self.repo.write("assurance/02-concept/figures/f.svg", '<svg xmlns="http://www.w3.org/2000/svg"/>')
    self.repo.commit("start")
    self.path = Path(self.tmp.name) / "ledger.jsonl"
    ledger.update(self.path, "main", cwd=root)
    self.seed = self.repo.git("rev-parse", "HEAD")
    self.old_repo, export_wp.REPO = export_wp.REPO, root

  def tearDown(self):
    export_wp.REPO = self.old_repo
    self.tmp.cleanup()

  def rows(self):
    return ledger.load(self.path)

  def test_header_history_handles_nested_brackets(self):
    self.assertEqual(export_wp.header_history("0.68 (a (b (c)); d). 0.67 (typo). 0.1"),
                     [("0.68", "a (b (c)); d"), ("0.67", "typo"), ("0.1", "")])

  def test_split_source_replaces_the_control_table(self):
    title, fields, body = export_wp.split_source(SOURCE)
    self.assertEqual(title, "WP-C-01 Item definition")
    self.assertEqual(fields["Status"], "Draft (since G0)")
    self.assertNotIn("| Version |", body)
    self.assertTrue(body.startswith("## 1. Purpose"))

  def test_markdown_export_is_stamped_from_the_ledger(self):
    out = Path(self.tmp.name) / "out"
    [p] = export_wp.export(["WP-C-01"], "md", out, rows=self.rows(), commit="main")
    self.assertEqual(p.name, "WP-C-01-v0.68.0.md")
    text = p.read_text()
    self.assertIn("| Version | 0.68.0 (X = 0: not yet approved at a gate) |", text)
    self.assertIn("| Status | Draft |", text)
    self.assertIn("| Copy | " + export_wp.UNCONTROLLED + " |", text)
    self.assertIn("| 0.68.0 | ", text)  # the seed row in the revision history
    self.assertIn("| 0.67 | typo |", text)  # before the ledger, from the header
    self.assertTrue(text.rstrip().endswith(export_wp.UNCONTROLLED))
    self.assertNotIn("| Version | 0.68 (TSR", text)  # the typed control table is gone

  def test_change_not_yet_in_the_ledger_is_marked_and_cannot_be_a_controlled_copy(self):
    self.repo.merge_pr(2, "edit", {WP_A: SOURCE + "\nMore.\n"})
    c = export_wp.control("WP-C-01", self.repo.git("rev-parse", "HEAD"), self.rows(), None)
    self.assertEqual(c["version"], "0.68.0+1")
    with self.assertRaises(SystemExit):
      export_wp.control("WP-C-01", self.repo.git("rev-parse", "HEAD"), self.rows(), "CC-2026-001")
    ledger.update(self.path, "main", cwd=self.repo.root)
    self.assertEqual(export_wp.control("WP-C-01", "main", self.rows(), None)["version"], "0.69.0")

  def test_older_commit_gets_the_version_it_had(self):
    self.repo.merge_pr(2, "edit", {WP_A: SOURCE + "\nMore.\n"})
    ledger.update(self.path, "main", cwd=self.repo.root)
    self.assertEqual(export_wp.control("WP-C-01", self.seed, self.rows(), None)["version"], "0.68.0")
    versions, _ = export_wp.versions_at(self.seed, self.rows())
    self.assertEqual(versions["WP-C-01"], "0.68.0")

  def test_without_a_ledger_the_header_version_is_used_and_said(self):
    c = export_wp.control("WP-C-01", "main", None, None)
    self.assertEqual(c["version"], "0.68.0")
    self.assertIn("from the header", dict(export_wp.block_rows(c))["Version"])

  def test_html_export_inlines_images_and_keeps_every_word(self):
    out = Path(self.tmp.name) / "out"
    [p] = export_wp.export(["WP-C-01"], "html", out, rows=self.rows(), commit="main")
    text = p.read_text()
    self.assertIn("data:image/svg+xml;base64,", text)
    self.assertIn("0.68.0", text)

  def test_completeness_guard_catches_a_lost_word(self):
    self.assertEqual(export_wp.check_complete("Never exceed 0x344 here.", "Never exceed 0x344 here."), [])
    self.assertEqual(export_wp.check_complete("Never exceed 0x344 here.", "Never exceed here."), ["0x344 (x1)"])
    self.assertEqual(export_wp.check_complete("a b ccc ccc", "ccc"), ["ccc (x1)"])
    self.assertEqual(export_wp.check_complete("```mermaid\ngraph\n```", "graph"), [])
    self.assertEqual(export_wp.check_complete("x <= 3 and y > 2 holds", "x <= 3 and y > 2 holds"), [])


class ChangeRecordTest(ExportTest):
  """Selected documents with a change record since the recipient's last copy."""

  def setUp(self):
    super().setUp()
    self.dist = export_wp.distribution_module()
    self.copies = []
    self.saved = self.dist.load
    self.dist.load = lambda path=None: self.copies

  def tearDown(self):
    self.dist.load = self.saved
    super().tearDown()

  def issue(self, cid, recipient, based_on, docs):
    self.copies.append({"id": cid, "issued_at": "2026-11-12T10:00Z", "issued_by": "lead", "recipient": recipient,
                        "purpose": "review", "based_on": based_on, "run": "", "status": "issued",
                        "documents": docs})

  def test_since_last_copy_lists_only_the_changes_after_it(self):
    self.issue("CC-2026-001", "Assessor A", self.seed, ["WP-C-01 0.68.0"])
    self.repo.merge_pr(2, "TSR wording", {WP_A: SOURCE + "\nMore.\n"})
    self.repo.merge_pr(3, "New figure", {WP_A: SOURCE + "\nMore.\nEven more.\n"})
    ledger.update(self.path, "main", cwd=self.repo.root)
    self.issue("CC-2026-002", "Assessor A", self.repo.git("rev-parse", "HEAD"), ["WP-C-01 0.70.0"])
    out = Path(self.tmp.name) / "out"
    files = export_wp.export(["WP-C-01"], "md", out, copy="CC-2026-002", rows=self.rows(), commit="main",
                             since="last-copy", recipient="  assessor a ")
    self.assertEqual([f.name for f in files], ["change-record.md", "WP-C-01-v0.70.0.md"])
    cr = files[0].read_text()
    self.assertIn("since copy CC-2026-001 to Assessor A", cr)
    self.assertIn("| WP-C-01 Item definition | 0.68.0 | 0.70.0 | 2 |", cr)
    self.assertIn("| 0.69.0 | ", cr)
    self.assertIn("TSR wording", cr)
    self.assertIn("Controlled copy CC-2026-002", cr)
    import json
    m = json.loads((out / "manifest.json").read_text())
    self.assertEqual(m["documents"]["WP-C-01"]["version"], "0.70.0")
    self.assertEqual(m["since"]["copy"], "CC-2026-001")
    self.assertEqual(len(m["change_record"]["sha256"]), 64)

  def test_first_copy_to_a_recipient_lists_every_recorded_change(self):
    since = export_wp.resolve_since("last-copy", "Nobody yet", None, self.seed)
    self.assertIsNone(since["commit"])
    self.assertIn("first copy", since["label"])

  def test_outdated_copies(self):
    self.issue("CC-2026-001", "Assessor A", self.seed, ["WP-C-01 0.68.0"])
    self.assertEqual(self.dist.outdated(self.copies, {"WP-C-01": "0.68.0"}), [])
    self.assertEqual(self.dist.outdated(self.copies, {"WP-C-01": "0.69.0"}),
                     [("CC-2026-001", "Assessor A", "WP-C-01", "0.68.0", "0.69.0")])

  def test_documents_field_is_checked(self):
    self.issue("CC-2026-001", "A", "a" * 40, ["WP-C-01 0.68"])
    self.assertTrue(any("documents must be" in e for e in self.dist.check(self.copies)))


if __name__ == "__main__":
  unittest.main()
