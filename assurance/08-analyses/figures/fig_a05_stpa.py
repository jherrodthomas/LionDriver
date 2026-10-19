#!/usr/bin/env python3
"""Draw the WP-A-05 (STPA) figures.

Sources of record: `../WP-A-05-stpa.md`, `../stpa-map.yaml` and the decision register
(`../../01-management/decisions/register.yaml`). The data-driven figures (2-1, 4-1, 5-1, 5-2) are
built from those files; so are the scene sheets 4-2 … 4-4, drawn by `stpa_scenes.py`. The structure
and block figures (3-1 … 3-7, 5-3 … 5-6) are laid out here by hand, because a layout is a drawing
decision. Every ID they name (H-, SC-, CA-, FB-, UCA-, LS-,
DQ-) is checked against the sources, so a renamed or removed item fails the check.
Nothing here is analysis content: change WP-A-05 and regenerate. The scene cards' belief lines and road
scenes illustrate §5 and are not themselves analysis.

    python3 fig_a05_stpa.py            # regenerate the SVGs
    python3 fig_a05_stpa.py --check    # fail if a committed SVG is stale or an ID is unknown

Needs PyYAML. Output is deterministic.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stpa_scenes

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "WP-A-05-stpa.md"
MAP = HERE.parent / "stpa-map.yaml"
REGISTER = HERE.parent.parent / "01-management" / "decisions" / "register.yaml"
FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SFMono-Regular', Menlo, Consolas, monospace"

INK, MUTED, RULE, PAPER, BG = "#0F172A", "#475569", "#CBD5E1", "#FFFFFF", "#F8FAFC"
CA, FB, CALLOUT, WRONG = "#C2410C", "#0F766E", "#3B6AA8", "#B42318"
STATUS = {  # fill, stroke
  "covered": ("#E3F2E8", "#2F7D4F"), "known_gap": ("#FCF0D2", "#9A6400"), "new": ("#FDE4E1", "#B42318"),
  "open_test": ("#E3EAF8", "#3B5BA9"), "external": ("#ECEEF1", "#6B7480"), "none": ("#ECEEF1", "#6B7480"),
}
STATUS_LABEL = {"covered": "Covered", "known_gap": "Known gap", "new": "New finding", "open_test": "Open test",
                "external": "External (assumption)", "none": "No scenario"}

STYLE = f"""<style>
text{{font-family:{FONT};fill:{INK}}}
.m{{fill:{MUTED}}} .s{{font-size:12px}} .xs{{font-size:11px}} .b{{font-weight:700}} .sb{{font-weight:600}}
.h{{fill:{MUTED};font:600 11.5px {MONO};letter-spacing:.04em}}
.mono{{font-family:{MONO};font-size:11px;font-weight:600}}
.box{{fill:{PAPER};stroke:{INK};stroke-width:1.3}}
.grey{{fill:#8C9196;stroke:none}} .greyt{{fill:#FFFFFF;font-weight:700;font-size:12.5px}}
.ar{{fill:none;stroke:{INK};stroke-width:1.3}}
.ca{{fill:none;stroke:{CA};stroke-width:1.8}} .fb{{fill:none;stroke:{FB};stroke-width:1.8}}
.cat{{fill:{CA};font:600 11px {MONO}}} .fbt{{fill:{FB};font:600 11px {MONO}}}
.dead{{fill:none;stroke:#94A3B8;stroke-width:1.6;stroke-dasharray:3 4}}
.fix{{fill:none;stroke:#2F7D4F;stroke-width:1.6;stroke-dasharray:6 4}}
.co{{fill:{CALLOUT};font-size:11.5px}} .cob{{fill:{CALLOUT};font-size:11.5px;font-weight:700}}
.cocurve{{fill:none;stroke:{CALLOUT};stroke-width:4;stroke-linecap:round;opacity:.75}}
.wr{{fill:{WRONG};font-size:11.5px}} .wrb{{fill:{WRONG};font:700 11px {MONO}}}
.grid{{stroke:{RULE};stroke-width:1}}
.blk{{stroke-width:1.5}} .bt{{font-weight:600;font-size:13px}} .bs{{fill:{MUTED};font-size:11.5px}}
.grp{{fill:none;stroke:{RULE};stroke-width:1.2;stroke-dasharray:5 4}} .gl{{fill:{MUTED};font:600 12px {MONO}}}
.chipt{{font:600 11px {MONO};fill:{INK}}}
.fm{{fill:{WRONG}}} .fx{{stroke:#FFFFFF;stroke-width:2.4}} .ft{{fill:{WRONG};font:700 12px {MONO}}} .fn{{font-size:11.5px}}
</style>"""

KIND = {  # block kinds: fill, stroke
  "item": (PAPER, "#64748B"), "env": ("#FFF4EC", CA), "ext": ("#ECEEF1", "#6B7480"), "drv": ("#E3EAF8", "#3B5BA9"),
  "bad": ("#FDE4E1", WRONG), "fix": ("#E3F2E8", "#2F7D4F"),
}


class ParseError(Exception):
  pass


# ============================================================================ sources
class Sources:
  def __init__(self, doc: str, smap: dict, register: list[dict]):
    self.doc, self.smap = doc, smap
    self.reg = {e["id"]: e for e in register}
    self.scen = {s["id"]: s for s in smap["scenarios"]}
    self.ext = {u["uca"] for u in smap.get("external_ucas", [])}
    self.losses = {c[0]: c[1] for c in self._rows(r"L-\d+")}
    self.hazards = {}
    for c in self._rows(r"H-(?:\d+|STPA-\d+)"):
      self.hazards[c[0]] = dict(text=c[1], losses=re.findall(r"L-\d+", c[2]), goal=c[3])
    self.constraints = {c[0]: dict(text=c[1], hazards=re.findall(r"H-(?:STPA-)?\d+", c[2])) for c in self._rows(r"SC-\d+")}
    self.ids = set(re.findall(r"^\| ((?:CA|FB|UCA|LS|CC|H|SC|L)-[\w-]+) \|", doc, re.M))
    self.ucas = self._parse_ucas()
    self.ls_type = {c[0]: c[3] for c in self._rows(r"LS-\d+") if len(c) >= 6 and c[1].startswith("UCA")}
    if not self.losses or not self.hazards or not self.ucas or not self.ls_type:
      raise ParseError("WP-A-05 tables not found (losses, hazards, UCAs or loss scenarios)")

  def _rows(self, pat):
    return [[x.strip() for x in l.strip().strip("|").split(" | ")]
            for l in self.doc.splitlines() if re.match(r"^\| %s \|" % pat, l)]

  def _parse_ucas(self):
    out = {}
    names = {"C2.1": "C2.1 Driving model", "C2.2": "C2.2 Planner", "C2.4": "C2.4 Supervisor",
             "C2.6": "C2.6 Calibration", "C2.7": "C2.7 Panda interface", "C7": "C7 Updater / owner"}
    for c in self._rows(r"UCA-\d+"):
      uid = c[0]
      if c[1] in "NPTD" and len(c[1]) == 1:
        n = int(uid.split("-")[1])
        ctrl = "C1 Driver" if n < 10 else "C2 openpilot" if n < 30 else "C3 panda"
        out[uid] = dict(ctrl=ctrl, type=c[1], text=c[2])
      elif len(c) > 2 and c[2] in ("N", "P", "T", "D"):
        first = c[1].replace("`", "").split(",")[0].split(" ")[0]
        ctrl = names.get(first, "C2 openpilot" if first == "C2" else first)
        out[uid] = dict(ctrl=ctrl, type=c[2], text=c[3])
      else:
        out[uid] = dict(ctrl=c[1] + " (external)", type="P", text=c[2])
    return out

  def worst(self, uid):
    if uid in self.ext:
      return "external"
    st = [s["status"] for s in self.smap["scenarios"] if uid in s["ucas"]]
    order = ["new", "known_gap", "open_test", "covered"]
    return min(st, key=order.index) if st else "none"

  def need(self, *ids):
    for i in ids:
      if i.startswith("DQ-"):
        if i not in self.reg:
          raise ParseError(f"{i} is not in the decision register")
      elif i not in self.ids:
        raise ParseError(f"{i} is not in WP-A-05")


def load() -> Sources:
  return Sources(SOURCE.read_text(encoding="utf-8"), yaml.safe_load(MAP.read_text(encoding="utf-8")),
                 yaml.safe_load(REGISTER.read_text(encoding="utf-8")))


# ============================================================================ svg helpers
def T(x, y, s, cls="", anchor="start", **kw):
  extra = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in kw.items())
  c = f' class="{cls}"' if cls else ""
  return f'<text x="{x:g}" y="{y:g}"{c} text-anchor="{anchor}"{extra}>{escape(s)}</text>'


def lines(x, y, rows, cls="", anchor="start", step=14):
  return "".join(T(x, y + i * step, r, cls, anchor) for i, r in enumerate(rows))


def wrap(s, n):
  out, cur = [], ""
  for w in s.split():
    if cur and len(cur) + len(w) + 1 > n:
      out.append(cur)
      cur = w
    else:
      cur = (cur + " " + w).strip()
  return out + ([cur] if cur else [])


def markers():
  return "".join(
    f'<marker id="m-{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
    f'<path d="M0 0L10 5L0 10z" fill="{c}"/></marker>'
    for k, c in (("ar", INK), ("ca", CA), ("fb", FB), ("fix", "#2F7D4F"), ("dead", "#94A3B8"), ("co", CALLOUT), ("wr", WRONG)))


def path(pts, cls, mk=None):
  d = "M" + " L".join(f"{x:g} {y:g}" for x, y in pts)
  m = f' marker-end="url(#m-{mk})"' if mk else ""
  return f'<path d="{d}" class="{cls}"{m}/>'


def svg(fig_id, w, h, title, desc, body):
  return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
          f'role="img" aria-labelledby="t d">\n<title id="t">{escape(title)}</title>\n<desc id="d">{escape(desc)}</desc>\n'
          f'<defs>{markers()}{STYLE}</defs>\n<rect width="{w}" height="{h}" fill="{BG}"/>\n{body}\n'
          f'<text x="{w - 12}" y="{h - 10}" class="m xs" text-anchor="end">WP-A-05 {escape(fig_id)} · generated by fig_a05_stpa.py</text>\n</svg>\n')


def chip(x, y, label, status, w=64, h=20, title=None):
  f, s = STATUS[status]
  t = f"<title>{escape(title)}</title>" if title else ""
  return (f'<g>{t}<rect x="{x:g}" y="{y:g}" width="{w}" height="{h}" rx="{h/2:g}" fill="{f}" stroke="{s}" stroke-width="1.4"/>'
          + T(x + w / 2, y + h * 0.7, label, "chipt", "middle") + "</g>")


# ============================================================================ Figure 2-1
def fig_2_1(S: Sources):
  W, rowh = 1180, 44
  hz = list(S.hazards)
  H = 100 + rowh * len(hz)
  b = []
  for x, t in [(20, "LOSSES (§2.1)"), (250, "SYSTEM-LEVEL HAZARDS (§2.2)"), (690, "SYSTEM CONSTRAINTS (§2.3)"), (1010, "SAFETY GOAL")]:
    b.append(T(x, 30, t, "h"))
  span = rowh * len(hz) / len(S.losses)
  ly = {}
  for i, (lid, lt) in enumerate(S.losses.items()):
    y = 50 + i * span
    ly[lid] = y + 20
    f, s = STATUS["new"]
    b.append(f'<rect x="20" y="{y:g}" width="190" height="{span - 10:g}" rx="6" fill="{f}" stroke="{s}" stroke-width="1.3"/>')
    b.append(T(32, y + 20, lid, "b s"))
    b.append(lines(32, y + 38, wrap(lt, 27)[:5], "m xs", step=13))
  sc_by_h = defaultdict(list)
  for sid, sc in S.constraints.items():
    for h in sc["hazards"]:
      sc_by_h[h].append(sid)
  for i, hid in enumerate(hz):
    y = 50 + i * rowh
    h = S.hazards[hid]
    for l in h["losses"]:
      if l in ly:
        b.append(f'<path d="M210 {ly[l]:g} C 230 {ly[l]:g}, 230 {y + 18:g}, 250 {y + 18:g}" fill="none" stroke="{RULE}" stroke-width="1.5"/>')
    dash = ' stroke-dasharray="5 4"' if hid.startswith("H-STPA") else ""
    b.append(f'<rect x="250" y="{y}" width="400" height="{rowh - 8}" rx="6" fill="{PAPER}" stroke="{WRONG if dash else MUTED}" stroke-width="1.3"{dash}/>')
    b.append(T(262, y + 22, hid, "b s"))
    ht = wrap(h["text"], 50)
    b.append(T(338, y + 22, ht[0] + ("…" if len(ht) > 1 else ""), "s"))
    b.append(path([(650, y + 18), (690, y + 18)], "ar"))
    scs = sc_by_h.get(hid, [])
    f, s = STATUS["open_test"]
    b.append(f'<rect x="690" y="{y}" width="290" height="{rowh - 8}" rx="6" fill="{f}" stroke="{s}" stroke-width="1.3"/>')
    if scs:
      st = wrap(S.constraints[scs[0]]["text"], 32)
      b.append(T(702, y + 22, f"{', '.join(scs)}: {st[0]}…", "s"))
    goals = re.findall(r"SG-\d+", h["goal"])
    gtxt = ", ".join(goals) if goals else ("none yet: H-09 (DQ-205)" if hid.startswith("H-STPA") else "within H-02, H-05, H-06")
    b.append(path([(980, y + 18), (1010, y + 18)], "ar"))
    f, s = STATUS["covered" if goals else "none"]
    b.append(f'<rect x="1010" y="{y}" width="150" height="{rowh - 8}" rx="6" fill="{f}" stroke="{s}" stroke-width="1.3"/>')
    b.append(T(1022, y + 22, gtxt, "b s" if goals else "m xs"))
  return svg("Figure 2-1", W, H, "Figure 2-1. Losses, system-level hazards, constraints and safety goals (WP-A-05 §2)",
             "Each loss links to the hazards that lead to it; each hazard to its system constraint and safety goal. "
             "H-STPA-1 has no goal yet; H-07 is rated within other hazards.", "".join(b))


# ============================================================================ Figure 3-1 vehicle-level control structure
F31_STYLE = """<style>
.t{fill:#0F172A}.m{fill:#475569}.s{font-size:11px}.xs{font-size:10px}.xxs{font-size:9.5px}.b{font-weight:700}.sb{font-weight:600}
.item{fill:#FFFFFF;stroke:#64748B;stroke-width:1.4}
.env{fill:#FFF7ED;stroke:#C2410C;stroke-width:1.8}
.ext{fill:#F1F5F9;stroke:#94A3B8;stroke-width:1.2}
.tag{font-size:10px;font-weight:700;letter-spacing:.04em}
.ca{fill:none;stroke:#C2410C;stroke-width:2}
.fb{fill:none;stroke:#0F766E;stroke-width:1.8}
.lr{fill:#C2410C;font-size:9.5px;font-weight:600}
.lt{fill:#0F766E;font-size:9.5px;font-weight:600}
</style>"""

# (x, y, w, h, class, [(text, x, y, class, size, anchor)])
F31_BOXES = [
  (680, 300, 420, 86, "item", [("C2 openpilot on the SoC", 696, 322, "t b", 13.5, None), ("item · E-01", 1086, 322, "m xxs", None, "end"),
                               ("modeld, planner, controlsd, selfdrived,", 696, 342, "m xs", None, None),
                               ("dmonitoringd, pandad, ui / soundd", 696, 356, "m xs", None, None)]),
  (640, 470, 360, 90, "env", [("C3 panda safety model (MCU)", 656, 492, "t b", 13.5, None), ("item · E-03", 986, 492, "m xxs", None, "end"),
                              ("block / forward, limits, authority,", 656, 514, "m xs", None, None),
                              ("intercept drive, heartbeat, watchdog", 656, 528, "m xs", None, None)]),
  (130, 470, 170, 90, "ext", [("C6 stock ADAS", 146, 492, "t b", 13, None), ("camera (PCS)", 146, 508, "t b", 13, None),
                              ("external · UCA-42 → AOU-04", 146, 528, "m xxs", None, None)]),
  (320, 660, 300, 80, "ext", [("C5 PCM / ACC / brake ECU", 336, 682, "t b", 13, None), ("cruise state, powertrain, brake", 336, 700, "m xs", None, None),
                              ("external · UCA-41 → AOU-03, AOU-05", 336, 728, "m xxs", None, None)]),
  (700, 660, 260, 80, "ext", [("C4 EPS ECU", 716, 682, "t b", 13, None), ("assist + LKA", 716, 700, "m xs", None, None),
                              ("external · UCA-40 → AOU-01, AOU-02", 716, 728, "m xxs", None, None)]),
  (972, 650, 204, 100, "item", [("Harness box (actuator)", 1074, 670, "t b", 12, "middle"), ("2 × DG419LE analog switches", 1074, 686, "m xs", None, "middle"),
                                ("pull-down → pass-through", 1074, 700, "m xs", None, "middle"),
                                ("supply: IGN via D1 / comma pwr", 1074, 714, "m xs", None, "middle"),
                                ("stock camera path runs through · E-05", 1074, 728, "m xxs", None, "middle")]),
]

# (ID, path, kind, dashed) — every line on the figure, with the CA/FB it draws
F31_EDGES = [
  ("CA-03", "M260 130 H70 V836", "ca", False), ("CA-01", "M330 190 V656", "ca", False), ("CA-02", "M450 190 V656", "ca", False),
  ("CA-04", "M570 190 V656", "ca", False), ("CA-07", "M850 300 V194", "ca", False), ("CA-05", "M710 386 V466", "ca", False),
  ("CA-08", "M820 386 V466", "ca", False), ("CA-06", "M690 560 V712 H624", "ca", False), ("CA-10", "M660 560 V680 H624", "ca", True),
  ("CA-10", "M760 560 V656", "ca", True), ("CA-05", "M870 560 V656", "ca", False), ("CA-09", "M980 560 V610 H1105 V646", "ca", False),
  ("CA-13", "M215 560 V712 H316", "ca", False), ("CA-12", "M470 740 V836", "ca", False), ("CA-11", "M830 740 V836", "ca", False),
  ("FB-03", "M100 840 V166 H256", "fb", False), ("FB-02", "M280 470 V194", "fb", False), ("FB-01", "M655 470 V194", "fb", False),
  ("FB-01", "M740 300 V194", "fb", False), ("FB-07", "M960 190 V296", "fb", False), ("FB-04", "M930 470 V390", "fb", False),
  ("FB-05", "M1190 840 V360 H1104", "fb", False), ("FB-05", "M1190 505 H1004", "fb", False), ("FB-06", "M1225 840 V330 H1104", "fb", False),
]

# (label, x, y, width, kind) — pills on the lines
F31_TAGS = [
  ("CA-01", 308, 214, 44, "ca"), ("CA-02", 428, 214, 44, "ca"), ("CA-04", 548, 214, 44, "ca"), ("CA-03", 96, 114, 44, "ca"),
  ("FB-01", 718, 214, 44, "fb"), ("CA-07", 828, 214, 44, "ca"), ("FB-07", 938, 232, 44, "fb"), ("FB-01", 633, 300, 44, "fb"),
  ("FB-02", 258, 300, 44, "fb"), ("CA-05 · CA-06", 666, 400, 88, "ca"), ("CA-08", 798, 400, 44, "ca"), ("FB-04", 908, 400, 44, "fb"),
  ("FB-06", 1112, 296, 44, "fb"), ("FB-05", 1168, 420, 44, "fb"), ("CA-10", 638, 600, 44, "ca"), ("CA-06", 632, 720, 44, "ca"),
  ("CA-10", 738, 600, 44, "ca"), ("CA-05", 848, 600, 44, "ca"), ("CA-09", 1010, 584, 44, "ca"), ("CA-13", 193, 600, 44, "ca"),
  ("CA-12", 448, 780, 44, "ca"), ("CA-11", 808, 780, 44, "ca"), ("FB-03", 78, 760, 44, "fb"),
]

# (x, y, kind, anchor, lines)
F31_LABELS = [
  (146, 127, "ca", None, ["steering input"]), (96, 148, "ca", None, ["mechanical, adds at the rack"]),
  (336, 248, "ca", None, ["engage / resume", "cruise SET, RES"]), (456, 248, "ca", None, ["disengage: brake", "pedal, CANCEL", "(also to C2, C3)"]),
  (576, 248, "ca", None, ["accelerator", "override"]), (274, 334, "fb", "end", ["cluster: cruise,", "LKA / LTA, PCS", "warnings (C5 / C6)"]),
  (649, 334, "fb", "end", ["siren", "from C3"]), (746, 248, "fb", None, ["engagement", "state, alerts", "(UI, sounds)"]),
  (856, 248, "ca", None, ["alerts, take-over", "requests, DM", "escalation"]), (966, 266, "fb", None, ["driver camera,", "wheel touch"]),
  (716, 436, "ca", None, ["torque 0x2E4,", "accel 0x343"]), (826, 436, "ca", None, ["safety mode 0xdc,", "heartbeat 0xf3"]),
  (936, 436, "fb", None, ["panda", "health"]), (1160, 309, "fb", None, ["road", "cameras"]), (1184, 456, "fb", "end", ["vehicle", "CAN state"]),
  (766, 634, "ca", None, ["block TX /", "controls off"]), (876, 634, "ca", None, ["lateral torque", "0x2E4"]),
  (1060, 597, "ca", None, ["intercept drive (SBU1)"]), (209, 634, "ca", "end", ["PCS brake,", "warnings;", "via harness box", "or forwarded by C3"]),
  (476, 816, "ca", None, ["accel / brake"]), (836, 816, "ca", None, ["rack torque"]), (106, 796, "fb", None, ["vehicle motion,", "steering feel"]),
]


def vehicle_level_ids(S):
  """CA and FB IDs of the vehicle-level structure (§3.3); §3.4 adds CA-14 … CA-22 and FB-08 … FB-11 inside openpilot."""
  return {i for i in S.ids if re.fullmatch(r"(CA-(0\d|1[0-3])|FB-0[1-7])", i)}


def fig_3_1(S):
  drawn = {e[0] for e in F31_EDGES}
  tagged = {t for lab, *_ in F31_TAGS for t in lab.split(" · ")}
  S.need(*sorted(drawn | tagged))
  missing = vehicle_level_ids(S) - drawn
  if missing:
    raise ParseError(f"Figure 3-1 does not draw {', '.join(sorted(missing))} of the §3.3 table")
  if drawn - tagged:
    raise ParseError(f"Figure 3-1 draws {', '.join(sorted(drawn - tagged))} without a tag")
  o = []
  o.append('<rect width="1280" height="1000" fill="#FFFFFF"/>')
  o.append('<text x="40" y="44" class="t b" font-size="20">Figure 3-1 · STPA control structure</text>')
  o.append('<text x="40" y="66" class="m" font-size="12.5">Reference configuration while driving · controllers top to bottom by authority · control actions down, feedback up</text>')
  o.append('<text x="1240" y="44" class="m s" text-anchor="end">WP-A-05 §3.1</text>')
  o.append('<text x="1240" y="62" class="m s" text-anchor="end">controllers §3.2 · CA / FB §3.3</text>')
  o.append('<line x1="40" y1="82" x2="1240" y2="82" stroke="#E2E8F0"/>')
  # C1 driver with a figure icon
  o.append('<rect x="260" y="98" width="740" height="92" rx="10" class="item"/>')
  o.append('<g transform="translate(296,126)" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round">'
           '<circle cx="0" cy="0" r="8"/><path d="M0 8V32M-13 16H13M0 32L-10 48M0 32L10 48"/></g>')
  o.append('<text x="330" y="124" class="t b" font-size="14">C1 Driver</text>')
  o.append('<text x="330" y="142" class="m xs">human controller: supervises at all times, overrides or disengages, responds to alerts</text>')
  o.append('<text x="330" y="160" class="t xs sb">Process model:</text>')
  o.append('<text x="408" y="160" class="m xs">item state (engaged / overriding / disengaged), road, own role</text>')
  for x, y, w, h, cls, texts in F31_BOXES:
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="{cls}"/>')
    for t, tx, ty, tc, size, anchor in texts:
      extra = (f' font-size="{size:g}"' if size else "") + (f' text-anchor="{anchor}"' if anchor else "")
      o.append(f'<text x="{tx}" y="{ty}" class="{tc}"{extra}>{escape(t)}</text>')
  o.append('<text x="1074" y="742" class="m xxs" text-anchor="middle" style="fill:#B91C1C">no position feedback (§3.5)</text>')
  o.append('<path d="M1168 650 V575 H1004" fill="none" stroke="#B91C1C" stroke-width="1.4" stroke-dasharray="3 4"/>')
  o.append('<text x="1012" y="570" class="m xxs" style="fill:#B91C1C">no feedback of the switch position</text>')
  o.append('<rect x="40" y="840" width="1200" height="56" rx="10" fill="#FFFBEB" stroke="#B45309" stroke-width="1.6"/>')
  o.append('<text x="640" y="864" class="t b" font-size="14" text-anchor="middle">Controlled process: vehicle lateral and longitudinal motion</text>')
  o.append('<text x="640" y="882" class="m xs" text-anchor="middle">rack torque from C4 and the driver\'s steering add at the rack; acceleration and braking via C5</text>')
  for ident, d, kind, dashed in F31_EDGES:
    dash = ' stroke-dasharray="6 4"' if dashed else ""
    mk = "aR" if kind == "ca" else "aT"
    o.append(f'<path d="{d}" class="{kind}"{dash} marker-end="url(#{mk})"><title>{ident}</title></path>')
  o.append('<circle cx="1190" cy="505" r="3" fill="#0F766E"/>')
  o.append('<g class="tag">')
  for lab, x, y, w, kind in F31_TAGS:
    col = "#C2410C" if kind == "ca" else "#0F766E"
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="18" rx="9" fill="{col}"/>'
             f'<text x="{x + w // 2}" y="{y + 13}" fill="#fff" text-anchor="middle">{escape(lab)}</text>')
  o.append('</g>')
  for x, y, kind, anchor, rows in F31_LABELS:
    a = f' text-anchor="{anchor}"' if anchor else ""
    for i, r in enumerate(rows):
      o.append(f'<text x="{x}" y="{y + 13 * i}" class="{"lr" if kind == "ca" else "lt"}"{a}>{escape(r)}</text>')
  o.append('<line x1="40" y1="926" x2="1240" y2="926" stroke="#E2E8F0"/>')
  o.append('<g transform="translate(40,952)" font-size="10.5">'
           '<line x1="0" y1="0" x2="28" y2="0" stroke="#C2410C" stroke-width="2"/><text x="36" y="4" class="t">Control action</text>'
           '<line x1="136" y1="0" x2="164" y2="0" stroke="#C2410C" stroke-width="2" stroke-dasharray="6 4"/><text x="172" y="4" class="t">Control action by withholding (frames not sent)</text>'
           '<line x1="430" y1="0" x2="458" y2="0" stroke="#0F766E" stroke-width="1.8"/><text x="466" y="4" class="t">Feedback</text>'
           '<rect x="546" y="-8" width="28" height="16" rx="4" fill="#FFFFFF" stroke="#64748B"/><text x="582" y="4" class="t">Controller in the item</text>'
           '<rect x="722" y="-8" width="28" height="16" rx="4" fill="#FFF7ED" stroke="#C2410C"/><text x="758" y="4" class="t">Safety envelope</text>'
           '<rect x="868" y="-8" width="28" height="16" rx="4" fill="#F1F5F9" stroke="#94A3B8"/><text x="904" y="4" class="t">External controller (UCAs as assumptions, §4.4)</text></g>')
  o.append('<text x="40" y="984" class="m xs">CA-07 is a control action of C2 on the driver and therefore points up. Every CA and FB of the §3.3 table is drawn; '
           'generated by fig_a05_stpa.py.</text>')
  title = "Figure 3-1. STPA control structure of the reference configuration (WP-A-05 §3.1)"
  desc = ("Controllers from top to bottom by authority: C1 driver; C2 openpilot on the SoC; C3 panda safety model on the MCU and C6 stock "
          "ADAS camera; C5 PCM/ACC/brake ECU, C4 EPS ECU and the harness box with its two intercept switches; the controlled process is "
          "the vehicle lateral and longitudinal motion. Control actions CA-01 to CA-13 point down (CA-07, alerts to the driver, points "
          "up); feedback FB-01 to FB-07 points up. The harness box reports no switch position.")
  defs = ('<marker id="aR" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#C2410C"/></marker>'
          '<marker id="aT" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#0F766E"/></marker>')
  return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="1000" viewBox="0 0 1280 1000" font-family="{FONT}" '
          f'role="img" aria-labelledby="t d">\n<title id="t">{escape(title)}</title>\n<desc id="d">{escape(desc)}</desc>\n'
          f'<defs>{defs}{F31_STYLE}</defs>\n' + "\n".join(o) + "\n</svg>\n")


# ============================================================================ Figure 3-2 simple -> detailed
def box(x, y, w, h, label, sub=None, cls="box"):
  out = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="{cls}"/>'
  rows = label.split("\n")
  top = y + h / 2 - (len(rows) - 1) * 7 + (4 if not sub else -2)
  out += lines(x + w / 2, top, rows, "s sb", "middle")
  if sub:
    out += T(x + w / 2, top + 14 * len(rows), sub, "m xs", "middle")
  return out


def lbl(x, y, text, anchor="start", cls="xs"):
  return lines(x, y, text.split("\n"), cls, anchor, 13)


def fig_3_2(S: Sources):
  S.need("CA-01", "CA-02", "CA-03", "CA-04", "CA-05", "CA-06", "CA-07", "CA-08", "CA-09", "CA-11", "CA-12", "CA-13",
         "CA-20", "CA-21", "FB-01", "FB-03", "FB-04", "FB-05", "FB-06", "FB-07", "FB-11")
  W, H = 1610, 760
  b = [T(20, 30, "SIMPLE", "h"), T(640, 30, "DETAILED (CONTROLLERS OF §3.2 AND §3.4)", "h")]
  # ---- simple panel: one column, outer loop like the classic STPA hierarchy
  X, w = 190, 180
  ys = [60, 200, 340, 480, 620]
  names = [("LionDriver project", "release, safety case"), ("Driver / owner", "C1, C7"),
           ("LionDriver item", "openpilot C2, panda C3"), ("Toyota ECUs", "EPS C4, PCM C5, camera C6"),
           ("Vehicle motion", "controlled process")]
  for y, (n, sub) in zip(ys, names):
    b.append(box(X, y, w, 56, n, sub))
  down = ["Releases\nUser information\nInstall checklist", "Engage, cancel\nOverride\n(CA-01, 02, 04)",
          "Torque, acceleration\nrequests (CA-05, 06)", "Rack torque\nDrive, brake (CA-11, 12)"]
  up = ["Field reports\nLogs", "Alerts, HMI\n(CA-07, FB-01)", "Vehicle CAN state\n(FB-05)", "Wheel speeds\nTorque, status"]
  for i in range(4):
    y1, y2 = ys[i] + 56, ys[i + 1]
    b.append(path([(X + 50, y1), (X + 50, y2)], "ar", "ar"))
    b.append(path([(X + 130, y2), (X + 130, y1)], "ar", "ar"))
    b.append(lbl(X + 44, y1 + 26, down[i], "end"))
    b.append(lbl(X + 136, y1 + 26, up[i]))
  # outer loop: driver steers the vehicle directly and feels it
  b.append(path([(X, ys[1] + 28), (40, ys[1] + 28), (40, ys[4] + 28), (X, ys[4] + 28)], "ar", "ar"))
  b.append(lbl(46, ys[3] - 10, "Steering\nPedals\n(CA-03, 04)"))
  b.append(path([(X + w, ys[4] + 28), (560, ys[4] + 28), (560, ys[1] + 28), (X + w, ys[1] + 28)], "ar", "ar"))
  b.append(lbl(554, ys[3] - 10, "Motion\nWheel feel\n(FB-03)", "end"))
  # ---- arrow
  b.append(f'<path d="M585 380 h55 v-18 l34 30 l-34 30 v-18 h-55 z" fill="#5E6B78"/>')
  b.append(lines(630, 450, ["ADD DETAILS", "AS NECESSARY"], "b xs", "middle", 13))
  # ---- detailed panel
  bx = {}
  def B(k, x, y, w, h, n, sub=None, cls="box"):
    bx[k] = (x, y, w, h)
    b.append(box(x, y, w, h, n, sub, cls))
  B("proj", 1060, 50, 200, 54, "LionDriver project", "release, user information")
  B("own", 760, 160, 190, 54, "Owner / updater", "C7")
  B("drv", 1100, 160, 190, 54, "Driver", "C1")
  B("op", 900, 310, 230, 60, "openpilot on the SoC", "C2 (C2.1–C2.7)")
  B("pan", 900, 450, 230, 60, "panda safety model", "C3")
  B("cam", 1360, 310, 170, 60, "Stock ADAS camera", "C6")
  B("hb", 1360, 450, 170, 60, "Harness box", "2 analog switches")
  B("eps", 760, 590, 190, 54, "EPS ECU", "C4")
  B("pcm", 1100, 590, 190, 54, "PCM / ACC / brake", "C5")
  B("veh", 760, 690, 770, 50, "Vehicle lateral and longitudinal motion")
  A = lambda pts, mk="ar": b.append(path(pts, "ar", mk))
  # project <-> owner, driver
  A([(1110, 104), (1110, 145), (855, 145), (855, 160)])
  b.append(lbl(862, 139, "Approved releases (CA-20)"))
  A([(1200, 104), (1200, 160)])
  b.append(lbl(1104, 114, "User information\nTraining", "end"))
  A([(1240, 160), (1240, 104)])
  b.append(lbl(1246, 150, "Field reports"))
  # owner -> openpilot
  A([(855, 214), (855, 340), (900, 340)])
  b.append(lbl(800, 260, "Updates\nSettings\n(CA-20, 21)", "end"))
  # driver -> pcm (engage, cancel, accelerator) down the right of openpilot
  A([(1270, 214), (1270, 560), (1250, 560), (1250, 590)])
  b.append(lbl(1276, 520, "SET/RES, brake\nCANCEL, accelerator\n(CA-01, 02, 04)"))
  # openpilot -> driver alerts ; driver -> openpilot DM
  A([(1080, 310), (1080, 240), (1140, 240), (1140, 214)])
  b.append(lbl(1086, 260, "Alerts (CA-07)"))
  A([(1170, 214), (1170, 280), (1110, 280), (1110, 310)])
  b.append(lbl(1176, 276, "Driver camera\n(FB-07)"))
  # openpilot <-> panda
  A([(960, 370), (960, 450)])
  b.append(lbl(954, 398, "Torque, acceleration\nSafety mode, heartbeat\n(CA-05, 06, 08)", "end"))
  A([(1070, 450), (1070, 370)])
  b.append(lbl(1076, 410, "Health (FB-04)"))
  # panda -> harness box (intercept drive)
  A([(1130, 480), (1360, 480)])
  b.append(lbl(1140, 474, "Intercept drive (CA-09)"))
  # camera -> harness box (PCS)
  A([(1445, 370), (1445, 450)])
  b.append(lbl(1451, 400, "PCS, LKA, ACC\n(CA-13)"))
  # harness box -> pcm (pass-through or forwarded)
  A([(1445, 510), (1445, 617), (1290, 617)])
  b.append(lbl(1451, 548, "Stock frames,\npassed through or\nforwarded"))
  # panda -> EPS, PCM
  A([(930, 510), (930, 560), (855, 560), (855, 590)])
  b.append(lbl(800, 556, "0x2E4", "end"))
  A([(1040, 510), (1040, 560), (1150, 560), (1150, 590)])
  b.append(lbl(1046, 552, "0x343"))
  # ECUs -> vehicle
  A([(855, 644), (855, 690)])
  b.append(lbl(861, 672, "Rack torque (CA-11)"))
  A([(1195, 644), (1195, 690)])
  b.append(lbl(1201, 672, "Drive, brake (CA-12)"))
  # feedback: vehicle CAN to panda (left loop)
  A([(780, 690), (780, 664), (720, 664), (720, 480), (900, 480)])
  b.append(lbl(726, 500, "CAN state\n(FB-05)"))
  # road cameras: vehicle scene -> openpilot (far left)
  A([(770, 690), (770, 676), (700, 676), (700, 355), (900, 355)])
  b.append(lbl(706, 372, "Road cameras\n(FB-06)"))
  return svg("Figure 3-2", W, H, "Figure 3-2. Control structure, simple and detailed (WP-A-05 §3)",
             "Left: the hierarchy from the LionDriver project to vehicle motion. Right: the same with the controllers of "
             "§3.2 and §3.4, including the owner/updater, the harness box and the stock camera.", "".join(b))


# ============================================================================ Figures 3-3 … 3-5 control loops
def loop(fig_id, title, desc, S, ctrl, sub, algo, beliefs, wrong, down, up, process, proc_sub, above_in=None, above_out=None,
         side_out=None, side_in=None):
  """Classic STPA control loop: controller with Control Algorithm and Process Model, callouts, actions down, feedback up."""
  ids = re.findall(r"\b(?:CA|FB|LS|UCA)-\d+\b|\bDQ-\d+\b", " ".join(
    [*algo, *beliefs, *[w for x in wrong for w in x], *down, *up, *(above_in or []), *(above_out or []),
     *(side_out or []), *(side_in or [])]))
  S.need(*sorted(set(ids)))
  W, H = 1180, 640
  cx, cy, cw, ch = 380, 120, 420, 150
  b = []
  b.append(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" class="box"/>')
  b.append(T(cx + cw / 2, cy + 112, ctrl, "b", "middle", font_size="17"))
  b.append(T(cx + cw / 2, cy + 132, sub, "m xs", "middle"))
  b.append(f'<rect x="{cx + 14}" y="{cy + 14}" width="150" height="54" class="grey"/>')
  b.append(lines(cx + 89, cy + 37, ["Control", "Algorithm"], "greyt", "middle", 15))
  b.append(f'<rect x="{cx + cw - 164}" y="{cy + 14}" width="150" height="54" class="grey"/>')
  b.append(lines(cx + cw - 89, cy + 37, ["Process Model", "(Beliefs)"], "greyt", "middle", 15))
  # callouts: algorithm (left), beliefs (right) with curved arrows like the classic figure
  b.append(f'<path d="M{cx + 70} {cy + 12} C {cx + 50} {cy - 40}, {cx - 10} {cy - 40}, {cx - 30} {cy + 4}" class="cocurve" marker-end="url(#m-co)"/>')
  b.append(T(cx - 40, cy + 26, "How it decides", "cob", "end"))
  b.append(lines(cx - 40, cy + 42, algo, "co", "end", 14))
  b.append(f'<path d="M{cx + cw - 70} {cy + 12} C {cx + cw - 50} {cy - 40}, {cx + cw + 10} {cy - 40}, {cx + cw + 30} {cy + 4}" class="cocurve" marker-end="url(#m-co)"/>')
  b.append(T(cx + cw + 40, cy + 26, "What it believes", "cob"))
  b.append(lines(cx + cw + 40, cy + 42, beliefs, "co", "start", 14))
  wy = cy + 52 + 14 * len(beliefs)
  b.append(T(cx + cw + 40, wy, "Can be wrong", "wrb"))
  for i, (txt, ls) in enumerate(wrong):
    b.append(T(cx + cw + 40, wy + 16 + i * 15, f"{ls}  ", "wrb"))
    b.append(T(cx + cw + 40 + 8 * len(ls) + 10, wy + 16 + i * 15, txt, "wr"))
  # process
  px, py, pw, ph = 380, 470, 420, 90
  b.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" class="box"/>')
  b.append(T(px + pw / 2, py + 42, process, "b", "middle", font_size="16"))
  b.append(T(px + pw / 2, py + 62, proc_sub, "m xs", "middle"))
  # control actions down, feedback up
  b.append(path([(cx + 120, cy + ch), (cx + 120, py)], "ca", "ca"))
  b.append(lines(cx + 110, cy + ch + 86, down, "s", "end", 16))
  b.append(path([(cx + cw - 120, py), (cx + cw - 120, cy + ch)], "fb", "fb"))
  b.append(lines(cx + cw - 110, cy + ch + 86, up, "s", "start", 16))
  b.append(T(cx + 110, cy + ch + 66, "Control actions", "cob", "end"))
  b.append(T(cx + cw - 110, cy + ch + 66, "Feedback", "cob"))
  # from / to the controller above
  if above_in:
    b.append(path([(cx + 160, 20), (cx + 160, cy)], "ar", "ar"))
    b.append(lines(cx + 154, 36, above_in, "xs", "end", 13))
  if above_out:
    b.append(path([(cx + cw - 160, cy), (cx + cw - 160, 20)], "ar", "ar"))
    b.append(lines(cx + cw - 154, 36, above_out, "xs", "start", 13))
  if side_out:  # an output that goes to another controller
    b.append(path([(cx, cy + ch - 30), (cx - 200, cy + ch - 30), (cx - 200, cy + ch + 60)], "ar", "ar"))
    b.append(lines(cx - 200, cy + ch + 80, side_out, "xs", "middle", 13))
  if side_in:  # other inputs into the process
    b.append(path([(px - 70, py + 45), (px, py + 45)], "ar", "ar"))
    b.append(lines(px - 76, py + 41, side_in, "xs", "end", 13))
  b.append(path([(px + 140, py + ph), (px + 140, py + ph + 40)], "ar", "ar"))
  b.append(path([(px + pw - 140, py + ph + 40), (px + pw - 140, py + ph)], "ar", "ar"))
  return svg(fig_id, W, H, title, desc, "".join(b))


def fig_3_3(S):
  return loop("Figure 3-3", "Figure 3-3. Control loop of the driver, C1 (WP-A-05 §3.2)",
              "The driver's control algorithm and beliefs, the beliefs the loss scenarios show can be wrong, "
              "the driver's control actions and the feedback the driver gets.", S,
              "C1 Driver", "supervises at all times; overrides or disengages",
              ["User information and briefing (WP-O-03)", "Experience with upstream openpilot",
               "Habits from other driver assists"],
              ["LionDriver is engaged, overriding or off", "Steering and speed both controlled",
               "Chill mode does not stop for lights", "Stock emergency braking still works"],
              [("off after a gas press (DQ-022)", "LS-36"), ("steering against it disengages it", "LS-14"),
               ("it yielded to a light correction", "LS-02"), ("it stops at red lights", "LS-03"),
               ("this road is one it handles", "LS-13")],
              ["Engage, resume (CA-01)", "Brake, CANCEL (CA-02)", "Steering (CA-03)", "Accelerator (CA-04)"],
              ["Screen, sounds, siren (FB-01)", "Cluster: cruise, PCS (FB-02)", "Motion, wheel feel (FB-03)"],
              "LionDriver and the vehicle", "C2 … C6 and vehicle motion",
              above_in=["User information, training", "from the LionDriver project"],
              above_out=["Field reports"])


def fig_3_4(S):
  return loop("Figure 3-4", "Figure 3-4. Control loop of openpilot, C2 (WP-A-05 §3.2, §3.4)",
              "openpilot's control algorithm and process model, the beliefs the loss scenarios show can be wrong, "
              "its control actions to the panda and the driver, and its feedback.", S,
              "C2 openpilot (SoC)", "model, planner, controller, supervisor, DM, pandad",
              ["Driving model → planner → controller", "Supervisor: events, alerts, state", "Driver-monitoring escalation"],
              ["Driver attentive and not overriding", "Panda grants authority", "Speed, cruise, brake, gas",
               "Model, plan and calibration valid"],
              [("driver attentive (sunglasses, phone)", "LS-09"), ("lead seen in time", "LS-18"),
               ("learned vehicle parameters right", "LS-26"), ("camera calibration right", "LS-27"),
               ("model output fresh (big model)", "LS-25")],
              ["Lateral torque (CA-05)", "Acceleration (CA-06)", "Safety mode, heartbeat (CA-08)"],
              ["Panda health (FB-04)", "Vehicle CAN state (FB-05)", "Road cameras (FB-06)", "Driver camera (FB-07)"],
              "panda, EPS, PCM, vehicle", "C3 passes or blocks each frame",
              above_in=["Updates, settings (CA-20, 21)", "Engage via PCM cruise"],
              side_out=["Alerts to the", "driver (CA-07)"])


def fig_3_5(S):
  return loop("Figure 3-5", "Figure 3-5. Control loop of the panda safety model, C3 (WP-A-05 §3.2, §3.5)",
              "The panda's safety rules and process model, the beliefs the loss scenarios show can be wrong, "
              "what it does to the EPS, PCM and harness box, and its feedback.", S,
              "C3 panda safety model", "Toyota safety mode on the MCU (reference build)",
              ["Per-frame limits (torque, acceleration)", "Authority: PCM edge + heartbeat engaged",
               "Watchdog, heartbeat, arrival checks"],
              ["controls_allowed", "Cruise engaged; brake, gas pressed", "SoC alive; frames fresh",
               "Intercept switches as commanded"],
              [("brake not pressed (0x226 stuck)", "LS-21"), ("switches passing through", "LS-22"),
               ("switches released after a reset", "LS-33"), ("stock PCS path intact", "LS-32"),
               ("limits match the vehicle", "LS-11")],
              ["Forward 0x2E4, 0x343 (CA-05, 06)", "Block TX, revoke (CA-10)", "Intercept drive (CA-09)"],
              ["Vehicle CAN state (FB-05)", "No feedback of the", "switch position"],
              "EPS, PCM, harness box", "C4, C5 and the stock camera path",
              above_in=["Requests, heartbeat", "(CA-05, 06, 08)"], above_out=["Health (FB-04)"],
              side_out=["Siren to the", "driver (FB-01)"], side_in=["Stock camera", "PCS (CA-13)"])


# ============================================================================ Figure 3-6 inside openpilot
def fig_3_6(S):
  S.need(*[f"CA-{i}" for i in range(14, 23)], "CA-05", "CA-06", "FB-08", "FB-09", "FB-10", "FB-11")
  W, H = 1180, 560
  b = [f'<rect x="20" y="20" width="840" height="320" rx="14" class="grp"/>', T(36, 44, "C2 openpilot on the SoC (§3.4)", "b")]
  nodes = {"C2.6": (60, 70, "C2.6 Calibration, learning", "calibrationd, paramsd, torqued"),
           "C2.1": (330, 70, "C2.1 Driving model", "modeld"),
           "C2.2": (600, 70, "C2.2 Longitudinal planner", "radard, plannerd"),
           "C2.4": (60, 240, "C2.4 Supervisor", "selfdrived"),
           "C2.3": (330, 240, "C2.3 Controller", "controlsd, CarController"),
           "C2.7": (600, 240, "C2.7 Panda interface", "pandad, card init")}
  for _, (x, y, t, p) in nodes.items():
    b.append(f'<rect x="{x}" y="{y}" width="230" height="74" class="box"/>')
    b.append(T(x + 12, y + 28, t, "s b"))
    b.append(T(x + 12, y + 48, p, "m xs"))
  for x, y, w, h, t, s, k in [(920, 70, 230, 74, "C7 Updater, owner settings", "updated; settings UI", "ext"),
                              (600, 440, 230, 56, "C3 panda safety model", "", "env"),
                              (900, 440, 250, 56, "Stock radar / ADAS ECU", "other platforms only", "ext")]:
    f, st = KIND[k]
    b.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{f}" stroke="{st}" stroke-width="1.4"/>')
    b.append(T(x + 12, y + 26, t, "s b"))
    if s:
      b.append(T(x + 12, y + 44, s, "m xs"))
  arrows = [("M290 100 H326", "CA-17", 294, 92, "ca"), ("M560 100 H596", "CA-14", 564, 92, "ca"),
            ("M445 144 V236", "CA-14", 452, 200, "ca"), ("M715 144 V190 H520 V236", "CA-15", 600, 184, "ca"),
            ("M175 144 V190 H380 V236", "CA-17", 230, 184, "ca"), ("M290 277 H326", "CA-16", 294, 270, "ca"),
            ("M445 314 V400 H640 V436", "CA-05 · CA-06", 452, 392, "ca"), ("M700 314 V436", "CA-18 · CA-19", 708, 380, "ca"),
            ("M830 290 H1010 V436", "CA-22", 940, 282, "ca"), ("M920 107 H864", "CA-20 · CA-21", 868, 62, "ca"),
            ("M815 440 V318", "FB-10", 772, 420, "fb")]
  for d, lab, lx, ly, cls in arrows:
    b.append(f'<path d="{d}" class="{cls}" marker-end="url(#m-{cls})"/>')
    b.append(T(lx, ly, lab, "cat" if cls == "ca" else "fbt"))
  b.append(T(20, 536, "Feedback not drawn: FB-08 model and plan validity → C2.3, C2.4 · FB-09 calibration status → C2.4 · "
                      "FB-11 release state → C1", "m s"))
  return svg("Figure 3-6", W, H, "Figure 3-6. Control structure inside openpilot (WP-A-05 §3.4)",
             "C2 opened into its sub-controllers C2.1 to C2.7, with the updater C7, the panda C3 and control actions CA-14 to CA-22.",
             "".join(b))


# ============================================================================ block diagrams (Figures 3-7, 5-2 … 5-5)
class Blocks:
  def __init__(self, S):
    self.S, self.out, self.bx = S, [], {}

  def block(self, k, x, y, title, sub="", kind="item", w=170, h=64):
    self.bx[k] = (x, y, w, h)
    f, s = KIND[kind]
    dash = ' stroke-dasharray="6 4"' if kind == "fix" else ""
    self.out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="{f}" stroke="{s}" class="blk"{dash}/>'
                    f'<rect x="{x}" y="{y}" width="{w}" height="5" rx="2" fill="{s}"/>')
    rows = title.split("\n")
    self.out.append(lines(x + w / 2, y + 24, rows, "bt", "middle", 15))
    if sub:
      self.out.append(lines(x + w / 2, y + 26 + 15 * len(rows), sub.split("\n"), "bs", "middle", 13))

  def group(self, x, y, w, h, label):
    self.out.insert(0, f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="grp"/>' + T(x + 12, y + 18, label, "gl"))

  def port(self, k, side, f=0.5):
    x, y, w, h = self.bx[k]
    return {"l": (x, y + h * f), "r": (x + w, y + h * f), "t": (x + w * f, y), "b": (x + w * f, y + h)}[side]

  def arrow(self, a, b, label="", kind="ca", via=None, lpos=None, anchor="middle"):
    pts = [a] + (via or []) + [b]
    self.out.append(path(pts, kind, kind))
    if label:
      if lpos is None:
        i = len(pts) // 2
        lpos = ((pts[i - 1][0] + pts[i][0]) / 2, (pts[i - 1][1] + pts[i][1]) / 2 - 6)
      cls = {"ca": "cat", "fb": "fbt", "fix": "cat", "dead": "mono"}[kind]
      self.out.append(T(lpos[0], lpos[1], label, cls, anchor))

  def fail(self, x, y, tag, note="", anchor="start"):
    self.S.need(*re.findall(r"\b(?:LS|DQ)-\d+\b", tag + " " + note))
    dx = 16 if anchor == "start" else -16
    self.out.append(f'<circle cx="{x}" cy="{y}" r="11" class="fm"/><path d="M{x-4} {y-4} L{x+4} {y+4} M{x+4} {y-4} L{x-4} {y+4}" class="fx"/>'
                    + T(x + dx, y + 4, tag, "ft", anchor))
    if note:
      self.out.append(lines(x + dx, y + 19, note.split("\n"), "fn", anchor, 13))

  def note(self, x, y, text):
    self.S.need(*re.findall(r"\b(?:LS|DQ|CA|FB)-\d+\b", text))
    self.out.append(lines(x, y, text.split("\n"), "m s", "start", 14))

  def need_text(self, *texts):
    self.S.need(*re.findall(r"\b(?:LS|DQ|CA|FB)-\d+\b", " ".join(texts)))

  def render(self, fig_id, w, h, title, desc):
    return svg(fig_id, w, h, title, desc, "".join(self.out))


def fig_3_7(S):
  d = Blocks(S)
  cols = [(20, "A  Intercepting (normal, engaged)"), (410, "B  Released (panda silent or reset)"), (800, "C  Box supply lost")]
  for i, (gx, lab) in enumerate(cols):
    d.group(gx, 10, 370, 450, lab)
    d.block(f"cam{i}", gx + 20, 50, "Stock camera", "PCS / LKA / ACC", "ext", w=150, h=56)
    d.block(f"car{i}", gx + 200, 50, "Car ADAS bus", "PCM, brake ECU", "ext", w=150, h=56)
    d.block(f"sw{i}", gx + 95, 160, "U1 / U2 switches", ["IN high → intercept", "IN low → pass-through", "unpowered → undefined"][i],
            ["env", "item", "bad"][i], w=180, h=60)
    d.block(f"pd{i}", gx + 20, 280, "R2+R3 pull-down", "240 Ω to GND", "ext" if i == 2 else "item", w=150, h=52)
    d.block(f"vin{i}", gx + 200, 280, "Box supply VIN", "IGN via D1 / comma pwr", "bad" if i == 2 else "item", w=150, h=52)
    d.block(f"pan{i}", gx + 95, 380, "panda (C3)", ["drives SBU1 = 5 V", "SBU1 not driven", "may still run"][i],
            "env" if i == 0 else "ext", w=180, h=56)
    d.arrow(d.port(f"pan{i}", "t"), d.port(f"sw{i}", "b"), "SBU1" if i == 0 else "", "ca" if i == 0 else "dead", lpos=(gx + 200, 360))
    d.arrow(d.port(f"pd{i}", "t"), (gx + 140, 222), "", "fb" if i == 1 else "dead")
    d.arrow(d.port(f"vin{i}", "t"), (gx + 240, 222), "V+, VL", "dead" if i == 2 else "ca", lpos=(gx + 290, 258))
  d.arrow(d.port("cam0", "b"), (140, 158), "camera CAN", "ca", lpos=(90, 140))
  d.arrow((270, 158), d.port("car0", "b"), "panda forwards PCS", "fb", lpos=(330, 140))
  d.note(40, 452, "stock path runs through the panda")
  d.arrow(d.port("cam1", "r"), d.port("car1", "l"), "direct, through powered switches", "fix", lpos=(595, 44))
  d.note(430, 452, "release relies on the pull-down")
  d.fail(440, 352, "LS-33  R2/R3 open: stays in intercept")
  d.arrow(d.port("cam2", "r"), d.port("car2", "l"), "PCS path may be cut", "dead", lpos=(985, 44))
  d.fail(830, 133, "LS-32  undefined; clamps load both buses")
  d.note(820, 452, "nothing in the item sees this")
  return d.render("Figure 3-7", 1180, 470, "Figure 3-7. Harness box: three states of the intercept switches (WP-A-05 §3.5)",
                  "Stock camera, the two DG419LE switches, the pull-down, the box supply and the panda in the intercepting, "
                  "released and unpowered states, after RR-2026-010.")


def fig_5_3(S):
  d = Blocks(S)
  d.block("drv", 20, 40, "Driver", "hands on wheel", "drv", w=150)
  d.block("rack", 20, 300, "Steering rack", "driver + EPS torque add", "ext", w=150)
  d.block("sens", 240, 40, "Torque sensor 0x260", "steeringPressed > 100 raw", "item", w=190)
  d.block("sm", 500, 40, "selfdrived (C2.4)", "state → overriding", "item", w=180)
  d.block("ctl", 750, 40, "controlsd (C2.3)", "latActive stays true", "bad", w=180)
  d.block("cc", 750, 170, "CarController", "torque continues;\nintegrator only frozen", "bad", w=180, h=70)
  d.block("pan", 500, 170, "panda limits (C3)", "1500 raw, no\ndriver-torque term", "bad", w=180, h=70)
  d.block("eps", 240, 300, "EPS ECU (C4)", "applies LKA torque", "ext", w=190)
  d.block("ui", 980, 40, "UI", "grey border only;\nno text, no sound", "bad", w=180, h=64)
  d.block("fix1", 980, 170, "Decided: back off", "DQ-053 · TSR-304,\nSWF-ACT-046", "fix", w=180, h=70)
  d.block("fix2", 980, 300, "Decided: show a cue", "DQ-053 · CC-2", "fix", w=180, h=64)
  d.need_text("DQ-053")
  d.arrow(d.port("drv", "r"), d.port("sens", "l"), "torque")
  d.arrow(d.port("sens", "r"), d.port("sm", "l"))
  d.arrow(d.port("sm", "r"), d.port("ctl", "l"))
  d.arrow(d.port("ctl", "b"), d.port("cc", "t"))
  d.arrow(d.port("cc", "l"), d.port("pan", "r"), "0x2E4")
  d.arrow(d.port("pan", "b"), d.port("eps", "r"), "passes in-limit torque", via=[(590, 332)], lpos=(520, 326))
  d.arrow(d.port("eps", "l"), d.port("rack", "r"))
  d.arrow(d.port("drv", "b"), d.port("rack", "t"))
  d.arrow(d.port("sm", "t", .8), d.port("ui", "t", .3), "", "fb", via=[(644, 22), (1034, 22)])
  d.arrow(d.port("fix1", "l"), d.port("cc", "r"), "", "fix")
  d.arrow(d.port("fix2", "r"), d.port("ui", "r"), "", "fix", via=[(1172, 332), (1172, 72)])
  d.fail(335, 120, "LS-02", "below 100 raw:\nnot detected at all")
  d.fail(840, 132, "LS-01", "", "end")
  d.fail(590, 255, "LS-01", "panda has no\noverride check", "end")
  d.fail(1070, 120, "LS-14", "driver thinks it\ndisengaged", "end")
  d.note(20, 410, "Steering only overrides; it never disengages (state.py:43). STEER_THRESHOLD 100 raw (values.py:585); panda maximum 1500 raw (toyota.h:299).")
  return d.render("Figure 5-3", 1180, 430, "Figure 5-3. The driver steers against LionDriver: LS-01, LS-02, LS-14 (WP-A-05 §5)",
                  "The driver's torque and the item's torque add at the rack. Where detection, the state machine, the controller "
                  "and the panda limits let the torque continue, and where the decided fix (DQ-053) applies.")


def fig_5_4(S):
  d = Blocks(S)
  d.block("pan", 20, 60, "panda (C3)", "revokes authority", "env", w=170)
  d.block("ps", 250, 60, "pandaStates", "health report", "item", w=150)
  d.block("sd", 460, 60, "selfdrived", "controlsMismatch,\npandaTxBlocked, …", "item", w=170, h=70)
  d.block("ui", 690, 20, "ui", "screen", "bad", w=150)
  d.block("snd", 690, 150, "soundd", "speaker", "bad", w=150)
  d.block("drv", 990, 75, "Driver", "takes over", "drv", w=170)
  d.block("siren", 250, 240, "panda siren", "heartbeat loss;\nEPS fault ≥ 1 s", "env", w=170, h=70)
  d.block("clu", 460, 260, "Cluster", "cruise icon only", "ext", w=150)
  d.arrow(d.port("pan", "r"), d.port("ps", "l"), "", "fb")
  d.arrow(d.port("ps", "r"), d.port("sd", "l"), "≤ 0.5 s", "fb")
  d.arrow(d.port("sd", "r", .3), d.port("ui", "l"))
  d.arrow(d.port("sd", "r", .7), d.port("snd", "l"))
  d.arrow(d.port("ui", "r"), d.port("drv", "l", .3))
  d.arrow(d.port("snd", "r"), d.port("drv", "l", .7))
  d.arrow(d.port("pan", "b"), d.port("siren", "l"), via=[(105, 275)])
  d.arrow(d.port("siren", "b"), d.port("drv", "b", .7), "independent of the SoC", via=[(335, 360), (1109, 360)], lpos=(720, 354))
  d.arrow(d.port("clu", "r"), d.port("drv", "b", .3), "", "fb", via=[(1041, 292)])
  d.fail(700, 248, "LS-20", "a hung ui/soundd\nmutes every SoC alert")
  d.fail(200, 330, "LS-04", "siren silent after a watchdog\nreset (fix decided: DQ-054)", "end")
  d.fail(115, 175, "LS-15", "EPS fault while touching\nthe wheel: no SoC alert")
  return d.render("Figure 5-4", 1180, 400, "Figure 5-4. How a take-over request reaches the driver: LS-04, LS-15, LS-20 (WP-A-05 §5)",
                  "Every SoC alert passes through ui and soundd; the panda siren covers only heartbeat loss and a persistent EPS fault.")


def fig_5_5(S):
  d = Blocks(S)
  d.block("cam", 20, 50, "Driver camera", "face, eyes, wheel touch", "item", w=160)
  d.block("dm", 220, 50, "dmonitoringd", "awareness 1 → 0", "item", w=160)
  d.block("a1", 420, 20, "Alert 1", "5 s", "item", w=110, h=52)
  d.block("a2", 420, 82, "Alert 2", "8 s / 15 s", "item", w=110, h=52)
  d.block("a3", 570, 50, "Alert 3", "13 s vision\n25 s wheel-touch", "bad", w=150, h=70)
  d.block("fd", 760, 50, "forceDecel", "+5 s at alert 3", "item", w=150)
  d.block("pl", 950, 50, "Planner", "cruise target → 0", "item", w=160)
  d.block("stop", 950, 200, "Stops in lane", "still steering", "env", w=160)
  d.block("miss", 570, 200, "Not there today", "warning of the stop, lockout;\nhold rests on PCM (AOU-16)", "bad", w=200, h=70)
  d.block("q", 330, 200, "Decided (DQ-365)", "stop, stay held, no\nre-engage until driver", "fix", w=200, h=70)
  d.need_text("DQ-365 DQ-205")
  d.arrow(d.port("cam", "r"), d.port("dm", "l"), "", "fb")
  d.arrow(d.port("dm", "r", .3), d.port("a1", "l"))
  d.arrow(d.port("dm", "r", .7), d.port("a2", "l"))
  d.arrow(d.port("a2", "r"), d.port("a3", "l", .7))
  d.arrow(d.port("a3", "r"), d.port("fd", "l"))
  d.arrow(d.port("fd", "r"), d.port("pl", "l"))
  d.arrow(d.port("pl", "b"), d.port("stop", "t"), "brakes", lpos=(1040, 182), anchor="start")
  d.arrow(d.port("q", "r"), d.port("miss", "l"), "", "fix")
  d.fail(100, 130, "LS-09", "sunglasses, low light:\nfalls back to 25 s")
  d.fail(645, 135, "LS-35", "", "end")
  d.note(20, 310, "From inattention to the slow-down: about 18 s (vision) or 30 s (wheel-touch). policy.py:31-44, 418-437; controlsd.py:236; longitudinal_planner.py:84.")
  return d.render("Figure 5-5", 1180, 330, "Figure 5-5. The driver stops responding: LS-09, LS-35 (WP-A-05 §5)",
                  "Driver camera, monitoring policy, alert levels with their times, forced deceleration and the stop in the lane.")


def fig_5_6(S):
  d = Blocks(S)
  d.block("drv", 20, 60, "Driver", "presses to pass", "drv", w=150)
  d.block("pcm", 220, 60, "PCM", "GAS_RELEASED = 0", "ext", w=150)
  d.block("sd", 420, 60, "selfdrived", "override (longitudinal)", "item", w=170)
  d.block("ui", 640, 60, "UI", "grey border only", "bad", w=150)
  d.block("bel", 840, 60, "Driver belief", "\"it switched off\"", "bad", w=150)
  d.block("res", 840, 170, "On release", "speed control resumes:\nbrakes or accelerates", "env", w=170, h=70)
  d.block("fix", 420, 170, "Decided (DQ-022)", "keep behaviour, add an\non-screen override alert", "fix", w=210, h=70)
  d.need_text("DQ-022")
  d.arrow(d.port("drv", "r"), d.port("pcm", "l"), "pedal")
  d.arrow(d.port("pcm", "r"), d.port("sd", "l"), "", "fb")
  d.arrow(d.port("sd", "r"), d.port("ui", "l"))
  d.arrow(d.port("ui", "r"), d.port("bel", "l"))
  d.arrow(d.port("bel", "b"), d.port("res", "t"))
  d.arrow(d.port("fix", "t", .8), d.port("ui", "b"), "", "fix", via=[(588, 140), (715, 140)])
  d.fail(915, 52, "LS-36", "", "end")
  return d.render("Figure 5-6", 1180, 260, "Figure 5-6. Accelerator override and release: LS-36 (WP-A-05 §5)",
                  "Accelerator, PCM, override state, UI and the resume on release; the decided override alert (DQ-022).")


# ============================================================================ Figure 4-1 UCA grid
def fig_4_1(S):
  order = ["C1 Driver", "C2 openpilot", "C2.1 Driving model", "C2.2 Planner", "C2.4 Supervisor", "C2.6 Calibration",
           "C2.7 Panda interface", "C3 panda", "C7 Updater / owner"]
  order += sorted({u["ctrl"] for u in S.ucas.values()} - set(order))
  grid = defaultdict(list)
  for uid, u in S.ucas.items():
    grid[(u["ctrl"], u["type"])].append(uid)
  types = [("N", "Not provided"), ("P", "Provided, unsafe"), ("T", "Too early / late"), ("D", "Too long / short")]
  x0, cw = 220, 230
  heights = [14 + 26 * ((max([len(grid[(c, t)]) for t, _ in types] + [1]) + 2) // 3) for c in order]
  W, H = x0 + cw * 4 + 20, 120 + sum(heights)
  b = [T(20, 40, "CONTROLLER", "h")]
  for i, (t, lab) in enumerate(types):
    b.append(T(x0 + i * cw + 10, 40, f"{t}  {lab.upper()}", "h"))
  y = 54
  for c, hgt in zip(order, heights):
    b.append(f'<line x1="20" y1="{y}" x2="{W - 20}" y2="{y}" class="grid"/>')
    b.append(T(20, y + 22, c, "s b"))
    for i, (t, _) in enumerate(types):
      for k, uid in enumerate(sorted(grid[(c, t)], key=lambda u: int(u.split("-")[1]))):
        st = S.worst(uid)
        b.append(chip(x0 + i * cw + 10 + (k % 3) * 72, y + 8 + (k // 3) * 26, uid, st,
                      title=f"{uid}: {S.ucas[uid]['text'][:150]} ({STATUS_LABEL[st]})"))
    y += hgt
  b.append(f'<line x1="20" y1="{y}" x2="{W - 20}" y2="{y}" class="grid"/>')
  x = 20
  for k in ["covered", "known_gap", "new", "open_test", "external"]:
    b.append(chip(x, y + 24, "", k, w=26, h=14))
    b.append(T(x + 32, y + 35, STATUS_LABEL[k], "m xs"))
    x += 180
  return svg("Figure 4-1", W, H, "Figure 4-1. Unsafe control actions by controller and type (WP-A-05 §4)",
             "Each chip is one UCA, coloured by the worst status among its loss scenarios in stpa-map.yaml.", "".join(b))


# ============================================================================ Figure 5-1 causal loop map
def classify(t):
  t = t.lower()
  for key, grp in (("external", "ext"), ("actuator", "act"), ("control path", "act"), ("feedback", "fb"), ("sensor", "fb"),
                   ("process model", "pm"), ("algorithm", "alg"), ("component failure", "alg"), ("control loop", "alg"),
                   ("release", "input"), ("installation", "input"), ("unsafe control input", "input"),
                   ("configuration", "input"), ("unsafe control action", "input"), ("common cause", "alg")):
    if key in t:
      return grp
  return "ext"


def fig_5_1(S):
  groups = defaultdict(list)
  for lid, t in S.ls_type.items():
    groups[classify(t)].append(lid)
  W, H = 1180, 640
  b = [f'<rect x="370" y="30" width="440" height="200" class="box"/>', T(590, 56, "Controller (C1, C2, C3)", "b", "middle"),
       f'<rect x="386" y="70" width="200" height="146" class="grey"/>', T(486, 90, "Control algorithm", "greyt", "middle"),
       f'<rect x="594" y="70" width="200" height="146" class="grey"/>', T(694, 90, "Process model", "greyt", "middle"),
       f'<rect x="60" y="290" width="280" height="110" class="box"/>', T(200, 314, "Actuator / control path", "b", "middle"),
       T(200, 330, "panda TX, harness box, EPS, PCM", "m xs", "middle"),
       f'<rect x="370" y="440" width="440" height="80" class="box"/>', T(590, 472, "Controlled process", "b", "middle"),
       T(590, 490, "vehicle lateral and longitudinal motion", "m xs", "middle"),
       f'<rect x="840" y="290" width="280" height="130" class="box"/>', T(980, 314, "Sensors / feedback", "b", "middle"),
       T(980, 330, "CAN state, cameras, HMI, health", "m xs", "middle"),
       path([(370, 150), (200, 150), (200, 286)], "ca", "ca"), path([(200, 400), (200, 480), (366, 480)], "ca", "ca"),
       path([(810, 480), (980, 480), (980, 424)], "fb", "fb"), path([(980, 290), (980, 150), (814, 150)], "fb", "fb"),
       T(210, 142, "control action", "cat"), T(840, 142, "feedback", "fbt")]

  def tags(x, y, ids, maxw):
    out, cx, cy = [], x, y
    for lid in sorted(ids, key=lambda s: int(s.split("-")[1])):
      if cx + 50 > x + maxw:
        cx, cy = x, cy + 24
      out.append(chip(cx, cy, lid, S.scen[lid]["status"], w=46, h=18, title=f"{lid}: {S.ls_type[lid]}"))
      cx += 50
    return "".join(out)
  b.append(tags(396, 102, groups["alg"], 190))
  b.append(tags(604, 102, groups["pm"], 190))
  b.append(tags(72, 344, groups["act"], 260))
  b.append(tags(852, 344, groups["fb"], 260))
  b.append(T(40, 556, "Unsafe input, configuration, release", "m xs b"))
  b.append(tags(40, 566, groups["input"], 400))
  b.append(T(840, 556, "Other controllers (assumptions)", "m xs b"))
  b.append(tags(840, 566, groups["ext"], 300))
  x = 40
  for k in ["covered", "known_gap", "new", "open_test"]:
    b.append(chip(x, 606, "", k, w=26, h=14))
    b.append(T(x + 32, 617, STATUS_LABEL[k], "m xs"))
    x += 150
  return svg("Figure 5-1", W, H, "Figure 5-1. Where the loss scenarios sit in the control loop (WP-A-05 §5)",
             "Each loss scenario placed on the element of the generic STPA control loop that its causal-factor type names, "
             "coloured by its status in stpa-map.yaml.", "".join(b))


# ============================================================================ Figure 5-2 decisions -> scenarios
def fig_5_2(S):
  # Only the IDs come from the register (checked to exist); status and wording are left out on purpose, because
  # every session edits the register and this figure must not go stale when an unrelated answer is recorded.
  dq_ls = defaultdict(list)
  for s in S.smap["scenarios"]:
    if s["status"] in ("known_gap", "new"):
      for d in s.get("decisions", []):
        dq_ls[d].append(s["id"])
  S.need(*dq_ls)
  order = sorted(dq_ls, key=lambda d: (-len(dq_ls[d]), int(d.split("-")[1])))
  W, rh = 1180, 34
  H = 90 + rh * len(order)
  b = [T(20, 30, "DECISION (REGISTER ID)", "h"), T(220, 30, "OPEN SCENARIOS IT DECIDES OR WAITS ON", "h")]
  for i, d in enumerate(order):
    y = 44 + i * rh
    b.append(f'<line x1="20" y1="{y + rh - 4}" x2="{W - 20}" y2="{y + rh - 4}" class="grid"/>')
    b.append(T(20, y + 18, d, "s b"))
    b.append(T(90, y + 18, f"{len(dq_ls[d])} scenario" + ("s" if len(dq_ls[d]) > 1 else ""), "m xs"))
    for k, lid in enumerate(sorted(dq_ls[d], key=lambda s: int(s.split("-")[1]))):
      b.append(chip(220 + k * 52, y + 4, lid, S.scen[lid]["status"], w=46))
  b.append(T(20, H - 30, "Status and wording of each decision: the decision inbox (register.yaml). Chip colour: the scenario's status.", "m xs"))
  return svg("Figure 5-2", W, H, "Figure 5-2. Lead decisions and the open scenarios they address (WP-A-05 §5.6)",
             "Each decision cited by a known-gap or new scenario in stpa-map.yaml, and the scenarios it decides or waits on.",
             "".join(b))


FIGURES = {
  "fig-a05-2-1-losses-hazards-goals.svg": fig_2_1,
  "fig-a05-3-1-stpa-control-structure.svg": fig_3_1,
  "fig-a05-3-2-control-structure-simple-detailed.svg": fig_3_2,
  "fig-a05-3-3-loop-driver.svg": fig_3_3,
  "fig-a05-3-4-loop-openpilot.svg": fig_3_4,
  "fig-a05-3-5-loop-panda.svg": fig_3_5,
  "fig-a05-3-6-inside-openpilot.svg": fig_3_6,
  "fig-a05-3-7-harness-box-states.svg": fig_3_7,
  "fig-a05-4-1-uca-grid.svg": fig_4_1,
  "fig-a05-5-1-scenarios-in-loop.svg": fig_5_1,
  "fig-a05-5-2-decisions-scenarios.svg": fig_5_2,
  "fig-a05-5-3-steering-override.svg": fig_5_3,
  "fig-a05-5-4-takeover-paths.svg": fig_5_4,
  "fig-a05-5-5-unresponsive-driver.svg": fig_5_5,
  "fig-a05-5-6-accelerator-override.svg": fig_5_6,
}


def build() -> dict[str, str]:
  S = load()
  out = {name: fn(S) for name, fn in FIGURES.items()}
  out.update(stpa_scenes.sheets(S, sys.modules[__name__]))  # Figures 4-2 … 4-4, one scene sheet per controller
  return out


def main(argv: list[str]) -> int:
  check = "--check" in argv
  try:
    out = build()
  except ParseError as e:
    print(f"fig_a05_stpa: {e}", file=sys.stderr)
    return 1
  stale = []
  for name, content in out.items():
    p = HERE / name
    if check:
      if not p.exists() or p.read_text(encoding="utf-8") != content:
        stale.append(name)
    else:
      p.write_text(content, encoding="utf-8")
  if stale:
    print("stale STPA figures; run fig_a05_stpa.py: " + ", ".join(stale), file=sys.stderr)
    return 1
  print(f"fig_a05_stpa: {len(out)} figures {'current' if check else 'written'}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
