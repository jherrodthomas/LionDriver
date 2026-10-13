# Change impact: diagnostic-mode gate and cluster HUD authority in the reference build

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for LionDriver-originated changes to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). Both close a gap the DFA (LD-DFA-001 rev 0.5) found while re-checking its insufficient initiators.

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-13: unit-tested and MISRA-clean; LionDriver pins the branch commits for CI (panda `4ac8e1c`, opendbc `c393a04`), to be re-pinned to the merge commits; not verified on the bench or the vehicle; not reviewed independently** |
| Change requests | [jherrodthomas/panda#16](https://github.com/jherrodthomas/panda/pull/16), [jherrodthomas/opendbc#13](https://github.com/jherrodthomas/opendbc/pull/13) |
| Reference configuration affected | Yes, in the reference build only (`LIONDRIVER_REFERENCE=1`, the default) |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | DFA | Requirements / design | Verification |
|---|---|---|---|---|---|
| panda `4ac8e1c` | `board/reference_lock.h`, `board/main.c`, `tests/reference_lock/` | Once TOYOTA has been accepted, host request `0xdc` with ELM327 is refused until the 1 Hz tick sees the ignition off (line or CAN). Fingerprinting before the car mode and bench use with the ignition off are unaffected. A refusal is counted in the health packet | DFI-08 insufficient → open; DM-12 required → existing (unverified) | LD-DES-001 DR-05 (without the stationary alternative: no vehicle speed outside a car mode); TSR-513 | Host tests (5 new); panda MISRA, both variants. HIL: not run |
| opendbc `c393a04` | `opendbc/safety/modes/toyota.h`, `opendbc/safety/tests/test_toyota.py` | An LKAS_HUD (0x412) with `BARRIERS != 0` is refused unless controls are allowed or were allowed within the last 1 s; the grant is stamped on RX frames and forgotten on a safety mode change | DFI-19 insufficient → open; DM-11 required → existing (unverified) | FSR-017, FSR-027 (DOI-005) | Safety suite and 100 % line coverage in both variants; MISRA; reference-variant mutation in CI |

## 2. Behaviour to watch

| Change | Normal-driving risk | How it is bounded |
|---|---|---|
| ELM327 gate | pandad restarting mid-drive cannot re-run fingerprinting (its ELM327 request is refused) | The item stays unavailable until the next ignition cycle, the safe direction; a refusal is counted in the health packet |
| HUD authority | A host that clears the HUD more than 1 s after a disengagement gets a blocked frame, which `selfdrived` reports as `pandaTxBlocked` if still engaged | The host clears it on the next on-change frame (tens of ms); replay of reference logs to confirm (as OI-3 of the host supervision change) |

## 3. Open items

| ID | Item |
|---|---|
| OI-1 | HIL: ELM327 refusal after the car mode and its reset on ignition off (extend `tests/hitl/test_11_reference_lock.py`) |
| OI-2 | Vehicle: confirm that `BARRIERS` is the indication the driver reads as lane assist active on the reference cluster, then name the bits in FSR-017/027 (DFA DOI-005) |
| OI-3 | Re-pin LionDriver to the forks' merge commits once panda#16 and opendbc#13 are merged |
