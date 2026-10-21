#!/usr/bin/env python3
"""Fog, dew and frost on the windshield in front of the road camera (WP-C-06 TC-19, WP-V-03 KS-16).

Water forms on a glass face when the face is colder than the dew point of the air touching it (the frost point
below 0 °C). Three questions, on the corridor's climate (`climate-gsp.csv`, NOAA 1991–2020 hourly normals):
- **parked overnight**: the glass radiates to the sky (Berdahl–Martin clear-sky emissivity, raised by cloud) and dew
  or frost forms outside;
- **driving at 110 km/h**: the glass's inner face against the cabin's dew point, which the occupants' breath raises
  and the air conditioning lowers: fresh air, recirculation or automatic climate control;
- **clearing a frosted morning**: the defroster jet heats the glass from the vents up; the camera looks through the
  top of the glass, which clears last.

Each month-and-hour cell mixes the five NOAA sky-cover classes and calm against windy hours by their shares, at the
hour's normal temperature and dew point. Humid nights are a spread around that normal, so the shares here are the
normal night's, not a frequency; the sun on the glass is left out (it only dries it). Writes
`../results/windshield-fog.json` and `.md`.

    python3 windshield_fog.py --figures
    python3 windshield_fog.py --check

Synthetic (DSR-12), design aid, no evidence credit (DQ-413).
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
import climate  # noqa: E402

SIM = HERE.parent
GEOM = SIM / "figures" / "corolla-e210-geometry.json"
OUT_JSON = SIM / "results" / "windshield-fog.json"
OUT_MD = SIM / "results" / "windshield-fog.md"
SIGMA = 5.670374419e-8
K0 = 273.15
RV, RA, CP_AIR = 461.5, 287.05, 1005.0
SKY = ("clr", "few", "sct", "bkn", "ovc")
MODES = ("auto", "fresh", "recirc")


def e_water(t):
  """Saturation vapour pressure over water, kPa (Magnus, Alduchov and Eskridge 1996)."""
  t = np.asarray(t, float)
  return 0.61094 * np.exp(17.625 * t / (t + 243.04))


def e_ice(t):
  """Saturation vapour pressure over ice, kPa (Magnus, Alduchov and Eskridge 1996)."""
  t = np.asarray(t, float)
  return 0.61121 * np.exp(22.587 * t / (t + 273.86))


def e_sat(t):
  """Over water at or above 0 °C, over ice below: the face's own condensate."""
  t = np.asarray(t, float)
  return np.where(t >= 0.0, e_water(t), e_ice(t))


def dew_point(e):
  """The temperature at which water vapour of pressure e (kPa) saturates over water."""
  g = np.log(np.asarray(e, float) / 0.61094)
  return 243.04 * g / (17.625 - g)


def ratio(e, p):
  """Humidity ratio, kg water per kg dry air."""
  return 0.622 * e / (p - e)


def vapour(w, p):
  return p * w / (0.622 + w)


def sky_emissivity(td, okta, cloud_factor):
  """Berdahl and Martin 1984 clear-sky emissivity from the dew point (°C), raised toward 1 by cloud."""
  clr = 0.711 + 0.56 * (td / 100.0) + 0.73 * (td / 100.0) ** 2
  return clr + (1.0 - clr) * cloud_factor * okta / 8.0


def h_parked(v):
  """Outside convection of a parked car, W/m²K (Watmuff et al., convection only)."""
  return 2.8 + 3.0 * v


def h_driving(v, length):
  """Turbulent flat plate over the glass length (Incropera eq. 7.36), air near 10 °C."""
  nu_air, k_air, pr = 1.42e-5, 0.0246, 0.71
  re = v * length / nu_air
  return 0.037 * re ** 0.8 * pr ** (1 / 3) * k_air / length


def glass_r(g):
  return g["thickness_m"] / g["k"] + g["pvb_m"] / g["k_pvb"]


