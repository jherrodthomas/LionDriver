#!/usr/bin/env python3
"""Draw WP-S-03 Figure 6-1, defence in depth per safety goal (fig-s03-6-1-defence-in-depth.svg).

For each safety goal SG-01…SG-07 the figure shows the protection layers between a fault and the hazard, from the
inside out, and what each layer contributes today:

  Host SoC (E-01)            TSRs whose allocated_to names SoC
  Safety envelope            TSRs whose allocated_to names P-SW, P-HW or HAR (panda MCU, its firmware, the harness),
                             plus envelope assumptions of use
  Vehicle ECUs               TSRs allocated to EXT and the vehicle assumptions of use (EPS, PCM, brake, PCS, VSC)
  Driver                     the HARA controllability rating of the goal's hazardous events and the driver
                             assumptions of use
  Operation (OPS)            TSRs allocated to OPS (installation, configuration, service); they act across layers

Every count is computed from the trace data in assurance/trace/items/*.yaml:
  - tsr.yaml (generated from WP-S-02 §3–§9 and WP-S-06): allocated_to, mechanism, baseline_impl, parents;
  - goals.yaml and hazards.yaml (WP-C-03): ASIL, aou_dependency, controllability `c`;
  - aou.yaml (WP-C-01 §7): aou_status and the text of each assumption.
A TSR reaches a goal when its parents lead there, transitively (TSR → FSR → SG, TSR → SG, TSR → TSR). A goal credits an
assumption through its own or its hazardous events' aou_dependency, or when a TSR under the goal names it in
baseline_impl ("Unverified (AOU-04R)"). A TSR allocated to several layers counts in each of them.

Status of each TSR, from its baseline_impl text (the conservative rule drawn in the figure, see `classify`):
  assumed      allocated to EXT, or baseline_impl starts with "Unverified" (credited only through an AoU)
  implemented  baseline_impl starts with "Implemented" or "Met" and carries none of the qualifiers in QUALIFIERS
  not impl.    baseline_impl starts with "Not", "Unknown" or "Not verified"; OPS whose status says "Blocked"
  partly       everything else: "Partial", "Partly", a qualified "Implemented"/"Met", other OPS procedures
Nothing is verified: "implemented" is drawn blue, never green.

Hand-listed values (the layer of each assumption, the short goal labels) carry the exact source text they were read
from; --check fails if that text no longer appears in the trace data.

    python3 fig_s03_defence_in_depth.py            # write the SVG
    python3 fig_s03_defence_in_depth.py --check    # fail if a source text changed or the SVG is stale

Standard library only (the YAML loader of check_trace.py falls back to its own subset parser). Output is deterministic.
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ITEMS = REPO / "assurance" / "trace" / "items"
sys.path.insert(0, str(REPO / "assurance" / "trace" / "tools"))
import check_trace as ct

OUT = "fig-s03-6-1-defence-in-depth.svg"

# ---------------------------------------------------------------- palette (assurance figure style, trace_figures.py)

FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SFMono-Regular', Menlo, Consolas, monospace"
INK, MUTED, FAINT, LINE, HAIR = "#0F172A", "#475569", "#94A3B8", "#CBD5E1", "#E2E8F0"
CHIP = "#F8FAFC"
SAFETY, SAFETY_BG = "#C2410C", "#FFF7ED"
SW, SW_BG = "#0F766E", "#F0FDFA"
AMBER, AMBER_BG = "#D97706", "#FFFBEB"
RED, RED_BG = "#D2553F", "#FEF2F2"
BLUE, BLUE_BG, BLUE_LINE = "#1D4ED8", "#EFF6FF", "#93C5FD"
GREY_BG = "#F1F5F9"

# ---------------------------------------------------------------- SVG helpers (copied from trace_figures.py)


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


MARKERS = {"muted": MUTED, "safety": SAFETY}
HATCH = ('<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">' +
         f'<rect width="6" height="6" fill="{GREY_BG}"/><line x1="0" y1="0" x2="0" y2="6" stroke="{LINE}" ' +
         'stroke-width="2"/></pattern>')


def svg(width: int, height: int, title: str, desc: str, body: list[str]) -> str:
  defs = "".join(
    f'<marker id="{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" ' +
    f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for k, c in MARKERS.items())
  head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" ' +
          f'font-family="{FONT}" role="img">')
  return "\n".join([head, el("title", title), el("desc", desc), f"<defs>{defs}{HATCH}</defs>",
                    rect(0, 0, width, height, fill="#FFFFFF", stroke="none", rx=0, sw=0), *body, "</svg>"]) + "\n"


def header(width: int, number: str, title: str, subtitle: str, ref: str) -> list[str]:
  return [text(40, 44, f"Figure {number} · {title}", size=20, weight=700),
          text(40, 66, subtitle, size=12.5, fill=MUTED),
          text(width - 40, 44, ref, size=11, fill=MUTED, anchor="end"),
          line(40, 82, width - 40, 82, stroke=HAIR, sw=1)]


# ---------------------------------------------------------------- hand-listed values, each with its source text

# Layer of each assumption of use; src must appear in the assumption's text in aou.yaml.
AOU_LAYER = {
  "AOU-01": ("vehicle", "The Toyota EPS limits the torque applied for LKA requests"),
  "AOU-02": ("driver", "A normal driver can override full LKA torque"),
  "AOU-03": ("vehicle", "Driver brake pedal application always produces braking"),
  "AOU-04": ("vehicle", "The stock PCS/AEB keeps full function"),
  "AOU-05": ("vehicle", "The PCM bounds ACC acceleration and deceleration requests"),
  "AOU-06": ("driver", "The driver is licensed, attentive"),
  "AOU-07": ("driver", "only trained safety drivers operate the item"),
  "AOU-09": ("vehicle", "The vehicle is maintained, unmodified"),
  "AOU-10": ("vehicle", "VSC/ABS are enabled and functional"),
  "AOU-12": ("vehicle", "The cluster cruise indicator is driven by PCM state"),
  "AOU-13": ("envelope", "The de-energised harness relay connects the forward camera"),
  "AOU-14": ("ops", "is used with openpilot's default alternative experience"),
  "AOU-15": ("ops", "is used only on camera-ACC configurations"),
}

# Short goal labels; src must appear in the goal's text in goals.yaml.
SG_LABEL = {
  "SG-01": ("Lateral motion beyond control", "cause lateral motion of the vehicle that exceeds what the driver can"),
  "SG-02": ("Lateral loss without warning", "lose or degrade lateral control while engaged without giving"),
  "SG-03": ("Unintended acceleration", "cause unintended vehicle acceleration"),
  "SG-04": ("Uncontrollable deceleration", "cause deceleration that exceeds what following traffic"),
  "SG-05": ("Release on driver action", "release control immediately when the driver brakes, cancels"),
  "SG-06": ("Decel. loss without warning", "lose longitudinal deceleration capability while engaged without"),
  "SG-07": ("Stock PCS/AEB untouched", "suppress, delay or alter the vehicle's stock pre-collision"),
}

# ---------------------------------------------------------------- data

LAYERS = [  # key, title, subtitle, allocation tokens
  ("host", "Host SoC", "E-01 · alloc. SoC · QM", ("SoC",)),
  ("envelope", "Safety envelope", "E-03 · E-04a · E-05 · P-SW, P-HW, HAR", ("P-SW", "P-HW", "HAR")),
  ("vehicle", "Vehicle ECUs", "EPS · PCM · brake · PCS · alloc. EXT", ("EXT",)),
  ("driver", "Driver", "HARA C rating · AoU", ()),
]
OPS_LAYER = ("ops", "Operation", "alloc. OPS · across layers", ("OPS",))
ALLOC_TOKEN = re.compile(r"\b(P-SW|P-HW|HAR|SoC|EXT|OPS)\b")
AOU_REF = re.compile(r"\bAOU-(\d\d)R?\b")

STATUSES = ("implemented", "partly", "not", "assumed")
# Qualifiers that keep an "Implemented"/"Met" text at "partly": the value is not derived, the behaviour exists only in
# the opt-in reference build or for a subset, it is provided through another requirement's design, or it is a
# procedure reference (OPS) rather than code.
QUALIFIERS = ("without rationale", "reference build", "Met for", "Implemented for", "Implemented by")
RULE = (  # drawn as lines under the legend
  "Status rule, per TSR from baseline_impl: “Implemented …”/“Met …” without a qualifier = implemented; “Partial”, " +
  "“Partly” or a qualified one (no rationale, reference build only, subset, via another TSR) = partly;",
  "“Not …”, “Unknown”, “Not verified” = not implemented; EXT or “Unverified (AOU-…)” = assumed; OPS procedures = " +
  "partly (“Blocked”: not implemented).",
  "A cell is implemented only if all its TSRs are, not implemented only if all are not, otherwise partly. A TSR " +
  "allocated to two layers counts in both.")


def load_items() -> dict[str, dict]:
  items: dict[str, dict] = {}
  for name in ("goals.yaml", "hazards.yaml", "aou.yaml", "fsr.yaml", "tsr.yaml"):
    for it in ct.load_yaml(ITEMS / name):
      items[it["id"]] = it
  return items


def allocation(it: dict) -> set[str]:
  return set(ALLOC_TOKEN.findall(str(it.get("allocated_to") or "")))


def classify(it: dict) -> str:
  """Status of one TSR at the baseline, from baseline_impl (conservative: when unsure, the lower class)."""
  alloc = allocation(it)
  impl = str(it.get("baseline_impl") or "").replace("**", "").strip()
  if alloc == {"OPS"}:
    return "not" if "Blocked" in impl else "partly"
  if alloc == {"EXT"} or impl.startswith("Unverified"):
    return "assumed"
  if impl.startswith(("Not", "Unknown")):
    return "not"
  if impl.startswith(("Implemented", "Met")):
    head = re.split(r"[.:;(]", impl, maxsplit=1)[0]
    return "partly" if any(q in head for q in QUALIFIERS) else "implemented"
  return "partly"


def layer_status(statuses: list[str]) -> str:
  """Aggregate of a cell: assumed if all assumed; else worst-wins over the item TSRs."""
  own = [s for s in statuses if s != "assumed"]
  if not own:
    return "assumed" if statuses else "none"
  if all(s == "implemented" for s in own):
    return "implemented"
  if all(s == "not" for s in own):
    return "not"
  return "partly"


def mechanisms(it: dict) -> list[str]:
  m = str(it.get("mechanism") or "")
  return [t.split()[0] for t in m.split(",") if t.strip()]


def missing_sources(items: dict[str, dict]) -> list[str]:
  out = []
  for aid, (_, src) in AOU_LAYER.items():
    if aid not in items or src not in items[aid].get("text", ""):
      out.append(f"{aid}: {src!r}")
  for sg, (_, src) in SG_LABEL.items():
    if sg not in items or src not in items[sg].get("text", ""):
      out.append(f"{sg}: {src!r}")
  return out


def build_model(items: dict[str, dict]) -> dict:
  kind = {i: it["kind"] for i, it in items.items()}
  children: dict[str, list[str]] = defaultdict(list)
  for i, it in items.items():
    for p in it.get("parents") or []:
      children[p].append(i)
  goals = sorted(i for i, k in kind.items() if k == "safety-goal")
  if set(goals) != set(SG_LABEL):
    raise SystemExit(f"goals.yaml goals {goals} differ from SG_LABEL; update fig_s03_defence_in_depth.py")

  def below(root: str) -> set[str]:
    seen: set[str] = set()
    todo = [root]
    while todo:
      for c in children.get(todo.pop(), []):
        if c not in seen and kind.get(c) in ("fsr", "tsr"):
          seen.add(c)
          todo.append(c)
    return seen

  status = {i: classify(it) for i, it in items.items() if kind[i] == "tsr"}
  rows = []
  for g in goals:
    sg = items[g]
    tsrs = sorted(t for t in below(g) if kind[t] == "tsr")
    hes = [h for h in sg.get("parents") or [] if kind.get(h) == "hazardous-event"]
    aous = set(sg.get("aou_dependency") or [])
    for h in hes:
      aous |= set(items[h].get("aou_dependency") or [])
    for t in tsrs:
      aous |= {f"AOU-{n}" for n in AOU_REF.findall(str(items[t].get("baseline_impl") or ""))}
    unknown = sorted(a for a in aous if a not in AOU_LAYER)
    if unknown:
      raise SystemExit(f"{g} credits {unknown}: add the layer to AOU_LAYER in fig_s03_defence_in_depth.py")
    cells = {}
    for key, _, _, tokens in [*LAYERS, OPS_LAYER]:
      ids = [t for t in tsrs if allocation(items[t]) & set(tokens)]
      st = ["assumed" if key == "vehicle" else status[t] for t in ids]
      la = sorted(a for a in aous if AOU_LAYER[a][0] == key)
      cells[key] = {
        "tsrs": ids,
        "counts": Counter(st),
        "mech": Counter(m for t in ids for m in mechanisms(items[t])),
        "aous": la,
        "aou_status": {a: items[a].get("aou_status", "") for a in la},
        "status": layer_status(st + ["assumed"] * len(la)),
      }
    cells["driver"]["c"] = Counter(int(items[h]["c"]) for h in hes if items[h].get("c") is not None)
    cells["driver"]["hes"] = len(hes)
    rows.append({"id": g, "asil": sg.get("asil", ""), "cells": cells})
  return {"rows": rows, "status": status, "items": items}


# ---------------------------------------------------------------- drawing

STYLE = {  # fill, stroke, dash, label
  "implemented": (BLUE_BG, BLUE_LINE, "", "implemented at baseline, not verified"),
  "partly": (AMBER_BG, AMBER, "", "partly implemented"),
  "not": (RED_BG, RED, "", "not implemented"),
  "assumed": ("url(#hatch)", FAINT, "5 4", "assumed (AoU or HARA rating, unverified)"),
  "none": ("#FFFFFF", HAIR, "3 4", "no TSR or AoU of this goal"),
}
BAR = {"implemented": BLUE, "partly": AMBER, "not": RED, "assumed": FAINT}
SHORT = {"implemented": "impl.", "partly": "partly", "not": "not", "assumed": "assumed"}

W = 1280
X0 = 212                       # first layer column
COLS = [("host", 200), ("envelope", 236), ("vehicle", 214), ("driver", 160)]
GAP = 10
OPS_X, OPS_W = 1076, 164
ROW_H, CELL_H = 80, 70


def col_x() -> dict[str, tuple[float, float]]:
  out, x = {}, X0
  for k, w in COLS:
    out[k] = (x, w)
    x += w + GAP
  out["ops"] = (OPS_X, OPS_W)
  return out


def mech_line(c: Counter, n: int = 3) -> str:
  return " · ".join(f"{m} {v}" for m, v in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:n])


def ids_line(ids: list[str], width: float) -> str:
  s = ", ".join(ids)
  limit = int(width / 6.4)
  return s if len(s) <= limit else s[: limit - 1].rsplit(",", 1)[0] + ", …"


def draw_tsr_cell(x, y, w, cell, out):
  fill, stroke, dash, _ = STYLE[cell["status"]]
  out.append(rect(x, y, w, CELL_H, fill=fill, stroke=stroke, dash=dash, sw=1.4, rx=8))
  n = len(cell["tsrs"])
  if not n and not cell["aous"]:
    out.append(text(x + w / 2, y + CELL_H / 2 + 4, "—", size=12, fill=FAINT, anchor="middle"))
    return
  label = f"{n} TSR" + ("s" if n != 1 else "")
  if cell["aous"]:
    label += f" + {', '.join(cell['aous'])}"
  out.append(text(x + 10, y + 18, label, size=12.5, weight=700))
  # stacked bar of statuses
  bx, bw = x + 10, w - 20
  cx = bx
  total = sum(cell["counts"].values())
  for s in STATUSES:
    v = cell["counts"][s]
    if not v:
      continue
    seg = bw * v / total
    out.append(rect(cx, y + 26, max(seg - 1.5, 1.5), 8, fill=BAR[s], stroke="none", rx=2, sw=0))
    cx += seg
  parts = [f"{cell['counts'][s]} {SHORT[s]}" for s in STATUSES if cell["counts"][s]]
  out.append(text(x + 10, y + 49, " · ".join(parts), size=10.5, fill=MUTED))
  mech = mech_line(cell["mech"])
  out.append(text(x + 10, y + 63, mech or "procedures (no SM type)", size=10.5, fill=INK if mech else MUTED,
                  family=MONO if mech else ""))


def draw_vehicle_cell(x, w, y, cell, out):
  fill, stroke, dash, _ = STYLE[cell["status"]]
  out.append(rect(x, y, w, CELL_H, fill=fill, stroke=stroke, dash=dash, sw=1.4, rx=8))
  if cell["status"] == "none":
    out.append(text(x + w / 2, y + CELL_H / 2 + 4, "—", size=12, fill=FAINT, anchor="middle"))
    return
  n = len(cell["tsrs"])
  out.append(text(x + 10, y + 18, f"{n} EXT TSR{'s' if n != 1 else ''} · {len(cell['aous'])} AoU", size=12.5,
                  weight=700))
  out.append(text(x + 10, y + 34, ids_line(cell["tsrs"], w - 20) or "no EXT TSR", size=10.5, fill=MUTED,
                  family=MONO))
  out.append(text(x + 10, y + 49, ids_line(cell["aous"], w - 20) or "no AoU", size=10.5, fill=INK, family=MONO))
  st = sorted(set(cell["aou_status"].values()))
  out.append(text(x + 10, y + 63, ("AoU " + ", ".join(s.lower() for s in st)) if st else "", size=10.5,
                  fill=MUTED))


def draw_driver_cell(x, w, y, cell, out):
  fill, stroke, dash, _ = STYLE["assumed"]
  out.append(rect(x, y, w, CELL_H, fill=fill, stroke=stroke, dash=dash, sw=1.4, rx=8))
  c = cell["c"]
  out.append(text(x + 10, y + 18, " · ".join(f"C{k} ×{c[k]}" for k in sorted(c)), size=12.5, weight=700))
  out.append(text(x + 10, y + 34, f"of {cell['hes']} hazardous events", size=10.5, fill=MUTED))
  out.append(text(x + 10, y + 49, ", ".join(cell["aous"]) if cell["aous"] else "no driver AoU credited", size=10.5,
                  fill=INK if cell["aous"] else MUTED, family=MONO if cell["aous"] else ""))
  st = sorted(set(cell["aou_status"].values()))
  if st:
    out.append(text(x + 10, y + 63, "AoU " + ", ".join(s.lower() for s in st), size=10.5, fill=MUTED))


def figure(model: dict) -> str:
  rows = model["rows"]
  cx = col_x()
  out = header(W, "6-1", "Defence in depth per safety goal",
               "Protection layers between a fault and the hazard, inside to outside, with the TSRs and assumptions " +
               "that make up each layer and their status at the baseline.", "WP-S-03 §6 · trace data")
  # fault -> hazard arrow over the layer columns
  ax0, ax1 = cx["host"][0], cx["driver"][0] + cx["driver"][1]
  out.append(text(ax0, 104, "FAULT", size=10.5, weight=700, fill=SAFETY))
  out.append(text(ax1, 104, "HAZARD", size=10.5, weight=700, fill=SAFETY, anchor="end"))
  out.append(line(ax0 + 44, 100, ax1 - 54, 100, stroke=SAFETY, sw=1.4, marker="safety"))
  out.append(text((ax0 + ax1) / 2, 116, "each layer can stop the fault before the next; inside → outside",
                  size=10.5, fill=MUTED, anchor="middle"))
  out.append(text(OPS_X + OPS_W / 2, 104, "PRECONDITION", size=10.5, weight=700, fill=MUTED, anchor="middle"))
  # column heads
  for key, title, sub, _ in [*LAYERS, OPS_LAYER]:
    x, w = cx[key]
    out.append(text(x + 10, 142, title.upper(), size=11, weight=700, fill=INK))
    out.append(text(x + 10, 157, sub, size=10, fill=MUTED))
  out.append(text(48, 142, "SAFETY GOAL", size=11, weight=700))
  out.append(text(48, 157, "ASIL (WP-C-03, proposed)", size=10, fill=MUTED))
  out.append(line(OPS_X - 8, 132, OPS_X - 8, 168 + len(rows) * ROW_H, stroke=HAIR, sw=1, dash="3 4"))
  y = 168
  for r in rows:
    out.append(text(48, y + 26, r["id"], size=14, weight=700))
    out.append(rect(108, y + 13, 58, 18, fill=SAFETY_BG, stroke=SAFETY, rx=9, sw=1))
    out.append(text(137, y + 26, f"ASIL {r['asil']}", size=10, weight=700, fill=SAFETY, anchor="middle"))
    out.append(text(48, y + 48, SG_LABEL[r["id"]][0], size=10.5, fill=MUTED))
    for key in ("host", "envelope", "ops"):
      x, w = cx[key]
      draw_tsr_cell(x, y, w, r["cells"][key], out)
    draw_vehicle_cell(*cx["vehicle"], y, r["cells"]["vehicle"], out)
    draw_driver_cell(*cx["driver"], y, r["cells"]["driver"], out)
    y += ROW_H
  # legend
  y += 8
  out.append(line(40, y, W - 40, y, stroke=HAIR, sw=1))
  y += 24
  x = 40
  for s in ("implemented", "partly", "not", "assumed"):
    fill, stroke, dash, label = STYLE[s]
    out.append(rect(x, y - 11, 22, 14, fill=fill, stroke=stroke, dash=dash, rx=3, sw=1.2))
    out.append(text(x + 28, y, label, size=11, fill=MUTED))
    x += 46 + 5.7 * len(label)
  y += 22
  out.append(text(40, y, "Bar: the TSRs of the cell by status. Monospace: the most frequent SM types of those TSRs " +
                  "(WP-S-02 §2.2: LIM limiter, GATE gating, PLB plausibility, TMO timeout, FR fault reaction, " +
                  "CFG configuration lock, WRN warning …).", size=10.5, fill=MUTED))
  for r_line in RULE:
    y += 17
    out.append(text(40, y, r_line, size=10.5, fill=MUTED))
  y += 17
  out.append(text(40, y, "Nothing here is verified: implemented means the baseline code does it. HARA C ratings, " +
                  "ASILs and AoUs are proposals.", size=10.5, fill=MUTED))
  desc = "; ".join(
    f"{r['id']} ASIL {r['asil']}: host {len(r['cells']['host']['tsrs'])} TSRs {r['cells']['host']['status']}, " +
    f"envelope {len(r['cells']['envelope']['tsrs'])} TSRs {r['cells']['envelope']['status']}, vehicle " +
    f"{len(r['cells']['vehicle']['tsrs'])} EXT TSRs and {len(r['cells']['vehicle']['aous'])} AoUs assumed, driver " +
    f"{r['cells']['driver']['hes']} hazardous events rated by controllability, operation " +
    f"{len(r['cells']['ops']['tsrs'])} TSRs" for r in rows)
  return svg(W, y + 22, "Figure 6-1 · Defence in depth per safety goal",
             "Matrix of safety goals by protection layer (host SoC, safety envelope, vehicle ECUs, driver, plus " +
             "operation) with TSR counts, status at the baseline and SM types. " + desc + ".", out)


def build() -> dict[str, str]:
  items = load_items()
  bad = missing_sources(items)
  if bad:
    raise SystemExit("fig_s03_defence_in_depth.py: source text no longer found: " + "; ".join(bad))
  return {OUT: figure(build_model(items))}


def main(argv: list[str]) -> int:
  outputs = build()
  if "--check" in argv:
    stale = [n for n, t in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != t]
    for n in stale:
      print(f"assurance/03-system/figures/{n} is stale; run fig_s03_defence_in_depth.py")
    if not stale:
      print(f"defence-in-depth figure: {len(outputs)} up to date")
    return 1 if stale else 0
  for n, t in outputs.items():
    (HERE / n).write_text(t, encoding="utf-8")
    print(f"wrote assurance/03-system/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
