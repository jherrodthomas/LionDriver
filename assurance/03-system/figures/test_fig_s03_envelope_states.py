#!/usr/bin/env python3
"""Tests for fig_s03_envelope_states.py: committed SVG current, every revoking transition and host state drawn,
the lists checked against the state-machine records."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_s03_envelope_states as fe


class TestEnvelopeStates(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.sms = fe.records()
    cls.sw = fe.csm.swsr_records()
    cls.d = fe.parse(cls.sms, cls.sw)

  def test_committed_output_current(self):
    for name, content in fe.build().items():
      self.assertEqual((fe.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run fig_s03_envelope_states.py")

  def test_every_revocation_drawn(self):
    svg = (fe.HERE / fe.OUT).read_text(encoding="utf-8")
    for r in self.d["revokes"]:
      self.assertIn(f">{r['id']}<", svg)
    self.assertEqual({r["id"] for r in self.d["revokes"]}, set(fe.REVOKE))

  def test_not_implemented_code_is_missing(self):
    by_id = {r["id"]: r["status"] for r in self.d["revokes"]}
    self.assertEqual(by_id["T10e"], "missing")
    self.assertEqual(by_id["T12"], "missing")
    self.assertNotEqual(by_id["T10a"], "missing")

  def test_new_revocation_fails(self):
    sms = copy.deepcopy(self.sms)
    sms["SM-TOY-AUTH"]["transitions"].append({"id": "T99", "from": "ALLOWED", "to": "NOT_ALLOWED", "event": "x", "code": "y"})
    with self.assertRaises(fe.EnvelopeError):
      fe.parse(sms, self.sw)

  def test_new_host_state_fails(self):
    sms = copy.deepcopy(self.sms)
    sms["SM-SELFDRIVED"]["states"].append("newState")
    with self.assertRaises(fe.EnvelopeError):
      fe.parse(sms, self.sw)

  def test_unknown_transition_cited_fails(self):
    sms = copy.deepcopy(self.sms)
    sms["SM-TOY-AUTH"]["transitions"] = [t for t in sms["SM-TOY-AUTH"]["transitions"] if t["id"] != "T1b"]
    with self.assertRaises(fe.EnvelopeError):
      fe.parse(sms, self.sw)


if __name__ == "__main__":
  unittest.main()
