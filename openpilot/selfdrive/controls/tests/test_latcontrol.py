from openpilot.common.test import OpenpilotTestCase
from openpilot.common.parameterized import parameterized

from openpilot.cereal import log
from opendbc.car.structs import car
from opendbc.car.car_helpers import interfaces
from opendbc.car.honda.values import CAR as HONDA
from opendbc.car.toyota.values import CAR as TOYOTA
from opendbc.car.nissan.values import CAR as NISSAN
from opendbc.car.gm.values import CAR as GM
from opendbc.car.volkswagen.values import CAR as VOLKSWAGEN
from opendbc.car.vehicle_model import VehicleModel
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.latcontrol_pid import LatControlPID
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.selfdrive.controls.lib.latcontrol_angle import LatControlAngle
from openpilot.selfdrive.controls.lib.latcontrol_curvature import LatControlCurvature


class TestLatControl(OpenpilotTestCase):

  @parameterized.expand([(HONDA.HONDA_CIVIC, LatControlPID), (TOYOTA.TOYOTA_RAV4, LatControlTorque),
                         (NISSAN.NISSAN_LEAF, LatControlAngle), (GM.CHEVROLET_BOLT_EUV, LatControlTorque),
                         (VOLKSWAGEN.VOLKSWAGEN_ID4_MK2, LatControlCurvature)])
  def test_saturation(self, car_name, controller):
    CarInterface = interfaces[car_name]
    CP = CarInterface.get_non_essential_params(car_name)
    CI = CarInterface(CP)
    VM = VehicleModel(CP)

    controller = controller(CP.as_reader(), CI, DT_CTRL)

    CS = car.CarState.new_message()
    CS.vEgo = 30
    CS.steeringPressed = False

    params = log.VehicleParameters.new_message()

    # Saturate for curvature limited and controller limited
    for _ in range(1000):
      _, _, lac_log = controller.update(True, CS, VM, params, False, 0, True, 0.2)
    assert lac_log.saturated

    for _ in range(1000):
      _, _, lac_log = controller.update(True, CS, VM, params, False, 0, False, 0.2)
    assert not lac_log.saturated

    for _ in range(1000):
      _, _, lac_log = controller.update(True, CS, VM, params, False, 1, False, 0.2)
    assert lac_log.saturated


class TestLatControlReset(OpenpilotTestCase):
  # LionDriver (SWF-042.C1): reset() clears the integrator, so an engagement does not start with the last one's correction

  @parameterized.expand([(HONDA.HONDA_CIVIC, LatControlPID), (TOYOTA.TOYOTA_COROLLA_TSS2, LatControlTorque),
                         (VOLKSWAGEN.VOLKSWAGEN_ID4_MK2, LatControlCurvature)])
  def test_reset_clears_integrator(self, car_name, controller):
    CarInterface = interfaces[car_name]
    CP = CarInterface.get_non_essential_params(car_name)
    controller = controller(CP.as_reader(), CarInterface(CP), DT_CTRL)
    VM = VehicleModel(CP)
    CS = car.CarState.new_message()
    CS.vEgo = 30
    params = log.VehicleParameters.new_message()

    for _ in range(300):
      controller.update(True, CS, VM, params, False, 0.0001, False, 0.2)
    assert controller.pid.i != 0.
    controller.reset()
    assert controller.pid.i == 0.
