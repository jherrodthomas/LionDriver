#!/usr/bin/env python3
"""Build the GitHub wiki pages from wiki/ and check them.

The wiki is kept in the repository under wiki/ so that every page is reviewed by pull request like
everything else. This tool turns that folder into what the GitHub wiki repository expects:

  * page links written as `Name.md` (so they work when the folder is read on GitHub) become `Name`,
    which is how the wiki resolves a link to another page;
  * repository links written as `../path` become absolute links to that path on the synced branch, and an
    image written as `![alt](../path)` becomes the raw file address, which is what the wiki renders;
  * `{{REPO}}`, `{{BRANCH}}`, `{{SYNC_COMMIT}}` and `{{SYNC_DATE}}` are filled in;
  * `{{MERGE_LOG}}` becomes the list of pull requests merged into the synced branch, newest first,
    read from the merge commits in the checkout (the Session log page);
  * the infographics of infographics.py are rendered from the records and written next to the pages, so a
    page embeds one as `![alt](decision-register.svg)`; the animations of animations.py (from the requirement
    texts), the fault tree figures of fta_animations.py (from WP-A-04), the safety-case explainers of
    case_animations.py (from assurance/case-records), the hazard-to-test explainers of h2t_animations.py (from the
    concept, system, software and hardware work products), the hardware figures of hw_animations.py (from
    the FMEDA and WP-A-02), the after-release figures of p7_animations.py (from WP-O-01, WP-O-02, WP-O-04) and
    the SOTIF figures of sotif_animations.py (from WP-C-03…07, WP-V-01, WP-V-02, WP-V-04 and the case records) and
    the cybersecurity figures of cyber_animations.py (from WP-C-09, WP-C-10, hatara/, WP-O-05 and WP-K-03),
    the AI figures of ai_animations.py (from WP-C-11, WP-M-10 and WP-W-10), the ASPICE figures of
    aspice_animations.py (from WP-M-13, the trace map and the process model) and the integrated-standards figures of
    integrated_animations.py (from the process model, WP-M-00, WP-C-03, WP-C-09, the trace map and the case records)
    and the how-it-works figures of how_animations.py (from WP-S-02, WP-S-03, WP-S-04, WP-W-09 and the TSR list)
    and the ASIL decomposition figures of dec_animations.py (from WP-A-01, WP-H-04 and WP-S-02)
    and the CAN and end-to-end figures of comms_animations.py (from WP-S-05 and the TSR list)
    likewise: a drawn phrase that is no longer in its source is a build problem;
  * wiki/README.md, which describes the folder, is not published.

It also checks the pages: every page is reachable from _Sidebar.md, every page link names a page that
exists, and every repository link names a file or folder that exists in the checkout.

Usage: python3 tools/wiki/build_wiki.py [--out DIR] [--repo OWNER/NAME] [--branch NAME]
                                        [--commit SHA] [--date YYYY-MM-DD] [--src DIR]
Exit status 1 and one line per problem when a check fails. Without --out the pages are only checked.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import animations
import case_animations
import fta_animations
import h2t_animations
import hw_animations
import p7_animations
import sotif_animations
import cyber_animations
import ai_animations
import aspice_animations
import integrated_animations
import how_animations
import dec_animations
import comms_animations
import infographics

ROOT = HERE.parents[1]
SRC = ROOT / "wiki"

EXCLUDED = {"README.md"}
SPECIAL = {"_Sidebar.md", "_Footer.md"}
LINK = re.compile(r"(!?\[[^\]]*\]\()([^)\s]+)(\))")
PLACEHOLDER = re.compile(r"\{\{(REPO|BRANCH|SYNC_COMMIT|SYNC_DATE|MERGE_LOG)\}\}")
MERGE_SUBJECT = re.compile(r"^Merge pull request #(\d+) from ")
MERGE_LOG_LIMIT = 120
NO_MERGE_LOG = "_No merge history is available in this checkout._"


def git_merges(root: Path, limit: int = MERGE_LOG_LIMIT) -> list[tuple[str, int, str, str]]:
  """(date, pull request number, title, short sha) for each pull request merged on the checked-out branch's
  first-parent line, newest first.

  GitHub writes "Merge pull request #N from ..." as the subject of a pull request's merge commit and the pull
  request's title as its body. Other merge commits (a branch merge, or the synthetic "Merge X into Y" commit a
  pull request is checked out at in CI) are not pull requests and are left out. Returns [] when the root is not
  a git checkout or has no merge history."""
  try:
    out = subprocess.run(
      ["git", "-C", str(root), "log", "--merges", "--first-parent", "--date=short", f"-n{limit}",
       "--format=%x1e%ad%x1f%h%x1f%s%x1f%b"],
      capture_output=True, text=True, check=True, timeout=30).stdout
  except (OSError, subprocess.SubprocessError):
    return []
  entries = []
  for record in out.split("\x1e"):
    if not record.strip():
      continue
    parts = record.split("\x1f", 3)
    while len(parts) < 4:
      parts.append("")
    date, sha, subject, body = (p.strip() for p in parts)
    m = MERGE_SUBJECT.match(subject)
    if not m:
      continue
    title = next((line.strip() for line in body.splitlines() if line.strip()), subject)
    entries.append((date, int(m.group(1)), title, sha))
  return entries


def render_merge_log(entries: list[tuple[str, int, str, str]], repo: str) -> str:
  if not entries:
    return NO_MERGE_LOG
  lines: list[str] = []
  current = None
  for date, number, title, _sha in entries:
    if date != current:
      lines.append(f"\n### {date}\n")
      current = date
    lines.append(f"- [#{number}](https://github.com/{repo}/pull/{number}) {title}")
  return "\n".join(lines).strip()


def pages(src: Path) -> list[Path]:
  return sorted(p for p in src.glob("*.md") if p.name not in EXCLUDED)


def split_target(target: str) -> tuple[str, str]:
  path, sep, anchor = target.partition("#")
  return path, (sep + anchor if sep else "")


def rewrite(text: str, page: Path, src: Path, root: Path, values: dict[str, str], problems: list[str]) -> str:
  names = {p.name for p in pages(src)}

  def link(m: re.Match) -> str:
    before, target, after = m.groups()
    path, anchor = split_target(target)
    if path.startswith(("http://", "https://", "mailto:")) or (path == "" and anchor):
      return m.group(0)
    if path.startswith("../"):
      rel = path[3:]
      if not (root / rel).exists():
        problems.append(f"{page.name}: repository link target does not exist: {rel}")
      if before.startswith("!"):
        # An image: the wiki renders it only from the raw file address, never from the blob page.
        return f"{before}https://raw.githubusercontent.com/{values['REPO']}/{values['BRANCH']}/{rel}{after}"
      kind = "tree" if (root / rel).is_dir() else "blob"
      return f"{before}https://github.com/{values['REPO']}/{kind}/{values['BRANCH']}/{rel}{anchor}{after}"
    if path.endswith(".md"):
      if path not in names:
        problems.append(f"{page.name}: page link target does not exist: {path}")
      return f"{before}{path[:-3]}{anchor}{after}"
    if path in infographics.NAMES or path in animations.NAMES or path in fta_animations.NAMES or path in case_animations.NAMES or path in h2t_animations.NAMES or path in hw_animations.NAMES or path in p7_animations.NAMES or path in sotif_animations.NAMES or path in cyber_animations.NAMES or path in ai_animations.NAMES or path in aspice_animations.NAMES or path in integrated_animations.NAMES or path in how_animations.NAMES or path in dec_animations.NAMES or path in comms_animations.NAMES:
      return m.group(0)  # a generated figure, written next to the pages by build()
    problems.append(f"{page.name}: link is neither a page (Name.md), a repository path (../path), a generated figure nor a URL: {target}")
    return m.group(0)

  text = LINK.sub(link, text)
  return PLACEHOLDER.sub(lambda m: values[m.group(1)], text)


def check_sidebar(src: Path, problems: list[str]) -> None:
  sidebar = src / "_Sidebar.md"
  if not sidebar.exists():
    problems.append("_Sidebar.md is missing")
    return
  linked = {split_target(m.group(2))[0] for m in LINK.finditer(sidebar.read_text(encoding="utf-8"))}
  for p in pages(src):
    if p.name in SPECIAL:
      continue
    if p.name not in linked:
      problems.append(f"{p.name}: not linked from _Sidebar.md")


def build(src: Path = SRC, out: Path | None = None, root: Path = ROOT, *, repo: str = "jherrodthomas/LionDriver",
          branch: str = "liondriver-dev", commit: str = "unsynced", date: str | None = None) -> list[str]:
  problems: list[str] = []
  values = {"REPO": repo, "BRANCH": branch, "SYNC_COMMIT": commit[:7] if commit != "unsynced" else commit,
            "SYNC_DATE": date or dt.date.today().isoformat(),
            "MERGE_LOG": render_merge_log(git_merges(root), repo)}
  if not (src / "Home.md").exists():
    problems.append("Home.md is missing")
  check_sidebar(src, problems)
  if (root / animations.TSC).exists():
    problems += animations.problems(root)
  if (root / fta_animations.FTA).exists():
    problems += fta_animations.problems(root)
  if (root / case_animations.CASE / "claims").exists():
    problems += case_animations.problems(root)
  if (root / h2t_animations.C03).exists():
    problems += h2t_animations.problems(root)
  if (root / hw_animations.FMEDA).exists():
    problems += hw_animations.problems(root)
  if (root / p7_animations.O02).exists():
    problems += p7_animations.problems(root)
  if (root / sotif_animations.C06).exists():
    problems += sotif_animations.problems(root)
  if (root / cyber_animations.C09).exists():
    problems += cyber_animations.problems(root)
  if (root / ai_animations.C11).exists():
    problems += ai_animations.problems(root)
  if (root / aspice_animations.M13).exists():
    problems += aspice_animations.problems(root)
  if (root / integrated_animations.REG).exists():
    problems += integrated_animations.problems(root)
  if (root / how_animations.W09).exists():
    problems += how_animations.problems(root)
  if (root / dec_animations.A01).exists():
    problems += dec_animations.problems(root)
  if (root / comms_animations.S05).exists():
    problems += comms_animations.problems(root)
  built: dict[str, str] = {}
  for page in pages(src):
    built[page.name] = rewrite(page.read_text(encoding="utf-8"), page, src, root, values, problems)
  if out is not None and not problems:
    out.mkdir(parents=True, exist_ok=True)
    for name, text in built.items():
      (out / name).write_text(text, encoding="utf-8")
    if (root / "assurance" / "01-management" / "decisions" / "register.yaml").exists():
      infographics.write_all(out, root)
    if (root / animations.TSC).exists():
      animations.write_all(out, root)
    if (root / fta_animations.FTA).exists():
      fta_animations.write_all(out, root)
    if (root / case_animations.CASE / "claims").exists():
      case_animations.write_all(out, root)
    if (root / h2t_animations.C03).exists():
      h2t_animations.write_all(out, root)
    if (root / hw_animations.FMEDA).exists():
      hw_animations.write_all(out, root)
    if (root / p7_animations.O02).exists():
      p7_animations.write_all(out, root)
    if (root / sotif_animations.C06).exists():
      sotif_animations.write_all(out, root)
    if (root / cyber_animations.C09).exists():
      cyber_animations.write_all(out, root)
    if (root / ai_animations.C11).exists():
      ai_animations.write_all(out, root)
    if (root / aspice_animations.M13).exists():
      aspice_animations.write_all(out, root)
    if (root / integrated_animations.REG).exists():
      integrated_animations.write_all(out, root)
    if (root / how_animations.W09).exists():
      how_animations.write_all(out, root)
    if (root / dec_animations.A01).exists():
      dec_animations.write_all(out, root)
    if (root / comms_animations.S05).exists():
      comms_animations.write_all(out, root)
  return problems


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--src", type=Path, default=SRC)
  ap.add_argument("--out", type=Path, default=None, help="write the built pages here (omit to only check)")
  ap.add_argument("--repo", default="jherrodthomas/LionDriver")
  ap.add_argument("--branch", default="liondriver-dev")
  ap.add_argument("--commit", default="unsynced")
  ap.add_argument("--date", default=None)
  args = ap.parse_args(argv)
  problems = build(args.src, args.out, args.src.resolve().parent, repo=args.repo, branch=args.branch,
                   commit=args.commit, date=args.date)
  for p in problems:
    print(p)
  if problems:
    return 1
  n = len(pages(args.src))
  print(f"wiki: {n} pages {'built into ' + str(args.out) if args.out else 'checked'}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
