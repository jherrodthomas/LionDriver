import math
from types import SimpleNamespace
from unittest import mock

import numpy as np

from opendbc.car.car_helpers import interfaces
from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.cereal import log
from openpilot.common.params import Params
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.controls import controlsd
from openpilot.selfdrive.locationd.helpers import Measurement, Pose

# The controlsd call sites of two LionDriver safety measures, run through the real Controls.state_control and publish
# with the reference CarParams. The measures themselves are tested in test_stock_aeb.py (stock_aeb_stand_down) and
# test_minimum_risk.py (the selfdrived latch); this checks that controlsd applies them:
#   SWF-093.C1 (DQ-300): during a stock AEB event no positive acceleration is requested, from the first frame
#   SWF-062.C1 (TSR-633): forceDecel is held while selfdrived reports the minimum-risk maneuver, and reaches the car

REFERENCE = TOYOTA.TOYOTA_COROLLA_TSS2
State = log.SelfdriveState.OpenpilotState


class FakeSubMaster:
  """The SubMaster surface Controls reads: every input received, valid and current"""
  def __init__(self, services, poll=None):
    self.services = services
    self.data = {s: log.Event.new_message().init(s) if s != 'onroadEvents' else [] for s in services}
    self.valid = dict.fromkeys(services, True)
    self.valid['lateralManeuverPlan'] = False
    self.seen = dict.fromkeys(services, True)
    self.alive = dict.fromkeys(services, True)
    self.logMonoTime = dict.fromkeys(services, 0)

  def __getitem__(self, s):
    return self.data[s]

  def all_checks(self, services=None):
    return True


class FakePubMaster:
  def __init__(self, services=None):
    self.sent = {}

  def send(self, s, dat):
    self.sent[s] = dat


def controls():
  CP = interfaces[REFERENCE].get_non_essential_params(REFERENCE)
  Params().put("CarParams", CP.to_bytes(), block=True)
  pm = FakePubMaster()
  with mock.patch.object(controlsd.messaging, 'SubMaster', FakeSubMaster), \
       mock.patch.object(controlsd.messaging, 'PubMaster', return_value=pm):
    c = controlsd.Controls()
  sm = c.sm
  sd = sm['selfdriveState']
  sd.enabled = sd.active = True
  sd.state = State.enabled
  cs = sm['carState']
  cs.vEgo, cs.vCruise, cs.canValid = 25., 100., True
  sm['longitudinalPlan'].aTarget = 1.5
  sm['vehicleParameters'].steerRatio = CP.steerRatio
  sm['vehicleParameters'].stiffnessFactor = 1.0
  return SimpleNamespace(c=c, sm=sm, pm=pm)


def step(t):
  CC, lac_log = t.c.state_control()
  t.c.publish(CC, lac_log)
  return SimpleNamespace(accel=CC.actuators.accel, force_decel=t.pm.sent['controlsState'].controlsState.forceDecel)


class TestStockAebCallSite(OpenpilotTestCase):
  def test_no_drive_from_the_first_aeb_frame(self):
    t = controls()
    before = [step(t).accel for _ in range(100)]
    self.assertTrue(all(a > 0. for a in before[50:]), "the controller requests drive before the event")
    # the car brakes hard on its own, as in a real event
    t.sm['carState'].stockAeb = True
    t.sm['carState'].aEgo = -5.0
    during = [step(t).accel for _ in range(50)]
    self.assertTrue(all(a <= 0. for a in during), during[:3])

  def test_braking_kept_during_aeb(self):
    t = controls()
    t.sm['carState'].stockAeb = True
    t.sm['longitudinalPlan'].aTarget = -2.0
    out = [step(t).accel for _ in range(100)]
    self.assertLess(out[-1], -1.0)

  def test_no_aeb_unchanged(self):
    t = controls()
    self.assertGreater([step(t).accel for _ in range(100)][-1], 0.)


