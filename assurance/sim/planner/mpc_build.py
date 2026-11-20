#!/usr/bin/env python3
"""Build openpilot's longitudinal MPC outside openpilot (physics plan round 4, phase C; tool TL-67).

openpilot generates its longitudinal planner's solver with acados from `long_mpc.py` and compiles it through SCons.
This does the same without the rest of openpilot:
1. copies `long_mpc.py` unchanged into `build/` (its SHA-256 is recorded and checked);
2. runs it as the generator, with stand-ins for the imports it does not need to solve (cereal's two enums, the logger)
   and the real values of the constants it reads (ACCEL_MIN/MAX, DT_MDL, _LEAD_ACCEL_TAU, index_function), each read
   from its source file;
3. compiles the generated C into the solver library and acados's Cython wrapper, with the flags and include paths of
   openpilot's SConscript.
`load()` then returns openpilot's own `LongitudinalMpc` class, running on that solver.

    python3 mpc_build.py            # about a minute
    python3 mpc_build.py --check    # fails if long_mpc.py or a constant changed since the committed record

Synthetic studies only (DSR-12): the solver is openpilot's, the car and the scenarios are not.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import runpy
import shutil
import subprocess
import sys
import sysconfig
import types
from enum import IntEnum
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BUILD = HERE / "build"
SRC = ROOT / "openpilot" / "selfdrive" / "controls" / "lib" / "longitudinal_mpc_lib" / "long_mpc.py"
RECORD = HERE / "mpc-source.json"
SOURCES = {
  "ACCEL_MIN": (ROOT / "opendbc_repo" / "opendbc" / "car" / "interfaces.py", r"^ACCEL_MIN = (-?[\d.]+)"),
  "ACCEL_MAX": (ROOT / "opendbc_repo" / "opendbc" / "car" / "interfaces.py", r"^ACCEL_MAX = (-?[\d.]+)"),
  "DT_MDL": (ROOT / "openpilot" / "common" / "realtime.py", r"^DT_MDL = ([\d.]+)"),
  "_LEAD_ACCEL_TAU": (ROOT / "openpilot" / "selfdrive" / "controls" / "radard.py", r"^_LEAD_ACCEL_TAU = ([\d.]+)"),
}
CONSTANTS = ROOT / "openpilot" / "selfdrive" / "modeld" / "constants.py"
CEREAL = ROOT / "openpilot" / "cereal" / "log.capnp"


def constants() -> dict:
  out = {}
  for k, (f, pat) in SOURCES.items():
    m = re.search(pat, f.read_text(encoding="utf-8"), re.M)
    if not m:
      raise SystemExit(f"{f.name}: {pat!r} not found; review mpc_build.py")
    out[k] = float(m.group(1))
  return out


def enums() -> dict:
  """The two cereal enums long_mpc.py uses, read from log.capnp."""
  cap = CEREAL.read_text(encoding="utf-8")
  def enum(name):
    m = re.search(rf"enum {name} \{{([^}}]*)\}}", cap)
    if not m:
      raise SystemExit(f"log.capnp: enum {name} not found; review mpc_build.py")
    return {k: int(v) for k, v in re.findall(r"(\w+) @(\d+);", m.group(1))}
  return {"LongitudinalPersonality": enum("LongitudinalPersonality"),
          "LongitudinalPlanSource": enum("LongitudinalPlanSource")}


def sha(p: Path) -> str:
  return hashlib.sha256(p.read_bytes()).hexdigest()


def _module(name: str, **attrs) -> types.ModuleType:
  m = types.ModuleType(name)
  m.__dict__.update(attrs)
  sys.modules[name] = m
  return m


def install_stand_ins() -> None:
  """Modules long_mpc.py imports, with the real values it reads and stand-ins for what it only logs."""
  c, e = constants(), enums()
  for pkg in ("openpilot", "openpilot.cereal", "openpilot.common", "openpilot.selfdrive", "openpilot.selfdrive.modeld",
              "openpilot.selfdrive.controls", "openpilot.selfdrive.controls.lib",
              "openpilot.selfdrive.controls.lib.longitudinal_mpc_lib", "opendbc", "opendbc.car"):
    if pkg not in sys.modules:
      _module(pkg, __path__=[])
  personality = IntEnum("LongitudinalPersonality", e["LongitudinalPersonality"])
  source = IntEnum("LongitudinalPlanSource", e["LongitudinalPlanSource"])
  log = types.SimpleNamespace(LongitudinalPersonality=personality,
                              LongitudinalPlan=types.SimpleNamespace(LongitudinalPlanSource=source))
  sys.modules["openpilot.cereal"].log = log
  _module("opendbc.car.interfaces", ACCEL_MIN=c["ACCEL_MIN"], ACCEL_MAX=c["ACCEL_MAX"])
  _module("openpilot.common.realtime", DT_MDL=c["DT_MDL"])
  _module("openpilot.common.swaglog", cloudlog=types.SimpleNamespace(warning=lambda *a, **k: None,
                                                                     error=lambda *a, **k: None))
  spec = importlib.util.spec_from_file_location("openpilot.selfdrive.modeld.constants", CONSTANTS)
  mod = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(mod)
  sys.modules["openpilot.selfdrive.modeld.constants"] = mod
  _module("openpilot.selfdrive.controls.radard", _LEAD_ACCEL_TAU=c["_LEAD_ACCEL_TAU"])


def build() -> None:
  import acados
  import numpy as np
  os.environ.update({"ACADOS_SOURCE_DIR": acados.DIR, "ACADOS_PYTHON_INTERFACE_PATH": acados.TEMPLATE_DIR,
                     "TERA_PATH": acados.TERA_PATH})                    # as openpilot's SConstruct sets them
  if BUILD.exists():
    shutil.rmtree(BUILD)
  BUILD.mkdir()
  shutil.copy2(SRC, BUILD / "long_mpc.py")
  install_stand_ins()
  cwd = os.getcwd()
  os.chdir(BUILD)
  try:
    runpy.run_path(str(BUILD / "long_mpc.py"), run_name="__main__")      # generates c_generated_code/ and the JSON
  finally:
    os.chdir(cwd)
  gen = BUILD / "c_generated_code"
  inc = [acados.INCLUDE_DIR, os.path.join(acados.INCLUDE_DIR, "blasfeo", "include"),
         os.path.join(acados.INCLUDE_DIR, "hpipm", "include")]
  files = ["acados_solver_long.c", "long_model/long_expl_ode_fun.c", "long_model/long_expl_vde_forw.c"]
  files += [f"long_cost/long_cost_{k}_{s}.c" for k in ("y", "y_e", "y_0") for s in ("fun", "fun_jac_ut_xt", "hess")]
  files += ["long_constraints/long_constr_h_fun.c", "long_constraints/long_constr_h_fun_jac_uxt_zt.c"]
  for lib in ("libacados.so", "libblasfeo.so", "libhpipm.so", "libqpOASES_e.so.3.1"):
    shutil.copy2(os.path.join(acados.LIB_DIR, lib), gen / lib)
  cc = ["cc", "-O2", "-fPIC", "-DACADOS_WITH_QPOASES", "-Wno-unused"] + [f"-I{d}" for d in inc] + [f"-I{gen}"]
  subprocess.run(cc + ["-shared", "-o", str(gen / "libacados_ocp_solver_long.so")] + [str(gen / f) for f in files]
                 + [f"-L{gen}", "-lacados", "-lhpipm", "-lblasfeo", "-l:libqpOASES_e.so.3.1", "-lm", "-Wl,-rpath,$ORIGIN",
                    "-Wl,--disable-new-dtags"], check=True)
  tpl = Path(acados.TEMPLATE_DIR)
  pyx_c = gen / "acados_ocp_solver_pyx.c"
  subprocess.run([sys.executable, "-m", "cython", "-o", str(pyx_c), "-I", str(gen), "-I", str(tpl),
                  str(tpl / "acados_ocp_solver_pyx.pyx")], check=True)
  ext = sysconfig.get_config_var("EXT_SUFFIX")
  subprocess.run(cc + ["-Wno-cpp", "-Wno-deprecated-declarations", f"-I{sysconfig.get_paths()['include']}",
                       f"-I{np.get_include()}", "-shared", "-pthread", "-o", str(gen / f"acados_ocp_solver_pyx{ext}"),
                       str(pyx_c), f"-L{gen}", "-lacados_ocp_solver_long", "-Wl,-rpath,$ORIGIN"], check=True)


def load():
  """openpilot's LongitudinalMpc, on the solver built here, and the long_mpc module itself."""
  if not (BUILD / "c_generated_code").exists():
    build()
  install_stand_ins()
  ext = sysconfig.get_config_var("EXT_SUFFIX")
  name = "openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.c_generated_code.acados_ocp_solver_pyx"
  _module("openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.c_generated_code", __path__=[])
  spec = importlib.util.spec_from_file_location(name, BUILD / "c_generated_code" / f"acados_ocp_solver_pyx{ext}")
  pyx = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(pyx)
  sys.modules[name] = pyx
  spec = importlib.util.spec_from_file_location("long_mpc_built", BUILD / "long_mpc.py")
  lm = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(lm)
  if sha(BUILD / "long_mpc.py") != sha(SRC):
    raise SystemExit("build/long_mpc.py differs from openpilot's; rebuild")
  return lm


def record() -> dict:
  import acados
  return {"long_mpc_sha256": sha(SRC), "constants": constants(), "enums": enums(),
          "acados_package": "comma-deps-acados", "acados_template": Path(acados.TEMPLATE_DIR).name}


def main(argv):
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("--check", action="store_true")
  a = ap.parse_args(argv[1:])
  if a.check:
    old = json.loads(RECORD.read_text(encoding="utf-8"))
    new = record()
    if old != new:
      print("FAIL long_mpc.py or a constant it reads changed; review the planner studies, then rebuild and re-record")
      print(json.dumps({k: (old.get(k), new.get(k)) for k in new if old.get(k) != new.get(k)}, indent=1))
      return 1
    print("mpc build: OK (long_mpc.py and its constants as recorded)")
    return 0
  build()
  RECORD.write_text(json.dumps(record(), indent=1) + "\n", encoding="utf-8")
  print("built", BUILD / "c_generated_code")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
