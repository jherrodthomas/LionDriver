---
name: assurance-chart
description: Draw or fix a data chart in LionDriver's assurance records, a plot of numbers rather than boxes and arrows. Targets against results, required against performed, coverage, timing budgets and distributions, parameter sweeps, simulation results, FMEDA metrics (SPFM, LFM, PMHF) against ASIL targets, or the option comparison on a decision card. The chart is generated from its record or results JSON in the house palette, labels synthetic data, ends with the terms line, and has a --check, a test and a CI line. Use it whenever someone wants to "plot", "graph", "chart", "compare against the target", "show the margin", "show the distribution", "visualise the results", or "put a picture of the numbers" in a work product, sim result, FMEA page or decision card, or when such a chart is stale or wrong, even if nobody says "chart". Box-and-arrow figures use assurance-figure; cars on a road use road-scene.
---

# Assurance chart

A chart in LionDriver is a generated figure whose marks are numbers. Everything in the `assurance-figure` skill
applies (generator next to the SVG, read every value from the record, `FigureError`, `--check`, test, CI line,
terms footer, alt text). This skill adds what is specific to charts: where the numbers come from, which colours
mean what, how synthetic results are labelled, and which existing generator to copy. The code stays in the repo:
call it and copy from it, don't paste it here.

## First

1. **Load the `dataviz` skill** for the chart design: the form heuristic (is it even a chart?), one axis only, thin
   marks, direct labels, legend rules and the anti-patterns list. The repo's palette **replaces** its placeholder
   palette (below), and committed SVGs are static, so its hover layer does not apply. The "table view" is the source
   record, named in the caption.
2. Read `assurance-figure/SKILL.md` if this session has not, then `references/conventions.md` here (who draws what,
   the token families, determinism, packages).
3. Find the closest existing chart and read it before writing:

| Chart | Copy from |
|---|---|
| Results against a required value, from a results JSON or a table (bars + dashed line) | `templates/fig_chart_template.py` here (figkit, stdlib) |
| Targets on a log scale, prose numbers each with a quoted `src` | `assurance/06-validation/figures/fig_v02_validation_targets.py` |
| Coverage matrix (cases × blocks × goals) | `assurance/06-validation/figures/fig_v05_fault_coverage.py` |
| Budgets vs measured or code-derived times | `assurance/03-system/figures/fig_s04_timing.py` |
| FMEDA metrics against ASIL targets, theme-aware cards | `tools/safety/fmeda_views.py` (`fig_cards`, `bar`) |
| Simulation result plot written by the study itself | `assurance/sim/plant/silent_stall.py` (`figure()`) |
| Simulation results as an animated loop | `assurance/sim/figures/fig_sim_plots.py` |
| Option comparison on a decision card | `assurance/01-management/decisions/figures/dq-424.svg` and `references/decision-cards.md` |

The three oldest work-product charts copy the palette inline (they predate figkit). Take their structure, not their
palette block.

## Colour means something

Pick a token for what the mark **means**; never cycle hues for "series 1, 2, 3". Different things that have no
meaning of their own get neutral greys and direct labels.

| Meaning | Token |
|---|---|
| Text, axes, grid | figkit `INK`, `MUTED`, `FAINT`, `HAIR` (grid recessive) |
| Holds / partly / fails (with a word beside it) | figkit `GREEN`, `AMBER`, `RED` (+ `_BG`) |
| Required (dashed) vs performed (solid), beside a scene | `scenekit.REQ` / `PERF`; then list the generator in `scene-style.md` |
| A target or limit on a standalone chart | dashed line in `INK`, labelled with its value |
| Real code / as built vs model or bound (sim pages) | `--real` blue vs `--amb` / `--ink3`, from `fig_sim_readme.STYLE` |
| Recommended option on a card | `s-acc`; today `s-muted` dashed; worst outcome `s-bad` |

Hard rules:
- **Estimates and synthetic results are never green.** An estimate that meets its target is amber (FMEDA
  convention). Placeholders and predictions are hollow, dashed or hatched, never solid (WP-V-02 Fig 4-1).
