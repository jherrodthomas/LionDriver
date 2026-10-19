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
# scenario families of WP-V-02 §5.3.2; scenarios the section does not assign are marked so, not guessed
FAMILY = {"KS-01": "SF-1", "KS-08": "SF-2", "KS-05": "SF-3", "KS-09": "SF-3", "KS-07": "SF-4", "KS-25": "SF-6", "KS-27": "SF-3"}
DT = 0.05
LANE_HALF = generate.LANE_W / 2


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
def check(sc_id: str, p: dict, R: dict[str, list[dict]], road: dict | None = None) -> list[tuple[str, bool, str]]:
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
  if sc_id == "KS-27":
    ld, r = R["lead"], road or generate.SCENARIOS_BY_ID["KS-27"].road
    rp, rw = r["radius"] + LANE_HALF, r["radius"] - r["wall"]["t"]
    lo, hi = r["reveal"]
    arc0 = r["straight"] + r["clothoid"]

    def visible(e, l):
      # both on the arc: the chord between the lane-centre points clears the wall circle (reference-line s)
      th = (l["s"] - e["s"]) / r["radius"]
      return rp * math.cos(th / 2) >= rw
    pairs = [(e, at(ld, e["time"])) for e in ego if e["s"] >= arc0]
    first = next(((e, l) for e, l in pairs if visible(e, l)), None)
    gap = None if first is None else (first[1]["s"] - first[0]["s"]) / r["radius"] * rp
    target = p["EgoSpeed"] + p["SetSpeedDelta"]
    return [(f"lead hidden until a gap of {lo:g}–{hi:g} m along the lane", bool(pairs) and not visible(*pairs[0])
             and gap is not None and lo <= gap <= hi, "never visible" if gap is None else f"{gap:.1f} m"),
            ("ego reaches EgoSpeed + SetSpeedDelta", abs(ego[-1]["speed"] - target) < 0.01, f"{ego[-1]['speed']:.2f} m/s"),
            ("lead keeps LeadSpeed in lane -1", all(abs(x["speed"] - p["LeadSpeed"]) < 1e-6 for x in ld) and lane_always(ld, -1), "")]
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
  rows = ["| Scenario | Family | Parameter point | Check | Result | Measured |", "|---|---|---|---|---|---|"]
  failures = 0
  for sc in generate.SCENARIOS:
    for fid, road in generate.files_of(sc):
      for p in points(sc):
        R = run(bin_dir, fid, p)
        changed = ", ".join(f"{k} = {v:g}" for k, v in p.items() if v != sc.params[k][0]) or "defaults"
        for name, ok, measured in check(sc.id, p, R, road):
          failures += not ok
          fam = FAMILY.get(sc.id, "not assigned in WP-V-02 §5.3.2")
          rows.append(f"| {fid} | {fam} | {changed} | {name} | {'pass' if ok else '**fail**'} | {measured or '—'} |")
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
    "| Label (WP-V-02 §5.3.5) | Value |",
    "|---|---|",
    "| data_kind | synthetic |",
    f"| simulator | esmini {generate_esmini_version()} (Linux release; archive SHA-256 `{esmini_sha()}`), default "
    "controllers; scenario files from scenariogeneration |",
    "| asset archive hash | none (headless, nothing rendered) |",
    "| scenario ID and family | per row below |",
    "| fidelity-case status | none |",
    "| credit | none |",
    "| camera frame rate | not applicable (no camera) |",
    "",
    "Each scenario runs at its defaults and at each sweep value of one parameter at a time.",
    "",
  ]
  return "\n".join(head) + "\n" + body + "\n"


def esmini_sha() -> str:
  from fetch_esmini import SHA256
  return SHA256[:12]


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
