#!/usr/bin/env python3
"""Replay every scenario file headless in esmini (MPL-2.0) and check that the scenario does what it says.

    python3 assurance/sim/scenarios/replay.py            # replay, write ../results/scenario-replay.md
    python3 assurance/sim/scenarios/replay.py --check    # fail if a replay fails or the committed table differs

Each scenario runs at its defaults and at each sweep value of one parameter at a time (the others at their defaults),
with a fixed 50 ms step, so the runs are deterministic. The checks are about the scenario, not the item: esmini's
default controller drives the ego, so a collision with a stopped vehicle, for example, is expected and says nothing
about LionDriver.

esmini: the pinned Linux release from fetch_esmini.py, or the directory in $ESMINI_BIN.
"""

from __future__ import annotations

import csv
import itertools
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import generate  # noqa: E402
from fetch_esmini import esmini_bin  # noqa: E402

TABLE = HERE.parent / "results" / "scenario-replay.md"
DT = 0.05


def run(bin_dir: Path, sc_id: str, params: dict) -> dict[str, list[dict]]:
  with tempfile.TemporaryDirectory() as tmp:
    dat = Path(tmp) / "run.dat"
    xosc = variant(sc_id, params, Path(tmp))
    cmd = [str(bin_dir / "esmini"), "--headless", "--osc", str(xosc), "--fixed_timestep",
           str(DT), "--record", str(dat), "--disable_stdout", "--logfile_path", str(Path(tmp) / "log.txt")]
    subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    subprocess.run([str(bin_dir / "dat2csv"), "--file", str(dat), "--extended"], check=True, capture_output=True,
                   timeout=60)
    log = (Path(tmp) / "log.txt").read_text(errors="replace")
    errors = [ln for ln in log.splitlines() if "[error]" in ln.lower()]
    if errors:
      raise RuntimeError(f"{sc_id} {params}: esmini reported errors: {errors[:3]}")
    rows: dict[str, list[dict]] = {}
    with open(dat.with_suffix(".csv"), newline="") as f:
      for r in csv.DictReader(f, skipinitialspace=True):
        rec = {k.strip(): v.strip() for k, v in r.items()}
        for k in ("time", "x", "y", "h", "s", "t", "offset", "speed"):
          rec[k] = float(rec[k])
        rec["laneId"] = int(rec["laneId"])
        rows.setdefault(rec["name"], []).append(rec)
    return rows


def variant(sc_id: str, params: dict, tmp: Path) -> Path:
  """A copy of the scenario file with the parameter defaults set to `params` (esmini 3.9 has no --param option)."""
  text = (HERE / "xosc" / f"{sc_id}.xosc").read_text(encoding="utf-8")
  text = text.replace(f'"../xodr/{sc_id}.xodr"', f'"{HERE / "xodr" / f"{sc_id}.xodr"}"')
  for k, v in params.items():
    text, n = re.subn(rf'(<ParameterDeclaration name="{k}" parameterType="double" value=")[^"]*(")', rf"\g<1>{v}\g<2>", text)
    if n != 1:
      raise ValueError(f"{sc_id}: parameter {k} not declared once")
  out = tmp / f"{sc_id}.xosc"
  out.write_text(text, encoding="utf-8")
  return out


def at(rows, t):
  return min(rows, key=lambda r: abs(r["time"] - t))


def lane_always(rows, lane):
  return all(r["laneId"] == lane for r in rows)


