# WP-M-03 Project Plan

| Field | Value |
|---|---|
| Work product | WP-M-03 Project plan (scope, WBS, schedule, resources) |
| Standard reference | ASPICE 4.0 MAN.3 (project management); ISO 26262-2 §6 (planning of safety activities, by reference to WP-M-02) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All (project management) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer |
| Baseline | `8b8c6ae` |

## 1. Purpose

This plan defines the scope, work breakdown, effort, schedule logic, resources, interfaces and tracking for taking LionDriver through the assurance path in [WP-M-01](WP-M-01-assurance-strategy.md). Safety-specific responsibilities are in the [safety plan (WP-M-02)](WP-M-02-safety-plan.md). Risks to this plan are in [WP-M-07](WP-M-07-risk-management.md).

## 2. Scope

### 2.1 In scope

- The reference configuration of [WP-M-01 §3.1](WP-M-01-assurance-strategy.md#31-reference-configuration-the-only-scope-claims-apply-to): 2020 Toyota Corolla LE (US, ICE, TSS2), one comma device revision with panda safety MCU, one tagged LionDriver release.
- All work products in the [register (WP-M-00)](WP-M-00-work-product-register.md), gates G0…G6.
- Engineering changes needed to close gaps in the safety envelope, the onboard stack and the cybersecurity posture ([gap assessment](../00-assessment/gap-assessment.md) GAP-01…GAP-37).
- Infrastructure LionDriver needs and does not have: forks of opendbc and panda, fork CI, HIL bench, process-replay reference set, a test vehicle.

### 2.2 Out of scope

- Any vehicle, device revision or ODD outside the reference configuration (needs [WP-M-12](WP-M-12-impact-analysis.md) impact analysis first).
- Driverless, Level 3 or higher operation (WP-M-01 §3.2).
- Retraining of the driving models (LionDriver has no training data; models are pinned, D-05).
- comma.ai back-end services (T-11).
- Hardware redesign of the comma device. If the analyses show the hardware is insufficient, an external monitor is a possible scope change, decided through change management.

## 3. Work breakdown structure

WBS elements follow the phases and gates in [WP-M-01 §7](WP-M-01-assurance-strategy.md#7-phases-gates-and-sequence). Work product IDs refer to WP-M-00.

| WBS | Element | Content | Exit |
|---|---|---|---|
| 0 | Project management (continuous) | Planning, tracking, risk management, gate reviews, assessor coordination | — |
| 1 | P0 Governance | | G0 |
| 1.1 | Plans | WP-M-00…M-13 | |
| 1.2 | Supporting procedures | WP-P-01…P-06 | |
| 1.3 | Configuration control | Fork `opendbc` and `panda` into LionDriver; absolute submodule URLs; pin tinygrad; freeze sync (D-01, D-02; GAP-29, GAP-37) | |
| 1.4 | Fork CI and review controls | Disable comma-only workflows and stale auto-close; CODEOWNERS; PR template with safety-impact checklist; branch protection; run opendbc safety tests, MISRA and mutation in LionDriver-controlled CI (D-03; GAP-31, GAP-32) | |
| 1.5 | Impact analysis of baseline | WP-M-12 | |
| 1.6 | External assessor engagement | Select, contract, schedule (D-06) | |
| 2 | P1 Concept | | G1 |
| 2.1 | Item and ODD | WP-C-01, WP-C-02; vehicle data capture (VIN, ECU firmware) | |
| 2.2 | HARA and misuse | WP-C-03, WP-C-08 | |
| 2.3 | FSC | WP-C-04 | |
| 2.4 | SOTIF concept | WP-C-05, C-06, C-07 (incl. Experimental Mode default, GAP-18 / D-08) | |
| 2.5 | Cybersecurity concept | WP-C-09, C-10 | |
| 2.6 | AI system definition | WP-C-11 | |
| 2.7 | Vehicle test operations | WP-V-07 | |
| 2.8 | Safety case v1 | WP-K-01 initial argument | |
| 3 | P2 System design | | G2 |
| 3.1 | Requirements back-fill | WP-S-01, S-02 from envelope code | |
| 3.2 | Architecture, timing, HSI | WP-S-03, S-04, S-05 | |
| 3.3 | Production/operation and CS requirements | WP-S-06, S-07 | |
| 3.4 | System safety analyses | WP-A-01…A-04 | |
| 3.5 | SOTIF V&V strategy | WP-V-02 | |
| 4 | P3 HW/SW development | | G3 |
| 4.1 | Hardware safety | WP-H-01…H-05, H-07 | |
| 4.2 | Software safety requirements, architecture, analysis | WP-W-01…W-04 | |
| 4.3 | Envelope hardening (code changes) | IWDG, fault → safe state, mode lock, gate `0xc5`, driver-torque and EPS-status monitoring, RX E2E strategy (gap §9 action 5) | |
| 4.4 | Firmware security | LionDriver signing key, modern algorithm, RDP/WRP, release build without debug key (gap §9 action 6) | |
| 4.5 | Onboard stack fixes | Soft disable and Chestnut masking (gap §9 action 8) | |
| 4.6 | Unit design and verification | WP-W-05, W-06 (structural coverage beyond line, MISRA deviation records) | |
| 4.7 | Configuration data, ML, CS implementation | WP-W-09, W-10, W-11 | |
| 4.8 | Qualification | WP-P-07, P-08, P-09 | |
| 5 | P4 Integration and verification | | G4 |
| 5.1 | HIL bench | Build, characterize, document (D-04) | |
| 5.2 | Process-replay references | Fork-owned reference logs and test routes | |
| 5.3 | Integration and qualification tests | WP-W-07, W-08, WP-H-06, WP-S-08, S-09 | |
| 5.4 | Fault injection | WP-V-05 | |
| 5.5 | Known scenarios | WP-V-03 | |
| 6 | P5 Validation and release | | G5 |
| 6.1 | Safety validation | WP-V-01 (vehicle, under WP-V-07) | |
| 6.2 | SOTIF unknown scenarios, release argument | WP-V-04, WP-K-02 | |
| 6.3 | CS validation and pen test | WP-V-06 (external tester) | |
| 6.4 | Production/operation | WP-O-01…O-03 | |
| 6.5 | Cases and assessments | WP-K-01, K-03, K-04, K-05, K-06; WP-P-10 | |
| 7 | P6 Operation (continuous) | WP-O-04, O-05, WP-P-03 | G6 |

## 4. Effort and feasibility estimate

### 4.1 Assumptions

- Estimates are rough-order magnitude, in person-weeks (pw) of competent effort (one pw ≈ 40 h). They are not based on historical data from this project, because none exists.
- The person doing the work already has the competence in [WP-M-04](WP-M-04-organization-competence-safety-culture.md). Learning time is not included.
- The HARA results in ASIL C or D for at least one safety goal on the envelope ([WP-C-03](../02-concept/WP-C-03-hara.md) 0.2: SG-01 ASIL D, SG-03…SG-05 ASIL C, decision D-09). A lower ASIL would reduce P3–P4 effort.
- The comma device hardware is analysable from public information; no supplier evidence arrives (WP-M-01 §9).
- External assessor and pen-test effort is listed separately and is not done by project staff.
- Envelope hardening is a modest change set (hundreds, not thousands, of lines of C).

### 4.2 Estimate

| Phase | Low (pw) | High (pw) | Main drivers |
|---|---|---|---|
| P0 Governance | 6 | 10 | 19 plans/procedures; fork and CI setup |
| P1 Concept | 14 | 24 | HARA and FSC from scratch; SOTIF analysis of an end-to-end ML function; TARA |
| P2 System design | 14 | 22 | Requirements back-fill from code; FFI and DFA on a shared-board design |
| P3 HW/SW development | 30 | 55 | FMEDA without supplier data; envelope hardening; structural coverage; tool qualification (arm-none-eabi-gcc, cppcheck) |
| P4 Integration and verification | 20 | 35 | HIL bench build (4–8 pw of this); fault injection; replay references |
| P5 Validation and release | 20 | 40 | Validation driving and data analysis; safety case; assessment support and finding closure |
| **Total P0–P5** | **≈ 105** | **≈ 185** | |
| P6 Operation | 0.1–0.2 FTE ongoing | | Field monitoring, incident response, controlled updates |

| External effort | Rough order |
|---|---|
| FuSa assessor: confirmation reviews G0–G4 | 10–20 assessor-days |
| FuSa assessor: interim assessments G1, G2; audits | 10–15 assessor-days |
| FuSa assessor: final assessment G5 | 15–30 assessor-days |
| Cybersecurity assessor | 10–20 assessor-days |
| Penetration test (device, firmware, OTA, remote access) | 10–20 tester-days |

### 4.3 Feasibility

- **Total effort is about 2–4 person-years.** At one full-time person this is 2.5–4.5 calendar years; at half-time it doubles. Gate-to-gate durations in §5 assume 1.0 FTE plus external support.
- **Single-maintainer bottleneck.** Every role in WP-M-02 §3.1 currently resolves to one person. That person is the critical path for every phase and cannot provide independent review of their own work. This is the dominant schedule and compliance risk (WP-M-07 R-01). Realistic delivery needs at least: one additional envelope engineer or reviewer (from P0), a SOTIF/ML person (from P1), a hardware safety engineer (P3, can be external), and a test driver (P1).
- The work is technically feasible because the ASIL scope is small (WP-M-01 §4.2.1). Hardware evidence (WP-H-04/05) and OEM ECU assumptions are the items most likely to limit the strength of the claim rather than the schedule.

## 5. Schedule

No calendar dates are set until staffing is known (OI-1). The schedule is a phase sequence with relative durations at 1.0 FTE plus the minimum added staff listed in §4.3.

| Phase | Relative duration | Depends on | Can overlap with |
|---|---|---|---|
| P0 | 2–3 months | — | Start of P1 item definition |
| P1 | 4–6 months | G0; assessor engaged (for HARA CR); test driver trained (for WP-V-07) | P2 requirements back-fill (start only after HARA draft is stable) |
| P2 | 4–6 months | G1 (HARA confirmation review passed) | Start of HIL bench build (5.1) |
| P3 | 8–12 months | G2 (FFI/DFA decide hardware route) | P4 HIL bench, replay references |
| P4 | 5–8 months | G3; HIL bench ready | Start of validation planning |
| P5 | 5–9 months | G4; vehicle; assessor availability | — |
| P6 | Continuous | G5 | — |

Critical path: P0 → HARA → HARA confirmation review → FFI/DFA → envelope hardening → HIL verification → validation → FSA.

Long-lead items to start early: assessor engagement (P0), HIL bench parts (P2), test vehicle access and safety driver training (P1), pen-test procurement (P4).

## 6. Resources

| Resource | Need | Status |
|---|---|---|
| Project maintainer / acting safety manager | Throughout | Jherrod Thomas; availability (FTE) not recorded (OI-1) |
| Additional engineers and reviewers | See §4.3 | TBD |
| External FuSa assessor | From P0 (engagement), G1 onward | TBD (D-06) |
| External CS assessor, pen tester | P4–P5 | TBD |
| Test vehicle | 2020 Toyota Corolla LE, US, ICE, TSS2; insurance and registration that cover test use | TBD; ownership and insurance status not recorded |
| comma device(s) | At least two of the identified revision (one in vehicle, one on HIL), plus Toyota harness | TBD |
| HIL bench | Bare panda or comma device, CAN interfaces (≥ 3 buses), host PC running Corolla DBC log replay and plant model, power supply with fault injection, relay/harness break-out, debug probe for STM32H7 | Not built (D-04, GAP-30) |
| Drive logs | Fork-owned Corolla logs for process replay and scenario evaluation | None yet |
| CI compute | GitHub Actions (hosted runners); optionally a self-hosted runner attached to the HIL bench | Hosted runners available; self-hosted TBD |
| Tools | Toolchain as pinned in `uv.lock` and submodules; cppcheck; coverage tools; requirements data in `trace/` | Available; qualification pending (WP-P-07) |
| Licensed standards | ISO 26262:2018, ISO 21448:2022, ISO/SAE 21434:2021, ISO/PAS 8800:2024, ASPICE PAM 4.0 | Availability not recorded (OI-3) |

## 7. Interfaces

| Interface | Party | Managed in |
|---|---|---|
| Upstream software | comma.ai (openpilot, opendbc, panda, models) — no contract | [WP-M-11](WP-M-11-upstream-and-supplier-management.md) |
| Hardware supplier | comma.ai (device, harness) — commercial purchase only | WP-M-11 |
| External assessors | FuSa and CS assessors | [WP-M-06](WP-M-06-confirmation-measures-plan.md) |
| Vehicle OEM | Toyota — no relationship; AoUs only | [WP-C-01](../02-concept/WP-C-01-item-definition.md) |
| Users and contributors | GitHub issues and PRs | [WP-M-04 §6](WP-M-04-organization-competence-safety-culture.md) |
| Regulators | NHTSA (SGO model for field monitoring, T-13) | [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md) |
| Discipline plans | SOTIF, CS, AI | WP-M-08, WP-M-09, WP-M-10 |

## 8. Monitoring and tracking

| Mechanism | Rule |
|---|---|
| Milestones | One GitHub milestone per gate: `G0 Governance` … `G6 Operation` |
| Issues | One issue per work product (title starts with the WP ID) and one per gap action or engineering change. Labels: `wp:<ID>`, `gap:GAP-nn`, `safety-relevant`, `safety-anomaly`, `risk:R-nn`, `decision:D-nn`, `qa-finding` |
| Status | WP-M-00 status column is updated in the PR that changes a work product's status |
| Reviews | Monthly progress review by the project maintainer: milestone burn-down, blocked items, risk register update (WP-M-07). Recorded as a comment on the milestone tracking issue |
| Gate reviews | Per [WP-M-02 §10](WP-M-02-safety-plan.md) |
| Re-planning | If a phase exceeds its high estimate by more than 25 %, or a key resource is lost, the project maintainer re-plans and updates this document |

None of these milestones, labels or issues exist yet; creating them is backlog item B-01.

## 9. Next 30 days backlog

Derived from [gap assessment §9](../00-assessment/gap-assessment.md#9-priority-actions-feed-into-the-g0g1-plan) and the P0 scope. Items are ordered by priority.

| # | Item | Gap / decision | Output | Owner |
|---|---|---|---|---|
| B-01 | Create milestones G0–G6, labels, and issues for every WP-M/WP-P work product and gap §9 action | — | GitHub tracking set up | PM |
| B-02 | Fork `commaai/opendbc` and `commaai/panda` into the LionDriver account; switch `.gitmodules` to absolute URLs; pin tinygrad by commit; adjust or replace `check-submodules.sh` | GAP-29, D-01 | Submodules under LionDriver control | PM |
| B-03 | Record the upstream freeze and the sync procedure | GAP-37, D-02 | WP-P-01, WP-P-02 drafts | PM |
| B-04 | Disable `jenkins-pr-trigger`, `ui_preview`, `stale`; review `release` and `repo-maintenance`; add a workflow that runs opendbc safety tests, MISRA and mutation in the LionDriver repo | GAP-31, D-03 | Fork CI that produces safety-test evidence | PM |
| B-05 | Add CODEOWNERS, PR template with safety-impact checklist, branch protection on `liondriver-dev` (and the release branch once defined) | GAP-32 | Review controls active | PM |
| B-06 | Turn the Experimental Mode default off for the reference configuration pending SOTIF assessment (change request with impact analysis) | GAP-18, D-08 | CR merged or decision recorded | PM / SL |
| B-07 | Add a LionDriver `SECURITY.md` and vulnerability intake; reroute issue templates away from comma.ai | GAP-28 | Intake channel | CSM |
| B-08 | Record the "no LionDriver public-road operation until G1 and WP-V-07" rule in README and WP-V-07 | Gap §9 action 10 | Rule published | SM |
| B-09 | Contact candidate external FuSa assessors; agree scope of G0/G1 confirmation reviews | D-06 | Shortlist and quote | PM |
| B-10 | Complete drafts of WP-M-08…M-13 and WP-P-01…P-06 | GAP-33 | G0 work products in Draft | SM |
| B-11 | Recruit at least one verification reviewer and one QA person independent of the author | R-01 | Names in WP-M-02 §3.1 | PM |
| B-12 | Record the reference vehicle's VIN, ECU firmware versions and device revision | — | Input to WP-C-01 | PM |

## 10. Open items

| ID | Open item | Owner | Due |
|---|---|---|---|
| OI-1 | Record the maintainer's available FTE and convert relative durations into a dated schedule | PM | G0 |
| OI-2 | Decide the funding source for external assessor, pen test and HIL hardware | PM | G0 |
| OI-3 | Confirm access to licensed copies of the standards | PM | G0 |
| OI-4 | Confirm test vehicle availability, ownership and insurance cover for test use | PM | G1 |
| OI-5 | Re-estimate P2–P5 after the HARA gives the actual ASILs | PM / SM | G1 |
