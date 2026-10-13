#!/usr/bin/env python3
"""Minimal cut sets of the WP-A-04 fault trees, checked against the hand-written tables.

Reads the same text trees as `fta_diagrams.py` and computes the minimal cut sets
of every top event by Boolean reduction (OR = union, AND = product, then
absorption). A transfer to a gate developed in another tree is expanded with
that gate's logic; a repeated event is the same Boolean variable wherever it
appears.

It then reads the "minimal cut sets (qualitative)" table of each goal in
WP-A-04 and classifies every row:

  match          the row is a computed minimal cut set
  reduced        the row omits events the tree logic needs (a smaller "effective"
                 order claimed from a latent, by-design or common-cause argument)
  not minimal    the row contains a computed cut set plus more events
  unrelated      the row neither contains nor is contained in any computed cut set
  in words       the row is described in words and cannot be checked

and lists computed cut sets that no row covers. The result is written to
`cut-sets.md`. Findings are analysis input for review; they do not fail CI.
`--check` fails only if `cut-sets.md` is stale or a tree or table cannot be parsed.

    python3 fta_cutsets.py            # regenerate cut-sets.md
    python3 fta_cutsets.py --check    # fail if cut-sets.md is stale
"""

from __future__ import annotations

import itertools
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fta_diagrams as fd

OUTPUT = fd.HERE / "cut-sets.md"

TABLE_HEAD_RE = re.compile(r"^### \d+\.\d+ (SG-\d+) minimal cut sets")
SHORTHAND_RE = re.compile(r"\b(BE|UE)-(\d+\.\d+)((?:/\d+\.\d+)+)")
EVENT_RE = re.compile(r"\b(?:BE|UE)-\d+\.\d+\b")
GATE_RE = re.compile(r"\bG(?:-[A-Za-z]+|\d+(?:\.\d+)*(?:\.[a-z])?)\b")

CutSet = frozenset
STATUSES = ("match", "effective", "argued", "outside tree", "reduced", "not minimal", "unrelated", "in words")


def minimise(sets) -> list[CutSet]:
  out: list[CutSet] = []
  for s in sorted(set(sets), key=lambda s: (len(s), sorted(s))):
    if not any(k <= s for k in out):
      out.append(s)
  return out


class Solver:
  def __init__(self, trees: list[fd.Tree]):
    self.trees = trees
    self.memo: dict[int, list[CutSet]] = {}
    self.gates: dict[str, fd.Node] = {}
    self.events: dict[str, fd.Node] = {}
    self.latent: frozenset[str] = frozenset()
    for t in trees:
      for n in _walk(t.root):
        if n.ref_of is None and n.ident:
          if n.children:
            self.gates[n.ident] = n
          else:
            self.events[n.ident] = n

  def finish(self) -> None:
    self.latent = frozenset(e for e in self.events if self.is_latent(e))

  def is_latent(self, ident: str) -> bool:
    node = self.events.get(ident)
    return node is not None and ("latent" in {k for k, _ in node.badges} or "by design" in node.text.lower())

  def cut_sets(self, node: fd.Node) -> list[CutSet]:
    key = id(node)
    if key in self.memo:
      return self.memo[key]
    if node.kind == "transfer_in":
      result = self.cut_sets(node.ref_of)
    elif not node.children:
      result = [CutSet([node.ident])]
    elif node.gate == "OR":
      result = minimise(s for c in node.children for s in self.cut_sets(c))
    else:
      acc = [CutSet()]
      for c in node.children:
        acc = minimise(a | b for a in acc for b in self.cut_sets(c))
      result = acc
    self.memo[key] = result
    return result


def _walk(node):
  yield node
  for c in node.children:
    yield from _walk(c)


# ---------------------------------------------------------------- hand tables

@dataclass
class HandRow:
  goal: str
  ident: str
  order: str
  events_text: str
  candidates: list[CutSet] | None   # None: described in words
  status: str = ""
  details: list[str] = field(default_factory=list)


def parse_tables(md: str, solver: Solver) -> dict[str, list[HandRow]]:
  rows: dict[str, list[HandRow]] = {}
  goal = None
  for line in md.splitlines():
    m = TABLE_HEAD_RE.match(line)
    if m:
      goal = m.group(1)
      rows[goal] = []
      continue
    if goal and line.startswith("| MCS-"):
      cells = [c.strip() for c in line.strip("|").split("|")]
      rows[goal].append(HandRow(goal, cells[0], cells[1], cells[2], _expand(cells[2], solver)))
    elif goal and line.startswith("#"):
      goal = None
  return rows


