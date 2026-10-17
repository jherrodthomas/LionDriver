# Vehicle 3D model for the simulation track

| Field | Value |
|---|---|
| Scope | A 3D mesh of the reference car (Corolla E210, CFG-001) for simulation layer 3 (MetaDrive) renders and for figures. Procurement comparison, what the mesh does and does not change, and the handover for whoever picks this up next |
| Version | 0.1 (2026-10-17) |
| Status | Draft. AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed. Purchase waits on decision DQ-368 |
| Feeds | [README](README.md) §2 layer 3; the WP-V-02/WP-V-03 figures that show the reference car; nothing in the safety case |

## 1. What a mesh is for here, and what it is not for

**For AI assistants and anyone new to the thread: read this section before spending time on car models.**

LionDriver's simulation is not a game engine. Layer 1 is a Python single-track plant with the real panda safety code in
the loop ([`plant/`](plant/)), layer 2 is OpenSCENARIO files replayed in esmini, layer 3 is openpilot's own MetaDrive
bridge (`openpilot/tools/sim`), layer 4 is a numerical search over layer 1. None of them reads a 3D mesh for physics.

| Question | Answer |
|---|---|
| Does the mesh change any simulation result? | **No.** Mass, wheelbase, centre of gravity, steering ratio, actuator lags and body width come from the opendbc `TOYOTA_COROLLA_TSS2` CarParams and the vehicle register ([`plant/corolla.py`](plant/corolla.py), [`vehicles.yaml`](../../docs/liondriver/vehicles/vehicles.yaml)). A mesh is drawn around those numbers; it never feeds them |
| Does openpilot see the mesh in layer 3? | **No.** The bridge spawns the ego with `render_vehicle: False` ([`metadrive_bridge.py`](../../openpilot/tools/sim/bridge/metadrive/metadrive_bridge.py) `spawn_world`), so the ego body is not in the road-camera image openpilot consumes. Only third-person and top-down views, used for videos and figures, would show it |
| Is a marketplace mesh a source for vehicle facts? | **No.** The register's width 1,781 mm is marked *to confirm*; a purchased mesh is an artist's model and does not confirm it. Only Toyota's data or a measurement on the reference car does (WP-S-04 M-01) |
| Is it evidence? | **No.** It is a presentation asset. Treat it like the figure colour tokens |
| Should the car be rigged in Unreal Engine or another game engine? | **No.** UE4/UE5 Chaos Vehicles, Rigacar and similar rigs were considered in the originating chat and dropped: the track has no Unreal in its toolchain, and MetaDrive (Panda3D) takes a plain glTF with wheels as separate nodes. A game-engine car rig would be a separate visualisation project with no owner |

So the value is cosmetic: layer-3 clips and WP-V figures show a Corolla instead of MetaDrive's stock car, and the body
shape helps camera-height and blind-zone drawings. The cost is $99 plus a decimation pass. The lead decides (DQ-368).

## 2. How MetaDrive takes a vehicle mesh

MetaDrive vehicle classes (`metadrive/component/vehicle/vehicle_type.py`) each name a glTF file with a scale, an
offset and a heading-pitch-roll, and declare `DEFAULT_LENGTH`, `DEFAULT_WIDTH`, `DEFAULT_HEIGHT` in metres. For
example `DefaultVehicle` uses `ferra/vehicle.gltf` at 4.515 × 1.852 × 1.19 m. A Corolla class would subclass
`BaseVehicle` with the E210 sedan dimensions and a `corolla_e210/vehicle.gltf` under MetaDrive's asset path, and the
bridge would pass that class in `vehicle_config`. Wheels must be separate nodes so MetaDrive can spin and steer them;
the body and the wheels are the whole rig.

Dimensions to use for the class (sedan, not hatchback; the register is authoritative where it has a value):

| Quantity | Value | Source |
|---|---|---|
| Length | 4,630 mm | 2020 Corolla sedan listings; to confirm |
| Width | 1,781 mm | vehicle register CFG-001 (*to confirm*) |
| Height | 1,435 mm | listings; to confirm |
| Wheelbase | opendbc CarSpecs | `plant/corolla.py` reads it; do not retype |
| Tyre | 205/55R16 | L/LE/XLE trims of CFG-001; the 2.0 L SE/XSE run 225/40R18 and are excluded from CFG-001 |

## 3. Procurement comparison (checked 2026-10-17)

No free, game-ready 2020 Corolla exists. Every real 2020 model is a paid render asset under an editorial-use licence
(Toyota owns the design), which is fine for this project and would not cover a commercial product. Prices and details
were read from the listing pages on the date above; confirm before buying.

