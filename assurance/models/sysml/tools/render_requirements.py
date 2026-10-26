"""Requirement views of the SysML model: V-05 thread, V-06 requirement diagram, V-07 satisfy/verify matrix.

Called by render_views.render_all for layout entries of kind "thread", "requirements" and "reqmatrix". Everything
drawn comes from the model (requirements, derivations, satisfy, verify, mechanisms); layout.toml only names the
requirement or function a view is about and the canvas width.
"""
from __future__ import annotations

import re

import render_views as rv
import svgkit as k
import sysml_lite

TEAL, BLUE, RED, RED_BG, VIOLET = "#0F766E", "#2563EB", "#D2553F", "#FEF2F2", "#7C3AED"
BLUE_LINE = "#93C5FD"
NEED = {"chip": "#0E7490", "fill": "#ECFEFF", "stroke": "#0891B2"}   # stakeholder needs
USE = {"chip": "#4338CA", "fill": "#EEF2FF", "stroke": "#818CF8"}    # use cases and functions
REQ_STROKE = "#475569"
ENV = k.ENVELOPE
KIND_ORDER = ("SN", "SG", "FSR", "TSR", "SYS", "CSR")
MARKERS = "".join([k.arrow_marker("rq-teal", TEAL), k.arrow_marker("rq-blue", BLUE), k.arrow_marker("rq-or", "#C2410C"),
                   k.arrow_marker("rq-ink", k.INK2), k.arrow_marker("rq-mut", k.MUTED)])


def sort_key(ident: str):
  return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", ident)]


def req_key(short: str):
  return (KIND_ORDER.index(short.split("-")[0]), sort_key(short))


def label(m: sysml_lite.Model, path: str) -> tuple[str, str]:
  """(chip, title) of an element."""
  e = m.elements[path]
  title = rv.TITLES.get(e.name) or ("" if e.short and e.short.split(".")[-1] == e.name else e.name)
  return (e.short or "", title)


def edge(pts, color, width=1.4, dash=None, marker=None) -> str:
  d = f' stroke-dasharray="{dash}"' if dash else ""
  mk = f' marker-end="url(#{marker})"' if marker else ""
  return f'<path d="{k.rounded_path(pts, 7)}" fill="none" stroke="{color}" stroke-width="{width}"{d}{mk}/>'


def tag(x, y, text, color) -> list[str]:
  tw = k.text_w(text, 9.5, 600, True) + 10
  return [k.rect(x - tw / 2, y - 9, tw, 16, "#FFFFFF", None, 4), k.text(x, y + 3, text, 9.5, color, 600, "middle", True)]


def card(x, y, w, h, title, chip=None, chip_color=k.INK2, fill="#FFFFFF", stroke=k.FAINT, lines=(), stereo=None, sw=1.3,
         mono_chip=True) -> list[str]:
  out = [k.rect(x, y, w, h, fill, stroke, 8, sw, None, ' filter="url(#lift)"')]
  ty = y + 21
  if stereo:
    out.append(k.text(x + 12, y + 16, k.clip(stereo, w - 24, 9.5, 400, True), 9.5, k.MUTED, 400, None, True))
    ty = y + 33
  cx = x + 12
  if chip:
    p, pw = k.pill(cx, ty - 13, chip, chip_color, size=9.5, mono=mono_chip)
    out.append(p)
    cx += pw + 7
  out.append(k.text(cx, ty, k.clip(title, x + w - cx - 10, 12, 600), 12, k.INK, 600))
  for i, ln in enumerate(lines):
    out.append(k.text(x + 12, ty + 17 + i * 14, k.clip(ln, w - 24, 10.5), 10.5, k.MUTED))
  return out


def column_title(x, y, text) -> str:
  return k.text(x, y, text, 10.5, k.MUTED, 700, extra=' letter-spacing="1.1"')


def req_style(short: str) -> tuple[str, str, str]:
  """(chip colour, fill, stroke) by requirement kind: safety requirements in the envelope colours."""
  kind = short.split("-")[0]
  if kind == "SN":
    return NEED["chip"], NEED["fill"], NEED["stroke"]
  if kind in ("SG", "FSR", "TSR"):
    return ENV["chip"], ENV["fill"], ENV["stroke"]
  if kind == "CSR":
    return k.UNTRUSTED["chip"], "#FFFFFF", k.UNTRUSTED["stroke"]
  return "#334155", "#FFFFFF", REQ_STROKE


def text_of(r: sysml_lite.Requirement) -> str:
  return r.doc


# ---------------------------------------------------------------- V-05 thread

