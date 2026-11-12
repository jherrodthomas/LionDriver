#!/usr/bin/env python3
"""The V-cycle crosswalk: every box of the V against every standard, in one table.

Rows are the boxes of the V, grouped by level and side in V order (down the definition side, implementation, up the
verification side), then the groups that run across every phase. Columns are the standards of vcycle_standards.py.
Each cell gives how many of the box's work products cite that standard in the WP-M-00 register, a bar for the share,
and the clauses they cite, sorted. A dash means none does.

One picture and one page, `assurance/01-management/vcycle/crosswalk.md`, reached from the "View by standard" link row
as "Crosswalk". The page repeats the table in Markdown with every clause in full and each box linked to its exploded
view, and links each standard's own page, which lists and links every citing work product.

Where each value comes from: the boxes from fig_m00_vcycle.build_model(); the levels from vcycle_time.LEVEL; the counts
and clauses from vcycle_standards.overlay() and summary(), which read the register's clause columns.

Fails (FigureError) through those modules: a standard's column citing nothing, or a side whose box count no longer
matches its levels. Called by fig_m00_vcycle.py; it has no command line of its own.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "trace" / "tools"))

import figkit as fk  # noqa: E402
from figkit import fmt, rect, text, line  # noqa: E402
import terms  # noqa: E402
import vcycle_explode as vx  # noqa: E402
import vcycle_standards as vs  # noqa: E402
import vcycle_time as vt  # noqa: E402

SVG = "fig-m00-vcycle-crosswalk.svg"
PAGE = "crosswalk.md"
W, X0, LW, BW, RH = 1760, 40, 120, 250, 62
SIDE = {"define": (fk.DEFINE, fk.DEFINE_BG, "define"), "build": (fk.INK, fk.GREY_BG, "build"),
        "verify": (fk.VERIFY, fk.VERIFY_BG, "verify"), "band": (fk.MUTED, fk.CHIP, "all phases")}


def groups(m: dict) -> list[tuple[str, str, list[dict]]]:
  """(level, side, boxes) in V order; neighbouring boxes of one level and side share a group."""
  out: list[tuple[str, str, list[dict]]] = []
  for r in vt.rows(m):
    if out and out[-1][0] == r["level"] and out[-1][1] == r["side"]:
      out[-1][2].append(r["box"])
    else:
      out.append((r["level"], r["side"], [r["box"]]))
  out.append(("Across phases", "band", list(m["band"])))
  return out


def cells(m: dict) -> dict:
  """standard key -> box title -> {"hit": [...], "of": n, "clauses": str}, and the totals."""
  _, _, _, ctx = vx.process_facts()
  out, totals = {}, {}
  for key, _, col, needle in vs.STANDARDS:
    ov = vs.overlay(m, key, col, needle, ctx.register)
    totals[key] = ov["total"]
    out[key] = {p["box"]["title"]: {"hit": p["hit"], "of": len(p["box"]["ids"]),
                                    "clauses": vs.summary(key, [p["cells"][w] for w in p["hit"]]) if p["hit"] else ""}
                for p in ov["boxes"]}
  return {"cells": out, "totals": totals}


def wrap(s: str, width: float, size: float, max_lines: int) -> list[str]:
  words, lines = s.split(" "), [""]
  for w in words:
    cand = (lines[-1] + " " + w).strip()
    if lines[-1] and fk.text_w(cand, size) > width:
      if len(lines) == max_lines:
        lines[-1] = lines[-1].rstrip(",·") + " …"
        return lines
      lines.append(w)
    else:
      lines[-1] = cand
  return lines


def draw(m: dict, gs, c: dict) -> tuple[int, list[str]]:
  cw = (W - 80 - LW - BW) / len(vs.STANDARDS)
  body = [text(40, 44, "V-cycle crosswalk: which clauses each box answers", 26, fk.INK, 700),
          text(40, 68, "Rows: the boxes of the V, grouped by level and side. Columns: the standards. Each cell: how many "
               "of the box's work products cite the standard, and the clauses they cite (WP-M-00 §3).", 13, fk.MUTED)]
  body += vs.toggle_row("crosswalk")
  y = 128
  body.append(rect(X0, y, W - 80, 40, fill=fk.INK, stroke="none", rx=8, sw=0))
  body += [text(X0 + 14, y + 25, "Level", 12.5, "#FFFFFF", 700), text(X0 + LW + 14, y + 25, "Box on the V", 12.5,
                                                                         "#FFFFFF", 700)]
  for i, (key, label, _, _) in enumerate(vs.STANDARDS):
    x = X0 + LW + BW + i * cw
    body += [text(x + 14, y + 25, label, 12.5, "#FFFFFF", 700),
             text(x + cw - 12, y + 25, f"{c['totals'][key]} cite it", 11, fk.LINE, anchor="end")]
  y += 48
  for gi, (level, side, boxes) in enumerate(gs):
    col, bg, word = SIDE[side]
    gh = RH * len(boxes)
    body.append(rect(X0, y, W - 80, gh - 4, fill=fk.CHIP if gi % 2 == 0 else "#FFFFFF", stroke=fk.HAIR, sw=1, rx=6))
    p, _ = fk.pill(0, 0, level, bg, col, h=20, size=10.5, stroke=col)
    body.append(f'<g transform="translate({X0 + 12},{fmt(y + 12)})">' + "".join(p) + "</g>")
    body.append(text(X0 + 14, y + 48, word, 10.5, fk.FAINT, style="italic"))
    for bi, b in enumerate(boxes):
      yy = y + bi * RH
      if bi:
        body.append(line(X0 + LW, yy - 2, W - 40, yy - 2, stroke=fk.HAIR, sw=1))
      n = len(b["ids"])
      body += [text(X0 + LW + 14, yy + 22, fk.fit(b["title"], BW - 24, 12.5, True), 12.5, fk.INK, 700),
               text(X0 + LW + 14, yy + 40, f"{n} work product{'s' if n != 1 else ''}", 10.5, fk.MUTED)]
      for i, (key, _, _, _) in enumerate(vs.STANDARDS):
        x, cell = X0 + LW + BW + i * cw, c["cells"][key][b["title"]]
        if not cell["hit"]:
          body.append(text(x + 14, yy + 24, "—", 13, fk.FAINT))
          continue
        share = len(cell["hit"]) / cell["of"]
        body += [rect(x + 10, yy + 9, cw - 24, 4, fill=fk.HAIR, stroke="none", rx=2, sw=0),
                 rect(x + 10, yy + 9, max(4, (cw - 24) * share), 4, fill=fk.OVERLAY, stroke="none", rx=2, sw=0),
                 text(x + cw - 14, yy + 26, f"{len(cell['hit'])}/{cell['of']}", 10.5, fk.OVERLAY, 700, "end")]
        for li, ln in enumerate(wrap(cell["clauses"], cw - 70, 11, 2)):
          body.append(text(x + 14, yy + 26 + li * 15, ln, 11, fk.INK))
    y += gh + 6
  body.append(text(40, y + 18, "Read across a row to see how one box serves several standards; down a column to see "
                   "where a standard's work sits on the V. The bar is the share of the box's work products that cite "
                   "the standard.", 11.5, fk.MUTED))
  body.append(text(40, y + 38, "Built from the register's clause columns. A work product citing a clause is not "
                   "evidence the clause is met. Long cells are cut at two lines; the page lists every clause.", 11,
                   fk.MUTED, style="italic"))
  foot, y = terms.svg_footer(body, 40, y + 62, W - 80)
  return int(y + 10), body + foot


def page(m: dict, gs, c: dict) -> str:
  heads = [label for _, label, _, _ in vs.STANDARDS]
  lines = ["<!-- GENERATED by assurance/01-management/figures/fig_m00_vcycle.py from WP-M-00 §3. Do not edit. -->", "",
           "# V-cycle crosswalk", "", vs.toggle_md("crosswalk", "../../"), "",
           "<p align=\"center\">",
           f'  <a href="../../README.md#the-v-cycle"><img src="../figures/vcycle/{SVG}" width="100%" alt="{alt(m, c)}">'
           "</a>", "</p>", "",
           "*Every box of the V against every standard: how many of its work products cite the standard in the "
           "[register](../WP-M-00-work-product-register.md), and which clauses. Citing a clause is not meeting it. "
           "Drawn by [`fig_m00_vcycle.py`](../figures/fig_m00_vcycle.py); CI fails if it is stale.*", "",
           "## The crosswalk in full", "",
           "Each box opens its exploded view; each standard's heading opens the page that links every work product "
           "citing it.", "",
           "| Level | Box | " + " | ".join(f"[{h}]({vs.page_name(k)})" for (k, _, _, _), h in zip(vs.STANDARDS, heads))
           + " |", "|---|---|" + "---|" * len(heads)]
  for level, side, boxes in gs:
    for b in boxes:
      row = [f"{level} ({SIDE[side][2]})", f"[{b['title']}]({vx.slug(b['title'])}.md)"]
      for key, _, _, _ in vs.STANDARDS:
        cell = c["cells"][key][b["title"]]
        row.append(f"{len(cell['hit'])} of {cell['of']}: {cell['clauses']}".replace("|", "/") if cell["hit"] else "—")
      lines.append("| " + " | ".join(row) + " |")
  return "\n".join(lines) + "\n"


def alt(m: dict, c: dict) -> str:
  tot = ", ".join(f"{label} {c['totals'][k]}" for k, label, _, _ in vs.STANDARDS)
  return (f"The V-cycle crosswalk: each box of the V against five standards, with how many of its work products cite "
          f"each and which clauses. Work products citing each standard, of {len(m['wps'])}: {tot}.")


def render(m: dict) -> dict[Path, str]:
  gs, c = groups(m), cells(m)
  h, body = draw(m, gs, c)
  return {vx.OUT / SVG: fk.svg(W, h, "LionDriver V-cycle crosswalk", alt(m, c), body), vx.PAGES / PAGE: page(m, gs, c)}
