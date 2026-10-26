"""Figures of the weather physics: sun in the road camera and hydroplaning. WebP (PNG and GIF go to LFS here).

Every figure is stamped synthetic (DSR-12), design aid, no evidence credit.
"""

from __future__ import annotations

import io
import json
import math
from pathlib import Path

import matplotlib
import matplotlib.ticker
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Circle, Patch, Polygon, Rectangle  # noqa: E402
from PIL import Image  # noqa: E402

INK, INK2, MUTED, CRIT, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#d03b3b", "#e6e5e0", "#fcfcfb"
BLUE = ["#86b6ef", "#2a78d6", "#104281"]
SUN = LinearSegmentedColormap.from_list("sun", ["#fdeee5", "#f6b48f", "#eb6834", "#b8401a"])
STAMP = "SYNTHETIC (DSR-12) · design aid, no evidence credit"
MONTHS = "J F M A M J J A S O N D".split()
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13, "axes.edgecolor": MUTED, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "figure.facecolor": SURF, "axes.facecolor": SURF})


def _stamp(fig, text=STAMP):
  fig.text(0.5, 0.012, text, ha="center", va="bottom", fontsize=10.5, color=CRIT, weight="bold",
           bbox=dict(boxstyle="round,pad=0.35", fc="#fdecec", ec=CRIT, lw=1))


def _png(fig):
  buf = io.BytesIO()
  fig.savefig(buf, format="png", facecolor=SURF)
  plt.close(fig)
  return Image.open(buf).convert("RGB")


def _save(fig, path):
  _png(fig).save(path, "WEBP", quality=90, method=6)


def _anim(frames, durs, path):
  frames[0].save(path, "WEBP", save_all=True, append_images=frames[1:], duration=durs, loop=0, quality=70, method=6)


def _month_ticks(ax, year):
  starts = [pd.Timestamp(year, m, 1).dayofyear - 1 for m in range(1, 13)]
  ax.set_xticks([s + 14 for s in starts]); ax.set_xticklabels(MONTHS)
  for s in starts[1:]:
    ax.axvline(s, color=GRID, lw=0.8)


# ------------------------------------------------------------------------------------------------ sun

def _calendar(r, path):
  fig = plt.figure(figsize=(9, 11.5), dpi=100)
  fig.text(0.05, 0.965, "When the sun is in the road camera's frame", fontsize=19, weight="bold", color=INK)
  fig.text(0.05, 0.94, f"I-85, Atlanta – Charlotte · {r['year']} · camera {r['camera']['hfov_deg']:.0f}° × "
           f"{r['camera']['vfov_deg']:.0f}° (camera.py) · clock time, Eastern", fontsize=12.5, color=INK2)
  for k, (name, d) in enumerate(r["corridor"].items()):
    g = np.array(d["calendar"], dtype=float).T
    ax = fig.add_axes([0.11, 0.55 - k * 0.42, 0.84, 0.34])
    g[g == 0] = np.nan
    ax.imshow(g, aspect="auto", origin="lower", cmap=SUN, vmin=0, vmax=20, extent=(0, g.shape[1], 0, 24),
              interpolation="nearest")
    ax.set_ylim(5, 21); ax.set_yticks(range(6, 21, 2)); ax.set_yticklabels([f"{h}:00" for h in range(6, 21, 2)])
    _month_ticks(ax, r["year"])
    ax.grid(axis="y", color=GRID)
    ax.set_title(f"{name.capitalize()} ({d['heading']:.0f}°): {d['hours_in_view']:.0f} h a year, longest "
                 f"{d['longest_daily_min']:.0f} min a day", loc="left", fontsize=14, color=INK)
  fig.text(0.05, 0.055, "Orange: the sun is inside the frame (darker = more of the 20 min slot). No terrain, trees or\n"
           "clouds, so an upper bound. Use it to schedule the low-sun drives of KS-12.", fontsize=11.5, color=INK2)
  _stamp(fig)
  _save(fig, path)


def _headings(r, path):
  hd = np.radians(np.array(r["headings"]) + 2.5)
  iv, fl = np.array(r["by_heading_h"]["in_view"]), np.array(r["by_heading_h"]["flare"])
  fig = plt.figure(figsize=(9, 10), dpi=100)
  fig.text(0.05, 0.955, "Hours a year with the sun in the frame, by heading", fontsize=18, weight="bold", color=INK)
  fig.text(0.05, 0.925, "Every direction of travel at the corridor; dark: in the frame, light: within 10° of it",
           fontsize=12.5, color=INK2)
  ax = fig.add_axes([0.1, 0.12, 0.8, 0.75], projection="polar")
  ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
  ax.bar(hd, fl, width=np.radians(4.6), color="#cde2fb", edgecolor="none")
  ax.bar(hd, iv, width=np.radians(4.6), color="#2a78d6", edgecolor="none")
  for name, d in r["corridor"].items():
    a = np.radians(d["heading"])
    ax.annotate(f"I-85 {name}\n{d['hours_in_view']:.0f} h", (a, d["hours_in_view"]), (a, max(fl) * 1.05),
                ha="center", fontsize=12, weight="bold", color=INK, arrowprops=dict(arrowstyle="-", color=INK))
  ax.set_xticks(np.radians(range(0, 360, 45))); ax.set_xticklabels(["N", "NE", "E", "SE", "S", "SW", "W", "NW"])
  ax.tick_params(axis="y", labelsize=10); ax.grid(color=GRID)
  _stamp(fig)
  _save(fig, path)


def _sun_anim(p, r, path):
  import pvlib
  s = p["sun"]
  d = r["corridor"]["southbound"]
  days = np.array(d["calendar"]).sum(axis=1)
  doy = int(np.argmax(days))
  day = pd.Timestamp(r["year"], 1, 1, tz=s["site"]["tz"]) + pd.Timedelta(days=doy)
  t = pd.date_range(day + pd.Timedelta(hours=15), day + pd.Timedelta(hours=19), freq="4min")
  sp = pvlib.solarposition.spa_python(t, s["site"]["lat"], s["site"]["lon"])
  dx = ((sp["azimuth"].to_numpy() - d["heading"] + 180) % 360) - 180
  el = sp["apparent_elevation"].to_numpy()
  keep = el > -3
  t, dx, el = t[keep], dx[keep], el[keep]
  hh, vh = r["camera"]["hfov_deg"] / 2, r["camera"]["vfov_deg"] / 2
  frames = []
  for i in range(len(t)):
    fig = plt.figure(figsize=(7.2, 9), dpi=80)
    fig.text(0.05, 0.955, "Driving southwest into the sunset", fontsize=19, weight="bold", color=INK)
    fig.text(0.05, 0.925, f"I-85 southbound ({d['heading']:.0f}°) · {day:%d %B} · road camera frame", fontsize=12.5,
             color=INK2)
    fig.text(0.95, 0.955, f"{t[i]:%H:%M}", ha="right", fontsize=18, color=INK, family="DejaVu Sans Mono")
    ax = fig.add_axes([0.06, 0.2, 0.88, 0.68])
    ax.set_xlim(-45, 45); ax.set_ylim(-14, 34); ax.set_aspect("equal"); ax.axis("off")
    sky = np.linspace(0, 1, 64)[:, None]
    ax.imshow(sky, extent=(-45, 45, 0, 34), origin="lower", aspect="auto",
              cmap=LinearSegmentedColormap.from_list("sky", ["#fde6c8", "#bcd6f2"]), zorder=0)
    ax.set_aspect("equal")
    ax.add_patch(Rectangle((-45, -14), 90, 14, color="#cfcdc4", zorder=1))
    ax.add_patch(Polygon([(-30, -14), (30, -14), (0.6, 0), (-0.6, 0)], color="#9a988f", zorder=2))
    for y0, y1 in ((-14, -10), (-7, -5), (-3.2, -2.2), (-1.2, -0.8)):
      w0, w1 = 0.6 * (y0 + 14) / 14, 0.6 * (y1 + 14) / 14
      ax.add_patch(Polygon([(-1 + w0, y0), (1 - w0, y0), (1 - w1, y1), (-1 + w1, y1)], color="white", zorder=3))
    ax.plot(dx[: i + 1], el[: i + 1], color="#eb6834", lw=1.5, ls=(0, (2, 2)), zorder=4)
    inside = abs(dx[i]) <= hh and 0 < el[i] <= vh
    ax.add_patch(Circle((dx[i], el[i]), 1.2, color="#f2a900" if el[i] > 0 else "#c9a76a", zorder=5))
    ax.add_patch(Rectangle((-hh, -vh), 2 * hh, 2 * vh, fill=False, ec=CRIT if inside else INK, lw=2.5, zorder=6))
    ax.text(-hh, vh + 0.8, f"road camera {2 * hh:.0f}° × {2 * vh:.0f}°", fontsize=11, color=INK, zorder=6)
    if inside:
      ax.text(0, 30, "Sun in the frame", ha="center", fontsize=15, weight="bold", color="white", zorder=7,
              bbox=dict(boxstyle="round,pad=0.4", fc=CRIT, ec=CRIT))
    fig.text(0.05, 0.1, f"Sun {dx[i]:+.0f}° from straight ahead, {el[i]:.0f}° above the horizon.", fontsize=12.5,
             color=INK2)
    _stamp(fig, "SYNTHETIC (DSR-12) · design aid, no credit · no terrain or trees")
    frames.append(_png(fig))
  _anim(frames, [160] * (len(frames) - 1) + [2500], path)


def sun_figures(p, r, out: Path):
  out.mkdir(exist_ok=True)
  _calendar(r, out / "fig-wx-1-sun-calendar.webp")
  _headings(r, out / "fig-wx-2-sun-headings.webp")
  _sun_anim(p, r, out / "fig-wx-3-sun-anim.webp")
  _report(out, "fig-wx-1", "fig-wx-2", "fig-wx-3")


# ------------------------------------------------------------------------------------------------ water

