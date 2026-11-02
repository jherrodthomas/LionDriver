#!/usr/bin/env python3
"""Losing GPS in a tunnel (physics plan round 3, study 20; WP-C-06 TC-18, its 'GNSS loss').

The plan was to run openpilot's localizer through a tunnel and measure how far its position drifts. The code shows
there is nothing to drift: `locationd` does not read the GPS. It fuses the inertial sensors, the camera's odometry and
the car's state into the device's motion (`deviceMotion`), not a position on the earth. This study reads that from
the code, and every place that does read the GPS, and pins each line, so a change in openpilot that makes the GPS
matter while engaged fails here. Writes `../results/gnss-tunnel.json` and `.md`.

    python3 gnss_tunnel.py --check

Only the GPS half of TC-18: the lighting half is the tunnel study (`tunnel.py`). Synthetic (DSR-12), design aid,
no evidence credit.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
OP = SIM.parents[1] / "openpilot"
OUT_JSON = SIM / "results" / "gnss-tunnel.json"
OUT_MD = SIM / "results" / "gnss-tunnel.md"
GPS_SERVICES = ("gpsLocation", "gpsLocationExternal", "ubloxGnss", "qcomGnss", "liveLocationKalman")

# file, the lines this study rests on (regex), and what each one means; a line that no longer matches stops the study
PINS = [
  ("selfdrive/locationd/locationd.py",
   [(r"pm = messaging\.PubMaster\(\['deviceMotion'\]\)", "locationd publishes deviceMotion, the device's motion"),
    (r"sm = messaging\.SubMaster\(\['carState', 'extrinsicsCalibration', 'cameraOdometry'\], poll='cameraOdometry'\)",
     "its inputs are the car's state, the calibration and the camera's odometry (and the IMU), no GPS")]),
  ("selfdrive/controls/controlsd.py",
   [(r"device_motion = Pose\.from_device_motion\(self\.sm\['deviceMotion'\]\)",
     "the controller takes the motion from deviceMotion")]),
  ("selfdrive/selfdrived/selfdrived.py",
   [(r"ignore = self\.sensor_packets \+ self\.gps_packets \+ \['alertDebug', 'lateralManeuverPlan'\]",
     "selfdrived ignores the GPS service for its alive, rate and valid checks"),
    (r"ignore_alive=ignore, ignore_avg_freq=ignore,", "the ignore list applies to alive and rate"),
    (r"ignore_valid=ignore, frequency=int\(1/DT_CTRL\)\)", "and to valid"),
    (r"if not gps_ok and self\.sm\['deviceMotion'\]\.inputsOK and \(self\.distance_traveled > 1500\):",
     "after 1500 m without a GPS fix it raises the noGps event"),
    (r"self\.events\.add\(EventName\.noGps\)", "the event itself")]),
  ("selfdrive/selfdrived/events.py",
   [(r"EventName\.noGps: \{\},", "noGps carries no alert in any state: it does not warn, disengage or block engaging")]),
]


def code() -> dict:
  out = {"pins": []}
  for rel, lines in PINS:
    src = (OP / rel).read_text(encoding="utf-8")
    for pat, meaning in lines:
      if not re.search(pat, src):
        raise SystemExit(f"openpilot changed: {pat!r} not found in {rel}; review gnss_tunnel.py")
      out["pins"].append({"file": f"openpilot/{rel}", "means": meaning})
  # every python file under selfdrive and system that names a GPS service, outside tests and tools
  readers = []
  for base in ("selfdrive", "system", "common"):
    for f in sorted((OP / base).rglob("*.py")):
      if "/test" in str(f) or "/tests/" in str(f):
        continue
      txt = f.read_text(encoding="utf-8", errors="ignore")
      found = [s for s in GPS_SERVICES if re.search(rf"['\"]{s}['\"]|\b{s}\b", txt)]
      if found:
        readers.append({"file": f"openpilot/{f.relative_to(OP)}", "services": found})
  out["gps_readers"] = readers
  out["no_gps_m"] = float(re.search(r"self\.distance_traveled > (\d+)", (OP / "selfdrive/selfdrived/selfdrived.py")
                                    .read_text(encoding="utf-8")).group(1))
  return out


ROLE = {
  "openpilot/common/gps.py": "chooses which GPS service the device has",
  "openpilot/selfdrive/selfdrived/selfdrived.py": "the noGps event (no alert); the service is on the ignore lists",
  "openpilot/selfdrive/ui/ui_state.py": "the UI subscribes (shown only)",
  "openpilot/system/hardware/hardwared.py": "copies the last fix into the device's status message (not read by the driving functions)",
  "openpilot/system/qcomgpsd/qcomgpsd.py": "the GPS driver (publishes)",
  "openpilot/system/ubloxd/ubloxd.py": "the GPS driver (publishes)",
}


def run(p: dict) -> dict:
  g = p["gnss_tunnel"]
  c = code()
  v = g["speed_kph"] / 3.6
  readers = [dict(r, role=ROLE.get(r["file"], "not reviewed: a new reader")) for r in c["gps_readers"]]
  return {"about": "Synthetic (DSR-12), design aid, no evidence credit. A reading of openpilot's code, pinned.",
          "pins": c["pins"], "gps_readers": readers, "no_gps_after_m": c["no_gps_m"],
          "no_gps_after_s": round(c["no_gps_m"] / v, 1),
          "tunnels": [{"length_m": L, "seconds": round(L / v, 1), "no_gps_event": L > c["no_gps_m"]} for L in g["tunnel_m"]["value"]],
          "unreviewed_readers": [r["file"] for r in readers if r["role"].startswith("not reviewed")]}


def markdown(r: dict, p: dict) -> str:
  L = [
    "# Losing GPS in a tunnel: what openpilot does with the GPS",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`weather/gnss_tunnel.py`](../weather/gnss_tunnel.py) from openpilot's code, every line it rests on pinned; do not "
    "edit by hand. The GPS half of TC-18; the lighting half is [`tunnel.md`](tunnel.md).",
    "",
    "## What the driving functions read",
    "",
    "| Code | What it shows |",
    "|---|---|",
  ]
  for pin in r["pins"]:
    L.append(f"| `{pin['file']}` | {pin['means']} |")
  L += ["", "## Every reader of the GPS", "", "| File | Service | Role |", "|---|---|---|"]
  for rd in r["gps_readers"]:
    L.append(f"| `{rd['file']}` | {', '.join(rd['services'])} | {rd['role']} |")
  L += ["", "## Through a tunnel at 110 km/h", "", "| Tunnel | Time inside | noGps event |", "|---|---|---|"]
  for t in r["tunnels"]:
    L.append(f"| {t['length_m'] / 1000:g} km | {t['seconds']:.0f} s | "
             + (f"yes, after {r['no_gps_after_m']:.0f} m ({r['no_gps_after_s']:.0f} s), with no alert" if t["no_gps_event"] else "no") + " |")
  L += ["", "## What this shows (generated)", "",
        "- **There is no position to drift.** openpilot's localizer estimates the device's motion from the inertial "
        "sensors and the camera, not a position from the GPS; lateral and longitudinal control use that motion. Losing "
        "the GPS in a tunnel changes nothing they read.",
        f"- **selfdrived notices but does nothing visible:** after {r['no_gps_after_m']:.0f} m without a fix "
        f"({r['no_gps_after_s']:.0f} s at 110 km/h) it raises noGps, which has no alert, and the GPS service is on its "
        "ignore lists, so a lost GPS is never a communication fault.",
        "- **The tunnel's risk is its light, not its GPS:** the road camera's exposure at the portals "
        "([`tunnel.md`](tunnel.md)) is what TC-18 has to validate.",
        ("- No reader of the GPS beyond the reviewed ones." if not r["unreviewed_readers"] else
         "- **New readers not yet reviewed:** " + ", ".join(f"`{x}`" for x in r["unreviewed_readers"]) + "."),
        "- For WP-C-06 TC-18: the GNSS-loss half needs no validation drive of its own; the pins here fail if openpilot "
        "starts using the GPS while engaged.",
        ""]
  return "\n".join(L)


def main(argv):
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("--check", action="store_true")
  a = ap.parse_args(argv[1:])
  p = yaml.safe_load((HERE / "params.yaml").read_text(encoding="utf-8"))
  r = run(p)
  md = markdown(r, p)
  if a.check:
    from sun_glare import compare
    errs = compare(r, json.loads(OUT_JSON.read_text(encoding="utf-8")))
    if not errs and OUT_MD.read_text(encoding="utf-8") != md:
      errs.append(f"{OUT_MD.name} is stale")
    if r["unreviewed_readers"]:
      errs.append(f"new GPS readers to review: {r['unreviewed_readers']}")
    for e in errs[:20]:
      print("FAIL", e)
    print("gnss tunnel:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, indent=1) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name, r["gps_readers"], r["unreviewed_readers"])
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
