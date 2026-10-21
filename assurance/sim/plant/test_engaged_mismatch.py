#!/usr/bin/env python3
"""Tests for engaged_mismatch.py: the safety task revokes 0.3 s after the first "not engaged" heartbeat, and the siren
starts 0.5 s after it because no cruise cancel reaches the PCM (panda `drivers/engaged_mismatch.h`)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engaged_mismatch as em
import simulate

TASK = 0.01       # s, safety task period
HEARTBEAT = 0.1   # s, pandad heartbeat period
SPEAKER = 0.25    # s, the speaker sounds on every other 8 Hz tick


class TestEngagedMismatch(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.rs = em.runs()

  def test_revoked_0_3_s_after_the_first_not_engaged_heartbeat(self):
    # heartbeat not engaged from host_stale_s (to within one task period, plus up to one heartbeat), then 30 ticks
    stale = simulate.ASSUMPTIONS["host_stale_s"][0]
    for r in self.rs:
      self.assertTrue(stale - TASK + 0.3 - TASK <= r["revoke"] <= stale + HEARTBEAT + 0.3 + 2 * TASK,
                      (r["road"], r["phase"], r["revoke"]))

  def test_phases_cover_the_heartbeat_period(self):
    for road in {r["road_key"] for r in self.rs}:
      rev = [r["revoke"] for r in self.rs if r["road_key"] == road]
      self.assertGreater(max(rev) - min(rev), HEARTBEAT / 2, road)

  def test_siren_0_2_s_after_the_revocation_and_before_the_alert(self):
    for r in self.rs:
      self.assertIsNotNone(r["siren"], (r["road"], r["phase"]))
      self.assertTrue(0.2 - TASK <= r["siren"] - r["revoke"] <= 0.2 + SPEAKER + 2 * TASK, (r["road"], r["phase"]))
      self.assertAlmostEqual(r["alert"], simulate.SELFDRIVE_STATE_TIMEOUT)
      self.assertEqual(r["cue_kind"], "siren")

  def test_steering_ends_before_the_revocation(self):
    for r in self.rs:
      if r["torque_off"] is not None:
        self.assertLess(r["torque_off"], r["revoke"])

  def test_outputs_current(self):
    for path, content in em.build().items():
      self.assertTrue(path.exists(), path.name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{path.name} is stale; run engaged_mismatch.py")


if __name__ == "__main__":
  unittest.main()
