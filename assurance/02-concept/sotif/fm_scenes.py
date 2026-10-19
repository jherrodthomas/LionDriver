#!/usr/bin/env python3
"""Draw the SOTIF modification sheets: one card per functional modification of WP-C-07, today against the same scene with it.

`../figures/fig-c07-3-1-fm-scenes-p1.svg` holds the P1 modifications and `fig-c07-3-2-fm-scenes-p2-p3.svg` the rest, in
WP-C-07 §2 order. Each card shows:

- a chart on one time axis: red is what the car does today, green is what it does with the modification, and the
  difference between them is shaded green;
- the same road scene twice, TODAY above and WITH FM-nn below (SMIL, no script, 6 s loop; a viewer that does not
  animate shows the last frame);
- what today's behaviour is, then the Change, Expected risk reduction and Verification cells of the WP-C-07 §3 table,
  and what the documents record about its implementation.

Title chips (priority, GAP, the SOTIF hazards addressed) come from WP-C-07 §2. Every "today" and "status" text quotes
the documents: each card lists the passages it relies on, and the build fails if one is no longer there. The behaviour
curves are schematic: they explain each modification and are not simulation results.

The build also fails if a §2 modification has no card or a card has no §2 row, if §2 and §3 disagree on the priority,
or if a card's hazard is not one §2 says the modification addresses. Built and checked by `sotif_figures.py`.

Standard library only. Drawing helpers come from sotif_scenes.py and ../hara/.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hara"))
import hara_figures as hf  # noqa: E402
import sotif_figures as sf  # noqa: E402
import sotif_scenes as ss  # noqa: E402
from guideword_scenes import _car_body  # noqa: E402
from hara_figures import HAIR, INK, MUTED, pill, svg_doc, t, wrap  # noqa: E402
from sotif_scenes import CG, CR, EGO, EGO_S, GREY, GREY_S, appear, drive, frame, line, marker, sample, trail, xt  # noqa: E402

C02 = HERE.parent / "WP-C-02-odd-and-intended-functionality.md"
C04 = HERE.parent / "WP-C-04-functional-safety-concept.md"
C07 = HERE.parent / "WP-C-07-sotif-functional-modifications.md"
GAPS = HERE.parent.parent / "00-assessment" / "gap-assessment.md"
SHEETS = {"fig-c07-3-1-fm-scenes-p1.svg": ("3-1", "P1 modifications", ["P1"]),
          "fig-c07-3-2-fm-scenes-p2-p3.svg": ("3-2", "P2 and P3 modifications", ["P2", "P3"])}
PRIO = {"P1": ("#FEE2E2", "#7F1D1D", "P1 · before on-road use"), "P2": ("#FEF3C7", "#78350F", "P2 · before G5 release"),
        "P3": ("#E0F2FE", "#075985", "P3 · decide at G2")}
STATUS = {"open": ("#E2E8F0", "#334155", "No implementation recorded"), "gap": ("#FFEDD5", "#7C2D12", "Open, recorded"),
          "decided": ("#EDE9FE", "#4C1D95", "Decided, not implemented"), "partial": ("#DCFCE7", "#14532D", "Partly implemented")}
GREEN_FILL = "#16A34A"


# ---------------------------------------------------------------- documents

def load(md: str | None = None) -> dict:
  """WP-C-07 §2 and §3 (md, by default the file), and the other documents a card may quote."""
  md = C07.read_text(encoding="utf-8") if md is None else md
  summary = {}
  for ln in sf._section(md, 2, "WP-C-07").splitlines():
    if re.match(r"^\| FM-\d\d \|", ln):
      c = sf._cells(ln)
      summary[c[0]] = dict(title=c[1], sh=sf._ids(c[2], "SH"), gap=sf._ids(c[3], "GAP"), prio=c[4])
  table, cur = {}, None
  for ln in sf._section(md, 3, "WP-C-07").splitlines():
    if m := re.match(r"^### (FM-\d\d) ", ln):
      cur = table.setdefault(m.group(1), {})
    elif cur is not None and ln.startswith("| ") and not ln.startswith("| Attribute") and not ln.startswith("|---"):
      c = sf._cells(ln)
      cur[c[0]] = c[1]
  for fm, s in summary.items():
    if fm not in table:
      raise sf.FigureError(f"WP-C-07: {fm} is in §2 but has no §3 table")
    if table[fm].get("Priority") != s["prio"]:
      raise sf.FigureError(f"WP-C-07: {fm} priority is {s['prio']} in §2 but {table[fm].get('Priority')} in §3")
  return dict(summary=summary, table=table, text={"WP-C-07": md, "WP-C-02": C02.read_text(encoding="utf-8"),
                                                  "WP-C-04": C04.read_text(encoding="utf-8"),
                                                  "gap-assessment": GAPS.read_text(encoding="utf-8")})


def _plain(s: str) -> str:
  s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)                  # [text](link) -> text
  return re.sub(r"\*+([^*]+)\*+", r"\1", s).replace("`", "")


def quoted(docs: dict, fm: str, src) -> None:
  """Each (where, passage) must be in the document: "FM-nn.Attribute" names a WP-C-07 §3 cell, else a whole document."""
  for where, passage in src:
    if m := re.fullmatch(r"(FM-\d\d)\.(.+)", where):
      hay = docs["table"].get(m.group(1), {}).get(m.group(2))
      if hay is None:
        raise sf.FigureError(f"{fm}: WP-C-07 §3 has no cell {where}")
    elif where in docs["text"]:
      hay = docs["text"][where]
    else:
      raise sf.FigureError(f"{fm}: unknown source {where}")
    if _plain(passage) not in _plain(hay):
      raise sf.FigureError(f"{fm}: {where} no longer says {passage!r}; redraw the card from the current text")


# ---------------------------------------------------------------- scene strip (280 x 70): ego lane centre y 51, next lane above

LANE, NEXT, X0, X1 = 51, 28, 14, 262


def road(markings=True):
  b = ['<rect width="280" height="70" fill="#C9DDBA"/>', '<rect x="0" y="12" width="280" height="56" fill="#B9C7A6"/>',
       '<rect x="0" y="14" width="280" height="52" fill="#565E69"/>']
  if markings:
    b += ['<line x1="0" y1="16" x2="280" y2="16" stroke="#F8FAFC" stroke-width="1.5"/>',
          '<line x1="0" y1="64" x2="280" y2="64" stroke="#F8FAFC" stroke-width="1.5"/>',
          '<line x1="0" y1="39.5" x2="280" y2="39.5" stroke="#F8FAFC" stroke-width="1.3" stroke-dasharray="9 9"/>']
  return b


def badge(s, col):
  w = hf.text_w(s, 7, True) + 10
  return f'<rect x="3" y="1.5" width="{w:.1f}" height="10" rx="3" fill="{col}"/>' + t(8, 9, s, 7, "#FFFFFF", 700)


def tag(f, x, y, s, col, anchor="middle"):
  """A label that appears at f of the drive; light text on a dark halo, kept inside the strip."""
  w = hf.text_w(s, 7.5, True)
  if anchor == "middle":
    x = min(276 - w / 2, max(4 + w / 2, x))
  elif anchor == "start":
    x = min(276 - w, max(4, x))
  else:
    x = min(276, max(4 + w, x))
  return (f"<g>{appear(f)}" + t(round(x, 1), y, s, 7.5, col, 700, anchor,
                                ' stroke="#1F242B" stroke-width="2.6" paint-order="stroke"') + "</g>")


def ego(path, col=CR):
  return [trail(path, col, 2.2), drive(path, _car_body(EGO, EGO_S))]


def other(path):
  return drive(path, _car_body(GREY, GREY_S))


def still(x, y):
  return ss.car(x, y, 0, GREY, GREY_S)


def straight_path(x0=X0, x1=X1, y=LANE, until=1.0):
  return sample(lambda f: (x0 + (x1 - x0) * min(f, until) / until if until else x0, y))


def drifting(f0, dy, y=LANE, x0=X0, x1=X1, k=2.0):
  """Straight until f0, then off by dy (curving in); dy < 0 is towards the next lane."""
  return sample(lambda f: (x0 + (x1 - x0) * f, y + (dy * min(1, ((f - f0) / (1 - f0))) ** k if f > f0 else 0)))


GOOD, BAD, NOTE = "#86EFAC", "#FCA5A5", "#FDE68A"


# ---------------------------------------------------------------- charts (280 x 110), red today, green with the modification

def removed(today, fm):
  """Shade the difference between two series [(f, y)] on any f grids."""
  pts = [(xt(f), y) for f, y in today] + [(xt(f), y) for f, y in fm[::-1]]
  return f'<path d="{ss._d(pts)} Z" fill="{GREEN_FILL}" opacity="0.16"/>'


def chart(ylabel, ticks, today, fm, notes=(), extra=()):
  return (frame(ylabel, ticks) + list(extra) + [removed(today, fm), line(today, CR), line(fm, CG)] +
          [t(xt(f), y, s, 7, col, 600, anchor) for f, y, s, col, anchor in notes])


def lim(y, s):
  return ss.limit(y, s)


# ---------------------------------------------------------------- one model per modification

def fm01():
  """Experimental Mode: the end-to-end planner stops for a light that is not there; Chill keeps the cruise."""
  stop = 0.38
  xs = lambda f: X0 + 248 * (f if f < stop else stop + (f - stop) * (1 - (f - stop) / (1 - stop) / 2) * 0.32)
  today = sample(lambda f: (xs(f), LANE))
  follow = sample(lambda f: (min(xs(f) - 26, X0 - 30 + 248 * 0.92 * f), LANE))
  ch = chart("speed", [(24, "cruise"), (96, "0")], [(0, 24), (stop, 24), (stop + 0.12, 70), (1, 74)], [(0, 24), (1, 24)],
             [(stop + 0.14, 62, "Experimental on (owner): false stop", CR, "start"), (0.5, 20, "Chill: cruise held", CG, "middle")])
  sc_today = road() + [other(follow)] + ego(today) + [marker(xs(stop), LANE, stop), badge("TODAY", CR),
                                                     tag(stop, xs(stop), 34, "Experimental on: phantom stop", BAD),
                                                     tag(0.8, 140, 66, "follower closes in", NOTE)]
  fm_path = straight_path()
  sc_fm = road() + [other(sample(lambda f: (X0 - 30 + 248 * f, LANE)))] + ego(fm_path, CG) + [
    badge("WITH FM-01", CG), tag(stop, 120, 34, "Chill locked: no end-to-end stop", GOOD)]
  return ch, sc_today, sc_fm


def fm02():
  """Model fails while engaged: diagnostics masked, hot switch to a cold model; with FM-02, a take-over request."""
  f0 = 0.3
  ch = chart("diagnostics active", [(24, "on"), (90, "off")], [(0, 24), (f0, 24), (f0 + 0.01, 90), (1, 90)],
             [(0, 24), (1, 24)],
             [(f0 + 0.03, 84, "masked while the model loads, + 5 s", CR, "start"),
              (0.62, 20, "failure: take-over request", CG, "middle")])
  sc_today = road() + ego(drifting(f0, -11)) + [marker(X0 + 248 * f0, LANE, f0), badge("TODAY", CR),
                                                tag(f0, X0 + 248 * f0, 66, "model fails: cold model, no alert", BAD)]
  sc_fm = road() + ego(straight_path(until=1.0), CG) + [marker(X0 + 248 * f0, LANE, f0), badge("WITH FM-02", CG),
                                                        tag(f0 + 0.05, 160, 34, "take over now (no hot switch)", GOOD)]
  return ch, sc_today, sc_fm


def fm03():
  """An input goes stale: today soft disable keeps actuating on it; with FM-03, take over now and torque ramps down."""
  s = lambda sec: 0.05 + 0.9 * sec / 4                       # 0..4 s on the chart
  ch = chart("acting on stale input", [(24, "yes"), (96, "no")],
             [(0, 96), (s(0), 96), (s(0) + .001, 24), (s(3.5), 24), (s(3.5) + .001, 96), (1, 96)],
             [(0, 96), (s(0), 96), (s(0) + .001, 24), (s(0.4), 24), (s(0.4) + .001, 96), (1, 96)],
             [(s(1.8), 20, "warning + 10× alive window: ≈3.5 s", CR, "middle"),
              (s(0.5), 60, "freshness bound from the FTTI", CG, "start")],
             [t(xt(s(3.5)), 105, "3.5 s", 7, MUTED, None, "middle")])
  f0 = 0.25
  sc_today = road() + ego(drifting(f0, 8)) + [marker(X0 + 248 * f0, LANE, f0), badge("TODAY", CR),
                                              tag(f0, X0 + 248 * f0, 34, "input stale", NOTE),
                                               tag(0.85, 200, 34, "still steering, ≈100 m", BAD)]
  stop = sample(lambda f: (X0 + 248 * (f if f < f0 else f0 + (f - f0) * 0.45), LANE))
  sc_fm = road() + ego(stop, CG) + [marker(X0 + 248 * f0, LANE, f0), badge("WITH FM-03", CG),
                                    tag(f0, X0 + 248 * f0, 34, "input stale", NOTE),
                                    tag(f0 + 0.05, 190, 34, "take over · torque to 0", GOOD)]
  return ch, sc_today, sc_fm


def fm04():
  """PCM cruise state and openpilot disagree: today an event with no reaction; with FM-04, cancel and disable."""
  f0 = 0.25
  ch = chart("mismatch unhandled", [(24, "yes"), (96, "no")], [(0, 96), (f0, 96), (f0 + .001, 24), (1, 24)],
             [(0, 96), (f0, 96), (f0 + .001, 24), (0.62, 24), (0.62 + .001, 96), (1, 96)],
             [(0.95, 20, "no reaction", CR, "end"), (0.64, 90, "cancel repeated, then disable", CG, "start")])
  sc_today = road() + ego(straight_path()) + [marker(X0 + 248 * f0, LANE, f0), badge("TODAY", CR),
                                              tag(f0, X0 + 248 * f0, 34, "cruiseMismatch", NOTE),
                                              tag(0.7, 200, 34, "event raised, nothing happens", BAD)]
  slow = sample(lambda f: (X0 + 248 * (f if f < 0.62 else 0.62 + (f - 0.62) * 0.5), LANE))
  sc_fm = road() + ego(slow, CG) + [marker(X0 + 248 * f0, LANE, f0), badge("WITH FM-04", CG),
                                    tag(f0, X0 + 248 * f0, 34, "cruiseMismatch", NOTE),
                                    tag(0.62, 200, 34, "PCM cancel · disable alert", GOOD)]
  return ch, sc_today, sc_fm


def fm05():
  """Wheel-touch fallback: today any small input resets awareness; with FM-05 only a deliberate input does."""
  nudges = (0.3, 0.55, 0.8)
  saw, a, last = [], 24.0, 0.0
  for f in [i / 40 for i in range(41)]:
    a = 24 + (f - last) * 120
    if any(abs(f - n) < 0.013 for n in nudges):
      saw += [(f, a), (f + 0.001, 24)]
      last = f
      continue
    saw.append((f, min(a, 96)))
  decay = [(f, min(24 + f * 120, 96)) for f in [i / 40 for i in range(41)]]
  ch = chart("driver awareness", [(24, "full"), (96, "none")], saw, decay,
             [(0.98, 20, "reset by small inputs", CR, "end"), (0.98, 91, "no reset: alert, then take over", CG, "end")],
             [lim(78, "alert")])
  sc_today = road() + ego(straight_path()) + [badge("TODAY", CR)] + [
    tag(n, X0 + 248 * n, 34, "small nudge: reset", BAD) for n in nudges[:1]] + [tag(0.8, 190, 66, "eyes off, still engaged", BAD)]
  sc_fm = road() + ego(straight_path(), CG) + [badge("WITH FM-05", CG), tag(0.3, X0 + 248 * 0.3, 34, "small nudge: ignored", NOTE),
                                               tag(0.62, 190, 66, "DM alert: take over", GOOD)]
  return ch, sc_today, sc_fm


def fm06():
  """DM demo mode onroad: today DM runs on synthetic inputs and never alerts; with FM-06 the parameter is ignored onroad."""
  f0 = 0.25
  ch = chart("DM watches the driver", [(24, "yes"), (96, "no")], [(0, 24), (f0, 24), (f0 + .001, 96), (1, 96)],
             [(0, 24), (1, 24)],
             [(f0 + 0.03, 90, "demo mode: synthetic inputs, no alert", CR, "start"),
              (0.62, 20, "ignored onroad: DM keeps watching", CG, "middle")])
  sc_today = road() + ego(straight_path()) + [marker(X0 + 248 * f0, LANE, f0), badge("TODAY", CR),
                                              tag(f0, X0 + 248 * f0, 34, "IsDriverViewEnabled set", NOTE),
                                              tag(0.7, 200, 66, "eyes off, no DM alert", BAD)]
  sc_fm = road() + ego(straight_path(), CG) + [marker(X0 + 248 * f0, LANE, f0), badge("WITH FM-06", CG),
                                               tag(f0, X0 + 248 * f0, 34, "IsDriverViewEnabled set", NOTE),
                                               tag(0.6, 200, 66, "ignored onroad: DM alerts", GOOD)]
  return ch, sc_today, sc_fm


def fm07():
  """Above the 110 km/h ODD bound: today nothing until ≈149 km/h, then a warning only; with FM-07, warn then soft disable."""
  v = lambda kmh: 96 - (kmh - 80) * 84 / 90                  # 80..170 km/h
  ch = chart("speed (km/h)", [(v(110), "110"), (v(149), "149")], [(0, v(90)), (1, v(165))],
             [(0, v(90)), (0.27, v(110)), (0.45, v(116)), (0.68, v(106)), (1, v(102))],
             [(0.98, v(165) - 4, "warning only at 149", CR, "end"), (0.5, v(98), "warn at 110, soft disable", CG, "middle")],
             [lim(v(110), ""), lim(v(149), "")])
  sc_today = road() + ego(straight_path()) + [badge("TODAY", CR), tag(0.27, X0 + 248 * 0.27, 34, "110: nothing", BAD),
                                              tag(0.85, 210, 34, "149: warning only", BAD)]
  slow = sample(lambda f: (X0 + 248 * (f if f < 0.5 else 0.5 + (f - 0.5) * 0.7), LANE))
  sc_fm = road() + ego(slow, CG) + [badge("WITH FM-07", CG), tag(0.27, X0 + 248 * 0.27, 34, "110: slow down", NOTE),
                                    tag(0.6, 200, 34, "not slowed: soft disable", GOOD)]
  return ch, sc_today, sc_fm


def fm08():
  """Off the highway: no ODD monitor, so the item engages; with FM-08 (DQ-280 A) it refuses below a speed floor."""
  ch = chart("engaged", [(24, "on"), (96, "off")], [(0, 96), (0.2, 96), (0.2 + .001, 24), (1, 24)], [(0, 96), (1, 96)],
             [(0.6, 20, "engages off the highway", CR, "middle"), (0.6, 90, "below the floor: no entry", CG, "middle")])
  unmarked = road(False) + ['<line x1="0" y1="16" x2="280" y2="16" stroke="#F8FAFC" stroke-width="1" opacity="0.35"/>']
  slow = sample(lambda f: (X0 + 150 * f, 40))
  sc_today = unmarked + ego(slow) + [badge("TODAY", CR), tag(0.2, 70, 64, "no markings, 40 km/h: engaged", BAD)]
  sc_fm = unmarked + [trail(slow, "#94A3B8", 2.2), drive(slow, _car_body(EGO, EGO_S))] + [
    badge("WITH FM-08", CG), tag(0.2, 70, 64, "below the floor: no entry, driver drives", GOOD)]
  return ch, sc_today, sc_fm


def fm09():
  """The model's plan becomes implausible: today it is acted on unchecked; with FM-09, warn and then request take-over."""
  f0, f1 = 0.32, 0.5
  unc = [(f, 92 - 70 * max(0, min(1, (f - 0.2) / 0.5))) for f in [i / 20 for i in range(21)]]
  ch = chart("take-over requested", [(24, "yes"), (96, "no")], [(0, 96), (1, 96)],
             [(0, 96), (f1, 96), (f1 + .001, 24), (1, 24)],
             [(0.96, 92, "acted on, unchecked", CR, "end"), (f1 + 0.02, 20, "sustained: take over", CG, "start"),
              (f0 - 0.02, 50, "uncertainty", "#64748B", "end")],
             [line(unc, "#94A3B8", 1.4, "2 2"), lim(60, "threshold")])
  path = drifting(f0, 8, k=1.4)
  sc_today = road() + ego(path) + [badge("TODAY", CR), tag(f0, X0 + 248 * f0, 34, "plan jumps", NOTE),
                                   tag(0.85, 210, 34, "no confidence check", BAD)]
  sc_fm = road() + ego(path, CG) + [badge("WITH FM-09", CG), tag(f0, X0 + 248 * f0, 34, "monitor: implausible, warn", NOTE),
                                    tag(f1, 210, 34, "take over", GOOD)]
  return ch, sc_today, sc_fm


