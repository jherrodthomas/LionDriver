#!/usr/bin/env python3
"""Render the animated explainers of the wiki page "Hardware safety and interference" as SVG.

  hw-numbers.svg  FIT, the classification of every failure (safe or detected, latent, single-point and residual),
                  SPFM, LFM, the largest contributors and the PMHF target, on the SG-01 FMEDA;
  hw-ffi.svg      freedom from interference on the panda chip: memory, time and messages, with the verdicts of
                  WP-A-02 §8.

Every number in hw-numbers.svg is computed from the FMEDA records (`fmeda-sg001.yaml`) with the same formulas as
tools/safety/fmea_lint.py, and the ASIL targets are read from WP-H-04; the FFI verdicts are read from WP-A-02 §8 and
the summaries of each channel are checked against their reasons there (`problems()`). When a record changes, the
figures follow it, or the wiki build fails. build_wiki.py renders them next to the pages at each sync (nothing is
committed). They loop with CSS; a viewer who asks for reduced motion sees the final frame.

Usage: python3 tools/wiki/hw_animations.py [--out DIR] [--check]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from animations import GRN, LIGHT, MID, NAVY, RED, W, Timeline, g, norm, stick, svg, t  # noqa: E402

NAMES = ("hw-numbers.svg", "hw-ffi.svg")
AMBER, BLUE, ORANGE = "#b7791f", "#2a78d6", "#c2410c"
FMEDA = Path("assurance") / "08-analyses" / "fmea" / "analyses" / "fmeda-sg001.yaml"
H03 = Path("assurance") / "04-hardware" / "WP-H-03-hardware-safety-analysis-fmeda.md"
H04 = Path("assurance") / "04-hardware" / "WP-H-04-hardware-metrics.md"
H05 = Path("assurance") / "04-hardware" / "WP-H-05-random-hardware-failures-pmhf.md"
A02 = Path("assurance") / "08-analyses" / "WP-A-02-coexistence-freedom-from-interference.md"
GOAL = "SG-01"

SOURCES = [
  (H04, "| SPFM | ≥ 90 % | ≥ 97 % | ≥ 99 % |"), (H04, "| LFM | ≥ 60 % | ≥ 80 % | ≥ 90 % |"),
  (H05, "| SG-01 | C (provisional"), (H05, "< 10⁻⁷ /h (100 FIT)"),
  (H05, "method approved by the lead: PMHF plus a per-cause check of the biggest contributors, DQ-066 option A"),
  (H05, "Draft (method and plan; no value computed)"),
  (H03, "First quantitative estimate with generic failure rates"),
]
TARGETS = {"spfm": [("B", 90), ("C", 97), ("D", 99)], "lfm": [("B", 60), ("C", 80), ("D", 90)]}
# FFI channels: (WP-A-02 §8 level, label, what protects it today, phrase of the §8 reason that summary stands on)
CHANNELS = [
  ("L-MCU spatial", "Memory (spatial)", "No memory protection unit; QM paths run in the same address space", "No MPU"),
  ("L-MCU temporal", "Time (temporal)", "Watchdog and 100 Hz safety task in place; no worst-case execution time", "no WCET"),
  ("L-DEV communication (data)", "Data from the SoC", "TX check limits every frame; weak checksum, no sequence count", "no freshness/sequence and weak checksum"),
  ("L-DEV communication (commands)", "Commands from the SoC", "Mode, relay, reset and reflash commands locked in the reference build", "reset or reflash the MCU"),
  ("L-DEV boot control", "Boot control", "The SoC can still restart the MCU into its bootloader (GAP-38)", "GAP-38"),
]


def metrics(doc: dict, goal: str = GOAL) -> dict:
  """SPFM, LFM and their parts, as tools/safety/fmea_lint.py fmeda_metrics computes them, plus every row's share."""
  total = spf = rf = latent = 0.0
  rows = []
  for comp in doc["components"]:
    if not comp["safety_related"]:
      continue
    lam = comp["failure_rate_fit"]
    total += lam
    for row in comp["failure_modes"]:
      fm = row
      for pg in row.get("per_goal", []):
        if pg["goal"] == goal:
          fm = {**row, **{k: v for k, v in pg.items() if k not in ("goal", "reason")}}
      l_fm = lam * fm["distribution"]
      if fm["violates_sg_directly"]:
        dc = fm.get("dc_spf", 0.0) if fm.get("safety_mechanism_spf") else 0.0
        if dc == 0.0:
          spf += l_fm
          rows.append((l_fm, "single-point", fm["mode"]))
        else:
          rf += l_fm * (1 - dc)
          rows.append((l_fm * (1 - dc), "residual", fm["mode"]))
      elif fm["mpf_potential"]:
        dc_lf = fm.get("dc_lf", 0.0) if fm.get("safety_mechanism_lf") else 0.0
        latent += l_fm * (1 - dc_lf)
        rows.append((l_fm * (1 - dc_lf), "latent", fm["mode"]))
  remaining = total - spf - rf
  return {"total": total, "spf_rf": spf + rf, "latent": latent, "spfm": 1 - (spf + rf) / total,
          "lfm": 1 - latent / remaining if remaining > 0 else 1.0, "top": sorted(rows, reverse=True)[:4]}


