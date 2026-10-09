# Configuration: 2020 Toyota Corolla LE (U.S. market)

The first vehicle configuration, and the car on which every [platform assumption](../../platform/README.md#assumptions-register-first-entries) is first checked against real hardware.

> [!WARNING]
> **Draft.** Parameters below are read from the pinned upstream source. Assumption checks have not been performed on the vehicle yet.

## Configuration baseline

Read from `opendbc_repo` at commit `229dc7062d8986b4f954c7c97875b4ffd0044d12`, the commit LionDriver pins.

| Parameter | Value | Source |
|---|---|---|
| Platform | `TOYOTA_COROLLA_TSS2` (Toyota Safety Sense 2.0) | `opendbc/car/toyota/values.py` |
| Vehicle | 3,060 lb · wheelbase 2.67 m · steering ratio 13.9 | `values.py` |
| Lateral control | Torque (STEERING_LKA), not angle (LTA) | `interface.py`: no `ANGLE_CONTROL` flag |
| Longitudinal control | openpilot (TSS2 camera ACC can be blocked) · stop and go | `interface.py` |
| Safety mode | `toyota`, safety parameter `73`: EPS factor 73, no flags | `interface.py`, `values.py` (`EPS_SCALE`) |
| Steering torque limit | 1500 · rise 15 per frame · fall 25 per frame · within 350 of EPS torque · 450 per 250 ms | `opendbc/safety/modes/toyota.h` |
| Acceleration limits | panda allows −3.5 to +2.0 m/s² · openpilot commands up to +2.0 (TSS2 raised limit) | `toyota.h`, `values.py` |

## Assumption checks

| Assumption | Check on this vehicle | Status |
|---|---|---|
| ASM-V-01 EPS limits its own output | EPS fault and torque-limit behavior under out-of-range commands, on a test rig or track | ⚪ To verify |
| ASM-V-02 Driver can overpower max torque | Measured steering-wheel torque at command 1500 | ⚪ To verify |
| ASM-V-03 Pedal state on CAN, fast and protected | PCM_CRUISE (0x1D2, checksummed) and BRAKE_MODULE (0x226) rates from logs | ⚪ To verify |
| ASM-V-04 Deliberate cruise engagement | Engagement taken from the stock PCM_CRUISE rising edge | 🟡 Design confirmed in source |
| ASM-V-05 Speed signals with fault indication | WHEEL_SPEEDS (0xAA) carries per-wheel fault bits, checked by the safety mode | 🟡 Design confirmed in source |
| ASM-V-06 All commands pass through the harness | Relay-malfunction detection on LKA, LTA and ACC frames | 🟡 Design confirmed in source |
| ASM-V-07 Powertrain honors accel limits | Measured response to requests at the limits | ⚪ To verify |
| ASM-V-08 Stock emergency braking available | PCS behavior with openpilot longitudinal engaged | ⚪ To verify |

## Evidence

### Toyota safety mode: independent equivalence check

The Toyota safety mode was re-implemented independently in [XZACT](https://github.com/jherrodthomas/XZACT-Lang/tree/claude/admiring-ritchie-hneag0/apps/openpilot_toyota_safety) and compared against the unmodified opendbc C at this exact commit:

| Check | Result |
|---|---|
| Event traces byte-identical (directed, exhaustive sweeps, 64 randomized drives over every mode-flag combination) | **72 / 72** · 1,703,142 events |
| Upstream lines the Toyota mode can reach, executed (gcov) | **100%** |
| Planted bugs detected | **30 / 30** |

**What this shows:** the safety mode's behavior is fully specified by its tests, and an independent implementation reproduces it exactly, including at every limit boundary.

**What it does not show:** that the limits are the *right* limits for this car (that comes from the HARA and the assumption checks above), or anything about timing on the panda's microcontroller.
