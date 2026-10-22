#!/usr/bin/env python3
"""Checks of the weather physics: what would catch a wrong formula, unit or input.

Sun
  S1  pvlib's SPA reproduces the published NREL reference case (Reda and Andreas, NREL/TP-560-34302).
  S2  An independent solar position (NOAA's algorithm, written here in numpy) agrees with SPA over a year.
  S3  The camera's field of view is read from camera.py, and a sun inside it is counted, one outside is not.
  S4  Sanity: at the June solstice the sun rises near 61° azimuth here; a northbound heading sees it, north never does.
Water
  W1  The metric film equation equals the imperial one (3.38e-3, in, ft, in/h, ft/ft) after unit conversion.
  W2  PAVDRN's two branches meet at 0.095 in, as its authors fitted them.
  W3  NASA's formula: 10.35 sqrt(p) mph; at 35 psi about 98.5 km/h.
  W4  Monotone: more rain, a longer path or a flatter slope never raises the hydroplaning speed.
  W5  The ODD speed bound is the one WP-C-02 states.
Fog on the windshield
  F1  Magnus over water and ice against the ASHRAE saturation table (Hyland and Wexler), within 0.5 %.
  F2  Frost forms at an air temperature of 2 °C on a clear, calm night (NWS: frost at 33–36 °F) and not under
      overcast; with the sky and cabin at air temperature the glass is at air temperature.
  F3  Recirculation: the closed-form minutes to fog equal a time-stepped moisture balance.
  F4  The defroster run's energy balance closes (heat in = heat out + stored + melting) within 0.1 %.
  F5  The climate table: 288 rows, sky shares add to 100 %, and each month's mean of the hourly normals is within
      1 K of NOAA's separate monthly normal (the two average different things: 24 hours against (max + min)/2).
  F6  At 110 km/h the flat-plate convection over the glass agrees with Watmuff's within 10 %.
Wet braking
  B1  The friction table is the handbook's at its nodes, and interpolation stays between neighbouring nodes.
  B2  The item's bound is read from opendbc (−3.5 m/s²) and equals WP-C-02 F-02; a level road needs 3.5/9.81.
  B3  Two sources agree: at 2 mm of water and speeds above NASA's hydroplaning speed the handbook gives at most 0.05.
  B4  Stopping distance: v·t + v²/2a, and the 110 km/h, 3.5 m/s² stop is 133 m plus the reaction distance.
Road crown
  R1  The roll path read from openpilot is the one reviewed: compensation by params.roll·g, calibration roll taken as
      zero, 20 Hz, process noise 1°/√s, fallback noise 10°, validity limit 1.5°. A change in the code fails here.
  R2  The steady Kalman gain solves the scalar Riccati equation in closed form, and a noisier localizer gives a slower
      filter.
  R3  The uncompensated push equals g × slope within 1 % (the plant's straight-drift convention); no mount roll gives
      no mount error; a crown change with a near-perfect localizer leaves almost nothing.

Synthetic (DSR-12), design aid, no evidence credit.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import pvlib
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import climate  # noqa: E402
import hydroplaning as hp  # noqa: E402
import road_crown as rc  # noqa: E402
import wet_braking as wb  # noqa: E402
import windshield_fog as wf  # noqa: E402
import cabin_soak as cs  # noqa: E402
import crosswind as cw  # noqa: E402
import sun_glare as sg  # noqa: E402

P = yaml.safe_load((HERE / "params.yaml").read_text(encoding="utf-8"))
WPC02 = HERE.parents[1] / "02-concept" / "WP-C-02-odd-and-intended-functionality.md"


def noaa(t_utc: pd.DatetimeIndex, lat: float, lon: float):
  """NOAA solar position (the ESRL spreadsheet algorithm): true elevation and azimuth in degrees, no refraction."""
  jd = t_utc.to_julian_date().to_numpy()
  jc = (jd - 2451545.0) / 36525.0
  L0 = np.radians((280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360)
  M = np.radians(357.52911 + jc * (35999.05029 - 0.0001537 * jc))
  e = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)
  C = np.radians(np.sin(M) * (1.914602 - jc * (0.004817 + 0.000014 * jc)) + np.sin(2 * M) * (0.019993 - 0.000101 * jc)
                 + np.sin(3 * M) * 0.000289)
  om = np.radians(125.04 - 1934.136 * jc)
  lam = L0 + C - np.radians(0.00569 + 0.00478 * np.sin(om))
  eps = np.radians(23 + (26 + (21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))) / 60) / 60 + 0.00256 * np.cos(om))
  dec = np.arcsin(np.sin(eps) * np.sin(lam))
  y = np.tan(eps / 2) ** 2
  eot = 4 * np.degrees(y * np.sin(2 * L0) - 2 * e * np.sin(M) + 4 * e * y * np.sin(M) * np.cos(2 * L0)
                       - 0.5 * y * y * np.sin(4 * L0) - 1.25 * e * e * np.sin(2 * M))
  minutes = (t_utc.hour * 60 + t_utc.minute + t_utc.second / 60).to_numpy()
  tst = (minutes + eot + 4 * lon) % 1440
  ha = np.radians(np.where(tst / 4 < 0, tst / 4 + 180, tst / 4 - 180))
  la = np.radians(lat)
  cz = np.clip(np.sin(la) * np.sin(dec) + np.cos(la) * np.cos(dec) * np.cos(ha), -1, 1)
  z = np.arccos(cz)
  ca = np.clip((np.sin(la) * np.cos(z) - np.sin(dec)) / (np.cos(la) * np.sin(z)), -1, 1)
  az = np.where(ha > 0, (np.degrees(np.arccos(ca)) + 180) % 360, (540 - np.degrees(np.arccos(ca))) % 360)
  return 90 - np.degrees(z), az


class Sun(unittest.TestCase):
  def test_s1_nrel_reference(self):
    t = pd.DatetimeIndex([pd.Timestamp("2003-10-17 12:30:30", tz="Etc/GMT+7")])
    sp = pvlib.solarposition.spa_python(t, 39.742476, -105.1786, altitude=1830.14, pressure=82000, temperature=11,
                                        delta_t=67, atmos_refract=0.5667)
    self.assertAlmostEqual(float(sp["apparent_zenith"].iloc[0]), 50.11162, places=4)
    self.assertAlmostEqual(float(sp["azimuth"].iloc[0]), 194.34024, places=4)

  def test_s2_noaa_cross_check(self):
    s = P["sun"]
    t = pd.date_range("2027-01-01", "2028-01-01", freq="37min", inclusive="left", tz="UTC")
    sp = pvlib.solarposition.spa_python(t, s["site"]["lat"], s["site"]["lon"])
    el, az = noaa(t, s["site"]["lat"], s["site"]["lon"])
    up = sp["elevation"].to_numpy() > 1
    self.assertLess(np.abs(el - sp["elevation"].to_numpy())[up].max(), 0.05)
    self.assertLess(np.abs(sg.offaxis(az, 0) - sg.offaxis(sp["azimuth"].to_numpy(), 0))[up].max(), 0.1)

  def test_s3_camera_and_frame(self):
    fov = sg.camera_fov()
    self.assertEqual((fov["width_px"], fov["height_px"], fov["focal_px"]), (1928, 1208, 2648.0))
    self.assertAlmostEqual(fov["hfov_deg"], 40.0, places=1)
    self.assertAlmostEqual(fov["vfov_deg"], 25.7, places=1)
    df = pd.DataFrame({"elev": [5.0, 5.0, 14.0, -1.0], "az": [80.0, 84.0, 60.0, 60.0]})
    m = sg.masks(df, 60.0, fov, P)
    self.assertEqual(list(m["in_view"]), [True, False, False, False])   # 20° off is in, 24° off is out; too high; set

  def test_s4_solstice_sanity(self):
    s = P["sun"]
    t = pd.date_range("2027-06-21 05:30", "2027-06-21 08:00", freq="1min", tz=s["site"]["tz"])
    sp = pvlib.solarposition.spa_python(t, s["site"]["lat"], s["site"]["lon"])
    rise = sp[sp["apparent_elevation"] > 0].iloc[0]
    self.assertTrue(58 < rise["azimuth"] < 64, rise["azimuth"])
    r = sg.run(P)
    self.assertGreater(r["corridor"]["northbound"]["by_month_h"][5], 0)   # June mornings
    self.assertEqual(r["by_heading_h"]["in_view"][0], 0.0)                # heading north: never


class Water(unittest.TestCase):
  def test_w1_metric_equals_imperial(self):
    T, L, I, S = 0.8, 11.0, 50.0, 2.0   # mm, m, mm/h, %
    imperial_in = 3.38e-3 * (T / 25.4) ** 0.11 * (L / 0.3048) ** 0.43 * (I / 25.4) ** 0.59 / (S / 100) ** 0.42 - T / 25.4
    metric_mm = float(hp.film_mm([I], L, S, T)[0])
    self.assertLess(abs(metric_mm - imperial_in * 25.4) / metric_mm, 0.01)

  def test_w2_branches_meet(self):
    # Where the texture-free term governs (fine texture), the thin-film fit and the thick-film fit meet at 0.095 in.
    # With coarse texture the thick-film branch takes the texture term and jumps (about 4 mph at 0.05 in): a property
    # of the published model, stated in the README, not of this code.
    lo = hp.pavdrn_mph([0.095 - 1e-9], 0.01)[0]
    hi = hp.pavdrn_mph([0.095], 0.01)[0]
    self.assertLess(abs(lo - hi), 0.1, (lo, hi))
    self.assertAlmostEqual(hi, 3.09 * (10.409 / 0.095 ** 0.06 + 3.507), places=9)

  def test_w3_nasa(self):
    self.assertAlmostEqual(hp.nasa_mph(100), 103.5)
    self.assertAlmostEqual(hp.nasa_mph(35) * hp.MPH, 98.5, places=1)

  def test_w4_monotone(self):
    r = np.array([1, 5, 10, 20, 40, 80, 160], float)
    base = hp.pavdrn_mph(hp.film_mm(r, 7.3, 2.0, 0.8) / 25.4, 0.8 / 25.4)
    for v in (hp.pavdrn_mph(hp.film_mm(r, 11.0, 2.0, 0.8) / 25.4, 0.8 / 25.4),
              hp.pavdrn_mph(hp.film_mm(r, 7.3, 1.5, 0.8) / 25.4, 0.8 / 25.4)):
      self.assertTrue(np.all(v <= base + 1e-9))
    self.assertTrue(np.all(np.diff(base[np.isfinite(base)]) <= 1e-9))

  def test_w5_odd_bound_from_wp_c02(self):
    m = re.search(r"\| Speed \| Ego speed \| 0 – (\d+) km/h", WPC02.read_text(encoding="utf-8"))
    self.assertEqual(float(m.group(1)), P["water"]["odd_speed_kph"]["value"])


class Cabin(unittest.TestCase):
  def test_c1_mclaren(self):
    m = P["cabin"]["mclaren"]
    rises = []
    for amb in m["ambient_c"]:
      r60, r30 = cs.mclaren(P, amb)
      self.assertLess(abs(r60 - m["rise_60min_k"]), m["tolerance_k"], (amb, r60))
      # measured: 80 % in the first 30 min; the model heats more slowly early (about 65 %), stated in the README
      self.assertGreater(r30 / r60, 0.6, (amb, r30 / r60))
      rises.append(r60)
    self.assertLess(abs(rises[0] - rises[1]), 2.0)   # independent of ambient, as measured

  def test_c2_no_heat_from_nowhere(self):
    p = yaml.safe_load((HERE / "params.yaml").read_text(encoding="utf-8"))
    c = p["cabin"]
    c["windshield"]["transmittance"] = c["windshield"]["absorptance"] = c["roof"]["absorptance"] = 0.0
    c["side_windows"]["transmittance"] = c["side_windows"]["absorptance"] = 0.0
    c["h_sky_rad"]["sky_below_air"] = 0.0
    df = cs.simulate(p, [("12:00", "13:00", "park", 180.0, 0.0, False)], "2027-06-21", 30.0, 30.0, start_temp=30.0)
    for n in ("air", "glass", "dash", "interior", "shell"):
      self.assertLess(abs(float(df[n].iloc[-1]) - 30.0), 1e-9, n)
    c["h_sky_rad"]["sky_below_air"] = 10.0                            # a clear night sky cools it, not below the sky
    night = cs.simulate(p, [("01:00", "02:00", "park", 180.0, 0.0, False)], "2027-06-21", 30.0, 30.0, start_temp=30.0)
    self.assertTrue(20.0 < float(night["air"].iloc[-1]) < 30.0)

  def test_c3_outside_curve(self):
    h = np.arange(0, 24, 0.25)
    t = cs.outside(h, 20.0, 30.0)
    self.assertAlmostEqual(float(h[np.argmin(t)]), 6.0)
    self.assertAlmostEqual(float(h[np.argmax(t)]), 15.0)
    self.assertAlmostEqual(float(t.min()), 20.0)
    self.assertAlmostEqual(float(t.max()), 30.0)

  def test_c4_geometry_from_the_mesh(self):
    g = json.loads((HERE.parent / "figures" / "corolla-e210-geometry.json").read_text(encoding="utf-8"))["glass"]
    c = P["cabin"]
    self.assertAlmostEqual(c["windshield"]["area"], g["windshield"]["area_m2"], places=3)
    self.assertAlmostEqual(c["windshield"]["tilt_deg"], g["windshield"]["tilt_from_horizontal_deg"], places=1)
    self.assertAlmostEqual(c["rear_window"]["area"], g["rear_window"]["area_m2"], places=3)
    self.assertAlmostEqual(c["rear_window"]["tilt_deg"], g["rear_window"]["tilt_from_horizontal_deg"], places=1)
    self.assertAlmostEqual(c["side_windows"]["area_each"],
                           g["side_front_each"]["area_m2"] + g["side_rear_each"]["area_m2"], places=3)


class Fog(unittest.TestCase):
  def test_f1_saturation_table(self):
    # ASHRAE Handbook Fundamentals, ch. 1, Table 3 (kPa): over water at 0..40 °C, over ice at -10 and -20 °C
    for t, e in ((0, 0.6112), (10, 1.2282), (20, 2.3392), (30, 4.2467), (40, 7.3844)):
      self.assertLess(abs(float(wf.e_water(t)) / e - 1), 0.005, t)
    for t, e in ((-10, 0.25987), (-20, 0.10326)):
      self.assertLess(abs(float(wf.e_ice(t)) / e - 1), 0.005, t)
    self.assertAlmostEqual(float(wf.dew_point(wf.e_water(12.3))), 12.3, places=9)

  def test_f2_frost_above_freezing(self):
    geo, fp = wf.setup(P), P["fog"]
    g = fp["glass"]
    h_in = P["cabin"]["h_inside"]["parked"] + fp["h_inside_rad"]["value"]
    def glass(okta):
      ts = wf.sky_temp(2.0, 0.0, okta, fp["sky"]["cloud_factor"]["value"])
      return float(wf.faces(2.0, 2.0, ts, geo["f_sky"], wf.h_parked(0.5), h_in, wf.glass_r(g), g["emissivity"])[0])
    clear, overcast = glass(0.0), glass(8.0)
    self.assertTrue(wf.e_water(0.0) > wf.e_sat(clear) and clear < 0.0, clear)
    self.assertTrue(wf.e_water(0.0) < wf.e_sat(overcast), overcast)
    to, ti = wf.faces(5.0, 5.0, 5.0, geo["f_sky"], 10.0, 8.0, wf.glass_r(g), g["emissivity"])
    self.assertAlmostEqual(float(to), 5.0, places=9)
    self.assertAlmostEqual(float(ti), 5.0, places=9)

  def test_f3_recirculation_closed_form(self):
    fp, c = P["fog"], P["cabin"]
    pr, vol, n = fp["pressure_kpa"]["value"], c["air_volume_m3"]["value"], 2
    t_out, td_out, ti = 3.0, -2.0, 9.0
    minutes = float(wf.recirc_minutes(P, t_out, td_out, ti, n))
    m_inf = 1.2 * vol * fp["recirc_ach"]["value"] / 3600
    g = n * fp["breath_g_h"]["value"] / 3.6e6
    w_out = float(wf.ratio(wf.e_water(td_out), pr))
    w, t, dt = w_out, 0.0, 0.5
    while wf.vapour(w, pr) < wf.e_sat(ti):
      w += dt * (g + m_inf * (w_out - w)) / (1.2 * vol)
      t += dt
    self.assertLess(abs(t / 60 - minutes), 0.05, (t / 60, minutes))

  def test_f4_defrost_energy(self):
    geo = wf.setup(P)
    res = wf.defrost(P, climate.load(), geo, 0.1)
    self.assertLess(abs(res["balance"]), 1e-3, res["balance"])
    self.assertTrue(np.all(np.diff(res["clear_min"]) >= 0))     # clears from the vents up

  def test_f5_climate_table(self):
    c = climate.load()
    self.assertEqual(len(c), 288)
    self.assertEqual(sorted(set(c["month"])), list(range(1, 13)))
    self.assertLess(float(np.abs(c[list(climate.SKY)].sum(axis=1) - 100).max()), 0.5)
    m = c.groupby("month")[["t", "tavg_monthly"]].mean()
    self.assertLess(float(np.abs(m["t"] - m["tavg_monthly"]).max()), 1.0)

  def test_f6_convection_agrees(self):
    v = 110 / 3.6
    a, b = wf.h_driving(v, wf.setup(P)["slant"]), wf.h_parked(v)
    self.assertLess(abs(a - b) / b, 0.1, (a, b))


class Braking(unittest.TestCase):
  def test_b1_table(self):
    t = P["braking"]["friction_table"]
    for tyre in wb.TYRES:
      for i, v in enumerate(t["speeds_kph"]):
        for j, w in enumerate(t["water_mm"]):
          self.assertAlmostEqual(wb.mu(P, tyre, v, w), t[tyre][i][j], places=12)
      m = wb.mu(P, tyre, 110.0, 0.6)
      corners = [t[tyre][i][j] for i in (1, 2) for j in (1, 2)]
      self.assertTrue(min(corners) - 1e-12 <= m <= max(corners) + 1e-12)
    self.assertEqual(t["new"][0], [0.85, 0.65, 0.55, 0.50])          # the 50 km/h row as printed

  def test_b2_item_bound(self):
    self.assertEqual(wb.accel_min(), -3.5)
    self.assertIn("acceleration −3.5…+2.0 m/s²", WPC02.read_text(encoding="utf-8"))
    self.assertAlmostEqual(wb.need(3.5), 3.5 / 9.81, places=12)
    self.assertGreater(wb.need(3.5, 4.0), wb.need(3.5))

  def test_b3_handbook_meets_nasa(self):
    v_hp = hp.nasa_mph(P["water"]["tyre_pressure_psi"]["value"]) * hp.MPH
    for v in (v_hp + 5, 110.0, 130.0):
      self.assertLessEqual(wb.mu(P, "new", v, 2.0), 0.05)

  def test_b4_stopping(self):
    v = 110 / 3.6
    self.assertAlmostEqual(wb.stop_m(110.0, 3.5, 0.0), v * v / 7.0, places=9)
    self.assertAlmostEqual(wb.stop_m(110.0, 3.5, 0.0), 133.4, places=1)
    self.assertAlmostEqual(wb.stop_m(110.0, 3.5, 0.5) - wb.stop_m(110.0, 3.5, 0.0), v * 0.5, places=9)


class Crown(unittest.TestCase):
  def test_r1_code_constants(self):
    c = rc.code()
    self.assertTrue(c["compensates"] and c["calibration_roll_zero"])
    self.assertEqual((c["dt"], c["q_roll_deg"], c["obs_std_factor"], c["invalid_std_deg"], c["roll_std_max_deg"], c["g"]),
                     (0.05, 1.0, 2.0, 10.0, 1.5, 9.81))

  def test_r2_riccati(self):
    q, r, dt = np.radians(1.0) ** 2, np.radians(0.6) ** 2, 0.05
    K = rc.kalman_gain(q, r, dt)
    qd = q * dt
    pm = (qd + np.sqrt(qd * qd + 4 * qd * r)) / 2
    self.assertAlmostEqual(K, pm / (pm + r), places=9)
    self.assertGreater(rc.tau(rc.kalman_gain(q, 4 * r, dt), dt), rc.tau(K, dt))

  def test_r3_limits(self):
    for pct in (1.5, 2.0, 6.0):
      self.assertLess(abs(9.81 * np.sin(np.arctan(pct / 100)) / (9.81 * pct / 100) - 1), 0.01)
    p = yaml.safe_load((HERE / "params.yaml").read_text(encoding="utf-8"))
    p["crown"]["mount_roll_deg"]["low"] = 0.0
    r = rc.run(p)
    self.assertEqual(r["residual"]["mount"]["low"], 0.0)
    self.assertLess(rc.crown_flip(rc.code(), p, 0.001)["peak"], 0.005)


class Crosswind(unittest.TestCase):
  def test_x1_mesh_against_published(self):
    r = cw.run(P)
    self.assertLess(abs(r["wheelbase_mesh_m"] - r["wheelbase_opendbc_m"]) / r["wheelbase_opendbc_m"], 0.02)
    self.assertTrue(2.0 < r["coefficients_per_deg"]["frontal_area_m2"] < 2.4)

  def test_x2_push_algebra(self):
    c = cw.corolla()
    v = 30.0
    self.assertLess(cw.push(1000.0, 0.0, v, c), 1e-9)
    m, L, a, b, cs_ = c["m"], c["L"], c["a"], c["b"], c["C_S"]
    Cf, Cr = cs_ * m * cw.G * b / L, cs_ * m * cw.G * a / L
    N = 500.0
    self.assertAlmostEqual(cw.push(0.0, N, v, c), v ** 2 * N * (1 / Cf + 1 / Cr) / L ** 2, places=9)

  def test_x3_monotone_and_ordered(self):
    r = cw.run(P)
    for d in r["speeds"].values():
      self.assertEqual(d["upper"][0], 0.0)
      self.assertTrue(all(np.diff(d["upper"]) > 0) and all(np.diff(d["lower"]) > 0))
      self.assertTrue(all(lo <= hi for lo, hi in zip(d["lower"], d["upper"], strict=True)))


if __name__ == "__main__":
  unittest.main(verbosity=2)
