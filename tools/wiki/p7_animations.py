#!/usr/bin/env python3
"""Render the animated explainers of the wiki page "After release (ISO 26262 Part 7)" as SVG.

  p7-general.svg  the five stages after development (plan, produce, operate, service, decommission) in plain words,
                  as an overview; it quotes nothing from the standard and carries no clause numbers;
  p7-ours.svg     the same five stages for LionDriver, a retrofit (plan, install, operate, service, remove), with each
                  step's procedure ID and status from WP-S-06, WP-O-01, WP-O-02, WP-O-04, WP-S-02 and WP-A-03.

Every step of p7-ours.svg names the record it comes from, and the phrase it stands on is checked against that record
at render time (`problems()`); a "gap" or "partly" status is tied to the open item or finding that makes it so. When
a record changes, the wiki build fails instead of showing an old status. build_wiki.py renders the figures next to
the pages at each sync (nothing is committed). They loop with CSS; reduced motion shows the final frame.

Usage: python3 tools/wiki/p7_animations.py [--out DIR] [--check]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from animations import GRN, MID, NAVY, RED, W, Timeline, g, norm, stick, svg, t  # noqa: E402

NAMES = ("p7-general.svg", "p7-ours.svg")
AMBER, BLUE, VIOLET, ORANGE, TEAL = "#b7791f", "#2a78d6", "#6250d6", "#c2410c", "#0f766e"
STOPS = [("PLAN", NAVY), ("PRODUCE", BLUE), ("OPERATE", TEAL), ("SERVICE", VIOLET), ("DECOMMISSION", ORANGE)]

O01 = Path("assurance") / "09-production-operation" / "WP-O-01-installation-and-provisioning-control.md"
O02 = Path("assurance") / "09-production-operation" / "WP-O-02-operation-service-decommissioning.md"
O04 = Path("assurance") / "09-production-operation" / "WP-O-04-field-monitoring.md"
S06 = Path("assurance") / "03-system" / "WP-S-06-requirements-production-operation.md"
S02 = Path("assurance") / "03-system" / "WP-S-02-technical-safety-requirements.md"
A03 = Path("assurance") / "08-analyses" / "WP-A-03-dependent-failure-analysis.md"
OK, PART, GAP = ("written", GRN), ("partly", AMBER), ("gap", RED)

# (stage, colour, [(line, status, [(record, phrase the line stands on)])])
OURS = [
  ("PLAN", NAVY, [
    ("Requirements for production and operation (WP-S-06)", OK, [(S06, "# WP-S-06")]),
    ("Procedures for each stage (WP-O-01…05)", OK, [(O01, "# WP-O-01"), (O02, "# WP-O-02"), (O04, "# WP-O-04")]),
    ("Roles: one maintainer does every stage (DFI-19)", PART, [(A03, "**Single maintainer** writes, reviews and approves")])]),
  ("INSTALL", BLUE, [
    ("Identify device, harness and car (INS-01…05)", OK, [(O01, "| INS-01 | Identify the device"), (O01, "| INS-05 | Record VIN")]),
    ("Special characteristics: harness, connector, mount (SC)", OK, [(O01, "| INS-03 **[SC]**"), (O01, "| INS-09 **[SC]**"), (O01, "| INS-11 **[SC]**")]),
    ("Released software and panda firmware verified (INS-15…17)", OK, [(O01, "| INS-15 **[SC]** | Install the released LionDriver software"),
                                                                       (O01, "| INS-17 **[SC]** | Panda firmware verification")]),
    ("Engagement check with a trained driver (INS-28)", OK, [(O01, "| INS-28 | Engagement check with a trained driver")])]),
  ("OPERATE", TEAL, [
    ("Only released baselines; parameters checked after update", OK, [(O02, "| UPD-01 | Only released LionDriver baselines"),
                                                                      (O02, "| UPD-06 | After an update, the parameter set is checked")]),
    ("A withdrawn release forces dashcam mode (UPD-08)", OK, [(O02, "| UPD-08 | A release that is withdrawn")]),
    ("Rollback and post-update re-validation (WP-O-02 OI-7)", GAP, [(O02, "| OI-7 | Specify how an installed release is rolled back")]),
    ("Field monitoring: designed, no data path yet (WP-O-04)", PART, [(O04, "| LionDriver access to field data | **Not available**: default upload goes to comma.ai")])]),
  ("SERVICE", VIOLET, [
    ("Dealer EPS update: re-check firmware before engaging (SVC-02)", OK, [(O02, "| SVC-02 | EPS replacement or EPS software update by a dealer")]),
    ("TSR-620: no engagement until ECU firmware matches", OK, [(S02, "| TSR-620 | The item shall not request the TOYOTA safety mode or allow engagement unless the ECU firmware versions")]),
    ("Alignment or tyres: recalibrate (SVC-01, SVC-06)", OK, [(O02, "| SVC-01 | Wheel alignment"), (O02, "| SVC-06 | Tyre change")]),
    ("Windscreen: re-aim stock camera, remount (SVC-04)", OK, [(O02, "| SVC-04 | Windscreen replacement")])]),
  ("REMOVE", ORANGE, [
    ("Unplug; reconnect the stock camera; latch and pull test (DEC-02)", OK, [(O02, "| DEC-02 | Remove the harness; reconnect the stock forward camera connector")]),
    ("Stock LTA, DRCC, PCS back; no trouble codes (DEC-03, 04)", OK, [(O02, "| DEC-03 | Ignition on: confirm no TSS warning"), (O02, "| DEC-04 | Read DTCs")]),
    ("Reset the device, wipe its identity keys (DEC-07, 08)", OK, [(O02, "| DEC-07 | Run the device reset"), (O02, "| DEC-08 | Wipe the device identity")]),
    ("Revoke credentials and data paths (DEC-09, 10)", OK, [(O02, "| DEC-09 | Remove any LionDriver credentials"), (O02, "| DEC-10 | Revoke the device from LionDriver data paths")])]),
]


# how the summary names each step that is not yet in place
SHORT = {"Roles: one maintainer does every stage (DFI-19)": "independent roles",
         "Rollback and post-update re-validation (WP-O-02 OI-7)": "update rollback and re-validation",
         "Field monitoring: designed, no data path yet (WP-O-04)": "field monitoring running"}


def problems(root: Path = ROOT) -> list[str]:
  errs, cache = [], {}
  for _, _, lines in OURS:
    for line, _, refs in lines:
      for path, phrase in refs:
        if path not in cache:
          p = root / path
          cache[path] = norm(p.read_text(encoding="utf-8")) if p.exists() else ""
        if norm(phrase) not in cache[path]:
          errs.append(f"{path}: the After-release step {line!r} stands on {phrase!r}, which is gone; update the figure")
  return errs


def caps(tl, steps):
  out = []
  for i, (t0, cap) in enumerate(steps):
    t1 = steps[i + 1][0] - 0.2 if i + 1 < len(steps) else None
    out.append(g(f"{tl.show(t0, t1)} {'fin' if t1 is None else 'tr'}", [f'<rect x="24" y="66" width="{W - 48}" height="28" rx="6" fill="{NAVY}"/>', t(36, 85, cap, 13, "#fff", 600)]))
  return out

def road(tl, labels, y=124, t0=0.4, step=0.0):
  o = [f'<rect x="24" y="{y + 26}" width="{W - 48}" height="10" rx="5" fill="#e5e9f0"/>']
  xs = [70 + i * 145 for i in range(5)]
  for i, (x, (lab, col)) in enumerate(zip(xs, labels)):
    o += [f'<circle cx="{x}" cy="{y + 31}" r="17" fill="#fff" stroke="{col}" stroke-width="3"/>', t(x, y + 37, str(i + 1), 13, col, 800, "middle"),
          t(x, y + 72, lab, 11, col, 800, "middle")]
  return [g(f"{tl.show(t0)} fin", o)], xs

def car(x, y):
  return [f'<path d="M{x - 30},{y} h60 l-6,-12 h-14 l-6,-8 h-18 l-6,8 h-10 z" fill="#e8f0fb" stroke="{BLUE}" stroke-width="2"/>',
          f'<circle cx="{x - 16}" cy="{y + 1}" r="6" fill="#fff" stroke="{NAVY}" stroke-width="2"/>', f'<circle cx="{x + 16}" cy="{y + 1}" r="6" fill="#fff" stroke="{NAVY}" stroke-width="2"/>']

def stop_card(tl, t0, t1, x, col, title, lines, y=220):
  body = [f'<rect x="24" y="{y}" width="{W - 48}" height="{40 + 22 * len(lines)}" rx="12" fill="#fff" stroke="{col}" stroke-width="2"/>', t(40, y + 26, title, 15, col, 800)]
  for i, l in enumerate(lines):
    if isinstance(l, tuple):
      txt, st, sc = l
      w = len(st) * 6.6 + 18
      body += [t(40, y + 52 + i * 22, "• " + txt, 12.5, NAVY), f'<rect x="{W - 40 - w:.0f}" y="{y + 37 + i * 22}" width="{w:.0f}" height="19" rx="9.5" fill="{sc}"/>',
               t(W - 40 - w / 2, y + 51 + i * 22, st, 10, "#fff", 700, "middle")]
    else:
      body.append(t(40, y + 52 + i * 22, "• " + l, 12.5, NAVY))
  return [g(f"{tl.show(t0, t1)} {'tr' if t1 else 'fin'}", body + [f'<line x1="{x}" y1="172" x2="{x}" y2="{y}" stroke="{col}" stroke-width="2" stroke-dasharray="4 3"/>'])]

def general():
  tl, h = Timeline(26.0), 400
  b = [t(24, 38, "After development: ISO 26262 Part 7 at a glance", 21, NAVY, 700)]
  b += caps(tl, [(0.3, "Safety does not end at release: five stages follow"), (3.0, "1 · Plan how safety is kept after release"),
                 (7.0, "2 · Produce it exactly as designed"), (11.0, "3 · Operate: keep it safe in use"),
                 (15.0, "4 · Service: repair without breaking safety"), (19.0, "5 · Decommission: take it out of use safely"),
                 (23.0, "Requirements flow in from development; what is learned in the field flows back")])
  r, xs = road(tl, STOPS)
  b += r
  cards = [
    (NAVY, "PLAN", ["Who does what after release, with which resources", "Which requirements apply to each stage (set during development)", "How records and traceability are kept"]),
    (BLUE, "PRODUCE", ["Build and install exactly as specified", "Watch the special characteristics that matter for safety", "Inspect and test; trace parts; handle nonconformities"]),
    (TEAL, "OPERATE", ["Tell users how to use it safely, and its limits", "Monitor the field: faults, incidents, complaints", "Update software without losing safety"]),
    (VIOLET, "SERVICE", ["Maintain and repair to written instructions", "Re-check what a repair could have changed", "Keep records of what was done"]),
    (ORANGE, "DECOMMISSION", ["Disable the function; restore a safe vehicle", "Remove data and keys", "Close the records"]),
  ]
  for i, ((col, title, lines), x) in enumerate(zip(cards, xs)):
    t0 = 3.2 + i * 4.0
    b += stop_card(tl, t0, t0 + 3.7, x, col, title, lines)
    b.append(g(f"{tl.show(t0, t0 + 3.7)} tr", car(x, 118)))
    b.append(g(f"{tl.show(t0 + 0.4)} fin", [f'<circle cx="{x}" cy="155" r="17" fill="{col}"/>', t(x, 161, str(i + 1), 13, "#fff", 800, "middle")]))
  b.append(g(f"{tl.show(23.2)} fin", [f'<rect x="24" y="220" width="{W - 48}" height="120" rx="12" fill="#eef2f8" stroke="{NAVY}"/>',
             f'<path d="M70,240 h580" stroke="{NAVY}" stroke-width="2" marker-end=""/>', t(40, 262, "→ Requirements for production, operation and service come from development (ISO 26262-4).", 12.5, NAVY, 600),
             t(40, 286, "← Field issues feed back into the analyses and the next release.", 12.5, NAVY, 600),
             t(40, 316, "Overview in plain words; the requirements are in the licensed ISO 26262-7:2018 text.", 11.5, MID, 400, "start", True)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "After development: ISO 26262 Part 7 at a glance (animated)",
             "Five stages after development, in plain words: plan how safety is kept after release; produce and install exactly as "
             "specified, with special characteristics, inspection, tests, traceable parts and nonconformity handling; operate, with "
             "user information, field monitoring and safe updates; service to written instructions, re-checking what a repair could "
             "change; decommission, disabling the function, restoring a safe vehicle and removing data and keys. Requirements flow in "
             "from development (ISO 26262-4); field issues flow back. An overview, not the standard's text.", tl, b)

def ours() -> str:
  tl, h = Timeline(28.0), 410
  b = [t(24, 38, "After release: LionDriver on the reference car", 21, NAVY, 700)]
  b += caps(tl, [(0.3, "A retrofit: 'production' is installing it on the owner's car"), (3.0, "1 · Plan: WP-S-06 sets the requirements; WP-O-01…05 the procedures"),
                 (7.4, "2 · Install (WP-O-01): every step checked and recorded"), (11.8, "3 · Operate (WP-O-02, WP-O-04): only released software"),
                 (16.2, "4 · Service (WP-O-02 §4): a workshop can change what we rely on"), (20.6, "5 · Remove (WP-O-02 §7): the stock car comes back"),
                 (25.0, "Where we are: procedures written, none yet run in the field")])
  r, xs = road(tl, [(stage, col) for stage, col, _ in OURS])
  b += r
  for i, ((stage, col, lines), x) in enumerate(zip(OURS, xs)):
    t0 = 3.2 + i * 4.4
    b += stop_card(tl, t0, t0 + 4.1, x, col, stage, [(line, *status) for line, status, _ in lines])
    b.append(g(f"{tl.show(t0, t0 + 4.1)} tr", car(x, 118)))
    b.append(g(f"{tl.show(t0 + 0.4)} fin", [f'<circle cx="{x}" cy="155" r="17" fill="{col}"/>', t(x, 161, str(i + 1), 13, "#fff", 800, "middle")]))
  open_ = [SHORT.get(line, line) for _, _, lines in OURS for line, status, _ in lines if status != OK]
  b.append(g(f"{tl.show(25.2)} fin", [f'<rect x="24" y="220" width="{W - 110}" height="132" rx="12" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 246, "Written: install, service and removal steps, with checks and records.", 12.5, NAVY, 600),
             t(40, 270, "Not yet: " + "; ".join(open_) + ".", 12, RED, 600),
             t(40, 294, "None of it has run on a customer car: no LionDriver field operation yet.", 12.5, NAVY, 600),
             t(40, 326, "Statuses from WP-O-01, WP-O-02 and WP-O-04 (all Draft).", 11.5, MID, 400, "start", True)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "After release: LionDriver on the reference car (animated)",
             "The five stages for LionDriver, a retrofit: " + " ".join(
               f"{stage}: " + "; ".join(f"{line} ({status[0]})" for line, status, _ in lines) + "." for stage, _, lines in OURS)
             + " None of it has run on a customer car yet.", tl, b)


def render(root: Path = ROOT) -> dict[str, str]:
  return {"p7-general.svg": general(), "p7-ours.svg": ours()}


def write_all(out: Path, root: Path = ROOT) -> None:
  out.mkdir(parents=True, exist_ok=True)
  for name, text in render(root).items():
    (out / name).write_text(text, encoding="utf-8")


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--out", type=Path, default=None, help="write the SVGs here")
  ap.add_argument("--check", action="store_true", help="fail if a step's record changed")
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
