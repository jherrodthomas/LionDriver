#!/usr/bin/env python3
"""Sun on the device through the car (physics plan study 6; WP-C-06 TC-21, WP-A-03 DFI-04): what the sun really puts
into the comma device, against the heat model's constant.

The device heat model (`../thermal/params.yaml`, `sun:`) puts 800 W/m² x 0.5 x 0.8 = 320 W/m² on the device's
windshield-side face, all day, and nothing on its other faces. Here the sun is clear-sky (pvlib, Ineichen) at the
corridor's middle for every 10 minutes of a year, on the car headed either way along I-85 or parked facing any way.
Which faces it reaches, and through which glass, comes from a ray cast through the Corolla mesh
(`../assets/tools/device_shading.py`, committed as `../figures/corolla-e210-device-shading.json`; the mesh itself is
not in git). Each face then takes the direct beam (cosine on the face, glass transmittance with its angle loss, pvlib's
physical model) and the sky's diffuse light through the glass it can see (isotropic sky). Writes
`../results/device-sun.json` and `.md`.

    python3 device_sun.py --figures
    python3 device_sun.py --check

Not modelled: light reflected off the dashboard, the hood or the ground; the stock camera housing behind the mirror
(not in the mesh); the windshield's frit. The device's place on the glass is an estimate until T1.
Synthetic (DSR-12), design aid, no evidence credit.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pvlib
import yaml

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
sys.path.insert(0, str(SIM / "assets" / "tools"))
import device_shading as ds  # noqa: E402

TABLE = SIM / "figures" / "corolla-e210-device-shading.json"
GEOMETRY = SIM / "figures" / "corolla-e210-geometry.json"
OUT_JSON = SIM / "results" / "device-sun.json"
OUT_MD = SIM / "results" / "device-sun.md"
STEP_MIN = 10
PARKED = np.arange(0.0, 360.0, 30.0)     # parked headings, deg
SUMMER = (6, 7, 8)                       # the hot months, when the device's heat matters
DAYS = {"summer": "2027-07-21", "winter": "2027-12-21"}


def lookup(t: dict, case: str, face: str, elev: np.ndarray, relaz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
  """Lit fraction (bilinear) and the glass code (nearest) of a face for sun directions in the car's frame."""
  E, A = np.array(t["elev_deg"]), np.array(t["relaz_deg"])
  f = t["cases"][case][face]
  lit, via = np.array(f["lit"]), np.array(f["glass"])
  e = np.clip(elev, E[0], E[-1])
  a = (relaz + 180.0) % 360.0 - 180.0
  fe = (e - E[0]) / (E[1] - E[0])
  fa = (a - A[0]) / (A[1] - A[0])
  i0 = np.clip(np.floor(fe).astype(int), 0, len(E) - 2)
  j0 = np.clip(np.floor(fa).astype(int), 0, len(A) - 2)
  u, v = fe - i0, fa - j0
  val = ((1 - u) * (1 - v) * lit[i0, j0] + u * (1 - v) * lit[i0 + 1, j0] + (1 - u) * v * lit[i0, j0 + 1]
         + u * v * lit[i0 + 1, j0 + 1])
  code = via[np.clip(np.rint(fe).astype(int), 0, len(E) - 1), np.clip(np.rint(fa).astype(int), 0, len(A) - 1)]
  return val, code


def glass_normals() -> dict:
  g = json.loads(GEOMETRY.read_text(encoding="utf-8"))["glass"]
  return {1: np.array(g["windshield"]["normal"]), 2: np.array(g["roof_glass"]["normal"]),
          3: np.array(g["side_front_each"]["normal"]), 4: np.array(g["rear_window"]["normal"])}


def through(d: dict, normals: dict, dirs: np.ndarray, code: np.ndarray) -> np.ndarray:
  """Solar transmittance of the glass each ray crosses: at normal incidence (params) times pvlib's physical angle
  loss (Fresnel and absorption, De Soto 2006) at the ray's angle to that glass."""
  tr = d["transmittance"]
  t0 = {1: tr["value"], 2: tr["roof"], 3: tr["side"], 4: tr["side"]}
  out = np.zeros(len(dirs))
  for c, n in normals.items():
    sel = code == c
    if not sel.any():
      continue
    nn = np.tile(n, (sel.sum(), 1))
    if c == 3:                                          # the side glass on the ray's side of the car
      nn[:, 2] = np.sign(dirs[sel, 2]) * abs(n[2])
    cos = np.clip(np.abs(np.einsum("ij,ij->i", dirs[sel], nn)), 0, 1)
    out[sel] = t0[c] * np.nan_to_num(pvlib.iam.physical(np.degrees(np.arccos(cos))))
  return out


