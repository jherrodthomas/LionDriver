# Plant interface specification

| Field | Value |
|---|---|
| Scope | The interface between the vehicle plant (vehicle, EPS, PCM, driver, road) and the harnesses that drive it: the fault-injection loop of `plant/simulate.py` today; an FMU under FMPy, MetaDrive and the HIL bench later (modelling-plan work item 4) |
| Version | 0.1 (2026-10-16) |
| Status | Draft. AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed |

One plant, many harnesses: every harness exchanges the same signals at the same rates, so a plant of another fidelity
level (L1 Python, L2 OpenModelica EPS physics) can replace another without changing the harness. The CAN side is
defined by the opendbc DBC `toyota_nodsu_pt_generated` and the Toyota RX checks of `opendbc/safety/modes/toyota.h`;
this table names the physical signals behind those frames.

## 1. Inputs to the plant

| Signal | Unit | Rate | Source in the loop | CAN frame (DBC signal) |
|---|---|---|---|---|
| LKA torque command | raw, −1500…1500 | 100 Hz, when a frame reaches the car bus | panda TX hook, or the stock camera through a pass-through switch | STEERING_LKA `0x2E4` (STEER_TORQUE_CMD) |
| LKA request | bool | with the torque command | as above | STEERING_LKA (STEER_REQUEST) |
| Acceleration request | m/s² | 33 Hz | panda TX hook | ACC_CONTROL `0x343` (ACCEL_CMD) |
| PCS braking request reaches the car | event | on change | camera side through the switch, or the panda forwarding hook | PRE_COLLISION_2 `0x344` |
| Injected plant faults | enum, time | on change | fault catalog (`faults.yaml`) | e.g. EPS fault, assist lost |

## 2. Outputs of the plant

| Signal | Unit | Rate | CAN frame (DBC signal) | Notes |
|---|---|---|---|---|
| Wheel speeds | km/h | 83 Hz | WHEEL_SPEEDS `0xAA` | all four equal (no wheel slip in the single-track model) |
| EPS motor torque | raw (EPS factor 73) | 50 Hz | STEER_TORQUE_SENSOR `0x260` (STEER_TORQUE_EPS) | the applied LKA torque after the EPS lag |
| Driver torque | raw | 50 Hz | STEER_TORQUE_SENSOR (STEER_TORQUE_DRIVER) | 0 at L1 (the driver is modelled as an angle); L2 provides it |
| Steering-wheel angle | deg | 50 Hz | STEER_TORQUE_SENSOR (STEER_ANGLE) | front-wheel angle × steerRatio |
| EPS state | enum | 25 Hz | EPS_STATUS `0x262` (LKA_STATE) | 5 normal; fault codes as in `toyota_lka_state_is_fault` |
| Cruise active, accelerator released | bool | 33 Hz | PCM_CRUISE `0x1D2` (CRUISE_ACTIVE, GAS_RELEASED) | |
| Main switch | bool | 33 Hz | PCM_CRUISE_2 `0x1D3` (MAIN_ON) | |
| Brake pressed | bool | 40 Hz | BRAKE_MODULE `0x226` (BRAKE_PRESSED) | |
| Vehicle state | m, m, rad, m/s, m/s² | 200 Hz (5 ms step) | — | position, heading, speed, lateral and longitudinal acceleration, for the measurements |
| Road-relative state | m, m, rad | 200 Hz | — | arc length s, lateral offset to the lane centre, heading error |

## 3. Parameters

All plant parameters, with value, unit, source and status (`opendbc`, `scaled`, `vehicle2`, `confirmed`, or an
assumption), are listed under the results table ([`results/plant-results.md`](results/plant-results.md) "Model
inputs"). An assumed value is marked as assumed in every result that uses it (MD-04).

## 4. Timing

The harness steps at 1 ms; the plant integrates at 5 ms (RK4). A harness running at another rate (the bench at
100 Hz) samples the outputs at its own rate and holds the inputs between frames.

## 5. FMU variables

The FMU of [`plant/fmu/`](plant/fmu/) (FMI 2.0 co-simulation) exposes the interface as these variables.

| Causality | Variables |
|---|---|
| Parameter | `v0` (m/s), `eps_timeout` (s), `pcm_timeout` (s) |
| Input | `lka_torque` (raw), `lka_request` (bool), `lka_frames` (counter: a change means a STEERING_LKA frame arrived), `accel_cmd` (m/s²), `acc_frames` (counter for ACC_CONTROL), `eps_fault` (bool), `driver_ay`, `driver_ax` (m/s², the driver's added acceleration) |
| Output | `sx`, `sy` (m), `delta` (rad, front wheel), `v` (m/s), `psi` (rad), `yaw_rate` (rad/s), `beta` (rad), `eps_torque` (raw), `ax`, `ay` (m/s²) |
