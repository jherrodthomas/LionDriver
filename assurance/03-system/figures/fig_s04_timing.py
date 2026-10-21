#!/usr/bin/env python3
"""Draw the WP-S-04 timing figures (Figure 5-1 budgets per safety goal, Figure 5-2 EPS-fault warning chain).

The source of record is `../WP-S-04-timing-ftti-budget.md` (§3.7 budgets, §4 T-xx rows, §5 verdicts).
The numbers are in prose cells, so they are listed in DATA below; every number carries the exact
text it was read from (`src`). `--check` fails when such a text no longer appears in WP-S-04, so a
changed number forces the figure to be reviewed, and when a committed SVG differs from the output.

    python3 fig_s04_timing.py            # regenerate the SVGs
    python3 fig_s04_timing.py --check    # fail if a source text changed or an SVG is stale

Standard library only. Output is deterministic.
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "WP-S-04-timing-ftti-budget.md"
FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"

# ---------------------------------------------------------------- data (all times in seconds)
# lane kinds: ("value", v) bar 0..v; ("range", lo, hi) bar 0..lo solid, lo..hi light;
# ("none",) not detected; ("blank",) no time recorded. Optional "ticks": extra values marked on the bar.
# "limit": the value the code-derived times are compared with (red beyond it).

GROUPS = [
  {
    "title": "SG-01 · lateral", "sub": "ASIL C until re-rated (B‡)", "ftti": 0.5, "ftti_label": "FTTI 0.5 s",
    "src": ["**FTTI(SG-01) = 0.5 s**"],
    "rows": [
      {"title": "RX loss / corruption", "sub": "TSR-401 · margin ≥ 0.2 s", "fdti": 0.2, "frti": 0.1, "limit": 0.2,
       "budget_text": "FDTI ≤ 0.2 s + FRTI ≤ 0.1 s",
       "src": ["| SG-01 RX loss/corruption | 0.5 s | ≤ 0.2 s (TSR-401) | ≤ 0.1 s | ≥ 0.2 s |"],
       "base": {"kind": ("range", 1.0, 2.0), "text": "1–2 s (T-01)", "src": ["**1–2 s** (at `8b8c6ae`)"]},
       "ref": {"kind": ("value", 0.162), "ticks": [0.21], "text": "≤ 0.162 s; 0x262 ≈ 0.21 s (T-01)",
               "src": ["**≤ 0.162 s** for `0x1D2`", "`0x262` (25 Hz, ≈ 0.21 s"]}},
      {"title": "SoC heartbeat loss", "sub": "TSR-407 · margin ≥ 0.1 s", "fdti": 0.3, "frti": 0.1, "limit": 0.3,
       "budget_text": "FDTI ≤ 0.3 s + FRTI ≤ 0.1 s",
       "src": ["| SG-01 SoC heartbeat loss | 0.5 s | ≤ 0.3 s (TSR-407) | ≤ 0.1 s | ≥ 0.1 s |"],
       "base": {"kind": ("range", 4.0, 5.0), "text": "4–5 s, ignition on (T-06)", "src": ["**4–5 s** (ign on)"]},
       "ref": {"kind": ("value", 0.31), "text": "revoke ≤ 0.31 s (T-06a); SILENT 4–5 s (T-06b)",
               "src": ["**≤ 0.31 s** (0.3 s + one task period)", "| unchanged | 4–5 s (ign on), 1–2 s (ign off); TSR-510"]}},
      {"title": "SoC command stall", "sub": "TSR-408 · margin ≥ 0.35 s", "fdti": 0.05, "frti": 0.1, "limit": 0.05,
       "budget_text": "FDTI ≤ 0.05 s + FRTI ≤ 0.1 s",
       "src": ["| SG-01 SoC command stall | 0.5 s | ≤ 0.05 s (TSR-408) | ≤ 0.1 s | ≥ 0.35 s |"],
       "base": {"kind": ("range", 0.1, 2.1), "text": "0.1 s at host (T-13), then EPS ≈ 2 s (T-23)",
                "src": ["0.1 s at host (T-13), then EPS ≈ 2 s (T-23)"]},
       "ref": {"kind": ("blank",), "text": "no reference-build time in §4", "src": []}},
      {"title": "MCU execution fault (hang)", "sub": "TSR-501 · margin ≥ 0.3 s", "fdti": 0.1, "frti": 0.1, "limit": 0.1,
       "budget_text": "FDTI ≤ 0.1 s + FRTI ≤ 0.1 s",
       "src": ["| SG-01 MCU execution fault | 0.5 s | ≤ 0.1 s (TSR-501;", "| ≤ 0.1 s (reset + relay release) | ≥ 0.3 s |"],
       "base": {"kind": ("none",), "text": "not detected (T-09)", "src": ["| MCU hang | ≤ 0.1 s | not detected (T-09) |"]},
       "ref": {"kind": ("value", 0.09), "text": "≈ 90 ms nominal, LSI-dependent (T-09a)", "src": ["**≈ 90 ms** nominal"]}},
      {"title": "Relay stuck", "sub": "TSR-506 · margin ≥ 0.1 s", "fdti": 0.3, "frti": 0.1, "limit": 0.3,
       "budget_text": "FDTI ≤ 0.3 s + FRTI ≤ 0.1 s",
       "src": ["| SG-01 relay stuck | 0.5 s | ≤ 0.3 s (TSR-506) | ≤ 0.1 s | ≥ 0.1 s |"],
       "base": {"kind": ("range", 1.0, 2.0), "text": "1–2 s window after mode set (T-08)",
                "src": ["| Relay stuck released | ≤ 0.3 s | 1–2 s window (T-08) |"]},
       "ref": {"kind": ("blank",), "text": "no reference-build time in §4", "src": []}},
    ],
  },
  {
    "title": "SG-02 / SG-06 · warning", "sub": "ASIL B", "ftti": 1.0, "ftti_label": "1 s to warning",
    "src": ["| SG-02/06 loss without warning | 1 s to warning | ≤ 0.5 s | ≤ 0.5 s |"],
    "rows": [
      {"title": "EPS fault → siren", "sub": "TSR-110, TSR-516 · OI-8", "fdti": 0.5, "frti": 0.5, "limit": 1.0,
       "budget_text": "detect ≤ 0.5 s + warn ≤ 0.5 s",
       "src": [],
       "base": {"kind": ("blank",), "text": "no time at 8b8c6ae (T-28 added 2026-10-12)", "src": []},
       "ref": {"kind": ("value", 0.96), "text": "siren ≤ 0.96 s worst case (T-28, DQ-048)",
               "src": ["siren ≤ 0.7 s + 10 ms + 2 × 125 ms ≈ **0.96 s** after fault onset worst case"]}},
      {"title": "SoC heartbeat loss → siren", "sub": "FSR-02.05, TSR-516", "fdti": 0.5, "frti": 0.5, "limit": 1.0,
       "budget_text": "detect ≤ 0.5 s + warn ≤ 0.5 s",
       "src": [],
       "base": {"kind": ("range", 4.0, 5.0), "text": "siren starts at T-06: 4–5 s (T-07)",
                "src": ["| 3 s siren if authority within last 5 s | starts at T-06 |"]},
       "ref": {"kind": ("value", 0.56), "text": "≈ 0.56 s if engaged, all builds, c33343b (T-07a)",
               "src": ["siren ≤ 0.3 s + 10 ms + 250 ms ≈ **0.56 s** after the last heartbeat",
                       "| warning within SG-02 1 s (§3.7) | siren at T-06: 4–5 s (T-07) |"]}},
    ],
  },
  {
    "title": "SG-03 / SG-04 · longitudinal", "sub": "ASIL B", "ftti": 1.0, "ftti_label": "FTTI 1 s",
    "src": ["| SG-03/04 | 1 s | ≤ 0.5 s | ≤ 0.3 s | ≥ 0.2 s |"],
    "rows": [
      {"title": "Longitudinal fault classes", "sub": "§3.3, §3.4 · margin ≥ 0.2 s", "fdti": 0.5, "frti": 0.3, "limit": 0.5,
       "budget_text": "FDTI ≤ 0.5 s + FRTI ≤ 0.3 s", "src": [],
       "single": {"kind": ("blank",), "text": "no §4 row is mapped to this class", "src": []}},
    ],
  },
  {
    "title": "SG-05 · release on driver action", "sub": "ASIL B", "ftti": 0.2, "ftti_label": "FTTI 0.2 s",
    "src": [],
    "rows": [
      {"title": "Brake / cancel", "sub": "TSR-302, TSR-109 · margin TBD", "fdti": 0.03, "frti": 0.01, "limit": 0.03, "tbd": True,
       "budget_text": "≤ 30 ms + ≤ 10 ms + EPS/PCM (TBD)",
       "src": ["| SG-05 brake/cancel | 0.2 s | ≤ 30 ms | ≤ 10 ms + EPS/PCM | TBD |"],
       "base": {"kind": ("value", 0.03), "ticks": [0.025], "text": "25 ms brake, 30 ms cruise (T-04)",
                "src": ["25 ms (brake 40 Hz), 30 ms (cruise 33 Hz)"]},
       "ref": {"kind": ("blank",), "text": "no reference-build time in §4", "src": []}},
      {"title": "Steering override", "sub": "TSR-304 · margin TBD", "fdti": 0.04, "frti": None, "limit": 0.04, "tbd": True,
       "budget_text": "≤ 40 ms + t_ovr, then FRTI ≤ 0.1 s",
       "src": ["| SG-05 steering override | 0.2 s | ≤ 40 ms + t_ovr | ≤ 0.1 s | TBD |"],
       "base": {"kind": ("none",), "text": "not in the envelope (§5)", "src": ["| Steering override | ≤ 0.2 s | not in envelope |"]},
       "ref": {"kind": ("blank",), "text": "no reference-build time in §4", "src": []}},
    ],
  },
  {
    "title": "SG-07 · PCS preservation", "sub": "ASIL B · FTTI preliminary", "ftti": 0.2, "ftti_label": "FTTI 0.2 s",
    "src": ["**Preliminary FTTI(SG-07, forwarding loss) = 0.2 s.**"],
    "rows": [
      {"title": "Forwarding loss", "sub": "TSR-711, TSR-501, TSR-706 · margin 0 (OI-7)", "fdti": 0.1, "frti": 0.1, "limit": 0.1,
       "budget_text": "FDTI ≤ 0.1 s + FRTI ≤ 0.1 s",
       "src": ["| SG-07 forwarding loss | 0.2 s (preliminary, §3.6) | ≤ 0.1 s (TSR-711;",
               "| ≤ 0.1 s (TSR-706, incl. relay drop-out) | 0 (depends on LSI tolerance, OI-7) |"],
       "base": {"kind": ("none",), "text": "MCU hang not detected (T-09)", "src": []},
       "ref": {"kind": ("value", 0.09), "text": "MCU hang ≈ 90 ms (T-09a); TSR-711: no time", "src": []}},
    ],
  },
  {
    # each row has its own FTTI (group "ftti" None): the budget is the time to the warning, then the driver acts
    "title": "Warning paths · §3.8", "sub": "no fault reaction: budget to the warning, the driver avoids the hazard",
    "ftti": None, "src": ["### 3.8 Warning paths without a fault reaction"],
    "rows": [
      {"title": "SG-02 insufficient lateral control", "sub": "§3.8.1 · Δa_y 1 m/s² · driver t_r not met",
       "ftti": 1.1, "fdti": 0.4, "frti": 0.1, "limit": 0.4,
       "budget_text": "FTTI 1.1 s · FDTI ≤ 0.4 s + FRTI ≤ 0.1 s",
       "src": ["| SG-02 insufficient lateral control (warning path, §3.8.1) | 1.1 s to 0.6 m at a 1 m/s² deficit;",
               "| ≤ 0.4 s (steerSaturated, T-30) | ≤ 0.1 s to alert |"],
       "single": {"kind": ("value", 0.4), "text": "steerSaturated at 0.4 s + 1 frame (T-30)",
                  "src": ["`steerLimitTimer` = 0.4 s (LKA torque cars) | 0.4 s + 1 frame |"]}},
      {"title": "SG-06 late braking warning (FCW)", "sub": "§3.8.2 · 1.0 s gap · FCW needed ≤ 0.6 s",
       "ftti": 1.6, "fdti": None, "frti": 0.1, "limit": 0.6, "tbd": True,
       "budget_text": "FTTI 1.6 s (off scale) · FCW onset TBD",
       "src": ["| SG-06 late or insufficient braking warning (FCW, §3.8.2) | 1.6 s at 1.0 s time gap;",
               "| FCW onset after the lead brakes (T-31, not derived) | ≤ 0.1 s to alert |"],
       "single": {"kind": ("blank",), "text": "not derived; to be measured (T-31, M-12)",
                  "src": ["| not derived; measure (M-12) |"]}},
      {"title": "Unintended engagement (latent gate fault)", "sub": "§3.8.3 · TSR-630 · margin ≥ 0.1 s",
       "ftti": 0.5, "fdti": 0.3, "frti": 0.1, "limit": 0.3,
       "budget_text": "FTTI 0.5 s · FDTI ≤ 0.3 s + FRTI ≤ 0.1 s",
       "src": ["| SG-01 / SG-03 unintended engagement (System FMEA SG-008, §3.8.3) | 0.5 s (as SG-01) |",
               "latent panda authority while disengaged ≤ 0.3 s (TSR-630, T-32) | ≤ 0.1 s | ≥ 0.1 s |"],
       "single": {"kind": ("none",), "text": "not implemented (TSR-630, T-32)",
                  "src": ["| not implemented (TSR-630) | not detected |"]}},
      {"title": "SG-08 driver not supervising", "sub": "§3.8.4 · first alert · OI-11",
       "ftti": 6.0, "fdti": 5.0, "frti": None, "limit": 5.0, "tbd": True,
       "budget_text": "FTTI 6 s (off scale) · alert at 5 s + DM latency",
       "src": ["| SG-08 driver not supervising (§3.8.4) | ≤ 6 s from loss of attention to the first alert",
               "first vision alert at 5 s of distraction (policy timer, T-24)"],
       "single": {"kind": ("value", 5.0), "text": "first vision alert at 5 s (T-24); latency not measured",
                  "src": ["vision 5/8/13 s"]}},
    ],
  },
]

# Figure 5-2: EPS-fault warning chain (T-28)
T28 = {
  "persist": 0.7, "task": 0.010, "tick": 0.250,  # tick: two 125 ms periods, the speaker sounds only on odd 8 Hz ticks
  "src": ["siren once the fault has persisted 0.7 s (70 ticks) after it was seen while `controls_allowed`",
          "siren ≤ 0.7 s + 10 ms + 2 × 125 ms ≈ **0.96 s** after fault onset worst case (TSR-516(b))",
          "With the 1 s persistence before panda",
          "LKA refused on receipt of the fault frame (TSR-110)"],
}

# ---------------------------------------------------------------- palette
INK, MUTED, HAIR = "#0F172A", "#475569", "#E2E8F0"
TEAL, ORANGE, GREY = "#0F766E", "#C2410C", "#94A3B8"
AMBER, RED = "#D97706", "#D2553F"
BASE_FILL, BASE_LIGHT = "#64748B", "#CBD5E1"
REF_FILL, REF_LIGHT = "#D97706", "#FCD9A8"


def t(x, y, s, size=11, fill=INK, weight=None, anchor=None, italic=False, extra=""):
  a = f' font-size="{size}" fill="{fill}"'
  if weight:
    a += f' font-weight="{weight}"'
  if anchor:
    a += f' text-anchor="{anchor}"'
  if italic:
    a += ' font-style="italic"'
  return f'<text x="{x:g}" y="{y:g}"{a}{extra}>{escape(s)}</text>'


def rect(x, y, w, h, fill, stroke="none", sw=1, rx=0, dash=None, opacity=None):
  a = f'<rect x="{x:g}" y="{y:g}" width="{max(w, 0):g}" height="{h:g}" fill="{fill}"'
  if stroke != "none":
    a += f' stroke="{stroke}" stroke-width="{sw:g}"'
  if rx:
    a += f' rx="{rx:g}"'
  if dash:
    a += f' stroke-dasharray="{dash}"'
  if opacity is not None:
    a += f' fill-opacity="{opacity:g}"'
  return a + "/>"


def line(x1, y1, x2, y2, stroke, sw=1, dash=None, cap=None):
  a = f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" stroke="{stroke}" stroke-width="{sw:g}"'
  if dash:
    a += f' stroke-dasharray="{dash}"'
  if cap:
    a += f' stroke-linecap="{cap}"'
  return a + "/>"


def header(out, w, title, subtitle, ref1, ref2):
  out.append(f'<rect width="{w}" height="100%" fill="#FFFFFF"/>')
  out.append(t(40, 44, title, 20, INK, 700))
  out.append(t(40, 66, subtitle, 12.5, MUTED))
  out.append(t(w - 40, 44, ref1, 11, MUTED, anchor="end"))
  out.append(t(w - 40, 62, ref2, 11, MUTED, anchor="end"))
  out.append(line(40, 82, w - 40, 82, HAIR))


DEFS = f"""<defs>
  <pattern id="tbd" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#F8FAFC"/><line x1="0" y1="0" x2="0" y2="6" stroke="#CBD5E1" stroke-width="2"/></pattern>
  <marker id="aI" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{INK}"/></marker>
  <marker id="aR" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{RED}"/></marker>
  <marker id="aM" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{MUTED}"/></marker>
