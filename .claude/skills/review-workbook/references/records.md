# Editing the analysis records

Read with: `assurance/08-analyses/fmea/fmea-plan.md` §5 (layout, IDs, what the linter checks),
`rating-tables.md` (RT-3), `msr-plan.md` (FMEA-MSR), the schema in `fmea/schema/`. When this page and those
records disagree, the records win; fix this page.

## IDs

| Analysis | Prefix | Structure | Function | Failure mode | Cause | Action |
|---|---|---|---|---|---|---|
| System FMEA | `SFM` | `SFM-SE-###` | `SFM-FN-###` | `SFM-###` | `SFM-###.C#` | `SFM-ACT-###` |
| DFMEA | `DFM` | `DFM-SE-###` | `DFM-FN-###` | `DFM-###` | `DFM-###.C#` | `DFM-ACT-###` |
| SW FMEA | `SWF` | `SWF-SE-###` | `SWF-FN-###` | `SWF-###` | `SWF-###.C#` | `SWF-ACT-###` |
| PFMEA | `PFM` | `PFM-SE-###` | `PFM-FN-###` | `PFM-###` | `PFM-###.C#` | `PFM-ACT-###` |
| FMEDA | `FMD-…` | | | unique only within its file | | |

- FMEA IDs are unique across all four files. A new entry takes the next free number; a removed one is never reused
  (gaps are normal: "SFM-ACT-001..011 (no 004)"). Other records cite these IDs (FTA map `fta-fmea-map.yaml`,
  `hara-mapping.yaml`, WP-A-04, WP-H-03, the decision register), so renaming one means `grep -rn "<ID>" assurance`
  and updating every citation in the same change.
- An `end` effect cites a second-set hazard `HZ-0nn` (and goals `SG-0nn`); `hara-mapping.yaml` maps each onto WP-C-03
  (`H-0n`, `HE-0n.m`, `SG-0n`) and the linter checks both ways. A new hazard link needs a mapped ID; do not invent one,
  and a hazard WP-C-03 lacks is a question for the lead.

## A failure mode and its causes (FMEA)

- `effects`: `local`, `next_higher`, `end`; an `end` effect linked to a `hazard` is severity 10 (RT §1.1). The mode's
  `severity` is the maximum of its effects.
- Each cause: `description`, `prevention_controls`, `detection_controls` (each `{description, ref}` or `{…, test}`),
  `occurrence`, `detection`, `ap`, and optional `element`, `linked_failure_mode`, `actions`, `rationale`, `previous`,
  `msr` or `msr_exempt`.
- **AP** is looked up in the RT §5 table from S, O, D (`fmea_lint.compute_ap`); the stored `ap` must equal it. AP H
  needs an action or a `rationale`.
- **Detection ≤ 8** must name a `test:` path that exists (a warning only inside an uninitialised submodule). State in
  the control description whether the test runs in CI and whether it is proven (mutation, fault injection).
- **Re-rating at a new baseline:** move the old O/D/AP into `previous` (with the baseline), write the new values, and
  say in the history line which evidence moved it. A System FMEA cause with `linked_failure_mode` inherits that row's
  rating; re-rate the lower-level analysis first (the linter warns when they drift).
