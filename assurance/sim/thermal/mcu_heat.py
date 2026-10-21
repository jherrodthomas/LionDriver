#!/usr/bin/env python3
"""The panda's safety MCU next to the SoC (WP-A-03 DFI-04, WP-S-02 TSR-509, WP-H-01 HWSR-509).

DFI-04: SoC heat in a sun-loaded enclosure raises the MCU's temperature, so both may leave their range together.
The device heat model (`heat.py`, the box of `params.yaml`) already carries the MCU as a source beside the SoC. Here
it runs steady (the end of a long drive) against the cabin air, in three set-ups: as built, with the SoC's heat
taken away (how much of the MCU's warmth is the SoC's), and with the fan stalled (HWSR-509a). The MCU's junction is
its block in the model plus its own power through the package to the board (P·ΘJB, DS13311).

Against the part's limits it answers: when the SoC reaches the 96 °C at which the host stops (`hardwared.py`), how hot
is the MCU's junction; and what trip point would TSR-509 need, given the DTS's accuracy, to act before the junction
leaves its range without tripping on a hot day inside the ODD. Writes `../results/mcu-heat.json` and `.md`.

    python3 mcu_heat.py --figures
    python3 mcu_heat.py --check

Estimated inputs until T1; synthetic (DSR-12), design aid, no evidence credit (DQ-413).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from thermal_pilot import PARAMS, bands, build, compare, refs  # noqa: E402

CABIN_DEVICE = HERE.parent / "results" / "cabin-device.json"
CABIN_SOAK = HERE.parent / "results" / "cabin-soak.json"
OUT_JSON = HERE.parent / "results" / "mcu-heat.json"
OUT_MD = HERE.parent / "results" / "mcu-heat.md"
SETUPS = {"as_built": "As built: fan at 100 %", "soc_off": "SoC's heat taken away", "fan_stalled": "Fan stalled"}


def fan_still_scale(p: dict) -> float:
  """The fan face's conductance with the fan stopped: natural convection, as the other faces (cabin_drive.py)."""
  size = p["device"]["size"]["value"]
  return p["boundaries"]["rear"]["h"] * size[1] * size[2] / p["boundaries"]["fan"]["conductance"]


def sweep(p: dict, setup: str) -> dict:
  scale = {"soc_off": {"soc_power": 0.0}, "fan_stalled": {"fan_conductance": fan_still_scale(p)}}.get(setup, {})
  m = build(p, scale)
  soc, mcu = [], []
  for a in p["mcu"]["air"]:
    T = m.steady(refs(p, a))
    soc.append(float(m.region_max("soc")(T)))
    mcu.append(float(m.region_mean("mcu")(T)))
  return {"soc": soc, "mcu_block": mcu}


def at(xs, ys, x):
  return float(np.interp(x, xs, ys))


def crossing(xs, ys, y):
  """x where a rising, straight ys reaches y (steady conduction is linear in the cabin air, so this is exact)."""
  k = np.polyfit(xs, ys, 1)
  return float((y - k[1]) / k[0])


