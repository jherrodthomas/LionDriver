# WP-C-11 AI System Definition and AI Safety Requirements

| Field | Value |
|---|---|
| Work product | WP-C-11 AI system definition and AI safety requirements |
| Standard reference | ISO/PAS 8800:2024 (AI system definition, input space, AI safety requirements, data requirements); ISO 21448:2022 §5, §7; ASPICE 4.0 MLE.1, SUP.11 (data requirements) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | QM (FuSa) / SOTIF for AI-1 and AI-2; AI-3 / DM chain QM per the [WP-C-04 §7](WP-C-04-functional-safety-concept.md) proposal (SOTIF misuse measure) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); acquired-model route confirmed by the external assessor ([WP-M-10](../01-management/WP-M-10-ai-safety-plan.md) OI-1) |
| Approver | Project maintainer (acting safety manager, AI safety lead) |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

This document defines the AI systems inside LD-SDA, the space of inputs they are expected to handle (derived from the ODD), how their outputs are allocated inside the safety-envelope architecture, the kinds of error they can make, and the AI safety requirements (AIR-nn) and dataset requirements (DSR-nn) that the pinned model artefacts must be evaluated against.

It implements the MLE.1 / "AI safety requirements" activity of the [AI safety plan (WP-M-10 §6.1)](../01-management/WP-M-10-ai-safety-plan.md). Because LionDriver does not train models (acquired, pre-trained model route, WP-M-10 §5), the AIRs are **acceptance criteria for an existing artefact plus requirements on the surrounding software** (pre/post-processing, runtime monitors, integrity, fallbacks). They do not steer a training process.

Inputs: [WP-C-01](WP-C-01-item-definition.md) (E-02, E-06, F-01…F-06), [WP-C-03](WP-C-03-hara.md) (SG-01…SG-07), [WP-M-08](../01-management/WP-M-08-sotif-plan.md), [WP-M-10](../01-management/WP-M-10-ai-safety-plan.md), the gap assessment (GAP-17, GAP-18, GAP-21, GAP-22). [WP-C-02](WP-C-02-odd-and-intended-functionality.md) (ODD-H, ODD-A), [WP-C-04](WP-C-04-functional-safety-concept.md) (FSR-02.02…02.09, FSR-06.01…06.04), [WP-C-05](WP-C-05-sotif-hazard-identification.md) (SH-01…SH-13), [WP-C-06](WP-C-06-sotif-insufficiencies-triggering-conditions.md) (FI-01…FI-22, TC-01…TC-31), [WP-C-07](WP-C-07-sotif-functional-modifications.md) (FM-01…FM-11) and [WP-C-08](WP-C-08-driver-hmi-misuse-analysis.md) (DMP-01…DMP-04).

## 2. AI system and component definition

### 2.1 AI components

