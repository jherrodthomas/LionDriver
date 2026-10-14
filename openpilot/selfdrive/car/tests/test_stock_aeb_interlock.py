import os
import unittest
from unittest import mock

from opendbc.car.car_helpers import interfaces
from opendbc.car.toyota.values import CAR as TOYOTA, ToyotaFlags
from opendbc.car.values import PLATFORMS
from openpilot.common.parameterized import parameterized
from openpilot.selfdrive.car import stock_aeb_interlock

# LD-FSR-001 / CA-001 verification (FI-2026-001)

SIM_ENV = {"SIMULATION": "1", "NOBOARD": "1"}


def get_params(platform, alpha_long):
  fingerprints = dict.fromkeys(range(7), {})
  return interfaces[platform].get_params(platform, fingerprints, [], alpha_long=alpha_long, is_release=False, docs=False)


class VehicleEnvTestCase(unittest.TestCase):
  def setUp(self):
    # tests run as on a vehicle unless they opt into the simulator
    patcher = mock.patch.dict(os.environ)
    patcher.start()
    self.addCleanup(patcher.stop)
    for key in SIM_ENV:
      os.environ.pop(key, None)


class TestAlphaLongAllowed(VehicleEnvTestCase):
  def test_not_requested(self):
    self.assertFalse(stock_aeb_interlock.alpha_long_allowed(False))

  def test_refused_on_vehicle(self):
    self.assertFalse(stock_aeb_interlock.alpha_long_permitted())
    self.assertFalse(stock_aeb_interlock.alpha_long_allowed(True))

  def test_allowed_in_simulator(self):
    with mock.patch.dict(os.environ, SIM_ENV):
      self.assertTrue(stock_aeb_interlock.alpha_long_permitted())
      self.assertTrue(stock_aeb_interlock.alpha_long_allowed(True))

  @parameterized.expand(sorted(SIM_ENV))
  def test_partial_simulator_env_refused(self, key):
    # both are needed: NOBOARD is what removes the path to a vehicle CAN bus
    with mock.patch.dict(os.environ, {key: "1"}):
      self.assertFalse(stock_aeb_interlock.alpha_long_allowed(True))


class TestStockAebPreserved(VehicleEnvTestCase):
  @parameterized.expand(sorted(PLATFORMS))
  def test_preserved_without_alpha_long(self, platform):
    # what card passes to the car interface on a vehicle once the request is refused
    CP = get_params(platform, stock_aeb_interlock.alpha_long_allowed(True))
    self.assertTrue(stock_aeb_interlock.stock_aeb_preserved(CP))

  @parameterized.expand(sorted(PLATFORMS))
  def test_detects_alpha_long(self, platform):
    CP = get_params(platform, alpha_long=True)
    if CP.alphaLongitudinalAvailable and CP.openpilotLongitudinalControl:
      self.assertFalse(stock_aeb_interlock.stock_aeb_preserved(CP))

  def test_radar_acc_toyota(self):
    # FI-2026-001 RC-01: alpha long on a radar-ACC Toyota disables the radar ECU and PCS
    CP = get_params(TOYOTA.TOYOTA_RAV4_TSS2_2022, alpha_long=True)
    self.assertTrue(CP.flags & ToyotaFlags.DISABLE_RADAR)
    self.assertFalse(stock_aeb_interlock.stock_aeb_preserved(CP))

    CP = get_params(TOYOTA.TOYOTA_RAV4_TSS2_2022, stock_aeb_interlock.alpha_long_allowed(True))
    self.assertFalse(CP.flags & ToyotaFlags.DISABLE_RADAR)
    self.assertFalse(CP.openpilotLongitudinalControl)
    self.assertTrue(stock_aeb_interlock.stock_aeb_preserved(CP))

  def test_reference_vehicle_keeps_openpilot_long(self):
    # 2020 Corolla is camera-ACC: openpilot longitudinal by default, radar ECU untouched
    CP = get_params(TOYOTA.TOYOTA_COROLLA_TSS2, stock_aeb_interlock.alpha_long_allowed(True))
    self.assertTrue(CP.openpilotLongitudinalControl)
    self.assertFalse(CP.flags & ToyotaFlags.DISABLE_RADAR)
    self.assertTrue(stock_aeb_interlock.stock_aeb_preserved(CP))

  def test_simulator_exempt(self):
    CP = get_params(TOYOTA.TOYOTA_RAV4_TSS2_2022, alpha_long=True)
    with mock.patch.dict(os.environ, SIM_ENV):
      self.assertTrue(stock_aeb_interlock.stock_aeb_preserved(CP))
