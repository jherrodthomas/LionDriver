#!/usr/bin/env python3
"""Draw the STPA scene sheets: one card per unsafe control action of the driver (C1), openpilot (C2) and the panda (C3).

One sheet per controller (`fig-a05-4-2-scenes-driver.svg`, `-4-3-scenes-openpilot.svg`, `-4-4-scenes-panda.svg`).
Each card shows:

- which of the four UCA types it is (not provided, provided, wrong timing, wrong duration);
- a top-down road scene that loops every 6 s (SMIL, no script; a viewer that does not animate shows the key moment);
- a "needed window" chart: when the control action is wanted against what happens, or a timing chart of the signals
  involved;
- what the controller believes against what is true;
- the controller's loop with the broken link in red (and a safety net that works in green);
- the loss scenarios with their status, the decisions and requirements from `../stpa-map.yaml`, and the controller
  constraints of WP-A-05 §4.5 that name the UCA.

UCA type and text, hazards, loss-scenario types and constraints come from WP-A-05; statuses, decisions and
requirements from `stpa-map.yaml`. The scenes, charts and belief lines below are drawings that explain each loss
scenario: they are schematic, not simulation or test results. The build fails if a UCA of §4.1–§4.3 has no card, a card
names a UCA that is not there, or a card cites an ID (LS-, CA-, FB-, DQ-) that the sources do not have.

Called from `fig_a05_stpa.py` (`build()`), which writes and checks the sheets with the other WP-A-05 figures and passes itself in,
so this module never imports it.
Its road scenes and text helpers also draw the WP-C-09 threat scene cards (`assurance/02-concept/figures/fig_c09_scenes.py`)
and the WP-C-04 FTTI scene cards (`assurance/02-concept/fsc/fsc_scenes.py`), whose `--check` therefore also catches a change
here. The road, cars, paths and pills come from the shared scene kit (`assurance/01-management/figures/scenekit.py`),
scaled to these 460 x 250 scenes (scenekit.LARGE_*); the scene coordinates below are in that large scene.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "01-management" / "figures"))
import scenekit as sk  # noqa: E402  (road, car, path and pill style)

FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SFMono-Regular', Menlo, Consolas, monospace"
K = None  # fig_a05_stpa, passed in by sheets(): it runs as __main__, so importing it here would load a second copy


def fail(msg):
  raise K.ParseError(msg)

INK, MUTED, RULE = "#16202A", "#55606C", "#D6DBE0"
REQ, PERF = "#16A34A", "#DC2626"
CARD_W, CARD_H, GAP, LOOP_S = 980, 730, 24, 6

SHEETS = {
  "fig-a05-4-2-scenes-driver.svg": ("C1 Driver", "4-2", "the driver (C1)"),
  "fig-a05-4-3-scenes-openpilot.svg": ("C2 openpilot", "4-3", "openpilot (C2)"),
  "fig-a05-4-4-scenes-panda.svg": ("C3 panda", "4-4", "the panda safety model (C3)"),
}
CTRL_NAME = {"C1 Driver": "Driver (C1)", "C2 openpilot": "openpilot (C2)", "C3 panda": "panda safety model (C3)"}
CTRL_INK = {"C1 Driver": "#3B5BA9", "C2 openpilot": MUTED, "C3 panda": "#C2410C"}
HZ_SHORT = {  # card labels for the hazards of WP-A-05 §2 (the full wording is in the table there)
  "H-01": "unintended steering", "H-02": "silent loss of steering", "H-03": "unintended acceleration", "H-04": "unintended braking",
  "H-05": "cannot override", "H-06": "silent loss of braking", "H-07": "mode confusion", "H-08": "stock PCS suppressed",
  "H-STPA-1": "driver not supervising",
}
TYPES = [("N", "not provided"), ("P", "provided, unsafe"), ("T", "wrong timing"), ("D", "wrong duration")]
TYPE_WORD = {"N": "not provided", "P": "provided", "T": "wrong timing", "D": "wrong duration"}
BOX = {"drv": ("#E3EAF8", "#3B5BA9"), "item": ("#FFFFFF", MUTED), "env": ("#FFF4EC", "#C2410C"),
       "ext": ("#ECEEF1", "#6B7480"), "bad": ("#FDE4E1", "#DC2626"), "ok": ("#E3F2E8", "#2F7D4F")}
PILL = {"drv": "#1E3A8A", "bad": "#7F1D1D", "ok": "#14532D", "info": "#334155"}
LINK = {"ca": "#C2410C", "fb": "#0F766E", "grey": "#94A3B8", "bad": "#DC2626", "dead": "#DC2626", "net": "#16A34A"}
LINK_T = {"ca": "#C2410C", "fb": "#0F766E", "grey": MUTED, "bad": "#B42318", "dead": "#B42318", "net": "#166534"}


def _f(v):
  return f"{v:.1f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def T(x, y, s, size=12, fill=INK, weight=400, anchor="start", font=FONT, extra=""):
  return (f'<text x="{_f(x)}" y="{_f(y)}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{fill}"'
          f'{"" if anchor == "start" else f" text-anchor={chr(34)}{anchor}{chr(34)}"}{extra}>{escape(s)}</text>')


def M(x, y, s, size=10.5, fill=INK, anchor="start"):
  return T(x, y, s, size, fill, 600, anchor, MONO)


def tw(s, size=12, mono=False):
  return len(s) * size * (0.62 if mono else 0.56)


def wrap(s, n):
  out, line = [], ""
  for w in s.split():
    if line and len(line) + 1 + len(w) > n:
      out.append(line)
      line = w
    else:
      line = f"{line} {w}".strip()
  return out + ([line] if line else [])


def anim(attr, values, keys, kind=None):
  a = f'attributeName="{attr}" values="{values}" keyTimes="{keys}" dur="{LOOP_S}s" repeatCount="indefinite"'
  return f'<animateTransform {a} type="{kind}"/>' if kind else f"<animate {a}/>"


def appear(at):
  return anim("opacity", "0;0;1;1", f"0;{at:.2f};{min(at + 0.02, 0.99):.2f};1")


def draw_on(d, stroke, width=2.4, dash=None):
  if dash:
    return f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{width}" stroke-dasharray="{dash}"/>'
  return (f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round" pathLength="1" '
          f'stroke-dasharray="1" stroke-dashoffset="0">{anim("stroke-dashoffset", "1;1;0;0", "0;0.05;0.92;1")}</path>')


# ============================================================================ smooth paths and the car that follows them
def _cr(pts):
  """Catmull-Rom through pts, as cubic Bezier segments [(p0, c1, c2, p1)]."""
  segs = []
  for i in range(len(pts) - 1):
    p0, p1 = pts[i], pts[i + 1]
    pm, pn = pts[i - 1] if i else p0, pts[i + 2] if i + 2 < len(pts) else p1
    c1 = (p0[0] + (p1[0] - pm[0]) / 6, p0[1] + (p1[1] - pm[1]) / 6)
    c2 = (p1[0] - (pn[0] - p0[0]) / 6, p1[1] - (pn[1] - p0[1]) / 6)
    segs.append((p0, c1, c2, p1))
  return segs


def smooth(pts):
  segs = _cr(pts)
  d = f"M{_f(float(pts[0][0]))} {_f(float(pts[0][1]))}"
  for _, c1, c2, p1 in segs:
    d += " C" + " ".join(f"{_f(round(a, 1))} {_f(round(b, 1))}" for a, b in (c1, c2, p1))
  return d


def _bez(seg, t):
  (a, b, c, d), u = seg, 1 - t
  return tuple(u ** 3 * a[i] + 3 * u * u * t * b[i] + 3 * u * t * t * c[i] + t ** 3 * d[i] for i in (0, 1))


def samples(pts, n=6):
  out = [pts[0]]
  for seg in _cr(pts):
    out += [_bez(seg, k / n) for k in range(1, n + 1)]
  return out


def pose_at(sm, frac):
  """Point and heading at fraction frac of the arc length of the sampled polyline sm."""
  L = [0.0]
  for a, b in zip(sm, sm[1:], strict=False):
    L.append(L[-1] + math.dist(a, b))
  s = frac * L[-1]
  for i in range(1, len(sm)):
    if L[i] >= s or i == len(sm) - 1:
      a, b = sm[i - 1], sm[i]
      u = 0 if L[i] == L[i - 1] else (s - L[i - 1]) / (L[i] - L[i - 1])
      return (a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1])), math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
  return sm[-1], 0.0


def car_shape(body=sk.EGO, arrows=(), brake=False):
  """The kit's car at the large scene's scale; arrows: who pushes the steering (driver up, openpilot down)."""
  a = ""
  if "drv" in arrows:
    a += '<line x1="-3" y1="-11" x2="-3" y2="-24" stroke="#93C5FD" stroke-width="2.6" marker-end="url(#ah-b)"/>'
  if "op" in arrows:
    a += '<line x1="3" y1="11" x2="3" y2="28" stroke="#FCA5A5" stroke-width="3" marker-end="url(#ah-r)"/>'
  inner = {sk.EGO: sk.ego_body(brake), sk.STOPPED: sk.other_body(stopped=True)}.get(body) or sk.other_body()
  return f'<g transform="scale({sk.LARGE_K})">{inner}</g>' + a


def follow(pts, still, inner, start=0.0, end=0.92):
  """A car group moving along pts over the loop; its static pose is at fraction `still` of the path."""
  sm = samples(pts)
  n = 16
  fr = [k / n for k in range(n + 1)]
  poses = [pose_at(sm, f) for f in fr]
  keys = ";".join(f"{start + (end - start) * f:.3f}" for f in fr)
  (sx, sy), sh = pose_at(sm, still)
  tr = ";".join(f"{p[0]:.1f} {p[1]:.1f}" for p, _ in poses)
  rot = ";".join(f"{h:.1f}" for _, h in poses)
  keys_t = f"0;{keys};1" if start > 0 else f"{keys};1"
  tr = f"{poses[0][0][0]:.1f} {poses[0][0][1]:.1f};{tr}" if start > 0 else tr
  rot = f"{poses[0][1]:.1f};{rot}" if start > 0 else rot
  tr += f";{poses[-1][0][0]:.1f} {poses[-1][0][1]:.1f}"
  rot += f";{poses[-1][1]:.1f}"
  return (f'<g transform="translate({sx:.1f} {sy:.1f})">{anim("transform", tr, keys_t, "translate")}'
          f'<g transform="rotate({sh:.1f})">{anim("transform", rot, keys_t, "rotate")}{inner}</g></g>')


def slide(keys, y, still, inner):
  """A car driving along a straight lane: keys [(loop fraction, x)]; static pose at loop fraction `still`."""
  x0 = keys[0][1]
  for (fa, xa), (fb, xb) in zip(keys, keys[1:], strict=False):
    if fa <= still <= fb:
      x0 = xa + (xb - xa) * (0 if fb == fa else (still - fa) / (fb - fa))
  if keys[-1][0] < 1:
    keys = keys + [(1.0, keys[-1][1])]
  if keys[0][0] > 0:
    keys = [(0.0, keys[0][1])] + keys
  vals = ";".join(f"{x:.1f} {y}" for _, x in keys)
  kt = ";".join(f"{f:.3f}" for f, _ in keys)
  return f'<g transform="translate({x0:.1f} {y})">{anim("transform", vals, kt, "translate")}{inner}</g>'


# ============================================================================ road scenes (460 x 250)
GRASS, VERGE, ASPHALT, PAINT = sk.GRASS, sk.VERGE, sk.ASPHALT, sk.PAINT
KS = sk.LARGE_K
CURVE = [(-10, 70), (100, 70), (190, 70), (260, 74), (320, 98), (370, 140), (405, 185), (430, 235), (440, 262)]
CURVE_D = "M-10 70 L190 70 C260 70 320 90 370 140 C400 170 420 200 440 260"


def pills(items):
  return [f"<g>{appear(at)}" + sk.pill(8, y, text, kind, 11, 18, num, 600, FONT) + "</g>" for num, text, kind, at, y in items]


def _obstacle(kind, x, y):
  if kind == "debris":
    return (f'<g transform="translate({x} {y})"><rect x="-8" y="-8" width="16" height="16" rx="3" fill="#78350F" stroke="#FBBF24" '
            'stroke-width="1.5"/><path d="M-4 -4 L4 4 M4 -4 L-4 4" stroke="#FBBF24" stroke-width="1.4"/></g>')
  if kind == "cyclist":
    return (f'<g transform="translate({x} {y})"><line x1="-9" y1="0" x2="9" y2="0" stroke="#1F2937" stroke-width="2"/>'
            '<circle cx="-8" cy="0" r="3.2" fill="none" stroke="#1F2937" stroke-width="1.4"/>'
            '<circle cx="8" cy="0" r="3.2" fill="none" stroke="#1F2937" stroke-width="1.4"/>'
            '<ellipse cx="0" cy="-3" rx="4.5" ry="3.4" fill="#F59E0B"/></g>')
  if kind == "cone":
    return f'<path d="M{x - 5} {y + 5} L{x} {y - 7} L{x + 5} {y + 5} Z" fill="#F97316" stroke="#7C2D12" stroke-width="0.8"/>'
  if kind == "light":
    return (f'<rect x="{x - 5}" y="{y - 13}" width="10" height="26" rx="2" fill="#1F2937"/><circle cx="{x}" cy="{y - 6}" r="3.6" '
            f'fill="#DC2626"/><circle cx="{x}" cy="{y + 6}" r="3.6" fill="#374151"/>')
  if kind == "phone":
    return (f'<g transform="translate({x} {y})"><rect x="-5" y="-8" width="10" height="16" rx="2" fill="#1F2937"/>'
            '<rect x="-3.5" y="-6" width="7" height="11" fill="#60A5FA"/></g>')
  fail(f"unknown scene object {kind}")


def scene_lat(sc):
  o = sk.large_road(faded=bool(sc.get("faded")))
  if sc.get("old_lines"):
    o.append(f'<path d="{smooth(sc["old_lines"])}" fill="none" stroke="#FDE68A" stroke-width="1.6" stroke-dasharray="10 8"/>')
  return o + _scene_common(sc)


def scene_curve(sc):
  o = [f'<rect width="460" height="250" fill="{GRASS}"/>', *sk.single_lane_road(CURVE_D, KS),
       sk.direction_arrow(f"translate(30 70) scale({KS})")]
  return o + _scene_common(sc)


def scene_lon(sc):
  o = sk.large_road()
  if "stop_x" in sc:
    o.append(f'<line x1="{sc["stop_x"]}" y1="127" x2="{sc["stop_x"]}" y2="187" stroke="{PAINT}" stroke-width="{3 * KS:.1f}"/>')
  return o + _scene_common(sc)


def _scene_common(sc):
  o = []
  for kind, x, y in sc.get("objects", ()):
    o.append(_obstacle(kind, x, y))
  if sc.get("want"):   # the kit's intended path, at the large scene's scale
    o.append(f'<path d="{smooth(sc["want"])}" fill="none" stroke="{sk.REQ_S}" stroke-width="{2.2 * KS:.1f}" '
             f'stroke-dasharray="{5 * KS:.1f} {3 * KS:.1f}" stroke-linecap="round"/>')
  if sc.get("ghost"):
    o.append(f'<path d="{smooth(sc["ghost"])}" fill="none" stroke="{sk.ARROW}" stroke-width="{2.2 * KS:.1f}" '
             f'stroke-dasharray="{4 * KS:.1f} {4 * KS:.1f}"/>')
  for x0, y0, x1, y1 in sc.get("marks", ()):
    o.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="#F87171" stroke-width="7" stroke-linecap="round"/>')
  for x, y0, y1, c in sc.get("dims", ()):
    o.append(f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y1}" stroke="{c}" stroke-width="1.6"/>'
             f'<line x1="{x - 5}" y1="{y0}" x2="{x + 5}" y2="{y0}" stroke="{c}" stroke-width="1.6"/>')
  if sc.get("act"):
    o.append(draw_on(smooth(sc["act"]), sk.PERF_S, f"{2.6 * KS:.1f}"))
  for x, y, text, fill, *rest in sc.get("labels", ()):
    o.append(T(x, y, text, 11, fill, 600 if rest and rest[0] == "b" else 400, rest[1] if len(rest) > 1 else "start"))
  for a in sc.get("actors", ()):
    inner = car_shape(a.get("body", sk.OTHER), a.get("arrows", ()), a.get("brake", False))
    o.append(follow(a["path"], sc["still"], inner) if "path" in a else slide(a["keys"], a["y"], sc["still"], inner))
  if sc.get("act"):
    o.append(follow(sc["act"], sc["still"], car_shape(arrows=sc.get("arrows", ())), sc.get("start", 0.0)))
  o += pills(sc["pills"])
  if sc.get("arrows"):
    o.append('<g transform="translate(300 236)"><line x1="0" y1="0" x2="14" y2="0" stroke="#93C5FD" stroke-width="2.6"/>' +
             T(18, 4, "driver", 11) + '<line x1="64" y1="0" x2="78" y2="0" stroke="#FCA5A5" stroke-width="3"/>' + T(82, 4, "openpilot", 11) + "</g>")
  if sc.get("foot"):
    o.append(T(8, 244, sc["foot"], 11, "#334155"))
  return o


SCENE = {"lat": scene_lat, "curve": scene_curve, "lon": scene_lon}


# ============================================================================ charts (440 x 250)
X0, X1, Y0, Y1 = 56, 424, 44, 204


def chart_signal(c):
  t0, t1 = c["t"]
  lo, hi = c["y"][0], c["y"][1]
  X = lambda t: X0 + (t - t0) / (t1 - t0) * (X1 - X0)
  Y = lambda v: Y1 - (v - lo) / (hi - lo) * (Y1 - Y0)
  pl = lambda pts: "M" + " L".join(f"{X(t):.1f} {Y(v):.1f}" for t, v in pts)
  o = ['<defs><pattern id="{id}hz" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
       '<rect width="8" height="8" fill="#FFF5F4"/><line x1="0" y1="0" x2="0" y2="8" stroke="#FCA5A5" stroke-width="2"/></pattern></defs>']
  for a, b, va, vb in c.get("band", ()):
    o.append(f'<rect x="{X(a):.1f}" y="{Y(vb):.1f}" width="{X(b) - X(a):.1f}" height="{Y(va) - Y(vb):.1f}" fill="#E3F5E9"/>')
  if c.get("hatch"):
    a, b = c["hatch"]
    o.append(f'<rect x="{X(a):.1f}" y="{Y0}" width="{X(b) - X(a):.1f}" height="{Y1 - Y0}" fill="url(#{{id}}hz)"/>')
  if c.get("thresh"):
    v, label = c["thresh"]
    o += [f'<line x1="{X0}" y1="{Y(v):.1f}" x2="{X1}" y2="{Y(v):.1f}" stroke="#94A3B8" stroke-dasharray="3 3"/>',
          T(X1 - 4, Y(v) - 6, label, 11, MUTED, anchor="end")]
  o += [f'<line x1="{X0}" y1="40" x2="{X0}" y2="{Y1}" stroke="#94A3B8"/>', f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="#94A3B8"/>',
        T(16, 124, c["y"][2], 11, MUTED, anchor="middle", extra=' transform="rotate(-90 16 124)"')]
  for v, label in c["yt"]:
    o.append(T(X0 - 6, Y(v) + 4, label, 11, MUTED, anchor="end"))
  for i, (t, label) in enumerate(c["xt"]):
    o.append(T(X(t), 220, label, 11, MUTED, anchor="end" if i == len(c["xt"]) - 1 else "middle"))
  for t, num, kind in c.get("ev", ()):
    o += [f'<line x1="{X(t):.1f}" y1="30" x2="{X(t):.1f}" y2="{Y1}" stroke="#94A3B8" stroke-dasharray="2 3"/>',
          f'<circle cx="{X(t):.1f}" cy="24" r="8" fill="{PILL[kind]}"/>', M(X(t), 28, str(num), 10.5, "#FFFFFF", "middle")]
  if c.get("ghost"):
    o.append(f'<path d="{pl(c["ghost"])}" fill="none" stroke="#94A3B8" stroke-width="2" stroke-dasharray="3 3"/>')
  if c.get("need"):
    o.append(f'<path d="{pl(c["need"])}" fill="none" stroke="{REQ}" stroke-width="2" stroke-dasharray="6 4"/>')
  o.append(draw_on(pl(c["perf"]), PERF, 2.6))
  for t, v, text, kind, *anc in c.get("notes", ()):
    fill, wt = {"need": ("#166534", 600), "perf": ("#B42318", 600), "m": (MUTED, 400), "bad": ("#B42318", 600)}[kind]
    o.append(T(X(t), Y(v), text, 12 if wt == 600 else 11, fill, wt, anc[0] if anc else "start"))
  return o + _chart_legend(c)


def chart_lanes(c):
  t0, t1 = c["t"]
  X = lambda t: 104 + (t - t0) / (t1 - t0) * (X1 - 104)
  o = ['<defs><pattern id="{id}tk" width="5.33" height="10" patternUnits="userSpaceOnUse"><rect width="5.33" height="10" fill="#FFFFFF"/>'
       '<rect width="1.6" height="10" fill="#16202A"/></pattern><pattern id="{id}tr" width="5.33" height="10" patternUnits="userSpaceOnUse">'
       '<rect width="5.33" height="10" fill="#FFFFFF"/><rect width="1.6" height="10" fill="#DC2626"/></pattern>'
       '<pattern id="{id}th" width="26" height="10" patternUnits="userSpaceOnUse"><rect width="26" height="10" fill="#FFFFFF"/>'
       '<rect width="2.2" height="10" fill="#0F766E"/></pattern><pattern id="{id}hs" width="7" height="7" patternUnits="userSpaceOnUse" '
       'patternTransform="rotate(45)"><rect width="7" height="7" fill="#F1F3F5"/><line x1="0" y1="0" x2="0" y2="7" stroke="#C3CAD2" '
       'stroke-width="2"/></pattern><pattern id="{id}hz" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
       '<rect width="8" height="8" fill="#FFF5F4"/><line x1="0" y1="0" x2="0" y2="8" stroke="#FCA5A5" stroke-width="2"/></pattern></defs>']
  fills = {"ok": ("#E3F2E8", "#2F7D4F"), "bad": ("#FDE4E1", "#DC2626"), "off": ("#FFFFFF", "#94A3B8"), "stall": ("url(#{id}hs)", "#94A3B8"),
           "tick": ("url(#{id}tk)", "none"), "tickr": ("url(#{id}tr)", "none"), "tickh": ("url(#{id}th)", "none")}
  for i, lane in enumerate(c["lanes"]):
    y = 50 + i * 36
    o.append(T(10, y + 10, lane[0], 12, INK, 600))
    if lane[1]:
      o.append(T(10, y + 22, lane[1], 11, MUTED))
    for a, b, style, label in lane[2]:
      f, s = fills[style]
      h, dy = (12, 1) if style.startswith("tick") else (14, 0)
      o.append(f'<rect x="{X(a):.1f}" y="{y + dy}" width="{X(b) - X(a):.1f}" height="{h}" rx="{0 if style.startswith("tick") else 2}" '
               f'fill="{f}" stroke="{s}"/>')
      if label:
        o.append(T(X(b) + 6, y + 11, label, 11, MUTED) if style.startswith("tick") or style == "off" and X(b) - X(a) < 60
                 else T((X(a) + X(b)) / 2, y + 11, label, 11, "#334155", anchor="middle"))
  st = c["step"]
  y = 160
  hi, lo = y + 6, y + 36
  L = lambda pts: "M" + " L".join(f"{X(t):.1f} {hi if v else lo}" for t, v in pts)
  o += [T(10, y + 20, st[0], 12, INK, 600), T(10, y + 32, st[1], 11, MUTED) if st[1] else "",
        f'<rect x="104" y="{y}" width="{X(st[2]) - 104:.1f}" height="40" fill="#E3F5E9"/>',
        f'<rect x="{X(st[2]):.1f}" y="{y}" width="{X1 - X(st[2]):.1f}" height="40" fill="url(#{{id}}hz)"/>']
  if st[5]:
    o += [f'<path d="{L(st[5])}" fill="none" stroke="#94A3B8" stroke-width="2" stroke-dasharray="3 3"/>', T(X1 - 4, y - 2, st[6], 11, MUTED, anchor="end")]
  o.append(f'<path d="{L(st[3])}" fill="none" stroke="{REQ}" stroke-width="2" stroke-dasharray="6 4"/>')
  o.append(draw_on(L(st[4]), PERF, 2.6))
  for t, num, kind in c.get("ev", ()):
    o += [f'<line x1="{X(t):.1f}" y1="36" x2="{X(t):.1f}" y2="{Y1}" stroke="#94A3B8" stroke-dasharray="2 3"/>',
          f'<circle cx="{X(t):.1f}" cy="28" r="8" fill="{PILL[kind]}"/>', M(X(t), 32, str(num), 10.5, "#FFFFFF", "middle")]
  for t, yy, text, kind, *anc in c.get("notes", ()):
    fill, wt = {"perf": ("#B42318", 600), "m": (MUTED, 400), "need": ("#166534", 600)}[kind]
    o.append(T(X(t), yy, text, 12 if wt == 600 else 11, fill, wt, anc[0] if anc else "start"))
  o.append(f'<line x1="104" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="#94A3B8"/>')
  for i, (t, label) in enumerate(c["xt"]):
    o.append(T(X(t), 218, label, 11, MUTED, anchor="end" if i == len(c["xt"]) - 1 else "middle"))
  return o + _chart_legend(c)


def _chart_legend(c):
  return ['<g transform="translate(60 238)"><rect x="0" y="-8" width="16" height="10" fill="#E3F5E9" stroke="#16A34A" stroke-dasharray="3 2"/>' +
          T(22, 1, "needed", 11, MUTED) + f'<line x1="78" y1="-3" x2="96" y2="-3" stroke="{PERF}" stroke-width="2.6"/>' +
          T(102, 1, "performed", 11, MUTED) + T(370, 1, c.get("foot", "schematic, not measured"), 11, MUTED, anchor="end") + "</g>"]


CHART = {"signal": chart_signal, "lanes": chart_lanes}


# ============================================================================ control loop (440 x 170)
SLOTS = {  # path, label anchor (x, y, text-anchor)
  "down": ("M230 68 L230 114", (244, 88, "start")),
  "up": ("M60 116 L60 70", (74, 96, "start")),
  "r_in": ("M346 62 L346 38 L280 38", (356, 30, "start")),
  "r_out": ("M276 40 L371 40 L371 60", (290, 32, "start")),
  "r_down": ("M371 116 L371 138 L280 138", (296, 156, "start")),
  "b_r": ("M276 138 L370 138 L370 118", (292, 154, "start")),
}


def loop(lp):
  o = ['<defs>' + "".join(f'<marker id="{{id}}l{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">'
                          f'<path d="M0 0L10 5L0 10z" fill="{c}"/></marker>' for k, c in LINK.items()) + '</defs>']
  name, sub, kind = lp["ctrl"]
  f, s = BOX[kind]
  o += [f'<rect x="14" y="10" width="262" height="58" rx="6" fill="{f}" stroke="{s}" stroke-width="1.5"/>', T(24, 28, name, 12, INK, 700)]
  inner = lp["inner"]
  if len(inner) == 1:
    o += [T(24, 44 + 14 * i, line, 11, MUTED) for i, line in enumerate(sub)]
    boxes = [(118, 18, 150, 42)]
  else:
    boxes = [(24, 34, 110, 28), (142, 18, 126, 44)]
  for (x, y, w, h), (label, text, ok) in zip(boxes, inner, strict=True):
    f, s = BOX["ok" if ok else "bad"]
    tc = "#14532D" if ok else "#7F1D1D"
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{f}" stroke="{s}" stroke-width="1.4"/>')
    if label:
      o += [T(x + 8, y + 16, label, 11, tc, 600), T(x + 8, y + 33, text + (" ✓" if ok else " ✕"), 12, tc)]
    else:
      o.append(T(x + 6, y + 18, text + (" ✓" if ok else " ✕"), 11, tc))
  name, sub = lp["bottom"]
  o += ['<rect x="14" y="116" width="262" height="44" rx="6" fill="#ECEEF1" stroke="#6B7480" stroke-width="1.3"/>',
        T(24, 135, name, 12, INK, 600), T(24, 151, sub, 11, MUTED)]
  name, sub, kind = lp["right"]
  f, s = BOX[kind]
  o += [f'<rect x="312" y="62" width="118" height="54" rx="6" fill="{f}" stroke="{s}" stroke-width="1.3"/>',
        T(322, 82, name, 12, INK, 600), T(322, 98, sub, 11, MUTED)]
  for slot, label, state in lp["links"]:
    d, (lx, ly, anc) = SLOTS[slot]
    wd = 3 if state in ("bad", "dead", "net") else 2
    dash = ' stroke-dasharray="6 4"' if state == "dead" else ""
    o.append(f'<path d="{d}" fill="none" stroke="{LINK[state]}" stroke-width="{wd}"{dash} marker-end="url(#{{id}}l{state})"/>')
    if state == "dead":
      cx, cy = _mid(d)
      o.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="9" fill="#DC2626"/><path d="M{cx - 4:.0f} {cy - 4:.0f} L{cx + 4:.0f} {cy + 4:.0f} '
               f'M{cx + 4:.0f} {cy - 4:.0f} L{cx - 4:.0f} {cy + 4:.0f}" stroke="#FFFFFF" stroke-width="2"/>')
    if "|" in label:
      ly -= {"r_in": 13, "r_out": 13, "r_down": 5}.get(slot, 0)
    for i, part in enumerate(label.split("|")):
      o.append(M(lx, ly + 13 * i, part, 10.5, LINK_T[state], anc))
  return o


def _mid(d):
  pts = [tuple(float(v) for v in p.split()) for p in re.findall(r"[ML](\d+ \d+)", d)]
  return pts[1] if len(pts) > 2 else ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)


# ============================================================================ sources the cards read
def uca_rows(S):
  """UCA -> hazards, from the §4.1–§4.3 tables (| UCA | type | text | hazards |)."""
  return {c[0]: re.findall(r"H-(?:STPA-)?\d+", c[3]) for c in S._rows(r"UCA-\d+") if len(c) >= 4 and c[1] in ("N", "P", "T", "D")}


def constraints(S):
  out = {}
  for c in S._rows(r"CC-\d+"):
    for u in re.findall(r"UCA-\d+", c[-1]):
      out.setdefault(u, []).append(c[0])
  return out


def card_ucas(S, ctrl):
  return sorted((u for u, v in S.ucas.items() if v["ctrl"] == ctrl and int(u[4:]) < 40), key=lambda u: int(u[4:]))


def footer(S, uid, m):
  chips = []
  for s in S.smap["scenarios"]:
    if uid in s["ucas"]:
      kind = S.ls_type[s["id"]].split(";")[0].split("(")[0].strip().lower()
      chips.append((f'{s["id"]} · {K.STATUS_LABEL[s["status"]].lower()} · {kind}', s["status"]))
  dq = sorted({d for s in S.smap["scenarios"] if uid in s["ucas"] for d in s.get("decisions", [])}, key=lambda d: int(d[3:]))
  tsr = sorted({r for s in S.smap["scenarios"] if uid in s["ucas"] for r in s.get("requirements", [])})
  if dq:
    chips.append(("Decisions " + ", ".join(dq), None))
  if tsr:
    chips.append(("Requirements " + ", ".join(tsr[:4]) + (" …" if len(tsr) > 4 else ""), None))
  cc = constraints(S).get(uid, [])
  if cc:
    chips.append(("Constraint" + ("s " if len(cc) > 1 else " ") + ", ".join(cc), None))
  chips += [(n, None) for n in m.get("notes", ())]
  return chips


# ============================================================================ one card
def check(S, uid, m):
  ids = set(re.findall(r"\b(?:LS|CA|FB|DQ|UCA)-\d+\b", repr(m)))
  S.need(*sorted(ids))
  for ls in m.get("ls", ()):
    if uid not in S.scen[ls]["ucas"]:
      fail(f"{uid} card cites {ls}, which stpa-map.yaml does not link to it")
  for h in uca_rows(S)[uid]:
    if h not in HZ_SHORT or h not in S.hazards:
      fail(f"{uid}: hazard {h} has no card label or is not in WP-A-05 §2")
  lp = m["loop"]
  if len(lp["inner"]) == 1 and any(len(x) > 15 for x in lp["ctrl"][1]):
    fail(f"{uid} card: controller note longer than 15 characters runs under the process-model box")
  if len(wrap(m["title"], 38)) > 2:
    fail(f"{uid} card title runs over two lines")


def card(S, uid, m, x, y, n):
  check(S, uid, m)
  u = S.ucas[uid]
  ink = CTRL_INK[u["ctrl"]]
  cid = f"c{n}"
  o = [f'<g transform="translate({x} {y})"><title>{escape(uid)}: {escape(m["title"])}</title>',
       f'<rect width="{CARD_W}" height="{CARD_H}" rx="12" fill="#F6F7F8" stroke="{RULE}"/>',
       M(24, 36, f'{uid} · {CTRL_NAME[u["ctrl"]]} · type {u["type"]}, {TYPE_WORD[u["type"]]}'.upper(), 12, ink)]
  for i, line in enumerate(wrap(m["title"], 38)):
    o.append(T(24, 70 + 30 * i, line, 25, INK, 700))
  o.append(T(24, 132, " · ".join(f"{h} {HZ_SHORT[h]}" for h in uca_rows(S)[uid]), 13, MUTED))
  o.append(M(956, 34, "FOUR WAYS A CONTROL ACTION GOES WRONG", 11, MUTED, "end"))
  for i, (k, word) in enumerate(TYPES):
    cx, on = 564 + i * 100, k == u["type"]
    f, s, sw = ("#FDE4E1", "#B42318", 2) if on else ("#FFFFFF", RULE, 1)
    bar = {"N": "", "P": '<rect x="52" y="7" width="18" height="6" rx="1" fill="#DC2626"/>',
           "T": '<rect x="38" y="7" width="22" height="6" rx="1" fill="#DC2626"/>',
           "D": '<rect x="14" y="7" width="54" height="6" rx="1" fill="#DC2626"/>'}[k]
    o.append(f'<g transform="translate({cx} 44)" opacity="{1 if on else 0.5}"><rect width="92" height="60" rx="6" fill="{f}" stroke="{s}" '
             f'stroke-width="{sw}"/><g transform="translate(10 8)"><rect x="14" y="3" width="36" height="14" rx="2" fill="#E3F5E9" '
             f'stroke="#16A34A" stroke-dasharray="3 2"/>{bar}</g>' +
             T(46, 42, f"{k} {word.split(',')[0]}", 11, "#B42318" if on else INK, 700 if on else 600, "middle") +
             (T(46, 55, "unsafe", 11, "#B42318", 700, "middle") if k == "P" else "") + "</g>")
  sc, ch = m["scene"], m["chart"]
  o += [M(24, 162, "ROAD SCENE · SCHEMATIC, LOOPS EVERY 6 S", 11, MUTED),
        f'<svg x="24" y="170" width="470" height="255" viewBox="0 0 460 250"><rect width="460" height="250" rx="8" fill="{GRASS}"/>' +
        "".join(SCENE[sc["kind"]](sc)) + "</svg>",
        M(516, 162, "NEEDED WINDOW · " + ch["caption"].upper(), 11, MUTED),
        f'<svg x="516" y="170" width="440" height="250" viewBox="0 0 440 250"><rect x="0.5" y="0.5" width="439" height="249" rx="8" '
        f'fill="#FFFFFF" stroke="{RULE}"/>' + "".join(CHART[ch["kind"]](ch)).replace("{id}", cid) + "</svg>"]
  who = {"C1 Driver": "THE DRIVER", "C2 openpilot": "OPENPILOT", "C3 panda": "THE PANDA"}[u["ctrl"]]
  bf, bs = {"C1 Driver": BOX["drv"], "C2 openpilot": ("#FFFFFF", MUTED), "C3 panda": BOX["env"]}[u["ctrl"]]
  q = wrap(f"“{m['believes']}”", 46)
  tr = wrap(m["true"], 62)
  h1, h2 = 34 + 23 * len(q), 34 + 20 * len(tr)
  if h1 + 10 + h2 > 206:
    fail(f"{uid} card: belief and truth text too long ({len(q)} + {len(tr)} lines)")
  o += [f'<rect x="24" y="446" width="470" height="{h1}" rx="8" fill="{bf}" stroke="{bs}"/>', M(38, 466, f"WHAT {who} BELIEVES", 11, ink)]
  o += [T(38, 490 + 23 * i, line, 17, INK, 600) for i, line in enumerate(q)]
  y2 = 446 + h1 + 10
  o += [f'<rect x="24" y="{y2}" width="470" height="{h2}" rx="8" fill="#FFFFFF" stroke="{RULE}"/>', M(38, y2 + 20, "WHAT IS TRUE", 11, MUTED)]
  o += [T(38, y2 + 42 + 20 * i, line, 14) for i, line in enumerate(tr)]
  lp = m["loop"]
  net = any(st == "net" for _, _, st in lp["links"])
  o += [M(516, 452, "CONTROL LOOP · BROKEN LINK IN RED" + (", SAFETY NET IN GREEN" if net else ""), 11, MUTED),
        f'<svg x="516" y="460" width="440" height="170" viewBox="0 0 440 170"><rect x="0.5" y="0.5" width="439" height="169" rx="8" '
        f'fill="#FFFFFF" stroke="{RULE}"/>' + "".join(loop(lp)).replace("{id}", cid) + "</svg>"]
  cx, cy = 24, 662
  for text, status in footer(S, uid, m):
    w = tw(text, 12.5) + 22
    if cx + w > CARD_W - 24:
      cx, cy = 24, cy + 32
    f, s = K.STATUS[status] if status else ("#FFFFFF", RULE)
    o += [f'<rect x="{cx:.0f}" y="{cy}" width="{w:.0f}" height="26" rx="13" fill="{f}" stroke="{s}"/>',
          T(cx + 11, cy + 17.5, text, 12.5, s if status else INK, 600 if status else 400)]
    cx += w + 8
  if cy + 26 > CARD_H - 8:
    fail(f"{uid} card: footer chips overflow the card")
  return "".join(o) + "</g>"


def sheet(S, name):
  ctrl, num, who = SHEETS[name]
  ucas = card_ucas(S, ctrl)
  missing = [u for u in ucas if u not in MODEL]
  if missing:
    fail(f"no scene card for {', '.join(missing)} (stpa_scenes.MODEL)")
  cols = 2
  rows = math.ceil(len(ucas) / cols)
  W = GAP + cols * (CARD_W + GAP)
  H = 120 + rows * (CARD_H + GAP) + 30
  b = [f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
       T(GAP, 46, f"Figure {num}. Scene cards: the unsafe control actions of {who}", 28, INK, 700),
       T(GAP, 76, "Each card: the UCA type; a road scene (schematic, loops every 6 s); when the control action is needed against what happens; "
                  "what the controller believes; its control loop with the broken link in red; the loss scenarios and their status.", 14, MUTED),
       T(GAP, 98, "UCA text and types from WP-A-05 §4, statuses, decisions and requirements from stpa-map.yaml. Scenes and charts explain the "
                  "scenarios; they are not simulation or test results.", 14, MUTED)]
  for i, uid in enumerate(ucas):
    b.append(card(S, uid, MODEL[uid], GAP + (i % cols) * (CARD_W + GAP), 120 + (i // cols) * (CARD_H + GAP), i))
  b.append(T(GAP, H - 14, f"WP-A-05 Figure {num} · generated by stpa_scenes.py through fig_a05_stpa.py; regenerate after any change to "
                          "WP-A-05 §4–§5 or stpa-map.yaml.", 12, MUTED))
  defs = ('<defs><marker id="ah-b" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">'
          '<path d="M0 0L10 5L0 10z" fill="#93C5FD"/></marker><marker id="ah-r" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" '
          'markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10z" fill="#FCA5A5"/></marker></defs>')
  title = f"Figure {num}. Scene cards: the unsafe control actions of {who} (WP-A-05 §4)"
  desc = f"One card per UCA of {who}: " + "; ".join(f"{u} {MODEL[u]['title']}" for u in ucas) + "."
  return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">\n'
          f'<title id="t">{escape(title)}</title>\n<desc id="d">{escape(desc)}</desc>\n{defs}\n' + "".join(b) + "\n</svg>\n")


def sheets(S, kit) -> dict[str, str]:
  """The scene sheets, from fig_a05_stpa's Sources S; kit is the fig_a05_stpa module itself (ParseError, STATUS)."""
  global K
  K = kit
  extra = sorted(set(MODEL) - {u for c, _, _ in SHEETS.values() for u in card_ucas(S, c)})
  if extra:
    fail(f"scene card for a UCA that is not in WP-A-05 §4.1–§4.3: {', '.join(extra)}")
  return {name: sheet(S, name) for name in SHEETS}


