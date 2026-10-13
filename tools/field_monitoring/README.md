# Field-monitoring event extraction

`extract_events.py` is step 2 of the field-monitoring pipeline in [WP-O-04](../../assurance/09-production-operation/WP-O-04-field-monitoring.md) §4.1 (open item OI-4). It scans openpilot logs for the monitored events MON-01…MON-17 of WP-O-04 §2.1. It also scores the SOTIF anomaly signatures AS-01…AS-11 of [WP-V-04](../../assurance/06-validation/WP-V-04-sotif-unknown-scenarios.md) §2.1. Development drives and field logs go through the same script and the same signature-set version, as WP-V-04 §2.1.1 requires.

## Use

```bash
# rlogs give every event; qlogs lack modelV2, so AS-05, AS-08, AS-09 and MON-13 are not scored
PYTHONPATH=. tools/field_monitoring/extract_events.py route/*/rlog.zst --json events.json --csv events.csv

# with a release record (MON-16) and evaluation-set uncertainty limits (AS-09)
tools/field_monitoring/extract_events.py rlog.zst --release release.json --uncertainty-limits limits.json
```

`release.json` maps fields to the released values, for example `{"initData.gitCommit": "…", "carParams.carFingerprint": "TOYOTA_COROLLA_TSS2"}`. `limits.json` holds the 99.9th percentiles of the evaluation set, for example `{"lead_x_std": 2.5}`.

The output has four parts:

- **Event table.** Each row has the route, the time from route start, the MON ID, the AS IDs, the triage class of WP-O-04 §4.2, whether the system was engaged, and the signals that triggered the event.
- **Exposure** (WP-O-04 §2.2). Total and engaged time and distance, and engaged distance per speed band. These are the denominators of the KPIs.
- **Counts.** Counts per MON and AS, and rates per engaged hour.
- **Not scored.** A list of the signatures the run could not score, with the reason.

Exit status 1 means at least one T1 event was found, or a KPI is a FINDING or BREACH. A T1 event needs review the same day.

## KPIs

The report also judges the KPIs of WP-O-04 §5 that the logs alone can show: K-01…K-04, K-06…K-08, K-10, K-13 and K-14. Their thresholds are proposals derived from the validation targets of WP-V-02 §4, for example K-13 ≤ 1 phantom deceleration per 1,000 engaged km from VT-04. They wait for assessor review (WP-O-04 OI-5).

| Status | Meaning |
|---|---|
| FINDING | A zero-tolerance KPI (K-01, K-02, K-03, K-07) has an occurrence |
| BREACH | The exact one-sided 95 % Poisson lower bound of the rate is above the threshold |
| WATCH | The observed rate is above the threshold, but the lower bound is not |
| MET | The 95 % upper bound is at or below the threshold |
| OPEN | Not enough exposure to decide. `exposure_to_demonstrate` says how much would show MET at the current count |
| BASELINE | No target yet (K-04, K-08); the rate is reported for the development baseline |

K-06 is evaluated for the whole fleet here; the per-driver check needs the driver identity from the retrieval log.

## How events are found

| MON | Source | Rule |
|---|---|---|
| MON-01 | `selfdriveState`, `carState` | Disengagement with no fault event active; pedal and steering flags recorded. AS-01: steering override while engaged, with no blinker on (blinker stands in for lane change). AS-02: hard deceleration below −4 m/s² within 2 s after a brake disengagement |
| MON-02 | `onroadEvents`, `pandaStates.epsFault` | Disengagement while a soft- or immediate-disable event is active; EPS fault reported by the envelope |
| MON-03, -04, -05, -07…-12, -15 | `onroadEvents` | Rising edge of the named events (WP-O-04 §2.1). `relayMalfunction` also from `pandaStates.faults` |
| MON-06 | `pandaStates` | Increase of `safetyTxBlocked` (AS-04) or `safetyRxInvalid`; `heartbeatLost`; `txRateExceeded` |
| MON-11 | `liveCalibration.calStatus` | Change to `invalid` or `recalibrating` |
| MON-13 | `modelV2` | Non-finite plan output; lead flicker above one toggle per second (AS-08); lead uncertainty above the evaluation limit (AS-09) |
| MON-14 | `userBookmark`, `carState.aEgo` | Every bookmark; deceleration below a placeholder of −6 m/s² as a candidate (WP-O-04 OI-8) |
| MON-15 | `carState.vEgo` | Engaged above 120 km/h, the ODD-H bound |
| MON-16 | `initData`, `carParams` | Any field that differs from the release record |
| MON-17 | `carState`, `longitudinalPlan`, `modelV2`, `radarState` | AS-03: gas while the planner target is below −1.5 m/s². AS-05: vehicle side within 0.3 m of a seen ego-lane line. AS-06: deceleration below −2 m/s² with no radar lead within a time to collision of 4 s |

Each event counts once, on its rising edge, because openpilot republishes an active event in every message.

## Interpretations

The AS-01, AS-05, AS-06 and AS-10 readings below were confirmed by the project maintainer on 2026-10-13 and are now part of the WP-V-04 §2.1 definitions (signature-set version `WP-V-04-2.1/2026-10-13`). The MON-14 placeholder of −6 m/s² is accepted as interim in WP-O-04 OI-8. Each one is a constant at the top of the script.

- **AS-01.** "Not during a lane change" is taken as no blinker on.
- **AS-05.** "Lane-line offset" is taken as the gap between the vehicle's side and the line, using the reference Corolla's width of 1.781 m. Only lines seen with probability ≥ 0.5 count.
- **AS-06.** "No lead within TTC 4 s" uses the radar lead (`radarState.leadOne`) and counts a lead only while it closes.
- **AS-10.** Only DM alert levels 2–3 and lockouts are scored. Periods of DM uncertainty fallback are not.
- **Exposure** (not a signature definition). Each interval between two `carState` messages counts in the state at its end.

## Limits

- **Tested on synthetic message streams only.** The tests check every rule. Before the counts are used as evidence, the script must run on recorded drives, and its events must be checked against a manual review of the same drives (OI-4).
- **Not scored:**
  - the at-limit part of AS-04, which needs the safety replay;
  - the curvature divergence of AS-08, which has no threshold in WP-V-04;
  - AS-09 without evaluation-set limits;
  - MON-16 without a release record.
- **Placeholder thresholds.** The MON-14 deceleration threshold and every KPI threshold are placeholders (WP-O-04 OI-5, OI-8). A change to any AS threshold changes `SIGNATURE_SET_VERSION`. Reports from different versions are not comparable.
- **Reading real logs.** This needs openpilot's `LogReader` (pycapnp, zstandard). The tests do not.
