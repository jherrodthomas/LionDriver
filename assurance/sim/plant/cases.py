"""Cases of the plant model: the faults of ../faults.yaml, the EPS-hold reruns, and three nominal runs."""

from __future__ import annotations

from pathlib import Path

import yaml

import re

from simulate import ODD_KPH, OVERSPEED_KPH, Case

CATALOG = Path(__file__).resolve().parents[1] / "faults.yaml"

NOMINAL = [
  Case("N-1", "No fault, straight", "none", "straight", "—", "—", t_fault=6.0, duration=4.0),
  Case("N-2", "No fault, curve inside the ODD (1.5 m/s²)", "none", "curve", "—", "—", t_fault=None, duration=6.0),
  Case("N-3", "No fault, curve at the ODD bound R_ODD (2.5 m/s²)", "none", "curve-odd-bound", "SG-02", "SFM-004",
       t_fault=None, duration=6.0, note="observation for WP-C-02 OI-2: the curve needs more than LAT_ACCEL_FACTOR"),
  Case("N-4", "No fault, KS-01 road (R = 300 m) at 2.0 m/s² (88.2 km/h)", "none", "KS-01", "—", "—",
       t_fault=None, duration=8.0, speed_kph=88.18),
]


def catalog() -> list[dict]:
  return yaml.safe_load(CATALOG.read_text(encoding="utf-8"))["faults"]


def from_entry(f: dict) -> Case:
  return Case(f["id"], f["title"], f["kind"], f["road"], ", ".join(f["sg"]), ", ".join(f["causes"]),
              wpv05=f.get("wp_v_05", ""), t_fault=f.get("t_fault"), engaged=f.get("engaged", True),
              figure=f.get("figure", False), longitudinal=f.get("longitudinal", False), note=f.get("note", ""),
              tsr=", ".join(f.get("tsr", [])), pcs=f.get("pcs", False), speed_kph=f.get("speed_kph", ODD_KPH))


def all_cases() -> list[Case]:
  out, over, families = list(NOMINAL), [], set()
  for f in catalog():
    c = from_entry(f)
    out.append(c)
    if f.get("eps_hold"):
      out.append(Case(**{**c.__dict__, "id": c.id + "-H", "eps": "hold", "figure": False}))
    family = re.sub(r"[a-z]$", "", c.id)
    if "speed_kph" not in f and family not in families:   # one over-speed margin case per fault family
      families.add(family)
      note = f"outside the ODD ({OVERSPEED_KPH:g} > {ODD_KPH:g} km/h, DQ-260): margin case"
      over.append(Case(**{**c.__dict__, "id": c.id + "-OS", "speed_kph": OVERSPEED_KPH, "figure": False,
                          "note": "; ".join(x for x in (c.note, note) if x)}))
  return out + over
