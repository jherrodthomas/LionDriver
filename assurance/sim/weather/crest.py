#!/usr/bin/env python3
"""Hill crests (physics plan round 3, study 12; WP-C-06 TC-17, WP-V-03 KS-27, WP-C-02 §3.1 vertical curves).

The ODD includes crests built to the design standard. AASHTO sizes a crest so a driver's eye at 1.08 m sees a car's
tail lights at 0.60 m over the top at the stopping sight distance (2.5 s reaction, 3.4 m/s²). The road camera sits
at 1.2 m and the radar lower; over a parabolic crest the sight distance from height h1 to an object of height h2 is
S = sqrt(200 K) (sqrt h1 + sqrt h2) (K in m per % of grade change, sight shorter than the curve). Each sensor's
sight to a stopped car (tail lights, roof, the height of its radar return) is set against the distance needed to
stop: AASHTO's design case, the driver after a take-over request (WP-S-04), and the item's own −3.5 m/s².
Writes `../results/crest.json` and `.md`.

    python3 crest.py --figures
    python3 crest.py --check

The item does not brake for a stopped car it has not tracked (WP-C-02 F-02): the driver and the stock PCS stop for
it, so the sight distances are what the scene gives them. Synthetic (DSR-12), design aid, no evidence credit.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wet_braking as wb  # noqa: E402
import wet_curves as wc  # noqa: E402

SIM = HERE.parent
OUT_JSON = SIM / "results" / "crest.json"
OUT_MD = SIM / "results" / "crest.md"


def ssd(v_kph: float, t: float, a: float) -> float:
  """AASHTO stopping sight distance, metric: 0.278 V t + 0.039 V² / a (m)."""
  return 0.278 * v_kph * t + 0.039 * v_kph ** 2 / a


def k_design(ssd_m: float, h1: float = 1.08, h2: float = 0.60) -> float:
  """Crest K (m per %) for sight distance S between heights h1 and h2, when S is shorter than the curve."""
  return ssd_m ** 2 / (200 * (math.sqrt(h1) + math.sqrt(h2)) ** 2)


def sight(k: float, h1: float, h2: float) -> float:
  """Sight distance over a crest of K from height h1 to an object of height h2 (S shorter than the curve)."""
  return math.sqrt(200 * k) * (math.sqrt(h1) + math.sqrt(h2))


def sight_numeric(k: float, grade_change_pct: float, h1: float, h2: float, n: int = 4001) -> float:
  """The same by brute force on the parabola y = -x² / (200 K) over a curve long enough: the shortest distance at
  which the line of sight from h1 to h2 touches the road, over the observer's positions."""
  L = k * grade_change_pct
  def y(x):
    return -x ** 2 / (200 * k)
  best = math.inf
  for x0 in np.linspace(-L / 2, 0, 201):
    lo, hi = 1.0, L
    for _ in range(60):                       # longest clear distance from x0
      d = (lo + hi) / 2
      xs = np.linspace(x0, x0 + d, n)
      line = (y(x0) + h1) + (y(x0 + d) + h2 - y(x0) - h1) * (xs - x0) / d
      clear = np.all(line[1:-1] >= y(xs[1:-1]))
      lo, hi = (d, hi) if clear else (lo, d)
    best = min(best, lo)
  return best


def run(p: dict) -> dict:
  c = p["crest"]
  dh = c["design_heights_m"]
  a_item = -wb.accel_min()
  mu_wet3 = wc.mu_odd(p, 110.0, float(wb.water(p, [p["curves"]["rain_mm_h"]["value"]])[0]))
  out = {"about": "Synthetic (DSR-12), design aid, no evidence credit. AASHTO's crest geometry; estimated sensor heights.",
         "cases": {}}
  sensors = {"driver": dh["eye"], "camera": c["camera_height_m"]["value"], "radar": c["radar_height_m"]["value"],
             "radar_low": c["radar_height_m"]["low"]}
  tg = c["targets_m"]
  for vd in c["design_speeds_kph"]["value"]:
    s_design = ssd(vd, c["ssd"]["reaction_s"], c["ssd"]["decel"])
    kt = c["k_table"]
    k = float(kt["k"][kt["speeds_kph"].index(vd)])    # crests are built to the published, rounded K
    sights = {
      "driver_tail_lights": sight(k, sensors["driver"], tg["tail_lights"]),
      "camera_tail_lights": sight(k, sensors["camera"], tg["tail_lights"]),
      "camera_roof": sight(k, sensors["camera"], tg["roof"]),
      "radar_return": sight(k, sensors["radar"], tg["radar_return"]),
      "radar_return_low": sight(k, sensors["radar_low"], tg["radar_return"]),
    }
    v = 110.0                                 # the ODD's top speed, on a crest built for vd
    need = {
      "aashto": ssd(v, c["ssd"]["reaction_s"], c["ssd"]["decel"]),
      "driver_dry": wb.stop_m(v, 0.8 * 9.81, c["driver_reaction_s"]["value"]),
      "driver_wet_3mm": wb.stop_m(v, mu_wet3 * 9.81, c["driver_reaction_s"]["value"]),
      "item_rate": wb.stop_m(v, a_item, p["braking"]["reaction_s"]["value"]),
    }
    out["cases"][f"{vd}"] = {"design_speed_kph": vd, "k": round(k, 1), "design_ssd_m": round(s_design, 1),
                             "sight_m": {kk: round(vv, 1) for kk, vv in sights.items()},
                             "need_at_110_m": {kk: round(vv, 1) for kk, vv in need.items()}}
  out["mu_wet_3mm_110"] = round(mu_wet3, 3)
  out["mu_dry"] = 0.8
  return out