**Recommended (option A of DQ-368):** Toyota Corolla 2020 Simple Interior, seller 3d_molier International,
[TurboSquid 1450755](https://www.turbosquid.com/3d-models/3d-toyota-corolla-2020-simple-model-1450755), $99.

- 214,054 polygons / 220,561 vertices, quads and tris, PBR, non-overlapping UVs
- Formats: glTF, USD, FBX, OBJ, Blender 2.7, 3ds Max 2012, Maya 2011, Cinema 4D R14, 3DS; textures and materials
  mapped in every format (11 PNG at 4096²)
- Doors open (so doors are separate objects); objects logically named; units cm, correctly scaled
- Not stated: trim and wheel size, and whether the wheels are separate nodes. Check both on receipt; TurboSquid
  accepts returns
- Needs a decimation pass in Blender to roughly 50–80k polygons before MetaDrive

**Low-cost alternative (option B):** Toyota Corolla low poly 3D model, seller RoyFld,
[TurboSquid 1664213](https://www.turbosquid.com/3d-models/toyota-corolla-model-1664213), $2.50. 5,550 polygons,
Blender 2.82 / FBX / OBJ / STL, real-life dimensions, flat materials, no textures. Enough for a recognisable silhouette
in top-down and third-person views; also a cheap way to test the MetaDrive vehicle class before the hero mesh arrives.

**Same seller, fuller cabin:** Detailed Interior, [TurboSquid 1450753](https://www.turbosquid.com/3d-models/toyota-corolla-2020-3d-1450753),
$129, 253,967 polygons, same formats. Only for in-car camera shots, which layer 3 does not need.

**Compared and not recommended**

| Model | Seller, site | Price | Polygons | Formats | Why not |
|---|---|---|---|---|---|
| Corolla 2020 Rigged | 3d_molier, [TurboSquid 1450756](https://www.turbosquid.com/3d-models/3d-model-toyota-corolla-2020-rigged-1450756) | $149 | 253,967 | 3ds Max, glTF, USD | The rig is 3ds Max helper objects; it does not export. MetaDrive needs no rig |
| Corolla 2020 | Swan3D Studios, [RenderHub](https://www.renderhub.com/swan3dstudios/toyota-corolla-2020) | $100 | 161k–630k (hi/lo per format) | 3ds, blend, c4d, fbx, max, mb, obj, skp | Wheels grouped separately, real scale in mm, but materials only in the Max file; basic interior. Usable backup |
| Corolla 2020 XSE | 3DStarving, [RenderHub](https://www.renderhub.com/3dstarving/toyota-corolla-2020) and [Free3D](https://free3d.com/3d-model/toyota-corolla-2020-1174.html) | $149 | 227,519 unsmoothed | max, 3ds, fbx, obj | XSE trim (18-inch wheels, excluded from CFG-001); FBX/OBJ ship without materials; Free3D listing is not free |
| Corolla sedan regular 2020 | Squir, [TurboSquid 1369466](https://www.turbosquid.com/3d-models/3d-model-toyota-corolla-sedan-1369466) | $129 | 500,000 | max, c4d, 3ds, fbx, obj, glTF, USD | Highest quality, 3ds Max-centric, heavy; overkill for a cosmetic asset |
| Corolla XSE 2020 | Podshyvalov, [RenderHub](https://www.renderhub.com/podshyvalov/toyota-corolla-xse-2020) | $60 | 320,147 | fbx, max, obj | XSE trim; scale and part separation not stated |
| Corolla Hybrid 2020 | Swan3D Studios, [RenderHub](https://www.renderhub.com/swan3dstudios/toyota-corolla-hybrid-2020) | $100 | as Swan3D above | as above | Hybrid badging; Hybrid is excluded from CFG-001 |
| Corolla Sport Hatchback 2020–2023 HQ Interior | Davidson, [RenderHub](https://www.renderhub.com/davidson/toyota-corolla-hatchback-2020-and-gr-corolla) | $29.90 | not stated | 3ds Max only | Hatchback, excluded from CFG-001 |

Not inspected: [CGTrader](https://www.cgtrader.com/3d-models/car/car/toyota-corolla-2020-88963874-e96d-4b79-ad87-0a3b105f95d3)
and [two](https://www.cgtrader.com/3d-models/car/car/2020-toyota-corolla) [more](https://www.cgtrader.com/3d-models/car/car/toyota-corolla-sedan-regular-2020)
CGTrader listings (the site refused automated reads); Sketchfab had no downloadable E210.

Checklist before buying any model: wheels as separate objects with pivots at the hub centres; real-world scale stated;
materials present in the glTF or FBX, not only in the native file; sedan, 1.8 L trim with 16-inch wheels; a polygon
count you can afford to decimate.

## 4. Handover

- **Where things stand.** Research done; nothing bought; DQ-368 queued for the lead. Purchased files are licensed
  content: keep them out of the repository (add the asset folder to `.gitignore` when one exists) and never push them.
- **If A or B is chosen:** put the glTF under a MetaDrive-visible asset path, write a `CorollaE210Vehicle` class with
  the §2 dimensions, decimate the hero mesh, confirm the wheels are separate nodes, and pass the class through the
  bridge's `vehicle_config`. Record the file, its licence and its source in this note. Any figure that uses it says so
  in its caption, as the figures already do for assumed values (MD-04).
- **If C is chosen:** mark this note withdrawn in the status field and leave it as the record of the comparison.
- **Do not** re-open the game-engine route (Unreal, Unity) or re-run the marketplace comparison without a new reason;
  cite this note and DQ-368 instead.

## 5. Origin

Written from a Claude Code session on 2026-10-17 that began as "can we use UE4 to create rigging for a car" and ended
at the comparison above once the project's actual simulation stack was read. The repo path for the next session is
`assurance/sim/`; this note is linked from the README's "Where things are" table.
