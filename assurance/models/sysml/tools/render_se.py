"""Systems-engineering views of the SysML model: V-08 N2 chart, V-09 verification matrix (VCRM).

Called by render_views.render_all for layout entries of kind "n2" and "vcrm"; `extra_outputs` also writes the
per-requirement VCRM page (generated/vcrm.md). Everything drawn comes from the model:

  V-08  every connection whose two ends lie in different components (E-01 to E-05) or outside the item, rolled up to
        the component or the outside element: interfaces with their IF ID, CAN bus attachments and data links. A
        cell (row, column) means "the row element sends to the column element"; its colour is the edge class of
        V-01/V-03 (render_views.edge_class), so the three views share one legend.
  V-09  the SYS, TSR and CSR requirements: verification method (the Verif attribute of WP-S-01/02/07) counted per
        requirement group and grouped by the NASA verification method (analysis, inspection, demonstration, test),
        then how many a case of each verification level verifies («verify» in the model). No case has a result in
        the model, so the result column stays empty until verification is run.

layout.toml gives the title, subtitle and canvas width only.
"""
from __future__ import annotations

import re
from collections import Counter

import render_views as rv
import svgkit as k
import sysml_lite

BLUE, BLUE_LINE, RED, RED_BG = "#2563EB", "#93C5FD", "#D2553F", "#FEF2F2"
SOFT = {"actuation": "#FFF7ED", "ffi": "#F5F3FF", "boot": "#F5F3FF", "sensing": "#F0FDFA", "power": "#FFFBEB",
        "network": "#FAF5FF", "internal": "#F8FAFC", "bus": "#F1F5F9"}

# ---------------------------------------------------------------- V-08 N2


def component(m: sysml_lite.Model, path: str) -> sysml_lite.Element:
  """The component (E-01 to E-05) or the outside element a port or part belongs to."""
  e = m.owner_element(path)
  for a in (e, *e.ancestors()):
    if a.parent is not None and (a.parent.name == "ldsda" or a.parent is m.root):
      return a
  raise sysml_lite.ModelError(f"{path} is not inside a component or the vehicle context")


def n2_cells(m: sysml_lite.Model) -> tuple[list[sysml_lite.Element], dict[tuple[str, str], list[tuple[str, str]]]]:
  cells: dict[tuple[str, str], list[tuple[str, str]]] = {}
  used: set[str] = set()
  for c in m.connections:
    a, b = (component(m, e) for e in c.ends)
    if a is b:
      continue
    cls = rv.edge_class(c) if c.kind != "connect" else "bus"
    lab = c.interface_id or ("CAN" if c.kind == "connect" else "no IF")
    pairs = [(a, b), (b, a)] if c.kind == "connect" else [(a, b)]
    for x, y in pairs:
      entry = (lab, cls)
      if entry not in cells.setdefault((x.path, y.path), []):
        cells[(x.path, y.path)].append(entry)
      used |= {x.path, y.path}
  inside = [e for e in m.root.walk() if e.parent is not None and e.parent.name == "ldsda"]
  outside = [e for e in m.root.children if e.name != "ldsda"]
  order = [e for e in inside + outside if e.path in used]
  return order, cells


def node_label(e: sysml_lite.Element) -> tuple[str, str]:
  title = rv.TITLES.get(e.name, e.name)
  return (e.short if e.short and e.short.startswith("E-") else "", title)


