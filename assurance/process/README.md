# WP-P-11 Integrated Process Model and Process Maps

| Field | Value |
|---|---|
| Work product | WP-P-11 Integrated process model (machine-readable) and generated process maps |
| Standard reference | ISO 26262-2:2018 §6 (safety lifecycle, planning of activities); ISO 21448:2022 §4; ISO/SAE 21434:2021 §6 (cybersecurity activities and their tailoring); ISO/PAS 8800:2024 (AI safety lifecycle); ASPICE 4.0 MAN.3 (project lifecycle definition). Informative: Integrated Automotive Standards Handbook (ISH-2026-001) §3.3–3.4, Ch. 5, Ch. 13 |
| Version | 0.1 |
| Status | Draft (pilot: concept phase G1 only) |
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
| [maps/lifecycle.md](maps/lifecycle.md) | L0: the seven phases G0…G6, their exit criteria and the handbook chapter each one corresponds to |
| [maps/g1-concept.md](maps/g1-concept.md) | L1 for the concept phase: swimlane map, interface map, activity table with clauses, clause coverage per standard, G1 readiness |

L2 (how to perform an activity) remains the procedures and plans the activities point to; it is not modelled here.

## 2. Single source of truth

The model holds only what no other document holds: the activities, their lanes, their inputs, the interfaces and the handbook mapping. Everything else is read at generation time:

| Fact | Read from |
|---|---|
| Gate names and exit criteria | WP-M-00 §2 |
| Clause references, ASPICE process, gate and status of each work product | WP-M-00 §3 (the row of each produced work product) |
| Who holds each lane's role, and by which gate | WP-M-02 §3.1 |
| Which confirmation measures a gate needs | WP-M-06 §9 |
| Whether a confirmation measure has been performed | Existence of `10-safety-case/confirmation/<id>.md` (WP-M-06 §10) |

A change to the register, the safety plan or the confirmation plan therefore shows up in the maps on the next run, and `--check` fails in CI until the maps are regenerated.

## 3. Record format

Records use the same flat YAML subset as [`case/`](../case/README.md): a top-level list of mappings with scalar or flow-list values. Flow-list items cannot contain commas. One record per item, with a `kind`:

| Kind | File | Fields |
|---|---|---|
| `phase` | [`model/lifecycle.yaml`](model/lifecycle.yaml) | `id` (gate G0…G6), `handbook_chapters`, `modelled` |
| `lane` | `model/lifecycle.yaml` | `id`, `name`, `role` (a role in WP-M-02 §3.1), `plan` (the plan that governs the lane) |
| `activity` | [`model/concept.yaml`](model/concept.yaml) | `id` (`CON-nn` in the concept phase), `phase`, `lane`, `name`, `produces`, `inputs`, `handbook_wp` |
| `review` | `model/concept.yaml` | `id` (as in WP-M-06), `phase`, `name`, `covers`, `independence` |
| `interface` | [`model/interfaces.yaml`](model/interfaces.yaml) | `id` (`IX-nn`), `phase`, `between` (two work products), `pattern`, `topic`, `anchors`, `status`, `open_item`, `due` |

Rules the records follow:

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
| P3 | Each activity's phase and lane exist; each produced work product is registered, has exactly one producing activity, is gated in the activity's phase and exists on disk |
| P4 | In a modelled phase, every work product WP-M-00 gates there is produced by an activity |
| P5 | Each input is produced by an earlier activity of the same phase or gated at an earlier gate |
| P6 | The phase's confirmation measures equal the WP-M-06 §9 row for its gate, are defined in WP-M-06, and cover registered work products |
| P7 | Interfaces connect two work products produced by activities; anchors occur verbatim; `open_item` is set exactly when the status is `open` |
| P8 | The committed maps equal what the model generates (`--check` only) |

`tools/test_process_model.py` shows that the committed model passes and that each check rejects a broken copy.

## 5. Changing the model

1. Edit the records in `model/`. Do not edit `maps/`.
2. Run `python3 assurance/process/tools/process_model.py` to check the model and regenerate the maps.
3. Commit the records and the maps together.

A new or renamed work product goes into WP-M-00 first; the model then refers to it. Modelling another phase means adding its activities and reviews, then setting `modelled: true` on its phase record. P4 and P6 then require the phase to be complete.

## 6. What the concept pilot shows

These findings come from the generated [G1 map](maps/g1-concept.md). They are observations for the safety manager, not decisions:

1. **One open interface blocks G1.** IX-02: the mapping from safety goals to cybersecurity goals was written from the HARA and has not been checked against the FSC (WP-C-10 OI-6). The other two open interfaces (IX-05 and IX-06, both SOTIF to AI) are due at G2.
2. **Six G1 work products have no confirmation measure at G1:** WP-C-02, WP-C-07, WP-C-11, WP-V-07, WP-T-01, WP-K-01. They are reviewed only through verification review (WP-P-05). This is allowed. It matters most for WP-C-11 (AI safety requirements), whose independent review SR-04 is planned for G3.
3. **Three of the five lane roles are unassigned:** SOTIF lead, AI/ML safety lead, and the external functional safety assessor (D-06). WP-M-02 needs all three by G1, and every G1 confirmation measure depends on the assessor.
4. **The SOTIF lane both feeds and consumes the HARA.** The ODD and misuse analysis (CON-02, CON-03) are HARA inputs; the SOTIF hazard and insufficiency analyses (CON-06…CON-08) depend on it. SOTIF and functional safety cannot run as sequential silos; the process has to interleave them.

## 7. Open items

| ID | Item | Owner | Gate |
|---|---|---|---|
| OI-1 | Model the remaining phases, starting with G2 system design (handbook Ch. 6) | Safety manager | G2 |
| OI-2 | Add an "agreed" interface status set only through a recorded review, and decide whether cross-domain interfaces become requirement items (`IFR-nn`) in `trace/` | Safety manager | G2 |
| OI-3 | Generate the G1 gate-record skeleton (`10-safety-case/gates/`) from §5 of the G1 map | Safety manager | G1 |
| OI-4 | Derive pull-request checklists from the model: which activities and interfaces a change to a work product re-opens | Configuration and change manager | G2 |