def sky_cells(t: dict) -> tuple[np.ndarray, np.ndarray]:
  """The table's directions and the solid angle each one stands for (the sky above the car's horizon)."""
  E, A = np.meshgrid(np.array(t["elev_deg"]), np.array(t["relaz_deg"]), indexing="ij")
  de, da = math.radians(t["elev_deg"][1] - t["elev_deg"][0]), math.radians(t["relaz_deg"][1] - t["relaz_deg"][0])
  w = np.cos(np.radians(E)).reshape(-1) * de * da
  w[np.isclose(A.reshape(-1), 180.0)] = 0.0                        # -180 and +180 are the same column
  w[np.isclose(E.reshape(-1), 0.0) | np.isclose(E.reshape(-1), 90.0)] *= 0.5
  return ds.direction(E, A).reshape(-1, 3), w


def sky_view(t: dict, d: dict, normals: dict, case: str, face: str) -> float:
  """The face's isotropic-sky diffuse factor through the glass: (1/pi) x the integral over the sky above the car's
  horizon of lit x transmittance x cos(angle to the face); an upright face open to the whole sky would have 0.5."""
  dirs, w = sky_cells(t)
  lit, code = (np.array(t["cases"][case][face][k]).reshape(-1) for k in ("lit", "glass"))
  cos = np.clip(dirs @ np.array(t["faces"][face]), 0, None)
  return float((lit * through(d, normals, dirs, code) * cos * w).sum() / math.pi)


def clear_sky(p: dict) -> pd.DataFrame:
  s = p["sun"]
  loc = pvlib.location.Location(s["site"]["lat"], s["site"]["lon"], tz=s["site"]["tz"])
  t = pd.date_range(f"{s['year']}-01-01", f"{s['year'] + 1}-01-01", freq=f"{STEP_MIN}min", inclusive="left",
                    tz=s["site"]["tz"])
  sp = loc.get_solarposition(t)
  cs = loc.get_clearsky(t, solar_position=sp)
  df = pd.DataFrame({"elev": sp["apparent_elevation"].to_numpy(), "az": sp["azimuth"].to_numpy(),
                     "dni": cs["dni"].to_numpy(), "dhi": cs["dhi"].to_numpy()}, index=t)
  return df[df["elev"] > 0]


def faces_flux(t, d, normals, case, df, heading) -> dict:
  """Absorbed sun (W/m²) on each face of the device, for the car facing `heading` at each time of df."""
  rel = df["az"].to_numpy() - heading
  elev = df["elev"].to_numpy()
  dirs = ds.direction(elev, rel)
  out = {}
  for face, n in t["faces"].items():
    lit, code = lookup(t, case, face, elev, rel)
    cos = np.clip(dirs @ np.array(n), 0, None)
    beam = df["dni"].to_numpy() * lit * cos * through(d, normals, dirs, code)
    out[face] = d["absorptance"]["value"] * (beam + df["dhi"].to_numpy() * t["sky"][case][face])
  return out


