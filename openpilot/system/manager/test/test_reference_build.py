"""LionDriver DQ-131 (FM-06, TSR-806, CSG-03): the reference build has no debug, maneuver or joystick processes.

In the reference build no debug param changes which control processes run, and the reference release ships without the
modules of the left-out processes. A non-reference build (LIONDRIVER_REFERENCE= empty) keeps the upstream process set.
"""
import importlib.util
import os
import unittest
from typing import cast
from unittest import mock

from opendbc.car.structs import car
from openpilot.common.basedir import BASEDIR
from openpilot.common.params import Params
from openpilot.system.manager import process_config

DEBUG_PARAMS = ("JoystickDebugMode", "LongitudinalManeuverMode", "LateralManeuverMode")
# processes that send or feed actuator commands in a debug mode: joystickd sends carControl in place of controlsd,
# maneuversd sends longitudinalPlan in place of plannerd, lateral_maneuversd sends lateralManeuverPlan to controlsd
UPSTREAM_DEBUG_PROCS = {"joystick", "joystickd", "maneuversd", "lateral_maneuversd"}


def load_process_config(upstream: bool):
  # a separate module instance, so the manager's own process_config is not changed
  marker, exists = process_config.UPSTREAM_BUILD_MARKER, os.path.exists
  spec = importlib.util.spec_from_file_location(f"process_config_{'upstream' if upstream else 'reference'}", process_config.__file__)
  assert spec is not None and spec.loader is not None
  mod = importlib.util.module_from_spec(spec)
  with mock.patch("os.path.exists", side_effect=lambda p: upstream if p == marker else exists(p)):
    spec.loader.exec_module(mod)
  return mod


def load_release_files():
  spec = importlib.util.spec_from_file_location("release_files", os.path.join(BASEDIR, "tools/release/release_files.py"))
  assert spec is not None and spec.loader is not None
  mod = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(mod)
  return mod


class FakeParams:
  def __init__(self, debug: str | None = None):
    self.debug = debug

  def get_bool(self, key):
    return key == self.debug

  def get(self, key):
    return None

  def put_bool(self, key, value, block=False):
    pass


def running(procs, debug=None, not_car=False):
  CP = car.CarParams(notCar=not_car)
  return {p.name for p in procs if p.should_run(True, cast(Params, FakeParams(debug)), CP)}


class TestReferenceBuild(unittest.TestCase):
  def setUp(self):
    self.reference = load_process_config(upstream=False)
    self.upstream = load_process_config(upstream=True)

  def test_debug_processes_not_registered(self):
    self.assertTrue(self.reference.REFERENCE_BUILD)
    for name in self.reference.REFERENCE_EXCLUDED_PROCS:
      self.assertNotIn(name, self.reference.managed_processes)

  def test_debug_params_do_not_change_control_processes(self):
    baseline = running(self.reference.procs)
    self.assertTrue({"controlsd", "plannerd"} <= baseline)
    self.assertFalse(UPSTREAM_DEBUG_PROCS & baseline)
    for debug in DEBUG_PARAMS:
      self.assertEqual(running(self.reference.procs, debug), baseline, debug)

  def test_joystickd_only_for_not_car(self):
    assert "joystickd" in running(self.reference.procs, not_car=True)

  def test_upstream_build_keeps_debug_processes(self):
    self.assertFalse(self.upstream.REFERENCE_BUILD)
    self.assertTrue(set(self.reference.REFERENCE_EXCLUDED_PROCS) <= set(self.upstream.managed_processes))
    self.assertTrue({"joystick", "joystickd"} <= running(self.upstream.procs, "JoystickDebugMode"))
    self.assertNotIn("controlsd", running(self.upstream.procs, "JoystickDebugMode"))
    assert "maneuversd" in running(self.upstream.procs, "LongitudinalManeuverMode")
    self.assertNotIn("plannerd", running(self.upstream.procs, "LongitudinalManeuverMode"))
    assert "lateral_maneuversd" in running(self.upstream.procs, "LateralManeuverMode")

  def test_reference_release_ships_no_debug_process(self):
    release_files = load_release_files()
    for name in self.reference.REFERENCE_EXCLUDED_PROCS:
      path = self.upstream.managed_processes[name].module.replace(".", "/") + ".py"
      self.assertTrue(os.path.isfile(os.path.join(BASEDIR, path)), path)
      self.assertFalse(release_files.released(path, "reference"), path)
      self.assertTrue(release_files.released(path, "upstream"), path)
    joystickd = self.reference.managed_processes["joystickd"].module.replace(".", "/") + ".py"
    self.assertTrue(release_files.released(joystickd, "reference"))

  @unittest.skipUnless(os.getenv("CI"), "checks the build CI made with the root SConstruct defaults")
  def test_default_build_is_reference(self):
    self.assertTrue(process_config.REFERENCE_BUILD)
    self.assertFalse(set(process_config.REFERENCE_EXCLUDED_PROCS) & set(process_config.managed_processes))


if __name__ == "__main__":
  unittest.main()
