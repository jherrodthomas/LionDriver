# Simulation track: method

| Field | Value |
|---|---|
| Scope | Simulation for LionDriver; modelling-plan work item 4, the HIL plant ([models README](../models/README.md), MD-01, MD-04): fault-injection plant model (layer 1), known scenarios as OpenSCENARIO (layer 2), MetaDrive closed loop (layer 3), unknown-scenario search (layer 4) |
| Version | 0.1 (layer 1, 2026-10-16) |
| Status | Draft. AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed. **No result here is evidence until the model is validated against Corolla logs; until then results rank risks and guide tests only** (§4) |
| Feeds | [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) timing (owned by the safety-concept session); [WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md) M4, [WP-V-03](../06-validation/WP-V-03-sotif-known-scenarios.md), [WP-V-04](../06-validation/WP-V-04-sotif-unknown-scenarios.md) (owned by the SOTIF session); previews [WP-V-05](../06-validation/WP-V-05-fault-injection.md) cases |

## 1. Where things are

Everything the simulation track adds lives in `assurance/sim/`: code next to the method and results it produces, as
the figure tools of the other work products do. The MetaDrive bridge stays where openpilot keeps it,
`openpilot/tools/sim/` (layer 3).

| Path | Content |
|---|---|
| [`faults.yaml`](faults.yaml) | Fault catalog: each fault with its FMEA causes, TSRs, injection point, trigger, duration and expected mechanism |
| [`INTERFACE.md`](INTERFACE.md) | Plant interface: signals, units and rates shared by every harness |
| [`plant/`](plant/) | Layer 1: the fault-injection plant model and its tests; the plant itself is [`plant/plant.py`](plant/plant.py) |
| [`plant/fmu/`](plant/fmu/) | The same plant as an FMI 2.0 co-simulation FMU (built, not committed), and its test under FMPy |
| [`results/plant-results.md`](results/plant-results.md) | Layer 1 results table, event log and model inputs (generated) |
| [`figures/`](figures/) | Layer 1 figures, one per selected case (generated) |
| [`requirements.txt`](requirements.txt) | Pinned Python packages of the track |

```sh
git submodule update --init opendbc_repo panda
python3 -m pip install -r assurance/sim/requirements.txt
python3 assurance/sim/plant/report.py           # run all cases (about 7 s), write the table and figures
python3 assurance/sim/plant/report.py --check   # CI: fail if the committed outputs differ from a fresh run
python3 assurance/sim/plant/test_plant.py       # unit tests (CI)
```

## 2. Layers: what each can and cannot show

| Layer | Status | Can show | Cannot show |
|---|---|---|---|
| 1. Fault-injection plant model (`plant/`) | Built | What the **real panda safety code** of the reference build does with each injected fault, frame by frame and in time: refusal, revocation, siren, IWDG reset, relay-malfunction detection. How far the car moves meanwhile under stated EPS, PCM and driver assumptions, against the WP-S-04 §3 kinematic estimates. Which assumptions decide the outcome (sensitivity runs) | Anything the assumptions decide: the EPS reaction to lost frames, the torque-to-lateral-acceleration gain, the driver. The SoC: openpilot is replaced by a perfect-perception controller, so no SoC alert, no model or planner fault. Interrupt latency and bus load on the real MCU. Tyre limits beyond the linear single-track model. Results are not measurements and not code-derived times |
| 2. Known scenarios as data (OpenSCENARIO + OpenDRIVE, esmini) | Planned (backlog item 2) | That each WP-V-03 scenario that simulation can represent is written down unambiguously, parses and replays headless; the same road and traffic used by layers 1 and 3 | Any behaviour of the item: esmini plays the scenario with its own simple controllers |
| 3. MetaDrive closed loop (`openpilot/tools/sim`) | Planned (backlog item 3) | The full openpilot stack driving on rendered images, with the Corolla CarParams and the panda safety code in the loop, in WP-V-03 scenarios with traffic: lateral and longitudinal behaviour, alert timing, outcome class | Camera realism, sensor faults, the real EPS and PCM; credit only per scenario family after the WP-V-02 §5.3 fidelity case (DQ-139) |
| 4. Unknown-scenario search (Scenic with VerifAI) | Planned (backlog item 4) | Parameter regions of layer 2/3 scenarios where the item fails, to direct closed-course tests (WP-V-04 U-4) | That no other failure exists; a rate of failure in the real ODD |

## 3. Layer 1: fault-injection plant model

### 3.1 Loop

