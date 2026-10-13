# Back-to-back test: SM-TOY-AUTH model vs C safety code

| Field | Value |
|---|---|
| What | A Python reference model of the Toyota authority state machine, run against the C safety code (`libsafety`) on the same stimuli |
| Status | Draft, AI-assisted (Claude), not reviewed |
| Decisions | [Modelling plan](../README.md) MD-01 (Python), MD-03 (the model follows the record, not the code) |
| Record | [`sm-toy-auth.yaml`](../../05-software/state-machines/sm-toy-auth.yaml) |
| Code | opendbc at the pinned commit: `safety.h`, `modes/toyota.h`, through `opendbc/safety/tests/libsafety` |

## What it is, and what it is not

`run_b2b.py` drives every scenario through the C code and through the model, once in the upstream build and once in the reference build (`LIONDRIVER_REFERENCE=1`). After every event it compares `controls_allowed` with the model state, and for every TX frame it compares accept/reject.

It is **not verification evidence**. The model, the scenarios and the harness are unreviewed, and Python is not classified for this use (WP-P-07 OI-8). A run without divergences shows only that the record and the code agree for these stimuli. A divergence is a question for an engineer: either the record or the code is wrong, or the model has misread the record.

| File | Content |
|---|---|
| `toy_auth_model.py` | The model. Lists the transitions it executes, the ones it cannot execute at the libsafety boundary (with reasons), and the assumptions it makes where the record is silent (A-1…A-6) |
| `scenarios.py` | Scenarios BB-01…BB-11: the car's RX messages at nominal rates, the host's TX frames, the 100 Hz safety task, plus the change each scenario makes |
| `run_b2b.py` | Builds libsafety twice, runs both sides, classifies divergences, writes `b2b-report.md` and `b2b-report.json` |

Before each run the harness checks that every transition in the record is either executed by the model or listed as not executable. It also checks that the constants the model takes from the code (the RX check rates and the TX rate rows) still match `modes/toyota.h`.

## Run

```sh
cd opendbc_repo && source setup.sh && cd ..      # opendbc test dependencies, as for the safety tests
python assurance/models/b2b/run_b2b.py <output dir>
```

CI runs it in `.github/workflows/assurance.yaml` (job "Back-to-back SM-TOY-AUTH model vs libsafety") and uploads the report as an artifact. The run takes a few seconds.

Divergence classes:

| Class | Meaning | Fails the run |
|---|---|---|
| expected | The model fired a transition whose record entry says "not implemented"; the divergence confirms an open SWSR | No |
| known | Listed in `KNOWN` in `run_b2b.py` with a candidate-finding ID below | No |
| UNEXPECTED | Anything else | Yes |

Sensitivity check, done by hand on 2026-10-13: four deliberate model errors were each detected as UNEXPECTED, and the run failed. The errors were T5 at 8 periods, T10c at 300 ms, T11 after 5 rejections and T10b at 80 ms.

## Coverage

| Executed by the model (libsafety boundary) | Not executed (reason in `toy_auth_model.py`) |
|---|---|
| T1, T2, T3, T4, T5, T7, T8, T9, T10b (reference), T10c (reference), T11 (reference); non_revoking EPS fault and gas | T6, T10a, T10d, T13, T14, T15 (panda level); T10e, T12 (record leaves the override event or its thresholds undefined) |

T4 covers checksum and quality flag only. The Toyota RX checks ignore counters, so the counter part of T4 cannot be stimulated in this configuration.

## Results at the first run (2026-10-13, opendbc `273f44e`)

22 scenarios × 2 builds. No UNEXPECTED divergence.

| Divergence | Scenario | Build | Class |
|---|---|---|---|
| T9: torque step over the rate limit is refused, but authority is kept | BB-09 | both | expected (SWSR-108 open) |
| Authority granted again after a safety-mode set without a new driver engagement | BB-08b | both | known, BB-C-01 |
| Cruise going active while MAIN_ON is off: the C code refuses at once, the record allows 150 ms | BB-06b | reference | known, BB-C-02 |

## Candidate findings

These are proposals for the next software review record. None is a finding until a reviewer accepts it.

| ID | Observation | Analysis | Proposed disposition |
|---|---|---|---|
| BB-C-01 | After a safety-mode set (T7) while CRUISE_ACTIVE stays 1, the C code grants authority again on the next PCM_CRUISE frame, with no new driver engagement. This happens when every RX check has been received again before that frame (BB-08b). When one has not (BB-08a), authority stays off. | `set_safety_hooks` clears `cruise_engaged_prev` (safety.h), so a held CRUISE_ACTIVE looks like a rising edge to `pcm_cruise_check`. SWSR-311 requires this reset ("all … edge state reset on every safety-mode change"). SWSR-301 allows authority "only on a rising edge of CRUISE_ACTIVE". The two requirements conflict. Whether authority returns depends on the order in which the frames arrive after the mode set. | Requirement conflict for the safety engineer. One option: SWSR-311 sets the edge memory to "unknown", and authority then needs CRUISE_ACTIVE to be seen at 0 before a rising edge counts. A code change would go through CT-1 with an impact analysis. Relevant to T7 causes that happen during a drive (heartbeat loss and recovery). |
| BB-C-02 | Cruise going active while MAIN_ON is off: the record's T10c guard says "for > 150 ms", but the C code never grants authority in this case. `toyota_cruise_main_check(true)` clears it in the same RX call that granted it (BB-06b). | The code is stricter than the record. SWSR-405 (c) says only "flag an RX fault"; it gives no tolerance and no special case for the first frame. | Record update: add the case "mismatch first seen on PCM_CRUISE: cleared at once" to T10c in `sm-toy-auth.yaml`. Then remove BB-C-02 from `KNOWN`. No code change. |

## Limits

- **Coverage:** only the stimuli in `scenarios.py` are compared. There are no random or log-derived vectors yet. The next vector sources are the existing opendbc test sequences, then drive logs owned by the fork (WP-W-06 OI-9).
- **Timing:** time runs on a 1 ms grid with fixed message phases. Ordering effects inside one millisecond follow the order in `RX_SCHEDULE`.
- **Timing figures:** the model takes its figures from the record where the record has them (T5, T10b, T10c, T11). It takes the RX rates and TX rate rows from `toyota.h`, so it cannot find a wrong rate in that table.
- **Configuration:** only one configuration is covered, CFG-001 (safety param 73: LKA, openpilot longitudinal, non-SecOC). LTA, SecOC, alt-brake and stock longitudinal are not run.
