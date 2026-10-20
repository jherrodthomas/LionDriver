#!/usr/bin/env python3
"""Draw the figures of docs/liondriver/driving-and-planning.md (pipeline, two control paths, authority funnel,
model output overlay, timing strip,
steering controller, emergency reactions).

Sources of record:
  - Figure 1, the camera-to-CAN pipeline: the process boxes are drawn here, and each box lists the functional
    modifications of WP-C-07 (FM-nn) whose "Affected code" cell names one of the box's files. The FM numbers and
    priorities come from the WP-C-07 §2 summary. `--check` fails when an FM touches no box, so a new FM that lands
    somewhere the figure does not show cannot be missed.
  - Figure 2, steering and speed paths: the constants are read from the openpilot code (`drive_helpers.py`,
    `longitudinal_planner.py`), and the candidate list of the speed arbitration from the code that builds it.
  - Figure 3, the authority funnel: the panda and controller limits come from the WP-C-01 §8 table, parsed by
    `fig_c01_interfaces.envelope` (the parser that draws WP-C-01 Figure 8-1), and the curvature bound from
    `drive_helpers.py`.
  - Figure 4, the model output overlay: a synthetic road-camera view. The sample grids (X_IDXS, T_IDXS), the road
    camera, the camera height and the UI's drawing rules (widths, colours, draw distance) are read from the openpilot
    code, and the steering action's formula from `modeld.py`. The road and the probabilities are illustrative.
  - Figure 6, the steering controller: constants and the structure of LatControlTorque.update are read from
    `latcontrol_torque.py`.
  - Figure 7, emergency and degraded reactions: hand-listed in EMERG_ROWS; each claim's source text is in
    EMERG_SOURCES and `--check` fails when one is gone.
  - Figure 5, the timing strip: the budgets and times are hand-listed in TIMING_ROWS from WP-S-04, WP-S-02 and the
    trace items; each carries the exact text it was read from (TIMING_SOURCES), and `--check` fails when one is gone.

    python3 fig_driving.py            # write the SVGs into docs/assets/liondriver/
    python3 fig_driving.py --check    # fail if an FM is unplaced, a source changed form, or an SVG is stale

Standard library only. Output is deterministic.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "assurance" / "01-management" / "figures"))
sys.path.insert(0, str(REPO / "assurance" / "02-concept" / "figures"))

from figkit import (AMBER, AMBER_BG, CHIP, FAINT, GREY_BG, HAIR, INK, LINE, MONO, MUTED, RED, SAFETY, SAFETY_BG,  # noqa: E402
                    SW, SW_BG, el, fit, header, legend, line, path, pill, plain, rect, section, svg, table, text, text_w)
import fig_c01_interfaces as c01  # noqa: E402

OUT_DIR = REPO / "docs" / "assets" / "liondriver"
WP_C07 = REPO / "assurance" / "02-concept" / "WP-C-07-sotif-functional-modifications.md"
WP_C01 = REPO / "assurance" / "02-concept" / "WP-C-01-item-definition.md"
DRIVE_HELPERS = REPO / "openpilot" / "selfdrive" / "controls" / "lib" / "drive_helpers.py"
LONG_PLANNER = REPO / "openpilot" / "selfdrive" / "controls" / "lib" / "longitudinal_planner.py"
OUTS = {"pipeline": "driving-1-pipeline.svg", "paths": "driving-2-paths.svg", "funnel": "driving-3-funnel.svg",
        "overlay": "driving-4-overlay.svg", "timing": "driving-5-timing.svg", "torque": "driving-6-torque-controller.svg",
        "emergency": "driving-7-emergency.svg"}
REF = "docs/liondriver/driving-and-planning.md"

PRIORITY = {"P1": (RED, "#FFFFFF"), "P2": (AMBER, "#FFFFFF"), "P3": (GREY_BG, MUTED)}


class SourceError(SystemExit):
  pass


# ---------------------------------------------------------------- sources

def fm_rows(md: str) -> dict[str, dict]:
  """WP-C-07: FM -> title, priority (from the §2 summary) and the Affected code cell (from the FM's own section)."""
  head, rows = table(section(md, "## 2. Summary"), "FM")
  out = {}
  for r in rows:
    fm = r[0]
    out[fm] = {"title": plain(r[head.index("Title")]), "priority": r[head.index("Priority")].strip(), "code": ""}
    if out[fm]["priority"] not in PRIORITY:
      raise SourceError(f"WP-C-07 §2: {fm} priority {out[fm]['priority']!r} unknown; update fig_driving.py")
  for fm, cell in re.findall(r"^### (FM-\d+)[^\n]*\n(?:.*\n)*?\| Affected code \| ([^\n]*)\|$", md, re.M):
    if fm in out:
      out[fm]["code"] = cell
  for fm, row in out.items():
    if not row["code"]:
      raise SourceError(f"WP-C-07: {fm} has no Affected code row; update fig_driving.py")
  return out


def constant(src: str, name: str, file: Path) -> str:
  m = re.search(rf"^{name}\s*=\s*([^#\n]+)", src, re.M)
  if not m:
    raise SourceError(f"{file.relative_to(REPO)}: {name} not found; update fig_driving.py")
  return m.group(1).strip()


def code_facts() -> dict:
  dh = DRIVE_HELPERS.read_text(encoding="utf-8")
  lp = LONG_PLANNER.read_text(encoding="utf-8")
  facts = {
    "max_curv": constant(dh, "MAX_CURVATURE", DRIVE_HELPERS),
    "lat_jerk": constant(dh, "MAX_LATERAL_JERK", DRIVE_HELPERS),
    "lat_accel": constant(dh, "MAX_LATERAL_ACCEL_NO_ROLL", DRIVE_HELPERS),
    "cruise_max": constant(lp, "A_CRUISE_MAX_VALS", LONG_PLANNER),
    "cruise_min": constant(lp, "A_CRUISE_MIN", LONG_PLANNER),
  }
  vals = re.findall(r"-?[\d.]+", facts["cruise_max"])
  if len(vals) < 2:
    raise SourceError("longitudinal_planner.py: A_CRUISE_MAX_VALS changed form; update fig_driving.py")
  facts["cruise_hi"], facts["cruise_lo"] = vals[0], vals[-1]
  # The arbitration: MPC and cruise always, the model's own acceleration (e2e) only in Experimental Mode, then min().
  want = [r"candidates = \[\(output_a_target_mpc,", r"\(self\.a_cruise, LongitudinalPlanSource\.cruise",
          r"if sm\['selfdriveState'\]\.experimentalMode:\s*\n\s*candidates\.append\(\(output_a_target_e2e",
          r"= min\(candidates", r"np\.clip\(output_a_target, ACCEL_MIN, ACCEL_MAX\)"]
  for w in want:
    if not re.search(w, lp):
      raise SourceError(f"longitudinal_planner.py: arbitration changed ({w}); update fig_driving.py and the page")
  # The model action is the steering command; lateralManeuverPlan overrides it only when that service is valid.
  ctl = (REPO / "openpilot" / "selfdrive" / "controls" / "controlsd.py").read_text(encoding="utf-8")
  for w in [r"requested_curvature = model_v2\.action\.desiredCurvature", r"self\.inputs_fresh\(LAT_INPUTS\)",
            r"math\.isfinite\(requested_curvature\)"]:
    if not re.search(w, ctl):
      raise SourceError(f"controlsd.py: steering path changed ({w}); update fig_driving.py and the page")
  return facts


# ---------------------------------------------------------------- Figure 1: pipeline

# key: (column, row, title, process, rate, files, kind). Files are matched as whole names in the FM's Affected code
# cell; "NEW" matches a cell that proposes a new component or module.
BOXES = {
  "cam":      (0, 0, "Cameras", "camerad", "20 Hz", [], "sw"),
  "modeld":   (1, 0, "Driving model", "modeld (AI-1)", "20 Hz", ["modeld.py", "fill_model_msg.py", "modeld/helpers.py"], "sw"),
  "monitor":  (2, 0, "New monitor", "proposed", "", ["NEW"], "new"),
  "controlsd": (3, 0, "Controls", "controlsd", "100 Hz", ["controlsd.py"], "sw"),
  "card":     (4, 0, "Car interface", "card + carcontroller", "100 Hz",
               ["car_events.py", "cruise.py", "carcontroller.py", "interface.py", "interfaces.py", "values.py"], "sw"),
  "panda":    (5, 0, "Safety envelope", "panda safety mode", "per frame", ["toyota.h", "lateral.h"], "safety"),
  "car":      (6, 0, "Vehicle", "EPS · PCM", "", [], "car"),
  "radard":   (1, 1, "Lead tracking", "radard", "20 Hz", ["radard.py"], "sw"),
  "plannerd": (2, 1, "Speed planner", "plannerd (MPC)", "20 Hz", ["plannerd.py", "longitudinal_planner.py"], "sw"),
  "params":   (3, 1, "Settings", "params, config", "", ["params_keys.h", "toggles.py", "process_config.py"], "sw"),
  "selfdrived": (4, 1, "State and alerts", "selfdrived", "100 Hz", ["selfdrived.py", "state.py", "events.py"], "sw"),
  "dm":       (5, 1, "Driver monitoring", "dmonitoringd", "20 Hz",
               ["dmonitoringmodeld.py", "dmonitoringd.py", "policy.py", "test_monitoring.py"], "sw"),
}


def file_hits(cell: str, files: list[str]) -> bool:
  if cell.lstrip().lower().startswith("new component"):  # the files it names are its inputs, not changed code
    return "NEW" in files
  for f in files:
    if f == "NEW":
      if re.search(r"\bnew (component|monitor)", cell, re.I):
        return True
    elif re.search(rf"(?<![\w]){re.escape(f)}", cell):
      return True
  return False


def placement(fms: dict[str, dict]) -> dict[str, list[str]]:
  return {k: [fm for fm, r in fms.items() if file_hits(r["code"], b[5])] for k, b in BOXES.items()}


def unplaced(fms: dict[str, dict]) -> list[str]:
  placed = {fm for v in placement(fms).values() for fm in v}
  return [fm for fm in fms if fm not in placed]


def chips(x: float, y: float, w: float, names: list[str], fms: dict[str, dict]) -> tuple[list[str], float]:
  """FM chips wrapped inside width w; returns (svg, height used)."""
  out, cx, cy = [], x, y
  for fm in names:
    fill, color = PRIORITY[fms[fm]["priority"]]
    cw = text_w(fm, 9.5, True) + 12
    if cx + cw > x + w and cx > x:
      cx, cy = x, cy + 20
    p, cw = pill(cx, cy, fm, fill, color=color, stroke=LINE if fill == GREY_BG else "none")
    out += p
    cx += cw + 5
  return out, (cy - y + 16) if names else 0


def build_pipeline(fms: dict[str, dict]) -> str:
  W, X0, BW, GAP = 1320, 40, 140, 47
  ROW_Y = [150, 400]
  place = placement(fms)
  body = header(W, "1", "Camera to CAN: the driving pipeline",
                "Every process talks over openpilot's own publish-subscribe messaging (cereal on msgq), not ROS. "
                "Chips mark where each WP-C-07 modification lands.", "WP-C-07 §2 · LionDriver driving and planning")

  def bx(col: int) -> float:
    return X0 + col * (BW + GAP)

  # Heights: each row as tall as its tallest box.
  heights = {}
  for k, (c, r, *_rest) in BOXES.items():
    _, ch = chips(0, 0, BW - 20, place[k], fms)
    heights[k] = 74 + (ch + 10 if ch else 0)
  row_h = [max(h for k, h in heights.items() if BOXES[k][1] == r) for r in (0, 1)]

  # Bands: the doer (main SoC) and the checker (panda MCU).
  band_top = ROW_Y[0] - 40
  body.append(rect(bx(0) - 12, band_top, bx(5) - bx(0) - 5, ROW_Y[1] + row_h[1] + 22 - band_top, fill=SW_BG,
                   stroke="none", rx=12))
  body.append(text(bx(0), band_top + 20, "DOER · main computer (QM, learned and conventional software)", size=11,
                   fill=SW, weight=700))
  body.append(rect(bx(5) - 7, band_top, BW + 14, ROW_Y[0] + row_h[0] + 22 - band_top, fill=SAFETY_BG, stroke="none",
                   rx=12))
  body.append(text(bx(5), band_top + 20, "CHECKER · panda MCU", size=11, fill=SAFETY, weight=700))

  centers = {}
  for k, (c, r, title, proc, rate, _files, kind) in BOXES.items():
    x, y, h = bx(c), ROW_Y[r], row_h[r]
    stroke = {"sw": SW, "safety": SAFETY, "new": MUTED, "car": INK}[kind]
    fill = {"sw": "#FFFFFF", "safety": "#FFFFFF", "new": CHIP, "car": GREY_BG}[kind]
    body.append(rect(x, y, BW, h, fill=fill, stroke=stroke, sw=1.4, dash="5 4" if kind == "new" else ""))
    body.append(text(x + 10, y + 22, fit(title, BW - 20, 13, True), size=13, weight=700))
    body.append(text(x + 10, y + 40, fit(proc, BW - 20, 10.5), size=10.5, fill=MUTED, family=MONO))
    if rate:
      body.append(text(x + 10, y + 58, rate, size=10.5, fill=stroke if kind != "new" else MUTED, weight=600))
    c_svg, _ = chips(x + 10, y + 70, BW - 20, place[k], fms)
    body += c_svg
    centers[k] = (x, y, h)

  def right(k):
    x, y, h = centers[k]
    return x + BW, y + 36

  def left(k):
    x, y, h = centers[k]
    return x, y + 36

  def arrow(x1, y1, x2, y2, label="", dash="", lx=None, ly=None, anchor="middle", color=MUTED):
    out = [line(x1, y1, x2, y2, stroke=color, sw=1.5, dash=dash)]
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    p1 = (x2 - 8 * math.cos(a - 0.4), y2 - 8 * math.sin(a - 0.4))
    p2 = (x2 - 8 * math.cos(a + 0.4), y2 - 8 * math.sin(a + 0.4))
    out.append(path(f"M{x2:.1f},{y2:.1f} L{p1[0]:.1f},{p1[1]:.1f} L{p2[0]:.1f},{p2[1]:.1f} Z", stroke=color, sw=1,
                    fill=color))
    if label:
      out.append(text(lx if lx is not None else (x1 + x2) / 2, ly if ly is not None else (y1 + y2) / 2 - 6, label,
                      size=9.5, fill=INK, anchor=anchor, family=MONO))
    return out

  # Row 0, left to right.
  labels = {("cam", "modeld"): "frames", ("modeld", "monitor"): "modelV2", ("monitor", "controlsd"): "modelV2",
            ("controlsd", "card"): "carControl", ("card", "panda"): "CAN TX", ("panda", "car"): "0x2E4, 0x343"}
  for (a, b), lab in labels.items():  # labels sit above the row, centred on the gap they name
    (x1, y1), (x2, _) = right(a), left(b)
    body += arrow(x1 + 2, y1, x2 - 2, y1, lab, ly=ROW_Y[0] - 8)
  # Row 1 into row 0.
  mx, my, mh = centers["modeld"]
  rx, ry, _ = centers["radard"]
  px, py, _ = centers["plannerd"]
  body += arrow(mx + BW / 2, my + row_h[0] + 2, rx + BW / 2, ry - 2, "modelV2", lx=mx + BW / 2 + 6,
                ly=(my + row_h[0] + ry) / 2, anchor="start")
  body += arrow(mx + BW - 10, my + row_h[0] + 2, px + 16, py - 2)
  body += arrow(rx + BW + 2, ry + 36, px - 2, ry + 36, "radarState", ly=ry - 8)
  cx, cy, _ = centers["controlsd"]
  body += arrow(px + BW - 20, py - 2, cx + 30, cy + row_h[0] + 2, "longitudinalPlan", lx=px + BW - 2,
                ly=(py + cy + row_h[0]) / 2 + 4, anchor="start")
  sx, sy, _ = centers["selfdrived"]
  body += arrow(sx + 20, sy - 2, cx + BW - 30, cy + row_h[0] + 2, "selfdriveState", lx=sx + 26,
                ly=(sy + cy + row_h[0]) / 2 + 4, anchor="start")
  dx, dy, _ = centers["dm"]
  body += arrow(dx - 2, dy + 36, sx + BW + 2, sy + 36, "driverMonitoringState", ly=dy - 8)
  qx, qy, _ = centers["params"]
  body += arrow(qx + BW + 2, qy + 62, sx - 2, sy + 62, "params", ly=qy + 78)

  # Notes and legend.
  ny = ROW_Y[1] + row_h[1] + 52
  notes = [
    "Steering has no separate path planner: the model's desiredCurvature goes straight to controlsd. "
    "Speed goes through plannerd's MPC. Every limit on what reaches the car is enforced again in the panda.",
    "A box's chips are the WP-C-07 modifications whose Affected code names one of its files. "
    "The dashed box is the new monitor FM-09 proposes (and FM-08's ODD monitor); it does not exist yet.",
  ]
  for i, n in enumerate(notes):
    body.append(text(40, ny + i * 18, n, size=11.5, fill=MUTED))
  lg, _ = legend(40, ny + 50, [(RED, "none", "P1, before on-road use"), (AMBER, "none", "P2, before release"),
                               (GREY_BG, LINE, "P3, decide at G2"), (CHIP, MUTED + " dashed", "proposed component")])
  body += lg
  H = int(ny + 72)
  desc = ("The LionDriver driving pipeline from cameras through the driving model, controls, car interface and the panda "
          "safety envelope to the EPS and PCM, with lead tracking, the speed planner, settings, state and driver monitoring "
          "below. Chips name the WP-C-07 functional modifications that change each process: " +
          "; ".join(f"{k}: {', '.join(v) or 'none'}" for k, v in place.items()) + ".")
  return svg(W, H, "Figure 1. Camera to CAN: the driving pipeline", desc, body)


# ---------------------------------------------------------------- Figure 2: steering and speed paths

def build_paths(f: dict) -> str:
  W = 1320
  body = header(W, "2", "Two paths: steering is direct, speed is planned",
                "What controlsd and plannerd do with the model's output, read from the pinned openpilot code.",
                "controlsd.py · drive_helpers.py · longitudinal_planner.py")

  def stage(x, y, w, h, title, lines_, kind="sw", dash=""):
    stroke = {"sw": SW, "safety": SAFETY, "model": INK, "off": MUTED, "ld": SAFETY}[kind]
    fill = {"sw": "#FFFFFF", "safety": SAFETY_BG, "model": GREY_BG, "off": CHIP, "ld": "#FFFFFF"}[kind]
    out = [rect(x, y, w, h, fill=fill, stroke=stroke, sw=1.4, dash=dash)]
    out.append(text(x + 10, y + 20, title, size=12.5, weight=700, fill=INK if kind != "off" else MUTED))
    for i, s in enumerate(lines_):
      out.append(text(x + 10, y + 38 + i * 15, fit(s, w - 18, 10.5), size=10.5, fill=MUTED))
    return out

  def arrow(x1, y1, x2, y2, color=MUTED, dash=""):
    out = [line(x1, y1, x2 - 6, y2, stroke=color, sw=1.6, dash=dash)]
    out.append(path(f"M{x2},{y2} L{x2 - 8},{y2 - 4.5} L{x2 - 8},{y2 + 4.5} Z", stroke=color, sw=1, fill=color))
    return out

  # Lane labels.
  ly1, ly2 = 120, 330
  body.append(text(40, ly1, "STEERING (lateral)", size=12, weight=700, fill=SW))
  body.append(text(40, ly2, "SPEED (longitudinal)", size=12, weight=700, fill=SW))

  # Steering lane: five stages.
  y, h, w = ly1 + 14, 104, 220
  xs = [40, 290, 540, 790, 1060]
  body += stage(xs[0], y, w, h, "Driving model action", ["action.desiredCurvature", "20 Hz, no lateral smoothing",
                                                         "(plan[33] is for UI and logs)"], "model")
  body += stage(xs[1], y, w, h, "LionDriver input checks", ["inputs fresh (TSR-602)", "curvature finite (SWF-045)",
                                                            "else latActive = False"], "ld")
  body += stage(xs[2], y, w, h, "Curvature clip", [f"|κ| ≤ {f['max_curv']} 1/m", f"|a_lat| ≤ {f['lat_accel']} m/s² + roll",
                                                   f"jerk ≤ {f['lat_jerk']} m/s³"])
  body += stage(xs[3], y, 240, h, "Torque controller", ["latcontrol_torque", "curvature → steer torque",
                                                        "100 Hz"])
  body += stage(xs[4], y, 220, h, "Panda + EPS", ["STEERING_LKA 0x2E4", "torque and rate limits", "(Figure 3)"],
                "safety")
  for a, b, wa in [(0, 1, w), (1, 2, w), (2, 3, w), (3, 4, 240)]:
    body += arrow(xs[a] + wa + 2, y + h / 2, xs[b] - 2, y + h / 2)
  body.append(text(xs[1], y + h + 26, "No planner between the model and the controller: the network's action is the "
                   "steering command. A lane change is a desire pulse from DesireHelper into the model, not a plan.",
                   size=11, fill=MUTED))

  # Speed lane: three candidates into min(), clip, controller, panda.
  cy0, ch, cw = ly2 + 14, 74, 250
  cands = [
    ("MPC (acados)", ["follows leads from radard", "radar + vision"], "sw", ""),
    ("Cruise", [f"toward set speed, a ≥ {f['cruise_min']} m/s²", f"a ≤ {f['cruise_hi']}…{f['cruise_lo']} m/s² by speed"],
     "sw", ""),
    ("Model's own acceleration", ["Experimental Mode only", "off by default (FM-01 a)"], "off", "5 4"),
  ]
  for i, (t, ls, k, d) in enumerate(cands):
    body += stage(40, cy0 + i * (ch + 12), cw, ch, t, ls, k, d)
  mx, my, mw, mh = 360, cy0 + ch + 12 - 6, 150, ch + 12
  body += stage(mx, my, mw, mh, "min()", ["lowest acceleration", "wins"])
  for i in range(3):
    yy = cy0 + i * (ch + 12) + ch / 2
    body += arrow(40 + cw + 2, yy, mx - 2, my + mh / 2, color=MUTED, dash="5 4" if i == 2 else "")
  xs2 = [560, 790, 1060]
  body += stage(xs2[0], my, 200, mh, "Clip and publish", ["ACCEL_MIN … ACCEL_MAX", "longitudinalPlan.aTarget"])
  body += stage(xs2[1], my, 240, mh, "Checks + controller", ["fresh and finite (TSR-602)", "longcontrol, 100 Hz"], "ld")
  body += stage(xs2[2], my, 220, mh, "Panda + PCM", ["ACC_CONTROL 0x343", "accel bounds (Figure 3)"], "safety")
  body += arrow(mx + mw + 2, my + mh / 2, xs2[0] - 2, my + mh / 2)
  body += arrow(xs2[0] + 202, my + mh / 2, xs2[1] - 2, my + mh / 2)
  body += arrow(xs2[1] + 242, my + mh / 2, xs2[2] - 2, my + mh / 2)

  ny = cy0 + 3 * (ch + 12) + 22
  lg, _ = legend(40, ny, [(GREY_BG, INK, "learned model"), ("#FFFFFF", SW, "inherited openpilot code"),
                          ("#FFFFFF", SAFETY, "LionDriver change already in the code"),
                          (SAFETY_BG, SAFETY, "safety envelope"), (CHIP, MUTED + " dashed", "off in the reference build")])
  body += lg
  H = int(ny + 26)
  desc = ("Steering: the driving model's desiredCurvature passes LionDriver's freshness and finiteness checks, a curvature "
          f"clip (|curvature| ≤ {f['max_curv']} per metre, lateral acceleration ≤ {f['lat_accel']} m/s² plus roll, jerk ≤ "
          f"{f['lat_jerk']} m/s³) and the torque controller to the panda and EPS. Speed: the MPC, the cruise target and, in "
          "Experimental Mode only, the model's own acceleration go into min(); the result is clipped, checked and sent "
          "through the panda to the PCM.")
  return svg(W, H, "Figure 2. Two paths: steering is direct, speed is planned", desc, body)


# ---------------------------------------------------------------- Figure 3: authority funnel

def build_funnel(env: dict, f: dict) -> str:
  W = 1320
  body = header(W, "3", "Who limits what reaches the car",
                "Each stage can only narrow what the stage before it asked for. All limits are inherited and not yet "
                "verified.", "WP-C-01 §8 · WP-C-04 §4.2 · WP-C-07 FM-10")
  t, r, la, a = env["torque"], env["rate"], env["lat"], env["accel"]

  def funnel(y0, label, stages):
    out = [text(40, y0, label, size=12, weight=700, fill=SW)]
    n, x, top = len(stages), 40, y0 + 14
    gap, w = 14, (W - 80 - 14 * (len(stages) - 1)) / len(stages)
    hmax, hmin = 150, 92
    for i, (title, ls, kind) in enumerate(stages):
      h = hmax - (hmax - hmin) * i / max(1, n - 1)
      yy = top + (hmax - h) / 2
      stroke = {"model": INK, "sw": SW, "safety": SAFETY, "car": INK, "fm": MUTED}[kind]
      fill = {"model": GREY_BG, "sw": "#FFFFFF", "safety": SAFETY_BG, "car": GREY_BG, "fm": CHIP}[kind]
      out.append(rect(x, yy, w, h, fill=fill, stroke=stroke, sw=1.4, dash="5 4" if kind == "fm" else ""))
      out.append(text(x + 10, yy + 20, fit(title, w - 18, 12.5, True), size=12.5, weight=700))
      for j, s in enumerate(ls):
        out.append(text(x + 10, yy + 38 + j * 15, fit(s, w - 18, 10.5), size=10.5, fill=MUTED))
      if i < n - 1:
        cx = x + w + gap / 2
        out.append(path(f"M{cx - 4},{top + hmax / 2 - 7} L{cx + 4},{top + hmax / 2} L{cx - 4},{top + hmax / 2 + 7}",
                        stroke=MUTED, sw=1.6))
      x += w + gap
    return out, top + hmax

  lat_stages = [
    ("Model asks", ["any curvature", "(a learned output)"], "model"),
    ("controlsd clips", [f"|κ| ≤ {f['max_curv']} 1/m", f"a_lat ≤ {la['accel_s']} m/s² + roll",
                         f"jerk ≤ {la['jerk_s']} m/s³"], "sw"),
    ("Panda allows", [f"torque ≤ {t['max']} raw", f"+{r['up']} / −{r['down']} raw per {r['frame_ms']} ms",
                      f"≤ {r['window']} raw per {r['window_ms']} ms", "only while engaged"], "safety"),
    ("EPS delivers", ["its own limits", f"physical torque: {t['gap']}", "driver can overpower (AOU)"], "car"),
    ("FM-10 would add", ["speed-dependent torque", "limit in the panda", "(proposed, P2)"], "fm"),
  ]
  lon_stages = [
    ("Planner picks", ["min(MPC, cruise", "[, model in Experimental])"], "model"),
    ("plannerd clips", ["ACCEL_MIN … ACCEL_MAX"], "sw"),
    ("Panda allows", [f"{a['min_s']} … {a['max_s']} m/s²", "only while engaged", "gas press blocks it"], "safety"),
    ("PCM delivers", ["its own ACC envelope", "(AOU-05)", "stock AEB kept (AOU-04)"], "car"),
  ]
  b1, y1 = funnel(116, "STEERING", lat_stages)
  b2, y2 = funnel(y1 + 50, "SPEED", lon_stages)
  body += b1 + b2
  ny = y2 + 34
  body.append(text(40, ny, "The panda limits are the safety argument: whatever the main computer computes, nothing "
                   "outside them is sent. Changing the planner does not move them.", size=11.5, fill=MUTED))
  lg, _ = legend(40, ny + 28, [(GREY_BG, INK, "request or vehicle"), ("#FFFFFF", SW, "main computer (QM)"),
                               (SAFETY_BG, SAFETY, "panda safety envelope"), (CHIP, MUTED + " dashed", "proposed")])
  body += lg
  H = int(ny + 50)
  desc = (f"Steering: the model asks for any curvature; controlsd clips it to {f['max_curv']} per metre, "
          f"{la['accel_s']} m/s² and {la['jerk_s']} m/s³; the panda allows at most {t['max']} raw torque, "
          f"+{r['up']}/−{r['down']} raw per {r['frame_ms']} ms and {r['window']} raw per {r['window_ms']} ms; the EPS "
          f"applies its own limits ({t['gap']}). FM-10 proposes a speed-dependent torque limit. Speed: the planner's min() "
          f"is clipped to ACCEL_MIN…ACCEL_MAX, the panda allows {a['min_s']} to {a['max_s']} m/s², and the PCM applies "
          "its own envelope.")
  return svg(W, H, "Figure 3. Who limits what reaches the car", desc, body)


# ---------------------------------------------------------------- Figure 4: model output overlay

OP = REPO / "openpilot"
OVERLAY_SOURCES = {
  "constants": OP / "selfdrive" / "modeld" / "constants.py",
  "camera": OP / "common" / "transformations" / "camera.py",
  "calib": OP / "selfdrive" / "locationd" / "calibrationd.py",
  "ui": OP / "selfdrive" / "ui" / "onroad" / "model_renderer.py",
  "modeld": OP / "selfdrive" / "modeld" / "modeld.py",
  "fill": OP / "selfdrive" / "modeld" / "fill_model_msg.py",
}
# The illustrative scene: a highway curve to the left inside the ODD (1.5 m/s² at 100 km/h, the plant's "curve inside
# the ODD", assurance/sim/plant/simulate.py), ego in the middle of three 3.7 m lanes.
SCENE = {"v_kmh": 100, "a_lat": 1.5, "lane": 3.7, "probs": [0.55, 0.95, 0.95, 0.75], "edge_stds": [0.25, 0.45],
         "left_shoulder": 1.0, "right_shoulder": 3.0}


def overlay_facts() -> dict:
  src = {k: p.read_text(encoding="utf-8") for k, p in OVERLAY_SOURCES.items()}

  def need(key: str, pattern: str, what: str) -> re.Match:
    m = re.search(pattern, src[key], re.M)
    if not m:
      raise SourceError(f"{OVERLAY_SOURCES[key].relative_to(REPO)}: {what} changed form; update fig_driving.py")
    return m

  f = {
    "idx_n": int(need("constants", r"^\s*IDX_N = (\d+)$", "IDX_N").group(1)),
    "t_max": float(need("constants", r"T_IDXS = \[index_function\(idx, max_val=([\d.]+)\)", "T_IDXS").group(1)),
    "x_max": float(need("constants", r"X_IDXS = \[index_function\(idx, max_val=([\d.]+)\)", "X_IDXS").group(1)),
    "height": float(need("calib", r"^HEIGHT_INIT = np\.array\(\[([\d.]+)\]\)", "HEIGHT_INIT").group(1)),
    "max_draw": float(need("ui", r"^MAX_DRAW_DISTANCE = ([\d.]+)", "MAX_DRAW_DISTANCE").group(1)),
    "line_w": float(need("ui", r"lane_line\.raw_points, ([\d.]+) \* self\._lane_line_probs\[i\]", "lane line width").group(1)),
    "edge_w": float(need("ui", r"road_edge\.raw_points, ([\d.]+), 0\.0", "road edge width").group(1)),
    "path_w": float(need("ui", r"self\._path\.raw_points, ([\d.]+), self\._path_offset_z", "path width").group(1)),
    "line_alpha_max": float(need("ui", r"np\.clip\(self\._lane_line_probs\[i\], 0\.0, ([\d.]+)\)", "lane alpha").group(1)),
  }
  need("constants", r"^def index_function\(idx, max_val=192, max_idx=32\):\n\s*return \(max_val\) \* \(\(idx/max_idx\)\*\*2\)",
       "index_function")
  cam = need("camera", r"^_ar_ox_config = DeviceCameraConfig\(CameraConfig\((\d+), (\d+), ([\d.]+)\)", "_ar_ox_config")
  f["cam_w"], f["cam_h"], f["focal"] = int(cam.group(1)), int(cam.group(2)), float(cam.group(3))
  need("modeld", r"desired_curvature = model_output\['action'\]\[0,0\] / \(max\(1\.0, v_ego\)\)\*\*2", "action formula")
  need("modeld", r"if 'action' not in model_output:", "plan fallback")
  need("fill", r"fill_xyzt\(modelV2\.position, ModelConstants\.T_IDXS", "plan on T_IDXS")
  need("fill", r"fill_xyzt\(lane_line, LINE_T_IDXS, np\.array\(ModelConstants\.X_IDXS\)", "lane lines on X_IDXS")
  n = f["idx_n"] - 1
  f["x_idxs"] = [f["x_max"] * (i / n) ** 2 for i in range(f["idx_n"])]
  f["t_idxs"] = [f["t_max"] * (i / n) ** 2 for i in range(f["idx_n"])]
  return f


def build_overlay(f: dict) -> str:
  W, S, WIDEN = 1320, 0.4, 3                          # page width; image scale (camera pixels to figure units);
  #                                                      model strips drawn this many times the UI width to be seen
  IX, IY = 40, 104                                     # image origin
  iw, ih = f["cam_w"] * S, f["cam_h"] * S
  v = SCENE["v_kmh"] / 3.6
  radius = v * v / SCENE["a_lat"]
  curv = SCENE["a_lat"] / max(1.0, v) ** 2
  h, lane = f["height"], SCENE["lane"]
  body = header(W, "4", "What the model draws, and what steers",
                "The road camera with the model's lane lines, road edges and plan drawn the way the onroad UI draws "
                "them. None of it is the steering command.", "WP-C-11 §2.4 · modeld.py · model_renderer.py")

  def proj(x: float, y: float) -> tuple[float, float]:
    """Ground point (x forward, y right, metres) to figure coordinates; level calibration, camera at height h."""
    return IX + S * (f["focal"] * y / x + f["cam_w"] / 2), IY + S * (f["focal"] * h / x + f["cam_h"] / 2)

  def centre(x: float) -> float:
    return -x * x / (2 * radius)                       # curve to the left: y decreases

  def xs(a: float, b: float, n: int = 48) -> list[float]:
    return [a * (b / a) ** (i / (n - 1)) for i in range(n)]

  def strip(d: float, half: float, a: float, b: float) -> str:
    left = [proj(x, centre(x) + d - half) for x in xs(a, b)]
    right = [proj(x, centre(x) + d + half) for x in reversed(xs(a, b))]
    return "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in left + right) + " Z"

  def band(d0: float, d1: float, a: float, b: float) -> str:
    left = [proj(x, centre(x) + d0) for x in xs(a, b)]
    right = [proj(x, centre(x) + d1) for x in reversed(xs(a, b))]
    return "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in left + right) + " Z"

  lines = [-1.5 * lane, -0.5 * lane, 0.5 * lane, 1.5 * lane]
  edges = [lines[0] - SCENE["left_shoulder"], lines[3] + SCENE["right_shoulder"]]
  near, far, horizon = 5.0, 1500.0, IY + ih / 2
  _, path_bottom = proj(near, 0)
  _, path_top = proj(f["max_draw"], 0)
  body.append("<defs>" +
              f'<clipPath id="cam"><rect x="{IX}" y="{IY}" width="{fmt_(iw)}" height="{fmt_(ih)}" rx="8"/></clipPath>' +
              f'<linearGradient id="sky" x1="0" y1="{IY}" x2="0" y2="{fmt_(horizon)}" gradientUnits="userSpaceOnUse">'
              '<stop offset="0" stop-color="#9FB9D3"/><stop offset="1" stop-color="#DCE5EC"/></linearGradient>' +
              f'<linearGradient id="path" x1="0" y1="{fmt_(path_bottom)}" x2="0" y2="{fmt_(path_top)}" '
              'gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#0DF87A" stop-opacity="0.4"/>'
              '<stop offset="0.5" stop-color="#72FF5C" stop-opacity="0.35"/>'
              '<stop offset="1" stop-color="#72FF5C" stop-opacity="0"/></linearGradient></defs>')
  scene = [rect(IX, IY, iw, ih / 2 + 1, fill="url(#sky)", stroke="none", rx=0),
           rect(IX, horizon, iw, ih / 2, fill="#8E9A7C", stroke="none", rx=0),
           path(band(edges[0] - 0.4, edges[1] + 0.4, near, far), stroke="none", fill="#9A9C92"),
           path(band(lines[0] - 0.1, lines[3] + 0.1, near, far), stroke="none", fill="#5E6266")]
  # Painted markings: solid outer lines, 3 m dashes with 9 m gaps between lanes (the road, not the model).
  for d in (lines[0], lines[3]):
    scene.append(path(strip(d, 0.075, near, far), stroke="none", fill="#E9E9E2"))
  for d in (lines[1], lines[2]):
    x = near
    while x < 400:
      scene.append(path(strip(d, 0.075, x, x + 3.0), stroke="none", fill="#E9E9E2"))
      x += 12.0
  # The model's output, drawn with the UI's rules.
  lim = f["max_draw"]
  scene.append(path(strip(0.0, f["path_w"], near, lim), stroke="none", fill="url(#path)"))
  for d, p in zip(lines, SCENE["probs"]):
    a = min(max(p, 0.0), f["line_alpha_max"])
    scene.append(el("path", None, d=strip(d, f["line_w"] * p * WIDEN, near, lim), fill="#FFFFFF", fill_opacity=fmt_(a)))
  for d, sd in zip(edges, SCENE["edge_stds"]):
    scene.append(el("path", None, d=strip(d, f["edge_w"] * WIDEN, near, lim), fill="#FF0000",
                    fill_opacity=fmt_(min(max(1 - sd, 0.0), 1.0))))
  body.append(f'<g clip-path="url(#cam)">' + "".join(scene) + "</g>")
  body.append(rect(IX, IY, iw, ih, fill="none", stroke=INK, sw=1.2))

  # Stamp and callouts.
  sp, sw_ = pill(IX + 14, IY + 14, "FOR DISPLAY, NOT FOR STEERING", INK, size=11, h=22)
  body += sp

  def callout(x_m: float, d: float, tx: float, ty: float, title: str, sub: str, color=INK):
    px, py = proj(x_m, centre(x_m) + d)
    out = [line(px, py, tx, ty + 4, stroke=INK, sw=1), el("circle", None, cx=fmt_(px), cy=fmt_(py), r=3, fill=INK)]
    tw = max(text_w(title, 11.5, True), text_w(sub, 10)) + 16
    bx = tx - tw / 2
    out.append(rect(bx, ty - 30, tw, 36, fill="#FFFFFF", stroke=LINE, rx=6, opacity="0.94"))
    out.append(text(tx, ty - 15, title, size=11.5, weight=700, anchor="middle", fill=color))
    out.append(text(tx, ty - 1, sub, size=10, anchor="middle", fill=MUTED))
    return out

  body += callout(28, lines[1], IX + 150, IY + 96, "laneLines[1]", f"prob {SCENE['probs'][1]}: alpha = prob, max "
                  f"{f['line_alpha_max']}")
  body += callout(45, edges[1], IX + iw - 120, IY + 150, "roadEdges[1]", f"std {SCENE['edge_stds'][1]}: red, alpha = 1 − std",
                  color=RED)
  body += callout(22, 0.0, IX + iw / 2 + 40, IY + 70, "plan.position",
                  f"± {f['path_w']} m, drawn to {fmt_(lim)} m", color=SW)
  body += callout(60, lines[0], IX + 120, IY + 186, "laneLines[0]",
                  f"prob {SCENE['probs'][0]}: fainter, less sure")

  cy = IY + ih + 22
  for i, s_ in enumerate([
      f"Road camera of the comma 3X ({f['cam_w']}×{f['cam_h']}, f = {fmt_(f['focal'])} px), level calibration, {h:g} m "
      "above the road.",
      f"Curve to the left, R = {radius:.0f} m at {SCENE['v_kmh']} km/h ({SCENE['a_lat']} m/s², inside the ODD), three "
      f"{lane:g} m lanes. Beyond {fmt_(f['max_draw'])} m only the paint shows.",
      "Synthetic drawing: the geometry a perfect model would report, with illustrative probabilities and stds; lane "
      f"lines and edges drawn {WIDEN}× the UI width."]):
    body.append(text(IX, cy + i * 16, s_, size=11, fill=MUTED))
  body.append(text(IX, cy + 50, "data_kind: synthetic · credit: none (WP-V-02 §5.3.5, DSR-12)", size=11, fill=MUTED,
                   family=MONO))

  # Right column: what steers.
  RX, RW = IX + iw + 36, W - 40 - (IX + iw + 36)
  y = IY
  body.append(rect(RX, y, RW, 214, fill=SAFETY_BG, stroke=SAFETY, sw=1.4))
  body.append(text(RX + 14, y + 24, "What steers the car", size=14, weight=700, fill=SAFETY))
  rows = [("network output", "action[0, 0]", f"= {SCENE['a_lat']} m/s²  (lateral acceleration)"),
          ("modeld divides", f"÷ max(1, v)²", f"v = {v:.1f} m/s"),
          ("modelV2", "action.desiredCurvature", f"= {curv:.5f} 1/m  (1 / {1 / curv:.0f} m)")]
  for i, (k, code, val) in enumerate(rows):
    yy = y + 52 + i * 46
    body.append(text(RX + 14, yy, k, size=10.5, fill=MUTED))
    body.append(text(RX + 14, yy + 17, code, size=12.5, weight=700, family=MONO))
    body.append(text(RX + 14 + text_w(code, 12.5, True) * 1.12 + 10, yy + 17, val, size=11, fill=INK))
  body.append(text(RX + 14, y + 196, "One number, 20 times a second, to controlsd (Figure 2).", size=11, fill=INK))

  y2 = y + 232
  body.append(rect(RX, y2, RW, 120, fill="#FFFFFF", stroke=LINE, sw=1.2))
  body.append(text(RX + 14, y2 + 24, "What the picture shows", size=14, weight=700))
  for i, s_ in enumerate(["plan, laneLines, roadEdges, leads: to the UI, the logs",
                          "and drivingModelData. They steer only if the network",
                          "has no action head: then modeld derives the curvature",
                          "from the plan (modeld.py, WP-C-11 §2.4)."]):
    body.append(text(RX + 14, y2 + 46 + i * 16, s_, size=11, fill=MUTED))

  # Sample grids, top-down.
  y3 = y2 + 140
  body.append(text(RX, y3 + 12, "Where the 33 points fall", size=13, weight=700))
  ax0, ax1, top = RX + 8, RX + RW - 8, y3 + 46
  span = max(f["x_max"], v * f["t_max"])
  span = 50 * -(-span // 50)

  def ax(m: float) -> float:
    return ax0 + (ax1 - ax0) * m / span

  body.append(rect(ax(0), top - 16, ax(lim) - ax(0), 84, fill=GREY_BG, stroke="none", rx=4))
  body.append(text(ax(lim) + 6, top - 4, f"← drawn on screen, ≤ {fmt_(lim)} m", size=9.5, fill=MUTED))
  for label_, pts, yy, col in [("laneLines, roadEdges: X_IDXS", f["x_idxs"], top + 16, INK),
                               (f"plan: T_IDXS × v (0–{fmt_(f['t_max'])} s)", [v * t for t in f["t_idxs"]], top + 54, SW)]:
    body.append(text(ax(0) + 4, yy - 7, label_, size=10, fill=col, weight=600))
    body.append(line(ax(0), yy, ax1, yy, stroke=LINE, sw=1))
    for m in pts:
      body.append(el("circle", None, cx=fmt_(ax(m)), cy=fmt_(yy), r=2.2, fill=col))
  for m in range(0, int(span) + 1, 50):
    body.append(text(ax(m), top + 84, f"{m} m", size=9.5, fill=MUTED, anchor="middle"))
  gap0, gap1 = f["x_idxs"][1] - f["x_idxs"][0], f["x_idxs"][-1] - f["x_idxs"][-2]
  body.append(text(RX, top + 104, f"Spacing grows with distance: {gap0:.2f} m apart at first, {gap1:.1f} m at "
                   f"{fmt_(f['x_max'])} m.", size=10.5, fill=MUTED))

  H = int(max(cy + 72, top + 124))
  desc = (f"A synthetic view from the comma 3X road camera of a highway curve to the left (R = {radius:.0f} m at "
          f"{SCENE['v_kmh']} km/h) with the model's four lane lines, two road edges and the plan drawn as the onroad UI "
          f"draws them, stamped for display, not for steering. Beside it: the steering command is one number, "
          f"action[0,0] = {SCENE['a_lat']} m/s² divided by v² to desiredCurvature = {curv:.5f} per metre. Lane lines and "
          f"road edges are sampled at {f['idx_n']} distances up to {fmt_(f['x_max'])} m, the plan at {f['idx_n']} times "
          f"up to {fmt_(f['t_max'])} s; the UI draws them to {fmt_(lim)} m.")
  return svg(W, H, "Figure 4. What the model draws, and what steers", desc, body)


def fmt_(v: float) -> str:
  return f"{v:.1f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------- Figure 5: timing strip

AS = REPO / "assurance"
# Each number of Figure 5 with the exact text it is read from; `--check` fails when a text is gone, so a changed
# budget or time forces the figure to be reviewed (the convention of WP-S-04's own fig_s04_timing.py).
TIMING_SOURCES = [
  (AS / "03-system" / "WP-S-04-timing-ftti-budget.md", "| SG-01 SoC command stall | 0.5 s | ≤ 0.05 s (TSR-408) | ≤ 0.1 s | ≥ 0.35 s |"),
  (AS / "03-system" / "WP-S-04-timing-ftti-budget.md", "| SG-01 SoC heartbeat loss | 0.5 s | ≤ 0.3 s (TSR-407) | ≤ 0.1 s | ≥ 0.1 s |"),
  (AS / "03-system" / "WP-S-04-timing-ftti-budget.md", "the reference build revokes within ≤ 0.06 s for `0x2E4` (T-34, simulated 0.043 s)"),
  (AS / "03-system" / "WP-S-04-timing-ftti-budget.md", "**≤ 0.31 s** (0.3 s + one task period)"),
  (AS / "03-system" / "WP-S-04-timing-ftti-budget.md", "Model inference ≤ 50 ms per frame; output older than 100 ms not used for actuation"),
  (AS / "03-system" / "WP-S-04-timing-ftti-budget.md", "Inference time to be measured (§6, M-09)"),
  (AS / "03-system" / "WP-S-02-technical-safety-requirements.md", "if no frame arrives for > 50 ms (5 frames)"),
  (AS / "03-system" / "WP-S-02-technical-safety-requirements.md", "before use (≤ 2 nominal periods) and shall set `latActive`/`longActive` false"),
  (AS / "trace" / "items" / "tsr.yaml", "but after 10 nominal periods, not 2"),
  (AS / "trace" / "items" / "tsr.yaml", "Not implemented: `input_freshness.py` (TSR-602) checks message age at arrival, not frame ID or source timestamp."),
  (AS / "07-supporting" / "impact" / "change-2026-10-13-host-supervision.md", "**Accepted for now** by the lead"),
  (REPO / "openpilot" / "selfdrive" / "controls" / "lib" / "input_freshness.py", "STALE_PERIODS = 10."),
  (REPO / "openpilot" / "cereal" / "services.py", '"modelV2": (True, 20.'),
  (REPO / "openpilot" / "cereal" / "services.py", '"carControl": (True, 100.'),
]
FTTI_SG01 = 0.5
# Rows of the lower panel (seconds): budget (FDTI, FRTI) and what the code does, with the status read from the sources.
TIMING_ROWS = [
  {"title": "SoC stops sending commands", "who": "panda: 0x2E4 arrival (T-34)", "fdti": 0.05, "frti": 0.1, "impl": 0.06,
   "impl_text": "≤ 0.06 s (simulated 0.043 s)", "status": "over", "note": "one 10 ms task period over the FDTI; not verified (M-05)"},
  {"title": "SoC heartbeat lost", "who": "panda: heartbeat (T-06a)", "fdti": 0.3, "frti": 0.1, "impl": 0.31,
   "impl_text": "≤ 0.31 s", "status": "over", "note": "0.3 s + one task period; not verified (M-05)"},
  {"title": "Model output stops", "who": "controlsd: input freshness (TSR-602)", "fdti": 0.1, "frti": None, "impl": 0.5,
   "impl_text": "0.5 s (10 periods at 20 Hz)", "status": "gap",
   "note": "TSR-602 asks 2 periods; 10 accepted for now, until logs show the jitter"},
  {"title": "Model output frozen", "who": "controlsd: frame ID / source age (TSR-631)", "fdti": 0.1, "frti": None,
   "impl": None, "impl_text": "not detected", "status": "none", "note": "messages keep arriving, so the age check passes"},
]


def timing_problems() -> list[str]:
  out, cache = [], {}
  for p, s in TIMING_SOURCES:
    cache.setdefault(p, p.read_text(encoding="utf-8"))
    if s not in cache[p]:
      out.append(f"{p.relative_to(REPO)}: text gone: {s}")
  return out


def build_timing() -> str:
  W, L = 1320, 250                                     # page width; label column
  body = header(W, "5", "Timing: one model cycle, and how fast a stop is caught",
                "Above, 100 ms of normal running. Below, how long each kind of stop takes to detect, against the "
                "SG-01 budget.", "WP-S-04 §3.7, §4, §5 · WP-S-02 TSR-408, 602, 631")
  x0, x1 = 40 + L, W - 40

  # Panel A: 0–100 ms.
  def ta(ms: float) -> float:
    return x0 + (x1 - x0) * ms / 100.0

  y = 112
  body.append(text(40, y, "NORMAL RUNNING · 0–100 ms", size=12, weight=700, fill=SW))
  lanes = [("Road camera", "20 Hz frames"), ("Driving model", "modeld, AIR-17: ≤ 50 ms per frame"),
           ("Controls", "controlsd, 100 Hz"), ("Steering frame 0x2E4", "card → panda → EPS, 100 Hz"),
           ("Panda safety task", "checks arrival, 100 Hz")]
  ly = [y + 34 + i * 40 for i in range(len(lanes))]
  for (t_, s_), yy in zip(lanes, ly):
    body.append(text(40, yy + 4, t_, size=12, weight=700))
    body.append(text(40, yy + 19, s_, size=10, fill=MUTED))
    body.append(line(x0, yy + 8, x1, yy + 8, stroke=HAIR, sw=1))
  for ms in range(0, 101, 10):
    body.append(line(ta(ms), y + 18, ta(ms), ly[-1] + 22, stroke=HAIR, sw=1, dash="2 3"))
    body.append(text(ta(ms), ly[-1] + 38, f"{ms} ms", size=9.5, fill=MUTED, anchor="middle"))
  for ms in (0, 50):                                   # camera frames
    body.append(rect(ta(ms) - 3, ly[0] - 6, 6, 22, fill=INK, stroke="none", rx=2))
    body.append(rect(ta(ms) + 4, ly[1] - 6, ta(ms + 50) - ta(ms) - 8, 26, fill="url(#hatch)", stroke=MUTED, rx=4,
                     sw=1))
    body.append(text(ta(ms) + 12, ly[1] + 11, "inference + parse; time not measured yet (M-09)", size=10, fill=INK))
  for ms in range(0, 100, 10):
    held = "A" if ms < 50 else "B"
    body.append(rect(ta(ms) + 2, ly[2] - 4, ta(10) - ta(0) - 4, 20, fill=SW_BG, stroke=SW, rx=3, sw=1))
    body.append(text(ta(ms + 5), ly[2] + 10, f"κ {held}", size=9.5, fill=SW, anchor="middle", weight=600))
    body.append(rect(ta(ms) + 2, ly[3] - 2, 5, 16, fill=SAFETY, stroke="none", rx=1))
    body.append(el("circle", None, cx=fmt_(ta(ms) + 4.5), cy=fmt_(ly[4] + 7), r=3.5, fill="#FFFFFF", stroke=SAFETY,
                   stroke_width=1.4))
  body.append(text(x1, y, "κ A, κ B: one model output's desiredCurvature, used for five control steps", size=10.5,
                   fill=MUTED, anchor="end"))

  # Panel B: 0–600 ms.
  y2 = ly[-1] + 76
  span = 0.6

  def tb(s: float) -> float:
    return x0 + (x1 - x0) * s / span

  body.append(text(40, y2, "WHEN SOMETHING STOPS · 0–600 ms", size=12, weight=700, fill=SW))
  ry = [y2 + 36 + i * 54 for i in range(len(TIMING_ROWS))]
  for r, yy in zip(TIMING_ROWS, ry):
    body.append(text(40, yy + 4, r["title"], size=12, weight=700))
    body.append(text(40, yy + 19, r["who"], size=10, fill=MUTED))
    # Budget: FDTI then FRTI, outlined.
    body.append(rect(tb(0), yy - 8, tb(r["fdti"]) - tb(0), 12, fill=GREY_BG, stroke=MUTED, rx=2, sw=1))
    lab = f"required ≤ {r['fdti']:g} s"
    if r["frti"]:
      body.append(rect(tb(r["fdti"]), yy - 8, tb(r["fdti"] + r["frti"]) - tb(r["fdti"]), 12, fill="#FFFFFF",
                       stroke=MUTED, rx=2, sw=1, dash="3 2"))
      lab += f" + reaction ≤ {r['frti']:g} s"
    body.append(text(tb(r["fdti"] + (r["frti"] or 0)) + 6, yy + 2, lab, size=9.5, fill=MUTED))
    # What the code does.
    col = {"over": AMBER, "gap": RED, "none": RED}[r["status"]]
    if r["impl"] is not None:
      body.append(rect(tb(0), yy + 8, tb(r["impl"]) - tb(0), 12, fill=col, stroke="none", rx=2))
      msg = f"{r['impl_text']} · {r['note']}"
      if tb(r["impl"]) + 6 + text_w(msg, 10) > x1:       # no room after the bar: write it inside, in white
        body.append(text(tb(0) + 8, yy + 18, msg, size=10, fill="#FFFFFF", weight=600))
      else:
        body.append(text(tb(r["impl"]) + 6, yy + 18, msg, size=10, fill=INK))
    else:
      p, _ = pill(tb(0), yy + 6, r["impl_text"].upper(), RED, size=9, h=16)
      body += p
      body.append(text(tb(0) + 92, yy + 18, r["note"], size=10, fill=INK))
  bottom = ry[-1] + 30
  body.append(line(tb(FTTI_SG01), y2 + 14, tb(FTTI_SG01), bottom, stroke=RED, sw=1.6, dash="5 3"))
  body.append(text(tb(FTTI_SG01) - 6, y2 + 12, f"SG-01 FTTI {FTTI_SG01:g} s", size=10.5, fill=RED, weight=700,
                   anchor="end"))
  for ms in range(0, 601, 100):
    body.append(text(tb(ms / 1000), bottom + 16, f"{ms} ms", size=9.5, fill=MUTED, anchor="middle"))

  ny = bottom + 44
  lg, _ = legend(40, ny, [(GREY_BG, MUTED, "detection required (FDTI)"), ("#FFFFFF", MUTED + " dashed",
                          "reaction required (FRTI)"), (AMBER, "none", "code: just over"),
                          (RED, "none", "code: well over, or missing")])
  body += lg
  body.append(text(40, ny + 22, "Times are code-derived or simulated, not measured on the car. The model's own run "
                   "time is unmeasured (M-09), so the strip shows the period it must fit, not how long it takes.",
                   size=11, fill=MUTED))
  H = int(ny + 40)
  desc = ("Upper strip: in 100 ms the road camera gives two frames, the driving model runs once per frame, and "
          "controlsd, the 0x2E4 steering frame and the panda safety task run every 10 ms, so each model output steers "
          "five control steps. Lower strip, against the SG-01 FTTI of 0.5 s: the panda catches missing commands in "
          "≤ 0.06 s (required 0.05 s) and a lost heartbeat in ≤ 0.31 s (required 0.3 s); controlsd stops steering on a "
          "stale model output after 0.5 s (required 0.1 s, accepted for now); a frozen model output is not detected.")
  return svg(W, H, "Figure 5. Timing: one model cycle, and how fast a stop is caught", desc, body)


# ---------------------------------------------------------------- Figure 6: steering controller

LATCTRL = REPO / "openpilot" / "selfdrive" / "controls" / "lib" / "latcontrol_torque.py"


def torque_facts() -> dict:
  src = LATCTRL.read_text(encoding="utf-8")

  def need(pattern: str, what: str) -> re.Match:
    m = re.search(pattern, src, re.M)
    if not m:
      raise SourceError(f"latcontrol_torque.py: {what} changed form; update fig_driving.py")
    return m
  f = {k: float(need(rf"^{n} = ([\d.]+)", n).group(1)) for k, n in
       [("kp", "KP"), ("ki", "KI"), ("lp_hz", "LP_FILTER_CUTOFF_HZ"), ("lookahead", "JERK_LOOKAHEAD_SECONDS"),
        ("jerk_gain", "JERK_GAIN"), ("buffer", "LAT_ACCEL_REQUEST_BUFFER_SECONDS")]}
  f["speeds"] = [float(v) for v in need(r"^INTERP_SPEEDS = \[([^\]]+)\]", "INTERP_SPEEDS").group(1).split(",")]
  f["kp_interp"] = need(r"^KP_INTERP = \[([^\]]+)\]", "KP_INTERP").group(1).replace(" ", "").split(",")
  for p, what in [(r"measurement = measured_curvature \* CS\.vEgo \*\* 2", "measurement"),
                  (r"expected_lateral_accel = self\.lat_accel_request_buffer\[-delay_frames\]", "delayed setpoint"),
                  (r"ff = gravity_adjusted_future_lateral_accel", "feedforward"),
                  (r"ff -= self\.torque_params\.latAccelOffset", "offset"),
                  (r"ff \+= get_friction\(error \+ JERK_GAIN \* desired_lateral_jerk", "friction"),
                  (r"freeze_integrator = steer_limited_by_safety or CS\.steeringPressed or CS\.vEgo < (\d+)", "integrator freeze"),
                  (r"output_torque = self\.torque_from_lateral_accel\(output_lataccel, self\.torque_params\)", "torque map")]:
    need(p, what)
  f["freeze_v"] = int(need(r"CS\.vEgo < (\d+)\n", "freeze speed").group(1))
  return f


def build_torque(f: dict) -> str:
  W = 1320
  body = header(W, "6", "From curvature to torque: the steering controller",
                "latcontrol_torque.py, 100 times a second. It works in lateral acceleration and converts to torque only "
                "at the end.", "latcontrol_torque.py · LatControlTorque.update")
  FL = {"in": (GREY_BG, INK), "sw": ("#FFFFFF", SW), "out": (SAFETY_BG, SAFETY), "note": (CHIP, LINE)}

  def blk(x, y, w, h, title, lines_, kind="sw"):
    fill, stroke = FL[kind]
    out = [rect(x, y, w, h, fill=fill, stroke=stroke, sw=1.4)]
    out.append(text(x + 10, y + 19, title, size=12, weight=700))
    for i, s in enumerate(lines_):
      out.append(text(x + 10, y + 35 + i * 14, fit(s, w - 18, 10.5), size=10.5, fill=MUTED,
                      family=MONO if any(c in s for c in "=×·²") else ""))
    return out

  def arr(x1, y1, x2, y2, label="", lx=None, ly=None):
    out = [line(x1, y1, x2, y2, stroke=MUTED, sw=1.5)]
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    pts = [(x2, y2), (x2 - 8 * math.cos(a - 0.4), y2 - 8 * math.sin(a - 0.4)), (x2 - 8 * math.cos(a + 0.4), y2 - 8 * math.sin(a + 0.4))]
    out.append(path("M" + " L".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts) + " Z", stroke=MUTED, sw=1, fill=MUTED))
    if label:
      out.append(text(lx if lx is not None else (x1 + x2) / 2, ly if ly is not None else min(y1, y2) - 6, label,
                      size=9.5, fill=INK, anchor="middle", family=MONO))
    return out

  y1, y2, y3 = 112, 250, 392
  body += blk(40, y1, 210, 78, "Desired curvature", ["action.desiredCurvature", "from the driving model"], "in")
  body += blk(300, y1, 250, 78, "Request buffer", [f"κ × v² = lateral accel", f"last {f['buffer']:g} s kept, 100 Hz"])
  body += blk(600, y1, 290, 78, "Setpoint", ["the request from lat_delay ago", "(learned actuator delay)"])
  body += blk(40, y2, 210, 78, "Steering angle", ["carState.steeringAngleDeg", "and roll, from the car"], "in")
  body += blk(300, y2, 250, 78, "Measurement", ["vehicle model curvature", "× v² = lateral accel now"])
  body += blk(600, y2, 290, 78, "Error = setpoint − measurement", ["in m/s², not in torque"])
  body += blk(300, y3, 590, 92, "Feedforward", ["future request − roll · g − latAccelOffset",
                                                f"+ friction(error + {f['jerk_gain']:g} · jerk), jerk filtered at "
                                                f"{f['lp_hz']:g} Hz, {f['lookahead']:g} s ahead",
                                                "(latAccelFactor, latAccelOffset, friction learned per car)"])
  kp0, kp1 = f["kp_interp"][0], f["kp_interp"][-1]
  body += blk(940, y2 - 40, 340, 128, "PID in lateral acceleration",
              [f"Kp by speed: {kp0} at {f['speeds'][0]:g} m/s … {f['kp']:g} at {f['speeds'][-1]:g} m/s",
               f"Ki = {f['ki']:g}", "integrator frozen when the panda limits the",
               f"torque, the driver steers, or v < {f['freeze_v']} m/s", "output = PID + feedforward"])
  body += blk(940, y3 + 6, 340, 80, "To torque", ["torque_from_lateral_accel (per car)", "→ clip → STEERING_LKA 0x2E4"],
              "out")
  body += arr(252, y1 + 39, 298, y1 + 39)
  body += arr(552, y1 + 39, 598, y1 + 39)
  body += arr(252, y2 + 39, 298, y2 + 39)
  body += arr(552, y2 + 39, 598, y2 + 39)
  body += arr(745, y1 + 80, 745, y2 - 2)
  body += arr(892, y2 + 39, 938, y2 + 39)
  body.append(path(f"M300,{y1 + 64} L276,{y1 + 64} L276,{y3 + 46} L292,{y3 + 46}", stroke=MUTED, sw=1.5))
  body += arr(290, y3 + 46, 298, y3 + 46)
  body.append(text(270, y3 - 8, "future request", size=9.5, fill=INK, anchor="end", family=MONO))
  body.append(path(f"M892,{y3 + 30} L916,{y3 + 30} L916,{y2 + 70} L930,{y2 + 70}", stroke=MUTED, sw=1.5))
  body += arr(928, y2 + 70, 938, y2 + 70)
  body += arr(1110, y2 + 90, 1110, y3 + 4)
  ny = y3 + 120
  body.append(text(40, ny, "There is no path search in steering: the learned model chooses the curvature, and this "
                   "controller only tracks it. The panda then limits the torque (Figure 3).", size=11.5, fill=MUTED))
  lg, _ = legend(40, ny + 26, [(GREY_BG, INK, "input"), ("#FFFFFF", SW, "computation"), (SAFETY_BG, SAFETY, "to the car")])
  body += lg
  desc = ("The torque controller: desired curvature times speed squared is buffered; the setpoint is the request from "
          "the learned actuator delay ago; the measurement is the vehicle model's curvature from the steering angle "
          f"times speed squared; the error goes to a PID with speed-scheduled Kp ({kp0} to {f['kp']:g}) and Ki "
          f"{f['ki']:g}; the feedforward is the future request less roll and offset plus friction; the sum is converted "
          "to torque per car and clipped.")
  return svg(W, int(ny + 44), "Figure 6. From curvature to torque: the steering controller", desc, body)


# ---------------------------------------------------------------- Figure 7: emergency and degraded reactions

EMERG_SOURCES = [
  (REPO / "assurance" / "02-concept" / "WP-C-01-item-definition.md", "Does not brake. The stock Toyota PCS stays in charge of AEB"),
  (REPO / "assurance" / "02-concept" / "WP-C-02-odd-and-intended-functionality.md", "turning at intersections, evasive steering, steering at standstill |"),
  (REPO / "assurance" / "03-system" / "WP-S-02-technical-safety-requirements.md", "| TSR-713 | While the stock system reports an AEB event (`stockAeb`), the SoC shall request zero acceleration"),
  (REPO / "assurance" / "03-system" / "WP-S-02-technical-safety-requirements.md", "**Implemented and unit-tested, not verified on the vehicle**: host side in `c045874` (#292)"),
  (REPO / "assurance" / "03-system" / "WP-S-02-technical-safety-requirements.md", "the item shall keep the lane and decelerate in lane to a standstill"),
  (REPO / "assurance" / "03-system" / "WP-S-02-technical-safety-requirements.md", "Implemented in software and unit-tested, not verified on the vehicle: `selfdrived` latches the manoeuvre"),
  (REPO / "openpilot" / "selfdrive" / "selfdrived" / "minimum_risk.py", "class MinimumRiskManeuver"),
  (REPO / "assurance" / "02-concept" / "WP-C-01-item-definition.md", "| AOU-16 |"),
  (REPO / "assurance" / "03-system" / "WP-S-02-technical-safety-requirements.md", "| TSR-621 | While engaged, `selfdrived` shall raise an immediate disable"),
  (REPO / "assurance" / "03-system" / "WP-S-04-timing-ftti-budget.md", "| model `hardBrakePredicted` or planner FCW | not derived; measure (M-12) |"),
  (REPO / "assurance" / "02-concept" / "WP-C-01-item-definition.md", "| AOU-04 | The stock PCS/AEB keeps full function"),
  (REPO / "openpilot" / "selfdrive" / "selfdrived" / "state.py", "SOFT_DISABLE_TIME = 3"),
  (REPO / "openpilot" / "selfdrive" / "controls" / "lib" / "longcontrol.py", "def stock_aeb_stand_down"),
  (REPO / "openpilot" / "selfdrive" / "monitoring" / "policy.py", "self._NO_RESPONSE_TIMEOUT = 5."),
]
EMERG_ROWS = [  # situation, what the item does, who finishes it, status, status class
  ("Lead brakes hard", "MPC brakes up to −3.5 m/s²; FCW warns (planner or model)", "driver brakes harder",
   "implemented; FCW onset not derived (T-31)", "amber"),
  ("Car's own AEB fires", "stands down: no drive requested while stockAeb is set (TSR-713)", "stock PCS brakes",
   "implemented, not verified (AOU-04)", "amber"),
  ("Input stale or failed", "stops steering on stale input; soft disable, 3 s of alerts", "driver takes over",
   "partly met (TSR-602 10 periods, FM-03)", "amber"),
  ("Panda and host disagree", "immediate disable with take-over request (TSR-621, TSR-615)", "driver takes over",
   "implemented, not verified", "amber"),
  ("Main computer stalls", "panda revokes authority ≤ 0.06 s, siren (T-34)", "driver takes over",
   "implemented, not verified (M-05)", "amber"),
  ("Driver does not respond", "alerts at 5, 8, 13 s, then the minimum-risk manoeuvre: stops in lane, still steering, "
   "stays held and cannot resume until the driver takes over (TSR-633, DQ-365 A)", "the item: minimum-risk manoeuvre",
   "implemented, not verified; PCM hold assumed (AOU-16)", "amber"),
  ("Obstacle needs a swerve", "nothing: evasive steering is not provided (WP-C-02)", "driver steers",
   "by design (Level 2)", "grey"),
]


def emerg_problems() -> list[str]:
  out, cache = [], {}
  for p, s in EMERG_SOURCES:
    cache.setdefault(p, p.read_text(encoding="utf-8"))
    if s not in cache[p]:
      out.append(f"{p.relative_to(REPO)}: text gone: {s}")
  return out


def build_emergency() -> str:
  W = 1320
  body = header(W, "7", "When something goes wrong: who reacts, and how",
                "The item's own reactions, from warning to standstill. In Level 2 the driver is the fallback, except "
                "where the driver is the problem.", "WP-S-02 TSR-602, 615, 621, 633, 713 · WP-C-01 F-06 · WP-C-02")
  cols = [(40, "SITUATION", 200), (250, "WHAT THE ITEM DOES", 520), (780, "WHO FINISHES IT", 210), (1000, "STATUS", 280)]
  y = 108
  for x, t_, _ in cols:
    body.append(text(x, y, t_, size=10.5, weight=700, fill=MUTED))
  y += 12
  rh = 52
  fills = {"amber": ("#FFF7E6", AMBER), "red": ("#FDE2E2", RED), "grey": (GREY_BG, MUTED)}
  for i, (sit, does, who, status, cls) in enumerate(EMERG_ROWS):
    yy = y + i * rh
    fill, col = fills[cls]
    body.append(rect(30, yy, W - 60, rh - 6, fill=fill if cls == "red" else ("#FFFFFF" if i % 2 else CHIP), stroke=col if cls == "red" else "none", rx=6))
    body.append(text(40, yy + 20, sit, size=12, weight=700))
    words, rows_, cur = does.split(), [], ""
    for w_ in words:
      if text_w(cur + " " + w_, 10.5) > 510:
        rows_.append(cur)
        cur = w_
      else:
        cur = (cur + " " + w_).strip()
    rows_.append(cur)
    for k, r in enumerate(rows_[:2]):
      body.append(text(250, yy + 18 + k * 15, r, size=10.5, fill=INK if k == 0 else MUTED))
    body.append(text(780, yy + 20, fit(who, 210, 10.5), size=10.5, fill=INK, weight=600 if cls == "red" else ""))
    p, _ = pill(1000, yy + 10, status, col, size=9.5, h=18)
    body += p
  ny = y + len(EMERG_ROWS) * rh + 18
  body.append(text(40, ny, "The one emergency behaviour the requirements ask for and the code only half has is the stop for "
                   "an unresponsive driver: the car slows (18 s, vision policy) but is not held, disengaged or locked out.",
                   size=11.5, fill=INK))
  body.append(text(40, ny + 18, "Emergency braking beyond −3.5 m/s² is the stock PCS's job, and evasive steering is the "
                   "driver's; neither is in the item's scope.", size=11.5, fill=MUTED))
  desc = "Emergency and degraded reactions: " + "; ".join(f"{s}: {d}; {w}; {st}" for s, d, w, st, _ in EMERG_ROWS) + "."
  return svg(W, int(ny + 36), "Figure 7. When something goes wrong: who reacts, and how", desc, body)


# ---------------------------------------------------------------- main

def build_all() -> dict[str, str]:
  fms = fm_rows(WP_C07.read_text(encoding="utf-8"))
  missing = unplaced(fms)
  if missing:
    raise SourceError("WP-C-07 modifications on no Figure 1 box: " + ", ".join(missing) +
                      "; add the file to BOXES in fig_driving.py")
  gone = timing_problems() + emerg_problems()
  if gone:
    raise SourceError("Figure 5 sources changed:\n" + "\n".join(gone) + "\nreview TIMING_ROWS in fig_driving.py")
  facts = code_facts()
  env = c01.envelope(WP_C01.read_text(encoding="utf-8"))
  return {OUTS["pipeline"]: build_pipeline(fms), OUTS["paths"]: build_paths(facts), OUTS["funnel"]: build_funnel(env, facts),
          OUTS["overlay"]: build_overlay(overlay_facts()), OUTS["timing"]: build_timing(),
          OUTS["torque"]: build_torque(torque_facts()), OUTS["emergency"]: build_emergency()}


def main(argv: list[str]) -> int:
  out = build_all()
  if "--check" in argv:
    stale = [n for n, s in out.items() if not (OUT_DIR / n).exists() or (OUT_DIR / n).read_text(encoding="utf-8") != s]
    if stale:
      print("stale: " + ", ".join(stale) + "\nrun: python3 docs/liondriver/figures/fig_driving.py", file=sys.stderr)
      return 1
    print(f"fig_driving: {len(out)} figures current, every WP-C-07 modification placed")
    return 0
  for n, s in out.items():
    (OUT_DIR / n).write_text(s, encoding="utf-8")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