def markdown(r: dict, p: dict) -> str:
  c = p["crest"]
  L = [
    "# Hill crests: sight over the top against the distance to stop",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`weather/crest.py`](../weather/crest.py); do not edit by hand. AASHTO's crest geometry; the radar's height is an "
    "estimate until T1.",
    "",
    "A crest built to AASHTO's stopping sight distance for its design speed, driven at the ODD's 110 km/h. Sight "
    f"from the driver's eye (1.08 m), the road camera ({c['camera_height_m']['value']:.1f} m) and the radar "
    f"({c['radar_height_m']['value']:.1f} m, {c['radar_height_m']['low']:.1f} m low) to a stopped car's tail lights "
    "(0.60 m), roof and radar return; against the distance to stop from 110 km/h.",
    "",
    "| Crest built for | K | Driver to tail lights | Camera to tail lights | Camera to roof | Radar to the car "
    "(0.5 / 0.4 m radar) |",
    "|---|---|---|---|---|---|",
  ]
  for vd, cs in r["cases"].items():
    s = cs["sight_m"]
    L.append(f"| {vd} km/h | {cs['k']:.0f} | {s['driver_tail_lights']:.0f} m | {s['camera_tail_lights']:.0f} m | "
             f"{s['camera_roof']:.0f} m | {s['radar_return']:.0f} / {s['radar_return_low']:.0f} m |")
  n = r["cases"]["110"]["need_at_110_m"]
  L += ["", "Distance to stop from 110 km/h: "
        f"AASHTO's design case {n['aashto']:.0f} m; a driver ({c['driver_reaction_s']['value']:.1f} s) braking fully on a "
        f"dry road {n['driver_dry']:.0f} m, on a wet road with 3 mm of tread (friction {r['mu_wet_3mm_110']:.2f}) "
        f"{n['driver_wet_3mm']:.0f} m; the item's own rate {n['item_rate']:.0f} m.", ""]
  c100, c110 = r["cases"]["100"], r["cases"]["110"]
  rad = c110["sight_m"]["radar_return"]
  cam = c110["sight_m"]["camera_tail_lights"]
  L += ["## What this shows (generated)", "",
        f"- **The camera sees a little farther than the driver** ({cam:.0f} m against "
        f"{c110['sight_m']['driver_tail_lights']:.0f} m on a 110 km/h crest), being higher. **The radar sees less** "
        f"({rad:.0f} m), being lower: over a crest the radar is the last to see a stopped car.",
        f"- On a crest built for 110 km/h, the driver stopping fully on a dry road needs {n['driver_dry']:.0f} m: "
        + ("inside what the camera sees." if n["driver_dry"] <= cam else "more than the camera sees.")
        + f" On a wet road with 3 mm of tread it takes {n['driver_wet_3mm']:.0f} m, "
        + ("still inside." if n["driver_wet_3mm"] <= cam else f"{n['driver_wet_3mm'] - cam:.0f} m beyond the camera's sight.")
        + f" The item's own −3.5 m/s² needs {n['item_rate']:.0f} m, "
        + ("inside the radar's sight." if n["item_rate"] <= rad else f"more than the radar sees ({rad:.0f} m).")
        ,
        f"- **Older crests built for 100 km/h** (K {c100['k']:.0f}) cut every sight distance: the camera sees "
        f"{c100['sight_m']['camera_tail_lights']:.0f} m, the radar {c100['sight_m']['radar_return']:.0f} m.",
        "- For WP-C-02 §3.1: the ODD's \"crests with stopping sight distance per design standards\" gives the camera "
        f"and an attentive driver room to stop on a crest built for 110 km/h, dry and wet "
        f"({n['driver_wet_3mm']:.0f} m wet against the standard's {c110['design_ssd_m']:.0f} m). On a crest built for "
        f"100 km/h, driven at 110, the wet stop ({c100['need_at_110_m']['driver_wet_3mm']:.0f} m) "
        + ("fits the camera's sight." if c100["need_at_110_m"]["driver_wet_3mm"] <= c100["sight_m"]["camera_tail_lights"]
           else f"is longer than the camera's sight ({c100['sight_m']['camera_tail_lights']:.0f} m).")
        + " The radar's real height (T1) moves its line.",
        ""]
  return "\n".join(L)


def main(argv):
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("--check", action="store_true")
  ap.add_argument("--figures", action="store_true")
  a = ap.parse_args(argv[1:])
  p = yaml.safe_load((HERE / "params.yaml").read_text(encoding="utf-8"))
  r = run(p)
  md = markdown(r, p)
  if a.check:
    from sun_glare import compare
    errs = compare(r, json.loads(OUT_JSON.read_text(encoding="utf-8")))
    if not errs and OUT_MD.read_text(encoding="utf-8") != md:
      errs.append(f"{OUT_MD.name} is stale")
    for e in errs[:20]:
      print("FAIL", e)
    print("crest:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, indent=1) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name, json.dumps(r["cases"]["110"]))
  if a.figures:
    import fig_weather
    fig_weather.crest_figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