```
SoC stand-in ── STEERING_LKA 100 Hz, ACC_CONTROL 33 Hz, heartbeat 10 Hz ──▶ panda safety code (real)
     ▲                                                                       │ frames the TX hook allows
     │ perfect perception                                                    ▼
CommonRoad single-track Corolla ◀── EPS model, PCM model ◀──────────── car bus ◀── stock camera frames
     │                                   ▲                                      (only through a pass-through switch)
     └─ driver model ────────────────────┘
car bus RX at the nominal rates (0xAA, 0x260, 0x262, 0x1D2, 0x1D3, 0x226) ──▶ panda RX hook and 100 Hz safety task
```

| Part | Real code or model | Detail |
|---|---|---|
| Panda safety decisions | **Real code** | opendbc `libsafety` compiled with `LIONDRIVER_REFERENCE`, Toyota mode with safety parameter 73 (`panda/board/reference_lock.h`); every RX and TX frame goes through its hooks |
| Panda 100 Hz safety task | **Real code**, glue restated | `panda/board/drivers/heartbeat_monitor.h`, `heartbeat_siren.h`, `eps_fault_siren.h`, `hw_watchdog.h` compiled unchanged into [`plant/sim_panda.c`](plant/sim_panda.c); the few lines of `main.c` that call them are restated there, and `test_plant.py` fails when the firmware's lines change |
| IWDG | Model of the peripheral | Counts down at f_LSI / (4 · 2^PR) from the reload value the firmware writes; a feed outside the window resets. Nominal LSI 32 kHz; its tolerance (watchdog impact record OI-2) is not modelled |
| Harness switch | Model | Two DG419LE switches with pull-down to pass-through and no feedback (RR-2026-010): pass-through whenever the MCU does not drive them, unless a stuck fault is injected. Transition time taken as zero (to be confirmed from the datasheet, WP-H-02) |
| Host frames | **Real code** | opendbc `toyotacan.create_steer_command` and `create_accel_command`; torque through `apply_meas_steer_torque_limits` with the Toyota `CarControllerParams` |
| SoC | Model | Perfect-perception lane keeping and speed holding, torque from the openpilot torque model (a_y / LAT_ACCEL_FACTOR). Not openpilot: no SoC alerts, no SoC-side fault reactions |
| Vehicle | Model | CommonRoad single-track model (`commonroad-vehicle-models` 3.0.2, `vehicle_dynamics_st`), RK4 at 5 ms. Parameters in §3.2 |
| EPS | Model, **assumption** | LKA torque with a first-order lag of `steerActuatorDelay`; lateral acceleration = LAT_ACCEL_FACTOR · torque / 1500, mapped to a front-wheel angle in steady state. Two cases for lost frames: release after 30 ms, or hold 2 s (T-23). M-02 decides |
| PCM | Model, **assumption** | Acceleration request with a first-order lag of `longitudinalActuatorDelay`; request taken as 0 after 100 ms without a frame. M-03 decides |
| Driver | Model, **assumption** | Reacts 1.5 s (WP-S-04 §3.2 upper value) after the first cue: the panda siren, a 0.2 m drift or a 1 m/s² change of acceleration; corrects with up to 4 m/s². WP-C-08 §8 to replace |
| Roads | Model | Highway only (ODD-H; DQ-023 answered B): straight, and a clothoid over 100 m into a left arc at 1.5 m/s² (inside the ODD) or at the ODD bound R_ODD = v²/2.5 m/s²; 3.7 m lane, thresholds also for the 3.0 m ODD minimum |

The full list of inputs, with source and status of each, is printed under the results table.

**One plant, many harnesses.** The vehicle, EPS and PCM are one class, `CorollaPlant` in
[`plant/plant.py`](plant/plant.py), behind the signals of [`INTERFACE.md`](INTERFACE.md). The fault-injection loop calls
it directly. [`plant/fmu/build_fmu.py`](plant/fmu/build_fmu.py) packages the same class as an FMI 2.0 co-simulation
FMU with pythonfmu, freezing the parameters into the FMU's resources, so that any FMI master can drive it: FMPy in the
test, later MetaDrive and the HIL bench. The test runs the FMU through FMPy and requires the same trajectory as the
in-process plant (to 1e-9). A plant of higher fidelity (L2, OpenModelica EPS physics) is meant to replace it behind
the same interface. The FMU runs Python from the host: it needs the packages of `requirements.txt`, and is a build
product, not a committed file.

### 3.2 Corolla parameters

