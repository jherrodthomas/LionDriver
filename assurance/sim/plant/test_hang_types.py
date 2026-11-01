#!/usr/bin/env python3
"""Tests for hang_types.py and the hang model of panda_loop.HANGS: each hang starts where the firmware's
fault-injection build puts it, and the IWDG resets as `drivers/hw_watchdog.h` makes it (SIM-OI-3, VS-FI-17)."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hang_types as ht
from corolla import ROOT
from panda_loop import HANGS

TASK = 0.010   # s, safety task period
TICK = 0.125   # s, 8 Hz tick period
COUNTS = 4 * 720   # 4 * 2^PR * (RLR + 1), the IWDG timeout in LSI cycles


class TestFirmwareInjection(unittest.TestCase):
  """The hang model restates fault_injection.h and the order of main.c; they must still read as modelled."""

  @classmethod
  def setUpClass(cls):
    board = ROOT / "panda" / "board"
    cls.fi = (board / "drivers" / "fault_injection.h").read_text(encoding="utf-8")
    cls.main = (board / "main.c").read_text(encoding="utf-8")
    cls.prio = (board / "drivers" / "irq_priorities.h").read_text(encoding="utf-8")

  def test_modes_exist(self):
    for kind, _, mode in ht.KINDS:
      self.assertIn(f"#define {HANGS[kind]} {mode}U", self.fi)

  def test_main_loop_sets_its_flag_before_it_hangs(self):
    body = self.main[self.main.index("static void main_loop_progress(void)"):]
    self.assertLess(body.index("hw_watchdog_main_loop_alive();"), body.index("fault_injection_main_loop();"))

  def test_safety_task_hangs_after_its_feed(self):
    body = self.main[self.main.index("static void safety_task_handler(void)"):]
    self.assertLess(body.index("hw_watchdog_tick();"), body.index("fault_injection_safety_task();"))

  def test_hooks_are_where_modelled(self):
    fn = lambda name: self.fi[self.fi.index(f"static void {name}(void)"):].split("\n}\n")[0]  # noqa: E731
    self.assertIn("FAULT_INJECTION_HANG_MAIN_LOOP", fn("fault_injection_main_loop"))
    self.assertIn("disable_interrupts();", fn("fault_injection_main_loop"))
    self.assertIn("FAULT_INJECTION_HANG_TICK", fn("fault_injection_tick"))
    self.assertIn("FAULT_INJECTION_HANG_SAFETY_TASK", fn("fault_injection_safety_task"))
    self.assertEqual(fn("fault_injection_safety_task").count("IND_WDG->KR = HW_WATCHDOG_KEY_FEED;"), 2)

  def test_no_interrupt_preempts_another(self):
    levels = set(re.findall(r"^#define IRQ_PRIO_\w+ (\d+)U", self.prio, re.M))
    self.assertEqual(len(levels), 1, levels)


class TestHangTypes(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.rs = ht.runs()
    cls.timing = [r for r in cls.rs if r["part"] == "timing"]

  def after(self, kind):
    return [(r["lsi"], r["reset"] - r["hang"]) for r in self.timing if r["kind"] == kind]

  def test_main_loop_gets_one_more_feed(self):
    for lsi, d in self.after("main_loop"):
      timeout = COUNTS / (lsi * 1000)
      self.assertTrue(timeout - 0.001 <= d <= timeout + TASK + 1e-9, (lsi, d))

  def test_hangs_that_stop_everything_reset_within_the_timeout(self):
    for kind in ht.STOPS_ALL:
      for lsi, d in self.after(kind):
        timeout = COUNTS / (lsi * 1000)
        self.assertTrue(timeout - TASK - 0.001 <= d <= timeout + 1e-9, (kind, lsi, d))

  def test_hang_starts_where_the_firmware_puts_it(self):
    limit = {"main_loop": 0.0, "irq_off": 0.0, "safety_task": TASK, "tick": TICK, "early_feed": TASK}
    for r in self.timing:
      self.assertTrue(0.0 <= r["hang"] <= limit[r["kind"]] + 1e-9, (r["kind"], r["phase"], r["hang"]))

  def test_early_feed_resets_at_once(self):
    for lsi, d in self.after("early_feed"):
      self.assertAlmostEqual(d, 0.0, places=6, msg=lsi)

  def test_interrupts_off_reproduces_f05(self):
    # the same hang as the catalog's F-05 at the same moment: the same events
    r = [x for x in self.rs if x["part"] == "car" and x["kind"] == "irq_off" and x["phase"] == 0.0
         and x["switch"] == "pass" and x["eps"] == "release"][0]
    import simulate
    f05 = simulate.simulate(ht.f05_case()).metrics
    self.assertAlmostEqual(r["cue"], f05["events"]["driver cue (drift)"])
    self.assertAlmostEqual(r["t_line"], f05["t_line"])

  def test_main_loop_hang_keeps_the_frames_until_the_reset(self):
    for r in self.rs:
      if r["part"] == "car" and r["kind"] == "main_loop":
        self.assertEqual(r["frames_stop"], r["reset"])
        self.assertGreater(r["frames_stop"], 0.08)

  def test_outputs_current(self):
    for path, content in ht.build().items():
      self.assertTrue(path.exists(), path.name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{path.name} is stale; run hang_types.py")


if __name__ == "__main__":
  unittest.main()
