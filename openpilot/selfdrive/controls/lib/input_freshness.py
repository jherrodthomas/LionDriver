"""LionDriver (TSR-602): staleness of controlsd inputs. Pure logic, unit-tested in tests/test_input_freshness.py.

selfdriveState drives the controlsd loop, so it is judged on the wall clock (SubMaster.alive, 10 nominal periods). Every
other input is compared with selfdriveState on the log clock (logMonoTime), so a process replay gives the same answer as the
drive, however fast it runs. An input not received yet is left to selfdrived's engagement checks.
"""

STALE_PERIODS = 10.  # same margin as SubMaster.alive


def inputs_fresh(services, seen, alive, log_mono_time, frequency, reference='selfdriveState') -> bool:
  ref_time = log_mono_time[reference]
  for s in services:
    if not seen[s]:
      continue
    if s == reference:
      if not alive[s]:
        return False
    elif ref_time - log_mono_time[s] > STALE_PERIODS * 1e9 / frequency[s]:
      return False
  return True