def _speed(r, path):
  odd, light, mod = r["odd_speed_kph"], r["classes_mm_h"]["light"], r["classes_mm_h"]["moderate"]
  rain = np.array(r["rain_mm_h"], float)
  fig, ax = plt.subplots(figsize=(9, 10), dpi=100)
  fig.subplots_adjust(left=0.12, right=0.95, top=0.84, bottom=0.2)
  fig.text(0.05, 0.95, "Hydroplaning speed in rain, against the ODD bound", fontsize=18, weight="bold", color=INK)
  fig.text(0.05, 0.92, "Corolla on a crowned Interstate, 0 % grade · Gallaway / PAVDRN film model", fontsize=12.5,
           color=INK2)
  ax.axvspan(0.8, light, color="#eef5e9"); ax.axvspan(light, mod, color="#fbf3dc"); ax.axvspan(mod, 120, color="#fdecec")
  for x, lab in ((1.4, "light\n(in ODD)"), (4.3, "moderate"), (30, "heavy")):
    ax.text(x, 182, lab, ha="center", va="top", fontsize=11.5, color=INK2)
  n = r["nasa_kph"]
  ax.axhspan(n["low"], n["high"], color="#e9e1f5")
  ax.text(1.0, n["value"], f"NASA, water deeper than\nthe tread: {n['value']:.0f} km/h", ha="left", va="center",
          fontsize=11.5, color="#5b3d99", weight="bold")
  ax.axhline(odd, color=CRIT, lw=2)
  ax.text(1.0, odd + 2, f"ODD bound {odd:.0f} km/h", color=CRIT, fontsize=12, weight="bold")
  rows = [k for k in r["rows"] if k.endswith(" 0 % grade")]
  for c, k in zip(BLUE, rows, strict=False):
    v = np.array([np.nan if x is None else x for x in r["rows"][k]["speed_kph"]], float)
    ax.plot(rain, v, color=c, lw=2.4, marker="o", ms=5)
    last = np.where(np.isfinite(v))[0]
    ax.text(rain[-1] * 1.04, v[-1], k.split(",")[0], fontsize=11.5, va="center", color=INK)
    if len(last):
      ax.plot([rain[last[0]]] * 2, [v[last[0]], 180], color=c, lw=1, ls=":")
  ax.text(3.2, 150, "no water film above\nthe texture: no\nhydroplaning\nfrom rain", fontsize=11, color=INK2, ha="center")
  ax.set_xscale("log"); ax.set_xlim(0.8, 160); ax.set_ylim(60, 185)
  ax.set_xticks([1, 2.5, 7.6, 25, 50, 100]); ax.set_xticklabels(["1", "2.5", "7.6", "25", "50", "100"])
  ax.set_xlabel("rain intensity, mm/h"); ax.set_ylabel("hydroplaning speed, km/h")
  ax.grid(axis="y", color=GRID); ax.spines[["top", "right"]].set_visible(False)
  fig.text(0.05, 0.08, "Lanes = how many lanes the water crosses to the edge. Empirical models from trough and\n"
           "track tests (FHWA 1979, NCHRP 1998, NASA 1963), not tests of this car's tyres.", fontsize=11.5, color=INK2)
  _stamp(fig)
  _save(fig, path)


def _tyre_anim(r, path):
  odd, vp = r["odd_speed_kph"], r["nasa_kph"]["value"]
  speeds = list(np.linspace(50, 130, 33))
  frames = []
  for v in speeds:
    contact = max(0.0, 1 - (v / vp) ** 2)
    fig = plt.figure(figsize=(7.2, 9), dpi=80)
    fig.text(0.05, 0.955, "Tyre on standing water", fontsize=19, weight="bold", color=INK)
    fig.text(0.05, 0.925, f"Corolla tyre at {r['nasa_pressure_psi']['value']:.0f} psi · NASA TN D-2056", fontsize=12.5,
             color=INK2)
    fig.text(0.95, 0.955, f"{v:3.0f} km/h", ha="right", fontsize=18, color=INK, family="DejaVu Sans Mono")
    ax = fig.add_axes([0.05, 0.42, 0.9, 0.48]); ax.set_xlim(-6, 6); ax.set_ylim(-1.2, 6.5); ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((-6, -1.2), 12, 1.2, color="#9a988f"))
    foot = 2.4
    dry_end = -foot / 2 + foot * contact   # water enters the footprint from its leading edge (+x)
    for x0, x1 in ((-6, -foot / 2), (dry_end, 6)):
      ax.add_patch(Rectangle((x0, 0), x1 - x0, 0.35, color="#7fb2e6"))
    lift = 0.35 * (1 - contact)
    ax.add_patch(Circle((0, 3.0 + lift), 3.0, color="#2b2a28"))
    ax.add_patch(Circle((0, 3.0 + lift), 1.6, color="#8a8984"))
    if contact > 0:
      ax.add_patch(Rectangle((-foot / 2, -0.06), foot * contact, 0.12, color="#0ca30c"))
    ax.annotate("", (5.5, 0.2), (3.2, 0.2), arrowprops=dict(arrowstyle="<-", color=INK2, lw=2))
    ax.text(4.3, 0.55, "water", fontsize=11, color="#1c5cab", ha="center")
    a2 = fig.add_axes([0.12, 0.2, 0.8, 0.16])
    a2.barh([0], [contact * 100], color="#0ca30c" if contact > 0.05 else CRIT, height=0.6)
    a2.set_xlim(0, 100); a2.set_yticks([]); a2.set_xlabel("tyre footprint still on the road, % (schematic)")
    a2.spines[["top", "right", "left"]].set_visible(False)
    msg = "Hydroplaning: no grip" if v >= vp else (f"Above the ODD bound ({odd:.0f} km/h)" if v > odd else "")
    if msg:
      fig.text(0.5, 0.39, msg, ha="center", fontsize=14, weight="bold", color="white",
               bbox=dict(boxstyle="round,pad=0.4", fc=CRIT, ec=CRIT))
    fig.text(0.05, 0.085, f"Lift grows with speed squared; full hydroplaning at {vp:.0f} km/h. The footprint bar is a\n"
             "schematic of that law, not a measurement.", fontsize=11, color=INK2)
    _stamp(fig, "SYNTHETIC (DSR-12) · design aid, no credit · schematic")
    frames.append(_png(fig))
  _anim(frames, [180] * (len(frames) - 1) + [2500], path)


def water_figures(p, r, out: Path):
  out.mkdir(exist_ok=True)
  _speed(r, out / "fig-wx-4-hydro-speed.webp")
  _tyre_anim(r, out / "fig-wx-5-hydro-anim.webp")
  _report(out, "fig-wx-4", "fig-wx-5")


def _report(out, *prefixes):
  for f in sorted(out.glob("*.webp")):
    if f.name.startswith(prefixes):
      print(f"wrote {f.name} ({f.stat().st_size // 1024} KB)")


# ------------------------------------------------------------------------------------------------ cabin

NODE_STYLE = {"outside": ("outside air", MUTED, 1.6, (0, (3, 2))), "air": ("cabin air", "#86b6ef", 2.0, "-"),
              "glass": ("windshield", "#2a78d6", 2.0, "-"), "dash": ("dashboard", "#b8401a", 2.0, "-"),
              "mount": ("mount air", "#104281", 3.2, "-")}


def _cabin_series(r, path):
  b = r["heat_model_bound"]
  fig = plt.figure(figsize=(9, 12), dpi=100)
  fig.text(0.05, 0.965, "Cabin heat soak: parked in the sun, then driving", fontsize=19, weight="bold", color=INK)
  fig.text(0.05, 0.94, "Corolla, I-85 corridor, clear 15 July, 35 °C afternoon · parked facing south 12–14 h",
           fontsize=12.5, color=INK2)
  for k, (name, title) in enumerate((("hot_july", "Then driving with the AC on"),
                                     ("hot_july_ac_off", "Then driving with the AC off (fan, fresh air)"))):
    d = r["scenarios"][name]
    t = np.array(d["t_min"]) / 60 + 12
    ax = fig.add_axes([0.1, 0.55 - k * 0.43, 0.68, 0.34])
    ax.axvspan(12, 12 + d["drive_starts_min"] / 60, color="#fbf3dc")
    ax.text(12.05, 113, "parked in the sun", fontsize=11, color=INK2)
    ax.text(14.05, 113, "driving 100 km/h", fontsize=11, color=INK2)
    ax.axhspan(b["worst_edge"], b["nominal"], color="#fdecec")
    ax.axhline(b["worst_edge"], color=CRIT, lw=1.5, ls=(0, (4, 3)))
    ax.text(15.02, b["worst_edge"] - 6, f"device model's\nbound {b['worst_edge']:.0f}–{b['nominal']:.0f} °C",
            color=CRIT, fontsize=10.5, va="center")
    for n, (lab, col, lw, ls) in NODE_STYLE.items():
      ax.plot(t, d[n], color=col, lw=lw, ls=ls, label=lab)
    if k == 0:
      ax.legend(loc="upper left", bbox_to_anchor=(1.0, 0.98), frameon=False, fontsize=10.5)
    ax.set_xlim(12, 15); ax.set_ylim(15, 118); ax.set_xticks([12, 13, 14, 15])
    ax.set_xticklabels(["12:00", "13:00", "14:00", "15:00"]); ax.set_ylabel("°C")
    ax.grid(axis="y", color=GRID); ax.spines[["top", "right"]].set_visible(False)
    ax.set_title(title, loc="left", fontsize=14, color=INK)
  fig.text(0.05, 0.055, "A lumped model (air, windshield, dashboard, interior, shell) with estimated inputs; checked\n"
           "against measured parked cars (McLaren et al. 2005). The logger at the mount (DQ-412) checks it.",
           fontsize=11.5, color=INK2)
  _stamp(fig)
  _save(fig, path)


GEOMETRY = Path(__file__).resolve().parents[1] / "figures" / "corolla-e210-geometry.json"


