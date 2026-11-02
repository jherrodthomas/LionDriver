# LionDriver skills

Skills load into every Claude Code session in this repository. Each one teaches the rules and the steps for one
kind of work and calls the project's own scripts; none copies code from the records, so nothing can drift.

| Skill | For | Wraps |
|---|---|---|
| [`decision-inbox`](decision-inbox/SKILL.md) | The loop with the project lead: read answers, copy them in, apply, open the next ten, republish the inbox | `assurance/01-management/decisions/` |
| [`assurance-figure`](assurance-figure/SKILL.md) | Any generated SVG figure: read from the record, house style, terms footer, `--check`, test, CI | `assurance/01-management/figures/figkit.py`, `assurance/trace/tools/terms.py` |
| [`assurance-chart`](assurance-chart/SKILL.md) | Data charts: targets against results, coverage, timing, sweeps, FMEDA metrics, decision-card comparisons | the chart generators, figkit, the `dataviz` skill |
| [`road-scene`](road-scene/SKILL.md) | Top-down scenes of the red car on a road (HARA, SOTIF, STPA, FSC, FMEA, TARA) | `assurance/01-management/figures/scenekit.py` / `.js`, `scene-style.md` |
| [`explainer-animation`](explainer-animation/SKILL.md) | The animated wiki explainers, every phrase quoted from its record | `tools/wiki/*_animations.py`, `build_wiki.py` |
| [`safety-case`](safety-case/SKILL.md) | Case records, GSN diagrams, dashboard, snapshot and controlled copy, gate skeletons; what an AI may not change | `assurance/case-records/`, WP-K-01 |
| [`sysml-model`](sysml-model/SKILL.md) | The SysML v2 model: what to regenerate after which work-product edit, its checks, views, explorer, AUTOSAR | `assurance/models/sysml/` |
| [`review-workbook`](review-workbook/SKILL.md) | FMEA/FMEDA/PFMEA records, lint, review cards and workbooks, the workbook viewer | `assurance/08-analyses/fmea/`, `tools/safety/`, `tools/xlsx_viewer.py` |
| [`hazard-scene-3d`](hazard-scene-3d/SKILL.md) | Blender scenes and dashboards for every hazardous event, the gallery, asset licences | `assurance/sim/blender/` |
| [`vehicle-asset`](vehicle-asset/SKILL.md) | The reference-car mesh, MetaDrive export, vehicle figures, the interactive device page; what the mesh is never for | `assurance/sim/assets/`, `assurance/sim/interactive/` |
| [`machine`](machine/SKILL.md) | Interactive 3D machine pages and films (vendored; see its `VENDORED.md`) | three.js kit |

How they fit: `decision-inbox` holds every question for the lead; the drawing skills (`assurance-figure`,
`assurance-chart`, `road-scene`, `explainer-animation`) share figkit's palette, the terms footer and
`assurance-figure/scripts/preview.mjs` for looking at the output; `sysml-model`, `review-workbook` and `safety-case`
cover the generated records and the pages published from them; `hazard-scene-3d`, `vehicle-asset` and `machine`
cover 3D.

The skills are AI-drafted (Claude; I0 under WP-M-02 §3.3) and not reviewed. They are working aids, not records: when
a skill and a record disagree, the record wins and the skill is fixed.
