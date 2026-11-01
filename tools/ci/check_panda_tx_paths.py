#!/usr/bin/env python3
"""Every host CAN transmission in the panda firmware passes the safety TX hook (SW FMEA SWF-016.C1, SWF-ACT-008).

`can_send(packet, bus, skip_tx_hook)` in board/drivers/can_common.h is the only way into the CAN TX queues, and it
calls `safety_tx_hook` unless `skip_tx_hook` is true. The check reads the pinned panda sources and fails when:

  - a `can_send` call in the host TX entry (board/can_comms.h, USB and SPI bulk writes) does not pass `false`;
  - a call passes anything other than `false` outside the reviewed list below (forwarding between the car and
    camera buses, and the body firmware, which is not a car mode);
  - the set of `can_send` call sites changes, so a new TX path is reviewed before it is accepted here;
  - anything other than `can_send` pushes into the TX queues (`can_queues[...]`, `can_tx1_q` ... `can_tx3_q`);
  - `can_send` itself no longer tests `skip_tx_hook || safety_tx_hook(...)`.

Usage: python3 tools/ci/check_panda_tx_paths.py [--root panda/board]
Standard library only.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BOARD = REPO / "panda" / "board"

HOST_ENTRY = "can_comms.h"
# Reviewed call sites, as (file relative to board/, last argument): two host entries that must run the hook, the
# bus forwarding (frames the car or camera sent, after safety_fwd_hook), and the body firmware (PANDA_BODY only)
EXPECTED = sorted([
  ("can_comms.h", "false"),
  ("can_comms.h", "false"),
  ("drivers/fdcan.h", "true"),
  ("body/can.h", "true"),
  ("body/can.h", "true"),
  ("body/can.h", "true"),
  ("body/can.h", "true"),
])
SKIP_ALLOWED = {"drivers/fdcan.h", "body/can.h"}
DEFINITION = "drivers/can_common.h"
HOOK_TEST = re.compile(r"if\s*\(\s*skip_tx_hook\s*\|\|\s*\(?\s*safety_tx_hook\s*\(\s*to_push\s*\)\s*!=\s*0\s*\)?\s*\)")
TX_QUEUE_PUSH = re.compile(r"can_push\s*\(\s*(?:can_queues\s*\[|&?\s*can_tx[123]_q\b)")
CALL = re.compile(r"\bcan_send\s*\(")


def strip_comments(text: str) -> str:
  text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
  return re.sub(r"//[^\n]*", "", text)


def call_args(text: str, start: int) -> str:
  """The argument text of the call whose '(' is at text[start]."""
  depth = 0
  for i in range(start, len(text)):
    if text[i] == "(":
      depth += 1
    elif text[i] == ")":
      depth -= 1
      if depth == 0:
        return text[start + 1:i]
  raise ValueError("unbalanced call")


def last_arg(args: str) -> str:
  depth, parts, cur = 0, [], ""
  for ch in args:
    if ch in "([{":
      depth += 1
    elif ch in ")]}":
      depth -= 1
    if ch == "," and depth == 0:
      parts.append(cur)
      cur = ""
    else:
      cur += ch
  parts.append(cur)
  return parts[-1].strip()


def scan(board: Path) -> tuple[list[tuple[str, str, int]], list[str]]:
  """(call sites as (file, last argument, line), problems found while scanning)."""
  calls, problems = [], []
  for path in sorted(list(board.rglob("*.h")) + list(board.rglob("*.c"))):
    rel = path.relative_to(board).as_posix()
    text = strip_comments(path.read_text(encoding="utf-8", errors="replace"))
    for m in CALL.finditer(text):
      line = text.count("\n", 0, m.start()) + 1
      before = text[:m.start()].rstrip()
      if before.endswith("void"):  # the definition or a declaration
        continue
      calls.append((rel, last_arg(call_args(text, m.end() - 1)), line))
    if rel != DEFINITION:
      for m in TX_QUEUE_PUSH.finditer(text):
        problems.append(f"{rel}:{text.count(chr(10), 0, m.start()) + 1}: pushes into a CAN TX queue outside can_send")
    else:
      body = text[text.find("void can_send("):]
      if not HOOK_TEST.search(body[:body.find("\n}")]):
        problems.append(f"{rel}: can_send no longer tests skip_tx_hook || safety_tx_hook(to_push) != 0")
  return calls, problems


def check(board: Path = BOARD) -> list[str]:
  calls, problems = scan(board)
  for rel, arg, line in calls:
    if rel == HOST_ENTRY and arg != "false":
      problems.append(f"{rel}:{line}: host TX entry calls can_send with skip_tx_hook={arg}, not false")
    elif arg != "false" and rel not in SKIP_ALLOWED:
      problems.append(f"{rel}:{line}: can_send with skip_tx_hook={arg} outside the reviewed forwarding and body paths")
  found = sorted((rel, arg) for rel, arg, _ in calls)
  if found != EXPECTED:
    problems.append(f"can_send call sites changed: found {found}, reviewed {EXPECTED}; review the new path and "
                    + "update EXPECTED in tools/ci/check_panda_tx_paths.py")
  return problems


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
  ap.add_argument("--root", type=Path, default=BOARD)
  problems = check(ap.parse_args(argv).root)
  for p in problems:
    print(f"check_panda_tx_paths: {p}")
  if problems:
    return 1
  print(f"check_panda_tx_paths: OK, {len(EXPECTED)} can_send call sites as reviewed; the host TX entry runs the safety hook")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
