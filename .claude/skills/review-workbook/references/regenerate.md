# Regenerating every derived output

All commands run from the repository root. Each writer is deterministic except for the workbook timestamp below. The
whole sequence takes about 25 seconds (LibreOffice recalculates the FMEDA workbooks).

## 1. Before: what is really stale

Run the checks of SKILL.md first, after the YAML edit and before writing anything. Each failing check names its stale
files, for example:

```
fmea_review_xlsx: stale, run tools/safety/fmea_review_xlsx.py: assurance/08-analyses/fmea/exports/review/pfmea-review.xlsx
stale: assurance/08-analyses/fmea/exports/review/pfmea.md
```

Write the names down. The workbook `--check`s compare cell content, not bytes, so this list is the set of workbooks
whose content changed.

## 2. Write everything

```bash
python3 tools/safety/fmea_lint.py --report                 # must end "0 error(s)"
python3 tools/safety/fmea_diagrams.py                      # figures/generated/*.svg + README.md, card versions
python3 tools/safety/fmea_cards.py                         # System FMEA failure-mode cards (figures/cards/)
python3 tools/safety/fmea_review_md.py                     # exports/review/<fmea>.md, figures/, README.md
python3 tools/safety/fmea_review_xlsx.py                   # exports/review/<fmea>-review.xlsx (all four)
python3 tools/safety/fmeda_review_md.py                    # exports/review/fmeda-*.md
python3 tools/safety/export_fmeda_xlsx.py --all            # exports/review/fmeda-*-review.xlsx (needs soffice)
python3 tools/safety/fmeda_views.py --html <scratchpad>/fmeda-worksheet.html   # fmeda-views/*.svg, page, sha
python3 tools/safety/fmeda_whatif.py --out <scratchpad>/fmeda-whatif.html      # only if an FMEDA file changed
```

Then regenerate the figures of other areas that read the changed file (`grep -rl "<file stem>" --include=*.py
assurance tools`; for example `assurance/08-analyses/figures/fta_fmea_figures.py`, `dfa/dfa_gates.py`,
`dfa/dfa_figures.py`, `figures/fig_a03_two_channel.py`) with their own write command, then their `--check`.

`fmeda_views.py --html` writes the page and rewrites `tools/safety/fmeda_views.sha256` (same bytes when the page is
unchanged); without `--html` it writes the SVGs only. Run it with `--html` only when you will republish (pages.md).

## 3. Restore the byte-only workbook changes

`fmea_review_xlsx.py` writes all four FMEA workbooks and `export_fmeda_xlsx.py --all` both FMEDA workbooks, every
time. A workbook whose content is unchanged still differs from the committed file: openpyxl stamps
`docProps/core.xml` `dcterms:modified` with the current time (verified 2026-11-02: that is the only part that
differs). `git diff` cannot show it (binary), so use the list from step 1:

```bash
git status --short -- assurance/08-analyses/fmea/exports/review/'*.xlsx'
git checkout -- assurance/08-analyses/fmea/exports/review/<unchanged>-review.xlsx   # every one not on the step-1 list
python3 tools/safety/fmea_review_xlsx.py --check && python3 tools/safety/export_fmeda_xlsx.py --check
```

Both checks must still pass after the restore. If one fails, that workbook did change: keep the regenerated file.
The Markdown and SVG writers produce identical bytes when nothing changed, so they need no restore.

## 4. The workbook viewer

Run `python3 tools/xlsx_viewer.py --check`. It reads the cached values of every **tracked** `assurance/**/*.xlsx`
(`git ls-files`), so a brand-new workbook counts only once `git add`ed. If it fails, a workbook or the viewer changed:
rebuild and republish (pages.md). A timestamp-only workbook does not change the fingerprint, so restoring those
first avoids a needless republish.

## 5. Look

Dump a sheet to check a row without opening Excel:

```bash
python3 -c "import openpyxl,sys; wb=openpyxl.load_workbook(sys.argv[1], data_only=True); ws=wb[sys.argv[2]]; [print(r) for r in ws.iter_rows(min_row=1, max_row=12, values_only=True)]" \
  assurance/08-analyses/fmea/exports/review/pfmea-review.xlsx Worksheet
```

`wb.sheetnames` lists the sheets (FMEA workbooks: Cover, Worksheet, Actions, Structure, and MSR for the System FMEA
and DFMEA; FMEDA workbooks use the fmeda-builder tab names, `06_FMEDA_Worksheet`, `10_Metrics_Dashboard` and so on).
The worksheet's first row is the AIAG-VDA step band, the second the column headers. Check the changed row, the AP colour, the Cover counts against `fmea_lint.py --report`, and that the
reviewer columns and the sign-off block are still empty.
