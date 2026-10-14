"""
CA-004 study prototype: emergency-only braking authority beyond ACCEL_MIN (option b).

Study artifact only. It is not wired into openpilot and changes no product limits.
It exists to quantify option (b) in the CA-004 braking-authority study.

Trigger: a lead is confirmed by vision and radar together (fused), the model is
confident, and stopping behind it needs more than the normal braking authority.
Once triggered, braking ramps at a jerk limit to the emergency deceleration and holds
until the ego no longer closes on the lead.
"""
from dataclasses import dataclass

from openpilot.common.realtime import DT_MDL
from openpilot.selfdrive.test.stopped_vehicle.scenarios import BRAKE_LIMIT

# gap to keep at standstill when computing the required deceleration
STOP_MARGIN = 2.


@dataclass
class EmergencyBrakeConfig:
  decel: float = 8.  # m/s^2, emergency deceleration
  jerk: float = 20.  # m/s^3, ramp rate to the emergency deceleration
  min_model_prob: float = 0.9
  require_radar: bool = True


class EmergencyBrake:
  def __init__(self, config: EmergencyBrakeConfig):
    self.config = config
    self.active = False
    self.accel = 0.
    self.triggered = False

  def required_decel(self, lead, v_ego: float) -> float:
    closing = v_ego - lead.vLeadK
    if closing <= 0.:
      return 0.
    return closing ** 2 / (2 * max(lead.dRel - STOP_MARGIN, 0.1))

  def update(self, lead, v_ego: float, a_planner: float) -> float | None:
    """Emergency acceleration command, or None when inactive. Ramps on from the planner's command."""
    cfg = self.config
    fused = lead.present and lead.modelProb >= cfg.min_model_prob and (lead.radar or not cfg.require_radar)

    if not self.active and fused and self.required_decel(lead, v_ego) > BRAKE_LIMIT:
      self.active = self.triggered = True
      self.accel = min(a_planner, 0.)
    elif self.active and (not lead.present or v_ego <= lead.vLeadK or v_ego < 0.1):
      self.active = False

    if not self.active:
      return None
    self.accel = max(-cfg.decel, self.accel - cfg.jerk * DT_MDL)
    return self.accel