def fm10():
  """A wrong lateral command at speed: today the full torque reaches the wheel; FM-10 limits it with speed."""
  f0 = 0.3
  big = [(f, 60 - 40 * max(0, min(1, (f - f0) / 0.5)) ** 1.5) for f in [i / 20 for i in range(21)]]
  small = [(f, 60 - 14 * max(0, min(1, (f - f0) / 0.5)) ** 1.5) for f in [i / 20 for i in range(21)]]
  ch = chart("lateral offset", [(60, "0"), (24, "line")], big, small,
             [(0.95, 16, "today: torque not speed-dependent", CR, "end"), (0.95, 56, "speed-dependent limit", CG, "end")],
             [lim(24, "")])
  sc_today = road() + ego(drifting(f0, -21, k=1.5)) + [marker(X0 + 248 * f0, LANE, f0), badge("TODAY", CR),
                                                       tag(f0, X0 + 248 * f0, 66, "wrong command", NOTE),
                                                       tag(0.85, 210, 66, "into the next lane", BAD)]
  sc_fm = road() + ego(drifting(f0, -7, k=1.5), CG) + [marker(X0 + 248 * f0, LANE, f0), badge("WITH FM-10", CG),
                                                       tag(f0, X0 + 248 * f0, 66, "wrong command", NOTE),
                                                       tag(0.85, 200, 66, "stays in lane: time to correct", GOOD)]
  return ch, sc_today, sc_fm


