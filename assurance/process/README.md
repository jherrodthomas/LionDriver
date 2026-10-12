# WP-P-11 Integrated Process Model and Process Maps

| Field | Value |
|---|---|
| Work product | WP-P-11 Integrated process model (machine-readable) and generated process maps |
| Standard reference | ISO 26262-2:2018 §6 (safety lifecycle, planning of activities); ISO 21448:2022 §4; ISO/SAE 21434:2021 §6 (cybersecurity activities and their tailoring); ISO/PAS 8800:2024 (AI safety lifecycle); ASPICE 4.0 MAN.3 (project lifecycle definition). Informative: Integrated Automotive Standards Handbook (ISH-2026-001) §3.3–3.4, Ch. 5, Ch. 13 |
| Version | 0.1 |
| Status | Draft (all phases G0 governance to G6 operation modelled) |
| ASIL / scope | Process (all disciplines) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` |

## 1. Purpose

LionDriver's plans ([WP-M-02](../01-management/WP-M-02-safety-plan.md), [WP-M-08](../01-management/WP-M-08-sotif-plan.md), [WP-M-09](../01-management/WP-M-09-cybersecurity-plan.md), [WP-M-10](../01-management/WP-M-10-ai-safety-plan.md)) say *what* each discipline produces. The [register (WP-M-00)](../01-management/WP-M-00-work-product-register.md) says *which gate* needs each work product. Neither says how the disciplines' work fits together inside a phase: which analysis waits for which, and where two disciplines must agree.

This folder records that as one integrated lifecycle. It follows the handbook principle "one lifecycle, not multiple parallel lifecycles":

- each phase is a set of **activities** in discipline **lanes**;
- activities are linked by the **work products** they consume and produce;
- explicit **cross-domain interfaces** mark where one discipline's result depends on another's;
- one **gate** collects the work and the **confirmation measures**.

The model is data, so a checker keeps it consistent with the documents and a generator draws the maps from it.

| Map | Content |
|---|---|
| [`10-safety-case/gates/skeletons/`](../10-safety-case/gates/skeletons/) | One pre-filled gate review skeleton per gate, following the gate record template ([gates README](../10-safety-case/gates/README.md)) |
| [maps/lifecycle.md](maps/lifecycle.md) | L0: the seven phases G0…G6, the feedback from operation into earlier phases, their exit criteria and the handbook chapter each one corresponds to |
| [maps/g0-governance.md](maps/g0-governance.md) | L1 for the governance phase: the plans and procedures the later phases read from, G0 readiness including role records that disagree |
| [maps/g1-concept.md](maps/g1-concept.md) | L1 for the concept phase: swimlane map, interface map, activity table with clauses, clause coverage per standard, G1 readiness |
| [maps/g2-system-design.md](maps/g2-system-design.md) | L1 for the system design phase, same sections, G2 readiness |
| [maps/g3-hw-sw-development.md](maps/g3-hw-sw-development.md) | L1 for the hardware and software development phase, same sections, G3 readiness |
| [maps/g4-integration-and-verification.md](maps/g4-integration-and-verification.md) | L1 for the integration and verification phase, same sections, G4 readiness |
| [maps/g5-validation-and-release.md](maps/g5-validation-and-release.md) | L1 for the validation and release phase, same sections, G5 readiness |
| [maps/g6-operation.md](maps/g6-operation.md) | L1 for the operation phase, same sections plus the feedback routes into earlier phases, G6 readiness |

L2 (how to perform an activity) remains the procedures and plans the activities point to; it is not modelled here.

## 2. Single source of truth

The model holds only what no other document holds: the activities, their lanes, their inputs, the interfaces and the handbook mapping. Everything else is read at generation time:

| Fact | Read from |
|---|---|
| Gate names and exit criteria | WP-M-00 §2 |
| Clause references, ASPICE process, gate and status of each work product | WP-M-00 §3 (the row of each produced work product) |
| Who holds each lane's role, and by which gate | WP-M-02 §3.1 |
| Which confirmation measures a gate needs | WP-M-06 §9 |
| Whether a confirmation measure has been performed | A record in `10-safety-case/confirmation/` named as its README requires: `CR-<nn>-<WP-ID>-v<version>.md` for a confirmation review, `SR-<nn>-<gate>.md` for a per-gate SOTIF/AI review, `<measure>.md` otherwise. A CR planned at several gates (CR-03, CR-06) cannot be told apart by file name, so any record of it counts at each of its gates |

A change to the register, the safety plan or the confirmation plan therefore shows up in the maps on the next run, and `--check` fails in CI until the maps are regenerated.

## 3. Record format

Records use the same flat YAML subset as [`case/`](../case/README.md): a top-level list of mappings with scalar or flow-list values. Flow-list items cannot contain commas. One record per item, with a `kind`:

| Kind | File | Fields |
|---|---|---|
| `phase` | [`model/lifecycle.yaml`](model/lifecycle.yaml) | `id` (gate G0…G6), `handbook_chapters`, `modelled` |
| `lane` | `model/lifecycle.yaml` | `id`, `name`, `role` (a role in WP-M-02 §3.1), `plan` (the plan that governs the lane) |
| `activity` | [`model/governance.yaml`](model/governance.yaml), [`model/concept.yaml`](model/concept.yaml), [`model/design.yaml`](model/design.yaml), [`model/development.yaml`](model/development.yaml), [`model/integration.yaml`](model/integration.yaml), [`model/release.yaml`](model/release.yaml), [`model/operation.yaml`](model/operation.yaml) | `id` (`GOV-nn` governance, `CON-nn` concept, `DES-nn` system design, `DEV-nn` HW/SW development, `INT-nn` integration and verification, `REL-nn` validation and release, `OPS-nn` operation), `phase`, `lane`, `name`, `produces`, `inputs`, `handbook_wp`; optional `updates` |
| `review` | same files as the phase's activities | `id` (the WP-M-06 measure; `<measure>@<gate>` when WP-M-06 plans it at several gates, e.g. `CR-06@G2`), `phase`, `name`, `covers`, `independence`; optional `record_wp` when the measure's record is itself a work product (FSA-F → WP-K-04), which then counts as performed once approved |
| `interface` | [`model/interfaces.yaml`](model/interfaces.yaml) | `id` (`IX-nn`), `phase`, `between` (two work products), `pattern`, `topic`, `anchors`, `status`, `open_item`, `due` |
| `feedback` | `model/operation.yaml` | `id` (`FB-nn`), `phase`, `source` (the work product that raises the finding), `targets` (work products of earlier phases it re-opens), `finding`, `anchors` |

Rules the records follow:

- **Living work products are produced once and updated later.** A work product whose WP-M-00 gate is a range (`G1→G5`) is produced by one activity in its first phase. Activities of later phases in the range list it under `updates`. Inputs and map edges in a phase use the latest activity of that phase that produces or updates the work product.
- **Independent assessments are activities in the confirmation lane** when they produce a work product of their own (the FSA report WP-K-04, the cybersecurity assessment WP-K-05). Readiness counts such an activity as checking its inputs.
- **Activity IDs follow execution order.** An activity's inputs from the same phase come from activities with lower IDs. Work that goes back and forth between disciplines is an interface, not an input, so the input graph has no cycles.
- **Interfaces are anchored.** Each anchor `WP-x-nn:text` names text that occurs verbatim in that work product. If the documents stop making the link, the check fails.
- **Interface status** is `documented` (both documents refer to each other; nobody has reviewed the agreement yet) or `open` (a recorded open item still has to settle it, named in `open_item`). There is no "agreed" status yet. It will come from a recorded review, as in `case/`.
- **`handbook_wp`** maps an activity to the handbook's eight integrated work products (Ch. 13: WP-1 item definition, WP-2 unified risk assessment, WP-3 concept, WP-4 requirements specification, WP-6 V&V, WP-7 assurance case). It is informative. LionDriver keeps its own work-product structure.

## 4. Checks

`python3 assurance/process/tools/process_model.py --check` runs these checks. CI runs it in the `assurance` workflow.

| Check | Rule |
|---|---|
| P1 | Records parse; required fields present; list fields are lists; IDs unique |
| P2 | Every gate G0…G6 has a phase record and a WP-M-00 §2 entry; every lane's role exists in WP-M-02 §3.1 and its plan in WP-M-00 |
| P3 | Each activity's phase and lane exist; each produced work product is registered, has exactly one producing activity, is gated in the activity's phase and exists on disk; an updated work product is living and the phase lies within its gate range |
| P4 | In a modelled phase, every work product WP-M-00 gates there is produced by an activity |
| P5 | Each input is produced by an earlier activity of the same phase or gated at an earlier gate |
| P6 | The phase's confirmation measures equal the WP-M-06 §9 row for its gate, are defined in WP-M-06, and cover registered work products |
| P7 | Interfaces connect two work products produced by activities; anchors occur verbatim; `open_item` is set exactly when the status is `open`; an interface is not due before its own phase |
| P8 | The committed maps and gate skeletons equal what the model generates (`--check` only) |
| P9 | Feedback comes from a work product produced in its own phase, goes only to work products of earlier phases, and its anchors occur verbatim |

`tools/test_process_model.py` shows that the committed model passes and that each check rejects a broken copy.

## 5. Changing the model

1. Edit the records in `model/`. Do not edit `maps/`.
2. Run `python3 assurance/process/tools/process_model.py` to check the model and regenerate the maps.
3. Commit the records and the maps together.

A new or renamed work product goes into WP-M-00 first; the model then refers to it. Modelling another phase means adding its activities and reviews, then setting `modelled: true` on its phase record. P4 and P6 then require the phase to be complete.

## 6. What the model shows

These findings come from the generated maps. They are observations for the safety manager, not decisions.

### 6.0 Governance phase ([G0 map](maps/g0-governance.md))

1. **"Roles assigned" is part of the G0 exit criterion, and it is not met.** WP-M-02 still lists the verification reviewer, QA and the external functional safety assessor as TBD (WP-M-02 OI-1 and OI-3, both due at G0). Every later gate inherits these gaps: they appear in every readiness section from G1 to G6.
2. **The role records disagreed; resolved.** The SOTIF plan (WP-M-08) and the AI safety plan (WP-M-10) named the maintainer as SOTIF lead and AI safety lead, while WP-M-02 §3.1 listed both as TBD. The maintainer confirmed they hold both roles in an acting capacity. All three plans now record "Jherrod Thomas (acting); permanent holder TBD", the same form as the cybersecurity manager. The G0 cross-check keeps comparing the records and reports any new disagreement.
3. **One person holds almost every role.** Safety manager, project maintainer, configuration and change manager, cybersecurity manager, envelope software engineer, and (acting) SOTIF lead and AI safety lead. WP-M-02 OI-2 asks who approves what the safety manager authors. Until that is answered, independent checking rests on the two G0 confirmation measures and the external assessor, and the assessor is not engaged.
4. **Only the impact analysis and the safety plan are confirmed independently at G0** (CR-01, CR-03@G0). The SOTIF, cybersecurity and AI plans are not. WP-M-09 does require the assessor's agreement to each cybersecurity tailoring entry before G1, but WP-M-06 §9 plans no measure for it.
5. **The handbook's eight integrated work products stop at the plans.** None of the Chapter 13 work products covers governance, so `handbook_wp` is empty for G0. The handbook treats the plans in Chapter 4 only.
6. **The process model is itself a G0 work product.** GOV-21 produces WP-P-11 from the register, the safety plan and the confirmation plan, so this model can only be as current as those three documents.
7. **The plan-level interface is closed from public information.** IX-33: no request was sent to comma.ai. By the maintainer's decision, WP-M-10 OI-7 is answered from comma.ai's published statements, now recorded in WP-M-11 §3.5. The driving models learn from drives uploaded by openpilot users through a learned world model. No model card, dataset description or evaluation report is published. G0 and G1 now have no open interface. The AI argument's limits stand: no claim relies on training-data coverage, and the ODD comparison (IX-06) still cannot be made.

### 6.1 Concept phase ([G1 map](maps/g1-concept.md))


1. **The interface that blocked G1 is closed.** IX-02: the mapping from safety goals to cybersecurity goals had been written from the HARA only. It was checked against the FSC allocation and corrected: CSG-01 and CSG-02 now protect every safety goal, and the SoC-dependent warning goals SG-02 and SG-06 gained the SoC entry-path goals. WP-C-04 now points to the mapping. The check was made by the author of both documents, so its independent confirmation is CS-I1 at G1. IX-05 (SOTIF to AI) is closed too: the driver-monitoring targets were confirmed with an end-to-end alert time of ≤ 6 s (WP-C-08 OI-2). IX-06 remains open and is due at G2.
2. **Six G1 work products have no confirmation measure at G1:** WP-C-02, WP-C-07, WP-C-11, WP-V-07, WP-T-01, WP-K-01. They are reviewed only through verification review (WP-P-05). This is allowed. It matters most for WP-C-11 (AI safety requirements), whose independent review SR-04 is planned for G3.
3. **The independent lane has no one in it.** The SOTIF lead and AI/ML safety lead are held by the maintainer on an acting basis, so every work lane is staffed by the same person. The external functional safety assessor (D-06) is unassigned, and every G1 confirmation measure depends on the assessor.
4. **The SOTIF lane both feeds and consumes the HARA.** The ODD and misuse analysis (CON-02, CON-03) are HARA inputs; the SOTIF hazard and insufficiency analyses (CON-06…CON-08) depend on it. SOTIF and functional safety cannot run as sequential silos; the process has to interleave them.

### 6.2 System design phase ([G2 map](maps/g2-system-design.md))

1. **The critical path is one serial chain in one lane.** Functional safety carries 8 of the 12 activities. Timing, TSRs, architecture, FFI, DFA, then decomposition and FTA (DES-02 → DES-03 → DES-05 → DES-07 → DES-08 → DES-09/DES-10) run one after another. WP-M-02 assigns the safety manager and envelope engineer roles to the same person today.
2. **No AI-lane work product is gated at G2.** AI concerns reach system design only through the SOTIF V&V strategy (IX-13: validation targets for the AI performance values) and the FFI analysis (IX-14: ML outputs contained by the envelope). Whether PAS 8800 needs an AI architecture view at G2 is a planning decision for WP-M-10.
3. **Two open interfaces are due by G2:** IX-06 and IX-13, both SOTIF–AI. IX-13 needs the assessor's approval of the numeric validation targets (VT-01…VT-11), which now include the confirmed driver-monitoring targets of IX-05. IX-06 needs the training-data ODD, which comma.ai does not publish. These are the main cross-domain blockers for G2.
4. **Three G2 work products have no confirmation measure at G2:** WP-S-01, WP-S-06, WP-S-07. WP-S-07 (cybersecurity requirements and architecture) names assessor sampling per WP-M-09 §8 in its header. WP-M-06 plans no independent cybersecurity review between the G1 interim review (CS-I1) and the final assessment at G5.
5. **Safety and security meet in three places in the architecture:** overlapping boot and mode-lock requirements (IX-09), the BOOT0/NRST trust boundary that the FFI claim FFI-3 depends on (IX-10), and unauthenticated SoC messaging (IX-11). Each is one design decision seen from two standards, so the safety architecture and the security architecture cannot be reviewed separately.

### 6.3 Hardware and software development phase ([G3 map](maps/g3-hw-sw-development.md))

1. **Hardware design comes before hardware requirements.** The device is COTS, so its design (DEV-03, WP-H-02) is recovered from firmware and documentation before the hardware safety requirements refine the TSRs onto it (DEV-04). Several HWSRs stay open until the device schematic is obtained (WP-H-01 OI-3). The hardware lane's owner is TBD (likely external) and was needed by G2.
2. **Tool qualification is a shared dependency.** One joint activity (DEV-02, WP-P-07) feeds software unit verification, ML engineering and cybersecurity verification, and its open items sit on the lane boundaries. IX-18 is closed: the independent reference for testing the ML compiler is ONNX Runtime 1.24.1 on CPU (TL-23), the version the pinned tinygrad itself tests against, and the perturbation scripts are classified as LionDriver test software (TL-24). Neither is installed in a LionDriver environment yet, and the `ffmpeg` they rely on is unpinned (WP-P-07 OI-8). The security static-analysis tools are still open (WP-W-11 OI-1).
3. **One coding guideline serves safety and security; IX-17 closed.** The CERT C subset for security static analysis is now recorded in WP-W-01 §5.5: the seven rules WP-W-11 §3.1 names, each mapped to the cppcheck core checker or MISRA rule that covers it, or to review. Choosing it surfaced that the designated cppcheck 2.21.0 has no CERT addon, one of the two tools WP-W-11 offered. The `cert-*` checks of clang-tidy cover none of the seven rules, so they serve as an additional net. Implementing SAST-02 in CI and qualifying clang-tidy remain open (WP-W-01 OI-13).
4. **Ten of the 18 G3 work products get only verification review at G3:** hardware requirements and design, software requirements, architecture, units and unit verification, configuration data, cybersecurity implementation and proven-in-use. For WP-P-09 this is deliberate: CR-11 is not planned while no proven-in-use claim is made (tailoring T-06). For the others, WP-M-06 plans no confirmation measure, so their independent check rests on the verification reviewer that WP-P-05 requires. WP-M-02 still lists that role as TBD.
5. **Two open interfaces are due by G3:** IX-06 and IX-13, both overdue since G2.

### 6.4 Integration and verification phase ([G4 map](maps/g4-integration-and-verification.md))

1. **The phase cannot start: there is no test bench.** All seven G4 work products are specifications with no recorded result. Four of the seven activities (INT-01, INT-03, INT-04, INT-05) need the LionDriver HIL bench of decision D-04, which does not exist. The HIL bench owner is unassigned, although WP-M-02 needs that role by G3.
2. **One bench, due by G3 (IX-20, closed).** WP-W-08 planned its own bench for G4 while WP-H-06 planned it for G3. WP-W-08 §3 now uses the WP-H-06 §2 bench and lists only its additional software needs, and WP-W-08 OI-1 is due at G3. G3 is the date WP-M-03 already requires: phase P4 depends on "G3; HIL bench ready". Building the bench is still open (WP-H-06 OI-1, WP-W-08 OI-1, WP-M-03 task 5.1, WP-P-07 OI-2). The staged build plan (05-software/hil-bench, stages B1–B4) now states the same bench and the same G3 date. Finding 1 stands, and a late bench now slips G3.
3. **Test campaigns overlap without an agreed split.** Embedded-software qualification, bench system integration and the fault-injection campaign each cover faults on the same interfaces; WP-W-08 OI-5 asks for the split (IX-21). Malfunctions and SOTIF triggering conditions are already split cleanly between WP-V-05 and WP-V-03 (IX-22).
4. **G4 has no independent check of its results.** The only measure WP-M-06 plans at G4 is the process audit AUD-2. None of the seven test specifications or reports gets a confirmation measure before the final assessment at G5. Until then their independent check rests on the verification reviewer, still TBD.
5. **The integrated item is not tested against attacks at G4.** Security verification at G3 is implementation-level (WP-W-11). The G4 fault-injection campaign treats configuration tampering as a fault, not an attack. Penetration testing (WP-V-06) is gated at G5, so the first attack test of the integrated item happens at the release gate.
6. **Three open interfaces are due by G4:** IX-06 and IX-13 from earlier phases, plus IX-21. IX-20 has been closed.

### 6.5 Validation and release phase ([G5 map](maps/g5-validation-and-release.md))

1. **Release depends on parties nobody has engaged yet.** The final functional safety assessment (FSA-F, report WP-K-04) and the safety case review CR-12 need the external FuSa assessor (D-06). The cybersecurity assessment (WP-K-05) needs the external cybersecurity assessor. Penetration testing (WP-V-06) needs a tester: "no tester is engaged". The SOTIF and AI reviews (SR-03, SR-04) need an external reviewer with SOTIF or ML competence, who may be the FuSa assessor (WP-M-06 §7). None of them is engaged today.
2. **Four of the 14 G5 work products are still skeletons:** the SOTIF release argument (WP-K-02), both assessment reports (WP-K-04, WP-K-05) and the release record (WP-K-06). The other ten are drafts; none of the validation activities has been run.
3. **The three arguments meet once.** Safety validation, the SOTIF release recommendation and the cybersecurity case come together only in REL-10, where the safety case is completed (IX-24 links its cybersecurity branch to WP-K-03). The FSA and the release record then depend on that single step.
4. **The SOTIF release argument waits on evidence from other lanes.** It needs P(not controlled) from the controllability tests of the safety validation, but the evidence route is undecided (IX-25). It also needs the model evaluation report from ML engineering, which is missing (IX-26).
5. **Most of what was opened before G5 is still open.** IX-02, IX-05, IX-17, IX-18, IX-20 and IX-33 have been closed. Four open interfaces are due by G5: the three due by G4 plus IX-25. Any of them still open at G5 is a condition on the release.
6. **The operation documents get no confirmation measure:** installation (WP-O-01), operation and service (WP-O-02), user information and warnings (WP-O-03), and release management (WP-P-10). The user warnings are a SOTIF misuse measure (ISO 21448 §6, §13 in the register).

### 6.6 Operation phase ([G6 map](maps/g6-operation.md))

1. **Field monitoring is needed five gates before it is gated.** WP-O-04 applies "from the first LionDriver public-road drive (development phase, under WP-V-07)", and the road-test hold point WP-V-07 is a G1 work product. The register gates WP-O-04 at G6. Either the register entry or the hold point needs a field-monitoring slice gated at G1.
2. **The G6 exit criterion is "processes running", and none is.** WP-O-05 is "process defined; not running": no vulnerability intake (GAP-28), no SBOM or scanning, no upstream advisory watch, and no signed updates (GAP-26, IX-30).
3. **Operation has no independent check.** WP-M-06 plans no confirmation measure at G6, so neither field monitoring nor incident response is confirmed by anyone other than its authors.
4. **Every field finding re-opens a G1 work product.** All six feedback routes (FB-01…FB-06) end in the concept phase: HARA, item definition, SOTIF analyses, misuse analysis, AI requirements or the safety case. WP-M-06 §4 repeats a confirmation review when a confirmed work product changes in a safety-relevant way. So a single field finding can trigger I3 confirmation reviews again, and that needs the external assessor even after release.
5. **Five open interfaces are due by G6:** the four due by G5 plus IX-28, the shared event signatures between pre-release exploration and field monitoring.

## 7. Open items

| ID | Item | Owner | Gate |
|---|---|---|---|
| OI-1 | Closed: all phases G0–G6 are modelled | Safety manager | — |
| OI-2 | Add an "agreed" interface status set only through a recorded review, and decide whether cross-domain interfaces become requirement items (`IFR-nn`) in `trace/` | Safety manager | G2 |
| OI-3 | Closed: gate review skeletons for G0–G6 are generated in `10-safety-case/gates/skeletons/` | Safety manager | — |
| OI-4 | Derive pull-request checklists from the model: which activities and interfaces a change to a work product re-opens | Configuration and change manager | G2 |
