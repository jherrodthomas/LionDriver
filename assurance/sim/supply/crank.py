#!/usr/bin/env python3
"""12 V cranking dip (physics plan study 8; WP-S-02 TSR-505, WP-H-01 HWSR-505…505b): does the panda MCU's supply stay
in range when the engine cranks, or does it brown out?

A circuit model in ngspice (tool entry in WP-P-07): the car's supply follows the ISO 16750-2 starting profile (levels
I, II and IV), through the harness and a reverse-polarity diode to the device's input and its hold-up capacitance.
The device's 12 V to 5 V converter regulates, falls into dropout, or stops below its under-voltage lockout; its
5 V loads draw constant power. The panda MCU's 3.3 V regulator hangs off the 5 V rail. The MCU's rail is set against
its own thresholds (DS13311 Table 20): the power-down reset, the brown-out levels BOR1–3 that TSR-505 asks for (not
configured today), and the 1.71 V below which the part is not specified with its internal reset on.

The device's power path is not published, so the circuit is generic with a band on each part (`params.yaml`). The
result is which dips the generic device rides through, which reset it, and which leave the MCU running unspecified
without a reset (the window TSR-505's brown-out reset would close). Writes `../results/crank-dip.json` and `.md`.

    python3 crank.py --figures
    python3 crank.py --check

Runs in the environment of `supply-linux-64.lock` (ngspice on the PATH or in that environment's bin).
Synthetic (DSR-12), design aid, no evidence credit (DQ-413).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
OUT_JSON = HERE.parent / "results" / "crank-dip.json"
OUT_MD = HERE.parent / "results" / "crank-dip.md"
T0 = 0.02                       # s of steady supply before the dip
REL_TOL = 0.01                  # --check: within 1 % (or 1 mV, 0.1 ms) of the committed results
VARIANTS = ("nominal", "uvlo_low", "uvlo_high", "holdup_low", "holdup_high", "power_high", "harness_high")


def ngspice() -> str:
  exe = shutil.which("ngspice") or str(Path(sys.executable).parent / "ngspice")
  if not Path(exe).exists():
    raise SystemExit("ngspice not found: create the environment from supply-linux-64.lock")
  return exe


def simulate(deck: str, vectors: list[str]) -> dict:
  """Run a netlist in ngspice (batch) and read the vectors back, on ngspice's own time points."""
  with tempfile.TemporaryDirectory() as d:
    out = Path(d) / "out.txt"
    control = (f".control\nset wr_singlescale\nset wr_vecnames\noption numdgt=9\nrun\n"
               f"wrdata {out} {' '.join(vectors)}\nquit\n.endc\n")
    src = Path(d) / "deck.cir"
    src.write_text(deck.replace(".end\n", control + ".end\n"), encoding="utf-8")
    env = dict(os.environ, SPICE_ASCIIRAWFILE="1")
    res = subprocess.run([ngspice(), "-b", str(src)], capture_output=True, text=True, env=env, cwd=d, timeout=600)
    if res.returncode != 0 or not out.exists():
      raise SystemExit(f"ngspice failed:\n{res.stdout[-2000:]}\n{res.stderr[-2000:]}")
    lines = out.read_text().split("\n")
    names = lines[0].split()
    data = np.loadtxt(lines[1:])
  return {n: data[:, i] for i, n in enumerate(names)}


def profile_points(p: dict, level: str) -> list[tuple[float, float]]:
  pr = p["profile"]
  lv = pr["levels"][level]
  t = [0.0, T0, T0 + pr["tf"], T0 + pr["tf"] + pr["t6"], T0 + pr["tf"] + pr["t6"] + pr["t7"]]
  v = [pr["ub"], pr["ub"], lv["us6"], lv["us6"], lv["us"]]
  t += [t[-1] + lv["t8"], t[-1] + lv["t8"] + lv["tr"]]
  v += [lv["us"], pr["ub"]]
  return list(zip(t, v, strict=True))