def verdicts(root: Path = ROOT) -> dict[str, tuple[str, str]]:
  """{level: (verdict, reason)} from WP-A-02 §8; the verdict is the last bold one in the cell (the current baseline)."""
  text = (root / A02).read_text(encoding="utf-8")
  sec = text[text.index("## 8. FFI verdict"):]
  sec = sec[:sec.index("\n## 9")]
  out = {}
  for line in sec.splitlines():
    if line.startswith("| L-"):
      cells = [c.strip() for c in line.strip().strip("|").split("|")]
      out[cells[0]] = (re.findall(r"\*\*(.+?)\*\*", cells[1])[-1], cells[2])
  return out


def problems(root: Path = ROOT) -> list[str]:
  errs, cache = [], {}
  for path, phrase in SOURCES:
    if path not in cache:
      p = root / path
      cache[path] = norm(p.read_text(encoding="utf-8")) if p.exists() else ""
    if norm(phrase) not in cache[path]:
      errs.append(f"{path}: phrase the hardware figures rely on is gone: {phrase!r}")
  try:
    v = verdicts(root)
  except (OSError, ValueError, IndexError) as e:
    return errs + [f"{A02}: §8 verdicts cannot be read: {e}"]
  for level, _, _, phrase in CHANNELS:
    if level not in v:
      errs.append(f"{A02} §8: no row for {level}")
    elif norm(phrase) not in norm(v[level][1]):
      errs.append(f"{A02} §8 {level}: reason no longer says {phrase!r}; re-check the figure's summary")
  try:
    m = metrics(yaml.safe_load((root / FMEDA).read_text(encoding="utf-8")))
    if m["total"] <= 0:
      errs.append(f"{FMEDA}: no safety-related failure rate")
  except (OSError, yaml.YAMLError, KeyError, TypeError, ZeroDivisionError) as e:
    errs.append(f"{FMEDA}: cannot compute the metrics: {e}")
  return errs


def caps(tl, steps):
  out = []
  for i, (t0, cap) in enumerate(steps):
    t1 = steps[i + 1][0] - 0.2 if i + 1 < len(steps) else None
    out.append(g(f"{tl.show(t0, t1)} {'fin' if t1 is None else 'tr'}", [f'<rect x="24" y="66" width="{W - 48}" height="28" rx="6" fill="{NAVY}"/>', t(36, 85, cap, 13, "#fff", 600)]))
  return out


def verdict_against(v: float, marks) -> tuple[str, str]:
  met = [a for a, x in marks if v * 100 >= x]
  missed = [(a, x) for a, x in marks if v * 100 < x]
  if not missed:
    return "meets ASIL D", GRN
  a, x = missed[0]
  gap = x - v * 100
  head = f"misses ASIL {a} by {gap:.1f} pts" if gap < 1 else f"misses ASIL {a}"
  return (head + (f"; meets {met[-1]}" if met else "")), (RED if a != "D" else MID)


