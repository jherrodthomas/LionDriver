# WP-O-04 Field Monitoring and Crash Reporting

| Field | Value |
|---|---|
| Work product | WP-O-04 Field monitoring (safety, SOTIF and AI) and crash reporting |
| Standard reference | ISO 26262-2:2018 §7 (safety management after release: field monitoring, anomaly handling); ISO 21448:2022 §13 (operation phase activities, field monitoring); ISO/SAE 21434:2021 §8 (cybersecurity monitoring, by reference to WP-O-05); ISO/PAS 8800:2024 (AI system operation and continuous assurance); NHTSA Standing General Order 2021-01 as amended (model, see §8); UL 4600 (informative: field feedback) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All safety goals (SG-01…SG-07); SOTIF; AI; CS interface |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

Field monitoring answers three questions while LD-SDA is in use:

1. Is any safety goal being violated, or close to being violated, in the field? (ISO 26262-2 §7)
2. Are there hazardous scenarios, triggering conditions or misuse that the SOTIF analysis did not foresee, and is the residual risk still within the acceptance criteria? (ISO 21448 §13; feeds [WP-V-04](../06-validation/WP-V-04-sotif-unknown-scenarios.md))
3. Are the ML models behaving as validated, inside their input space? (ISO/PAS 8800; feeds [WP-W-10](../05-software/WP-W-10-ml-engineering.md))

It applies from the first LionDriver public-road drive (development phase, under [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md)) and continues after release (gate G6). In the development phase the "field" is the safety-driver test fleet (one reference vehicle at the baseline); the process is the same, with shorter retrieval intervals.

Cybersecurity monitoring (vulnerability intake, threat intelligence) is in [WP-O-05](WP-O-05-cybersecurity-incident-response-updates.md). Events found here that may have a cybersecurity cause are passed to it.

## 2. What is monitored

### 2.1 Monitored events

Each event class has an ID (`MON-nn`), its source signal in the logs, and the safety question it answers. All signals listed are logged at the baseline; the source column says where they come from.

