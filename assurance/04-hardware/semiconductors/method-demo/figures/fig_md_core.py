#!/usr/bin/env python3
"""Figures 1 and 2 of the Part 11 method demonstration (assurance/04-hardware/semiconductors/method-demo).

Figure 1 · the PicoRV32 core synthesised to sky130 cells, split into ten sub-parts: a tree map sized by cell area, the
netlist facts and the most used cells. Every number comes from results/subparts.json.
Figure 2 · the measured diagnostic coverage of the software self-test per sub-part, for stuck-at faults and bit flips, the
whole-core totals and the three test runs. Every number comes from results/coverage.json and results/coverage-history.json.

Fails (FigureError) when a results file or field is missing, the sub-parts are not the expected ten, a share or coverage
is outside 0..1, the sub-part areas do not add up to the core, or the history does not end with the current run.

    python3 fig_md_core.py            # write both SVGs
    python3 fig_md_core.py --check    # exit 1 when a results file changed shape or an SVG is stale
"""
from __future__ import annotations

import sys

from mdkit import (HERE, MONO, INK, MUTED, FAINT, LINE, HAIR, CHIP, SAFETY, SAFETY_BG, SW, SW_BG, HW, HW_BG, GREEN, GREEN_BG,
                   AMBER, RED, SUB_COLOUR, FigureError, load, need, check_sub_parts, pct, arrow, squarify, name,
                   el, fmt, text, rect, line, svg, header, terms)

REF = "ISO 26262-11 method demonstration · supports WP-H-03, WP-H-07"
NAMES = {"split": "fig-md-1-core-split.svg", "coverage": "fig-md-2-measured-coverage.svg"}


def col(dc: float) -> str:
  return GREEN if dc >= 0.90 else AMBER if dc >= 0.60 else RED


