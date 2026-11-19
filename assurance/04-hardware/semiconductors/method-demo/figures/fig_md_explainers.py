#!/usr/bin/env python3
"""The six "Part 11 in one minute" explainers (phone format) of the Part 11 method demonstration.

  E1 how long before the top bit of a counter is ever tested   results/coverage.json (self-test length); 50 MHz assumed
  E2 where a CPU's failure rate goes                           results/subparts.json, results/sky130_dfxtp_1.json
  E3 how to check that a CPU self-test really works            results/coverage.json, results/coverage-history.json
  E4 why one flipped bit doesn't crash the CPU                 results/coverage.json
  E5 what ECC on the register file buys                        results/ecc_summary.json
  E6 why run two CPUs (lockstep)                               results/lockstep_summary.json

Every number is read from those files. Illustrative parts (the example values in the E3 and E4 pictures) say so on
the figure. Fails (FigureError) on a missing file or field, a wrong set of sub-parts, counts that do not add up, a
transistor count that is not what the layout shows, or a lockstep result where a wrong command was not caught first.

    python3 fig_md_explainers.py            # write the six SVGs
    python3 fig_md_explainers.py --check    # exit 1 when a results file changed shape or an SVG is stale
"""
from __future__ import annotations

import math
import sys

from mdkit import (HERE, MONO, INK, MUTED, FAINT, LINE, HAIR, CHIP, SAFETY, SAFETY_BG, SW, SW_BG, HW, HW_BG, GREEN, GREEN_BG,
                   AMBER, AMBER_BG, RED, RED_BG, GREY_BG, SUB_COLOUR, PW, FigureError, load, need, check_sub_parts, pct, arrow,
                   squarify, name, frame, tiles, finish, el, fmt, text, rect, line)

CLK = 50e6        # assumed clock for E1, stated on the figure
YEAR = 3.156e7    # seconds
NAMES = {k: f"fig-md-{k.lower()}-{s}.svg" for k, s in [("E1", "counter-bits"), ("E2", "where-lambda-goes"), ("E3", "grading-a-selftest"),
                                                       ("E4", "bit-flips"), ("E5", "what-ecc-buys"), ("E6", "why-lockstep")]}
SRC = "PicoRV32 (ISC) synthesised with Yosys to sky130_fd_sc_hd (Apache-2.0); "