def render_thread(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  view = m.views[vid]
  r = m.requirements[spec["requirement"]]
  w = spec["width"]
  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  # ancestors, nearest first
  levels: list[list[str]] = []
  frontier = list(r.derived_from)
  seen: set[str] = set()
  while frontier:
    frontier = sorted({f for f in frontier if f not in seen}, key=req_key)
    if not frontier:
      break
    levels.append(frontier)
    seen.update(frontier)
    frontier = [p for f in frontier for p in m.requirements[f].derived_from]
  mechs = sorted((me for me in m.mechanisms.values() if r.short in me.tsr), key=lambda me: int(me.short[3:]))
  cases = sorted(r.verified_by, key=sort_key)
  cols = {"concept": 40, "system": 360, "arch": 752, "verif": 1074}
  top = 130
  body.append(column_title(cols["concept"], 114, "DERIVED FROM · «derivation»"))
  body.append(column_title(cols["system"], 114, "REQUIREMENT"))
  body.append(column_title(cols["arch"], 114, "SATISFIED BY · «satisfy»"))
  body.append(column_title(cols["verif"], 114, "VERIFIED BY · «verify»"))
  # requirement card
  chip, fill, stroke = req_style(r.short)
  lines = k.wrap(text_of(r), 296, 10.5)[:7]
  named = {"asil": "ASIL", "timing": "timing", "verifMethod": "verification", "mechanism": "mechanism class"}
  lines += [f"{named[a]}: {r.values[a]}" for a in named if r.values.get(a)]
  rh = 54 + 14 * len(lines)
  body += card(cols["system"], top, 310, rh, "", r.short, chip, fill, stroke, lines,
               f"«requirement» {r.definition}", 2)
  ry = top + 30
  # ancestors: the nearest parents first, then theirs; arrows run from the derived requirement to its originals
  cx0 = cols["concept"] + 16
  y = top
  anc_y: dict[str, float] = {}
  for lvl in levels:
    for a in lvl:
      ra = m.requirements[a]
      c, f_, s_ = req_style(a)
      meta = " · ".join(x for x in (f"ASIL {ra.values.get('asil')}" if ra.values.get("asil") else "", ra.values.get("workProduct", "")) if x)
      body += card(cx0, y, 280, 54, ra.doc, a, c, f_, s_, [meta])
      anc_y[a] = y + 27
      y += 64
    y += 10
  concept_bottom = y
  if levels:
    for a in levels[0]:
      body.append(edge([(cols["system"], ry), (cols["system"] - 22, ry), (cols["system"] - 22, anc_y[a]), (cx0 + 280, anc_y[a])],
                       ENV["stroke"], 1.3, None, "rq-or"))
    for i in range(1, len(levels)):
      for a in levels[i]:
        kids = [c for c in levels[i - 1] if a in m.requirements[c].derived_from]
        for kid in kids:
          body.append(edge([(cx0, anc_y[kid]), (cx0 - 10, anc_y[kid]), (cx0 - 10, anc_y[a]), (cx0, anc_y[a])],
                           ENV["stroke"], 1.1, None, "rq-or"))
  else:
    body.append(k.text(cols["concept"], top + 20, "no parent requirement in the model", 11, k.MUTED))
  # satisfied by, then the mechanisms that cite the requirement
  y = top
  sat_y = []
  for p in r.satisfied_by:
    e = m.elements[p]
    st = rv.style_of(e)
    ch, title = label(m, p)
    body += card(cols["arch"], y, 300, 58, title or ch, ch or None, st["chip"], st["fill"], st["stroke"],
                 [f"{e.definition or ''} · {k.INTEGRITY_LABEL.get(e.integrity() or '', e.integrity() or '')}"], "«part»")
    sat_y.append(y + 35)
    y += 70
  if sat_y:
    body.append(edge([(cols["arch"], sat_y[0]), (cols["arch"] - 14, sat_y[0]), (cols["arch"] - 14, ry), (cols["system"] + 312, ry)],
                     TEAL, 1.6, "6 4", "rq-teal"))
    for sy in sat_y[1:]:
      body.append(edge([(cols["arch"], sy), (cols["arch"] - 14, sy), (cols["arch"] - 14, ry)], TEAL, 1.6, "6 4"))
    body += tag((cols["system"] + 312 + cols["arch"] - 14) / 2, ry - 12, "«satisfy»", TEAL)
  else:
    body.append(k.text(cols["arch"], top + 20, "no satisfying element", 11, RED, 600))
  if mechs:
    y += 18
    body.append(k.text(cols["arch"], y, "SAFETY MECHANISMS THAT CITE IT (WP-S-03 §6)", 9.5, k.MUTED, 700, extra=' letter-spacing="1"'))
    y += 10
  for me in mechs:
    perf = ", ".join(label(m, p)[0] or label(m, p)[1] for p in me.performers)
    body += card(cols["arch"], y, 300, 72, me.name or me.short, me.short, ENV["chip"], "#FFFFFF", ENV["stroke"],
                 [f"performed by {perf}", f"DC target {me.dc_target}"], "«action» SafetyMechanism · tsr")
    y += 84
  arch_bottom = y
  # verification cases; the verify arrow runs under the architecture column into the requirement's bottom edge
  y = top
  vy = []
  for cid in cases:
    v = m.verifications[cid]
    body += card(cols["verif"], y, 270, 54, v.doc or cid, cid, BLUE, "#FFFFFF", BLUE_LINE,
                 [f"{v.values.get('spec', '')} · specified"])
    vy.append(y + 27)
    y += 64
  verif_bottom = y
  if vy:
    lane = max(arch_bottom, top + rh) + 18
    bus = cols["verif"] - 16
    for yy in vy:
      body.append(edge([(cols["verif"], yy), (bus, yy)], BLUE, 1.4, "6 4"))
    body.append(edge([(bus, min(vy)), (bus, lane), (cols["system"] + 155, lane), (cols["system"] + 155, top + rh + 2)],
                     BLUE, 1.6, "6 4", "rq-blue"))
    body += tag((bus + cols["system"] + 155) / 2, lane, f"«verify» × {len(vy)}", BLUE)
    verif_bottom = max(verif_bottom, lane + 12)
  else:
    body.append(k.text(cols["verif"], top + 20, "no verification case names it", 11, RED, 600))
  # status column
  sx = w - 152
  body.append(k.rect(sx, top, 120, 230, k.WASH, k.HAIR, 8))
  body.append(k.text(sx + 12, top + 22, "THREAD", 10, k.MUTED, 700, extra=' letter-spacing="1.1"'))
  rows = [("derived", f"{sum(len(x) for x in levels)} ancestors", TEAL if levels else RED),
          ("satisfied", f"{len(r.satisfied_by)} element(s)", TEAL if r.satisfied_by else RED),
          ("mechanisms", f"{len(mechs)} cite it", TEAL if mechs else k.FAINT),
          ("verified", f"{len(cases)} case(s)", BLUE if cases else RED),
          ("run", "not recorded", "#D97706")]
  for i, (a, b, c) in enumerate(rows):
    yy = top + 50 + i * 36
    body.append(f'<circle cx="{sx + 16}" cy="{yy - 4}" r="5" fill="{c}"/>')
    body.append(k.text(sx + 28, yy, a, 11, k.INK, 600))
    body.append(k.text(sx + 28, yy + 14, b, 10, k.MUTED))
  h_content = max(top + rh, arch_bottom, verif_bottom, top + 240, concept_bottom)
  note_y = h_content + 20
  body.append(k.text(40, note_y, "Every arrow is a model relationship: #derivation connections from the trace data and WP-S-01 §1.3, satisfy from the "
                     "allocation, perform statements of the mechanisms, verify from the test specifications. Execution results are "
                     "not in the model.", 11, k.MUTED))
  legend_y = note_y + 24
  items = [edge([(40, legend_y + 30), (66, legend_y + 30)], TEAL, 2, "6 4"), k.text(74, legend_y + 34, "«satisfy»", 11, k.INK2),
           edge([(150, legend_y + 30), (176, legend_y + 30)], BLUE, 2, "6 4"), k.text(184, legend_y + 34, "«verify»", 11, k.INK2),
           edge([(256, legend_y + 30), (282, legend_y + 30)], ENV["stroke"], 2), k.text(290, legend_y + 34, "«derivation»", 11, k.INK2)]
  body += rv.footer(w, legend_y, items)
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body, MARKERS)


# ---------------------------------------------------------------- V-06 requirement diagram

