---
name: hazard-scene-3d
description: Work on LionDriver's Blender hazardous-event scenes in assurance/sim/blender, the 3D scene and review dashboard drawn for every HARA hazardous event (HE-), every SOTIF hazard (SH-) and every edge case of the failure search (EC-). It covers how a scene is defined in scenes.yaml (an environment, a condition W01 to W06 or TC-01, traffic and a plant or kinematic motion source), the scene library, the rule that a render-only change leaves every scene's exported analysis identical (test_scenes.py), what runs without Blender and what needs it, rendering stills, dashboards and clips, the committed gallery and its claude.ai page, and the asset licences (the purchased Corolla mesh, CC0 and CC-BY kits, the credits). Use it whenever someone says "render the hazard scene", "3D scene of HE-…", "a scene for SH-…", "add a variant", "W02 version", "re-render the gallery", "dashboard", "clip", "Blender", "hazard scenes page", "fetch the assets" or "test_scenes failed", or wants a hazardous event shown in 3D or photoreal, even if nobody names a script. For flat top-down scene figures use the road-scene skill.
---

# Hazard scene 3D

`assurance/sim/blender/` draws one 3D scene and one review dashboard per HARA hazardous event, SOTIF hazard and
edge case (125 scenes with their condition variants, 31 clips). Its [README](../../../assurance/sim/blender/README.md)
and [library README](../../../assurance/sim/blender/library/README.md) are the source of truth: read both once per
session before changing anything. This skill is the working summary, the rules and the recipe.

**A scene is a picture, not evidence.** Every dashboard is synthetic (DSR-12), *no evidence credit*. Feeds: review
of the HARA, the SOTIF analysis and the WP-V-03 scenarios, and figures. Nothing in the safety case.

## The rules

1. **Name the motion source.** *Plant*: a layer-1 run with the real panda safety code under the plant's stated
   assumptions ([`../plant/`](../../../assurance/sim/plant/)). *Kinematic*: stated accelerations and a lateral law,
   no item code. Prefer a plant case whose fault and road match the entry; use kinematic only where the plant cannot
   represent the situation, and write every time and acceleration as a named assumption of `export_scene.py`
   (`t_r`, `a_item_max`, `a_driver_full`, `a_pcs`, …) where one exists. Never invent a number.
2. **Road users nobody simulates are labelled.** They are placed by hand for a qualitative analysis. The committed
   renders say *illustrative*; the next re-render and every new scene says **qualitative** (the lead, 2026-10-24).
3. **Contact is not modelled.** A scene freezes at the first overlap of two outlines, records the relative speed and
   ends 0.5 s later. Say "not modelled" for what follows; never describe damage or injury as a result.
4. **No perception.** Layer 1 has none, so a triggering condition (low sun, night, fog, faded lines, an occluding
   truck, a tunnel) is *drawn, not simulated*. Only TC-15 crosswind enters the plant (`ay_disturbance`).
5. **A condition changes the picture, never the dynamics.** The plant's tyre model is linear with no friction
   limit, so a W02 or W05 variant has the base scene's motion and outcome. The dashboard says so; so must you.
6. **The look never changes the analysis.** Everything only the picture needs is drawn outside the carriageway and
   beyond the barrier line, or lives in look keys of an `env` block that `export_scene.build` never reads. A
   render-only change must leave every scene's exported analysis identical. See "Checks" below.
7. **Ratings are the records'.** The card shows the HARA (WP-C-03) or WP-C-05 entry as it stands, proposals
   marked as proposals. A scene never re-rates anything; a new hazard (`SH-new`, `proposed: DQ-…`) goes to the lead
   through the `decision-inbox` skill.
8. **Licences.** No licensed mesh, `.blend` or CC-BY kit file is ever committed; renders that show the kits carry
   their credits. See [references/assets-and-licences.md](references/assets-and-licences.md).

## What runs here and what needs Blender

| Step | Script | Needs | Here (cloud container) |
|---|---|---|---|
| 0 | `fetch_assets.py` | network; a clone of private `LionDriver-assets` for the CC-BY kits | `--check-hosts` works; no kit clone, no Corolla GLB |
| 1 | `export_scene.py` | the sim track's Python: `git submodule update --init --depth 1 opendbc_repo panda` and `pip install -r assurance/sim/requirements.txt` | yes, about 20 s for all scenes |
| 2 | `hazard_scene.py` (+ `scene_assets`, `street_layout`, `street_life`, `scenery_kits`) | Blender 4.2+ (`blender -b -P …`) or `pip install bpy` on Python 3.13 | **no**: `which blender` finds nothing and `bpy` is not installed |
| 3 | `compose.py` | Pillow; ffmpeg for `--video` | yes, once stills exist |
| 4 | `gallery.py` | Pillow; ffmpeg for clip previews | yes |
| CI | `test_scenes.py`, `test_fetch_assets.py` | step 1's Python; no Blender, no network | yes (17 tests in about 30 s; 10 tests) |

