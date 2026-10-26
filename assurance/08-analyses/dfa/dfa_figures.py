#!/usr/bin/env python3
"""Draw the five figures of the DFA README (dfa/README.md) from the same join as dfa_gates.py.

  fig-dfa-1-boundary.svg   the item boundary of WP-C-01 Figure 3-2 in the DFA view: on each element the shared
                           resources it depends on, and on each boundary the independence claim that crosses it, with
                           its WP-A-03 §5 verdict and the resources not analysed under it
  fig-dfa-2-method.svg     how the check works: the three sources, the join per AND gate, and what comes out
  fig-dfa-3-gaps.svg       each independence claim against each shared resource: shared by a gate under the claim
                           and analysed there (a DFI of the resource listed under the claim), shared but not
                           analysed, or reached only through an unknown dependence; the WP-A-03 §5 verdict per claim
  fig-dfa-4-gates.svg      every AND gate, by safety goal, with what the check found for it
  fig-dfa-5-example.svg    one gate worked through (EXAMPLE): its inputs, the elements they lie in, the resources they
                           share and whether each resource's DFIs are listed under the gate's claim

Every count and cell comes from `dfa_gates.analyse()`; nothing is typed in by hand except EXAMPLE. A figure says
where a dependent failure can start and whether WP-A-03 has analysed it under the claim; it says nothing about whether
the claim holds (that is the WP-A-03 §5 verdict, shown in figures 1 and 3). The places of figure 1 follow WP-C-01
Figure 3-2 and the TARA view (02-concept/figures/fig_c09_boundary.py); which claim sits on which boundary is CLAIM_AT.

    python3 dfa_figures.py            # write the five SVGs
    python3 dfa_figures.py --check    # fail if an SVG is stale or EXAMPLE is not an AND gate across elements

Needs PyYAML (through dfa_gates.py). Output is deterministic.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parents[1]
sys.path.insert(0, str(HERE))
import dfa_gates  # noqa: E402
sys.path.insert(0, str(A / "03-system" / "figures"))
from fig_s03_defence_in_depth import (INK, MUTED, FAINT, LINE, HAIR, SW, SW_BG, AMBER, AMBER_BG,  # noqa: E402
                                      RED, RED_BG, GREY_BG, CHIP, MONO, text, rect, line, svg, header, el)
sys.path.insert(0, str(A / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)
sys.path.insert(0, str(A / "02-concept" / "hara"))
from hara_figures import wrap  # noqa: E402

EXAMPLE = "G-LATCUE"          # the gate figure 4 works through: two inputs, five shared resources, one analysed
W = 1120
REF = "WP-A-03 §5.1 · dfa_gates.py"
OUTS = {"boundary": HERE / "fig-dfa-1-boundary.svg", "method": HERE / "fig-dfa-2-method.svg",
        "gaps": HERE / "fig-dfa-3-gaps.svg", "gates": HERE / "fig-dfa-4-gates.svg",
        "example": HERE / "fig-dfa-5-example.svg"}

# what the check says about one (claim, resource) cell or one gate
STATE = {
  "analysed": ("analysed under the claim", SW, SW_BG, ""),
  "gap": ("not analysed under the claim", AMBER, AMBER_BG, ""),
  "none": ("no claim covers the gate", RED, RED_BG, ""),
  "unknown": ("dependence not known yet", MUTED, "#FFFFFF", "4 3"),
  "other": ("not an independence gate", FAINT, GREY_BG, ""),
}


class FigureError(ValueError):
  pass


def data():
  rows, no_claim, not_under, unknown, res, elements, claims = dfa_gates.analyse()
  _, _, _, dfis, claim_list = dfa_gates.load()
  under = dfa_gates.claim_dfis(dfis, claim_list)
  return {"rows": rows, "no_claim": no_claim, "not_under": not_under, "unknown": unknown, "res": res,
          "elements": elements, "claims": claims, "under": under}


def gate_state(r: dict, under: dict) -> tuple[str, list, list, list]:
  """(state, resources analysed, not analysed, unknown) of one gate."""
  if r["kind"] != "independence":
    return "other", [], [], []
  ics = dfa_gates.claims_of(r)
  covered = set().union(*(under[c] for c in ics)) if ics else set()
  ok, gap, maybe = [], [], []
  for res, m in r["shared"]:
    if m:
      maybe.append(res)
    elif ics and set(res["dfis"]) & covered:
      ok.append(res)
    else:
      gap.append(res)
  if not ics:
    return "none", ok, gap, maybe
  return ("gap" if gap else "unknown" if maybe else "analysed"), ok, gap, maybe


def pill(x, y, label, state, size=11, w=None):
  _, col, bg, dash = STATE[state]
  w = w or (len(label) * size * 0.56 + 22)
  return [rect(x, y, w, size + 11, fill=bg, stroke=col, sw=1.3, rx=(size + 11) / 2, dash=dash),
          text(x + w / 2, y + size + 4, label, size=size, fill=col if state != "other" else MUTED, weight=600,
               anchor="middle")], w


def finish(body, y, title, desc, note):
  body.append(text(40, y, note, size=11, fill=MUTED))
  extra, y = terms.svg_footer(body, 40, y + 22, W - 80)
  return svg(W, int(y + 12), title, desc, body + extra)


# ---------------------------------------------------------------- figure 1: how the check works

def fig_method(d) -> str:
  rows = d["rows"]
  kinds = defaultdict(int)
  for r in rows:
    kinds[r["kind"]] += 1
  ind = kinds["independence"]
  states = defaultdict(int)
  for r in rows:
    states[gate_state(r, d["under"])[0]] += 1
  n_res = len(d["res"]["resources"])
  body = header(W, "2", "How the AND gate check works",
                "Three sources are joined for every AND gate of the fault trees; the result is review input for WP-A-03",
                REF)
  # sources
  src = [("Fault trees", "WP-A-04, eight trees, one per safety goal", f"{len(rows)} AND gates"),
         ("Gate classification", "and-gates.yaml: the elements each input lies in, and the claim that covers it",
          f"{ind} across elements"),
         ("Shared-resource map", "shared-resources.yaml: what each element depends on, and the DFIs of each resource",
          f"{n_res} resources"),
         ("Claims and initiators", "WP-A-03 §2 claims IC-01…IC-07; §4 DFIs; §5 the DFIs listed under each claim",
          f"{len(d['claims'])} claims")]
  y0, bh, gap = 112, 76, 14
  x1, w1 = 40, 330
  for i, (name, what, n) in enumerate(src):
    y = y0 + i * (bh + gap)
    body += [rect(x1, y, w1, bh, fill=CHIP, stroke=LINE),
             text(x1 + 16, y + 24, name, size=13.5, weight=700),
             text(x1 + w1 - 16, y + 24, n, size=12, fill=MUTED, anchor="end", weight=600)]
    for k, ln in enumerate(wrap(what, w1 - 32, 11.5)[:2]):
      body.append(text(x1 + 16, y + 44 + k * 15, ln, size=11.5, fill=MUTED))
  mid_y = y0 + 2 * (bh + gap) - gap / 2
  # join
  x2, w2 = 430, 300
  jy, jh = y0 + 40, 4 * (bh + gap) - gap - 80
  body += [rect(x2, jy, w2, jh, fill="#FFFFFF", stroke=INK, sw=1.6),
           text(x2 + 18, jy + 30, "For each AND gate across elements", size=13.5, weight=700)]
  steps = ["Pair up its inputs that lie in different elements.",
           "Find the resources both inputs of a pair depend on: the shared resources.",
           "Take the DFIs of each shared resource.",
           "Is one of them listed under the gate's claim in WP-A-03?"]
  yy = jy + 58
  for k, s in enumerate(steps):
    body.append(text(x2 + 18, yy, f"{k + 1}", size=12, weight=700, fill=MUTED))
    for j, ln in enumerate(wrap(s, w2 - 60, 12)):
      body.append(text(x2 + 40, yy + j * 16, ln, size=12))
    yy += 16 * len(wrap(s, w2 - 60, 12)) + 14
  for i in range(4):
    y = y0 + i * (bh + gap) + bh / 2
    body.append(line(x1 + w1, y, x2 - 6, min(max(y, jy + 20), jy + jh - 20), stroke=FAINT, sw=1.3, marker="muted"))
  # outcomes
  x3, w3 = 790, W - 40 - 790
  outs = [("analysed", states["analysed"], "gates whose shared resources all have a DFI under the claim"),
          ("gap", states["gap"], "gates with a shared resource whose DFIs are not under the claim"),
          ("unknown", states["unknown"], "gates where a dependence is not known yet (and nothing else is missing)"),
          ("none", states["none"], "gates across elements that no claim covers"),
          ("other", kinds["same_element"] + kinds["common_cause"] + kinds["condition"],
           "same element, a common cause drawn as one event, or a driving situation")]
  oy, oh = y0 - 4, 66
  for k, (st, n, what) in enumerate(outs):
    y = oy + k * (oh + 8)
    _, col, bg, dash = STATE[st]
    body += [rect(x3, y, w3, oh, fill=bg, stroke=col, sw=1.3, dash=dash),
             text(x3 + 16, y + 38, str(n), size=26, weight=700, fill=col if st != "other" else MUTED),
             text(x3 + 70, y + 22, STATE[st][0], size=12.5, weight=700, fill=INK)]
    for j, ln in enumerate(wrap(what, w3 - 86, 11)[:3]):
      body.append(text(x3 + 70, y + 38 + j * 13.5, ln, size=11, fill=MUTED))
    body.append(line(x2 + w2, mid_y, x3 - 6, y + oh / 2, stroke=FAINT, sw=1.3, marker="muted"))
  y = max(y0 + 4 * (bh + gap), oy + 5 * (oh + 8)) + 18
  body.append(text(40, y, f"Also counted: {len(d['not_under'])} claim-and-resource pairs not analysed, "
                           f"{len(d['unknown'])} resources with an unknown dependence (dfa-gates.md, Findings).",
                   size=12, fill=INK))
  return finish(body, y + 24, "Figure 2. How the AND gate check works",
                f"{len(rows)} AND gates of WP-A-04; {ind} across elements are joined with {n_res} shared resources and "
                f"the DFIs of WP-A-03. " + "; ".join(f"{n} {STATE[s][0]}" for s, n, _ in outs) + ".",
                "Generated by dfa_figures.py from the join of dfa_gates.py. A gate analysed under its claim is not a "
                "verdict: the claim's verdict is WP-A-03 §5 (figures 1 and 3).")


# ---------------------------------------------------------------- figure 2: claims against shared resources

def fig_gaps(d) -> str:
  res = d["res"]["resources"]
  claim_ids = sorted({c for r in d["rows"] for c in dfa_gates.claims_of(r)})
  cells: dict[tuple[str, str], dict[str, list]] = defaultdict(lambda: defaultdict(list))
  for r in d["rows"]:
    st, ok, gap, maybe = gate_state(r, d["under"])
    if st == "other":
      continue
    keys = dfa_gates.claims_of(r) or ["none"]
    for x in ok:                                  # a gate under two claims: credit the claim that lists the DFI
      for k in keys:
        if set(x["dfis"]) & d["under"][k]:
          cells[(k, x["id"])]["analysed"].append(r["gate"])
    for k in keys:
      for x in gap:
        cells[(k, x["id"])]["none" if k == "none" else "gap"].append(r["gate"])
      for x in maybe:
        cells[(k, x["id"])]["unknown"].append(r["gate"])
  lines_ = claim_ids + (["none"] if any(k[0] == "none" for k in cells) else [])
  body = header(W, "3", "Where a dependent failure can start, claim by claim",
                "Each cell: the AND gates under that claim whose inputs share the resource, and whether WP-A-03 "
                "lists one of its DFIs under the claim", REF)
  x0, cw, top, rh = 250, 38, 150, 46
  vx = x0 + cw * len(res) + 16
  cats = []
  for i, r in enumerate(res):
    cx = x0 + i * cw + cw / 2
    body.append(text(cx, top - 14, r["id"].replace("R-", ""), size=11, weight=700, anchor="middle"))
    if not cats or cats[-1][0] != r["category"]:
      cats.append([r["category"], i, i])
    else:
      cats[-1][2] = i
  body.append(text(x0 - 12, top - 14, "Shared resource R-", size=11, fill=MUTED, anchor="end"))
  for cat, a, b in cats:
    xa, xb = x0 + a * cw + 3, x0 + (b + 1) * cw - 3
    body.append(line(xa, top - 40, xb, top - 40, stroke=LINE, sw=2))
    label = cat if (b - a + 1) * cw >= len(cat) * 6.2 else CAT_SHORT.get(cat, cat)
    body.append(text((xa + xb) / 2, top - 46, label, size=10, fill=MUTED, anchor="middle"))
  body.append(text(vx, top - 14, "WP-A-03 §5 verdict", size=11, fill=MUTED, weight=700))
  for k, c in enumerate(lines_):
    y = top + k * rh
    if k % 2 == 0:
      body.append(rect(32, y, W - 64, rh, fill="#F8FAFC", stroke="none", rx=0, sw=0))
    if c == "none":
      body += [text(44, y + 20, "No claim", size=13, weight=700, fill=RED),
               text(44, y + 36, "gates across elements no claim covers", size=10.5, fill=MUTED)]
    else:
      cl = d["claims"][c]
      body += [text(44, y + 20, c, size=13, weight=700),
               text(44, y + 36, wrap(claim_title(cl), 190, 10.5)[0], size=10.5, fill=MUTED)]
    for i, r in enumerate(res):
      cell = cells.get((c, r["id"]))
      if not cell:
        continue
      st = next(s for s in ("none", "gap", "unknown", "analysed") if cell.get(s))
      n = len(set(cell[st]))
      _, col, bg, dash = STATE[st]
      cx = x0 + i * cw
      body += [rect(cx + 3, y + 7, cw - 6, rh - 14, fill=bg, stroke=col, sw=1.4, rx=5, dash=dash),
               text(cx + cw / 2, y + rh / 2 + 4.5, str(n) if st != "unknown" else "?", size=12, weight=700,
                    fill=col, anchor="middle")]
    if c != "none":
      v = d["claims"][c].verdict
      st = "none" if v.lower().startswith("not") else "gap" if v.lower().startswith("partly") else "unknown"
      p, _ = pill(vx, y + 12, short_verdict(v), st, size=10.5)
      body += p
  y = top + len(lines_) * rh + 26
  lx = 40
  for st in ("analysed", "gap", "none", "unknown"):
    _, col, bg, dash = STATE[st]
    body += [rect(lx, y - 13, 26, 18, fill=bg, stroke=col, sw=1.4, rx=4, dash=dash),
             text(lx + 34, y + 1, STATE[st][0], size=11.5)]
    lx += 60 + len(STATE[st][0]) * 6.3
  body.append(text(lx, y + 1, "number = AND gates", size=11.5, fill=MUTED))
  # resource key, two columns by id
  y += 30
  body.append(text(40, y, "Shared resources", size=12, weight=700))
  half = (len(res) + 1) // 2
  for i, r in enumerate(res):
    cx, cy = 40 + (i // half) * ((W - 80) / 2), y + 20 + (i % half) * 17
    body += [text(cx, cy, r["id"], size=11, weight=700, family=MONO),
             text(cx + 44, cy, f"{r['name']} ({', '.join(r['dfis'])})", size=11, fill=MUTED)]
  y += 20 + half * 17 + 10
  n_gap = sum(1 for k, v in cells.items() if v.get("gap"))
  return finish(body, y, "Figure 3. Claims against shared resources",
                f"{len(lines_)} rows of claims against {len(res)} shared resources; {n_gap} claim-and-resource cells "
                "where a shared resource is not analysed under the claim.",
                "Generated by dfa_figures.py from the join of dfa_gates.py; a cell lists the worst state among its "
                "gates. dfa-gates.md has the gates of every cell.")


CAT_SHORT = {"information": "info", "configuration": "config", "cascading": "casc.", "systematic": "syst.",
             "installation": "inst.", "environment": "env.", "shared part": "part", "physical": "phys."}


def claim_title(cl) -> str:
  return {"IC-01": "envelope vs SoC command path", "IC-02": "envelope vs EPS limits",
          "IC-03": "envelope and EPS vs driver", "IC-04": "cluster shows engagement on its own",
          "IC-05": "stock PCS unaffected", "IC-06": "panda buzzer vs SoC HMI",
          "IC-07": "fallback monitor vs envelope"}.get(cl.ident, "")


def short_verdict(v: str) -> str:
  v = v.replace("*", "").strip()
  return v.split("(")[0].split(";")[0].strip().rstrip(".") or "—"


# ---------------------------------------------------------------- figure 3: every gate by safety goal

def fig_gates(d) -> str:
  by_goal: dict[str, list] = defaultdict(list)
  for r in d["rows"]:
    by_goal[r["goal"]].append(r)
  goals = sorted(by_goal, key=lambda g: int(g.split("-")[1]))
  body = header(W, "4", "Every AND gate, by safety goal",
                "What the check found for each gate of the WP-A-04 fault trees", REF)
  y = 116
  lx = 40
  for st in ("analysed", "gap", "unknown", "none", "other"):
    _, col, bg, dash = STATE[st]
    body += [rect(lx, y - 13, 26, 18, fill=bg, stroke=col, sw=1.4, rx=9, dash=dash),
             text(lx + 34, y + 1, STATE[st][0], size=11.5)]
    lx += 56 + len(STATE[st][0]) * 6.2
  y += 26
  chip_w, chip_h, gx = 112, 44, 10
  per_row = int((W - 80 - 110) // (chip_w + gx))
  for g in goals:
    gs = by_goal[g]
    n_rows = (len(gs) + per_row - 1) // per_row
    h = n_rows * (chip_h + 8) + 12
    body += [line(40, y, W - 40, y, stroke=HAIR, sw=1), text(44, y + 28, g, size=14, weight=700)]
    counts = defaultdict(int)
    for k, r in enumerate(gs):
      st, ok, gap, maybe = gate_state(r, d["under"])
      counts[st] += 1
      _, col, bg, dash = STATE[st]
      cx = 150 + (k % per_row) * (chip_w + gx)
      cy = y + 10 + (k // per_row) * (chip_h + 8)
      sub = {"analysed": ", ".join(dfa_gates.claims_of(r)), "none": "no claim",
             "gap": f"{', '.join(dfa_gates.claims_of(r))} · {len(gap)} not",
             "unknown": f"{', '.join(dfa_gates.claims_of(r))} · ?",
             "other": r["kind"].replace("_", " ")}[st]
      body += [rect(cx, cy, chip_w, chip_h, fill=bg, stroke=col, sw=1.3, rx=8, dash=dash),
               text(cx + 10, cy + 18, r["gate"], size=12, weight=700, family=MONO,
                    fill=INK if st != "other" else MUTED),
               text(cx + 10, cy + 34, sub if len(sub) <= 20 else sub[:19] + "…", size=10.5,
                    fill=col if st not in ("other", "unknown") else MUTED)]
    body.append(text(44, y + 46, f"{len(gs)} gate{'s' * (len(gs) != 1)}", size=10.5, fill=MUTED))
    y += max(h, 64)
  body.append(line(40, y, W - 40, y, stroke=HAIR, sw=1))
  y += 26
  body.append(text(40, y, "\"IC-06 · 6 not\": the gate is under claim IC-06 and 6 resources its inputs share have no "
                          "DFI listed under IC-06.", size=11.5, fill=INK))
  return finish(body, y + 24, "Figure 4. Every AND gate, by safety goal",
                f"{len(d['rows'])} AND gates across {len(goals)} safety goals, each marked with what the check found.",
                "Generated by dfa_figures.py from the join of dfa_gates.py; dfa-gates.md has one row per gate.")


# ---------------------------------------------------------------- figure 4: one gate worked through

def fig_example(d) -> str:
  r = next((x for x in d["rows"] if x["gate"] == EXAMPLE), None)
  if r is None or r["kind"] != "independence" or len(r["inputs"]) != 2:
    raise FigureError(f"EXAMPLE {EXAMPLE}: not an AND gate across elements with two inputs; choose another")
  st, ok, gap, maybe = gate_state(r, d["under"])
  ics = dfa_gates.claims_of(r)
  claim = ", ".join(ics) or "no claim"
  els = d["elements"]
  body = header(W, "5", f"One gate worked through: {r['gate']} ({r['goal']})",
                "Its two inputs, the elements they lie in, the resources both depend on, and whether WP-A-03 has "
                "analysed each one under the gate's claim", REF)
  # the gate
  gw = 560
  gx, gy = (W - gw) / 2, 108
  gt = wrap(r["text"], gw - 40, 12.5)
  gh = 48 + 17 * len(gt)
  body += [rect(gx, gy, gw, gh, fill="#FFFFFF", stroke=INK, sw=1.6),
           text(gx + 18, gy + 26, f"{r['gate']}  ·  AND gate  ·  claim {claim}", size=13, weight=700)]
  for k, ln in enumerate(gt):
    body.append(text(gx + 18, gy + 48 + k * 17, ln, size=12.5, fill=MUTED))
  # inputs
  iw, ih = 250, 0
  names = list(r["inputs"])
  in_y = gy + gh + 50
  cards = []
  for k, name in enumerate(names):
    ix = 40 if k == 0 else W - 40 - iw
    lines_ = [f"{e} {els[e]}" for e in r["inputs"][name]]
    wrapped = [w_ for ln in lines_ for w_ in wrap(ln, iw - 32, 11.5)]
    h = 46 + 16 * len(wrapped)
    ih = max(ih, h)
    cards.append((ix, name, wrapped))
  for ix, name, wrapped in cards:
    body += [rect(ix, in_y, iw, ih, fill=CHIP, stroke=LINE),
             text(ix + 16, in_y + 24, f"Input {name}", size=12.5, weight=700, family=MONO),
             text(ix + iw - 16, in_y + 24, "lies in", size=10.5, fill=MUTED, anchor="end")]
    for j, ln in enumerate(wrapped):
      body.append(text(ix + 16, in_y + 46 + j * 16, ln, size=11.5))
    tx = gx + 70 if ix < W / 2 else gx + gw - 70
    body.append(line(ix + iw / 2, in_y, tx, gy + gh + 4, stroke=FAINT, sw=1.3, marker="muted"))
  # shared resources in the middle
  rx, rw = 40 + iw + 60, W - 2 * (40 + iw + 60)
  ry = in_y
  rows_ = [(x, "analysed") for x in ok] + [(x, "gap") for x in gap] + [(x, "unknown") for x in maybe]
  body.append(text(rx + rw / 2, ry - 12, f"Resources both inputs depend on ({len(rows_)})", size=12, weight=700,
                   anchor="middle"))
  y = ry
  for x, s in rows_:
    _, col, bg, dash = STATE[s]
    nm = wrap(f"{x['id']} {x['name']}", rw - 150, 12, bold=True)
    rh = 40 + 16 * len(nm)
    body.append(rect(rx, y, rw, rh, fill=bg, stroke=col, sw=1.3, dash=dash))
    body += [text(rx + 14, y + 22 + 16 * j, ln, size=12, weight=700) for j, ln in enumerate(nm)]
    body.append(text(rx + 14, y + 26 + 16 * len(nm), f"its DFIs: {', '.join(x['dfis'])}", size=11, fill=MUTED))
    lab = {"analysed": f"under {claim}", "gap": f"not under {claim}", "unknown": "not known"}[s]
    body.append(text(rx + rw - 14, y + 22, lab, size=11, weight=700, fill=col, anchor="end"))
    for ix, _, _ in cards:
      xa = ix + iw if ix < W / 2 else ix
      xb = rx if ix < W / 2 else rx + rw
      body.append(line(xa, in_y + ih / 2, xb, y + rh / 2, stroke=LINE, sw=1.2))
    y += rh + 10
  y = max(y, in_y + ih) + 22
  verdict = {"analysed": "Every shared resource has a DFI under the claim.",
             "gap": f"{len(gap)} of {len(rows_)} shared resources have no DFI under {claim}: WP-A-03 has not "
                    f"analysed them for this claim (finding, OI-12).",
             "unknown": "A dependence is not known yet.", "none": "No claim covers this gate."}[st]
  body.append(text(40, y, verdict, size=12.5, weight=700, fill=STATE[st][1]))
  return finish(body, y + 26, f"Figure 5. One gate worked through: {r['gate']}",
                f"{r['gate']} ({r['goal']}, claim {claim}): inputs " +
                "; ".join(f"{n} in {', '.join(v)}" for n, v in r["inputs"].items()) + ". " + verdict,
                "Generated by dfa_figures.py from the join of dfa_gates.py; the gate shown is set in the script.")


# ---------------------------------------------------------------- figure 1: the item boundary in the DFA view

# Places, as WP-C-01 Figure 3-2: id -> (x, y, w, h, title, inside the item). E-04 is the device frame.
PLACES = {
  "E-04": (266, 176, 712, 300, "E-04 comma device hardware", True),
  "E-01": (282, 222, 330, 130, "E-01 SoC software (openpilot)", True),
  "E-02": (282, 364, 330, 96, "E-02 ML models", True),
  "E-03": (702, 222, 260, 238, "E-03 panda safety MCU", True),
  "E-05": (430, 512, 260, 104, "E-05 harness and harness box", True),
  "EXT-CLU": (240, 700, 172, 112, "Cluster, cruise indicator", False),
  "EXT-PCM": (424, 700, 172, 112, "PCM, ACC execution", False),
  "EXT-EPS": (608, 700, 172, 112, "EPS", False),
  "EXT-CAM": (792, 700, 172, 112, "Stock camera and PCS", False),
  "DRIVER": (40, 222, 172, 238, "Driver", False),
}
# Where each claim of WP-A-03 §2 is drawn: (x, y) of its badge, and the line it sits on (or None).
CLAIM_AT = {
  "IC-01": ((657, 266), ((612, 263), (702, 263))),
  "IC-06": ((657, 366), ((612, 363), (702, 363))),
  "IC-04": ((330, 666), ((330, 460), (330, 700))),
  "IC-02": ((740, 666), ((740, 460), (740, 700))),
  "IC-05": ((900, 666), ((900, 460), (900, 700))),
  "IC-03": ((228, 490), ((212, 420), (266, 420))),
}


def resource_states(d) -> tuple[dict, dict]:
  """Per resource: 'gap' if some claim relies on it without listing its DFIs; per claim: its gap resources and gates."""
  st, per_claim = {}, defaultdict(lambda: {"gap": set(), "gates": set()})
  for (ic, r_id), gs in d["not_under"].items():
    st[r_id] = "gap"
    for c in ic.split(", "):
      per_claim[c]["gap"].add(r_id)
  for r in d["rows"]:
    for c in dfa_gates.claims_of(r):
      per_claim[c]["gates"].add(r["gate"])
  return st, per_claim


def verdict_state(v: str) -> str:
  lv = v.replace("*", "").strip().lower()
  return "none" if lv.startswith("not") else "gap" if lv.startswith("partly") else "unknown"


def fig_boundary(d) -> str:
  WB = 1280
  res = d["res"]["resources"]
  rstate, per_claim = resource_states(d)
  missing = [c for c in per_claim if c not in CLAIM_AT]
  if missing:
    raise FigureError(f"claims {', '.join(missing)} are used by AND gates but have no place in CLAIM_AT")
  body = [text(40, 44, "Figure 1 · The item boundary in the DFA view", size=20, weight=700),
          text(40, 66, "WP-C-01 Figure 3-2 with the dependent failure analysis on it: the shared resources each element "
                       "depends on, and the independence claims between elements", size=12.5, fill=MUTED),
          text(WB - 40, 44, "WP-A-03 §2, §5, §5.1", size=11, fill=MUTED, anchor="end"),
          text(WB - 40, 60, "layout: WP-C-01 Figure 3-2", size=11, fill=MUTED, anchor="end"),
          line(40, 82, WB - 40, 82, stroke=HAIR, sw=1)]
  body += [rect(244, 150, 736, 492, fill="#FFFDF7", stroke="#C2410C", sw=1.6, rx=16, dash="7 5"),
           rect(262, 136, 190, 26, fill="#C2410C", stroke="none", rx=13, sw=0),
           text(357, 153.5, "ITEM BOUNDARY · LD-SDA", size=11, fill="#FFFFFF", weight=700, anchor="middle")]
  for p, (x, y, w, h, title, inside) in PLACES.items():
    deps = [r for r in res if p in r["elements"] or p in r.get("unknown", [])]
    fill = "#FFFFFF" if inside else "#F8FAFC"
    body.append(rect(x, y, w, h, fill=fill, stroke="#94A3B8" if p == "E-04" else LINE, sw=1.3, rx=10,
                     dash="" if inside else "5 4"))
    body.append(text(x + 12, y + 20, title, size=12.5, weight=700))
    cx, cy = x + 12, y + 30
    if p == "E-04":                                   # the frame: its chips run along the top, right of the title
      cx, cy = x + 240, y + 7
    for r in deps:
      maybe = p in r.get("unknown", [])
      s = "unknown" if maybe else rstate.get(r["id"], "plain")
      lab = r["id"] + ("?" if maybe else "")
      cw = len(lab) * 6.6 + 12
      right = x + w - 10
      if cx + cw > right:
        cx, cy = (x + 240 if p == "E-04" else x + 12), cy + 22
      if s == "plain":
        col, bg, dash = MUTED, "#FFFFFF", ""
      else:
        _, col, bg, dash = STATE[s]
      body += [rect(cx, cy, cw, 18, fill=bg, stroke=col, sw=1.2, rx=4, dash=dash),
               text(cx + cw / 2, cy + 13, lab, size=10, weight=700, fill=INK if s == "plain" else col,
                    anchor="middle", family=MONO)]
      cx += cw + 5
  # no-claim gates, on the element pair they cross
  nc = [r for r in d["rows"] if r["gate"] in d["no_claim"]]
  pcm = [r["gate"] for r in nc if any("EXT-PCM" in v for v in r["inputs"].values())]
  others = [r["gate"] for r in nc if r["gate"] not in pcm]
  x, y, w, h, *_ = PLACES["EXT-PCM"]
  if pcm:
    body.append(text(x + 12, y + h - 30, "no claim:", size=10, weight=700, fill=RED))
    for k, ln in enumerate(wrap(", ".join(pcm), w - 24, 10)[:2]):
      body.append(text(x + 12, y + h - 17 + k * 12, ln, size=10, fill=RED))
  x, y, w, h, *_ = PLACES["E-02"]
  if others:
    body.append(text(x + w - 12, y + 20, "no claim: " + ", ".join(others), size=10, weight=700, fill=RED,
                     anchor="end"))
  # claims on their boundaries
  for c, ((bx, by), seg) in CLAIM_AT.items():
    if c not in per_claim:
      continue
    v = d["claims"][c].verdict
    s = verdict_state(v)
    _, col, bg, dash = STATE[s]
    if seg:
      (x1, y1), (x2, y2) = seg
      body.append(line(x1, y1, x2, y2, stroke=col, sw=2.2, dash="6 4"))
    n_gap = len(per_claim[c]["gap"])
    body += [rect(bx - 34, by - 14, 68, 22, fill=bg, stroke=col, sw=1.6, rx=11, dash=dash),
             text(bx, by + 2, c, size=11, weight=700, fill=col, anchor="middle"),
             text(bx, by + 22, f"{n_gap} not analysed" if n_gap else "all analysed", size=9.5,
                  fill=AMBER if n_gap else SW, weight=700, anchor="middle")]
  # claims panel, right
  px, py, pw = 1000, 150, WB - 40 - 1000
  body.append(text(px, py, "Independence claims (WP-A-03 §2, §5)", size=12, fill=INK, weight=700))
  py += 14
  for c in sorted(per_claim):
    cl = d["claims"][c]
    s = verdict_state(cl.verdict)
    _, col, bg, dash = STATE[s]
    gaps = sorted(per_claim[c]["gap"])
    body += [rect(px, py, 50, 20, fill=bg, stroke=col, sw=1.4, rx=10, dash=dash),
             text(px + 25, py + 14, c, size=10.5, weight=700, fill=col, anchor="middle"),
             text(px + 58, py + 14, short_verdict(cl.verdict), size=11, weight=700, fill=col)]
    yy = py + 34
    for ln in wrap(claim_title(cl), pw, 10.5):
      body.append(text(px, yy, ln, size=10.5))
      yy += 13
    n_g = len(per_claim[c]["gates"])
    gl = f"{n_g} AND gate{'s' * (n_g != 1)}" + (f"; not analysed: {', '.join(gaps)}" if gaps else
                                                        "; every shared resource analysed")
    for ln in wrap(gl, pw, 10):
      body.append(text(px, yy, ln, size=10, fill=AMBER if gaps else MUTED))
      yy += 12.5
    py = yy + 10
  # resource key
  y = 846
  body.append(line(40, y, WB - 40, y, stroke=HAIR, sw=1))
  y += 24
  body.append(text(40, y, "Shared resources (shared-resources.yaml)", size=12, weight=700))
  third = (len(res) + 2) // 3
  for i, r in enumerate(res):
    kx, ky = 40 + (i // third) * ((WB - 80) / 3), y + 20 + (i % third) * 16
    nm = r["name"] if len(r["name"]) <= 58 else r["name"][:57] + "…"
    body += [text(kx, ky, r["id"], size=10.5, weight=700, family=MONO), text(kx + 40, ky, nm, size=10.5, fill=MUTED)]
  y += 20 + third * 16
  # legend
  body.append(line(40, y, WB - 40, y, stroke=HAIR, sw=1))
  y += 26
  lx = 40
  for lab, col, bg, dash in (("R-nn depends on it", MUTED, "#FFFFFF", ""),
                             ("a claim relies on it but WP-A-03 has not analysed it under that claim", AMBER, AMBER_BG, ""),
                             ("dependence not known yet (OI-2)", MUTED, "#FFFFFF", "4 3")):
    body += [rect(lx, y - 13, 30, 18, fill=bg, stroke=col, sw=1.2, rx=4, dash=dash),
             text(lx + 38, y + 1, lab, size=11)]
    lx += 60 + len(lab) * 6.1
  y += 24
  lx = 40
  for s, lab in (("none", "claim not independent"), ("gap", "partly"), ("unknown", "open")):
    _, col, bg, dash = STATE[s]
    body += [rect(lx, y - 13, 44, 18, fill=bg, stroke=col, sw=1.4, rx=9, dash=dash),
             text(lx + 52, y + 1, lab, size=11)]
    lx += 80 + len(lab) * 6.1
  body.append(text(lx, y + 1, "Claim colour: its WP-A-03 §5 verdict. Other road users share no resource.", size=11,
                   fill=MUTED))
  y += 26
  desc = ("The WP-C-01 item boundary with the WP-A-03 dependent failure analysis on it. " +
          " ".join(f"{PLACES[p][4]}: depends on " +
                   ", ".join(r["id"] for r in res if p in r["elements"] or p in r.get("unknown", [])) + "."
                   for p in PLACES) + " " +
          " ".join(f"{c} ({short_verdict(d['claims'][c].verdict)}): not analysed {', '.join(sorted(v['gap'])) or 'none'}."
                   for c, v in sorted(per_claim.items())))
  body.append(text(40, y, "Generated by dfa_figures.py from shared-resources.yaml, and-gates.yaml and WP-A-03. Where "
                          "each claim is drawn is CLAIM_AT in the script; the resource map is an AI-assisted draft.",
                   size=11, fill=MUTED))
  extra, y = terms.svg_footer(body, 40, y + 22, WB - 80)
  return svg(WB, int(y + 12), "Figure 1. The item boundary in the DFA view", desc, body + extra)


def build() -> dict[Path, str]:
  d = data()
  return {OUTS["boundary"]: fig_boundary(d), OUTS["method"]: fig_method(d), OUTS["gaps"]: fig_gaps(d), OUTS["gates"]: fig_gates(d),
          OUTS["example"]: fig_example(d)}


def main(argv: list[str]) -> int:
  try:
    out = build()
  except (dfa_gates.DfaError, FigureError) as e:
    print(f"error: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [p for p, c in out.items() if not p.exists() or p.read_text(encoding="utf-8") != c]
    for p in stale:
      print(f"stale: {p.name}; run dfa_figures.py", file=sys.stderr)
    if not stale:
      print(f"dfa_figures: {len(out)} figures current")
    return 1 if stale else 0
  for p, c in out.items():
    p.write_text(c, encoding="utf-8")
  print(f"wrote {', '.join(p.name for p in out)}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
