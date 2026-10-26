# Change impact: no engagement on an active EPS or ABS/VSC fault code (DQ-132)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant host software (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). It implements the project lead's decision on DQ-132, option A (2026-10-25): read the EPS and ABS/VSC fault codes at start-up and block engagement on an active one. DQ-132 confirms DQ-056 A (2026-10-14), which set FSR-02.12 and TSR-629 but left the implementation open.

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-25**; unit-tested on the host with mocked UDS responses; **not verified on the vehicle**; not reviewed independently |
| Change requests | This LionDriver change |
| Reference configuration affected | Yes, the reference platform only (`assured_config.ASSURED_PLATFORMS`, the Corolla TSS2). Other platforms send no new frames and get no new events |
| Decisions | DQ-132 A (confirms DQ-056 A) |
| Requirements | FSR-02.12 (status); TSR-629 refined (WP-S-02 v0.57); new SWSR-629, 629a, 629b, 629c, 629d (WP-W-02 v0.47); TSR-811 status and OI-4 closed (WP-S-06 v0.2); OPS-01 and OI-2 closed (WP-O-02 v0.3); INS-06 (WP-O-01 v0.5); FSR-02.12 status (WP-C-04 v0.30); vehicle case VS-SQ-20 (WP-S-09 v0.5) |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Verification |
|---|---|---|---|
| Start-up read (SWSR-629, 629a) | `selfdrive/car/vehicle_dtc.py` (new), `selfdrive/car/card.py`, `common/params_keys.h` (`VehicleDtcStatus`) | In `Car.__init__`, after fingerprinting and before `FirmwareQueryDone`, `card` checks that the car is stationary (20 consecutive valid `carState` samples with standstill, within 1 s) and then sends tester present and UDS ReadDTCInformation, reportDTCByStatusMask (`0x19 0x02 0xFF`) on bus 0 to the EPS and ABS addresses of the firmware-query table (`0x7a1`, `0x7b0`). It stores the result per ECU in `VehicleDtcStatus` and logs every code with its status. If the car is not seen stationary, nothing is sent. Not done in a log replay or in the simulator (`SIMULATION` with `NOBOARD`, the LD-FSR-001 test for no vehicle CAN bus) | `selfdrive/car/tests/test_vehicle_dtc.py`: request bytes and addresses, multi-frame list, no frame when moving, without valid CAN or when the car starts to move, a static check that the only call is in `__init__` before `FirmwareQueryDone`. 33 passed on 2026-10-25 (host, Python 3.12) |
| Active codes (SWSR-629b) | `vehicle_dtc.py` | Active = status AND availability AND `0x8B` (bits 0, 1, 3, 7); pending and history bits alone do not count. `EXEMPT_DTCS` is empty | Each bit alone; unsupported bit ignored; exempt code |
| Read failure (SWSR-629c) | `vehicle_dtc.py` | 0.5 s per response, 2 s per attempt, 2 attempts; silent, negative, malformed, unsupported-bits or missing-address → failed; an error → not read, `card` keeps running | Silent, `0x7F 0x19 0x11`, malformed, availability `0x30`, no address, raised error; retry count |
| Entry check (SWSR-629d) | `selfdrive/selfdrived/selfdrived.py` (`dtc_entry_events`, `add_reference_entry_events`), `events.py`, `cereal/log.capnp` (`epsFaultCode` @113, `brakeFaultCode` @114, `faultCodeReadFailed` @115) | On the reference platform `selfdrived` reads the record once at start (card writes it before `CarParams`) and raises NO_ENTRY "EPS Fault Code: Have Car Checked", "ABS/VSC Fault Code: Have Car Checked" or "Fault Code Check Failed: Restart Car". A missing record counts as not read. Entry only | `selfdrive/selfdrived/tests/test_vehicle_dtc_entry.py` (9 tests) and the updated helper in `test_assured_config.py`: run here with stubbed `msgq` and `Params` (the environment has neither): the 9 pass; of the selfdrived and car test folders 878 pass, and 4 existing tests (2 in `test_assured_config.py`, 2 in `test_alerts.py`) fail only because they need the compiled params library; `test_cruise_speed.py` needs the acados build and was not run. **CI to confirm** |

## 2. Design choices

