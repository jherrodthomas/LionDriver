#!/usr/bin/env python3
"""The V-cycle by standard: the same V, once per standard, showing which work products answer it and where.

GitHub cannot run a toggle inside a page, so the toggle is a row of links: the V-cycle section of the assurance
README and each overlay page carry "View by standard: All · ISO 26262 · ISO 21448 · ISO/SAE 21434 · ISO/PAS 8800 ·
ASPICE". Each link opens `assurance/01-management/vcycle/standard-<key>.md`: the V with each box showing how many of
its work products answer that standard and which clauses, then a table linking each of those work products.

Where each value comes from: the clause columns of the WP-M-00 register rows (through process_model.load_context):
`ISO 26262`, `ISO 21448`, `ISO/SAE 21434` and `ASPICE` as they are, and ISO/PAS 8800 from the rows of the `Other`
column that name "PAS 8800". A cell of "—" or blank does not count. The boxes are those of fig_m00_vcycle.py.

Fails (FigureError) when a standard's column answers no work product at all (a column moved or was renamed).
Called by fig_m00_vcycle.py; it has no command line of its own.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(A / "trace" / "tools"))

import figkit as fk  # noqa: E402
from figkit import FigureError, fmt, rect, text, line, path  # noqa: E402
import terms  # noqa: E402
import vcycle_explode as vx  # noqa: E402

# key, label, register column, filter on the cell (None: any non-empty cell counts)
STANDARDS = [("iso26262", "ISO 26262", "iso26262", None), ("iso21448", "ISO 21448", "iso21448", None),
             ("iso21434", "ISO/SAE 21434", "iso21434", None), ("pas8800", "ISO/PAS 8800", "other", "PAS 8800"),
             ("aspice", "ASPICE", "aspice", None)]
W, BW, BH, STEP, PITCH, Y0 = 1400, 400, 88, 36, 104, 150


def page_name(key: str) -> str:
  return f"standard-{key}.md"


def svg_name(key: str) -> str:
  return f"fig-m00-vcycle-std-{key}.svg"


# ---------------------------------------------------------------- reading the clause cells

def cell(row, col: str, needle: str | None) -> str:
  v = row.clauses.get(col, "").strip()
  if v in ("", "—", "-"):
    return ""
  if needle:
    if needle not in v:
      return ""
    m = re.search(rf"{re.escape(needle)}\s*\(([^)]*)\)", v)
    return m.group(1) if m else needle
  return v


def summary(key: str, cells: list[str]) -> str:
  """The clauses a box's work products cite, deduplicated, in first-seen order."""
  if key == "iso26262":
    parts: dict[str, list[str]] = {}
    for c in cells:
      part = None
      for tok in (t.strip() for t in re.split(r"[;,]", re.sub(r"\s*\([^)]*\)", "", c))):
        m = re.match(r"(\d+)\s+(.+)", tok)  # "9 §5" starts a new part; "§6" or "Annex C" continues it
        if m:
          part, tok = m.group(1), m.group(2).strip()
        if part and tok and tok not in parts.setdefault(part, []):
          parts[part].append(tok)
    return " · ".join(f"26262-{p} {', '.join(cls)}" for p, cls in parts.items())
  if key == "aspice":
    out: list[str] = []
    for c in cells:
      for tok in re.findall(r"[A-Z]{2,4}\.(?:\d+(?:–\d+)?|\*)|All in scope", c):
        if tok not in out:
          out.append(tok)
    return ", ".join(out)
  out = []
  for c in cells:
    for tok in (s.strip() for s in re.split(r"[;,]", re.sub(r"\s*\([^)]*\)", "", c))):
      if tok and tok not in out:
        out.append(tok)
  return ", ".join(out)


def overlay(m: dict, key: str, col: str, needle: str | None, register) -> dict:
  per_box = []
  for side, idx, b in vx.all_boxes(m):
    cells = {w: cell(register[w], col, needle) for w in b["ids"]}
    per_box.append({"side": side, "idx": idx, "box": b, "cells": cells,
                    "hit": [w for w in b["ids"] if cells[w]]})
  total = sum(len(p["hit"]) for p in per_box)
  if not total:
    raise FigureError(f"{key}: no work product answers it; did the {col!r} column of WP-M-00 §3 move?")
  return {"boxes": per_box, "total": total}