# ============================================================================ the cards
def P(*items):
  return list(items)


MODEL: dict[str, dict] = {}
DRIFT = [(-10, 70), (100, 70), (190, 70), (250, 72), (310, 84), (360, 108), (400, 138), (430, 172)]
STALE_SCENE = dict(kind="curve", act=CURVE, still=0.36, marks=[(190, 70, 214, 70)], ghost=[(214, 70), (330, 72), (460, 76)],
                   labels=[(250, 16, "without the arrival check: heartbeat still", "#334155"),
                           (250, 29, "arrives, so the stale command runs on", "#334155"),
                           (176, 128, "0.16 s ≈ 4.8 m at 108 km/h", INK, "b", "end"), (176, 142, "stale command, then revoked", "#334155", "", "end")],
                   pills=P((1, "controlsd stalls at the curve entry", "bad", 0.34, 150), (2, "Frames stop: arrival check revokes", "ok", 0.41, 174),
                           (3, "SoC alert; the driver steers the curve", "drv", 0.52, 198)),
                   foot="No panda siren for this case: the alert comes from the SoC")
STALE_CHART = dict(kind="lanes", caption="when authority may stand", t=(-0.1, 0.5),
                   xt=[(0, "0 s"), (0.1, "0.1"), (0.2, "0.2"), (0.3, "0.3"), (0.4, "0.4"), (0.5, "0.5 s")],
                   lanes=[("controlsd", "", [(-0.1, 0, "ok", ""), (0, 0.5, "stall", "stalled")]),
                          ("0x2E4 frames", "", [(-0.1, 0, "tick", ""), (0, 0.1, "tickr", "repeat last command, then stop")]),
                          ("heartbeat", "from pandad", [(-0.1, 0.5, "tickh", "")])],
                   step=("authority", "controls_allowed", 0.0, [(-0.1, 1), (0, 1), (0, 0), (0.5, 0)], [(-0.1, 1), (0.16, 1), (0.16, 0), (0.5, 0)],
                         [(0.16, 1), (0.5, 1)], "without arrival check"),
                   ev=[(0, 1, "bad"), (0.16, 2, "ok")],
                   notes=[(-0.01, 22, "0.1 s repeat, by design", "m", "end"), (0.17, 22, "+50 ms: arrival check", "m"),
                          (0.5, 118, "keeps arriving", "m", "end"), (0.19, 190, "performed: off at ≈ 0.16 s", "perf")],
                   foot="from code reading, not measured")
