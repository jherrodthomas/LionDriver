#!/usr/bin/env python3
"""Tests for engaged_mismatch.py: the 1 Hz check revokes within two to three ticks, silently, after the steering ends."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engaged_mismatch as em
import simulate


class TestEngagedMismatch(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.rs = em.runs()

  def test_revoked_on_the_third_1hz_tick(self):
    # heartbeat not engaged from host_stale_s (plus up to one 100 ms heartbeat), then three 1 Hz ticks: the first
    # within 1 s, the third 2 s later
    stale = simulate.ASSUMPTIONS["host_stale_s"][0]
    for r in self.rs:
      self.assertTrue(stale + 2.0 < r["revoke"] <= stale + 0.1 + 3.0 + 0.01, (r["road"], r["phase"], r["revoke"]))

  def test_phases_cover_the_1hz_tick(self):
    for road in {r["road_key"] for r in self.rs}:
      rev = [r["revoke"] for r in self.rs if r["road_key"] == road]
      self.assertGreater(max(rev) - min(rev), 0.75, road)

  def test_no_siren_and_the_alert_at_the_soundd_timeout(self):
    for r in self.rs:
      self.assertIsNone(r["siren"])
      self.assertAlmostEqual(r["alert"], simulate.SELFDRIVE_STATE_TIMEOUT)

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
