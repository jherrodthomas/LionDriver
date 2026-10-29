# Change impact: no engagement while the driver-camera view is open (TSR-610, DQ-427)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant host software (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). The driver-camera view (cabin camera dialog) sets `IsDriverViewEnabled`, which puts `dmonitoringd` in demo mode: the policy runs on a synthetic vehicle state, ignores wheel touches and can switch the monitored seat (SW FMEA SWF-085). The view opens only offroad but can stay open after the car is started, and a parameter left set by tooling or a UI crash kept demo mode for the drive; nothing refused engagement (GAP-20, TSR-610 not met). This change implements TSR-610 and SWSR-610. It is recorded as a reversible technical choice, DQ-427 (decider: Claude, option A).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-29** in this LionDriver PR; unit-tested on the real processes and mutation-checked in CI; not verified on the device; not reviewed independently |
| Change requests | This LionDriver PR |
| Class | SR-Q (`openpilot/selfdrive/selfdrived/selfdrived.py`, `events.py`, `openpilot/selfdrive/monitoring/dmonitoringd.py`, `openpilot/cereal/log.capnp`) ([safety-relevant-paths.txt](../safety-relevant-paths.txt)) |
| Reference configuration affected | Yes, and every other platform: the event is raised only while the parameter is set |
| Decision | DQ-427 A (decider: Claude; reversible; the lead may object until 2026-11-01) |
| Requirements | TSR-610 and SWSR-610 ([WP-S-02](../../03-system/WP-S-02-technical-safety-requirements.md), [WP-W-02](../../05-software/WP-W-02-software-safety-requirements.md)) and CSR-072 ([WP-S-07](../../03-system/WP-S-07-cybersecurity-requirements-architecture.md)): status set to implemented, not verified on the vehicle |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Verification |
|---|---|---|---|
| Demo mode only offroad | `openpilot/selfdrive/monitoring/dmonitoringd.py` | `demo_active(driver_view, car_state_alive)`: demo mode applies only while `carState` is not alive, that is while card is not running (offroad). While started the real driver is monitored with the real inputs and the validity gate, even if the parameter is set | `test_driver_view.py` `TestDmonitoringdLoop` runs the real `dmonitoringd_thread` for three model frames with the parameter set: offroad every step is demo, started none is. `TestDemoModeInDmonitoringd` checks the truth table |
| Engagement interlock | `openpilot/selfdrive/selfdrived/selfdrived.py`, `events.py`, `openpilot/cereal/log.capnp` | `selfdrived` reads `IsDriverViewEnabled` at start and every 0.1 s in its parameter thread, and raises the new event `driverViewActive` (`@116`) while it is set: NO_ENTRY "Close Driver Camera View", SOFT_DISABLE "Driver Camera View Open" (the view covers the onroad screen and its alerts) | `TestDriverViewInterlock`: real `SelfdriveD` constructor, `update_events` and `params_thread`; the event alone gives NO_ENTRY and SOFT_DISABLE and no immediate disable |
| Mutation | `tools/ci/host_mutants.toml` | DV-1 (event not raised), DV-2 (start read), DV-3 (thread read), DV-4 (no soft disable), DV-5 (`demo_active` ignores started), DV-6 (the loop does not call it): each killed. 51 host mutants in all | `tools/ci/host_mutation.py` |

Before the change the new tests fail to import (`demo_active` does not exist). The selfdrived and monitoring suites pass (406 tests).

## 2. Impact

- **Safety:** removes demo mode as a way to lose monitoring of the actual driver while the item is engaged (HZ-013, SWF-085, SFM-022.C4, BE-8.06 / MCS-08.4 in WP-A-04). A view left open blocks engagement with a clear reason.
- **Driver:** a driver who opens the view parked and starts driving must close it before engaging. If the parameter is set while engaged (not possible from the UI, whose buttons are disabled onroad), a soft disable with a take-over alert follows.
- **Not changed:** the UI does not clear the parameter on the onroad transition (option C of DQ-427). The comma four dialog still publishes its own `selfdriveState` while open, a second publisher (WP-A-03 DFI-31, SWF-ACT-076).
- **Process replay:** no recorded segment sets the parameter, so `dmonitoringd` and `selfdrived` outputs are unchanged.
- **Upstream:** a fork difference to carry at each openpilot sync (WP-M-11); the new event number is LionDriver's.

## 3. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Device check: open the view parked, start the car, confirm "Close Driver Camera View" and that monitoring follows the driver (WP-S-09) | G3 |
| OI-2 | Fault-injection scenario VS-FI-23 (params tampering) with this parameter (WP-V-05) | G3 |
| OI-3 | WP-A-04 MCS-08.4 and BE-8.06 text to cite the interlock (FTA document owner) | FTA owner |