# ---------------------------------------------------------------- E1
def e1(C: dict) -> str:
  need(C, "cycles")
  cyc = C["cycles"]
  b, y = frame(1, ["How long before the top bit", "of a counter is ever tested?"], "a bit stuck at 0 only shows up once it should be 1",
               ["fault", "wait", "test", "gap", "fix"], 1)
  b.append(rect(24, y, PW - 48, 230, fill=CHIP, stroke=LINE, sw=1, rx=14))
  b.append(text(44, y + 28, "64-bit cycle counter, counting up from reset", 14, INK, "700"))
  bw = (PW - 88) / 32
  for row in range(2):
    for k in range(32):
      bit = 63 - (row * 32 + k)
      t = 2 ** bit / CLK
      c = GREEN if t < 1e-3 else AMBER if t < 3600 else RED
      x, yy = 44 + k * bw, y + 50 + row * 70
      b.append(rect(x + 1, yy, bw - 2, 34, fill=c, stroke="#FFFFFF", sw=1, rx=3))
      if bit in (63, 48, 32, 31, 16, 0):
        b.append(text(x + bw / 2, yy + 50, str(bit), 11, MUTED, "", "middle", family=MONO))
  b.append(el("circle", None, cx=fmt(44 + bw / 2), cy=fmt(y + 67), r=9, fill="none", stroke=INK, stroke_width=2.5))
  x = 44
  for n, c in [("found within 1 ms", GREEN), ("within 1 hour", AMBER), ("later than that", RED)]:
    b.append(rect(x, y + 176, 14, 14, fill=c, stroke="none", sw=0, rx=3))
    b.append(text(x + 20, y + 188, n, 12, INK))
    x += 30 + len(n) * 6.6
  b.append(text(44, y + 212, "circled: bit 63 stuck at 0 stays invisible until the counter reaches 2^63", 12, INK, "600"))
  y += 250
  b.append(rect(24, y, PW - 48, 70, fill=SAFETY_BG, stroke=SAFETY, sw=1.5, rx=12))
  b.append(text(PW / 2, y + 30, f"At 50 MHz: bit 31 after {2 ** 31 / CLK:.0f} seconds.", 18, INK, "700", "middle"))
  b.append(text(PW / 2, y + 56, f"Bit 63 after {2 ** 63 / CLK / YEAR:,.0f} years.", 18, SAFETY, "800", "middle"))
  y += 92
  life = 15 * YEAR * CLK
  y = tiles(b, y, [("our self-test", f"{cyc / CLK * 1e3:.2f}", "milliseconds", f"{cyc:,} cycles", HW),
                   ("bits it can reach", f"{int(math.log2(cyc)) + 1}", "of 64", f"bits 0 to {int(math.log2(cyc))}", AMBER),
                   ("one 15-year car life", f"{int(math.log2(life)) + 1}", "bits reached", f"bits 0 to {int(math.log2(life))}, not 63", RED)])
  cx, cy, cw, ch = 70, y + 20, PW - 110, 300
  b.append(text(24, cy - 4, "time until bit k first becomes 1 (log scale)", 13, INK, "700"))
  lo, hi = -8, 12
  Y = lambda s: cy + ch - (math.log10(s) - lo) / (hi - lo) * ch
  X = lambda k: cx + k / 63 * cw
  for s, lab in ((1e-6, "1 µs"), (1e-3, "1 ms"), (1, "1 s"), (3600, "1 h"), (YEAR, "1 yr"), (1000 * YEAR, "1,000 yr")):
    b.append(line(cx, Y(s), cx + cw, Y(s), stroke=HAIR, sw=1))
    b.append(text(cx - 6, Y(s) + 4, lab, 11, MUTED, "", "end"))
  b.append(el("path", None, d="M" + " L".join(f"{fmt(X(k))},{fmt(Y(2 ** k / CLK))}" for k in range(64)), fill="none", stroke=HW, stroke_width=3))
  for s, lab, c in ((cyc / CLK, "our self-test", GREEN), (3600, "one drive", AMBER), (15 * YEAR, "car lifetime", RED)):
    b.append(line(cx, Y(s), cx + cw, Y(s), stroke=c, sw=1.6, dash="6 4"))
    b.append(text(cx + cw, Y(s) - 6, lab, 11, c, "700", "end"))
  for k in (0, 16, 32, 48, 63):
    b.append(text(X(k), cy + ch + 18, str(k), 11, MUTED, "", "middle", family=MONO))
  b.append(text(cx + cw / 2, cy + ch + 36, "bit k of the counter", 12, MUTED, "", "middle"))
  return finish(b, cy + ch + 40, "Not a lazy test: counting itself hides these faults.",
                ["Assumed: 50 MHz clock, counter starts at 0 on reset. Self-test length from our PicoRV32 campaign.",
                 "In the FMEDA: count these faults as not testable in time, or check the counter against a second clock."],
                "Part 11 in one minute 1 · counter bits",
                f"A 64-bit counter's bit k is first 1 after 2^k cycles: bit 63 after {2 ** 63 / CLK / YEAR:,.0f} years at 50 MHz; "
                f"our {cyc:,}-cycle self-test reaches bits 0 to {int(math.log2(cyc))}.")