def gauge(x, y, w, value, marks, label, col, tl, t0, lo=50.0):
  X = lambda v: x + (v - lo) / (100 - lo) * w
  o = [t(x, y - 12, label, 13, NAVY, 700), f'<rect x="{x}" y="{y}" width="{w}" height="22" rx="4" fill="#f1f3f7" stroke="{LIGHT}"/>', t(x, y + 40, f"{lo:g} %", 10.5, MID, 400)]
  if max(v for _, v in marks) < 97:
    o.append(t(x + w, y + 40, "100 %", 10.5, MID, 400, "end"))
  for lab, v in marks:
    o += [f'<line x1="{X(v):.1f}" y1="{y - 4}" x2="{X(v):.1f}" y2="{y + 26}" stroke="{NAVY}" stroke-width="1.5" stroke-dasharray="3 2"/>',
          t(X(v), y + 40, f"{lab} {v:g} %", 10.5, MID, 700, "middle")]
  bar = [f'<rect x="{x}" y="{y}" width="{X(value) - x:.1f}" height="22" rx="4" fill="{col}"/>']
  return [g(f"{tl.show(t0)} fin", o), g(f"{tl.show(t0 + 0.8)} fin", bar)]

def numbers(root: Path = ROOT) -> str:
  doc = yaml.safe_load((root / FMEDA).read_text(encoding="utf-8"))
  m = metrics(doc)
  total, spf_rf, lat = m["total"], m["spf_rf"], m["latent"]
  safe = total - spf_rf - lat
  tl, h = Timeline(28.0), 720
  b = [t(24, 38, "Hardware safety in numbers", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "1 · FIT: how often hardware fails"), (4.4, "2 · Sort every failure by what it does to the safety goal"),
                 (9.4, "3 · SPFM: how much is caught before it can harm"), (13.6, "4 · LFM: how much hidden failure is found in time"),
                 (17.8, "5 · Where the risk comes from"), (21.6, "6 · PMHF: the chance per hour the goal is violated")])
  b.append(g(f"{tl.show(0.5)} fin", [t(24, 124, "1 FIT = one failure in 10⁹ device-hours", 15, NAVY, 700),
             t(24, 144, "e.g. a million cars each driven 1,000 hours would see about one failure.", 12.5, MID)]))
  b.append(g(f"{tl.show(2.0)} fin", [f'<rect x="460" y="106" width="236" height="46" rx="10" fill="#eef4fc" stroke="{BLUE}"/>',
             t(474, 126, f"{GOAL} hardware, all failures", 11, BLUE, 700), t(474, 144, f"{total:.1f} FIT (generic estimate)", 14, NAVY, 800)]))
  y, wbar = 196, W - 48
  segs = [("safe or detected", safe, GRN), ("latent: hidden, harmless alone", lat, AMBER), ("single-point + residual: harm directly", spf_rf, RED)]
  x = 24
  for i, (lab, v, col) in enumerate(segs):
    w = max(v / total * wbar, 10)
    b.append(g(f"{tl.show(4.8 + i * 0.9)} fin", [f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="30" fill="{col}"/>',
               t(24 + i * 230, y + 52, lab, 11, col, 700), t(24 + i * 230, y + 68, f"{v:.1f} FIT", 12, NAVY, 700)]))
    x += w
  b.append(g(f"{tl.show(8.0)} fin", [t(24, y + 92, "Single-point: one fault breaks the goal and nothing catches it. Residual: the part a safety mechanism misses.", 11, MID, 400, "start", True),
             t(24, y + 108, "Latent: a fault that does no harm alone, but leaves a safety mechanism unable to act when a second fault comes.", 11, MID, 400, "start", True)]))
  for key, yy, label, col, t0, lo in (("spfm", 350, f"SPFM = 1 − {spf_rf:.1f} / {total:.1f} = {m['spfm'] * 100:.1f} %", ORANGE, 9.6, 80.0),
                                     ("lfm", 440, f"LFM = 1 − {lat:.1f} / {total - spf_rf:.1f} = {m['lfm'] * 100:.1f} %", GRN, 13.8, 50.0)):
    b += gauge(24, yy, 520, m[key] * 100, TARGETS[key], label, col, tl, t0, lo=lo)
    text, vcol = verdict_against(m[key], TARGETS[key])
    words = text.split("; ")
    b.append(g(f"{tl.show(t0 + 1.6)} fin", [t(560, yy + 18 + i * 16, w + (";" if i < len(words) - 1 else ""), 11.5, vcol, 700) for i, w in enumerate(words)]))
  cy = 528
  b.append(g(f"{tl.show(18.0)} fin", [t(24, cy, "Largest contributors (FIT)", 13, NAVY, 700)]))
  for i, (v, kind, mode) in enumerate(m["top"]):
    yy = cy + 20 + i * 22
    label = mode if len(mode) <= 62 else mode[:61].rstrip(" ,(") + "…"
    b.append(g(f"{tl.show(18.4 + i * 0.5)} fin", [f'<rect x="24" y="{yy - 12}" width="{max(v * 16, 4):.0f}" height="14" rx="3" fill="{ORANGE}"/>',
               t(24 + max(v * 16, 4) + 8, yy, f"{v:.2g}  {label} ({kind})", 11.5, NAVY)]))
  b.append(g(f"{tl.show(21.8)} fin", [f'<rect x="24" y="626" width="{W - 110}" height="70" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 648, "PMHF target for ASIL C: fewer than 100 FIT that violate the goal. Not computed yet:", 12.5, NAVY, 700),
             t(40, 666, "the method is approved (DQ-066 A); it needs the real parts and their failure rates.", 12.5, NAVY),
             t(40, 684, "All numbers here are generic-rate estimates (WP-H-03 §6.3), not the real bill of materials.", 11.5, MID)]))
  b.append(stick(W - 40, h - 14, "point"))
  return svg(h, "Hardware safety in numbers (animated)",
             f"{GOAL} FMEDA with generic failure rates: {total:.1f} FIT in all, {safe:.1f} safe or detected, {lat:.1f} latent, "
             f"{spf_rf:.1f} single-point and residual. SPFM {m['spfm'] * 100:.1f} % ({verdict_against(m['spfm'], TARGETS['spfm'])[0]}); "
             f"LFM {m['lfm'] * 100:.1f} % ({verdict_against(m['lfm'], TARGETS['lfm'])[0]}). Largest contributors: "
             + "; ".join(f"{mode} {v:.2g} FIT" for v, _, mode in m["top"]) + ". PMHF target for ASIL C below 100 FIT, not computed yet.", tl, b)


