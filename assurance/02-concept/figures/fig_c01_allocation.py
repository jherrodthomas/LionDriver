#!/usr/bin/env python3
"""Draw WP-C-01 Figure 3-4, the functions on the elements (fig-c01-3-4-function-allocation.svg).

One row per function of WP-C-01 §2.1, one column per element inside the item (§3.1) and per element outside it that
the function relies on (§3.2). A cell says what the element does for the function:

  realizes  its code, model or hardware performs the function (the "Main implementation" of §2.1)
  carries   it hosts or passes the function on without deciding anything (device hardware, harness, the envelope's
            checks on a command it did not make)
  relies on an element outside the item the function needs, credited only through an assumption of use (§3.2, §7)

The cells are an analyst reading of §2.1 and §3.1–§3.2 (`ALLOCATION` below), because §2.1 names code paths rather than
elements. The build fails if a function or element is missing from `ALLOCATION` or names one WP-C-01 does not have.

    python3 fig_c01_allocation.py            # write the SVG
    python3 fig_c01_allocation.py --check    # fail if a function or element is unmapped or the SVG is stale

Standard library only. Drawing helpers come from ../hara/hara_figures.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "WP-C-01-item-definition.md"
OUT = "fig-c01-3-4-function-allocation.svg"
sys.path.insert(0, str(HERE.parent / "hara"))
import hara_figures as hf  # noqa: E402
from hara_figures import INK, MUTED, HAIR, t, wrap, header, svg_doc  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)

INSIDE = [("E-01", "SoC software"), ("E-02", "ML models"), ("E-03", "safety MCU firmware"), ("E-04", "device hardware"),
          ("E-05", "harness")]
OUTSIDE = [("EPS", "Toyota EPS"), ("PCM", "PCM and brakes"), ("CAM", "forward camera"), ("RADAR", "forward radar"),
           ("CLUSTER", "cluster and stalk"), ("DRIVER", "driver"), ("BACKEND", "comma.ai back end")]
# §3.2 row each outside column stands for (the first words of its Element cell), checked against the document.
OUTSIDE_ROW = {"EPS": "Toyota EPS", "PCM": "Engine/powertrain ECU", "CAM": "Toyota forward camera",
               "RADAR": "Toyota forward radar", "CLUSTER": "Instrument cluster", "DRIVER": "Driver",
               "BACKEND": "comma.ai back end"}
R, C, X = "realizes", "carries", "relies on"
ALLOCATION = {
  "F-01": {"E-01": R, "E-02": R, "E-03": C, "E-04": C, "E-05": C, "EPS": X, "DRIVER": X},
  "F-02": {"E-01": R, "E-02": R, "E-03": C, "E-04": C, "E-05": C, "PCM": X, "RADAR": X, "DRIVER": X},
  "F-03": {"E-01": R, "E-03": R, "E-04": C, "PCM": X, "CLUSTER": X, "DRIVER": X},
  "F-04": {"E-01": R, "E-02": R, "E-04": C, "DRIVER": X},
  "F-05": {"E-01": R, "E-04": C, "CLUSTER": X, "DRIVER": X},
  "F-06": {"E-01": R, "E-02": R, "E-04": C, "DRIVER": X},
  "F-07": {"E-01": R, "E-02": R, "E-04": C, "DRIVER": X},
  "F-08": {"E-03": R, "E-04": C, "E-05": C, "CAM": X},
  "F-09": {"E-01": R, "E-04": C, "BACKEND": X},
}


class AllocationError(ValueError):
  pass


def _cells(ln: str) -> list[str]:
  return [c.strip() for c in ln.strip()[1:-1].split("|")]


def parse(md: str) -> tuple[dict[str, str], set[str]]:
  m = re.search(r"^### 2\.1 .*?$(.*?)(?=^### )", md, re.M | re.S)
  funcs = {}
  for ln in (m.group(1) if m else "").splitlines():
    if ln.startswith("| F-"):
      c = _cells(ln)
      funcs[c[0]] = c[1]
  m = re.search(r"^### 3\.1 .*?$(.*?)(?=^### )", md, re.M | re.S)
  elements = set(re.findall(r"^\| (E-0\d) ", m.group(1) if m else "", re.M))
  m = re.search(r"^### 3\.2 .*?$(.*?)(?=^### )", md, re.M | re.S)
  outside = [_cells(ln)[0] for ln in (m.group(1) if m else "").splitlines() if ln.startswith("| ") and not ln.startswith(("| Element", "|---"))]
  if not funcs or not elements or not outside:
    raise AllocationError("WP-C-01 §2.1, §3.1 or §3.2 table not found")
  if set(funcs) != set(ALLOCATION):
    raise AllocationError(f"ALLOCATION functions {sorted(ALLOCATION)} differ from §2.1 {sorted(funcs)}")
  for e, _ in INSIDE:
    if e not in elements:
      raise AllocationError(f"{e} is not an element of §3.1")
  for k, row in OUTSIDE_ROW.items():
    if not any(o.startswith(row) for o in outside):
      raise AllocationError(f"no §3.2 row starts with {row!r} (column {k})")
  cols = {e for e, _ in INSIDE} | {k for k, _ in OUTSIDE}
  for f, cells in ALLOCATION.items():
    if bad := set(cells) - cols:
      raise AllocationError(f"{f} names unknown columns {sorted(bad)}")
    if not any(v == R for v in cells.values()):
      raise AllocationError(f"{f}: no element realizes it")
  return funcs, elements


MARK = {R: ("#0F766E", "#0F766E"), C: ("#FFFFFF", "#0F766E"), X: ("#FFFFFF", "#64748B")}


def mark(cx, cy, kind):
  fill, stroke = MARK[kind]
  dash = ' stroke-dasharray="3 2"' if kind == X else ""
  return f'<circle cx="{cx:g}" cy="{cy:g}" r="8" fill="{fill}" stroke="{stroke}" stroke-width="2"{dash}/>'


def figure(funcs: dict[str, str], md: str) -> str:
  W = 1280
  NX = 40
  CX0, CW = 330, 78
  GAP = 30
  RH = 40
  body = header(W, "Figure 3-4 · Which elements realize each function",
                "Each function of §2.1 against the elements inside the item (§3.1) that realize or carry it, and the "
                "elements outside it (§3.2) it relies on", "WP-C-01 §2.1, §3.1, §3.2", "")
  y = 112
  ox = CX0 + len(INSIDE) * CW + GAP
  body.append(t(CX0 + len(INSIDE) * CW / 2, y, "Inside the item (§3.1)", 11.5, INK, 700, "middle"))
  body.append(f'<line x1="{CX0 + 6}" y1="{y + 6}" x2="{CX0 + len(INSIDE) * CW - 6}" y2="{y + 6}" stroke="#0F766E" stroke-width="1.5"/>')
  body.append(t(ox + len(OUTSIDE) * CW / 2 * 0.86, y, "Outside the item, relied on (§3.2)", 11.5, INK, 700, "middle"))
  ocw = CW * 0.86
  body.append(f'<line x1="{ox + 6}" y1="{y + 6}" x2="{ox + len(OUTSIDE) * ocw - 6}" y2="{y + 6}" stroke="#64748B" stroke-width="1.5" stroke-dasharray="4 3"/>')
  y += 26
  xs = {}
  for i, (e, cap) in enumerate(INSIDE):
    cx = CX0 + i * CW + CW / 2
    xs[e] = cx
    body.append(t(cx, y, e, 11, INK, 700, "middle"))
    for j, ln in enumerate(wrap(cap, CW - 8, 9.5)):
      body.append(t(cx, y + 14 + 12 * j, ln, 9.5, MUTED, None, "middle"))
  for i, (k, cap) in enumerate(OUTSIDE):
    cx = ox + i * ocw + ocw / 2
    xs[k] = cx
    for j, ln in enumerate(wrap(cap, ocw - 6, 9.5)):
      body.append(t(cx, y + 12 * j, ln, 9.5, INK, 600, "middle"))
  y += 34
  top = y
  bands, rows = [], []
  for i, (f, name) in enumerate(funcs.items()):
    if i % 2 == 0:
      bands.append(f'<rect x="32" y="{y}" width="{W - 64}" height="{RH}" rx="6" fill="#F8FAFC"/>')
    rows.append(t(NX, y + 25, f, 12, INK, 700))
    nm = re.sub(r"\s*\(.*\)$", "", name)
    lines = wrap(nm, CX0 - NX - 70, 11)[:2]
    for j, ln in enumerate(lines):
      rows.append(t(NX + 46, y + (25 if len(lines) == 1 else 18) + 14 * j, ln, 11, INK))
    for col, kind in ALLOCATION[f].items():
      rows.append(mark(xs[col], y + RH / 2, kind))
    y += RH
  guides = [f'<line x1="{x:g}" y1="{top}" x2="{x:g}" y2="{y}" stroke="{HAIR}" stroke-width="1"/>' for x in xs.values()]
  body += bands + guides + rows
  body.append(f'<line x1="{ox - GAP / 2:g}" y1="{top - 60}" x2="{ox - GAP / 2:g}" y2="{y}" stroke="#CBD5E1" stroke-dasharray="4 3"/>')
  y += 26
  lx = 40
  for kind, txt in ((R, "realizes: its code, model or hardware performs the function"),
                    (C, "carries: hosts it or passes it on"),
                    (X, "relies on: outside the item, credited through an assumption of use (§7)")):
    body.append(mark(lx + 8, y - 4, kind))
    body.append(t(lx + 22, y, txt, 11))
    lx += 22 + hf.text_w(txt, 11) + 28
  y += 22
  body.append(t(40, y, "E-06 (external compute) is excluded from the reference configuration and not drawn. The cells "
                "are an analyst reading of §2.1–§3.2, listed in fig_c01_allocation.py; the code paths are in §2.1.",
                11, MUTED))
  extra, y = terms.svg_footer(body, 40, y + 20, W - 80)
  body += extra
  body.append(t(W - 40, y + 6, "Generated by fig_c01_allocation.py", 10, MUTED, None, "end"))
  h = y + 20
  desc = ("Functions of WP-C-01 §2.1 against elements. " + " ".join(
    f"{f}: " + ", ".join(f"{k} {v}" for k, v in ALLOCATION[f].items()) + "." for f in funcs))
  return svg_doc(W, h, "Figure 3-4. Which elements realize each function (WP-C-01 §2.1, §3.1, §3.2)", desc, body)


def build() -> dict[str, str]:
  md = SOURCE.read_text(encoding="utf-8")
  funcs, _ = parse(md)
  return {OUT: figure(funcs, md)}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except AllocationError as e:
    print(f"fig_c01_allocation: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"assurance/02-concept/figures/{n} is stale; run fig_c01_allocation.py", file=sys.stderr)
    if not stale:
      print(f"fig_c01_allocation: {len(outputs)} figure current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote assurance/02-concept/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
