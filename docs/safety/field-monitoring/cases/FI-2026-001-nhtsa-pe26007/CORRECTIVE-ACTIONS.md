# FI-2026-001 — Corrective & Preventive Actions

Every action traces to a root cause (RC) in [`RCA.md`](RCA.md) and a hazard (HZ) in [`../../HAZARD-LOG.md`](../../HAZARD-LOG.md).

Control tiers (PROCESS §5.7): **1** Eliminate · **2** Inherent design · **3** Safety mechanism · **4** Warning/HMI · **5** Information/procedure.

Each CA gets its own `CA-NNN.md` (from `templates/CORRECTIVE-ACTION.md`) when it moves to **Approved**.

## Summary

| ID | Title | RC | HZ | Tier | Status |
|---|---|---|---|---|---|
| CA-001 | Interlock: never disable stock PCS/AEB in an assured configuration | RC-01 | HZ-002 | 1 | **Implemented**: software verified; panda layer and vehicle check open |
| CA-002 | Stopped / slow in-lane vehicle scenario suite with acceptance criteria | RC-02, RC-03, RC-06 | HZ-001, HZ-003 | 2 (V&V) | **Phase 1 done** (SIL, idealized perception); phase 2 open |
| CA-003 | Perception evaluation on emergency vehicles and atypical stationary targets | RC-06 | HZ-001 | 2 | Proposed |
| CA-004 | Stationary-target performance requirement and braking-authority study | RC-02 | HZ-001, HZ-006, HZ-007, HZ-008 | 2 | **Study complete**: decision pending approval |
| CA-005 | Independent forward-collision monitor (radar-based) for FCW | RC-03 | HZ-003 | 3 | Proposed |
| CA-006 | Hazard-timed driver monitoring escalation | RC-04 | HZ-004 | 3 / 4 | Proposed |
| CA-007 | Event data capture for safety-relevant events | RC-05 | HZ-005 | 3 | Proposed |
| CA-008 | Assured-configuration identity and fork-parameter control | RC-05 | HZ-005 | 2 | **Implemented** (identity, check, log); UI display open |
| CA-009 | Update limitations, operator briefing and test-driver protocol | RC-02, RC-04 | HZ-001, HZ-004 | 5 | Proposed |
| CA-010 | Measure stock PCS on the 2020 Corolla in cut-out and lead-braking scenarios with openpilot longitudinal engaged | RC-02 | HZ-001, HZ-008 | V&V | Proposed (from CA-004) |
| CA-011 | Relaxed following distance by default in the assured configuration | RC-02 | HZ-008 | 2 | **Implemented** (approved 2026-10-10); deviations flagged by CA-008 |
| CA-012 | Operating-domain speed cap for openpilot longitudinal, from the verified confirmation range | RC-02, RC-06 | HZ-001 | 2 | Proposed (from CA-004); waits on CA-003 |
| PA-01 | Seed the first HARA from the hazard log | — | all | — | Proposed |
| PA-02 | Create the SOTIF triggering-condition catalog (TC-01…TC-06) | — | HZ-001 | — | Proposed |
| FA-01 | Retrieve the NHTSA ODI resume for PE26007 and update REPORT §2 | — | — | — | Open |

---

## CA-001 — Interlock: never disable stock PCS/AEB in an assured configuration

- **Root cause:** RC-01. On radar-ACC Toyotas, alpha longitudinal silences the radar ECU and sends `PCS_OFF = 1`. The independent OEM barrier disappears.
- **Change:**
  1. **Requirement LD-FSR-001:** "In any LionDriver assured configuration, openpilot shall not disable, suppress or override the stock OEM AEB/PCS function."
  2. Implement a configuration interlock: refuse `DISABLE_RADAR` / alpha longitudinal on any platform where it removes stock AEB, unless a separate safety case for a replacement AEB has been approved. Candidate location: where the alpha-long toggle is read and passed to `get_car()` (`openpilot/selfdrive/car/card.py:93-101 @ 8b8c6ae`). For defense in depth, a panda safety-mode check that rejects the UDS CommunicationControl disable-TX request to the radar address `0x750`.
  3. Record per platform whether stock AEB is preserved under openpilot longitudinal. Make this a gate for adding any vehicle to the assured scope (README "Future vehicle configurations").
