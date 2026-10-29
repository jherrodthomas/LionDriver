"""LionDriver host supervision of the panda's reports (TSR-615, TSR-621). Pure logic, unit-tested in tests/test_supervision.py."""


class ControlsMismatch:
  """TSR-621: controlsAllowed false while engaged triggers after `samples` consecutive pandaStates samples (transport skew
  between the CAN and pandaStates sockets), and in any case `max_time` after the first mismatched frame (stale pandaStates).
  A sample with controlsAllowed true, or disengaging, starts the count again.

  `engage_grace`: samples taken within this time after engaging are not counted, because the panda grants authority only
  once the heartbeat reports openpilot engaged (WP-A-05 LS-06), which takes up to two pandad periods. The `max_time`
  bound still runs from the first mismatched frame, so a panda that never grants is detected within `max_time`."""

  def __init__(self, samples: int, max_time: float, dt: float, engage_grace: float = 0.0):
    self.samples = samples
    self.max_frames = round(max_time / dt)
    self.grace_frames = round(engage_grace / dt)
    self.count = 0
    self.start_frame: int | None = None
    self.enabled_prev = False
    self.enabled_frame: int | None = None

  def update(self, mismatch: bool, new_sample: bool, frame: int, enabled: bool = True) -> None:
    if enabled and not self.enabled_prev:
      self.enabled_frame = frame
    self.enabled_prev = enabled
    if not mismatch:
      self.count = 0
      self.start_frame = None
      return
    if self.start_frame is None:
      self.start_frame = frame
    in_grace = self.enabled_frame is not None and frame - self.enabled_frame < self.grace_frames
    if new_sample and not in_grace:
      self.count += 1

  def triggered(self, frame: int) -> bool:
    if self.start_frame is None:
      return False
    return self.count >= self.samples or frame - self.start_frame >= self.max_frames


class TxBlockedMonitor:
  """TSR-615: a rise of a panda's safetyTxBlocked count between two pandaStates samples while engaged. The first sample of
  each panda only sets the baseline, and a lower count (panda reset) moves it down."""

  def __init__(self):
    self.last: dict[int, int] = {}

  def update(self, index: int, count: int, engaged: bool) -> bool:
    previous = self.last.get(index)
    self.last[index] = count
    return engaged and previous is not None and count > previous


FCW_INPUTS = ('modelV2', 'longitudinalPlan')
FCW_MAX_AGE_PERIODS = 2.


def fcw_inputs_fresh(valid: dict, recv_frame: dict, frame: int, frequency: dict, dt: float) -> bool:
  """TSR-625 (SWSR-625): FCW only from inputs that are valid and received within 2 nominal periods, in selfdrived frames
  (the loop clock, so a process replay gives the same answer as the drive). An input never received is not fresh."""
  for s in FCW_INPUTS:
    if not valid[s] or recv_frame[s] <= 0:
      return False
    if (frame - recv_frame[s]) * dt > FCW_MAX_AGE_PERIODS / frequency[s]:
      return False
  return True
