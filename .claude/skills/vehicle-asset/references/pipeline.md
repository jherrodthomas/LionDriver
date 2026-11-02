# Vehicle asset pipeline: commands, outputs, checks

Paths are from the repository root. "GLB" means `assurance/sim/assets/1450755-gltf-extended.glb`, the full delivered
file (ignored and licensed). Use the full GLB, not the Draco/KTX2 one, because panda3d-gltf is not confirmed to read
those extensions.

## Getting the mesh

The GLB is not in this repository. Copy it from the private repository `jherrodthomas/LionDriver-assets`, folder
`corolla-e210-3dmolier-1450755/`, and check it against that folder's `SHA256SUMS`. If the session cannot reach that
repository, stop and say so. Do not look for the model elsewhere, and do not buy or download a substitute. Procurement
is DQ-368 and was answered A.

## Commands

| Command | Needs | Does |
|---|---|---|
| `python3 assurance/sim/assets/tools/vehicle_figures.py` | Nothing (GLB optional) | Writes the three mock-up SVGs. With the GLB it first re-extracts `figures/corolla-e210-silhouette.json` |
| `python3 assurance/sim/assets/tools/vehicle_figures.py --check` | Nothing | Exits 1 if a committed mock-up SVG differs from a fresh draw |
| `python3 assurance/sim/assets/tools/vehicle_geometry.py` | GLB, numpy | Writes `figures/corolla-e210-geometry.json` (glass areas and rakes, side elevation; frame x forward, y up, z left) |
| `python3 assurance/sim/assets/tools/vehicle_geometry.py --check` | Nothing | The committed JSON is well formed (it does not re-measure) |
| `python3 assurance/sim/assets/tools/device_shading.py` | GLB, numpy | Ray-casts the device face through the mesh and writes `figures/corolla-e210-device-shading.json` |
| `python3 assurance/sim/assets/tools/device_shading.py --check` | Nothing | The committed table is well formed |
| `python3 assurance/sim/assets/tools/render_views.py <GLB> assurance/sim/figures` | GLB, panda3d, panda3d-gltf | The three documentation PNGs (paint recoloured grey, glass translucent) |
| `python3 assurance/sim/assets/tools/corolla_e210_gltf_export.py --glb <GLB> --output-dir assurance/sim/assets/corolla_e210` | GLB, numpy | MetaDrive layout, no decimation (about 200k body triangles) |
| `blender --background --python assurance/sim/assets/tools/corolla_e210_metadrive_export.py -- --input <GLB> --output-dir assurance/sim/assets/corolla_e210` | GLB, Blender 4.x | Decimated MetaDrive layout (about 70k triangles). **Unrun. It treats the fused wheel pair as the front, which is wrong (§4). Fix that first** |

Both exporters write the same layout: `vehicle.gltf`, `right_tire_front.gltf`, `right_tire_back.gltf`,
`vehicle_full.gltf` (all four wheels on hub nodes, for figures and load tests), `geometry.json`, `textures/` and
`SHA256SUMS`. All of it is licensed. It goes to the private repository, never to git.

## Who reads the committed outputs

| Output | Read by |
|---|---|
| `corolla-e210-silhouette.json` | `vehicle_figures.py` (mock-ups), `assurance/sim/plant/report.py` (outline in every layer-1 figure; falls back to a rectangle with a warning), `assurance/sim/blender/scene_assets.py` (stand-in car) |
| `corolla-e210-geometry.json` | `assurance/sim/weather/crosswind.py`, and the `mesh-derived` entries of `weather/params.yaml` (glass, camera height) |
| `corolla-e210-device-shading.json` | `assurance/sim/weather/device_sun.py`; `thermal/params.yaml` `glass_tilt_deg` (mesh-derived) |
| Render PNGs | `vehicle-3d-model.md` §5, `assets/README.md` |
| Mock-up SVGs | `vehicle-3d-model.md` §7 |

To find any new consumer, run `grep -rln "corolla-e210-" assurance --include=*.py --include=*.yaml`. When a JSON
changes, regenerate and check every consumer in the same change.

<a id="checks"></a>
## Checks

All of these run without the GLB. They were verified on 2026-11-02 and exit 0 on a clean tree.

```sh
python3 assurance/sim/assets/tools/vehicle_figures.py --check      # mock-ups current (not yet in CI; §9 asks for it)
python3 assurance/sim/assets/tools/vehicle_geometry.py --check     # CI: simulation weather physics
python3 assurance/sim/assets/tools/device_shading.py --check       # CI: simulation weather physics
python3 tools/vehicles/vehicle_register.py --check                 # CI: trace and link checks (register and citing docs agree)
python3 assurance/trace/tools/terms.py --check                     # CI: every page and figure defines its terms
# vehicle class without MetaDrive (pytest; not yet in CI):
PYTHONPATH=. python3 -m pytest -q openpilot/tools/sim/tests/test_corolla_vehicle.py
```

When the silhouette or geometry JSON changed, also run the consumers' checks:

```sh
python3 assurance/sim/plant/report.py --check                      # CI: simulation plant model (needs opendbc, panda submodules)
python3 assurance/sim/weather/crosswind.py --check                 # CI: simulation weather physics
python3 assurance/sim/weather/device_sun.py --check
```

If `pytest` is missing, install it outside the repository, for example
`python3 -m pip install --target <scratchpad>/py pytest`, and put that folder first on `PYTHONPATH`.

## Interactive pages (`assurance/sim/interactive/`)

These pages are built with the vendored `machine` skill (TL-57, upstream `e0bd066`). `page.html` is the shell, and
`<name>.js` is the machine; it reads its numbers only from `D`. `build_pages.py` pastes in the kit, the data (read from
committed results such as `results/mcu-heat.json` and `thermal/params.yaml`) and the script, and writes `<name>.html`.
Edit the `.js` or the results, never the built `.html`.

```sh
python3 assurance/sim/interactive/build_pages.py            # rebuild
python3 assurance/sim/interactive/build_pages.py --check    # page current and vendored skill unchanged (CI: simulation interactive pages)
npm i --no-save --no-audit --no-fund --prefix assurance/sim/interactive playwright@1.56.1
(cd assurance/sim/interactive && npx playwright install chromium)
node assurance/sim/interactive/check_pages.mjs              # headless: no page error, stamp present, numbers equal the results at 8 settings
```

A new page needs a builder entry in `build_pages.py` and a probe entry in `check_pages.mjs`. The probe interpolates
the results file independently, so do not import the page's own interpolation. It also needs a row in the
interactive README's table.

To look at a page, take a still with the machine skill's `shot.mjs`. It resolves Playwright next to itself, and
installing Playwright inside the vendored folder would leave an untracked `node_modules/` there. So run a scratchpad
copy:

```sh
cp -r .claude/skills/machine/scripts <scratchpad>/machine-scripts
npm i --no-save --no-audit --no-fund --prefix <scratchpad>/machine-scripts playwright@1.56.1
node <scratchpad>/machine-scripts/shot.mjs assurance/sim/interactive/comma3x.html <scratchpad>/shot.png \
  --root assurance/sim/interactive --js "__ld.settle()" --w 1280 --h 800
```

Then Read the PNG. Check that the stamp and the pills are visible, the numbers equal the results, and no label sits on
another. Also take a still at phone width (`--w 390 --h 844`). `GPU stall due to ReadPixels` console lines are harmless.
Films (`record.mjs`, which needs ffmpeg) go to Actions artifacts, never to git.
