"""Renderers of the architecture views added with the MBSE extension (README §6, OI-10).

  V-10 functional architecture   the functions F-01 to F-09 along their functional chain, each step on the element
                                 that performs it (LionDriverFunctions, perform statements)

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
