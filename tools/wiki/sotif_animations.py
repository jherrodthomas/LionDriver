#!/usr/bin/env python3
"""Render the animated explainers of the wiki page "SOTIF and ISO 26262" as SVG.

  sotif-two-questions.svg  the same swerve from a fault (ISO 26262, HE-01.4, SG-01) and from a model error (SOTIF,
                           TC-05, FI-01, SH-01): one hazard log entry, two causes, two cures;
  sotif-who-owns.svg       two questions that send a cause to ISO 26262, to SOTIF or to both, with four real causes;
  sotif-triggering.svg     two chains of WP-C-06 (a performance and a specification insufficiency) and the count of
                           its evaluation outcomes;
  sotif-four-areas.svg     the four areas of ISO 21448 and how analysis, changes and exploration move situations;
  sotif-how-much.svg       from the acceptance criterion to a validation target, the driving it would take, and why
                           LionDriver splits it into scenarios (WP-V-02);
  sotif-unknowns.svg       the search for unknown scenarios, its triage and its stop rule (WP-V-04);
  sotif-one-chain.svg      one requirement (FSR-01.01, AC-02), one test and the two claims it supports.

Every ID, rating, status and number drawn is tied to a phrase of the record it comes from (SOURCES) and checked at
render time (`problems()`). The counts of WP-C-05 and WP-C-06 are computed from their tables by
assurance/02-concept/figures/fig_c05_four_areas.py, which also draws WP-C-05 Figure 2-1. When a record changes, the
wiki build fails instead of showing old text. build_wiki.py renders the figures next to the pages at each sync
(nothing is committed). They loop with CSS; reduced motion shows the final frame.

Usage: python3 tools/wiki/sotif_animations.py [--out DIR] [--check]
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from animations import GRN, LIGHT, MID, NAVY, RED, RED_BG, W, Timeline, g, norm, stick, svg, t  # noqa: E402

NAMES = ("sotif-two-questions.svg", "sotif-who-owns.svg", "sotif-triggering.svg", "sotif-four-areas.svg",
         "sotif-how-much.svg", "sotif-unknowns.svg", "sotif-one-chain.svg")
AMBER, BLUE, VIOLET, ORANGE, TEAL = "#b7791f", "#2a78d6", "#6250d6", "#c2410c", "#0f766e"
FS, SO, BOTH = BLUE, ORANGE, VIOLET          # ISO 26262 blue, ISO 21448 orange, both violet

FIG = Path("assurance") / "02-concept" / "figures"
C03 = Path("assurance") / "02-concept" / "WP-C-03-hara.md"
C04 = Path("assurance") / "02-concept" / "WP-C-04-functional-safety-concept.md"
C05 = Path("assurance") / "02-concept" / "WP-C-05-sotif-hazard-identification.md"
C06 = Path("assurance") / "02-concept" / "WP-C-06-sotif-insufficiencies-triggering-conditions.md"
C07 = Path("assurance") / "02-concept" / "WP-C-07-sotif-functional-modifications.md"
V01 = Path("assurance") / "06-validation" / "WP-V-01-safety-validation.md"
V02 = Path("assurance") / "06-validation" / "WP-V-02-sotif-vv-strategy.md"
V04 = Path("assurance") / "06-validation" / "WP-V-04-sotif-unknown-scenarios.md"
G1 = Path("assurance") / "case-records" / "claims" / "g1-functional-safety.yaml"
G2 = Path("assurance") / "case-records" / "claims" / "g2-sotif.yaml"
EV = Path("assurance") / "case-records" / "evidence" / "evidence.yaml"
TOYOTA = Path("opendbc_repo") / "opendbc" / "safety" / "modes" / "toyota.h"   # checked when the submodule is there

# (record, phrase a figure stands on)
SOURCES = [
  (C03, "| HE-01.4 | Torque while not engaged"), (C03, "Unexpected steering disturbance during manual driving | S3 | E4 | C2 ⚠ | **C** |"),
  (C03, "| H-01 | [WP-C-05](WP-C-05-sotif-hazard-identification.md) SH-01"), (C03, "| Hazard | SOTIF evaluation | TARA damage scenarios | FSC |"),
  (C05, "| SH-01 | Model-commanded steering moves the vehicle out of the lane"), (C05, "OS-21 (no markings) | S3 | C2 | HE-01.1–01.3"),
  (C05, "SH-02 under SG-02 (G2.8, a curve too tight for the torque limit). Decided 2026-10-18 by the project lead, decision register DQ-361 option A."),
  (C05, "| SH-12 | Prolonged unsupervised operation"), (C05, "Foreseeable misuse in both SOTIF and the HARA (decision register DQ-003"),
  (C05, "Exposure** is not used to compute an ASIL"), (C05, "| AC-02 | Every actuation produced by the intended function stays inside the envelope limits"),
  (C06, "| TC-05 | Faded, missing or doubled lane markings; tar seams"), (C06, "| FI-01 | P | Driving model | Lane/path estimate wrong"),
  (C06, "| TC-01 | Low sun in the camera field of view"), (C06, "| FI-02 | P | Driving model | Degraded perception"),
  (C06, "| TC-01, TC-02 | FI-02 | SH-01, SH-02, SH-06 | None specific; no uncertainty gating | Needs validation | Scenario tests (WP-V-03); FM-09 |"),
  (C06, "| TC-14 | Curve tighter than R_ODD at the travel speed"), (C06, "| FI-11 | S | Controller / EPS authority | Steering torque bounded"),
  (C06, "| TC-14 | FI-09, FI-11 | SH-02 | `steerSaturated` warning (`events.py:619`) | Needs modification (ODD bound + authority characterisation) | WP-C-02 §3.2; FM-10 |"),
  (C06, "| TC-04 | FI-02 | SH-01, SH-02, SH-06 | None | Needs modification (ODD exclusion + user info) |"),
  (C06, "| TC-09 | Lead vehicle changes lanes and reveals a stopped vehicle"), (C06, "| TC-35 | Lead hidden or not acquired in a curve"),
  (C06, "| TC-32 | Narrow lane"), (C06, "| TC-34 | Imminent collision in which the stock PCS would warn or brake"),
  (C06, "The driving model is a black box from LionDriver's point of view"),
  (C07, "| FM-09 | ML action plausibility and uncertainty monitor"), (C07, "| FM-10 | Reduced, speed-dependent lateral authority"),
  (V02, "| C. Match an injury-crash rate of ≈ 1 per 2 × 10⁶ mi | 5 × 10⁻⁷ /mi | ≈ 6 × 10⁶ mi"),
  (V02, "| A. Match US fatality rate (≈ 1.3 per 10⁸ vehicle-miles, all roads) | 1.3 × 10⁻⁸ /mi | ≈ 2.3 × 10⁸ mi"),
  (V02, "| D. Hazardous-behaviour rate for SH-01 with k = 0.1 of case C and P(harm \\| HB) = 0.01 (controllability 0.9 × harmful situation 0.1, both needing evidence) | 5 × 10⁻⁶ /mi | ≈ 6 × 10⁵ mi"),
  (V02, "| E. Per-scenario: stationary-lead approach, p_max = 1 % | — | 299 trials"), (V02, "| F. Per-scenario: p_max = 5 % | — | 59 trials"),
  (V02, "10⁴ – 2 × 10⁴ km engaged"), (V02, "LionDriver therefore **does not claim a rate-level demonstration**"),
  (V02, "1. the safety envelope bounding the magnitude of every hazardous behaviour"),
  (V02, "Zero occurrences in KS-07…KS-09 trials (≥ 59 per scenario)"), (V02, "decision register DQ-096 option B"),
  (V04, "| U-1 | Randomised long-tail driving"), (V04, "| U-2 | Disengagement and takeover analysis"), (V04, "| U-3 | Fleet-log mining"),
  (V04, "| U-4 | Adversarial and randomised simulation"), (V04, "| U-5 | Replay perturbation search"),
  (V04, "| U-6 | Reproduction on closed course"), (V04, "| U-7 | External information"),
  (V04, "| N | Nominal"), (V04, "| K | Instance of a known scenario"), (V04, "| U | New hazardous scenario"), (V04, "| F | Malfunction (E/E fault, software bug)"),
  (V04, "**Threshold: P̂₀ ≤ 0.10, with N ≥ 30** (DQ-262 A)"), (V04, "(decision register DQ-108, option A)"),
  (V04, "**Not yet executed.** No exploration block has been run. No LionDriver drive logs exist at the baseline."),
  (V04, "Two lateral rows matched no hazardous event"), (V04, "the HARA rates it as HE-01.6"),
  (C04, "| FSR-01.01 | The envelope shall limit the commanded LKA torque magnitude to a speed-dependent bound derived from driver controllability"),
  (C04, "Partial: fixed 1500 raw"), (C04, "not speed-dependent, no physical rationale (GAP-04)"),
  (V01, "| VS-VAL-10 | Worst-case lateral disturbance inside the envelope"), (V01, "at 30, 50, 70, 90 and 110 km/h"), (V01, "≥ 20/20 subjects"),
  (G1, "title: \"SG-01 lateral motion is met\""), (G2, "title: \"SOTIF (ISO 21448)\""),
  (EV, "Draft; controllability tests (CA-01…CA-07) not performed"),
]


def counts(root: Path = ROOT) -> dict:
  sys.path.insert(0, str(root / FIG))
  import fig_c05_four_areas as fa
  return fa.sotif_counts(root / C05, root / C06)


def problems(root: Path = ROOT) -> list[str]:
  errs, cache = [], {}
  for path, phrase in SOURCES:
    if path not in cache:
      p = root / path
      cache[path] = norm(p.read_text(encoding="utf-8")) if p.exists() else ""
    if norm(phrase) not in cache[path]:
      errs.append(f"{path}: the SOTIF page stands on {phrase!r}, which is gone; update the figure")
  if (root / TOYOTA).exists() and ".max_torque = 1500," not in (root / TOYOTA).read_text(encoding="utf-8"):
    errs.append(f"{TOYOTA}: the torque cap is no longer 1500 raw; update sotif-one-chain.svg")
  try:
    counts(root)
  except Exception as e:  # noqa: BLE001  a table that cannot be read is a build problem, whatever the cause
    errs.append(f"SOTIF counts: {e}")
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


# ------------------------------------------------------------------ 0 two questions
def two_questions():
  tl, h = Timeline(26.0), 600
  b = [t(24, 38, "Two questions about the same swerve", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "The car steers itself out of its lane. Why?"), (3.6, "ISO 26262 asks: what if something breaks?"),
                 (9.4, "ISO 21448 (SOTIF) asks: what if nothing breaks, but it still gets it wrong?"),
                 (15.6, "Same effect, one hazard log entry; different causes, so different cures"),
                 (21.0, "LionDriver needs both: openpilot rarely breaks, but it often misjudges")])
  # shared road at the top
  rx, ry, rw, rh = 300, 108, 120, 150
  b.append(g(f"{tl.show(0.4)} fin", road(rx, ry, rw, rh)))
  b.append(g(f"{tl.show(0.4, 2.0)} tr", topcar(rx + 90, ry + 118)))
  b.append(g(f"{tl.show(1.8)} fin", [f'<path d="M{rx + 90},{ry + 118} C{rx + 90},{ry + 70} {rx + 110},{ry + 50} {rx + 130},{ry + 8}" fill="none" stroke="{RED}" stroke-width="3" stroke-dasharray="6 5"/>']
                                     + topcar(rx + 122, ry + 30, RED, 22)))
  b.append(g(f"{tl.show(2.2)} fin", [t(rx + rw + 18, ry + 40, "Leaves its lane", 14, RED, 700), t(rx + rw + 18, ry + 60, "the vehicle-level effect", 11.5, MID),
                                     t(rx + rw + 18, ry + 80, "H-01 in the hazard log", 11.5, MID)]))
  # two columns
  cw, cy = 324, 290
  lx, rx2 = 24, W - 24 - cw

  def col(x, colr, title, q):
    return [f'<rect x="{x}" y="{cy}" width="{cw}" height="208" rx="12" fill="#fff" stroke="{colr}" stroke-width="2.2"/>',
            f'<rect x="{x}" y="{cy}" width="{cw}" height="30" rx="12" fill="{colr}"/>', f'<rect x="{x}" y="{cy + 18}" width="{cw}" height="12" fill="{colr}"/>',
            t(x + 14, cy + 21, title, 13, "#fff", 700), t(x + 14, cy + 52, q, 13, colr, 700)]
  b.append(g(f"{tl.show(3.8)} fin", col(lx, FS, "ISO 26262 · FUNCTIONAL SAFETY", "Something broke")))
  b.append(g(f"{tl.show(4.6)} fin", [  # chip with a fault
    f'<rect x="{lx + 16}" y="{cy + 68}" width="54" height="40" rx="5" fill="#f1f3f7" stroke="{NAVY}" stroke-width="1.6"/>',
    *[f'<line x1="{lx + 22 + i * 10}" y1="{cy + 108}" x2="{lx + 22 + i * 10}" y2="{cy + 115}" stroke="{NAVY}" stroke-width="1.6"/>' for i in range(5)],
    f'<path d="M{lx + 46},{cy + 72} l-9,15 h8 l-6,15 l14,-19 h-8 l6,-11 z" fill="{RED}"/>',
    t(lx + 84, cy + 82, "A software bug sends steering", 12.5, NAVY, 600), t(lx + 84, cy + 99, "torque while not engaged", 12.5, NAVY, 600)]))
  b.append(g(f"{tl.show(6.0)} fin", [t(lx + 16, cy + 140, "HE-01.4 · rated S3 · E4 · C2  →  ASIL C", 12.5, NAVY, 700),
                                     t(lx + 16, cy + 160, "Safety goal SG-01: no steering unless asked", 12, MID)]))
  b.append(g(f"{tl.show(7.4)} fin", [t(lx + 16, cy + 188, "Cure: detect and contain the fault", 12.5, FS, 700)]))
  b.append(g(f"{tl.show(9.6)} fin", col(rx2, SO, "ISO 21448 · SOTIF", "Nothing broke")))
  b.append(g(f"{tl.show(10.4)} fin", [  # faded line + tar seam
    f'<rect x="{rx2 + 16}" y="{cy + 66}" width="54" height="50" rx="5" fill="#eef0f3"/>',
    f'<line x1="{rx2 + 26}" y1="{cy + 66}" x2="{rx2 + 26}" y2="{cy + 116}" stroke="#fff" stroke-width="3" stroke-dasharray="3 9" opacity="0.6"/>',
    f'<path d="M{rx2 + 58},{cy + 116} C{rx2 + 50},{cy + 96} {rx2 + 40},{cy + 86} {rx2 + 34},{cy + 66}" fill="none" stroke="#3b3f47" stroke-width="2.4"/>',
    t(rx2 + 84, cy + 82, "Every part works as designed; the", 12.5, NAVY, 600), t(rx2 + 84, cy + 99, "model takes a tar seam for a line", 12.5, NAVY, 600)]))
  b.append(g(f"{tl.show(11.8)} fin", [t(rx2 + 16, cy + 140, "TC-05 → FI-01 → SH-01 · S3 · C2 · no ASIL", 12.5, NAVY, 700),
                                      t(rx2 + 16, cy + 160, "S and C reused from the HARA, same effect", 12, MID)]))
  b.append(g(f"{tl.show(13.2)} fin", [t(rx2 + 16, cy + 188, "Cure: improve, restrict or validate it", 12.5, SO, 700)]))
  # link
  b.append(g(f"{tl.show(15.8)} fin", [f'<path d="M{lx + cw / 2},{cy + 208} V512" stroke="{FS}" stroke-width="2.5"/>',
                                      f'<path d="M{rx2 + cw / 2},{cy + 208} V512" stroke="{SO}" stroke-width="2.5"/>']))
  b.append(g(f"{tl.show(17.0)} fin", [f'<rect x="24" y="512" width="{W - 110}" height="66" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
                                      t(40, 535, "One hazard log, two ways in. SH-01 is the SOTIF side of H-01 (WP-C-03 §7).", 12.5, NAVY, 700),
                                      t(40, 556, "Severity and controllability are rated once; only ISO 26262 turns them into an ASIL.", 12, MID)]))
  b.append(stick(W - 40, h - 22, "point"))
  return svg(h, "Two questions about the same swerve (animated)",
             "The car steers itself out of its lane (H-01). ISO 26262 asks what if something breaks: a software bug sends steering torque while not engaged, the hazardous event HE-01.4, rated S3, E4, C2, ASIL C, safety goal SG-01; the cure is to detect and contain the fault. ISO 21448 (SOTIF) asks what if nothing breaks: every part works as designed but the model takes a tar seam for a lane line, TC-05 to FI-01 to SH-01, S3 and C2 reused from the HARA, no ASIL; the cure is to improve, restrict or validate the function. Both are one entry of the shared hazard log.", tl, b)


# ------------------------------------------------------------------ 1 who owns it
def wrap2(txt, n=22):
  words, a = txt.split(), ""
  while words and len(a + " " + words[0]) <= n + 1:
    a = (a + " " + words.pop(0)).strip()
  return [a, " ".join(words)]


def who_owns():
  tl, h = Timeline(30.0), 600
  b = [t(24, 38, "Which standard handles this cause?", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "Sort each cause by asking two questions"), (3.4, "Cause 1: the panda firmware lets torque through while not engaged"),
                 (8.4, "Cause 2: the model takes a tar seam for a lane line"),
                 (13.4, "Cause 3: a curve tighter than the steering torque limit allows"),
                 (18.4, "Cause 4: the driver stops watching the road"),
                 (23.6, "Both sides write into one hazard log: H-0x and SH-0x share numbers")])
  # decision column
  qx, qw = 206, 308
  def diamond(y, txt1, txt2):
    return [f'<path d="M{qx + qw / 2},{y} L{qx + qw},{y + 34} L{qx + qw / 2},{y + 68} L{qx},{y + 34} z" fill="#fff" stroke="{NAVY}" stroke-width="2"/>',
            t(qx + qw / 2, y + 31, txt1, 11.5, NAVY, 700, "middle"), t(qx + qw / 2, y + 46, txt2, 11, NAVY, 600, "middle")]
  y1, y2 = 120, 230
  b.append(g(f"{tl.show(0.5)} fin", diamond(y1, "Did a part fail?", "hardware fault, software bug")
             + diamond(y2, "Does the function fall short,", "or is it misused?")
             + [f'<line x1="{qx + qw / 2}" y1="{y1 + 68}" x2="{qx + qw / 2}" y2="{y2}" stroke="{NAVY}" stroke-width="2"/>',
                t(qx + qw / 2 + 8, y1 + 90, "no", 11.5, MID, 700),
                f'<path d="M{qx + qw},{y1 + 34} H{W - 90} V{378}" fill="none" stroke="{NAVY}" stroke-width="2"/>', t(qx + qw + 10, y1 + 28, "yes", 11.5, MID, 700),
                f'<path d="M{qx},{y2 + 34} H90 V378" fill="none" stroke="{NAVY}" stroke-width="2"/>', t(qx - 30, y2 + 28, "yes", 11.5, MID, 700)]))
  # bins
  by, bh = 380, 130
  bins = [(24, SO, "ISO 21448 · SOTIF", "SH · FI · TC · no ASIL"), (250, BOTH, "BOTH", "analysed on each side"), (476, FS, "ISO 26262", "H · SG · ASIL")]
  bw = 220
  for x, c, ttl, sub in bins:
    b.append(g(f"{tl.show(0.8)} fin", [f'<rect x="{x}" y="{by}" width="{bw}" height="{bh}" rx="12" fill="#fff" stroke="{c}" stroke-width="2.2"/>',
                                        t(x + 14, by + 22, ttl, 13, c, 800), t(x + 14, by + 40, sub, 11, MID)]))
  b.append(g(f"{tl.show(0.8)} fin", [f'<line x1="{qx + qw / 2}" y1="{y2 + 68}" x2="{qx + qw / 2}" y2="{by}" stroke="{LIGHT}" stroke-width="2" stroke-dasharray="4 4"/>',
                                     t(qx + qw / 2 + 8, y2 + 92, "…and a safety goal covers it too", 11, MID, 600)]))
  causes = [
    (3.6, "panda passes torque while not engaged", 2, ["H-01 · SG-01 · ASIL C", "caught by the gate SM-04"], "fault"),
    (8.6, "model takes a tar seam for a line", 0, ["TC-05 → FI-01 → SH-01", "no part failed"], "sotif"),
    (13.6, "curve tighter than the torque limit", 1, ["SH-02 + SG-02 tree", "branch G2.8 [SOTIF], DQ-361"], "both"),
    (18.6, "driver stops watching the road", 1, ["misuse: SH-12 + HARA entry", "WP-C-08; DQ-003"], "both"),
  ]
  for i, (t0, txt, bi, lines, kind) in enumerate(causes):
    # incoming card at left
    b.append(g(f"{tl.show(t0, t0 + 4.6)} tr", card(24, 116, 172, 82, f"CAUSE {i + 1}", NAVY, wrap2(txt), size=12)))
    path_col = {"fault": FS, "sotif": SO, "both": BOTH}[kind]
    hl = []
    if kind == "fault":
      hl = [f'<path d="M{qx + qw},{y1 + 34} H{W - 90} V{by}" fill="none" stroke="{path_col}" stroke-width="4"/>']
    elif kind == "sotif":
      hl = [f'<line x1="{qx + qw / 2}" y1="{y1 + 68}" x2="{qx + qw / 2}" y2="{y2}" stroke="{path_col}" stroke-width="4"/>',
            f'<path d="M{qx},{y2 + 34} H90 V{by}" fill="none" stroke="{path_col}" stroke-width="4"/>']
    else:
      hl = [f'<line x1="{qx + qw / 2}" y1="{y1 + 68}" x2="{qx + qw / 2}" y2="{by}" stroke="{path_col}" stroke-width="4"/>']
    b.append(g(f"{tl.show(t0 + 1.0, t0 + 4.6)} tr", hl))
    x = bins[bi][0]
    slot = sum(1 for c in causes[:i] if c[2] == bi)
    yy = by + 58 + slot * 46
    b.append(g(f"{tl.show(t0 + 2.2)} fin", [f'<circle cx="{x + 22}" cy="{yy}" r="10" fill="{path_col}"/>', t(x + 22, yy + 4, str(i + 1), 11, "#fff", 800, "middle"),
                                             t(x + 40, yy + 4, lines[0], 11.5, NAVY, 700), t(x + 40, yy + 20, lines[1], 10.5, MID)]))
  b.append(g(f"{tl.show(23.8)} fin", [f'<rect x="24" y="524" width="{W - 110}" height="44" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
                                      t(40, 543, "An attack goes to ISO/SAE 21434 (the TARA), into the same log. Severity and", 12, NAVY, 600),
                                      t(40, 559, "controllability are rated once and reused; exposure gives an ASIL only on the 26262 side.", 12, NAVY, 600)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "Which standard handles this cause? (animated)",
             "Two questions sort a cause: did a part fail (a hardware fault or a software bug)? Then ISO 26262. Does the intended function fall short, or is it misused? Then ISO 21448 (SOTIF), and both when a safety goal covers it too. Four causes: the panda passing torque while not engaged goes to ISO 26262 (H-01, SG-01); the model taking a tar seam for a line goes to SOTIF (TC-05, FI-01, SH-01); a curve tighter than the torque limit goes to both (SH-02 and branch G2.8 of the SG-02 fault tree, DQ-361); the driver who stops watching goes to both (SH-12 and a rated HARA entry, DQ-003). An attack goes to ISO/SAE 21434, into the same hazard log.", tl, b)


# ------------------------------------------------------------------ 2 triggering conditions
def perspective(x, y, w, h, sun=False, curve=False, faded=False, cid="v"):
  """Driver's-eye view: sky, road to the horizon, lane lines."""
  hy = y + h * 0.42
  o = [f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/></clipPath><g clip-path="url(#{cid})">', f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#dfe8f4"/>',
       f'<rect x="{x}" y="{hy}" width="{w}" height="{y + h - hy}" fill="#c9d3c4"/>']
  vx = x + w / 2 + (40 if curve else 0)
  if curve:
    o += [f'<path d="M{x + 20},{y + h} C{x + 60},{hy + 30} {x + w - 30},{hy + 30} {x + w},{hy + 8} L{x + w},{hy + 22} C{x + w - 20},{hy + 50} {x + w - 40},{hy + 70} {x + w - 20},{y + h} z" fill="#8a919c"/>',
          f'<path d="M{x + 46},{y + h} C{x + 80},{hy + 34} {x + w - 30},{hy + 34} {x + w},{hy + 12}" fill="none" stroke="#fff" stroke-width="2.4"/>',
          f'<path d="M{x + w - 44},{y + h} C{x + w - 60},{hy + 60} {x + w - 20},{hy + 40} {x + w},{hy + 18}" fill="none" stroke="#fff" stroke-width="2.4"/>']
  else:
    o += [f'<path d="M{x + 20},{y + h} L{vx - 6},{hy} L{vx + 6},{hy} L{x + w - 20},{y + h} z" fill="#8a919c"/>']
    op = "0.35" if faded else "1"
    o += [f'<line x1="{x + 44}" y1="{y + h}" x2="{vx - 4}" y2="{hy}" stroke="#fff" stroke-width="2.4" opacity="{op}"/>',
          f'<line x1="{x + w - 44}" y1="{y + h}" x2="{vx + 4}" y2="{hy}" stroke="#fff" stroke-width="2.4" opacity="{op}"/>']
  if sun:
    o += [f'<circle cx="{vx + 4}" cy="{hy - 8}" r="70" fill="#fff6c9" opacity="0.75"/>', f'<circle cx="{vx + 4}" cy="{hy - 8}" r="20" fill="#ffe27a"/>',
          f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#fff8d8" opacity="0.35"/>']
  return o + ['</g>']


def triggering(cnt):
  tl, h = Timeline(30.0), 620
  b = [t(24, 38, "How a working system still gets it wrong", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "A triggering condition: something in the world the function cannot cope with"),
                 (3.6, "It exposes a functional insufficiency: here, performance (the camera model)"),
                 (6.6, "…which leads to hazardous behaviour, harmful only if the driver does not step in"),
                 (10.0, "Each chain is evaluated: is today's response good enough?"),
                 (14.0, "Second kind: the specification itself falls short"),
                 (24.0, f"WP-C-06: {cnt['tc']} triggering conditions, {cnt['fi']} insufficiencies, each chain evaluated")])
  sx, sy, sw, sh = 24, 108, 180, 150

  def chain(t0, scene, tc, fi, fi_kind, sh_, outcome, ocol, action, t_out):
    o = []
    o.append(g(f"{tl.show(t0, t_out)} {'tr' if t_out else 'fin'}", scene))
    bx = [222, 386, 550]
    boxes = [("TRIGGERING CONDITION", BLUE, tc), (f"INSUFFICIENCY · {fi_kind}", VIOLET, fi), ("HAZARDOUS BEHAVIOUR", RED, sh_)]
    for k, ((tag, c, lines), x) in enumerate(zip(boxes, bx)):
      ts = t0 + [0.2, 3.2, 6.4][k] if t0 < 12 else t0 + [0.2, 1.4, 2.6][k]
      o.append(g(f"{tl.show(ts, t_out)} {'tr' if t_out else 'fin'}", card(x, sy, 146, sh, tag, c, lines, size=11.5)
                 + ([f'<path d="M{x - 14},{sy + sh / 2} h10" stroke="{NAVY}" stroke-width="2"/><path d="M{x - 6},{sy + sh / 2 - 5} l6,5 l-6,5" fill="none" stroke="{NAVY}" stroke-width="2"/>'] if k else
                    [f'<path d="M{x - 14},{sy + sh / 2} h10" stroke="{NAVY}" stroke-width="2"/>'])))
    te = t0 + (10.2 if t0 < 12 else 4.0)
    ch, w = chip(124, 301, outcome, ocol, 11)
    o.append(g(f"{tl.show(te, t_out)} {'tr' if t_out else 'fin'}", [f'<rect x="24" y="272" width="{W - 48}" height="76" rx="10" fill="#fff" stroke="{LIGHT}"/>',
                                            t(40, 300, "Evaluation:", 12.5, NAVY, 700)] + ch
               + [t(40, 326, action, 12, NAVY), t(40, 342, "", 1)]))
    return o

  sun_scene = perspective(sx, sy, sw, sh, sun=True, faded=True, cid='v1') + [t(sx + 10, sy + sh - 10, "low sun ahead", 11, NAVY, 700)]
  b += chain(0.4, sun_scene, ["TC-01", "Low sun in the", "camera's view;", "glare on a wet road"],
             ["FI-02 · performance", "Perception degrades", "in glare, rain, fog,", "low light"], "P",
             ["SH-01 · SH-02", "Steers on a wrong", "path or drifts out", "S3 · C2"],
             "needs validation", AMBER, "No specific response today. Scenario tests (WP-V-03); FM-09, an uncertainty monitor, proposed.", 13.6)
  curve_scene = perspective(sx, sy, sw, sh, curve=True, cid='v2') + [t(sx + 10, sy + sh - 10, "curve tighter than R_ODD", 11, NAVY, 700)]
  b += chain(14.2, curve_scene, ["TC-14", "Curve tighter than", "the ODD radius at", "the travel speed"],
             ["FI-11 · specification", "Steering torque is", "capped; not enough", "for sharp curves"], "S",
             ["SH-02", "Drifts out of the", "curve, a warning", "only · S3 · C2"],
             "needs modification", RED, "Warning only (steerSaturated). Bound the ODD; FM-10, speed-dependent lateral authority.", None)
  # S vs P explainer, stays
  b.append(g(f"{tl.show(14.4)} fin", [t(24, 380, "P · performance: the design is right, a part is not good enough here (a camera in glare).", 12, NAVY, 600),
                                      t(24, 398, "S · specification: the design itself is wrong here (a torque cap too low for this curve).", 12, NAVY, 600)]))
  # tally
  ty = 430
  b.append(g(f"{tl.show(24.2)} fin", [f'<rect x="24" y="{ty}" width="{W - 48}" height="150" rx="12" fill="#eef2f8" stroke="{NAVY}"/>',
                                      t(40, ty + 26, "LionDriver today (WP-C-06 §5)", 14, NAVY, 700)]))
  bars = [("needs modification", cnt["mod"], RED), ("needs validation", cnt["val"], AMBER), ("acceptable, with a condition", cnt["acc"], GRN)]
  unit = 330 / max(n for _, n, _ in bars)
  for i, (lab, n, c) in enumerate(bars):
    b.append(g(f"{tl.show(24.6 + i * 0.5)} fin", [f'<rect x="230" y="{ty + 44 + i * 30}" width="{n * unit:.0f}" height="20" rx="4" fill="{c}"/>',
                                                   t(222, ty + 59 + i * 30, lab, 12, NAVY, 600, "end"), t(236 + n * unit, ty + 59 + i * 30, str(n), 12, NAVY, 700)]))
  b.append(g(f"{tl.show(26.2)} fin", [t(40, ty + 138, "No chain is closed by evidence yet: 'needs validation' waits on the WP-V-03 scenario tests.", 11.5, MID, 400, "start", True)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "How a working system still gets it wrong (animated)",
             f"Two chains of WP-C-06. Low sun in the camera view (TC-01) exposes a performance insufficiency, degraded perception (FI-02), leading to SH-01 or SH-02; evaluated: needs validation, scenario tests and the proposed FM-09. A curve tighter than the ODD radius (TC-14) exposes a specification insufficiency, the steering torque cap (FI-11), leading to SH-02; evaluated: needs modification, ODD bound and FM-10. WP-C-06 lists {cnt['tc']} triggering conditions and {cnt['fi']} insufficiencies; its {cnt['rows']} evaluation rows: {cnt['mod']} need modification, {cnt['val']} need validation, {cnt['acc']} acceptable with a condition.", tl, b)


# ------------------------------------------------------------------ 3 four areas
def four_areas(cnt):
  tl, h = Timeline(30.0), 640
  b = [t(24, 38, "The goal of SOTIF: shrink what is unsafe", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "Every driving situation is known or unknown to us, and safe or hazardous"),
                 (4.0, "Analysis finds hazardous situations: unknown → known (WP-C-05, WP-C-06)"),
                 (10.0, "Changes make known ones safe: modify, restrict the ODD, inform (WP-C-07)"),
                 (16.0, "Exploration hunts the rest: unknown → known (WP-V-04, AC-07)"),
                 (22.0, "Done when areas 2 and 3 are small enough to meet the acceptance criteria")])
  gx, gy, cw, ch = 110, 136, 290, 170
  cells = {1: (gx, gy + ch + 12, "1 · Known, not hazardous", GRN, "#eef8f2"), 2: (gx, gy, "2 · Known, hazardous", ORANGE, "#fff4ec"),
           3: (gx + cw + 12, gy, "3 · Unknown, hazardous", RED, RED_BG), 4: (gx + cw + 12, gy + ch + 12, "4 · Unknown, not hazardous", MID, "#f4f5f8")}
  base = [t(gx + cw / 2, gy - 10, "KNOWN", 11, MID, 800, "middle"), t(gx + cw * 1.5 + 12, gy - 10, "UNKNOWN", 11, MID, 800, "middle"),
          t(gx - 12, gy + ch / 2, "HAZARDOUS", 11, MID, 800, "end"), t(gx - 12, gy + ch * 1.5 + 12, "NOT", 11, MID, 800, "end"),
          t(gx - 12, gy + ch * 1.5 + 26, "HAZARDOUS", 11, MID, 800, "end")]
  for k, (x, y, lab, c, fill) in cells.items():
    dash = ' stroke-dasharray="6 4"' if k in (3, 4) else ""
    base += [f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="12" fill="{fill}" stroke="{c}" stroke-width="2"{dash}/>', t(x + 12, y + 22, lab, 13, c, 800)]
  b.append(g(f"{tl.show(0.5)} fin", base))

  def dot(x, y, c, label="", r=7):
    o = [f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}"/>']
    if label:
      o.append(t(x + 12, y + 4, label, 11, NAVY, 600))
    return o
  # unknown hazardous scenarios: start in area 3
  a3 = [(gx + cw + 40, gy + 52, "glare (TC-01)"), (gx + cw + 40, gy + 80, "tar seam (TC-05)"), (gx + cw + 40, gy + 108, "cut-out (TC-09)"),
        (gx + cw + 40, gy + 136, "fog (TC-04)"), (gx + cw + 180, gy + 70, ""), (gx + cw + 200, gy + 100, ""), (gx + cw + 230, gy + 130, ""),
        (gx + cw + 180, gy + 140, ""), (gx + cw + 240, gy + 60, ""), (gx + cw + 210, gy + 155, "")]
  a2 = [(gx + 30, gy + 52), (gx + 30, gy + 80), (gx + 30, gy + 108), (gx + 30, gy + 136)]
  # phase 0: all in area 3; phase 1: first four moved to area 2
  for i, (x, y, lab) in enumerate(a3):
    t_out = 5.0 if i < 4 else (17.0 if i < 7 else None)
    b.append(g(f"{tl.show(1.4 + i * 0.1, t_out)} {'tr' if t_out else 'fin'}", dot(x, y, RED, lab if i < 4 else "")))
  for i, (x, y) in enumerate(a2):
    lab = a3[i][2]
    t_out = 11.0 if i == 3 else None
    b.append(g(f"{tl.show(5.4 + i * 0.3, t_out)} {'tr' if t_out else 'fin'}", dot(x, y, ORANGE, lab)))
  b.append(g(f"{tl.show(5.0, 9.6)} tr", [f'<path d="M{gx + cw + 8},{gy + 95} h-6" stroke="{NAVY}" stroke-width="2"/>',
                                         f'<rect x="{gx + cw - 30}" y="{gy + 80}" width="70" height="26" rx="13" fill="{NAVY}"/>', t(gx + cw + 5, gy + 98, "analyse", 11.5, "#fff", 700, "middle")]))
  # phase 2: fog excluded from ODD → area 1
  b.append(g(f"{tl.show(10.4, 15.6)} tr", [f'<rect x="{gx + 110}" y="{gy + ch - 8}" width="70" height="26" rx="13" fill="{NAVY}"/>',
                                            t(gx + 145, gy + ch + 10, "change", 11.5, "#fff", 700, "middle")]))
  b.append(g(f"{tl.show(11.2)} fin", dot(gx + 30, gy + ch + 60, GRN, "fog: outside the ODD + user info")))
  b.append(g(f"{tl.show(12.2)} fin", [t(gx + 30, gy + ch + 92, "other rows: proposed, not yet built", 11, MID, 400, "start", True)]))
  # phase 3: exploration finds three more
  b.append(g(f"{tl.show(16.2, 21.6)} tr", [f'<rect x="{gx + cw - 30}" y="{gy + 110}" width="70" height="26" rx="13" fill="{NAVY}"/>',
                                            t(gx + cw + 5, gy + 128, "explore", 11.5, "#fff", 700, "middle")]))
  for i, (lab) in enumerate(["hidden lead (TC-35)", "narrow lane (TC-32)", "stock PCS (TC-34)"]):
    b.append(g(f"{tl.show(17.4 + i * 0.6)} fin", dot(gx + 160, gy + 52 + i * 28, ORANGE, lab)))
  b.append(g(f"{tl.show(18.8)} fin", [t(gx + 14, gy + ch - 12, "right column found later: RR-2026-011, WP-V-03", 10.5, MID, 400, "start", True)]))
  b.append(g(f"{tl.show(22.4)} fin", [t(gx + cw + 24, gy + 44, "what is left here is not estimated", 10.5, RED, 400, "start", True)]))
  # today panel
  py = 500
  b.append(g(f"{tl.show(22.2)} fin", [f'<rect x="24" y="{py}" width="{W - 110}" height="118" rx="12" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, py + 24, "LionDriver today (WP-C-05 Figure 2-1)", 14, NAVY, 700),
             t(40, py + 46, f"Area 2: {cnt['sh']} SOTIF hazards, {cnt['fi']} insufficiencies, {cnt['tc']} triggering conditions, each evaluated.", 12, NAVY),
             t(40, py + 64, "Area 3: large. The driving model is a black box (GAP-22); its size is not estimated.", 12, NAVY),
             t(40, py + 82, "Area 1: nothing there by evidence yet; every 'acceptable' carries a condition.", 12, NAVY),
             t(40, py + 104, "Area 4 is harmless by definition, so SOTIF does not work on it.", 11.5, MID, 400, "start", True)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "The goal of SOTIF: shrink what is unsafe (animated)",
             f"The four areas of ISO 21448: known or unknown, hazardous or not. Analysis moves hazardous situations from unknown to known (glare, tar seam, cut-out, fog); changes make known ones safe (fog: outside the ODD with user information); exploration finds more (a hidden lead in a curve, a narrow lane, the stock PCS interplay). Today: area 2 holds {cnt['sh']} SOTIF hazards, {cnt['fi']} insufficiencies and {cnt['tc']} triggering conditions; area 3 is large and not estimated, the driving model being a black box; area 1 has nothing by evidence yet.", tl, b)


# ------------------------------------------------------------------ 4 how much driving
def how_much():
  tl, h = Timeline(32.0), 660
  b = [t(24, 38, "How much driving would prove it?", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "Acceptance criterion: no worse than a human driving the stock car (WP-C-05 §5)"),
                 (3.4, "Turn it into a rate of wrong moves we may allow (WP-V-02 §3)"),
                 (11.6, "Zero failures at 95 % confidence needs about 3 ÷ that rate"),
                 (15.6, "LionDriver drives 10 000–20 000 km a year: about 50 times too few"),
                 (20.6, "So split it into scenarios, each tested many times"),
                 (27.0, "The targets are proposals until the lead freezes them")])
  # derivation steps
  steps = [(3.6, "Human injury crash", "≈ 1 per 2 million miles", "US data; illustrative until OI-2"),
           (5.4, "× share for SOTIF hazards", "k = 0.1", "the rest of the risk budget goes elsewhere"),
           (7.2, "÷ chance a wrong move hurts", "P(harm | HB) = 0.01", "driver catches 90 % · harmful situation 10 %"),
           (9.0, "= wrong lane departures allowed", "≤ 5 × 10⁻⁶ per mile", "VT-01, case D")]
  for i, (t0, a, v, n) in enumerate(steps):
    y = 112 + i * 50
    col = SO if i == 3 else NAVY
    b.append(g(f"{tl.show(t0)} fin", [f'<rect x="24" y="{y}" width="{W - 48}" height="42" rx="8" fill="{"#fff4ec" if i == 3 else "#fff"}" stroke="{col if i == 3 else LIGHT}" stroke-width="{2 if i == 3 else 1}"/>',
                                       t(40, y + 26, a, 13, NAVY, 600), t(300, y + 26, v, 14, col, 800), t(W - 40, y + 26, n, 11, MID, 400, "end", True)]))
  # log chart
  cy, x0, x1 = 340, 196, 690
  lo, hi = 3, 9
  def X(miles):
    return x0 + (math.log10(miles) - lo) / (hi - lo) * (x1 - x0)
  axis = [f'<line x1="{x0}" y1="{cy + 150}" x2="{x1}" y2="{cy + 150}" stroke="{NAVY}" stroke-width="1.5"/>']
  for e in range(lo, hi + 1):
    axis += [f'<line x1="{X(10 ** e):.0f}" y1="{cy + 150}" x2="{X(10 ** e):.0f}" y2="{cy + 156}" stroke="{NAVY}"/>',
             t(X(10 ** e), cy + 170, f"10{'⁰¹²³⁴⁵⁶⁷⁸⁹'[e]}", 11, MID, 600, "middle")]
  axis += [t(x1, cy + 186, "miles of engaged driving", 11, MID, 400, "end", True), t(24, cy - 2, "Miles needed with no failure, 95 % confidence", 13, NAVY, 700)]
  b.append(g(f"{tl.show(11.8)} fin", axis))
  bars = [(12.0, "wrong lane departures (D)", 6e5, SO), (12.6, "injury crashes (C)", 6e6, NAVY), (13.2, "fatal crashes (A)", 2.3e8, NAVY)]
  for i, (t0, lab, m, c) in enumerate(bars):
    y = cy + 30 + i * 32
    b.append(g(f"{tl.show(t0)} fin", [t(x0 - 8, y + 15, lab, 11.5, NAVY, 600, "end"),
                                       f'<rect x="{x0}" y="{y}" width="{X(m) - x0:.0f}" height="20" rx="4" fill="{c}" opacity="{1 if c == SO else 0.35}"/>',
                                       t(X(m) + 6, y + 15, f"{m:.1g}".replace("e+0", " × 10")[:-1] + "⁰¹²³⁴⁵⁶⁷⁸⁹"[int(f"{m:.1g}"[-1])], 11, NAVY, 700)]))
  # capacity band 10^4..2e4 km = 6.2e3..1.24e4 mi
  b.append(g(f"{tl.show(15.8)} fin", [f'<rect x="{X(6.2e3):.0f}" y="{cy + 22}" width="{X(1.24e4) - X(6.2e3):.0f}" height="128" fill="{GRN}" opacity="0.22"/>',
                                      f'<line x1="{X(1.24e4):.0f}" y1="{cy + 22}" x2="{X(1.24e4):.0f}" y2="{cy + 150}" stroke="{GRN}" stroke-width="2"/>',
                                      t(X(6.2e3) - 4, cy + 128, "LionDriver,", 10.5, GRN, 700, "end"), t(X(6.2e3) - 4, cy + 140, "one year", 10.5, GRN, 700, "end")]))
  b.append(g(f"{tl.show(16.6)} fin", [f'<path d="M{X(1.24e4) + 4:.0f},{cy + 18} H{X(6e5) - 4:.0f}" stroke="{RED}" stroke-width="2" stroke-dasharray="4 3"/>',
                                      t((X(1.24e4) + X(6e5)) / 2, cy + 14, "≈ 50× short", 11.5, RED, 700, "middle")]))
  # scenarios panel
  py = 540
  b.append(g(f"{tl.show(20.8, 26.8)} tr", [f'<rect x="24" y="{py}" width="{W - 110}" height="100" rx="12" fill="#fff" stroke="{SO}" stroke-width="2"/>',
             t(40, py + 24, "Per scenario instead: a wrong move in at most 1 % of tries", 13, SO, 700),
             t(40, py + 46, "needs 299 tries with no failure (59 for 5 %): within reach of simulation and a closed course.", 12, NAVY),
             t(40, py + 66, "Example VT-03: no acceleration toward a stopped lead in ≥ 59 tries per scenario.", 12, NAVY),
             t(40, py + 86, "Plus: drive logs measure how often each scenario happens per km.", 12, MID)]))
  b.append(g(f"{tl.show(27.2)} fin", [f'<rect x="24" y="{py}" width="{W - 110}" height="100" rx="12" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, py + 24, "LionDriver today (WP-V-02 §3.2, §4)", 13, NAVY, 700),
             t(40, py + 46, "No rate-level claim: the gap is stated in the release argument (WP-K-02), not hidden.", 12, NAVY),
             t(40, py + 66, "It rests on the envelope + controllability tests + scenario targets + field monitoring.", 12, NAVY),
             t(40, py + 86, "VT-01…VT-15 proposed; evidence counts only after the freeze (OI-3, DQ-096).", 12, MID)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "How much driving would prove it? (animated)",
             "From the acceptance criterion to a rate: a human injury crash about once per 2 million miles, a share of 0.1 for SOTIF hazards and a 1 % chance that a wrong move causes harm give at most 5 × 10⁻⁶ wrong lane departures per mile (WP-V-02 case D). With no failure at 95 % confidence that needs about 6 × 10⁵ miles, against 10 000 to 20 000 km a year for LionDriver, about 50 times short. Per scenario instead: 299 tries without failure show at most 1 %. LionDriver claims no rate-level demonstration; the targets are proposals until they are frozen (DQ-096).", tl, b)


# ------------------------------------------------------------------ 5 hunting the unknowns
def unknowns():
  tl, h = Timeline(32.0), 660
  b = [t(24, 38, "Hunting for what we do not know yet", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "Area 3 cannot be listed, only searched (WP-V-04)"),
                 (5.4, "Every odd event is sorted into one of four classes"),
                 (12.4, "Keep searching until new kinds of trouble stop turning up"),
                 (20.0, "Stop rule R3: few classes seen only once, over enough events"),
                 (26.4, "LionDriver today: no search block driven yet")])
  # area 3 cloud with seven tools
  cx, cy = 320, 220
  b.append(g(f"{tl.show(0.5)} fin", [f'<ellipse cx="{cx}" cy="{cy}" rx="80" ry="72" fill="{RED_BG}" stroke="{RED}" stroke-width="2" stroke-dasharray="6 4"/>',
                                     t(cx, cy - 6, "3 · Unknown,", 13, RED, 800, "middle"), t(cx, cy + 12, "hazardous", 13, RED, 800, "middle")]))
  for i, (x, y) in enumerate([(290, 200), (350, 245), (305, 255), (345, 185)]):
    b.append(g(f"{tl.show(0.8)} fin", [f'<circle cx="{x}" cy="{y}" r="5" fill="{RED}" opacity="0.6"/>']))
  tools = [("U-1", "random routes"), ("U-2", "takeover review"), ("U-3", "log mining"), ("U-4", "adversarial sim"),
           ("U-5", "replay perturbation"), ("U-6", "closed-course rebuild"), ("U-7", "outside reports")]
  for i, (tid, lab) in enumerate(tools):
    ty = 132 + i * 26
    a = math.atan2(ty - cy, 190 - cx)
    ex, ey = cx + 80 * math.cos(a), cy + 72 * math.sin(a)
    b.append(g(f"{tl.show(1.0 + i * 0.5)} fin", [t(24, ty + 4, tid, 11, NAVY, 800), t(54, ty + 4, lab, 11, NAVY, 400),
                                                  f'<line x1="190" y1="{ty}" x2="{ex:.0f}" y2="{ey:.0f}" stroke="{LIGHT}" stroke-width="1.5"/>',
                                                  f'<circle cx="190" cy="{ty}" r="3" fill="{NAVY}"/>']))
  # triage
  tx0, ty0 = 430, 112
  b.append(g(f"{tl.show(5.6)} fin", [t(tx0, ty0 + 14, "TRIAGE (§3)", 11, MID, 800)]))
  cls = [("N", "nominal", "close it", MID), ("K", "a known scenario", "count it in WP-V-03", SO), ("U", "new hazardous scenario", "new TC, KS; modify or restrict", RED),
         ("F", "a part failed", "→ ISO 26262 problem report", FS)]
  for i, (c, a, act, col) in enumerate(cls):
    y = ty0 + 26 + i * 44
    b.append(g(f"{tl.show(6.0 + i * 1.3)} fin", [f'<rect x="{tx0}" y="{y}" width="266" height="38" rx="8" fill="#fff" stroke="{col}" stroke-width="2"/>',
                                                  f'<circle cx="{tx0 + 20}" cy="{y + 19}" r="12" fill="{col}"/>', t(tx0 + 20, y + 24, c, 12, "#fff", 800, "middle"),
                                                  t(tx0 + 40, y + 16, a, 12, NAVY, 700), t(tx0 + 40, y + 31, act, 11, MID)]))
  # discovery curve
  gx, gy, gw, gh = 70, 350, 300, 170
  b.append(g(f"{tl.show(12.6)} fin", [f'<line x1="{gx}" y1="{gy + gh}" x2="{gx + gw}" y2="{gy + gh}" stroke="{NAVY}" stroke-width="1.5"/>',
                                      f'<line x1="{gx}" y1="{gy}" x2="{gx}" y2="{gy + gh}" stroke="{NAVY}" stroke-width="1.5"/>',
                                      t(gx + gw, gy + gh + 18, "engaged km", 11, MID, 400, "end", True),
                                      f'<text x="{gx - 10}" y="{gy + gh / 2}" font-size="11" fill="{MID}" font-style="italic" text-anchor="middle" transform="rotate(-90 {gx - 10} {gy + gh / 2})">new kinds found</text>']))
  pts = [(0, 0), (40, 45), (80, 78), (120, 100), (160, 114), (200, 122), (240, 126), (280, 128)]
  for i in range(1, len(pts)):
    (a0, b0), (a1, b1) = pts[i - 1], pts[i]
    b.append(g(f"{tl.show(13.0 + i * 0.6)} fin", [f'<line x1="{gx + a0}" y1="{gy + gh - b0}" x2="{gx + a1}" y2="{gy + gh - b1}" stroke="{SO}" stroke-width="3" stroke-linecap="round"/>']))
  for k, lab in enumerate(["B1", "B2", "B3"]):
    xx = gx + 100 + k * 90
    b.append(g(f"{tl.show(14.0)} fin", [f'<line x1="{xx}" y1="{gy}" x2="{xx}" y2="{gy + gh}" stroke="{LIGHT}" stroke-dasharray="3 3"/>', t(xx - 4, gy + 12, lab, 10.5, MID, 700, "end")]))
  b.append(g(f"{tl.show(18.0)} fin", [t(gx + 110, gy + 120, "flattening: the common", 11, SO, 700), t(gx + 110, gy + 134, "unknowns are found", 11, SO, 700)]))
  # R3 box
  rx = 400
  b.append(g(f"{tl.show(20.2)} fin", [f'<rect x="{rx}" y="{gy}" width="296" height="150" rx="12" fill="#fff" stroke="{NAVY}" stroke-width="1.5"/>',
             t(rx + 14, gy + 24, "Stop rule R3 (DQ-108, DQ-262)", 13, NAVY, 700),
             t(rx + 14, gy + 48, "P̂₀ = f₁ ÷ N ≤ 0.10, with N ≥ 30", 14, SO, 800),
             t(rx + 14, gy + 70, "f₁: kinds of trouble seen exactly once", 11.5, NAVY),
             t(rx + 14, gy + 88, "N: hazardous events sorted K or U", 11.5, NAVY),
             t(rx + 14, gy + 110, "30 events, 3 seen once → 0.10: just meets", 11.5, NAVY, 600),
             t(rx + 14, gy + 132, "and no rise over the last three blocks", 11.5, MID, 400, "start", True)]))
  b.append(g(f"{tl.show(26.6)} fin", [f'<rect x="24" y="580" width="{W - 110}" height="62" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 602, "No block (B0–B3) has run and no LionDriver drive logs exist yet (WP-V-04 §6).", 12, NAVY, 600),
             t(40, 622, "A simulation prototype, with no evidence credit, found a case the HARA lacked: now rated HE-01.6.", 12, MID)]))
  b.append(stick(W - 40, h - 18, "point"))
  return svg(h, "Hunting for what we do not know yet (animated)",
             "Area 3 is searched with seven methods U-1 to U-7 of WP-V-04. Each odd event is triaged: N nominal, K a known scenario, U a new hazardous scenario, or F a part failed, which goes to ISO 26262. New kinds found flatten over the blocks B1 to B3; the search stops when f1 / N is at most 0.10 with N at least 30 and no rise over three blocks (DQ-108, DQ-262). No block has run and no LionDriver drive logs exist yet; a simulation prototype found a case the HARA lacked, now rated HE-01.6.", tl, b)


# ------------------------------------------------------------------ 6 one chain, both standards
def one_chain():
  tl, h = Timeline(30.0), 680
  b = [t(24, 38, "One requirement, two standards", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "Two causes of the same swerve: a fault, or the model getting it wrong"),
                 (4.0, "One requirement answers both: cap the steering to what a driver can overpower"),
                 (9.4, "The panda enforces it, whatever the openpilot computer asks for"),
                 (13.4, "One test shows the cap is controllable: drivers face the worst it allows"),
                 (18.2, "The same evidence supports a claim on each side of the safety case"),
                 (24.0, "Why SOTIF leans on it: driving alone cannot prove the model's rate (scene 4)")])
  cw = 300
  lx, rx = 24, W - 24 - cw
  # row 1 causes
  y1 = 110
  b.append(g(f"{tl.show(0.5)} fin", card(lx, y1, cw, 64, "ISO 26262 · H-01, SG-01", FS, ["A fault sends steering torque", "a software bug, a bad frame"])))
  b.append(g(f"{tl.show(1.4)} fin", card(rx, y1, cw, 64, "ISO 21448 · SH-01", SO, ["The model steers on a wrong path", "every part working as designed"])))
  # merge to the requirement
  y2 = 214
  b.append(g(f"{tl.show(4.2)} fin", [f'<path d="M{lx + cw / 2},{y1 + 64} V{y2 - 14} H{W / 2 - 30} V{y2}" fill="none" stroke="{FS}" stroke-width="2.5"/>',
                                     f'<path d="M{rx + cw / 2},{y1 + 64} V{y2 - 14} H{W / 2 + 30} V{y2}" fill="none" stroke="{SO}" stroke-width="2.5"/>']
             + card(120, y2, W - 240, 70, "THE REQUIREMENT · FSR-01.01, ASIL C · SOTIF AC-02", BOTH,
                    ["Limit steering torque to a speed-dependent bound", "that a driver can control"], fill="#f3f0fd")))
  y3 = 314
  b.append(g(f"{tl.show(9.6)} fin", [f'<line x1="{W / 2}" y1="{y2 + 70}" x2="{W / 2}" y2="{y3}" stroke="{BOTH}" stroke-width="2.5"/>']
             + card(120, y3, W - 240, 70, "THE DESIGN · panda safety mode", NAVY,
                    ["Torque capped at 1500 raw (opendbc safety, toyota.h)", "Partly met: fixed, not speed-dependent (GAP-04); FM-10"])))
  y4 = 414
  b.append(g(f"{tl.show(13.6)} fin", [f'<line x1="{W / 2}" y1="{y3 + 70}" x2="{W / 2}" y2="{y4}" stroke="{BOTH}" stroke-width="2.5"/>']
             + card(120, y4, W - 240, 70, "THE TEST · VS-VAL-10 / CA-01 (WP-V-01)", NAVY,
                    ["Unannounced worst-case torque at 30–110 km/h:", "20 of 20 drivers must keep the car in its lane"])))
  ch, w = chip(W - 120 - 96, y4 + 20, "not run yet", AMBER)
  b.append(g(f"{tl.show(15.2)} fin", ch))
  # split to two claims
  y5 = 520
  b.append(g(f"{tl.show(18.4)} fin", [f'<path d="M{W / 2 - 30},{y4 + 70} V{y5 - 14} H{lx + cw / 2} V{y5}" fill="none" stroke="{FS}" stroke-width="2.5"/>',
                                      f'<path d="M{W / 2 + 30},{y4 + 70} V{y5 - 14} H{rx + cw / 2} V{y5}" fill="none" stroke="{SO}" stroke-width="2.5"/>']
             + card(lx, y5, cw, 64, "CLAIM G1.1 · ISO 26262", FS, ["SG-01 lateral motion is met", "a fault's torque stays controllable"])
             + card(rx, y5, cw, 64, "CLAIM G2 · ISO 21448", SO, ["SOTIF hazards acceptably low", "WP-V-02: release argument, point 1"])))
  b.append(g(f"{tl.show(24.2)} fin", [f'<rect x="24" y="598" width="{W - 110}" height="46" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 617, "Whatever the model gets wrong, the cap keeps it within what a driver can correct.", 12, NAVY, 700),
             t(40, 634, "Build it once, test it once, cite it twice; a gap in it (GAP-04) weakens both claims.", 11.5, MID)]))
  b.append(stick(W - 40, h - 16, "point"))
  return svg(h, "One requirement, two standards (animated)",
             "A fault (H-01, SG-01) and a model error (SH-01) are both answered by FSR-01.01, ASIL C, also SOTIF criterion AC-02: limit steering torque to a speed-dependent bound a driver can control. The panda caps the torque at 1500 raw, partly met because the cap is fixed (GAP-04, FM-10). The test VS-VAL-10 / CA-01, unannounced worst-case torque at 30 to 90 km/h with 20 of 20 drivers keeping the lane, is not run yet. The same evidence supports claim G1.1 (ISO 26262) and claim G2 (ISO 21448).", tl, b)



def render(root: Path = ROOT) -> dict[str, str]:
  c = counts(root)
  return dict(zip(NAMES, (two_questions(), who_owns(), triggering(c), four_areas(c), how_much(), unknowns(), one_chain()), strict=True))


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
