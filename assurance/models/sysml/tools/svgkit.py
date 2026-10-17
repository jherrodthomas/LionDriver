"""Drawing kit for the SysML views: palette, Inter text metrics, SVG primitives, orthogonal routing.

The palette and type follow the existing LionDriver work-product figures (for example
WP-S-03 Figure 3-2): slate for QM elements, the envelope orange for C (B‡) and B, teal for sensing,
violet for SoC control of the MCU (FFI), amber for power, purple for untrusted networks.
"""
from __future__ import annotations

from xml.sax.saxutils import escape

FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace"

# ---------------------------------------------------------------- palette

INK = "#0F172A"
INK2 = "#334155"
MUTED = "#64748B"
FAINT = "#94A3B8"
HAIR = "#E2E8F0"
PAPER = "#FFFFFF"
WASH = "#F8FAFC"

SLATE = {"fill": "#FFFFFF", "stroke": "#94A3B8", "chip": "#475569", "wash": "#F8FAFC"}
ENVELOPE = {"fill": "#FFF7ED", "fill2": "#FFEDD5", "stroke": "#C2410C", "chip": "#C2410C", "text": "#9A3412"}
ASIL_B = {"fill": "#FFFBF5", "stroke": "#EA580C", "chip": "#EA580C"}
ML = {"fill": "#EEF2FF", "stroke": "#818CF8", "chip": "#4F46E5"}
OUTSIDE = {"fill": "#F1F5F9", "stroke": "#94A3B8", "chip": "#64748B"}
UNTRUSTED = {"fill": "#FAF5FF", "stroke": "#A855F7", "chip": "#9333EA"}

EDGE = {
  "actuation": {"color": "#C2410C", "width": 2.4, "dash": None, "label": "Actuation, envelope path"},
  "sensing": {"color": "#0F766E", "width": 2.0, "dash": None, "label": "Sensing, HMI, forwarded CAN"},
  "ffi": {"color": "#7C3AED", "width": 2.2, "dash": None, "label": "SoC ↔ MCU link (FFI claim)"},
  "boot": {"color": "#7C3AED", "width": 1.8, "dash": "5 4", "label": "SoC control of MCU boot (FFI, CS)"},
  "power": {"color": "#B45309", "width": 1.8, "dash": "5 4", "label": "Power, ignition"},
  "network": {"color": "#9333EA", "width": 1.6, "dash": "4 4", "label": "Untrusted network"},
  "internal": {"color": "#64748B", "width": 1.4, "dash": None, "label": "Internal data flow"},
  "bus": {"color": "#334155", "width": 2.0, "dash": None, "label": "CAN bus attachment"},
}

INTEGRITY_LABEL = {"C": "C", "BDagger": "B‡", "B": "B", "QMBsup": "QM · B-sup", "QM": "QM", "AoU": "AoU",
                   "Untrusted": "untrusted"}

