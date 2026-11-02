---
name: review-workbook
description: Work on LionDriver's analysis records and the review outputs generated from them. It covers the System FMEA, SW FMEA, DFMEA, PFMEA, FMEDA, DFA and FSC YAML under assurance/08-analyses/fmea (schema, IDs, ratings, actions, history), fmea_lint, and every derived output (figures, FMEA cards, review pages, reviewer .xlsx workbooks, FMEDA views and live worksheet, what-if page), the HARA/FSC/item checklist exports, the review-record input workbooks (hsi_to_xlsx, tsc_to_xlsx), and the workbook viewer page (tools/xlsx_viewer.py) with its sha fingerprint and republish. Use it whenever someone says "FMEA", "FMEDA", "PFMEA", "DFMEA", "System FMEA", "SW FMEA", "cause", "action priority", "AP H", "re-rate", "FMEA-MSR", "SPFM", "LFM", "HARA workbook", "FSC workbook", "spreadsheet for review", "xlsx", "workbook", "review cards", "workbook viewer", "live worksheet", "fmea_lint failed", "xlsx_viewer --check failed" or "fmeda_views --check failed", or changes anything those outputs are built from, even if nobody names a tool.
---

# Review workbook

**The YAML is the analysis of record. Every workbook, page, card and figure is generated from it, never edited by
hand, and CI fails when one is stale.** The reviewer reads the outputs, often on a phone (the workbook viewer and the
live FMEDA worksheet are claude.ai pages for that), so a change is finished only when every output is regenerated,
checked and, for the two pages, republished.

## Honesty rules (read before editing anything)

- AI work is **I0** (WP-M-02 §3.3). Record it as Claude in history and `team`; never as a reviewer.
- **Never fill reviewer cells.** The reviewer workbooks have "Reviewer decision", "Reviewer comment" and a "Review
  sign-off" block (reviewer, independence level, date, result). They stay empty for a human. The same holds for the
  checklist workbooks of review records `RR-*`: an AI pre-check is labelled I0, "not verification", and accepts
  nothing.
- **Ratings need evidence.** Do not lower S, O, D, F or M, raise a DC, or mark an action `completed` without a cited
  source (a test path that exists, a commit, a measurement). A predicted rating goes in `revised`, never in place of the
  current one. A completed action earns credit only at the next baseline's re-rating.
- **Never** lower an ASIL, change a safety-goal target or an FTTI, or edit `rating-tables.md` to clear a lint error
  or an AP H. Severity and hazard scope are the lead's (`decision-inbox` skill).
- `analyses/hara.yaml` and `analyses/fsc.yaml` are **withdrawn** (DQ-124 A): do not revise them. WP-C-03 with
  `hara_model.py`, and WP-C-04 with `fsc_model.py`, are of record; `hara-mapping.yaml` carries the old `HZ-`/`SG-0nn`
  IDs that FMEA rows still cite.

## Where things are

| What | Source of truth | Generated from it |
|---|---|---|
| FMEAs (`SFM-`, `SWF-`, `DFM-`, `PFM-`) | `assurance/08-analyses/fmea/analyses/{system-fmea,sw-fmea,dfmea,pfmea}.yaml`, `diagrams/<analysis>.yaml` | `figures/generated/`, `figures/cards/`, `exports/review/<analysis>.md` + `figures/`, `exports/review/<analysis>-review.xlsx` |
| FMEDA (`FMD-`) | `analyses/fmeda-sg001.yaml`, `fmeda-sg009.yaml` | `exports/review/fmeda-*.md`, `fmeda-*-review.xlsx`, `fmeda-views/*.svg`, live worksheet page, what-if page |
| DFA (and the withdrawn FSC) | `analyses/dfa.yaml` (`fsc.yaml`) | DFA figure 2-1, `dfa_gates.py`, `fig_a03_two_channel.py`; checklist exports |
| HARA, FSC workbooks | `assurance/02-concept/hara/hara_model.py`, `fsc/fsc_model.py` | `WP-C-03-hara-cartesian*.xlsx`, `WP-C-04-fsc-completeness.xlsx` (external builders) |
| Review-record inputs | WP-S-02…05, WP-A-03, WP-C-03/04 Markdown, `system-fmea.yaml`, `hara-mapping.yaml` | `RR-NNNN-{tsc,hsi}-input.xlsx` (`assurance/03-system/reviews/tools/`) |
| Workbook viewer | every tracked `assurance/**/*.xlsx` | <https://claude.ai/artifact/8raovSPWh354z9GvLzoXpx>, `tools/xlsx_viewer.sha256` |

Rules and tables: `fmea/rating-tables.md` (RT-3: S/O/D, AP table §5, FMEDA §6, MSR §7). Method and ID scheme:
`fmea/fmea-plan.md` §5. Schemas: `fmea/schema/*.schema.json`. `references/records.md` has the editing detail.

