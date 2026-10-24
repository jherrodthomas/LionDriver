#!/usr/bin/env python3
"""Draw two overview figures of the HARA from the model (generated, not hand-drawn).

WP-C-03 Figure 3-1 (`figures/fig-c03-3-1-situations.svg`): the operational situations of §3 (`SITUATIONS`) on a
speed axis, one bar per situation over its speed range, coloured by exposure, with the situations that are foreseeable
misuse (outside the ODD or the intended driver state) drawn hatched, and the weather and surface conditions of §3.1.

WP-C-03 Figure 4-9 (`figures/fig-c03-4-9-function-hazard-view.svg`): the functions of WP-C-01 §2.1 in the hazard
view. One row per function (`FUNCTIONS`) with its 14 guide words, each cell its classification (`FM`): an expanded
safety-critical pair coloured by the highest ASIL of its rows, a subsumed one marked with the pair that covers it, NSC
and NA in grey. On the right, the hazards the function reaches, the goals they lead to (`SG_MAP`) and its highest ASIL.

Both are written and checked by `hara_figures.py`; reference scope (Chill mode) only. Standard library only.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hara_model as hm  # noqa: E402
import hara_figures as hf  # noqa: E402
from hara_figures import INK, MUTED, HAIR, ASIL_FILL, ASIL_TEXT, ASIL_STROKE, t, wrap, header, svg_doc  # noqa: E402

SIT_NAME = "fig-c03-3-1-situations.svg"
FUN_NAME = "fig-c03-4-9-function-hazard-view.svg"
RANK = {"—": -1, "QM": 0, "A": 1, "B": 2, "C": 3, "D": 4}
E_COL = {"E4": ("#1E3A8A", "#FFFFFF"), "E3": ("#3B82F6", "#FFFFFF"), "E2": ("#93C5FD", INK), "E1": ("#DBEAFE", INK),
         "E0": ("#F8FAFC", INK)}


def _hatch(pid: str) -> str:
  return (f'<pattern id="{pid}" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
          '<rect width="6" height="6" fill="#FFFFFF" fill-opacity="0"/><line x1="0" y1="0" x2="0" y2="6" '
          'stroke="#FFFFFF" stroke-width="2.2" stroke-opacity=".75"/></pattern>')


def misuse(name: str) -> bool:
  return "foreseeable misuse" in name


# ---------------------------------------------------------------- Figure 3-1: operational situations

def situations_figure() -> str:
  W = 1280
  LX, LW = 40, 470             # id and situation text
  AX0, AX1 = 560, 1000         # speed axis 0 … 120 km/h
  EX = 1020                    # exposure text
  RH = 30
  vmax = 120

  def sx(v: float) -> float:
    return AX0 + (AX1 - AX0) * v / vmax

  body = header(W, "Figure 3-1 · Operational situations: speed range and exposure",
                f"The {len(hm.SITUATIONS)} situations of §3 crossed with every safety-critical malfunction, and the "
                f"{len(hm.WEATHER)} weather and surface conditions of §3.1", "WP-C-03 §3, §3.1", "SITUATIONS in hara_model.py")
  body.insert(0, f"<defs>{_hatch('os-h')}</defs>")
  y = 112
  body.append(t(LX, y, "SITUATION", 10.5, MUTED, 700, extra=' letter-spacing=".04em"'))
  body.append(t(AX0, y, "SPEED RANGE (km/h) · colour = exposure", 10.5, MUTED, 700, extra=' letter-spacing=".04em"'))
  body.append(t(EX, y, "EXPOSURE", 10.5, MUTED, 700, extra=' letter-spacing=".04em"'))
  y += 12
  top = y
  # ODD speed band: highway ODD up to the 110 km/h bound
  body.append(f'<rect x="{sx(0):g}" y="{top}" width="{sx(110) - sx(0):g}" height="{RH * len(hm.SITUATIONS)}" fill="#F0FDFA"/>')
  for v in range(0, vmax + 1, 20):
    body.append(f'<line x1="{sx(v):g}" y1="{top}" x2="{sx(v):g}" y2="{top + RH * len(hm.SITUATIONS)}" stroke="{HAIR}"/>')
  body.append(f'<line x1="{sx(110):g}" y1="{top - 4}" x2="{sx(110):g}" y2="{top + RH * len(hm.SITUATIONS)}" '
              'stroke="#0F766E" stroke-width="1.6" stroke-dasharray="5 4"/>')
  for code, name, vmin, vmx, e, _ in hm.SITUATIONS:
    short = re.split(r":", name)[0].strip()
    lines = wrap(short, LW - 60, 11)
    body.append(t(LX, y + 19, code, 11.5, INK, 700))
    body.append(t(LX + 52, y + 19 - (6 if len(lines) > 1 else 0), lines[0], 11, INK))
    if len(lines) > 1:
      body.append(t(LX + 52, y + 19 + 7, hf.wrap(" ".join(lines[1:]), LW - 60, 11)[0] + ("…" if len(lines) > 2 else ""), 11, INK))
    fill, tc = E_COL[e]
    x0, x1 = sx(vmin), sx(max(vmx, vmin + 3))
    body.append(f'<rect x="{x0:g}" y="{y + 7}" width="{x1 - x0:g}" height="{RH - 14}" rx="4" fill="{fill}"/>')
    if misuse(name):
      body.append(f'<rect x="{x0:g}" y="{y + 7}" width="{x1 - x0:g}" height="{RH - 14}" rx="4" fill="url(#os-h)"/>')
    body.append(t(EX, y + 19, e, 11, INK, 700))
    tag = "foreseeable misuse" if misuse(name) else ("not engaged" if code == "OS-13" else "in the ODD")
    body.append(t(EX + 28, y + 19, tag, 10.5, "#B45309" if misuse(name) else MUTED))
    y += RH
  for v in range(0, vmax + 1, 20):
    body.append(t(sx(v), y + 16, str(v), 10, MUTED, None, "middle"))
  body.append(t(sx(110), top - 8, "ODD bound 110 km/h", 10, "#0F766E", 700, "middle"))
  y += 40
  body.append(f'<line x1="40" y1="{y}" x2="{W - 40}" y2="{y}" stroke="{HAIR}"/>')
  y += 26
  body.append(t(40, y, "WEATHER AND SURFACE (§3.1), crossed with every situation; a combination is rated no more frequent "
                "than the rarer of the two", 10.5, MUTED, 700, extra=' letter-spacing=".02em"'))
  y += 14
  cw = (W - 80 - 5 * 10) / 6
  for i, (code, name, e, *rest) in enumerate(hm.WEATHER):
    x = 40 + i * (cw + 10)
    fill, tc = E_COL[e]
    out = "outside ODD" in name
    body.append(f'<rect x="{x:g}" y="{y}" width="{cw:g}" height="62" rx="8" fill="#FFFFFF" stroke="#CBD5E1"/>')
    body.append(f'<rect x="{x + 10:g}" y="{y + 10}" width="30" height="18" rx="4" fill="{fill}"/>')
    if out:
      body.append(f'<rect x="{x + 10:g}" y="{y + 10}" width="30" height="18" rx="4" fill="url(#os-h)"/>')
    body.append(t(x + 25, y + 23, e, 10, tc, 700, "middle"))
    body.append(t(x + 48, y + 23, code, 11, INK, 700))
    nm = name.replace(" (outside ODD, foreseeable)", "")
    for j, ln in enumerate(wrap(nm, cw - 20, 10.5)[:2]):
      body.append(t(x + 10, y + 44 + j * 13, ln, 10.5, INK))
  y += 62 + 26
  lx = 40
  for e in ("E4", "E3", "E2", "E1"):
    body.append(f'<rect x="{lx}" y="{y - 11}" width="28" height="14" rx="3" fill="{E_COL[e][0]}"/>')
    lab = {"E4": "E4 > 10 % of time", "E3": "E3 1–10 %", "E2": "E2 < 1 %", "E1": "E1 very rare"}[e]
    body.append(t(lx + 34, y, lab, 11))
    lx += 34 + hf.text_w(lab, 11) + 20
  body.append(f'<rect x="{lx}" y="{y - 11}" width="28" height="14" rx="3" fill="{E_COL["E3"][0]}"/>')
  body.append(f'<rect x="{lx}" y="{y - 11}" width="28" height="14" rx="3" fill="url(#os-h)"/>')
  body.append(t(lx + 34, y, "hatched: foreseeable misuse (outside the ODD or driver state), rated all the same", 11))
  y += 20
  body.append(t(40, y, "Exposure by duration (ISO 26262-3 Table B.2), except OS-07, rated by frequency (Table B.3, DQ-036). "
                "Driver monitoring is not credited in OS-17 and OS-18.", 11, MUTED))
  body.append(t(W - 40, y + 20, "Generated by hara_views.py", 10, MUTED, None, "end"))
  h = y + 34
  desc = ("Operational situations of WP-C-03 §3: " + "; ".join(
    f"{c} {re.split(':', n)[0]} {a}–{b} km/h {e}" + (" (foreseeable misuse)" if misuse(n) else "")
    for c, n, a, b, e, _ in hm.SITUATIONS) + ". Weather: " + "; ".join(f"{w[0]} {w[1]} {w[2]}" for w in hm.WEATHER) + ".")
  return svg_doc(W, h, "Figure 3-1. Operational situations (WP-C-03 §3)", desc, body)


# ---------------------------------------------------------------- Figure 4-9: the functions in the hazard view

def function_model() -> dict[str, dict]:
  _, rows = hm.build(False)
  worst = defaultdict(lambda: "—")
  for r in rows:
    k = (r["f"], r["m"])
    if RANK[r["asil"]] > RANK[worst[k]]:
      worst[k] = r["asil"]
  out = {}
  for f_id, name, auth, _ in hm.FUNCTIONS:
    cells, hazards = [], []
    for m_id, _ in hm.MALFUNCTIONS:
      cls, h, sub, _ = hm.FM[f_id][m_id]
      cells.append((m_id, cls, sub, worst.get((f_id, m_id), "—") if cls == hm.SC and not sub else None))
      if cls == hm.SC and h and h not in hazards:
        hazards.append(h)
    top = max((c[3] for c in cells if c[3]), key=lambda a: RANK[a], default="—")
    goals = []
    for h in sorted(hazards):
      for g in re.findall(r"SG-\d\d", hm.SG_MAP[h]):
        if g not in goals:
          goals.append(g)
    out[f_id] = {"name": name, "auth": auth, "cells": cells, "hazards": sorted(hazards), "goals": sorted(goals),
                 "top": top, "n_sc": sum(1 for c in cells if c[1] == hm.SC)}
  return out


def function_figure() -> str:
  model = function_model()
  W = 1280
  NX, NW = 40, 270
  CX, CW = 322, 42
  RX = CX + 14 * CW + 18
  RH = 58
  body = header(W, "Figure 4-9 · The item's functions in the hazard view",
                "The functions of WP-C-01 §2.1, each with its 14 guide words classified (§2 step 2), the hazards its "
                "safety-critical pairs reach (§4) and the goals they lead to (§6)", "WP-C-03 §2, §4, §6",
                "FM, FUNCTIONS in hara_model.py")
  y = 112
  body.append(t(NX, y, "FUNCTION (WP-C-01 §2.1)", 10.5, MUTED, 700, extra=' letter-spacing=".04em"'))
  for i, (m_id, m_name) in enumerate(hm.MALFUNCTIONS):
    cx = CX + i * CW + CW / 2
    body.append(t(cx, y, m_id, 10, INK, 700, "middle"))
  body.append(t(RX, y, "HAZARDS (§4) · GOALS (§6) · HIGHEST", 10.5, MUTED, 700, extra=' letter-spacing=".04em"'))
  y += 10
  for i, (f_id, v) in enumerate(model.items()):
    if i % 2 == 0:
      body.append(f'<rect x="32" y="{y}" width="{W - 64}" height="{RH}" rx="6" fill="#F8FAFC"/>')
    body.append(t(NX, y + 22, f_id, 12.5, INK, 700))
    for j, ln in enumerate(wrap(v["name"], NW - 50, 11)[:2]):
      body.append(t(NX + 46, y + 22 + j * 14, ln, 11, INK))
    body.append(t(NX + 46, y + 50, f"{v['n_sc']}/14 safety-critical · authority {v['auth']}", 9.5, MUTED))
    for k, (m_id, cls, sub, a) in enumerate(v["cells"]):
      x = CX + k * CW + 3
      cy = y + 12
      w, hh = CW - 6, RH - 24
      if cls == hm.SC and not sub:
        key = a if a in ASIL_FILL else "QM"
        body.append(f'<rect x="{x}" y="{cy}" width="{w}" height="{hh}" rx="5" fill="{ASIL_FILL[key]}" stroke="{ASIL_STROKE[key]}"/>')
        body.append(t(x + w / 2, cy + hh / 2 + 4, a if a != "—" else "S0", 10.5, ASIL_TEXT[key], 700, "middle"))
      elif cls == hm.SC:
        body.append(f'<rect x="{x}" y="{cy}" width="{w}" height="{hh}" rx="5" fill="#FFFFFF" stroke="#94A3B8" stroke-dasharray="3 2"/>')
        body.append(t(x + w / 2, cy + hh / 2 + 4, "→" + sub[-2:], 9.5, MUTED, 700, "middle"))
      elif cls == hm.NSC:
        body.append(f'<rect x="{x}" y="{cy}" width="{w}" height="{hh}" rx="5" fill="#E2E8F0"/>')
      else:
        body.append(f'<rect x="{x}" y="{cy}" width="{w}" height="{hh}" rx="5" fill="#FFFFFF" stroke="#E2E8F0"/>')
    rx = RX
    for h in v["hazards"]:
      body.append(f'<rect x="{rx}" y="{y + 9}" width="40" height="16" rx="4" fill="#FFFFFF" stroke="#64748B"/>')
      body.append(t(rx + 20, y + 21, h, 9.5, INK, 700, "middle"))
      rx += 43
    if not v["hazards"]:
      body.append(t(RX, y + 21, "no safety-critical pair", 10, "#94A3B8", None, extra=' font-style="italic"'))
    rx = RX
    for g in v["goals"]:
      body.append(f'<rect x="{rx}" y="{y + 31}" width="44" height="16" rx="8" fill="#FFF7ED" stroke="#C2410C"/>')
      body.append(t(rx + 22, y + 43, g, 9.5, "#9A3412", 700, "middle"))
      rx += 47
    if v["top"] in ASIL_FILL:
      key = v["top"]
      body.append(f'<rect x="{W - 40 - 34}" y="{y + 17}" width="34" height="22" rx="11" fill="{ASIL_FILL[key]}" stroke="{ASIL_STROKE[key]}"/>')
      body.append(t(W - 40 - 17, y + 32, key, 11, ASIL_TEXT[key], 700, "middle"))
    y += RH
  y += 18
  lx = 40
  for key in ("C", "B", "A", "QM"):
    body.append(f'<rect x="{lx}" y="{y - 12}" width="26" height="16" rx="4" fill="{ASIL_FILL[key]}" stroke="{ASIL_STROKE[key]}"/>')
    body.append(t(lx + 13, y, key, 9.5, ASIL_TEXT[key], 700, "middle"))
    lx += 32
  body.append(t(lx, y, "safety-critical, expanded: highest ASIL of its rows", 11))
  lx += hf.text_w("safety-critical, expanded: highest ASIL of its rows", 11) + 22
  body.append(f'<rect x="{lx}" y="{y - 12}" width="26" height="16" rx="4" fill="#FFFFFF" stroke="#94A3B8" stroke-dasharray="3 2"/>')
  body.append(t(lx + 34, y, "subsumed by the pair named", 11))
  lx += 34 + hf.text_w("subsumed by the pair named", 11) + 22
  body.append(f'<rect x="{lx}" y="{y - 12}" width="26" height="16" rx="4" fill="#E2E8F0"/>')
  body.append(t(lx + 34, y, "NSC", 11))
  lx += 34 + hf.text_w("NSC", 11) + 22
  body.append(f'<rect x="{lx}" y="{y - 12}" width="26" height="16" rx="4" fill="#FFFFFF" stroke="#E2E8F0"/>')
  body.append(t(lx + 34, y, "NA", 11))
  y += 22
  names = [f"{m} {n.lower()}" for m, n in hm.MALFUNCTIONS]
  for ln in wrap("Guide words: " + " · ".join(names), W - 80, 10.5):
    body.append(t(40, y, ln, 10.5, INK))
    y += 15
  y += 4
  body.append(t(40, y, "Every pair keeps its written reason in the workbook (tab 11) and hara-function-guideword.csv. Reference "
                "scope: Experimental Mode (F-02X) is in the variant workbook (§5.11). Ratings as proposed, before I3 confirmation.", 11, MUTED))
  body.append(t(W - 40, y + 20, "Generated by hara_views.py", 10, MUTED, None, "end"))
  h = y + 34
  desc = ("The functions of WP-C-01 §2.1 with their guide-word classification. " + " ".join(
    f"{f}: {v['n_sc']} safety-critical pairs, hazards {', '.join(v['hazards']) or 'none'}, goals "
    f"{', '.join(v['goals']) or 'none'}, highest {v['top']}." for f, v in model.items()))
  return svg_doc(W, h, "Figure 4-9. The item's functions in the hazard view (WP-C-03 §2, §4, §6)", desc, body)


def build() -> dict[str, str]:
  return {SIT_NAME: situations_figure(), FUN_NAME: function_figure()}