# ---------------------------------------------------------------- drawing

def toggle_row(key: str) -> list[str]:
  out, x = [text(40, 104, "View by standard:", 12, fk.MUTED, 700)], 160
  for k, label, _, _ in [("all", "All", None, None), *STANDARDS]:
    on = k == key
    p, w = fk.pill(0, 0, label, fk.OVERLAY if on else "#FFFFFF", "#FFFFFF" if on else fk.MUTED, h=22, size=11,
                   stroke=fk.OVERLAY if on else fk.LINE)
    out.append(f'<g transform="translate({x},{91})">' + "".join(p) + "</g>")
    x += w + 8
  return out


def box(x: float, y: float, w: float, p: dict, key: str, skew: int) -> list[str]:
  b, hit, n = p["box"], p["hit"], len(p["box"]["ids"])
  on = bool(hit)
  s = 12 * skew
  col = fk.OVERLAY if on else fk.FAINT
  out = [path(f"M{fmt(x + s)} {y} h{w} l{fmt(-2 * s)} {BH} h{-w} z", stroke=col, sw=1.6 if on else 1,
              fill=fk.OVERLAY_BG if on else "#FFFFFF", dash="" if on else "4 3")]
  tx = x + 24
  out.append(text(tx, y + 24, fk.fit(b["title"], w - 140, 14, True), 14, fk.INK if on else fk.FAINT, 700))
  out.append(text(x + w - 18, y + 24, f"{len(hit)} of {n}", 13, col, 700, "end"))
  sm = summary(key, [p["cells"][wp] for wp in hit]) if on else "no work product in this box answers it"
  out.append(text(tx, y + 44, fk.fit(sm, w - 50, 11.5), 11.5, fk.INK if on else fk.FAINT, style="" if on else "italic"))
  out.append(text(tx, y + 61, fk.fit(vx.pm_compress(hit) if on else vx.pm_compress(b["ids"]), w - 50, 10.5), 10.5,
                  fk.MUTED if on else fk.FAINT))
  seg = (w - 60) / n
  for k, wp in enumerate(b["ids"]):
    out.append(rect(tx + k * seg + 1, y + 69, max(seg - 2, 1), 8, fill=fk.OVERLAY if p["cells"][wp] else fk.HAIR,
                    stroke="none", rx=2, sw=0))
  return out


def draw(m: dict, key: str, label: str, ov: dict) -> tuple[int, list[str]]:
  n_wp = len(m["wps"])
  body = [text(40, 44, f"LionDriver V-cycle · {label}", 26, fk.INK, 700),
          text(40, 68, f"{ov['total']} of {n_wp} work products cite {label} in the register (WP-M-00 §3). Each box: how "
               "many of its work products do, and which clauses; one block per work product.", 13, fk.MUTED)]
  body += toggle_row(key)
  boxes = {(p["side"], p["idx"]): p for p in ov["boxes"]}
  nd = len(m["boxes"]["define"])
  for i in range(nd):
    y = Y0 + i * PITCH
    body += box(60 + i * STEP, y, BW, boxes[("define", i)], key, 1)
    body += box(W - 60 - BW - i * STEP, y, BW, boxes[("verify", i)], key, -1)
    body.append(line(60 + i * STEP + BW + 6, y + BH / 2, W - 60 - BW - i * STEP - 6, y + BH / 2, stroke=fk.HAIR,
                     sw=1.2, dash="5 5"))
  y = Y0 + nd * PITCH
  body += box((W - 640) / 2, y, 640, boxes[("build", 0)], key, 0)
  y += BH + 34
  body.append(text(60, y - 10, "Runs across every phase", 12, fk.MUTED, 700))
  cw = (W - 120 - 4 * 12) / 5
  for i in range(len(m["band"])):
    body += chip(60 + i * (cw + 12), y, cw, boxes[("band", i)], key)
  y += 96
  body.append(text(40, y, "A work product counts when its register row cites the standard. Citing a clause is not "
                   "meeting it: status is shown on the V, and nothing here is assessed or accepted.", 11.5, fk.MUTED,
                   style="italic"))
  foot, y = terms.svg_footer(body, 40, y + 24, W - 80)
  return int(y + 10), body + foot


