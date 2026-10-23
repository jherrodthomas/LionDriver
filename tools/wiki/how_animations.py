#!/usr/bin/env python3
"""Render the animated explainers of the wiki page "How LionDriver works" as SVG.

  how-hookup.svg       how the device connects to the car: the stock camera link, the harness that splits it, what
                       the panda forwards and what it blocks, and the relay that restores the stock link;
  how-one-command.svg  the life of one steering command from camera frame to steering motor, and what the panda does
                       when the chain stalls, against the FTTI;
  how-envelope.svg     the checks the panda runs on each steering frame, with five commands meeting them;
  how-in-charge.svg    how control changes hands between driver and system, and the driver-monitoring escalation;
  how-failures.svg     five faults, each with its detection and reaction budget against the FTTI;
  how-stock.svg        what stays stock: PCS forwarded, never imitated, the stock path restored; the assumptions of use;
  how-odd.svg          inside and outside the operating domain, and how many ways out of it the system detects.

The envelope limits are read from the calibration record (WP-W-09 CD-02), the stall times and the forwarding rule from
the technical safety requirements (WP-S-02), the FTTI and the fault budgets from the timing analysis (WP-S-04 §3.7), the
implementation status of each requirement from the TSR list, the model rate from WP-C-11, the driver-monitoring times
from TSR-608 and TSR-633, the assumptions of use from WP-C-01 §7 and the operating domain and its exits from WP-C-02. Every other phrase is tied to its
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

NAMES = ("how-hookup.svg", "how-one-command.svg", "how-envelope.svg", "how-in-charge.svg", "how-failures.svg", "how-stock.svg",
         "how-odd.svg")
BLUE, ORANGE, AMBER = "#2a78d6", "#c2410c", "#b7791f"
QM_BG, C_BG = "#eef2f8", "#e7f5ee"

A = Path("assurance")
S02 = A / "03-system" / "WP-S-02-technical-safety-requirements.md"
S03 = A / "03-system" / "WP-S-03-technical-safety-concept-architecture.md"
S04 = A / "03-system" / "WP-S-04-timing-ftti-budget.md"
TSR_LIST = A / "03-system" / "requirements" / "tsr-list.md"
W09 = A / "05-software" / "WP-W-09-configuration-calibration-data.md"
C11 = A / "02-concept" / "WP-C-11-ai-system-definition-and-safety-requirements.md"
C01 = A / "02-concept" / "WP-C-01-item-definition.md"
C02 = A / "02-concept" / "WP-C-02-odd-and-intended-functionality.md"
HARNESS = A / "04-hardware" / "wiring" / "e05-toyota-a-harness.yaml"
REF = Path("wiki") / "Reference-vehicle.md"
TOYOTA_H = Path("opendbc_repo") / "opendbc" / "safety" / "modes" / "toyota.h"
SAFETY_H = Path("opendbc_repo") / "opendbc" / "safety" / "safety.h"

# the requirements the figures name; their status is read from the TSR list
TSRS = ("TSR-101", "TSR-102", "TSR-103", "TSR-108", "TSR-301", "TSR-302", "TSR-304", "TSR-305", "TSR-407", "TSR-408",
        "TSR-512", "TSR-516", "TSR-633", "TSR-704", "TSR-705", "TSR-706")
# driver actions drawn in how-in-charge.svg: (action, result, requirement, colour)
ACTS = [("Driver sets the car's cruise", "panda grants authority; the cruise light shows it", "TSR-301", GRN),
        ("Driver presses the brake", "all authority ends at once", "TSR-302", RED),
        ("Driver cancels cruise", "authority ends in the same frame", "TSR-301", RED),
        ("Driver steers against it", "refuse torque that fights the driver", "TSR-304", AMBER),
        ("Driver presses the accelerator", "speed control pauses; steering stays on", "TSR-305", BLUE)]
# fault classes of WP-S-04 §3.7 drawn in how-failures.svg, in plain words
FAULTS = [("SG-01 RX loss/corruption", "a car message stops arriving"), ("SG-01 SoC heartbeat loss", "the main computer stops reporting"),
          ("SG-01 SoC command stall", "the main computer stops steering"), ("SG-01 MCU execution fault", "the panda itself hangs (watchdog)"),
          ("SG-01 relay stuck", "the harness relay sticks")]
# assumptions of use drawn in how-stock.svg, in plain words
AOUS = [("AOU-01", "the EPS limits LKA torque to what a driver can overpower"), ("AOU-03", "the brake pedal always brakes"),
        ("AOU-04", "stock PCS keeps full function with the harness fitted"), ("AOU-13", "the dropped relay is a plain wire to the car")]
# the operating domain in plain words (WP-C-02 §3.1); each line stands on a SOURCES phrase
INSIDE = ["Limited-access divided highways", "0–110 km/h, never above the limit", "Engage above a speed floor (proposed 60 km/h)",
          "Curves ≥ v²/2.5 m/s² ({r100} m radius at 100 km/h)", "Dry or wet; rain below 2.5 mm/h", "Visibility 200 m or more",
          "Day, dusk or night with headlights", "Lane markings on at least one side"]
OUTSIDE = ["City streets, intersections, roundabouts", "Above 110 km/h", "Heavy rain, snow, ice, fog", "Work zones, toll plazas",
           "Ramps and tight curves", "Low sun in the camera, tunnels", "Faded or missing markings", "Driver not visible to the camera"]
# ODD exits (WP-C-02 §5.2, first cell starts with) that how-odd.svg names as not detected
UNDETECTED = ("Speed > 110 km/h", "Missing/faded markings", "Heavy rain, fog")
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
  (S04, "Status | Draft — kinematic estimates and code-derived times"), (S04, "cross-checked in simulation"),
  (S04, "(EPS torque 0, PCM inactive)"), (S04, "≤ 6 s from loss of attention to the first alert"),
  (S02, "revoke it in the same frame in which CRUISE_ACTIVE is received false"),
  (S02, "cluster cruise indicator is an indication of engagement"),
  (S02, "reject `0x2E4` frames that increase torque opposing the driver"),
  (S02, "withdraw longitudinal authority"), (S02, "The accelerator shall not revoke lateral authority"),
  (S02, "sound its own acoustic warning within ≤ 0.5 s"), (S02, "decelerate in lane to a standstill"),
  (S02, "shall not accept from the SoC any frame on the car-side bus that the stock PCS function uses"),
  (C01, "The Toyota EPS limits the torque applied for LKA requests to a level a normal driver can overpower"),
  (C01, "Driver brake pedal application always produces braking"),
  (C01, "The stock PCS/AEB keeps full function with the harness installed"),
  (C01, "The de-energised harness relay connects the forward camera to the vehicle CAN (stock path) without any active component"),
  (C02, "limited-access highways only (ODD-H)"), (C02, "Limited-access divided highway"),
  (C02, "0 – 110 km/h (68 mph), not above the posted limit"), (C02, "proposed 60 km/h (37 mph)"),
  (C02, "None or light rain: below 2.5 mm/h"), (C02, "| Weather | Visibility | ≥ 200 m |"),
  (C02, "Day; dusk/dawn; night with headlights"), (C02, "Visible longitudinal markings on at least one side"),
  (C02, "roundabouts"), (C02, "All at-grade intersections"), (C02, "Moderate/heavy rain (2.5 mm/h and above), snow"),
  (C02, "Snow, ice, standing water"), (C02, "Fog, smoke, dust"), (C02, "Construction / work zones, restricted lanes, toll booths"),
  (C02, "Tighter curves; ramps"), (C02, "Low sun directly in the camera field of view"), (C02, "tunnels (not validated)"),
  (C02, "Unmarked roads; faded or missing markings"), (C02, "Driver not visible to DM"),
  (C02, "FM-07"), (C02, "FM-08"), (C02, "FM-09"),
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
  m = re.search(r"vision (\d+)/(\d+)/(\d+) s, wheel-touch (\d+)/(\d+)/(\d+) s", _row(s02, "TSR-608", S02))
  if not m:
    raise ValueError(f"{S02}: TSR-608 escalation times not found")
  vision, wheel = [int(m.group(i)) for i in (1, 2, 3)], [int(m.group(i)) for i in (4, 5, 6)]
  extra = int(_num(r"has not responded for (\d+) s", _row(s02, "TSR-633", S02), "TSR-633 delay"))
  faults = []
  for key, plain in FAULTS:
    c = cells(_row(s04, key, S04))
    tsr_id = re.search(r"TSR-\d+", c[2])
    if not tsr_id:
      raise ValueError(f"{S04} §3.7 {key}: no TSR in the FDTI cell")
    faults.append((plain, float(_num(r"([0-9.]+) s", c[1], f"{key} FTTI")), budget(c[2]), budget(c[3]), tsr_id.group(0)))
  c01 = _read(root, C01)
  aous = [(k, plain, cells(_row(c01, k, C01))[-1]) for k, plain in AOUS]
  c02 = _read(root, C02)
  r100 = int(cells(_row(c02, "100", C02))[3])
  sec = c02.split("### 5.2", 1)[1].split("### 5.3", 1)[0]
  exits = [(c[0], exit_kind(c[1])) for c in (cells(r) for r in sec.splitlines() if r.startswith("| ") and not r.startswith("| ODD exit"))]
  return {"cap": cap, "up": up, "down": down, "err": err, "gap_ms": gap_ms, "rate_hz": round(frames / gap_ms * 1000),
          "hb_s": hb_s, "ftti": ftti, "blocked": blocked, "status": status, "vision": vision, "wheel": wheel, "extra": extra,
          "faults": faults, "aous": aous, "r100": r100, "exits": exits}


def cells(line: str) -> list[str]:
  return [c.strip() for c in line.strip().strip("|").split("|")]


def budget(cell: str) -> float:
  """Seconds from a budget cell such as '≤ 0.2 s (TSR-401)' or '≤ 50 ms'."""
  m = re.search(r"≤ ([0-9.]+) (m?s)\b", cell)
  if not m:
    raise ValueError(f"no budget in {cell!r}")
  return float(m.group(1)) / (1000 if m.group(2) == "ms" else 1)


def exit_kind(detected: str) -> str:
  return "yes" if detected.startswith("Yes") else "partly" if detected.startswith("Partly") else "no"


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
    for plain, ftti, det, rea, _k in d["faults"]:
      if ftti != d["ftti"] or det + rea > ftti:
        errs.append(f"{S04} §3.7: '{plain}' no longer ends inside the {d['ftti']:g} s FTTI; how-failures.svg says every bar does")
    if not (d["vision"] == sorted(d["vision"]) and d["wheel"] == sorted(d["wheel"])) or max(d["wheel"]) + d["extra"] > 32:
      errs.append(f"{S02}: TSR-608/633 times changed shape; how-in-charge.svg draws an axis to 32 s")
    kinds = dict(d["exits"])
    for start in UNDETECTED:
      hit = [k for e, k in kinds.items() if e.startswith(start)]
      if hit != ["no"]:
        errs.append(f"{C02} §5.2: exit {start!r} is {hit or 'gone'}; how-odd.svg names it as not detected")
    if len(d["exits"]) > 16:
      errs.append(f"{C02} §5.2: {len(d['exits'])} exits; how-odd.svg draws at most 16")
    errs += code_problems(root, d)
  except (OSError, ValueError, IndexError) as e:
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


def chip(x, y, status: str) -> str:
  col = {"implemented": GRN, "partly": AMBER, "not implemented": RED}.get(status, MID)
  w = len(status) * 6.6 + 14
  return (f'<rect x="{x}" y="{y - 12}" width="{w:.0f}" height="17" rx="8.5" fill="#fff" stroke="{col}" stroke-width="1.3"/>'
          + t(x + w / 2, y + 1, status, 10.5, col, 700, "middle"))


def bar(tl: Timeline, t0: float, dur: float) -> str:
  """CSS class of a bar that grows from its left edge between t0 and t0 + dur; reduced motion shows it full."""
  tl.n += 1
  k = f"k{tl.n}"
  a, e = t0 / tl.loop * 100, (t0 + dur) / tl.loop * 100
  tl.css.append(f"@keyframes {k}{{0%,{a:.2f}%{{transform:scaleX(0)}} {e:.2f}%,100%{{transform:scaleX(1)}}}} "
                f".{k}{{transform-box:fill-box;transform-origin:left;animation:{k} {tl.loop:g}s linear infinite}}")
  return k


# ---------------------------------------------------------------- 4. who is in charge

def in_charge(d: dict) -> str:
  L = 28.0
  tl = Timeline(L)
  st = d["status"]
  b = [t(24, 36, "Who is in charge", 23, NAVY, 700),
       t(24, 58, "The driver supervises at all times: how control changes hands, and what if they stop watching", 14, MID)]
  for i, (a, r, k, c) in enumerate(ACTS):
    y = 96 + 34 * i
    b += [g(tl.show(0.4 + i * 1.6) + " fin", [box(24, y - 18, 196, 26, "#fff", NAVY, 13, 1.3), t(122, y, a, 12.5, NAVY, 700, "middle"),
                                               arrow(222, y - 5, 246, c, 1.8),
                                               t(252, y, ("planned: " if st[k] == "not implemented" else "") + r, 12.5, NAVY),
                                               t(538, y, k, 11.5, MID), chip(592, y - 1, st[k])])]
  y0, x0, x1, smax = 360, 150, 620, 32
  X = lambda s: x0 + s * (x1 - x0) / smax  # noqa: E731
  ax = [line(x0, y0 + 80, x1, y0 + 80, NAVY, 1.5)]
  for s in range(0, smax + 1, 5):
    ax += [line(X(s), y0 + 76, X(s), y0 + 84, NAVY, 1.2), t(X(s), y0 + 100, f"{s} s", 11.5, MID, 400, "middle")]
  b += [g(tl.show(8.6) + " fin", [t(24, 300, "If the driver stops watching the road", 15, NAVY, 700),
                                  t(24, 320, "Time since the driver looked away (driver monitoring, SG-08)", 12.5, MID)] + ax)]
  extra = d["extra"]
  for j, (name, ts) in enumerate([("face visible", d["vision"]), ("face not visible", d["wheel"])]):
    yy, t0, stop = y0 + 50 * j, 9.4 + j * 6.0, ts[2] + extra
    items = [t(24, yy + 4, name, 12.5, NAVY, 700), line(x0, yy, X(stop), yy, MID, 1.2)]
    for i, (s, lab, col) in enumerate(zip(ts, ("alert", "louder", "final alert"), (AMBER, ORANGE, RED), strict=True)):
      items += [f'<circle cx="{X(s):.1f}" cy="{yy}" r="6" fill="{col}"/>',
                t(X(s), yy - 11 if (i % 2 == 0 or j == 1) else yy + 21, f"{lab} {s} s", 11, col, 700, "middle")]
    items += [f'<rect x="{X(stop) - 6:.1f}" y="{yy - 6}" width="12" height="12" fill="{NAVY}"/>',
              t(X(stop) + 10, yy + 4, "slows to a stop", 11, NAVY, 700)]
    b += [g(tl.show(t0) + " fin", items), dot(L, f"M{x0},{yy} L{X(stop):.0f},{yy}", t0 + 0.2, 5.0 + 1.4 * j, RED, 5)]
  b += [g(tl.show(22.0) + " fin", [
    t(24, 492, f"After the final alert and {extra} s more without response, the car slows to a stop in its lane and holds (TSR-633,", 12.5, NAVY),
    t(24, 510, f"{st['TSR-633']}). Times from TSR-608; the 6 s target to the first alert is preliminary (WP-S-04 §3.7).", 12.5, NAVY)])]
  return svg(526, "Who is in charge",
             "Five driver actions and how each changes who controls the car, then the driver-monitoring alerts that escalate "
             "when the driver stops watching, ending in a stop in lane.", tl, b)


# ---------------------------------------------------------------- 5. when something fails

def failures(d: dict) -> str:
  L = 22.0
  tl = Timeline(L)
  ftti = d["ftti"]
  b = [t(24, 36, "When something fails", 23, NAVY, 700),
       t(24, 58, f"How fast the panda notices a fault and makes the steering safe, against the {ftti:g} s it has", 14, MID)]
  x0, x1 = 270, 680
  X = lambda s: x0 + s * (x1 - x0) / 0.5  # noqa: E731
  ax = [line(x0, 118, x0, 300, NAVY, 1.5), line(x0, 300, x1, 300, NAVY, 1.5)]
  for s in (0, 0.1, 0.2, 0.3, 0.4, 0.5):
    ax += [line(X(s), 300, X(s), 306, NAVY, 1.2), t(X(s), 322, f"{s:g} s", 11.5, MID, 400, "middle")]
  b += [g(tl.show(0.3) + " fin", ax + [line(X(ftti), 96, X(ftti), 300, RED, 2.5), t(X(ftti) - 4, 92, f"FTTI {ftti:g} s", 12, RED, 700, "end"),
                                       f'<rect x="{X(0.42):.0f}" y="342" width="14" height="10" fill="{BLUE}"/>', t(X(0.42) + 20, 352, "detect", 12, NAVY),
                                       f'<rect x="{X(0.42):.0f}" y="360" width="14" height="10" fill="{ORANGE}"/>', t(X(0.42) + 20, 370, "react", 12, NAVY)])]
  for i, (plain, _f, det, rea, k) in enumerate(d["faults"]):
    y, t0 = 128 + 34 * i, 1.0 + i * 2.2
    b += [g(tl.show(t0) + " fin", [t(24, y + 15, plain, 13, NAVY, 600), t(24, y + 29, k, 11, MID)]),
          f'<rect x="{x0}" y="{y}" width="{X(det) - x0:.1f}" height="22" fill="{BLUE}" class="{bar(tl, t0, 0.8)}"/>',
          f'<rect x="{X(det):.1f}" y="{y}" width="{X(det + rea) - X(det):.1f}" height="22" fill="{ORANGE}" class="{bar(tl, t0 + 0.8, 0.6)}"/>',
          g(tl.show(t0 + 1.4) + " fin", [t(X(det + rea) + 6, y + 16, f"safe by {det + rea:g} s", 11.5, NAVY, 700)])]
  b += [g(tl.show(12.4) + " fin", [
    t(24, 400, "Safe state: steering torque zero and the driver steers. The panda sounds its own siren within 0.5 s", 13, NAVY, 600),
    t(24, 418, f"(TSR-516, {d['status']['TSR-516']}), even if the main computer has stopped.", 13, NAVY, 600),
    t(24, 446, "Budgets from WP-S-04 §3.7, code-derived and cross-checked in simulation; none measured on the car yet.", 11.5, MID)])]
  return svg(462, "When something fails",
             f"Five faults, each with its detection and reaction time as a bar against the {ftti:g} s FTTI; every bar ends inside it.",
             tl, b)


# ---------------------------------------------------------------- 6. what stays stock

def stock(d: dict) -> str:
  L = 24.0
  tl = Timeline(L)
  b = [t(24, 36, "What stays stock", 23, NAVY, 700),
       t(24, 58, "The car keeps its own safety systems. LionDriver passes them through and never imitates them.", 14, MID)]
  b += [box(196, 80, 290, 160, "none", GRN, 12, 1.6, "6 4"), t(206, 98, "LionDriver (the item)", 12, GRN, 700),
        box(216, 110, 120, 50, QM_BG, MID), t(276, 140, "SoC", 13, NAVY, 700, "middle"),
        box(352, 110, 120, 50, C_BG, GRN, sw=2), t(412, 140, "panda", 13, NAVY, 700, "middle"),
        box(260, 186, 160, 40), t(340, 210, "harness + relay", 12.5, NAVY, 700, "middle"), line(412, 160, 412, 186, NAVY, 2),
        box(24, 150, 140, 64), t(94, 176, "Forward camera", 13, NAVY, 700, "middle"), t(94, 196, "stock PCS / AEB", 12, MID, 400, "middle"),
        line(164, 206, 260, 206, ORANGE, 3)]
  for i, (n, s) in enumerate([("EPS", "own torque limit"), ("Brakes", "PCS braking"), ("PCM", "engine, ACC")]):
    y = 92 + 52 * i
    b += [box(540, y, 156, 42), t(556, y + 18, n, 13, NAVY, 700), t(556, y + 34, s, 11.5, MID), line(520, y + 21, 540, y + 21, BLUE, 2)]
  b += [line(420, 206, 520, 206, BLUE, 3), line(520, 113, 520, 248, BLUE, 3),
        t(24, 236, "outside the item:", 11.5, MID, 700), t(24, 250, "the car's own systems", 11.5, MID)]
  pcs = "M164,206 L260,206 L420,206 L520,206 L520,165 L540,165"
  b += [dot(L, pcs, 0.8, 2.4, GRN, 7), dot(L, pcs, 3.0, 2.4, GRN, 7)]
  b.append(caption(tl, 0.6, 5.6, "The camera's emergency braking messages pass through unchanged.", 290))
  b += [dot(L, "M276,160 L276,172 L412,172 L412,166", 6.4, 1.2, RED, 7), g(tl.show(7.6, 11.6) + " tr", [t(430, 182, "✗", 22, RED, 700)])]
  b.append(caption(tl, 6.2, 11.6, "The device may never send a PCS frame of its own: the panda refuses it.", 290))
  b += [g(tl.show(12.2, 17.4) + " tr", [line(164, 268, 520, 268, ORANGE, 3), line(520, 248, 520, 268, ORANGE, 3),
                                        t(342, 262, "relay dropped: camera straight to the car", 11.5, ORANGE, 700, "middle")]),
        dot(L, "M164,268 L520,268 L520,248", 13.0, 2.4, GRN, 7)]
  b.append(caption(tl, 12.2, 17.4, "If the device fails, the relay drops and the stock path returns.", 290))
  rows = [("Camera PCS messages forwarded unchanged", "TSR-704"), ("The device never sends PCS frames", "TSR-705"),
          ("Relay restores the stock path on any fault", "TSR-706")]
  for i, (s, k) in enumerate(rows):
    y = 322 + 20 * i
    b += [g(tl.show(17.8 + i * 0.4) + " fin", [t(24, y, s, 12.5, NAVY, 600), t(350, y, k, 11.5, MID), chip(410, y - 1, d["status"][k])])]
  b += [g(tl.show(19.4) + " fin", [t(24, 396, "Assumed of the car, to be checked on it (assumptions of use, WP-C-01 §7):", 13, NAVY, 700)])]
  for i, (k, s, st) in enumerate(d["aous"]):
    y = 418 + 19 * i
    b += [g(tl.show(19.8 + i * 0.3) + " fin", [t(24, y, k, 12, MID, 700), t(86, y, s, 12.5, NAVY),
                                               t(500, y, st.lower(), 12, AMBER if st.lower() != "verified" else GRN, 700)])]
  return svg(500, "What stays stock",
             "The car's emergency braking passes through the harness unchanged, the device is never allowed to send it, and the "
             "stock path returns on any fault; then the assumptions about the car still to be checked.", tl, b)


# ---------------------------------------------------------------- 7. where it is meant to work

def odd(d: dict) -> str:
  L = 22.0
  tl = Timeline(L)
  b = [t(24, 36, "Where it is meant to work", 23, NAVY, 700),
       t(24, 58, "The operating domain (ODD) the analysis covers: highways only. Everything else is outside.", 14, MID),
       box(24, 76, 330, 214, "#f1faf5", GRN, 10, 1.6), t(40, 100, "Inside: the system is designed for this", 14, GRN, 700),
       box(366, 76, 330, 214, "#fdf2f0", RED, 10, 1.6), t(382, 100, "Outside: the driver must not rely on it", 14, RED, 700)]
  for i, s in enumerate(INSIDE):
    b += [g(tl.show(0.5 + i * 0.35) + " fin", [t(40, 126 + 21 * i, "✓ " + s.format(**d), 12, NAVY)])]
  for i, s in enumerate(OUTSIDE):
    b += [g(tl.show(3.8 + i * 0.35) + " fin", [t(382, 126 + 21 * i, "✗ " + s, 12, NAVY)])]
  exits = d["exits"]
  n = {k: sum(kind == k for _, kind in exits) for k in ("yes", "partly", "no")}
  b += [g(tl.show(7.6) + " fin", [t(24, 326, "When the car leaves the ODD, does the system notice?", 15, NAVY, 700),
                                  t(24, 346, f"The {len(exits)} ways out of it listed in WP-C-02 §5.2:", 12.5, MID)])]
  w = 672 / len(exits)
  for j, (_e, kind) in enumerate(sorted(exits, key=lambda e: ["yes", "partly", "no"].index(e[1]))):
    col = {"yes": GRN, "partly": AMBER, "no": RED}[kind]
    b += [g(tl.show(8.2 + j * 0.25) + " fin", [f'<rect x="{24 + j * w + 1:.1f}" y="360" width="{w - 2:.1f}" height="26" rx="4" fill="{col}"/>'])]
  b += [g(tl.show(11.4) + " fin", [t(24, 410, f"{n['yes']} detected", 13, GRN, 700), t(130, 410, f"{n['partly']} partly", 13, AMBER, 700),
                                   t(220, 410, f"{n['no']} not detected", 13, RED, 700),
                                   t(24, 438, "Leaving the highway, bad weather, missing markings and speeding above 110 km/h are", 13, NAVY),
                                   t(24, 456, "not detected yet: the driver has to notice and take over. Planned: FM-07, FM-08, FM-09.", 13, NAVY),
                                   t(24, 482, "Source: WP-C-02 §3.1 (ODD), §3.2 (curves), §5.2 (exits).", 11.5, MID)])]
  return svg(496, "Where it is meant to work",
             f"Inside and outside the highway-only ODD, then how many of the {len(exits)} ways out of it the system detects today: "
             f"{n['yes']} detected, {n['partly']} partly, {n['no']} not.", tl, b)


def render(root: Path = ROOT) -> dict[str, str]:
  d = data(root)
  return dict(zip(NAMES, (hookup(d), one_command(d), envelope(d), in_charge(d), failures(d), stock(d), odd(d)), strict=True))


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
