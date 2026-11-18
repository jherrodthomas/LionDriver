from openpilot.cereal import log
from openpilot.common.realtime import DT_CTRL
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.selfdrived.events import EVENTS, ET, Events, NormalPermanentAlert
from openpilot.selfdrive.selfdrived.state import SOFT_DISABLE_TIME, StateMachine

# Requirements-based tests of the selfdrived transitions the driver causes (WP-W-05 §5.3 X2, E2, O2, P1; DQ-151 A):
#   SWSR-302h (TSR-302, TSR-308)  X2: a driver disengagement (USER_DISABLE) ends the engagement in the same cycle
#   SWSR-302i (TSR-302)           P1, P2: the pre-enable phase (brake held at standstill) and how it ends;
#                                 P2: a soft disable ends the attempt at once (DQ-433 A)
#   SWSR-305h (TSR-305)           E2: a driver override while enabled keeps the engagement (overriding)
#   SWSR-305i (TSR-305)           O2: the end of an override returns to enabled without a new engagement request

State = log.SelfdriveState.OpenpilotState
EventName = log.OnroadEvent.EventName

ENGAGED_STATES = (State.preEnabled, State.enabled, State.softDisabling, State.overriding)
# the event types that keep each engaged state
MAINTAIN = {State.preEnabled: [ET.PRE_ENABLE], State.enabled: [], State.softDisabling: [ET.SOFT_DISABLE],
            State.overriding: [ET.OVERRIDE_LATERAL]}
OVERRIDES = ([ET.OVERRIDE_LATERAL], [ET.OVERRIDE_LONGITUDINAL], [ET.OVERRIDE_LATERAL, ET.OVERRIDE_LONGITUDINAL])
SOFT_DISABLE_CYCLES = int(SOFT_DISABLE_TIME / DT_CTRL)


def make_event(event_types):
  # as test_state_machine.py: one synthetic event (name 0) that carries the given event types
  EVENTS[0] = {et: NormalPermanentAlert("alert") for et in event_types}
  return 0


class _Base(OpenpilotTestCase):
  def setup_method(self):
    self.sm = StateMachine()
    self.events = Events()

  def step(self, state, event_types, timer=None):
    if state is not None:
      self.sm.state = state
    if timer is not None:
      self.sm.soft_disable_timer = timer
    self.events.clear()
    if event_types:
      self.events.add(make_event(event_types))
    return self.sm.update(self.events)

  def step_named(self, state, names):
    self.sm.state = state
    self.events.clear()
    for name in names:
      self.events.add(name)
    return self.sm.update(self.events)


class TestDriverDisengagement(_Base):
  """SWSR-302h (X2)."""

  def test_user_disable_ends_every_engaged_state_in_the_same_cycle(self):
    for state in ENGAGED_STATES:
      for timer in (SOFT_DISABLE_CYCLES, 1):
        assert self.step(state, MAINTAIN[state] + [ET.USER_DISABLE], timer) == (False, False), state
        assert self.sm.state == State.disabled
        assert ET.USER_DISABLE in self.sm.current_alert_types
        assert ET.WARNING not in self.sm.current_alert_types

  def test_user_disable_has_priority_over_soft_disable_override_and_pre_enable(self):
    others = [ET.SOFT_DISABLE, ET.OVERRIDE_LATERAL, ET.OVERRIDE_LONGITUDINAL, ET.PRE_ENABLE]
    for state in ENGAGED_STATES:
      assert self.step(state, others + [ET.USER_DISABLE], SOFT_DISABLE_CYCLES) == (False, False), state
      assert self.sm.state == State.disabled
      assert self.sm.current_alert_types == [ET.PERMANENT, ET.USER_DISABLE]

  def test_immediate_disable_has_priority_over_user_disable(self):
    for state in ENGAGED_STATES:
      self.step(state, MAINTAIN[state] + [ET.USER_DISABLE, ET.IMMEDIATE_DISABLE])
      assert self.sm.state == State.disabled
      assert ET.IMMEDIATE_DISABLE in self.sm.current_alert_types
      assert ET.USER_DISABLE not in self.sm.current_alert_types

  def test_driver_disengagement_events_are_user_disable(self):
    # cruise off (PCM cars), cancel button, brake (or gas with DisengageOnAccelerator), steering disengage
    for name in (EventName.pcmDisable, EventName.buttonCancel, EventName.pedalPressed, EventName.steerDisengage):
      assert ET.USER_DISABLE in EVENTS[name], name
      for state in ENGAGED_STATES:
        assert self.step_named(state, [name]) == (False, False), (name, state)
        assert self.sm.state == State.disabled


