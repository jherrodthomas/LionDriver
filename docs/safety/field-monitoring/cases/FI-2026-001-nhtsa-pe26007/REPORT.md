# FI-2026-001 — NHTSA PE26007: openpilot collisions with stopped / slow in-lane vehicles

> **ID note (added 2026-10-19).** HZ-nnn in this dated file is field hazard **FHZ-nnn** of [HAZARD-LOG.md](../../HAZARD-LOG.md) revision C. It is not the FMEA hazard of the same number (`assurance/08-analyses/fmea/analyses/hara.yaml`). The text is otherwise unchanged.

## 1. Header

| Field | Value |
|---|---|
| FI ID | FI-2026-001 |
| Title | NHTSA Preliminary Evaluation PE26007: comma devices / openpilot strike stopped or slow vehicles in their own lane |
| Date received | 2026-10-10 |
| Reporter / source | Project maintainer, from public reporting |
| Source type | Regulator (NHTSA ODI), media |
| Source links | **Primary:** [NHTSA ODI resume, PE26007, opened 2026-09-21](evidence/INOA-PE26007-17274.pdf) (2 pages; SHA-256 `e8eac1901d9bf5a13be62ed290898f11cc09c490e270514b005ca0e2af62da6c`) · Press: [Electrek, 2026-09-24](https://electrek.co/2026/09/24/comma-ai-openpilot-nhtsa-investigation-crashes/) · [Repairer Driven News, 2026-09-29](https://www.repairerdrivennews.com/2026/09/29/nhtsa-investigating-deaths-injuries-linked-to-comma-ai-driving-system/) · [Self Drive News](https://selfdrivenews.com/nhtsa-comma-ai-openpilot-investigation/) · [Roic.ai](https://www.roic.ai/news/us-opens-safety-probe-into-commaai-driver-assistance-after-five-crashes-three-deaths-09-23-2026) · [Yahoo News](https://www.yahoo.com/news/us/articles/federal-probe-opens-aftermarket-self-152942156.html) |
| Severity class | **A — Critical** (fatalities; regulatory defect investigation) |
| Provisional category | PERF, ML, MISUSE, CFG, PROC (see RCA) |
| Safety anomaly? | **Yes.** Collision with an in-lane obstacle while the system was engaged is a hazardous event for a longitudinal-control item. |
| Status | RCA — complete at the code level; awaiting field logs and reproduction. Problem statement: [`PROBLEM-STATEMENT.md`](PROBLEM-STATEMENT.md) |
| Safety manager | Project maintainer |
| RCA lead | Project maintainer |

> **Source quality (revised 2026-11-18, rev B).** The NHTSA ODI resume for PE26007 is now held as
> [`evidence/INOA-PE26007-17274.pdf`](evidence/INOA-PE26007-17274.pdf) (action FA-01). Facts it states are marked
> **Verified** below and quote it. Facts it does not state (the RAV4 crash, FrogPilot, the data NHTSA will request) stay
> **Reported**, from the press. Three press figures differed from the resume and are corrected: the date opened is
> 2026-09-21, the prompt was SGO crash reports, an owner complaint (VOQ) and police outreach, and the five crashes are
> five SGO reports whose IDs the resume lists.

## 2. Event description

| # | Fact | Source | Confidence |
|---|---|---|---|
| 1 | NHTSA ODI opened Preliminary Evaluation **PE26007** on **2026-09-21**, "prompted by: SGO 2021-01 reports, VOQ, Police outreach". Subject: "Crashes involving comma.ai driving automation products". | ODI resume p. 1 | **Verified** |
| 2 | Products: "comma three, comma 3X, comma four, openpilot". Population: "30,000 (Estimated)". | ODI resume p. 1 | **Verified** |
| 3 | Problem description: "Crashes involving stopped or slow moving in-lane vehicles". ODI "received notice of five (5) crashes in which vehicles with comma devices installed reportedly struck stopped or slowly moving vehicles within the same travel lane". | ODI resume p. 1 | **Verified** |
| 4 | "Two crashes resulted in a total of three (3) fatalities. Four of the five crashes contributed to various non-fatal injuries, including serious injuries, to eleven (11) other individuals." The failure report summary counts 5 crashes, 4 injury incidents, 14 people injured or killed, 2 fatal incidents and 3 fatalities, with duplicates removed. | ODI resume pp. 1–2 | **Verified** |
| 5 | "ODI has confirmed that the systems were powered on or engaged in multiple crashes. Preliminary data reviewed by ODI suggests that the comma system may not have adequately detected or responded to the in-lane vehicles." | ODI resume pp. 1–2 | **Verified** |
| 6 | Scope: "particularly crashes involving slower or stopped vehicles or hazards in lane". ODI will "verify system status for each incident and evaluate system performance and safeguards", and where a fork is involved will "consider the shared components between openpilot and the fork". **LionDriver is a fork in that sense.** | ODI resume p. 2 | **Verified** |
| 7 | The five crashes are SGO reports 30351-15888, 30351-14668, 30351-11961, 30351-1807 and 62-14853, downloadable from NHTSA's Standing General Order crash-reporting page. | ODI resume p. 2 | **Verified** (IDs); report contents not yet retrieved (FA-02) |
| 8 | One fatal crash (Feb 2026, Ascension Parish, Louisiana): a **2022 Toyota RAV4**, reportedly running **FrogPilot** (an openpilot fork), struck a **stopped emergency-response vehicle**. Two rear-seat passengers were killed. | Electrek, Yahoo | Reported (not in the resume) |
| 9 | NHTSA will request crash logs, software version histories and driver-monitoring data. | Electrek | Reported (the resume says only that ODI "will obtain data to verify system status") |
| 10 | A Preliminary Evaluation is **not** a finding of defect or causation. The resume's action is "Open this Preliminary Evaluation (PE)". | ODI resume p. 1; NHTSA via press | **Verified** (action); Reported (characterisation) |

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
| **C-3.** The alpha-longitudinal toggle must not be enabled on any radar-ACC Toyota in LionDriver testing. | Enabling it silences the stock radar and sets PCS to off (RCA RC-01). | 2026-10-10 | CA-001 implemented (makes C-3 permanent in code). **Now enforced in software by CA-001**; lifting fully waits on CA-001 AC-2/AC-3 |

## 6. Links

- RCA: [`RCA.md`](RCA.md)
- Corrective actions: [`CORRECTIVE-ACTIONS.md`](CORRECTIVE-ACTIONS.md)
- Hazard log entries: HZ-001 … HZ-007 in [`../../HAZARD-LOG.md`](../../HAZARD-LOG.md)

## 7. Revision history

| Rev | Date | Author | Change |
|---|---|---|---|
| A | 2026-10-10 | LionDriver maintainers | Initial record from press coverage and code review |
| B | 2026-11-18 | LionDriver maintainers | NHTSA ODI resume filed as evidence (FA-01). §2 facts 1–7 and 10 verified against it; opening date 2026-09-21, prompt and SGO report IDs added; RAV4 and data-request facts stay Reported. Link to the problem statement added. |
