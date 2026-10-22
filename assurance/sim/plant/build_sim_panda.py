"""Prebuild the plant's panda safety library (sim_panda.c) for a machine with no C compiler at run time.

panda_loop.py compiles sim_panda.c on each run with the system `cc`. A machine without a compiler (a packaged
Windows build, say) instead takes the two libraries this script writes, the reference build and the plain one, with
LIONDRIVER_SIM_PANDA_DIR set to their folder. The compiler call is panda_loop.compile_command, the same flags as the
run-time build (less -fPIC for Windows).

  python3 assurance/sim/plant/build_sim_panda.py --out build/sim-panda                    # this machine
  python3 assurance/sim/plant/build_sim_panda.py --out build/sim-panda --cc gcc --windows  # on Windows (MinGW)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import panda_loop


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--out", type=Path, required=True)
  ap.add_argument("--cc", default="cc", help="the C compiler (Windows: MinGW-w64 gcc)")
  ap.add_argument("--windows", action="store_true", help="build .dll files for Windows")
  args = ap.parse_args(argv)
  args.out.mkdir(parents=True, exist_ok=True)
  suffix = ".dll" if args.windows else ".so"
  for reference in (True, False):
    out = args.out / (panda_loop.prebuilt_name(reference).rsplit(".", 1)[0] + suffix)
    subprocess.check_call(panda_loop.compile_command(reference, str(out), args.cc, args.windows))
    print(out)
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
