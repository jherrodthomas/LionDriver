#!/usr/bin/env python3
"""Check the README and the LionDriver documentation pages for broken links and unsafe images.

For each page:
  L1  every relative link (Markdown or HTML href/src) points to an existing file or directory
  L2  every #anchor resolves to a heading in the target Markdown file (GitHub slug rules)
  L3  every referenced SVG parses, has a <title>, and contains no script, event handler or
      external reference (GitHub serves SVGs as images; external content would not load)

Absolute URLs are not fetched. Links inside code spans and fenced code blocks are ignored.

Usage: python3 assurance/case/tools/check_pages.py [PAGE ...]
Default pages: README.md and docs/liondriver/*.md. Exit code 0 when clean, 1 otherwise.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MD_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HTML_LINK = re.compile(r"""\b(?:href|src)=["']([^"']+)["']""")
FENCE = re.compile(r"^\s*```")
CODE_SPAN = re.compile(r"`[^`]*`")
SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)
SVG_NS = "{http://www.w3.org/2000/svg}"


def slug(heading: str) -> str:
  text = re.sub(r"<[^>]+>", "", heading)
  text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
  text = text.replace("`", "").strip().lower()
  text = re.sub(r"[^\w\- ]", "", text)
  return text.replace(" ", "-")


def anchors(md: Path) -> set[str]:
  found: set[str] = set()
  counts: dict[str, int] = {}
  in_fence = False
  for line in md.read_text(encoding="utf-8").splitlines():
    if FENCE.match(line):
      in_fence = not in_fence
      continue
    m = re.match(r"^#{1,6}\s+(.*?)\s*#*\s*$", line)
    if m and not in_fence:
      base = slug(m.group(1))
      n = counts.get(base, 0)
      counts[base] = n + 1
      found.add(base if n == 0 else f"{base}-{n}")
  return found


def check_svg(path: Path) -> list[str]:
  problems = []
  try:
    root = ET.parse(path).getroot()
  except ET.ParseError as e:
    return [f"not well-formed XML: {e}"]
  if root.find(f"{SVG_NS}title") is None:
    problems.append("no <title> for accessibility")
  for el in root.iter():
    if el.tag == f"{SVG_NS}script":
      problems.append("contains <script>")
    for attr, value in el.attrib.items():
      if attr.startswith("on"):
        problems.append(f"event handler {attr}")
      if attr.endswith("href") and SCHEME.match(value):
        problems.append(f"external reference {value}")
  return problems


def check_page(page: Path) -> tuple[int, list[str]]:
  errors, total = [], 0
  in_fence = False
  for n, line in enumerate(page.read_text(encoding="utf-8").splitlines(), 1):
    if FENCE.match(line):
      in_fence = not in_fence
      continue
    if in_fence:
      continue
    text = CODE_SPAN.sub("", line)
    for target in [m.group(1) for m in MD_LINK.finditer(text)] + [m.group(1) for m in HTML_LINK.finditer(text)]:
      if SCHEME.match(target):
        continue
      total += 1
      where = f"{page.relative_to(REPO_ROOT)}:{n}: {target}"
      path_part, _, anchor = target.partition("#")
      dest = (page.parent / path_part).resolve() if path_part else page
      if not dest.exists():
        errors.append(f"[L1] {where}: target does not exist")
        continue
      if anchor and dest.suffix == ".md" and anchor not in anchors(dest):
        errors.append(f"[L2] {where}: no heading with anchor #{anchor}")
      if dest.suffix == ".svg":
        errors += [f"[L3] {where}: {p}" for p in check_svg(dest)]
  return total, errors


def main(argv: list[str]) -> int:
  pages = [Path(a).resolve() for a in argv] or [REPO_ROOT / "README.md", *sorted((REPO_ROOT / "docs" / "liondriver").glob("*.md"))]
  total, errors = 0, []
  for page in pages:
    t, e = check_page(page)
    total += t
    errors += e
  for e in errors:
    print(e)
  print(f"{len(pages)} pages, {total} relative links and images checked, {len(errors)} problem(s)")
  return 1 if errors else 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