# ---------------------------------------------------------------- E2
def e2(S: dict, L: dict) -> str:
  need(S, "sub_parts", "cells", "flip_flops", "area_um2", "cell_types")
  need(L, "gates", "layers", "bbox", "cell")
  check_sub_parts([s["sub_part"] for s in S["sub_parts"]], "subparts.json")
  ntr = len(L["gates"])
  if ntr != 24:
    raise FigureError(f"{L['cell']}: {ntr} transistor gates, the figure says 24")
  b, y = frame(2, ["Where does a CPU's", "failure rate go?"], "split it by what the silicon is made of", ["chip", "core", "sub-parts", "cell", "λ"], 2)
  by = {s["sub_part"]: s for s in S["sub_parts"]}
  th = 330
  for key, x, yy, w, h in squarify([(s["sub_part"], s["area_um2"]) for s in S["sub_parts"]], 24, y, PW - 48, th):
    s = by[key]
    b.append(rect(x + 2, yy + 2, w - 4, h - 4, fill=SUB_COLOUR[key], stroke="#FFFFFF", sw=2, rx=6))
    if w > 80 and h > 44:
      b.append(text(x + 10, yy + 24, name(key), 13 if w < 160 else 16, "#FFFFFF", "700"))
      b.append(text(x + 10, yy + 44, pct(s["area_share"], 0), 13, "#FFFFFF", "600"))
    else:
      for m, t in enumerate(name(key).split(" ") + [pct(s["area_share"], 0)]):
        b.append(text(x + 8, yy + 22 + m * 16, t, 11, "#FFFFFF", "700"))
  b.append(text(24, y + th + 20, f"PicoRV32 synthesised to {S['cells']:,} real cells; tile size = silicon area", 12, MUTED))
  y += th + 40
  (x0, y0), (x1, y1) = L["bbox"]
  rw = PW - 48 - 220
  s_ = rw / (x1 - x0)
  T = lambda p: (24 + (p[0] - x0) * s_, y + (y1 - p[1]) * s_)
  style = [("nwell", "#FEF3C7", 0.6), ("diff", "#16A34A", 0.55), ("poly", "#DC2626", 0.7), ("li1", "#3B82F6", 0.35),
           ("met1", "#8B5CF6", 0.35), ("licon", "#111827", 0.9), ("mcon", "#111827", 0.9)]
  for layer, fill, op in style:
    for poly in L["layers"][layer]:
      b.append(el("path", None, d="M" + " L".join(f"{fmt(a)},{fmt(c)}" for a, c in (T(q) for q in poly)) + " Z", fill=fill, fill_opacity=op))
  for g in L["gates"]:
    b.append(el("path", None, d="M" + " L".join(f"{fmt(a)},{fmt(c)}" for a, c in (T(q) for q in g)) + " Z", fill="none", stroke="#FFFFFF", stroke_width=1.6))
  hh = (y1 - y0) * s_
  tx = 24 + rw + 20
  b.append(text(tx, y + 30, "one flip-flop", 15, INK, "700"))
  b.append(text(tx, y + 52, "real layout, open", 12, MUTED))
  b.append(text(tx, y + 68, "SkyWater 130 nm library", 12, MUTED))
  b.append(text(tx, y + 102, str(ntr), 34, SAFETY, "800"))
  b.append(text(tx + 50, y + 102, "transistors", 13, INK, "600"))
  b.append(text(tx, y + 122, "white outlines", 11, MUTED))
  y += max(hh, 130) + 24
  rf = by["Register file"]
  ct = S["cell_types"]
  y = tiles(b, y, [("register file", pct(rf["area_share"], 0), "of the core", f"{rf['flip_flops']:,} flip-flops", "#B45309"),
                   ("whole core", f"{S['area_um2'] / 1e6:.3f}", "mm² of cells", f"{S['cells']:,} cells", HW),
                   ("flip-flops", f"{S['flip_flops']:,}", "in the core", f"{ct.get('sky130_fd_sc_hd__edfxtp_1', 0):,} with an enable", SAFETY)])
  b.append(rect(24, y + 6, PW - 48, 128, fill=CHIP, stroke=LINE, sw=1, rx=12))
  b.append(text(44, y + 34, "Three kinds of silicon, three ways to split λ", 15, INK, "700"))
  for k, (n, how, c) in enumerate([("memory", "by bits, plus a soft-error rate per bit", "#7D68A3"),
                                   ("logic", "by gate count or cell area", SAFETY), ("analog", "by area, with its own failure modes", "#65A30D")]):
    yy = y + 62 + k * 26
    b.append(rect(44, yy - 12, 14, 14, fill=c, stroke="none", sw=0, rx=3))
    b.append(text(66, yy, n, 14, INK, "700"))
    b.append(text(140, yy, how, 14, INK))
  return finish(b, y + 134, "Big storage takes most of the λ, so cover it first.",
                [SRC + "cell area only, no wiring or clock tree.", f"Flip-flop layout: {L['cell']}, rendered from its GDS."],
                "Part 11 in one minute 2 · where the failure rate goes",
                f"PicoRV32 split by cell area, register file {pct(rf['area_share'])}; one sky130 flip-flop has {ntr} transistors.")