def faces(t_air, t_cabin, t_sky, f_sky, h_out, h_in, r_glass, eps, iters=30):
  """Steady outer and inner face temperatures (°C) of the glass: convection and long-wave outside (sky over f_sky,
  ground at air temperature over the rest), conduction through the glass, convection and long-wave inside."""
  ta, tc, ts = (np.asarray(x, float) for x in (t_air, t_cabin, t_sky))
  to = ta.copy()
  a = h_in / (h_in + 1 / r_glass)
  b = (1 / r_glass) / (h_in + 1 / r_glass)
  for _ in range(iters):
    tk, sk, ak = to + K0, ts + K0, ta + K0
    hrs = eps * SIGMA * f_sky * (tk ** 2 + sk ** 2) * (tk + sk)
    hrg = eps * SIGMA * (1 - f_sky) * (tk ** 2 + ak ** 2) * (tk + ak)
    to = (h_out * ta + hrs * ts + hrg * ta + a * tc / r_glass) / (h_out + hrs + hrg + (1 - b) / r_glass)
  ti = a * tc + b * to
  return to, ti


def setup(p):
  geom = json.loads(GEOM.read_text(encoding="utf-8"))["glass"]["windshield"]
  tilt = p["cabin"]["windshield"]["tilt_deg"]
  slant = math.hypot(np.ptp(geom["x_range_m"]), np.ptp(geom["y_range_m"]))
  return {"tilt": tilt, "f_sky": (1 + math.cos(math.radians(tilt))) / 2, "slant": slant,
          "width": p["cabin"]["windshield"]["area"] / slant}


def sky_temp(t_air, td, okta, f):
  eps = sky_emissivity(td, okta, f)
  return eps ** 0.25 * (np.asarray(t_air) + K0) - K0


def parked(p, clim, geo, cloud_factor=None):
  """Shares (0–1) of the normal hour with dew and with frost outside, mixing sky classes and calm against windy
  hours."""
  fp = p["fog"]
  cf = fp["sky"]["cloud_factor"]["value"] if cloud_factor is None else cloud_factor
  g = fp["glass"]
  r, eps = glass_r(g), g["emissivity"]
  h_in = p["cabin"]["h_inside"]["parked"] + fp["h_inside_rad"]["value"]
  calm = clim["calm"].to_numpy() / 100
  v_windy = clim["wind"].to_numpy() / np.maximum(1 - calm, 0.05)
  t, td = clim["t"].to_numpy(), clim["td"].to_numpy()
  e_air = e_water(td)
  dew, frost = np.zeros(len(clim)), np.zeros(len(clim))
  for s in SKY:
    w = clim[s].to_numpy() / 100
    ts = sky_temp(t, td, fp["sky"]["cover_okta"][s], cf)
    for wind_share, v in ((calm, fp["convection"]["calm_wind_m_s"]["value"]), (1 - calm, v_windy)):
      to, _ti = faces(t, t, ts, geo["f_sky"], h_parked(v), h_in, r, eps)
      wet = e_air > e_sat(to)
      dew += w * wind_share * (wet & (to >= 0))
      frost += w * wind_share * (wet & (to < 0))
  return dew, frost


def cabin_air(p, t_out, td_out, mode, occupants):
  """Cabin temperature and vapour pressure (kPa) in steady driving; for recirculation, the start (outside air)."""
  fp, c = p["fog"], p["cabin"]
  pr = fp["pressure_kpa"]["value"]
  tc = np.maximum(t_out, fp["cabin_setpoint_c"])
  w_out = ratio(e_water(td_out), pr)
  g = occupants * fp["breath_g_h"]["value"] / 3.6e6                 # kg/s of water
  fresh = c["fan_only_fresh_kg_s"]["value"]
  if mode == "auto":
    coil = c["ac"]["coil_c"]
    dried = np.minimum(w_out, ratio(e_water(coil), pr))
    w = np.where(t_out > fp["ac_lockout_c"]["value"], dried, w_out) + g / fresh
  elif mode == "fresh":
    w = w_out + g / fresh
  else:
    w = w_out
  return tc, vapour(w, pr)


def recirc_minutes(p, t_out, td_out, ti, occupants, ach=None):
  """Minutes of recirculation, heater on and no air conditioning, until the inner face fogs (inf: never; 0: at
  once). Only the body's leaks exchange the cabin air; seats, clothes and wet mats are left out."""
  fp, c = p["fog"], p["cabin"]
  pr = fp["pressure_kpa"]["value"]
  vol = c["air_volume_m3"]["value"]
  m_inf = 1.2 * vol * (fp["recirc_ach"]["value"] if ach is None else ach) / 3600
  tau = 1.2 * vol / m_inf
  g = occupants * fp["breath_g_h"]["value"] / 3.6e6
  w0 = ratio(e_water(td_out), pr)
  w_star = ratio(e_sat(ti), pr)
  x = (w_star - w0) * m_inf / g
  with np.errstate(divide="ignore", invalid="ignore"):
    t = np.where(x <= 0, 0.0, np.where(x >= 1, np.inf, -tau * np.log(1 - x) / 60))
  return t


