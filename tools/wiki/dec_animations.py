#!/usr/bin/env python3
"""Render the animated explainers of the wiki page "ASIL decomposition: what it is and what it isn't" as SVG.

  dec-idea.svg          one requirement met by one element, then by two independent elements B(C) + A(C);
  dec-myths.svg         five misreadings of decomposition, each struck through and corrected;
  dec-schemes.svg       the splits ISO 26262-9 allows, as bars that add up to the original ASIL;
  dec-independence.svg  what the fallback monitor E-07 must not share with the panda envelope (IR-01…IR-10);
  dec-liondriver.svg    LionDriver's decision: no decomposition today, the hardware-metric trigger and the four schemes.

The decision, the independence requirements and the scheme records are read from WP-A-01, the hardware-metric gap from
WP-H-04 OI-6, and the LionDriver ASIL notations from WP-S-02 §2.1. The allowed splits (SCHEMES) and the definitions are
those of ISO 26262-9:2018 clause 5, which is not in the repository; the page says so. Every phrase drawn from a record is
tied to it (SOURCES) and checked at render time (`problems()`). When a record changes, the wiki build fails instead of
showing old text. build_wiki.py renders them next to the pages at each sync; they loop with CSS and reduced motion shows
the final frame.

Usage: python3 tools/wiki/dec_animations.py [--out DIR] [--check]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from animations import GRN, MID, NAVY, RED, Timeline, g, norm, svg, t  # noqa: E402
from how_animations import ORANGE, QM_BG, box, caption, line  # noqa: E402

NAMES = ("dec-idea.svg", "dec-myths.svg", "dec-schemes.svg", "dec-independence.svg", "dec-liondriver.svg")
VIOLET = "#6250d6"
LEVEL = {"QM": 0, "A": 1, "B": 2, "C": 3, "D": 4}
LCOL = {"QM": "#9aa6bd", "A": "#3aa17e", "B": "#2a78d6", "C": "#c2410c", "D": "#9b1c1c"}

A = Path("assurance")
A01 = A / "08-analyses" / "WP-A-01-asil-decomposition.md"
H04 = A / "04-hardware" / "WP-H-04-hardware-metrics.md"
S02 = A / "03-system" / "WP-S-02-technical-safety-requirements.md"

# ISO 26262-9:2018 clause 5: the decompositions allowed per ASIL (standard text, not a repository record)
SCHEMES = [("D", [("C", "A"), ("B", "B"), ("D", "QM")]), ("C", [("B", "A"), ("C", "QM")]), ("B", [("A", "A"), ("B", "QM")]),
           ("A", [("A", "QM")])]
MYTHS = [("A way to lower the safety goal's ASIL", "The goal stays C. Only the elements' development rigour drops."),
         ("Half the job here, half the job there", "Each element meets the whole requirement on its own."),
         ("Two copies of the same thing", "Independent: no shared power, clock, code or inputs, shown by a dependent failure analysis."),
         ("Free", "Integration, verification and confirmation stay at C, and so do the hardware metrics."),
         ("What B‡ and QM (C-sup) mean", "Those are LionDriver notations, not decompositions (WP-S-02 §2.1).")]
# what the envelope shares on the comma device, and what each independence requirement gives E-07 instead (WP-A-01 §4.3)
SHARED = [("12 V supply and regulators", "IR-01", "own supply, or opens on losing it"), ("clock", "IR-02", "own clock"),
          ("circuit board", "IR-08", "own board in the harness box"), ("CAN path through the panda", "IR-03", "own CAN transceiver, listen-only"),
          ("opendbc code and limit tables", "IR-04", "own code and limits, set separately"), ("compiler and toolchain", "IR-05", "different toolchain"),
          ("reset and boot pins the SoC drives", "IR-06", "no command interface at all")]
IRS = tuple(f"IR-{i:02d}" for i in range(1, 11))
# the four candidate schemes of WP-A-01 §4.1 in plain words: (record, what, why)
CARDS = [("DEC-01", ("panda +", "independent monitor E-07"), ("the prepared fallback", "")),
         ("DEC-02", ("two software channels", "on one chip"), ("same die, clock, power", "")),
         ("DEC-03", ("panda + Toyota's", "steering limiter"), ("no evidence;", "checks the same command")),
         ("DEC-04", ("main computer", "+ panda"), ("makes the command", "it would check"))]

# (record, phrase a figure stands on)
SOURCES = [
  (A01, "ISO 26262-9 §5 allows decomposition only between sufficiently independent elements that each implement the safety requirement"),
  (A01, "hardened to **ASIL C** as a single, non-decomposed element"), (A01, "HARA v0.4 raises SG-02, SG-03 and SG-06 to ASIL C outright"),
  (A01, "| DEC-01 | C(C) = B(C) + A(C) |"), (A01, "E-07 is a concept, not a design."),
  (A01, "Integration, verification of the safety goal, confirmation measures and the DFA stay at ASIL C"),
  (A01, "evaluated at the level of the original ASIL C goal"), (A01, "This must be checked against the licensed text during review (OI-4)"),
  (A01, "Shares clock, power, memory, CAN peripheral"), (A01, "No development evidence"), (A01, "No independence of input"),
  (A01, "It cannot be shown independent of the failure it would monitor (it produces the command)"),
  (A01, "Using it as an external measure that supports a controllability rating is different from crediting it with a decomposed ASIL."),
  (A01, "shall de-energise the relay on loss of its own supply"), (A01, "E-07 shall use its own clock source"),
  (A01, "E-07 shall receive bus 0 through its own CAN transceiver and controller"), (A01, "E-07 shall share no source code"),
  (A01, "E-07 shall be compiled with a different toolchain"), (A01, "E-07 shall have no command interface in release builds"),
  (A01, "E-07 shall act through a de-energise-to-safe path"), (A01, "E-07 shall be physically separated from the comma device PCB"),
  (A01, "covered by a relay-state readback seen by both E-03 and E-07"),
  (A01, "E-07 limits shall be set from the controllability evidence (WP-C-04 OI-2), independently of the E-01 controller limits and the E-03 limits"),
  (A01, "so the stock camera reconnects to the vehicle"),
  (H04, "so the ASIL C SPFM target is **likely missed**"), (H04, "back to the lead (DQ-362)"),
  (S02, "| **B‡** | Target ASIL B under FSC option (c). **ASIL C applies until the HARA re-rates SG-01"),
  (S02, "| **QM (C-sup)**, **QM (B-sup)** | Allocated to the QM SoC. It supports an ASIL C (or B) FSR, but the ASIL argument rests on the named envelope TSR"),
]


def _read(root: Path, path: Path) -> str:
  return (root / path).read_text(encoding="utf-8")


def data(root: Path = ROOT) -> dict:
  a01, h04 = _read(root, A01), _read(root, H04)
  sec = a01.split("### 4.3", 1)[1].split("### 4.4", 1)[0]
  irs = re.findall(r"^\| (IR-\d+) \|", sec, re.M)
  sec7 = a01.split("## 7. Decomposition records", 1)[1].split("## 8.", 1)[0]
  recs = {m.group(1): m.group(2).replace("**", "").split(" (")[0] for m in
          re.finditer(r"^\| (DEC-\d+) \|[^|]*\|[^|]*\| ([^|]+?) \|", sec7, re.M)}
  m = re.search(r"SPFM ([0-9.]+) % on the shared generic-rate estimate, ([0-9.]+) points below ([0-9.]+) %", h04)
  rb = re.search(r"TSR-517 transmit read-back \(estimate ([0-9.]+) %", h04)
  if not m or not rb:
    raise ValueError(f"{H04} OI-6: the SPFM estimate or the TSR-517 read-back estimate is not found")
  return {"irs": irs, "recs": recs, "spfm": float(m.group(1)), "gap": float(m.group(2)), "target": float(m.group(3)),
          "readback": float(rb.group(1))}


def problems(root: Path = ROOT) -> list[str]:
  errs, cache = [], {}
  for path, phrase in SOURCES:
    if path not in cache:
      p = root / path
      cache[path] = norm(p.read_text(encoding="utf-8")) if p.exists() else ""
    if norm(phrase) not in cache[path]:
      errs.append(f"{path}: the ASIL decomposition page stands on {phrase!r}, which is gone; update the figure")
  try:
    d = data(root)
    if tuple(d["irs"]) != IRS:
      errs.append(f"{A01} §4.3: the independence requirements are now {d['irs']}; dec-independence.svg draws {IRS[0]}…{IRS[-1]}")
    if set(d["recs"]) != {c[0] for c in CARDS}:
      errs.append(f"{A01} §7: the decomposition records are now {sorted(d['recs'])}; dec-liondriver.svg draws {[c[0] for c in CARDS]}")
    if d["recs"].get("DEC-01") != "Proposed" or any(v == "Applied" for v in d["recs"].values()):
      errs.append(f"{A01} §7: a record changed status ({d['recs']}); the page says no decomposition is applied and DEC-01 is the fallback")
    if d["spfm"] >= d["target"] or round(d["target"] - d["spfm"], 2) != d["gap"]:
      errs.append(f"{H04} OI-6: SPFM {d['spfm']} % against {d['target']} %; dec-liondriver.svg says the target is likely missed")
  except (OSError, ValueError, IndexError) as e:
    errs.append(f"cannot read the records the ASIL decomposition page is drawn from: {e}")
  return errs


# ---------------------------------------------------------------- 1. the idea

def idea() -> str:
  L = 24.0
  tl = Timeline(L)
  b = [t(24, 36, "ASIL decomposition in one picture", 23, NAVY, 700),
       t(24, 58, "One safety requirement, met twice, by two elements that cannot fail together", 14, MID),
       box(200, 78, 320, 52, "#fff", NAVY, 10, 2), t(360, 100, "Safety requirement (ASIL C)", 14, NAVY, 700, "middle"),
       t(360, 118, "e.g. never pass a steering torque above the limit", 12, MID, 400, "middle")]
  b += [g(tl.show(0.4, 6.0) + " tr", [line(360, 130, 360, 170, NAVY, 2), box(270, 170, 180, 64, "#fff", LCOL["C"], 10, 2.4),
                                      t(360, 198, "one element", 14, NAVY, 700, "middle"),
                                      t(360, 218, "developed to ASIL C", 12.5, LCOL["C"], 700, "middle")])]
  b.append(caption(tl, 0.4, 6.0, "Without decomposition: one element carries the whole ASIL C.", 290))
  b += [g(tl.show(6.4) + " fin", [
    line(360, 130, 360, 150, NAVY, 2), line(180, 150, 540, 150, NAVY, 2), line(180, 150, 180, 170, NAVY, 2), line(540, 150, 540, 170, NAVY, 2),
    box(80, 170, 200, 64, "#fff", LCOL["B"], 10, 2.4), t(180, 198, "element 1", 14, NAVY, 700, "middle"), t(180, 218, "B(C)", 15, LCOL["B"], 700, "middle"),
    box(440, 170, 200, 64, "#fff", LCOL["A"], 10, 2.4), t(540, 198, "element 2", 14, NAVY, 700, "middle"), t(540, 218, "A(C)", 15, LCOL["A"], 700, "middle"),
    t(360, 206, "+", 26, NAVY, 700, "middle")])]
  b.append(caption(tl, 6.4, 11.4, "With it: two elements, each meeting the whole requirement on its own.", 290))
  b += [g(tl.show(11.8, 16.6) + " tr", [box(80, 170, 200, 64, "#fdecec", RED, 10, 2.4), t(180, 198, "element 1 fails", 14, RED, 700, "middle"),
                                        t(540, 160, "still catches it", 12.5, GRN, 700, "middle")]),
        g(tl.show(17.0, 22.6) + " tr", [box(440, 170, 200, 64, "#fdecec", RED, 10, 2.4), t(540, 198, "element 2 fails", 14, RED, 700, "middle"),
                                        t(180, 160, "still catches it", 12.5, GRN, 700, "middle")])]
  b.append(caption(tl, 11.8, 16.6, "If one fails, the other still keeps the requirement.", 290))
  b.append(caption(tl, 17.0, 22.6, "That only works if nothing can make both fail at once.", 290))
  b += [g(tl.show(11.8) + " fin", [
    t(24, 330, "How to read B(C):", 14, NAVY, 700),
    t(24, 352, "B   the ASIL the element is developed to: its process, methods and rigour", 13, NAVY),
    t(24, 372, "(C) the ASIL of the safety goal it serves, which never changes", 13, NAVY),
    t(24, 400, "The split lowers the development rigour of each element. It never lowers the goal.", 13, NAVY, 600),
    t(24, 428, "Source: ISO 26262-9:2018 clause 5; LionDriver's record is WP-A-01.", 11.5, MID)])]
  return svg(444, "ASIL decomposition in one picture",
             "One ASIL C requirement met by one ASIL C element, then by two independent elements B(C) and A(C) that each meet it "
             "alone, so that one failing is caught by the other.", tl, b)


# ---------------------------------------------------------------- 2. what it is not

def wrap(s: str, width: int) -> list[str]:
  lines = [""]
  for w in s.split():
    if lines[-1] and len(lines[-1]) + 1 + len(w) > width:
      lines.append(w)
    else:
      lines[-1] = f"{lines[-1]} {w}".strip()
  return lines


def myths() -> str:
  L = 22.0
  tl = Timeline(L)
  b = [t(24, 36, "What ASIL decomposition is not", 23, NAVY, 700),
       t(24, 58, "Five common misreadings, and what the standard actually asks", 14, MID),
       t(24, 92, "It is not…", 13, RED, 700), t(330, 92, "Instead…", 13, GRN, 700)]
  for i, (wrong, right) in enumerate(MYTHS):
    y, t0 = 124 + 56 * i, 0.6 + i * 3.4
    b += [g(tl.show(t0) + " fin", [t(24, y, "✗", 15, RED, 700), t(44, y, wrong, 13, NAVY, 600)]),
          g(tl.show(t0 + 1.2) + " fin", [line(42, y - 4.5, 46 + len(wrong) * 6.0, y - 4.5, RED, 1.8), t(310, y, "✓", 15, GRN, 700)]
            + [t(330, y + 18 * j, s, 13, NAVY) for j, s in enumerate(wrap(right, 50))])]
  b += [g(tl.show(18.0) + " fin", [
    t(24, 412, "B‡: target ASIL B, but ASIL C until the HARA re-rates SG-01. QM (C-sup): a QM function on the main", 12, MID),
    t(24, 428, "computer whose ASIL C argument rests on a panda requirement. Hardware metrics at the original ASIL: WP-A-01 §4.4", 12, MID),
    t(24, 444, "records this and asks for it to be checked against the licensed text (OI-4).", 12, MID)])]
  return svg(458, "What ASIL decomposition is not", "Five misreadings of ASIL decomposition, each struck through and corrected.", tl, b)


# ---------------------------------------------------------------- 3. the allowed splits

def schemes() -> str:
  L = 20.0
  tl = Timeline(L)
  b = [t(24, 36, "The splits the standard allows", 23, NAVY, 700),
       t(24, 58, "ISO 26262-9 §5: the two halves must add up to the original ASIL (counting QM 0, A 1, B 2, C 3, D 4)", 14, MID)]
  unit, xa, y, step = 56, 220, 96, 0.5
  for orig, splits in SCHEMES:
    b += [g(tl.show(step) + " fin", [t(24, y + 26, f"ASIL {orig}", 16, LCOL[orig], 700),
                                     f'<rect x="104" y="{y + 8}" width="{LEVEL[orig] * 18}" height="24" rx="4" fill="{LCOL[orig]}"/>'])]
    step += 0.6
    for a, c in splits:
      wa, wc = LEVEL[a] * unit, max(LEVEL[c] * unit, 16)
      xc = xa + wa + 18
      items = [f'<rect x="{xa}" y="{y + 8}" width="{wa}" height="24" rx="4" fill="{LCOL[a]}"/>',
               t(xa + wa / 2, y + 25, f"{a}({orig})", 12.5, "#fff", 700, "middle"), t(xa + wa + 9, y + 25, "+", 15, NAVY, 700, "middle"),
               f'<rect x="{xc}" y="{y + 8}" width="{wc}" height="24" rx="4" fill="{LCOL[c]}"/>']
      if c == "QM":
        items += [t(xc + wc + 6, y + 25, f"QM({orig})", 12.5, LCOL["QM"], 700), t(xc + wc + 64, y + 25, "one element carries it all", 12, MID)]
      else:
        items += [t(xc + wc / 2, y + 25, f"{c}({orig})", 12.5, "#fff", 700, "middle")]
      if (orig, a, c) == ("C", "B", "A"):
        items += [f'<rect x="{xa - 6}" y="{y + 2}" width="{wa + wc + 30}" height="36" rx="8" fill="none" stroke="{VIOLET}" stroke-width="2.2"/>',
                  t(xa + wa + wc + 36, y + 25, "LionDriver's fallback, DEC-01", 12.5, VIOLET, 700)]
      b += [g(tl.show(step) + " fin", items)]
      step += 0.6
      y += 40
    y += 12
  b += [g(tl.show(step + 0.4) + " fin", [
    t(24, y + 20, "The bar length is the ASIL. Every split keeps the total; none makes it smaller.", 13, NAVY, 600),
    t(24, y + 44, "Each element is developed to its own letter; the bracket keeps the goal's ASIL for everything else.", 12, MID)])]
  return svg(y + 60, "The splits the standard allows",
             "ASIL D, C, B and A with each decomposition ISO 26262-9 allows, drawn as bars that add up to the original ASIL; "
             "C(C) = B(C) + A(C) is LionDriver's fallback.", tl, b)


# ---------------------------------------------------------------- 4. independence

def independence(d: dict) -> str:
  L = 24.0
  tl = Timeline(L)
  b = [t(24, 36, "Independence: what the second element must not share", 23, NAVY, 700),
       t(24, 58, f"The fallback DEC-01 adds a monitor, E-07, beside the panda. {len(d['irs'])} rules say what it must not share.", 14, MID),
       box(24, 80, 250, 210, QM_BG, MID, 10, 1.4), t(149, 102, "E-03 panda envelope · B(C)", 13.5, NAVY, 700, "middle"),
       t(149, 120, "on the comma device, shares:", 12, MID, 400, "middle"),
       box(446, 80, 250, 210, "#f3f0fd", VIOLET, 10, 2, "6 4"), t(571, 102, "E-07 monitor · A(C)", 13.5, VIOLET, 700, "middle"),
       t(571, 120, "a concept: nothing is built", 12, MID, 400, "middle")]
  for i, (shared, ir, own) in enumerate(SHARED):
    y, t0 = 146 + 20 * i, 1.4 + i * 2.2
    b += [t(40, y, "• " + shared, 12, NAVY),
          g(tl.show(t0) + " fin", [line(274, y - 4, 446, y - 4, VIOLET, 1), t(360, y - 7, ir, 11, VIOLET, 700, "middle")]),
          g(tl.show(t0 + 0.6) + " fin", [t(462, y, "• " + own, 12, NAVY)])]
  b += [box(240, 314, 240, 50, "#fff", NAVY, 10, 1.6), t(360, 336, "harness relay E-05: shared", 13, NAVY, 700, "middle"),
        t(360, 354, "both read its state back (IR-09)", 11.5, MID, 400, "middle"),
        line(149, 290, 149, 339, MID, 1.5), line(149, 339, 240, 339, MID, 1.5), line(571, 290, 571, 339, VIOLET, 1.5),
        line(480, 339, 571, 339, VIOLET, 1.5)]
  b += [g(tl.show(17.4) + " fin", [
    t(24, 394, "E-07 acts only by opening the relay, so the stock camera takes over again (IR-07), and its limits are set from", 12.5, NAVY),
    t(24, 412, "the controllability evidence, never copied from the panda (IR-10). Identical constants would be a shared fault.", 12.5, NAVY),
    t(24, 438, "Why not two channels on the panda chip, or the main computer, or Toyota's own steering limiter?", 13, NAVY, 700),
    t(24, 456, "They share too much with the panda, or produce the command they would check (WP-A-01 §4.1, §5).", 12.5, NAVY),
    t(24, 480, f"Source: WP-A-01 §4.2–§4.3 ({d['irs'][0]}…{d['irs'][-1]}); the DFA that must show independence is WP-A-03.", 11.5, MID)])]
  return svg(496, "Independence: what the second element must not share",
             "What the panda envelope shares on the comma device, the independence requirements, and the own resources they give the "
             "concept monitor E-07; the relay stays shared.", tl, b)


# ---------------------------------------------------------------- 5. LionDriver's decision

def decision(d: dict) -> str:
  L = 24.0
  tl = Timeline(L)
  b = [t(24, 36, "LionDriver's decision", 23, NAVY, 700),
       t(24, 58, "No decomposition today. One fallback, ready if the panda cannot meet ASIL C on its own.", 14, MID),
       box(24, 78, 672, 52, "#fff", NAVY, 10, 1.6),
       t(360, 100, "SG-02, SG-03 and SG-06 are ASIL C, so the panda envelope must be ASIL C", 13.5, NAVY, 700, "middle"),
       t(360, 118, "The lead chose to harden it to ASIL C as one element (DQ-341)", 12, MID, 400, "middle")]
  b += [g(tl.show(0.8) + " fin", [line(360, 130, 360, 150, NAVY, 2), box(110, 150, 500, 50, "#fff", NAVY, 10, 1.6),
                                  t(360, 172, "Does it meet the ASIL C hardware metrics (WP-H-04)?", 13.5, NAVY, 700, "middle"),
                                  t(360, 190, f"Single-point fault metric today: {d['spfm']:g} % against {d['target']:g} % (generic-rate estimate)",
                                    12, MID, 400, "middle")])]
  b += [g(tl.show(2.6) + " fin", [line(250, 200, 160, 230, GRN, 2), box(24, 230, 296, 58, "#f1faf5", GRN, 10, 1.6),
                                  t(172, 254, "Yes → no decomposition", 13.5, GRN, 700, "middle"),
                                  t(172, 274, "the envelope stays one ASIL C element", 12, NAVY, 400, "middle")])]
  b += [g(tl.show(4.4) + " fin", [line(470, 200, 560, 230, ORANGE, 2), box(400, 230, 296, 58, "#fff6ec", ORANGE, 10, 1.6),
                                  t(548, 254, "No → back to the lead at G2", 13.5, ORANGE, 700, "middle"),
                                  t(548, 274, "DEC-01 is the prepared answer (DQ-362)", 12, NAVY, 400, "middle")])]
  b += [g(tl.show(6.2) + " fin", [
    t(24, 314, f"Today: {d['gap']:g} points short, \"likely missed\" (WP-H-04 OI-6). Routes to close it:", 13, ORANGE, 700),
    t(24, 332, f"the TSR-517 transmit read-back (estimate {d['readback']:g} %) and handbook failure rates.", 13, NAVY)])]
  for i, (k, what, why) in enumerate(CARDS):
    x, col = 24 + 170 * i, VIOLET if i == 0 else RED
    b += [g(tl.show(8.0 + i * 1.6) + " fin", [box(x, 348, 162, 112, "#fff", col, 10, 1.8), t(x + 12, 370, k, 13.5, col, 700),
                                              t(x + 12, 390, what[0], 11.5, NAVY), t(x + 12, 405, what[1], 11.5, NAVY),
                                              t(x + 12, 424, why[0], 11, MID), t(x + 12, 438, why[1], 11, MID),
                                              t(x + 12, 456, d["recs"][k], 11.5, col, 700)])]
  b += [g(tl.show(15.0) + " fin", [
    t(24, 484, "Source: WP-A-01 §2, §4.1 and §7; WP-H-04 OI-6. Toyota's limiter still counts as an external measure,", 11.5, MID),
    t(24, 500, "just not as half of a decomposition.", 11.5, MID)])]
  return svg(514, "LionDriver's decision",
             "The panda envelope is hardened to ASIL C with no decomposition; if the ASIL C hardware metrics are missed, the lead decides "
             "at G2 with DEC-01 as the prepared fallback; the other three schemes are rejected.", tl, b)


def render(root: Path = ROOT) -> dict[str, str]:
  d = data(root)
  return dict(zip(NAMES, (idea(), myths(), schemes(), independence(d), decision(d)), strict=True))


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
