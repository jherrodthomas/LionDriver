#!/usr/bin/env python3
"""Render the animated explainers of the wiki page "Cybersecurity and ISO/SAE 21434" as SVG.

  cyber-third-question.svg   the same swerve from a fault, a model error and an attack (DS-01, TS-02), one hazard log;
  cyber-one-threat.svg       TS-02 through the seven questions of the TARA, from asset to treatment;
  cyber-more-than-safety.svg the four impact categories, steering (DS-01) against leaked cabin video (DS-08);
  cyber-how-hard.svg         the attack-potential factors of AP-02 and AP-01, and how closing a path moves the attacker;
  cyber-risk-map.svg         every threat scenario on the impact × feasibility matrix, the threshold and the treatments;
  cyber-goal-to-evidence.svg CSG-01 from goal to requirement, control, verification, validation and claim;
  cyber-meet.svg             four safety–security interactions of hatara/ and the count by type;
  cyber-after-release.svg    monitoring, an example vulnerability report through WP-O-05, secure updates, and today.

The risk-map placements, the treatment lists, the attack-path factors, the damage-scenario counts and the interaction
counts are read from WP-C-09, WP-C-10 and hatara/hatara-interactions.md. Every other ID, rating, status and number is
tied to a phrase of the record it comes from (SOURCES) and checked at render time (`problems()`), and the code paths it
names are checked to exist. When a record changes, the wiki build fails instead of showing old text. build_wiki.py
renders the figures next to the pages at each sync (nothing is committed). They loop with CSS; reduced motion shows the
final frame. The vulnerability report of cyber-after-release.svg is an example and is labelled so.

Usage: python3 tools/wiki/cyber_animations.py [--out DIR] [--check]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from animations import GRN, LIGHT, MID, NAVY, RED, RED_BG, W, Timeline, g, norm, stick, svg, t  # noqa: E402

NAMES = ("cyber-third-question.svg", "cyber-one-threat.svg", "cyber-more-than-safety.svg", "cyber-how-hard.svg",
         "cyber-risk-map.svg", "cyber-goal-to-evidence.svg", "cyber-meet.svg", "cyber-after-release.svg")
AMBER, BLUE, VIOLET, ORANGE, TEAL = "#b7791f", "#2a78d6", "#6250d6", "#c2410c", "#0f766e"
FS, SO, CS = BLUE, ORANGE, "#be185d"      # ISO 26262 blue, ISO 21448 orange, ISO/SAE 21434 magenta

CON = Path("assurance") / "02-concept"
C03, C05, C06 = CON / "WP-C-03-hara.md", CON / "WP-C-05-sotif-hazard-identification.md", CON / "WP-C-06-sotif-insufficiencies-triggering-conditions.md"
C09, C10 = CON / "WP-C-09-tara.md", CON / "WP-C-10-cybersecurity-goals-and-concept.md"
IX = CON / "hatara" / "hatara-interactions.md"
S02 = Path("assurance") / "03-system" / "WP-S-02-technical-safety-requirements.md"
W11 = Path("assurance") / "05-software" / "WP-W-11-cybersecurity-implementation-verification.md"
V06 = Path("assurance") / "06-validation" / "WP-V-06-cybersecurity-validation.md"
O05 = Path("assurance") / "09-production-operation" / "WP-O-05-cybersecurity-incident-response-updates.md"
K03 = Path("assurance") / "10-safety-case" / "WP-K-03-cybersecurity-case.md"
LOCK = Path("panda") / "board" / "reference_lock.h"              # checked when the submodule is there
VARIANT = Path("tools") / "release" / "release_variant.sh"
SAFETY_CI = Path(".github") / "workflows" / "safety.yaml"

# (record, phrase a figure stands on)
SOURCES = [
  (C03, "| HE-01.4 | Torque while not engaged"), (C05, "| SH-01 | Model-commanded steering moves the vehicle out of the lane"),
  (C06, "| TC-05 | Faded, missing or doubled lane markings; tar seams"),
  (C09, "| AS-02 | Panda safety mode and safety parameter | Integrity, Authenticity"),
  (C09, "| DS-01 | Unintended/excessive lateral actuation induced by manipulation | H-01 (ASIL C; D if AOU-01/02 fail) | Severe | Major | Major | Negligible | 4 |"),
  (C09, "| DS-08 | Disclosure of driver-facing video / cabin imagery | — | Negligible | Moderate | Moderate | Severe | 4 |"),
  (C09, "| TS-02 | Compromised SoC user space sets an unsafe panda safety mode/parameter (`0xdc`) | Tampering, Elevation |"),
  (C09, "| AP-02 | Root on SoC (QM user space) | Host→panda `0xdc` sets a permissive/non-Toyota safety mode or parameter with no authentication"),
  (C09, "| AP-01 |"), (C09, "| TS-02 | 4 | High | **5** | **Reduce** |"), (C09, "LionDriver is open source, so **KoI is \"public\" for every path**"),
  (C09, "firmware lock implemented (reference build, `board/reference_lock.h`, TSR-512/513), not verified; not re-rated (OI-5)"),
  (C09, "| 2 | TS-03 | **5** | SoC drives panda boot pins and flashes a dev bootstub"),
  (C09, "| TS-11 | Physical theft / possession of the device exposes stored video, location and keys"),
  (C09, "Encrypt sensitive data at rest; protect the identity key; decommissioning wipe (WP-O-02)"),
  (C09, "**Risk treatment threshold.** Risk value **≥ 3** requires treatment"), (C09, "risk value 4–5 drives a cybersecurity goal"),
  (C10, "| **CSG-01** | The integrity and authenticity of the panda safety configuration"), (C10, "| TS-02 (5) | **CAL 3** |"),
  (C10, "| **CSG-02** | The integrity and authenticity of the panda firmware and its boot chain"),
  (C10, "| CSR-C-01 | The panda firmware shall enforce the Toyota safety mode and reject any mode/parameter change from the SoC that is not authorized for the reference configuration"),
  (C10, "| 5, safety impact | local-to-safety-element or physical-fleet | CAL 3 |"),
  (C10, "| CSG-08 | Encrypt personal data and the identity key at rest"),
  (S02, "| TSR-512 | In release builds for the reference configuration the safety MCU shall accept only the modes"),
  (K03, "| CSn-21 | Safety-mode lock and command-gating tests (shared with TSR-512, TSR-513) | WP-W-06/WP-W-08 | CG2.1 | Partial |"),
  (K03, "| CSn-30 | Validation TC-01, TC-02 (command fuzzing, mode lock) |"), (K03, "| CG2.1, CG4.1 | Missing |"),
  (K03, "→ CG2.1 CSG-01 safety configuration integrity (CAL 3)"),
  (V06, "**no validation or penetration test has been executed and no tester is engaged**"),
  (IX, "| IX-04 | One lock serves both | Mutual reinforcement | both |"), (IX, "CSR-C-01 implemented, not verified"),
  (IX, "| IX-01 | A recovery path is also an attack path | Antagonism | safety → security |"), (IX, "CSR-C-05 not implemented"),
  (IX, "| IX-03 | A rejected frame is a lost function | Antagonism | security → safety |"),
  (IX, "| IX-10 | Firmware integrity holds up SG-01…SG-07 | Conditional dependency | security → safety |"),
  (IX, "| IX-11 | Screen and DM attacks reach H-07, H-09 |"), (IX, "Closed: WP-C-09 §3 links them now"),
  (O05, "**not running**. No monitoring, intake or incident record exists yet (GAP-28)"),
  (O05, "| MS-01 | Upstream comma repositories"), (O05, "| MS-03 | GitHub Advisory Database / OSV"), (O05, "| MS-07 | LionDriver vulnerability intake"),
  (O05, "| MS-08 | Field data"), (O05, "| Acknowledge an intake report | 3 working days |"),
  (O05, "5 working days (2 for intake and safety-tagged events)"), (O05, "| Safety decision for safety-relevant Critical/High | 24 h from E4 = yes |"),
  (O05, "| **Critical** | Risk value 5, or any exploitable path to a safety-goal violation"), (O05, "Fix release within **14 days**"),
  (O05, "Stage 2: up to 10 % of known installations or 3 vehicles"), (O05, "for Critical fixes the SM may shorten stages to 24 h each"),
  (O05, "| Advisory publication | With the fix release, or ≤ 90 days |"), (O05, "automatic updates are disabled"), (O05, "(CSR-121…CSR-126)"),
  (O05, "rollback that changes panda firmware tested on the bench first"),
  (VARIANT, 'RELEASE_VARIANT="${RELEASE_VARIANT:-reference}"'), (SAFETY_CI, "reference_lock"),
  (Path("SECURITY.md"), "## Reporting a vulnerability"),
]

FACTORS = [("ET", ["Hours", "Days", "Weeks", "Months"]), ("Ex", ["Layman", "Proficient", "Expert", "Multi"]),
           ("KoI", ["Public", "Restricted", "Confidential", "Strictly"]), ("WoO", ["Unlimited", "Moderate", "Limited", "Difficult"]),
           ("Eq", ["Standard", "Specialized", "Bespoke", "Multi"])]


MATRIX = [[5, 4, 3, 2], [4, 3, 2, 1], [3, 2, 2, 1], [2, 1, 1, 1]]      # WP-C-09 §7, impact 4…1 by feasibility
MATRIX_COLS = ["High", "Medium", "Low", "Very low"]


class ParseError(Exception):
  pass


def rows(text: str, prefix: str, start: str, end: str) -> list[list[str]]:
  i = text.find(start)
  if i < 0:
    raise ParseError(f"heading {start!r} not found")
  j = text.find(end, i + len(start))
  return [[c.strip() for c in r.strip().strip("|").split("|")] for r in text[i:j if j > 0 else None].splitlines()
          if r.startswith(f"| {prefix}-")]


def data(root: Path = ROOT) -> dict:
  """Everything the figures compute from the records."""
  t9 = (root / C09).read_text(encoding="utf-8")
  t10 = (root / C10).read_text(encoding="utf-8")
  ds = rows(t9, "DS", "## 3. Damage scenarios", "\n## 4.")
  risk = rows(t9, "TS", "## 8. Risk determination", "![Figure 8-1")
  aps = {r[0]: r for r in rows(t9, "AP", "## 6. Attack feasibility", "\n## 7.")}
  ap = {}
  for key in ("AP-02", "AP-01"):
    r = aps.get(key)
    if r is None:
      raise ParseError(f"WP-C-09 §6: {key} missing")
    vals = []
    for (name, scale), cell in zip(FACTORS, r[1:6], strict=True):
      hit = [k for k, w in enumerate(scale) if cell.startswith(w)]
      if not hit:
        raise ParseError(f"WP-C-09 §6 {key}: {name} {cell!r} is not on the drawn scale {scale}")
      vals.append(hit[0])
    ap[key] = (vals, r[6].strip("*"))
  cells: dict[tuple[int, str], list[str]] = {}
  treat: dict[str, list[str]] = {"Reduce": [], "Avoid": [], "Share": [], "Retain": []}
  amber = []
  for r in risk:
    ts, imp, feas, val, tr = r[0], int(r[1]), r[2], int(r[3].strip("*")), r[4].strip("*")
    cells.setdefault((imp, feas), []).append((ts, val))
    for opt in treat:
      if opt in tr:
        treat[opt].append(ts)
    if "not verified" in r[5]:
      amber.append(ts)
  ix = [l.split("|")[3].strip() for l in (root / IX).read_text(encoding="utf-8").splitlines() if l.startswith("| IX-")]
  return {"ds": len(ds), "ds_hara": sum(1 for r in ds if r[2] != "—"), "cells": cells, "treat": treat, "amber": sorted(amber),
          "ts": len(risk), "ts45": sum(1 for r in risk if int(r[3].strip("*")) >= 4), "ap": ap,
          "csg": len(re.findall(r"^\| \*\*CSG-\d+\*\* \|", t10, re.M)),
          "ix": len(ix), "ix_hurt": ix.count("Antagonism"), "ix_help": ix.count("Mutual reinforcement"),
          "ix_hold": ix.count("Conditional dependency")}


def problems(root: Path = ROOT) -> list[str]:
  errs, cache = [], {}
  for path, phrase in SOURCES:
    if path not in cache:
      p = root / path
      cache[path] = norm(p.read_text(encoding="utf-8")) if p.exists() else ""
    if norm(phrase) not in cache[path]:
      errs.append(f"{path}: the cybersecurity page stands on {phrase!r}, which is gone; update the figure")
  if (root / "panda" / "board").exists() and not (root / LOCK).exists():
    errs.append(f"{LOCK}: the safety-mode lock moved; update cyber-goal-to-evidence.svg")
  try:
    d = data(root)
    if d["ix_hurt"] + d["ix_help"] + d["ix_hold"] != d["ix"]:
      errs.append(f"{IX}: an interaction type is not one of the three the figure draws")
    for (imp, feas), tss in d["cells"].items():
      for ts, val in tss:
        if feas not in MATRIX_COLS or not 1 <= imp <= 4 or MATRIX[4 - imp][MATRIX_COLS.index(feas)] != val:
          errs.append(f"{C09}: {ts} risk {val} at impact {imp}, feasibility {feas} does not match the §7 matrix the map draws")
    if ("4", "High") not in {(str(k[0]), k[1]) for k in d["cells"]}:
      errs.append(f"{C09}: no threat scenario at impact 4, feasibility High; redraw cyber-risk-map.svg")
  except (ParseError, ValueError, IndexError, OSError) as e:
    errs.append(f"cybersecurity records: {e}")
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



def soc_icon(x, y):
  return [f'<rect x="{x}" y="{y}" width="54" height="40" rx="5" fill="#f1f3f7" stroke="{NAVY}" stroke-width="1.6"/>',
          t(x + 27, y + 25, "SoC", 12, NAVY, 700, "middle")]


def hacker(x, y):
  """A hooded figure, feet at (x, y)."""
  return [f'<path d="M{x - 14},{y} q0,-26 14,-30 q14,4 14,30 z" fill="{CS}" opacity="0.85"/>',
          f'<circle cx="{x}" cy="{y - 38}" r="11" fill="{CS}"/>', f'<circle cx="{x}" cy="{y - 36}" r="6" fill="#fff"/>']


# ------------------------------------------------------------------ 0 the third question
def third_question():
  tl, h = Timeline(26.0), 610
  b = [t(24, 38, "The third question: what if someone attacks it?", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "The same swerve: the car steers itself out of its lane (H-01)"),
                 (3.4, "Two causes you have met: a part breaks, or the function gets it wrong"),
                 (7.6, "A third: someone makes it happen on purpose"),
                 (14.6, "One hazard, three causes, three kinds of cure"),
                 (20.4, "An attacker chooses the worst moment, so failure rates do not apply")])
  rx, ry, rw, rh = 300, 104, 120, 120
  b.append(g(f"{tl.show(0.4)} fin", road(rx, ry, rw, rh)))
  b.append(g(f"{tl.show(0.4, 2.0)} tr", topcar(rx + 90, ry + 92)))
  b.append(g(f"{tl.show(1.8)} fin", [f'<path d="M{rx + 90},{ry + 92} C{rx + 90},{ry + 50} {rx + 110},{ry + 36} {rx + 130},{ry + 6}" fill="none" stroke="{RED}" stroke-width="3" stroke-dasharray="6 5"/>']
                                     + topcar(rx + 120, ry + 26, RED, 22)))
  b.append(g(f"{tl.show(2.2)} fin", [t(rx + rw + 18, ry + 44, "Leaves its lane", 14, RED, 700), t(rx + rw + 18, ry + 64, "H-01 in the hazard log", 11.5, MID)]))
  cw, cy, ch = 214, 246, 218
  cols = [(24, FS, "ISO 26262", "Something broke", ["A software bug sends", "steering torque while", "not engaged"], "HE-01.4 · ASIL C", "Cure: catch the fault"),
          (24 + cw + 9, SO, "ISO 21448 · SOTIF", "Nothing broke", ["The model takes a tar", "seam for a lane line"], "SH-01 · no ASIL", "Cure: improve, restrict"),
          (24 + 2 * (cw + 9), CS, "ISO/SAE 21434", "Someone did it", ["With root on the openpilot", "computer, an attacker tells", "the panda to drop its limits"], "DS-01 · TS-02 · risk 5", "Cure: make it hard")]
  for i, (x, c, ttl, q, lines, idl, cure) in enumerate(cols):
    t0 = [3.6, 5.4, 7.8][i]
    o = [f'<rect x="{x}" y="{cy}" width="{cw}" height="{ch}" rx="12" fill="#fff" stroke="{c}" stroke-width="2.2"/>',
         f'<rect x="{x}" y="{cy}" width="{cw}" height="28" rx="12" fill="{c}"/>', f'<rect x="{x}" y="{cy + 16}" width="{cw}" height="12" fill="{c}"/>',
         t(x + 12, cy + 20, ttl, 12, "#fff", 700), t(x + 12, cy + 50, q, 13, c, 700)]
    o += [t(x + 12, cy + 120 + k * 17, s, 12, NAVY, 600) for k, s in enumerate(lines)]
    o += [t(x + 12, cy + 186, idl, 11.5, NAVY, 700), t(x + 12, cy + 205, cure, 11.5, c, 700)]
    b.append(g(f"{tl.show(t0)} fin", o))
  # icons
  x0 = 24
  b.append(g(f"{tl.show(3.8)} fin", soc_icon(x0 + 12, cy + 62) + [f'<path d="M{x0 + 80},{cy + 64} l-8,14 h7 l-5,14 l13,-18 h-7 l5,-10 z" fill="{RED}"/>']))
  x1 = 24 + cw + 9
  b.append(g(f"{tl.show(5.6)} fin", [f'<rect x="{x1 + 12}" y="{cy + 60}" width="54" height="44" rx="5" fill="#eef0f3"/>',
                                     f'<line x1="{x1 + 22}" y1="{cy + 60}" x2="{x1 + 22}" y2="{cy + 104}" stroke="#fff" stroke-width="3" stroke-dasharray="3 9" opacity="0.6"/>',
                                     f'<path d="M{x1 + 54},{cy + 104} C{x1 + 46},{cy + 86} {x1 + 36},{cy + 76} {x1 + 30},{cy + 60}" fill="none" stroke="#3b3f47" stroke-width="2.4"/>']))
  x2 = 24 + 2 * (cw + 9)
  b.append(g(f"{tl.show(8.2)} fin", hacker(x2 + 32, cy + 106)))
  b.append(g(f"{tl.show(9.0)} fin", soc_icon(x2 + 70, cy + 62)
             + [f'<path d="M{x2 + 46},{cy + 82} h22" stroke="{CS}" stroke-width="2.5"/>',
                f'<rect x="{x2 + 150}" y="{cy + 62}" width="54" height="40" rx="5" fill="#fff6ef" stroke="{ORANGE}" stroke-width="2"/>',
                t(x2 + 177, cy + 86, "panda", 11.5, NAVY, 700, "middle"), f'<path d="M{x2 + 124},{cy + 82} h24" stroke="{CS}" stroke-width="2.5"/>']))
  b.append(g(f"{tl.show(10.6)} fin", [f'<rect x="{x2 + 150}" y="{cy + 62}" width="54" height="40" rx="5" fill="{RED_BG}" stroke="{RED}" stroke-width="2" stroke-dasharray="4 3"/>',
                                      t(x2 + 177, cy + 78, "limits", 10.5, RED, 700, "middle"), t(x2 + 177, cy + 92, "off", 10.5, RED, 700, "middle")]))
  b.append(g(f"{tl.show(14.8)} fin", [f'<rect x="24" y="480" width="{W - 110}" height="58" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
                                      t(40, 502, "One hazard log: the damage scenario DS-01 points at H-01 and takes its", 12.5, NAVY, 700),
                                      t(40, 522, "safety impact from the HARA (Severe: H-01 is ASIL C).", 12.5, NAVY, 700)]))
  b.append(g(f"{tl.show(20.6)} fin", [t(24, 562, "A broken part fails at random; an attacker waits for the worst moment and repeats it on every car.", 12, CS, 700),
                                      t(24, 582, "So ISO/SAE 21434 rates how hard an attack is, not how often it happens.", 12, MID)]))
  b.append(stick(W - 40, 540, "point"))
  return svg(h, "The third question: what if someone attacks it? (animated)",
             "The car steers out of its lane (H-01). ISO 26262: a software bug sends torque while not engaged (HE-01.4, ASIL C). ISO 21448: the model takes a tar seam for a lane line (SH-01). ISO/SAE 21434: an attacker with root on the openpilot computer tells the panda to drop its limits (DS-01, TS-02, risk 5). One hazard log: DS-01 takes its safety impact from H-01. An attacker chooses the worst moment and repeats it on every car, so ISO/SAE 21434 rates how hard an attack is, not how often it happens.", tl, b)


# ------------------------------------------------------------------ 1 one threat through the TARA
def one_threat():
  tl, h = Timeline(34.0), 690
  b = [t(24, 38, "Following one threat through the TARA", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "A threat analysis and risk assessment (TARA) asks seven questions (WP-C-09)"),
                 (30.0, "Top of LionDriver's list: risk 5 of 5, treated, not yet verified")])
  steps = [
    ("1", "What do we protect?", "Asset AS-02: the panda's safety mode and parameter", "integrity · authenticity", None),
    ("2", "What harm if it is broken?", "Damage DS-01: unintended steering (H-01)", "impact Severe · level 4", RED),
    ("3", "Who could do what?", "Threat TS-02: a hacked openpilot computer sets an unsafe mode", "STRIDE: tampering, elevation", None),
    ("4", "How, step by step?", "Attack path AP-02: root on the SoC → mode command → no check", "", None),
    ("5", "How hard is it?", "Hours · proficient · public design · moderate access · standard kit", "feasibility High", RED),
    ("6", "So how risky?", "Impact 4 × feasibility High", "risk 5 of 5", RED),
    ("7", "What do we do?", "Reduce: goal CSG-01 (CAL 3), lock the mode in panda firmware", "built, not verified", AMBER),
  ]
  y0 = 112
  for i, (n, q, ans, tag, tc) in enumerate(steps):
    y = y0 + i * 66
    t0 = 1.0 + i * 4.0
    b.append(g(f"{tl.show(t0)} fin", [f'<circle cx="44" cy="{y + 26}" r="15" fill="{CS}"/>', t(44, y + 31, n, 13, "#fff", 800, "middle"),
                                       t(70, y + 20, q, 12, CS, 700)]
               + ([f'<line x1="44" y1="{y + 41}" x2="44" y2="{y + 66 + 11}" stroke="{CS}" stroke-width="2" opacity="0.4"/>'] if i < 6 else [])))
    o = [f'<rect x="70" y="{y + 28}" width="{W - 94}" height="30" rx="7" fill="#fff" stroke="{LIGHT}"/>', t(82, y + 48, ans, 12.5, NAVY, 600)]
    if tag:
      ch, w = chip(W - 30 - len(tag) * 6.3 - 16, y + 48, tag, tc or MID)
      o += ch
    b.append(g(f"{tl.show(t0 + 1.0)} fin", o))
  # mini matrix next to step 6
  mx, my = 520, y0 + 5 * 66 - 6
  b.append(g(f"{tl.show(22.4, 29.6)} tr", [f'<rect x="{mx - 6}" y="{my - 44}" width="136" height="40" rx="6" fill="#fff" stroke="{LIGHT}"/>']
             + [f'<rect x="{mx + k * 30}" y="{my - 38}" width="26" height="28" rx="3" fill="{c}"/>' for k, c in enumerate([RED, "#e0884f", "#f0c27b", "#f6e3b4"])]
             + [t(mx + 13 + k * 30, my - 19, v, 11, "#fff" if k < 2 else NAVY, 800, "middle") for k, v in enumerate(["5", "4", "3", "2"])]
             + [f'<rect x="{mx - 2}" y="{my - 40}" width="30" height="32" rx="4" fill="none" stroke="{NAVY}" stroke-width="2.5"/>']))
  b.append(g(f"{tl.show(30.2)} fin", [t(70, y0 + 7 * 66 + 10, "The firmware lock is in the reference build but not verified, and the threat is not re-rated (OI-5).", 11.5, MID, 400, "start", True)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "Following one threat through the TARA (animated)",
             "Seven questions for TS-02: the asset AS-02, the panda safety mode and parameter; the damage DS-01, unintended steering, impact Severe, level 4; the threat, a hacked openpilot computer setting an unsafe mode (tampering, elevation); the attack path AP-02, root on the SoC to the mode command with no check; the feasibility, High; the risk, 5 of 5; the treatment, reduce with goal CSG-01 at CAL 3, a lock in the panda firmware, built in the reference build and not verified (OI-5).", tl, b)


# ------------------------------------------------------------------ 2 damage is more than safety
def more_than_safety(d):
  tl, h = Timeline(28.0), 600
  b = [t(24, 38, "Damage is more than safety", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "ISO/SAE 21434 rates each damage four ways: safety, financial, operational, privacy"),
                 (3.6, "Unintended steering: Severe on safety"),
                 (10.6, "Leaked driver video: Severe on privacy, a harm ISO 26262 never sees"),
                 (17.4, "The impact level is the worst of the four"),
                 (22.4, "Both are level 4; easy to do, both are risk 5 (TS-02, TS-11)")])
  cats = [("S", "Safety"), ("F", "Financial"), ("O", "Operational"), ("P", "Privacy")]
  lv = {"Negligible": 1, "Moderate": 2, "Major": 3, "Severe": 4}
  colf = {1: "#cbd5e1", 2: "#f0c27b", 3: "#e0884f", 4: RED}

  def panel(x, t0, ttl, sub, vals, scene):
    o = [g(f"{tl.show(t0)} fin", [f'<rect x="{x}" y="108" width="324" height="330" rx="12" fill="#fff" stroke="{CS}" stroke-width="2"/>',
                                  t(x + 14, 132, ttl, 14, NAVY, 700), t(x + 14, 150, sub, 11.5, MID)] + scene)]
    for k, ((c, name), v) in enumerate(zip(cats, vals)):
      y = 250 + k * 40
      n = lv[v]
      o.append(g(f"{tl.show(t0 + 1.0 + k * 0.8)} fin", [t(x + 14, y + 15, name, 12, NAVY, 600),
                                                         f'<rect x="{x + 100}" y="{y}" width="140" height="20" rx="4" fill="#f1f3f7"/>',
                                                         f'<rect x="{x + 100}" y="{y}" width="{n * 35}" height="20" rx="4" fill="{colf[n]}"/>',
                                                         t(x + 248, y + 15, v, 11.5, NAVY, 700)]))
    return o
  sc1 = [f'<rect x="38" y="164" width="120" height="70" rx="8" fill="#eef0f3"/>',
         f'<path d="M80,234 C80,204 100,190 120,168" fill="none" stroke="{RED}" stroke-width="3" stroke-dasharray="6 5"/>'] + topcar(112, 186, RED, 22) \
        + [t(170, 196, "DS-01 · from H-01", 12, NAVY, 700), t(170, 214, "unintended steering", 11.5, MID)]
  sc2 = [f'<rect x="372" y="164" width="120" height="70" rx="8" fill="#1e2d4d"/>', f'<circle cx="432" cy="194" r="16" fill="#cbd5e1"/>',
         f'<path d="M408,234 q24,-30 48,0 z" fill="#cbd5e1"/>', f'<rect x="372" y="164" width="120" height="70" rx="8" fill="none" stroke="{CS}" stroke-width="2" stroke-dasharray="5 4"/>',
         t(504, 196, "DS-08 · no hazard", 12, NAVY, 700), t(504, 214, "cabin video disclosed", 11.5, MID)]
  b += panel(24, 3.8, "Steering taken over", "the hazard ISO 26262 also rates", ["Severe", "Major", "Major", "Negligible"], sc1)
  b += panel(372, 10.8, "Driver video leaked", "no hazard: nobody is hurt in the car", ["Negligible", "Moderate", "Moderate", "Severe"], sc2)
  for x in (24, 372):
    b.append(g(f"{tl.show(17.6)} fin", [f'<rect x="{x + 14}" y="404" width="296" height="26" rx="6" fill="{CS}"/>',
                                        t(x + 162, 422, "impact level 4 (the worst of the four)", 12, "#fff", 700, "middle")]))
  b.append(g(f"{tl.show(22.6)} fin", [f'<rect x="24" y="456" width="{W - 110}" height="118" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 480, f"LionDriver (WP-C-09 §3): {d['ds']} damage scenarios", 13, NAVY, 700),
             t(40, 502, f"{d['ds_hara']} point at a HARA hazard and take its safety rating from there.", 12, NAVY),
             t(40, 522, f"{d['ds'] - d['ds_hara']} harm only data or identity: driver video, location history, the device key, a stolen device.", 12, NAVY),
             t(40, 546, "A stolen device (TS-11) is risk 5 with no hazard at all: it is treated by", 12, NAVY, 600),
             t(40, 564, "encryption at rest and a wipe at decommissioning (CSG-08).", 12, NAVY, 600)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "Damage is more than safety (animated)",
             f"Each damage scenario is rated for safety, financial, operational and privacy impact. Steering taken over (DS-01, from H-01): Severe, Major, Major, Negligible. Cabin video leaked (DS-08, no hazard): Negligible, Moderate, Moderate, Severe. Both are impact level 4, the worst of the four. WP-C-09 has {d['ds']} damage scenarios, {d['ds_hara']} linked to a HARA hazard; a stolen device (TS-11) is risk 5 with no hazard, treated by encryption at rest and a wipe at decommissioning (CSG-08).", tl, b)



def how_hard(d):
  tl, h = Timeline(30.0), 640
  b = [t(24, 38, "How hard is the attack?", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "Five questions about the attacker give the attack feasibility (WP-C-09 §6)"),
                 (11.2, "LionDriver is open source: the design is public on every path"),
                 (15.4, "Close one path and the attacker moves to the next"),
                 (22.6, "Feasibility High or Medium; each control should move it down")])
  factors = [("Time it takes", ["Hours", "Days", "Weeks", "Months"]), ("Expertise", ["Layman", "Proficient", "Expert", "Multi-expert"]),
             ("Knowledge of the item", ["Public", "Restricted", "Confidential", "Strictly conf."]),
             ("Window of opportunity", ["Unlimited", "Moderate", "Limited", "Difficult"]), ("Equipment", ["Standard", "Specialized", "Bespoke", "Multi-bespoke"])]
  paths = [("AP-02 · from a hacked openpilot computer", CS, *d["ap"]["AP-02"]),
           ("AP-01 · plugged into the car's CAN bus", BLUE, *d["ap"]["AP-01"])]
  sx, sw = 230, 420
  b.append(g(f"{tl.show(0.5)} fin", [t(sx, 116, "easier to attack", 11, RED, 700), t(sx + sw, 116, "harder", 11, GRN, 700, "end"),
                                     f'<line x1="{sx}" y1="122" x2="{sx + sw}" y2="122" stroke="{LIGHT}" stroke-width="1.5"/>']))
  for k, (name, lev) in enumerate(factors):
    y = 150 + k * 44
    o = [t(24, y + 5, name, 12.5, NAVY, 700), f'<line x1="{sx}" y1="{y}" x2="{sx + sw}" y2="{y}" stroke="#e5e9f0" stroke-width="8" stroke-linecap="round"/>']
    for j, l in enumerate(lev):
      xx = sx + j * sw / 3
      o += [f'<circle cx="{xx:.0f}" cy="{y}" r="3" fill="{LIGHT}"/>', t(xx, y + 20, l, 10, MID, 400, "middle")]
    b.append(g(f"{tl.show(0.8 + k * 0.3)} fin", o))
  for pi, (lab, c, vals, feas) in enumerate(paths):
    t0 = 2.6 + pi * 4.2
    off = -7 if pi == 0 else 7
    b.append(g(f"{tl.show(t0)} fin", [f'<rect x="24" y="{372 + pi * 34}" width="14" height="14" rx="7" fill="{c}"/>', t(46, 384 + pi * 34, lab, 12.5, NAVY, 700)]))
    for k, v in enumerate(vals):
      xx = sx + v * sw / 3
      b.append(g(f"{tl.show(t0 + 0.4 + k * 0.4)} fin", [f'<circle cx="{xx:.0f}" cy="{150 + k * 44 + off}" r="8" fill="{c}" stroke="#fff" stroke-width="2"/>']))
    ch, w = chip(W - 150, 384 + pi * 34, f"feasibility {feas}", RED if feas == "High" else AMBER)
    b.append(g(f"{tl.show(t0 + 2.6)} fin", ch))
  b.append(g(f"{tl.show(11.4)} fin", [f'<rect x="{sx - 22}" y="{150 + 2 * 44 - 18}" width="44" height="44" rx="8" fill="none" stroke="{CS}" stroke-width="2" stroke-dasharray="5 4"/>',
                                      t(24, 150 + 2 * 44 + 20, "public: anyone can read the code", 11, CS, 700)]))
  # the next path
  py = 452
  b.append(g(f"{tl.show(15.6)} fin", [f'<rect x="24" y="{py}" width="{W - 48}" height="88" rx="12" fill="#fff" stroke="{CS}" stroke-width="2"/>',
             t(40, py + 24, "Lock the safety mode (CSG-01) and AP-02 is blocked …", 12.5, NAVY, 700),
             t(40, py + 46, "… but the attacker can still replace the panda firmware through its boot chain:", 12.5, NAVY),
             t(40, py + 66, "TS-03, also risk 5, until goal CSG-02 protects the boot chain. Defence needs every layer.", 12.5, CS, 700)]))
  b.append(g(f"{tl.show(22.8)} fin", [t(24, 566, "No path is re-rated yet after its control is built (OI-5): a control counts once it is verified", 11.5, MID, 400, "start", True),
                                      t(24, 584, "and the rating is redone with it in place.", 11.5, MID, 400, "start", True)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "How hard is the attack? (animated)",
             f"Five attack-potential factors: time, expertise, knowledge of the item, window of opportunity, equipment. AP-02, from a hacked openpilot computer, gives feasibility {d['ap']['AP-02'][1]}; AP-01, plugged into the CAN bus, gives {d['ap']['AP-01'][1]}. LionDriver is open source, so knowledge of the item is public on every path. Locking the safety mode (CSG-01) blocks AP-02, but the boot chain (TS-03, risk 5) stays open until CSG-02. No path is re-rated yet (OI-5).", tl, b)


# ------------------------------------------------------------------ 4 the risk map
def risk_map(d):
  tl, h = Timeline(30.0), 650
  b = [t(24, 38, "The risk map: what must be treated", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "Risk = how bad (impact) × how easy (feasibility), from 1 to 5 (WP-C-09 §7)"),
                 (4.4, "All 14 LionDriver threat scenarios, placed on the map"),
                 (11.6, "Risk 3 or more must be treated; 4 or 5 gets a cybersecurity goal"),
                 (17.0, "Four ways to treat a risk"),
                 (23.4, "Today: every scenario is to be reduced; none is verified yet")])
  M = MATRIX
  fill = {5: RED, 4: "#e0884f", 3: "#f0c27b", 2: "#f6e3b4", 1: "#eef0f3"}
  gx, gy, cw, ch = 150, 132, 130, 64
  base = [t(gx + 2 * cw, gy - 14, "FEASIBILITY →", 11, MID, 800, "middle")]
  for j, f in enumerate(["High", "Medium", "Low", "Very low"]):
    base.append(t(gx + j * cw + cw / 2, gy - 0 + 4 * ch + 18, f, 11.5, NAVY, 700, "middle"))
  for i, (lev, name) in enumerate([(4, "Severe"), (3, "Major"), (2, "Moderate"), (1, "Negligible")]):
    base += [t(gx - 10, gy + i * ch + 30, f"{lev} {name}", 11.5, NAVY, 700, "end")]
    for j in range(4):
      v = M[i][j]
      base += [f'<rect x="{gx + j * cw + 2}" y="{gy + i * ch + 2}" width="{cw - 4}" height="{ch - 4}" rx="6" fill="{fill[v]}" opacity="0.55"/>',
               t(gx + j * cw + cw - 10, gy + i * ch + 18, str(v), 12, NAVY, 800, "end")]
  base.append(t(24, gy - 14, "IMPACT ↓", 11, MID, 800))
  b.append(g(f"{tl.show(0.5)} fin", base))
  feas = ["High", "Medium", "Low", "Very low"]
  cells = {(4 - imp, feas.index(f)): sorted(ts for ts, _ in tss) for (imp, f), tss in sorted(d["cells"].items(), key=lambda kv: (-kv[0][0], feas.index(kv[0][1])))}
  amber = set(d["amber"])
  k = 0
  for (i, j), tss in cells.items():
    for n, ts in enumerate(tss):
      x = gx + j * cw + 8 + (n % 3) * 40
      y = gy + i * ch + 26 + (n // 3) * 16
      col = AMBER if ts in amber else NAVY
      b.append(g(f"{tl.show(4.6 + k * 0.35)} fin", [f'<rect x="{x}" y="{y - 11}" width="38" height="15" rx="7" fill="{col}"/>', t(x + 19, y, ts, 9.5, "#fff", 700, "middle")]))
      k += 1
  # threshold outline (risk >= 3)
  th = (f'M{gx},{gy} H{gx + 3 * cw} V{gy + ch} H{gx + 2 * cw} V{gy + 2 * ch} H{gx + cw} V{gy + 3 * ch} H{gx} Z')
  b.append(g(f"{tl.show(11.8)} fin", [f'<path d="{th}" fill="none" stroke="{CS}" stroke-width="3"/>', t(gx + 4 * cw, gy - 14, "outlined: treat (risk ≥ 3)", 11, CS, 700, "end")]))
  # treatments
  ty = 430
  tr = d["treat"]
  opts = [("Reduce", "add a control", f"all {d['ts']}" if len(tr["Reduce"]) == d["ts"] else ", ".join(tr["Reduce"])),
          ("Avoid", "remove the feature", ", ".join(tr["Avoid"]) + " too" if tr["Avoid"] else "none"),
          ("Share", "transfer it, e.g. insurance", ", ".join(tr["Share"]) or "none"),
          ("Retain", "accept it, with a reason", ", ".join(tr["Retain"]) + " may be" if tr["Retain"] else "none")]
  for n, (o, what, ours) in enumerate(opts):
    x = 24 + n * 168
    b.append(g(f"{tl.show(17.2 + n * 0.6)} fin", [f'<rect x="{x}" y="{ty}" width="160" height="78" rx="10" fill="#fff" stroke="{CS}" stroke-width="{2.5 if n == 0 else 1.5}"/>',
                                                   t(x + 12, ty + 22, o, 14, CS, 800), t(x + 12, ty + 42, what, 11.5, NAVY), t(x + 12, ty + 64, ours, 11.5, MID, 600)]))
  b.append(g(f"{tl.show(23.6)} fin", [f'<rect x="24" y="526" width="{W - 110}" height="92" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 548, f"{d['ts45']} scenarios at risk 4–5 drive {d['csg']} cybersecurity goals, CSG-01…CSG-{d['csg']:02d} (WP-C-10).", 12.5, NAVY, 700),
             f'<rect x="40" y="560" width="30" height="13" rx="6" fill="{AMBER}"/>', t(78, 571, f"{', '.join(d['amber'])}: fix built in the reference build, not verified, not re-rated.", 12, NAVY),
             t(40, 600, "No scenario has moved on the map yet.", 12, MID, 400, "start", True)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "The risk map: what must be treated (animated)",
             f"All {d['ts']} threat scenarios of WP-C-09 on the impact by feasibility matrix with its risk values 1 to 5. Risk 3 or more must be treated; 4 or 5 drives a cybersecurity goal: {d['ts45']} scenarios drive {d['csg']} goals. Treatments: reduce, avoid, share, retain. Built in the reference build but not verified: {', '.join(d['amber'])}.", tl, b)


# ------------------------------------------------------------------ 5 goal to control to evidence
def goal_to_evidence():
  tl, h = Timeline(30.0), 680
  b = [t(24, 38, "From goal to control to evidence", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "A goal says what must hold; its CAL says how much rigour it gets"),
                 (5.0, "Requirements say how; the control is built into the firmware"),
                 (10.4, "Tests show it works; a penetration tester tries to break it"),
                 (16.0, "The results become evidence for a claim of the cybersecurity case"),
                 (21.8, "The same lock is a safety requirement: one control, two cases")])
  rows = [
    (0.5, "GOAL · CSG-01 · CAL 3 (of 4)", CS, ["No unauthenticated command may put the panda's", "safety envelope into an unsafe configuration"], None),
    (5.2, "REQUIREMENT · CSR-C-01", CS, ["The panda firmware enforces the Toyota safety mode and", "rejects any change the reference configuration does not allow"], None),
    (7.6, "CONTROL · panda board/reference_lock.h", NAVY, ["Built into every reference release", "(release_variant.sh: reference by default)"], ("built", GRN)),
    (10.6, "VERIFICATION · host tests panda/tests/reference_lock", NAVY, ["Run in CI on every change (safety.yaml)", "no run yet recorded as evidence (CSn-21)"], ("partial", AMBER)),
    (13.0, "VALIDATION · penetration test (WP-V-06)", NAVY, ["Command fuzzing and mode-lock attack", "not executed; no independent tester engaged"], ("missing", RED)),
    (16.2, "CLAIM · CG2.1 in the cybersecurity case (WP-K-03)", CS, ["Safety configuration integrity holds", "draft: not yet supported by verified evidence"], ("open", MID)),
  ]
  y = 110
  for i, (t0, tag, c, lines, st) in enumerate(rows):
    yy = y + i * 80
    o = card(80, yy, W - 160, 68, tag, c, lines, size=12)
    if i:
      o.append(f'<line x1="{W / 2}" y1="{yy - 12}" x2="{W / 2}" y2="{yy}" stroke="{CS}" stroke-width="2.5"/>')
    if st:
      ch, w = chip(W - 80 - 14 - (len(st[0]) * 6.3 + 16), yy + 22, st[0], st[1])
      o += ch
    b.append(g(f"{tl.show(t0)} fin", o))
  # CAL explainer
  b.append(g(f"{tl.show(1.6, 4.8)} tr", [t(W - 76, y + 20, "", 1)]))
  b.append(g(f"{tl.show(22.0)} fin", [f'<rect x="24" y="594" width="{W - 110}" height="66" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 616, "The lock is also TSR-512 of the safety requirements: built once, verified once,", 12.5, NAVY, 700),
             t(40, 636, "cited by both the safety case and the cybersecurity case.", 12.5, NAVY, 700),
             t(40, 654, "CAL comes from the risk and the attack vector (WP-C-10): risk 5 with safety impact gives CAL 3.", 11, MID, 400, "start", True)]))
  b.append(stick(W - 40, h - 14, "point"))
  return svg(h, "From goal to control to evidence (animated)",
             "CSG-01, CAL 3: no unauthenticated command may put the panda safety envelope into an unsafe configuration. Requirement CSR-C-01. Control: board/reference_lock.h, built into every reference release. Verification: host tests run in CI, no run recorded as evidence (partial). Validation: penetration test not executed, no tester engaged (missing). Claim CG2.1 of the cybersecurity case: open. The same lock is TSR-512 of the safety requirements.", tl, b)



def arrow(x1, y, x2, col, both=False):
  o = [f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{col}" stroke-width="3"/>']
  d = 1 if x2 > x1 else -1
  o.append(f'<path d="M{x2},{y} l{-8 * d},-6 v12 z" fill="{col}"/>')
  if both:
    o.append(f'<path d="M{x1},{y} l{8 * d},-6 v12 z" fill="{col}"/>')
  return o


# ------------------------------------------------------------------ 6 where safety and security meet
def bars(x, y, items, unit=24):
  o = []
  for n, lab, col in items:
    o += [f'<rect x="{x}" y="{y}" width="{max(n, 1) * unit}" height="16" rx="4" fill="{col}"/>', t(x + max(n, 1) * unit + 6, y + 13, f"{n} {lab}", 11.5, NAVY, 700)]
    x += max(n, 1) * unit + 90
  return o


def meet(d):
  tl, h = Timeline(30.0), 660
  b = [t(24, 38, "Where safety and security meet", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "A measure on one side can help, hurt or hold up the other (hatara/)"),
                 (2.6, "Help: one mechanism closes a hazard and a threat"),
                 (7.4, "Hurt: a safety measure opens a door for an attacker"),
                 (12.2, "Hurt: a security measure can cause a hazard"),
                 (17.0, "Hold up: a safety goal holds against attackers only if a security goal does"),
                 (22.4, "So the HARA and the TARA are checked against each other")])
  b.append(g(f"{tl.show(0.4)} fin", [t(150, 112, "SAFETY SIDE", 11, FS, 800, "middle"), t(W - 150, 112, "SECURITY SIDE", 11, CS, 800, "middle")]))
  rows = [
    (2.8, "HELP · IX-04", GRN, "One lock serves both", ["Envelope must run Toyota mode", "TSR-512 (SG-01…SG-07)"], ["No SoC command may change it", "CSR-C-01 (TS-02, risk 5)"], "both",
     "Verify it once, for both. Built, not verified."),
    (7.6, "HURT · IX-01", RED, "A recovery path is an attack path", ["If the panda will not boot,", "a recovery path revives it"], ["The same route can load other", "firmware (TS-03, risk 5)"], "right",
     "Authenticate the recovery or remove it (CSR-C-05: not built)."),
    (12.4, "HURT · IX-03", RED, "A rejected frame is a lost function", ["Stopping control unannounced", "is silent loss (H-02, H-06)"], ["Counter and CRC checks reject", "forged frames (CSR-C-09)"], "left",
     "A rejection must end in an announced take-over request."),
    (17.2, "HOLD UP · IX-10", AMBER, "Firmware integrity holds up SG-01…SG-07", ["SG-01…SG-07 rest on the", "panda firmware"], ["CSG-01 and CSG-02 protect", "that firmware"], "left",
     "Until both are met, those goals do not hold against an attacker on the SoC."),
  ]
  y0 = 124
  for i, (t0, tag, col, title, sa, se, dirn, so) in enumerate(rows):
    y = y0 + i * 104
    o = [f'<rect x="24" y="{y}" width="{W - 48}" height="96" rx="12" fill="#fff" stroke="{col}" stroke-width="2"/>',
         f'<rect x="24" y="{y}" width="{len(tag) * 7 + 20}" height="22" rx="11" fill="{col}"/>', t(34, y + 15, tag, 11, "#fff", 800),
         t(len(tag) * 7 + 56, y + 16, title, 13, NAVY, 700)]
    o += [t(40, y + 46, sa[0], 12, NAVY, 600), t(40, y + 62, sa[1], 11.5, MID)]
    o += [t(W - 40, y + 46, se[0], 12, NAVY, 600, "end"), t(W - 40, y + 62, se[1], 11.5, MID, 400, "end")]
    if dirn == "both":
      o += arrow(300, y + 52, 420, col, both=True)
    elif dirn == "right":
      o += arrow(300, y + 52, 420, col)
    else:
      o += arrow(420, y + 52, 300, col)
    o += [t(40, y + 86, "→ " + so, 11.5, col if col != AMBER else "#8a5a12", 700)]
    b.append(g(f"{tl.show(t0)} fin", o))
  b.append(g(f"{tl.show(22.6)} fin", [f'<rect x="24" y="544" width="{W - 110}" height="96" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 566, f"LionDriver (hatara/): {d['ix']} interactions", 13, NAVY, 700),
             *bars(40, 578, [(d["ix_hurt"], "hurt", RED), (d["ix_help"], "help", GRN), (d["ix_hold"], "hold up", AMBER)]),
             t(40, 616, "A tool checks every interaction against the HARA and the TARA; one found a threat", 11.5, NAVY),
             t(40, 632, "the TARA had no damage scenario for (IX-11), since closed.", 11.5, NAVY)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "Where safety and security meet (animated)",
             f"Four interactions of hatara/: one lock serves both (IX-04); a recovery path is an attack path (IX-01); a rejected frame is a lost function unless it ends in a take-over request (IX-03); firmware integrity holds up SG-01 to SG-07 (IX-10). Of {d['ix']} interactions, {d['ix_hurt']} hurt, {d['ix_help']} help and {d['ix_hold']} hold up.", tl, b)


# ------------------------------------------------------------------ 7 after release
def after_release():
  tl, h = Timeline(32.0), 660
  b = [t(24, 38, "After release: watch, fix, tell", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "Security work does not end at release: new attacks appear (WP-O-05)"),
                 (3.6, "Example: a researcher finds a way around the safety-mode lock"),
                 (21.6, "Fixes ship as updates, which must be safe and secure themselves"),
                 (26.4, "LionDriver today: the process is written, not running")])
  # sources
  srcs = ["upstream comma repos", "CVE / advisory feeds", "reports (SECURITY.md)", "field: tampering signs"]
  b.append(g(f"{tl.show(0.6)} fin", [t(24, 116, "WATCH", 11, MID, 800)]))
  x = 80
  for i, s in enumerate(srcs):
    ch, w = chip(x, 120, s, CS if i == 2 else NAVY, 10.5)
    b.append(g(f"{tl.show(0.9 + i * 0.4)} fin", ch))
    x += w + 8
  # timeline
  ty = 200
  steps = [(3.8, "day 0", "Report arrives through the private channel", "SECURITY.md"),
           (5.6, "≤ 3 days", "Acknowledged to the reporter", ""),
           (7.4, "≤ 2 days", "Evaluated: it can lead to unintended steering (DS-01)", "safety-relevant: E4 = yes"),
           (9.6, "Critical", "Risk 5 or a path to a safety goal: the top severity", "§4.2"),
           (11.6, "≤ 24 h", "Safety manager decides: stop-use notice to every user", "no technical detail"),
           (14.0, "≤ 14 days", "Fix release, verified like any change (WP-P-02)", ""),
           (16.2, "staged", "Bench and reference car, then 10 %, then everyone", "stages may shrink to 24 h"),
           (18.4, "≤ 90 days", "Advisory published with the fix, reporter credited", "")]
  for i, (t0, when, what, note) in enumerate(steps):
    y = ty + i * 40
    o = [f'<circle cx="110" cy="{y}" r="7" fill="{CS}"/>', t(94, y + 4, when, 11.5, CS, 800, "end"), t(128, y + 5, what, 12.5, NAVY, 600)]
    if note:
      o.append(t(W - 40, y + 5, note, 11, MID, 400, "end", True))
    if i < len(steps) - 1:
      o.append(f'<line x1="110" y1="{y + 7}" x2="110" y2="{y + 33}" stroke="{CS}" stroke-width="2" opacity="0.4"/>')
    b.append(g(f"{tl.show(t0)} fin", o))
  b.append(g(f"{tl.show(3.6, 21.2)} tr", [t(24, 178, "EXAMPLE, NOT A REAL REPORT", 11, AMBER, 800)]))
  # update box
  uy = 528
  b.append(g(f"{tl.show(21.8, 26.2)} tr", [f'<rect x="24" y="{uy}" width="{W - 110}" height="104" rx="12" fill="#fff" stroke="{CS}" stroke-width="2"/>',
             t(40, uy + 24, "A secure update (§6.2)", 13, CS, 700),
             t(40, uy + 46, "Signed manifest checked on the device; offroad only; parameters checked;", 12, NAVY),
             t(40, uy + 66, "rollback only to a release whose evidence holds. A new model is a SOTIF", 12, NAVY),
             t(40, uy + 86, "change, new panda firmware an ISO 26262 change: each needs evidence.", 12, NAVY)]))
  b.append(g(f"{tl.show(26.6)} fin", [f'<rect x="24" y="{uy}" width="{W - 110}" height="104" rx="12" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, uy + 24, "LionDriver today (WP-O-05: draft, not running, GAP-28)", 13, NAVY, 700),
             t(40, uy + 46, "SECURITY.md is published; WP-O-05 records no monitoring, intake or incident yet.", 12, NAVY),
             t(40, uy + 66, "Signed updates not built (CSR-121): automatic updates are off; install by hand", 12, NAVY),
             t(40, uy + 86, "and compare hashes with the release record.", 12, NAVY)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "After release: watch, fix, tell (animated)",
             "Monitoring sources: upstream repositories, advisory feeds, reports under SECURITY.md, field signs of tampering. An example report, not a real one, through WP-O-05: acknowledged within 3 working days, evaluated within 2, rated Critical, a stop-use decision within 24 hours, a fix within 14 days, a staged rollout, an advisory within 90 days. Secure updates: signed manifest, offroad, parameters checked, rollback only to a release whose evidence holds. Today the process is written but not running (GAP-28); signed updates are not built, so automatic updates are off.", tl, b)


def render(root: Path = ROOT) -> dict[str, str]:
  d = data(root)
  figs = (third_question(), one_threat(), more_than_safety(d), how_hard(d), risk_map(d), goal_to_evidence(), meet(d), after_release())
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
