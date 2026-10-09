# WP-W-10 ML Engineering

| Field | Value |
|---|---|
| Work product | WP-W-10 ML engineering: model requirements, data management, training route, testing, deployment |
| Standard reference | ASPICE 4.0 MLE.1 (ML requirements analysis), MLE.2 (ML architecture), MLE.3 (ML training), MLE.4 (ML model testing), SUP.11 (ML data management); ISO/PAS 8800:2024 (data, AI V&V, deployment, operation); ISO 21448:2022 §7, §10 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | QM / SOTIF (AI-1, AI-2); AI-3 integrity pending [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (AI safety lead) |
| Baseline | `8b8c6ae` (tinygrad submodule pin `d3f09c9`, not initialized in this checkout) |

## 1. Purpose and scope

This document carries out the ML engineering activities of the [AI safety plan (WP-M-10)](../01-management/WP-M-10-ai-safety-plan.md) for the AI components AI-1 (driving model), AI-2 (Chestnut big model, excluded from the reference configuration) and AI-3 (driver monitoring model) defined in [WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md).

LionDriver follows the **acquired, pre-trained model** route (WP-M-10 §5). MLE.3 "training" is replaced by acceptance of a received artefact. Everything else (requirements, architecture description, data management for evaluation data, testing, deployment and change control) is LionDriver's own work and is specified here.

Nothing in this document has been executed yet. The status table in §9 says what exists.

## 2. ML requirements (MLE.1)

The AI safety requirements AIR-01…AIR-30 and dataset requirements DSR-01…DSR-13 are in [WP-C-11 §6–7](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md). This section refines them into ML-level requirements that can be tested directly on the model and its pre/post-processing (MLR-nn). Each MLR traces to one AIR.

| ID | ML requirement | Parent | Test |
|---|---|---|---|
| MLR-01 | Lane-centre offset error metric (AIR-01) computed per stratum on the evaluation set meets the AIR-01 threshold | AIR-01, AIR-09 | VS-ML-03 |
| MLR-02 | Unrequested lane-departure count per 1000 km per stratum is reported with a 95 % upper confidence bound | AIR-02 | VS-ML-03 |
| MLR-03 | Lead detection latency and distance error versus the stock radar track meet AIR-03 | AIR-03 | VS-ML-03 |
| MLR-04 | First stable detection distance of stationary leads meets AIR-04 per speed band | AIR-04 | VS-ML-03, KS-05 |
| MLR-05 | Phantom-deceleration events per 1000 km are reported with a 95 % upper bound | AIR-05 | VS-ML-03 |
| MLR-06 | `hardBrakePredicted` TTC at assertion meets AIR-06 | AIR-06 | VS-ML-03 |
| MLR-07 | DM recall and false-alert rate per DM stratum meet AIR-07/AIR-08 | AIR-07, AIR-08 | VS-ML-06 |
| MLR-08 | Output change under each perturbation class stays within the VS-ML-04 bounds, or the monitor flags the frame | AIR-10 | VS-ML-04 |
| MLR-09 | Frame-to-frame curvature rate and lead toggling meet AIR-11 | AIR-11 | VS-ML-07 |
| MLR-10 | Standard deviations are calibrated per AIR-13 | AIR-13 | VS-ML-05 |
| MLR-11 | Monitor recall / false-flag rate meet AIR-14 | AIR-14 | VS-ML-08 |
| MLR-12 | Non-finite / range checks detect every injected bad output | AIR-16 | VS-ML-09 |
| MLR-13 | Inference time on the reference device meets AIR-17 at the 99.9th percentile under full onroad load | AIR-17 | VS-ML-10 |
| MLR-14 | Compiled artefact reproduces the ONNX reference within tolerance | AIR-22 | VS-ML-01 |
| MLR-15 | Tampered or unknown artefacts are rejected before deserialization | AIR-19, AIR-20 | VS-ML-11 |

## 3. ML architecture as received (MLE.2)

### 3.1 Data flow

```
 VisionIPC NV12 (narrow + wide road)                  VisionIPC NV12 (cabin)
        │ 2 frames, calib warp matrix                         │ dm warp matrix (fixed intrinsics)
        ▼                                                     ▼
 driving_warp_<WxH>_tinygrad.pkl  (GPU)              dm_warp_<WxH>_tinygrad.pkl
        ▼ 512×256 YUV                                         ▼ 1440×960 luma
 driving_tinygrad.pkl  ◀─ recurrent state (next_*)    dmonitoring_model_tinygrad.pkl
   + desire pulse, traffic convention, action_t               + calib (rpy)
        ▼ flat float vector                                   ▼ flat float vector
 output_slices (from pkl metadata) → Parser          output_slices → parse_model_output
        ▼                                                     ▼
 get_action_from_model (smoothing) / fill_model_msg   get_driverstate_packet (valid=True)
        ▼                                                     ▼
 modelV2, drivingModelData, cameraOdometry            driverStateV2
```

### 3.2 Model inputs and outputs

Detailed in [WP-C-11 §2.3–2.4](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md). Key structural facts for testing:

| Item | Value | Code |
|---|---|---|
| Driving model input image | 512×256, two consecutive frames per camera, two cameras | `common/transformations/model.py:10`; `SConscript:58-62`; `modeld.py:149, 193-195` |
| Output layout | Not fixed in code: slice table stored in the compiled artefact's metadata as a base64 pickled dict | `modeld.py:150`; `dmonitoringmodeld.py:33` |
| Plan | 33 time points (0–10 s, quadratic spacing) × 15 (position, velocity, acceleration, Euler, rate) with std | `constants.py:8-9, 40`; `parse_model_outputs.py:113` |
| Leads | 3 hypotheses selected from 2 MHP components, 6 time points (0–10 s) × 4 (x, y, v, a) with std, plus probabilities | `constants.py:11-12, 37, 49-55`; `parse_model_outputs.py:104-109` |
| Meta | engaged, gas/brake disengage, steer override, hard-brake 3/4/5 m/s² at 2…10 s; gas/brake press, blinkers at 0…10 s | `constants.py:75-88` |
| Action | `action[0]` = lateral acceleration-like quantity converted to curvature by `/max(1, v)²`; `action[1]` = acceleration | `modeld.py:65-67` |
| DM outputs | Per LHD/RHD: 6 face descriptors with 6 std, face/eye/blink/sunglasses/phone/sleep probabilities, wheel-on-right | `dmonitoringmodeld.py:73-96` |

### 3.3 Pre-processing

| Step | Implementation | Assurance note |
|---|---|---|
| Frame selection and synchronisation | Main and extra frames paired within 25 ms; > 10 ms mismatch only logged | `modeld.py:329-354`. No reaction to persistent desync (candidate for AIR-17 monitor) |
| Calibration warp | Warp matrix from `rpyCalib` and device intrinsics; zero matrix before first calibration | `modeld.py:367-375`. `modelV2.valid` is false until calibration is seen (`fill_model_msg.py:79`) |
| Warp kernel | tinygrad-compiled GPU kernel (`compile_warp.py`), separate artefact per camera resolution | `SConscript:54-71`. It is compiled software, not ML: verified by VS-ML-01 equivalence |
| Desire | Rising-edge pulse only | `modeld.py:197-200` |
| Input packing | All host inputs in one buffer, one upload | `modeld.py:169-186` |

### 3.4 Post-processing and smoothing

| Step | Implementation | Assurance note |
|---|---|---|
| Output parsing | MDN mean/std split, `safe_exp` clipped at 11 to avoid FLOAT16 overflow, sigmoid/softmax | `parse_model_outputs.py:4-18, 44-86`. A missing output raises `ValueError` (`:24-28`) |
| Hypothesis selection | Highest-weight hypothesis per lead slot | `parse_model_outputs.py:54-76` |
| Longitudinal smoothing | First-order, 0.3 s | `modeld.py:47, 69` |
| Lateral smoothing | None (`LAT_SMOOTH_SECONDS = 0.0`); curvature held below 0.3 m/s | `modeld.py:46, 70-73` |
| Stop decision | `should_stop(v_ego, accel)` | `modeld.py:68` |
| FCW | All of last 5 hard-brake-5 probs > thresholds and last 2 hard-brake-3 probs > 0.7 | `fill_model_msg.py:142-148`; `constants.py:29-30` |
| Confidence class | Rolling disengage score, green/yellow/red | `fill_model_msg.py:150-171`; no consumer |
| Non-finite check | AI-2 only | `modeld.py:210-211` |

### 3.5 Compile and load chain

```
 driving_supercombo.onnx (Git LFS)                      big_driving_tinygrad.pkl (Git LFS, pre-compiled by comma)
        │ scons: tinygrad_repo/examples/openpilot/compile_onnx.py
        │   device flags: DEV=QCOM IMAGE=1 FLOAT16=1 NOLOCALS=1 JIT_BATCH_SIZE=0 OPENPILOT_HACKS=1
        │   --out-of-band --benchmark-runs 1
        ▼
 driving_tinygrad.pkl  (pickle: JIT-captured kernels + metadata + weights out of band)
        │ runtime: load_oob() → tinygrad load_pickle(out_of_band=True)   (helpers.py:15-20)
        │          lower_and_compile() on the captured graph               (modeld.py:160-162)
        ▼
 GPU execution in modeld
```

| Stage | Tool / input | Identity recorded today | Issue |
|---|---|---|---|
| Source model | ONNX via Git LFS (`.gitattributes:5`) | LFS oid in pointer file | Only identity of the source; LFS objects not present in this checkout |
| Compiler | tinygrad at submodule pin `d3f09c9` (`.gitmodules` tracks `branch = master`, GAP-29) | Submodule SHA | Tool qualification open (GAP-34, [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md)); output depends on flags and host |
| Build trigger | SCons rebuilds when any tinygrad file, the ONNX or the command string changes (`SConscript:41-49`) | None | Compiled pkl hash not recorded |
| Load | `pickle` (code execution on load) | None | GAP-22; AIR-19/20 |
| Big model | Pre-compiled `.pkl`, included only with `INCLUDE_BIG_MODEL` (`tools/release/release_files.py:34`, `build_release.sh:62-65`) | LFS oid | No ONNX source; VS-ML-01 impossible; excluded (AIR-30) |

## 4. Training route: acquired pre-trained model (MLE.3 substitute)

LionDriver performs no training, fine-tuning or quantisation-aware retraining. MLE.3 is satisfied, to the extent possible, by an **acceptance procedure** for each model artefact proposed for a release:

| Step | Acceptance criterion | Evidence |
|---|---|---|
| A1 Identification | Artefact identified by LFS oid and size; upstream commit and commit message recorded; compiled artefact hash recorded (AIR-21) | Provenance record in the change request |
| A2 Provenance enquiry | Upstream asked for model card / training-data description (WP-M-10 OI-7); answer recorded, including "no answer" | WP-M-11 log |
| A3 Structural check | ONNX graph inputs/outputs and the `output_slices` table match what `modeld.py` / `parse_model_outputs.py` expect; no missing output (Parser raises otherwise) | VS-ML-02 |
| A4 Compile equivalence | VS-ML-01 passes | Test record |
| A5 Requirements-based evaluation | VS-ML-03…VS-ML-10 pass against WP-C-11 thresholds | Test records |
| A6 Regression against the previous pin | Model replay difference report reviewed; every behaviour change explained | VS-ML-12 |
| A7 Scenario re-validation | WP-V-03 known-scenario suite re-run for affected scenarios | WP-V-03 results |
| A8 Sign-off | AI safety lead and SOTIF lead sign the change request; residual issues listed | Change record (WP-P-02) |

An artefact that fails any step is not released. Because the model was not designed against WP-C-11, a failure leads to an ODD restriction, a runtime monitor, or keeping the previous model — never to "fixing the model".

## 5. Data management (SUP.11)

### 5.1 Data collected

| Dataset | Content | Source | Use |
|---|---|---|---|
| DS-EVAL-DRV | Full logs (`rlog`, road cameras) of engaged and disengaged driving on the reference vehicle | Safety-driver drives under [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md) | VS-ML-03, -05, -07, -08 |
| DS-EVAL-KS | Logs of known-scenario tests (closed course and public road) | [WP-V-03](../06-validation/WP-V-03-sotif-known-scenarios.md) | Scenario metrics, VS-ML-03 |
| DS-EVAL-DM | Cabin video + `driverStateV2` with scripted driver behaviours (look away, eyes closed, phone), recorded parked and on closed course | Consenting participants | VS-ML-06 |
| DS-TUNE | Disjoint subset for choosing monitor thresholds (DSR-11) | From DS-EVAL-DRV by drive | RM-3/AIR-14 tuning |
| DS-SIM | MetaDrive runs and perturbed replays, marked synthetic (DSR-12) | `openpilot/tools/sim`, perturbation scripts | VS-ML-04, exploration |
| DS-REF | Fixed input frames for equivalence and regression | Selected from DS-EVAL-DRV | VS-ML-01, VS-ML-12 |

### 5.2 Collection rules

1. Recorded only with the released LionDriver software and the pinned models of the configuration under test; the model hash is written into the dataset manifest (AIR-23 is not implemented yet, so the manifest is the only link).
2. Upload to comma.ai servers is disabled for evaluation drives (device not paired, or uploads disabled per [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md)); logs are copied to LionDriver storage over a local connection (DSR-05).
3. Each drive gets a drive sheet ([WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md) §10) recording weather, light, route, ODD conformance and events.

### 5.3 Labelling and ODD coverage tags

| Label / tag | Method | Reference |
|---|---|---|
| ODD tags per segment (road type, markings, curvature band, speed band, light, weather, traffic) | Drive sheet + reviewer annotation on 1-minute segments | DSR-03 |
| Lane-departure events | Automatic candidate detection (lane-line offset from `modelV2` near zero, steering override) then human confirmation on video | DSR-06 |
| Lead ground truth | Stock radar track (`radarState`/raw tracks) where available; human annotation where radar is absent | DSR-06 |
| Phantom braking | Candidate: `aEgo` < −2 m/s² while engaged with no radar/vision object within TTC 4 s; human confirmation | DSR-06 |
| DM labels | Two annotators mark gaze-on-road, eyes closed, phone use per 0.5 s on cabin video | DSR-06, DSR-07 |

Labelling guide, annotator training and agreement measurement follow DSR-07.

### 5.4 Storage, versioning and privacy

- Datasets are stored on LionDriver-controlled storage with a manifest listing every file and its SHA-256; a dataset version is immutable once referenced by a test record (DSR-08).
- Cabin video is personal data. It is recorded only with written consent from every occupant, kept encrypted at rest, accessible to named people only, and deleted on request or at the end of the retention period set in [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md) §11 (DSR-13).
- Road video containing third-party faces or plates is not published. Excerpts used in reports are blurred.

## 6. ML model testing (MLE.4)

### 6.1 Existing upstream capability and its limits

`openpilot/selfdrive/test/process_replay/model_replay.py` is a **regression comparison**, not requirements-based testing:

| Property | Fact | Code |
|---|---|---|
| Input | One route, one segment, frames 0–60 (3 s at 20 Hz) | `model_replay.py:23-26` |
| Reference | Logs downloaded from comma's `model_replay_master` bucket | `:34, 251` |
| Comparison | Exact on device; on PC tolerance 0.3 with most plan, lead, lane-line and road-edge fields ignored | `:258-291` |
| Pass/fail | In CI the result is forced to pass after posting a report (`failed = False`) | `:294-296` |
| Timing | Instant/average execution-time limits for `modelV2` and `driverStateV2` | `:37-40, 183-203` |
| Where it runs | comma Jenkins device pool `tizi-replay` | `Jenkinsfile:297-299` |

It cannot show that AIRs are met. It is reused as VS-ML-12 (regression), with a fork-owned route set and reference logs (D-03; [WP-M-08](../01-management/WP-M-08-sotif-plan.md) OI-5).

### 6.2 Test specification

| ID | Test | Method | Pass criterion | AIR / MLR |
|---|---|---|---|---|
| VS-ML-01 | Compile equivalence | Run DS-REF frames through (a) the compiled device artefact on the reference device and (b) an independent ONNX runtime on PC in FP32; compare every output field | Per-field tolerance from a documented FP16 error budget; no field outside | AIR-22, MLR-14 |
| VS-ML-02 | Structural acceptance | Parse ONNX graph; compare input/output names, shapes and `output_slices` with code expectations | Exact match; Parser raises no missing-output error on DS-REF | A3 |
| VS-ML-03 | Scenario-sliced performance | Replay DS-EVAL-DRV and DS-EVAL-KS through `modeld` (process replay with the pinned artefact) and compute AIR-01…AIR-06 metrics per ODD stratum | Each stratum meets its threshold; strata without enough data (DSR-04) are reported "insufficient" and not claimed | AIR-01…06, AIR-09 |
| VS-ML-04 | Robustness perturbations | Re-run DS-REF and a DS-EVAL sample with: calibration offsets (±INS-25 tolerance), exposure ±1 EV, Gaussian noise, HEVC re-encode at lower bitrate, synthetic lens occlusion (raindrop/dirt masks, 5 % and 10 % area), frame drop and frame duplication | Action deviation within bounds (initially: curvature Δ ≤ 0.002 1/m, accel Δ ≤ 0.3 m/s² **(TBC)**) **or** monitor flag raised | AIR-10 |
| VS-ML-05 | Uncertainty calibration | Compare published σ with observed error on DS-EVAL-DRV; reliability curves per stratum | AIR-13 thresholds | AIR-13 |
| VS-ML-06 | DM evaluation | DS-EVAL-DM through `dmonitoringmodeld` + `policy.py` in replay; strata: day, night, low sun/glare, clear glasses, sunglasses (IR-opaque and IR-transparent), hat brim, face partly out of view, phone low and high | Recall and false-alert rates per AIR-07/08 per stratum; time-to-alert matches `policy.py` timers (5/8/13 s, `policy.py:34-36`); behaviour with uncertain model matches the wheel-touch fallback (`policy.py:77-78`) | AIR-07, AIR-08, AIR-15 |
| VS-ML-07 | Temporal consistency | Metrics on DS-EVAL-DRV: curvature rate distribution in steady scenes, lead-existence toggle rate, recovery time after recurrent-state reset (forced reset in replay) | AIR-11, AIR-12 thresholds | AIR-11, AIR-12 |
| VS-ML-08 | Runtime monitor effectiveness | Monitor (once implemented) evaluated on DS-EVAL with known-TC segments labelled; thresholds tuned on DS-TUNE only | AIR-14 recall / false-flag targets | AIR-14, AIR-18 |
| VS-ML-09 | Output fault injection | Inject NaN, Inf, out-of-range values into each output field in replay and on device | Every injection detected; message invalid; take-over requested; no actuation from bad value | AIR-16, AIR-25 |
| VS-ML-10 | Timing under load | On the reference device, full onroad process set, logging and UI active, 1 h drive replay; record `modelExecutionTime`, frame drops | 99.9th percentile ≤ AIR-17 deadline; frame drop ≤ 1 % | AIR-17 |
| VS-ML-11 | Integrity at load | Modify one byte of each artefact; replace artefact with a different valid model; remove artefact | Load refused before deserialization; engagement prevented; event logged | AIR-19, AIR-20 |
| VS-ML-12 | Regression against previous pin | Fork-owned model replay over a route set (≥ 10 Corolla segments covering ODD strata) instead of one 3 s segment; CI must fail on unexplained differences | Report reviewed and signed (step A6) | AIR-24 |

### 6.3 Test environment

| Need | Status |
|---|---|
| Reference device for VS-ML-01/-10 | Not available as a test asset (D-04 HIL bench) |
| PC ONNX reference runtime | To be selected and classified ([WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md)) |
| Replay harness with dataset manifests | Upstream `process_replay.py` usable; route/frame fetching must be pointed at LionDriver storage instead of `openpilot/tools/lib/openpilotci.py` |
| Perturbation scripts | To be written; classified as test tools |

## 7. Deployment

| Topic | Rule | Current state |
|---|---|---|
| Pinning | Release manifest lists every model and warp artefact with SHA-256 (source and compiled) and the tinygrad commit and flags (AIR-21) | Not done. Only LFS pointers |
| Installation check | [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md) INS-18 compares on-device hashes with the release record | Procedure written; no hashes yet |
| Integrity at load | Hash verified before deserialization (AIR-19); unsafe deserialization only after verification (AIR-20) | **GAP-22: models are loaded with `pickle` and no hash check** (`helpers.py:15-20`, `modeld.py:150, 158-159`, `dmonitoringmodeld.py:30-33, 47-48`) |
| Runtime identity | Model identity in logs (AIR-23) | Only `modelV2.big` (`modeld.py:435`) |
| Big model | Not in reference releases (AIR-30) | Excluded unless `INCLUDE_BIG_MODEL` |
| On-device rebuild | SCons may recompile models on device if tinygrad files change (`SConscript:41-49`); release builds must ship pre-built artefacts whose hashes are in the manifest | To be enforced by release procedure ([WP-P-10](../07-supporting/WP-P-10-release-management.md)) |

## 8. Model change control (D-05)

Implements [WP-M-10 §9](../01-management/WP-M-10-ai-safety-plan.md#9-model-change-control-d-05) and [WP-M-08 §9](../01-management/WP-M-08-sotif-plan.md).

| Trigger | Required before release |
|---|---|
| New model artefact (any file under `openpilot/selfdrive/modeld/models/`) | Full acceptance A1–A8 (§4) |
| tinygrad pin or compile flags change | A1, A4, VS-ML-10, VS-ML-12; A5 if VS-ML-12 shows output change beyond tolerance |
| Change to `modeld.py`, `dmonitoringmodeld.py`, `parse_model_outputs.py`, `fill_model_msg.py`, `constants.py`, `helpers.py`, `modeld/SConscript` | Impact analysis ([WP-M-12 §7](../01-management/WP-M-12-impact-analysis.md)); VS-ML-12; tests for the changed function |
| Change to consumers of AI outputs (`radard`, `longitudinal_planner`, `controlsd`, `policy.py`) | Handled as SOTIF-relevant software change; affected VS-ML and WP-V-03 tests |
| Upstream sync touching any of the above | No automatic adoption (D-02); each model change is a separate change request |

Upstream history shows why this matters: the big model was replaced and reverted the same day (`0e0c7c7`, `f59056e`) and a "bump tinygrad" commit also rebuilt the big models (`d05c2d9`) ([WP-M-10 §2](../01-management/WP-M-10-ai-safety-plan.md)).

## 9. Current status

| Activity | ASPICE | Status at `8b8c6ae` | Gap / next step |
|---|---|---|---|
| ML requirements | MLE.1 | Drafted (WP-C-11, §2 here) | Confirm (TBC) values via WP-V-02 |
| ML architecture description | MLE.2 | Drafted (§3) | Review against ONNX graph once LFS objects are fetched |
| Training / acceptance | MLE.3 | Procedure defined (§4); never applied | Apply to the current pins as the first baseline |
| Data management | SUP.11 | Procedure defined (§5); **no data exists** | Storage, consent forms, label spec (WP-C-11 OI-6) |
| Model testing | MLE.4 | Specification (§6); **none executed**. Upstream model replay runs only on comma infrastructure and is forced to pass in CI | Fork-owned replay, perturbation scripts, reference device |
| Deployment integrity | — | **GAP-22 open**: no hashes, `pickle` loading | Implement AIR-19/20 (RM-1) |
| Runtime monitors RM-1…RM-5 | — | Not implemented except partial DM fallback and AI-2 NaN check | Specify in WP-S-03 / TSR-6xx |
| Change control | SUP.10 | Defined (§8) | Exercise on the first model-related change |
| Expected capability | — | MLE.1–4: CL0 today; target CL1 (T-12) | — |

## Open items

| ID | Item |
|---|---|
| OI-1 | Fetch the LFS objects, compile on the reference device and record source and compiled hashes (first application of §4) |
| OI-2 | Select and classify the independent ONNX reference runtime and the perturbation tools (WP-P-07) |
| OI-3 | Build fork-owned model replay (route set, LionDriver storage, CI that fails on unexplained differences) |
| OI-4 | Write the label specification and consent forms for DS-EVAL-DM |
| OI-5 | Decide the replacement for `pickle` loading or the verified-hash precondition (shared with WP-C-11 OI-4) |
| OI-6 | Define the FP16 error budget for VS-ML-01 tolerances |
