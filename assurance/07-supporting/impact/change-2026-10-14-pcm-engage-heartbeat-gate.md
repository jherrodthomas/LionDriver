# Change impact: PCM-edge authority gated on the heartbeat's engaged flag

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware and host software (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). It closes STPA finding LS-06 ([WP-A-05](../../08-analyses/WP-A-05-stpa.md) OI-9).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Integrated 2026-10-14: LionDriver pins opendbc `9a13f60` (merge commit of `b9f7451`, [jherrodthomas/opendbc#14](https://github.com/jherrodthomas/opendbc/pull/14)); unit-tested, MISRA-clean in both variants, reference-variant mutation run; not verified on the bench or the vehicle; not reviewed independently** |
| Change requests | [jherrodthomas/opendbc#14](https://github.com/jherrodthomas/opendbc/pull/14); this LionDriver PR (pin, `selfdrived`, requirements) |
| Reference configuration affected | Yes, in the reference build only (`LIONDRIVER_REFERENCE=1`, the default) for the opendbc part; the host part applies to every build |
| Decision | The user chose the heartbeat gate over a shorter mismatch window (2026-10-14) |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Requirements | Verification |
|---|---|---|---|---|
| opendbc `b9f7451` | `opendbc/safety/safety.h`, `opendbc/safety/tests/libsafety/safety.c`, `opendbc/safety/tests/test_toyota.py` | In the reference build, a PCM cruise rising edge no longer grants `controls_allowed` by itself. It opens a 1 s window. Authority is granted once `heartbeat_engaged` is set and the RX checks allow engagement, at the edge or in the 100 Hz safety task (never from the host command handler, so no new interrupt context writes the flag). The window is cancelled by cruise off, a brake rising edge, an RX fault or a safety mode change; once it expires, only a new rising edge opens another | TSR-301 (WP-S-02 v0.20) | 3 new Toyota tests (reference variant); full safety suite in both variants (3334 tests); MISRA in both variants; reference-variant mutation: 3 survivors, the known upstream `lateral.h` boundaries, none in the new code |
| openpilot `selfdrived` | `selfdrive/selfdrived/supervision.py`, `selfdrived.py`, `tests/test_supervision.py` | `controlsMismatch` does not count `pandaStates` samples taken in the first 0.3 s after engaging. The panda's grant now waits for the next 10 Hz heartbeat, so up to two samples can show `controlsAllowed` false at engagement. The 0.5 s bound from the first mismatched frame is unchanged | TSR-621 | 3 new unit tests (13 in the file) |

## 2. Timing at engagement

`pandad` sends the heartbeat with the engaged flag at 10 Hz, after it reads the panda state, and `selfdrived` enables on the same PCM edge. Worst case from the edge: `selfdrived` enables (≤ 10 ms), `pandad`'s next tick reads a stale `selfdriveState` and sends engaged = 0 (≤ 100 ms), the following tick sends engaged = 1 (≤ 100 ms), and the safety task grants within 10 ms. That is about 0.21 s, inside the 0.3 s grace and well inside the 1 s window.

## 3. Behaviour to watch

| Change | Normal-driving risk | How it is bounded |
|---|---|---|
| Heartbeat gate | Engagement takes up to about 0.2 s longer to reach the panda; the item's first actuation frames in that time are refused | Frames refused before the grant do not count towards TX-arrival or rate supervision, which start at the grant (TSR-408); replay and vehicle test to confirm (OI-1) |
| Heartbeat gate | `pandad` restarting during the window (no heartbeat) | No grant; the driver re-engages, the safe direction |
| Engagement grace | A panda that never grants is detected 0.5 s after the first mismatched frame instead of after two samples | The bound is the TSR-621 limit; during it the panda refuses every actuation frame |

## 4. Open items

| ID | Item |
|---|---|
| OI-1 | Vehicle or HIL: measure the edge-to-grant time and confirm that no `controlsMismatch` occurs at engagement over repeated engagements |
| OI-2 | ~~Re-pin LionDriver to the fork's merge commit once opendbc#14 is merged~~ **Closed:** opendbc `9a13f60` |
| OI-3 | ~~WP-A-05 LS-06 status to covered~~ **Done** (WP-A-05 v0.3.1). Open: SW FMEA SWF-039 safety mechanism line; SM-TOY-AUTH model to include the heartbeat condition: **done 2026-10-17**, the model has the window and the B2B harness drives the heartbeat flag ([B2B-TOY-AUTH-2026-10-13](../../05-software/reference-models/results/B2B-TOY-AUTH-2026-10-13.md) §13). The state-machine record has it since 2026-10-16 (state ENGAGE_PENDING, T1a–T1c), and writing it found SM-F1: an edge while MAIN_ON = 0 opened the window (same change record §2), fixed at opendbc `98d3be1` ([change-2026-10-17-pin-98d3be1](change-2026-10-17-pin-98d3be1.md)) |