def fm11():
  """Stopped behind a lead: today auto-resume when it moves off; with FM-11, the driver resumes."""
  lead = sample(lambda f: (150 if f < 0.3 else 150 + (f - 0.3) * 160, LANE))
  walk = [(0, 118, 6), (0.3, 118, 6), (0.75, 118, 60), (1, 118, 60)]
  ch = chart("acceleration", [(30, "go"), (90, "0")], [(0, 90), (0.32, 90), (0.32 + .001, 30), (1, 30)], [(0, 90), (1, 90)],
             [(0.36, 24, "auto-resume, as specified", CR, "start"), (0.6, 84, "held until the driver resumes", CG, "middle")])
  resume = sample(lambda f: (80 if f < 0.32 else 80 + min(1, (f - 0.32) / 0.4) * 28, LANE))
  sc_today = road() + [other(lead), ss.walker(walk)] + ego(resume) + [
    badge("TODAY", CR), tag(0.3, 220, 34, "lead moves off", NOTE), tag(0.6, 70, 34, "auto-resumes", BAD)]
  sc_fm = road() + [other(lead), ss.walker(walk), ss.car(80, LANE, 0, EGO, EGO_S)] + [
    badge("WITH FM-11", CG), tag(0.3, 220, 34, "lead moves off", NOTE), tag(0.5, 70, 34, "holds: press resume", GOOD)]
  return ch, sc_today, sc_fm


