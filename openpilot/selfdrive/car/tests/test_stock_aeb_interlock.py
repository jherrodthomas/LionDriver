import os
from unittest import mock

import pytest

from opendbc.car.car_helpers import interfaces
from opendbc.car.toyota.values import CAR as TOYOTA, ToyotaFlags
from opendbc.car.values import PLATFORMS
from openpilot.selfdrive.car import stock_aeb_interlock

# LD-FSR-001 / CA-001 verification (FI-2026-001)

SIM_ENV = {"SIMULATION": "1", "NOBOARD": "1"}


def get_params(platform, alpha_long):
  fingerprints = dict.fromkeys(range(7), {})
  return interfaces[platform].get_params(platform, fingerprints, [], alpha_long=alpha_long, is_release=False, docs=False)


@pytest.fixture(autouse=True)
def vehicle_env():
  # tests run as on a vehicle unless they opt into the simulator
  with mock.patch.dict(os.environ, clear=False):
    for key in SIM_ENV:
      os.environ.pop(key, None)
    yield


class TestAlphaLongAllowed:
  def test_not_requested(self):
    assert not stock_aeb_interlock.alpha_long_allowed(False)

  def test_refused_on_vehicle(self):
    assert not stock_aeb_interlock.alpha_long_permitted()
    assert not stock_aeb_interlock.alpha_long_allowed(True)

  def test_allowed_in_simulator(self):
    with mock.patch.dict(os.environ, SIM_ENV):
      assert stock_aeb_interlock.alpha_long_permitted()
      assert stock_aeb_interlock.alpha_long_allowed(True)

  @pytest.mark.parametrize("key", sorted(SIM_ENV))
  def test_partial_simulator_env_refused(self, key):
    # both are needed: NOBOARD is what removes the path to a vehicle CAN bus
    with mock.patch.dict(os.environ, {key: "1"}):
      assert not stock_aeb_interlock.alpha_long_allowed(True)


class TestStockAebPreserved:
  @pytest.mark.parametrize("platform", sorted(PLATFORMS))
  def test_preserved_without_alpha_long(self, platform):
    # what card passes to the car interface on a vehicle once the request is refused
    CP = get_params(platform, stock_aeb_interlock.alpha_long_allowed(True))
    assert stock_aeb_interlock.stock_aeb_preserved(CP)

  @pytest.mark.parametrize("platform", sorted(PLATFORMS))
  def test_detects_alpha_long(self, platform):
    CP = get_params(platform, alpha_long=True)
    if CP.alphaLongitudinalAvailable and CP.openpilotLongitudinalControl:
      assert not stock_aeb_interlock.stock_aeb_preserved(CP)

  def test_radar_acc_toyota(self):
    # FI-2026-001 RC-01: alpha long on a radar-ACC Toyota disables the radar ECU and PCS
    CP = get_params(TOYOTA.TOYOTA_RAV4_TSS2_2022, alpha_long=True)
    assert CP.flags & ToyotaFlags.DISABLE_RADAR
    assert not stock_aeb_interlock.stock_aeb_preserved(CP)

    CP = get_params(TOYOTA.TOYOTA_RAV4_TSS2_2022, stock_aeb_interlock.alpha_long_allowed(True))
    assert not CP.flags & ToyotaFlags.DISABLE_RADAR
    assert not CP.openpilotLongitudinalControl
    assert stock_aeb_interlock.stock_aeb_preserved(CP)

  def test_reference_vehicle_keeps_openpilot_long(self):
    # 2020 Corolla is camera-ACC: openpilot longitudinal by default, radar ECU untouched
    CP = get_params(TOYOTA.TOYOTA_COROLLA_TSS2, stock_aeb_interlock.alpha_long_allowed(True))
    assert CP.openpilotLongitudinalControl
    assert not CP.flags & ToyotaFlags.DISABLE_RADAR
    assert stock_aeb_interlock.stock_aeb_preserved(CP)

  def test_simulator_exempt(self):
    CP = get_params(TOYOTA.TOYOTA_RAV4_TSS2_2022, alpha_long=True)
    with mock.patch.dict(os.environ, SIM_ENV):
      assert stock_aeb_interlock.stock_aeb_preserved(CP)
