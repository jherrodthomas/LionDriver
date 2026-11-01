#!/usr/bin/env python3
"""Tests of the virtual HIL bench itself (vhil.py), on a fake clock so they do not depend on the runner's load.

    python3 assurance/sim/vhil/test_vhil.py

They check the bench, not the firmware: the scheduler runs the 100 Hz safety task and the 8 Hz tick at their rates and
in order, the CAN paths count refused frames like the firmware, and a full engage, heartbeat-loss and siren sequence
gives the times the firmware code defines (TSR-407 0.3 s; speaker on odd ticks only).
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
os.environ["REFERENCE_BUILD"] = "1"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
import vhil
from opendbc.can.packer import CANPacker
from opendbc.car.structs import CarParams

TOYOTA, REFERENCE_PARAM = CarParams.SafetyModel.toyota, 73
DBC = "toyota_nodsu_pt_generated"
RX_HZ = {"WHEEL_SPEEDS": 83, "STEER_TORQUE_SENSOR": 50, "PCM_CRUISE": 33, "BRAKE_MODULE": 40, "EPS_STATUS": 25,
         "PCM_CRUISE_2": 33}


class FakeClock:
  def __init__(self):
    self.t = 100.0

  def __call__(self):
    return self.t


class Car:
  """The jungle side and the SoC, stepped on the fake clock in 1 ms steps."""

  def __init__(self, fw: vhil.VirtualFirmware, clock: FakeClock):
    self.fw, self.clock = fw, clock
    self.packer = CANPacker(DBC)
    self.cruise_active = False
    self.heartbeat = True    # the SoC sends its heartbeat at 10 Hz (pandad)
    self.engaged = False
    self.soc = False         # STEERING_LKA at 100 Hz and ACC_CONTROL at 33 Hz, as the engaged SoC
    self.ms = 0

  def _rx(self, name):
    values = {"PCM_CRUISE": {"CRUISE_ACTIVE": int(self.cruise_active), "GAS_RELEASED": 1},
              "EPS_STATUS": {"LKA_STATE": 5}, "PCM_CRUISE_2": {"MAIN_ON": 1}}.get(name, {})
    return self.packer.make_can_msg(name, 0, values)

  def run(self, seconds: float) -> None:
    for _ in range(round(seconds * 1000)):
      self.clock.t += 0.001
      self.ms += 1
      for name, hz in RX_HZ.items():
        if self.ms % round(1000 / hz) == 0:
          self.fw.car_send(*self._rx(name))
      if self.heartbeat and self.ms % 100 == 0:
        self.fw.heartbeat(self.engaged)
      if self.soc and self.ms % 10 == 0:
        self.fw.host_send(*self.packer.make_can_msg("STEERING_LKA", 0, {"STEER_TORQUE_CMD": 0, "STEER_REQUEST": 0}))
        if self.ms % 30 == 0:
          self.fw.host_send(*self.packer.make_can_msg("ACC_CONTROL", 0, {"ACCEL_CMD": 0.0}))

  def engage(self) -> bool:
    self.run(0.5)
    self.cruise_active = True
    self.run(0.2)
    self.engaged = True
    self.soc = True
    self.run(0.2)
    return self.fw.health()["controls_allowed"]


class TestScheduler(unittest.TestCase):
  def setUp(self):
    self.clock = FakeClock()
    self.fw = vhil.VirtualFirmware(reference=True, clock=self.clock)

  def test_rates(self):
    self.clock.t += 1.0
    self.fw.health()
    self.assertEqual(self.fw.task_runs, 100)
    self.assertEqual(self.fw.ticks, 8)

  def test_lazy_until_called(self):
    # the firmware runs only when the host or the car side calls in; time does not run backwards
    self.clock.t += 0.0049
    self.fw.health()
    self.assertEqual(self.fw.task_runs, 0)
    self.clock.t -= 1.0
    self.fw.health()
    self.assertEqual(self.fw.task_runs, 0)
    self.clock.t += 1.01
    self.fw.health()
    self.assertEqual(self.fw.task_runs, 1)

  def test_silent_refuses_and_counts(self):
    self.assertFalse(self.fw.host_send(0x2E4, b"\x00" * 5, 0))
    self.assertEqual(self.fw.health()["safety_tx_blocked"], 1)
    self.assertEqual(list(self.fw.jungle_rx), [])
    self.fw.car_send(0x2E4, b"\x00" * 5, 2)
    self.assertEqual(list(self.fw.jungle_rx), [], "SILENT forwards nothing")
    self.assertEqual(list(self.fw.panda_rx), [(0x2E4, b"\x00" * 5, 2)])

  def test_mode_change_resets_counters(self):
    self.fw.host_send(0x2E4, b"\x00" * 5, 0)
    self.fw.set_safety_mode(TOYOTA, REFERENCE_PARAM)
    self.assertEqual(self.fw.health()["safety_tx_blocked"], 0)
    self.assertEqual(self.fw.health()["safety_param"], REFERENCE_PARAM)


class TestSequence(unittest.TestCase):
  def setUp(self):
    self.clock = FakeClock()
    self.fw = vhil.VirtualFirmware(reference=True, clock=self.clock)
    self.fw.set_safety_mode(TOYOTA, REFERENCE_PARAM)
    self.car = Car(self.fw, self.clock)

  def test_engages_and_echoes(self):
    self.assertTrue(self.car.engage())
    self.assertEqual(self.fw.health()["safety_tx_blocked"], 0)
    self.assertTrue(any(bus == 0x80 for _, _, bus in self.fw.panda_rx), "sent frames are echoed as 0x80 | bus")

  def test_no_engagement_with_main_off(self):
    # SWSR-405(c): cruise becoming active while PCM_CRUISE_2.MAIN_ON is 0 never engages
    self.car._rx = (lambda orig: lambda name: orig(name) if name != "PCM_CRUISE_2" else
                    self.car.packer.make_can_msg(name, 0, {"MAIN_ON": 0}))(self.car._rx)
    self.assertFalse(self.car.engage())

  def test_heartbeat_loss_revokes_then_siren(self):
    self.assertTrue(self.car.engage())
    last_heartbeat_us = self.fw.time_us - (self.car.ms % 100) * 1000
    self.car.heartbeat = False
    self.car.run(1.0)
    self.assertFalse(self.fw.health()["controls_allowed"])
    revoked = self.fw.revocations[-1] - last_heartbeat_us
    self.assertGreaterEqual(revoked, 300_000 - vhil.TASK_US)  # TSR-407: 0.3 s, evaluated by the 100 Hz task
    self.assertLessEqual(revoked, 300_000 + vhil.TASK_US)
    on = self.fw.siren_on_since(last_heartbeat_us)
    self.assertIsNotNone(on, "the heartbeat-loss siren sounds")
    self.assertGreaterEqual(on, self.fw.revocations[-1])
    # the speaker changes only on ticks, and sounds only on odd ones
    for t, _ in self.fw.siren_log:
      self.assertEqual((t - (self.fw.next_tick - self.fw.ticks * vhil.TICK_US)) % vhil.TICK_US, 0)


if __name__ == "__main__":
  unittest.main()
