"""Renderers of the architecture views added with the MBSE extension (README §6, OI-10).

  V-10 functional architecture   the functions F-01 to F-09 along their functional chain, each step on the element
                                 that performs it (LionDriverFunctions, perform statements)

  V-03 at phone width            the technical safety architecture stacked top to bottom along the command path
                                 (render_interconnection_phone, from V-03's [phone] layout)

  V-26 safety mechanisms         SM-01 to SM-45 on the elements that perform them and on the interfaces whose TSRs
                                 they implement, top to bottom along the command path, at phone width
  V-27 coverage per goal         per safety goal, the mechanisms behind it (SG -> FSR -> TSR -> SM) by status, and the
                                 FSRs with no mechanism behind them, at phone width

Called by render_views.render_all, which sets `rv` to itself so that TITLES and the shared frame are available.
layout.toml gives the title, subtitle and canvas width only; positions follow from the model.
"""
from __future__ import annotations

import re

import svgkit as k
import sysml_lite

rv = None  # render_views, set by render_all

# ---------------------------------------------------------------- V-10 functional architecture

STAGES = [("sense", "Sense"), ("perceive", "Perceive"), ("plan", "Plan, decide"), ("control", "Control"),
          ("command", "Command path"), ("envelope", "Safety envelope"), ("act", "Act, inform")]


def element_label(e: sysml_lite.Element) -> str:
  title = rv.TITLES.get(e.name, e.name)
  if e.short and e.short.startswith("host."):
    return e.short
  if e.short and e.short.startswith("EXT-") and title.upper() in e.short:
    return e.short
  if e.short and (e.short.startswith("E-0") or e.short.startswith("EXT-")):
    return f"{e.short} {title}" if title != e.name else e.short
  return title[:1].upper() + title[1:]


def step_chip(x: float, y: float, w: float, step: sysml_lite.Step, m: sysml_lite.Model) -> tuple[list[str], float]:
  performers = [m.elements[p] for p in step.performers]
  st = rv.style_of(performers[0])
  lines = k.wrap(step.doc, w - 18, 10.5, 600)[:3]
  who = " · ".join(element_label(e) for e in performers)
  who_lines = k.wrap(who, w - 18, 9.5, 400)[:2]
  h = 12 + 13 * len(lines) + 12 * len(who_lines) + 6
  out = [k.rect(x, y, w, h, st["fill"], st["stroke"], 7, 1.4)]
  yy = y + 16
  for ln in lines:
    out.append(k.text(x + 9, yy, ln, 10.5, k.INK, 600))
    yy += 13
  for ln in who_lines:
    out.append(k.text(x + 9, yy + 1, ln, 9.5, st.get("chip", k.MUTED)))
    yy += 12
  return out, h


def render_functions(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  view = m.views[vid]
  w = spec["width"]
  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  x0, top, lw = 40, 112, 220
  cw = (w - 40 - x0 - lw) / len(STAGES)
  cx = {s: x0 + lw + i * cw for i, (s, _) in enumerate(STAGES)}
  # stage headers; the envelope column is the ASIL C safety envelope
  for s, label in STAGES:
    env = s == "envelope"
    body.append(k.rect(cx[s] + 4, top, cw - 8, 26, k.ENVELOPE["chip"] if env else k.INK, None, 6))
    body.append(k.text(cx[s] + cw / 2, top + 17, label, 11.5, "#FFFFFF", 700, "middle"))
  y = top + 40
  rows = []
  for fid in sorted(m.functions, key=lambda s: int(s[2:])):
    f = m.functions[fid]
    cells: dict[str, list[tuple[list[str], float]]] = {}
    for st in f.steps:
      cells.setdefault(st.stage, [])
    heights = {}
    for s, _ in STAGES:
      steps = [st for st in f.steps if st.stage == s]
      if not steps:
        continue
      yy, parts = 0.0, []
      for st in steps:
        svg, h = step_chip(cx[s] + 6, y + 10 + yy, cw - 12, st, m)
        parts += svg
        yy += h + 6
      cells[s] = parts
      heights[s] = yy - 6
    title_h = 46 + 15 * len(k.wrap(f.doc, lw - 30, 12, 700)[:3]) + 18
    rh = max([*heights.values(), 52]) + 20
    rh = max(rh, title_h)
    rows.append((f, y, rh, cells, heights))
    y += rh
  for i, (f, y, rh, cells, heights) in enumerate(rows):
    if i % 2 == 0:
      body.append(k.rect(x0, y, w - 80, rh, k.WASH, None, 8))
    env_x = cx["envelope"]
    body.append(f'<rect x="{k.f(env_x + 2)}" y="{k.f(y)}" width="{k.f(cw - 4)}" height="{k.f(rh)}" '
                f'fill="{k.ENVELOPE["fill"]}" opacity="0.55"/>')
    pill, pw = k.pill(x0 + 12, y + 12, f.short, k.INK, size=10)
    body.append(pill)
    for li, ln in enumerate(k.wrap(f.doc, lw - 30, 12, 700)[:3]):
      body.append(k.text(x0 + 12, y + 46 + li * 15, ln, 12, k.INK, 700))
    n_el = len({p for st in f.steps for p in st.performers})
    body.append(k.text(x0 + 12, y + rh - 12, f"{len(f.steps)} steps · {n_el} elements", 10, k.MUTED))
    present = [s for s, _ in STAGES if s in heights]
    # flow arrows between consecutive occupied stages, at the first chip's middle
    for a, b in zip(present, present[1:], strict=False):
      ya = y + 10 + min(heights[a], heights[b], 40) / 2
      x1, x2 = cx[a] + cw - 6, cx[b] + 6
      body.append(f'<line x1="{k.f(x1)}" y1="{k.f(ya)}" x2="{k.f(x2 - 2)}" y2="{k.f(ya)}" stroke="{k.MUTED}" '
                  'stroke-width="1.4" marker-end="url(#fa-arrow)"/>')
    for s in present:
      body += cells[s]
  y = rows[-1][1] + rows[-1][2] + 26
  body.append(k.text(40, y, "Read a row left to right: the function's chain from sensing to acting on the vehicle or "
                     "informing the driver; each step sits on the element that performs it (perform in the model). "
                     "Decomposition AI-drafted, not reviewed (I0).", 11.5, k.INK2))
  legend_y = y + 16
  items, lx = [], 40
  for label, st in (("QM element (SoC software, device)", k.SLATE), ("ML element (E-02)", k.ML),
                    ("ASIL C safety envelope", k.ENVELOPE), ("Outside the item", k.OUTSIDE),
                    ("Untrusted (back end)", k.UNTRUSTED)):
    items.append(k.rect(lx, legend_y + 22, 18, 14, st["fill"], st["stroke"], 4, 1.4))
    items.append(k.text(lx + 24, legend_y + 33, label, 11, k.INK2))
    lx += 40 + k.text_w(label, 11)
  body += rv.footer(w, legend_y, items)
  defs = k.arrow_marker("fa-arrow", k.MUTED, 6)
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body, defs)


RENDERERS = {"functions": render_functions}


# ---------------------------------------------------------------- V-11 security zones

def trust_style(trust: str) -> tuple[dict, str]:
  """Zone colour and the short trust label from the WP-S-07 trust-level text."""
  short = trust.split(";")[0].split("(")[0].strip()
  t = short.lower()
  if t.startswith("trusted") and "outside" in t:
    return {"fill": "#F0FDFA", "stroke": "#0F766E", "chip": "#0F766E"}, short
  if t.startswith("trusted"):
    return k.ENVELOPE, short
  if t.startswith("untrusted"):
    return k.UNTRUSTED, short
  if t.startswith("owner"):
    return k.OUTSIDE, short
  return k.SLATE, short


def csr_count(text: str) -> int:
  n = 0
  for a, b in re.findall(r"CSR-(\d+)(?:…CSR-(\d+))?", text):
    n += int(b) - int(a) + 1 if b else 1
  return n


def zone_members(m: sysml_lite.Model, zid: str, expand: list[str]) -> list[sysml_lite.Element]:
  roots = [e for e in m.root.walk() if e.zone() == zid and (e.parent is None or e.parent.zone() != zid)]
  out = []
  for e in roots:
    out += [c for c in e.children if c.zone() == zid] if e.short in expand else [e]
  return out


def render_security(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  view = m.views[vid]
  w = spec["width"]
  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  boxes = {z: tuple(v) for z, v in spec["zones"].items()}
  missing = sorted(set(m.zones) ^ set(boxes))
  if missing:
    raise sysml_lite.ModelError(f"layout.toml V-11: zones {missing} do not match the model's security zones")
  if "device" in spec:
    x, y, bw, bh = spec["device"]
    body.append(k.rect(x, y, bw, bh, "none", k.INK2, 14, 1.6, "7 5"))
    body.append(k.text(x + 14, y + 20, spec.get("device_label", "comma device"), 12, k.INK2, 700))
  for zid, (x, y, bw, bh) in boxes.items():
    z = m.zones[zid]
    st, trust = trust_style(str(z.values.get("trust", "")))
    body.append(k.rect(x, y, bw, bh, st["fill"], st["stroke"], 10, 1.6))
    pill, pw = k.pill(x + 12, y + 12, zid, st["chip"], size=10.5, h=20)
    body.append(pill)
    tp, tw = k.pill(x + bw - 12, y + 12, trust, "#FFFFFF", st["chip"], h=20, size=10, stroke=st["stroke"], anchor="end")
    body.append(tp)
    name_lines = k.wrap(z.doc, bw - pw - tw - 50, 13, 700)[:2]
    for li, ln in enumerate(name_lines):
      body.append(k.text(x + 20 + pw, y + 27 + li * 16, ln, 13, k.INK, 700))
    # model elements in the zone
    cx, cy = x + 12, y + 44 + 16 * (len(name_lines) - 1)
    members = zone_members(m, zid, spec.get("expand", []))
    for e in members:
      label = element_label(e)
      est = rv.style_of(e)
      cw = k.text_w(label, 10.5, 600) + 16
      if cx + cw > x + bw - 12:
        cx, cy = x + 12, cy + 26
      body.append(k.rect(cx, cy, cw, 20, est["fill"], est["stroke"], 5, 1.2))
      body.append(k.text(cx + 8, cy + 14, label, 10.5, k.INK, 600))
      cx += cw + 6
    ty = cy + 38 if members else cy + 14
    for ln in k.wrap("WP-S-07: " + str(z.values.get("holds", "")).replace("`", ""), bw - 24, 10.5)[:3]:
      if ty > y + bh - 8:
        break
      body.append(k.text(x + 12, ty, ln, 10.5, k.MUTED))
      ty += 14
  # trust boundaries
  for tb, pts in spec["boundaries"].items():
    b = m.boundaries.get(tb)
    if b is None:
      raise sysml_lite.ModelError(f"layout.toml V-11: {tb} is not a trust boundary of the model")
    x1, y1, x2, y2 = pts[:4]
    if (x1, y1) == (x2, y2):
      lx, ly = pts[4:6]
      body.append(k.pill(lx, ly - 10, tb, k.INK, size=10, h=20, anchor="middle")[0])
      continue
    two_way = "↔" in b.doc
    body.append(f'<line x1="{k.f(x1)}" y1="{k.f(y1)}" x2="{k.f(x2)}" y2="{k.f(y2)}" stroke="{k.INK}" stroke-width="2" '
                f'marker-end="url(#tb-arrow)"{" marker-start=" + chr(34) + "url(#tb-arrow)" + chr(34) if two_way else ""}/>')
    lx, ly = pts[4:6] if len(pts) >= 6 else ((x1 + x2) / 2, (y1 + y2) / 2)
    pill, pw = k.pill(lx, ly - 10, tb, k.INK, size=10, h=20, anchor="middle")
    body.append(pill)
  # the boundaries as a table: what crosses, threats, controls
  y = spec["note_y"]
  body.append(k.text(40, y, "Trust boundary", 11, k.INK, 700))
  body.append(k.text(420, y, "Data or control crossing", 11, k.INK, 700))
  body.append(k.text(1150, y, "Threats", 11, k.INK, 700))
  body.append(k.text(w - 40, y, "Controls", 11, k.INK, 700, "end"))
  y += 10
  for tb in sorted(m.boundaries, key=lambda s: int(s[3:])):
    b = m.boundaries[tb]
    lines = k.wrap(str(b.values.get("crossing", "")).replace("`", ""), 700, 10.5)[:2]
    rh = 10 + 14 * max(len(lines), 1) + 6
    body.append(f'<line x1="40" y1="{k.f(y)}" x2="{k.f(w - 40)}" y2="{k.f(y)}" stroke="{k.HAIR}"/>')
    pill, pw = k.pill(40, y + 7, tb, k.INK, size=9.5, h=18)
    body.append(pill)
    body.append(k.text(46 + pw, y + 20, b.doc, 10.5, k.INK, 600))
    for li, ln in enumerate(lines):
      body.append(k.text(420, y + 20 + li * 14, ln, 10.5, k.INK2))
    body.append(k.text(1150, y + 20, str(b.values.get("threats", "")), 10.5, k.INK2))
    body.append(k.text(w - 40, y + 20, f"{csr_count(str(b.values.get('controls', '')))} CSR", 10.5, k.INK2, 600, "end"))
    y += rh
  y += 24
  body.append(k.text(40, y, "Zones and boundaries carry every column of WP-S-07 §3.1 and §3.2 (check M10); the chips are the "
                     "model elements in each zone (@Zone). Every safety-relevant protection sits at Z1 or below it in the "
                     "trust order.", 11.5, k.INK2))
  legend_y = y + 16
  items, lx = [], 40
  for label, st in (("Trusted (envelope)", k.ENVELOPE), ("QM, assumed compromisable", k.SLATE),
                    ("Untrusted", k.UNTRUSTED), ("Owner-controlled", k.OUTSIDE),
                    ("Trusted, outside the device", trust_style("Trusted, outside the device")[0])):
    items.append(k.rect(lx, legend_y + 22, 18, 14, st["fill"], st["stroke"], 4, 1.4))
    items.append(k.text(lx + 24, legend_y + 33, label, 11, k.INK2))
    lx += 40 + k.text_w(label, 11)
  body += rv.footer(w, legend_y, items)
  defs = k.arrow_marker("tb-arrow", k.INK, 8)
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body, defs)