def render_n2(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  view = m.views[vid]
  order, cells = n2_cells(m)
  n = len(order)
  w = spec["width"]
  x0, y0 = 40, 112
  c = (w - 80) / n
  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  n_inside = sum(1 for e in order if e.parent is not None and e.parent.name == "ldsda")
  # the item boundary around the E-0n block of the matrix
  body.append(k.rect(x0 - 6, y0 - 6, n_inside * c + 12, n_inside * c + 12, "none", k.ENVELOPE["stroke"], 10, 1.4, "6 4"))
  body.append(k.text(x0 - 4, y0 - 12, "item boundary · LD-SDA", 11, k.ENVELOPE["text"], 600))
  for i, a in enumerate(order):
    for j, b in enumerate(order):
      x, y = x0 + j * c, y0 + i * c
      if i == j:
        st = rv.style_of(a)
        chip, title = node_label(a)
        body.append(k.rect(x + 3, y + 3, c - 6, c - 6, st.get("chip", k.INK2), None, 8))
        lines = k.wrap(title, c - 14, 10.5, 600)[:3]
        ty = y + c / 2 + 4 - (len(lines) - 1) * 6.5 + (7 if chip else 0)
        if chip:
          body.append(k.text(x + c / 2, y + 17, chip, 10, "#FFFFFF", 700, "middle", True))
        for li, ln in enumerate(lines):
          body.append(k.text(x + c / 2, ty + li * 13, ln, 10.5, "#FFFFFF", 600, "middle"))
        continue
      entries = cells.get((a.path, b.path), [])
      if not entries:
        body.append(k.rect(x + 3, y + 3, c - 6, c - 6, k.WASH, k.HAIR, 6, 1))
        continue
      cls = min((e[1] for e in entries), key=rv.CLASS_PRIORITY.index)
      st = k.EDGE[cls]
      body.append(k.rect(x + 3, y + 3, c - 6, c - 6, SOFT[cls], st["color"], 6, 1.6, st["dash"]))
      labels = sorted({e[0] for e in entries}, key=lambda s: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)])
      for li, lab in enumerate(labels[:3]):
        body.append(k.text(x + c / 2, y + c / 2 + 4 + (li - (min(len(labels), 3) - 1) / 2) * 14, lab, 10.5,
                           st["color"], 700, "middle", True))
  y = y0 + n * c + 28
  body.append(k.text(40, y, "Read a row across: the row element sends to the column element over the interfaces in the cell "
                     "(IF-nn of WP-S-03 §3.3; CAN = bus attachment, both ways; no IF = a model link with no IF number). "
                     "Diagonal: the elements.", 11.5, k.INK2))
  legend_y = y + 18
  items, lx = [], 40
  for cls in ("actuation", "ffi", "boot", "sensing", "power", "network", "bus"):
    st = k.EDGE[cls]
    items.append(k.rect(lx, legend_y + 22, 18, 14, SOFT[cls], st["color"], 4, 1.6, st["dash"]))
    items.append(k.text(lx + 24, legend_y + 33, st["label"], 11, k.INK2))
    lx += 34 + k.text_w(st["label"], 11)
  body += rv.footer(w, legend_y, items)
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body)


# ---------------------------------------------------------------- V-09 VCRM

METHODS = [("A", "Analysis"), ("LOG", "Analysis"), ("SIM", "Analysis"), ("R", "Inspection"), ("Rec", "Inspection"),
           ("DEM", "Demonstration"), ("T-SIL", "Test"), ("T-HIL", "Test"), ("FI", "Test"), ("PT", "Test"),
           ("T-VEH", "Test")]
METHOD_TEXT = {"A": "analysis", "LOG": "drive-log analysis", "SIM": "simulation", "R": "review", "Rec": "operational record",
               "DEM": "demonstration", "T-SIL": "software test", "T-HIL": "bench test", "FI": "fault injection",
               "PT": "fuzzing, penetration test", "T-VEH": "vehicle test"}
# WP-S-07 §3 writes its own codes; they fold into the columns above
CSR_CODES = {"UT": "T-SIL", "HIL": "T-HIL", "FZ": "PT", "PT": "PT", "BA": "R", "PR": "R", "CM": "R"}
LEVELS = [("SYS.4", ("VS-SI", "VS-FI")), ("SYS.5", ("VS-SQ",)), ("VAL.1", ("VS-VAL",)), ("below", None)]
GROUPS = {"SYS": "functional, non-safety (WP-S-01)", "TSR-1": "lateral envelope", "TSR-2": "longitudinal envelope",
          "TSR-3": "engagement, override", "TSR-4": "communication integrity", "TSR-5": "safety-MCU platform",
          "TSR-6": "host monitoring, DM, HMI", "TSR-7": "PCS, harness", "TSR-8": "production, operation",
          "CSR": "cybersecurity (WP-S-07)"}