def run(p: dict) -> dict:
  mc = p["mcu"]
  air = mc["air"]
  limit = bands()["comma 3X"]["overheated_above"]
  rise = {e: mc["die_power"][e if e != "nominal" else "value"] * mc["theta_jb"][t]
          for e, t in (("low", "low"), ("high", "high"))}
  rise_nom = mc["die_power"]["value"] * (mc["theta_jb"]["low"] + mc["theta_jb"]["high"]) / 2
  out = {"about": "Synthetic (DSR-12), design aid, no evidence credit (DQ-413). Estimated inputs until T1.",
         "air": air, "soc_limit": limit, "junction_rise_k": {"low": round(rise["low"], 2),
                                                              "nominal": round(rise_nom, 2),
                                                              "high": round(rise["high"], 2)},
         "setups": {}}
  for s in SETUPS:
    d = sweep(p, s)
    out["setups"][s] = {"soc": [round(v, 2) for v in d["soc"]], "mcu_block": [round(v, 2) for v in d["mcu_block"]]}
  b, off = out["setups"]["as_built"], out["setups"]["soc_off"]
  share = [(m - o) / (m - a) for m, o, a in zip(b["mcu_block"], off["mcu_block"], air, strict=True)]
  out["soc_share_of_mcu_rise"] = round(float(np.mean(share)), 3)
  out["soc_adds_k"] = round(float(np.mean(np.array(b["mcu_block"]) - np.array(off["mcu_block"]))), 2)
  stop = {}
  for s in ("as_built", "fan_stalled"):
    d = out["setups"][s]
    a_stop = crossing(air, d["soc"], limit)
    blk = at(air, d["mcu_block"], a_stop) if air[0] <= a_stop <= air[-1] else \
      float(np.polyval(np.polyfit(air, d["mcu_block"], 1), a_stop))
    a_mcu = crossing(air, np.array(d["mcu_block"]) + rise["high"], mc["tj_max"]["industrial"])
    stop[s] = {"air_at_soc_limit": round(a_stop, 1), "mcu_block": round(blk, 1),
               "tj_low": round(blk + rise["low"], 1), "tj_high": round(blk + rise["high"], 1),
               "air_at_mcu_limit": round(a_mcu, 1)}
  out["at_soc_limit"] = stop
  # TSR-509: the DTS may read 7 K (+1 K supply) low, so a reading of TJmax − 8 K is the last that still guarantees
  # the junction is inside; it may read 2 K (+1 K) high, which eats into the margin to a hot day in the ODD.
  e = mc["dts_error_k"]
  hot = json.loads(CABIN_DEVICE.read_text(encoding="utf-8"))["scenarios"]
  hottest = max(v["mcu_peak"] for v in hot.values())
  thr = {}
  for grade in ("industrial", "extended"):
    trip = mc["tj_max"][grade] + e["low"] - e["supply"]
    highest_reading = hottest + rise["high"] + e["high"] + e["supply"]
    thr[grade] = {"tj_max": mc["tj_max"][grade], "trip_at_most": round(trip, 1),
                  "hot_day_highest_reading": round(highest_reading, 1),
                  "margin_k": round(trip - highest_reading, 1)}
  out["tsr509"] = {"hot_drive_mcu_block_peak": hottest, "grades": thr}
  soak = json.loads(CABIN_SOAK.read_text(encoding="utf-8"))["scenarios"]
  out["parked_mount_air_max"] = max(v["park_end"]["mount"] for v in soak.values())
  return out