def _cabin_anim(r, path):
  """The hot day on the Corolla's side elevation, measured on the purchased mesh (corolla-e210-geometry.json)."""
  import json
  side = json.loads(GEOMETRY.read_text(encoding="utf-8"))["side_elevation"]
  d = r["scenarios"]["hot_july"]
  b = r["heat_model_bound"]
  t = np.array(d["t_min"])
  heat = LinearSegmentedColormap.from_list("heat", ["#cde2fb", "#fdeee5", "#f6b48f", "#eb6834", "#b8401a", "#6b220b"])
  norm = plt.Normalize(20, 95)
  ws = np.array(side["windshield"][0])
  top = ws[np.argmax(ws[:, 1])]                     # the windshield's top edge, where the device hangs
  device = (top[0] + 0.07, top[1] - 0.07)
  dash = [(top[0] + 0.25, 0.86), (top[0] + 0.62, 0.9), (top[0] + 0.62, 0.95), (top[0] + 0.25, 0.97)]
  frames = []
  for i in range(0, len(t), 2):
    driving = t[i] >= d["drive_starts_min"]
    fig = plt.figure(figsize=(7.2, 9), dpi=80)
    fig.text(0.05, 0.955, "A hot day in the cabin", fontsize=19, weight="bold", color=INK)
    fig.text(0.05, 0.925, "Corolla E210 (outline from the 3D model) · clear 15 July · AC on when driving", fontsize=12,
             color=INK2)
    clock = 12 + t[i] / 60
    fig.text(0.95, 0.955, f"{int(clock):02d}:{int(round((clock % 1) * 60)) % 60:02d}", ha="right", fontsize=18,
             color=INK, family="DejaVu Sans Mono")
    ax = fig.add_axes([0.02, 0.5, 0.96, 0.38]); ax.set_xlim(-2.45, 2.45); ax.set_ylim(-0.1, 2.0)
    ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Polygon(side["body"][0], color="#c9c7bf", zorder=1))
    for k in ("side_front", "side_rear"):                     # the cabin, seen through the side glass
      ax.add_patch(Polygon(side[k][0], color=heat(norm(d["air"][i])), ec="#52514e", lw=0.6, zorder=2))
    for k in ("windshield", "rear_window"):
      ax.add_patch(Polygon(side[k][0], color=heat(norm(d["glass"][i])), ec="#52514e", lw=0.6, zorder=3))
    ax.add_patch(Polygon(dash, color=heat(norm(d["dash"][i])), zorder=3))
    for wpoly in side["wheels"]:
      ax.add_patch(Polygon(wpoly, color="#2b2a28", zorder=4))
    ax.add_patch(Circle(device, 0.05, color="white", ec=INK, lw=1.5, zorder=6))
    ax.annotate(f"mount air {d['mount'][i]:.0f} °C", device, (device[0] - 0.4, 1.75), fontsize=13, weight="bold",
                color=INK, ha="center", arrowprops=dict(arrowstyle="-", color=INK, lw=1))
    ax.text(-0.35, 1.05, f"cabin {d['air'][i]:.0f} °C", fontsize=12, color=INK, ha="center", zorder=7)
    ax.text(top[0] + 0.62, 0.72, f"dash {d['dash'][i]:.0f} °C", fontsize=11, color=INK, ha="right", zorder=7)
    if not driving:
      ax.add_patch(Circle((2.05, 1.75), 0.14, color="#f2a900"))
      ax.text(-2.35, 1.75, "Parked in the sun", fontsize=13, weight="bold", color="#b8401a")
    else:
      ax.text(-2.35, 1.75, "Driving, AC on", fontsize=13, weight="bold", color="#1c5cab")
      for y in (0.45, 0.75, 1.05):
        ax.plot([-2.45, -2.45 + 0.15 + 0.1 * (i % 3)], [y, y], color=MUTED, lw=1.5)
    a2 = fig.add_axes([0.13, 0.13, 0.82, 0.3])
    a2.axhspan(b["worst_edge"], b["nominal"], color="#fdecec")
    a2.axhline(b["worst_edge"], color=CRIT, lw=1.5, ls=(0, (4, 3)))
    a2.text(178, b["worst_edge"] + 1.5, f"device model's bound {b['worst_edge']:.0f} °C", color=CRIT, ha="right",
            fontsize=10.5)
    a2.plot(t, d["mount"], color=GRID, lw=2)
    a2.plot(t[: i + 1], d["mount"][: i + 1], color="#104281", lw=2.6)
    a2.plot(t[i], d["mount"][i], "o", ms=9, mfc="white", mec="#104281", mew=2)
    a2.axvline(d["drive_starts_min"], color=MUTED, lw=1)
    a2.set_xlim(0, 180); a2.set_ylim(20, 70); a2.set_xticks([0, 60, 120, 180])
    a2.set_xticklabels(["12:00", "13:00", "14:00", "15:00"]); a2.set_ylabel("mount air, °C")
    a2.grid(axis="y", color=GRID); a2.spines[["top", "right"]].set_visible(False)
    _stamp(fig, "SYNTHETIC (DSR-12) · design aid, no credit · estimated inputs")
    frames.append(_png(fig))
  _anim(frames, [140] * (len(frames) - 1) + [2500], path)


def cabin_figures(p, r, out: Path):
  out.mkdir(exist_ok=True)
  _cabin_series(r, out / "fig-wx-6-cabin.webp")
  _cabin_anim(r, out / "fig-wx-7-cabin-anim.webp")
  _report(out, "fig-wx-6", "fig-wx-7")


# ------------------------------------------------------------------------------------------------ crosswind

SILHOUETTE = Path(__file__).resolve().parents[1] / "figures" / "corolla-e210-silhouette.json"


def _top_outline():
  """Top view from the committed silhouette: x forward (the file's car faces -y), y to the left."""
  import json
  t = json.loads(SILHOUETTE.read_text(encoding="utf-8"))["top_outline_body"]
  pts = [(-a, s) for a, s in t["left"]] + [(-a, s) for a, s in reversed(t["right"])]
  return np.array(pts)


def _crosswind_car(r, path):
  import json
  geom = json.loads(GEOMETRY.read_text(encoding="utf-8"))
  side = geom["side_elevation"]
  d = r["distribution_110_ks02"]
  x, dy = np.array(d["x"]), np.array(d["dY"])
  edges = np.arange(-2.4, 2.45, 0.1)                       # 10 cm bins for display: mean force per metre in each
  idx = np.digitize(x, edges)
  xb = np.array([x[idx == i].mean() for i in range(1, len(edges)) if (idx == i).any()])
  yb = np.array([dy[idx == i].mean() for i in range(1, len(edges)) if (idx == i).any()])
  fig = plt.figure(figsize=(9, 11), dpi=100)
  fig.text(0.05, 0.965, "Where a crosswind pushes the Corolla", fontsize=19, weight="bold", color=INK)
  fig.text(0.05, 0.94, "110 km/h, 30 km/h wind square to the road (KS-02) · outline measured on the 3D model",
           fontsize=12.5, color=INK2)
  ax = fig.add_axes([0.06, 0.62, 0.9, 0.27]); ax.set_xlim(-2.5, 2.5); ax.set_ylim(-0.05, 1.65); ax.set_aspect("equal")
  ax.axis("off")
  ax.add_patch(Polygon(side["body"][0], color="#d9d7d1", zorder=1))
  for k in ("windshield", "rear_window", "side_front", "side_rear"):
    ax.add_patch(Polygon(side[k][0], color="#bcd6f2", zorder=2))
  for wpoly in side["wheels"]:
    ax.add_patch(Polygon(wpoly, color="#2b2a28", zorder=3))
  ax.text(2.4, 1.5, "front →", ha="right", fontsize=11, color=INK2)
  a2 = fig.add_axes([0.06, 0.47, 0.9, 0.13])               # same x span as the elevation above
  a2.bar(xb, yb, width=0.09, color="#eb6834")
  dy = yb
  a2.axvline(r["x_cg_m"], color=INK, lw=1.4); a2.axvline(r["cp_m"], color=CRIT, lw=1.6, ls=(0, (4, 3)))
  a2.text(r["x_cg_m"] - 0.05, dy.max() * 0.9, "centre of\ngravity", ha="right", fontsize=10.5, color=INK)
  a2.text(r["cp_m"] + 0.05, dy.max() * 0.9, "centre of\npressure", ha="left", fontsize=10.5, color=CRIT)
  a2.set_xlim(-2.5, 2.5); a2.set_yticks([])
  a2.text(-2.45, dy.max() * 0.95, "side force along the car\n(N per m)", fontsize=10.5, color=INK2, va="top")
  a2.spines[["top", "right"]].set_visible(False); a2.tick_params(labelbottom=False)
  a3 = fig.add_axes([0.06, 0.13, 0.9, 0.3]); a3.set_xlim(-2.5, 2.5); a3.set_ylim(-1.6, 1.4); a3.set_aspect("equal")
  a3.axis("off")
  top = _top_outline()
  a3.add_patch(Polygon(top, color="#d9d7d1", ec=INK2, lw=0.8))
  scale = 0.9 / max(dy.max(), 1e-9)
  for xi, f in zip(xb, yb, strict=True):
    if f > dy.max() * 0.04:
      a3.annotate("", (xi, 0.95), (xi, 0.95 + f * scale * 0.45), arrowprops=dict(arrowstyle="->", color="#eb6834", lw=1.4))
  a3.plot(r["x_cg_m"], 0, "o", ms=9, mfc="white", mec=INK, mew=1.5)
  a3.annotate("", (r["cp_m"] + 0.25, -0.15), (r["cp_m"] + 0.25, 0.55),
              arrowprops=dict(arrowstyle="-|>", color=CRIT, lw=2.4, mutation_scale=18))
  a3.text(r["cp_m"] + 0.35, 0.2, "resultant", fontsize=11, color=CRIT)
  a3.text(-2.45, 1.25, "wind ↓ from this side", fontsize=11.5, color="#1c5cab")
  a3.annotate("nose turned away from the wind", (2.3, -0.3), (0.6, -1.35), fontsize=11, color=INK2,
              arrowprops=dict(arrowstyle="->", color=INK2, connectionstyle="arc3,rad=-0.3"))
  c = r["coefficients_per_deg"]
  fig.text(0.05, 0.065, f"Slender-body force where the height grows, separated where it falls, plus crossflow drag. "
           f"Nominal C_Y {c['C_Y']:.3f}\nand C_N {c['C_N']:.3f} per degree (frontal area {c['frontal_area_m2']:.2f} m², "
           "wheelbase); the band takes half the slender-body force.", fontsize=11, color=INK2)
  _stamp(fig)
  _save(fig, path)


