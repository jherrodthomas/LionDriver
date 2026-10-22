"""Checks of Hazard Scene Studio's engine (CI on Linux and Windows; no Blender: tests/fake_blender.py stands in):
a row goes through export, render and compose with progress events; a second run reuses the render; Stop ends the
render part way and the next run carries on from the stills made; another quality is another render; the queue runs
rows on a worker thread and Stop drops the rest; the plant fingerprint finds a difference and none in itself."""

from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

import row_to_scene as rs  # first: puts ../blender on the path
import engine as en  # noqa: E402
import plant_fingerprint as pf  # noqa: E402

FAKE = [sys.executable, str(rs.HERE / "tests" / "fake_blender.py")]
DEMO = "F-01/M03/OS-01/W02"


class TestEngine(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.ctx = rs.Context.load()
    cls.ad = next(a for a in rs.load_adapters() if a["id"] == "iso26262-hara")
    cls.row = rs.prefill(cls.ad, DEMO, cls.ctx)

  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    self.dir = Path(self.tmp.name)
    self.eng = en.Engine(en.Settings(out=self.dir / "out", blender=FAKE), self.ctx)

  def tearDown(self):
    os.environ.pop("FAKE_DELAY", None)
    self.tmp.cleanup()

  def run_row(self, row=None, cancel=None, eng=None):
    ev = []
    with contextlib.redirect_stdout(io.StringIO()):
      res = (eng or self.eng).run(row or self.row, self.ad, self.dir / "dash", ev.append, cancel)
    return res, ev

  def test_a_row_end_to_end(self):
    res, ev = self.run_row()
    self.assertIsNone(res.error)
    self.assertTrue(res.dashboard.exists())
    stages = [e["stage"] for e in ev]
    self.assertEqual(stages[0], "exported")
    self.assertEqual(stages[-2:], ["rendered", "drawn"])
    stills = [e for e in ev if e["stage"] == "still"]
    self.assertEqual([e["done"] for e in stills], list(range(1, stills[0]["total"] + 1)))
    self.assertTrue(res.outcome["Contact"].startswith("yes: adjacent car"))
    self.assertEqual(res.status(rendered=True), "drawn (stand-in)")

  def test_second_run_reuses_the_render(self):
    self.run_row()
    _, ev = self.run_row({**self.row, "Row ID": "another", "ASIL": "C"})
    self.assertNotIn("still", [e["stage"] for e in ev])
    self.assertEqual(ev[-1]["stage"], "drawn")

  def test_stop_and_carry_on(self):
    os.environ["FAKE_DELAY"] = "0.05"
    cancel = threading.Event()

    def stop_at_two(e):
      if e["stage"] == "still" and e["done"] == 2:
        cancel.set()
    ev = []
    with contextlib.redirect_stdout(io.StringIO()):
      res = self.eng.run(self.row, self.ad, self.dir / "dash", lambda e: (ev.append(e), stop_at_two(e)), cancel)
    self.assertEqual(ev[-1]["stage"], "cancelled")
    self.assertIsNotNone(res.error)
    d = next((self.dir / "out" / "renders").iterdir())
    made = {p.name: p.stat().st_mtime_ns for p in (d / "stills").iterdir()}
    self.assertGreaterEqual(len(made), 2)
    self.assertFalse((d / "render.json").exists())
    res, _ = self.run_row()
    self.assertIsNone(res.error)
    for name, t in made.items():                   # the stills made before Stop were kept, not made again
      self.assertEqual((d / "stills" / name).stat().st_mtime_ns, t, name)

  def test_quality_is_its_own_render(self):
    self.run_row()
    other = en.Engine(en.Settings(out=self.dir / "out", blender=FAKE, samples=8, res="960x540"), self.ctx)
    _, ev = self.run_row(eng=other)
    self.assertIn("still", [e["stage"] for e in ev])
    self.assertEqual(len(list((self.dir / "out" / "renders").iterdir())), 2)

  def test_a_row_that_cannot_be_drawn(self):
    res, ev = self.run_row({**self.row, "Environment": "moon"})
    self.assertEqual([e["stage"] for e in ev], ["error"])
    self.assertTrue(res.status(rendered=True).startswith("cannot draw: environment moon"))

  def test_no_blender(self):
    eng = en.Engine(en.Settings(out=self.dir / "out", blender=None), self.ctx)
    real = en.blender_command
    en.blender_command = lambda: None
    try:
      res, _ = self.run_row(eng=eng)
    finally:
      en.blender_command = real
    self.assertEqual(res.error, "no Blender: install it, pip install bpy, or set LIONDRIVER_BLENDER")

  def test_queue(self):
    done = []
    q = en.RenderQueue(self.eng, lambda e: None, done.append)
    with contextlib.redirect_stdout(io.StringIO()):
      q.add(self.row, self.ad, self.dir / "dash")
      q.add({**self.row, "Row ID": "night", "Condition": "W03"}, self.ad, self.dir / "dash")
      q.join()
    self.assertEqual([r.row for r in done], [DEMO, "night"])
    self.assertTrue(all(r.dashboard and r.dashboard.exists() for r in done))

  def test_queue_stop_drops_the_rest(self):
    os.environ["FAKE_DELAY"] = "0.05"
    done, started = [], threading.Event()
    q = en.RenderQueue(self.eng, lambda e: started.set() if e["stage"] == "still" else None, done.append)
    with contextlib.redirect_stdout(io.StringIO()):
      for i in range(3):
        q.add({**self.row, "Row ID": f"r{i}", "Speed km/h": 80 + 10 * i}, self.ad, self.dir / "dash")
      self.assertTrue(started.wait(30))
      q.stop()
      q.join()
    self.assertEqual(len(done), 1)
    self.assertEqual(done[0].error, "stopped before the picture was finished")

  def test_fingerprint_compare(self):
    a = {"s": {"events": [[0.0, "fault"]], "ego": [[1.0, 2.0, 0.1]], "contact": None}}
    self.assertEqual(pf.differences(a, a), [])
    near = {"s": {"events": [[0.0, "fault"]], "ego": [[1.0 + 5e-7, 2.0, 0.1]], "contact": None}}
    self.assertEqual(pf.differences(a, near), [])
    far = {"s": {"events": [[0.0, "fault"]], "ego": [[1.001, 2.0, 0.1]], "contact": None}}
    self.assertEqual(len(pf.differences(a, far)), 1)
    self.assertEqual(len(pf.differences(a, {"s": {**a["s"], "events": [[0.0, "siren"]]}})), 1)
    self.assertEqual(len(pf.differences(a, {"s": {**a["s"], "contact": {"t": 1.0}}})), 1)


if __name__ == "__main__":
  unittest.main()
