# Views: changing one, adding one

The model decides **what** a view shows; `views/layout.toml` decides only **where**, and its `kind` picks the
renderer. A figure in `generated/` is never edited by hand, and a layout entry never adds or removes a connection.

## Where things are

| Piece | File |
|---|---|
| View declaration: name, `doc`, `expose`, `render` | `model/Views.sysml` (`view <'V-nn'> camelName : SomeView { … }`) |
| Placement, title, subtitle, width, `desc`, display names (`[titles]`) | `views/layout.toml`, `[views.V-nn]` |
| Interconnection, hierarchy and matrix views (V-01 to V-04) | `tools/render_views.py` |
| Architecture and behaviour views (`kind` functions, security, integration, states, records, sequence, budgets, signals, responsibilities, activity, hsiblocks, parametric, mechanisms, coverage) | `tools/render_arch.py`, `RENDERERS` |
| Requirement views (`thread`, `requirements`, `reqmatrix`, `needs`, `endtoend`, `usecases`, `tsrblocks`) | `tools/render_requirements.py`, `RENDERERS` |
| Systems-engineering views (`n2`, `vcrm`, and `generated/vcrm.md`) | `tools/render_se.py`, `RENDERERS` |
| Palette, Inter text metrics, `text`, `rect`, `pill`, `wrap`, `clip`, routing, `svg_doc` | `tools/svgkit.py` |

`svgkit` keeps the colours of the work-product figures (slate for QM, envelope orange for ASIL, teal for sensing,
purple for untrusted networks). Use its tokens; if a colour is missing, add it there, not in a renderer.

## Changing a view

- Wrong content: fix the model (or the work product it is generated from), not the renderer.
- Wrong place or overlap: change `layout.toml`. An `el` that names no model element fails the build
  (`test_layout_must_name_model_elements`).
- Then `python3 tools/render_views.py`, look at the PNG (below), `python3 tools/test_sysml.py`.

## Adding a view

1. Read the closest existing renderer first. A card list at phone width: `render_goal_coverage` (V-27). A state
   machine: `render_states` (V-13). A matrix: `render_n2` (V-08). A SysML `req` diagram: `render_requirement_diagram`.
2. Declare it in `Views.sysml` with the next number, a `doc` that says what it shows, what it `expose`s and a
   `render` (`asInterconnectionDiagram`, `asTreeDiagram`, `asElementTable`, …). Keep to the reader's subset; the
   pilot must still parse it.
3. Add `[views.V-nn]` to `layout.toml`: `file = "fig-sysml-vNN-<slug>.svg"`, `kind`, `title`, `subtitle`, `width`
   (640 for a phone-first view) and a `desc` that states what the figure shows. A view drawn as several figures
   lists `functions` or `blocks`; a second phone layout uses a `[views.V-nn.phone]` table.
4. Write the renderer `render_x(m, vid, spec, digest) -> str` (or a dict of file name to SVG for several figures)
   and register it: `RENDERERS["x"] = render_x`. Read every label and count from the model `m`; start with the view
   title, the subtitle and the line `SysML v2 view LionDriverViews::<name> · model <digest>` as the others do, and
   end with `k.svg_doc(w, h, title, desc, body)`. Raise `sysml_lite.ModelError` on missing data; never draw a guess.
   Output must be deterministic (no dates, sorted iteration).
5. Add a test to `test_sysml.py` that asserts the facts the view must show (see `test_mechanism_coverage_per_goal`).
   `test_every_view_is_drawn` already fails if a declared view draws no figure or the figure count is off.
6. `python3 tools/render_views.py`, then look:
   ```bash
   node .claude/skills/assurance-figure/scripts/preview.mjs <scratchpad>/png \
     assurance/models/sysml/generated/fig-sysml-vNN-<slug>.svg --width 390
   ```
   Read both PNGs: nothing overlaps or is cut off, a `clip()` ellipsis does not hide the point, counts add up.
7. Add a paragraph and the image to README §6 with alt text that states what it shows, numbers included; if a work
   product page should show it, embed the SVG there by relative path, not a copy. If it should be in the explorer,
   add it to `VIEW_ORDER` in `explorer.py`.
8. The new SVGs change the explorer: run the common tail (README §4 commands, `explorer.py --fragment`, republish).

If the view is meant to replace a hand-drawn figure (SY-06, README §2.1), the swap is the lead's call per figure:
list what the view still lacks in §2.1 and raise it through the `decision-inbox` skill.
