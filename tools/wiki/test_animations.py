#!/usr/bin/env python3
"""Unit tests for animations.py: every drawn phrase is in its source, and both SVGs are well formed."""
from __future__ import annotations

import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import animations
import build_wiki


class SourceTests(unittest.TestCase):
  def test_every_drawn_phrase_is_in_the_real_sources(self):
    self.assertEqual(animations.problems(), [])

  def test_a_changed_source_is_reported(self):
    with tempfile.TemporaryDirectory() as d:
      root = Path(d)
      for rel in (animations.TSC, animations.PAGE):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text((animations.ROOT / rel).read_text(encoding="utf-8").replace("for at least 3 s", "for 2 s"),
                                encoding="utf-8")
      errs = animations.problems(root)
      self.assertTrue(any("for at least 3 s" in e for e in errs), errs)

  def test_split_lines_join_back_to_the_quoted_line(self):
    for line, parts in animations.PARTS.items():
      self.assertEqual(" ".join(s for _, s in parts), line)
      self.assertTrue(all(slot in animations.SLOT for slot, _ in parts))


class RenderTests(unittest.TestCase):
  def test_both_render_to_well_formed_accessible_svg(self):
    out = animations.render()
    self.assertEqual(set(out), set(animations.NAMES))
    for name, text in out.items():
      doc = xml.dom.minidom.parseString(text.encode("utf-8"))
      self.assertTrue(doc.getElementsByTagName("title")[0].firstChild.data, name)
      self.assertTrue(doc.getElementsByTagName("desc")[0].firstChild.data, name)
      self.assertIn("prefers-reduced-motion: reduce", text)

  def test_clauses_are_coloured_by_their_part(self):
    text = animations.render()["req-vague-to-verifiable.svg"]
    for slot in ("TRIGGER", "AGENT", "MODAL", "ACTION", "OBJECT", "CONSTRAINT"):
      self.assertIn(f'<tspan fill="{animations.SLOT[slot]}">', text)

  def test_all_nine_incose_characteristics_are_drawn_once(self):
    names = animations.INCOSE_SHOWN + animations.INCOSE_REVIEW
    self.assertEqual(len(set(names)), 9)
    text = animations.render()["req-vague-to-verifiable.svg"]
    for n in names:
      self.assertIn(f">{'✓ ' if n in animations.INCOSE_SHOWN else ''}{n}</text>", text)

  def test_the_wiki_build_writes_both_and_accepts_the_embeds(self):
    with tempfile.TemporaryDirectory() as d:
      out = Path(d) / "wiki"
      self.assertEqual(build_wiki.build(out=out), [])
      for name in animations.NAMES:
        self.assertTrue((out / name).exists(), name)
      page = (out / animations.PAGE.name).read_text(encoding="utf-8")
      for name in animations.NAMES:
        self.assertIn(f"]({name})", page)


if __name__ == "__main__":
  unittest.main()
