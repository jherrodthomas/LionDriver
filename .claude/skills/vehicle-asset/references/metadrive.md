# MetaDrive vehicle class conventions (layer 3)

The source is `vehicle-3d-model.md` §2 and §6, read against MetaDrive's `base_vehicle.py` (upstream `main` and the
`commaai/metadrive@minimal` branch that openpilot pins) on 2026-10-17. Re-read those files if the pin moves.

## Layout MetaDrive expects

- A class in `metadrive/component/vehicle/vehicle_type.py` names a glTF through `path = [file, scale, offset, hpr]` and
  declares `DEFAULT_LENGTH`, `DEFAULT_WIDTH` and `DEFAULT_HEIGHT` in metres. These dimensions drive the collision box.
- `vehicle.gltf` is the **body only**. `_add_wheel` loads `right_tire_front.gltf` and `right_tire_back.gltf` from the
  same folder, one wheel per file with its origin at the hub, and mirrors them (`set_scale(-1)`) for the left side.
- The frame is Panda3D's: **+Y forward, X lateral, Z up**. Wheels go at
  `(±LATERAL_TIRE_TO_CENTER, +FRONT_WHEELBASE / −REAR_WHEELBASE, TIRE_RADIUS − CHASSIS_TO_WHEEL_AXIS)`. The body goes
  at `Z = −(TIRE_RADIUS + CHASSIS_TO_WHEEL_AXIS)`, so the body file's origin belongs on the ground under the body
  centre.
- `AssetLoader.file_path` joins paths with `pathlib`, so an absolute path wins. The licensed files can therefore stay
  outside both repositories' code.
- `vehicle_config["vehicle_model"]` picks the class from the module-level `vehicle_type` dict. A new class is
  registered by inserting it there in the MetaDrive process.

## LionDriver's pieces

| Piece | Where | Behaviour |
|---|---|---|
| `CorollaE210Vehicle` | `openpilot/tools/sim/bridge/metadrive/corolla_vehicle.py` | Subclass of `DefaultVehicle`. Length 4.63, width 1.781 and height 1.435 m (the register's values, still *to confirm*). Hubs and tyre radius come from `geometry.json`, with the §4 receipt values as fallback. Mass, suspension, steering and friction stay `DefaultVehicle`'s |
| Bridge hook | `metadrive_bridge.py`, `metadrive_process.py` | Active only when `LIONDRIVER_VEHICLE_ASSETS` names an export folder. It fails with a message naming the missing file. Unset, the bridge is byte-for-byte the old behaviour. `render_vehicle` stays `False` |
| Test without MetaDrive | `openpilot/tools/sim/tests/test_corolla_vehicle.py` | Stubs `vehicle_type` in `sys.modules` and checks the class, the asset lookup and the error messages. It does **not** prove MetaDrive loads the glTF |

The dimensions in the class come from the register and §2's table, not from the mesh. If the register changes, change
the class to match. Never change the register to match the mesh.

## State, and the first-load caveats

As of the record (§9), the pure-Python export was load-tested in Panda3D 1.10 with panda3d-gltf, and **MetaDrive has
never loaded the class**. The first run needs `LIONDRIVER_VEHICLE_ASSETS` set, `use_render` on, and a look at the
third-person view. Then check:

- **Wheel side.** The files hold the **+X** wheels of a car facing +Y, and MetaDrive labels +X as `left` while
  loading `right_tire_*`. If the rims face inward, set `TIRE_MODEL_CORRECT = -1` in the class, as MetaDrive's
  `XLVehicle` does. Do not edit the mesh.
- **Height.** If the tyres float or sink, adjust the Z of the class's `path` offset. Do not edit the mesh.
- **Materials.** panda3d-gltf ignores clearcoat, transmission and volume, so the paint loses its gloss and the glass
  may be opaque. This is cosmetic.
- **Mirror parts.** A loose-part split can leave more than two pieces per fused mesh. The Blender script groups the
  pieces by the sign of X.

Record what you saw in §9 and in `assets/README.md`, including the `SHA256SUMS` hashes, and state plainly what was not
checked.
