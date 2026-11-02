---
name: vehicle-asset
description: Work with LionDriver's reference-car 3D asset and the figures and pages drawn from it. It covers the purchased Corolla E210 mesh (DQ-368, Standard editorial licence, kept out of git), the pure-Python and Blender exporters to MetaDrive's vehicle layout (body glTF plus separate right-wheel files, +Y forward), the CorollaE210Vehicle class and the bridge's LIONDRIVER_VEHICLE_ASSETS hook, the committed mesh-derived outputs (silhouette, geometry and device-shading JSON, documentation renders, the mock-up figures) and their --check runs, and the interactive comma 3X page built with the vendored machine skill. Use it whenever someone says "car model", "3D model", "mesh", "glTF", "GLB", "MetaDrive vehicle", "render the Corolla", "vehicle figure", "silhouette", "side view of the car", "device in the car", "windshield geometry", "comma 3X page" or "interactive 3D", or wants the car drawn, exported, rendered or measured. It also covers what the mesh must never be used for.
---

# Vehicle asset

The reference car (CFG-001, Corolla E210 sedan) has a purchased 3D mesh. It is a **presentation asset**. Its record is
[`assurance/sim/vehicle-3d-model.md`](../../../assurance/sim/vehicle-3d-model.md). Read its §1 before you touch a car
model, and §4 and §6 before you change a tool. When this skill and that record disagree, the record wins and the skill
is fixed.

## What the mesh is not for (§1)

| Never | Instead |
|---|---|
| A vehicle fact: length, width, wheelbase, track, trim, mass | The vehicle register [`docs/liondriver/vehicles/vehicles.yaml`](../../../docs/liondriver/vehicles/vehicles.yaml) (edit it, then `python3 tools/vehicles/vehicle_register.py`). Plant parameters come from opendbc through [`assurance/sim/plant/corolla.py`](../../../assurance/sim/plant/corolla.py). Never retype either from the mesh. The register's 1,781 mm width stays *to confirm* whatever the mesh says |
| An input to the plant, the panda code, MetaDrive's dynamics or any result | Nothing. In layer 3 the bridge keeps `render_vehicle: False`, so openpilot never sees the body |
| Evidence | It is like a colour token. Captions say the figure shows the purchased mesh |
| A reason to rig the car in Unreal or Unity, or to re-run the marketplace comparison | Cite §1, §3 and DQ-368 |

Some numbers *measured on* the mesh do feed design-aid models: glass areas and rakes, the windshield top, a side
elevation (`vehicle_geometry.py`) and the sun on the device (`device_shading.py`). The weather and thermal models read
them. Every such value has `status: mesh-derived` in `assurance/sim/weather/params.yaml` or `thermal/params.yaml`, with
the JSON named as its source. The results stay synthetic (DSR-12) with no credit, and a measurement on the reference car
replaces the value.

## Licensing: what may be committed

- **Never commit** the delivered model files or anything exported from them (GLB, glTF, `.bin`, textures, the
  `corolla_e210/` folder, `geometry.json`, a decimated mesh). `.gitignore` ignores `assurance/sim/assets/*` except its
  `README.md` and `tools/`. Never `git add -f` in there.
- **Where it lives:** the private repository `jherrodthomas/LionDriver-assets` (Git LFS):
  `corolla-e210-3dmolier-1450755/` holds the delivered files, and `gltf-export-corolla_e210/` and
  `blender-decimated-corolla_e210/` hold the exports, each with `SHA256SUMS`. A working copy goes in
  `assurance/sim/assets/1450755-gltf-extended.glb`. Never push it to a public place, never attach it to an artifact or
  an Actions upload, and never paste it into a page.
- **May be published:** code that loads the mesh from a path, rendered images, outlines, and numbers derived from it.
- Buying another model, or using this one beyond editorial use, is a money and licence question for the lead. Use the
  `decision-inbox` skill; do not decide it here.

## The pieces

