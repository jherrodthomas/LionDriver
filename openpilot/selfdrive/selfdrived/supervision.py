"""LionDriver host supervision of the panda's reports (TSR-615, TSR-621). Pure logic, unit-tested in tests/test_supervision.py."""


class ControlsMismatch:
  """TSR-621: controlsAllowed false while engaged triggers after `samples` consecutive pandaStates samples (transport skew
  between the CAN and pandaStates sockets), and in any case `max_time` after the first mismatched frame (stale pandaStates).
  A sample with controlsAllowed true, or disengaging, starts the count again."""

  def __init__(self, samples: int, max_time: float, dt: float):
    self.samples = samples
    self.max_frames = round(max_time / dt)
    self.count = 0
    self.start_frame: int | None = None

  def update(self, mismatch: bool, new_sample: bool, frame: int) -> None:
    if not mismatch:
      self.count = 0
      self.start_frame = None
      return
    if self.start_frame is None:
      self.start_frame = frame
    if new_sample:
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