class TestPreEnable(_Base):
  """SWSR-302i (P1)."""

  def test_brake_held_at_standstill_is_pre_enable(self):
    assert ET.PRE_ENABLE in EVENTS[EventName.preEnableStandstill]
    self.step_named(State.disabled, [EventName.buttonEnable, EventName.preEnableStandstill])
    assert self.sm.state == State.preEnabled

  def test_pre_enabled_is_enabled_but_not_active(self):
    for _ in range(3):
      assert self.step(State.preEnabled, [ET.PRE_ENABLE]) == (True, False)
      assert self.sm.state == State.preEnabled
      assert self.sm.current_alert_types == [ET.PERMANENT, ET.PRE_ENABLE]

  def test_end_of_pre_enable_goes_to_enabled(self):
    assert self.step(State.preEnabled, []) == (True, True)
    assert self.sm.state == State.enabled
    assert ET.ENABLE not in self.sm.current_alert_types

  def test_disable_events_end_the_attempt(self):
    for et in (ET.USER_DISABLE, ET.IMMEDIATE_DISABLE):
      assert self.step(State.preEnabled, [ET.PRE_ENABLE, et]) == (False, False)
      assert self.sm.state == State.disabled
      assert et in self.sm.current_alert_types

  def test_soft_disable_ends_the_attempt_at_once(self):
    # DQ-433 A: a soft-disable fault during the wait ends the attempt in the same cycle, with the soft-disable alert,
    # whether or not the brake is still held
    for held in ([ET.PRE_ENABLE], []):
      assert self.step(State.preEnabled, held + [ET.SOFT_DISABLE], 0) == (False, False), held
      assert self.sm.state == State.disabled
      assert ET.SOFT_DISABLE in self.sm.current_alert_types
      assert ET.PRE_ENABLE not in self.sm.current_alert_types

  def test_no_actuation_after_a_soft_disable_in_pre_enabled(self):
    # the car never becomes active: brake release afterwards needs a new engagement request
    self.step(State.preEnabled, [ET.PRE_ENABLE, ET.SOFT_DISABLE], 0)
    for _ in range(SOFT_DISABLE_CYCLES + 10):
      assert self.step(None, []) == (False, False)
      assert self.sm.state == State.disabled

  def test_user_and_immediate_disable_keep_priority_over_soft_disable(self):
    for et in (ET.USER_DISABLE, ET.IMMEDIATE_DISABLE):
      assert self.step(State.preEnabled, [ET.PRE_ENABLE, ET.SOFT_DISABLE, et]) == (False, False)
      assert et in self.sm.current_alert_types
      assert ET.SOFT_DISABLE not in self.sm.current_alert_types


class TestOverrideEntry(_Base):
  """SWSR-305h (E2)."""

  def test_override_while_enabled_keeps_the_engagement(self):
    for ov in OVERRIDES:
      assert self.step(State.enabled, ov) == (True, True), ov
      assert self.sm.state == State.overriding
      for et in (ET.OVERRIDE_LATERAL, ET.OVERRIDE_LONGITUDINAL, ET.WARNING):
        assert et in self.sm.current_alert_types
      assert ET.USER_DISABLE not in self.sm.current_alert_types

  def test_held_override_stays_engaged(self):
    self.step(State.enabled, [ET.OVERRIDE_LONGITUDINAL])
    for _ in range(500):
      assert self.step(None, [ET.OVERRIDE_LONGITUDINAL]) == (True, True)
      assert self.sm.state == State.overriding

  def test_soft_disable_has_priority_over_override(self):
    for ov in OVERRIDES:
      self.step(State.enabled, ov + [ET.SOFT_DISABLE], 0)
      assert self.sm.state == State.softDisabling
      assert self.sm.soft_disable_timer == SOFT_DISABLE_CYCLES

  def test_driver_override_events(self):
    assert ET.OVERRIDE_LATERAL in EVENTS[EventName.steerOverride]
    assert ET.OVERRIDE_LONGITUDINAL in EVENTS[EventName.gasPressedOverride]
    for name in (EventName.steerOverride, EventName.gasPressedOverride):
      assert ET.USER_DISABLE not in EVENTS[name] and ET.IMMEDIATE_DISABLE not in EVENTS[name]
      assert self.step_named(State.enabled, [name]) == (True, True)
      assert self.sm.state == State.overriding


class TestOverrideEnd(_Base):
  """SWSR-305i (O2)."""

  def test_end_of_override_returns_to_enabled(self):
    assert self.step(State.overriding, []) == (True, True)
    assert self.sm.state == State.enabled
    assert self.sm.current_alert_types == [ET.PERMANENT, ET.WARNING]  # no new ENABLE alert

  def test_override_held_stays_overriding(self):
    for ov in OVERRIDES:
      assert self.step(State.overriding, ov) == (True, True)
      assert self.sm.state == State.overriding

  def test_soft_disable_while_overriding_starts_the_soft_disable(self):
    for ov in ([], *OVERRIDES):
      self.step(State.overriding, ov + [ET.SOFT_DISABLE], 0)
      assert self.sm.state == State.softDisabling
      assert self.sm.soft_disable_timer == SOFT_DISABLE_CYCLES
      assert ET.SOFT_DISABLE in self.sm.current_alert_types

  def test_override_round_trip(self):
    self.step(State.enabled, [ET.OVERRIDE_LATERAL])
    assert self.sm.state == State.overriding
    self.step(None, [])
    assert self.sm.state == State.enabled
    self.step(None, [])
    assert self.sm.state == State.enabled