Identifiers follow [WP-M-10 §2](../01-management/WP-M-10-ai-safety-plan.md#2-ai-component-inventory).

| ID | Component | Artefact (this checkout: Git LFS pointer) | LFS identity (sha256 oid, size) | Runtime | In reference configuration |
|---|---|---|---|---|---|
| AI-1 | Driving model ("supercombo"), vision + policy, recurrent | `openpilot/selfdrive/modeld/models/driving_supercombo.onnx` → compiled `driving_tinygrad.pkl` | `65a08adc…7248cce`, 60 918 562 B | Device GPU (`QCOM`), process `modeld`, 20 Hz (`constants.py:17` `MODEL_RUN_FREQ = 20`) | Yes |
| AI-2 | Big driving model ("Chestnut") | `models/big_driving_tinygrad.pkl` (pre-compiled by comma, no ONNX source) + `big_driving_warp_*` | `51420a13…3c79c04`, 799 942 038 B | External USB AMD eGPU (`helpers.py:17`, `USB+AMD:LLVM`) | **No** — E-06 is excluded pending [WP-C-01](WP-C-01-item-definition.md) OI-4 and [WP-C-07](WP-C-07-sotif-functional-modifications.md). Requirements below still state what would apply if it were included |
| AI-3 | Driver monitoring model | `models/dmonitoring_model.onnx` → compiled `dmonitoring_model_tinygrad.pkl` | `dee5a294…3ede1b04`, 7 844 499 B | Device GPU, process `dmonitoringmodeld`, real-time priority 5 on core 7 (`dmonitoringmodeld.py:112`) | Yes |

The full SHA-256 values are in the LFS pointer files. They identify the source artefacts only; the compiled `.pkl` files are build outputs whose hashes are not recorded anywhere today (GAP-22; requirement AIR-21).

### 2.2 AI system boundary

The **AI system** for this document is the chain from the camera frame buffers to the published model messages, including the pre- and post-processing that LionDriver can inspect:

```
 camerad (VisionIPC NV12 frames)
   │  narrow road + wide road (AI-1/AI-2)       cabin (AI-3)
   ▼
 [warp kernel: calibrated perspective warp]   [dm warp kernel]          ← compiled by tinygrad (compile_warp.py)
   ▼                                            ▼
 [AI-1 / AI-2 network, recurrent state]      [AI-3 network]            ← compiled by tinygrad (compile_onnx.py) or shipped pre-compiled
   ▼                                            ▼
 [Parser: mdn / sigmoid / softmax]           [parse_model_output]       ← parse_model_outputs.py, dmonitoringmodeld.py:73-82
   ▼                                            ▼
 [action extraction + smoothing, FCW,        driverStateV2              ← modeld.py:52-77, fill_model_msg.py
  confidence, desire helper]
   ▼
 modelV2, drivingModelData, cameraOdometry
```

Outside the AI system but consuming its outputs: `controlsd`, `plannerd`, `radard`, `locationd`, `selfdrived`, `dmonitoringd` / `policy.py`, and ultimately the panda safety envelope. The runtime monitors required here (§6.4) are conventional QM software placed around the AI system, not part of the network.

### 2.3 Inputs

| Input | Component | Source and pre-processing | Code |
|---|---|---|---|
| Road images, two cameras (`img` from main, `big_img` from wide/extra) | AI-1/AI-2 | NV12 frames from VisionIPC; two consecutive frames per input (`--frames 2`); warped on GPU to the model input size 512×256 (`MEDMODEL_INPUT_SIZE`, `common/transformations/model.py:10`) using the calibration-dependent warp matrix | `modeld.py:193-205`, `modeld.py:367-374`, `SConscript:54-62` |
| Calibration transform | AI-1/AI-2 | From `extrinsicsCalibration.rpyCalib` and camera intrinsics per device/sensor (`DEVICE_CAMERAS`); zero matrix until the first calibration message | `modeld.py:308-309, 367-375` |
| Desire pulse (8) | AI-1/AI-2 | One-hot from `DesireHelper` (lane change), sent as a rising-edge pulse only | `modeld.py:197-200, 380-382` |
| Traffic convention (2) | AI-1/AI-2 | LHD/RHD from `driverMonitoringState.isRHD` | `modeld.py:363, 377-378` |
| Action time (2) | AI-1/AI-2 | Lateral and longitudinal actuator delay + frame delay + half a model period | `modeld.py:396-404` |
| Recurrent state (`next_*` outputs fed back) | AI-1/AI-2 | Held on device; zeroed at construction and by `warmup()` | `modeld.py:148, 164-166, 218-226` |
| Cabin image | AI-3 | Cabin camera NV12 → luma warp to 1440×960 (`DM_INPUT_SIZE`) | `dmonitoringmodeld.py:50-62`, `SConscript:64-71` |
| Calibration (`calib`) | AI-3 | `extrinsicsCalibration.rpyCalib`; zeros until received | `dmonitoringmodeld.py:127-141` |

### 2.4 Outputs and their consumers

| Output | Component | Post-processing | Consumer and use | Effect on vehicle |
|---|---|---|---|---|
| `action.desiredCurvature` | AI-1/AI-2 | `action[0] / max(1, v)²`; no lateral smoothing (`LAT_SMOOTH_SECONDS = 0.0`); held at the previous value below 0.3 m/s (`modeld.py:46, 66-73`). If the network has no `action` head, derived from the plan (`modeld.py:54-64`) | `controlsd.py:126` → lateral controller → `STEERING_LKA` | **Direct lateral command** (F-01), bounded by controller limits and the panda envelope |
| `action.desiredAcceleration`, `shouldStop` | AI-1/AI-2 | Smoothed with a 0.3 s time constant (`modeld.py:47, 69`) | `longitudinal_planner.py:132-133`; a candidate in the `min()` arbitration **only in Experimental Mode** (`:143-147`) | Longitudinal command in Experimental Mode (GAP-18, D-08) |
| `leadsV3[0..2]` (x, y, v, a with std), `lead_prob` | AI-1/AI-2 | MDN parse, hypothesis selection (`parse_model_outputs.py:44-86, 105-109`) | `radard.py:113-165`: associates vision lead with radar tracks using the model std; uses a vision-only lead when no track matches and `lead_prob > 0.5` | Longitudinal command in both Chill and Experimental modes via the MPC lead |
| `plan` (33×15 with std), `laneLines` (4), `roadEdges` (2), probs and std | AI-1/AI-2 | MDN parse; `laneLineProbs` from sigmoid | UI, logging, `drivingModelData`; plan-based action only if no `action` head | Indirect |
| `meta`: engaged, gas/brake disengage, steer override, hard-brake 3/4/5 m/s², gas/brake press, blinkers | AI-1/AI-2 | Sigmoid (`parse_model_outputs.py:103`) | `hardBrakePredicted` → FCW (`fill_model_msg.py:142-148`, `selfdrived.py:442`); brake-disengage prob tightens DM (`policy.py:447`); gas-press prob gates throttle (`longitudinal_planner.py:95-97`) | Warning (F-06); DM sensitivity; longitudinal |
| `confidence` (green/yellow/red) | AI-1/AI-2 | Rolling score from disengage probs (`fill_model_msg.py:150-171`) | No Python consumer found in `openpilot/` at the baseline | None |
| `desireState`, lane-change state | AI-1/AI-2 + DesireHelper | Softmax | `selfdrived.py:314-324` (lane-change alerts); next model input | Lane-change assist |
| `cameraOdometry` (pose, std) | AI-1/AI-2 | MDN parse | `locationd`, `calibrationd` (`posenetInvalid`) | Indirect (state estimation, calibration) |
| `driverStateV2` (face pose/position with std, face/eye/blink/sunglasses/phone/sleep probs, wheel-on-right) | AI-3 | `safe_exp` on std, sigmoid on probs (`dmonitoringmodeld.py:73-82`); message `valid` hard-coded `True` (`:99`) | `dmonitoringd.py` → `policy.py` → `driverMonitoringState` → `selfdrived.py:217-239` | Alerts, force-decel, lockout (F-04) |

### 2.5 Operating context

| Aspect | Value at baseline |
|---|---|
| Execution | AI-1: process `modeld`, `SCHED_FIFO` priority 54 on core 7 (`modeld.py:291`). AI-3: `dmonitoringmodeld`, priority 5 on core 7. Both share the SoC GPU with UI and encoders (GAP-23) |
| Rate and deadline | 20 Hz camera-driven. Upstream model-replay timing limits: modelV2 instant ≤ 50 ms, average ≤ 30 ms; driverStateV2 instant ≤ 50 ms, average ≤ 18 ms (`process_replay/model_replay.py:37-40`). These are regression thresholds, not derived deadlines |
| Precision | Device compile uses `FLOAT16=1 IMAGE=1` (`SConscript:28`); PC builds use `CPU:LLVM` full precision. Device and PC outputs differ, which is why PC model replay ignores most fields (`model_replay.py:268-288`) |
| Start-up | AI-1 loaded synchronously; with AI-2, the small model is also loaded (not warmed up) as a fallback (`modeld.py:285`). AI-2 loading may take up to `BIG_MODEL_TIMEOUT = 60 s` (`modeld.py:49, 281`) |
| Failure handling | AI-1 exception terminates `modeld` (`modeld.py:411-413`) → `processNotRunning` / `commIssue` in `selfdrived`. AI-2 exception or non-finite output → hot switch to cold AI-1 while engaged (`modeld.py:414-421`), with diagnostics masked (GAP-17). No non-finite check on AI-1 or AI-3 outputs |
| Validity flags | `modelV2.valid` = calibration seen (`fill_model_msg.py:79`, `modeld.py:434`); `cameraOdometry.valid` additionally requires no dropped frame (`fill_model_msg.py:179`); `driverStateV2.valid` always `True` |

## 3. Input space definition linked to the ODD

The input space is the set of input conditions under which the AIRs in §6 are claimed. It is derived from the ODD taxonomy in [WP-C-02 §3.1](WP-C-02-odd-and-intended-functionality.md#31-odd-taxonomy) (ODD-H limited-access highway, ODD-A arterial and rural roads); the ODD column gives the link. Anything outside this space is out-of-distribution (OOD) by definition for LionDriver's argument, whether or not comma's training set covered it.

| Dimension | Input-space bound (proposed) | ODD link | Observable at runtime? | Basis |
|---|---|---|---|---|
| Road type | ODD-H: limited-access divided highway; ODD-A: divided/undivided arterials and two-lane rural highways, intersections traversed with the driver controlling stops and turns | WP-C-02 §3.1 road type, intersections; HARA OS-01…OS-07 | Partially (map/GNSS not used for gating today) | `docs/LIMITATIONS.md:14-19` |
| Lane marking quality | Visible longitudinal markings on at least one side (US MUTCD); no long faded sections, no conflicting old/new markings, no work-zone markings (TC-05, TC-06) | WP-C-02 §3.1 lane markings | Partially (`laneLineProbs`) | `LIMITATIONS.md:15` |
| Curvature | R ≥ v²/2.5 m/s² (R_ODD, 0.5 m/s² margin below the 3.0 m/s² controller limit, `drive_helpers.py:9-14`); grade and banking ≤ 6 % (TC-14…TC-16) | WP-C-02 §3.1, §3.2 | Yes (vehicle state) | `LIMITATIONS.md:14` |
| Speed | ODD-H 0–120 km/h, ODD-A 0–90 km/h, not above the posted limit; upstream allows engagement up to ≈ 149 km/h and only warns (GAP-19, TC-20, FM-07) | WP-C-02 §3.1 speed | Yes | `events.py:989-996` |
| Illumination | Day, dusk/dawn, night with headlights; excludes low sun directly in the camera field of view, oncoming high-beam glare and tunnels until validated (TC-01, TC-02, TC-18) | WP-C-02 §3.1 lighting | Partially (camera exposure stats) | `LIMITATIONS.md:18` |
| Weather / visibility | None or light rain; visibility ≥ 200 m (ODD-H) / ≥ 150 m (ODD-A); no snow, fog, moderate/heavy rain (TC-03, TC-04) | WP-C-02 §3.1 weather | No direct detector | `LIMITATIONS.md:10` |
| Optical path | Clean windscreen; no obstruction in the camera area | AOU-08, OPS-03 ([WP-O-02](../09-production-operation/WP-O-02-operation-service-decommissioning.md)) | No dedicated detector | `LIMITATIONS.md:11-12` |
| Mounting / calibration | `calStatus == calibrated`, pitch −5.2°…+9.7°, yaw ±4.0° (`calibrationd.py:43-46`), plus the narrower installation tolerance of [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md) INS-25 | AOU-08 | Yes | `calibrationd.py:51` |
| Camera hardware | The road and cabin sensors of the reference device revision ([WP-C-01](WP-C-01-item-definition.md) OI-2); intrinsics from `DEVICE_CAMERAS` (`common/transformations/camera.py:55-71`) | Reference configuration | Yes (`deviceType`, sensor) | — |
| Vehicle | Toyota Corolla TSS2 (vehicle dynamics, bonnet line in image, actuator delay `CP.longitudinalActuatorDelay`, learned `lateralDelay`) | Reference configuration | Yes | `modeld.py:323, 366` |
| Traffic convention | Right-hand traffic, left-hand-drive vehicle (US) | WP-C-02 §3.1 geography | Yes | `modeld.py:377-378` |
| Traffic participants | Passenger cars, trucks, motorcycles as leads; pedestrians and cyclists **not** claimed as detected objects; stationary objects in lane are a driver task (SH-06, SH-11, TC-08, TC-12) | WP-C-02 §3.1 traffic, VRUs; `LIMITATIONS.md:34` | — | — |
| Traffic control | Traffic lights and stop signs not claimed (Experimental Mode off, FM-01; SH-09, TC-13) | WP-C-02 §3.1, §6 | — | `LIMITATIONS.md:35` |
| Driver (AI-3) | Adult driver in the driver seat, face within the cabin camera field of view; with or without glasses; sunglasses claimed only if DSR-10 evidence supports it; day and night (IR illumination) | WP-C-08 | Partially (`faceProb`) | `LIMITATIONS.md:53-56` |

Each dimension becomes a tag on the evaluation data (DSR-03) so that AIR metrics can be reported per stratum.

## 4. Allocation within the envelope architecture

| Output path | Upstream QM processing | Bound applied downstream | What the bound does **not** cover |
|---|---|---|---|
| AI-1 curvature → lateral | `controlsd` curvature limits (`MAX_CURVATURE`, lateral accel 3.0 m/s², jerk 5 m/s³, `drive_helpers.py:9-14, 28-42`) | Panda envelope: torque 1500 raw, rate +15/−25 per frame, measured-torque tracking 350 raw (`toyota.h:173-177`); EPS authority (AOU-01) | A **wrong but in-limit** curvature (e.g., following a wrong lane line, drifting at a gore area). Containment relies on driver controllability within the envelope (GAP-04 must be closed for this to hold) |
| AI-1 leads → MPC → acceleration | `radard` association, MPC, `ACCEL_MIN/MAX` clip (`longitudinal_planner.py:149`) | Envelope accel −3.5…+2.0 m/s² (`toyota.h:207-210`); PCM ACC envelope (AOU-05) | Missed or late stationary lead (SH-06), phantom lead (SH-04): both are inside the bounds |
| AI-1 action accel (Experimental only) | `min()` with MPC and cruise (`longitudinal_planner.py:142-149`) | As above | Phantom stops, missed red light; excluded from claims (D-08) |
| AI-1 FCW | `selfdrived.py:441-445` | None (warning only) | Missing/late FCW (QM, SH-06 contributor) |
| AI-3 driver state | `policy.py` timers and thresholds; wheel-touch fallback when model std > 0.3 for 10 s (`policy.py:77-78`) | None at the envelope. DM is a measure against foreseeable misuse (SH-12); [WP-C-04 §7](WP-C-04-functional-safety-concept.md) argues that the HARA C2 ratings assume a supervising driver and do not credit DM | DM false negatives let inattention persist, which removes the supervision that the C2 ratings assume (AOU-06R) |

Consequence: every AI error type in §5 is bounded in **magnitude and rate** by the envelope, but **none is bounded in direction or timeliness**. The AIRs therefore concentrate on (a) keeping in-limit errors rare enough to meet the validation targets in [WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md), and (b) making errors detectable so that the driver is warned (SG-02, SG-06).

## 5. AI-related error types

| Code | Error type | Description | Examples for LD-SDA | Linked FI (WP-C-06) and SOTIF hazard (WP-C-05) |
|---|---|---|---|---|
| AE-P | Perception error | Wrong estimate of the scene | Lane line or road edge misplaced (worn paint, tar seams, shadows); lead missed, late or phantom (bridges, metal plates, overhead signs); lead distance/velocity bias; wrong `wheel_on_right` | FI-01, FI-02, FI-04 (FI-06/07 radar fusion consume its leads); SH-01, SH-02, SH-04, SH-06, SH-11 |
| AE-L | Planning / policy error | Wrong action for a correctly perceived scene | Curvature that cuts a curve or follows an exit lane; acceleration toward a slowing lead; unnecessary stop (Experimental) | FI-03, FI-05; SH-01, SH-03, SH-04, SH-09 |
| AE-T | Temporal inconsistency | Outputs that are individually plausible but inconsistent across frames | Lead flicker (prob crossing 0.5), lane-line switching, curvature oscillation, recurrent-state drift; cold start after reset or fallback (GAP-17); dropped frames | FI-22, FI-15; SH-01, SH-02, SH-04 |
| AE-O | Out-of-distribution input | Input outside the training distribution or the input space of §3 | Snow, low sun, unseen road furniture, construction zones, non-standard mounting, sensor degradation, different vehicle bonnet | FI-03; SH-01…SH-06, SH-13 |
| AE-N | Numerical / runtime error | Fault of the execution, not of the learned function | Non-finite outputs; FLOAT16 overflow (handled partly by `safe_exp` clip at 11, `parse_model_outputs.py:4-6`); compile-time miscompilation (tinygrad, GAP-34); inference overrun | FI-17 (silent clamp); SH-01…SH-06 via the QM software path |
| AE-D | DM classification error | False negative (inattention missed) or false positive (nuisance alerts leading to misuse) | Sunglasses with IR, night, glare, face partly out of view, phone low in the lap | FI-18, FI-19; SH-12 (misuse, WP-C-08) |

## 6. AI safety requirements

Attributes as required by the shared conventions. "Parent" lists the safety goal (SG), SOTIF hazard (SH, [WP-C-05](WP-C-05-sotif-hazard-identification.md)), functional safety requirement (FSR, [WP-C-04](WP-C-04-functional-safety-concept.md)), functional modification (FM, [WP-C-07](WP-C-07-sotif-functional-modifications.md)) or DM performance requirement (DMP, [WP-C-08 §5.3](WP-C-08-driver-hmi-misuse-analysis.md)). ASIL is **QM** for every AIR: AI-1/AI-2 are QM elements managed under SOTIF, and [WP-C-04 §7](WP-C-04-functional-safety-concept.md) proposes QM for the DM chain (FSR-02.06…02.09) as a misuse measure. If that proposal is not accepted at G1, AIR-07, AIR-08, AIR-15 and AIR-27 inherit the DM allocation (OI-3). Numerical values marked **(TBC)** are proposals that [WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md) must confirm against the validation targets. Verification methods use the test identifiers of [WP-W-10 §6](../05-software/WP-W-10-ml-engineering.md) (VS-ML-nn) and [WP-V-03](../06-validation/WP-V-03-sotif-known-scenarios.md) (KS-nn).

Abbreviations for verification: **EVAL** = metric evaluation on LionDriver evaluation data; **REPLAY** = model/process replay; **SIM** = MetaDrive simulation; **CC** = closed course; **PR** = public road with safety driver; **REV** = review/analysis; **INSP** = code inspection.

### 6.1 Performance

| ID | Statement | Comp. | Parent | Verification | Status / evidence |
|---|---|---|---|---|---|
| AIR-01 | In nominal ODD conditions, while lateral control is active and no lane change is requested, the vehicle's lateral offset from the lane centre shall stay within ±0.5 m **(TBC)** for at least 99.5 % **(TBC)** of engaged time, per ODD stratum | AI-1 | SH-01, SH-02; FI-01 | EVAL (VS-ML-03), PR | Not evaluated. No LionDriver data |
| AIR-02 | The rate of unrequested lane departures (a front wheel crossing a lane marking with no desire active and no driver steering input) shall not exceed the validation target VT-01 of WP-V-02 | AI-1 | SH-01 | EVAL, PR, field monitoring | Not evaluated |
| AIR-03 | A lead vehicle in the ego lane within 80 m **(TBC)** shall be reported (`leadsV3[0].prob > 0.5`) within 0.5 s **(TBC)** of becoming unoccluded, with distance error ≤ max(2 m, 10 %) **(TBC)** against the radar reference | AI-1 | SH-06, SH-03; FI-04, FI-07 | EVAL (radar as reference), REPLAY | Not evaluated |
| AIR-04 | A stationary vehicle in the ego lane shall be reported as a lead at a distance not less than v·t_r + v²/(2·a_lim), with t_r = 1.0 s **(TBC)** and a_lim = 3.0 m/s² **(TBC)**, for all speeds in the ODD (e.g., ≈ 180 m at 30 m/s) | AI-1 | SH-06; FI-04, TC-08 | CC (soft target, KS-05), EVAL | Not evaluated. Known limitation `LIMITATIONS.md:37` |
| AIR-05 | The rate of model-induced decelerations stronger than 2.0 m/s² **(TBC)** with no relevant object present (phantom braking) shall not exceed VT-04 of WP-V-02 | AI-1 | SH-04; FI-06, FI-07 | EVAL, PR, field monitoring | Not evaluated |
| AIR-06 | In a closing-lead scenario requiring more than 5 m/s² to avoid collision, `hardBrakePredicted` shall become true at a time-to-collision of at least 2.0 s **(TBC)** | AI-1 | SH-06 (F-06, QM) | CC, SIM, REPLAY | Not evaluated |
| AIR-07 | The DM chain shall classify a driver whose gaze is off the road for more than 2 s as distracted within 1.0 s **(TBC)** with recall ≥ 95 % **(TBC)** per DM stratum (day, night, glasses, sunglasses) | AI-3 | SH-12; FSR-02.06; DMP-01 | EVAL (VS-ML-06), CC | Not evaluated. Thresholds exist in `policy.py:49-60` without performance evidence |
| AIR-08 | The DM chain shall detect eyes closed > 1 s and handheld phone use with recall ≥ 90 % **(TBC)** and a false-distraction rate ≤ 1 per hour **(TBC)** of attentive driving | AI-3 | SH-12; FSR-02.06; DMP-02 | EVAL (VS-ML-06) | Not evaluated |

IDs AIR-01…AIR-30 are allocated in this document.

### 6.2 Robustness

| ID | Statement | Comp. | Parent | Verification | Status / evidence |
|---|---|---|---|---|---|
| AIR-09 | AIR-01…AIR-08 shall be met in **each** input-space stratum of §3 for which a claim is made, not only in aggregate; a stratum that fails is removed from the ODD ([WP-C-07](WP-C-07-sotif-functional-modifications.md)) | AI-1, AI-3 | SH-01…SH-06 | EVAL (sliced metrics, VS-ML-03) | Not evaluated |
| AIR-10 | Under perturbations inside the input space (calibration error up to the INS-25 tolerance, exposure ±1 EV, sensor noise, JPEG/HEVC artefacts, partial lens occlusion ≤ 10 % **(TBC)**), the AI-1 action shall change by less than the bounds in VS-ML-04, **or** the runtime monitor AIR-14 shall flag the frame | AI-1 | SH-01, SH-04 | REPLAY with perturbations (VS-ML-04) | Not evaluated |
| AIR-11 | Frame-to-frame change of `desiredCurvature` while the scene is steady shall not exceed the curvature-rate implied by 5 m/s³ lateral jerk at the current speed **(TBC)**; lead existence (`prob` crossing 0.5) shall not toggle more than once per second **(TBC)** for a continuously visible lead | AI-1 | SH-01, SH-04 | EVAL, REPLAY (VS-ML-07) | Not evaluated |
| AIR-12 | After any (re)initialisation of recurrent state, model outputs shall not be used for actuation until at least 2 s **(TBC)** of consecutive frames have been processed | AI-1, AI-2 | SH-01; FI-22, FI-15; FM-02; GAP-17 | INSP, fault injection (WP-V-05) | **Not met**: the AI-2 → AI-1 fallback uses a cold model immediately while engaged (`modeld.py:414-421`); the fallback model is never warmed up (`modeld.py:285`) |

### 6.3 Uncertainty estimation

| ID | Statement | Comp. | Parent | Verification | Status / evidence |
|---|---|---|---|---|---|
| AIR-13 | The standard deviations published for plan, lead and lane lines shall be calibrated on LionDriver evaluation data: the observed error shall lie within ±2σ for 90–98 % **(TBC)** of samples per stratum, and mean error shall increase monotonically with σ decile | AI-1 | Enables AIR-14 | EVAL (VS-ML-05) | Not evaluated. σ is used today only by `radard` association (`radard.py:113-122`) and posenet checks |
| AIR-14 | A runtime plausibility/uncertainty monitor (RM-3 of WP-M-10) shall flag low-confidence or OOD states from model σ, lane-line probabilities and action–plan consistency, with recall ≥ 80 % **(TBC)** on the known-triggering-condition set and ≤ 1 false flag per hour **(TBC)** in nominal ODD driving; a flag shall raise a driver take-over alert | Monitor (QM SW, not the model) | SH-01, SH-04, SH-06, SH-13; FI-03; FM-09 | EVAL (VS-ML-08), PR | **Not implemented** (GAP-22). `modelV2.confidence` exists (`fill_model_msg.py:150-171`) but nothing consumes it |
| AIR-15 | `driverStateV2.valid` shall be false when the cabin image or model uncertainty indicates that the driver state cannot be determined (RM-4) | AI-3 + monitor | SH-12; FSR-02.07; DMP-03; FM-05; GAP-21 | INSP, EVAL | **Not met**: `valid=True` constant (`dmonitoringmodeld.py:99`). Partial mitigation: policy wheel-touch fallback on σ > 0.3 for 10 s (`policy.py:77-78`) |

### 6.4 Runtime monitoring

| ID | Statement | Comp. | Parent | Verification | Status / evidence |
|---|---|---|---|---|---|
| AIR-16 | Every AI-1 and AI-3 output tensor shall be checked for non-finite values and for range plausibility before use; a failed check shall make the published message invalid and cause a driver take-over request, never a silent substitution | AI-1, AI-3 + modeld | SG-02, SG-06; FSR-02.02, FSR-06.04; FM-04; TSR-6xx ([WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md)) | INSP, fault injection (VS-ML-09) | **Partially**: only AI-2 is checked (`modeld.py:210-211`). `controlsd` silently clamps non-finite actuator values to 0 (`controlsd.py:140-147`, GAP-19) |
| AIR-17 | Model inference shall complete within 50 ms **(TBC from WP-S-04)** per frame; an output older than 100 ms **(TBC)** shall not be used for actuation, and a sustained overrun shall raise a take-over request within the FTTI budget of [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) | AI-1 + consumers | SG-02, SG-06; FSR-02.02, FSR-06.01; FM-03; GAP-16 | Timing test on device (VS-ML-10), INSP | **Partially**: `modeldLagging` on > 1 % frame drop (`selfdrived.py:457`); messaging "alive" allows 10× period (0.5 s) (GAP-16); `controlsd` does not check model freshness |
| AIR-18 | The monitor shall compare `action.desiredCurvature` with the curvature implied by the published plan and flag divergence above a threshold set from evaluation data | Monitor | SH-01; FM-09 | EVAL, INSP | Not implemented |

### 6.5 Integrity and provenance

| ID | Statement | Comp. | Parent | Verification | Status / evidence |
|---|---|---|---|---|---|
| AIR-19 | Before deserialization, each model and warp artefact shall be verified against a SHA-256 value from the signed release manifest; on mismatch the artefact shall not be loaded and engagement shall be prevented (RM-1) | modeld, dmonitoringmodeld | All SGs (via FFI/CS); GAP-22; CSR (WP-C-10) | INSP, test with tampered file (VS-ML-11) | **Not implemented**. Loading is unconditional (`helpers.py:15-20`, `modeld.py:150, 158-159`, `dmonitoringmodeld.py:30-33, 47-48`) |
| AIR-20 | No deserialization mechanism capable of executing code (Python `pickle`) shall be applied to data that has not passed AIR-19 | modeld, dmonitoringmodeld | GAP-22 | INSP | **Not met**: `pickle.load` / `pickle.loads` on artefact content |
| AIR-21 | For each released model, the provenance record shall contain: source artefact LFS oid and size, upstream commit that introduced it, tinygrad commit and compile flags used, compiled artefact hash, compile host, and date | Process | G3.1 of WP-M-10 | REV (release audit) | Not started ([WP-M-10](../01-management/WP-M-10-ai-safety-plan.md) OI-4) |
| AIR-22 | The compiled device artefact shall reproduce the outputs of a reference execution of the source ONNX (independent runtime) on a fixed input set within a stated tolerance per output field | Toolchain | Tool confidence ([WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md)) | VS-ML-01 | Not started. Not possible for AI-2 (no ONNX source) |

### 6.6 Version control

| ID | Statement | Comp. | Parent | Verification | Status / evidence |
|---|---|---|---|---|---|
| AIR-23 | Every drive log shall identify the exact model artefacts in use (hash or release-manifest ID), so that field data can be attributed to a model version | modeld, dmonitoringmodeld | WP-O-04; G3.6 | INSP, log check | **Not met**: only `modelV2.big` is published (`modeld.py:435`) |
| AIR-24 | Any change to a model artefact, the tinygrad pin, or the files listed in WP-M-10 §9 shall be released only after the AIR verification set has been re-run on the new configuration (D-05) | Process | D-05 | REV (change records) | Process defined in WP-M-10 §9; no change has occurred under it |

### 6.7 Fallback behaviour and architecture

| ID | Statement | Comp. | Parent | Verification | Status / evidence |
|---|---|---|---|---|---|
| AIR-25 | On failure of the driving model while engaged (exception, AIR-16 check, AIR-17 overrun), the system shall stop using model outputs for actuation, warn the driver and hand back control within the SG-02 / SG-06 fault-to-warning budget; it shall not switch to another model while actuating | System (modeld, selfdrived) | SG-02, SG-06; FSR-02.02, FSR-02.03, FSR-06.02; FM-02; GAP-17 | Fault injection (WP-V-05), INSP | **Not met for AI-2** (hot switch, diagnostics masked for 5 s, `selfdrived.py:382-384, 403, 457`). AI-1 failure kills `modeld` → `processNotRunning` (behaviour to be timed in WP-V-05) |
| AIR-26 | Engagement shall not be permitted until the driving model has published valid outputs for at least 2 s **(TBC)** after start-up | selfdrived | SG-02 | Test | Partially: `bigModelLoading` NO_ENTRY for AI-2 only; AI-1 start covered indirectly by `all_checks` (to be verified) |
| AIR-27 | If the DM model output is unavailable or invalid for longer than 2 s **(TBC)** while engaged, the system shall escalate to a take-over alert and disengage if the condition persists | dmonitoringd, selfdrived | SH-12; FSR-02.07, FSR-02.09 | Fault injection | **Partially**: invalid inputs stop the DM timers and set `driverMonitoringState.valid=False` (`dmonitoringd.py:25-33`), which leads to a soft disable via `commIssue`; behaviour on stale-but-valid DM output not tested (GAP-21) |
| AIR-28 | AI outputs shall reach the actuators only through `controlsd`/`card` and the panda safety envelope; no AI-derived signal shall alter envelope limits or the safety mode | Architecture | SG-01, SG-03, SG-04 (containment, G3.3) | REV ([WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md)) | Holds by construction at baseline for the CAN path; FFI of the SoC (GAP-09, GAP-20) is open |
| AIR-29 | In the reference configuration, `action.desiredAcceleration` (end-to-end longitudinal) shall not be a candidate in longitudinal arbitration unless [WP-C-07](WP-C-07-sotif-functional-modifications.md) admits Experimental Mode to the ODD | Configuration | SH-09, SH-03, SH-04; FM-01; D-08; GAP-18 | INSP of release parameters (INS-19) | **Not met by default**: `ExperimentalMode` defaults to on (`common/params_keys.h:43`) |
| AIR-30 | AI-2 (Chestnut) shall not be present or loadable in the reference configuration until AIR-12, AIR-21, AIR-22 and AIR-25 are met for it | Configuration | FM-02; GAP-17; WP-C-01 OI-4 | INSP of release file list (`release_files.py:34`) | Default releases exclude it unless `INCLUDE_BIG_MODEL` is set (`build_release.sh:62-65`); presence on a dev install not prevented |

## 7. Dataset requirements

**Training data.** All three models were trained by comma.ai on data LionDriver cannot access. Nothing is known about its content, coverage of the reference ODD, labelling or bias. LionDriver does not train, fine-tune or calibrate the networks. Consequently LionDriver **makes no claim about training data**. The DSRs below apply to data LionDriver collects to **evaluate** the pinned models and to tune and verify its own runtime monitors.

| ID | Requirement | Parent | Verification | Status |
|---|---|---|---|---|
| DSR-01 | For each pinned model, the provenance record (AIR-21) shall state what is known about its training data (at baseline: nothing) and the request made to upstream (WP-M-10 OI-7). No argument shall rely on training-data coverage | G3 limitation | REV | Not started |
| DSR-02 | Evaluation data shall be recorded on the reference configuration (vehicle, device revision, release software) by safety drivers under [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md), with full logs (`rlog`, `fcamera`, `ecamera`, `dcamera` where consented) | AIR-01…AIR-18 | REV of dataset manifest | Not started. No LionDriver data exists |
| DSR-03 | Every evaluation segment shall carry tags for each input-space dimension in §3 (road type, marking quality, curvature band, speed band, illumination, weather, calibration state, traffic density, driver attributes for DM) | AIR-09 | Sample audit | Not started |
| DSR-04 | Each stratum for which a claim is made shall hold enough data to support its acceptance criterion at the confidence level set in WP-V-02 (e.g., zero-failure demonstration of a 5 % event rate at 95 % confidence needs ≥ 59 independent scenario instances) | AIR-09, VT-nn | REV | Not started |
| DSR-05 | Evaluation data shall be independent of the model's training data: recorded after the model's upstream release date, and not uploaded to comma.ai servers, or with an upload log that lets independence be judged for later models | WP-M-10 §6.3 | REV of upload settings and logs | Not started |
| DSR-06 | A label specification shall define each ground-truth quantity (lane-centre offset, lane-departure events, lead presence/distance with the stock radar track as reference, phantom-braking events, DM gaze/eyes/phone labels) with its measurement method and tolerance | AIR-01…AIR-08 | REV | Not started |
| DSR-07 | At least 10 % **(TBC)** of human labels shall be double-annotated; agreement (Cohen's κ for classes, RMS difference for continuous values) shall meet thresholds set in the label specification | DSR-06 | Measurement | Not started |
| DSR-08 | Datasets shall be versioned by content hash, immutable once used for a verification record, and stored under LionDriver control ([WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md)) | AIR-24 | CM audit | Not started |
| DSR-09 | The dataset shall contain instances of every known triggering condition and known scenario of [WP-V-03](../06-validation/WP-V-03-sotif-known-scenarios.md) that is inside the ODD | AIR-14, WP-C-06 | Coverage report | Not started |
| DSR-10 | DM evaluation data shall cover day and night, low sun / glare, glasses and sunglasses, hats, a range of driver ages, skin tones and seating positions, with documented informed consent of every recorded person | AIR-07, AIR-08 | Coverage report, consent records | Not started |
| DSR-11 | Data used to choose runtime-monitor thresholds (AIR-14, AIR-18) shall be disjoint (by drive) from data used to verify them | AIR-14 | REV | Not started |
| DSR-12 | Simulated or synthetic data (MetaDrive, perturbed replays) shall be labelled as such, kept in separate datasets and never pooled into real-world rate estimates | WP-V-02 | REV | Not started |
| DSR-13 | Personal data (cabin video, faces and plates of third parties, location traces) shall be handled per the data-protection rules of [WP-M-09](../01-management/WP-M-09-cybersecurity-plan.md) and [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md) §11: access control, encryption at rest, retention limits, deletion on request | Privacy | Audit | Not started |

## 8. Traceability summary

| Parent | AIRs / DSRs |
|---|---|
| SG-01 (containment) | AIR-28 |
| SG-02 / SG-06 (take-over warning) | AIR-12, AIR-16, AIR-17, AIR-25, AIR-26 |
| SH-12 / DM (FSR-02.06…02.09, DMP-01…03) | AIR-07, AIR-08, AIR-15, AIR-27, DSR-10 |
| SH-01 / SH-02 lateral | AIR-01, AIR-02, AIR-09…AIR-11, AIR-14, AIR-18 |
| SH-03 / SH-04 / SH-06 longitudinal; SH-09 | AIR-03…AIR-06, AIR-29 |
| FM-01 / FM-02 / FM-03 / FM-04 / FM-05 / FM-09 | AIR-29 / AIR-12, AIR-25, AIR-30 / AIR-17 / AIR-16 / AIR-15 / AIR-14, AIR-18 |
| GAP-17 | AIR-12, AIR-25, AIR-30 |
| GAP-18 | AIR-29 |
| GAP-21 | AIR-15, AIR-27 |
| GAP-22 | AIR-14, AIR-16, AIR-19, AIR-20, AIR-23 |
| Evaluation data | DSR-01…DSR-13 |

Machine-readable entries go to [`trace/`](../trace/README.md) when WP-T-01 defines the schema.

## Open items

| ID | Item |
|---|---|
| OI-1 | Ask the WP-C-06 owner to reference AIR-nn from FI-01…FI-04, FI-18, FI-22, and the WP-C-07 owner to reference AIR-14/AIR-16/AIR-19 from FM-09/FM-04, so that the trace is bidirectional |
| OI-2 | Confirm or replace every **(TBC)** value through the target derivation in WP-V-02 and the B2 stock-TSS2 comparison |
| OI-3 | Confirm at G1 the WP-C-04 §7 proposal that the DM chain is QM; if rejected, update AIR-07, AIR-08, AIR-15, AIR-27 and DSR-10 |
| OI-4 | Decide the replacement for `pickle` loading (AIR-20) with the cybersecurity lead (WP-S-07) |
| OI-5 | Obtain the LFS objects and record compiled-artefact hashes (AIR-21; WP-M-10 OI-4) |
| OI-6 | Define the ground-truth method for lane-centre offset (AIR-01) without lidar or RTK: candidate is human annotation of lane-line pixels on sampled frames |