TICKS_395 = dict(dims=[(170, 190, 200, "#FDE68A"), (260, 190, 200, "#FDE68A"), (415, 190, 200, "#FDE68A")],
                 labels=[(170, 214, "150 m", "#334155", "", "middle"), (260, 214, "240 m", "#334155", "", "middle"),
                         (415, 214, "395 m", "#334155", "", "middle")])
TORQUE_LAT = dict(kind="lat", objects=[("debris", 306, 166)], want=[(20, 157), (170, 157), (230, 120), (330, 118), (440, 157)],
                  act=[(20, 157), (170, 157), (255, 141), (300, 151), (440, 156)], arrows=("drv", "op"), still=0.6,
                  labels=[(328, 112, "where the driver steers", "#BBF7D0"), (352, 150, "where the car goes", "#FECACA"), (318, 184, "debris", PAINT)])

MODEL.update({
  # ------------------------------------------------------------------ C1 driver
  "UCA-01": dict(
    title="The driver engages on a road the item does not handle", ls=["LS-13"],
    believes="The road looks fine. It will handle this.",
    true="Nothing checks road type, curve radius or glare before engaging. Off a highway the item is to refuse to engage (CC-18, "
         "DQ-280), but that gate does not exist yet.",
    scene=dict(kind="lat", faded=True, still=0.8,
               objects=[("cone", x, y) for x, y in ((250, 184), (270, 172), (290, 160), (310, 148), (330, 136), (360, 132), (390, 132), (420, 132))],
               want=[(20, 157), (210, 157), (290, 100), (450, 93)], act=[(20, 157), (200, 157), (290, 156), (330, 155)],
               labels=[(330, 84, "where the lane goes", "#BBF7D0")],
               pills=P((1, "Roadworks ahead, lines faded", "info", 0.15, 6), (2, "Driver engages anyway", "drv", 0.3, 28),
                       (3, "Follows the old lane into the cones", "bad", 0.6, 224))),
    chart=dict(kind="signal", caption="when engaging is allowed", t=(0, 4), y=(0, 1.3, "engagement"), yt=[(0, "off"), (1, "on")],
               xt=[(0, "0 s"), (1, "1"), (2, "2"), (3, "3"), (4, "4 s")], band=[(0, 1.2, 0, 1.3)], hatch=(1.2, 4),
               need=[(1.2, 0.02), (4, 0.02)], perf=[(0, 0.02), (1.6, 0.02), (1.6, 1), (4, 1)],
               ev=[(1.2, 1, "info"), (1.6, 2, "drv"), (2.8, 3, "bad")],
               notes=[(0.05, 0.62, "highway: may engage", "need"), (1.3, 1.18, "off a highway: refuse (CC-18)", "bad"),
                      (1.7, 0.84, "performed: engaged; nothing refuses", "perf"), (1.7, 0.72, "no ODD gate exists yet", "m")]),
    loop=dict(ctrl=("C1 Driver", ["sees easy road"], "drv"), inner=[("process model", "“it can do this”", False)],
              right=("openpilot (C2)", "no ODD gate", "item"), bottom=("PCM cruise (C5)", "engages on SET"),
              links=[("down", "CA-01|engage", "ca"), ("r_in", "FB-01 no|refusal", "dead"), ("up", "FB-03 road", "fb")])),
  "UCA-02": dict(
    title="The driver fights the steering but never brakes or cancels", ls=["LS-14"],
    believes="Steering against it switches it off.",
    true="Steering only overrides; it never disengages (state.py:43). The torque keeps coming. A brake tap or CANCEL would end it, "
         "and the driver gives neither.",
    scene=dict(TORQUE_LAT, pills=P((1, "Driver steers around debris", "drv", 0.28, 6), (2, "Expects that to switch it off", "drv", 0.38, 28),
                                    (3, "No brake, no cancel: the torque goes on", "bad", 0.6, 224))),
    chart=dict(kind="signal", caption="when the driver must disengage", t=(0, 4), y=(0, 1.3, "brake or CANCEL"),
               yt=[(0, "none"), (1, "given")], xt=[(0, "0 s"), (1, "1"), (2, "2"), (3, "3"), (4, "4 s")], band=[(1.2, 4, 0, 1.3)],
               need=[(0, 0.02), (1.2, 0.02), (1.2, 1), (4, 1)], perf=[(0, 0.02), (4, 0.02)],
               ev=[(1.0, 1, "drv"), (1.2, 2, "drv"), (2.6, 3, "bad")],
               notes=[(1.3, 1.12, "needed: brake or CANCEL", "need"), (1.3, 0.16, "performed: nothing", "perf")]),
    loop=dict(ctrl=("C1 Driver", ["keeps steering"], "drv"), inner=[("process model", "“steering ends it”", False)],
              right=("openpilot (C2)", "state: overriding", "item"), bottom=("Brake pedal, CANCEL", "to the PCM, openpilot and panda"),
              links=[("down", "CA-02|not given", "dead"), ("up", "FB-03 wheel feel", "fb"), ("r_in", "FB-01 grey|border only", "bad")])),
  "UCA-03": dict(
    title="The driver takes over too late after a silent loss of steering", ls=["LS-15"],
    believes="It's still steering. My hands are only resting on the wheel.",
    true="An EPS fault started while the driver touched the wheel, so no take-over event is raised (car_events.py:163-168). The only "
         "cue is the EPS-fault siren after 1 s, at worst 1.26 s.",
    scene=dict(kind="curve", act=DRIFT, want=CURVE, still=0.8,
               pills=P((1, "Steering fault while hands touch the wheel", "bad", 0.36, 150), (2, "No take-over alert; siren after 1 s or more", "bad", 0.5, 174),
                       (3, "Driver corrects late, near the edge", "drv", 0.75, 198))),
    chart=dict(kind="signal", caption="when the driver must take over", t=(0, 3), y=(0, 1.3, "driver steering correction"),
               yt=[(0, "none"), (1, "full")], xt=[(0, "0 s"), (1, "1"), (2, "2"), (3, "3 s")], band=[(0.3, 1.3, 0, 1.3)], hatch=(1.3, 3),
               need=[(0, 0.02), (0.3, 0.02), (0.5, 1), (3, 1)], perf=[(0, 0.02), (2.0, 0.02), (2.3, 1), (3, 1)],
               ev=[(0.3, 1, "bad"), (1.56, 2, "bad"), (2.0, 3, "drv")],
               notes=[(0.35, 1.18, "needed: correct at once", "need"), (0.6, 0.42, "performed: late;", "perf"),
                      (0.6, 0.3, "siren at 1–1.26 s only", "m")]),
    loop=dict(ctrl=("C1 Driver", ["hands on wheel"], "drv"), inner=[("process model", "“it's steering”", False)],
              right=("openpilot (C2)", "latActive dropped", "item"), bottom=("Vehicle", "runs wide in the curve"),
              links=[("r_in", "FB-01 alert|suppressed", "dead"), ("down", "CA-03|late", "ca"), ("up", "FB-03 feel", "fb")])),
  "UCA-04": dict(
    title="The driver steers lightly against openpilot and thinks it has let go", ls=["LS-02"],
    believes="I've taken over. The car has let me steer.",
    true="70 raw is under the 100-raw override threshold. openpilot has not noticed and keeps steering back to the lane centre. "
         "Nothing on screen or in sound says otherwise.",
    scene=dict(kind="lat", objects=[("cyclist", 310, 180)], arrows=("drv", "op"), still=0.6,
               want=[(20, 157), (170, 157), (240, 140), (360, 140), (440, 157)], act=[(20, 157), (170, 157), (240, 152), (360, 152), (440, 157)],
               dims=[(276, 149, 173, "#4ADE80"), (290, 161, 173, "#F87171")],
               labels=[(336, 134, "gap the driver wanted", "#BBF7D0"), (350, 170, "gap they got", "#FECACA"), (322, 208, "cyclist", "#334155")],
               pills=P((1, "Driver nudges left, about 70 raw", "drv", 0.28, 6), (2, "Under 100 raw: not detected, no cue", "bad", 0.4, 28),
                       (3, "Passes the cyclist closer than intended", "bad", 0.58, 224))),
    chart=dict(kind="signal", caption="what the driver's input had to do", t=(0, 4), y=(0, 200, "driver torque, raw"),
               yt=[(0, "0"), (100, "100"), (200, "200")], xt=[(0, "0 s"), (1, "1"), (2, "2"), (3, "3"), (4, "4 s")], band=[(1.0, 4, 100, 200)],
               thresh=(100, "override threshold 100 raw"), need=[(1.0, 200), (1.0, 100), (4, 100)],
               perf=[(0, 1), (1, 1), (1.4, 70), (3.6, 70), (3.8, 1), (4, 1)], ev=[(1.0, 1, "drv"), (1.4, 2, "bad"), (2.6, 3, "bad")],
               notes=[(1.1, 178, "needed: torque above 100 raw,", "need"), (1.1, 162, "or brake / cancel", "need"),
                      (1.5, 48, "performed: about 70 raw, held", "perf"), (1.5, 30, "below the line, so openpilot never sees it", "m")]),
    loop=dict(ctrl=("C1 Driver", ["steers lightly", "to make room"], "drv"), inner=[("process model", "“openpilot yielded”", False)],
              right=("openpilot (C2)", "UI and sounds", "item"), bottom=("Steering rack", "driver and openpilot torque add up"),
              links=[("down", "CA-03|steering", "ca"), ("up", "FB-03 wheel feel", "fb"), ("b_r", "0x260 torque, below 100", "grey"),
                     ("r_in", "FB-01 no cue|< 100 raw", "dead")])),
  "UCA-05": dict(
    title="The driver stops supervising while engaged", ls=["LS-09"],
    believes="It's fine to look away for a bit. It will warn me in time.",
    true="With sunglasses or low light the camera loses the eyes and falls back to wheel touch: alerts at 5, 15 and 25 s. At 108 km/h, "
         "25 s is about 750 m unsupervised.",
    scene=dict(kind="lon", still=0.6, objects=[("phone", 440, 30)], **TICKS_395,
               actors=[dict(y=157, body="#DC2626", keys=[(0, 20), (0.92, 430)])],
               pills=P((1, "Sunglasses: the camera can't see the eyes", "info", 0.1, 6), (2, "Falls back to wheel touch", "bad", 0.3, 28),
                       (3, "Driver on the phone; alerts come late", "bad", 0.55, 228))),
    chart=dict(kind="signal", caption="when the driver must supervise", t=(0, 30), y=(0, 1.3, "driver attention"),
               yt=[(0, "away"), (1, "on road")], xt=[(0, "0 s"), (10, "10"), (20, "20"), (30, "30 s")], band=[(0, 30, 0.85, 1.3)],
               need=[(0, 1), (30, 1)], perf=[(0, 1), (3, 1), (3, 0.02), (30, 0.02)], ev=[(1, 1, "info"), (3, 2, "bad"), (25, 3, "bad")],
               notes=[(0.5, 1.18, "needed: supervise all the time", "need"), (4, 0.3, "performed: looks away; wheel-touch alerts", "perf"),
                      (4, 0.18, "at 5, 15, 25 s; TSR-634 adds 150 / 240 / 395 m", "m")]),
    loop=dict(ctrl=("C1 Driver", ["on the phone"], "drv"), inner=[("process model", "“it'll warn me”", False)],
              right=("openpilot (C2)", "DM: low confidence", "item"), bottom=("Vehicle", "at highway speed"),
              links=[("r_out", "FB-07 eyes not seen", "bad"), ("up", "FB-03 motion", "fb")])),
  "UCA-06": dict(
    title="The driver waits for a stop at a red light that never comes", ls=["LS-03"],
    believes="The car will stop for the red light.",
    true="The reference configuration runs Chill mode, which does not stop for lights (D-08). A driver used to Experimental mode, "
         "the old upstream default, expects it to.",
    scene=dict(kind="lon", still=0.75, stop_x=330, objects=[("light", 345, 208)], want=[(20, 157), (316, 157)],
               labels=[(200, 140, "where it should stop", "#BBF7D0")], actors=[dict(y=157, body="#DC2626", keys=[(0, 20), (0.85, 430)])],
               pills=P((1, "Red light ahead", "info", 0.2, 6), (2, "Driver waits for the car to stop", "drv", 0.35, 28),
                       (3, "Chill mode does not stop: runs the light", "bad", 0.62, 228))),
    chart=dict(kind="signal", caption="when the driver must brake", t=(0, 4), y=(0, 1.3, "driver braking"), yt=[(0, "none"), (1, "firm")],
               xt=[(0, "0 s"), (1, "1"), (2, "2"), (3, "3"), (4, "4 s")], band=[(1.0, 3.2, 0, 1.3)],
               need=[(0, 0.02), (1.2, 0.02), (1.5, 1), (3.2, 1)], perf=[(0, 0.02), (4, 0.02)],
               ev=[(0.8, 1, "info"), (1.2, 2, "drv"), (3.0, 3, "bad")],
               notes=[(1.1, 1.18, "needed: brake for the light", "need"), (1.3, 0.16, "performed: no brake; waits for the car", "perf")]),
    loop=dict(ctrl=("C1 Driver", ["waits to stop"], "drv"), inner=[("process model", "“it stops at lights”", False)],
              right=("openpilot (C2)", "Chill: no lights", "item"), bottom=("Brake pedal", "to the PCM and brakes"),
              links=[("down", "CA-02|not given", "dead"), ("r_in", "FB-01: mode,|not limits", "bad")])),
  "UCA-07": dict(
    title="The driver lets go of the gas, thinking the item is off", ls=["LS-36"],
    believes="I pressed the gas, so it switched off.",
    true="Gas only pauses speed control. On release it brakes or accelerates towards the set speed or the lead. The override shows a "
         "grey border with no text or sound.",
    scene=dict(kind="lon", still=0.7,
               actors=[dict(y=157, keys=[(0, 252), (0.92, 422)]), dict(y=157, body="#DC2626", brake=True, keys=[(0, 40), (0.4, 180), (0.6, 225), (0.92, 280)]),
                       dict(y=157, keys=[(0, -52), (0.4, 88), (0.6, 158), (0.92, 210)])],
               pills=P((1, "Driver presses the gas: grey border", "drv", 0.15, 6), (2, "Releases, thinks it is off", "drv", 0.4, 28),
                       (3, "Speed control resumes: brakes for the lead", "bad", 0.55, 228))),
    chart=dict(kind="signal", caption="what the driver expects after release", t=(0, 4), y=(-2.2, 2.2, "acceleration, m/s²"),
               yt=[(-2, "−2"), (0, "0"), (2, "+2")], xt=[(0, "0 s"), (1, "1"), (2, "2"), (3, "3"), (4, "4 s")], band=[(1.6, 4, -0.3, 0.3)],
               need=[(1.6, 0), (4, 0)], perf=[(0, 0), (0.4, 1.2), (1.6, 1.2), (1.7, 0), (2.0, -1.5), (3.4, -1.5), (3.6, 0), (4, 0)],
               ev=[(0.4, 1, "drv"), (1.6, 2, "drv"), (2.0, 3, "bad")],
               notes=[(0.45, 1.5, "driver's gas", "m"), (1.65, 0.5, "expected: coast", "need"), (2.05, -1.85, "performed: brakes for the lead", "perf")]),
    loop=dict(ctrl=("C1 Driver", ["lets go of gas"], "drv"), inner=[("process model", "“it's switched off”", False)],
              right=("openpilot (C2)", "override: grey only", "item"), bottom=("PCM", "resumes speed control"),
              links=[("down", "CA-04|released", "ca"), ("r_in", "FB-01 grey|border only", "dead")])),
  # ------------------------------------------------------------------ C2 openpilot
  "UCA-10": dict(
    title="openpilot keeps steering while the driver steers against it", ls=["LS-01"],
    believes="The driver is overriding, but the lane centre is still my target.",
    true="The driver is steering around debris. Steering only overrides; it never disengages. So openpilot pulls the car back towards "
         "the debris, and the panda passes that torque because its limits ignore the driver.",
    scene=dict(TORQUE_LAT, pills=P((1, "Driver swerves left around debris", "drv", 0.28, 6),
                                    (2, "Override seen, but steering torque continues", "bad", 0.36, 28),
                                    (3, "Pulled back: the car clips the debris", "bad", 0.6, 224))),
    chart=dict(kind="signal", caption="when steering torque is wanted", t=(0, 4), y=(0, 1.3, "torque to lane centre"),
               yt=[(0, "0"), (1, "max")], xt=[(0, "0 s"), (1, "1"), (2, "2"), (3, "3"), (4, "4 s")], band=[(0, 1.2, 0, 1.3)], hatch=(1.2, 4),
               thresh=(1.0, "panda limit 1500 raw: no driver-torque term"), need=[(0, 0.3), (1.2, 0.3), (1.45, 0.05), (4, 0.05)],
               perf=[(0, 0.3), (1.0, 0.3), (1.3, 0.45), (1.8, 0.66), (2.2, 0.72), (4, 0.72)],
               ev=[(1.0, 1, "drv"), (1.2, 2, "bad"), (2.2, 3, "bad")],
               notes=[(0.05, 1.2, "wanted: keep lane", "need"), (2.6, 1.2, "unsafe: driver overriding", "bad", "middle"),
                      (2.3, 0.58, "performed: rises, then holds", "perf"), (2.3, 0.48, "latActive stays true", "m"),
                      (3.95, 0.11, "needed: back off (CC-1)", "need", "end")]),
    loop=dict(ctrl=("C2 openpilot", [], "item"), inner=[("", "overriding = true", True), ("control algorithm", "keeps latActive", False)],
              right=("panda (C3)", "in limit: passes", "env"), bottom=("EPS and steering rack", "driver and openpilot torque fight"),
              links=[("r_out", "CA-05 torque continues", "bad"), ("r_down", "no driver-torque check", "bad"), ("up", "FB-05 driver torque, seen", "fb")])),
  "UCA-11": dict(
    title="openpilot steers out of lane along misleading lines", ls=["LS-10"],
    believes="The lane bends to the right here.",
    true="Lines are faded and old roadworks markings are left. The model plans a wrong path, the torque stays inside the envelope, so "
         "the panda passes it. Only the driver can catch it (SOTIF).",
    scene=dict(kind="lat", faded=True, still=0.75, old_lines=[(150, 125), (260, 142), (360, 166), (460, 186)],
               want=[(20, 157), (440, 157)], act=[(20, 157), (200, 157), (300, 170), (380, 186), (440, 196)],
               labels=[(330, 146, "old marking", "#FDE68A")],
               pills=P((1, "Faded lines, old markings left", "info", 0.15, 6), (2, "Model plans along the old marking", "bad", 0.35, 28),
                       (3, "Torque in limits: the panda passes it", "bad", 0.6, 224))),
    chart=dict(kind="signal", caption="where the car must stay", t=(0, 4), y=(0, 1.3, "offset from lane centre"),
               yt=[(0, "0"), (1, "edge")], xt=[(0, "0 s"), (1, "1"), (2, "2"), (3, "3"), (4, "4 s")], band=[(0, 4, 0, 0.3)],
               thresh=(1.0, "lane edge"), need=[(0, 0.01), (4, 0.01)], perf=[(0, 0.01), (1.2, 0.01), (2.2, 0.6), (3.2, 1.1), (4, 1.18)],
               ev=[(0.5, 1, "info"), (1.2, 2, "bad"), (2.8, 3, "bad")],
               notes=[(0.1, 0.4, "needed: near the centre", "need"), (2.3, 0.42, "performed: drifts to the edge", "perf"),
                      (2.3, 0.32, "the driver is the only control", "m")]),
    loop=dict(ctrl=("C2 openpilot", ["wrong path"], "item"), inner=[("process model", "“lane goes right”", False)],
              right=("panda (C3)", "in limit: passes", "env"), bottom=("EPS and steering rack", "steers along the old marking"),
              links=[("up", "FB-06 cameras:|misleading lines", "bad"), ("r_out", "CA-05 torque", "ca"), ("r_down", "in limit: passes", "grey")])),
  "UCA-12": dict(
    title="openpilot stops steering in a curve and says nothing", ls=["LS-16"],
    believes="The driver touched the wheel, so no warning is needed.",
    true="The saturation warning needs undershoot, lateral acceleration and a saturated controller, and is muted for 2 s after any "
         "steering touch. A non-finite target drops steering for a step with no event.",
    scene=dict(kind="curve", act=DRIFT, want=CURVE, still=0.8,
               pills=P((1, "Curve: steering saturates or drops", "bad", 0.38, 150), (2, "No alert: muted after a steering touch", "bad", 0.5, 174),
                       (3, "The car runs wide", "bad", 0.7, 198))),
    chart=dict(kind="signal", caption="when steering torque is needed", t=(0, 4), y=(0, 1.3, "steering torque"),
               yt=[(0, "0"), (1, "max")], xt=[(0, "0 s"), (1, "1"), (2, "2"), (3, "3"), (4, "4 s")], band=[(1.2, 4, 0.5, 0.95)],
               need=[(0, 0.2), (1.0, 0.2), (1.3, 0.7), (4, 0.7)], perf=[(0, 0.2), (1.2, 0.2), (1.2, 0.01), (4, 0.01)],
               ev=[(1.2, 1, "bad"), (1.35, 2, "bad"), (2.6, 3, "bad")],
               notes=[(1.4, 1.05, "needed: torque through the curve", "need"), (1.4, 0.12, "performed: none, and no alert", "perf")]),
    loop=dict(ctrl=("C2 openpilot", [], "item"), inner=[("", "latActive false", True), ("control algorithm", "raises no alert", False)],
              right=("Driver (C1)", "not told", "drv"), bottom=("EPS and steering rack", "no torque in the curve"),
              links=[("r_out", "CA-07 take-over|alert: none", "dead"), ("down", "CA-05|stops", "ca"), ("up", "FB-05 lat. accel", "fb")])),
  "UCA-13": dict(
    title="openpilot holds a stale steering command after the SoC stalls", ls=["LS-05"], notes=["Not verified on the vehicle"],
    believes="controlsd will send a new command any moment; keep the last one going.",
    true="controlsd has stalled. card repeats the last carControl for about 0.1 s (by design), then the frames stop and the panda's "
         "arrival check revokes authority 50 ms later.",
    scene=STALE_SCENE, chart=STALE_CHART,
    loop=dict(ctrl=("C2 openpilot", [], "item"), inner=[("", "pandad alive", True), ("card", "repeats last cmd", False)],
              right=("panda (C3)", "TX-arrival check", "env"), bottom=("EPS (C4)", "applies LKA torque"),
              links=[("r_out", "CA-05 repeats,|then stops", "bad"), ("r_down", "CA-10 revoked|at ≈ 0.16 s", "net"), ("up", "FB-05 vehicle state", "fb")])),
  "UCA-14": dict(
    title="openpilot accelerates towards a stopped car", ls=["LS-17"],
    believes="The road ahead is clear.",
    true="In Chill mode the model can miss a stopped or slower lead. The planner asks for acceleration, and the panda passes up to "
         "+2.0 m/s² because it knows nothing of leads.",
    scene=dict(kind="lon", still=0.8, want=[(20, 157), (330, 157)], labels=[(200, 140, "where it should stop", "#BBF7D0")],
               actors=[dict(y=157, body=sk.STOPPED, keys=[(0, 402)]), dict(y=157, body="#DC2626", keys=[(0, 20), (0.5, 200), (0.8, 330), (0.92, 352)])],
               pills=P((1, "Stopped car ahead; the model misses it", "bad", 0.2, 6), (2, "Plans acceleration", "bad", 0.35, 28),
                       (3, "Panda passes up to +2.0 m/s²", "bad", 0.55, 228))),
    chart=dict(kind="signal", caption="when braking is needed", t=(0, 4), y=(-3.5, 2.5, "acceleration, m/s²"),
               yt=[(-3.5, "−3.5"), (0, "0"), (2, "+2.0")], xt=[(0, "0 s"), (1, "1"), (2, "2"), (3, "3"), (4, "4 s")], band=[(1, 4, -3.5, -0.5)],
               thresh=(2.0, "panda bound +2.0 m/s²: knows nothing of leads"), need=[(0, 0), (1, 0), (1.4, -2.5), (4, -2.5)],
               perf=[(0, 0.3), (1, 0.3), (1.5, 1.5), (3, 1.5), (3.2, 0.3), (4, 0.3)], ev=[(1, 1, "bad"), (1.4, 2, "bad"), (2.4, 3, "bad")],
               notes=[(1.5, -1.7, "needed: brake for the stopped car", "need"), (1.3, 0.95, "performed: accelerates", "perf")]),
    loop=dict(ctrl=("C2 openpilot", ["plans no lead"], "item"), inner=[("process model", "“road is clear”", False)],
              right=("panda (C3)", "passes ≤ +2.0", "env"), bottom=("PCM, brakes", "accelerates"),
              links=[("up", "FB-06 cameras:|lead missed", "bad"), ("r_out", "CA-06 acceleration", "bad"), ("r_down", "in bounds: passes", "grey")])),
  "UCA-15": dict(
    title="openpilot brakes too late for a car cutting in", ls=["LS-18"],
    believes="There is no car close ahead yet.",
    true="On the Corolla the leads come from the driving model; no radar is parsed. The same late detection removes planner braking "
         "and the forward-collision warning together (DFI-26).",
    scene=dict(kind="lon", still=0.7,
               actors=[dict(path=[(120, 93), (220, 93), (280, 128), (330, 157), (440, 157)], body="#9CA3AF"),
                       dict(y=157, body="#DC2626", keys=[(0, 20), (0.5, 180), (0.75, 240), (0.92, 270)])],
               pills=P((1, "A car cuts in close ahead", "bad", 0.3, 6), (2, "The model sees it late", "bad", 0.45, 28),
                       (3, "Brakes late, capped at −3.5 m/s²", "bad", 0.6, 228))),
    chart=dict(kind="signal", caption="when braking is needed", t=(0, 4), y=(-4.2, 1, "acceleration, m/s²"),
               yt=[(-3.5, "−3.5"), (0, "0")], xt=[(0, "0 s"), (1, "1"), (2, "2"), (3, "3"), (4, "4 s")], band=[(1, 4, -4.2, -0.5)],
               thresh=(-3.5, "cap −3.5 m/s²; beyond it, stock PCS"), need=[(0, 0), (1, 0), (1.2, -2.5), (4, -2.5)],
               perf=[(0, 0), (2, 0), (2.4, -3.5), (4, -3.5)], ev=[(1, 1, "bad"), (2, 2, "bad"), (2.4, 3, "bad")],
               notes=[(1.05, 0.45, "needed: brake from the cut-in", "need"), (0.05, -3.0, "performed: late, then capped", "perf")]),
    loop=dict(ctrl=("C2 openpilot", ["lead seen late"], "item"), inner=[("process model", "“no car ahead”", False)],
              right=("panda (C3)", "passes ≥ −3.5", "env"), bottom=("PCM, brakes", "brake late"),
              links=[("up", "FB-06 cameras:|cut-in seen late", "bad"), ("r_out", "CA-06 braking, late", "bad"), ("r_down", "FCW: same model", "grey")])),
  "UCA-16": dict(
    title="openpilot brakes hard for nothing", ls=["LS-19"],
    believes="There is a car braking ahead.",
    true="A false lead brakes hard. The panda passes any step inside its bounds and has no jerk limit; the host's jerk limit acts "
         "before pitch compensation and the PID.",
    scene=dict(kind="lon", still=0.7, labels=[(330, 150, "nothing there", "#F8FAFC")],
               actors=[dict(y=157, body="#DC2626", brake=True, keys=[(0, 40), (0.4, 200), (0.7, 250), (0.92, 262)]),
                       dict(y=157, keys=[(0, -52), (0.4, 108), (0.7, 190), (0.92, 210)])],
               pills=P((1, "The model sees a lead that isn't there", "bad", 0.3, 6), (2, "Hard braking; no jerk limit in the panda", "bad", 0.42, 28),
                       (3, "The follower closes in", "bad", 0.65, 228))),
    chart=dict(kind="signal", caption="when braking is wanted", t=(0, 4), y=(-4.2, 1, "acceleration, m/s²"),
               yt=[(-3.5, "−3.5"), (0, "0")], xt=[(0, "0 s"), (1, "1"), (2, "2"), (3, "3"), (4, "4 s")], band=[(0, 4, -0.5, 0.5)],
               thresh=(-3.5, "panda passes any in-bound step"), need=[(0, 0), (4, 0)],
               perf=[(0, 0), (1.2, 0), (1.3, -3.5), (2.6, -3.5), (2.8, 0), (4, 0)], ev=[(1.2, 1, "bad"), (1.3, 2, "bad"), (2.4, 3, "bad")],
               notes=[(0.05, 0.65, "needed: keep speed", "need"), (1.38, -2.0, "performed:", "perf"), (1.38, -2.6, "step to −3.5", "perf")]),
    loop=dict(ctrl=("C2 openpilot", ["false lead"], "item"), inner=[("process model", "“car ahead”", False)],
              right=("panda (C3)", "no jerk limit", "env"), bottom=("PCM, brakes", "hard braking"),
              links=[("up", "FB-06 cameras:|false lead", "bad"), ("r_out", "CA-06 hard braking", "bad"), ("r_down", "in-bound step passes", "bad")])),
  "UCA-17": dict(
    title="openpilot loses control and the driver is not told", ls=["LS-20"],
    believes="The take-over alert is on the screen and sounding.",
    true="Every SoC alert goes through ui and soundd, so a hung HMI mutes them all. The panda's own siren covers only heartbeat loss "
         "and an EPS fault.",
    scene=dict(kind="curve", act=DRIFT, want=CURVE, still=0.8,
               pills=P((1, "Control lost in the curve", "bad", 0.38, 150), (2, "Alert raised, but ui and soundd hang", "bad", 0.48, 174),
                       (3, "Driver not told; no panda siren", "bad", 0.66, 198))),
    chart=dict(kind="signal", caption="when the driver must be alerted", t=(0, 4), y=(0, 1.3, "take-over alert"),
               yt=[(0, "none"), (1, "alert")], xt=[(0, "0 s"), (1, "1"), (2, "2"), (3, "3"), (4, "4 s")], band=[(0.5, 4, 0, 1.3)],
               need=[(0, 0.02), (0.5, 0.02), (0.5, 1), (4, 1)], perf=[(0, 0.02), (4, 0.02)],
               ev=[(0.5, 1, "bad"), (0.65, 2, "bad"), (2, 3, "bad")],
               notes=[(0.6, 1.12, "needed: alert within the take-over budget", "need"),
                      (0.7, 0.16, "performed: silent; a hung HMI mutes every alert", "perf")]),
    loop=dict(ctrl=("C2 openpilot", [], "item"), inner=[("", "alert raised", True), ("ui / soundd", "hung", False)],
              right=("Driver (C1)", "not told", "drv"), bottom=("Vehicle", "leaves the curve"),
              links=[("r_out", "CA-07 alert:|not delivered", "dead"), ("up", "FB-05 vehicle state", "fb")])),
  "UCA-18": dict(
    title="openpilot escalates too slowly when the driver looks away", ls=["LS-09"],
    believes="The wheel was touched, so the driver is attentive.",
    true="With low DM confidence the policy falls back to wheel touch: 5, 15 and 25 s, about 750 m at 108 km/h. TSR-634 adds 150, 240 "
         "and 395 m, whichever comes first; it is not yet validated on the vehicle.",
    scene=dict(kind="lon", still=0.6, objects=[("phone", 440, 30)], **TICKS_395,
               actors=[dict(y=157, body="#DC2626", keys=[(0, 20), (0.92, 430)])],
               pills=P((1, "Driver looks away; eyes not seen", "info", 0.1, 6), (2, "Falls back to wheel-touch timing", "bad", 0.3, 28),
                       (3, "Last alert far too late at speed", "bad", 0.6, 228))),
    chart=dict(kind="signal", caption="when each alert is needed", t=(0, 26), y=(0, 3.4, "alert level"),
               yt=[(0, "0"), (1, "1"), (2, "2"), (3, "3")], xt=[(0, "0 s"), (5, "5"), (10, "10"), (15, "15"), (20, "20"), (25, "25 s")],
               need=[(0, 0.02), (5, 0.02), (5, 1), (8, 1), (8, 2), (13.2, 2), (13.2, 3), (26, 3)],
               perf=[(0, 0.04), (5, 0.04), (5, 1.04), (15, 1.04), (15, 2.04), (25, 2.04), (25, 3.04), (26, 3.04)],
               ev=[(0.5, 1, "info"), (8, 2, "bad"), (13.2, 3, "bad")],
               notes=[(13.6, 3.2, "needed: alert 3 at 395 m (13 s)", "need"), (15.5, 1.55, "performed: alert 3 at 25 s", "perf"),
                      (15.5, 1.3, "TSR-634 not yet validated", "m")],
               foot="needed: TSR-634 at 108 km/h"),
    loop=dict(ctrl=("C2 openpilot", ["DM unsure"], "item"), inner=[("process model", "“driver attentive”", False)],
              right=("Driver (C1)", "on the phone", "drv"), bottom=("Driver camera", "sunglasses, low light"),
              links=[("r_out", "CA-07 escalation|5 / 15 / 25 s", "bad"), ("up", "FB-07 eyes|not seen", "bad")])),
  "UCA-19": dict(
    title="openpilot and the PCM disagree on engagement", ls=["LS-06"], notes=["PCM response test open (OI-4)"],
    believes="I'm not engaged, so I command nothing.",
    true="Until v0.3 the panda granted authority on the PCM's rising edge whatever openpilot's state. Now it grants only once the "
         "heartbeat says openpilot is engaged (TSR-301), and openpilot sends cancel at once.",
    scene=dict(kind="lon", still=0.6, ghost=[(150, 157), (460, 157)], labels=[(250, 148, "until v0.3: could accelerate here", "#E5E7EB")],
               actors=[dict(y=157, body="#DC2626", keys=[(0, 30), (0.92, 260)])],
               pills=P((1, "Driver presses SET; openpilot not ready", "drv", 0.2, 6), (2, "PCM engages cruise, openpilot does not", "info", 0.32, 28),
                       (3, "Cancel sent; alert after 1 s", "ok", 0.5, 228))),
    chart=dict(kind="lanes", caption="when authority may stand", t=(-0.2, 1.2),
               xt=[(0, "0 s"), (0.5, "0.5"), (1.0, "1.0 s")],
               lanes=[("PCM cruise", "", [(-0.2, 0, "off", ""), (0, 1.2, "ok", "engaged by SET")]),
                      ("openpilot", "", [(-0.2, 1.2, "off", "not engaged (not ready)")]),
                      ("cancel request", "CANCEL_REQ", [(0.02, 1.2, "tick", "")])],
               step=("authority", "controls_allowed", -0.2, [(-0.2, 0), (1.2, 0)], [(-0.2, 0), (1.2, 0)], [(-0.2, 0), (0, 0), (0, 1), (1.2, 1)],
                     "until v0.3: granted on the PCM edge"),
               ev=[(0, 1, "drv"), (1.0, 2, "ok")],
               notes=[(0.98, 22, "cruiseMismatch alert at 1.0 s", "m", "end"), (0.05, 190, "performed: not granted", "perf")]),
    loop=dict(ctrl=("C2 openpilot", ["not engaged"], "item"), inner=[("process model", "engaged = false", True)],
              right=("panda (C3)", "grants on heartbeat", "env"), bottom=("PCM cruise (C5)", "engaged by SET"),
              links=[("down", "CA-06|cancel", "net"), ("r_out", "CA-08 heartbeat:|not engaged", "net"), ("up", "FB-05 cruise", "fb")])),
  "UCA-20": dict(
    title="openpilot is set up for the wrong car", ls=["LS-12"],
    believes="This is the reference Corolla.",
    true="A wrong brand or parameter leaves the panda in NOOUTPUT, so engagement is refused. Another Toyota with EPS scale 73 and no "
         "flags gets the same parameter: the envelope is right, the host tuning is not.",
    scene=dict(kind="lat", still=0.62, want=[(20, 157), (440, 157)],
               act=[(20, 157), (100, 150), (180, 165), (260, 148), (340, 166), (440, 152)],
               pills=P((1, "Another Toyota, same EPS scale 73", "info", 0.1, 6), (2, "Panda lock passes: the parameter matches", "bad", 0.25, 28),
                       (3, "Host tuning wrong: the car weaves", "bad", 0.5, 224))),
    chart=dict(kind="signal", caption="how well the car must track", t=(0, 4), y=(-1.2, 1.2, "tracking error"),
               yt=[(-1, "−"), (0, "0"), (1, "+")], xt=[(0, "0 s"), (1, "1"), (2, "2"), (3, "3"), (4, "4 s")], band=[(0, 4, -0.25, 0.25)],
               need=[(0, 0), (4, 0)], perf=[(0, 0), (0.5, 0.5), (1, -0.5), (1.5, 0.6), (2, -0.6), (2.5, 0.6), (3, -0.55), (3.5, 0.6), (4, -0.5)],
               ev=[(0.2, 1, "info"), (0.5, 2, "bad"), (1.5, 3, "bad")],
               notes=[(0.05, 0.98, "needed: track the lane", "need"), (1.2, -0.98, "performed: weaves inside the envelope", "perf")]),
    loop=dict(ctrl=("C2 openpilot", ["wrong tuning"], "item"), inner=[("process model", "“a Corolla”", False)],
              right=("panda (C3)", "param 73: accepts", "env"), bottom=("EPS and steering rack", "tuned for another car"),
              links=[("r_out", "CA-08 TOYOTA,|parameter 73", "bad"), ("r_down", "limits right,|tuning wrong", "grey"), ("up", "FB-05 fingerprint", "bad")])),
  "UCA-21": dict(
    title="openpilot has no assured reaction when the driver stays unresponsive", ls=["LS-35"],
    believes="The driver will respond to the alerts.",
    true="After alert 3 and 5 s more, the car brakes to a stop in its lane. Missing: an announcement, hazard lights, an assured hold "
         "and a lockout until the driver responds (DQ-365, TSR-633).",
    scene=dict(kind="lon", still=0.75,
               actors=[dict(y=157, body="#DC2626", brake=True, keys=[(0, 40), (0.3, 200), (0.7, 300), (0.8, 310)]),
                       dict(y=157, keys=[(0, -62), (0.5, 148), (0.85, 236), (0.92, 246)])],
               pills=P((1, "Driver unresponsive: alert 3", "bad", 0.1, 6), (2, "5 s later the car brakes to a stop", "info", 0.3, 28),
                       (3, "No announcement, no hazard lights, hold not proven", "bad", 0.7, 228))),
    chart=dict(kind="signal", caption="what the reaction must include", t=(0, 40), y=(0, 130, "speed, km/h"),
               yt=[(0, "0"), (108, "108")], xt=[(0, "0 s"), (10, "10"), (20, "20"), (30, "30"), (40, "40 s")],
               band=[(15, 18, 0, 130), (30, 40, 0, 130)], need=[(0, 108), (18, 108), (30, 0), (40, 0)], perf=[(0, 106), (18, 106), (30, 1), (40, 1)],
               ev=[(13, 1, "bad"), (18, 2, "info"), (30, 3, "bad")],
               notes=[(0.5, 118, "alert 3 at 13 s (vision)", "m"), (15.2, 124, "announce (TSR-624): missing", "bad"),
                      (3, 70, "performed: brakes to a stop", "perf"), (39.6, 52, "needed: stay held,", "need", "end"),
                      (39.6, 40, "lock out re-engaging", "need", "end"), (39.6, 26, "hold untested (AOU-16)", "m", "end")]),
    loop=dict(ctrl=("C2 openpilot", [], "item"), inner=[("", "forceDecel", True), ("process model", "“driver wakes”", False)],
              right=("Driver (C1)", "unresponsive", "drv"), bottom=("PCM, brakes", "stops; hold untested"),
              links=[("r_out", "CA-07 announce:|missing", "dead"), ("down", "CA-06|brakes", "ca"), ("up", "FB-07 no response", "fb")])),
  # ------------------------------------------------------------------ C3 panda
  "UCA-30": dict(
    title="The panda passes torque the driver cannot counter", ls=["LS-11"],
    believes="Anything inside my limits is controllable.",
    true="The envelope still equals the controller limits: torque 1500, rate 15/25, error 350; −3.5 m/s² both sides. A wrong plan "
         "at full torque and rate passes unchanged.",
    scene=dict(kind="lat", still=0.62, want=[(20, 157), (440, 157)], act=[(20, 157), (180, 157), (240, 135), (300, 112), (360, 105), (440, 110)],
               actors=[dict(y=93, keys=[(0, 180), (0.92, 420)])],
               pills=P((1, "Wrong plan: full torque, full rate", "bad", 0.3, 6), (2, "Passes: limits = controller limits", "bad", 0.42, 28),
                       (3, "The car darts into the next lane", "bad", 0.62, 224))),
    chart=dict(kind="signal", caption="how much torque may pass", t=(0, 4), y=(0, 1700, "torque request, raw"),
               yt=[(0, "0"), (1500, "1500")], xt=[(0, "0 s"), (1, "1"), (2, "2"), (3, "3"), (4, "4 s")], band=[(0, 4, 0, 900)],
               thresh=(1500, "panda limit = controller limit"), need=[(0, 900), (4, 900)],
               perf=[(0, 200), (1.2, 200), (1.6, 1500), (3, 1500), (3.3, 200), (4, 200)], ev=[(1.2, 1, "bad"), (1.6, 2, "bad"), (2.4, 3, "bad")],
               notes=[(0.05, 990, "needed: limit derived", "need"), (0.05, 880, "from the vehicle", "need"),
                      (1.7, 1320, "performed: up to 1500 raw passes", "perf")]),
    loop=dict(ctrl=("C3 panda", [], "env"), inner=[("", "limits enforced", True), ("safety rules", "limits too wide", False)],
              right=("openpilot (C2)", "wrong plan", "item"), bottom=("EPS (C4)", "applies the full torque"),
              links=[("r_in", "CA-05 at|1500 raw", "ca"), ("down", "CA-05|passed", "bad")])),
  "UCA-31": dict(
    title="The panda keeps authority while the driver brakes", ls=["LS-21"],
    believes="The driver is not braking.",
    true="The brake frame 0x226 has no checksum or counter, so a stuck “not pressed” value with live timing passes. The panda keeps "
         "authority while the driver brakes (GAP-01).",
    scene=dict(kind="lon", still=0.7,
               actors=[dict(y=157, body=sk.STOPPED, keys=[(0, 382)]),
                       dict(y=157, body="#DC2626", brake=True, keys=[(0, 40), (0.4, 240), (0.7, 310), (0.92, 320)])],
               pills=P((1, "Driver brakes for traffic", "drv", 0.2, 6), (2, "Brake frame stuck at “not pressed”", "bad", 0.3, 28),
                       (3, "Panda keeps authority while braking", "bad", 0.5, 228))),
    chart=dict(kind="lanes", caption="when authority must end", t=(-0.5, 2), xt=[(0, "0 s"), (1, "1"), (2, "2 s")],
               lanes=[("brake pedal", "driver", [(-0.5, 0, "off", ""), (0, 2, "ok", "pressed")]),
                      ("0x226 brake bit", "no checksum", [(-0.5, 2, "bad", "stuck at “not pressed”")])],
               step=("authority", "controls_allowed", 0.0, [(-0.5, 1), (0, 1), (0, 0), (2, 0)], [(-0.5, 1), (2, 1)], None, ""),
               ev=[(0, 1, "drv")], notes=[(0.1, 190, "performed: kept", "perf")], foot="from the scenario, not measured"),
    loop=dict(ctrl=("C3 panda", ["keeps authority"], "env"), inner=[("process model", "“not braking”", False)],
              right=("openpilot (C2)", "keeps commanding", "item"), bottom=("Brake ECU, 0x226", "stuck frame, live timing"),
              links=[("up", "FB-05 0x226|stuck", "bad"), ("down", "CA-10|not given", "dead"), ("r_in", "CA-05, CA-06", "ca")])),
  "UCA-32": dict(
    title="The panda keeps authority after openpilot has stalled", ls=["LS-05"], notes=["Not verified on the vehicle"],
    believes="Heartbeats keep coming, so openpilot is alive and these frames are fresh.",
    true="controlsd has stalled. card repeats the last command for about 0.1 s, then the frames stop. The heartbeat comes from "
         "pandad, which still runs. The TX-arrival check ends authority 50 ms after the last frame.",
    scene=STALE_SCENE, chart=STALE_CHART,
    loop=dict(ctrl=("C3 panda", ["on heartbeat"], "env"), inner=[("process model", "“SoC alive”", False)],
              right=("openpilot (C2)", "controlsd stalled", "item"), bottom=("EPS (C4)", "applies LKA torque"),
              links=[("r_in", "CA-08 on,|CA-05 stops", "bad"), ("down", "CA-10|at 0.16 s", "net")])),
  "UCA-33": dict(
    title="The panda stays in intercept while stock PCS is not forwarded", ls=["LS-07", "LS-33"],
    believes="I let go of the switches, so stock PCS passes through.",
    true="A watchdog reset releases the switches only through the pull-down. With R2 or R3 open they may stay in intercept: stock "
         "PCS frames are neither passed nor forwarded, and nothing in the item can tell.",
    scene=dict(kind="lon", still=0.85, want=[(20, 157), (320, 157)], labels=[(180, 140, "with PCS: stops here", "#BBF7D0")],
               actors=[dict(y=157, body=sk.STOPPED, keys=[(0, 392)]), dict(y=157, body="#DC2626", keys=[(0, 20), (0.92, 345)])],
               pills=P((1, "Panda resets; switches should release", "info", 0.15, 6), (2, "Pull-down open: stays in intercept", "bad", 0.3, 28),
                       (3, "Stock PCS frames lost: no AEB", "bad", 0.6, 228))),
    chart=dict(kind="lanes", caption="when stock PCS must reach the car", t=(-0.05, 0.25), xt=[(0, "0 s"), (0.1, "0.1"), (0.2, "0.2 s")],
               lanes=[("panda", "", [(-0.05, 0, "ok", ""), (0, 0.25, "stall", "hung, then reset")]),
                      ("SBU1 drive", "", [(-0.05, 0.09, "ok", ""), (0.09, 0.25, "off", "not driven")]),
                      ("switches", "no feedback", [(-0.05, 0.25, "bad", "stay in intercept (R2/R3 open)")])],
               step=("stock PCS", "reaches the car", 0.25, [(-0.05, 1), (0.25, 1)], [(-0.05, 1), (0, 1), (0, 0), (0.25, 0)],
                     [(0.09, 0), (0.09, 1), (0.25, 1)], "pull-down intact: back at ≈ 0.09 s"),
               ev=[(0, 1, "info"), (0.09, 2, "bad")], notes=[(0.1, 190, "performed: lost", "perf")], foot="from the drawing, not bench-tested"),
    loop=dict(ctrl=("C3 panda", ["SBU1 undriven"], "env"), inner=[("process model", "“switch released”", False)],
              right=("Camera (C6)", "stock PCS", "ext"), bottom=("Harness box", "U1/U2, pull-down R2/R3"),
              links=[("down", "CA-09|released", "ca"), ("up", "no position|feedback", "dead"), ("r_down", "CA-13 PCS cut|in the box", "bad")])),
  "UCA-34": dict(
    title="The panda transmits while stock steering still gets through", ls=["LS-22"],
    believes="The switches are in intercept; only my frames reach the car.",
    true="A switch stuck in pass-through (or SBU1 lost, R2/R3 shorted) lets the camera's 0x2E4 and 0x343 reach the car with the "
         "item's. The stock-ECU check sees them only after the 1 s allowance.",
    scene=dict(kind="lat", still=0.55, want=[(20, 157), (440, 157)],
               act=[(20, 157), (90, 157), (140, 150), (180, 163), (220, 149), (260, 164), (300, 150), (340, 162), (440, 156)],
               pills=P((1, "The item transmits steering", "info", 0.15, 6), (2, "A switch is stuck in pass-through", "bad", 0.3, 28),
                       (3, "Stock and item commands both reach the car", "bad", 0.5, 224))),
    chart=dict(kind="lanes", caption="when authority may stand", t=(-0.2, 1.4), xt=[(0, "0 s"), (0.5, "0.5"), (1.0, "1.0 s")],
               lanes=[("item 0x2E4", "", [(-0.2, 1.4, "tick", "")]),
                      ("stock 0x2E4", "camera", [(-0.2, 0, "off", "blocked"), (0, 1.4, "tickr", "")]),
                      ("switches", "no feedback", [(-0.2, 0, "ok", ""), (0, 1.4, "bad", "stuck in pass-through")])],
               step=("authority", "controls_allowed", 0.0, [(-0.2, 1), (0, 1), (0, 0), (1.4, 0)], [(-0.2, 1), (1.0, 1), (1.0, 0), (1.4, 0)], None, ""),
               ev=[(0, 1, "bad"), (1.0, 2, "ok")],
               notes=[(0.97, 22, "stock-ECU check at 1 s", "m", "end"), (0.05, 118, "stock frames pass too", "m"),
                      (1.03, 190, "off", "perf")], foot="from the drawing, not bench-tested"),
    loop=dict(ctrl=("C3 panda", ["transmits"], "env"), inner=[("process model", "“intercepting”", False)],
              right=("Camera (C6)", "stock LKA, ACC", "ext"), bottom=("Harness box", "switch stuck in pass-through"),
              links=[("down", "CA-09|drive lost", "ca"), ("up", "no position|feedback", "dead"), ("r_down", "stock frames|pass too", "bad")])),
  "UCA-35": dict(
    title="The panda drops authority at once, and only the SoC says so", ls=["LS-04"],
    believes="I've just booted; nothing is engaged, so there is nothing to warn about.",
    true="A watchdog reset drops authority at once. The MCU boots SILENT, and every siren source needs controls_allowed or a counter "
         "the reset cleared. Only the SoC alerts, within 0.5 s.",
    scene=dict(kind="curve", act=[(-10, 70), (100, 70), (190, 70), (250, 72), (310, 88), (360, 118), (395, 150), (420, 190)], want=CURVE, still=0.75,
               pills=P((1, "Panda watchdog reset in the curve", "bad", 0.36, 150), (2, "Authority gone; SoC alert within 0.5 s", "info", 0.46, 174),
                       (3, "No siren: the reset cleared what it needs", "bad", 0.6, 198))),
    chart=dict(kind="lanes", caption="when the driver must be warned", t=(-0.1, 0.8), xt=[(0, "0 s"), (0.25, "0.25"), (0.5, "0.5"), (0.75, "0.75 s")],
               lanes=[("panda", "", [(-0.1, 0, "ok", ""), (0, 0.8, "stall", "reset, boots SILENT")]),
                      ("SoC alert", "controlsMismatch", [(0, 0.5, "off", ""), (0.5, 0.8, "ok", "by 0.5 s")]),
                      ("panda siren", "", [(-0.1, 0.8, "off", "cannot sound after a reset")])],
               step=("driver warned", "alert or siren", 0.8, [(-0.1, 0), (0, 0), (0, 1), (0.8, 1)], [(-0.1, 0), (0.5, 0), (0.5, 1), (0.8, 1)], None, ""),
               ev=[(0, 1, "bad"), (0.5, 2, "info")], notes=[(0.03, 190, "performed: SoC alert only", "perf")]),
    loop=dict(ctrl=("C3 panda", ["boots in SILENT"], "env"), inner=[("process model", "state lost", False)],
              right=("openpilot (C2)", "alerts ≤ 0.5 s", "item"), bottom=("Driver (C1)", "hears no siren"),
              links=[("r_out", "FB-04 SILENT,|not allowed", "net"), ("down", "CA-07|no siren", "dead")])),
  "UCA-36": dict(
    title="The item stays engaged while the stock PCS path is cut", ls=["LS-32"],
    believes="Stock PCS reaches the car, through me or around me.",
    true="If the box loses its supply, its switches are undefined and the clamp diodes load both buses. The PCS frames may stop, "
         "whether the panda intercepts or not. Nothing in the item sees the stock path.",
    scene=dict(kind="lon", still=0.85, want=[(20, 157), (320, 157)], labels=[(180, 140, "with PCS: stops here", "#BBF7D0")],
               actors=[dict(y=157, body=sk.STOPPED, keys=[(0, 392)]), dict(y=157, body="#DC2626", keys=[(0, 20), (0.92, 345)])],
               pills=P((1, "The harness box loses its supply", "bad", 0.15, 6), (2, "Stock PCS path cut; nothing sees it", "bad", 0.3, 28),
                       (3, "The item stays engaged; no AEB", "bad", 0.6, 228))),
    chart=dict(kind="lanes", caption="when the item may stay engageable", t=(-0.5, 2), xt=[(0, "0 s"), (1, "1"), (2, "2 s")],
               lanes=[("box supply", "IGN via D1", [(-0.5, 0, "ok", ""), (0, 2, "bad", "lost")]),
                      ("PCS path", "camera to car", [(-0.5, 0, "ok", ""), (0, 2, "bad", "may be cut")]),
                      ("item sees it?", "", [(-0.5, 2, "off", "no feedback")])],
               step=("engageable", "", 0.0, [(-0.5, 1), (0, 1), (0, 0), (2, 0)], [(-0.5, 1), (2, 1)], None, ""),
               ev=[(0, 1, "bad")], notes=[(0.05, 190, "performed: stays engageable", "perf")], foot="from the drawing, not bench-tested"),
    loop=dict(ctrl=("C3 panda", ["forwards blind"], "env"), inner=[("process model", "“PCS path fine”", False)],
              right=("Camera (C6)", "stock PCS", "ext"), bottom=("Harness box", "unpowered: undefined"),
              links=[("up", "no feedback|of the path", "dead"), ("r_down", "CA-13 PCS|may be cut", "bad")])),
})
