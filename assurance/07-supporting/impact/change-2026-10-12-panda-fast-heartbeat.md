# Change impact: authority revoked 0.3 s after the last SoC heartbeat

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Integrated 2026-10-12: LionDriver pins panda `c2e5d93` (merge commit of panda#7 on the fork's `master`); not yet verified on hardware (HIL bench D-04); not reviewed independently**. Follow-up §5 (siren when heartbeat loss revokes authority): panda `c33343b`, 2026-10-13, not verified on hardware, not reviewed independently |
| Change request | [jherrodthomas/panda#7](https://github.com/jherrodthomas/panda/pull/7) |
| Range | panda `3859fa8..c2e5d93` |
| Reference configuration affected | Yes: every build of the panda firmware |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `b87197f` | `board/drivers/heartbeat_monitor.h` (new), `board/drivers/drivers.h`, `board/main.c`, `board/main_comms.h`, `tests/heartbeat_monitor/` (new), `tests/hitl/test_12_rx_timeout.py` | The 100 Hz safety task counts ticks since the last `0xf3` heartbeat. In a car safety mode it clears `controls_allowed` once 0.3 s (30 ticks) have passed without one, every tick until the next heartbeat. Re-engagement needs a new PCM rising edge. The 1 Hz counter and the 5 s SILENT path (TSR-510) are unchanged | Yes | Yes (more disengagements if the host stalls) | No | Yes (a host that stops talking loses authority within 0.3 s) | SG-01, SG-03, SG-04; FSR-01.07; GAP-06, GAP-10 | WP-S-02 (TSR-407), WP-W-02 (SWSR-407), WP-W-03 §5.1–5.2, WP-W-06 (host tests), WP-V-05 (heartbeat loss) | Builds (all variants), MISRA, host tests; HIL: stop the heartbeat in a car mode and time the drop of `controls_allowed` | Taken (maintainer merged panda#7, 2026-10-12) |

## 2. Behaviour changes to watch

| Change | Effect | Check |
|---|---|---|
| `pandad` sends the heartbeat at 10 Hz from its 100 Hz loop (`selfdrive/pandad/pandad.cc`), only when the panda state read succeeds | Two missed heartbeats are tolerated. A `pandad` stall or failed state read of 0.3 s or more now disengages, where before it went unnoticed until the 5 s SILENT path | Count `controlsMismatch`-free disengagements caused by heartbeat loss in drive logs (the panda health has `heartbeat_lost` only for the 5 s path; add a reason code if this proves frequent) |
| Equal interrupt priority (WP-W-03 §5.1) | The safety task can be delayed by long handlers; the 0.3 s includes one task period only if the task runs on time | WP-W-03 §5.4.5 measurement |

## 3. Verification results

| Check | Result |
|---|---|
| `scons` default, `LIONDRIVER_REFERENCE=1`, `FAULT_INJECTION=1`, `RELEASE=1 LIONDRIVER_REFERENCE=1` | Pass (`-Werror`) |
| `tests/misra/test_misra.sh` (standard and reference variants) | Clean |
| `tests/heartbeat_monitor` (host) | Pass: timeout equals 0.3 s; revokes exactly after it and holds; heartbeats at 10 Hz never revoke; two missed heartbeats tolerated; a heartbeat clears it |
| HIL | **Not run** (D-04). `test_12` now keeps the heartbeat fresh while engaging |

## 4. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | HIL: stop the heartbeat in TOYOTA mode and time the drop of `controls_allowed` | Release |
| OI-2 | Report a heartbeat-caused revocation to the host with its own reason (TSR-406 fault-specific reason codes) | Later change |

## 5. Follow-up: siren when heartbeat loss revokes authority (panda#15, TSR-516)

Added 2026-10-13.

| Item | Detail |
|---|---|
| Change request | [jherrodthomas/panda#15](https://github.com/jherrodthomas/panda/pull/15) (`6dee6fa..c33343b`; branch commit `7dd0c4b`); LionDriver pins panda `c33343b`, which contains `6dee6fa` (§7 of the [safety-mode lock record](change-2026-10-12-panda-safety-mode-lock.md)) |
| Change | New `board/drivers/heartbeat_siren.h`, wired in `board/main.c` `safety_task_handler`. When the 0.3 s heartbeat monitor (§1) revokes authority in a car safety mode and `controls_allowed` was set at that moment, the 100 Hz safety task asks for the panda's own siren at once and holds it for 3 s (`HEARTBEAT_SIREN_HOLD_TICKS` 300). The tick drives the speaker with the other siren requests (`set_siren((loop_counter & 1U) && ...)`). The state is reset on every safety mode change. Compiled in every build, like `heartbeat_monitor.h` and `eps_fault_siren.h`, not only with `LIONDRIVER_REFERENCE` |
| Not changed | The 1 Hz path: SILENT after 4–5 s (ignition on) or 1–2 s (off), and the 3 s siren then if authority was granted within the last 5 s (`siren_countdown`, `controls_allowed_countdown`). It still sounds when it fires |
| Why | TSR-516(a) and SG-02/SG-06 ask for a take-over warning within 1 s that does not depend on the SoC. Before this change the only siren on heartbeat loss came from the 1 Hz path, 4–5 s after the last heartbeat (WP-S-04 T-07) |
| Timing | The 8 Hz tick sounds the speaker only on odd ticks, so the siren is audible within up to 2 × 125 ms of the request. Worst case from the last heartbeat: 0.3 s + 10 ms + 250 ms ≈ 0.56 s, within the SG-02/SG-06 1 s budget and within the WP-S-04 §3.7 split (detection ≤ 0.5 s + warning ≤ 0.5 s; here ≤ 0.31 s + ≤ 0.25 s). WP-S-04 T-07a |
| Effect | A heartbeat loss while engaged now sounds the siren within about 0.56 s. A heartbeat loss while disengaged sounds nothing from this path. If authority ended within the 5 s before the loss, only the 1 Hz path sounds, at 4–5 s (WP-S-04 OI-9) |
| Requirements | TSR-516 (a), and (b) for this revocation; SWSR-516; TSR-407. The firmware comments name TSR-516(b) |
| Hazards / findings | SG-02, SG-06; FSR-02.05; WP-A-04 BE-2.14, MCS-02.5, SPF-11; WP-A-03 DFI-14; WP-A-02 FFI-TM-07 |
| WPs affected | WP-S-02 (TSR-516), WP-W-02 (SWSR-516), WP-S-04 (T-07a, §5, OI-9), WP-W-06 (host suite), WP-W-08 (VS-SWQ-10), [HIL bench](../../05-software/hil-bench/README.md) (test_15), WP-A-02, WP-A-03, WP-A-04, WP-M-02 §4.1, WP-P-01 (pin) |
| Verification | Host: `tests/heartbeat_siren` (8 tests, compiled with `heartbeat_monitor.h` in the safety-task order): 3 s hold; siren in the task that revokes granted authority, not before; worst case to sound below 1 s; none when not engaged or while heartbeats arrive; stops after 3 s; once per revocation; again after re-engagement. Pass locally on 2026-10-13; in LionDriver CI (`safety.yaml`, job `panda_host_tests`, now six suites). HIL: `tests/hitl/test_15_heartbeat_siren.py` measures the 0.3 s revocation after the last heartbeat (needs a `LIONDRIVER_REFERENCE=1` build for the car simulation); the host cannot read the speaker, so the siren is confirmed by ear or microphone and recorded in the bench log. **Not run** (D-04). Nothing run on hardware |
| Decision | Taken (maintainer merged panda#15, 2026-10-13). Not reviewed independently; an AI draft is not a review (WP-M-06) |
| Open | OI-1 extended: on the HIL bench also confirm the siren within 0.56 s of the last heartbeat. WP-S-04 OI-9: the case of authority that ended within the 5 s before the loss |
