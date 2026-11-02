# Assets and licences

Sources: `assurance/sim/assets/README.md` (the car), `assurance/sim/blender/library/README.md` §4 (CC0) and §5
(CC-BY), `assurance/sim/blender/library/people/README.md` (pedestrians). The `vehicle-asset` skill covers the car
mesh in depth.

| Asset | Licence | Where it lives | Committed here |
|---|---|---|---|
| Corolla E210 mesh (TurboSquid 1450755, 3d_molier) | **Purchased, Standard licence**, royalty-free, editorial use only; bought 2026-10-17, DQ-368 option A | private `jherrodthomas/LionDriver-assets` (Git LFS, `corolla-e210-3dmolier-1450755/`); local copy at `assurance/sim/assets/1450755-gltf-extended.glb` (git-ignored) or `LIONDRIVER_VEHICLE_GLB` | Never. Renders and figures made from it may be published; a `scene.blend` made with it holds the mesh and stays private in `out/` |
| Sky HDRIs, textures, scanned plants, street furniture (Poly Haven, ambientCG) | CC0 1.0 | fetched by `fetch_assets.py` to `assurance/sim/assets/library/<slot>/` (git-ignored) | Only `library/assets.lock.json` (IDs, URLs, SHA-256) |
| Pedestrians (Quaternius) | CC0 1.0 | built by `library/people/build_people.py` | Yes, the two small GLBs (no attribution required) |
| Building, farm, car-pack, trailer and civil-vehicle kits (eight Sketchfab models) | **CC-BY 4.0** | private `LionDriver-assets` under `sketchfab/` with `SHA256SUMS`; unpacked by `fetch_assets.py` from a local clone (`LIONDRIVER_ASSETS_REPO`, else a `liondriver-assets` folder beside this repository) | Never; only the lock entries |

## Rules

1. **Nothing licensed or bulky is committed.** No GLB, FBX, zip, texture or `.blend` from these sources goes into
   this repository; `out/` and `assets/library/` are git-ignored. Only renders (JPEG dashboards, MP4 clips, WebP
   previews) and the lock file are committed. Before committing, `git status` must show nothing under those paths.
2. **Credit the CC-BY kits.** Any render that shows them must credit title, author, licence and link. `gallery.py`
   writes the Credits section of `dashboards/README.md` from the lock; a figure, page or post that uses a render
   outside the gallery must carry the same credit lines (library README §5 table).
3. **Without the assets the pipeline still runs**: no GLB gives the silhouette stand-in
   (`../figures/corolla-e210-silhouette.json`), no CC0 slot gives the procedural look for that slot, no kit clone
   gives procedural buildings and Corollas for traffic. A render made like that must not replace a committed
   dashboard made with the real assets unless the lead wants that look; say which look a render used.
4. **`fetch_assets.py --locked`** fetches exactly the locked files and checks every SHA-256, so two machines render
   the same pixels. Plain `fetch_assets.py` may resolve a different asset (search fallback) and rewrite the lock:
   look at a test render before committing a changed lock, as was done for the 2026-10-18 picks.
5. **Kit choices are the lead's.** The Brooklyn kit is unused (graffiti); the gas station and overpass are not used
   yet. Buying or adding a paid asset is a money decision: ask through the `decision-inbox` skill.
6. Car-pack and civil-vehicle bodies are generic (no real makes). Keep it that way; no brand marks on any road user.

```bash
python3 assurance/sim/blender/fetch_assets.py --check-hosts   # can this machine reach Poly Haven and ambientCG?
python3 assurance/sim/blender/fetch_assets.py --locked        # the locked files only, SHA-256 checked
python3 assurance/sim/blender/test_fetch_assets.py            # CI: the fetcher against fake API answers
```