# Each card: short title, the SH it shows (one of §2 "Addresses"), today text, its passages, status, status passages.
C04_SG02 = ("WP-C-04", "Soft disable warns at once, but actuates on stale inputs up to ≈3.5 s")
OI2 = ("WP-C-07", "Raise change requests for P1 FMs under WP-P-02")
MODELS = {
  "FM-01": dict(title="Experimental Mode off and locked", sh="SH-04", draw=fm01,
                today="Chill is the default on new installs, but the owner can still turn Experimental Mode on, and a stored 1 persists.",
                src=[("FM-01.Status", "implemented 2026-10-14"),
                     ("FM-01.Status", "the toggle stays and the owner can still turn Experimental Mode on"),
                     ("FM-01.Status", "a device that already stored `1` keeps it")],
                status="partial", status_text="(a) Chill default in the code since 2026-10-14 (DQ-001 A), not verified on the vehicle; "
                                              "(b) the lock and (c) ignoring a stored 1 are not implemented (WP-C-07 §3).",
                status_src=[("FM-01.Status", "not reviewed independently, not verified on the vehicle"),
                            ("FM-01.Status", "Toggle disabled: **not implemented**"),
                            ("FM-01.Status", "Stored `\"1\"` ignored: **not implemented**")]),
  "FM-02": dict(title="No diagnostic masking, no hot switch", sh="SH-01", draw=fm02,
                today="Diagnostics are masked while the big model loads; a failure hot-switches to a model with zero recurrent state.",
                src=[("FM-02.Rationale", "Diagnostics are masked while the system may be engaged"),
                     ("FM-02.Rationale", "zero recurrent state")],
                status="open", status_text="No implementation recorded; change requests for P1 FMs are open (WP-C-07 OI-2).",
                status_src=[OI2]),
  "FM-03": dict(title="Stop steering on stale inputs", sh="SH-02", draw=fm03,
                today="Soft disable keeps actuating on the input that just failed for up to ≈3.5 s, about 100 m at 30 m/s.",
                src=[("FM-03.Rationale", "keeps actuating up to ≈3.5 s on the inputs that failed"),
                     ("FM-03.Rationale", "at 30 m/s about 100 m")],
                status="gap", status_text="WP-C-04 §8 today: soft disable warns at once, but actuates on stale inputs up to ≈3.5 s (GAP-16).",
                status_src=[C04_SG02]),
  "FM-04": dict(title="React to a cruise mismatch", sh="SH-05", draw=fm04,
                today="cruiseMismatch raises an event with no reaction; canError shows the wrong text; non-finite commands are clamped to 0.",
                src=[("gap-assessment", "`cruiseMismatch` raises an event with no reaction (IMMEDIATE_DISABLE commented out)"),
                     ("gap-assessment", "Non-finite actuator commands are silently clamped to 0")],
                status="open", status_text="No implementation recorded; change requests for P1 FMs are open (WP-C-07 OI-2).",
                status_src=[OI2]),
  "FM-05": dict(title="Awareness reset only by a deliberate input", sh="SH-12", draw=fm05,
                today="The wheel-touch fallback resets awareness on any steering or gas input; DM source validity is always True.",
                src=[("gap-assessment", "the wheel-touch fallback resets awareness on any steering or gas input"),
                     ("gap-assessment", "Source validity is always `True`")],
                status="open", status_text="No implementation recorded; change requests for P1 FMs are open (WP-C-07 OI-2).",
                status_src=[OI2]),
  "FM-06": dict(title="Lock out debug, maneuver and DM demo modes", sh="SH-12", draw=fm06,
                today="One local parameter can replace control processes or neutralise DM: IsDriverViewEnabled puts DM into demo mode with synthetic inputs.",
                src=[("FM-06.Rationale", "One local parameter can replace control processes or neutralise DM (FI-20)"),
                     ("gap-assessment", "`IsDriverViewEnabled` puts DM into demo mode with synthetic inputs")],
                status="open", status_text="No implementation recorded; change requests for P1 FMs are open (WP-C-07 OI-2).",
                status_src=[OI2]),
  "FM-07": dict(title="Hold the 110 km/h ODD bound", sh="SH-13", draw=fm07,
                today="speedTooHigh warns without disengaging, and only above ≈149 km/h; the ODD stops at 110 km/h.",
                src=[("gap-assessment", "warns without disengaging"), ("FM-07.Change", "Above `MAX_CTRL_SPEED` (≈149 km/h)"),
                     ("FM-07.Change", "Above the ODD bound (110 km/h")],
                status="gap", status_text="WP-C-02 OI-8: FM-07 implementation (software) is left open.",
                status_src=[("WP-C-02", "Left elsewhere: FM-07 implementation (software)")]),
  "FM-08": dict(title="Refuse to engage off the highway", sh="SH-13", draw=fm08,
                today="No ODD monitor exists: the item can be engaged on unmarked roads and in construction zones.",
                src=[("FM-08.Rationale", "No ODD monitor exists (WP-C-02 §5)"),
                     ("FM-08.Rationale", "construction zones and unmarked roads are TCs")],
                status="decided", status_text="DQ-280 A: refuse to engage below a highway speed floor now; floor value, implementation and verification open (WP-C-02 OI-9).",
                status_src=[("WP-C-02", "refuse to engage below a highway speed floor now"),
                            ("WP-C-02", "Open: the floor value and requirement")]),
  "FM-09": dict(title="Check the model's plan before acting", sh="SH-01", draw=fm09,
                today="No confidence or OOD gating of the control action: an implausible plan is acted on.",
                src=[("FM-09.Rationale", "No confidence or OOD gating of the control action (FI-03)")],
                status="open", status_text="No implementation recorded in the assurance documents.", status_src=[]),
  "FM-10": dict(title="Lateral authority that falls with speed", sh="SH-01", draw=fm10,
                today="Torque limits are not speed-dependent, so a wrong lateral command at speed gets the full torque.",
                src=[("gap-assessment", "Torque is not speed-dependent"),
                     ("FM-10.Expected risk reduction", "may increase SH-02 frequency")],
                status="open", status_text="No implementation recorded; it may increase SH-02 frequency and must be balanced (WP-C-07).",
                status_src=[("FM-10.Expected risk reduction", "may increase SH-02 frequency (less authority in curves) — must be balanced")]),
  "FM-11": dict(title="No auto-resume into a pedestrian", sh="SH-03", draw=fm11,
                today="After a stop the car auto-resumes when the lead moves off, without checking between ego and lead.",
                src=[("FM-11.Rationale", "FI-12, TC-27 (VRU crossing between ego and lead)")],
                status="open", status_text="No implementation recorded in the assurance documents.", status_src=[]),
}


