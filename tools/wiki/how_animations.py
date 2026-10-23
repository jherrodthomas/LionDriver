#!/usr/bin/env python3
"""Render the animated explainers of the wiki page "How LionDriver works" as SVG.

  how-hookup.svg       how the device connects to the car: the stock camera link, the harness that splits it, what
                       the panda forwards and what it blocks, and the relay that restores the stock link;
  how-one-command.svg  the life of one steering command from camera frame to steering motor, and what the panda does
                       when the chain stalls, against the FTTI;
  how-envelope.svg     the checks the panda runs on each steering frame, with five commands meeting them.

The envelope limits are read from the calibration record (WP-W-09 CD-02), the stall times and the forwarding rule from
the technical safety requirements (WP-S-02), the FTTI from the timing analysis (WP-S-04 §3.7), the implementation
status of each requirement from the TSR list, and the model rate from WP-C-11. Every other phrase is tied to its
record (SOURCES) and checked at render time (`problems()`). When a record changes, the wiki build fails instead of
showing old text. When opendbc is checked out, the limits are also compared with `toyota.h`. build_wiki.py renders
them next to the pages at each sync; they loop with CSS and reduced motion shows the final frame.

Usage: python3 tools/wiki/how_animations.py [--out DIR] [--check]
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

NAMES = ("how-hookup.svg", "how-one-command.svg", "how-envelope.svg")
BLUE, ORANGE = "#2a78d6", "#c2410c"
QM_BG, C_BG = "#eef2f8", "#e7f5ee"

A = Path("assurance")
S02 = A / "03-system" / "WP-S-02-technical-safety-requirements.md"
S03 = A / "03-system" / "WP-S-03-technical-safety-concept-architecture.md"
S04 = A / "03-system" / "WP-S-04-timing-ftti-budget.md"
TSR_LIST = A / "03-system" / "requirements" / "tsr-list.md"
W09 = A / "05-software" / "WP-W-09-configuration-calibration-data.md"
C11 = A / "02-concept" / "WP-C-11-ai-system-definition-and-safety-requirements.md"
HARNESS = A / "04-hardware" / "wiring" / "e05-toyota-a-harness.yaml"
REF = Path("wiki") / "Reference-vehicle.md"
TOYOTA_H = Path("opendbc_repo") / "opendbc" / "safety" / "modes" / "toyota.h"
SAFETY_H = Path("opendbc_repo") / "opendbc" / "safety" / "safety.h"

# the requirements the figures name; their status is read from the TSR list
TSRS = ("TSR-101", "TSR-102", "TSR-103", "TSR-108", "TSR-301", "TSR-302", "TSR-407", "TSR-408", "TSR-512", "TSR-704",
        "TSR-706")
# the checks drawn in the panda box: (text, requirement)
CHECKS = [("mode locked to Toyota", "TSR-512"), ("driver engaged it", "TSR-301"), ("|torque| ≤ {cap}", "TSR-101"),
          ("rise ≤ {up}, fall ≤ {down} /frame", "TSR-103"), ("≤ {err} above motor torque", "TSR-103"),
          ("frame arrived on time", "TSR-408")]

# (record, phrase a figure stands on)
SOURCES = [
  (REF, "Toyota Corolla sedan, US market, 12th generation (E210)"), (REF, "| Driver assistance | Toyota Safety Sense 2.0 |"),
  (REF, "comma 3X or comma four with the integrated panda, Toyota A connector"),
  (HARNESS, "CAN2_H camera"), (HARNESS, "CAN0_H car"), (HARNESS, "CAN1_H radar"),
  (S03, "| E-05 Harness | Toyota TSS2 harness with intercept relay"), (S03, "(relay released: direct link)"),
  (S03, "| E-01 SoC software | openpilot processes on AGNOS Linux (Qualcomm SoC); §8 | QM"),
  (S03, "| E-03a Safety layer | opendbc safety core + Toyota mode, compiled into the panda firmware | C"),
  (S03, "plannerd ─▶ controlsd ─▶ card ─sendcan─"), (S03, "| IF-01 | Car-side CAN TX | E-03 → EPS, PCM |"),
  (S02, "| TSR-706 | On SS-S, any MCU fault, MCU reset, loss of device power or harness supply, the relay shall return to the stock"),
  (S02, "| TSR-302 | The envelope shall revoke all actuation authority when a driver brake press is received"),
  (C11, "process `modeld`, 20 Hz"),
  (S04, "Status | Draft — kinematic estimates and code-derived times"),
]


def _read(root: Path, path: Path) -> str:
  return (root / path).read_text(encoding="utf-8")


def _row(text: str, key: str, path: Path) -> str:
  m = re.search(rf"^\| {re.escape(key)} \|.*$", text, re.M)
  if not m:
    raise ValueError(f"{path}: row {key!r} not found")
  return m.group(0)


def _num(pattern: str, text: str, what: str) -> float:
  m = re.search(pattern, text)
  if not m:
    raise ValueError(f"{what} not found ({pattern!r})")
  return float(m.group(1))


def data(root: Path = ROOT) -> dict:
  w09, s02, s04, tsr = _read(root, W09), _read(root, S02), _read(root, S04), _read(root, TSR_LIST)
  cap = int(_num(r"\| `max_torque` \| (\d+) raw \|", w09, f"{W09} CD-02 max_torque"))
  m = re.search(r"\| `max_rate_up` / `max_rate_down` \| (\d+) / (\d+) raw per frame \|", w09)
  if not m:
    raise ValueError(f"{W09} CD-02: max_rate_up / max_rate_down not found")
  up, down = int(m.group(1)), int(m.group(2))
  err = int(_num(r"\| `max_torque_error` \| (\d+) raw \|", w09, f"{W09} CD-02 max_torque_error"))
  r408 = _row(s02, "TSR-408", S02)
  gap_ms = _num(r"no frame arrives for > (\d+) ms", r408, "TSR-408 gap")
  frames = _num(r"> \d+ ms \((\d+) frames\)", r408, "TSR-408 frames")
  hb_s = _num(r"heartbeat \(`0xf3`\) for > ([0-9.]+) s", _row(s02, "TSR-407", S02), "TSR-407 heartbeat timeout")
  ftti = _num(r"^([0-9.]+) s \|", _row(s04, "SG-01 SoC command stall", S04).split(" | ", 1)[1], f"{S04} §3.7 SG-01 FTTI")
  r704 = _row(s02, "TSR-704", S02)
  blocked = re.findall(r"`(0x[0-9A-F]+)`", r704.split(", and shall forward", 1)[0])
  status = {}
  for k in TSRS:
    m = re.search(rf"^\| \[{k}\]\([^)]*\) \|[^|]*\|[^|]*\|[^|]*\| ([^|]+?) \|", tsr, re.M)
    if not m:
      raise ValueError(f"{TSR_LIST}: {k} not found")
    status[k] = m.group(1)
  return {"cap": cap, "up": up, "down": down, "err": err, "gap_ms": gap_ms, "rate_hz": round(frames / gap_ms * 1000),
          "hb_s": hb_s, "ftti": ftti, "blocked": blocked, "status": status}


def code_problems(root: Path, d: dict) -> list[str]:
  """When opendbc is checked out, the limits the figures draw must be those of the code."""
  if not (root / TOYOTA_H).exists():
    return []
  code, errs = _read(root, TOYOTA_H), []
  lim = code.split("TOYOTA_TORQUE_STEERING_LIMITS", 1)[-1].split("};", 1)[0]
  for field, key in (("max_torque", "cap"), ("max_rate_up", "up"), ("max_rate_down", "down"), ("max_torque_error", "err")):
    m = re.search(rf"\.{field} = (\d+)", lim)
    if not m or int(m.group(1)) != d[key]:
      errs.append(f"{TOYOTA_H}: .{field} is {m.group(1) if m else 'missing'}, {W09} CD-02 says {d[key]}; how-envelope.svg draws the record")
  m = re.search(r"\{\.addr = 0x2E4U, \.bus = 0U, \.frequency = (\d+)U", code)
  if not m or int(m.group(1)) != d["rate_hz"]:
    errs.append(f"{TOYOTA_H}: 0x2E4 rate is {m.group(1) if m else 'missing'} Hz, TSR-408 implies {d['rate_hz']} Hz")
  m = re.search(r"\{\.addr = 0x2E4U, \.bus = 0U, \.timeout_us = (\d+)U", code)
  if not m or int(m.group(1)) != d["gap_ms"] * 1000:
    errs.append(f"{TOYOTA_H}: 0x2E4 arrival timeout is {m.group(1) if m else 'missing'} us, TSR-408 says {d['gap_ms']:g} ms")
  relay = set(re.findall(r"\{(0x[0-9A-F]+), 0, \d+, \.check_relay = true\}", code))
  if set(d["blocked"]) - relay:  # other Toyota variants (SecOC) block more; the reference car's are those of TSR-704
    errs.append(f"{TOYOTA_H}: {sorted(set(d['blocked']) - relay)} no longer blocked from the camera side, TSR-704 says {d['blocked']}")
  if (root / SAFETY_H).exists() and "exit controls on rising edge of brake press" not in _read(root, SAFETY_H):
    errs.append(f"{SAFETY_H}: the brake-press exit is gone; how-envelope.svg shows it")
  return errs


def problems(root: Path = ROOT) -> list[str]:
  errs, cache = [], {}
  for path, phrase in SOURCES:
    if path not in cache:
      p = root / path
      cache[path] = norm(p.read_text(encoding="utf-8")) if p.exists() else ""
    if norm(phrase) not in cache[path]:
      errs.append(f"{path}: the how-it-works page stands on {phrase!r}, which is gone; update the figure")
  try:
    d = data(root)
    if d["blocked"] != ["0x2E4", "0x191", "0x412", "0x343"]:
      errs.append(f"{S02}: TSR-704 now blocks {d['blocked']}; how-hookup.svg names 0x2E4, 0x191, 0x412 and 0x343")
    if d["gap_ms"] / 1000 >= d["hb_s"] or d["hb_s"] >= d["ftti"]:
      errs.append(f"{S02}/{S04}: the stall times no longer sit in order 0x2E4 gap < heartbeat < FTTI; how-one-command.svg draws them so")
    if d["ftti"] > 0.5:
      errs.append(f"{S04}: the FTTI is {d['ftti']:g} s; how-one-command.svg draws an axis to 0.5 s")
    errs += code_problems(root, d)
  except (OSError, ValueError) as e:
    errs.append(f"cannot read the records the how-it-works page is drawn from: {e}")
  return errs


# ---------------------------------------------------------------- SVG pieces

def box(x, y, w, h, fill="#fff", stroke=NAVY, rx=8, sw=1.6, dash=""):
  d = f' stroke-dasharray="{dash}"' if dash else ""
  return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def line(x1, y1, x2, y2, c=NAVY, w=2):
  return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="{w}"/>'


def arrow(x1, y, x2, c=NAVY, w=2):
  return line(x1, y, x2, y, c, w) + f'<polygon points="{x2},{y} {x2 - 8},{y - 5} {x2 - 8},{y + 5}" fill="{c}"/>'


def dot(loop, path, t0, dur, c, r=6):
  """A dot that travels a path once per loop between t0 and t0 + dur, hidden otherwise and under reduced motion."""
  k = lambda s: f"{s / loop:.4f}"  # noqa: E731
  return (f'<circle class="tr" r="{r}" fill="{c}" opacity="0"><animateMotion path="{path}" dur="{loop:g}s" repeatCount="indefinite" '
          f'keyPoints="0;0;1;1" keyTimes="0;{k(t0)};{k(t0 + dur)};1" calcMode="linear"/>'
          f'<animate attributeName="opacity" dur="{loop:g}s" repeatCount="indefinite" values="0;0;1;1;0;0" '
          f'keyTimes="0;{k(max(t0 - .01, 0))};{k(t0)};{k(t0 + dur)};{k(t0 + dur + .05)};1"/></circle>')


def caption(tl, t_in, t_out, s, y):
  return g(tl.show(t_in, t_out) + " tr", [t(360, y, s, 15, NAVY, 600, "middle")])


def open_note(d: dict, ids: list[str]) -> list[str]:
  return [k for k in ids if d["status"][k] == "not implemented"]


# ---------------------------------------------------------------- 1. the hookup

def hookup(d: dict) -> str:
  L = 26.0
  tl = Timeline(L)
  b = [t(24, 36, "How it connects to the car", 23, NAVY, 700),
       t(24, 58, "Reference car: Toyota Corolla E210, TSS 2.0 · comma device with the Toyota A harness", 14, MID)]
  b += [box(24, 150, 150, 92), t(99, 178, "Toyota forward", 14, NAVY, 700, "middle"),
        t(99, 196, "camera (stock)", 14, NAVY, 700, "middle"), t(99, 218, "lane keeping, PCS", 12.5, MID, 400, "middle"),
        t(99, 232, "radar link: bus 1", 12.5, MID, 400, "middle")]
  b += [box(530, 130, 172, 132), t(616, 156, "The car's CAN", 14, NAVY, 700, "middle")]
  for i, (n, s) in enumerate([("EPS", "steering motor"), ("PCM", "engine, cruise"), ("ABS", "brakes, speed"), ("cluster", "alerts")]):
    b += [t(544, 180 + 20 * i, n, 13, NAVY, 700), t(600, 180 + 20 * i, s, 12.5, MID)]
  # 1: stock, one cable
  b += [g(tl.show(0.3, 6.2) + " tr", [line(174, 196, 530, 196, NAVY, 3), t(352, 186, "one connector behind the mirror", 12.5, MID, 400, "middle"),
                                      dot(L, "M174,196 L530,196", 1.2, 1.4, BLUE), dot(L, "M530,196 L174,196", 3.0, 1.4, MID),
                                      dot(L, "M174,196 L530,196", 4.4, 1.4, BLUE)])]
  b.append(caption(tl, 0.3, 6.2, "Stock: the camera steers the car itself, over one cable.", 300))
  # 2: the device and the harness
  dev = [box(238, 86, 244, 90, QM_BG), t(250, 104, "comma device", 13, NAVY, 700),
         box(250, 112, 102, 54, "#fff", MID), t(301, 134, "SoC (QM)", 12.5, NAVY, 700, "middle"),
         t(301, 150, "runs openpilot", 11.5, MID, 400, "middle"),
         box(366, 112, 104, 54, C_BG, GRN, sw=2), t(418, 134, "panda MCU", 12.5, NAVY, 700, "middle"),
         t(418, 150, "ASIL C envelope", 11.5, GRN, 700, "middle"), arrow(352, 139, 366, MID, 1.5)]
  har = [box(268, 210, 184, 56), t(360, 230, "harness box + relay (E-05)", 12.5, NAVY, 700, "middle"),
         t(360, 248, "plugs in at the camera connector", 11.5, MID, 400, "middle"),
         line(174, 238, 268, 238, ORANGE, 3), t(221, 258, "bus 2", 12, ORANGE, 700, "middle"), t(221, 272, "camera side", 11, ORANGE, 400, "middle"),
         line(452, 238, 530, 238, BLUE, 3), t(491, 258, "bus 0", 12, BLUE, 700, "middle"), t(491, 272, "car side", 11, BLUE, 400, "middle"),
         line(418, 166, 418, 210, NAVY, 2), t(426, 196, "CAN", 11, MID)]
  b += [g(tl.show(6.6) + " fin", dev + har)]
  b.append(caption(tl, 6.6, 11.6, "The harness splits that cable: camera on one side, car on the other.", 300))
  # 3: forwarding
  b += [g(tl.show(12.0, 19.2) + " tr", [dot(L, "M174,238 L268,238 L418,238 L418,200", 12.4, 1.6, RED),
                                        dot(L, "M174,238 L268,238 L452,238 L530,238", 14.4, 2.0, GRN),
                                        dot(L, "M530,238 L452,238 L268,238 L174,238", 16.6, 2.0, GRN)])]
  b.append(caption(tl, 12.0, 19.2, "The panda forwards what the camera says, except its steering commands.", 300))
  rows = [(" · ".join(d["blocked"]), RED, "blocked: the device steers instead"),
          ("PCS braking and everything else", GRN, "forwarded both ways, unchanged")]
  for i, (m, c, s) in enumerate(rows):
    y = 330 + 30 * i
    b += [g(tl.show(12.6 + i * 1.6) + " fin", [f'<circle cx="40" cy="{y - 5}" r="6" fill="{c}"/>', t(54, y, m, 13.5, NAVY, 700),
                                               t(330, y, s, 13.5, c, 600)])]
  # 4: the device steers
  b += [g(tl.show(19.6, 25.6) + " tr", [dot(L, "M301,166 L301,190 L418,190 L418,238 L530,238", 20.0, 1.8, BLUE),
                                        dot(L, "M301,166 L301,190 L418,190 L418,238 L530,238", 22.4, 1.8, BLUE)])]
  b.append(caption(tl, 19.6, 25.6, "openpilot's steering goes out through the panda, which checks every frame.", 300))
  b += [g(tl.show(19.6) + " fin", [t(24, 412, "If the device faults or is unplugged, the relay drops and the camera's direct", 13.5, NAVY),
                                   t(24, 430, f"link to the car returns (TSR-706, {d['status']['TSR-706']}).", 13.5, NAVY),
                                   t(24, 454, "Sources: harness drawing E-05, WP-S-03 §3–4, TSR-704, TSR-706", 11.5, MID)])]
  return svg(470, "How LionDriver connects to the car",
             "The stock camera talks to the car over one cable; the harness splits that cable, the panda blocks the camera's "
             "steering frames, forwards PCS braking and everything else, and sends openpilot's checked steering.", tl, b)


# ---------------------------------------------------------------- 2. the life of one command

STAGES = [("camera", "20 Hz", QM_BG), ("model", "modeld", QM_BG), ("planner", "plannerd", QM_BG), ("controls", "controlsd", QM_BG),
          ("card", "car interface", QM_BG), ("panda", "checks it", C_BG), ("EPS", "motor", "#fff")]


def one_command(d: dict) -> str:
  L = 22.0
  tl = Timeline(L)
  b = [t(24, 36, "The life of one steering command", 23, NAVY, 700),
       t(24, 58, "From a camera frame to the steering motor, and what happens if the chain stalls", 14, MID)]
  b += [box(16, 78, 486, 120, "none", MID, 10, 1.2, "5 4"), t(26, 94, "SoC · QM (not safety-rated)", 11.5, MID, 700),
        box(508, 78, 96, 120, "none", GRN, 10, 1.6, "5 4"), t(516, 94, "ASIL C", 11.5, GRN, 700)]
  xs = [24 + i * 96 for i in range(len(STAGES))]
  for i, ((n, s, f), x) in enumerate(zip(STAGES, xs, strict=True)):
    safe = f == C_BG
    b += [g(tl.show(0.3 + i * 0.5) + " fin", [box(x, 108, 82, 70, f, GRN if safe else NAVY, 8, 2 if safe else 1.4),
                                              t(x + 41, 138, n, 13.5, NAVY, 700, "middle"), t(x + 41, 156, s, 11, MID, 400, "middle")]
          + ([arrow(x + 82, 143, x + 96, NAVY, 1.6)] if i < len(STAGES) - 1 else []))]
  b += [g(tl.show(2.6) + " fin", [t(551, 216, "CAN 0x2E4", 11.5, BLUE, 700, "middle"), t(551, 230, f"{d['rate_hz']} Hz", 11, MID, 400, "middle")])]
  b += [dot(L, f"M{xs[0] + 41},143 L{xs[-1] + 41},143", 3.4, 3.2, BLUE, 7)]
  b.append(caption(tl, 3.2, 7.4, f"Every {1000 / d['rate_hz']:g} ms a new torque command; the panda checks it before the car sees it.", 250))
  y0, x0, x1 = 336, 70, 650
  X = lambda s: x0 + s * (x1 - x0) / 0.5  # noqa: E731
  ax = [line(x0, y0, x1, y0, NAVY, 2)]
  for s in (0, 0.1, 0.2, 0.3, 0.4, 0.5):
    ax += [line(X(s), y0 - 5, X(s), y0 + 5, NAVY, 1.5), t(X(s), y0 + 22, f"{s:g} s", 12, MID, 400, "middle")]
  b += [g(tl.show(7.8) + " fin", ax + [t(24, 270, "If the chain stalls: time since the last good message", 14.5, NAVY, 700)])]
  b += [g(tl.show(7.8, 9.6) + " tr", [t(360, y0 + 44, "The SoC freezes. The panda keeps counting.", 14, NAVY, 600, "middle")])]
  b += [f'<line class="tr" x1="{x0}" y1="{y0 - 34}" x2="{x0}" y2="{y0 + 6}" stroke="{RED}" stroke-width="2.5" opacity="0">'
        f'<animate attributeName="opacity" dur="{L:g}s" repeatCount="indefinite" values="0;0;1;1;0;0" '
        f'keyTimes="0;{8.2 / L:.4f};{8.3 / L:.4f};{15 / L:.4f};{15.1 / L:.4f};1"/>'
        f'<animateTransform attributeName="transform" type="translate" dur="{L:g}s" repeatCount="indefinite" '
        f'values="0 0;0 0;{x1 - x0} 0;{x1 - x0} 0" keyTimes="0;{8.3 / L:.4f};{14.8 / L:.4f};1"/></line>']
  marks = [(d["gap_ms"] / 1000, f"{d['gap_ms']:g} ms", f"> {d['gap_ms']:g} ms without 0x2E4: steering authority revoked (TSR-408)", BLUE),
           (d["hb_s"], f"{d['hb_s']:g} s", f"> {d['hb_s']:g} s without heartbeat 0xf3: all authority revoked (TSR-407)", ORANGE),
           (d["ftti"], f"FTTI {d['ftti']:g} s", f"FTTI {d['ftti']:g} s (SG-01): earliest possible hazardous drift", RED)]
  for i, (s, tag, text, col) in enumerate(marks):
    ti = 8.3 + s / 0.5 * 6.5
    b += [g(tl.show(ti) + " fin", [line(X(s), y0 - 30, X(s), y0, col, 3), t(X(s), y0 - 36, tag, 12.5, col, 700, "middle" if s < 0.45 else "end")])]
    b += [g(tl.show(ti) + " fin", [f'<circle cx="34" cy="{396 + 20 * i}" r="5" fill="{col}"/>', t(46, 400 + 20 * i, text, 13, NAVY)])]
  b += [g(tl.show(15.4) + " fin", [t(24, 464, "Times from WP-S-02 and WP-S-04 §3.7, code-derived; not yet measured on the car.", 11.5, MID)])]
  return svg(480, "The life of one steering command",
             "A camera frame flows through the driving model, planner, controls and car interface to the panda, which checks "
             f"it and sends CAN 0x2E4 to the EPS; if the chain stalls the panda revokes authority well inside the {d['ftti']:g} s FTTI.",
             tl, b)


# ---------------------------------------------------------------- 3. the envelope

def commands(d: dict) -> list[tuple[str, bool, str]]:
  return [(f"+300, rising {d['up'] - 5} per frame", True, "within every limit"),
          (f"+{d['cap'] + 200}", False, f"over the {d['cap']} cap (TSR-101)"),
          (f"rising {d['up'] * 2 + 10} per frame", False, f"faster than {d['up']} per frame (TSR-103)"),
          ("+200 while not engaged", False, "no authority: not engaged (TSR-301)"),
          ("+600 while the driver brakes", False, "brake press ends authority (TSR-302)")]


def envelope(d: dict) -> str:
  L = 24.0
  tl = Timeline(L)
  b = [t(24, 36, "The panda: the gate every command passes", 23, NAVY, 700),
       t(24, 58, "The checks the safety MCU runs on each STEERING_LKA (0x2E4) frame", 14, MID)]
  b += [box(262, 84, 196, 196, C_BG, GRN, 12, 2.2), t(360, 108, "panda envelope", 14, NAVY, 700, "middle"),
        t(360, 124, "ASIL C · per frame", 11.5, GRN, 700, "middle")]
  for i, (c, _) in enumerate(CHECKS):
    b += [t(276, 150 + 21 * i, "✓ " + c.format(**d), 12, NAVY)]
  b += [box(24, 140, 150, 80, QM_BG, MID), t(99, 170, "openpilot (SoC)", 13, NAVY, 700, "middle"),
        t(99, 188, "asks for torque", 12, MID, 400, "middle"),
        box(546, 140, 150, 80), t(621, 170, "EPS", 13, NAVY, 700, "middle"), t(621, 188, "steering motor", 12, MID, 400, "middle"),
        arrow(174, 180, 256, MID, 1.5), arrow(458, 180, 540, MID, 1.5)]
  step = 3.6
  for i, (cmd, ok, why) in enumerate(commands(d)):
    t0 = 0.6 + i * step
    col = GRN if ok else RED
    path = "M174,180 L228,180 L228,298 L492,298 L492,180 L540,180" if ok else "M174,180 L248,180"
    b += [dot(L, path, t0, 1.6 if ok else 0.8, col, 8)]
    b += [g(tl.show(t0, t0 + step - 0.2) + " tr", [t(99, 262, cmd, 12.5, NAVY, 700, "middle"),
                                                   t(360, 326, ("PASSED: " if ok else "BLOCKED: ") + why, 15, col, 700, "middle")])]
    y = 356 + 20 * i
    b += [g(tl.show(t0 + 1.2) + " fin", [t(40, y, "✓" if ok else "✗", 14, col, 700), t(60, y, cmd, 13, NAVY, 600), t(300, y, why, 13, col)])]
  todo = open_note(d, ["TSR-108", "TSR-102"])
  what = {"TSR-108": "revoking authority after a blocked frame (TSR-108)", "TSR-102": "a speed-dependent torque limit (TSR-102)"}
  notes = [f"Not implemented yet: {what[k]}." for k in todo] or ["TSR-108 and TSR-102 are implemented."]
  b += [g(tl.show(19.0) + " fin", [t(24, 474, "A blocked frame never reaches the car.", 12.5, NAVY, 700)]
          + [t(24, 492 + 18 * i, n, 12.5, NAVY) for i, n in enumerate(notes)])]
  return svg(520, "The panda: the gate every command passes",
             "Five steering commands meet the panda's per-frame checks; one passes, four are blocked: over the torque cap, "
             "too fast a rise, not engaged, driver braking.", tl, b)


def render(root: Path = ROOT) -> dict[str, str]:
  d = data(root)
  return dict(zip(NAMES, (hookup(d), one_command(d), envelope(d)), strict=True))


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
