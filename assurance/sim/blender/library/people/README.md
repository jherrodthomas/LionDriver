# Pedestrians

Two walking figures for the pedestrians of the hazardous-event scenes. They are built by
[`build_people.py`](build_people.py) from two free Quaternius packs, both **CC0 1.0** (public domain dedication; no
attribution required), so the built files are committed here rather than fetched. Pictures only: synthetic (DSR-12),
no evidence credit.

| File | Figure | Built from |
|---|---|---|
| `pedestrian_male.glb` | Male base character, short parted hair; 1.78 m | Universal Base Characters [Standard]: `Superhero_Male_FullBody`, `Hair_SimpleParted` |
| `pedestrian_female.glb` | Female base character, hair in buns; 1.66 m | Universal Base Characters [Standard]: `Superhero_Female_FullBody`, `Hair_Buns` |

Both files carry the pack's 65-bone rig and the `Walk_Loop` animation of the Universal Animation Library [Standard].
Their textures are cut to 1024 px JPEG, and the grey hair textures are tinted brown. Clothes are assigned from the bone each polygon follows: a long-sleeved shirt, trousers and shoes. The head and hands keep the skin texture. The packs ship only base bodies, and
their outfits are in the paid versions.

**In a scene:**
- `hazard_scene.py` imports one figure per pedestrian, faces it along the path at its standing height, and recolours the shirt.
- It plays `Walk_Loop` by the distance walked: one loop, two steps, every 1.45 m. The figure stands still when the pedestrian stops.
- A scene picks the figure with `figure: male` or `female` on the actor in [`../../scenes.yaml`](../../scenes.yaml). Without it, the figure and shirt colour follow from the actor's name and the base scene's ID, so a condition variant shows the same person.
- Without these files, the scene falls back to the procedural figure.

**Sources** (downloaded 2026-10-19):
- Universal Base Characters: [quaternius.com](https://quaternius.com/packs/universalbasecharacters.html), [itch.io](https://quaternius.itch.io/universal-base-characters).
- Universal Animation Library: [quaternius.com](https://quaternius.com/packs/universalanimationlibrary.html), [itch.io](https://quaternius.itch.io/universal-animation-library).

Both packs' `License.txt` give CC0 1.0. To rebuild, download the two "Standard" zips and run:

```sh
python3 assurance/sim/blender/library/people/build_people.py "Universal Base Characters[Standard].zip" "Universal Animation Library[Standard].zip"
```
