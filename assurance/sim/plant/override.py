#!/usr/bin/env python3
"""Driver override against LKA torque on the L2 steering column (SG-05, TSR-304; roadmap S3).

    python3 assurance/sim/plant/override.py --fmu PATH            # run the sweep, write ../results/override-l2.md
    python3 assurance/sim/plant/override.py --fmu PATH --check    # fail if the committed table differs

The column is the OpenModelica FMU built from modelica/SteeringColumn.mo (build_column_fmu.py), run through FMPy.
Around it: the panda reference build (real safety code, as in the L1 plant), the Toyota car controller's own torque
rule (`lat_active` drops when |STEER_TORQUE_DRIVER| reaches MAX_USER_TORQUE, real opendbc constants) and a driver who
ramps torque against a held LKA command. Every column parameter and both CAN torque scales are assumptions (M-02):
the scales are swept, nothing here is measured, and the results earn no credit (WP-V-02 §5.3).
"""

from __future__ import annotations

import itertools
import math
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import corolla  # noqa: E402
from corolla import ROOT  # noqa: E402
from panda_loop import Panda  # noqa: E402
from report import submodule_commit  # noqa: E402
from simulate import DT_US, EPS_SCALE, LIMITS, SoC, _decode_steer  # noqa: E402

sys.path.insert(0, str(ROOT / "opendbc_repo"))
from opendbc.car.lateral import apply_meas_steer_torque_limits  # noqa: E402
from opendbc.car.toyota import toyotacan  # noqa: E402
from opendbc.car.toyota.carcontroller import MAX_USER_TORQUE  # noqa: E402
from opendbc.car.toyota.values import STEER_THRESHOLD  # noqa: E402

TABLE = HERE.parent / "results" / "override-l2.md"
STEER_MAX = 1500
SPEED_KPH = 110.0          # ODD-H bound (DQ-260)
T_DRIVER = 2.0             # s: driver input starts (the LKA command ramps up from 0.3 s and is held from about 1.3 s)
DURATION = 1.5             # s after the driver input
SG05_S = 0.2               # s: SG-05 / TSR-304 back-off budget from the driver's input

# Column parameters (SteeringColumn.mo). All assumed; ranges from published column-EPS models are to be checked
# against the sources once they can be read (README §6) and replaced by measurement (M-02).
COLUMN = {
  "J_sw": (0.04, "kg·m²", "steering wheel and upper column inertia"),
  "c_sw": (0.2, "N·m·s/rad", "steering wheel damping"),
  "k_tb": (130.0, "N·m/rad", "torsion bar stiffness"),
  "c_tb": (0.1, "N·m·s/rad", "torsion bar damping"),
  "J_l": (0.2, "kg·m²", "lower column, reflected motor and rack inertia"),
  "c_l": (1.0, "N·m·s/rad", "lower column and rack damping"),
  "tau_m": (corolla.as_dict()["tau_eps"], "s", "motor torque lag = the L1 EPS lag (steerActuatorDelay)"),
}

# Swept assumptions: what 1500 LKA units and 500 driver-torque units are in N·m at the column
LKA_FULL_NM = (1.5, 3.0)            # N·m at the column for STEER_MAX
HOST_THRESHOLD_NM = (2.0, 3.5, 5.0)  # N·m at the wheel for MAX_USER_TORQUE (500 units)
DRIVER_PEAK_NM = (3.0, 5.0, 8.0)    # N·m the driver applies
DRIVER_RISE_S = (0.1, 0.3)          # s to reach it (linear ramp)


@dataclass
class Run:
  lka_nm: float
  host_nm: float
  peak_nm: float
  rise_s: float
  t_steering_pressed: float | None = None   # |driver units| > STEER_THRESHOLD seen by the host
  t_host_drop: float | None = None          # host sets lat_active False (MAX_USER_TORQUE)
  t_zero_frame: float | None = None         # first zero-torque frame the panda passes to the car
  t_motor_5: float | None = None            # motor torque below 5 % of the held value
  sw_deg_at_5: float | None = None          # steering wheel angle when the motor is below 5 %
  panda_refused: int = 0