- **The dash carries required vs performed**, not the hue: green/red alone fails colour-blind separation (dataviz
  validator, deutan ΔE 5.0). Keep both the dash and a label.
- A new colour goes into figkit (or the family's token block), never a local copy. Check any new pair of series
  colours with the dataviz `scripts/validate_palette.js` in light and, for theme-aware families, dark.

## Honesty rules

- **Synthetic data says so on the chart**, not only in the caption: "Synthetic (DSR-12) · design aid, no evidence
  credit" (WP-V-02 §5.3.5, DQ-139, DQ-413). The generator fails if the source does not declare itself synthetic (the
  results JSON's `about` starts with "Synthetic (DSR-12)"; the template checks this).
- A chart is never evidence on its own account. It restates a record; the verdict lives in the record. Do not draw
  a pass the record does not state, and do not draw a placeholder target as if frozen.
- Every number comes from the source at build time. Prose numbers are listed with the exact `src` text they come
  from, and `--check` fails when that text changes (`fig_v02`, `fig_s04_timing`).
- Your work is AI-authored: I0 under WP-M-02 §3.3. Ask for human review; never mark it approved or close a finding
  with it.

## Steps

1. Decide the form with dataviz; write the docstring first (what it shows, the source and its keys or §, what fails).
2. Copy the closest reference into `assurance/<area>/figures/` as `fig_<wp>_<topic>.py` and `test_fig_<wp>_<topic>.py`
   (sim results: inside the study script, beside its `.md` table, as `silent_stall.py` does). The template runs
   as is against `assurance/sim/results/crest.json`, so you can see it work before changing CONFIG.
3. Stdlib SVG for anything CI byte-compares. matplotlib only in a job that installs it, and then see
   `references/conventions.md` § Determinism. Width 640 for anything read on a phone (text 12 px or more), 1200
   for wide work-product sheets.
4. Run it twice and compare hashes (deterministic), then **look at it**:
   ```bash
   python3 assurance/<area>/figures/fig_x.py && sha256sum assurance/<area>/figures/fig-*.svg
   node .claude/skills/assurance-figure/scripts/preview.mjs <scratchpad>/png assurance/<area>/figures/fig-….svg --width 390
   ```
   Read both PNGs: no label crosses a line or another label, nothing past the right edge, the value labels match
   the source, the synthetic stamp is visible. Theme-aware SVGs render light here; card SVGs need the wrapper in
   `references/decision-cards.md`.
5. Test (unittest, at least): output current; every value drawn once; a new, missing or changed key raises
   `FigureError`; the synthetic label is present and a source without it fails; no undefined term
   (`terms.find(terms.svg_texts(svg))` unknown is empty); the chart agrees with the number the page states.
6. Wire it: the `--check` and test into the right job of `.github/workflows/assurance.yaml` ("Work-product figures
   match their source tables and records" for stdlib charts; the sim job for sim results), the SVG into
   `terms.FIGURES`. Both files are SR-T (`assurance/07-supporting/safety-relevant-paths.txt`).
7. Embed with alt text that states the numbers and a caption naming the source and generator; bump the page's
   version and history line (WP-P-04).
8. Run:
   ```bash
   python3 assurance/<area>/figures/fig_x.py --check && python3 assurance/<area>/figures/test_fig_x.py
   python3 assurance/trace/tools/terms.py --check
   ruff check assurance/<area>/figures/fig_x.py assurance/<area>/figures/test_fig_x.py
   ```

## What runs where

Stdlib generators (`fig_v02`, `fig_v05`, `fig_s04_timing`, `fmeda_views.py`, `fmea_diagrams.py`, the template) run
anywhere. `fig_sim_plots.py` and `silent_stall.py` need `assurance/sim/requirements.txt` (scenariogeneration,
pycapnp, …) and the `opendbc_repo`/`panda` submodules; CI's sim jobs install them. matplotlib, pandas, pvlib and
Pillow come only from `assurance/sim/weather/requirements.txt` in the weather job; those WebP charts are written with
`--figures` and CI checks the results JSON (within 0.05) and the `.md`, not the pixels. If a package is missing
locally, say so and leave the check to CI; do not restyle a chart you cannot run.
