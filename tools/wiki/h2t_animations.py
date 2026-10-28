#!/usr/bin/env python3
"""Render the animated explainers of the wiki page "From hazard to test" as SVG.

One real chain, followed from the item to the tests: SG-01 (no steering the driver did not ask for).

  h2t-item.svg        the item, its boundary, functions, ODD and the assumptions of use on the outside (WP-C-01);
  h2t-hara.svg        the hazardous event HE-01.4 rated S3 E4 C2, ASIL C, and the safety goal SG-01 (WP-C-03);
  h2t-what-how.svg    FSR-01.04 (the what, WP-C-04) and TSR-105 (the how, WP-S-02);
  h2t-allocation.svg  TSR-105 to software (SWSR-105), and the watchdog that keeps the check running to hardware
                      (FSR-01.09, TSR-501, HWSR-501);
  h2t-engineers.svg   the firmware check and the watchdog settings, the known gap, and their tests;
  h2t-mechanism.svg   the gate (SM-04) at work, with and without it, and the watchdog: an illustration;
  h2t-testing.svg     one goal, several kinds of test, each with its status from the records, and how the results
                      become evidence for the claim G1.1.3.

They loop with CSS and need no script; a viewer who asks for reduced motion sees the final frame. Every phrase that
quotes or summarises a record is checked against it at render time (`problems()`), and the evidence statuses are
read from `assurance/case-records`. The code excerpts are checked against opendbc and panda when those submodules are checked
out (the wiki workflow does not check them out; the assurance workflow's checks cover them). build_wiki.py renders
the figures next to the pages at each sync (nothing is committed).

Usage: python3 tools/wiki/h2t_animations.py [--out DIR] [--check]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from animations import GRN, LIGHT, MID, NAVY, RED, RED_BG, W, Timeline, g, norm, stick, svg, t  # noqa: E402
from fta_animations import blk, wire  # noqa: E402

NAMES = ("h2t-item.svg", "h2t-hara.svg", "h2t-what-how.svg", "h2t-allocation.svg", "h2t-engineers.svg",
         "h2t-mechanism.svg", "h2t-testing.svg")
AMBER, BLUE, VIOLET, ORANGE, TEAL, BOUND = "#b7791f", "#2a78d6", "#6250d6", "#c2410c", "#0f766e", "#b45309"

C01 = Path("assurance") / "02-concept" / "WP-C-01-item-definition.md"
C02 = Path("assurance") / "02-concept" / "WP-C-02-odd-and-intended-functionality.md"
C03 = Path("assurance") / "02-concept" / "WP-C-03-hara.md"
C04 = Path("assurance") / "02-concept" / "WP-C-04-functional-safety-concept.md"
C08 = Path("assurance") / "02-concept" / "WP-C-08-driver-hmi-misuse-analysis.md"
S02 = Path("assurance") / "03-system" / "WP-S-02-technical-safety-requirements.md"
S03 = Path("assurance") / "03-system" / "WP-S-03-technical-safety-concept-architecture.md"
W02 = Path("assurance") / "05-software" / "WP-W-02-software-safety-requirements.md"
H01 = Path("assurance") / "04-hardware" / "WP-H-01-hardware-safety-requirements.md"
V05 = Path("assurance") / "06-validation" / "WP-V-05-fault-injection.md"
LATERAL = Path("opendbc_repo") / "opendbc" / "safety" / "lateral.h"
WATCHDOG = Path("panda") / "board" / "drivers" / "hw_watchdog.h"
CASE = Path("assurance") / "case"

# (file, phrase): every record the figures quote or summarise
SOURCES = [
  (C01, "| F-01 | Lateral control (lane centring)"), (C01, "| F-02 | Longitudinal control (ACC"),
  (C01, "| F-03 | Engagement and mode management"), (C01, "| F-04 | Driver monitoring"),
  (C01, "| F-05 | Driver information and warnings"), (C01, "| F-08 | Safety envelope"),
  (C01, "| F-06 | Forward collision warning"), (C01, "| F-07 | Lane departure warning"),
  (C01, "| AOU-01 | The Toyota EPS limits the torque applied for LKA requests to a level a normal driver can overpower"),
  (C01, "| AOU-02 | A normal driver can override full LKA torque"),
  (C02, "limited-access highways only"),
  (C03, "| HE-01.4 | Torque while not engaged, OS-13 manual driving on any road"),
  (C03, "Unexpected steering disturbance during manual driving | S3 | E4 | C2 ⚠ | **C**"),
  (C03, "| HE-01.4 | AOU-01, AOU-02 | C | D |"),
  (C03, "The item shall not cause lateral motion of the vehicle that exceeds what the driver can control, including any steering actuation while the item is not engaged"),
  (C04, "| FSR-01.04 | The envelope shall block any non-zero LKA torque or set steer-request bit while lateral authority is not granted."),
  (C04, "| FSR-01.09 | The safety MCU shall detect its own execution faults"),
  (C08, "≥ 20 valid subjects; 20/20 keep the vehicle in its lane"),
  (S02, "| TSR-105 | While lateral authority is not granted, the envelope shall reject every `0x2E4` frame with non-zero torque **or** with STEER_REQUEST set. | B‡ | FSR-01.04 | P-SW | GATE | per frame |"),
  (S02, "STEER_REQUEST = 1 with zero torque is accepted while not engaged"),
  (S02, "| TSR-105, 106, 107 | FSR-01.04 | SG-01 |"),
  (S02, "| TSR-501 | The safety MCU shall be supervised by an independent hardware watchdog"),
  (S03, "| SM-04 | Authority gating (PCM edge, brake, gas, steer request) | actuation when not engaged"),
  (W02, "| SWSR-105 | While lateral authority is not granted, the lateral check shall reject every `0x2E4` frame with non-zero torque or with STEER_REQUEST = 1. | B‡ | TSR-105 | U-SAF-LAT |"),
  (H01, "| HWSR-501 | The safety MCU shall be supervised by a watchdog whose clock source and counter are independent of the CPU core clock tree"),
  (H01, "**Implemented, not verified on hardware**"),
  (V05, "| VS-FI-01 | Corrupted frame (bad checksum, wrong length)"),
  (V05, "| VS-FI-01 | — | — | — | — | — | — | — | — | **Not yet executed**"),
]
CODE = ["bool torque_requested = desired_torque != 0;", "if (!controls_allowed && torque_requested) {", "  violation = true;", "}"]
WDG = ["#define HW_WATCHDOG_PRESCALER 0U", "#define HW_WATCHDOG_RELOAD 719U", "#define HW_WATCHDOG_WINDOW 679U"]
CODE_SOURCES = [(LATERAL, CODE), (WATCHDOG, WDG + ["nominal\n// timeout is 90 ms", "(5 ms nominal with WINR = 679)"])]
CLAIM, EVIDENCE = "G1.1.3", ["Sn-10", "Sn-12"]


def problems(root: Path = ROOT) -> list[str]:
  errs, cache = [], {}
  for path, phrase in SOURCES:
    if path not in cache:
      p = root / path
      cache[path] = norm(p.read_text(encoding="utf-8")) if p.exists() else ""
    if norm(phrase) not in cache[path]:
      errs.append(f"{path}: phrase the hazard-to-test figures rely on is gone: {phrase!r}")
  for path, lines in CODE_SOURCES:
    p = root / path
    if p.exists():
      text = norm(p.read_text(encoding="utf-8"))
      errs += [f"{path}: code the hazard-to-test figures show is gone: {line!r}" for line in lines if norm(line) not in text]
  try:
    claim, ev = case(root)
  except (OSError, yaml.YAMLError, KeyError, StopIteration) as e:
    return errs + [f"{CASE}: records cannot be read: {e}"]
  missing = [e for e in EVIDENCE if e not in claim["evidence_refs"]]
  if missing:
    errs.append(f"{CASE}: {CLAIM} no longer cites {', '.join(missing)}")
  return errs


def case(root: Path = ROOT):
  claims = {}
  for f in sorted((root / CASE / "claims").glob("*.yaml")):
    for c in yaml.safe_load(f.read_text(encoding="utf-8")):
      claims[c["id"]] = c
  ev = {e["id"]: e for e in yaml.safe_load((root / CASE / "evidence" / "evidence.yaml").read_text(encoding="utf-8"))}
  return claims[CLAIM], {e: ev[e] for e in EVIDENCE}


def caps(tl, steps):
  out = []
  for i, (t0, cap) in enumerate(steps):
    t1 = steps[i + 1][0] - 0.2 if i + 1 < len(steps) else None
    out.append(g(f"{tl.show(t0, t1)} {'fin' if t1 is None else 'tr'}", [f'<rect x="24" y="66" width="{W - 48}" height="28" rx="6" fill="{NAVY}"/>', t(36, 85, cap, 13, "#fff", 600)]))
  return out


def card(x, y, w, h, tag, tagcol, lines, fill="#fff", size=12.5):
  o = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{tagcol}" stroke-width="2"/>', t(x + 14, y + 20, tag, 11, tagcol, 700)]
  for i, line in enumerate(lines):
    o.append(t(x + 14, y + 42 + i * 18, line, size, NAVY, 600 if i == 0 else 400))
  return o


def chip(x, y, label, col, size=11):
  w = len(label) * 6.6 + 18
  return [f'<rect x="{x}" y="{y - 15}" width="{w:.0f}" height="22" rx="11" fill="{col}"/>', t(round(x + w / 2), y, label, size, "#fff", 700, "middle")], w


def scale(x, y, letter, levels, pick, col, word, t0, tl):
  o = [t(x, y, letter, 22, NAVY, 800)]
  for i, lv in enumerate(levels):
    o.append(f'<rect x="{x + 30 + i * 44}" y="{y - 20}" width="40" height="26" rx="5" fill="#f1f3f7" stroke="{LIGHT}"/>')
    o.append(t(x + 50 + i * 44, y - 2, lv, 12, MID, 700, "middle"))
  hit = [g(f"{tl.show(t0)} fin", [f'<rect x="{x + 30 + pick * 44}" y="{y - 20}" width="40" height="26" rx="5" fill="{col}"/>',
                                   t(x + 50 + pick * 44, y - 2, levels[pick], 12, "#fff", 800, "middle"),
                                   t(x + 30 + len(levels) * 44 + 10, y - 2, word, 12.5, NAVY, 600)])]
  return [g(f"{tl.show(t0 - 0.6)} fin", o)] + hit

# ---------------- 0a item
def item():
  tl, h = Timeline(20.0), 640
  b = [t(24, 38, "The item: what we are making safe", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "1 · The item: the parts we are responsible for (WP-C-01)"), (3.6, "2 · Outside it: the car, the driver and the road"),
                 (7.0, "3 · What it does: its functions"), (11.0, "4 · Where it may be used: its operational design domain"),
                 (14.0, "5 · What we assume of the outside: assumptions of use")])
  dy = 112
  inside = [f'<rect x="150" y="{dy}" width="410" height="196" rx="12" fill="#fffaf2" stroke="{BOUND}" stroke-width="1.8" stroke-dasharray="7 5"/>',
            t(162, dy + 16, "ITEM BOUNDARY · LD-SDA", 10.5, BOUND, 700)]
  inside += blk(166, dy + 28, 92, 44, "Cameras", "E-04") + blk(276, dy + 24, 130, 56, "E-01 SoC", "openpilot") + blk(424, dy + 24, 122, 56, "E-03 panda", "safety envelope", "#fff6ef", ORANGE)
  inside += blk(166, dy + 122, 112, 44, "Display, speaker", "E-04") + blk(424, dy + 122, 122, 44, "E-05 harness", "switches, CAN")
  inside += [wire([(258, dy + 50), (276, dy + 50)]), wire([(406, dy + 52), (424, dy + 52)]), wire([(485, dy + 80), (485, dy + 122)]),
             wire([(340, dy + 80), (340, dy + 100), (222, dy + 100), (222, dy + 122)])]
  b.append(g(f"{tl.show(0.5)} fin", inside))
  out = blk(24, dy + 30, 100, 140, "Driver", "outside", "#f1f3f7") + blk(588, dy + 10, 108, 50, "EPS", "steering", "#f1f3f7")
  out += blk(588, dy + 74, 108, 50, "PCM / ACC", "engine, brakes", "#f1f3f7") + blk(588, dy + 138, 108, 50, "Cluster", "cruise light", "#f1f3f7")
  out += [wire([(546, dy + 144), (570, dy + 144), (570, dy + 35), (588, dy + 35)]), wire([(570, dy + 99), (588, dy + 99)]), wire([(570, dy + 144), (588, dy + 163)]),
          wire([(166, dy + 144), (124, dy + 144)])]
  b.append(g(f"{tl.show(3.8)} fin", out))
  fy = dy + 222
  fs = [("F-01 lane centring", BLUE), ("F-02 ACC", BLUE), ("F-03 engagement", VIOLET), ("F-04 driver monitoring", TEAL),
        ("F-05 warnings", TEAL), ("F-08 safety envelope", ORANGE)]
  x, yy = 24, fy
  for i, (f, col) in enumerate(fs):
    if i == 4:
      x, yy = 24, fy + 28
    c, w = chip(x, yy, f, col)
    b.append(g(f"{tl.show(7.2 + i * 0.4)} fin", c))
    x += w + 6
  fy += 28
  b.append(g(f"{tl.show(9.8)} fin", [t(24, fy + 26, "plus F-06 forward collision warning, F-07 lane departure warning, F-09 logging and updates", 11, MID, 400, "start", True)]))
  ry = fy + 52
  b.append(g(f"{tl.show(11.2)} fin", [f'<path d="M24,{ry} h{W - 48}" stroke="{TEAL}" stroke-width="3"/>', f'<path d="M24,{ry + 36} h{W - 48}" stroke="{TEAL}" stroke-width="3"/>',
             f'<path d="M24,{ry + 18} h{W - 48}" stroke="{TEAL}" stroke-width="2" stroke-dasharray="14 10"/>',
             t(24, ry + 58, "ODD: limited-access highways only (WP-C-02). Anywhere else is outside what we claim.", 12.5, NAVY, 600)]))
  b.append(g(f"{tl.show(14.2)} fin", [f'<rect x="24" y="{ry + 74}" width="{W - 110}" height="72" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, ry + 96, "AOU-01: the EPS limits steering torque so a normal driver can overpower it.", 12.5, NAVY, 600),
             t(40, ry + 116, "AOU-02: a normal driver can override full steering torque.", 12.5, NAVY, 600),
             t(40, ry + 136, "The item is analysed; the outside is assumed, and the assumptions must be verified.", 11.5, MID)]))
  b.append(stick(W - 40, h - 14, "point"))
  return svg(h, "The item: what we are making safe (animated)", "The item boundary of WP-C-01 with the cameras, the SoC running openpilot, the panda safety envelope, the display and speaker and the harness inside; the driver, the EPS, the PCM and the cluster outside; its functions F-01 to F-09; its ODD, limited-access highways only; and the assumptions of use AOU-01 and AOU-02 about the outside.", tl, b)

# ---------------- 1 what vs how
def what_how():
  tl, h = Timeline(20.0), 640
  b = [t(24, 38, "The what and the how", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "1 · The safety goal says what must never happen"), (2.8, "2 · A functional requirement (FSR) says WHAT the item must do"),
                 (7.6, "3 · A technical requirement (TSR) says HOW this system does it"), (13.4, "4 · One FSR, several TSRs; each TSR names its element, signal and timing")])
  b.append(g(f"{tl.show(0.5)} fin", card(24, 108, W - 48, 56, "SAFETY GOAL · SG-01 · ASIL C", NAVY,
             ["No lateral motion the driver can't control, including any steering while not engaged."])))
  b.append(g(f"{tl.show(3.0)} fin", [wire([(W / 2, 164), (W / 2, 180)])] + card(24, 180, W - 48, 92, "FSR-01.04 · WHAT", BLUE,
             ["The envelope shall block any non-zero LKA torque or set steer-request bit", "while lateral authority is not granted."], "#f3f7fd")
             + [t(40, 262, "No design yet: it says what must be true, not which signal, how fast or in which part.", 11.5, MID, 400, "start", True)]))
  b.append(g(f"{tl.show(7.8)} fin", [wire([(W / 2, 272), (W / 2, 288)])] + card(24, 288, W - 48, 76, "TSR-105 · HOW", ORANGE,
             ["While lateral authority is not granted, the envelope shall reject every 0x2E4", "frame with non-zero torque or with STEER_REQUEST set."], "#fff6ef")))
  attrs = [("element: panda software", ORANGE), ("mechanism: gate", ORANGE), ("timing: every frame", ORANGE), ("verified by: SIL, HIL tests", ORANGE)]
  x = 24
  for i, (a, col) in enumerate(attrs):
    c, w = chip(x, 392, a, col)
    b.append(g(f"{tl.show(9.6 + i * 0.6)} fin", c))
    x += w + 6
  b.append(g(f"{tl.show(13.6)} fin", [t(24, 432, "FSR-01.04 is met by three TSRs:", 13, NAVY, 700)]
             + chip(24, 462, "TSR-105 reject torque frames", ORANGE)[0] + chip(250, 462, "TSR-106 steer-request tolerance", ORANGE)[0]
             + chip(484, 462, "TSR-107 reject angle frames", ORANGE)[0]))
  b.append(g(f"{tl.show(15.6)} fin", [f'<rect x="24" y="492" width="{W - 110}" height="72" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 514, "WHAT: the behaviour that keeps the goal true (FSR, WP-C-04).", 13, BLUE, 700),
             t(40, 534, "HOW: the element, the signal and the timing that make it so (TSR, WP-S-02).", 13, ORANGE, 700),
             t(40, 554, "Change the design and the TSRs change; the FSR stays.", 12, MID)]))
  b.append(stick(W - 40, h - 60, "point"))
  return svg(h, "The what and the how (animated)", "The safety goal SG-01; the functional safety requirement FSR-01.04, what the item must do: block any non-zero LKA torque or set steer-request bit while lateral authority is not granted; the technical safety requirement TSR-105, how: the envelope rejects every 0x2E4 frame with non-zero torque or STEER_REQUEST set, in the panda software, as a gate, on every frame; FSR-01.04 is met by TSR-105, 106 and 107.", tl, b)

# ---------------- 2 allocation
def alloc():
  tl, h = Timeline(22.0), 660
  b = [t(24, 38, "Allocation: who owns each requirement", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "1 · A TSR is allocated to an element of the architecture"), (3.6, "2 · Software: a software requirement for one unit"),
                 (8.6, "3 · But the gate only works while its chip is running"), (12.2, "4 · Hardware: a requirement for an independent watchdog"),
                 (16.6, "5 · Every requirement ends up owned by one software unit or hardware part")])
  b.append(g(f"{tl.show(0.5)} fin", card(24, 108, 330, 76, "TSR-105 · HOW", ORANGE, ["Reject every steering frame with", "torque while not engaged."], "#fff6ef")))
  # the panda split into layers
  px = 400
  b.append(g(f"{tl.show(1.4)} fin", [f'<rect x="{px}" y="108" width="296" height="236" rx="12" fill="#fff" stroke="{ORANGE}" stroke-width="2"/>',
             t(px + 14, 128, "E-03 panda safety MCU", 13, NAVY, 700),
             f'<rect x="{px + 14}" y="140" width="268" height="86" rx="8" fill="#f3f7fd" stroke="{BLUE}"/>', t(px + 26, 160, "SOFTWARE · firmware", 11, BLUE, 700),
             t(px + 26, 180, "unit U-SAF-LAT (the lateral check)", 11.5, NAVY),
             f'<rect x="{px + 14}" y="236" width="268" height="96" rx="8" fill="#f5f3fd" stroke="{VIOLET}"/>', t(px + 26, 256, "HARDWARE · STM32H7 chip", 11, VIOLET, 700),
             t(px + 26, 276, "core, clock, IWDG1 watchdog (own LSI clock)", 11.5, NAVY)]))
  b.append(g(f"{tl.show(3.8)} fin", [f'<path d="M354,146 C380,146 380,196 {px + 14},196" fill="none" stroke="{BLUE}" stroke-width="2"/>',
             f'<rect x="{px + 26}" y="190" width="244" height="28" rx="6" fill="{BLUE}"/>', t(px + 36, 209, "SWSR-105 · reject torque or steer req.", 11.5, "#fff", 700)]))
  b.append(g(f"{tl.show(4.6)} fin", card(24, 200, 330, 92, "SWSR-105 · SOFTWARE", BLUE, ["The lateral check shall reject every", "0x2E4 frame with non-zero torque or", "STEER_REQUEST = 1 while not granted."], "#f3f7fd", 12)))
  b.append(g(f"{tl.show(8.8)} fin", card(24, 308, 330, 92, "FSR-01.09 → TSR-501", NAVY, ["The MCU detects its own hang and", "enters the safe state; an independent", "watchdog supervises it."], "#fff", 12)))
  b.append(g(f"{tl.show(12.4)} fin", [f'<path d="M354,354 C380,354 380,300 {px + 14},300" fill="none" stroke="{VIOLET}" stroke-width="2"/>',
             f'<rect x="{px + 26}" y="290" width="244" height="28" rx="6" fill="{VIOLET}"/>', t(px + 36, 309, "HWSR-501 · independent watchdog", 11.5, "#fff", 700)]))
  b.append(g(f"{tl.show(13.0)} fin", card(24, 416, 330, 92, "HWSR-501 · HARDWARE", VIOLET, ["A watchdog with its own clock and", "counter supervises the MCU; expiry", "forces a reset (to the safe state)."], "#f5f3fd", 12)))
  b.append(g(f"{tl.show(16.8)} fin", [f'<rect x="{px}" y="360" width="296" height="148" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(px + 14, 384, "Software owns the check;", 13, NAVY, 700), t(px + 14, 404, "hardware owns the guarantee", 13, NAVY, 700),
             t(px + 14, 424, "that the check keeps running.", 13, NAVY, 700),
             t(px + 14, 452, "Each has its own requirement, its", 11.5, MID), t(px + 14, 470, "own engineer and its own tests.", 11.5, MID)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "Allocation: who owns each requirement (animated)", "TSR-105 is allocated to the panda firmware as SWSR-105 in the lateral check unit; the check only works while its chip runs, so FSR-01.09 and TSR-501 allocate an independent watchdog to the hardware as HWSR-501.", tl, b)

# ---------------- 3 how engineers meet them
CODE = ["bool torque_requested = desired_torque != 0;", "if (!controls_allowed && torque_requested) {", "  violation = true;", "}"]
WDG = ["#define HW_WATCHDOG_PRESCALER 0U", "#define HW_WATCHDOG_RELOAD 719U", "#define HW_WATCHDOG_WINDOW 679U"]
def code_panel(x, y, w, lines, title):
  o = [f'<rect x="{x}" y="{y}" width="{w}" height="{36 + 20 * len(lines)}" rx="8" fill="#0f1b33"/>', t(x + 12, y + 20, title, 10.5, "#9fb3d1", 700)]
  for i, l in enumerate(lines):
    o.append(f'<text x="{x + 12}" y="{y + 42 + i * 20}" font-family="ui-monospace, Menlo, Consolas, monospace" font-size="12.5" fill="#e8eef8" xml:space="preserve">{l.replace("&", "&amp;").replace("<", "&lt;")}</text>')
  return o
def engineers():
  tl, h = Timeline(22.0), 660
  b = [t(24, 38, "How the engineers meet them", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "1 · Software: the check, in the firmware"), (5.0, "2 · Honest about the gap the review found"),
                 (8.4, "3 · Hardware: the watchdog's settings"), (13.4, "4 · Each is tested against its requirement"),
                 (17.4, "5 · Code and settings point back to requirements; reviewers check both ways")])
  b.append(g(f"{tl.show(0.5)} fin", code_panel(24, 108, 420, CODE, "opendbc/safety/lateral.h:98-101")))
  b.append(g(f"{tl.show(1.6)} fin", chip(460, 128, "SWSR-105", BLUE)[0] + [t(460, 156, "torque while not engaged", 11.5, NAVY), t(460, 172, "→ the frame is a violation,", 11.5, NAVY), t(460, 188, "so it is never sent", 11.5, NAVY)]))
  b.append(g(f"{tl.show(5.2)} fin", [f'<rect x="24" y="230" width="{W - 48}" height="46" rx="8" fill="#fdf6e8" stroke="{AMBER}"/>',
             t(40, 250, "Known gap (TSR-105, NF-01): a steer-request bit with zero torque is still accepted", 12, NAVY, 600),
             t(40, 267, "while not engaged. Recorded as partial, not hidden.", 12, NAVY)]))
  b.append(g(f"{tl.show(8.6)} fin", code_panel(24, 292, 420, WDG, "panda/board/drivers/hw_watchdog.h")))
  b.append(g(f"{tl.show(9.6)} fin", chip(460, 312, "HWSR-501 / 501b", VIOLET)[0] + [t(460, 340, "LSI clock, 90 ms timeout,", 11.5, NAVY),
             t(460, 356, "5 ms window: too late or too", 11.5, NAVY), t(460, 372, "early both reset the chip", 11.5, NAVY)]))
  b.append(g(f"{tl.show(13.6)} fin", [f'<rect x="24" y="408" width="{W - 48}" height="96" rx="10" fill="#fff" stroke="{LIGHT}"/>',
             t(40, 430, "Tests that check them", 13, NAVY, 700),
             t(40, 452, "test_steer_safety_check: with control not allowed, any non-zero torque frame must be refused", 11.5, NAVY),
             t(40, 472, "panda/tests/hw_watchdog: the window, timeout and feeding rules on a PC", 11.5, NAVY),
             t(40, 492, "Not yet: the watchdog on the real chip (HWSR-501 implemented, not verified on hardware)", 11.5, AMBER, 600)]))
  b.append(g(f"{tl.show(17.6)} fin", [f'<rect x="24" y="520" width="{W - 110}" height="62" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 544, "Requirement → code or setting → test → result.", 13.5, NAVY, 700),
             t(40, 566, "A line with no requirement, or a requirement with no line, is a finding.", 12, MID)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "How the engineers meet them (animated)", "The firmware check in opendbc safety/lateral.h that marks a torque frame a violation while control is not allowed (SWSR-105); the known gap that a steer-request bit with zero torque is still accepted; the watchdog settings in panda hw_watchdog.h, 90 ms timeout and 5 ms window (HWSR-501, 501b); the tests that check them, and that the watchdog is not yet verified on hardware.", tl, b)

def hara():
  tl, h = Timeline(22.0), 640
  b = [t(24, 38, "What could go wrong, and how bad? (HARA)", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "1 · Pick a driving situation"), (3.0, "2 · Ask what the system could do wrong in it"),
                 (5.8, "3 · Rate it: severity, exposure, controllability"), (12.4, "4 · The three ratings give an ASIL"),
                 (15.0, "5 · The ASIL C hazard becomes a safety goal")])
  # situation
  b.append(g(f"{tl.show(0.5)} fin", [f'<rect x="24" y="108" width="330" height="96" rx="10" fill="#fff" stroke="{LIGHT}"/>',
             t(40, 130, "SITUATION · OS-13", 11, MID, 700), t(40, 152, "Driving manually, on any road.", 13.5, NAVY, 700),
             t(40, 172, "The system is powered but not engaged;", 12.5, NAVY), t(40, 190, "the driver steers by hand.", 12.5, NAVY)]))
  # wheel icon
  b.append(g(f"{tl.show(0.5)} fin", [f'<circle cx="326" cy="132" r="15" fill="none" stroke="{NAVY}" stroke-width="3.5"/>',
             f'<line x1="311" y1="132" x2="341" y2="132" stroke="{NAVY}" stroke-width="3"/>', f'<line x1="326" y1="132" x2="326" y2="147" stroke="{NAVY}" stroke-width="3"/>']))
  b.append(g(f"{tl.show(3.2)} fin", [f'<rect x="366" y="108" width="330" height="96" rx="10" fill="{RED_BG}" stroke="{RED}"/>',
             t(382, 130, "HAZARDOUS EVENT · HE-01.4", 11, RED, 700), t(382, 152, "It applies steering torque anyway:", 13.5, NAVY, 700),
             t(382, 172, "an unexpected steering disturbance", 12.5, NAVY), t(382, 190, "during manual driving.", 12.5, NAVY)]))
  b.append(g(f"{tl.show(3.6, 5.6)} tr", [f'<path d="M314,120 a15,15 0 0 1 24,0" fill="none" stroke="{RED}" stroke-width="3"/>',
             t(296, 124, "tug!", 12, RED, 800, "end")]))
  y0 = 248
  b += scale(24, y0, "S", ["S0", "S1", "S2", "S3"], 3, RED, "Severity: life-threatening injuries", 6.6, tl)
  b += scale(24, y0 + 48, "E", ["E0", "E1", "E2", "E3", "E4"], 4, AMBER, "Exposure: most of the time on the road", 8.4, tl)
  b += scale(24, y0 + 96, "C", ["C0", "C1", "C2", "C3"], 2, BLUE, "Controllability: most drivers can catch it", 10.2, tl)
  b.append(g(f"{tl.show(11.0)} fin", [t(70, y0 + 124, "⚠ C2 counts on the EPS letting the driver overpower the torque (AOU-01, AOU-02); without that, ASIL D.", 11, MID, 400, "start", True)]))
  # combine
  b.append(g(f"{tl.show(12.6)} fin", [f'<rect x="24" y="{y0 + 140}" width="420" height="56" rx="10" fill="#fff" stroke="{LIGHT}"/>',
             t(40, y0 + 164, "S3 + E4 + C2  →  ISO 26262-3 table  →", 15, NAVY, 700), t(40, y0 + 184, "the more severe, frequent and uncontrollable, the higher the ASIL", 11.5, MID),
             f'<rect x="460" y="{y0 + 140}" width="100" height="56" rx="10" fill="{ORANGE}"/>', t(510, y0 + 176, "ASIL C", 20, "#fff", 800, "middle"),
             t(574, y0 + 162, "QM · A · B · C · D", 11.5, MID, 700), t(574, y0 + 180, "D is the highest", 11, MID)]))
  b.append(g(f"{tl.show(15.2)} fin", [f'<line x1="510" y1="{y0 + 196}" x2="510" y2="{y0 + 214}" stroke="{MID}" stroke-width="2"/>',
             f'<rect x="24" y="{y0 + 214}" width="{W - 48}" height="76" rx="4" fill="#fff" stroke="{NAVY}" stroke-width="3"/>',
             t(40, y0 + 236, "SAFETY GOAL · SG-01 · ASIL C", 11, MID, 700),
             t(40, y0 + 258, "The item shall not cause lateral motion that exceeds what the driver can control,", 13, NAVY, 700),
             t(40, y0 + 278, "including any steering actuation while the item is not engaged.", 13, NAVY, 700)]))
  b.append(g(f"{tl.show(17.5)} fin", [t(24, y0 + 318, "A safety goal says what must never happen. The next steps say how the system makes sure of it.", 12.5, MID, 600)]))
  return svg(h, "What could go wrong, and how bad? (animated)", "The hazardous event HE-01.4: driving manually with the system powered but not engaged, it applies steering torque anyway, an unexpected steering disturbance. Rated S3 (life-threatening), E4 (most of the time on the road), C2 (most drivers can catch it, crediting AOU-01 and AOU-02; ASIL D without them): ASIL C. The safety goal SG-01.", tl, b)

def mech():
  tl, h = Timeline(26.0), 660
  b = [t(24, 38, "The safety mechanism at work", 22, NAVY, 700), t(W - 24, 36, "ILLUSTRATION", 12, AMBER, 700, "end")]
  b += caps(tl, [(0.3, "1 · Driving manually; the system is not engaged"), (2.8, "2 · A software bug makes the SoC send a steering command"),
                 (5.6, "3 · The gate (SM-04, TSR-105) checks every frame"), (11.0, "4 · What if the gate itself stops running?"),
                 (17.4, "5 · Two layers: the gate catches bad commands, the watchdog catches a dead gate")])
  def lane(y, label, gate):
    o = [t(24, y - 10, label, 12.5, GRN if gate else RED, 700),
         f'<rect x="24" y="{y}" width="110" height="52" rx="8" fill="#fff" stroke="{NAVY}" stroke-width="1.8"/>', t(79, y + 22, "SoC", 13, NAVY, 700, "middle"),
         t(79, y + 40, "openpilot (QM)", 10.5, MID, 400, "middle"),
         f'<line x1="134" y1="{y + 26}" x2="{300 if gate else 470}" y2="{y + 26}" stroke="{LIGHT}" stroke-width="3"/>']
    if gate:
      o += [f'<rect x="300" y="{y - 4}" width="130" height="60" rx="8" fill="#fff6ef" stroke="{ORANGE}" stroke-width="2.5"/>',
            t(365, y + 20, "panda gate", 13, NAVY, 700, "middle"), t(365, y + 38, "SM-04 · ASIL C", 10.5, MID, 400, "middle"),
            f'<line x1="430" y1="{y + 26}" x2="470" y2="{y + 26}" stroke="{LIGHT}" stroke-width="3"/>']
    o += [f'<rect x="470" y="{y}" width="90" height="52" rx="8" fill="#f1f3f7" stroke="{NAVY}" stroke-width="1.8"/>', t(515, y + 31, "EPS", 13, NAVY, 700, "middle"),
          f'<circle cx="640" cy="{y + 26}" r="26" fill="none" stroke="{NAVY}" stroke-width="5"/>', f'<line x1="614" y1="{y + 26}" x2="666" y2="{y + 26}" stroke="{NAVY}" stroke-width="4"/>',
          f'<line x1="560" y1="{y + 26}" x2="612" y2="{y + 26}" stroke="{LIGHT}" stroke-width="3"/>']
    return o
  yA, yB = 132, 262
  b.append(g(f"{tl.show(0.4)} fin", lane(yA, "WITH THE GATE", True) + lane(yB, "WITHOUT IT", False)
             + [t(24, 360, "status: not engaged · authority not granted", 12, MID, 600)]))
  # frames travelling
  def frame(x, y, col=RED):
    return [f'<rect x="{x}" y="{y + 14}" width="64" height="24" rx="4" fill="{col}"/>', t(x + 32, y + 31, "torque!", 11, "#fff", 700, "middle")]
  for k, x in enumerate((150, 220)):
    b.append(g(f"{tl.show(3.0 + k * 0.7, 3.7 + k * 0.7)} tr", frame(x, yA) + frame(x, yB)))
  b.append(g(f"{tl.show(4.4)} fin", frame(228, yA)))
  b.append(g(f"{tl.show(5.8)} fin", [f'<circle cx="290" cy="{yA + 26}" r="14" fill="{RED}"/>', t(290, yA + 31, "✗", 15, "#fff", 800, "middle"),
             t(300, yA + 78, "rejected: torque while not engaged (TSR-105)", 11.5, GRN, 700)]))
  b.append(g(f"{tl.show(6.6)} fin", [t(640, yA + 76, "wheel stays still ✓", 11.5, GRN, 700, "middle")]))
  for k, x in enumerate((300, 400)):
    b.append(g(f"{tl.show(4.4 + k * 0.7, 5.1 + k * 0.7)} tr", frame(x, yB)))
  b.append(g(f"{tl.show(6.0)} fin", [f'<g transform="rotate(35 640 {yB + 26})"><line x1="614" y1="{yB + 26}" x2="666" y2="{yB + 26}" stroke="{RED}" stroke-width="4"/></g>',
             t(620, yB + 76, "wheel turns on its own ✗", 11.5, RED, 700, "middle")]))
  # watchdog beat
  wy = 392
  b.append(g(f"{tl.show(11.2)} fin", [f'<rect x="24" y="{wy}" width="{W - 48}" height="150" rx="12" fill="#fff" stroke="{LIGHT}"/>',
             t(40, wy + 24, "The chip running the gate hangs (a fault inside it)", 13, NAVY, 700),
             f'<rect x="40" y="{wy + 40}" width="150" height="50" rx="8" fill="#e9ebf0" stroke="{NAVY}"/>', t(115, wy + 62, "panda MCU", 12.5, NAVY, 700, "middle"),
             t(115, wy + 80, "hung: gate not running", 10.5, RED, 600, "middle"),
             f'<rect x="220" y="{wy + 40}" width="150" height="50" rx="8" fill="#fff" stroke="{VIOLET}" stroke-width="2"/>', t(295, wy + 62, "watchdog", 12.5, NAVY, 700, "middle"),
             t(295, wy + 80, "own clock · HWSR-501", 10.5, MID, 400, "middle")]))
  for i in range(6):
    b.append(g(f"{tl.show(12.4 + i * 0.4)} fin", [f'<rect x="{390 + i * 20}" y="{wy + 52}" width="16" height="26" rx="3" fill="{VIOLET}" opacity="{0.4 + i * 0.1}"/>']))
  b.append(t(390, wy + 100, "", 1))
  b.append(g(f"{tl.show(12.4)} fin", [t(390, wy + 46, "not serviced in time…", 10.5, VIOLET, 600)]))
  b.append(g(f"{tl.show(15.0)} fin", [f'<rect x="520" y="{wy + 40}" width="150" height="50" rx="8" fill="#eaf6ef" stroke="{GRN}" stroke-width="2"/>',
             t(595, wy + 62, "reset → safe state", 12.5, NAVY, 700, "middle"), t(595, wy + 80, "no steering frames sent", 10.5, GRN, 700, "middle"),
             t(40, wy + 120, "Software alone cannot guard against its own chip stopping; a hardware watchdog with its own clock can.", 12, NAVY, 600)]))
  b.append(g(f"{tl.show(17.6)} fin", [f'<rect x="24" y="556" width="{W - 110}" height="64" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 578, "A safety mechanism keeps the safety goal true when something else fails.", 13, NAVY, 700),
             t(40, 598, "Here SG-01: no steering unless engaged. Gate in place; watchdog not yet verified on hardware (DF-01).", 12, MID)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "The safety mechanism at work (animated illustration)", "Illustration. A software bug makes the SoC send a steering torque frame while the system is not engaged: with the gate SM-04 the frame is rejected (TSR-105) and the wheel stays still; without it the wheel turns. If the chip running the gate hangs, the watchdog (HWSR-501) is not serviced and resets it to the safe state, with no steering frames sent.", tl, b)


# ---------------- 5 testing
def status_chip(x, y, label, col):
  return chip(x, y, label, col, 10.5)[0]


def testing(root: Path = ROOT):
  claim, ev = case(root)
  tl, h = Timeline(24.0), 700
  b = [t(24, 38, "Testing it: more than one way", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "1 · Does the code do what the requirement says?"), (4.0, "2 · Does it do it on the real chip?"),
                 (7.6, "3 · Does it hold when something breaks? (fault injection)"), (11.6, "4 · Does the driver cope, in the car?"),
                 (15.6, "5 · Results become evidence for the safety case")])

  def ev_status(sid):
    e = ev[sid]
    col = GRN if e["evidence_status"] == "available" else AMBER if e["evidence_status"] == "partial" else RED
    return f"{e['evidence_status']} · {e['review_state'].replace('-', ' ')}", col

  lanes = [
    (0.5, "REQUIREMENT TESTS · SIL", BLUE, ["opendbc safety tests: with control not allowed, any non-zero", "torque frame must be refused (test_steer_safety_check)"],
     ev_status("Sn-10"), "Sn-10"),
    (4.2, "ON THE TARGET · HIL", VIOLET, ["The same checks on the real panda chip, and the watchdog", "resetting a hung chip (HWSR-501)"], ev_status("Sn-12"), "Sn-12"),
    (7.8, "FAULT INJECTION · VS-FI-01", ORANGE, ["Corrupt the frames the envelope gates on: authority must be", "revoked on the first bad frame, within 0.1 s"], ("not yet executed", RED), "WP-V-05"),
    (11.8, "IN THE CAR · CA-01, INS-28", TEAL, ["Drivers face injected worst-case torque: 20 of 20 must keep the", "car in its lane. At installation: the wheel stays still when off"], ("planned", AMBER), "WP-C-08"),
  ]
  y = 108
  for t0, tag, col, lines, (st, scol), ref in lanes:
    b.append(g(f"{tl.show(t0)} fin", card(24, y, W - 48, 80, tag, col, lines, "#fff", 12)
               + status_chip(W - 40 - (len(st) * 6.6 + 18), y + 50, st, scol) + [t(W - 40, y + 20, ref, 10.5, MID, 700, "end")]))
    y += 92
  b.append(g(f"{tl.show(15.8)} fin", [f'<rect x="24" y="{y + 4}" width="{W - 110}" height="96" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, y + 28, f"CLAIM · {CLAIM} · {claim['title']}", 12.5, NAVY, 700),
             t(40, y + 50, f"Evidence: {', '.join(EVIDENCE)}. A test that passes is not yet evidence that counts:", 12, NAVY),
             t(40, y + 68, "it must be complete, on the right baseline, and independently reviewed.", 12, NAVY),
             t(40, y + 88, "See What is a safety case?", 11.5, MID, 600, "start", True)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "Testing it: more than one way (animated)",
             f"Requirement tests in software (Sn-10, {ev_status('Sn-10')[0]}); tests on the real chip (Sn-12, {ev_status('Sn-12')[0]}); "
             "fault injection VS-FI-01, not yet executed; controllability tests in the car (CA-01) and the installation check "
             f"(INS-28), planned. The results become evidence for the claim {CLAIM}, {claim['title']}.", tl, b)


def render(root: Path = ROOT) -> dict[str, str]:
  return {"h2t-item.svg": item(), "h2t-hara.svg": hara(), "h2t-what-how.svg": what_how(), "h2t-allocation.svg": alloc(),
          "h2t-engineers.svg": engineers(), "h2t-mechanism.svg": mech(), "h2t-testing.svg": testing(root)}


def write_all(out: Path, root: Path = ROOT) -> None:
  out.mkdir(parents=True, exist_ok=True)
  for name, text in render(root).items():
    (out / name).write_text(text, encoding="utf-8")


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--out", type=Path, default=None, help="write the SVGs here")
  ap.add_argument("--check", action="store_true", help="fail if a quoted record or code line changed")
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
