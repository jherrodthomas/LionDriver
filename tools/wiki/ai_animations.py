#!/usr/bin/env python3
"""Render the animated explainers of the wiki page "AI safety and ISO/PAS 8800" as SVG.

  ai-why.svg          coded against learned: the panda gate's four lines against 61 MB of weights, where each standard
                      fits, and LionDriver's acquired, pre-trained model route;
  ai-boundary.svg     the AI system boundary of WP-C-11 §2 and the code around it; a wild output is cut to the
                      envelope, a wrong in-limit one passes;
  ai-errors.svg       the six AI error types of WP-C-11 §5 with their SOTIF insufficiencies;
  ai-input-space.svg  the claimed input space against the unseen training data, and which dimensions the car can observe;
  ai-requirements.svg the AI safety requirements AIR-nn in their seven groups, coloured by their status in WP-C-11 §6;
  ai-data.svg         the dataset requirements DSR-nn and today's state;
  ai-testing.svg      the upstream model replay, the twelve model tests of WP-W-10 §6.2 and model change control;
  ai-layers.svg       the layers around the model, with the runtime monitors' status, and the envelope shared by four
                      standards.

The AIR groups and statuses, the input-space dimensions and their observability, and the DSR and VS-ML counts are read
from WP-C-11 and WP-W-10; the monitor statuses of ai-layers.svg are those of the AIRs that specify them. Every other
ID, number and status is tied to a phrase of its record (SOURCES) and checked at render time (`problems()`); the code
it quotes is checked against opendbc and openpilot when they are checked out. When a record changes, the wiki build
fails instead of showing old text. build_wiki.py renders the figures next to the pages at each sync (nothing is
committed). They loop with CSS; reduced motion shows the final frame.

Usage: python3 tools/wiki/ai_animations.py [--out DIR] [--check]
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

NAMES = ("ai-why.svg", "ai-boundary.svg", "ai-errors.svg", "ai-input-space.svg", "ai-requirements.svg", "ai-data.svg",
         "ai-testing.svg", "ai-layers.svg")
AMBER, BLUE, VIOLET, ORANGE, TEAL = "#b7791f", "#2a78d6", "#6250d6", "#c2410c", "#0f766e"
FS, SO, AI = BLUE, ORANGE, TEAL      # ISO 26262 blue, ISO 21448 orange, ISO/PAS 8800 teal

C11 = Path("assurance") / "02-concept" / "WP-C-11-ai-system-definition-and-safety-requirements.md"
M10 = Path("assurance") / "01-management" / "WP-M-10-ai-safety-plan.md"
W10 = Path("assurance") / "05-software" / "WP-W-10-ml-engineering.md"
V04 = Path("assurance") / "06-validation" / "WP-V-04-sotif-unknown-scenarios.md"
C04 = Path("assurance") / "02-concept" / "WP-C-04-functional-safety-concept.md"
C10 = Path("assurance") / "02-concept" / "WP-C-10-cybersecurity-goals-and-concept.md"
LATERAL = Path("opendbc_repo") / "opendbc" / "safety" / "lateral.h"                       # checked when checked out
REPLAY = Path("openpilot") / "selfdrive" / "test" / "process_replay" / "model_replay.py"

GROUP_NAMES = [("Performance", "how well it drives and sees"), ("Robustness", "per condition, under noise"),
               ("Uncertainty", "knows when it is unsure"), ("Runtime checks", "outputs sane and on time"),
               ("Integrity", "the right model, unaltered"), ("Version control", "which model ran, and its changes"),
               ("Fallback", "safe when the model fails")]
GROUP_HEADINGS = ["### 6.1 Performance", "### 6.2 Robustness", "### 6.3 Uncertainty", "### 6.4 Runtime monitoring",
                  "### 6.5 Integrity", "### 6.6 Version control", "### 6.7 Fallback"]
STATUS = {"ne": ("not evaluated", "#cbd5e1"), "ns": ("not started", "#94a3b8"), "ni": ("not built", "#e0884f"),
          "pa": ("partly", AMBER), "nm": ("not met", RED), "ok": ("holds", GRN)}
# (monitor of WP-M-10 §7, what it does, the AIR of WP-C-11 §6 that specifies it)
MONITORS = [("RM-1", "hash checked at load", "AIR-19"), ("RM-2", "non-finite, range checks", "AIR-16"),
            ("RM-3", "uncertainty monitor", "AIR-14"), ("RM-4", "DM flags when unsure", "AIR-15"),
            ("RM-5", "inference on time", "AIR-17")]

# (record, phrase a figure stands on)
SOURCES = [
  (C11, "| AI-1 | Driving model (\"supercombo\"), vision + policy, recurrent"), (C11, "`65a08adc…7248cce`, 60 918 562 B"),
  (C11, "`MODEL_RUN_FREQ = 20`"), (C11, "| AI-2 | Big driving model (\"Chestnut\")"), (C11, "| **No** — E-06 is excluded"),
  (C11, "| AI-3 | Driver monitoring model"),
  (C11, "every AI error type in §5 is bounded in **magnitude and rate** by the envelope, but **none is bounded in direction or timeliness**"),
  (C11, "| AE-P | Perception error |"), (C11, "| AE-L | Planning / policy error |"), (C11, "| AE-T | Temporal inconsistency |"),
  (C11, "| AE-O | Out-of-distribution input |"), (C11, "| AE-N | Numerical / runtime error |"), (C11, "| AE-D | DM classification error |"),
  (C11, "FI-01, FI-02, FI-04 (FI-06/07 radar fusion consume its leads)"), (C11, "| FI-03, FI-05; SH-01, SH-03, SH-04, SH-09 |"),
  (C11, "| FI-22, FI-15; SH-01, SH-02, SH-04 |"), (C11, "| FI-03; SH-01…SH-06, SH-13 |"), (C11, "| FI-17 (silent clamp); SH-01…SH-06 via the QM software path |"),
  (C11, "| FI-18, FI-19; SH-12 (misuse, WP-C-08) |"),
  (C11, "ODD-H 0–110 km/h"), (C11, "None or light rain; visibility ≥ 200 m"), (C11, "Toyota Corolla TSS2"),
  (C11, "| AIR-09 | AIR-01…AIR-08 shall be met in **each** input-space stratum"),
  (C11, "| AIR-14 | A runtime plausibility/uncertainty monitor"), (C11, "| AIR-11 | Frame-to-frame change of `desiredCurvature` while the scene is steady"),
  (C11, "| AIR-16 | Every AI-1 and AI-3 output tensor shall be checked for non-finite values"), (C11, "| AIR-15 | `driverStateV2.valid` shall be false"),
  (C11, "| AIR-20 | No deserialization mechanism capable of executing code (Python `pickle`)"),
  (C11, "| AIR-29 | In the reference configuration, `action.desiredAcceleration` (end-to-end longitudinal)"),
  (C11, "`ExperimentalMode` defaults to off since 2026-10-14"),
  (C11, "| DSR-02 | Evaluation data shall be recorded on the reference configuration"), (C11, "| DSR-03 | Every evaluation segment shall carry tags"),
  (C11, "| DSR-05 | Evaluation data shall be independent of the model's training data"), (C11, "| DSR-06 | A label specification"),
  (C11, "| DSR-07 | At least 10 % **(TBC)** of human labels shall be double-annotated"), (C11, "| DSR-08 | Datasets shall be versioned by content hash"),
  (C11, "| DSR-09 | The dataset shall contain instances of every known triggering condition"),
  (C11, "| DSR-11 | Data used to choose runtime-monitor thresholds (AIR-14, AIR-18) shall be disjoint"), (C11, "| DSR-13 | Personal data"),
  (C11, "Labelling rule defined (WP-V-02 §5.3.5); not yet implemented"),
  (M10, "LionDriver does not train models"), (M10, "## 5. The acquired, pre-trained model route"),
  (M10, "| RM-1 | Verify artefact hash against the release manifest"), (M10, "| RM-2 | Non-finite and range checks"),
  (M10, "| RM-3 | Uncertainty / plausibility monitor"), (M10, "| RM-4 | DM validity"), (M10, "| RM-5 | Inference timing monitor"),
  (W10, "| Input | One route, one segment, frames 0–60 (3 s at 20 Hz)"), (W10, "In CI the result is forced to pass after posting a report (`failed = False`)"),
  (W10, "| Model testing | MLE.4 | Specification (§6); **none executed**."), (W10, "MLE.1–4: CL0 today; target CL1"),
  (W10, "| Reference device for VS-ML-01/-10 | Not available as a test asset"), (W10, "| Upstream sync touching any of the above | No automatic adoption (D-02)"),
  (W10, "| New model artefact (any file under `openpilot/selfdrive/modeld/models/`) | Full acceptance A1–A8"),
  (W10, "the big model was replaced and reverted the same day (`0e0c7c7`, `f59056e`)"),
  (W10, "| Data management | SUP.11 | Procedure defined (§5); **no data exists**"),
  (W10, "| Change control | SUP.10 | Defined (§8) | Exercise on the first model-related change |"),
  (V04, "| Bn | Repeated after each release and after every model or tinygrad change"), (V04, "| ≥ 1 000 km engaged |"),
  (V04, "no uploads to comma's servers, DQ-084 option A"),
  (C04, "| FSR-01.01 | The envelope shall limit the commanded LKA torque magnitude"),
  (C10, "| **CSG-01** | The integrity and authenticity of the panda safety configuration"),
]
CODE = [(LATERAL, "bool torque_requested = desired_torque != 0;"), (LATERAL, "if (!controls_allowed && torque_requested) {"),
        (REPLAY, "failed = False")]


class ParseError(Exception):
  pass


def classify(cell: str) -> str:
  c = cell.replace("*", "").strip()
  for key, words in (("nm", ("Not met",)), ("ni", ("Not implemented",)), ("pa", ("Partially", "Partly")),
                     ("ne", ("Not evaluated",)), ("ns", ("Not started",)),
                     ("ok", ("Holds", "Met", "Process defined", "Default releases exclude"))):
    if c.startswith(words):
      return key
  raise ParseError(f"WP-C-11 §6: status not recognised: {c[:50]!r}")


def data(root: Path = ROOT) -> dict:
  """Everything the figures compute from the records."""
  t = (root / C11).read_text(encoding="utf-8")
  air, groups = {}, []
  for k, head in enumerate(GROUP_HEADINGS):
    i = t.find(head)
    if i < 0:
      raise ParseError(f"WP-C-11: heading {head!r} not found")
    j = t.find(GROUP_HEADINGS[k + 1], i) if k + 1 < len(GROUP_HEADINGS) else t.find("\n## 7.", i)
    ids = []
    for line in t[i:j].splitlines():
      if line.startswith("| AIR-"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        air[cells[0]] = classify(cells[-1])
        ids.append(cells[0])
    groups.append(ids)
  i, j = t.find("## 3. Input space"), t.find("\n## 4.")
  obs = {"yes": 0, "partly": 0, "no": 0, "scope": 0}
  dims = 0
  for line in t[i:j].splitlines():
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if not line.startswith("| ") or cells[0] in ("Dimension",) or set(cells[0]) <= {"-"}:
      continue
    dims += 1
    o = cells[3]
    obs["yes" if o.startswith("Yes") else "partly" if o.startswith("Partially") else "no" if o.startswith("No") else "scope"] += 1
  dsr = [l for l in t.splitlines() if l.startswith("| DSR-")]
  dsr_ns = sum(1 for l in dsr if l.strip().strip("|").split("|")[-1].strip().startswith("Not started"))
  w = (root / W10).read_text(encoding="utf-8")
  vs = len(re.findall(r"^\| VS-ML-\d+ \|", w, re.M))
  return {"air": air, "groups": groups, "n_air": len(air), "dims": dims, "obs": obs, "n_dsr": len(dsr), "dsr_ns": dsr_ns, "vs": vs}


def problems(root: Path = ROOT) -> list[str]:
  errs, cache = [], {}
  for path, phrase in SOURCES:
    if path not in cache:
      p = root / path
      cache[path] = norm(p.read_text(encoding="utf-8")) if p.exists() else ""
    if norm(phrase) not in cache[path]:
      errs.append(f"{path}: the AI safety page stands on {phrase!r}, which is gone; update the figure")
  for path, line in CODE:
    p = root / path
    if p.exists() and line not in p.read_text(encoding="utf-8"):
      errs.append(f"{path}: the AI safety page quotes {line!r}, which is gone; update the figure")
  try:
    d = data(root)
    if len(d["groups"]) != len(GROUP_NAMES) or any(not g_ for g_ in d["groups"]):
      errs.append(f"{C11}: the §6 groups changed; update the requirement map")
    if max(len(g_) for g_ in d["groups"]) > 8:
      errs.append(f"{C11}: a §6 group has more than 8 requirements; the map draws at most 8 per row")
    for _, _, a in MONITORS:
      if a not in d["air"]:
        errs.append(f"{C11}: {a} is gone; update the monitor statuses of ai-layers.svg")
    if d["vs"] != 12:
      errs.append(f"{W10}: {d['vs']} model tests, the figure draws 12; update ai-testing.svg")
  except (ParseError, ValueError, IndexError, OSError) as e:
    errs.append(f"AI records: {e}")
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



def code_box(x, y, w, lines, title):
  o = [f'<rect x="{x}" y="{y}" width="{w}" height="{30 + 17 * len(lines)}" rx="8" fill="#0f1b33"/>', t(x + 12, y + 18, title, 10.5, "#9fb3d1", 700)]
  for i, l in enumerate(lines):
    o.append(f'<text x="{x + 12}" y="{y + 38 + i * 17}" font-size="10" fill="#e6edf7" font-family="monospace">{l}</text>')
  return o


def net(x, y, w, h, seed=0):
  """A small neural-network drawing: four columns of nodes, every node joined to the next column."""
  cols = [3, 5, 5, 2]
  pts = []
  for c, n in enumerate(cols):
    xx = x + 14 + c * (w - 28) / 3
    pts.append([(xx, y + (k + 1) * h / (n + 1)) for k in range(n)])
  o = []
  for a, bcol in zip(pts, pts[1:]):
    for (x1, y1) in a:
      for (x2, y2) in bcol:
        o.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="{AI}" stroke-width="0.8" opacity="0.45"/>')
  for col in pts:
    for (xx, yy) in col:
      o.append(f'<circle cx="{xx:.0f}" cy="{yy:.0f}" r="5" fill="#fff" stroke="{AI}" stroke-width="2"/>')
  return o


# ------------------------------------------------------------------ 0 why AI needs its own rules
def why_ai():
  tl, h = Timeline(28.0), 620
  b = [t(24, 38, "Why AI needs its own rules", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "Coded software: the rule is written down, so you can read it and test it"),
                 (5.4, "A learned model: 61 MB of numbers, and no line says 'follow the lane'"),
                 (10.8, "You cannot review a requirement into a network; you check its behaviour on data"),
                 (16.2, "ISO/PAS 8800 adds what the other standards do not cover for AI"),
                 (22.2, "LionDriver does not train its models: it accepts a finished one")])
  cw = 324
  b.append(g(f"{tl.show(0.5)} fin", [f'<rect x="24" y="108" width="{cw}" height="230" rx="12" fill="#fff" stroke="{NAVY}" stroke-width="2"/>',
                                     t(38, 132, "CODED · the panda gate (TSR-105)", 12, NAVY, 800)]
             + code_box(38, 146, cw - 28, ["bool torque_requested = desired_torque != 0;", "if (!controls_allowed &amp;&amp; torque_requested) {", "  violation = true;", "}"], "opendbc/safety/lateral.h")
             + [t(38, 266, "Read it: the rule is right there.", 12.5, NAVY, 600), t(38, 286, "Test it: every input you can think of.", 12.5, NAVY, 600),
                t(38, 312, "Faults → ISO 26262", 12, FS, 700)]))
  x2 = 24 + cw + 24
  b.append(g(f"{tl.show(5.6)} fin", [f'<rect x="{x2}" y="108" width="{cw}" height="230" rx="12" fill="#fff" stroke="{AI}" stroke-width="2"/>',
                                     t(x2 + 14, 132, "LEARNED · the driving model (AI-1)", 12, AI, 800)]
             + net(x2 + 20, 142, cw - 40, 110)
             + [t(x2 + 14, 266, "60 918 562 bytes of weights, trained by comma", 12.5, NAVY, 600),
                t(x2 + 14, 286, "on data LionDriver cannot see (GAP-22).", 12.5, NAVY, 600),
                t(x2 + 14, 312, "Its behaviour comes from data, not lines", 12, AI, 700)]))
  b.append(g(f"{tl.show(7.4)} fin", [f'<rect x="{x2 + 70}" y="158" width="190" height="24" rx="12" fill="{RED_BG}" stroke="{RED}"/>',
                                     t(x2 + 165, 175, "where is 'follow the lane'?", 11.5, RED, 700, "middle")]))
  # where 8800 fits
  y = 358
  stds = [(FS, "ISO 26262", "a part or the hardware running the model fails"), (SO, "ISO 21448", "the function falls short in a situation"),
          (AI, "ISO/PAS 8800", "data, training, model testing, monitors, model changes")]
  for i, (c, n, what) in enumerate(stds):
    yy = y + i * 40
    b.append(g(f"{tl.show(16.4 + i * 1.0)} fin", [f'<rect x="24" y="{yy}" width="{W - 48}" height="32" rx="8" fill="#fff" stroke="{c}" stroke-width="{2.5 if c == AI else 1.5}"/>',
                                                   t(38, yy + 21, n, 13, c, 800), t(170, yy + 21, what, 12.5, NAVY)]))
  b.append(g(f"{tl.show(22.4)} fin", [f'<rect x="24" y="490" width="{W - 110}" height="108" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 512, "LionDriver's route (WP-M-10 §5): acquired, pre-trained models", 13, NAVY, 700),
             t(40, 534, "LionDriver does not train. Its AI safety requirements are acceptance criteria", 12, NAVY),
             t(40, 552, "for a finished model, plus requirements on the code around it (WP-C-11).", 12, NAVY),
             t(40, 578, "So the questions are: what may it see, how can it fail, and what catches it?", 12, AI, 700)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "Why AI needs its own rules (animated)",
             "Coded software: the panda gate in opendbc/safety/lateral.h, a rule you can read and test. A learned model: AI-1, 60 918 562 bytes of weights trained by comma on data LionDriver cannot see (GAP-22), with no line that says follow the lane. ISO 26262 covers failures, ISO 21448 a function that falls short, ISO/PAS 8800 adds data, training, model testing, monitors and model changes. LionDriver does not train: its AI safety requirements are acceptance criteria for a finished model and requirements on the code around it.", tl, b)


# ------------------------------------------------------------------ 1 learned vs coded
def boundary():
  tl, h = Timeline(30.0), 640
  b = [t(24, 38, "What is learned, and what is coded around it", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "The AI system: from camera frames to the model's messages (WP-C-11 §2)"),
                 (6.4, "Everything after it is ordinary code, and the panda has the last word"),
                 (12.6, "A wild output is cut down to size by the limits …"),
                 (18.6, "… but a wrong output that stays inside the limits passes"),
                 (24.4, "The envelope bounds how much and how fast, not which way or when")])
  y = 120
  # AI boundary
  b.append(g(f"{tl.show(0.5)} fin", [f'<rect x="24" y="{y}" width="390" height="190" rx="14" fill="#ecf7f5" stroke="{AI}" stroke-width="2" stroke-dasharray="7 5"/>',
                                     t(36, y + 20, "AI SYSTEM (dashed)", 11, AI, 800)]))

  def box(x, yy, w, hh, l1, l2, col, fill="#fff"):
    return [f'<rect x="{x}" y="{yy}" width="{w}" height="{hh}" rx="8" fill="{fill}" stroke="{col}" stroke-width="1.8"/>',
            t(x + w / 2, yy + hh / 2 - 2, l1, 12, NAVY, 700, "middle"), t(x + w / 2, yy + hh / 2 + 14, l2, 10.5, MID, 400, "middle")]
  ar = lambda x1, y1, x2, y2: f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{NAVY}" stroke-width="1.8"/>'
  steps = [(0.8, box(36, y + 34, 80, 54, "camera", "frames", NAVY)), (1.4, box(132, y + 34, 80, 54, "warp", "coded", NAVY)),
           (2.0, box(228, y + 30, 100, 62, "AI-1 network", "learned · 20 Hz", AI, "#d7efea")),
           (2.6, box(132, y + 116, 80, 54, "parser", "coded", NAVY)), (3.2, box(228, y + 116, 100, 54, "smoothing", "coded", NAVY))]
  for t0, o in steps:
    b.append(g(f"{tl.show(t0)} fin", o))
  b.append(g(f"{tl.show(3.4)} fin", [ar(116, y + 61, 132, y + 61), ar(212, y + 61, 228, y + 61), ar(278, y + 92, 278, y + 116),
                                     ar(228, y + 143, 212, y + 143), t(36, y + 150, "AI-3 driver", 10.5, AI, 700), t(36, y + 164, "monitoring: same", 10.5, AI, 700),
                                     t(36, y + 178, "pattern", 10.5, AI, 700)]))
  b.append(g(f"{tl.show(4.2)} fin", [t(342, y + 52, "AI-2", 10.5, MID, 700), t(342, y + 66, "excluded", 10.5, MID, 400)]))
  # downstream
  b.append(g(f"{tl.show(6.6)} fin", box(440, y + 30, 120, 62, "controlsd", "limits · QM", NAVY)
             + box(580, y + 30, 116, 62, "panda", "envelope · ASIL C", ORANGE, "#fff6ef")
             + box(580, y + 116, 116, 54, "EPS", "steering", NAVY)
             + [ar(414, y + 61, 440, y + 61), ar(560, y + 61, 580, y + 61), ar(638, y + 92, 638, y + 116)]))
  # meters: magnitude
  my = 340
  def meter(t0, t1, val, lim, col, lab, cls="tr"):
    o = [f'<rect x="200" y="{my}" width="420" height="22" rx="5" fill="#f1f3f7"/>',
         f'<rect x="200" y="{my}" width="{lim}" height="22" rx="5" fill="{GRN}" opacity="0.18"/>',
         f'<line x1="{200 + lim}" y1="{my - 6}" x2="{200 + lim}" y2="{my + 28}" stroke="{ORANGE}" stroke-width="3"/>',
         t(200 + lim, my - 10, "envelope limit", 10.5, ORANGE, 700, "middle"),
         f'<rect x="200" y="{my + 5}" width="{val}" height="12" rx="4" fill="{col}"/>', t(24, my + 16, lab, 12, NAVY, 700)]
    return g(f"{tl.show(t0, t1)} {cls}", o)
  b.append(meter(12.8, 18.2, 400, 260, RED, "model asks for:"))
  b.append(g(f"{tl.show(14.4, 18.2)} tr", [f'<rect x="200" y="{my + 34}" width="260" height="12" rx="4" fill="{GRN}"/>', t(24, my + 45, "panda passes:", 12, NAVY, 700),
                                           t(470, my + 45, "cut to the limit ✓", 11.5, GRN, 700)]))
  b.append(meter(18.8, None, 180, 260, AMBER, "model asks for:", "fin"))
  b.append(g(f"{tl.show(20.2)} fin", [f'<rect x="200" y="{my + 34}" width="180" height="12" rx="4" fill="{AMBER}"/>', t(24, my + 45, "panda passes:", 12, NAVY, 700),
                                      t(390, my + 45, "in limits, but the wrong way ✗", 11.5, RED, 700)]))
  b.append(g(f"{tl.show(24.6)} fin", [f'<rect x="24" y="410" width="{W - 48}" height="110" rx="12" fill="#fff" stroke="{AI}" stroke-width="2"/>',
             t(40, 434, "So the AI safety requirements aim at two things (WP-C-11 §4):", 13, NAVY, 700),
             t(40, 458, "1. keep in-limit errors rare enough to meet the SOTIF validation targets;", 12.5, NAVY),
             t(40, 478, "2. make errors visible: monitors around the model that the driver or the code can act on.", 12.5, NAVY),
             t(40, 504, "The envelope is the safety net; it is not the argument that the model is good.", 12, AI, 700)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "What is learned, and what is coded around it (animated)",
             "The AI system of WP-C-11: camera frames, a coded warp, the learned AI-1 network at 20 Hz, a coded parser and smoothing; AI-2 is excluded and driver monitoring (AI-3) follows the same pattern. After it, controlsd limits and the panda envelope (ASIL C). A wild output is cut to the envelope limit; a wrong output inside the limits passes. The envelope bounds magnitude and rate, not direction or timeliness.", tl, b)


# ------------------------------------------------------------------ 2 how a model gets it wrong
def error_types():
  tl, h = Timeline(30.0), 660
  b = [t(24, 38, "How a model gets it wrong", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "WP-C-11 §5 sorts AI errors into six types"),
                 (21.6, "Each type points at a SOTIF insufficiency, so the analyses share one chain"),
                 (25.6, "Six types, one question each: how would we notice?")])
  rows = [("AE-P", "Perception", "sees the scene wrong", "a tar seam taken for a lane line; a phantom lead under a bridge", "FI-01, FI-02, FI-04"),
          ("AE-L", "Planning", "right scene, wrong action", "a curvature that follows an exit lane", "FI-03, FI-05"),
          ("AE-T", "Temporal", "each frame fine, the sequence not", "a lead that flickers in and out; lane lines that switch", "FI-22, FI-15"),
          ("AE-O", "Out of distribution", "never saw anything like it", "snow, low sun, road works, a different bonnet", "FI-03"),
          ("AE-N", "Numerical", "the execution fails, not the learning", "a non-finite output; a miscompiled model", "FI-17"),
          ("AE-D", "Driver monitoring", "misreads the driver", "sunglasses at night; a phone low in the lap", "FI-18, FI-19")]
  for i, (code, name, what, ex, fi) in enumerate(rows):
    y = 112 + i * 72
    t0 = 1.0 + i * 3.3
    b.append(g(f"{tl.show(t0)} fin", [f'<rect x="24" y="{y}" width="{W - 48}" height="64" rx="10" fill="#fff" stroke="{AI}" stroke-width="1.6"/>',
                                       f'<rect x="24" y="{y}" width="64" height="64" rx="10" fill="{AI}"/>', t(56, y + 38, code, 13, "#fff", 800, "middle"),
                                       t(102, y + 24, name, 13.5, NAVY, 700), t(270, y + 24, "· " + what, 12, MID, 600),
                                       t(102, y + 46, "e.g. " + ex, 12, NAVY)]))
    ch, w = chip(W - 40 - (len(fi) * 6.3 + 16), y + 25, fi, SO)
    b.append(g(f"{tl.show(21.8 + i * 0.25)} fin", ch))
  b.append(g(f"{tl.show(25.8)} fin", [f'<rect x="24" y="552" width="{W - 110}" height="88" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 574, "How we would notice, by type (WP-C-11 §6):", 12.5, NAVY, 700),
             t(40, 596, "P, L, O: scenario tests and an uncertainty monitor (AIR-14, FM-09) · T: a steady-scene", 12, NAVY),
             t(40, 614, "check (AIR-11) · N: non-finite checks (AIR-16) · D: DM validity (AIR-15). Most are not built yet.", 12, NAVY)]))
  b.append(stick(W - 40, h - 14, "point"))
  return svg(h, "How a model gets it wrong (animated)",
             "The six AI error types of WP-C-11: perception, planning, temporal inconsistency, out-of-distribution input, numerical or runtime error, and driver-monitoring classification, each with an example and the SOTIF functional insufficiencies it links to, and how each would be noticed: scenario tests and an uncertainty monitor (AIR-14), a steady-scene check (AIR-11), non-finite checks (AIR-16), DM validity (AIR-15).", tl, b)



# ------------------------------------------------------------------ 3 input space vs ODD
def input_space(d):
  tl, h = Timeline(30.0), 650
  b = [t(24, 38, "What the model must handle, and what it learned", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "The input space: the conditions we claim the model works in (WP-C-11 §3)"),
                 (6.0, "What the model was trained on is unknown: it is comma's data"),
                 (11.2, "So nobody can show the claim sits inside the training data: it must be tested"),
                 (16.6, "And the car cannot always tell when it has left the input space"),
                 (23.6, "Where it cannot tell, the driver must: user information, plus a monitor")])
  # left: diagram of two regions
  cx, cy = 190, 250
  b.append(g(f"{tl.show(0.5)} fin", [f'<rect x="{cx - 120}" y="{cy - 80}" width="240" height="160" rx="18" fill="#ecf7f5" stroke="{AI}" stroke-width="2.5"/>',
                                     t(cx, cy - 56, "INPUT SPACE", 11.5, AI, 800, "middle"), t(cx, cy - 40, "what we claim", 11, AI, 600, "middle"),
                                     t(cx, cy - 6, "highways · ≤ 110 km/h", 11.5, NAVY, 600, "middle"), t(cx, cy + 12, "markings visible · day or", 11.5, NAVY, 600, "middle"),
                                     t(cx, cy + 28, "headlit night · light rain", 11.5, NAVY, 600, "middle"), t(cx, cy + 46, "Corolla TSS2 · US", 11.5, NAVY, 600, "middle")]))
  b.append(g(f"{tl.show(6.2)} fin", [f'<path d="M{cx - 150},{cy - 40} C{cx - 170},{cy - 140} {cx + 40},{cy - 150} {cx + 90},{cy - 110} C{cx + 190},{cy - 120} {cx + 200},{cy + 30} {cx + 140},{cy + 70} C{cx + 120},{cy + 140} {cx - 60},{cy + 130} {cx - 110},{cy + 90} C{cx - 190},{cy + 80} {cx - 170},{cy} {cx - 150},{cy - 40} Z" fill="none" stroke="{MID}" stroke-width="2" stroke-dasharray="6 5"/>',
                                     t(cx - 150, cy + 128, "TRAINING DATA ? (dashed)", 11, MID, 800), t(cx - 150, cy + 142, "comma's, not visible (GAP-22)", 10.5, MID, 400)]))
  b.append(g(f"{tl.show(11.4)} fin", [f'<rect x="24" y="404" width="330" height="56" rx="10" fill="#fff" stroke="{AI}"/>',
                                      t(36, 426, "Test it ourselves, per condition (AIR-09):", 12, NAVY, 700),
                                      t(36, 446, "every claim must hold in each stratum, not on average", 11.5, NAVY)]))
  # right: dimensions with observability
  rows = [("Curvature", "yes"), ("Speed", "yes"), ("Mounting, calibration", "yes"), ("Camera, vehicle, traffic side", "yes"),
          ("Road type", "partly"), ("Lane markings", "partly"), ("Light, glare", "partly"), ("Driver's face (AI-3)", "partly"),
          ("Weather, visibility", "no"), ("Clean windscreen", "no")]
  col = {"yes": GRN, "partly": AMBER, "no": RED}
  b.append(g(f"{tl.show(16.8)} fin", [t(380, 118, "CAN THE CAR TELL IT IS INSIDE?", 11, MID, 800)]))
  for i, (n, o) in enumerate(rows):
    y = 140 + i * 30
    ch, w = chip(W - 30 - 60, y + 4, o, col[o])
    b.append(g(f"{tl.show(17.0 + i * 0.4)} fin", [f'<rect x="380" y="{y - 12}" width="{W - 404}" height="26" rx="6" fill="#fff" stroke="{LIGHT}"/>',
                                                   t(392, y + 5, n, 12, NAVY, 600)] + ch))
  b.append(g(f"{tl.show(23.8)} fin", [f'<rect x="24" y="480" width="{W - 110}" height="150" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 502, "Where the car cannot tell, it keeps driving when it should not:", 12.5, NAVY, 700),
             t(40, 524, "• heavy rain or a dirty windscreen has no detector today;", 12, NAVY),
             t(40, 544, "• the driver is told the limits (WP-O-03) and must take over;", 12, NAVY),
             t(40, 564, "• a monitor should flag inputs the model finds unfamiliar (AIR-14, FM-09):", 12, NAVY),
             t(40, 584, "  not built yet.", 12, RED, 700),
             t(40, 612, f"{d['dims']} dimensions in WP-C-11 §3; {d['obs']['yes']} observable, {d['obs']['partly']} partly, {d['obs']['no']} not, {d['obs']['scope']} are scope limits.", 11, MID, 400, "start", True)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "What the model must handle, and what it learned (animated)",
             f"The claimed input space (highways up to 110 km/h, visible markings, day or headlit night, light rain, the Corolla TSS2) inside an unknown training distribution (GAP-22), so each claim must be tested per condition (AIR-09). Of {d['dims']} dimensions, {d['obs']['yes']} are observable at runtime, {d['obs']['partly']} partly and {d['obs']['no']} not; where the car cannot tell, the driver must, and an uncertainty monitor (AIR-14) is not built yet.", tl, b)


# ------------------------------------------------------------------ 4 AI safety requirements
def requirements(d):
  tl, h = Timeline(30.0), 650
  b = [t(24, 38, "AI safety requirements: what the model must meet", 22, NAVY, 700)]
  b += caps(tl, [(0.3, f"{d['n_air']} requirements (AIR-01…AIR-{d['n_air']:02d}) in seven groups (WP-C-11 §6)"),
                 (13.0, "Their status today, from the records"),
                 (20.4, "Nothing about the model's performance is measured yet: there is no LionDriver data")])
  ST = STATUS
  groups = [(name, what, [(a[-2:], d["air"][a]) for a in d["groups"][gi]]) for gi, (name, what) in enumerate(GROUP_NAMES)]
  y = 110
  k = 0
  for gi, (name, what, airs) in enumerate(groups):
    yy = y + gi * 56
    b.append(g(f"{tl.show(0.6 + gi * 1.6)} fin", [t(24, yy + 20, name, 13, NAVY, 700), t(24, yy + 36, what, 11, MID)]))
    for j, (n, st) in enumerate(airs):
      x = 230 + j * 58
      b.append(g(f"{tl.show(0.9 + gi * 1.6 + j * 0.12)} fin", [f'<rect x="{x}" y="{yy + 6}" width="52" height="34" rx="6" fill="#fff" stroke="{AI}" stroke-width="1.5"/>',
                                                               t(x + 26, yy + 28, f"AIR-{n}", 10.5, NAVY, 700, "middle")]))
      lab, c = ST[st]
      b.append(g(f"{tl.show(13.2 + k * 0.12)} fin", [f'<rect x="{x}" y="{yy + 6}" width="52" height="34" rx="6" fill="{c}"/>',
                                                      t(x + 26, yy + 28, f"AIR-{n}", 10.5, "#fff" if st not in ("ne",) else NAVY, 700, "middle")]))
      k += 1
  # legend
  lx = 24
  for key in ("ne", "ns", "ni", "pa", "nm", "ok"):
    lab, c = ST[key]
    b.append(g(f"{tl.show(17.4)} fin", [f'<rect x="{lx}" y="510" width="14" height="14" rx="3" fill="{c}"/>', t(lx + 20, 522, lab, 11.5, NAVY, 600)]))
    lx += len(lab) * 7 + 44
  b.append(g(f"{tl.show(20.6)} fin", [f'<rect x="24" y="540" width="{W - 110}" height="90" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 562, "Examples: AIR-20, no code-executing model loading — not met (pickle).", 12, NAVY),
             t(40, 582, "AIR-15, driver-monitoring output marked invalid when unsure — not met (always valid).", 12, NAVY),
             t(40, 602, "AIR-29, end-to-end acceleration off — partly: off by default since 2026-10-14, toggle still there.", 12, NAVY),
             t(40, 620, "Performance targets are marked TBC until the validation targets are frozen.", 11, MID, 400, "start", True)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "AI safety requirements: what the model must meet (animated)",
             f"The {d['n_air']} AI safety requirements of WP-C-11 in seven groups (performance, robustness, uncertainty, runtime checks, integrity, change control, fallback), each coloured by its status in the record: not evaluated, not started, not built, partly, not met or holds. No performance requirement is evaluated: there is no LionDriver data.", tl, b)


# ------------------------------------------------------------------ 5 data
def data_scene(d):
  tl, h = Timeline(30.0), 650
  b = [t(24, 38, "Data: the evidence a model needs", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "A model is tested on data, so the data needs requirements too (WP-C-11 §7)"),
                 (3.4, "Recorded on the reference car, and never seen in training"),
                 (8.6, "Every segment tagged with its conditions, so results can be split by them"),
                 (13.8, "Labelled to a written spec, checked by a second person, and frozen"),
                 (19.0, "Enough of every known hard case, and personal data protected"),
                 (24.2, f"LionDriver today: no data recorded yet; {d['dsr_ns']} of {d['n_dsr']} data rules not started")])
  # conveyor
  cy = 150
  b.append(g(f"{tl.show(0.5)} fin", [f'<rect x="24" y="{cy + 40}" width="{W - 48}" height="8" rx="4" fill="#e5e9f0"/>']))
  segs = [(3.6, 60), (4.2, 200), (4.8, 340), (5.4, 480)]
  for t0, x in segs:
    b.append(g(f"{tl.show(t0)} fin", [f'<rect x="{x}" y="{cy - 10}" width="120" height="48" rx="6" fill="#1e2d4d"/>',
                                       f'<path d="M{x + 20},{cy + 38} L{x + 56},{cy + 4} L{x + 64},{cy + 4} L{x + 100},{cy + 38} Z" fill="#8a919c"/>',
                                       f'<line x1="{x + 60}" y1="{cy + 8}" x2="{x + 60}" y2="{cy + 36}" stroke="#fff" stroke-width="2" stroke-dasharray="4 4"/>']))
  b.append(g(f"{tl.show(5.8)} fin", [t(620, cy + 20, "DSR-02", 11, AI, 800), t(620, cy + 34, "DSR-05", 11, AI, 800)]))
  tags = ["highway", "night", "light rain", "faded lines", "curve", "glare"]
  tx = 60
  for i, tg in enumerate(tags):
    ch, w = chip(tx, cy + 72, tg, AI, 10)
    tx += w + 10
    b.append(g(f"{tl.show(8.8 + i * 0.3)} fin", ch))
  b.append(g(f"{tl.show(10.8)} fin", [t(620, cy + 76, "DSR-03", 11, AI, 800)]))
  # exam analogy
  b.append(g(f"{tl.show(3.6, 8.4)} tr", [f'<rect x="24" y="{cy + 100}" width="{W - 48}" height="40" rx="8" fill="#fff" stroke="{AI}"/>',
                                         t(40, cy + 125, "Why unseen data: a test on data the model trained on is an exam with the answers handed out.", 12, NAVY, 600)]))
  steps = [(14.0, "Label spec", "what 'lane centre' and 'lead' mean exactly", "DSR-06"), (15.0, "Second annotator", "≥ 10 % double-labelled, agreement measured", "DSR-07"),
           (16.0, "Frozen by hash", "a dataset used for evidence never changes", "DSR-08"), (19.2, "Hard cases", "every known triggering condition present", "DSR-09"),
           (20.2, "Kept apart", "monitor thresholds tuned on other drives", "DSR-11"), (21.2, "Privacy", "faces, plates, location handled as personal data", "DSR-13")]
  for i, (t0, a, bb, ref) in enumerate(steps):
    x = 24 + (i % 3) * 228
    y = 300 + (i // 3) * 92
    b.append(g(f"{tl.show(t0)} fin", [f'<rect x="{x}" y="{y}" width="216" height="80" rx="10" fill="#fff" stroke="{AI}" stroke-width="1.6"/>',
                                       t(x + 12, y + 22, a, 13, NAVY, 700), t(x + 204, y + 22, ref, 10.5, AI, 800, "end"),
                                       t(x + 12, y + 44, wrap2(bb, 32)[0], 11.5, NAVY), t(x + 12, y + 61, wrap2(bb, 32)[1], 11.5, NAVY)]))
  b.append(g(f"{tl.show(24.4)} fin", [f'<rect x="24" y="500" width="{W - 110}" height="128" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 522, "LionDriver today (WP-C-11 §7, WP-W-10 §5)", 13, NAVY, 700),
             t(40, 544, "No LionDriver drive data exists yet, so no AI requirement can be evaluated.", 12, NAVY),
             t(40, 564, f"{d['dsr_ns']} of the {d['n_dsr']} data rules are not started; the rule that labels simulated data", 12, NAVY),
             t(40, 582, "as synthetic is defined (DSR-12), not yet applied.", 12, NAVY),
             t(40, 608, "Logs stay under LionDriver control: no uploads to comma's servers (DQ-084).", 11.5, MID, 400, "start", True)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "Data: the evidence a model needs (animated)",
             f"Data requirements of WP-C-11: recorded on the reference car and independent of training (DSR-02, DSR-05), tagged by condition (DSR-03), labelled to a spec with double annotation (DSR-06, DSR-07), frozen by hash (DSR-08), covering every known triggering condition (DSR-09), monitor-threshold data kept apart (DSR-11), personal data protected (DSR-13). Today no drive data exists and {d['dsr_ns']} of {d['n_dsr']} data rules are not started.", tl, b)



# ------------------------------------------------------------------ 6 testing a model, and changing it
def testing():
  tl, h = Timeline(32.0), 670
  b = [t(24, 38, "Testing a model, and changing it", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "What openpilot has: a model replay over one 3 s segment, forced to pass in CI"),
                 (5.0, "A regression check says 'it changed', not 'it is good enough'"),
                 (8.4, "LionDriver specifies twelve model tests (WP-W-10 §6.2)"),
                 (17.6, "A new model is a safety change: nothing upstream is adopted automatically"),
                 (26.0, "Today: tests specified, none executed; no reference device as a test asset")])
  # upstream replay
  b.append(g(f"{tl.show(0.5)} fin", [f'<rect x="24" y="108" width="{W - 48}" height="52" rx="10" fill="#fff" stroke="{LIGHT}"/>',
                                     t(40, 130, "Upstream model replay", 12.5, NAVY, 700), t(40, 148, "1 route · frames 0–60 · compared with comma's reference logs", 11.5, MID),
                                     f'<rect x="{W - 230}" y="120" width="190" height="28" rx="6" fill="#0f1b33"/>',
                                     f'<text x="{W - 220}" y="139" font-size="11" fill="#e6edf7" font-family="monospace">failed = False</text>']))
  b.append(g(f"{tl.show(5.2)} fin", [t(W - 135, 176, "model_replay.py:294-296", 10.5, RED, 600, "middle")]))
  cats = [("Same model?", [("01", "compile check"), ("02", "graph structure")]),
          ("Good enough?", [("03", "per condition"), ("05", "uncertainty"), ("06", "driver monitor"), ("07", "steady in time")]),
          ("Hard to break?", [("04", "perturbed input"), ("09", "bad outputs"), ("11", "tampered file")]),
          ("Fit to ship?", [("08", "monitor works"), ("10", "timing on load"), ("12", "vs last pin")])]
  y0 = 196
  for ci, (name, tests) in enumerate(cats):
    x = 24 + ci * 170
    b.append(g(f"{tl.show(8.6 + ci * 1.6)} fin", [f'<rect x="{x}" y="{y0}" width="162" height="{36 + 30 * len(tests)}" rx="10" fill="#fff" stroke="{AI}" stroke-width="1.8"/>',
                                                   t(x + 12, y0 + 22, name, 13, AI, 800)]
               + sum([[f'<rect x="{x + 10}" y="{y0 + 34 + k * 30}" width="40" height="22" rx="5" fill="{AI}"/>', t(x + 30, y0 + 49 + k * 30, n, 11, "#fff", 800, "middle"),
                       t(x + 56, y0 + 50 + k * 30, lab, 10.5, NAVY, 600), t(x + 56, y0 + 50 + k * 30, "", 1)] for k, (n, lab) in enumerate(tests)], [])))
  b.append(g(f"{tl.show(15.2)} fin", [t(24, y0 + 172, "VS-ML-01 … VS-ML-12, each tied to the AI requirements it checks", 11, MID, 400, "start", True)]))
  # change flow
  fy = 400
  flow = [("upstream", "new model or", "tinygrad bump", NAVY), ("stop", "no automatic", "adoption (D-02)", RED), ("accept", "tests A1–A8,", "VS-ML-12", AI),
          ("explore", "≥ 1 000 km block", "(WP-V-04 Bn)", SO), ("release", "manifest with", "hashes", GRN)]
  for i, (a, l1, l2, c) in enumerate(flow):
    x = 24 + i * 136
    b.append(g(f"{tl.show(17.8 + i * 1.0)} fin", [f'<rect x="{x}" y="{fy}" width="124" height="64" rx="10" fill="#fff" stroke="{c}" stroke-width="2"/>',
                                                   t(x + 62, fy + 22, a.upper(), 11.5, c, 800, "middle"), t(x + 62, fy + 40, l1, 11, NAVY, 600, "middle"),
                                                   t(x + 62, fy + 55, l2, 11, NAVY, 600, "middle")]
               + ([f'<path d="M{x - 12},{fy + 32} h10" stroke="{NAVY}" stroke-width="2"/>'] if i else [])))
  b.append(g(f"{tl.show(22.8)} fin", [t(24, fy + 92, "Why: upstream once replaced its big model and reverted it the same day (0e0c7c7, f59056e).", 11.5, NAVY, 600)]))
  b.append(g(f"{tl.show(26.2)} fin", [f'<rect x="24" y="520" width="{W - 110}" height="128" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 542, "LionDriver today (WP-W-10 §6.3, §9)", 13, NAVY, 700),
             t(40, 564, "Twelve tests specified, none executed. No reference device as a test asset,", 12, NAVY),
             t(40, 582, "no fork-owned replay set, perturbation scripts still to write.", 12, NAVY),
             t(40, 604, "Model engineering is at capability level 0, target 1 (ASPICE MLE.1–4).", 12, NAVY),
             t(40, 628, "Change control is defined and has not yet been exercised on a real model change.", 11.5, MID, 400, "start", True)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "Testing a model, and changing it (animated)",
             "The upstream model replay covers one 3 s segment and is forced to pass in CI. WP-W-10 specifies twelve model tests in four groups: same model, good enough, hard to break, fit to ship. A model change is a safety change: no automatic adoption (D-02), acceptance tests A1 to A8, a 1 000 km exploration block (WP-V-04 Bn), a release manifest with hashes. Today none of the tests is executed and change control has not been exercised.", tl, b)


# ------------------------------------------------------------------ 7 the envelope bounds any model
def layers(d):
  tl, h = Timeline(30.0), 670
  b = [t(24, 38, "No single model is trusted alone", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "The model sits inside layers of ordinary, checkable code"),
                 (3.0, "Layer 1: monitors around the model (WP-M-10 RM-1…RM-5)"),
                 (9.6, "Layer 2: the controller's limits; layer 3: the panda envelope"),
                 (14.6, "Layer 4: the supervising driver, watched by driver monitoring"),
                 (19.6, "The argument does not rest on the model being good"),
                 (24.8, "One envelope, four standards: the same cap and lock as on the other pages")])
  # nested rounded rectangles
  cx, cy = 180, 300
  rings = [(160, 170, "#fdf6ee", NAVY, "4 · driver, supervising", 14.8), (134, 136, "#fff6ef", ORANGE, "3 · panda envelope (ASIL C)", 10.6),
           (108, 102, "#f4f6fa", NAVY, "2 · controller limits (QM)", 9.8), (82, 68, "#ecf7f5", AI, "1 · runtime monitors", 3.2)]
  for rw, rh, fill, c, lab, t0 in rings:
    b.append(g(f"{tl.show(t0)} fin", [f'<rect x="{cx - rw}" y="{cy - rh}" width="{2 * rw}" height="{2 * rh}" rx="22" fill="{fill}" stroke="{c}" stroke-width="2.2"/>',
                                       t(cx, cy - rh + 18, lab, 11.5, c, 800, "middle")]))
  b.append(g(f"{tl.show(0.5)} fin", [f'<rect x="{cx - 56}" y="{cy - 30}" width="112" height="70" rx="10" fill="#fff" stroke="{AI}" stroke-width="2"/>']
             + net(cx - 52, cy - 28, 104, 50) + [t(cx, cy + 34, "AI-1 model", 11, AI, 800, "middle")]))
  # monitors list with status
  mons = [(rm, what, *STATUS[d["air"][air]]) for rm, what, air in MONITORS]
  b.append(g(f"{tl.show(3.4)} fin", [t(370, 124, "LAYER 1 TODAY", 11, AI, 800)]))
  for i, (rid, what, st, c) in enumerate(mons):
    y = 140 + i * 34
    ch, w = chip(W - 30 - (len(st) * 6.3 + 16), y + 16, st, c)
    b.append(g(f"{tl.show(4.0 + i * 1.0)} fin", [f'<rect x="370" y="{y}" width="{W - 394}" height="28" rx="6" fill="#fff" stroke="{LIGHT}"/>',
                                                  t(380, y + 19, rid, 11.5, AI, 800), t(422, y + 19, what, 11.5, NAVY)] + ch))
  others = [(10.0, "Layer 2", "controller clips", "in place", GRN), (11.0, "Layer 3", "torque cap, accel bounds", "in place", GRN),
            (15.0, "Layer 4", "driver + DM alerts", "partly", AMBER)]
  for i, (t0, l, what, st, c) in enumerate(others):
    y = 326 + i * 34
    ch, w = chip(W - 30 - (len(st) * 6.3 + 16), y + 16, st, c)
    b.append(g(f"{tl.show(t0)} fin", [f'<rect x="370" y="{y}" width="{W - 394}" height="28" rx="6" fill="#fff" stroke="{LIGHT}"/>',
                                       t(380, y + 19, l, 11.5, NAVY, 800), t(440, y + 19, what, 11, NAVY)] + ch))
  b.append(g(f"{tl.show(19.8)} fin", [f'<rect x="24" y="490" width="{W - 48}" height="70" rx="10" fill="#fff" stroke="{AI}" stroke-width="2"/>',
             t(40, 512, "The safety argument (WP-C-11 §4): the envelope bounds how much and how fast;", 12.5, NAVY, 700),
             t(40, 532, "SOTIF validation keeps in-limit errors rare; monitors and the driver catch the rest.", 12.5, NAVY),
             t(40, 550, "A better model makes the system better, never the argument for its safety.", 12, AI, 700)]))
  b.append(g(f"{tl.show(25.0)} fin", [f'<rect x="24" y="574" width="{W - 110}" height="76" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 596, "The torque cap of layer 3 is FSR-01.01 on the SOTIF page; the safety-mode", 12, NAVY),
             t(40, 614, "lock that keeps layer 3 in place is CSG-01 on the cybersecurity page.", 12, NAVY),
             t(40, 636, "One mechanism carries ISO 26262, ISO 21448, ISO/SAE 21434 and ISO/PAS 8800.", 12, AI, 700)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "No single model is trusted alone (animated)",
             "Four layers around the model: runtime monitors RM-1 to RM-5, with the status of the AI requirements that specify them; the controller limits; the panda envelope (ASIL C); the supervising driver with driver monitoring. The envelope bounds how much and how fast, SOTIF validation keeps in-limit errors rare, monitors and the driver catch the rest. The torque cap (FSR-01.01) and the safety-mode lock (CSG-01) make one mechanism serve ISO 26262, ISO 21448, ISO/SAE 21434 and ISO/PAS 8800.", tl, b)



def wrap2(txt, n=22):
  words, a = txt.split(), ""
  while words and len(a + " " + words[0]) <= n + 1:
    a = (a + " " + words.pop(0)).strip()
  return [a, " ".join(words)]




def render(root: Path = ROOT) -> dict[str, str]:
  d = data(root)
  figs = (why_ai(), boundary(), error_types(), input_space(d), requirements(d), data_scene(d), testing(), layers(d))
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
