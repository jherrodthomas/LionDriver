from types import SimpleNamespace

from opendbc.car.structs import car
from openpilot.common.test import OpenpilotTestCase
from openpilot.cereal import log
from openpilot.common.realtime import DT_DMON
from openpilot.selfdrive.monitoring.policy import DriverMonitoring, DRIVER_MONITOR_SETTINGS

EventName = log.OnroadEvent.EventName
dm_settings = DRIVER_MONITOR_SETTINGS()

TEST_TIMESPAN = 120  # seconds
DISTRACTED_SECONDS_TO_ORANGE = dm_settings._VISION_POLICY_ALERT_2_TIMEOUT + 1
DISTRACTED_SECONDS_TO_RED = dm_settings._VISION_POLICY_ALERT_3_TIMEOUT + 1
INVISIBLE_SECONDS_TO_ORANGE = dm_settings._WHEELTOUCH_POLICY_ALERT_2_TIMEOUT + 1
INVISIBLE_SECONDS_TO_RED = dm_settings._WHEELTOUCH_POLICY_ALERT_3_TIMEOUT + 1

def make_msg(face_detected, distracted=False, model_uncertain=False):
  ds = log.DriverStateV2.new_message()
  ds.leftDriverData.faceOrientation = [0., 0., 0.]
  ds.leftDriverData.facePosition = [0., 0.]
  ds.leftDriverData.faceProb = 1. * face_detected
  ds.leftDriverData.leftEyeProb = 1.
  ds.leftDriverData.rightEyeProb = 1.
  ds.leftDriverData.leftBlinkProb = 1. * distracted
  ds.leftDriverData.rightBlinkProb = 1. * distracted
  ds.leftDriverData.faceOrientationStd = [1.*model_uncertain, 1.*model_uncertain, 1.*model_uncertain]
  ds.leftDriverData.facePositionStd = [1.*model_uncertain, 1.*model_uncertain]
  # TODO: test both separately when e2e is used
  ds.leftDriverData.phoneProb = 0.
  ds.leftDriverData.sleepProb = 0.
  return ds


# driver state from neural net, 10Hz
msg_NO_FACE_DETECTED = make_msg(False)
msg_ATTENTIVE = make_msg(True)
msg_DISTRACTED = make_msg(True, distracted=True)
msg_ATTENTIVE_UNCERTAIN = make_msg(True, model_uncertain=True)
msg_DISTRACTED_UNCERTAIN = make_msg(True, distracted=True, model_uncertain=True)
msg_DISTRACTED_BUT_SOMEHOW_UNCERTAIN = make_msg(True, distracted=True, model_uncertain=dm_settings._HI_STD_THRESHOLD*1.5)

# driver interaction with car
car_interaction_DETECTED = True
car_interaction_NOT_DETECTED = False

# some common state vectors
always_no_face = [msg_NO_FACE_DETECTED] * int(TEST_TIMESPAN / DT_DMON)
always_attentive = [msg_ATTENTIVE] * int(TEST_TIMESPAN / DT_DMON)
always_distracted = [msg_DISTRACTED] * int(TEST_TIMESPAN / DT_DMON)
always_true = [True] * int(TEST_TIMESPAN / DT_DMON)
always_false = [False] * int(TEST_TIMESPAN / DT_DMON)

