#!/usr/bin/env python3
"""Draw WP-S-03 Figure 3-3, the functional flow (fig-s03-3-3-functional-flow.svg).

The functions in the order they act, from what the car sees to what it does, by partition rather than by hardware: the
openpilot processes of the QM partition joined by the cereal services between them, the four stages of the ASIL C
envelope, and the vehicle and driver. Each process carries the item functions it realises (WP-C-01 §2.1) and the AI
error types that can enter there (WP-C-11 §5).

The layout is hand-placed. What it shows is checked against the documents, so the figure fails the build when they
change under it:
  every process is a row of WP-S-03 §8, with the element given there;
  every service arrow is a row of §9 with that publisher and subscriber;
  every function F-nn is a row of WP-C-01 §2.1 and every error type AE-x a row of WP-C-11 §5.

    python3 fig_s03_functional_flow.py            # write the SVG
    python3 fig_s03_functional_flow.py --check    # fail if a check fails or the SVG is stale

Standard library only. Output is deterministic.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fig_s03_defence_in_depth import (INK, MUTED, FAINT, LINE, SAFETY, SAFETY_BG, SW, RED, RED_BG, GREY_BG,  # noqa: E402
                                      text, rect, svg, header, el, fmt)
sys.path.insert(0, str(HERE.parents[1] / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)
sys.path.insert(0, str(HERE.parents[1] / "02-concept" / "hara"))
from hara_figures import wrap  # noqa: E402

SOURCE = HERE.parent / "WP-S-03-technical-safety-concept-architecture.md"
ITEM = HERE.parents[1] / "02-concept" / "WP-C-01-item-definition.md"
AI = HERE.parents[1] / "02-concept" / "WP-C-11-ai-system-definition-and-safety-requirements.md"
OUT = "fig-s03-3-3-functional-flow.svg"
W = 1440
NW, NH = 170, 78

# Processes of the QM partition: (name, x, y, what it does here, functions, AI error types).
PROCESSES = [
  ("camerad", 50, 150, "road and cabin camera frames", [], []),
  ("modeld", 310, 150, "AI-1 driving model: path, lanes, leads, curvature", ["F-01", "F-02"], ["AE-P", "AE-O", "AE-T", "AE-N"]),
  ("plannerd", 570, 150, "longitudinal plan: leads, set speed", ["F-02"], ["AE-L"]),
  ("controlsd", 830, 150, "control law: steering torque, acceleration", ["F-01", "F-02"], []),
  ("card", 1090, 150, "CAN to carState; commands to CAN frames", [], []),
  ("pandad", 1090, 300, "link to the panda: frames, mode, heartbeat", [], []),
  ("dmonitoringmodeld", 50, 300, "AI-3 driver monitoring model", ["F-04"], ["AE-D"]),
  ("dmonitoringd", 310, 300, "driver monitoring policy: timers, lockout", ["F-04"], []),
  ("radard", 570, 300, "lead fusion: radar and vision", ["F-02"], []),
  ("selfdrived", 830, 300, "engagement, events, alerts, warnings", ["F-03", "F-05", "F-06", "F-07"], []),
]
# Cereal services drawn: (service, publisher, subscriber, polyline, label position).
SERVICES = [
  ("modelV2", "modeld", "plannerd", [(482, 176), (568, 176)], (525, 168)),
  ("longitudinalPlan", "plannerd", "controlsd", [(742, 176), (828, 176)], (785, 168)),
  ("carControl", "controlsd", "card", [(1002, 170), (1088, 170)], (1045, 162)),
  ("carState", "card", "controlsd", [(1088, 206), (1004, 206)], (1045, 222)),
  ("sendcan", "card", "pandad", [(1150, 228), (1150, 298)], (1158, 268)),
  ("can", "pandad", "card", [(1210, 298), (1210, 230)], (1218, 268)),
  ("modelV2", "modeld", "controlsd", [(316, 150), (316, 128), (915, 128), (915, 148)], (622, 122)),
  ("radarState", "radard", "plannerd", [(655, 300), (655, 230)], (663, 270)),
  ("driverStateV2", "dmonitoringmodeld", "dmonitoringd", [(222, 339), (308, 339)], (265, 331)),
  ("driverMonitoringState", "dmonitoringd", "selfdrived", [(395, 378), (395, 404), (915, 404), (915, 380)], (655, 418)),
  ("selfdriveState", "selfdrived", "controlsd", [(895, 300), (895, 230)], (903, 270)),
  ("selfdriveState", "selfdrived", "pandad", [(1002, 326), (1088, 326)], (1045, 318)),
  ("pandaStates", "pandad", "selfdrived", [(1088, 358), (1004, 358)], (1045, 374)),
]
# Envelope stages (ASIL C, F-08) and the vehicle.
STAGES = [("RX checks", "brake, cruise, checksums, timeouts", 290), ("Authority", "controls_allowed: grant, revoke (Figure 4-5)", 570),
          ("Limits", "torque, rate, −3.5…+2.0 m/s²", 850), ("Transmit", "relay; frames to the EPS and PCM", 1130)]


class FlowError(ValueError):
  pass


def section(md: str, start: str) -> str:
  m = re.search(rf"^#+ {re.escape(start)}.*?$(.*?)(?=^#+ \d)", md, re.M | re.S)
  if not m:
    raise FlowError(f"section {start!r} not found")
  return m.group(1)


def check(s03: str, item: str, ai: str) -> None:
  procs: dict[str, str] = {}
  for ln in section(s03, "8.").splitlines():
    if ln.startswith("| `"):
      c = [x.strip() for x in ln.strip()[1:-1].split("|")]
      for name in re.findall(r"`([^`]+)`", c[0]):
        procs[name] = c[2]
  for name, *_ in PROCESSES:
    if name not in procs:
      raise FlowError(f"process {name} is not in WP-S-03 §8")
    if not procs[name].startswith("E-01"):
      raise FlowError(f"process {name} is on {procs[name]} in §8, not the SoC")
  svc: dict[str, tuple[str, set[str]]] = {}
  for ln in section(s03, "9.").splitlines():
    m = re.match(r"^\| `(\w+)` \| [^|]+ \| ([\w]+) → ([^|]+) \|", ln)
    if m:
      svc[m.group(1)] = (m.group(2), {s.strip() for s in m.group(3).split(",")})
  for name, pub, sub, *_ in SERVICES:
    if name not in svc:
      raise FlowError(f"service {name} is not in WP-S-03 §9")
    if svc[name][0] != pub or sub not in svc[name][1]:
      raise FlowError(f"§9 has {name} as {svc[name][0]} → {', '.join(sorted(svc[name][1]))}, the figure {pub} → {sub}")
  funcs = set(re.findall(r"^\| (F-\d\d) \|", section(item, "2.1"), re.M))
  errs = set(re.findall(r"^\| (AE-[A-Z]) \|", section(ai, "5."), re.M))
  for name, _, _, _, fs, aes in PROCESSES:
    for f in fs + ["F-08"]:
      if f not in funcs:
        raise FlowError(f"{f} ({name}) is not a function of WP-C-01 §2.1")
    for a in aes:
      if a not in errs:
        raise FlowError(f"{a} ({name}) is not an error type of WP-C-11 §5")
  drawn = {a for *_, aes in PROCESSES for a in aes}
  if drawn != errs:
    raise FlowError(f"error types not drawn: {sorted(errs - drawn)}")


def arrow(pts, col=INK, w=1.5, dash="", marker="muted"):
  p = " ".join(f"{fmt(x)},{fmt(y)}" for x, y in pts)
  return el("polyline", None, points=p, fill="none", stroke=col, stroke_width=w, stroke_dasharray=dash,
            marker_end=f"url(#{marker})")


def chip(x, y, label, fill, color="#FFFFFF", size=9.5):
  w = len(label) * size * 0.62 + 12
  return [rect(x, y, w, 17, fill=fill, stroke="none", sw=0, rx=8.5),
          text(x + w / 2, y + 12.5, label, size=size, fill=color, weight=700, anchor="middle")], w


def figure() -> str:
  out = header(W, "3-3", "Functional flow: from what the car sees to what it does",
               "The functions in the order they act, by partition rather than by hardware, with where each kind of AI "
               "error enters and what the envelope can catch", "WP-S-03 §3.4 · §8, §9")
  bands = [(100, 344, "QM partition · SoC processes (E-01) and models (E-02)", GREY_BG, FAINT, MUTED),
           (462, 130, "ASIL C safety envelope · panda MCU (E-03, E-04a) · F-08", SAFETY_BG, SAFETY, SAFETY),
           (610, 108, "Vehicle and driver", "#F8FAFC", LINE, MUTED)]
  for y, h, name, fill, st, tc in bands:
    out.append(rect(30, y, W - 60, h, fill=fill, stroke=st, sw=1.4, rx=12))
    if st == SAFETY:  # bottom left, clear of the arrows that enter and leave the envelope
      out.append(text(290, y + h - 10, name, size=12.5, fill=tc, weight=700))
    else:
      out.append(text(W - 46, y + 22, name, size=12.5, fill=tc, weight=700, anchor="end"))
  for name, x, y, role, fs, aes in PROCESSES:
    out.append(rect(x, y, NW, NH, fill="#FFFFFF", stroke=FAINT, sw=1.4, rx=10))
    out.append(text(x + 12, y + 21, name, size=12.5, weight=700))
    for i, ln in enumerate(wrap(role, NW - 24, 10)[:2]):
      out.append(text(x + 12, y + 38 + i * 13, ln, size=10, fill=MUTED))
    cx = x + 12
    for f in fs:
      c, w = chip(cx, y + NH - 1 - 17 + 9, f, SW)
      out += c
      cx += w + 4
    cx = x + NW
    for a in reversed(aes):
      c, w = chip(0, 0, a, RED)
      cx -= w
      c, _ = chip(cx, y - 9, a, RED)
      out += c
      cx -= 4
  out.append(arrow([(222, 176), (308, 176)]))
  out.append(text(265, 168, "frames", size=9.5, fill=MUTED, anchor="middle"))
  out.append(arrow([(135, 228), (135, 298)]))
  out.append(text(143, 268, "frames", size=9.5, fill=MUTED))
  for name, _, _, pts, (lx, ly) in SERVICES:
    out.append(arrow(pts))
    out.append(text(lx, ly, name, size=9, fill=INK, anchor="middle" if abs(pts[0][1] - pts[-1][1]) < 5 else "",
                    family="'JetBrains Mono', Menlo, Consolas, monospace"))
  # callout
  out.append(rect(42, 474, 236, 108, fill=RED_BG, stroke=RED, sw=1.2, rx=10, dash="5 4"))
  ly = 494
  for i, ln in enumerate(wrap("The envelope bounds the size of a command, not its direction.", 212, 10.5, True) +
                         wrap("A wrong curvature or a missed lead inside the limits passes every check; only the "
                              "driver or a monitor on the SoC catches it.", 212, 9.5)):
    out.append(text(54, ly, ln, size=10.5 if i < 2 else 9.5, fill=RED, weight=700 if i < 2 else ""))
    ly += 14 if i < 2 else 12.5
  # envelope stages
  for i, (name, sub, x) in enumerate(STAGES):
    out.append(rect(x, 494, 230, 70, fill="#FFFFFF", stroke=SAFETY, sw=1.4, rx=10))
    out.append(text(x + 12, 515, name, size=12.5, weight=700))
    for j, ln in enumerate(wrap(sub, 206, 10)[:2]):
      out.append(text(x + 12, 532 + j * 13, ln, size=10, fill=MUTED))
    if i < 3:
      out.append(arrow([(x + 230, 529), (STAGES[i + 1][2] - 2, 529)]))
  out.append(arrow([(1120, 378), (1120, 476), (965, 476), (965, 492)]))
  out.append(text(1128, 396, "frames (SPI)", size=9.5, fill=MUTED))
  out.append(arrow([(1240, 378), (1240, 453), (685, 453), (685, 492)], dash="5 4"))
  out.append(text(695, 484, "heartbeat 0xf3: engaged, 10 Hz", size=9.5, fill=MUTED))
  # vehicle
  out.append(rect(1130, 636, 230, 64, fill="#FFFFFF", stroke="#64748B", sw=1.4, rx=10))
  out.append(text(1142, 657, "EPS · PCM", size=12.5, weight=700))
  out.append(text(1142, 674, "steer and drive the car", size=10, fill=MUTED))
  out.append(rect(290, 636, 300, 64, fill="#FFFFFF", stroke="#64748B", sw=1.4, rx=10))
  out.append(text(302, 657, "Driver", size=12.5, weight=700))
  out.append(text(302, 674, "supervises; brakes, cancels, steers, takes over", size=10, fill=MUTED))
  out.append(arrow([(1245, 564), (1245, 634)]))
  out.append(arrow([(405, 636), (405, 566)]))
  out.append(text(413, 610, "brake, cancel (car CAN)", size=9.5, fill=MUTED))
  out.append(arrow([(1128, 668), (592, 668)], dash="5 4"))
  out.append(text(860, 660, "the car's motion, seen by the driver and the cameras", size=9.5, fill=MUTED, anchor="middle"))
  # footer
  y = 744
  lx = 40
  for lab, fill, desc in (("F-01", SW, "item function it realises (WP-C-01 §2.1)"), ("AE-P", RED, "AI error type that enters there (WP-C-11 §5)")):
    c, w = chip(lx, y - 12, lab, fill)
    out += c
    out.append(text(lx + w + 6, y, desc, size=10.5, fill=MUTED))
    lx += w + 6 + len(desc) * 5.7 + 24
  out.append(text(lx, y, "Arrows between processes are cereal services (§9); dashed arrows are not data the item acts on.",
                  size=10.5, fill=MUTED))
  y += 18
  out.append(text(40, y, "Generated by fig_s03_functional_flow.py; every process, service, function and error type is "
                  "checked against WP-S-03 §8–§9, WP-C-01 §2.1 and WP-C-11 §5.", size=10.5, fill=MUTED))
  extra, y = terms.svg_footer(out, 40, y + 22, W - 80)
  out += extra
  h = int(y + 12)
  desc = ("Processes: " + "; ".join(f"{n}: {r}" for n, _, _, r, *_ in PROCESSES) + ". Services: " +
          "; ".join(f"{s} {p} → {b}" for s, p, b, *_ in SERVICES) + ". Envelope: " +
          ", ".join(n for n, *_ in STAGES) + ".")
  return svg(W, h, "Figure 3-3. Functional flow (WP-S-03 §3.4)", desc, out)


def build() -> dict[str, str]:
  check(SOURCE.read_text(encoding="utf-8"), ITEM.read_text(encoding="utf-8"), AI.read_text(encoding="utf-8"))
  return {OUT: figure()}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except FlowError as e:
    print(f"fig_s03_functional_flow: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"assurance/03-system/figures/{n} is stale; run fig_s03_functional_flow.py", file=sys.stderr)
    if not stale:
      print(f"fig_s03_functional_flow: {len(outputs)} figure current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote assurance/03-system/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
