#!/usr/bin/env python3
"""Harness box v3 switch path (DFMEA DFM-010.C3, DFM-011.C2, DFM-014.C2, DFM-021.C1): a circuit to look at the four
box faults, as a Falstad link for review and an ngspice deck for the numbers.

One element list with drawing coordinates is the source of both. Falstad (CircuitJS) connects elements by their
coordinates; the ngspice deck is derived from the same coordinates, so the two circuits have the same topology and
values by construction. `check_falstad.mjs` then runs each scenario in Falstad headless and compares its node voltages
with the ngspice results committed here: two solvers, one circuit.

Three blocks, drawn side by side:
- **Switch drive** (HE-08): the device's 5 V drive on SBU1 against the 240 ohm pull-down R2/R3, and the DG419LE input
  threshold as a fraction of VL = VIN. Faults: pull-down open with SBU1 undriven, so IN floats on its leakage
  (DFM-010.C3); a threshold above the drive at high VIN (DFM-011.C2).
- **Ignition sense** (HE-10): Q6 pulls SBU2 low through R1 while ignition is on; the device reads SBU2 against 0.9 V.
  Fault: Q6 shorted, so ignition reads on with the car off (DFM-014.C2).
- **CAN clamp** (HB-04): a dominant CAN_H into the 60 ohm bus, with a degraded clamp diode D2 to GND (DFM-021.C1).

    python3 harness_box.py           # run ngspice, write ../results/harness-box.json, .md and the Falstad files
    python3 harness_box.py --check   # fail if a fresh run differs from the committed results

Parts are bands (`params.yaml`): the DG419LE threshold at VL = VIN, the device's SBU1 driver and SBU2 pull-up are not
published. Runs in the environment of ../supply/supply-linux-64.lock (ngspice 41, TL-58).
Synthetic (DSR-12), design aid, no evidence credit (DQ-413).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"
OUT_JSON = RESULTS / "harness-box.json"
OUT_MD = RESULTS / "harness-box.md"
FALSTAD_DIR = HERE / "falstad"
FALSTAD_URL = "https://www.falstad.com/circuit/circuitjs.html"
CLOSED_R = 1e-3          # ngspice: a closed switch (Falstad draws it as a wire)
TOL_V = 0.005            # --check and the Falstad comparison: within 5 mV
NODES = ("VIN", "VTH", "SBU1", "SBU2", "CANH")


@dataclass
class El:
  kind: str                      # rail, r, sw, g, w, lbl, text
  p1: tuple[int, int]
  p2: tuple[int, int]
  value: float = 0.0
  name: str = ""                 # switch id, label name or text
  closed: bool = True


@dataclass
class Scenario:
  id: str
  title: str
  fmea: str
  switches: dict[str, bool] = field(default_factory=dict)
  params: dict[str, float] = field(default_factory=dict)


def load_params(path: Path = HERE / "params.yaml") -> dict:
  return yaml.safe_load(path.read_text(encoding="utf-8"))


def values(p: dict, override: dict[str, float]) -> dict[str, float]:
  v = {
    "vin": p["vin"]["value"], "pull_down": p["pull_down"]["value"], "drive_v": p["drive"]["v"]["value"],
    "drive_r": p["drive"]["r_out"]["value"], "k": p["switch_input"]["threshold_fraction"]["value"],
    "leak_hi": p["switch_input"]["leak"]["value"], "leak_lo": p["switch_input"]["leak"]["value"],
    "r1": p["ignition_sense"]["r1"]["value"], "pu_v": p["ignition_sense"]["pull_up_v"]["value"],
    "pu_r": p["ignition_sense"]["pull_up_r"]["value"], "dom_v": p["can_clamp"]["dominant_v"]["value"],
    "rec_v": p["can_clamp"]["recessive_v"]["value"], "drv_r": p["can_clamp"]["driver_r"]["value"],
    "bus_r": p["can_clamp"]["bus_r"]["value"], "leak_r": p["can_clamp"]["leak_r"]["value"],
  }
  v.update(override)
  return v


def scenarios(p: dict) -> list[Scenario]:
  si, cc = p["switch_input"], p["can_clamp"]
  return [
    Scenario("intercept", "Device drives SBU1: intercept", "nominal", {"drive": True}),
    Scenario("pass_through", "SBU1 undriven: stock path", "nominal", {"drive": False}),
    Scenario("pulldown_open_leak_up", "Pull-down open, SBU1 undriven, IN leaks to VIN", "DFM-010.C3",
             {"drive": False, "pulldown": False}, {"leak_hi": si["leak"]["band"][0], "leak_lo": si["leak"]["band"][1]}),
    Scenario("pulldown_open_leak_down", "Pull-down open, SBU1 undriven, IN leaks to GND", "DFM-010.C3",
             {"drive": False, "pulldown": False}, {"leak_hi": si["leak"]["band"][1], "leak_lo": si["leak"]["band"][0]}),
    Scenario("threshold_high_vin_high", "Drive at the low band, threshold and VIN at the high band", "DFM-011.C2",
             {"drive": True}, {"vin": p["vin"]["band"][1], "k": si["threshold_fraction"]["band"][1],
                               "drive_v": p["drive"]["v"]["band"][0], "drive_r": p["drive"]["r_out"]["band"][1]}),
    Scenario("ignition_off", "Ignition off", "nominal", {"q6": False}),
    Scenario("ignition_on", "Ignition on", "nominal", {"q6": True}),
    Scenario("q6_short", "Ignition off, Q6 shorted", "DFM-014.C2", {"q6": False, "q6_short": True}),
    Scenario("can_nominal", "Dominant CAN_H, clamp diode healthy", "nominal", {"clamp_leak": False}),
    Scenario("clamp_leak", "Dominant CAN_H, clamp diode leaking (nominal leak)", "DFM-021.C1", {"clamp_leak": True}),
    Scenario("clamp_short", "Dominant CAN_H, clamp diode shorted", "DFM-021.C1", {"clamp_leak": True},
             {"leak_r": cc["leak_r"]["band"][0]}),
  ]


def circuit(v: dict[str, float], sw: dict[str, bool]) -> list[El]:
  """Elements with Falstad drawing coordinates (multiples of 16). Default switch states draw the intercept case."""
  st = {"drive": True, "pulldown": True, "q6": True, "q6_short": False, "clamp_leak": False} | sw
  k = v["k"]
  e = [
    # switch drive
    El("text", (16, 32), (300, 36), 16, "Switch drive (DFM-010.C3, DFM-011.C2)"),
    El("rail", (64, 96), (64, 48), v["vin"], "VIN"),
    El("lbl", (64, 96), (16, 96), name="VIN"),
    El("r", (64, 96), (64, 208), 1e5 * (1 - k)),
    El("lbl", (64, 208), (16, 208), name="VTH"),
    El("r", (64, 208), (64, 320), 1e5 * k),
    El("g", (64, 320), (64, 368)),
    El("rail", (192, 96), (192, 48), v["drive_v"], "5 V drive"),
    El("r", (192, 96), (192, 160), v["drive_r"]),
    El("sw", (192, 160), (192, 224), name="drive", closed=st["drive"]),
    El("lbl", (192, 224), (144, 224), name="SBU1"),
    El("sw", (192, 224), (192, 288), name="pulldown", closed=st["pulldown"]),
    El("r", (192, 288), (192, 384), v["pull_down"]),
    El("g", (192, 384), (192, 432)),
    El("w", (192, 224), (320, 224)),
    El("r", (320, 224), (320, 128), v["leak_hi"]),
    El("lbl", (320, 128), (368, 128), name="VIN"),
    El("r", (320, 224), (320, 320), v["leak_lo"]),
    El("g", (320, 320), (320, 368)),
    El("text", (16, 464), (420, 468), 12, "IN switches to intercept when SBU1 > VTH (VTH = k x VIN)"),
    # ignition sense
    El("text", (464, 32), (720, 36), 16, "Ignition sense (DFM-014.C2)"),
    El("rail", (512, 96), (512, 48), v["pu_v"], "3.3 V"),
    El("r", (512, 96), (512, 208), v["pu_r"]),
    El("lbl", (512, 208), (464, 208), name="SBU2"),
    El("r", (512, 208), (512, 304), v["r1"]),
    El("sw", (512, 304), (512, 384), name="q6", closed=st["q6"]),
    El("w", (512, 304), (608, 304)),
    El("sw", (608, 304), (608, 384), name="q6_short", closed=st["q6_short"]),
    El("w", (608, 384), (512, 384)),
    El("g", (512, 384), (512, 432)),
    El("text", (464, 464), (760, 468), 12, "The device reads ignition on when SBU2 < 0.9 V"),
    # CAN clamp
    El("text", (800, 32), (1060, 36), 16, "CAN clamp D2 (DFM-021.C1)"),
    El("rail", (848, 96), (848, 48), v["dom_v"], "3.5 V"),
    El("r", (848, 96), (848, 208), v["drv_r"]),
    El("lbl", (848, 208), (800, 208), name="CANH"),
    El("r", (848, 208), (976, 208), v["bus_r"]),
    El("rail", (976, 208), (976, 160), v["rec_v"], "2.5 V"),
    El("sw", (848, 208), (848, 288), name="clamp_leak", closed=st["clamp_leak"]),
    El("r", (848, 288), (848, 384), v["leak_r"]),
    El("g", (848, 384), (848, 432)),
    El("text", (800, 464), (1100, 468), 12, "Dominant needs CAN_H - CAN_L > 0.9 V (CAN_L at 1.5 V)"),
  ]
  return e


# ---------------------------------------------------------------------------------------------------------- Falstad

def num(x: float) -> str:
  """A number as Falstad parses it: it reads 1e+08 as 1, so no '+' in the exponent."""
  return f"{x:.10g}".replace("e+", "e")


def falstad_text(els: list[El]) -> str:
  def xy(e):
    return f"{e.p1[0]} {e.p1[1]} {e.p2[0]} {e.p2[1]}"
  lines = ["$ 1 0.000005 10.20027730826997 50 5 43 5e-11"]
  for e in els:
    if e.kind == "rail":
      lines.append(f"R {xy(e)} 0 0 40 {num(e.value)} 0 0 0.5")
    elif e.kind == "r":
      lines.append(f"r {xy(e)} 0 {num(e.value)}")
    elif e.kind == "sw":
      lines.append(f"s {xy(e)} 0 {0 if e.closed else 1} false")
    elif e.kind == "g":
      lines.append(f"g {xy(e)} 0 0")
    elif e.kind == "w":
      lines.append(f"w {xy(e)} 0")
    elif e.kind == "lbl":
      lines.append(f"207 {xy(e)} 4 {e.name}")
    elif e.kind == "text":
      lines.append(f"x {xy(e)} 4 {int(e.value)} {e.name.replace(' ', chr(92) + 's')}")
  return "\n".join(lines) + "\n"


def falstad_link(text: str) -> str:
  return f"{FALSTAD_URL}?running=true&cct={urllib.parse.quote(text)}"


# ---------------------------------------------------------------------------------------------------------- ngspice

def nets(els: list[El]) -> dict[tuple[int, int], str]:
  """Node of every terminal point: points joined by wires, by closed switches in Falstad's drawing sense (both ends of
  a switch stay separate nodes; the switch is a component), and labels of one name; ground is 0."""
  parent: dict = {}

  def find(a):
    parent.setdefault(a, a)
    while parent[a] != a:
      parent[a] = parent[parent[a]]
      a = parent[a]
    return a

  def union(a, b):
    parent[find(a)] = find(b)

  for e in els:
    if e.kind in ("r", "sw", "w"):
      find(e.p1), find(e.p2)
    if e.kind in ("rail", "g", "lbl"):
      find(e.p1)
    if e.kind == "w":
      union(e.p1, e.p2)
    if e.kind == "lbl":
      union(e.p1, ("label", e.name))
    if e.kind == "g":
      union(e.p1, ("ground",))
  ground = find(("ground",)) if ("ground",) in parent else None
  names, out = {}, {}
  for pt in [q for q in parent if isinstance(q[0], int)]:
    root = find(pt)
    if root == ground:
      out[pt] = "0"
      continue
    label = next((q[1] for q in parent if q[0] == "label" and find(q) == root), None)
    out[pt] = names.setdefault(root, (label or f"n{len(names)}").lower())
  return out


def spice_deck(els: list[El]) -> str:
  n = nets(els)
  lines = ["* harness box switch path (harness_box.py); synthetic, DSR-12"]
  for i, e in enumerate(els):
    a, b = n.get(e.p1), n.get(e.p2)
    if e.kind == "rail":
      lines.append(f"V{i} {a} 0 DC {e.value:g}")
    elif e.kind == "r":
      lines.append(f"R{i} {a} {b} {e.value:g}")
    elif e.kind == "sw" and e.closed:
      lines.append(f"R{i} {a} {b} {CLOSED_R:g}")
  lines += [".op", ".end"]
  return "\n".join(lines) + "\n"


def ngspice() -> str:
  exe = shutil.which("ngspice") or str(Path(sys.executable).parent / "ngspice")
  if not Path(exe).exists():
    raise SystemExit("ngspice not found: create the environment from ../supply/supply-linux-64.lock")
  return exe


def run_spice(deck: str) -> dict[str, float]:
  want = [x.lower() for x in NODES]
  present = [w for w in want if re.search(rf"\b{w}\b", deck)]
  control = ".control\nop\n" + "".join(f"print v({w})\n" for w in present) + "quit\n.endc\n"
  with tempfile.TemporaryDirectory() as d:
    src = Path(d) / "deck.cir"
    src.write_text(deck.replace(".end\n", control + ".end\n"), encoding="utf-8")
    r = subprocess.run([ngspice(), "-b", str(src)], capture_output=True, text=True, timeout=60)
  out = {}
  for w in present:
    m = re.search(rf"v\({w}\)\s*=\s*([-+0-9.eE]+)", r.stdout)
    if not m:
      raise SystemExit(f"ngspice gave no v({w}):\n{r.stdout[-1500:]}\n{r.stderr[-800:]}")
    out[w.upper()] = float(m.group(1))
  return out


# ---------------------------------------------------------------------------------------------------------- results

def verdict(s: Scenario, v: dict[str, float], nodes: dict[str, float], p: dict) -> str:
  vth = nodes["VTH"]
  if s.id.startswith(("intercept", "pass", "pulldown", "threshold")):
    margin = nodes["SBU1"] - vth
    state = "intercept" if margin > 0 else "pass-through"
    return f"IN reads {state} (SBU1 {margin:+.2f} V from the threshold)"
  if s.id.startswith(("ignition", "q6")):
    on = nodes["SBU2"] < p["ignition_sense"]["adc_threshold"]["value"]
    return f"device reads ignition {'on' if on else 'off'}"
  diff = nodes["CANH"] - 1.5
  dom = diff > p["can_clamp"]["dominant_threshold"]["value"]
  return f"differential {diff:.2f} V: {'dominant' if dom else 'NOT dominant: frames corrupted, bus errors'}"


def build() -> dict:
  p = load_params()
  out = {"note": "Synthetic (DSR-12), design aid, no evidence credit (DQ-413). ngspice 41 DC operating points.",
         "scenarios": []}
  FALSTAD_DIR.mkdir(exist_ok=True)
  for s in scenarios(p):
    v = values(p, s.params)
    els = circuit(v, s.switches)
    nodes = run_spice(spice_deck(els))
    text = falstad_text(els)
    (FALSTAD_DIR / f"{s.id}.txt").write_text(text, encoding="utf-8")
    out["scenarios"].append({"id": s.id, "title": s.title, "fmea": s.fmea, "switches": s.switches,
                             "params": s.params, "nodes": {k: round(x, 6) for k, x in nodes.items()},
                             "verdict": verdict(s, v, nodes, p)})
  nominal = falstad_text(circuit(values(p, {}), {}))
  (FALSTAD_DIR / "interactive.txt").write_text(nominal, encoding="utf-8")
  out["link"] = falstad_link(nominal)
  return out


def markdown(r: dict) -> str:
  rows = "\n".join(f"| {s['title']} | {s['fmea']} | " + ", ".join(f"{k} {x:.3f} V" for k, x in s["nodes"].items()
                                                                  if k in ("SBU1", "VTH", "SBU2", "CANH"))
                   + f" | {s['verdict']} |" for s in r["scenarios"])
  return f"""# Harness box switch path: results

> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by
> [`harness_box/harness_box.py`](../harness_box/harness_box.py) from [`params.yaml`](../harness_box/params.yaml);
> do not edit. The DG419LE threshold at VL = VIN, the device's SBU1 driver and its SBU2 pull-up are estimates.

**[Open the circuit in Falstad]({r['link']})** (runs in the browser; click a switch to flip it). The same circuit as
each row below is in [`harness_box/falstad/`](../harness_box/falstad/); CI runs every one in Falstad headless and
checks its node voltages against this table within {TOL_V * 1000:.0f} mV.

| Scenario | FMEA | ngspice node voltages | Reading |
|---|---|---|---|
{rows}
"""


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
  ap.add_argument("--check", action="store_true")
  a = ap.parse_args(argv)
  r = build()
  if a.check:
    old = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    bad = []
    for s, o in zip(r["scenarios"], old["scenarios"], strict=True):
      for k, x in s["nodes"].items():
        if abs(x - o["nodes"][k]) > TOL_V:
          bad.append(f"{s['id']} {k}: {x:.4f} V, committed {o['nodes'][k]:.4f} V")
      if s["verdict"] != o["verdict"]:
        bad.append(f"{s['id']}: {s['verdict']!r}, committed {o['verdict']!r}")
    if r["link"] != old["link"] or OUT_MD.read_text(encoding="utf-8") != markdown(old):
      bad.append("link or results page stale")
    if bad:
      print("harness_box: results differ from the committed ones:\n  " + "\n  ".join(bad), file=sys.stderr)
      return 1
    print(f"harness_box: {len(r['scenarios'])} scenarios current")
    return 0
  OUT_JSON.write_text(json.dumps(r, indent=1) + "\n", encoding="utf-8")
  OUT_MD.write_text(markdown(r), encoding="utf-8")
  print(f"wrote {OUT_JSON.relative_to(HERE.parent)}, {OUT_MD.relative_to(HERE.parent)} and {len(r['scenarios']) + 1} Falstad files")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
