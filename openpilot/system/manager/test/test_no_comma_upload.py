"""LionDriver DQ-121: the manager never starts the comma uploader or athena, whatever the registration or settings."""
from typing import cast

from opendbc.car.structs import car
from openpilot.common.params import Params
from openpilot.system.manager.process_config import managed_processes

COMMA_LINK = ("uploader", "manage_athenad")


class FakeParams:
  def get_bool(self, key):
    return True

  def get(self, key):
    return None


def test_comma_link_processes_disabled():
  for name in COMMA_LINK:
    assert not managed_processes[name].enabled, name


def test_comma_link_processes_never_selected():
  # ensure_running starts a process only if it is enabled and should_run; check both onroad and offroad
  CP = car.CarParams()
  for started in (False, True):
    for name in COMMA_LINK:
      p = managed_processes[name]
      assert not (p.enabled and p.should_run(started, cast(Params, FakeParams()), CP)), (name, started)
