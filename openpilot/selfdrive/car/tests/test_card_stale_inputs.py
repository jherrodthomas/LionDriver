import importlib
import sys
import unittest
from unittest import mock

from opendbc.can.packer import CANPacker
from opendbc.car.can_definitions import CanData
from opendbc.car.car_helpers import interfaces
from opendbc.car.structs import car
from opendbc.car.toyota.values import CAR as TOYOTA

# Stale-input injection for card (SW FMEA SWF-056.C2, SWF-056.C3, SWF-047; SWF-ACT-044). The vehicle CAN input runs through the real
# Toyota CarInterface.update with the reference car's parsers, fed every message they read as packed frames at 100 Hz:
#   a supervised message that stops, or arrives with a bad checksum, makes carState.canValid false within 10 periods plus 5 evaluations
#   (selfdrived then disables on canError); in the first second, before its rate is learned, a stopped message takes up to 10 s
#   (SWF-056.C2, the open design action SWF-ACT-056: the bound is asserted so a fix that shortens it still passes)
#   card sends no CAN while carControl is not alive

REFERENCE = TOYOTA.TOYOTA_COROLLA_TSS2
STEP_NS = 10_000_000  # 100 Hz
LEARNED_BOUND_S = 10 * 0.01 + 5 * 0.01  # 10 periods to time out, then CAN_INVALID_CNT evaluations
FIRST_SECOND_BOUND_S = 10.0 + 5 * 0.01  # assumed 1 Hz: 10 s to time out


class CanFeed:
  """The reference car interface, fed packed frames for every message its parsers read"""
  def __init__(self):
    self.CI = interfaces[REFERENCE](interfaces[REFERENCE].get_non_essential_params(REFERENCE))
    self.packers = {cp.bus: CANPacker(cp.dbc_name) for cp in self.CI.can_parsers.values()}
    self.t = 0

  def messages(self, supervised=True):
    return {s.name: a for cp in self.CI.can_parsers.values() for a, s in cp.message_states.items() if s.ignore_alive != supervised}

  def has_checksum(self, name):
    return any(sig.calc_checksum is not None for cp in self.CI.can_parsers.values() for s in cp.message_states.values()
               if s.name == name for sig in s.signals)

  def step(self, drop=None, corrupt=None):
    frames = []
    for cp in self.CI.can_parsers.values():
      for addr, st in cp.message_states.items():
        if st.name == drop:
          continue
        dat = self.packers[cp.bus].make_can_msg(st.name, cp.bus, {})[1]
        if st.name == corrupt:
          dat = bytes([dat[0] ^ 0xFF]) + dat[1:]
        frames.append(CanData(addr, dat, cp.bus))
    CS = self.CI.update([(self.t, frames)])
    self.t += STEP_NS
    return CS

  def warm(self, steps):
    CS = None
    for _ in range(steps):
      CS = self.step()
    return CS

  def seconds_to_invalid(self, limit_s=15., **fault):
    for n in range(1, int(limit_s / 0.01)):
      if not self.step(**fault).canValid:
        return n * 0.01
    return None


class TestStaleVehicleInput(unittest.TestCase):
  def setUp(self):
    self.feed = CanFeed()
    self.feed.warm(2)
    self.names = sorted(self.feed.messages())
    self.assertGreater(len(self.names), 10)

  def test_unsupervised_messages(self):
    # registered without a timeout on purpose (blinker lamps); any other message joining this list is noticed here
    self.assertEqual(sorted(self.feed.messages(supervised=False)), ['BLINKERS_STATE'])

  def test_valid_while_every_message_arrives(self):
    feed = CanFeed()
    self.assertTrue(feed.warm(300).canValid)
    self.assertTrue(all(feed.step().canValid for _ in range(100)))

  def test_stopped_message_invalid_within_learned_bound(self):
    for name in self.names:
      with self.subTest(name):
        feed = CanFeed()
        self.assertTrue(feed.warm(300).canValid)
        t = feed.seconds_to_invalid(drop=name)
        self.assertIsNotNone(t)
        self.assertLessEqual(t, LEARNED_BOUND_S + 1e-9)

  def test_stopped_message_in_the_first_second(self):
    # SWF-056.C2: the rate is not learned yet, so the parser assumes 1 Hz
    for name in ('BRAKE_MODULE', 'STEER_TORQUE_SENSOR', 'PCM_CRUISE'):
      with self.subTest(name):
        feed = CanFeed()
        feed.warm(50)
        t = feed.seconds_to_invalid(drop=name)
        self.assertIsNotNone(t)
        self.assertLessEqual(t, FIRST_SECOND_BOUND_S + 1e-9)

  def test_bad_checksum_invalid_within_learned_bound(self):
    checked = [n for n in self.names if self.feed.has_checksum(n)]
    assert 'STEER_TORQUE_SENSOR' in checked, checked
    for name in checked:
      with self.subTest(name):
        feed = CanFeed()
        self.assertTrue(feed.warm(300).canValid)
        t = feed.seconds_to_invalid(corrupt=name)
        self.assertIsNotNone(t)
        self.assertLessEqual(t, LEARNED_BOUND_S + 1e-9)


CARD = 'openpilot.selfdrive.car.card'


class TestCardActuatesOnlyAliveCarControl(unittest.TestCase):
  # SWF-047: card sends the latest carControl only while carControl is alive (SubMaster all_alive: 10 periods).
  # card reads REPLAY from the environment when imported, and process replay forks it from this process, so the module is
  # dropped again after these tests: a replay later in the same worker then imports it with REPLAY set
  @classmethod
  def setUpClass(cls):
    cls.loaded_before = CARD in sys.modules
    cls.card = importlib.import_module(CARD)

  @classmethod
  def tearDownClass(cls):
    if not cls.loaded_before:
      sys.modules.pop(CARD, None)

  def make(self, alive):
    c = self.card.Car.__new__(self.card.Car)
    c.CI = interfaces[REFERENCE](interfaces[REFERENCE].get_non_essential_params(REFERENCE))
    c.CP = c.CI.CP
    c.initialized_prev = True
    c.pm = mock.Mock()
    c.sm = mock.Mock()
    c.sm.all_alive.return_value = alive
    c.CC_prev = car.CarControl.new_message()
    return c

  def step(self, c):
    CC = car.CarControl.new_message()
    CS = car.CarState.new_message(canValid=True)
    with mock.patch.object(self.card, 'REPLAY', False):
      c.controls_update(CS.as_reader(), CC.as_reader())

  def test_sends_while_alive(self):
    c = self.make(alive=True)
    self.step(c)
    self.assertEqual([call.args[0] for call in c.pm.send.call_args_list], ['sendcan'])

  def test_no_can_when_car_control_not_alive(self):
    c = self.make(alive=False)
    for _ in range(10):
      self.step(c)
    c.pm.send.assert_not_called()


if __name__ == "__main__":
  unittest.main()
