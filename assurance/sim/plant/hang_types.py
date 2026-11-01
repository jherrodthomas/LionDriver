#!/usr/bin/env python3
"""Hang types of the safety MCU (SIM-OI-3, WP-V-05 VS-FI-17): what each hang stops, when the IWDG resets, and what
the car does meanwhile, over the spread of the IWDG's LSI clock.

The firmware's fault-injection build (`panda/board/drivers/fault_injection.h`) hangs on request in five ways: the
main loop, the 8 Hz tick, the main loop with interrupts disabled, the 100 Hz safety task (after its IWDG feed), and
a second IWDG feed straight after the first. The plant runs each with the real panda safety code and its IWDG feed
(`drivers/hw_watchdog.h`); `panda_loop.HANGS` says where each one starts and what it stops. Every interrupt has the
same NVIC priority (`drivers/irq_priorities.h`), so a hang inside one stops them all. The impact record of the
watchdog (OI-2) still has to read the LSI's spread from the STM32H725 datasheet; until it has, the timing part sweeps
28-36 kHz around the nominal 32 kHz.

Two parts:
  - timing: the five hangs at 10 request phases (13 ms apart, so they cover the 10 ms safety task and the 125 ms
    tick) and five LSI frequencies, on a straight;
  - the car: the five hangs in F-05's place (110 km/h, settled in a curve inside the ODD), with the switch going to
    pass-through or stuck in intercept and the EPS releasing or holding (SIM-OI-1), at five request phases, with the
    nominal LSI.

It writes `../results/hang-types.md` and `../results/hang-types.svg`.

    python3 hang_types.py            # run 450 cases on every core, write both files
    python3 hang_types.py --check    # CI: fail if the committed files differ from a fresh run

Synthetic (DSR-12), no evidence credit: the EPS, the driver and the road are the plant's stated assumptions, and the
plant's clocks are 1 ms steps. The switch moves at the reset; the relay's drop-out time (TSR-706) is not modelled.
"""

from __future__ import annotations

import dataclasses
import multiprocessing as mp
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
sys.path.insert(0, str(HERE))

import cases  # noqa: E402
import simulate  # noqa: E402
from panda_loop import HANGS, LSI_HZ  # noqa: E402

OUT_MD = SIM / "results" / "hang-types.md"
OUT_SVG = SIM / "results" / "hang-types.svg"

KINDS = [  # (panda_loop.HANGS key, label, fault_injection.h mode)
  ("main_loop", "Main loop hangs", 1),
  ("tick", "8 Hz tick hangs", 2),
  ("irq_off", "Interrupts off, main loop hangs", 3),
  ("safety_task", "Safety task hangs", 4),
  ("early_feed", "Feed too early", 5),
]
SHORT = {"main_loop": "the main-loop hang", "tick": "the tick hang", "irq_off": "interrupts off",
         "safety_task": "the safety-task hang"}
STOPS_ALL = {"tick", "irq_off", "safety_task"}   # a hang inside an interrupt, or with interrupts off
LSI_KHZ = [28.0, 30.0, 32.0, 34.0, 36.0]
TIMING_PHASES = [i * 0.013 for i in range(10)]   # s; 13 ms apart: every residue of the 10 ms task, 0-117 ms of the tick
CAR_PHASES = [i * 0.026 for i in range(5)]       # s; residues 0, 6, 2, 8, 4 ms of the task, 0-104 ms of the tick
T_TIMING, D_TIMING = 3.0, 0.35
D_CAR = 6.0   # as F-05: the driver's correction after a late cue still falls inside the run
TSR_501 = 0.1   # s, reset within this of a stall
assert set(k for k, _, _ in KINDS) == set(HANGS)


