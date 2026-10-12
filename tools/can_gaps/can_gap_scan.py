#!/usr/bin/env python3
"""Inter-frame gap scan for the envelope RX checks (LionDriver TSR-401).

The 5-period RX timeout of jherrodthomas/opendbc#1 revokes authority when a gating
message is missing for longer than 5 nominal periods (60 ms for WHEEL_SPEEDS). If the
real bus ever pauses that long, engagement drops on the road. This script measures, for
each RX-checked message, the largest gap between consecutive frames in recorded drives
and compares it with the timeout. It also reports the observed rate against the nominal
rate the safety mode declares.

Inputs (one or more files; each file is scanned on its own, so the gap across a file
boundary is never counted):
  - openpilot rlog (raw, .bz2 or .zst). qlogs are refused: they keep only a fraction of
    the CAN frames, which would create gaps that are not on the bus.
  - candump log (`candump -l` format: "(1690000000.123456) can0 0AA#...").
  - CSV with a header containing time_s, bus, address (address decimal or 0x hex).

Timing uncertainty: an rlog stamps CAN frames per pandad batch (about 10 ms), not per
frame, so a measured gap can be off by up to one batch period. The margin check adds
that uncertainty (--uncertainty-ms, default 10 for rlogs and 0 otherwise).

Verdicts per message:
  MISSING     no frame of the message on the bus
  FAIL        a measured gap is longer than the timeout: this drive would have revoked
  LOW MARGIN  max gap + uncertainty above --margin of the timeout (default 0.8)
  PASS        otherwise

Exit status: 1 if any message is MISSING or FAIL (or LOW MARGIN with --strict), else 0.

Usage:
  tools/can_gaps/can_gap_scan.py rlog.zst [more rlogs ...]
  tools/can_gaps/can_gap_scan.py --variant secoc --format candump drive.log
  tools/can_gaps/can_gap_scan.py --msg 0x262:33 --format csv frames.csv --json out.json
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field

# Toyota RX checks as declared in opendbc/safety/modes/toyota.h (address, nominal Hz).
# test_can_gap_scan.py cross-checks these against the opendbc submodule when it is present.
VARIANTS: dict[str, list[tuple[int, int]]] = {
  "lka": [(0xAA, 83), (0x260, 50), (0x1D2, 33), (0x226, 40)],
  "alt_brake": [(0xAA, 83), (0x260, 50), (0x1D2, 33), (0x224, 40)],
  "secoc": [(0xAA, 83), (0x260, 50), (0x176, 32), (0x116, 42), (0x101, 50)],
}
VARIANTS["lta"] = VARIANTS["lka"]

RX_TIMEOUT_PERIODS = 5  # opendbc#1, Toyota
RX_BUS = 0
RLOG_UNCERTAINTY_MS = 10.0


def timeout_us(freq_hz: int, periods: int = RX_TIMEOUT_PERIODS) -> int:
  # same arithmetic as safety_tick(): uint32_t timestep = 1e6 / frequency
  return int(1e6 / freq_hz) * periods


@dataclass
class MsgStats:
  address: int
  freq_hz: int
  frames: int = 0
  gaps_us: list[int] = field(default_factory=list)

  @property
  def timeout_us(self) -> int:
    return timeout_us(self.freq_hz)

  @property
  def max_gap_us(self) -> int | None:
    return max(self.gaps_us) if self.gaps_us else None

  def percentile_us(self, p: float) -> float | None:
    if not self.gaps_us:
      return None
    s = sorted(self.gaps_us)
    k = (len(s) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)

  @property
  def over_timeout(self) -> int:
    return sum(1 for g in self.gaps_us if g > self.timeout_us)

  @property
  def observed_hz(self) -> float | None:
    med = self.percentile_us(0.5)
    return 1e6 / med if med else None

  def verdict(self, uncertainty_us: float, margin: float) -> str:
    if self.frames == 0:
      return "MISSING"
    if self.max_gap_us is None:
      return "MISSING"  # a single frame gives no gap
    if self.max_gap_us > self.timeout_us:
      return "FAIL"
    if self.max_gap_us + uncertainty_us > margin * self.timeout_us:
      return "LOW MARGIN"
    return "PASS"


# ---------------------------------------------------------------- readers
# Each reader yields (time_us, bus, address) in file order.

CANDUMP_RE = re.compile(r"^\((\d+(?:\.\d+)?)\)\s+(\S+)\s+([0-9A-Fa-f]+)#")


def read_candump(path: str, iface_bus: dict[str, int]):
  with open(path) as f:
    for line in f:
      m = CANDUMP_RE.match(line.strip())
      if not m:
        continue
      ts, iface, addr = m.groups()
      if iface not in iface_bus:
        continue
      yield round(float(ts) * 1e6), iface_bus[iface], int(addr, 16)


def read_csv(path: str):
  with open(path, newline="") as f:
    for row in csv.DictReader(f):
      yield round(float(row["time_s"]) * 1e6), int(row["bus"]), int(row["address"], 0)


def read_rlog(path: str):
  if "qlog" in os.path.basename(path):
    raise ValueError(f"{path}: qlogs keep only some CAN frames; use the rlog")
  from opendbc.car.logreader import LogReader  # needs pycapnp and zstandard
  for ev in LogReader(path, sort_by_time=True):
    if ev.which() != "can":
      continue
    t_us = ev.logMonoTime // 1000
    for c in ev.can:
      yield t_us, c.src, c.address


def detect_format(path: str) -> str:
  name = os.path.basename(path).lower()
  if name.endswith(".csv"):
    return "csv"
  if name.endswith((".log", ".candump")):
    return "candump"
  return "rlog"


# ---------------------------------------------------------------- scan

def scan(frames, stats: dict[int, MsgStats], bus: int = RX_BUS) -> None:
  """Add the gaps of one file to stats. frames: iterable of (time_us, bus, address)."""
  last: dict[int, int] = {}
  for t_us, b, addr in frames:
    if b != bus or addr not in stats:
      continue
    st = stats[addr]
    st.frames += 1
    if addr in last:
      st.gaps_us.append(t_us - last[addr])
    last[addr] = t_us


def new_stats(msgs: list[tuple[int, int]]) -> dict[int, MsgStats]:
  return {addr: MsgStats(addr, hz) for addr, hz in msgs}


def report_rows(stats: dict[int, MsgStats], uncertainty_us: float, margin: float) -> list[dict]:
  rows = []
  for st in stats.values():
    p999 = st.percentile_us(0.999)
    rows.append({
      "address": f"0x{st.address:X}",
      "nominal_hz": st.freq_hz,
      "observed_hz": round(st.observed_hz, 1) if st.observed_hz else None,
      "frames": st.frames,
      "timeout_ms": st.timeout_us / 1000,
      "max_gap_ms": st.max_gap_us / 1000 if st.max_gap_us is not None else None,
      "p99_9_gap_ms": round(p999 / 1000, 1) if p999 is not None else None,
      "gaps_over_timeout": st.over_timeout,
      "verdict": st.verdict(uncertainty_us, margin),
    })
  return rows


def markdown(rows: list[dict], uncertainty_ms: float, margin: float) -> str:
  def fmt(v):
    return "–" if v is None else str(v)
  header = (f"Timeout = {RX_TIMEOUT_PERIODS} nominal periods; timing uncertainty {uncertainty_ms} ms; " +
            f"margin {margin:.0%} of the timeout.")
  out = [header, "",
         "| Message | Nominal Hz | Observed Hz | Frames | Timeout ms | Max gap ms | p99.9 gap ms | Gaps > timeout | Verdict |",
         "|---|---|---|---|---|---|---|---|---|"]
  for r in rows:
    out.append("| " + " | ".join(fmt(r[k]) for k in ("address", "nominal_hz", "observed_hz", "frames", "timeout_ms",
                                                     "max_gap_ms", "p99_9_gap_ms", "gaps_over_timeout", "verdict")) + " |")
  return "\n".join(out)


def parse_msg(s: str) -> tuple[int, int]:
  addr, hz = s.split(":")
  return int(addr, 0), int(hz)


def main(argv: list[str] | None = None) -> int:
  ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
  ap.add_argument("files", nargs="+")
  ap.add_argument("--variant", choices=sorted(VARIANTS), default="lka", help="Toyota RX check set (default lka)")
  ap.add_argument("--msg", action="append", type=parse_msg, metavar="ADDR:HZ",
                  help="scan these messages instead of the variant set (repeatable)")
  ap.add_argument("--format", choices=["auto", "rlog", "candump", "csv"], default="auto")
  ap.add_argument("--iface", action="append", default=[], metavar="IFACE=BUS",
                  help="candump interface to bus mapping (default can0=0)")
  ap.add_argument("--bus", type=int, default=RX_BUS, help="bus of the RX checks (default 0)")
  ap.add_argument("--uncertainty-ms", type=float, help="timing uncertainty (default 10 for rlogs, else 0)")
  ap.add_argument("--margin", type=float, default=0.8, help="LOW MARGIN above this fraction of the timeout")
  ap.add_argument("--strict", action="store_true", help="exit 1 on LOW MARGIN too")
  ap.add_argument("--json", metavar="PATH", help="also write the rows as JSON")
  args = ap.parse_args(argv)

  msgs = args.msg or VARIANTS[args.variant]
  iface_bus = {k: int(v) for k, v in (s.split("=") for s in args.iface)} or {"can0": 0}
  stats = new_stats(msgs)

  formats = set()
  for path in args.files:
    fmt = detect_format(path) if args.format == "auto" else args.format
    formats.add(fmt)
    if fmt == "csv":
      frames = read_csv(path)
    elif fmt == "candump":
      frames = read_candump(path, iface_bus)
    else:
      frames = read_rlog(path)
    scan(frames, stats, args.bus)

  unc_ms = args.uncertainty_ms if args.uncertainty_ms is not None else (RLOG_UNCERTAINTY_MS if "rlog" in formats else 0.0)
  rows = report_rows(stats, unc_ms * 1000, args.margin)
  print(markdown(rows, unc_ms, args.margin))
  if args.json:
    with open(args.json, "w") as f:
      json.dump({"files": args.files, "uncertainty_ms": unc_ms, "margin": args.margin, "rows": rows}, f, indent=2)

  bad = {"MISSING", "FAIL"} | ({"LOW MARGIN"} if args.strict else set())
  return 1 if any(r["verdict"] in bad for r in rows) else 0


if __name__ == "__main__":
  sys.exit(main())