class TestMonitoring(OpenpilotTestCase):
  def _run_seq(self, msgs, interaction, engaged, lowspeed):
    DM = DriverMonitoring()
    alert_lvls = []
    for idx in range(len(msgs)):
      DM._update_states(msgs[idx], [0, 0, 0], 0, engaged[idx], lowspeed[idx])
      # cal_rpy and car_speed don't matter here

      # evaluate events at 10Hz for tests
      DM._update_events(interaction[idx], engaged[idx], lowspeed[idx], 0)
      alert_lvls.append(DM.alert_level)
    assert len(alert_lvls) == len(msgs), f"got {len(alert_lvls)} for {len(msgs)} driverState input msgs"
    return alert_lvls, DM


  # engaged, driver is attentive all the time
  def test_fully_aware_driver(self):
    alert_lvls, d_status = self._run_seq(always_attentive, always_false, always_true, always_false)
    assert all(a == 0 for a in alert_lvls)
    assert d_status.active_policy == log.DriverMonitoringState.MonitoringPolicy.vision

  # engaged, driver is distracted and does nothing
  def test_fully_distracted_driver(self):
    alert_lvls, d_status = self._run_seq(always_distracted, always_false, always_true, always_false)
    s = d_status.settings
    assert alert_lvls[int(s._VISION_POLICY_ALERT_1_TIMEOUT / 2 / DT_DMON)] == 0
    assert alert_lvls[int((s._VISION_POLICY_ALERT_1_TIMEOUT + \
                    (s._VISION_POLICY_ALERT_2_TIMEOUT - s._VISION_POLICY_ALERT_1_TIMEOUT) / 2) / DT_DMON)] == 1
    assert alert_lvls[int((s._VISION_POLICY_ALERT_2_TIMEOUT + \
                    (s._VISION_POLICY_ALERT_3_TIMEOUT - s._VISION_POLICY_ALERT_2_TIMEOUT) / 2) / DT_DMON)] == 2
    assert alert_lvls[int((s._VISION_POLICY_ALERT_3_TIMEOUT + \
                    (TEST_TIMESPAN - 10 - s._VISION_POLICY_ALERT_3_TIMEOUT) / 2) / DT_DMON)] == 3
    assert isinstance(d_status.awareness, float)

  # engaged, distracted past red and beyond the no-response window -> unavailability response + lockout
  # (TSR-633: the item stays engaged, stopped and held, so the lockout timer holds until the driver takes over)
  def test_distracted_lockout(self):
    alert_lvls, d_status = self._run_seq(always_distracted, always_false, always_true, always_false)
    assert alert_lvls[int(DISTRACTED_SECONDS_TO_RED / DT_DMON)] == 3
    assert d_status.lockout_active
    assert d_status.lockout_time_elapsed == 0
    assert d_status.lockout_count >= 1

  # TSR-633: a long hold after no response does not use up the lockout; it runs from the takeover
  def test_lockout_runs_from_the_takeover(self):
    held = int(DISTRACTED_SECONDS_TO_RED / DT_DMON) + int(dm_settings._NO_RESPONSE_TIMEOUT / DT_DMON) + int(90 / DT_DMON)
    engaged = [True] * held + [False] * int(30 / DT_DMON)
    msgs = [msg_DISTRACTED] * len(engaged)
    _, d_status = self._run_seq(msgs, [False] * len(engaged), engaged, [False] * len(engaged))
    assert d_status.lockout_active                               # first lockout is 1 min; 30 s have run
    assert d_status.lockout_time_elapsed == int(30 / DT_DMON)    # only the 30 s since the takeover count
    assert d_status.lockout_time_elapsed < d_status.lockout_duration

  # no face -> wheeltouch red, sustained past the no-response timeout -> unavailability response + lockout
  def test_invisible_lockout(self):
    _, d_status = self._run_seq(always_no_face, always_false, always_true, always_false)
    assert d_status.active_policy == log.DriverMonitoringState.MonitoringPolicy.wheeltouch
    assert d_status.lockout_active
    assert d_status.lockout_count >= 1

  # engaged, no face detected the whole time, no action
  def test_fully_invisible_driver(self):
    alert_lvls, d_status = self._run_seq(always_no_face, always_false, always_true, always_false)
    s = d_status.settings
    assert alert_lvls[int(s._WHEELTOUCH_POLICY_ALERT_1_TIMEOUT / 2 / DT_DMON)] == 0
    assert alert_lvls[int((s._WHEELTOUCH_POLICY_ALERT_1_TIMEOUT + \
                    (s._WHEELTOUCH_POLICY_ALERT_2_TIMEOUT - s._WHEELTOUCH_POLICY_ALERT_1_TIMEOUT) / 2) / DT_DMON)] == 1
    assert alert_lvls[int((s._WHEELTOUCH_POLICY_ALERT_2_TIMEOUT + \
                    (s._WHEELTOUCH_POLICY_ALERT_3_TIMEOUT - s._WHEELTOUCH_POLICY_ALERT_2_TIMEOUT) / 2) / DT_DMON)] == 2
    assert alert_lvls[int((s._WHEELTOUCH_POLICY_ALERT_3_TIMEOUT + \
                    (TEST_TIMESPAN - 10 - s._WHEELTOUCH_POLICY_ALERT_3_TIMEOUT) / 2) / DT_DMON)] == 3
    assert d_status.active_policy == log.DriverMonitoringState.MonitoringPolicy.wheeltouch

  # engaged, down to orange, driver pays attention, back to normal; then down to orange, driver touches wheel
  #  - should have short orange recovery time and no green afterwards; wheel touch only recovers when paying attention
  def test_normal_driver(self):
    ds_vector = [msg_DISTRACTED] * int(DISTRACTED_SECONDS_TO_ORANGE/DT_DMON) + \
                [msg_ATTENTIVE] * int(DISTRACTED_SECONDS_TO_ORANGE/DT_DMON) + \
                [msg_DISTRACTED] * int((DISTRACTED_SECONDS_TO_ORANGE+2)/DT_DMON) + \
                [msg_ATTENTIVE] * (int(TEST_TIMESPAN/DT_DMON)-int((DISTRACTED_SECONDS_TO_ORANGE*3+2)/DT_DMON))
    interaction_vector = [car_interaction_NOT_DETECTED] * int(DISTRACTED_SECONDS_TO_ORANGE*3/DT_DMON) + \
                         [car_interaction_DETECTED] * (int(TEST_TIMESPAN/DT_DMON)-int(DISTRACTED_SECONDS_TO_ORANGE*3/DT_DMON))
    alert_lvls, _ = self._run_seq(ds_vector, interaction_vector, always_true, always_false)
    assert alert_lvls[int(DISTRACTED_SECONDS_TO_ORANGE*0.5/DT_DMON)] == 0
    assert alert_lvls[int((DISTRACTED_SECONDS_TO_ORANGE-0.1)/DT_DMON)] == 2
    assert alert_lvls[int(DISTRACTED_SECONDS_TO_ORANGE*1.5/DT_DMON)] == 0
    assert alert_lvls[int((DISTRACTED_SECONDS_TO_ORANGE*3-0.1)/DT_DMON)] == 2
    assert alert_lvls[int((DISTRACTED_SECONDS_TO_ORANGE*3+0.1)/DT_DMON)] == 2
    assert alert_lvls[int((DISTRACTED_SECONDS_TO_ORANGE*3+2.5)/DT_DMON)] == 0

  # engaged, down to orange, driver dodges camera, then comes back still distracted, down to red, \
  #                          driver dodges, and then touches wheel to no avail, disengages and reengages
  #  - orange/red alert should remain after disappearance, and only disengaging clears red
  def test_biggest_comma_fan(self):
    _invisible_time = 2  # seconds
    ds_vector = always_distracted[:]
    interaction_vector = always_false[:]
    op_vector = always_true[:]
    ds_vector[int(DISTRACTED_SECONDS_TO_ORANGE/DT_DMON):int((DISTRACTED_SECONDS_TO_ORANGE+_invisible_time)/DT_DMON)] \
                                                        = [msg_NO_FACE_DETECTED] * int(_invisible_time/DT_DMON)
    ds_vector[int((DISTRACTED_SECONDS_TO_RED+_invisible_time)/DT_DMON):int((DISTRACTED_SECONDS_TO_RED+2*_invisible_time)/DT_DMON)] \
                                                        = [msg_NO_FACE_DETECTED] * int(_invisible_time/DT_DMON)
    interaction_vector[int((DISTRACTED_SECONDS_TO_RED+2*_invisible_time+0.5)/DT_DMON):int((DISTRACTED_SECONDS_TO_RED+2*_invisible_time+1.5)/DT_DMON)] \
                                                        = [True] * int(1/DT_DMON)
    op_vector[int((DISTRACTED_SECONDS_TO_RED+2*_invisible_time+2.5)/DT_DMON):int((DISTRACTED_SECONDS_TO_RED+2*_invisible_time+3)/DT_DMON)] \
                                                        = [False] * int(0.5/DT_DMON)
    alert_lvls, _ = self._run_seq(ds_vector, interaction_vector, op_vector, always_false)
    assert alert_lvls[int((DISTRACTED_SECONDS_TO_ORANGE+0.5*_invisible_time)/DT_DMON)] == 2
    assert alert_lvls[int((DISTRACTED_SECONDS_TO_RED+1.5*_invisible_time)/DT_DMON)] == 3
    assert alert_lvls[int((DISTRACTED_SECONDS_TO_RED+2*_invisible_time+1.5)/DT_DMON)] == 3
    assert alert_lvls[int((DISTRACTED_SECONDS_TO_RED+2*_invisible_time+3.5)/DT_DMON)] == 0

  # engaged, invisible driver, down to orange, driver touches wheel; then down to orange again, driver appears
  #  - both actions should clear the alert, but momentary appearance should not
  def test_sometimes_transparent_commuter(self):
    for _visible_time in (0.5, 10):
      ds_vector = always_no_face[:]*2
      interaction_vector = always_false[:]*2
      ds_vector[int((2*INVISIBLE_SECONDS_TO_ORANGE+1)/DT_DMON):int((2*INVISIBLE_SECONDS_TO_ORANGE+1+_visible_time)/DT_DMON)] = \
                                                                                               [msg_ATTENTIVE] * int(_visible_time/DT_DMON)
      interaction_vector[int((INVISIBLE_SECONDS_TO_ORANGE)/DT_DMON):int((INVISIBLE_SECONDS_TO_ORANGE+1)/DT_DMON)] = [True] * int(1/DT_DMON)
      alert_lvls, _ = self._run_seq(ds_vector, interaction_vector, 2*always_true, 2*always_false)
      assert alert_lvls[int(dm_settings._WHEELTOUCH_POLICY_ALERT_1_TIMEOUT/2/DT_DMON)] == 0
      assert alert_lvls[int((INVISIBLE_SECONDS_TO_ORANGE-0.1)/DT_DMON)] == 2
      assert alert_lvls[int((INVISIBLE_SECONDS_TO_ORANGE+0.1)/DT_DMON)] == 0
      if _visible_time == 0.5:
        assert alert_lvls[int((INVISIBLE_SECONDS_TO_ORANGE*2+1-0.1)/DT_DMON)] == 2
        assert alert_lvls[int((INVISIBLE_SECONDS_TO_ORANGE*2+1+0.1+_visible_time)/DT_DMON)] == 2
      elif _visible_time == 10:
        assert alert_lvls[int((INVISIBLE_SECONDS_TO_ORANGE*2+1-0.1)/DT_DMON)] == 2
        assert alert_lvls[int((INVISIBLE_SECONDS_TO_ORANGE*2+1+0.1+_visible_time)/DT_DMON)] == 0

  # engaged, invisible driver, down to red, driver appears and then touches wheel, then disengages/reengages
  #  - only disengage will clear the alert
  def test_last_second_responder(self):
    _visible_time = 2  # seconds
    ds_vector = always_no_face[:]
    interaction_vector = always_false[:]
    op_vector = always_true[:]
    ds_vector[int(INVISIBLE_SECONDS_TO_RED/DT_DMON):int((INVISIBLE_SECONDS_TO_RED+_visible_time)/DT_DMON)] = [msg_ATTENTIVE] * int(_visible_time/DT_DMON)
    interaction_vector[int((INVISIBLE_SECONDS_TO_RED+_visible_time)/DT_DMON):int((INVISIBLE_SECONDS_TO_RED+_visible_time+1)/DT_DMON)] = [True] * int(1/DT_DMON)
    op_vector[int((INVISIBLE_SECONDS_TO_RED+_visible_time+1)/DT_DMON):int((INVISIBLE_SECONDS_TO_RED+_visible_time+0.5)/DT_DMON)] = [False] * int(0.5/DT_DMON)
    alert_lvls, _ = self._run_seq(ds_vector, interaction_vector, op_vector, always_false)
    assert alert_lvls[int(dm_settings._WHEELTOUCH_POLICY_ALERT_1_TIMEOUT/2/DT_DMON)] == 0
    assert alert_lvls[int((INVISIBLE_SECONDS_TO_ORANGE-0.1)/DT_DMON)] == 2
    assert alert_lvls[int((INVISIBLE_SECONDS_TO_RED-0.1)/DT_DMON)] == 3
    assert alert_lvls[int((INVISIBLE_SECONDS_TO_RED+0.5*_visible_time)/DT_DMON)] == 3
    assert alert_lvls[int((INVISIBLE_SECONDS_TO_RED+_visible_time+0.5)/DT_DMON)] == 3
    assert alert_lvls[int((INVISIBLE_SECONDS_TO_RED+_visible_time+1+0.1)/DT_DMON)] == 0

  # disengaged, always distracted driver
  #  - dm should stay quiet when not engaged
  def test_pure_dashcam_user(self):
    alert_lvls, _ = self._run_seq(always_distracted, always_false, always_false, always_false)
    assert all(a == 0 for a in alert_lvls)

  # engaged, car stops at traffic light, down to orange, no action, then car starts moving
  #  - should only reach green when stopped, but continues counting down on launch
  def test_long_traffic_light_victim(self):
    _redlight_time = 60  # seconds
    lowspeed_vector = always_true[:]
    lowspeed_vector[int(_redlight_time/DT_DMON):] = [False] * int((TEST_TIMESPAN-_redlight_time)/DT_DMON)
    alert_lvls, d_status = self._run_seq(always_distracted, always_false, always_true, lowspeed_vector)
    s = d_status.settings
    assert alert_lvls[int((_redlight_time-0.1)/DT_DMON)] == 0
    _alert_1_to_2 = s._VISION_POLICY_ALERT_2_TIMEOUT - s._VISION_POLICY_ALERT_1_TIMEOUT
    assert alert_lvls[int((_redlight_time+0.5)/DT_DMON)] == 1
    assert alert_lvls[int((_redlight_time+_alert_1_to_2+0.5)/DT_DMON)] == 2

  # engaged, distracted while moving, then car stops after reaching orange
  #  - should reset timer to pre green at low speed
  def test_distracted_then_stops(self):
    _stop_time = DISTRACTED_SECONDS_TO_ORANGE + 1  # stop 1 second after reaching orange
    lowspeed_vector = always_false[:]
    lowspeed_vector[int(_stop_time/DT_DMON):] = [True] * int((TEST_TIMESPAN-_stop_time)/DT_DMON)
    alert_lvls, _ = self._run_seq(always_distracted, always_false, always_true, lowspeed_vector)
    # just before and briefly after stopping: orange alert; goes away quickly after stopped
    assert alert_lvls[int((_stop_time+0.1)/DT_DMON)] == 2
    assert alert_lvls[int((_stop_time+0.5)/DT_DMON)] == 0

  # engaged, model is somehow uncertain and driver is distracted
  #  - should fall back to wheel touch after uncertain alert
  def test_somehow_indecisive_model(self):
    ds_vector = [msg_DISTRACTED_BUT_SOMEHOW_UNCERTAIN] * int(TEST_TIMESPAN/DT_DMON)
    interaction_vector = always_false[:]
    alert_lvls, d_status = self._run_seq(ds_vector, interaction_vector, always_true, always_false)
    s = d_status.settings
    # LionDriver SWSR-635b: an uncertain pose counts as not attentive from the first output, so the vision timers run
    # at once and through the 10 s fallback (before: no countdown for 10 s, then the wheel-touch timers)
    assert alert_lvls[int((s._VISION_POLICY_ALERT_1_TIMEOUT - 0.1) / DT_DMON)] == 0
    assert alert_lvls[int((s._VISION_POLICY_ALERT_1_TIMEOUT + 0.1) / DT_DMON)] == 1
    assert alert_lvls[int((s._VISION_POLICY_ALERT_2_TIMEOUT + 0.1) / DT_DMON)] == 2
    assert alert_lvls[int((s._VISION_POLICY_ALERT_3_TIMEOUT + 0.1) / DT_DMON)] == 3

  # LionDriver TSR-634 (WP-C-08 §5.4): wheel-touch alert k at T_k seconds or D_k m since the last interaction,
  # whichever comes first
  def _run_speed_seq(self, msgs, interaction, speed):
    # speed: m/s, constant or a function of time
    DM = DriverMonitoring()
    alert_lvls = []
    for idx in range(len(msgs)):
      v = speed(idx * DT_DMON) if callable(speed) else speed
      DM._update_states(msgs[idx], [0, 0, 0], v, True, False)
      DM._update_events(interaction[idx], True, False, 0, car_speed=v)
      alert_lvls.append(DM.alert_level)
    return alert_lvls, DM

  @staticmethod
  def _first_time(alert_lvls, level, start=0.):
    return next((i + 1) * DT_DMON for i, a in enumerate(alert_lvls) if a >= level and (i + 1) * DT_DMON > start)

  WHEELTOUCH_TIMES = (dm_settings._WHEELTOUCH_POLICY_ALERT_1_TIMEOUT, dm_settings._WHEELTOUCH_POLICY_ALERT_2_TIMEOUT,
                      dm_settings._WHEELTOUCH_POLICY_ALERT_3_TIMEOUT)
  WHEELTOUCH_DISTANCES = (dm_settings._WHEELTOUCH_POLICY_ALERT_1_DISTANCE, dm_settings._WHEELTOUCH_POLICY_ALERT_2_DISTANCE,
                          dm_settings._WHEELTOUCH_POLICY_ALERT_3_DISTANCE)

  def test_wheeltouch_alert_times_by_speed(self):
    times, distances = self.WHEELTOUCH_TIMES, self.WHEELTOUCH_DISTANCES
    # WP-C-08 §5.4 speed table: 110 km/h gives 4.9 / 7.9 / 12.9 s, 80 km/h 5.0 / 10.8 / 17.8 s, 50 km/h unchanged;
    # WP-V-02 §4.4 check (a): constant speeds 30…120 km/h in 10 km/h steps
    for kph in (0, 50, 57, *range(30, 130, 10)):
      speed = kph / 3.6
      alert_lvls, d_status = self._run_speed_seq(always_no_face, always_false, speed)
      assert d_status.active_policy == log.DriverMonitoringState.MonitoringPolicy.wheeltouch
      for level, (t, d) in enumerate(zip(times, distances, strict=True), start=1):
        expected = min(t, d / speed) if speed > 0 else t
        assert abs(self._first_time(alert_lvls, level) - expected) <= DT_DMON + 1e-6, (kph, level)
        # the distance driven up to the alert never exceeds D_k (one step of margin)
        assert self._first_time(alert_lvls, level) * speed <= d + speed * DT_DMON + 1e-6, (kph, level)

  def test_wheeltouch_alert_times_on_speed_ramps(self):
    # WP-V-02 §4.4 check (a): ±1.5 m/s² ramps across 57 km/h, where distance starts to govern
    for v0, v1 in ((40, 100), (100, 40)):
      v0, v1 = v0 / 3.6, v1 / 3.6
      accel = 1.5 if v1 > v0 else -1.5
      def speed(t, v0=v0, v1=v1, accel=accel):
        return min(max(v0 + accel * t, min(v0, v1)), max(v0, v1))
      alert_lvls, _ = self._run_speed_seq(always_no_face, always_false, speed)
      for level, (t, d) in enumerate(zip(self.WHEELTOUCH_TIMES, self.WHEELTOUCH_DISTANCES, strict=True), start=1):
        # expected: first time the integrated distance reaches D_k, or T_k, whichever comes first
        dt, travelled, expected = 1e-3, 0., t
        for i in range(int(t / dt)):
          travelled += speed(i * dt) * dt
          if travelled >= d:
            expected = (i + 1) * dt
            break
        assert abs(self._first_time(alert_lvls, level) - expected) <= DT_DMON + 2e-3, (v0, v1, level)

  def test_wheeltouch_distance_reset_on_interaction(self):
    speed = 110 / 3.6
    touch = 4.  # s, before alert 1 at 4.9 s
    interaction_vector = always_false[:]
    interaction_vector[int(touch / DT_DMON) - 1] = True
    alert_lvls, _ = self._run_speed_seq(always_no_face, interaction_vector, speed)
    expected = touch + dm_settings._WHEELTOUCH_POLICY_ALERT_1_DISTANCE / speed
    assert all(a == 0 for a in alert_lvls[:int(touch / DT_DMON)])
    assert abs(self._first_time(alert_lvls, 1) - expected) <= DT_DMON + 1e-6

  def test_wheeltouch_distance_recovers_with_vision(self):
    # face lost past alert 1 at 110 km/h, then seen attentive long enough to restore wheel-touch awareness:
    # the distance bound restarts too, so losing the face again does not alert at once
    speed = 110 / 3.6
    lost, seen = 6., 60.
    ds_vector = [msg_NO_FACE_DETECTED] * int(lost / DT_DMON) + [msg_ATTENTIVE] * int(seen / DT_DMON) + \
                [msg_NO_FACE_DETECTED] * int(20 / DT_DMON)
    alert_lvls, _ = self._run_speed_seq(ds_vector, [False] * len(ds_vector), speed)
    assert alert_lvls[int(lost / DT_DMON) - 1] == 1
    assert all(a == 0 for a in alert_lvls[int((lost + seen - 1) / DT_DMON):int((lost + seen + 4.5) / DT_DMON)])
    expected = lost + seen + dm_settings._WHEELTOUCH_POLICY_ALERT_1_DISTANCE / speed
    assert abs(self._first_time(alert_lvls, 1, start=lost + seen) - expected) <= DT_DMON + 1e-6

  def test_wheeltouch_distance_not_counted_when_disengaged(self):
    speed = 110 / 3.6
    DM = DriverMonitoring()
    for _ in range(int(20 / DT_DMON)):
      DM._update_states(msg_NO_FACE_DETECTED, [0, 0, 0], speed, False, False)
      DM._update_events(False, False, False, 0, car_speed=speed)
    assert DM.wheeltouch_distance == 0.

  def test_wheeltouch_distance_no_alert_at_low_speed(self):
    # slowing below the alert speed just before the alert 1 distance (147 m at 4.8 s): no alert there, as for the timers
    DM = DriverMonitoring()
    alert_lvls = []
    for idx in range(int(60 / DT_DMON)):
      t = idx * DT_DMON
      speed, lowspeed = (110 / 3.6, False) if t < 4.8 else (2.5, True)
      DM._update_states(msg_NO_FACE_DETECTED, [0, 0, 0], speed, True, lowspeed)
      DM._update_events(False, True, lowspeed, 0, car_speed=speed)
      alert_lvls.append(DM.alert_level)
    assert all(a == 0 for a in alert_lvls)