| ID | Event | Source signal (log service) | Code reference | Why it matters |
|---|---|---|---|---|
| MON-01 | Disengagement by driver (brake, cancel, steering override), with the 10 s before it | `selfdriveState` (enabled/active transitions), `carState` (brakePressed, steeringPressed, gasPressed, cruiseState) | `selfdrive/selfdrived/state.py`; `selfdrived.py:253-256` | Proxy for driver-perceived insufficiency (SOTIF); override effort (AOU-02) |
| MON-02 | Fault-triggered disengagement (any IMMEDIATE_DISABLE or SOFT_DISABLE event) | `onroadEvents`, `selfdriveState.alertType` | `selfdrived/events.py` | E/E or system fault reaching the driver (SG-02, SG-06) |
| MON-03 | `controlsMismatch` | `onroadEvents`; `pandaStates` (safetyModel, safetyParam, controlsAllowed, safetyRxChecksInvalid) | `selfdrived.py:328-339`; `events.py:919-922` | Host and envelope disagree: possible FFI or configuration fault (SG-01, GAP-09) |
| MON-04 | `relayMalfunction` | `pandaStates.faults`; `onroadEvents` | `opendbc/safety/safety.h:215-220, 372-380`; `selfdrived.py:341-342` | Harness or relay fault: SG-07 (stock PCS) at risk |
| MON-05 | Excessive actuation (latched) | `onroadEvents` (`excessiveActuation`), param `Offroad_ExcessiveActuation` | `selfdrived/helpers.py:16-53`; `selfdrived.py:305-310` | Direct indicator of a possible SG-01/SG-03/SG-04 violation |
| MON-06 | Panda TX blocks and safety violations | `pandaStates` (safetyTxBlocked, safetyRxInvalid, faults, heartbeatLost) | `panda/board/drivers/can_common.h:161-176`; `panda/board/main.c:182-213` | Envelope intervened: the QM stack commanded outside the envelope. Each one is a near-miss for SG-01/03/04 |
| MON-07 | Driver monitoring: alert levels 1–3, no-response forced deceleration, lockouts, DM uncertainty fallback | `driverMonitoringState`, `onroadEvents` (`driverDistracted1-3`, `driverUnresponsive1-3`, `tooDistracted`) | `selfdrive/monitoring/policy.py:28-44, 77-78, 398`; `selfdrived.py:217-239` | Effectiveness of the misuse measure (AOU-06); controllability basis |
| MON-08 | FCW and stock AEB activations | `onroadEvents` (`fcw`, `stockAeb`, `stockFcw`), `carState.stockAeb` | `selfdrived.py:441-445`; `events.py:470-498` | Near-miss indicator; SG-07 evidence that stock PCS still acts |
| MON-09 | Steering saturation; steer temporarily unavailable | `onroadEvents` (`steerSaturated`, `steerTempUnavailable*`) | `selfdrived.py:430-438`; `events.py:511-517, 619-625` | Demand above envelope: ODD/curvature insufficiency (SOTIF) |
| MON-10 | Inter-process communication and timing faults (`commIssue`, `processNotRunning`, `modeldLagging`, `selfdrivedLagging`) | `onroadEvents`; `managerState` | `selfdrived.py:352-390, 457` | FFI and timing on the QM SoC (GAP-16, GAP-23) |
| MON-11 | Calibration status changes (`recalibrating`, `invalid`) | `extrinsicsCalibration` | `locationd/calibrationd.py:150-167` | Mount disturbance (AOU-08) |
| MON-12 | `cruiseMismatch`, `canError`, `canBusMissing` | `onroadEvents` | `events.py:458-460, 928-946` | Known weak reactions (GAP-19); vehicle interface faults |
| MON-13 | Model anomalies: non-finite outputs clamped, large plan/action discontinuities, high model uncertainty (std), lead-probability flicker, frame drops, any big-model fallback (if Chestnut ever enabled) | `modelV2` (rlog only), `controlsState`, `carControl`, `cameraOdometry` | `controls/controlsd.py:140-147`; `modeld/modeld.py:46-77, 411-419`; `modeld/fill_model_msg.py:142-147, 179` | AI/SOTIF: out-of-distribution or degraded model behaviour (GAP-17, GAP-22) |
| MON-14 | Crash or near-miss reported by the driver, or detected (high deceleration in IMU / `carState.aEgo`, airbag-related CAN signals if available, flag button) | `userBookmark`; `accelerometer`; `carState`; driver report | `system/loggerd/loggerd.cc:198-285` (bookmark preserves segment) | Safety goal violation evidence; SGO-style reporting (§8) |
| MON-15 | Use outside the ODD (speed, road type, weather, night) while engaged | `carState.vEgo`, GPS, model road-edge and lane outputs, time of day; `speedTooHigh` event | `events.py:989-996` | Misuse frequency (AOU-06, [WP-O-03](WP-O-03-user-information-safety-warnings.md) UI-10) |
| MON-16 | Configuration drift: software commit, panda firmware signature, model hashes, parameters, `carFw`, fingerprint fuzzy flag | `initData`, `carParams`, `pandaStates`, params snapshot | `selfdrive/car/card.py:141-150, 195-201` | Field units must equal the released reference configuration ([WP-O-01](WP-O-01-installation-and-provisioning-control.md) SPC-04…SPC-07) |

### 2.2 Exposure data (denominators)

KPIs are rates, so exposure is recorded too: engaged distance and time, total driven distance and time, split by road type, speed band, day/night and weather where it can be derived (`carState.vEgo`, GPS, `selfdriveState.enabled`). Without exposure, field counts cannot be compared with the SOTIF validation targets ([WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md)).

## 3. Data sources and data path

### 3.1 What the device records (inherited)

| Artefact | Content | Notes |
|---|---|---|
| `rlog` | All logged services at full rate (services marked loggable in `cereal/services.py`), one file per 60 s segment (`system/loggerd/config.py:7`) | Contains `modelV2`, `pandaStates`, `carState`, `carControl`, `onroadEvents`, `driverMonitoringState`, GPS |
| `qlog` | Decimated subset (third field in `cereal/services.py`; e.g. `onroadEvents` every message, `carState` 1 in 10; `modelV2` **not** in qlog) | Enough for event detection, not for model analysis |
| `fcamera.hevc`, `ecamera.hevc` | Road and wide-road camera video | Large |
| `dcamera.hevc` | Driver camera video, only if `RecordFront` is set (`system/loggerd/loggerd.h:115-116`) | Personal data |
| `qcamera.ts` | Low-resolution road video | |
| Storage | `/data/media/0/realdata/` (`common/hardware/hw.py:15-21`); oldest segments deleted when free space < 5 GB or < 10% (`system/loggerd/deleter.py:11-12`), except bookmarked segments and their two predecessors (`deleter.py:16-43`) | Data is lost if not retrieved in time |

