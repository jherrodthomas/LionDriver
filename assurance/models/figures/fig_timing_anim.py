#!/usr/bin/env python3
"""Draw the animated FTTI timing-loop figure from the Octave timing-loop model (`../octave/timing_loop_model.m`).

  fig-md-3-ftti-loops-anim.svg   one looping timeline per fault class: normal operation, the fault, the detection
                                 time (FDTI) growing tick by tick against the 100 Hz safety task and the 8 Hz speaker
                                 tick, the reaction (FRTI budget), the safe state and the warning, against the FTTI

The numbers come from `../octave/timing_loop_results.csv`, which the Octave model writes and CI keeps current
(`run_models.m` fails when it is stale). The worst case over all loop phases is drawn. SMIL animation, no script.
The reaction after detection is the WP-S-04 §3.7 FRTI budget: the EPS and PCM response is not modelled (M-02).
A model of the code, not a measurement (WP-S-04 §6).

    python3 fig_timing_anim.py            # write the SVG next to this script
    python3 fig_timing_anim.py --check    # fail if the SVG is stale

Standard library only. Output is deterministic.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
CSV = HERE.parent / "octave" / "timing_loop_results.csv"
OUT = "fig-md-3-ftti-loops-anim.svg"

# the rows drawn, in order: within the FTTI, FTTI exceeded (original baseline), and the reference-build paths
ROWS = ["rx-1d2-ref", "rx-260-base", "hb-ref", "stall-ref", "iwdg-slow", "eps-ref"]
TASK_S, TICK_S = 0.010, 0.125   # 100 Hz safety task, 8 Hz tick (speaker on every other tick); see ld_timing_constants.m

W, X0, X1 = 1280, 380, 1060     # timeline from X0 (t = 0) to X1 (t = row scale)
ROW_H, TOP = 156, 108
DUR, SWEEP = 9.0, 0.72          # loop length (s) and the share of it the time cursor sweeps
FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
INK, MUTED, HAIR = "#0F172A", "#475569", "#E2E8F0"
GREEN, YELLOW, ORANGE, RED, BLUE, AMBER = "#22A06B", "#F5B700", "#E8761B", "#D2453A", "#2F80ED", "#B7791F"


def fmt(v: float) -> str:
  return f"{v:.2f}".rstrip("0").rstrip(".")


def ms(v: float) -> str:
  return f"{v * 1000:.0f} ms" if v < 0.995 else f"{v:.2f} s"


def text(x, y, s, size=12, fill=INK, weight=None, anchor=None, extra=""):
  a = f' font-size="{size}" fill="{fill}"'
  a += f' font-weight="{weight}"' if weight else ""
  a += f' text-anchor="{anchor}"' if anchor else ""
  return f'<text x="{fmt(x)}" y="{fmt(y)}"{a}{extra}>{escape(s)}</text>'


def load() -> dict[str, dict]:
  with CSV.open(encoding="utf-8", newline="") as f:
    rows = {r["id"]: r for r in csv.DictReader(f)}
  for r in rows.values():
    for k in ("ftti_s", "fdti_budget_s", "frti_budget_s", "fdti_max_s", "fhti_max_s"):
      r[k] = float(r[k])
    for k in ("warn_budget_s", "warn_max_s"):
      r[k] = float(r[k]) if r[k] else None
  missing = [i for i in ROWS if i not in rows]
  if missing:
    raise SystemExit(f"rows not in {CSV.name}: {missing}")
  return rows


def verdict(r: dict) -> tuple[str, str]:
  if r["ftti_ok"] != "1":
    return f"FTTI exceeded: safe state at {ms(r['fhti_max_s'])}, FTTI {ms(r['ftti_s'])}", RED
  if r["warn_ok"] == "0":
    return f"warning late: {ms(r['warn_max_s'])} > {ms(r['warn_budget_s'])}", RED
  if r["fdti_ok"] != "1":
    over = r["fdti_max_s"] - r["fdti_budget_s"]
    return f"safe state within FTTI · FDTI {ms(over)} over its {ms(r['fdti_budget_s'])} budget", AMBER
  return "safe state within FTTI" + (" · siren within its budget" if r["warn_ok"] == "1" else ""), GREEN


def at(t: float, scale: float) -> float:
  """Animation key time (0..1) at which the cursor reaches time t of a row."""
  return round(SWEEP * min(t, scale) / scale, 4)


def appear(k: float, extra_attr="opacity") -> str:
  """Hidden until key time k, then shown until the loop restarts."""
  k = min(max(k, 0.001), 0.998)
  return (f'<animate attributeName="{extra_attr}" values="0;0;1;1" keyTimes="0;{k};{min(k + 0.001, 0.999)};1" '
          f'dur="{DUR}s" repeatCount="indefinite"/>')


def grow(x0: float, w: float, k0: float, k1: float) -> str:
  """Width grows from 0 at key time k0 to w at k1."""
  k0 = min(max(k0, 0.0), 0.997)
  k1 = min(max(k1, k0 + 0.001), 0.998)
  if k0 == 0:  # grows from the start of the loop
    return (f'<animate attributeName="width" values="0;{fmt(w)};{fmt(w)}" keyTimes="0;{k1};1" '
            f'dur="{DUR}s" repeatCount="indefinite"/>')
  return (f'<animate attributeName="width" values="0;0;{fmt(w)};{fmt(w)}" keyTimes="0;{k0};{k1};1" '
          f'dur="{DUR}s" repeatCount="indefinite"/>')


def row_svg(r: dict, y: float) -> list[str]:
  o: list[str] = []
  warn = r["warn_max_s"]
  end = max(r["ftti_s"], r["fhti_max_s"], warn or 0)
  scale = end * 1.18
  X = lambda t: X0 + (X1 - X0) * min(t, scale) / scale  # noqa: E731
  by = y + 34          # bar top
  bh = 16
  fd, fh, ft = r["fdti_max_s"], r["fhti_max_s"], r["ftti_s"]
  if fd == 0:  # refused on receipt of the first fault frame: the safe state is immediate, the warning is what is timed
    fh = 0.0
  build = "original baseline 8b8c6ae" if r["build"].startswith("baseline") else "reference build"

  # label column
  o.append(text(40, y + 30, r["label"].replace(", baseline", ""), 14, INK, 700))
  o.append(text(40, y + 48, f'{r["sg"]} · {build}', 11.5, MUTED))
  o.append(text(40, y + 64, f'FDTI ≤ {ms(fd)} (budget {ms(r["fdti_budget_s"])})', 11.5, MUTED))
  if warn is not None:
    o.append(text(40, y + 80, f'warning ≤ {ms(warn)} (budget {ms(r["warn_budget_s"])})', 11.5, MUTED))

  # normal operation before the fault, then the bars that grow with the cursor
  o.append(f'<rect x="{X0 - 70}" y="{by}" width="68" height="{bh}" rx="3" fill="{GREEN}"/>')
  o.append(text(X0 - 36, by + bh + 14, "normal", 10.5, MUTED, anchor="middle"))
  if fd > 0:
    o.append(f'<rect x="{fmt(X0)}" y="{by}" width="0" height="{bh}" rx="3" fill="{YELLOW}">{grow(X0, X(fd) - X0, 0, at(fd, scale))}</rect>')
  if fh > fd:
    o.append(f'<rect x="{fmt(X(fd))}" y="{by}" width="0" height="{bh}" rx="3" fill="{ORANGE}">'
             f'{grow(X(fd), X(fh) - X(fd), at(fd, scale), at(fh, scale))}</rect>')
  o.append(f'<rect x="{fmt(X(fh))}" y="{by}" width="0" height="{bh}" rx="3" fill="{GREEN}">'
           f'{grow(X(fh), max(X1 + 30 - X(fh), 0), at(fh, scale), SWEEP + 0.02)}</rect>')

  # fault: lightning bolt at t = 0
  bx = X0
  o.append(f'<path d="M{fmt(bx + 2)} {fmt(by - 30)}l-9 15h7l-6 13 14-17h-7l6-11z" fill="{RED}"/>')
  o.append(text(bx + 12, by - 18, "fault", 11, RED, 700))
  o.append(f'<line x1="{fmt(bx)}" y1="{fmt(by - 4)}" x2="{fmt(bx)}" y2="{fmt(by + bh + 34)}" stroke="{INK}" stroke-dasharray="2 3"/>')

  # detection marker, phase labels
  if fd > 0:
    o.append(f'<g opacity="0">{appear(at(fd, scale))}'
             f'<line x1="{fmt(X(fd))}" y1="{fmt(by - 8)}" x2="{fmt(X(fd))}" y2="{fmt(by + bh + 8)}" stroke="{INK}" stroke-width="2"/>'
             f'{text(X(fd) + 4, by - 10, "fault detected", 11, INK, 600)}</g>')
    if X(fd) - X0 > 90:
      o.append(text((X0 + X(fd)) / 2, by + bh + 14, "FDTI (detection)", 10.5, AMBER, 600, "middle"))
  if X(fh) - X(fd) > 70:
    o.append(text((X(fd) + X(fh)) / 2, by + bh + 14, "FRTI budget", 10.5, ORANGE, 600, "middle"))
  safe = "safe state" if fh > 0 else "safe state: LKA refused on the first fault frame"
  o.append(f'<g opacity="0">{appear(at(fh, scale))}{text(min(X(fh) + 6, X1 - 10), by + 12, safe, 11, "#FFFFFF", 700)}</g>')

  # the loops: 100 Hz safety-task runs and 8 Hz ticks (speaker on odd ticks) under the bar
  ly = by + bh + 22
  task_step = TASK_S if scale <= 1.5 else TICK_S  # thin out the 100 Hz marks on long rows
  n = int(scale / task_step)
  marks = "".join(f'M{fmt(X(i * task_step))} {fmt(ly)}v4' for i in range(1, n + 1))
  o.append(f'<path d="{marks}" stroke="#94A3B8" stroke-width="1"/>')
  ticks = "".join(f'M{fmt(X(i * TICK_S))} {fmt(ly + 6)}v{8 if i % 2 else 5}' for i in range(1, int(scale / TICK_S) + 1))
  o.append(f'<path d="{ticks}" stroke="{BLUE}" stroke-width="1.6"/>')
  o.append(text(X1 + 8, ly + 5, "100 Hz task" if task_step == TASK_S else "task (thinned)", 9.5, MUTED))
  o.append(text(X1 + 8, ly + 15, "8 Hz tick · tall = speaker", 9.5, BLUE))
  if fd > 0:  # the task run that detects flashes
    o.append(f'<circle cx="{fmt(X(fd))}" cy="{fmt(ly + 2)}" r="0" fill="none" stroke="{INK}" stroke-width="1.6">'
             f'<animate attributeName="r" values="0;0;9;0;0" keyTimes="0;{at(fd, scale)};{min(at(fd, scale) + 0.03, 0.99)};'
             f'{min(at(fd, scale) + 0.06, 0.995)};1" dur="{DUR}s" repeatCount="indefinite"/></circle>')

  # warning (siren) on the speaker tick
  if warn is not None:
    wx = X(warn)
    o.append(f'<g opacity="0">{appear(at(warn, scale))}'
             f'<path d="M{fmt(wx - 7)} {fmt(by - 34)}h5l7-6v20l-7-6h-5z" fill="{RED}"/>'
             f'<path d="M{fmt(wx + 8)} {fmt(by - 31)}q4 4 0 8" stroke="{RED}" fill="none" stroke-width="1.6"/>'
             f'{text(wx + 14, by - 22, f"siren {ms(warn)}", 11, RED, 700)}'
             f'<line x1="{fmt(wx)}" y1="{fmt(by - 16)}" x2="{fmt(wx)}" y2="{fmt(ly + 14)}" stroke="{RED}" stroke-dasharray="3 2"/></g>')

  # FTTI: blue double arrow from the fault, under the loops
  ay = ly + 30
  o.append(f'<line x1="{fmt(X0 + 2)}" y1="{fmt(ay)}" x2="{fmt(X(ft) - 2)}" y2="{fmt(ay)}" stroke="{BLUE}" stroke-width="3" '
           f'marker-start="url(#ab)" marker-end="url(#ab)"/>')
  o.append(f'<line x1="{fmt(X(ft))}" y1="{fmt(by - 6)}" x2="{fmt(X(ft))}" y2="{fmt(ay + 4)}" stroke="{BLUE}" stroke-dasharray="2 3"/>')
  o.append(text((X0 + X(ft)) / 2, ay + 15, f"FTTI {ms(ft)}", 11.5, BLUE, 700, "middle"))

  # verdict bubble when the cursor reaches the end
  msg, col = verdict(r)
  bw = 9 + 6.4 * len(msg)
  vx, vy = min(max(X(end) - bw / 2, X0), X1 - bw), ay + 22
  o.append(f'<g opacity="0">{appear(SWEEP + 0.01)}'
           f'<rect x="{fmt(vx)}" y="{fmt(vy)}" width="{fmt(bw)}" height="22" rx="11" fill="{col}"/>'
           f'{text(vx + bw / 2, vy + 15, msg, 11.5, "#FFFFFF", 700, "middle")}</g>')

  # time cursor
  o.append(f'<line x1="{X0}" y1="{fmt(by - 10)}" x2="{X0}" y2="{fmt(ly + 16)}" stroke="{INK}" stroke-width="1.2" opacity=".55">'
           f'<animateTransform attributeName="transform" type="translate" values="0 0;{fmt(X1 - X0)} 0;{fmt(X1 - X0)} 0" '
           f'keyTimes="0;{SWEEP};1" dur="{DUR}s" repeatCount="indefinite"/></line>')
  o.append(text(X1 + 8, ay + 4, f"axis 0 – {fmt(scale)} s", 9.5, MUTED))
  o.append(f'<line x1="40" y1="{fmt(y + ROW_H - 4)}" x2="{W - 40}" y2="{fmt(y + ROW_H - 4)}" stroke="{HAIR}"/>')
  return o


def figure() -> str:
  rows = load()
  H = TOP + ROW_H * len(ROWS) + 92
  o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}" role="img" aria-labelledby="t d">',
       '<title id="t">FTTI timing loops, animated: detection and reaction against the fault tolerant time interval</title>',
       '<desc id="d">One looping timeline per fault class, from the Octave timing-loop model of the panda code. Each starts in '
       'normal operation; a fault occurs at t = 0; the detection time grows against the 100 Hz safety-task runs and the 8 Hz '
       'ticks until the task run that detects the fault flashes; the reaction (the WP-S-04 §3.7 FRTI budget) follows and the '
       'safe state is reached; a siren is shown where the path warns the driver, on an odd 8 Hz tick. A blue arrow marks the '
       'FTTI. Rows: RX loss in the reference build, within the FTTI; the same fault in the original baseline, which exceeds '
       'the FTTI; SoC heartbeat loss; SoC command stall, 10 ms over its detection budget but within the FTTI; MCU hang with '
       'a 10 % slow watchdog clock, exactly at its budget; and the EPS-fault warning. Worst case over all loop phases. '
       'A model of the code, not a measurement.</desc>',
       f'<defs><marker id="ab" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
       f'<path d="M0 0L10 5L0 10z" fill="{BLUE}"/></marker></defs>',
       f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
       text(40, 44, "FTTI timing loops · worst case over every loop phase", 21, INK, 700),
       text(40, 68, "Octave model of the panda loops (octave/timing_loop_results.csv) · reaction = §3.7 FRTI budget, "
            "EPS response not modelled (M-02) · not a measurement (WP-S-04 §6)", 12, MUTED),
       text(W - 40, 44, "WP-S-04 §3.7, §4", 11, MUTED, anchor="end"),
       f'<line x1="40" y1="84" x2="{W - 40}" y2="84" stroke="{HAIR}"/>']
  for i, rid in enumerate(ROWS):
    o += row_svg(rows[rid], TOP + i * ROW_H)
  ly = TOP + ROW_H * len(ROWS) + 22
  legend = [(GREEN, "normal operation / safe state"), (YELLOW, "FDTI: fault to detection"),
            (ORANGE, "FRTI budget: detection to safe state"), (BLUE, "FTTI"), (RED, "fault, siren, FTTI exceeded")]
  x = 40
  for col, lab in legend:
    o.append(f'<rect x="{x}" y="{ly}" width="22" height="10" rx="2" fill="{col}"/>')
    o.append(text(x + 30, ly + 9, lab, 11.5, INK))
    x += 40 + 6.6 * len(lab)
  o.append(text(40, ly + 34, "FHTI = FDTI + FRTI must fit inside the FTTI. Emergency operation (EOTI) is a planned phase after "
                "the FHTI, not a fallback for a missed FTTI: here only the SG-08 no-response reaction uses one (WP-S-04 §2, §3.8.4).",
                11.5, MUTED))
  o.append("</svg>")
  return "\n".join(o) + "\n"


def main(argv: list[str]) -> int:
  svg = figure()
  path = HERE / OUT
  if "--check" in argv:
    if not path.exists() or path.read_text(encoding="utf-8") != svg:
      print(f"stale: {OUT}; run: python3 assurance/models/figures/fig_timing_anim.py", file=sys.stderr)
      return 1
    print(f"fig_timing_anim: {OUT} current")
    return 0
  path.write_text(svg, encoding="utf-8")
  print(f"fig_timing_anim: wrote {OUT}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
