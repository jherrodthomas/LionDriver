#!/usr/bin/env python3
"""Draw the WP-C-01 mode and assumption figures.

  Figure 4-1  Operating modes and actuation authority: the §4 table as one state diagram. Each arrow names the
              state-machine record transitions it stands for (sm-selfdrived, sm-toy-auth, sm-safety-mode) and is
              coloured by who enforces it: the panda envelope, the host only, or the host only while the envelope
              still allows actuation (GAP-16).
  Figure 4-2  One engagement, three layers in time: an illustrative episode on a shared time axis. Only the 3 s
              soft-disable and the 1–30 min lockout are code values.
  Figure 7-1  Assumptions of use by subject and status: the 15 rows of the §7 table, grouped by what they assume.

Sources of record:
  - `../WP-C-01-item-definition.md` §4 and §7 tables (parsed);
  - the state-machine records `assurance/05-software/state-machines/*.yaml`, loaded with
    `assurance/trace/tools/check_state_machines.py` (every transition ID drawn must exist there);
  - prose and code values are listed below with the exact text they were read from (`src`, checked in WP-C-01;
    `CODE_SRC`, checked in the cited code file).
`--check` fails when a `src` text is gone, a drawn record ID does not exist, a §4 or §7 row is not drawn, or a
committed SVG differs.

    python3 fig_c01_modes.py            # regenerate the SVGs
    python3 fig_c01_modes.py --check    # fail if a source changed or an SVG is stale

Standard library only. Output is deterministic.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "WP-C-01-item-definition.md"
ASSURANCE = HERE.parents[1]
REPO = ASSURANCE.parent
sys.path.insert(0, str(ASSURANCE / "trace" / "tools"))
import check_state_machines as csm

# ---------------------------------------------------------------- palette (assurance figure style)

FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SFMono-Regular', Menlo, Consolas, monospace"
INK, MUTED, FAINT, LINE, HAIR = "#0F172A", "#475569", "#94A3B8", "#CBD5E1", "#E2E8F0"
CHIP = "#F8FAFC"
SAFETY, SAFETY_BG = "#C2410C", "#FFF7ED"
SW, SW_BG = "#0F766E", "#F0FDFA"
HW, HW_BG = "#4F46E5", "#EEF2FF"
AMBER, AMBER_BG = "#D97706", "#FFFBEB"
RED, RED_BG = "#D2553F", "#FEF2F2"
GREY_BG = "#F1F5F9"
BORDER = "#64748B"

# ---------------------------------------------------------------- code values (each with its source text)

# Text that must still appear in WP-C-01 for what the figures draw from prose.
PROSE = {
  "off": ["Ignition off or device offroad. pandad puts the panda in `NO_OUTPUT` (`pandad.cc:204-207`)",
          "A panda found in `SILENT` is also switched to `NO_OUTPUT` (`pandad.cc:195-196`)"],
  "disengaged": ["Car safety mode active, `controls_allowed = false`",
                 "None (non-zero torque or accel rejected, `lateral.h:98-101`)"],
  "enabled": ["Engaged after the PCM cruise rising edge and no NO_ENTRY condition (`state.py:79-90`)"],
  "overriding": ["Driver gas or steering input while engaged. Longitudinal blocked while gas pressed (`longitudinal.h:3-5`)"],
  "soft": ["Fault detected; warning; actuation continues up to 3 s (`state.py:7`) — see GAP-16"],
  "immediate": ["Critical fault; control released at once"],
  "lockout": ["DM non-compliance; engagement prevented for 1–30 min (`policy.py:47-49`)"],
  "chill": ["Longitudinal policy selection (MPC vs end-to-end model). Upstream default is Experimental (`params_keys.h:43`, GAP-18)",
            "| OI-8 | Decide whether Experimental Mode (end-to-end longitudinal, traffic light stopping) is in the reference ODD |"],
  "debug": ["Developer modes that replace control processes (`process_config.py:34-47`)",
            "**Excluded from the reference configuration** (OI-5)"],
  "aou05": ["The PCM bounds ACC acceleration and deceleration requests to its own ACC envelope and honours the cancel bit"],
}
# Code values drawn as numbers or as behaviour: (file, exact text). The line-cited ones also give the line.
CODE_SRC = [
  ("openpilot/selfdrive/selfdrived/state.py", 7, "SOFT_DISABLE_TIME = 3  # seconds"),
  ("openpilot/selfdrive/monitoring/policy.py", 49, "for n_min in [1, 5, 15, 30]]"),
  ("opendbc_repo/opendbc/safety/longitudinal.h", 4, "return controls_allowed && !gas_pressed_prev;"),
  ("opendbc_repo/opendbc/safety/lateral.h", 99, "if (!controls_allowed && torque_requested) {"),
  ("openpilot/selfdrive/pandad/pandad.cc", 0, "panda->set_safety_model(cereal::CarParams::SafetyModel::NO_OUTPUT);"),
  ("openpilot/system/manager/process_config.py", 0,
   'PythonProcess("selfdrived", "openpilot.selfdrive.selfdrived.selfdrived", only_onroad)'),
  ("openpilot/selfdrive/controls/controlsd.py", 0,
   "CC.cruiseControl.cancel = CS.cruiseState.enabled and (not CC.enabled or not self.CP.pcmCruise)"),
  ("openpilot/selfdrive/selfdrived/events.py", 0, 'ET.IMMEDIATE_DISABLE: ImmediateDisableAlert("Controls Mismatch")'),
  ("openpilot/selfdrive/selfdrived/events.py", 0, "ET.NO_ENTRY: too_distracted_alert"),
]
# The record text the 3 s soft-disable is also read from (sm-selfdrived E1).
E1_ACTION = "soft-disable timer = 3 s (300 cycles)"
SOFT_S, LOCKOUT_MIN = 3, (1, 30)

# ---------------------------------------------------------------- SVG helpers (copied from trace_figures.py)


def el(tag: str, text: str | None = None, **attrs) -> str:
  """One SVG element; attribute names use _ for - (stroke_width -> stroke-width), a trailing _ is dropped."""
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


def line(x1, y1, x2, y2, stroke=MUTED, sw=1.4, dash="", marker="") -> str:
  return el("line", None, x1=fmt(x1), y1=fmt(y1), x2=fmt(x2), y2=fmt(y2), stroke=stroke, stroke_width=sw,
            stroke_dasharray=dash, marker_end=f"url(#{marker})" if marker else "")


def path(d, stroke=MUTED, sw=1.4, fill="none", dash="", marker="", opacity="") -> str:
  return el("path", None, d=d, stroke=stroke, stroke_width=sw, fill=fill, stroke_dasharray=dash,
            marker_end=f"url(#{marker})" if marker else "", opacity=opacity, stroke_linejoin="round")


def pill_width(s: str, size=10) -> float:
  return 14 + 6.0 * len(s) * size / 10


def pill(x, y, s, fill, size=10, color="#FFFFFF", stroke="none", dash="", anchor="start") -> list[str]:
  """A rounded tag, height 18, vertical centre y; left edge x (or right edge for anchor='end')."""
  w = pill_width(s, size)
  if anchor == "end":
    x -= w
  return [rect(x, y - 9, w, 18, fill=fill, stroke=stroke, rx=9, dash=dash, sw=1.2),
          text(x + w / 2, y + 3.5, s, size=size, fill=color, weight=700, anchor="middle")]


MARKERS = {"muted": MUTED, "safety": SAFETY, "red": RED, "ink": INK}


def svg(width: int, height: int, title: str, desc: str, body: list[str]) -> str:
  defs = "".join(
    f'<marker id="{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" ' +
    f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for k, c in MARKERS.items())
  defs += ('<pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">' +
           f'<rect width="8" height="8" fill="#FFFFFF"/><line x1="0" y1="0" x2="0" y2="8" stroke="{HAIR}" ' +
           'stroke-width="2.5"/></pattern>')
  defs += ('<pattern id="hatch-red" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">' +
           f'<rect width="8" height="8" fill="{RED_BG}"/><line x1="0" y1="0" x2="0" y2="8" stroke="#F5B5A8" ' +
           'stroke-width="2"/></pattern>')
  head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" ' +
          f'font-family="{FONT}" role="img">')
  return "\n".join([head, el("title", title), el("desc", desc), f"<defs>{defs}</defs>",
                    rect(0, 0, width, height, fill="#FFFFFF", stroke="none", rx=0, sw=0), *body, "</svg>"]) + "\n"


def header(width: int, number: str, title: str, subtitle: str, ref: str) -> list[str]:
  return [text(40, 44, f"Figure {number} · {title}", size=20, weight=700),
          text(40, 66, subtitle, size=12.5, fill=MUTED),
          text(width - 40, 44, ref, size=11, fill=MUTED, anchor="end"),
          line(40, 82, width - 40, 82, stroke=HAIR, sw=1)]


def wrap(s: str, width_px: float, size=10.5, factor=0.55) -> list[str]:
  """Greedy word wrap with a conservative average glyph width."""
  limit = max(8, int(width_px / (factor * size)))
  out: list[str] = []
  cur = ""
  for w in s.split():
    if cur and len(cur) + 1 + len(w) > limit:
      out.append(cur)
      cur = w
    else:
      cur = f"{cur} {w}" if cur else w
  if cur:
    out.append(cur)
  return out or [""]


# ---------------------------------------------------------------- source parsing


def split_row(row: str) -> list[str]:
  cells = re.split(r"(?<!\\)\|", row.strip())
  return [c.strip() for c in cells[1:-1]]


def section(md: str, heading: str) -> str:
  body = md.split(heading, 1)[1]
  return re.split(r"\n#{2,3} ", body, maxsplit=1)[0]


def table(body: str) -> list[list[str]]:
  rows = [split_row(r) for r in body.splitlines() if r.startswith("|")]
  return [r for r in rows[2:] if r]


def plain(s: str) -> str:
  s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
  return s.replace("**", "").replace("`", "").strip()


def modes_table(md: str) -> list[dict]:
  body = section(md, "## 4. Operating modes and states")
  head = split_row(next(r for r in body.splitlines() if r.startswith("|")))
  if head != ["Mode", "Description", "Actuation"]:
    raise SystemExit(f"WP-C-01 §4 header changed: {head}; update fig_c01_modes.py")
  return [{"mode": m, "desc": d, "act": a} for m, d, a in table(body)]


def aou_table(md: str) -> list[dict]:
  body = section(md, "## 7. Assumptions of use (AoU) and external measures")
  head = split_row(next(r for r in body.splitlines() if r.startswith("|")))
  if head != ["ID", "Assumption", "Credited in", "Verification approach", "Status"]:
    raise SystemExit(f"WP-C-01 §7 header changed: {head}; update fig_c01_modes.py")
  return [{"id": i, "text": plain(t), "credit": plain(c), "verif": plain(v), "status": plain(s)}
          for i, t, c, v, s in table(body)]


def chips(actuation: str) -> list[str]:
  """Actuation column -> chips: 'lateral', 'longitudinal', 'longitudinal (forced decel)', 'no longitudinal', 'none'."""
  a = plain(actuation).lower()
  if a.startswith("none"):
    return ["none"]
  out = []
  if "lateral" in a:
    out.append("lateral")
  if "no longitudinal" in a:
    out.append("no longitudinal")
  elif "longitudinal" in a:
    out.append("longitudinal (forced decel)" if "forced decel" in a else "longitudinal")
  return out


def records() -> dict[str, dict]:
  """machine name -> record, loaded with check_state_machines.load (no own parsing)."""
  return {sm["machine"]: sm for sm in (csm.load(p) for p in sorted(csm.SM_DIR.glob("*.yaml")))}


def transition(recs: dict, machine: str, tid: str) -> dict | None:
  return next((t for t in recs[machine]["transitions"] if t["id"] == tid), None)


# ---------------------------------------------------------------- Figure 4-1 data

SD, TA, SM = "SM-SELFDRIVED", "SM-TOY-AUTH", "SM-SAFETY-MODE"
PREFIX = {SD: "H", TA: "P", SM: "P"}

# §4 state rows -> box. host / panda: record states the box stands for (checked against the records).
MODES = {
  "Off / offroad": {
    "key": "off", "host": [], "host_text": "selfdrived: not running", "panda": [(SM, "NOOUTPUT"), (SM, "SILENT")],
    "panda_text": "NOOUTPUT", "detail": ["ignition off or device offroad;", "SILENT is switched to NOOUTPUT"], "code": "pandad.cc",
    "src": "off"},
  "Onroad, disengaged": {
    "key": "dis", "host": ["disabled"], "host_text": "selfdrived: disabled", "panda": [(SM, "TOYOTA"), (TA, "NOT_ALLOWED")],
    "panda_text": "TOYOTA · controls_allowed = 0", "detail": ["car safety mode active; non-zero", "torque or accel rejected"],
    "code": "lateral.h:98-101", "src": "disengaged"},
  "Pre-enabled / enabled": {
    "key": "en", "host": ["preEnabled", "enabled"], "host_text": "selfdrived: preEnabled →P1→ enabled",
    "panda": [(SM, "TOYOTA"), (TA, "ALLOWED")], "panda_text": "TOYOTA · controls_allowed = 1",
    "detail": ["after the PCM cruise rising edge, no NO_ENTRY"], "code": "state.py:79-90", "src": "enabled"},
  "Overriding": {
    "key": "ovr", "host": ["overriding"], "host_text": "selfdrived: overriding", "panda": [(TA, "ALLOWED")],
    "panda_text": "controls_allowed = 1 · gas blocks long.", "detail": ["driver gas or steering input"],
    "code": "longitudinal.h:3-5", "src": "overriding"},
  "Soft disabling": {
    "key": "soft", "host": ["softDisabling"], "host_text": f"selfdrived: softDisabling · {SOFT_S} s",
    "panda": [(TA, "ALLOWED")], "panda_text": "controls_allowed = 1 (unchanged)",
    "detail": ["fault detected; warning; actuation", f"continues up to {SOFT_S} s"], "code": "state.py:7", "src": "soft",
    "tag": "GAP-16 · envelope does not know"},
  "Immediate disable": {
    "key": "imm", "host": [], "host_text": "transient: X1 ends in disabled", "panda": [], "panda_text": "",
    "detail": ["critical fault; control released at once"], "code": "", "src": "immediate", "dashed": True},
  "Driver lockout": {
    "key": "lock", "host": ["disabled"], "host_text": "selfdrived: disabled · N1 refuses", "panda": [], "panda_text": "",
    "detail": ["DM non-compliance; engagement prevented", f"for {LOCKOUT_MIN[0]}–{LOCKOUT_MIN[1]} min"],
    "code": "policy.py:47-49", "src": "lockout"},
}
# Record IDs named inside the mode boxes (host_text): P1 (preEnabled -> enabled), X1, N1.
BOX_IDS = [(SD, "P1"), (SD, "X1"), (SD, "N1")]
CONFIG = {
  "Chill vs Experimental Mode": "chill",
  "Debug / maneuver / joystick modes": "debug",
}
CODE_REFS = ["pandad.cc:204-207", "lateral.h:98-101", "state.py:79-90", "longitudinal.h:3-5", "state.py:7",
             "policy.py:47-49", "params_keys.h:43", "process_config.py:34-47"]

# Kinds of enforcement
ENV, HOST, GAP = "envelope", "host", "gap16"
KIND_COLOR = {ENV: (SAFETY, "safety", 2.2), HOST: (MUTED, "muted", 1.7), GAP: (RED, "red", 2.2)}

# Figure 4-1 geometry
W = 1280
BOX = {
  "off": (40, 336, 196, 156),
  "dis": (380, 300, 252, 220),
  "imm": (380, 112, 252, 124),
  "lock": (380, 596, 252, 140),
  "ovr": (900, 112, 290, 140),
  "en": (900, 320, 290, 160),
  "soft": (900, 560, 290, 176),
}
GROUP = (880, 96, 360, 656)   # the engaged states (host): X1, X2 and envelope faults leave from its edge


def envelope_fault_ids(recs: dict) -> tuple[list[str], list[str], list[str]]:
  """sm-toy-auth transitions that clear authority on a fault: (all builds, reference only, not implemented).

  T2/T3 (driver), T6 (host no longer engaged) and T7 (mode set) are drawn on their own arrows."""
  own = {"T2", "T3", "T6", "T7"}
  allb, ref, notimpl = [], [], []
  for t in recs[TA]["transitions"]:
    if t["to"] != "NOT_ALLOWED" or t["from"] not in ("ALLOWED", "any") or t["id"] in own:  # only a granted authority is cleared
      continue
    if t.get("code", "").startswith("not implemented"):
      notimpl.append(t["id"])
    elif t.get("build") == "reference":
      ref.append(t["id"])
    else:
      allb.append(t["id"])
  return allb, ref, notimpl


def arrows(recs: dict) -> list[dict]:
  """Every transition arrow of Figure 4-1: geometry, label lines, the record IDs it stands for, who enforces it."""
  fault, fault_ref, _ = envelope_fault_ids(recs)
  gx = GROUP[0]
  ox, oy, ow, oh = BOX["off"]
  dx, dy, dw, dh = BOX["dis"]
  ix, iy, iw, ih = BOX["imm"]
  lx, ly, lw, lh = BOX["lock"]
  vx, vy, vw, vh = BOX["ovr"]
  ex, ey, ew, eh = BOX["en"]
  sx, sy, sw_, sh = BOX["soft"]
  a = []
  # off <-> disengaged
  a.append({"name": "onroad", "kind": ENV, "d": f"M{ox + ow},{360 + 18} L{dx},{360 + 18}",
                "ids": [(SM, "M2"), (SM, "M4")],
                "labels": [(ox + ow + 8, 360, "onroad: 0xdc TOYOTA", "start", INK, 600),
                        (ox + ow + 8, 373, "P: M2 · M4 (reference)", "start", SAFETY, "")]})
  a.append({"name": "offroad", "kind": ENV, "d": f"M{dx},{430} L{ox + ow},{430}",
                "ids": [(SM, "M2"), (SM, "M5"), (TA, "T7")],
                "labels": [(ox + ow + 8, 412, "offroad: NOOUTPUT", "start", INK, 600),
                        (ox + ow + 8, 448, "P: M2 · M5 (ref.) · T7", "start", SAFETY, "")]})
  a.append({"name": "heartbeat lost", "kind": ENV, "d": f"M{dx},{486} L{ox + ow},{486}",
                "ids": [(SM, "M7"), (TA, "T7")],
                "labels": [(ox + ow + 8, 476, "heartbeat lost", "start", INK, 600),
                        (ox + ow + 8, 504, "P: M7 → SILENT · T7", "start", SAFETY, "")]})
  # engage
  ye = 352
  a.append({"name": "engage", "kind": ENV, "d": f"M{dx + dw},{ye} L{ex},{ye}",
                "ids": [(SD, "D1"), (SD, "D3"), (SD, "D2"), (TA, "T1")],
                "labels": [(dx + dw + 10, ye - 39, "cruise set: PCM rising edge", "start", INK, 600),
                        (dx + dw + 10, ye - 26, "H: D1 · D3 (D2 → overriding)", "start", MUTED, ""),
                        (dx + dw + 10, ye - 9, "P: T1 grants authority", "start", SAFETY, 600)]})
  a.append({"name": "refused", "kind": None, "d": "", "ids": [(SD, "N1"), (TA, "T8")],
                "labels": [(dx + dw + 10, ye + 17, "refused: H N1 (NO_ENTRY) · P T8", "start", MUTED, "")]})
  # driver disengage
  yd = 424
  a.append({"name": "driver disengage", "kind": ENV, "d": f"M{gx},{yd} L{dx + dw},{yd}",
                "ids": [(SD, "X2"), (TA, "T2"), (TA, "T3")],
                "labels": [(dx + dw + 10, yd - 22, "brake · cancel · cruise off", "start", INK, 600),
                        (dx + dw + 10, yd - 9, "H: X2 · P: T2, T3 clear", "start", SAFETY, "")]})
  # envelope fault
  yf = 484
  ref_s = " · ref.: " + " ".join(fault_ref) if fault_ref else ""
  a.append({"name": "envelope fault", "kind": ENV, "d": f"M{gx},{yf} L{dx + dw},{yf}",
                "ids": [(TA, t) for t in fault + fault_ref] + [(SD, "X1")],
                "labels": [(dx + dw + 10, yf - 35, "envelope fault (RX, heartbeat)", "start", INK, 600),
                        (dx + dw + 10, yf - 22, "P: " + " ".join(fault) + ref_s, "start", SAFETY, ""),
                        (dx + dw + 10, yf - 9, "H follows: controlsMismatch → X1", "start", MUTED, "")]})
  # soft disable timer runs out
  ys = sy + 80
  xv = 724
  a.append({"name": "SD2", "kind": GAP, "d": f"M{sx},{ys} L{xv},{ys} L{xv},{dy + dh - 8} L{dx + dw},{dy + dh - 8}",
                "ids": [(SD, "SD2"), (TA, "T2"), (TA, "T6")],
                "labels": [(xv + 10, ys - 22, f"{SOFT_S} s timer runs out", "start", RED, 700),
                        (xv + 10, ys - 9, "H: SD2 → disabled", "start", RED, ""),
                        (xv + 10, ys + 17, "P keeps authority until T2", "start", INK, 600),
                        (xv + 10, ys + 30, "(host cancel → PCM cruise", "start", MUTED, ""),
                        (xv + 10, ys + 43, "off; AOU-05) or T6", "start", MUTED, ""),
                        (xv + 10, ys + 56, "(3 heartbeats, engaged = 0)", "start", MUTED, "")]})
  # immediate disable
  yi = iy + 56
  a.append({"name": "X1", "kind": HOST, "d": f"M{gx},{yi} L{ix + iw},{yi}",
                "ids": [(SD, "X1")],
                "labels": [(ix + iw + 10, yi - 22, "IMMEDIATE_DISABLE", "start", INK, 600),
                        (ix + iw + 10, yi - 9, "H: X1 (any engaged state)", "start", MUTED, "")]})
  a.append({"name": "X1 end", "kind": HOST, "d": f"M{ix + 126},{iy + ih} L{ix + 126},{dy}",
                "ids": [(SD, "X1"), (TA, "T2"), (TA, "T6")],
                "labels": [(ix + 136, iy + ih + 26, "at once (X1 → disabled)", "start", MUTED, ""),
                        (ix + 136, iy + ih + 39, "P: T2 after cancel, or T6", "start", MUTED, "")]})
  # lockout
  a.append({"name": "lockout", "kind": HOST, "d": f"M{lx + 70},{dy + dh} L{lx + 70},{ly}",
                "ids": [],
                "labels": [(lx + 62, dy + dh + 30, "DM non-compliance", "end", INK, 600),
                        (lx + 62, dy + dh + 43, "dmonitoringd (no record)", "end", MUTED, "")]})
  a.append({"name": "lockout expires", "kind": HOST, "d": f"M{lx + 180},{ly} L{lx + 180},{dy + dh}",
                "ids": [], "dash": "5 4",
                "labels": [(lx + 188, dy + dh + 30, "expires after", "start", MUTED, ""),
                        (lx + 188, dy + dh + 43, f"{LOCKOUT_MIN[0]}–{LOCKOUT_MIN[1]} min", "start", MUTED, "")]})
  # inside the engaged group
  a.append({"name": "E2", "kind": HOST, "d": f"M{ex + 96},{ey} L{ex + 96},{vy + vh}",
                "ids": [(SD, "E2")],
                "labels": [(ex + 88, vy + vh + 28, "gas / steering", "end", INK, 600),
                        (ex + 88, vy + vh + 41, "H: E2", "end", MUTED, "")]})
  a.append({"name": "O2", "kind": HOST, "d": f"M{ex + 190},{vy + vh} L{ex + 190},{ey}",
                "ids": [(SD, "O2")],
                "labels": [(ex + 198, vy + vh + 28, "released", "start", INK, 600),
                        (ex + 198, vy + vh + 41, "H: O2", "start", MUTED, "")]})
  a.append({"name": "E1", "kind": GAP, "d": f"M{ex + 96},{ey + eh} L{ex + 96},{sy}",
                "ids": [(SD, "E1")],
                "labels": [(ex + 88, ey + eh + 34, "SOFT_DISABLE", "end", RED, 700),
                        (ex + 88, ey + eh + 47, "H only: E1", "end", RED, "")]})
  a.append({"name": "SD1", "kind": HOST, "d": f"M{ex + 190},{sy} L{ex + 190},{ey + eh}", "dash": "5 4",
                "ids": [(SD, "SD1")],
                "labels": [(ex + 198, ey + eh + 34, "cleared", "start", INK, 600),
                        (ex + 198, ey + eh + 47, "H: SD1", "start", MUTED, "")]})
  xo = vx + vw + 22
  a.append({"name": "O1", "kind": GAP, "d": f"M{vx + vw},{vy + 100} L{xo},{vy + 100} L{xo},{sy + 40} L{sx + sw_},{sy + 40}",
                "ids": [(SD, "O1")],
                "labels": [(xo + 5, (ey + eh + sy) / 2 + 4, "O1", "start", RED, 700)]})
  return a


def mode_box(b: list[str], key: str, title: str, info: dict, acts: list[str]) -> None:
  x, y, w, h = BOX[key]
  fill, stroke, sw, dash = "#FFFFFF", INK, 1.8, ""
  if key in ("off", "lock"):
    fill, stroke, sw = GREY_BG, BORDER, 1.5
  elif key in ("en", "ovr"):
    fill, stroke = SAFETY_BG, SAFETY
  elif key == "soft":
    fill, stroke = RED_BG, RED
  if info.get("dashed"):
    dash, sw = "6 4", 1.4
  b.append(rect(x, y, w, h, fill=fill, stroke=stroke, sw=sw, rx=12, dash=dash))
  b.append(text(x + 14, y + 25, title, size=14.5, weight=700))
  ty = y + 45
  b.append(text(x + 14, ty, info["host_text"], size=10.5, fill=MUTED, family=MONO))
  if info["panda_text"]:
    ty += 17
    b.append(text(x + 14, ty, info["panda_text"], size=10.5, fill=SAFETY, family=MONO))
  ty += 6
  for d in info["detail"]:
    ty += 15
    b.append(text(x + 14, ty, d, size=10.5, fill=MUTED))
  if info["code"]:
    ty += 15
    b.append(text(x + 14, ty, info["code"], size=10, fill=FAINT, family=MONO))
  cy = y + h - 22
  if info.get("tag"):
    b += pill(x + 14, y + h - 20, info["tag"], RED, size=10)
    cy -= 26
  cx = x + 14
  for c in acts:
    if c == "none":
      b += pill(cx, cy, "no actuation", "#FFFFFF", color=MUTED, stroke=FAINT)
    elif c == "no longitudinal":
      b += pill(cx, cy, c, "url(#hatch)", color=MUTED, stroke=FAINT, dash="4 3")
    else:
      b += pill(cx, cy, c, SAFETY)
    cx += pill_width(c if c != "none" else "no actuation") + 8


def label_lines(b: list[str], labels) -> None:
  for x, y, s, anchor, fill, weight in labels:
    if s:
      b.append(text(x, y, s, size=10.5, fill=fill, anchor=anchor, weight=weight))


def figure_4_1(md: str, recs: dict) -> str:
  rows = modes_table(md)
  b: list[str] = []
  b += header(W, "4-1", "Operating modes and actuation authority",
              "The §4 modes as one state diagram. Each arrow names the state-machine record transitions it stands for " +
              "and is coloured by who enforces it.", "WP-C-01 §4")
  gx, gy, gw, gh = GROUP
  b.append(rect(gx, gy, gw, gh, fill="#FFFFFF", stroke=FAINT, dash="6 4", rx=14, sw=1.2))
  b += pill(gx + 20, gy, "ENGAGED · host selfdrived", BORDER, size=9.5)
  for r in rows:
    info = MODES.get(r["mode"])
    if info:
      mode_box(b, info["key"], r["mode"], info, chips(r["act"]))
  for a in arrows(recs):
    if a["kind"]:
      color, marker, sw = KIND_COLOR[a["kind"]]
      b.append(path(a["d"], stroke=color, sw=sw, marker=marker, dash=a.get("dash", "")))
    label_lines(b, a["labels"])
  # configuration strip
  y0 = 778
  b.append(rect(40, y0, W - 80, 112, fill=CHIP, stroke="none", rx=10))
  b.append(text(56, y0 + 24, "CONFIGURATION · selected before driving, not states (§4 rows)", size=11, fill=MUTED,
                weight=700))
  cw = (W - 80 - 32 - 24) / 3
  cards = []
  for r in rows:
    k = CONFIG.get(r["mode"])
    if k == "chill":
      cards.append(("Chill (MPC longitudinal)", "longitudinal policy selection", "#FFFFFF", BORDER, "", MUTED))
      cards.append(("Experimental (end-to-end model)", "upstream default (params_keys.h:43) · GAP-18 · in ODD? OI-8",
                    AMBER_BG, AMBER, "", AMBER))
    elif k == "debug":
      cards.append(("Debug · maneuver · joystick", "replace control processes (process_config.py:34-47) · " +
                    "excluded, OI-5", "url(#hatch)", FAINT, "5 4", MUTED))
  for i, (t1, t2, fill, stroke, dash, c2) in enumerate(cards):
    x = 56 + i * (cw + 12)
    b.append(rect(x, y0 + 38, cw, 58, fill=fill, stroke=stroke, dash=dash, rx=10, sw=1.4))
    b.append(text(x + 14, y0 + 62, t1, size=13, weight=700, fill=INK if not dash else MUTED))
    b.append(text(x + 14, y0 + 82, t2, size=10.5, fill=c2))
  # legend
  ly = y0 + 140
  b.append(line(40, ly - 22, W - 40, ly - 22, stroke=HAIR, sw=1))
  x = 40
  for kind, label in ((ENV, "enforced by the panda envelope (P); the host (H) also acts"),
                      (HOST, "host only (H, selfdrived, QM)"),
                      (GAP, "host only while the envelope still allows actuation (GAP-16)")):
    color, marker, sw = KIND_COLOR[kind]
    b.append(line(x, ly - 4, x + 34, ly - 4, stroke=color, sw=sw, marker=marker))
    b.append(text(x + 42, ly, label, size=11, fill=MUTED))
    x += 42 + 5.9 * len(label) + 26
  ly2 = ly + 26
  b += pill(40, ly2 - 4, "lateral", SAFETY)
  b.append(text(40 + pill_width("lateral") + 8, ly2, "actuation allowed", size=11, fill=MUTED))
  b += pill(220, ly2 - 4, "no actuation", "#FFFFFF", color=MUTED, stroke=FAINT)
  b.append(text(220 + pill_width("no actuation") + 8, ly2, "none", size=11, fill=MUTED))
  b += pill(370, ly2 - 4, "no longitudinal", "url(#hatch)", color=MUTED, stroke=FAINT, dash="4 3")
  b.append(text(370 + pill_width("no longitudinal") + 8, ly2, "blocked", size=11, fill=MUTED))
  _, _, notimpl = envelope_fault_ids(recs)
  b.append(text(560, ly2, "Record IDs: H = sm-selfdrived; P = sm-toy-auth (T), sm-safety-mode (M).", size=11, fill=MUTED))
  b.append(text(40, ly2 + 24, "Envelope clears the record lists as not implemented, so not drawn as enforcement: " +
                " ".join(notimpl) + ".", size=11, fill=MUTED))
  b.append(text(40, ly2 + 44, "Nothing here is verified; it is the design as WP-C-01 §4 and the records state it. " +
                "The lockout and the 3 s timer exist only on the host; the envelope does not know them.",
                size=11, fill=MUTED))
  height = int(ly2 + 66)
  ids = sorted({f"{PREFIX[m]}:{t}" for a in arrows(recs) for m, t in a["ids"]})
  desc = ("State diagram of the WP-C-01 §4 operating modes: " + "; ".join(
    f"{r['mode']} (actuation: {', '.join(chips(r['act']))})" for r in rows if r["mode"] in MODES) +
    ". Transitions carry the record IDs " + ", ".join(ids) + ". Engagement (D1/D3, T1) and driver disengagement " +
    "(X2, T2/T3) and envelope faults are enforced by the panda envelope; override (E2/O2), immediate disable (X1) and " +
    "the lockout are host only; soft disabling (E1, O1, SD2) is host only while the envelope keeps controls_allowed = 1 " +
    "(GAP-16). Configuration: Chill, Experimental (upstream default, GAP-18), debug modes excluded (OI-5).")
  return svg(W, height, "Figure 4-1 · Operating modes and actuation authority", desc, b)


# ---------------------------------------------------------------- Figure 4-2 data

# The illustrative episode (times in s, made up). Only SOFT_S and LOCKOUT_MIN are code values.
T_SET, T_GAS, T_REL, T_FAULT = 2, 5, 7, 9
T_SD2 = T_FAULT + SOFT_S
T_RE, T_DM, T_BRAKE, T_END = 16, 18, 20, 22.5
T6_WINDOW = 3   # T6: 3 consecutive 1 Hz heartbeat ticks with engaged = 0 (sm-toy-auth T6 guard)
EVENTS = [
  (T_SET, "① cruise set", INK), (T_GAS, "② gas pressed", INK), (T_REL, "③ gas released", INK),
  (T_FAULT, "④ fault: SOFT_DISABLE", RED), (T_SD2, f"⑤ {SOFT_S} s elapsed", RED), (T_RE, "⑥ re-engaged", INK),
  (T_DM, "⑦ DM lockout reached", AMBER), (T_BRAKE, "⑧ driver brakes", INK),
]
# Host states over time (start, end, state) and the record ID of the transition into each.
HOST_SEGMENTS = [
  (0, T_SET, "disabled", ""), (T_SET, T_GAS, "enabled", "D3"), (T_GAS, T_REL, "overriding", "E2"),
  (T_REL, T_FAULT, "enabled", "O2"), (T_FAULT, T_SD2, "softDisabling", "E1"), (T_SD2, T_RE, "disabled", "SD2"),
  (T_RE, T_BRAKE, "enabled", "D3"), (T_BRAKE, T_END, "disabled", "X2"),
]
EPISODE_IDS = [(SD, "D3"), (SD, "E2"), (SD, "O2"), (SD, "E1"), (SD, "SD2"), (SD, "X2"), (SD, "N1"),
               (TA, "T1"), (TA, "T2"), (TA, "T3"), (TA, "T6"), (SM, "M2"), (SM, "M4")]

X0, PX = 240, 40.0


def tx(t: float) -> float:
  return X0 + PX * t


def htext(x, y, s, size=10.5, fill=INK, weight="", anchor="", family="") -> str:
  """Text with a white halo, for labels that sit on the event lines."""
  return el("text", s, x=fmt(x), y=fmt(y), font_size=size, fill=fill, font_weight=weight, text_anchor=anchor,
            font_family=family, stroke="#FFFFFF", stroke_width=4, paint_order="stroke", stroke_linejoin="round")


def wave(t0: float, t1: float, y: float, amp=12.0) -> str:
  pts, n = [], 24
  for k in range(n + 1):
    t = t0 + (t1 - t0) * k / n
    env = math.sin(math.pi * k / n)
    pts.append(f"{fmt(tx(t))},{fmt(y - amp * env * (0.55 + 0.45 * math.sin(2.3 * t)))}")
  return "M" + " L".join(pts)


def figure_4_2(md: str, recs: dict) -> str:
  b: list[str] = []
  b += header(W, "4-2", "One engagement, three layers in time",
              "An illustrative episode: what the host state machine, the panda authority and the actuators do on a " +
              "shared time axis.", "WP-C-01 §4")
  b += pill(W - 40, 62, "ILLUSTRATIVE EPISODE · times made up", AMBER, anchor="end", size=9.5)
  xe = tx(T_END)
  bottom = 690
  # event markers, labels staggered on two lines
  for i, (t, s, c) in enumerate(EVENTS):
    x = tx(t)
    ly = 108 if i % 2 == 0 else 124
    b.append(line(x, ly + 6, x, bottom, stroke=c, sw=1, dash="3 4"))
    b.append(htext(x, ly, s, size=11, fill=c, weight=700, anchor="middle"))
  rows = [
    (160, "selfdrived state", "host · QM · sm-selfdrived"),
    (240, "panda controls_allowed", "envelope · sm-toy-auth"),
    (330, "panda safety mode", "envelope · sm-safety-mode"),
    (390, "lateral command", "0x2E4 on bus 0"),
    (470, "longitudinal command", "0x343 on bus 0"),
    (550, "HMI alert", "ui · soundd"),
    (620, "DM lockout", "dmonitoringd · policy.py"),
  ]
  for y, t1, t2 in rows:
    b.append(text(40, y + 4, t1, size=12.5, weight=700))
    b.append(text(40, y + 19, t2, size=10.5, fill=MUTED))
  # selfdrived bars
  style = {"disabled": ("#FFFFFF", BORDER, INK), "enabled": (SAFETY_BG, SAFETY, INK), "overriding": (HW_BG, HW, INK),
           "softDisabling": (RED_BG, RED, RED)}
  for t0, t1, st, tid in HOST_SEGMENTS:
    f, s, c = style[st]
    b.append(rect(tx(t0), 150, tx(t1) - tx(t0), 28, fill=f, stroke=s, rx=0, sw=1.2))
    lab = f"{st} · {SOFT_S} s" if st == "softDisabling" else st
    b.append(text((tx(t0) + tx(t1)) / 2, 168, lab, size=11, weight=700, fill=c, anchor="middle"))
    if tid:
      b.append(htext(tx(t0) + 4, 193, tid, size=10, fill=MUTED, weight=700, family=MONO))
  # controls_allowed trace
  hi, lo = 228, 256
  b.append(text(X0 - 8, hi + 4, "1", size=10, fill=MUTED, anchor="end"))
  b.append(text(X0 - 8, lo + 4, "0", size=10, fill=MUTED, anchor="end"))
  b.append(rect(tx(T_FAULT), hi - 14, tx(T_SD2) - tx(T_FAULT), lo - hi + 22, fill=RED, stroke="none", rx=0,
                opacity=".09"))
  b.append(rect(tx(T_SD2), hi - 2, PX * T6_WINDOW, lo - hi + 4, fill="url(#hatch-red)", stroke=RED, rx=0, sw=1,
                dash="3 3"))
  b.append(path(f"M{X0},{lo} L{tx(T_SET)},{lo} L{tx(T_SET)},{hi} L{tx(T_SD2)},{hi}", stroke=SAFETY, sw=2.6))
  b.append(path(f"M{tx(T_SD2 + T6_WINDOW)},{lo} L{tx(T_RE)},{lo} L{tx(T_RE)},{hi} L{tx(T_BRAKE)},{hi} " +
                f"L{tx(T_BRAKE)},{lo} L{xe},{lo}", stroke=SAFETY, sw=2.6))
  b.append(htext(tx(T_SET) + 6, hi - 7, "T1: cruise rising edge", fill=SAFETY))
  b.append(htext((tx(T_FAULT) + tx(T_SD2)) / 2, hi - 20, "GAP-16: still 1", fill=RED, weight=700, anchor="middle"))
  b.append(htext(tx(T_SD2) + 4, lo + 19, "→ 0 at T2 (PCM cruise off after", size=10, fill=RED))
  b.append(htext(tx(T_SD2) + 4, lo + 32, "host cancel), at latest T6", size=10, fill=RED))
  b.append(htext(tx(T_RE) + 6, hi - 7, "T1", fill=SAFETY))
  b.append(htext(tx(T_BRAKE) + 6, lo - 7, "T3: brake", fill=SAFETY))
  # safety mode
  b.append(rect(X0, 316, xe - X0, 26, fill=SAFETY_BG, stroke="#FDBA74", rx=0))
  b.append(htext((X0 + xe) / 2, 333, "TOYOTA throughout (set by pandad when onroad: 0xdc; M2, or M4 in the " +
                 "reference build)", size=11, fill=SAFETY, weight=700, anchor="middle"))
  # lateral
  yl = 398
  b.append(line(X0, yl, xe, yl, stroke=HAIR, sw=1))
  b.append(path(f"M{X0},{yl} L{tx(T_SET)},{yl}", stroke=SAFETY, sw=2.2))
  b.append(path(wave(T_SET, T_SD2, yl), stroke=SAFETY, sw=2.2))
  b.append(path(f"M{tx(T_SD2)},{yl} L{tx(T_RE)},{yl}", stroke=SAFETY, sw=2.2))
  b.append(path(wave(T_RE, T_BRAKE, yl), stroke=SAFETY, sw=2.2))
  b.append(path(f"M{tx(T_BRAKE)},{yl} L{xe},{yl}", stroke=SAFETY, sw=2.2))
  b.append(htext(tx(T_SD2) + 6, yl + 17, "0 (host disabled)", size=10, fill=MUTED))
  # longitudinal
  yg = 478
  b.append(line(X0, yg, xe, yg, stroke=HAIR, sw=1))
  b.append(path(f"M{X0},{yg} L{tx(T_SET)},{yg} C{tx(T_SET + 1)},{yg - 14} {tx(T_SET + 2)},{yg - 12} {tx(T_GAS)},{yg - 10}",
                stroke=SAFETY, sw=2.2))
  b.append(rect(tx(T_GAS), yg - 24, tx(T_REL) - tx(T_GAS), 34, fill="url(#hatch)", stroke=FAINT, dash="4 3", rx=0))
  b.append(htext((tx(T_GAS) + tx(T_REL)) / 2, yg - 10, "blocked by", size=10, fill=MUTED, weight=700, anchor="middle"))
  b.append(htext((tx(T_GAS) + tx(T_REL)) / 2, yg + 3, "panda (gas)", size=10, fill=MUTED, weight=700, anchor="middle"))
  b.append(path(f"M{tx(T_REL)},{yg - 10} L{tx(T_FAULT)},{yg - 10} L{tx(T_SD2)},{yg + 16} L{tx(T_SD2)},{yg} " +
                f"L{tx(T_RE)},{yg} C{tx(T_RE + 1)},{yg - 12} {tx(T_RE + 2)},{yg - 10} {tx(T_BRAKE)},{yg - 8} " +
                f"L{tx(T_BRAKE)},{yg} L{xe},{yg}", stroke=SAFETY, sw=2.2))
  b.append(htext(tx(T_FAULT) + 6, yg + 24, "forced decel while", size=10, fill=RED, weight=700))
  b.append(htext(tx(T_FAULT) + 6, yg + 37, "soft disabling", size=10, fill=RED, weight=700))
  # HMI
  yh = 550
  for t0, t1, s, c in ((T_SET, T_SET + 1.8, "engage", SW), (T_GAS, T_REL, "override", HW),
                       (T_FAULT, T_SD2, "TAKE CONTROL", RED), (T_RE, T_RE + 1.3, "engage", SW),
                       (T_DM - 0.5, T_BRAKE, "DM alerts", AMBER)):
    b.append(rect(tx(t0) + 1, yh - 11, tx(t1) - tx(t0) - 2, 22, fill=c, stroke="none", rx=11))
    b.append(text((tx(t0) + tx(t1)) / 2, yh + 4, s, size=10, fill="#FFFFFF", weight=700, anchor="middle"))
  # DM lockout row
  yk = 620
  b.append(rect(X0, yk - 11, tx(T_DM) - X0, 22, fill=CHIP, stroke=LINE, rx=0))
  b.append(htext((X0 + tx(T_DM)) / 2, yk + 4, "no lockout", fill=MUTED, anchor="middle"))
  b.append(rect(tx(T_DM), yk - 11, xe - tx(T_DM), 22, fill="url(#hatch)", stroke=FAINT, dash="4 3", rx=0))
  b.append(htext((tx(T_DM) + xe) / 2, yk + 4, "lockout · N1 refuses ENABLE", fill=INK, weight=700, anchor="middle"))
  # time break and lockout continuation
  bx = xe + 16
  cx = (bx + 10 + W - 40) / 2
  b.append(rect(bx + 10, yk - 11, W - 40 - bx - 10, 22, fill="url(#hatch)", stroke=FAINT, dash="4 3", rx=0))
  b.append(htext(cx, yk + 4, f"{LOCKOUT_MIN[0]}–{LOCKOUT_MIN[1]} min", fill=INK, weight=700, anchor="middle"))
  b.append(text(W - 40, yk + 30, "policy.py:47-49", size=10, fill=MUTED, anchor="end", family=MONO))
  # axis
  ya = bottom + 6
  b.append(line(X0, ya, xe, ya, stroke=FAINT, sw=1))
  for t in range(0, int(T_END) + 1, 2):
    b.append(line(tx(t), ya, tx(t), ya + 6, stroke=FAINT, sw=1))
    b.append(text(tx(t), ya + 20, f"{t} s" if t == 0 else str(t), size=10.5, fill=MUTED, anchor="middle"))
  b.append(text(bx, ya + 5, "⫽", size=15, fill=FAINT, anchor="middle"))
  b.append(text(cx, ya + 20, "+1 … 30 min", size=10.5, fill=MUTED, anchor="middle"))
  b.append(text(xe, ya + 36, "time (s), illustrative", size=10.5, fill=MUTED, anchor="end"))
  # footer
  fy = ya + 62
  b.append(line(40, fy - 18, W - 40, fy - 18, stroke=HAIR, sw=1))
  notes = [
    f"Illustrative: the times between events are made up. Code values: the {SOFT_S} s soft-disable (state.py:7; " +
    f"sm-selfdrived E1 \"{E1_ACTION}\") and the {LOCKOUT_MIN[0]}–{LOCKOUT_MIN[1]} min lockout (policy.py:47-49).",
    f"Red band (GAP-16): for up to {SOFT_S} s the host keeps commanding and the panda keeps allowing it; the envelope " +
    "has no soft-disable of its own.",
    "After SD2 no record transition clears controls_allowed directly: the host requests a PCM cancel (controlsd.py, " +
    "not in a record), the PCM drops cruise",
    "(AOU-05, unverified) and T2 clears; otherwise T6 clears after 3 heartbeat ticks (1 Hz) with engaged = 0. " +
    "The hatched window marks that interval.",
  ]
  for i, s in enumerate(notes):
    b.append(text(40, fy + 18 * i, s, size=11, fill=MUTED))
  height = int(fy + 18 * len(notes) + 14)
  desc = ("Timing diagram of an illustrative engagement episode with rows for the selfdrived state, panda " +
          "controls_allowed, panda safety mode, lateral and longitudinal commands, HMI alerts and the DM lockout. " +
          "Events: cruise set (D3, T1), gas pressed (E2, longitudinal blocked by the panda), released (O2), fault " +
          f"(E1, soft disabling for {SOFT_S} s with controls_allowed still 1, GAP-16), timer runs out (SD2; the panda " +
          "clears at T2 after the host cancel, or at latest T6), re-engagement (D3, T1), DM lockout reached, driver brakes " +
          f"(X2, T3), lockout {LOCKOUT_MIN[0]} to {LOCKOUT_MIN[1]} min during which N1 refuses engagement. Times are " +
          "made up except the 3 s and the lockout duration.")
  return svg(W, height, "Figure 4-2 · One engagement, three layers in time", desc, b)


# ---------------------------------------------------------------- Figure 7-1 data

# AoU -> (group, subject tag, text that must appear in the assumption). Every §7 row must be here exactly once.
AOU_GROUPS = [
  ("veh", "Vehicle ECUs", "existing elements outside the item (§3.2)"),
  ("inst", "Installation and maintenance", "device, harness, vehicle condition"),
  ("drv", "Driver", "supervision and operation"),
  ("net", "Network and back end", "external, untrusted"),
  ("build", "Build configuration", "reference build use"),
]
AOU_MAP = {
  "AOU-01": ("veh", "EPS", "The Toyota EPS limits the torque"),
  "AOU-02": ("veh", "EPS", "A normal driver can override full LKA torque"),
  "AOU-03": ("veh", "brake · PCM", "Driver brake pedal application always produces braking"),
  "AOU-04": ("veh", "PCS", "The stock PCS/AEB keeps full function"),
  "AOU-05": ("veh", "PCM", "The PCM bounds ACC acceleration"),
  "AOU-10": ("veh", "VSC/ABS", "VSC/ABS are enabled and functional"),
  "AOU-12": ("veh", "cluster", "The cluster cruise indicator is driven by PCM state"),
  "AOU-16": ("veh", "PCM", "the PCM keeps it stopped and held"),
  "AOU-08": ("inst", "device mount", "The device is mounted and calibrated"),
  "AOU-09": ("inst", "vehicle", "The vehicle is maintained, unmodified"),
  "AOU-13": ("inst", "harness", "The de-energised harness relay connects the forward camera"),
  "AOU-06": ("drv", "driver", "The driver is licensed, attentive"),
  "AOU-07": ("drv", "safety driver", "only trained safety drivers operate the item"),
  "AOU-11": ("net", "back end", "The comma.ai back end and network are untrusted"),
  "AOU-14": ("build", "reference build", "is used with openpilot's default alternative experience"),
  "AOU-15": ("build", "reference build", "is used only on camera-ACC configurations"),
}
STATUS_STYLE = [  # (prefix of the §7 Status cell, pill text, colour); never green: nothing is verified
  ("Unverified", "Unverified", RED),
  ("Not started", "Not started", RED),
  ("Partially", "Partially", AMBER),
  ("Assumption (SOTIF-managed)", "SOTIF-managed", FAINT),
  ("Design constraint", "Design constraint", FAINT),
]


def status_pill(status: str) -> tuple[str, str]:
  for prefix, label, colour in STATUS_STYLE:
    if status.startswith(prefix):
      return label, colour
  raise SystemExit(f"WP-C-01 §7: unknown status '{status}'; add it to STATUS_STYLE in fig_c01_modes.py")


def short_title(s: str) -> str:
  """First clause: parentheticals dropped, up to the first sentence or semicolon break."""
  s = re.sub(r"\s*\([^()]*\)", "", s)
  return re.split(r"\.\s|;\s|\.$", s, maxsplit=1)[0].strip()


def short_verif(s: str) -> str:
  """Up to the first semicolon outside parentheses."""
  depth = 0
  for i, ch in enumerate(s):
    depth += {"(": 1, ")": -1}.get(ch, 0)
    if ch == ";" and depth == 0:
      return s[:i].strip()
  return s.strip()


def figure_7_1(md: str) -> str:
  rows = aou_table(md)
  by_id = {r["id"]: r for r in rows}
  b: list[str] = []
  b += header(W, "7-1", "Assumptions of use by subject and status",
              f"The {len(rows)} assumptions of §7 grouped by what they assume. No assumption is verified; each needs " +
              "evidence before it is credited.", "WP-C-01 §7")
  cols, x0, lab_w, gap = 3, 40, 176, 12
  cw = (W - 40 - x0 - lab_w - gap * (cols - 1)) / cols
  y = 102
  for gk, gname, gsub in AOU_GROUPS:
    ids = [i for i in AOU_MAP if AOU_MAP[i][0] == gk and i in by_id]
    ids.sort(key=lambda i: int(i.split("-")[1]))
    cards = []
    for i in ids:
      r = by_id[i]
      title = wrap(short_title(r["text"]), cw - 28, size=11.5, factor=0.56)
      credit = wrap("Credited in: " + r["credit"], cw - 28, size=10.5)
      verif = wrap("Verification: " + short_verif(r["verif"]), cw - 28, size=10.5)
      cards.append((i, r, title, credit, verif))
    rows_n = (len(cards) + cols - 1) // cols
    heights = []
    for k in range(rows_n):
      part = cards[k * cols:(k + 1) * cols]
      heights.append(max(48 + 15 * len(t) + 6 + 14 * (len(c) + len(v)) for _i, _r, t, c, v in part))
    gh = sum(heights) + gap * (rows_n - 1) + 24
    b.append(rect(x0, y, W - 40 - x0, gh, fill=CHIP, stroke="none", rx=12))
    names = wrap(gname, lab_w - 24, size=13.5, factor=0.6)
    for j, s in enumerate(names):
      b.append(text(x0 + 14, y + 28 + 17 * j, s, size=13.5, weight=700))
    ty = y + 28 + 17 * (len(names) - 1) + 18
    subs = wrap(gsub, lab_w - 24, size=10.5)
    for j, s in enumerate(subs):
      b.append(text(x0 + 14, ty + 14 * j, s, size=10.5, fill=MUTED))
    b.append(text(x0 + 14, ty + 14 * len(subs) + 6, f"{len(cards)} AoU", size=10.5, fill=MUTED, weight=700))
    cy = y + 12
    for k in range(rows_n):
      for c, (i, r, title, credit, verif) in enumerate(cards[k * cols:(k + 1) * cols]):
        cx = x0 + lab_w + c * (cw + gap)
        label, colour = status_pill(r["status"])
        b.append(rect(cx, cy, cw, heights[k], fill="#FFFFFF", stroke=LINE, rx=10, sw=1.2))
        b.append(rect(cx, cy + 10, 4, heights[k] - 20, fill=colour, stroke="none", rx=2))
        b.append(text(cx + 16, cy + 24, i, size=12.5, weight=700, family=MONO))
        b.append(text(cx + 86, cy + 23, AOU_MAP[i][1], size=10.5, fill=MUTED, weight=600))
        b += pill(cx + cw - 12, cy + 19, label, colour, size=9.5, anchor="end")
        ty = cy + 44
        for s in title:
          b.append(text(cx + 16, ty, s, size=11.5, weight=600))
          ty += 15
        ty += 6
        for s in credit:
          b.append(text(cx + 16, ty, s, size=10.5, fill=MUTED))
          ty += 14
        for s in verif:
          b.append(text(cx + 16, ty, s, size=10.5, fill=SW))
          ty += 14
      cy += heights[k] + gap
    y += gh + 14
  # legend
  ly = y + 22
  b.append(line(40, ly - 20, W - 40, ly - 20, stroke=HAIR, sw=1))
  x = 40
  for label, colour in (("Unverified / Not started", RED), ("Partially", AMBER),
                        ("SOTIF-managed / Design constraint (not a verification status)", FAINT)):
    b.append(rect(x, ly - 10, 26, 12, fill=colour, stroke="none", rx=6))
    b.append(text(x + 32, ly, label, size=11, fill=MUTED))
    x += 32 + 6.0 * len(label) + 26
  b.append(text(x, ly, "Verification line in teal: the approach of §7, not a result.", size=11, fill=MUTED))
  b.append(text(40, ly + 24, "What credits each assumption (hazardous events, goals, TSRs, HWSRs) is shown in WP-T-01 " +
                "Figure 6 (assumption exposure); this figure groups the §7 table and does not repeat those counts.",
                size=11, fill=MUTED))
  height = int(ly + 44)
  desc = (f"Cards for the {len(rows)} assumptions of use of WP-C-01 §7, grouped as " +
          "; ".join(f"{n}: " + ", ".join(i for i in AOU_MAP if AOU_MAP[i][0] == k) for k, n, _s in AOU_GROUPS) +
          ". Each card shows the ID, the first clause of the assumption, a status pill (" +
          "; ".join(f"{r['id']} {status_pill(r['status'])[0]}" for r in rows) +
          "), where it is credited and the verification approach. None is verified.")
  return svg(W, height, "Figure 7-1 · Assumptions of use by subject and status", desc, b)


# ---------------------------------------------------------------- consistency

def in_submodule(rel: str) -> bool:
  """True when `rel` lies in a git submodule (listed in .gitmodules)."""
  gm = REPO / ".gitmodules"
  paths = re.findall(r"^\s*path\s*=\s*(\S+)", gm.read_text(encoding="utf-8"), re.M) if gm.exists() else []
  return any(rel == p or rel.startswith(p.rstrip("/") + "/") for p in paths)


def problems(md: str, recs: dict) -> list[str]:
  out = []
  for key, srcs in PROSE.items():
    out += [f"source text ({key}) no longer in WP-C-01: {s}" for s in srcs if s not in md]
  out += [f"code reference no longer in WP-C-01: {c}" for c in CODE_REFS if f"`{c}" not in md]
  for f, ln, snippet in CODE_SRC:
    p = REPO / f
    if not p.exists():
      if not in_submodule(f):  # submodules are not checked out in the assurance CI job; checked locally
        out.append(f"{f}: file missing")
      continue
    lines = p.read_text(encoding="utf-8").splitlines()
    if ln and (len(lines) < ln or snippet not in lines[ln - 1]):
      out.append(f"{f}:{ln} no longer reads: {snippet}")
    elif not ln and not any(snippet in s for s in lines):
      out.append(f"{f}: text not found: {snippet}")
  e1 = transition(recs, SD, "E1")
  if not e1 or E1_ACTION not in e1.get("action", ""):
    out.append(f"sm-selfdrived E1 action no longer contains '{E1_ACTION}'")
  # §4 rows: every one drawn, as a state box or a configuration card
  for r in modes_table(md):
    if r["mode"] not in MODES and r["mode"] not in CONFIG:
      out.append(f"§4 row '{r['mode']}' is not drawn; map it in MODES or CONFIG")
  rows = {r["mode"] for r in modes_table(md)}
  out += [f"MODES/CONFIG names '{m}', no longer a §4 row" for m in [*MODES, *CONFIG] if m not in rows]
  for m, info in MODES.items():
    for h in info["host"]:
      if h not in recs[SD]["states"]:
        out.append(f"{m}: host state {h} not in sm-selfdrived")
    for mach, st in info["panda"]:
      if st not in recs[mach]["states"]:
        out.append(f"{m}: panda state {st} not in {mach}")
  # record IDs
  for mach, tid in drawn_ids(recs):
    if transition(recs, mach, tid) is None:
      out.append(f"{mach} has no transition {tid}")
  # §7 rows: every AoU placed exactly once, with its guard text
  aous = aou_table(md)
  ids = [r["id"] for r in aous]
  out += [f"§7 {i} not placed in AOU_MAP" for i in ids if i not in AOU_MAP]
  out += [f"AOU_MAP names {i}, not in §7" for i in AOU_MAP if i not in ids]
  out += [f"§7 lists {i} more than once" for i in set(ids) if ids.count(i) > 1]
  for r in aous:
    if r["id"] in AOU_MAP and AOU_MAP[r["id"]][2] not in r["text"]:
      out.append(f"§7 {r['id']} no longer says: {AOU_MAP[r['id']][2]}")
    try:
      status_pill(r["status"])
    except SystemExit as e:
      out.append(str(e))
  return out


def drawn_ids(recs: dict) -> list[tuple[str, str]]:
  ids = [(m, t) for a in arrows(recs) for m, t in a["ids"]] + list(EPISODE_IDS) + list(BOX_IDS)
  for _t0, _t1, _st, tid in HOST_SEGMENTS:
    if tid:
      ids.append((SD, tid))
  return sorted(set(ids))


# ---------------------------------------------------------------- build / check

OUTPUTS = {
  "fig-c01-4-1-operating-modes.svg": figure_4_1,
  "fig-c01-4-2-engagement-timeline.svg": figure_4_2,
  "fig-c01-7-1-aou-map.svg": lambda md, recs: figure_7_1(md),
}


def build(md: str | None = None, recs: dict | None = None) -> dict[str, str]:
  md = md if md is not None else SOURCE.read_text(encoding="utf-8")
  recs = recs if recs is not None else records()
  return {name: fn(md, recs) for name, fn in OUTPUTS.items()}


def main(argv: list[str]) -> int:
  md = SOURCE.read_text(encoding="utf-8")
  recs = records()
  issues = problems(md, recs)
  if issues:
    for s in issues:
      print(s, file=sys.stderr)
    print("review the figure data in fig_c01_modes.py against WP-C-01, the records and the code, and regenerate",
          file=sys.stderr)
    return 1
  outputs = build(md, recs)
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"stale: {n}", file=sys.stderr)
    if stale:
      print("run: python3 assurance/02-concept/figures/fig_c01_modes.py", file=sys.stderr)
      return 1
    print(f"fig_c01_modes: {len(outputs)} figure(s) current, {len(drawn_ids(recs))} record transitions drawn")
    return 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
  print(f"fig_c01_modes: wrote {len(outputs)} figure(s)")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
