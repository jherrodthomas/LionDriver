#!/usr/bin/env python3
"""The safety case on the V-cycle: every claim, and the boxes of the V its evidence comes from.

It reads the Living Safety Case records (assurance/case-records, through caselib.load_case): the claims with their
parent and `evidence_refs`, and the open defeaters against each claim. Each evidence item sits on the box of the work
product it lives in, exactly as the evidence maturity view places it (vcycle_evidence.model); an item whose location
names no work product goes in the last column, "Not on the V".

Rows are the claims as a tree from the top claim; columns are the boxes in V order (down the definition side, build,
up the verification side, then the groups that run across every phase). A circle is that claim's evidence from that
box: its size the count, its colour the furthest step on the evidence maturity ladder any of them has reached.

What each claim stands on, from the sides its own evidence comes from:

- both sides of the V: evidence from a definition box and from a verification box;
- definition only: evidence from a definition box, and none from build or a verification box;
- verification only: evidence from a verification box, and none from a definition box;
- across the V: no evidence from either side, only from build, the cross-phase groups or off the V;
- through its sub-claims: no evidence of its own, but it has sub-claims;
- no evidence: neither.

One picture and one page, `assurance/01-management/vcycle/assurance-case.md`. Fails (FigureError) on a claim whose
parent is not a claim or that cites an evidence item that does not exist. Drawing a claim does not review or accept
it. Called by fig_m00_vcycle.py; it has no command line of its own.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(A / "trace" / "tools"))
sys.path.insert(0, str(A / "case-records" / "tools"))

import caselib  # noqa: E402
import figkit as fk  # noqa: E402
from figkit import FigureError, rect, text, line  # noqa: E402
import terms  # noqa: E402
import vcycle_evidence as ve  # noqa: E402
import vcycle_explode as vx  # noqa: E402

SVG = "fig-m00-vcycle-case.svg"
PAGE = "assurance-case.md"
OFF_V = "Not on the V"
GROUPS = [("define", "Definition, down the V", fk.DEFINE, fk.DEFINE_BG), ("build", "Build", fk.INK, fk.CHIP),
          ("verify", "Verification, up the V", fk.VERIFY, fk.VERIFY_BG), ("band", "Across every phase", fk.MUTED, fk.CHIP),
          ("off", "", fk.MUTED, "#FFFFFF")]
SHAPES = [  # name, colour, bold
  ("both sides of the V", fk.GREEN_DARK, False), ("definition only", fk.AMBER, True),
  ("verification only", fk.HW, False), ("across the V", fk.MUTED, False),
  ("through its sub-claims", fk.MUTED, False), ("no evidence", fk.RED, True)]
SHAPE = {s[0]: s for s in SHAPES}
W, TX, CX, CW, RH, HY = 1640, 40, 560, 40, 24, 300


# ---------------------------------------------------------------- data

def columns(m: dict) -> list[tuple[str, str]]:
  """(box title, group) in V order."""
  return ([(b["title"], "define") for b in m["boxes"]["define"]] + [(m["boxes"]["build"][0]["title"], "build")]
          + [(b["title"], "verify") for b in reversed(m["boxes"]["verify"])]
          + [(b["title"], "band") for b in m["band"]] + [(OFF_V, "off")])


def shape(groups: set[str], has_kids: bool) -> str:
  if not groups:
    return "through its sub-claims" if has_kids else "no evidence"
  if "define" in groups and "verify" in groups:
    return "both sides of the V"
  if "define" in groups and not groups & {"verify", "build"}:
    return "definition only"
  if "verify" in groups and "define" not in groups:
    return "verification only"
  return "across the V"


def model(m: dict) -> dict:
  case = caselib.load_case()
  ev = ve.model(m)
  items = {e["id"]: e for e in ev["evidence"]}
  box_of = {e["id"]: title for title, es in ev["per"].items() for e in es}
  cols = columns(m)
  group_of = dict(cols)
  claims = {c["id"]: c for c in case.of_kind("claim")}
  kids: dict[str, list[str]] = {}
  roots = []
  for c in claims.values():
    p = c.get("parent")
    if p is None:
      roots.append(c["id"])
    elif p not in claims:
      raise FigureError(f"{c['id']}: parent {p!r} is not a claim")
    else:
      kids.setdefault(p, []).append(c["id"])
  if len(roots) != 1:
    raise FigureError(f"expected one top claim, found {', '.join(sorted(roots)) or 'none'}")
  rows: list[dict] = []

  def walk(cid: str, depth: int) -> None:
    c = claims[cid]
    cells: dict[str, list[dict]] = {}
    for ref in c.get("evidence_refs") or []:
      if ref not in items:
        raise FigureError(f"{cid}: evidence {ref} is not an evidence record")
      cells.setdefault(box_of.get(ref, OFF_V), []).append(items[ref])
    groups = {group_of[b] for b in cells}
    defeaters = sorted(d["id"] for d in ev["open"] if cid in (d.get("related_claims") or []))
    rows.append({"id": cid, "title": c["title"], "depth": depth, "cells": cells, "defeaters": defeaters,
                 "shape": shape(groups, cid in kids), "status": c.get("lifecycle_status"),
                 "review": c.get("review_state") or "not-reviewed", "file": c.get("_file")})
    for k in kids.get(cid, []):
      walk(k, depth + 1)

  walk(roots[0], 0)
  return {"rows": rows, "cols": cols, "open": ev["open"]}


def counts(d: dict) -> dict[str, int]:
  return {s[0]: sum(1 for r in d["rows"] if r["shape"] == s[0]) for s in SHAPES}


# ---------------------------------------------------------------- drawing

def circle(cx: float, cy: float, rad: float, fill: str, stroke: str) -> str:
  return f'<circle cx="{fk.fmt(cx)}" cy="{fk.fmt(cy)}" r="{fk.fmt(rad)}" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>'


def header(d: dict) -> list[str]:
  cols, out = d["cols"], []
  table_h = 200 + RH * len(d["rows"]) + 8
  for key, label, colour, fill in GROUPS:
    idx = [i for i, (_, g) in enumerate(cols) if g == key]
    a, b = CX + idx[0] * CW, CX + (idx[-1] + 1) * CW
    out.append(rect(a + 1, HY - 200, b - a - 2, table_h, fill=fill, stroke=fk.LINE, sw=0.6, rx=6))
    if label:
      out.append(text((a + b) / 2, HY - 212, label, 11, colour, 700, "middle"))
  for i, (name, g) in enumerate(cols):
    colour = next(c for k, _, c, _ in GROUPS if k == g)
    x, y = CX + i * CW + CW / 2 + 4, HY - 8
    out.append(f'<g transform="rotate(-55 {fk.fmt(x)} {fk.fmt(y)})">'
               + text(x, y, fk.fit(name, 190, 11), 11, colour, 600) + "</g>")
  rx = CX + len(cols) * CW + 16
  out += [text(rx, HY - 8, "Stands on", 11, fk.MUTED, 700), text(rx + 170, HY - 8, "Open defeaters", 11, fk.MUTED, 700)]
  return out


def row(r: dict, y: float, cols: list[tuple[str, str]]) -> list[str]:
  out, dp = [], r["depth"]
  rx = CX + len(cols) * CW + 16
  if dp <= 1:
    out.append(line(TX, y, rx + 260, y, fk.LINE, 1.4 if dp == 0 else 1))
  x = TX + dp * 16
  out += [text(x, y + 16, r["id"], 11.5, fk.INK, 700),
          text(x + 52, y + 16, fk.fit(r["title"], CX - x - 62, 11.5, dp <= 1), 11.5, fk.INK, 700 if dp <= 1 else "")]
  for i, (name, _) in enumerate(cols):
    es = r["cells"].get(name)
    if es:
      name_, fill, stroke, _ = ve.LADDER[max(ve.level(e) for e in es)]
      cx = CX + i * CW + CW / 2
      out += [circle(cx, y + 12, 6 + 2 * min(len(es), 4), fill, stroke),
              text(cx, y + 16, str(len(es)), 10, stroke, 700, "middle")]
  name, colour, bold = SHAPE[r["shape"]]
  nd = len(r["defeaters"])
  out += [text(rx, y + 16, name, 11, colour, 700 if bold else ""),
          text(rx + 230, y + 16, str(nd) if nd else "–", 11.5, fk.SAFETY if nd else fk.FAINT, 700 if nd else "", "end")]
  return out


def legend(d: dict, y: float) -> tuple[float, list[str]]:
  c = counts(d)
  out = [text(TX, y, f"Stands on, for the {len(d['rows'])} claims:", 12, fk.INK, 700)]
  x = TX + fk.text_w(f"Stands on, for the {len(d['rows'])} claims:", 12, True) + 24
  for name, colour, _ in SHAPES:
    s = f"{c[name]} {name}"
    out.append(text(x, y, s, 12, colour if c[name] else fk.FAINT, 700))
    x += fk.text_w(s, 12, True) + 24
  y += 26
  lead = "Circle: evidence items from that box (size = count), coloured by the furthest step reached:"
  out.append(text(TX, y, lead, 11.5, fk.MUTED))
  x = TX + fk.text_w(lead, 11.5) + 12
  for name, fill, stroke, _ in ve.LADDER:
    out += [circle(x + 7, y - 4, 7, fill, stroke), text(x + 20, y, name.lower(), 11.5, stroke)]
    x += fk.text_w(name.lower(), 11.5) + 40
  return y, out


def draw(d: dict) -> tuple[int, list[str]]:
  body = [text(40, 44, "The safety case on the V-cycle", 26, fk.INK, 700),
          text(40, 68, "Every claim of the safety case (case-records), and the boxes of the V its evidence comes from: "
               "does each claim stand on both definition and verification?", 13, fk.MUTED)]
  body += header(d)
  y = HY + 6
  for r in d["rows"]:
    body += row(r, y, d["cols"])
    y += RH
  y, lg = legend(d, y + 24)
  body += lg
  body.append(text(TX, y + 24, "A claim's evidence is its evidence_refs in case-records; an item's box is where it "
                   "lives, as in evidence maturity. Drawing a claim does not review or accept it.", 11.5, fk.MUTED,
                   style="italic"))
  foot, y = terms.svg_footer(body, 40, y + 48, W - 80)
  return int(y + 10), body + foot


# ---------------------------------------------------------------- page

def page(m: dict, d: dict) -> str:
  c = counts(d)
  lines = ["<!-- GENERATED by assurance/01-management/figures/fig_m00_vcycle.py from assurance/case-records. "
           "Do not edit. -->", "", "# The safety case on the V-cycle", "",
           "[← Back to the V-cycle](../../README.md#the-v-cycle) · [evidence maturity](evidence.md) · "
           "[Living Safety Case](../../README.md#living-safety-case) · [records](../../case-records/README.md)", "",
           "<p align=\"center\">",
           f'  <a href="../../README.md#the-v-cycle"><img src="../figures/vcycle/{SVG}" width="100%" alt="{alt(d)}"></a>',
           "</p>", "",
           "*Every claim of the [safety case records](../../case-records/README.md), and the boxes of the V its "
           "evidence comes from. Drawing a claim does not review or accept it. Drawn by "
           "[`fig_m00_vcycle.py`](../figures/fig_m00_vcycle.py); CI fails if it is stale.*", "",
           "## What each claim stands on", "",
           "From the sides of the V its own evidence comes from: " + "; ".join(f"{c[s[0]]} {s[0]}" for s in SHAPES)
           + ".", "",
           "| Claim | Stands on | Evidence, by box | Open defeaters | Status | Review |", "|---|---|---|---|---|---|"]
  for r in d["rows"]:
    ev = "; ".join((f"[{b}]({vx.slug(b)}.md)" if b != OFF_V else b) + ": " + ", ".join(e["id"] for e in es)
                   for b, es in sorted(r["cells"].items(), key=lambda kv: [n for n, _ in d["cols"]].index(kv[0])))
    claim = ("&nbsp;" * 2 * r["depth"]) + f"{r['id']} {r['title'].replace('|', '/')}"
    if r["file"]:
      claim = ("&nbsp;" * 2 * r["depth"]) + f"[{r['id']}](../../../{r['file']}) {r['title'].replace('|', '/')}"
    lines.append(f"| {claim} | {r['shape']} | {ev or '—'} | {', '.join(r['defeaters']) or '—'} | {r['status']} | "
                 f"{r['review']} |")
  return "\n".join(lines) + "\n"


def alt(d: dict) -> str:
  c = counts(d)
  return (f"The safety case on the V-cycle: {len(d['rows'])} claims; " + ", ".join(f"{c[s[0]]} {s[0]}" for s in SHAPES)
          + f"; {len(d['open'])} open defeaters.")


def render(m: dict) -> dict[Path, str]:
  d = model(m)
  h, body = draw(d)
  return {vx.OUT / SVG: fk.svg(W, h, "The safety case on the V-cycle", alt(d), body), vx.PAGES / PAGE: page(m, d)}
