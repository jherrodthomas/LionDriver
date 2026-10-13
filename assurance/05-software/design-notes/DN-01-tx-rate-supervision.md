# DN-01 Design note: per-ID TX rate supervision (TSR-518)

| Field | Value |
|---|---|
| Work product | DN-01 Design note: per-ID TX rate supervision (supports [WP-W-03](../WP-W-03-software-architecture.md) and [WP-W-05](../WP-W-05-software-unit-design.md) UN-03) |
| Standard reference | ISO 26262-6:2018 §7, §8 |
| ASIL / scope | B‡ (SWSR-518) |
| Version | 0.3 (RR-2026-009 F-27: check order corrected from the code, `0x1D2` and `0x750` budgets, D-4 naming, stale wording; 2026-10-12). 0.2 (decisions recorded and implemented, 2026-10-12). 0.1: proposal |
| Status | Draft — design decisions recorded; implemented in the reference build (opendbc `7993399`, panda `8aa8671`; §10). Not yet verified on hardware; budgets not yet confirmed on logs |
| Requirements | [TSR-518](../../03-system/WP-S-02-technical-safety-requirements.md), [SWSR-518](../WP-W-02-software-safety-requirements.md) |
| Analyses | [WP-A-02](../../08-analyses/WP-A-02-coexistence-freedom-from-interference.md) FFI-CM-04 (SoC floods CAN TX); [WP-W-04](../WP-W-04-software-safety-analysis.md) SDF-05 (shared TX queue delays forwarded PCS frames), OI-2 |
| Units | [WP-W-05](../WP-W-05-software-unit-design.md) UN-03 `safety_tx_hook`, UN-15 `toyota_tx_hook` |
| Author / reviewer | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `682f184` (opendbc `7993399`, panda `8aa8671`) for §10; §1–§8 written before implementation |

## 1. Problem

TSR-518: the envelope shall reject frames of each TX-whitelisted ID sent faster than the nominal rate plus a tolerance, and revoke authority and report when the excess persists while authority is granted (revoke ≤ 0.1 s).

At `8b8c6ae` the TX hook checked content only (the problem this note solved). A faulty or compromised SoC can send in-limit frames at any rate. That has three effects:

| Effect | Bound at `8b8c6ae` | Why it matters |
|---|---|---|
| Faster effective ramp of a per-frame limit | Torque: the real-time check (`max_rt_delta` 450 per 250 ms) bounds the ramp regardless of frame rate. Accel (`0x343`): **no** time-based bound; only the absolute range is checked | A per-frame-limited command sent faster changes the vehicle faster than the limits assume |
| Bus load on bus 0 | None | Delays other frames, including forwarded camera frames (SDF-05) and the car's own traffic |
| Shared TX queue fills | `can_queues[0]` overflow counted (`tx_buffer_overflow`) | Forwarded PCS frames from the camera can be delayed or dropped (SG-07) |

## 2. Facts the design has to respect

### 2.1 What the host sends (reference car: Corolla TSS2, openpilot longitudinal, LKA torque)

From `opendbc_repo/opendbc/car/toyota/carcontroller.py` (`self.frame` counts 100 Hz control cycles):

| ID | Message | Nominal | Notes |
|---|---|---|---|
| `0x2E4` | STEERING_LKA | 100 Hz | Every cycle |
| `0x191` | STEERING_LTA | 50 Hz | TSS2, every 2nd cycle, zero actuation in LKA mode |
| `0x343` | ACC_CONTROL | 33 Hz | Every 3rd cycle; also sent when a PCM cancel is requested |
| `0x412` | LKAS_HUD | 5 Hz + on change | Every 20th cycle, and immediately when an alert starts or stops or a cancel is sent |
| `0x283` | PRE_COLLISION | — | Zero payload only; no openpilot caller sends it |
| `0x1D2` | PCM cancel | event | Only `UNSUPPORTED_DSU` cars; not the reference car |
| `0x750`, `0x411` | Tester present, PCS_HUD | 5 Hz, 1 Hz + on change | `DISABLE_RADAR` only; `0x411` refused in the reference build |

### 2.2 The TX path is bursty

