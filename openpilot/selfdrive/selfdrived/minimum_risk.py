"""LionDriver minimum-risk maneuver after an unresponsive driver (TSR-633; register DQ-365, option A).

When the driver has not responded for 5 s at the terminal driver-monitoring alert, the DM policy requests a forced
deceleration (`driverMonitoringState.noResponseForceDecel`). The item then keeps the lane, slows to a standstill in it
and must stay stopped and held, with the alert sounding, until the driver takes over: it must not drive off again.

The DM request alone does not guarantee that: it is recomputed every DM frame, so a restart of dmonitoringd or a reset
of its awareness would drop it, and the planner would go back to the set speed (on the reference Corolla the PCM
resumes from standstill on its own). This latch holds the maneuver from the first request until the item disengages,
which is the driver's response (brake or cancel). While it is set, controlsd keeps the forced deceleration on, so the
planner keeps the car stopped and the car controller keeps requesting standstill hold, and selfdrived keeps the
terminal alert sounding.
"""


class MinimumRiskManeuver:
  def __init__(self):
    self.active = False

  def update(self, enabled: bool, no_response_decel: bool) -> bool:
    """enabled: the item is engaged after this frame's state transition; no_response_decel: the DM policy's request."""
    if not enabled:
      self.active = False
    elif no_response_decel:
      self.active = True
    return self.active
