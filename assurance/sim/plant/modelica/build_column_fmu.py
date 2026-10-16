#!/usr/bin/env python3
"""Export the L2 steering column (SteeringColumn.mo) as an FMI 2.0 co-simulation FMU with OpenModelica (TL-44).

    python3 assurance/sim/plant/modelica/build_column_fmu.py [OUT_DIR]     # prints the FMU path

`omc` comes from the explicit conda lock omc-linux-64.lock (OpenModelica 1.27.1 from conda-forge, every package
pinned by URL and md5), or from $OMC. The FMU is a build product and is not committed.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = HERE / "SteeringColumn.mo"
OMC_VERSION = "1.27.1"
BUILD = HERE.parents[3] / "build" / "sim-column"


def omc() -> str:
  exe = os.environ.get("OMC") or shutil.which("omc")
  if not exe:
    raise SystemExit("omc not found: create the environment from omc-linux-64.lock (README §3.5) or set $OMC")
  version = subprocess.run([exe, "--version"], capture_output=True, text=True, check=True).stdout.strip()
  if OMC_VERSION not in version:
    raise SystemExit(f"omc {version} found, {OMC_VERSION} required (TL-44)")
  return exe


def build(out_dir: Path = BUILD) -> Path:
  out_dir.mkdir(parents=True, exist_ok=True)
  with tempfile.TemporaryDirectory() as tmp:
    script = Path(tmp) / "build.mos"
    # CVODE inside the FMU (the default is forward Euler at the communication step, ≈ 0.4 % error at 1 ms)
    script.write_text('setCommandLineOptions("--fmiFlags=s:cvode"); getErrorString();\n'
                      f'loadFile("{MODEL}"); getErrorString();\n'
                      'buildModelFMU(SteeringColumn, version="2.0", fmuType="cs", platforms={"static"}); '
                      'getErrorString();\n', encoding="utf-8")
    exe = omc()
    # the export compiles the FMU with the environment's own C toolchain, found next to omc
    env = {**os.environ, "PATH": f"{Path(exe).parent}{os.pathsep}{os.environ.get('PATH', '')}"}
    run = subprocess.run([exe, str(script)], cwd=tmp, capture_output=True, text=True, timeout=600, env=env)
    fmu = Path(tmp) / "SteeringColumn.fmu"
    if run.returncode or not fmu.exists() or "Error" in run.stdout:
      raise SystemExit(f"FMU export failed:\n{run.stdout}\n{run.stderr}")
    shutil.copy(fmu, out_dir / fmu.name)
  return out_dir / "SteeringColumn.fmu"


if __name__ == "__main__":
  print(build(Path(sys.argv[1]) if len(sys.argv) > 1 else BUILD))