- **Note for the reference vehicle:** the 2020 Corolla (`TOYOTA_COROLLA_TSS2`) is camera-ACC and does **not** take the `DISABLE_RADAR` path today. CA-001 stops it from ever getting there (variant drift, future platforms, forks).
- **New hazards from the change:** none expected. Radar-ACC Toyotas lose openpilot longitudinal (an availability loss, not a safety loss).
- **Acceptance criteria:**
  1. Unit test: with the interlock enabled, setting the alpha-long toggle on a `RADAR_ACC` platform leaves `openpilotLongitudinalControl = False` and no `DISABLE_RADAR` flag.
  2. Panda safety test: a CommunicationControl disable-TX to `0x750` is blocked.
  3. Bench or vehicle check on one radar-ACC Toyota: PCS stays available (confirms the vehicle-level effect behind RC-01).
- **Verification:** unit + safety replay tests in CI; one documented bench/vehicle check.

### CA-001 implementation record (2026-10-10)

**Scope decision.** Alpha longitudinal is blocked on **every** vehicle, not just radar-ACC Toyotas. Across the opendbc car ports at `229dc70`, alpha longitudinal is the path that hands longitudinal control from the stock system to openpilot. On several brands (Toyota radar-ACC, Honda Bosch, Hyundai) that path disables the stock radar/ADAS ECU. Upstream's own UI warns that it "may disable Automatic Emergency Braking (AEB)". No platform has evidence that stock AEB survives, so the strongest control (tier 1, eliminate) applies to all of them. 90 of 254 platforms would otherwise run alpha longitudinal. Platforms where openpilot longitudinal is the **default**, such as the 2020 Corolla, are unaffected.

**Implementation:**

| Layer | Change | File |
|---|---|---|
| 1. Request gate | The alpha-long request is refused before it reaches `get_car()`, and the param is cleared so the UI and `ui_state` stay consistent | `openpilot/selfdrive/car/stock_aeb_interlock.py` (`alpha_long_allowed`), `openpilot/selfdrive/car/card.py` |
| 2. Postcondition check | After fingerprinting, `stock_aeb_preserved(CP)` checks that the car interface did not enable openpilot longitudinal on an alpha-capable platform. Every port only does that when alpha was requested. If the check fails, card forces passive mode (`noOutput` safety) and **skips `CI.init()`**, which is where ECU knockouts such as the Toyota radar disable happen | `stock_aeb_interlock.py`, `card.py` |
| 3. HMI | The alpha-long toggle is hidden in both UIs, and the stored param is removed | `openpilot/selfdrive/ui/layouts/settings/developer.py`, `openpilot/selfdrive/ui/mici/layouts/settings/developer.py` |
| Simulator exemption | Allowed only when **both** `SIMULATION` and `NOBOARD` are set. `NOBOARD` stops pandad, so there is no path to a vehicle CAN bus. The simulator bridge needs openpilot longitudinal on its Honda fingerprint | `stock_aeb_interlock.py` (`is_simulation`) |

Process replay is unaffected: it builds the car interface itself and passes it to `Car`, so the vehicle-path checks do not run there.

**Verification evidence** (`openpilot/selfdrive/car/tests/test_stock_aeb_interlock.py`, 516 tests):

| AC | Evidence | Result |
|---|---|---|
| AC-1 | `test_radar_acc_toyota`: with the toggle requested, the 2022 RAV4 gets `openpilotLongitudinalControl = False` and no `DISABLE_RADAR`. Without the interlock it gets `DISABLE_RADAR` and the postcondition check trips | **Pass** |
| AC-1 (fleet) | `test_preserved_without_alpha_long`: every one of 254 platforms passes the postcondition check under the interlock. `test_detects_alpha_long`: every platform that would run alpha long is caught | **Pass** |
| AC-1 (reference vehicle) | `test_reference_vehicle_keeps_openpilot_long`: the 2020 Corolla keeps openpilot longitudinal and the radar ECU untouched | **Pass** |
| AC-1 (sim) | Exemption needs both env vars; either one alone is refused | **Pass** |
| Test effectiveness | Mutation check: with the request gate made to always allow, 94 tests fail | **Pass** |
| AC-2 | Panda safety-mode block on UDS CommunicationControl to `0x750` | **Open.** The safety modes live in the `opendbc_repo` submodule, which tracks `commaai/opendbc`. Needs a LionDriver fork of opendbc. Software layers 1–3 cover the risk meanwhile |
| AC-3 | Bench/vehicle check that PCS stays available on a radar-ACC Toyota | **Open.** Needs hardware |