def cards(docs: dict | None = None, models: dict | None = None):
  docs = docs or load()
  models = MODELS if models is None else models
  if missing := [fm for fm in docs["summary"] if fm not in models]:
    raise sf.FigureError(f"FM scenes: no card model for {', '.join(missing)}")
  if extra := [fm for fm in models if fm not in docs["summary"]]:
    raise sf.FigureError(f"FM scenes: card for {', '.join(extra)}, which WP-C-07 §2 does not list")
  out = []
  for fm, s in docs["summary"].items():
    m = models[fm]
    if m["sh"] not in s["sh"]:
      raise sf.FigureError(f"{fm}: WP-C-07 §2 says it addresses {', '.join(s['sh'])}, not {m['sh']}")
    quoted(docs, fm, m["src"] + m["status_src"])
    chart_, today, with_fm = m["draw"]()
    tb = docs["table"][fm]
    out.append(dict(fm=fm, title=m["title"], full=s["title"], prio=s["prio"], gap=s["gap"], shs=s["sh"], sh=m["sh"],
                    today=m["today"], status=m["status"], status_text=m["status_text"],
                    change=_plain(tb["Change"]), expected=_plain(tb["Expected risk reduction"]),
                    verification=_plain(tb["Verification"]), chart=chart_, scene_today=today, scene_fm=with_fm))
  return out


