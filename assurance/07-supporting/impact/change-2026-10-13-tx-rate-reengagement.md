# Change impact: no re-engagement while a TX-rate excess persists (ATC-20)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Integrated 2026-10-16**: merged into the opendbc fork as [jherrodthomas/opendbc#15](https://github.com/jherrodthomas/opendbc/pull/15) (merge commit `9859cb0`, 2026-10-14); LionDriver pins opendbc `515b9a2` ([change-2026-10-16-pin-515b9a2](change-2026-10-16-pin-515b9a2.md)); not verified on hardware; not reviewed independently. History: proposed 2026-10-13: opendbc branch `claude/atc-20-tx-rate-reengagement`, commit `a0938fa` (from `a57b667`), [jherrodthomas/opendbc#15](https://github.com/jherrodthomas/opendbc/pull/15); LionDriver pin unchanged until it is merged; not verified on hardware; not reviewed independently |
| Change requests | WP-W-03 ATC-20; [RR-2026-009](../../05-software/reviews/RR-2026-009.md) F-34 (decision §7: amend SWSR-518, then change the code); WP-W-02 OI-11 (closed by the amendment) |
| Requirement | SWSR-518 as amended in WP-W-02 v0.20: "…after such a revocation, authority shall not be granted again until one full 250 ms window has passed without a rejected frame" |
| Range | opendbc `a57b667..a0938fa`: `opendbc/safety/safety.h`, `opendbc/safety/tests/test_toyota.py` |
| Reference configuration affected | Yes, in the reference build only (`LIONDRIVER_REFERENCE`); the upstream build is unchanged |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Problem

After a TX-rate revocation (SWSR-518), the next PCM cruise rising edge granted authority again, even while the host was still flooding. `rx_checks_allow_engagement()` did not look at the revocation. The driver re-engaging cruise would hand authority straight back to a host that is still misbehaving (F-34).

## 2. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| opendbc `a0938fa` | `opendbc/safety/safety.h` | Reference build only. Each TX-rate rejection records its time. A revocation sets an engagement block. While the block is set, `rx_checks_allow_engagement()` refuses the grant; the block clears on the first engagement attempt at least 250 ms (`TX_RATE_WINDOW_US`) after the last rejected frame. `set_safety_hooks` clears the block with the rest of the envelope state (SWSR-311). The report flag `safety_tx_rate_exceeded` is unchanged: still set at the revocation and latched until the next mode change | Yes | Yes (a driver's re-engagement is refused for up to one window after a flood; the cruise edge is consumed, so the driver re-engages once more) | No | Yes (a compromised host that floods cannot get authority back through a driver re-engagement while it floods) | F-34; SG-01, SG-03, SG-04; TSR-518; SWSR-518 | WP-W-02 (SWSR-518, done), WP-W-03 ATC-20 (status), WP-W-05 §5.2 (`sm-toy-auth.yaml` T1 guard, at the pin bump), DN-01 (§ re-engagement), WP-W-06 (new unit test) | Safety unit tests (both variants, UBSan, 100 % line coverage); opendbc MISRA; B2B test (new scenario at the pin bump); HIL test 14 extended | Proposed |
| same | `opendbc/safety/tests/test_toyota.py` | New `test_tx_rate_no_reengagement_while_excess_persists`. Engage, flood `0x2E4` at 2× until revoked; keep flooding and check that each new rising edge is refused; stop; check refusal 1 µs before and grant at 250 ms after the last rejected frame; check the report stays latched; check that rejections while authority was never granted do not block | — | — | — | — | — | — | — | — |

Design choice: a separate block instead of the report flag. ATC-20 first proposed clearing `safety_tx_rate_exceeded` after a clean window. That would have changed the meaning of health bit 11 and `pandaState.txRateExceeded`, which the host and the logs read as "a revocation happened since the mode was set". Keeping the flag latched leaves reporting unchanged.

## 3. Interaction with B2B-06 (first found as candidate BB-C-01)

A safety-mode set clears the block (SWSR-311 resets all envelope state on a mode change). The same reset clears the CRUISE_ACTIVE edge memory, and the B2B test showed that authority can then come back on the next PCM_CRUISE frame without a new driver engagement (B2B-06, first found as candidate BB-C-01). A host that floods, is revoked, and then sets the safety mode again could therefore get authority back while cruise stays on. That path does not exist through the driver's re-engagement, which this change closes, but it exists through the mode reset. This change does not close it. The B2B-06 decision (2026-10-14) closes it in a separate change on the same opendbc branch: [change-2026-10-14-mode-set-regrant](change-2026-10-14-mode-set-regrant.md) (ATC-26). That fix would cover both cases, because any grant would then require CRUISE_ACTIVE to be seen at 0 first.

## 4. Verification results (local, 2026-10-13)

| Check | Result |
|---|---|
| New unit test, reference build | Pass in all 5 non-SecOC Toyota classes (skipped on SecOC, which has no TX-rate rows) |
| Same test with the block removed from `tx_rate_check` (mutation by hand) | Fails in all 5 classes, as intended |
| `test_toyota`, both variants | Pass |
| Full safety suite, upstream variant: UBSan run and coverage run | Pass; 100 % line coverage (2364/2364) |
| Full safety suite, reference variant: UBSan run and coverage run | Pass; 100 % line coverage (2478/2478) |
| opendbc MISRA (cppcheck 2.21, MISRA addon) | **Not established locally.** The addon did not run inside cppcheck in this environment, and the repo's `test_misra.sh` could not install its locked environment (network). Run separately on cppcheck dumps of `misra/main.c`, base and change give the same findings except shifted line numbers, with and without `-DLIONDRIVER_REFERENCE`. That differential run does not cover rules that read raw tokens of header files (for example 15.6). Authoritative result: the opendbc and panda MISRA CI jobs |
| B2B (`assurance/05-software/reference-models`) | Not yet: the LionDriver pin still points to `a57b667`. At the pin bump, the T1 guard in `sm-toy-auth.yaml` and the model gain the block, and a new scenario (flood, revoke, re-engage during and after the flood) is added |
| HIL test 14 extension | **Not run** (D-04) |

## 5. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | **Done 2026-10-16** ([change-2026-10-16-pin-515b9a2](change-2026-10-16-pin-515b9a2.md): pin `515b9a2`, deviation removed, B2B gate OK, record and WP-W-05 §5.2 updated). ~~Merge the opendbc branch and bump the LionDriver pin; update `sm-toy-auth.yaml` T1 guard, the B2B model and add the B2B scenario; regenerate WP-W-05 §5.2~~ | Pin bump |
| OI-2 | DN-01: add the re-engagement rule to the design note | Pin bump |
| OI-3 | Extend HIL test 14: re-engage during and after a flood | HIL bench (D-04) |
| OI-4 | B2B-06 (BB-C-01): decided 2026-10-14 (ATC-26); change [change-2026-10-14-mode-set-regrant](change-2026-10-14-mode-set-regrant.md) | Done |
