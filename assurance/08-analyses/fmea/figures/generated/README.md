# FMEA, FMEDA and DFA figures

Generated from the YAML analyses in [`analyses/`](../../analyses/) by `tools/safety/fmea_diagrams.py`. The YAML is the analysis of record; edit it and run `python3 tools/safety/fmea_diagrams.py` (`--check` fails when a figure is stale). Figure numbers follow the sections of [fmea-plan.md](../../fmea-plan.md). This folder is owned by the generator: hand-drawn figures belong in `figures/`, one level up.

| Figure | Shows | Source | Files |
|---|---|---|---|
| 2-1 | DFA: dependent failure initiators × ASIL decompositions, measures, open items | `analyses/dfa.yaml` | [fig-2-1-dfa-initiators.svg](fig-2-1-dfa-initiators.svg) |
| 3-1 | System FMEA structure and function tree (steps 2–3) | `analyses/system-fmea.yaml` | [fig-3-1-sfm-structure.svg](fig-3-1-sfm-structure.svg) |
| 3-2 | System FMEA failure chains: element → function → failure mode → causes (steps 4–6) | `analyses/system-fmea.yaml` | [1](fig-3-2-sfm-failure-chains-1.svg), [2](fig-3-2-sfm-failure-chains-2.svg), [3](fig-3-2-sfm-failure-chains-3.svg), [4](fig-3-2-sfm-failure-chains-4.svg), [5](fig-3-2-sfm-failure-chains-5.svg), [6](fig-3-2-sfm-failure-chains-6.svg), [7](fig-3-2-sfm-failure-chains-7.svg), [8](fig-3-2-sfm-failure-chains-8.svg) |
| 3-3 | DFMEA structure and function tree (steps 2–3) | `analyses/dfmea.yaml` | [fig-3-3-dfm-structure.svg](fig-3-3-dfm-structure.svg) |
| 3-4 | DFMEA failure chains: element → function → failure mode → causes (steps 4–6) | `analyses/dfmea.yaml` | [1](fig-3-4-dfm-failure-chains-1.svg), [2](fig-3-4-dfm-failure-chains-2.svg), [3](fig-3-4-dfm-failure-chains-3.svg) |
| 3-5 | SW FMEA structure and function tree (steps 2–3) | `analyses/sw-fmea.yaml` | [fig-3-5-swf-structure.svg](fig-3-5-swf-structure.svg) |
| 3-6 | SW FMEA failure chains: element → function → failure mode → causes (steps 4–6) | `analyses/sw-fmea.yaml` | [1](fig-3-6-swf-failure-chains-1.svg), [2](fig-3-6-swf-failure-chains-2.svg), [3](fig-3-6-swf-failure-chains-3.svg), [4](fig-3-6-swf-failure-chains-4.svg), [5](fig-3-6-swf-failure-chains-5.svg), [6](fig-3-6-swf-failure-chains-6.svg), [7](fig-3-6-swf-failure-chains-7.svg), [8](fig-3-6-swf-failure-chains-8.svg), [9](fig-3-6-swf-failure-chains-9.svg), [10](fig-3-6-swf-failure-chains-10.svg), [11](fig-3-6-swf-failure-chains-11.svg), [12](fig-3-6-swf-failure-chains-12.svg), [13](fig-3-6-swf-failure-chains-13.svg) |
| 3-7 | SW FMEA: Action Priority as rated and as predicted by the planned actions (not achieved) | `analyses/sw-fmea.yaml` | [fig-3-7-swf-action-effect.svg](fig-3-7-swf-action-effect.svg) |
| 3-8 | PFMEA structure and function tree (steps 2–3) | `analyses/pfmea.yaml` | [fig-3-8-pfm-structure.svg](fig-3-8-pfm-structure.svg) |
| 3-9 | PFMEA failure chains: element → function → failure mode → causes (steps 4–6) | `analyses/pfmea.yaml` | [1](fig-3-9-pfm-failure-chains-1.svg), [2](fig-3-9-pfm-failure-chains-2.svg) |
| 3-10 | FMEDA SG-001: SPFM, LFM, λSPF+λRF against ASIL D (estimate, not verified) | `analyses/fmeda-sg001.yaml` | [fig-3-10-fmeda-sg001-metrics.svg](fig-3-10-fmeda-sg001-metrics.svg) |
| 3-11 | FMEDA SG-009: SPFM, LFM, λSPF+λRF against ASIL B (estimate, not verified) | `analyses/fmeda-sg009.yaml` | [fig-3-11-fmeda-sg009-metrics.svg](fig-3-11-fmeda-sg009-metrics.svg) |
| 3-12 | SW FMEA: occurrence × detection per element, with the moves predicted by planned actions | `analyses/sw-fmea.yaml` | [fig-3-12-swf-od-elements.svg](fig-3-12-swf-od-elements.svg) |
| 3-13 | SW FMEA: what each detection rating rests on (test run in CI, hardware only, not run, none) | `analyses/sw-fmea.yaml, .github/workflows/, tools/test_runner.py` | [fig-3-13-swf-detection-evidence.svg](fig-3-13-swf-detection-evidence.svg) |
| 3-14 | SW FMEA: occurrence, detection and AP of the re-rated causes, previous baseline against this one | `analyses/sw-fmea.yaml` | [fig-3-14-swf-baseline-delta.svg](fig-3-14-swf-baseline-delta.svg) |
| 3-15 | SW FMEA: reaction time of the timed safety mechanisms by defence layer (code-derived, not measured) | `analyses/sw-fmea.yaml` | [fig-3-15-swf-reaction-layers.svg](fig-3-15-swf-reaction-layers.svg) |
| 3-16 | SW FMEA: per element, the causes rated here and the performance part left to SOTIF | `analyses/sw-fmea.yaml` | [fig-3-16-swf-sotif-boundary.svg](fig-3-16-swf-sotif-boundary.svg) |
| 4-1 | Action Priority overview of the four FMEAs | `analyses/*fmea.yaml` | [fig-4-1-action-priority-overview.svg](fig-4-1-action-priority-overview.svg) |
| 4-2 | FMEA-MSR overview of the System FMEA and DFMEA (handbook MSR AP table, RT-3) | `analyses/system-fmea.yaml, dfmea.yaml` | [fig-4-2-msr-overview.svg](fig-4-2-msr-overview.svg) |

Conventions: Action Priority H / M / L in red / amber / teal as rated in the YAML; predicted ratings of open actions are hatched and dashed and never shown as achieved. FMEDA metrics are drawn from generic failure-rate estimates and are marked as not verified; a target met on the estimate is amber, never green. In the DFA, green marks only measures recorded as `existing` (verified); `existing_unverified` is amber.

Large failure-chain trees are split into sheets; an element or function repeated on a later sheet is tagged “continued”.
