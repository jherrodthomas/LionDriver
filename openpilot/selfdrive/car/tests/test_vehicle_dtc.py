import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from opendbc.car.can_definitions import CanData
from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.common.parameterized import parameterized
from openpilot.selfdrive.car import vehicle_dtc
from openpilot.selfdrive.car.vehicle_dtc import ACTIVE, FAILED, OK, DtcStatus

# TSR-629, SWSR-629...629d verification with mocked UDS responses (register DQ-056 A, DQ-132 A). Not verified on the
# reference vehicle (WP-S-09 VS-SQ-20)

REFERENCE = TOYOTA.TOYOTA_COROLLA_TSS2
EPS, ABS = 0x7a1, 0x7b0
AVAILABLE = 0xFF  # status availability mask: every bit supported
NOT_ACTIVE_BITS = (0x04, 0x10, 0x20, 0x40)  # pending; not completed since clear; failed since clear; not completed this cycle


def dtc(code: int, status: int) -> bytes:
  return code.to_bytes(3, "big") + bytes([status])


class FakeEcus:
  """ISO-TP answers of the EPS and ABS/VSC ECUs on bus 0. replies[addr]: the 0x19 response payload, 'silent' or 'nrc'"""

  def __init__(self, replies: dict[int, bytes | str]):
    self.replies = replies
    self.sent: list[CanData] = []
    self.queue: list[CanData] = []
    self.pending_cf: dict[int, list[bytes]] = {}

  def can_send(self, msgs):
    for msg in msgs:
      self.sent.append(msg)
      self._handle(msg.address, msg.dat)

  def can_recv(self, wait_for_one=False):
    out, self.queue = self.queue, []
    return [out] if out else []

  def _reply(self, addr, payload: bytes):
    rx = addr + 8
    if len(payload) < 8:
      self.queue.append(CanData(rx, (bytes([len(payload)]) + payload).ljust(8, b"\x00"), 0))
      return
    self.queue.append(CanData(rx, bytes([0x10 | (len(payload) >> 8), len(payload) & 0xFF]) + payload[:6], 0))
    rest = payload[6:]
    self.pending_cf[addr] = [(bytes([0x20 | ((i // 7 + 1) & 0xF)]) + rest[i:i + 7]).ljust(8, b"\x00")
                             for i in range(0, len(rest), 7)]

  def _handle(self, addr, dat: bytes):
    reply = self.replies.get(addr, "silent")
    if reply == "silent":
      return
    if dat[0] == 0x30:  # flow control from the tester
      for cf in self.pending_cf.pop(addr, []):
        self.queue.append(CanData(addr + 8, cf, 0))
      return
    request = dat[1:1 + (dat[0] & 0x0F)]
    if request == b"\x3e\x00":
      self._reply(addr, b"\x7e\x00")
    elif request == vehicle_dtc.DTC_REQUEST:
      self._reply(addr, b"\x59\x02" + reply if isinstance(reply, bytes) else b"\x7f\x19\x11")


def stationary_sample():
  return SimpleNamespace(canValid=True, standstill=True)


def read(replies, sample=stationary_sample, fingerprint=REFERENCE):
  ecus = FakeEcus(replies)
  status = vehicle_dtc.read_startup_dtcs(ecus.can_send, ecus.can_recv, fingerprint, sample)
  return status, ecus


def results(status: DtcStatus) -> dict[str, str]:
  return {e.ecu: e.result for e in status.ecus}


class TestDtcRead(unittest.TestCase):
  def test_reference_addresses_from_fw_query(self):
    self.assertEqual(vehicle_dtc.target_addrs(REFERENCE), {"eps": (EPS, None), "abs": (ABS, None)})

  def test_request_bytes(self):
    self.assertEqual(vehicle_dtc.REQUESTS, [b"\x3e\x00", b"\x19\x02\xff"])
    self.assertEqual(vehicle_dtc.RESPONSES, [b"\x7e\x00", b"\x59\x02"])

  def test_no_dtc_allows(self):
    status, ecus = read({EPS: bytes([AVAILABLE]), ABS: bytes([AVAILABLE])})
    self.assertTrue(status.read)
    self.assertEqual(results(status), {"eps": OK, "abs": OK})
    self.assertTrue(status.complete())
    self.assertEqual(status.active_ecus(), [])
    # only the two target ECUs on bus 0 were addressed
    self.assertEqual({m.address for m in ecus.sent}, {EPS, ABS})
    self.assertEqual({m.src for m in ecus.sent}, {0})

  @parameterized.expand([(0x01,), (0x02,), (0x08,), (0x80,), (0x09,), (0x2F,)])
  def test_active_status_bit_blocks(self, status_byte):
    status, _ = read({EPS: bytes([AVAILABLE]) + dtc(0x5A1234, status_byte), ABS: bytes([AVAILABLE])})
    self.assertEqual(results(status), {"eps": ACTIVE, "abs": OK})
    self.assertEqual(status.active_ecus(), ["eps"])
    self.assertEqual(status.ecus[0].active, ("C1a1234",))

  @parameterized.expand([(b,) for b in NOT_ACTIVE_BITS])
  def test_history_and_pending_bits_alone_do_not_block(self, status_byte):
    status, _ = read({EPS: bytes([AVAILABLE]), ABS: bytes([AVAILABLE]) + dtc(0x401111, status_byte)})
    self.assertEqual(results(status), {"eps": OK, "abs": OK})
    # still logged
    self.assertEqual(len(status.ecus[1].stored), 1)

  def test_long_code_list_multi_frame(self):
    codes = b"".join(dtc(0x400000 + i, 0x10) for i in range(5)) + dtc(0x401234, 0x08)
    status, _ = read({EPS: bytes([AVAILABLE]), ABS: bytes([AVAILABLE]) + codes})
    self.assertEqual(results(status)["abs"], ACTIVE)
    self.assertEqual(len(status.ecus[1].stored), 6)

  def test_unsupported_status_bit_ignored(self):
    # bit 3 set in the status, but the ECU says it does not support bit 3
    status, _ = read({EPS: bytes([0x01]) + dtc(0x5A1234, 0x08), ABS: bytes([AVAILABLE])})
    self.assertEqual(results(status)["eps"], OK)

  def test_exempt_code_does_not_block(self):
    with mock.patch.object(vehicle_dtc, "EXEMPT_DTCS", frozenset({("eps", "C1a1234")})):
      status, _ = read({EPS: bytes([AVAILABLE]) + dtc(0x5A1234, 0x09), ABS: bytes([AVAILABLE])})
    self.assertEqual(results(status)["eps"], OK)

  @parameterized.expand([
    ("timeout", "silent"),
    ("negative response", "nrc"),
    ("malformed", bytes([AVAILABLE, 0x12, 0x34])),
    ("no active bit available", bytes([0x30])),
  ])
  def test_read_failure_is_not_healthy(self, _, reply):
    status, _ = read({EPS: reply, ABS: bytes([AVAILABLE])})
    self.assertEqual(results(status), {"eps": FAILED, "abs": OK})
    self.assertFalse(status.complete())

  def test_timeout_retried_once(self):
    status, ecus = read({EPS: bytes([AVAILABLE])})
    self.assertEqual(results(status), {"eps": OK, "abs": FAILED})
    tester_present_to_abs = [m for m in ecus.sent if m.address == ABS and m.dat[1] == 0x3E]
    self.assertEqual(len(tester_present_to_abs), vehicle_dtc.ATTEMPTS)
    # the answered ECU is not asked again
    self.assertEqual(len([m for m in ecus.sent if m.address == EPS and m.dat[1] == 0x19]), 1)

  def test_platform_without_addresses_fails(self):
    with mock.patch.object(vehicle_dtc, "FW_VERSIONS", {}):
      status, ecus = read({EPS: bytes([AVAILABLE]), ABS: bytes([AVAILABLE])})
    self.assertEqual(results(status), {"eps": FAILED, "abs": FAILED})
    self.assertEqual(ecus.sent, [])


class TestOnlyWhileStationary(unittest.TestCase):
  """SWSR-629a: nothing is sent unless the car has been seen stationary"""

  def test_moving_car_is_not_queried(self):
    status, ecus = read({EPS: bytes([AVAILABLE]), ABS: bytes([AVAILABLE])},
                        sample=lambda: SimpleNamespace(canValid=True, standstill=False))
    self.assertFalse(status.read)
    self.assertFalse(status.complete())
    self.assertEqual(ecus.sent, [])

  def test_no_valid_can_is_not_queried(self):
    with mock.patch.object(vehicle_dtc, "STATIONARY_MAX_TIME", 0.05):
      status, ecus = read({EPS: bytes([AVAILABLE]), ABS: bytes([AVAILABLE])},
                          sample=lambda: SimpleNamespace(canValid=False, standstill=True))
    self.assertFalse(status.read)
    self.assertEqual(ecus.sent, [])

  def test_starting_to_move_during_check_is_not_queried(self):
    samples = iter([True] * (vehicle_dtc.STATIONARY_SAMPLES - 1) + [False])
    status, ecus = read({EPS: bytes([AVAILABLE]), ABS: bytes([AVAILABLE])},
                        sample=lambda: SimpleNamespace(canValid=True, standstill=next(samples)))
    self.assertFalse(status.read)
    self.assertEqual(ecus.sent, [])

  def test_error_counts_as_not_read(self):
    def sample():
      raise ValueError("bad frame")
    status, ecus = read({EPS: bytes([AVAILABLE]), ABS: bytes([AVAILABLE])}, sample=sample)
    self.assertFalse(status.read)
    self.assertFalse(status.complete())
    self.assertEqual(ecus.sent, [])

  def test_needs_consecutive_valid_standstill_samples(self):
    calls = []

    def sample():
      calls.append(1)
      return SimpleNamespace(canValid=True, standstill=True)
    self.assertTrue(vehicle_dtc.vehicle_stationary(sample))
    self.assertEqual(len(calls), vehicle_dtc.STATIONARY_SAMPLES)


class TestStatusRecord(unittest.TestCase):
  def test_round_trip(self):
    status, _ = read({EPS: bytes([AVAILABLE]) + dtc(0x5A1234, 0x09), ABS: bytes([AVAILABLE])})
    self.assertEqual(DtcStatus.from_dict(status.to_dict()), status)

  @parameterized.expand([(None,), ({},), ({"read": True},), ("garbage",)])
  def test_missing_or_malformed_record_is_not_read(self, record):
    status = DtcStatus.from_dict(record)
    self.assertFalse(status.read)
    self.assertFalse(status.complete())


CARD = Path(vehicle_dtc.__file__).with_name("card.py")


class TestCardCallSite(unittest.TestCase):
  """SWSR-629a: card reads the codes once, in __init__, before FirmwareQueryDone lets pandad set the car safety mode"""

  def test_called_only_in_init_before_firmware_query_done(self):
    tree = ast.parse(CARD.read_text())
    calls = {}
    for fn in ast.walk(tree):
      if isinstance(fn, ast.FunctionDef):
        for node in ast.walk(fn):
          if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            calls.setdefault(node.func.attr, []).append((fn.name, node.lineno, node))
    reads = calls["read_startup_dtcs"]
    self.assertEqual([(name, ) for name, _, _ in reads], [("__init__",)])
    done = [line for name, line, node in calls["put_bool"]
            if name == "__init__" and isinstance(node.args[0], ast.Constant) and node.args[0].value == "FirmwareQueryDone"]
    self.assertEqual(len(done), 1)
    self.assertLess(reads[0][1], done[0])


if __name__ == "__main__":
  unittest.main()
