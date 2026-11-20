# openpilot's planner in the loop: a cut-in, a cut-out and a hard-braking lead

> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** openpilot's own longitudinal MPC, built outside
> openpilot (tool TL-67), in a closed loop with a point-mass car and scripted leads. Physics plan round 4, phase C
> ([`physics-plan-round4.md`](../physics-plan-round4.md) §4).

**Question.** How does openpilot's longitudinal planner meet a close cut-in (TC-07), a cut-out that uncovers a stopped
car (TC-09, TC-08) and a lead braking harder than the item may (TC-33), with the item's braking clipped at
−3.5 m/s²?

**Method.**
- **The solver:** [`mpc_build.py`](mpc_build.py) copies `long_mpc.py` unchanged into `build/`, runs it as acados's
  code generator and compiles the solver with openpilot's own acados and Cython (the versions in `uv.lock`). cereal's
  two enums, the logger and four constants are stand-ins; the constants are read from their source files. The
  source's SHA-256 is recorded in [`mpc-source.json`](mpc-source.json).
- **The loop:** [`loop.py`](loop.py) does at 20 Hz what `longitudinal_planner.py` does with a lead: the MPC, the plan
  resampled, `get_accel_from_plan` (run from `drive_helpers.py`'s source) at the actuator delay, the lower of that
  and the cruise target, clipped to ACCEL_MIN/MAX. The car follows the target after the Corolla's
  `longitudinalActuatorDelay` (0.15 s). FCW is the planner's own rule.
- **The scenarios** ([`lead_events.py`](lead_events.py), inputs in [`params.yaml`](params.yaml)): cut-ins 0.5–1.5 s
  ahead and 0–30 km/h slower at 110 km/h; cut-outs at 60–110 km/h uncovering a stopped car the lead would have reached
  1–3 s later; leads braking at 4–9 m/s² from the planner's gap, with the item alone and with a driver braking fully
  1.5 s after FCW. The model's latency in taking a new lead is assumed, 0.2–1 s.

**Result** ([`results/lead-events.md`](../results/lead-events.md)):
- **The planner ramps its braking** over about a second or two (its jerk and acceleration-change costs) rather than
  braking hard at once.
- **Cut-ins are mostly within the item:** 4 of 36 runs hit, all cut-ins half a second ahead and 20–30 km/h slower.
- **A cut-out is beyond it:** at 110 km/h the uncovered car is 81–142 m away (standard gap, 0.5 s latency) and the item
  alone hits it at 34–82 km/h. Even at 60 km/h a late swerve hits.
- **A hard-braking lead is beyond it too,** even at 4 m/s²: the item alone hits at 10–39 km/h from 80 km/h and
  33–66 km/h from 110 km/h. openpilot's FCW comes 1.2–6.4 s after the lead starts braking; a driver braking fully
  1.5 s after it still hits in 18 of 24 runs.
- **So the stock PCS (not modelled) is the backstop** for cut-outs and hard-braking leads, as WP-C-02 F-02 says.

![Above: impact speed with the item alone against how late the lead swerves out of a stopped car's way, at 60, 80, 100 and 110 km/h. Below: impact speed against the lead's braking at 80 and 110 km/h, with the item alone and with a driver braking 1.5 s after FCW](figures/fig-pl-1-lead-events.webp)

*Figure 1. openpilot's planner: a cut-out and a hard-braking lead.*

**Limits.** The car is a point mass with a pure delay; the PCM's own response, the stock PCS and the radar's view are
left out. The model's latency is assumed. The leads move in our lane only (the cut-in appears at its gap).

## Checks

[`test_planner.py`](test_planner.py) runs in CI (job "simulation planner"):

| Check | Catches |
|---|---|
| O1 long_mpc.py's SHA-256 and the constants it reads equal the record; the build's copy is byte-identical | a planner change or a stale build |
| O2 Steady following at the planner's own gap asks for no braking and holds the gap | a wrong loop or stand-in |
| O3 get_accel_from_plan, run from its source, gives zero on a constant plan and the rate on a constant slowing | a wrong planner step |
| O4 A lead braking within the item's bound is followed to a stop without impact or clip | a loop that brakes wrongly |

`lead_events.py --check` reruns every case and fails if a number moves by more than 5 % from the committed JSON.

```sh
python3 -m pip install -r assurance/sim/planner/requirements.txt
python3 assurance/sim/planner/mpc_build.py        # about a minute; needs the opendbc submodule
python3 assurance/sim/planner/test_planner.py
python3 assurance/sim/planner/lead_events.py --figures   # about 15 s
```

## Files

| File | What |
|---|---|
| [`mpc_build.py`](mpc_build.py) | Builds openpilot's MPC outside openpilot; `--check` against the source record |
| [`mpc-source.json`](mpc-source.json) | The record: long_mpc.py's SHA-256, its constants, cereal's enums |
| [`loop.py`](loop.py) | The planner's step in a closed loop |
| [`lead_events.py`](lead_events.py) | The three studies and their results page |
| [`params.yaml`](params.yaml) | Every input with its source and status |
| [`fig_planner.py`](fig_planner.py) | The figure |
| [`test_planner.py`](test_planner.py) | Checks O1–O4 |
| [`requirements.txt`](requirements.txt) | The environment, pinned |