def _crosswind_push(r, path):
  fig, ax = plt.subplots(figsize=(9, 10), dpi=100)
  fig.subplots_adjust(left=0.12, right=0.95, top=0.84, bottom=0.2)
  fig.text(0.05, 0.95, "Crosswind push against the steering margin", fontsize=18, weight="bold", color=INK)
  fig.text(0.05, 0.92, "steering-equivalent lateral push to hold a straight line · Corolla, steady wind square to the road",
           fontsize=12, color=INK2)
  cols = {"80.0": "#86b6ef", "110.0": "#104281"}
  for k, d in r["speeds"].items():
    w = np.array(d["wind"]) * 3.6
    ax.fill_between(w, d["lower"], d["upper"], color=cols.get(k, INK2), alpha=0.35, lw=0)
    ax.plot(w, d["upper"], color=cols.get(k, INK2), lw=2.2)
    ax.text(w[-1] + 1, d["upper"][-1], f"{float(k):.0f} km/h", fontsize=12, color=INK, va="center")
  ax.axhline(r["odd_margin_m_s2"], color=CRIT, lw=1.6, ls=(0, (4, 3)))
  ax.text(2, r["odd_margin_m_s2"] + 0.12, f"ODD margin {r['odd_margin_m_s2']} m/s² (WP-C-02)", color=CRIT, fontsize=11.5)
  ax.axhline(r["controller_limit_m_s2"], color=CRIT, lw=2)
  ax.text(2, r["controller_limit_m_s2"] + 0.12, f"controller limit {r['controller_limit_m_s2']} m/s²", color=CRIT,
          fontsize=11.5, weight="bold")
  ax.axvline(30, color=INK2, lw=1.2)
  ax.text(31, 5.6, "KS-02:\n30 km/h wind", fontsize=11, color=INK2)
  ax.set_xlim(0, 100); ax.set_ylim(0, 6.5)
  ax.set_xlabel("crosswind, km/h"); ax.set_ylabel("push, m/s²")
  ax.grid(axis="y", color=GRID); ax.spines[["top", "right"]].set_visible(False)
  fig.text(0.05, 0.08, "Line: the upper estimate; band down to half the slender-body force. Textbook models on the\n"
           "mesh's outline, not a wind-tunnel test: a windy-day measurement sets the real value.", fontsize=11.5,
           color=INK2)
  _stamp(fig)
  _save(fig, path)


def _crosswind_anim(r, path):
  d = r["speeds"]["110.0"]
  a = float(np.mean(d["push_at_ks02"]))
  v = 110 / 3.6
  lane = 3.7
  half = 1.781 / 2
  t_line = math.sqrt(2 * (lane / 2 - half) / a)
  ts = np.linspace(0, min(t_line + 0.6, 4.0), 36)
  top = _top_outline()
  frames = []
  for t in ts:
    y = 0.5 * a * t * t
    fig = plt.figure(figsize=(7.2, 9), dpi=80)
    fig.text(0.05, 0.955, "Assist lost in a crosswind", fontsize=19, weight="bold", color=INK)
    fig.text(0.05, 0.925, f"110 km/h · 30 km/h wind from the left · push {a:.1f} m/s² (middle of the band)", fontsize=12,
             color=INK2)
    fig.text(0.95, 0.955, f"t = {t:3.1f} s", ha="right", fontsize=16, color=INK, family="DejaVu Sans Mono")
    ax = fig.add_axes([0.05, 0.18, 0.9, 0.7]); ax.set_xlim(-4, 4); ax.set_ylim(-4, 26); ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((-4, -4), 8, 30, color="#d6d4cc"))
    for xl, st in ((-lane / 2 - lane, "-"), (-lane / 2, (0, (6, 6))), (lane / 2, (0, (6, 6))), (lane / 2 + lane, "-")):
      ax.plot([xl, xl], [-4, 26], color="white", lw=2.5, ls=st)
    off = (v * t) % 12
    for k in range(-1, 4):
      for xw in (-3.6, -3.0):
        yy = 22 - ((k * 8 + off * 0.6) % 30)
        ax.annotate("", (xw + 1.4, yy), (xw, yy), arrowprops=dict(arrowstyle="->", color="#1c5cab", lw=1.5))
    car = np.c_[-top[:, 1] + y, top[:, 0] + 2]
    over = y + half > lane / 2
    ax.add_patch(Polygon(car, color="#c84b2f" if over else "#6d6b64", ec=INK, lw=1))
    ax.plot([0, 0], [-4, 26], color="#86b6ef", lw=1, ls=":")
    ax.text(0.15, 24.5, "lane centre", fontsize=10, color="#1c5cab")
    if over:
      ax.text(0, 13, "Over the lane line", ha="center", fontsize=15, weight="bold", color="white",
              bbox=dict(boxstyle="round,pad=0.4", fc=CRIT, ec=CRIT))
    fig.text(0.05, 0.1, f"Drift {y:.2f} m. A sketch: ½·a·t², no driver, no tyre self-alignment\n(an upper bound). The "
             "plant's straight-drift study gives the times with the driver.", fontsize=10.5, color=INK2)
    _stamp(fig, "SYNTHETIC (DSR-12) · design aid, no credit · textbook models")
    frames.append(_png(fig))
  _anim(frames, [140] * (len(frames) - 1) + [2500], path)


def crosswind_figures(p, r, out: Path):
  out.mkdir(exist_ok=True)
  _crosswind_car(r, out / "fig-wx-8-crosswind-car.webp")
  _crosswind_push(r, out / "fig-wx-9-crosswind-push.webp")
  _crosswind_anim(r, out / "fig-wx-10-crosswind-anim.webp")
  _report(out, "fig-wx-8", "fig-wx-9", "fig-wx-10")


# ------------------------------------------------------------------------------------------------ fog

FOG = LinearSegmentedColormap.from_list("fog", ["#fcfcfb", "#cde2fb", "#86b6ef", "#2a78d6", "#104281"])


def _fog_map(r, path):
  g = r["grid"]
  month, hour = np.array(g["month"]), np.array(g["hour"])
  fig = plt.figure(figsize=(9, 12.5), dpi=100)
  fig.text(0.05, 0.965, "Water on the windshield, by month and hour", fontsize=19, weight="bold", color=INK)
  fig.text(0.05, 0.94, "I-85 corridor, normal year (NOAA 1991–2020 hourly normals, GSP airport),\nlocal "
           "standard time. Shade: share of the normal hour.", fontsize=12, color=INK2, va="top")
  panels = (("parked", "Parked in the open: dew or frost outside", "wipers clear dew; frost needs the defroster"),
            ("drive_recirc", "Driving 110 km/h on recirculation, no AC, heater on",
             "fog inside, in front of the camera, within the hour"))
  for k, (key, title, sub) in enumerate(panels):
    z = np.zeros((24, 12))
    z[hour, month - 1] = g[key]
    ax = fig.add_axes([0.1, 0.53 - k * 0.38, 0.84, 0.26])
    im = ax.imshow(z, origin="lower", aspect="auto", cmap=FOG, vmin=0, vmax=1, extent=(0.5, 12.5, -0.5, 23.5))
    for x in np.arange(1.5, 12.5):
      ax.axvline(x, color=SURF, lw=2)
    ax.set_xticks(range(1, 13)); ax.set_xticklabels(MONTHS)
    ax.set_yticks([0, 6, 12, 18, 23]); ax.set_yticklabels(["0 h", "6 h", "12 h", "18 h", "23 h"])
    hy = r["hours_per_year"][key]
    ax.text(0, 1.11, title, transform=ax.transAxes, fontsize=14, color=INK, va="bottom", weight="bold")
    ax.text(0, 1.03, f"{hy:.0f} h a year · {sub}", transform=ax.transAxes, fontsize=11, color=INK2, va="bottom")
    for sp in ax.spines.values():
      sp.set_visible(False)
  cax = fig.add_axes([0.1, 0.875, 0.5, 0.015])
  cb = fig.colorbar(im, cax=cax, orientation="horizontal")
  cb.set_ticks([0, 0.5, 1]); cb.set_ticklabels(["never", "half", "always"])
  cb.outline.set_visible(False)
  fig.text(0.05, 0.055, "Each cell mixes NOAA's sky-cover classes and calm against windy hours at the hour's normal\n"
           "temperature and dew point. Fresh air or automatic climate control: no fog while driving.",
           fontsize=11.5, color=INK2)
  _stamp(fig)
  _save(fig, path)