## Steps: change an analysis

1. **Read first.** The schema, the rating-table rows you will use, and the YAML around the entry. Check that the
   baseline you rate against is the current one in `fmea/baseline.yaml`.
2. **Edit the YAML** (`references/records.md`): new IDs continue the file's sequence and are never reused; severity of
   a mode = max of its effects; AP is what the RT table gives; AP H needs an action or a rationale; detection ≤ 8 names
   a `test` that exists. Bump `analysis.revision` and `updated`, and add the history line (header comment `# Rev …`
   for the FMEAs, `analysis.history` for FMEDA and DFA), saying what changed and why, author Claude.
3. **Lint.** `python3 tools/safety/fmea_lint.py --report` must end `0 error(s)`. Read new warnings; about 93 are
   standing (FTA map single points, unbacked events). Fix the data, never the linter's rule.
4. **See what is stale before regenerating**: run the `--check` list below. Each names the files it would rewrite.
   Note them: that is your list of real changes.
5. **Regenerate everything in one go** (`references/regenerate.md`, about 25 s). The workbook writers
   (`fmea_review_xlsx.py`, `export_fmeda_xlsx.py --all`) rewrite **every** workbook, and a workbook whose content did
   not change still differs in bytes (the `docProps/core.xml` modified time). **Restore those** with
   `git checkout -- <file>`; commit only the workbooks step 4 named.
6. **Republish the pages** a workbook or FMEDA change touches (`references/pages.md`): the workbook viewer when any
   tracked `.xlsx` changed, the live FMEDA worksheet and the what-if page when an FMEDA file changed.
7. **Re-run every check and test** (below) and look at the outputs (below). Commit sources, outputs and `.sha256`
   files together, with the analysis revision in the message.

## The checks (all verified to run here; CI runs them in `.github/workflows/assurance.yaml`, job `checks`)

```bash
python3 tools/safety/fmea_lint.py --report
python3 -m unittest discover -s tools/safety -p 'test_fmea_lint.py'
python3 tools/safety/fmea_diagrams.py --check   && python3 tools/safety/test_fmea_diagrams.py
python3 tools/safety/fmea_cards.py --check      && python3 tools/safety/test_fmea_cards.py
python3 tools/safety/fmea_review_xlsx.py --check && python3 tools/safety/test_fmea_review_xlsx.py
python3 tools/safety/fmea_review_md.py --check  && python3 tools/safety/test_fmea_review_md.py
python3 tools/safety/fmeda_review_md.py --check
python3 tools/safety/export_fmeda_xlsx.py --check
python3 tools/safety/fmeda_views.py --check     && python3 tools/safety/test_fmeda_views.py
python3 tools/xlsx_viewer.py --check            && python3 tools/test_xlsx_viewer.py
python3 assurance/02-concept/hara/hara_model.py --check
python3 assurance/02-concept/fsc/fsc_model.py --check
python3 tools/safety/gen_vehicle_catalog.py --check
```

They sit in the steps "FMEA, FMEDA and DFA figures…", "FMEA data lint…", "FMEA review pages for GitHub…", "Workbook
viewer page rebuilt…", "HARA model consistency" and "FSC completeness". Figures of other areas read the same YAML
(`fta_fmea_figures.py`, `dfa_gates.py`, `fig_a03_two_channel.py`, `fig_c01_interfaces.py`, `vehicle_register.py`):
`grep -rl "<file stem>" --include=*.py assurance tools` and run their `--check` too. `safety.yaml` checks none of
these outputs: it runs the firmware safety tests, mutation and MISRA jobs that the FMEA detection ratings cite as
evidence. Renaming or dropping one of those jobs or tests breaks a cited `test:` or `ref:`, so lint and re-rate.
Workflow files are SR-T (`assurance/07-supporting/safety-relevant-paths.txt`): edits go the WP-P-02 route.

## Look at the outputs

- **Workbooks:** open the viewer page you built (step 6) or dump rows with openpyxl (`references/regenerate.md`).
  Check that the changed row shows, AP chips and counts match the lint report, and reviewer cells are still empty.
- **Review pages:** read `exports/review/<analysis>.md` and the summary table in `exports/review/README.md`.
- **SVGs** (cards, fmeda-views, figures): render with the assurance-figure skill's previewer and Read the PNGs at
  full and 390 px width:
  `node .claude/skills/assurance-figure/scripts/preview.mjs <scratchpad>/png <file>.svg --width 390`

## Do not

- Do not edit a generated `.xlsx`, `.md` or `.svg`; do not run the external builders' `recalc.py` on the FMEA
  workbooks (it restores their wrong AP rule).
- Do not commit a workbook whose only change is its timestamp, or a `.sha256` for a page you did not publish.
- Do not regenerate the input or checklist workbooks of an existing review record: they record what was reviewed.
- Do not say a page was published unless the Artifact tool returned success for that URL.
