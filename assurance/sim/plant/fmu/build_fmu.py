#!/usr/bin/env python3
"""Build the L1 plant FMU: python3 build_fmu.py <out_dir>. The parameters are frozen into resources/parameters.json
from the opendbc sources at build time, so the FMU does not need the repository to run (it needs the packages of
../../requirements.txt in the Python that runs it). The FMU is a build product: it is not committed."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLANT = HERE.parent
sys.path.insert(0, str(PLANT))
import corolla  # noqa: E402


def build(out_dir: Path) -> Path:
  out_dir.mkdir(parents=True, exist_ok=True)
  with tempfile.TemporaryDirectory() as tmp:
    params = Path(tmp) / "parameters.json"
    params.write_text(json.dumps(corolla.as_dict(), sort_keys=True, indent=1))
    project = [str(PLANT / "plant.py"), str(PLANT / "corolla.py"), str(params)]
    subprocess.check_call([sys.executable, "-m", "pythonfmu", "build", "-f", str(HERE / "corolla_plant_fmu.py"),
                           "-d", str(out_dir), *project], env={**os.environ, "PYTHONPATH": str(PLANT)})
  return out_dir / "CorollaPlantFMU.fmu"


if __name__ == "__main__":
  print(build(Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp())))
