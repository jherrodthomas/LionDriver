#!/usr/bin/env python3
"""The change ledger: one append-only, hash-chained row per change merged to liondriver-dev, and the work-product
versions computed from it (WP-P-04 §5 and §6, decisions DQ-441 and DQ-442).

A row is written by CI (.github/workflows/ledger.yaml) after each push to liondriver-dev and never edited. Each row
carries the hash of the row before it, so changing or deleting an old row breaks every later hash; `verify` checks
the chain and that every recorded commit is still in the branch history, so a rewritten history is caught too.
The ledger lives on its own branch (`ledger`, file ledger.jsonl), so writing it never adds commits to liondriver-dev.

What a row holds: the merge commit, date, pull request, title, files changed, the work products it touched and the
version each one has after it, and, when the GitHub API is reachable, the change-class labels, who merged, who
approved and the check results of the PR head. Rows written before the ledger existed (the backfill) carry what git
alone knows.

Versions are X.Y.Z and are computed, never typed (DQ-441):
  X  approved issue: +1 when a gate approval lists the work product in gate-approvals.yaml (DQ-442); resets Y and Z
  Y  content change: +1 for each merged change that touches the work product; resets Z
  Z  editorial change: +1 for each merged change labelled `editorial`
The first run starts every work product at the version its header carries at that commit (0.68 -> 0.68.0), so no
history is renumbered.

Usage:
  ledger.py update   --ledger FILE [--ref REF] [--repo OWNER/NAME]   append rows for new commits (GitHub data if
                                                                    GITHUB_TOKEN is set and --repo is given)
  ledger.py verify   --ledger FILE [--ref REF]                       exit 1 if the chain or the history is broken
  ledger.py versions --ledger FILE [--doc WP-S-02]                   current version of every (or one) work product
  ledger.py xlsx     --ledger FILE --out FILE.xlsx                   the spreadsheet view: Changes, Documents, Exceptions
  ledger.py check-labels --event FILE                                PR rule: `editorial` never on sr-a or sr-q
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
APPROVALS = "assurance/07-supporting/ledger/gate-approvals.yaml"
GENESIS = "0" * 64
WP_FILE = re.compile(r"(?:^|/)(WP-[A-Z]{1,2}-\d{2,3}[a-z]?)-[^/]*\.md$")
HEADER_VERSION = re.compile(r"^\|\s*Version\s*\|\s*v?(\d+)\.(\d+)(?:\.(\d+))?", re.M)
PR_SUBJECT = re.compile(r"^Merge (?:pull request )?#(\d+)\b")
DECISION = re.compile(r"\bDQ-\d{3}\b")
SAFETY_CLASSES = ("sr-a", "sr-q")
CLASSES = ("sr-a", "sr-q", "sr-t", "nsr")
EDITORIAL = "editorial"


# ---------------------------------------------------------------------------------------------------- git helpers

def git(*args: str, cwd: Path | None = None) -> str:
  return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def first_parent_commits(ref: str, cwd: Path | None = None) -> list[str]:
  """Oldest first. Stops at a shallow boundary without error."""
  out = git("rev-list", "--first-parent", "--reverse", ref, cwd=cwd)
  return [line for line in out.split() if line]


def commit_info(sha: str, cwd: Path | None = None) -> dict:
  raw = git("show", "-s", "--format=%H%x00%P%x00%cI%x00%s%x00%b", sha, cwd=cwd)
  full, parents, date, subject, body = raw.split("\x00", 4)
  return {"commit": full, "parents": parents.split(), "date": date.strip(), "subject": subject,
          "body": body.strip()}


def changed_files(sha: str, parent: str | None, cwd: Path | None = None) -> list[str]:
  if parent is None:
    out = git("show", "--name-only", "--format=", sha, cwd=cwd)
  else:
    out = git("diff", "--name-only", "--no-renames", parent, sha, cwd=cwd)
  return sorted({line for line in out.splitlines() if line})


def documents_at(sha: str, cwd: Path | None = None) -> dict[str, str]:
  """Work-product ID -> path of its file at a commit."""
  docs = {}
  for path in git("ls-tree", "-r", "--name-only", sha, "assurance", cwd=cwd).splitlines():
    m = WP_FILE.search(path)
    if m:
      docs[m.group(1)] = path
  return docs


def header_version(sha: str, path: str, cwd: Path | None = None) -> str:
  text = git("show", f"{sha}:{path}", cwd=cwd)
  m = HEADER_VERSION.search(text)
  if not m:
    return "0.1.0"
  return f"{int(m.group(1))}.{int(m.group(2))}.{int(m.group(3) or 0)}"


def approvals_at(sha: str, cwd: Path | None = None) -> list[dict]:
  try:
    text = git("show", f"{sha}:{APPROVALS}", cwd=cwd)
  except subprocess.CalledProcessError:
    return []
  import yaml
  data = yaml.safe_load(text) or []
  return [a for a in data if isinstance(a, dict)]


def approval_key(a: dict) -> str:
  return f"{a.get('gate')}|{a.get('record')}|{a.get('date')}"


# ---------------------------------------------------------------------------------------------------- versions

def bump(version: str, kind: str) -> str:
  x, y, z = (int(p) for p in version.split("."))
  if kind == "approval":
    return f"{x + 1}.0.0"
  if kind == "editorial":
    return f"{x}.{y}.{z + 1}"
  return f"{x}.{y + 1}.0"


def current_versions(rows: list[dict]) -> dict[str, str]:
  """Fold the ledger: the seed row sets every version, later rows overwrite those they touched."""
  versions: dict[str, str] = {}
  for row in rows:
    for doc, ver in (row.get("documents") or {}).items():
      if ver:
        versions[doc] = ver
  return dict(sorted(versions.items()))


# ---------------------------------------------------------------------------------------------------- GitHub data

def gh_get(url: str, token: str):
  req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}",
                                             "Accept": "application/vnd.github+json",
                                             "X-GitHub-Api-Version": "2022-11-28"})
  with urllib.request.urlopen(req, timeout=30) as resp:
    return json.load(resp)


def github_meta(repo: str, pr: int, token: str) -> dict:
  api = f"https://api.github.com/repos/{repo}"
  pull = gh_get(f"{api}/pulls/{pr}", token)
  reviews = gh_get(f"{api}/pulls/{pr}/reviews?per_page=100", token)
  latest: dict[str, str] = {}
  for r in reviews:
    latest[r["user"]["login"]] = r["state"]
  author = pull["user"]["login"]
  checks = gh_get(f"{api}/commits/{pull['head']['sha']}/check-runs?per_page=100", token)
  tally = {"total": 0, "success": 0, "failure": 0, "skipped": 0, "other": 0}
  for run in checks.get("check_runs", []):
    tally["total"] += 1
    c = run.get("conclusion")
    if c == "success":
      tally["success"] += 1
    elif c in ("failure", "timed_out", "cancelled", "action_required"):
      tally["failure"] += 1
    elif c in ("skipped", "neutral"):
      tally["skipped"] += 1
    else:
      tally["other"] += 1
  return {"title": pull["title"], "author": author,
          "labels": sorted(label["name"] for label in pull.get("labels", [])),
          "merged_by": (pull.get("merged_by") or {}).get("login"),
          "approved_by": sorted(u for u, s in latest.items() if s == "APPROVED" and u != author),
          "checks": tally}


def exceptions_for(row: dict) -> list[str]:
  out = []
  if row["kind"] == "direct":
    out.append("pushed without a pull request")
  gh = row.get("github")
  if not gh:
    return out
  labels = set(gh["labels"])
  if not labels & set(CLASSES):
    out.append("no change-class label")
  if EDITORIAL in labels and labels & set(SAFETY_CLASSES):
    out.append("editorial label on a safety-class change")
  if labels & set(SAFETY_CLASSES) and not gh["approved_by"]:
    out.append("safety-class change without an approving review by someone other than the author")
  if gh["checks"]["failure"]:
    out.append(f"merged with {gh['checks']['failure']} failed check(s)")
  return out


# ---------------------------------------------------------------------------------------------------- the chain

def row_hash(prev: str, row: dict) -> str:
  body = {k: v for k, v in row.items() if k != "hash"}
  return hashlib.sha256((prev + json.dumps(body, sort_keys=True, separators=(",", ":"))).encode()).hexdigest()


def load_ref(ref: str = "origin/ledger", cwd: Path | None = None) -> list[dict] | None:
  """The ledger as committed on its branch, or None when the branch is not there (before the first run)."""
  try:
    text = git("show", f"{ref}:ledger.jsonl", cwd=cwd)
  except subprocess.CalledProcessError:
    return None
  return [json.loads(line) for line in text.splitlines() if line.strip()]


def load(path: Path) -> list[dict]:
  if not path.exists():
    return []
  return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def append(path: Path, rows: list[dict], new: list[dict]) -> None:
  prev = rows[-1]["hash"] if rows else GENESIS
  with path.open("a") as f:
    for row in new:
      row["seq"] = (rows[-1]["seq"] + 1) if rows else 1
      row["prev"] = prev
      row["hash"] = row_hash(prev, row)
      f.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
      rows.append(row)
      prev = row["hash"]


def verify(rows: list[dict], ref: str | None = None, cwd: Path | None = None) -> list[str]:
  problems = []
  prev = GENESIS
  for i, row in enumerate(rows, 1):
    if row.get("seq") != i:
      problems.append(f"row {i}: seq is {row.get('seq')}")
    if row.get("prev") != prev:
      problems.append(f"row {i}: prev does not match the hash of row {i - 1}")
    if row.get("hash") != row_hash(row.get("prev", ""), row):
      problems.append(f"row {i}: hash does not match its content (row edited)")
    prev = row.get("hash", "")
  if ref:
    history = set(first_parent_commits(ref, cwd))
    for row in rows:
      if row["commit"] not in history:
        problems.append(f"row {row['seq']}: commit {row['commit'][:8]} is no longer in the history of {ref}")
  return problems


# ---------------------------------------------------------------------------------------------------- update

def title_of(info: dict) -> str:
  if PR_SUBJECT.match(info["subject"]) and info["subject"].startswith("Merge pull request") and info["body"]:
    return info["body"].splitlines()[0].strip()
  m = re.match(r"^Merge #\d+:\s*(.*)$", info["subject"])
  return m.group(1).strip() if m else info["subject"].strip()


def change_row(sha: str, versions: dict[str, str] | None, repo: str | None, token: str | None,
               cwd: Path | None = None) -> dict:
  info = commit_info(sha, cwd)
  parent = info["parents"][0] if info["parents"] else None
  files = changed_files(sha, parent, cwd)
  m = PR_SUBJECT.match(info["subject"])
  pr = int(m.group(1)) if m else None
  if pr is None and len(info["parents"]) < 2:
    m2 = re.search(r"\(#(\d+)\)\s*$", info["subject"])  # a squash merge names its PR at the end
    pr = int(m2.group(1)) if m2 else None
  kind = "change" if (len(info["parents"]) > 1 or pr) else "direct"
  row = {"kind": kind, "commit": info["commit"], "parent": parent, "date": info["date"], "pr": pr,
         "title": title_of(info), "files": len(files),
         "decisions": sorted(set(DECISION.findall(info["subject"] + "\n" + info["body"])))}
  if pr and repo and token:
    try:
      row["github"] = github_meta(repo, pr, token)
      row["title"] = row["github"]["title"]
    except Exception as e:  # noqa: BLE001 - a missing API answer is recorded, never fatal
      row["github_error"] = str(e)[:200]
  touched = sorted({WP_FILE.search(f).group(1) for f in files if f.startswith("assurance/") and WP_FILE.search(f)})
  docs: dict[str, str | None] = {d: None for d in touched}
  if versions is not None:
    editorial = EDITORIAL in (row.get("github") or {}).get("labels", [])
    present = documents_at(sha, cwd)
    for d in touched:
      if d in present:
        base = versions.get(d) or header_version(sha, present[d], cwd)
        versions[d] = docs[d] = bump(base, "editorial" if editorial else "content")
    if parent and APPROVALS in files:
      before = {approval_key(a) for a in approvals_at(parent, cwd)}
      for a in approvals_at(sha, cwd):
        if approval_key(a) in before:
          continue
        for d in a.get("documents") or []:
          if d in present:
            versions[d] = docs[d] = bump(versions.get(d) or header_version(sha, present[d], cwd), "approval")
        row.setdefault("approvals", []).append({"gate": a.get("gate"), "record": a.get("record")})
  row["documents"] = docs
  row["exceptions"] = exceptions_for(row)
  return row


def seed_row(sha: str, cwd: Path | None = None) -> dict:
  info = commit_info(sha, cwd)
  docs = {d: header_version(sha, p, cwd) for d, p in sorted(documents_at(sha, cwd).items())}
  return {"kind": "seed", "commit": info["commit"], "parent": None, "date": info["date"], "pr": None,
          "title": f"Ledger starts: {len(docs)} work products take the version in their header at this commit",
          "files": 0, "decisions": ["DQ-441", "DQ-442"], "documents": docs, "exceptions": []}


def update(path: Path, ref: str = "HEAD", repo: str | None = None, token: str | None = None,
           cwd: Path | None = None) -> int:
  rows = load(path)
  problems = verify(rows)
  if problems:
    raise SystemExit("ledger chain broken, not appending:\n  " + "\n  ".join(problems))
  commits = first_parent_commits(ref, cwd)
  new: list[dict] = []
  if not rows:
    # first run: the history before the ledger (git data only), then the seed row at the tip
    for sha in commits:
      new.append(change_row(sha, None, None, None, cwd))
    new.append(seed_row(commits[-1], cwd))
  else:
    done = {r["commit"] for r in rows}
    last = next(r["commit"] for r in reversed(rows))
    if last not in commits:
      raise SystemExit(f"last ledger commit {last[:8]} is not in the history of {ref}; history was rewritten")
    versions = current_versions(rows)
    for sha in commits[commits.index(last) + 1:]:
      if sha not in done:
        new.append(change_row(sha, versions, repo, token, cwd))
  append(path, rows, new)
  return len(new)


# ---------------------------------------------------------------------------------------------------- views

def write_xlsx(rows: list[dict], out: Path) -> None:
  import openpyxl
  from openpyxl.styles import Font, PatternFill

  wb = openpyxl.Workbook()
  bold = Font(bold=True)
  head_fill = PatternFill("solid", fgColor="F1F5F9")

  def sheet(ws, header, data):
    ws.append(header)
    for c in ws[1]:
      c.font, c.fill = bold, head_fill
    for r in data:
      ws.append(r)
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = ws.dimensions

  ws = wb.active
  ws.title = "Changes"
  sheet(ws, ["Row", "Date", "Kind", "PR", "Change", "Class", "Documents -> version", "Files", "Checks",
             "Approved by", "Merged by", "Decisions", "Commit", "Row hash"],
        [[r["seq"], r["date"][:10], r["kind"], r["pr"], r["title"],
          ", ".join(l for l in (r.get("github") or {}).get("labels", []) if l in CLASSES + (EDITORIAL,)),
          ", ".join(f"{d} {v}" if v else d for d, v in r["documents"].items()) if r["kind"] != "seed"
          else f"{len(r['documents'])} work products seeded",
          r["files"],
          (lambda c: f"{c['success']}/{c['total']}" + (f", {c['failure']} failed" if c["failure"] else ""))(
              r["github"]["checks"]) if r.get("github") else "",
          ", ".join((r.get("github") or {}).get("approved_by", [])),
          (r.get("github") or {}).get("merged_by") or "",
          ", ".join(r["decisions"]), r["commit"][:10], r["hash"][:12]] for r in reversed(rows)])

  last_change: dict[str, dict] = {}
  for r in rows:
    for d in r["documents"]:
      last_change[d] = r
  sheet(wb.create_sheet("Documents"), ["Work product", "Version", "Status", "Last changed", "By row", "PR"],
        [[d, v, "Draft" if v.startswith("0.") else "Approved", last_change[d]["date"][:10], last_change[d]["seq"],
          last_change[d]["pr"]] for d, v in current_versions(rows).items()])
  sheet(wb.create_sheet("Exceptions"), ["Row", "Date", "PR", "Change", "Exception", "Commit"],
        [[r["seq"], r["date"][:10], r["pr"], r["title"], e, r["commit"][:10]]
         for r in reversed(rows) for e in r["exceptions"]])
  for ws in wb.worksheets:
    for col in ws.columns:
      width = max(len(str(c.value or "")) for c in col[:200])
      ws.column_dimensions[col[0].column_letter].width = min(max(8, width + 2), 70)
  wb.save(out)


# ---------------------------------------------------------------------------------------------------- PR rule

def check_labels(event_path: Path) -> list[str]:
  event = json.loads(event_path.read_text())
  labels = {label["name"] for label in event.get("pull_request", {}).get("labels", [])}
  if EDITORIAL in labels and labels & set(SAFETY_CLASSES):
    return [f"`{EDITORIAL}` cannot be combined with {', '.join(sorted(labels & set(SAFETY_CLASSES)))}: a "
            "safety-class change is a content change (Y), never an editorial one (Z) (WP-P-04 §5)"]
  return []


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("command", choices=["update", "verify", "versions", "xlsx", "check-labels"])
  ap.add_argument("--ledger", type=Path)
  ap.add_argument("--ref", default=None)
  ap.add_argument("--repo")
  ap.add_argument("--doc")
  ap.add_argument("--out", type=Path)
  ap.add_argument("--event", type=Path)
  a = ap.parse_args(argv)
  if a.command == "check-labels":
    problems = check_labels(a.event)
    print("\n".join(problems) or "labels ok")
    return 1 if problems else 0
  if a.ledger is None:
    ap.error("--ledger is required")
  if a.command == "update":
    n = update(a.ledger, a.ref or "HEAD", a.repo, os.environ.get("GITHUB_TOKEN"))
    print(f"appended {n} row(s); ledger has {len(load(a.ledger))}")
    return 0
  rows = load(a.ledger)
  if a.command == "verify":
    problems = verify(rows, a.ref)
    print("\n".join(problems) or f"ledger ok: {len(rows)} rows, chain intact")
    return 1 if problems else 0
  if a.command == "versions":
    v = current_versions(rows)
    if a.doc:
      if a.doc not in v:
        print(f"{a.doc}: not in the ledger", file=sys.stderr)
        return 1
      print(v[a.doc])
    else:
      for d, ver in v.items():
        print(f"{d}\t{ver}")
    return 0
  if a.command == "xlsx":
    write_xlsx(rows, a.out)
    print(f"wrote {a.out}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
