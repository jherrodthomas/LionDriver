# Change impact: no drive requested during a stock AEB event (DQ-300)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant host software (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). It implements the project lead's decision of 2026-10-18 on DQ-300, option A: while the car reports a stock AEB event, LionDriver requests zero acceleration (no added drive), and the AOU-04R vehicle test still runs. It is the software action SFM-ACT-020 of System FMEA SFM-036 (FTA cut set MCS-07.10, SG-07).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-19** in this LionDriver PR; unit-tested; not verified in the vehicle; not reviewed independently |
| Change requests | This LionDriver PR |
| Reference configuration affected | Yes: every car with openpilot longitudinal control that reports `carState.stockAeb`. On the reference Corolla TSS2 it comes from `PRE_COLLISION` on the camera bus (`PRECOLLISION_ACTIVE` with a braking force), which is read whenever alpha longitudinal is off, as in the assured configuration |
| Decision | DQ-300 A |
| Requirements | Parent TSR and SWSR to be written by their owners (safety-concept session, WP-W-02); SFM-ACT-020 status by the System FMEA owner |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Verification |
|---|---|---|---|
| Stand down during stock AEB | `selfdrive/controls/lib/longcontrol.py` (`stock_aeb_stand_down`), `selfdrive/controls/controlsd.py` | While `carState.stockAeb` is true, `controlsd` caps the longitudinal target and the upper PID limit at 0 m/s². The longitudinal controller clips its output to the limits, so `actuators.accel` is at most 0 from the first frame of the event. A braking request from the planner still passes. When the event ends, the normal target and limits apply again | 4 unit tests in `selfdrive/controls/tests/test_stock_aeb.py`. One runs the reference car's controller wound up to a positive request: from the first AEB frame the output is ≤ 0 |

"Zero acceleration (no added drive)" is implemented as "no positive acceleration request": a braking request is kept, because braking alongside the car's AEB adds no drive.

## 2. Limits of this change

- It acts on the host's request (`actuators.accel`). The Toyota car controller in opendbc shapes that request before it reaches the engine computer:
  - A rate limit of 4 m/s³ on the falling request means a +1.5 m/s² request reaches 0 about 0.4 s after the event starts.
  - Its own feedback loop and pitch compensation can add a small positive term to the engine-computer command.

  Both are opendbc behaviour, unchanged here (OI-2).
- It relies on the car reporting the event. An AEB event the car does not report on `PRE_COLLISION` is not seen; the AOU-04R vehicle test of the engine computer's priority stays the main measure.
- A false AEB report cuts the drive request while it lasts, as the decision accepted.

## 3. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Parent TSR and SWSR; SFM-ACT-020 status | Their owners |
| OI-2 | Whether the opendbc Toyota controller should also skip its rate limit and positive terms during stock AEB, so the engine-computer command itself is ≤ 0 at once | Technical choice, after AOU-04R |
| OI-3 | AOU-04R vehicle test, and a check on the car that `stockAeb` is reported during a real or staged PCS event | Vehicle test |