class TestMinimumRiskCallSite(OpenpilotTestCase):
  def test_force_decel_held_while_latched(self):
    t = controls()
    self.assertFalse(step(t).force_decel)
    t.sm['selfdriveState'].minimumRiskManeuver = True
    # the DM request has dropped (dmonitoringd restart, awareness reset): the latch alone keeps the stop
    t.sm['driverMonitoringState'].noResponseForceDecel = False
    self.assertTrue(all(step(t).force_decel for _ in range(10)))

  def test_force_decel_from_dm_request_and_soft_disable(self):
    t = controls()
    t.sm['driverMonitoringState'].noResponseForceDecel = True
    self.assertTrue(step(t).force_decel)
    t.sm['driverMonitoringState'].noResponseForceDecel = False
    t.sm['selfdriveState'].state = State.softDisabling
    self.assertTrue(step(t).force_decel)

  def test_force_decel_reaches_the_car(self):
    t = controls()
    t.sm['selfdriveState'].minimumRiskManeuver = True
    step(t)
    self.assertTrue(t.pm.sent['carControl'].carControl.driverMonitoringEscalation)


class TestHarness(OpenpilotTestCase):
  def test_inputs_judged_fresh(self):
    # the real freshness check runs and passes, so lateral and longitudinal control are active
    t = controls()
    CC, _ = t.c.state_control()
    self.assertTrue(CC.longActive and CC.latActive)


class TestFreshnessGateCallSite(OpenpilotTestCase):
  # SWF-040.C1, SWF-043.C1 (TSR-602): controlsd drops lateral or longitudinal control when one of its inputs is stale.
  # The gate logic is tested in test_input_freshness.py; this checks the inputs controlsd passes and what it gates
  NS = 1e9

  def gated(self, stale=None, alive_sd=True):
    t = controls()
    for s in t.sm.logMonoTime:
      t.sm.logMonoTime[s] = int(10 * self.NS)
    if stale:
      t.sm.logMonoTime[stale] = int(9 * self.NS)  # 1 s old: past the bound for every input
    t.sm.alive['selfdriveState'] = alive_sd
    CC, _ = t.c.state_control()
    return CC.latActive, CC.longActive

  def test_all_fresh(self):
    self.assertEqual(self.gated(), (True, True))

  def test_stale_model_ends_lateral_only(self):
    self.assertEqual(self.gated('modelV2'), (False, True))

  def test_stale_plan_ends_longitudinal_only(self):
    self.assertEqual(self.gated('longitudinalPlan'), (True, False))

  def test_stale_car_state_ends_both(self):
    self.assertEqual(self.gated('carState'), (False, False))

  def test_selfdrive_state_not_alive_ends_both(self):
    self.assertEqual(self.gated(alive_sd=False), (False, False))


class TestLateralResetCallSite(OpenpilotTestCase):
  # SWF-042.C1: when lateral control ends, controlsd resets the reference car's torque controller, integrator included
  def test_integrator_cleared_when_lateral_control_ends(self):
    t = controls()
    t.sm['modelV2'].action.desiredCurvature = 0.0005
    for _ in range(300):
      step(t)
    assert t.c.LaC.pid.i != 0.
    t.sm['selfdriveState'].active = False
    step(t)
    assert t.c.LaC.pid.i == 0.