- **Where the read runs.** In the firmware-query window of `card`: `pandad` holds the panda in ELM327 (no actuation, controls not allowed) until `card` sets `FirmwareQueryDone` and `ControlsReady`. So the item cannot be engaged during the read, and once the car safety mode is set no read is possible: the Toyota safety mode does not let `0x7a1` or `0x7b0` through. The cached-CarParams path skips the firmware query but not this read, so it runs at every start of `card`, that is every ignition.
- **Once per ignition, not during the drive.** DQ-132 A reads the codes at start-up and never while driving, so FSR-02.12's "while the item can engage" is met as "at every start-up". A code that sets after the start-up read is not read by the item until the next start-up; during the drive the live fault signals cover it (EPS status `0x262` and the steering-fault events, TSR-110; `espDisabled` and `accFaulted` in `car_events.py`), and the driver's lamp.
- **Never while driving.** A stationary check from the car's own wheel speeds comes first. A start while rolling (device booted on the move, `card` restarted) sends nothing.
- **Service.** UDS `0x19 0x02` is the service of `tools/scripts/car/read_dtc_status.py`, the tool INS-06 names. The read does not change the diagnostic session. Tester present first, as in the firmware query. Addresses come from the firmware-query table. **Not knowable from the repository:** several Corolla TSS2 EPS and ABS firmware versions in that table answer only the Toyota KWP version request, so these ECUs may not support `0x19`. If so, the read fails and the item does not engage on that car. VS-SQ-20 (b) finds this before any road use; then a change request adds the service the ECU supports.
- **Which bits count.** Bits 0, 1, 3, 7. Confirmed (bit 3) stays set after a fault heals, until the code is cleared. That matches AOU-09 and INS-06, "no active DTC", and the service rule that codes are cleared only under a recorded repair (SVC-10): a stored chassis fault sends the car to the workshop. Pending alone (bit 2) is not matured and would refuse engagement on transient start-up events, for example low voltage while cranking. It is logged, not blocking.
- **Timeout and failure policy: block until the next start-up.** An unread, incomplete or malformed answer counts as "not known healthy" and refuses engagement with its own alert, until the next stationary start. Why: the ratings assume a healthy car (AOU-09, AOU-10). DQ-132 exists so that this does not rest on the driver alone. Treating an unanswered read as healthy would quietly reduce the check to the lamp check whenever an ECU is slow or silent. Cost: availability. A car whose ECU never answers cannot be used with the item until the read is adapted. This is bounded by VS-SQ-20, and repeated failures show in the field log (WP-O-04). A second attempt for the ECUs that did not answer limits refusals from a single lost frame. No retry while driving: the car safety mode blocks the frames, and a read while moving is excluded by design.

## 3. Impact

| Area | Impact |
|---|---|
| HARA, safety goals | None. The change adds an entry condition; nothing is disengaged |
| FSC / TSC | FSR-02.12 now implemented in software; TSR-629 wording refined (§1). AOU-09 and AOU-10 keep the driver's lamp check (TSR-811, OPS-01) as a second barrier, and the only one for engine, camera and radar codes |
| SW FMEA, STPA | New failure modes for the SW FMEA owner: read reports healthy wrongly (status parse, wrong address); read never answers (availability); read sent while moving (excluded by the stationary check and the ELM327 window). STPA: a no-entry condition like CC-14 and CC-18 |
| Start-up time | Adds up to 5 s before `FirmwareQueryDone`: the 1 s stationary check, then at most 2 attempts of 2 s. Typically under 1 s with both ECUs answering |
| Other ECUs and the vehicle | Two read-only services per ECU, sent while parked and in the same window as the firmware query, which already sends tester present and session requests to these ECUs. No session change, no clearing. VS-SQ-20 (e) checks for side effects |
| Process replay, simulator | Not affected: card skips the read and selfdrived the gate under `REPLAY`, and in the simulator (`SIMULATION` with `NOBOARD`), whose simulated Corolla has no diagnostic ECUs; the simulator therefore does not exercise this check |
| User information (WP-O-03) | The three new alerts and what to do: have the car checked; restart while stationary (OI-2) |
| Params / build | New key `VehicleDtcStatus` in `common/params_keys.h` (needs the C++ params library rebuilt); three new `EventName` values |

## 4. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Vehicle check per ECU: WP-S-09 VS-SQ-20, including whether the reference car's EPS and ABS/VSC answer `0x19` | Vehicle test, before road use with this build |
| OI-2 | User information (WP-O-03): the three alerts and what to do | WP-O-03 owner |
| OI-3 | SW FMEA rows for the read (§3) | SW FMEA owner |
| OI-4 | The alert does not say which code is active; the code is in the log and on a scan tool | Accepted for now |