# ---------------------------------------------------------------- E3
def e3(C: dict, Hst: dict) -> str:
  need(C, "faults", "perm_dc", "seconds", "sub_parts")
  first = {r: v for r, v in Hst["runs"][0]["sub_parts"].items()}
  check_sub_parts(list(first), "coverage-history.json run 1")
  b, y = frame(3, ["How do you check that a", "CPU self-test really works?"], "break the CPU on purpose, thousands of times",
               ["synthesise", "break", "run", "compare", "score"], 1)
  b.append(rect(24, y, PW - 48, 250, fill=CHIP, stroke=LINE, sw=1, rx=14))
  b.append(text(44, y + 28, f"one of {C['faults']:,} faults, followed through (example values)", 14, INK, "700"))
  steps = [("gate output", ["stuck at 1"], RED, RED_BG), ("adder", ["7 + 5 =", "13"], RED, RED_BG),
           ("result stored", ["mem[...] =", "13"], AMBER, AMBER_BG), ("compare", ["expected 12"], SW, SW_BG), ("caught", ["detected"], GREEN, GREEN_BG)]
  bw = (PW - 88 - 4 * 14) / 5
  for k, (n, vals, fg, bg) in enumerate(steps):
    x = 44 + k * (bw + 14)
    b.append(rect(x, y + 50, bw, 110, fill=bg, stroke=fg, sw=1.5, rx=10))
    b.append(text(x + bw / 2, y + 84, n, 13, fg, "700", "middle"))
    for m, t in enumerate(vals):
      b.append(text(x + bw / 2, y + 112 + m * 18, t, 12, INK, "", "middle", family=MONO))
    if k < 4:
      b += arrow(x + bw + 1, y + 105, x + bw + 13, y + 105)
  for k, t in enumerate(["The test stores every result. A fault that changes any result, address", "or timing is visible; a compare plus a watchdog would catch it.",
                         "Thousands of faulty copies run side by side in one simulation."]):
    b.append(text(44, y + 192 + k * 20, t, 12, MUTED))
  y += 270
  y = tiles(b, y, [("faults simulated", f"{C['faults']:,}", "one per run", "cells × 2 + one flip per FF", HW),
                   ("found by the test", pct(C["perm_dc"]), "of stuck-at faults", f"run 1: {pct(Hst['runs'][0]['perm_dc'])}", GREEN),
                   ("campaign time", f"{C['seconds'] / 60:.1f}", "minutes", "4 CPUs", SAFETY)])
  cx = 190
  b.append(text(24, y + 14, "coverage per sub-part: first test (grey) and fixed test (colour)", 13, INK, "700"))
  bwid = PW - cx - 70
  cy = y + 34
  for p in (60, 90):
    xx = cx + bwid * p / 100
    b.append(line(xx, cy - 6, xx, cy + len(C["sub_parts"]) * 30, stroke=LINE, sw=1, dash="3 3"))
    b.append(text(xx, cy + len(C["sub_parts"]) * 30 + 16, f"{p} %", 11, MUTED, "", "middle"))
  for i, r in enumerate(C["sub_parts"]):
    yy = cy + i * 30
    d, o = r["perm_dc"], first[r["sub_part"]]
    c = GREEN if d >= 0.9 else AMBER if d >= 0.6 else RED
    b.append(text(cx - 10, yy + 15, name(r["sub_part"]), 13, INK, "600", "end"))
    b.append(rect(cx, yy + 2, bwid * o, 9, fill=GREY_BG, stroke=FAINT, sw=1, rx=2))
    b.append(rect(cx, yy + 12, bwid * d, 11, fill=c, stroke="none", sw=0, rx=2))
    b.append(text(cx + bwid * max(d, o) + 6, yy + 21, pct(d, 0), 12, c, "700", family=MONO))
  return finish(b, cy + len(C["sub_parts"]) * 30 + 20, "A self-test is graded by breaking the CPU, not by reading the code.",
                [SRC + "fault-free run checked against an ISA model.", "An open RISC-V core, not LionDriver's MCU: this shows the method."],
                "Part 11 in one minute 3 · grading a self-test",
                f"{C['faults']:,} faults simulated on PicoRV32; the self-test finds {pct(C['perm_dc'])} of stuck-at faults, up from "
                f"{pct(Hst['runs'][0]['perm_dc'])} in the first run.")


