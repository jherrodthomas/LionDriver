#!/usr/bin/env python3
"""Climate of the test corridor: NOAA's 1991–2020 hourly normals for Greenville-Spartanburg airport, month by hour.

The committed table `climate-gsp.csv` (288 rows, SI units) is derived from two NOAA NCEI products for station
USW00003870 (GREER, SC, 34.88 N, 82.22 W, 287 m), both US-government public domain:
- hourly normals, https://www.ncei.noaa.gov/data/normals-hourly/1991-2020/access/USW00003870.csv: temperature and dew
  point (normal, 10th and 90th percentile), sky cover shares (clear, few, scattered, broken, overcast), mean wind
  speed and the share of calm hours, for each hour of each day of the normal year, local standard time;
- monthly normals, https://www.ncei.noaa.gov/data/normals-monthly/1991-2020/access/USW00003870.csv: the monthly mean
  temperature, kept as an independent check of the reduction (test_weather.py F5).
Each hourly value is averaged over the days of its month. Rebuild after downloading both files:

    python3 climate.py --hourly USW00003870.csv --monthly USW00003870-monthly.csv

Synthetic use only (DSR-12): the table is real climate, but what the studies make of it is a design aid.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TABLE = HERE / "climate-gsp.csv"
HOURLY = {"t": "HLY-TEMP-NORMAL", "t10": "HLY-TEMP-10PCTL", "t90": "HLY-TEMP-90PCTL", "td": "HLY-DEWP-NORMAL",
          "td10": "HLY-DEWP-10PCTL", "td90": "HLY-DEWP-90PCTL", "clr": "HLY-CLOD-PCTCLR", "few": "HLY-CLOD-PCTFEW",
          "sct": "HLY-CLOD-PCTSCT", "bkn": "HLY-CLOD-PCTBKN", "ovc": "HLY-CLOD-PCTOVC", "wind": "HLY-WIND-AVGSPD",
          "calm": "HLY-WIND-PCTCLM"}
TEMPS = ("t", "t10", "t90", "td", "td10", "td90")
SKY = ("clr", "few", "sct", "bkn", "ovc")


def f_to_c(f):
  return (np.asarray(f, float) - 32.0) * 5.0 / 9.0


def build(hourly: Path, monthly: Path) -> pd.DataFrame:
  rows = list(csv.DictReader(hourly.open(encoding="utf-8")))
  df = pd.DataFrame({k: [float(r[c]) for r in rows] for k, c in HOURLY.items()})
  df["month"] = [int(r["month"]) for r in rows]
  df["hour"] = [int(r["hour"]) for r in rows]
  g = df.groupby(["month", "hour"]).mean().reset_index()
  for k in TEMPS:
    g[k] = f_to_c(g[k])
  g["wind"] = g["wind"] * 0.44704                      # mph to m/s
  mon = {int(r["DATE"]): float(r["MLY-TAVG-NORMAL"]) for r in csv.DictReader(monthly.open(encoding="utf-8"))}
  g["tavg_monthly"] = f_to_c([mon[m] for m in g["month"]])
  return g.round(3)


def load() -> pd.DataFrame:
  """The month × hour table: temperatures in °C, sky shares and calm share in %, wind in m/s."""
  return pd.read_csv(TABLE)


def main(argv):
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("--hourly", type=Path, required=True)
  ap.add_argument("--monthly", type=Path, required=True)
  a = ap.parse_args(argv[1:])
  g = build(a.hourly, a.monthly)
  g.to_csv(TABLE, index=False)
  print("wrote", TABLE.name, len(g), "rows")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