- **FMEA-MSR** (`msr:` on System FMEA and DFMEA causes in scope): `mechanisms`, `diagnostic`, `system_response`,
  `effect_after_response`, `severity_after`, `frequency` (= the cause's O), `monitoring`, `ap`, `timing`
  (`ftti_ref`, `fdti_ms`, `frti_ms`, `basis: code_derived | measured`), `evidence`, `actions`. M 1–4 needs measured
  timing within the FTTI (DQ-206 A); simulation results are cross-checks with no rating credit (msr-plan §4.2).

## Actions

`{id, kind: prevention | detection | design_change | monitoring, description, owner, due, status, evidence, revised}`.
`status` is `open`, `decision_pending`, `in_progress`, `completed` or `not_implemented`. `completed` needs `evidence`
(PR, commit, test). `revised` holds the *predicted* ratings after the action; they are not the current rating. A
`decision_pending` action points at the register question (DQ-…) by name in the description.

## Header and history

- `analysis.revision` (string), `updated` (date), `baseline` (from `fmea/baseline.yaml`), `rating_tables` (RT-n),
  `status`. Keep `draft`; `in_review` only when a human review is actually scheduled; `released` is a human approval,
  never set by Claude. `team` lists Claude as "drafting assistance; content requires human review".
- History: the four FMEAs keep it in the header comment block (`# Rev 0.nn (date, …): what changed, why, rating
  changes or "no rating changes"`); FMEDA, DFA and FSC keep it in `analysis.history` (`{revision, date, author,
  change}`). `export_fmea_xlsx.py` and the review pages show it, so write it for a reviewer.

## FMEDA

Per component: `id`, `safety_related`, `failure_rate_fit` with its rate source, and `failure_modes` each with
`distribution` (summing to 1 per component), `violates_sg_directly`, `mpf_potential`, `safety_mechanism_spf` /
`dc_spf`, `safety_mechanism_lf` / `dc_lf`, and `per_goal` overrides where another goal classifies the row
differently. The classification rules are RT §6.1; DC claims need the §6.2 basis. The linter computes SPFM, LFM and
λSPF+λRF per goal against the WP-H-04 §4 targets (`fmea_lint.py --report` prints them). Try values first on the
what-if page; a value worth keeping goes into the YAML with its source.

## The other workbooks

| Workbook | How it is made | Committed? |
|---|---|---|
| `exports/review/<fmea>-review.xlsx` | `tools/safety/fmea_review_xlsx.py` (all four) | yes, CI-checked |
| `exports/review/fmeda-*-review.xlsx` | `tools/safety/export_fmeda_xlsx.py --all` (formulas, recalculated by LibreOffice `soffice`) | yes, CI-checked |
| Builder-layout FMEA workbooks | `export_fmea_xlsx.py {system,dfmea,sw} --generator …`, `export_pfmea_xlsx.py --generator …` | no (git-ignored `exports/`) |
| HARA / FSC / item checklist exports | `export_hara_xlsx.py`, `export_fsc_xlsx.py`, `export_item_xlsx.py [OUT.xlsx]` | no; for the checklist-reviewer skills |
| `WP-C-03-hara-cartesian*.xlsx` | `hara_model.py`, then hara-builder `generate_hara.py`, `hara_model.py --postprocess`, `recalc.py` (hara `README.md` "Regenerating") | yes; viewer-tracked |
| `WP-C-04-fsc-completeness.xlsx` | `fsc_model.py`, fsc-builder `generate_fsc.py`, `fsc_model.py --postprocess`, `recalc.py` (fsc `README.md`) | yes; viewer-tracked |
| `RR-NNNN-{tsc,hsi}-input.xlsx` | `python3 assurance/03-system/reviews/tools/{tsc,hsi}_to_xlsx.py assurance <OUT.xlsx>` | yes, frozen with its review record |

The builder scripts (hara-builder, fsc-builder, dfmea-builder, sw-fmea-builder, pfmea-builder) come from
`jherrodthomas/automotive-skills-suite` and are **not** in this repository. If they are not available, say so and stop
at the model and its `--check`; never patch a committed builder workbook by hand. Exports render the YAML as is; the
builders' and reviewers' heuristic ratings are never written back into the analyses.

On 2026-11-02 `hsi_to_xlsx.py` runs against the current documents, but `tsc_to_xlsx.py` stops with
`KeyError: 'Interface'` at line 140: the WP-S-05 HSI table it reads no longer has an `Interface` column. Fix the
converter's column mapping (copy, invent nothing) before the next TSC review record needs it.

A new review record gets new `RR-NNNN-*-input.xlsx` files written next to its `RR-NNNN.md`; the earlier records keep
theirs and their old viewer links (they record what was reviewed).
