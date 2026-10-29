from types import SimpleNamespace
from unittest import mock

from opendbc.car.car_helpers import interfaces
from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.cereal import log
from openpilot.common.params import Params
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.controls import controlsd

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
