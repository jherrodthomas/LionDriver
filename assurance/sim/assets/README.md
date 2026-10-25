# Vehicle assets (not in this repository)

![Three-quarter render of the Corolla E210 mesh, neutral grey, made with assets/tools/render_views.py](../figures/corolla-e210-render-three-quarter.png)

The Corolla E210 3D model used for layer-3 renders and figures is a purchased, licensed asset and is **not committed
here**: TurboSquid's licence forbids redistributing the model files, and the listing carries an editorial-use-only
restriction (Toyota design rights). This folder is git-ignored except for this file.

| Field | Value |
|---|---|
| Model | Toyota Corolla 2020 Simple Interior, 3d_molier International, TurboSquid product 1450755 |
| Bought | 2026-10-17, Standard licence (royalty-free, editorial uses only), decision DQ-368 option A |
| Files | glTF/GLB (full and Draco-compressed), USDZ, 3ds Max, plus 3DS, Blender, Cinema 4D, FBX and OBJ archives |
| Where they live | Private repository `jherrodthomas/LionDriver-assets` (Git LFS), folder `corolla-e210-3dmolier-1450755/` with SHA-256 sums; a local copy goes in this folder (see [`../vehicle-3d-model.md`](../vehicle-3d-model.md) §4–5) |
| What is allowed in public | Code that loads the mesh from a path, and rendered images and figures made from it |

`tools/` is the one committed subfolder: `vehicle_figures.py` (silhouette extraction and the mock-up figures),
`vehicle_geometry.py` (glass areas and rakes and a side elevation for the physics models, written to
`../figures/corolla-e210-geometry.json`, labelled mesh-derived), `device_shading.py` (a ray cast from each face of
the comma device through the mesh, for the sun on the device: `../figures/corolla-e210-device-shading.json`, derived
numbers only),
`render_views.py` (the documentation renders) and `corolla_e210_metadrive_export.py` (headless Blender script that
writes the MetaDrive files below). All read the GLB from this folder when it is present.

## Derived files for MetaDrive (`corolla_e210/`, ignored)

Written by `tools/corolla_e210_metadrive_export.py` from `1450755-gltf-extended.glb` (see
[`../vehicle-3d-model.md`](../vehicle-3d-model.md) §2 and §6). Same licence as the source: private repository only,
folder `blender-decimated-corolla_e210/` next to the delivered files, with the `SHA256SUMS` the script writes.

| File | Content | SHA-256 |
|---|---|---|
| `vehicle.gltf` (+ `.bin`, `textures/`) | body without wheels or interior (body and wheels together target 70 k triangles), origin on the ground under the body centre, forward +Y | *pending: the script has not been run yet (no Blender on the authoring machine, 2026-10-17); paste from `SHA256SUMS` after the first run* |
| `right_tire_front.gltf`, `right_tire_back.gltf` | right wheels (rim, tyre, disc), origin at the hub; MetaDrive mirrors them for the left side | *pending, as above* |
| `vehicle_full.gltf` | body plus four wheels on hub empties, for figures and viewers, not read by MetaDrive | *pending, as above* |
| `geometry.json` | hub centres, tyre radius, body box, triangle counts, source checksum; read by the vehicle class | *pending, as above* |

To use the mesh in layer 3, set `LIONDRIVER_VEHICLE_ASSETS` to the folder that holds these files (this folder's
`corolla_e210/`, or the private repository's `blender-decimated-corolla_e210/`) before starting the bridge;
`openpilot/tools/sim/bridge/metadrive/corolla_vehicle.py` fails with a message naming the missing file otherwise.
Unset, the bridge uses MetaDrive's stock vehicle. Nothing in CI depends on these files.

`tools/corolla_e210_gltf_export.py` (pure Python, no Blender, no decimation) wrote `corolla_e210/` on 2026-10-17; `vehicle.gltf` sha256 starts `4cee6578f03b50a1`; the full set with `SHA256SUMS` is `gltf-export-corolla_e210/` in the private repository.