def _expand(text: str, solver: Solver) -> list[CutSet] | None:
  m = re.search(r"\{([^}]*)\}", text)
  if not m:
    return None
  body = re.sub(r"\([^)]*\)", "", m.group(1))
  body = SHORTHAND_RE.sub(lambda s: " or ".join(
    [f"{s.group(1)}-{s.group(2)}"] + [f"{s.group(1)}-{x}" for x in s.group(3).strip("/").split("/")]), body)
  slots: list[list[CutSet]] = []
  for slot in body.split(","):
    alts: list[CutSet] = []
    for alt in slot.split(" or "):
      events = EVENT_RE.findall(alt)
      gates = [g for g in GATE_RE.findall(alt) if g in solver.gates]
      if events and not gates:
        alts.append(CutSet(events))
      elif gates and not events:
        for g in gates:
          alts.extend(solver.cut_sets(solver.gates[g]))
      else:
        return None
    slots.append(alts)
  return minimise(CutSet().union(*combo) for combo in itertools.product(*slots))


def classify(row: HandRow, computed: list[CutSet], solver: Solver, tree_events: set[str]) -> None:
  if row.candidates is None:
    row.status = "in words"
    row.details.append("not machine-checkable; review by hand")
    return
  effective_claimed = "effective" in row.order
  statuses = []
  for cand in row.candidates:
    label = _fmt(cand)
    supers = [c for c in computed if cand < c]
    hits = [c for c in computed if c <= cand | solver.latent]
    if cand in computed:
      statuses.append("match")
    elif not cand <= tree_events:
      statuses.append("outside tree")
      row.details.append(f"{label}: {', '.join(_ids(cand - tree_events))} not in this tree " +
                         "(argued outside the gate logic, e.g. from a CCF note)")
    elif hits:
      c = min(hits, key=lambda h: (len(cand - h), len(h)))
      if cand <= c:
        statuses.append("effective")
        row.details.append(f"{label}: omits latent {', '.join(_ids(c - cand))} (computed {_fmt(c)})")
      else:
        statuses.append("not minimal")
        row.details.append(f"{label}: {_fmt(c)} is already a cut set, so {', '.join(_ids(cand - c))} " +
                           "is not needed")
    elif supers:
      missing = _ids({e for c in supers for e in c - cand})
      status = "argued" if effective_claimed else "reduced"
      statuses.append(status)
      row.details.append(f"{label}: tree needs also one of the sets containing {', '.join(missing)} " +
                         f"(e.g. {_fmt(supers[0])})" + ("; the row argues a lower order" if effective_claimed else ""))
    else:
      best = max(computed, key=lambda c: len(c & cand))
      statuses.append("unrelated")
      row.details.append(f"{label}: not a cut set; nearest computed {_fmt(best)}")
  rank = ["unrelated", "not minimal", "reduced", "argued", "outside tree", "effective", "match"]
  row.status = min(statuses, key=rank.index)


def _ids(s) -> list[str]:
  return sorted(s, key=_sort_key)


def _fmt(s: CutSet) -> str:
  return "{" + ", ".join(sorted(s, key=_sort_key)) + "}"


def _sort_key(ident: str):
  prefix, num = ident.split("-", 1)
  major, minor = num.split(".")
  return (prefix != "BE", int(major), int(minor))


# ---------------------------------------------------------------- report