RENDERERS["security"] = render_security


# ---------------------------------------------------------------- V-12 integration build-up

def render_integration(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  view = m.views[vid]
  w = spec["width"]
  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  steps = sorted(m.integration, key=lambda s: int(s[2:]))
  n = len(steps)
  hand_w = 150
  gap = 34
  cw = (w - 80 - hand_w - gap * n) / n
  rise, base = spec.get("rise", 34), 112 + spec.get("rise", 34) * (n - 1)
  cases = {sid: sorted((v.short for v in m.verifications.values()
                        if sid in sysml_lite._as_list(v.values.get("steps"))), key=rv_natural) for sid in steps}
  so_far: list[sysml_lite.Element] = []
  cards = []
  for i, sid in enumerate(steps):
    st = m.integration[sid]
    x, y = 40 + i * (cw + gap), base - i * rise
    new = []
    for ident in sysml_lite._as_list(st.values.get("integrates")):
      e = m.find(ident) or next(e for e in m.elements.values() if e.name == ident and not e.short)
      new.append(e)
    part = [k.rect(x, y, cw, 0, "#FFFFFF", k.INK2, 10, 1.4)]  # height patched below
    pill, pw = k.pill(x + 12, y + 12, sid, k.INK, size=10.5, h=20)
    part.append(pill)
    part.append(k.text(x + 20 + pw, y + 27, k.clip(st.doc, cw - pw - 32, 12.5, 700), 12.5, k.INK, 700))
    yy = y + 50
    part.append(k.text(x + 12, yy, "INTEGRATED", 9.5, k.MUTED, 700))
    yy += 8
    cx = x + 12
    for e, fresh in [(e, False) for e in so_far] + [(e, True) for e in new]:
      label = element_label(e)
      est = rv.style_of(e)
      bw = k.text_w(label, 10, 600) + 14
      if cx + bw > x + cw - 12:
        cx, yy = x + 12, yy + 24
      op = "" if fresh else ' opacity="0.45"'
      part.append(f'<g{op}>' + k.rect(cx, yy, bw, 19, est["fill"], est["stroke"], 5, 1.6 if fresh else 1)
                  + k.text(cx + 7, yy + 13.5, label, 10, k.INK, 600) + "</g>")
      cx += bw + 5
    if not new:
      yy += 24
      part.append(k.text(x + 12, yy + 12, spec.get("no_new", "no new element: the plant model is bench equipment"), 10, k.MUTED))
    yy += 40
    part.append(k.text(x + 12, yy, "INTERFACES EXERCISED", 9.5, k.MUTED, 700))
    yy += 8
    cx = x + 12
    for i_id in sysml_lite._as_list(st.values.get("exercises")):
      p, pw2 = k.pill(cx, yy, i_id, "#FFFFFF", k.INK2, h=18, size=9.5, stroke=k.FAINT, mono=True)
      if cx + pw2 > x + cw - 12:
        cx, yy = x + 12, yy + 23
        p, pw2 = k.pill(cx, yy, i_id, "#FFFFFF", k.INK2, h=18, size=9.5, stroke=k.FAINT, mono=True)
      part.append(p)
      cx += pw2 + 5
    yy += 40
    for head, key in (("STIMULUS", "stimulus"), ("PURPOSE", "purpose")):
      part.append(k.text(x + 12, yy, head, 9.5, k.MUTED, 700))
      yy += 15
      for ln in k.wrap(str(st.values.get(key, "")).replace("`", "").replace("**", ""), cw - 24, 10.5)[:4]:
        part.append(k.text(x + 12, yy, ln, 10.5, k.INK2))
        yy += 14
      yy += 8
    nc = len(cases[sid])
    part.append(k.rect(x + 12, yy, cw - 24, 26, "#EFF6FF" if nc else "#FEF2F2", None, 6))
    part.append(k.text(x + 22, yy + 17, f"{nc} VS-SI cases run at this step", 11, "#1D4ED8" if nc else "#B91C1C", 700))
    yy += 40
    part[0] = k.rect(x, y, cw, yy - y, "#FFFFFF", k.INK2, 10, 1.4)
    cards.append((x, y, yy))
    body += part
    so_far += new
  # arrows between steps and the hand-over
  for (x1, y1, b1), (x2, y2, _) in zip(cards, cards[1:], strict=False):
    ya = y2 + 26
    body.append(f'<path d="M{k.f(x1 + cw)} {k.f(ya + rise)} H{k.f(x1 + cw + gap / 2)} V{k.f(ya)} H{k.f(x2 - 2)}" fill="none" '
                f'stroke="{k.INK2}" stroke-width="1.6" marker-end="url(#ib-arrow)"/>')
  xh, yh = 40 + n * (cw + gap), cards[-1][1]
  body.append(f'<line x1="{k.f(xh - gap)}" y1="{k.f(yh + 26)}" x2="{k.f(xh - 2)}" y2="{k.f(yh + 26)}" stroke="{k.INK2}" '
              'stroke-width="1.6" marker-end="url(#ib-arrow)"/>')
  body.append(k.rect(xh, yh, hand_w, 120, "#EFF6FF", "#2563EB", 10, 1.4))
  for li, ln in enumerate(k.wrap(spec.get("handover", "Hand-over to system verification"), hand_w - 20, 11.5, 700)):
    body.append(k.text(xh + 10, yh + 24 + li * 15, ln, 11.5, "#1D4ED8", 700))
  bottom = max(c[2] for c in cards)
  y = bottom + 30
  total = len({c for v in cases.values() for c in v})
  body.append(k.text(40, y, f"Bottom-up: each step keeps what the steps before it integrated (faded) and adds its own elements; "
                     f"its tests must pass before the next starts. {total} VS-SI cases name a step (WP-S-08 §6, Step column). "
                     "Rows of WP-S-08 §3.1 held cell by cell (check M11).", 11.5, k.INK2))
  legend_y = y + 16
  items, lx = [], 40
  for label, st in (("QM element", k.SLATE), ("ML element", k.ML), ("ASIL C safety envelope", k.ENVELOPE),
                    ("Outside the item", k.OUTSIDE)):
    items.append(k.rect(lx, legend_y + 22, 18, 14, st["fill"], st["stroke"], 4, 1.4))
    items.append(k.text(lx + 24, legend_y + 33, label, 11, k.INK2))
    lx += 40 + k.text_w(label, 11)
  items.append(k.text(lx, legend_y + 33, "faded: integrated at an earlier step", 11, k.INK2))
  body += rv.footer(w, legend_y, items)
  defs = k.arrow_marker("ib-arrow", k.INK2, 7)
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body, defs)


def rv_natural(s: str) -> list:
  return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


RENDERERS["integration"] = render_integration


# ---------------------------------------------------------------- V-13 system modes (state machine)

ENFORCER = {"envelope": (k.ENVELOPE["chip"], 2.2, "Enforced by the envelope (panda)"),
            "host": (k.MUTED, 1.6, "Host only (selfdrived, dmonitoringd)"),
            "gap16": ("#D2553F", 2.2, "Host only while the envelope still allows actuation (GAP-16)")}
MACHINE_TAG = {"SM-SELFDRIVED": "H", "SM-TOY-AUTH": "P", "SM-SAFETY-MODE": "P"}


def record_line(refs: list[str]) -> str:
  groups: dict[str, list[str]] = {}
  for r in refs:
    machine, _, tid = r.partition(" ")
    groups.setdefault(MACHINE_TAG.get(machine, machine), []).append(tid)
  return "  ".join(f"{tag}: {' · '.join(ids)}" for tag, ids in groups.items())


def render_states(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  view = m.views[vid]
  w = spec["width"]
  sm = m.state_machines[spec["machine"]]
  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  boxes = {p.replace("_", "."): tuple(v) for p, v in spec["states"].items()}
  missing = sorted(set(sm.states) ^ set(boxes))
  if missing:
    raise sysml_lite.ModelError(f"layout.toml {vid}: states {missing} do not match {sm.short}")
  for path, (x, y, bw, bh) in boxes.items():
    st = sm.states[path]
    row = st.meta.get("ModeRow") or {}
    composite = bool(st.children)
    if composite:
      body.append(k.rect(x, y, bw, bh, k.ENVELOPE["fill"], k.ENVELOPE["stroke"], 16, 1.4, "7 5"))
      body.append(k.text(x + 16, y + 22, st.path.split(".")[-1].capitalize(), 13, k.ENVELOPE["text"], 700))
      continue
    actuation = str(row.get("actuation", ""))
    acts = "—" not in actuation and not actuation.lower().startswith("none") and actuation.strip() not in ("", "—")
    style = (k.ENVELOPE if acts else k.OUTSIDE)
    if path.endswith("softDisabling"):
      style = {"fill": "#FEF2F2", "stroke": "#D2553F"}
    transient = not row.get("host") and not row.get("panda")
    body.append(k.rect(x, y, bw, bh, style["fill"], style["stroke"], 12, 1.4 if transient else 1.8,
                       "6 4" if transient else None))
    body.append(k.text(x + 14, y + 24, st.doc, 14, k.INK, 700))
    ty = y + 44
    for side, color in (("host", k.MUTED), ("panda", k.ENVELOPE["chip"])):
      refs = sysml_lite._as_list(row.get(side))
      if refs:
        txt = ("host: " if side == "host" else "panda: ") + " · ".join(r.split(" ", 1)[1] for r in refs)
        body.append(k.text(x + 14, ty, k.clip(txt, bw - 28, 10.5, 400, True), 10.5, color, 400, None, True))
        ty += 16
    room = max(1, int((y + bh - 34 - (ty + 4)) // 14) + 1)  # text above the actuation pill
    for ln in k.wrap(re.sub(r"\s*\(`[^)]*`\)|`", "", str(row.get("description", ""))), bw - 28, 10.5)[:room]:
      body.append(k.text(x + 14, ty + 4, ln, 10.5, k.INK2))
      ty += 14
    label = "actuates: " + re.sub(r"\(.*?\)", "", actuation).strip() if acts else "no actuation"
    p, _ = k.pill(x + 14, y + bh - 28, k.clip(label, bw - 40, 10), k.ENVELOPE["chip"] if acts else "#FFFFFF",
                  "#FFFFFF" if acts else k.MUTED, h=18, size=10, stroke=None if acts else k.FAINT)
    body.append(p)
  # initial state
  ix, iy = spec.get("initial", [0, 0])
  if ix:
    tx, ty_, _, _ = boxes[sm.initial]
    body.append(f'<circle cx="{k.f(ix)}" cy="{k.f(iy)}" r="7" fill="{k.INK}"/>')
    body.append(f'<line x1="{k.f(ix)}" y1="{k.f(iy + 7)}" x2="{k.f(ix)}" y2="{k.f(ty_ - 2)}" stroke="{k.INK}" '
                'stroke-width="1.6" marker-end="url(#st-ink)"/>')
  by_name = {t.name: t for t in sm.transitions}
  missing = sorted(set(by_name) ^ set(spec["transitions"]))
  if missing:
    raise sysml_lite.ModelError(f"layout.toml {vid}: transitions {missing} do not match {sm.short}")
  for name, tl in spec["transitions"].items():
    t = by_name[name]
    enf = t.meta.get("Enforcement") or {}
    kind = str(enf.get("kind", "host")).split("::")[-1]
    color, sw, _ = ENFORCER[kind]
    pts = tl.get("points", [])
    if pts:
      d = "M" + " L".join(f"{k.f(px)} {k.f(py)}" for px, py in pts)
      dash = ' stroke-dasharray="5 4"' if tl.get("dash") else ""
      body.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}"{dash} '
                  f'marker-end="url(#st-{kind})"/>')
    lx, ly = tl["label"][:2]
    anchor = tl["label"][2] if len(tl["label"]) > 2 else None
    recs = record_line(sysml_lite._as_list(enf.get("records")))
    lines = [] if tl.get("compact") else [(ln, k.INK if kind != "gap16" else color, 600)
                                          for ln in k.wrap(t.doc, tl.get("wrap", 260), 10.5, 600)]
    if recs:
      for ln in k.wrap(recs, tl.get("wrap", 260), 10.5):
        lines.append((ln, color if kind != "host" else k.MUTED, 400))
    elif not tl.get("compact"):
      lines.append(("no record (dmonitoringd)", k.MUTED, 400))
    for i, (s, c, wt) in enumerate(lines):
      body.append(k.text(lx, ly + i * 13, s, 10.5, c, wt, anchor))
  y = spec["note_y"]
  configs = sysml_lite._as_list((sm.meta.get("ModeConfigurations") or {}).get("rows"))
  note = (f"{sm.short}: the operating modes of WP-C-01 §4 (check M12). H: selfdrived record (SM-SELFDRIVED); "
          "P: panda records (SM-TOY-AUTH, SM-SAFETY-MODE). Not states but configurations: " + "; ".join(configs) + ".")
  for i, ln in enumerate(k.wrap(note, w - 80, 11.5)):
    body.append(k.text(40, y + i * 16, ln, 11.5, k.INK2))
  legend_y = y + 16 * (len(k.wrap(note, w - 80, 11.5)) - 1) + 16
  items, lx = [], 40
  for kind, (color, sw, label) in ENFORCER.items():
    items.append(f'<line x1="{lx}" y1="{legend_y + 29}" x2="{lx + 26}" y2="{legend_y + 29}" stroke="{color}" '
                 f'stroke-width="{sw}"/>')
    items.append(k.text(lx + 32, legend_y + 33, label, 11, k.INK2))
    lx += 52 + k.text_w(label, 11)
  body += rv.footer(w, legend_y, items)
  defs = "".join(k.arrow_marker(f"st-{kd}", c, 8) for kd, (c, _, _) in ENFORCER.items()) + k.arrow_marker("st-ink", k.INK, 8)
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body, defs)


RENDERERS["states"] = render_states


# ---------------------------------------------------------------- V-16 state-machine records

REC_STATUS = [("not implemented", "#D2553F", "#FEF2F2", "not implemented: the record says what is required"),
              ("gap", "#B45309", "#FFFBEB", "implemented with a gap the record names"),
              ("reference build", k.ENVELOPE["chip"], k.ENVELOPE["fill"], "in the reference build only"),
              ("upstream build", k.MUTED, "#F1F5F9", "without the reference build only"),
              ("every build", "#334155", "#F8FAFC", "in every build")]