# ---------------------------------------------------------------- E4
def e4(C: dict) -> str:
  need(C, "seu_faults", "seu_detected", "seu_dc", "sub_parts")
  if abs(C["seu_detected"] / C["seu_faults"] - C["seu_dc"]) > 1e-3:
    raise FigureError("bit-flip counts and share disagree")
  b, y = frame(4, ["Why doesn't one flipped bit", "crash the CPU?"], "most flips land in a value that is overwritten", ["flip", "masked", "visible", "numbers", "fix"], 1)
  b.append(rect(24, y, PW - 48, 270, fill=CHIP, stroke=LINE, sw=1, rx=14))
  b.append(text(44, y + 28, "register file: 36 registers × 32 bits (example flips)", 14, INK, "700"))
  cw = (PW - 88) / 32
  for r in range(8):
    for k in range(32):
      hit = (r == 2 and k == 9) or (r == 5 and k == 20)
      c = (AMBER if r == 2 else RED) if hit else HW_BG
      b.append(rect(44 + k * cw + 1, y + 44 + r * 18, cw - 2, 14, fill=c, stroke=HW, sw=0.6, rx=2))
  for k, (t, c, w) in enumerate([("x3 bit 22 flips, then x3 is written again before anyone reads it", INK, "600"), ("→ masked: no effect", AMBER, "700"),
                                 ("x6 bit 11 flips and the next instruction reads x6", INK, "600"), ("→ visible: a wrong result", RED, "700")]):
    b.append(text(44, y + 204 + k * 19, t, 12, c, w))
  y += 290
  y = tiles(b, y, [("bit flips injected", f"{C['seu_faults']:,}", "one per flip-flop", "at a random cycle", HW),
                   ("changed a result", pct(C["seu_dc"], 0), "of flips", f"{C['seu_detected']:,} flips", RED),
                   ("vanished", pct(1 - C["seu_dc"], 0), "masked", "overwritten or unused", GREEN)])
  cx = 190
  b.append(text(24, y + 14, "flips that changed a result, per sub-part", 13, INK, "700"))
  bwid = PW - cx - 70
  rows = sorted(C["sub_parts"], key=lambda r: (-(r["seu_dc"] or 0), r["sub_part"]))
  cy = y + 34
  for i, r in enumerate(rows):
    d = r["seu_dc"] or 0
    yy = cy + i * 28
    b.append(text(cx - 10, yy + 14, name(r["sub_part"]), 13, INK, "600", "end"))
    b.append(rect(cx, yy + 3, bwid * d, 14, fill=RED if d > 0.5 else AMBER if d > 0.2 else FAINT, stroke="none", sw=0, rx=2))
    b.append(text(cx + bwid * d + 6, yy + 15, pct(d, 0), 12, MUTED, family=MONO))
  y = cy + len(rows) * 28 + 10
  b.append(rect(24, y, PW - 48, 96, fill=SAFETY_BG, stroke=SAFETY, sw=1, rx=12))
  b.append(text(44, y + 28, "A software test can't wait for a random flip.", 15, SAFETY, "700"))
  b.append(text(44, y + 52, "Transient faults need hardware that checks every access:", 13, INK))
  b.append(text(44, y + 72, "parity or ECC on registers and memory, or a lockstep second core.", 13, INK))
  return finish(b, y + 96, "Most flips vanish. The rest need hardware, not software.",
                [SRC + "one flip per flip-flop at a random cycle of our self-test.",
                 "'Changed a result' = visible on the memory bus during the test. Counters score high because the test reads them."],
                "Part 11 in one minute 4 · bit flips",
                f"{C['seu_faults']:,} single bit flips in PicoRV32; {pct(C['seu_dc'])} changed a result, the rest were masked.")


# ---------------------------------------------------------------- E5
SEG = [("wrong", "wrong result, unnoticed", RED), ("flagged", "flagged as an error", AMBER), ("corrected", "read, and corrected", GREEN),
       ("none", "no effect", "#CBD5E1")]