# LionDriver TSR-635 / SWSR-635a, 635b: the first alert comes at the policy times in real time, whatever the DM frame
# rate or the model's certainty
def sm_for(ds, frame_id, speed=25.):
  """Just the messages DriverMonitoring.run_step reads, with the cabin frame index set"""
  ds.frameId = frame_id
  drive = car.CarState.GearShifter.drive
  return {"driverStateV2": ds,
          "carState": SimpleNamespace(vEgo=speed, gearShifter=drive, steeringPressed=False, gasPressed=False,
                                      steeringAngleDeg=0.),
          "selfdriveState": SimpleNamespace(enabled=True),
          "modelV2": SimpleNamespace(meta=SimpleNamespace(disengagePredictions=SimpleNamespace(brakeDisengageProbs=[0.]))),
          "extrinsicsCalibration": SimpleNamespace(rpyCalib=[0., 0., 0.])}


class TestFirstAlertTime(OpenpilotTestCase):
  def _first_alert(self, msg, frames_per_step, seconds=30.):
    DM = DriverMonitoring()
    frame_id = 0
    for _ in range(int(seconds / (frames_per_step * DT_DMON))):
      frame_id += frames_per_step
      DM.run_step(sm_for(msg, frame_id))
      if DM.alert_level >= 1:
        return frame_id * DT_DMON
    return None

  def test_alert_1_in_real_time_at_any_dm_rate(self):
    # SWSR-635a: with the DM model at 20, 10 and 5 Hz (frames skipped), alert 1 comes at the same elapsed time, within
    # two frame periods: the filter crossing and the countdown each land on a frame (before: 5.3 / 10.6 / 21.2 s)
    at_20hz = self._first_alert(msg_DISTRACTED, 1)
    assert at_20hz is not None and at_20hz <= dm_settings._VISION_POLICY_ALERT_1_TIMEOUT + 0.5
    for frames_per_step in (2, 4):
      t = self._first_alert(msg_DISTRACTED, frames_per_step)
      assert t is not None and abs(t - at_20hz) <= 2 * frames_per_step * DT_DMON + 1e-6, (frames_per_step, t, at_20hz)

  def test_frame_gap_capped(self):
    DM = DriverMonitoring()
    assert DM._frame_dt(100) == DT_DMON  # first frame
    assert DM._frame_dt(101) == DT_DMON
    assert DM._frame_dt(103) == 2 * DT_DMON
    assert DM._frame_dt(10_000) == dm_settings._MAX_FRAME_GAP_TIME
    assert DM._frame_dt(5) == DT_DMON  # frame index restarted

  def test_uncertain_pose_alert_1_without_fallback_delay(self):
    # SWSR-635b: distracted with an uncertain pose, alert 1 at the vision time (before: 15.0 s, after the fallback)
    t = self._first_alert(msg_DISTRACTED_BUT_SOMEHOW_UNCERTAIN, 1)
    assert t is not None and t <= dm_settings._VISION_POLICY_ALERT_1_TIMEOUT + 0.5, t

  def test_attentive_certain_driver_still_recovers(self):
    DM = DriverMonitoring()
    for i in range(int(4 / DT_DMON)):
      DM.run_step(sm_for(msg_DISTRACTED_BUT_SOMEHOW_UNCERTAIN, i + 1))
    awareness_low = DM.awareness
    for i in range(int(4 / DT_DMON), int(30 / DT_DMON)):
      DM.run_step(sm_for(msg_ATTENTIVE, i + 1))
    assert awareness_low < 1. and DM.awareness == 1. and DM.alert_level == 0

  def test_escalation_does_not_stop_at_orange(self):
    # SWSR-635b: past orange the vision countdown keeps running when the face is lost or the pose turns uncertain,
    # so the terminal alert comes at the vision time (before: orange for good, no terminal alert)
    for after in (msg_NO_FACE_DETECTED, msg_DISTRACTED_BUT_SOMEHOW_UNCERTAIN):
      seq = [msg_DISTRACTED] * int(9 / DT_DMON) + [after] * int(20 / DT_DMON)
      DM = DriverMonitoring()
      red = None
      for i, m in enumerate(seq):
        DM._update_states(m, [0, 0, 0], 25., True, False)
        DM._update_events(False, True, False, 0, 25.)
        if DM.alert_level == 3:
          red = (i + 1) * DT_DMON
          break
      assert red is not None and red <= dm_settings._VISION_POLICY_ALERT_3_TIMEOUT + 0.5, (after, red)

