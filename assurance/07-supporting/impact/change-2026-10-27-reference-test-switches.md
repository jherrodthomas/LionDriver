# Change impact: test-only environment switches have no effect in the reference build on the device (DQ-425)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant host software (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). Ten environment switches meant for tests, replay and the simulator were read by the processes `manager` starts on the device, and each bypasses a check or fakes an input (SW FMEA SWF-028.C2, SWF-030.C2, SWF-058.C2, SWF-082.C1). No launch path sets them, but a shell on the device can. This change makes `manager` remove them from its environment before it starts any process, in the reference build on the device only. It follows the reasoning of DQ-131 A (the reference build leaves the debug modes out) and is recorded as a reversible technical choice, DQ-425 (decider: Claude, option A).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-27** in this LionDriver PR; unit-tested and mutation-checked in CI; not verified on the device; not reviewed independently |
| Change requests | This LionDriver PR |
| Class | SR-Q (`openpilot/system/manager/manager.py`, `openpilot/system/manager/reference_env.py`) ([safety-relevant-paths.txt](../safety-relevant-paths.txt)) |
| Reference configuration affected | Yes: a reference build (the default) on comma hardware. On a PC, and in a build with `LIONDRIVER_REFERENCE=` (empty), nothing changes |
| Decision | DQ-425 A (decider: Claude; reversible; the lead may object until 2026-10-30) |
| Requirements | TSR-603 and TSR-613 ([WP-S-02](../../03-system/WP-S-02-technical-safety-requirements.md)) in part, the REPLAY, SIMULATION and TESTING_CLOSET switches of SWF-ACT-031; no new requirement. A parent TSR or SWSR for "no test hook in the reference build" is for the safety-concept session (OI-1) |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Verification |
|---|---|---|---|
| Switches removed before any process starts | `openpilot/system/manager/reference_env.py` (new), `openpilot/system/manager/manager.py` | In `manager_thread`, before `BLOCK` is read and before `ensure_running` starts a process, `remove_test_switches(os.environ, REFERENCE_BUILD, not PC)` removes `REPLAY`, `SIMULATION`, `TESTING_CLOSET`, `FINGERPRINT`, `BLOCK`, `BOARDD_SKIP_FW_CHECK`, `STARTED`, `FAKESEND`, `SPI_ERR_PROB` and `BOARDD_LOOPBACK`, and logs an error event naming the ones it removed. Every process `manager` starts inherits its environment, so none sees them. A set but empty switch counts, as the readers test for presence | `openpilot/system/manager/test/test_reference_env.py` (6 tests): every switch removed alone and together, other variables kept, PC and non-reference builds unchanged, the call comes before `BLOCK` is read and before any process starts, and each switch is still read somewhere in the sources. `tools/ci/host_mutation.py` mutants RE-1..RE-4 (no removal, removal on a PC too, one switch left set, call dropped) are each killed. Run locally: manager tests 14 passed, 2 skipped |

## 2. Impact

- **Safety:** removes the paths by which one environment variable makes selfdrived engage on a panda grant (REPLAY), relaxes the input checks (SIMULATION, TESTING_CLOSET), overrides the car identification (FINGERPRINT), stops a process without an event (BLOCK), skips the panda firmware check (BOARDD_SKIP_FW_CHECK), keeps a car mode with ignition off (STARTED) or disturbs the panda link (FAKESEND, SPI_ERR_PROB, BOARDD_LOOPBACK). The normal control path is unchanged: with none of them set, the environment is the same as before.
- **Not covered:** a process started by hand from a shell, which bypasses `manager` (cybersecurity: shell access, CSG-03); the cached-CarParams reuse after a VIN match (SWF-058.C2, SWF-ACT-057); a process that never starts for another reason (SWF-082.C1, SWF-ACT-070); the big-model path of SWF-ACT-031.
- **Development:** the simulator, process replay and the tests run on a PC and keep every switch. A developer who needs a switch on the device builds with `LIONDRIVER_REFERENCE=` (empty), which is outside the safety claims, as for DQ-131.
- **Upstream:** at each openpilot sync (WP-M-11), a new test-only `getenv` in a process `manager` starts needs adding to `TEST_SWITCHES`; the test fails if a listed switch is no longer read anywhere.

## 3. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Parent requirement: a TSR or SWSR stating that no test hook changes the reference build's behaviour on the device | Safety-concept session |
| OI-2 | Check on the reference device: start with each switch set; the log shows it removed and the processes behave as without it | Vehicle test (WP-V-07) |
| OI-3 | Review `TEST_SWITCHES` at each upstream sync (sync report, WP-M-11) | Each sync |
