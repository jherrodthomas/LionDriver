#!/usr/bin/env python3
"""Write "One requirement, six routes": one safety requirement reached by six analysis methods, and its anatomy.

The specimen is SG-02 → FSR-02.05 → TSR-516 (b)/(c): the panda's own siren when the envelope ends actuation authority
for a reason the driver did not cause. Six methods already in this repository each reach it from a different side
(FTA, FMEA, STPA, the HARA guide words, the plant scenarios, the trace). Every page ends with the same anatomy strip:
TRIGGER · AGENT · MODAL · ACTION · OBJECT · CONSTRAINT, the slots of the FRET structured language (condition,
component, shall, response, timing), with the slots that method pinned down in colour.

  requirement-routes.md                 the walk-through, linked from README.md and 03-system/README.md
  figures/fig-c04-r1-anatomy.svg        the six slots, defined once on FSR-02.05
  figures/fig-c04-r2-routes.svg         the six routes and the slots each one fixed
  figures/fig-c04-r3-<n>-<route>.svg    one page per route, ending with the strip
  figures/fig-c04-r4-tsr516c.svg        TSR-516(c) split into slots, WP-S-02 v0.52 against v0.53 (FRET FF-04…FF-06)

Every record a route cites is quoted from its file; the build fails if a quote is no longer there, so a route that
goes stale shows up in CI rather than in a review. The slot texts of TSR-516 and FSR-02.05 are checked against the
current WP-S-02 and WP-C-04 text the same way. The v0.52 strip is a quote of the superseded text and is kept as is.
The F-05 guide-word grid is read from the HARA model. The road scene is a drawing of the plant result, which is
synthetic (DSR-12) and carries no evidence credit.

    python3 fsc_routes.py            # write all outputs
    python3 fsc_routes.py --check    # fail if an output is stale or a quote is gone

Standard library only. Output is deterministic.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
A = HERE.parents[1]  # assurance/
sys.path.insert(0, str(A / "08-analyses" / "figures"))
sys.path.insert(0, str(A / "02-concept" / "hara"))
import hara_model as hm  # noqa: E402  (F-05 guide-word classification)
import stpa_scenes as ss  # noqa: E402  (the large road scene, from the shared scene kit)

FIG = HERE / "figures"
PAGE = HERE / "requirement-routes.md"
FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SFMono-Regular', Menlo, Consolas, monospace"
INK, MUTED, FAINT, HAIR, PANEL = "#0F172A", "#475569", "#94A3B8", "#E2E8F0", "#F8FAFC"
BAD, BAD_BG, OK, OK_BG = "#B42318", "#FDECEA", "#166534", "#E3F2E8"
W, M = 720, 24  # every figure is 720 wide with a 24 margin, so it reads on a phone at full width


class RouteError(Exception):
  pass


def fail(msg):
  raise RouteError(msg)


# ============================================================================ the anatomy
# (key, question, FRET field, colour, light fill)
SLOTS = [
  ("TRIGGER", "when?", "condition", "#B45309", "#FEF3C7"),
  ("AGENT", "who?", "component", "#0F766E", "#CCFBF1"),
  ("MODAL", "how binding?", "shall", "#6D28D9", "#EDE9FE"),
  ("ACTION", "does what?", "response", "#1D4ED8", "#DBEAFE"),
  ("OBJECT", "to what?", "response", "#BE185D", "#FCE7F3"),
  ("CONSTRAINT", "how fast, long, loud?", "timing", "#4D7C0F", "#ECFCCB"),
]
KEYS = [s[0] for s in SLOTS]
COL = {s[0]: s[3] for s in SLOTS}
FILL = {s[0]: s[4] for s in SLOTS}

WP_C04 = A / "02-concept" / "WP-C-04-functional-safety-concept.md"
WP_S02 = A / "03-system" / "WP-S-02-technical-safety-requirements.md"

# FSR-02.05 and TSR-516(c) split into slots. Each text is a quote of the current document (checked), except where
# `None` marks a slot the requirement leaves empty and `derived` a slot it states only through another clause.
FSR = dict(
  TRIGGER="When granted actuation authority ends for a reason other than a driver action that the safety MCU itself observes",
  AGENT="the safety MCU",
  MODAL="shall",
  ACTION="give",
  OBJECT="an acoustic warning that does not depend on the SoC",
  CONSTRAINT=None,
)
TSR_NOW = dict(
  TRIGGER="(c) PCM cruise is still active 0.5 s (within one 10 ms task period) after the SoC heartbeat first reported \"not engaged\"",
  AGENT="The safety MCU",
  MODAL="shall",
  ACTION="sound",
  OBJECT="its own acoustic warning … without depending on SoC software",
  CONSTRAINT="within ≤ 0.5 s of detection … for at least 3 s or for as long as its condition holds if longer, at a level audible over the cabin noise of the reference vehicle (level set by WP-S-04 M-05)",
)
# WP-S-02 v0.52 (superseded 2026-10-21), kept as quoted
TSR_OLD = dict(TSR_NOW,
               TRIGGER="(c) PCM cruise is still active more than 0.5 s after the SoC heartbeat first reported \"not engaged\"",
               CONSTRAINT="within ≤ 0.5 s of detection")
OLD_MARKS = {"TRIGGER": "FF-06 · one tick off", "CONSTRAINT": "FF-05 · how long? how loud?"}
# the strip at the foot of each route page, abridged so the page stays short on a phone
TSR_SHORT = dict(TRIGGER="PCM cruise still active 0.5 s after the first \"not engaged\" heartbeat", AGENT="The safety MCU",
                 MODAL="shall", ACTION="sound", OBJECT="its own siren, not via the SoC",
                 CONSTRAINT="≤ 0.5 s; ≥ 3 s; audible (M-05)")
FRET = A / "models" / "fret" / "fretish-requirements.md"
FRETISH = [("upon not_engaged_ticks = 50 & persisted(49, pcm_cruise_active)", "TRIGGER"), ("the envelope", "AGENT"), ("shall", "MODAL"),
           ("within 50 ticks", "CONSTRAINT"), ("satisfy siren_on", "ACTION")]

# ============================================================================ the six routes
# Each source: (path under assurance/, quote that must be in it, label). `fixed`: the slots the route pinned down.
ROUTES = [
  dict(
    key="fta", name="Fault tree", short="FTA", asks="Which combinations of faults violate SG-02?",
    records="WP-A-04 SG-02 tree: MCS-02.5, MCS-02.9, BE-2.14",
    src=[("08-analyses/WP-A-04-system-fta-fmea.md", "| MCS-02.5 | 1 (effective) | {BE-2.05} | One cause removes control and the SoC warning", "MCS-02.5 SoC stall"),
         ("08-analyses/WP-A-04-system-fta-fmea.md", "| MCS-02.9 | 1 (effective) | {BE-2.21} | selfdrived crash or hang", "MCS-02.9 selfdrived hang"),
         ("08-analyses/WP-A-04-system-fta-fmea.md", "BE-2.14 Siren not triggered", "BE-2.14 siren not triggered")],
    fixed=["AGENT", "TRIGGER"],
    gave="A single SoC fault both removes steering and silences the SoC's own alert (cut sets of order 1). The warning "
         "must come from an element that survives the SoC: the safety MCU. The cut sets list the causes the trigger must cover.",
    watch="Credit is by design only: the order stays 1 until the siren timing is verified on hardware (OI-11). BE-2.14 "
          "described only the baseline triggers until PR #400.",
  ),
  dict(
    key="fmea", name="FMEA", short="FMEA", asks="How does each element fail, and what control catches it?",
    records="System FMEA SFM-026 (alert not presented), WP-W-04 SWF-39 (siren omission)",
    src=[("08-analyses/fmea/analyses/system-fmea.yaml", "The panda siren is the SoC-independent control (FSR-02.05;", "SFM-026 alert not presented"),
         ("05-software/WP-W-04-software-safety-analysis.md", "| SWF-39 | U-PND-HK siren | Omission: siren not sounding when SoC lost", "SWF-39 siren omission")],
    fixed=["ACTION", "OBJECT"],
    gave="The alert row names the control (the panda siren) and traces it to FSR-02.05. The software row turns the "
         "control into an item with its own failure mode, omission, which a test must exclude.",
    watch="Rows age with the code: until PRs #398 and #399, SWF-39 credited only the heartbeat case and the System FMEA "
          "F-04b entries described a silent SoC stall.",
  ),
  dict(
    key="stpa", name="STPA", short="STPA", asks="Which control actions are unsafe, and why?",
    records="WP-A-05 UCA-17, loss scenario LS-20",
    src=[("08-analyses/WP-A-05-stpa.md", "| UCA-17 | N | Take-over alert not given, or given after the driver can react", "UCA-17 alert not given or late"),
         ("08-analyses/WP-A-05-stpa.md", "| LS-20 | UCA-17 | A take-over request is not perceived.", "LS-20 not perceived")],
    fixed=["CONSTRAINT", "TRIGGER"],
    gave="The unsafe action is 'not given, or given after the driver can react': the constraint is relative to the driver. "
         "The loss scenario says why: an alert the driver does not perceive is not given. That is the audible-level clause.",
    watch="Loss scenarios age: until PR #401, LS-20 said the siren covers only heartbeat loss and an EPS fault, and no "
          "loss scenario covered the failed-cancel case (c); LS-37 now does.",
  ),
  dict(
    key="guidewords", name="Guide words", short="HAZOP", asks="What if the warning function does NO, LATE, TOO SHORT …?",
    records="HARA F-05 'Driver information and warnings': M01 and the guide words rated the same",
    src=[("02-concept/hara/hara_model.py", '"M01": (SC, "H-07", "", "Take-over request or disengagement alert not given', "F-05 M01 no function"),
         ("02-concept/hara/hara_model.py", '"M09": (SC, "H-07", "M01", "Alert too short to be noticed; same as missing."', "F-05 M09 too short"),
         ("02-concept/hara/hara_model.py", '"M08": (SC, "H-07", "M01", "Alert shown after the driver needed it; same as missing."', "F-05 M08 late")],
    fixed=["MODAL", "CONSTRAINT"],
    gave="NO makes the warning mandatory. LATE, DELAYED and TOO SHORT are each rated 'same as missing', so the timing and the "
         "duration belong in the requirement, not in a test note. TOO SHORT was in the HARA before TSR-516 said how long.",
    watch="Generic: the rows name the take-over alert, not who sounds it, so they reach SG-02 through H-07 and need the "
          "other routes to reach the panda.",
  ),
  dict(
    key="scenario", name="Scenario", short="PLANT", asks="What happens on the road, in seconds?",
    records="Plant runs F-04b (SoC stall) and engaged mismatch (selfdrived stops)",
    src=[("sim/results/silent-stall.md", "| curve inside the ODD (1.5 m/s²) | as built (siren on revocation) | 0.05 s | 0.29 s | siren at 0.29 s | 1.79 s |", "F-04b curve, as built"),
         ("sim/results/silent-stall.md", "| curve inside the ODD (1.5 m/s²) | before DQ-404 (siren muted) | 0.05 s | — | drift at 1.39 s | 2.89 s |", "F-04b curve, siren muted"),
         ("sim/results/engaged-mismatch.md", "the panda siren starts 0.5 s after that heartbeat, at 0.63–0.88 s (TSR-516(c))", "engaged mismatch, siren"),
         ("sim/results/silent-stall.md", "**No evidence credit** (DQ-139)", "synthetic, no credit")],
    fixed=["CONSTRAINT"],
    gave="The numbers: with the siren on revocation the driver starts correcting at 1.79 s instead of 2.89 s, and the peak "
         "offset in the curve falls from 3.64 m to 0.83 m. In the failed-cancel case the siren comes at 0.63–0.88 s, "
         "inside SG-02's 1 s.",
    watch="Synthetic (DSR-12), no evidence credit: real panda code in the loop, but the driver, EPS and road are the plant's "
          "assumptions. At the ODD bound the car still reaches the lane line.",
  ),
  dict(
    key="trace", name="Trace", short="TRACE", asks="Is every link there, with the right ASIL and a test?",
    records="SG-02 → FSR-02.05 → TSR-516 → SWSR-516, SWSR-516b → tests",
    src=[("trace/items/tsr.yaml", "parents: [FSR-02.05, FSR-06.05]", "TSR-516 parents"),
         ("trace/items/swsr.yaml", "The envelope shall record the time at which the heartbeat first reports", "SWSR-516b"),
         ("05-software/WP-W-02-software-safety-requirements.md", "| SWSR-516b |", "WP-W-02 SWSR-516b")],
    fixed=[],
    gave="Confirms the chain rather than deriving anything. It checks the attributes: TSR-516 is ASIL C like its parent, "
         "verification T-HIL. It found SWSR-516 and SWSR-516b at ASIL B (raised to C in PR #392, with eight more), and no HIL or VS case for (c) (VS-FI-10 (b) added in PR #396, a HIL test proposed in PR #402).",
    watch="A complete trace says nothing about whether the text is right: every FRET finding (FF-01…FF-07) passed the trace.",
  ),
]

# ============================================================================ text and checks
def norm(s):
  return re.sub(r"\s+", " ", s.replace("\\\"", "\"")).strip()


def quote_in(path: Path, q: str, what: str):
  if norm(q) not in norm(path.read_text(encoding="utf-8")):
    fail(f"{what}: quote no longer in {path.relative_to(A.parent)}: {q[:80]}")


def check_sources():
  for r in ROUTES:
    for p, q, label in r["src"]:
      quote_in(A / p, q, f"route {r['key']} ({label})")
  c04, s02 = WP_C04.read_text(encoding="utf-8"), WP_S02.read_text(encoding="utf-8")
  fsr = next((ln for ln in c04.splitlines() if ln.startswith("| FSR-02.05 |")), "")
  tsr = next((ln for ln in s02.splitlines() if ln.startswith("| TSR-516 |")), "")
  if not fsr or not tsr:
    fail("FSR-02.05 or TSR-516 row not found")
  for k, v in FSR.items():
    if v and norm(v) not in norm(fsr):
      fail(f"FSR-02.05 {k} slot no longer in WP-C-04: {v[:60]}")
  for k, v in TSR_NOW.items():
    for part in v.removeprefix("(c) ").split(" … "):
      if norm(part) not in norm(tsr):
        fail(f"TSR-516 {k} slot no longer in WP-S-02: {part[:60]}")
  quote_in(FRET, "`" + " ".join(p for p, _ in FRETISH[:4]) + " " + FRETISH[4][0] + "`", "FR-516c FRETish")
  return fsr, tsr


def tw(s, size, bold=False, mono=False):
  return len(s) * size * (0.61 if mono else 0.57 if bold else 0.54)


def wrap_px(s, width, size, bold=False):
  out, line = [], ""
  for w in s.split():
    cand = f"{line} {w}".strip()
    if line and tw(cand, size, bold) > width:
      out.append(line)
      line = w
    else:
      line = cand
  out.append(line)
  for ln in out:
    if " " in ln and tw(ln, size, bold) > width + 0.5:
      fail(f"line too wide: {ln}")
  return out


def T(x, y, s, size=13, fill=INK, weight=400, anchor="start", mono=False, extra=""):
  a = "" if anchor == "start" else f' text-anchor="{anchor}"'
  f = f' font-family="{MONO}"' if mono else ""
  return f'<text x="{x:g}" y="{y:g}" font-size="{size}" font-weight="{weight}" fill="{fill}"{a}{f}{extra}>{escape(str(s))}</text>'


def para(x, y, s, width, size=13, fill=INK, weight=400, lh=None):
  lh = lh or round(size * 1.38, 1)
  lines = wrap_px(s, width, size, weight >= 600)
  return [T(x, y + i * lh, ln, size, fill, weight) for i, ln in enumerate(lines)], y + len(lines) * lh


def svg(title, desc, h, body):
  return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h:g}" viewBox="0 0 {W} {h:g}" font-family="{FONT}" '
          f'role="img" aria-labelledby="t d"><title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>'
          f'<rect width="{W}" height="{h:g}" fill="#FFFFFF"/>' + "".join(body) + "</svg>\n")


def head(title, sub, tag):
  o = [T(M, 34, tag, 11.5, MUTED, 700, mono=True)]
  o += [T(M, 60 + 26 * i, ln, 21, INK, 700) for i, ln in enumerate(wrap_px(title, W - 2 * M, 21, True))]
  y = 60 + 26 * len(wrap_px(title, W - 2 * M, 21, True))
  p, y = para(M, y + 2, sub, W - 2 * M, 13, MUTED)
  return o + p, y + 6


# ============================================================================ the strip
SW, SG = (W - 2 * M - 5 * 6) / 6, 6  # slot width, gap


def strip(y, cells, lit=None, marks=None, label=None, size=12):
  """Six slots in a row. cells: slot -> text (None: empty). lit: slots in colour (others faded). marks: slot -> defect."""
  lit = set(KEYS if lit is None else lit)
  marks = marks or {}
  o = []
  if label:
    o.append(T(M, y + 12, label, 11.5, MUTED, 700, mono=True))
    y += 22
  bodies = {k: wrap_px(cells.get(k) or "—", SW - 14, size) for k in KEYS}
  n = max(len(v) for v in bodies.values())
  ml = {k: wrap_px(v, SW - 12, 10.5, True) for k, v in marks.items()}
  bh = 16 + n * round(size * 1.3, 1) + (8 + 13 * max(len(v) for v in ml.values()) if ml else 0)
  for i, (k, q, fret, col, fill) in enumerate(SLOTS):
    x = M + i * (SW + SG)
    on = k in lit
    op = "" if on else ' opacity="0.32"'
    o.append(f"<g{op}>")
    o.append(f'<rect x="{x:.1f}" y="{y}" width="{SW:.1f}" height="38" rx="6" fill="{col}"/>')
    o.append(T(x + SW / 2, y + 17, k, 11.5, "#FFFFFF", 700, "middle", mono=True))
    o.append(T(x + SW / 2, y + 31, q, 10.5, "#FFFFFF", 500, "middle"))
    empty = cells.get(k) is None
    o.append(f'<rect x="{x:.1f}" y="{y + 42}" width="{SW:.1f}" height="{bh:.1f}" rx="6" fill="{FILL[k] if not empty else "#FFFFFF"}" '
             f'stroke="{col}" stroke-width="1.2"{" stroke-dasharray=\"4 3\"" if empty else ""}/>')
    for j, ln in enumerate(bodies[k]):
      o.append(T(x + 7, y + 42 + 18 + j * round(size * 1.3, 1), ln, size, INK if not empty else MUTED))
    o.append("</g>")
    if k in marks:
      o.append(f'<rect x="{x + 1:.1f}" y="{y + 43}" width="{SW - 2:.1f}" height="{bh - 2:.1f}" rx="5" fill="none" stroke="{BAD}" '
               'stroke-width="2.4" stroke-dasharray="6 3"/>')
      for j, ln in enumerate(ml[k][::-1]):
        o.append(T(x + 7, y + 42 + bh - 9 - j * 13, ln, 10.5, BAD, 700))
  return o, y + 42 + bh


def fret_row(y):
  o = [T(M, y + 12, "FRET FIELD", 11.5, MUTED, 700, mono=True)]
  for i, (k, *_r) in enumerate(SLOTS):
    x = M + i * (SW + SG)
    o.append(T(x + SW / 2, y + 32, SLOTS[i][2], 12.5, COL[k], 700, "middle", mono=True))
  return o, y + 44


def attrs(y, items):
  o, x = [], M
  for k, v in items:
    s = f"{k} {v}"
    w = tw(s, 12, True) + 20
    o += [f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="24" rx="12" fill="{PANEL}" stroke="{FAINT}"/>',
          T(x + 10, y + 16.5, k, 12, MUTED, 600), T(x + 10 + tw(k + " ", 12, True), y + 16.5, v, 12, INK, 700)]
    x += w + 8
  if x > W - M + 8:
    fail("attribute chips too wide")
  return o, y + 24


# ============================================================================ figures
def fig_anatomy():
  o, y = head("The anatomy of a requirement", "Six slots, each answering one question. A slot left empty, or filled with "
              "words that cannot be tested, is a defect you can see. The slots are those of FRET's structured English, "
              "so a requirement split this way can also be formalised and checked against the code.", "ANATOMY · FSR-02.05")
  s, y = strip(y + 6, FSR, label="FSR-02.05 (WP-C-04 §5), SPLIT INTO SLOTS")
  o += s
  f, y = fret_row(y + 4)
  o += f
  a, y = attrs(y + 10, [("ASIL", "C"), ("parent", "SG-02"), ("allocated", "E-03 panda"), ("verified by", "T-HIL")])
  o += a
  note = ("CONSTRAINT is empty at FSR level: SG-02 only gives the 1 s budget from fault to warning. TSR-516 fills it. "
          "Attributes ride with the requirement but are not part of its sentence.")
  p, y = para(M, y + 30, note, W - 2 * M, 13, MUTED)
  return svg("The anatomy of a requirement", "FSR-02.05 split into the six slots TRIGGER, AGENT, MODAL, ACTION, OBJECT and "
             "CONSTRAINT, with the FRET field each slot maps to and the requirement's attributes.", y + 10, o + p)


def fig_routes():
  o, y = head("Six routes, one requirement", "Each method starts from SG-02 and reaches the same siren requirement from a "
              "different side. The chips show which slots of TSR-516 each route pinned down.", "OVERVIEW · SG-02 → FSR-02.05 → TSR-516")
  cw, ch, g = (W - 2 * M - 14) / 2, 128, 14
  y0 = y + 8
  for i, r in enumerate(ROUTES):
    x, yy = M + (i % 2) * (cw + g), y0 + (i // 2) * (ch + g)
    o += [f'<rect x="{x:.1f}" y="{yy:.1f}" width="{cw:.1f}" height="{ch}" rx="10" fill="{PANEL}" stroke="{HAIR}"/>',
          f'<circle cx="{x + 22:.1f}" cy="{yy + 24:.1f}" r="12" fill="{INK}"/>', T(x + 22, yy + 28.5, str(i + 1), 13, "#FFFFFF", 700, "middle"),
          T(x + 42, yy + 29, r["name"], 16, INK, 700), T(x + cw - 12, yy + 29, r["short"], 11, MUTED, 700, "end", mono=True)]
    p, _ = para(x + 14, yy + 52, r["asks"], cw - 28, 12.5, MUTED)
    o += p[:2]
    cx = x + 14
    chips = r["fixed"] or ["confirms"]
    for k in chips:
      w = tw(k, 11, True, True) + 16
      c, fc = (COL[k], "#FFFFFF") if k in COL else ("#FFFFFF", MUTED)
      o += [f'<rect x="{cx:.1f}" y="{yy + ch - 34:.1f}" width="{w:.1f}" height="22" rx="11" fill="{c}" stroke="{COL.get(k, FAINT)}"/>',
            T(cx + w / 2, yy + ch - 19, k, 11, fc, 700, "middle", mono=True)]
      cx += w + 6
  y = y0 + 3 * (ch + g) + 4
  bx = M
  o += [f'<rect x="{bx}" y="{y}" width="{W - 2 * M}" height="62" rx="10" fill="#FFF7ED" stroke="#C2410C" stroke-width="1.6"/>',
        T(bx + 16, y + 26, "TSR-516 (b)/(c) · ASIL C", 15, INK, 700),
        T(bx + 16, y + 47, "The safety MCU sounds its own siren when authority ends for a reason the driver did not cause.", 12.5, MUTED)]
  y += 62
  o += [T(M, y + 30, "Cross-checks: FRET found three anatomy defects (FF-04…FF-06); fmdtools, 10 cut sets the siren covers.", 12.5, MUTED)]
  return svg("Six routes, one requirement", "Six cards, one per analysis route (fault tree, FMEA, STPA, guide words, plant "
             "scenario, trace), each with the question it asks and the slots of TSR-516 it fixed, above the TSR-516 box.", y + 46, o)


def mini_fta(y):
  o = []
  box = lambda x, yy, w, h, txt, col="#FFFFFF", st=FAINT, tc=INK: [
    f'<rect x="{x}" y="{yy}" width="{w}" height="{h}" rx="7" fill="{col}" stroke="{st}" stroke-width="1.3"/>',
    *[T(x + w / 2, yy + 19 + 16 * i, ln, 12.5, tc, 600 if i == 0 else 400, "middle") for i, ln in enumerate(txt)]]
  o += box(210, y, 300, 46, ["SG-02 violated", "steering lost and no warning"], "#FDECEA", BAD)
  o += [f'<path d="M360 {y + 46} V{y + 62}" stroke="{MUTED}" stroke-width="1.4"/>',
        f'<path d="M346 {y + 62} h28 v10 a14 14 0 0 1 -28 0 Z" fill="#FFFFFF" stroke="{MUTED}" stroke-width="1.4"/>',
        T(360, y + 76, "AND", 9.5, MUTED, 700, "middle", mono=True),
        f'<path d="M360 {y + 86} V{y + 96} M170 {y + 96} H550 M170 {y + 96} V{y + 108} M550 {y + 96} V{y + 108}" stroke="{MUTED}" fill="none" stroke-width="1.4"/>']
  o += box(40, y + 108, 260, 64, ["steering lost", "SoC stall BE-2.05 · selfdrived", "hang BE-2.21 · EPS fault"])
  o += box(420, y + 108, 260, 64, ["no warning", "SoC alert lost with the SoC", "AND siren fails BE-2.14"], "#FFFFFF", COL["AGENT"])
  o += [f'<path d="M300 {y + 140} H420" stroke="{BAD}" stroke-width="2" stroke-dasharray="5 4"/>',
        T(360, y + 133, "one cause", 11.5, BAD, 700, "middle"), T(360, y + 158, "takes both", 11.5, BAD, 700, "middle")]
  return o, y + 182


def mini_fmea(y):
  cols = [("Item", 108), ("Failure mode", 176), ("Effect", 128), ("Control", 150), ("Trace", 110)]
  rows = [["HMI (ui, soundd)", "Take-over alert not presented (crash)", "Unannounced loss", "panda siren", "FSR-02.05"],
          ["U-PND-HK siren", "Omission: siren not sounding when SoC lost", "No warning", "malfunction reported", "SWSR-516"]]
  o, x = [], M
  for name, w in cols:
    o += [f'<rect x="{x}" y="{y}" width="{w}" height="28" fill="{INK}"/>', T(x + 8, y + 19, name, 12, "#FFFFFF", 700)]
    x += w
  yy = y + 28
  for r, row in enumerate(rows):
    x, cells = M, [wrap_px(v, w - 14, 12) for v, (_, w) in zip(row, cols, strict=True)]
    h = 14 + 16 * max(len(c) for c in cells)
    for c, (_, w), lines in zip(range(5), cols, cells, strict=True):
      hl = (r == 0 and c == 3) or (r == 1 and c == 1)
      fill = FILL["ACTION"] if hl and c == 3 else BAD_BG if hl else "#FFFFFF"
      o.append(f'<rect x="{x}" y="{yy}" width="{w}" height="{h}" fill="{fill}" stroke="{HAIR}"/>')
      o += [T(x + 8, yy + 19 + 16 * i, ln, 12, INK, 600 if hl else 400) for i, ln in enumerate(lines)]
      x += w
    yy += h
  o.append(T(M, yy + 20, "SFM-026 (System FMEA) above, SWF-39 (WP-W-04) below: the control of one row is the item of the next.", 12, MUTED))
  return o, yy + 30


def mini_stpa(y):
  o = []
  b = lambda x, yy, w, h, l1, l2, st: [f'<rect x="{x}" y="{yy}" width="{w}" height="{h}" rx="8" fill="#FFFFFF" stroke="{st}" stroke-width="1.5"/>',
                                       T(x + w / 2, yy + 22, l1, 13, INK, 700, "middle"), T(x + w / 2, yy + 40, l2, 11.5, MUTED, 400, "middle")]
  o += b(40, y, 200, 52, "openpilot + panda", "controller C2 / C3", MUTED)
  o += b(480, y, 200, 52, "Driver", "controller C1", "#3B5BA9")
  o += b(260, y + 118, 200, 52, "Steering (EPS)", "controlled process", MUTED)
  o += [f'<path d="M140 {y + 52} V{y + 144} H260" fill="none" stroke="#C2410C" stroke-width="1.6"/>',
        T(146, y + 98, "torque", 11.5, "#C2410C", 600),
        f'<path d="M240 {y + 22} H480" stroke="{BAD}" stroke-width="2.4" stroke-dasharray="7 5"/>',
        f'<path d="M352 {y + 12} l16 20 M368 {y + 12} l-16 20" stroke="{BAD}" stroke-width="2.6"/>',
        T(360, y + 50, "UCA-17: take-over alert", 12, BAD, 700, "middle"), T(360, y + 66, "not given, or after the driver can react", 12, BAD, 600, "middle"),
        f'<path d="M580 {y + 52} V{y + 144} H460" fill="none" stroke="#3B5BA9" stroke-width="1.6"/>',
        T(574, y + 98, "takes over", 11.5, "#3B5BA9", 600, "end")]
  o.append(T(M, y + 196, "LS-20: the request is sent but not perceived, so it counts as not given.", 12.5, MUTED))
  return o, y + 206


GUIDE = {"M01": "NO", "M02": "STOPS", "M03": "UNASKED", "M04": "STUCK", "M05": "TOO MUCH", "M06": "PARTIAL", "M07": "EARLY",
         "M08": "LATE", "M09": "TOO SHORT", "M10": "TOO LONG", "M11": "DELAYED", "M12": "INVERSE", "M13": "ERRATIC", "M14": "UNEVEN"}


def mini_guidewords(y):
  if [m for m, _ in hm.MALFUNCTIONS] != list(GUIDE):
    fail("the HARA guide-word list changed; update GUIDE")
  fm = hm.FM["F-05"]
  hl = {mid for mid, (cls, _h, same, _t) in fm.items() if cls == hm.SC and (mid == "M01" or same == "M01")}
  o = [T(M, y + 12, "F-05 DRIVER INFORMATION AND WARNINGS × 14 GUIDE WORDS (HARA)", 11.5, MUTED, 700, mono=True)]
  cw, chh = (W - 2 * M - 6 * 6) / 7, 50
  for i, (mid, name) in enumerate(hm.MALFUNCTIONS):
    x, yy = M + (i % 7) * (cw + 6), y + 22 + (i // 7) * (chh + 6)
    cls = fm[mid][0]
    on = mid in hl
    fill = BAD_BG if on else "#FFFFFF" if cls == hm.SC else PANEL
    st = BAD if on else FAINT
    o.append(f'<rect x="{x:.1f}" y="{yy}" width="{cw:.1f}" height="{chh}" rx="6" fill="{fill}" stroke="{st}" stroke-width="{1.6 if on else 1}"/>')
    o += [T(x + 6, yy + 17, GUIDE[mid], 11.5, INK if cls == hm.SC else FAINT, 700, mono=True),
          T(x + 6, yy + 31, mid, 10, MUTED if cls == hm.SC else FAINT, 400, mono=True)]
    o.append(T(x + cw - 6, yy + chh - 8, cls, 10, BAD if on else MUTED if cls == hm.SC else FAINT, 700, "end", mono=True))
  y += 22 + 2 * (chh + 6) + 6
  o.append(T(M, y + 14, "Red: no alert (M01) and the guide words the HARA rates the same as it. SC: safety-relevant.", 12, MUTED))
  return o, y + 24


def mini_scenario(y):
  sc = dict(kind="curve", still=0.6, want=ss.CURVE,
            act=[(-10, 70), (100, 70), (190, 70), (255, 73), (318, 92), (366, 134), (402, 180), (428, 232)],
            ghost=[(190, 70), (250, 72), (310, 84), (360, 108), (400, 138), (430, 172), (452, 210)],
            labels=[(452, 18, "white dashed: siren muted", "#334155", "", "end"),
                    (452, 33, "red: siren at 0.29 s", "#334155", "", "end")],
            pills=ss.P((1, "SoC stalls at the curve entry", "bad", 0.30, 150),
                       (2, "Revoked 0.05 s · siren 0.29 s", "ok", 0.40, 174),
                       (3, "Driver corrects at 1.79 s", "drv", 0.55, 198)))
  inner = "".join(ss.SCENE["curve"](sc))
  o = [f'<svg x="{M}" y="{y}" width="460" height="250" viewBox="0 0 460 250"><rect width="460" height="250" rx="8" fill="{ss.GRASS}"/>{inner}</svg>']
  x = M + 476
  rows = [("F-04b SoC stall, curve", ""), ("siren", "0.29 s"), ("correction", "1.79 s"), ("muted", "2.89 s"), ("peak offset", "0.83 m"),
          ("muted", "3.64 m"), ("", ""), ("Engaged mismatch (c)", ""), ("siren", "0.63–0.88 s"), ("SG-02 budget", "1 s")]
  for i, (k, v) in enumerate(rows):
    if not v:
      o.append(T(x, y + 16 + 22 * i, k, 12, INK, 700))
    else:
      o += [T(x, y + 16 + 22 * i, k, 12, MUTED), T(W - M, y + 16 + 22 * i, v, 12.5, INK, 700, "end", mono=True)]
  o += [f'<rect x="{x}" y="{y + 228}" width="{W - M - x}" height="22" rx="11" fill="#FEF3C7" stroke="#B45309"/>',
        T(x + (W - M - x) / 2, y + 243, "SYNTHETIC · NO CREDIT", 10.5, "#92400E", 700, "middle", mono=True)]
  return o, y + 258


def mini_trace(y):
  chain = [("SG-02", "C", "goal"), ("FSR-02.05", "C", "functional"), ("TSR-516", "C", "technical"), ("SWSR-516 / 516b", "B → C", "software"),
           ("tests", "", "host · HIL not run")]
  o, n = [], len(chain)
  bw = (W - 2 * M - (n - 1) * 22) / n
  for i, (ident, asil, kind) in enumerate(chain):
    x = M + i * (bw + 22)
    bad = asil.startswith("B")
    o += [f'<rect x="{x:.1f}" y="{y}" width="{bw:.1f}" height="74" rx="8" fill="{BAD_BG if bad else PANEL}" stroke="{BAD if bad else FAINT}" stroke-width="1.4"/>',
          *[T(x + bw / 2, y + 22 + 15 * j, ln, 12.5, INK, 700, "middle") for j, ln in enumerate(wrap_px(ident, bw - 12, 12.5, True))],
          T(x + bw / 2, y + 52, kind, 11, MUTED, 400, "middle")]
    if asil:
      o.append(T(x + bw / 2, y + 67, f"ASIL {asil}", 11, BAD if bad else MUTED, 700, "middle", mono=True))
    if i:
      o.append(f'<path d="M{x - 18:.1f} {y + 37} h12 m-5 -5 l5 5 l-5 5" fill="none" stroke="{MUTED}" stroke-width="1.6"/>')
  o.append(T(M, y + 100, "Found: SWSR-516 and SWSR-516b at ASIL B under an ASIL C TSR. Raised to C in PR #392.", 12.5, BAD, 600))
  return o, y + 110


MINI = {"fta": mini_fta, "fmea": mini_fmea, "stpa": mini_stpa, "guidewords": mini_guidewords, "scenario": mini_scenario, "trace": mini_trace}


def fig_route(i, r):
  o, y = head(f"{i}. {r['name']}: {r['asks']}", r["records"], f"ROUTE {i} OF 6 · {r['short']}")
  d, y = MINI[r["key"]](y + 10)
  o += d
  o.append(T(M, y + 24, "WHAT IT GAVE", 11.5, INK, 700, mono=True))
  p, y = para(M, y + 44, r["gave"], W - 2 * M, 13, INK)
  o += p
  o.append(T(M, y + 10, "WATCH", 11.5, MUTED, 700, mono=True))
  q, y = para(M, y + 30, r["watch"], W - 2 * M, 13, MUTED)
  o += q
  lab = "SLOTS THIS ROUTE PINNED DOWN" if r["fixed"] else "THIS ROUTE FIXES NO SLOT; IT CHECKS THE ATTRIBUTES"
  s, y = strip(y + 6, TSR_SHORT, lit=r["fixed"], label=f"TSR-516(c), ABRIDGED: {lab}", size=11.5)
  o += s
  return svg(f"Route {i}: {r['name']}", f"How the {r['name']} reaches TSR-516, and the slots of its anatomy it fixed: {', '.join(r['fixed']) or 'none'}.", y + 16, o)


def fig_tsr516c():
  o, y = head("TSR-516(c), split into slots: before and after the FRET pilot",
              "The FRET pilot restated the text in structured English and checked it against panda f4803c5. The split shows "
              "where the old text was weak: the 0.5 s guard was one tick off, and nothing said how long or how loud.",
              "TSR-516(c) · WP-S-02 v0.52 → v0.53")
  s, y = strip(y + 6, TSR_OLD, marks=OLD_MARKS, label="v0.52 (SUPERSEDED 2026-10-21)", size=11.5)
  o += s
  s, y = strip(y + 14, TSR_NOW, label="v0.53 (CURRENT)", size=11.5)
  o += s
  o.append(T(M, y + 30, "FRETISH (PILOT, NO EVIDENCE CREDIT)", 11.5, MUTED, 700, mono=True))
  x, yy = M, y + 56
  for part, k in FRETISH:
    w = tw(part, 12.5, False, True) + 14
    if x + w > W - M:
      x, yy = M, yy + 34
    o += [f'<rect x="{x:.1f}" y="{yy - 18}" width="{w:.1f}" height="26" rx="5" fill="{FILL[k]}" stroke="{COL[k]}"/>',
          T(x + 7, yy, part, 12.5, INK, 600, mono=True)]
    x += w + 6
  p, y = para(M, yy + 34, "The FRETish has no OBJECT slot of its own: siren_on is both what is done and to what. FF-04, on (b), "
              "is in the same row: the EPS-fault persistence clause now replaces the 0.5 s bound instead of contradicting it.",
              W - 2 * M, 12.5, MUTED)
  return svg("TSR-516(c) before and after", "TSR-516(c) split into six slots for WP-S-02 v0.52 and v0.53, with the FRET "
             "findings FF-05 and FF-06 marked on the old text, and the FRETish sentence coloured by slot.", y + 12, o + p)


# ============================================================================ the page
def link(p):
  return f"[`{Path(p).name}`](../../{p})"


def page():
  L = ["<!-- Generated by assurance/02-concept/fsc/fsc_routes.py; do not edit by hand. -->", "",
       "# One requirement, six routes", "",
       "How do we know a safety requirement is the right one? One way to check is to reach it more than once, by methods "
       "that look from different sides, and see whether they agree. This page takes one requirement and walks it through "
       "six methods that already run in this repository. Each page ends with the same anatomy strip, so you can see which "
       "part of the requirement each method actually pinned down.", "",
       "**Specimen:** SG-02 (no loss of lateral control without an adequate take-over warning, ASIL C, ≤ 1 s to warning) "
       "→ [FSR-02.05](../WP-C-04-functional-safety-concept.md) → [TSR-516](../../03-system/WP-S-02-technical-safety-requirements.md) "
       "(b) and (c): the panda's own siren when it ends actuation authority for a reason the driver did not cause.", "",
       "Every record quoted below is checked against its file when this page is built, so a route whose record changes "
       "fails CI. The plant results are synthetic (DSR-12) and carry no evidence credit.", "",
       "## The anatomy", "",
       "![FSR-02.05 split into six slots: TRIGGER, AGENT, MODAL, ACTION, OBJECT, CONSTRAINT, with the FRET field of each](figures/fig-c04-r1-anatomy.svg)", "",
       "| Slot | Question | FRET field | A defect looks like |", "|---|---|---|---|",
       "| TRIGGER | When does it apply? | condition (and scope) | a condition no element can observe, or one narrower than the parent's |",
       "| AGENT | Who does it? | component | an element that fails with the fault it must catch |",
       "| MODAL | How binding? | shall | *should*, *may*, or two *shalls* in one sentence that cannot be tested apart |",
       "| ACTION | Does what? | response | a verb with no observable result |",
       "| OBJECT | To what? | response | an output no test can see at the item's boundary |",
       "| CONSTRAINT | How fast, how long, how much? | timing | a start without a reference point, a bound with no duration or level |", "",
       "ASIL, parent, allocation and verification method are attributes: they travel with the requirement but are not part of its sentence.", "",
       "## The six routes", "",
       "![Six route cards, each with the question it asks and the slots it fixed, above the TSR-516 box](figures/fig-c04-r2-routes.svg)", ""]
  for i, r in enumerate(ROUTES, 1):
    L += [f"### {i}. {r['name']}", "", f"![Route {i}, {r['name']}: {r['records']}](figures/fig-c04-r3-{i}-{r['key']}.svg)", "",
          "Sources (quoted, checked at build): " + "; ".join(f"{label} in {link(p)}" for p, _, label in r["src"]) + ".", ""]
  L += ["## Two cross-checks", "",
        f"**FRET** (pilot, {link('models/fret/fretish-requirements.md')}, no evidence credit) restated six TSRs in structured English and checked "
        "them against the code. It found seven places where the text and the code disagreed (FF-01…FF-07). Three of them, "
        "FF-04, FF-05 and FF-06, are in TSR-516 and are exactly anatomy defects: the CONSTRAINT slot had no duration and no "
        "level, and the TRIGGER was off by one task tick. All seven are fixed in WP-S-02 v0.53.", "",
        "![TSR-516(c) split into slots for v0.52 and v0.53, FF-05 and FF-06 marked on the old text, and the FRETish sentence](figures/fig-c04-r4-tsr516c.svg)", "",
        f"**fmdtools** (TE-02, {link('07-supporting/tool-evaluations/TE-02-fmdtools-fault-propagation.md')}) propagated "
        "every joint fault through a model of the item. In 10 of the 31 effective SG-02 cut sets the model needs the siren "
        "to fail as well, so the siren is what keeps them from being single points. The tightest, a selfdrived hang "
        "({BE-2.21}), is warned 0.78 s after the loss, a margin of 0.22 s to SG-02's 1 s. Synthetic, no evidence credit.", "",
        "## How the methods compare", "",
        "| Method | Shines at | Watch for | Fixed here |", "|---|---|---|---|",
        "| Fault tree | Showing that one cause removes both steering and the SoC's warning, so the warning needs an independent agent | Credit only as current as its event texts | AGENT, TRIGGER |",
        "| FMEA | Naming the control, then giving the control its own failure mode | Rows age with the code | ACTION, OBJECT |",
        "| STPA | Perception: an alert the driver does not notice is not given | Loss scenarios age; it missed (c) until LS-37 was added | CONSTRAINT, TRIGGER |",
        "| Guide words | Systematic: LATE, DELAYED and TOO SHORT are each 'same as missing' | Generic: names the alert, not who sounds it | MODAL, CONSTRAINT |",
        "| Scenario | Numbers in seconds and metres the driver lives with | Synthetic; the plant's driver and road are assumptions | CONSTRAINT values |",
        "| Trace | Completeness: every parent, ASIL and test is there | Confirms, does not derive; a complete trace can carry wrong text | attributes |",
        "| FRET | Ambiguity: off-by-one bounds, missing durations, contradictions | Only as good as the variables it is given | TRIGGER, CONSTRAINT |", "",
        "No single route filled all six slots. The guide words had TOO SHORT long before the TSR said how long; it took FRET to "
        "notice that the TSR had not carried it over.", "",
        "## Checklist", "",
        "Applied to TSR-516(c) as it stands in WP-S-02 v0.53.", "",
        "| # | Check | TSR-516(c) |", "|---|---|---|",
        "| 1 | TRIGGER is observable by the AGENT and names the requirement that detects it | Yes: the heartbeat flag (TSR-307(a)) and PCM_CRUISE |",
        "| 2 | TRIGGER is no narrower than the parent's, and the parent covers it | Yes since WP-C-04 v0.26: FSR-02.05 covers any end of authority that is not an observed driver action. Before, it named only SoC communication loss and an MCU reset |",
        "| 3 | AGENT does not fail with the fault it must catch | Yes: the safety MCU, not SoC software |",
        "| 4 | One MODAL per testable clause | Yes: (a)–(d) share one *shall* but each has its own trigger and bound |",
        "| 5 | ACTION and OBJECT are visible at the item's boundary | Yes: the siren output |",
        "| 6 | CONSTRAINT has a reference point, a bound, a duration and a level | Yes since v0.53 (FF-05, FF-06) |",
        "| 7 | The bound fits the parent's budget | Yes by design: 0.63–0.88 s in the plant against 1 s; not verified on hardware |",
        "| 8 | ASIL matches the parent's, or a decomposition is stated | TSR yes (C); SWSR-516 and SWSR-516b were B, raised to C in PR #392 |",
        "| 9 | A verification case exists for the method named | **Partly**: VS-FI-10 (b) targets (c) since PR #396; HIL test `test_16_engaged_mismatch_siren.py` proposed (panda PR #22, PR #402); neither has run on hardware |",
        "| 10 | Every route's record states the current behaviour | **No**: see below |", "",
        "## What the walk found", "",
        "These records are behind the requirement. Each is with its owner, through the coordinator.", "",
        "| Record | What is out of date | Owner |", "|---|---|---|",
        "| FSR-02.05 (WP-C-04 §5) | Trigger named only SoC communication loss and an MCU reset; TSR-516(b)/(c) cover any non-driver revocation and a failed cancel. Widened in WP-C-04 v0.26 | FSC |",
        "| SWSR-516, SWSR-516b (WP-W-02) | ASIL B under ASIL C; SWSR-516(b) listed the heartbeat \"not engaged\" case, which TSR-516 moved to (c). Both fixed in PR #392, with eight more SWSRs raised to C | software requirements |",
        "| WP-A-05 LS-20, LS-05 | Said the siren covers only heartbeat loss and an EPS fault; no loss scenario for (c). Fixed in PR #401 (v0.15, new LS-37) | STPA |",
        "| WP-A-04 BE-2.14; fta-fmea-map BE-2.14 note | Event text listed the baseline triggers; the map said (b)/(c) were not implemented. Fixed in PR #400 | FTA |",
        "| System FMEA F-04b entries (SFM-005.C2, SFM-006.C1) | Described a silent SoC stall; fixed in PR #398 (siren at 0.25 s) | System FMEA |",
        "| SW FMEA: `sw-fmea.yaml` SWF-036, SWF-039; WP-W-04 SWF-39 status | Said a 3 s engaged mismatch and credited only the heartbeat siren; fixed in PR #399 (rev 1.8, WP-W-04 v1.3), re-rating open | SW FMEA |",
        "| WP-V-05 VS-FI-31, VS-FI-10 | VS-FI-31 said 1 s persistence; no case targeted TSR-516(c). Fixed in PR #396 (WP-V-05 v0.7: 0.7 s; VS-FI-10 (b) and (b2)); HIL test proposed in panda PR #22 and PR #402, not run on hardware | verification |",
        "| fmdtools README | Said 58 sets where p4-timing.md and TE-02 say 61; fixed in PR #396 | fmdtools |", "",
        "## Regenerating", "",
        "```bash", "python3 fsc_routes.py          # write this page and its figures", "python3 fsc_routes.py --check  # CI: fail if stale or a quote is gone", "```", ""]
  return "\n".join(L)


def build():
  check_sources()
  out = {FIG / "fig-c04-r1-anatomy.svg": fig_anatomy(), FIG / "fig-c04-r2-routes.svg": fig_routes()}
  for i, r in enumerate(ROUTES, 1):
    out[FIG / f"fig-c04-r3-{i}-{r['key']}.svg"] = fig_route(i, r)
  out[FIG / "fig-c04-r4-tsr516c.svg"] = fig_tsr516c()
  out[PAGE] = page()
  return out


def main(argv):
  try:
    out = build()
  except RouteError as e:
    print(f"fsc_routes: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [p for p, s in out.items() if not p.exists() or p.read_text(encoding="utf-8") != s]
    stale += [p for p in FIG.glob("fig-c04-r*.svg") if p not in out]
    for p in stale:
      print(f"stale: {p.relative_to(A.parent)}", file=sys.stderr)
    if stale:
      print("run: python3 assurance/02-concept/fsc/fsc_routes.py", file=sys.stderr)
      return 1
    print(f"{len(out)} route outputs current")
    return 0
  for p, s in out.items():
    p.write_text(s, encoding="utf-8")
  print(f"wrote {len(out)} files")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