def sysml_frame(x, y, w, h, kind: str, package: str, name: str) -> list[str]:
  """A SysML diagram frame with its name tab: kind [package] name, as in the SysML v2 graphical notation."""
  label = f"{kind} [{package}] {name}"
  tw = k.text_w(label, 11, 600) + 26
  return [k.rect(x, y, w, h, "none", k.FAINT, 4, 1.2),
          f'<path d="M{k.f(x)} {k.f(y)}h{k.f(tw)}v12l-10 10h{k.f(-(tw - 10))}z" fill="#F8FAFC" stroke="{k.FAINT}" stroke-width="1.2"/>',
          k.text(x + 10, y + 15, label, 11, k.INK2, 600)]


def render_requirement_diagram(m: sysml_lite.Model, vid: str, spec: dict, digest: str):
  """One SysML requirement diagram per function: its system requirements with the needs they refine, the elements
  that satisfy them and the cases that verify them. With `functions` in the layout, one figure per function."""
  if "functions" in spec:
    out = {}
    for fn in spec["functions"]:  # an entry "F-06/F-07" draws functions that share their requirements together
      title = " and ".join(m.functions[f].doc.split(" (")[0].lower() for f in fn.split("/"))
      one = {**{k_: v for k_, v in spec.items() if k_ != "functions"}, "function": fn,
             "title": f"Requirement diagram · {fn} {title}"}
      out[spec["file"].format(f=fn.lower().replace("-", "").replace("/", ""))] = render_requirement_diagram(m, vid, one, digest)
    return out
  view = m.views[vid]
  fn = spec["function"]
  w = spec["width"]
  fns = fn.split("/")
  reqs = sorted((r for r in m.requirements.values() if set(fns) & set(str(r.values.get("functionId", "")).split(", "))),
                key=lambda r: sort_key(r.short))
  elems: list[str] = []
  for r in reqs:
    for p in r.satisfied_by:
      if p not in elems:
        elems.append(p)
  cases = sorted({c for r in reqs for c in r.verified_by}, key=sort_key)
  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  top, rh, gap = 154, 102, 12
  ex, rx, cx = 40, 340, 980
  rw = 520
  body.append(column_title(ex, 138, "SATISFIED BY · «part»"))
  body.append(column_title(rx, 138, f"REQUIREMENTS · {fn} · «requirement»"))
  body.append(column_title(cx, 138, "VERIFIED BY · «verification»"))
  ry = {}
  for i, r in enumerate(reqs):
    y = top + i * (rh + gap)
    gap_ = not r.verified_by
    attrs = f"type {r.values.get('reqType', '')} · verif {r.values.get('verifMethod', '')} · target {r.values.get('target', '')}"
    needs = [p for p in r.derived_from if p.startswith("SN-")]
    derive = f"«deriveReqt» from {', '.join(needs)}: {m.requirements[needs[0]].doc}" if needs else "derived from no need"
    txt = k.wrap(r.doc, rw - 110, 11.5, 600)
    txt = txt[:2] if len(txt) <= 2 else [txt[0], k.clip(txt[1] + " " + " ".join(txt[2:]), rw - 110, 11.5, 600)]
    body += card(rx, y, rw, rh, txt[0], r.short, "#334155", "#FFFFFF", RED if gap_ else REQ_STROKE,
                 ([txt[1]] if len(txt) > 1 else [""]) + [attrs, derive],
                 f"«requirement» {r.definition}", 1.8 if gap_ else 1.3)
    if gap_:
      p, _ = k.pill(rx + rw - 12, y + 7, "no verifier", RED, size=9, anchor="end")
      body.append(p)
    ry[r.short] = y + 36
  n = len(reqs)
  total_h = n * (rh + gap)
  # elements, spread over the requirement column height
  ey = {}
  step = max(70, total_h / max(len(elems), 1))
  for i, p in enumerate(elems):
    e = m.elements[p]
    st = rv.style_of(e)
    ch, title = label(m, p)
    y = top + i * step
    body += card(ex, y, 220, 58, title, ch or None, st["chip"], st["fill"], st["stroke"],
                 [rv.k.INTEGRITY_LABEL.get(e.integrity() or "", e.integrity() or "")], "«part»")
    ey[p] = y + 36
  for r in reqs:
    for j, p in enumerate(r.satisfied_by):
      xm = 262 + 12 * elems.index(p)
      body.append(edge([(ex + 220, ey[p]), (xm, ey[p]), (xm, ry[r.short] + 6 * j - 4), (rx, ry[r.short] + 6 * j - 4)],
                       TEAL, 1.2, "5 4", "rq-teal"))
  body += tag(300, 148, "«satisfy»", TEAL)
  # cases
  cy = {}
  cstep = max(100, total_h / max(len(cases), 1))
  for i, c in enumerate(cases):
    v = m.verifications[c]
    y = top + i * cstep
    names = [r.short for r in reqs if c in r.verified_by]
    body += card(cx, y, 300, 72, v.doc or c, c, BLUE, "#FFFFFF", BLUE_LINE,
                 [v.values.get("spec", ""), f"verifies {', '.join(names)}"], "«verification»")
    cy[c] = y + 36
  bus = {c: rx + rw + 20 + 14 * i for i, c in enumerate(cases)}
  for r in reqs:
    for j, c in enumerate(r.verified_by):
      off = 6 * j - 3
      body.append(edge([(cx, cy[c]), (bus[c], cy[c]), (bus[c], ry[r.short] + off), (rx + rw + 2, ry[r.short] + off)],
                       BLUE, 1.2, "5 4", "rq-blue"))
  body += tag(rx + rw + 40, 148, "«verify»", BLUE)
  bottom = top + max(total_h, len(elems) * step, len(cases) * cstep) + 10
  missing = [r.short for r in reqs if not r.verified_by]
  if missing:
    body.append(k.rect(cx, bottom - 120, 300, 100, RED_BG, "#FCA5A5", 8))
    body.append(k.text(cx + 14, bottom - 96, "Not verified by any case (R4 report)", 12, "#991B1B", 700))
    for i, ln in enumerate(k.wrap(", ".join(missing) + ". Add a case to a test specification, or record why none is needed.", 270, 11)[:4]):
      body.append(k.text(cx + 14, bottom - 76 + i * 15, ln, 11, "#7F1D1D"))
  body += sysml_frame(24, 100, w - 48, bottom - 92, "req", "LionDriverRequirements",
                      " / ".join(f"{f} {m.functions[f].doc.split(' (')[0]}" for f in fns))
  legend_y = bottom + 18
  items = [edge([(40, legend_y + 30), (66, legend_y + 30)], TEAL, 2, "5 4"), k.text(74, legend_y + 34, "«satisfy»", 11, k.INK2),
           edge([(150, legend_y + 30), (176, legend_y + 30)], BLUE, 2, "5 4"), k.text(184, legend_y + 34, "«verify» (specified, not run)", 11, k.INK2),
           k.rect(370, legend_y + 23, 22, 14, RED_BG, RED, 3), k.text(400, legend_y + 34, "requirement without a verification case", 11, k.INK2)]
  body += rv.footer(w, legend_y, items)
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body, MARKERS)