def _run(job: tuple) -> dict:
  part, kind, lsi_khz, phase, switch, eps = job
  if part == "timing":
    case = simulate.Case("SIM-OI-3", "hang", "hang_" + kind, "straight", "SG-07", "", t_fault=T_TIMING + phase,
                         duration=D_TIMING, lsi_hz=lsi_khz * 1000.0)
  else:
    f05 = f05_case()
    case = dataclasses.replace(f05, id="SIM-OI-3", fault="hang_" + kind, eps=eps, t_fault=f05.t_fault + phase,
                               duration=D_CAR, stuck_intercept=switch == "intercept")
  r = simulate.simulate(case)
  m, ev = r.metrics, r.metrics["events"]
  first = lambda p: next((t for k, t in ev.items() if k.startswith(p)), None)  # noqa: E731
  hang, reset = first("hang starts"), first("IWDG counter at zero")
  out = {"part": part, "kind": kind, "lsi": lsi_khz, "phase": phase, "switch": switch, "eps": eps,
         "hang": hang, "reset": reset}
  if part == "car":
    out.update({"frames_stop": hang if kind in STOPS_ALL else reset, "cue": first("driver cue"),
                "cue_kind": next((k[len("driver cue ("):-1] for k in ev if k.startswith("driver cue")), None),
                "corr": first("driver correction"), "t_line": m["t_line"], "t_narrow": m["t_narrow"],
                "max_dev": abs(m["max_dev"])})
  return out


def f05_case() -> simulate.Case:
  return {c.id: c for c in cases.all_cases()}["F-05"]


def jobs() -> list[tuple]:
  out = [("timing", k, f, p, "pass", "release") for k, _, _ in KINDS for f in LSI_KHZ for p in TIMING_PHASES]
  out += [("car", k, LSI_HZ / 1000.0, p, s, e) for k, _, _ in KINDS for s in ("pass", "intercept")
          for e in ("release", "hold") for p in CAR_PHASES]
  return out


def runs(n_jobs: int | None = None) -> list[dict]:
  js = jobs()
  n = n_jobs or os.cpu_count() or 1
  if n == 1:
    return [_run(j) for j in js]
  with mp.get_context("fork").Pool(n) as pool:
    return pool.map(_run, js, chunksize=4)


def ms(vals) -> str:
  vals = [round(v * 1000) for v in vals]
  lo, hi = min(vals), max(vals)
  return f"{lo} ms" if lo == hi else f"{lo}–{hi} ms"


def span(vals, unit=" s"):
  if all(v is None for v in vals):
    return "—"
  if any(v is None for v in vals):
    return "partly"
  lo, hi = f"{min(vals):.2f}", f"{max(vals):.2f}"
  return f"{lo}{unit}" if lo == hi else f"{lo}–{hi}{unit}"


def worst_after_hang(rs, kind, lsi) -> float:
  return max(r["reset"] - r["hang"] for r in rs if r["part"] == "timing" and r["kind"] == kind and r["lsi"] == lsi)


def lsi_limit(rs, kind) -> float | None:
  """Lowest swept LSI (kHz) at which every phase resets within TSR-501 of the hang; None if none does."""
  ok = [f for f in LSI_KHZ if worst_after_hang(rs, kind, f) <= TSR_501 + 1e-9]
  return min(ok) if ok else None


