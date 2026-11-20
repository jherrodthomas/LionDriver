"""Figure of the planner studies (round 4 phase C). WebP; stamped synthetic (DSR-12), no evidence credit."""

from __future__ import annotations

import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

INK, INK2, MUTED, CRIT, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#d03b3b", "#e6e5e0", "#fcfcfb"
BLUE = ["#86b6ef", "#2a78d6", "#104281"]
STAMP = "SYNTHETIC (DSR-12) · design aid, no evidence credit"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13, "axes.edgecolor": MUTED, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "figure.facecolor": SURF, "axes.facecolor": SURF})


def _save(fig, path):
  buf = io.BytesIO()
  fig.savefig(buf, format="png", facecolor=SURF)
  plt.close(fig)
  Image.open(buf).convert("RGB").save(path, "WEBP", quality=90, method=6)


def figures(p, r, out: Path):
  out.mkdir(exist_ok=True)
  fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 11), dpi=100)
  fig.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.15, hspace=0.35)
  fig.text(0.05, 0.955, "openpilot's planner: a cut-out and a hard-braking lead", fontsize=18, weight="bold", color=INK)
  fig.text(0.05, 0.925, "openpilot's own longitudinal MPC in a closed loop · braking clipped at 3.5 m/s² · standard "
           "personality", fontsize=11.5, color=INK2)
  co = [x for x in r["cut_out"] if x["personality"] == "standard" and x["latency_s"] == 0.5]
  cols = {60: BLUE[0], 80: BLUE[1], 100: BLUE[2], 110: CRIT}
  for vk in p["speed_kph"]["value"]:
    rs = [x for x in co if x["speed_kph"] == vk]
    a1.plot([x["reveal_s"] for x in rs], [x["impact_kph"] or 0 for x in rs], "o-", color=cols[vk], lw=2,
            label=f"{vk} km/h")
  a1.set_xlabel("how late the lead swerves: its time to the stopped car, s"); a1.set_ylabel("impact speed, item alone, km/h")
  a1.set_title("29. A cut-out uncovers a stopped car (model takes it after 0.5 s)", fontsize=12, color=INK2, loc="left")
  a1.legend(frameon=False, fontsize=10.5); a1.set_ylim(bottom=0)
  hb = [x for x in r["hard_brake"] if x["personality"] == "standard"]
  for vk, col in ((80, BLUE[1]), (110, CRIT)):
    rs = [x for x in hb if x["speed_kph"] == vk]
    a2.plot([x["lead_decel"] for x in rs], [x["alone"]["impact_kph"] or 0 for x in rs], "o-", color=col, lw=2,
            label=f"{vk} km/h, item alone")
    a2.plot([x["lead_decel"] for x in rs], [x["with_driver"]["impact_kph"] or 0 for x in rs], "o--", color=col, lw=1.6,
            label=f"{vk} km/h, driver brakes 1.5 s after FCW")
  a2.set_xlabel("the lead's braking, m/s²"); a2.set_ylabel("impact speed, km/h")
  a2.set_title("30. A lead brakes hard at the planner's following gap", fontsize=12, color=INK2, loc="left")
  a2.legend(frameon=False, fontsize=10); a2.set_ylim(bottom=0)
  for ax in (a1, a2):
    ax.grid(color=GRID); ax.spines[["top", "right"]].set_visible(False)
  fig.text(0.05, 0.07, "Both are beyond the item's braking bound: the driver and the stock PCS (not modelled) stop "
           "for them.\nA cut-in (study 28) is mostly within it; see the results page.", fontsize=11, color=INK2)
  fig.text(0.5, 0.012, STAMP, ha="center", va="bottom", fontsize=10.5, color=CRIT, weight="bold",
           bbox=dict(boxstyle="round,pad=0.35", fc="#fdecec", ec=CRIT, lw=1))
  path = out / "fig-pl-1-lead-events.webp"
  _save(fig, path)
  print(f"wrote {path.name} ({path.stat().st_size // 1024} KB)")
