"""Shared tree side of the fmdtools sweeps (tool evaluation TE-02): the WP-A-04 cut sets of a goal and the comparison
of a model's minimal fault sets with them. Used by the SG-06 sweep and the goals after it (DQ-417); the SG-02 sweep
keeps its own copy of the same functions.

Synthetic (DSR-12): the comparison points reviewers at possible gaps in a tree; it earns no evidence credit.
"""

import itertools
import sys
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "assurance/08-analyses/fta"))
import fta_cutsets as fc  # noqa: E402
import fta_diagrams as fd  # noqa: E402


def solve(goal: str):
  """(solver, computed cut sets of the goal's top event) from the WP-A-04 trees."""
  trees = fd.parse_document(fd.SOURCE.read_text(encoding="utf-8"))
  fd.resolve(trees)
  solver = fc.Solver(trees)
  solver.finish()
  return solver, solver.cut_sets(next(t for t in trees if t.goal == goal).root)


def tree_singles(goal: str) -> tuple[dict[str, list[str]], frozenset[str]]:
  """Events that give the top event alone once the tree's latent events are taken as present: event -> other members
  of the cut set that are not latent (undeveloped events, such as a driver who does not notice)."""
  solver, cut_sets = solve(goal)
  singles: dict[str, list[str]] = {}
  for cs in cut_sets:
    rest = cs - solver.latent
    be = [e for e in rest if e.startswith("BE")]
    if len(be) == 1 and all(e.startswith("UE") for e in rest - {be[0]}):
      singles.setdefault(be[0], sorted(rest - {be[0]}))
  return singles, solver.latent


def effective(cut_sets, latent, order: int) -> list[frozenset[str]]:
  """The tree's effective sets: cut sets with the latent events taken as present, minimised, up to `order` events."""
  return [c for c in fc.minimise([frozenset(c - latent) for c in cut_sets]) if len(c) <= order]


def tree_gaps(model_sets, cut_sets, latent) -> list[frozenset[str]]:
  """Model sets the tree does not predict: no cut set, with its latent events taken as present, lies inside the set."""
  return [c for c in model_sets if not any((t - latent) <= c for t in cut_sets)]


def mcs_rows(goal: str, solver, latent) -> list[tuple[str, frozenset[str]]]:
  """(row ID, effective set) for every machine-readable row of the WP-A-04 cut-set table of the goal."""
  rows = fc.parse_tables(fd.SOURCE.read_text(encoding="utf-8"), solver).get(goal, [])
  return [(r.ident, frozenset(c - latent)) for r in rows for c in (r.candidates or [])]


def minimal_sets(modes: dict, causes: set[str], te, order: int) -> tuple[list[tuple[str, ...]], list[int]]:
  """The minimal sets of up to `order` modes for which `te(events) -> (events, top event)` holds. A set with no cause
  cannot lose control, and a superset of a set already found is not minimal, so neither is run. `te` must be a
  module-level function, so the pool can send it to its workers."""
  found: list[tuple[str, ...]] = []
  runs = []
  with Pool() as pool:
    for k in range(1, order + 1):
      cands = [c for c in itertools.combinations(sorted(modes), k)
               if causes & set(c) and not any(set(f) <= set(c) for f in found)]
      runs.append(len(cands))
      found += sorted(c for c, hit in pool.map(te, cands, chunksize=16) if hit)
  return sorted(found, key=lambda c: (len(c), c)), runs


def fset(c) -> str:
  return "{" + ", ".join(sorted(c)) + "}"