# ---------------------------------------------------------------- sheet

COLS, CW, GAP, M = 3, 400, 20, 40
PW = CW - 24
CH_H, ST_H = PW * 110 / 280, PW * 70 / 280
LW, FS = 72, 10


def _lines(s, width, max_lines):
  ls = wrap(s, width, FS)
  if len(ls) > max_lines:
    ls = ls[:max_lines]
    ls[-1] = sf._trunc(ls[-1] + " …", width, FS)
  return ls


def _rows(c):
  return [("Today", c["today"], 3), ("Change", c["change"], 3), ("Expected", c["expected"], 2),
          ("Verified by", c["verification"], 2), ("Status", c["status_text"], 3)]


def card_svg(x, y, c):
  b = [None]
  px, yy = x + 12, y + 26
  b.append(t(px, yy, c["fm"], 12, MUTED, 600))
  b.append(t(px + 46, yy, c["title"], 14.5, INK, 700))
  yy += 12
  chips = [PRIO[c["prio"]]] + [("#FFEDD5", "#7C2D12", g) for g in c["gap"]] + [("#EDE9FE", "#4C1D95", s) for s in c["shs"]]
  chips.append(STATUS[c["status"]])
  cx = px
  for bg, fg, s in chips:
    w = hf.text_w(s, 10, True) + 14
    if cx + w > px + PW:
      cx, yy = px, yy + 22
    b.append(pill(cx, yy, s, bg, fg, 18, 10)[0])
    cx += w + 6
  yy += 26
  b.append(f'<svg x="{px}" y="{yy:.1f}" width="{PW}" height="{CH_H:.1f}" viewBox="0 0 280 110">'
           '<rect width="280" height="110" rx="6" fill="#F8FAFC"/>' + "".join(c["chart"]) + "</svg>")
  yy += CH_H + 6
  for k, scene in (("t", c["scene_today"]), ("f", c["scene_fm"])):
    cid = f"m{c['fm']}{k}"
    b.append(f'<svg x="{px}" y="{yy:.1f}" width="{PW}" height="{ST_H:.1f}" viewBox="0 0 280 70">'
             f'<clipPath id="{cid}"><rect width="280" height="70" rx="5"/></clipPath>'
             f'<g clip-path="url(#{cid})">' + "".join(scene) + "</g></svg>")
    yy += ST_H + 4
  for k, v, n in _rows(c):
    ls = _lines(v, PW - LW, n)
    for i, ln in enumerate(ls):
      yy += 13
      if i == 0:
        b.append(t(px, yy, k, FS, MUTED))
      b.append(t(px + LW, yy, ln, FS, INK))
    yy += 3
  return b, yy + 12 - y