CommonRoad has no Corolla set. The model starts from **CommonRoad vehicle 2 (BMW 320i)**: of the four CommonRoad
sets it is the only front-engined compact sedan (vehicle 1 is an older, lighter Ford Escort, vehicle 3 a VW Vanagon
van, vehicle 4 a semi-trailer truck). Over it go the Corolla values openpilot itself uses: mass with standard cargo,
wheelbase and centre of gravity from the opendbc `TOYOTA_COROLLA_TSS2` CarParams, yaw inertia scaled by m·L² (the rule
of opendbc's `scale_rot_inertia`), and the body width checked in WP-V-02 §3.5. Tyre stiffness, friction and steering
rate stay at vehicle 2. With one normalised cornering stiffness front and rear the single-track model is neutral-steer;
the test suite checks it. Nothing is measured on the reference car (WP-S-04 M-01).

### 3.3 Faults and measurements

The faults are those of the backlog, each traced to its FMEA rows and to the WP-V-05 case it previews:
over-limit torque and rate (F-01a, F-01b), torque while not engaged (F-02), frozen command (F-03), SoC heartbeat loss
and SoC stall (F-04a, F-04b), MCU hang until the IWDG reset (F-05), harness switch stuck in pass-through or intercept
(F-06a, F-06b), EPS fault (F-07), RX loss (F-08), the longitudinal equivalents for SG-03/SG-04 (L-01…L-04), and
the stock PCS path for SG-07 (P-01…P-03, from the safety-concept session's handover). The catalog
[`faults.yaml`](faults.yaml) holds each fault with its FMEA causes and TSRs; the tests check that every one exists.
Faults whose reaction is a loss of frames at the EPS are run again with the EPS-hold assumption (suffix `-H`).

Measured per case: the panda's reaction times, EPS torque below 5 %, siren, driver cue and correction, lateral
deviation at the 0.5 s SG-01 FTTI, time until the body edge reaches the lane line (3.0 m and 3.7 m lanes), the WP-S-04
§3.1 kinematic estimate for the same acceleration, and for longitudinal cases the gaps to a lead and a follower against
WP-S-04 §3.3/§3.4. The §3.1 formulas are restated in [`plant/kinematics.py`](plant/kinematics.py) and tested against
the §3.1 table.

Figures follow the layout the lead approved: a top-down lane view with the ego path, the lateral deviation against
time with the 0.5 s FTTI band and the lane-line thresholds, and an event timeline. They use colour tokens with a dark
variant, so they read in either theme.

## 4. Credit and hand-back

**Evidence rule.** No result of this track is evidence until the model is validated against Corolla logs (roadmap
phase S7: system identification of EPS lag, steer ratio and tyre stiffness, and the WP-V-02 §5.3 fidelity case).
Until then the results only rank risks and guide which tests to run on the bench and the car.

- **No evidence credit.** Simulation earns credit only once the WP-V-02 §5.3 fidelity case is approved for the scenario
  family; whether any family may get credit is queued for the lead as DQ-139 (DQ-107 is its duplicate). Every output is labelled synthetic data
  under DSR-12 and is kept apart from real-world data.
- **Not self-credited.** Timing results go to the safety-concept session, which decides what enters WP-S-04. Scenario
  results go to the SOTIF session for WP-V-03/04. The simulation track does not edit those documents.
- **Rating tables.** The FMEA-MSR rating tables (RT-2 §7) allow `measured | code_derived | unknown` timing only. A
  simulated time enters them only if the System FMEA session accepts a proposal to add a category.

## 5. Dependencies and licences

| Package | Version | Licence | Use |
|---|---|---|---|
| commonroad-vehicle-models | 3.0.2 | BSD-3-Clause (TUM) | single-track vehicle model and vehicle-2 parameters |
| omegaconf, PyYAML | 2.4.0, 6.0.3 | BSD-3-Clause, MIT | parameter loading of commonroad-vehicle-models |
| cffi, pycparser | 2.1.1, 3.11 | MIT-0, BSD-3-Clause | loading the compiled panda code |
| pycapnp | 2.1.0 | BSD-2-Clause | imported by opendbc (same pin as the root `pyproject.toml`) |
| numpy | 2.5.4 | BSD-3-Clause with permissive bundled licences | opendbc host limit functions |
| pythonfmu | 0.7.0 | MIT | packaging the plant as an FMU |
| fmpy | 0.3.32 | BSD-2-Clause; its dependencies MIT, BSD-3-Clause, Apache-2.0 | running the FMU in the test |

Licences read from the package metadata on 2026-10-16. All were reachable through the network proxy. The panda and
opendbc code is the project's own (MIT).

## 6. Open items

| ID | Item |
|---|---|
| SIM-OI-1 | The EPS reaction to lost STEERING_LKA frames decides most layer-1 results (release vs hold). Replace both cases with M-02 once measured |
| SIM-OI-2 | Replace the driver assumptions with WP-C-08 §8 values; add the SoC take-over alert once openpilot runs in the loop (layer 3) |
| SIM-OI-3 | Model the LSI tolerance and the other hang types of WP-V-05 VS-FI-17 (main loop only, tick, safety task) |
| SIM-OI-4 | Layers 2–4 (backlog items 2–4) |
