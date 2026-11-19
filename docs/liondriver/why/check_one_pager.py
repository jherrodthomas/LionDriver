#!/usr/bin/env python3
"""Check the "Why LionDriver exists" one-pager against its sources.

Every quotation and number on why-liondriver-exists.html is listed in FACTS with the record it comes from; the check
fails when the page no longer carries it or the source no longer says it. It also checks that the printed PDF is one
page and newer than the HTML it was printed from (by git commit order, not file times). Re-print with render.cjs.

    python3 docs/liondriver/why/check_one_pager.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CASE = REPO / "docs/safety/field-monitoring/cases/FI-2026-001-nhtsa-pe26007"
PAGE = HERE / "why-liondriver-exists.html"
PDF = HERE / "why-liondriver-exists.pdf"

# (text on the page, source file, text that must be in the source)
FACTS = [
  ("21 September 2026", CASE / "REPORT.md", "on **2026-09-21**"),
  ('"reportedly struck stopped or slowly moving vehicles within the same travel lane"', CASE / "REPORT.md",
   "reportedly struck stopped or slowly moving vehicles within the same travel lane"),
  ('"powered on or engaged in multiple crashes"', CASE / "REPORT.md", "powered on or engaged in multiple crashes"),
  ('"may not have adequately detected or responded to the in-lane vehicles"', CASE / "REPORT.md",
   "may not have adequately detected or responded to the in-lane vehicles"),
  ('"consider the shared components between openpilot and the fork"', CASE / "REPORT.md",
   "consider the shared components between openpilot and the fork"),
  ("<b>5</b>", CASE / "REPORT.md", "five (5) crashes"),
  ('<b class="red">3</b>', CASE / "REPORT.md", "three (3) fatalities"),
  ('<b class="red">11</b>', CASE / "REPORT.md", "eleven (11) other individuals"),
  ("<b>30,000</b>", CASE / "REPORT.md", "30,000 (Estimated)"),
  ("capped at -3.5&nbsp;m/s²", CASE / "RCA.md", "capped at **-3.5 m/s²**"),
  ("5 s eyes-off before the first alert", CASE / "RCA.md", "tolerates **5 s**"),
  ("turns the stock pre-collision system off", CASE / "RCA.md", "`PCS_OFF = 1`"),
  ("<b>144 m</b>", CASE / "RCA.md", "| 108 km/h (30 m/s) | 144 m | 71 m |"),
  ("full braking needs 71 m", CASE / "RCA.md", "| 108 km/h (30 m/s) | 144 m | 71 m |"),
  ("LionDriver started 9 Oct 2026", None, None),
]
FIRST_COMMIT = "8b8c6aefc34ea1e3ca3cf0938927c08b6a35e85c"


def norm(text: str) -> str:
  return re.sub(r"\s+", " ", text)


def git(*args: str) -> str:
  return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


def main() -> int:
  page = norm(PAGE.read_text(encoding="utf-8"))
  errors = []
  for on_page, source, in_source in FACTS:
    if on_page not in page:
      errors.append(f"page no longer carries {on_page!r}; update FACTS with the change")
    if source and norm(in_source) not in norm(source.read_text(encoding="utf-8")):
      errors.append(f"{source.relative_to(REPO)} no longer says {in_source!r}; correct the one-pager")
  started = git("log", "-1", "--format=%ad", "--date=format:%-d %b %Y", FIRST_COMMIT)
  if started and f"LionDriver started {started}" not in page:
    errors.append(f"LionDriver's first commit is dated {started}; the page says otherwise")
  pdf = PDF.read_bytes()
  if len(re.findall(rb"/Type\s*/Page\b", pdf)) != 1:
    errors.append("the PDF is not exactly one page; re-print with render.cjs")
  last_html, last_pdf = git("log", "-1", "--format=%ct", "--", str(PAGE)), git("log", "-1", "--format=%ct", "--", str(PDF))
  if last_html and last_pdf and int(last_html) > int(last_pdf):
    errors.append("the HTML changed after the PDF was last printed; re-print with render.cjs")
  for e in errors:
    print(f"check_one_pager: {e}", file=sys.stderr)
  if not errors:
    print(f"check_one_pager: {len(FACTS)} facts match their sources; one page")
  return 1 if errors else 0


if __name__ == "__main__":
  sys.exit(main())
