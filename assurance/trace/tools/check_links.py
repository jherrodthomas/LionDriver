#!/usr/bin/env python3
"""Check relative markdown links in the assurance tree (WP-P-04 documentation management).

Reports every relative link in assurance/**/*.md whose target file or directory does not
exist. Anchors, absolute URLs, and links inside code spans or fenced code blocks are ignored.

Usage: python3 assurance/trace/tools/check_links.py [ROOT]
Exit code 0 when no broken links, 1 otherwise.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[2]

LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)|!\[[^\]]*\]\(([^)\s]+)\)')
FENCE = re.compile(r'^\s*```')
CODE_SPAN = re.compile(r'`[^`]*`')
SCHEME = re.compile(r'^[a-z][a-z0-9+.-]*:', re.I)


def check(root: Path) -> tuple[int, list[str]]:
  total = 0
  broken = []
  for md in sorted(root.rglob('*.md')):
    in_fence = False
    for n, line in enumerate(md.read_text(encoding='utf-8').splitlines(), 1):
      if FENCE.match(line):
        in_fence = not in_fence
        continue
      if in_fence:
        continue
      for m in LINK.finditer(CODE_SPAN.sub('', line)):
        target = m.group(1) or m.group(2)
        if SCHEME.match(target) or target.startswith('#'):
          continue
        path = target.split('#', 1)[0]
        if not path:
          continue
        total += 1
        if not (md.parent / path).resolve().exists():
          broken.append(f'{md.relative_to(root)}:{n}: {target}')
  return total, broken


def main(argv: list[str]) -> int:
  root = Path(argv[0]).resolve() if argv else DEFAULT_ROOT
  total, broken = check(root)
  for b in broken:
    print(b)
  print(f'{total} relative links checked, {len(broken)} broken')
  return 1 if broken else 0


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
