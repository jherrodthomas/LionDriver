"""LionDriver: in the reference build on the device, manager removes the test-only environment switches before it starts
any process (reference_env.py; SW FMEA SWF-028.C2, SWF-030.C2)."""
import inspect
import re
import unittest
from pathlib import Path

from openpilot.common.basedir import BASEDIR
from openpilot.system.manager import manager
from openpilot.system.manager.reference_env import TEST_SWITCHES, remove_test_switches


class TestRemoveTestSwitches(unittest.TestCase):
  def env(self):
    return dict.fromkeys(TEST_SWITCHES, "1") | {"HOME": "/data", "PYTHONPATH": "/data/openpilot"}

  def test_reference_build_on_device_removes_every_switch(self):
    environ = self.env()
    removed = remove_test_switches(environ, reference_build=True, on_device=True)
    self.assertEqual(sorted(removed), sorted(TEST_SWITCHES))
    self.assertEqual(environ, {"HOME": "/data", "PYTHONPATH": "/data/openpilot"})   # other variables kept

  def test_each_switch_alone(self):
    for name in TEST_SWITCHES:
      environ = {name: ""}                          # set but empty still counts: the readers test for presence
      self.assertEqual(remove_test_switches(environ, True, True), [name])
      self.assertEqual(environ, {})

  def test_pc_and_upstream_builds_keep_them(self):
    # the simulator, process replay and the tests run on a PC; a non-reference build keeps the upstream behavior
    for reference_build, on_device in ((True, False), (False, True), (False, False)):
      environ = self.env()
      self.assertEqual(remove_test_switches(environ, reference_build, on_device), [])
      self.assertEqual(environ, self.env())

  def test_nothing_to_remove(self):
    environ = {"HOME": "/data"}
    self.assertEqual(remove_test_switches(environ, True, True), [])


class TestManagerUsesIt(unittest.TestCase):
  def test_removed_before_any_switch_is_read_or_process_started(self):
    src = inspect.getsource(manager.manager_thread)
    guard = src.index("remove_test_switches(os.environ, REFERENCE_BUILD, not PC)")
    self.assertLess(guard, src.index('os.getenv("BLOCK"'))
    self.assertLess(guard, src.index("ensure_running("))
    self.assertNotIn("ensure_running(", inspect.getsource(manager.manager_init))   # nothing starts before manager_thread

  def test_every_switch_is_still_read_somewhere(self):
    # a switch no process reads any more is dead weight in the list; one missing from the list is the risk this
    # test cannot see, so the list is reviewed with each new getenv in the safety processes
    sources = ""
    for pattern in ("openpilot/selfdrive/**/*.py", "openpilot/selfdrive/**/*.cc", "openpilot/system/**/*.py",
                    "openpilot/cereal/**/*.py", "opendbc_repo/opendbc/car/*.py"):
      for p in Path(BASEDIR).glob(pattern):
        if "/test" not in str(p) and p.name != "reference_env.py":
          sources += p.read_text(errors="ignore")
    for name in TEST_SWITCHES:
      self.assertTrue(re.search(rf"""["']{name}["']""", sources), name)


if __name__ == "__main__":
  unittest.main()