**Residual risk.** A fork, or someone with code access, can still edit `stock_aeb_interlock.py` or set both simulator env vars on a device. Both put the build outside the assured configuration (CA-008 will make that visible in logs). AC-2 adds the independent firmware-level layer.

## CA-002 — Stopped / slow in-lane vehicle scenario suite

- **Root causes:** RC-02, RC-03, RC-06. Covers them even while RC-06 is unconfirmed.
- **Change:** build a SIL/replay scenario suite (and later HIL / closed-course) for TC-01…TC-06. Parameters:

  | Parameter | Values |
  |---|---|
  | Ego speed | 40, 60, 80, 100, 120 km/h |
  | Target | Stopped passenger car; stopped truck; emergency vehicle with lights; slow vehicle at 20% of ego speed |
  | Reveal | Visible from > 250 m; cut-out reveal at 120 / 80 / 50 m |
  | Lateral offset | 0, 0.5, 1.0, 1.5 m |
  | Conditions | Day, night, low sun / glare, rain |
- **Metrics (log for every run):** first-detection range (`lead_prob > 0.5`); radar-match range; FCW onset TTC; minimum TTC; impact speed; peak decel.
- **Acceptance criteria (initial — set formally by CA-004):**
  1. **Visible-from-range cases:** no collision at any speed ≤ 120 km/h with -3.5 m/s² available. First detection ≥ required stopping distance + 20% margin (§3.1 of the RCA).
  2. **Cut-out reveals:** FCW at TTC ≥ 2.0 s whenever physically possible. Impact-speed reduction recorded and trended.
  3. Every failure becomes a permanent regression case.
- **SPIs:** SPI-02, SPI-03.

### CA-002 phase 1 record (2026-10-10)

**Delivered:** a closed-loop SIL suite in `openpilot/selfdrive/test/stopped_vehicle/`. It runs the real `RadarD` lead selection and the real `LongitudinalPlanner` / MPC for the 2020 Corolla (TSS2), and is collected by `tools/test_runner.py`. Results and limitations: [`evidence/CA-002-BASELINE-RESULTS.md`](evidence/CA-002-BASELINE-RESULTS.md).

**AC-2 made precise:** an AC on a cut-out that cannot physically be avoided has to be about the warning, not the outcome. So: no collision when the reveal gap ≥ the required stopping distance. If a collision occurs, an FCW must fire, at TTC ≥ 2.0 s whenever the reveal leaves ≥ 2.5 s.

| Grid item | Phase 1 (SIL, idealized perception) | Phase 2 |
|---|---|---|
| Ego speed 40–120 km/h | ✔ | ✔ |
| Stopped / slow (20%) target | ✔ | Truck, emergency vehicle (needs perception, CA-003) |
| Visible from range; cut-out at 120/80/50 m | ✔ | Cut-out from a real following state |
| Radar-only stationary target | ✔ (`expectedFailure`, known gap) | — |
| Lateral offset 0.5–1.5 m (TC-06) | — | Needs perception / simulator |
| Day, night, glare, rain | — | Needs perception / simulator |
| Detection latency and flicker; PID and brake ramp | — | Logged model outputs; HIL |

**Results:** AC-1 and AC-2 pass with idealized perception, 36 tests passed and 1 expected failure. A mutation check with braking weakened to -2.5 m/s² makes 18 tests fail.

**What the results mean for the RCA:**
- RC-02 / FTA B3 (a radar-only stationary target is ignored above 4 m/s) moves from **Verified design** to **confirmed in SIL**.
- Cut-out collisions happen exactly where the reveal gap is shorter than the stopping distance at -3.5 m/s². That gives CA-004 its quantitative case.

