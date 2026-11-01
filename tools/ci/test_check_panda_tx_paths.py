#!/usr/bin/env python3
"""Tests for check_panda_tx_paths.py (SWF-016.C1): the pinned panda tree passes, and each kind of bypass is caught."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_panda_tx_paths as tx


class TestRealTree(unittest.TestCase):
  def test_pinned_panda_passes(self):
    self.assertEqual(tx.check(), [])


class TestBypasses(unittest.TestCase):
  def setUp(self):
    self.tmp = Path(tempfile.mkdtemp())
    self.addCleanup(shutil.rmtree, self.tmp)
    self.board = self.tmp / "board"
    shutil.copytree(tx.BOARD, self.board, ignore=shutil.ignore_patterns("obj", "*.o", "*.bin", "*.elf"))

  def edit(self, rel, old, new, count=1):
    p = self.board / rel
    s = p.read_text()
    self.assertIn(old, s)
    p.write_text(s.replace(old, new, count))

  def problems(self):
    return "\n".join(tx.check(self.board))

  def test_copy_passes(self):
    self.assertEqual(tx.check(self.board), [])

  def test_host_entry_skipping_the_hook(self):
    self.edit("can_comms.h", "can_send(&to_push, to_push.bus, false);", "can_send(&to_push, to_push.bus, true);")
    self.assertIn("host TX entry calls can_send with skip_tx_hook=true", self.problems())

  def test_host_entry_with_a_variable(self):
    self.edit("can_comms.h", "can_send(&to_push, to_push.bus, false);", "can_send(&to_push, to_push.bus, skip);")
    self.assertIn("skip_tx_hook=skip", self.problems())

  def test_new_skip_path_elsewhere(self):
    self.edit("main_comms.h", "\n", "\nstatic void x(CANPacket_t *p) { can_send(p, 0U, true); }\n")
    out = self.problems()
    self.assertIn("main_comms.h", out)
    self.assertIn("outside the reviewed forwarding and body paths", out)

  def test_new_hooked_call_site_needs_review(self):
    self.edit("main_comms.h", "\n", "\nstatic void x(CANPacket_t *p) { can_send(p, 0U, false); }\n")
    self.assertIn("can_send call sites changed", self.problems())

  def test_direct_push_into_a_tx_queue(self):
    self.edit("main_comms.h", "\n", "\nstatic void x(CANPacket_t *p) { (void)can_push(can_queues[0], p); }\n")
    self.assertIn("pushes into a CAN TX queue outside can_send", self.problems())

  def test_hook_test_removed_from_can_send(self):
    self.edit("drivers/can_common.h", "if (skip_tx_hook || safety_tx_hook(to_push) != 0) {", "if (true) {")
    self.assertIn("can_send no longer tests", self.problems())

  def test_comments_ignored(self):
    self.edit("main_comms.h", "\n", "\n// can_send(p, 0U, true); can_push(can_queues[0], p);\n")
    self.assertEqual(tx.check(self.board), [])


if __name__ == "__main__":
  unittest.main()