def driving(p, clim, geo, occupants=None, ach=None):
  """Share of the normal hour with fog on the inner face at 110 km/h for each ventilation mode, and the minutes
  of recirculation to fog under a clear sky."""
  fp = p["fog"]
  n = fp["occupants"]["value"] if occupants is None else occupants
  g = fp["glass"]
  r, eps = glass_r(g), g["emissivity"]
  v = fp["drive_speed_kph"] / 3.6
  h_out = h_driving(v, geo["slant"])
  h_in = p["cabin"]["h_inside"]["blower"] + fp["h_inside_rad"]["value"]
  t, td = clim["t"].to_numpy(), clim["td"].to_numpy()
  out = {m: np.zeros(len(clim)) for m in MODES}
  rec = None
  for s in SKY:
    w = clim[s].to_numpy() / 100
    ts = sky_temp(t, td, fp["sky"]["cover_okta"][s], fp["sky"]["cloud_factor"]["value"])
    for m in ("auto", "fresh"):
      tc, e_c = cabin_air(p, t, td, m, n)
      _to, ti = faces(t, tc, ts, geo["f_sky"], h_out, h_in, r, eps)
      out[m] += w * (e_c > e_sat(ti))
    tc, _e = cabin_air(p, t, td, "recirc", n)
    _to, ti = faces(t, tc, ts, geo["f_sky"], h_out, h_in, r, eps)
    mins = recirc_minutes(p, t, td, ti, n, ach)
    out["recirc"] += w * ((mins < 60) & (t < fp["heater_below_c"]["value"]))
    if s == "clr":
      rec = mins
  return out, rec, h_out


def frost_night(p, clim, geo, depression=None):
  """Frost laid down outside on January's normal clear, calm night (kg/m²), by the Chilton–Colburn analogy; with
  `depression` (K) the dew point is that far below the air instead of its normal."""
  fp = p["fog"]
  m = fp["defrost"]["morning"]
  start, end = m["night"]
  hours = list(range(start, 24)) + list(range(end))
  c = clim[clim["month"] == m["month"]].set_index("hour")
  g = fp["glass"]
  h_in = p["cabin"]["h_inside"]["parked"] + fp["h_inside_rad"]["value"]
  v = fp["convection"]["calm_wind_m_s"]["value"]
  hc = h_parked(v)
  hm = hc / (1.2 * CP_AIR * fp["lewis_number"]["value"] ** (2 / 3))     # m/s
  mass, trace = 0.0, []
  for h in hours:
    t, td = float(c.loc[h, "t"]), float(c.loc[h, "td"])
    if depression is not None:
      td = t - depression
    ts = sky_temp(t, td, 0.0, fp["sky"]["cloud_factor"]["value"])
    to, _ti = faces(t, t, ts, geo["f_sky"], hc, h_in, glass_r(g), g["emissivity"])
    to = float(to)
    rho_air = e_water(td) * 1000 / (RV * (t + K0))
    rho_face = float(e_sat(to)) * 1000 / (RV * (to + K0))
    mass += max(hm * (rho_air - rho_face), 0.0) * 3600
    trace.append({"hour": h, "air": round(t, 2), "dew_point": round(td, 2), "glass": round(to, 2),
                  "frost_kg_m2": round(mass, 4)})
  return mass, trace


