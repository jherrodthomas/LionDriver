# What the model copies, and from where

The model reads every table by its **section heading text** (for example `3.1 Approach` in WP-S-08). Renaming or
renumbering one of these headings in a work product breaks the generator or the check that reads it; change the
heading string in the tool in the same commit. Column headers are matched too.

## Generated files

| Model file | Generator | Read from | Check |
|---|---|---|---|
| `Requirements.sysml` | `gen_requirements.py` | SG, FSR, TSR from `assurance/trace/items` (goals, fsr, tsr; FSR and TSR are synced from WP-C-04 §5, WP-S-02 §3-§9 and WP-S-06 by `trace/tools/sync_requirements.py`); SYS from WP-S-01 §2-§9; CSR from WP-S-07 §4; parent links as `#derivation` | R1 |
| `Satisfaction.sysml` | `gen_requirements.py` | `allocated_to` of the trace data (resolved as in M8), WP-S-01 §10.1, the Alloc column of WP-S-07 §4 (FW to E-03, SoC to E-01; ENV, USR, EXT, OPS give no relationship) | R1, R2 |
| `Verification.sysml` | `gen_requirements.py` | every Markdown table under `assurance/` whose first header cell is `ID` and whose rows are `VS-…` (test specifications), ranges expanded; `maps/` and `models/` are skipped | R1, R3 |
| `Needs.sysml` | `gen_requirements.py` | WP-S-01 §1.2 stakeholders and actors, §1.3 needs, §1.4 use cases | R1, N1-N3 |
| `StateRecords.sysml` | `gen_behaviour.py` | `assurance/05-software/state-machines/*.yaml` (the WP-W-05 §5 records) | B1, B2 |
| `Sequences.sysml` | `gen_behaviour.py` | WP-S-03 §4.1, Table 4-1 and its lifelines | B1-B3 |
| `Lifecycle.sysml` | `gen_behaviour.py` | WP-S-06 §3, parsed by `assurance/03-system/figures/fig_s06_lifecycle.py`; the phase order is `PHASE_FLOW` in the generator | B1, B4 |
| `Timing.sysml` | `gen_timing_hsi.py` | WP-S-04 §3.7 budgets, §4 code-derived times T-nn, §5 fault reaction times | H1, H2, H6 |
| `Signals.sysml` | `gen_timing_hsi.py` | WP-S-05 §11.1-§11.3 signals, §11.4 responsibilities, §2 HW resources | H1, H3-H5 |

## Hand-written files and the tables they must match

| Model file | Must match | Check |
|---|---|---|
| `Architecture.sysml` | WP-S-03 §3.1 elements and integrity; §3.3 interfaces (`@InterfaceId`); §9 cereal services; WP-W-03 §3.1 firmware catalogue (`@Catalogue`, `@Unit`) and §4.1 host components; a `@FfiClaim` naming the WP-S-03 §7 claims on any QM to ASIL connection inside the item (M7 requires one; it does not compare it with §7) | M1-M4, M6, M7, T1 |
| `Mechanisms.sysml` | WP-S-03 §6 safety mechanism catalogue: same set, performers, TSRs and every column | M5, T1 |
| `Functions.sysml` | WP-C-01 §2.1 functions F-01 to F-09: IDs and titles; every step performed by an element | M9 |
| `Security.sysml` | WP-S-07 §3.1 zones and §3.2 trust boundaries, cell by cell; every element inside the item in a zone | M10 |
| `Integration.sysml` | WP-S-08 §3.1 steps I-1 to I-4: `elements`, `interfaces`, `stimulus`, `purpose` equal the cells exactly (Markdown included); `integrates` and `exercises` name model elements and IF-nn; every E-0n integrated by some step | M11 |
| `Behaviour.sysml` | WP-C-01 §4 operating modes: each row a state of SM-SYS (description and actuation cell by cell) or a listed configuration; record states and transitions it names exist in `StateRecords.sysml` | M12 |
| `LionDriverLibrary.sysml` | Definitions and metadata only; change it when a new attribute or kind is needed | via the reader and pilot |
| `Views.sysml`, `views/layout.toml` | The views (see views.md) | render_views, test_sysml |

## What to run after editing a source

| You edited | Run (from `assurance/models/sysml` unless stated) |
|---|---|
| WP-C-04 §5, WP-S-02, WP-S-06 TSR tables | `sync_requirements.py` (repository root), `gen_requirements.py`, `gen_behaviour.py` if WP-S-06 §3 changed, then the common tail |
| `trace/items/*.yaml` allocations or parents | `gen_requirements.py`, common tail (M8 report changes) |
| WP-S-01 | `gen_requirements.py`, common tail; N1-N3 and R2 may ask for model edits (a new SYS must refine a need and be satisfied) |
| WP-S-07 §4 | `gen_requirements.py`, common tail. §3.1 or §3.2: edit `Security.sysml` |
| A test specification (`VS-…` rows) | `gen_requirements.py`, common tail |
| A state-machine record | `gen_behaviour.py`, common tail; M12 may need `Behaviour.sysml` edits |
| WP-S-03 §4.1 | `gen_behaviour.py`, common tail |
| WP-S-03 §3.1, §3.3, §6, §9 or WP-W-03 §3.1, §4.1 | edit `Architecture.sysml` or `Mechanisms.sysml`, then `check_model.py`, `gen_tables.py`, common tail |
| WP-S-04 §3.7-§5, WP-S-05 §2 or §11 | `gen_timing_hsi.py`, common tail, then the AUTOSAR generator |
| WP-S-08 §3.1 | edit `Integration.sysml`, common tail |
| WP-C-01 §2.1 or §4 | edit `Functions.sysml` or `Behaviour.sysml`, common tail |

**Common tail:** `check_model.py --write`, `check_model.py`, `gen_tables.py`, `render_views.py`,
`explorer.py --fragment <scratchpad>/sysml-explorer.html` and republish, `test_sysml.py`, `tools/pilot/validate.sh`,
then from `assurance/models/autosar` `gen_arxml.py` and its checks, and the downstream figure checks
(`fig_s01_requirements.py --check`, `fig_s00_se.py --check`, `trace_figures.py --check`,
`assurance/05-software/diagrams/make_diagrams.py --check`).
