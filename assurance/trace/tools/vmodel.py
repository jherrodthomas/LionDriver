#!/usr/bin/env python3
"""The system V of LD-SDA as one reusable SVG component: one geometry, three sizes, five lenses.

    render(lens, size, highlight=(), goal=None, model=None) -> str   # a standalone SVG

  lens  "status"  box = work-product register status (WP-M-00 §3); verification boxes add "N cases · 0 run"
        "trace"   box = items per level in items/ and the work products; bridge = trace_map.pair_status
        "vv"      verification side only: cases specified, executed, passed
        "goal"    one safety goal: its items per level (left), "named/total" by the paired test cases (right)
        "gate"    box = the gate that first needs the level's work products, coloured by that gate's record
  size  "full"    full page: names, work products, numbers, bridge labels, the gate band G0–G6 and a legend
        "card"    small: process ID and one short number per box
        "locator" text-free thumbnail; the `highlight` levels are solid orange, the rest light grey

The geometry follows the V of ASPICE 4.0: the system trunk (SYS.1–SYS.3 on the left, SYS.4, SYS.5 and VAL.1 on
the right) steps inward, then one dashed bracket holds the parallel engineering arms, one per process group
(SWE, HWE, MLE), each with its specification levels on the left and their verification levels on the right.

Nothing about the V is typed here. Levels, names, work products, test prefixes and pairs come from
trace_map.LEFT, RIGHT, PAIRS and SHORT; the trunk and the arms are derived from the process prefixes in PAIRS
order. Status comes from the register tables of WP-M-00 §3 and its gate list §2, gate outcomes from the gate
records (caselib.gate_records), counts from trace_map.build(). No verification result exists yet:
links/verification.yaml links tests to requirements but records no result, so every executed count is 0; if
an entry carries a result, this module stops and asks to be extended.

One colour rule for every lens: grey dashed = nothing yet; amber = in progress or specified; blue = done in the
design, not verified; green only for approved or baselined work products, or a passed gate or verification;
red = gap; solid orange = locator highlight.

Standard library only; deterministic. `check(drawing)` is the geometry self-check the tests run.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import trace_map as tm

TRACE_DIR = HERE.parent
ASSURANCE_DIR = TRACE_DIR.parent
REPO = ASSURANCE_DIR.parent
REGISTER = ASSURANCE_DIR / "01-management" / "WP-M-00-work-product-register.md"
GATES_DIR = ASSURANCE_DIR / "10-safety-case" / "gates"
CASE_TOOLS = ASSURANCE_DIR / "case-records" / "tools"
VERIFICATION_LINKS = TRACE_DIR / "links" / "verification.yaml"

LENSES = ("status", "trace", "vv", "goal", "gate")
SIZES = ("full", "card", "locator")

# ---------------------------------------------------------------- palette

FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
INK, MUTED, FAINT, LINE = "#0F172A", "#475569", "#94A3B8", "#CBD5E1"
GREEN, GREEN_BG = "#2E9E6A", "#ECFDF5"
HL, HL_STROKE = "#C2410C", "#9A3412"          # locator highlight
LOC_FILL, LOC_STROKE = "#E2E8F0", "#64748B"   # locator, not highlighted
STATE = {  # state -> fill, stroke, dash, legend label
  "none": ("#F8FAFC", FAINT, "5 4", "nothing yet"),
  "prog": ("#FFFBEB", "#D97706", "", "in progress · specified"),
  "done": ("#EFF6FF", "#2563EB", "", "done in the design, not verified"),
  "ok": (GREEN_BG, GREEN, "", "approved, baselined or passed"),
  "gap": ("#FEF2F2", "#D2553F", "", "gap"),
  "dim": ("#F1F5F9", LINE, "", "not part of this lens"),
}
STATE_WORD = {"none": "nothing yet", "prog": "in progress", "done": "done in the design, not verified",
              "ok": "approved or passed", "gap": "gap", "dim": "not shown"}
WP_STATUS = {"S": "Skeleton", "D": "Draft", "R": "In review", "A": "Approved", "B": "Baselined"}
GATE_STATE = {"passed": "ok", "failed": "gap", "not decided": "prog", "not passed": "none"}
LENS_TAG = {"status": "STATUS LENS · work-product register", "trace": "TRACE LENS · items and named links",
            "vv": "V&V LENS · specified and executed", "goal": "GOAL LENS", "gate": "GATE LENS · gate that needs each level"}
ARM_NAME = {"SWE": "SOFTWARE", "HWE": "HARDWARE", "MLE": "MACHINE LEARNING"}

# ---------------------------------------------------------------- structure (derived from trace_map.PAIRS)


def structure() -> tuple[list[tuple[str, str]], list[tuple[str, list[tuple[str, str]]]]]:
  """(trunk pairs, [(process prefix, arm pairs)]) in PAIRS order. The trunk is every pair whose specification
  level is a SYS process; each other prefix of a specification level opens an arm."""
  trunk: list[tuple[str, str]] = []
  arms: dict[str, list[tuple[str, str]]] = {}
  for left, right, _ in tm.PAIRS:
    prefix = tm.level(left).process.split(".")[0]
    if prefix == "SYS":
      trunk.append((left, right))
      continue
    if tm.level(right).process.split(".")[0] != prefix:
      raise SystemExit(f"vmodel.py: pair {left}/{right} crosses process groups; the V layout cannot draw it")
    if prefix not in ARM_NAME:
      raise SystemExit(f"vmodel.py: no arm name for process group {prefix}; add it to ARM_NAME")
    arms.setdefault(prefix, []).append((left, right))
  return trunk, list(arms.items())


# ---------------------------------------------------------------- data


@dataclass
class Data:
  m: tm.Model
  register: dict[str, tuple[str, str]]   # WP ID -> (status letter, gate cell), WP-M-00 §3
  gates: list[tuple[str, str]]           # (gate, name), WP-M-00 §2
  gate_status: dict[str, str]            # gate -> passed / failed / not decided / not passed
  cases: dict[str, int]                  # verification level -> specified cases
  executed: dict[str, int]               # verification level -> executed cases
  passed: dict[str, int]                 # verification level -> passed cases
  children: dict[str, list[str]] = field(default_factory=dict)


def read_register(md: str | None = None) -> tuple[dict[str, tuple[str, str]], list[tuple[str, str]]]:
  """WP-M-00: the §3 register tables (ID -> status, gate) and the §2 gate list."""
  text = md if md is not None else REGISTER.read_text(encoding="utf-8")
  gates_md = text.split("\n## 2.", 1)[1].split("\n## ", 1)[0]
  gates = [(c[0], c[1]) for c in (tm.split_row(ln) for ln in gates_md.splitlines() if re.match(r"^\|\s*G\d\s*\|", ln))]
  body = text.split("\n## 3.", 1)[1].split("\n## 4.", 1)[0]
  reg: dict[str, tuple[str, str]] = {}
  head: list[str] = []
  for ln in body.splitlines():
    if ln.startswith("| ID |"):
      head = tm.split_row(ln)
      continue
    m = re.match(r"^\|\s*\[(WP-[A-Z]-\d\d)\]", ln)
    if m and head:
      cells = tm.split_row(ln)
      reg[m.group(1)] = (cells[head.index("Status")], cells[head.index("Gate")])
  if not gates or not reg:
    raise SystemExit("vmodel.py: WP-M-00 §2 gates or §3 register tables not found")
  return reg, gates


def gate_outcomes(gates: list[tuple[str, str]]) -> dict[str, str]:
  """Per gate: passed when a gate record with a ticked Pass outcome exists, else failed / not decided / not passed."""
  sys.path.insert(0, str(CASE_TOOLS))
  import caselib  # only for gate_records(); importing it reads nothing
  records = caselib.gate_records()
  out = {}
  for g, _ in gates:
    outcomes = [r["outcome"] for r in records if r["gate"] == g]
    out[g] = ("passed" if any(o.startswith("pass") for o in outcomes) else "failed" if "fail" in outcomes
              else "not decided" if outcomes else "not passed")
  return out


def load(m: tm.Model | None = None) -> Data:
  m = m or tm.build()
  reg, gates = read_register()
  missing = sorted({w for lv in tm.LEFT + tm.RIGHT for w in lv.wps} - set(reg))
  if missing:
    raise SystemExit(f"vmodel.py: work products of trace_map.LEFT/RIGHT missing from the WP-M-00 register: {missing}")
  if VERIFICATION_LINKS.exists() and "result:" in VERIFICATION_LINKS.read_text(encoding="utf-8"):
    raise SystemExit(f"{VERIFICATION_LINKS.relative_to(REPO)} now records results: extend vmodel.py to count executed " +
                     "and passed cases from it")
  cases = {lv.key: sum(len(m.specs.get(p, {})) for p in lv.tests) for lv in tm.RIGHT}
  zero = dict.fromkeys(cases, 0)  # no verification result exists (links/verification.yaml holds links, not results)
  children: dict[str, list[str]] = {}
  for i, it in sorted(m.items.items()):
    for p in it.get("parents") or []:
      children.setdefault(p, []).append(i)
  return Data(m, reg, gates, gate_outcomes(gates), cases, dict(zero), dict(zero), children)


def as_data(model) -> Data:
  if model is None:
    return load()
  return model if isinstance(model, Data) else load(model)


# ---------------------------------------------------------------- per-level values


def lv(key: str) -> tm.Level:
  return tm.level(key)


def is_left(key: str) -> bool:
  return any(x.key == key for x in tm.LEFT)


def pair_of(key: str) -> tuple[str, str, tuple[str, ...]]:
  return next(p for p in tm.PAIRS if key in p[:2])


def wp_state(d: Data, key: str) -> str:
  st = [d.register[w][0] for w in lv(key).wps if d.register[w][0] != "N/A"]
  if st and all(s in ("A", "B") for s in st):
    return "ok"
  return "none" if all(s == "S" for s in st) else "prog"


def wp_summary(d: Data, key: str) -> str:
  st = [d.register[w][0] for w in lv(key).wps]
  kinds = sorted(set(st), key=st.index)
  if len(kinds) == 1:
    return WP_STATUS.get(kinds[0], kinds[0]) if len(st) == 1 else f"all {WP_STATUS.get(kinds[0], kinds[0])}"
  return " · ".join(f"{st.count(s)} {WP_STATUS.get(s, s)}" for s in kinds)


def needed_gate(d: Data, key: str) -> str:
  found = [g for w in lv(key).wps for g in re.findall(r"G\d", d.register[w][1])[:1]]
  return min(found) if found else ""


def gate_state(d: Data, gate: str) -> str:
  return GATE_STATE[d.gate_status.get(gate, "not passed")] if gate else "none"


def descendants(d: Data, root: str) -> set[str]:
  seen: set[str] = set()
  todo = [root]
  while todo:
    for c in d.children.get(todo.pop(), []):
      if c not in seen:
        seen.add(c)
        todo.append(c)
  return seen


def goal_counts(d: Data, goal: str, key: str) -> tuple[int, int]:
  """For a goal and any level: (items of the pair's kinds under the goal, how many the paired cases name).
  The pool is trace_map.pool_for, so TSRs allocated to operation are left out as in the trace map."""
  left, right, kinds = pair_of(key)
  ids = descendants(d, goal) | {goal}
  named = {r for p in lv(right).tests for refs in d.m.specs.get(p, {}).values() for r in refs}
  pool = [i for k in kinds for i in tm.pool_for(d.m, right, k) if i in ids]
  return len(pool), sum(1 for i in pool if i in named)


def trace_tokens(d: Data, key: str) -> list[str]:
  level = lv(key)
  traced = [f"{k} {len(d.m.ids.get(k, ()))}" for k in level.kinds if k in d.m.in_trace]
  doc = [f"{k} {len(d.m.ids.get(k, ()))}*" for k in level.kinds if k not in d.m.in_trace]
  der = []
  if key in tm.BOX_DERIVED:
    parent, child = tm.BOX_DERIVED[key]
    done, total, _ = tm.derivation(d.m, parent, child, tm.ALLOC.get((parent, child)))
    der = [f"from {parent} {done}/{total}"]
  return traced + der + doc or ["no items of its own"]


@dataclass
class Box:
  state: str
  lines: list[str]      # full size: detail lines under process and name
  short: str            # card size: one short number
  words: str            # alt text


@dataclass
class Bridge:
  state: str
  text: str


def values(d: Data, lens: str, goal: str | None) -> tuple[dict[str, Box], dict[str, Bridge]]:
  boxes: dict[str, Box] = {}
  bridges: dict[str, Bridge] = {}
  for level in tm.LEFT + tm.RIGHT:
    k = level.key
    left = is_left(k)
    if lens == "status":
      st = wp_state(d, k)
      summary = wp_summary(d, k)
      if left:
        boxes[k] = Box(st, [*level.wps, summary], f"{len(level.wps)} WP", f"{', '.join(level.wps)}: {summary}")
      else:
        n, x = d.cases[k], d.executed[k]
        boxes[k] = Box(st, [f"{n} cases · {x} run", *level.wps, summary], f"{x}/{n}",
                       f"{n} cases specified, {x} run; {', '.join(level.wps)}: {summary}")
    elif lens == "trace":
      if left:
        ls = tm.left_status(d.m, level)
        st = {"all": "done", "some": "prog"}.get(ls, "none")
        n = sum(len(d.m.ids.get(kk, ())) for kk in level.kinds)
        toks = trace_tokens(d, k)
        boxes[k] = Box(st, toks, str(n) if level.kinds else "–", "; ".join(toks))
      else:
        n = d.cases[k]
        pst, ptxt = tm.pair_status(d.m, k, pair_of(k)[2])
        done = sum(int(x.split()[1].split("/")[0]) for x in ptxt.split(" · ")) if pst != "untraced" else 0
        total = sum(int(x.split("/")[1]) for x in ptxt.split(" · ")) if pst != "untraced" else 0
        parts = ptxt.split(" · ")
        toks = [f"{p} {len(d.m.specs.get(p, {}))}" for p in level.tests] + parts
        boxes[k] = Box("prog" if n else "none", toks, f"{done}/{total}",
                       f"{n} cases in {', '.join(level.tests)}; items named: {ptxt}")
    elif lens == "vv":
      if left:
        boxes[k] = Box("dim", [], "", "not part of this lens")
      else:
        n, x, p = d.cases[k], d.executed[k], d.passed[k]
        boxes[k] = Box("gap" if n == 0 else "ok" if n and p == n else "prog", [f"{n} specified", f"{x} executed · {p} passed"],
                       f"{x}/{n}", f"{n} cases specified, {x} executed, {p} passed")
    elif lens == "goal":
      if goal is None:
        raise ValueError("the goal lens needs goal=")
      total, named = goal_counts(d, goal, k)
      kinds = "/".join(pair_of(k)[2])
      if left:
        boxes[k] = Box("done" if total else "none", [f"{kinds} {total}"], str(total), f"{total} {kinds} under {goal}")
      else:
        st = "none" if not total else "gap" if not named else "done" if named == total else "prog"
        boxes[k] = Box(st, [f"{named}/{total} named"] if total else ["no items"], f"{named}/{total}" if total else "–",
                       f"{named} of {total} {kinds} under {goal} named by {', '.join(level.tests)}")
    elif lens == "gate":
      g = needed_gate(d, k)
      st = gate_state(d, g)
      name = dict(d.gates).get(g, "")
      boxes[k] = Box(st, [f"needed at {g}", f"gate {d.gate_status.get(g, 'not passed')}"], g or "–",
                     f"needed at {g} ({name}), {d.gate_status.get(g, 'not passed')}")
    else:
      raise ValueError(f"unknown lens {lens!r}; one of {LENSES}")
  for left, right, kinds in tm.PAIRS:
    n, x = d.cases[right], d.executed[right]
    if lens in ("status", "vv"):
      bridges[left] = Bridge("prog" if n else ("gap" if lens == "vv" else "none"),
                             f"{n} specified · {x} executed" if n else "no cases yet")
    elif lens == "trace":
      pst, ptxt = tm.pair_status(d.m, right, kinds)
      bridges[left] = Bridge({"full": "done", "partial": "prog", "none": "gap"}.get(pst, "none"), ptxt)
    elif lens == "goal":
      total, named = goal_counts(d, goal, right)
      bridges[left] = Bridge(boxes[right].state, f"{named}/{total} named" if total else "")
    else:
      bridges[left] = Bridge("none", "")
  return boxes, bridges


# ---------------------------------------------------------------- geometry

def text_w(s: str, size: float, bold: bool = False, spacing: float = 0.0) -> float:
  """Rough rendered width of s (Inter-like metrics); spacing is letter-spacing in em."""
  w = 0.0
  for ch in s:
    if ch in "il.,:;'|!·":
      w += 0.28
    elif ch in "fjrt() -/*":
      w += 0.36
    elif ch.isupper() or ch in "mwMW≥≤–—…→×&↓↑":
      w += 0.70
    elif ch.isdigit():
      w += 0.56
    else:
      w += 0.55
  return (w * (1.06 if bold else 1.0) + spacing * len(s)) * size


GEO = {  # per size: box height and row pitch of the trunk and the arms, gap above the arms, fonts
  "full": {"top": 56, "bh": 66, "pitch": 88, "ah": 66, "apitch": 82, "arm_top": 62, "sw": 1.6, "conn": 1.4},
  "card": {"top": 16, "bh": 88, "pitch": 108, "ah": 84, "apitch": 100, "arm_top": 62, "sw": 2.4, "conn": 3},
  "locator": {"top": 16, "bh": 88, "pitch": 108, "ah": 84, "apitch": 100, "arm_top": 30, "sw": 5, "conn": 4},
}
W, MARGIN, STEP, BW, IN_GAP, ARM_GAP = 1120, 24, 74, 236, 26, 24


@dataclass
class Layout:
  pos: dict[str, tuple[float, float, float, float]]
  arms: list[tuple[str, float, float, float]]   # prefix, x, width, label baseline y
  bracket: tuple[float, float, float, float]
  height: float
  band_y: float = 0
  legend_y: float = 0


def layout(size: str) -> Layout:
  g = GEO[size]
  trunk, arms = structure()
  pos: dict[str, tuple[float, float, float, float]] = {}
  for i, (left, right) in enumerate(trunk):
    y = g["top"] + i * g["pitch"]
    pos[left] = (MARGIN + i * STEP, y, BW, g["bh"])
    pos[right] = (W - MARGIN - BW - i * STEP, y, BW, g["bh"])
  y0 = g["top"] + (len(trunk) - 1) * g["pitch"] + g["bh"] + 26
  x0, x1 = 44, W - 44
  weights = [1 + 0.15 * len(rows) for _, rows in arms]
  avail = x1 - x0 - ARM_GAP * (len(arms) - 1)
  ay = y0 + g["arm_top"]
  x, placed = float(x0), []
  for (prefix, rows), wt in zip(arms, weights, strict=True):
    aw = avail * wt / sum(weights)
    bw = (aw - IN_GAP) / 2
    for j, (left, right) in enumerate(rows):
      y = ay + j * g["apitch"]
      pos[left] = (x, y, bw, g["ah"])
      pos[right] = (x + aw - bw, y, bw, g["ah"])
    placed.append((prefix, x, aw, ay - (10 if size == "full" else 14)))
    x += aw + ARM_GAP
  bottom = max(y + h for _, y, _, h in pos.values()) + 22
  bracket = (30, y0, W - 60, bottom - y0)
  if size == "full":
    band_y = bottom + 16
    legend_y = band_y + 22 + 30
    return Layout(pos, placed, bracket, legend_y + 16, band_y, legend_y)
  return Layout(pos, placed, bracket, bottom + 14)


# ---------------------------------------------------------------- drawing

def fmt(v: float) -> str:
  return f"{v:.1f}".rstrip("0").rstrip(".")


def el(tag: str, text: str | None = None, **attrs) -> str:
  a = "".join(f' {k.rstrip("_").replace("_", "-")}="{v}"' for k, v in attrs.items() if v not in ("", None))
  return f"<{tag}{a}/>" if text is None else f"<{tag}{a}>{escape(text)}</{tag}>"


@dataclass
class Drawing:
  width: float
  height: float
  title: str
  desc: str
  body: list[str] = field(default_factory=list)
  boxes: list[tuple[str, float, float, float, float]] = field(default_factory=list)       # key, x, y, w, h
  texts: list[tuple[str, float, float, float, float, str | None]] = field(default_factory=list)  # s, x0, y0, x1, y1, box
  lines: list[tuple[float, float, float, float]] = field(default_factory=list)
  states: dict[str, str] = field(default_factory=dict)    # level key -> state drawn

  def rect(self, x, y, w, h, fill, stroke, sw=1.6, rx=8, dash="", key=None):
    self.body.append(el("rect", None, x=fmt(x), y=fmt(y), width=fmt(w), height=fmt(h), rx=rx, fill=fill, stroke=stroke,
                        stroke_width=sw, stroke_dasharray=dash))
    if key:
      self.boxes.append((key, x, y, w, h))

  def text(self, x, y, s, size, fill=INK, weight="", anchor="", within=None, spacing=0.0):
    w = text_w(s, size, weight == 700, spacing)
    x0 = x - w / 2 if anchor == "middle" else x - w if anchor == "end" else x
    self.texts.append((s, x0, y - size * 0.78, x0 + w, y + size * 0.24, within))
    self.body.append(el("text", s, x=fmt(x), y=fmt(y), font_size=fmt(size), fill=fill, font_weight=weight,
                        text_anchor=anchor, letter_spacing=f"{spacing}em" if spacing else ""))

  def line(self, x1, y1, x2, y2, stroke=FAINT, sw=1.4, dash="", marker="vm-a"):
    self.lines.append((x1, y1, x2, y2))
    self.body.append(el("line", None, x1=fmt(x1), y1=fmt(y1), x2=fmt(x2), y2=fmt(y2), stroke=stroke, stroke_width=sw,
                        stroke_dasharray=dash, marker_end=f"url(#{marker})" if marker else ""))


def marker_defs(body: list[str]) -> str:
  """Arrowhead markers, only those the body uses (so an unused colour never appears in the file)."""
  used = set(re.findall(r"url\(#(vm-[a-z]+)\)", "".join(body)))
  out = []
  for name, colour in (("vm-a", FAINT), *((f"vm-{k}", v[1]) for k, v in STATE.items())):
    if name not in used:
      continue
    out.append(f'<marker id="{name}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" ' +
               f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{colour}"/></marker>')
  return "<defs>" + "".join(out) + "</defs>"


def pack(tokens: list[str], width: float, size: float, max_lines: int) -> list[str]:
  """Join tokens with " · " into at most max_lines lines no wider than width (a token never splits)."""
  lines: list[str] = []
  for t in tokens:
    if lines and text_w(lines[-1] + " · " + t, size) <= width:
      lines[-1] += " · " + t
    else:
      lines.append(t)
  if len(lines) > max_lines:
    raise SystemExit(f"vmodel.py: {tokens} needs {len(lines)} lines in a box {width:.0f} wide; widen the layout")
  return lines


def levels_named(keys) -> str:
  order = [x.key for x in tm.LEFT + tm.RIGHT]
  return ", ".join(lv(k).process for k in sorted(keys, key=order.index))


def draw(lens: str, size: str, highlight=(), goal: str | None = None, model=None) -> Drawing:
  if lens not in LENSES or size not in SIZES:
    raise ValueError(f"lens must be one of {LENSES}, size one of {SIZES}")
  highlight = set(highlight)
  unknown = highlight - {x.key for x in tm.LEFT + tm.RIGHT}
  if unknown:
    raise ValueError(f"unknown levels to highlight: {sorted(unknown)}")
  if lens != "goal":
    goal = None
  lay = layout(size)
  loc = size == "locator"
  if loc:
    lit = levels_named(highlight) or "none"
    dr = Drawing(W, lay.height, f"System V locator · {lit}",
                 f"Locator thumbnail of the system V (ASPICE 4.0). Highlighted: {lit}.")
    boxes, bridges = {}, {}
  else:
    d = as_data(model)
    boxes, bridges = values(d, lens, goal)
    head = f"System V · {lens} lens" + (f" · {goal}" if goal else "")
    dr = Drawing(W, lay.height, head, "")
  g = GEO[size]
  dr.rect(0, 0, W, lay.height, "#FFFFFF", "none", sw=0, rx=0)
  trunk, arms = structure()
  # connectors down the left and up the right of the trunk, into and out of the bracket
  for i in range(len(trunk) - 1):
    (lx, ly, lw, lh), (nx, ny, _, _) = lay.pos[trunk[i][0]], lay.pos[trunk[i + 1][0]]
    dr.line(lx + 40, ly + lh, nx + 40, ny - 1, sw=g["conn"])
    (rx, ry, rw, rh), (px, py, pw, ph) = lay.pos[trunk[i + 1][1]], lay.pos[trunk[i][1]]
    dr.line(rx + rw - 40, ry, px + pw - 40, py + ph + 1, sw=g["conn"])
  bx, by, bwid, bh = lay.bracket
  dr.rect(bx, by, bwid, bh, "none", LINE, sw=1.4 if not loc else 3, rx=14, dash="3 4" if not loc else "8 8")
  sx, sy, sw_, sh = lay.pos[trunk[-1][0]]
  tx, ty, tw, th = lay.pos[trunk[-1][1]]
  dr.line(sx + sw_ / 2, sy + sh, sx + sw_ / 2, by - 1, sw=g["conn"])
  dr.line(tx + tw / 2, by, tx + tw / 2, ty + th + 1, sw=g["conn"])
  if size == "full":
    tops = [rows[0] for _, rows in arms]
    dr.text(bx + 18, by + 18, f"↓ allocated from {lv(trunk[-1][0]).process} to " + " · ".join(lv(a).process for a, _ in tops),
            10.5, fill=MUTED)
    dr.text(bx + bwid - 18, by + 18, " · ".join(lv(b).process for _, b in tops) + f" integrate into {lv(trunk[-1][1]).process} ↑",
            10.5, fill=MUTED, anchor="end")
  for prefix, ax, aw, label_y in lay.arms:
    rows = dict(arms)[prefix]
    if not loc:
      dr.text(ax + aw / 2, label_y, ARM_NAME[prefix], 10 if size == "full" else 22, fill=MUTED, weight=700,
              anchor="middle", spacing=0.08)
    for j in range(len(rows) - 1):
      a, b = lay.pos[rows[j][0]], lay.pos[rows[j + 1][0]]
      dr.line(a[0] + 20, a[1] + a[3], b[0] + 20, b[1] - 1, sw=g["conn"])
      a, b = lay.pos[rows[j + 1][1]], lay.pos[rows[j][1]]
      dr.line(a[0] + a[2] - 20, a[1], b[0] + b[2] - 20, b[1] + b[3] + 1, sw=g["conn"])
  # bridges: verification level -> the level it verifies
  for left, right, _ in tm.PAIRS:
    lx, ly, lw, lh = lay.pos[left]
    rx, ry, rw, rh = lay.pos[right]
    y = ly + lh / 2
    if loc:
      dr.line(rx - 2, y, lx + lw + 6, y, stroke=FAINT, sw=g["conn"], dash="10 8")
      continue
    br = bridges[left]
    st = "dim" if highlight and left not in highlight and right not in highlight else br.state
    colour = STATE[st][1]
    dr.line(rx - 2, y, lx + lw + 6, y, stroke=colour, sw=2 if size == "full" else 4, dash="6 4" if size == "full" else "12 8",
            marker=f"vm-{st}")
    if size == "full" and br.text and rx - (lx + lw) > text_w(br.text, 11, True) + 40:
      dr.text((rx + lx + lw) / 2, y - 7, br.text, 11, fill=colour, weight=700, anchor="middle")
  # boxes
  pad = 10
  for key, (x, y, w, h) in lay.pos.items():
    level = lv(key)
    if loc:
      on = key in highlight
      dr.rect(x, y, w, h, HL if on else LOC_FILL, HL_STROKE if on else LOC_STROKE, sw=g["sw"], rx=12, key=key)
      dr.states[key] = "highlight" if on else "locator"
      continue
    b = boxes[key]
    st = "dim" if highlight and key not in highlight else b.state
    dr.states[key] = st
    fill, stroke, dash, _ = STATE[st]
    dr.rect(x, y, w, h, fill, stroke, sw=g["sw"], rx=8 if size == "full" else 12, dash=dash if size == "full" else
            " ".join(str(int(v) * 2) for v in dash.split()), key=key)
    ink = MUTED if st == "dim" else INK
    if size == "full":
      dr.text(x + pad, y + 18, level.process, 12.5, fill=ink, weight=700, within=key)
      dr.text(x + pad, y + 32, tm.SHORT[key], 10.5, fill=MUTED, within=key)
      if st != "dim":
        for i, ln in enumerate(pack(b.lines, w - 2 * pad, 10.5, 2)):
          dr.text(x + pad, y + 47 + 13 * i, ln, 10.5, within=key)
    else:
      dr.text(x + w / 2, y + h / 2 - 4, level.process, 34, fill=ink, weight=700, anchor="middle", within=key)
      if b.short and st != "dim":
        dr.text(x + w / 2, y + h / 2 + 30, b.short, 28, fill=INK, anchor="middle", within=key)
  if size == "full":
    tag = LENS_TAG[lens] + (f" · {goal}" if goal else "")
    tw_ = text_w(tag, 11.5, True, 0.06) + 28
    dr.rect(W / 2 - tw_ / 2, 12, tw_, 26, INK, "none", sw=0, rx=13)
    dr.text(W / 2, 29.5, tag, 11.5, fill="#FFFFFF", weight=700, anchor="middle", spacing=0.06)
    dr.text(MARGIN, 30, "SPECIFICATION", 10.5, fill=MUTED, weight=700, spacing=0.08)
    dr.text(W - MARGIN, 30, "VERIFICATION", 10.5, fill=MUTED, weight=700, anchor="end", spacing=0.08)
    gw = (W - 2 * MARGIN - 8 * (len(d.gates) - 1)) / len(d.gates)
    for i, (gid, _) in enumerate(d.gates):
      st = gate_state(d, gid)
      fill, stroke, dash, _ = STATE[st]
      gx = MARGIN + i * (gw + 8)
      dr.rect(gx, lay.band_y, gw, 22, fill, stroke, sw=1.2, rx=11, dash=dash, key=f"gate-{gid}")
      dr.text(gx + gw / 2, lay.band_y + 15, f"{gid} · {d.gate_status[gid]}", 10.5, fill=MUTED if st == "none" else INK,
              weight=700, anchor="middle", within=f"gate-{gid}")
    used = sorted(set(dr.states.values()) | {gate_state(d, gid) for gid, _ in d.gates} |
                  {bridges[left].state for left, _, _ in tm.PAIRS}, key=list(STATE).index)
    x = MARGIN
    for st in used:
      fill, stroke, dash, label = STATE[st]
      dr.rect(x, lay.legend_y - 10, 16, 12, fill, stroke, sw=1.4, rx=3, dash="3 2" if dash else "")
      dr.text(x + 22, lay.legend_y, label, 11, fill=MUTED)
      x += 22 + text_w(label, 11) + 22
    if lens == "trace":
      note = "verification boxes: cases per specification, then items named / items · * only in work products, not in items/"
      dr.text(W - MARGIN, lay.legend_y, note, 11, fill=MUTED, anchor="end")
  if not loc:
    shown = [f"{lv(k).process} {STATE_WORD[dr.states[k]]}" + ("" if dr.states[k] == "dim" else f" ({boxes[k].words})")
             for k in [x.key for x in tm.LEFT + tm.RIGHT]]
    lit = f" Highlighted: {levels_named(highlight)}." if highlight else ""
    gates = " Gates: " + ", ".join(f"{gid} {d.gate_status[gid]}" for gid, _ in d.gates) + "." if size == "full" else ""
    dr.desc = (f"System V (ASPICE 4.0), {lens} lens{' for ' + goal if goal else ''}.{lit} " + "; ".join(shown) + "." + gates)
  return dr


def svg(dr: Drawing) -> str:
  head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt(dr.width)}" height="{fmt(dr.height)}" ' +
          f'viewBox="0 0 {fmt(dr.width)} {fmt(dr.height)}" font-family="{FONT}" role="img">')
  return "\n".join([head, el("title", dr.title), el("desc", dr.desc), marker_defs(dr.body), *dr.body, "</svg>"]) + "\n"


def render(lens: str, size: str, highlight=(), goal: str | None = None, model=None) -> str:
  """The system V as a standalone SVG string (role=img, <title>, <desc> naming what is lit and shown)."""
  return svg(draw(lens, size, highlight, goal, model))


def place(dr: Drawing, x: float, y: float, width: float) -> str:
  """dr scaled to `width` at (x, y), as a group for composing several Vs into one SVG (add marker_defs(body) once)."""
  return f'<g transform="translate({fmt(x)},{fmt(y)}) scale({width / dr.width:.5f})">' + "".join(dr.body) + "</g>"


# ---------------------------------------------------------------- small multiples: one V per safety goal

def goals(d: Data) -> list[str]:
  return sorted(d.m.ids["SG"])


def goal_grid(model=None, width: float = 1280, cols: int = 4, top: float = 0, stacked: bool = False) -> Drawing:
  """One goal-lens card per safety goal, `cols` per row, with a title per card and a legend under the grid (one entry
  per line with `stacked`, for narrow drawings)."""
  d = as_data(model)
  gs = goals(d)
  margin, gap, head = 40, 24, 24
  cw = (width - 2 * margin - gap * (cols - 1)) / cols
  cards = [draw("goal", "card", goal=g, model=d) for g in gs]
  ch = cards[0].height * cw / W
  rows = (len(gs) + cols - 1) // cols
  used = sorted({s for c in cards for s in c.states.values()}, key=list(STATE).index)
  height = round(top + rows * (head + ch + gap) + 40 + (18 * len(used) if stacked else 0))
  dr = Drawing(width, height, "System V per safety goal", "")
  dr.rect(0, 0, width, height, "#FFFFFF", "none", sw=0, rx=0)
  for i, (g, card) in enumerate(zip(gs, cards, strict=True)):
    x = margin + (i % cols) * (cw + gap)
    y = top + (i // cols) * (head + ch + gap)
    dr.text(x, y + 16, g, 13, weight=700)
    dr.text(x + text_w(g, 13, True) + 8, y + 16, f"ASIL {d.m.items[g].get('asil', '')}", 11, fill=MUTED)
    dr.body.append(place(card, x, y + head, cw))
    dr.rect(x, y + head, cw, ch, "none", "#E2E8F0", sw=1, rx=6)
  ly = height - 14 - (18 * len(used) if stacked else 0)
  x = margin
  for st in used:
    fill, stroke, dash, label = STATE[st]
    dr.rect(x, ly - 10, 16, 12, fill, stroke, sw=1.4, rx=3, dash="3 2" if dash else "")
    dr.text(x + 22, ly, label, 11, fill=MUTED)
    if stacked:
      ly += 18
    else:
      x += 22 + text_w(label, 11) + 22
  note = "left: items of the level under the goal · right: named by a case / items"
  if stacked:
    dr.text(margin, ly, note, 11, fill=MUTED)
  else:
    dr.text(width - margin, ly, note, 11, fill=MUTED, anchor="end")
  dr.desc = "One system V per safety goal. " + " ".join(
    f"{g}: " + "; ".join(f"{lv(k).process} {boxes.words}" for k, boxes in values(d, "goal", g)[0].items()) + "."
    for g in gs)
  dr.states = {s: s for s in used}
  return dr


# ---------------------------------------------------------------- geometry self-check

def check(dr: Drawing) -> list[str]:
  """Problems in a drawing: overlapping boxes, anything outside the viewBox, text wider than its box."""
  out = []
  eps = 0.5
  for i, (ka, xa, ya, wa, ha) in enumerate(dr.boxes):
    for kb, xb, yb, wb, hb in dr.boxes[i + 1:]:
      if xa < xb + wb - eps and xb < xa + wa - eps and ya < yb + hb - eps and yb < ya + ha - eps:
        out.append(f"boxes {ka} and {kb} overlap")
  for k, x, y, w, h in dr.boxes:
    if x < 0 or y < 0 or x + w > dr.width + eps or y + h > dr.height + eps:
      out.append(f"box {k} outside the viewBox")
  box = {k: (x, y, w, h) for k, x, y, w, h in dr.boxes}
  for s, x0, y0, x1, y1, within in dr.texts:
    if x0 < 0 or y0 < 0 or x1 > dr.width + eps or y1 > dr.height + eps:
      out.append(f"text {s!r} outside the viewBox")
    if within:
      bx, by, bw, bh = box[within]
      if x0 < bx + 2 or x1 > bx + bw - 2 or y0 < by or y1 > by + bh:
        out.append(f"text {s!r} does not fit in box {within}")
  free = [t for t in dr.texts if not t[5]]
  for i, a in enumerate(free):
    for b in free[i + 1:]:
      if a[1] < b[3] and b[1] < a[3] and a[2] < b[4] and b[2] < a[4]:
        out.append(f"texts {a[0]!r} and {b[0]!r} overlap")
    for k, x, y, w, h in dr.boxes:
      if a[1] < x + w and x < a[3] and a[2] < y + h and y < a[4]:
        out.append(f"text {a[0]!r} overlaps box {k}")
  for x1, y1, x2, y2 in dr.lines:
    if min(x1, x2) < 0 or min(y1, y2) < 0 or max(x1, x2) > dr.width or max(y1, y2) > dr.height:
      out.append(f"line {x1:.0f},{y1:.0f} -> {x2:.0f},{y2:.0f} outside the viewBox")
  return out


if __name__ == "__main__":
  data = load()
  for ln in (f"{lens} {size}: {len(svg(draw(lens, size, goal=goals(data)[0], model=data)))} bytes"
             for lens in LENSES for size in ("full", "card")):
    print(ln)
