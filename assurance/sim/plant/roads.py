"""Highway roads of the plant model (ODD-H, WP-C-02 §3.1-3.2): a straight, then optionally a clothoid into a
constant-radius arc to the left. One lane is modelled; its centre line is the reference line.

The road is a sampled centre line (x, y, heading, curvature against arc length s), so the same description can be
written out as OpenDRIVE (backlog item 2) and read back here.
"""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass, field


@dataclass
class Road:
  name: str
  lane_width: float
  straight: float                 # m before the clothoid starts
  radius: float | None = None     # m, None for a straight road
  clothoid: float = 100.0         # m of linear curvature change into the arc
  length: float = 2000.0
  ds: float = 0.5
  s: list[float] = field(default_factory=list, repr=False)
  x: list[float] = field(default_factory=list, repr=False)
  y: list[float] = field(default_factory=list, repr=False)
  h: list[float] = field(default_factory=list, repr=False)

  def __post_init__(self):
    n = int(self.length / self.ds) + 1
    x = y = h = 0.0
    for i in range(n):
      s = i * self.ds
      self.s.append(s)
      self.x.append(x)
      self.y.append(y)
      self.h.append(h)
      k0, k1 = self.curvature(s), self.curvature(s + self.ds)
      hm = h + 0.5 * self.ds * (0.5 * (k0 + k1))
      x += self.ds * math.cos(hm)
      y += self.ds * math.sin(hm)
      h += self.ds * 0.5 * (k0 + k1)
    self._hint = 0

  @property
  def curve_start(self) -> float:
    return self.straight

  def curvature(self, s: float) -> float:
    if self.radius is None or s <= self.straight:
      return 0.0
    k = 1.0 / self.radius
    if s >= self.straight + self.clothoid:
      return k
    return k * (s - self.straight) / self.clothoid

  def project(self, px: float, py: float) -> tuple[float, float, float]:
    """(s, lateral offset to the left of the centre line, road heading) of a point near the road."""
    i = self._hint
    best = None
    lo, hi = max(0, i - 8), min(len(self.s) - 1, i + 24)
    for j in range(lo, hi):
      d = (px - self.x[j]) ** 2 + (py - self.y[j]) ** 2
      if best is None or d < best[0]:
        best = (d, j)
    j = best[1]
    self._hint = j
    hj = self.h[j]
    dx, dy = px - self.x[j], py - self.y[j]
    along = dx * math.cos(hj) + dy * math.sin(hj)
    lat = -dx * math.sin(hj) + dy * math.cos(hj)
    s = self.s[j] + along
    return s, lat, hj + along * self.curvature(self.s[j])

  def reset(self, s: float = 0.0):
    self._hint = int(s / self.ds)

  def point(self, s: float) -> tuple[float, float, float]:
    j = min(max(bisect.bisect_left(self.s, s), 0), len(self.s) - 1)
    return self.x[j], self.y[j], self.h[j]


def lane_line_threshold(lane_width: float, car_width: float) -> float:
  """Lateral offset at which the body edge reaches the lane line: (lane width - vehicle width) / 2 (WP-S-04 §3.1)."""
  return (lane_width - car_width) / 2.0
