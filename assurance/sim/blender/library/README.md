# Scene library

The parts the hazardous-event scenes are built from ([`../scenes.yaml`](../scenes.yaml), [`../README.md`](../README.md)).
A scene is **environment + condition + traffic + motion source**, so one hazardous event can be drawn under every
weather or lighting code it is rated for. Pictures only: synthetic (DSR-12), no evidence credit.

| File | Holds | Used by |
|---|---|---|
| [`environments.yaml`](environments.yaml) | 14 static worlds: cross-section, geometry, scenery, road furniture, the operational situations (OS-) they represent, the conditions each allows | `export_scene.py` |
| [`conditions.yaml`](conditions.yaml) | W01 to W06 of the HARA and the TC-01 low-sun preset: exposure, ODD, what the HARA model changes, and the look | `export_scene.py`, `hazard_scene.py` |
| [`traffic.yaml`](traffic.yaml) | Illustrative traffic presets placed relative to the ego | `export_scene.py` |
| [`assets.yaml`](assets.yaml) | CC0 sky HDRIs, ground textures, scanned plants and street furniture (Poly Haven, ambientCG) with candidate IDs and a search fallback; CC-BY 4.0 model kits (buildings, cars, a trailer) from the private LionDriver-assets repository (section 5) | `fetch_assets.py`, `hazard_scene.py`, `scenery_kits.py` |
| [`people/`](people/README.md) | Two CC0 pedestrian figures (Quaternius) with a walk cycle, built by `people/build_people.py` and committed | `hazard_scene.py` |
| `assets.lock.json` | The asset IDs and SHA-256 sums `fetch_assets.py` chose; committed once it has run (section 4) | `fetch_assets.py --locked`, `hazard_scene.py` |

![Dashboard of scene HE-04.2 under condition W02: the orange ego Corolla braking in a left highway curve on wet, glossy asphalt with puddles under an overcast sky, its follower 22.5 m behind; panels around the 3D view give the hazardous event, ego state, plots and a filmstrip](../dashboards/he-04-2-wet-curve-braking.jpg)

![Dashboard of scene SH-12 under condition W03: the ego at night on a moonlit highway, headlights on the barrier as it drifts out of a left curve with the driver inattentive and undetected](../dashboards/sh-12-unsupervised-night.jpg)

*The same library under two conditions of §2: W02 wet road ([HE-04.2](../dashboards/he-04-2-wet-curve-braking.jpg)) and W03 night ([SH-12](../dashboards/sh-12-unsupervised-night.jpg)). Synthetic, no evidence credit.*

## 1. How a scene uses it

```yaml
- id: he-02-4-silent-loss-truck
  environment: highway-free-flow     # road, scenery, props; must allow the condition
  conditions: W01                    # the default
  traffic: free-flow                 # optional; illustrative road users around the ego
  variants: [W02, W03, W04, W05]     # also render he-02-4-silent-loss-truck--w02 ... --w05
  actors: [...]                      # the scene's own road users, added after the preset's
```

The scene's own `road:` fields override the environment's (for example `geometry: "curve@1.5"`). Its `props:`,
`env:` and `actors:` are added to the environment's, the condition's and the preset's. `test_scenes.py` checks that:

- every scene names an environment;
- each scene and variant uses a condition its environment allows;
- a plant case drives the geometry its environment has;
- the W-codes match `hara_model.py` (exposure and ODD);
- traffic is never the critical road user or the contact;
- every variant has its base scene's motion, events and contact.

## 2. Conditions

A condition changes the picture only. The plant's tyre model is linear with no friction limit, and the kinematic
scenes use their stated accelerations, so the motion is the same under every condition. The dashboard and the
gallery say so.

