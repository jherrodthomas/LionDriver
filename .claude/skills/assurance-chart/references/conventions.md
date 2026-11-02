# Chart conventions found in the generators

Read from the code on 2026-11-02. When a generator and this page disagree, the generator wins; fix this page.

## Who draws what, and how

| Chart | Generator | Drawn with | Source | Checked by |
|---|---|---|---|---|
| Validation targets on two log axes (WP-V-02 Fig 4-1) | `assurance/06-validation/figures/fig_v02_validation_targets.py` | hand SVG, stdlib | §4 table parsed; prose numbers in `MARKS`/`BANDS`, each with its `src` quote | `--check` (quotes still in the page, SVG current) + 8 tests |
| Fault-injection coverage matrix (WP-V-05 Fig 6-1) | `assurance/06-validation/figures/fig_v05_fault_coverage.py` | hand SVG, stdlib | §5/§6/§8 tables of WP-V-05 and WP-S-02 | `--check` + test |
| Timing budgets vs code-derived times (WP-S-04 Fig 5-1, 5-2) | `assurance/03-system/figures/fig_s04_timing.py` | hand SVG, stdlib | prose numbers in `GROUPS`, each with `src` | `--check` + test |
| FMEDA SPFM / LFM / PMHF against ASIL targets (cards and sheet) | `tools/safety/fmeda_views.py` | hand SVG, theme-aware CSS variables | `assurance/08-analyses/fmea/analyses/fmeda-*.yaml` via `fmea_lint` | `--check` + `test_fmeda_views.py` |
| FMEA/FMEDA figures of record (AP overview, O×D, metrics) | `tools/safety/fmea_diagrams.py` | hand SVG | the FMEA YAMLs | `--check` |
| Sim result plot (lateral offset vs time, two variants) | `assurance/sim/plant/silent_stall.py` `figure()` | hand SVG, theme-aware | its own plant runs; writes `results/silent-stall.{md,svg}` together | `--check` in the sim job |
| Sim result loops (reachability, failure search) | `assurance/sim/figures/fig_sim_plots.py` | hand SVG + SMIL, tokens of `fig_sim_readme.py` | `reach/*.json`, `results/search-*.md` | `--check` + test in the sim job |
| Weather, thermal, supply studies | `assurance/sim/weather/fig_weather.py`, `sim/thermal/figures.py`, `sim/supply/fig_supply.py` | **matplotlib → WebP** | the study's results dict, written with `--figures` | JSON within 0.05 and `.md` current; pixels are not compared |
| Assessment audit charts | `assurance/00-assessment/iso26262-2018/build_audit.py` | matplotlib → SVG | audit data | not in CI |
| Decision cards (`dq-002`, `dq-404`, `dq-407`, `dq-424` …) | none: hand-written SVG in `assurance/01-management/decisions/figures/` | inbox page tokens | numbers copied from the study or record | `check_decisions.py` (file exists, has a caption) only |

The three oldest work-product charts (`fig_v02`, `fig_v05`, `fig_s04_timing`) carry their own copy of the palette
from before `figkit.py` existed. Do not copy those blocks; import from figkit. Their SVGs are also not yet in
`terms.FIGURES`, so they have no terms footer.

## Palettes: one meaning per colour

**figkit (work-product figures, light only)**, `assurance/01-management/figures/figkit.py`: `INK MUTED FAINT LINE HAIR`
for text and rules, `GREEN/AMBER/RED (+_BG)` for holds / partly / fails, `SAFETY` orange for safety goals and
mechanisms, `SW` teal and `HW` indigo for software and hardware elements, `GREY_BG`, `HATCH` (defs id `hatch`).

**Required vs performed**, `scenekit.REQ` `#16A34A` dashed and `scenekit.PERF` `#DC2626` solid on white (and `REQ_S` /
`PERF_S` on asphalt). Use them for a chart that sits beside a road scene. A generator that imports `scenekit` must be
listed in the "Who uses it" table of `scene-style.md` (`test_scenekit.py` fails otherwise). The `dataviz` validator
gives this pair a deutan ΔE of 5.0 (FAIL alone), so **the dash is the encoding, not the hue**: never draw REQ solid
or PERF dashed, and label both.