**Remaining for closure:** phase 2 rows above, and the CA-004 requirement (which replaces the initial AC thresholds).

## CA-003 — Perception evaluation on emergency vehicles and atypical stationary targets

- **Root cause:** RC-06 (hypothesis).
- **Change:** curate an evaluation set (public datasets plus LionDriver drives) of emergency scenes, stopped trucks, stalled and crash-damaged cars, and queue tails. Measure driving-model lead recall vs. range, by lighting condition. Feed the results to CA-002 targets. Report gaps upstream.
- **Acceptance criteria:** recall-vs-range curve published per category. Confirm or refute RC-06 with data. Any category below the CA-004 range requirement opens a new CA (data, model or operating-domain restriction).

## CA-004 — Stationary-target performance requirement and braking-authority study

- **Root cause:** RC-02.
- **Change:**
  1. **Requirement LD-SOTIF-001 (draft):** "With longitudinal control engaged and a stationary or slow vehicle in the ego lane visible from at least D_req(v), the system shall decelerate to avoid collision. D_req(v) is the stopping distance at the configured braking authority, plus latency and a margin."
  2. **Study:** compare three options:
     - (a) keep -3.5 m/s² and require detection at D_req;
     - (b) an *emergency-only* higher deceleration authority (e.g. down to -6…-8 m/s²) gated on high-confidence fused (vision + radar) detection and imminent TTC;
     - (c) restrict the operating domain (speed cap) for longitudinal control.
     Option (b) changes panda safety limits (`toyota.h:208-209`) and the car port (`values.py:43`). It needs its own impact analysis because of **HZ-006 (phantom braking)** and **HZ-007 (rear-end collision)**, plus checks of Toyota actuator behavior and limits.
- **Acceptance criteria:** decision recorded with a quantitative argument. Requirement baselined. CA-002 thresholds updated to match.

### CA-004 study record (2026-10-10)

Full study: [`evidence/CA-004-BRAKING-AUTHORITY-STUDY.md`](evidence/CA-004-BRAKING-AUTHORITY-STUDY.md).

- **Result:** an emergency-only -8 m/s² layer (option b) halves the required confirmation range: 166 → 79 m at 120 km/h. It cuts cut-out collisions from 11 to 5 of 25. But it is blocked by four open unknowns:
  - whether the Toyota ACC interface can actuate it (U1);
  - false-trigger rate (U3);
  - integrity and FMVSS 127-style expectations (U5);
  - and it may duplicate the stock PCS, which has not been measured yet (U2).
- **New finding:** at the standard following distance, a lead braking at 4 m/s² from ≥ 100 km/h out-brakes the -3.5 m/s² limit (TC-07, HZ-008).
- **Proposed decision:** adopt LD-SOTIF-001 with the simulated D_req values. Add CA-010 (measure stock PCS), CA-011 (relaxed following by default) and CA-012 (speed cap once CA-003 reports). Keep option (b) as a candidate, to reopen if CA-010 shows stock PCS falls short.
- **Approval:** pending, safety manager.

## CA-010 — Measure stock PCS with openpilot longitudinal engaged

- **Root cause / hazards:** RC-02 · HZ-001, HZ-008. Resolves CA-004 U2.
- **Change:** closed-course tests on the 2020 Corolla (TSS2) with soft targets. Run the CA-002 / CA-004 cut-out (S2) and lead-braking (S3) scenarios, with openpilot longitudinal engaged and no driver braking. Record PCS warning time, PCS braking onset and peak deceleration, and impact speed.
- **Acceptance criteria:** results tabulated against the S2/S3 simulation. A decision recorded on whether stock PCS covers the gap, or whether option (b) is reopened.

## CA-011 — Relaxed following distance by default

- **Root cause / hazard:** RC-02 · HZ-008 (TC-07).
- **Change:** in the LionDriver assured configuration, default the longitudinal personality to relaxed, and flag any change as out of assured scope (CA-008).
- **New hazards:** more cut-ins into the larger gap (comfort and availability); no safety hazard identified.
- **Acceptance criteria:** CA-004 S3 at the relaxed distance: no collision for lead braking ≤ 4 m/s² at ≤ 100 km/h. The setting is enforced and logged.

