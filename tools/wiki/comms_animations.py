#!/usr/bin/env python3
"""Render the explainers of the wiki page "CAN, CAN FD and end-to-end protection" as SVG.

  comms-frames.svg  a classical CAN frame and a CAN FD frame, field by field, and inside the data field the Toyota
                    steering frame 0x2E4 with its counter and checksum: what the CAN controller adds on every hop and
                    what the sender adds end to end;
  comms-e2e.svg     the four hops of the reference configuration as tracks, each with the checks a frame passes in
                    order (the "gates"), coloured by whether the check is built; six faults are sent down the tracks
                    one after another and either stop at the gate that catches them or get through.

The hops, the checks and the faults are those of WP-S-05 §12.3; the status of every check that names a requirement is
read from the TSR list, and the counter and checksum facts from WP-S-05 §5 and §11. Every phrase a figure stands on is
tied to its record (SOURCES) and checked at render time (`problems()`): when a record changes, the wiki build fails
instead of showing old text. build_wiki.py renders them next to the pages at each sync; they loop with CSS and SMIL,
and reduced motion shows the final frame: the tracks and their gates without the faults.

Usage: python3 tools/wiki/comms_animations.py [--out DIR] [--check]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from animations import GRN, LIGHT, MID, NAVY, RED, W, Timeline, g, norm, svg, t  # noqa: E402
from how_animations import box  # noqa: E402

NAMES = ("comms-frames.svg", "comms-e2e.svg")
BLUE, AMBER, TEAL, GREY = "#2a78d6", "#b7791f", "#0f766e", "#9aa5b8"

A = Path("assurance")
S05 = A / "03-system" / "WP-S-05-hsi-specification.md"
TSR_LIST = A / "03-system" / "requirements" / "tsr-list.md"

# phrases the figures stand on: (record, phrase)
SOURCES = [
  (S05, "| `0xAA` | WHEEL_SPEEDS | 83 Hz | no | no |"),
  (S05, "| `0x226` | BRAKE_MODULE | 40 Hz | no | no |"),
  (S05, "8-bit CHECKSUM (byte 4) | 6-bit COUNTER (checked by the EPS, not by the item)"),
  (S05, "**No counter on any of them**"),
  (S05, "For these frames the panda is a black channel"),
  (S05, "**E2E protects the channel, not the sender.**"),
  (S05, "**The protocol CRC protects one hop, not the path.**"),
  (S05, "CRC-17 (≤ 16 bytes) or CRC-21, with a stuff-bit count inside the CRC field"),
  (S05, "| H1 | SoC (QM) → panda, SPI (§4) | 8-bit XOR per transfer and per CAN packet |"),
]

# gate kinds that do not name a requirement: (fill, stroke, dash, ink, status word)
FIXED = {
  "protocol": ("#e7f5ee", GRN, "", GRN, "built in"),
  "weak": ("#fdf3e1", AMBER, "", AMBER, "weak"),
  "ecu": ("#e8f0fb", BLUE, "", BLUE, "car checks"),
  "none": ("#f3f4f7", GREY, "4 3", GREY, "none here"),
}
STATUS = {  # TSR list status -> (fill, stroke, dash, ink, status word)
  "implemented": ("#e7f5ee", GRN, "", GRN, "built"),
  "partly": ("#fdf3e1", AMBER, "", AMBER, "partly"),
  "not implemented": ("#fdecec", RED, "5 3", RED, "planned"),
}

# the four hops of WP-S-05 §12.3: (hop, title, sender, receiver, gates); a gate is (name, requirement or kind)
HOPS = [
  ("H1", "SoC → panda · SPI link", "openpilot (QM)", "panda",
   [("XOR", "weak"), ("CRC", "TSR-410"), ("counter, age", "TSR-411")]),
  ("H2", "panda → steering · bus 0", "envelope", "EPS",
   [("limits", "TSR-101"), ("CAN CRC", "protocol"), ("checksum, counter", "ecu")]),
  ("H3", "car → panda · bus 0", "car ECUs", "envelope",
   [("CAN CRC", "protocol"), ("checksum", "TSR-402"), ("counter", "none"), ("timeout", "TSR-401"),
    ("frozen value", "TSR-404"), ("cross-check", "TSR-405")]),
  ("H4", "camera → brakes · forwarded", "camera", "brake ECU",
   [("forward as is", "TSR-704"), ("CAN CRC", "protocol"), ("checksum, counter", "ecu")]),
]
# the faults, in the order they are sent: (hop, gate that catches it, what happens, what the caption says)
FAULTS = [
  ("H3", "CAN CRC", "A bit flips on the wire", "The CAN controller's CRC catches it, on this hop."),
  ("H3", "timeout", "The brake module goes silent", "Absence for 5 periods is detected."),
  ("H3", "frozen value", "Wheel speeds freeze but keep coming", "No counter on this car: only a frozen-value check can see it."),
  ("H1", "CRC", "Two bits flip on the SPI link", "The 8-bit XOR misses two flips in the same bit position; a CRC would not."),
  ("H2", "limits", "openpilot packs a wrong torque, correctly", "E2E protects the channel, not the sender: only the limits stop it."),
  ("H4", "checksum, counter", "A byte changes inside the panda", "A fresh CAN CRC hides it; the camera's own checksum does not."),
]
LOOP_SCENE = 4.2


def _read(root: Path, path: Path) -> str:
  return (root / path).read_text(encoding="utf-8")


def tsrs() -> list[str]:
  return sorted({k for _h, _t, _s, _r, gates in HOPS for _n, k in gates if k.startswith("TSR-")})


def data(root: Path = ROOT) -> dict:
  tsr = _read(root, TSR_LIST)
  status = {}
  for k in tsrs():
    m = re.search(rf"^\| \[{k}\]\([^)]*\) \|[^|]*\|[^|]*\|[^|]*\| ([^|]+?) \|", tsr, re.M)
    if not m:
      raise ValueError(f"{TSR_LIST}: {k} not found")
    status[k] = m.group(1)
  return {"status": status}


def look(kind: str, d: dict) -> tuple[str, str, str, str, str]:
  if kind in FIXED:
    return FIXED[kind]
  return STATUS.get(d["status"][kind], ("#fff", MID, "", MID, d["status"][kind]))


def caught(hop: str, gate: str, d: dict) -> bool:
  """Whether the gate that should catch a fault is there today: a fault passes a planned check."""
  kind = dict(next(h[4] for h in HOPS if h[0] == hop))[gate]
  return kind in ("protocol", "ecu") or d["status"].get(kind) in ("implemented", "partly")


def problems(root: Path = ROOT) -> list[str]:
  errs, cache = [], {}
  for path, phrase in SOURCES:
    if path not in cache:
      p = root / path
      cache[path] = norm(p.read_text(encoding="utf-8")) if p.exists() else ""
    if norm(phrase) not in cache[path]:
      errs.append(f"{path}: the CAN page stands on {phrase!r}, which is gone; update the figure")
  hops = {h[0]: [n for n, _k in h[4]] for h in HOPS}
  for hop, gate, _w, _c in FAULTS:
    if gate not in hops.get(hop, []):
      errs.append(f"comms-e2e.svg: fault on {hop} names gate {gate!r}, which the hop does not have")
  try:
    d = data(root)
    if d["status"]["TSR-410"] == "implemented" or d["status"]["TSR-404"] == "implemented":
      errs.append(f"{TSR_LIST}: TSR-410 or TSR-404 is now implemented; comms-e2e.svg captions say those faults get through")
  except (OSError, ValueError) as e:
    errs.append(f"cannot read the records the CAN page is drawn from: {e}")
  return errs


# ---------------------------------------------------------------- SVG pieces

def mover(loop: float, x0: float, x1: float, y: float, t0: float, t1: float, hold: float, c: str) -> str:
  """A small frame that slides from x0 to x1 between t0 and t1, waits for `hold` seconds and vanishes; hidden under
  reduced motion."""
  k = lambda s: f"{min(max(s / loop, 0), 1):.4f}"  # noqa: E731
  return (f'<g class="tr" opacity="0"><rect x="-13" y="{y - 8}" width="26" height="16" rx="3" fill="{c}"/>'
          f'<rect x="5" y="{y - 8}" width="8" height="16" rx="2" fill="#fff" opacity="0.55"/>'
          f'<animateTransform attributeName="transform" type="translate" dur="{loop:g}s" repeatCount="indefinite" '
          f'values="{x0},0;{x0},0;{x1},0;{x1},0" keyTimes="0;{k(t0)};{k(t1)};1"/>'
          f'<animate attributeName="opacity" dur="{loop:g}s" repeatCount="indefinite" values="0;0;1;1;0;0" '
          f'keyTimes="0;{k(t0 - .02)};{k(t0)};{k(t1 + hold)};{k(t1 + hold + .05)};1"/></g>')


def spark(x, y, c=RED) -> str:
  pts = " ".join(f"{x + dx},{y + dy}" for dx, dy in ((0, -11), (3, -3), (11, -2), (4, 3), (6, 11), (0, 6), (-6, 11), (-4, 3),
                                                      (-11, -2), (-3, -3)))
  return f'<polygon points="{pts}" fill="{c}"/>'


# ---------------------------------------------------------------- 1. the frames

CLASSIC = [("SOF", 1, NAVY), ("identifier", 11, BLUE), ("ctrl", 3, MID), ("DLC", 4, MID), ("data 0–8 bytes", 64, TEAL),
           ("CRC-15", 16, GRN), ("ACK", 2, MID), ("EOF", 7, NAVY)]
FD = [("SOF", 1, NAVY), ("identifier", 11, BLUE), ("FDF BRS", 6, MID), ("DLC", 4, MID),
      ("data 0–64 bytes, fast", 64, TEAL), ("CRC-17/21", 22, GRN), ("ACK", 2, MID), ("EOF", 7, NAVY)]
# Toyota STEERING_LKA 0x2E4 data field, as WP-S-05 §11 S-01 and S-02 describe it, sized by bits
LKA = [("COUNTER", 6, AMBER), ("REQ", 2, MID), ("TORQUE_CMD 16 bit", 16, NAVY), ("other", 8, LIGHT), ("CHECKSUM", 8, AMBER)]


def bar_row(x0: float, x1: float, y: float, fields, h=34) -> list[str]:
  total, out, x = sum(f[1] for f in fields), [], x0
  for name, n, c in fields:
    w = (x1 - x0) * n / total
    out.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{h}" fill="{c}" stroke="#fff" stroke-width="1.5"/>')
    if len(name) * 5.9 < w - 4:
      out.append(t(x + w / 2, y + h / 2 + 4.5, name, 11, NAVY if c == LIGHT else "#fff", 700, "middle"))
    x += w
  return out


def span(fields, i: int, j: int, x0: float, x1: float) -> tuple[float, float]:
  """x range of fields[i:j] in a bar drawn between x0 and x1."""
  total = sum(f[1] for f in fields)
  return (x0 + (x1 - x0) * sum(f[1] for f in fields[:i]) / total, x0 + (x1 - x0) * sum(f[1] for f in fields[:j]) / total)


def frames() -> str:
  tl, h = Timeline(14.0), 470
  x0, x1 = 24, W - 24
  b = [t(24, 38, "Inside a CAN frame", 24, NAVY, 700),
       t(24, 62, "What the CAN controller adds on every hop, and what the sender adds end to end", 15, MID)]
  b.append(g(f"{tl.show(0.3)} fin", [t(24, 100, "Classical CAN · ISO 11898-1 · 500 kbit/s on the reference car", 14, NAVY, 700)]
             + bar_row(x0, x1, 110, CLASSIC)))
  # the data field of 0x2E4, drawn under the data field it fills
  dx0, dx1 = span(CLASSIC, 4, 5, x0, x1)
  k = tl.show(1.6)
  b.append(g(f"{k} fin", [f'<path d="M{dx0:.0f},148 v6 H{dx1:.0f} v-6" fill="none" stroke="{TEAL}" stroke-width="2"/>',
                          t(24, 186, "Toyota", 12, NAVY, 700), t(24, 200, "0x2E4", 12, NAVY, 700)]
             + bar_row(dx0, dx1, 166, LKA, 30)))
  k = tl.show(3.0)
  b.append(g(f"{k} fin", [box(24, 214, W - 48, 58, "#fdf3e1", AMBER),
                          t(36, 234, "Counter and checksum: written by the sender, checked by the receiver, end to end.", 13, NAVY, 600),
                          t(36, 250, "Here the sender is openpilot (QM) and the receiver the EPS. A wrong torque packed", 13, NAVY),
                          t(36, 266, "correctly passes both: E2E protects the channel, not the sender.", 13, NAVY)]))
  b.append(g(f"{tl.show(4.6)} fin", [t(24, 306, "CAN FD · same start, then up to 64 bytes at a faster data rate", 14, NAVY, 700)]
             + bar_row(x0, x1, 316, FD)))
  fx0, fx1 = span(FD, 3, 6, x0, x1)
  k = tl.show(6.0)
  b.append(g(f"{k} fin", [f'<path d="M{fx0:.0f},354 v6 H{fx1:.0f} v-6" fill="none" stroke="{TEAL}" stroke-width="2"/>',
                          t((fx0 + fx1) / 2, 376, "after the bit-rate switch: 2 to 5 Mbit/s; the CRC also counts the stuff bits", 12.5,
                            TEAL, 700, "middle")]))
  k = tl.show(7.6)
  b.append(g(f"{k} fin", [box(24, 396, W - 48, 44, "#e7f5ee", GRN),
                          t(36, 414, "CRC, stuffing, ACK: added and checked by each CAN controller, again on every hop.", 13, NAVY, 600),
                          t(36, 431, "A frame corrupted inside a box leaves it with a fresh, valid CRC.", 13, NAVY)]))
  return svg(h, "Inside a CAN frame (animated)",
             "A classical CAN frame (start of frame, 11-bit identifier, control bits, 4-bit DLC, 0 to 8 data bytes, CRC-15, "
             "acknowledge, end of frame). Under its data field, the Toyota steering command 0x2E4: a 6-bit counter, the steer "
             "request, the 16-bit torque command, other signals and the checksum in byte 4, written by the sender (openpilot, "
             "QM) and checked by the receiver (the EPS); a wrong torque packed correctly passes both: E2E protects the channel, "
             "not the sender. Then a CAN FD frame: the same start, FDF and BRS bits, 0 to 64 data bytes sent at 2 to 5 Mbit/s "
             "after the bit-rate switch, CRC-17 or CRC-21 that also counts the stuff bits. The CRC, stuffing and acknowledge "
             "are added and checked by every CAN controller on every hop, so a frame corrupted inside a box leaves with a "
             "fresh, valid CRC.", tl, b)


# ---------------------------------------------------------------- 2. the gauntlet

TRACK_X0, TRACK_X1, LANE_H, TOP = 28, W - 28, 100, 88


def gate_geometry(n: int) -> tuple[list[float], float]:
  """Centres of n gates spread along the track, and their width."""
  slot = (TRACK_X1 - TRACK_X0 - 40) / n
  return [TRACK_X0 + 40 + slot * (i + 0.5) for i in range(n)], min(110.0, slot - 8)


def e2e(d: dict) -> str:
  scenes = len(FAULTS)
  tl = Timeline(scenes * LOOP_SCENE + 0.8)
  h = TOP + LANE_H * len(HOPS) + 100
  b = [t(24, 38, "Six faults, four hops", 24, NAVY, 700),
       t(24, 62, "Each frame meets its hop's checks in order; a fault stops at the check that catches it", 15, MID)]
  lane_y, gx, gw = {}, {}, {}
  for i, (hop, title, sender, receiver, gates) in enumerate(HOPS):
    y = TOP + i * LANE_H
    ty = y + 50
    lane_y[hop] = ty
    b += [box(16, y, W - 32, LANE_H - 8, "#fff", LIGHT, 10, 1.2),
          f'<rect x="26" y="{y + 9}" width="30" height="20" rx="10" fill="{NAVY}"/>', t(41, y + 23, hop, 11.5, "#fff", 700, "middle"),
          t(64, y + 24, title, 14, NAVY, 700),
          t(TRACK_X0, ty + 34, f"from {sender}", 11.5, MID, 600), t(TRACK_X1, ty + 34, f"to {receiver}", 11.5, MID, 600, "end"),
          f'<line x1="{TRACK_X0}" y1="{ty}" x2="{TRACK_X1}" y2="{ty}" stroke="{LIGHT}" stroke-width="4" stroke-linecap="round"/>']
    xs, w = gate_geometry(len(gates))
    for (name, kind), x in zip(gates, xs, strict=True):
      fill, stroke, dash, ink, word = look(kind, d)
      gx[(hop, name)], gw[hop] = x, w
      ds = f' stroke-dasharray="{dash}"' if dash else ""
      sub = f"{kind} · {word}" if kind.startswith("TSR-") else word
      b += [f'<rect x="{x - w / 2:.1f}" y="{ty - 17}" width="{w:.1f}" height="34" rx="7" fill="{fill}" stroke="{stroke}" stroke-width="1.6"{ds}/>',
            t(x, ty - 2, name, 11.5, NAVY, 700, "middle"), t(x, ty + 12, sub, 10, ink, 700, "middle")]
  # the faults, one per scene
  cap_y = TOP + LANE_H * len(HOPS) + 6
  b.append(box(16, cap_y, W - 32, 58, "#fff", LIGHT, 10, 1.2))
  b.append(g(f"{tl.show(0)} fin", [t(36, cap_y + 24, "The final frame shows every check and its status.", 14, NAVY, 700),
                                  t(36, cap_y + 44, "Six faults are sent down the tracks in turn.", 13.5, MID)]))
  for j, (hop, gate, what, says) in enumerate(FAULTS):
    t0 = 0.6 + j * LOOP_SCENE
    ty = lane_y[hop]
    stop = caught(hop, gate, d)
    gate_x, w = gx[(hop, gate)], gw[hop]
    end_x = gate_x - w / 2 - 16 if stop else TRACK_X1 - 14
    col = GRN if stop else RED
    kind = dict(next(hh[4] for hh in HOPS if hh[0] == hop))[gate]
    partly = d["status"].get(kind) == "partly"
    b.append(mover(tl.loop, TRACK_X0 + 14, end_x, ty, t0 + 0.5, t0 + 2.2, 1.3, NAVY))
    k = tl.show(t0 + 0.2, t0 + LOOP_SCENE - 0.4, 0.2)
    b.append(g(f"{k} tr", [spark(W - 36 - len(what) * 6.6 - 14, ty - 30), t(W - 36, ty - 26, what, 12.5, RED, 700, "end")]))
    verdict = ("caught" + (" · partly built" if partly else "")) if stop else "gets through today"
    k = tl.show(t0 + 2.3, t0 + LOOP_SCENE - 0.4, 0.2)
    mx, my = gate_x + w / 2 - 2, ty - 17
    b.append(g(f"{k} tr", [
      f'<circle cx="{mx:.1f}" cy="{my}" r="9" fill="{col}"/>', t(mx, my + 4.5, "✓" if stop else "✗", 12, "#fff", 700, "middle"),
      *([] if stop else [spark(TRACK_X1 - 14, ty - 2)]),
      f'<rect x="20" y="{cap_y + 4}" width="{W - 40}" height="50" fill="#fff"/>',
      t(36, cap_y + 24, f"{j + 1}. {what}: {verdict}.", 14, AMBER if partly else col, 700),
      t(36, cap_y + 44, says, 13.5, NAVY)]))
  # legend, always shown
  ly = h - 16
  x = 24
  for fill, stroke, dash, ink, word in (STATUS["implemented"], STATUS["partly"], STATUS["not implemented"], FIXED["ecu"],
                                        FIXED["none"]):
    ds = f' stroke-dasharray="{dash}"' if dash else ""
    b += [f'<rect x="{x}" y="{ly - 12}" width="22" height="15" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="1.4"{ds}/>',
          t(x + 28, ly, word, 12, ink, 700)]
    x += 40 + len(word) * 7
  b.append(t(W - 24, ly, "status from the TSR list", 11.5, MID, 400, "end"))
  desc = ["The four hops of the reference configuration, each a track of checks a frame meets in order."]
  for hop, title, sender, receiver, gates in HOPS:
    desc.append(f"{hop}, {title}, from {sender} to {receiver}: "
                + ", ".join(f"{n} ({look(k, d)[4]}{', ' + k if k.startswith('TSR-') else ''})" for n, k in gates) + ".")
  for j, (hop, gate, what, says) in enumerate(FAULTS):
    desc.append(f"Fault {j + 1} on {hop}: {what}; "
                f"{'caught at ' + gate if caught(hop, gate, d) else 'gets through today, ' + gate + ' is planned'}. {says}")
  return svg(h, "Six faults, four hops (animated)", " ".join(desc), tl, b)


def render(root: Path = ROOT) -> dict[str, str]:
  d = data(root)
  return dict(zip(NAMES, (frames(), e2e(d)), strict=True))


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
