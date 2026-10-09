# Baseline Gap Assessment

| Field | Value |
|---|---|
| Work product | Baseline gap assessment (supporting document, not a registered work product) |
| Standard reference | ISO 26262:2018 parts 2–9; ISO 21448:2022; ISO/SAE 21434:2021; ISO/PAS 8800:2024; ASPICE PAM 4.0 |
| Version | 0.1 |
| Status | Draft |
| Author | Assurance team (initial review, assisted by static code review) |
| Reviewer(s) | TBD |
| Baseline | LionDriver `8b8c6ae`; submodules `opendbc_repo@229dc70`, `panda@92eb565` |

## 1. Scope and method

This was a static review of the repository at the baseline above. No code was executed and no vehicle testing was done.

- **Areas reviewed:**
  1. the safety-enforcement layer: `opendbc_repo/opendbc/safety`, `panda/board`, and the Toyota port in `opendbc_repo/opendbc/car/toyota`;
  2. the onboard application stack: `openpilot/selfdrive`, `openpilot/system`;
  3. development process and CI evidence.
- **Configuration:** findings are stated for the reference configuration, a 2020 Corolla LE (`TOYOTA_COROLLA_TSS2`, ICE, openpilot longitudinal).
- **Not reviewed:** the msgq, rednose, teleoprtc and tinygrad submodules were not initialized. The ML model weights are Git LFS pointers in this checkout.
- **Verification:** the most severe findings (marked ✔) were re-checked directly in the source.

**Provenance.** LionDriver is upstream openpilot ≈ v0.11.2 (`openpilot/common/version.h`). The only fork change is `README.md`. Every finding below is therefore a finding about upstream openpilot as inherited, not about LionDriver-authored code.

## 2. Summary

