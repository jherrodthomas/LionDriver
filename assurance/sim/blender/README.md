# Hazardous-event scenes in Blender

| Field | Value |
|---|---|
| Scope | Pictures of HARA hazardous events (HE-) driven by layer-1 plant runs: an animated Blender scene per event and a review dashboard (stills and clip) |
| Version | 0.1 (2026-10-18) |
| Status | Draft. AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed. Synthetic (DSR-12): **pictures only, no evidence credit** |
| Feeds | Review of the HARA and the WP-V-03 scenarios; figures. Nothing in the safety case |

![Dashboard of HE-01.2, hard-over beside an adjacent car](../figures/fig-he-01-2-dashboard.png)

## 1. What it shows, and what it does not

The ego car's motion, the panda and driver events and, in longitudinal cases, the lead and follower come from a
[plant](../plant/) run: the real panda safety code in the loop, under the assumptions stated in
[plant-results.md](../results/plant-results.md). Blender only draws them. A road user marked **illustrative** in
[`scenes.yaml`](scenes.yaml) is drawn at constant speed in its lane and is not simulated, and the plant does not model
contact: a scene ends shortly after the first overlap of body boxes (or of the body and the barrier), labelled "not
modelled". Layer 1 has no perception (openpilot is replaced by a perfect-perception controller), so the dashboard has
no perception, camera-detection or sensor-fusion panel; the forward view is a render, not openpilot's input.

## 2. Pipeline

| Step | Script | Runs in | Writes (all under `out/<scene>/`, git-ignored) |
|---|---|---|---|
| 1 | [`export_scene.py`](export_scene.py) | the track's Python (needs the plant: `opendbc_repo`, `panda`, [`../requirements.txt`](../requirements.txt)) | `scene.json`: road, poses at 24 fps, signals, events, the HE's HARA text |
| 2 | [`hazard_scene.py`](hazard_scene.py) | Blender 4.2+ (`blender -b -P`) or Python 3.13 with `pip install bpy` | `scene.blend` (animated, three cameras), `screen.json`, `stills/`, `frames/` with `--video` |
| 3 | [`compose.py`](compose.py) | Python with Pillow; ffmpeg for `--video` | `dashboard/`, `dashboard.png`, `<scene>.mp4` |

```sh
python3 assurance/sim/blender/export_scene.py                                   # all scenes
blender -b -P assurance/sim/blender/hazard_scene.py -- assurance/sim/blender/out/he-01-2-hardover-adjacent/scene.json --stills --video
python3 assurance/sim/blender/compose.py assurance/sim/blender/out/he-01-2-hardover-adjacent --video
python3 assurance/sim/blender/test_scenes.py                                    # CI: scenes.yaml resolves and exports
```

Rendering is Cycles on the CPU, so it runs headless without a GPU: about 4 s per 1280×720 still at 16 samples on 4
cores, and about 10 minutes for a 4-second clip with all three views.

## 3. The car

The ego is the purchased Corolla E210 mesh when `assets/1450755-gltf-extended.glb` is present (or `--vehicle PATH`, or
`LIONDRIVER_VEHICLE_GLB`); the script centres it on the ground and turns it to face forward, finding the front by the
lower bonnet end (override with `--front`). Without it, and for every other car, it is a stand-in lofted from the
committed outline [`../figures/corolla-e210-silhouette.json`](../figures/corolla-e210-silhouette.json). The GLB is a
Git LFS file in the private `jherrodthomas/LionDriver-assets`: GitHub's "Download ZIP" holds only the LFS pointer, so
fetch the file itself. Renders made with it may be published; a `scene.blend` made with it holds the licensed mesh and
stays private ([assets/README.md](../assets/README.md)).

## 4. Adding a scene

Add an entry to [`scenes.yaml`](scenes.yaml): the HE, the plant case that drives the ego, the window around the fault,
the road layout and any illustrative actors. Pick a case whose fault and road match the HE's situation; where none
does (urban, rural or oncoming-traffic situations, which the highway plant does not model), the scene waits for a
plant case rather than borrowing one.

| Scene | HE | Plant case | Road users |
|---|---|---|---|
| `he-01-2-hardover-adjacent` | HE-01.2 lateral departure into an adjacent vehicle or barrier | F-01b hard-over within the envelope | adjacent car (illustrative) |
| `he-02-1-eps-loss-curve` | HE-02.1 straight on in a curve | F-07 EPS fault with loss of assist | none |
| `he-04-1-step-decel-follower` | HE-04.1 rear impact by a close follower | L-03 deceleration step at the envelope minimum | lead and follower (plant) |
