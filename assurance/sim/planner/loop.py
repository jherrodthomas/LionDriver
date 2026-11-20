"""openpilot's longitudinal planner in a closed loop with a point-mass car and scripted leads (round 4 phase C).

Each 0.05 s step does what `longitudinal_planner.py` does with a lead: the MPC (`long_mpc.py`, built by mpc_build.py)
from the car's speed and last target, the plan resampled on CONTROL_N_T_IDX, the target from `get_accel_from_plan`
(executed from drive_helpers.py's own source) at the actuator delay, the lower of that and the cruise target, clipped to
ACCEL_MIN/ACCEL_MAX. The car follows the target after the Corolla's `longitudinalActuatorDelay` (opendbc), with no
other dynamics: the friction to brake at −3.5 m/s² is there in the dry (the wet-braking study). FCW is the planner's
rule, `crash_cnt > 2`.
"""

from __future__ import annotations

import ast
import re
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mpc_build  # noqa: E402

ROOT = mpc_build.ROOT
HELPERS = ROOT / "openpilot" / "selfdrive" / "controls" / "lib" / "drive_helpers.py"
PLANNER = ROOT / "openpilot" / "selfdrive" / "controls" / "lib" / "longitudinal_planner.py"
TOYOTA = ROOT / "opendbc_repo" / "opendbc" / "car" / "interfaces.py"
LM = mpc_build.load()
DT = LM.DT_MDL


def _helpers() -> dict:
  src = HELPERS.read_text(encoding="utf-8")
  ns = {"np": np, "DT_MDL": DT}
  ns["MIN_STABLE_DELAY"] = float(re.search(r"^MIN_STABLE_DELAY = ([\d.]+)", src, re.M).group(1))
  ns["CONTROL_N"] = int(re.search(r"^CONTROL_N = (\d+)", src, re.M).group(1))
  tree = ast.parse(src)
  fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_accel_from_plan")
  exec(compile(ast.Module(body=[fn], type_ignores=[]), str(HELPERS), "exec"), ns)
  p = PLANNER.read_text(encoding="utf-8")
  for pat in (r"self\.fcw = self\.mpc\.crash_cnt > 2 and not sm\['carState'\]\.standstill",
              r"action_t =  self\.CP\.longitudinalActuatorDelay \+ DT_MDL",
              r"self\.a_desired_trajectory = np\.interp\(CONTROL_N_T_IDX, T_IDXS_MPC, self\.mpc\.a_solution\)"):
    if not re.search(pat, p):
      raise SystemExit(f"longitudinal_planner.py changed: {pat!r}; review loop.py")
  ns["A_CRUISE_MIN"] = float(re.search(r"^A_CRUISE_MIN = (-?[\d.]+)", p, re.M).group(1))
  ns["actuator_delay"] = float(re.search(r"ret\.longitudinalActuatorDelay = ([\d.]+)", TOYOTA.read_text(encoding="utf-8")).group(1))
  return ns


H = _helpers()
CONTROL_N_T_IDX = sys.modules["openpilot.selfdrive.modeld.constants"].ModelConstants.T_IDXS[:H["CONTROL_N"]]
PERSONALITY = LM.log.LongitudinalPersonality


@dataclass
class Lead:
  present: bool = False
  dRel: float = 0.0
  vLead: float = 0.0
  aLeadK: float = 0.0
  aLeadTau: float = mpc_build.constants()["_LEAD_ACCEL_TAU"]
  modelProb: float = 1.0


@dataclass
class Result:
  t: list = field(default_factory=list)
  gap: list = field(default_factory=list)
  v: list = field(default_factory=list)
  a: list = field(default_factory=list)
  a_cmd: list = field(default_factory=list)
  fcw_t: float | None = None
  impact_v: float | None = None


def run(v0: float, lead_fn, duration: float, personality=PERSONALITY.standard, v_cruise: float | None = None,
        delay: float | None = None, driver=None) -> Result:
  """lead_fn(t, x_ego) -> (visible, x_lead, v_lead, a_lead) with x along the lane; driver(t, fcw_t) -> decel or None."""
  delay = H["actuator_delay"] if delay is None else delay
  v_cruise = v0 if v_cruise is None else v_cruise
  mpc = LM.LongitudinalMpc()
  mpc.set_weights(personality=personality)
  x, v, a = 0.0, v0, 0.0
  a_target = 0.0
  q = [0.0] * max(1, int(round(delay / DT)))
  r = Result()
  for k in range(int(round(duration / DT))):
    t = k * DT
    vis, xl, vl, al = lead_fn(t, x)
    gap = xl - x - 4.5 if xl is not None else None           # bumper to bumper, a 4.5 m car
    lead = Lead(present=bool(vis), dRel=max(gap, 0.0) if gap is not None else 0.0, vLead=vl or 0.0, aLeadK=al or 0.0)
    rs = types.SimpleNamespace(leadOne=lead, leadTwo=Lead())
    mpc.set_cur_state(v, a_target)
    mpc.update(rs, personality=personality)
    a_traj = np.interp(CONTROL_N_T_IDX, LM.T_IDXS, mpc.a_solution)
    v_traj = np.interp(CONTROL_N_T_IDX, LM.T_IDXS, mpc.v_solution)
    a_mpc = H["get_accel_from_plan"](v_traj, a_traj, CONTROL_N_T_IDX, action_t=delay + DT)
    a_cruise = float(np.clip(v_cruise - v, H["A_CRUISE_MIN"], LM.ACCEL_MAX))
    a_target = float(np.clip(min(a_mpc, a_cruise), LM.ACCEL_MIN, LM.ACCEL_MAX))
    if mpc.crash_cnt > 2 and r.fcw_t is None and v > 0.1:
      r.fcw_t = t
    q.append(a_target)
    a = q.pop(0)
    if driver is not None:
      d = driver(t, r.fcw_t)
      if d is not None:
        a = min(a, -d)
    v_new = max(v + a * DT, 0.0)
    x += (v + v_new) / 2 * DT
    v = v_new
    r.t.append(round(t, 3)); r.gap.append(gap); r.v.append(v); r.a.append(a); r.a_cmd.append(a_target)
    if gap is not None and xl - x - 4.5 <= 0 and r.impact_v is None:
      r.impact_v = v - (vl or 0.0)
      break
  return r