def fig_split(S: dict) -> str:
  need(S, "cells", "flip_flops", "area_um2", "register_file_read_port_cells", "unattributed_cells", "cell_types", "sub_parts")
  subs = S["sub_parts"]
  check_sub_parts([s["sub_part"] for s in subs], "subparts.json")
  tot = sum(s["area_um2"] for s in subs)
  if abs(tot - S["area_um2"]) > 1.0:
    raise FigureError(f"sub-part areas add to {tot:.1f}, the core is {S['area_um2']:.1f}")
  if sum(s["flip_flops"] for s in subs) != S["flip_flops"]:
    raise FigureError("sub-part flip-flops do not add up to the core")
  W, H = 1500, 1010
  b = header(W, "1", "PicoRV32 synthesised to real cells, split for the FMEDA",
             "An open RISC-V core turned into SkyWater 130 nm standard cells with Yosys. Every count on this figure comes from that netlist.", REF)
  tx, ty, tw, th = 40, 100, 890, 620
  by = {s["sub_part"]: s for s in subs}
  for key, x, y, w, h in squarify([(s["sub_part"], s["area_um2"]) for s in subs], tx, ty, tw, th):
    s = by[key]
    if not 0 < s["area_share"] < 1:
      raise FigureError(f"area share of {key} out of range")
    b.append(rect(x + 2, y + 2, w - 4, h - 4, fill=SUB_COLOUR[key], stroke="#FFFFFF", sw=2, rx=6))
    small = w < 140
    b.append(text(x + 12, y + 28, name(key), 14 if small else 17, "#FFFFFF", "700"))
    b.append(text(x + 12, y + 50, pct(s["area_share"]) + ("" if small else " of core area"), 13, "#FFFFFF", "600"))
    if h > 100:
      b.append(text(x + 12, y + 74, f"{s['flip_flops']:,} {'FF' if small else 'flip-flops'}", 12, "#FFFFFF", family=MONO))
      b.append(text(x + 12, y + 92, f"{s['logic_cells']:,} {'cells' if small else 'logic cells'}", 12, "#FFFFFF", family=MONO))
  b.append(text(tx, ty + th + 24, "Tile area = cell area of the sub-part: its flip-flops plus the logic that feeds them", 12, MUTED))
  px, pw = 960, 500
  b.append(rect(px, 100, pw, 232, fill=HW_BG, stroke=HW, sw=1, rx=12))
  b.append(text(px + 20, 130, "The netlist", 16, HW, "700"))
  facts = [("standard cells", f"{S['cells']:,}"), ("flip-flops", f"{S['flip_flops']:,}"),
           ("cell area", f"{S['area_um2']:,.0f} µm² ({S['area_um2'] / 1e6:.3f} mm²)"),
           ("register-file read-port cells", f"{S['register_file_read_port_cells']:,}"),
           ("cells not assigned to a sub-part", f"{S['unattributed_cells']}"),
           ("fault list (stuck-at 0/1 per cell output, one flip per flip-flop)", f"{2 * S['cells'] + S['flip_flops']:,}")]
  for k, (a, v) in enumerate(facts):
    b.append(text(px + 20, 160 + k * 28, a, 13, INK))
    b.append(text(px + pw - 20, 160 + k * 28, v, 13, INK, "700", "end", family=MONO))
  ct = sorted(S["cell_types"].items(), key=lambda kv: (-kv[1], kv[0]))[:8]
  y0 = 362
  b.append(text(px, y0, "Most used cells", 15, INK, "700"))
  for k, (n, v) in enumerate(ct):
    y = y0 + 16 + k * 27
    short = n.replace("sky130_fd_sc_hd__", "")
    b.append(text(px, y + 15, short, 12, INK, family=MONO))
    w = 290 * v / ct[0][1]
    b.append(rect(px + 150, y + 3, w, 16, fill=SAFETY if "df" in short else HW, stroke="none", sw=0, rx=3))
    b.append(text(px + 156 + w, y + 16, f"{v:,}", 12, MUTED, family=MONO))
  b.append(text(px, y0 + 248, "orange = flip-flops (edfxtp has an enable input)", 12, MUTED))
  rf = by["Register file"]
  b.append(rect(px, 640, pw, 120, fill=SAFETY_BG, stroke=SAFETY, sw=1, rx=12))
  b.append(text(px + 20, 668, "What this changes in the FMEDA", 15, SAFETY, "700"))
  for k, t in enumerate([f"The register file is {pct(rf['area_share'], 0)} of the core ({rf['flip_flops']:,} flip-flops), so it carries",
                         "that share of the core's failure rate. A register file built from flip-flops is",
                         "big; a memory macro with ECC would change the split."]):
    b.append(text(px + 20, 694 + k * 20, t, 13, INK))
  y = 790
  b.append(rect(40, y, 1420, 110, fill=CHIP, stroke=LINE, sw=1, rx=12))
  b.append(text(60, y + 28, "How the split was made, and its limits", 15, INK, "700"))
  for k, t in enumerate([
      "• Flip-flops are grouped by the register they implement; each logic cell goes to the sub-parts whose flip-flops it feeds (shared cells split equally).",
      "• Register-file read multiplexers count in the register file. Cell area at the typical corner: no placement, wiring or clock tree.",
      "• Configuration: RV32I with multiply, divide, interrupts and counters. Sizes only, no failure rate. An open core, not the STM32 in LionDriver: this is a method demonstration, not evidence."]):
    b.append(text(60, y + 54 + k * 22, t, 12.5, INK))
  b.append(text(40, 926, "PicoRV32 © 2015 Claire Xenia Wolf, ISC licence. sky130_fd_sc_hd cell library, Apache-2.0. Synthesis: Yosys, "
                "synth -flatten, dfflibmap and abc to the tt_025C_1v80 liberty (flow/synth.ys).", 11, FAINT))
  extra, yy = terms.svg_footer(b, 40, 950, W - 80)
  return svg(W, int(yy + 14), "Figure 1 · PicoRV32 sub-part split",
             f"Tree map of the {S['cells']:,}-cell PicoRV32 netlist in ten sub-parts by cell area; register file "
             f"{pct(rf['area_share'])}. Drawn from results/subparts.json.", b + extra)


FINDINGS_LEFT = ["What is left, and why:",
                 "• x0's storage and unused coprocessor fields can",
                 "  never matter: {safe} provably safe faults.",
                 "• End-of-interrupt output: software can't see it.",
                 "• Counter high bits: bit 63 needs millennia to",
                 "  become 1 (Part 11 in one minute, 1).",
                 "Bit flips: {seu} change a result; the rest are",
                 "  overwritten first. Those need ECC or lockstep."]