# ------------------------------------------------------------------------------------------------ checks per scenario
def check(sc_id: str, p: dict, R: dict[str, list[dict]]) -> list[tuple[str, bool, str]]:
  ego = R.get("ego", [])
  if sc_id == "KS-01":
    v = p["EgoSpeed"]
    steady = [r for r in ego if r["s"] > 400 + 50]
    rates = [(b["h"] - a["h"]) / DT for a, b in zip(steady, steady[1:]) if abs(b["h"] - a["h"]) < 1.0]
    ay = v * sum(rates) / len(rates)
    want = v * v / generate.R01
    return [("ego stays in lane -2", lane_always(ego, -2), ""),
            ("a_y = v²/R within 5 %", abs(ay - want) <= 0.05 * want, f"{ay:.2f} m/s² for {want:.2f}")]
  if sc_id == "KS-05":
    st = R["stopped"]
    off = st[-1]["offset"]
    return [("stationary vehicle at speed 0 in lane -2", all(r["speed"] == 0 for r in st) and lane_always(st, -2), ""),
            ("offset as set", abs(off - p["TargetOffset"]) < 0.01, f"{off:+.2f} m")]
  if sc_id == "KS-06":
    tr = R["truck"]
    gap = abs(at(tr, 10.0)["t"] - at(ego, 10.0)["t"])
    return [("truck stays in lane -3 alongside the ego", lane_always(tr, -3) and abs(at(tr, 10.0)["s"] - at(ego, 10.0)["s"]) < 0.5, ""),
            ("lane centres 3.3 m apart", abs(gap - 3.3) < 0.01, f"{gap:.2f} m")]
  if sc_id == "KS-07":
    c = R["cutin"]
    gap = at(c, 2.0)["s"] - at(ego, 2.0)["s"]
    return [("cut-in car in lane -2 at the end", c[-1]["laneId"] == -2, ""),
            ("gap at the start = CutInDistance within 0.5 m", abs(gap - p["CutInDistance"]) <= 0.5, f"{gap:.2f} m")]
  if sc_id == "KS-08":
    ld = R["lead"]
    braking = [r for r in ld if 3.2 <= r["time"] and r["speed"] > 0.5]
    decel = (braking[0]["speed"] - braking[-1]["speed"]) / (braking[-1]["time"] - braking[0]["time"])
    return [("lead decelerates at LeadDecel within 5 %", abs(decel - p["LeadDecel"]) <= 0.05 * p["LeadDecel"], f"{decel:.2f} m/s²"),
            ("lead stops in lane -2", ld[-1]["speed"] == 0 and lane_always(ld, -2), "")]
  if sc_id == "KS-09":
    ld, st = R["lead"], R["stopped"]
    start = next(r for r in ld if r["laneId"] != -2 or abs(r["offset"]) > 1e-3)   # first step of the lane change
    bumper = st[0]["s"] - start["s"] - 4.8
    return [("lead in lane -1 after the cut-out", ld[-1]["laneId"] == -1, ""),
            ("stopped vehicle at speed 0 in lane -2", all(r["speed"] == 0 for r in st) and lane_always(st, -2), ""),
            # the condition fires on the first step below the distance and the lane change moves from the next step:
            # up to two steps of travel
            ("cut-out starts at CutOutDistance (bumper to bumper), within two steps of travel",
             0 <= p["CutOutDistance"] - bumper <= 2 * p["EgoSpeed"] * DT, f"{bumper:.1f} m")]
  if sc_id == "KS-14":
    tg = R["target"]
    gap = (ego[0]["s"] - tg[0]["s"]) / p["EgoSpeed"]
    return [("ego in lane -3 after the lane change", ego[-1]["laneId"] == -3, ""),
            ("target-lane car at TargetGap behind", abs(gap - p["TargetGap"]) < 0.01, f"{gap:.2f} s")]
  if sc_id == "KS-23":
    ld = R["lead"]
    move = next((r["time"] for r in ld if r["speed"] > 0), None)
    return [("ego starts at standstill", ego[0]["speed"] == 0, ""),
            # the time condition fires on the first step after StandTime; the speed rises from the step after that
            ("lead leaves after StandTime (within 3 steps)", move is not None and 0 < move - p["StandTime"] <= 3 * DT,
             f"{move:.2f} s")]
  if sc_id == "KS-25":
    cross = next((r["time"] for r in ego if r["speed"] > 120 / 3.6), None)
    return [("ego speed crosses 120 km/h", cross is not None, "" if cross is None else f"at {cross:.2f} s")]
  raise ValueError(sc_id)


def points(sc) -> list[dict]:
  defaults = {k: v[0] for k, v in sc.params.items()}
  out = [defaults]
  for k, (default, sweep, *_r) in sc.params.items():
    for val in sweep:
      if val != default:
        out.append({**defaults, k: val})
  return out


def replay(bin_dir: Path) -> tuple[str, int]:
  rows = ["| Scenario | Parameter point | Check | Result | Measured |", "|---|---|---|---|---|"]
  failures = 0
  for sc in generate.SCENARIOS:
    for p in points(sc):
      R = run(bin_dir, sc.id, p)
      changed = ", ".join(f"{k} = {v:g}" for k, v in p.items() if v != sc.params[k][0]) or "defaults"
      for name, ok, measured in check(sc.id, p, R):
        failures += not ok
        rows.append(f"| {sc.id} | {changed} | {name} | {'pass' if ok else '**fail**'} | {measured or '—'} |")
  return "\n".join(rows), failures


def table(body: str) -> str:
  head = [
    "# Known scenarios: esmini replay",
    "",
    "> **Synthetic data (DSR-12).** Generated by [`scenarios/replay.py`](../scenarios/replay.py); do not edit by hand. "
    "It shows that each scenario file parses and plays as specified, headless, in esmini "
    f"{generate_esmini_version()} with a fixed 50 ms step. esmini's default controller drives the ego: **nothing here "
    "is about LionDriver's behaviour**, and nothing is evidence. Method: [README](../README.md) §2 and "
    "[scenarios](../scenarios/README.md).",
    "",
    "Each scenario runs at its defaults and at each sweep value of one parameter at a time.",
    "",
  ]
  return "\n".join(head) + body + "\n"


def generate_esmini_version() -> str:
  from fetch_esmini import VERSION
  return VERSION


def main(argv) -> int:
  bin_dir = esmini_bin()
  body, failures = replay(bin_dir)
  text = table(body)
  if failures:
    print(f"{failures} scenario check(s) failed", file=sys.stderr)
  if "--check" in argv:
    if not TABLE.exists() or TABLE.read_text(encoding="utf-8") != text:
      print(f"stale: {TABLE.name}; run: python3 assurance/sim/scenarios/replay.py", file=sys.stderr)
      return 1
    print("scenario replay: table current" + ("" if not failures else f", {failures} check(s) failed"))
    return 1 if failures else 0
  TABLE.write_text(text, encoding="utf-8")
  print(f"scenario replay: wrote {TABLE.name}, {failures} failure(s)")
  return 1 if failures else 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
