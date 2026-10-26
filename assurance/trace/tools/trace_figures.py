#!/usr/bin/env python3
"""Generate the eight traceability figures of WP-T-01 (assurance/trace/figures/fig-*.svg).

  1  How the trace data works: who writes what, which tool turns it into checked data, who reads it
  2  Trace data model: the item kinds per standard, solid when in items/, dashed when only in a work product
  3  Derivation flow: hazard to software and hardware requirement, band width = number of parent links
  4  Trace depth per safety goal: derived, refined, allocated, named by a test case, tagged, passed
  5  TSR blocks x safety goals: how many TSRs of each block trace up to each goal
  6  Assumption exposure: what credits each assumption of use
  7  Consistency checks: implemented, partly, not yet (from the table in README §6)
  8  Allocation resolution: how many allocated_to values name an element of the SysML model
  9  The system V, status lens: register status per ASPICE level, cases specified and run, gate records (vmodel.py)
 10  The system V per safety goal: the goal's items per level and how many the paired cases name (vmodel.py)

Every number is computed. The sources are:
  - the trace data in assurance/trace/items/*.yaml (via trace_map.build(), which also counts the IDs of
    the kinds that exist only in work products, and the requirement IDs each test-specification case names);
  - the SysML v2 architecture model (assurance/models/sysml), for the allocation resolution of check M8;
  - the check table in README §6, for figure 7;
  - the section titles of WP-S-02, for the TSR block names of figure 5.
A case naming a requirement is a specified link, not a passed test; the figures never show it as verified.

Usage (from the repository root):
    python3 assurance/trace/tools/trace_figures.py           # write assurance/trace/figures/
    python3 assurance/trace/tools/trace_figures.py --check   # fail if a committed figure is stale

Standard library only.
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import trace_map as tm
import vmodel

TRACE_DIR = HERE.parent
ASSURANCE_DIR = TRACE_DIR.parent
REPO = ASSURANCE_DIR.parent
FIG_DIR = TRACE_DIR / "figures"
README = TRACE_DIR / "README.md"
WP_S_02 = ASSURANCE_DIR / "03-system" / "WP-S-02-technical-safety-requirements.md"
SYSML_TOOLS = ASSURANCE_DIR / "models" / "sysml" / "tools"
VERIFICATION_LINKS = TRACE_DIR / "links" / "verification.yaml"

REQ_KINDS = ("FSR", "TSR", "SWSR", "HWSR")
GOALS_ORDER = ("H", "HE", "SG", "AOU", "FSR", "TSR", "SWSR", "HWSR")

# ---------------------------------------------------------------- palette (assurance figure style)

FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SFMono-Regular', Menlo, Consolas, monospace"
INK, MUTED, FAINT, LINE, HAIR = "#0F172A", "#475569", "#94A3B8", "#CBD5E1", "#E2E8F0"
CHIP = "#F8FAFC"
SAFETY, SAFETY_BG = "#C2410C", "#FFF7ED"
SW, SW_BG = "#0F766E", "#F0FDFA"
HW, HW_BG = "#4F46E5", "#EEF2FF"
HAZ = "#475569"
AOU_C = "#D97706"
GREEN, GREEN_BG = "#2E9E6A", "#ECFDF5"
AMBER, AMBER_BG = "#D97706", "#FFFBEB"
RED, RED_BG = "#D2553F", "#FEF2F2"
GREY_BG = "#F1F5F9"


# ---------------------------------------------------------------- SVG helpers

def el(tag: str, text: str | None = None, **attrs) -> str:
  """One SVG element; attribute names use _ for - (stroke_width -> stroke-width), a trailing _ is dropped."""
  a = "".join(f' {k.rstrip("_").replace("_", "-")}="{v}"' for k, v in attrs.items() if v not in ("", None))
  return f"<{tag}{a}/>" if text is None else f"<{tag}{a}>{escape(text)}</{tag}>"


def fmt(v: float) -> str:
  return f"{v:.1f}".rstrip("0").rstrip(".")


def text(x, y, s, size=11, fill=INK, weight="", anchor="", family="", style="") -> str:
  return el("text", s, x=fmt(x), y=fmt(y), font_size=size, fill=fill, font_weight=weight, text_anchor=anchor,
            font_family=family, font_style=style)


def rect(x, y, w, h, fill="#FFFFFF", stroke=LINE, sw=1.2, rx=8, dash="", opacity="") -> str:
  return el("rect", None, x=fmt(x), y=fmt(y), width=fmt(w), height=fmt(h), rx=rx, fill=fill, stroke=stroke,
            stroke_width=sw, stroke_dasharray=dash, opacity=opacity)


def line(x1, y1, x2, y2, stroke=MUTED, sw=1.4, dash="", marker="") -> str:
  return el("line", None, x1=fmt(x1), y1=fmt(y1), x2=fmt(x2), y2=fmt(y2), stroke=stroke, stroke_width=sw,
            stroke_dasharray=dash, marker_end=f"url(#{marker})" if marker else "")


def path(d, stroke=MUTED, sw=1.4, fill="none", dash="", marker="", opacity="") -> str:
  return el("path", None, d=d, stroke=stroke, stroke_width=sw, fill=fill, stroke_dasharray=dash,
            marker_end=f"url(#{marker})" if marker else "", opacity=opacity, stroke_linejoin="round")


def box(x, y, w, h, title, detail="", fill="#FFFFFF", stroke=LINE, dash="", title_fill=INK, detail_fill=MUTED,
        mono=False, size=12, rx=8) -> list[str]:
  """A box with a bold title and up to two detail lines, centred."""
  details = detail.split("\n") if detail else []
  n = 1 + len(details)
  y0 = y + h / 2 - (n - 1) * 7 + 4
  out = [rect(x, y, w, h, fill=fill, stroke=stroke, dash=dash, rx=rx, sw=1.4)]
  out.append(text(x + w / 2, y0, title, size=size, weight=700, anchor="middle", fill=title_fill,
                  family=MONO if mono else ""))
  for i, d in enumerate(details):
    out.append(text(x + w / 2, y0 + 15 * (i + 1), d, size=10.5, anchor="middle", fill=detail_fill))
  return out


MARKERS = {"ink": INK, "muted": MUTED, "faint": FAINT, "safety": SAFETY, "sw": SW, "hw": HW, "aou": AOU_C,
           "red": RED}


def svg(width: int, height: int, title: str, desc: str, body: list[str]) -> str:
  defs = "".join(
    f'<marker id="{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" ' +
    f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for k, c in MARKERS.items())
  head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" ' +
          f'font-family="{FONT}" role="img">')
  return "\n".join([head, el("title", title), el("desc", desc), f"<defs>{defs}</defs>",
                    rect(0, 0, width, height, fill="#FFFFFF", stroke="none", rx=0, sw=0), *body, "</svg>"]) + "\n"


def header(width: int, number: int, title: str, subtitle: str, ref: str) -> list[str]:
  return [text(40, 44, f"Figure {number} · {title}", size=20, weight=700),
          text(40, 66, subtitle, size=12.5, fill=MUTED),
          text(width - 40, 44, ref, size=11, fill=MUTED, anchor="end"),
          line(40, 82, width - 40, 82, stroke=HAIR, sw=1)]


def legend(x: float, y: float, entries: list[tuple[str, str, str]]) -> list[str]:
  """entries: (fill, stroke, label); dashed stroke when the label ends with ' ⁽ᵈ⁾' is not used, pass dash in fill."""
  out = []
  for fill, stroke, label in entries:
    dash = ""
    if stroke.endswith(" dashed"):
      stroke, dash = stroke[:-7], "4 3"
    out.append(rect(x, y - 10, 14, 12, fill=fill, stroke=stroke, rx=3, dash=dash))
    out.append(text(x + 20, y, label, size=11, fill=MUTED))
    x += 34 + 6.2 * len(label)
  return out


def pct(n: int, d: int) -> int:
  return round(100 * n / d) if d else 0


# ---------------------------------------------------------------- data

@dataclass
class Data:
  m: tm.Model
  kind: dict[str, str]                  # item ID -> kind prefix (H, HE, ...)
  children: dict[str, list[str]]        # item ID -> items that list it in `parents`
  links: Counter                        # (parent kind, child kind) -> number of parent links
  named: set[str]                       # item IDs named by at least one test-specification case
  linked: dict[str, int]                # requirement ID -> number of tests links/verification.yaml links to it
  n_links: int                          # entries of links/verification.yaml
  alloc: dict[str, str]                 # requirement ID -> resolved / partly resolved / not resolved
  alloc_values: dict[str, list[str]]    # unresolved allocated_to text -> requirement IDs
  checks: list[tuple[str, str, str]]    # (check ID, description, implemented: yes / partly / no)
  blocks: dict[str, str]                # "1" -> WP-S-02 section title of TSR-1xx
  cases: int                            # test-specification cases
  test_prefixes: int


def allocation(items: dict[str, dict]) -> tuple[dict[str, str], dict[str, list[str]]]:
  """Resolution of every allocated_to value against the SysML model, as check_model.py M8 computes it."""
  sys.path.insert(0, str(SYSML_TOOLS))
  import check_model as cm
  import sysml_lite
  model = sysml_lite.load()
  units: dict[str, list[str]] = defaultdict(list)
  for e in model.elements.values():
    u = e.meta.get("Unit")
    if u:
      units[u["id"]].append(e.short)
  status: dict[str, str] = {}
  values: dict[str, list[str]] = defaultdict(list)
  for iid, it in items.items():
    a = it.get("allocated_to")
    if not a:
      continue
    _, res, unres = cm.resolve_allocation(model, str(a), units)
    status[iid] = "resolved" if res and not unres else ("partly resolved" if res else "not resolved")
    if status[iid] == "not resolved":
      values[str(a)].append(iid)
  return status, dict(values)


CHECK_ROW = re.compile(r"^\|\s*([KRXPSACQI]\d+)(?:\s+\*\*\[ext\]\*\*|\s+\(planned\))?\s*\|")


def readme_checks() -> list[tuple[str, str, str]]:
  """The check table of README §6: ID, description, and the first word of the Implemented column."""
  body = README.read_text(encoding="utf-8").split("## 6. Consistency checks", 1)[1].split("\n## ", 1)[0]
  out = []
  for row in body.splitlines():
    m = CHECK_ROW.match(row)
    if not m:
      continue
    cells = tm.split_row(row)
    word = cells[3].split()[0].rstrip(":,").lower()
    if word not in ("yes", "partly", "no"):
      raise SystemExit(f"README §6 {m.group(1)}: Implemented must start with Yes, Partly or No, found {cells[3]!r}")
    out.append((m.group(1), cells[1], word))
  return out


BLOCK_HEAD = re.compile(r"^## \d+\. TSR-(\d)xx (.+?)\s*$", re.M)


def block_titles() -> dict[str, str]:
  out = {}
  for n, title in BLOCK_HEAD.findall(WP_S_02.read_text(encoding="utf-8")):
    out[n] = re.sub(r"\s*\([^)]*\)$", "", title)
  return out


def load() -> Data:
  m = tm.build()
  kind = {i: tm.YAML_KIND[it["kind"]] for i, it in m.items.items()}
  children: dict[str, list[str]] = defaultdict(list)
  links: Counter = Counter()
  for i, it in m.items.items():
    for p in it.get("parents") or []:
      if p in m.items:
        children[p].append(i)
        links[(kind[p], kind[i])] += 1
  named = {r for cases in m.specs.values() for refs in cases.values() for r in refs} & set(m.items)
  alloc, values = allocation(m.items)
  ver = tm.ct.load_yaml(VERIFICATION_LINKS) if VERIFICATION_LINKS.exists() else []
  linked = Counter(r for ln in ver for r in ln.get("reqs") or [])
  if any("result" in ln for ln in ver):
    raise SystemExit(f"{VERIFICATION_LINKS.relative_to(REPO)} now records results: teach trace_figures.py (figures 1, 2, 4) " +
                     "to count its test results")
  return Data(m, kind, dict(children), links, named, dict(linked), len(ver), alloc, values, readme_checks(), block_titles(),
              sum(len(c) for c in m.specs.values()), len(m.specs))


def count(d: Data, k: str) -> int:
  return len(d.m.ids.get(k, ()))


def descendants(d: Data, root: str) -> set[str]:
  seen: set[str] = set()
  todo = [root]
  while todo:
    for c in d.children.get(todo.pop(), []):
      if c not in seen:
        seen.add(c)
        todo.append(c)
  return seen


def goals(d: Data) -> list[str]:
  return sorted(d.m.ids["SG"])


def aou_credits(d: Data) -> dict[str, Counter]:
  """AOU ID -> kind -> number of items that credit it (aou_dependency on HE/SG, parents on TSR/HWSR)."""
  out: dict[str, Counter] = {a: Counter() for a in sorted(d.m.ids["AOU"])}
  for i, it in d.m.items.items():
    refs = set(it.get("aou_dependency") or []) | {p for p in it.get("parents") or [] if p.startswith("AOU-")}
    for a in refs:
      if a in out:
        out[a][d.kind[i]] += 1
  return out


def leftovers(d: Data) -> dict[str, list[str]]:
  """Items whose chain stops, with the reason the trace data records."""
  he_no_sg = [h for h in sorted(d.m.ids["HE"]) if not any(d.kind[c] == "SG" for c in d.children.get(h, []))]
  fsr_no_tsr = [f for f in sorted(d.m.ids["FSR"]) if not any(d.kind[c] == "TSR" for c in d.children.get(f, []))]
  tsr_leaf = [t for t in sorted(d.m.ids["TSR"]) if not any(d.kind[c] in ("SWSR", "HWSR") for c in d.children.get(t, []))]
  return {"HE": he_no_sg, "FSR": fsr_no_tsr, "TSR": tsr_leaf}


# ---------------------------------------------------------------- Figure 1: how the trace data works

def fig1(d: Data) -> str:
  W, H = 1280, 690
  out = header(W, 1, "How the trace data works",
               "Who writes what, which tool turns it into checked data, and who reads it. The Markdown work product " +
               "is the source of truth; the YAML is a checked copy.", "WP-T-01 §1–§2")
  lanes = [("AUTHORS", 100), ("WORK PRODUCTS", 186), ("GENERATORS", 286), ("TRACE DATA", 376),
           ("CHECKS · CI", 466), ("CONSUMERS", 556)]
  lane_h = [86, 100, 90, 90, 90, 90]
  for i, ((name, y), h) in enumerate(zip(lanes, lane_h, strict=True)):
    out.append(rect(40, y, W - 80, h, fill=CHIP if i % 2 == 0 else "#FFFFFF", stroke="none", rx=0, sw=0))
    out.append(text(56, y + h / 2 + 4, name, size=10.5, weight=700, fill=MUTED))
  out.append(line(180, 100, 180, 646, stroke=HAIR, sw=1))
  impl = [c for c, _, w in d.checks if w == "yes" and not c.startswith("P")]
  total = len(d.m.items)
  counts = " · ".join(f"{k} {count(d, k)}" for k in GOALS_ORDER)
  res = sum(1 for s in d.alloc.values() if s == "resolved")
  # authors
  out += box(200, 116, 250, 52, "Maintainer", "writes and approves the work products")
  out += box(500, 116, 250, 52, "AI assistant", "drafts; never a reviewer", fill=HW_BG, stroke="#A5B4FC")
  out += box(800, 116, 280, 52, "Verification reviewer (I1)", "TBD · no review recorded yet", dash="5 4",
             stroke=FAINT, detail_fill=RED)
  # work products
  wps = [("WP-C-01 · WP-C-03", "AoU · HARA\nH · HE · SG"), ("WP-C-04", "FSC\nFSR tables"),
         ("WP-S-02 · WP-S-06", "TSC\nTSR tables"), ("WP-W-02 · WP-H-01", "SW · HW safety req.\nSWSR · HWSR tables"),
         ("Test specifications", f"{d.test_prefixes} VS- prefixes\n{d.cases} cases")]
  xs = [200, 410, 620, 830, 1040]
  for x, (t, s) in zip(xs, wps, strict=True):
    out += box(x, 200, 196, 72, t, s, size=11.5)
  out.append(line(200 + 98, 184, 1040 + 98, 184, stroke=MUTED, sw=1.4))  # one bus: every author touches every WP
  for x in (325, 625):
    out.append(line(x, 168, x, 184, stroke=MUTED, sw=1.4))
  out.append(line(940, 168, 940, 184, stroke=FAINT, sw=1.2, dash="5 4"))
  for x in xs:
    out.append(line(x + 98, 184, x + 98, 198, marker="muted"))
  # generators
  out += box(200, 300, 196, 62, "hazards · goals · aou.yaml", "kept by hand, compared\nwith the WPs (X1, X2)",
             fill=GREY_BG, size=11.5)
  out += box(430, 300, 576, 62, "sync_requirements.py", "regenerates fsr · tsr · swsr · hwsr.yaml from the tables " +
             "(X3, --check)", fill=SAFETY_BG, stroke=SAFETY, mono=True)
  out += box(1040, 300, 196, 62, "trace_map.py", "reads the case tables\nand the items", fill=SAFETY_BG,
             stroke=SAFETY, mono=True)
  out.append(line(298, 272, 298, 298, marker="muted"))
  for x in (508, 718, 928):
    out.append(line(x, 272, x if x != 718 else 718, 298, marker="muted"))
  out.append(line(1138, 272, 1138, 298, marker="muted"))
  # trace data
  out += box(200, 390, 806, 62, f"items/*.yaml · {total} items", counts, fill=SW_BG, stroke=SW, title_fill=SW)
  out += box(1040, 390, 196, 62, "links/verification.yaml",
             f"{d.n_links} test links · no results\n0 @req tags" if d.n_links else "not yet · 0 @req tags",
             dash="" if d.n_links else "5 4", stroke=AMBER if d.n_links else RED, detail_fill=INK if d.n_links else RED,
             mono=True, size=11)
  out.append(line(298, 362, 298, 388, marker="muted"))
  out.append(line(718, 362, 718, 388, marker="muted"))
  out.append(path("M1006,404 L1022,404 L1022,331 L1038,331", stroke=MUTED, sw=1.4, marker="muted"))
  # checks
  out += box(200, 480, 300, 62, "check_trace.py", f"{len(impl)} checks run in full ({impl[0]} … {impl[-1]});\n" +
             "see Figure 7", fill=GREEN_BG, stroke=GREEN, mono=True)
  out += box(530, 480, 340, 62, "--check modes", "sync, trace map, these figures, links,\ntables, state machines",
             fill=GREEN_BG, stroke=GREEN, mono=True)
  out += box(900, 480, 336, 62, "CI gate", "assurance.yaml fails the pull request", fill=INK, stroke=INK,
             title_fill="#FFFFFF", detail_fill="#CBD5E1")
  out.append(line(350, 452, 350, 478, marker="muted"))
  out.append(line(700, 452, 700, 478, marker="muted"))
  out.append(line(500, 511, 528, 511, marker="muted"))
  out.append(line(870, 511, 898, 511, marker="muted"))
  # consumers
  cons = [("ASPICE trace map", "V-model and coverage"), ("Living safety case", "claims cite SG / FSR IDs"),
          ("SysML allocation report", f"{res} of {len(d.alloc)} allocations resolved"),
          ("Safety case snapshot", "downloadable PDF")]
  for i, (t, s) in enumerate(cons):
    x = 200 + i * 262
    out += box(x, 570, 246, 56, t, s)
    out.append(line(x + 123, 556, x + 123, 568, stroke=SAFETY, sw=1.3, marker="safety"))
  out.append(line(1068, 542, 1068, 556, stroke=SAFETY, sw=1.3))
  out.append(line(323, 556, 200 + 3 * 262 + 123, 556, stroke=SAFETY, sw=1.3))
  out.append(text(40, 672, "Arrows: solid = in place and checked; dashed = planned. Every count above is computed " +
                  "from the repository when the figure is generated.", size=11, fill=MUTED))
  return svg(W, H, "Figure 1 · How the trace data works",
             "Swimlane from authors through work products, generators, the trace data and its checks to the " +
             f"consumers. The trace data holds {total} items ({counts}); requirement YAML is regenerated from the work " +
             (f"product tables; {d.n_links} test links come from WP-W-06, no results and no @req tags exist yet." if d.n_links
              else "product tables; no verification links or @req tags exist yet."), out)


# ---------------------------------------------------------------- Figure 2: trace data model

NODE_W, NODE_H = 104, 34
F2_POS = {  # kind -> centre; layout only, every count is computed
  "H": (210, 140), "HE": (210, 210), "SG": (210, 280), "FSR": (210, 350), "TSR": (210, 420),
  "SWSR": (140, 500), "HWSR": (290, 500), "AOU": (80, 210),
  "SH": (660, 210), "TC": (600, 330), "FI": (720, 330), "FM": (660, 430),
  "AIR": (885, 330), "DSR": (885, 430), "TS": (1060, 210), "CSG": (1060, 330), "CSR": (1060, 430),
  "SYS": (1190, 330),
}
F2_COLUMNS = [("ISO 26262", 40, 520), ("ISO 21448", 520, 800), ("ISO/PAS 8800", 800, 970),
              ("ISO/SAE 21434", 970, 1140), ("ASPICE", 1140, 1240)]


def fig2(d: Data) -> str:
  W, H = 1280, 690
  out = header(W, 2, "Trace data model: what is in, what is missing",
               "One column per standard. Solid kinds are in items/ and checked; dashed kinds exist only in their work " +
               "products. Edge labels are links counted in items/.", "WP-T-01 §3")
  for name, x0, x1 in F2_COLUMNS:
    out.append(text((x0 + x1) / 2, 108, name, size=11, weight=700, fill=MUTED, anchor="middle"))
    if x0 > 40:
      out.append(line(x0, 96, x0, 530, stroke=HAIR, sw=1, dash="3 4"))

  def node_box(k: str) -> list[str]:
    cx, cy = F2_POS[k]
    solid = k in d.m.in_trace
    return box(cx - NODE_W / 2, cy - NODE_H / 2, NODE_W, NODE_H, f"{k}  {count(d, k)}", "",
               fill=SW_BG if solid else "#FFFFFF", stroke=SW if solid else FAINT, dash="" if solid else "5 4",
               title_fill=SW if solid else MUTED, rx=7)

  def down(a: str, b: str, label: str | None, solid: bool, dx_label: float = 8) -> list[str]:
    (ax, ay), (bx, by) = F2_POS[a], F2_POS[b]
    x1, y1, x2, y2 = ax, ay + NODE_H / 2, bx, by - NODE_H / 2 - 1
    if ax != bx:  # leave from the bottom edge towards the target
      x1 = ax + (bx - ax) * 0.35
    res = [line(x1, y1, x2, y2, stroke=SW if solid else FAINT, sw=1.6 if solid else 1.2, dash="" if solid else "5 4",
                marker="sw" if solid else "faint")]
    if label:
      mx, my = (x1 + x2) / 2, (y1 + y2) / 2
      res.append(text(mx + (dx_label if x2 >= x1 else -dx_label), my + 4, label, size=11, weight=700, fill=SW,
                      anchor="start" if x2 >= x1 else "end"))
    return res

  for a, b in (("H", "HE"), ("HE", "SG"), ("SG", "FSR"), ("FSR", "TSR"), ("TSR", "SWSR"), ("TSR", "HWSR")):
    out += down(a, b, str(d.links[(a, b)]), True)
  # skip links and the assumption links, as notes beside the chain
  out.append(text(268, 384, f"+ {d.links[('SG', 'TSR')]} SG → TSR", size=10.5, fill=MUTED))
  out.append(text(268, 430, f"+ {d.links[('TSR', 'TSR')]} TSR → TSR", size=10.5, fill=MUTED))
  out.append(text(348, 504, f"+ {d.links[('FSR', 'HWSR')]} FSR → HWSR", size=10.5, fill=MUTED))
  ax, ay = F2_POS["AOU"]
  tx, ty = F2_POS["TSR"]
  out.append(path(f"M{ax + 38},{ay + NODE_H / 2} L{ax + 38},{ty} L{tx - NODE_W / 2 - 1},{ty}", stroke=AOU_C, sw=1.6,
                  marker="aou"))
  out.append(text(ax + 44, ty - 6, str(d.links[("AOU", "TSR")]), size=11, weight=700, fill=AOU_C))
  credit = aou_credits(d)
  he_c = sum(c["HE"] for c in credit.values())
  sg_c = sum(c["SG"] for c in credit.values())
  out.append(line(F2_POS["HE"][0] - NODE_W / 2, ay, ax + NODE_W / 2 + 1, ay, stroke=AOU_C, sw=1.2, dash="2 3",
                  marker="aou"))
  out.append(text(ax - NODE_W / 2, ay + 34, "credited by", size=10, fill=AOU_C))
  out.append(text(ax - NODE_W / 2, ay + 47, f"{he_c} HE · {sg_c} SG", size=10, fill=AOU_C))
  # other standards: solid with the link count once both kinds are in items/, dashed while either is in documents only
  def traced(a: str, b: str) -> bool:
    return a in d.m.in_trace and b in d.m.in_trace

  for a, b in (("SH", "TC"), ("SH", "FI"), ("TC", "FM"), ("FI", "FM"), ("AIR", "DSR"), ("TS", "CSG"), ("CSG", "CSR")):
    (ax2, ay2), (bx2, by2) = F2_POS[a], F2_POS[b]
    x1, y1, x2, y2 = ax2 + (bx2 - ax2) * 0.3, ay2 + NODE_H / 2, bx2 - (bx2 - ax2) * 0.1, by2 - NODE_H / 2 - 1
    on = traced(a, b)
    out.append(line(x1, y1, x2, y2, stroke=SW if on else FAINT, sw=1.6 if on else 1.2, dash="" if on else "5 4",
                    marker="sw" if on else "faint"))
    if on:
      right = x2 >= x1
      out.append(text((x1 + x2) / 2 + (8 if right else -8), (y1 + y2) / 2 + 4, str(d.links[(a, b)]), size=11,
                      weight=700, fill=SW, anchor="start" if right else "end"))
  fx, fy = F2_POS["FI"]
  on = traced("FI", "AIR")
  out.append(line(fx + NODE_W / 2, fy, F2_POS["AIR"][0] - NODE_W / 2 - 1, fy, stroke=SW if on else FAINT,
                  sw=1.6 if on else 1.2, dash="" if on else "5 4", marker="sw" if on else "faint"))
  if on:
    out.append(text((fx + F2_POS["AIR"][0]) / 2, fy - 8, str(d.links[("FI", "AIR")]), size=11, weight=700, fill=SW,
                    anchor="middle"))
  # cross-standard links
  sx, sy = F2_POS["SH"]
  hx, hy = F2_POS["H"]
  shared = sum(len(it.get("shares_event") or []) for it in d.m.items.values())
  on = traced("SH", "H") and shared > 0
  out.append(line(sx - NODE_W / 2, sy, hx + NODE_W / 2 + 1, hy, stroke=SW if on else FAINT, sw=1.6 if on else 1.2,
                  dash="" if on else "5 4", marker="sw" if on else "faint"))
  out.append(text(400, 150, "shares hazard (SH → H)" + (f" · {shared}" if on else ""), size=10.5,
                  fill=SW if on else MUTED, weight=700 if on else "", anchor="middle"))
  cx, cy = F2_POS["CSG"]
  gx, gy = F2_POS["SG"]
  protects = sum(len(it.get("protects") or []) for it in d.m.items.values())
  on = traced("CSG", "SG") and protects > 0
  out.append(path(f"M{cx - NODE_W / 2},{cy - 8} L{cx - NODE_W / 2 - 22},{cy - 8} L{cx - NODE_W / 2 - 22},{gy} " +
                  f"L{gx + NODE_W / 2 + 1},{gy}", stroke=SW if on else FAINT, sw=1.6 if on else 1.2,
                  dash="" if on else "5 4", marker="sw" if on else "faint"))
  out.append(text(430, gy - 8, "protects (CSG → SG)" + (f" · {protects}" if on else ""), size=10.5,
                  fill=SW if on else MUTED, weight=700 if on else "", anchor="middle"))
  sx2, sy2 = F2_POS["SYS"]
  related = sum(len(it.get("related_tsr") or []) for it in d.m.items.values() if d.kind.get(it["id"]) == "SYS")
  out.append(text(sx2, sy2 + 34, f"related to TSRs: {related}" if traced("SYS", "TSR") else "not linked yet", size=10,
                  fill=SW if traced("SYS", "TSR") else MUTED, anchor="middle"))
  for k in F2_POS:
    out += node_box(k)
  # footer: the two halves that are not item kinds
  res = Counter(d.alloc.values())
  per = {k: (sum(1 for i, s in d.alloc.items() if d.kind[i] == k and s == "resolved"),
             sum(1 for i in d.alloc if d.kind[i] == k)) for k in REQ_KINDS + ("CSR", "SYS")}
  out.append(rect(40, 552, 590, 74, fill="#EFF6FF", stroke="#93C5FD", rx=10))
  out.append(text(58, 576, "Elements · SysML v2 model", size=12, weight=700))
  out.append(text(58, 596, f"allocated_to resolved: {res['resolved']} of {len(d.alloc)} · "
                  + " · ".join(f"{k} {a}/{b}" for k, (a, b) in per.items()), size=11, fill=MUTED))
  out.append(text(58, 614, "See Figure 8 and the allocation resolution report.", size=11, fill=MUTED))
  named = len(d.named)
  out.append(rect(650, 552, 590, 74, fill=RED_BG, stroke=RED, rx=10, dash="5 4"))
  out.append(text(668, 576, "Code and tests · @req tags, links/verification.yaml", size=12, weight=700, fill=RED))
  out.append(text(668, 596, f"{d.n_links} test links to {len(d.linked)} requirements (from WP-W-06), 0 @req tags, " +
                  "no results.", size=11, fill=MUTED))
  out.append(text(668, 614, f"{named} of {len(d.m.items)} items are named by a test-specification case: specified, " +
                  "not passed.", size=11, fill=MUTED))
  out += legend(40, 660, [(SW_BG, SW, "in items/, checked"), ("#FFFFFF", FAINT + " dashed", "only in its work product"),
                          ("#FFFFFF", AOU_C, "assumption link")])
  return svg(W, H, "Figure 2 · Trace data model",
             "The item kinds of each standard with their counts and the parent links between them. ISO 26262 kinds " +
             f"are in the trace data ({', '.join(f'{k} {count(d, k)}' for k in GOALS_ORDER)}); SOTIF, AI, " +
             "cybersecurity and system requirement kinds exist only in their work products.", out)


# ---------------------------------------------------------------- Figure 3: derivation flow (Sankey)

SANKEY_X = {"H": 90, "HE": 270, "SG": 450, "FSR": 640, "AOU": 640, "TSR": 840, "SWSR": 1070, "HWSR": 1070}
SANKEY_TOP = {"H": None, "HE": None, "SG": None, "FSR": 140, "AOU": 452, "TSR": 150, "SWSR": 120, "HWSR": 352}
BAND = {"H": HAZ, "HE": HAZ, "SG": SAFETY, "FSR": SAFETY, "TSR": SAFETY, "SWSR": SW, "HWSR": HW, "AOU": AOU_C}
SANKEY_LINKS = [("H", "HE"), ("HE", "SG"), ("SG", "FSR"), ("SG", "TSR"), ("FSR", "TSR"), ("AOU", "TSR"),
                ("TSR", "SWSR"), ("TSR", "HWSR"), ("FSR", "HWSR"), ("AOU", "HWSR")]
NODE_COL = {"H": HAZ, "HE": HAZ, "SG": SAFETY, "FSR": SAFETY, "TSR": SAFETY, "SWSR": SW, "HWSR": HW, "AOU": AOU_C}


def fig3(d: Data) -> str:
  W, H, S, NW = 1280, 640, 1.35, 18
  out = header(W, 3, "Derivation flow: hazard to software and hardware requirement",
               "Band width is the number of parent links in items/. Every safety goal is derived; the items where a " +
               "chain stops each carry their reason.", "WP-T-01 §3.2")
  links = [(a, b, d.links[(a, b)]) for a, b in SANKEY_LINKS if d.links[(a, b)]]
  inflow, outflow = Counter(), Counter()
  for a, b, n in links:
    outflow[a] += n
    inflow[b] += n
  size = {k: max(inflow[k], outflow[k]) * S for k in SANKEY_X}
  top = {}
  for k, t in SANKEY_TOP.items():
    top[k] = t if t is not None else 275 - size[k] / 2 + (40 if k == "SG" else 0)
  centre = {k: top[k] + size[k] / 2 for k in SANKEY_X}
  # port offsets: outgoing sorted by target centre, incoming by source centre
  out_off, in_off = {}, {}
  for k in SANKEY_X:
    y = top[k]
    for a, b, n in sorted((x for x in links if x[0] == k), key=lambda x: centre[x[1]]):
      out_off[(a, b)] = y
      y += n * S
    y = top[k]
    for a, b, n in sorted((x for x in links if x[1] == k), key=lambda x: centre[x[0]] if x[0] != "AOU" else 9e9):
      in_off[(a, b)] = y
      y += n * S
  bands = []
  skip_under = {"TSR": [], "FSR": []}  # waypoints below an intermediate column
  for a, b, n in links:
    w = n * S
    x0, x1 = SANKEY_X[a] + NW, SANKEY_X[b]
    y0, y1 = out_off[(a, b)], in_off[(a, b)]
    mid = [k for k in ("FSR", "TSR") if SANKEY_X[a] < SANKEY_X[k] < SANKEY_X[b] and k != a]
    if mid:  # route below the column it skips
      k = mid[0]
      ym = top[k] + size[k] + 14 + sum(skip_under[k])
      skip_under[k].append(w + 22)
      xm = SANKEY_X[k] + NW / 2
      c0, c1 = (x0 + xm) / 2, (xm + x1) / 2
      d_ = (f"M{fmt(x0)},{fmt(y0)} C{fmt(c0)},{fmt(y0)} {fmt(c0)},{fmt(ym)} {fmt(xm)},{fmt(ym)} " +
            f"C{fmt(c1)},{fmt(ym)} {fmt(c1)},{fmt(y1)} {fmt(x1)},{fmt(y1)} L{fmt(x1)},{fmt(y1 + w)} " +
            f"C{fmt(c1)},{fmt(y1 + w)} {fmt(c1)},{fmt(ym + w)} {fmt(xm)},{fmt(ym + w)} " +
            f"C{fmt(c0)},{fmt(ym + w)} {fmt(c0)},{fmt(y0 + w)} {fmt(x0)},{fmt(y0 + w)} Z")
      lx, ly = xm, ym + w + 13
      if a == "AOU":
        lx, ly = x1 - 120, (y1 + w) - 6
    else:
      c = (x0 + x1) / 2
      d_ = (f"M{fmt(x0)},{fmt(y0)} C{fmt(c)},{fmt(y0)} {fmt(c)},{fmt(y1)} {fmt(x1)},{fmt(y1)} " +
            f"L{fmt(x1)},{fmt(y1 + w)} C{fmt(c)},{fmt(y1 + w)} {fmt(c)},{fmt(y0 + w)} {fmt(x0)},{fmt(y0 + w)} Z")
      lx, ly = c, (y0 + y1) / 2 - 6
      if a == "AOU":
        lx, ly = x0 + 62, y0 + w + 14
    colour = BAND[b] if b in ("SWSR", "HWSR") and a != "AOU" else BAND[a]
    bands.append(el("path", None, d=d_, fill=colour, opacity=0.28 if a not in ("H", "HE") else 0.22))
    label = f"{a} → {b}  {n}" if mid or a == "AOU" or (a, b) == ("SG", "TSR") else str(n)
    bands.append(text(lx, ly, label, size=10.5, weight=700, fill=colour, anchor="middle"))
  out += bands
  for k in SANKEY_X:
    if not size[k]:
      continue
    out.append(rect(SANKEY_X[k], top[k], NW, size[k], fill=NODE_COL[k], stroke="none", rx=3, sw=0))
    label = f"{k} {count(d, k)}"
    if k in ("SWSR", "HWSR"):
      out.append(text(SANKEY_X[k] + NW + 10, centre[k] + 4, label, size=12.5, weight=700))
    elif k == "AOU":
      out.append(text(SANKEY_X[k] - 8, centre[k] + 4, label, size=12.5, weight=700, anchor="end"))
    else:
      out.append(text(SANKEY_X[k] + NW / 2, top[k] - 8, label, size=12.5, weight=700, anchor="middle"))
  # where chains stop
  lo = leftovers(d)
  ops = [t for t in lo["TSR"] if d.m.items[t].get("allocated_to") == "OPS"]
  notes = [
    (130, 452, f"{len(lo['HE'])} HE without a goal", ", ".join(lo["HE"]) + " · " +
     ("QM, exempt with a reason" if all(d.m.items[h].get("sg_exempt_reason") for h in lo["HE"]) else "no reason")),
    (130, 512, f"{len(lo['FSR'])} FSR without its own TSR", ", ".join(lo["FSR"]) + " · applies other FSRs"),
    (870, 520, f"{len(lo['TSR'])} TSRs with no SWSR or HWSR",
     f"{len(ops)} allocated to operation (OPS); {len(lo['TSR']) - len(ops)} listed as not refined\n" +
     "(WP-W-02 §10, WP-H-01) or not allocated to SW or HW (K4)"),
  ]
  for x, y, t, s in notes:
    lines_ = s.split("\n")
    w = 360 if x > 500 else 330
    out.append(rect(x, y, w, 24 + 15 * len(lines_), fill=CHIP, stroke=LINE, rx=8))
    out.append(text(x + 12, y + 18, t, size=11.5, weight=700))
    for i, s2 in enumerate(lines_):
      out.append(text(x + 12, y + 34 + 15 * i, s2, size=10.5, fill=MUTED))
  out += legend(40, 620, [(HAZ, HAZ, "hazard analysis"), (SAFETY, SAFETY, "safety requirements"),
                          (SW, SW, "software"), (HW, HW, "hardware"), (AOU_C, AOU_C, "assumption credited")])
  out.append(text(W - 40, 620, f"{d.links[('TSR', 'TSR')]} TSR → TSR links not drawn", size=10.5, fill=MUTED,
                  anchor="end"))
  return svg(W, H, "Figure 3 · Derivation flow",
             "Sankey diagram of parent links: " + ", ".join(f"{a} to {b} {n}" for a, b, n in links) +
             f". {len(lo['HE'])} hazardous event has no goal, {len(lo['FSR'])} FSR has no TSR of its own, " +
             f"{len(lo['TSR'])} TSRs have no SW or HW requirement.", out)


# ---------------------------------------------------------------- Figure 4: trace depth per goal

def goal_row(d: Data, ids: set[str]) -> dict:
  by = Counter(d.kind[i] for i in ids)
  reqs = [i for i in ids if d.kind[i] in REQ_KINDS]
  alloc = [i for i in reqs if d.alloc.get(i) == "resolved"]
  named = [i for i in reqs if i in d.named]
  linked = [i for i in reqs if i in d.linked]
  return {"by": by, "n": len(reqs), "alloc": len(alloc), "named": len(named), "linked": len(linked)}


def fig4(d: Data) -> str:
  W = 1280
  gs = goals(d)
  out = header(W, 4, "Trace depth per safety goal",
               "How far each goal's chain reaches today, over the requirements it derives (FSR, TSR, SWSR, HWSR). " +
               "No chain reaches a recorded result.", "WP-T-01 §6")
  cols = [("DERIVED", "FSR · TSR", 210), ("REFINED", "SWSR · HWSR", 380), ("ALLOCATED", "to a model element", 550),
          ("NAMED BY A", "test-spec case", 740), ("LINKED", "to a test (K6)", 930), ("TEST", "passed", 1090)]
  cw = [150, 150, 170, 170, 140, 150]
  for (a, b, x), w in zip(cols, cw, strict=True):
    out.append(text(x + w / 2, 112, a, size=10.5, weight=700, fill=MUTED, anchor="middle"))
    out.append(text(x + w / 2, 126, b, size=10.5, fill=MUTED, anchor="middle"))
  out.append(text(48, 126, "GOAL", size=10.5, weight=700, fill=MUTED))
  rows = [(g, d.m.items[g].get("asil", ""), descendants(d, g)) for g in gs]
  rows.append(("All goals", "", set().union(*(r[2] for r in rows))))
  y = 140
  for name, asil, ids in rows:
    r = goal_row(d, ids)
    last = name == "All goals"
    if last:
      out.append(line(40, y - 4, W - 40, y - 4, stroke=LINE, sw=1))
      y += 6
    out.append(text(48, y + 24, name, size=12.5, weight=700))
    if asil:
      out.append(text(48 + 50, y + 24, f"ASIL {asil}", size=10.5, fill=MUTED))
    vals = [f"{r['by']['FSR']} · {r['by']['TSR']}", f"{r['by']['SWSR']} · {r['by']['HWSR']}"]
    for (_, _, x), w, v in zip(cols[:2], cw[:2], vals, strict=True):
      out.append(rect(x, y + 4, w - 12, 32, fill="#EFF6FF", stroke="#93C5FD", rx=6))
      out.append(text(x + (w - 12) / 2, y + 25, v, size=12.5, weight=700, fill="#1D4ED8", anchor="middle"))
    for (_, _, x), w, num in ((cols[2], cw[2], r["alloc"]), (cols[3], cw[3], r["named"]), (cols[4], cw[4], r["linked"])):
      p = pct(num, r["n"])
      full = num == r["n"]
      fill, stroke = ((GREEN_BG, GREEN) if full and x == cols[2][2] else (RED_BG, RED) if num == 0 else
                      (AMBER_BG, AMBER))
      out.append(rect(x, y + 4, w - 12, 32, fill=fill, stroke=stroke, rx=6))
      out.append(text(x + (w - 12) / 2, y + 20, f"{p} %", size=12.5, weight=700, fill=INK, anchor="middle"))
      out.append(text(x + (w - 12) / 2, y + 32, f"{num} of {r['n']}", size=9.5, fill=MUTED, anchor="middle"))
    for (_, _, x), w in ((cols[5], cw[5]),):
      out.append(rect(x, y + 4, w - 12, 32, fill=CHIP, stroke=LINE, rx=6, dash="4 3"))
      out.append(text(x + (w - 12) / 2, y + 25, "no data yet", size=11, fill=FAINT, anchor="middle"))
    y += 46
  y += 14
  out += legend(40, y, [("#EFF6FF", "#93C5FD", "count of derived items (proposed, not approved)"),
                        (RED_BG, RED, "none"), (AMBER_BG, AMBER, "partial"), (GREEN_BG, GREEN, "complete"),
                        (CHIP, LINE + " dashed", "no data source yet")])
  out.append(text(40, y + 24, "“Named”: a test-specification case cites the ID. “Linked”: links/verification.yaml " +
                  "links an existing test to it (WP-W-06 §4.1, §4.9). Both are specified links, not a passed test (K7).",
                  size=11, fill=MUTED))
  out.append(text(40, y + 40, "Allocated: the requirement's allocated_to names elements of the SysML model " +
                  "(check M8). A requirement under several goals counts in each row.", size=11, fill=MUTED))
  allr = goal_row(d, rows[-1][2])
  return svg(W, y + 58, "Figure 4 · Trace depth per safety goal",
             "For each safety goal: the derived and refined requirement counts, the share allocated to model elements " +
             f"and the share named by a test-specification case. Over all goals {allr['alloc']} of {allr['n']} " +
             f"requirements are allocated, {allr['named']} named and {allr['linked']} linked to an existing test; none is " +
             "verified by a recorded passed test.", out)


# ---------------------------------------------------------------- Figure 5: TSR blocks x goals

HEAT = ["#FFFFFF", "#FFEDD5", "#FED7AA", "#FDBA74", "#FB923C", "#EA580C", "#C2410C"]


def fig5(d: Data) -> str:
  gs = goals(d)
  x0, cw, ch = 500, 84, 34
  W = max(1280, x0 + len(gs) * cw + 160)  # room for the "TSRs" and "no goal" columns
  ancestors: dict[str, set[str]] = defaultdict(set)
  for g in gs:
    for t in descendants(d, g):
      ancestors[t].add(g)
  tsrs = sorted(d.m.ids["TSR"])
  blocks = sorted({t.split("-")[1][0] for t in tsrs})
  grid = {(b, g): sum(1 for t in tsrs if t.split("-")[1][0] == b and g in ancestors[t]) for b in blocks for g in gs}
  peak = max(grid.values()) or 1
  out = header(W, 5, "Where each safety goal lands: TSR blocks × goals",
               "Cell = TSRs in the block that trace up to the goal through their parents. A TSR serving several goals " +
               "counts in each column.", "WP-T-01 §6 · WP-S-02")
  for j, g in enumerate(gs):
    out.append(text(x0 + j * cw + cw / 2 - 4, 116, g, size=11, weight=700, fill=MUTED, anchor="middle"))
  out.append(text(x0 + len(gs) * cw + 40, 116, "TSRs", size=11, weight=700, fill=MUTED, anchor="middle"))
  out.append(text(x0 + len(gs) * cw + 110, 116, "no goal", size=11, weight=700, fill=MUTED, anchor="middle"))
  y = 130
  for b in blocks:
    in_block = [t for t in tsrs if t.split("-")[1][0] == b]
    out.append(text(48, y + 22, f"{b}xx", size=12.5, weight=700, family=MONO))
    out.append(text(100, y + 22, d.blocks.get(b, ""), size=12))
    for j, g in enumerate(gs):
      v = grid[(b, g)]
      lvl = 0 if v == 0 else 1 + min(len(HEAT) - 2, int((len(HEAT) - 2) * v / peak + 0.5))
      out.append(rect(x0 + j * cw, y, cw - 8, ch, fill=HEAT[lvl] if v else CHIP, stroke=HAIR if not v else "none",
                      rx=6, sw=1))
      out.append(text(x0 + j * cw + (cw - 8) / 2, y + 22, str(v) if v else "·", size=12.5,
                      weight=700 if v else "", fill="#FFFFFF" if lvl >= 5 else (INK if v else FAINT),
                      anchor="middle"))
    out.append(text(x0 + len(gs) * cw + 40, y + 22, str(len(in_block)), size=12.5, weight=700, anchor="middle"))
    orphan = sum(1 for t in in_block if not ancestors[t])
    out.append(text(x0 + len(gs) * cw + 110, y + 22, str(orphan) if orphan else "·", size=12,
                    fill=MUTED if orphan else FAINT, anchor="middle"))
    y += 40
  y += 16
  out.append(text(40, y, "Block names are the WP-S-02 section titles. “No goal”: TSRs whose parents reach no " +
                  "safety goal (operation requirements in 8xx, for example).", size=11, fill=MUTED))
  scale_x = 40
  out.append(text(scale_x, y + 26, "Fewer", size=10.5, fill=MUTED))
  for i, c in enumerate(HEAT[1:]):
    out.append(rect(scale_x + 40 + i * 26, y + 16, 22, 14, fill=c, stroke="none", rx=3, sw=0))
  out.append(text(scale_x + 40 + 6 * 26 + 4, y + 26, f"more TSRs (max {peak})", size=10.5, fill=MUTED))
  return svg(W, y + 44, "Figure 5 · TSR blocks × safety goals",
             "Heat map of how many TSRs of each block 1xx–8xx trace up to each safety goal: " +
             "; ".join(f"{b}xx " + ", ".join(f"{g} {grid[(b, g)]}" for g in gs) for b in blocks) + ".", out)


# ---------------------------------------------------------------- Figure 6: assumption exposure

STATUS_PILL = {"Unverified": (RED_BG, RED), "Not started": (RED_BG, RED), "Partially": (AMBER_BG, AMBER)}
CREDIT_KINDS = [("HE", HAZ, "hazardous events (controllability rating)"), ("SG", SAFETY, "safety goals"),
                ("TSR", AOU_C, "TSRs"), ("HWSR", HW, "HWSRs")]


def fig6(d: Data) -> str:
  W = 1280
  credit = aou_credits(d)
  used = sorted((a for a, c in credit.items() if sum(c.values())),
                key=lambda a: (-(3 * credit[a]["HE"] + 2 * credit[a]["SG"] + sum(credit[a].values())), a))
  unused = [a for a in credit if not sum(credit[a].values())]
  out = header(W, 6, "Assumption exposure: what rests on each assumption of use",
               "If an assumption fails, every rating and requirement that credits it is at stake. Unverified " +
               "assumptions with the most exposure are the first to verify.", "WP-T-01 §3.2 · WP-C-01 §7")
  out.append(text(48, 112, "AOU", size=10.5, weight=700, fill=MUTED))
  out.append(text(130, 112, "STATUS (WP-C-01 §7)", size=10.5, weight=700, fill=MUTED))
  out.append(text(330, 112, "CREDITED BY", size=10.5, weight=700, fill=MUTED))
  unit = 22
  y = 124
  for a in used:
    st = d.m.items[a].get("aou_status", "")
    short = st.split(" (")[0] if not st.startswith("Assumption") else "SOTIF-managed"
    fill, stroke = STATUS_PILL.get(short, (GREY_BG, FAINT))
    out.append(text(48, y + 15, a, size=12, weight=700, family=MONO))
    out.append(rect(130, y + 2, 7 * len(short) + 18, 18, fill=fill, stroke=stroke, rx=9, sw=1))
    out.append(text(139, y + 15, short, size=10.5, weight=700, fill=stroke))
    x = 330
    parts = []
    for k, colour, _ in CREDIT_KINDS:
      n = credit[a][k]
      if n:
        out.append(rect(x, y + 3, n * unit - 3, 16, fill=colour, stroke="none", rx=3, sw=0))
        x += n * unit
        parts.append(f"{n} {k}")
    out.append(text(600, y + 15, " · ".join(parts), size=11.5, fill=INK))
    y += 28
  if unused:
    out.append(text(48, y + 15, ", ".join(unused), size=11.5, fill=MUTED, family=MONO))
    out.append(text(330, y + 15, "not credited by any item in the trace data", size=11.5, fill=MUTED,
                    style="italic"))
    y += 28
  y += 26
  out += legend(40, y, [(c, c, label) for _, c, label in CREDIT_KINDS])
  out.append(text(40, y + 24, "Ordered by exposure (hazardous-event and goal credits weigh most). HE and SG credit through " +
                  "aou_dependency; TSR and HWSR through parents.", size=11, fill=MUTED))
  return svg(W, y + 44, "Figure 6 · Assumption exposure",
             "For each assumption of use, the hazardous events, safety goals, TSRs and HWSRs that credit it: " +
             "; ".join(f"{a} " + ", ".join(f"{credit[a][k]} {k}" for k, _, _ in CREDIT_KINDS if credit[a][k])
                       for a in used) + (f". Not credited: {', '.join(unused)}." if unused else "."), out)


# ---------------------------------------------------------------- Figure 7: consistency checks

CHECK_SHORT = {
  "K1": "files parse, keys, status enum", "K2": "IDs unique · “no ID removed”", "K3": "references resolve, right kind",
  "K4": "SG → FSR → TSR → SW / HW", "K5": "child ASIL ≥ parent", "K6": "@req tags resolve",
  "K7": "verified ⇒ passing test", "K8": "SWSR ≥ A has a code tag", "K9": "HIL reqs have a procedure",
  "K10": "every SR-A file tagged", "K11": "WP tables = YAML", "K12": "every HE → SG or exempt",
  "R1": "HE ASIL = S + E + C", "R2": "SG ASIL = max of HEs", "R3": "AoU-fail ASIL rule", "R4": "every H has an HE",
  "X1": "HARA = WP-C-03", "X2": "AoU = WP-C-01", "X3": "generated YAML fresh",
  "P1": "unverified AoU in WP-K-01", "P2": "IDs in the block ranges", "S1": "SH → FI, TC → FM complete",
  "A1": "AIR basis · AIR ↔ TSR",
  "C1": "TS → CSG → CSR; SG → CSG",
  "Q1": "SYS: function, alloc, row",
  "I1": "IFR agreed only by review",
}
CHECK_GROUPS = [("STRUCTURE AND DERIVATION (WP-P-06 §7)", ("K1", "K2", "K3", "K4", "K5", "K11", "K12")),
                ("CODE AND TEST LINKS, AND PLANNED CHECKS", ("K6", "K7", "K8", "K9", "K10", "P1", "P2")),
                ("LIONDRIVER EXTENSIONS", ("R1", "R2", "R3", "R4", "X1", "X2", "X3")),
                ("CHAINS OF THE OTHER STANDARDS", ("S1", "A1", "C1", "Q1", "I1"))]
CHECK_STYLE = {"yes": (GREEN_BG, GREEN, ""), "partly": (AMBER_BG, AMBER, ""), "no": (CHIP, FAINT, "4 3")}


def fig7(d: Data) -> str:
  W = 1280
  status = {c: w for c, _, w in d.checks}
  missing = [c for c in status if c not in CHECK_SHORT] + [c for g in CHECK_GROUPS for c in g[1] if c not in status]
  if missing:
    raise SystemExit(f"trace_figures.py: README §6 and CHECK_SHORT/CHECK_GROUPS disagree on {missing}")
  tile_w, tile_h, gap = 163, 58, 10.5
  out = header(W, 7, "Consistency checks: what is enforced, what is a roadmap",
               "Each tile is a check of §6. Green runs in CI and passes; amber runs in part; grey is not implemented. " +
               "The middle row is the path from “specified” to “verified”.", "WP-T-01 §6")
  y = 104
  for title, ids in CHECK_GROUPS:
    out.append(text(40, y + 8, title, size=10.5, weight=700, fill=MUTED))
    y += 18
    for i, c in enumerate(ids):
      fill, stroke, dash = CHECK_STYLE[status[c]]
      x = 40 + i * (tile_w + gap)
      out.append(rect(x, y, tile_w, tile_h, fill=fill, stroke=stroke, rx=8, dash=dash, sw=1.4))
      out.append(text(x + 12, y + 22, c, size=14, weight=700, fill=INK if status[c] != "no" else MUTED))
      out.append(text(x + 12, y + 42, CHECK_SHORT[c], size=10.5, fill=MUTED))
    y += tile_h + 26
  n = Counter(status.values())
  out += legend(40, y + 6, [(GREEN_BG, GREEN, f"implemented · {n['yes']}"), (AMBER_BG, AMBER, f"partly · {n['partly']}"),
                            (CHIP, FAINT + " dashed", f"not yet · {n['no']}")])
  return svg(W, y + 30, "Figure 7 · Consistency checks",
             f"{n['yes']} checks implemented ({', '.join(c for c, w in status.items() if w == 'yes')}), " +
             f"{n['partly']} partly ({', '.join(c for c, w in status.items() if w == 'partly')}), {n['no']} not yet " +
             f"({', '.join(c for c, w in status.items() if w == 'no')}).", out)


# ---------------------------------------------------------------- Figure 8: allocation resolution

def fig8(d: Data) -> str:
  W = 1280
  rows = []
  for k in ("TSR", "FSR", "SWSR", "HWSR", "CSR", "SYS"):
    ids = [i for i in d.alloc if d.kind[i] == k]
    c = Counter(d.alloc[i] for i in ids)
    rows.append((k, len(ids), c))
  rows.append(("All", len(d.alloc), Counter(d.alloc.values())))
  out = header(W, 8, "Allocation: do requirements land on real architecture elements?",
               "Every allocated_to value matched against the SysML v2 model (check M8). A value is resolved when every " +
               "identifier in it names a model element.", "WP-T-01 §3.2 · SysML report")
  x0, bw, y = 130, 860, 104
  peak = max(n for _, n, _ in rows)
  for k, n, c in rows:
    if k == "All":
      out.append(line(40, y - 6, W - 40, y - 6, stroke=HAIR, sw=1))
      y += 4
    out.append(text(48, y + 19, k, size=13, weight=700))
    x = x0
    full = bw * n / peak
    for s, colour in (("resolved", SW), ("partly resolved", AMBER), ("not resolved", RED)):
      v = c[s]
      if not v:
        continue
      w = full * v / n
      out.append(rect(x, y + 4, w, 22, fill=colour, stroke="none", rx=4, sw=0))
      lab = str(v) if s != "not resolved" or w < 140 else f"{v} not resolved"
      if w > 24:
        out.append(text(x + w / 2, y + 19, lab, size=11, weight=700, fill="#FFFFFF", anchor="middle"))
      x += w
    out.append(text(x0 + full + 12, y + 19, f"{c['resolved']} / {n} · {pct(c['resolved'], n)} %", size=12,
                    weight=700 if k == "All" else "", fill=INK))
    y += 36
  y += 12
  top = sorted(d.alloc_values.items(), key=lambda kv: (-len(kv[1]), kv[0]))
  out.append(text(40, y + 4, f"Most common unresolved values ({len(top)} distinct, by number of requirements):",
                  size=11.5, weight=700))
  y += 16
  x = 40
  shown = 0
  for value, ids in top:
    label = f"{value if len(value) <= 34 else value[:32] + '…'} ×{len(ids)}"
    w = 5.9 * len(label) + 18
    if x + w > W - 150:
      if y > 104 + 36 * 5 + 50:
        break
      x, y = 40, y + 26
    out.append(rect(x, y, w, 20, fill=RED_BG, stroke="#F5B5A8", rx=10, sw=1))
    out.append(text(x + 9, y + 14, label, size=10.5, fill=RED))
    x += w + 8
    shown += 1
  if shown < len(top):
    out.append(text(x, y + 14, f"… and {len(top) - shown} more", size=10.5, fill=MUTED))
  y += 46
  out += legend(40, y, [(SW, SW, "resolved to a model element"), (RED, RED, "not resolved")])
  hw = sum(1 for i, st in d.alloc.items() if st == "not resolved" and d.kind[i] == "HWSR")
  out.append(text(W - 40, y, f"{hw} of {rows[-1][2]['not resolved']} unresolved allocations are HWSRs: WP-H-01 " +
                  "allocates to part descriptions, not element IDs.", size=11, fill=MUTED, anchor="end"))
  allc = rows[-1][2]
  return svg(W, y + 22, "Figure 8 · Allocation resolution",
             f"Of {len(d.alloc)} allocated_to values {allc['resolved']} resolve to SysML model elements: " +
             ", ".join(f"{k} {c['resolved']} of {n}" for k, n, c in rows[:-1]) + ".", out)


# ---------------------------------------------------------------- Figures 9 and 10: the system V (vmodel.py)

def fig9(d: Data) -> str:
  W = 1280
  vd = vmodel.load(d.m)
  dr = vmodel.draw("status", "full", model=vd)
  out = header(W, 9, "The system V, status lens",
               "Register status of each level's work products, the test cases specified and run on the right, the gate " +
               "records below. Nothing is approved or verified yet.", "WP-T-01 §2.1 · WP-M-00 §3")
  out += [vmodel.marker_defs(dr.body), vmodel.place(dr, (W - dr.width) / 2, 96, dr.width)]
  return svg(W, int(96 + dr.height + 16), "Figure 9 · The system V, status lens", dr.desc, out)


def fig10(d: Data) -> str:
  W = 1280
  vd = vmodel.load(d.m)
  dr = vmodel.goal_grid(vd, width=W, top=100)
  out = header(W, 10, "The system V per safety goal",
               "Left: the goal's items at each level (TSRs allocated to operation left out). Right: how many of them the " +
               "paired test cases name, a specified link, not a passed test.", "WP-T-01 §2.1")
  out += [vmodel.marker_defs(dr.body), *dr.body]
  return svg(W, int(dr.height), "Figure 10 · The system V per safety goal", dr.desc, out)


# ---------------------------------------------------------------- main

FIGURES = {
  "fig-1-trace-workflow.svg": fig1,
  "fig-2-trace-data-model.svg": fig2,
  "fig-3-derivation-flow.svg": fig3,
  "fig-4-trace-depth-per-goal.svg": fig4,
  "fig-5-tsr-blocks-by-goal.svg": fig5,
  "fig-6-aou-exposure.svg": fig6,
  "fig-7-consistency-checks.svg": fig7,
  "fig-8-allocation-resolution.svg": fig8,
  "fig-9-system-v-status.svg": fig9,
  "fig-10-v-per-goal.svg": fig10,
}


def render_all() -> dict[Path, str]:
  d = load()
  return {FIG_DIR / name: fn(d) for name, fn in FIGURES.items()}


def main(argv: list[str]) -> int:
  outputs = render_all()
  if "--check" in argv:
    stale = [p for p, t in outputs.items() if not p.exists() or p.read_text(encoding="utf-8") != t]
    extra = sorted(set(FIG_DIR.glob("fig-*.svg")) - set(outputs))
    for p in stale:
      print(f"{p.relative_to(REPO)} is stale; run assurance/trace/tools/trace_figures.py")
    for p in extra:
      print(f"{p.relative_to(REPO)} is not generated by trace_figures.py; delete it")
    if not stale and not extra:
      print(f"trace figures: {len(outputs)} up to date")
    return 1 if stale or extra else 0
  FIG_DIR.mkdir(exist_ok=True)
  for p, t in outputs.items():
    p.write_text(t, encoding="utf-8")
    print(f"wrote {p.relative_to(REPO)}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