def build() -> str:
  md = fd.SOURCE.read_text(encoding="utf-8")
  trees = fd.parse_document(md)
  fd.resolve(trees)
  trees.sort(key=lambda t: t.goal)
  solver = Solver(trees)
  solver.finish()
  tables = parse_tables(md, solver)

  out = [
    "# Minimal cut sets",
    "",
    "Generated by `fta_cutsets.py` from the fault trees in [WP-A-04](../WP-A-04-system-fta-fmea.md); " +
    "do not edit. Each cut set is computed from the gate logic as written (OR = union, AND = product, " +
    "absorption); transfers are expanded and repeated events are one variable. The tables of WP-A-04 " +
    "are then checked against it. Findings here are input to the WP-A-04 review, not a verdict: an " +
    "\"effective\" order argued from a latent or by-design condition shows as *effective*, one argued " +
    "otherwise (e.g. common cause) as *argued*.",
    "",
    "Order: *n* BE + *m* UE = basic events in the item plus undeveloped events (outside the item, " +
    "driver or traffic). Effective: item basic events that are not latent or by design at the baseline " +
    "(an event tagged `(latent, …)` or described as \"by design\" in WP-A-04 is taken as already present). " +
    "Tags: L = latent or by design, S = SOTIF, C = carries a CCF tag.",
    "",
    "Row results: *match* = a computed cut set; *effective* = omits only latent events; *argued* = a row " +
    "marked effective that omits events the logic needs (the reason is in its comment); *outside tree* = names an event that is not in this tree; " +
    "*reduced* = omits events the logic needs, with no stated reason; *not minimal* = a smaller computed " +
    "cut set exists; *unrelated* = not a cut set; *in words* = not machine-checkable.",
    "",
    "## Summary",
    "",
    "| Goal | Cut sets | Effective order ≤ 1 | Table rows | " + " | ".join(STATUSES) + " | Cut sets not in the table |",
    "|---|---|---|---|" + "---|" * len(STATUSES) + "---|",
  ]
  sections = []
  for tree in trees:
    computed = solver.cut_sets(tree.root)
    rows = tables.get(tree.goal, [])
    tree_events = {e for c in computed for e in c}
    for r in rows:
      classify(r, computed, solver, tree_events)
    covered = set()
    for r in rows:
      for cand in r.candidates or []:
        for c in computed:
          if cand == c or c < cand or cand < c:
            covered.add(c)
    uncovered = [c for c in computed if c not in covered]
    counts = {s: sum(r.status == s for r in rows) for s in STATUSES}
    singles = sum(1 for c in computed if sum(1 for e in c if e.startswith("BE") and not solver.is_latent(e)) <= 1)
    out.append(f"| {tree.goal} | {len(computed)} | {singles} | {len(rows)} | "
               + " | ".join(str(counts[s]) for s in STATUSES) + f" | {len(uncovered)} |")

    sec = [f"## {tree.goal}: {tree.title}", "", f"Top event {tree.root.ident}. " +
           f"{len(computed)} minimal cut sets.", "",
           "### Computed cut sets", "", "| # | Order | Effective | Events | Tags | Table row |",
           "|---|---|---|---|---|---|"]
    for i, c in enumerate(computed, 1):
      refs = [r.ident for r in rows for cand in (r.candidates or []) if cand == c or cand < c or c < cand]
      eff = sum(1 for e in c if e.startswith("BE") and not solver.is_latent(e))
      sec.append(f"| {i} | {_n(c, 'BE')} BE + {_n(c, 'UE')} UE | {eff} | {_fmt(c)} | {_tags(c, solver)} " +
                 f"| {', '.join(dict.fromkeys(refs)) or '**not in table**'} |")
    sec += ["", "### Table rows of WP-A-04", "", "| Row | Order stated | Events stated | Result | Detail |",
            "|---|---|---|---|---|"]
    for r in rows:
      detail = "<br>".join(d.replace("|", "\\|") for d in r.details) or "—"
      sec.append(f"| {r.ident} | {r.order} | {r.events_text.replace('|', chr(92) + '|')} | {r.status} | {detail} |")
    sections += sec + [""]
  out += [""] + sections
  return "\n".join(out).rstrip() + "\n"


def _n(c: CutSet, prefix: str) -> int:
  return sum(1 for e in c if e.startswith(prefix))


def _tags(c: CutSet, solver: Solver) -> str:
  tags = set()
  for e in c:
    node = solver.events.get(e)
    if node is None:
      continue
    kinds = {k for k, _ in node.badges}
    text = node.text.lower()
    if "latent" in kinds or "by design" in text:
      tags.add("L")
    if "sotif" in kinds or "[sotif]" in text:
      tags.add("S")
    if "ccf" in kinds or "ccf" in text:
      tags.add("C")
  return " ".join(sorted(tags)) or ""


def main(argv: list[str]) -> int:
  try:
    report = build()
  except fd.FtaError as e:
    print(f"fta_cutsets: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != report:
      print("stale: cut-sets.md\nrun: python3 assurance/08-analyses/fta/fta_cutsets.py", file=sys.stderr)
      return 1
    print("fta_cutsets: cut-sets.md current")
    return 0
  OUTPUT.write_text(report, encoding="utf-8")
  print(f"fta_cutsets: wrote {OUTPUT.name}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