def methods_of(r: sysml_lite.Requirement) -> list[str]:
  """The Verif attribute as method codes. Review variants (R-SW, R-CFG …) are R; the WP-S-07 codes fold in through
  CSR_CODES (audits and procedure reviews are R); records of production and operation (maintenance log, release
  record …) are Rec."""
  out = []
  for tok in re.split(r"[,;]", re.sub(r"\s*\([^)]*\)", "", str(r.values.get("verifMethod") or ""))):
    t = tok.strip()
    if not t:
      continue
    code = ("T-SIL" if t.startswith("T-SIL") else CSR_CODES[t] if t in CSR_CODES else t if t in METHOD_TEXT else
            "R" if re.match(r"^R(-[A-Z]+)?\b", t) else "Rec")
    if code not in out:
      out.append(code)
  return out


def group_of(short: str) -> str | None:
  if short.startswith("SYS-"):
    return "SYS"
  if short.startswith("CSR-"):
    return "CSR"
  if short.startswith("TSR-"):
    return "TSR-" + short[4]
  return None


def level_of(case: str) -> str:
  for lv, prefixes in LEVELS:
    if prefixes and case.startswith(prefixes):
      return lv
  return "below"


def vcrm_rows(m: sysml_lite.Model) -> list[sysml_lite.Requirement]:
  reqs = [r for r in m.requirements.values() if group_of(r.short)]
  return sorted(reqs, key=lambda r: (list(GROUPS).index(group_of(r.short)),
                                     [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", r.short)]))


def render_vcrm(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  view = m.views[vid]
  w = spec["width"]
  reqs = vcrm_rows(m)
  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  x0, cw, rh, top = 300, 62, 38, 176
  ncols = len(METHODS) + len(LEVELS) + 1
  # NASA method bands and the coverage band
  bands, start = [], 0
  for i, (_, nasa) in enumerate(METHODS + [(None, None)]):
    if i == len(METHODS) or (i and nasa != METHODS[start][1]):
      bands.append((METHODS[start][1], start, i))
      start = i
  for name, a, b in bands:
    used = any(c in methods_of(r) for r in reqs for c, nm in METHODS[a:b])
    body.append(k.rect(x0 + a * cw + 3, top - 76, (b - a) * cw - 6, 22, k.INK if used else "#FFFFFF", None if used else k.FAINT, 6))
    body.append(k.text(x0 + (a + b) / 2 * cw, top - 61, name if used or b - a > 1 else "none", 11,
                       "#FFFFFF" if used else k.MUTED, 700, "middle"))
  cx = x0 + len(METHODS) * cw
  body.append(k.rect(cx + 3, top - 76, (len(LEVELS) + 1) * cw - 6, 22, BLUE, None, 6))
  body.append(k.text(cx + (len(LEVELS) + 1) * cw / 2, top - 61, "Verified by a case («verify»)", 11, "#FFFFFF", 700, "middle"))
  heads = [c for c, _ in METHODS] + [lv if lv != "below" else "SW/HW" for lv, _ in LEVELS] + ["result"]
  for j, h in enumerate(heads):
    body.append(k.text(x0 + j * cw + cw / 2, top - 22, h, 11, k.INK2, 600, "middle"))
  y = top - 8
  for gi, g in enumerate(GROUPS):
    rs = [r for r in reqs if group_of(r.short) == g]
    if not rs:
      continue
    body.append(f'<line x1="40" y1="{k.f(y)}" x2="{k.f(w - 40)}" y2="{k.f(y)}" stroke="{k.HAIR}"/>')
    title = "SYS" if g == "SYS" else "CSR" if g == "CSR" else g + "xx"
    body.append(k.text(40, y + 17, title, 12.5, k.INK, 700))
    body.append(k.text(40, y + 31, f"{GROUPS[g]} · {len(rs)}", 10.5, k.MUTED))
    cnt = Counter(c for r in rs for c in methods_of(r))
    lv_cnt = Counter(lv for r in rs for lv in {level_of(v) for v in r.verified_by})
    vals = [cnt[c] for c, _ in METHODS] + [lv_cnt[lv] for lv, _ in LEVELS] + [0]
    for j, v in enumerate(vals):
      x = x0 + j * cw
      if j < len(METHODS):
        a = min(v / len(rs), 1)
        fill = f"rgba(194,65,12,{0.08 + 0.5 * a:.2f})" if v else "#FFFFFF"
        txt = str(v) if v else "·"
        col = k.INK if v else k.FAINT
      elif j < ncols - 1:
        a = v / len(rs)
        fill = f"rgba(37,99,235,{0.08 + 0.5 * a:.2f})" if v else RED_BG
        txt, col = str(v), k.INK if v else RED
      else:
        fill, txt, col = "#FFFFFF", "—", k.FAINT
      body.append(k.rect(x + 3, y + 5, cw - 6, rh - 10, fill, None, 5))
      body.append(k.text(x + cw / 2, y + rh / 2 + 4, txt, 12, col, 600 if txt not in ("·", "—") else 400, "middle"))
    y += rh
  body.append(f'<line x1="40" y1="{k.f(y)}" x2="{k.f(w - 40)}" y2="{k.f(y)}" stroke="{k.HAIR}"/>')
  verified = sum(1 for r in reqs if r.verified_by)
  body.append(k.text(40, y + 26, f"{len(reqs)} requirements · {verified} verified by at least one case · {len(reqs) - verified} by "
                     "none · no case has a result yet (specified, not run) · one row per requirement: generated/vcrm.md",
                     12, k.INK, 600))
  legend_y = y + 42
  codes = " · ".join(f"{c} {METHOD_TEXT[c]}" for c, _ in METHODS)
  items = [k.text(40, legend_y + 30, codes, 11, k.INK2),
           k.text(40, legend_y + 50, "SYS.4 integration (VS-SI, VS-FI) · SYS.5 system verification (VS-SQ) · VAL.1 validation (VS-VAL) "
                  "· SW/HW cases below system level · a requirement counts once per level", 11, k.INK2)]
  body += rv.footer(w, legend_y + 14, items)
  return k.svg_doc(w, legend_y + 106, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body)


def vcrm_page(m: sysml_lite.Model) -> str:
  reqs = vcrm_rows(m)
  out = ["<!-- Generated from assurance/models/sysml by tools/render_views.py; do not edit by hand. -->", "",
         "# Verification cross-reference matrix (VCRM)", "",
         "One row per system-level requirement of the SysML model: SYS (WP-S-01), TSR (WP-S-02) and CSR (WP-S-07). "
         "Method is the requirement's Verif attribute; the NASA column groups it as analysis (A), inspection (I), "
         "demonstration (D) or test (T). The cases are the verification cases that «verify» it in the model, by level. "
         "No case has been run, so no result is recorded. Summary: [V-09](fig-sysml-v09-vcrm.svg).", ""]
  nasa = {c: n[0] for c, n in METHODS}
  for g, gname in GROUPS.items():
    rs = [r for r in reqs if group_of(r.short) == g]
    if not rs:
      continue
    title = "SYS" if g == "SYS" else "CSR" if g == "CSR" else g + "xx"
    out += [f"## {title}: {gname}", "", "| Requirement | Integrity | Method | NASA | SYS.4 | SYS.5 | VAL.1 | SW/HW | Result |",
            "|---|---|---|---|---|---|---|---|---|"]
    for r in rs:
      ms = methods_of(r)
      by = {lv: sorted((v for v in r.verified_by if level_of(v) == lv),
                       key=lambda s: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]) for lv, _ in LEVELS}
      cell = lambda vs: ", ".join(vs) if vs else "—"
      out.append(f"| {r.short} | {r.values.get('asil') or '—'} | {', '.join(ms) or '—'} | "
                 f"{''.join(sorted({nasa[c] for c in ms}, key='AIDT'.index)) or '—'} | {cell(by['SYS.4'])} | "
                 f"{cell(by['SYS.5'])} | {cell(by['VAL.1'])} | {cell(by['below'])} | none |")
    out.append("")
  return "\n".join(out)


def extra_outputs(m: sysml_lite.Model) -> dict[str, str]:
  return {"vcrm.md": vcrm_page(m)}


RENDERERS = {"n2": render_n2, "vcrm": render_vcrm}
