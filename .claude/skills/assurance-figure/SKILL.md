---
name: assurance-figure
description: Add or change a generated SVG figure in LionDriver's assurance records. A figure is a small standard-library Python generator next to the SVG that reads every label and number from its source record (a Markdown table, a YAML register, a results JSON). It draws in the shared figkit house style, ends with the terms definitions line, fails when the source changes shape, and has a --check, a test and a CI line. Use it whenever a work product, README, wiki page or decision card needs a diagram, chart, overview, status board, timeline or picture, or when a figure is stale, wrong or "needs regenerating", even if nobody says "generator". For top-down road scenes with cars use the road-scene skill, which builds on this one.
---

# Assurance figure

LionDriver has about 40 figure generators, and they all follow one pattern. **The SVG is never edited by hand. The
generator is the source, the record is the truth, and CI fails when they disagree.** A reader on a phone should get
the point of a figure without the page around it.

## Before drawing: should this be a figure?

Draw one when it shows something the table cannot: a structure, a flow, a comparison, the shape of a distribution,
where things stand at a glance. Skip it when it would only repeat a short table in boxes. For a decision card, the
picture must show **the difference between the options**.

Find the closest existing generator and read it before writing. Good references:

| Kind | Look at |
|---|---|
| Status board from a table (one tile per row) | `assurance/03-system/figures/fig_s07_csr_status.py` |
| Flow, hierarchy, boxes and arrows | `assurance/03-system/figures/fig_s03_functional_flow.py`, `fig_s03_hierarchy.py` |
| Timing and sequence | `assurance/03-system/figures/fig_s04_timing.py` |
| Plans, management, folder overviews | `assurance/01-management/figures/fig_m_plans.py`, `folder_index.py` |
| Data chart (targets, coverage) | `assurance/06-validation/figures/fig_v02_validation_targets.py`; also load the `dataviz` skill |
| Top-down road scene | the `road-scene` skill |

## The contract

1. **Where.** The generator goes in the work product's area: `assurance/<area>/figures/fig_<wp>_<topic>.py` (for
   example `fig_s07_csr_status.py`). It writes `fig-<wp>-<section>-<n>-<slug>.svg` next to itself
   (`fig-s07-4-1-csr-status.svg` is Figure 4-1 of WP-S-07). Decision cards use `decisions/figures/dq-NNN.svg`.
2. **Standard library only, deterministic.** The same input gives byte-identical output: no dates, no random
   numbers, no dict-order surprises. CI compares bytes.
3. **Read it, don't type it.** Every ID, label, count and number comes from the source at build time, through
   `figkit.section()`, `table()`, `col()` and `plain()` for Markdown, or `yaml`/`json` for registers and results. When
   a cell is free text, map it explicitly (`STATUS_OF` in `fig_s07_csr_status.py`) with a phrase quoted from the
   cell, so a change re-sorts on purpose.
4. **Fail loudly.** Define a `FigureError`. Raise it on a missing section or column, an unknown status word, a
   duplicate ID or an empty table. Never fall back to a default colour or a guessed value.
5. **House style.** Import from `assurance/01-management/figures/figkit.py`: `svg()` (with `<title>` and `<desc>`),
   `header()` ("Figure N-n · Title", a subtitle, the WP reference), `legend()`, `pill()`, `rect`, `text`, `fit()`. The
   colours mean the same thing on every figure:

   | Token | Means |
   |---|---|
   | `SAFETY` / `_BG` (orange) | safety goals, safety mechanisms, the safety path |
   | `SW` (teal), `HW` (indigo) | software elements, hardware elements |
   | `GREEN`, `AMBER`, `RED` (+ `_BG`) | holds or done, partly or open, fails or missing |
   | `INK`, `MUTED`, `FAINT`, `LINE`, `HAIR` | text, secondary text, captions, box strokes, rules |

   Don't add a palette copy. If a colour is missing, add it to figkit.
6. **Terms.** End the body with `terms.svg_footer(body, x, y, width)` (from `assurance/trace/tools/terms.py`). Add
   the SVG path to `terms.FIGURES`, and any new abbreviation or record code to `TERMS`. `terms.py --check` fails on an
   undefined term.
7. **Say what it is.** If the figure shows synthetic, simulated or illustrative data, say so on the figure ("Synthetic
   data, no evidence credit" or "illustrative"). A figure is never evidence on its own account.
8. **`--check`.** `python3 fig_x.py` writes; `python3 fig_x.py --check` exits 1 when the source changed shape or
   the committed SVG is stale.
9. **Test.** `test_fig_x.py` (unittest) needs at least four tests: the committed output is current; every source
   row appears exactly once; a changed or unknown cell raises `FigureError`; and the figure agrees with any count the
   document states elsewhere.

`templates/fig_template.py` and `templates/test_fig_template.py` implement all of this for the most common kind, a
status board with one tile per table row. Copy both into the target `figures/` folder, rename them, fill in CONFIG,
and change `draw()` to the picture you need. The template runs as is against `06-validation/README.md`, so you can
see the pattern work before changing it.

## Steps

1. Copy the templates, then rename and fill them in. Write the docstring first: what the figure shows, where each
   number comes from, and what fails the build.
2. Run the generator, then **look at the result**:
   ```bash
   node .claude/skills/assurance-figure/scripts/preview.mjs <scratchpad>/png path/to/fig-….svg --width 390
   ```
   Then Read the PNGs. Check the full width and the 390 px phone width: no text overlaps, nothing is cut off, a
   `fit()` ellipsis doesn't hide the point, and the legend counts add up.
3. Embed it in the page with alt text that **states what the figure shows, numbers included**, and a caption that
   says where it is drawn from:
   ```markdown
   ![Figure 4-1: the 64 detailed cybersecurity requirements in sixteen groups …: 6 in place, 15 partly, 36 not met, 7 not determined; none verified](figures/fig-s07-4-1-csr-status.svg)

   *Figure 4-1.* <what to read off it>. Drawn from §4 by [`figures/fig_s07_csr_status.py`](figures/fig_s07_csr_status.py); CI fails if it is stale.
   ```
4. Wire CI. Add the generator's `--check` and its test to the "Work-product figures match their source tables and
   records" step of `.github/workflows/assurance.yaml`. Add the SVG to `terms.FIGURES`. Both files are SR-T in
   `assurance/07-supporting/safety-relevant-paths.txt`, so the pull request follows the WP-P-02 safety-relevant
   route.
5. Run the checks:
   ```bash
   python3 assurance/<area>/figures/fig_x.py --check && python3 assurance/<area>/figures/test_fig_x.py
   python3 assurance/trace/tools/terms.py --check
   ```
6. Bump the version and history line of the page that embeds the figure (WP-P-04).

## Changing a source later

When a record changes, regenerate every figure drawn from it in the same commit. `grep -rl "<source file name>"
assurance/*/figures/*.py` finds them. If a generator fails with `FigureError`, fix the mapping on purpose (a new
status gets a colour, a new row gets its phrase). Never loosen the check.