def table(rs: list[dict]) -> str:
  timing = [r for r in rs if r["part"] == "timing"]
  car = [r for r in rs if r["part"] == "car"]
  nom = LSI_HZ / 1000.0
  lines = [
    "# Hang types of the safety MCU: reset time and what the car does",
    "",
    "> **Synthetic data (DSR-12).** Generated by [`plant/hang_types.py`](../plant/hang_types.py); do not edit by hand. "
    "The real panda safety code of the reference build runs in the loop with its IWDG feed (`drivers/hw_watchdog.h`); "
    "the five hangs are those of the firmware's fault-injection build (`drivers/fault_injection.h`, WP-V-05 VS-FI-17), "
    "placed as `panda_loop.HANGS` says. The IWDG counter is modelled from the registers the firmware writes. EPS, "
    "driver and road are the plant's stated assumptions ([plant-results.md](plant-results.md)). **No evidence "
    "credit** (DQ-139). Closes SIM-OI-3.",
    "",
    "![Reset time after the hang starts against the LSI frequency, one band per hang type, with the TSR-501 limit of "
    "0.1 s](hang-types.svg)",
    "",
    "## 1. What each hang stops, and when the IWDG resets",
    "",
    f"The request comes at {len(TIMING_PHASES)} phases 13 ms apart, against the 10 ms safety task and the 125 ms tick. "
    "Times run from the request, or from the moment the hang starts; the reset is when the IWDG counter reaches zero. "
    f"Every interrupt has the same priority, so a hang inside one stops them all. LSI {nom:g} kHz (nominal).",
    "",
    "| Injected fault (fault_injection.h mode) | What stops | Hang starts after the request | "
    "Reset after the hang starts | Reset after the request |",
    "|---|---|---|---|---|",
  ]
  stops = {"main_loop": "the main loop only: the safety task, CAN, the host link and the tick run on",
           "tick": "everything", "irq_off": "everything", "safety_task": "everything",
           "early_feed": "nothing: the second feed resets at once"}
  for k, label, mode in KINDS:
    g = [r for r in timing if r["kind"] == k and r["lsi"] == nom]
    lines.append(f"| {label} ({mode}) | {stops[k]} | {ms([r['hang'] for r in g])} | "
                 f"{ms([r['reset'] - r['hang'] for r in g])} | {ms([r['reset'] for r in g])} |")
  lines += [
    "",
    "## 2. The LSI clock's spread",
    "",
    "Worst case over the request phases of the reset after the hang starts, per LSI frequency. TSR-501 asks for a "
    f"reset within {TSR_501 * 1000:.0f} ms of a stall. The STM32H725 datasheet's LSI range is not yet read (watchdog "
    "impact record OI-2, WP-S-04 M-14).",
    "",
    "| Injected fault | " + " | ".join(f"{f:g} kHz" for f in LSI_KHZ) + " |",
    "|---|" + "---|" * len(LSI_KHZ),
  ]
  for k, label, _ in KINDS:
    cells = []
    for f in LSI_KHZ:
      w = worst_after_hang(rs, k, f)
      cells.append(f"{w * 1000:.0f} ms" + (" **over**" if w > TSR_501 + 1e-9 else ""))
    lines.append(f"| {label} | " + " | ".join(cells) + " |")
  lines += [
    "",
    f"## 3. The car: in a curve at {f05_case().speed_kph:.0f} km/h",
    "",
    f"The request comes where F-05 injects its hang ({f05_case().t_fault:g} s, settled in a curve inside the ODD, "
    f"1.5 m/s²), at {len(CAR_PHASES)} phases 26 ms apart; LSI {nom:g} kHz. Times are seconds from the request. The item's frames stop when the hang starts (a hang that stops everything) "
    "or at the reset (main loop, early feed). After the reset the switch goes to pass-through, and the stock camera "
    "path is back, or it stays in intercept and nothing reaches the car. The driver reacts 1.5 s after the first cue; "
    "no hang sounds the siren.",
    "",
    "| Injected fault | Switch after the reset | EPS | Item's frames stop | Reset | Driver cue | Correction starts | "
    "Body on the lane line, 3.0 / 3.7 m lane | Peak drift |",
    "|---|---|---|---|---|---|---|---|---|",
  ]
  for k, label, _ in KINDS:
    for sw in ("pass", "intercept"):
      for eps in ("release", "hold"):
        g = [r for r in car if r["kind"] == k and r["switch"] == sw and r["eps"] == eps]
        kinds = sorted({r["cue_kind"] for r in g if r["cue_kind"]})
        cue = f"{' / '.join(kinds)} at {span([r['cue'] for r in g])}" if kinds else "—"
        lines.append(f"| {label} | {'pass-through' if sw == 'pass' else 'stuck in intercept'} | {eps} | "
                     f"{span([r['frames_stop'] for r in g])} | {span([r['reset'] for r in g])} | {cue} | "
                     f"{span([r['corr'] for r in g])} | {span([r['t_narrow'] for r in g])} / "
                     f"{span([r['t_line'] for r in g])} | {span([r['max_dev'] for r in g], ' m')} |")
  ml = [r for r in timing if r["kind"] == "main_loop" and r["lsi"] == nom]
  others = [r["reset"] - r["hang"] for r in timing if r["kind"] in STOPS_ALL and r["lsi"] == nom]
  lim = {k: lsi_limit(rs, k) for k, _, _ in KINDS if k != "early_feed"}
  line_t = lambda k: [r["t_line"] for r in car  # noqa: E731
                      if r["kind"] == k and r["switch"] == "pass" and r["eps"] == "release"]
  lines += [
    "",
    "**What this shows** (generated from the rows above):",
    "",
    f"- A main-loop hang resets {ms([r['reset'] - r['hang'] for r in ml])} after it starts, not the timeout alone: "
    "the main loop sets its flag just before it spins, so the next safety task still feeds the IWDG once. The hangs "
    f"that stop everything reset {ms(others)} after they start. The watchdog impact record's D-1 (\"detection time is "
    "the timeout only\") holds for those, not for the main loop.",
    "- During a main-loop hang the panda still runs its safety task and its CAN and host interrupts, so the item's "
    "frames keep passing its checks until the reset. That buys little: with the switch going to pass-through and the "
    f"EPS releasing, the body reaches the lane line at {span(line_t('main_loop'))} against "
    f"{span(line_t('irq_off'))} for interrupts off (today's F-05).",
    "- With the LSI swept: " + "; ".join(
      f"{SHORT[k]} stays within {TSR_501 * 1000:.0f} ms down to {lim[k]:g} kHz" if lim[k] is not None else
      f"{SHORT[k]} is over {TSR_501 * 1000:.0f} ms at every swept frequency"
      for k, label, _ in KINDS if k != "early_feed") +
    ". Below the nominal 32 kHz the main-loop hang has no margin; the datasheet's range (OI-2) decides whether it meets "
    "TSR-501.",
    f"- A second feed straight after the first resets {ms([r['reset'] - r['hang'] for r in timing if r['kind'] == 'early_feed'])} "
    "after it at every LSI swept: the window (HWSR-501b) catches a safety task that runs too fast.",
    "- With the switch stuck in intercept nothing reaches the car after the reset in any hang; the drift then runs "
    "until the driver corrects, as in F-05's stuck-intercept case.",
  ]
  return "\n".join(lines) + "\n"


