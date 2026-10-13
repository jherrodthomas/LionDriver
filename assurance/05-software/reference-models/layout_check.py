#!/usr/bin/env python3
"""Signal-layout check: the CAN bit positions stated in the HSI specification, against the DBC and against the C.

The back-to-back run (b2b_toy_auth.py) packs every frame with opendbc's CANPacker from the DBC, so the model and the C
share one input. A DBC error would therefore go unnoticed there if the C used the same wrong position (TE-01 §5,
TL-29 known issue). This check uses a second source, the bit positions stated in WP-S-05 §11.1:

  L0  the positions below are still the ones WP-S-05 §11.1 states (read from the document at run time).
  L1  DBC vs specification: packing the signal with the DBC changes exactly the stated bit (checksum byte excluded).
  L2  C vs specification: frames built by hand (stated bit set, every other data bit as given, checksum computed
      here) make the C react as the SM record says, and the neighbouring bits do not.

Signals whose position the specification does not state are listed as "not stated" and are not checked here; that is
a gap in WP-S-05, not a pass. Bit numbering: "bit n" is read as byte n // 8, bit n % 8 counted from the least
significant bit (LA-01: WP-S-05 does not define its numbering; this is the reading under which all stated
positions are consistent). Checksum: WP-W-05 UN-17 (a description of the code, so not independent of it).

Needs the opendbc test environment, like b2b_toy_auth.py. Prints JSON; exit 1 on any mismatch.
  opendbc_repo/.venv/bin/python assurance/05-software/reference-models/layout_check.py [--variant reference|upstream]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# WP-S-05 §11.1 (v at this baseline): signal, message, address, stated bit, row
STATED = [
  ("CRUISE_ACTIVE", "PCM_CRUISE", 0x1D2, 5, "S-09"),
  ("GAS_RELEASED", "PCM_CRUISE", 0x1D2, 4, "S-10"),
  ("BRAKE_PRESSED", "BRAKE_MODULE", 0x226, 37, "S-11"),
]
# Signals the envelope or the model uses whose bit position WP-S-05 §11.1 does not state
NOT_STATED = [
  ("MAIN_ON", "PCM_CRUISE_2 0x1D3", "S-13 gives no bit"),
  ("WHEEL_SPEED_FR/FL/RR/RL and *_FAULT", "WHEEL_SPEEDS 0xAA", "S-06 gives width, scale and offset, not positions; fault bits not mentioned"),
  ("LKA_STATE", "EPS_STATUS 0x262", "S-12 gives width only"),
  ("STEER_ANGLE_INITIALIZING (quality flag)", "STEER_TORQUE_SENSOR 0x260", "not in §11.1 (WP-W-05 UN-17 describes bit 3 from the code)"),
]
DLC = 8
BIT = {sig: bit for sig, _, _, bit, _ in STATED}
CRUISE, GAS, BRAKE = BIT["CRUISE_ACTIVE"], BIT["GAS_RELEASED"], BIT["BRAKE_PRESSED"]


def bitpos(n: int) -> tuple[int, int]:
  return n // 8, n % 8  # LA-01


def toyota_checksum(addr: int, data: bytes) -> int:
  # WP-W-05 UN-17: 8-bit sum of the address bytes, the length and the data bytes except the last
  return ((addr & 0xFF) + (addr >> 8) + len(data) + sum(data[:-1])) & 0xFF


def hand_frame(addr: int, bits: set[int], checksum: bool) -> bytes:
  d = bytearray(DLC)
  for n in bits:
    byte, bit = bitpos(n)
    d[byte] |= 1 << bit
  if checksum:
    d[-1] = toyota_checksum(addr, bytes(d))
  return bytes(d)


def data_bits(exclude_last: bool) -> list[int]:
  return list(range((DLC - 1 if exclude_last else DLC) * 8))


WP_S05 = HERE.parents[1] / "03-system" / "WP-S-05-hsi-specification.md"


def l0() -> list[dict]:
  """The positions above must still be the ones WP-S-05 §11.1 states (the check is only as current as this copy)."""
  rows = {}
  for line in WP_S05.read_text(encoding="utf-8").splitlines():
    cells = [c.strip() for c in line.split("|")]
    if len(cells) > 2 and cells[1].startswith("S-"):
      rows[cells[1]] = cells[2]
  out = []
  for sig, _, addr, bit, row in STATED:
    text = rows.get(row, "")
    found = [int(n) for n in re.findall(r"\bbit (\d+)", text)]
    out.append({"check": "L0", "signal": sig, "row": row, "stated_bit": bit, "spec_text": text,
                "ok": sig in text and f"0x{addr:X}" in text and found == [bit]})
  return out


def l1(packer) -> list[dict]:
  out = []
  for sig, msg, addr, bit, row in STATED:
    _, zero, _ = packer.make_can_msg(msg, 0, {sig: 0})
    _, one, _ = packer.make_can_msg(msg, 0, {sig: 1})
    n_check = DLC - 1 if addr == 0x1D2 else DLC  # 0x1D2 carries a checksum in its last byte, 0x226 does not
    changed = [i * 8 + b for i in range(n_check) for b in range(8) if (zero[i] ^ one[i]) >> b & 1]
    out.append({"check": "L1", "signal": sig, "row": row, "stated_bit": bit, "dbc_bits": changed,
                "ok": changed == [bit]})
  return out


def l2(c) -> list[dict]:
  """C reaction to hand-built frames. Background messages (not under test) are packed from the DBC."""
  s, lp = c.s, c.lp
  out = []

  def background(t, cruise_frame=None, brake_frame=None):
    s.set_timer(t)
    for name, addr, vals in (("WHEEL_SPEEDS", 0x0AA, {f"WHEEL_SPEED_{w}": 0.0 for w in ("FR", "FL", "RR", "RL")}),
                             ("STEER_TORQUE_SENSOR", 0x260, {}),
                             ("EPS_STATUS", 0x262, {"LKA_STATE": 5}),
                             ("PCM_CRUISE_2", 0x1D3, {"MAIN_ON": 1})):
      _, dat, _ = c.packer.make_can_msg(name, 0, vals)
      s.safety_rx_hook(lp.make_CANPacket(addr, 0, dat))
    s.safety_rx_hook(lp.make_CANPacket(0x226, 0, brake_frame or hand_frame(0x226, set(), False)))
    s.safety_rx_hook(lp.make_CANPacket(0x1D2, 0, cruise_frame or hand_frame(0x1D2, {GAS}, True)))
    s.safety_tick()

  def settle(t0):
    for k in range(20):
      background(t0 + k * 10_000)
    return t0 + 20 * 10_000

  def engaged_at(t):
    background(t, cruise_frame=hand_frame(0x1D2, {GAS, CRUISE}, True))
    return bool(s.get_controls_allowed())

  def case(name, ok, detail=""):
    out.append({"check": "L2", "case": name, "ok": bool(ok), "detail": detail})

  others_1d2 = set(data_bits(True)) - {CRUISE}
  others_226 = set(data_bits(False)) - {BRAKE}

  # CRUISE_ACTIVE bit 5: a rising edge on bit 5 alone engages; every other data bit set, bit 5 clear, does not
  c.start(); t = settle(0)
  case("bit 5 rising engages (S-09)", engaged_at(t))
  c.start(); t = settle(0)
  background(t, cruise_frame=hand_frame(0x1D2, others_1d2, True))
  case("all 0x1D2 data bits except 5 set: no engagement", not s.get_controls_allowed())
  c.start(); t = settle(0); pre = engaged_at(t)
  background(t + 10_000, cruise_frame=hand_frame(0x1D2, others_1d2, True))
  case("engaged, bit 5 cleared with all other bits set: authority cleared (T2)", pre and not s.get_controls_allowed())

  # GAS_RELEASED bit 4: gas pressed is the inverse of bit 4 and is held in gas_pressed_prev after the RX call
  c.start(); t = settle(0)
  background(t, cruise_frame=hand_frame(0x1D2, set(), True))
  pressed_without = bool(s.get_gas_pressed_prev())
  background(t + 10_000, cruise_frame=hand_frame(0x1D2, {GAS}, True))
  released_with = not s.get_gas_pressed_prev()
  background(t + 20_000, cruise_frame=hand_frame(0x1D2, set(data_bits(True)) - {GAS, CRUISE}, True))
  pressed_others = bool(s.get_gas_pressed_prev())
  case("bit 4 clear = gas pressed, bit 4 set = released, other bits do not release (S-10)",
       pressed_without and released_with and pressed_others,
       f"pressed_without_bit4={pressed_without} released_with_bit4={released_with} pressed_with_others={pressed_others}")

  # BRAKE_PRESSED bit 37: engaged, a 0x226 frame with only bit 37 clears; every other bit set does not
  c.start(); t = settle(0); pre = engaged_at(t)
  background(t + 10_000, cruise_frame=hand_frame(0x1D2, {GAS, CRUISE}, True), brake_frame=hand_frame(0x226, others_226, False))
  kept = bool(s.get_controls_allowed()) and not s.get_brake_pressed_prev()
  background(t + 20_000, cruise_frame=hand_frame(0x1D2, {GAS, CRUISE}, True), brake_frame=hand_frame(0x226, {BRAKE}, False))
  cleared = not s.get_controls_allowed() and bool(s.get_brake_pressed_prev())
  case("all 0x226 bits except 37 set: authority kept; bit 37 alone: cleared (S-11, T3)", pre and kept and cleared,
       f"kept_with_others={kept} cleared_with_bit37={cleared}")

  # the hand checksum must be the one the C accepts: a frame with the checksum off by one is an RX fault (T4)
  c.start(); t = settle(0); pre = engaged_at(t)
  bad = bytearray(hand_frame(0x1D2, {GAS, CRUISE}, True)); bad[-1] ^= 0x01
  background(t + 10_000, cruise_frame=bytes(bad))
  case("hand checksum agrees with the C (corrupted copy clears authority)", pre and not s.get_controls_allowed())
  return out


def main() -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--variant", choices=["reference", "upstream"], default="reference")
  a = ap.parse_args()
  want = "1" if a.variant == "reference" else "0"
  if os.environ.get("LIONDRIVER_REFERENCE", "0") != want:
    os.environ["LIONDRIVER_REFERENCE"] = want
    os.execv(sys.executable, [sys.executable, *sys.argv])
  from b2b_toy_auth import CSide
  c = CSide()
  results = l0() + l1(c.packer) + l2(c)
  failed = [r for r in results if not r["ok"]]
  print(json.dumps({"variant": a.variant, "results": results,
                    "not_stated": [dict(zip(("signal", "message", "note"), n)) for n in NOT_STATED],
                    "failed": len(failed)}, indent=1))
  for r in results:
    print(f"{'ok  ' if r['ok'] else 'FAIL'} {r['check']} {r.get('signal') or r.get('case')} "
          f"{r.get('detail', '') or (str(r.get('dbc_bits')) if r['check'] == 'L1' else str(r.get('stated_bit', '')))}", file=sys.stderr)
  return 1 if failed else 0


if __name__ == "__main__":
  sys.exit(main())