def fig_coverage(C: dict, Hst: dict) -> str:
  need(C, "faults", "cycles", "seconds", "perm_faults", "perm_detected", "perm_dc", "perm_dc_excl_safe", "safe_faults",
       "seu_faults", "seu_dc", "sub_parts")
  rows = C["sub_parts"]
  check_sub_parts([r["sub_part"] for r in rows], "coverage.json")
  runs = Hst["runs"]
  if not runs or abs(runs[-1]["perm_dc"] - C["perm_dc"]) > 1e-9:
    raise FigureError("coverage-history.json does not end with the current run")
  W, H = 1500, 1120
  b = header(W, "2", "Measured diagnostic coverage of a software self-test, on real gates",
             f"PicoRV32 netlist, {C['faults']:,} faults, each simulated while the self-test runs. Coverage = share of faults the test makes visible.", REF)
  steps = [("1 Synthesise", "PicoRV32 → sky130", "cells (Yosys)"), ("2 Self-test", "every result stored", "to memory"),
           ("3 Golden run", f"{C['cycles']:,} cycles, checked", "against an ISA model"),
           ("4 Fault list", "stuck-at 0/1 per cell,", "one flip per FF"), ("5 Simulate", "thousands of faulty", "cores side by side"),
           ("6 Score", "visible on the bus", "= detected")]
  for j, (n, a, c) in enumerate(steps):
    x = 40 + j * 238
    fg, bg = [(HW, HW_BG), (SW, SW_BG), (GREEN, GREEN_BG), (SAFETY, SAFETY_BG), (SW, SW_BG), (GREEN, GREEN_BG)][j]
    b.append(rect(x, 98, 222, 80, fill=bg, stroke=fg, sw=1.4, rx=10))
    b.append(text(x + 14, 121, n, 14, fg, "700"))
    b.append(text(x + 14, 143, a, 12.5, INK))
    b.append(text(x + 14, 162, c, 12.5, INK))
    if j < 5:
      b += arrow(x + 223, 138, x + 237, 138)
  cx, cy, cw, ch = 40, 198, 920, 640
  b.append(rect(cx, cy, cw, ch, fill="#FFFFFF", stroke=LINE, sw=1, rx=12))
  b.append(text(cx + 20, cy + 30, "Coverage per sub-part: stuck-at faults (bar) and bit flips (diamond)", 15, INK, "700"))
  lx, bx, bw = cx + 20, cx + 270, 560
  for p in (0, 60, 90, 99):
    xx = bx + bw * p / 100
    b.append(line(xx, cy + 52, xx, cy + ch - 50, stroke=LINE if p else HAIR, sw=1, dash="3 3" if p else ""))
    if p != 99:
      b.append(text(xx, cy + ch - 30, f"{p} %", 12, MUTED, anchor="middle"))
  rowh = (ch - 120) / len(rows)
  for i, r in enumerate(rows):
    for k in ("perm_dc", "perm_faults", "seu_faults"):
      if k not in r:
        raise FigureError(f"{r['sub_part']}: {k} missing")
    if not 0 <= r["perm_dc"] <= 1:
      raise FigureError(f"{r['sub_part']}: coverage out of range")
    y = cy + 58 + i * rowh
    b.append(text(lx, y + 18, name(r["sub_part"]), 14, INK, "600"))
    b.append(text(lx, y + 36, f"{r['perm_faults']:,} stuck-at · {r['seu_faults']:,} flips", 12, MUTED, family=MONO))
    d = r["perm_dc"]
    b.append(rect(bx, y + 8, bw * d, 22, fill=col(d), stroke="none", sw=0, rx=3))
    b.append(text(bx + bw * d + 8, y + 25, pct(d), 13, col(d), "700", family=MONO))
    if r["seu_dc"] is not None:
      sx = bx + bw * r["seu_dc"]
      b.append(el("path", None, d=f"M{fmt(sx)},{fmt(y + 30)} l7,7 l-7,7 l-7,-7 z", fill=INK, stroke="#FFFFFF", stroke_width=1))
  b.append(text(cx + 20, cy + ch - 12, "Bar: stuck-at faults found by the test. Diamond: single bit flips (one random cycle each) that changed a result.", 12, MUTED))
  px, pw = 984, 476
  b.append(rect(px, 198, pw, 256, fill=HW_BG, stroke=HW, sw=1, rx=12))
  b.append(text(px + 20, 228, "Whole core", 16, HW, "700"))
  n_safe = sum(C["safe_faults"].values())
  facts = [("stuck-at faults", f"{C['perm_faults']:,}"), ("  found by the self-test", f"{C['perm_detected']:,}"),
           ("  diagnostic coverage", pct(C["perm_dc"])), (f"  without {n_safe} provably safe faults", pct(C["perm_dc_excl_safe"])),
           ("bit flips", f"{C['seu_faults']:,}"), ("  that changed a result", pct(C["seu_dc"])),
           ("simulation time, 4 CPUs", f"{C['seconds'] / 60:.1f} min")]
  for k, (a, v) in enumerate(facts):
    y = 258 + k * 27
    b.append(text(px + 20 + (14 if a.startswith("  ") else 0), y, a.strip(), 13, INK, "700" if "coverage" in a else ""))
    b.append(text(px + pw - 20, y, v, 14, INK, "700", "end", family=MONO))
  b.append(rect(px, 470, pw, 368, fill=SAFETY_BG, stroke=SAFETY, sw=1, rx=12))
  b.append(text(px + 20, 498, "Three runs: each fix came from the missed faults", 15, SAFETY, "700"))
  y = 524
  for r in runs:
    b.append(text(px + 20, y, f"Run {r['run']}: {pct(r['perm_dc'])}", 13, INK, "700"))
    words, cur, out = r["change"].split(), "", []
    for w in words:
      if len(cur) + len(w) > 58:
        out.append(cur)
        cur = w
      else:
        cur = (cur + " " + w).strip()
    out.append(cur)
    for t in out:
      y += 18
      b.append(text(px + 34, y, t, 12, INK))
    y += 24
  for t in FINDINGS_LEFT:
    t = t.format(safe=n_safe, seu=pct(C["seu_dc"], 0))
    b.append(text(px + 20 + (14 if t.startswith("  ") else 0), y, t.strip(), 12.5, INK, "700" if t.endswith(":") else ""))
    y += 19
  y = 858
  b.append(rect(40, y, 1420, 168, fill=CHIP, stroke=LINE, sw=1, rx=12))
  b.append(text(60, y + 28, "How 'detected' is defined, and the limits", 15, INK, "700"))
  for k, t in enumerate([
      "• Detected = the faulty core's memory-bus traffic differs from the fault-free core during the test: a wrong stored result, a wrong address,",
      "   a missing or extra access, or a trap. The test stores every result, so a compare against known-good results plus a run-time watchdog sees exactly this.",
      "• Faults outside the test's reach count as undetected even if no program would be affected: the coverage is conservative.",
      "• Two-valued logic, flip-flops start at 0, faults on cell outputs only, one random cycle per bit flip. Runs 1 and 2 used earlier versions of the self-test.",
      "• An open RISC-V core, not the STM32's Cortex-M7: this shows how a self-test is graded. It is a method demonstration, not LionDriver evidence."]):
    b.append(text(60 + (14 if t.startswith("   ") else 0), y + 54 + k * 22, t.strip(), 12.5, INK))
  b.append(text(40, 1050, "Simulation: our bit-parallel gate simulator over the liberty cell functions (flow/gatesim.py); self-test, ISA model "
                "and scoring in flow/.", 11, FAINT))
  extra, yy = terms.svg_footer(b, 40, 1074, W - 80)
  return svg(W, int(yy + 14), "Figure 2 · Measured self-test coverage",
             f"Stuck-at coverage of the self-test per PicoRV32 sub-part; whole core {pct(C['perm_dc'])} of {C['perm_faults']:,} "
             f"faults, bit flips {pct(C['seu_dc'])} visible. Drawn from results/coverage.json.", b + extra)


def build() -> dict[str, str]:
  return {NAMES["split"]: fig_split(load("subparts.json")),
          NAMES["coverage"]: fig_coverage(load("coverage.json"), load("coverage-history.json"))}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except FigureError as e:
    print(f"fig_md_core: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"method-demo/figures/{n} is stale; run fig_md_core.py", file=sys.stderr)
    if not stale:
      print(f"fig_md_core: {len(outputs)} figures current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote method-demo/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