def run(p: dict) -> dict:
  d = p["device_sun"]
  t = json.loads(TABLE.read_text(encoding="utf-8"))
  normals = glass_normals()
  w, h, depth = d["box_m"]["value"]
  area = {"front": w * h, "screen": w * h, "left": depth * h, "right": depth * h}
  model_w = d["model_flux_w_m2"]["value"] * area["front"]
  t["sky"] = {c: {f: sky_view(t, d, normals, c, f) for f in t["faces"]} for c in t["cases"]}
  df = clear_sky(p)
  heads = {"northbound": p["sun"]["corridor"]["northbound"]["heading"],
           "southbound": p["sun"]["corridor"]["southbound"]["heading"]} | {f"parked_{h:03.0f}": h for h in PARKED}
  out = {"about": "Synthetic (DSR-12), design aid, no evidence credit. Clear sky every day of the year at the corridor's "
                  "middle; the device's place on the glass and the glass's transmittance are estimates until T1.",
         "model": {"front_w_m2": d["model_flux_w_m2"]["value"], "power_w": round(model_w, 3),
                   "band_w": [round(model_w * x, 3) for x in p["uncertainty_irradiance"]]},
         "area_m2": area, "sky_view": {c: {f: round(v, 4) for f, v in fs.items()} for c, fs in t["sky"].items()},
         "cases": {}}
  summer = df.index.month.isin(SUMMER)
  for case in t["cases"]:
    res = {"headings": {}}
    for name, hd in heads.items():
      fl = faces_flux(t, d, normals, case, df, hd)
      power = sum(fl[f] * area[f] for f in fl)
      i = int(np.argmax(power))
      res["headings"][name] = {
        "heading": hd, "power_max_w": round(float(power[i]), 3), "when": df.index[i].strftime("%m-%d %H:%M"),
        "sun_at_max": [round(float(df["elev"].iloc[i]), 1), round(float((df["az"].iloc[i] - hd + 180) % 360 - 180), 1)],
        "faces_at_max_w": {f: round(float(fl[f][i] * area[f]), 3) for f in fl},
        "face_max_w_m2": {f: round(float(fl[f].max()), 1) for f in fl},
        "hours_over_model": round(float((power > model_w).sum() * STEP_MIN / 60), 1),
        "summer_power_max_w": round(float(power[summer].max()), 3)}
    parked = {k: v for k, v in res["headings"].items() if k.startswith("parked")}
    worst = max(parked, key=lambda k: parked[k]["power_max_w"])
    drive = max(("northbound", "southbound"), key=lambda k: res["headings"][k]["power_max_w"])
    res["worst_parked"], res["worst_driving"] = worst, drive
    res["front_max_w_m2"] = max(v["face_max_w_m2"]["front"] for v in res["headings"].values())
    res["power_max_w"] = max(v["power_max_w"] for v in res["headings"].values())
    res["summer_power_max_w"] = max(v["summer_power_max_w"] for v in res["headings"].values())
    res["face_max_w"] = {f: round(max(v["face_max_w_m2"][f] for v in res["headings"].values()) * area[f], 3)
                         for f in area}
    # the day traces for the figure: both corridor headings and the worst parked one, summer and winter
    res["days"] = {}
    for dn, day in DAYS.items():
      sel = df.loc[day]
      res["days"][dn] = {"hour": [round(x.hour + x.minute / 60, 3) for x in sel.index]}
      for name in ("northbound", "southbound", worst):
        fl = faces_flux(t, d, normals, case, sel, heads[name])
        res["days"][dn][name] = {f: [round(float(x * area[f]), 3) for x in fl[f]] for f in fl}
    out["cases"][case] = res
  return out


