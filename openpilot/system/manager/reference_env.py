"""LionDriver: test-only environment switches have no effect in the reference build on the device (SW FMEA SWF-028.C2,
SWF-030.C2, SWF-058.C2, SWF-082.C1; SWF-ACT-028, -031, -057, -070; as DQ-131 A leaves the debug modes out).

Each switch below is read from the environment by a process manager starts, and each one bypasses a check or fakes an
input: REPLAY sets selfdrived enabled when the panda allows controls, SIMULATION and TESTING_CLOSET relax the input
checks, FINGERPRINT overrides the car identification, BLOCK keeps a process from starting without an event,
BOARDD_SKIP_FW_CHECK skips the panda firmware check, STARTED spoofs ignition, FAKESEND drops TX, SPI_ERR_PROB corrupts
SPI transfers and BOARDD_LOOPBACK switches the panda to loopback. manager removes them from its own environment before
it starts any process, so no process it starts sees them, and logs what it removed.

PC builds keep them: the simulator, process replay and the tests run on a PC and need them. A process started by hand
from a shell bypasses manager, which is a cybersecurity matter (shell access), not this guard's.
"""
from collections.abc import MutableMapping

TEST_SWITCHES = ("REPLAY", "SIMULATION", "TESTING_CLOSET", "FINGERPRINT", "BLOCK", "BOARDD_SKIP_FW_CHECK", "STARTED",
                 "FAKESEND", "SPI_ERR_PROB", "BOARDD_LOOPBACK")


def remove_test_switches(environ: MutableMapping[str, str], reference_build: bool, on_device: bool) -> list[str]:
  """Removes the test-only switches from environ in a reference build on the device; returns the names removed."""
  if not (reference_build and on_device):
    return []
  removed = [name for name in TEST_SWITCHES if name in environ]
  for name in removed:
    del environ[name]
  return removed
