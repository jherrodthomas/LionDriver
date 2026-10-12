# Change impact: per-ID TX rate supervision (reference build)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Integrated 2026-10-12: LionDriver pins opendbc `7993399` and panda `8aa8671` (merge commits on the forks' `master`); not yet verified on hardware (HIL bench D-04); budgets not yet confirmed on reference logs; not reviewed independently** |
| Change requests | [jherrodthomas/opendbc#10](https://github.com/jherrodthomas/opendbc/pull/10), [jherrodthomas/panda#13](https://github.com/jherrodthomas/panda/pull/13), this LionDriver change |
| Design | [DN-01](../../05-software/design-notes/DN-01-tx-rate-supervision.md) (decisions D-1…D-6, §10) |
| Range | opendbc `875e325..7993399`; panda `877730e..8aa8671` |
| Reference configuration affected | Yes, in the reference build only (`LIONDRIVER_REFERENCE`, non-SecOC Toyota); other builds unchanged |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| opendbc `951b459` | `opendbc/safety/declarations.h`, `safety.h`, `modes/defaults.h`, `modes/toyota.h`, tests | Per-ID TX rate supervision: each whitelisted frame of a listed ID is counted in a sliding 250 ms window; beyond `ceil(f × 0.3) + 1 + burst` it is rejected before the content checks; 3 rejections in a half-window while controls are allowed revoke them and set `safety_tx_rate_exceeded` | Yes | Yes (frames refused and authority revoked if the host sends above budget) | No | Yes (a compromised SoC cannot flood actuation IDs or the shared TX queue) | SG-01, SG-03, SG-04, SG-07; FSR-01.08, FSR-01.12; FFI-CM-04; SDF-05 (partly) | WP-S-02 (TSR-518), WP-W-02 (SWSR-518), WP-W-05 (UN-03), WP-W-06 (unit tests), WP-V-05 (HIL flood) | Safety unit tests (both variants, 100 % line coverage); opendbc and panda MISRA; replay of reference logs (peak count per window per ID); HIL test 14 | Taken (maintainer merged, 2026-10-12) |
| panda `b13f48f` | `board/health.h`, `board/main_comms.h`, `python/__init__.py`, `tests/hitl/test_14_tx_rate.py` (new) | Health flag `HEALTH_FLAG_TX_RATE_EXCEEDED` (bit 11) | Yes | No | No | No | TSR-518 (report) | WP-V-05 | Builds, MISRA, host tests; HIL test 14 | Taken (maintainer merged, 2026-10-12) |
| LionDriver | `openpilot/cereal/log.capnp`, `openpilot/selfdrive/pandad/pandad.cc` | `pandaState.txRateExceeded` (field 45) from the flag; `pandad` logs its onset. No alert or engagement logic changes | No (QM host) | No | No | No | TSR-518 (report) | — | Unit tests, process replay | This change |

## 2. Behaviour changes to watch

| Change | Effect | Check |
|---|---|---|
| Host catch-up after a stall | Up to ~29 queued `0x2E4` frames at once pass (unit test, stalls 50–290 ms). A longer stall is revoked by the heartbeat (TSR-407) anyway | Reference logs: largest burst after `card`/`pandad` stalls |
| `0x343` cancel spam (stock longitudinal only) | Extra cancel frames rejected; authority revoked after 3 rejections, which the cancel intends anyway | Not the reference configuration |
| Report latched until the next mode change | `pandaState.txRateExceeded` stays set for the rest of the drive after one revocation | Drive logs |

## 3. Verification results

| Check | Result |
|---|---|
| opendbc safety unit tests, default and `LIONDRIVER_REFERENCE=1` | OK under UBSan and with coverage; 100 % line coverage in both variants |
| Rate tests (reference variant, 5 non-SecOC classes) | Pass: every whitelisted ID has a budget; flood rejected beyond the budget; window slides; 10 s of host cadence passes; at 2× the rate revocation ≤ 0.1 s after the first rejection and ≤ 0.2 s after onset; catch-up bursts after 50–290 ms stalls pass; a rejected frame does not update the torque limits |
| Mutation check | Budget +1 (34 failures), revoke threshold 3 → 30 (5), report flag removed (5), full-window clearing removed (5), fixed 250 ms window (31), brand hook before the rate check (3) |
| opendbc MISRA (cppcheck step); panda `tests/misra/test_misra.sh` (standard and reference) | Clean |
| panda builds (default, reference, fault injection, reference release) | Pass (`-Werror`) |
| `log.capnp` with the new field | Loads |
| Replay, HIL | **Not run** (no reference logs; D-04) |

## 4. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Confirm the budgets on reference logs: peak frame count per 250 ms per TX ID, and the largest catch-up burst (DN-01 §9) | Release |
| OI-2 | HIL test 14 on the bench (D-04) | Release |
| OI-3 | Separate forwarding queue (WP-W-04 OI-2, SDF-05) still open | Later change |

## Addendum: further work products affected (2026-10-12)

The software alignment audit ([RR-2026-008](../../05-software/reviews/RR-2026-008.md) F-30) found that this change also affects: WP-W-09 (TX-rate budgets, window and burst values), WP-W-11 (SoC TX flooding as a cybersecurity threat, if a CSR applies). These were updated in the RR-2026-008 alignment change, not in the change above. The original "WPs affected" entries are left as recorded.