def record_status(meta: dict) -> str:
  if str(meta.get("code", "")).startswith("not implemented"):
    return "not implemented"
  if meta.get("gap"):
    return "gap"
  return {"reference": "reference build", "upstream": "upstream build"}.get(str(meta.get("build")), "every build")


def ends_label(names: list[str], states: list[str]) -> str:
  return "any state" if len(names) == len(states) > 1 else ", ".join(names)


def render_records(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  """The state-machine records (WP-W-05 §5) as modelled: one panel per machine, one row per record transition."""
  view = m.views[vid]
  w = spec["width"]
  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  style = {s: (c, bg) for s, c, bg, _ in REC_STATUS}
  y = 104
  totals: dict[str, int] = {}
  for short in spec["machines"]:
    sm = m.state_machines[short]
    states = list(sm.states)
    groups: dict[str, dict] = {}
    for t in sm.transitions:
      meta = t.meta.get("RecordTransition") or {}
      g = groups.setdefault(str(meta.get("id")), {"meta": meta, "src": [], "dst": [], "self": True})
      g["self"] = g["self"] and t.source == t.target
      for key, end in (("src", t.source), ("dst", t.target)):
        if end not in g[key]:
          g[key].append(end)
    rows = list(groups.items())
    rh = 24
    ph = 92 + len(rows) * rh
    body.append(k.rect(30, y, w - 60, ph, k.WASH, k.HAIR, 12))
    body.append(k.text(46, y + 26, f"{short} · {sm.doc}", 15, k.INK, 700))
    units = sysml_lite._as_list(sm.meta["StateRecord"].get("units"))
    body.append(k.text(w - 46, y + 26, "runs on " + " · ".join(units), 11, k.MUTED, 400, "end", True))
    sx = 46
    body.append(k.text(sx, y + 52, "STATES", 9.5, k.MUTED, 700, extra=' letter-spacing="1"'))
    sx += 58
    for st in states:
      init = st == sm.initial
      p, pw = k.pill(sx, y + 40, st + (" · initial" if init else ""), k.INK2 if init else "#FFFFFF",
                     "#FFFFFF" if init else k.INK2, 18, 10, 700, None if init else k.FAINT, mono=True)
      body.append(p)
      sx += pw + 6
    ty = y + 72
    cols = (54, 120, 560, 900, 1030)
    for x, h in zip(cols, ("ID", "trigger · guard", "from → to", "status", "requirements (SWSR)")):
      body.append(k.text(x, ty, h.upper(), 9.5, k.MUTED, 700, extra=' letter-spacing="1"'))
    ty += 8
    for i, (tid, g) in enumerate(rows):
      meta = g["meta"]
      st = record_status(meta)
      totals[st] = totals.get(st, 0) + 1
      col, bg = style[st]
      if i % 2 == 0:
        body.append(k.rect(40, ty, w - 80, rh, "#FFFFFF", None, 4))
      p, _ = k.pill(cols[0], ty + 3, tid, col, size=9.5, mono=True)
      body.append(p)
      trig = str(meta.get("trigger", ""))
      guard = str(meta.get("condition", ""))
      body.append(f'<text x="{cols[1]}" y="{k.f(ty + 16)}" font-size="10.5" fill="{k.INK}">{k.escape(trig)}'
                  + (f'<tspan fill="{k.MUTED}"> · {k.escape(k.clip(guard, max(40, cols[2] - cols[1] - 24 - k.text_w(trig + " · ", 10.5)), 10.5))}</tspan>'
                     if guard else "") + "</text>")
      fr = f"{ends_label(g['src'], states)} → {'same' if g['self'] else ends_label(g['dst'], states)}"
      body.append(k.text(cols[2], ty + 16, k.clip(fr, cols[3] - cols[2] - 16, 10.5, 400, True), 10.5, k.INK2, 400, None, True))
      p, _ = k.pill(cols[3], ty + 4, st, bg, col, 16, 9.5, 700, col)
      body.append(p)
      xx = cols[4]
      swsr = [x for x in sysml_lite._as_list(meta.get("swsr")) if x]
      for j, s_ in enumerate(swsr):
        p, pw = k.pill(xx, ty + 4, s_.replace("SWSR-", ""), "#FFFFFF", "#334155", 16, 9, 700, k.FAINT, mono=True)
        if xx + pw > w - 70:
          body.append(k.text(xx, ty + 16, f"+{len(swsr) - j}", 10, k.MUTED, 700))
          break
        body.append(p)
        xx += pw + 3
      if not swsr:
        body.append(k.text(cols[4], ty + 16, "no SWSR", 10, "#B45309", 600))
      ty += rh
    y += ph + 16
  summary = " · ".join(f"{totals.get(s, 0)} {s}" for s, *_ in REC_STATUS)
  body.append(k.text(40, y + 8, f"{sum(totals.values())} record transitions: {summary}. A transition from any state or "
                     "to the requested mode is one record row and several model transitions (gen_behaviour.py).", 12, k.INK, 600))
  legend_y = y + 26
  items, lx = [], 40
  for s, c, bg, label in REC_STATUS:
    p, pw = k.pill(lx, legend_y + 21, s, bg, c, 16, 9.5, 700, c)
    items += [p, k.text(lx + pw + 8, legend_y + 33, label, 11, k.INK2)]
    lx += pw + 30 + k.text_w(label, 11)
  body += rv.footer(w, legend_y, items)
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body)


RENDERERS["records"] = render_records


# ---------------------------------------------------------------- V-17 sequence

SEQ_STATUS = {"as inherited": (k.INK2, None, "as inherited"),
              "required, in the reference build": (k.ENVELOPE["chip"], None, "required, in the reference build (not verified)"),
              "required, not implemented": ("#D2553F", "6 4", "required, not yet implemented")}


def render_sequence(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  """A sequence of the model as a sequence diagram: lifelines left to right, one row per step."""
  view = m.views[vid]
  w = spec["width"]
  q = m.sequences[spec["sequence"]]
  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  x0, x1 = 140, 990
  lx = {name: x0 + i * (x1 - x0) / (len(q.lifelines) - 1) for i, (name, _) in enumerate(q.lifelines)}
  top = 104
  decl = next(o for p in m.packages.values() for o in p.members if o.kind == "occurrence def" and o.short == q.short)
  titles = {x.name: x.doc for x in decl.members if x.kind == "part" and x.doc}
  lanes_at = len(body)  # lifelines are drawn behind the steps, once their length is known
  for name, ident in q.lifelines:
    e = m.find(ident)
    if e is None:
      named = [x for x in m.elements.values() if x.kind == "part" and x.name == ident]
      e = named[0] if named else None
    st = rv.style_of(e) if e is not None else k.OUTSIDE
    if e is not None and e.scope() != "inside":
      st = k.OUTSIDE
    cx = lx[name]
    body.append(k.rect(cx - 58, top, 116, 44, st["fill"], st["stroke"], 8, 1.4))
    body.append(k.text(cx, top + 19, titles.get(name, name), 12, k.INK, 700, "middle"))
    body.append(k.text(cx, top + 34, ident, 9.5, k.MUTED, 400, "middle", True))
  rx = 1100
  body.append(k.text(rx, top + 19, "RECORDS · CODE", 9.5, k.MUTED, 700, extra=' letter-spacing="1"'))
  y = top + 64
  phase = None
  for msg in q.messages:
    stp = msg.meta.get("SequenceStep") or {}
    if stp.get("phase") != phase:
      phase = stp.get("phase")
      y += 8
      body.append(k.rect(40, y, w - 80, 22, k.WASH, None, 4))
      body.append(k.text(52, y + 15, str(phase).upper(), 10, k.MUTED, 700, extra=' letter-spacing="1.1"'))
      y += 30
    color, dash, _ = SEQ_STATUS[str(stp.get("status"))]
    sx, tx = lx[msg.source], lx[msg.target]
    text = msg.doc
    cond = str(stp.get("condition", ""))
    after = str(stp.get("stateAfter", ""))
    rh = 40 + (12 if cond else 0)
    body.append(k.text(48, y + 18, msg.short, 10.5, k.MUTED, 700, None, True))
    if sx == tx:
      d = f' stroke-dasharray="{dash}"' if dash else ""
      body.append(f'<path d="M{k.f(sx)} {k.f(y + 10)}h26v16h-24" fill="none" stroke="{color}" stroke-width="1.6"{d} '
                  f'marker-end="url(#sq-{list(SEQ_STATUS).index(str(stp.get("status")))})"/>')
      last = sx == max(lx.values())
      label_x, anchor = (sx - 64, "end") if last else (sx + 34, None)
      width = 300 if not last else 420
    else:
      d = f' stroke-dasharray="{dash}"' if dash else ""
      body.append(f'<line x1="{k.f(sx)}" y1="{k.f(y + 22)}" x2="{k.f(tx)}" y2="{k.f(y + 22)}" stroke="{color}" '
                  f'stroke-width="1.6"{d} marker-end="url(#sq-{list(SEQ_STATUS).index(str(stp.get("status")))})"/>')
      label_x, anchor = (sx + tx) / 2, "middle"
      width = max(abs(tx - sx) - 12, 220)
    body.append(k.text(label_x, y + 16, k.clip(text, width, 10.5), 10.5, color if color != k.INK2 else k.INK, 600, anchor))
    if cond:
      body.append(k.text(label_x, y + 36, k.clip(f"[{cond}]", width, 10), 10, k.MUTED, 400, anchor))
    if after:
      p, _ = k.pill(tx + 8 if sx != tx else tx + 34, y + 26 + (12 if cond else 0) - (0 if sx != tx else -2),
                    after.split(":", 1)[-1].strip(), "#FFFFFF", k.INK2, 16, 9.5, 700, k.INK2, mono=True)
      if sx == tx:
        p, _ = k.pill(sx - 8, y + 4, after.split(":", 1)[-1].strip(), "#FFFFFF", k.INK2, 16, 9.5, 700, k.INK2,
                      anchor="end", mono=True)
      body.append(p)
    recs = [r for r in sysml_lite._as_list(stp.get("records")) if r]
    code = str(stp.get("code", ""))
    side = [ln for ln in (" · ".join(recs), code) if ln]
    for i, ln in enumerate(side[:2]):
      body.append(k.text(rx, y + 14 + i * 13, k.clip(ln, w - rx - 40, 10, 400, True), 10, k.MUTED if i else k.INK2, 400, None, True))
    y += rh
  body[lanes_at:lanes_at] = [f'<line x1="{k.f(lx[name])}" y1="{k.f(top + 44)}" x2="{k.f(lx[name])}" y2="{k.f(y)}" '
                             f'stroke="{k.FAINT}" stroke-width="1" stroke-dasharray="3 4"/>' for name, _ in q.lifelines]
  legend_y = y + 14
  items, lxx = [], 40
  for i, (s, (c, dash, label)) in enumerate(SEQ_STATUS.items()):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    items.append(f'<line x1="{lxx}" y1="{legend_y + 29}" x2="{lxx + 30}" y2="{legend_y + 29}" stroke="{c}" stroke-width="1.6"{d} '
                 f'marker-end="url(#sq-{i})"/>')
    items.append(k.text(lxx + 38, legend_y + 33, label, 11, k.INK2))
    lxx += 70 + k.text_w(label, 11)
  p, pw = k.pill(lxx, legend_y + 21, "SILENT", "#FFFFFF", k.INK2, 16, 9.5, 700, k.INK2, mono=True)
  items += [p, k.text(lxx + pw + 8, legend_y + 33, "state after the step (safety MCU or selfdrived record)", 11, k.INK2)]
  body += rv.footer(w, legend_y, items)
  defs = "".join(k.arrow_marker(f"sq-{i}", c, 8) for i, (c, _, _) in enumerate(SEQ_STATUS.values()))
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body, defs)


RENDERERS["sequence"] = render_sequence


# ---------------------------------------------------------------- V-18 timing budgets

BUDGET_COLORS = {"fdti": ("#2563EB", "FDTI: detection"), "frti": (k.ENVELOPE["chip"], "FRTI: reaction"),
                 "margin": ("#0F766E", "margin left")}


def short_cell(text: str, width: float) -> str:
  return k.clip(re.sub(r"\s+", " ", re.sub(r"`|\*\*", "", text)), width, 10)