def parts(p: dict, variant: str) -> dict:
  """The circuit's values for one variant: nominal, or one part at an end of its band."""
  b = p["buck"]
  c = {"rh": p["harness"]["r"], "lh": p["harness"]["l"], "c": p["holdup"]["c"], "esr": p["holdup"]["esr"],
       "uvlo": b["uvlo"]["value"], "p5": p["load_5v"]["power"]}
  if variant == "uvlo_low":
    c["uvlo"] = b["uvlo"]["band"][0]
  elif variant == "uvlo_high":
    c["uvlo"] = b["uvlo"]["band"][1]
  elif variant == "holdup_low":
    c["c"] = p["holdup"]["band"][0]
  elif variant == "holdup_high":
    c["c"] = p["holdup"]["band"][1]
  elif variant == "power_high":
    c["p5"] = p["load_5v"]["band"][1]
  elif variant == "harness_high":
    c["rh"] = p["harness"]["r_band"][1]
  return c


def deck(p: dict, points: list, c: dict, window: float, step: float) -> str:
  """The netlist. Behavioural sources: the buck (regulation, dropout, lockout, power conserved at its efficiency),
  the 5 V loads at constant power, the LDO (regulation and dropout)."""
  b, ldo = p["buck"], p["ldo"]
  pwl = " ".join(f"{t:.6g} {v:.6g}" for t, v in points)
  rmcu = ldo["vout"] / p["mcu_load"]["current"]
  return f"""* 12 V cranking dip: car supply, harness, diode, hold-up, buck, 5 V loads, LDO, MCU (crank.py)
.param uvlo={c['uvlo']} vbuck={b['vout']} hr={b['headroom']} eta={b['efficiency']} p5={c['p5']}
.param vldo={ldo['vout']} vdo={ldo['dropout']} rs=0.02
.func en(v) {{0.5*(1+tanh((v-uvlo)/0.05))}}
.func ib(vi,vo) {{en(vi)*max(0,(min(vbuck,vi-hr)-vo)/rs)}}
.func il(vi,vo) {{max(0,(min(vldo,vi-vdo)-vo)/rs)}}
Vcar car 0 PWL({pwl})
Rh car h1 {c['rh']}
Lh h1 h2 {c['lh']}
D1 h2 vin dshottky
.model dshottky D(Is={p['diode']['is']} N={p['diode']['n']})
Chold vin c1 {c['c']}
Resr c1 0 {c['esr']}
Bbuck 0 v5 I={{ib(v(vin),v(v5))}}
Bbuckin vin 0 I={{v(v5)*ib(v(vin),v(v5))/(eta*max(v(vin),0.5))}}
C5 v5 0 {b['c_out']}
B5 v5 0 I={{p5*v(v5)/max(v(v5)*v(v5),16)}}
Bldo 0 v33 I={{il(v(v5),v(v33))}}
Bldoin v5 0 I={{il(v(v5),v(v33))}}
C33 v33 0 {ldo['c_out']}
Rmcu v33 0 {rmcu}
.tran {step} {window} 0 {step}
.end
"""


def thresholds(p: dict) -> dict:
  m = p["mcu_thresholds"]
  return {k: m[k]["value"] for k in ("pdr", "bor1", "bor2", "bor3", "vdd_min")}


def metrics(w: dict, th: dict) -> dict:
  t, vin, v5, v33 = w["time"], w["v(vin)"], w["v(v5)"], w["v(v33)"]
  dt = np.diff(t, append=t[-1])
  def below(x, level):
    return float((dt * (x < level)).sum())
  out = {"vin_min": round(float(vin.min()), 3), "v5_min": round(float(v5.min()), 3),
         "v33_min": round(float(v33.min()), 3), "vin_end": round(float(vin[-1]), 3), "v5_end": round(float(v5[-1]), 3),
         "v33_end": round(float(v33[-1]), 3)}
  out["below_ms"] = {k: round(1000 * below(v33, v), 2) for k, v in th.items()}
  # unspecified without reset: under the 1.71 V the part needs with its internal reset on, but above the reset itself
  out["unspecified_ms"] = round(1000 * float((dt * ((v33 < th["vdd_min"]) & (v33 > th["pdr"]))).sum()), 2)
  if v33.min() >= th["bor3"]:
    out["outcome"] = "rides through"
  elif v33.min() < th["pdr"]:
    out["outcome"] = "resets, restarts at US" if v33[-1] >= th["bor3"] else "resets, stays off"
  else:
    out["outcome"] = "rail sags, no reset (BOR off)"
  # on the way down: from the BOR3 level to the power-down reset, the MCU runs on a rail a BOR would have reset
  fall = np.where(v33 < th["bor3"])[0]
  if len(fall) and v33.min() < th["pdr"]:
    i0 = fall[0]
    i1 = i0 + int(np.argmax(v33[i0:] < th["pdr"]))
    out["bor3_to_reset_ms"] = round(1000 * float(t[i1] - t[i0]), 3)
  else:
    out["bor3_to_reset_ms"] = 0.0
  return out


