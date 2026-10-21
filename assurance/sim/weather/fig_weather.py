"""Figures of the weather physics: sun in the road camera and hydroplaning. WebP (PNG and GIF go to LFS here).

Every figure is stamped synthetic (DSR-12), design aid, no evidence credit.
"""

from __future__ import annotations

import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Circle, Polygon, Rectangle  # noqa: E402
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
           "against measured parked cars (McLaren et al. 2005). The logger at the mount (DQ-411) checks it.",
           fontsize=11.5, color=INK2)
  _stamp(fig)
  _save(fig, path)


def _cabin_anim(r, path):
  d = r["scenarios"]["hot_july"]
  b = r["heat_model_bound"]
  t = np.array(d["t_min"])
  heat = LinearSegmentedColormap.from_list("heat", ["#cde2fb", "#fdeee5", "#f6b48f", "#eb6834", "#b8401a", "#6b220b"])
  norm = plt.Normalize(20, 90)
  body = [(0.5, 1.0), (1.2, 1.9), (3.0, 2.15), (4.4, 3.35), (6.6, 3.45), (8.2, 2.3), (9.6, 2.1), (9.7, 1.0)]
  cabin = [(3.15, 2.1), (4.5, 3.2), (6.5, 3.28), (7.9, 2.15), (7.9, 1.3), (3.15, 1.3)]
  frames = []
  for i in range(0, len(t), 2):
    driving = t[i] >= d["drive_starts_min"]
    fig = plt.figure(figsize=(7.2, 9), dpi=80)
    fig.text(0.05, 0.955, "A hot day in the cabin", fontsize=19, weight="bold", color=INK)
    fig.text(0.05, 0.925, "Corolla, clear 15 July · AC on when driving", fontsize=12.5, color=INK2)
    clock = 12 + t[i] / 60
    fig.text(0.95, 0.955, f"{int(clock):02d}:{int(round((clock % 1) * 60)) % 60:02d}", ha="right", fontsize=18,
             color=INK, family="DejaVu Sans Mono")
    ax = fig.add_axes([0.03, 0.47, 0.94, 0.42]); ax.set_xlim(0, 10.2); ax.set_ylim(0.2, 4.6); ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Polygon(body, color="#c9c7bf"))
    ax.add_patch(Polygon(cabin, color=heat(norm(d["air"][i]))))
    ax.plot([7.9, 6.5], [2.15, 3.28], color=heat(norm(d["glass"][i])), lw=7, solid_capstyle="round")
    ax.add_patch(Polygon([(7.0, 1.95), (7.85, 2.12), (7.85, 1.75), (7.0, 1.7)], color=heat(norm(d["dash"][i]))))
    for x in (2.0, 8.0):
      ax.add_patch(Circle((x, 1.0), 0.55, color="#2b2a28")); ax.add_patch(Circle((x, 1.0), 0.25, color="#8a8984"))
    ax.add_patch(Circle((6.62, 3.0), 0.14, color="white", ec=INK, lw=1.5, zorder=5))
    ax.text(5.4, 3.75, f"mount air {d['mount'][i]:.0f} °C", fontsize=13, weight="bold", color=INK)
    ax.text(4.0, 1.6, f"cabin {d['air'][i]:.0f} °C", fontsize=12, color=INK)
    ax.text(7.85, 1.42, f"dash {d['dash'][i]:.0f} °C", fontsize=11, color=INK, ha="right")
    if not driving:
      ax.add_patch(Circle((9.2, 4.1), 0.32, color="#f2a900"))
      ax.text(0.4, 4.1, "Parked in the sun", fontsize=13, weight="bold", color="#b8401a")
    else:
      ax.text(0.4, 4.1, "Driving, AC on", fontsize=13, weight="bold", color="#1c5cab")
      for y in (1.6, 2.1, 2.6):
        ax.annotate("", (0.2, y), (-0.6 + 0.4 * (i % 3), y), arrowprops=dict(arrowstyle="-", color=MUTED, lw=1.5))
    a2 = fig.add_axes([0.13, 0.13, 0.82, 0.28])
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
