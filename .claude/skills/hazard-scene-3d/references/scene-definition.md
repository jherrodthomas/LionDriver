# Defining a scene

The full field list is the header comment of `assurance/sim/blender/scenes.yaml`; the library is
`assurance/sim/blender/library/README.md`. This page is the short version and the parts that are easy to get wrong.

## A scene is environment + condition + traffic + motion

```yaml
- id: he-02-4-silent-loss-truck        # folder name in out/ and dashboards/; he-NN-N-slug, sh-NN-slug, ec-NN-slug
  he: HE-02.4                          # or sotif: {id: SH-NN, title, situation, effect, s, c}; edge_case: EC-NN
  case: F-04b                          # plant (default): a catalog case of faults.yaml / plant/cases.py
  case_overrides: {speed_kph: 100}     #   fields of that case changed for this scene
  assumptions: {driver_t_r_s: 1000}    #   plant assumptions changed (1000: a driver who does not react)
  environment: highway-free-flow       # library/environments.yaml; must allow the condition
  conditions: W01                      # library/conditions.yaml; W01 is the default
  traffic: free-flow                   # library/traffic.yaml preset; never the critical road user or the contact
  variants: [W02, W03, W04, W05]       # rendered as <id>--w02 … with the base scene's motion and outcome
  actors: [...]                        # the scene's own road users; one has critical: true (gap and TTC are to it)
  tc: [TC-..]  ks: [KS-..]             # shown on the dashboard
  window: [-1.5, 6.0]                  # seconds around the trigger (t = 0)
  caption: >-                          # what happens, in plain words; name every illustrative road user
```

A kinematic scene sets `motion: kinematic` and an `ego:` block (`speed_kph`, `accel` steps, `lateral` laws `hold`,
`drift`, `track`, `walk`), with values written as numbers or expressions over the named assumptions of
`export_scene.py` (`t_r`, `t_r_min`, `a_item_max`, `a_item_min`, `a_driver_full`, `a_pcs`, …).
`test_kinematic_values_resolve` checks two of them; `export_scene.py` fails (NameError) on an unknown name.

Actor fields `paint`, `yaw_deg`, `beacons` and `body` (the civil-vehicles kit: fire truck, police sedan, ambulance,
tow truck) change the picture only.

## Where the facts come from

| Entry | Source the scene reads (export_scene.py fails on a bad reference) |
|---|---|
| HE- | `assurance/trace/items/hazards.yaml` (WP-C-03 HARA); ratings via `assurance/02-concept/hara/hara_model.py` |
| SH- | WP-C-05 as written in the `sotif:` block; `SH-new` with no `s`, `c` = not rated; `proposed: DQ-…` = rated but not accepted |
| TC- / KS- | WP-C-06 triggering conditions, WP-V-03 known scenarios |
| EC- | `assurance/sim/results/edge-cases.md`; `search/test_search.py` checks the scene reproduces the row's rho |
| Plant cases | `assurance/sim/faults.yaml`, `assurance/sim/plant/cases.py`; extensions in blender README §4 |

## Choosing an environment and condition

Pick the environment whose operational situations (OS-) match the entry (library README §3 lists 14, including
four for SOTIF triggering conditions: `highway-crosswind` TC-15, `highway-tunnel` TC-18, `highway-exit-split` TC-31,
`highway-narrow-truck` TC-32). Its `conditions` list must allow the condition (`highway-worn-markings` and
`highway-construction` exclude W05).

| Code | Condition | Exposure | ODD |
|---|---|---|---|
| W01 | Dry, daylight | E4 | in |
| W02 | Wet road or light rain | E3 | in |
| W03 | Night, headlights | E3 | in |
| W04 | Moderate or heavy rain | E2 | outside |
| W05 | Snow or ice | E2 | outside |
| W06 | Fog below the 200 m ODD bound | E1 | outside |
| TC-01 / TC-01-NB | Low sun in the camera's view (SOTIF; no class) | — | in |

`test_library_matches_the_hara` fails if these codes drift from `hara_model.py`; fix the library, never the test.

**Add a variant only** where the HARA model changes the rating for that condition (snow or ice raises C; wet or
heavy rain changes braking in a curve; heavy rain and fog raise C for lost deceleration), or where the condition is
the SOTIF hazard's triggering condition. A variant moves preset traffic by up to the preset's `jitter_m`, seeded by
its ID, so it does not look copied; its own actors, motion, events and contact stay the base scene's.

TC-17 (a crest hiding a lead) is not pictured: the roads are flat. Say so rather than faking a crest.

## Look keys (render-only)

These live in an `env` block of an environment or condition and are read only by the renderer:
`horizon`, `haze_km`, `terrain`, `verge_plants`, `distant`, `cloud_shadows`, `spray`, `road_wear`, `camera_feel`
(surroundings, `scene_assets.build_surroundings`), and `city_blocks`, `street_life`, `farmstead`, `traffic_skins`,
`trailers` (CC-BY extras, planned by `street_life.py`, drawn by `scenery_kits.py`). Also `sky_strength`,
`walkway_m`, `sun` and the other fields of library README §2. A new one must be added to the `look` set in
`test_scenes.py::test_surroundings_never_reach_the_analysis` and validated there.

Placement rules the tests enforce: ground changes height only from 7 m past the verge; distant objects 20 m or more
past the verge; urban furniture 6 m from any pedestrian or cyclist pose, out of junctions (+6 m), 3 m from a
traffic light, 6 m from a crosswalk; lamp posts and extras never near the chase camera or on its line of sight to
the ego; passing cars 8 m and walkers 2.5 m from every road user at the same frame; parked cars 6 m from every pose;
the ego and the critical road user never skinned or given a trailer.

## Proving a change is render-only

`export_scene.py` is deterministic: two exports of an unchanged tree are byte-identical. So:

```bash
S=<your scratchpad>
python3 assurance/sim/blender/export_scene.py >/dev/null && rm -rf $S/before && cp -a assurance/sim/blender/out $S/before
# … make the change …
python3 assurance/sim/blender/export_scene.py >/dev/null && diff -rq $S/before assurance/sim/blender/out
```

A code-only render change must print nothing. A look-key change alters `env` (and the `condition` / `environment`
blocks that carry it), so compare every other field:

```bash
python3 - $S/before assurance/sim/blender/out <<'EOF'
import json, sys, pathlib
a, b = map(pathlib.Path, sys.argv[1:3]); look = {"env", "condition", "environment"}; bad = 0
for f in sorted(a.glob("*/scene.json")):
    x, y = json.loads(f.read_text()), json.loads((b / f.parent.name / "scene.json").read_text())
    for k in sorted((set(x) | set(y)) - look):
        if x.get(k) != y.get(k): print(f.parent.name, k); bad += 1
print("scenes:", len(list(a.glob("*/scene.json"))), "differences:", bad); sys.exit(bad > 0)
EOF
```

Then `test_scenes.py`. Record the result in the README version line ("Render-only: all N scenes export
byte-identical (`test_scenes.py`)").
