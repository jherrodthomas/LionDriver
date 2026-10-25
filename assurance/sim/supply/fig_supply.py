"""Figures of the 12 V cranking dip (crank.py). WebP (PNG and GIF go to LFS here). Stamped synthetic (DSR-12), design
aid, no evidence credit."""

from __future__ import annotations

import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

INK, INK2, MUTED, CRIT, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#d03b3b", "#e6e5e0", "#fcfcfb"
STAMP = "SYNTHETIC (DSR-12) · design aid, no evidence credit · generic power path"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13, "axes.edgecolor": MUTED, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "figure.facecolor": SURF, "axes.facecolor": SURF})
LINES = {"car": ("car supply (ISO 16750-2)", MUTED, 1.8, (0, (4, 2))), "vin": ("device input", "#86b6ef", 2.0, "-"),
         "v5": ("5 V rail", "#2a78d6", 2.0, "-"), "v33": ("MCU rail, 3.3 V", "#104281", 2.6, "-")}


def _save(fig, path):
  buf = io.BytesIO()
  fig.savefig(buf, format="png", facecolor=SURF)
  plt.close(fig)
  Image.open(buf).convert("RGB").save(path, "WEBP", quality=90, method=6)


def crank_figure(p: dict, r: dict, out: Path):
  out.mkdir(exist_ok=True)
  th = r["thresholds"]
  fig = plt.figure(figsize=(9, 12), dpi=100)
  fig.text(0.05, 0.968, "Engine cranking: the panda MCU's supply", fontsize=19, weight="bold", color=INK)
  fig.text(0.05, 0.943, "ngspice · ISO 16750-2 starting profiles · generic device power path, nominal parts",
           fontsize=12, color=INK2)
  for k, (level, res) in enumerate(r["levels"].items()):
    tr = res["trace"]
    t = (np.array(tr["t"]) - 0.02) * 1000
    ax = fig.add_axes([0.1, 0.665 - k * 0.25, 0.86, 0.19])
    for key, (lab, col, lw, ls) in LINES.items():
      ax.plot(t, tr[key], color=col, lw=lw, ls=ls, label=lab)
    ax.axhspan(th["pdr"], th["vdd_min"], color="#fdecec", lw=0)
    ax.axhline(th["bor3"], color=CRIT, lw=1.2, ls=(0, (2, 2)))
    if k == 0:
      ax.text(158, th["bor3"] - 0.5, "BOR3 2.61 V (not configured)", color=CRIT, fontsize=10, ha="right", va="top")
    lv = p["profile"]["levels"][level]
    m = res["variants"]["nominal"]
    ax.set_title(f"Level {level}: {lv['us6']:g} V for 15 ms, then {lv['us']:g} V  ·  {m['outcome']}", loc="left",
                 fontsize=13, color=INK)
    ax.set_xlim(-10, 160); ax.set_ylim(0, 15)
    ax.set_ylabel("V"); ax.grid(axis="y", color=GRID); ax.spines[["top", "right"]].set_visible(False)
    if k == 2:
      ax.set_xlabel("ms after the dip starts")
  fig.legend(*fig.axes[0].get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(0.06, 0.935), ncol=2,
             frameon=False, fontsize=10.5)
  fig.text(0.05, 0.06, "Level II drops the input under the converter's lockout: the 5 V and MCU rails collapse and "
           "the\ndevice restarts at 6.5 V. The lockout band (3.5–6 V) decides levels II and IV; the results table has "
           "each\npart's band. Red band: 1.62–1.71 V, where the MCU is out of range and not yet reset.",
           fontsize=11, color=INK2)
  fig.text(0.5, 0.012, STAMP, ha="center", va="bottom", fontsize=10.5, color=CRIT, weight="bold",
           bbox=dict(boxstyle="round,pad=0.35", fc="#fdecec", ec=CRIT, lw=1))
  path = out / "fig-sp-1-crank.webp"
  _save(fig, path)
  print(f"wrote {path.name} ({path.stat().st_size // 1024} KB)")
