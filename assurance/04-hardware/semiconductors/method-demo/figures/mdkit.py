#!/usr/bin/env python3
"""Shared drawing helpers for the Part 11 method-demonstration figures: results loading, the phone-format frame of the
"Part 11 in one minute" explainers, number tiles, arrows and a squarified tree map. Standard library only; the colours and
primitives come from the shared figkit, the definitions line from terms.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"
ASSURANCE = HERE.parents[3]
sys.path.insert(0, str(ASSURANCE / "01-management" / "figures"))
sys.path.insert(0, str(ASSURANCE / "trace" / "tools"))
from figkit import (FONT, MONO, INK, MUTED, FAINT, LINE, HAIR, CHIP, SAFETY, SAFETY_BG, SW, SW_BG, HW, HW_BG,  # noqa: F401
                    GREEN, GREEN_BG, AMBER, AMBER_BG, RED, RED_BG, GREY_BG, el, fmt, text, rect, line, path, svg, header)
import terms

SUB_PARTS = ["Register file", "Multiplier", "Divider", "ALU + execute", "Control", "IRQ + timer", "Decoder", "Load / store",
             "Fetch + PC", "Counters"]
SUB_COLOUR = {"Register file": "#CA8A04", "Multiplier": "#9333EA", "Divider": "#7C3AED", "ALU + execute": "#EA580C",
              "Control": "#64748B", "IRQ + timer": "#DB2777", "Decoder": "#16A34A", "Load / store": "#0891B2",
              "Fetch + PC": "#0D9488", "Counters": "#94A3B8"}


class FigureError(Exception):
  pass


def load(name: str) -> dict:
  p = RESULTS / name
  if not p.exists():
    raise FigureError(f"missing results file {p.name}")
  return json.loads(p.read_text(encoding="utf-8"))


def need(d: dict, *keys: str) -> None:
  for k in keys:
    if k not in d:
      raise FigureError(f"results field missing: {k}")


def check_sub_parts(names: list[str], where: str) -> None:
  if sorted(names) != sorted(SUB_PARTS) or len(set(names)) != len(names):
    raise FigureError(f"{where}: sub-parts {sorted(names)} do not match the expected ten")


DISPLAY = {"Fetch + PC": "Program counter"}  # "PC" means personal computer in the shared term list


def name(sub_part: str) -> str:
  return DISPLAY.get(sub_part, sub_part)


def pct(x: float, nd: int = 1) -> str:
  return f"{x * 100:.{nd}f} %"


def arrow(x1: float, y1: float, x2: float, y2: float, c: str = MUTED) -> list[str]:
  """A line with a filled arrowhead at (x2, y2)."""
  dx, dy = x2 - x1, y2 - y1
  n = (dx * dx + dy * dy) ** 0.5 or 1
  ux, uy = dx / n, dy / n
  bx, by = x2 - 9 * ux, y2 - 9 * uy
  head = f"M{fmt(x2)},{fmt(y2)} L{fmt(bx - 4.5 * uy)},{fmt(by + 4.5 * ux)} L{fmt(bx + 4.5 * uy)},{fmt(by - 4.5 * ux)} Z"
  return [line(x1, y1, bx, by, stroke=c, sw=1.6), el("path", None, d=head, fill=c)]


def chip(x: float, y: float, s: str, fg: str, bg: str, size: float = 11) -> tuple[list[str], float]:
  w = 6.6 * len(s) * size / 11 + 14
  return [rect(x, y, w, 20, fill=bg, stroke=fg, sw=1, rx=10), text(x + w / 2, y + 14, s, size, fg, "600", "middle")], w


def squarify(items: list[tuple[str, float]], x: float, y: float, w: float, h: float) -> list[tuple[str, float, float, float, float]]:
  """Squarified tree map of (key, value) items, largest first: [(key, x, y, w, h)]."""
  out, items = [], sorted(items, key=lambda kv: (-kv[1], kv[0]))
  while items:
    total = sum(v for _, v in items)
    horiz = w >= h
    side = h if horiz else w
    row, best = [], None
    for k in range(1, len(items) + 1):
      cand = items[:k]
      s = sum(v for _, v in cand)
      thick = s / total * (w if horiz else h)
      worst = max(max((side * v / s) / thick, thick / (side * v / s)) for _, v in cand)
      if best is not None and worst > best:
        break
      best, row = worst, cand
    s = sum(v for _, v in row)
    thick = s / total * (w if horiz else h)
    off = 0.0
    for key, v in row:
      ln = side * v / s
      out.append((key, x, y + off, thick, ln) if horiz else (key, x + off, y, ln, thick))
      off += ln
    items = items[len(row):]
    if horiz:
      x, w = x + thick, w - thick
    else:
      y, h = y + thick, h - thick
  return out


# ---------------------------------------------------------------- phone-format explainers
PW = 720


def frame(n: int, title: list[str], sub: str, steps: list[str], cur: int) -> tuple[list[str], float]:
  b = [rect(24, 22, 236, 30, fill=HW_BG, stroke=HW, sw=1, rx=15),
       text(142, 42, f"PART 11 IN ONE MINUTE · {n}", 12, HW, "700", "middle")]
  y = 92
  for t in title:
    b.append(text(PW / 2, y, t, 30, INK, "800", "middle"))
    y += 38
  b.append(text(PW / 2, y + 2, sub, 15, MUTED, "", "middle"))
  y += 30
  x = 24
  cw = (PW - 48 - 6 * (len(steps) - 1)) / len(steps)
  for k, s in enumerate(steps):
    on = k == cur
    b.append(rect(x, y, cw, 26, fill=SAFETY if on else GREY_BG, stroke=SAFETY if on else LINE, sw=1, rx=13))
    b.append(text(x + cw / 2, y + 17, s, 11, "#FFFFFF" if on else MUTED, "700" if on else "", "middle"))
    x += cw + 6
  return b, y + 44


def tiles(b: list[str], y: float, items: list[tuple[str, str, str, str, str]]) -> float:
  w = (PW - 48 - 24) / 3
  for k, (lab, big, unit, sub, c) in enumerate(items):
    x = 24 + k * (w + 12)
    b.append(text(x + w / 2, y + 16, lab, 12, MUTED, "", "middle"))
    b.append(text(x + w / 2, y + 60, big, 40, c, "800", "middle"))
    b.append(text(x + w / 2, y + 84, unit, 13, INK, "600", "middle"))
    b.append(text(x + w / 2, y + 102, sub, 11, MUTED, "", "middle"))
  return y + 120


def finish(b: list[str], y: float, closing: str, notes: list[str], title: str, desc: str) -> str:
  """Closing line, source notes and the terms line under the content; the page height follows the content."""
  y += 34
  b.append(text(PW / 2, y, closing, 16, INK, "700", "middle"))
  y += 26
  for t in notes:
    b.append(text(PW / 2, y, t, 11, FAINT, "", "middle"))
    y += 17
  extra, y = terms.svg_footer(b, 24, y + 12, PW - 48)
  return svg(PW, int(y + 16), title, desc, b + extra)
