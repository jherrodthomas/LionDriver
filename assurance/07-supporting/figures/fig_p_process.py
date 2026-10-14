#!/usr/bin/env python3
"""Draw the generated process figures of the supporting processes (WP-P-02, WP-P-03, WP-P-04, WP-P-10).

- Figure 5-1 of WP-P-02 (`fig-p02-5-1-change-swimlane.svg`): the §5 process table as a swimlane, one lane
  per role of the "Responsible" column (first role named; the rest of the cell is printed in the box), one
  row per step, with the decision step's reject/defer exit taken from the text under the table.
- Figure 5-1 of WP-P-03 (`fig-p03-5-1-problem-swimlane.svg`): the §5 workflow table as a swimlane, lanes
  from the "Who" column, one row per state label, the exit criterion as the box output.
- Figure 5-1 of WP-P-04 (`fig-p04-5-1-wp-lifecycle.svg`): the work-product status values of the
  assurance README (Skeleton to Baselined) with the §5 rule that moves a work product into each state,
  and below them the §7 review and approval steps that take a work product from In review to Approved.
- Figure 4-1 of WP-P-10 (`fig-p10-4-1-release-swimlane.svg`): the §4 procedure table as a swimlane, lanes
  from the "Responsible" column, with the new-RC loop of the text under the table.

Every box, lane and label is parsed from the work products. The few values that exist only in prose (the
reject/defer exit, the RC loop) carry the exact source text in SRC; `--check` fails if that text is no
longer in the document, or if a committed SVG is stale.

    python3 fig_p_process.py            # write the SVGs next to this script
    python3 fig_p_process.py --check    # fail if a source text changed or an SVG is stale

Standard library only. Output is deterministic. Drawing helpers and palette are shared with
assurance/01-management/figures/fig_m_management.py.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOC_DIR = HERE.parent
ASSURANCE = DOC_DIR.parent
sys.path.insert(0, str(ASSURANCE / "01-management" / "figures"))
from fig_m_management import (AMBER, AMBER_BG, CHIP, FigureError, GREEN, GREEN_BG, HAIR, INK, LINE, MUTED, SAFETY,
                              SAFETY_BG, SW, SW_BG, col, fit, header, path, pill, rect, section, svg, table, text, text_w)

WP_P_02 = DOC_DIR / "WP-P-02-change-management.md"
WP_P_03 = DOC_DIR / "WP-P-03-problem-resolution.md"
WP_P_04 = DOC_DIR / "WP-P-04-documentation-management.md"
WP_P_10 = DOC_DIR / "WP-P-10-release-management.md"
README = ASSURANCE / "README.md"

# Values that exist only in prose: (document, exact source text).
SRC = {
  "p02_kept": (WP_P_02, "A rejected or deferred CR stays as a closed or open issue with its reason; it is never deleted."),
  "p10_loop": (WP_P_10, "If any fix is needed after step 3, a new RC (`-rc2`) is tagged and steps 4–9 are repeated for the affected scope"),
}
# WP-P-10 §4 loop (from SRC p10_loop): back to the RC tag step, steps repeated
P10_LOOP_TO, P10_LOOP_FROM = 3, 9

W = 1280
X0, GUTTER = 40, 40           # left margin; gutter left of the lanes for loop arrows
LANE_TOP = 128                # top of the lane headers
LANE_HEAD = 40
BOX_PAD = 8
ROW_GAP = 30


class Step:
  def __init__(self, label: str, activity: str, output: str, who: str):
    self.label, self.activity, self.output = label, plain(activity), plain(output)
    self.lane, self.note = split_who(plain(who))


def plain(s: str) -> str:
  """Markdown cell text as plain text: links to their text, no code ticks or emphasis."""
  s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
  return re.sub(r"[`*]", "", s).strip()


def split_who(who: str) -> tuple[str, str]:
  """(lane, note): the first role named in a Responsible/Who cell, and the rest of the cell."""
  m = re.match(r"([^;/+(]+)(.*)$", who)
  lane, rest = m.group(1).strip(), m.group(2).strip()
  rest = re.sub(r"^[;/+]\s*", "", rest)
  if rest.startswith("(") and rest.endswith(")"):
    rest = rest[1:-1]
  return lane[:1].upper() + lane[1:], rest


def wrap(s: str, width: float, size: float, lines: int, bold: bool = False) -> list[str]:
  """s in at most `lines` lines no wider than width; the last line ends in an ellipsis if cut."""
  out, cur = [], ""
  words = s.split()
  for i, wd in enumerate(words):
    cand = (cur + " " + wd).strip()
    if text_w(cand, size, bold) <= width or not cur:
      cur = cand
      continue
    out.append(cur)
    cur = wd
    if len(out) == lines:
      out[-1] = fit(" ".join([out[-1]] + words[i:]), width, size, bold)
      return out
  if cur:
    out.append(cur)
  return out


def arrowhead(x: float, y: float, d: str, color: str = MUTED) -> str:
  """A filled arrowhead with its tip at (x, y), pointing d (down, right, left, up)."""
  pts = {"down": [(x - 5, y - 8), (x + 5, y - 8)], "up": [(x - 5, y + 8), (x + 5, y + 8)],
         "right": [(x - 8, y - 5), (x - 8, y + 5)], "left": [(x + 8, y - 5), (x + 8, y + 5)]}[d]
  (ax, ay), (bx, by) = pts
  return path(f"M{x:g} {y:g} L{ax:g} {ay:g} L{bx:g} {by:g} Z", stroke=color, sw=1, fill=color)


# ---------------------------------------------------------------- swimlane

@dataclass
class Exit:
  step: str        # label of the step the exit leaves
  title: str
  text: str


@dataclass
class Loop:
  from_step: str
  to_step: str
  text: str


def swimlane(number: str, title: str, subtitle: str, ref: str, steps: list[Step], badge: str,
             exits: list[Exit] | None = None, loop: Loop | None = None, foot: str = "") -> str:
  lanes: list[str] = []
  for s in steps:
    if s.lane not in lanes:
      lanes.append(s.lane)
  left = X0 + GUTTER
  lane_w = (W - X0 - left) / len(lanes)
  box_w = lane_w - 2 * 14
  body = header(W, number, title, subtitle, ref)
  inner = box_w - 2 * BOX_PAD

  # box geometry first (heights depend on wrapped text)
  layout = []
  y = LANE_TOP + LANE_HEAD + 22
  for s in steps:
    act = wrap(s.activity, inner, 11.5, 4)
    out = wrap("→ " + s.output, inner, 10, 2) if s.output else []
    note = wrap(s.note, inner, 9.5, 2) if s.note else []
    h = 30 + 15 * len(act) + (10 + 13 * len(out) if out else 0) + (4 + 12 * len(note) if note else 0) + 6
    x = left + lanes.index(s.lane) * lane_w + 14
    layout.append((s, x, y, h, act, out, note))
    y += h + ROW_GAP
  bottom = y - ROW_GAP + 22

  # lanes
  for i, lane in enumerate(lanes):
    lx = left + i * lane_w
    body.append(rect(lx, LANE_TOP, lane_w, bottom - LANE_TOP, fill=CHIP if i % 2 == 0 else "#FFFFFF", stroke=HAIR, rx=0, sw=1))
    body.append(rect(lx, LANE_TOP, lane_w, LANE_HEAD, fill=SW_BG, stroke=HAIR, rx=0, sw=1))
    body.append(text(lx + lane_w / 2, LANE_TOP + 25, fit(lane, lane_w - 12, 12.5, True), size=12.5, weight=700, fill=SW, anchor="middle"))

  # arrows between consecutive steps
  for (a, ax, ay, ah, *_), (_b, bx, by, *_) in zip(layout, layout[1:], strict=False):
    x1, y1, x2, y2 = ax + box_w / 2, ay + ah, bx + box_w / 2, by
    mid = y1 + ROW_GAP / 2
    d = f"M{x1:g} {y1:g} L{x1:g} {mid:g} L{x2:g} {mid:g} L{x2:g} {y2 - 7:g}" if x1 != x2 else f"M{x1:g} {y1:g} L{x2:g} {y2 - 7:g}"
    body.append(path(d))
    body.append(arrowhead(x2, y2, "down"))
    if a.label in {e.step for e in exits or []}:
      body.append(text(x1 + 6, y1 + 12, "accept", size=10, weight=700, fill=AMBER))

  boxes = {s.label: (x, y, h) for s, x, y, h, *_ in layout}
  decision = {e.step for e in exits or []}
  for s, x, y, h, act, out, note in layout:
    is_dec = s.label in decision
    body.append(rect(x, y, box_w, h, fill=AMBER_BG if is_dec else "#FFFFFF", stroke=AMBER if is_dec else LINE, sw=1.4 if is_dec else 1.2))
    p, _ = pill(x + BOX_PAD, y + 8, f"{badge} {s.label}" if badge else s.label, AMBER if is_dec else SW)
    body += p
    ty = y + 40
    for ln in act:
      body.append(text(x + BOX_PAD, ty, ln, size=11.5, fill=INK))
      ty += 15
    if out:
      body.append(path(f"M{x + BOX_PAD:g} {ty - 5:g} L{x + box_w - BOX_PAD:g} {ty - 5:g}", stroke=HAIR, sw=1))
      ty += 9
      for ln in out:
        body.append(text(x + BOX_PAD, ty, ln, size=10, fill=MUTED))
        ty += 13
    if note:
      ty += 3
      for ln in note:
        body.append(text(x + BOX_PAD, ty, ln, size=9.5, fill=MUTED, style="italic"))
        ty += 12

  # decision exits: a dashed terminal in the next lane of the same row
  for e in exits or []:
    x, y, h = boxes[e.step]
    lane_i = int((x - left) // lane_w)
    tx = x + lane_w if lane_i + 1 < len(lanes) else x - lane_w
    lines = wrap(e.text, inner, 10, 4)
    th = 28 + 13 * len(lines)
    ty0 = y + (h - th) / 2
    body.append(rect(tx, ty0, box_w, th, fill="#FFFFFF", stroke=AMBER, dash="4 3", sw=1.2))
    body.append(text(tx + BOX_PAD, ty0 + 17, e.title, size=10.5, weight=700, fill=AMBER))
    for i, ln in enumerate(lines):
      body.append(text(tx + BOX_PAD, ty0 + 31 + 13 * i, ln, size=10, fill=MUTED))
    if tx > x:
      body.append(path(f"M{x + box_w:g} {y + h / 2:g} L{tx - 7:g} {y + h / 2:g}", stroke=AMBER, dash="4 3"))
      body.append(arrowhead(tx, y + h / 2, "right", AMBER))
    else:
      body.append(path(f"M{x:g} {y + h / 2:g} L{tx + box_w + 7:g} {y + h / 2:g}", stroke=AMBER, dash="4 3"))
      body.append(arrowhead(tx + box_w, y + h / 2, "left", AMBER))

  # loop: dashed back arrow in the left gutter, label written along it
  if loop:
    fx, fy, fh = boxes[loop.from_step]
    tx, ty, th = boxes[loop.to_step]
    gx = X0 + GUTTER / 2
    y_from, y_to = fy + fh / 2, ty + th / 2
    body.append(path(f"M{fx:g} {y_from:g} L{gx:g} {y_from:g} L{gx:g} {y_to:g} L{tx - 7:g} {y_to:g}", stroke=SAFETY, dash="5 3", sw=1.5))
    body.append(arrowhead(tx, y_to, "right", SAFETY))
    cy = (y_from + y_to) / 2
    label = fit(loop.text, y_from - y_to - 40, 10.5, True)
    body.append(f'<g transform="translate({gx - 6:g} {cy:g}) rotate(-90)">' + text(0, 0, label, size=10.5, weight=700, fill=SAFETY, anchor="middle") + "</g>")

  h_total = bottom + 30
  if foot:
    body.append(text(X0, bottom + 24, foot, size=10.5, fill=MUTED))
    h_total += 6
  desc = f"{title}. Lanes: {', '.join(lanes)}. " + " ".join(
    f"{badge} {s.label}: {s.activity} ({s.lane}{'; ' + s.note if s.note else ''}){' → ' + s.output if s.output else ''}." for s in steps)
  return svg(W, int(h_total), f"Figure {number} · {title}", desc, body)


# ---------------------------------------------------------------- sources

def missing_sources() -> list[str]:
  return [f"{doc.name}: {s}" for doc, s in SRC.values() if s not in doc.read_text(encoding="utf-8")]


def load_steps(doc: Path, heading: str, first: str, label: str, activity: str, output: str, who: str) -> list[Step]:
  head, rows = table(section(doc.read_text(encoding="utf-8"), heading), first)
  i = [col(head, c) for c in (label, activity, output, who)]
  return [Step(plain(r[i[0]]), r[i[1]], r[i[2]], r[i[3]]) for r in rows]


def fig_p02() -> str:
  steps = load_steps(WP_P_02, "## 5. Process", "Step", "Step", "Activity", "Output", "Responsible")
  dec = [s for s in steps if s.activity.lower().startswith("decide")]
  if len(dec) != 1:
    raise FigureError("WP-P-02 §5: expected exactly one 'Decide' step")
  options = [o.strip() for o in dec[0].activity.split(":", 1)[1].split("/")]
  exits = [Exit(dec[0].label, " / ".join(o for o in options if o != "accept").capitalize(), SRC["p02_kept"][1])]
  return swimlane("5-1", "Change request swimlane (WP-P-02)", "Who does each step of a change, from the CR to its closure; accept continues down",
                  "WP-P-02 §5, §7", steps, "Step", exits=exits,
                  foot="Generated by fig_p_process.py from the WP-P-02 §5 table; amber: the decision step and its exit (text under the table).")


def fig_p03() -> str:
  steps = load_steps(WP_P_03, "## 5. Workflow", "State (label)", "State (label)", "Activity", "Exit criterion", "Who")
  return swimlane("5-1", "Problem resolution swimlane (WP-P-03)", "Each state label of a problem issue, who works it, and the exit criterion that moves it on",
                  "WP-P-03 §5, §6", steps, "",
                  foot="Generated by fig_p_process.py from the WP-P-03 §5 table; → exit criterion of the state; italic: the rest of the Who cell.")


def fig_p10() -> str:
  steps = load_steps(WP_P_10, "## 4. Procedure", "Step", "Step", "Activity", "Output", "Responsible")
  loop = Loop(str(P10_LOOP_FROM), str(P10_LOOP_TO), "Fix needed after step 3: tag a new RC (-rc2), repeat steps 4–9 for the affected scope")
  return swimlane("4-1", "Release swimlane (WP-P-10)", "From release branch to published release, one row per step of the procedure",
                  "WP-P-10 §4, §5", steps, "Step", loop=loop,
                  foot="Generated by fig_p_process.py from the WP-P-10 §4 table; red dashed: the new-RC loop (text under the table).")


# ---------------------------------------------------------------- WP-P-04 lifecycle

def load_lifecycle() -> tuple[list[tuple[str, str]], dict[str, str], list[tuple[str, str]], str]:
  """(states with meaning, rule into each state, review steps, version rule)."""
  head, rows = table(README.read_text(encoding="utf-8"), "Status")
  if head[1:] != ["Meaning"]:
    raise FigureError(f"assurance README: status table header is {head}")
  states = [(plain(r[0]), plain(r[1])) for r in rows]
  md = WP_P_04.read_text(encoding="utf-8")
  head, rows5 = table(section(md, "## 5. Document control header and status"), "Field")
  fields = {r[0]: r[1] for r in rows5}
  rules = {m.group(1): plain(m.group(2)) for m in re.finditer(r'"([^"]+)"\s+([^;"]+)', fields["Status"])}
  for st in rules:
    if st not in dict(states):
      raise FigureError(f"WP-P-04 §5 names status {st!r}, not in the assurance README status table")
  _, rows7 = table(section(md, "## 7. Review and approval"), "Step")
  return states, rules, [(plain(r[0]), plain(r[1])) for r in rows7], plain(fields["Version"])


def fig_p04() -> str:
  states, rules, review, version = load_lifecycle()
  body = header(W, "5-1", "Work-product lifecycle (WP-P-04)",
                "Status values of the document control header, what moves a work product into each, and the review that gets it to Approved",
                "WP-P-04 §5, §7; assurance README")
  n = len(states)
  gap = 34
  bw = (W - 2 * X0 - gap * (n - 1)) / n
  y0 = 120
  bh = 46 + 14 * max(len(wrap(m, bw - 20, 10.5, 6)) for _, m in states) + 10
  col_of = {}
  for i, (st, meaning) in enumerate(states):
    x = X0 + i * (bw + gap)
    col_of[st] = x
    done = st in ("Approved", "Baselined")
    body.append(rect(x, y0, bw, bh, fill=GREEN_BG if done else "#FFFFFF", stroke=GREEN if done else LINE, sw=1.4))
    body.append(text(x + 10, y0 + 24, st, size=14, weight=700, fill=GREEN if done else INK))
    for j, ln in enumerate(wrap(meaning, bw - 20, 10.5, 6)):
      body.append(text(x + 10, y0 + 46 + 14 * j, ln, size=10.5, fill=MUTED))
    if i:
      ax = x - gap
      body.append(path(f"M{ax + 4:g} {y0 + bh / 2:g} L{x - 7:g} {y0 + bh / 2:g}"))
      body.append(arrowhead(x, y0 + bh / 2, "right"))
  # rule into each state, under its box
  ry = y0 + bh + 12
  max_rule = 0
  for st, rule in rules.items():
    x = col_of[st]
    lines = wrap(f"{st} {rule}", bw - 16, 10, 4)
    body.append(rect(x, ry, bw, 18 + 13 * len(lines), fill=SAFETY_BG, stroke="none", rx=6))
    for j, ln in enumerate(lines):
      body.append(text(x + 8, ry + 15 + 13 * j, ln, size=10, fill=SAFETY))
    max_rule = max(max_rule, 18 + 13 * len(lines))
  vy = ry + max_rule + 26
  body.append(text(X0, vy, fit("Version: " + version, W - 2 * X0, 11), size=11, fill=MUTED))

  # §7 review chain
  sy = vy + 40
  body.append(text(X0, sy, "§7 Review and approval: In review → Approved", size=13, weight=700, fill=INK))
  sy += 16
  m = len(review)
  sgap = 26
  sw_ = (W - 2 * X0 - sgap * (m - 1)) / m
  sh = max(28 + 14 * len(wrap(mech, sw_ - 16, 10.5, 8)) for _, mech in review) + 8
  for i, (step, mech) in enumerate(review):
    x = X0 + i * (sw_ + sgap)
    body.append(rect(x, sy, sw_, sh, fill="#FFFFFF", stroke=LINE))
    p, _ = pill(x + 8, sy + 8, step, SW)
    body += p
    for j, ln in enumerate(wrap(mech, sw_ - 16, 10.5, 8)):
      body.append(text(x + 8, sy + 42 + 14 * j, ln, size=10.5, fill=INK))
    if i:
      body.append(path(f"M{x - sgap + 4:g} {sy + sh / 2:g} L{x - 7:g} {sy + sh / 2:g}"))
      body.append(arrowhead(x, sy + sh / 2, "right"))
  fy = sy + sh + 30
  body.append(text(X0, fy, "Generated by fig_p_process.py from the assurance README status table and the WP-P-04 §5 and §7 tables; green: approved states.",
                   size=10.5, fill=MUTED))
  desc = ("Work-product lifecycle. States: " + "; ".join(f"{s}: {m}" for s, m in states) + ". Rules: " +
          "; ".join(f"{s}: {r}" for s, r in rules.items()) + ". Review steps: " + "; ".join(f"{s}: {m}" for s, m in review) + ".")
  return svg(W, int(fy + 24), "Figure 5-1 · Work-product lifecycle (WP-P-04)", desc, body)


# ---------------------------------------------------------------- build / main

def build() -> dict[str, str]:
  return {
    "fig-p02-5-1-change-swimlane.svg": fig_p02(),
    "fig-p03-5-1-problem-swimlane.svg": fig_p03(),
    "fig-p04-5-1-wp-lifecycle.svg": fig_p04(),
    "fig-p10-4-1-release-swimlane.svg": fig_p10(),
  }


def main(argv: list[str]) -> int:
  check = "--check" in argv
  missing = missing_sources()
  if missing:
    for s in missing:
      print(f"source text no longer found: {s}", file=sys.stderr)
    print("review the prose values in fig_p_process.py (SRC) and regenerate", file=sys.stderr)
    return 1
  try:
    outputs = build()
  except FigureError as e:
    print(f"fig_p_process: {e}", file=sys.stderr)
    return 1
  if check:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"stale: {n}", file=sys.stderr)
    if stale:
      print("run: python3 assurance/07-supporting/figures/fig_p_process.py", file=sys.stderr)
      return 1
    print(f"fig_p_process: {len(outputs)} figure(s) current, {len(SRC)} source texts found")
    return 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
  print(f"fig_p_process: wrote {len(outputs)} figure(s)")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
