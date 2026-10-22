#!/usr/bin/env python3
"""Cabin heat soak (WP-C-02 OI-3, WP-C-06 TC-21): how hot the air at the device mount gets, parked and driving.

A lumped heat model of the Corolla's cabin: cabin air, windshield, dashboard, interior (seats, trim) and shell (roof,
doors, other glass), driven by clear-sky sun on each glazed and opaque surface (pvlib: Ineichen clear sky, isotropic
sky on the tilted planes) and a daily outside-temperature curve. The car parks in the sun, then drives with the air
conditioning on (or off). The air at the device mount is the cabin air plus a share of the glass's excess.

Its answer goes to the device heat model (`../thermal`): the mount-air temperature during a drive, against the
candidate ambient bound read from `../results/thermal-pilot.json`. Writes `../results/cabin-soak.json` and `.md`.

    python3 cabin_soak.py --figures
    python3 cabin_soak.py --check

Every input is an estimate until the logger at the mount (DQ-412) measures it; the model is checked against the
McLaren et al. 2005 parked-car measurements. Synthetic (DSR-12), design aid, no evidence credit (DQ-413).
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
OUT_JSON = HERE.parent / "results" / "cabin-soak.json"
OUT_MD = HERE.parent / "results" / "cabin-soak.md"
THERMAL = HERE.parent / "results" / "thermal-pilot.json"
RHO_AIR, CP_AIR = 1.2, 1005.0
STEP_S = 10.0
NODES = ("air", "glass", "dash", "interior", "shell")


def outside(t_h, tmin, tmax):
  """Daily outside temperature: minimum at 06:00, maximum at 15:00 (cosine between)."""
  t = np.asarray(t_h, float)
  rise = (t >= 6) & (t < 15)
  a = np.where(rise, (t - 6) / 9, 1 - ((t - 15) % 24) / 15)
  return tmin + (tmax - tmin) * (1 - np.cos(math.pi * np.clip(a, 0, 1))) / 2


def h_out(v):
  """Exterior convection (McAdams): 5.7 + 3.8 v below 5 m/s, 7.4 v^0.78 above."""
  return 5.7 + 3.8 * v if v <= 5 else 7.4 * v ** 0.78


def sun_loads(c, site, times, facing):
  """Absorbed and transmitted sun (W) on each surface for a car facing `facing` (deg) at each time."""
  loc = pvlib.location.Location(site["lat"], site["lon"], tz=site["tz"])
  sp = loc.get_solarposition(times)
  cs = loc.get_clearsky(times, solar_position=sp)
  def poa(tilt, az):
    return pvlib.irradiance.get_total_irradiance(tilt, az % 360, sp["apparent_zenith"], sp["azimuth"], cs["dni"],
                                                 cs["ghi"], cs["dhi"], albedo=0.2)["poa_global"].fillna(0).to_numpy()
  w, rf, sd, rr = c["windshield"], c["roof"], c["side_windows"], c["rear_window"]
  p_ws = poa(w["tilt_deg"], facing)
  p_roof = poa(0.0, facing)
  p_side = poa(90.0, facing + 90) + poa(90.0, facing - 90)
  p_rear = poa(rr["tilt_deg"], facing + 180)
  through_ws = p_ws * w["area"] * w["transmittance"]
  through_other = (p_side * sd["area_each"] + p_rear * rr["area"]) * sd["transmittance"]
  share = c["dash"]["share_of_windshield_sun"]
  return {"glass": p_ws * w["area"] * w["absorptance"],
          "dash": through_ws * share,
          "interior": through_ws * (1 - share) + through_other,
          "shell": p_roof * rf["area"] * rf["absorptance"]
                   + (p_side * sd["area_each"] + p_rear * rr["area"]) * sd["absorptance"],
          "ghi": cs["ghi"].to_numpy()}


def simulate(p, phases, date, tmin, tmax, start_temp=None):
  """phases: list of (start 'HH:MM', end 'HH:MM', mode, facing, speed_kph, ac). Returns a DataFrame per step."""
  c, site = p["cabin"], p["sun"]["site"]
  t0 = pd.Timestamp(f"{date} {phases[0][0]}", tz=site["tz"])
  t1 = pd.Timestamp(f"{date} {phases[-1][1]}", tz=site["tz"])
  times = pd.date_range(t0, t1, freq=f"{int(STEP_S)}s")
  hours = (times.hour + times.minute / 60 + times.second / 3600).to_numpy()
  t_out = outside(hours, tmin, tmax)
  cap = {"air": RHO_AIR * CP_AIR * c["air_volume_m3"]["value"], "glass": c["windshield"]["heat_capacity"],
         "dash": c["dash"]["heat_capacity"], "interior": c["interior"]["heat_capacity"],
         "shell": c["shell"]["heat_capacity"]}
  hr, dsky = c["h_sky_rad"]["value"], c["h_sky_rad"]["sky_below_air"]
  aw, ad, ai, ash = c["windshield"]["area"], c["dash"]["area"], c["interior"]["area"], c["shell"]["area"]
  T = {n: (t_out[0] if start_temp is None else start_temp) for n in NODES}
  rows = []
  phase_idx = np.zeros(len(times), dtype=int)
  for k, (a, b, *_rest) in enumerate(phases):
    ta, tb = pd.Timestamp(f"{date} {a}", tz=site["tz"]), pd.Timestamp(f"{date} {b}", tz=site["tz"])
    phase_idx[(times >= ta) & (times <= tb)] = k
  loads = {}
  for k, (_a, _b, _mode, facing, _v, _ac) in enumerate(phases):
    loads[k] = sun_loads(c, site, times, facing)
  infil = RHO_AIR * c["air_volume_m3"]["value"] * c["infiltration_ach"]["value"] / 3600 * CP_AIR
  mix = c["mount_mix"]["value"]
  for i in range(len(times)):
    k = phase_idx[i]
    mode, v_kph, ac = phases[k][2], phases[k][4], phases[k][5]
    L = {n: loads[k][n][i] for n in ("glass", "dash", "interior", "shell")}
    driving = mode == "drive"
    hi = c["h_inside"]["blower" if driving else "parked"]
    ho = h_out(v_kph / 3.6 if driving else c["wind_parked_m_s"])
    to, tsky = t_out[i], t_out[i] - dsky
    q = {n: 0.0 for n in NODES}
    for n in ("glass", "dash", "interior", "shell"):
      q[n] += L[n]
    for n, area in (("glass", aw), ("shell", ash)):          # outside: convection and long-wave to the sky
      q[n] += area * (ho * (to - T[n]) + hr * (tsky - T[n]))
    hrd = c["dash"]["h_rad_cabin"] * ad / 2
    for a, b, g in (("glass", "air", aw * hi), ("dash", "air", ad * hi), ("interior", "air", ai * hi),
                    ("shell", "air", ash * hi), ("dash", "glass", ad * 5.0 * 0.5), ("dash", "shell", 2.0),
                    ("dash", "interior", hrd), ("dash", "shell", hrd)):
      f = g * (T[a] - T[b])
      q[a] -= f
      q[b] += f
    q["air"] += infil * (to - T["air"])
    q_ac = 0.0
    if driving and ac:
      a = c["ac"]
      want = np.clip((T["air"] - a["setpoint_c"]) / 2.0, 0, 1)
      q_ac = min(a["capacity_w"], a["airflow_kg_s"] * CP_AIR * max(T["air"] - a["coil_c"], 0)) * want
      q["air"] -= q_ac
    elif driving:
      q["air"] += c["fan_only_fresh_kg_s"]["value"] * CP_AIR * (to - T["air"])
    if i % 12 == 0:
      rows.append({"t": times[i], "outside": to, **{n: T[n] for n in NODES},
                   "mount": T["air"] + mix * (T["glass"] - T["air"]), "q_ac": q_ac, "ghi": loads[k]["ghi"][i],
                   "phase": mode})
    for n in NODES:
      T[n] += STEP_S * q[n] / cap[n]
  return pd.DataFrame(rows).set_index("t")


def scenario(p, s):
  ph = [(s["park"][0], s["park"][1], "park", s["park_facing"], 0.0, False),
        (s["drive"][0], s["drive"][1], "drive", s["drive_heading"], s["speed_kph"], s["ac"])]
  return simulate(p, ph, s["date"], s["t_min"], s["t_max"])


def mclaren(p, ambient):
  """The McLaren set-up: closed car starting at ambient, 60 min in clear sun around noon, constant ambient."""
  ph = [("12:00", "13:00", "park", 180.0, 0.0, False)]
  df = simulate(p, ph, "2027-06-21", ambient, ambient, start_temp=ambient)
  rise = df["air"] - ambient
  return float(rise.iloc[-1]), float(rise[df.index <= df.index[0] + pd.Timedelta(minutes=30)].iloc[-1])


def run(p):
  bound = json.loads(THERMAL.read_text(encoding="utf-8"))["bound"]
  out = {"about": "Synthetic (DSR-12), design aid, no evidence credit. Estimated inputs; clear sky.",
         "heat_model_bound": bound, "scenarios": {}, "mclaren": {}}
  for name, s in p["cabin"]["scenarios"].items():
    df = scenario(p, s)
    drive = df[df["phase"] == "drive"]
    park = df[df["phase"] == "park"]
    over = drive["mount"] > bound["worst_edge"]
    out["scenarios"][name] = {
      "t_min": [round((t - df.index[0]).total_seconds() / 60, 1) for t in df.index],
      **{n: [round(float(v), 2) for v in df[n]] for n in ("outside", "air", "glass", "dash", "mount")},
      "drive_starts_min": round((drive.index[0] - df.index[0]).total_seconds() / 60, 1),
      "park_end": {n: round(float(park[n].iloc[-1]), 1) for n in ("air", "glass", "dash", "mount", "outside")},
      "drive_mount_max": round(float(drive["mount"].max()), 1),
      "drive_mount_last": round(float(drive["mount"].iloc[-1]), 1),
      "drive_minutes_above_worst_bound": round(float(over.sum()) * 2.0, 0),
      "ac": s["ac"]}
  m = p["cabin"]["mclaren"]
  for amb in m["ambient_c"]:
    r60, r30 = mclaren(p, amb)
    out["mclaren"][str(amb)] = {"rise_60": round(r60, 1), "share_30": round(r30 / r60, 2)}
  return out


def markdown(r, p):
  b, m = r["heat_model_bound"], p["cabin"]["mclaren"]
  names = {"hot_july": "Hot July day, AC on", "hot_july_ac_off": "Hot July day, AC off (fan, fresh air)",
           "mild_april": "Mild April day, AC on"}
  L = [
    "# Cabin heat soak: the air at the device mount, parked and driving",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`weather/cabin_soak.py`](../weather/cabin_soak.py) from [`params.yaml`](../weather/params.yaml); do not edit "
    "by hand. **Every cabin input is an estimate** until the logger at the mount measures it (DQ-412); clear sky.",
    "",
    f"Each day: parked in the sun facing south 12:00–14:00, then driving southwest on I-85 at 100 km/h 14:00–15:00. "
    f"The device heat model's candidate bound for the air at the mount is **{b['worst_edge']} °C** (worst edge) and "
    f"{b['nominal']} °C (nominal), read from [`thermal-pilot.json`](thermal-pilot.json).",
    "",
    "| Day | Outside at 14:00 | At the end of parking: cabin air / glass / dash / mount | Mount air while driving: highest, after 60 min | Minutes of the drive above the worst-edge bound |",
    "|---|---|---|---|---|",
  ]
  for k, d in r["scenarios"].items():
    e = d["park_end"]
    L.append(f"| {names.get(k, k)} | {e['outside']:.0f} °C | {e['air']:.0f} / {e['glass']:.0f} / {e['dash']:.0f} / "
             f"{e['mount']:.0f} °C | {d['drive_mount_max']:.0f} °C, {d['drive_mount_last']:.0f} °C | "
             f"{d['drive_minutes_above_worst_bound']:.0f} |")
  L += ["", "## Check against measured parked cars (McLaren et al. 2005)", "",
        f"Measured: about {m['rise_60min_k']:.0f} K rise of cabin air in 60 min on clear days, the same at any ambient "
        f"from {m['ambient_c'][0]:.0f} to {m['ambient_c'][1]:.0f} °C, {100 * m['share_30min']:.0f} % of it in the "
        "first 30 min (a dark sedan in California).", "",
        "| Ambient | Model rise in 60 min | Share in the first 30 min |", "|---|---|---|"]
  for a, v in r["mclaren"].items():
    L.append(f"| {float(a):.0f} °C | {v['rise_60']:.1f} K | {100 * v['share_30']:.0f} % |")
  hot, off = r["scenarios"]["hot_july"], r["scenarios"]["hot_july_ac_off"]
  wb = b["worst_edge"]
  def above(v):
    return "above" if v > wb else "below"
  L += ["", "## What this shows (generated)", "",
        f"- Parked on a hot day, the mount air reaches {hot['park_end']['mount']:.0f} °C, {above(hot['park_end']['mount'])} "
        f"the worst-edge bound ({wb} °C), and the glass {hot['park_end']['glass']:.0f} °C: the device starts its drive hot.",
        f"- With the AC on, the mount air is above the worst-edge bound for {hot['drive_minutes_above_worst_bound']:.0f} "
        f"min of the drive and ends at {hot['drive_mount_last']:.0f} °C.",
        f"- With the AC off it is above it for {off['drive_minutes_above_worst_bound']:.0f} min and ends at "
        f"{off['drive_mount_last']:.0f} °C, {above(off['drive_mount_last'])} the bound.",
        "- The heat model assumes a constant cabin temperature; this curve (a hot start that the AC pulls down) is the "
        "input it should take instead. The logger at the mount (DQ-412) checks both.", ""]
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
    print("cabin soak:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, separators=(",", ":")) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name, r["mclaren"],
        {k: (v["park_end"]["mount"], v["drive_mount_max"], v["drive_minutes_above_worst_bound"]) for k, v in r["scenarios"].items()})
  if a.figures:
    import fig_weather
    fig_weather.cabin_figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