# ---------------------------------------------------------------- V-07 matrix

def render_requirement_matrix(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  view = m.views[vid]
  w = spec["width"]
  reqs = sorted((r for r in m.requirements.values() if r.short.startswith(spec.get("requirements", "SYS") + "-")), key=lambda r: sort_key(r.short))
  cols: list[str] = []
  for e in m.root.walk():
    if any(e.path in r.satisfied_by for r in reqs):
      cols.append(e.path)
  groups: dict[str, list] = {}
  for r in reqs:
    groups.setdefault(str(r.values.get("functionId", "")), []).append(r)
  rh, top = 21, 210
  x0, cw = 290, 46
  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  for j, p in enumerate(cols):
    cxx = x0 + j * cw + cw / 2
    ch, title = label(m, p)
    body.append(f'<text transform="translate({k.f(cxx + 4)},{top - 14}) rotate(-55)" font-size="11" fill="{k.INK}" '
                f'font-weight="600">{k.escape(title or ch)}</text>')
  body.append(column_title(x0, 112, "SATISFIED BY («satisfy» in the model)"))
  vx = x0 + len(cols) * cw + 28
  body.append(column_title(vx, 112, "VERIFIED BY («verify»)"))
  chk = w - 160
  body.append(column_title(chk, 112, "COVERAGE"))
  y = top
  gaps = 0
  for gi, (fn, rs) in enumerate(groups.items()):
    body.append(k.rect(40, y - 2, w - 80, len(rs) * rh + 4, k.WASH if gi % 2 == 0 else "#FFFFFF", None, 4))
    body.append(k.text(48, y + 15, fn, 11.5, k.INK, 700))
    for r in rs:
      body.append(k.text(132, y + 15, r.short, 11, k.INK2, 600, None, True))
      for j, p in enumerate(cols):
        cxx = x0 + j * cw + cw / 2
        body.append(f'<line x1="{k.f(cxx)}" y1="{k.f(y)}" x2="{k.f(cxx)}" y2="{k.f(y + rh)}" stroke="{k.HAIR}"/>')
        if p in r.satisfied_by:
          body.append(f'<circle cx="{k.f(cxx)}" cy="{k.f(y + rh / 2)}" r="5.5" fill="{TEAL}"/>')
      xx = vx
      for c in sorted(r.verified_by, key=sort_key):
        p_, pw = k.pill(xx, y + 2, c.replace("VS-", ""), "#FFFFFF", BLUE, 16, 9.5, 700, BLUE_LINE, mono=True)
        if xx + pw > chk - 10:
          body.append(k.text(xx, y + 15, "…", 11, BLUE, 700))
          break
        body.append(p_)
        xx += pw + 4
      if r.verified_by:
        body.append(k.text(chk, y + 15, "✓ satisfied · verified", 11, TEAL, 600))
      else:
        gaps += 1
        p_, _ = k.pill(chk, y + 2, "no verifier", RED, size=9)
        body.append(p_)
      y += rh
    y += 8
  sat = sum(1 for r in reqs if r.satisfied_by)
  body.append(k.text(40, y + 24, f"{len(reqs)} requirements · {sat} satisfied · {len(reqs) - gaps} verified by at least one case · "
                     f"{gaps} not verified (generated/requirements-coverage.md)", 12, k.INK, 600))
  legend_y = y + 40
  p_, _ = k.pill(150, legend_y + 22, "SQ-16", "#FFFFFF", BLUE, 16, 9.5, 700, BLUE_LINE, mono=True)
  items = [f'<circle cx="48" cy="{k.f(legend_y + 30)}" r="5.5" fill="{TEAL}"/>', k.text(60, legend_y + 34, "satisfies", 11, k.INK2),
           p_, k.text(210, legend_y + 34, "verification case VS-SQ-16 verifies (specified, not run)", 11, k.INK2)]
  body += rv.footer(w, legend_y, items)
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body, MARKERS)


# ---------------------------------------------------------------- V-14 needs and use cases



def needs_of(m: sysml_lite.Model) -> list[sysml_lite.Requirement]:
  return sorted((r for r in m.requirements.values() if r.definition == "StakeholderNeed"), key=lambda r: sort_key(r.short))


def refined_by(m: sysml_lite.Model, need: str) -> list[str]:
  return sorted((r.short for r in m.requirements.values() if need in r.derived_from), key=req_key)


def people_label(pairs: list[tuple[str, str]]) -> str:
  return ", ".join(re.sub(r"(?<!^)([A-Z])", r" \1", d).capitalize() for _, d in pairs)