def k_rack(lka_nm: float) -> float:
  """Rack stiffness at the column that gives the L1 steady state: full LKA torque -> LAT_ACCEL_FACTOR at SPEED_KPH."""
  d = corolla.as_dict()
  v = SPEED_KPH / 3.6
  # neutral steer (L1): a_y = v² δ / L with δ = θ_pinion / steer_ratio
  delta = d["lat_accel_factor"] * d["L"] / (v * v)
  return lka_nm / (delta * d["steer_ratio"])


class Column:
  """The FMU through FMPy, co-simulated at 1 ms."""

  def __init__(self, fmu: str):
    from fmpy import extract, read_model_description
    from fmpy.fmi2 import FMU2Slave
    md = read_model_description(fmu)
    self.vr = {v.name: v.valueReference for v in md.modelVariables}
    self.unzip = extract(fmu)
    self.fmu = FMU2Slave(guid=md.guid, unzipDirectory=self.unzip, modelIdentifier=md.coSimulation.modelIdentifier,
                         instanceName="column")
    self.fmu.instantiate()

  def start(self, params: dict):
    f = self.fmu
    f.reset()
    f.setupExperiment(startTime=0.0)
    f.enterInitializationMode()
    f.setReal([self.vr[k] for k in params], list(params.values()))
    f.setReal([self.vr["T_d"], self.vr["T_cmd"]], [0.0, 0.0])
    f.exitInitializationMode()
    self.t = 0.0

  def step(self, t_d: float, t_cmd: float, dt: float):
    self.fmu.setReal([self.vr["T_d"], self.vr["T_cmd"]], [t_d, t_cmd])
    self.fmu.doStep(currentCommunicationPoint=self.t, communicationStepSize=dt)
    self.t += dt
    return dict(zip(("T_tb", "th_sw", "T_m"), self.fmu.getReal([self.vr["T_tb"], self.vr["th_sw"], self.vr["T_m"]]),
                    strict=True))


