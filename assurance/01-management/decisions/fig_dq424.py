#!/usr/bin/env python3
"""Draw the DQ-424 decision-card chart (`figures/dq-424.svg`): speed over time in the unresponsive-driver stop.

The card asks how firmly the car brakes when the driver does not respond (TSR-633). The chart shows one speed curve
per option, from the start speed to standstill, labelled with its letter and the computed stop time and distance.

Every number is read from its record at build time:

- start speed and option A's rate, "ramped in within j_down": TSR-633 in WP-S-02;
- j_down and the host's final-command rate limit: TSR-624 in WP-S-02 ("below j_down = 5 m/s³ of WP-W-02 §2.5"),
  which must equal the j_down row of WP-W-02 §2.5;
- option B's rate: `A_CRUISE_MIN` in openpilot's `longitudinal_planner.py` (today's planner minimum), which must
  equal the rate in option B's title;
- option C's rate and the time and distance each option states ("about 15 s and 230 m"): the DQ-424 options in
  register.yaml; A's are also stated by TSR-633 and the SG-08 no-response row of WP-S-04 §3.7.

Option A ramps in at j_down, the steepest the requirement allows; B and C brake at a constant rate, as their options
describe. `--check` fails when a source text is gone, when a computed stop time or distance no longer agrees with
what the documents state (within ABOUT_S and ABOUT_FRAC), when an end label would cross a line, another label or the
edge, when the register no longer names the figure, or when the committed SVG is stale.

The SVG is inlined into the inbox page by build_inbox.py, so it uses the page's colour classes and brings no
<style> of its own (assurance-chart references/decision-cards.md).

    python3 fig_dq424.py            # write the SVG
    python3 fig_dq424.py --check    # fail if a source changed, the numbers disagree or the SVG is stale

Standard library (and PyYAML, as check_decisions.py). Output is deterministic.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REGISTER = HERE / "register.yaml"
OUT = HERE / "figures" / "dq-424.svg"
WP_S02 = ROOT / "assurance/03-system/WP-S-02-technical-safety-requirements.md"
WP_S04 = ROOT / "assurance/03-system/WP-S-04-timing-ftti-budget.md"
WP_W02 = ROOT / "assurance/05-software/WP-W-02-software-safety-requirements.md"
PLANNER = ROOT / "openpilot/selfdrive/controls/lib/longitudinal_planner.py"
ENTRY = "DQ-424"
sys.path.insert(0, str(HERE.parents[0] / "figures"))
from figkit import FigureError, el, fmt, section, table, text_w

ABOUT_S = 0.6     # "about 15 s": the computed stop time is within this of the stated whole second
ABOUT_FRAC = 0.05  # "about 230 m": the computed distance is within 5 % of the stated one

W = 640
X0, X1 = 70, 620           # plot area
Y_TOP, Y_BASE = 60, 200
SIZE = {"title": 12, "key": 12, "tick": 12, "end": 13, "note": 12}
STYLE = {  # option role -> (line colour, width, dash, text class)
  "recommended": ("var(--accent)", 3.5, "", "s-acc"),
  "today": ("var(--muted)", 2, "6 4", "s-muted"),
  "worst": ("var(--bad)", 2, "", "s-bad"),
}


# ---------------------------------------------------------------- sources

def _one(pattern: str, text: str, what: str) -> re.Match:
  m = re.search(pattern, text)
  if not m:
    raise FigureError(f"source text no longer found: {what} (pattern {pattern!r})")
  return m


def _row(md: str, rid: str) -> str:
  rows = [ln for ln in md.splitlines() if ln.startswith(f"| {rid} |") and " shall " in ln]
  if len(rows) != 1:
    raise FigureError(f"WP-S-02: expected one requirement row {rid}, found {len(rows)}")
  return rows[0]


def entry(path: Path = REGISTER) -> dict:
  sys.path.insert(0, str(HERE))
  from check_decisions import load
  hits = [d for d in load(path) if d.get("id") == ENTRY]
  if len(hits) != 1:
    raise FigureError(f"register: expected one {ENTRY}, found {len(hits)}")
  return hits[0]


def sources(s02: str | None = None, s04: str | None = None, w02: str | None = None, planner: str | None = None,
            dq: dict | None = None) -> dict:
  """Every number the chart draws or checks, read from the records."""
  s02 = s02 if s02 is not None else WP_S02.read_text(encoding="utf-8")
  s04 = s04 if s04 is not None else WP_S04.read_text(encoding="utf-8")
  w02 = w02 if w02 is not None else WP_W02.read_text(encoding="utf-8")
  planner = planner if planner is not None else PLANNER.read_text(encoding="utf-8")
  dq = dq if dq is not None else entry()

  tsr633 = _row(s02, "TSR-633")
  m = _one(r"decelerate in lane to a standstill at ([\d.]+) m/s², ramped in within j_down", tsr633,
           "TSR-633 rate, ramped in within j_down")
  rate_a = float(m.group(1))
  m = _one(r"about (\d+) s and (\d+) m from (\d+) km/h", tsr633, "TSR-633 stop time, distance and start speed")
  tsr_stated = (float(m.group(1)), float(m.group(2)))
  v0_kmh = float(m.group(3))

  tsr624 = _row(s02, "TSR-624")
  j_down = float(_one(r"below j_down = ([\d.]+) m/s³ of WP-W-02 §2\.5", tsr624, "TSR-624 j_down").group(1))
  j_host = float(_one(r"rate-limited to ([\d.]+) m/s³", tsr624, "TSR-624 host final-command rate").group(1))
  head, rows = table(section(w02, "### 2.5"), "Symbol")
  vals = [r[head.index("Provisional value")] for r in rows if r and r[0] == "j_down"]
  if len(vals) != 1:
    raise FigureError("WP-W-02 §2.5: expected one j_down row")
  j_w02 = float(_one(r"^([\d.]+) m/s³", vals[0], "WP-W-02 §2.5 j_down value").group(1))
  if j_w02 != j_down:
    raise FigureError(f"j_down differs: TSR-624 {j_down} m/s³, WP-W-02 §2.5 {j_w02} m/s³")

  row37 = [r for r in table(section(s04, "### 3.7"), "SG / fault class")[1] if r[0].startswith("SG-08 no-response")]
  if len(row37) != 1:
    raise FigureError("WP-S-04 §3.7: expected one 'SG-08 no-response' row")
  m = _one(r"standstill about (\d+) s and (\d+) m later from (\d+) km/h at ([\d.]+) m/s², ramped in", row37[0][1],
           "WP-S-04 §3.7 SG-08 no-response standstill")
  s04_stated = (float(m.group(1)), float(m.group(2)))
  if float(m.group(3)) != v0_kmh or float(m.group(4)) != rate_a:
    raise FigureError(f"WP-S-04 §3.7 states {m.group(4)} m/s² from {m.group(3)} km/h; TSR-633 {rate_a} from {v0_kmh}")

  m = re.search(r"^A_CRUISE_MIN = (-?[\d.]+)\s*$", planner, re.M)
  if not m:
    raise FigureError("longitudinal_planner.py: A_CRUISE_MIN not found")
  a_cruise_min = float(m.group(1))

  if f"from {fmt(v0_kmh)} km/h" not in " ".join(str(dq.get(k, "")) for k in ("context", "caption")):
    raise FigureError(f"{ENTRY}: context or caption no longer says 'from {fmt(v0_kmh)} km/h'")
  opts = dq.get("options") or []
  if [o.get("key") for o in opts] != ["A", "B", "C"]:
    raise FigureError(f"{ENTRY}: options are {[o.get('key') for o in opts]}, the chart draws A, B, C")
  if [bool(o.get("recommended")) for o in opts] != [True, False, False]:
    raise FigureError(f"{ENTRY}: the chart draws A as the recommended option")
  options = []
  for o in opts:
    t = str(o.get("title", ""))
    rate = float(_one(r"([\d.]+) m/s²", t, f"{ENTRY} option {o['key']} rate").group(1))
    m = _one(r"about (\d+) s and (\d+) m", t, f"{ENTRY} option {o['key']} time and distance")
    options.append({"key": o["key"], "title": t, "rate": rate, "stated": (float(m.group(1)), float(m.group(2)))})
  a, b, c = options
  if a["rate"] != rate_a or "ramped in" not in a["title"]:
    raise FigureError(f"{ENTRY} option A ({a['title']!r}) differs from TSR-633 ({rate_a} m/s², ramped in)")
  if b["rate"] != -a_cruise_min or "Keep" not in b["title"]:
    raise FigureError(f"{ENTRY} option B ({b['title']!r}) is not today's A_CRUISE_MIN = {a_cruise_min}")
  a.update(role="recommended", jerk=j_down, word="ramped in")
  b.update(role="today", jerk=None, word="today")
  c.update(role="worst", jerk=None, word="")
  return {"v0_kmh": v0_kmh, "j_down": j_down, "j_host": j_host, "options": options,
          "stated_a": {"TSR-633": tsr_stated, "WP-S-04 §3.7": s04_stated, f"{ENTRY} A": a["stated"]},
          "figure": dq.get("figure"), "caption": dq.get("caption")}


# ---------------------------------------------------------------- kinematics

def stop(v0: float, a: float, jerk: float | None) -> tuple[float, float, float]:
  """(stop time s, stop distance m, ramp time s) from v0 m/s at deceleration a, ramped in at jerk if given."""
  tr = a / jerk if jerk else 0.0
  v1 = v0 - jerk * tr * tr / 2 if jerk else v0
  d_ramp = v0 * tr - jerk * tr ** 3 / 6 if jerk else 0.0
  return tr + v1 / a, d_ramp + v1 * v1 / (2 * a), tr


def speed(t: float, v0: float, a: float, jerk: float | None) -> float:
  tr = a / jerk if jerk else 0.0
  if t < tr:
    return max(0.0, v0 - jerk * t * t / 2)
  v1 = v0 - (jerk * tr * tr / 2 if jerk else 0.0)
  return max(0.0, v1 - a * (t - tr))


def computed(src: dict) -> list[dict]:
  v0 = src["v0_kmh"] / 3.6
  out = []
  for o in src["options"]:
    t, d, tr = stop(v0, o["rate"], o["jerk"])
    out.append({**o, "t": t, "d": d, "ramp": tr, "label": f"{o['key']} · {round(t)} s, {5 * round(d / 5)} m"})
  return out


def agrees(t: float, d: float, stated: tuple[float, float]) -> bool:
  return abs(t - stated[0]) <= ABOUT_S and abs(d - stated[1]) <= ABOUT_FRAC * stated[1]


# ---------------------------------------------------------------- layout

def axis(src: dict, opts: list[dict]):
  t_max = math.ceil(max(o["t"] for o in opts) + 0.5)
  def x(t): return X0 + (X1 - X0) * t / t_max
  def y(kmh): return Y_BASE - (Y_BASE - Y_TOP) * kmh / src["v0_kmh"]
  return t_max, x, y


def points(o: dict, src: dict, x, y) -> list[tuple[float, float]]:
  v0 = src["v0_kmh"] / 3.6
  ts = [k * 0.05 for k in range(int(o["ramp"] / 0.05) + 1)] if o["ramp"] else [0.0]
  ts += [o["ramp"], o["t"]] if o["ramp"] else [o["t"]]
  return [(x(t), y(speed(t, v0, o["rate"], o["jerk"]) * 3.6)) for t in ts]


def _hits(box, segs, pad=3.0) -> bool:
  x0, y0, x1, y1 = box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad
  for (ax, ay), (bx, by) in segs:
    for k in range(41):
      px, py = ax + (bx - ax) * k / 40, ay + (by - ay) * k / 40
      if x0 <= px <= x1 and y0 <= py <= y1:
        return True
  return False


def place(opts: list[dict], lines: dict[str, list[tuple[float, float]]]) -> dict[str, tuple[float, float, str, tuple]]:
  """End label per option: the clear spot nearest its end dot, inside the viewBox, crossing no line and no other
  label. Raises FigureError if there is none."""
  segs = [s for pts in lines.values() for s in zip(pts, pts[1:], strict=False)]
  dots = [(pts[-1][0] - 6, pts[-1][1] - 6, pts[-1][0] + 6, pts[-1][1] + 6) for pts in lines.values()]
  placed: dict[str, tuple[float, float, str, tuple]] = {}
  size = SIZE["end"]
  for o in opts:
    ex, ey = lines[o["key"]][-1]
    w = text_w(o["label"], size, True)
    best = None
    for yb in (ey - 8, ey - 26, ey - 44, ey - 62):
      for k in range(-20, 21):
        lx = ex + 8 + 10 * k  # left edge of the label
        box = (lx, yb - size, lx + w, yb + 3)
        if box[0] < 0 or box[2] > W - 2:
          continue
        if _hits(box, segs) or any(_overlap(box, b) for b in dots + [p[3] for p in placed.values()]):
          continue
        dist = math.hypot(max(box[0] - ex, 0, ex - box[2]), max(box[1] - ey, 0, ey - box[3]))
        if best is None or dist < best[0] - 1e-9:
          best = (dist, (lx, yb, "start", box))
    if best is None:
      raise FigureError(f"no clear place for the end label {o['label']!r}")
    placed[o["key"]] = best[1]
  return placed


def _overlap(a, b, pad=3.0) -> bool:
  return not (a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1])


# ---------------------------------------------------------------- figure

def T(x, y, s, cls, size, weight="", anchor="", spacing="") -> str:
  return el("text", s, x=fmt(x), y=fmt(y), class_=cls, font_size=size, font_weight=weight, text_anchor=anchor,
            letter_spacing=spacing)


def build(src: dict | None = None) -> str:
  src = src if src is not None else sources()
  opts = computed(src)
  t_max, x, y = axis(src, opts)
  a, b, c = opts
  v0 = src["v0_kmh"]
  lines = {o["key"]: points(o, src, x, y) for o in opts}
  labels = place(opts, lines)

  body = [T(0, 14, f"UNRESPONSIVE DRIVER: SPEED AFTER THE STOP STARTS, FROM {fmt(v0)} KM/H", "s-muted",
            SIZE["title"], 600, spacing=".06em")]
  key = []
  for i, o in enumerate(opts):
    note = {"recommended": f"{o['word']}, recommended", "today": o["word"], "worst": ""}[o["role"]]
    s = f"{o['key']} {fmt(o['rate'])} m/s²" + (f" ({note})" if note else "")
    key.append(el("tspan", s, class_=STYLE[o["role"]][3], dx=14 if i else ""))
  body.append(f'<text x="0" y="34" font-size="{SIZE["key"]}" font-weight="700">{"".join(key)}</text>')
  for t in range(0, t_max + 1, 5):
    body.append(el("line", None, x1=fmt(x(t)), y1=Y_TOP - 12, x2=fmt(x(t)), y2=Y_BASE, stroke="var(--line)",
                   stroke_width=1))
    body.append(T(x(t), Y_BASE + 18, f"{t} s", "s-muted", SIZE["tick"], anchor="middle"))
  for kmh in sorted({0.0, 50.0, v0}):
    body.append(T(X0 - 8, y(kmh) + 4, f"{fmt(kmh)} km/h", "s-muted", SIZE["tick"], anchor="end"))
  body.append(el("line", None, x1=X0, y1=Y_BASE, x2=X1, y2=Y_BASE, stroke="var(--ink)", stroke_width=1))
  for o in sorted(opts, key=lambda o: o["role"] == "recommended"):  # the recommended line on top
    colour, width, dash, cls = STYLE[o["role"]]
    pts = lines[o["key"]]
    d = "M" + " L".join(f"{fmt(px)},{fmt(py)}" for px, py in pts)
    body.append(el("path", None, d=d, fill="none", stroke=colour, stroke_width=width, stroke_dasharray=dash,
                   stroke_linejoin="round"))
    ex, ey = pts[-1]
    body.append(el("circle", None, cx=fmt(ex), cy=fmt(ey), r=4.5, fill=colour))
    lx, yb, anchor, _box = labels[o["key"]]
    body.append(T(lx, yb, o["label"], cls, SIZE["end"], 700, anchor=anchor if anchor == "end" else ""))
  plain_a = stop(v0 / 3.6, a["rate"], None)
  note1 = (f"A ramps in at j_down = {fmt(src['j_down'])} m/s³ over {a['ramp']:.1f} s, which adds " +
           f"{a['t'] - plain_a[0]:.1f} s and {round(a['d'] - plain_a[1])} m; B and C brake at a constant rate.")
  note2 = "Kinematic estimate from TSR-633 and the options, not a measurement."
  yn = Y_BASE + 46
  body += [T(0, yn, note1, "s-muted", SIZE["note"]), T(0, yn + 18, note2, "s-muted", SIZE["note"])]
  h = int(yn + 18 + 8)
  title = (f"Speed after the in-lane stop starts, from {fmt(v0)} km/h: " +
           "; ".join(f"{o['key']}, {fmt(o['rate'])} m/s²{' ramped in at ' + fmt(o['jerk']) + ' m/s³' if o['jerk'] else ''}" +
                     f"{' (today)' if o['role'] == 'today' else ''}, stops after {o['t']:.1f} s and {round(o['d'])} m"
                     for o in opts))
  head = f'<svg viewBox="0 0 {W} {h}" role="img" aria-labelledby="dq424t">'
  return "\n".join([head, el("title", title, id="dq424t"), *body, "</svg>"]) + "\n"


def problems(src: dict | None = None) -> list[str]:
  """Disagreements between the computed stops and what the documents state; an unplaceable label."""
  try:
    src = src if src is not None else sources()
    opts = computed(src)
  except FigureError as e:
    return [str(e)]
  out = []
  for o in opts:
    if not agrees(o["t"], o["d"], o["stated"]):
      out.append(f"option {o['key']}: computed {o['t']:.1f} s and {o['d']:.0f} m, the option states about " +
                 f"{fmt(o['stated'][0])} s and {fmt(o['stated'][1])} m")
  a = opts[0]
  for where, stated in src["stated_a"].items():
    if not agrees(a["t"], a["d"], stated):
      out.append(f"{where}: states about {fmt(stated[0])} s and {fmt(stated[1])} m, computed {a['t']:.1f} s and " +
                 f"{a['d']:.0f} m")
  t_h, d_h, _ = stop(src["v0_kmh"] / 3.6, a["rate"], src["j_host"])
  if not agrees(t_h, d_h, a["stated"]):
    out.append(f"option A at the host rate {src['j_host']} m/s³: {t_h:.1f} s and {d_h:.0f} m disagree with the option")
  if src["figure"] != f"figures/{OUT.name}" or not src["caption"]:
    out.append(f"{ENTRY} no longer names figures/{OUT.name} with a caption")
  try:
    build(src)
  except FigureError as e:
    out.append(str(e))
  return out


def main(argv: list[str]) -> int:
  try:
    src = sources()
  except FigureError as e:
    print(f"fig_dq424: {e}", file=sys.stderr)
    return 1
  errs = problems(src)
  out = build(src) if not errs else ""
  if "--check" in argv:
    if not errs and (not OUT.exists() or OUT.read_text(encoding="utf-8") != out):
      errs.append(f"{OUT.name} is stale; run assurance/01-management/decisions/fig_dq424.py")
    for e in errs:
      print(f"fig_dq424: {e}", file=sys.stderr)
    if not errs:
      print("fig_dq424: figure current; " + "; ".join(f"{o['key']} {o['t']:.1f} s {o['d']:.0f} m"
                                                       for o in computed(src)) + " agree with the documents")
    return 1 if errs else 0
  if errs:
    for e in errs:
      print(f"fig_dq424: {e}", file=sys.stderr)
    return 1
  OUT.write_text(out, encoding="utf-8")
  print(f"fig_dq424: wrote {OUT.name}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
