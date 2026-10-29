from opendbc.car.structs import car
from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.cereal import log
from openpilot.common.realtime import DT_CTRL
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.selfdrived.selfdrived import FCW_FREQUENCY, SelfdriveD
from openpilot.selfdrive.selfdrived.supervision import fcw_inputs_fresh

# TSR-625 (SWSR-625): FCW only from a modelV2 and a longitudinalPlan that are valid and received within 2 nominal periods
# (0.1 s at 20 Hz, 10 selfdrived frames). SWF-051.C1

EventName = log.OnroadEvent.EventName
FREQ = {'modelV2': 20., 'longitudinalPlan': 20.}


def fresh(age_model=0, age_plan=0, valid_model=True, valid_plan=True, frame=1000):
  valid = {'modelV2': valid_model, 'longitudinalPlan': valid_plan}
  recv = {'modelV2': frame - age_model, 'longitudinalPlan': frame - age_plan}
  return fcw_inputs_fresh(valid, recv, frame, FREQ, DT_CTRL)


class TestFcwInputsFresh(OpenpilotTestCase):
  def test_fresh_and_valid(self):
    assert fresh()
    assert fresh(age_model=4, age_plan=4)  # one 20 Hz period between messages

  def test_two_periods_is_the_bound(self):
    assert fresh(age_model=10, age_plan=10)
    assert not fresh(age_model=11)
    assert not fresh(age_plan=11)

  def test_invalid(self):
    assert not fresh(valid_model=False)
    assert not fresh(valid_plan=False)

  def test_never_received(self):
    valid = dict.fromkeys(FREQ, True)
    assert not fcw_inputs_fresh(valid, {'modelV2': 0, 'longitudinalPlan': 5}, 5, FREQ, DT_CTRL)
    assert not fcw_inputs_fresh(valid, {'modelV2': 5, 'longitudinalPlan': 0}, 5, FREQ, DT_CTRL)


class TestFcwInSelfdrived(OpenpilotTestCase):
  """The real SelfdriveD.update_events with a model hard-brake prediction"""

  def setUp(self):
    super().setUp()
    self.make()

  def make(self):
    CP = car.CarParams.new_message()
    CP.carFingerprint = TOYOTA.TOYOTA_COROLLA_TSS2
    self.sd = SelfdriveD(CP=CP.as_reader())
    self.sd.initialized = True
    sm = self.sd.sm
    sm.data['modelV2'] = log.Event.new_message().init('modelV2')
    sm.data['modelV2'].meta.hardBrakePredicted = True
    sm.frame = 1000
    for s in FCW_FREQUENCY:
      sm.valid[s] = True
      sm.recv_frame[s] = sm.frame

  def fcw(self):
    self.sd.update_events(car.CarState.new_message())
    return EventName.fcw in self.sd.events.names

  def test_fcw_from_fresh_inputs(self):
    assert self.fcw()

  def test_no_fcw_from_stale_model(self):
    self.sd.sm.recv_frame['modelV2'] = self.sd.sm.frame - 11
    assert not self.fcw()

  def test_no_fcw_from_stale_plan(self):
    self.sd.sm.recv_frame['longitudinalPlan'] = self.sd.sm.frame - 11
    assert not self.fcw()

  def test_no_fcw_from_invalid_input(self):
    for s in FCW_FREQUENCY:
      self.make()
      self.sd.sm.valid[s] = False
      assert not self.fcw(), s