def _fog_anim(p, r, path):
  """The humid January morning: the defroster clears the frost from the vents up; the camera looks through the top."""
  case = r["defrost"]["cases"]["heavy_frost"]
  clear = np.array([np.inf if c is None else c for c in case["clear_min"]])
  n = len(clear)
  zone = r["defrost"]["camera_zone"]
  slant, width = r["geometry"]["slant"], r["geometry"]["width"]
  t_end = float(np.nanmax(clear[np.isfinite(clear)])) + 1.0
  ts = np.concatenate([np.linspace(0, t_end, 40)])
  frames = []
  for t in ts:
    fig = plt.figure(figsize=(7.2, 9), dpi=80)
    fig.text(0.05, 0.955, "Defrosting a frosted windshield", fontsize=19, weight="bold", color=INK)
    fig.text(0.05, 0.925, f"Humid January night, {1000 * r['frost_night']['humid_kg_m2']:.0f} g/m² of frost · "
             f"engine idling, defroster on", fontsize=12, color=INK2)
    fig.text(0.95, 0.955, f"{t:4.1f} min", ha="right", fontsize=16, color=INK, family="DejaVu Sans Mono")
    ax = fig.add_axes([0.08, 0.2, 0.84, 0.66]); ax.set_xlim(-0.8, 0.8); ax.set_ylim(-0.12, slant + 0.12)
    ax.set_aspect("equal"); ax.axis("off")
    top_w = width * 0.82
    for i in range(n):
      y0, y1 = i * slant / n, (i + 1) * slant / n
      w0 = width - (width - top_w) * y0 / slant
      w1 = width - (width - top_w) * y1 / slant
      done = clear[i] <= t
      col = "#4f6f8f" if done else "#e8ecf1"
      ax.add_patch(Polygon([(-w0 / 2, y0), (w0 / 2, y0), (w1 / 2, y1), (-w1 / 2, y1)], color=col, ec=col, lw=0.5))
    ax.add_patch(Polygon([(-width / 2, 0), (width / 2, 0), (top_w / 2, slant), (-top_w / 2, slant)], fill=False,
                         ec=INK, lw=2))
    ax.add_patch(Rectangle((-0.8, slant + 0.02), 1.6, 0.08, color="#fcfcfb"))
    za, zb = zone[0] * slant, zone[1] * slant
    cam_clear = bool(np.all(clear[int(zone[0] * n):int(math.ceil(zone[1] * n))] <= t))
    ax.add_patch(Rectangle((0.02, za), 0.16, zb - za, fill=False, ec=CRIT if not cam_clear else "#86b6ef", lw=2.6,
                           ls=(0, (4, 2))))
    ax.add_patch(Rectangle((0.04, zb + 0.005), 0.12, slant - zb - 0.01, color="#3a3936"))
    ax.text(0.21, (za + zb) / 2, "camera's view\n" + ("clear" if cam_clear else "frosted"), fontsize=12,
            color="white" if cam_clear else CRIT, va="center", weight="bold")
    for xv in (-0.45, -0.15, 0.15, 0.45):
      ax.annotate("", (xv, 0.16), (xv, -0.08), arrowprops=dict(arrowstyle="->", color="#b8401a", lw=2))
    ax.text(0, -0.11, "defroster vents", ha="center", fontsize=11, color="#b8401a")
    fig.text(0.05, 0.1, "Pale: frost; dark: clear glass. A lumped glass layer per strip, the jet's heat\ntransfer falling "
             "up the glass; estimated inputs, a band in windshield-fog.md.", fontsize=10.5, color=INK2)
    _stamp(fig)
    frames.append(_png(fig))
  _anim(frames, [150] * (len(frames) - 1) + [2500], path)


def fog_figures(p, r, out: Path):
  out.mkdir(exist_ok=True)
  _fog_map(r, out / "fig-wx-11-fog-map.webp")
  _fog_anim(p, r, out / "fig-wx-12-defrost-anim.webp")
  _report(out, "fig-wx-11", "fig-wx-12")


# ------------------------------------------------------------------------------------------------ crown

def _crown_budget(r, path):
  res, m = r["residual"], r["margin_m_s2"]
  crown, bank = r["slopes"][0]["uncompensated"], r["slopes"][1]["uncompensated"]
  rows = [("Crown, not compensated", crown, MUTED),
          ("Bank 2–6 %, not compensated", bank, MUTED),
          ("Filter lag at a crown change (brief)", res["flip_peak"], "#86b6ef"),
          ("Body roll against the fitted gain", [0.0, res["gradient_mismatch_bank"]], "#86b6ef"),
          ("Device mount roll 0–2°, before torqued learns it", [res["mount"]["low"], res["mount"]["high"]], "#2a78d6"),
          ("Roll invalid on a 2–6 % bank: all of it comes back", bank, "#104281"),
          ("Crosswind 30 km/h (for comparison)", r["crosswind_ks02"], "#b8401a")]
  fig = plt.figure(figsize=(9, 10), dpi=100)
  fig.text(0.05, 0.955, "Road crown: what is left after roll compensation", fontsize=18, weight="bold", color=INK)
  fig.text(0.05, 0.925, "110 km/h · lateral push or steering error, m/s², against the 0.5 m/s² curve margin",
           fontsize=12, color=INK2)
  ax = fig.add_axes([0.06, 0.2, 0.9, 0.66])
  ax.set_axisbelow(True)
  ax.axvspan(m, 2.0, color="#fdecec")
  ax.axvline(m, color=CRIT, lw=2)
  ax.text(m + 0.02, len(rows) - 0.35, f"{m} m/s² margin (WP-C-02 §3.2)", color=CRIT, fontsize=11, weight="bold")
  for i, (lab, (lo, hi), col) in enumerate(rows):
    y = len(rows) - 1 - i
    w = max(hi - lo, 0.012)
    ax.barh(y, w, left=lo, height=0.42, color=col)
    ax.text(0.0, y + 0.33, lab, fontsize=11.5, color=INK, va="bottom")
    ax.text(hi + 0.03, y, f"{lo:.2f}–{hi:.2f}" if hi - lo > 0.01 else f"{hi:.2f}", fontsize=11, color=INK2,
            va="center")
  ax.set_xlim(0, 2.0); ax.set_ylim(-0.6, len(rows) + 0.1); ax.set_yticks([])
  ax.set_xlabel("m/s²"); ax.grid(axis="x", color=GRID); ax.spines[["top", "right", "left"]].set_visible(False)
  fig.text(0.05, 0.075, "Grey: what compensation removes when the roll estimate is valid. Blue: what is left.\n"
           "openpilot's roll path read from the code; car and localizer inputs estimated.", fontsize=11.5, color=INK2)
  _stamp(fig)
  _save(fig, path)


def crown_figures(p, r, out: Path):
  out.mkdir(exist_ok=True)
  _crown_budget(r, out / "fig-wx-13-crown-budget.webp")
  _report(out, "fig-wx-13")


# ------------------------------------------------------------------------------------------------ wet braking

def _braking_mu(r, path):
  sp = np.array(r["speeds_kph"])
  conds = [("dry", "dry", MUTED, (0, (3, 2))), (f"{r['rain_mm_h'][0]:g}", f"rain {r['rain_mm_h'][0]:g} mm/h\n(ODD bound)",
                                                "#2a78d6", "-"),
           (f"{r['rain_mm_h'][-1]:g}", f"rain {r['rain_mm_h'][-1]:g} mm/h", "#104281", "-")]
  fig = plt.figure(figsize=(9, 12), dpi=100)
  fig.text(0.05, 0.965, "Friction for braking on a wet road", fontsize=19, weight="bold", color=INK)
  fig.text(0.05, 0.94, "Peak tyre-road friction (Bosch Automotive Handbook, typical tyres) against what the item needs",
           fontsize=12, color=INK2)
  for k, (tyre, title) in enumerate((("new", "New tyres"), ("worn_1_6mm", "Worn tyres, 1.6 mm tread"))):
    ax = fig.add_axes([0.1, 0.57 - k * 0.42, 0.66, 0.31])
    ax.axhspan(0, r["need_level"], color="#fdecec")
    ax.axhline(r["need_level"], color=CRIT, lw=2)
    ax.text(129, r["need_level"] + 0.02, f"item's −{r['item_decel']:.1f} m/s² needs {r['need_level']:.2f}", color=CRIT,
            fontsize=11, weight="bold", ha="right")
    ax.axvline(r["odd_speed_kph"], color=INK2, lw=1, ls=(0, (2, 2)))
    ax.text(r["odd_speed_kph"] + 1, 0.95, "ODD speed", fontsize=10.5, color=INK2)
    for key, lab, col, ls in conds:
      y = r["curves"][tyre][key]
      ax.plot(sp, y, color=col, lw=2.4, ls=ls)
      ax.text(sp[-1] + 1.5, y[-1], lab, fontsize=11, color=INK, va="center")
    ax.set_xlim(50, 130); ax.set_ylim(0, 1.05); ax.set_ylabel("peak friction")
    ax.set_title(title, loc="left", fontsize=14, color=INK)
    ax.grid(axis="y", color=GRID); ax.spines[["top", "right"]].set_visible(False)
    if k == 1:
      ax.set_xlabel("speed, km/h")
  fig.text(0.05, 0.06, "Water depth from the hydroplaning study's worst drainage row, at least 0.2 mm (a wet road).\n"
           "A handbook table of typical tyres, interpolated; not this car's tyres.", fontsize=11.5, color=INK2)
  _stamp(fig)
  _save(fig, path)


def _braking_anim(r, path):
  odd = r["odd_speed_kph"]
  key = f"{r['rain_mm_h'][0]:g}"
  cars = [("New tyres", r["at_odd_speed"]["new"][key], "#2a78d6"),
          ("Worn tyres, 1.6 mm", r["at_odd_speed"]["worn_1_6mm"][key], "#104281")]
  v0 = odd / 3.6
  t_react = 0.5
  def pos(t, a):
    if t < t_react:
      return v0 * t, v0
    tb = min(t - t_react, v0 / a)
    return v0 * t_react + v0 * tb - 0.5 * a * tb * tb, max(v0 - a * (t - t_react), 0.0)
  t_end = t_react + v0 / min(min(c[1]["a_max"], r["item_decel"]) for c in cars) + 1.0
  frames = []
  ts = np.linspace(0, t_end, 48)
  far = max(c[1]["stop_item_m"] for c in cars) * 1.05
  for t in ts:
    fig = plt.figure(figsize=(7.2, 9), dpi=80)
    fig.text(0.05, 0.955, "Braking from 110 km/h, light rain", fontsize=18, weight="bold", color=INK)
    fig.text(0.05, 0.925, f"the item asks for −{r['item_decel']:.1f} m/s²; the tyres give what they can", fontsize=12,
             color=INK2)
    fig.text(0.95, 0.885, f"t = {t:4.1f} s", ha="right", fontsize=15, color=INK, family="DejaVu Sans Mono")
    ax = fig.add_axes([0.05, 0.2, 0.9, 0.66]); ax.set_xlim(-6, 6); ax.set_ylim(-10, far + 10); ax.axis("off")
    ax.add_patch(Rectangle((-6, -10), 12, far + 20, color="#a9a7a0"))
    ax.plot([0, 0], [-10, far + 10], color="white", lw=2, ls=(0, (8, 8)))
    for yy in range(0, int(far) + 1, 50):
      ax.text(5.8, yy, f"{yy} m", fontsize=10, color="white", ha="right", va="center")
    for i, (lab, d, col) in enumerate(cars):
      a = min(d["a_max"], r["item_decel"])
      y, v = pos(t, a)
      x = -3 if i == 0 else 3
      ax.add_patch(Rectangle((x - 0.9, y - 12), 1.8, 12, color=col, ec=INK, lw=1))
      ax.plot([x - 1.3, x + 1.3], [d["stop_item_m"], d["stop_item_m"]], color=CRIT if i else "#1c5cab", lw=2)
      ax.text(x, -8, f"{lab}\n{v * 3.6:3.0f} km/h", ha="center", fontsize=11.5, color=INK, weight="bold",
              bbox=dict(boxstyle="round,pad=0.3", fc=SURF, ec=col))
    fig.text(0.05, 0.1, f"Stops at {cars[0][1]['stop_item_m']:.0f} m and {cars[1][1]['stop_item_m']:.0f} m, "
             f"0.5 s to brake. Worn tyres give {cars[1][1]['a_max']:.1f} m/s² on a\nwet road (handbook table): "
             "less than the item asks for. Cars not to scale.", fontsize=11, color=INK2)
    _stamp(fig)
    frames.append(_png(fig))
  _anim(frames, [140] * (len(frames) - 1) + [2500], path)