def run_one(col: Column, lka_nm: float, host_nm: float, peak_nm: float, rise_s: float) -> Run:
  r = Run(lka_nm, host_nm, peak_nm, rise_s)
  params = {k: v[0] for k, v in COLUMN.items()} | {"k_r": k_rack(lka_nm), "T_m_max": lka_nm}
  col.start(params)
  d = corolla.as_dict()
  panda = Panda(reference=True)
  soc = SoC(d, panda.packer)
  last_torque = 0
  nm_per_drv_unit = host_nm / MAX_USER_TORQUE
  nm_per_lka_unit = lka_nm / STEER_MAX
  v = SPEED_KPH / 3.6
  t_cmd_nm, drv_units, motor_units, held = 0.0, 0, 0.0, None
  lat_active, cruise = True, False
  out = {"T_tb": 0.0, "th_sw": 0.0, "T_m": 0.0}
  n = int((T_DRIVER + DURATION) * 1e6 / DT_US)
  for k in range(n + 1):
    t_us = k * DT_US
    t = t_us / 1e6
    panda.set_time(t_us)
    if t >= 0.2:
      cruise = True
    # car bus -> panda: the reading of the column's torque sensor and motor torque (Toyota carstate scales)
    if k % 20 == 2:
      drv_units = int(round(out["T_tb"] / nm_per_drv_unit))
      motor_units = out["T_m"] / nm_per_lka_unit
      panda.rx("STEER_TORQUE_SENSOR", {"STEER_TORQUE_EPS": motor_units / EPS_SCALE * 100.0,
                                       "STEER_TORQUE_DRIVER": drv_units, "STEER_ANGLE": 0.0})
    if k % 12 == 1:
      panda.rx("WHEEL_SPEEDS", {f"WHEEL_SPEED_{w}": v * 3.6 for w in ("FR", "FL", "RR", "RL")})
    if k % 30 == 4:
      panda.rx("PCM_CRUISE", {"CRUISE_ACTIVE": int(cruise), "GAS_RELEASED": 1})
      panda.rx("PCM_CRUISE_2", {"MAIN_ON": 1})
    if k % 25 == 7:
      panda.rx("BRAKE_MODULE", {"BRAKE_PRESSED": 0})
    if k % 40 == 9:
      panda.rx("EPS_STATUS", {"LKA_STATE": 5})
    # host, 100 Hz: the car controller's rule (carcontroller.py: lat_active and |steeringTorque| < MAX_USER_TORQUE)
    if k % 10 == 0:
      frame = k // 10
      engaged = t >= 0.2
      if r.t_steering_pressed is None and t >= T_DRIVER and abs(drv_units) > STEER_THRESHOLD:
        r.t_steering_pressed = t - T_DRIVER
      if lat_active and abs(drv_units) >= MAX_USER_TORQUE:
        lat_active = False
        r.t_host_drop = t - T_DRIVER
      want = -STEER_MAX if (engaged and t >= 0.3) else 0     # held LKA command, opposing the driver
      # carcontroller.py: host rate limits against the measured motor torque, then zero when not lat_active
      torque = apply_meas_steer_torque_limits(want, last_torque, motor_units, LIMITS) if engaged else 0
      if not lat_active:
        torque = 0
      last_torque = torque
      req = int(lat_active and engaged and t >= 0.3)
      addr, dat, bus = toyotacan.create_steer_command(panda.packer, torque, req)
      if panda.tx(addr, dat, bus):
        torque_sent, _ = _decode_steer(panda, dat)
        t_cmd_nm = torque_sent * nm_per_lka_unit
        if not lat_active and r.t_zero_frame is None and torque_sent == 0:
          r.t_zero_frame = t - T_DRIVER
      elif req or torque:
        r.panda_refused += 1
        t_cmd_nm = 0.0                       # a refused frame does not reach the EPS
      if frame % 3 == 0:
        addr, dat, bus = soc.accel_frame(engaged)
        panda.tx(addr, dat, bus)
      if frame % 10 == 0:
        panda.heartbeat(engaged)
    panda.main_loop()
    if k % 10 == 3:
      panda.safety_task()
    # driver: torque ramp against the LKA command from T_DRIVER
    t_d = peak_nm * min(max(t - T_DRIVER, 0.0) / rise_s, 1.0)
    out = col.step(t_d, t_cmd_nm, DT_US / 1e6)
    if t < T_DRIVER:
      held = out["T_m"]
    elif r.t_motor_5 is None and held and abs(out["T_m"]) < 0.05 * abs(held):
      r.t_motor_5 = t - T_DRIVER
      r.sw_deg_at_5 = math.degrees(out["th_sw"])
  return r


@contextmanager
def quiet_stdout():
  """The OpenModelica runtime writes its solver log to the C-level stdout on every reset; keep it out of the output."""
  sys.stdout.flush()
  saved, devnull = os.dup(1), os.open(os.devnull, os.O_WRONLY)
  os.dup2(devnull, 1)
  try:
    yield
  finally:
    os.dup2(saved, 1)
    os.close(saved)
    os.close(devnull)


def sweep(fmu: str) -> list[Run]:
  with quiet_stdout():
    col = Column(fmu)
    return [run_one(col, *p) for p in itertools.product(LKA_FULL_NM, HOST_THRESHOLD_NM, DRIVER_PEAK_NM, DRIVER_RISE_S)]


def _s(x):
  return "never" if x is None else f"{x:.3f}"