def markdown(r: dict, p: dict) -> str:
  d = p["device_sun"]
  m = r["model"]
  L = [
    "# Sun on the device through the car",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`weather/device_sun.py`](../weather/device_sun.py) from the ray cast through the Corolla mesh "
    "([`device_shading.py`](../assets/tools/device_shading.py), "
    "[`corolla-e210-device-shading.json`](../figures/corolla-e210-device-shading.json)); do not edit by hand. Clear "
    "sky every day; the device's place on the glass and the glass's transmittance are estimates until T1.",
    "",
    f"The heat model puts {m['front_w_m2']:.0f} W/m² on the device's windshield-side face, all day: "
    f"{m['power_w']:.2f} W into the box ({m['band_w'][0]:.2f}–{m['band_w'][1]:.2f} W over its uncertainty band), and "
    f"nothing on the other faces. The device hangs {d['mount_down_glass_m']['value']:.2f} m down the glass from its top "
    "edge, on the car's centre line, upright.",
    "",
    "## How much sky each face sees through the glass",
    "",
    "Diffuse factor through the glass, with transmittance (an upright face open to the whole sky: 0.5):",
    "",
    "| Face | Roof panel glass (the mesh) | Roof metal |",
    "|---|---|---|",
  ]
  names = {"front": "Windshield side", "screen": "Screen (cabin side)", "left": "Left side", "right": "Right side (fan)"}
  for f in names:
    L.append(f"| {names[f]} | {r['sky_view']['glass_roof'][f]:.3f} | {r['sky_view']['metal_roof'][f]:.3f} |")
  L += ["", "## Most sun into the box", "",
        "| Roof | Car | Most sun into the box | When (sun elevation, side) | Windshield side / screen / sides | "
        "Most in June–August | Hours a year over the model's |",
        "|---|---|---|---|---|---|---|"]
  for case, lab in (("glass_roof", "glass panel"), ("metal_roof", "metal")):
    c = r["cases"][case]
    for name in ("northbound", "southbound", c["worst_parked"]):
      v = c["headings"][name]
      car = name if not name.startswith("parked") else f"parked facing {v['heading']:.0f}° (the worst)"
      fa = v["faces_at_max_w"]
      side = "left" if v["sun_at_max"][1] < 0 else "right"
      L.append(f"| {lab} | {car} | {v['power_max_w']:.2f} W | {v['when']} ({v['sun_at_max'][0]:.0f}°, "
               f"{abs(v['sun_at_max'][1]):.0f}° {side}) | {fa['front']:.2f} / {fa['screen']:.2f} / "
               f"{fa['left'] + fa['right']:.2f} W | {v['summer_power_max_w']:.2f} W | {v['hours_over_model']:.0f} |")
  g, mm = r["cases"]["glass_roof"], r["cases"]["metal_roof"]
  ratio = g["power_max_w"] / m["power_w"]
  hot = g["summer_power_max_w"] / m["power_w"]
  inside = m["band_w"][0] <= g["power_max_w"] <= m["band_w"][1]
  L += ["", "## What this shows (generated)", "",
        "- **The windshield side is never shaded by the car.** The face sits just under the glass, so every direction "
        "in front of it and above the horizon is windshield; only the A-pillars cut the sun at grazing angles. What "
        "limits its sun is its angle: upright, it faces the sun squarely only when the sun is low ahead, and then "
        f"through glass at a steep angle. Its most is {g['front_max_w_m2']:.0f} W/m², against the model's "
        f"{m['front_w_m2']:.0f} W/m², on a winter day with the sun low ahead.",
        f"- **The screen side takes sun from behind**, through the rear window and, on the mesh, the roof panel: up to "
        f"{g['face_max_w']['screen']:.2f} W ({mm['face_max_w']['screen']:.2f} W with a metal roof) when the sun is "
        "low behind the car. The windshield side is dark then, so the box's total stays under its peak; the heat model "
        "puts no sun on that face, and puts it into the box all the same.",
        f"- **The most sun into the box** in the year is {g['power_max_w']:.2f} W with a glass roof panel and "
        f"{mm['power_max_w']:.2f} W with a metal roof: {ratio:.2f} times the model's {m['power_w']:.2f} W "
        f"({'inside' if inside else 'outside'} its band of {m['band_w'][0]:.2f}–{m['band_w'][1]:.2f} W). It comes in "
        "winter, when the cabin is cool.",
        f"- **In June–August**, when the heat matters, it is at most {g['summer_power_max_w']:.2f} W: {hot:.2f} times "
        "the model's. The high summer sun meets the upright face at a grazing angle.",
        "- For the heat model (TE-04 T1): its constant is about the year's peak, and "
        f"{1 / hot:.1f} times the most a summer day gives, so the hot-day bound carries margin on the sun. The model's "
        "input stays as it is until T1 measures the mount; then the summer value can replace it.",
        ""]
  return "\n".join(L)


def main(argv):
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("--check", action="store_true")
  ap.add_argument("--figures", action="store_true")
  a = ap.parse_args(argv[1:])
  p = yaml.safe_load((HERE / "params.yaml").read_text(encoding="utf-8"))
  th = yaml.safe_load((SIM / "thermal" / "params.yaml").read_text(encoding="utf-8"))
  p["uncertainty_irradiance"] = th["uncertainty"]["irradiance"]
  r = run(p)
  md = markdown(r, p)
  if a.check:
    from sun_glare import compare
    errs = ds.check(json.loads(TABLE.read_text(encoding="utf-8")))
    errs += compare(r, json.loads(OUT_JSON.read_text(encoding="utf-8")))
    if not errs and OUT_MD.read_text(encoding="utf-8") != md:
      errs.append(f"{OUT_MD.name} is stale")
    for e in errs[:20]:
      print("FAIL", e)
    print("device sun:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, separators=(",", ":")) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name, r["model"], r["sky_view"],
        {c: (v["power_max_w"], v["front_max_w_m2"], v["worst_parked"]) for c, v in r["cases"].items()})
  if a.figures:
    import fig_weather
    fig_weather.device_sun_figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