</defs>"""


# ---------------------------------------------------------------- Figure 5-1
W1 = 1280
X0, X1, TMAX = 350, 950, 1.2
VX = 966
LANE = 18


def X(v):
  return X0 + (X1 - X0) * min(v, TMAX) / TMAX


def fhti(r):
  """FHTI = FDTI + FRTI when both budgets are numbers, else None (ISO 26262-1:2018 definition)."""
  if r["fdti"] is None or r["frti"] is None or r.get("tbd"):
    return None
  return round(r["fdti"] + r["frti"], 3)


def code_lane(out, y, lane, limit, solid, light):
  """Draw one code-derived lane; y = lane top. Returns nothing."""
  kind = lane["kind"]
  bh, by = 10, y + 4
  cy = y + 9
  if kind[0] == "blank":
    out.append(line(X0, cy, X0 + 14, cy, BASE_LIGHT, 1.2))
  elif kind[0] == "none":
    out.append(f'<path d="M{X0:g} {cy:g}H{X1 + 6:g}" stroke="{RED}" stroke-width="1.8" stroke-dasharray="6 4" fill="none" marker-end="url(#aR)"/>')
  else:
    lo = kind[1]
    hi = kind[2] if kind[0] == "range" else lo
    # solid part 0..lo, light part lo..hi; red where beyond limit
    out.append(rect(X0, by, X(lo) - X0, bh, solid))
    if hi > lo:
      out.append(rect(X(lo), by, X(hi) - X(lo), bh, light))
    if hi > limit:
      out.append(rect(X(limit), by, X(hi) - X(limit), bh, RED, opacity=.9 if lo > limit else .9))
      if lo < hi and lo > limit:
        # keep the range distinction visible inside the red part
        out.append(rect(X(lo), by, X(hi) - X(lo), bh, "#FFFFFF", opacity=.45))
    for tv in lane.get("ticks", []):
      if tv > limit:
        out.append(rect(X(max(lo, limit)), by, X(tv) - X(max(lo, limit)), bh, RED, opacity=.9))
      out.append(line(X(tv), by - 3, X(tv), by + bh + 3, INK, 1.4))
    if hi > TMAX:  # off-scale break and arrow
      bx = X1 - 10
      out.append(f'<path d="M{bx - 3:g} {by + bh + 2:g}L{bx + 1:g} {by - 2:g}M{bx + 2:g} {by + bh + 2:g}L{bx + 6:g} {by - 2:g}" stroke="#FFFFFF" stroke-width="2.4"/>')
      out.append(f'<path d="M{X1:g} {by - 1:g}L{X1 + 7:g} {cy:g}L{X1:g} {by + bh + 1:g}z" fill="{RED if hi > limit else solid}"/>')
  col = RED if lane.get("warn") else (MUTED if kind[0] == "blank" else INK)
  out.append(t(VX, cy + 3.5, lane["text"], 10.5, col, 600 if lane.get("warn") else None, italic=kind[0] == "blank"))


def figure_5_1() -> str:
  out: list[str] = []
  rows_h = 0
  for g in GROUPS:
    rows_h += 30
    for r in g["rows"]:
      rows_h += LANE * (2 if "single" in r else 3) + 12
  top = 140
  legend_y = top + rows_h + 22
  H = legend_y + 92
  out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W1}" height="{H}" viewBox="0 0 {W1} {H}" font-family="{FONT}" role="img" aria-labelledby="t d">')
  out.append('<title id="t">Figure 5-1. FTTI, detection and reaction budgets per safety goal against code-derived times (WP-S-04 §3.7, §4, §5)</title>')
  out.append('<desc id="d">For each fault class of §3.7 the budget bar shows the fault detection time interval, the fault reaction time interval and the margin up to the fault tolerant time interval, on a linear time axis from 0 to 1.2 s. Below it the code-derived times of §4 are drawn to the same scale for the original baseline 8b8c6ae (grey) and for the reference build bf6ce8c (amber, implemented but not verified on hardware). Red marks the part of a time beyond its budget. The right column gives the fault handling time interval FHTI = FDTI + FRTI where both budgets are numbers. The EPS-fault siren of the reference build sounds at up to 0.96 s worst case since panda bf8102a, within the SG-02 1 s warning budget (DQ-048). Since panda c33343b (all builds) the siren after SoC heartbeat loss sounds about 0.56 s after the last heartbeat when authority was granted, within the budget; the 1 Hz path at 4 to 5 s is unchanged. The last group draws the warning paths of §3.8, each against its own FTTI; the FCW and driver-monitoring FTTIs lie beyond the 1.2 s axis. No time has been measured.</desc>')
  out.append(DEFS)
  header(out, W1, "Figure 5-1 · Timing budgets per safety goal vs code-derived times",
         "Fault onset at t = 0 · budgets from §3.7 · code-derived times from §4 (T-xx) · drawn to scale · nothing measured yet (§6)",
         "WP-S-04 §5", "budgets §3.7 · times §4")
  # column heads and axis
  out.append(t(40, 104, "FAULT CLASS · REQUIREMENT", 10, MUTED, 700, extra=' letter-spacing=".06em"'))
  out.append(t((X0 + X1) / 2, 104, "TIME FROM FAULT ONSET (s)", 10, MUTED, 700, "middle", extra=' letter-spacing=".06em"'))
  out.append(t(VX, 104, "CODE-DERIVED TIME (§4)", 10, MUTED, 700, extra=' letter-spacing=".06em"'))
  for i in range(13):
    v = i / 10
    x = X(v)
    out.append(line(x, 130, x, top + rows_h, "#F1F5F9" if i % 5 else "#E2E8F0", 1))
    out.append(line(x, 126, x, 130, MUTED, 1))
    out.append(t(x, 122, "0" if i == 0 else f"{v:.1f}", 10, MUTED, anchor="middle"))
  out.append(line(X0, 130, X1, 130, MUTED, 1))
  y = top
  for g in GROUPS:
    gy = y
    out.append(rect(40, gy, W1 - 80, 24, "#F8FAFC", "#E2E8F0", 1, rx=4))
    out.append(t(50, gy + 16, g["title"], 12.5, INK, 700))
    tw = len(g["title"]) * 7.3
    out.append(t(50 + tw + 10, gy + 16, g["sub"], 10.5, MUTED))
    y += 30
    gstart = y
    for r in g["rows"]:
      nl = 2 if "single" in r else 3
      rh = LANE * nl + 12
      out.append(t(40, y + 13, r["title"], 12, INK, 600))
      out.append(t(40, y + 28, r["sub"], 10, MUTED))
      # lane labels
      labels = ["budget", "§4"] if nl == 2 else ["budget", "8b8c6ae", "bf6ce8c"]
      for i, lab in enumerate(labels):
        col = AMBER if lab == "bf6ce8c" else MUTED
        out.append(t(338, y + i * LANE + 12.5, lab, 9.5, col, 600, "end"))
      # budget lane
      by, bh = y + 3, 12
      fdti, frti, ftti = r["fdti"], r["frti"], r.get("ftti", g["ftti"])
      end = 0
      if fdti is not None:
        out.append(rect(X0, by, X(fdti) - X0, bh, "#CCFBF1", TEAL, 1))
        end = fdti
        if frti is not None:
          out.append(rect(X(fdti), by, X(fdti + frti) - X(fdti), bh, "#FFEDD5", ORANGE, 1))
          end = fdti + frti
      if r.get("tbd"):
        out.append(rect(X(end), by, X(ftti) - X(end), bh, "url(#tbd)", GREY, 1, dash="3 2"))
      elif ftti - end > 1e-9:
        out.append(rect(X(end), by, X(ftti) - X(end), bh, "#FFFFFF", GREY, 1, dash="3 2"))
      h = fhti(r)
      out.append(t(VX, y + 12.5, r["budget_text"] + (f" · FHTI ≤ {h:g} s" if h is not None else ""), 10.5, MUTED))
      if g["ftti"] is None:  # per-row FTTI, drawn at the axis end when off scale
        out.append(line(X(ftti), y, X(ftti), y + rh - 6, INK, 1.6, "4 2" if ftti > TMAX else None))
      # FDTI guide through the code lanes (detection rows only)
      if r["limit"] < ftti - 1e-9:
        out.append(line(X(r["limit"]), y + LANE, X(r["limit"]), y + LANE * nl, TEAL, 1, "2 2"))
      if nl == 2:
        code_lane(out, y + LANE, r["single"], r["limit"], BASE_FILL, BASE_LIGHT)
      else:
        code_lane(out, y + LANE, r["base"], r["limit"], BASE_FILL, BASE_LIGHT)
        code_lane(out, y + 2 * LANE, r["ref"], r["limit"], REF_FILL, REF_LIGHT)
      y += rh
    if g["ftti"] is None:
      continue
    # FTTI line for the group, with label pill in the group header
    fx = X(g["ftti"])
    out.append(line(fx, gstart - 4, fx, y - 6, INK, 1.6))
    lab = g["ftti_label"]
    pw = len(lab) * 6.0 + 16
    out.append(rect(fx - pw / 2, gy + 3, pw, 18, INK, rx=9))
    out.append(t(fx, gy + 15.5, lab, 10, "#FFFFFF", 700, "middle"))
  # legend
  ly = legend_y
  out.append(line(40, ly - 10, W1 - 40, ly - 10, HAIR))
  L = []
  gx = 40
  def item(sw_svg, label, width):
    nonlocal gx
    L.append(f'<g transform="translate({gx},{ly})">{sw_svg}{t(34, 9, label, 10.5, INK)}</g>')
    gx += width
  item(rect(0, 0, 26, 12, "#CCFBF1", TEAL, 1), "FDTI budget", 120)
  item(rect(0, 0, 26, 12, "#FFEDD5", ORANGE, 1), "FRTI budget", 120)
  item(rect(0, 0, 26, 12, "#FFFFFF", GREY, 1, dash="3 2"), "Margin to FTTI", 140)
  item(rect(0, 0, 26, 12, "url(#tbd)", GREY, 1, dash="3 2"), "Not quantified (TBD)", 170)
  item(line(13, -3, 13, 15, INK, 1.6), "FTTI / warning budget", 175)
  item(line(13, -3, 13, 15, TEAL, 1, "2 2"), "FDTI budget, compared with the times below", 290)
  ly2 = ly + 26
  gx = 40
  ly, ly_save = ly2, ly
  item(rect(0, 1, 26, 10, BASE_FILL), "Baseline 8b8c6ae, code-derived", 225)
  item(rect(0, 1, 26, 10, REF_FILL), "Reference build bf6ce8c: implemented, not verified on hardware", 410)
  item(rect(0, 1, 13, 10, BASE_FILL) + rect(13, 1, 13, 10, BASE_LIGHT), "Range (lower – upper)", 175)
  item(rect(0, 1, 26, 10, RED, opacity=.9), "Beyond its budget", 150)
  ly = ly2 + 26
  gx = 40
  item(f'<path d="M0 6H22" stroke="{RED}" stroke-width="1.8" stroke-dasharray="6 4" marker-end="url(#aR)"/>', "Not detected", 120)
  item(f'<path d="M0 1L7 6L0 11z" fill="{MUTED}"/>' + line(-2, 6, 0, 6, MUTED), "Off scale (> 1.2 s, value in the right column)", 320)
  item(line(13, -2, 13, 14, INK, 1.4), "Second value on the same bar", 220)
  L.append(t(W1 - 40, ly + 9, "FHTI = FDTI + FRTI. Per-frame rows of §3.7 (SG-01 limits, SG-07 content) have no detection budget and are not drawn.", 10, MUTED, anchor="end"))
  out.extend(L)
  out.append("</svg>")
  return "\n".join(out) + "\n"


# ---------------------------------------------------------------- Figure 5-2
W2 = 1280
P0, P1, PMAX = 300, 1180, 1.5


def P(v):
  return P0 + (P1 - P0) * v / PMAX


def figure_5_2() -> str:
  out: list[str] = []
  H = 580
  p, k, s = T28["persist"], T28["task"], T28["tick"]
  siren = p + k + s
  out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W2}" height="{H}" viewBox="0 0 {W2} {H}" font-family="{FONT}" role="img" aria-labelledby="t d">')
  out.append('<title id="t">Figure 5-2. EPS-fault warning chain of the reference build against the SG-02 1 s warning budget (WP-S-04 T-28, OI-8)</title>')
  out.append('<desc id="d">Time axis from the first EPS fault frame. The envelope refuses STEERING_LKA with torque on receipt of the fault frame (TSR-110). The panda 100 Hz safety task counts 0.7 s of persistence once the fault has been seen while controls are allowed (DQ-048), adds up to 10 ms of task period, and the 8 Hz tick drives the speaker only on every other tick, adding up to 250 ms, so the siren starts at most 0.96 s after fault onset, within the SG-02 1 s warning budget. From the end of the persistence it is at most 0.26 s, inside TSR-516 0.5 s. With the earlier 1 s persistence the chain reached 1.26 s (OI-8). Not verified on hardware.</desc>')
  out.append(DEFS)
  header(out, W2, "Figure 5-2 · EPS-fault warning chain (T-28) vs the SG-02 warning budget",
         "Reference build at panda bf8102a (persistence 0.7 s, DQ-048) · upper bounds from §4 T-28 · drawn to scale · not verified on hardware",
         "WP-S-04 §5, OI-8", "T-28 · §3.7 SG-02/06 row")
  # axis
  ay = 118
  for i in range(round(PMAX * 10) + 1):
    v = i / 10
    x = P(v)
    out.append(line(x, ay + 4, x, 404, "#F1F5F9" if i % 5 else "#E2E8F0", 1))
    out.append(line(x, ay, x, ay + 4, MUTED))
    out.append(t(x, ay - 6, "0" if i == 0 else f"{v:.1f} s" if i % 5 == 0 else f"{v:.1f}", 10, MUTED, anchor="middle"))
  out.append(line(P0, ay + 4, P1, ay + 4, MUTED))
  # lanes
  lanes = [
    ("SG-02 budget (§3.7)", "1 s to warning", 140),
    ("EPS · 0x262 LKA_STATE", "vehicle CAN, bus 0", 196),
    ("Envelope · toyota.h", "opendbc 338f5fc", 252),
    ("Safety task · 100 Hz", "eps_fault_siren.h", 308),
    ("Speaker tick · 8 Hz", "siren on every other tick", 364),
  ]
  for name, sub, ly in lanes:
    out.append(t(40, ly + 13, name, 12, INK, 600))
    out.append(t(40, ly + 28, sub, 10, MUTED))
  # budget lane
  by = 146
  out.append(rect(P0, by, P(0.5) - P0, 16, "#CCFBF1", TEAL, 1))
  out.append(rect(P(0.5), by, P(1.0) - P(0.5), 16, "#FFEDD5", ORANGE, 1))
  out.append(t((P0 + P(0.5)) / 2, by + 12, "detection ≤ 0.5 s", 10.5, TEAL, 600, "middle"))
  out.append(t((P(0.5) + P(1.0)) / 2, by + 12, "to warning ≤ 0.5 s", 10.5, ORANGE, 600, "middle"))
  # EPS lane: fault present from 0
  ey = 204
  out.append(rect(P0, ey, P(PMAX) - P0, 14, "#F1F5F9", GREY, 1))
  out.append(t(P(0.08), ey + 11, "LKA_STATE fault code present (persistent fault)", 10.5, MUTED))
  out.append(f'<path d="M{P0:g} {ey - 6:g}L{P0 + 6:g} {ey + 7:g}L{P0:g} {ey + 20:g}L{P0 - 6:g} {ey + 7:g}z" fill="{RED}"/>')
  out.append(t(P0 + 10, ey - 5, "first fault frame (t = 0)", 10, RED, 600))
  # envelope lane: refused from receipt
  vy = 260
  out.append(rect(P0, vy, P(PMAX) - P0, 14, "#FDE68A", AMBER, 1))
  out.append(t(P(0.08), vy + 11, "STEERING_LKA with torque refused from receipt of the fault frame (TSR-110)", 10.5, INK))
  # safety task lane: persistence 0..1 s, then +10 ms
  sy = 316
  out.append(rect(P0, sy, P(p) - P0, 14, REF_LIGHT, AMBER, 1))
  out.append(t((P0 + P(p)) / 2, sy + 11, "fault persists 0.7 s (70 ticks) once seen with controls_allowed", 10.5, INK, anchor="middle"))
  out.append(rect(P(p), sy, P(p + k) - P(p), 14, AMBER))
  # speaker tick lane: up to two 125 ms tick periods (the speaker sounds only on odd ticks)
  ky = 372
  out.append(rect(P(p + k), ky, P(p + k + s / 2) - P(p + k), 14, REF_LIGHT, AMBER, 1))
  out.append(rect(P(p + k + s / 2), ky, P(siren) - P(p + k + s / 2), 14, AMBER))
  out.append(f'<path d="M{P(p + k):g} {sy + 14:g}V{ky:g}" stroke="{MUTED}" stroke-width="1.2" fill="none" marker-end="url(#aM)"/>')
  # siren marker
  out.append(f'<path d="M{P(siren):g} {ky - 4:g}V{ky + 20:g}" stroke="{RED}" stroke-width="2"/>')
  out.append(t(P(siren) + 8, ky + 11, "siren", 11, RED, 700))
  # budget line at 1 s and the overrun
  out.append(line(P(1.0), 136, P(1.0), 404, INK, 1.6))
  out.append(rect(P(1.0) - 34, 404, 68, 18, INK, rx=9))
  out.append(t(P(1.0), 416.5, "1 s budget", 10, "#FFFFFF", 700, "middle"))
  out.append(line(P0, 136, P0, 404, MUTED, 1))
  # brackets
  def bracket(x1, x2, y, col, label, sub, anchor_x=None):
    out.append(f'<path d="M{x1:g} {y - 6:g}V{y:g}H{x2:g}V{y - 6:g}" stroke="{col}" stroke-width="1.4" fill="none"/>')
    ax = anchor_x if anchor_x is not None else (x1 + x2) / 2
    out.append(t(ax, y + 16, label, 11, col, 700, "middle"))
    out.append(t(ax, y + 30, sub, 10, MUTED, anchor="middle"))
  # task and tick annotations above their bars, with leader text to the right
  out.append(t(P(siren) + 50, sy + 11, "+ ≤ 10 ms task period", 10, MUTED))
  out.append(line(P(p + k) + 2, sy + 7, P(siren) + 46, sy + 7, BASE_LIGHT, 1))
  out.append(t(P(p + k) - 8, ky + 11, "+ ≤ 2 × 125 ms: the speaker sounds only on every other 8 Hz tick", 10, MUTED, anchor="end"))
  bracket(P0, P(siren), 456, TEAL, f"From fault onset: ≤ {siren:.2f} s worst case, within the 1 s warning budget (margin {1.0 - siren:.2f} s)",
          "how §3.7 measures the SG-02 row (FDTI + FRTI from fault onset)")
  bracket(P(p), P(siren), 512, AMBER, f"From the end of the persistence: ≤ {siren - p:.2f} s, within TSR-516(b) ≤ 0.5 s",
          "persistence 0.7 s (DQ-048)", anchor_x=P(siren) - 200)
  # OI-8 note box on the left under lanes
  out.append(rect(40, 440, 236, 96, "#F0FDFA", TEAL, 1.2, rx=8))
  out.append(t(54, 460, "OI-8 · implemented (DQ-048)", 12, TEAL, 700))
  for i, s_ in enumerate(["Lead decision 2026-10-14:", "• persistence 0.7 s (was 1 s)", "  → siren ≤ 0.96 s from onset", "• panda bf8102a, HIL timing open"]):
    out.append(t(54, 478 + i * 14, s_, 10, INK))
  out.append("</svg>")
  return "\n".join(out) + "\n"


# ---------------------------------------------------------------- build / check
OUTPUTS = {
  "fig-s04-5-1-timing-budgets.svg": figure_5_1,
  "fig-s04-5-2-eps-fault-warning.svg": figure_5_2,
}


def sources() -> list[str]:
  found = []
  for g in GROUPS:
    found += g.get("src", [])
    for r in g["rows"]:
      found += r.get("src", [])
      for k in ("base", "ref", "single"):
        if k in r:
          found += r[k].get("src", [])
  return found + T28["src"]


def missing_sources(md: str) -> list[str]:
  return [s for s in sources() if s not in md]


def build() -> dict[str, str]:
  return {name: fn() for name, fn in OUTPUTS.items()}


def main(argv: list[str]) -> int:
  check = "--check" in argv
  missing = missing_sources(SOURCE.read_text(encoding="utf-8"))
  if missing:
    for s in missing:
      print(f"source text no longer in WP-S-04: {s}", file=sys.stderr)
    print("review the figure data in fig_s04_timing.py against WP-S-04 and regenerate", file=sys.stderr)
    return 1
  outputs = build()
  if check:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"stale: {n}", file=sys.stderr)
    if stale:
      print("run: python3 assurance/03-system/figures/fig_s04_timing.py", file=sys.stderr)
      return 1
    print(f"fig_s04_timing: {len(outputs)} figure(s) current, {len(sources())} source texts found")
    return 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
  print(f"fig_s04_timing: wrote {len(outputs)} figure(s)")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