def braking_figures(p, r, out: Path):
  out.mkdir(exist_ok=True)
  _braking_mu(r, out / "fig-wx-14-braking-friction.webp")
  _braking_anim(r, out / "fig-wx-15-braking-anim.webp")
  _report(out, "fig-wx-14", "fig-wx-15")


# ------------------------------------------------------------------------------------------------ gust

def _gust_peaks(r, path):
  rows = [x for x in r["rows"] if x["kind"] != "step"]
  T = np.array([x["period_s"] for x in rows])
  step = next(x for x in r["rows"] if x["kind"] == "step")
  room = r["room_m"]
  fig = plt.figure(figsize=(9, 10), dpi=100)
  fig.text(0.05, 0.955, "A gust through the car and its lane keeping", fontsize=19, weight="bold", color=INK)
  fig.text(0.05, 0.925, f"Corolla at {r['speed_kph']:.0f} km/h, wind to {r['wind_kph']:.0f} km/h · peak sideways "
           "movement against the room to the lane line", fontsize=12, color=INK2)
  ax = fig.add_axes([0.12, 0.2, 0.62, 0.64])
  for k, lab in (("lane", "room, 3.7 m lane"), ("narrow", "room, 3.3 m lane")):
    ax.axhline(100 * room[k], color=CRIT, lw=1.8 if k == "lane" else 1.2, ls="-" if k == "lane" else (0, (4, 3)))
    ax.text(8.6, 100 * room[k], lab, color=CRIT, fontsize=11, va="center")
  lo = [100 * x["ideal_low"]["peak_m"] for x in rows]
  hi = [100 * x["ideal_high"]["peak_m"] for x in rows]
  ax.fill_between(T, lo, hi, color="#86b6ef", alpha=0.45, lw=0)
  ax.plot(T, hi, color="#2a78d6", lw=2.4, marker="o")
  ax.plot(T, lo, color="#2a78d6", lw=1.4, marker="o", mfc="white")
  ax.text(T[-1] * 1.08, hi[-1] + 6, "ideal steering\n(upper / lower band)", fontsize=11, color=INK)
  fb = [100 * x["feedback_high"]["peak_m"] for x in rows]
  ax.plot(T, fb, color=MUTED, lw=1.6, ls=(0, (3, 2)), marker="s", ms=5)
  ax.text(T[-1] * 1.08, fb[-1], "plant's stand-in,\nupper band", fontsize=11, color=INK2, va="center")
  for e, mk in (("ideal_low", "o"), ("ideal_high", "D")):
    ax.plot([0.3], [100 * step[e]["peak_m"]], mk, color="#104281", ms=10, mfc="white" if e == "ideal_low" else "#104281")
  ax.annotate(f"step, upper band: {100 * step['ideal_high']['peak_m']:.0f} cm", (0.3, 100 * step["ideal_high"]["peak_m"]),
              (0.45, 100 * step["ideal_high"]["peak_m"] - 25), fontsize=11, color=INK)
  ax.annotate(f"step, lower band: {100 * step['ideal_low']['peak_m']:.0f} cm", (0.3, 100 * step["ideal_low"]["peak_m"]),
              (0.45, 100 * step["ideal_low"]["peak_m"] + 25), fontsize=11, color=INK)
  ax.set_xscale("log"); ax.set_xlim(0.22, 9); ax.set_ylim(0, 260)
  ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
  ax.set_xticks([0.3, 0.5, 1, 2, 4, 8]); ax.set_xticklabels(["step", "0.5", "1", "2", "4", "8"])
  ax.set_xlabel("gust length, s (one-minus-cosine)"); ax.set_ylabel("peak sideways movement, cm")
  ax.grid(axis="y", color=GRID); ax.spines[["top", "right"]].set_visible(False)
  fig.text(0.05, 0.075, "Ideal steering adds the gust's push at once; only opendbc's torque rise limit and the EPS lag\n"
           "hold it back. In the upper band the steady push takes 89 % of the steering, so a step is not caught.",
           fontsize=11.5, color=INK2)
  _stamp(fig)
  _save(fig, path)


def _gust_anim(r, path):
  t = np.array(r["t_s"])
  lo, hi = r["traces"]["ideal-low-step-0"], r["traces"]["ideal-high-step-0"]
  lane, width = 3.7, 1.781
  top = _top_outline()
  sel = np.arange(0, len(t), 3)[: int(9.0 / (t[1] - t[0]) / 3)]
  frames = []
  for i in sel:
    fig = plt.figure(figsize=(7.2, 9), dpi=80)
    fig.text(0.05, 0.955, "Leaving shelter into a 30 km/h wind", fontsize=18, weight="bold", color=INK)
    fig.text(0.05, 0.925, "110 km/h, ideal steering · the wind's load band, lower and upper", fontsize=12, color=INK2)
    fig.text(0.95, 0.885, f"t = {max(t[i] - 1.0, 0):3.1f} s", ha="right", fontsize=15, color=INK, family="DejaVu Sans Mono")
    for k, (tr, title) in enumerate(((lo, "lower band"), (hi, "upper band"))):
      ax = fig.add_axes([0.04 + k * 0.48, 0.2, 0.44, 0.62]); ax.set_xlim(-3.2, 3.2); ax.set_ylim(-2, 14); ax.set_aspect("equal")
      ax.axis("off")
      ax.add_patch(Rectangle((-3.2, -2), 6.4, 16, color="#d6d4cc"))
      for xl, st in ((-lane / 2, "-"), (lane / 2, "-")):
        ax.plot([xl, xl], [-2, 14], color="white", lw=2.5, ls=st)
      y = tr["y"][i]
      over = abs(y) + width / 2 > lane / 2
      car = np.c_[-top[:, 1] + y, top[:, 0] + 3]      # downwind (+y) is to the right, the wind from the left
      ax.add_patch(Polygon(car, color="#c84b2f" if over else "#6d6b64", ec=INK, lw=1))
      if tr["w"][i] > 0.5:
        for yy in (1, 5, 9):
          ax.annotate("", (-1.2, yy), (-2.9, yy), arrowprops=dict(arrowstyle="->", color="#1c5cab", lw=1.6))
      ax.text(0, 12.6, f"{title}\n{100 * abs(y):3.0f} cm", ha="center", fontsize=12, color=INK, weight="bold")
    fig.text(0.05, 0.1, "Top view of the 3.7 m lane, the wind from the left. In the upper band the steady\npush takes "
             "almost all the steering, and the car leaves the lane.", fontsize=10.5, color=INK2)
    _stamp(fig, "SYNTHETIC (DSR-12) · design aid, no credit · textbook loads")
    frames.append(_png(fig))
  _anim(frames, [120] * (len(frames) - 1) + [2500], path)


def gust_figures(p, r, out: Path):
  out.mkdir(exist_ok=True)
  _gust_peaks(r, out / "fig-wx-16-gust-peaks.webp")
  _gust_anim(r, out / "fig-wx-17-gust-anim.webp")
  _report(out, "fig-wx-16", "fig-wx-17")


# ------------------------------------------------------------------------------------------------ tunnel

def _tunnel_timeline(p, r, path):
  n = r["cases"]["nominal"]
  tr = n["trace"]
  t, lum, grey, target = (np.array(tr[k]) for k in ("t", "lum", "grey", "target"))
  stops = p["tunnel"]["off_stops"]["value"]
  fig = plt.figure(figsize=(9, 11.5), dpi=100)
  fig.text(0.05, 0.965, "Through a tunnel: the road camera's exposure", fontsize=19, weight="bold", color=INK)
  fig.text(0.05, 0.94, "openpilot's auto exposure (ported from camerad, OX03C10) at 110 km/h · CIE 88 orders of luminance",
           fontsize=12, color=INK2)
  wins = (("Entry", n["entry_s"] - 0.6, n["entry_s"] + 1.6), ("Exit", n["exit_s"] - 0.6, n["exit_s"] + 2.4))
  for k, (title, a, b) in enumerate(wins):
    sel = (t >= a) & (t <= b)
    ts = t[sel] - (n["entry_s"] if k == 0 else n["exit_s"])
    ax1 = fig.add_axes([0.1 + k * 0.46, 0.62, 0.38, 0.24])
    ax1.semilogy(ts, lum[sel], color=MUTED, lw=2)
    ax1.set_ylim(3, 2e4); ax1.set_title(title, loc="left", fontsize=14, color=INK)
    ax1.set_ylabel("road ahead, cd/m²" if k == 0 else ""); ax1.grid(axis="y", color=GRID)
    ax1.spines[["top", "right"]].set_visible(False)
    ax2 = fig.add_axes([0.1 + k * 0.46, 0.2, 0.38, 0.36])
    tg = target[sel]
    ax2.fill_between(ts, tg / 2 ** stops, np.minimum(tg * 2 ** stops, 1), color="#cde2fb", lw=0)
    ax2.plot(ts, tg, color="#2a78d6", lw=1.2, ls=(0, (4, 3)))
    g = grey[sel]
    bad = np.abs(np.log2(np.maximum(g, 1e-6) / tg)) > stops
    ax2.plot(ts, g, color=INK, lw=2.2)
    ax2.scatter(ts[bad], g[bad], color=CRIT, s=18, zorder=5)
    ax2.set_ylim(0, 1.02); ax2.set_xlabel(f"s after the {'portal' if k == 0 else 'exit'}")
    ax2.set_ylabel("grey the loop measures" if k == 0 else ""); ax2.grid(axis="y", color=GRID)
    ax2.spines[["top", "right"]].set_visible(False)
    w = n["entry"] if k == 0 else n["exit"]
    ax2.text(0.98, 0.95, f"{w['frames']} frames off\n({1000 * w['frames'] / r['code']['fps']:.0f} ms)", transform=ax2.transAxes,
             ha="right", va="top", fontsize=12, color=CRIT, weight="bold")
  fig.text(0.05, 0.085, "Blue band: within one stop of the loop's target grey; red dots: frames outside it. The exit is "
           "the\nlonger window: an overexposed frame tells the loop little, so it steps down slowly.", fontsize=11.5,
           color=INK2)
  _stamp(fig)
  _save(fig, path)


