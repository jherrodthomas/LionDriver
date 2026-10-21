#!/usr/bin/env python3
"""Device heat model, TE-04 pilot: the comma device behind a sun-loaded windshield during a drive.

Builds the 3D box of `params.yaml`, runs a 60 min drive per cabin air temperature, sweeps the cabin temperature with
one-at-a-time parameter variations, and finds where the peak SoC temperature reaches the code's overheat band
(read from `openpilot/system/hardware/hardwared.py`). Writes `../results/thermal-pilot.json` and `.md`; with
`--figures`, renders the figures (PyVista off-screen, matplotlib) into `figures/`.

    python3 thermal_pilot.py --figures   # write results and figures
    python3 thermal_pilot.py --check     # CI: fail if a fresh run differs from the committed results

Runs in the environment of `thermal-linux-64.lock`. Every input is an estimate until step T1 (params.yaml):
the numbers show what the model does, not what the device does.
Synthetic (DSR-12), design aid, no evidence credit (DQ-412).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from heat import Box, Face, Model  # noqa: E402

PARAMS = HERE / "params.yaml"
HARDWARED = ROOT / "openpilot" / "system" / "hardware" / "hardwared.py"
OUT_JSON = HERE.parent / "results" / "thermal-pilot.json"
OUT_MD = HERE.parent / "results" / "thermal-pilot.md"
FIG = HERE / "figures"
CELLS = (48, 24, 10)
TOL_K = 0.05
FACES = {"x0": (0, 0), "x1": (0, 1), "y0": (1, 0), "y1": (1, 1), "z0": (2, 0), "z1": (2, 1)}


def bands() -> dict:
  """The comma 3X (tici) and comma four (mici) thermal bands, as the code has them."""
  src = HARDWARED.read_text(encoding="utf-8")
  blocks = re.findall(r"THERMAL_BANDS = OrderedDict\(\{(.*?)\}\)", src, re.S)
  out = {}
  for name, blk in zip(("comma four", "comma 3X"), blocks, strict=False):
    ok = re.search(r"ok: ThermalBand\(None, ([\d.]+)\)", blk)
    ov = re.search(r"overheated: ThermalBand\(([\d.]+), ([\d.]+)\)", blk)
    out[name] = {"overheated_above": float(ok.group(1)), "ok_again_below": float(ov.group(1))}
  if len(out) != 2:
    raise SystemExit(f"could not read the thermal bands from {HARDWARED}")
  return out


def build(p: dict, scale: dict | None = None, cells=CELLS) -> Model:
  s = {"soc_power": 1.0, "fan_conductance": 1.0, "conductivity": 1.0, "irradiance": 1.0} | (scale or {})
  dev, sun = p["device"], p["sun"]
  size = tuple(dev["size"]["value"])
  area = {"x": size[1] * size[2], "y": size[0] * size[2], "z": size[0] * size[1]}
  flux = sun["irradiance"]["value"] * s["irradiance"] * sun["glass_transmittance"]["value"] * sun["absorptance"]["value"]
  faces = []
  for name, b in p["boundaries"].items():
    axis, side = FACES[b["face"]]
    h = b["h"] if "h" in b else b["conductance"] * s["fan_conductance"] / area[b["face"][0]]
    faces.append(Face(name, axis, side, h, b["ref"], flux if name == "front" else 0.0))
  src = p["sources"]
  sources = {n: (src[n]["centre"], src[n]["size"], src[n]["power"] * (s["soc_power"] if n == "soc" else 1.0))
             for n in ("soc", "mcu")}
  return Model(Box(size=size, cells=cells, k=dev["conductivity"]["value"] * s["conductivity"],
                   rho_c=dev["heat_capacity"]["value"], faces=faces, sources=sources,
                   uniform_power=src["rest"]["power"]))


def refs(p: dict, air: float) -> dict:
  return {"air": air, "glass": air + p["sun"]["glass_above_air"]["value"]}


def drive(model: Model, p: dict, air: float, every: int = 1):
  d = p["drive"]
  return model.transient(refs(p, air), d["duration"], d["step"], air + d["soak_above_air"]["value"],
                         [model.region_max("soc"), model.region_mean("mcu")], every=every)


def crossing(xs, ys, limit):
  """Lowest x where y reaches the limit, by linear interpolation; None if it never does in the sweep."""
  for i in range(1, len(xs)):
    if ys[i - 1] < limit <= ys[i]:
      return xs[i - 1] + (limit - ys[i - 1]) * (xs[i] - xs[i - 1]) / (ys[i] - ys[i - 1])
  return xs[0] if ys[0] >= limit else None


def run(p: dict) -> tuple[dict, dict]:
  b = bands()
  limit = b["comma 3X"]["overheated_above"]
  air = p["sweep"]["air"]
  variants = [("nominal", {})] + [(f"{k} x{v}", {k: v}) for k, vs in p["uncertainty"].items() for v in vs]
  sweep, keep = {}, {}
  for name, sc in variants:
    m = build(p, sc)
    rows = []
    for a in air:
      t, y, snaps = drive(m, p, a)
      rows.append({"air": a, "soc_peak": round(float(y[:, 0].max()), 2), "mcu_at_end": round(float(y[-1, 1]), 2)})
      if name == "nominal" and a in p["sweep"]["plot"]:
        cross = crossing(list(t), list(y[:, 0]), limit)
        keep[a] = {"t_min": [round(v / 60, 2) for v in t], "soc": [round(float(v), 2) for v in y[:, 0]],
                   "mcu": [round(float(v), 2) for v in y[:, 1]],
                   "crosses_at_min": None if cross is None else round(cross / 60, 1)}
    sweep[name] = rows
  nominal = [r["soc_peak"] for r in sweep["nominal"]]
  worst = [max(sweep[n][i]["soc_peak"] for n in sweep) for i in range(len(air))]
  best = [min(sweep[n][i]["soc_peak"] for n in sweep) for i in range(len(air))]
  b_nom, b_worst = crossing(air, nominal, limit), crossing(air, worst, limit)
  m = build(p)
  m.steady(refs(p, 45.0))
  power = m.source_power() + sum(f.flux for f in m.box.faces) * p["device"]["size"]["value"][0] * p["device"]["size"]["value"][1]
  balance = abs(m.boundary_loss(refs(p, 45.0)) - m.source_power()) / power
  res = {
    "about": "Synthetic (DSR-12), design aid, no evidence credit (DQ-412). Inputs are estimates until T1.",
    "bands": b, "limit_used": limit, "cells": list(CELLS), "dofs": int(m.V.dofmap.index_map.size_global),
    "energy_balance_rel": float(f"{balance:.1e}"),
    "drives": {str(a): v for a, v in keep.items()},
    "sweep": {"air": air, "nominal": nominal, "band_low": best, "band_high": worst, "variants": sweep},
    "bound": {"nominal": None if b_nom is None else round(b_nom, 1),
              "worst_edge": None if b_worst is None else round(b_worst, 1),
              "worst_variant": max(sweep, key=lambda n: max(r["soc_peak"] for r in sweep[n]))},
  }
  return res, {"model": m}


def fmt(v, unit=" °C"):
  return "—" if v is None else f"{v:.1f}{unit}"


def markdown(r: dict) -> str:
  s, bnd = r["sweep"], r["bound"]
  lines = [
    "# Device heat model: the comma device behind a sun-loaded windshield (TE-04 pilot)",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-412).** Generated by "
    "[`thermal/thermal_pilot.py`](../thermal/thermal_pilot.py) from [`params.yaml`](../thermal/params.yaml); "
    "do not edit by hand. **Every input is an estimate until step T1** (device measured, power from the device "
    "logs), so these numbers show what the model does, not what the device does.",
    "",
    f"Overheat limit used: SoC above **{r['limit_used']:.0f} °C** puts the comma 3X in `overheated`, which "
    "soft-disables LionDriver (`openpilot/system/hardware/hardwared.py`, read by the script; comma four: "
    f"{r['bands']['comma four']['overheated_above']:.0f} °C). Mesh {r['cells'][0]}×{r['cells'][1]}×{r['cells'][2]} "
    f"hexahedra, {r['dofs']} unknowns; energy balance closes to {r['energy_balance_rel']:.0e} of the heat in.",
    "",
    "## Peak SoC temperature in a 60 min drive, by cabin air temperature at the mount",
    "",
    "| Cabin air | Nominal | Band (one-at-a-time variations) | MCU at the end, nominal |",
    "|---|---|---|---|",
  ]
  for i, a in enumerate(s["air"]):
    lines.append(f"| {a:.0f} °C | {s['nominal'][i]:.1f} °C | {s['band_low'][i]:.1f} – {s['band_high'][i]:.1f} °C | "
                 f"{s['variants']['nominal'][i]['mcu_at_end']:.1f} °C |")
  lines += [
    "",
    "## Candidate ambient bound (for WP-C-02 OI-3, not the bound itself)",
    "",
    f"- Nominal: the SoC reaches {r['limit_used']:.0f} °C at {fmt(bnd['nominal'])} cabin air.",
    f"- Worst edge of the band: {fmt(bnd['worst_edge'])} (driven by `{bnd['worst_variant']}`). "
    "A candidate is read from the worst edge, never the nominal line.",
    "- It becomes a number the ODD can use only after a measured hot drive confirms the model (T4, DQ-411); "
    "the bound itself is set in WP-C-02 by the lead.",
    "",
    "## Drives",
    "",
    "| Cabin air | SoC after 60 min | Crosses the limit at | MCU after 60 min |",
    "|---|---|---|---|",
  ]
  for a, d in r["drives"].items():
    lines.append(f"| {float(a):.0f} °C | {d['soc'][-1]:.1f} °C | "
                 f"{'—' if d['crosses_at_min'] is None else str(d['crosses_at_min']) + ' min'} | {d['mcu'][-1]:.1f} °C |")
  lines += ["", "Checks behind these numbers: [`thermal/test_thermal.py`](../thermal/test_thermal.py) "
            "(analytic slab, lumped transient, FiPy cross-check, mesh study).", ""]
  return "\n".join(lines)


def compare(new: dict, old: dict, path="") -> list[str]:
  errs = []
  if isinstance(new, dict):
    for k in set(new) | set(old):
      if k not in new or k not in old:
        errs.append(f"{path}/{k}: missing")
      else:
        errs += compare(new[k], old[k], f"{path}/{k}")
  elif isinstance(new, list):
    if len(new) != len(old):
      return [f"{path}: length {len(new)} != {len(old)}"]
    for i, (a, b) in enumerate(zip(new, old, strict=True)):
      errs += compare(a, b, f"{path}[{i}]")
  elif isinstance(new, float) and isinstance(old, (int, float)) and path != "/energy_balance_rel":
    if abs(new - old) > TOL_K:
      errs.append(f"{path}: {new} != {old}")
  elif path == "/energy_balance_rel":
    if new > 1e-6:
      errs.append(f"{path}: {new} above 1e-6")
  elif new != old:
    errs.append(f"{path}: {new!r} != {old!r}")
  return errs


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("--check", action="store_true")
  ap.add_argument("--figures", action="store_true")
  a = ap.parse_args(argv[1:])
  p = yaml.safe_load(PARAMS.read_text(encoding="utf-8"))
  res, ctx = run(p)
  md = markdown(res)
  if a.check:
    old = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    errs = compare(res, old)
    if OUT_MD.read_text(encoding="utf-8") != md and not errs:
      errs.append(f"{OUT_MD.name} is stale: run thermal_pilot.py")
    for e in errs[:20]:
      print("FAIL", e)
    print("thermal pilot:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print(f"wrote {OUT_JSON.name}, {OUT_MD.name}; bound nominal {res['bound']['nominal']}, worst {res['bound']['worst_edge']}")
  if a.figures:
    import figures
    figures.render(p, res, FIG)
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
