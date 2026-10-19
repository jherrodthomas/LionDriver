#!/usr/bin/env python3
"""Fill WP-S-03 Figure 3-1, system element hierarchy (fig-s03-3-1-system-element-hierarchy.svg), from §5 and §6.

The layout is hand-drawn and lives in fig_s03_hierarchy_template.svg. This script writes the parts that change with the
document into it:

  {{BOX:E-xx}}   the TSR list of each element box, word-wrapped, from the §5 table "Allocation of TSRs to elements",
                 and the safety mechanisms whose §6 Element column names that element alone
  {{SHARED}}     the mechanisms whose §6 Element column names two elements, grouped by the pair, and the count line
  {{BOXH}} …     box, partition and page heights: the boxes grow when a list needs more lines, and everything below
                 them moves down by the same amount ({{D}})

Two checks guard the figure against the drift that hand-drawn figures had:
  - every TSR in assurance/trace/items/tsr.yaml (WP-S-02 and WP-S-06) is allocated in §5, to an element, EXT or OPS;
  - every SM-xx of §6 names elements the figure has.

    python3 fig_s03_hierarchy.py            # write the SVG
    python3 fig_s03_hierarchy.py --check    # fail if a TSR is unallocated or the SVG is stale

Standard library only. Output is deterministic.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCE = REPO / "assurance" / "03-system" / "WP-S-03-technical-safety-concept-architecture.md"
TSR_ITEMS = REPO / "assurance" / "trace" / "items" / "tsr.yaml"
TEMPLATE = HERE / "fig_s03_hierarchy_template.svg"
OUT = "fig-s03-3-1-system-element-hierarchy.svg"

# Element boxes of the template: text x, text width and whether the element is in the ASIL C envelope.
BOXES = {
  "E-01": (160, 216, False),
  "E-02": (404, 111, False),
  "E-04b": (543, 111, False),
  "E-03a": (690, 111, True),
  "E-03b": (829, 111, True),
  "E-04a": (968, 111, True),
  "E-05": (1115, 111, True),
}
ORDER = ["E-03a", "E-03b", "E-04a", "E-05", "E-01", "E-02", "E-04b"]  # shared pairs: envelope pairs first
SAFETY, INK, MUTED, FAINT = "#C2410C", "#0F172A", "#475569", "#94A3B8"

# Template geometry (y of the first TSR line, line pitch, bottom margin, box bottom and heights in the template).
Y_TSR, PITCH, MARGIN = 452, 13, 11
TEMPLATE_BOTTOM, TEMPLATE_H, QM_H, ENV_H = 544, 1371, 981, 532
Y_SHARED, SHARED_PITCH, SHARED_MAX = 890, 18, 4


def section(md: str, number: int) -> str:
  start = md.index(f"\n## {number}.")
  return md[start:md.index("\n## ", start + 1)]


def allocation(md: str) -> dict[str, str]:
  """§5 rows: element key (E-01, …, EXT, OPS) -> the TSR cell as written."""
  rows = {}
  for name, tsrs in re.findall(r"^\| ((?:E-0\d[ab]?|EXT|OPS)[^|]*)\| ([^|]+)\|", section(md, 5), re.M):
    rows[name.split()[0]] = tsrs.strip()
  return rows


def numbers(cell: str) -> set[int]:
  out = set()
  for a, b in re.findall(r"(\d{3})(?:\s*[–-]\s*(\d{3}))?", cell):
    out.update(range(int(a), int(b or a) + 1))
  return out


def mechanisms(md: str) -> dict[str, list[str]]:
  """§6 rows: SM-xx -> the elements its Element column names (E-03a/b and E-04a/E-03b spellings normalised)."""
  out = {}
  for sm, cell in re.findall(r"^\| (SM-\d\d) \|[^|]*\|[^|]*\| ([^|]+)\|", section(md, 6), re.M):
    names = []
    for part in cell.split("/"):
      part = part.strip().split()[0]
      if re.fullmatch(r"[ab]", part):  # "E-03a/b"
        part = names[-1][:-1] + part
      names.append(part)
    out[sm] = names
  return out


def trace_tsrs() -> set[int]:
  return {int(n) for n in re.findall(r"^- id: TSR-(\d+)$", TSR_ITEMS.read_text(encoding="utf-8"), re.M)}


def unallocated(md: str) -> list[int]:
  allocated = set().union(*(numbers(c) for c in allocation(md).values()))
  return sorted(trace_tsrs() - allocated)


def width(s: str, size: float = 10) -> float:
  """Rough advance width in Inter: digits and letters 0.56 em, narrow punctuation 0.28 em."""
  return sum((0.28 if c in " ,.()/" else 0.56) * size for c in s)


def wrap(s: str, limit: float) -> list[str]:
  """Break between list items ("506 (logic), 507"); inside an item only when it is wider than the box on its own."""
  lines, cur = [], ""
  items = s.split(", ")
  for i, item in enumerate(items):
    item += "," if i < len(items) - 1 else ""
    trial = f"{cur} {item}" if cur else item
    if not cur or width(trial) <= limit:
      cur = trial
      continue
    lines.append(cur)
    cur = item
  if cur:
    lines.append(cur)
  out = []
  for line in lines:  # an item wider than the box: break at its spaces
    words, part = line.split(" "), ""
    for w in words:
      trial = f"{part} {w}" if part else w
      if part and width(trial) > limit:
        out.append(part)
        part = w
      else:
        part = trial
    out.append(part)
  return out


def sm_list(ids: list[str]) -> str:
  """SM-25, 27, 28, 30–34: runs of three or more as a range."""
  nums = sorted(int(i[3:]) for i in ids)
  parts, i = [], 0
  while i < len(nums):
    j = i
    while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
      j += 1
    parts.append(f"{nums[i]:02d}–{nums[j]:02d}" if j - i >= 2 else ", ".join(f"{n:02d}" for n in nums[i:j + 1]))
    i = j + 1
  return "SM-" + ", ".join(parts)


def text(x: int, y: int, s: str, fill: str, weight: str = "", size: float = 10, extra: str = "") -> str:
  w = f' font-weight="{weight}"' if weight else ""
  return f'  <text x="{x}" y="{y}" font-size="{size:g}"{w}{extra} fill="{fill}">{escape(s)}</text>'


def build(md: str | None = None) -> str:
  md = md if md is not None else SOURCE.read_text(encoding="utf-8")
  alloc, sms = allocation(md), mechanisms(md)
  single = {e: [s for s, n in sms.items() if n == [e]] for e in BOXES}
  shared: dict[tuple[str, ...], list[str]] = {}
  for s, names in sms.items():
    if len(names) > 1:
      shared.setdefault(tuple(sorted(names, key=ORDER.index)), []).append(s)

  tsr_lines, sm_lines = {}, {}
  for e, (x, w, env) in BOXES.items():
    cell = alloc.get(e, "")
    tsr_lines[e] = wrap(cell, w) if cell else []
    if single[e]:
      sm_lines[e] = wrap(sm_list(single[e]), w)
    else:
      sm_lines[e] = ["only shared", "(see below)"] if any(e in p for p in shared) else ["none"]
  n_tsr = max(max(len(v) for v in tsr_lines.values()), 1)
  n_sm = max(len(v) for v in sm_lines.values())
  y_sm_head = Y_TSR + PITCH * (n_tsr - 1) + 15
  bottom = y_sm_head + 14 + PITCH * (n_sm - 1) + MARGIN
  d = bottom - TEMPLATE_BOTTOM

  boxes = {}
  for e, (x, w, env) in BOXES.items():
    out = []
    if tsr_lines[e]:
      for k, line in enumerate(tsr_lines[e]):
        out.append(text(x, Y_TSR + PITCH * k, line, INK))
    else:
      out.append(text(x, Y_TSR, "none allocated", FAINT))
    out.append(text(x, y_sm_head, "SMs §6", "#64748B", "700", 9, ' letter-spacing=".05em"'))
    for k, line in enumerate(sm_lines[e]):
      if single[e]:
        out.append(text(x, y_sm_head + 14 + PITCH * k, line, SAFETY if env else MUTED, "700"))
      else:
        out.append(text(x, y_sm_head + 14 + PITCH * k, line, FAINT if line == "none" else MUTED, "400"))
    boxes[e] = "\n".join(out)

  if len(shared) > SHARED_MAX:
    raise SystemExit(f"{len(shared)} shared element pairs; the template has room for {SHARED_MAX}")
  rows = []
  for k, pair in enumerate(sorted(shared, key=lambda p: [ORDER.index(e) for e in p])):
    y = Y_SHARED + SHARED_PITCH * k
    env = any(BOXES[e][2] for e in pair)
    rows.append(text(694, y, " + ".join(pair), INK, "700", 10.5))
    rows.append(text(790, y, ", ".join(sorted(shared[pair])), SAFETY if env else MUTED, "700", 10.5))
  n_single = sum(len(v) for v in single.values())
  n_shared = sum(len(v) for v in shared.values())
  first, last = min(sms), max(sms)
  rows.append(f'  <text x="694" y="{Y_SHARED + SHARED_PITCH * (SHARED_MAX - 1) + 26}" class="m" font-size="9.5">'
              f'{first}…{last}: {n_single} on one element (in the boxes) + {n_shared} shared (here).</text>')

  svg = TEMPLATE.read_text(encoding="utf-8")
  for e, body in boxes.items():
    svg = svg.replace("{{BOX:%s}}" % e, body)
  values = {"SHARED": "\n".join(rows), "D": str(d), "BOXH": str(bottom - 312), "QMH": str(QM_H + d),
            "ENVH": str(ENV_H + d), "H": str(TEMPLATE_H + d)}
  for k, v in values.items():
    svg = svg.replace("{{%s}}" % k, v)
  if "{{" in svg:
    raise SystemExit("template placeholder left unfilled: " + re.search(r"\{\{[^}]*\}\}", svg).group(0))
  return svg


def problems(md: str) -> list[str]:
  out = [f"TSR-{n} is in tsr.yaml but not allocated in WP-S-03 §5" for n in unallocated(md)]
  for s, names in mechanisms(md).items():
    out += [f"{s}: §6 element {n} is not in Figure 3-1" for n in names if n not in BOXES]
  return out


def main(argv: list[str]) -> int:
  md = SOURCE.read_text(encoding="utf-8")
  found = problems(md)
  for p in found:
    print(p, file=sys.stderr)
  if found:
    return 1
  svg = build(md)
  path = HERE / OUT
  if "--check" in argv:
    if not path.exists() or path.read_text(encoding="utf-8") != svg:
      print(f"stale: {OUT}\nrun: python3 assurance/03-system/figures/fig_s03_hierarchy.py", file=sys.stderr)
      return 1
    print(f"fig_s03_hierarchy: {OUT} current, every TSR allocated in §5")
    return 0
  path.write_text(svg, encoding="utf-8")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