| Code | Condition | Exposure | ODD | Drawn as |
|---|---|---|---|---|
| W01 | Dry, daylight | E4 | in | Clear sky, sun at 30° behind |
| W02 | Wet road or light rain | E3 | in | A darker overcast, a water film on the asphalt with streaky reflections along the road, puddles, light rain, haze (1.5 km) |
| W03 | Night, dry, headlights | E3 | in | Moonlit sky, headlights and tail lamps, street and road lighting where the environment has it, glare |
| W04 | Moderate or heavy rain | E2 | outside | The darkest overcast, standing water with longer streaks and mirror-smooth wheel tracks, a rain ripple, heavy rain, visibility 350 m, lights on |
| W05 | Snow or ice | E2 | outside | Overcast, snow on verges and trees, slush between the wheel tracks, icy tracks, snowfall, visibility 600 m |
| W06 | Fog below the ODD bound | E1 | outside | A slightly darker overcast, fog at 120 m visibility (the ODD bound is 200 m, WP-C-02 §3), lights on |
| TC-01 | Low sun in the camera's view | — (SOTIF; no class. Sun in the frame on I-85 about 203 h/year southbound, 158 h/year northbound: [sun-glare.md](../../results/sun-glare.md), synthetic, no evidence credit) | in | Sun 5° above the horizon ahead (12° where buildings would hide it), bloom |

Fog and haze are a volume over the scene with extinction 3 / visibility per metre (Koschmieder: 5 % contrast at the
stated visibility).