def defrost(p, clim, geo, frost_kg_m2, jet_h=None, decay=None, warmup=None, strips=40, dt=2.0, t_end=1800.0):
  """The morning: engine idling, defroster on. Each strip of the glass up from the vents is a lumped glass layer
  heated by the jet inside (h falls with height) and cooled outside (calm, clear sky); frost on it melts once it
  reaches 0 °C. Returns the minutes until each strip is clear and an energy balance."""
  fp = p["fog"]
  d = fp["defrost"]
  jet = d["jet_h"]["value"] if jet_h is None else jet_h
  ell = d["decay_m"]["value"] if decay is None else decay
  rate = (d["warmup_k_min"]["value"] if warmup is None else warmup) / 60
  m = d["morning"]
  c = clim[(clim["month"] == m["month"]) & (clim["hour"] == m["night"][1])].iloc[0]
  t_out, td = float(c["t"]), float(c["td"])
  t_sky = float(sky_temp(t_out, td, 0.0, fp["sky"]["cloud_factor"]["value"]))
  cap = p["cabin"]["windshield"]["heat_capacity"] / p["cabin"]["windshield"]["area"]   # J/m²K
  s = (np.arange(strips) + 0.5) / strips * geo["slant"]
  h_jet = jet * np.exp(-s / ell) + p["cabin"]["h_inside"]["blower"]
  hc = h_parked(fp["convection"]["calm_wind_m_s"]["value"])
  eps, f = fp["glass"]["emissivity"], geo["f_sky"]
  lf = 334e3
  start_t, _ = faces(t_out, t_out, t_sky, f, hc, p["cabin"]["h_inside"]["parked"] + fp["h_inside_rad"]["value"],
                     glass_r(fp["glass"]), eps)
  T = np.full(strips, float(start_t))
  ice = np.full(strips, frost_kg_m2)
  clear = np.full(strips, np.nan)
  e_in = e_store = e_melt = e_out = 0.0
  T0 = T.copy()
  for k in range(int(t_end / dt)):
    t = (k + 1) * dt
    t_jet = min(t_out + rate * t, d["outlet_c"]["value"])
    q_in = h_jet * (t_jet - T)
    tk, sk, ak = T + K0, t_sky + K0, t_out + K0
    q_out = hc * (T - t_out) + eps * SIGMA * (f * (tk ** 4 - sk ** 4) + (1 - f) * (tk ** 4 - ak ** 4))
    q = q_in - q_out
    T_new = T + dt * q / cap
    melting = (ice > 0) & (T_new > 0)
    if melting.any():
      spare = (T_new[melting] - 0.0) * cap                     # J/m² above 0 °C goes into the ice first
      melt = np.minimum(spare / lf, ice[melting])
      ice[melting] -= melt
      T_new[melting] -= melt * lf / cap
      e_melt += float((melt * lf).sum())
      done = melting.copy()
      done[melting] = ice[melting] <= 1e-12
      clear[done & np.isnan(clear)] = t / 60
    e_in += float(q_in.sum()) * dt
    e_out += float(q_out.sum()) * dt
    T = T_new
  e_store = float(((T - T0) * cap).sum())
  balance = (e_in - e_out - e_store - e_melt) / max(abs(e_in), 1.0)
  return {"s": s, "clear_min": clear, "t_out": t_out, "balance": balance, "t_end_min": t_end / 60}


def zone_minutes(res, geo, zone):
  frac = res["s"] / geo["slant"]
  sel = (frac >= zone[0]) & (frac <= zone[1])
  v = res["clear_min"][sel]
  return float(np.nanmax(v)) if not np.isnan(v).any() else None


def area_minutes(res, share):
  v = np.sort(np.where(np.isnan(res["clear_min"]), np.inf, res["clear_min"]))
  x = v[int(math.ceil(share * len(v))) - 1]
  return None if not np.isfinite(x) else float(x)


