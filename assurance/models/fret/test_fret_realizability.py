#!/usr/bin/env python3
"""Tests for fret_realizability.py: grouping, and Kind 2 on known cases, including a conflict injected on purpose.

Needs FRET (FRET_DIR), Kind 2 and Z3 on PATH, as the `fret` CI job provides; the grouping tests need neither.
"""

import json
import os
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fret_realizability as fr

FRET_DIR = Path(os.environ.get("FRET_DIR", ".fret/fret-electron")).resolve()


DATA = yaml.safe_load(fr.SOURCE.read_text(encoding="utf-8"))
FORMULAS = json.loads(fr.FORMULAS.read_text(encoding="utf-8"))["requirements"]
GLOSSARY = {g["name"]: g for g in DATA["glossary"]}
REQS = {r["id"]: r for r in DATA["requirements"]}
USES = {k: set(fr.NAME.findall(FORMULAS[k]["lustre"])) & set(GLOSSARY) for k in REQS}


class Fixture:
  data, formulas, glossary, reqs, uses = DATA, FORMULAS, GLOSSARY, REQS, USES
  outputs = {n for n, g in GLOSSARY.items() if g["role"] == "output"}

  def result(self, ids, extra=None):
    members = [self.reqs[i] for i in ids]
    formulas = dict(self.formulas)
    if extra:
      members.append(extra)
      formulas[extra["id"]] = {"lustre": extra["lustre"]}
      uses = dict(self.uses, **{extra["id"]: set(fr.NAME.findall(extra["lustre"])) & set(self.glossary)})
    else:
      uses = self.uses
    return fr.kind2(fr.render(FRET_DIR, fr.contract("t", members, uses, self.glossary, formulas)), "t")


class TestGrouping(unittest.TestCase, Fixture):
  def test_every_guarantee_in_one_component(self):
    groups = fr.components(self.data["requirements"], self.uses, self.outputs)
    ids = [r["id"] for g in groups for r in g if "assumption" not in r["id"].lower()]
    self.assertEqual(sorted(ids), sorted(r for r in self.reqs if "assumption" not in r.lower()))
    self.assertEqual(len(ids), len(set(ids)))

  def test_torque_rules_share_a_component(self):
    groups = fr.components(self.data["requirements"], self.uses, self.outputs)
    torque = next(g for g in groups if any(r["id"] == "FR-101" for r in g))
    self.assertTrue({"FR-103a", "FR-103d", "FR-104", "FA-101-assumption"} <= {r["id"] for r in torque})

  def test_every_variable_has_a_role(self):
    self.assertTrue(all(g.get("role") in ("input", "output") for g in self.glossary.values()))


@unittest.skipUnless((FRET_DIR / "support").exists(), "needs FRET (install_fret.sh); the CI job installs it")
class TestKind2(unittest.TestCase, Fixture):
  def test_single_rule_realizable(self):
    self.assertEqual(self.result(["FR-101", "FA-101-assumption"]), "realizable")

  def test_known_conflict_unrealizable(self):
    self.assertEqual(self.result(["FR-103d", "FR-104", "FA-104-assumption"]), "unrealizable")

  def test_injected_conflict_caught(self):
    # A requirement that never rejects contradicts TSR-101 for any frame above tau_max.
    never = {"id": "FR-injected", "fretish": "the envelope shall always satisfy !lka_frame_rejected",
             "lustre": "H(not (lka_frame_rejected))"}
    self.assertEqual(self.result(["FR-101", "FA-101-assumption"], never), "unrealizable")


if __name__ == "__main__":
  unittest.main()
