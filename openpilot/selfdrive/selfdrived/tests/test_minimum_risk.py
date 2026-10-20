from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.selfdrived.minimum_risk import MinimumRiskManeuver


class TestMinimumRiskManeuver(OpenpilotTestCase):
  """TSR-633 (DQ-365 A): stop, stay stopped and held, and do not resume until the driver takes over."""

  def test_off_until_the_dm_requests_it(self):
    mrm = MinimumRiskManeuver()
    assert not any(mrm.update(True, False) for _ in range(100))

  def test_stays_latched_when_the_dm_request_drops(self):
    # e.g. dmonitoringd restarts, or its awareness resets: the car must not drive off again
    mrm = MinimumRiskManeuver()
    assert mrm.update(True, True)
    assert all(mrm.update(True, False) for _ in range(6000))   # one minute at 100 Hz, held

  def test_ends_only_when_the_driver_takes_over(self):
    mrm = MinimumRiskManeuver()
    mrm.update(True, True)
    assert not mrm.update(False, False)                         # brake or cancel: the item disengages
    assert not mrm.update(True, False)                          # a new engagement starts clean

  def test_not_set_while_disengaged(self):
    mrm = MinimumRiskManeuver()
    assert not mrm.update(False, True)
