#!/usr/bin/env python3
"""Tests for vmodel.py: geometry self-check for every lens and size, determinism, the colour rule, the structure
derived from trace_map, locator highlighting and alt text."""
from __future__ import annotations

import dataclasses
import re
import sys
import unittest
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trace_map as tm
import vmodel as vm

LEVELS = [lv.key for lv in tm.LEFT + tm.RIGHT]


class VModel(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.d = vm.load()
    cls.goal = vm.goals(cls.d)[0]
    cls.drawings = {(lens, size): vm.draw(lens, size, goal=cls.goal, model=cls.d,
                                          highlight={"SYS3", "SYS4"} if size == "locator" else ())
                    for lens in vm.LENSES for size in vm.SIZES}

  def test_geometry_self_check_every_lens_and_size(self):
    for (lens, size), dr in self.drawings.items():
      self.assertEqual(vm.check(dr), [], f"{lens} {size}")
    for g in vm.goals(self.d):
      self.assertEqual(vm.check(vm.draw("goal", "card", goal=g, model=self.d)), [], g)
    self.assertEqual(vm.check(vm.goal_grid(self.d)), [])

  def test_self_check_catches_problems(self):
    dr = vm.draw("status", "full", model=self.d)
    k, x, y, w, h = dr.boxes[0]
    dr.boxes.append(("clone", x + 5, y + 5, w, h))
    dr.texts.append(("x" * 200, x + 5, y + 5, x + 2000, y + 15, k))
    problems = vm.check(dr)
    self.assertTrue(any("overlap" in p for p in problems))
    self.assertTrue(any("outside the viewBox" in p for p in problems))
    self.assertTrue(any("does not fit" in p for p in problems))

  def test_deterministic(self):
    for lens in vm.LENSES:
      for size in vm.SIZES:
        self.assertEqual(vm.render(lens, size, goal=self.goal, model=self.d), vm.render(lens, size, goal=self.goal, model=self.d))
    self.assertEqual(vm.render("trace", "full"), vm.render("trace", "full", model=self.d))

  def test_valid_svg_with_role_title_desc(self):
    for lens in vm.LENSES:
      for size in vm.SIZES:
        doc = xml.dom.minidom.parseString(vm.render(lens, size, goal=self.goal, model=self.d))
        root = doc.documentElement
        self.assertEqual(root.getAttribute("role"), "img")
        self.assertTrue(doc.getElementsByTagName("title")[0].firstChild.data)
        self.assertTrue(doc.getElementsByTagName("desc")[0].firstChild.data)
        self.assertRegex(root.getAttribute("height"), r"^\d+$")  # render.js and browsers read whole pixels

  def test_every_level_drawn_exactly_once(self):
    for (lens, size), dr in self.drawings.items():
      keys = [b[0] for b in dr.boxes if not b[0].startswith("gate-")]
      self.assertEqual(sorted(keys), sorted(LEVELS), f"{lens} {size}")
    svg = vm.render("status", "full", model=self.d)
    for lv in tm.LEFT + tm.RIGHT:
      self.assertEqual(svg.count(f">{lv.process}</text>"), 1, lv.process)

  def test_bridges_follow_pairs(self):
    for (lens, size), dr in self.drawings.items():
      pos = {k: (x, y, w, h) for k, x, y, w, h in dr.boxes}
      for left, right, _ in tm.PAIRS:
        lx, ly, lw, lh = pos[left]
        rx = pos[right][0]
        self.assertIn((rx - 2, ly + lh / 2, lx + lw + 6, ly + lh / 2), dr.lines, f"{lens} {size} {left}-{right}")
        self.assertLess(lx + lw, rx, "a verification level sits right of the level it verifies")
    trace = vm.render("trace", "full", model=self.d)
    for _, right, kinds in tm.PAIRS[:3]:  # trunk bridges carry the trace_map coverage text
      self.assertIn(f">{tm.pair_status(self.d.m, right, kinds)[1]}</text>", trace)

  def test_arm_grouping_derived_from_pairs(self):
    trunk, arms = vm.structure()
    self.assertEqual(trunk, [(lv_l, lv_r) for lv_l, lv_r, _ in tm.PAIRS if tm.level(lv_l).process.startswith("SYS.")])
    prefixes = [p for p, _ in arms]
    expected = []
    for left, _, _ in tm.PAIRS:
      p = tm.level(left).process.split(".")[0]
      if p != "SYS" and p not in expected:
        expected.append(p)
    self.assertEqual(prefixes, expected)
    self.assertEqual(prefixes, ["SWE", "HWE", "MLE"])
    self.assertEqual(dict(arms)["SWE"], [("SWE1", "SWE6"), ("SWE2", "SWE5"), ("SWE3", "SWE4")])
    self.assertEqual(dict(arms)["HWE"], [("HWE1", "HWE4"), ("HWE2", "HWE3")])
    self.assertEqual(dict(arms)["MLE"], [("MLE1", "MLE4")])
    self.assertEqual(set(vm.ARM_NAME), set(prefixes))
    for prefix, rows in arms:
      for left, right in rows:
        self.assertEqual({tm.level(left).process[:3], tm.level(right).process[:3]}, {prefix})

  def test_trunk_steps_inward_and_arms_sit_in_the_bracket(self):
    lay = vm.layout("full")
    trunk, arms = vm.structure()
    xs = [lay.pos[left][0] for left, _ in trunk]
    self.assertEqual(xs, sorted(xs))
    bx, by, bw, bh = lay.bracket
    for _, rows in arms:
      for left, right in rows:
        for k in (left, right):
          x, y, w, h = lay.pos[k]
          self.assertTrue(bx < x and x + w < bx + bw and by < y and y + h < by + bh, k)

  def test_colour_rule_nothing_green_today(self):
    earned = (any(st in ("A", "B") for st, _ in self.d.register.values()) or "passed" in self.d.gate_status.values()
              or any(self.d.passed.values()))
    if not earned:
      for (lens, size), dr in self.drawings.items():
        self.assertNotIn(vm.GREEN, vm.svg(dr), f"{lens} {size}")
        self.assertNotIn("ok", dr.states.values())

  def test_colour_rule_green_only_when_earned(self):
    reg = dict(self.d.register)
    for w in tm.level("SYS1").wps:
      reg[w] = ("A", reg[w][1])
    d = dataclasses.replace(self.d, register=reg, gate_status={**self.d.gate_status, "G1": "passed"})
    st = vm.draw("status", "full", model=d)
    self.assertEqual(st.states["SYS1"], "ok")
    self.assertEqual(st.states["SYS2"], "prog")
    self.assertIn(vm.GREEN, vm.svg(st))
    gate = vm.draw("gate", "card", model=d)
    self.assertEqual({k for k, s in gate.states.items() if s == "ok"}, {k for k in LEVELS if vm.needed_gate(d, k) == "G1"})
    vv = vm.draw("vv", "card", model=d)  # an approved WP never makes a verification level green: only passed cases do
    self.assertNotIn("ok", vv.states.values())
    sk = dict(self.d.register)
    for w in tm.level("SWE2").wps:
      sk[w] = ("S", sk[w][1])
    self.assertEqual(vm.draw("status", "card", model=dataclasses.replace(self.d, register=sk)).states["SWE2"], "none")

  def test_named_is_never_green(self):
    for g in vm.goals(self.d):
      dr = vm.draw("goal", "card", goal=g, model=self.d)
      self.assertNotIn("ok", dr.states.values(), g)

  def test_executed_counts_are_derived(self):
    # links/verification.yaml links tests to requirements; it records no result, so nothing counts as executed
    self.assertNotIn("result:", vm.VERIFICATION_LINKS.read_text(encoding="utf-8") if vm.VERIFICATION_LINKS.exists() else "")
    self.assertEqual(set(self.d.executed.values()), {0})
    self.assertEqual(self.d.cases["SYS4"], sum(len(self.d.m.specs.get(p, {})) for p in tm.level("SYS4").tests))
    self.assertIn(f">{self.d.cases['VAL1']} specified · 0 executed</text>", vm.render("status", "full", model=self.d))

  def test_status_from_register(self):
    reg, gates = vm.read_register()
    self.assertEqual([g for g, _ in gates], [f"G{i}" for i in range(7)])
    self.assertEqual(reg["WP-C-01"][0], "D")
    self.assertEqual(vm.needed_gate(self.d, "SYS1"), "G1")
    self.assertEqual(vm.needed_gate(self.d, "VAL1"), "G5")

  def test_locator_highlight(self):
    lit = {"SYS3", "SWE1"}
    dr = vm.draw("status", "locator", highlight=lit)
    svg = vm.svg(dr)
    self.assertEqual({k for k, s in dr.states.items() if s == "highlight"}, lit)
    self.assertEqual(svg.count(f'fill="{vm.HL}"'), len(lit))
    self.assertEqual(svg.count(f'fill="{vm.LOC_FILL}"'), len(LEVELS) - len(lit))
    self.assertEqual(re.findall(r"<text", svg), [], "a locator has no text")
    title = re.search(r"<title>(.*?)</title>", svg).group(1)
    desc = re.search(r"<desc>(.*?)</desc>", svg).group(1)
    for k in lit:
      self.assertIn(tm.level(k).process, title)
      self.assertIn(tm.level(k).process, desc)
    self.assertNotIn("SYS.1", title)
    with self.assertRaises(ValueError):
      vm.draw("status", "locator", highlight={"NOPE"})

  def test_alt_text_names_what_is_shown(self):
    dr = vm.draw("trace", "card", highlight={"SWE1"}, model=self.d)
    self.assertIn("Highlighted: SWE.1", dr.desc)
    for lv in tm.LEFT + tm.RIGHT:
      self.assertIn(lv.process, dr.desc)
    self.assertIn("G0 not passed", vm.draw("status", "full", model=self.d).desc)

  def test_card_text_is_process_and_one_number(self):
    dr = vm.draw("status", "card", model=self.d)
    for k in LEVELS:
      inside = [t[0] for t in dr.texts if t[5] == k]
      self.assertEqual(inside[0], tm.level(k).process)
      self.assertLessEqual(len(inside), 2)
      self.assertTrue(all(len(t) <= 8 for t in inside[1:]), inside)

  def test_unknown_lens_or_size(self):
    with self.assertRaises(ValueError):
      vm.render("colour", "full", model=self.d)
    with self.assertRaises(ValueError):
      vm.render("goal", "card", model=self.d)


if __name__ == "__main__":
  unittest.main()