def run(p):
  clim = climate.load()
  geo = setup(p)
  fp = p["fog"]
  dew, frost_h = parked(p, clim, geo)
  park = dew + frost_h
  drive, rec, h_out = driving(p, clim, geo)
  drive4, _rec4, _ = driving(p, clim, geo, occupants=fp["occupants"]["high"])
  frost, trace = frost_night(p, clim, geo)
  heavy, _ = frost_night(p, clim, geo, fp["defrost"]["humid_night_depression_k"]["value"])
  rec_lo, _r, _ = driving(p, clim, geo, ach=fp["recirc_ach"]["high"])
  rec_hi, _r, _ = driving(p, clim, geo, ach=fp["recirc_ach"]["low"])
  zone = fp["defrost"]["camera_zone"]["value"]
  d = fp["defrost"]
  cases = {"nominal": {}}
  for k, lo_hi in (("jet_h", "jet_h"), ("decay", "decay_m"), ("warmup", "warmup_k_min")):
    for edge in ("low", "high"):
      cases[f"{k}_{edge}"] = {k: d[lo_hi][edge]}
  cases["heavy_frost"] = {"frost": heavy}
  dfr = {}
  for name, kw in cases.items():
    kw = dict(kw)
    res = defrost(p, clim, geo, kw.pop("frost", frost), **kw)
    dfr[name] = {"half_min": area_minutes(res, 0.5), "most_min": area_minutes(res, 0.9),
                 "camera_min": zone_minutes(res, geo, zone), "balance": round(res["balance"], 6),
                 "clear_min": [None if np.isnan(x) else round(float(x), 2) for x in res["clear_min"]]}
  nominal = defrost(p, clim, geo, frost)
  months = range(1, 13)
  def per_month(a):
    return {str(m): round(float(a[(clim["month"] == m).to_numpy()].sum()), 2) for m in months}
  days = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
  def hours_year(a):
    return round(float(sum(a[(clim["month"] == m).to_numpy()].sum() * days[m - 1] for m in months)), 0)
  rec_c = np.where(np.isfinite(rec), rec, -1.0)
  return {
    "about": "Synthetic (DSR-12), design aid, no evidence credit. Normal-year climate (NOAA 1991–2020 hourly normals, "
             "GSP); estimated car inputs.",
    "geometry": {k: round(v, 3) for k, v in geo.items()},
    "h_out_driving": round(float(h_out), 1),
    "grid": {"month": clim["month"].tolist(), "hour": clim["hour"].tolist(),
             "parked": [round(float(x), 3) for x in park],
             **{f"drive_{m}": [round(float(x), 3) for x in drive[m]] for m in MODES},
             "drive_fresh_4": [round(float(x), 3) for x in drive4["fresh"]],
             "recirc_clear_min": [round(float(x), 1) for x in rec_c]},
    "hours_per_year": {"parked": hours_year(park), "parked_dew": hours_year(dew), "parked_frost": hours_year(frost_h),
                       **{f"drive_{m}": hours_year(drive[m]) for m in MODES},
                       "drive_fresh_4": hours_year(drive4["fresh"]),
                       "drive_recirc_band": [hours_year(rec_lo["recirc"]), hours_year(rec_hi["recirc"])]},
    "per_month_hours_per_day": {"parked": per_month(park), "parked_frost": per_month(frost_h), **{f"drive_{m}": per_month(drive[m]) for m in MODES}},
    "frost_night": {"kg_m2": round(frost, 4), "humid_kg_m2": round(heavy, 4), "trace": trace},
    "defrost": {"t_out": round(nominal["t_out"], 2), "camera_zone": zone, "cases": dfr},
  }