def ffi(root: Path = ROOT) -> str:
  v = verdicts(root)
  tl, h = Timeline(26.0), 680
  b = [t(24, 38, "Freedom from interference", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "1 · A safety part shares a chip with parts that are not safety-rated (QM)"),
                 (3.6, "2 · Memory: QM code must not overwrite the safety code's data"),
                 (8.4, "3 · Time: QM work must not delay the safety task"),
                 (13.2, "4 · Messages: the openpilot computer must not send what breaks the envelope"),
                 (18.4, "5 · Where we are: FFI must be shown before gate G2 (WP-A-02)")])
  # chip
  b.append(g(f"{tl.show(0.5)} fin", [f'<rect x="24" y="108" width="440" height="230" rx="14" fill="#fff" stroke="{NAVY}" stroke-width="2"/>',
             t(40, 130, "panda MCU (one chip, one CPU, one memory)", 12.5, NAVY, 700),
             f'<rect x="40" y="146" width="200" height="80" rx="10" fill="#fff6ef" stroke="{ORANGE}" stroke-width="2.5"/>',
             t(140, 174, "Safety envelope", 13.5, NAVY, 700, "middle"), t(140, 194, "ASIL C · limits, authority", 11, MID, 400, "middle"),
             t(140, 212, "100 Hz safety task", 11, MID, 400, "middle"),
             f'<rect x="256" y="146" width="192" height="80" rx="10" fill="#f1f3f7" stroke="{MID}" stroke-width="1.8"/>',
             t(352, 174, "Other firmware", 13.5, NAVY, 700, "middle"), t(352, 194, "QM · USB, SPI, other modes", 11, MID, 400, "middle"),
             t(352, 212, "debug commands", 11, MID, 400, "middle"),
             f'<rect x="40" y="242" width="408" height="30" rx="6" fill="#f4f6f9" stroke="{LIGHT}"/>', t(244, 262, "shared memory (RAM)", 11.5, MID, 700, "middle"),
             f'<rect x="40" y="282" width="408" height="30" rx="6" fill="#f4f6f9" stroke="{LIGHT}"/>', t(244, 302, "shared CPU time", 11.5, MID, 700, "middle"),
             f'<rect x="560" y="146" width="136" height="80" rx="10" fill="#f1f3f7" stroke="{NAVY}" stroke-width="1.8"/>',
             t(628, 174, "openpilot", 13.5, NAVY, 700, "middle"), t(628, 194, "computer (SoC)", 11, MID, 400, "middle"), t(628, 212, "QM", 11, MID, 400, "middle"),
             f'<line x1="464" y1="186" x2="560" y2="186" stroke="{LIGHT}" stroke-width="3"/>', t(512, 178, "SPI", 10.5, MID, 700, "middle")]))
  # memory
  b.append(g(f"{tl.show(3.8, 8.2)} tr", [f'<path d="M352,226 C352,250 200,236 160,248" fill="none" stroke="{RED}" stroke-width="3" stroke-dasharray="6 4"/>',
             f'<rect x="120" y="244" width="80" height="26" rx="4" fill="{RED}" opacity="0.85"/>', t(160, 262, "limits?!", 11, "#fff", 800, "middle")]))
  # time
  b.append(g(f"{tl.show(8.6, 13.0)} tr", [f'<rect x="256" y="284" width="190" height="26" rx="4" fill="{RED}" opacity="0.8"/>', t(351, 302, "QM work hogs the CPU", 11, "#fff", 700, "middle"),
             f'<rect x="44" y="284" width="60" height="26" rx="4" fill="{ORANGE}"/>', t(74, 302, "late!", 11, "#fff", 800, "middle")]))
  # messages
  b.append(g(f"{tl.show(13.4, 18.2)} tr", [f'<rect x="478" y="196" width="72" height="22" rx="4" fill="{RED}"/>', t(514, 211, "reflash!", 10.5, "#fff", 800, "middle"),
             f'<rect x="478" y="222" width="72" height="22" rx="4" fill="{RED}"/>', t(514, 237, "stale cmd", 10.5, "#fff", 800, "middle")]))
  rows = []
  for (level, label, why, _), t0 in zip(CHANNELS, (4.4, 9.2, 14.0, 15.4, 16.6)):
    verdict = v[level][0].replace(" in the reference build", "")
    verdict = {"Partially shown": "Partly shown"}.get(verdict, verdict)
    rows.append((label, why, verdict, GRN if verdict == "Shown" else AMBER if verdict == "Partly shown" else RED, t0))
  y = 360
  b.append(g(f"{tl.show(4.2)} fin", [t(24, y, "Channel", 11.5, MID, 700), t(200, y, "What protects it today", 11.5, MID, 700), t(W - 24, y, "Verdict", 11.5, MID, 700, "end")]))
  for i, (ch, why, verdict, col, t0) in enumerate(rows):
    yy = y + 30 + i * 40
    w = len(verdict) * 7 + 18
    b.append(g(f"{tl.show(t0)} fin", [f'<rect x="20" y="{yy - 20}" width="{W - 40}" height="34" rx="6" fill="{"#f4f6f9" if i % 2 == 0 else "#fff"}"/>',
               t(28, yy, ch, 12.5, NAVY, 700), t(200, yy, why, 11, NAVY),
               f'<rect x="{W - 24 - w}" y="{yy - 15}" width="{w}" height="22" rx="11" fill="{col}"/>', t(W - 24 - w / 2, yy, verdict, 10.5, "#fff", 700, "middle")]))
  b.append(g(f"{tl.show(18.6)} fin", [f'<rect x="24" y="580" width="{W - 110}" height="64" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 602, "Without FFI, a QM fault could break the ASIL C envelope, and the safety", 12.5, NAVY, 700),
             t(40, 620, "concept that puts all the safety in the envelope would not hold.", 12.5, NAVY, 700),
             t(40, 638, "Cascading: one failure causing another. Common cause: one root breaking two parts (DFA, WP-A-03).", 11, MID)]))
  b.append(stick(W - 40, h - 14, "point"))
  return svg(h, "Freedom from interference (animated)",
             "The panda chip runs the ASIL C safety envelope next to QM firmware, sharing memory and CPU time, and takes commands "
             "from the QM openpilot computer. Interference by memory, by time and by messages, and the verdicts of WP-A-02: "
             + "; ".join(f"{r[0]} {r[2].lower()}" for r in rows) + ". FFI must be shown before gate G2.", tl, b)


def render(root: Path = ROOT) -> dict[str, str]:
  return {"hw-numbers.svg": numbers(root), "hw-ffi.svg": ffi(root)}


def write_all(out: Path, root: Path = ROOT) -> None:
  out.mkdir(parents=True, exist_ok=True)
  for name, text in render(root).items():
    (out / name).write_text(text, encoding="utf-8")


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--out", type=Path, default=None, help="write the SVGs here")
  ap.add_argument("--check", action="store_true", help="fail if a record the figures rely on changed")
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
