"""
LionDriver start-up fault-code read (TSR-629, SWSR-629, SWSR-629a...629d; register DQ-056 A, DQ-132 A).

The ratings assume a healthy car (AOU-09, AOU-10). Before every drive the driver checks the warning lamps (WP-O-02
OPS-01), but a missed lamp, or a stored fault without a lamp, would go unseen by the item. So at start-up card reads
the stored diagnostic trouble codes (DTCs) of the EPS and of the ABS/VSC ECU, and on the reference platform selfdrived
refuses engagement while one of them reports an active code, or when the read gave no complete answer.

The read is UDS ReadDTCInformation (0x19), reportDTCByStatusMask (0x02), sent to the addresses of the existing
firmware query (opendbc FW_VERSIONS). It runs once per start of card, in the window where the firmware query runs:
after fingerprinting and before card sets FirmwareQueryDone, so pandad still holds the panda in the ELM327
diagnostic mode, where no actuation is possible and the item cannot be engaged. It also runs only after the car has
been seen stationary; otherwise nothing is sent and the status is "not read", which refuses engagement as well.

Not verified on the reference vehicle: whether its EPS and ABS/VSC ECUs answer this service is checked by
WP-S-09 VS-SQ-20.
"""
import time
from collections.abc import Callable
from dataclasses import dataclass

from opendbc.car import uds
from opendbc.car.can_definitions import CanRecvCallable, CanSendCallable
from opendbc.car.carlog import carlog
from opendbc.car.fingerprints import FW_VERSIONS
from opendbc.car.fw_query_definitions import ECU_NAME, StdQueries
from opendbc.car.isotp_parallel_query import IsoTpParallelQuery
from opendbc.car.structs import CarParams

Ecu = CarParams.Ecu

# SWSR-629: the ECUs read, with the name the driver sees in the no-entry alert
TARGET_ECUS: dict[str, str] = {"eps": "EPS", "abs": "ABS/VSC"}

# SWSR-629b: a code is active when the ECU reports any of these status bits (ISO 14229-1 DTC status byte)
ACTIVE_STATUS_MASK = (uds.DTC_STATUS_MASK_TYPE.TEST_FAILED |                       # bit 0: failing now
                      uds.DTC_STATUS_MASK_TYPE.TEST_FAILED_THIS_OPERATION_CYCLE |  # bit 1: failed since this ignition
                      uds.DTC_STATUS_MASK_TYPE.CONFIRMED_DTC |                     # bit 3: matured, stored until cleared
                      uds.DTC_STATUS_MASK_TYPE.WARNING_INDICATOR_REQUESTED)        # bit 7: the ECU asks for its lamp
# codes the release record exempts as not affecting lateral or longitudinal control, as (ecu, code); none exempt.
# Adding one needs an impact analysis (WP-M-12)
EXEMPT_DTCS: frozenset[tuple[str, str]] = frozenset()

# the request: tester present, then every stored code (mask 0xFF) so that the log shows all of them
DTC_REQUEST = bytes([uds.SERVICE_TYPE.READ_DTC_INFORMATION, uds.DTC_REPORT_TYPE.DTC_BY_STATUS_MASK,
                     uds.DTC_STATUS_MASK_TYPE.ALL])
DTC_RESPONSE = bytes([uds.SERVICE_TYPE.READ_DTC_INFORMATION + 0x40, uds.DTC_REPORT_TYPE.DTC_BY_STATUS_MASK])
REQUESTS = [StdQueries.TESTER_PRESENT_REQUEST, DTC_REQUEST]
RESPONSES = [StdQueries.TESTER_PRESENT_RESPONSE, DTC_RESPONSE]
DTC_BUS = 0  # the bus of the Toyota firmware query (opendbc toyota/values.py FW_QUERY_CONFIG)

# SWSR-629c: read limits. An ECU that has not answered completely after these is "failed"
RESPONSE_TIMEOUT = 0.5  # s, per ISO-TP response (the firmware query uses 0.1 s; a code list can be longer)
ATTEMPT_TIMEOUT = 2.0   # s, all ECUs of one attempt
ATTEMPTS = 2            # a second attempt only for the ECUs that did not answer the first

# SWSR-629a: the car is stationary when this many consecutive valid carState samples show standstill
STATIONARY_SAMPLES = 20      # 0.2 s at 100 Hz
STATIONARY_MAX_TIME = 1.0    # s to find them, else the read is skipped

OK, ACTIVE, FAILED = "ok", "active", "failed"
PARAM = "VehicleDtcStatus"


@dataclass(frozen=True)
class EcuDtcResult:
  ecu: str
  result: str                          # OK, ACTIVE or FAILED
  active: tuple[str, ...] = ()         # active, not exempt codes
  stored: tuple[str, ...] = ()         # every code reported, as "C1234:0x09"
  detail: str = ""

  def to_dict(self) -> dict:
    return {"ecu": self.ecu, "result": self.result, "active": list(self.active), "stored": list(self.stored),
            "detail": self.detail}