def render_budgets(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  """The FTTI budgets of WP-S-04 §3.7 on one time axis, with the elements their TSRs are allocated to."""
  view = m.views[vid]
  w = spec["width"]
  tmax = spec.get("axis_seconds", 1.2)
  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  x0, x1 = 470, 1010
  px = lambda s: x0 + (x1 - x0) * min(s, tmax) / tmax  # noqa: E731
  top = 104
  body.append(k.text(40, top + 8, "SAFETY GOAL · FAULT CLASS", 9.5, k.MUTED, 700, extra=' letter-spacing="1"'))
  body.append(k.text(1040, top + 8, "TSRs · SATISFIED BY (allocation)", 9.5, k.MUTED, 700, extra=' letter-spacing="1"'))
  for i in range(0, int(round(tmax * 10)) + 1, 2):
    s_ = i / 10
    body.append(f'<line x1="{k.f(px(s_))}" y1="{top + 16}" x2="{k.f(px(s_))}" y2="{top + 22}" stroke="{k.FAINT}"/>')
    body.append(k.text(px(s_), top + 8, f"{s_:g} s", 9.5, k.MUTED, 400, "middle"))
  y = top + 28
  rh = 40
  closed = timeless = 0
  for i, (label, b) in enumerate(m.budgets.items()):
    v = b.values
    sec = {a: v.get(f"{a}Seconds") for a in ("ftti", "fdti", "frti", "margin", "fhti")}
    if i % 2 == 0:
      body.append(k.rect(30, y, w - 60, rh, k.WASH, None, 4))
    xx = 40
    for g in sysml_lite._as_list(v.get("goals")):
      p, pw = k.pill(xx, y + 5, g, k.ENVELOPE["chip"], size=9, mono=True)
      body.append(p)
      xx += pw + 4
    rest = re.sub(r"^(SG-\d\d(?:/\d\d)?\s*(?:/\s*SG-\d\d)?\s*)", "", label)
    body.append(k.text(xx + 4, y + 18, k.clip(rest or "all fault classes", x0 - xx - 24, 11), 11, k.INK, 600))
    body.append(k.text(40, y + 33, short_cell(f"FTTI {v.get('ftti', '')}", x0 - 60), 10, k.MUTED))
    numeric = None not in (sec["ftti"], sec["fdti"], sec["frti"])
    by = y + 9
    if numeric:
      closed += 1
      xa = px(0)
      for key in ("fdti", "frti"):
        xb = px((sec["fdti"] if key == "fdti" else sec["fdti"] + sec["frti"]))
        body.append(k.rect(xa, by, max(xb - xa, 1.5), 14, BUDGET_COLORS[key][0], None, 2))
        xa = xb
      xf = px(sec["ftti"])
      if xf > xa:
        body.append(k.rect(xa, by + 4, xf - xa, 6, "#99F6E4", None, 2))
      body.append(f'<line x1="{k.f(xf)}" y1="{k.f(by - 4)}" x2="{k.f(xf)}" y2="{k.f(by + 18)}" stroke="{k.INK}" stroke-width="2"/>')
      body.append(k.text(xf + 4 if sec["ftti"] <= tmax else xf - 4, by + 26, f"FTTI {sec['ftti']:g} s" + (" →" if sec["ftti"] > tmax else ""),
                         9.5, k.INK, 700, None if sec["ftti"] <= tmax else "end"))
    else:
      timeless += 1
      parts = [f"FDTI {v.get('fdti', '')}", f"FRTI {v.get('frti', '')}"]
      body.append(k.text(x0, y + 18, short_cell(" · ".join(parts), x1 - x0), 10, k.MUTED))
      body.append(k.text(x0, y + 32, "not all times: drawn as text (WP-S-04 §3.7)", 9.5, "#B45309", 600))
    els: list[str] = []
    tsrs = [t for t in sysml_lite._as_list(v.get("tsr")) if t]
    for t in tsrs:
      for p in m.requirements[t].satisfied_by:
        ch, title = rv_label(m, p)
        if (ch or title) not in els:
          els.append(ch or title)
    body.append(k.text(1040, y + 17, k.clip(", ".join(t.replace("TSR-", "") for t in tsrs) and
                                            "TSR " + ", ".join(t.replace("TSR-", "") for t in tsrs) or "no TSR named", w - 1080, 10.5, 600, True),
                       10.5, k.INK2 if tsrs else "#B45309", 600, None, True))
    body.append(k.text(1040, y + 32, k.clip("on " + ", ".join(els) if els else "", w - 1080, 10, 400, True), 10, k.MUTED, 400, None, True))
    y += rh
  body.append(k.text(40, y + 22, f"{len(m.budgets)} budgets: {closed} given as times and checked to add up (FDTI + FRTI within the FTTI, "
                     f"FHTI and margin consistent, check H2); {timeless} with a cell that is not a time.", 12, k.INK, 600))
  legend_y = y + 40
  items, lx = [], 40
  for key, (c, lab) in BUDGET_COLORS.items():
    items.append(k.rect(lx, legend_y + 22 + (4 if key == "margin" else 0), 26, 6 if key == "margin" else 14,
                        "#99F6E4" if key == "margin" else c, None, 2))
    items.append(k.text(lx + 34, legend_y + 33, lab, 11, k.INK2))
    lx += 60 + k.text_w(lab, 11)
  items += [f'<line x1="{lx}" y1="{legend_y + 18}" x2="{lx}" y2="{legend_y + 40}" stroke="{k.INK}" stroke-width="2"/>',
            k.text(lx + 8, legend_y + 33, "FTTI", 11, k.INK2)]
  body += rv.footer(w, legend_y, items)
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body)


def rv_label(m: sysml_lite.Model, path: str) -> tuple[str, str]:
  e = m.elements[path]
  title = rv.TITLES.get(e.name) or e.name
  return (e.short or "", title)


RENDERERS["budgets"] = render_budgets


# ---------------------------------------------------------------- V-19 HSI signals

PROTECTION = {"integrity": re.compile(r"checksum|crc|xor", re.I),
              "validity": re.compile(r"counter|alive|changes while|supervised|serviced", re.I)}


def protection(m: sysml_lite.Model, sid: str, key: str) -> bool:
  """Whether the signal carries integrity protection (a checksum, CRC or XOR) or a liveness indication (a counter,
  alive check or supervision) of its own. "as S-nn" refers to another signal's cell; "none…" and "required…" mean
  not in place."""
  seen = set()
  text = ""
  while sid not in seen:
    seen.add(sid)
    text = re.sub(r"`|\*\*", "", str(m.signals[sid].values.get(key, ""))).strip()
    ref = re.fullmatch(r"as (S-\d\d)", text)
    if not ref or ref.group(1) not in m.signals:
      break
    sid = ref.group(1)
  low = text.lower()
  if low.startswith(("none", "required", "—", "-")) or not low:
    return False
  return bool(PROTECTION[key].search(text))


def render_signals(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  """The HSI signals of WP-S-05 §11: owner elements, protection in the signal, TSRs and test cases."""
  view = m.views[vid]
  w = spec["width"]
  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  cols = {"id": 40, "name": 96, "dir": 420, "owner": 640, "prot": 930, "asil": 1130, "tsr": 1210, "tests": 1370}
  top = 104
  for key, lab in (("name", "SIGNAL"), ("dir", "DIRECTION"), ("owner", "OWNER ELEMENTS"), ("prot", "IN THE SIGNAL"),
                   ("asil", "ASIL"), ("tsr", "TSRs"), ("tests", "TESTS")):
    body.append(k.text(cols[key], top + 8, lab, 9.5, k.MUTED, 700, extra=' letter-spacing="1"'))
  y = top + 20
  group = None
  rh = 26
  no_int = no_live = 0
  for sid, sg in m.signals.items():
    v = sg.values
    if v.get("group") != group:
      group = v.get("group")
      y += 6
      hsi = sysml_lite._as_list(v.get("hsi"))
      body.append(k.rect(30, y, w - 60, 24, k.WASH, None, 4))
      body.append(k.text(42, y + 16, f"{group} · {hsi[0]}" + (f"…{hsi[-1][4:]}" if len(hsi) > 1 else ""), 11, k.INK, 700))
      y += 30
    p, _ = k.pill(cols["id"], y + 4, sid, "#334155", size=9.5, mono=True)
    body.append(p)
    body.append(k.text(cols["name"], y + 17, k.clip(re.sub(r"`", "", sg.doc), cols["dir"] - cols["name"] - 14, 10.5), 10.5, k.INK, 600))
    body.append(k.text(cols["dir"], y + 17, k.clip(re.sub(r"`", "", str(v.get("direction", ""))), cols["owner"] - cols["dir"] - 14, 10), 10, k.INK2))
    xx = cols["owner"]
    for o in sysml_lite._as_list(v.get("owners")):
      e = m.find(o) or next((x for x in m.elements.values() if x.short == o or x.path.endswith("." + o.split(".")[-1])), None)
      st = rv.style_of(e) if e is not None else k.OUTSIDE
      pp, pw = k.pill(xx, y + 5, o, "#FFFFFF", st["chip"], 16, 9, 700, st["stroke"], mono=True)
      if xx + pw > cols["prot"] - 10:
        break
      body.append(pp)
      xx += pw + 3
    integ, live = protection(m, sid, "integrity"), protection(m, sid, "validity")
    no_int += not integ
    no_live += not live
    xx = cols["prot"]
    for ok, lab_ok, lab_no in ((integ, "integrity", "no integrity"), (live, "liveness", "no liveness")):
      pp, pw = k.pill(xx, y + 5, lab_ok if ok else lab_no, "#F0FDFA" if ok else "#FEF2F2", "#0F766E" if ok else "#D2553F",
                      16, 9, 700, "#0F766E" if ok else "#D2553F")
      body.append(pp)
      xx += pw + 4
    body.append(k.text(cols["asil"], y + 17, k.clip(str(v.get("asil", "")), 74, 10), 10, k.INK2, 600))
    tsr = [t for t in sysml_lite._as_list(v.get("tsr")) if t]
    body.append(k.text(cols["tsr"], y + 17, k.clip(", ".join(t[4:] for t in tsr), cols["tests"] - cols["tsr"] - 10, 10, 400, True),
                       10, k.INK2, 400, None, True))
    tests = [t for t in sysml_lite._as_list(v.get("tests")) if t]
    body.append(k.text(cols["tests"], y + 17, f"{len(tests)} case{'s' if len(tests) != 1 else ''}", 10, k.MUTED))
    y += rh
  n = len(m.signals)
  body.append(k.text(40, y + 22, f"{n} signals: {no_int} carry no checksum, CRC or XOR of their own and {no_live} no counter, "
                     "alive check or supervision; the receiver's own checks (rates, timeouts, cross-checks) are in the Failure "
                     "reaction column of WP-S-05 §11.", 12, k.INK, 600))
  legend_y = y + 40
  p1, w1 = k.pill(40, legend_y + 21, "integrity", "#F0FDFA", "#0F766E", 16, 9, 700, "#0F766E")
  p2, w2 = k.pill(320, legend_y + 21, "no liveness", "#FEF2F2", "#D2553F", 16, 9, 700, "#D2553F")
  items = [p1, k.text(40 + w1 + 8, legend_y + 33, "checksum, CRC or XOR in the signal", 11, k.INK2),
           p2, k.text(320 + w2 + 8, legend_y + 33, "no counter, alive check or supervision of the signal (\"as S-nn\" followed)", 11, k.INK2)]
  body += rv.footer(w, legend_y, items)
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body)


RENDERERS["signals"] = render_signals


# ---------------------------------------------------------------- V-20 HSI responsibilities

STATUS_STYLE = {"in place": ("#F0FDFA", "#0F766E"), "partial": ("#FFFBEB", "#B45309"), "missing": ("#FEF2F2", "#D2553F")}


def _plain(text) -> str:
  return re.sub(r"`|\*\*", "", str(text or "")).strip()


def render_responsibilities(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  """WP-S-05 §11.4 per interface: what the hardware provides and the software must do, with their owner elements,
  who detects a failure of the other side, the reaction and the status."""
  import gen_timing_hsi
  view = m.views[vid]
  w = spec["width"]
  names = gen_timing_hsi.interfaces()
  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  cols = [("iface", 40, 210, "INTERFACE"), ("hw", 262, 330, "HARDWARE PROVIDES"), ("sw", 608, 360, "SOFTWARE MUST"),
          ("detect", 984, 228, "FAILURE DETECTED BY"), ("react", 1228, 252, "REACTION · STATUS")]
  top = 104
  for _key, x, _cw, lab in cols:
    body.append(k.text(x, top + 8, lab, 9.5, k.MUTED, 700, extra=' letter-spacing="1"'))
  y = top + 22
  size, lh = 10.5, 14
  counts = {st: 0 for st in STATUS_STYLE}
  undetected = 0
  for hsi, r in m.responsibilities.items():
    v = r.values
    status = str(v.get("status", ""))
    counts[status] = counts.get(status, 0) + 1
    detect = _plain(v.get("detection"))
    blind = detect.lower().startswith("not detected")
    undetected += blind
    shared = _plain(v.get("shared"))
    left = k.wrap(names.get(hsi, ""), 200, size, 600)
    if shared and shared != "—":
      left_shared = k.wrap("Shared: " + shared, 200, 9.5)
    else:
      left_shared = []
    cells = {"hw": k.wrap(_plain(v.get("hardware")), 330 - 8, size), "sw": k.wrap(_plain(v.get("software")), 360 - 8, size),
             "detect": k.wrap(detect, 228 - 8, size), "react": k.wrap(_plain(v.get("reaction")), 252 - 8, size)}
    rh = max(46, 40 + len(left) * lh + len(left_shared) * 13, 40 + max(len(cells[c]) for c in ("hw", "sw", "react")) * lh,
             20 + len(cells["detect"]) * lh) - 4
    body.append(k.rect(30, y, w - 60, rh, k.PAPER, k.HAIR, 6))
    p, _ = k.pill(40, y + 8, hsi, "#334155", size=9.5, mono=True)
    body.append(p)
    yy = y + 40
    for ln in left:
      body.append(k.text(40, yy, ln, size, k.INK, 600))
      yy += lh
    for ln in left_shared:
      body.append(k.text(40, yy, ln, 9.5, k.MUTED))
      yy += 13
    for key, owners_key in (("hw", "hwOwners"), ("sw", "swOwners")):
      x = next(c[1] for c in cols if c[0] == key)
      xx = x
      for o in sysml_lite._as_list(v.get(owners_key)):
        e = m.find(o)
        st = rv.style_of(e) if e is not None else k.OUTSIDE
        pp, pw = k.pill(xx, y + 8, o, "#FFFFFF", st["chip"], 16, 9, 700, st["stroke"], mono=True)
        body.append(pp)
        xx += pw + 4
      yy = y + 40
      for ln in cells[key]:
        body.append(k.text(x, yy, ln, size, k.INK2))
        yy += lh
    x = next(c[1] for c in cols if c[0] == "detect")
    yy = y + 20
    for ln in cells["detect"]:
      body.append(k.text(x, yy, ln, size, "#D2553F" if blind else k.INK2, 600 if blind else 400))
      yy += lh
    x = next(c[1] for c in cols if c[0] == "react")
    fill, color = STATUS_STYLE.get(status, (k.WASH, k.MUTED))
    pp, _ = k.pill(x, y + 8, status, fill, color, 16, 9, 700, color)
    body.append(pp)
    yy = y + 40
    for ln in cells["react"]:
      body.append(k.text(x, yy, ln, size, k.INK2))
      yy += lh
    y += rh + 6
  n = len(m.responsibilities)
  body.append(k.text(40, y + 22, f"{n} interfaces: {counts.get('in place', 0)} in place, {counts.get('partial', 0)} partial, "
                     f"{counts.get('missing', 0)} missing; at {undetected} a failure of the other side is not detected "
                     "today.", 12, k.INK, 600))
  legend_y = y + 40
  items = []
  xx = 40
  for st, (fill, color) in STATUS_STYLE.items():
    pp, pw = k.pill(xx, legend_y + 21, st, fill, color, 16, 9, 700, color)
    items.append(pp)
    xx += pw + 10
  items.append(k.text(xx + 6, legend_y + 33, "status of the row in WP-S-05 §11.4; owner chips are coloured by the "
                      "element's integrity, as in V-03", 11, k.INK2))
  body += rv.footer(w, legend_y, items)
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body)


