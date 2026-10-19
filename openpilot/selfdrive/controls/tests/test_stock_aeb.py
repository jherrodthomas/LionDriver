from openpilot.common.test import OpenpilotTestCase

from opendbc.car.structs import car
from opendbc.car.car_helpers import interfaces
from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.selfdrive.controls.lib.longcontrol import LongControl, stock_aeb_stand_down

# LionDriver DQ-300 (SFM-ACT-020): no drive is requested while the car reports a stock AEB event

REFERENCE = TOYOTA.TOYOTA_COROLLA_TSS2


class TestStockAebStandDown(OpenpilotTestCase):
  def test_no_aeb_unchanged(self):
    self.assertEqual(stock_aeb_stand_down(False, 1.5, (-3.5, 2.0)), (1.5, (-3.5, 2.0)))
    self.assertEqual(stock_aeb_stand_down(False, -2.0, (-3.5, 2.0)), (-2.0, (-3.5, 2.0)))

  def test_aeb_caps_drive_at_zero(self):
    self.assertEqual(stock_aeb_stand_down(True, 1.5, (-3.5, 2.0)), (0.0, (-3.5, 0.0)))

  def test_aeb_keeps_braking_request(self):
    self.assertEqual(stock_aeb_stand_down(True, -2.0, (-3.5, 2.0)), (-2.0, (-3.5, 0.0)))

  def test_reference_controller_requests_no_drive_during_aeb(self):
    CarInterface = interfaces[REFERENCE]
    CP = CarInterface.get_non_essential_params(REFERENCE)
    CS = car.CarState.new_message(vEgo=25., aEgo=0.)
    limits = CarInterface.get_pid_accel_limits(CP, CS.vEgo, 30.)

    def run(stock_aeb, steps=200):
      LoC = LongControl(CP)
      out = []
      for frame in range(steps):
        # the controller has wound up to a positive request before the AEB event at frame 100
        aeb = stock_aeb and frame >= 100
        a_target, accel_limits = stock_aeb_stand_down(aeb, 1.5, limits)
        out.append(LoC.update(True, CS, a_target, False, accel_limits))
      return out

    without, with_aeb = run(False), run(True)
    self.assertTrue(all(a > 0. for a in without[100:]))
    self.assertTrue(all(a > 0. for a in with_aeb[50:100]))
    # from the first frame of the event, no positive acceleration is requested
    self.assertTrue(all(a <= 0. for a in with_aeb[100:]))