METRIC_CHARS = "0123456789 !\"#$%&'()*+,-./:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~‡·–—…→←↔≥≤µ°×§±²"
_W400 = [
  63, 41, 61, 62, 65, 61, 62, 57, 62, 62, 28, 29, 47, 63, 64, 98, 64, 30, 36, 36, 50, 66, 29, 46,
  29, 36, 29, 30, 66, 66, 66, 51, 97, 69, 65, 73, 72, 60, 59, 75, 74, 27, 57, 67, 57, 90, 75, 76,
  64, 76, 64, 64, 65, 74, 69, 99, 68, 68, 63, 36, 36, 36, 47, 46, 32, 56, 61, 57, 61, 58, 37, 61,
  59, 24, 24, 55, 24, 88, 59, 60, 61, 61, 38, 53, 33, 59, 56, 82, 55, 56, 55, 43, 33, 43, 66, 49,
  29, 50, 100, 86, 95, 95, 134, 66, 66, 59, 46, 66, 55, 66, 44,
]
_W600 = [
  66, 42, 62, 64, 67, 63, 64, 58, 64, 64, 25, 32, 52, 64, 65, 100, 66, 33, 37, 37, 54, 67, 32, 47,
  32, 38, 32, 33, 67, 67, 67, 54, 100, 73, 66, 74, 72, 61, 59, 75, 75, 28, 58, 70, 57, 92, 76, 77,
  65, 77, 65, 65, 66, 74, 73, 102, 72, 71, 65, 37, 38, 37, 48, 47, 35, 57, 62, 58, 62, 59, 39, 63,
  61, 26, 26, 57, 26, 90, 61, 61, 62, 62, 40, 55, 35, 61, 59, 84, 57, 59, 57, 45, 36, 45, 67, 55,
  32, 50, 100, 96, 95, 95, 134, 67, 67, 61, 46, 67, 58, 67, 45,
]
_W700 = [
  67, 43, 63, 65, 68, 64, 65, 58, 65, 65, 24, 34, 55, 65, 65, 102, 67, 34, 38, 38, 56, 68, 33, 47,
  33, 39, 33, 34, 68, 68, 68, 56, 102, 75, 66, 74, 72, 61, 59, 75, 75, 28, 58, 72, 57, 93, 76, 77,
  65, 78, 66, 65, 67, 73, 75, 104, 74, 73, 66, 38, 39, 38, 49, 48, 37, 58, 63, 59, 63, 60, 40, 63,
  62, 27, 27, 58, 27, 91, 62, 61, 63, 63, 41, 56, 37, 62, 60, 85, 58, 60, 57, 47, 37, 47, 68, 58,
  33, 50, 100, 100, 95, 95, 134, 68, 68, 63, 46, 68, 59, 68, 46,
]
_WIDTHS = {400: dict(zip(METRIC_CHARS, _W400, strict=True)), 600: dict(zip(METRIC_CHARS, _W600, strict=True)),
           700: dict(zip(METRIC_CHARS, _W700, strict=True))}


def text_w(s: str, size: float, weight: int = 400, mono: bool = False) -> float:
  """Advance width of s in Inter (measured in Chromium) or a monospace font."""
  if mono:
    return len(s) * 0.6 * size
  table = _WIDTHS[600 if 500 <= weight < 650 else (700 if weight >= 650 else 400)]
  return sum(table.get(ch, 62) for ch in s) / 100 * size


def wrap(s: str, width: float, size: float, weight: int = 400, mono: bool = False) -> list[str]:
  out, line = [], ""
  for word in s.split():
    cand = word if not line else line + " " + word
    if text_w(cand, size, weight, mono) <= width or not line:
      line = cand
    else:
      out.append(line)
      line = word
  if line:
    out.append(line)
  return out


def clip(s: str, width: float, size: float, weight: int = 400, mono: bool = False) -> str:
  if text_w(s, size, weight, mono) <= width:
    return s
  while s and text_w(s + "…", size, weight, mono) > width:
    s = s[:-1]
  return s.rstrip() + "…"


# ---------------------------------------------------------------- primitives

def f(v: float) -> str:
  return f"{v:.1f}".rstrip("0").rstrip(".")


def text(x, y, s, size=11, fill=INK, weight=400, anchor=None, mono=False, cls=None, extra=""):
  a = f' text-anchor="{anchor}"' if anchor else ""
  w = f' font-weight="{weight}"' if weight != 400 else ""
  fam = f' font-family="{escape(MONO)}"' if mono else ""
  c = f' class="{cls}"' if cls else ""
  return f'<text x="{f(x)}" y="{f(y)}" font-size="{f(size)}" fill="{fill}"{w}{a}{fam}{c}{extra}>{escape(s)}</text>'


def rect(x, y, w, h, fill, stroke=None, rx=8, sw=1.2, dash=None, extra=""):
  s = f' stroke="{stroke}" stroke-width="{f(sw)}"' if stroke else ""
  d = f' stroke-dasharray="{dash}"' if dash else ""
  return f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(rx)}" fill="{fill}"{s}{d}{extra}/>'


def pill(x, y, label, fill, color="#FFFFFF", h=18, size=10, weight=700, stroke=None, anchor="start", mono=False):
  """Rounded label; returns (svg, width). x is the left edge (or the centre with anchor='middle')."""
  w = text_w(label, size, weight, mono) + 14
  if anchor == "middle":
    x -= w / 2
  elif anchor == "end":
    x -= w
  st = f' stroke="{stroke}" stroke-width="1"' if stroke else ""
  return (f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{h}" rx="{f(h / 2)}" fill="{fill}"{st}/>'
          + text(x + w / 2, y + h / 2 + size * 0.36, label, size, color, weight, "middle", mono)), w


