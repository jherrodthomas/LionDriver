---
name: road-scene
description: Draw LionDriver's top-down road scenes, the small animated SVG (or canvas) pictures of the item's red car on a road that explain a hazardous event, a fault, a SOTIF triggering condition, a safety mechanism, a fault tolerant time interval or a threat. All scenes come from the one scene kit (assurance/01-management/figures/scenekit.py and scenekit.js), so a car, a lane and a mark mean the same thing in the HARA, SOTIF, STPA, TARA, FSC and FMEA figures. Use it whenever a figure, card, page or explorer needs a car on a road seen from above, a "what should happen vs what does" picture, a before-and-after of a mechanism, or a looping scene, even if nobody says "scenekit". For 3D or photoreal scenes use the Blender pipeline in assurance/sim/blender instead.
---

# Road scene

Every scene in LionDriver is drawn by **one kit**. `scenekit.py` draws SVG for generated figures (CI checks them),
and `scenekit.js` is its canvas twin for live pages. Both live in `assurance/01-management/figures/`, and
`scene-style.md` next to them is the style's source of truth. Read it once per session before drawing; this skill is
the working summary and the recipe.

A scene **explains a mechanism**. It is not test or simulation output, unless the sheet says it replays a run and
names the run.

## The rules, short

1. **One red car.** The item's car is red (`sk.ego_body()`) and is the only red car. Other traffic is grey
   (`sk.other_body()`). A stopped car is paler with hazard lights (`other_body(stopped=True)`).
2. **Green is what should happen, red is what does.** `intended_path` is dashed green, as is the `ghost_body()`
   outline of where the car should be. `performed_path` is solid red, drawn in as the car drives. `gap_band` shades
   the difference. Charts over a scene use `sk.REQ` / `sk.PERF` on white.
3. **One fault, one moment.** `fault_marker` (amber, bolt) is where the failure or triggering condition starts.
   `callout` (yellow ring and label) is the first moment that matters. Each appears at most once per scene.
4. **Pills top-left, in order of appearance.** Styles: `drv` blue for the driver, `bad` dark red for what goes
   wrong, `ok` green for what holds, `info` slate for context. Number them (`num=`) only when they key to marks on a
   chart beside the scene.
5. **Loops end where they matter.** Every scene loops in `sk.DUR` = 6 s: `sk.DRIVE` = 80 % driving, then a hold. A
   viewer that does not animate shows the static pose, so **every animated element's static pose is its end state**.
   The kit's helpers do this for you; hand-written `<animate>` elements must too.
6. **Readable text.** Labels and pills keep their reading size; they are not scaled with the large scene. Light text
   on asphalt gets `halo=True`.
7. **Never copy the palette.** `test_scenekit.py` fails if any generator under `assurance/` or `docs/` draws the
   road from its own colour copy. A missing element goes into the kit (both halves), not into a figure.

## Pick the size

| Size | Units | Use for | Calls |
|---|---|---|---|
| Full | 280 × 130 | one scene per card | `straight_road()`, `curved_road(edge)`, `single_lane_road(d)` |
| Strip | 280 × 80 | two scenes per card (today / with a change) | `strip_road()`, coordinates `STRIP_*`, height `STRIP_H` (never a fixed 70) |
| Large | 460 × 250 | cards drawn in 460 × 250 (STPA, TARA, FSC) | `large_road()`, cars and marks scaled by `LARGE_K` |

Geometry of the full scene: traffic drives left to right, lanes are 30 units (about 3.6 m), the ego lane centre is
`sk.EGO_LANE` = 84 and the other lane `sk.OTHER_LANE` = 54. The centre line is at 69, and the edges at 39 and 99.

## Recipe (SVG figure)

`templates/fig_scene_template.py` is a working generator: a sheet of cards, one full scene each, with the scenes as
**data**. Each scene has its path, the fault's x, the moment, the pills, the other traffic, and a phrase quoted from
the source. `templates/test_fig_scene_template.py` checks the style rules on the output. Both pass as they are,
which shows the pattern before you change it.

1. Read the analysis row the scene explains (the HE-, SH-, TC-, FM-, UCA- or threat row) and get the facts from it:
   what fails, when, what should happen, what does, and the number that matters (the FTTI, a deviation in metres, a
   time). Put a phrase from that row in `quote`, so a reworded row fails the build.
2. Copy both templates into the work product's `figures/` folder, rename them (`fig_<wp>_<topic>.py`), and fill in
   the header, `SOURCE` and `SCENES`. Coordinates are scene units; keep paths inside 14 ≤ x ≤ 262 so the car stays
   on the sheet.
3. Timing is by position. `key_for(path)` maps x to loop time, so the fault marker and the callout appear as the car
   reaches them. For time-keyed motion (stops, pedestrians, a car that waits) use `sk.drive_t`,
   `sk.drive_turning` and `sk.track`, with samples `(drive share 0..1, x, y)`.
4. Run it, then look at **both** the still frame and a mid-loop frame:
   ```bash
   node .claude/skills/assurance-figure/scripts/preview.mjs <scratchpad>/png path/to/fig-….svg
   node .claude/skills/assurance-figure/scripts/preview.mjs <scratchpad>/png path/to/fig-….svg --at 2.5
   ```
   Then Read the PNGs. The still must show the car at its end, every mark and pill present, and labels clear of cars
   and pills. Mid-loop, the red track must follow the car and the marks must appear only once the car reaches them.
5. Everything the `assurance-figure` skill requires still applies: the terms footer and `terms.FIGURES`, `--check`,
   the test, the CI line in `.github/workflows/assurance.yaml`, alt text with the facts, and a caption naming the
   generator.
6. **Add the generator to the "Who uses it" table in `scene-style.md`.** `test_scenekit.py` fails until every
   generator that imports the kit is listed there. Then run:
   ```bash
   python3 assurance/01-management/figures/test_scenekit.py
   ```

## Recipe (live page, canvas)

For an explorer, a mockup or an artifact that animates a scene live, inline `scenekit.js` (it contains no closing
script tag) and draw in scene units:

```js
const k = scenekit, SK = k.SK;
const { ctx } = k.frame(canvas, SK.W, SK.H);
k.straightRoad(ctx, { dashOffset: travelled });
k.intendedPath(ctx, [[14, 84], [262, 84]]);
k.performedPath(ctx, track);
k.car(ctx, x, y, heading, "ego");
k.badges(ctx, [[1, "lead brakes", "drv"], ["stays engaged", "bad"]]);
```

Drive the motion from the model the page shows (a plant step, a recorded run), never from hand-tuned easing, and
label the page "Synthetic data, no evidence credit" when the numbers are simulated.

## Changing the kit itself

Change `scenekit.py` and the matching drawing in `scenekit.js` together. If a colour, a geometry value, a size or
the timing changed, run `python3 scenekit.py --js` to rewrite the JS constants block. Then regenerate every scene
figure (the commands are in the `scene-style.md` table), look at them, and run `test_scenekit.py`. Every scene in the
project changes with the kit, so check them all before committing.