### CA-011 implementation record (2026-10-10)

- **Approval:** approved by the project maintainer on 2026-10-10. This covers CA-011 only; the rest of the CA-004 decision is still pending.
- **Changes:**

  | Change | File |
  |---|---|
  | `LongitudinalPersonality` defaults to relaxed. Devices with a saved setting keep it | `openpilot/common/params_keys.h` |
  | `set_personality()` logs `following distance outside assured configuration` when the setting changes to anything other than relaxed: at startup, from settings, or from the distance button. The driver can still choose | `openpilot/selfdrive/selfdrived/selfdrived.py` |
  | Settings text: "Relaxed is recommended". Translations of this string will show English until updated | `openpilot/selfdrive/ui/layouts/settings/toggles.py`, `openpilot/selfdrive/ui/mici/layouts/settings/toggles.py` |
  | Process replay uses the personality each route was driven with, so the new default doesn't shift replay output | `openpilot/selfdrive/test/process_replay/process_replay.py` |

- **Verification** (`openpilot/selfdrive/test/stopped_vehicle/test_following_distance.py`):
  - the default reads back as relaxed;
  - changes are logged on change only;
  - acceptance criterion: at the relaxed distance, no collision for a lead braking at 2, 3 and 4 m/s² from 60 and 100 km/h. **Pass.**
- **Not done:** "enforced" in the acceptance criterion means marking non-relaxed drives as out of assured scope, which is part of CA-008. For now the setting is only logged.
- **Residual risk:**
  - at 120 km/h a lead braking at 4 m/s² still leads to 4 km/h contact (CA-004 S3);
  - lead emergency stops (≥ 6 m/s²) still collide.

  HZ-008 stays open, with CA-010 and the option (b) candidate.

## CA-012 — Operating-domain speed cap for openpilot longitudinal

- **Root causes / hazard:** RC-02, RC-06 · HZ-001.
- **Change:** set the maximum speed for openpilot longitudinal in the assured configuration from CA-004 S4, using the confirmation range that CA-003 verifies for the worst target type and lighting in the operating domain.
- **Acceptance criteria:** the cap is derived and documented. It is enforced in software, and CA-002 passes at the cap with the measured confirmation range.

## CA-005 — Independent forward-collision monitor for FCW

- **Root cause:** RC-03. FCW shares perception with longitudinal control.
- **Change:** add a radar-track-based TTC monitor that raises FCW when a radar track in the ego path has TTC below threshold, *independent of* `lead_prob`. It uses its own stationary-clutter rejection, tuned for warnings, not braking (a false warning is far cheaper than false braking).
- **Acceptance criteria:** in CA-002, FCW onset TTC ≥ 2.0 s in ≥ 95% of physically-possible cases. Nuisance FCW rate on a baseline drive set ≤ an agreed target (SPI-03 / SPI-06).

## CA-006 — Hazard-timed driver monitoring escalation

- **Root cause:** RC-04.
- **Change:** analyze DM vision-policy timings (`policy.py:34-36`: 5 / 8 / 13 s) against TC-01/TC-02 closing times. Evaluate speed-dependent and scene-dependent thresholds: shorter eyes-off allowance at high speed, and when a lead is uncertain or the scene is complex.
- **Acceptance criteria:** at speeds ≥ 100 km/h, eyes-off time before the first alert ≤ the time to cover D_req at that speed minus driver reaction time (~1.5 s). Nuisance-alert impact measured (SPI-05).

## CA-007 — Event data capture

- **Root cause:** RC-05.
- **Change:** guarantee that every FCW, hard-brake (≤ -3 m/s²), stock AEB activation, collision-like jerk, or disengagement within 3 s of one of these preserves:
  - −30 s / +10 s of `radarState`, `modelV2` lead outputs, `longitudinalPlan`, `carState`, `driverMonitoringState`, `carControl`;
  - the software commit, platform flags and all non-default params.
- **Acceptance criteria:** fault-injection test shows the snapshot survives power loss within 1 s of the event.

