#!/usr/bin/env python3
"""Draw the System FMEA failure-mode cards (fmea-plan Figure 3-17, three sheets) from analyses/system-fmea.yaml.

One card per failure mode SFM-nnn. Each card shows:

- the failure mode, its severity, the WP-C-03 hazards of its end effects (through hara-mapping.yaml), its guide word and
  how many of its causes are rated AP H;
- the effect chain local → next higher level → end effect, lighting up in turn;
- a looping road scene of the end effect (SMIL, 6 s; a still viewer shows the end pose);
- every cause with three 1–10 meters: occurrence, detection and FMEA-MSR monitoring, coloured by the M table of
  rating-tables §7.3 and DQ-206 A: green for M 1–4 (within the FTTI on measured timing, the only band that can close a
  cause), amber for M 5–7 (targets the cause, FTTI met on code-derived timing only, or untimed), red for M 8–10 (late, not
  designed for this cause, or none), grey where the cause has no MSR rating; then its AP and its MSR AP;
- the actions of its causes, with their status. A completed action with a predicted (`revised`) rating that none of its
  linked causes has reached (or bettered) yet reads "completed, not yet credited": its effect waits for the next baseline's re-rating;
- where it sits in the fault trees of WP-A-04: per goal, the basic events (red if a single point) and gates whose FMEA
  backing it is in fta-fmea-map.yaml, or that the map lists it outside the tree (justified, or a tree gap). Read through
  assurance/08-analyses/figures/fta_fmea_figures.backlinks(), so a tree or map change asks for a regeneration here too.

Everything on a card is read from the YAML except the scene, which is chosen per failure mode below. The build fails if
a failure mode has no scene or sheet, a scene or sheet names one that is not in the YAML, a hazard is not mapped or an
action does not exist. Long texts are cut with "…" on the card and given in full in the figure's text description.

Each sheet comes twice: fig-3-17-sfm-cards-<n>.svg in the original style, the figure of record, and
fig-3-17-sfm-cards-<n>-cards.svg in the card style of the FMEA and fault tree card views (FMEA_FIG_STYLE=cards, drawn
in a second process because the palette is fixed when fmea_diagrams is imported).

    python3 tools/safety/fmea_cards.py            # regenerate the SVGs
    python3 tools/safety/fmea_cards.py --check    # fail if the YAML disagrees or an SVG is stale

Standard library only (the YAML is read with fmea_diagrams' loader). Output is deterministic.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
for p in ("assurance/08-analyses/figures", "assurance/02-concept/sotif", "assurance/02-concept/hara"):
  sys.path.insert(0, str(ROOT / p))
import fmea_diagrams as fd  # the FMEA's own stdlib YAML loader
import fta_fmea_figures as ff  # FMEA failure mode -> fault-tree events, from fta-fmea-map.yaml
import stpa_ls_scenes as ls  # road scenes, shared with the STPA loss scenario cards
from hara_figures import HAIR as _HAIR, INK as _INK, MUTED as _MUTED, header as _header, pill, svg_doc, t, text_w, wrap  # noqa: E402

# Two styles, as in fmea_diagrams.py: the original cards are the figure of record (fig-3-17-sfm-cards-<n>.svg); the
# card style of the FMEA and fault tree card views is a second version (…-cards.svg), drawn when FMEA_FIG_STYLE=cards.
CARDS = fd.CARDS
if CARDS:
  INK, MUTED, HAIR, LINE, SOFT, BG = fd.INK, fd.MUTED, fd.GRID, fd.LINE, fd.SOFT, fd.BG
else:
  INK, MUTED, HAIR, LINE, SOFT, BG = _INK, _MUTED, _HAIR, "#94A3B8", "#F1F5F9", "#FFFFFF"
DOTS = '<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1.2" cy="1.2" r="1.2" fill="#E7E6E0"/></pattern>'


def header(w, title, subtitle, ref1, ref2):
  if not CARDS:
    return _header(w, title, subtitle, ref1, ref2)
  return [t(40, 44, title, 20, INK, 700), t(40, 66, subtitle, 12.5, MUTED),
          t(w - 40, 44, ref1, 11, MUTED, None, "end"), t(w - 40, 62, ref2, 11, MUTED, None, "end"),
          f'<line x1="40" y1="82" x2="{w - 40}" y2="82" stroke="{HAIR}"/>']

OUT = fd.FMEA_DIR / "figures" / "cards"
MAPPING = fd.FMEA_DIR / "hara-mapping.yaml"


class CardError(Exception):
  pass


SHEETS = {  # file -> (figure, title, failure modes in card order)
  "fig-3-17-sfm-cards-1.svg": ("3-17a", "lateral and longitudinal control",
                               ["SFM-001", "SFM-002", "SFM-003", "SFM-004", "SFM-005", "SFM-006", "SFM-007", "SFM-038",
                                "SFM-008", "SFM-009", "SFM-010", "SFM-011", "SFM-012", "SFM-037"]),
  "fig-3-17-sfm-cards-2.svg": ("3-17b", "engagement, disengagement, driver monitoring and alerts",
                               ["SFM-013", "SFM-014", "SFM-015", "SFM-016", "SFM-017", "SFM-018", "SFM-019", "SFM-020",
                                "SFM-021", "SFM-022", "SFM-023", "SFM-024", "SFM-025", "SFM-026", "SFM-027", "SFM-028"]),
  "fig-3-17-sfm-cards-3.svg": ("3-17c", "limits, configuration and the stock functions",
                               ["SFM-029", "SFM-030", "SFM-031", "SFM-032", "SFM-033", "SFM-034", "SFM-035", "SFM-036"]),
}
SCENE = {  # failure mode -> (scene kind, first tag, second tag); a drawing of the end effect, not data
  "SFM-001": ("steer", "not engaged", "wheel turns"), "SFM-002": ("lane", "torque above limit", "jerks off line"),
  "SFM-003": ("lane", "steers the wrong way", "toward the line"), "SFM-004": ("curve", "too little steering", "drifts wide"),
  "SFM-005": ("fault", "steering lost", "no alert"), "SFM-006": ("curve", "command frozen", "leaves the lane"),
  "SFM-007": ("lane", "oscillating", "weaves"), "SFM-038": ("fault", "lateral fault", "warning late"),
  "SFM-008": ("accel", "unintended", "accelerates"), "SFM-009": ("phantom", "phantom braking", "hard brake"),
  "SFM-010": ("late", "too little braking", "closes on lead"), "SFM-011": ("late", "braking lost", "no alert"),
  "SFM-012": ("late", "lead brakes", "reacts late"), "SFM-037": ("late", "command frozen", "no braking"),
  "SFM-013": ("resume", "engages unasked", "item takes over"), "SFM-014": ("fault", "fault, still engaged", "keeps control"),
  "SFM-015": ("fault", "drops out", "no alert"), "SFM-016": ("fault", "fault", "disengages late"),
  "SFM-017": ("accel", "driver brakes", "still engaged"), "SFM-018": ("steer", "driver steers", "item resists"),
  "SFM-019": ("straight", "cancel pressed", "still engaged"), "SFM-020": ("straight", "driver accelerates", "not honoured"),
  "SFM-021": ("straight", "item off", "stock cruise on"), "SFM-022": ("straight", "driver looks away", "not detected"),
  "SFM-023": ("straight", "distracted", "escalates slowly"), "SFM-024": ("straight", "attentive driver", "false alerts"),
  "SFM-025": ("straight", "driver unresponsive", "still engaged"), "SFM-026": ("fault", "take-over needed", "no alert"),
  "SFM-027": ("late", "alert late", "driver late"), "SFM-028": ("straight", "shows engaged", "is not"),
  "SFM-029": ("lane", "limits not enforced", "excess torque"), "SFM-030": ("lane", "excess actuation", "not detected"),
  "SFM-031": ("straight", "normal driving", "false alarm"), "SFM-032": ("lane", "wrong car profile", "wrong limits"),
  "SFM-033": ("pcs", "stock PCS degraded", "no stock braking"), "SFM-034": ("pcs", "switch stuck", "stock cut off"),
  "SFM-035": ("pcs", "frame alters PCS", "stock braking off"), "SFM-036": ("pcs", "PCS brakes", "item accelerates"),
}
CW, GAP, M, COLS = 400, 20, 40, 3
PW = CW - 24
STEP = [MUTED, "#B45309", fd.RED] if CARDS else ["#475569", "#B45309", "#DC2626"]
LEVELS = (("local", "Local"), ("next_higher", "Next level"), ("end", "End effect"))
if CARDS:
  ACT_C = {st: fd.ACTION_TINT[st][:2] for st in ("open", "in_progress", "completed")}
else:
  ACT_C = {"open": ("#FEE2E2", "#7F1D1D"), "in_progress": ("#FEF3C7", "#78350F"), "completed": ("#DCFCE7", "#14532D")}
ACT_C["completed, not yet credited"] = ("#ECFCCB", "#3F6212")
AP_C = {"H": "#DC2626", "M": "#D97706", "L": "#0F766E"}   # original style


def monitoring(m):
  """Colour and legend of an M rating (rating-tables §7.3, DQ-206 A: only measured timing, M 1–4, can close a cause)."""
  if m is None:
    return "#94A3B8", "no MSR rating"
  if m <= 4:
    return "#16A34A", "within FTTI, measured"
  if m <= 7:
    return "#D97706", "targets the cause; code-derived timing or untimed"
  return "#DC2626", "late, not designed for this cause, or none"


def cut(text, width, size, n, bold=False):
  ls_ = wrap(text, width, size, bold)
  return ls_[:n - 1] + [ls_[n - 1] + " …"] if len(ls_) > n else ls_


def load():
  doc = fd.load_analyses()["system-fmea"]
  mapping = {h["second"]: h["wp_c03"] for h in fd.load_yaml(MAPPING.read_text(encoding="utf-8"))["hazards"]}
  return doc, mapping


def cards(doc, mapping, links=None):
  links = ff.backlinks() if links is None else links
  fms = {f["id"]: f for f in doc["failure_modes"]}
  acts = {a["id"]: a["status"] for a in doc["actions"]}
  linked = {}  # action -> [(occurrence, detection)] of every cause that names it
  for f in doc["failure_modes"]:
    for c in f["causes"]:
      for a in (c.get("actions") or []) + ((c.get("msr") or {}).get("actions") or []):
        linked.setdefault(a, []).append((c["occurrence"], c["detection"]))
  for a in doc["actions"]:
    rv = a.get("revised")
    reached = any(o <= rv["occurrence"] and d <= rv["detection"] for o, d in linked.get(a["id"], [])) if rv else True
    if a["status"] == "completed" and not reached:
      acts[a["id"]] = "completed, not yet credited"
  placed = [s for _, _, ids in SHEETS.values() for s in ids]
  if dupes := sorted({s for s in placed if placed.count(s) > 1}):
    raise CardError(f"on two sheets: {', '.join(dupes)}")
  if missing := sorted(set(fms) - set(placed)):
    raise CardError(f"failure mode with no sheet: {', '.join(missing)}; add it to SHEETS and SCENE")
  if extra := sorted(set(placed) - set(fms)):
    raise CardError(f"sheet names a failure mode the System FMEA does not have: {', '.join(extra)}")
  if bad := sorted(set(fms) ^ set(SCENE)):
    raise CardError(f"scene list and System FMEA differ: {', '.join(bad)}")
  for k, *_ in SCENE.values():
    if k not in ls.SCENES:
      raise CardError(f"unknown scene kind '{k}'")
  out = {}
  for fid, f in fms.items():
    hz = []
    for e in f["effects"]:
      h = e.get("hazard")
      if h:
        if h not in mapping:
          raise CardError(f"{fid}: {h} is not in hara-mapping.yaml")
        hz += [x for x in mapping[h] if x not in hz]
    chain = []
    for lvl, lab in LEVELS:
      es = [e["description"] for e in f["effects"] if e["level"] == lvl]
      if not es:
        raise CardError(f"{fid}: no {lvl} effect")
      chain.append((lab + (f" (+{len(es) - 1})" if len(es) > 1 else ""), es[0], es))
    causes, a_ids = [], []
    for c in f["causes"]:
      msr = c.get("msr") or {}
      causes.append(dict(id=c["id"], text=c["description"], o=c["occurrence"], d=c["detection"], m=msr.get("monitoring"), ap=c["ap"],
                         msr_ap=msr.get("ap")))
      for a in (c.get("actions") or []) + (msr.get("actions") or []):
        if a not in acts:
          raise CardError(f"{c['id']}: action {a} is not in the System FMEA actions")
        if a not in a_ids:
          a_ids.append(a)
    out[fid] = dict(id=fid, title=f["failure_mode"], s=f["severity"], gw=f["guideword"], hz=hz, chain=chain, causes=causes,
                    actions=[(a, acts[a]) for a in sorted(a_ids)], scene=SCENE[fid], trees=links.get(fid, []))
  return out


def meter(x, y, v, col, lab):
  b = [t(x, y + 8, lab, 8.5, MUTED, 700)]
  for i in range(10):
    b.append(f'<rect x="{x + 12 + i * 6}" y="{y}" width="4.5" height="9" rx="1" fill="{col if v and i < v else HAIR}"/>')
  return b


def card(x, y, c):
  b = [None, f"<title>{c['id']}: {c['title']}</title>"]
  px, yy = x + 12, y + 24
  if CARDS:
    b.append(fd.kind_icon("fm", px, yy - 10.5))
    b.append(f'<text x="{px + 18}" y="{yy}" font-size="11.5" font-weight="700" fill="{INK}" font-family="{fd.MONO}">{c["id"]}</text>')
  else:
    b.append(t(px, yy, c["id"], 12, MUTED, 600))
  tx = 86 if CARDS else 68
  tl = cut(c["title"], PW - (86 if CARDS else 70), 13.5, 2, True)
  for i, ln in enumerate(tl):
    b.append(t(px + tx, yy + 17 * i, ln, 13.5, INK, 700))
  yy += 17 * len(tl) - 4
  aps = [k["ap"] for k in c["causes"]]
  ap_label = f"AP H × {aps.count('H')} of {len(aps)}"
  if CARDS:
    chips = [(INK, "#FFFFFF", None, f"S {c['s']}")] + [("#FFFFFF", INK, LINE, h) for h in c["hz"]] + \
            [(SOFT, MUTED, None, c["gw"]), ("ap", None, None, ap_label)]
  else:
    chips = [("#0F172A", "#FFFFFF", None, f"S {c['s']}")] + [("#FEE2E2", "#B91C1C", None, h) for h in c["hz"]] + \
            [("#F1F5F9", "#334155", None, c["gw"]), ("#FFFFFF", "#DC2626", "#DC2626", ap_label)]
  cx = px
  for bg, fg, st, s in chips:
    w = (fd.ap_pill_w("H", s) if bg == "ap" else text_w(s, 10, True) + 14)
    if cx + w > px + PW:
      cx, yy = px, yy + 22
    if bg == "ap":
      b.append(fd.ap_pill(cx, yy + 1.5, "H", s)[0] if aps.count("H") else pill(cx, yy, s, SOFT, MUTED, 18, 10)[0])
    else:
      b.append(pill(cx, yy, s, bg, fg, 18, 10, st)[0])
    cx += w + 6
  yy += 30
  sw, sh = (PW - 28) / 3, 100
  for i, (lab, text, _) in enumerate(c["chain"]):
    sx = px + i * (sw + 14)
    an = (f'<animate attributeName="opacity" values="0.35;0.35;1;1" keyTimes="0;{0.1 + 0.25 * i:.2f};{0.13 + 0.25 * i:.2f};1" '
          f'dur="6s" repeatCount="indefinite"/>')
    b.append(f'<g>{an}<rect x="{sx:.1f}" y="{yy}" width="{sw:.1f}" height="{sh}" rx="{10 if CARDS else 7}" fill="#FFFFFF" '
             f'stroke="{STEP[i]}" stroke-width="1.4"/>')
    b.append(t(round(sx + 8, 1), yy + 15, lab, 9.5, STEP[i], 700))
    for k, ln in enumerate(cut(text, sw - 14, 9, 6)):
      b.append(t(round(sx + 8, 1), yy + 30 + 11.5 * k, ln, 9, INK))
    b.append("</g>")
    if i < 2:
      arrow = LINE if CARDS else "#94A3B8"
      b.append(f'<path d="M{sx + sw + 3:.1f} {yy + sh / 2 - 6} L{sx + sw + 11:.1f} {yy + sh / 2} L{sx + sw + 3:.1f} '
               f'{yy + sh / 2 + 6} Z" fill="{arrow}"/>')
  yy += sh + 8
  sth = PW * ls.fm.sk.STRIP_H / 280
  kind, t1, t2 = c["scene"]
  cid = f"c{c['id']}"
  b.append(f'<svg x="{px}" y="{yy:.1f}" width="{PW}" height="{sth:.1f}" viewBox="0 0 280 {ls.fm.sk.STRIP_H}"><clipPath id="{cid}"><rect width="280" height="{ls.fm.sk.STRIP_H}" rx="5"/>'
           f'</clipPath><g clip-path="url(#{cid})">' + "".join(ls.SCENES[kind](t1, t2) + ([ls.badge(" · ".join(c["hz"][:3]), "#DC2626")] if c["hz"] else []))
           + "</g></svg>")
  yy += sth + 16
  b.append(t(px, yy, f"Causes ({len(c['causes'])})", 9.5, MUTED, 700))
  b.append(t(px + PW, yy, "O occurrence · D detection · M monitoring · AP and MSR AP", 8.5, MUTED, None, "end"))
  yy += 8
  for k in c["causes"]:
    col, _ = monitoring(k["m"])
    lines = cut(f"{k['id'].split('.')[-1]}  {k['text']}", PW - 150, 9.5, 2)
    for i, ln in enumerate(lines):
      b.append(t(px, yy + 12 + 12 * i, ln, 9.5, INK))
    mx = px + PW - 140
    od = MUTED if CARDS else "#64748B"
    b += meter(mx, yy + 2, k["o"], od, "O") + meter(mx, yy + 14, k["d"], od, "D") + meter(mx, yy + 26, k["m"], col, "M")
    if not CARDS:
      b.append(t(px + PW, yy + 11, k["ap"], 10, AP_C.get(k["ap"], MUTED), 700, "end"))
      if k["msr_ap"]:
        b.append(t(px + PW, yy + 35, f"MSR {k['msr_ap']}", 8.5, AP_C.get(k["msr_ap"], MUTED), 700, "end"))
    elif k["ap"] in fd.AP_TINT_PILL:
      b.append(fd.ap_pill(px + PW - fd.ap_pill_w(k["ap"], k["ap"]), yy + 1, k["ap"], k["ap"], 14)[0])
    else:
      b.append(t(px + PW, yy + 11, k["ap"], 10, MUTED, 700, "end"))
    if CARDS and k["msr_ap"] in fd.AP_TINT_PILL:
      lab = f"MSR {k['msr_ap']}"
      b.append(fd.ap_pill(px + PW - fd.ap_pill_w(k["msr_ap"], lab), yy + 25, k["msr_ap"], lab, 14)[0])
    yy += max(12 * len(lines), 36) + 6
  yy += 4
  b.append(t(px, yy + 6, "Actions", 9.5, MUTED))
  cx, row0 = px + 56, yy
  if not c["actions"]:
    b.append(t(cx, yy + 6, "none", 9.5, MUTED))
  for a, st in c["actions"]:
    bg, fg = ACT_C.get(st, (SOFT, MUTED) if CARDS else ("#F1F5F9", "#334155"))
    s = f"{a} {st.replace('_', ' ')}"
    w = text_w(s, 9, True) + 12
    if cx + w > px + PW:
      cx, yy = px + 56, yy + 21
    b.append(pill(cx, yy - 7, s, bg, fg, 17, 9)[0])
    cx += w + 6
  yy += 24
  b.append(t(px, yy + 6, "Fault trees", 9.5, MUTED))
  cx = px + 70
  chips = []
  for goal, ids, kind in c["trees"]:
    if kind:
      chips.append((f"{goal} {'outside the tree, justified' if kind == 'justified' else 'tree gap'}",
                    ((SOFT, MUTED, None) if kind == "justified" else fd.AP_TINT_PILL["H"] + (None,)) if CARDS else
                    (("#F1F5F9", "#334155", None) if kind == "justified" else ("#FEE2E2", "#B91C1C", None)), 10))
      continue
    chips.append((goal, (INK, "#FFFFFF", None) if CARDS else ("#0F172A", "#FFFFFF", None), 4))
    if CARDS:
      chips += [(i, fd.AP_TINT_PILL["H"] + (None,) if sp else ("#FFFFFF", INK, LINE), 4) for i, sp in ids]
    else:
      chips += [(i, ("#FFFFFF", "#DC2626", "#DC2626") if sp else ("#FFFFFF", "#1D4ED8", "#2563EB"), 4) for i, sp in ids]
    chips[-1] = chips[-1][:2] + (10,)
  if not chips:
    b.append(t(cx, yy + 6, "in no fault tree", 9.5, MUTED))
  for s, (bg, fg, st), after in chips:
    w = text_w(s, 9, True) + 14
    if cx + w > px + PW:
      cx, yy = px + 70, yy + 21
    b.append(pill(cx, yy - 7, s, bg, fg, 17, 9, st)[0])
    cx += w + after
  return b, yy + 22 - y


def legend(y):
  b, x = [], M
  for col, lab in (("#16A34A", "M 1–4: within FTTI, measured"), ("#D97706", "M 5–7: code-derived timing or untimed"),
                   ("#DC2626", "M 8–10: late, not designed for it, or none"), ("#94A3B8", "no MSR rating")):
    b.append(f'<rect x="{x}" y="{y - 9}" width="22" height="9" rx="1" fill="{col}"/>')
    b.append(t(x + 28, y, lab, 10.5, INK))
    x += 28 + text_w(lab, 10.5) + 22
  for st, (bg, fg) in ACT_C.items():
    s = f"action {st.replace('_', ' ')}"
    b.append(pill(x, y - 12, s, bg, fg, 17, 9)[0])
    x += text_w(s, 9, True) + 18
  return b


def sheet(name, cs):
  num, title, ids = SHEETS[name]
  w = 2 * M + COLS * CW + (COLS - 1) * GAP
  body = header(w, f"System FMEA · {title}",
                "Each failure mode from its causes to the road: the effect chain, a scene of the end effect, every cause with its "
                "ratings and monitoring, and the actions.", "fmea/analyses/system-fmea.yaml · hara-mapping.yaml", "Schematic scenes")
  body += legend(104)
  y = 122
  for r in range(0, len(ids), COLS):
    built = [card(M + k * (CW + GAP), y, cs[i]) for k, i in enumerate(ids[r:r + COLS])]
    row_h = max(h for _, h in built)
    for k, (b, _) in enumerate(built):
      cx0 = M + k * (CW + GAP)
      b[0] = (f'<rect x="{cx0}" y="{y + 3}" width="{CW}" height="{row_h:.0f}" rx="12" fill="#000000" opacity=".05"/>'
              if CARDS else "") + \
             f'<rect x="{cx0}" y="{y}" width="{CW}" height="{row_h:.0f}" rx="12" fill="#FFFFFF" stroke="{HAIR}"/>'
      body += ["<g>"] + b + ["</g>"]
    y += row_h + GAP
  body.append(t(M, y + 6, "Ratings, effects, hazards and actions from the YAML at its current baseline; scenes are drawings. Text cut with … "
                "is given in full in the figure description.", 10.5, MUTED))
  body.append(t(w - M, y + 24, "Generated by tools/safety/fmea_cards.py", 10, MUTED, None, "end"))
  desc = f"Figure {num}: {len(ids)} System FMEA failure modes, {title}. " + " ".join(
    f"{cs[i]['id']} {cs[i]['title']} (S {cs[i]['s']}; {', '.join(cs[i]['hz']) or 'no hazard'}). Effects: " +
    " / ".join(" ; ".join(es) for _, _, es in cs[i]["chain"]) + ". Causes: " +
    "; ".join(f"{k['id']} {k['text']} (O {k['o']}, D {k['d']}, M {k['m'] if k['m'] is not None else '-'}, AP {k['ap']}"
              f"{', MSR AP ' + k['msr_ap'] if k['msr_ap'] else ''})" for k in cs[i]["causes"]) +
    ". Actions: " + (", ".join(f"{a} {s}" for a, s in cs[i]["actions"]) or "none") + ". Fault trees: " +
    ("; ".join(f"{g} {kind.replace('_', ' ')}" if kind else f"{g} " + ", ".join(e + (" (single point)" if sp else "") for e, sp in ev)
               for g, ev, kind in cs[i]["trees"]) or "none") + "." for i in ids)
  h = int(y + 38)
  if not CARDS:
    return svg_doc(w, h, f"Figure {num}. System FMEA failure modes: {title}", desc, body)
  body.insert(0, f'<rect y="83" width="{w}" height="{h - 83}" fill="url(#dots)"/>')
  out = svg_doc(w, h, f"Figure {num}. System FMEA failure modes: {title}", desc, body, DOTS)
  return out.replace(f'<rect width="{w}" height="{h}" fill="#FFFFFF"/>', f'<rect width="{w}" height="{h}" fill="{BG}"/>', 1)


def build() -> dict[str, str]:
  cs = cards(*load(), ff.backlinks())
  return {name: sheet(name, cs) for name in SHEETS}


def build_all() -> dict[str, str]:
  """The sheets of record and their card versions (drawn in a second process, as in fmea_diagrams.build_cards())."""
  if CARDS:
    raise CardError("build_all() runs in the original style; unset FMEA_FIG_STYLE")
  out = build()
  env = dict(os.environ, FMEA_FIG_STYLE="cards")
  proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--emit-json"], env=env, capture_output=True,
                        text=True, check=False)
  if proc.returncode != 0:
    raise CardError(f"card versions: {(proc.stderr or proc.stdout).strip()[-600:]}")
  out.update({fd.cards_name(k): v for k, v in json.loads(proc.stdout).items()})
  return out


def main(argv: list[str]) -> int:
  check = "--check" in argv
  if "--emit-json" in argv:   # used by build_all()
    print(json.dumps(build(), ensure_ascii=False))
    return 0
  try:
    out = build_all()
  except (CardError, fd.FigError, ff.FigureError) as e:
    print(f"fmea_cards: {e}", file=sys.stderr)
    return 1
  stale = []
  OUT.mkdir(parents=True, exist_ok=True)
  for name, content in out.items():
    p = OUT / name
    if check:
      if not p.exists() or p.read_text(encoding="utf-8") != content:
        stale.append(name)
    else:
      p.write_text(content, encoding="utf-8")
  if stale:
    print("stale System FMEA cards; run tools/safety/fmea_cards.py: " + ", ".join(stale), file=sys.stderr)
    return 1
  print(f"fmea_cards: {len(out)} sheets {'current' if check else 'written'}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
