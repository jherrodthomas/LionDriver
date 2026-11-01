from unittest import mock

from opendbc.car.structs import car
from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.cereal import log
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.selfdrived.selfdrived import MISMATCH_ENGAGE_GRACE, MISMATCH_MAX_TIME, SelfdriveD
from openpilot.common.realtime import DT_CTRL

# The selfdrived call sites of the panda status supervision (SW FMEA SWF-034.C1, SWF-032.C3, SWF-ACT-055), run through
# the real SelfdriveD.data_sample and update_events. The logic is tested in test_supervision.py; this checks that
# selfdrived feeds it from pandaStates and raises the events:
#   TSR-621: controlsAllowed false while enabled gives controlsMismatch within MISMATCH_MAX_TIME of the first frame
#   TSR-615: a rise of safetyTxBlocked while enabled gives pandaTxBlocked; txRateExceeded and heartbeatLost give their events

EventName = log.OnroadEvent.EventName
SAMPLE_EVERY = 10  # pandaStates at 10 Hz, selfdrived at 100 Hz


class TestPandaSupervisionCallSites(OpenpilotTestCase):
  def setUp(self):
    super().setUp()
    CP = car.CarParams.new_message()
    CP.carFingerprint = TOYOTA.TOYOTA_COROLLA_TSS2
    self.sd = SelfdriveD(CP=CP.as_reader())
    self.sd.initialized = True
    self.sd.CS_prev = car.CarState.new_message()
    sm = self.sd.sm
    patcher = mock.patch.object(sm, 'update')  # the test sets the received data
    patcher.start()
    self.addCleanup(patcher.stop)
    sm.frame = 100  # under 10 s: the safety-mode check of the same event is not armed yet
    sm.data['pandaStates'] = [log.PandaState.new_message()]
    self.ps.safetyModel = car.CarParams.SafetyModel.toyota
    self.ps.controlsAllowed = True

  @property
  def ps(self):
    return self.sd.sm.data['pandaStates'][0]

  def step(self):
    """One selfdrived frame; returns the events raised"""
    sm = self.sd.sm
    sm.frame += 1
    sm.updated['pandaStates'] = sm.frame % SAMPLE_EVERY == 0
    CS = self.sd.data_sample()
    self.sd.update_events(CS)
    return self.sd.events.names

  def engage(self, frames=100):
    self.sd.enabled = True
    for _ in range(frames):
      self.step()

  def frames_to_mismatch(self, limit=200):
    for n in range(1, limit + 1):
      if EventName.controlsMismatch in self.step():
        return n
    return None

  def test_controls_mismatch_raised(self):
    self.engage()
    self.ps.controlsAllowed = False
    n = self.frames_to_mismatch()
    assert n is not None and n * DT_CTRL <= MISMATCH_MAX_TIME + 1e-9, n

  def test_controls_mismatch_within_the_bound_right_after_engaging(self):
    # a panda that never grants is detected within MISMATCH_MAX_TIME of engaging, the grace notwithstanding
    self.ps.controlsAllowed = False
    self.sd.enabled = True
    n = self.frames_to_mismatch()
    assert n is not None and MISMATCH_ENGAGE_GRACE < n * DT_CTRL <= MISMATCH_MAX_TIME + 1e-9, n

  def test_no_mismatch_while_allowed_or_disengaged(self):
    self.engage()
    for _ in range(200):
      assert EventName.controlsMismatch not in self.step()
    self.sd.enabled = False
    self.ps.controlsAllowed = False
    for _ in range(200):
      assert EventName.controlsMismatch not in self.step()

  def test_tx_blocked_rise_while_engaged(self):
    self.ps.safetyTxBlocked = 5
    self.engage()
    self.ps.safetyTxBlocked = 6
    raised = [EventName.pandaTxBlocked in self.step() for _ in range(SAMPLE_EVERY)]
    assert any(raised)
    for _ in range(50):
      assert EventName.pandaTxBlocked not in self.step()  # no further rise

  def test_tx_rate_and_heartbeat_flags(self):
    self.engage()
    for flag, event in (('txRateExceeded', EventName.pandaTxRateExceeded), ('heartbeatLost', EventName.pandaHeartbeatLost)):
      assert event not in self.step()
      setattr(self.ps, flag, True)
      assert event in self.step()
      setattr(self.ps, flag, False)
