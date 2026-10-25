"""openpilot's road-camera auto exposure, ported line by line from camerad, for the tunnel and headlight studies.

Source: `openpilot/system/camerad/cameras/camera_qcom2.cc` (`CameraState::set_camera_exposure`, `get_gain_factor`),
`cameras/camera_common.cc` (`calculate_exposure_value`: the median luminance of the exposure rectangle) and
`sensors/ox03c10.cc` (the comma 3X's road sensor: exposure and gain limits, the gain table, the exposure score, the
gamma curve). Every constant is read from those files here, and `code()` fails if a line the port relies on has
changed, so the port cannot silently drift from the code.

The port runs the controller once per frame (20 Hz). The image a frame measures was exposed with the setting
chosen three frames before (the code's comment: one frame already started, two of register buffering).
Synthetic (DSR-12), design aid, no evidence credit.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
CAMERAD = ROOT / "openpilot" / "system" / "camerad"
QCOM2 = CAMERAD / "cameras" / "camera_qcom2.cc"
OX03C10 = CAMERAD / "sensors" / "ox03c10.cc"


def _num(pattern: str, text: str) -> float:
  m = re.search(pattern, text)
  if not m:
    raise SystemExit(f"camerad changed: no match for {pattern!r}; review the port in camera_ae.py")
  return float(m.group(1))


def code() -> dict:
  """The controller's and the sensor's constants, read from the camerad sources."""
  q = QCOM2.read_text(encoding="utf-8")
  s = OX03C10.read_text(encoding="utf-8")
  # the lines of the loop the port follows; a change in any of them stops the study
  for line in (r"float new_target_grey = std::clamp\(0\.4 - 0\.3 \* log2\(1\.0 \+ sensor->target_grey_factor\*cur_ev_\) "
               r"/ log2\(6000\.0\), target_grey_minimums\[camera\.cc\.camera_num\], 0\.4\);",
               r"float target_grey = \(1\.0 - k_grey\) \* target_grey_fraction \+ k_grey \* new_target_grey;",
               r"float desired_ev = std::clamp\(cur_ev_ / sensor->ev_scale \* target_grey / grey_frac, sensor->min_ev, sensor->max_ev\);",
               r"float k = \(1\.0 - k_ev\) / 3\.0;",
               r"desired_ev = \(k \* cur_ev\[0\]\) \+ \(k \* cur_ev\[1\]\) \+ \(k \* cur_ev\[2\]\) \+ \(k_ev \* desired_ev\);",
               r"int min_g = std::max\(gain_idx - 1, sensor->analog_gain_min_idx\);",
               r"int max_g = std::min\(gain_idx \+ 1, sensor->analog_gain_max_idx\);",
               r"int t = std::clamp\(int\(std::round\(desired_ev / gain\)\), sensor->exposure_time_min, sensor->exposure_time_max\);",
               r"if \(g < sensor->analog_gain_rec_idx && t > 20 && g < gain_idx\) \{",
               r"const float cur_ev_ = cur_ev\[\(camera\.buf\.cur_frame_data\.frame_id - 1\) % 3\] \* sensor->ev_scale;",
               r"cur_ev\[camera\.buf\.cur_frame_data\.frame_id % 3\] = exposure_time \* gain;"):
    if not re.search(line, q):
      raise SystemExit(f"camerad changed: {line!r} not found in camera_qcom2.cc; review the port in camera_ae.py")
  for line in (r"float score = std::abs\(desired_ev - \(exp_t \* exp_gain\)\);",
               r"float m = exp_g_idx > analog_gain_rec_idx \? analog_gain_cost_high : analog_gain_cost_low;",
               r"score \+= std::abs\(exp_g_idx - \(int\)analog_gain_rec_idx\) \* m;",
               r"fx = -0\.507089\*exp\(-12\.54124638\*fx\) \+ 0\.9655\*pow\(fx, 0\.5\) - 0\.472597\*fx \+ 0\.507089;"):
    if not re.search(line, s):
      raise SystemExit(f"camerad changed: {line!r} not found in ox03c10.cc; review the port in camera_ae.py")
  gains = [float(x) for x in re.search(r"sensor_analog_gains_OX03C10\[\] = \{(.*?)\};", s, re.S).group(1).replace("\n", " ").split(",") if x.strip()]
  c = {
    "dt": _num(r"const float dt = ([\d.]+);", q),
    "ts_grey": _num(r"const float ts_grey = ([\d.]+);", q),
    "ts_ev": _num(r"const float ts_ev = ([\d.]+);", q),
    "grey_min_road": float(re.search(r"target_grey_minimums = \{([\d.]+), ([\d.]+), ([\d.]+)\}", q).group(2)),
    "target_grey_init": _num(r"float target_grey_fraction = ([\d.]+);", q),
    "exposure_time_init": _num(r"int exposure_time = (\d+);", q),
    "dc_gain_factor": _num(r"dc_gain_factor = ([\d.]+);", s),
    "dc_gain_min_weight": _num(r"dc_gain_min_weight = (\d+);", s),
    "dc_gain_max_weight": _num(r"dc_gain_max_weight = (\d+);", s),
    "exposure_time_min": _num(r"exposure_time_min = (\d+);", s),
    "exposure_time_max": _num(r"exposure_time_max = (\d+);", s),
    "vs_time_min": _num(r"VS_TIME_MIN_OX03C10 = (\d+);", s),
    "gain_min_idx": int(_num(r"analog_gain_min_idx = 0x([\dA-Fa-f]+);".replace(r"([\dA-Fa-f]+)", r"(\d+)"), s)),
    "gain_rec_idx": int(_num(r"analog_gain_rec_idx = 0x(\d+);", s)),
    "gain_max_idx": int(re.search(r"analog_gain_max_idx = 0x([\dA-Fa-f]+);", s).group(1), 16),
    "cost_delta": _num(r"analog_gain_cost_delta = (-?[\d.]+);", s),
    "cost_low": _num(r"analog_gain_cost_low = ([\d.]+);", s),
    "cost_high": _num(r"analog_gain_cost_high = ([\d.]+);", s),
    "target_grey_factor": _num(r"target_grey_factor = ([\d.]+);", s),
    "fps": _num(r"\.fps = (\d+),", (CAMERAD / "cameras" / "spectra.cc").read_text(encoding="utf-8")),
    "gains": gains,
  }
  c["gain_factor"] = 1 + c["dc_gain_min_weight"] * (c["dc_gain_factor"] - 1) / c["dc_gain_max_weight"]
  c["min_ev"] = (c["exposure_time_min"] + c["vs_time_min"]) * gains[c["gain_min_idx"]]
  c["max_ev"] = c["exposure_time_max"] * c["dc_gain_factor"] * gains[c["gain_max_idx"]]
  return c


def gamma(x):
  """The OX03C10 gamma curve of ox03c10.cc, from linear signal (0..1) to output (0..1)."""
  x = np.clip(np.asarray(x, float), 0.0, 1.0)
  return -0.507089 * np.exp(-12.54124638 * x) + 0.9655 * np.sqrt(x) - 0.472597 * x + 0.507089


def gamma_inv(y: float) -> float:
  lo, hi = 0.0, 1.0
  for _ in range(80):
    mid = (lo + hi) / 2
    lo, hi = (mid, hi) if gamma(mid) < y else (lo, mid)
  return (lo + hi) / 2


class AutoExposure:
  """set_camera_exposure for the road camera (camera_num 1), with the OX03C10 sensor."""

  def __init__(self, c: dict):
    self.c = c
    self.exposure_time = int(c["exposure_time_init"])
    self.gain_idx = c["gain_rec_idx"]
    ev0 = c["gain_factor"] * c["gains"][self.gain_idx] * self.exposure_time
    self.cur_ev = [ev0, ev0, ev0]
    self.target_grey_fraction = c["target_grey_init"]
    self.frame_id = 0

  def score(self, desired_ev, exp_t, exp_g_idx, exp_gain):
    c = self.c
    s = abs(desired_ev - exp_t * exp_gain)
    m = c["cost_high"] if exp_g_idx > c["gain_rec_idx"] else c["cost_low"]
    s += abs(exp_g_idx - c["gain_rec_idx"]) * m
    s += ((1 - c["cost_delta"]) + c["cost_delta"] * (exp_g_idx - c["gain_min_idx"]) / (c["gain_max_idx"] - c["gain_min_idx"])) \
      * abs(exp_g_idx - self.gain_idx) * 5.0
    return s

  def step(self, grey_frac: float) -> dict:
    """One frame: the measured grey fraction in, the new exposure out (ev = exposure time x gain)."""
    c = self.c
    k_grey = (c["dt"] / c["ts_grey"]) / (1.0 + c["dt"] / c["ts_grey"])
    k_ev = (c["dt"] / c["ts_ev"]) / (1.0 + c["dt"] / c["ts_ev"])
    cur_ev_ = self.cur_ev[(self.frame_id - 1) % 3]          # ev_scale is 1.0 for the OX03C10
    new_target = min(max(0.4 - 0.3 * math.log2(1.0 + c["target_grey_factor"] * cur_ev_) / math.log2(6000.0),
                         c["grey_min_road"]), 0.4)
    target_grey = (1.0 - k_grey) * self.target_grey_fraction + k_grey * new_target
    desired_ev = min(max(cur_ev_ * target_grey / max(grey_frac, 1e-9), c["min_ev"]), c["max_ev"])
    k = (1.0 - k_ev) / 3.0
    desired_ev = k * self.cur_ev[0] + k * self.cur_ev[1] + k * self.cur_ev[2] + k_ev * desired_ev
    best, new_g, new_t = 1e6, 0, 0
    for g in range(max(self.gain_idx - 1, c["gain_min_idx"]), min(self.gain_idx + 1, c["gain_max_idx"]) + 1):
      gain = c["gains"][g] * c["gain_factor"]
      t = int(min(max(round(desired_ev / gain), c["exposure_time_min"]), c["exposure_time_max"]))
      if g < c["gain_rec_idx"] and t > 20 and g < self.gain_idx:
        continue
      sc = self.score(desired_ev, t, g, gain)
      if sc < best:
        best, new_g, new_t = sc, g, t
    self.target_grey_fraction = target_grey
    self.gain_idx, self.exposure_time = new_g, new_t
    ev = self.exposure_time * c["gains"][new_g] * c["gain_factor"]
    self.cur_ev[self.frame_id % 3] = ev
    self.frame_id += 1
    return {"ev": ev, "target": target_grey, "desired": desired_ev}


def run(c: dict, luminance: np.ndarray, scale: float, ev_start: float | None = None, warm: int = 1200) -> dict:
  """Drive the loop with the median scene luminance of each frame (cd/m²). The image of a frame is exposed with the
  ev chosen three frames earlier; its grey fraction is the gamma curve of luminance x ev / scale. warm: frames on the
  first luminance before the trace starts (60 s: the target grey settles with a 10 s time constant)."""
  ae = AutoExposure(c)
  if ev_start is not None:
    t = max(int(round(ev_start / c["gain_factor"])), int(c["exposure_time_min"]))
    ae.exposure_time = t
    ae.cur_ev = [t * c["gain_factor"]] * 3
  applied = list(ae.cur_ev)                    # ev of the frames already in flight
  out = {"grey": [], "ev": [], "target": []}
  lum = np.concatenate([np.full(warm, luminance[0]), luminance])
  for i, L in enumerate(lum):
    ev_img = applied[-3]
    grey = float(gamma(L * ev_img / scale))
    r = ae.step(grey)
    applied.append(r["ev"])
    if i >= warm:
      out["grey"].append(grey); out["ev"].append(ev_img); out["target"].append(r["target"])
  return {k: np.array(v) for k, v in out.items()}
