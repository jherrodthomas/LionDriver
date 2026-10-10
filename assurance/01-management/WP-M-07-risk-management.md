# WP-M-07 Project Risk Management Plan and Register

| Field | Value |
|---|---|
| Work product | WP-M-07 Project risk management plan and register |
| Standard reference | ASPICE 4.0 MAN.5 (risk management); ISO 26262-2 §6 (planning and progress, by reference to WP-M-02) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All (project risk; not product hazard analysis) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

This document defines how LionDriver identifies, analyses, treats and monitors **project risks**: events that could stop the project from achieving the assurance path in [WP-M-01](WP-M-01-assurance-strategy.md) on its planned scope, effort and quality. It also tracks the open strategic decisions D-01…D-08 from [WP-M-01 §8](WP-M-01-assurance-strategy.md#8-strategic-decisions-required).

Product risks (hazards to road users, threats to the vehicle) are **not** managed here. They belong to the HARA ([WP-C-03](../02-concept/WP-C-03-hara.md)), the SOTIF analyses ([WP-C-05](../02-concept/WP-C-05-sotif-hazard-identification.md)) and the TARA ([WP-C-09](../02-concept/WP-C-09-tara.md)). Where a project risk would weaken a product safety argument, the register says so and links the affected work product.

## 2. Risk management process

### 2.1 Identification

Sources: the [gap assessment](../00-assessment/gap-assessment.md), [WP-M-01 §9](WP-M-01-assurance-strategy.md#9-top-risks-to-the-assurance-path), gate reviews, QA findings ([WP-M-05](WP-M-05-quality-assurance-plan.md)), confirmation findings ([WP-M-06](WP-M-06-confirmation-measures-plan.md)), upstream changes ([WP-M-11](WP-M-11-upstream-and-supplier-management.md)), and anyone on the project. A risk is raised as a GitHub issue with label `risk` and added to §4 in the next update of this document.

### 2.2 Analysis

| Score | Probability (P) | Impact (I) |
|---|---|---|
| 1 | Very unlikely (< 10 %) | Negligible: absorbed within a phase |
| 2 | Unlikely (10–30 %) | Minor: delays one work product, or weakens a non-critical claim |
| 3 | Possible (30–50 %) | Moderate: delays a gate by up to ~2 months, or needs re-work of several work products |
| 4 | Likely (50–80 %) | Major: delays a gate by more than ~2 months, or a sub-claim (G1–G5) can only be made with significant restrictions |
| 5 | Almost certain (> 80 %) | Severe: a gate cannot be passed, the ASIL claim on the envelope is not achievable, or the project stops |

Exposure = P × I. **High** ≥ 15, **Medium** 8–14, **Low** ≤ 7. Scores are engineering judgement at baseline `8b8c6ae` and are re-scored at each review.

### 2.3 Treatment

| Strategy | When used |
|---|---|
| Avoid | Change scope or approach so the risk cannot occur (e.g., remove a feature from the reference configuration) |
| Mitigate | Reduce probability or impact |
| Transfer | Move to a party able to carry it (e.g., external assessor, pen tester). Limited options in an open-source project |
| Accept | Record rationale; accepted High risks need the safety manager's agreement if they affect a safety claim |

Each High and Medium risk has an owner, a treatment action with a due gate, and a trigger that shows the risk is materialising.

### 2.4 Monitoring

- Reviewed monthly by the project maintainer with the progress review ([WP-M-03 §8](WP-M-03-project-plan.md)) and at every gate review ([WP-M-02 §10](WP-M-02-safety-plan.md)).
- Changes in score, new risks and closed risks are recorded in §4 (via pull request, so the history is in git).
- A risk becomes an issue (a problem to resolve via [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md)) when it occurs.
- Risks with exposure ≥ 15 that are not decreasing over two reviews are escalated to the gate review agenda.

## 3. Roles

| Role | Responsibility |
|---|---|
| Project maintainer | Owns this process and the register; approves acceptance of risks |
| Safety manager | Agrees treatment of risks that affect safety claims; maintains the link to the safety case |
| Risk owner | Carries out treatment, reports status |
| Everyone | Raises risks |

## 4. Risk register (initial)

P/I/E = probability / impact / exposure. Status at baseline: all **Open**; no treatment has been carried out yet.

| ID | Risk (cause → effect) | Source | P | I | E | Treatment | Owner | Trigger / indicator | Due |
|---|---|---|---|---|---|---|---|---|---|
| R-01 | Single maintainer holds every role → critical-path bottleneck; independence (I1 and above) cannot be achieved internally; work stalls if the maintainer is unavailable | WP-M-01 §9; WP-M-02 §3 | 5 | 5 | 25 | Mitigate: recruit verification reviewer and QA (B-11); external assessor; document work so others can continue; bus-factor plan for keys and accounts | PM | No second reviewer named by G0 | G0 |
| R-02 | No supplier evidence for the comma device / STM32H7 → FMEDA, metrics and component qualification incomplete; ASIL claim on the envelope limited | WP-M-01 §9; T-04; GAP-15 | 4 | 5 | 20 | Mitigate: derive FMEDA from published panda design and STM32H7 safety manual; conservative assumptions; decide early (G2) whether an external monitor is needed. Accept residual limitation in the safety case if needed | SM / HW | Schematic-level data unavailable at P3 start | G2 |
| R-03 | OEM ECU behaviour (EPS limiting and fault reaction, PCM, PCS availability) cannot be verified from Toyota → AoUs remain assumptions; controllability and envelope arguments weakened | WP-M-01 §9; GAP-05 | 4 | 4 | 16 | Mitigate: characterise by vehicle test under WP-V-07; restrict claims to what was measured | SM | Tests cannot reproduce EPS fault reactions safely | G1–G4 |
| R-04 | Upstream velocity and sync pressure → safety case stale; unreviewed safety changes enter | WP-M-01 §9; GAP-37 | 4 | 4 | 16 | Avoid/mitigate: freeze (D-02); sync only by change request with impact analysis; track upstream security fixes as anomalies | PM | Sync PR merged without impact analysis | G0 |
| R-05 | Safety code not under LionDriver configuration control (submodules resolve to `commaai/*`, tinygrad on `master`) → cannot change or baseline the envelope | GAP-29; D-01 | 5 | 4 | 20 | Mitigate: fork opendbc and panda, absolute URLs, pin tinygrad (B-02) | PM | Not done by G0 | G0 |
| R-06 | No HIL or on-device verification in the fork → no target-level evidence for P4; fault injection impossible | GAP-30; D-04 | 5 | 4 | 20 | Mitigate: build HIL bench (WBS 5.1) starting in P2; self-hosted runner | HIL owner | Bench parts not procured by end of P2 | G3 |
| R-07 | ML insufficiencies cannot be quantified without training data → SOTIF unknown-scenario residual risk cannot be shown | WP-M-01 §9; T-10; GAP-22 | 4 | 5 | 20 | Mitigate: tight ODD; validation targets; fork-owned drive logs; scenario simulation; field monitoring; envelope bounds | SL | Validation targets need more driving than resources allow | G2 |
| R-08 | No external assessor engaged, or none affordable → HARA confirmation review (I3) cannot be done; G1 blocked | D-06; T-09 | 3 | 5 | 15 | Mitigate: approach assessors in P0 (B-09); budget decision (WP-M-03 OI-2) | PM | No quote by end of P0 | G0 |
| R-09 | Single-channel panda MCU sharing power, clock and board with the SoC → DFA shows insufficient independence for the HARA ASIL | WP-M-01 §4.2.3; GAP-11 | 3 | 5 | 15 | Mitigate: early DFA (P2); options: ASIL decomposition with vehicle-side measures, or external monitor (scope change) | ENG / HW | DFA identifies unmitigated common-cause initiators | G2 |
| R-10 | Safety mode and parameter set by the QM SoC (`0xdc`), debug relay `0xc5` not gated → FFI argument fails | GAP-09 | 4 | 4 | 16 | Mitigate: lock safety mode for the reference configuration in panda firmware; gate `0xc5` (WBS 4.3) | ENG | Lock not feasible without breaking upstream interfaces | G3 |
| R-11 | Envelope fault handling weak (IWDG not initialised, faults report-only, no E2E counters) → required hardening larger than estimated | GAP-01, GAP-07, GAP-08 | 3 | 4 | 12 | Mitigate: scope hardening in P2 from TSRs; prototype IWDG and safe-state early | ENG | P3 estimate exceeded by > 25 % | G3 |
| R-12 | comma.ai bans LionDriver devices from its servers (fork policy) or changes server APIs → users lose services; update and upload paths break | `docs/SAFETY.md`; WP-M-04 §2.3; T-11 | 3 | 3 | 9 | Avoid: no safety function depends on comma servers; comply with the fork policy (keep safety tests, no trademark); plan fork-owned update path | CSM | Ban notice or API change | G1 |
| R-13 | Tool qualification for arm-none-eabi-gcc, cppcheck/MISRA, coverage and mutation tools is harder than planned (comma-packaged binaries, mutable branches) | GAP-34 | 3 | 3 | 9 | Mitigate: pin tool versions; qualify by validation and increased confidence from use where justified; consider alternative builds | ENG | TCL3 tool without feasible qualification route | G3 |
| R-14 | Structural coverage beyond line coverage (branch, MC/DC) and target-level testing require new tooling and test effort | GAP-13 | 3 | 3 | 9 | Mitigate: evaluate coverage tools in P2; run tests on Cortex-M7 via HIL | ENG | No MC/DC-capable tool selected by G2 | G2 |
| R-15 | Firmware signing remains RSA-1024/SHA-1 with debug key acceptance → CS goals for firmware authenticity not met | GAP-24, GAP-25 | 3 | 4 | 12 | Mitigate: LionDriver key with modern algorithm, release build pipeline, RDP/WRP (WBS 4.4) | CSM | Bootstub change bricks devices in test | G3 |
| R-16 | Remote access and OTA surface (athena, SSH, git-based updates) cannot be constrained without breaking user expectations → large TARA residual risk | GAP-26, GAP-27 | 3 | 3 | 9 | Mitigate: disable or constrain in reference configuration; document in user information | CSM | Constraint rejected by users / maintainers | G2 |
| R-17 | Experimental Mode on by default (upstream `f21bfc3`) stays enabled → unassessed end-to-end longitudinal behaviour in the reference configuration | GAP-18; D-08 | 3 | 4 | 12 | Avoid: disable by default for the reference configuration pending SOTIF assessment (B-06) | SL | Default still on at G1 | G1 |
| R-18 | Public-road testing happens before the analyses and test procedures are done → harm to third parties; project credibility lost | WP-M-01 §9; gap §9 action 10 | 2 | 5 | 10 | Avoid: hold point in WP-M-02 §4 and WP-M-04 OR-5; trained safety drivers only | SM | Any LionDriver road test before G1 | G1 |
| R-19 | No test vehicle access or insurance for test use → no AoU characterisation, no validation | WP-M-03 §6 | 3 | 4 | 12 | Mitigate: confirm vehicle and insurance in P1 (WP-M-03 OI-4) | PM | Not confirmed by mid-P1 | G1 |
| R-20 | Funding for external assessor, pen test and HIL hardware not available → G1/G5 confirmation and CS validation cannot be done | WP-M-03 §4.2 | 3 | 5 | 15 | Mitigate: funding decision in P0; phase external spend by gate | PM | No funding source by G0 | G0 |
| R-21 | Competence gaps (FS expert level for safety manager, SOTIF, ML, HW safety) → work products rejected in confirmation reviews | WP-M-04 §4.3 | 4 | 3 | 12 | Mitigate: training plan (WP-M-04 §5); external experts; early interim FSA feedback | PM | Major confirmation findings on method | G1 |
| R-22 | Effort estimate (2–4 person-years) is optimistic → schedule overrun at every gate | WP-M-03 §4 | 4 | 3 | 12 | Mitigate: re-estimate after HARA (WP-M-03 OI-5); reduce scope (narrower ODD) rather than lower quality | PM | Phase exceeds high estimate by > 25 % | Each gate |
| R-23 | Licensed standards not available to the team → clause references and Table 1 values cannot be checked; audit findings | WP-M-03 OI-3; WP-M-06 OI-1 | 3 | 3 | 9 | Mitigate: obtain licensed copies before G0 confirmation reviews | PM | Not available at G0 | G0 |
| R-24 | Upstream model swaps or tinygrad changes alter driving behaviour silently → scenario evaluations invalid | D-05; GAP-22 | 3 | 4 | 12 | Avoid: pin weights and tinygrad per release; any model change triggers SOTIF re-evaluation | ML | Model hash differs from release record | G3 |
| R-25 | Hosted CI logs and artefacts expire → verification evidence lost | WP-M-05 §9 | 3 | 2 | 6 | Mitigate: archive release-relevant CI results with the release record | PM | Evidence link broken at audit | G3 |

Summary at baseline: 25 risks — High 11, Medium 13, Low 1 (§4.1).

### 4.1 Exposure summary

| Band | Risks |
|---|---|
| High (≥ 15) | R-01, R-02, R-03, R-04, R-05, R-06, R-07, R-08, R-09, R-10, R-20 |
| Medium (8–14) | R-11, R-12, R-13, R-14, R-15, R-16, R-17, R-18, R-19, R-21, R-22, R-23, R-24 |
| Low (≤ 7) | R-25 |

## 5. Decision log (strategic decisions from WP-M-01 §8)

Each decision is tracked as a GitHub issue labelled `decision:D-nn`. A decision is closed when the project maintainer records the choice, the rationale and the date in this table (via pull request) and the dependent work products are updated.

| ID | Decision | Recommendation (WP-M-01) | Status | Owner | Needed by | Linked risks |
|---|---|---|---|---|---|---|
| D-01 | Take configuration control of the safety code | Fork opendbc and panda; absolute submodule URLs; pin tinygrad | Open | PM | G0 | R-05 |
| D-02 | Upstream synchronization policy | Freeze; sync only by change request with impact analysis | Open | PM | G0 | R-04 |
| D-03 | CI for the fork | Disable/replace comma-dependent workflows; fork-owned replay references; safety tests, MISRA and mutation in fork CI | Open | PM | G0 | R-05, R-25 |
| D-04 | HIL capability | Build a minimal HIL bench | Open | PM | G2 (decision); G3 (bench) | R-06 |
| D-05 | Model update policy | Pin weights per release; model change re-runs scenario evaluations | Open | PM / ML | G1 | R-24 |
| D-06 | External assessor | Engage an independent FuSa assessor for the G1 HARA confirmation review | Open | PM | G0 | R-08, R-20 |
| D-07 | Work product format | Markdown docs-as-code; machine-readable requirements in `trace/`; PR review | Open (de facto in use; not formally decided) | PM | G0 | — |
| D-08 | Default enablement of Experimental Mode | Disabled for the reference configuration until validated | Open | PM / SL | G1 | R-17 |

## 6. Records

- This document (register and decision log), versioned in git.
- GitHub issues labelled `risk` and `decision:D-nn`, with review comments.
- Monthly review notes on the milestone tracking issue (WP-M-03 §8).

## 7. Open items

| ID | Open item | Owner | Due |
|---|---|---|---|
| OI-1 | Create `risk` and `decision:D-nn` labels and one issue per High risk and per decision | PM | G0 |
| OI-2 | Have the initial scores reviewed by a second person (scores are single-author judgement) | PM | G0 |
| OI-3 | Decide whether MAN.5 is added to the ASPICE capability target in WP-M-01 T-12 (currently not listed) | PM | G0 |
| OI-4 | Link R-02, R-03, R-07 and R-09 to the corresponding counter-evidence or assumption nodes in the safety case once WP-K-01 has an argument structure | SM | G1 |
