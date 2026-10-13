#!/usr/bin/env python3
"""Draw WP-A-03 Figure 5-1: dependent failure initiators (DFI-xx) against the independence claims (IC-xx).

The source of record is `../WP-A-03-dependent-failure-analysis.md`. This script parses
  * the §4.x DFI tables (ID, initiator, "Elements reached" with its IC-xx tags, "Eval"), and
  * the §5 table (per claim: not controlled DFIs, partly controlled DFIs, verdict),
and draws one row per DFI and one column per claim. Nothing here is analysis content:
change WP-A-03 and regenerate.

Cell rule: a cell is filled when §5 lists the DFI under that claim (red = not controlled,
amber = partly controlled). A DFI whose §4 "Elements reached" names a claim that §5 does not
list is drawn as a dashed outline with a dagger, so the gap between the two tables stays visible.
A §4 rating that changes in the reference build ("**N** at `8b8c6ae`; **P** in the reference build")
is drawn as a split cell.

    python3 fig_a03_dfi_matrix.py            # regenerate the SVG
    python3 fig_a03_dfi_matrix.py --check    # fail if the committed SVG is stale

Standard library only. Output is deterministic.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "WP-A-03-dependent-failure-analysis.md"
OUTPUT = "fig-a03-5-1-dfi-claim-matrix.svg"
FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"

INK, MUTED, HAIR = "#0F172A", "#475569", "#E2E8F0"
RED, AMBER, GREEN, GREY = "#D2553F", "#D97706", "#2E9E6A", "#94A3B8"
RATING_COLOUR = {"N": RED, "P": AMBER, "C": GREEN}


class ParseError(Exception):
  pass


@dataclass
class Dfi:
  ident: str
  name: str
  section: str
  reached: str
  ic_tags: list[str]
  base: str               # N / P / C
  ref: str | None = None  # rating in the reference build, if the row says so


@dataclass
class Claim:
  ident: str
  label: str
  not_controlled: list[str] = field(default_factory=list)
  partly: list[str] = field(default_factory=list)
  verdict: str = ""
  note: str = ""
  unchanged: bool = False


def cells(line: str) -> list[str]:
  return [c.strip() for c in line.strip().strip("|").split("|")]


def short_name(initiator: str) -> str:
  m = re.match(r"\*\*(.+?)\*\*", initiator)
  if not m:
    raise ParseError(f"initiator without bold name: {initiator[:40]}")
  return m.group(1).replace("`", "").rstrip(".").strip()


def parse_eval(text: str) -> tuple[str, str | None]:
  ratings = re.findall(r"\*\*([NPC])\*\*", text)
  if not ratings:
    if text.strip().startswith("n/a"):
      return "n/a", None
    raise ParseError(f"no rating in Eval cell: {text}")
  ref = None
  m = re.search(r"\*\*([NPC])\*\* in the reference build", text)
  if m and m.group(1) != ratings[0]:
    ref = m.group(1)
  return ratings[0], ref


def dfi_list(text: str) -> list[str]:
  text = re.sub(r"\([^)]*\)", "", text).split(" plus ")[0]
  if text.strip() in ("—", "n/a", ""):
    return []
  out = []
  for m in re.finditer(r"(?:DFI)?-(\d{2})\b", text):
    out.append(f"DFI-{m.group(1)}")
  return out


def parse(md: str) -> tuple[list[Dfi], list[Claim], dict[str, str]]:
  dfis: list[Dfi] = []
  claims: list[Claim] = []
  sections: dict[str, str] = {}
  section = ""
  in_s5 = False
  claim_elements: dict[str, str] = {}
  for line in md.splitlines():
    h = re.match(r"^### (4\.\d) (.+)$", line)
    if h:
      section = h.group(1)
      sections[section] = h.group(2).strip()
      continue
    if line.startswith("## "):
      in_s5 = line.startswith("## 5.")
      if not line.startswith("## 4."):
        section = ""
      continue
    if line.startswith("| IC-") and not in_s5:
      c = cells(line)
      claim_elements[c[0]] = c[3]
      continue
    if section and line.startswith("| DFI-"):
      c = cells(line)
      if len(c) != 8:
        raise ParseError(f"{c[0]}: expected 8 columns, got {len(c)}")
      base, ref = parse_eval(c[6])
      tags = sorted(set(re.findall(r"IC-\d{2}", c[3])))
      dfis.append(Dfi(c[0], short_name(c[1]), section, c[3], tags, base, ref))
      continue
    if in_s5 and line.startswith("| IC-"):
      c = cells(line)
      m = re.match(r"(IC-\d{2})\s*(.*)", c[0])
      cl = Claim(m.group(1), m.group(2).strip())
      cl.not_controlled = dfi_list(c[1])
      cl.partly = dfi_list(c[2])
      v = re.match(r"\*\*(.+?)\*\*", c[3])
      cl.verdict = v.group(1) if v else c[3].split(";")[0].strip()
      plus = re.sub(r"\([^)]*\)", "", c[2]).split(" plus ")
      cl.note = plus[1].strip() if len(plus) > 1 else ""
      cl.unchanged = "(unchanged 2026-10-12" in c[3]
      claims.append(cl)
  if not dfis or not claims:
    raise ParseError("no DFI rows or no §5 claims found")
  ids = {d.ident for d in dfis}
  for cl in claims:
    for d in cl.not_controlled + cl.partly:
      if d not in ids:
        raise ParseError(f"§5 {cl.ident} lists unknown {d}")
  return dfis, claims, sections


def findings(dfis: list[Dfi], claims: list[Claim]) -> list[str]:
  """Differences between §4 and §5 (reported, never fixed here)."""
  out = []
  listed = {cl.ident: set(cl.not_controlled) | set(cl.partly) for cl in claims}
  for d in dfis:
    for ic in d.ic_tags:
      if ic in listed and d.ident not in listed[ic]:
        out.append(f"{d.ident}: §4 names {ic}, §5 does not list it under {ic}")
    if not any(d.ident in s for s in listed.values()):
      out.append(f"{d.ident}: not listed under any claim in §5")
  for cl in claims:
    for did in cl.not_controlled + cl.partly:
      d = next(x for x in dfis if x.ident == did)
      col = "N" if did in cl.not_controlled else "P"
      if col != d.base and col != d.ref:
        out.append(f"{did}: §4 Eval {d.base}, §5 {cl.ident} lists it as {col}")
  return out


# ---------------------------------------------------------------- drawing
def t(x, y, s, size=11, fill=INK, weight=None, anchor=None, italic=False):
  a = f' font-size="{size}" fill="{fill}"'
  if weight:
    a += f' font-weight="{weight}"'
  if anchor:
    a += f' text-anchor="{anchor}"'
  if italic:
    a += ' font-style="italic"'
  return f'<text x="{x:g}" y="{y:g}"{a}>{escape(s)}</text>'


def rect(x, y, w, h, fill, stroke="none", sw=1.0, rx=0, dash=None):
  a = f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="{fill}"'
  if stroke != "none":
    a += f' stroke="{stroke}" stroke-width="{sw:g}"'
  if rx:
    a += f' rx="{rx:g}"'
  if dash:
    a += f' stroke-dasharray="{dash}"'
  return a + "/>"


def wrap(s: str, n: int) -> list[str]:
  lines, cur = [], ""
  for w in s.split():
    if cur and len(cur) + 1 + len(w) > n:
      lines.append(cur)
      cur = w
    else:
      cur = f"{cur} {w}".strip()
  return lines + ([cur] if cur else [])


W = 1280
LX, EX, CX0, CW = 40, 452, 552, 96
RH = 22


def verdict_colour(v: str) -> tuple[str, str]:
  lv = v.lower()
  if lv.startswith("not independent"):
    return RED, "#FFFFFF"
  if lv.startswith("partly"):
    return AMBER, "#FFFFFF"
  if lv.startswith("open"):
    return "#F1F5F9", INK
  return "#F8FAFC", MUTED


def draw(dfis: list[Dfi], claims: list[Claim], sections: dict[str, str]) -> str:
  listed_n = {cl.ident: set(cl.not_controlled) for cl in claims}
  listed_p = {cl.ident: set(cl.partly) for cl in claims}
  out: list[str] = []
  head_y = 96
  grid_top = head_y + 58
  order = sorted(sections)
  nrows = len(dfis) + len(order)
  grid_bottom = grid_top + nrows * RH
  verdict_y = grid_bottom + 10
  legend_y = verdict_y + 62
  notes = [cl for cl in claims if cl.note]
  H = legend_y + 70 + 16 * len(notes)
  out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}" role="img" aria-labelledby="t d">')
  out.append('<title id="t">Figure 5-1. Dependent failure initiators against the independence claims they reach, with evaluation (WP-A-03 §4, §5)</title>')
  n_n = sum(1 for d in dfis if d.base == "N")
  out.append(f'<desc id="d">Matrix of the {len(dfis)} dependent failure initiators DFI-01 to DFI-26 of §4 (rows, grouped by §4.1 to §4.6) against the independence claims IC-01 to IC-07 (columns). A red cell means §5 lists the initiator as not controlled for that claim, an amber cell partly controlled. Split cells show a rating that improves in the reference build. Dashed cells with a dagger are claims named in the §4 Elements reached column but not listed in §5. The bottom row gives the §5 verdict per claim: IC-01 and IC-06 not independent, IC-02, IC-04 and IC-05 partly, IC-03 open, IC-07 not applicable. {n_n} initiators are rated not controlled at the baseline; none is rated controlled.</desc>')
  out.append('<defs><pattern id="na" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#F8FAFC"/><line x1="0" y1="0" x2="0" y2="6" stroke="#E2E8F0" stroke-width="2"/></pattern></defs>')
  out.append(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')
  out.append(t(40, 44, "Figure 5-1 · Dependent failure initiators vs independence claims", 20, INK, 700))
  out.append(t(40, 66, "Rows: DFI-xx of §4 · columns: claims IC-xx of §2 · cell colour: evaluation from §5 · baseline 8b8c6ae, reference-build changes split", 12.5, MUTED))
  out.append(t(W - 40, 44, "WP-A-03 §5", 11, MUTED, anchor="end"))
  out.append(t(W - 40, 62, "initiators §4 · claims §2 · evaluation §5", 11, MUTED, anchor="end"))
  out.append(f'<line x1="40" y1="82" x2="{W - 40}" y2="82" stroke="{HAIR}"/>')
  # column heads
  out.append(t(LX, head_y + 14, "INITIATOR", 10, MUTED, 700))
  out.append(t(EX + 40, head_y + 14, "EVAL (§4)", 10, MUTED, 700, "middle"))
  for i, cl in enumerate(claims):
    cx = CX0 + i * CW + CW / 2
    out.append(t(cx, head_y + 14, cl.ident, 12, INK, 700, "middle"))
    for j, ln in enumerate(wrap(cl.label, 17)[:2]):
      out.append(t(cx, head_y + 30 + j * 13, ln, 10, MUTED, anchor="middle"))
  # column backgrounds
  for i, cl in enumerate(claims):
    x = CX0 + i * CW
    fill = "url(#na)" if cl.verdict.lower().startswith("not applicable") else ("#FFFFFF" if i % 2 else "#FBFCFD")
    out.append(rect(x + 2, grid_top, CW - 4, grid_bottom - grid_top, fill))
  y = grid_top
  for sec in order:
    out.append(rect(LX, y + 2, W - 80, RH - 4, "#F1F5F9", rx=4))
    out.append(t(LX + 8, y + 15, f"§{sec} {sections[sec]}", 10.5, MUTED, 700))
    y += RH
    for d in [x for x in dfis if x.section == sec]:
      out.append(f'<line x1="{LX}" y1="{y + RH:g}" x2="{W - 40}" y2="{y + RH:g}" stroke="#F1F5F9"/>')
      out.append(t(LX, y + 15, d.ident, 11, INK, 700))
      name = d.name if len(d.name) <= 58 else d.name[:56].rstrip() + "…"
      out.append(t(LX + 52, y + 15, name, 11, INK))
      # eval chip
      cy = y + 4
      if d.ref:
        out.append(rect(EX, cy, 22, 14, RATING_COLOUR[d.base], rx=3))
        out.append(t(EX + 11, cy + 11, d.base, 10, "#FFFFFF", 700, "middle"))
        out.append(t(EX + 30, cy + 11, "→", 10, MUTED, anchor="middle"))
        out.append(rect(EX + 38, cy, 22, 14, RATING_COLOUR[d.ref], rx=3))
        out.append(t(EX + 49, cy + 11, d.ref, 10, "#FFFFFF", 700, "middle"))
        out.append(t(EX + 66, cy + 11, "ref", 9.5, AMBER, 600))
      else:
        out.append(rect(EX, cy, 22, 14, RATING_COLOUR.get(d.base, GREY), rx=3))
        out.append(t(EX + 11, cy + 11, d.base, 10, "#FFFFFF", 700, "middle"))
      any_cell = False
      for i, cl in enumerate(claims):
        x = CX0 + i * CW + 10
        w = CW - 20
        if d.ident in listed_n[cl.ident] or d.ident in listed_p[cl.ident]:
          any_cell = True
          r = "N" if d.ident in listed_n[cl.ident] else "P"
          if d.ref and d.ref != r:
            out.append(rect(x, cy, w / 2, 14, RATING_COLOUR[r]))
            out.append(rect(x + w / 2, cy, w / 2, 14, RATING_COLOUR[d.ref]))
            out.append(t(x + w / 4, cy + 11, r, 10, "#FFFFFF", 700, "middle"))
            out.append(t(x + 3 * w / 4, cy + 11, f"{d.ref} ref", 9.5, "#FFFFFF", 700, "middle"))
          else:
            out.append(rect(x, cy, w, 14, RATING_COLOUR[r], rx=3))
            out.append(t(x + w / 2, cy + 11, r, 10, "#FFFFFF", 700, "middle"))
        elif cl.ident in d.ic_tags:
          any_cell = True
          col = RATING_COLOUR.get(d.base, GREY)
          out.append(rect(x, cy, w, 14, "#FFFFFF", col, 1.4, rx=3, dash="3 2"))
          out.append(t(x + w / 2, cy + 11, f"{d.base} †", 10, col, 700, "middle"))
      if not any_cell:
        x = CX0 + 10
        w = CW * len(claims) - 20
        out.append(rect(x, cy, w, 14, "#FFFFFF", RATING_COLOUR.get(d.base, GREY), 1.4, rx=3, dash="3 2"))
        out.append(t(x + w / 2, cy + 11, f"{d.base} † · reaches: {re.sub(r'[*`]', '', d.reached)} · not assigned to a claim in §5", 10, RATING_COLOUR.get(d.base, GREY), 700, "middle"))
      y += RH
  # verdict row
  out.append(f'<line x1="{LX}" y1="{verdict_y - 4}" x2="{W - 40}" y2="{verdict_y - 4}" stroke="{MUTED}"/>')
  out.append(t(LX, verdict_y + 18, "Verdict per claim (§5, current baseline)", 12, INK, 700))
  same = [cl.ident for cl in claims if cl.unchanged]
  if same:
    out.append(t(LX, verdict_y + 34, f"{', '.join(same)}: unchanged in the reference build (§5)", 10, MUTED))
  for i, cl in enumerate(claims):
    x = CX0 + i * CW + 6
    fill, tc = verdict_colour(cl.verdict)
    label = "n/a" if cl.verdict.lower().startswith("not applicable") else cl.verdict
    stroke = GREY if fill.startswith("#F") else "none"
    out.append(rect(x, verdict_y + 4, CW - 12, 36, fill, stroke, 1, rx=6, dash="4 3" if label == "n/a" else None))
    ls = wrap(label, 12)
    for j, ln in enumerate(ls):
      out.append(t(x + (CW - 12) / 2, verdict_y + 26 - 6.5 * (len(ls) - 1) + j * 13, ln, 10.5, tc, 700, "middle"))
  # legend
  ly = legend_y
  out.append(f'<line x1="40" y1="{ly - 12}" x2="{W - 40}" y2="{ly - 12}" stroke="{HAIR}"/>')
  items = [
    (rect(0, 0, 26, 14, RED, rx=3) + t(13, 11, "N", 10, "#FFFFFF", 700, "middle"), "Not controlled", 150),
    (rect(0, 0, 26, 14, AMBER, rx=3) + t(13, 11, "P", 10, "#FFFFFF", 700, "middle"), "Partly controlled (none is rated controlled)", 310),
    (rect(0, 0, 13, 14, RED) + rect(13, 0, 13, 14, AMBER), "Baseline → reference build bf6ce8c (not verified on hardware)", 400),
    (rect(0, 0, 26, 14, "#FFFFFF", AMBER, 1.4, rx=3, dash="3 2"), "† named in §4 “Elements reached”, not listed in §5", 330),
  ]
  gx = 40
  for sw, lab, wdt in items:
    out.append(f'<g transform="translate({gx},{ly})">{sw}{t(34, 11, lab, 10.5, INK)}</g>')
    gx += wdt
  ly2 = ly + 26
  out.append(f'<g transform="translate(40,{ly2})">{rect(0, 0, 26, 14, "url(#na)", GREY, 1, rx=3)}{t(34, 11, "Fallback claim, not applicable unless WP-A-01 DEC-01 is activated", 10.5, INK)}</g>')
  for k, cl in enumerate(notes):
    out.append(t(40, ly2 + 34 + 16 * k, f"{cl.ident} §5 also counts {cl.note} as partly controlled (interference, analysed in WP-A-02).", 10.5, MUTED))
  out.append("</svg>")
  return "\n".join(out) + "\n"


def build() -> str:
  dfis, claims, sections = parse(SOURCE.read_text(encoding="utf-8"))
  return draw(dfis, claims, sections)


def main(argv: list[str]) -> int:
  check = "--check" in argv
  try:
    content = build()
  except ParseError as e:
    print(f"fig_a03_dfi_matrix: {e}", file=sys.stderr)
    return 1
  path = HERE / OUTPUT
  if "--findings" in argv:
    dfis, claims, _ = parse(SOURCE.read_text(encoding="utf-8"))
    for f in findings(dfis, claims):
      print(f)
    return 0
  if check:
    if not path.exists() or path.read_text(encoding="utf-8") != content:
      print(f"stale: {OUTPUT}", file=sys.stderr)
      print("run: python3 assurance/08-analyses/figures/fig_a03_dfi_matrix.py", file=sys.stderr)
      return 1
    print("fig_a03_dfi_matrix: figure current")
    return 0
  path.write_text(content, encoding="utf-8")
  print(f"fig_a03_dfi_matrix: wrote {OUTPUT}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