def markdown(r: dict, p: dict) -> str:
  mc = p["mcu"]
  st, t5 = r["at_soc_limit"], r["tsr509"]
  ind, ext = t5["grades"]["industrial"], t5["grades"]["extended"]
  soak = r["parked_mount_air_max"]
  i35 = r["air"].index(35.0)
  L = [
    "# The safety MCU next to the SoC: DFI-04 and a TSR-509 trip point",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`thermal/mcu_heat.py`](../thermal/mcu_heat.py) from the device heat model's [`params.yaml`](../thermal/params.yaml); "
    "do not edit by hand. **The device's inputs are estimates** until T1; the MCU's limits are the datasheet's "
    f"({mc['part']['value']}, DS13311).",
    "",
    "Steady state (the end of a long drive), the windshield 15 K above the cabin air and the sun on the device, as the "
    f"pilot. The junction is the MCU's block in the model plus {r['junction_rise_k']['low']:.0f}–"
    f"{r['junction_rise_k']['high']:.0f} K through its package (the package is not yet known).",
    "",
    "## How much of the MCU's warmth is the SoC's (DFI-04)",
    "",
    "| Cabin air | MCU block, as built | With the SoC's heat taken away | Fan stalled |",
    "|---|---|---|---|",
  ]
  for i, a in enumerate(r["air"]):
    if a in (25.0, 35.0, 45.0, 55.0, 65.0):
      L.append(f"| {a:.0f} °C | {r['setups']['as_built']['mcu_block'][i]:.1f} °C | "
               f"{r['setups']['soc_off']['mcu_block'][i]:.1f} °C | {r['setups']['fan_stalled']['mcu_block'][i]:.1f} °C |")
  L += [
    "",
    f"The SoC's heat lifts the MCU by about **{r['soc_adds_k']:.0f} K**, {100 * r['soc_share_of_mcu_rise']:.0f} % of its "
    "rise above the cabin air; the rest is its own power, the rest of the board and the sun. The coupling DFI-04 "
    "names is real.",
    "",
    "## When the SoC reaches its limit",
    "",
    f"The host stops above {r['soc_limit']:.0f} °C on the SoC (`hardwared.py`). The MCU's junction at that moment:",
    "",
    "| Set-up | Cabin air when the SoC reaches its limit | MCU junction then | Cabin air at which the MCU would reach "
    f"{mc['tj_max']['industrial']:.0f} °C (hottest package) |",
    "|---|---|---|---|",
  ]
  for s in ("as_built", "fan_stalled"):
    d = st[s]
    L.append(f"| {SETUPS[s]} | {d['air_at_soc_limit']:.0f} °C | {d['tj_low']:.0f}–{d['tj_high']:.0f} °C | "
             f"{d['air_at_mcu_limit']:.0f} °C |")
  L += [
    "",
    "## A trip point for TSR-509",
    "",
    f"The DTS may read up to {-mc['dts_error_k']['low']:.0f} K low (+{mc['dts_error_k']['supply']:.0f} K for the supply) and "
    f"{mc['dts_error_k']['high']:.0f} K high (+{mc['dts_error_k']['supply']:.0f} K). A trip point must sit low enough "
    "to act before the junction leaves its range, and high enough not to trip on the hottest drive inside the ODD "
    f"(the hot July day with the AC off: MCU block {t5['hot_drive_mcu_block_peak']:.0f} °C, "
    "[`cabin-device.md`](cabin-device.md)).",
    "",
    "| Part's temperature range | TJ max | Trip at a DTS reading of at most | Hottest ODD drive could read | Margin |",
    "|---|---|---|---|---|",
    f"| Industrial (suffix 6) | {ind['tj_max']:.0f} °C | {ind['trip_at_most']:.0f} °C | {ind['hot_day_highest_reading']:.0f} °C | {ind['margin_k']:.0f} K |",
    f"| Extended (suffix 3) | {ext['tj_max']:.0f} °C | {ext['trip_at_most']:.0f} °C | {ext['hot_day_highest_reading']:.0f} °C | {ext['margin_k']:.0f} K |",
    "",
    "## What this shows (generated)",
    "",
    f"- At {r['air'][i35]:.0f} °C cabin air the MCU block runs at {r['setups']['as_built']['mcu_block'][i35]:.0f} °C; "
    f"about {r['soc_adds_k']:.0f} K of it is the SoC's.",
    f"- When the SoC reaches its limit, the MCU's junction is at {st['as_built']['tj_low']:.0f}–"
    f"{st['as_built']['tj_high']:.0f} °C as built and {st['fan_stalled']['tj_low']:.0f}–{st['fan_stalled']['tj_high']:.0f} °C "
    f"with the fan stalled: below the industrial grade's {ind['tj_max']:.0f} °C. While the host runs its thermal "
    "policy, the SoC limit is reached first and the MCU is still in range. Without it (a hung host still drawing power), "
    f"the MCU would leave its range only at about {st['as_built']['air_at_mcu_limit']:.0f} °C cabin air as built, or "
    f"{st['fan_stalled']['air_at_mcu_limit']:.0f} °C with the fan stalled, close to the {soak:.0f} °C the mount air "
    "reaches parked on a hot July day ([`cabin-soak.md`](cabin-soak.md)). Two faults together, but the case TSR-509 "
    "is for.",
    "- That protection depends on the host. TSR-509 asks the MCU to act on its own DTS, and the numbers leave room "
    f"for it: a trip at a reading of about {ind['trip_at_most']:.0f} °C or below (industrial part) keeps "
    f"{ind['margin_k']:.0f} K from the hottest drive in the ODD. A candidate for the HWSR-509 owner; the part's suffix "
    "and package (T1) and the device's own logs of `temperature_pkt` settle it.",
    "",
  ]
  return "\n".join(L)


def main(argv):
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("--check", action="store_true")
  ap.add_argument("--figures", action="store_true")
  a = ap.parse_args(argv[1:])
  p = yaml.safe_load(PARAMS.read_text(encoding="utf-8"))
  r = run(p)
  md = markdown(r, p)
  if a.check:
    errs = compare(r, json.loads(OUT_JSON.read_text(encoding="utf-8")))
    if not errs and OUT_MD.read_text(encoding="utf-8") != md:
      errs.append(f"{OUT_MD.name} is stale: run mcu_heat.py")
    for e in errs[:20]:
      print("FAIL", e)
    print("mcu heat:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, indent=1) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name, r["soc_adds_k"], r["soc_share_of_mcu_rise"], r["at_soc_limit"], r["tsr509"])
  if a.figures:
    import figures
    figures.mcu_figure(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
