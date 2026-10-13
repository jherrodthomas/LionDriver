from openpilot.selfdrive.selfdrived.supervision import ControlsMismatch, TxBlockedMonitor

DT = 0.01  # selfdrived runs at 100 Hz; pandaStates arrives at 10 Hz


def run(mismatch_frames, sample_every=10, samples=2, max_time=0.5):
  """Feed `mismatch_frames` frames of mismatch; return the frame offset at which the check triggers, or None."""
  cm = ControlsMismatch(samples, max_time, DT)
  for f in range(mismatch_frames):
    cm.update(True, f % sample_every == 0, f)
    if cm.triggered(f):
      return f
  return None


class TestControlsMismatch:
  def test_triggers_on_second_consecutive_sample(self):
    # first sample at frame 0, second at frame 10: 0.1 s, inside the 0.5 s bound of TSR-621
    assert run(100) == 10

  def test_single_sample_is_absorbed(self):
    cm = ControlsMismatch(2, 0.5, DT)
    cm.update(True, True, 0)
    assert not cm.triggered(0)
    for f in range(1, 10):
      cm.update(True, False, f)
      assert not cm.triggered(f)
    cm.update(False, True, 10)  # next sample agrees
    assert not cm.triggered(10)
    assert cm.count == 0 and cm.start_frame is None

  def test_samples_must_be_consecutive(self):
    # a 200-sample cumulative count (the upstream rule) would trigger here eventually; alternating samples never must
    cm = ControlsMismatch(2, 0.5, DT)
    for k in range(100):
      f = 10 * k
      mismatch = k % 2 == 0
      cm.update(mismatch, True, f)
      assert not cm.triggered(f)

  def test_time_bound_with_stale_samples(self):
    # pandaStates stops arriving after the first mismatched sample: the time bound triggers at 0.5 s
    cm = ControlsMismatch(2, 0.5, DT)
    triggered = None
    for f in range(200):
      cm.update(True, f == 0, f)
      if cm.triggered(f):
        triggered = f
        break
    assert triggered == 50

  def test_not_triggered_without_mismatch(self):
    cm = ControlsMismatch(2, 0.5, DT)
    for f in range(1000):
      cm.update(False, f % 10 == 0, f)
      assert not cm.triggered(f)


class TestTxBlockedMonitor:
  def test_first_sample_sets_baseline(self):
    m = TxBlockedMonitor()
    assert not m.update(0, 5, True)

  def test_rise_while_engaged(self):
    m = TxBlockedMonitor()
    m.update(0, 5, True)
    assert m.update(0, 6, True)
    assert not m.update(0, 6, True)

  def test_rise_while_disengaged_moves_baseline(self):
    m = TxBlockedMonitor()
    m.update(0, 5, False)
    assert not m.update(0, 9, False)
    assert not m.update(0, 9, True)
    assert m.update(0, 10, True)

  def test_panda_reset_lowers_baseline(self):
    m = TxBlockedMonitor()
    m.update(0, 50, True)
    assert not m.update(0, 0, True)
    assert m.update(0, 1, True)

  def test_pandas_are_independent(self):
    m = TxBlockedMonitor()
    m.update(0, 5, True)
    m.update(1, 7, True)
    assert not m.update(1, 7, True)
    assert m.update(0, 6, True)