def run(p: dict) -> dict:
  r = p["run"]
  th = thresholds(p)
  out = {"about": "Synthetic (DSR-12), design aid, no evidence credit. A generic device power path with a band on "
                  "each part; ISO 16750-2 starting profiles (levels I, II, IV).",
         "thresholds": th, "levels": {}}
  for level in p["profile"]["levels"]:
    pts = profile_points(p, level)
    res = {"profile": [[round(t, 4), v] for t, v in pts], "variants": {}}
    for var in VARIANTS:
      w = simulate(deck(p, pts, parts(p, var), r["window_s"], r["step_s"]), ["v(car)", "v(vin)", "v(v5)", "v(v33)"])
      res["variants"][var] = metrics(w, th)
      if var == "nominal":
        k = np.unique(np.searchsorted(w["time"], np.linspace(0, r["window_s"], 801)).clip(0, len(w["time"]) - 1))
        res["trace"] = {n[2:-1] if n != "time" else "t": [round(float(x), 4) for x in w[n][k]]
                        for n in ("time", "v(car)", "v(vin)", "v(v5)", "v(v33)")}
    out["levels"][level] = res
  return out


NAMES = {"nominal": "nominal", "uvlo_low": "lockout 3.5 V", "uvlo_high": "lockout 6.0 V", "holdup_low": "hold-up 22 µF",
         "holdup_high": "hold-up 470 µF", "power_high": "9 W", "harness_high": "harness 0.15 Ω"}