def tunnel_figures(p, r, out: Path):
  out.mkdir(exist_ok=True)
  _tunnel_timeline(p, r, out / "fig-wx-18-tunnel.webp")
  _report(out, "fig-wx-18")


# ------------------------------------------------------------------------------------------------ headlights

def _headlight_contrast(p, r, path):
  h = p["headlights"]
  vf = h["veil_fraction"]
  cases = [("undivided", h["offsets_m"]["undivided"], "undivided road, one lane over (outside the ODD)", CRIT),
           ("divided", h["offsets_m"]["divided"][0], f"divided, {h['offsets_m']['divided'][0]:g} m median", "#104281"),
           ("divided", h["offsets_m"]["divided"][1], f"divided, {h['offsets_m']['divided'][1]:g} m median", "#2a78d6"),
           ("divided", h["offsets_m"]["divided"][2], f"divided, {h['offsets_m']['divided'][2]:g} m median", "#86b6ef")]
  fig = plt.figure(figsize=(9, 10), dpi=100)
  fig.text(0.05, 0.955, "Oncoming high beams at night: the road's contrast", fontsize=18, weight="bold", color=INK)
  fig.text(0.05, 0.925, "Undipped driving beam (UN R112, 40,500 cd) · veiling glare from the lens and windshield, "
           "1–10 %", fontsize=12, color=INK2)
  ax = fig.add_axes([0.12, 0.2, 0.84, 0.64])
  for road, off, lab, col in cases:
    tr = r["cases"][f"{road}-{off:g}-high-value"]["trace"]
    d, veil = np.array(tr["d"]), np.array(tr["veil"])
    seen = veil > 0
    c_lo = 1 / (1 + veil * vf["high"] / vf["value"])     # the veil scales with the scatter share
    c_hi = 1 / (1 + veil * vf["low"] / vf["value"])
    ax.fill_between(d[seen], 100 * c_lo[seen], 100 * c_hi[seen], color=col, alpha=0.18, lw=0)
    leave = r["cases"][f"{road}-{off:g}-high-value"]["leave_frame_m"]
    ax.plot(d[seen], 100 / (1 + veil[seen]), color=col, lw=2.2, label=f"{lab}: leaves the frame at {leave:.0f} m")
    ax.plot([d[seen][-1]], [100 / (1 + veil[seen][-1])], "o", color=col, ms=7)
  ax.set_xlim(250, 0); ax.set_ylim(0, 105)
  ax.legend(loc="lower left", frameon=False, fontsize=10.5)
  ax.set_xlabel("distance to the oncoming car along the road, m"); ax.set_ylabel("road contrast left, %")
  ax.grid(axis="y", color=GRID); ax.spines[["top", "right"]].set_visible(False)
  low = min(v["contrast_min"] for k, v in r["cases"].items() if "-low-" in k)
  fig.text(0.05, 0.075, "Lines: 3 % scatter; bands: 1–10 %. The beam's peak intensity is taken in every direction, an\n"
           f"upper bound. Low beams (≤ 350 cd toward us) leave at least {100 * low:.0f} % of the contrast in every case.",
           fontsize=11.5, color=INK2)
  _stamp(fig)
  _save(fig, path)


def headlight_figures(p, r, out: Path):
  out.mkdir(exist_ok=True)
  _headlight_contrast(p, r, out / "fig-wx-19-headlights.webp")
  _report(out, "fig-wx-19")


# ------------------------------------------------------------------------------------------------ sun on the device

GLASS_COL = {1: "#86b6ef", 2: "#f6b48f", 3: "#b9b7ae", 4: "#cfa6e8"}
GLASS_LAB = {1: "through the windshield", 2: "through the roof panel", 3: "through a side window", 4: "through the rear window"}


def _sky_map(ax, t, case, face, title, sun_paths):
  """The sky above the car as the face sees it: relative azimuth around (ahead at the top), elevation inward."""
  E, A = np.array(t["elev_deg"]), np.array(t["relaz_deg"])
  f = t["cases"][case][face]
  lit, via = np.array(f["lit"]), np.array(f["glass"])
  th = np.radians(A)
  for i in range(len(E) - 1):
    for j in range(len(A) - 1):
      if lit[i, j] <= 0:
        continue
      ax.bar((th[j] + th[j + 1]) / 2, E[i + 1] - E[i], width=th[j + 1] - th[j], bottom=90 - E[i + 1],
             color=GLASS_COL[int(via[i, j])], alpha=0.25 + 0.75 * float(lit[i, j]), lw=0)
  for lab, (rel, el, col) in sun_paths.items():
    ax.plot(np.radians(rel), 90 - el, color=col, lw=2.4, label=lab)
  ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
  ax.set_ylim(0, 90); ax.set_yticks([30, 60]); ax.set_yticklabels(["60°", "30°"], fontsize=9, color=MUTED)
  ax.set_xticks(np.radians([0, 90, 180, 270])); ax.set_xticklabels(["ahead", "right", "behind", "left"], fontsize=10)
  ax.grid(color=GRID); ax.set_title(title, fontsize=13, color=INK, pad=12)


def _device_sun(p, r, path):
  import pvlib
  t = json.loads((Path(__file__).resolve().parent.parent / "figures" / "corolla-e210-device-shading.json").read_text())
  s = p["sun"]
  head = s["corridor"]["northbound"]["heading"]
  paths = {}
  for lab, day, col in (("21 July", "2027-07-21", CRIT), ("21 December", "2027-12-21", "#104281")):
    tt = pd.date_range(f"{day} 05:00", f"{day} 21:00", freq="10min", tz=s["site"]["tz"])
    sp = pvlib.solarposition.get_solarposition(tt, s["site"]["lat"], s["site"]["lon"])
    up = sp["apparent_elevation"].to_numpy() > 0
    rel = (sp["azimuth"].to_numpy()[up] - head + 180) % 360 - 180
    paths[f"sun, {lab}, northbound"] = (rel, sp["apparent_elevation"].to_numpy()[up], col)
  fig = plt.figure(figsize=(9, 12.5), dpi=100)
  fig.text(0.05, 0.968, "Sun on the device through the car", fontsize=19, weight="bold", color=INK)
  fig.text(0.05, 0.943, "Ray cast through the Corolla mesh from each face of the comma device · clear sky, I-85 corridor",
           fontsize=12, color=INK2)
  for k, (face, title) in enumerate((("front", "Windshield side: the sky it sees"), ("screen", "Screen side (cabin)"))):
    ax = fig.add_axes([0.06 + 0.5 * k, 0.57, 0.37, 0.29], projection="polar")
    _sky_map(ax, t, "glass_roof", face, title, paths)
  hs = [Patch(color=GLASS_COL[c], label=GLASS_LAB[c]) for c in (1, 2, 3, 4)]
  hs += [plt.Line2D([], [], color=v[2], lw=2.4, label=k) for k, v in paths.items()]
  fig.legend(handles=hs, loc="upper left", bbox_to_anchor=(0.05, 0.535), ncol=2, frameon=False, fontsize=10.5)
  c = r["cases"]["glass_roof"]
  m = r["model"]
  ax = fig.add_axes([0.12, 0.17, 0.84, 0.25])
  styles = {"northbound": ("northbound", "#2a78d6"), "southbound": ("southbound", "#104281"),
            c["worst_parked"]: (f"parked facing {c['headings'][c['worst_parked']]['heading']:.0f}°", "#b8401a")}
  for dn, ls in (("summer", "-"), ("winter", (0, (4, 2)))):
    dd = c["days"][dn]
    hr = np.array(dd["hour"])
    for name, (lab, col) in styles.items():
      tot = sum(np.array(v) for v in dd[name].values())
      ax.plot(hr, tot, color=col, lw=2.2, ls=ls, label=f"{lab}, {'21 July' if dn == 'summer' else '21 December'}")
  ax.axhspan(m["band_w"][0], m["band_w"][1], color=GRID, lw=0)
  ax.axhline(m["power_w"], color=INK, lw=1.6)
  ax.text(5.2, m["power_w"] + 0.05, f"heat model: {m['power_w']:.2f} W all day (band {m['band_w'][0]:.1f}–{m['band_w'][1]:.1f})",
          fontsize=10.5, color=INK, va="bottom")
  ax.set_xlim(5, 21); ax.set_ylim(0, max(3.3, m["band_w"][1] + 0.3))
  ax.set_xlabel("hour of day (local)"); ax.set_ylabel("sun into the device, W")
  ax.grid(axis="y", color=GRID); ax.spines[["top", "right"]].set_visible(False)
  ax.legend(loc="upper right", frameon=False, fontsize=9.5, ncol=2)
  fig.text(0.05, 0.07, f"Brighter cells: more of the face lit. The year's most is {c['power_max_w']:.2f} W, in winter; in "
           f"June–August at most\n{c['summer_power_max_w']:.2f} W. The device's place on the glass is an estimate until T1; the "
           "mesh has a glass roof panel,\nthe reference car may not.", fontsize=11, color=INK2)
  _stamp(fig)
  _save(fig, path)


def device_sun_figures(p, r, out: Path):
  out.mkdir(exist_ok=True)
  _device_sun(p, r, out / "fig-wx-20-device-sun.webp")
  _report(out, "fig-wx-20")


# ------------------------------------------------------------------------------------------------ wet curves