Check before promising a render: `which blender; python3 -c "import bpy"`. Without either, say so, do steps 1, 3
and 4 and the tests, and leave the render to a machine with Blender (the lead's, or install `bpy`, which is large
and untested here). A render is CPU Cycles: 2.5 to 12 min of stills per scene, about 9 h for the gallery; a clip
about ten times a scene's stills. Details: [references/render-and-publish.md](references/render-and-publish.md).

## Recipe: add or change a scene

1. Read the entry the scene pictures: the HE- row in `assurance/trace/items/hazards.yaml` (WP-C-03), or the SH- row
   of WP-C-05 with its TC- (WP-C-06) and KS- (WP-V-03); for an edge case, its row in `assurance/sim/results/edge-cases.md`.
2. Write the `scenes.yaml` entry. Its header lists every field; the short version, the library and the variant
   rule are in [references/scene-definition.md](references/scene-definition.md). Pick an `environment` whose
   situations (OS-) match the entry, a condition it allows, and `variants` only for conditions the HARA model
   rates differently or the SOTIF hazard's triggering condition.
3. Export and test (from the repo root):
   ```bash
   python3 assurance/sim/blender/export_scene.py <scene-id>     # writes out/<scene-id>/scene.json (git-ignored)
   python3 assurance/sim/blender/test_scenes.py
   python3 assurance/sim/search/test_search.py TestFamilies.test_scenes_reproduce_their_rows   # edge-case scenes
   ```
   Read the events, contact, gap and TTC in `scene.json` against the entry before rendering anything.
4. Render (Blender), compose and rebuild the gallery: [references/render-and-publish.md](references/render-and-publish.md).
5. **Look at it.** Read `out/<scene>/dashboard.png` (or the committed `dashboards/<scene>.jpg`) with the Read tool,
   then the chase still at the decisive moment. Check: the ego (orange-red Corolla) and the critical road user are
   in view and tagged; the source labels are right; the banner names the event the card is about; no tree, lamp,
   parked car or walker hides a road user; the weather reads as the condition (W06 fog visibly below 200 m); the
   outcome tile matches `scene.json`. For a variant, compare it side by side with its base.
6. Update the README version line (WP-P-04) when the pipeline, library or gallery changes, and the gallery page.

## Checks

- `test_scenes.py` checks: every HE has a scene; every scene exports with its events inside its window; the
  environment allows the condition; a plant case drives its environment's geometry; W-codes match `hara_model.py`;
  traffic is never critical or the contact; a variant keeps its base's motion, events and contact; furniture,
  lamps and render-only extras keep clear of every road user and the chase camera's line of sight; and every scene
  exports the same analysis with all look keys removed.
- **A new look key** goes into the `look` set of `test_surroundings_never_reach_the_analysis`, or the test does not
  cover it. Never loosen a clearance or an equality to make a test pass.
- **A render-only code change** (in `hazard_scene.py`, `scene_assets.py`, `scenery_kits.py`, …): export every scene
  before and after and compare. The export is deterministic, so `diff -r` of the two `out/` copies must be empty;
  for a look-key change compare every field but `env`, `condition` and `environment` (snippet in
  [references/scene-definition.md](references/scene-definition.md#proving-a-change-is-render-only)).

## Relation to the 2D road scenes and to the sim results

The `road-scene` skill's flat figures and these 3D scenes mean the same where both draw a thing: **the item's car is
the only red one** (orange-red here, `EGO_RGB`), other traffic is grey or the scene's paint, a fault's moment is
named in the event list and banner. Two differences to state when you put them side by side: the 3D scenes add
**blue for the road users the plant itself models** (lead, follower); and the 3D "ghosts" are the ego's own pose at
each event, with its drawn path the *performed* path, while a 2D green ghost and dashed path are what *should*
happen. There is no intended path in 3D. Do not copy colours between the kits; each has its own source.

Numbers come from the sim track, never the other way round: plant runs and assumptions from
`assurance/sim/results/plant-results.md`, edge cases from `assurance/sim/results/edge-cases.md` (an `edge_case:` scene must reproduce its
row's rho), the dashboard reading guide in `assurance/sim/README.md` §1.1. A scene is never cited as a result.
