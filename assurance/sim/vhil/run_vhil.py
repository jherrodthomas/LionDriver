#!/usr/bin/env python3
"""Run the panda HIL tests on the virtual bench (vhil.py) and write a report.

    python3 assurance/sim/vhil/run_vhil.py                       # test_12 ... test_16, reference build
    python3 assurance/sim/vhil/run_vhil.py --report out.md        # also write the report
    python3 assurance/sim/vhil/run_vhil.py -k test_15             # only matching test modules

The test files run unchanged: `import panda` gives the virtual Panda and PandaJungle (vhil.install), and HITL=1,
REFERENCE_BUILD=1 select them as on the bench. Exit status 1 if a test fails, unless the failure is a known open item (KNOWN_OPEN). A model of the bench, not a
measurement (WP-S-04 §6): a pass here closes no FMEA cause (DQ-206 A); the real bench runs M-04 ... M-06.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
# the HIL tests that need only the safety logic, the CAN paths and the health packet. test_10 (watchdog hang
# injection, relay drive on the SBU lines) and test_11 (USB command lock) need the real board
MODULES = ["test_12_rx_timeout", "test_13_eps_fault", "test_14_tx_rate", "test_15_heartbeat_siren",
           "test_16_engaged_mismatch_siren"]
# Failures that show an open item of the firmware design, each with its register entry. They still run and are
# reported as FAIL; they do not fail the run, because the test cannot pass until its open item is settled. Remove the
# entry when it is. Any other failure fails the run.
KNOWN_OPEN = {
  "test_12_rx_timeout.TestToyotaRxTimeout.test_timeout_per_message [EPS_STATUS]":
    "DQ-431 A: 0x262 at 25 Hz is detected within 0.21 s against TSR-401's 0.2 s; open until its rate is measured",
}


class Recorder(unittest.TextTestResult):
  """Keeps each test's outcome and the lines it printed (the tests print their measured times)."""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.rows: list[tuple[str, str, str, list[str]]] = []
    self._out = None
    self._t = 0.0

  def startTest(self, test):
    self._out = io.StringIO()
    self._redirect = contextlib.redirect_stdout(self._out)
    self._redirect.__enter__()
    self._t = time.monotonic()
    super().startTest(test)

  def _row(self, test, outcome, detail=""):
    self.rows.append((test.id().split(".", 3)[-1], outcome, detail, []))

  def stopTest(self, test):
    self._redirect.__exit__(None, None, None)
    lines = [ln for ln in self._out.getvalue().splitlines() if ln.strip()]
    name = test.id().split(".", 3)[-1]
    rows = [r for r in self.rows if r[0].startswith(name)]
    if rows:  # the test's own row, or its last failed subtest when a subtest failed (no addSuccess then)
      rows[-1][3].extend(lines)
    super().stopTest(test)

  def addSuccess(self, test):
    super().addSuccess(test)
    self._row(test, "pass")

  def addFailure(self, test, err):
    super().addFailure(test, err)
    self._row(test, "FAIL", str(err[1]).splitlines()[0])

  def addError(self, test, err):
    super().addError(test, err)
    self._row(test, "ERROR", str(err[1]).splitlines()[0])

  def addSkip(self, test, reason):
    super().addSkip(test, reason)
    self._row(test, "skip", reason)

  def addSubTest(self, test, subtest, err):
    super().addSubTest(test, subtest, err)
    if err is not None:
      name = subtest.id().split(".", 3)[-1]
      self.rows.append((name, "FAIL", str(err[1]).splitlines()[0], []))


def unexpected(rows) -> list[str]:
  """The failed tests that are not a known open item."""
  return [r[0] for r in rows if r[1] in ("FAIL", "ERROR") and r[0] not in KNOWN_OPEN]


def report(rows, reference: bool, wall_s: float) -> str:
  n_fail = sum(r[1] in ("FAIL", "ERROR") for r in rows)
  n_open = sum(r[1] == "FAIL" and r[0] in KNOWN_OPEN for r in rows)
  out = ["# Virtual HIL run", "",
         " ".join([f"Panda HIL tests `{', '.join(MODULES)}` on the virtual bench (`assurance/sim/vhil`),",
                   f"{'reference' if reference else 'base'} build, {wall_s:.0f} s wall time:",
                   f"{sum(r[1] == 'pass' for r in rows)} passed, {n_fail} failed ({n_open} of them a known open item),",
                   f"{sum(r[1] == 'skip' for r in rows)} skipped."]), "",
         "A model of the bench, not a measurement (WP-S-04 §6): a pass closes no FMEA cause (DQ-206 A).", "",
         "| Test | Result | Detail | Printed by the test |", "|---|---|---|---|"]
  for name, outcome, detail, lines in rows:
    if outcome == "FAIL" and name in KNOWN_OPEN:
      outcome, detail = "FAIL (open)", f"{detail}. {KNOWN_OPEN[name]}"
    out.append(f"| `{name}` | {outcome} | {detail.replace('|', '/')} | {'<br>'.join(lines).replace('|', '/')} |")
  return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--report", type=Path, help="write the run report (Markdown) to this path")
  ap.add_argument("-k", dest="pattern", help="only test modules whose name contains this")
  ap.add_argument("--base-build", action="store_true", help="the base build instead of the reference build")
  args = ap.parse_args(argv)

  os.environ["HITL"] = "1"
  os.environ["REFERENCE_BUILD"] = "0" if args.base_build else "1"
  sys.path.insert(0, str(ROOT))
  sys.path.insert(0, str(HERE))
  import vhil
  vhil.install()

  modules = [m for m in MODULES if not args.pattern or args.pattern in m]
  suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(f"panda.tests.hitl.{m}") for m in modules)
  t = time.monotonic()
  runner = unittest.TextTestRunner(resultclass=Recorder, verbosity=2, stream=sys.stderr)
  result = runner.run(suite)
  wall = time.monotonic() - t
  text = report(result.rows, os.environ["REFERENCE_BUILD"] == "1", wall)
  if args.report:
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(text, encoding="utf-8")
  print(text)
  bad = unexpected(result.rows)
  if bad:
    print("unexpected failures: " + ", ".join(bad), file=sys.stderr)
  return 1 if bad else 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