def markdown(r, p):
  hy, d, fr = r["hours_per_year"], r["defrost"], r["frost_night"]
  nom, hv = d["cases"]["nominal"], d["cases"]["heavy_frost"]
  def mm(x):
    return "not in 30 min" if x is None else f"{x:.0f} min"
  def band(key):
    vals = [c[key] for n, c in d["cases"].items() if n != "heavy_frost"]
    if any(v is None for v in vals):
      return f"{mm(min(v for v in vals if v is not None))} to not in 30 min"
    return f"{min(vals):.0f}–{max(vals):.0f} min"
  rm = r["per_month_hours_per_day"]
  months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
  L = [
    "# Fog, dew and frost on the windshield in front of the road camera",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`weather/windshield_fog.py`](../weather/windshield_fog.py) from [`params.yaml`](../weather/params.yaml) and "
    "[`climate-gsp.csv`](../weather/climate-gsp.csv) (NOAA 1991–2020 hourly normals, Greenville-Spartanburg); do not "
    "edit by hand. The car's inputs are estimates; each hour is the normal hour, so these are shares of a normal "
    "year, not counts of foggy days.",
    "",
    "## Hours of a normal year with water on the glass",
    "",
    "Counted over all 8760 hours of the year: for the driving rows, the hours in which a drive would fog the glass.",
    "",
    "| Where and when | Hours a year | What it means for the camera |",
    "|---|---|---|",
    f"| Outside, parked in the open: dew | {hy['parked_dew']:.0f} | The wipers clear it in a sweep |",
    f"| Outside, parked in the open: frost | {hy['parked_frost']:.0f} | Needs the defroster (or a scraper) before driving off |",
    "| Inside, driving at 110 km/h, automatic climate control (air conditioning dries the air above "
    f"{p['fog']['ac_lockout_c']['value']:.0f} °C) | {hy['drive_auto']:.0f} | |",
    f"| Inside, driving, fresh air, no air conditioning, the driver alone | {hy['drive_fresh']:.0f} | |",
    f"| The same with four people | {hy['drive_fresh_4']:.0f} | |",
    f"| Inside, driving, recirculation, no air conditioning, heater on: fogs within the hour | {hy['drive_recirc']:.0f} "
    f"(band {hy['drive_recirc_band'][0]:.0f}–{hy['drive_recirc_band'][1]:.0f} with the body's leaks at "
    f"{p['fog']['recirc_ach']['high']:.0f} to {p['fog']['recirc_ach']['low']:.0f} air changes an hour) | Fog on the "
    "inside, in front of the camera; the wipers cannot reach it |",
    "",
    "| Month | " + " | ".join(months) + " |",
    "|---|" + "---|" * 12,
    "| Parked, dew or frost outside (h/day) | " + " | ".join(f"{rm['parked'][str(m)]:.1f}" for m in range(1, 13)) + " |",
    "| of which frost (h/day) | " + " | ".join(f"{rm['parked_frost'][str(m)]:.1f}" for m in range(1, 13)) + " |",
    "| Driving, recirculation (h/day) | " + " | ".join(f"{rm['drive_recirc'][str(m)]:.1f}" for m in range(1, 13)) + " |",
    "",
    "## Clearing a frosted January morning",
    "",
    f"January's normal clear, calm night lays down about **{1000 * fr['kg_m2']:.0f} g/m²** of frost on the glass by "
    f"07:00 ({d['t_out']:.1f} °C outside); a humid night with the same temperatures, about "
    f"**{1000 * fr['humid_kg_m2']:.0f} g/m²**. Engine idling, defroster on; clear means the frost has melted:",
    "",
    "| | Normal night | Band (jet strength, its reach up the glass, heater warm-up, one at a time) | Humid night |",
    "|---|---|---|---|",
    f"| Half the glass clear | {mm(nom['half_min'])} | {band('half_min')} | {mm(hv['half_min'])} |",
    f"| 90 % of the glass clear | {mm(nom['most_min'])} | {band('most_min')} | {mm(hv['most_min'])} |",
    f"| The camera's view clear ({100 * d['camera_zone'][0]:.0f}–{100 * d['camera_zone'][1]:.0f} % of the way up) | "
    f"{mm(nom['camera_min'])} | {band('camera_min')} | {mm(hv['camera_min'])} |",
    "",
    "## What this shows (generated)",
    "",
    f"- Water outside is the common case: dew for about {hy['parked_dew']:.0f} hours of a normal year, most on humid "
    f"summer and autumn nights, which the wipers clear, and frost for about {hy['parked_frost']:.0f}, in winter. "
    "Frost is cleared before the drive, and **the camera's view clears last**: the defroster jet enters at the "
    f"bottom, and the top of the glass clears about {hv['camera_min'] - hv['half_min']:.0f} min after half of it on a "
    "humid night." if hv["camera_min"] is not None and hv["half_min"] is not None else
    f"- Water outside: dew for about {hy['parked_dew']:.0f} hours of a normal year, frost for {hy['parked_frost']:.0f}.",
    "- The normal year understates frost: real nights scatter around the normal, and the frosty ones are the clear, "
    "calm, colder ones. The count says when to expect it, not how often; local logs and photos from the car set it.",
    f"- Driving at 110 km/h, the outside air keeps the glass close to its own temperature; with fresh air the cabin "
    f"stays dry enough ({hy['drive_fresh']:.0f} h a year alone, {hy['drive_fresh_4']:.0f} h with four people).",
    f"- **Recirculation without air conditioning** is the case that fogs the glass while driving: within the hour "
    f"in {hy['drive_recirc']:.0f} hours of a normal year, from October to May, and the count rests on how leaky the "
    f"body is ({hy['drive_recirc_band'][0]:.0f}–{hy['drive_recirc_band'][1]:.0f} h). Automatic climate control dries "
    f"the air and keeps it to {hy['drive_auto']:.0f} h.",
    "- For KS-16 (camera obstruction): fog on the inside is a slow, whole-view obstruction that the driver also sees. "
    "Two lines for the user information and the installation checks: start only once the glass in front of the "
    "camera is clear, and keep the ventilation on fresh air or automatic in the cold months.",
    "",
  ]
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
    print("windshield fog:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, separators=(",", ":")) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name, r["hours_per_year"], r["frost_night"]["kg_m2"],
        {k: (v["half_min"], v["camera_min"]) for k, v in r["defrost"]["cases"].items()}, r["h_out_driving"])
  if a.figures:
    import fig_weather
    fig_weather.fog_figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
