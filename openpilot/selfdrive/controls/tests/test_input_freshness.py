from openpilot.selfdrive.controls.lib.input_freshness import inputs_fresh

FREQ = {'selfdriveState': 100., 'carState': 100., 'modelV2': 20., 'longitudinalPlan': 20.}
SERVICES = ('selfdriveState', 'carState', 'modelV2')
NS = 1e9


def check(times, seen=None, alive_sd=True):
  seen = seen or dict.fromkeys(FREQ, True)
  alive = dict.fromkeys(FREQ, True)
  alive['selfdriveState'] = alive_sd
  return inputs_fresh(SERVICES, seen, alive, times, FREQ)


class TestInputsFresh:
  def test_all_current(self):
    assert check({'selfdriveState': 10 * NS, 'carState': 10 * NS - 0.01 * NS, 'modelV2': 10 * NS - 0.05 * NS})

  def test_model_at_the_bound_is_fresh(self):
    # 10 periods of 20 Hz = 0.5 s
    assert check({'selfdriveState': 10 * NS, 'carState': 10 * NS, 'modelV2': 10 * NS - 0.5 * NS})

  def test_model_past_the_bound_is_stale(self):
    assert not check({'selfdriveState': 10 * NS, 'carState': 10 * NS, 'modelV2': 10 * NS - 0.51 * NS})

  def test_car_state_stale(self):
    # 10 periods of 100 Hz = 0.1 s
    assert not check({'selfdriveState': 10 * NS, 'carState': 10 * NS - 0.11 * NS, 'modelV2': 10 * NS})

  def test_selfdrive_state_judged_on_wall_clock(self):
    assert not check({'selfdriveState': 10 * NS, 'carState': 10 * NS, 'modelV2': 10 * NS}, alive_sd=False)

  def test_unseen_input_is_not_stale(self):
    seen = dict.fromkeys(FREQ, True)
    seen['modelV2'] = False
    assert check({'selfdriveState': 10 * NS, 'carState': 10 * NS, 'modelV2': 0}, seen=seen)