def render_needs(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  """Stakeholder needs and actors against the use cases, and the functions each use case performs."""
  view = m.views[vid]
  w = spec["width"]
  needs = needs_of(m)
  cases = sorted(m.use_cases.values(), key=lambda u: sort_key(u.short))
  actors = list(dict.fromkeys(d for u in cases for _, d in u.actors))  # in order of first appearance
  fns = sorted(m.functions.values(), key=lambda f: sort_key(f.short))
  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  x0, cw = 470, 70
  rx = x0 + len(cases) * cw + 24
  top = 104
  body.append(column_title(x0, top + 8, "USE CASES · «use case» with subject LD-SDA"))
  body.append(column_title(rx, top + 8, "REFINED BY · «derivation»"))
  hy = top + 22
  for j, u in enumerate(cases):
    cx = x0 + j * cw + cw / 2
    p_, _ = k.pill(cx, hy, u.short, USE["chip"], size=9.5, anchor="middle", mono=True)
    body.append(p_)
    for i, ln in enumerate(k.wrap(u.doc, cw - 6, 9.5)[:3]):
      body.append(k.text(cx, hy + 32 + i * 12, ln, 9.5, k.INK2, 600, "middle"))
  y = hy + 76

  def band(title: str, rows: list[tuple[str, str, str, list[bool], list[str]]], dot: str) -> None:
    nonlocal y
    body.append(column_title(40, y + 4, title))
    y += 14
    for i, (chip, chip_col, text_, marks, right) in enumerate(rows):
      rh = 26
      if i % 2 == 0:
        body.append(k.rect(40, y, w - 80, rh, k.WASH, None, 4))
      if chip:
        p_, pw = k.pill(48, y + 4, chip, chip_col, size=9.5, mono=True)
        body.append(p_)
      else:
        pw = -8
      body.append(k.text(56 + pw, y + 17, k.clip(text_, x0 - 70 - pw, 11), 11, k.INK))
      for j, on in enumerate(marks):
        cx = x0 + j * cw + cw / 2
        body.append(f'<line x1="{k.f(cx)}" y1="{k.f(y)}" x2="{k.f(cx)}" y2="{k.f(y + rh)}" stroke="{k.HAIR}"/>')
        if on:
          body.append(f'<circle cx="{k.f(cx)}" cy="{k.f(y + rh / 2)}" r="6" fill="{dot}"/>')
      xx = rx
      for c in right:
        col = ENV["chip"] if c.startswith("SG-") else "#334155"
        p_, pw2 = k.pill(xx, y + 5, c, "#FFFFFF", col, 16, 9, 700, col, mono=True)
        if xx + pw2 > w - 46:
          body.append(k.text(xx, y + 17, f"+{len(right) - right.index(c)}", 10.5, k.MUTED, 700))
          break
        body.append(p_)
        xx += pw2 + 3
      y += rh
    y += 16

  band("ACTORS · «actor» of the use case",
       [("", "", people_label([("", d)]), [d in dict(u.actors).values() for u in cases], []) for d in actors], k.INK2)
  band("STAKEHOLDER NEEDS · the use case's objective requires the need",
       [(n.short, NEED["chip"], f"{people_label(n.stakeholders)}: {n.doc}", [n.short in u.needs for u in cases],
         refined_by(m, n.short)) for n in needs], NEED["chip"])
  band("FUNCTIONS (WP-C-01 §2.1) · «perform» in the use case",
       [(f.short, USE["chip"], f.doc, [f.short in u.functions for u in cases], []) for f in fns], USE["chip"])
  n_req = sum(len(refined_by(m, n.short)) for n in needs)
  body.append(k.text(40, y + 8, f"{len(needs)} needs · {len(cases)} use cases · {len(fns)} functions · {n_req} refinements to "
                     f"system requirements and safety goals. Every need has a use case and a refining requirement; every "
                     f"function is used (check_model N1-N3).", 12, k.INK, 600))
  legend_y = y + 26
  p1, _ = k.pill(330, legend_y + 22, "SYS-001", "#FFFFFF", "#334155", 16, 9, 700, "#334155", mono=True)
  p2, _ = k.pill(500, legend_y + 22, "SG-05", "#FFFFFF", ENV["chip"], 16, 9, 700, ENV["chip"], mono=True)
  items = [f'<circle cx="48" cy="{k.f(legend_y + 30)}" r="6" fill="{NEED["chip"]}"/>',
           k.text(60, legend_y + 34, "the use case serves the need", 11, k.INK2),
           f'<circle cx="250" cy="{k.f(legend_y + 30)}" r="6" fill="{USE["chip"]}"/>', k.text(262, legend_y + 34, "performs", 11, k.INK2),
           p1, k.text(390, legend_y + 34, "system requirement", 11, k.INK2), p2, k.text(552, legend_y + 34, "safety goal", 11, k.INK2)]
  body += rv.footer(w, legend_y, items)
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body, MARKERS)


# ---------------------------------------------------------------- V-15 end-to-end thread

