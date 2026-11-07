# The published pages

Three private claude.ai pages show the workbooks and the FMEDA to the lead and reviewers on a phone. Each is a
self-contained HTML file built from the repository; the published copy has to follow the records.

| Page | Built by | URL constant (and other places it is written) | Fingerprint | CI |
|---|---|---|---|---|
| Workbook viewer: every tracked `assurance/**/*.xlsx` | `python3 tools/xlsx_viewer.py --out <scratchpad>/workbook-viewer.html` | `VIEWER_URL` in `tools/xlsx_viewer.py` = <https://claude.ai/artifact/QB1X8yPHBFitzEtAkB3PjT>; linked from `assurance/02-concept/hara/README.md` and `fsc/README.md` | `tools/xlsx_viewer.sha256` | `xlsx_viewer.py --check`, `tools/test_xlsx_viewer.py` |
| Live FMEDA worksheet (template `tools/safety/fmeda_views_page.html`) | `python3 tools/safety/fmeda_views.py --html <scratchpad>/fmeda-worksheet.html` | `WORKSHEET_URL` in `fmeda_views.py` and `WORKSHEET` in `fmeda_review_md.py` = <https://claude.ai/artifact/PCbGoJH1mrjZGDmEzegu7N>; linked from the generated `exports/review/fmeda-*.md` | `tools/safety/fmeda_views.sha256` | `fmeda_views.py --check`, `test_fmeda_views.py` |
| FMEDA what-if | `python3 tools/safety/fmeda_whatif.py --out <scratchpad>/fmeda-whatif.html` | `WHAT_IF` in `fmeda_review_md.py` = <https://claude.ai/artifact/6btZjojvGtcyZdYrhzsR8Z> (also in `fmeda_whatif.py`'s docstring) | none | none: republish by hand when an FMEDA file changes |

A `.sha256` file holds `<sha256 of the page as last built>  published at <URL>`. `--check` rebuilds the page in
memory and fails when the hash differs: a workbook, an FMEDA file, the tool or the template changed and the page
was not rebuilt. Only `--out` / `--html` rewrite the fingerprint.

## When to republish

- **Viewer:** any tracked `.xlsx` under `assurance/` added, removed or changed in content (FMEA and FMEDA review
  workbooks, HARA and FSC workbooks, review-record and audit workbooks), or a change to `xlsx_viewer.py`. A new
  workbook is named from its file name; add it to `TITLES` in the tool only when that name does not read well.
- **Worksheet:** any `analyses/fmeda-*.yaml` change that alters the page, or a change to `fmeda_views.py` or its
  template.
- **What-if:** any `analyses/fmeda-*.yaml` change (it embeds a snapshot).

## How

1. Build the page to the scratchpad with the command above (this rewrites the fingerprint).
2. Publish it with the Artifact tool **to the same URL**: `file_path` = the built file, `url` = the URL constant,
   no `capabilities` (keep what the page has), no `icon`. If this conversation has not published or read that
   artifact yet, `read` it first (a publish without that is refused and hands back the live version: publish your
   rebuilt file over it, not the old content).
3. Only after the tool returns success: run the page's `--check` and commit the `.sha256` with the change. Say in the
   final message which page was republished, with its link.

## If the publish fails

- **Never claim it published.** Do not commit a fingerprint for a page that is not live: restore it with
  `git checkout -- tools/xlsx_viewer.sha256` (or `tools/safety/fmeda_views.sha256`). CI then stays red on that
  `--check`, which is the honest state, and the rest of the change can still go up.
- **Tell the user** in plain words: which page, the error the tool returned, and that the published page now shows
  the old data. Common causes: the page was deleted, or this account cannot write to it.
- **A new page only with the lead's go-ahead.** Ask in chat, recommendation first: "republish to a new link and
  update the links (recommended)" or "leave the old page for now". If they say yes:
  1. Publish the built file **without** `url` (a new artifact, `icon: "table"`), and note the URL the tool returns.
  2. Change the URL constant(s): `VIEWER_URL` in `tools/xlsx_viewer.py`; for the worksheet both `WORKSHEET_URL`
     (`fmeda_views.py`) and `WORKSHEET` (`fmeda_review_md.py`); for the what-if `WHAT_IF` (`fmeda_review_md.py`)
     and the URL in `fmeda_whatif.py`'s docstring.
  3. Rebuild with `--out` / `--html` so the `.sha256` names the new URL (and the page hash matches what you published:
     if the build changed after publishing, republish to the new URL).
  4. Update every live link: `grep -rln "<old artifact id>" --include=*.md --include=*.py .`. Update the READMEs
     (`hara/README.md`, `fsc/README.md`, …) and regenerate the FMEDA review pages (`fmeda_review_md.py`) for the
     worksheet and what-if links. **Leave the review records `RR-*.md` alone**: they keep the link they were reviewed
     with.
  5. Run the checks, and commit with a message that names the old and new links and that the lead asked for it
     (precedent: commit `9e788ad`, "Publish the SysML explorer and the workbook viewer to new pages").
