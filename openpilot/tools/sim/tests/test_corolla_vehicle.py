"""Tests for the Corolla E210 MetaDrive vehicle class that run without MetaDrive installed.

MetaDrive's vehicle_type module is replaced by a stub in sys.modules, so the class definition, the asset lookup and
the error messages are checked here; whether MetaDrive loads the glTF is checked by running the bridge with
LIONDRIVER_VEHICLE_ASSETS set, which this test does not do.
"""
import importlib
import json
import sys
import types

import pytest

from openpilot.tools.sim.bridge.metadrive import corolla_vehicle as cv


@pytest.fixture
def assets(tmp_path):
  for name in (cv.VEHICLE_FILE, *cv.WHEEL_FILES):
    (tmp_path / name).write_text("{}")
  return tmp_path


@pytest.fixture
def stub_metadrive(monkeypatch):
  """A fake metadrive.component.vehicle.vehicle_type with a DefaultVehicle and the vehicle_type dict."""
  class DefaultVehicle:
    MASS = 1100
    TIRE_RADIUS = 0.313
    FRONT_WHEELBASE = 1.05234
    REAR_WHEELBASE = 1.4166
    LATERAL_TIRE_TO_CENTER = 0.815
    path = ["ferra/vehicle.gltf", (1, 1, 1), (0, 0.075, 0.0), (0, 0, 0)]

  vt = types.ModuleType("metadrive.component.vehicle.vehicle_type")
  vt.DefaultVehicle = DefaultVehicle
  vt.vehicle_type = {"default": DefaultVehicle}
  vt.vehicle_class_to_type = {DefaultVehicle: "default"}
  for n in ("metadrive", "metadrive.component", "metadrive.component.vehicle"):
    monkeypatch.setitem(sys.modules, n, types.ModuleType(n))
  sys.modules["metadrive.component.vehicle"].vehicle_type = vt
  monkeypatch.setitem(sys.modules, vt.__name__, vt)
  return vt


def test_dimensions_are_the_e210_sedan():
  assert (cv.DEFAULT_LENGTH, cv.DEFAULT_WIDTH, cv.DEFAULT_HEIGHT) == (4.63, 1.781, 1.435)


def test_disabled_when_env_unset():
  assert not cv.enabled({})
  assert not cv.enabled({cv.ENV_VAR: "  "})
  assert cv.enabled({cv.ENV_VAR: "/somewhere"})


def test_unset_variable_gives_a_clear_error():
  with pytest.raises(cv.VehicleAssetError, match=f"{cv.ENV_VAR} is not set"):
    cv.asset_dir({})


def test_missing_directory_is_reported(tmp_path):
  with pytest.raises(cv.VehicleAssetError, match="is not a directory"):
    cv.asset_dir({cv.ENV_VAR: str(tmp_path / "nope")})


def test_missing_files_are_named(tmp_path):
  (tmp_path / cv.VEHICLE_FILE).write_text("{}")
  with pytest.raises(cv.VehicleAssetError) as e:
    cv.asset_dir({cv.ENV_VAR: str(tmp_path)})
  listed = str(e.value).split("lacks", 1)[1]
  assert "right_tire_front.gltf" in listed and "right_tire_back.gltf" in listed
  assert cv.VEHICLE_FILE not in listed


def test_complete_folder_is_accepted(assets):
  assert cv.asset_dir({cv.ENV_VAR: str(assets)}) == assets


def test_geometry_falls_back_to_receipt_check(assets):
  geom = cv.load_geometry(assets)
  assert geom["front_wheelbase"] == pytest.approx(1.396)   # tail-lamp end is the rear; the separate wheels are the front
  assert "receipt check" in geom["source"]


def test_geometry_json_is_read(assets):
  (assets / cv.GEOMETRY_FILE).write_text(json.dumps({"front_wheelbase": 1.31, "tire_radius": 0.32}))
  geom = cv.load_geometry(assets)
  assert geom["front_wheelbase"] == 1.31
  assert geom["tire_radius"] == 0.32
  assert geom["rear_wheelbase"] == pytest.approx(1.314)  # not in the file: fallback
  assert geom["source"].endswith(cv.GEOMETRY_FILE)


def test_bad_geometry_is_rejected(assets):
  (assets / cv.GEOMETRY_FILE).write_text(json.dumps({"tire_radius": 0}))
  with pytest.raises(cv.VehicleAssetError, match="tire_radius"):
    cv.load_geometry(assets)


def test_vehicle_class_definition(assets, stub_metadrive):
  cls = cv.make_vehicle_class(assets)
  assert issubclass(cls, stub_metadrive.DefaultVehicle)
  assert cls.__name__ == "CorollaE210Vehicle"
  assert cls.path[0].endswith(cv.VEHICLE_FILE)
  assert cls.path[1:] == [(1, 1, 1), (0, 0, 0), (0, 0, 0)]
  assert (cls.DEFAULT_LENGTH, cls.DEFAULT_WIDTH, cls.DEFAULT_HEIGHT) == (4.63, 1.781, 1.435)
  assert cls.FRONT_WHEELBASE + cls.REAR_WHEELBASE == pytest.approx(2.709, abs=1e-3)
  assert cls.MASS == stub_metadrive.DefaultVehicle.MASS  # physics other than geometry is inherited
  v = cls.__new__(cls)
  assert (v.LENGTH, v.WIDTH, v.HEIGHT) == (4.63, 1.781, 1.435)


def test_register_adds_the_model_key(assets, stub_metadrive):
  key = cv.register(assets)
  assert key == cv.MODEL_KEY == "corolla_e210"
  assert stub_metadrive.vehicle_type[key].__name__ == "CorollaE210Vehicle"
  assert stub_metadrive.vehicle_class_to_type[stub_metadrive.vehicle_type[key]] == key


def test_module_does_not_import_metadrive_at_import_time(monkeypatch):
  for name in [n for n in sys.modules if n.startswith("metadrive")]:
    monkeypatch.delitem(sys.modules, name)
  importlib.reload(cv)
  assert not any(n.startswith("metadrive") for n in sys.modules)
