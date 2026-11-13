#!/usr/bin/env python3
"""Tests for ledger.py on a throwaway git repository: backfill and seed, X.Y.Z bumps, gate approvals, the hash
chain (an edited or deleted row and a rewritten history are caught), the spreadsheet and the label rule."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger  # noqa: E402

WP_A = "assurance/02-concept/WP-C-01-item-definition.md"
WP_B = "assurance/07-supporting/WP-P-04-documentation-management.md"


def header(version: str) -> str:
  return f"# WP\n\n| Field | Value |\n|---|---|\n| Version | {version} (some history) |\n\nBody\n"


class Repo:
  def __init__(self, root: Path):
    self.root = root
    self.git("init", "-q", "-b", "main")
    self.git("config", "user.email", "t@example.invalid")
    self.git("config", "user.name", "t")

  def git(self, *args):
    return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True).stdout.strip()

  def write(self, path, text):
    p = self.root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

  def commit(self, msg):
    self.git("add", "-A")
    self.git("commit", "-q", "-m", msg)
    return self.git("rev-parse", "HEAD")

  def merge_pr(self, number, title, files):
    self.git("checkout", "-q", "-b", f"pr{number}")
    for path, text in files.items():
      self.write(path, text)
    self.commit(title)
    self.git("checkout", "-q", "main")
    self.git("merge", "-q", "--no-ff", f"pr{number}", "-m", f"Merge pull request #{number} from x/pr{number}\n\n{title}")
    return self.git("rev-parse", "HEAD")


class LedgerTest(unittest.TestCase):
  def setUp(self):
    self.saved_base, ledger.FORK_BASE = ledger.FORK_BASE, None  # throwaway repositories have no LionDriver fork base
    self.tmp = tempfile.TemporaryDirectory()
    (Path(self.tmp.name) / "r").mkdir()
    self.repo = Repo(Path(self.tmp.name) / "r")
    self.path = Path(self.tmp.name) / "ledger.jsonl"
    self.repo.write(WP_A, header("0.68"))
    self.repo.write(WP_B, header("1.2.3"))
    self.repo.commit("start")
    self.repo.merge_pr(1, "First change to WP-C-01 (DQ-007)", {WP_A: header("0.68") + "more\n"})

  def tearDown(self):
    ledger.FORK_BASE = self.saved_base
    self.tmp.cleanup()

  def update(self):
    return ledger.update(self.path, "main", cwd=self.repo.root)

  def test_backfill_starts_at_the_fork_base(self):
    base = self.repo.git("rev-list", "--first-parent", "main").split()[0]  # the merge of PR 1
    saved, ledger.FORK_BASE = ledger.FORK_BASE, base
    try:
      self.assertEqual(self.update(), 2)  # merge 1 and the seed; "start" (upstream) is left out
      rows = ledger.load(self.path)
      self.assertEqual([r["kind"] for r in rows], ["change", "seed"])
      self.assertEqual(rows[0]["commit"], base)
      self.assertEqual(ledger.verify(rows, "main", self.repo.root), [])
    finally:
      ledger.FORK_BASE = saved

  def test_backfill_refuses_a_history_without_the_fork_base(self):
    saved, ledger.FORK_BASE = ledger.FORK_BASE, "f" * 40
    try:
      with self.assertRaises(SystemExit):
        self.update()
      self.assertFalse(self.path.exists() and self.path.read_text())
    finally:
      ledger.FORK_BASE = saved

  def test_first_run_backfills_then_seeds_from_headers(self):
    self.assertEqual(self.update(), 3)  # start, merge 1, seed
    rows = ledger.load(self.path)
    self.assertEqual([r["kind"] for r in rows], ["direct", "change", "seed"])
    self.assertEqual(rows[1]["pr"], 1)
    self.assertEqual(rows[1]["title"], "First change to WP-C-01 (DQ-007)")
    self.assertEqual(rows[1]["decisions"], ["DQ-007"])
    self.assertEqual(rows[1]["documents"], {"WP-C-01": None})  # before the ledger: no version
    self.assertEqual(ledger.current_versions(rows), {"WP-C-01": "0.68.0", "WP-P-04": "1.2.3"})
    self.assertEqual(ledger.verify(rows, "main", self.repo.root), [])

  def test_content_change_bumps_y_and_resets_z(self):
    self.update()
    self.repo.merge_pr(2, "Change P-04", {WP_B: header("1.2.3") + "x\n"})
    self.assertEqual(self.update(), 1)
    rows = ledger.load(self.path)
    self.assertEqual(rows[-1]["documents"], {"WP-P-04": "1.3.0"})
    self.assertEqual(ledger.current_versions(rows)["WP-C-01"], "0.68.0")  # untouched

  def test_header_edit_does_not_set_the_version(self):
    self.update()
    self.repo.merge_pr(2, "Someone types 9.9 in the header", {WP_A: header("9.9")})
    self.update()
    self.assertEqual(ledger.current_versions(ledger.load(self.path))["WP-C-01"], "0.69.0")

  def test_editorial_bumps_z(self):
    self.assertEqual(ledger.bump("0.68.0", "editorial"), "0.68.1")
    self.assertEqual(ledger.bump("0.68.1", "content"), "0.69.0")
    self.assertEqual(ledger.bump("0.69.4", "approval"), "1.0.0")

  def test_gate_approval_raises_x(self):
    self.update()
    self.repo.merge_pr(2, "G1 approved", {ledger.APPROVALS:
                       "- gate: G1\n  date: 2026-12-01\n  record: gates/G1.md\n  documents: [WP-C-01]\n"})
    self.update()
    rows = ledger.load(self.path)
    self.assertEqual(rows[-1]["documents"], {"WP-C-01": "1.0.0"})
    self.assertEqual(rows[-1]["approvals"], [{"gate": "G1", "record": "gates/G1.md"}])

  def test_new_work_product_starts_from_its_header(self):
    self.update()
    self.repo.merge_pr(2, "New WP", {"assurance/05-software/WP-W-99-new.md": header("0.1")})
    self.update()
    self.assertEqual(ledger.load(self.path)[-1]["documents"], {"WP-W-99": "0.2.0"})

  def test_direct_push_is_an_exception(self):
    self.update()
    self.repo.write(WP_A, header("0.68") + "pushed\n")
    self.repo.commit("pushed straight to main")
    self.update()
    row = ledger.load(self.path)[-1]
    self.assertEqual(row["kind"], "direct")
    self.assertIn("pushed without a pull request", row["exceptions"])

  def test_distribution_record_push_is_not_an_exception(self):
    self.update()
    self.repo.write(ledger.DISTRIBUTION, "- id: CC-2026-001\n")
    self.repo.commit("Distribution record: controlled copy CC-2026-001")
    self.update()
    row = ledger.load(self.path)[-1]
    self.assertEqual((row["kind"], row["exceptions"]), ("distribution", []))

  def test_edited_row_breaks_the_chain(self):
    self.update()
    lines = self.path.read_text().splitlines()
    row = json.loads(lines[1])
    row["title"] = "rewritten"
    lines[1] = json.dumps(row, sort_keys=True, separators=(",", ":"))
    self.path.write_text("\n".join(lines) + "\n")
    problems = ledger.verify(ledger.load(self.path))
    self.assertTrue(any("row edited" in p for p in problems))
    with self.assertRaises(SystemExit):
      self.update()

  def test_deleted_row_breaks_the_chain(self):
    self.update()
    lines = self.path.read_text().splitlines()
    self.path.write_text("\n".join([lines[0]] + lines[2:]) + "\n")
    self.assertTrue(ledger.verify(ledger.load(self.path)))

  def test_rewritten_history_is_caught(self):
    self.update()
    self.repo.git("reset", "-q", "--hard", "HEAD~1")
    self.repo.write(WP_A, header("0.68") + "other\n")
    self.repo.commit("replacement")
    problems = ledger.verify(ledger.load(self.path), "main", self.repo.root)
    self.assertTrue(any("no longer in the history" in p for p in problems))
    with self.assertRaises(SystemExit):
      self.update()

  def test_exceptions_from_github_data(self):
    row = {"kind": "change", "github": {"labels": ["sr-a", "editorial"], "approved_by": [],
                                        "checks": {"failure": 1}}}
    ex = ledger.exceptions_for(row)
    self.assertIn("editorial label on a safety-class change", ex)
    self.assertTrue(any("without an approving review" in e for e in ex))
    self.assertTrue(any("failed check" in e for e in ex))
    self.assertEqual(ledger.exceptions_for({"kind": "change", "github": {"labels": ["nsr"], "approved_by": [],
                                                                         "checks": {"failure": 0}}}), [])

  def test_label_rule(self):
    ev = Path(self.tmp.name) / "event.json"
    ev.write_text(json.dumps({"pull_request": {"labels": [{"name": "sr-q"}, {"name": "editorial"}]}}))
    self.assertEqual(len(ledger.check_labels(ev)), 1)
    ev.write_text(json.dumps({"pull_request": {"labels": [{"name": "nsr"}, {"name": "editorial"}]}}))
    self.assertEqual(ledger.check_labels(ev), [])

  def test_xlsx(self):
    import openpyxl
    self.update()
    out = Path(self.tmp.name) / "ledger.xlsx"
    ledger.write_xlsx(ledger.load(self.path), out)
    wb = openpyxl.load_workbook(out)
    self.assertEqual(wb.sheetnames, ["Changes", "Documents", "Exceptions"])
    self.assertEqual(wb["Documents"]["B2"].value, "0.68.0")
    self.assertEqual(wb["Exceptions"].max_row, 2)  # the initial direct commit


if __name__ == "__main__":
  unittest.main()
