# Change impact: no authority after a safety-mode change without a new engagement (ATC-26, B2B-06)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Integrated 2026-10-16**: merged into the opendbc fork as [jherrodthomas/opendbc#15](https://github.com/jherrodthomas/opendbc/pull/15) (merge commit `9859cb0`, 2026-10-14); LionDriver pins opendbc `515b9a2` ([change-2026-10-16-pin-515b9a2](change-2026-10-16-pin-515b9a2.md)); not verified on hardware; not reviewed independently. History: proposed 2026-10-14: opendbc commit `3ed789a` on branch `claude/atc-20-tx-rate-reengagement`, [jherrodthomas/opendbc#15](https://github.com/jherrodthomas/opendbc/pull/15); LionDriver pin unchanged until it is merged; not verified on hardware; not reviewed independently |
| Change requests | WP-W-03 ATC-26; back-to-back finding B2B-06 ([B2B-TOY-AUTH-2026-10-13](../../05-software/reference-models/results/B2B-TOY-AUTH-2026-10-13.md), scenario D19b; first found as candidate BB-C-01); WP-W-02 OI-14 (closed by the amendment) |
| Decision | Delegated decision of the project maintainer, 2026-10-14 ("go with your recommendation"): resolve the SWSR-301/SWSR-311 conflict by amending SWSR-311 so the cruise edge state resets to "not yet seen disengaged"; the alternative (accept and document) was not taken |
| Requirement | SWSR-311 as amended in WP-W-02 v0.21; SWSR-301 unchanged |
| Range | opendbc: `opendbc/safety/safety.h`, `opendbc/safety/tests/test_toyota.py`, `test_ford.py`, `test_tesla.py` |
| Reference configuration affected | Yes, in the reference build only (`LIONDRIVER_REFERENCE`); the upstream build is unchanged |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Problem

The back-to-back test found this (candidate BB-C-01, now B2B-06, scenario D19b). `set_safety_hooks` clears `cruise_engaged_prev`, as SWSR-311 requires ("all … edge state reset"). After a safety-mode change, a CRUISE_ACTIVE that stayed 1 is therefore seen as a rising edge on the next PCM_CRUISE frame. Authority is granted again without a new driver engagement, against SWSR-301 ("only on a rising edge"). Whether that happens depends on frame order: every RX check must have been received again before that PCM_CRUISE frame.

A safety-mode change can come from the host (`0xdc`), from a heartbeat loss and recovery, or from a harness change. Together with ATC-20, this path matters most for a host that floods, is revoked, and then sets the safety mode again: the ATC-20 engagement block is cleared by the same reset.

## 2. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| opendbc `3ed789a` | `opendbc/safety/safety.h` | Reference build only. New flag `pcm_cruise_seen_disengaged`, cleared by `set_safety_hooks` and set by `pcm_cruise_check` when CRUISE_ACTIVE = 0 is received. A rising edge grants authority only if the flag is set. `rx_checks_allow_engagement()` is still called on every rising edge (its side effects stay unchanged), and the flag is combined after the call (MISRA 13.5) | Yes | Yes (after a mode change with cruise held, the driver must switch cruise off and on to engage) | No | Yes (a host cannot regain authority by re-setting the safety mode while cruise stays on) | BB-C-01; SG-01, SG-03, SG-04; TSR-301, TSR-311; SWSR-301, SWSR-311 | WP-W-02 (SWSR-311, done), WP-W-03 ATC-26 (done), WP-W-05 §5.2 (`sm-toy-auth.yaml` T1/T7, at the pin bump), WP-W-06 (new unit test) | Safety unit tests (both variants, UBSan, 100 % line coverage); opendbc and panda MISRA; B2B test at the pin bump (BB-08b should then agree) | Proposed |
| same | `opendbc/safety/tests/test_toyota.py` | New `test_no_grant_after_mode_set_without_new_engagement`: engage, set the safety mode again, receive every other RX check, then PCM_CRUISE with CRUISE_ACTIVE still 1 three times (no grant), then off and on (grant) | — | — | — | — | — | — | — | — |
| same | `test_ford.py`, `test_tesla.py` | Two upstream brand tests engaged on the first cruise frame of a mode, which the reference rule now refuses. Each now sends one cruise-off frame first. The upstream build behaves the same with or without that frame; the brands themselves cannot run in the reference build (safety-mode lock) | — | — | — | — | — | — | — | — |

Interaction with [jherrodthomas/opendbc#14](https://github.com/jherrodthomas/opendbc/pull/14) (LS-06, merged into the opendbc fork on 2026-10-14): there a rising edge no longer grants authority directly but opens a 1 s engagement window, and the grant waits for the host heartbeat's engaged flag. After merging opendbc `master` into this branch, the check applies at the window: a rising edge opens the window only if CRUISE_ACTIVE = 0 has been received in the current mode. The ATC-20 block is checked again at the grant (`rx_checks_allow_engagement()` in `pcm_engage_check`).

Applies to every mode that uses the shared `pcm_cruise_check` in the reference build. Only the Toyota mode can be active there (safety-mode lock, TSR-512).

## 3. Verification results (local, 2026-10-14)

| Check | Result |
|---|---|
| New unit test, reference build | Pass in the 4 applicable Toyota classes (LKA, LTA, each with and without stock longitudinal); skipped for SecOC and alt-brake |
| Same test with the flag check removed | Fails in all 4, as intended |
| Full safety suite, both variants (UBSan run, coverage run, 100 % line gate) | Pass; 100 % line coverage (upstream 2365/2365, reference 2482/2482) |
| opendbc MISRA | **Not established locally** (see [change-2026-10-13-tx-rate-reengagement](change-2026-10-13-tx-rate-reengagement.md) §4); the opendbc and panda MISRA CI jobs are authoritative |
| B2B (`assurance/05-software/reference-models`) | Not yet: the pin does not include the change. Today the reference model follows the old SWSR-311 reading (MA-01: the edge state is reset on a mode set), and C and model agree on the re-grant in D19b. At the pin bump, MA-01 must follow the amended SWSR-311, and D19b must then show no re-grant on both sides |
| HIL | **Not run** (D-04) |

## 4. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | **Done 2026-10-16** ([change-2026-10-16-pin-515b9a2](change-2026-10-16-pin-515b9a2.md): pin `515b9a2`, deviation removed, B2B gate OK, record and WP-W-05 §5.2 updated). ~~Merge the opendbc PR, bump the pin; update the reference model's MA-01 to the amended SWSR-311 and re-run the B2B (D19b: no re-grant on both sides); state the T7/T1 behaviour in `sm-toy-auth.yaml`~~ | Pin bump |
| OI-2 | HIL: set the safety mode with cruise held on the bench; no authority until cruise off and on | HIL bench (D-04) |
| OI-3 | HMI: after a mode change during a drive, the driver must re-engage cruise. Check that the host shows why engagement is refused | Host alert review |
