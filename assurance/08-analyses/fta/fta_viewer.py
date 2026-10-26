#!/usr/bin/env python3
"""Interactive viewer for the WP-A-04 fault trees: one HTML page, every goal, no sheets.

Reads the same text trees as `fta_diagrams.py`, with the same parser, and writes
`fta-viewer.html`: a self-contained page (no network) that draws each tree top-down
(or left to right) as cards with IEC 61025 gate symbols. Gates open and close in place,
and a transfer opens the gate it refers to where it stands, so a tree never splits into
sheets. Each gate shows its number of minimal cut sets (`fta_cutsets.Solver`) and the
fewest item basic events among them.

Two highlights, chosen on the page:

  record   the single-point paths of the SVG sheets: one item basic event (BE) reaches the
           top event, undeveloped events (UE) assumed (`fta_diagrams.single_point_nodes`)
  latents  the same with latent basic events counted as already failed, so a path that
           needs one detectable fault plus latent ones is shown too

Nothing here is analysis content and the SVG sheets stay the drawing of record; change
the trees in WP-A-04 and regenerate.

    python3 fta_viewer.py            # regenerate fta-viewer.html
    python3 fta_viewer.py --check    # fail if the committed page is stale

Standard library only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fta_cutsets as fc
import fta_diagrams as fd

OUTPUT = fd.HERE / "fta-viewer.html"
TEMPLATE = fd.HERE / "fta_viewer.template.html"
RECORD, LATENTS = 1, 2   # bits of an occurrence's `h`: on a single-point path in that mode


def target(node: fd.Node) -> fd.Node:
  return node.ref_of if node.ref_of is not None else node


class Model:
  """Node table and fully expanded occurrence trees, with both highlight modes."""

  def __init__(self, trees: list[fd.Tree]):
    self.solver = fc.Solver(trees)
    self.solver.finish()
    self.keys: dict[int, str] = {}
    self.nodes: dict[str, dict] = {}
    self.cost_memo: dict[tuple[int, bool], int] = {}

  def key(self, node: fd.Node) -> str:
    """Stable key of a defining node: its ID, or the parent's key for an unnamed implicit OR."""
    return self.keys[id(node)]

  def register(self, node: fd.Node, parent_key: str) -> None:
    if id(node) in self.keys or node.ref_of is not None:
      return
    k = node.ident or f"{parent_key}/any-of-{len([x for x in self.nodes if x.startswith(parent_key + '/')]) + 1}"
    self.keys[id(node)] = k
    entry = {"id": node.ident, "text": node.text, "kind": node.kind, "tree": node.tree,
             "badges": [list(b) for b in node.badges]}
    if node.children:
      entry["gate"] = node.gate
      entry["cs"] = len(self.solver.cut_sets(node))
      entry["min"] = [self.cost(node, False), self.cost(node, True)]
    elif node.ident in self.solver.latent:
      entry["latent"] = True
    if node.notes:
      entry["notes"] = node.notes
    self.nodes[k] = entry
    for c in node.children:
      self.register(c, k)

  def cost(self, node: fd.Node, latents: bool) -> int:
    """Fewest item basic events in a cut set; UE count 0, and latent BE too in the latents mode."""
    d = target(node)
    memo = (id(d), latents)
    if memo not in self.cost_memo:
      if not d.children:
        v = 1 if d.ident.startswith("BE-") and not (latents and d.ident in self.solver.latent) else 0
      else:
        orders = [self.cost(c, latents) for c in d.children]
        v = min(orders) if d.gate == "OR" else sum(orders)
      self.cost_memo[memo] = v
    return self.cost_memo[memo]

  def occurrence(self, node: fd.Node, budgets: tuple[int | None, int | None]) -> dict:
    """The node where it stands, its inputs expanded through transfers; budgets of None: not reachable."""
    d = target(node)
    o: dict = {"k": self.key(d)}
    if node.ref_of is not None:
      o["t"] = 1
      if node.ref_tree:
        o["x"] = node.ref_tree
      if node.notes:
        o["n"] = node.notes
    h = 0
    kids = []
    if d.children:
      per_mode = []
      for latents, budget in ((False, budgets[0]), (True, budgets[1])):
        orders = [self.cost(c, latents) for c in d.children]
        rooms = []
        for order in orders:
          room = None if budget is None else (budget if d.gate == "OR" else budget - (sum(orders) - order))
          rooms.append(room if room is not None and order <= room else None)
        per_mode.append(rooms)
      for i, c in enumerate(d.children):
        co = self.occurrence(c, (per_mode[0][i], per_mode[1][i]))
        h |= co.get("h", 0)
        kids.append(co)
      o["c"] = kids
    else:
      for bit, budget in ((RECORD, budgets[0]), (LATENTS, budgets[1])):
        if budget is not None and d.ident.startswith("BE-") and self.cost(d, bit == LATENTS) <= budget:
          h |= bit
    if h:
      o["h"] = h
    return o


def hot_idents(occ: dict, bit: int, inside_transfer: bool = False) -> set[str]:
  """IDs on a path of that mode, outside transfers, as `single_point_nodes` records them."""
  out = set()
  if occ.get("h", 0) & bit and not inside_transfer:
    out.add(occ["k"])
  for c in occ.get("c", []):
    out |= hot_idents(c, bit, inside_transfer or bool(occ.get("t")))
  return out


def build_data() -> dict:
  trees = fd.parse_document(fd.SOURCE.read_text(encoding="utf-8"))
  fd.resolve(trees)
  trees.sort(key=lambda t: t.goal)
  model = Model(trees)
  for t in trees:
    model.register(t.root, t.goal)
  asils = fd.goal_asils()
  goals = []
  for t in trees:
    root = model.occurrence(t.root, (1, 1))
    goals.append({"goal": t.goal, "title": t.title, "asil": asils.get(t.goal, "?"), "root": root})
  return {"source": "WP-A-04", "goals": goals, "nodes": model.nodes}


def render(data: dict) -> str:
  page = TEMPLATE.read_text(encoding="utf-8")
  blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
  if page.count("/*DATA*/null") != 1:
    raise fd.FtaError(f"{TEMPLATE.name}: expected one /*DATA*/null placeholder")
  return page.replace("/*DATA*/null", blob)


def main(argv: list[str]) -> int:
  try:
    text = render(build_data())
  except fd.FtaError as e:
    print(f"fta_viewer: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != text:
      print(f"stale: {OUTPUT.name}\nrun: python3 assurance/08-analyses/fta/fta_viewer.py", file=sys.stderr)
      return 1
    print("fta_viewer: fta-viewer.html current")
    return 0
  OUTPUT.write_text(text, encoding="utf-8")
  print(f"fta_viewer: wrote {OUTPUT.name}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
