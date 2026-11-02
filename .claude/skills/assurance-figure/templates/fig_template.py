#!/usr/bin/env python3
"""Draw <WP-ID> Figure <N-n>, <what it shows in one line> (<fig-xx-n-n-slug>.svg).

<Two or three lines: what the figure shows, where every label and number comes from (the source file and §), and
what makes the build fail when the source changes. Say what it is NOT, if a reader could mistake it for evidence.>

One tile per row of the <table> in <SOURCE> §<n>, grouped by its <GROUP_COL> column and coloured by <STATUS_COL>.
Template from .claude/skills/assurance-figure; replace every <...> and the CONFIG block, then delete this line.

    python3 fig_xx_topic.py            # write the SVG next to this file
    python3 fig_xx_topic.py --check    # fail if the source changed shape or the SVG is stale

Standard library only. Output is deterministic.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p / "assurance" / "trace").is_dir())
sys.path.insert(0, str(REPO / "assurance" / "01-management" / "figures"))
from figkit import (AMBER, AMBER_BG, FAINT, GREEN, GREEN_BG, GREY_BG, HAIR, INK, MUTED, RED,
                    RED_BG, col, fit, header, legend, plain, rect, section, svg, table, text)
import figkit
sys.path.insert(0, str(REPO / "assurance" / "trace" / "tools"))
import terms

# ---------------------------------------------------------------- CONFIG: the source and what to read from it
SOURCE = REPO / "assurance" / "06-validation" / "README.md"          # <the record the figure is drawn from>
HEADING = "## Work products"                                       # <the § that holds the table>
FIRST = "ID"                                                       # <first header cell, to pick the right table>
ID_COL, LABEL_COL, GROUP_COL, STATUS_COL = "ID", "Work product", "Gate", "Status"
OUT = "fig-xx-1-1-template.svg"                                    # <fig-<wp>-<section>-<n>-<slug>.svg>
NUMBER, TITLE, REF = "X-1", "<Title>", "<WP-ID §n>"
SUBTITLE = "<One line: what to read off it.>"
W = 1200
# Status words as written in the source -> (label, stroke, fill). An unknown word fails the build, so a new status
# is sorted on purpose rather than drawn in a default colour.
STATUS = {
  "Draft": ("draft", AMBER, AMBER_BG),
  "In review": ("in review", "#4F46E5", "#EEF2FF"),
  "Approved": ("approved", GREEN, GREEN_BG),
  "Not started": ("not started", FAINT, GREY_BG),
  "Blocked": ("blocked", RED, RED_BG),
}
# ---------------------------------------------------------------- end of CONFIG


class FigureError(Exception):
  """The source no longer has the shape this figure reads."""


figkit.FigureError = FigureError   # figkit's parsers raise its FigureError; make it ours so callers catch one type


def parse(md: str) -> list[dict]:
  """The rows to draw, each {id, label, group, status}. Raises FigureError on anything unexpected."""
  head, rows = table(section(md, HEADING), FIRST)
  ci, cl, cg, cs = (col(head, c) for c in (ID_COL, LABEL_COL, GROUP_COL, STATUS_COL))
  out, seen = [], set()
  for r in rows:
    rid = plain(r[ci])
    if rid in seen:
      raise FigureError(f"{rid} listed twice")
    seen.add(rid)
    status = plain(r[cs])
    if status not in STATUS:
      raise FigureError(f"{rid}: status {status!r} is not in STATUS; add it with its colour")
    out.append({"id": rid, "label": plain(r[cl]), "group": plain(r[cg]), "status": status})
  if not out:
    raise FigureError("the table has no rows")
  return out


def draw(rows: list[dict]) -> str:
  groups: dict[str, list[dict]] = {}
  for r in rows:
    groups.setdefault(r["group"], []).append(r)
  body = header(W, NUMBER, TITLE, SUBTITLE, REF)
  used = [s for s in STATUS if any(r["status"] == s for r in rows)]
  leg, _ = legend(40, 110, [(STATUS[s][2], STATUS[s][1], f"{STATUS[s][0]} ({sum(r['status'] == s for r in rows)})")
                            for s in used])
  body += leg
  y, tile_w, tile_h, gap = 134, 266, 58, 12
  per_row = (W - 80 - 90 + gap) // (tile_w + gap)
  for g in sorted(groups):
    items = groups[g]
    body.append(text(40, y + 34, g, size=14, weight=700))
    for i, r in enumerate(items):
      x = 130 + (i % per_row) * (tile_w + gap)
      ty = y + (i // per_row) * (tile_h + gap)
      label, stroke, fill = STATUS[r["status"]]
      body.append(rect(x, ty, tile_w, tile_h, fill=fill, stroke=stroke, rx=8))
      body.append(text(x + 12, ty + 22, r["id"], size=12, weight=700, fill=INK))
      body.append(text(x + tile_w - 12, ty + 22, label, size=10, fill=stroke, weight=600, anchor="end"))
      body.append(text(x + 12, ty + 42, fit(r["label"], tile_w - 24, 11), size=11, fill=MUTED))
    y += ((len(items) - 1) // per_row + 1) * (tile_h + gap) + 14
    body.append(f'<line x1="40" y1="{y - 7}" x2="{W - 40}" y2="{y - 7}" stroke="{HAIR}" stroke-width="1"/>')
  foot, y = terms.svg_footer(body, 40, y + 14, W - 80)
  body += foot
  body.append(text(40, y + 6, f"Drawn from {SOURCE.relative_to(REPO).as_posix()} {HEADING.lstrip('# ')} by " +
                   f"{Path(__file__).name}; CI fails if it is stale.", size=10, fill=FAINT))
  desc = (f"{len(rows)} rows of {SOURCE.name} in {len(groups)} groups: " +
          "; ".join(f"{sum(r['status'] == s for r in rows)} {STATUS[s][0]}" for s in used))
  return svg(W, int(y + 24), f"Figure {NUMBER} · {TITLE}", desc, body)


def build() -> dict[str, str]:
  return {OUT: draw(parse(SOURCE.read_text(encoding="utf-8")))}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except FigureError as e:
    print(f"{Path(__file__).stem}: {e}", file=sys.stderr)
    return 1
  rel = HERE.relative_to(REPO).as_posix()
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"{rel}/{n} is stale; run {Path(__file__).name}", file=sys.stderr)
    if not stale:
      print(f"{Path(__file__).stem}: {len(outputs)} figure(s) current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote {rel}/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
