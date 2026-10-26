#!/usr/bin/env python3
import os
import re
import subprocess
import sys

HERE = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../.."))

blacklist = [
  ".git/",
  ".venv/",
  ".github/workflows/",

  "matlab.*.md",

  # release scripts configure LFS for the big driving model and warps
  ".lfsconfig",
  ".gitattributes",
  ".git$",
  ".gitmodules",
]

# gets you through the blacklist
whitelist: list[str] = [r"^\.lfsconfig$"] if os.getenv("INCLUDE_BIG_MODEL") else []

# LionDriver DQ-131 (FM-06, TSR-806, CSG-03): the reference variant (RELEASE_VARIANT, release_variant.sh; reference
# when unset) ships without the joystick and maneuver processes. The manager does not register them in a reference
# build either (system/manager/process_config.py REFERENCE_EXCLUDED_PROCS). joystickd stays: it serves notCar only.
reference_excluded = [
  r"^openpilot/tools/joystick/joystick_control\.py$",
  r"^openpilot/tools/longitudinal_maneuvers/",
  r"^openpilot/tools/lateral_maneuvers/",
]


def released(rf: str, variant: str) -> bool:
  if not os.getenv("INCLUDE_BIG_MODEL") and rf.startswith("openpilot/selfdrive/modeld/models/big_"):
    return False
  if variant == "reference" and any(re.search(p, rf) for p in reference_excluded):
    return False
  blacklisted = any(re.search(p, rf) for p in blacklist)
  whitelisted = any(re.search(p, rf) for p in whitelist)
  return not blacklisted or whitelisted


if __name__ == "__main__":
  variant = os.getenv("RELEASE_VARIANT") or "reference"
  tracked_files = subprocess.check_output(["git", "ls-files", "-z", "--recurse-submodules"], cwd=ROOT).split(b"\0")
  for tracked_file in tracked_files:
    if not tracked_file:
      continue

    if not released(os.fsdecode(tracked_file), variant):
      continue

    sys.stdout.buffer.write(tracked_file + b"\0")
