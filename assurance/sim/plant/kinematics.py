"""WP-S-04 §3.1 kinematic estimates, restated so that simulated times can be set beside them.

Lateral deviation from rest under a lateral acceleration error that is (i) a step, or (iii) a linear ramp to a_y over
1.0 s (the envelope torque rate limit). test_plant.py checks these against the §3.1 table.
"""

from __future__ import annotations

import math


def t_step(d: float, a: float) -> float:
  return math.sqrt(2.0 * d / a)


def t_ramp(d: float, a: float, ramp: float = 1.0) -> float:
  # y(t) = a t^3 / (6 T) for t <= T; afterwards constant a
  y_t = a * ramp ** 2 / 6.0
  if d <= y_t:
    return (6.0 * ramp * d / a) ** (1.0 / 3.0)
  v_t = a * ramp / 2.0
  # d - y_t = v_t tau + a tau^2 / 2
  tau = (-v_t + math.sqrt(v_t ** 2 + 2.0 * a * (d - y_t))) / a
  return ramp + tau


def gap_loss(a: float, t: float) -> float:
  """WP-S-04 §3.3: gap closure with an acceleration error a relative to a lead at constant speed."""
  return 0.5 * a * t * t