`card` publishes `sendcan` at 100 Hz. `pandad`'s `can_send_thread` forwards every queued `sendcan` message that is **less than 1 s old**, and the queue holds up to 139 messages (`services.py`). After a stall of `card` or `pandad`, the backlog reaches the panda back-to-back over SPI. The TX hook runs in the SPI interrupt (`can_common.h:162`), so the frames of one burst carry nearly the same timestamp.

Consequences:

- A **minimum interval between frames** of one ID is not usable: every catch-up frame after a stall would be rejected, and `0x412` legitimately sends two frames within 50 ms when an alert changes.
- A host stall of 0.3 s or more already revokes authority through the heartbeat (TSR-407). Catch-up frames after such a stall are stale actuation. Rejecting them is the safe direction and not a false positive.

### 2.3 What went wrong with the RX rate check (TSR-403)

An earlier attempt at TSR-403 (RX rate) broke 35 common tests and was backed out. The common tests send many frames at one timer value, so a per-timestamp rate check counts them as a flood. A TX rate check meets the same problem, because the common steering tests call `_tx` hundreds of times without advancing the timer.

## 3. Options

| Option | How | For | Against |
|---|---|---|---|
| A. Minimum interval per ID | Reject a frame if `now - last < period × (1 - tol)` | Simplest | Rejects every burst frame (§2.2); false positives on `0x412` alerts |
| B. Token bucket per ID | Tokens refill at `f × (1 + tol)`, capacity `C`; each frame takes one | Tolerates bursts up to `C`; exact long-term rate | New mechanism; refill arithmetic in the ISR; extra state per ID |
| **C. Windowed count per ID (recommended)** | Count frames per ID in a sliding 250 ms window made of two half-windows; reject when the count exceeds `ceil(f × 0.25 × 1.2) + 1 + burst` | The **same pattern upstream already uses** for angle and curvature commands (`rt_angle_rate_limit_check`, `rt_curvature_rate_limit_check` in `lateral.h`, 1.2× buffer + 1). Tests and reviewers know it. Tolerates bursts within the window | Coarser than B: a flood is detected within one half-window (125 ms), not per frame |

Recommendation: **C**, generalised from the curvature check (two half-windows, so the effective window slides) into a table-driven check in `safety.h` that every mode can use. Toyota uses it in the reference build first.

## 4. Design (option C, implemented)

### 4.1 Configuration

A new optional table in `safety_config`, next to `tx_msgs`:

```c
typedef struct {
  uint32_t addr;
  uint8_t bus;
  uint16_t frequency;  // nominal Hz
  uint8_t burst;       // extra frames tolerated per window
  // state
  uint16_t msgs, msgs_prev;
  uint32_t ts_last;
  uint16_t rejected_in_window;
} TxRateCheck;
```

Toyota reference values (window 250 ms, 1.2× buffer), as implemented at opendbc `7993399`:

| ID | f (Hz) | burst | Budget per 250 ms | Host sends per 250 ms |
|---|---|---|---|---|
| `0x2E4` | 100 | 5 | 36 | 25 |
| `0x191` | 50 | 3 | 19 | 12–13 |
| `0x343` | 33 | 3 | 14 | 8–9 (+ cancel) |
| `0x412` | 5 | 4 | 7 | 1–2 (+ on change) |
| `0x283` | 1 | 2 | 4 | 0 |
| `0x1D2` | 1 | 2 | 4 | 0 (PCM cancel; not sent by the reference car) |
| `0x750` | 5 | 2 | 5 | 0 (radar tester present; DISABLE_RADAR cars only) |

Budget = ⌈f × 0.25 s × 1.2⌉ + 1 + burst (opendbc `7993399`, `safety.h` `tx_rate_check`). The `0x1D2` and `0x750` rows were added at implementation (`modes/toyota.h`, `toyota_tx_rate_checks`); they were missing from the v0.1 proposal.

An ID in the TX whitelist but not in this table is not rate-checked. Unit test T6 enforces that every whitelisted ID of the reference build has a row.

### 4.2 Algorithm (in `safety_tx_hook`, after the whitelist check and before the brand hook)

