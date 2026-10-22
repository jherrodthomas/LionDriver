#!/usr/bin/env python3
"""Render the animated explainers of the wiki page "ASPICE: is the process capable?" as SVG.

  aspice-question.svg  product against process, the capability levels 0–5, LionDriver's targets and baseline;
  aspice-v.svg         the ASPICE 4.0 V with each process's LionDriver work product, and the processes around it;
  aspice-rating.svg    how a process is rated, with SWE.4 as the example: evidence found and missing, N/P/L/F, level 2;
  aspice-baseline.svg  every process in scope with its level today and its target, and where evidence has moved;
  aspice-trace.svg     two-way traceability: one chain, the derivation and verification coverage of the trace map;
  aspice-together.svg  ASPICE beside ISO 26262, what only each covers, and the integrated process model;
  aspice-plan.svg      the improvement actions, the self-assessment at each gate and the formal assessment.

The process levels and targets, the processes and actions where evidence has moved, the improvement actions, the trace
coverage and the activity count are read from WP-M-13, the ASPICE trace map (WP-T-01) and the process model (WP-P-11).
Every other phrase is tied to its record (SOURCES) and checked at render time (`problems()`). When a record changes,
the wiki build fails instead of showing old text. The levels shown are those of WP-M-13's self-assessment, which is not
a formal ASPICE assessment, and the figures say so. build_wiki.py renders them next to the pages at each sync; they loop
with CSS and reduced motion shows the final frame.

Usage: python3 tools/wiki/aspice_animations.py [--out DIR] [--check]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from animations import GRN, LIGHT, MID, NAVY, RED, W, Timeline, g, norm, stick, svg, t  # noqa: E402

NAMES = ("aspice-question.svg", "aspice-v.svg", "aspice-rating.svg", "aspice-baseline.svg", "aspice-trace.svg",
         "aspice-together.svg", "aspice-plan.svg")
AMBER, BLUE, VIOLET, ORANGE, TEAL = "#b7791f", "#2a78d6", "#6250d6", "#c2410c", "#0f766e"
FS, AS = BLUE, VIOLET

M13 = Path("assurance") / "01-management" / "WP-M-13-aspice-capability-baseline.md"
MAP = Path("assurance") / "trace" / "maps" / "aspice-trace-map.md"
MODEL = Path("assurance") / "process" / "model"
REG = Path("assurance") / "01-management" / "WP-M-00-work-product-register.md"

# (record, phrase a figure stands on)
SOURCES = [
  (M13, "Self-assessment**, not a formal ASPICE assessment"), (M13, "N (0–15 %), P (>15–50 %), L (>50–85 %), F (>85–100 %)"),
  (M13, "CL1 needs PA 1.1 rated L or F. CL2 additionally needs PA 1.1 = F and PA 2.1, PA 2.2 rated L or F"),
  (M13, "| A | SYS.1, SYS.2, SYS.3, SYS.4, SYS.5, SWE.1–SWE.6, SUP.1, SUP.8, SUP.9, SUP.10, MAN.3, MAN.5 | **CL2** |"),
  (M13, "| SWE.4 Software unit verification | L (safety code) / P (rest) | Safety code: 100 % line coverage gate"),
  (M13, "mutation testing (`tests/mutation.py`, CI job), UBSan, MISRA static analysis, per-brand tests (`tests/test_toyota.py`)"),
  (M13, "No unit verification strategy or specification separate from code; criteria are line coverage only (no branch/MC/DC); tests run on x86 host builds, not the target; results not retained"),
  (M13, "**All processes in scope are rated N for PA 2.1 and PA 2.2.**"),
  (M13, "The self-assessment is repeated at each gate (G0…G5)"), (M13, "a formal assessment by a certified assessor is required (OI-1)"),
  (M13, "Re-rating is an assessment; it is due at the next gate review, G0"),
  (MAP, "| SYS.2 ↔ SYS.5 | VS-SQ | FSR |"), (MAP, "## 6. Test cases naming unknown IDs"),
  (MAP, "but no test → result link exists"), (MAP, "- **Kinds outside the trace data:** none"),
  (Path("assurance") / "02-concept" / "WP-C-03-hara.md", "| SG-01 |"),
  (Path("assurance") / "02-concept" / "WP-C-04-functional-safety-concept.md", "| FSR-01.04 |"),
  (Path("assurance") / "03-system" / "WP-S-02-technical-safety-requirements.md", "| TSR-105 |"),
  (Path("assurance") / "05-software" / "WP-W-02-software-safety-requirements.md", "| SWSR-105 |"),
  (REG, "| [WP-W-06]"), (REG, "| [WP-S-09]"), (REG, "| [WP-W-03]"), (REG, "| [WP-V-01]"),
]
COVERAGE = [  # (kind, label, section, row key): the trace map row each bar is read from
  ("down", "safety goal → FSR", 4, "safety goal -> FSR"), ("down", "FSR → TSR", 4, "FSR -> TSR"),
  ("down", "TSR → SWSR", 4, "TSR -> SWSR (SW-allocated TSRs)"),
  ("across", "FSR checked by a system test", 5, ("SYS.2 ↔ SYS.5", "FSR")), ("across", "TSR checked by a system test", 5, ("SYS.2 ↔ SYS.5", "TSR")),
  ("across", "SWSR checked by a unit test", 5, ("SWE.3 ↔ SWE.4", "SWSR")), ("across", "AI requirement checked by a model test", 5, ("MLE.1 ↔ MLE.4", "AIR"))]


class ParseError(Exception):
  pass


def section(text: str, start: str, end: str) -> str:
  i = text.find(start)
  if i < 0:
    raise ParseError(f"heading {start!r} not found")
  j = text.find(end, i + len(start))
  return text[i:j if j > 0 else None]


def cells(line: str) -> list[str]:
  return [c.strip() for c in line.strip().strip("|").split("|")]


def data(root: Path = ROOT) -> dict:
  m = (root / M13).read_text(encoding="utf-8")
  base = []
  for line in section(m, "## 6. Summary", "![Figure 6-1").splitlines():
    if re.match(r"^\| [A-Z]{3}\.\d", line):
      c = cells(line)
      label = re.sub(r"^([A-Z]{3})\.(\d)–[A-Z]{3}\.(\d)$", r"\1.\2–\3", c[0])
      cur = c[1].replace(" ", "")
      tgt = int(c[2])
      grp = "A" if tgt == 2 else ("B" if c[0][:3] in ("MLE", "HWE") else "C")
      base.append((label, cur, tgt, grp))
  moved = set()
  for line in section(m, "## 9. Changes since", "## Open items").splitlines():
    if re.match(r"^\| [A-Z]{3}\.\d", line):
      moved |= set(re.findall(r"[A-Z]{3}\.\d+", cells(line)[0]))
  moved_rows = {lab for lab, *_ in base if lab in moved}
  ias, moved_ias = [], []
  for line in section(m, "## 7. Improvement actions", "## 8.").splitlines():
    if line.startswith("| IA-"):
      c = cells(line)
      ias.append(c[0])
      if set(re.findall(r"[A-Z]{3}\.\d+", c[2])) & moved:
        moved_ias.append(c[0])
  t = (root / MAP).read_text(encoding="utf-8")
  s4 = {cells(l)[0]: cells(l)[1] for l in section(t, "## 4. Derivation", "## 5.").splitlines() if l.startswith("| ") and "/" in l}
  s5 = {(cells(l)[0], cells(l)[2]): cells(l)[3] for l in section(t, "## 5. Verification", "## 6.").splitlines() if l.startswith("| ") and "↔" in l}
  cov = []
  for kind, lab, sec, key in COVERAGE:
    v = (s4 if sec == 4 else s5).get(key)
    if v is None:
      raise ParseError(f"trace map §{sec}: row {key!r} not found")
    n, d = (int(x) for x in v.split("/"))
    cov.append((kind, lab, n, d))
  unknown_none = section(t, "## 6. Test cases naming unknown IDs", "## 7.").strip().splitlines()[-1].strip() == "None."
  acts = sum(len(re.findall(r"^\s*kind: activity", p.read_text(encoding="utf-8"), re.M)) for p in sorted((root / MODEL).glob("*.yaml")))
  cl1 = [b for b in base if b[1].startswith("1")]
  return {"base": base, "ias": ias, "moved_rows": moved_rows, "moved_ias": moved_ias, "n_ia": len(ias), "coverage": cov,
          "unknown_none": unknown_none, "activities": acts, "cl1": len(cl1), "cl1_split": sum(1 for b in cl1 if "/" in b[1])}


def problems(root: Path = ROOT) -> list[str]:
  errs, cache = [], {}
  for path, phrase in SOURCES:
    if path not in cache:
      p = root / path
      cache[path] = norm(p.read_text(encoding="utf-8")) if p.exists() else ""
    if norm(phrase) not in cache[path]:
      errs.append(f"{path}: the ASPICE page stands on {phrase!r}, which is gone; update the figure")
  try:
    d = data(root)
    if len(d["base"]) > 24:
      errs.append(f"{M13}: {len(d['base'])} processes in §6; the baseline grid draws at most 24")
    if any(b[1].split("/")[0] not in ("0", "1") for b in d["base"]):
      errs.append(f"{M13}: a process is above level 1; add its colour to aspice-baseline.svg")
    if d["ias"] != [f"IA-{k}" for k in range(1, 16)]:
      errs.append(f"{M13}: the improvement actions are now {d['ias']}; aspice-plan.svg draws IA-1…IA-15, update it")
  except (ParseError, ValueError, IndexError, OSError) as e:
    errs.append(f"ASPICE records: {e}")
  return errs


def caps(tl, steps):
  out = []
  for i, (t0, cap) in enumerate(steps):
    t1 = steps[i + 1][0] - 0.2 if i + 1 < len(steps) else None
    out.append(g(f"{tl.show(t0, t1)} {'fin' if t1 is None else 'tr'}", [f'<rect x="24" y="66" width="{W - 48}" height="28" rx="6" fill="{NAVY}"/>', t(36, 85, cap, 13, "#fff", 600)]))
  return out


def card(x, y, w, h, tag, col, lines, fill="#fff", size=12.5):
  o = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{col}" stroke-width="2"/>', t(x + 14, y + 20, tag, 10 if len(tag) > 17 else 11, col, 700)]
  for i, line in enumerate(lines):
    o.append(t(x + 14, y + 42 + i * 18, line, size, NAVY, 600 if i == 0 else 400))
  return o


def chip(x, y, label, col, size=10.5, fg="#fff"):
  w = len(label) * 6.3 + 16
  return [f'<rect x="{x}" y="{y - 14}" width="{w:.0f}" height="20" rx="10" fill="{col}"/>', t(round(x + w / 2), y, label, size, fg, 700, "middle")], w


def topcar(x, y, col=BLUE, ang=0):
  return [f'<g transform="rotate({ang} {x} {y})"><rect x="{x - 11}" y="{y - 20}" width="22" height="40" rx="6" fill="#e8f0fb" stroke="{col}" stroke-width="2"/>',
          f'<rect x="{x - 8}" y="{y - 12}" width="16" height="9" rx="2" fill="{col}" opacity="0.35"/></g>']


def road(x, y, w, h):
  """Top-down two-lane highway section, driving up the page."""
  cx = x + w / 2
  return [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#eef0f3"/>',
          f'<line x1="{x + 14}" y1="{y}" x2="{x + 14}" y2="{y + h}" stroke="#fff" stroke-width="3"/>',
          f'<line x1="{x + w - 14}" y1="{y}" x2="{x + w - 14}" y2="{y + h}" stroke="#fff" stroke-width="3"/>',
          f'<line x1="{cx}" y1="{y}" x2="{cx}" y2="{y + h}" stroke="#fff" stroke-width="3" stroke-dasharray="14 12"/>']



# ------------------------------------------------------------------ 0 a different question
def question(d):
  tl, h = Timeline(30.0), 650
  b = [t(24, 38, "ASPICE asks a different question", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "The safety standards ask: is the product safe?"),
                 (3.4, "ASPICE asks: is the way you build it good enough to trust what comes out?"),
                 (8.6, "It rates each process on a capability level from 0 to 5"),
                 (19.0, "LionDriver's target: level 2 for the core processes, level 1 for the rest (T-12)"),
                 (24.6, "Today, from a self-assessment: almost everything at level 0")])
  # product vs process
  b.append(g(f"{tl.show(0.5)} fin", [f'<rect x="24" y="108" width="324" height="120" rx="12" fill="#fff" stroke="{FS}" stroke-width="2"/>',
                                     t(38, 132, "THE PRODUCT", 11.5, FS, 800), t(38, 156, "ISO 26262, ISO 21448, ISO/SAE 21434,", 12, NAVY, 600),
                                     t(38, 174, "ISO/PAS 8800", 12, NAVY, 600), t(38, 202, "Is this car function safe enough?", 12.5, FS, 700)]))
  b.append(g(f"{tl.show(3.6)} fin", [f'<rect x="372" y="108" width="324" height="120" rx="12" fill="#fff" stroke="{AS}" stroke-width="2"/>',
                                     t(386, 132, "THE PROCESS", 11.5, AS, 800), t(386, 156, "Automotive SPICE (ASPICE)", 12, NAVY, 600),
                                     t(386, 174, "requirements, design, test, change, release …", 12, NAVY, 600),
                                     t(386, 202, "Will the way you work keep it that way?", 12.5, AS, 700)]))
  # ladder
  levels = [(0, "Incomplete", "not done, or nothing to show for it"), (1, "Performed", "done, and its outputs exist"),
            (2, "Managed", "planned, tracked; outputs reviewed and controlled"), (3, "Established", "one defined process the whole project uses"),
            (4, "Predictable", "measured and kept within limits"), (5, "Innovating", "improved on purpose")]
  base = 560
  for i, (n, name, what) in enumerate(levels):
    y = base - i * 50
    w = 150 + i * 70
    b.append(g(f"{tl.show(8.8 + i * 1.4)} fin", [f'<rect x="24" y="{y - 40}" width="{w}" height="42" rx="6" fill="{AS}" opacity="{0.25 + i * 0.13:.2f}"/>',
                                                  t(38, y - 14, f"{n} · {name}", 13, "#fff" if i >= 2 else NAVY, 800), t(w + 36, y - 14, what, 12, NAVY)]))
  b.append(g(f"{tl.show(19.2)} fin", [f'<path d="M24,{base - 2 * 50 - 42} h{150 + 2 * 70}" stroke="{GRN}" stroke-width="4"/>',
                                      t(W - 24, base - 2 * 50 - 46, "target, core processes", 11.5, GRN, 700, "end"),
                                      f'<path d="M24,{base - 1 * 50 - 42} h{150 + 70}" stroke="{GRN}" stroke-width="3" stroke-dasharray="6 4"/>',
                                      t(W - 24, base - 1 * 50 - 46, "target, ML, hardware, security", 11.5, GRN, 700, "end")]))
  b.append(g(f"{tl.show(24.8)} fin", [f'<rect x="24" y="580" width="{W - 110}" height="56" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 602, f"At the 2026-10-14 baseline (WP-M-13): level 1 for {d['cl1']} processes ({d['cl1_split']} only for safety code), 0 elsewhere.", 12, NAVY, 700),
             t(40, 622, "A self-assessment, not a formal ASPICE assessment: no certified assessor yet.", 11.5, MID, 400, "start", True)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "ASPICE asks a different question (animated)",
             f"The safety standards ask whether the product is safe; ASPICE asks whether the way it is built can be trusted, rating each process on a capability level from 0 (incomplete) to 5 (innovating). LionDriver targets level 2 for the core processes and level 1 for ML, hardware and security; at the 2026-10-14 baseline {d['cl1']} processes are at level 1 ({d['cl1_split']} only for the safety code) and the rest at 0. This is a self-assessment, not a formal ASPICE assessment.", tl, b)


# ------------------------------------------------------------------ 1 the V
def vmodel():
  tl, h = Timeline(30.0), 660
  b = [t(24, 38, "The V: specify down, verify up", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "Left side: say what to build, from the whole car down to code"),
                 (7.6, "Right side: show each level does what its partner on the left said"),
                 (14.6, "Around the V: hardware, ML, security, support and management processes"),
                 (21.0, "Each process leaves work products; LionDriver's are in assurance/")])
  left = [("SYS.1", "Needs", "hazards, goals (WP-C-03)"), ("SYS.2", "System reqs", "FSR, TSR (WP-C-04, S-02)"), ("SYS.3", "Architecture", "WP-S-03"),
          ("SWE.1", "SW reqs", "SWSR (WP-W-02)"), ("SWE.2", "SW architecture", "WP-W-03"), ("SWE.3", "Design + code", "opendbc, panda")]
  right = [("SWE.4", "Unit tests", "safety tests, MISRA"), ("SWE.5", "SW integration", "process replay"), ("SWE.6", "SW verification", "on device"),
           ("SYS.4", "System integration", "HIL bench (D-04)"), ("SYS.5", "System verification", "WP-S-09"), ("VAL.1", "Validation", "WP-V-01, in the car")]
  bw, bh = 200, 46
  pts_l, pts_r = [], []
  for i, (pid, name, wp) in enumerate(left):
    x = 24 + i * 22
    y = 112 + i * 62
    pts_l.append((x, y))
    b.append(g(f"{tl.show(0.6 + i * 1.1)} fin", [f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="8" fill="#fff" stroke="{AS}" stroke-width="2"/>',
                                                  t(x + 10, y + 19, pid, 12, AS, 800), t(x + 60, y + 19, name, 12, NAVY, 700), t(x + 10, y + 37, wp, 11, MID)]))
  for i, (pid, name, wp) in enumerate(reversed(right)):
    pass
  for i, (pid, name, wp) in enumerate(right):
    j = 5 - i
    x = W - 24 - bw - j * 22
    y = 112 + j * 62
    b.append(g(f"{tl.show(7.8 + i * 1.1)} fin", [f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="8" fill="#fff" stroke="{AS}" stroke-width="2"/>',
                                                  t(x + 10, y + 19, pid, 12, AS, 800), t(x + 60, y + 19, name, 12, NAVY, 700), t(x + 10, y + 37, wp, 11, MID)]
               + [f'<line x1="{24 + j * 22 + bw}" y1="{y + bh / 2}" x2="{x}" y2="{y + bh / 2}" stroke="{AS}" stroke-width="1.5" stroke-dasharray="5 4" opacity="0.6"/>',
                  t((24 + j * 22 + bw + x) / 2, y + bh / 2 - 5, "verifies", 10, AS, 600, "middle")]))
  # around the V
  ay = 494
  groups = [("HWE.1–4", "hardware", NAVY), ("MLE.1–4", "machine learning", TEAL), ("SEC.1–4", "cybersecurity", "#be185d"),
            ("SUP.1, 8–11", "quality, config, problems, change, data", MID), ("MAN.3, 5, 7", "project, risk, security risk", MID)]
  x = 24
  for i, (pid, what, c) in enumerate(groups):
    w = max(len(pid), len(what) * 0.68) * 7.2 + 24
    b.append(g(f"{tl.show(14.8 + i * 0.8)} fin", [f'<rect x="{x:.0f}" y="{ay}" width="{w:.0f}" height="46" rx="8" fill="#fff" stroke="{c}" stroke-width="1.8"/>',
                                                   t(x + 10, ay + 19, pid, 12, c, 800), t(x + 10, ay + 36, what, 10.5, NAVY)]))
    x += w + 8
  b.append(g(f"{tl.show(21.2)} fin", [f'<rect x="24" y="560" width="{W - 110}" height="78" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 582, "The generated traceability map (WP-T-01) draws this V from the trace data:", 12, NAVY, 700),
             t(40, 602, "how many items each process holds and how many have a verification partner.", 12, NAVY),
             t(40, 622, "ASPICE 4.0 process names; the licensed process model has the base practices.", 11, MID, 400, "start", True)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "The V: specify down, verify up (animated)",
             "The ASPICE 4.0 V: SYS.1 to SWE.3 down the left, SWE.4 to VAL.1 up the right, each verifying its partner, with the LionDriver work product of each process; hardware, ML, security, support and management processes around it. The traceability map WP-T-01 draws this V from the trace data.", tl, b)


# ------------------------------------------------------------------ 2 how an assessor rates a process
def rating():
  tl, h = Timeline(32.0), 660
  b = [t(24, 38, "How an assessor rates a process", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "Example: SWE.4, software unit verification"),
                 (3.2, "1 · The assessor looks for evidence of each expected practice"),
                 (10.6, "2 · …and for what is missing"),
                 (16.0, "3 · The evidence gives a rating: N, P, L or F"),
                 (22.4, "4 · Level 2 needs more: the work is planned, tracked and its outputs controlled"),
                 (27.6, "Ratings of the 2026-10-14 baseline (WP-M-13 §4, §5)")])
  b.append(g(f"{tl.show(0.5)} fin", [f'<rect x="24" y="106" width="{W - 48}" height="40" rx="8" fill="#fff" stroke="{AS}" stroke-width="2"/>',
                                     t(38, 131, "SWE.4 purpose: show that each software unit does what its design says", 12.5, NAVY, 700)]))
  found = ["100 % line coverage gate on the safety code", "mutation testing in CI", "MISRA static analysis, sanitizers", "per-brand safety tests (test_toyota.py)"]
  missing = ["a verification strategy and specification", "branch or MC/DC coverage criteria", "results kept as records", "tests on the target, not only on a PC"]
  b.append(g(f"{tl.show(3.4)} fin", [t(24, 172, "FOUND", 11.5, GRN, 800)]))
  for i, f in enumerate(found):
    b.append(g(f"{tl.show(3.8 + i * 1.4)} fin", [t(24, 196 + i * 22, "✓ " + f, 12, NAVY, 600)]))
  b.append(g(f"{tl.show(10.8)} fin", [t(372, 172, "MISSING", 11.5, RED, 800)]))
  for i, f in enumerate(missing):
    b.append(g(f"{tl.show(11.2 + i * 1.0)} fin", [t(372, 196 + i * 22, "✗ " + f, 12, NAVY, 600)]))
  # NPLF scale
  sy, sx, sw = 316, 120, 560
  bands = [("N", 0, 15), ("P", 15, 50), ("L", 50, 85), ("F", 85, 100)]
  sc = [f'<rect x="{sx + a * sw / 100:.0f}" y="{sy}" width="{(e - a) * sw / 100:.0f}" height="30" fill="{AS}" opacity="{0.15 + k * 0.2:.2f}" stroke="#fff"/>' for k, (n, a, e) in enumerate(bands)]
  sc += [t(sx + (a + e) / 2 * sw / 100, sy + 20, f"{n} {a}–{e} %", 11.5, NAVY, 800, "middle") for n, a, e in bands]
  b.append(g(f"{tl.show(16.2)} fin", sc + [t(24, sy + 20, "rating", 12, NAVY, 700)]))
  b.append(g(f"{tl.show(17.6)} fin", [f'<path d="M{sx + 67.5 * sw / 100:.0f},{sy + 34} v18" stroke="{GRN}" stroke-width="3"/>',
                                      t(sx + 67.5 * sw / 100, sy + 66, "safety code: L → level 1", 12, GRN, 700, "middle"),
                                      f'<path d="M{sx + 32.5 * sw / 100:.0f},{sy + 34} v18" stroke="{AMBER}" stroke-width="3"/>',
                                      t(sx + 32.5 * sw / 100, sy + 66, "rest of openpilot: P → level 0", 12, "#8a5a12", 700, "middle")]))
  # level 2 attributes
  ly = 420
  b.append(g(f"{tl.show(22.6)} fin", [f'<rect x="24" y="{ly}" width="{W - 48}" height="96" rx="10" fill="#fff" stroke="{AS}" stroke-width="2"/>',
             t(38, ly + 22, "Level 2 = level 1 rated F, plus two more attributes rated L or F:", 12.5, NAVY, 700),
             t(38, ly + 46, "PA 2.1 performance management: objectives, plans, responsibilities, monitoring", 12, NAVY),
             t(38, ly + 66, "PA 2.2 work product management: content rules, review, control", 12, NAVY),
             t(38, ly + 86, "Every process in scope: N for both at the baseline.", 12, RED, 700)]))
  b.append(g(f"{tl.show(27.8)} fin", [f'<rect x="24" y="530" width="{W - 110}" height="108" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 552, "Since the baseline, evidence has moved (WP-M-13 §9): change records with impact", 12, NAVY),
             t(40, 572, "analysis, a risk register, forked submodules, safety tests in fork CI.", 12, NAVY),
             t(40, 592, "Re-rating is an assessment of its own, due at the next gate (G0).", 12, NAVY, 600),
             t(40, 616, "Ratings are indicative: a self-assessment cannot be quoted as an ASPICE result.", 11, MID, 400, "start", True)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "How an assessor rates a process (animated)",
             "SWE.4, software unit verification, as the example: evidence found (100 % line coverage gate on the safety code, mutation testing, MISRA, per-brand safety tests) and missing (a strategy and specification, branch or MC/DC criteria, retained results, tests on the target); the N/P/L/F scale, the safety code rated L (level 1) and the rest P (level 0); level 2 needs PA 2.1 and PA 2.2, rated N for every process at the baseline.", tl, b)



# ------------------------------------------------------------------ 3 the baseline
def baseline(d):
  tl, h = Timeline(30.0), 660
  b = [t(24, 38, "Where LionDriver stands", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "Every process in scope, its level today and its target (WP-M-13 §6)"),
                 (8.0, "Level 1 only where the work is done and leaves outputs: mostly the safety code"),
                 (14.0, "No process reaches level 2: nothing is planned, tracked or controlled as ASPICE asks"),
                 (20.0, "Evidence has moved since the baseline; the re-rating is due at the next gate")])
  cols = 4
  cw, ch = 164, 38
  for i, (p, cur, tgt, grp) in enumerate(d["base"]):
    x = 24 + (i % cols) * (cw + 8)
    y = 112 + (i // cols) * (ch + 8)
    c1 = cur.split("/")[0]
    fill = {"0": "#f6d6cf", "1": "#f6e3b4"}[c1]
    o = [f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="6" fill="{fill}" stroke="{AS if grp == "A" else (TEAL if grp == "B" else "#be185d")}" stroke-width="1.5"/>',
         t(x + 10, y + 24, p, 12.5, NAVY, 800), t(x + cw - 10, y + 24, f"{cur} → {tgt}", 12, NAVY, 700, "end")]
    b.append(g(f"{tl.show(0.6 + i * 0.25)} fin", o))
    if p in d["moved_rows"]:
      b.append(g(f"{tl.show(20.2)} fin", [f'<circle cx="{x + cw - 4}" cy="{y + 4}" r="6" fill="{GRN}" stroke="#fff" stroke-width="1.5"/>']))
  ly = 112 + 6 * (ch + 8) + 10
  b.append(g(f"{tl.show(7.0)} fin", [f'<rect x="24" y="{ly}" width="14" height="14" rx="3" fill="#f6d6cf"/>', t(44, ly + 12, "level 0 today", 11.5, NAVY),
                                     f'<rect x="150" y="{ly}" width="14" height="14" rx="3" fill="#f6e3b4"/>', t(170, ly + 12, "level 1 (1/0 = safety code / rest)", 11.5, NAVY),
                                     t(420, ly + 12, "border: group A (target 2), B or C (target 1)", 11.5, MID)]))
  b.append(g(f"{tl.show(20.4)} fin", [f'<circle cx="31" cy="{ly + 32}" r="6" fill="{GRN}"/>', t(44, ly + 36, "evidence has moved since the baseline (WP-M-13 §9)", 11.5, NAVY)]))
  b.append(g(f"{tl.show(14.2)} fin", [f'<rect x="24" y="{ly + 56}" width="{W - 110}" height="108" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, ly + 78, "Why nothing is at level 2 yet:", 12.5, NAVY, 700),
             t(40, ly + 100, "PA 2.1 and PA 2.2 are N everywhere: no process had plans, roles, monitoring", 12, NAVY),
             t(40, ly + 118, "or reviewed work products at the baseline. The assurance/ work products now", 12, NAVY),
             t(40, ly + 136, "describe that practice; the re-rating decides how much of it is performed.", 12, NAVY),
             t(40, ly + 156, "", 1)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "Where LionDriver stands (animated)",
             "Every process in scope of WP-M-13 with its capability level at the 2026-10-14 baseline and its target, marking where evidence has moved since; no process reaches level 2, because process planning and work-product control were rated N everywhere.", tl, b)


# ------------------------------------------------------------------ 4 traceability
def trace(d):
  tl, h = Timeline(30.0), 660
  b = [t(24, 38, "Traceability: every link both ways", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "Down the left: every requirement comes from a parent"),
                 (4.6, "Across the V: every requirement is checked by a test"),
                 (9.0, "Back: every test names a requirement that exists"),
                 (12.6, "The trace map counts both directions from the data (WP-T-01)"),
                 (23.4, "Still missing: links into the code and into test results")])
  chain = [("SG-01", "goal"), ("FSR-01.04", "what"), ("TSR-105", "how"), ("SWSR-105", "software")]
  for i, (cid, lab) in enumerate(chain):
    x = 40 + i * 130
    y = 108 + i * 34
    b.append(g(f"{tl.show(0.6 + i * 0.8)} fin", [f'<rect x="{x}" y="{y}" width="112" height="30" rx="6" fill="#fff" stroke="{AS}" stroke-width="2"/>',
                                                  t(x + 56, y + 20, cid, 12, NAVY, 800, "middle"), t(x + 56, y - 4, lab, 10, MID, 600, "middle")]
               + ([f'<path d="M{x - 18},{y - 19} l18,19" stroke="{AS}" stroke-width="2"/>'] if i else [])))
  b.append(g(f"{tl.show(4.8)} fin", [f'<rect x="580" y="236" width="116" height="30" rx="6" fill="#fff" stroke="{GRN}" stroke-width="2"/>',
                                     t(638, 256, "unit test case", 12, NAVY, 800, "middle"),
                                     f'<path d="M542,225 L580,250" stroke="{GRN}" stroke-width="2.5"/>', t(600, 222, "checks", 10.5, GRN, 700, "middle")]))
  b.append(g(f"{tl.show(9.2)} fin", [f'<path d="M600,266 C580,290 500,288 486,242" fill="none" stroke="{AS}" stroke-width="2" stroke-dasharray="5 4"/>',
                                     t(560, 292, "names SWSR-105", 10.5, AS, 700, "middle")]))
  # coverage bars
  rows = d["coverage"]
  y0 = 300
  for i, (kind, lab, n, den) in enumerate(rows):
    y = y0 + i * 30
    frac = n / den
    col = GRN if frac == 1 else (AMBER if frac >= 0.6 else RED)
    b.append(g(f"{tl.show(12.8 + i * 0.6)} fin", [t(24, y + 14, kind.upper(), 10, MID, 800), t(84, y + 14, lab, 12, NAVY, 600),
                                                   f'<rect x="380" y="{y + 2}" width="250" height="16" rx="4" fill="#f1f3f7"/>',
                                                   f'<rect x="380" y="{y + 2}" width="{250 * frac:.0f}" height="16" rx="4" fill="{col}"/>',
                                                   t(638, y + 15, f"{n}/{den}", 12, NAVY, 700)]))
  b.append(g(f"{tl.show(17.4)} fin", [t(24, y0 + 7 * 30 + 14, "BACK", 10, MID, 800), t(84, y0 + 7 * 30 + 14, "test cases naming an ID that does not exist", 12, NAVY, 600),
                                      t(638, y0 + 7 * 30 + 15, "none ✓" if d["unknown_none"] else "some ✗", 12, GRN if d["unknown_none"] else RED, 700)]))
  b.append(g(f"{tl.show(23.6)} fin", [f'<rect x="24" y="552" width="{W - 110}" height="90" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 574, "Not traced yet (WP-T-01 §7): no requirement tags in the code, and tests are", 12, NAVY),
             t(40, 594, "linked to requirements (links/verification.yaml) but no result is recorded.", 12, NAVY),
             t(40, 614, "A test that names a requirement is not yet a passed test.", 12, NAVY, 700),
             t(40, 632, "", 1)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "Traceability: every link both ways (animated)",
             "One chain from SG-01 to FSR-01.04, TSR-105 and SWSR-105 and a unit test that names it; the derivation and verification coverage of the ASPICE trace map, and the check that no test names an unknown ID. Not traced yet: requirement tags in the code and links from tests to results.", tl, b)


# ------------------------------------------------------------------ 5 ASPICE and ISO 26262
def together(d):
  tl, h = Timeline(30.0), 650
  b = [t(24, 38, "ASPICE and ISO 26262 together", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "ISO 26262 says which work products must exist, and how rigorous by ASIL"),
                 (4.4, "ASPICE says how well the process that makes them runs"),
                 (8.4, "Most activities line up: one piece of work serves both"),
                 (18.6, "Where they differ, both are needed"),
                 (24.0, "LionDriver keeps one process model for all of it (WP-P-11)")])
  pairs = [("Part 2 · management", "MAN.3, MAN.5, SUP.1"), ("Part 3 · concept", "SYS.1"), ("Part 4 · system", "SYS.2–SYS.5"),
           ("Part 5 · hardware", "HWE.1–HWE.4"), ("Part 6 · software", "SWE.1–SWE.6"), ("Part 8 · supporting", "SUP.8, SUP.9, SUP.10")]
  b.append(g(f"{tl.show(0.5)} fin", [t(150, 112, "ISO 26262", 13, FS, 800, "middle")]))
  b.append(g(f"{tl.show(4.6)} fin", [t(570, 112, "ASPICE", 13, AS, 800, "middle")]))
  for i, (l, r) in enumerate(pairs):
    y = 124 + i * 44
    b.append(g(f"{tl.show(0.8 + i * 0.5)} fin", [f'<rect x="24" y="{y}" width="252" height="34" rx="8" fill="#fff" stroke="{FS}" stroke-width="1.8"/>', t(38, y + 22, l, 12.5, NAVY, 700)]))
    b.append(g(f"{tl.show(4.8 + i * 0.5)} fin", [f'<rect x="444" y="{y}" width="252" height="34" rx="8" fill="#fff" stroke="{AS}" stroke-width="1.8"/>', t(458, y + 22, r, 12.5, NAVY, 700)]))
    b.append(g(f"{tl.show(8.6 + i * 0.5)} fin", [f'<path d="M276,{y + 17} H444" stroke="{LIGHT}" stroke-width="2.5"/>']))
  b.append(g(f"{tl.show(11.8)} fin", [f'<rect x="300" y="{124 + 4 * 44 - 4}" width="120" height="42" rx="8" fill="#f3f0fd" stroke="{AS}"/>',
                                      t(360, 124 + 4 * 44 + 14, "unit verification", 10.5, NAVY, 700, "middle"),
                                      t(360, 124 + 4 * 44 + 29, "WP-W-06", 10.5, AS, 800, "middle")]))
  diffs = [("Only ISO 26262", FS, ["ASIL-dependent methods (e.g. MC/DC at ASIL D)", "safety analyses: HARA, FMEA, FTA, DFA", "confirmation measures, the safety case"]),
           ("Only ASPICE", AS, ["capability levels and their rating", "planning and monitoring of every process (PA 2.1)", "work-product control and review (PA 2.2)"])]
  for i, (ttl, c, lines) in enumerate(diffs):
    x = 24 + i * 348
    b.append(g(f"{tl.show(18.8 + i * 1.0)} fin", [f'<rect x="{x}" y="398" width="324" height="98" rx="10" fill="#fff" stroke="{c}" stroke-width="2"/>',
                                                   t(x + 14, 420, ttl, 12.5, c, 800)] + [t(x + 14, 442 + k * 18, "• " + l_, 11.5, NAVY) for k, l_ in enumerate(lines)]))
  b.append(g(f"{tl.show(24.2)} fin", [f'<rect x="24" y="510" width="{W - 110}" height="120" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 532, "LionDriver: one integrated process model (assurance/process, WP-P-11)", 12.5, NAVY, 700),
             t(40, 554, f"{d['activities']} activities in discipline lanes, linked by the work products they make; each", 12, NAVY),
             t(40, 572, "work product's register row (WP-M-00) names the clauses of every standard it serves.", 12, NAVY),
             t(40, 596, "So a work product is written once and counted wherever it applies.", 12, AS, 700),
             t(40, 616, "ASPICE process names after ASPICE 4.0; no clause text is quoted.", 11, MID, 400, "start", True)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "ASPICE and ISO 26262 together (animated)",
             f"ISO 26262 Parts 2, 3, 4, 5, 6 and 8 beside the ASPICE processes they line up with, with unit verification (WP-W-06) serving both; what only ISO 26262 covers and what only ASPICE covers; LionDriver's single process model of {d['activities']} activities, whose work products name every standard they serve.", tl, b)


# ------------------------------------------------------------------ 6 improvement plan
def plan(d):
  tl, h = Timeline(30.0), 650
  b = [t(24, 38, "Getting to the target", 22, NAVY, 700)]
  b += caps(tl, [(0.3, f"{d['n_ia']} improvement actions, each tied to processes and work products (WP-M-13 §7)"),
                 (12.4, "The self-assessment is repeated at every gate"),
                 (18.4, "A formal assessment by a certified assessor comes before any public claim"),
                 (23.0, "Level 1: do the work and keep the outputs. Level 2: plan it, track it, review it")])
  ias = [("IA-1", "plans, roles, monitoring", "MAN.3, 5"), ("IA-2", "review criteria, recorded reviews", "PA 2.2, SUP.1"), ("IA-3", "configuration control, baselines", "SUP.8"),
         ("IA-4", "change requests with impact", "SUP.10"), ("IA-5", "problem and vulnerability intake", "SUP.9"), ("IA-6", "requirements with IDs, trace", "SYS.1, 2, SWE.1"),
         ("IA-7", "architecture, timing budgets", "SYS.3, SWE.2"), ("IA-8", "detailed design, MISRA records", "SWE.3"), ("IA-9", "unit verification spec, coverage", "SWE.4"),
         ("IA-10", "fork-owned replay references", "SWE.5"), ("IA-11", "HIL bench, on-device tests", "SYS.4, SWE.6"), ("IA-12", "system verification", "SYS.5"),
         ("IA-13", "ML requirements, model tests, data", "MLE, SUP.11"), ("IA-14", "HW requirements, COTS qualification", "HWE"), ("IA-15", "TARA-driven security work", "SEC")]
  moved = set(d["moved_ias"])
  cw = 216
  for i, (ia, what, procs) in enumerate(ias):
    x = 24 + (i % 3) * (cw + 8)
    y = 108 + (i // 3) * 54
    b.append(g(f"{tl.show(0.6 + i * 0.6)} fin", [f'<rect x="{x}" y="{y}" width="{cw}" height="46" rx="8" fill="#fff" stroke="{AS}" stroke-width="1.6"/>',
                                                  t(x + 10, y + 19, ia, 11.5, AS, 800), t(x + 54, y + 19, procs, 10.5, MID, 700),
                                                  t(x + 10, y + 37, what, 11.5, NAVY)]))
    if ia in moved:
      b.append(g(f"{tl.show(23.4)} fin", [f'<circle cx="{x + cw - 6}" cy="{y + 6}" r="6" fill="{GRN}" stroke="#fff" stroke-width="1.5"/>']))
  # gates timeline
  gy = 400
  b.append(g(f"{tl.show(12.6)} fin", [f'<line x1="60" y1="{gy}" x2="{W - 60}" y2="{gy}" stroke="{LIGHT}" stroke-width="4"/>']))
  for k in range(6):
    x = 60 + k * (W - 120) / 5
    b.append(g(f"{tl.show(12.8 + k * 0.6)} fin", [f'<circle cx="{x:.0f}" cy="{gy}" r="14" fill="{AS}"/>', t(x, gy + 5, f"G{k}", 11, "#fff", 800, "middle"),
                                                   t(x, gy + 32, "self-assess", 10, MID, 600, "middle")]))
  b.append(g(f"{tl.show(18.6)} fin", [f'<rect x="{W - 230}" y="{gy + 36}" width="200" height="22" rx="8" fill="{GRN}"/>',
                                      t(W - 130, gy + 51, "then a formal assessment (OI-1)", 11.5, "#fff", 700, "middle")]))
  b.append(g(f"{tl.show(23.2)} fin", [f'<rect x="24" y="464" width="{W - 110}" height="170" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 484, "What moves a process up", 12.5, NAVY, 700),
             t(40, 500, "0 → 1: the work is done for real and leaves outputs you can show", 12, NAVY),
             t(40, 518, "(e.g. unit tests with kept results, not only a CI tick).", 12, NAVY),
             t(40, 542, "1 → 2: the work is planned, someone owns it, progress is tracked,", 12, NAVY),
             t(40, 560, "and its outputs are reviewed against criteria and kept under control.", 12, NAVY),
             t(40, 586, "Since the baseline, change records, a risk register, forked submodules and", 12, AS, 600),
             t(40, 604, "safety tests in fork CI give evidence for " + ", ".join(d["moved_ias"]) + " (WP-M-13 §9).", 12, AS, 600),
             t(40, 624, "", 1)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "Getting to the target (animated)",
             f"The {d['n_ia']} improvement actions of WP-M-13 with their processes, those with new evidence marked; the self-assessment at every gate and a formal assessment before any public claim; what moves a process from level 0 to 1 and from 1 to 2.", tl, b)



def render(root: Path = ROOT) -> dict[str, str]:
  d = data(root)
  figs = (question(d), vmodel(), rating(), baseline(d), trace(d), together(d), plan(d))
  return dict(zip(NAMES, figs, strict=True))


def write_all(out: Path, root: Path = ROOT) -> None:
  out.mkdir(parents=True, exist_ok=True)
  for name, text in render(root).items():
    (out / name).write_text(text, encoding="utf-8")


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--out", type=Path, default=None, help="write the SVGs here")
  ap.add_argument("--check", action="store_true", help="fail if a record a figure stands on changed")
  args = ap.parse_args(argv)
  errs = problems()
  for e in errs:
    print(e, file=sys.stderr)
  if args.out is not None and not errs:
    write_all(args.out)
    print(f"wrote {len(NAMES)} animations to {args.out}")
  return 1 if errs else 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