RENDERERS["responsibilities"] = render_responsibilities

# ---------------------------------------------------------------- V-23 life cycle of an installed item

LC_STATUS = {"defined": ("procedure defined", "#334155", "#F8FAFC"), "waiting": ("waiting on an input", "#B45309", "#FFFBEB"),
             "blocked": ("blocked by a design gap", "#D2553F", "#FEF2F2"), "design": ("backed by the design", "#0F766E", "#F0FDFA")}


def lc_step(x: float, y: float, w: float, st: sysml_lite.Record, m: sysml_lite.Model) -> list[str]:
  """One procedure step: the TSR it carries, its ASIL and status, the requirement, the steps and record that carry it,
  and the cases that verify the TSR."""
  v = st.values
  label, col, bg = LC_STATUS[str(v.get("status"))]
  out = [k.rect(x, y, w, LC_H, bg, col, 10, 1.3), k.rect(x, y + 6, 4, LC_H - 12, col, None, 2)]
  p, pw = k.pill(x + 12, y + 8, str(v.get("tsr")), col, "#FFFFFF", 17, 9.5, 700, mono=True)
  out.append(p)
  out.append(k.text(x + 18 + pw, y + 21, f"ASIL {v.get('asil')}", 10, k.INK2, 600))
  out.append(k.text(x + w - 10, y + 21, label, 9.5, col, 700, "end"))
  for i, ln in enumerate(k.wrap(st.doc, w - 24, 10.5, 400)[:2]):
    if i == 1 and len(k.wrap(st.doc, w - 24, 10.5, 400)) > 2:
      ln = k.clip(ln + " …", w - 24, 10.5)
    out.append(k.text(x + 12, y + 39 + i * 13, ln, 10.5, k.INK))
  r = m.requirements.get(str(v.get("tsr")))
  cases = ", ".join(c.replace("VS-", "") for c in sorted(r.verified_by)) if r and r.verified_by else "no case"
  out.append(k.text(x + 12, y + LC_H - 9, k.clip(f"by {v.get('steps')} · record {v.get('record')} · «verify» {cases}",
                                                 w - 24, 9, 400, True), 9, k.MUTED, 400, None, True))
  return out


LC_H, LC_GAP, LC_HEAD = 76, 8, 46


def render_lifecycle(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  """An action flow diagram of the life of an installed item: start, the phases as actions with the procedure steps
  they contain, the successions between them, done."""
  view = m.views[vid]
  w = spec["width"]
  act = m.activities[spec["activity"]]
  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  steps = act.steps
  # columns: the first phase, the hub it leads to, the phases reached from the hub; the phase that leads to done sits
  # under the hub
  first = next(b for a, b in act.flows if a == "start")
  hub = next(b for a, b in act.flows if a == first)
  last = next(a for a, b in act.flows if b == "done")
  side = [p.name for p in act.phases if p.name not in (first, hub, last)]
  cw, top = 400, 132
  col_x = {first: 100, hub: 100 + cw + 72}
  x3 = col_x[hub] + cw + 100
  boxes = {}

  def height(ph: str) -> float:
    return LC_HEAD + len(steps[ph]) * (LC_H + LC_GAP) + 6

  boxes[first] = (col_x[first], top, cw, height(first))
  boxes[hub] = (col_x[hub], top, cw, height(hub))
  boxes[last] = (col_x[hub], top + height(hub) + 84, cw, height(last))
  y3 = top
  for ph in side:
    boxes[ph] = (x3, y3, cw, height(ph))
    y3 += height(ph) + 84
  phase_of = {p.name: p for p in act.phases}
  for ph, (x, y, bw, bh) in boxes.items():
    p = phase_of[ph]
    body.append(k.rect(x, y, bw, bh, "#FFFFFF", k.INK2, 18, 1.6))
    body.append(k.text(x + 16, y + 20, f"§{p.short} {p.doc}", 12.5, k.INK, 700))
    body.append(k.text(x + 16, y + 36, k.clip(f"action {ph} : LifecyclePhase · {len(steps[ph])} procedure steps",
                                              bw - 32, 9.5, 400, True), 9.5, k.MUTED, 400, None, True))
    for i, st in enumerate(steps[ph]):
      body += lc_step(x + 12, y + LC_HEAD + i * (LC_H + LC_GAP), bw - 24, st, m)
  # start and done
  fx, fy, fw, fh = boxes[first]
  sx, sy = fx - 52, fy + 24
  body.append(f'<circle cx="{k.f(sx)}" cy="{k.f(sy)}" r="9" fill="{k.INK}"/>')
  body.append(k.text(sx, sy - 16, "start", 10, k.INK2, 600, "middle"))
  arrows = [[(sx + 9, sy), (fx, sy)]]
  lx, ly, lw_, lh = boxes[last]
  dx, dy = lx + lw_ / 2, ly + lh + 46
  body.append(f'<circle cx="{k.f(dx)}" cy="{k.f(dy)}" r="11" fill="none" stroke="{k.INK}" stroke-width="1.6"/>'
              f'<circle cx="{k.f(dx)}" cy="{k.f(dy)}" r="6.5" fill="{k.INK}"/>')
  body.append(k.text(dx + 20, dy + 4, "done", 10, k.INK2, 600))
  arrows.append([(dx, ly + lh), (dx, dy - 11)])
  hx, hy, hw, hh = boxes[hub]
  arrows.append([(fx + fw, hy + 24), (hx, hy + 24)])                     # first -> hub
  arrows.append([(hx + hw / 2, hy + hh), (hx + hw / 2, ly)])            # hub -> last
  # hub <-> each side phase: out on an outer lane, back on an inner one, so the routes do not cross
  for i, ph in enumerate(side):
    bx, by, _, bh = boxes[ph]
    if by < hy + hh - 40:                                              # beside the hub: two straight arrows
      y_out, y_back = by + 30 + 0, by + 52
      arrows.append([(hx + hw, y_out), (bx, y_out)])
      arrows.append([(bx, y_back), (hx + hw, y_back)])
    else:                                                              # below: route through the gap
      lane_out, lane_back = hx + hw + 66, hx + hw + 34
      y_hub_out, y_hub_back = hy + hh - 46, hy + hh - 22
      arrows.append([(hx + hw, y_hub_out), (lane_out, y_hub_out), (lane_out, by + 30), (bx, by + 30)])
      arrows.append([(bx, by + 56), (lane_back, by + 56), (lane_back, y_hub_back), (hx + hw, y_hub_back)])
  for pts in arrows:
    body.append(f'<path d="{k.rounded_path(pts)}" fill="none" stroke="{k.INK2}" stroke-width="1.5" '
                'marker-end="url(#lc-arrow)"/>')
  bottom = max(max(y + h for _, y, _, h in boxes.values()), dy + 12) + 18
  from render_requirements import sysml_frame
  body += sysml_frame(24, 100, w - 48, bottom - 100, "act", "LionDriverLifecycle", act.name)
  allr = [st for v in steps.values() for st in v]
  count = {s_: sum(str(st.values.get("status")) == s_ for st in allr) for s_ in LC_STATUS}
  note = (f"{len(allr)} procedure steps, one per production or operation requirement: {count['defined']} defined, "
          f"{count['waiting']} waiting on an input, {count['blocked']} blocked by a design gap, {count['design']} backed by "
          "the design. Each arrow is a succession of the model; operation returns from service and from an update.")
  for i, ln in enumerate(k.wrap(note, w - 80, 11.5)):
    body.append(k.text(40, bottom + 26 + i * 16, ln, 11.5, k.INK2))
  legend_y = bottom + 26 + 16 * len(k.wrap(note, w - 80, 11.5))
  items, lx_ = [], 40
  for s_, (label, col, bg) in LC_STATUS.items():
    items.append(k.rect(lx_, legend_y + 22, 18, 14, bg, col, 4, 1.4))
    items.append(k.text(lx_ + 24, legend_y + 33, label, 11, k.INK2))
    lx_ += 40 + k.text_w(label, 11)
  items.append(f'<circle cx="{k.f(lx_ + 8)}" cy="{k.f(legend_y + 29)}" r="6" fill="{k.INK}"/>')
  items.append(k.text(lx_ + 20, legend_y + 33, "start", 11, k.INK2))
  lx_ += 70
  items.append(f'<circle cx="{k.f(lx_ + 8)}" cy="{k.f(legend_y + 29)}" r="7" fill="none" stroke="{k.INK}" stroke-width="1.4"/>'
               f'<circle cx="{k.f(lx_ + 8)}" cy="{k.f(legend_y + 29)}" r="4" fill="{k.INK}"/>')
  items.append(k.text(lx_ + 22, legend_y + 33, "done", 11, k.INK2))
  body += rv.footer(w, legend_y, items)
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body, k.arrow_marker("lc-arrow", k.INK2, 7))


RENDERERS["activity"] = render_lifecycle

# ---------------------------------------------------------------- V-24 HSI internal block diagram

HSI_STATUS = {"in place": ("#0F766E", "#F0FDFA"), "partial": ("#B45309", "#FFFBEB"), "missing": ("#D2553F", "#FEF2F2")}


