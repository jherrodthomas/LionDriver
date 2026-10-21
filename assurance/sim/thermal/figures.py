"""Figures of the device heat model: the 3D field (PyVista, off-screen), the drive and the bound (matplotlib).

Called by `thermal_pilot.py --figures`. Writes lossless or near-lossless WebP into `figures/` (PNG and GIF go to the
read-only LFS store in this repository). Rendering differs slightly between machines, so CI checks the numbers,
not the pixels. Every figure is stamped synthetic (DSR-12), design aid, no evidence credit (DQ-413).
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from PIL import Image  # noqa: E402

INK, INK2, CRIT, GRID, SURF = "#0b0b0b", "#52514e", "#d03b3b", "#e6e5e0", "#fcfcfb"
HEAT = LinearSegmentedColormap.from_list("heat", ["#fdeee5", "#f6b48f", "#eb6834", "#b8401a", "#6b220b"])
BLUES = {35.0: "#86b6ef", 45.0: "#2a78d6", 55.0: "#104281"}
STAMP = "SYNTHETIC (DSR-12) · design aid, no evidence credit · inputs are estimates until T1"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13, "axes.edgecolor": "#8a8984",
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "figure.facecolor": SURF, "axes.facecolor": SURF})


def _stamp(fig):
  fig.text(0.5, 0.012, STAMP, ha="center", va="bottom", fontsize=10.5, color=CRIT, weight="bold",
           bbox=dict(boxstyle="round,pad=0.35", fc="#fdecec", ec=CRIT, lw=1))


def _save(fig, path: Path):
  buf = io.BytesIO()
  fig.savefig(buf, format="png", facecolor=SURF)
  plt.close(fig)
  Image.open(buf).convert("RGB").save(path, "WEBP", quality=90, method=6)


def _offscreen():
  # Mesa's software EGL, no screen or GPU (TE-04 OI-2); harmless where a display exists
  prefix = Path(os.environ.get("CONDA_PREFIX", Path(__file__).resolve().parent))
  vendor = prefix / "share" / "glvnd" / "egl_vendor.d" / "50_mesa.json"
  if vendor.is_file():
    os.environ.setdefault("__EGL_VENDOR_LIBRARY_FILENAMES", str(vendor))
  os.environ.setdefault("EGL_PLATFORM", "surfaceless")
  os.environ.setdefault("VTK_DEFAULT_OPENGL_WINDOW", "vtkEGLRenderWindow")


def _grid(model, values):
  import pyvista as pv
  from dolfinx import plot
  top, types, geom = plot.vtk_mesh(model.V)
  g = pv.UnstructuredGrid(top, types, geom * 1000.0)
  g.point_data["T"] = values
  return g


def _render(model, values, centres, clim, size=(900, 640), clip=False):
  import pyvista as pv
  g = _grid(model, values)
  p = pv.Plotter(off_screen=True, window_size=size)
  p.set_background(SURF)
  kw = dict(scalars="T", cmap=HEAT, clim=clim, show_scalar_bar=False, ambient=0.55, diffuse=0.45, specular=0.0)
  if clip:
    # cut through the SoC plane to show the inside
    p.add_mesh(g.clip(normal=(0, 0, -1), origin=(0, 0, centres["soc"][2] * 1000.0)), **kw)
  else:
    p.add_mesh(g, **kw)
  L = model.box.size
  glass = pv.Plane(center=(L[0] * 500, L[1] * 1000 + 3, L[2] * 500 + 10), direction=(0, 1, -0.25),
                   i_size=L[0] * 1000 * 1.25, j_size=L[2] * 1000 * 2.4)
  p.add_mesh(glass, color="#9ec5f4", opacity=0.3)
  pts = np.array([np.array(centres[n]) * 1000.0 for n in ("soc", "mcu")])
  if not clip:
    pts[:, 2] = 0.0
  L0 = np.array([[L[0] * 1000.0, L[1] * 500.0, 0.0 if not clip else centres["soc"][2] * 1000.0]])
  pts = np.vstack([pts, L0])
  p.add_point_labels(pts, ["SoC", "panda MCU", "fan side"], font_size=22, point_size=14, point_color="white",
                     text_color=INK, shape_opacity=0.75, always_visible=True)
  p.add_mesh(g.outline(), color=INK2, line_width=1.5)
  p.camera_position = [(-60, 40, -170), (L[0] * 500, L[1] * 500, L[2] * 500), (0, 1, 0)]
  p.camera.zoom(1.15)
  img = p.screenshot(return_img=True)
  p.close()
  return img


def _field(model, res, snaps, air, path):
  centres = {n: model.box.sources[n][0] for n in ("soc", "mcu")}
  lim = res["limit_used"]
  clim = (5 * np.floor(snaps[-1].min() / 5), max(5 * np.ceil(snaps[-1].max() / 5), lim + 2))
  outside = _render(model, snaps[-1], centres, clim)
  inside = _render(model, snaps[-1], centres, clim, clip=True)
  fig = plt.figure(figsize=(9, 12.2), dpi=100)
  fig.text(0.05, 0.968, "Device temperature after a 60 min drive", fontsize=20, weight="bold", color=INK)
  fig.text(0.05, 0.945, f"comma 3X box model · cabin air {air:.0f} °C · sun on the glass · fan at 100 %",
           fontsize=13, color=INK2)
  for k, (img, title) in enumerate([(outside, "Outside: the screen side faces you, the glass is above"),
                                    (inside, "Cut through the SoC plane (screen half removed)")]):
    ax = fig.add_axes([0.03, 0.53 - k * 0.43, 0.82, 0.39])
    ax.imshow(img); ax.axis("off")
    ax.set_title(title, loc="left", fontsize=13.5, color=INK)
  cax = fig.add_axes([0.88, 0.2, 0.03, 0.6])
  sm = plt.cm.ScalarMappable(cmap=HEAT, norm=plt.Normalize(*clim))
  cb = fig.colorbar(sm, cax=cax); cb.set_label("°C", color=INK2); cb.outline.set_visible(False)
  cb.ax.axhline(lim, color=CRIT, lw=2.5)
  cb.ax.text(-0.3, lim, f"{lim:.0f}", color=CRIT, ha="right", va="center", fontsize=11, weight="bold",
             transform=cb.ax.get_yaxis_transform())
  d = res["drives"][str(air)]
  fig.text(0.05, 0.065, f"Hottest SoC point {d['soc'][-1]:.0f} °C, panda MCU {d['mcu'][-1]:.0f} °C. "
           "A homogenised box: no board,\nspreader or fan duct is drawn, so it shows where the heat goes, "
           "not the exact hot spot.", fontsize=11.5, color=INK2)
  _stamp(fig)
  _save(fig, path)


def _drive(res, path):
  lim, back = res["limit_used"], res["bands"]["comma 3X"]["ok_again_below"]
  fig, ax = plt.subplots(figsize=(9, 9), dpi=100)
  fig.subplots_adjust(left=0.12, right=0.8, top=0.82, bottom=0.2)
  fig.text(0.05, 0.94, "SoC temperature during a drive, against the overheat limit", fontsize=18, weight="bold",
           color=INK)
  fig.text(0.05, 0.905, "comma 3X box model · hottest SoC point · after a sun soak · fan at 100 %", fontsize=13,
           color=INK2)
  ax.axhspan(lim, 120, color="#fdecec")
  ax.axhline(lim, color=CRIT, lw=2)
  ax.text(59, lim + 11, f"above {lim:.0f} °C: overheated → soft disable", color=CRIT, fontsize=12, weight="bold",
          ha="right")
  ax.axhline(back, color=CRIT, lw=1, ls=(0, (4, 3)))
  ax.text(59, back - 3, f"{back:.0f} °C: back to ok", color=CRIT, fontsize=11, ha="right")
  for a, d in res["drives"].items():
    a = float(a)
    ax.plot(d["t_min"], d["soc"], color=BLUES.get(a, INK2), lw=2.4)
    ax.text(61, d["soc"][-1], f"cabin {a:.0f} °C", color=INK, fontsize=12.5, va="center")
    if d["crosses_at_min"] is not None:
      ax.plot(d["crosses_at_min"], lim, "o", ms=9, mfc="white", mec=CRIT, mew=2)
      ax.annotate(f"crosses at {d['crosses_at_min']:.0f} min", (d["crosses_at_min"], lim), (2, lim + 9),
                  fontsize=12.5, color=CRIT, weight="bold", arrowprops=dict(arrowstyle="-", color=CRIT))
  ax.set_xlim(0, 60); ax.set_ylim(40, 120)
  ax.set_xlabel("minutes after engaging"); ax.set_ylabel("°C")
  ax.grid(axis="y", color=GRID); ax.spines[["top", "right"]].set_visible(False)
  fig.text(0.05, 0.085, "One line per cabin air temperature; darker = hotter. The limit is read from\n"
           "openpilot/system/hardware/hardwared.py by the script.", fontsize=11.5, color=INK2)
  _stamp(fig)
  _save(fig, path)


def _bound(res, path):
  s, b, lim = res["sweep"], res["bound"], res["limit_used"]
  fig, ax = plt.subplots(figsize=(9, 9), dpi=100)
  fig.subplots_adjust(left=0.12, right=0.95, top=0.82, bottom=0.2)
  fig.text(0.05, 0.94, "A candidate ambient bound for the ODD", fontsize=18, weight="bold", color=INK)
  fig.text(0.05, 0.905, "Peak SoC temperature in a 60 min drive, against cabin air (WP-C-02 OI-3)", fontsize=13,
           color=INK2)
  ax.fill_between(s["air"], s["band_low"], s["band_high"], color="#cde2fb", lw=0)
  ax.plot(s["air"], s["nominal"], color="#2a78d6", lw=2.4)
  ax.axhline(lim, color=CRIT, lw=2)
  ax.text(s["air"][0] + 1, lim + 1.5, f"{lim:.0f} °C overheat limit", color=CRIT, fontsize=12, weight="bold")
  ax.text(s["air"][-1] - 1, min(s["band_low"]) - 1, "band: SoC power ±20 %, fan ±30 %,\nconductivity ±30 %, sun ±30 %",
          fontsize=11.5, color=INK2, ha="right")
  if b["worst_edge"] is not None:
    ax.axvline(b["worst_edge"], color=INK, lw=1.4, ls=(0, (4, 3)))
    ax.annotate(f"candidate bound\n≈ {b['worst_edge']:.0f} °C cabin air\n(worst edge of the band)",
                (b["worst_edge"], lim), (s["air"][0] + 1, lim + 12), fontsize=12.5, color=INK,
                weight="bold", arrowprops=dict(arrowstyle="->", color=INK))
  ax.set_xlim(s["air"][0], s["air"][-1]); ax.set_ylim(min(s["band_low"]) - 5, max(max(s["band_high"]), lim + 25))
  ax.set_xlabel("cabin air temperature at the mount, °C"); ax.set_ylabel("peak SoC, °C")
  ax.grid(axis="y", color=GRID); ax.spines[["top", "right"]].set_visible(False)
  nom = "—" if b["nominal"] is None else f"{b['nominal']:.0f} °C"
  fig.text(0.05, 0.085, f"Read from the worst edge, not the middle line ({nom}). A measured hot drive must\n"
           "confirm the model before the ODD uses it; the bound is the lead's (WP-C-02).", fontsize=11.5, color=INK2)
  _stamp(fig)
  _save(fig, path)


def _anim(model, res, times, snaps, air, path):
  centres = {n: model.box.sources[n][0] for n in ("soc", "mcu")}
  d = res["drives"][str(air)]
  lim = res["limit_used"]
  frames = []
  clim = (5 * np.floor(min(v.min() for v in snaps) / 5), max(5 * np.ceil(max(v.max() for v in snaps) / 5), lim + 2))
  for i in range(0, len(snaps), 2):
    img = _render(model, snaps[i], centres, clim, size=(720, 520))
    t = times[i] / 60
    fig = plt.figure(figsize=(7.2, 10), dpi=80)
    fig.text(0.05, 0.955, "Device heating up on a hot drive", fontsize=19, weight="bold", color=INK)
    fig.text(0.05, 0.925, f"comma 3X box model · cabin air {air:.0f} °C · sun on the glass", fontsize=13, color=INK2)
    ax = fig.add_axes([0.02, 0.5, 0.86, 0.4]); ax.imshow(img); ax.axis("off")
    cax = fig.add_axes([0.9, 0.53, 0.025, 0.33])
    cb = fig.colorbar(plt.cm.ScalarMappable(cmap=HEAT, norm=plt.Normalize(*clim)), cax=cax)
    cb.outline.set_visible(False); cb.ax.tick_params(labelsize=10); cb.ax.axhline(lim, color=CRIT, lw=2)
    fig.text(0.95, 0.955, f"t = {t:2.0f} min", ha="right", fontsize=16, color=INK, family="DejaVu Sans Mono")
    k = int(np.searchsorted(d["t_min"], t, side="right"))
    soc = d["soc"][max(k - 1, 0)]
    if soc >= lim:
      ax.text(0.5, 0.95, "⚠ System Overheated → soft disable", transform=ax.transAxes, ha="center", va="top",
              fontsize=14, weight="bold", color="white", bbox=dict(boxstyle="round,pad=0.4", fc=CRIT, ec=CRIT))
    a2 = fig.add_axes([0.13, 0.13, 0.82, 0.32])
    a2.axhspan(lim, 120, color="#fdecec"); a2.axhline(lim, color=CRIT, lw=2)
    a2.text(59, lim - 6, f"{lim:.0f} °C overheat limit", color=CRIT, ha="right", fontsize=12, weight="bold")
    a2.plot(d["t_min"], d["soc"], color=GRID, lw=2)
    a2.plot(d["t_min"][:k], d["soc"][:k], color="#104281", lw=2.6)
    a2.plot(t, soc, "o", ms=10, mfc="white", mec="#104281", mew=2.2)
    a2.set_xlim(0, 60); a2.set_ylim(40, 120)
    a2.set_xlabel("minutes after engaging"); a2.set_ylabel("hottest SoC point, °C")
    a2.grid(axis="y", color=GRID); a2.spines[["top", "right"]].set_visible(False)
    fig.text(0.5, 0.012, "SYNTHETIC (DSR-12) · design aid, no credit · estimated inputs", ha="center", va="bottom",
             fontsize=10.5, color=CRIT, weight="bold", bbox=dict(boxstyle="round,pad=0.35", fc="#fdecec", ec=CRIT))
    buf = io.BytesIO(); fig.savefig(buf, format="png", facecolor=SURF); plt.close(fig)
    frames.append(Image.open(buf).convert("RGB"))
  durs = [120] * (len(frames) - 1) + [2500]
  frames[0].save(path, "WEBP", save_all=True, append_images=frames[1:], duration=durs, loop=0, quality=72, method=6)


def render(p: dict, res: dict, out: Path):
  _offscreen()
  from thermal_pilot import build, drive
  out.mkdir(exist_ok=True)
  model = build(p)
  hot = max(float(a) for a in res["drives"])
  for air in (45.0, hot):
    times, _, snaps = drive(model, p, air)
    if air == 45.0:
      _field(model, res, snaps, air, out / "fig-th-1-field.webp")
    else:
      _anim(model, res, times, snaps, air, out / "fig-th-4-anim.webp")
  _drive(res, out / "fig-th-2-drive.webp")
  _bound(res, out / "fig-th-3-bound.webp")
  for f in sorted(out.glob("*.webp")):
    print(f"wrote {f.name} ({f.stat().st_size // 1024} KB)")


def cabin_figure(r: dict, path: Path):
  """The device's SoC through a hot day, on the cabin model's mount air and glass (cabin_drive.py)."""
  lim = r["limit_used"]
  names = {"hot_july": ("Hot July, AC on", "#2a78d6", "-"), "hot_july_ac_off": ("Hot July, AC off", "#104281", "-"),
           "mild_april": ("Mild April, AC on", "#86b6ef", "-")}
  fig, ax = plt.subplots(figsize=(9, 9.5), dpi=100)
  fig.subplots_adjust(left=0.12, right=0.78, top=0.84, bottom=0.2)
  fig.text(0.05, 0.95, "The device through a hot day", fontsize=19, weight="bold", color=INK)
  fig.text(0.05, 0.92, "comma 3X box model on the cabin model's mount air and glass · hottest SoC point", fontsize=12.5,
           color=INK2)
  first = next(iter(r["scenarios"].values()))
  t_drive = first["drive_starts_min"] / 60 + 12
  ax.axvspan(12, t_drive, color="#fbf3dc")
  ax.text(12.05, 113, "parked, device off", fontsize=11, color=INK2)
  ax.text(t_drive + 0.05, 113, "driving, device on", fontsize=11, color=INK2)
  ax.axhspan(lim, 120, color="#fdecec"); ax.axhline(lim, color=CRIT, lw=2)
  ax.text(12.05, lim + 1.5, f"{lim:.0f} °C overheat limit", color=CRIT, fontsize=12, weight="bold")
  for k, d in r["scenarios"].items():
    lab, col, ls = names.get(k, (k, INK2, "-"))
    t = np.array(d["t_min"]) / 60 + 12
    ax.plot(t, d["soc"], color=col, lw=2.4, ls=ls)
    ax.text(15.03, d["soc"][-1], lab, color=INK, fontsize=11.5, va="center")
  ax.set_xlim(12, 15); ax.set_ylim(20, 120); ax.set_xticks([12, 13, 14, 15])
  ax.set_xticklabels(["12:00", "13:00", "14:00", "15:00"]); ax.set_ylabel("°C")
  ax.grid(axis="y", color=GRID); ax.spines[["top", "right"]].set_visible(False)
  fig.text(0.05, 0.085, "Parked: the board is off and the fan still, the sun heats the device through the glass. "
           "Driving:\nthe board runs, the fan is at 100 % and the AC (or fresh air) cools the cabin.", fontsize=11.5,
           color=INK2)
  _stamp(fig)
  _save(fig, path)


def mcu_figure(p: dict, r: dict, out: Path):
  """The MCU's junction against the cabin air, as built and with the fan stalled, against its limit (mcu_heat.py)."""
  air = np.array(r["air"])
  jr = r["junction_rise_k"]
  tj = p["mcu"]["tj_max"]["industrial"]
  trip = r["tsr509"]["grades"]["industrial"]["trip_at_most"]
  fig, ax = plt.subplots(figsize=(9, 10), dpi=100)
  fig.subplots_adjust(left=0.12, right=0.74, top=0.84, bottom=0.2)
  fig.text(0.05, 0.95, "The safety MCU next to the SoC", fontsize=19, weight="bold", color=INK)
  fig.text(0.05, 0.92, "STM32H725 junction in the comma 3X box model, steady drive · band: package unknown",
           fontsize=12.5, color=INK2)
  ax.axhspan(tj, 150, color="#fdecec"); ax.axhline(tj, color=CRIT, lw=2)
  ax.text(air[0] + 0.5, tj + 2, f"{tj:.0f} °C junction limit (industrial part)", color=CRIT, fontsize=11.5,
          weight="bold")
  ax.axhline(trip, color=CRIT, lw=1.5, ls=(0, (5, 3)))
  ax.text(air[-1] - 0.5, trip - 5, f"candidate TSR-509 trip,\nDTS reading {trip:.0f} °C", color=CRIT, fontsize=11,
          ha="right", va="top")
  styles = {"as_built": ("as built, fan at 100 %", "#2a78d6"), "soc_off": ("SoC's heat taken away", "#86b6ef"),
            "fan_stalled": ("fan stalled", "#104281")}
  for s, (lab, col) in styles.items():
    blk = np.array(r["setups"][s]["mcu_block"])
    ax.fill_between(air, blk + jr["low"], blk + jr["high"], color=col, alpha=0.25, lw=0)
    ax.plot(air, blk + jr["nominal"], color=col, lw=2.4)
    ax.text(air[-1] + 0.8, blk[-1] + jr["nominal"], lab, color=INK, fontsize=11.5, va="center")
    if s in r["at_soc_limit"]:
      d = r["at_soc_limit"][s]
      y = (d["tj_low"] + d["tj_high"]) / 2
      ax.plot([d["air_at_soc_limit"]], [y], "o", ms=10, mfc="white", mec=col, mew=2.4)
      ax.annotate("SoC reaches 96 °C:\nthe host stops", (d["air_at_soc_limit"], y), (d["air_at_soc_limit"] + 3, y - 22),
                  fontsize=10.5, color=INK2, ha="left", arrowprops=dict(arrowstyle="-", color=INK2, lw=1))
  ax.set_xlim(air[0], air[-1]); ax.set_ylim(30, 150)
  ax.set_xlabel("cabin air at the device, °C"); ax.set_ylabel("MCU junction, °C")
  ax.grid(axis="y", color=GRID); ax.spines[["top", "right"]].set_visible(False)
  fig.text(0.05, 0.085, "Windshield 15 K above the cabin air, sun on the device. While the host runs, the SoC limit\n"
           "comes first; the trip line is for when it does not (TSR-509).", fontsize=11.5, color=INK2)
  _stamp(fig)
  out.mkdir(exist_ok=True)
  path = out / "fig-th-6-mcu.webp"
  _save(fig, path)
  print(f"wrote {path.name} ({path.stat().st_size // 1024} KB)")
