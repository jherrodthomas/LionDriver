# Change impact: the Toyota CarController sends the inactive acceleration while longitudinal control is not active (pin opendbc f23b4fa)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to the opendbc Toyota port and the pin that brings it in (change type CT-1, [WP-P-02](../WP-P-02-change-management.md); pin rule [WP-M-11](../../01-management/WP-M-11-upstream-and-supplier-management.md) §3). The CarController took `ACCEL_CMD` from `actuators.accel` with no `longActive` gate and relied on LongControl returning 0 in its off state. A defect or a stale `carControl` upstream could therefore pass a braking request through while the item is not engaged (SW FMEA SWF-052.C1, HZ-006; the panda refuses it while controls are not allowed, TSR-203). The same pin bump lets the host mutation run cover the opendbc stock-AEB cap (SWF-093.C2), which had been the open part of SWF-ACT-081.

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-29** in this LionDriver PR; unit-tested and mutation-checked in CI; not verified on the vehicle; not reviewed independently |
| Change requests | jherrodthomas/opendbc#22 (merged as `f23b4fa`, change commit `56dede1`); this LionDriver PR (pin `4d1a056` → `f23b4fa`) |
| Class | SR-Q (`opendbc_repo`, `opendbc/car/toyota/carcontroller.py`; car code, not the safety model) ([safety-relevant-paths.txt](../safety-relevant-paths.txt)) |
| Reference configuration affected | Yes: the Corolla TSS2 longitudinal command. Other Toyota platforms too |
| Requirements | No host requirement for the inactive value; TSR-203 is the envelope's. TSR-208 (the PCM's response to the inactive value, AOU-05R) is unchanged and unverified (SWF-ACT-053) |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Verification |
|---|---|---|---|
| Inactive value | `opendbc/car/toyota/carcontroller.py` | While `CC.longActive` is false, `pcm_accel_cmd = INACTIVE_ACCEL` (0 m/s², the panda's `inactive_accel`) after the clip, on 0x343 and on 0x183 for SecOC cars; `self.accel` follows, so the final rate limit starts from 0 when control becomes active | `opendbc/car/toyota/tests/test_carcontroller.py`, three new cases: the inactive value for -3.5, -0.5 and +1.5 m/s² requests while not active, the decoded `ACC_CONTROL.ACCEL_CMD` frame, and a return to active control within the final rate limit. Toyota tests 20 pass, `test_car_interfaces` 255 pass, ruff and ty clean |
| Mutation | `tools/ci/host_mutants.toml` | IA-1 (`actuators.accel` passed through while inactive) for SWF-052.C1; AE-5 (cap not applied during a stock AEB event) and AE-6 (cap at +0.5) for SWF-093.C2. Each killed by `test_carcontroller.py`, which `host_mutation.py` runs from the LionDriver checkout; 59 host mutants, all killed | `tools/ci/host_mutation.py` |
| Pin | `opendbc_repo` | `4d1a056` → `f23b4fa`; the only commit between them is `56dede1` | `check_pin_records.py`; the safety suite, MISRA and safety mutation jobs run on the new pin in CI. The safety code is unchanged, so the plant model results are identical (`plant-results.md` changes only in the SHA it names) |

## 2. Impact

- **Safety:** removes a path by which a non-zero acceleration request reaches 0x343 while longitudinal control is not active (WP-A-04 BE-4.13). The panda still refuses any value other than the inactive one while controls are not allowed.
- **Driving:** none in normal operation. LongControl already returns 0 when it is off, so the command was 0 in these states before. When control becomes active again, the command leaves 0 at no more than the final rate limit, as before.
- **Process replay:** `card` sends 0x343 from the recorded `carControl`; with LongControl at 0 in the off state, no frame should change. CI shows it.
- **Upstream:** a fork difference in the Toyota port, carried at each opendbc sync (WP-M-11).

## 3. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Vehicle test of the PCM response when the inactive value replaces an active deceleration (TSR-208, AOU-05R, SWF-ACT-053) | G3 |