def arrow_marker(mid: str, color: str, size: float = 7, back: float = 0) -> str:
  """Arrowhead whose tip sits `back` pixels before the end of the line (to clear a port square)."""
  ref = 8.6 + back * 10 / size
  return (f'<marker id="{mid}" viewBox="0 0 10 10" refX="{f(ref)}" refY="5" markerWidth="{f(size)}" ' +
          f'markerHeight="{f(size)}" orient="auto-start-reverse" markerUnits="userSpaceOnUse">' +
          f'<path d="M0.5 0.8L9.4 5L0.5 9.2z" fill="{color}"/></marker>')


def rounded_path(pts: list[tuple[float, float]], r: float = 7) -> str:
  """SVG path through orthogonal points with rounded corners."""
  pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
  if len(pts) < 2:
    return ""
  d = [f"M{f(pts[0][0])} {f(pts[0][1])}"]
  for i in range(1, len(pts) - 1):
    (x0, y0), (x1, y1), (x2, y2) = pts[i - 1], pts[i], pts[i + 1]
    l1 = abs(x1 - x0) + abs(y1 - y0)
    l2 = abs(x2 - x1) + abs(y2 - y1)
    rr = min(r, l1 / 2, l2 / 2)
    if rr < 0.5 or (x0 == x1 == x2) or (y0 == y1 == y2):
      d.append(f"L{f(x1)} {f(y1)}")
      continue
    ax = x1 - rr * ((x1 > x0) - (x1 < x0))
    ay = y1 - rr * ((y1 > y0) - (y1 < y0))
    bx = x1 + rr * ((x2 > x1) - (x2 < x1))
    by = y1 + rr * ((y2 > y1) - (y2 < y1))
    d.append(f"L{f(ax)} {f(ay)}Q{f(x1)} {f(y1)} {f(bx)} {f(by)}")
  d.append(f"L{f(pts[-1][0])} {f(pts[-1][1])}")
  return "".join(d)


def actor(x, y, color=INK2, scale=1.0):
  """Stick figure (SysML actor) with its head centre at (x, y)."""
  s = scale
  return (f'<g fill="none" stroke="{color}" stroke-width="{f(1.6 * s)}" stroke-linecap="round">' +
          f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(7 * s)}"/>' +
          f'<path d="M{f(x)} {f(y + 7 * s)}V{f(y + 26 * s)}M{f(x - 12 * s)} {f(y + 14 * s)}H{f(x + 12 * s)}' +
          f'M{f(x)} {f(y + 26 * s)}L{f(x - 9 * s)} {f(y + 40 * s)}M{f(x)} {f(y + 26 * s)}L{f(x + 9 * s)} {f(y + 40 * s)}"/></g>')


HATCH = ('<pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">' +
         '<rect width="7" height="7" fill="#F8FAFC"/><line x1="0" y1="0" x2="0" y2="7" stroke="#E2E8F0" ' +
         'stroke-width="3"/></pattern>')
SHADOW = ('<filter id="lift" x="-10%" y="-10%" width="120%" height="130%">' +
          '<feDropShadow dx="0" dy="1.2" stdDeviation="1.4" flood-color="#0F172A" flood-opacity="0.08"/></filter>')


def svg_doc(w: float, h: float, title: str, desc: str, body: list[str], defs: str = "") -> str:
  return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{f(w)}" height="{f(h)}" viewBox="0 0 {f(w)} {f(h)}" ' +
          f'font-family="{escape(FONT)}" role="img" aria-labelledby="t d">\n' +
          f'<title id="t">{escape(title)}</title>\n<desc id="d">{escape(desc)}</desc>\n' +
          f'<defs>{HATCH}{SHADOW}{defs}</defs>\n' +
          f'<rect width="{f(w)}" height="{f(h)}" fill="{PAPER}"/>\n' + "\n".join(body) + "\n</svg>\n")
