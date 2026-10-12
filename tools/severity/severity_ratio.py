#!/usr/bin/env python3
"""P(severity class) from FARS and CRSS (LionDriver WP-V-02 §3.5).

For each collision type, road class and speed-limit band this script computes:

  P(fatal | crash)  = FARS fatal crashes / CRSS estimated crashes
  P(injury | crash) = CRSS estimated injury crashes / CRSS estimated crashes

with a one-sided upper confidence bound. FARS is a census and has no sampling error, so
the fatal-ratio bound uses the lower bound of the CRSS total. The injury ratio uses the
Taylor-linearised standard error of a ratio. CRSS variances use the stratified cluster
design: PSUs within strata, sampled with replacement. A cell with too few CRSS cases or
strata with a single PSU is reported, and its bound falls back to 1 (WP-V-02 §3.5 item 3).

It then summarises per SOTIF hazard (SH): the largest upper bound over the hazard's
collision types and the speed-limit bands of the claimed ODD. That is the value WP-V-02
§3.5 uses, and every input row is printed so the value can be reviewed.

VERIFY BEFORE USE. The variable names and codes in CODES and DESIGN below are taken
from the FARS and CRSS analytical user's manuals as remembered, not checked against a
specific release. Check each one against the manual of the release year you load, and
record the check with the result (WP-V-02 §3.5 item 4).

Usage:
  tools/severity/severity_ratio.py --fars FARS2022NationalCSV/ --crss CRSS2022CSV/ \
      --json severity-2022.json
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field

# --- Codes to verify per release year (see module docstring) -----------------------------

CODES = {
  # MAN_COLL: manner of collision of the first harmful event with a motor vehicle in transport
  "collision": {
    "rear_end": {"MAN_COLL": {1}},
    "head_on": {"MAN_COLL": {2}},
    "angle": {"MAN_COLL": {6}},
    "sideswipe_same": {"MAN_COLL": {7}},
    "sideswipe_opposite": {"MAN_COLL": {8}},
    # Not a collision with a motor vehicle: identified by the first harmful event
    "pedestrian": {"MAN_COLL": {0}, "HARM_EV": {8}},
    "pedalcyclist": {"MAN_COLL": {0}, "HARM_EV": {9}},
    # Roadside barrier as first harmful event (lane departure into a barrier, HE-01.2):
    # 20 impact attenuator/crash cushion, 23 bridge rail, 24 guardrail face, 25 concrete traffic
    # barrier, 26 other traffic barrier, 52 guardrail end, 57 cable barrier
    "barrier": {"MAN_COLL": {0}, "HARM_EV": {20, 23, 24, 25, 26, 52, 57}},
  },
  # Interstate flag: FARS ROUTE (1 = Interstate); CRSS INT_HWY (1 = yes)
  "interstate": {"FARS": ("ROUTE", {1}), "CRSS": ("INT_HWY", {1})},
  # CRSS MAX_SEV (KABCO): 1 C possible, 2 B minor, 3 A serious, 4 K fatal, 5 injured unknown severity,
  # 6 died prior to crash (excluded)
  "injury_max_sev": {1, 2, 3, 4, 5},
  # VSPD_LIM in the vehicle file: posted limit in mph; these values mean "no limit / unknown"
  "speed_unknown": {0, 98, 99},
}

DESIGN = {"weight": "WEIGHT", "stratum": "PSUSTRAT", "psu": "PSU_VAR"}

# Speed-limit bands in mph (inclusive), road class per ODD part (WP-C-02 §3.1)
BANDS = [(0, 35), (40, 45), (50, 55), (60, 65), (70, 85)]
ODD = {
  "ODD-H": {"interstate": True, "bands": [(60, 65), (70, 85)]},
  "ODD-A": {"interstate": False, "bands": [(40, 45), (50, 55)]},
}

# Collisions per SH (WP-V-02 §3.5 item 2).
SH_COLLISIONS = {
  # SH-01/02 head-on (OS-03, no reaction, full closing speed) is on the curve of risk_curve.py
  "SH-01": ["sideswipe_same", "barrier"],
  "SH-02": ["sideswipe_same", "barrier"],
  "SH-03": ["rear_end"],
  "SH-04": ["rear_end"],
  "SH-06": ["rear_end"],
  "SH-10": ["sideswipe_same"],
  # SH-11 (VRU, no braking) is on the pedestrian curve of risk_curve.py, not this ratio
  # (WP-V-02 §3.5 item 3); its pedestrian and pedalcyclist cells are still reported.
}

MIN_CASES = 30  # unweighted CRSS cases per cell below which the bound falls back to 1


# --- Reading ---------------------------------------------------------------------------

def _find(directory: str, name: str) -> str:
  for f in os.listdir(directory):
    if f.lower() == name:
      return os.path.join(directory, f)
  raise SystemExit(f"{name} not found in {directory}")


def _rows(path: str):
  with open(path, newline="", encoding="latin-1") as f:
    yield from csv.DictReader(f)


def _int(v) -> int | None:
  try:
    return int(float(v))
  except (TypeError, ValueError):
    return None


def max_speed_limits(vehicle_csv: str) -> dict[str, int]:
  """Highest known posted limit over the vehicles of each crash (key ST_CASE or CASENUM)."""
  out: dict[str, int] = {}
  for r in _rows(vehicle_csv):
    key = r.get("ST_CASE") or r.get("CASENUM")
    lim = _int(r.get("VSPD_LIM"))
    if key is None or lim is None or lim in CODES["speed_unknown"]:
      continue
    out[key] = max(out.get(key, 0), lim)
  return out


def collision_type(r: dict) -> str | None:
  for name, rule in CODES["collision"].items():
    if all(_int(r.get(var)) in vals for var, vals in rule.items()):
      return name
  return None


def band_of(limit: int | None) -> tuple[int, int] | None:
  if limit is None:
    return None
  for lo, hi in BANDS:
    if lo <= limit <= hi:
      return (lo, hi)
  return None


def _cell(r: dict, source: str, limits: dict[str, int]):
  key = r.get("ST_CASE") or r.get("CASENUM")
  ctype = collision_type(r)
  var, vals = CODES["interstate"][source]
  band = band_of(limits.get(key))
  if ctype is None or band is None:
    return None
  return (ctype, _int(r.get(var)) in vals, band)


# --- Estimation --------------------------------------------------------------------------

@dataclass
class Cell:
  fars: int = 0
  cases: int = 0
  records: list = field(default_factory=list)  # (stratum, psu, weight, injury)


def load(fars_dir: str, crss_dir: str) -> dict:
  cells: dict = defaultdict(Cell)
  limits = max_speed_limits(_find(fars_dir, "vehicle.csv"))
  for r in _rows(_find(fars_dir, "accident.csv")):
    c = _cell(r, "FARS", limits)
    if c:
      cells[c].fars += 1
  limits = max_speed_limits(_find(crss_dir, "vehicle.csv"))
  for r in _rows(_find(crss_dir, "accident.csv")):
    missing = [v for v in DESIGN.values() if v not in r]
    if missing:
      raise SystemExit(f"CRSS accident file lacks design variables {missing}; check DESIGN against the manual")
    c = _cell(r, "CRSS", limits)
    if not c:
      continue
    w = float(r[DESIGN["weight"]])
    inj = 1.0 if _int(r.get("MAX_SEV")) in CODES["injury_max_sev"] else 0.0
    cells[c].cases += 1
    cells[c].records.append((r[DESIGN["stratum"]], r[DESIGN["psu"]], w, inj))
  return cells


def design_variance(records, value) -> tuple[float, bool]:
  """Variance of a weighted total: stratified PSUs sampled with replacement.

  value(record) is the per-record contribution before weighting. Returns the variance and
  whether a stratum had a single PSU (whose contribution cannot be estimated)."""
  psu_tot: dict = defaultdict(lambda: defaultdict(float))
  for rec in records:
    psu_tot[rec[0]][rec[1]] += rec[2] * value(rec)
  var, single = 0.0, False
  for psus in psu_tot.values():
    n = len(psus)
    if n < 2:
      single = True
      continue
    mean = sum(psus.values()) / n
    var += n / (n - 1) * sum((t - mean) ** 2 for t in psus.values())
  return var, single


def estimate(cell: Cell, z: float) -> dict:
  x = sum(r[2] for r in cell.records)
  y = sum(r[2] * r[3] for r in cell.records)
  var_x, single_x = design_variance(cell.records, lambda r: 1.0)
  out = {"fars_fatal_crashes": cell.fars, "crss_cases": cell.cases, "crss_crashes": x,
         "crss_crashes_se": math.sqrt(var_x), "crss_injury_crashes": y}
  reasons = []
  if cell.cases < MIN_CASES:
    reasons.append(f"fewer than {MIN_CASES} CRSS cases")
  if single_x:
    reasons.append("a stratum with a single PSU")
  if x <= 0:
    reasons.append("no CRSS crashes")
  if reasons:
    out.update(p_fatal=None, p_fatal_ub=1.0, p_injury=None, p_injury_ub=1.0, fallback="; ".join(reasons))
    return out
  lower_x = x - z * math.sqrt(var_x)
  out["p_fatal"] = cell.fars / x
  out["p_fatal_ub"] = 1.0 if lower_x <= 0 else min(1.0, cell.fars / lower_x)
  ratio = y / x
  var_r, _ = design_variance(cell.records, lambda r: r[3] - ratio)
  out["p_injury"] = ratio
  out["p_injury_ub"] = min(1.0, ratio + z * math.sqrt(var_r) / x)
  out["fallback"] = None
  return out


def by_sh(results: dict) -> list[dict]:
  rows = []
  for sh, ctypes in SH_COLLISIONS.items():
    for odd, spec in ODD.items():
      cells = [(c, results.get((c, spec["interstate"], b))) for c in ctypes for b in spec["bands"]]
      ub_f = max((r["p_fatal_ub"] if r else 1.0) for _, r in cells)
      ub_i = max((r["p_injury_ub"] if r else 1.0) for _, r in cells)
      rows.append({"sh": sh, "odd": odd, "collisions": ctypes, "p_fatal_ub": ub_f, "p_injury_ub": ub_i,
                   "missing_cells": sum(1 for _, r in cells if r is None)})
  return rows


def _fmt(v) -> str:
  return "—" if v is None else f"{v:.2e}" if v < 0.01 else f"{v:.3f}"


def main(argv: list[str] | None = None) -> int:
  ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
  ap.add_argument("--fars", required=True, help="directory with FARS accident.csv and vehicle.csv")
  ap.add_argument("--crss", required=True, help="directory with CRSS accident.csv and vehicle.csv")
  ap.add_argument("--z", type=float, default=1.645, help="one-sided normal quantile (default 95 %%)")
  ap.add_argument("--json", help="write cell and per-SH results to this file")
  a = ap.parse_args(argv)

  results = {k: estimate(c, a.z) for k, c in load(a.fars, a.crss).items()}
  print("| Collision | Interstate | Limit (mph) | FARS fatal | CRSS cases | CRSS crashes | P(fatal) | UB | P(injury) | UB | Fallback |")
  print("|---|---|---|---|---|---|---|---|---|---|---|")
  for (ctype, inter, band), r in sorted(results.items()):
    cols = [ctype, "yes" if inter else "no", f"{band[0]}–{band[1]}", r["fars_fatal_crashes"], r["crss_cases"],
            f"{r['crss_crashes']:.0f}", _fmt(r["p_fatal"]), _fmt(r["p_fatal_ub"]), _fmt(r["p_injury"]),
            _fmt(r["p_injury_ub"]), r["fallback"] or ""]
    print("| " + " | ".join(str(c) for c in cols) + " |")
  summary = by_sh(results)
  print("\n| SH | ODD | Collisions | P(fatal) UB | P(injury) UB | Cells without data |\n|---|---|---|---|---|---|")
  for s in summary:
    print(f"| {s['sh']} | {s['odd']} | {', '.join(s['collisions'])} | {_fmt(s['p_fatal_ub'])} | {_fmt(s['p_injury_ub'])} | {s['missing_cells']} |")
  if a.json:
    with open(a.json, "w") as f:
      json.dump({"cells": [{"collision": k[0], "interstate": k[1], "band_mph": list(k[2]), **v} for k, v in sorted(results.items())],
                 "by_sh": summary, "codes": {k: str(v) for k, v in CODES.items()}, "design": DESIGN, "z": a.z}, f, indent=2)
  return 0


if __name__ == "__main__":
  sys.exit(main())