def e5(E: dict) -> str:
  for k in ("base_single", "ecc_single", "base_double", "ecc_double"):
    need(E, k)
    if sum(E[k][s] for s, _, _ in SEG) != E[k]["n"]:
      raise FigureError(f"ecc_summary {k}: classes do not add up to n")
  need(E, "area_um2")
  b, y = frame(5, ["What does ECC on the", "register file buy you?"], "the same bit flips, at the same cycles, in two CPUs", ["flip", "read", "check", "correct", "cost"], 3)
  b.append(rect(24, y, PW - 48, 250, fill=CHIP, stroke=LINE, sw=1, rx=14))
  b.append(text(44, y + 28, "one register, one flipped bit", 14, INK, "700"))

  def word(x, yy, n, chk, label):
    b.append(text(x, yy - 8, label, 12, MUTED))
    for k in range(n):
      check = k >= n - chk
      c, s = ("#EDE9FE", "#7C3AED") if check else (HW_BG, HW)
      if k == 9:
        c, s = RED, RED
      b.append(rect(x + k * 15, yy, 13, 22, fill=c, stroke=s, sw=0.8, rx=2))

  word(44, y + 62, 32, 0, "without ECC: 32 bits")
  b.append(text(44 + 32 * 15 + 10, y + 78, "→ read as is", 12, RED, "700"))
  word(44, y + 122, 39, 7, "with SECDED: 32 data bits + 7 check bits (purple)")
  b.append(text(44, y + 166, "On every read the check bits give a syndrome:", 12, INK))
  b.append(text(44, y + 184, "• one bit wrong → the syndrome names it → flipped back (corrected)", 12, GREEN, "600"))
  b.append(text(44, y + 202, "• two bits wrong → can't tell which → error flag raised (flagged)", 12, AMBER, "600"))
  b.append(text(44, y + 228, "No scrubbing: a bad word stays bad until it is written again.", 11, MUTED))
  y += 270
  bs, es, ed, bd = E["base_single"], E["ecc_single"], E["ecc_double"], E["base_double"]
  cost = E["area_um2"]["ecc"] / E["area_um2"]["base"] - 1
  y = tiles(b, y, [("single flips → wrong result", f"{bs['wrong'] / bs['n'] * 100:.1f}→{es['wrong'] / es['n'] * 100:.0f}", "percent",
                    f"{bs['wrong']} → {es['wrong']} of the flips", GREEN),
                   ("double flips flagged", pct(ed["flagged"] / ed["n"], 0), "with ECC", f"without ECC: {bd['flagged']}", AMBER),
                   ("area cost", f"+{cost * 100:.1f}", "percent", "of the whole core", SAFETY)])
  b.append(text(24, y + 14, "what happened to each flip", 13, INK, "700"))
  bx, bwid = 170, PW - 170 - 24
  for i, (lab, key) in enumerate([("no ECC · 1 bit", "base_single"), ("ECC · 1 bit", "ecc_single"), ("no ECC · 2 bits", "base_double"), ("ECC · 2 bits", "ecc_double")]):
    yy = y + 34 + i * 46
    d = E[key]
    b.append(text(bx - 10, yy + 20, lab, 13, INK, "600", "end"))
    b.append(text(bx - 10, yy + 36, f"{d['n']:,} flips", 11, MUTED, "", "end"))
    x = bx
    for k, _, c in SEG:
      w = bwid * d[k] / d["n"]
      if w > 0:
        b.append(rect(x, yy + 4, w, 30, fill=c, stroke="#FFFFFF", sw=1, rx=0))
        if w > 34:
          b.append(text(x + w / 2, yy + 24, pct(d[k] / d["n"], 0), 11, INK if c == "#CBD5E1" else "#FFFFFF", "700", "middle"))
      x += w
  ly = y + 34 + 4 * 46 + 6
  x = 24
  for _, n, c in SEG:
    b.append(rect(x, ly, 12, 12, fill=c, stroke="none", sw=0, rx=2))
    b.append(text(x + 17, ly + 11, n, 11, INK))
    x += 30 + len(n) * 6.0
  y = ly + 30
  b.append(rect(24, y, PW - 48, 92, fill=SAFETY_BG, stroke=SAFETY, sw=1, rx=12))
  b.append(text(44, y + 28, "In FMEDA terms", 15, SAFETY, "700"))
  b.append(text(44, y + 52, "Single flips in the register file move from 'residual' to 'covered'.", 13, INK))
  b.append(text(44, y + 72, "Double flips become 'detected': the error flag must lead to a safe state.", 13, INK))
  return finish(b, y + 92, "ECC turns silent wrong results into corrections or alarms.",
                ["PicoRV32 with our Hamming (39,32) SECDED register file (flow/gen_regs_ecc.py), synthesised with Yosys.",
                 f"Flips in x1 to x31 and q0 to q3, one random cycle each, during our self-test; {bd['n']} random double flips."],
                "Part 11 in one minute 5 · what ECC buys",
                f"Single register-file flips causing a wrong result: {bs['wrong']} of {bs['n']} without ECC, {es['wrong']} of {es['n']} "
                f"with SECDED; area +{cost * 100:.1f} %.")