def chip(x: float, y: float, w: float, p: dict, key: str) -> list[str]:
  hit, n = p["hit"], len(p["box"]["ids"])
  on = bool(hit)
  col = fk.OVERLAY if on else fk.FAINT
  out = [rect(x, y, w, 62, fill=fk.OVERLAY_BG if on else "#FFFFFF", stroke=col, sw=1.2, rx=10, dash="" if on else "4 3"),
         text(x + 12, y + 20, fk.fit(p["box"]["title"], w - 70, 12.5, True), 12.5, fk.INK if on else fk.FAINT, 700),
         text(x + w - 12, y + 20, f"{len(hit)} of {n}", 12, col, 700, "end"),
         text(x + 12, y + 37, fk.fit(summary(key, [p["cells"][wp] for wp in hit]) if on else "none", w - 24, 10.5),
              10.5, fk.INK if on else fk.FAINT)]
  seg = (w - 24) / n
  for k, wp in enumerate(p["box"]["ids"]):
    out.append(rect(x + 12 + k * seg + 1, y + 46, max(seg - 2, 1), 7, fill=fk.OVERLAY if p["cells"][wp] else fk.HAIR,
                    stroke="none", rx=2, sw=0))
  return out


# ---------------------------------------------------------------- pages and links

def toggle_md(current: str, up: str) -> str:
  """The link row. `up` is the path from the page to assurance/ (``""`` from the assurance README)."""
  here = "" if up else "01-management/vcycle/"
  items = ["**All**" if current == "all" else f"[All]({up}README.md#the-v-cycle)"]
  for k, label, _, _ in STANDARDS:
    items.append(f"**{label}**" if k == current else f"[{label}]({here}{page_name(k)})")
  return "View by standard: " + " · ".join(items)


def page(m: dict, key: str, label: str, ov: dict, register) -> str:
  lines = ["<!-- GENERATED by assurance/01-management/figures/fig_m00_vcycle.py from WP-M-00 §3. Do not edit. -->", "",
           f"# V-cycle by standard: {label}", "", toggle_md(key, "../../"), "",
           "<p align=\"center\">",
           f'  <a href="../../README.md#the-v-cycle"><img src="../figures/vcycle/{svg_name(key)}" width="100%" '
           f'alt="{alt(m, label, ov)}"></a>', "</p>", "",
           f"*The V-cycle with each box showing how many of its work products cite {label} in the "
           "[register](../WP-M-00-work-product-register.md), and which clauses. Citing a clause is not meeting it. "
           "Drawn by [`fig_m00_vcycle.py`](../figures/fig_m00_vcycle.py); CI fails if it is stale.*", "",
           f"## Work products that cite {label}", "", f"| Box | Work product | {label} |", "|---|---|---|"]
  for p in ov["boxes"]:
    for wp in p["hit"]:
      row = register[wp]
      rel = Path(os.path.relpath(row.path, vx.PAGES)).as_posix()
      lines.append(f"| [{p['box']['title']}]({vx.slug(p['box']['title'])}.md) | [{wp} {row.name}]({rel}) | "
                   f"{p['cells'][wp].replace('|', '/')} |")
  empty = [p["box"]["title"] for p in ov["boxes"] if not p["hit"]]
  lines += ["", "## Boxes with no work product citing it", ""]
  lines += [f"- {t}" for t in empty] or ["None."]
  return "\n".join(lines) + "\n"


def alt(m: dict, label: str, ov: dict) -> str:
  per = "; ".join(f"{p['box']['title']} {len(p['hit'])} of {len(p['box']['ids'])}" for p in ov["boxes"])
  return f"The V-cycle by standard, {label}: {ov['total']} of {len(m['wps'])} work products cite it. {per}."


def render(m: dict) -> dict[Path, str]:
  _, _, _, ctx = vx.process_facts()
  files = {}
  for key, label, col, needle in STANDARDS:
    ov = overlay(m, key, col, needle, ctx.register)
    h, body = draw(m, key, label, ov)
    files[vx.OUT / svg_name(key)] = fk.svg(W, h, f"LionDriver V-cycle by standard: {label}", alt(m, label, ov), body)
    files[vx.PAGES / page_name(key)] = page(m, key, label, ov, ctx.register)
  return files