**Sim and decision tokens (theme-aware)**: SVGs shown on GitHub or in an artifact define CSS variables and redefine
them under `@media (prefers-color-scheme: dark)`.

| Family | Defined in | Tokens |
|---|---|---|
| Sim figures | `assurance/sim/figures/fig_sim_readme.py` `STYLE` | `--bg --ink --ink2 --ink3 --grid --card`, `--real` blue (real code / as built), `--amb` amber (bound, model), `--bad` red, `--pic` violet, `--flt` orange (fault) |
| Sim study plot | `silent_stall.py` `figure()` | `--ink --muted --line --bad --accent --bg` and classes `s-ink s-muted s-bad s-acc` |
| FMEDA views | `tools/safety/fmeda_views.py` (style block near line 117) | `--bg --ink --ink2 --line --head --card --track` |
| Decision inbox | `assurance/01-management/decisions/build_inbox.py` `TEMPLATE` | `--accent` (recommended), `--muted`, `--bad`, `--ok`, `--warn`, `--line`, classes `s-ink s-muted s-line s-ok s-bad s-acc s-warn …` |

Validator results (`node <dataviz>/scripts/validate_palette.js "<hexes>" --mode light`): sim `--real`/`--bad`
passes in light and dark (ΔE 21.6 / 19.2). figkit `SAFETY,SW,HW` as a categorical set fails the chroma floor on `SW`
teal, which is fine for its job (identity of element kind, always with a text label) but a reason never to use the
figkit hues as a series palette.

## How the repo palette overrides the dataviz placeholder palette

The `dataviz` skill ships a brand-neutral palette (`references/palette.md`) and says to swap it. Here:

1. **Colour is semantic, not categorical.** Pick the token for what the mark *means* (holds/fails, safety path, real
   vs model, required vs performed, recommended option). Series that are just "different things" get neutral greys and
   direct labels, not hues. Never invent hues; a missing meaning goes into figkit (or the family's token block).
2. **Status colours are figkit `GREEN/AMBER/RED`** with a word beside them. An estimate or a synthetic result that
   meets its target is **amber, never green** (FMEDA convention); predicted or placeholder values are **hollow,
   dashed or hatched**, never solid (WP-V-02 Fig 4-1, FMEA AP figures).
3. **Hover and table view.** Committed figures are static SVG in Markdown, so there is no tooltip layer. The "table
   view" is the source record (the §-table or the results `.md`), named in the caption; the `<desc>` states every
   number. Live pages (artifacts, the FMEDA worksheet) follow dataviz's interaction rules in full.
4. **Dark mode** only where the family is theme-aware (sim, FMEDA views, decision cards). figkit figures are light
   only and paint their own white background.
5. Dataviz's form heuristic, one-axis rule, thin marks, legend rules and anti-patterns apply unchanged.

## Determinism

- Stdlib SVG: fixed rounding (`fmt`, `f"{v:.1f}"`), lists in source or CONFIG order, no timestamps, no `random`.
  Sample long traces with a fixed stride (`silent_stall.py` keeps every 5th point).
- matplotlib SVG (only where CI installs it): `matplotlib.use("Agg")`, `rcParams["svg.hashsalt"] = "<fixed id>"`,
  `rcParams["svg.fonttype"] = "none"`, `savefig(..., metadata={"Date": None})`, set `MPLCONFIGDIR` (all in
  `build_audit.py`). Raster outputs (WebP) are not byte-stable across library versions; CI compares the results JSON
  within a tolerance instead (`sun_glare.compare`), so a raster chart must never be the only place a number appears.
- Packages: matplotlib, pandas, pvlib and Pillow are pinned in `assurance/sim/weather/requirements.txt` and installed
  only in that CI job. `assurance/sim/requirements.txt` (numpy, pycapnp, scenariogeneration, …) is installed in the
  sim jobs. Work-product jobs have only `assurance/trace/requirements.txt`, so their charts must be stdlib (PyYAML is
  available).
