# Vehicle assets (not in this repository)

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

To use the mesh locally, place the files here and point the loader at this folder (`LIONDRIVER_VEHICLE_ASSETS`, to
be defined with the MetaDrive vehicle class). Nothing in CI depends on these files.
