# WP-P-09 Proven-in-Use Argument Evaluation

| Field | Value |
|---|---|
| Work product | WP-P-09 Proven-in-use argument evaluation |
| Standard reference | ISO 26262-8:2018 §14; ISO 26262-2:2018 §6 (tailoring) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | Envelope (opendbc safety + panda firmware) and QM stack |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1). Confirmation review CR-11 not planned while no claim is made ([WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md)) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` |

## 1. Purpose

Evaluates whether a proven-in-use (PIU) argument under ISO 26262-8 §14 could be made for any openpilot or panda element, and records the conclusion that supports tailoring T-06 in [WP-M-01](../01-management/WP-M-01-assurance-strategy.md#5-tailoring): **no PIU claim is made**. The openpilot field history is used only as supporting, non-credited evidence.

## 2. Candidate scope

| Candidate | Why considered | Relevant configuration |
|---|---|---|
| PIU-C1 opendbc Toyota safety mode | Small, stable C code; long upstream history | `opendbc_repo/opendbc/safety/modes/toyota.h` with `safety.h`, `lateral.h`, `longitudinal.h` at `229dc70` |
| PIU-C2 panda firmware safety paths | Same firmware family runs on all comma devices | `panda/board/**` at `92eb565`, STM32H7 build |
| PIU-C3 Toyota car port (host) | Toyota is a widely used openpilot brand upstream | `opendbc_repo/opendbc/car/toyota/**` |
| PIU-C4 openpilot driving stack and models | Large fleet use claimed upstream | `openpilot/selfdrive/**`, model files |

## 3. Criteria and assessment

The criteria below paraphrase what 8 §14 requires a PIU argument to establish. Each is assessed against what is actually available to LionDriver.

| # | Criterion | What is needed | What is available | Met? |
|---|---|---|---|---|
| P1 | Candidate is clearly identified and its configuration is stable | Exact version identity; the same version (or controlled, analysed changes) used across the service period | Upstream changes daily (GAP-37). Toyota safety code, panda firmware and models change between releases; `RELEASES.md` lists frequent model changes (e.g. 0.11.0, 0.11.1, 0.11.2 each with new driving or DM models). No configuration history ties field operation to specific versions in a form LionDriver can access | No |
| P2 | Intended use in the new item matches the use during the service period | Same vehicle, same function, same operating conditions | Upstream fleet spans many brands, models and hardware revisions (comma 3/3X/four). The share running `TOYOTA_COROLLA_TSS2` with the pinned versions is unknown | No |
| P3 | Service period sufficient for the target ASIL | Accumulated operating hours for the specific configuration, against the limit for the target ASIL | Only public claims of fleet distance by comma.ai (blog posts, talks). These are aggregates over all versions and vehicles. **Public claims, not verifiable by LionDriver.** No per-configuration hours | No |
| P4 | Field problem data collected and analysed | Systematic recording of field incidents and their root causes, with defined counting rules | comma collects logs and has internal tooling; incident data, counting rules and analyses are not published. Upstream issue templates route reports to comma and exclude forks (`.github/ISSUE_TEMPLATE/bug_report.yml`) | No |
| P5 | Changes during the service period are analysed for impact | Change records with impact analysis for each change to the candidate | Git history is available (and shallow, 50 commits, in this checkout). No safety impact analyses exist upstream | No |
| P6 | No observed safety-relevant failures in the evaluated period, or all analysed and resolved | Incident list with dispositions | Not available | No |
| P7 | Candidate is used in the new item without modification, or modifications are analysed | Diff to the evaluated version | LionDriver plans envelope hardening (IWDG, fault reaction, mode lock, per gap assessment action 5), so the deployed version will differ from any upstream service history | No |

## 4. Conclusion

A proven-in-use argument is **not claimable** for any candidate (PIU-C1 to PIU-C4). Every criterion fails on lack of controlled configuration data, per-configuration service hours and field incident data, all of which belong to comma.ai and are not available to LionDriver (no development interface agreement, T-08 and [WP-M-11](../01-management/WP-M-11-upstream-and-supplier-management.md)). This supports T-06.

Consequences:

- The envelope is re-verified under T-03 ([WP-W-06](../05-software/WP-W-06-software-unit-verification.md) to [WP-W-08](../05-software/WP-W-08-embedded-software-testing.md)).
- QM components are qualified per [WP-P-08](WP-P-08-software-component-qualification.md) at QM.
- No ASIL credit is taken from upstream fleet usage.

## 5. Permitted use as supporting evidence

Upstream history may be cited in the safety case ([WP-K-01](../10-safety-case/WP-K-01-safety-case.md)) only as context, never as a claim:

| Use | Condition |
|---|---|
| "The envelope pattern has been in public use upstream" | Cited as background with the source, marked "public claim, not verified by LionDriver" |
| Upstream bug fixes and issues as input to hazard and FMEA brainstorming | Listed as sources in [WP-C-03](../02-concept/WP-C-03-hara.md) / [WP-W-04](../05-software/WP-W-04-software-safety-analysis.md) |
| Upstream test suites (e.g. `test_toyota.py`, `common.py`) | Used as verification assets after review under [WP-P-05](WP-P-05-verification-review-procedure.md), not as service history |
| LionDriver's own field data after release | Collected under [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md); could support a future argument for a frozen LionDriver configuration |

No fleet distance, hours or incident numbers are stated in this document because none could be verified.

## 6. Conditions for revisiting

A PIU argument would only be re-evaluated if one of these becomes true:

1. comma.ai (or another party) provides per-version, per-vehicle service data and incident records under an agreement that allows assessment.
2. LionDriver accumulates its own controlled field history for a frozen configuration through WP-O-04, with counting rules defined in advance.

Either case requires a new revision of this document and confirmation review CR-11 at I3.

## 7. Open items

| ID | Item |
|---|---|
| OI-1 | Ask comma.ai (via [WP-M-11](../01-management/WP-M-11-upstream-and-supplier-management.md)) whether any per-configuration service or incident data could be shared; record the answer |
| OI-2 | Define field-data counting rules in WP-O-04 so that LionDriver's own history could be used later |
| OI-3 | Confirm the criteria wording in §3 against the licensed copy of 26262-8 §14 |
