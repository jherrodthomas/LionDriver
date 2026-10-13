# Change impact: pandad fault mapping (SWF-025)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant host code (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **In review: unit test passes, `scons` builds, process replay unchanged in CI; HIL not run; not reviewed independently** |
| Change requests | This LionDriver change |
| Finding | SW FMEA SWF-025 / action SWF-ACT-025 (`assurance/08-analyses/fmea/analyses/sw-fmea.yaml`, on branch `claude/charming-knuth-b8nnqh`, not yet on `liondriver-dev`) |
| Range | LionDriver `682f184..` this change |
| Reference configuration affected | Yes (all builds) |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| LionDriver | `openpilot/cereal/log.capnp`, `openpilot/selfdrive/pandad/pandad.cc`, `pandad.h`, `SConscript`, `tests/test_pandad_faults.cc` (new), `openpilot/test_native.py` | `PandaState.FaultType.interruptRateSoundDma @27` added for the panda's `FAULT_INTERRUPT_RATE_SOUND_DMA` (`panda/board/sys/sys.h:47`). `pandaStates.faults` is now sized from the bits that have a FaultType only, so no entry is left at the default value 0 (`relayMalfunction`). Bits without a FaultType are left out and logged once per change (`LOGE`) | Yes (removes a false `relayMalfunction` IMMEDIATE_DISABLE) | No | No | No | SWF-025 (SWF-ACT-025); TSR-615 (input); WP-O-04 MON-04 / K-03 (no false T1 trigger from this cause) | WP-W-04 (SW FMEA SWF-025), WP-W-06 (unit test), WP-O-04 (MON-04) | Native unit test; process replay | This change |

The schema change only appends an enumerant, so old logs read unchanged and old readers see the new value as an unknown enumerant. `selfdrived` matches on `relayMalfunction` only (`selfdrived.py:341`), so `interruptRateSoundDma` raises no event. A real relay malfunction (bit 0) is still reported.

## 2. Behaviour changes to watch

| Change | Effect | Check |
|---|---|---|
| Sound DMA interrupt-rate fault (bit 27) | Previously a spurious `relayMalfunction` (IMMEDIATE_DISABLE, NO_ENTRY for the drive); now `interruptRateSoundDma` in `pandaStates.faults`, no event | Drive logs: `pandaStates.faults`; `swaglog` for "fault bits without a FaultType" |
| Unknown future fault bits | Dropped from the list and logged; no longer a false `relayMalfunction`. They raise no event either: TSR-615 (disable on any panda fault flag) stays open as before | TSR-615 status |

## 3. Verification results

| Check | Result |
|---|---|
| `tests/test_pandad_faults` (new): no faults; bit 27 alone; bit 27 with unknown bits 28 and 31; only unknown bits; real relay malfunction with an unknown bit; every bit except bit 0; `PANDA_FAULT_TYPE_MAX` equals the last FaultType in the schema; panda bit 27 equals `interruptRateSoundDma` | Pass |
| Mutation check: list sized from all set bits again | Test fails (`faults.size() == 1U`, bit 27 with unknown bits) |
| `tests/test_pandad_canprotocol` | Pass |
| `scons` | pandad and both pandad tests build. `scons -k` on the full tree builds every target except the two modeld `*_tinygrad.pkl` models, whose ONNX inputs are Git LFS pointers in the test environment (unrelated to this change) |
| `log.capnp` with the new enumerant | Loads (`log.PandaState.FaultType.interruptRateSoundDma == 27`) |
| Process replay (CI, PR #48) | 0 changed, 66 passed, 0 errors |
| HIL | **Not run** |

## 4. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Set SWF-ACT-025 to done and rate SWF-025 detection with the new test once `sw-fmea.yaml` is on `liondriver-dev` | FMEA merge |
| OI-2 | TSR-615: react to panda faults other than `relayMalfunction` (unchanged by this change) | Later change |