def table(runs: list[Run]) -> str:
  head = [
    "# Driver override against LKA torque (L2 steering column)",
    "",
    "> **Synthetic data (DSR-12).** Generated by [`plant/override.py`](../plant/override.py); do not edit by hand. "
    "Column: OpenModelica FMU of [`modelica/SteeringColumn.mo`](../plant/modelica/SteeringColumn.mo) (fidelity L2, "
    "tool TL-44). Panda: real safety code, reference build. Host: the Toyota car controller's override rule "
    f"(`MAX_USER_TORQUE` = {MAX_USER_TORQUE} units). **Every column parameter and both CAN torque scales are "
    "assumptions** (M-02), swept where they decide the result. **No evidence credit** (WP-V-02 §5.3).",
    "",
    f"LKA holds full torque ({STEER_MAX} units) to the right from 0.3 s; from t = {T_DRIVER:g} s the driver ramps "
    f"torque to the left. Times are seconds from the driver's input. Speed {SPEED_KPH:g} km/h (ODD-H bound); the rack "
    "stiffness is set so that full LKA torque gives the L1 steady state (LAT_ACCEL_FACTOR). The panda does not act on "
    "driver torque on the LKA path (TSR-304 not implemented, GAP-02), so the host's rule is the only override "
    f"path. SG-05 / TSR-304 budget: back-off ≤ {SG05_S:g} s.",
    "",
    "| Label (WP-V-02 §5.3.5) | Value |",
    "|---|---|",
    "| data_kind | synthetic |",
    "| simulator | LionDriver steering column, fidelity L2: OpenModelica 1.27.1 FMU of `SteeringColumn.mo` run by FMPy; panda "
    f"safety code compiled from panda `{submodule_commit('panda')}` and opendbc `{submodule_commit('opendbc_repo')}` "
    "(reference build) |",
    "| asset archive hash | none (nothing is rendered) |",
    "| scenario ID and family | none: a held LKA command against a driver torque ramp, not a WP-V-03 scenario |",
    "| fidelity-case status | none |",
    "| credit | none |",
    "| camera frame rate | not applicable (no camera) |",
    "",
    "| LKA full torque (N·m) | Host threshold (N·m) | Driver peak (N·m) / rise (s) | steeringPressed (s) | "
    "Host drops LKA (s) | Zero frame passed (s) | Motor < 5 % (s) | Wheel angle then (°) | Back-off within "
    f"{SG05_S:g} s |",
    "|---|---|---|---|---|---|---|---|---|",
  ]
  rows = []
  for r in runs:
    ok = r.t_host_drop is not None and r.t_host_drop <= SG05_S
    rows.append(f"| {r.lka_nm:g} | {r.host_nm:g} | {r.peak_nm:g} / {r.rise_s:g} | {_s(r.t_steering_pressed)} | "
                f"{_s(r.t_host_drop)} | {_s(r.t_zero_frame)} | {_s(r.t_motor_5)} | "
                f"{'—' if r.sw_deg_at_5 is None else f'{r.sw_deg_at_5:.1f}'} | {'yes' if ok else '**no**'} |")
  params = ["", "## Column parameters (assumed)", "", "| Parameter | Value | Unit | Meaning |", "|---|---|---|---|"]
  params += [f"| `{k}` | {v[0]:g} | {v[1]} | {v[2]} |" for k, v in COLUMN.items()]
  params += [f"| `k_r` | {k_rack(LKA_FULL_NM[0]):.0f} / {k_rack(LKA_FULL_NM[1]):.0f} | N·m/rad | rack stiffness at the "
             "column, from the L1 steady state for each LKA torque scale |"]
  return "\n".join(head + rows + params) + "\n"


def main(argv: list[str]) -> int:
  fmu = argv[argv.index("--fmu") + 1]
  text = table(sweep(fmu))
  if "--check" in argv:
    if not TABLE.exists() or TABLE.read_text(encoding="utf-8") != text:
      print(f"stale: {TABLE.name}; run: python3 assurance/sim/plant/override.py --fmu <fmu>", file=sys.stderr)
      return 1
    print("override: table current")
    return 0
  TABLE.write_text(text, encoding="utf-8")
  print(f"override: wrote {TABLE.name}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
