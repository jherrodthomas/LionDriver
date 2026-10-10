# FI-2026-001 — NHTSA PE26007: openpilot collisions with stopped / slow in-lane vehicles

## 1. Header

| Field | Value |
|---|---|
| FI ID | FI-2026-001 |
| Title | NHTSA Preliminary Evaluation PE26007: comma devices / openpilot strike stopped or slow vehicles in their own lane |
| Date received | 2026-10-10 |
| Reporter / source | Project maintainer, from public reporting |
| Source type | Regulator (NHTSA ODI), media |
| Source links | [Electrek, 2026-09-24](https://electrek.co/2026/09/24/comma-ai-openpilot-nhtsa-investigation-crashes/) · [Repairer Driven News, 2026-09-29](https://www.repairerdrivennews.com/2026/09/29/nhtsa-investigating-deaths-injuries-linked-to-comma-ai-driving-system/) · [Self Drive News](https://selfdrivenews.com/nhtsa-comma-ai-openpilot-investigation/) · [Roic.ai](https://www.roic.ai/news/us-opens-safety-probe-into-commaai-driver-assistance-after-five-crashes-three-deaths-09-23-2026) · [Yahoo News](https://www.yahoo.com/news/us/articles/federal-probe-opens-aftermarket-self-152942156.html) |
| Severity class | **A — Critical** (fatalities; regulatory defect investigation) |
| Provisional category | PERF, ML, MIS, CFG, PROC (see RCA) |
| Safety anomaly? | **Yes.** Collision with an in-lane obstacle while the system was engaged is a hazardous event for a longitudinal-control item. |
| Status | RCA — complete at the code level; awaiting field logs and reproduction |
| Safety manager | Project maintainer |
| RCA lead | Project maintainer |

> **Note on source quality:** the NHTSA resume (ODI document) has not been retrieved for this record. The facts below come from consistent press coverage. Replace them with the primary ODI source when available (action FA-01 in `CORRECTIVE-ACTIONS.md`).

## 2. Event description

| # | Fact | Source | Confidence |
|---|---|---|---|
| 1 | NHTSA ODI opened Preliminary Evaluation **PE26007** on 2026-09-21. | Electrek, Roic.ai | Reported |
| 2 | Scope is ~30,000 comma three, comma 3X and comma four devices **and** the openpilot open-source software. | Electrek, Yahoo | Reported |
| 3 | Five crashes in which comma-equipped vehicles struck **stopped or slow-moving vehicles in their own lane**: 3 fatalities, 11 injuries. | Electrek, RDN, Self Drive News | Reported |
| 4 | NHTSA's initial review suggests the system **may not have adequately detected or responded to** the in-lane vehicles. | Electrek, Self Drive News | Reported |
| 5 | One fatal crash (Feb 2026, Ascension Parish, Louisiana): a **2022 Toyota RAV4**, reportedly running **FrogPilot** (an openpilot fork), struck a **stopped emergency-response vehicle**. Two rear-seat passengers were killed. | Electrek, Yahoo | Reported |
| 6 | NHTSA will request crash logs, software version histories and driver-monitoring data, and will evaluate forks for components shared with openpilot. | Electrek | Reported |
| 7 | A Preliminary Evaluation is **not** a finding of defect or causation. | NHTSA via press | Reported |

**Known unknowns.** Any of these would change the analysis:

- Vehicle, software version and fork for four of the five crashes.
- For the RAV4 crash: was longitudinal control **openpilot** (alpha / experimental longitudinal) or **stock Toyota ACC**? Which FrogPilot toggles were set (following distance, braking profile, "conditional experimental mode", radar handling)?
- Speeds, closing speeds, detection range and the time of the first FCW or driver alert.
- Driver-monitoring state in the 15 s before impact.
- Whether stock Toyota PCS/AEB was active, and whether it fired.
- Lighting and weather; emergency lighting, flares or cones; whether the stopped vehicle was fully or partially in the lane; whether a lead vehicle cut out just before.

## 3. Operating context (RAV4 case, as far as is known)

| Item | Value |
|---|---|
| Vehicle | 2022 Toyota RAV4 (hybrid or ICE unknown) |
| ADAS platform | Toyota TSS2, **radar-based ACC** (`TOYOTA_RAV4_TSS2_2022`, `flags=ToyotaFlags.RADAR_ACC`, `opendbc_repo/opendbc/car/toyota/values.py:273-279 @ 229dc70`) |
| Software | FrogPilot (version unknown) |
| Function engaged | Unknown — lateral assumed; longitudinal owner unknown |
| Scenario | Stopped emergency vehicle in or partly in the ego lane |
| Driver state | Unknown |
| Outcome | 2 fatalities (rear-seat occupants) |

## 4. Applicability to LionDriver

| Question | Answer | Evidence |
|---|---|---|
| Is the suspected component in our baseline? | **Yes.** Driving model, `radard` lead selection, longitudinal MPC/planner, FCW logic, DM policy and Toyota car port are all inherited unchanged. | `openpilot/selfdrive/controls/radard.py`, `openpilot/selfdrive/controls/lib/longitudinal_planner.py`, `openpilot/selfdrive/monitoring/policy.py` @ `8b8c6ae`; `opendbc_repo/opendbc/car/toyota/` @ `229dc70` |
| Is our reference platform architecturally similar? | **Yes, partly.** The reference vehicle (2020 Corolla, `TOYOTA_COROLLA_TSS2`) is Toyota TSS2, the same family as the RAV4. Difference: the Corolla is **camera-ACC** with openpilot longitudinal **by default**. The 2022 RAV4 is **radar-ACC**: stock longitudinal by default, openpilot longitudinal only via the alpha toggle, which **disables the radar ECU**. | `opendbc_repo/opendbc/car/toyota/interface.py:93-106 @ 229dc70` |
| Can the triggering scenario occur in our operating domain? | **Yes.** Stopped vehicles in the lane (traffic queues, crashes, emergency scenes) are part of any public-road operating domain. | — |
| Same HMI / DM policy / driver population? | **Yes.** Same DM policy and alert timings, same HMI. | `openpilot/selfdrive/monitoring/policy.py:31-36 @ 8b8c6ae` |
| **Applicable?** | **Yes** | |

## 5. Containment

| Decision | Rationale | In force from | Lift criterion |
|---|---|---|---|
| **C-1.** No LionDriver public-road test with openpilot **longitudinal** control engaged above 40 km/h (25 mph) until CA-002 (stopped-vehicle scenario suite) shows the baseline meets its acceptance criteria, or a safety driver protocol per C-2 is in place. | Root cause is unconfirmed; the scenario is fatal at highway speed. Below ~40 km/h, the required stopping distance at -3.5 m/s² is short (≤ 24 m incl. latency) and radar low-speed override applies under 4 m/s. | 2026-10-10 | CA-002 passed **or** C-2 adopted |
| **C-2.** Any longitudinal test above 40 km/h uses a trained safety driver, a no-secondary-task rule, a hand-near-brake rule, and a closed or low-traffic route without emergency scenes. | Puts back the human barrier that failed in the field. | 2026-10-10 | CA-002 and CA-004 verified |
| **C-3.** The alpha-longitudinal toggle must not be enabled on any radar-ACC Toyota in LionDriver testing. | Enabling it silences the stock radar and sets PCS to off (RCA RC-01). | 2026-10-10 | CA-001 implemented (makes C-3 permanent in code) |

## 6. Links

- RCA: [`RCA.md`](RCA.md)
- Corrective actions: [`CORRECTIVE-ACTIONS.md`](CORRECTIVE-ACTIONS.md)
- Hazard log entries: HZ-001 … HZ-007 in [`../../HAZARD-LOG.md`](../../HAZARD-LOG.md)

## 7. Revision history

| Rev | Date | Author | Change |
|---|---|---|---|
| A | 2026-10-10 | LionDriver maintainers | Initial record from press coverage and code review |
