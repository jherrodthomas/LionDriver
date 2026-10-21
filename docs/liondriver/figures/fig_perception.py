#!/usr/bin/env python3
"""Draw the figures of docs/liondriver/perception-models.md (pipeline, lead fusion, insufficiencies, lead overlay,
driver-monitoring timing).

Sources of record:
  - Figure 1: the AIR chips and their colours are parsed from the WP-C-11 §6 tables (the Status / evidence cell); the
    outputs, their effect and their consumers are hand-listed from WP-C-11 §2.4 with the exact text each comes from.
  - Figure 2: radard's matching constants and logic are read from `radard.py`.
  - Figure 3: parsed from WP-C-06 §3 (perception insufficiencies, Type P) and §5 (TC → FI), WP-C-05 §6 (proposed
    modifications per SH) and the WP-C-11 §6 Parent column (AIRs that name the FI).
  - Figure 4: a synthetic road-camera view; the camera comes from fig_driving.overlay_facts and the chevron rules from
    the onroad UI (`model_renderer.py`).
  - Figure 5: the DM timers and thresholds are read from `policy.py`; the budgets from WP-S-04 and the TSR statuses
    from the trace items, each with the exact text it comes from.

    python3 fig_perception.py            # write the SVGs into docs/assets/liondriver/
    python3 fig_perception.py --check    # fail if a source changed form or an SVG is stale

Standard library only. Output is deterministic.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fig_driving as fd  # noqa: E402
from fig_driving import (AMBER, CHIP, GREY_BG, HAIR, INK, LINE, MONO, MUTED, RED, REPO, SAFETY, SAFETY_BG, SW,  # noqa: E402
                         SW_BG, SourceError, el, fit, fmt_, header, legend, line, path, pill, plain, rect, section, svg,
                         table, text, text_w)
from fig_speed import arrow, box  # noqa: E402
from figkit import split_row  # noqa: E402

OUT_DIR = REPO / "docs" / "assets" / "liondriver"
OUTS = {"pipeline": "perception-1-pipeline.svg", "fusion": "perception-2-lead-fusion.svg",
        "fi": "perception-3-insufficiencies.svg", "overlay": "perception-4-lead-overlay.svg",
        "dm": "perception-5-dm-timing.svg"}
AS = REPO / "assurance"
C05 = AS / "02-concept" / "WP-C-05-sotif-hazard-identification.md"
C06 = AS / "02-concept" / "WP-C-06-sotif-insufficiencies-triggering-conditions.md"
C11 = AS / "02-concept" / "WP-C-11-ai-system-definition-and-safety-requirements.md"
S04 = AS / "03-system" / "WP-S-04-timing-ftti-budget.md"
TSR = AS / "trace" / "items" / "tsr.yaml"
OP = REPO / "openpilot"
RADARD = OP / "selfdrive" / "controls" / "radard.py"
POLICY = OP / "selfdrive" / "monitoring" / "policy.py"
UI = OP / "selfdrive" / "ui" / "onroad" / "model_renderer.py"
MODEL_PY = OP / "common" / "transformations" / "model.py"

TEXTS = [
  (C11, "| AI-1 | Driving model (\"supercombo\"), vision + policy, recurrent |"),
  (C11, "| AI-3 | Driver monitoring model |"),
  (C11, "Device GPU (`QCOM`), process `modeld`, 20 Hz"),
  (C11, "**Direct lateral command** (F-01), bounded by controller limits and the panda envelope"),
  (C11, "Longitudinal command in Experimental Mode (GAP-18, D-08)"),
  (C11, "Longitudinal command in both Chill and Experimental modes via the MPC lead"),
  (C11, "| UI, logging, `drivingModelData`; plan-based action only if no `action` head | Indirect |"),
  (C11, "| Warning (F-06); DM sensitivity; longitudinal |"),
  (C11, "| Indirect (state estimation, calibration) |"),
  (C11, "| Alerts, force-decel, lockout (F-04) |"),
  (C11, "message `valid` hard-coded `True` (`:99`)"),
  (C11, "No non-finite check on AI-1 or AI-3 outputs"),
  (S04, "| SG-08 driver not supervising (§3.8.4) | ≤ 6 s from loss of attention to the first alert"),
  (S04, "+ DM frame and model latency (not measured)"),
  (S04, "reaction ≤ 5 s after the terminal alert (TSR-633, T-33)"),
  (S04, "DM invalid → take-over request ≤ 2 s (TSR-609)"),
  (TSR, "Not met: `driverStateV2` always `valid=True` at source"),
  (TSR, "Implemented in software and unit-tested, not verified on the vehicle: `selfdrived` latches the manoeuvre"),
]


def problems() -> list[str]:
  out, cache = [], {}
  for p, s in TEXTS:
    cache.setdefault(p, p.read_text(encoding="utf-8"))
    if s not in cache[p]:
      out.append(f"{p.relative_to(REPO)}: text gone: {s}")
  return out


def grab(p: Path, pattern: str, what: str, flags=re.M) -> re.Match:
  m = re.search(pattern, p.read_text(encoding="utf-8"), flags)
  if not m:
    raise SourceError(f"{p.relative_to(REPO)}: {what} changed form; update fig_perception.py")
  return m


# ---------------------------------------------------------------- sources

def airs() -> dict[str, dict]:
  """WP-C-11 §6: AIR-nn -> statement, parent cell, status class (red: not met / not implemented, amber: partial)."""
  body = section(C11.read_text(encoding="utf-8"), "## 6. AI safety requirements")
  out = {}
  for ln in body.splitlines():
    if not ln.startswith("| AIR-"):
      continue
    cells = split_row(ln)
    status = plain(cells[-1])
    low = status.lower()
    cls = ("red" if re.match(r"\W*(not met|not implemented|not started)", low) else
           "amber" if re.match(r"\W*partial", low) else "grey")
    out[cells[0]] = {"statement": plain(cells[1]), "parent": plain(cells[3]), "status": status, "cls": cls}
  if len(out) < 30:
    raise SourceError(f"WP-C-11 §6: found {len(out)} AIRs, expected 30; update fig_perception.py")
  return out


def insufficiencies() -> list[dict]:
  c06 = C06.read_text(encoding="utf-8")
  head, rows = table(section(c06, "## 3. Functional insufficiencies"), "ID")
  _, tcrows = table(section(c06, "## 5. TC → FI → SH evaluation"), "TC")
  _, shrows = table(section(C05.read_text(encoding="utf-8"), "## 6. Risk evaluation summary"), "SH")
  fm_by_sh = {r[0]: re.findall(r"FM-\d+", r[3]) for r in shrows}
  air = airs()
  out = []
  for r in rows:
    if r[head.index("Type")] != "P":
      continue
    fi = r[0]
    tcs = sorted({t for tr in tcrows if re.search(rf"\b{fi}\b", tr[1]) for t in re.findall(r"TC-\d+", tr[0])},
                 key=lambda t: int(t[3:]))
    shs = re.findall(r"SH-\d+", r[head.index("Linked SH")])
    fms = sorted({m for s in shs for m in fm_by_sh.get(s, [])}, key=lambda m: int(m[3:]))
    ai = [a for a, v in air.items() if re.search(rf"\b{fi}\b", v["parent"])]
    out.append({"id": fi, "component": plain(r[head.index("Component")]), "text": plain(r[head.index("Insufficiency")]),
                "sh": shs, "tc": tcs, "fm": fms, "air": ai})
  if not out:
    raise SourceError("WP-C-06 §3: no Type P rows; update fig_perception.py")
  return out


def radard_facts() -> dict:
  f = {"r2c": float(grab(RADARD, r"^RADAR_TO_CAMERA = ([\d.]+)", "RADAR_TO_CAMERA").group(1)),
       "v_stat": float(grab(RADARD, r"^V_EGO_STATIONARY = ([\d.]+)", "V_EGO_STATIONARY").group(1))}
  m = grab(RADARD, r"dist_sane = abs\(track\.dRel - offset_vision_dist\) < max\(\[\(offset_vision_dist\)\*([\d.]+), ([\d.]+)\]\)",
           "dist_sane")
  f["sane_frac"], f["sane_min"] = float(m.group(1)), float(m.group(2))
  m = grab(RADARD, r"vel_sane = \(abs\(track\.vRel \+ v_ego - lead\.v\[0\]\) < ([\d.]+)\) or \(v_ego \+ track\.vRel > ([\d.]+)\)",
           "vel_sane")
  f["vel_tol"], f["moving"] = float(m.group(1)), float(m.group(2))
  f["prob"] = float(grab(RADARD, r"if len\(tracks\) > 0 and ready and lead_prob > ([\d.]+):", "lead prob gate").group(1))
  grab(RADARD, r"elif \(track is None\) and ready and \(lead_prob > \.5\):", "vision fallback")
  grab(RADARD, r"return prob_d \* prob_y \* prob_v", "match product")
  m = grab(RADARD, r"return abs\(self\.yRel\) < ([\d.]+) and \(v_ego < V_EGO_STATIONARY\) and \(([\d.]+) < self\.dRel < ([\d.]+)\)",
           "low-speed lead")
  f["ls_y"], f["ls_d0"], f["ls_d1"] = float(m.group(1)), float(m.group(2)), float(m.group(3))
  f["prob_decay"] = float(grab(RADARD, r"FirstOrderFilter\(0\.0, ([\d.]+), DT_MDL\) for _ in range\(2\)", "prob filter").group(1))
  f["tau_vision"] = float(grab(RADARD, r'"aLeadTau": ([\d.]+),', "vision tau").group(1))
  return f


def ui_facts() -> dict:
  f = {}
  m = grab(UI, r"speed_buff, lead_buff = ([\d.]+), ([\d.]+)", "lead buffers")
  f["speed_buff"], f["lead_buff"] = float(m.group(1)), float(m.group(2))
  m = grab(UI, r"sz = np\.clip\(\(25 \* 30\) / \(d_rel / 3 \+ 30\), ([\d.]+), ([\d.]+)\) \* ([\d.]+)", "chevron size")
  f["sz_min"], f["sz_max"], f["sz_k"] = float(m.group(1)), float(m.group(2)), float(m.group(3))
  grab(UI, r"rl\.Color\(218, 202, 37, 255\)", "glow colour")
  grab(UI, r"rl\.Color\(201, 34, 49, lead\.fill_alpha\)", "chevron colour")
  return f


def model_inputs() -> dict:
  m = grab(MODEL_PY, r"^MEDMODEL_INPUT_SIZE = \((\d+), (\d+)\)", "MEDMODEL_INPUT_SIZE")
  d = grab(MODEL_PY, r"^DM_INPUT_SIZE = \((\d+), (\d+)\)", "DM_INPUT_SIZE")
  return {"med": f"{m.group(1)}×{m.group(2)}", "dm": f"{d.group(1)}×{d.group(2)}"}


def dm_facts() -> dict:
  src = POLICY.read_text(encoding="utf-8")

  def num(name: str) -> float:
    m = re.search(rf"self\.{name} = ([\d.]+)", src)
    if not m:
      raise SourceError(f"policy.py: {name} changed form; update fig_perception.py")
    return float(m.group(1))
  f = {"vision": [num(f"_VISION_POLICY_ALERT_{i}_TIMEOUT") for i in (1, 2, 3)],
       "wheel": [num(f"_WHEELTOUCH_POLICY_ALERT_{i}_TIMEOUT") for i in (1, 2, 3)],
       "dist": [num(f"_WHEELTOUCH_POLICY_ALERT_{i}_DISTANCE") for i in (1, 2, 3)],
       "no_resp": num("_NO_RESPONSE_TIMEOUT"), "hi_std": num("_HI_STD_THRESHOLD"),
       "min_speed": num("_ALERT_MIN_SPEED")}
  m = re.search(r"self\._HI_STD_FALLBACK_TIME = int\(([\d.]+)\s*/ DT_DMON\)", src)
  if not m:
    raise SourceError("policy.py: _HI_STD_FALLBACK_TIME changed form; update fig_perception.py")
  f["fallback"] = float(m.group(1))
  m = re.search(r"for n_min in \[([\d, ]+)\]", src)
  f["lockout"] = [int(v) for v in m.group(1).split(",")] if m else []
  if not f["lockout"]:
    raise SourceError("policy.py: lockout minutes changed form; update fig_perception.py")
  return f


# ---------------------------------------------------------------- Figure 1: pipeline

OUTPUTS = [  # (output, AI, effect, consumer, kind, AIR chips)
  ("action.desiredCurvature", "AI-1", "Direct lateral command", "controlsd → steering", "direct", ["AIR-01", "AIR-18"]),
  ("leadsV3[0..2], lead_prob", "AI-1", "Longitudinal, via the MPC lead", "radard → plannerd", "direct",
   ["AIR-03", "AIR-04", "AIR-05", "AIR-11"]),
  ("action.desiredAcceleration", "AI-1", "Longitudinal, Experimental only", "plannerd min()", "off", ["AIR-29"]),
  ("meta.hardBrakePredicted …", "AI-1", "Warning (FCW); DM sensitivity", "selfdrived, policy", "warn", ["AIR-06"]),
  ("plan, laneLines, roadEdges", "AI-1", "Indirect", "UI, logs, drivingModelData", "ind", ["AIR-13"]),
  ("cameraOdometry", "AI-1", "Indirect (state estimation)", "locationd, calibrationd", "ind", []),
  ("driverStateV2", "AI-3", "Alerts, force-decel, lockout", "dmonitoringd → policy", "warn", ["AIR-07", "AIR-08", "AIR-15"]),
]
AIR_FILL = {"red": RED, "amber": AMBER, "grey": GREY_BG}


def build_pipeline(air: dict, mi: dict) -> str:
  W = 1320
  body = header(W, "1", "Perception: what the two models see and what they output",
                "Cameras, the driving model (AI-1) and the driver-monitoring model (AI-3), each output and who uses it. "
                "Chips are the WP-C-11 AI requirements on that output.", "WP-C-11 §2.1, §2.4, §6")
  y0 = 112
  body += box(40, y0, 200, 92, "Road cameras", ["narrow and wide, 20 Hz", f"two frames each, warped to {mi['med']}"], "car")
  body += box(40, y0 + 380, 200, 76, "Cabin camera", ["20 Hz", f"warped to {mi['dm']}"], "car")
  body += box(290, y0, 210, 92, "AI-1 driving model", ["\"supercombo\", recurrent", "modeld, GPU, 20 Hz"], "model",
              [("AIR-16", AIR_FILL[air["AIR-16"]["cls"]]), ("AIR-17", AIR_FILL[air["AIR-17"]["cls"]])])
  body += box(290, y0 + 380, 210, 76, "AI-3 DM model", ["dmonitoringmodeld, GPU", "valid hard-coded True"], "model")
  body += arrow(242, y0 + 46, 288, y0 + 46)
  body += arrow(242, y0 + 418, 288, y0 + 418)
  col = {"direct": (SAFETY_BG, SAFETY), "off": (CHIP, MUTED), "warn": ("#FFF7E6", AMBER), "ind": ("#FFFFFF", LINE)}
  ox, ow, oh = 560, 720, 50
  for i, (name, ai, effect, consumer, kind, chips) in enumerate(OUTPUTS):
    yy = y0 + i * (oh + 9) if ai == "AI-1" else y0 + 380 + 13
    fill, stroke = col[kind]
    body.append(rect(ox, yy, ow, oh, fill=fill, stroke=stroke, sw=1.3, dash="5 4" if kind == "off" else ""))
    body.append(text(ox + 12, yy + 20, name, size=12, weight=700, family=MONO))
    body.append(text(ox + 12, yy + 37, f"{effect} · {consumer}", size=10.5, fill=MUTED))
    cx = ox + ow - 12
    for a in reversed(chips):
      fill_ = AIR_FILL[air[a]["cls"]]
      wch = text_w(a, 9.5, True) + 12
      cx -= wch
      p, _ = pill(cx, yy + 17, a, fill_, color=MUTED if fill_ == GREY_BG else "#FFFFFF", stroke=LINE if fill_ == GREY_BG else "none")
      body += p
      cx -= 5
    src_y = y0 + 46 if ai == "AI-1" else y0 + 418
    body += arrow(502, src_y, ox - 2, yy + oh / 2)
  ny = y0 + 486
  body.append(text(40, ny, "Only two outputs command the car: the steering action and the leads. Everything else warns, "
                   "informs or is drawn on screen. No output of AI-1 or AI-3 is checked for non-finite values.",
                   size=11.5, fill=MUTED))
  lg, _ = legend(40, ny + 28, [(SAFETY_BG, SAFETY, "commands the car"), ("#FFF7E6", AMBER, "warns or alerts"),
                               ("#FFFFFF", LINE, "indirect"), (CHIP, MUTED + " dashed", "off in the reference build"),
                               (RED, "none", "AIR not met"), (AMBER, "none", "AIR partly met"),
                               (GREY_BG, LINE, "AIR not yet verified")])
  body += lg
  desc = ("Road cameras feed the driving model AI-1 and the cabin camera feeds the driver-monitoring model AI-3. AI-1's "
          "outputs: the steering action (direct lateral command), leads (longitudinal via the MPC), the model's own "
          "acceleration (Experimental only), meta including hardBrakePredicted (warning), plan, lane lines and road "
          "edges (indirect) and camera odometry (indirect). AI-3 outputs driverStateV2 (alerts, force-decel, lockout). "
          "Each carries chips for its WP-C-11 AI requirements, coloured by status: " +
          "; ".join(f"{a} {air[a]['cls']}" for o in OUTPUTS for a in o[5]) + ".")
  return svg(W, int(ny + 46), "Figure 1. Perception: what the two models see and what they output", desc, body)


# ---------------------------------------------------------------- Figure 2: lead fusion

def build_fusion(f: dict) -> str:
  W = 1320
  body = header(W, "2", "Picking the lead: radar track or the model's guess",
                "radard runs once per model output. The leads the MPC brakes for come from here.", "radard.py get_lead, "
                "match_vision_to_track")
  # Left: top-down sketch, 0–80 m.
  x0, x1, yc = 60, 640, 250

  def X(d: float) -> float:
    return x0 + (x1 - x0) * d / 80.0

  def Yl(y: float) -> float:
    return yc + y * 26.0
  body.append(rect(x0, Yl(-5.55), x1 - x0, Yl(5.55) - Yl(-5.55), fill="#E9EBE7", stroke="none", rx=0))
  for yy in (-5.55, 5.55):
    body.append(line(x0, Yl(yy), x1, Yl(yy), stroke=INK, sw=1.4))
  for yy in (-1.85, 1.85):
    body.append(line(x0, Yl(yy), x1, Yl(yy), stroke=MUTED, sw=1.2, dash="10 12"))
  body.append(rect(X(0) - 2, Yl(-0.9), 30, Yl(0.9) - Yl(-0.9), fill=INK, stroke="none", rx=4))
  body.append(text(X(0) + 13, Yl(-0.9) - 6, "ego", size=10, fill=INK, anchor="middle"))
  # The model's lead: 40 m, std 3 m.
  d_v, sd = 40.0, 3.0
  body.append(rect(X(d_v - 2 * sd), Yl(-1.2), X(d_v + 2 * sd) - X(d_v - 2 * sd), Yl(1.2) - Yl(-1.2), fill="#FFF7E6",
                   stroke=AMBER, rx=4, dash="4 3"))
  body.append(text(X(d_v), Yl(-1.2) - 8, f"model lead: x = {d_v:g} m ± std, prob 0.9", size=10, fill=AMBER, anchor="middle",
                   weight=600))
  d_r = d_v - f["r2c"]
  tracks = [(d_r + 0.6, 0.2, "matched track", SW), (52, -3.7, "track in the next lane", MUTED),
            (72, 0.0, "stationary return (a bridge?)", MUTED)]
  for d, y, lab, col in tracks:
    body.append(el("circle", None, cx=fmt_(X(d)), cy=fmt_(Yl(y)), r=6, fill=col))
    right = X(d) + 10 + text_w(lab, 10, True) < x1
    body.append(text(X(d) + 10 if right else X(d), Yl(y) + (18 if y >= 0 else -10), lab, size=10, fill=col, weight=600,
                     anchor="" if right else "middle"))
  body.append(text(x0, Yl(5.55) + 30, f"Radar distances are measured from the radar, {f['r2c']:g} m ahead of the camera, "
                   "so the model's x is shifted before matching.", size=10.5, fill=MUTED))
  for d in range(0, 81, 20):
    body.append(text(X(d), Yl(-5.55) - 10, f"{d} m", size=9.5, fill=MUTED, anchor="middle"))

  # Right: the decision.
  rx, rw = 700, 580
  steps = [
    ("1  Model sure enough?", f"lead_prob > {f['prob']:g} and radar tracks exist", INK),
    ("2  Best track", "max of p(d) · p(y) · p(v), each a Laplace curve around the model's value, width = its std", INK),
    ("3  Sane?", f"|Δd| < max({int(f['sane_frac'] * 100)} % of d, {f['sane_min']:g} m), and speed within {f['vel_tol']:g} m/s "
                 f"or the track moving > {f['moving']:g} m/s", INK),
    ("→  yes: radar lead", "distance and speed from the radar, filtered; radar = True", SW),
    ("→  no track, prob still high: vision-only lead", f"the model's own x, v, a; radar = False, tau {f['tau_vision']:g}", AMBER),
    ("→  otherwise: no lead", "the MPC follows the cruise target", MUTED),
    ("Below 4 m/s", f"the closest radar track with |y| < {f['ls_y']:g} m and {f['ls_d0']:g} < d < {f['ls_d1']:g} m "
                    "replaces leadOne if it is closer", INK),
    ("Holding on", f"the lead probability rises at once and decays with a {f['prob_decay']:g} s filter", INK),
  ]
  yy = 112
  for t_, s_, col_ in steps:
    body.append(text(rx, yy, t_, size=12, weight=700, fill=col_))
    body.append(text(rx, yy + 16, fit(s_, rw, 10.5), size=10.5, fill=MUTED))
    yy += 40
  body.append(text(40, yy + 8, "Two of the SOTIF insufficiencies sit right here: a false or misassociated radar target "
                   "(FI-06) and a lead kept or dropped wrongly when the model is unsure (FI-07).", size=11, fill=MUTED))
  desc = (f"Top-down sketch: the model's lead at {d_v:g} m with its uncertainty, a radar track inside it (matched), one in "
          "the next lane and a stationary return far ahead. Decision steps from radard.py: the model must report "
          f"lead_prob > {f['prob']:g}; the best track maximises the product of three Laplace likelihoods; it must be "
          f"within max({int(f['sane_frac'] * 100)} %, {f['sane_min']:g} m) and speed-sane; otherwise a vision-only lead "
          "if the model is still sure, else no lead; a low-speed override below 4 m/s; the probability filter.")
  return svg(W, int(yy + 28), "Figure 2. Picking the lead: radar track or the model's guess", desc, body)


# ---------------------------------------------------------------- Figure 3: insufficiencies

def build_fi(rows: list[dict]) -> str:
  W = 1320
  body = header(W, "3", "What perception can get wrong, and what is planned",
                "The perception insufficiencies of WP-C-06 with their triggering conditions, the hazards they lead to, "
                "the planned modifications and the AI requirements written against them.", "WP-C-06 §3, §5 · WP-C-05 §6 · WP-C-11 §6")
  cols = [(40, "Insufficiency", 470), (520, "Triggering conditions", 230), (760, "Hazards", 150),
          (920, "Planned (WP-C-07)", 150), (1080, "AI requirements", 200)]
  y = 108
  for x, t_, _ in cols:
    body.append(text(x, y, t_.upper(), size=10.5, weight=700, fill=MUTED))
  y += 12
  rh = 50

  def chip_row(x, yy, labels, fill, color, width):
    cx, cy, out = x, yy, []
    for lab in labels:
      wch = text_w(lab, 9, True) + 10
      if cx + wch > x + width and cx > x:
        cx, cy = x, cy + 18
      p, wch = pill(cx, cy, lab, fill, color=color, size=9, h=15, stroke=LINE if fill == GREY_BG else "none")
      out += p
      cx += wch + 4
    return out
  for i, r in enumerate(rows):
    yy = y + i * rh
    if i % 2 == 0:
      body.append(rect(30, yy, W - 60, rh, fill=CHIP, stroke="none", rx=4))
    body.append(text(40, yy + 18, f"{r['id']} · {r['component']}", size=11.5, weight=700))
    body.append(text(40, yy + 34, fit(r["text"], 470, 10.5), size=10.5, fill=MUTED))
    body += chip_row(520, yy + 10, r["tc"], GREY_BG, MUTED, 230)
    body += chip_row(760, yy + 10, r["sh"], RED, "#FFFFFF", 150)
    body += chip_row(920, yy + 10, r["fm"] or ["none"], AMBER if r["fm"] else GREY_BG, "#FFFFFF" if r["fm"] else MUTED, 150)
    body += chip_row(1080, yy + 10, r["air"] or ["none"], SW if r["air"] else GREY_BG, "#FFFFFF" if r["air"] else MUTED, 200)
  ny = y + len(rows) * rh + 26
  body.append(text(40, ny, "Each row is parsed from the work products: WP-C-06 §3 (Type P) and §5, WP-C-05 §6, and the "
                   "Parent column of WP-C-11 §6.", size=11, fill=MUTED))
  desc = "Perception insufficiencies: " + "; ".join(
    f"{r['id']} ({r['component']}): TCs {', '.join(r['tc']) or 'none'}; hazards {', '.join(r['sh'])}; planned "
    f"{', '.join(r['fm']) or 'none'}; AIRs {', '.join(r['air']) or 'none'}" for r in rows) + "."
  return svg(W, int(ny + 20), "Figure 3. What perception can get wrong, and what is planned", desc, body)


# ---------------------------------------------------------------- Figure 4: lead overlay

LEADS = [  # dRel (m), yRel (m), vRel (m/s), radar
  {"d": 24.0, "y": 0.0, "v": -3.0, "radar": True, "name": "leadOne"},
  {"d": 70.0, "y": 0.6, "v": 0.0, "radar": False, "name": "leadTwo"},
]


def build_overlay(cam: dict, ui: dict) -> str:
  W, S = 1320, 0.4
  IX, IY = 40, 104
  iw, ih = cam["cam_w"] * S, cam["cam_h"] * S
  h = cam["height"]
  body = header(W, "4", "Leads on screen, and the numbers behind them",
                "The onroad UI draws each lead radard reports as a chevron; size and opacity follow its distance and "
                "closing speed.", "model_renderer.py · radard.py")

  def proj(x: float, y: float, z: float = 0.0) -> tuple[float, float]:
    return IX + S * (cam["focal"] * y / x + cam["cam_w"] / 2), IY + S * (cam["focal"] * (h - z) / x + cam["cam_h"] / 2)

  def band(y0: float, y1: float, a: float = 5.0, b: float = 2000.0) -> str:
    pts = [proj(a, y0), proj(b, y0), proj(b, y1), proj(a, y1)]
    return "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts) + " Z"
  hz = IY + ih / 2
  scene = [rect(IX, IY, iw, ih / 2 + 1, fill="#C7D4E0", stroke="none", rx=0),
           rect(IX, hz, iw, ih / 2, fill="#8E9A7C", stroke="none", rx=0),
           path(band(-6.6, 8.6), stroke="none", fill="#9A9C92"), path(band(-5.65, 5.65), stroke="none", fill="#5E6266")]
  for yy in (-5.55, 5.55):
    scene.append(path(band(yy - 0.075, yy + 0.075), stroke="none", fill="#E9E9E2"))
  for yy in (-1.85, 1.85):
    x = 5.0
    while x < 300:
      scene.append(path(band(yy - 0.075, yy + 0.075, x, x + 3.0), stroke="none", fill="#E9E9E2"))
      x += 12.0
  for ld in sorted(LEADS, key=lambda l: -l["d"]):           # cars, far first, drawn at the lead's distance
    d = ld["d"]
    bl, tr = proj(d, ld["y"] - 0.9, 0.0), proj(d, ld["y"] + 0.9, 1.45)
    scene.append(rect(bl[0], tr[1], tr[0] - bl[0], bl[1] - tr[1], fill="#2B2F36", stroke="none", rx=3))
    scene.append(rect(bl[0] + (tr[0] - bl[0]) * 0.1, tr[1] + (bl[1] - tr[1]) * 0.45, (tr[0] - bl[0]) * 0.18,
                      (bl[1] - tr[1]) * 0.12, fill="#C9343F", stroke="none", rx=1))
    scene.append(rect(bl[0] + (tr[0] - bl[0]) * 0.72, tr[1] + (bl[1] - tr[1]) * 0.45, (tr[0] - bl[0]) * 0.18,
                      (bl[1] - tr[1]) * 0.12, fill="#C9343F", stroke="none", rx=1))
  body.append(f'<defs><clipPath id="cam2"><rect x="{IX}" y="{IY}" width="{fmt_(iw)}" height="{fmt_(ih)}" rx="8"/></clipPath></defs>')
  # Chevrons by the UI's rules, at the lead's ground point.
  chev = []
  info = []
  for ld in LEADS:
    d, v = ld["d"], ld["v"]
    alpha = 0.0
    if d < ui["lead_buff"]:
      alpha = 255 * (1.0 - d / ui["lead_buff"])
      if v < 0:
        alpha += 255 * (-v / ui["speed_buff"])
      alpha = min(alpha, 255)
    sz = min(max(750 / (d / 3 + 30), ui["sz_min"]), ui["sz_max"]) * ui["sz_k"] * S
    x, y = proj(d, ld["y"])
    go, gy = sz / 5, sz / 10
    glow = [(x + sz * 1.35 + go, y + sz + gy), (x, y - gy), (x - sz * 1.35 - go, y + sz + gy)]
    cv = [(x + sz * 1.25, y + sz), (x, y), (x - sz * 1.25, y + sz)]
    chev.append(path("M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in glow) + " Z", stroke="none", fill="#DACA25"))
    chev.append(el("path", None, d="M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in cv) + " Z", fill="#C92231",
                   fill_opacity=fmt_(alpha / 255)))
    info.append((ld, alpha, sz / S, x, y + sz))
  body.append('<g clip-path="url(#cam2)">' + "".join(scene + chev) + "</g>")
  body.append(rect(IX, IY, iw, ih, fill="none", stroke=INK, sw=1.2))
  sp, _ = pill(IX + 14, IY + 14, "SYNTHETIC · data_kind: synthetic · credit: none", INK, size=10, h=20)
  body += sp
  for (ld, alpha, sz, x, y), (tx, ty) in zip(info, [(IX + 170, IY + ih - 40), (IX + iw - 170, IY + 120)]):
    body.append(line(x, y, tx, ty - 26, stroke=INK, sw=1))
    t1 = f"{ld['name']}: {'radar track' if ld['radar'] else 'vision-only'}"
    t2 = f"dRel {ld['d']:g} m, vRel {ld['v']:+g} m/s → opacity {alpha / 255:.2f}"
    if ld["name"] == "leadTwo":
      t1 += ", hidden behind leadOne"
    tw = max(text_w(t1, 11, True), text_w(t2, 10)) + 18
    body.append(rect(tx - tw / 2, ty - 30, tw, 38, fill="#FFFFFF", stroke=LINE, rx=6, opacity="0.95"))
    body.append(text(tx, ty - 14, t1, size=11, weight=700, anchor="middle"))
    body.append(text(tx, ty + 1, t2, size=10, fill=MUTED, anchor="middle"))
  cy = IY + ih + 22
  body.append(text(IX, cy, f"Chevron opacity: 1 − d/{ui['lead_buff']:g} m inside {ui['lead_buff']:g} m, plus closing speed / "
                   f"{ui['speed_buff']:g} m/s; none beyond {ui['lead_buff']:g} m, only the yellow glow.", size=11, fill=MUTED))
  body.append(text(IX, cy + 16, "Same camera and calibration as Figure 4 of the driving page; chevron sizes scaled to the "
                   "camera image, so approximate.", size=11, fill=MUTED))
  rx, rw = IX + iw + 36, W - 40 - (IX + iw + 36)
  body.append(rect(rx, IY, rw, 236, fill=SAFETY_BG, stroke=SAFETY, sw=1.4))
  body.append(text(rx + 14, IY + 24, "What the speed planner uses", size=14, weight=700, fill=SAFETY))
  for i, (k, v) in enumerate([("leadOne.dRel", "distance, m"), ("leadOne.vRel / vLead", "closing and lead speed"),
                              ("leadOne.aLeadK, aLeadTau", "lead acceleration and how fast it fades"),
                              ("leadOne.modelProb", "how sure the model is (FCW needs > 0.9)"),
                              ("leadOne.radar", "radar track or vision-only")]):
    body.append(text(rx + 14, IY + 52 + i * 36, k, size=12, weight=700, family=MONO))
    body.append(text(rx + 14, IY + 67 + i * 36, v, size=10.5, fill=MUTED))
  body.append(rect(rx, IY + 254, rw, 128, fill="#FFFFFF", stroke=LINE, sw=1.2))
  body.append(text(rx + 14, IY + 278, "What the picture does not show", size=14, weight=700))
  for i, s_ in enumerate(["whether the chevron is a radar track or the", "model's guess, or how sure either is. Both look",
                          "the same on screen; the safety analysis has to", "use the logged radarState, not the UI."]):
    body.append(text(rx + 14, IY + 300 + i * 16, s_, size=11, fill=MUTED))
  desc = ("A synthetic road-camera view of a straight highway with two cars ahead and the UI's lead chevrons: leadOne, a "
          f"radar track at {LEADS[0]['d']:g} m closing at {-LEADS[0]['v']:g} m/s, drawn opaque; leadTwo, vision-only at "
          f"{LEADS[1]['d']:g} m, beyond {ui['lead_buff']:g} m, drawn as a glow only. Beside it, the radarState fields the "
          "speed planner uses, and a note that the screen does not show which source a lead comes from.")
  return svg(W, int(max(cy + 36, IY + 400)), "Figure 4. Leads on screen, and the numbers behind them", desc, body)


# ---------------------------------------------------------------- Figure 5: driver-monitoring timing

def build_dm(f: dict) -> str:
  W = 1320
  body = header(W, "5", "Driver monitoring: from eyes off the road to the car slowing",
                "The alert timers of policy.py against the SG-08 budget of WP-S-04. Times count from the moment the "
                "driver stops watching.", "policy.py · WP-S-04 §3.7 · TSR-609, 633")
  x0, x1, span = 290, W - 40, 36.0

  def T(s: float) -> float:
    return x0 + (x1 - x0) * s / span
  rows = [("Camera sees the face", "vision policy", f["vision"], SW),
          ("Model unsure, or no camera", f"wheel-touch policy (after {f['fallback']:g} s with std > {f['hi_std']:g})",
           f["wheel"], AMBER)]
  y = 136
  for i, (t_, s_, al, col) in enumerate(rows):
    yy = y + i * 70
    body.append(text(40, yy + 4, t_, size=12, weight=700))
    body.append(text(40, yy + 19, s_, size=10, fill=MUTED))
    prev = 0.0
    for k, a in enumerate(al):
      body.append(rect(T(prev), yy - 8, T(a) - T(prev), 16, fill=[CHIP, "#FFF7E6", "#FDE2E2"][k], stroke=LINE, rx=0, sw=1))
      body.append(line(T(a), yy - 14, T(a), yy + 14, stroke=col, sw=2))
      body.append(text(T(a), yy - 18, f"alert {k + 1} · {a:g} s", size=10, fill=col, anchor="middle", weight=600))
      prev = a
    dec = al[-1] + f["no_resp"]
    body.append(rect(T(al[-1]), yy - 8, T(dec) - T(al[-1]), 16, fill="#FDE2E2", stroke=RED, rx=0, sw=1, dash="3 2"))
    body.append(line(T(dec), yy - 14, T(dec), yy + 14, stroke=RED, sw=2))
    body.append(text(T(dec) + 6, yy + 4, f"forced deceleration · {dec:g} s", size=10.5, fill=RED, weight=600))
  bottom = y + 2 * 70 - 20
  ftti = 6.0
  body.append(line(T(ftti), y - 32, T(ftti), bottom, stroke=RED, sw=1.6, dash="5 3"))
  body.append(text(T(ftti) + 6, bottom - 4, f"SG-08: first alert ≤ {ftti:g} s", size=10.5, fill=RED, weight=700))
  for s in range(0, int(span) + 1, 5):
    body.append(text(T(s), bottom + 18, f"{s} s", size=9.5, fill=MUTED, anchor="middle"))
  d = f["dist"]
  body.append(text(40, bottom + 44, f"At speed the wheel-touch alerts also come by distance: {d[0]:g}, {d[1]:g} and {d[2]:g} m "
                   f"(LionDriver, TSR-634), about the vision times at 110 km/h. No alerts below {f['min_speed'] * 3.6:.0f} km/h.",
                   size=11, fill=MUTED))
  y2 = bottom + 74
  body.append(text(40, y2, "WHERE IT FALLS SHORT", size=12, weight=700, fill=SW))
  items = [("Latency not measured", "the first vision alert is at 5 s plus the DM frame and model latency, which is not "
            "measured; the 1 s margin to the 6 s budget is TBD (OI-11)"),
           ("DM output never invalid", "driverStateV2 is always valid=True, so the TSR-609 take-over request on an invalid "
            "DM output (≤ 2 s) cannot happen"),
           ("Safe stop not verified", "after the terminal alert the item stops in lane and stays held until the driver "
            "takes over (TSR-633); not verified on the car, and the PCM hold is assumed (AOU-16)"),
           ("Lockout", f"repeated terminal alerts lock out engagement for {', '.join(map(str, f['lockout']))} min, "
            "counted from the takeover")]
  for i, (t_, s_) in enumerate(items):
    body.append(text(40, y2 + 24 + i * 34, t_, size=11.5, weight=700))
    body.append(text(250, y2 + 24 + i * 34, fit(s_, W - 290, 10.5), size=10.5, fill=MUTED))
  desc = (f"Two timelines from loss of attention: vision policy alerts at {', '.join(f'{a:g}' for a in f['vision'])} s and "
          f"forced deceleration {f['no_resp']:g} s after the terminal alert; wheel-touch policy at "
          f"{', '.join(f'{a:g}' for a in f['wheel'])} s. The SG-08 budget is a first alert within {ftti:g} s. Below: latency "
          "not measured, DM output never invalid (TSR-609), safe stop not verified on the car (TSR-633, AOU-16), lockout.")
  return svg(W, int(y2 + 24 + len(items) * 34), "Figure 5. Driver monitoring: from eyes off the road to the car slowing",
             desc, body)


# ---------------------------------------------------------------- main

def build_all() -> dict[str, str]:
  gone = problems()
  if gone:
    raise SourceError("perception figure sources changed:\n" + "\n".join(gone) + "\nreview fig_perception.py")
  air = airs()
  return {OUTS["pipeline"]: build_pipeline(air, model_inputs()), OUTS["fusion"]: build_fusion(radard_facts()),
          OUTS["fi"]: build_fi(insufficiencies()), OUTS["overlay"]: build_overlay(fd.overlay_facts(), ui_facts()),
          OUTS["dm"]: build_dm(dm_facts())}


def main(argv: list[str]) -> int:
  out = build_all()
  if "--check" in argv:
    stale = [n for n, s in out.items() if not (OUT_DIR / n).exists() or (OUT_DIR / n).read_text(encoding="utf-8") != s]
    if stale:
      print("stale: " + ", ".join(stale) + "\nrun: python3 docs/liondriver/figures/fig_perception.py", file=sys.stderr)
      return 1
    print(f"fig_perception: {len(out)} figures current")
    return 0
  for n, s in out.items():
    (OUT_DIR / n).write_text(s, encoding="utf-8")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
