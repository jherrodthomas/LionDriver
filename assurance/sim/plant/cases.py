"""Fault cases of the plant model, each traced to the FMEA rows it exercises, the WP-V-05 case it previews and the
WP-S-04 timing it is compared with. The fault list is the backlog's (simulation track, item 1)."""

from __future__ import annotations

from simulate import Case

T_CURVE = 7.0   # s: fault onset in the steady part of the curve

LATERAL = [
  Case("F-01a", "Torque above the envelope limit (3000 > 1500)", "overlimit", "curve", "SG-01",
       "SFM-002, SFM-029, SWF-001", "VS-FI-14", t_fault=T_CURVE, figure=False,
       note="a host build that skips the host limits; every frame is refused"),
  Case("F-01b", "Hard-over within the envelope (torque ramped at 15/frame to 1500)", "hardover", "straight", "SG-01",
       "SFM-002, SWF-042", "VS-FI-14, VS-FI-27", t_fault=6.0, figure=True,
       note="wrong but limited command: the envelope passes it"),
  Case("F-02", "Torque request while not engaged", "not_engaged", "straight", "SG-01",
       "SFM-001, SWF-002, SWF-041", "VS-FI-14", t_fault=6.0, engaged=False),
  Case("F-03", "Command frozen at curve entry (heartbeat alive)", "frozen", "curve", "SG-01, SG-02",
       "SFM-006, SWF-043, SWF-020", "VS-FI-08", t_fault=None, figure=True,
       note="the frozen frame keeps its counter and checksum; nothing in the envelope checks content freshness"),
  Case("F-04a", "SoC heartbeat loss, commands continue", "heartbeat", "curve", "SG-01, SG-02",
       "SWF-014, SWF-021", "VS-FI-10(a)", t_fault=T_CURVE, figure=True),
  Case("F-04b", "SoC stall: heartbeat and commands stop", "soc_stall", "curve", "SG-01, SG-02",
       "SWF-014, SWF-024, SWF-027", "VS-FI-09", t_fault=T_CURVE),
  Case("F-05", "MCU hang (all execution stops) until the IWDG reset", "mcu_hang", "curve", "SG-01, SG-07",
       "DFM-004, DFM-006, SWF-018", "VS-FI-17", t_fault=T_CURVE, figure=True),
  Case("F-06a", "Harness switch drops to pass-through while driven", "switch_pass", "curve", "SG-01, SG-07",
       "DFM-011, SFM-034", "VS-FI-21", t_fault=T_CURVE,
       note="DG419LE switches with pull-down default to pass-through, no state feedback (RR-2026-010)"),
  Case("F-06b", "Harness switch stuck in intercept, revealed by an MCU hang and reset", "mcu_hang_stuck_intercept",
       "curve", "SG-01, SG-07", "DFM-010, SFM-034, DFM-004", "VS-FI-21, VS-FI-17", t_fault=T_CURVE,
       note="after the reset the stock camera frames do not reach the car; nothing reports the switch position"),
  Case("F-07", "EPS fault (LKA_STATE 9) with loss of EPS assist", "eps_fault", "curve", "SG-02",
       "SFM-005", "VS-FI-31", t_fault=T_CURVE, figure=True),
  Case("F-08", "RX loss: STEER_TORQUE_SENSOR (0x260) stops", "rx_loss", "curve", "SG-01",
       "SWF-006", "VS-FI-04", t_fault=T_CURVE),
]

# faults whose reaction is a loss of STEERING_LKA frames at the EPS: run again with the EPS-hold assumption
FRAME_LOSS = {"F-01a", "F-04a", "F-04b", "F-05", "F-06b", "F-08"}

LONGITUDINAL = [
  Case("L-01", "Acceleration request at the envelope maximum (+2.0 m/s²)", "accel_max", "straight", "SG-03",
       "SFM-008, SWF-046", "VS-FI-14", t_fault=6.0, longitudinal=True),
  Case("L-02", "Acceleration request above the envelope (+4.0 m/s²)", "accel_overlimit", "straight", "SG-03",
       "SFM-008, SFM-029, SWF-003", "VS-FI-14", t_fault=6.0, longitudinal=True),
  Case("L-03", "Deceleration request at the envelope minimum (-3.5 m/s², step)", "decel_min", "straight", "SG-04",
       "SFM-009, SWF-004", "VS-FI-14", t_fault=6.0, longitudinal=True),
  Case("L-04", "Deceleration request above the envelope (-6.0 m/s²)", "decel_overlimit", "straight", "SG-04",
       "SFM-009, SFM-029, SWF-003", "VS-FI-14", t_fault=6.0, longitudinal=True),
]

NOMINAL = [
  Case("N-1", "No fault, straight", "none", "straight", "—", "—", t_fault=6.0, duration=4.0),
  Case("N-2", "No fault, curve inside the ODD (1.5 m/s²)", "none", "curve", "—", "—", t_fault=None, duration=6.0),
  Case("N-3", "No fault, curve at the ODD bound R_ODD (2.5 m/s²)", "none", "curve-odd-bound", "SG-02", "SFM-004",
       t_fault=None, duration=6.0, note="observation for WP-C-02 OI-2: the curve needs more than LAT_ACCEL_FACTOR"),
]


def all_cases() -> list[Case]:
  out = list(NOMINAL)
  for c in LATERAL:
    out.append(c)
    if c.id in FRAME_LOSS:
      out.append(Case(**{**c.__dict__, "id": c.id + "-H", "eps": "hold", "figure": False}))
  return out + LONGITUDINAL