def _wet_curves(r, path):
  v = np.array(r["speeds_kph"])
  n = r["need"]["flat"]
  fig, ax = plt.subplots(figsize=(9, 9.5), dpi=100)
  fig.subplots_adjust(left=0.12, right=0.95, top=0.84, bottom=0.2)
  fig.text(0.05, 0.95, "A curve at the ODD's bound on a wet road", fontsize=19, weight="bold", color=INK)
  fig.text(0.05, 0.92, f"Cornering at {r['a_lat']:.1f} m/s², with and without the item's {r['a_brake']:.1f} m/s² braking · "
           "light rain · handbook friction", fontsize=12, color=INK2)
  ax.fill_between(v, r["available"]["odd_3mm_mira"]["wet"], r["available"]["odd_3mm_continental"]["wet"],
                  color="#2a78d6", alpha=0.25, lw=0, label="grip, wet: 3 mm, the ODD's minimum (MIRA to Continental)")
  styles = {"new": ("new tyres", "#86b6ef"), "legal_1_6mm": ("1.6 mm, legal minimum (outside the ODD)", "#104281")}
  for k, (lab, col) in styles.items():
    ax.plot(v, r["available"][k]["wet"], "o-", color=col, lw=2.4, label=f"grip, wet: {lab}")
  ax.axhline(n["corner"], color=INK, lw=1.6, ls=(0, (4, 2)))
  ax.text(v[0], n["corner"] + 0.01, f"needed to corner: {n['corner']:.2f}", fontsize=11, color=INK, va="bottom")
  ax.axhline(n["corner_brake"], color=CRIT, lw=1.8)
  ax.text(v[0], n["corner_brake"] + 0.01, f"needed to corner and brake at the item's rate: {n['corner_brake']:.2f}",
          fontsize=11, color=CRIT, va="bottom")
  ax.set_xlim(v[0] - 2, v[-1] + 2); ax.set_ylim(0, 0.7)
  ax.set_xlabel("speed, km/h"); ax.set_ylabel("tyre-road friction")
  ax.grid(axis="y", color=GRID); ax.spines[["top", "right"]].set_visible(False)
  ax.legend(loc="upper right", frameon=False, fontsize=10.5)
  b = r["brake_in_curve_wet_3mm"]
  fig.text(0.05, 0.075, f"At 110 km/h the 3 mm tyres hold the curve and leave {b['odd_3mm_mira']['110']:.1f}–"
           f"{b['odd_3mm_continental']['110']:.1f} m/s² of braking.\nRound friction circle; the 3 mm band from measured "
           "wet stops 7 % (Continental) to 35 % (MIRA)\nlonger than with new tyres.", fontsize=11.5, color=INK2)
  _stamp(fig)
  _save(fig, path)


def wet_curves_figures(p, r, out: Path):
  out.mkdir(exist_ok=True)
  _wet_curves(r, out / "fig-wx-21-wet-curves.webp")
  _report(out, "fig-wx-21")


# ------------------------------------------------------------------------------------------------ crest

def _crest(p, r, path):
  c = r["cases"]["110"]
  k = c["k"]
  A = 4.0
  L = k * A
  fig = plt.figure(figsize=(9, 11), dpi=100)
  fig.text(0.05, 0.965, "Over a hill crest: who sees the stopped car first", fontsize=19, weight="bold", color=INK)
  fig.text(0.05, 0.94, f"AASHTO crest built for 110 km/h (K {k:.0f}, 4 % grade change) · heights exaggerated ×40",
           fontsize=12, color=INK2)
  ax = fig.add_axes([0.08, 0.6, 0.88, 0.28])
  x = np.linspace(-L / 2 - 60, L / 2 + 60, 600)
  def y(xx):
    xx = np.asarray(xx, float)
    inside = -xx ** 2 / (200 * k)
    left = -(L / 2) ** 2 / (200 * k) + (A / 200) * (xx + L / 2)
    right = -(L / 2) ** 2 / (200 * k) - (A / 200) * (xx - L / 2)
    return np.where(xx < -L / 2, left, np.where(xx > L / 2, right, inside))
  ex = 40.0
  ax.fill_between(x, y(x) * ex - 4, y(x) * ex, color="#d9d7cf", lw=0)
  ax.plot(x, y(x) * ex, color=INK2, lw=1.5)
  ch = p["crest"]["camera_height_m"]["value"]; rh = p["crest"]["radar_height_m"]["value"]
  tg = p["crest"]["targets_m"]
  for lab, h1, h2, d, col in (("camera", ch, tg["tail_lights"], c["sight_m"]["camera_tail_lights"], "#2a78d6"),
                              ("radar", rh, tg["radar_return"], c["sight_m"]["radar_return"], CRIT)):
    x0 = -d / 2 * (math.sqrt(h1) / (math.sqrt(h1) + math.sqrt(h2))) * 2
    x1 = x0 + d
    ax.plot([x0, x1], [(y(x0) + h1) * ex, (y(x1) + h2) * ex], color=col, lw=2, label=f"{lab}: sees it at {d:.0f} m")
    ax.plot([x0], [(y(x0) + h1) * ex], "o", color=col, ms=7)
    if lab == "camera":
      car_x = x1
  ax.add_patch(Rectangle((car_x, float(y(car_x)) * ex), 4.5, tg["roof"] * ex, color=INK, lw=0))
  ax.text(car_x + 6, float(y(car_x)) * ex + tg["roof"] * ex / 2, "stopped car", fontsize=10.5, color=INK, va="center")
  ax.set_xlim(x[0], x[-1]); ax.set_yticks([]); ax.set_xlabel("m along the road")
  ax.spines[["top", "right", "left"]].set_visible(False)
  ax.legend(loc="lower center", frameon=False, fontsize=10.5, ncol=2)
  ax2 = fig.add_axes([0.3, 0.17, 0.62, 0.32])
  rows = [("camera sees the tail lights", c["sight_m"]["camera_tail_lights"], "#2a78d6"),
          ("driver sees the tail lights", c["sight_m"]["driver_tail_lights"], "#86b6ef"),
          ("radar sees the car", c["sight_m"]["radar_return"], CRIT),
          ("stop: driver, wet, 3 mm tread", c["need_at_110_m"]["driver_wet_3mm"], INK),
          ("stop: the item's −3.5 m/s²", c["need_at_110_m"]["item_rate"], INK2),
          ("stop: driver, dry", c["need_at_110_m"]["driver_dry"], MUTED)]
  for i, (lab, val, col) in enumerate(rows):
    ax2.barh(i, val, color=col, height=0.6)
    ax2.text(val + 3, i, f"{val:.0f} m", va="center", fontsize=11, color=INK)
  ax2.set_yticks(range(len(rows))); ax2.set_yticklabels([r_[0] for r_ in rows], fontsize=11)
  ax2.invert_yaxis(); ax2.set_xlim(0, 300); ax2.set_xlabel("distance at 110 km/h, m")
  ax2.spines[["top", "right"]].set_visible(False); ax2.grid(axis="x", color=GRID)
  fig.text(0.05, 0.075, "The radar sits lowest, so over a crest it sees the stopped car last. Radar height is an estimate "
           "until T1;\nthe item does not brake for an untracked stopped car: the driver and the stock PCS do.",
           fontsize=11, color=INK2)
  _stamp(fig)
  _save(fig, path)


def crest_figures(p, r, out: Path):
  out.mkdir(exist_ok=True)
  _crest(p, r, out / "fig-wx-22-crest.webp")
  _report(out, "fig-wx-22")


# ------------------------------------------------------------------------------------------------ stopped car

def _stopped_car(p, r, path):
  s = p["stopped_car"]
  w = s["car_rear_m"]["width"]
  d = np.linspace(20, 300, 400)
  fig, ax = plt.subplots(figsize=(9, 9.5), dpi=100)
  fig.subplots_adjust(left=0.12, right=0.95, top=0.84, bottom=0.2)
  fig.text(0.05, 0.95, "A stopped car ahead: its size in the driving model's input", fontsize=18, weight="bold", color=INK)
  fig.text(0.05, 0.92, f"{w:.1f} m wide car's rear · model input frames from openpilot's model.py · 110 km/h",
           fontsize=12, color=INK2)
  for frame, col in (("narrow", "#2a78d6"), ("wide", "#86b6ef")):
    fl = r["code"][f"{frame}_fl_px"]
    ax.plot(d, fl * w / d, color=col, lw=2.4, label=f"{frame} road camera frame ({fl:.0f} px focal length)")
  ax.axhspan(0, s["small_object_px"]["value"], color="#fdecec", lw=0)
  ax.text(295, s["small_object_px"]["value"] + 1, "below 32 px: a small object for detectors (MS COCO)", ha="right",
          fontsize=10.5, color=CRIT)
  labels = {"item": "item stops at −3.5", "driver_unwarned_dry": "driver, 2.5 s, dry",
            "driver_unwarned_wet": "driver, 2.5 s, wet 3 mm"}
  for i, (k, lab) in enumerate(labels.items()):
    x = r["stop_m"][k]
    ax.axvline(x, color=INK2, lw=1.2, ls=(0, (4, 2)))
    ax.text(x + 3, 58 - 7 * (i % 2), f"{lab}\n{x:.0f} m", fontsize=10, color=INK2, va="top")
  ax.set_xlim(20, 300); ax.set_ylim(0, 60)
  ax.set_xlabel("distance to the stopped car, m"); ax.set_ylabel("car's width in the model's input, px")
  ax.grid(axis="y", color=GRID); ax.spines[["top", "right"]].set_visible(False)
  ax.legend(loc="upper right", bbox_to_anchor=(1.0, 0.72), frameon=False, fontsize=10.5)
  fig.text(0.05, 0.075, f"For the item to stop on its own the model must take the car as a lead at "
           f"{r['stop_m']['item']:.0f} m, where it is {r['px_at_stop']['narrow']['item']:.0f} px wide.\nWhat the model "
           "detects at that size is learned, not computed here.", fontsize=11.5, color=INK2)
  _stamp(fig)
  _save(fig, path)


def stopped_car_figures(p, r, out: Path):
  out.mkdir(exist_ok=True)
  _stopped_car(p, r, out / "fig-wx-23-stopped-car.webp")
  _report(out, "fig-wx-23")