def figure(rs: list[dict]) -> str:
  W, H = 760, 385
  x0, x1, y0, y1 = 70, 520, 40, 330
  fmin, fmax, tmin, tmax = 27.0, 37.0, 0.07, 0.125

  def X(f):
    return x0 + (f - fmin) / (fmax - fmin) * (x1 - x0)

  def Y(t):
    return y1 - (t - tmin) / (tmax - tmin) * (y1 - y0)

  cols = {"main_loop": "var(--a)", "tick": "var(--b)", "irq_off": "var(--c)", "safety_task": "var(--d)"}
  out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
         'aria-labelledby="t">',
         "<style>svg{--ink:#0b0b0b;--muted:#52514e;--line:#e3e2de;--bad:#e34948;--bg:#ffffff;--a:#2a78d6;--b:#eb6834;"
         "--c:#6250d6;--d:#1baf7a;font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif}"
         "@media (prefers-color-scheme: dark){svg{--ink:#f0efec;--muted:#c3c2b7;--line:#33322f;--bad:#e66767;"
         "--bg:#1a1a19;--a:#3987e5;--b:#f07d4f;--c:#7d6fe3;--d:#3cc08e}}"
         ".s-ink{fill:var(--ink)} .s-muted{fill:var(--muted)} .s-bad{fill:var(--bad)}</style>",
         f'<rect width="{W}" height="{H}" style="fill:var(--bg)"/>',
         '<title id="t">Reset time after the hang starts against the LSI frequency, worst and best over the request '
         'phases, per hang type, with the TSR-501 limit of 100 ms</title>',
         '<text x="4" y="14" class="s-muted" font-size="12" font-weight="600" letter-spacing=".06em">'
         'IWDG RESET AFTER THE HANG STARTS · SYNTHETIC, NO EVIDENCE CREDIT</text>']
  t = 0.07
  while t <= tmax + 1e-9:
    out.append(f'<line x1="{x0}" y1="{Y(t):.1f}" x2="{x1}" y2="{Y(t):.1f}" stroke="var(--line)" stroke-width="1"/>')
    out.append(f'<text x="{x0 - 8}" y="{Y(t) + 4:.1f}" text-anchor="end" class="s-muted" font-size="11">'
               f'{t * 1000:.0f}</text>')
    t += 0.01
  for f in LSI_KHZ:
    out.append(f'<text x="{X(f):.1f}" y="{y1 + 18}" text-anchor="middle" class="s-muted" font-size="11">{f:g}</text>')
  out.append(f'<text x="{(x0 + x1) / 2:.0f}" y="{y1 + 38}" text-anchor="middle" class="s-muted" font-size="11">'
             'LSI frequency (kHz); nominal 32, datasheet range not yet read (OI-2)</text>')
  out.append(f'<text x="{x0 - 8}" y="{y0 - 12}" text-anchor="end" class="s-muted" font-size="11">ms</text>')
  out.append(f'<line x1="{x0}" y1="{Y(TSR_501):.1f}" x2="{x1}" y2="{Y(TSR_501):.1f}" stroke="var(--bad)" '
             'stroke-width="1.5" stroke-dasharray="5 4"/>')
  out.append(f'<text x="{x1 - 4}" y="{Y(TSR_501) - 6:.1f}" text-anchor="end" class="s-bad" font-size="11">'
             'TSR-501: reset within 100 ms</text>')
  offs = {"main_loop": -0.45, "tick": -0.15, "irq_off": 0.15, "safety_task": 0.45}
  for k, label, _ in KINDS:
    if k not in cols:
      continue
    for f in LSI_KHZ:
      g = [r["reset"] - r["hang"] for r in rs if r["part"] == "timing" and r["kind"] == k and r["lsi"] == f]
      x = X(f + offs[k])
      out.append(f'<line x1="{x:.1f}" y1="{Y(min(g)):.1f}" x2="{x:.1f}" y2="{Y(max(g)):.1f}" stroke="{cols[k]}" '
                 'stroke-width="6" stroke-linecap="round"/>')
  ly = y0 + 10
  for i, (k, label, _) in enumerate(KINDS[:4]):
    out.append(f'<line x1="{x1 + 30}" y1="{ly + 22 * i}" x2="{x1 + 52}" y2="{ly + 22 * i}" stroke="{cols[k]}" '
               'stroke-width="6" stroke-linecap="round"/>')
    out.append(f'<text x="{x1 + 60}" y="{ly + 22 * i + 4}" class="s-ink" font-size="12">'
               f'{SHORT[k][0].upper() + SHORT[k][1:]}</text>')
  out.append(f'<text x="{x1 + 30}" y="{ly + 100}" class="s-muted" font-size="11">Bars: best to worst over</text>')
  out.append(f'<text x="{x1 + 30}" y="{ly + 115}" class="s-muted" font-size="11">10 request phases. A</text>')
  out.append(f'<text x="{x1 + 30}" y="{ly + 130}" class="s-muted" font-size="11">second early feed resets</text>')
  out.append(f'<text x="{x1 + 30}" y="{ly + 145}" class="s-muted" font-size="11">at once (not drawn).</text>')
  out.append("</svg>")
  return "\n".join(out) + "\n"


def build(n_jobs: int | None = None) -> dict[Path, str]:
  rs = runs(n_jobs)
  return {OUT_MD: table(rs), OUT_SVG: figure(rs)}


def main(argv: list[str]) -> int:
  n = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else None
  out = build(n)
  if "--check" in argv:
    stale = [p for p, c in out.items() if not p.exists() or p.read_text(encoding="utf-8") != c]
    for p in stale:
      print(f"stale: {p.relative_to(SIM.parent)}", file=sys.stderr)
    if not stale:
      print(f"hang_types: {len(out)} file(s) current")
    return 1 if stale else 0
  for p, c in out.items():
    p.write_text(c, encoding="utf-8")
  print(f"wrote {len(out)} file(s)")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
