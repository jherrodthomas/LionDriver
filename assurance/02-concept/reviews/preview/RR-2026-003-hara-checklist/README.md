# RR-2026-003 HARA review checklist

> Generated from [`RR-2026-003-hara-checklist.xlsx`](../../RR-2026-003-hara-checklist.xlsx) by `tools/xlsx_review.py`, so it can be read and reviewed on GitHub without downloading the workbook. Regenerate, never edit this page. The review record is [RR-2026-003](../../RR-2026-003.md).

**Sheets.** [Title](#title) · [General Info](#general-info) · [Guide](#guide) · [Summary](#summary) · [Confirmation Review](#confirmation-review) · [Functional Safety Assessment](#functional-safety-assessment) · [Verification Assessment](#verification-assessment)

## Title

*HARA Confirmation Measures Checklist*

Hazard Analysis and Risk Assessment (HARA)

| Project Number & Name | LionDriver |
|---|---|
| Document ID (HARA) | WP-C-03 |
| Document Title | Confirmation Measures - HARA (Hazard Analysis and Risk Assessment) |
| HARA Revision | 0.2 (Cartesian) |
| HARA Status | Draft: ratings are proposals for review; not approved until the I3 confirmation review (WP-C-03 header) |
| Source HARA | WP-C-03-hara-cartesian.xlsx |
| Checklist Generated | 2026-10-12 |
| Standard | ISO 26262:2018 Part 3 §7 (HARA) and Part 8 §9 (verification) |
| Reviewer | (to be assigned — independence per ISO 26262-2 Table 1) |

## General Info

*General Information*

Tabs in this Checklist

| Tab | Purpose |
|---|---|
| Title | HARA being assessed and reviewer info |
| General Info | This tab — TOC and document conventions |
| Guide | How to interpret ratings and use the checklist |
| Summary | Statistical roll-up of findings |
| Confirmation Review | Generic doc-quality checks (ISO 26262-8 §10) |
| Functional Safety Assessment | HARA substantive checks (ISO 26262-3 §7) |
| Verification Assessment | HARA verification checks (ISO 26262-8 §9 and §7.4.5) |

References

**ID.** Title

**Ref-1.** ISO 26262:2018 — Road vehicles - Functional safety

**Ref-2.** TOMCO HARA Confirmation Measures template (template inspiration for layout)

**Ref-3.** Source HARA workbook — see Title tab

## Guide

*Guide — How to Use This Checklist*

| # | Instruction |
|---|---|
| 1 | Each check has an Assessment column. Possible values: FC (Fully Compliant), LC (Largely Compliant), PC (Partially Compliant), NO (Not Compliant), NA (Not Applicable), or blank (pending reviewer judgment). |
| 2 | Findings cells contain evidence the auto-reviewer found in the source HARA. Cells marked '(Auto-suggest, requires reviewer judgment)' need a human pass. |
| 3 | Page/Section cells reference where in the source HARA the evidence lives so you can verify each finding directly. |
| 4 | Recommended Actions cells contain corrective actions for any non-compliances. They do NOT modify the source HARA — the analyst decides whether to fix the HARA and re-run the checklist. |
| 5 | Confidence column: High = directly verified from xlsx content; Medium = inferred with caveat; Low = subjective or external artifact required. |
| 6 | Obligation: Shall = mandatory; Should = recommended. A 'NO' on a Shall is a major non-conformance; on a Should is a minor non-conformance. |
| 7 | The Summary tab rolls up counts from the three review tabs. Update an Assessment cell and the Summary recomputes. |
| 8 | Acceptance of the HARA can only be granted once the Functional Safety Assessment indicates Functional Safety has been achieved. Statistical summaries are informational only. |
| 9 | The reviewer is responsible for the final judgment. The auto-fill is an aid, not a substitute. ISO 26262-2 requires confirmation reviews to have I1 / I2 / I3 independence per ASIL. |

## Summary

*Summary — Statistical Roll-up*

**Overall Status.** TBD — Reviewer to set after evaluating major non-conformances.

Confirmation Review (CR)

| Metric | Count | % of Applicable | Notes |
|---|---|---|---|
| Total Items | 14 |  |  |
| Not Applicable | 0 | 0% |  |
| Applicable | 14 |  |  |
| Pending (reviewer to assess) | 5 | 36% |  |
| Fully Compliant (FC) | 9 | 64% |  |
| Largely Compliant (LC) | 0 | 0% | Minor gaps, no safety impact |
| Partially Compliant (PC) | 0 | 0% |  |
| Not Compliant (NO) | 0 | 0% |  |
| Major Non-Conformances (NO + Shall) | 0 |  | Block acceptance |
| Minor Non-Conformances (NO + Should) | 0 |  |  |

Functional Safety Assessment (FSA)

**Metric.** Count · % of Applicable · Notes

**Total Items.** 24

**Not Applicable.** 2 · 8%

**Applicable.** 22

**Pending (reviewer to assess).** 6 · 27%

**Fully Compliant (FC).** 14 · 64%

**Largely Compliant (LC).** 1 · 5% · Minor gaps, no safety impact

**Partially Compliant (PC).** 1 · 5%

**Not Compliant (NO).** 0 · 0%

**Major Non-Conformances (NO + Shall).** 0 · Block acceptance

**Minor Non-Conformances (NO + Should).** 0

Verification Assessment (VA)

**Metric.** Count · % of Applicable · Notes

**Total Items.** 44

**Not Applicable.** 1 · 2%

**Applicable.** 43

**Pending (reviewer to assess).** 39 · 91%

**Fully Compliant (FC).** 2 · 5%

**Largely Compliant (LC).** 0 · 0% · Minor gaps, no safety impact

**Partially Compliant (PC).** 2 · 5%

**Not Compliant (NO).** 0 · 0%

**Major Non-Conformances (NO + Shall).** 0 · Block acceptance

**Minor Non-Conformances (NO + Should).** 0

Findings (NO and PC items)

**Tab.** ID · Requirement · Finding

**FSA.** 8 · Were hazardous events determined for all relevant combinations of operational situations and hazards? · HARA has 2790 rows; expected ~6930 for full Cartesian. Coverage may be incomplete.

**VA.** 33 · Have the HARA-specific items been verified (see 33a–e)? · HARA has 2790 rows; expected ~6930 for full Cartesian. Coverage may be incomplete.

**VA.** 33d · Completeness of the coverage of the hazardous events? · HARA has 2790 rows; expected ~6930 for full Cartesian. Coverage may be incomplete.

## Confirmation Review

*Confirmation Review*

| ID | Section | Requirement | Obligation | Assessment | Findings | Page/Section in HARA | Recommended Actions |
|---|---|---|---|---|---|---|---|
| Document Quality |  |  |  |  |  |  |  |
| 1 | Document Quality | Is the document structured in a clear manner (using headlines, template layouts, context etc.) that supports the maintainability and understandability? | Shall | FC | Document is structured into 15 tabs with distinct sections (Title, Doc Control, Assumptions, etc.). | All tabs |  |
| 2 | Document Quality | On the date the document was first created, was the latest template available used? | Should | — | (Auto-suggest, requires reviewer judgment) Template version cannot be detected from the xlsx content alone. |  | Confirm the latest applicable HARA template was used at document creation. |
| 3 | Document Quality | Does the document structure facilitate the search for relevant information e.g. cross references, index table, list of abbreviations? | Should | FC | Document has a Title/Contents tab and a References tab; structured columns aid search. | Sheets: 00_Title_Page, 07_Severity_Reference |  |
| 4a | Document Quality | Does the title cover the scope of the content? | Shall | — | (Auto-suggest, requires reviewer judgment) Title is: 'Hazard Analysis and Risk Assessment (HARA)'. Reviewer to confirm it covers the document scope. | Title page row 2 | (Reviewer to verify and assess) |
| 4b | Document Quality | Are the author and approver(s) listed? | Shall | FC | Author='Assurance team (draft)', Approver='Safety manager' both populated on Title page. | Title page |  |
| 4c | Document Quality | Is there a unique identification for each different revision (version) e.g. in a history table? | Shall | FC | Revision='0.2 (Cartesian)' is set on the Title page. | Title page Revision field |  |
| 4d | Document Quality | Is there a change history available? | Shall | FC | Document Control tab contains 5 revision history row(s). | Sheet '01_Document_Control' |  |
| 4e | Document Quality | Is the status of the work product provided? | Shall | FC | Status='Draft: ratings are proposals for review; not approved until the I3 confirmation review (WP-C-03 header)' is set on the Title page. | Title page Status field |  |
| 5 | Document Quality | Is the current applicable revision (version) of a document clearly identifiable? | Shall | FC | Current revision '0.2 (Cartesian)' is identifiable on Title page. | Title page Revision field |  |
| 6 | Document Quality | Is the document under configuration and change management? | Shall | — | (Auto-suggest, requires reviewer judgment) Configuration management is an organizational practice; cannot be verified from xlsx content. |  | Confirm the document is checked into the project's configuration-management system (e.g., Polarion, DOORS, Git). |
| 7 | Document Quality | Are the header and footer updated? | Should | — | (Auto-suggest, requires reviewer judgment) Worksheet headers/footers cannot be reliably verified programmatically. |  | Open the workbook in Excel and confirm header/footer reflect current document ID and revision. |
| 8 | Document Quality | Does this document contain a correct table of content? | Shall | FC | A Title or Contents tab is present in the first three sheets. | Sheet '00_Title_Page' |  |
| 9 | Document Quality | Does the Reference Table list all of the references contained in the Work Product? | Should | — | (Auto-suggest, requires reviewer judgment) References-style content found on sheet '07_Severity_Reference'. Reviewer to confirm completeness. | Sheet '07_Severity_Reference' | (Reviewer to verify and assess) |
| 10 | Document Quality | Have all sections of the Work Product been completed? | Should | FC | All major sections are populated. HARA rows 100% complete; SGs 100% complete. |  |  |

## Functional Safety Assessment

*Functional Safety Assessment*

| ID | Section | Requirement | Obligation | Assessment | Findings | Page/Section in HARA | Recommended Actions |
|---|---|---|---|---|---|---|---|
| Prerequisites |  |  |  |  |  |  |  |
| 1 | Prerequisites | Prerequisites Available and Useful: Item Definition | Shall | — | (Auto-suggest, requires reviewer judgment) Item-definition content appears on '02_Assumptions' or boundary tab. Reviewer to confirm an Item Definition document exists and is referenced. | Sheet '02_Assumptions' | (Reviewer to verify and assess) |
| 2 | Prerequisites | Further Supporting Information: Impact analysis (if applicable), relevant information on other independent items | Should | — | (Auto-suggest, requires reviewer judgment) Impact analysis and information on independent items typically reside in separate documents. |  | Confirm the impact analysis and any related-item information are referenced in the HARA. |
| Initiation |  |  |  |  |  |  |  |
| 3 | Initiation | Have technical safety requirements been specified in accordance with the FSC and the preliminary architectural assumptions of the item? | Shall | NA | This requirement appears to belong to a TSC review (refers to Technical Safety Requirements). Mark NA for HARA review. |  |  |
| 4 | Initiation | If applicable, have external system interfaces properties been considered? | Shall | NA | This requirement appears to belong to a TSC review (refers to external interface properties). Mark NA for HARA review. |  |  |
| Situation Analysis and Hazard Identification |  |  |  |  |  |  |  |
| 5 | Situation Analysis and Hazard Identification | Have the operational situations and operating modes been described for both correct and incorrect use of the vehicle? | Shall | FC | Operating environment tab lists 23 situation rows. | Sheet '06_Operating_Environment' |  |
| 6 | Situation Analysis and Hazard Identification | Were adequate techniques used to systematically determine all hazards? | Shall | LC | Each function evaluated against 11 malfunction guide words. |  | Confirm coverage; consider adding the remaining 3 guide words from the standard 14-malfunction set. |
| 7 | Situation Analysis and Hazard Identification | Are the hazards defined in terms of the conditions or behavior that can be observed at the vehicle level? | Shall | FC | 30/30 sampled hazardous events use vehicle-level language. | Sheet '12_HARA_Worksheet' |  |
| 8 | Situation Analysis and Hazard Identification | Were hazardous events determined for all relevant combinations of operational situations and hazards? | Shall | PC | HARA has 2790 rows; expected ~6930 for full Cartesian. Coverage may be incomplete. |  | Verify Cartesian coverage of (function × malfunction × operational situation). |
| 9 | Situation Analysis and Hazard Identification | Were all consequences of hazardous events identified? | Shall | — | (Auto-suggest, requires reviewer judgment) Hazardous-event descriptions are present; reviewer to confirm consequence (occupant, other road user, property) is captured for each. | Sheet '12_HARA_Worksheet' | (Reviewer to verify and assess) |
| 10 | Situation Analysis and Hazard Identification | Were the appropriate measures to mitigate or control hazards outside the scope of ISO 26262 highlighted and reported? | Should | — | (Auto-suggest, requires reviewer judgment) Out-of-scope hazards (cybersecurity, SOTIF, environmental) and their owners are typically called out in Assumptions. | Sheet '02_Assumptions' | (Reviewer to verify and assess) |
| Classification of Hazardous Events |  |  |  |  |  |  |  |
| 10b | Classification of Hazardous Events | Have all identified hazardous events, except those outside the scope of ISO 26262, been classified? | Shall | FC | All 2790 HARA rows have S, E, and C populated. | Sheet '12_HARA_Worksheet' |  |
| 11 | Classification of Hazardous Events | Has the severity of potential harm been estimated based on a defined rationale and assigned to S0, S1, S2 or S3? | Shall | FC | All severity ratings have rationale (2790/2790). S values used: ['S0', 'S1', 'S2', 'S3']. | Sheet '12_HARA_Worksheet', S Rationale column |  |
| 12 | Classification of Hazardous Events | Is severity class S0 used only when malfunctioning behavior is clearly limited to material damage and does not involve harm to persons (no further analysis)? | Shall | FC | 852 S0 rows present; none derive a safety goal (ASIL is — or QM as expected). |  |  |
| 13 | Classification of Hazardous Events | Has the probability of exposure of each operational situation been estimated and assigned to E0, E1, E2, E3 or E4 with rationale? | Shall | FC | All exposure ratings have rationale (2790/2790). E values: ['E1', 'E2', 'E3', 'E4']. | Sheet '12_HARA_Worksheet', E Rationale column |  |
| 14 | Classification of Hazardous Events | Did the estimating of the probability of exposure NOT take into account the number of vehicles equipped with the item? | Shall | — | (Auto-suggest, requires reviewer judgment) Verify E rationale text references operational-situation probability, not number of vehicles equipped. | Sheet '12_HARA_Worksheet', E Rationale column | (Reviewer to verify and assess) |
| 15 | Classification of Hazardous Events | Was class E0 assigned for situations that are extremely unusual or incredible and therefore not followed up? | Shall | FC | No E0 rows; check vacuously satisfied. |  |  |
| 16 | Classification of Hazardous Events | Has the controllability of each hazardous event been estimated and assigned to C0, C1, C2 or C3 with rationale? | Shall | FC | All controllability ratings have rationale (2790/2790). C values: ['C0', 'C1', 'C2', 'C3']. | Sheet '12_HARA_Worksheet', C Rationale column |  |
| 17 | Classification of Hazardous Events | For hazards addressing item unavailability that does not affect safe operation, are appropriate justifications or regulatory citations provided? | Should | — | (Auto-suggest, requires reviewer judgment) Hazards addressing item unavailability: confirm appropriate justification or applicable regulatory citations. |  | (Reviewer to verify and assess) |
| Determination of ASIL and Safety Goals |  |  |  |  |  |  |  |
| 18 | Determination of ASIL and Safety Goals | Was an ASIL determined for each hazardous event using S, E, and C? | Shall | FC | ASIL determined for all 1938 eligible HARA rows (excluding S0 and E0). | Sheet '12_HARA_Worksheet', ASIL column |  |
| 19 | Determination of ASIL and Safety Goals | Has it been determined that the chosen level of detail of operational situations does not lead to inappropriate lowering of ASIL? | Should | FC | 23 operating-environment rows; granularity supports realistic exposure ratings. |  |  |
| 20 | Determination of ASIL and Safety Goals | Was a safety goal determined for each hazardous event with ASIL≥A and were similar safety goals combined into one? | Shall | FC | 13 safety goals derived from 1221 ASIL≥A HARA rows; consolidation evident. | Sheet '13_Safety_Goals' |  |
| 21 | Determination of ASIL and Safety Goals | When similar safety goals were combined, was the highest ASIL assigned to the combined safety goal? | Shall | FC | All 13 safety goals carry an ASIL value (['A', 'B', 'C']); presumed to reflect worst-case across driving rows. |  |  |
| 22 | Determination of ASIL and Safety Goals | If a safety goal is achieved by transitioning to or maintaining safe state(s), were these safe state(s) specified? | Shall | FC | All 13 safety goals specify a safe state. | Sheet '13_Safety_Goals', Safe State column |  |
| 23 | Determination of ASIL and Safety Goals | Were the safety goals with their attributes specified in accordance with ISO 26262-8:2011, Clause 6? | Should | FC | All 13 safety goals have ID, ASIL, text, and safe state populated. | Sheet '13_Safety_Goals' |  |

## Verification Assessment

*Verification Assessment*

| ID | Section | Requirement | Obligation | Assessment | Findings | Page/Section in HARA | Recommended Actions |
|---|---|---|---|---|---|---|---|
| Verification Planning |  |  |  |  |  |  |  |
| 24 | Verification Planning | Does the Verification Plan ensure compliance and consistency with the FSC and preliminary architectural design assumptions? | Shall | — | (Auto-suggest, requires reviewer judgment) Verification Plan ensuring compliance with FSC is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 25 | Verification Planning | If applicable, was Safety Validation refined based on Technical Safety requirements? | Should | NA | Belongs to TSC/validation review, not HARA confirmation. |  |  |
| 26 | Verification Planning | Does the Verification Plan address content, methods, pass/fail criteria, env, tools, anomalies, regression? | Shall | — | (Auto-suggest, requires reviewer judgment) Verification Plan addressing content/methods/criteria/env/tools/anomalies/regression is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 26a | Verification Planning | Content of the work product(s) to be verified? | Shall | — | (Auto-suggest, requires reviewer judgment) Plan content is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 26b | Verification Planning | Methods to be used (consistent with Safety Plan)? | Shall | — | (Auto-suggest, requires reviewer judgment) Verification methods is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 26c | Verification Planning | Pass/fail criteria? | Shall | — | (Auto-suggest, requires reviewer judgment) Pass/fail criteria is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 26d | Verification Planning | Verification environment (if applicable)? | Shall | — | (Auto-suggest, requires reviewer judgment) Verification environment is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 26e | Verification Planning | Tools used for verification (if applicable)? | Shall | — | (Auto-suggest, requires reviewer judgment) Verification tools is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 26f | Verification Planning | Actions to be taken when anomalies are detected? | Shall | — | (Auto-suggest, requires reviewer judgment) Anomaly handling is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 26g | Verification Planning | The regression strategy? | Shall | — | (Auto-suggest, requires reviewer judgment) Regression strategy is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 27 | Verification Planning | Does verification planning consider method adequacy, complexity, prior experience, technology maturity? | Should | — | (Auto-suggest, requires reviewer judgment) Planning considerations is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 27a | Verification Planning | Adequacy of the verification methods? | Should | — | (Auto-suggest, requires reviewer judgment) Method adequacy is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 27b | Verification Planning | Complexity of the work product? | Should | — | (Auto-suggest, requires reviewer judgment) Work product complexity is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 27c | Verification Planning | Prior experiences related to verification of the work product? | Should | — | (Auto-suggest, requires reviewer judgment) Prior experience is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 27d | Verification Planning | Maturity of technologies / risks associated with their use? | Should | — | (Auto-suggest, requires reviewer judgment) Technology maturity is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| Verification Specification |  |  |  |  |  |  |  |
| 28 | Verification Specification | Are review/analysis checklists, simulation scenarios, or test cases specified for verification? | Shall | — | (Auto-suggest, requires reviewer judgment) Verification method specification is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 28a | Verification Specification | Review of analysis checklists? | Shall | — | (Auto-suggest, requires reviewer judgment) Review/analysis checklists (e.g., this skill's output) is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 28b | Verification Specification | Simulation scenarios? | Shall | — | (Auto-suggest, requires reviewer judgment) Simulation scenarios is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 28c | Verification Specification | Test cases, data, and objects? | Shall | — | (Auto-suggest, requires reviewer judgment) Test cases / data / objects is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 29 | Verification Specification | If applicable, for testing does the specification of each test case include the listed elements? | Shall | — | (Auto-suggest, requires reviewer judgment) Test case content specification is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 29a | Verification Specification | A unique identification? | Shall | — | (Auto-suggest, requires reviewer judgment) Test case unique identification is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 29b | Verification Specification | A reference to the version of the associated work product? | Shall | — | (Auto-suggest, requires reviewer judgment) Reference to verified work-product version is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 29c | Verification Specification | The preconditions and configurations? | Shall | — | (Auto-suggest, requires reviewer judgment) Preconditions and configurations is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 29d | Verification Specification | If appropriate, the environmental conditions? | Shall | — | (Auto-suggest, requires reviewer judgment) Environmental conditions is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 29e | Verification Specification | The input data, their time sequence and values? | Shall | — | (Auto-suggest, requires reviewer judgment) Input data / sequences / values is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 29f | Verification Specification | The expected behavior including output data and tolerance behavior? | Shall | — | (Auto-suggest, requires reviewer judgment) Expected behavior / output / tolerances is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 30 | Verification Specification | Are test cases grouped by method with environment, dependencies, and resources specified per method? | Shall | — | (Auto-suggest, requires reviewer judgment) Test case grouping is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 30a | Verification Specification | The test environment? | Shall | — | (Auto-suggest, requires reviewer judgment) Test environment per group is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 30b | Verification Specification | The logical and temporal dependencies? | Shall | — | (Auto-suggest, requires reviewer judgment) Logical/temporal dependencies is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 30c | Verification Specification | The resources? | Shall | — | (Auto-suggest, requires reviewer judgment) Resources is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| Verification Execution and Evaluation |  |  |  |  |  |  |  |
| 31 | Verification Execution and Evaluation | Was the verification executed as per the verification plan and specification? | Shall | — | (Auto-suggest, requires reviewer judgment) Verification executed per plan is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 32 | Verification Execution and Evaluation | Does the Verification Report include the listed elements? | Shall | — | (Auto-suggest, requires reviewer judgment) Verification Report content is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 32a | Verification Execution and Evaluation | A unique identification of the verified work product? | Shall | — | (Auto-suggest, requires reviewer judgment) Verified work-product unique identification is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 32b | Verification Execution and Evaluation | A reference to the verification plan and specification? | Shall | — | (Auto-suggest, requires reviewer judgment) Reference to plan and specification is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 32c | Verification Execution and Evaluation | Configuration of verification env / tools / calibration data? | Shall | — | (Auto-suggest, requires reviewer judgment) Verification environment / tools / calibration data is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 32d | Verification Execution and Evaluation | The level of compliance of the verification results with expected results? | Shall | — | (Auto-suggest, requires reviewer judgment) Compliance level of verification results is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 32e | Verification Execution and Evaluation | An unambiguous pass/fail statement (with rationale on failure)? | Shall | — | (Auto-suggest, requires reviewer judgment) Pass/fail statement and rationale is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| 32f | Verification Execution and Evaluation | The reasons why any verification step(s) were not executed? | Shall | — | (Auto-suggest, requires reviewer judgment) Reasons for un-executed verification steps is governed by an external Verification Plan / Specification / Report — not in the HARA xlsx. |  | Verify against the project's Verification Plan, Specification, and Report documents. |
| HARA-specific Verification |  |  |  |  |  |  |  |
| 33 | HARA-specific Verification | Have the HARA-specific items been verified (see 33a–e)? | Shall | PC | HARA has 2790 rows; expected ~6930 for full Cartesian. Coverage may be incomplete. |  | Verify Cartesian coverage of (function × malfunction × operational situation). |
| 33a | HARA-specific Verification | Completeness with regard to situations? | Shall | FC | 23 operating-environment rows; situational completeness adequate. |  |  |
| 33b | HARA-specific Verification | Compliance with the item definition? | Shall | — | (Auto-suggest, requires reviewer judgment) 9 functions enumerated in the HARA. Reviewer to verify each is in the Item Definition. | Sheet '04_Functions' | (Reviewer to verify and assess) |
| 33c | HARA-specific Verification | Consistency with related hazard analyses and risk assessments? | Shall | — | (Auto-suggest, requires reviewer judgment) Consistency with related HARAs / hazard analyses cannot be verified from a single workbook. |  | (Reviewer to verify and assess) |
| 33d | HARA-specific Verification | Completeness of the coverage of the hazardous events? | Shall | PC | HARA has 2790 rows; expected ~6930 for full Cartesian. Coverage may be incomplete. |  | Verify Cartesian coverage of (function × malfunction × operational situation). |
| 33e | HARA-specific Verification | Consistency of the assigned ASILs with the corresponding hazardous events? | Shall | FC | HARA produced by hara-builder uses formula-driven ASIL (INDEX/MATCH against ASIL Matrix tab); recorded ASIL is structurally consistent with S/E/C inputs. | Sheet '12_HARA_Worksheet', ASIL formula chain |  |
