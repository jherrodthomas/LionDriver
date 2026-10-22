"""The plant's fingerprint on every gallery scene, to check one machine against another (windows-build-plan.md §3).

Hazard Scene Studio on Windows runs the plant with the panda safety code prebuilt for Windows. This script exports
every scene of ../blender/scenes.yaml with its variants (export_scene.py, the plant or the stated kinematic motion)
and writes what the analysis rests on: the frame count, the events, the contact, the critical road user, and the
ego and critical poses, speed, lateral offset, gap and TTC every sixth frame. `compare` checks two fingerprints
value by value: the same labels and counts, every number within 1e-6 (m, s, m/s). CI writes one on Linux and one on
Windows from the same commit and compares them; a difference stops the build.

  python3 assurance/sim/render-tool/plant_fingerprint.py write linux.json
  python3 assurance/sim/render-tool/plant_fingerprint.py compare linux.json windows.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import row_to_scene as rs  # puts ../blender on the path
import export_scene as ex  # noqa: E402

EVERY = 6          # frames between samples
TOL = 1e-6


def fingerprint() -> dict:
  hes, lib = ex.hazardous_events(), ex.load_library()
  out = {}
  for sc in ex.load_scenes():
    d = ex.build(sc, hes, lib)
    crit = next((a for a in d["actors"] if a["name"] == d["critical"]), None)
    pick = lambda xs: None if xs is None else xs[::EVERY]
    out[sc["id"]] = {
      "frames": len(d["t"]), "events": [[e["t"], e["label"]] for e in d["events"]], "contact": d["contact"],
      "critical": d["critical"], "speed": pick(d["speed"]), "lateral": pick(d["lateral"]), "gap": pick(d["gap"]),
      "ttc": pick(d["ttc"]), "ego": pick(d["actors"][0]["poses"]), "crit": pick(crit["poses"]) if crit else None}
  return out


def differences(a, b, path: str = "") -> list[str]:
  """Where two fingerprints differ beyond TOL (labels, counts and None exactly)."""
  if isinstance(a, dict) and isinstance(b, dict):
    if a.keys() != b.keys():
      return [f"{path}: keys {sorted(a.keys() ^ b.keys())}"]
    return [x for k in a for x in differences(a[k], b[k], f"{path}/{k}")]
  if isinstance(a, list) and isinstance(b, list):
    if len(a) != len(b):
      return [f"{path}: {len(a)} against {len(b)} items"]
    return [x for i, (p, q) in enumerate(zip(a, b)) for x in differences(p, q, f"{path}[{i}]")]
  if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
    return [] if math.isclose(a, b, rel_tol=0, abs_tol=TOL) else [f"{path}: {a!r} against {b!r}"]
  return [] if a == b else [f"{path}: {a!r} against {b!r}"]


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  sub = ap.add_subparsers(dest="cmd", required=True)
  w = sub.add_parser("write")
  w.add_argument("out", type=Path)
  c = sub.add_parser("compare")
  c.add_argument("a", type=Path)
  c.add_argument("b", type=Path)
  args = ap.parse_args(argv)
  if args.cmd == "write":
    fp = fingerprint()
    args.out.write_text(json.dumps(fp))
    print(f"{args.out}: {len(fp)} scenes")
    return 0
  diff = differences(json.loads(args.a.read_text()), json.loads(args.b.read_text()))
  for line in diff[:40]:
    print(line, file=sys.stderr)
  if diff:
    print(f"{len(diff)} differences between {args.a} and {args.b}", file=sys.stderr)
    return 1
  print(f"{args.a} and {args.b} agree on every scene (tolerance {TOL:g})")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
