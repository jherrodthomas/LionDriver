#!/usr/bin/env python3
"""Build the GitHub wiki pages from wiki/ and check them.

The wiki is kept in the repository under wiki/ so that every page is reviewed by pull request like
everything else. This tool turns that folder into what the GitHub wiki repository expects:

  * page links written as `Name.md` (so they work when the folder is read on GitHub) become `Name`,
    which is how the wiki resolves a link to another page;
  * repository links written as `../path` become absolute links to that path on the synced branch;
  * `{{REPO}}`, `{{BRANCH}}`, `{{SYNC_COMMIT}}` and `{{SYNC_DATE}}` are filled in;
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
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / "wiki"

EXCLUDED = {"README.md"}
SPECIAL = {"_Sidebar.md", "_Footer.md"}
LINK = re.compile(r"(!?\[[^\]]*\]\()([^)\s]+)(\))")
PLACEHOLDER = re.compile(r"\{\{(REPO|BRANCH|SYNC_COMMIT|SYNC_DATE)\}\}")


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
      kind = "tree" if (root / rel).is_dir() else "blob"
      return f"{before}https://github.com/{values['REPO']}/{kind}/{values['BRANCH']}/{rel}{anchor}{after}"
    if path.endswith(".md"):
      if path not in names:
        problems.append(f"{page.name}: page link target does not exist: {path}")
      return f"{before}{path[:-3]}{anchor}{after}"
    problems.append(f"{page.name}: link is neither a page (Name.md), a repository path (../path) nor a URL: {target}")
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
            "SYNC_DATE": date or dt.date.today().isoformat()}
  if not (src / "Home.md").exists():
    problems.append("Home.md is missing")
  check_sidebar(src, problems)
  built: dict[str, str] = {}
  for page in pages(src):
    built[page.name] = rewrite(page.read_text(encoding="utf-8"), page, src, root, values, problems)
  if out is not None and not problems:
    out.mkdir(parents=True, exist_ok=True)
    for name, text in built.items():
      (out / name).write_text(text, encoding="utf-8")
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