def render_end_to_end(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  """One stakeholder need from its stakeholder, through the use cases that serve it and the functions they perform,
  and through the requirements that refine it, to the elements that satisfy them and the cases that verify them."""
  view = m.views[vid]
  w = spec["width"]
  need = m.requirements[spec["need"]]
  cases = sorted((u for u in m.use_cases.values() if need.short in u.needs), key=lambda u: sort_key(u.short))
  reqs = [m.requirements[s] for s in refined_by(m, need.short)]
  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  top = 116
  ax, aw = 40, 300            # stakeholder and need
  bx, bw = 400, 300           # use cases / requirements
  cx_, cw_ = 744, 330         # functions / satisfying elements
  dx, dw = 1112, w - 1112 - 40  # performers / verification cases
  # stakeholders and the need
  y = top
  body.append(column_title(ax, y - 6, "STAKEHOLDER · NEED"))
  for name, d in need.stakeholders:
    body.append(k.actor(ax + 20, y + 14, k.INK2, 0.8))
    body.append(k.text(ax + 42, y + 24, people_label([(name, d)]), 12, k.INK, 600))
    body.append(k.text(ax + 42, y + 39, f"«part def» {d} · stakeholder", 10, k.MUTED, 400, None, True))
    y += 50
  lines = k.wrap(need.doc, aw - 24, 11)
  nh = 64 + 15 * len(lines) + 12
  body.append(k.rect(ax, y, aw, nh, NEED["fill"], NEED["stroke"], 8, 1.6, None, ' filter="url(#lift)"'))
  body.append(k.text(ax + 12, y + 16, "«requirement» StakeholderNeed", 9.5, k.MUTED, 400, None, True))
  p_, _ = k.pill(ax + 12, y + 22, need.short, NEED["chip"], size=9.5, mono=True)
  body.append(p_)
  for i, ln in enumerate(lines):
    body.append(k.text(ax + 12, y + 58 + i * 15, ln, 11, k.INK))
  body.append(k.text(ax + 12, y + nh - 10, f"source: {need.values.get('source', '')}", 9.5, k.MUTED))
  need_mid = y + nh / 2
  need_bottom = y + nh

  def chips(x, y0, width, items, style) -> float:
    """Pills left to right, wrapping; returns the height used."""
    xx, yy = x, y0
    for label_, fill, color, stroke in items:
      p_, pw = k.pill(0, 0, label_, fill, color, 18, 9.5, 700, stroke, mono=style)
      if xx + pw > x + width and xx > x:
        xx, yy = x, yy + 22
      p_, pw = k.pill(xx, yy, label_, fill, color, 18, 9.5, 700, stroke, mono=style)
      body.append(p_)
      xx += pw + 4
    return yy - y0 + 22

  # band 1: how the need is used
  y = top
  body.append(column_title(bx, y - 6, "SERVED BY · «use case» objective requires it"))
  body.append(column_title(cx_, y - 6, "PERFORMS · «perform» a function"))
  body.append(column_title(dx, y - 6, "ON THE ELEMENTS THAT PERFORM ITS STEPS"))
  uc_y = []
  n_fn, performers_all = 0, set()
  for u in cases:
    fns = [m.functions[f] for f in u.functions]
    ul = k.wrap(u.goal, bw - 24, 10.5)[:5]
    uh = max(58 + 14 * len(ul) + 18, 70 * len(fns) - 10)
    body += card(bx, y, bw, uh, u.doc, u.short, USE["chip"], USE["fill"], USE["stroke"], ul, "«use case» ItemUseCase", 1.4)
    body.append(k.text(bx + 12, y + uh - 10, f"actors: {people_label(u.actors)}", 9.5, k.MUTED))
    uc_y.append(y + 30)
    fy = y
    for f in fns:
      n_fn += 1
      perf = []
      for st in f.steps:
        for p in st.performers:
          if p not in perf:
            perf.append(p)
      performers_all.update(perf)
      body += card(cx_, fy, cw_, 60, f.doc, f.short, USE["chip"], "#FFFFFF", USE["stroke"],
                   [f"{len(f.steps)} steps, sense to act"], "«action» ItemFunction")
      body.append(edge([(bx + bw, y + 30), (bx + bw + 20, y + 30), (bx + bw + 20, fy + 30), (cx_, fy + 30)], USE["chip"], 1.3, None, "rq-ink"))
      items = []
      for p in perf:
        ch, title = label(m, p)
        st_ = rv.style_of(m.elements[p])
        items.append((ch or title, "#FFFFFF", st_["chip"], st_["stroke"]))
      body.append(edge([(cx_ + cw_, fy + 30), (dx - 6, fy + 30)], k.FAINT, 1.1, "3 3"))
      chips(dx, fy + 6, dw, items, True)
      fy += 70
    y += uh + 14
  band1_bottom = max(y, need_bottom + 10)
  # band 2: how the need is refined
  y = band1_bottom + 26
  body.append(f'<line x1="{bx}" y1="{k.f(y - 14)}" x2="{k.f(w - 40)}" y2="{k.f(y - 14)}" stroke="{k.HAIR}"/>')
  body.append(column_title(bx, y + 6, "REFINED BY · «derivation»"))
  body.append(column_title(cx_, y + 6, "SATISFIED BY · «satisfy»"))
  body.append(column_title(dx, y + 6, "VERIFIED BY · «verify» (specified, not run)"))
  y += 20
  req_y = []
  n_case, no_case, sat_all = set(), [], set()
  for r in reqs:
    chip, fill, stroke = req_style(r.short)
    rl = k.wrap(r.doc, bw - 24, 10.5)[:3]
    extra = " · ".join(x for x in (f"target {r.values['target']}" if r.values.get("target") not in (None, "", "as stated") else "",
                                    f"ASIL {r.values['asil']}" if r.values.get("asil") else "") if x)
    if extra:
      rl.append(k.clip(extra, bw - 24, 10.5))
    rh = 48 + 14 * len(rl)
    body += card(bx, y, bw, rh, "", r.short, chip, fill, stroke, rl, f"«requirement» {r.definition}", 1.3)
    req_y.append(y + 30)
    items = []
    for p in r.satisfied_by:
      ch, title = label(m, p)
      st_ = rv.style_of(m.elements[p])
      items.append((ch or title, "#FFFFFF", st_["chip"], st_["stroke"]))
      sat_all.add(p)
    body.append(edge([(bx + bw, y + 30), (cx_ - 6, y + 30)], TEAL, 1.4, "6 4", "rq-teal"))
    if items:
      chips(cx_, y + 21, cw_, items, True)
    else:
      body.append(k.text(cx_, y + 34, "no satisfying element", 11, RED, 600))
    if r.verified_by:
      chips(dx, y + 21, dw, [(c.replace("VS-", ""), "#FFFFFF", BLUE, BLUE_LINE) for c in sorted(r.verified_by, key=sort_key)], True)
      n_case.update(r.verified_by)
    else:
      p_, _ = k.pill(dx, y + 21, "no test case", RED, size=9.5)
      body.append(p_)
      no_case.append(r.short)
    y += rh + 10
  bottom = y
  # need -> use cases and requirements
  bus = ax + aw + 24
  for yy in uc_y:
    body.append(edge([(bx, yy), (bus, yy), (bus, need_mid), (ax + aw, need_mid)], NEED["chip"], 1.4, None, "rq-ink"))
  for yy in req_y:
    body.append(edge([(bx, yy), (bus, yy), (bus, need_mid)], "#334155", 1.2))
  body.append(edge([(bus, need_mid), (ax + aw, need_mid)], "#334155", 1.4, None, "rq-ink"))
  # summary under the need
  sy = need_bottom + 24
  body.append(k.rect(ax, sy, aw, 200, k.WASH, k.HAIR, 8))
  body.append(k.text(ax + 12, sy + 22, "THREAD", 10, k.MUTED, 700, extra=' letter-spacing="1.1"'))
  rows = [("use cases", f"{len(cases)} serve it", TEAL if cases else RED),
          ("functions", f"{n_fn} performed on {len(performers_all)} elements", TEAL if n_fn else RED),
          ("requirements", f"{len(reqs)} refine it", TEAL if reqs else RED),
          ("satisfied", f"{sum(1 for r in reqs if r.satisfied_by)} of {len(reqs)}, by {len(sat_all)} elements", TEAL),
          ("verified", f"{len(reqs) - len(no_case)} of {len(reqs)}, by {len(n_case)} cases", BLUE if not no_case else "#D97706")]
  for i, (a, b, c) in enumerate(rows):
    yy = sy + 48 + i * 30
    body.append(f'<circle cx="{ax + 16}" cy="{yy - 4}" r="5" fill="{c}"/>')
    body.append(k.text(ax + 28, yy, a, 11, k.INK, 600))
    body.append(k.text(ax + 118, yy, b, 10.5, k.MUTED))
  bottom = max(bottom, sy + 210)
  note_y = bottom + 16
  gap = f" No case verifies {', '.join(no_case)} yet." if no_case else ""
  body.append(k.text(40, note_y, "Every line is a model relationship: the use case's objective requires the need, perform from the use case "
                     "and from each element, #derivation from WP-S-01 §1.3, satisfy from §10.1, verify from the test specifications."
                     + gap, 11, k.MUTED))
  legend_y = note_y + 22
  items = [edge([(40, legend_y + 30), (66, legend_y + 30)], NEED["chip"], 2), k.text(74, legend_y + 34, "objective requires", 11, k.INK2),
           edge([(200, legend_y + 30), (226, legend_y + 30)], USE["chip"], 2), k.text(234, legend_y + 34, "«perform»", 11, k.INK2),
           edge([(320, legend_y + 30), (346, legend_y + 30)], "#334155", 2), k.text(354, legend_y + 34, "«derivation»", 11, k.INK2),
           edge([(450, legend_y + 30), (476, legend_y + 30)], TEAL, 2, "6 4"), k.text(484, legend_y + 34, "«satisfy»", 11, k.INK2),
           k.pill(570, legend_y + 21, "SQ-16", "#FFFFFF", BLUE, 18, 9.5, 700, BLUE_LINE, mono=True)[0],
           k.text(630, legend_y + 34, "«verify»: a case that names the requirement", 11, k.INK2)]
  body += rv.footer(w, legend_y, items)
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body, MARKERS)