| Tool (`assurance/sim/assets/tools/`) | Needs the GLB | Writes (committed unless noted) | Checked by |
|---|---|---|---|
| `vehicle_figures.py` | Optional: extracts the silhouette when present, otherwise reads the JSON | `figures/corolla-e210-silhouette.json` (with GLB), `figures/fig-sim-mock-0{1,2,3}-*.svg` | `--check` (not yet in CI) |
| `vehicle_geometry.py` | Yes, to write | `figures/corolla-e210-geometry.json` | `--check` (well-formed) in CI "simulation weather physics" |
| `device_shading.py` | Yes, to write (numpy) | `figures/corolla-e210-device-shading.json` | `--check` (well-formed) in CI "simulation weather physics" |
| `render_views.py` | Yes (panda3d, panda3d-gltf) | `figures/corolla-e210-render-{three-quarter,side,top}.png` | Nothing. Look at them |
| `corolla_e210_gltf_export.py` | Yes (numpy) | `assets/corolla_e210/` (**ignored**, licensed) | Load test in Panda3D |
| `corolla_e210_metadrive_export.py` | Yes (Blender 4.x) | `assets/corolla_e210/`, decimated (**ignored**) | **Never run**; front/rear bug, see below |

`plant/report.py` draws the silhouette in every layer-1 figure, and `assurance/sim/blender/scene_assets.py` uses it as
the stand-in car. A change to the silhouette JSON therefore changes those figures too: run their `--check` runs
(see [`references/pipeline.md`](references/pipeline.md)). For Blender hazardous-event scenes that place the mesh, use
the `hazard-scene-3d` skill. For flat top-down scenes with the red car, use `road-scene`.

Read [`references/pipeline.md`](references/pipeline.md) for commands, inputs, outputs and the downstream chain, and
[`references/metadrive.md`](references/metadrive.md) for the vehicle class conventions and the first-load caveats.

## Rules that are easy to get wrong

1. **Front and rear: never trust mesh names.** The separate `wheel_1/2`, `tire_1/2` are the **front** wheels. The fused
   `wheels_forward`, `tires_forward` and `brake_discs_3` are the **rear** (§4). Tell the ends apart by the tail lamps.
   The file faces −y. On a side view the rear has the higher deck and the shark-fin antenna. The Blender script and the
   wheel labels in `vehicle_figures.py` still follow the names; fix that on purpose before you rely on either.
2. **MetaDrive layout (§2):** `vehicle.gltf` is the body only, origin on the ground under the body centre, **+Y
   forward**, X lateral, Z up. Each wheel is its own file (`right_tire_front.gltf`, `right_tire_back.gltf`), origin at
   the hub, and MetaDrive mirrors them for the left. The class's wheelbase constants must match the mesh's arches; take
   them from `geometry.json`. Fix the wheel side and the body height in the class, never in the mesh.
3. **Trim:** the mesh has 18-inch sport-trim wheels, and CFG-001 is 16-inch L/LE/XLE. Any figure that shows the wheels
   says "sport-trim wheels".
4. **Mock-ups say so.** Every figure that is not drawn from results says "mock-up" and "illustrative" in its title,
   `<desc>` and footer, and every placeholder number is labelled as one. Turning a mock-up into a real figure follows
   the `assurance-figure` skill (record-driven, figkit, terms footer, test, CI line).
5. **Interactive pages show only committed results.** `assurance/sim/interactive/` pages use the vendored `machine`
   skill as a presentation layer: no second solver, the stamp "SYNTHETIC (DSR-12) · design aid, no evidence credit",
   no MP4 in git, and **no licensed mesh**. Geometry is built in code at the models' sizes. Its README rules override
   the machine skill's `SKILL.md`. Do not edit the vendored files; `build_pages.py --check` hashes them.

## Steps

1. Read §1, then the section of the record for your task. Check whether the GLB is present:
   `ls assurance/sim/assets/*.glb`. If it is missing, you can only run checks and change code that reads committed
   JSON. Say so, and do not fake an output.
2. Make the change with the existing tool. For a new kind of output, extend that tool rather than copying its loader.
   Keep it deterministic, because CI compares bytes.
3. Regenerate, then run every check in [`references/pipeline.md`](references/pipeline.md#checks) that the change
   reaches. Run all of them when a shared JSON changed.
4. **Look at the output.** For SVGs, run
   `node .claude/skills/assurance-figure/scripts/preview.mjs <scratchpad>/png assurance/sim/figures/fig-sim-mock-03-camera-geometry.svg --width 390`
   and Read the PNGs. Check the car faces the way the caption says (rule 1), that labels do not sit on the outline, and
   that the phone width still reads. For pages, see the interactive section of the pipeline reference.
5. Update the record: version and history line of `vehicle-3d-model.md` or `assets/README.md` (WP-P-04), the §9
   handover state, and the `SHA256SUMS` / pending cells when an export was run. Write only what you ran ("load-tested in
   Panda3D", "not loaded in MetaDrive"), not what should work.
6. Work by an AI is I0 (WP-M-02 §3.3): mark it draft and unreviewed, and ask for review. Never mark it approved.