1. Find the row for (addr, bus). If there is none, no check.
2. Roll the window: if 125 ms have passed since `ts_last`, set `msgs_prev = msgs`, `msgs = 0`, `rejected_in_window = 0`, `ts_last = now`.
3. If `msgs + msgs_prev >= budget`: **reject** the frame and increment `rejected_in_window`. Otherwise count it (`msgs += 1`).
4. **Persistent excess:** if `controls_allowed` and `rejected_in_window >= 3`, clear `controls_allowed` and set a reported flag (§4.3).

Timing, for `0x2E4` (budget 36):

| SoC rate | Budget used up after | Revocation (3rd rejected frame) after flood onset |
|---|---|---|
| 2× (200 Hz) | 25 frames in the first half-window, 11 in the second: ≈ 180 ms | ≈ 190 ms |
| 4× (400 Hz) | ≈ 90 ms | ≈ 95 ms |
| 10× (1 kHz) | ≈ 36 ms | ≈ 40 ms |

An Octave model of this algorithm ([`assurance/models/octave/`](../../models/octave/README.md), a model, not the C code) gives the same 190 ms from an empty window, and 135 ms when the normal frames sent just before the flood count against the budget. TSR-518 asks for revocation ≤ 0.1 s. That holds from the **first rejected frame**, but not from flood onset at rates below about 4×. A shorter window lowers the latency but also lowers the burst tolerance of §2.2. While the flood is below the budget, the steering torque is still bounded by the real-time limit (450 per 250 ms), and every frame is still content-checked. Decision D-6.