RENDERERS = {"thread": render_thread, "requirements": render_requirement_diagram, "reqmatrix": render_requirement_matrix,
             "needs": render_needs, "endtoend": render_end_to_end}


# ---------------------------------------------------------------- V-20 use case diagram

def render_use_cases(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  """SysML use case diagram: the subject LD-SDA as a boundary with one oval per use case, the actors outside it on the
  side the layout names, and an association from each actor to each use case it takes part in."""
  view = m.views[vid]
  w = spec["width"]
  cases = sorted(m.use_cases.values(), key=lambda u: sort_key(u.short))
  side = spec["actor_side"]   # actor definition -> "left" | "right"
  actors = list(dict.fromkeys(d for u in cases for _, d in u.actors))
  missing = [a for a in actors if a not in side]
  if missing:
    raise sysml_lite.ModelError(f"layout.toml {vid}: actor_side has no side for {missing}")
  head = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  boundary, lines, body = [], [], []  # drawn in this order: subject, associations, then ovals and actors
  top = 140
  ow, oh, gap = 420, 46, 14
  ox = w / 2 - ow / 2
  sub_x, sub_w = ox - 60, ow + 120
  sub_h = 40 + len(cases) * (oh + gap) + 10
  boundary.append(k.rect(sub_x, top, sub_w, sub_h, "#FFFFFF", k.INK2, 6, 1.6))
  boundary.append(k.text(sub_x + 14, top + 22, "«subject» LD-SDA · LionDriver Supervised Driving Assistance", 12, k.INK, 700))
  oy = {}
  for i, u in enumerate(cases):
    y = top + 40 + i * (oh + gap)
    body.append(f'<ellipse cx="{k.f(w / 2)}" cy="{k.f(y + oh / 2)}" rx="{k.f(ow / 2)}" ry="{k.f(oh / 2)}" '
                f'fill="{USE["fill"]}" stroke="{USE["stroke"]}" stroke-width="1.4"/>')
    p, pw = k.pill(w / 2 - ow / 2 + 34, y + oh / 2 - 9, u.short, USE["chip"], size=9.5, mono=True)
    body.append(p)
    body.append(k.text(w / 2 - ow / 2 + 44 + pw, y + oh / 2 + 4, k.clip(u.doc, ow - pw - 90, 12, 600), 12, k.INK, 600))
    oy[u.short] = y + oh / 2
  # actors, spread down each side
  pos = {}
  for s, x in (("left", 120), ("right", w - 120)):
    group = [a for a in actors if side[a] == s]
    for j, a in enumerate(group):
      y = top + 40 + (j + 0.5) * (sub_h - 60) / max(len(group), 1) - 20
      body.append(k.actor(x, y, k.INK2, 1.1))
      body.append(k.text(x, y + 62, people_label([("", a)]), 12, k.INK, 700, "middle"))
      body.append(k.text(x, y + 77, "«actor»", 10, k.MUTED, 400, "middle", True))
      pos[a] = (x, y + 22)
  for u in cases:
    for _, a in u.actors:
      ax, ay = pos[a]
      ex = w / 2 - ow / 2 if side[a] == "left" else w / 2 + ow / 2
      sx = ax + 22 if side[a] == "left" else ax - 22
      lines.append(f'<line x1="{k.f(sx)}" y1="{k.f(ay)}" x2="{k.f(ex)}" y2="{k.f(oy[u.short])}" stroke="{k.INK2}" '
                   'stroke-width="1.1" stroke-opacity="0.7"/>')
  body = head + boundary + lines + body
  bottom = top + sub_h + 20
  body += sysml_frame(24, 100, w - 48, bottom - 92, "uc", "LionDriverNeeds", "use cases of LD-SDA")
  n_assoc = sum(len(u.actors) for u in cases)
  body.append(k.text(40, bottom + 24, f"{len(cases)} use cases, {len(actors)} actors, {n_assoc} associations, from WP-S-01 §1.4 "
                     "through the model (LionDriverNeeds). Each use case's objective requires the stakeholder needs it serves "
                     "and it performs functions of WP-C-01 §2.1 (view V-14).", 11.5, k.INK2))
  legend_y = bottom + 40
  items = [k.actor(52, legend_y + 18, k.INK2, 0.5), k.text(66, legend_y + 34, "actor", 11, k.INK2),
           f'<ellipse cx="150" cy="{k.f(legend_y + 30)}" rx="34" ry="11" fill="{USE["fill"]}" stroke="{USE["stroke"]}"/>',
           k.text(192, legend_y + 34, "use case", 11, k.INK2),
           f'<line x1="270" y1="{k.f(legend_y + 30)}" x2="300" y2="{k.f(legend_y + 30)}" stroke="{k.INK2}"/>',
           k.text(308, legend_y + 34, "association: the actor takes part", 11, k.INK2)]
  body += rv.footer(w, legend_y, items)
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body, MARKERS)


RENDERERS["usecases"] = render_use_cases


# ---------------------------------------------------------------- V-22 TSR requirement diagrams