## CA-008 — Assured configuration identity and parameter control

- **Root cause:** RC-05.
- **Change:** define the LionDriver *assured configuration* (commit + platform + allowed params). Compute a configuration hash at startup, log it, and show it in the UI. Any deviation (fork, toggle, param) marks the drive as **out of assured scope** in the logs.
- **Acceptance criteria:** changing any safety-relevant param flips the out-of-scope flag in a test.

### CA-008 implementation record (2026-10-10)

**What the assured configuration is** (`openpilot/selfdrive/selfdrived/assured_config.py`):

| Element | Assured value | Why |
|---|---|---|
| Platform | `TOYOTA_COROLLA_TSS2` | The reference vehicle (README) |
| `LongitudinalPersonality` | relaxed | CA-011 |
| `ExperimentalMode` | off | End-to-end longitudinal was not modeled in CA-002 / CA-004 (see finding below) |
| `AlphaLongitudinalEnabled` | off | CA-001 |
| `JoystickDebugMode`, `LongitudinalManeuverMode`, `LateralManeuverMode` | off | Debug control modes |
| Software origin | LionDriver repository | Forks are out of scope (RC-05) |
| Local changes | none | An uncommitted build can't be identified |

**How it works:**
- selfdrived evaluates the configuration at startup and on each params poll (every 0.1 s).
- When the result changes, it logs a `cloudlog` event `assured configuration` with `in_scope`, the list of deviations and a 16-hex `config_hash`. It also stores the same JSON in the new `AssuredConfiguration` param (cleared on manager start), which tools and a future UI can read.
- The hash covers the platform, the values of the params above, the git commit, the origin and the dirty flag.
- Deviations are allowed, not blocked: the driver can still choose. The point is that every drive can be identified afterwards as in or out of scope.

**Verification** (`openpilot/selfdrive/selfdrived/tests/test_assured_config.py`):
- the reference configuration is in scope;
- each of the six params, a different platform, a fork origin and a dirty tree each flag exactly one deviation;
- the hash is stable, and changes with the commit or a param;
- selfdrived logs and stores on change only.

**Pass.**

**Finding: experimental mode is on by default.** Upstream defaults `ExperimentalMode` to on (`params_keys.h`), and the manager writes defaults at startup. So on a fresh 2020 Corolla, openpilot runs **experimental (end-to-end) longitudinal by default**, and the device is out of the assured configuration from the start.
- What the CA-002 / CA-004 results still say: in experimental mode the planner takes the *minimum* of the MPC and end-to-end accelerations (`longitudinal_planner.py:142-147`). So braking for a lead is never weaker than simulated, and those results stay a valid lower bound.
- What they don't cover: behavior specific to the end-to-end model, such as model-initiated stops and possible phantom braking (HZ-006). The harness can't represent that without the driving model's outputs.
- **Decision needed:** either default `ExperimentalMode` off in LionDriver, or extend the analyses to experimental mode (needs logged model outputs or a rendering simulator). Until then the test records this as a known deviation.

**Not done:**
- Showing the configuration hash and scope in the UI (onroad or settings).
- Extending the fingerprint beyond these params (for example the panda firmware version and the opendbc commit) is a candidate for a later revision.

## CA-009 — Limitations, operator briefing, test-driver protocol (tier 5)

- **Root causes:** RC-02, RC-04. **Not acceptable as the only control.** It runs alongside CA-001…CA-008.
- **Change:** update the LionDriver limitations to state the -3.5 m/s² limit and the stopped-vehicle scenarios explicitly. Write a test-driver protocol (containment C-2).
- **Acceptance criteria:** protocol signed by every test driver before C-1 is lifted.

---

## Preventive actions

- **PA-01:** the first HARA must disposition HZ-001…HZ-007 explicitly.
- **PA-02:** create `docs/safety/sotif/TRIGGERING-CONDITIONS.md` seeded with TC-01…TC-06, and link the scenario IDs to the CA-002 suite.

## Follow-up actions

- **FA-01:** retrieve the NHTSA ODI resume for PE26007. Update REPORT §2 facts from **Reported** to primary-source **Verified**. Track any upgrade to an Engineering Analysis or a recall.
