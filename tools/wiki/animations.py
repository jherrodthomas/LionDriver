#!/usr/bin/env python3
"""Render the wiki's two animated explainers of a safety requirement as SVG, from the requirement texts.

  req-anatomy.svg             the six parts of TSR-307(a) appear one at a time (trigger, agent, modal, action, object,
                              constraint); then the old text without "continuously for 0.3 s" is shown struck out,
                              the finding of the FRET pilot (rule 4 of the wiki page); then the attributes;
  req-vague-to-verifiable.svg "The system should warn the driver promptly" grows into TSR-516 one question at a time:
                              who and how binding, when it applies, how fast, how long, how loud, independent of the
                              SoC; a checklist ticks as each is answered.

Both loop with CSS animation and need no script. A viewer who asks for reduced motion sees the final frame.

Every requirement phrase drawn on screen is quoted from its source and checked at render time (`problems()`): the
TSR-307 and TSR-516 rows of WP-S-02, and the anatomy table and rules of the wiki page "Deriving and writing safety
requirements". Only the joining "when"/"or" and the line-end punctuation are the animation's own. When a
requirement is reworded, the wiki build fails here instead of animating the old wording. build_wiki.py renders both
next to the pages at each sync (nothing is committed), as it does for infographics.py.

Usage: python3 tools/wiki/animations.py [--out DIR] [--check]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TSC = Path("assurance") / "03-system" / "WP-S-02-technical-safety-requirements.md"
PAGE = Path("wiki") / "Deriving-and-writing-safety-requirements.md"

NAMES = ("req-anatomy.svg", "req-vague-to-verifiable.svg")

FONT = "'Source Sans 3', 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
NAVY, NAVY2, MID, LIGHT, BG = "#0F1B33", "#1E2D4D", "#7F92B3", "#B9C3D6", "#FCFCFB"
SLOT = {"TRIGGER": "#2a78d6", "AGENT": "#6250d6", "MODAL": "#0f766e", "ACTION": "#c2410c", "OBJECT": "#b45309",
        "CONSTRAINT": "#be185d"}
RED, RED_BG, GRN = "#d2553f", "#fdecec", "#1f9d63"
W = 720

# ---------------------------------------------------------------- what is drawn, and where each phrase comes from
# (slot, question, lines); every line is a phrase of TSR-307 in WP-S-02 or of the wiki's anatomy table
ANATOMY = [
  ("TRIGGER", "When?", ['the SoC heartbeat has reported "not engaged"', "continuously for 0.3 s", "while authority is granted"]),
  ("AGENT", "Who acts?", ["the envelope (panda safety code)"]),
  ("MODAL", "Required?", ["shall"]),
  ("ACTION", "Does what?", ["revoke"]),
  ("OBJECT", "To what?", ["authority"]),
  ("CONSTRAINT", "How fast?", ["within the same safety-task tick", "once the 0.3 s is reached"]),
]
ANATOMY_MISSING = "continuously for 0.3 s"    # the clause the FRET pilot found missing (wiki before/after table)
ANATOMY_RULE = "Say how long a condition must hold."
ATTRIBUTES = ["ASIL", "parent", "allocation", "verification"]

# the vague sentence, coloured by the part each word tries to fill: it has no trigger at all
VAGUE_PARTS = [("AGENT", "The system"), ("MODAL", "should"), ("ACTION", "warn"), ("OBJECT", "the driver"),
               ("CONSTRAINT", "promptly.")]
VAGUE = " ".join(s for _slot, s in VAGUE_PARTS)
VAGUE_QUESTIONS = ["who?", "should?", "when?", "promptly?", "how long?", "how loud?"]
# (part, lines of TSR-516 added at this step, checklist question it answers); a line is drawn in its part's colour
# unless PARTS splits it
VERIFIABLE = [
  ("AGENT", ["The safety MCU shall sound its own acoustic warning"], "Who acts, and is it required?"),
  ("TRIGGER", ["when the SoC heartbeat is lost (TSR-407) while authority is granted,",
               "or the envelope revokes authority while it is granted",
               "for any reason other than a driver action that the envelope itself observes,"], "When does it apply?"),
  ("CONSTRAINT", ["within ≤ 0.5 s of detection,"], "How fast, from what event?"),
  ("CONSTRAINT", ["for at least 3 s,"], "For how long?"),
  ("CONSTRAINT", ["at a level audible over the cabin noise,"], "How loud?"),
  ("CONSTRAINT", ["without depending on SoC software."], "Independent of the SoC?"),
]
# INCOSE Guide to Writing Requirements, characteristics C1-C9 of one requirement: the wording shows these ...
INCOSE_SHOWN = ["Unambiguous", "Complete", "Singular", "Verifiable", "Conforming"]
# ... and these need the trace and a review, which no rewording can show
INCOSE_REVIEW = ["Necessary", "Appropriate", "Feasible", "Correct"]
PARTS = {"The safety MCU shall sound its own acoustic warning":
         [("AGENT", "The safety MCU"), ("MODAL", "shall"), ("ACTION", "sound"), ("OBJECT", "its own acoustic warning")]}


def parts(line: str, slot: str) -> list[tuple[str, str]]:
  return PARTS.get(line, [(slot, line)])


def quoted(line: str) -> str:
  """A drawn line as it appears in its source: without the joining word or punctuation the animation adds."""
  return re.sub(r"^(when|or) ", "", line).rstrip(",.")


def sources() -> list[tuple[Path, str, str]]:
  """(file, row key or "" for the whole file, phrase), derived from what is drawn: every drawn line of a requirement
  must be a phrase of its source."""
  out = []
  for slot, _q, lines in ANATOMY:
    if slot == "TRIGGER":
      out += [(TSC, "TSR-307", quoted(line)) for line in lines]
    elif slot in ("AGENT", "CONSTRAINT"):
      out.append((PAGE, "", " ".join(lines)))    # the wiki's anatomy table words these two parts
  out += [(TSC, "TSR-307", "shall revoke authority"), (PAGE, "", ANATOMY_MISSING), (PAGE, "", ANATOMY_RULE)]
  out += [(PAGE, "", a) for a in ATTRIBUTES + INCOSE_SHOWN + INCOSE_REVIEW]
  out += [(TSC, "TSR-516", quoted(line)) for _slot, lines, _q in VERIFIABLE for line in lines]
  return out


def norm(s: str) -> str:
  return re.sub(r"\s+", " ", s.replace("**", "")).strip()


def problems(root: Path = ROOT) -> list[str]:
  errs = [f"PARTS of {line!r} do not join back to it" for line, ps in PARTS.items() if " ".join(x for _, x in ps) != line]
  cache: dict[Path, str] = {}
  for path, key, phrase in sources():
    if path not in cache:
      p = root / path
      cache[path] = p.read_text(encoding="utf-8") if p.exists() else ""
    text = cache[path]
    if key:
      m = re.search(rf"^\| {re.escape(key)} \|.*$", text, re.M)
      text = m.group(0) if m else ""
    if norm(phrase) not in norm(text):
      errs.append(f"{path}{' ' + key if key else ''}: drawn phrase no longer in the source: {phrase!r}")
  return errs


# ---------------------------------------------------------------- SVG pieces

class Timeline:
  """CSS keyframes for elements that fade in at t_in and out at t_out within one loop."""

  def __init__(self, loop: float):
    self.loop, self.css, self.n = loop, [], 0

  def show(self, t_in: float, t_out: float | None = None, fade: float = 0.35) -> str:
    self.n += 1
    k = f"k{self.n}"
    a, f = t_in / self.loop * 100, fade / self.loop * 100
    frames = f"0%{{opacity:0}} {max(a - 0.01, 0):.2f}%{{opacity:0}} {min(a + f, 100):.2f}%{{opacity:1}}"
    if t_out is None:
      frames += " 96%{opacity:1} 100%{opacity:0}"
    else:
      b = t_out / self.loop * 100
      frames += f" {b:.2f}%{{opacity:1}} {min(b + f, 100):.2f}%{{opacity:0}} 100%{{opacity:0}}"
    self.css.append(f"@keyframes {k}{{{frames}}} .{k}{{animation:{k} {self.loop:g}s linear infinite}}")
    return k


def t(x, y, s, size=16, fill=NAVY, weight=400, anchor="start", italic=False) -> str:
  it = ' font-style="italic"' if italic else ""
  return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}"{it}>'
          f"{escape(s)}</text>")


def coloured(x, y, segs: list[tuple[str, str]], size=17, weight=600, italic=False) -> str:
  """One line of text, each segment in the colour of its part."""
  it = ' font-style="italic"' if italic else ""
  spans = " ".join(f'<tspan fill="{SLOT[slot]}">{escape(s)}</tspan>' for slot, s in segs)
  return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}"{it}>{spans}</text>'


def legend(x, y, slots) -> list[str]:
  out = []
  for slot in slots:
    w = len(slot) * 8 + 18
    out += [f'<rect x="{x}" y="{y - 15}" width="{w}" height="21" rx="10.5" fill="{SLOT[slot]}"/>',
            t(x + w / 2, y, slot, 11.5, "#fff", 700, "middle")]
    x += w + 6
  return out


def pills(x0, y, x1, names, filled, prefix="") -> tuple[list[str], int]:
  """Pills wrapped between x0 and x1 from baseline y; returns the items and the baseline after the last row."""
  out, x = [], x0
  for n in names:
    label = prefix + n
    w = len(label) * 7.6 + 24
    if x + w > x1:
      x, y = x0, y + 30
    fill, stroke, ink = (GRN, GRN, "#fff") if filled else ("#fff", MID, MID)
    out += [f'<rect x="{x:.0f}" y="{y - 17}" width="{w:.0f}" height="24" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>',
            t(round(x + w / 2), y, label, 12.5, ink, 700, "middle")]
    x += w + 6
  return out, y


def stick(x, y, pose="point") -> str:
  """A stick figure with its feet at (x, y), about 70 px tall: pointing, or holding a clipboard."""
  o = [f'<g stroke="{NAVY}" stroke-width="3" stroke-linecap="round" fill="none">',
       f'<circle cx="{x}" cy="{y - 62}" r="9" fill="{BG}"/>', f'<line x1="{x}" y1="{y - 53}" x2="{x}" y2="{y - 22}"/>',
       f'<line x1="{x}" y1="{y - 22}" x2="{x - 10}" y2="{y}"/>', f'<line x1="{x}" y1="{y - 22}" x2="{x + 10}" y2="{y}"/>']
  if pose == "point":
    o += [f'<line x1="{x}" y1="{y - 45}" x2="{x + 24}" y2="{y - 58}"/>', f'<line x1="{x}" y1="{y - 45}" x2="{x - 12}" y2="{y - 30}"/>']
  else:
    o += [f'<line x1="{x}" y1="{y - 45}" x2="{x + 14}" y2="{y - 34}"/>', f'<line x1="{x}" y1="{y - 45}" x2="{x - 14}" y2="{y - 34}"/>',
          f'<rect x="{x + 10}" y="{y - 46}" width="14" height="18" rx="2" fill="{BG}"/>']
  return "".join(o) + "</g>"


def svg(h: int, title: str, desc: str, tl: Timeline, body: list[str]) -> str:
  # reduced motion: no animation; transient elements (.tr) hidden, final-frame elements (.fin) shown
  rm = "@media (prefers-reduced-motion: reduce){[class*=k]{animation:none!important} .tr{opacity:0} .fin{opacity:1}}"
  return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" '
          f'aria-labelledby="t d" font-family="{FONT}"><title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>'
          f'<style>{" ".join(tl.css)} {rm}</style><rect width="{W}" height="{h}" fill="{BG}"/>' + "".join(body) + "</svg>\n")


def g(cls: str, items: list[str]) -> str:
  return f'<g class="{cls}">' + "".join(items) + "</g>"


# ---------------------------------------------------------------- the two animations

def anatomy() -> str:
  tl, h = Timeline(14.0), 560
  b = [t(24, 38, "Anatomy of a safety requirement", 24, NAVY, 700), t(24, 62, "Six parts, one at a time · TSR-307(a)", 15, MID)]
  y, missing_y = 92, None
  for i, (slot, q, lines) in enumerate(ANATOMY):
    k, c, hh = tl.show(0.6 + i * 1.1), SLOT[slot], 20 + 20 * len(lines)
    items = [f'<rect x="24" y="{y}" width="{W - 120}" height="{hh}" rx="8" fill="#fff" stroke="{LIGHT}"/>',
             f'<rect x="24" y="{y}" width="8" height="{hh}" rx="3" fill="{c}"/>', t(44, y + 25, slot, 14, c, 700),
             t(150, y + 25, q, 14, MID, 600)]
    for j, line in enumerate(lines):
      items.append(t(250, y + 26 + 20 * j, line, 16, NAVY, 600))
      if line == ANATOMY_MISSING:
        missing_y = y + 26 + 20 * j
    b.append(g(f"{k} fin", items))
    y += hh + 8
  # the FRET finding: the clause was missing before v0.53
  k = tl.show(8.4, 12.4)
  b.append(g(f"{k} tr", [
    f'<rect x="246" y="{missing_y - 15}" width="186" height="22" rx="4" fill="{RED}" opacity="0.18"/>',
    f'<line x1="250" y1="{missing_y - 5}" x2="428" y2="{missing_y - 5}" stroke="{RED}" stroke-width="3"/>',
    t(442, missing_y, "missing in v0.52", 14, RED, 700),
    f'<circle cx="{W - 112}" cy="{missing_y - 6}" r="14" fill="{RED}"/>', t(W - 112, missing_y + 1, "?", 18, "#fff", 700, "middle"),
    f'<rect x="24" y="{h - 118}" width="{W - 48}" height="54" rx="10" fill="{RED_BG}" stroke="{RED}"/>',
    t(40, h - 94, "Rule 4: " + ANATOMY_RULE.lower()[0] + ANATOMY_RULE[1:], 16, RED, 700),
    t(40, h - 73, "The FRET pilot found the old text had no duration.", 14, NAVY)]))
  k = tl.show(7.4)
  items, x = [t(24, h - 36, "Attributes, not part of the sentence:", 14, MID, 600)], 290
  for a in ATTRIBUTES:
    w = len(a) * 8 + 22
    items += [f'<rect x="{x}" y="{h - 52}" width="{w}" height="24" rx="12" fill="{NAVY2}"/>', t(x + w / 2, h - 35, a, 13, "#fff", 600, "middle")]
    x += w + 8
  b.append(g(f"{k} fin", items))
  b.append(stick(W - 50, 300, "point"))
  return svg(h, "Anatomy of a safety requirement (animated)",
             "TSR-307(a) built one part at a time: trigger, the SoC heartbeat has reported not engaged continuously for "
             "0.3 s while authority is granted; agent, the envelope; modal, shall; action, revoke; object, authority; "
             "constraint, within the same safety-task tick once the 0.3 s is reached. Then the clause continuously for "
             "0.3 s is struck out as missing in version 0.52, rule 4: say how long a condition must hold. Attributes "
             "ASIL, parent, allocation and verification are not part of the sentence.", tl, b)


def vague_to_verifiable() -> str:
  tl, h = Timeline(18.0), 620
  b = [t(24, 38, "From vague to verifiable", 24, NAVY, 700), t(24, 62, "One question at a time · TSR-516", 15, MID)]
  k = tl.show(0.3, 2.6)
  b.append(g(f"{k} tr", [f'<rect x="24" y="86" width="{W - 48}" height="64" rx="10" fill="{RED_BG}" stroke="{RED}"/>',
                         coloured(44, 126, [("AGENT", "“" + VAGUE_PARTS[0][1])] + VAGUE_PARTS[1:-1]
                                  + [("CONSTRAINT", VAGUE_PARTS[-1][1] + "”")], 20, italic=True)]))
  for i, q in enumerate(VAGUE_QUESTIONS):
    k, x = tl.show(0.9 + i * 0.2, 2.6), 44 + i * 108
    b.append(g(f"{k} tr", [f'<rect x="{x}" y="160" width="100" height="28" rx="14" fill="{RED}"/>',
                           t(x + 50, 179, q, 14, "#fff", 700, "middle")]))
  n_lines = sum(len(lines) for _, lines, _ in VERIFIABLE)
  box_h = 24 + 28 * n_lines
  k = tl.show(3.0)
  b.append(f'<rect x="24" y="86" width="{W - 48}" height="{box_h}" rx="10" fill="#fff" stroke="{LIGHT}" class="{k} fin"/>')
  y, starts = 112, []
  for i, (slot, lines, _q) in enumerate(VERIFIABLE):
    t0 = 3.0 + i * 2.0
    starts.append(t0)
    k = tl.show(t0)
    b.append(g(f"{k} fin", [coloured(44, y + 28 * j, parts(line, slot)) for j, line in enumerate(lines)]))
    y += 28 * len(lines)
  y = 86 + box_h + 34
  for (slot, _lines, q), t0 in zip(VERIFIABLE, starts):
    k0, k1 = tl.show(3.0), tl.show(t0 + 0.3)
    b.append(g(f"{k0} fin", [f'<rect x="32" y="{y - 17}" width="5" height="22" rx="2" fill="{SLOT[slot]}"/>',
                             f'<rect x="44" y="{y - 17}" width="22" height="22" rx="5" fill="#fff" stroke="{MID}" stroke-width="2"/>',
                             t(78, y, q, 16, NAVY)]))
    b.append(g(f"{k1} fin", [f'<path d="M48,{y - 6} l6,7 l12,-14" fill="none" stroke="{GRN}" stroke-width="4" '
                             'stroke-linecap="round" stroke-linejoin="round"/>']))
    y += 32
  b.append(g(f"{tl.show(3.0)} fin", legend(24, h - 30, list(SLOT))))
  b.append(stick(W - 150, h - 24, "clip"))
  k = tl.show(starts[4])
  b.append(g(f"{k} fin", [f'<g stroke="{NAVY}" stroke-width="2.5" fill="none"><path d="M{W - 110},{h - 40} h80 l-10,-20 h-46 z"/>',
                          f'<circle cx="{W - 92}" cy="{h - 36}" r="7" fill="{BG}"/><circle cx="{W - 46}" cy="{h - 36}" r="7" fill="{BG}"/>',
                          f'<path d="M{W - 20},{h - 80} q10,12 0,24 M{W - 12},{h - 86} q16,18 0,36" stroke="{SLOT["CONSTRAINT"]}"/></g>']))
  # INCOSE C1-C9: what the rewrite shows, and what still needs the trace and a review
  px, py = 336, 86 + box_h + 34
  k = tl.show(starts[-1] + 1.0)
  shown, end = pills(px, py + 26, W - 24, INCOSE_SHOWN, True, "✓ ")
  b.append(g(f"{k} fin", [t(px, py, "INCOSE C1–C9 · shown by the wording", 13, GRN, 700)] + shown))
  k = tl.show(starts[-1] + 2.0)
  ry = end + 34
  review, _ = pills(px, ry + 26, W - 24, INCOSE_REVIEW, False)
  b.append(g(f"{k} fin", [t(px, ry, "needs the trace and a review", 13, MID, 700)] + review))
  full = " ".join(line for _, lines, _ in VERIFIABLE for line in lines)
  return svg(h, "From vague to verifiable (animated)",
             f"The vague sentence '{VAGUE}' with the questions {', '.join(VAGUE_QUESTIONS)}; then TSR-516 grows one "
             f"clause at a time, each part in its own colour (trigger, agent, modal, action, object, constraint), and a "
             f"checklist is ticked: {full}. The INCOSE characteristics the wording shows are ticked: "
             f"{', '.join(INCOSE_SHOWN)}; {', '.join(INCOSE_REVIEW)} need the trace and a review.", tl, b)


def render() -> dict[str, str]:
  return {"req-anatomy.svg": anatomy(), "req-vague-to-verifiable.svg": vague_to_verifiable()}


def write_all(out: Path, root: Path = ROOT) -> None:
  out.mkdir(parents=True, exist_ok=True)
  for name, text in render().items():
    (out / name).write_text(text, encoding="utf-8")


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--out", type=Path, default=None, help="write the SVGs here")
  ap.add_argument("--check", action="store_true", help="fail if a drawn phrase is no longer in its source")
  args = ap.parse_args(argv)
  errs = problems()
  for e in errs:
    print(e, file=sys.stderr)
  if args.out is not None and not errs:
    write_all(args.out)
    print(f"wrote {len(NAMES)} animations to {args.out}")
  return 1 if errs else 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