# ---------------------------------------------------------------- E6
def e6(Ls: dict) -> str:
  need(Ls, "wrong_cmd", "caught_first", "lead_median", "seu_latency_median", "per_sub_part", "cc_glitches", "cc_wrong_cmd",
       "cc_delayed_caught", "cc_wrong_cmd_delayed_caught", "area_um2", "faults", "app_cycles")
  if Ls["caught_first"] != Ls["wrong_cmd"]:
    raise FigureError("lockstep did not catch every wrong command first: the headline no longer holds")
  check_sub_parts(list(Ls["per_sub_part"]), "lockstep_summary.json")
  b, y = frame(6, ["Why run two CPUs to do", "the work of one?"], "lockstep: same inputs, compare every output, every cycle", ["copy", "compare", "catch", "blind spot", "cost"], 2)
  b.append(rect(24, y, PW - 48, 250, fill=CHIP, stroke=LINE, sw=1, rx=14))
  b.append(text(44, y + 28, "a torque limiter running on two cores", 14, INK, "700"))
  b.append(rect(44, y + 92, 90, 50, fill="#FFFFFF", stroke=LINE, sw=1, rx=8))
  b.append(text(89, y + 114, "sensor", 12, INK, "600", "middle"))
  b.append(text(89, y + 130, "inputs", 12, INK, "600", "middle"))
  for cy_, lab, bad in ((y + 44, "core A", True), (y + 140, "core B", False)):
    b.append(rect(180, cy_, 150, 80, fill=RED_BG if bad else HW_BG, stroke=RED if bad else HW, sw=1.6, rx=10))
    b.append(text(255, cy_ + 32, lab, 15, RED if bad else HW, "700", "middle"))
    b.append(text(255, cy_ + 52, "PicoRV32", 12, MUTED, "", "middle"))
    if bad:
      b.append(text(255, cy_ + 70, "fault inside", 11, RED, "700", "middle"))
  b += arrow(136, y + 117, 178, y + 90) + arrow(136, y + 117, 178, y + 180)
  b.append(el("circle", None, cx=440, cy=fmt(y + 150), r=34, fill=SAFETY_BG, stroke=SAFETY, stroke_width=2))
  b.append(text(440, y + 147, "=?", 18, SAFETY, "800", "middle"))
  b.append(text(440, y + 166, "every cycle", 10, SAFETY, "", "middle"))
  b += arrow(332, y + 84, 408, y + 136) + arrow(332, y + 180, 408, y + 164) + arrow(476, y + 150, 540, y + 108) + arrow(476, y + 150, 540, y + 194)
  b.append(rect(544, y + 84, 128, 44, fill="#FFFFFF", stroke=LINE, sw=1, rx=8))
  b.append(text(608, y + 111, "command", 12, INK, "600", "middle"))
  b.append(rect(544, y + 172, 128, 44, fill=RED_BG, stroke=RED, sw=1, rx=8))
  b.append(text(608, y + 199, "stop: mismatch", 12, RED, "700", "middle"))
  b.append(text(44, y + 236, "In simulation core B is the fault-free copy; the comparator watches all core outputs.", 11, MUTED))
  y += 270
  ratio = Ls["area_um2"]["lockstep"] / Ls["area_um2"]["single"]
  y = tiles(b, y, [("wrong commands caught first", pct(Ls["caught_first"] / Ls["wrong_cmd"], 0), f"{Ls['caught_first']:,} of {Ls['wrong_cmd']:,} faults",
                    f"median {Ls['lead_median']:.0f} cycles before the write", GREEN),
                   ("a bit flip is caught", f"{Ls['seu_latency_median']:.0f}", "cycles, median", "after it happens, when seen", HW),
                   ("area cost", f"×{ratio:.2f}", "of one core", "two cores + comparator", SAFETY)])
  b.append(text(24, y + 14, "blind spot 1: logic the program never uses stays silent", 13, INK, "700"))
  b.append(text(24, y + 32, "stuck-at faults that reach an output during this application", 11, MUTED))
  bx, bwid = 190, PW - 190 - 70
  rows = sorted(Ls["per_sub_part"].items(), key=lambda kv: (-kv[1], kv[0]))
  for i, (g, d) in enumerate(rows):
    yy = y + 44 + i * 24
    c = GREEN if d >= 0.9 else AMBER if d >= 0.5 else RED
    b.append(text(bx - 10, yy + 13, name(g), 12, INK, "600", "end"))
    b.append(rect(bx, yy + 2, bwid * d, 14, fill=c, stroke="none", sw=0, rx=2))
    b.append(text(bx + bwid * d + 6, yy + 14, pct(d, 0), 11, MUTED, family=MONO))
  y += 44 + len(rows) * 24 + 8
  b.append(text(24, y + 6, "The limiter never divides, so a broken divider is invisible until the day it is used.", 12, INK))
  b.append(text(24, y + 24, "That is why a start-up self-test still runs on a lockstep core.", 12, INK, "600"))
  y += 46
  b.append(rect(24, y, PW - 48, 154, fill=SAFETY_BG, stroke=SAFETY, sw=1, rx=12))
  b.append(text(44, y + 26, "blind spot 2: one glitch that hits both cores the same way", 14, SAFETY, "700"))
  b.append(text(44, y + 50, f"Same flip-flop flipped in both cores at the same cycle ({Ls['cc_glitches']:,} glitches,", 12, INK))
  b.append(text(44, y + 68, f"{Ls['cc_wrong_cmd']} of them sent a wrong command): plain lockstep caught 0.", 12, INK, "700"))
  b.append(text(44, y + 90, f"Checker 2 cycles behind (delayed lockstep): caught {Ls['cc_delayed_caught']:,} glitches,", 12, INK))
  b.append(text(44, y + 108, f"including {Ls['cc_wrong_cmd_delayed_caught']} of the {Ls['cc_wrong_cmd']} wrong commands.", 12, AMBER, "700"))
  b.append(text(44, y + 130, "A value that doesn't change in those 2 cycles is corrupted the same way in", 12, INK))
  b.append(text(44, y + 146, "both cores. Real designs add physical separation and diverse clocking too.", 12, INK))
  return finish(b, y + 154, "Two cores catch what one can't see, except what hits both alike.",
                [f"PicoRV32; {Ls['faults']:,} faults in one core while a 64-sample torque limiter runs ({Ls['app_cycles']:,} cycles).",
                 "Lockstep area from synthesising two cores and a comparator (flow/lockstep_top.v)."],
                "Part 11 in one minute 6 · lockstep",
                f"Lockstep caught all {Ls['wrong_cmd']:,} faults that sent a wrong command, a median {Ls['lead_median']:.0f} cycles early; "
                f"area ×{ratio:.2f}; plain lockstep missed all {Ls['cc_wrong_cmd']} common-cause wrong commands, delayed lockstep caught "
                f"{Ls['cc_wrong_cmd_delayed_caught']}.")


def build() -> dict[str, str]:
  C, Hst = load("coverage.json"), load("coverage-history.json")
  return {NAMES["E1"]: e1(C), NAMES["E2"]: e2(load("subparts.json"), load("sky130_dfxtp_1.json")), NAMES["E3"]: e3(C, Hst),
          NAMES["E4"]: e4(C), NAMES["E5"]: e5(load("ecc_summary.json")), NAMES["E6"]: e6(load("lockstep_summary.json"))}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except FigureError as e:
    print(f"fig_md_explainers: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"method-demo/figures/{n} is stale; run fig_md_explainers.py", file=sys.stderr)
    if not stale:
      print(f"fig_md_explainers: {len(outputs)} figures current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote method-demo/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
