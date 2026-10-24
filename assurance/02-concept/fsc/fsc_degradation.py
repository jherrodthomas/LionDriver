#!/usr/bin/env python3
"""Draw WP-C-04 Figure 12-1, the degradation ladder (`figures/fig-c04-12-1-degradation-ladder.svg`).

One row per degradation level of WP-C-04 §12.1 (L0 full function … L5 lockout) with what happens to lateral and
longitudinal control, what the driver is told and what triggers the level. The safe states SS-L, SS-G and SS-S that
the cells name are drawn as pills and defined below the ladder from the §6 table (definition, entered by, exit).

WP-C-04 is the source of record. Run through `fsc_figures.py`, which writes and checks every fig-c04-<n> figure.
It fails if §12.1 does not list L0…L5 in order, if a cell names a safe state that §6 does not define, or if §6
defines a safe state that no level uses.

Standard library only. Drawing helpers and palette are shared with ../hara/hara_figures.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "hara"))
import hara_figures as hf  # noqa: E402
from hara_figures import INK, MUTED, HAIR, t, wrap, svg_doc, header  # noqa: E402

NAME = "fig-c04-12-1-degradation-ladder.svg"
SS_RE = re.compile(r"SS-[LGS]")
# Level colour, from full function (teal) to envelope silent (deep red); lockout is grey, the function is withheld.
LEVEL_COLOUR = {
  "L0": ("#0F766E", "#F0FDFA"), "L1": ("#1D4ED8", "#EFF6FF"), "L2": ("#D97706", "#FFFBEB"),
  "L3": ("#D2553F", "#FEF2F2"), "L4": ("#991B1B", "#FEE2E2"), "L5": ("#475569", "#F1F5F9"),
}
SS_COLOUR = ("#9A3412", "#FFF7ED")


class LadderError(ValueError):
  pass


def _cells(line: str) -> list[str]:
  return [c.strip().replace("`", "") for c in line.strip()[1:-1].split("|")]


def parse(md: str) -> tuple[list[list[str]], dict[str, list[str]]]:
  m = re.search(r"^### 12\.1 .*?$(.*?)(?=^### |^## )", md, re.M | re.S)
  if not m:
    raise LadderError("WP-C-04 §12.1 not found")
  levels = [_cells(ln) for ln in m.group(1).splitlines() if re.match(r"^\| L\d \|", ln)]
  if [r[0] for r in levels] != list(LEVEL_COLOUR):
    raise LadderError(f"§12.1 lists {[r[0] for r in levels]}, expected {list(LEVEL_COLOUR)}")
  for r in levels:
    if len(r) != 6:
      raise LadderError(f"§12.1 row {r[0]} has {len(r)} cells, expected 6")
  m = re.search(r"^## 6\. .*?$(.*?)(?=^## \d+\. )", md, re.M | re.S)
  if not m:
    raise LadderError("WP-C-04 §6 not found")
  states = {}
  for ln in m.group(1).splitlines():
    if ln.startswith("| SS-"):
      c = _cells(ln)
      states[c[0].split()[0]] = c
  used = {s for r in levels for cell in r[2:4] for s in SS_RE.findall(cell)}
  if used - set(states):
    raise LadderError(f"§12.1 names safe states §6 does not define: {sorted(used - set(states))}")
  if set(states) - used:
    raise LadderError(f"§6 defines safe states no level uses: {sorted(set(states) - used)}")
  return levels, states


def _cell(body: list[str], x: float, y: float, s: str, width: float, size: float = 11) -> float:
  """Write a cell; a leading safe-state code becomes a pill. Returns the height used."""
  h = 0.0
  ss = SS_RE.findall(s)
  if ss and re.fullmatch(r"(SS-[LGS])( \+ .*)?", s):
    pw = hf.text_w(ss[0], 10, True) + 14
    body.append(f'<rect x="{x:g}" y="{y - 12:g}" width="{pw:.1f}" height="18" rx="9" fill="{SS_COLOUR[1]}" '
                f'stroke="{SS_COLOUR[0]}" stroke-width="1.3"/>')
    body.append(t(x + pw / 2, y + 1, ss[0], 10, SS_COLOUR[0], 700, "middle"))
    rest = s[len(ss[0]):].strip()
    if rest:
      for i, ln in enumerate(wrap(rest, width - pw - 6, size)):
        body.append(t(x + pw + 6, y + i * 14, ln, size, INK))
        h = (i + 1) * 14
    return max(h, 18)
  for i, ln in enumerate(wrap(s, width, size)):
    body.append(t(x, y + i * 14, ln, size, INK))
    h = (i + 1) * 14
  return h


def figure(md: str) -> str:
  levels, states = parse(md)
  w = 1280
  LX, LW = 92, 210                                   # level badge and name
  cols = [("LATERAL", 312, 190), ("LONGITUDINAL", 512, 170), ("DRIVER INFORMATION", 692, 250), ("TRIGGER EXAMPLES", 952, 288)]
  body = header(w, "Figure 12-1 · Degradation ladder: from full function to lockout",
                "What the item does at each level of §12.1: lateral and longitudinal control, what the driver is told, "
                "and what puts it there", "WP-C-04 §12.1, §6", "fail-silent: no emergency operation (§6)")
  y = 112
  for name, x, _ in cols:
    body.append(t(x, y, name, 10.5, MUTED, 700, extra=' letter-spacing=".04em"'))
  body.append(t(LX, y, "LEVEL", 10.5, MUTED, 700, extra=' letter-spacing=".04em"'))
  y += 14
  top = y
  for lv in levels:
    code, name, *rest = lv
    line_c, bg = LEVEL_COLOUR[code]
    heights = []
    tmp: list[str] = []
    for (_, x, cw), s in zip(cols, rest, strict=True):
      heights.append(_cell(tmp, x, y + 26, s, cw - 14))
    name_lines = wrap(name, LW - 64, 13, True)
    h = max(max(heights), 14 * len(name_lines)) + 30
    body.append(f'<rect x="{LX - 8}" y="{y}" width="{w - 40 - LX + 8}" height="{h:g}" rx="9" fill="{bg}" stroke="{line_c}" stroke-width="1.2"/>')
    body.append(f'<rect x="{LX - 8}" y="{y}" width="6" height="{h:g}" rx="3" fill="{line_c}"/>')
    body.append(f'<rect x="{LX + 6}" y="{y + 12}" width="40" height="22" rx="11" fill="{line_c}"/>')
    body.append(t(LX + 26, y + 27.5, code, 12, "#FFFFFF", 700, "middle"))
    for i, ln in enumerate(name_lines):
      body.append(t(LX + 56, y + 28 + i * 15, ln, 13, INK, 700))
    body += tmp
    y += h + 10
  # severity arrow beside the ladder
  body.append('<defs><marker id="dl-arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="7" markerHeight="7" '
              f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/></marker></defs>')
  body.append(f'<line x1="56" y1="{top + 8}" x2="56" y2="{y - 22}" stroke="{MUTED}" stroke-width="1.6" marker-end="url(#dl-arrow)"/>')
  mid = (top + y) / 2
  body.append(t(48, mid, "more function withdrawn", 11, MUTED, 700, "middle", f' transform="rotate(-90 48 {mid:g})"'))
  y += 14
  body.append(f'<line x1="40" y1="{y}" x2="{w - 40}" y2="{y}" stroke="{HAIR}"/>')
  y += 26
  body.append(t(40, y, "SAFE STATES (§6)", 10.5, MUTED, 700, extra=' letter-spacing=".04em"'))
  y += 14
  sw = (w - 80 - 2 * 16) / 3
  card_h = 0.0
  cards: list[tuple[float, list[str]]] = []
  for i, (code, c) in enumerate(states.items()):
    x = 40 + i * (sw + 16)
    tmp = []
    yy = y + 24
    label = c[0][len(code):].strip(" ()")
    tmp.append(f'<rect x="{x + 14:g}" y="{yy - 13:g}" width="{hf.text_w(code, 10, True) + 14:.1f}" height="18" rx="9" '
               f'fill="{SS_COLOUR[1]}" stroke="{SS_COLOUR[0]}" stroke-width="1.3"/>')
    tmp.append(t(x + 21 + hf.text_w(code, 10, True) / 2, yy, code, 10, SS_COLOUR[0], 700, "middle"))
    tmp.append(t(x + 14 + hf.text_w(code, 10, True) + 14 + 8, yy, label, 12, INK, 700))
    yy += 22
    for head, val in (("What it is", c[1]), ("Entered by", c[2]), ("Left by", c[3])):
      tmp.append(t(x + 14, yy, head.upper(), 9.5, MUTED, 700, extra=' letter-spacing=".04em"'))
      yy += 14
      for ln in wrap(val, sw - 28, 10.5):
        tmp.append(t(x + 14, yy, ln, 10.5, INK))
        yy += 13.5
      yy += 6
    card_h = max(card_h, yy - y)
    cards.append((x, tmp))
  for x, tmp in cards:
    body.append(f'<rect x="{x:g}" y="{y}" width="{sw:g}" height="{card_h:g}" rx="9" fill="#FFFFFF" stroke="#CBD5E1"/>')
    body += tmp
  y += card_h + 26
  body.append(t(40, y, "Every fault-induced move to L2, L3 or L4 gives an acoustic and visual take-over request (§12.2). "
                "There is no lateral-only or longitudinal-only mode.", 11, MUTED))
  body.append(t(w - 40, y, "Generated by fsc_degradation.py", 10, MUTED, None, "end"))
  h = int(y + 22)
  desc = ("Six degradation levels of WP-C-04 §12.1, one row each: "
          + "; ".join(f"{r[0]} {r[1]}: lateral {r[2]}, longitudinal {r[3]}" for r in levels)
          + ". Safe states from §6: " + "; ".join(f"{k}: {v[1]}" for k, v in states.items()) + ".")
  return svg_doc(w, h, "Figure 12-1. Degradation ladder (WP-C-04 §12.1, §6)", desc, body)


def build(md: str) -> dict[str, str]:
  return {NAME: figure(md)}