From wet 0.75 on (W02, W04) the asphalt is a water film (`scene_assets._wet_sheen`): its roughness is anisotropic
with the tangent along the road (the road UV's v), so the lamps, lights and sky reflect as long streaks; the wheel
tracks get a lower roughness floor (0.07 at W02, 0.03 at W04; puddles 0.02) and rain adds a fine ripple to the
normal. W04 stretches further and is smoother than W02. Below 0.75 (W01 dry, W05, W06) the road is drawn as before.
`sky_strength` in a condition's `env` dims the overcast sky (W02 0.8, W04 0.7, W06 0.85); W01 keeps its clear sky.

The road edges follow the "City Road Builder" look the lead preferred, built from our own cross-section
(`scene_assets.edge_features`, visual only): a raised concrete kerb, 15 cm high and 25 cm wide with a chamfered top,
along the highway's left verge and on the right at the shoulder's outer edge, or just behind the barrier's posts where
the barrier stands on that edge; a kerb stone at the road edge of every urban sidewalk; and, where an environment sets
`walkway_m` (`highway-interchange`), a paved walkway of concrete flags behind the right kerb. The kerbs and walkway
use the `concrete` slot (the walkway with joints cut every 0.6 m), or the procedural concrete without it. Highway
street lights (`lamps` props: `highway-free-flow`, `highway-curve`, `highway-interchange`) are a row of 10 m tapered
poles every 45 m beyond the barrier, the arm curving 2.6 m out over the road to a slim luminaire, lit at night; a post
that would stand near the chase camera or on its line of sight to the ego is left out (`street_layout.lamp_row`,
checked by `test_scenes.py`).

Around the road, `scene_assets.build_surroundings` draws what the environment and the condition switch on (all on
where they fit, from the lead's choice of the environment-realism mockup). Each is a key of an `env` block:

| Key | Set in | What it draws | Where it is on |
|---|---|---|---|
| `horizon` | environment | Patchwork far fields to 2 km, a tree line about 1 to 1.6 km out, hills 2 to 5.6 km out, round the chase camera | every highway and rural environment |
| `haze_km` | condition | With `horizon`, a thin blue haze for that visibility, 160 m deep so the sky above stays clear | W01, TC-01 (22 km) |
| `terrain` | environment | `rolling`: ground rolling from 15 m past the verge; `ditch`: and a shallow drainage ditch 7 to 10 m past the verge; `embankment`: the road on a 3 m bank on the left, in a 4.5 m cutting on the right. Trees, lamps and posts stand on it | `embankment`: free-flow, crosswind; `ditch`: rural; `rolling`: the other highways but the tunnel |
| `verge_plants` | environment | 3D grass blades, weeds and wildflowers on both verges within 40 m of the road along the stretch the chase camera sees, thinning into the ground texture (none under snow) | every highway and rural environment |
| `distant` | environment | `pylons` (a line of lattice pylons with sagging wires), `billboard` (22 m past the verge), `farm` (barn, house and silo 150 m out), `flyover` (about 380 m ahead, past the modelled road) | highway and rural, as `environments.yaml` lists |
| `cloud_shadows` | condition (an environment may set `false`) | Soft cloud shadows from a shadow-only layer 450 m up, drifting at 6 m/s | W01; not in the urban environments |
| `spray` | condition | 0 to 1: a plume of spray behind the wheels of every moving car and truck | W02 (0.45), W04 (1.0) |
| `road_wear` | environment | Repair patches, cracks, sealed joints, faint skid marks, road studs on the lines (manhole covers in town), flat under the markings | every environment |
| `camera_feel` | environment | A vignette and film grain in the compositor (not on the top view) and mild depth of field on the chase camera, focused on the ego | every environment |

Like the kerbs, these are visual only: the ground changes height only from 7 m past the verge start, the objects stand
at least 20 m past the verge or beyond the modelled road, the wear is flat texture on the asphalt, and `export_scene.py`
never reads them. `test_scenes.py` exports every scene with all of these keys removed and checks that the motion,
events, contact, gap, TTC, poses, cross-section and props are the same.

## 3. Environments and traffic

| Environment | Situations | Conditions |
|---|---|---|
| `highway-free-flow` | OS-01, 05, 07, 08, 09, 10, 12, 13, 17, 18 | all |
| `highway-curve` | OS-02 (curve near R_ODD) | all |
| `highway-interchange` | OS-01, OS-08 (overpass, gantry, lighting) | all |
| `highway-queue` | OS-06, OS-07 | all |
| `highway-worn-markings` | OS-01 with TC-05 | all but W05 (snow hides the markings the scene is about) |
| `highway-construction` | OS-14 with TC-06 (cone taper, drums) | all but W05 |
| `rural-undivided` | OS-03 | all |
| `rural-curve` | OS-16 | all |
| `urban-arterial` | OS-04, OS-06 | all |
| `urban-intersection` | OS-15 | all |
| `highway-narrow-truck` | OS-01, OS-02 with TC-32 (a 3.1 m lane, a barrier 0.6 m beyond the shoulder line, a truck alongside) | all |
| `highway-crosswind` | OS-01, OS-02 with TC-15 (open embankment, windsocks, a wind sign) | all |
| `highway-tunnel` | OS-01, OS-02 with TC-18 (a lit tunnel under a hill; its roof is hidden from the top camera) | all |
| `highway-exit-split` | OS-01 with TC-31 (the right lane splits off as an exit: gantry and chevron gore) | all |

Triggering conditions are drawn, not simulated, except the crosswind or bank of TC-15, which the plant can add as a
steady lateral push (`ay_disturbance`). TC-17 (a crest hiding a lead) is not pictured: the roads are flat, and a
vertical profile would need the road, the cars and the cameras to follow it.

Traffic presets: `none`, `free-flow`, `dense`, `adjacent-truck`, `close-follower`, `cut-in`, `oncoming`, `parked`.
A variant moves each preset road user by up to the preset's `jitter_m` along the road (seeded by the variant's ID),
so the same event under another condition does not look copied.

## 4. CC0 assets

```sh
python3 assurance/sim/blender/fetch_assets.py --check-hosts   # api.polyhaven.com, dl.polyhaven.org, ambientcg.com
python3 assurance/sim/blender/fetch_assets.py                 # resolve, download, write assets.lock.json
python3 assurance/sim/blender/fetch_assets.py --locked        # the locked files only, SHA-256 checked
```

Each slot tries its candidate IDs in order. When none resolves, it searches the source's API and takes the most
downloaded match. Files go under `assurance/sim/assets/library/<slot>/`, which is git-ignored. Every asset on both
sites is CC0 1.0. `hazard_scene.py` uses a slot only when all its files are on disk. Otherwise it falls back to the
procedural look: noise-varied asphalt with grain, stones, bump and polished wheel tracks; varied grass with dry
patches; voronoi gravel; concrete slabs; a Nishita or overcast sky; lumpy-crowned trees and stacked-cone conifers,
with no verge grass. The wet, snow and ice layers apply to both.
Road surfaces carry UVs in metres (u lateral, v along the road), so a texture follows the road round a curve and
its tangent-space normal map is correct.

**Fetched (2026-10-18)**, all CC0 1.0; `assets.lock.json` holds the files and their
SHA-256. Tile sizes are the ones each source publishes.

| Slot | Asset | Tile |
|---|---|---|
| `hdri_clear` | Poly Haven [`kloofendal_48d_partly_cloudy_puresky`](https://polyhaven.com/a/kloofendal_48d_partly_cloudy_puresky) | 2k HDR |
| `hdri_overcast` | Poly Haven [`overcast_soil_puresky`](https://polyhaven.com/a/overcast_soil_puresky) | 2k HDR |
| `hdri_low_sun` | Poly Haven [`spruit_sunrise`](https://polyhaven.com/a/spruit_sunrise) | 2k HDR |
| `hdri_night` | Poly Haven [`dikhololo_night`](https://polyhaven.com/a/dikhololo_night) | 2k HDR |
| `asphalt` | Poly Haven [`asphalt_02`](https://polyhaven.com/a/asphalt_02) | 3 m, 2k |
| `grass` | ambientCG [`Grass004`](https://ambientcg.com/view?id=Grass004) | 1.4 m, 1K |
| `gravel` | Poly Haven [`gravel_floor_02`](https://polyhaven.com/a/gravel_floor_02) | 2 m, 1k |
| `concrete` | ambientCG [`Concrete034`](https://ambientcg.com/view?id=Concrete034) | 1.1 × 0.55 m, 1K |
| `snow` | Poly Haven [`snow_02`](https://polyhaven.com/a/snow_02) | 2 m, 1k |

The offline picks were checked against the sites' previews before locking. Three were replaced:
`aerial_grass_rock` (a 15 m aerial of mostly bare earth) by `Grass004`, `gravelly_sand` (orange desert sand) by
`gravel_floor_02`, and `concrete_floor_02` (a stained floor) by `Concrete034`; after a test render, `moonless_golf`
(floodlights on its horizon, which drew as a glowing patch in the sky) by `dikhololo_night`. Test renders then showed the asphalt scan about
2.5 times brighter than fresh asphalt and the grass scan glossy enough to shine at grazing angles, so the slots
carry a `tint` (asphalt 0.5, gravel 0.45) and a `roughness_min` (grass 0.8), which `fetch_assets.py` copies into the
lock.

**Plants (2026-10-18).** The `model` slots are scanned Poly Haven plants, fetched as glTF with their 1k textures
(`textures/` beside the `.gltf`, as the glTF expects). Each mesh in a glTF is a variant; it is imported once, kept out
of the scene, and every instance shares its mesh data, as the road users share the Corolla mesh.

| Slot | Asset | Use |
|---|---|---|
| `tree_broadleaf_a` | Poly Haven [`island_tree_02`](https://polyhaven.com/a/island_tree_02) | Broadleaf trees, 6 to 8.4 m |
| `tree_broadleaf_b` | Poly Haven [`tree_small_02`](https://polyhaven.com/a/tree_small_02) | Broadleaf trees, 6 to 8.4 m |
| `tree_conifer` | Poly Haven [`fir_sapling_medium`](https://polyhaven.com/a/fir_sapling_medium) (3 variants) | Conifers, 6.4 to 9 m |
| `shrub` | Poly Haven [`shrub_02`](https://polyhaven.com/a/shrub_02) (4 variants) | Under the trees of a tree-lined road |
| `verge_short` | Poly Haven [`grass_bermuda_01`](https://polyhaven.com/a/grass_bermuda_01) (17 clumps) | First metre of a rural or highway verge |
| `verge_meadow` | Poly Haven [`grass_medium_02`](https://polyhaven.com/a/grass_medium_02) (5 clumps) | 0.5 to 6.5 m beyond the road edge, thinning out into the field |

A scanned tree stands exactly where the procedural tree would, so switching between the two looks does not move
anything in a scene. Where a role's slot is missing, that role falls back to the procedural look on its own. Verge
grass is scattered by geometry nodes on rural and highway verges. It is left out under snow, which would cover it,
and on urban streets, which have pavements. Under snow the plants' own materials get snow on their upward-facing
parts. With the `grass` texture, the fields also get 50 to 100 m dry patches and faint mowing rows beyond the verge.

Cost, measured on 1280 × 720 chase stills at 16 samples on 4 CPU cores: Poly Haven ships only the full-detail mesh,
0.4 to 2 million triangles a tree. Peak memory goes from about 1.5 GB to 4.4 GB for each Blender process, and a still
takes about 12 to 20 s longer (23 to 37–42 s; 47 to 65 s with snowfall). Building a scene takes about 14 s longer, once
per scene. Leave the plant slots unfetched, or delete their folders, to render with the procedural trees.

**Street furniture (2026-10-18).** Urban pavements are laid out by [`../street_layout.py`](../street_layout.py), which
is plain Python, so CI checks every urban scene (`test_scenes.py`). Each side gets street trees in kerbside pits about
every 36 m, the two sides staggered (the scanned broadleaf trees at 0.75 of their height, or the procedural tree). It
also gets lamp columns every 30 m with a bin by most of them, benches facing the carriageway, hydrants at the kerb,
street cabinets against the buildings, and a bus stop 45 m (left) and 95 m (right) ahead of the ego's start, then
every 180 m. Nothing stands within 6 m of any pedestrian or cyclist pose, across an intersection (plus 6 m), within
3 m of a traffic light or within 6 m of a crosswalk. Furniture must not hide a road user the scene does not already
hide.

| Slot | Asset | Use |
|---|---|---|
| `bin` | Poly Haven [`metal_trash_can`](https://polyhaven.com/a/metal_trash_can) (clean and rusted) | By the lamp columns |
| `bench` | Poly Haven [`modular_street_seating`](https://polyhaven.com/a/modular_street_seating) (the bench with a back) | Facing the carriageway |
| `hydrant` | Poly Haven [`fire_hydrant`](https://polyhaven.com/a/fire_hydrant) | At the kerb |
| `utility_box` | Poly Haven [`utility_box_01`](https://polyhaven.com/a/utility_box_01) | Against the buildings |

The lamp columns (10 m tapered poles whose 2 m arm curves over the carriageway, with a point light at night) and the glass bus shelters
(with a bench, a lit advert and the stop sign) are procedural. Poly Haven has only 3.9 m heritage lamp posts and no
shelter. The furniture models are small (4,000 to 75,000 triangles), so render time and memory do not change.

## 5. CC-BY kits and render-only extras

Busy streets, farmsteads and varied traffic come from seven Sketchfab model kits under **CC-BY 4.0**. Each was
checked to be its author's own work (a portfolio of originals, no game rips). The project lead downloaded them on
2026-10-22. They live in the private repository `jherrodthomas/LionDriver-assets` under `sketchfab/`, with a
`SHA256SUMS` file, because some are bigger than this repository should hold.

`fetch_assets.py` unpacks a kit slot from a local clone of that repository (`LIONDRIVER_ASSETS_REPO`, else a
`liondriver-assets` folder beside this one). It first checks the zip against `SHA256SUMS`, then records the SHA-256 of
the zip and of every unpacked file in `assets.lock.json`; `--locked` unpacks again and checks them. Without the
clone the scenes keep the procedural look.

**Credits.** A render that shows these models must credit them. The gallery and the dashboards carry this table.

| Slot | Model (Sketchfab) | Author | Used for |
|---|---|---|---|
| `city_brownstones` | [Brownstone Building Set - Low poly model](https://sketchfab.com/3d-models/b15e6344acd844eabc823e1cc8332574) | DanielZhabotinsky | Brownstone rows on urban streets |
| `city_chicago` | [Realistic chicago buildings](https://sketchfab.com/3d-models/c4a3993ef1e84e6d9d5a15c78da88aae) | 99.Miles | A pair of commercial buildings among them |
| `city_downtown` | [Downtown Buildings Set - Low Poly model](https://sketchfab.com/3d-models/7378e7fb9c914c39880d9913a6f4e1d6) | DanielZhabotinsky | Office blocks on the street, towers beyond it |
| `rural_buildings` | [Rural Buildings Set - Low Poly models](https://sketchfab.com/3d-models/51ab7e74bac347a89725f1d22b928edf) | DanielZhabotinsky | Farmstead, roadside diner and stores |
| `grain_bins` | [Panola Grain Bins](https://sketchfab.com/3d-models/342892c5b0ff4519a2327d05316e266c) | frankmcmains | Grain bins on the farmstead |
| `car_pack` | [Generic passenger car pack](https://sketchfab.com/3d-models/20f9af9b8a404d5cb022ac6fe87f21f5) | comrade1280 | Traffic, parked and passing cars (nine shapes, no real makes) |
| `box_trailer` | [Truck Trailer FREE](https://sketchfab.com/3d-models/575958a53e3d4e9f8bcfb1ee2cef67bf) | NLM-Group | A 53 ft box trailer behind traffic trucks |

All seven are [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/). The pedestrians are the CC0 Quaternius
figures of `people/`. The Brooklyn street-row kit is in the private folder but not used, because its facades carry
graffiti. The gas station and the overpass from the shortlist are not used yet: one came as a `.rar` inside its zip,
the other is over GitHub's 100 MB file limit.

**What the extras are.** [`../street_life.py`](../street_life.py) plans them, in plain Python so CI checks every
scene. [`../scenery_kits.py`](../scenery_kits.py) draws them in Blender. Each is a key of an environment's `env`:

| Key | What it draws | Where it is on |
|---|---|---|
| `city_blocks` | Brownstone, Chicago and office buildings shoulder to shoulder on both building lines, in place of the procedural boxes, breaking for every cross street and crosswalk; towers beyond the end of the street | urban |
| `street_life` | `dense` or `light`: cars in the parking lanes, cars driving the oncoming lanes, and people walking the pavements both ways or waiting at the corners of a cross street | urban (`dense`) |
| `farmstead` | A farm (house, barns, sheds, grain bins) about 30 m past the verge on one side, and a diner or stores with parked cars about 16 m past it, ahead of the chase camera, standing on the terrain | rural |
| `traffic_skins` | The traffic cars drawn with the car pack, so a street is not all Corollas, each scaled to the length of the car outline the analysis uses (4.63 m), so a skin never reaches past its road user. The ego and the critical road user keep the Corolla | every environment |
| `trailers` | A box trailer behind each traffic truck, the truck's cab kept, where no road user follows closely enough to touch it | highway |

**They never change the analysis.** `export_scene.py` never reads any of this, and a skin or a trailer is drawn on a
road user's own animated root, so its poses do not move. Nor may an extra change what a scene shows.
`test_scenes.py` checks every scene's plan:

- no extra stands near the chase camera or on its line of sight to the ego at any frame;
- a passing car stays 8 m from every scene road user at the same frame;
- a pedestrian stays 2.5 m from every road user at the same frame, 6 m from every pose of a scene pedestrian or
  cyclist, and clear of the street furniture;
- a parked car stays 6 m from every pose of every road user, and out of the cross streets;
- a building row breaks for every intersection and crosswalk;
- the ego and the critical road user are never skinned or given a trailer.

The same test exports every scene with these keys removed and checks that the analysis is unchanged.

Scans carry daylight in their colour maps, so at night they are dimmed; under snow their roofs get snow. People are
cloned from the two figures, each with its own rig, walk and shirt colour. A 1280 × 720 chase still of
`sh-09-red-light`, with 30 buildings, 36 parked and 5 passing cars and 57 people, builds in about 25 s and peaks at
6.2 GB, against about 5 GB without the extras.

