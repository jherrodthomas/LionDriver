#!/usr/bin/env python3
"""Draw WP-V-05 Figure 6-1: fault-injection coverage (cases x TSR blocks x safety goals, plus §6 analysis items).

The source of record is `../WP-V-05-fault-injection.md`. This script parses
  * the §5.1–§5.6 fault tables (ID, fault, level, mechanism TSRs, "At `682f184`" column),
  * the §6 coverage table (analysis item -> fault-injection cases), and
  * the §8 report table (result per case),
and, from `../../03-system/WP-S-02-technical-safety-requirements.md`, the TSR IDs, their parent FSRs (FSR-nn.mm
belongs to SG-nn) and the block titles. Nothing here is test content: change the documents and regenerate.

Cell rules: a TSR-block cell is filled when the case's Mechanism column names a TSR of that block (the number
is how many); a safety-goal cell is filled when one of those TSRs has a parent FSR of that goal. A case whose
Mechanism reads "As in the referenced cases" inherits the TSRs of the cases its Target names, drawn hollow.
Status is never drawn green: no case has been executed (§8), and the "At `682f184`" column is implementation
status from WP-W-02, not verification.

    python3 fig_v05_fault_coverage.py            # regenerate the SVG
    python3 fig_v05_fault_coverage.py --check    # fail if a source text changed or the SVG is stale

Standard library only. Output is deterministic.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "WP-V-05-fault-injection.md"
WP_S_02 = HERE.parent.parent / "03-system" / "WP-S-02-technical-safety-requirements.md"
OUTPUT = "fig-v05-6-1-fault-coverage.svg"

# ---------------------------------------------------------------- palette (assurance figure style)
FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SFMono-Regular', Menlo, Consolas, monospace"
INK, MUTED, FAINT, LINE, HAIR = "#0F172A", "#475569", "#94A3B8", "#CBD5E1", "#E2E8F0"
CHIP = "#F8FAFC"
SAFETY, SAFETY_BG = "#C2410C", "#FFF7ED"
SW, SW_BG = "#0F766E", "#F0FDFA"
HW, HW_BG = "#4F46E5", "#EEF2FF"
GREEN = "#2E9E6A"
AMBER, AMBER_BG = "#D97706", "#FFFBEB"
RED, RED_BG = "#D2553F", "#FEF2F2"
GREY_BG = "#F1F5F9"

LEVELS = ("U", "S", "H", "V", "A")
GOALS = tuple(f"SG-0{i}" for i in range(1, 8))
RESULT_COLOUR = {"pass": GREEN, "fail": RED, "fail known gap": RED, "blocked": AMBER}

# Prose-only facts, each with the exact text it is read from (checked by --check).
PROSE = {
  "sfmea_open": {"label": "8 System FMEA causes", "detail": "from WP-A-04 v0.2: no case yet (OI-6)",
                 "src": ["except eight added in WP-A-04 v0.2, which still need cases (OI-6)"]},
  "not_executed": {"src": ["| Status | Draft (specification). **Results: not yet executed** |"]},
  "level_a": {"src": ["| VS-FI-20 | Clock fault | HSE stop (test pad) or analysis; clock drift (if injectable) | H, A |"]},
}


class ParseError(Exception):
  pass


# ---------------------------------------------------------------- parsing (split_row / refs_in as in trace_map.py)

ID_RE = re.compile(r"\b(TSR)-(\d{3})([a-z]?)\b")
RANGE_RE = re.compile(r"\b(TSR)-(\d{3})\s*[…–-]\s*(?:\1-)?(\d{3})\b")


def split_row(line: str) -> list[str]:
  cells = re.split(r"(?<!\\)\|", line.strip())
  return [c.strip() for c in cells[1:-1]]


def refs_in(text: str, known: set[str]) -> set[str]:
  """TSR IDs named in a cell: prefixed IDs and prefixed ranges (TSR-101…TSR-109)."""
  found = {f"{k}-{n}{s}" for k, n, s in ID_RE.findall(text)}
  for kind, lo, hi in RANGE_RE.findall(text):
    for n in range(int(lo), int(hi) + 1):
      if f"{kind}-{n}" in known:
        found.add(f"{kind}-{n}")
  return found


def case_refs(text: str) -> list[str]:
  """VS-FI cases named in a cell, with the short form "VS-FI-06, -08, -10"."""
  out: list[str] = []
  for m in re.finditer(r"VS-FI-(\d{2})((?:\s*,\s*-\d{2}\b)*)", text):
    out.append(f"VS-FI-{m.group(1)}")
    out += [f"VS-FI-{n}" for n in re.findall(r"-(\d{2})\b", m.group(2))]
  return out


@dataclass
class Tsr:
  ident: str
  block: str            # "1" … "8"
  goals: set[str]


@dataclass
class Case:
  ident: str
  section: str
  fault: str
  levels: list[str]
  tsrs: set[str]
  inherited: bool
  status: dict[str, int]      # WP-W-02 baseline words -> count ("unchanged" when "As at `8b8c6ae`")
  result: str = ""
  goals: set[str] = field(default_factory=set)


@dataclass
class Item:
  analysis: str         # WP-A-04 / WP-A-02 / WP-A-03
  ident: str            # SPF-06, FFI-CM-01…-04, -11, ...
  detail: str
  cases: list[str]


def parse_tsrs(md: str) -> tuple[dict[str, Tsr], dict[str, str]]:
  titles = {n: re.sub(r"\s*\([^)]*\)$", "", t) for n, t in re.findall(r"^## \d+\. TSR-(\d)xx (.+?)\s*$", md, re.M)}
  tsrs: dict[str, Tsr] = {}
  head: list[str] = []
  for line in md.splitlines():
    if line.startswith("| ID |"):
      head = split_row(line)
    m = re.match(r"^\|\s*(TSR-(\d)\d{2}[a-z]?)\s*\|", line)
    if not m or len(head) < 4 or not head[1].startswith("Requirement") or head[3] != "Parent":
      continue
    c = split_row(line)
    goals = {f"SG-{g}" for g in re.findall(r"\bFSR-(\d{2})\.\d{2}", c[3])}
    goals |= {f"SG-{g}" for g in re.findall(r"\bSG-(\d{2})\b", c[3])}
    tsrs[m.group(1)] = Tsr(m.group(1), m.group(2), goals)
  if not tsrs or len(titles) != 8:
    raise ParseError("WP-S-02: TSR rows or the eight TSR-nxx block headings not found")
  return tsrs, titles


def status_words(cell: str) -> dict[str, int]:
  if cell.startswith("As at"):
    return {"unchanged": 1}
  out: dict[str, int] = {}
  for word in re.findall(r"SWSR-\d{3}[a-z]?:\s*(Met|Partial|Implemented)", cell):
    out[word] = out.get(word, 0) + 1
  if not out:
    raise ParseError(f"'At 682f184' cell without a known status: {cell[:60]}")
  return out


def parse(md: str, tsrs: dict[str, Tsr]) -> tuple[list[Case], dict[str, str], list[Item]]:
  known = set(tsrs)
  cases: list[Case] = []
  sections: dict[str, str] = {}
  section = ""
  for line in md.splitlines():
    h = re.match(r"^### (5\.\d) (.+)$", line)
    if h:
      section = h.group(1)
      sections[section] = h.group(2).strip()
      continue
    if line.startswith("## "):
      section = ""
      continue
    if section and re.match(r"^\|\s*VS-FI-\d{2}\s*\|", line):
      c = split_row(line)
      if len(c) != 10:
        raise ParseError(f"{c[0]}: expected 10 columns, got {len(c)}")
      levels = re.findall(r"\b([A-Z])\b", re.sub(r"\([^)]*\)", "", c[3]))
      for lv in levels:
        if lv not in LEVELS:
          raise ParseError(f"{c[0]}: unknown level {lv}")
      inherited = c[4].startswith("As in the referenced cases")
      cases.append(Case(c[0], section, c[1], levels, refs_in(c[4], known), inherited, status_words(c[9])))
  if not cases:
    raise ParseError("no VS-FI rows in §5")
  by_id = {c.ident: c for c in cases}
  for c in cases:
    if c.inherited:
      target = next(line for line in md.splitlines() if line.startswith(f"| {c.ident} |"))
      for ref in case_refs(split_row(target)[2]):
        c.tsrs |= by_id[ref].tsrs
    unknown = c.tsrs - known
    if unknown:
      raise ParseError(f"{c.ident}: TSR not in WP-S-02: {sorted(unknown)}")
    if not c.tsrs:
      raise ParseError(f"{c.ident}: no TSR in the Mechanism column")
    c.goals = set().union(*(tsrs[t].goals for t in c.tsrs))
  # §8 results
  s8 = md.split("\n## 8. Report", 1)[1].split("\n## ", 1)[0]
  for line in s8.splitlines():
    if re.match(r"^\|\s*VS-FI-\d{2}\s*\|", line):
      c = split_row(line)
      if c[0] in by_id:
        by_id[c[0]].result = c[9].replace("*", "").strip()
  # §6 items
  s6 = md.split("\n## 6. Coverage of safety analyses", 1)[1].split("\n## ", 1)[0]
  items: list[Item] = []
  for line in s6.splitlines():
    m = re.match(r"^\|\s*(WP-A-0\d)\s+(.+?)\s*\|", line)
    if not m:
      continue
    c = split_row(line)
    ident, _, detail = m.group(2).partition(" (")
    refs = case_refs(c[1])
    for r in refs:
      if r not in by_id:
        raise ParseError(f"§6 {ident} names {r}, which is not a §5 case")
    items.append(Item(m.group(1), ident.strip(), detail.rstrip(")"), refs))
  if not items:
    raise ParseError("no rows in the §6 coverage table")
  return cases, sections, items


def missing_sources(md: str) -> list[str]:
  return [s for p in PROSE.values() for s in p["src"] if s not in md]


# ---------------------------------------------------------------- SVG helpers (as trace_figures.py)

def el(tag: str, text: str | None = None, **attrs) -> str:
  a = "".join(f' {k.rstrip("_").replace("_", "-")}="{v}"' for k, v in attrs.items() if v not in ("", None))
  return f"<{tag}{a}/>" if text is None else f"<{tag}{a}>{escape(text)}</{tag}>"


def fmt(v: float) -> str:
  return f"{v:.1f}".rstrip("0").rstrip(".")


def text(x, y, s, size=11, fill=INK, weight="", anchor="", family="", style="") -> str:
  return el("text", s, x=fmt(x), y=fmt(y), font_size=size, fill=fill, font_weight=weight, text_anchor=anchor,
            font_family=family, font_style=style)


def rect(x, y, w, h, fill="#FFFFFF", stroke=LINE, sw=1.2, rx=8, dash="", opacity="") -> str:
  return el("rect", None, x=fmt(x), y=fmt(y), width=fmt(w), height=fmt(h), rx=rx, fill=fill, stroke=stroke,
            stroke_width=sw, stroke_dasharray=dash, opacity=opacity)


def line(x1, y1, x2, y2, stroke=MUTED, sw=1.4, dash="") -> str:
  return el("line", None, x1=fmt(x1), y1=fmt(y1), x2=fmt(x2), y2=fmt(y2), stroke=stroke, stroke_width=sw,
            stroke_dasharray=dash)


def circle(x, y, r, fill, stroke, sw=1.4, dash="") -> str:
  return el("circle", None, cx=fmt(x), cy=fmt(y), r=fmt(r), fill=fill, stroke=stroke, stroke_width=sw,
            stroke_dasharray=dash)


def header(width: int, number: str, title: str, subtitle: str, ref: str) -> list[str]:
  return [text(40, 44, f"Figure {number} · {title}", size=20, weight=700),
          text(40, 66, subtitle, size=12.5, fill=MUTED),
          text(width - 40, 44, ref, size=11, fill=MUTED, anchor="end"),
          line(40, 82, width - 40, 82, stroke=HAIR, sw=1)]


def svg(width: int, height: int, title: str, desc: str, body: list[str]) -> str:
  hatch = ('<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" ' +
           'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="#CBD5E1" ' +
           'stroke-width="2"/></pattern></defs>')
  head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" ' +
          f'viewBox="0 0 {width} {height}" font-family="{FONT}" role="img">')
  return "\n".join([head, el("title", title), el("desc", desc), hatch,
                    rect(0, 0, width, height, fill="#FFFFFF", stroke="none", rx=0, sw=0), *body, "</svg>"]) + "\n"


def clip(s: str, n: int) -> str:
  s = s.replace("`", "")
  return s if len(s) <= n else s[:n - 1].rstrip(" ,;/(") + "…"


# ---------------------------------------------------------------- layout

W = 1280
X_ID, X_FAULT = 40, 106
X_LVL, LVL_W = 334, 15
X_TSR, TSR_W = 424, 33
X_SG, SG_W = 700, 31
X_S6 = 940
X_STAT = 972
X_RES = 1140
ROW_H, GROUP_H = 21, 26


def status_text(st: dict[str, int]) -> tuple[str, str]:
  if "unchanged" in st:
    return "unchanged since 8b8c6ae", FAINT
  short = {"Met": "Met", "Implemented": "Impl.", "Partial": "Partial"}
  parts = [f"{short[w]} {st[w]}" for w in ("Met", "Implemented", "Partial") if w in st]
  return "SWSR " + " · ".join(parts), AMBER


def figure(cases: list[Case], sections: dict[str, str], items: list[Item], tsrs: dict[str, Tsr],
           titles: dict[str, str]) -> str:
  body: list[str] = []
  n = len(cases)
  covered = {c for it in items for c in it.cases}
  body += header(W, "6-1", "Fault-injection coverage",
                 f"The {n} fault-injection cases of §5 against the TSR blocks and safety goals their mechanisms " +
                 "serve, and the §6 analysis items they cover. Specification only: nothing has been executed.",
                 "WP-V-05 §5, §6, §8")

  top = 104
  # column headers
  body.append(text(X_ID, top + 40, "Case · fault", size=11.5, weight=700))
  body.append(text(X_LVL, top + 12, "Level (§3)", size=11, weight=700))
  body.append(text(X_TSR, top + 12, "TSR block of the mechanism (WP-S-02)", size=11, weight=700))
  body.append(text(X_SG, top + 12, "Safety goal (via parent FSR)", size=11, weight=700))
  body.append(text(X_S6 + 14, top + 12, "§6", size=11, weight=700, anchor="middle"))
  body.append(text(X_STAT, top + 12, "At 682f184 (WP-W-02)", size=11, weight=700))
  body.append(text(X_RES, top + 12, "Result (§8)", size=11, weight=700))
  hy = top + 40
  for i, lv in enumerate(LEVELS):
    body.append(text(X_LVL + i * LVL_W + 7, hy, lv, size=10.5, fill=MUTED, weight=700, anchor="middle",
                     family=MONO))
  for b in range(1, 9):
    body.append(text(X_TSR + (b - 1) * TSR_W + TSR_W / 2, hy, f"{b}xx", size=10.5, fill=MUTED, weight=700,
                     anchor="middle", family=MONO))
  for i, g in enumerate(GOALS):
    body.append(text(X_SG + i * SG_W + SG_W / 2, hy, g[3:], size=10.5, fill=MUTED, weight=700, anchor="middle",
                     family=MONO))
  body.append(text(X_S6 + 14, hy, "item", size=10, fill=MUTED, anchor="middle"))
  body.append(text(X_STAT, hy, "SWSR status of the case's TSRs", size=10, fill=MUTED))
  body.append(text(X_RES, hy, "campaign", size=10, fill=MUTED))
  body.append(text(X_SG, top + 26, "SG-0n", size=10, fill=MUTED))
  body.append(line(40, hy + 8, W - 40, hy + 8, stroke=LINE, sw=1))

  y = hy + 8
  tsr_count = dict.fromkeys(range(1, 9), 0)
  goal_count = dict.fromkeys(GOALS, 0)
  for sec in sorted(sections):
    group = [c for c in cases if c.section == sec]
    body.append(rect(40, y, W - 80, GROUP_H, fill=GREY_BG, stroke="none", rx=0, sw=0))
    body.append(text(X_ID + 6, y + 17, f"§{sec} {sections[sec]}", size=11, weight=700))
    body.append(text(X_FAULT + 300, y + 17, f"{len(group)} case{'s' if len(group) != 1 else ''}", size=10.5,
                     fill=MUTED))
    y += GROUP_H
    for k, c in enumerate(group):
      ym = y + ROW_H / 2
      if k % 2 == 1:
        body.append(rect(40, y, W - 80, ROW_H, fill=CHIP, stroke="none", rx=0, sw=0))
      body.append(text(X_ID + 6, ym + 4, c.ident[3:], size=10.5, weight=700, family=MONO))
      body.append(text(X_FAULT, ym + 4, clip(c.fault, 41), size=10, fill=INK))
      for i, lv in enumerate(LEVELS):
        if lv in c.levels:
          body.append(rect(X_LVL + i * LVL_W + 1, ym - 6.5, 12, 13, fill=INK if lv != "A" else "#FFFFFF",
                           stroke=INK if lv != "A" else MUTED, sw=1, rx=2, dash="" if lv != "A" else "2 1.5"))
          body.append(text(X_LVL + i * LVL_W + 7, ym + 3.5, lv, size=9, fill="#FFFFFF" if lv != "A" else MUTED,
                           weight=700, anchor="middle"))
      blocks: dict[int, int] = {}
      for t in c.tsrs:
        blocks[int(tsrs[t].block)] = blocks.get(int(tsrs[t].block), 0) + 1
      for b in range(1, 9):
        cx = X_TSR + (b - 1) * TSR_W + TSR_W / 2
        if b in blocks:
          tsr_count[b] += 1
          if c.inherited:
            body.append(circle(cx, ym, 7.5, "#FFFFFF", SAFETY, 1.4, "2.5 2"))
            body.append(text(cx, ym + 3.5, str(blocks[b]), size=9, fill=SAFETY, weight=700, anchor="middle"))
          else:
            body.append(circle(cx, ym, 7.5, SAFETY, SAFETY))
            body.append(text(cx, ym + 3.5, str(blocks[b]), size=9, fill="#FFFFFF", weight=700, anchor="middle"))
        else:
          body.append(circle(cx, ym, 1.6, HAIR, HAIR, 0))
      for i, g in enumerate(GOALS):
        cx = X_SG + i * SG_W + SG_W / 2
        if g in c.goals:
          goal_count[g] += 1
          if c.inherited:
            body.append(circle(cx, ym, 5.5, "#FFFFFF", HW, 1.4, "2.5 2"))
          else:
            body.append(circle(cx, ym, 5.5, HW, HW))
        else:
          body.append(circle(cx, ym, 1.6, HAIR, HAIR, 0))
      if c.ident in covered:
        body.append(circle(X_S6 + 14, ym, 5, SW_BG, SW, 1.4))
      else:
        body.append(text(X_S6 + 14, ym + 4, "—", size=10, fill=FAINT, anchor="middle"))
      st, colour = status_text(c.status)
      body.append(text(X_STAT, ym + 4, st, size=10, fill=colour if colour == FAINT else INK))
      if colour == AMBER:
        body.append(rect(X_STAT - 9, ym - 4, 5, 8, fill=AMBER, stroke="none", rx=1, sw=0))
      res = c.result.lower()
      rc = RESULT_COLOUR.get(res)
      if rc:
        body.append(rect(X_RES, ym - 7.5, 96, 15, fill=rc, stroke=rc, rx=7.5))
        body.append(text(X_RES + 48, ym + 3.5, c.result, size=9.5, fill="#FFFFFF", weight=700, anchor="middle"))
      else:
        body.append(rect(X_RES, ym - 7.5, 96, 15, fill="#FFFFFF", stroke=FAINT, rx=7.5, dash="3 2"))
        body.append(text(X_RES + 48, ym + 3.5, c.result.lower() or "no entry", size=9.5, fill=MUTED,
                         anchor="middle"))
      y += ROW_H
  body.append(line(40, y, W - 40, y, stroke=LINE, sw=1))
  # column totals
  ty = y + 16
  body.append(text(X_FAULT, ty, "cases naming the column", size=10, fill=MUTED, anchor=""))
  for b in range(1, 9):
    body.append(text(X_TSR + (b - 1) * TSR_W + TSR_W / 2, ty, str(tsr_count[b]), size=10.5, fill=SAFETY, weight=700,
                     anchor="middle"))
  for i, g in enumerate(GOALS):
    body.append(text(X_SG + i * SG_W + SG_W / 2, ty, str(goal_count[g]), size=10.5, fill=HW, weight=700,
                     anchor="middle"))
  body.append(text(X_S6 + 14, ty, str(len(covered)), size=10.5, fill=SW, weight=700, anchor="middle"))
  n_done = sum(1 for c in cases if c.result.lower() in RESULT_COLOUR)
  body.append(text(X_RES, ty, f"{n_done} of {n} executed", size=10.5, fill=MUTED, weight=700))
  # block key
  ky = ty + 20
  key = "  ·  ".join(f"{b}xx {titles[str(b)]}" for b in range(1, 9))
  body.append(text(X_FAULT, ky, "TSR blocks: " + key[:150], size=9.5, fill=MUTED))
  if len(key) > 150:
    rest = key[150:]
    body.append(text(X_FAULT, ky + 13, rest, size=9.5, fill=MUTED))
    ky += 13

  # §6 strip
  sy = ky + 32
  body.append(line(40, sy - 16, W - 40, sy - 16, stroke=HAIR, sw=1))
  body.append(text(40, sy, "§6 Coverage of safety analyses", size=13, weight=700))
  n_cov = sum(1 for it in items if it.cases)
  body.append(text(270, sy, f"{len(items)} items listed: {n_cov} have a specified case (not executed), " +
                   f"{len(items) - n_cov} not testable by fault injection; eight System FMEA causes from WP-A-04 v0.2 have no case yet. " +
                   "§6 names no STPA (WP-A-05) item.", size=10.5, fill=MUTED))
  groups = [("WP-A-04", "System FTA / FMEA (WP-A-04)"), ("WP-A-02", "Freedom from interference (WP-A-02)"),
            ("WP-A-03", "Dependent failures (WP-A-03)")]
  cy = sy + 16
  chip_w, chip_h, gap = 232, 36, 8
  for key_a, title in groups:
    group = [it for it in items if it.analysis == key_a]
    if key_a == "WP-A-04":
      group = group + [Item("WP-A-04", PROSE["sfmea_open"]["label"], PROSE["sfmea_open"]["detail"], [])]
    body.append(text(40, cy + 14, title, size=10.5, weight=700, fill=INK))
    x = 250
    row_y = cy
    for it in group:
      if x + chip_w > W - 40:
        x = 250
        row_y += chip_h + gap
      is_open = it.ident == PROSE["sfmea_open"]["label"]
      if it.cases:
        body.append(rect(x, row_y, chip_w, chip_h, fill="#FFFFFF", stroke=SW, sw=1.3, rx=6))
        sub = "→ " + ", ".join(c[3:] for c in it.cases)
        col = SW
      elif is_open:
        body.append(rect(x, row_y, chip_w, chip_h, fill=RED_BG, stroke=RED, sw=1.3, rx=6, dash="4 3"))
        sub = "no fault-injection case yet (OI-6)"
        col = RED
      else:
        body.append(rect(x, row_y, chip_w, chip_h, fill="url(#hatch)", stroke=FAINT, sw=1.2, rx=6, dash="4 3"))
        sub = "not testable by fault injection"
        col = MUTED
      body.append(text(x + 8, row_y + 15, it.ident, size=10.5, weight=700, fill=INK, family=MONO))
      det = clip(it.detail, 34 - len(it.ident) // 2) if it.detail and not is_open else ""
      if det:
        body.append(text(x + 14 + len(it.ident) * 6.4, row_y + 15, det, size=9.5, fill=MUTED))
      body.append(text(x + 8, row_y + 29, clip(sub, 40), size=9.5, fill=col, weight=600 if col != MUTED else ""))
      x += chip_w + gap
    cy = row_y + chip_h + 12

  # legend
  ly = cy + 18
  body.append(line(40, ly - 16, W - 40, ly - 16, stroke=HAIR, sw=1))
  lx = 40
  body.append(circle(lx + 7, ly - 4, 7, SAFETY, SAFETY))
  body.append(text(lx + 20, ly, "TSRs of the block named (count)", size=10.5, fill=MUTED))
  lx += 205
  body.append(circle(lx + 6, ly - 4, 5.5, HW, HW))
  body.append(text(lx + 18, ly, "goal reached via the TSR's parent FSR", size=10.5, fill=MUTED))
  lx += 228
  body.append(circle(lx + 7, ly - 4, 7, "#FFFFFF", SAFETY, 1.4, "2.5 2"))
  body.append(text(lx + 20, ly, "inherited: \"As in the referenced cases\" (27 → 08, 09, 14)", size=10.5, fill=MUTED))
  lx += 330
  body.append(circle(lx + 6, ly - 4, 5, SW_BG, SW, 1.4))
  body.append(text(lx + 17, ly, "named by a §6 item", size=10.5, fill=MUTED))
  ly2 = ly + 22
  body.append(rect(40, ly2 - 10, 12, 13, fill=INK, stroke=INK, rx=2, sw=1))
  body.append(text(58, ly2, "level U unit, S SoC SIL, H HIL, V vehicle; A is not defined in §3 (VS-FI-20)",
                   size=10.5, fill=MUTED))
  body.append(rect(500, ly2 - 9, 5, 8, fill=AMBER, stroke="none", rx=1, sw=0))
  body.append(text(512, ly2, "implementation status from WP-W-02, not verified", size=10.5, fill=MUTED))
  body.append(rect(800, ly2 - 10, 34, 13, fill="#FFFFFF", stroke=FAINT, rx=6.5, dash="3 2"))
  body.append(text(842, ly2, "§8: not yet executed (nothing is green)", size=10.5, fill=MUTED))
  height = int(ly2 + 22)
  desc = (f"Matrix of the {n} fault-injection cases VS-FI-01 to VS-FI-{n:02d}, grouped by §5.1 to §5.6. For each " +
          "case: injection levels, the TSR blocks 1xx to 8xx its mechanism names (with counts), the safety goals " +
          "SG-01 to SG-07 reached through the parent FSRs, whether a §6 analysis item names it, the WP-W-02 " +
          "implementation status, and the §8 result, which is 'not yet executed' for every case. Below, the " +
          f"{len(items)} §6 analysis items from WP-A-04, WP-A-02 and WP-A-03 with their cases; SPF-01 is not " +
          "testable by fault injection and eight System FMEA causes from WP-A-04 v0.2 have no case yet.")
  return svg(W, height, "Figure 6-1 · Fault-injection coverage", desc, body)


def load() -> tuple[list[Case], dict[str, str], list[Item], dict[str, Tsr], dict[str, str]]:
  tsrs, titles = parse_tsrs(WP_S_02.read_text(encoding="utf-8"))
  cases, sections, items = parse(SOURCE.read_text(encoding="utf-8"), tsrs)
  return cases, sections, items, tsrs, titles


def build() -> str:
  return figure(*load())


def main(argv: list[str]) -> int:
  check = "--check" in argv
  missing = missing_sources(SOURCE.read_text(encoding="utf-8"))
  if missing:
    for s in missing:
      print(f"source text no longer in WP-V-05: {s}", file=sys.stderr)
    print("review the prose data in fig_v05_fault_coverage.py against WP-V-05 and regenerate", file=sys.stderr)
    return 1
  out = build()
  path = HERE / OUTPUT
  if check:
    if not path.exists() or path.read_text(encoding="utf-8") != out:
      print(f"stale: {OUTPUT}", file=sys.stderr)
      print("run: python3 assurance/06-validation/figures/fig_v05_fault_coverage.py", file=sys.stderr)
      return 1
    print(f"fig_v05_fault_coverage: {OUTPUT} current")
    return 0
  path.write_text(out, encoding="utf-8")
  print(f"fig_v05_fault_coverage: wrote {OUTPUT}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