def render_hsi_ibd(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  """Internal block diagram of the hardware-software interface of the safety MCU: the firmware parts and the SoC
  software above, the parts of the MCU hardware (E-04a) below, one connector per interface HSI-nn of WP-S-05 crossing
  the boundary between them, and the parts outside the MCU each hardware part leads to."""
  view = m.views[vid]
  w = spec["width"]
  order = [h for g in spec["groups"] for h in g["hsi"]]
  missing = sorted(set(m.responsibilities) - set(order))
  if missing or len(order) != len(set(order)) or set(order) - set(m.responsibilities):
    raise sysml_lite.ModelError(f"layout.toml {vid}: groups must list each HSI of the model once (missing {missing})")
  rs = {h: m.responsibilities[h] for h in order}
  lst = sysml_lite._as_list

  def vals(h, key):
    return [x for x in lst(rs[h].values.get(key)) if x]

  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  x0, n = 56, len(order)
  cw = (w - 2 * x0) / n
  cx = {h: x0 + cw * (i + 0.5) for i, h in enumerate(order)}
  base_sw = "E-03b"
  y_up, up_h, y_sw, sw_h = 150, 40, 222, 44
  y_if, if_h = 334, 116
  y_hw, part_y, part_h = 492, 504, 46
  hw_bottom = part_y + part_h + 44
  # software owners above E-03b: one box per owner over the interfaces it owns; a shared column is split
  uppers = {}
  for h in order:
    for o in vals(h, "swOwners"):
      if o != base_sw:
        uppers.setdefault(o, []).append(h)
  spans = []
  for o, hs in uppers.items():
    spans.append([cx[hs[0]] - cw / 2 + 4, cx[hs[-1]] + cw / 2 - 4, o, hs])
  spans.sort()
  for a, b in zip(spans, spans[1:], strict=False):
    if a[1] > b[0]:
      shared = next(h for h in b[3] if h in a[3])
      a[1], b[0] = cx[shared] - 3, cx[shared] + 3
  for left, right, o, hs in spans:
    e = sysml_lite_find(m, o)
    st = rv.style_of(e) if e else k.SLATE
    body.append(k.rect(left, y_up, right - left, up_h, st["fill"], st["stroke"], 6, 1.4))
    body.append(k.text(left + 8, y_up + 16, "«part»", 9, k.MUTED))
    body.append(k.text(left + 8, y_up + 31, k.clip(element_label(e) if e else o, right - left - 16, 11, 700), 11, k.INK, 700))
  e3 = m.find(base_sw)
  st3 = rv.style_of(e3)
  body.append(k.rect(x0 + 4, y_sw, w - 2 * x0 - 8, sw_h, st3["fill"], st3["stroke"], 6, 1.6))
  body.append(k.text(x0 + 14, y_sw + 17, "«part»", 9, k.MUTED))
  body.append(k.text(x0 + 14, y_sw + 33, f"{element_label(e3)} : PlatformFirmware · ASIL C · drivers, comms, "
                     "fault handling, bootstub", 11.5, k.INK, 700))
  lines = []
  for h in order:
    at = [o for o, hs in uppers.items() if h in hs]
    for i, o in enumerate(at):
      dx = (i - (len(at) - 1) / 2) * 22
      lines.append((cx[h] + dx, y_sw, cx[h] + dx, y_up + up_h))
    if base_sw in vals(h, "swOwners"):
      lines.append((cx[h], y_if, cx[h], y_sw + sw_h))
  # the boundary and the interfaces on it
  body.append(f'<line x1="{k.f(x0 - 30)}" y1="{k.f(y_if - 22)}" x2="{k.f(w - x0 + 30)}" y2="{k.f(y_if - 22)}" '
              f'stroke="{k.FAINT}" stroke-width="1.2" stroke-dasharray="6 4"/>')
  body.append(k.text(x0 - 26, y_if - 28, "SOFTWARE ↑", 9.5, k.MUTED, 700))
  body.append(k.text(x0 - 26, y_if - 8, "HARDWARE ↓", 9.5, k.MUTED, 700))
  undetected = []
  for gi, g in enumerate(spec["groups"]):
    if gi:
      xs = cx[g["hsi"][0]] - cw / 2
      body.append(f'<line x1="{k.f(xs)}" y1="{k.f(y_if - 8)}" x2="{k.f(xs)}" y2="{k.f(y_if + if_h + 8)}" stroke="{k.HAIR}" '
                  'stroke-width="1.4"/>')
  for h in order:
    v = rs[h].values
    col, bg = HSI_STATUS.get(str(v.get("status")), (k.INK2, k.WASH))
    x = cx[h] - cw / 2 + 5
    bw = cw - 10
    body.append(k.rect(x, y_if, bw, if_h, bg, col, 8, 1.4))
    p, pw = k.pill(x + 6, y_if + 7, h, col, "#FFFFFF", 16, 9, 700, mono=True)
    body.append(p)
    for i, ln in enumerate(k.wrap(rs[h].doc, bw - 12, 9.5, 600)[:3]):
      body.append(k.text(x + 6, y_if + 38 + i * 12, ln, 9.5, k.INK, 600))
    ntsr = len(vals(h, "tsr"))
    body.append(k.text(x + 6, y_if + if_h - 30, f"{ntsr} TSR{'s' if ntsr != 1 else ''}", 9, k.INK2))
    det = str(v.get("detection", ""))
    nd = det.lower().startswith("not detected")
    if nd:
      undetected.append(h)
    label = "not detected" if nd else ("HW + SW" if "HW" in det and "SW" in det else "HW detects" if "HW" in det else "SW detects")
    body.append(k.text(x + 6, y_if + if_h - 14, label, 9, "#D2553F" if nd else k.MUTED, 700 if nd else 400))
  # the MCU hardware and its parts, ordered by the interfaces that use them
  mcu = m.find("E-04a")
  stm = rv.style_of(mcu)
  body.append(k.rect(x0 + 4, y_hw, w - 2 * x0 - 8, hw_bottom - y_hw, stm["fill"], stm["stroke"], 8, 1.6))
  users = {}
  for h in order:
    for p_ in vals(h, "hwParts"):
      users.setdefault(p_, []).append(h)
  parts = sorted(users, key=lambda p_: sum(cx[h] for h in users[p_]) / len(users[p_]))
  pw_ = (w - 2 * x0 - 28) / len(parts)
  px = {p_: x0 + 14 + i * pw_ + pw_ / 2 for i, p_ in enumerate(parts)}
  for p_ in parts:
    title = {"spi4": "SPI4 + DMA", "fdcanPeripherals": "FDCAN1–3", "iwdg1": "IWDG1 watchdog", "sirenPath": "siren path",
             "memories": "memories, flash"}.get(p_, p_)
    body.append(k.rect(px[p_] - pw_ / 2 + 4, part_y, pw_ - 8, part_h, "#FFFFFF", stm["stroke"], 5, 1.2))
    body.append(k.text(px[p_], part_y + 19, title, 10.5, k.INK, 700, "middle"))
    sub = ", ".join(h if i == 0 else h[4:] for i, h in enumerate(sorted(users[p_])))
    body.append(k.text(px[p_], part_y + 34, k.clip(sub, pw_ - 16, 8.5, 400, True), 8.5, k.MUTED, 400, "middle", True))
    for h in users[p_]:
      lines.append((cx[h], y_if + if_h, px[p_], part_y))
  for x1, y1, x2, y2 in lines:
    body.append(f'<line x1="{k.f(x1)}" y1="{k.f(y1)}" x2="{k.f(x2)}" y2="{k.f(y2)}" stroke="{k.INK2}" stroke-width="1.2"/>')
  # what an interface leads to outside the MCU (its other hardware owners, and the peers of the layout), drawn from
  # the part its resource names first
  peers_of = {h: [o for o in vals(h, "hwOwners") if o != "E-04a"] + [spec.get("peers", {}).get(h)] for h in order}
  edges = []
  for h in order:
    for o in (x for x in peers_of[h] if x):
      for p_ in vals(h, "hwParts")[:1]:
        if (p_, o) not in edges:
          edges.append((p_, o))
  # the part's name in the strip under its parts, in the widest gap between the ports
  title = f"«part» {element_label(mcu)} : SafetyMcuHardware · ASIL C"
  stops = sorted([x0 + 4, w - x0 - 4] + [px[p_] for p_, _ in edges])
  a, b = max(zip(stops, stops[1:], strict=False), key=lambda ab: ab[1] - ab[0])
  body.append(k.text((a + b) / 2, hw_bottom - 15, title, 11.5, k.INK, 700, "middle"))
  peer_ids = list(dict.fromkeys(o for _, o in edges))
  peer_x = {o: sum(px[p_] for p_, oo in edges if oo == o) / sum(1 for _, oo in edges if oo == o) for o in peer_ids}
  pbw = 230
  placed = sorted(peer_ids, key=lambda o: peer_x[o])
  for a, b in zip(placed, placed[1:], strict=False):
    if peer_x[b] - peer_x[a] < pbw + 20:
      peer_x[b] = peer_x[a] + pbw + 20
  for o in placed:
    peer_x[o] = min(max(peer_x[o], x0 + pbw / 2), w - x0 - pbw / 2)
  edges.sort(key=lambda e_: (px[e_[0]]))
  lane0 = hw_bottom + 14
  y_peer = lane0 + 9 * len(edges) + 16
  for i, (p_, o) in enumerate(edges):
    ly = lane0 + 9 * i
    k_ = [e_ for e_ in edges if e_[1] == o].index((p_, o))
    n_ = sum(1 for e_ in edges if e_[1] == o)
    tx = peer_x[o] + (k_ - (n_ - 1) / 2) * 14
    body.append(f'<rect x="{k.f(px[p_] - 4)}" y="{k.f(hw_bottom - 4)}" width="8" height="8" fill="#FFFFFF" '
                f'stroke="{k.INK2}" stroke-width="1.2"/>')
    body.append(f'<path d="{k.rounded_path([(px[p_], part_y + part_h), (px[p_], ly), (tx, ly), (tx, y_peer)], 5)}" '
                f'fill="none" stroke="{k.INK2}" stroke-width="1.2"/>')
  for o in placed:
    e = sysml_lite_find(m, o)
    st = rv.style_of(e) if e else k.OUTSIDE
    x = peer_x[o] - pbw / 2
    body.append(k.rect(x, y_peer, pbw, 40, st["fill"], st["stroke"], 6, 1.4))
    body.append(k.text(x + 8, y_peer + 15, "«part»", 9, k.MUTED))
    body.append(k.text(x + 8, y_peer + 30, k.clip(element_label(e) if e else o, pbw - 16, 11, 700), 11, k.INK, 700))
  bottom = y_peer + 58
  from render_requirements import sysml_frame
  body += sysml_frame(24, 100, w - 48, bottom - 100, "ibd", "LionDriverArchitecture", "safety MCU hardware-software interface")
  count = {s_: sum(str(r.values.get("status")) == s_ for r in rs.values()) for s_ in HSI_STATUS}
  note = (f"{n} interfaces cross the boundary between the firmware and the MCU hardware: {count['in place']} in place, "
          f"{count['partial']} partial, {count['missing']} missing (WP-S-05 §11.4). At {len(undetected)} ({', '.join(undetected)}) "
          "a failure of the other side is not detected today. Each line is a connection of the model: an interface to the software "
          "that owns it (WP-S-05 §11.4) and to the hardware parts its resource names (§2, check H5).")
  for i, ln in enumerate(k.wrap(note, w - 80, 11.5)):
    body.append(k.text(40, bottom + 26 + i * 16, ln, 11.5, k.INK2))
  legend_y = bottom + 26 + 16 * len(k.wrap(note, w - 80, 11.5))
  items, lx_ = [], 40
  for s_, (col, bg) in HSI_STATUS.items():
    items.append(k.rect(lx_, legend_y + 22, 18, 14, bg, col, 4, 1.4))
    items.append(k.text(lx_ + 24, legend_y + 33, s_, 11, k.INK2))
    lx_ += 40 + k.text_w(s_, 11)
  items.append(f'<rect x="{k.f(lx_)}" y="{k.f(legend_y + 25)}" width="8" height="8" fill="#FFFFFF" stroke="{k.INK2}" '
               'stroke-width="1.2"/>')
  items.append(k.text(lx_ + 14, legend_y + 33, "port of E-04a to a part outside the MCU", 11, k.INK2))
  lx_ += 270
  items.append(k.text(lx_, legend_y + 33, "part colours: integrity, as in V-03", 11, k.MUTED))
  body += rv.footer(w, legend_y, items)
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body)


def sysml_lite_find(m: sysml_lite.Model, ident: str):
  """An element by short name or, for a part outside the item, by its part name."""
  e = m.find(ident)
  if e is None:
    named = [x for x in m.elements.values() if x.kind == "part" and x.name == ident]
    e = named[0] if len(named) == 1 else None
  return e


RENDERERS["hsiblocks"] = render_hsi_ibd

# ---------------------------------------------------------------- V-25 fault reaction times, parametric

PAR_VERDICT = [("not", "not met", "#D2553F", "#FEF2F2"), ("partly", "partly, or just over the budget", "#B45309", "#FFFBEB"),
               ("verify", "no derived time yet", "#64748B", "#F1F5F9"),
               ("design", "met by design in the reference build, not verified", "#1D4ED8", "#FFFFFF"),
               ("met", "met, code-derived (envelope side)", "#1D4ED8", "#EFF6FF")]


def par_cell(x: float, y: float, w: float, h: float, name: str, r: sysml_lite.Record, col: str, bg: str) -> list[str]:
  """One fault reaction time as a small parametric diagram: the constraint {time <= budget}, its two parameters bound
  to the time (latest, with the code-derived times it cites) and the budget."""
  v = r.values
  lst = sysml_lite._as_list
  out = [k.rect(x, y, w, h, bg, col, 8, 1.3)]
  out.append(k.text(x + 10, y + 18, k.clip(name, w - 120, 11.5, 700), 11.5, k.INK, 700))
  tsr = [t for t in lst(v.get("tsr")) if t]
  out.append(k.text(x + w - 10, y + 18, k.clip(", ".join(tsr), 110, 9, 400, True), 9, k.MUTED, 400, "end", True))
  bx, bw, by, bh = x + 10, 150, y + 30, 58
  cx_, cw_ = x + w / 2 - 62, 124
  rx_ = x + w - 10 - 130
  # value properties
  out.append(k.rect(bx, by, bw, bh, "#FFFFFF", k.FAINT, 4, 1.1))
  out.append(k.text(bx + 6, by + 12, "time", 8.5, k.MUTED, 600))
  for i, ln in enumerate(k.wrap(str(v.get("latest", "")), bw - 12, 9.5)[:3]):
    out.append(k.text(bx + 6, by + 25 + i * 11.5, ln, 9.5, k.INK))
  out.append(k.rect(rx_, by, 130, bh, "#FFFFFF", k.FAINT, 4, 1.1))
  out.append(k.text(rx_ + 6, by + 12, "budget", 8.5, k.MUTED, 600))
  for i, ln in enumerate(k.wrap(str(v.get("budget", "")), 118, 9.5, 600)[:3]):
    out.append(k.text(rx_ + 6, by + 25 + i * 11.5, ln, 9.5, k.INK, 600))
  # the constraint property with its two parameters, and the binding connectors
  cy = by + 6
  out.append(k.rect(cx_, cy, cw_, bh - 12, "#FFFFFF", col, 16, 1.5))
  out.append(k.text(cx_ + cw_ / 2, cy + 15, "«constraint»", 8.5, k.MUTED, 400, "middle"))
  out.append(k.text(cx_ + cw_ / 2, cy + 32, "{time ≤ budget}", 10.5, col, 700, "middle", True))
  pin_y = cy + (bh - 12) / 2
  for px_ in (cx_, cx_ + cw_):
    out.append(f'<rect x="{k.f(px_ - 4)}" y="{k.f(pin_y - 4)}" width="8" height="8" fill="#FFFFFF" stroke="{col}" '
               'stroke-width="1.3"/>')
  out.append(f'<line x1="{k.f(bx + bw)}" y1="{k.f(pin_y)}" x2="{k.f(cx_ - 4)}" y2="{k.f(pin_y)}" stroke="{k.INK2}" '
             'stroke-width="1.1"/>')
  out.append(f'<line x1="{k.f(cx_ + cw_ + 4)}" y1="{k.f(pin_y)}" x2="{k.f(rx_)}" y2="{k.f(pin_y)}" stroke="{k.INK2}" '
             'stroke-width="1.1"/>')
  # the code-derived times the time is bound to
  times = [t for t in lst(v.get("times")) if t]
  xx = bx
  out.append(k.text(xx, y + h - 12, "code:" if times else "no code-derived time", 9, k.MUTED, 600))
  xx += 34
  for t in times:
    p, pw = k.pill(xx, y + h - 24, t, "#FFFFFF", k.INK2, 16, 8.5, 700, k.FAINT, mono=True)
    out.append(p)
    xx += pw + 4
  return out