@dataclass(frozen=True)
class DtcStatus:
  read: bool                           # false: no request was sent (car moving or not stationary-confirmed)
  reason: str
  ecus: tuple[EcuDtcResult, ...] = ()

  def to_dict(self) -> dict:
    return {"read": self.read, "reason": self.reason, "ecus": [e.to_dict() for e in self.ecus]}

  @staticmethod
  def from_dict(d) -> "DtcStatus":
    """A missing or malformed record counts as not read (SWSR-629d)"""
    try:
      ecus = tuple(EcuDtcResult(e["ecu"], e["result"], tuple(e["active"]), tuple(e["stored"]), e.get("detail", ""))
                   for e in d["ecus"])
      return DtcStatus(bool(d["read"]), str(d["reason"]), ecus)
    except (KeyError, TypeError, ValueError):
      return DtcStatus(False, "no fault-code record from card")

  def active_ecus(self) -> list[str]:
    return [e.ecu for e in self.ecus if e.result == ACTIVE]

  def complete(self) -> bool:
    """Every target ECU answered completely (SWSR-629c)"""
    results = {e.ecu: e.result for e in self.ecus}
    return self.read and all(results.get(ecu) in (OK, ACTIVE) for ecu in TARGET_ECUS)


def parse_dtc_response(ecu: str, data: bytes) -> EcuDtcResult:
  """data follows the 0x59 0x02 prefix: the status availability mask, then 3 bytes code and 1 byte status per code"""
  if len(data) < 1 or (len(data) - 1) % 4 != 0:
    return EcuDtcResult(ecu, FAILED, detail=f"malformed response 0x{data.hex()}")
  availability = data[0]
  if availability & ACTIVE_STATUS_MASK == 0:
    return EcuDtcResult(ecu, FAILED, detail=f"status availability 0x{availability:02x} has none of the active bits")

  stored, active = [], []
  for i in range(1, len(data), 4):
    code = uds.get_dtc_num_as_str(data[i:i + 3])
    status = data[i + 3]
    stored.append(f"{code}:0x{status:02x}")
    if status & availability & ACTIVE_STATUS_MASK and (ecu, code) not in EXEMPT_DTCS:
      active.append(code)
  return EcuDtcResult(ecu, ACTIVE if active else OK, tuple(active), tuple(stored))


def target_addrs(car_fingerprint: str) -> dict[str, tuple[int, int | None]]:
  """The EPS and ABS/VSC addresses of the platform's firmware query; an ECU missing here cannot be read"""
  addrs = {}
  for (ecu, addr, sub_addr) in FW_VERSIONS.get(car_fingerprint, {}):
    name = ECU_NAME.get(ecu)
    if name in TARGET_ECUS and name not in addrs:
      addrs[name] = (addr, sub_addr)
  return addrs


def query_dtcs(can_send: CanSendCallable, can_recv: CanRecvCallable, car_fingerprint: str) -> tuple[EcuDtcResult, ...]:
  addrs = target_addrs(car_fingerprint)
  responses: dict[str, bytes] = {}
  for _ in range(ATTEMPTS):
    pending = [a for name, a in addrs.items() if name not in responses]
    if not pending:
      break
    query = IsoTpParallelQuery(can_send, can_recv, DTC_BUS, pending, REQUESTS, RESPONSES)
    data = query.get_data(RESPONSE_TIMEOUT, total_timeout=ATTEMPT_TIMEOUT)
    for name, a in addrs.items():
      if a in data:
        responses[name] = data[a]

  results = []
  for name in TARGET_ECUS:
    if name not in addrs:
      results.append(EcuDtcResult(name, FAILED, detail=f"no {name} address for {car_fingerprint}"))
    elif name not in responses:
      results.append(EcuDtcResult(name, FAILED, detail=f"no complete answer from 0x{addrs[name][0]:x}"))
    else:
      results.append(parse_dtc_response(name, responses[name]))
  return tuple(results)


def vehicle_stationary(sample: Callable[[], object]) -> bool:
  """sample() parses the CAN received since the last call and returns a carState (SWSR-629a)"""
  start = time.monotonic()
  count = 0
  while time.monotonic() - start < STATIONARY_MAX_TIME:
    cs = sample()
    if not cs.canValid:
      count = 0
      continue
    if not cs.standstill:
      return False
    count += 1
    if count >= STATIONARY_SAMPLES:
      return True
  return False


def read_startup_dtcs(can_send: CanSendCallable, can_recv: CanRecvCallable, car_fingerprint: str,
                      sample: Callable[[], object]) -> DtcStatus:
  """Called once by card, before it sets FirmwareQueryDone (the panda is still in the ELM327 mode)"""
  try:
    if not vehicle_stationary(sample):
      status = DtcStatus(False, "car not seen stationary at start-up: fault codes not read")
    else:
      # drop the frames buffered during the stationary check
      can_recv()
      status = DtcStatus(True, "read at start-up", query_dtcs(can_send, can_recv, car_fingerprint))
  except Exception as e:
    # an error ends in the same place as a failed read: no engagement this ignition cycle, and card keeps running
    carlog.exception("vehicle fault-code read failed")
    status = DtcStatus(False, f"fault-code read raised {type(e).__name__}")
  carlog.warning({"event": "vehicle fault codes", **status.to_dict()})
  return status
