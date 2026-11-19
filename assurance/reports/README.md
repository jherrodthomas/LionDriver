# Generated reports (LaTeX)

The work products stay the records: Markdown documents and YAML data, checked in CI. This folder renders them as
LaTeX reports, the format academic and assessment readers expect, without making a second copy anyone edits.

- **Generated, never edited.** [`build_reports.py`](build_reports.py) writes each report's `.tex` from its record.
  The `.tex` is committed, and `--check` in CI fails when a record has changed and the report was not regenerated.
- **Numbers are macros.** Every number a report's prose uses is a `\newcommand` in the report's `numbers.tex`,
  written from the record. The text says `\FsrCount{} functional safety requirements`, never a typed number.
- **Tables and figures come from the record.** Tables are read column by column from the work product, and the
  build fails if a column is renamed or a section is missing. Figures are the committed SVGs, converted to PDF at
  build time.
- **Abbreviations and references are shared.** The abbreviations appendix is written from the project's single terms
  list (`trace/tools/terms.py`), with only the terms the report uses. The bibliography is written from
  [`references.yaml`](references.yaml), and the build fails on a citation that is not there.
- **The PDF is a build artifact.** CI builds it with TeX Live 2023 from the Ubuntu 24.04 archive (WP-P-07 TL-66) and
  keeps it as the `latex-reports` artifact of the assurance workflow. It is not committed. The build is reproducible:
  the same sources give the same bytes.

| Report | Record | Generated sources |
|---|---|---|
| Functional Safety Concept | [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) | [`fsc/fsc.tex`](fsc/fsc.tex), [`fsc/numbers.tex`](fsc/numbers.tex) |
| Harness Box Component FMEDA | [WP-H-03 §6.5](../04-hardware/fmeda/README.md), from [`harness-box-parts.yaml`](../04-hardware/fmeda/harness-box-parts.yaml) through the checks of `harness_box_fmeda.py` | [`harness-box/harness-box.tex`](harness-box/harness-box.tex), [`harness-box/numbers.tex`](harness-box/numbers.tex) |

```bash
python3 assurance/reports/build_reports.py               # regenerate the .tex after a record changes
python3 assurance/reports/build_reports.py --check       # what CI runs
python3 assurance/reports/build_reports.py --pdf build/reports   # build the PDFs locally (needs pdflatex, rsvg-convert)
```

The shared style is [`latex/liondriver-report.sty`](latex/liondriver-report.sty). To add a report, add a function to
`REPORTS` in the generator that reads its record, returns its `.tex`, `numbers.tex` and figures, and fails when the
record changes shape; then add tests for it in [`test_build_reports.py`](test_build_reports.py).

The reports carry the status of their records: today drafts, AI-assisted (independence I0) and not reviewed.
