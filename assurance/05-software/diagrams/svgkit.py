"""Minimal deterministic SVG helpers for the generated diagrams (standard library only).

Colours are CSS custom properties with a light and a dark set, so a diagram follows the viewer's colour scheme when
it is shown as an image (GitHub honours prefers-color-scheme inside SVG images). Trace colours are slots 1 and 2 of
the reference categorical palette (blue, orange), validated for both modes.
"""
from __future__ import annotations

from xml.sax.saxutils import escape

FONT = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
CHAR_W = 6.4   # average glyph width at 11.5 px, for wrapping and box sizing (approximate, layout only)

# Categorical slots of the reference palette (light, dark). Fills are tints of a slot over the panel colour, with the
# slot itself as the border, so text on a fill stays in the ink colours. Colour is never the only cue: every
# coloured element also has a name, a glyph or a legend entry.
SLOTS = {1: ("#2a78d6", "#3987e5"), 2: ("#eb6834", "#d95926"), 3: ("#1baf7a", "#199e70"),
         4: ("#eda100", "#c98500"), 6: ("#008300", "#008300"), 7: ("#6250d6", "#9085e9"),
         8: ("#e34948", "#e66767")}
PANEL = ("#ffffff", "#232322")
TINT = (0.16, 0.30)   # share of the slot colour in the fill, light and dark


def mix(hex_a: str, hex_b: str, share_a: float) -> str:
  a = [int(hex_a[i:i + 2], 16) for i in (1, 3, 5)]
  b = [int(hex_b[i:i + 2], 16) for i in (1, 3, 5)]
  return "#" + "".join(f"{round(x * share_a + y * (1 - share_a)):02x}" for x, y in zip(a, b))


def _vars(mode: int) -> str:
  return " ".join(f"--c{n}:{c[mode]}; --f{n}:{mix(c[mode], PANEL[mode], TINT[mode])};" for n, c in SLOTS.items())


STYLE = f"""<style>
svg {{ --surface:#fcfcfb; --panel:#ffffff; --ink:#0b0b0b; --ink2:#52514e; --ink3:#8a8984; --grid:#e3e2de;
       --edge:#3d3c39; --shade:#d9d8d3; --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --hi:#f4f3ef;
       {_vars(0)} }}
@media (prefers-color-scheme: dark) {{
  svg {{ --surface:#1a1a19; --panel:#232322; --ink:#f0efec; --ink2:#c3c2b7; --ink3:#8d8c85; --grid:#33322f;
         --edge:#c3c2b7; --shade:#0e0e0d; --s1:#3987e5; --s2:#d95926; --s3:#199e70; --hi:#2b2b29;
         {_vars(1)} }}
}}
.bg {{ fill:var(--surface); }}
.t {{ font-family:{FONT}; font-size:11.5px; fill:var(--ink); }}
.t2 {{ font-family:{FONT}; font-size:11.5px; fill:var(--ink2); }}
.tm {{ font-family:{MONO}; font-size:10.5px; fill:var(--ink2); }}
.tb {{ font-family:{FONT}; font-size:12.5px; font-weight:600; fill:var(--ink); }}
.th {{ font-family:{FONT}; font-size:15px; font-weight:600; fill:var(--ink); }}
.ts {{ font-family:{FONT}; font-size:10.5px; fill:var(--ink3); }}
.box {{ fill:var(--panel); stroke:var(--edge); stroke-width:1.2; }}
.shadow {{ fill:var(--shade); }}
.hi {{ fill:var(--hi); }}
.edge {{ fill:none; stroke:var(--edge); stroke-width:1.2; }}
.edge.thin {{ stroke-width:0.8; }}
.edge.target {{ stroke:var(--ink3); stroke-dasharray:5 4; }}
.grid {{ stroke:var(--grid); stroke-width:1; }}
.axis {{ stroke:var(--ink3); stroke-width:1; }}
.s1 {{ fill:none; stroke:var(--s1); stroke-width:2; }}
.s2 {{ fill:none; stroke:var(--s2); stroke-width:2; stroke-dasharray:6 3; }}
.s3 {{ fill:none; stroke:var(--s3); stroke-width:2; }}
.band {{ fill:var(--f1); }}
.edge.todo {{ stroke:var(--s2); stroke-dasharray:5 4; }}
.box.dead {{ fill:none; stroke:var(--ink3); stroke-dasharray:5 4; }}
.sup {{ fill:var(--hi); stroke:var(--edge); stroke-width:1.2; }}
.arrow.todo {{ fill:var(--s2); }}
{"".join(f".k{n} {{ fill:var(--f{n}); stroke:var(--c{n}); stroke-width:1.4; }}{chr(10)}" for n in SLOTS)}.m1 {{ fill:var(--s1); }}
.m2 {{ fill:var(--s2); }}
.m3 {{ fill:var(--s3); }}
.arrow {{ fill:var(--edge); }}
.arrow.target {{ fill:var(--ink3); }}
.dot {{ fill:var(--edge); }}
.lbl {{ fill:var(--surface); }}
</style>"""


def esc(s: str) -> str:
  return escape(str(s), {'"': "&quot;"})


def wrap(text: str, width_px: float) -> list[str]:
  per_line = max(8, int(width_px / CHAR_W))
  words, lines, cur = str(text).split(), [], ""
  for w in words:
    if cur and len(cur) + 1 + len(w) > per_line:
      lines.append(cur)
      cur = w
    else:
      cur = f"{cur} {w}" if cur else w
  if cur:
    lines.append(cur)
  return lines or [""]


def text(x, y, s, cls="t", anchor="start"):
  return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="{anchor}">{esc(s)}</text>'


def doc(w: int, h: int, title: str, desc: str, body: list[str]) -> str:
  return "\n".join([
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
    f'aria-labelledby="t d">',
    f"<title id=\"t\">{esc(title)}</title>",
    f"<desc id=\"d\">{esc(desc)}</desc>",
    STYLE,
    f'<rect class="bg" x="0" y="0" width="{w}" height="{h}"/>',
    *body,
    "</svg>",
    "",
  ])


def arrowhead(x, y, dx, dy, cls="arrow", size=7.0):
  n = (dx * dx + dy * dy) ** 0.5 or 1.0
  ux, uy = dx / n, dy / n
  px, py = -uy, ux
  a = (x - ux * size + px * size * 0.45, y - uy * size + py * size * 0.45)
  b = (x - ux * size - px * size * 0.45, y - uy * size - py * size * 0.45)
  return f'<path class="{cls}" d="M{x:.1f},{y:.1f} L{a[0]:.1f},{a[1]:.1f} L{b[0]:.1f},{b[1]:.1f} Z"/>'
