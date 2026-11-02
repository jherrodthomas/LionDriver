# LionDriver skills

Skills load into every Claude Code session in this repository. Each one teaches the rules and the steps for one
kind of work and calls the project's own scripts; none copies code from the records, so nothing can drift.

| Skill | For | Wraps |
|---|---|---|
| [`decision-inbox`](decision-inbox/SKILL.md) | The loop with the project lead: read answers, copy them in, apply, open the next ten, republish the inbox | `assurance/01-management/decisions/` |
| [`assurance-figure`](assurance-figure/SKILL.md) | Any generated SVG figure: read from the record, house style, terms footer, `--check`, test, CI | `assurance/01-management/figures/figkit.py`, `assurance/trace/tools/terms.py` |
| [`road-scene`](road-scene/SKILL.md) | Top-down scenes of the red car on a road (HARA, SOTIF, STPA, FSC, FMEA, TARA) | `assurance/01-management/figures/scenekit.py` / `.js`, `scene-style.md` |
| [`machine`](machine/SKILL.md) | Interactive 3D machine pages and films (vendored; see its `VENDORED.md`) | three.js kit |

Planned next, in order: charts (with the `dataviz` skill), explainer animations (`tools/wiki/*_animations.py`), GSN
case diagrams, SysML views, Blender hazard scenes, the vehicle asset pipeline, review workbooks.

The skills are AI-drafted (Claude; I0 under WP-M-02 §3.3) and not reviewed. They are working aids, not records: when
a skill and a record disagree, the record wins and the skill is fixed.