| Area | Assessment |
|---|---|
| Safety architecture | Sound pattern: a QM driving stack bounded by a MISRA-checked safety envelope on a separate MCU (panda). This pattern is the basis of the LionDriver strategy ([WP-M-01 §4](../01-management/WP-M-01-assurance-strategy.md#4-safety-architecture-argument-the-central-strategy)). The envelope needs hardening before it can carry an ASIL claim |
| Safety code verification | The strongest asset in the repo: 100% line coverage gate, MISRA C:2012 (154/156 rules checked), mutation testing, and per-brand safety tests including Toyota |
| Requirements, architecture, analyses | Absent. Two informal safety requirements in `docs/SAFETY.md`. `docs/contributing/architecture.md` is empty. The HARA and FMEA it mentions are not in the repo |
| HIL / on-device verification | Exists upstream on comma's private device farm only. **The fork has none** |
| Process capability (ASPICE) | CL0 in most processes. CL1 at best for SUP.8, SWE.4 (safety code) and SWE.5 |
| Cybersecurity | Several high findings: unsigned git-based OTA, RSA-1024/SHA-1 panda boot signing, a committed debug private key, debug builds by default, unauthenticated safety-mode changes, broad remote RPC surface |
| SOTIF / AI | No ODD or validation targets. No uncertainty or OOD supervision of the ML action. Experimental Mode (end-to-end longitudinal) turned on by default upstream with no recorded hazard re-assessment |

## 3. Safety enforcement layer (panda + opendbc safety)

### 3.1 Reference configuration as traced in code

| Item | Value | Source |
|---|---|---|
| Platform | `TOYOTA_COROLLA_TSS2`, flags `TSS2 \| NO_DSU` | `opendbc_repo/opendbc/car/toyota/values.py:160-165, 201-213` |
| Safety mode | Toyota, LKA torque path, openpilot longitudinal TX set | `opendbc_repo/opendbc/safety/modes/toyota.h:393-425` |
| safetyParam | `EPS_SCALE = 73`; no ALT_BRAKE, LTA or SECOC; `STOCK_LONGITUDINAL` not set | `toyota/interface.py:27-118`, `values.py:588` |
| Longitudinal | openpilot longitudinal (TSS2 without RADAR_ACC); `RAISED_ACCEL_LIMIT` | `toyota/interface.py:105-106, 117-118` |
| Max steering torque | 1500 raw (no Nm conversion documented) | `toyota.h:173` |
| Torque rate up / down | 15 / 25 raw per frame; real-time ≤ 450 raw per 250 ms | `toyota.h:174-177`, `declarations.h:71` |
| Command vs measured EPS torque | ≤ 350 raw difference | `toyota.h:176` |
| Accel bounds | +2.0 / −3.5 m/s² | `toyota.h:207-210` |
| Engagement | Only on the rising edge of PCM `CRUISE_ACTIVE`. Revoked on cruise off, brake press (rising edge or while moving), RX check failure, heartbeat mismatch (3 s) or loss (5 s) | `safety.h:354-356, 518-527`; `panda/board/main.c:182-213` |
| Gas | Blocks longitudinal only, does not disengage | `longitudinal.h:3-5` |

The controller limits (`values.py:20, 39-47`) are **identical** to the safety limits, so the operating envelope has zero margin to the enforcement envelope.

### 3.2 Findings

| ID | Finding | Evidence | Standard | Severity |
|---|---|---|---|---|
| GAP-01 ✔ | **No E2E alive counters on any Toyota RX message.** Brake (`0x226`) and wheel speed (`0xAA`) have no checksum either. The checksum on the others is an 8-bit additive sum. Stuck or replayed frames with a valid checksum go undetected; only silence is detected | `toyota.h:40-46, 65-72` | 26262-4 §6 (TSC), 26262-6 §7; 26262-5 Annex D (communication) | High |
| GAP-02 | The envelope does **not monitor driver steering torque** on the LKA path. Override depends on the EPS plus a host-side (QM) 500 raw check | `toyota.h:114-116`; `toyota/carcontroller.py:33, 83` | 26262-3 §7 (FSC), 21448 §8 | High |
| GAP-03 | The envelope does **not monitor EPS fault status** (`EPS_STATUS.LKA_STATE`). Only the host reads it | `toyota/carstate.py:122-127` | 26262-4 §6 | Medium |
| GAP-04 | Limits have no physical or controllability rationale: raw 1500/15/25/350/450 are not traced to Nm, lateral acceleration or ISO 11270 / ISO 15622. Torque is not speed-dependent. There is no longitudinal jerk limit in the envelope | `toyota.h:173-210`; `longitudinal.h:8-12` | 26262-3 §6–7, 26262-4 §6 | High |
| GAP-05 | Undocumented assumptions about OEM ECUs: EPS internal torque limiting, EPS command timeout (≈1.5–2 s per a code comment), PCM cruise and brake logic, stock PCS/AEB staying available with openpilot longitudinal | `toyota/carstate.py:15-16`; `docs/INTEGRATION.md` | 26262-3 §5/§7 (AoU, external measures) | High |
| GAP-06 | Detection times have no FTTI rationale: RX timeout ≤ ≈2 s (1 Hz tick), heartbeat mismatch ≈3 s, heartbeat loss 5 s. `docs/SAFETY.md` itself cites 0.9 s to reach 1 m lateral deviation | `safety.h:321-344`; `panda/board/main.c:101-103, 182-193` | 26262-3 §7, 26262-4 §6 | High |
| GAP-07 ✔ | **The hardware independent watchdog (IWDG) is never initialized.** The software watchdog is checked from the same tick ISR it supervises, so it cannot detect a hang | `panda/board/stm32h7/stm32h7_config.h:43` (only reference); `main.c:301`, `simple_watchdog.h:7-17` | 26262-5 §7 (HW safety mechanisms), 26262-6 §7 | High |
| GAP-08 ✔ | **Faults are report-only.** `PERMANENT_FAULTS = 0U`. No fault other than relay malfunction drives a safe state. No MPU configuration and no RAM ECC handling | `panda/board/sys/sys.h:50`; `sys/faults.h:8-19` | 26262-5 §7, 26262-6 §7.4 | High |
| GAP-09 ✔ | **The QM host configures the safety element.** Command `0xdc` sets any safety mode or parameter at any time with no authentication or cross-check. Debug relay drive `0xc5` is not gated by `ALLOW_DEBUG` in release builds | `panda/board/main_comms.h:144-147, 222-225` | 26262-9 §6 (FFI), 26262-6 §7 | High |
| GAP-10 | Host→panda comms integrity is weak: 8-bit XOR, no sequence counter or freshness check. The heartbeat shows `pandad` is alive, not that the control loop is | `panda/board/drivers/spi.h:97-138`; `can_comms.h:27` | 26262-6 §7, 26262-5 Annex D | Medium |
| GAP-11 | Single MCU and single channel: safety checks, comms ISRs and forwarding share one STM32H7 with no partitioning. Forwarding is decided before RX validation of the same frame | `panda/board/drivers/fdcan.h:199-221` | 26262-9 §6–7 | Medium |
| GAP-12 | Relay failure is detected only by watching traffic, with a 1–2 s grace period. There is no relay contact readback | `safety.h:215-220, 372-380` | 26262-5 §7 | Medium |
| GAP-13 | Verification: **line coverage only** (no branch or MC/DC). 6 global MISRA suppressions plus GNU-extension inline deviations with no formal deviation records. The panda bootstub is not MISRA-checked. 3 accepted surviving mutants (two on the Toyota LTA path). Tests run on x86 host builds, not the Cortex-M7 target | `opendbc_repo/opendbc/safety/tests/test.sh:36-43`; `tests/misra/suppressions.txt`; `tests/mutation.py`; `panda/tests/misra/test_misra.sh:35` | 26262-6 §9 Table 7/9, 26262-8 §11 | Medium |
| GAP-14 | No requirement IDs or traceability: limits live as commented constants, and tests reference constants rather than requirements | whole safety tree | 26262-8 §6, ASPICE SWE.1/SWE.4 | High (process) |
| GAP-15 | No hardware safety analysis: no FMEDA, SPFM, LFM or PMHF for the panda MCU, relay, power, or harness | n/a | 26262-5 §8–9 | High |
| GAP-42 ✔ | **The envelope allows the SoC to transmit PCS messages without a content check.** For the reference configuration (openpilot longitudinal), `TOYOTA_COMMON_LONG_TX_MSGS` whitelists PRE_COLLISION `0x344` and PCS_HUD `0x411` on the car bus. Only `0x283` has a content check (all-zero). The reference car does not send them in normal operation (`toyota/carcontroller.py:294-295`, DISABLE_RADAR only), but a QM fault could, which threatens SG-07 | `opendbc_repo/opendbc/safety/modes/toyota.h:19-28, 251-257, 359-360` | 26262-4 §6, 26262-9 §6 | High |
| GAP-43 | **An MCU hang leaves the relay in intercept, so the vehicle loses the camera's PCS messages.** Default exception handlers, `assert_fatal` and the missing hardware watchdog all end in a hang with the relay GPIO in its last state. Forwarding stops, cutting the camera→car path that stock PCS/AEB relies on (single-point fault for SG-07). A relay stuck in the intercept position is not detected; the existing check only detects the released direction. The only on-chip mechanism that forces a reaction is the clock security system (`panda/board/stm32h7/clock.h:119`) | `panda/board/`; hardware analysis in [WP-H-03](../04-hardware/WP-H-03-hardware-safety-analysis-fmeda.md) | 26262-5 §7, 26262-9 §8 | High |

## 4. Onboard application stack (QM, SOTIF-managed)

| ID | Finding | Evidence | Standard | Severity |
|---|---|---|---|---|
| GAP-16 | **Soft disable keeps actuating for 3 s** on the inputs that just failed. Inter-process "alive" allows 10× the nominal period (0.5 s for modelV2), so stale-data actuation can last up to ≈3.5 s, about 100 m at 30 m/s. controlsd does not check input freshness itself | `selfdrived/state.py:7-8`; `cereal/messaging/__init__.py:152-153`; `controls/controlsd.py:66, 122-127` | 26262-4 §6 (fault reaction), 21448 §8 | High |
| GAP-17 | **Diagnostics are suppressed during the big-model ("Chestnut") fallback.** commIssue, posenet, locationd and modeldLagging checks are masked while the big model loads and for 5 s after it becomes ready or fails. After a failure, the system hot-switches to a cold small model (recurrent state zero) while still actuating. Upstream `948ad05` ("chestnut: fix offroad alert") widened the masking window and added `modeldLagging` to it | `selfdrived/selfdrived.py:382-384, 403, 457`; `modeld/modeld.py:411-419` | 26262-6 §7, 21448 §7–8, PAS 8800 | High |
| GAP-18 | **Experimental Mode on by default without confirmation** (upstream `f21bfc3`). This makes end-to-end model longitudinal behaviour the default. Its own UI says "Mistakes should be expected", and it conflicts with `docs/LIMITATIONS.md:35` ("traffic lights not detected"). No hazard re-assessment is recorded | `common/params_keys.h:43`; `selfdrive/ui/layouts/settings/toggles.py` | 21448 §5–6, 26262-8 §8 (change impact) | High |
| GAP-19 | `cruiseMismatch` raises an event with no reaction (IMMEDIATE_DISABLE commented out). `canError` shows the wrong HMI text ("Unknown Vehicle Variant"). `speedTooHigh` (raised in `selfdrive/car/car_events.py:126`) warns without disengaging. Non-finite actuator commands are silently clamped to 0 | `selfdrived/events.py:458-460, 928-936, 989-996`; `controlsd.py:140-147` | 26262-4 §6, 21448 §8 | Medium |
| GAP-20 | **Parameters and IPC can change safety behaviour with no authentication:** debug and maneuver modes replace controlsd or plannerd; `lateralManeuverPlan` overrides model curvature; `IsDriverViewEnabled` puts DM into demo mode with synthetic inputs; any local process can publish on msgq | `system/manager/process_config.py:34-47, 95-109`; `controlsd.py:123-124`; `monitoring/dmonitoringd.py:26-27` | 26262-9 §6, 21434 §10 | High |
| GAP-21 | Driver monitoring: the wheel-touch fallback resets awareness on any steering or gas input. Source validity is always `True` (`dmonitoringmodeld.py:99`). No tests for DM data loss. Alerts only start above 2.8 m/s | `monitoring/policy.py:29, 335`; `modeld/dmonitoringmodeld.py:99`; `monitoring/test_monitoring.py` | 21448 §6 (misuse), 26262-3 controllability basis | High |
| GAP-22 | ML: no uncertainty, confidence or OOD gating of the control action. No model hash, version or signature check at load. Models are deserialized with `pickle` (code execution). No training-data ODD specification. An external USB eGPU sits in the control loop with no timing or FFI argument | `modeld/modeld.py:158-159, 210-211`; `modeld/helpers.py:11-44` | PAS 8800, 21448 §7, 21434 | High |
| GAP-23 | Host runtime: CPython with GC disabled; no WCET or timing budgets (only an averaged `Ratekeeper` lag); no spatial or temporal partitioning between safety-relevant processes and QM processes (UI, encoders, uploader, athena, webrtcd) on the shared SoC | `common/realtime.py:41-46, 72-74`; `process_config.py:70-121` | 26262-6 §7, 26262-9 §6 | Medium (QM allocation makes it acceptable *if* the envelope is shown to be sufficient) |

## 5. Cybersecurity

| ID | Finding | Evidence | Standard | Severity |
|---|---|---|---|---|
| GAP-24 ✔ | **Panda firmware signing uses RSA-1024 with SHA-1.** No RDP/WRP option-byte setup in code. No runtime flash integrity check. Softloader entry is allowed in release builds | `panda/board/crypto/rsa.h:37`, `sha.h:45`; `bootstub.c:47-72`; `main_comms.h:176-179` | 21434 §10, UN R155 Annex 5 | High |
| GAP-25 ✔ | **A debug RSA private key is committed**, and **firmware builds default to DEBUG with `ALLOW_DEBUG`** unless `RELEASE` and `CERT` are set. A fork that builds its own panda firmware ships debug capabilities (ALLOUTPUT mode, debug-key acceptance) by default | `panda/board/crypto/certs/debug`; `panda/SConscript:12-20` | 21434 §10, 26262-6 §7 | High |
| GAP-26 | OTA updates are git fetches from a configurable branch, staged with sudo. There is no signature verification beyond TLS transport and commit hashes | `openpilot/system/updated/updated.py:205-222, 238, 387-399` (AGNOS images checked only against hashes from the same unsigned git tree) | 21434 §13, UN R156 | High |
| GAP-27 | Remote access through athenad: a persistent connection to a server set by `ATHENA_HOST`, plus RPCs to read any live service, upload log-root files to arbitrary URLs, tunnel SSH (port 22, remote URI supplied by the server) and read authorized keys. Live streaming is blocked while the ignition is on (`IsLiveStreaming` cleared on ignition, `openpilot/system/webrtc/helpers.py:28`); webrtcd listens on localhost only | `openpilot/system/athena/athenad.py:51, 355-807` | 21434 §9 (TARA), §15 | High |
| GAP-28 | `SECURITY.md` and the issue templates route reports to comma.ai. LionDriver has no vulnerability intake | `SECURITY.md`; `.github/ISSUE_TEMPLATE/*` | 21434 §8 | Medium |
| GAP-38 ✔ | **The SoC controls the panda MCU's boot pins.** Through `STM_BOOT0`/`STM_RST_N` it can put the MCU into its ROM bootloader (`openpilot/common/hardware/comma/hardware.py:410-419`). When the flashed firmware does not boot, pandad's recovery path flashes a *development* bootstub (`openpilot/selfdrive/pandad/pandad.py:34-39`). Without RDP/WRP, anyone with root on the SoC (QM) controls the safety MCU's firmware. This undermines both freedom from interference and the boot-integrity claims | `hardware.py:410-419`; `pandad.py:34-39`; `panda/board/stm32h7/llflash.h:14` | 26262-9 §6, 21434 §10 | High |

## 6. Process and configuration management

| ID | Finding | Evidence | Standard | Severity |
|---|---|---|---|---|
| GAP-29 | **Safety code is not under LionDriver configuration control.** Submodules use relative URLs that resolve to `commaai/*`. tinygrad tracks `branch = master`. `check-submodules.sh` requires pins to be on upstream master | `.gitmodules`; `tools/release/check-submodules.sh` | 26262-8 §7, SUP.8 | High |
| GAP-30 | **No HIL, on-road or model-replay verification in the fork.** `Jenkinsfile` relies entirely on comma's device pools, credentials and signing certificates. Process-replay reference logs and test routes are fetched from comma storage | `Jenkinsfile`; `selfdrive/test/process_replay/test_processes.py:70`; `tools/lib/openpilotci.py` | 26262-4 §7, 26262-6 §10–11, SYS.4/SWE.5–6 | High |
| GAP-31 | Workflows that do not fit a fork: `ui_preview.yaml` is currently disabled (`if: false`) but would need a comma deploy key; `jenkins-pr-trigger.yaml` targets a Jenkins the fork does not have and deletes its trigger comments (part of the review record). `stale.yaml` auto-closes PRs after 31 days, so safety change requests can be lost | `.github/workflows/*` | SUP.10 | Medium |
| GAP-32 | No CODEOWNERS file, PR template or visible branch protection. "Review" is limited to labelling | `.github/` | 26262-8 §9, SUP.10 | High |
| GAP-33 | No plans: safety, SOTIF, cybersecurity, project, CM, change, verification, tool qualification | n/a | 26262-2 §6, MAN.3 | High |
| GAP-34 | Tool qualification is absent. Tools at TCL2–3 include arm-none-eabi-gcc 13.2.1 (comma-packaged), cppcheck+MISRA (mutable `release-cppcheck` branch, known exit-code bug), tinygrad (model compiler, tracks master), acados code generation, capnp code generation, gcovr and in-house mutation/replay tools | `pyproject.toml`; `uv.lock`; `opendbc/safety/tests/misra/test_misra.sh` | 26262-8 §11 | Medium |
| GAP-35 | No LionDriver versioning: `version.h` still says `0.11.2`; `pyproject.toml` authors are `user@comma.ai` | `openpilot/common/version.h`; `pyproject.toml` | SUP.8 | Low |
| GAP-36 | No coverage threshold for openpilot Python/C++. Type checking uses `ty` 0.0.80 with unresolved imports and attributes ignored | `pyproject.toml` | 26262-6 §9 | Low (QM) |
| GAP-37 | Upstream sync velocity (daily bumps, weekly lockfile upgrades, model swaps) with no impact analysis would make the safety case stale on every merge | git history | 26262-8 §8, SUP.10 | High |
| GAP-39 | **LionDriver CI does not run the safety-code verification.** The opendbc safety tests (100% coverage gate), MISRA and mutation jobs exist only in `opendbc_repo/.github/workflows/tests.yml`. `tools/op.sh test` collects tests under `openpilot/` only. `.github/workflows/tests.yaml` runs on pushes to `master` and on PRs, not on pushes to `liondriver-dev` | `.github/workflows/tests.yaml:5-7`; `opendbc_repo/.github/workflows/tests.yml` | 26262-6 §9, SUP.8 | High |
| GAP-40 | Model weights are fetched from comma's Git LFS store (`.lfsconfig` → `huggingface.co/commaai/openpilot-lfs`). LionDriver does not control the storage of a safety-relevant configuration item | `.lfsconfig` | 26262-8 §7, PAS 8800 | Medium |
| GAP-41 | Safety unit tests build `libsafety` with `-DALLOW_DEBUG`. Only `test_release_build.py` checks the release configuration, so the tested configuration differs from the shipped one | `opendbc_repo/opendbc/safety/tests/` | 26262-6 §9 (test environment representativeness) | Medium |

## 7. ASPICE capability baseline (estimated)

| Process | CL | Process | CL |
|---|---|---|---|
| SYS.1 | 0 | SWE.4 | 1 (safety code) / 0–1 (rest) |
| SYS.2 | 0 | SWE.5 | 1 |
| SYS.3 | 0 | SWE.6 | 0–1 (comma only) |
| SYS.4 | 0–1 (comma only) | SUP.1 | 0 |
| SYS.5 | 0 | SUP.8 | 1 |
| SWE.1 | 0 | SUP.9 | 0 |
| SWE.2 | 0 | SUP.10 | 0–1 |
| SWE.3 | 1 (partial) | MAN.3 | 0 |
| MLE.1–4, SUP.11 | 0 | HWE.1–4 | 0 (supplier) |

The detailed rating is in [WP-M-13](../01-management/WP-M-13-aspice-capability-baseline.md).

## 8. Existing strengths to build on

- The envelope pattern itself: all actuation goes through the panda; there is a TX whitelist; relay-malfunction latching; engagement only on the PCM cruise edge; brake disengage; heartbeat-loss → SILENT.
- opendbc safety verification (runs in upstream opendbc CI only; LionDriver must run it in its own CI to claim it as evidence, see D-03): a 100% line coverage gate, MISRA C:2012 via cppcheck (`--check-level=exhaustive`), mutation testing in CI with a checker self-test, UBSan, a shared safety test suite (`common.py`, 1217 lines) and a Toyota suite (`test_toyota.py`, 397 lines), and drive-log safety replay.
- Process replay as a regression oracle across the main control processes.
- A driver monitoring policy with escalation, wheel-touch fallback on model uncertainty, forced deceleration on no response, and lockout.
- Excessive-actuation detection with a persistent latch.
- Reproducible builds: hash-pinned `uv.lock`, SHA-pinned submodules, `check-dirty.sh`.

## 9. Priority actions (feed into the G0/G1 plan)

| # | Action | Closes | Owner WP |
|---|---|---|---|
| 1 | Fork opendbc and panda under LionDriver control; absolute submodule URLs; pin tinygrad; freeze upstream sync | GAP-29, GAP-37 | [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md), [WP-M-11](../01-management/WP-M-11-upstream-and-supplier-management.md) |
| 2 | CODEOWNERS, PR template with safety-impact checklist, branch protection; disable comma-only workflows and stale auto-close | GAP-31, GAP-32 | [WP-P-02](../07-supporting/WP-P-02-change-management.md) |
| 3 | Revert the Experimental Mode default for the reference configuration pending SOTIF assessment | GAP-18 | [WP-C-07](../02-concept/WP-C-07-sotif-functional-modifications.md) |
| 4 | Complete the concept phase (item definition, HARA, FSC) so envelope limits and detection times get FTTI-based rationale | GAP-04, GAP-05, GAP-06 | [WP-C-01](../02-concept/WP-C-01-item-definition.md), [WP-C-03](../02-concept/WP-C-03-hara.md), [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) |
| 5 | Envelope hardening backlog: IWDG, fault → safe state, lock safety mode for the reference configuration, gate `0xc5`, driver-torque and EPS-status monitoring, E2E strategy for RX | GAP-02, -03, -07, -08, -09, -01 | [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md), [WP-W-02](../05-software/WP-W-02-software-safety-requirements.md) |
| 6 | Firmware security: release build pipeline with a LionDriver key (modern algorithm), RDP/WRP, remove debug-key acceptance from release | GAP-24, GAP-25 | [WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md) |
| 7 | Build a LionDriver HIL bench and fork-owned process-replay references | GAP-30 | [WP-S-08](../03-system/WP-S-08-system-integration-test.md), [WP-W-08](../05-software/WP-W-08-embedded-software-testing.md) |
| 8 | Fix the soft-disable and Chestnut diagnostic-masking behaviour (or remove Chestnut from the reference configuration) | GAP-16, GAP-17 | [WP-C-07](../02-concept/WP-C-07-sotif-functional-modifications.md), [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) |
| 9 | LionDriver `SECURITY.md` and vulnerability intake; disable or constrain athena/SSH/OTA in the reference configuration | GAP-26, -27, -28 | [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) |
| 10 | No public-road LionDriver operation beyond safety-driver testing under WP-V-07 until G1 | — | [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md) |