def markdown(r: dict, p: dict) -> str:
  th = r["thresholds"]
  L = [
    "# 12 V cranking dip: the panda MCU's supply",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`supply/crank.py`](../supply/crank.py) with ngspice; do not edit by hand. The device's power path is not "
    "published: the circuit is generic, with a band on each part ([`params.yaml`](../supply/params.yaml)), until a "
    "schematic or a bench measurement replaces it.",
    "",
    "The car's supply follows the ISO 16750-2 starting profile (via TI SCPS268A Table 10-5): from 14 V it falls to "
    "US6 for 15 ms, rises to US and stays there. The device: harness, a Schottky diode, hold-up capacitance, a buck to "
    f"5 V (lockout {p['buck']['uvlo']['value']:.1f} V, band {p['buck']['uvlo']['band'][0]:.1f}–"
    f"{p['buck']['uvlo']['band'][1]:.1f} V) feeding {p['load_5v']['power']:.0f} W, and the MCU's 3.3 V LDO. The MCU's "
    f"thresholds (DS13311 Table 20, falling): power-down reset {th['pdr']:.2f} V, BOR1–3 {th['bor1']:.2f} / "
    f"{th['bor2']:.2f} / {th['bor3']:.2f} V, and {th['vdd_min']:.2f} V, below which it is not specified with its "
    "internal reset on.",
    "",
    "| Level (US6 → US) | Circuit | Device input, lowest | 5 V rail, lowest | MCU rail, lowest | MCU rail at US | "
    "BOR3 to reset | Outcome |",
    "|---|---|---|---|---|---|---|---|",
  ]
  for level, res in r["levels"].items():
    lv = p["profile"]["levels"][level]
    for var, m in res["variants"].items():
      L.append(f"| {level} ({lv['us6']:g} → {lv['us']:g} V) | {NAMES[var]} | {m['vin_min']:.2f} V | {m['v5_min']:.2f} V | "
               f"{m['v33_min']:.2f} V | {m['v33_end']:.2f} V | {m['bor3_to_reset_ms']:.2f} ms | {m['outcome']} |")
  nom = {lv: res["variants"]["nominal"] for lv, res in r["levels"].items()}
  unspec = [(lv, var) for lv, res in r["levels"].items() for var, m in res["variants"].items() if m["unspecified_ms"] > 0]
  fast = [m["bor3_to_reset_ms"] for res in r["levels"].values() for m in res["variants"].values()
          if m["bor3_to_reset_ms"] > 0]
  sag = [(lv, var) for lv, res in r["levels"].items() for var, m in res["variants"].items()
         if m["outcome"] == "rail sags, no reset (BOR off)"]
  L += ["", "## What this shows (generated)", "",
        f"- **Level I** (8 V): the generic device rides through; its input falls to {nom['I']['vin_min']:.1f} V, "
        "the converter stays in regulation.",
        f"- **Level II** (4.5 V, then 6.5 V for 10 s): nominal outcome **{nom['II']['outcome']}**; the input falls to "
        f"{nom['II']['vin_min']:.1f} V. The hold-up capacitance hardly helps: at about 8 W it holds a few milliseconds, "
        "not 15. Whether the converter locks out sets the outcome.",
        f"- **Level IV** (6 V, then 6.5 V): nominal outcome **{nom['IV']['outcome']}**.",
        ("- **Sagging without a reset**: in " + ", ".join(f"level {lv} ({NAMES[v]})" for lv, v in sag)
         + " the MCU's rail falls below the BOR levels but not to the power-down reset. With BOR off (today) the MCU "
         "keeps running on a low rail; a BOR at level 3 would reset it." if sag else
         "- In no case does the MCU's rail stop between the BOR levels and the power-down reset: it either stays up "
         "or falls through to a reset."),
        (f"- **Unspecified**: where the rail collapses, it falls from the BOR3 level to the power-down reset in "
         f"{min(fast):.2f}–{max(fast):.2f} ms, and spends a fraction of that under 1.71 V with nothing resetting the "
         "MCU. Short, but code runs there on a rail the part is not specified for; a brown-out reset (TSR-505, "
         "HWSR-505) closes the window. A slower collapse (more capacitance on the 3.3 V rail, a lighter load) "
         "lengthens it." if unspec else "- No case leaves the MCU under 1.71 V without a reset for any time."),
        f"- **HWSR-505b**: in a crank the device's input dips to {nom['I']['vin_min']:.1f} V (level I) and "
        f"{min(m['vin_min'] for m in nom.values()):.1f} V (level II). An input threshold for the safe state above "
        "the dip trips on each such start; while engaged that matters only with engine stop-start (T1: does the "
        "reference car have it?).",
        "- The circuit is generic: the conclusions hold for a converter and hold-up like these, not for the 3X's own, "
        "until its schematic or a bench test with these profiles replaces the model.",
        ""]
  return "\n".join(L)


def compare(new, old, path=""):
  if isinstance(new, dict):
    return [e for k in set(new) | set(old) for e in
            ([f"{path}/{k}: missing"] if k not in new or k not in old else compare(new[k], old[k], f"{path}/{k}"))]
  if isinstance(new, list):
    if len(new) != len(old):
      return [f"{path}: length differs"]
    return [e for i, (a, b) in enumerate(zip(new, old, strict=True)) for e in compare(a, b, f"{path}[{i}]")]
  if isinstance(new, float) and isinstance(old, (int, float)):
    return [] if abs(new - old) <= 1e-3 + REL_TOL * abs(old) else [f"{path}: {new} != {old}"]
  return [] if new == old else [f"{path}: {new!r} != {old!r}"]


def main(argv):
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("--check", action="store_true")
  ap.add_argument("--figures", action="store_true")
  a = ap.parse_args(argv[1:])
  p = yaml.safe_load((HERE / "params.yaml").read_text(encoding="utf-8"))
  r = run(p)
  md = markdown(r, p)
  if a.check:
    errs = compare(r, json.loads(OUT_JSON.read_text(encoding="utf-8")))
    if not errs and OUT_MD.read_text(encoding="utf-8") != md:
      errs.append(f"{OUT_MD.name} is stale")
    for e in errs[:20]:
      print("FAIL", e)
    print("crank dip:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, separators=(",", ":")) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name,
        {lv: {v: (m["vin_min"], m["v5_min"], m["v33_min"], m["outcome"]) for v, m in res["variants"].items()}
         for lv, res in r["levels"].items()})
  if a.figures:
    import fig_supply
    fig_supply.crank_figure(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
