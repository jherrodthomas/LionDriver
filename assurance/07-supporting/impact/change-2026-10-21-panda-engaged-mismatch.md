# Change impact: panda pin to `f4803c5`, heartbeat "not engaged" revokes within 0.3 s and sounds the siren if cruise stays on (TSR-307(a), TSR-516(c))

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-21** in this LionDriver PR; host-tested; not verified on hardware; not reviewed independently |
| Pin | panda `8a69ccf` → `f4803c5` (merge commit of [jherrodthomas/panda#21](https://github.com/jherrodthomas/panda/pull/21), change commit `895dc44`). opendbc unchanged |
| Decision | The lead asked for the fix in chat on 2026-10-21 ("Yes, with a cancel-lag guard") and for panda#21 to be merged ("Merge now"). The requirements were already set (TSR-307(a) ≤ 0.3 s; TSR-516(b)/(c), SWSR-516b 0.5 s); the guard reuses them. Running the check in the reference build only and reusing the 3 s heartbeat siren are Claude's choices (reversible) |
| Requirements | TSR-307(a), SWSR-307; TSR-516(b)/(c), SWSR-516, SWSR-516b; SWSR-401a |
| Reference configuration affected | Yes: the check is compiled only with `LIONDRIVER_REFERENCE`; other builds keep the 1 Hz check of `main.c` (three ticks) and are unchanged |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| panda `895dc44` | `board/drivers/engaged_mismatch.h` (new), `drivers.h`, `main.c`, `heartbeat_siren.h` (third input renamed `start_siren`), `tests/engaged_mismatch` (new, 10 tests), `tests/hitl/test_12_rx_timeout.py`, `test_15_heartbeat_siren.py` | In the 100 Hz safety task, an episode starts at the first heartbeat that reports "not engaged" while authority is granted. At 30 ticks (0.3 s) authority is revoked (SWSR-307). At 50 ticks (0.5 s), if PCM cruise is still active, the existing 3 s heartbeat siren starts once (SWSR-516b, 516(c)). An "engaged" heartbeat, or a cruise drop after the revocation, ends the episode; a mode change resets it. Before, only the 1 Hz check revoked, after three ticks (2–3 s), with no siren. The HIL heartbeat helper now reports "engaged" so the existing cases stay valid | Yes (detection time 2–3 s → 0.3 s; a siren where there was none) | Yes (more revocations if the heartbeat flag flickers; see §2) | No | No | MCS-02.9 (WP-A-04); SG-01, SG-02; GAP-06 | WP-W-02 SWSR-307, 401a, 516, 516b; WP-S-02 TSR-307, TSR-516 status (FSC/TSC owner); WP-S-04 §5; `assurance/sim` | panda host tests, panda MISRA (both builds), plant simulation, HIL `test_15` | Lead in chat, 2026-10-21 |
| this PR | `panda`, WP-W-02 v0.42, WP-W-05 §5.2 (generated from `state-machines/sm-toy-auth.yaml`: new T6a, reference build; T6 kept as the upstream 1 Hz backstop and marked as not meeting SWSR-307) and its charts, `assurance/sim/plant/sim_panda.c` (follows `main.c`), `test_plant.py`, `engaged_mismatch.py` (text from the rows) and `test_engaged_mismatch.py` (expects the 0.3 s revocation and the siren), `.github/workflows/safety.yaml` (new host suite), sim results | Pin; records state the implemented check | — | — | — | — | — | — | — | — |

## 2. Effect on the driver

- **selfdrived stops while pandad keeps the heartbeat** (MCS-02.9): authority is revoked 0.39–0.48 s after the stop instead of 2.25–3.16 s, and the panda siren sounds at 0.63–0.88 s, where there was none. The driver now corrects at 2.13–2.38 s instead of 2.32–3.37 s ([engaged-mismatch.md](../../sim/results/engaged-mismatch.md), synthetic, no evidence credit). Peak drift: straight 0.41–0.52 m (1.03–1.04 m before), inside the ODD 1.70–3.35 m (3.67–4.55 m), at the ODD curve bound 4.16–8.78 m (7.36–9.83 m). At the curve bound the body still reaches the lane line at 1.25–1.72 s, before the correction: the item stops steering at 0.1 s, so the revocation does not stop that drift; the earlier cue shortens it.
- **Ordinary disengagements stay silent** as long as PCM cruise drops within 0.5 s of the first "not engaged" heartbeat. A brake press or a PCM cruise drop is seen by the envelope's own RX hook, which revokes before the heartbeat changes (TSR-301, TSR-302). Toyota has no separate cancel-button event: openpilot disengages on a cancel only after the PCM has dropped cruise. Every disengagement openpilot makes on its own (soft disable, USER_DISABLE) sends a cruise cancel; if the PCM takes longer than 0.5 s to honour it, the siren would sound on that disengagement. That lag is not yet measured (OI-1).
- **A heartbeat flag that flickers** to "not engaged" for less than 0.3 s while openpilot is engaged revokes nothing; one that stays "not engaged" for 0.3 s now revokes after 0.3 s instead of 2–3 s.

## 3. Verification results

| Check | Result |
|---|---|
| panda host tests (local) | All seven suites pass. `tests/engaged_mismatch`: revocation at tick 30 and not at 29, siren once at tick 50 with cruise on, no siren when cruise drops after the revocation, reset on an "engaged" heartbeat and on a mode change, no episode while authority is not granted, stock-cruise resume |
| panda MISRA (local) | cppcheck MISRA C:2012 clean in both builds, with the host gcc include path (the ARM toolchain is not installed locally; CI runs the real script) |
| Mutation (local, by hand) | A cruise check at the siren time turned out equivalent to the episode end and was removed; tests added for the cruise drop without revocation and the stock-cruise resume |
| Plant simulation (local) | `sim_panda.c` follows the new `safety_task_handler` body statement by statement (`test_plant.py`); engaged-mismatch study as §2. `plant-results.md` and `override-l2.md` change only in the pinned SHA they name; the other studies and figures are unchanged |
| HIL | **Not run** (D-04). New case `test_not_engaged_heartbeat_revokes_within_0_3_s` in `test_15_heartbeat_siren.py` |

## 4. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Measure the PCM cancel lag in reference logs: time from the first heartbeat with `engaged` false to PCM_CRUISE CRUISE_ACTIVE 0, for each disengagement openpilot makes on its own (WP-W-02 OI-18). It could not be measured here: the public CI logs are not reachable from this environment and the process-replay references are not causal. If it exceeds 0.5 s, the threshold goes to the lead as a vehicle-behaviour question | Release |
| OI-2 | HIL on the bench: `test_15` not-engaged case, siren by ear (WP-S-04 M-05) | HIL bench (D-04) |
| OI-3 | TSR-307(a) and TSR-516 status in WP-S-02, WP-S-04 §5 and WP-C-04 still state the 1 Hz check and no siren (FSC/TSC owner) | Next WP-S-02 revision |
| OI-4 | SW FMEA: the cause "heartbeat not engaged, authority kept for 2–3 s" now has a control; the new module as a cause and control row (SW FMEA owner). The fmdtools SG-02 model's 3.0 s revocation to be updated to the simulated 0.39–0.48 s | SW FMEA revision |
