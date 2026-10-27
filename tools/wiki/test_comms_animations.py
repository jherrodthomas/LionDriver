#!/usr/bin/env python3
"""Unit tests for comms_animations.py: the records each figure stands on, the statuses read from them, the figures and the build."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_wiki
import comms_animations as C


def copy_records(root: Path) -> None:
  for path in {p for p, _ in C.SOURCES} | {C.TSR_LIST}:
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(C.ROOT / path, root / path)


def edit(root: Path, path: Path, old: str, new: str) -> None:
  f = root / path
  text = f.read_text(encoding="utf-8")
  assert old in text, old
  f.write_text(text.replace(old, new, 1), encoding="utf-8")


class RecordTests(unittest.TestCase):
  def test_every_figure_stands_on_its_records(self):
    self.assertEqual(C.problems(), [])

  def test_statuses_are_read_from_the_tsr_list(self):
    d = C.data()
    self.assertEqual(set(d["status"]), set(C.tsrs()))
    self.assertEqual(d["status"]["TSR-410"], "not implemented")

  def test_every_fault_names_a_gate_of_its_hop(self):
    hops = {h[0]: {n for n, _k in h[4]} for h in C.HOPS}
    for hop, gate, _w, _c in C.FAULTS:
      self.assertIn(gate, hops[hop], (hop, gate))

  def test_a_planned_check_lets_its_fault_through(self):
    d = C.data()
    self.assertFalse(C.caught("H1", "CRC", d))
    self.assertTrue(C.caught("H3", "CAN CRC", d))
    self.assertTrue(C.caught("H4", "checksum, counter", d))

  def test_the_timeline_verdicts_follow_the_budgets(self):
    v = {r[0]: C.verdict(r[3], r[4], r[6])[0] for r in C.TIMELINE}
    self.assertEqual(v["Brake or wheel message stops"], C.GRN)
    self.assertEqual(v["Main computer's heartbeat stops"], C.AMBER)
    self.assertEqual(v["panda hangs while forwarding PCS"], C.RED)
    self.assertEqual(v["Wheel speeds freeze but keep coming"], C.RED)

  def test_a_changed_budget_is_a_problem(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      copy_records(root)
      edit(root, C.S04, "| SG-01 SoC heartbeat loss | 0.5 s | ≤ 0.3 s (TSR-407) |", "| SG-01 SoC heartbeat loss | 0.5 s | ≤ 0.2 s (TSR-407) |")
      self.assertTrue(any("heartbeat loss" in e for e in C.problems(root)))

  def test_a_reworded_record_is_a_problem(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      copy_records(root)
      edit(root, C.S05, "For these frames the panda is a black channel", "For these frames the panda forwards")
      self.assertTrue(any("black channel" in e for e in C.problems(root)))

  def test_a_built_crc_is_a_problem(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      copy_records(root)
      text = (root / C.TSR_LIST).read_text(encoding="utf-8")
      row = next(line for line in text.splitlines() if line.startswith("| [TSR-410]"))
      edit(root, C.TSR_LIST, row, row.replace("| not implemented |", "| implemented |"))
      self.assertTrue(any("TSR-410" in e for e in C.problems(root)))


class RenderTests(unittest.TestCase):
  def test_all_render_to_well_formed_accessible_svg(self):
    out = C.render()
    self.assertEqual(tuple(out), C.NAMES)
    for name, text in out.items():
      doc = xml.dom.minidom.parseString(text.encode("utf-8"))
      self.assertTrue(doc.getElementsByTagName("title")[0].firstChild.data, name)
      self.assertTrue(doc.getElementsByTagName("desc")[0].firstChild.data, name)
      self.assertIn("prefers-reduced-motion: reduce", text)

  def test_the_gauntlet_shows_the_record_statuses(self):
    svg, d = C.render()["comms-e2e.svg"], C.data()
    gauntlet = {k for h in C.HOPS for _n, k in h[4] if k.startswith("TSR-")}
    for k, status in ((k, d["status"][k]) for k in sorted(gauntlet)):
      self.assertIn(f"{k} · {C.STATUS[status][4]}", svg)

  def test_the_path_and_timeline_show_the_record_statuses(self):
    out, d = C.render(), C.data()
    for k in ("TSR-101", "TSR-410", "TSR-411", "TSR-408", "TSR-518"):
      self.assertIn(f"{k} · {C.STATUS[d['status'][k]][4]}", out["comms-path.svg"])
    for r in C.TIMELINE:
      self.assertIn(f"{r[5]} · {d['status'][r[5]]}", out["comms-timeline.svg"])

  def test_the_wiki_build_writes_all_and_accepts_the_embeds(self):
    with tempfile.TemporaryDirectory() as tmp:
      out = Path(tmp) / "wiki"
      self.assertEqual(build_wiki.build(out=out), [])
      page = (out / "CAN-CAN-FD-and-end-to-end-protection.md").read_text(encoding="utf-8")
      for name in C.NAMES:
        self.assertTrue((out / name).exists(), name)
        self.assertIn(f"]({name})", page)


if __name__ == "__main__":
  unittest.main()
