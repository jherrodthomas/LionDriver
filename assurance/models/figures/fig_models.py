#!/usr/bin/env python3
"""Draw the figures of the modelling plan (`../README.md`), at phone width (640 px wide, 13–15 px text):

  fig-md-1-tool-map.svg      which tool models which work item, its WP-P-07 classification, what the output may be used for
  fig-md-2-work-items.svg    the §2 work items with their state (Done, Exists, In progress, Draft)

Both are drawn from the tables, not typed in: the work items, their tools and states from §2 of the README, the
tool classes and target elements from the WP-P-07 §3 inventory, and the evidence rule from the README's own
sentence. GATES says which WP-P-07 row classifies which work item; each pairing carries a keyword that must appear
in both rows, and every §2 item that names a tool must have one, so `--check` fails when the tables drift apart,
when a figure is not embedded in the README, or when a committed SVG is stale.

    python3 fig_models.py            # write the SVGs next to this script
    python3 fig_models.py --check    # fail if the tables drifted or an SVG is stale

Standard library only. Output is deterministic. Table parsing is shared with 01-management/figures/figkit.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
MODELS = HERE.parent
ASSURANCE = MODELS.parent
README = MODELS / "README.md"
WP_P_07 = ASSURANCE / "07-supporting" / "WP-P-07-tool-classification-qualification.md"
sys.path.insert(0, str(ASSURANCE / "01-management" / "figures"))
from figkit import FigureError, col, plain, section, table  # noqa: E402

W = 640

# Tools named in the §2 "Tool" column, in the order the figure lists them, with their colour class.
TOOLS = [("Python", "py"), ("OpenModelica", "om"), ("Octave", "oc"), ("SysML v2", "sy")]

# Which WP-P-07 row classifies which §2 work item ("#" cell). The keyword must appear in both rows.
GATES = [("2", "TL-28", "state machine"), ("3", "TL-29", "back to back"), ("4", "TL-30", "plant"),
         ("—", "TL-25", "octave"), ("5", "TL-26", "sysml"), ("5", "TL-27", "sysml"),
         ("6", "TL-49", "fault propagation"), ("7", "TL-51", "structured requirements"),
         ("8", "TL-61", "autosar")]

STATES = {"Done": "s-done", "Exists": "s-exists", "In progress": "s-prog", "Draft": "s-draft"}

EVIDENCE_RULE = "No model output is verification evidence"

STYLE = """<style>
svg { --bg:#ffffff; --ink:#0b0b0b; --ink2:#52514e; --ink3:#8a8984; --grid:#e3e2de; --card:#f7f7f5;
      --py:#2a78d6; --py-bg:#e9f1fb; --om:#6250d6; --om-bg:#efedfb; --oc:#0f8a6e; --oc-bg:#e3f5ef;
      --sy:#b4570f; --sy-bg:#fbeee2; --amb:#c98500; --amb-bg:#fdf4dc; --ok:#2e9e6a; }
@media (prefers-color-scheme: dark) {
  svg { --bg:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --ink3:#8d8c85; --grid:#33322f; --card:#232321;
        --py:#3987e5; --py-bg:#16273c; --om:#9085e9; --om-bg:#26223f; --oc:#2fb08f; --oc-bg:#14302a;
        --sy:#e07b33; --sy-bg:#3a2617; --amb:#eda100; --amb-bg:#3a2f12; --ok:#3fb97d; }
}
.bg { fill:var(--bg); }
.h { font:600 21px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.t { font:15px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.tb { font:600 15px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.t2 { font:13px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink2); }
.t2b { font:600 13px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink2); }
.ta { font:600 13px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--amb); }
.num { font:600 24px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink3); }
.chip { font:600 12px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:#ffffff; }
.chipo { font:600 12px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink2); }
.hair { stroke:var(--grid); stroke-width:1; }
.card { fill:var(--card); stroke:var(--grid); stroke-width:1.2; }
.gate { fill:var(--amb-bg); stroke:var(--amb); stroke-width:1.6; stroke-dasharray:6 4; }
.f-py { fill:var(--py); } .f-om { fill:var(--om); } .f-oc { fill:var(--oc); } .f-sy { fill:var(--sy); }
.o-py { fill:var(--bg); stroke:var(--py); stroke-width:1.4; } .o-om { fill:var(--bg); stroke:var(--om); stroke-width:1.4; stroke-dasharray:4 3; }
.o-oc { fill:var(--bg); stroke:var(--oc); stroke-width:1.4; } .o-sy { fill:var(--bg); stroke:var(--sy); stroke-width:1.4; }
.s-done { fill:var(--ok); } .s-exists { fill:var(--py); } .s-prog { fill:var(--amb); }
.s-draft { fill:var(--bg); stroke:var(--ink3); stroke-width:1.4; stroke-dasharray:4 3; }
.f-ink2 { fill:var(--ink2); }
.arr { stroke:var(--ink2); stroke-width:1.6; fill:none; }
</style>"""

MARKERS = ('<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
           'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="f-ink2"/></marker>')

# approximate advance per character as a share of the font size (system sans)
CHAR = {"t": 0.53, "tb": 0.6, "t2": 0.53, "t2b": 0.56, "ta": 0.56, "chip": 0.58, "chipo": 0.58, "h": 0.56}
SIZE = {"t": 15, "tb": 15, "t2": 13, "t2b": 13, "ta": 13, "chip": 12, "chipo": 12, "h": 21}


# ---------------------------------------------------------------- SVG helpers

def fmt(v: float) -> str:
  return f"{v:.1f}".rstrip("0").rstrip(".")


def el(tag: str, content: str | None = None, **attrs) -> str:
  a = "".join(f' {k.rstrip("_").replace("_", "-")}="{v}"' for k, v in attrs.items() if v not in ("", None))
  return f"<{tag}{a}/>" if content is None else f"<{tag}{a}>{escape(content)}</{tag}>"


def T(x, y, s, cls="t", anchor="") -> str:
  return el("text", s, x=fmt(x), y=fmt(y), class_=cls, text_anchor=anchor)


def R(x, y, w, h, cls="card", rx=8) -> str:
  return el("rect", None, x=fmt(x), y=fmt(y), width=fmt(w), height=fmt(h), rx=rx, class_=cls)


def P(d, cls="arr") -> str:
  return el("path", None, d=d, class_=cls, marker_end="url(#a)")


def width(s: str, cls="t") -> float:
  return len(s) * CHAR[cls] * SIZE[cls]


def wrap(s: str, w: float, cls="t") -> list[str]:
  out, cur = [], ""
  for word in s.split():
    nxt = f"{cur} {word}".strip()
    if cur and width(nxt, cls) > w:
      out.append(cur)
      cur = word
    else:
      cur = nxt
  return out + ([cur] if cur else [])


def para(x, y, s, w, cls="t", anchor="") -> tuple[list[str], float]:
  """Wrapped text; y is the first baseline. Returns the elements and the baseline after the last line."""
  lh = round(SIZE[cls] * 1.35)
  lines = wrap(s, w, cls)
  return [T(x, y + i * lh, ln, cls, anchor) for i, ln in enumerate(lines)], y + len(lines) * lh


def chip(x, y, s, cls) -> tuple[list[str], float]:
  """A chip of height 20 at (x, y) top left; an outlined class (o-…, s-draft) gets dark text."""
  w = width(s, "chip") + 16
  tcls = "chipo" if cls.startswith("o-") or cls == "s-draft" else "chip"
  return [R(x, y, w, 20, cls, rx=10), T(x + w / 2, y + 14, s, tcls, "middle")], w


def svg(h: int, title: str, desc: str, body: list[str]) -> str:
  head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" '
          'aria-labelledby="t d">')
  return "\n".join([head, el("title", title, id="t"), el("desc", desc, id="d"), STYLE, f"<defs>{MARKERS}</defs>",
                    f'<rect class="bg" width="{W}" height="{h}"/>', *body, "</svg>"]) + "\n"


def header(title: str, sub: str) -> list[str]:
  return [T(24, 34, title, "h"), T(24, 56, sub, "t2"),
          el("line", None, x1=24, y1=70, x2=W - 24, y2=70, class_="hair")]


# ---------------------------------------------------------------- sources

def norm(s: str) -> str:
  return re.sub(r"[\s\-]+", " ", s).strip().lower()


class Item:
  def __init__(self, num: str, item: str, tool: str, state: str):
    self.num, self.item, self.tool, self.state_text = plain(num), plain(item), plain(tool), plain(state)
    self.title = re.sub(r"\s*\(.*?\)$", "", self.item.split(":", 1)[0]).strip()
    self.state = next((s for s in sorted(STATES, key=len, reverse=True) if self.state_text.startswith(s)), "")
    found = sorted((self.tool.find(name), name, cls) for name, cls in TOOLS if name in self.tool)
    # (name, colour class, conditional): a tool written as "<tool> only …" is used only when needed
    self.tools = [(name, cls, f"{name} only" in self.tool) for _pos, name, cls in found]


def items(md: str | None = None) -> list[Item]:
  md = md if md is not None else README.read_text(encoding="utf-8")
  head, rows = table(section(md, "## 2. Work items"), "#")
  i = [col(head, c) for c in ("#", "Item", "Tool", "State")]
  return [Item(*(r[k] for k in i)) for r in rows]


def tool_rows() -> dict[str, dict[str, str]]:
  head, rows = table(section(WP_P_07.read_text(encoding="utf-8"), "## 3. Tool inventory"), "ID")
  return {r[0]: {h: plain(c) for h, c in zip(head, r)} for r in rows}


def evidence_rule(md: str | None = None) -> str:
  md = md if md is not None else README.read_text(encoding="utf-8")
  m = re.search(rf"{EVIDENCE_RULE}[^\n]*?\.(?=\s|$)", md)
  if not m:
    raise FigureError(f"README: the sentence starting {EVIDENCE_RULE!r} is gone")
  return plain(m.group(0))


def problems(md: str | None = None) -> list[str]:
  md = md if md is not None else README.read_text(encoding="utf-8")
  out = []
  its, tls = {it.num: it for it in items(md)}, tool_rows()
  for num, tl, key in GATES:
    if num not in its:
      out.append(f"GATES: work item {num!r} not in README §2")
    elif key not in norm(its[num].item + " " + its[num].tool):
      out.append(f"GATES: keyword {key!r} not in README §2 item {num}")
    if tl not in tls:
      out.append(f"GATES: {tl} not in WP-P-07 §3")
    elif key not in norm(tls[tl]["Tool"] + " " + tls[tl]["Use case"]):
      out.append(f"GATES: keyword {key!r} not in WP-P-07 {tl}")
  gated = {n for n, _t, _k in GATES}
  for it in its.values():
    if not it.state:
      out.append(f"README §2 item {it.num}: state {it.state_text[:30]!r} is none of {list(STATES)}")
    if it.tools and it.num not in gated:
      out.append(f"README §2 item {it.num} names a tool but has no WP-P-07 row in GATES")
  try:
    evidence_rule(md)
  except FigureError as e:
    out.append(str(e))
  for name in OUTPUTS:
    if f"(figures/{name})" not in md:
      out.append(f"README does not embed figures/{name}")
  return out


# ---------------------------------------------------------------- figure 1: tool map

def fig_tool_map() -> str:
  its, tls, rule = items(), tool_rows(), evidence_rule()
  rows = [it for it in its if it.tools]
  gates = {}
  for num, tl, _k in GATES:
    gates.setdefault(num, []).append(tl)
  X_TOOL, X_ITEM, W_ITEM, X_GATE, W_GATE, X_USE = 24, 160, 196, 372, 76, 462
  W_USE = W - 24 - X_USE
  body = header("Modelling: tool → what it models → use", "From §2 of this page and the WP-P-07 §3 tool inventory")
  y = 96
  body += [T(X_TOOL, y, "Tool", "t2b"), T(X_ITEM, y, "Models (§2 item)", "t2b"),
           T(X_GATE + W_GATE / 2, y, "WP-P-07", "ta", "middle"), T(X_USE, y, "Output may be used for", "t2b")]
  y += 14
  top = y
  drawn, descs = [], []
  for it in rows:
    tls_here = [tls[t] for t in gates[it.num]]
    title, ty = para(X_ITEM + 10, y + 22, it.title, W_ITEM - 20, "tb")
    title.append(T(X_ITEM + 10, ty, f"#{it.num} · {it.state}" if it.num != "—" else it.state, "t2"))
    ty += 4
    uses, uy = [], y + 20
    for row in tls_here:
      u, uy = para(X_USE + 10, uy, row["Target element"], W_USE - 20, "t2")
      uses += u
      uy += 4
    gy = y + 22
    gate = []
    for row in tls_here:
      gate += [T(X_GATE + W_GATE / 2, gy, row["ID"], "t2b", "middle"),
               T(X_GATE + W_GATE / 2, gy + 16, row["TCL"].replace(" / ", "/"), "t2", "middle")]
      gy += 38
    chips, cy = [], y + 10
    for name, cls, cond in it.tools:
      c, _w = chip(X_TOOL, cy, name, f"o-{cls}" if cond else f"f-{cls}")
      chips += c
      cy += 24
      if cond:
        chips.append(T(X_TOOL, cy + 8, "only if needed", "t2"))
        cy += 18
    h = max(ty, uy, gy - 16, cy) - y + 8
    mid = y + min(h / 2, 21)
    drawn += [R(X_ITEM, y, W_ITEM, h), R(X_USE, y, W_USE, h), *chips, *title, *uses, *gate,
              P(f"M{X_ITEM - 22} {fmt(mid)} H{X_ITEM - 2}"), P(f"M{X_ITEM + W_ITEM + 2} {fmt(mid)} H{X_GATE - 2}"),
              P(f"M{X_GATE + W_GATE + 2} {fmt(mid)} H{X_USE - 2}")]
    descs.append(f"{', '.join(n for n, _c, _d in it.tools)} → {it.title} ({it.state}) → " +
                 "; ".join(f"{r['ID']} {r['TCL']}: {r['Target element']}" for r in tls_here))
    y += h + 10
  # the gate band runs behind the gate column, over every row
  body.append(R(X_GATE, top - 4, W_GATE, y - top - 2, "gate", rx=6))
  body += drawn
  # the evidence rule, from the README
  y += 6
  lines, yb = para(40, y + 22, rule, W - 80, "t")
  body += [R(24, y, W - 48, yb - y + 4, "gate", rx=8), *lines]
  y = yb + 16
  desc = ("Tool map of the modelling plan. " + " | ".join(descs) + ". Rule: " + rule)
  return svg(int(y), "Modelling plan: tools, what they model, and what the output may be used for", desc, body)


# ---------------------------------------------------------------- figure 2: work-item status strip

def fig_status() -> str:
  its = items()
  body = header("Modelling work items: state", "From the §2 table of this page")
  X_NUM, X_CHIP, X_TITLE = 24, 52, 168
  y = 82
  for it in its:
    title, ty = para(X_TITLE, y + 24, it.title, W - 24 - X_TITLE - 12, "tb")
    tool = wrap(it.tool if it.tool != "—" else "no tool", W - 24 - X_TITLE - 12, "t2")
    if len(tool) > 1:
      tool = [tool[0].rstrip(",;:(") + " …"]
    c, _w = chip(X_CHIP, y + 10, it.state, STATES[it.state])
    h = ty + 14 - y
    body += [R(X_NUM - 8, y, W - 2 * (X_NUM - 8), h), T(X_NUM, y + 27, it.num if it.num != "—" else "–", "tb"), *c,
             *title, T(X_TITLE, ty, tool[0], "t2")]
    y += h + 6
  desc = "Work items of the modelling plan: " + "; ".join(
      f"{it.num if it.num != '—' else 'unnumbered'} {it.title}: {it.state}" for it in its)
  return svg(int(y + 10), "Modelling plan: work items and their state", desc, body)


OUTPUTS = {"fig-md-1-tool-map.svg": fig_tool_map, "fig-md-2-work-items.svg": fig_status}


def build() -> dict[str, str]:
  return {name: f() for name, f in OUTPUTS.items()}


def main(argv: list[str]) -> int:
  try:
    errs, out = problems(), build()
  except FigureError as e:
    print(f"fig_models: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    errs += [f"{n} is stale; run assurance/models/figures/fig_models.py" for n, c in out.items()
             if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for e in errs:
      print(f"fig_models: {e}", file=sys.stderr)
    if not errs:
      print(f"fig_models: {len(out)} figures current, tables consistent")
    return 1 if errs else 0
  for n, c in out.items():
    (HERE / n).write_text(c, encoding="utf-8")
  print(f"fig_models: wrote {len(out)} figures")
  for e in errs:
    print(f"fig_models: warning: {e}", file=sys.stderr)
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