def legend(y):
  items = [(f'<line x1="0" y1="-4" x2="26" y2="-4" stroke="{CR}" stroke-width="2.8"/>', 32, "Today"),
           (f'<line x1="0" y1="-4" x2="26" y2="-4" stroke="{CG}" stroke-width="2.8"/>', 32, "With the modification"),
           (f'<rect x="0" y="-10" width="20" height="12" fill="{GREEN_FILL}" opacity="0.3"/>', 26, "What the modification changes"),
           (f'<circle cx="6" cy="-4" r="5" fill="{ss.FAULT}" stroke="{INK}" stroke-width="0.9"/>', 16, "Fault or triggering condition")]
  b, x = [], M
  for g, w, s in items:
    b.append(f'<g transform="translate({x} {y})">{g}</g>')
    x += w
    b.append(t(x, y, s, 11, INK))
    x += hf.text_w(s, 11) + 20
  return b


def sheet(name: str, cs: list) -> str:
  num, what, prios = SHEETS[name]
  cs = [c for c in cs if c["prio"] in prios]
  w = 2 * M + COLS * CW + (COLS - 1) * GAP
  body = hf.header(w, f"SOTIF modifications · {what}",
                   "Each modification of WP-C-07: what the car does today, against the same scene with the modification in place.",
                   "WP-C-07 §2-§3", "Schematic, not simulation output")
  body += legend(108)
  y, rows = 128, []
  for r in range(0, len(cs), COLS):
    built = [card_svg(M + k * (CW + GAP), y, c) for k, c in enumerate(cs[r:r + COLS])]
    row_h = max(h for _, h in built)
    for (b, _), k in zip(built, range(COLS)):
      b[0] = f'<rect x="{M + k * (CW + GAP)}" y="{y}" width="{CW}" height="{row_h:.0f}" rx="10" fill="#FFFFFF" stroke="{HAIR}"/>'
      rows += b
    y += row_h + GAP
  body += rows
  body.append(t(M, y + 6, "Today and status texts quote WP-C-07, WP-C-04, WP-C-02 and the gap assessment; the build fails if a quoted "
                "passage changes. P1: before on-road operation beyond safety-driver testing; P2: before G5; P3: decide at G2.", 10.5, MUTED))
  body.append(t(w - M, y + 24, "Generated by fm_scenes.py", 10, MUTED, None, "end"))
  desc = (f"Figure {num}: {len(cs)} cards, one per WP-C-07 modification with priority {' or '.join(prios)}. " +
          " ".join(f"{c['fm']} {c['full']} ({c['prio']}): today, {c['today']} With it: {c['expected']}" for c in cs))
  return svg_doc(w, int(y + 36), f"SOTIF modifications: {what} (WP-C-07)", desc, body)


def build(docs: dict | None = None) -> dict[str, str]:
  cs = cards(docs)
  return {name: sheet(name, cs) for name in SHEETS}


if __name__ == "__main__":
  sys.exit(sf.main(sys.argv[1:]))