Rejected frames do not update the brand limit state: the rate check runs before the brand hook, and the brand hook is called only for a frame within budget (opendbc `7993399`, `safety.h` `safety_tx_hook`: `if (whitelisted && tx_rate_check(msg)) { safety_allowed = current_hooks->tx(msg); }`). The proposal (v0.1) placed the check after the brand hook; the implementation moved it in front, which is simpler and gives the same guarantee (the same rule as the EPS fault gate, opendbc#7). [RR-2026-009](../reviews/RR-2026-009.md) F-27.

### 4.3 Reporting

- Each rejected frame is counted in the existing `safety_tx_blocked`.
- New health flag `HEALTH_FLAG_TX_RATE_EXCEEDED` (bit 11), set while the last revocation was caused by persistent excess, published as `pandaState.txRateExceeded` and logged by `pandad`. This is the same path as `epsFault` (panda#11, LionDriver#38).

### 4.4 Scope

`LIONDRIVER_REFERENCE` only at first, like the other envelope additions. Upstream modes keep their behaviour until the table is filled for them.

## 5. Testing approach (the TSR-403 lesson)

| # | Test | Notes |
|---|---|---|
| T1 | Host cadence passes | Send each ID at its nominal rate for 10 s of simulated time, including `0x412` on-change bursts: no rejection |
| T2 | Flood rejected | Each ID at 2× and 10× its rate: frames beyond the budget rejected; others pass |
| T3 | Revocation timing | `0x2E4` at 2×: `controls_allowed` cleared within 0.1 s of the first rejection; flag set |
| T4 | Burst after stall | 30 frames of `0x2E4` at one timestamp after a 300 ms gap: at most the budget passes; no revocation unless the excess persists |
| T5 | No brand-state side effect | A rejected frame does not change `desired_torque_last` / `rt_torque_last` |
| T6 | Table complete | Every whitelisted ID of the reference build has a rate row |

**Keeping the common tests valid.** The common steering tests send many frames at one timer value. The upstream angle tests handle the same issue: the message helpers advance the libsafety timer by one nominal period per frame (`increment_timer=True`). Proposal: do the same for the Toyota reference variant's TX message helpers.

This interacts with the torque real-time tests, which set the timer themselves (`MAX_RT_INTERVAL` 250 ms). Before changing any helper, the implementation has to run the full suite in both variants and check that every existing assertion still exercises the same boundary. If this does not hold, the fallback is a test-only libsafety helper that resets the TX rate state before each `_tx` call outside the rate tests. That helper would live in `tests/libsafety/safety.c` only and would not change firmware code.

Mutation targets: budget formula, window roll, the persistent-excess threshold, revocation removed.

## 6. False-positive analysis

| Source | Effect | Mitigation |
|---|---|---|
| Host catch-up after a short stall (< 0.3 s) | Up to ~30 `0x2E4` frames at once | Budget 36 per 250 ms. Frames of the stalled period were missing from the window, so the count stays near nominal. A longer stall is already revoked by the heartbeat (TSR-407) |
| `0x412` alert changes | 2–3 extra frames | burst 4 |
| `0x343` cancel spam (`pcm_cancel_cmd` every cycle) | Up to 100 Hz on `0x343` when cancelling with stock longitudinal | Not the reference car (openpilot longitudinal sends `0x343` at 33 Hz with the cancel bit). Rejecting extra cancel frames is harmless: one gets through per budget. **To confirm on reference logs** |
| SPI retransmissions | Duplicate frames | The SPI layer resends only on NACK. A retransmitted frame is a second copy and is counted. Covered by the budget slack |

## 7. What this does not cover

- **Content of in-budget frames.** That is covered by the existing limit checks.
- **SDF-05.** Forwarded camera frames share `can_queues[0]` with SoC frames. This design bounds the SoC's share of the queue but does not reserve capacity for forwarding. WP-W-04 OI-2 (separate forwarding queue) stays open.
- **The RX side.** RX rate checking is TSR-403, which needs reference logs.

## 8. Decisions needed (resolved in §10)

| # | Decision | Recommendation |
|---|---|---|
| D-1 | Option A, B or C | C (§3) |
| D-2 | Budgets and burst values of §4.1 | As proposed; confirm against reference logs (peak count per 250 ms per ID) before release |
| D-3 | Persistent-excess threshold (3 rejected frames per half-window) | As proposed |
| D-4 (DN-01/D-4; not the HIL bench decision D-04 of WP-M-01) | New health flag and `pandaState.txRateExceeded` | Yes, same path as `epsFault` |
| D-5 | Scope: reference build only | Yes, for now |
| D-6 | Reference point of "revoke ≤ 0.1 s" in TSR-518 | Measure from the first rejected frame and amend TSR-518 to say so; the latency from onset (≤ 0.19 s at 2×) is bounded by the existing real-time torque limit. Alternative: a 100 ms window (half-windows of 50 ms) with larger burst values |

## 9. Evidence still needed

- Reference drive logs. For every TX ID: the peak frame count per 250 ms, and the largest catch-up burst seen after a `card`/`pandad` stall. The tool [`tools/can_gaps/can_gap_scan.py`](../../../tools/can_gaps/README.md) reports gaps. A small extension would also report peak counts per window.
- HIL (D-04): flood each ID from the SoC side and measure the time to revocation.

## 10. Decisions and implementation

Decision (2026-10-12, project maintainer): **all recommendations of §8 accepted** (D-1 option C; D-2 budgets as proposed; D-3 threshold 3; D-4 health flag; D-5 reference build only; D-6 reaction time from the first rejected frame, TSR-518 amended). A maintainer decision, not an independent review (WP-M-06).

Implementation ([IA TX rate](../../07-supporting/impact/change-2026-10-12-tx-rate-supervision.md)):

| Part | Where | Deviation from the proposal |
|---|---|---|
| Rate check | opendbc `opendbc/safety/safety.h` `tx_rate_check`, compiled only with `LIONDRIVER_REFERENCE` | When a whole window has passed without frames, the previous half-window is cleared too, so host catch-up after a short stall is not counted against stale frames |
| Budgets | opendbc `modes/toyota.h`, non-SecOC configurations | `0x750` included (5 Hz, burst 2) |
| Reporting | panda health flag bit 11; LionDriver `pandaState.txRateExceeded`, `pandad` log | Flag latched until the next safety mode change |
| Tests | opendbc `test_toyota.py` `test_tx_rate_*`; panda `tests/hitl/test_14_tx_rate.py` | The §5 fallback was used: content tests clear the rate windows through a libsafety-only helper (`reset_tx_rate_state`), because the torque real-time tests set the timer themselves |