def render_tsr_blocks(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> dict[str, str]:
  """One SysML requirement diagram per TSR block: each TSR with the FSRs it is derived from («deriveReqt», arrows to
  the FSR column), the elements that satisfy it («satisfy»), the safety mechanisms that cite it and the cases that
  verify it («verify»). Blocks too long for one page are split by the ranges in the layout."""
  out = {}
  view = m.views[vid]
  w = spec["width"]
  for g in spec["blocks"]:
    lo, hi = int(g["from"][4:]), int(g["to"][4:])
    reqs = sorted((r for r in m.requirements.values() if r.short.startswith("TSR-") and lo <= int(r.short[4:7]) <= hi),
                  key=lambda r: sort_key(r.short))
    if not reqs:
      raise sysml_lite.ModelError(f"layout.toml {vid}: no TSR between {g['from']} and {g['to']}")
    parents = sorted({p for r in reqs for p in r.derived_from}, key=req_key)
    body = rv.header(w, view, f"TSR requirement diagram · {g['title']}",
                     f"{g['from']}…{g['to']} of WP-S-02 with the FSRs they derive from, the elements that satisfy them, "
                     "the mechanisms that cite them and the cases that verify them", digest)
    top, rh, gap = 156, 74, 8
    fx, fw, tx, tw, cx = 40, 270, 360, 560, 950
    kinds = {}
    for p_ in parents:
      kinds.setdefault(re.match(r"[A-Z]+", p_).group(0), []).append(p_)
    only_fsr = set(kinds) == {"FSR"}
    body.append(column_title(fx, 140, "DERIVED FROM · «requirement» FSR" if only_fsr else "DERIVED FROM · «requirement»"))
    body.append(column_title(tx, 140, "TECHNICAL SAFETY REQUIREMENTS · «requirement»"))
    body.append(column_title(cx, 140, "«satisfy» · MECHANISMS · «verify»"))
    ty = {}
    no_case = []
    for i, r in enumerate(reqs):
      y = top + i * (rh + gap)
      chip, fill, stroke = req_style(r.short)
      txt = k.wrap(r.doc, tw - 110, 11, 600)
      line2 = k.clip(" ".join(txt[1:]), tw - 24, 10.5) if len(txt) > 1 else ""
      attrs = " · ".join(x for x in (f"ASIL {r.values.get('asil')}" if r.values.get("asil") else "",
                                      f"SM {r.values.get('mechanism')}" if r.values.get("mechanism") else "",
                                      str(r.values.get("timing") or "")) if x)
      gap_ = not r.verified_by
      if gap_:
        no_case.append(r.short)
      body += card(tx, y, tw, rh, txt[0] if txt else "", r.short, chip, fill, RED if gap_ else stroke,
                   [line2, k.clip(attrs, tw - 24, 10.5)], None, 1.8 if gap_ else 1.3)
      ty[r.short] = y + rh / 2
      # right side: satisfy elements, mechanisms, verify cases
      rows = [("«satisfy»", [label(m, p)[0] or label(m, p)[1] for p in r.satisfied_by], TEAL, "#F0FDFA"),
              ("SM", [me.short for me in m.mechanisms.values() if r.short in me.tsr], ENV["chip"], ENV["fill"]),
              ("«verify»", [c.replace("VS-", "") for c in sorted(r.verified_by, key=sort_key)], BLUE, "#EFF6FF")]
      yy = y + 8
      for lab, items, col, bg in rows:
        body.append(k.text(cx, yy + 12, lab, 9.5, col, 700, None, True))
        xx = cx + 66
        if not items:
          body.append(k.text(xx, yy + 12, "none" if lab != "«verify»" else "no case", 9.5,
                             RED if lab == "«verify»" else k.FAINT, 600))
        for j, it in enumerate(items):
          p, pw = k.pill(xx, yy + 1, it, bg, col, 15, 8.5, 700, col, mono=True)
          if xx + pw > w - 40:
            body.append(k.text(xx, yy + 12, f"+{len(items) - j}", 9.5, col, 700))
            break
          body.append(p)
          xx += pw + 3
        yy += 20
    # FSR cards spread along the TSR column, with deriveReqt arrows from each TSR to its FSRs
    total = len(reqs) * (rh + gap)
    step = max(52, total / max(len(parents), 1))
    fy = {}
    for i, p in enumerate(parents):
      y = top + i * step
      rp = m.requirements[p]
      c_, f_, s_ = req_style(p)
      body += card(fx, y, fw, 44, rp.doc, p, c_, f_, s_, [], None, 1.2)
      fy[p] = y + 22
    for r in reqs:
      for j, p in enumerate(r.derived_from):
        if p in fy:
          xm = fx + fw + 14 + 4 * (parents.index(p) % 8)
          body.append(edge([(tx, ty[r.short] + 4 * j - 4), (xm, ty[r.short] + 4 * j - 4), (xm, fy[p]), (fx + fw, fy[p])],
                           "#64748B", 1.0, "4 3", "rq-mut"))
    body += tag(fx + fw + 26, 150, "«deriveReqt»", k.MUTED)
    bottom = top + max(total, len(parents) * step) + 4
    body += sysml_frame(24, 100, w - 48, bottom - 92, "req", "LionDriverRequirements",
                        f"{g['from']}…{g['to']} {g['title']}")
    kind_name = {"SG": ("safety goal", "safety goals"), "FSR": ("FSR", "FSRs"), "TSR": ("TSR", "TSRs")}
    src = (f"{len(parents)} FSRs" if only_fsr else
           ", ".join(f"{len(v)} {kind_name.get(k_, (k_, k_))[len(v) != 1]}" for k_, v in sorted(kinds.items(), key=lambda kv: ["SG", "FSR", "TSR"].index(kv[0]) if kv[0] in ("SG", "FSR", "TSR") else 9)))
    note = (f"{len(reqs)} TSRs from {src}; {len(reqs) - len(no_case)} named by a verification case"
            + (f"; no case yet: {', '.join(no_case)}." if no_case else "."))
    for i, ln in enumerate(k.wrap(note, w - 80, 11.5)):
      body.append(k.text(40, bottom + 26 + i * 16, ln, 11.5, k.INK2))
    legend_y = bottom + 26 + 16 * len(k.wrap(note, w - 80, 11.5))
    items = [edge([(40, legend_y + 30), (66, legend_y + 30)], "#64748B", 1.6, "4 3", "rq-mut"),
             k.text(74, legend_y + 34, "«deriveReqt»: the TSR refines the FSR" if only_fsr else
                    "«deriveReqt»: the TSR refines its parent", 11, k.INK2),
             k.pill(330, legend_y + 22, "E-03", "#F0FDFA", TEAL, 15, 8.5, 700, TEAL, mono=True)[0],
             k.text(372, legend_y + 34, "satisfying element", 11, k.INK2),
             k.pill(500, legend_y + 22, "SM-12", ENV["fill"], ENV["chip"], 15, 8.5, 700, ENV["chip"], mono=True)[0],
             k.text(548, legend_y + 34, "safety mechanism that cites it (WP-S-03 §6)", 11, k.INK2),
             k.pill(830, legend_y + 22, "SI-05", "#EFF6FF", BLUE, 15, 8.5, 700, BLUE, mono=True)[0],
             k.text(872, legend_y + 34, "verification case VS-SI-05 (specified, not run)", 11, k.INK2)]
    body += rv.footer(w, legend_y, items)
    out[spec["file"].format(f=g["key"])] = k.svg_doc(
      w, legend_y + 92, f"{view.short}. TSR requirement diagram {g['from']}…{g['to']} (SysML v2 view {view.name})",
      spec.get("desc", view.doc), body, MARKERS)
  return out


RENDERERS["tsrblocks"] = render_tsr_blocks