### 3.2 Where data goes by default, and why LionDriver needs its own path

The inherited `uploader` sends `qlog`, `qcamera` and (on request) `rlog` and video to **comma.ai's servers**: it asks `api.commadotai.com` (`openpilot/common/api.py:8`) for an upload URL per file (`system/loggerd/uploader.py:140-161`). Remote retrieval of any file is also possible through athena (`system/athena/athenad.py`, GAP-27). This means that, by default:

- LionDriver has **no access** to the data from its own installations;
- personal data (video, location, possibly driver video) of LionDriver users is sent to a third party that has no agreement with LionDriver ([WP-M-11](../01-management/WP-M-11-upstream-and-supplier-management.md));
- the back end is outside LionDriver's control and untrusted (AOU-11, T-11).

### 3.3 LionDriver data path (proposed)

| Phase | Path | Controls |
|---|---|---|
| Development (now → G5) | **Manual retrieval.** After each test day, the maintainer copies the routes from the device (USB or local network SSH with LionDriver keys, offroad only) to LionDriver-controlled encrypted storage. comma upload disabled (device not paired, or upload disabled per OI-1) | Retrieval log per route; checksum of copied files; device storage checked for space before each test day |
| After release (G6) | Either (a) continue manual retrieval at service intervals plus driver-triggered reports, or (b) a LionDriver upload endpoint. Option (b) needs a compatible API host (the uploader's host is overridable through `API_HOST`, `common/api.py:8`, but the upload-URL protocol and device authentication must be re-implemented), a cybersecurity assessment ([WP-C-09](../02-concept/WP-C-09-tara.md)) and user consent | Decision OI-2 |

Minimum data set retrieved for every engaged route: `qlog` and `rlog` for all segments; video only for segments with a monitored event (§2.1) or a bookmark.

### 3.4 Privacy and data protection

| Rule | Detail |
|---|---|
| PRV-01 | Collect only what §2 needs. Driver-camera recording (`RecordFront`) off by default; enabled only for development-phase safety drivers who consent, when DM investigation needs it |
| PRV-02 | Users are told what is recorded, where it goes and how to delete it ([WP-O-03](WP-O-03-user-information-safety-warnings.md) UI-43) before first use |
| PRV-03 | Stored data is encrypted at rest, access limited to named project roles, access logged |
| PRV-04 | Retention: event-related data kept for the life of the release plus the period in [WP-P-04](../07-supporting/WP-P-04-documentation-management.md); other data deleted after analysis (target 90 days) |
| PRV-05 | Location data and VIN are pseudonymised in analysis datasets and in any published report |
| PRV-06 | Applicable US state privacy law and any data-protection obligations are to be confirmed (OI-3) |

## 4. Processing and triage

### 4.1 Pipeline

1. **Ingest**: copy, checksum, register route ID, vehicle, software baseline (from `initData` / `carParams`).
2. **Automatic event extraction**: script scans `qlog`/`rlog` for MON-01…MON-16 and writes an event table (route, time, event, context signals). Not written yet (OI-4).
3. **Configuration check**: compare MON-16 with the release record; a mismatch is an event in itself.
4. **Review**: the safety manager (or delegate) reviews every event in the triage classes below within the stated time.
5. **Problem report**: open an issue under [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md) with category and severity, linking route and time.
6. **Feed-forward** to the analyses (§6).

### 4.2 Triage classes

| Class | Events | Review target after retrieval | Default WP-P-03 severity |
|---|---|---|---|
| T1 Immediate | Crash or near-miss while engaged or within 30 s after disengagement (MON-14); excessive actuation (MON-05); `controlsMismatch` (MON-03); `relayMalfunction` (MON-04); configuration drift on a safety-relevant item (MON-16) | Same day | S-1 until analysed |
| T2 Priority | Envelope TX blocks while engaged (MON-06); stock AEB activations while engaged (MON-08); DM no-response or lockout (MON-07); fault disengagements (MON-02); model non-finite outputs (MON-13) | 5 working days | S-2 until analysed |
| T3 Statistical | Driver disengagements, FCW, steering saturation, DM level 1–2, calibration changes, out-of-ODD use, timing faults | Monthly trend review | S-3/S-4, or none if within expected rates |

A T3 event becomes T2 when its rate exceeds the threshold in §5 or a new pattern (location, condition, software baseline) appears.

## 5. KPIs and thresholds

Thresholds are placeholders until the SOTIF validation targets proposed in [WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md) §4 (VT-01…VT-13, Draft, not yet confirmed) are agreed and baseline rates from development driving exist (OI-5). A KPI breach is a problem report, not an automatic field action.

| KPI | Definition | Initial threshold (placeholder) | Linked claim |
|---|---|---|---|
| K-01 | Crashes while engaged per engaged distance | 0 tolerated without T1 investigation; rate compared with VT targets | G0, G2 |
| K-02 | Excessive-actuation latches per 1,000 engaged km | 0 (any occurrence → T1) | SG-01, SG-03, SG-04 |
| K-03 | `controlsMismatch` / `relayMalfunction` per 1,000 engaged hours | 0 (any occurrence → T1) | SG-01, SG-07 |
| K-04 | Envelope TX blocks while engaged per engaged hour | Baseline from development drives; > 2× baseline → T2 | SG-01, SG-03, SG-04 |
| K-05 | Safety-relevant driver disengagements (driver takeover judged necessary on review) per 100 engaged km | Baseline; trend | SOTIF residual risk |
| K-06 | DM level-3 alerts and lockouts per engaged hour, per driver | Baseline; trend per driver | AOU-06; misuse |
| K-07 | Engaged time outside ODD / total engaged time | < 1% (placeholder) | AOU-06, UI-10 |
| K-08 | Fault disengagements (soft + immediate) per engaged hour | Baseline | SG-02, SG-06 |
| K-09 | Stock AEB activations while engaged, each reviewed for whether LD-SDA contributed | Review all | SG-07, H-06 |
| K-10 | Model anomaly events per engaged hour (MON-13) | Baseline | G3 (AI) |
| K-11 | Field units on non-released configuration | 0 | All |
| K-12 | Data coverage: share of engaged distance whose logs were retrieved | ≥ 95% | Validity of all KPIs |

## 6. Feeding the analyses

| Finding type | Goes to | Action |
|---|---|---|
| Potential safety goal violation, E/E fault | [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md) (cat-fusa), [WP-C-03](../02-concept/WP-C-03-hara.md) / [WP-A-04](../08-analyses/WP-A-04-system-fta-fmea.md) review | Check whether the hazard, rating or failure mode was covered; update analyses |
| New hazardous scenario or triggering condition | [WP-V-04](../06-validation/WP-V-04-sotif-unknown-scenarios.md) (unknown → known), [WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md) (new TC/FI), [WP-V-03](../06-validation/WP-V-03-sotif-known-scenarios.md) (add to scenario catalogue) | Add scenario; evaluate; decide functional modification ([WP-C-07](../02-concept/WP-C-07-sotif-functional-modifications.md)) or ODD restriction |
| New misuse pattern | [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md), [WP-O-03](WP-O-03-user-information-safety-warnings.md) | Update misuse analysis and user information; consider technical measure |
| Model anomaly | [WP-W-10](../05-software/WP-W-10-ml-engineering.md), [WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md) | Add to model test set (where data rights allow); review input-space definition |
| AoU found not to hold (e.g. EPS behaviour, PCS not acting) | [WP-C-01](../02-concept/WP-C-01-item-definition.md) §7, [WP-C-03](../02-concept/WP-C-03-hara.md) | Re-rate affected hazardous events (⚠ ratings) |
| Possible cyber cause | [WP-O-05](WP-O-05-cybersecurity-incident-response-updates.md) | Incident response |
| Counter-evidence to the safety case | [WP-K-01](../10-safety-case/WP-K-01-safety-case.md) defeater list | Add or update defeater |

The SOTIF "unknown scenario" discovery rate (new scenarios per 1,000 engaged km) is reported to WP-V-04 monthly as an input to the residual-risk argument.

## 7. Reviews and reporting inside the project

| Report | Content | Frequency | Audience |
|---|---|---|---|
| Field monitoring summary | KPIs, T1/T2 events and status, new scenarios, data coverage | Monthly (development: after each test week) | Safety manager, SOTIF lead, AI lead; filed under `assurance/09-production-operation/reports/` |
| Gate input | Summary since last gate | Each gate | Gate review ([WP-M-02 §10](../01-management/WP-M-02-safety-plan.md#10-progress-tracking-and-gate-reviews)) |
| Safety case update | Changes to defeaters and evidence status | Quarterly and on T1 closure | [WP-K-01](../10-safety-case/WP-K-01-safety-case.md) |

## 8. External reporting obligations

| Obligation | Applicability to LionDriver | Action |
|---|---|---|
| NHTSA Standing General Order 2021-01 (as amended): crash reporting for vehicles equipped with L2 ADAS | The SGO is addressed to named manufacturers and operators. Whether an open-source aftermarket retrofit project falls under it is **not established** (OI-6). LionDriver uses its reporting criteria and timelines as a **model** for internal reporting (T-13) | Record every crash with LD-SDA engaged at any time within 30 s before the crash in the SGO data fields (time, location, speeds, engagement state, injuries, airbag, VRU involvement, damage); legal review of applicability before release |
| Safety defect reporting (49 CFR Part 573) for motor vehicle equipment | Applicability to a software/hardware retrofit distributed by an individual is to be confirmed (OI-6) | Legal review |
| Police/insurance reporting | Driver's legal obligation | Covered in user information |
| Disclosure to comma.ai of upstream defects | Voluntary; useful for upstream fixes | Through [WP-M-11](../01-management/WP-M-11-upstream-and-supplier-management.md) channels, without personal data |
| Vulnerability disclosure | Per [WP-O-05](WP-O-05-cybersecurity-incident-response-updates.md) | — |

## 9. Field action criteria

The safety manager decides field actions. The criteria below trigger a decision; they do not replace judgement.

| Action | Trigger (any of) |
|---|---|
| **Stop-use notice** (all users of the affected release stop engaging LD-SDA immediately; [WP-O-03](WP-O-03-user-information-safety-warnings.md) UI-42) | A crash or near-miss where analysis shows, or cannot exclude, that LD-SDA contributed through a safety goal violation; any reproducible excessive actuation; any `relayMalfunction` or PCS suppression traced to a systematic cause; a confirmed exploitable vulnerability with safety impact (from WP-O-05); field units found on a non-released safety-relevant configuration that cannot be corrected remotely |
| **Restriction notice** (narrow the ODD or disable a feature, e.g. Experimental Mode) | A SOTIF KPI exceeds its threshold in a specific condition; a new triggering condition found with no immediate fix |
| **Corrective release** | Any S-1/S-2 problem with a verified fix, released per [WP-P-10](../07-supporting/WP-P-10-release-management.md) |
| **Information update** | New limitation or misuse pattern without technical fix |

Every field action is recorded with: trigger, affected releases and installations, decision, notification method and date, confirmation of receipt per user, closure evidence. The notification channel must reach every installation within 24 hours (to be established, OI-7). Until then, the number of installations is limited to those the maintainer can reach directly.

## 10. Roles

| Role | Responsibility |
|---|---|
| Safety manager | Owns this process; T1 review; field action decision |
| SOTIF lead | T3 trends, unknown-scenario feed, KPI thresholds |
| AI/ML safety lead | MON-13 review; model-related feed |
| Cybersecurity manager | Hand-over of events with possible cyber cause |
| Maintainer | Data retrieval, storage, extraction tooling |
| Drivers | Flag and report events ([WP-O-03](WP-O-03-user-information-safety-warnings.md) UI-39/UI-40); do not delete routes |

## 11. Current capability (honest status)

| Capability | Status at `8b8c6ae` |
|---|---|
| Event signals logged on the device | Available (inherited) |
| LionDriver access to field data | **Not available**: default upload goes to comma.ai; no LionDriver path |
| Event extraction tooling | Not available (OI-4) |
| KPI thresholds | Not defined (OI-5) |
| Notification channel for field actions | Not available (OI-7) |
| Field monitoring records | None (no LionDriver field operation yet) |

## 12. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Decide how comma upload and athena are disabled for LionDriver installations (unpaired device, configuration change, or code change) and verify no data leaves the device unintentionally | G1 (before LionDriver public-road testing) |
| OI-2 | Decide the post-release data path (manual vs. LionDriver endpoint) | G5 |
| OI-3 | Privacy and consent review (data categories, consent text, retention) | G1 |
| OI-4 | Write the event-extraction script for MON-01…MON-16 over qlog/rlog | G1 (for development driving) |
| OI-5 | Set KPI thresholds from validation targets and development-drive baselines | G4 |
| OI-6 | Legal review of SGO and Part 573 applicability | G5 |
| OI-7 | Establish a field-action notification channel with confirmed receipt | G5 |
| OI-8 | Define crash detection criteria from IMU/`carState` for MON-14 (automatic flagging) | G4 |