class TestNonFiniteInputs(OpenpilotTestCase):
  # SWF-045.C1, SWF-045.C2, SWF-047.C1 (TSR-604, SWF-ACT-044): a non-finite input for one step must not reach the
  # controllers, whose state (integrator, desired curvature) would otherwise keep it for the rest of the drive, and must not
  # raise. Run through the real Controls.state_control with the reference CarParams
  WARM, BAD, AFTER = 200, 1, 50

  def run_with(self, set_bad, set_good):
    t = controls()
    t.sm['modelV2'].action.desiredCurvature = 0.0005
    for _ in range(self.WARM):
      step(t)
    set_bad(t.sm)
    bad = t.c.state_control()[0]
    finite_during = math.isfinite(t.c.curvature) and math.isfinite(t.c.desired_curvature)
    set_good(t.sm)
    for _ in range(self.AFTER):
      CC, _ = t.c.state_control()
    return t, bad, CC, finite_during

  def assert_controllers_finite(self, t, CC):
    for name, v in (('lateral integrator', t.c.LaC.pid.i), ('longitudinal integrator', t.c.LoC.pid.i),
                    ('desired curvature', t.c.desired_curvature), ('torque', CC.actuators.torque), ('accel', CC.actuators.accel)):
      self.assertTrue(math.isfinite(v), f'{name} is {v}')
    self.assertNotEqual(CC.actuators.torque, 0.0)  # lateral control works again, not a sanitized 0
    self.assertGreater(CC.actuators.accel, 0.0)

  def test_non_finite_desired_curvature(self):
    for bad in (float('nan'), float('inf')):
      def set_bad(sm, bad=bad):
        sm['modelV2'].action.desiredCurvature = bad
      t, CCbad, CC, _ = self.run_with(set_bad, lambda sm: setattr(sm['modelV2'].action, 'desiredCurvature', 0.0005))
      self.assertFalse(CCbad.latActive)
      self.assert_controllers_finite(t, CC)

  def test_non_finite_roll(self):
    t, CCbad, CC, finite_during = self.run_with(lambda sm: setattr(sm['vehicleParameters'], 'roll', float('nan')),
                                                lambda sm: setattr(sm['vehicleParameters'], 'roll', 0.0))
    self.assertFalse(CCbad.latActive)
    self.assertTrue(finite_during)
    self.assert_controllers_finite(t, CC)

  def test_non_finite_acceleration_target(self):
    t, CCbad, CC, _ = self.run_with(lambda sm: setattr(sm['longitudinalPlan'], 'aTarget', float('nan')),
                                    lambda sm: setattr(sm['longitudinalPlan'], 'aTarget', 1.5))
    self.assertFalse(CCbad.longActive)
    self.assert_controllers_finite(t, CC)

  def test_non_finite_lateral_delay_does_not_raise(self):
    t, _, CC, _ = self.run_with(lambda sm: setattr(sm['lateralDelay'], 'lateralDelay', float('nan')),
                                lambda sm: setattr(sm['lateralDelay'], 'lateralDelay', 0.2))
    self.assert_controllers_finite(t, CC)


class TestNonFinitePoseToCard(OpenpilotTestCase):
  # SWF-060.C1 (SWF-ACT-044): controlsd forwards the calibrated orientation to card, and the reference car's CarController filters the
  # pitch for its compensation. A single non-finite orientation must not reach it (controlsd sends the last finite one again): the NaN
  # would stay in the filter and card would raise on packing the acceleration (card has no exception handling), ending lateral and
  # longitudinal control. Run through the real controlsd publish and the real Toyota CarInterface.apply
  STEPS = 100

  @staticmethod
  def pose(pitch):
    def m(xyz):
      return Measurement(np.array(xyz, dtype=float), np.zeros(3))
    return Pose(orientation=m([0., pitch, 0.]), velocity=m([25., 0., 0.]), acceleration=m([0., 0., 0.]),
                angular_velocity=m([0., 0., pitch]))

  def drive(self, bad):
    t = controls()
    CI = interfaces[REFERENCE](t.c.CP)
    out = []
    for i in range(self.STEPS):
      t.c.calibrated_pose = self.pose(bad if i == self.STEPS // 2 else 0.02)
      CC, lac_log = t.c.state_control()
      t.c.publish(CC, lac_log)
      sent = t.pm.sent['carControl'].carControl
      actuators, _ = CI.apply(sent.as_reader(), int(i * 1e7))  # raises if a NaN reaches the packer
      out.append((sent, actuators.accel))
    return out

  def test_non_finite_orientation_not_sent_and_card_keeps_running(self):
    for bad in (float('nan'), float('inf')):
      out = self.drive(bad)
      sent, _ = out[self.STEPS // 2]
      # the last finite values are sent again, so the planner keeps its coast limit (SWF-065.C3)
      self.assertAlmostEqual(sent.orientationNED[1], 0.02, places=6)
      self.assertAlmostEqual(sent.angularVelocity[2], 0.02, places=6)
      self.assertTrue(all(math.isfinite(a) for _, a in out), bad)
      self.assertGreater(out[-1][1], 0.)

  def test_finite_orientation_sent(self):
    sent, _ = self.drive(0.02)[-1]
    self.assertAlmostEqual(sent.orientationNED[1], 0.02, places=6)
