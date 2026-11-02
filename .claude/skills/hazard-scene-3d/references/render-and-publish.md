# Rendering, committing and publishing

All paths from the repository root. `out/` (under `assurance/sim/blender/`) is git-ignored; only
`dashboards/` is committed.

## Setup for the steps that run without Blender

```bash
git submodule update --init --depth 1 opendbc_repo panda          # the plant loads the panda safety code
python3 -m pip install --user --break-system-packages -r assurance/sim/requirements.txt
```

Without them `export_scene.py` and `test_scenes.py` stop with `ModuleNotFoundError: No module named 'opendbc'`.
CI runs the same two steps in the `sim-plant` job of `.github/workflows/assurance.yaml`, then
`test_scenes.py` and `test_fetch_assets.py`.

## The four steps

```bash
python3 assurance/sim/blender/export_scene.py [scene-id …]                                # 1: out/<id>/scene.json
blender -b -P assurance/sim/blender/hazard_scene.py -- assurance/sim/blender/out/<id>/scene.json --stills   # 2
python3 assurance/sim/blender/compose.py assurance/sim/blender/out/<id>                   # 3: dashboard.png
python3 assurance/sim/blender/gallery.py                                                  # 4: dashboards/
```

Step 2 without the `blender` binary: `python3 assurance/sim/blender/hazard_scene.py assurance/sim/blender/out/<id>/scene.json --stills`
with `pip install bpy` on Python 3.13. Useful options: `--standin` (silhouette car, no GLB), `--res`, `--samples`
(default 16), `--no-blend`, `--vehicle PATH`. It writes `scene.blend`, `screen.json` and `stills/`.

**Clips.** `--stills --video --resume --max-frames 60` renders 60 new frames and exits with code 75; run the same
command again until it exits 0 (Blender's memory grows per frame). Then
`compose.py out/<id> --video --crf 24` (the committed clips are x264 CRF 24; the script's default is 20) and copy
`out/<id>/<id>.mp4` into `dashboards/clips/` by hand: `gallery.py` lists clips, it does not copy them.

**Cost** (4 CPU cores, Cycles, 16 samples): 2.5 to 12 min of stills per scene, weather variants longest; about 9 h
for every scene; a clip about ten times its stills. Peak memory about 5 GB, 6.2 GB on busy urban streets. Run long
renders in the background and in parts.

## What gallery.py commits

- `dashboards/<id>.jpg`: the decisive dashboard frame at 1600 × 900, **JPEG quality 75**, `optimize=True`. A scene
  not rendered in this run keeps its committed JPEG, but its README row is built from `out/<id>/scene.json`, so run
  step 1 for all scenes first or the row drops out ("not rendered yet").
- `dashboards/clips/previews/<id>.webp`: a 3 s, 10 fps, 640 px looping crop of the 3D view around the decisive
  moment (ffmpeg, WebP q 50), because GitHub plays no MP4 from the repository. It is rebuilt when the clip's mtime is
  newer than the preview's. **After a fresh clone the mtimes are arbitrary**, so `gallery.py` may rebuild previews
  whose clips did not change: check `git status` afterwards and `git checkout --` any preview you did not mean to
  change (or `touch` the previews before running).
- `dashboards/README.md`: one row per scene (entry, effect, environment and condition, motion, outcome), the edge
  cases, the variants with what the HARA changes under each condition, the clips, and the **Credits** section built
  from the CC-BY kit slots in `library/assets.lock.json`. It links the claude.ai page (`PAGE` in `gallery.py`).

`gallery.py` is deterministic: with the committed JPEGs and a fresh export it rewrites `dashboards/README.md` and
the JPEGs byte for byte. To try it without touching the tree, import it and point `gallery.GAL` at a copy of
`dashboards/` in your scratchpad.

The hero strip `assurance/sim/figures/sim-hero-dashboards.jpg` crops three committed dashboards
(`fig_sim_readme.py`; `--check` and `test_fig_sim_readme.py` are in CI). Re-run it when HE-01.2, HE-02.1 or SH-11
is re-rendered.

## Looking at the result

Read the JPEG or PNG with the Read tool; it shows the image. The dashboard layout and its ten panels are explained
in `assurance/sim/README.md` §1.1. Check at full size and imagine phone width: the 3D view must carry the point on
its own. Look at the chase still at the decisive frame in `out/<id>/stills/` when a tag or banner looks wrong. For a
clip, look at its preview WebP and two or three dashboard frames from `out/<id>/dashboard/`.

## The claude.ai gallery page

The gallery is also a web page with filters by hazard, outcome, motion and condition and the clips in a viewer:
**https://claude.ai/artifact/9jBQoqn2dNVRcpYwsJF8W3** (named in `assurance/sim/blender/README.md`, the gallery
README and `gallery.py` `PAGE`). It is private to the project lead and republished after each gallery change.
There is no generator for it in the repository: the page is one HTML file with the scene list as a JSON `ITEMS`
array, plus its images and clips published as files at `dashboards/<id>.jpg` and `dashboards/clips/<id>.mp4`.

To republish:

1. `Artifact` `read` the URL. If the link no longer works (not found, no write access), **stop**: tell the user,
   and publish a new page only with the lead's go-ahead; then update `PAGE` in `gallery.py` and the two READMEs.
2. Use the saved full HTML as the base. Never rebuild it from memory or from an earlier copy.
3. Update `ITEMS` from `out/<id>/scene.json` and the gallery README (one object per scene and variant: `id`,
   `entry`, `kind`, `group`, `asil`, `title`, `situation`, `effect`, `motion`, `case`, `outcome`, `contact`, `rel`,
   `tc`, `ks`, `caption`, `clip`, `variant_of`, `cond`, `cond_title`, `env_title`) and the header counts.
4. Publish to the same `url` with `files` adding or replacing only the changed JPEGs and MP4s
   (`"dashboards/<id>.jpg": "assurance/sim/blender/dashboards/<id>.jpg"`). Files left out are kept.
5. Keep the page's honesty note (synthetic, DSR-12, no evidence credit; contact not modelled; HARA ratings are
   proposals until accepted) and add the CC-BY credits if a re-render brought the kits onto the page.

Since 2026-11-02 (page version 19) the page lists all 125 scenes, the SH-06 and SH-14 emergency-vehicle scenes
included. Check the count against `dashboards/README.md` before each republish; the page has no generator, so it
drifts silently.
