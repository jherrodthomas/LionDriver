"""Corolla E210 (CFG-001) vehicle for the MetaDrive bridge, drawn with the purchased 3d_molier mesh.

The mesh is a licensed, editorial-use asset and is not in this repository. Point LIONDRIVER_VEHICLE_ASSETS at the
folder written by assurance/sim/assets/tools/corolla_e210_metadrive_export.py (vehicle.gltf, right_tire_front.gltf,
right_tire_back.gltf, geometry.json, textures/). When the variable is unset the bridge behaves exactly as before and
never imports this module's MetaDrive parts.

Only `make_vehicle_class` and `register` import MetaDrive; everything else is plain Python so the module and its
test run on a machine without MetaDrive (see tools/sim/tests/test_corolla_vehicle.py).

What the class changes in MetaDrive and what it does not (assurance/sim/vehicle-3d-model.md sections 1-2):
  * chassis box and drawn body: 4.63 x 1.781 x 1.435 m (E210 sedan; width from the vehicle register, "to confirm")
  * wheel positions and tyre radius: read from geometry.json so the wheels sit under the mesh's arches
    (the mesh's wheelbase is 2.709 m against opendbc's 2.700)
  * mass, suspension, steering, engine and tyre friction: inherited from DefaultVehicle, untouched
  * nothing in layer 1 (plant), the safety case or openpilot's camera path: the bridge keeps render_vehicle False,
    so the ego body is not in the images openpilot consumes

Draft. AI-drafted (Claude, AI assistant; I0 under WP-M-02 section 3.3); not reviewed. Not yet loaded in MetaDrive.
"""
import json
import os
from pathlib import Path

ENV_VAR = "LIONDRIVER_VEHICLE_ASSETS"
MODEL_KEY = "corolla_e210"            # key added to metadrive's vehicle_type dict
VEHICLE_FILE = "vehicle.gltf"
WHEEL_FILES = ("right_tire_front.gltf", "right_tire_back.gltf")
GEOMETRY_FILE = "geometry.json"

# E210 sedan, metres (vehicle-3d-model.md section 2)
DEFAULT_LENGTH = 4.63
DEFAULT_WIDTH = 1.781
DEFAULT_HEIGHT = 1.435

# Fallback when geometry.json is absent: hub centres from the receipt check (vehicle-3d-model.md section 4), metres,
# relative to the body centre, and the mesh's 18-inch tyre. The export script writes the measured values.
RECEIPT_GEOMETRY = {
  "front_wheelbase": 1.305,
  "rear_wheelbase": 1.404,
  "lateral_tire_to_center": 0.752,
  "tire_radius": 0.3245,
  "tire_width": 0.225,
}


class VehicleAssetError(RuntimeError):
  """The Corolla mesh is requested but cannot be found."""


def enabled(env=None) -> bool:
  """True when the user asked for the Corolla mesh by setting LIONDRIVER_VEHICLE_ASSETS."""
  env = os.environ if env is None else env
  return bool(env.get(ENV_VAR, "").strip())


def asset_dir(env=None) -> Path:
  """The folder holding vehicle.gltf; raises VehicleAssetError with a message that says what to do."""
  env = os.environ if env is None else env
  raw = env.get(ENV_VAR, "").strip()
  if not raw:
    raise VehicleAssetError(
      f"{ENV_VAR} is not set. Point it at the folder that holds {VEHICLE_FILE} "
      "(the output of assurance/sim/assets/tools/corolla_e210_metadrive_export.py, kept in the private "
      "LionDriver-assets repository), or unset it to use MetaDrive's stock vehicle.")
  d = Path(raw).expanduser()
  if not d.is_dir():
    raise VehicleAssetError(f"{ENV_VAR}={raw!r} is not a directory.")
  missing = [f for f in (VEHICLE_FILE, *WHEEL_FILES) if not (d / f).is_file()]
  if missing:
    raise VehicleAssetError(
      f"{ENV_VAR}={raw!r} lacks {', '.join(missing)}. Run the Blender export script on "
      "assurance/sim/assets/1450755-gltf-extended.glb, or copy blender-decimated-corolla_e210/ from the private "
      "LionDriver-assets repository into that folder.")
  return d


def load_geometry(d: Path) -> dict:
  """Hub geometry measured by the export script, or the receipt-check fallback (with a 'source' key saying which)."""
  p = Path(d) / GEOMETRY_FILE
  geom = dict(RECEIPT_GEOMETRY)
  if p.is_file():
    with open(p, encoding="utf-8") as f:
      data = json.load(f)
    for k in RECEIPT_GEOMETRY:
      if k in data:
        geom[k] = float(data[k])
    geom["source"] = str(p)
  else:
    geom["source"] = "receipt check (vehicle-3d-model.md section 4); geometry.json not found"
  for k in RECEIPT_GEOMETRY:
    if not geom[k] > 0:
      raise VehicleAssetError(f"{GEOMETRY_FILE}: {k} must be positive, got {geom[k]!r}")
  return geom


def make_vehicle_class(d: Path | None = None):
  """Build the MetaDrive vehicle class for the Corolla mesh. Imports MetaDrive; call it in the MetaDrive process."""
  from metadrive.component.vehicle.vehicle_type import DefaultVehicle  # noqa: PLC0415 (lazy on purpose)

  d = asset_dir() if d is None else Path(d)
  geom = load_geometry(d)
  vehicle_path = str((d / VEHICLE_FILE).resolve())
  length, width, height = DEFAULT_LENGTH, DEFAULT_WIDTH, DEFAULT_HEIGHT

  class CorollaE210Vehicle(DefaultVehicle):
    """Toyota Corolla E210 sedan (LionDriver CFG-001), 3d_molier mesh. Physics other than geometry: DefaultVehicle."""
    # AssetLoader.file_path("models", path) joins with pathlib, so an absolute path wins over MetaDrive's asset root,
    # and the wheel files are looked up next to it (base_vehicle.py _add_wheel: dirname(path[0])).
    path = [vehicle_path, (1, 1, 1), (0, 0, 0), (0, 0, 0)]  # file, scale, offset (x, y, z), HPR
    DEFAULT_LENGTH = length
    DEFAULT_WIDTH = width
    DEFAULT_HEIGHT = height
    FRONT_WHEELBASE = geom["front_wheelbase"]
    REAR_WHEELBASE = geom["rear_wheelbase"]
    LATERAL_TIRE_TO_CENTER = geom["lateral_tire_to_center"]
    TIRE_RADIUS = geom["tire_radius"]
    TIRE_WIDTH = geom["tire_width"]
    GEOMETRY_SOURCE = geom["source"]

    @property
    def LENGTH(self):
      return self.DEFAULT_LENGTH

    @property
    def WIDTH(self):
      return self.DEFAULT_WIDTH

    @property
    def HEIGHT(self):
      return self.DEFAULT_HEIGHT

  return CorollaE210Vehicle


def register(d: Path | None = None) -> str:
  """Add the Corolla class to MetaDrive's vehicle_type dict under MODEL_KEY and return the key."""
  from metadrive.component.vehicle import vehicle_type as vt  # noqa: PLC0415

  vt.vehicle_type[MODEL_KEY] = make_vehicle_class(d)
  if hasattr(vt, "vehicle_class_to_type"):
    vt.vehicle_class_to_type[vt.vehicle_type[MODEL_KEY]] = MODEL_KEY
  return MODEL_KEY
