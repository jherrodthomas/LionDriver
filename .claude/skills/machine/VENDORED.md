# Machine Skill, vendored

| Field | Value |
|---|---|
| Upstream | https://github.com/AirsupHQ/machine-skill |
| Commit | `e0bd066` (2026-10, "Refinery examples for plant training") |
| Licence | MIT, Copyright (c) 2026 Air Supply Technologies Inc. ([`LICENSE`](LICENSE)) |
| Taken | `SKILL.md`, `LICENSE`, `package.json`, `kit/`, `scripts/`, `references/`, unchanged |
| Left out | `examples/`, `film/`, `evals/`, `.github/` and the launch notes (about 20 MB of example pages, stills and posters) |
| Check | [`SHA256SUMS`](SHA256SUMS): `assurance/sim/interactive/build_pages.py --check` fails if a vendored file differs from upstream |
| Tool record | WP-P-07 TL-56 |

## How LionDriver uses it

The skill builds interactive 3D pages of a machine in one HTML file. In LionDriver it is a **presentation layer**,
never a model. Its pages live in [`assurance/sim/interactive/`](../../../assurance/sim/interactive/README.md), and the rules
there apply over `SKILL.md`:

1. **No second solver.** Every number on a page comes from a committed, CI-checked results file of the simulation track
   (for example `assurance/sim/results/mcu-heat.json`), pasted in by `build_pages.py`. The page interpolates and
   animates; it computes no physics of its own.
2. **Stamped.** Every page carries "SYNTHETIC (DSR-12) · design aid, no evidence credit".
3. **No films in git.** The recorder's MP4 films go to Actions artifacts or release assets, not the repository.
4. **The licensed Corolla mesh is never used.** Geometry is built from code, as the skill does.

To update the pin: copy the same files from the new upstream commit, rerun
`(cd .claude/skills/machine && find . -type f ! -name SHA256SUMS ! -name VENDORED.md | sort | xargs sha256sum > SHA256SUMS)`,
rebuild the pages and record the change in this file.