def render_reactions(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  """Parametric view of the fault reaction times of WP-S-04 §5: one constraint {time <= budget} per fault class, its
  parameters bound to the time the item takes (with the code-derived times T-nn of §4 it rests on) and to the budget,
  grouped by the verdict."""
  view = m.views[vid]
  w = spec["width"]
  body = rv.header(w, view, spec["title"], spec["subtitle"], digest)
  cols, gap, ch = 3, 12, 122
  cw = (w - 80 - 24 - (cols - 1) * gap) / cols
  y = 136
  for key, title, col, bg in PAR_VERDICT:
    rows = [(n, r) for n, r in m.reactions.items() if r.values.get("verdict") == key]
    if not rows:
      continue
    body.append(k.text(52, y + 14, f"{title[0].upper() + title[1:]} ({len(rows)})", 12, col, 700))
    y += 24
    for i, (n, r) in enumerate(rows):
      x = 52 + (i % cols) * (cw + gap)
      body += par_cell(x, y + (i // cols) * (ch + gap), cw, ch, n, r, col, bg)
    y += ((len(rows) + cols - 1) // cols) * (ch + gap) + 10
  bottom = y + 4
  from render_requirements import sysml_frame
  body += sysml_frame(24, 100, w - 48, bottom - 100, "par", "LionDriverTiming", "fault reaction times")
  count = {kk: sum(1 for r in m.reactions.values() if r.values.get("verdict") == kk) for kk, *_ in PAR_VERDICT}
  cited = {t for r in m.reactions.values() for t in sysml_lite._as_list(r.values.get("times")) if t}
  note = (f"{len(m.reactions)} fault classes: {count['not']} not met, {count['partly']} partly, {count['verify']} with no "
          f"derived time, {count['design'] + count['met']} met by design or in code. Each is a constraint of the model "
          f"bound to the time the item takes and to its budget; {len(cited)} of the {len(m.code_times)} code-derived times "
          "of §4 are cited (check H6). Nothing is measured yet (WP-S-04 §6).")
  for i, ln in enumerate(k.wrap(note, w - 80, 11.5)):
    body.append(k.text(40, bottom + 26 + i * 16, ln, 11.5, k.INK2))
  legend_y = bottom + 26 + 16 * len(k.wrap(note, w - 80, 11.5))
  items = [k.rect(40, legend_y + 20, 60, 18, "#FFFFFF", k.INK2, 9, 1.4),
           k.text(110, legend_y + 33, "constraint property: the time to react shall not exceed the budget", 11, k.INK2),
           f'<rect x="{k.f(520)}" y="{k.f(legend_y + 25)}" width="8" height="8" fill="#FFFFFF" stroke="{k.INK2}" '
           'stroke-width="1.2"/>',
           k.text(536, legend_y + 33, "parameter, bound to a value", 11, k.INK2),
           k.pill(740, legend_y + 21, "T-06a", "#FFFFFF", k.INK2, 16, 8.5, 700, k.FAINT, mono=True)[0],
           k.text(790, legend_y + 33, "code-derived time of WP-S-04 §4", 11, k.INK2)]
  body += rv.footer(w, legend_y, items)
  return k.svg_doc(w, legend_y + 92, f"{view.short}. {spec['title']} (SysML v2 view {view.name})",
                   spec.get("desc", view.doc), body)


RENDERERS["parametric"] = render_reactions

# ---------------------------------------------------------------- V-03 at phone width

def _element(m: sysml_lite.Model, ident: str) -> sysml_lite.Element:
  """An element by id or by name in the context, as V-03's layout names it."""
  e = m.find(ident) or m.elements.get(ident) or m.elements.get("context." + ident)
  if e is None:
    raise sysml_lite.ModelError(f"layout.toml V-03 phone: {ident!r} is not an element of the model")
  return e


def _node_text(spec: dict) -> dict[str, dict]:
  """Title and subtitle of each element as V-03 draws them, so that both versions say the same."""
  return {n["el"]: n for n in spec.get("node", []) if "el" in n}


def _phone_block(m: sysml_lite.Model, el: str, spec: dict, x: float, y: float, w: float) -> tuple[list[str], float]:
  """One element as a block: its id, title and integrity, its subtitle, and its parts (or its software units) as cards
  or chips."""
  e = _element(m, el)
  st = rv.style_of(e)
  ns = _node_text(spec).get(el, {})
  title = ns.get("title") or rv.Canvas.default_title(e)
  out = []
  hx = x + 12
  if e.short:
    p, pw = k.pill(hx, y + 12, e.short, st["chip"], h=18, size=10.5)
    out.append(p)
    hx += pw + 8
  out.append(k.text(hx, y + 26, title, 14, k.INK, 700))
  ip, _ = rv.integrity_pill(x + w - 12, y + 12, e, h=18, size=10)
  out.append(ip)
  yy = y + 40
  for ln in k.wrap(ns.get("sub", ""), w - 24, 11)[:3]:
    out.append(k.text(x + 12, yy + 10, ln, 11, k.MUTED))
    yy += 15
  subs = spec.get("subs", {})
  kids = [] if el in spec["phone"].get("no_parts", []) else list(e.children)
  if ns.get("list") == "units-inline":
    units = []
    for c in e.walk():
      u = (c.meta.get("Unit") or {}).get("id")
      if c is not e and u and u not in units:
        units.append(u)
    yy += 6
    cx = x + 12
    for u in units:
      p, pw = k.pill(cx, yy, u, "#FFEDD5", k.ENVELOPE["text"], 18, 9.5, 600, "#FDBA74", mono=True)
      if cx + pw > x + w - 12:
        cx, yy = x + 12, yy + 22
        p, pw = k.pill(cx, yy, u, "#FFEDD5", k.ENVELOPE["text"], 18, 9.5, 600, "#FDBA74", mono=True)
      out.append(p)
      cx += pw + 5
    yy += 24
  elif kids:
    yy += 6
    cw = (w - 24 - 8) / 2
    for i, c in enumerate(kids):
      cx, cy = x + 12 + (i % 2) * (cw + 8), yy + (i // 2) * 48
      cst = rv.style_of(c)
      out.append(k.rect(cx, cy, cw, 42, "#FFFFFF", cst["stroke"], 6, 1))
      name = rv.Canvas.default_title(c)
      out.append(k.text(cx + 8, cy + 17, k.clip(name, cw - 16, 12, 600), 12, k.INK, 600))
      key = c.short if c.short and c.short.startswith("host.") else c.name
      sub = subs.get(key, "")
      if c.integrity() == "QMBsup":
        tag = "QM · B-sup"
        out.append(k.text(cx + cw - 8, cy + 17, tag, 9, k.INK2, 700, "end"))
      out.append(k.text(cx + 8, cy + 33, k.clip(sub, cw - 16, 10.5), 10.5, k.MUTED))
    yy += -(-len(kids) // 2) * 48
  sm = rv.sm_line(e)
  if sm:
    for ln in k.wrap(sm, w - 24, 10.5, 700):
      out.append(k.text(x + 12, yy + 12, ln, 10.5, k.ENVELOPE["chip"], 700))
      yy += 15
  yy += 8
  return [k.rect(x, y, w, yy - y, st.get("fill", "#FFFFFF"), st["stroke"], 10, 1.4), *out], yy


def _phone_links(m: sysml_lite.Model, ids: list[str], labels: dict, x: float, y: float) -> tuple[list[str], float]:
  """A connector between two blocks with the interfaces it carries, coloured by edge class as in V-03."""
  out, top = [], y
  y += 6
  first = None
  for i in ids:
    conn = next(c for c in m.connections if c.interface_id == i)
    cls = rv.edge_class(conn)
    first = first or cls
    st = k.EDGE[cls]
    p, pw = k.pill(x + 34, y, i, st["color"], h=18, size=10.5, mono=True)
    out.append(p)
    out.append(k.text(x + 34 + pw + 8, y + 13, labels.get(i, ""), 11.5, k.INK2, 600))
    y += 24
  st = k.EDGE[first]
  dash = f' stroke-dasharray="{st["dash"]}"' if st["dash"] else ""
  line = (f'<line x1="{x + 16}" y1="{k.f(top - 4)}" x2="{x + 16}" y2="{k.f(y + 6)}" stroke="{st["color"]}" '
          f'stroke-width="2.4"{dash}/>')
  return [line, *out], y + 10


def render_interconnection_phone(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  """V-03 for a phone: the same elements and interfaces stacked top to bottom along the command path, from the driver
  and the road through the device's QM partition and the ASIL C envelope to the harness and the car."""
  view = m.views[vid]
  ph = spec["phone"]
  w, mx = ph["width"], 24
  bw = w - 2 * mx
  body = [k.text(mx, 38, f"{view.short} · {spec['title']}", 19, k.INK, 700)]
  y = 60
  for ln in k.wrap(ph["subtitle"], bw, 12.5):
    body.append(k.text(mx, y, ln, 12.5, k.MUTED))
    y += 17
  body.append(k.text(mx, y + 2, f"SysML v2 view LionDriverViews::{view.name} · phone layout · model {digest}", 10.5,
                     k.FAINT))
  y += 16
  body.append(f'<line x1="{mx}" y1="{y}" x2="{w - mx}" y2="{y}" stroke="{k.HAIR}"/>')
  y += 16
  labels = ph["interfaces"]
  ns = _node_text(spec)
  for step in ph["sequence"]:
    if step.startswith("IF"):
      svg, y = _phone_links(m, step.split(), labels, mx, y)
      body += svg
    elif step.startswith("band:"):
      text, style = ph["bands"][step[5:]]
      st = {"slate": k.SLATE, "envelope": k.ENVELOPE}[style]
      body.append(k.rect(mx, y, bw, 22, st["chip"], rx=4))
      body.append(k.text(mx + bw / 2, y + 15, text, 10.5, "#FFFFFF", 700, "middle", extra=' letter-spacing="0.6"'))
      y += 30
    elif step.startswith("row:"):
      els = step[4:].split()
      cw = (bw - 8 * (len(els) - 1)) / len(els)
      h = 58
      for i, el in enumerate(els):
        e = _element(m, el)
        st = rv.style_of(e)
        n = ns.get(el, {})
        cx = mx + i * (cw + 8)
        body.append(k.rect(cx, y, cw, h, st.get("fill", k.OUTSIDE["fill"]), st["stroke"], 8, 1.2,
                           "4 3" if e.scope() == "excluded" else None))
        tx = cx + 10
        if e.short and not e.short.startswith("host."):
          p, pw = k.pill(tx, y + 8, e.short, st["chip"], h=16, size=9)
          body.append(p)
          tx += pw + 6
        body.append(k.text(tx, y + 21, k.clip(n.get("title") or rv.Canvas.default_title(e), cx + cw - tx - 8, 12, 700),
                           12, k.INK, 700))
        for j, ln in enumerate(k.wrap(n.get("sub", ""), cw - 20, 10.5)[:2]):
          body.append(k.text(cx + 10, y + 37 + j * 13, ln, 10.5, k.MUTED))
      y += h + 12
    else:
      svg, y2 = _phone_block(m, step, spec, mx, y, bw)
      body += svg
      y = y2 + 12
  # legend
  y += 4
  body.append(f'<line x1="{mx}" y1="{y}" x2="{w - mx}" y2="{y}" stroke="{k.HAIR}"/>')
  y += 16
  xx = mx
  for cls in ("actuation", "ffi", "sensing", "power", "network"):
    st = k.EDGE[cls]
    lab = {"actuation": "actuation", "ffi": "SoC ↔ MCU", "sensing": "sensing, HMI", "power": "power",
           "network": "untrusted"}[cls]
    dash = f' stroke-dasharray="{st["dash"]}"' if st["dash"] else ""
    lw = 20 + 6 + k.text_w(lab, 11) + 16
    if xx + lw > w - mx:
      xx, y = mx, y + 20
    body.append(f'<line x1="{xx}" y1="{y + 9}" x2="{xx + 20}" y2="{y + 9}" stroke="{st["color"]}" stroke-width="2.4"{dash}/>')
    body.append(k.text(xx + 26, y + 13, lab, 11, k.INK2))
    xx += lw
  y += 26
  for ln in k.wrap("SM-nn: the safety mechanisms each element performs (WP-S-03 §6). The full-width V-03 shows where "
                   "each interface attaches; this layout lists them between the blocks they join.", bw, 11):
    body.append(k.text(mx, y + 10, ln, 11, k.INK2))
    y += 16
  y += 8
  body.append(k.text(mx, y + 10, rv.GENERATED, 9.5, k.FAINT))
  return k.svg_doc(w, y + 28, f"{view.short}. {spec['title']}, phone layout (SysML v2 view {view.name})",
                   ph.get("desc", spec.get("desc", view.doc)), body)


# ---------------------------------------------------------------- V-26 safety mechanisms on the architecture

def tsr_match(t: str, u: str) -> bool:
  """TSR-307(b) is on TSR-307; TSR-1xx (an interface's TSR family) covers TSR-101 to TSR-199."""
  t = t.split("(")[0]
  return t == u or (u.endswith("xx") and t.startswith(u[:-2]))


def interface_guards(m: sysml_lite.Model) -> dict[str, list[sysml_lite.Mechanism]]:
  """Per interface IF-nn, the mechanisms that implement a TSR the interface carries (@InterfaceId tsr)."""
  tsr: dict[str, set[str]] = {}
  for c in m.connections:
    if c.interface_id:
      tsr.setdefault(c.interface_id, set()).update(sysml_lite._as_list((c.meta.get("InterfaceId") or {}).get("tsr")))
  return {i: [me for me in m.mechanisms.values() if any(tsr_match(t, u) for t in me.tsr for u in ts)]
          for i, ts in tsr.items()}


def mech_chip(x: float, y: float, w: float, me: sysml_lite.Mechanism, also: list[str]) -> list[str]:
  """One mechanism in its element: the SM id coloured by DC target, its name, and the other elements performing it."""
  label, fill, color, stroke = rv.dc_style(me)
  out = []
  p, pw = k.pill(x, y + 3, me.short, fill, color, 18, 10.5, 700, stroke)
  out.append(p)
  tail = "+" + " +".join(also) if also else ""
  tw = k.text_w(tail, 10, 600) + 6 if tail else 0
  out.append(k.text(x + pw + 6, y + 16, k.clip(me.doc or me.name, w - pw - 8 - tw, 11.5), 11.5, k.INK))
  if tail:
    out.append(k.text(x + w, y + 16, tail, 10, k.MUTED, 600, "end"))
  return [f'<g data-sm="{me.short}"><title>{k.escape(f"{me.short} {me.doc} · DC {me.dc_target}")}</title>', *out, "</g>"]


def render_mechanisms(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  """The architecture top to bottom along the command path, with every safety mechanism drawn on the element that
  performs it and, on each interface, the mechanisms whose TSRs the interface carries. Phone width."""
  view = m.views[vid]
  w, mx = spec["width"], 24
  bw = w - 2 * mx
  body = [k.text(mx, 38, f"{view.short} · {spec['title']}", 19, k.INK, 700)]
  y = 60
  for ln in k.wrap(spec["subtitle"], bw, 12.5):
    body.append(k.text(mx, y, ln, 12.5, k.MUTED))
    y += 17
  body.append(k.text(mx, y + 2, f"SysML v2 view LionDriverViews::{view.name} · model {digest}", 10.5, k.FAINT))
  y += 16
  body.append(f'<line x1="{mx}" y1="{y}" x2="{w - mx}" y2="{y}" stroke="{k.HAIR}"/>')
  mechs = list(m.mechanisms.values())
  counts: dict[str, list] = {}
  for me in mechs:
    label, *style = rv.dc_style(me)
    counts.setdefault(label, [0, style])[0] += 1
  y += 14
  body.append(k.text(mx, y + 13, f"{len(mechs)} mechanisms", 13, k.INK, 700))
  xx = mx + k.text_w(f"{len(mechs)} mechanisms", 13, 700) + 12
  for label in ("high", "medium", "low", "QM", *sorted(set(counts) - {"high", "medium", "low", "QM"})):
    if label in counts:
      n, (fill, color, stroke) = counts[label]
      p, pw = k.pill(xx, y, f"{n} {label}", fill, color, 18, 10.5, 700, stroke)
      body.append(p)
      xx += pw + 6
  y += 34
  guards = interface_guards(m)
  shorts = {e.path: e.short for e in m.elements.values()}
  titles = spec.get("titles", {})
  for step in spec["sequence"]:
    if step.startswith("IF"):
      # the interfaces between the blocks above and below: a connector with the mechanisms guarding each
      ids = step.split()
      rows = []
      for i in ids:
        conn = next(c for c in m.connections if c.interface_id == i)
        rows.append((i, rv.edge_class(conn), sorted(guards.get(i, []), key=lambda me: int(me.short[3:]))))
      top, at = y, len(body)
      for i, cls, gs in rows:
        st = k.EDGE[cls]
        p, pw = k.pill(mx + 34, y + 4, i, st["color"], h=18, size=10.5, mono=True)
        body.append(p)
        body.append(k.text(mx + 34 + pw + 8, y + 17, k.clip(spec["interfaces"][i], bw - 42 - pw, 11.5), 11.5, k.INK2, 600))
        y += 26
        gx = mx + 34
        if not gs:
          body.append(k.text(gx, y + 10, "no mechanism with a TSR of this interface", 10.5, k.FAINT))
          y += 18
        for me in gs:
          label, fill, color, stroke = rv.dc_style(me)
          p, pw = k.pill(gx, y, me.short, fill, color, 18, 10, 700, stroke)
          if gx + pw > w - mx:
            gx, y = mx + 34, y + 22
            p, pw = k.pill(gx, y, me.short, fill, color, 18, 10, 700, stroke)
          body.append(f'<g data-sm="{me.short}" data-if="{i}">{p}</g>')
          gx += pw + 5
        y += 30 if gs else 6
      st = k.EDGE[rows[0][1]]
      dash = f' stroke-dasharray="{st["dash"]}"' if st["dash"] else ""
      body.insert(at, f'<line x1="{mx + 16}" y1="{k.f(top - 10)}" x2="{mx + 16}" y2="{k.f(y + 4)}" '
                  f'stroke="{st["color"]}" stroke-width="2.4"{dash}/>')
      y += 4
      continue
    if step == "vehicle":
      body.append(k.rect(mx, y, bw, 44, k.OUTSIDE["fill"], k.OUTSIDE["stroke"], 8))
      body.append(k.text(mx + 14, y + 27, spec["vehicle"], 12.5, k.INK2, 600))
      y += 56
      continue
    e = m.find(step)
    st = rv.style_of(e)
    mine = sorted((me for me in mechs if e.path in me.performers), key=lambda me: int(me.short[3:]))
    cw, nrow = bw - 24, len(mine)
    bh = 50 + nrow * 26 + 6
    block = [k.rect(mx, y, bw, bh, st.get("fill", "#FFFFFF"), st["stroke"], 10, 1.4)]
    p, pw = k.pill(mx + 12, y + 12, e.short, st["chip"], h=18, size=10.5)
    block.append(p)
    block.append(k.text(mx + 12 + pw + 8, y + 26, titles.get(e.short, rv.Canvas.default_title(e)), 14, k.INK, 700))
    ip, _ = rv.integrity_pill(w - mx - 12, y + 12, e, h=18, size=10)
    block.append(ip)
    block.append(k.text(w - mx - 12 - k.text_w(k.INTEGRITY_LABEL.get(e.integrity(), ""), 10, 700) - 22, y + 26,
                        f"{len(mine)}", 13, st["chip"], 700, "end"))
    for n, me in enumerate(mine):
      cx, cy = mx + 12, y + 44 + n * 26
      also = [shorts[p] for p in me.performers if p != e.path and p in shorts]
      block += mech_chip(cx, cy, cw, me, also)
    body.append(f'<g data-element="{e.short}">')
    body += block
    body.append("</g>")
    y += bh + 14
  # legend
  y += 4
  body.append(f'<line x1="{mx}" y1="{y}" x2="{w - mx}" y2="{y}" stroke="{k.HAIR}"/>')
  y += 14
  xx = mx
  for dc in ("high", "medium", "low", "QM"):
    fill, color = rv.DC_FILL[dc]
    p, pw = k.pill(xx, y, dc, fill, color, 18, 10)
    body.append(p)
    xx += pw + 5
  body.append(k.text(xx + 6, y + 13, "DC target of the mechanism (WP-S-03 §6)", 11, k.INK2))
  y += 28
  for ln in k.wrap("+E-nn: also performed by that element. Under an interface IF-nn: the mechanisms that implement a "
                   "TSR the interface carries, so a fault on that link is caught there.", bw, 11):
    body.append(k.text(mx, y + 10, ln, 11, k.INK2))
    y += 16
  y += 8
  body.append(k.text(mx, y + 10, rv.GENERATED, 9.5, k.FAINT))
  return k.svg_doc(w, y + 28, f"{view.short}. {spec['title']} (SysML v2 view {view.name})", spec.get("desc", view.doc), body)


RENDERERS["mechanisms"] = render_mechanisms

# ---------------------------------------------------------------- V-27 mechanism coverage per safety goal

MECH_STATUS = [("impl", "implemented", "#1D4ED8"), ("partial", "partial", "#B45309"),
               ("missing", "not there yet", "#D2553F"), ("unknown", "unknown", k.FAINT)]
GOAL_ASIL = {"C": k.ENVELOPE["chip"], "B": k.ASIL_B["chip"], "A": "#FB923C"}


def mech_status(me: sysml_lite.Mechanism) -> str:
  """The current status of a WP-S-03 §6 row: its last bold update when it has one ("New at baseline; **Partial** ...")."""
  s = str(me.values.get("status", ""))
  bold = re.findall(r"\*\*([^*]+)\*\*", s)
  s = (bold[-1] if bold else s).lower()
  if s.startswith("impl"):
    return "impl"
  if s.startswith("partial"):
    return "partial"
  if s.startswith(("new", "not met")):
    return "missing"
  return "unknown"


def goal_coverage(m: sysml_lite.Model) -> list[dict]:
  """Per safety goal, its FSRs, the mechanisms that implement a TSR derived from them, and the FSRs no mechanism stands
  behind: outside the item (an AOU), by reference to other FSRs, or a gap."""
  reqs = m.requirements
  by_tsr: dict[str, list[sysml_lite.Mechanism]] = {}
  for me in m.mechanisms.values():
    for t in me.tsr:
      by_tsr.setdefault(t.split("(")[0], []).append(me)
  children: dict[str, list[sysml_lite.Requirement]] = {}
  for r in reqs.values():
    for p in r.derived_from:
      children.setdefault(p, []).append(r)
  out = []
  for sg in sorted(s for s in reqs if s.startswith("SG-")):
    fsrs = sorted((r for r in children.get(sg, []) if r.short.startswith("FSR-")), key=lambda r: r.short)
    mechs, open_fsrs, bare = {}, [], 0
    for f in fsrs:
      found = False
      for t in (r for r in children.get(f.short, []) if r.short.startswith("TSR-")):
        bare += t.short not in by_tsr
        for me in by_tsr.get(t.short, []):
          mechs[me.short] = me
          found = True
      if not found:
        ext = re.search(r"External measure, (AOU-\w+)", f.doc)
        ref = re.match(r"(FSR-[\d.…]+) apply", f.doc)
        kind = "outside" if ext else "reference" if ref else "gap"
        open_fsrs.append((f, kind, (ext or ref).group(1) if ext or ref else None))
    out.append({"goal": reqs[sg], "fsrs": fsrs, "mechs": sorted(mechs.values(), key=lambda me: int(me.short[3:])),
                "open": open_fsrs, "bare": bare})
  return out


def render_goal_coverage(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  """One card per safety goal: the mechanisms behind it (SG -> FSR -> TSR -> SM) by status, coloured by DC target, and
  the FSRs with no mechanism behind them. Phone width."""
  view = m.views[vid]
  w, mx = spec["width"], 24
  bw = w - 2 * mx
  bx, iw = mx + 12, bw - 24
  body = [k.text(mx, 38, f"{view.short} · {spec['title']}", 19, k.INK, 700)]
  y = 60
  for ln in k.wrap(spec["subtitle"], bw, 12.5):
    body.append(k.text(mx, y, ln, 12.5, k.MUTED))
    y += 17
  body.append(k.text(mx, y + 2, f"SysML v2 view LionDriverViews::{view.name} · model {digest}", 10.5, k.FAINT))
  y += 16
  body.append(f'<line x1="{mx}" y1="{y}" x2="{w - mx}" y2="{y}" stroke="{k.HAIR}"/>')
  y += 16
  for cov in goal_coverage(m):
    g = cov["goal"]
    asil = str(g.values.get("asil", ""))
    by = {key: [me for me in cov["mechs"] if mech_status(me) == key] for key, _, _ in MECH_STATUS}
    top = y
    card = []
    p, pw = k.pill(bx, y + 12, g.short, GOAL_ASIL.get(asil, k.SLATE["chip"]), h=20, size=11)
    card.append(p)
    ap, _ = k.pill(w - mx - 12, y + 12, f"ASIL {asil}", "#FFFFFF", k.INK2, 20, 10, 700, k.FAINT, "end")
    card.append(ap)
    title = re.sub(r"^The item shall ", "", g.doc).rstrip(".")
    ty = y + 27
    for ln in k.wrap(title[:1].upper() + title[1:], iw - pw - 78, 12.5, 600)[:3]:
      card.append(k.text(bx + pw + 8, ty, ln, 12.5, k.INK, 600))
      ty += 16
    yy = max(ty, y + 44) + 4
    n = len(cov["mechs"]) or 1
    xx = bx
    for key, _, col in MECH_STATUS:
      if by[key]:
        card.append(k.rect(xx, yy, iw * len(by[key]) / n, 10, col, rx=2))
        xx += iw * len(by[key]) / n
    if not cov["mechs"]:
      card.append(k.rect(bx, yy, iw, 10, "#FFFFFF", "#D2553F", 2, 1, "3 2"))
    yy += 26
    nm = len(cov["mechs"])
    card.append(k.text(bx, yy, f"{nm} mechanism{'s' * (nm != 1)} via {len(cov['fsrs'])} FSRs", 11.5, k.INK2, 600))
    yy += 10
    for key, lab, col in MECH_STATUS:
      if not by[key]:
        continue
      yy += 8
      head = f"{lab} ({len(by[key])})"
      card.append(f'<circle cx="{k.f(bx + 4)}" cy="{k.f(yy + 9)}" r="4" fill="{col}"/>')
      card.append(k.text(bx + 14, yy + 13, head, 11, col, 700))
      gx = bx + 14 + k.text_w(head, 11, 700) + 10
      for me in by[key]:
        label, fill, color, stroke = rv.dc_style(me)
        pp, ppw = k.pill(gx, yy, me.short, fill, color, 18, 10, 700, stroke)
        if gx + ppw > w - mx - 12:
          gx, yy = bx + 14, yy + 22
          pp, ppw = k.pill(gx, yy, me.short, fill, color, 18, 10, 700, stroke)
        card.append(f'<g data-sm="{me.short}" data-goal="{g.short}" data-status="{key}">{pp}</g>')
        gx += ppw + 4
      yy += 20
    for f, kind, ref in cov["open"]:
      yy += 8
      if kind == "outside":
        note, col, bg = f"Outside the item: {ref} (the car's own systems). " + f.doc.split("(External")[0], k.MUTED, k.WASH
      elif kind == "reference":
        note, col, bg = f"Shares the mechanisms of {ref} by reference; no TSR of its own.", k.MUTED, k.WASH
      else:
        note, col, bg = "No mechanism yet. " + f.doc, "#D2553F", "#FEF2F2"
      lines = k.wrap(note, iw - 100, 11)
      if len(lines) > 2:
        lines = [lines[0], k.clip(lines[1] + " …", iw - 100, 11)]
      hh = 12 + 15 * len(lines)
      card.append(f'<g data-fsr="{f.short}" data-kind="{kind}">')
      card.append(k.rect(bx, yy, iw, hh, bg, col, 6, 1))
      card.append(k.text(bx + 10, yy + 18, f.short, 11, col, 700, mono=True))
      for i, ln in enumerate(lines):
        card.append(k.text(bx + 90, yy + 18 + 15 * i, ln, 11, k.INK2))
      card.append("</g>")
      yy += hh
    yy += 10
    card.append(k.text(bx, yy + 8, f"{cov['bare']} of its TSRs name no mechanism (met by design, test or the driver)",
                       10.5, k.MUTED))
    yy += 18
    body.append(f'<g data-goal="{g.short}">')
    body.append(k.rect(mx, top, bw, yy - top, "#FFFFFF", k.HAIR, 10, 1.2))
    body += card
    body.append("</g>")
    y = yy + 14
  # legend
  y += 2
  xx = mx
  for _, lab, col in MECH_STATUS[:3]:
    body.append(f'<circle cx="{xx + 5}" cy="{y + 9}" r="5" fill="{col}"/>')
    body.append(k.text(xx + 14, y + 13, lab, 11, k.INK2))
    xx += 14 + k.text_w(lab, 11) + 18
  body.append(k.text(xx, y + 13, "status in WP-S-03 §6", 11, k.MUTED))
  y += 26
  xx = mx
  for dc in ("high", "medium", "low", "QM"):
    fill, color = rv.DC_FILL[dc]
    p, pw = k.pill(xx, y, dc, fill, color, 18, 10)
    body.append(p)
    xx += pw + 5
  body.append(k.text(xx + 6, y + 13, "chip colour: DC target", 11, k.INK2))
  y += 28
  for ln in k.wrap("Red: an FSR with no mechanism behind it yet. Grey: met outside the item (an AOU) or by reference "
                   "to other FSRs.", bw, 11):
    body.append(k.text(mx, y + 10, ln, 11, k.INK2))
    y += 16
  y += 8
  body.append(k.text(mx, y + 10, rv.GENERATED, 9.5, k.FAINT))
  return k.svg_doc(w, y + 28, f"{view.short}. {spec['title']} (SysML v2 view {view.name})", spec.get("desc", view.doc), body)


RENDERERS["coverage"] = render_goal_coverage
