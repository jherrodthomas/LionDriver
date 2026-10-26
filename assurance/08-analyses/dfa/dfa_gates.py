#!/usr/bin/env python3
"""The AND gates of the WP-A-04 fault trees against the independence claims and shared resources of WP-A-03.

Every AND gate claims that its inputs do not fail together. This script joins three sources:

  * the AND gates of every tree in `../WP-A-04-system-fta-fmea.md` (parsed by `../fta/fta_diagrams.py`);
  * `and-gates.yaml`: for each gate, the elements its inputs lie in, and the WP-A-03 independence claim (IC-xx) that
    covers it, or why none is needed;
  * `shared-resources.yaml`: what each element depends on, and the WP-A-03 DFIs that analyse each resource;
  * the DFIs and claims of `../WP-A-03-dependent-failure-analysis.md` (parsed by `../figures/fig_a03_dfi_matrix.py`).

For each gate across elements it derives the shared resources (those that reach two inputs lying in different
elements) and the
DFIs that WP-A-03 lists under the gate's claim. It writes `dfa-gates.md` (findings, the map, one row per gate) and
`fig-dfa-resource-map.svg`. Findings are input to the WP-A-03 review; they do not fail CI:

  no claim               an AND gate across elements that no IC-xx covers
  not under the claim    a resource the gate's inputs share whose DFIs WP-A-03 does not list under the gate's claim
  unknown dependence     an element whose dependence on a shared resource is not known (schematic, WP-A-03 OI-2)

`--check` fails if an output is stale, a tree has an AND gate that `and-gates.yaml` does not classify (or the other
way round), a gate's inputs differ from the tree, or an element, claim or DFI is unknown.

    python3 dfa_gates.py            # regenerate dfa-gates.md and the figure
    python3 dfa_gates.py --check
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

HERE = Path(__file__).resolve().parent
ANALYSES = HERE.parent
sys.path.insert(0, str(ANALYSES / "fta"))
sys.path.insert(0, str(ANALYSES / "figures"))
import fig_a03_dfi_matrix as wpa03  # noqa: E402
import fta_diagrams  # noqa: E402

GATES = HERE / "and-gates.yaml"
RESOURCES = HERE / "shared-resources.yaml"
OUT_MD = HERE / "dfa-gates.md"
OUT_SVG = HERE / "fig-dfa-resource-map.svg"
KINDS = ("independence", "same_element", "common_cause", "condition")


class DfaError(Exception):
  pass


def input_key(node) -> str:
  return node.ident or node.text


def tree_gates() -> dict[str, dict]:
  """AND gates of the WP-A-04 trees: ident -> {goal, text, inputs}, in tree order."""
  trees = fta_diagrams.parse_document(fta_diagrams.SOURCE.read_text(encoding="utf-8"))
  fta_diagrams.resolve(trees)
  out: dict[str, dict] = {}

  def walk(goal, node):
    if node.gate == "AND" and node.ident and node.ident not in out:
      out[node.ident] = {"goal": goal, "text": node.text, "inputs": [input_key(c) for c in node.children]}
    for c in node.children:
      walk(goal, c)

  for tr in trees:
    walk(tr.goal, tr.root)
  return out


def load() -> tuple[dict, dict, dict, list, list]:
  gates = yaml.safe_load(GATES.read_text(encoding="utf-8"))["gates"]
  res = yaml.safe_load(RESOURCES.read_text(encoding="utf-8"))
  dfis, claims, _ = wpa03.parse(wpa03.SOURCE.read_text(encoding="utf-8"))
  return gates, res["elements"], res, dfis, claims


def claim_dfis(dfis, claims) -> dict[str, set[str]]:
  """Per claim: the DFIs WP-A-03 lists under it in §5 or tags with it in §4."""
  out: dict[str, set[str]] = defaultdict(set)
  for c in claims:
    out[c.ident] |= set(c.not_controlled) | set(c.partly)
  for d in dfis:
    for ic in d.ic_tags:
      out[ic].add(d.ident)
  return out


def validate(tree: dict, gates: dict, elements: dict, res: dict, dfis, claims) -> list[str]:
  errs = []
  for g in tree:
    if g not in gates:
      errs.append(f"{g} ({tree[g]['goal']}): AND gate in WP-A-04 not classified in and-gates.yaml")
  for g, e in gates.items():
    if g not in tree:
      errs.append(f"{g}: in and-gates.yaml but not an AND gate of WP-A-04")
      continue
    if e.get("kind") not in KINDS:
      errs.append(f"{g}: kind must be one of {', '.join(KINDS)}")
    if list(e.get("inputs", {})) != tree[g]["inputs"]:
      errs.append(f"{g}: inputs {list(e.get('inputs', {}))} differ from the tree {tree[g]['inputs']}")
    for els in e.get("inputs", {}).values():
      errs += [f"{g}: unknown element {x}" for x in els if x not in elements]
    if e.get("kind") == "independence" and not claims_of(e) and not e.get("note"):
      errs.append(f"{g}: independence gate with no claim needs a note")
  known_claims = {c.ident for c in claims}
  errs += [f"{g}: unknown claim {c}" for g, e in gates.items() for c in claims_of(e) if c not in known_claims]
  known_dfis = {d.ident for d in dfis}
  for r in res["resources"]:
    if r["category"] not in res["categories"]:
      errs.append(f"{r['id']}: unknown category {r['category']}")
    for x in r["elements"] + r.get("unknown", []):
      if x not in elements:
        errs.append(f"{r['id']}: unknown element {x}")
    errs += [f"{r['id']}: unknown {d}" for d in r["dfis"] if d not in known_dfis]
  return errs


def shared(e: dict, resources: list) -> list[tuple[dict, bool]]:
  """Resources that reach two inputs lying in different elements (no element in common); True when the resource
  reaches one of them only through an unknown dependence."""
  ins = [set(v) for v in e["inputs"].values()]
  pairs = [(a, b) for i, a in enumerate(ins) for b in ins[i + 1:] if not a & b]
  out = []
  for r in resources:
    known, maybe = set(r["elements"]), set(r["elements"]) | set(r.get("unknown", []))
    if any(a & known and b & known for a, b in pairs):
      out.append((r, False))
    elif any(a & maybe and b & maybe for a, b in pairs):
      out.append((r, True))
  return out


def claims_of(e: dict) -> list[str]:
  c = e.get("claim")
  return [] if not c else [c] if isinstance(c, str) else list(c)


def analyse():
  tree = tree_gates()
  gates, elements, res, dfis, claims = load()
  errs = validate(tree, gates, elements, res, dfis, claims)
  if errs:
    raise DfaError("\n".join(errs))
  under = claim_dfis(dfis, claims)
  rows, no_claim, not_under, unknown = [], [], defaultdict(list), defaultdict(list)
  for g, t in tree.items():
    e = gates[g]
    sh = shared(e, res["resources"]) if e["kind"] == "independence" else []
    ics = claims_of(e)
    covered = set().union(*(under[c] for c in ics)) if ics else set()
    found = sorted({d for r, _ in sh for d in r["dfis"]} & covered)
    if e["kind"] == "independence" and not ics:
      no_claim.append(g)
    for r, maybe in sh:
      if maybe:
        unknown[r["id"]].append(g)
      elif ics and not set(r["dfis"]) & covered:
        not_under[(", ".join(ics), r["id"])].append(g)
    rows.append({"gate": g, "goal": t["goal"], "text": t["text"], **e, "shared": sh, "found": found})
  return rows, no_claim, not_under, unknown, res, elements, {c.ident: c for c in claims}


def dfi_short(ids) -> str:
  return ", ".join(ids) if ids else "—"


def markdown(rows, no_claim, not_under, unknown, res, elements, claims) -> str:
  rid = {r["id"]: r for r in res["resources"]}
  kinds = defaultdict(int)
  for r in rows:
    kinds[r["kind"]] += 1
  L = ["# AND gates, independence claims and shared resources", "",
       "Generated by [`dfa_gates.py`](dfa_gates.py) from the fault trees of [WP-A-04](../WP-A-04-system-fta-fmea.md), the "
       "classification in [`and-gates.yaml`](and-gates.yaml), the map in [`shared-resources.yaml`](shared-resources.yaml) "
       "and the DFIs and claims of [WP-A-03](../WP-A-03-dependent-failure-analysis.md); do not edit. Findings are input to the "
       "WP-A-03 review, not a verdict. Draft, AI-assisted: the classification and the map need review.", "",
       "Every AND gate claims that its inputs do not fail together. A gate whose inputs lie in different elements is an "
       "independence claim; the resources those elements share are where a dependent failure can start. DFI numbers are "
       "those of WP-A-03, which the decomposition-level DFA `fmea/analyses/dfa.yaml` also uses.", "",
       "## Summary", "",
       f"{len(rows)} AND gates: {kinds['independence']} across elements, {kinds['same_element']} within one element, "
       f"{kinds['common_cause']} that draw a common cause as one event, {kinds['condition']} with a driving situation.", "",
       "| Finding | Count |", "|---|---|",
       f"| Gates across elements with no independence claim | {len(no_claim)} |",
       f"| Shared resources not analysed under the gate's claim (claim, resource) | {len(not_under)} |",
       f"| Shared resources with an unknown dependence | {len(unknown)} |", "",
       "## Findings", "", "### Gates across elements with no independence claim", ""]
  if no_claim:
    L += ["| Gate | Goal | Inputs | Note |", "|---|---|---|---|"]
    for r in rows:
      if r["gate"] in no_claim:
        L.append(f"| {r['gate']} | {r['goal']} | {inputs_cell(r)} | {r.get('note', '')} |")
  else:
    L.append("None.")
  L += ["", "### Shared resources not analysed under the gate's claim", "",
        "Two inputs of the gate that lie in different elements share the resource, but none of its DFIs is listed under "
        "the gate's claim in WP-A-03 §5 or tagged with it in §4.", ""]
  if not_under:
    L += ["| Claim | Resource | Its DFIs | Gates |", "|---|---|---|---|"]
    for (ic, r_id), gs in sorted(not_under.items()):
      L.append(f"| {ic} | {r_id} {rid[r_id]['name']} | {dfi_short(rid[r_id]['dfis'])} | {', '.join(gs)} |")
  else:
    L.append("None.")
  L += ["", "### Shared resources with an unknown dependence", ""]
  if unknown:
    L += ["| Resource | Unknown for | Gates it may reach |", "|---|---|---|"]
    for r_id, gs in sorted(unknown.items()):
      L.append(f"| {r_id} {rid[r_id]['name']} | {', '.join(rid[r_id]['unknown'])} | {', '.join(gs)} |")
  else:
    L.append("None.")
  L += ["", "## Shared-resource map", "",
        "![Shared-resource map: resources by coupling category against the elements of the item, with the WP-A-03 DFIs of each](fig-dfa-resource-map.svg)",
        "", "| ID | Resource | Category | Elements | Unknown | DFIs |", "|---|---|---|---|---|---|"]
  for r in res["resources"]:
    L.append(f"| {r['id']} | {r['name']} | {r['category']} | {', '.join(r['elements'])} | {', '.join(r.get('unknown', [])) or '—'} | "
             f"{dfi_short(r['dfis'])} |")
  L += ["", "## AND gates", "",
        "Shared: resources that reach two inputs lying in different elements (? = only through an unknown dependence). "
        "DFIs: those of the shared resources that WP-A-03 lists under the claim.", "",
        "| Gate | Goal | Kind | Claim | Inputs → elements | Shared | DFIs under the claim | Note |", "|---|---|---|---|---|---|---|---|"]
  for r in rows:
    claim = ", ".join(claims_of(r)) or ("**none**" if r["kind"] == "independence" else "—")
    sh = ", ".join(x["id"] + ("?" if m else "") for x, m in r["shared"]) or "—"
    L.append(f"| {r['gate']} | {r['goal']} | {r['kind'].replace('_', ' ')} | {claim} | {inputs_cell(r)} | {sh} | "
             f"{dfi_short(r['found'])} | {r.get('note', '')} |")
  L += ["", "Elements: " + "; ".join(f"{k} {v}" for k, v in elements.items()) + ".", ""]
  return "\n".join(L)


def inputs_cell(r) -> str:
  return "<br>".join(f"{k} → {', '.join(v)}" for k, v in r["inputs"].items())


CAT_COLOUR = {"power": "#c2410c", "clock": "#c2410c", "physical": "#c2410c", "shared part": "#c2410c", "installation": "#b45309",
              "information": "#2a78d6", "configuration": "#2a78d6", "cascading": "#6250d6", "systematic": "#7f8aa0",
              "environment": "#1f9d63"}
INK, MUTED, LINE, AMBER = "#0F1B33", "#5b6b88", "#d6dbe5", "#b7791f"


def figure(res, elements) -> str:
  els = list(elements)
  x0, cw, rh, y0 = 300, 64, 34, 104
  W = x0 + cw * len(els) + 240
  H = y0 + rh * len(res["resources"]) + 54

  def t(x, y, s, size=12, fill=INK, w=400, anchor="start"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{w}" text-anchor="{anchor}">{escape(s)}</text>'

  o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t" '
       "font-family=\"Inter, 'Segoe UI', Helvetica, Arial, sans-serif\">",
       '<title id="t">Shared-resource map: resources by coupling category against the elements of the item, with the WP-A-03 '
       'DFIs of each</title>', f'<rect width="{W}" height="{H}" fill="#fff"/>',
       t(16, 30, "Shared-resource map", 20, INK, 700),
       t(16, 52, "Generated from shared-resources.yaml by dfa_gates.py. Filled: depends on it. Dashed ?: not known yet (WP-A-03 OI-2).", 12, MUTED)]
  for i, e in enumerate(els):
    cx = x0 + i * cw + cw / 2
    o.append(t(cx, y0 - 12, e, 11, INK, 700, "middle"))
  o.append(t(x0 + len(els) * cw + 12, y0 - 12, "DFIs (WP-A-03)", 11, MUTED, 700))
  for k, r in enumerate(res["resources"]):
    y = y0 + k * rh
    if k % 2 == 0:
      o.append(f'<rect x="8" y="{y}" width="{W - 16}" height="{rh}" fill="#f4f6f9"/>')
    col = CAT_COLOUR[r["category"]]
    name = r["name"] if len(r["name"]) <= 40 else r["name"][:38] + "…"
    o += [f'<rect x="16" y="{y + 7}" width="5" height="{rh - 14}" rx="2" fill="{col}"/>',
          t(28, y + 15, f"{r['id']} {name}", 11.5, INK, 600), t(28, y + 28, r["category"], 10, col, 700)]
    for i, e in enumerate(els):
      cx, cy = x0 + i * cw + cw / 2, y + rh / 2
      if e in r["elements"]:
        o.append(f'<circle cx="{cx}" cy="{cy}" r="7" fill="{INK}"/>')
      elif e in r.get("unknown", []):
        o += [f'<circle cx="{cx}" cy="{cy}" r="7" fill="#fff" stroke="{AMBER}" stroke-width="2" stroke-dasharray="3 2"/>',
              t(cx, cy + 4, "?", 10, AMBER, 700, "middle")]
    o.append(t(x0 + len(els) * cw + 12, y + rh / 2 + 4, ", ".join(r["dfis"]), 10.5, INK))
  o.append(t(16, H - 16, "Elements: WP-C-01 §3.1 and the external elements of WP-A-03. Draft, AI-assisted; needs review.", 11, MUTED))
  o.append("</svg>")
  return "\n".join(o) + "\n"


def build() -> dict[Path, str]:
  rows, no_claim, not_under, unknown, res, elements, claims = analyse()
  return {OUT_MD: markdown(rows, no_claim, not_under, unknown, res, elements, claims), OUT_SVG: figure(res, elements)}


def main(argv: list[str]) -> int:
  try:
    out = build()
  except (DfaError, wpa03.ParseError) as e:
    print(f"error: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [p for p, c in out.items() if not p.exists() or p.read_text(encoding="utf-8") != c]
    for p in stale:
      print(f"stale: {p.name}; run dfa_gates.py", file=sys.stderr)
    if not stale:
      print(f"dfa_gates: {len(out)} file(s) current")
    return 1 if stale else 0
  for p, c in out.items():
    p.write_text(c, encoding="utf-8")
  print(f"wrote {', '.join(p.name for p in out)}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
