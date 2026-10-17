import unittest

from opendbc.car import DT_CTRL, structs
from opendbc.car.car_helpers import interfaces
from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.cereal import log
from openpilot.selfdrive.car.car_events import CarEvents, STEER_FAULT_SILENT_FRAMES

# LionDriver TSR-607 (b) verification (DQ-342 A, System FMEA SFM-ACT-023)

EventName = log.OnroadEvent.EventName
SILENT = EventName.steerTempUnavailableSilent
FULL = EventName.steerTempUnavailable


def get_params():
  fingerprints = dict.fromkeys(range(7), {})
  return interfaces[TOYOTA.TOYOTA_COROLLA_TSS2].get_params(TOYOTA.TOYOTA_COROLLA_TSS2, fingerprints, [], alpha_long=False,
                                                           is_release=False, docs=False)


def car_state(fault=False, pressed=False, standstill=False):
  CS = structs.CarState.new_message()
  CS.gearShifter = structs.CarState.GearShifter.drive
  CS.cruiseState.available = True
  CS.vEgo = 0. if standstill else 20.
  CS.standstill = standstill
  CS.steerFaultTemporary = fault
  CS.steeringPressed = pressed
  return CS.as_reader()


class TestSteerFaultWarning(unittest.TestCase):
  def setUp(self):
    self.car_events = CarEvents(get_params())
    self.CC = structs.CarControl.new_message().as_reader()
    self.CS_prev = car_state()
    # past the start-up latch: a fault right after start-up gets the lighter prompt
    self.step(car_state(), int(2 / DT_CTRL))

  def step(self, CS, frames):
    names = []
    for _ in range(frames):
      events = self.car_events.update(CS, self.CS_prev, self.CC)
      names.append(SILENT if SILENT in events.names else FULL if FULL in events.names else None)
      self.CS_prev = CS
    return names

  def test_silent_window(self):
    self.assertEqual(STEER_FAULT_SILENT_FRAMES, round(1.5 / DT_CTRL))

  def test_no_recent_override(self):
    # (a): a fault without a recent override is the take-over request from its first frame
    self.assertEqual(set(self.step(car_state(fault=True), int(3 / DT_CTRL))), {FULL})

  def test_after_override_escalates(self):
    # (b): the lighter prompt after an override, then the take-over request 1.5 s after fault onset
    self.step(car_state(pressed=True), 10)
    self.step(car_state(), int(0.5 / DT_CTRL))
    names = self.step(car_state(fault=True), int(5 / DT_CTRL))
    self.assertEqual(names[:STEER_FAULT_SILENT_FRAMES], [SILENT] * STEER_FAULT_SILENT_FRAMES)
    self.assertEqual(set(names[STEER_FAULT_SILENT_FRAMES:]), {FULL})

  def test_standstill_escalates(self):
    # (b): at standstill the lighter prompt is not held for the whole fault either
    self.step(car_state(standstill=True), 10)
    names = self.step(car_state(fault=True, standstill=True), int(5 / DT_CTRL))
    self.assertEqual(names[:STEER_FAULT_SILENT_FRAMES], [SILENT] * STEER_FAULT_SILENT_FRAMES)
    self.assertEqual(set(names[STEER_FAULT_SILENT_FRAMES:]), {FULL})

  def test_released_after_holding(self):
    # driver keeps steering through the fault onset: no alert while holding (upstream), but after release the
    # fault is older than 1.5 s, so the take-over request follows at once
    self.step(car_state(pressed=True), 10)
    self.assertEqual(set(self.step(car_state(fault=True, pressed=True), int(3 / DT_CTRL))), {None})
    self.assertEqual(set(self.step(car_state(fault=True), int(1 / DT_CTRL))), {FULL})

  def test_new_fault_rearms(self):
    # a fault that clears and returns after a new override gets the lighter prompt again
    self.step(car_state(pressed=True), 10)
    self.step(car_state(fault=True), int(3 / DT_CTRL))
    self.step(car_state(pressed=True), 10)
    self.step(car_state(), 5)
    names = self.step(car_state(fault=True), int(3 / DT_CTRL))
    self.assertEqual(names[0], SILENT)
    self.assertEqual(names[STEER_FAULT_SILENT_FRAMES], FULL)
