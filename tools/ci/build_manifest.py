#!/usr/bin/env python3
"""Write the build manifest of a CI run (WP-W-01 ENV-01, WP-M-14 §8.3).

Records the superproject commit, every submodule commit, the build flags that select the
configuration (RELEASE, LIONDRIVER_REFERENCE), the CI run, and the version of each tool found on
PATH. Prints the manifest to the job log and writes it as JSON for upload as a CI artifact.

A tool that is not on PATH is recorded as "not on PATH": a job that installs a tool into its own
environment (for example cppcheck inside test_misra.sh) logs that version itself.

Usage: python3 tools/ci/build_manifest.py <output.json>
Standard library only.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOLS = ["cc", "gcc", "clang", "arm-none-eabi-gcc", "cppcheck", "python3", "scons", "uv", "git"]
FLAGS = ["RELEASE", "LIONDRIVER_REFERENCE"]


def run(cmd: list[str]) -> str:
  try:
    out = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=30, check=False)
  except (OSError, subprocess.TimeoutExpired) as e:
    return f"error: {e}"
  if out.returncode != 0:
    lines = (out.stderr or out.stdout).strip().splitlines()
    return f"error: exit {out.returncode}: {lines[0] if lines else ''}"
  return (out.stdout or out.stderr).strip()


def tool_version(name: str) -> str:
  if shutil.which(name) is None:
    return "not on PATH"
  lines = run([name, "--version"]).splitlines()
  return lines[0] if lines else "no version output"


def submodules() -> dict[str, str]:
  status = run(["git", "submodule", "status"])
  if status.startswith("error: "):
    return {"(error)": status}  # never parse an error message as submodule lines
  out: dict[str, str] = {}
  for line in status.splitlines():
    parts = line.strip().lstrip("-+U").split()
    if len(parts) >= 2:
      state = {"-": "not checked out", "+": "differs from pin", "U": "conflict"}.get(line[:1], "at pin")
      out[parts[1]] = f"{parts[0]} ({state})"
  return out


def manifest() -> dict:
  env = os.environ
  return {
    "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "superproject": env.get("GITHUB_SHA") or run(["git", "rev-parse", "HEAD"]),
    "ref": env.get("GITHUB_REF", ""),
    "ci_run": {k: env.get(k, "") for k in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_WORKFLOW", "GITHUB_JOB")},
    "runner": {k: env.get(k, "") for k in ("RUNNER_OS", "RUNNER_ARCH", "ImageOS", "ImageVersion")},
    "submodules": submodules(),
    "flags": {k: env.get(k, "") for k in FLAGS},
    "tools": {t: tool_version(t) for t in TOOLS},
  }


def main(argv: list[str]) -> int:
  if len(argv) != 2:
    print(__doc__)
    return 2
  m = manifest()
  text = json.dumps(m, indent=2, sort_keys=True)
  print(text)
  out = Path(argv[1])
  out.parent.mkdir(parents=True, exist_ok=True)
  out.write_text(text + "\n", encoding="utf-8")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
