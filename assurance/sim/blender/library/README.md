# Scene library

The parts the hazardous-event scenes are built from ([`../scenes.yaml`](../scenes.yaml), [`../README.md`](../README.md)).
A scene is **environment + condition + traffic + motion source**, so one hazardous event can be drawn under every
weather or lighting code it is rated for. Pictures only: synthetic (DSR-12), no evidence credit.

| File | Holds | Used by |
|---|---|---|
| [`environments.yaml`](environments.yaml) | 10 static worlds: cross-section, geometry, scenery, road furniture, the operational situations (OS-) they represent, the conditions each allows | `export_scene.py` |
| [`conditions.yaml`](conditions.yaml) | W01 to W06 of the HARA and the TC-01 low-sun preset: exposure, ODD, what the HARA model changes, and the look | `export_scene.py`, `hazard_scene.py` |
| [`traffic.yaml`](traffic.yaml) | Illustrative traffic presets placed relative to the ego | `export_scene.py` |
| [`assets.yaml`](assets.yaml) | CC0 sky HDRIs and ground textures (Poly Haven, ambientCG) with candidate IDs and a search fallback | `fetch_assets.py`, `hazard_scene.py` |
| `assets.lock.json` | The asset IDs and SHA-256 sums `fetch_assets.py` chose; committed once it has run (section 4) | `fetch_assets.py --locked`, `hazard_scene.py` |

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
| W02 | Wet road or light rain | E3 | in | Overcast, wet glossy asphalt with puddles, light rain, haze (1.5 km) |
| W03 | Night, dry, headlights | E3 | in | Moonlit sky, headlights and tail lamps, street and road lighting where the environment has it, glare |
| W04 | Moderate or heavy rain | E2 | outside | Dark overcast, standing water, heavy rain, visibility 350 m, lights on |
| W05 | Snow or ice | E2 | outside | Overcast, snow on verges and trees, slush between the wheel tracks, icy tracks, snowfall, visibility 600 m |
| W06 | Fog below the ODD bound | E1 | outside | Fog at 120 m visibility (the ODD bound is 200 m, WP-C-02 §3), lights on |
| TC-01 | Low sun in the camera's view | — (SOTIF) | in | Sun 5° above the horizon ahead (12° where buildings would hide it), bloom |

Fog and haze are a volume over the scene with extinction 3 / visibility per metre (Koschmieder: 5 % contrast at the
stated visibility).

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
patches; voronoi gravel; concrete slabs; a Nishita or overcast sky. The wet, snow and ice layers apply to both.
Road surfaces carry UVs in metres (u lateral, v along the road), so a texture follows the road round a curve and
its tangent-space normal map is correct.

**Fetched (2026-10-18)**, all CC0 1.0, every first candidate resolved; `assets.lock.json` holds the files and their
SHA-256. Tile sizes are the ones each source publishes.

| Slot | Asset | Tile |
|---|---|---|
| `hdri_clear` | Poly Haven [`kloofendal_48d_partly_cloudy_puresky`](https://polyhaven.com/a/kloofendal_48d_partly_cloudy_puresky) | 2k HDR |
| `hdri_overcast` | Poly Haven [`overcast_soil_puresky`](https://polyhaven.com/a/overcast_soil_puresky) | 2k HDR |
| `hdri_low_sun` | Poly Haven [`spruit_sunrise`](https://polyhaven.com/a/spruit_sunrise) | 2k HDR |
| `hdri_night` | Poly Haven [`moonless_golf`](https://polyhaven.com/a/moonless_golf) | 2k HDR |
| `asphalt` | Poly Haven [`asphalt_02`](https://polyhaven.com/a/asphalt_02) | 3 m, 2k |
| `grass` | ambientCG [`Grass004`](https://ambientcg.com/view?id=Grass004) | 1.4 m, 1K |
| `gravel` | Poly Haven [`gravel_floor_02`](https://polyhaven.com/a/gravel_floor_02) | 2 m, 1k |
| `concrete` | ambientCG [`Concrete034`](https://ambientcg.com/view?id=Concrete034) | 1.1 × 0.55 m, 1K |
| `snow` | Poly Haven [`snow_02`](https://polyhaven.com/a/snow_02) | 2 m, 1k |

The offline picks were checked against the sites' previews before locking. Three were replaced:
`aerial_grass_rock` (a 15 m aerial of mostly bare earth) by `Grass004`, `gravelly_sand` (orange desert sand) by
`gravel_floor_02`, and `concrete_floor_02` (a stained floor) by `Concrete034`.
