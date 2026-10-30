#!/usr/bin/env python3
"""Draw the two figures at the top of the concept folder's index page and write that part of the page (index-top.md).

- Figure C-0-1 (`fig-c00-1-concept-flow.svg`), the concept phase on one page: one box per work product, top to bottom
  in the order of the activities CON-01 to CON-15 of assurance/process/model/concept.yaml, the four lanes (functional
  safety, SOTIF, cybersecurity, AI) ending in the hazard log and argument structure, then gate G1 and system design.
  The dashed connectors are the G1 rows of assurance/process/model/interfaces.yaml. Each box carries the number of
  defined rows of its document's table and a status chip from the WP-M-00 §3 register.
- Figure C-0-2 (`fig-c00-2-one-hazard.svg`), follow one hazard: the EPS torque command of WP-C-01 → the highway
  situation → HE-01.2 → SG-01 → the FSRs of WP-C-04 that limit the torque → the 3D scene of the gallery. Every value
  is read from the documents; the build fails if HE-01.2 no longer rolls up to SG-01, or if a drawn FSR no longer
  serves SG-01 or no longer says what its label says.

folder_index.py places index-top.md at the top of 02-concept/README.md, its links rebased. The thumbnail at the end
of Figure C-0-2 (`fig-c00-2-thumb.jpg`, the 3D view cropped from the committed dashboard) is rebuilt only when Pillow
is installed; the SVG embeds the committed file, so --check needs no Pillow.

    python3 fig_c00_overview.py            # write both SVGs and index-top.md (and the thumbnail, with Pillow)
    python3 fig_c00_overview.py --check    # fail if a source cannot be read, the chain changed, or an output is stale

Output is deterministic. Needs PyYAML.
"""

from __future__ import annotations

import base64
import re
import struct
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

HERE = Path(__file__).resolve().parent
CONCEPT = HERE.parent
ASSURANCE = HERE.parents[1]
FOLDER = "02-concept"
MODEL = ASSURANCE / "process" / "model"
DASH = ASSURANCE / "sim" / "blender" / "dashboards"
OUT_A, OUT_D, SECTION = "fig-c00-1-concept-flow.svg", "fig-c00-2-one-hazard.svg", "index-top.md"
THUMB = HERE / "fig-c00-2-thumb.jpg"
THUMB_CROP, THUMB_SIZE, THUMB_MAX_BYTES = (322, 55, 1232, 566), (440, 247), 60_000  # the 3D view of a dashboard
sys.path.insert(0, str(ASSURANCE / "01-management" / "figures"))
import folder_index  # noqa: E402
from figkit import FigureError, col, plain, section, table, text_w  # noqa: E402
sys.path.insert(0, str(HERE))
import fig_c05_four_areas  # noqa: E402  (SOTIF counts)
import fig_c10_concept_view  # noqa: E402  (cybersecurity goals)
sys.path.insert(0, str(ASSURANCE / "trace" / "tools"))
import terms  # noqa: E402  (each figure ends with the definitions of its terms)

DOC = {
  "WP-C-01": "WP-C-01-item-definition.md", "WP-C-02": "WP-C-02-odd-and-intended-functionality.md",
  "WP-C-03": "WP-C-03-hara.md", "WP-C-04": "WP-C-04-functional-safety-concept.md",
  "WP-C-05": "WP-C-05-sotif-hazard-identification.md",
  "WP-C-06": "WP-C-06-sotif-insufficiencies-triggering-conditions.md",
  "WP-C-07": "WP-C-07-sotif-functional-modifications.md", "WP-C-08": "WP-C-08-driver-hmi-misuse-analysis.md",
  "WP-C-09": "WP-C-09-tara.md", "WP-C-10": "WP-C-10-cybersecurity-goals-and-concept.md",
  "WP-C-11": "WP-C-11-ai-system-definition-and-safety-requirements.md",
  "WP-C-12": "WP-C-12-item-and-environment-models.md",
}
# Box titles (the work product in a few words) and the short name used in "after:" lines and the link labels
TITLE = {
  "WP-C-01": "Item and its boundary", "WP-C-12": "Item and environment models",
  "WP-C-02": "ODD and intended functionality", "WP-C-08": "Driver, HMI and misuse analysis",
  "WP-C-03": "HARA", "WP-C-04": "Functional safety concept",
  "WP-C-05": "SOTIF hazards and acceptance criteria", "WP-C-06": "Insufficiencies and triggering conditions",
  "WP-C-07": "Functional modifications", "WP-C-09": "TARA", "WP-C-10": "Cybersecurity goals and concept",
  "WP-C-11": "AI system and AI safety requirements",
}
SHORT = {"WP-C-01": "item", "WP-C-02": "ODD", "WP-C-03": "HARA", "WP-C-04": "FSC", "WP-C-05": "SOTIF hazards",
         "WP-C-06": "insufficiencies", "WP-C-07": "modifications", "WP-C-08": "driver analysis", "WP-C-09": "TARA",
         "WP-C-10": "cyber goals", "WP-C-11": "AI requirements", "WP-C-12": "models"}
TOP = [["WP-C-01", "WP-C-12"], ["WP-C-02"], ["WP-C-08"]]
LANES = [("fs", "Functional safety", "ISO 26262-3", ["WP-C-03", "WP-C-04"]),
         ("so", "SOTIF", "ISO 21448", ["WP-C-05", "WP-C-06", "WP-C-07"]),
         ("cy", "Cybersecurity", "ISO/SAE 21434", ["WP-C-09", "WP-C-10"]),
         ("ai", "AI", "ISO/PAS 8800", ["WP-C-11"])]
CHIP = {"fs": "Func. safety", "so": "SOTIF", "cy": "Cyber", "ai": "AI"}   # lane names on the narrow chips
END_ACTIVITY = "CON-13"   # hazard log and argument structure: every lane feeds it
# A few words for each G1 interface of interfaces.yaml; the build fails when the G1 rows and these keys differ
IX_LABEL = {
  "IX-01": "cyber effects rated on the HARA hazards",
  "IX-02": "cybersecurity goals protect the safety goals",
  "IX-03": "one hazard log for HARA and SOTIF hazards",
  "IX-04": "driver monitoring: a misuse measure, no ASIL",
  "IX-05": "driver-monitoring targets are AI requirements",
  "IX-06": "ODD claimed only where evaluation data covers it",
  "IX-07": "model files load without a signature",
  "IX-08": "FSC transition rule implemented by FM-03",
}

# Figure C-0-2: the thread, and the FSRs drawn with the words each requirement must still contain
CHAIN_HE, CHAIN_SG = "HE-01.2", "SG-01"
CHAIN_FSR = [("FSR-01.01", "torque magnitude limit", "torque magnitude"),
             ("FSR-01.02", "torque rate limit", "rate of change of the commanded LKA torque"),
             ("FSR-01.03", "torque tracks the measured EPS torque", "measured EPS motor torque"),
             ("FSR-01.13", "EPS keeps LKA torque overpowerable", "overpowerable")]
SCENE = "he-01-2-hardover-adjacent"

W, X0 = 500, 16
CW = 380                       # content width; the gutter on the right carries the interface connectors
XR = X0 + CW                   # right edge of the content
TRACK0, TRACK_STEP = XR + 22, 9
FONT = "-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
STYLE = """<style>
svg { --bg:#ffffff; --ink:#0b0b0b; --ink2:#52514e; --ink3:#8a8984; --grid:#e3e2de; --card:#f7f7f5;
      --amb:#c98500; --amb-bg:#fdf4dc; --ok:#2e9e6a; --ok2:#166534;
      --fs:#c2410c; --fs-bg:#fff4ec; --so:#0f766e; --so-bg:#eaf6f3; --cy:#7c3aed; --cy-bg:#f3effd;
      --ai:#2563eb; --ai-bg:#edf3fe; --gate:#0b0b0b; }
@media (prefers-color-scheme: dark) {
  svg { --bg:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --ink3:#8d8c85; --grid:#3a3936; --card:#232321;
        --amb:#eda100; --amb-bg:#3a2f12; --ok:#3fb97d; --ok2:#2f9e5f;
        --fs:#f2885a; --fs-bg:#2c1c13; --so:#3cc4ae; --so-bg:#112826; --cy:#ab8df6; --cy-bg:#221a35;
        --ai:#71a3f6; --ai-bg:#132238; --gate:#f0efec; }
}
.bg { fill:var(--bg); }
text { font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif; }
.h { font-weight:600; font-size:20px; fill:var(--ink); }
.tb { font-weight:600; font-size:14px; fill:var(--ink); }
.t2 { font-size:13px; fill:var(--ink2); }
.t3 { font-size:12px; fill:var(--ink3); }
.ti { font-size:12px; font-style:italic; fill:var(--ink2); }
.nb { font-weight:700; font-size:10.5px; fill:var(--bg); }
.gt { font-weight:700; font-size:14px; fill:var(--bg); }
.terms text { font-size:11px; fill:var(--ink2); }
.box { fill:var(--bg); stroke:var(--grid); stroke-width:1.2; }
.card { fill:var(--card); stroke:var(--grid); stroke-width:1.2; }
.hair { stroke:var(--grid); stroke-width:1; }
.arr { stroke:var(--ink2); stroke-width:1.5; fill:none; }
.ix { stroke:var(--ink2); stroke-width:1.3; fill:none; stroke-dasharray:4 3; }
.dot { fill:var(--ink2); } .badge { fill:var(--ink); }
.gate { fill:var(--gate); }
.s-skel { fill:var(--bg); stroke:var(--ink3); stroke-width:1.4; stroke-dasharray:4 3; }
.s-draft { fill:var(--amb); } .s-rev { fill:var(--amb-bg); stroke:var(--amb); stroke-width:1.6; }
.s-appr { fill:var(--ok); } .s-base { fill:var(--ok2); }
.s-na { fill:var(--bg); stroke:var(--grid); stroke-width:1.2; stroke-dasharray:2 2; }
.fs { fill:var(--fs); } .so { fill:var(--so); } .cy { fill:var(--cy); } .ai { fill:var(--ai); }
.fs-band { fill:var(--fs-bg); stroke:var(--fs); stroke-width:1.2; }
.so-band { fill:var(--so-bg); stroke:var(--so); stroke-width:1.2; }
.cy-band { fill:var(--cy-bg); stroke:var(--cy); stroke-width:1.2; }
.ai-band { fill:var(--ai-bg); stroke:var(--ai); stroke-width:1.2; }
.fs-l { stroke:var(--fs); } .so-l { stroke:var(--so); } .cy-l { stroke:var(--cy); } .ai-l { stroke:var(--ai); }
.fs-t { font-weight:700; font-size:13px; fill:var(--fs); } .so-t { font-weight:700; font-size:13px; fill:var(--so); }
.cy-t { font-weight:700; font-size:13px; fill:var(--cy); } .ai-t { font-weight:700; font-size:13px; fill:var(--ai); }
</style>"""
SIZE = {"h": 20, "tb": 14, "t2": 13, "t3": 12, "ti": 12, "fs-t": 13, "so-t": 13, "cy-t": 13, "ai-t": 13, "gt": 14}
BOLD = {"h", "tb", "fs-t", "so-t", "cy-t", "ai-t", "gt"}
MARKER = ('<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
          'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="dot"/></marker>')


class OverviewError(FigureError):
  pass


# ---------------------------------------------------------------- SVG helpers

def fmt(v: float) -> str:
  return f"{v:.1f}".rstrip("0").rstrip(".")


def el(tag: str, content: str | None = None, **attrs) -> str:
  a = "".join(f' {k.rstrip("_").replace("_", "-")}="{fmt(v) if isinstance(v, float) else v}"'
              for k, v in attrs.items() if v not in ("", None))
  return f"<{tag}{a}/>" if content is None else f"<{tag}{a}>{escape(content)}</{tag}>"


def T(x, y, s, cls="t2", anchor="") -> str:
  return el("text", s, x=float(x), y=float(y), class_=cls, text_anchor=anchor)


def R(x, y, w, h, cls, rx=8) -> str:
  return el("rect", None, x=float(x), y=float(y), width=float(w), height=float(h), rx=rx, class_=cls)


def wrap(s: str, width: float, cls: str) -> list[str]:
  out, cur = [], ""
  for wd in s.split():
    cand = (cur + " " + wd).strip()
    if cur and text_w(cand, SIZE[cls], cls in BOLD) > width:
      out.append(cur)
      cur = wd
    else:
      cur = cand
  return out + ([cur] if cur else [])


def chip(x, y, status: str, names: dict) -> tuple[list[str], float]:
  """The index-status chip (same classes as folder_index.py) and the status word; returns (svg, width)."""
  word = names[status]
  return ([R(x, y - 10, 22, 12, folder_index.STATUS_CLS[status], rx=6), T(x + 27, y, word, "t3")],
          27 + text_w(word, 12) + 4)


def svg_doc(h: float, title: str, desc: str, body: list[str]) -> str:
  head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{int(h)}" viewBox="0 0 {W} {int(h)}" '
          'role="img" aria-labelledby="t d">')
  return "\n".join([head, el("title", title, id="t"), el("desc", desc, id="d"), STYLE, f"<defs>{MARKER}</defs>",
                    f'<rect class="bg" width="{W}" height="{int(h)}"/>', *body, "</svg>"]) + "\n"


def footer(body: list[str], y: float, script: str) -> tuple[list[str], float]:
  extra, y = terms.svg_footer(body, X0, y, W - 2 * X0, size=11)
  return extra + [T(W - X0, y + 8, f"Generated by {script}", "t3", "end")], y + 22


# ---------------------------------------------------------------- sources

def doc(wid: str) -> str:
  return (CONCEPT / DOC[wid]).read_text(encoding="utf-8")


def rows(md: str, start: str, end: str, pattern: str) -> list[str]:
  """IDs of the table rows of md between the headings start and end whose first cell matches pattern."""
  i = md.find(start)
  if i < 0:
    raise OverviewError(f"heading {start!r} not found")
  j = md.find(end, i + len(start))
  return re.findall(rf"^\| \**({pattern})\** \|", md[i:j if j > 0 else None], re.M)


def counts() -> dict[str, int]:
  """Defined rows of each document's table (not every ID mentioned)."""
  c03 = doc("WP-C-03")
  he = []
  for blk in re.split(r"^### ", section(c03, "## 5. "), flags=re.M):
    head = blk.split("\n|---", 1)[0].splitlines()[-1] if "\n|---" in blk else ""
    if head.startswith("| HE | Situation"):
      he += re.findall(r"^\| (HE-\d\d\.\d+) \|", blk, re.M)
  stated = re.search(r"Representative hazardous events recorded in §5: (\d+)", c03)
  if not stated or int(stated.group(1)) != len(he):
    raise OverviewError(f"WP-C-03 §5 has {len(he)} HE rows, §2.1 states {stated.group(1) if stated else 'none'}")
  sotif = fig_c05_four_areas.sotif_counts()
  out = {"HE": len(he), "SG": len(rows(c03, "## 6. Safety goals", "\n### 6.1", r"SG-\d\d")),
         "FSR": len(rows(doc("WP-C-04"), "## 5. Functional safety requirements", "\n## 6.", r"FSR-\d\d\.\d\d")),
         "SH": sotif["sh"], "FI": sotif["fi"], "TC": sotif["tc"],
         "FM": len(rows(doc("WP-C-07"), "## 2. Summary", "\n## 3.", r"FM-\d\d")),
         "TS": len(rows(doc("WP-C-09"), "## 4. Threat scenarios", "\n## 5.", r"TS-\d\d")),
         "CSG": len(fig_c10_concept_view.parse(doc("WP-C-10"))["goals"]),
         "AIR": len(rows(doc("WP-C-11"), "## 6. AI safety requirements", "\n## 7.", r"AIR-\d\d"))}
  for k, v in out.items():
    if not v:
      raise OverviewError(f"no {k} rows found; a heading or table moved")
  return out


def count_lines(wid: str, c: dict[str, int]) -> list[str]:
  return {"WP-C-03": [f"{c['HE']} hazardous events → {c['SG']} safety goals"],
          "WP-C-04": [f"{c['FSR']} functional safety requirements"],
          "WP-C-05": [f"{c['SH']} SOTIF hazards"],
          "WP-C-06": [f"{c['FI']} insufficiencies · {c['TC']} triggering conditions"],
          "WP-C-07": [f"{c['FM']} functional modifications"],
          "WP-C-09": [f"{c['TS']} threat scenarios"],
          "WP-C-10": [f"{c['CSG']} cybersecurity goals"],
          "WP-C-11": [f"{c['AIR']} AI safety requirements"]}.get(wid, [])


def activities() -> dict[str, dict]:
  """{produced WP: activity} for the CON activities of concept.yaml."""
  out = {}
  for a in yaml.safe_load((MODEL / "concept.yaml").read_text(encoding="utf-8")):
    if a.get("id", "").startswith("CON-"):
      for p in a.get("produces", []):
        out[p] = a
  return out


def interfaces() -> list[dict]:
  ix = yaml.safe_load((MODEL / "interfaces.yaml").read_text(encoding="utf-8"))
  return [i for i in ix if i.get("kind") == "interface" and i.get("phase") == "G1"]


def register() -> tuple[dict[str, dict], dict[str, str], list]:
  regs, reg = folder_index.register_rows()
  return {it["id"]: it for _t, items in regs.values() for it in items}, dict(reg.statuses), reg


def flow_problems(acts: dict, ixs: list[dict]) -> list[str]:
  """The drawn order must follow concept.yaml: every box's activity exists, an arrow a → b means b needs a, each lane
  starts from the work products above the lanes, and each lane feeds the hazard log (CON-13)."""
  out = []
  drawn = [w for row in TOP for w in row] + [w for *_x, wps in LANES for w in wps]
  if sorted(drawn) != sorted(DOC):
    out.append(f"the figure draws {sorted(drawn)}, the concept folder has {sorted(DOC)}")
  for w in drawn:
    if w not in acts:
      out.append(f"{w}: no CON activity of concept.yaml produces it")
  if out:
    return out
  arrows = [("WP-C-01", "WP-C-12"), ("WP-C-01", "WP-C-02"), ("WP-C-02", "WP-C-08")]
  arrows += [(a, b) for *_x, wps in LANES for a, b in zip(wps, wps[1:])]
  for a, b in arrows:
    if a not in acts[b]["inputs"]:
      out.append(f"arrow {a} → {b}: {acts[b]['id']} does not take {a} as input")
  top = {w for row in TOP for w in row}
  for _k, name, _s, wps in LANES:
    if not top & set(acts[wps[0]]["inputs"]):
      out.append(f"lane {name}: {wps[0]} needs none of the work products above the lanes")
  end = next((a for a in acts.values() if a["id"] == END_ACTIVITY), None)
  if end is None:
    out.append(f"{END_ACTIVITY} not in concept.yaml")
  else:
    for _k, name, _s, wps in LANES:
      if not set(wps) & set(end["inputs"]):
        out.append(f"lane {name}: {END_ACTIVITY} takes none of {wps} as input")
  ids = [i["id"] for i in ixs]
  if sorted(ids) != sorted(IX_LABEL):
    out.append(f"G1 interfaces of interfaces.yaml {ids} differ from the labelled ones {sorted(IX_LABEL)}")
  for i in ixs:
    for w in i["between"]:
      if w not in drawn:
        out.append(f"{i['id']}: {w} is not drawn")
  return out


def cross_inputs(w: str, acts: dict) -> list[str]:
  """Inputs of w from other lanes (drawn as an 'after:' line)."""
  lane = next((wps for *_x, wps in LANES if w in wps), [])
  top = {x for row in TOP for x in row}
  return [i for i in acts[w]["inputs"] if i in DOC and i not in lane and i not in top]


# ---------------------------------------------------------------- Figure C-0-1

def box(x, y, w, wid, reg, names, extra, cls_l="") -> tuple[list[str], float, float]:
  """One work-product box; returns (svg, height, y of the box top)."""
  inner = w - 22 if cls_l else w - 20
  tx = x + (14 if cls_l else 10)
  title = wrap(TITLE[wid], inner, "tb")
  lines = [(ln, "tb") for ln in title]
  body: list[str] = []
  h = 10 + 18 * len(title) + 16 + sum(16 for _ in extra) + 8
  body.append(R(x, y, w, h, "box", rx=7))
  if cls_l:
    body.append(el("rect", None, x=float(x), y=float(y), width=4.0, height=float(h), rx=2, class_=cls_l))
  yy = y + 24
  for ln, cls in lines:
    body.append(T(tx, yy, ln, cls))
    yy += 18
  yy -= 1
  body.append(T(tx, yy, wid, "t3"))
  c, _ = chip(tx + text_w(wid, 12) + 16, yy, reg[wid]["status"], names)
  body += c
  for ln, cls in extra:
    yy += 16
    body.append(T(tx, yy, ln, cls))
  return body, h, y


def arrow(x1, y1, x2, y2) -> str:
  return el("path", None, d=f"M{fmt(x1)},{fmt(y1)} L{fmt(x2)},{fmt(y2)}", class_="arr", marker_end="url(#a)")


def flow_figure(c: dict, acts: dict, ixs: list[dict], reg: dict, names: dict, gates: list) -> str:
  b = [T(X0, 32, "The concept phase on one page", "h"),
       *(T(X0, 54 + 17 * i, ln, "t2") for i, ln in enumerate(wrap(
         "One box per work product, in the order of the concept activities; the number in a box is the count of "
         "its document's table rows.", W - 2 * X0, "t2")))]
  y = 54 + 17 * 2 + 14
  pos: dict[str, tuple[float, float]] = {}      # wid -> (top y, height) for the interface connectors
  # row 1: the item, with its models beside it
  w1 = (CW - 14) * 0.52
  w2 = CW - 14 - w1
  s1, h1, _ = box(X0, y, w1, "WP-C-01", reg, names, [])
  s2, h2, _ = box(X0 + w1 + 14, y, w2, "WP-C-12", reg, names, [])
  hh = max(h1, h2)
  b += s1 + s2 + [arrow(X0 + w1 + 1, y + 22, X0 + w1 + 13, y + 22)]
  pos["WP-C-01"], pos["WP-C-12"] = (y, h1), (y, h2)
  y += hh
  for wid in ("WP-C-02", "WP-C-08"):
    b.append(arrow(X0 + w1 / 2, y + 1, X0 + w1 / 2, y + 21))
    y += 22
    s, h, _ = box(X0, y, CW, wid, reg, names, [])
    b += s
    pos[wid] = (y, h)
    y += h
  # fan out into the four lanes
  y += 30
  cwid = (CW - 3 * 8) / 4
  for i, (k, name, _s, _w) in enumerate(LANES):
    cx = X0 + i * (cwid + 8)
    b.append(arrow(X0 + CW / 2 + (i - 1.5) * 24, y - 29, cx + cwid / 2, y - 1))
    b.append(R(cx, y, cwid, 26, f"{k}-band", rx=13))
    b.append(T(cx + cwid / 2, y + 17.5, CHIP[k], f"{k}-t", "middle"))
  b.append(T(X0 + CW / 2, y + 44, "the four lanes, worked in parallel", "ti", "middle"))
  y += 26 + 30
  # the lanes
  for k, name, std, wps in LANES:
    y0 = y
    lane: list[str] = [T(X0 + 10, y + 20, f"{name}", f"{k}-t"), T(XR - 10, y + 20, std, "t3", "end")]
    y += 30
    for j, wid in enumerate(wps):
      extra = [(ln, "tb") for ln in count_lines(wid, c)]
      after = cross_inputs(wid, acts)
      if after:
        extra.append(("after: " + ", ".join(SHORT[a] for a in after), "ti"))
      s, h, _ = box(X0 + 10, y, CW - 20, wid, reg, names, extra, cls_l=k)
      lane += s
      pos[wid] = (y, h)
      y += h
      if j < len(wps) - 1:
        lane.append(arrow(X0 + 40, y + 1, X0 + 40, y + 17))
        y += 18
    y += 10
    b += [R(X0, y0, CW, y - y0, f"{k}-band", rx=10)] + lane
    y += 12
  # fan in to the hazard log
  end = next(a for a in acts.values() if a["id"] == END_ACTIVITY)
  b.append(T(X0, y + 10, "Each lane feeds the hazard log:", "ti"))
  y += 18
  for i, (k, name, _s, wps) in enumerate(LANES):
    cx = X0 + i * (cwid + 8)
    feeds = ", ".join(SHORT[w] for w in wps if w in end["inputs"])
    ln = wrap(feeds, cwid - 10, "t3")
    hc = 10 + 15 * len(ln)
    b.append(R(cx, y, cwid, hc, f"{k}-band", rx=8))
    for j, s in enumerate(ln):
      b.append(T(cx + cwid / 2, y + 16 + 15 * j, s, "t3", "middle"))
    b.append(arrow(cx + cwid / 2, y + hc + 1, X0 + CW / 2 + (i - 1.5) * 30, y + 48))
  y += 50
  hb = 70
  b.append(R(X0, y, CW, hb, "card", rx=7))
  b.append(T(X0 + 10, y + 24, "Hazard log and argument structure", "tb"))
  xx = X0 + 10
  for wid in end["produces"]:
    b.append(T(xx, y + 44, wid, "t3"))
    cc, cwd = chip(xx + text_w(wid, 12) + 16, y + 44, reg[wid]["status"], names)
    b += cc
    xx += text_w(wid, 12) + 16 + cwd + 14
  b.append(T(X0 + 10, y + 61, "One log for the HARA, SOTIF, TARA and AI hazards", "t3"))
  y += hb
  # gate G1, then system design
  g1 = [it for it in reg.values() if it["href"].startswith(f"../{FOLDER}/") and 1 in it["gates"]]
  st = {}
  for it in g1:
    st[names[it["status"]].lower()] = st.get(names[it["status"]].lower(), 0) + 1
  b.append(arrow(X0 + CW / 2, y + 1, X0 + CW / 2, y + 21))
  y += 22
  b.append(R(X0, y, CW, 50, "gate", rx=25))
  b.append(T(X0 + CW / 2, y + 21, f"Gate G1 · {gates[1][1]}", "gt", "middle"))
  b.append(el("text", f"needs these {len(g1)} work products; now " + ", ".join(f"{n} {s}" for s, n in st.items()),
              x=fmt(X0 + CW / 2), y=fmt(y + 39), class_="t3", text_anchor="middle", style="fill:var(--bg)"))
  y += 50
  b.append(arrow(X0 + CW / 2, y + 1, X0 + CW / 2, y + 21))
  y += 22
  b.append(R(X0, y, CW, 46, "box", rx=7))
  b.append(T(X0 + 10, y + 21, f"System design (G2) · 03-system", "tb"))
  b.append(T(X0 + 10, y + 38, "technical safety concept, system requirements, architecture", "t3"))
  y += 46 + 18
  # the interface connectors in the gutter
  ends: dict[str, list[tuple[str, str]]] = {}
  for n, i in enumerate(ixs):
    a, z = i["between"]
    ends.setdefault(a, []).append((i["id"], z))
    ends.setdefault(z, []).append((i["id"], a))
  ystub: dict[tuple[str, str], float] = {}
  for wid, lst in ends.items():
    top, h = pos[wid]
    lst.sort(key=lambda e: pos[e[1]][0])
    for k, (iid, _o) in enumerate(lst):
      ystub[(iid, wid)] = top + h * (k + 1) / (len(lst) + 1)
  spans = []
  for n, i in enumerate(ixs):
    a, z = i["between"]
    ya, yz = ystub[(i["id"], a)], ystub[(i["id"], z)]
    spans.append((abs(yz - ya), n, min(ya, yz), max(ya, yz), ya, yz))
  track: dict[int, int] = {}
  used: dict[int, list[tuple[float, float]]] = {}
  for _len, n, lo, hi, _a, _z in sorted(spans):
    k = 0
    while any(not (hi + 6 < l2 or lo - 6 > h2) for l2, h2 in used.get(k, [])):
      k += 1
    track[n] = k
    used.setdefault(k, []).append((lo, hi))
  if max(track.values()) > 7:
    raise OverviewError("more than eight interface tracks needed; widen the gutter")
  for _len, n, lo, hi, ya, yz in spans:
    tx = TRACK0 + TRACK_STEP * track[n]
    b.append(el("path", None, d=f"M{fmt(XR)},{fmt(ya)} H{fmt(tx)} V{fmt(yz)} H{fmt(XR)}", class_="ix"))
  for _len, n, lo, hi, ya, yz in spans:
    for yy in (ya, yz):
      b.append(el("circle", None, cx=float(XR + 10), cy=float(yy), r=7.0, class_="badge"))
      b.append(T(XR + 10, yy + 3.7, str(n + 1), "nb", "middle"))
  # legend of the connectors
  b.append(el("line", None, x1=float(X0), y1=float(y - 8), x2=float(W - X0), y2=float(y - 8), class_="hair"))
  b.append(T(X0, y + 10, "Dashed: where one lane's analysis depends on another's", "tb"))
  b.append(T(X0, y + 27, "(the G1 interfaces of the process model)", "t3"))
  y += 44
  for n, i in enumerate(ixs):
    a, z = i["between"]
    b.append(el("circle", None, cx=float(X0 + 8), cy=float(y - 4), r=7.0, class_="badge"))
    b.append(T(X0 + 8, y - 0.3, str(n + 1), "nb", "middle"))
    for ln in wrap(f"{SHORT[a]} ↔ {SHORT[z]}: {IX_LABEL[i['id']]}", W - 2 * X0 - 22, "t2"):
      b.append(T(X0 + 22, y, ln, "t2"))
      y += 17
    y += 3
  y += 6
  extra, y = footer(b, y, "fig_c00_overview.py")
  b += extra
  desc = ("The concept phase, top to bottom: " + "; ".join(
    f"{w} {TITLE[w]}" + (f" ({', '.join(count_lines(w, c))})" if count_lines(w, c) else "")
    for row in TOP for w in row) + ". Four lanes in parallel: " + "; ".join(
    f"{name}: " + ", then ".join(f"{w} {TITLE[w]}" + (f" ({', '.join(count_lines(w, c))})" if count_lines(w, c) else "")
                                 for w in wps) for _k, name, _s, wps in LANES) +
    ". All lanes feed the hazard log and argument structure (" + ", ".join(end["produces"]) + "), then gate G1, then "
    "system design (G2). Every work product is draft. Dashed connectors: " + "; ".join(
      f"{SHORT[i['between'][0]]} and {SHORT[i['between'][1]]}: {IX_LABEL[i['id']]}" for i in ixs) + ".")
  if any(it["status"] != "D" for it in reg.values() if it["id"] in DOC):
    desc = desc.replace(" Every work product is draft.", "")
  return svg_doc(y, "Figure C-0-1. The concept phase on one page", desc, b)


# ---------------------------------------------------------------- Figure C-0-2: the thread

def expand(cell: str) -> set[str]:
  """IDs of a cell such as 'HE-01.1–01.6, HE-02.3' or 'FSR-01.01–01.04'."""
  out = set()
  for m in re.finditer(r"(HE|FSR)-(\d\d)\.(\d+)(?:–(\d\d)\.(\d+))?", cell):
    p, a, i, b2, j = m.groups()
    if b2 is None:
      out.add(f"{p}-{a}.{i}")
    else:
      width = len(i)
      for n in range(int(i), int(j) + 1):
        out.add(f"{p}-{a}.{n:0{width}d}")
  return out


def chain() -> dict:
  """Every value of the thread, read from WP-C-01 to WP-C-04 and the dashboards README."""
  c01, c02, c03, c04, c08 = doc("WP-C-01"), doc("WP-C-02"), doc("WP-C-03"), doc("WP-C-04"), doc("WP-C-08")
  head, rws = table(section(c01, "### 3.4 Interfaces"), "ID")
  if01 = next((r for r in rws if r[0] == "IF-01"), None)
  m = re.search(r"`0x2E4` STEERING_LKA \(([^)]*)\)", if01[col(head, "Content (examples)")] if if01 else "")
  if not if01 or not m:
    raise OverviewError("WP-C-01 §3.4: IF-01 no longer carries 0x2E4 STEERING_LKA")
  speed = re.search(r"^\| Speed \| Ego speed \| ([^|]+?) \|", c02, re.M)
  if not speed:
    raise OverviewError("WP-C-02 §3.1: the speed row is gone")
  sup = "on the basis of a supervising driver"
  if sup not in c08:
    raise OverviewError(f"WP-C-08: {sup!r} is gone")
  he_row = next((r for r in re.findall(r"^\| (HE-\d\d\.\d+) \| (.*)$", section(c03, "## 5. "), re.M)
                 if r[0] == CHAIN_HE), None)
  if not he_row:
    raise OverviewError(f"WP-C-03 §5: {CHAIN_HE} not found")
  cells = [x.strip() for x in he_row[1].rstrip("|").split("|")]
  situation, effect, s, e, c, asil, why = cells[:7]
  hz = re.findall(r"^### 5\.\d+ (H-\d\d) (.+)$", c03[:c03.find(f"| {CHAIN_HE} |")], re.M)[-1]
  fallback = next((r for r in re.findall(r"^\| (HE-\d\d\.\d+) \| [^|]+ \| (\w) \| (\w) \|", section(c03, "### 5.12"), re.M)
                   if r[0] == CHAIN_HE), None)
  if f"governing event of {CHAIN_SG}" not in why:
    raise OverviewError(f"{CHAIN_HE} is no longer stated to be the governing event of {CHAIN_SG}")
  sg_head, sg_rows = table(section(c03, "## 6. Safety goals"), "ID")
  sg = next((r for r in sg_rows if plain(r[0]) == CHAIN_SG), None)
  if not sg:
    raise OverviewError(f"WP-C-03 §6: {CHAIN_SG} not found")
  if CHAIN_HE not in expand(sg[col(sg_head, "Source HEs")]):
    raise OverviewError(f"{CHAIN_HE} is not a source HE of {CHAIN_SG}; follow the documents and redraw the chain")
  sg_asil = plain(sg[col(sg_head, "ASIL")])
  ftti = re.match(r"\**(≤ [\d.]+ s)", sg[col(sg_head, "Preliminary FTTI")])
  fh, frows = table(section(c04, "### 5.1 SG-01"), "ID")
  trh, trrows = table(section(c04, "## 9. FSR → SG trace"), "FSR")
  served = set()
  for r in trrows:
    if r[col(trh, CHAIN_SG)] == "●":
      served |= expand(r[0])
  eh, erows = table(section(c04, "## 2. Architectural elements"), "Element")
  elements = {r[0]: r[1] for r in erows}
  fsrs = []
  for fid, label, words in CHAIN_FSR:
    r = next((r for r in frows if r[0] == fid), None)
    if not r:
      raise OverviewError(f"WP-C-04 §5.1: {fid} not found")
    if words not in r[col(fh, "Requirement")]:
      raise OverviewError(f"{fid} no longer says {words!r}; redraw its label {label!r}")
    if fid not in served:
      raise OverviewError(f"WP-C-04 §9: {fid} no longer serves {CHAIN_SG}")
    alloc = r[col(fh, "Alloc")]
    impl = re.split(r"[:(;]", plain(r[col(fh, "Impl / GAP")]))[0].strip()
    fsrs.append({"id": fid, "label": label, "asil": r[col(fh, "ASIL")], "alloc": alloc, "impl": impl})
  for f in fsrs:
    if f["alloc"] not in elements:
      raise OverviewError(f"{f['id']}: allocation {f['alloc']} is not an element of WP-C-04 §2")
  dash = (DASH / "README.md").read_text(encoding="utf-8")
  row = re.search(rf"^\| \[{SCENE}\]\({SCENE}\.jpg\) \| {re.escape(CHAIN_HE)} \(ASIL (\w)\) \|.*\| ([^|]+) \|$", dash, re.M)
  if not row:
    raise OverviewError(f"sim/blender/dashboards/README.md: no {SCENE} row for {CHAIN_HE}")
  files = [DASH / f"{SCENE}.jpg", DASH / "clips" / f"{SCENE}.mp4", DASH / "clips" / "previews" / f"{SCENE}.webp"]
  for p in files:
    if not p.exists():
      raise OverviewError(f"{p.relative_to(ASSURANCE)} does not exist")
  return {"lka": m.group(1), "if01": if01[1], "speed": speed.group(1).strip(), "situation": situation,
          "effect": effect, "s": s, "e": e, "c": c, "asil": plain(asil), "hazard": hz,
          "fallback": fallback[2] if fallback else "", "sg_text": sg[col(sg_head, "Safety goal")],
          "sg_asil": sg_asil, "safe_state": sg[col(sg_head, "Safe state")], "ftti": ftti.group(1) if ftti else "",
          "fsrs": fsrs, "elements": {f["alloc"]: elements[f["alloc"]] for f in fsrs},
          "scene_asil": row.group(1), "outcome": plain(row.group(2)),
          "files": [p.relative_to(ASSURANCE).as_posix() for p in files]}


def thumb_uri() -> str:
  return "data:image/jpeg;base64," + base64.b64encode(THUMB.read_bytes()).decode()


def build_thumb() -> bool:
  try:
    from PIL import Image
  except ImportError:
    return False
  with Image.open(DASH / f"{SCENE}.jpg") as im:
    im.convert("RGB").crop(THUMB_CROP).resize(THUMB_SIZE, Image.LANCZOS).save(
      THUMB, "JPEG", quality=72, optimize=True, progressive=True)
  return True


def jpeg_size(path: Path) -> tuple[int, int] | None:
  data = path.read_bytes()
  i = 2
  while i < len(data) - 9:
    if data[i] != 0xFF:
      return None
    marker, seg = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
    if marker in (0xC0, 0xC1, 0xC2):
      h, w = struct.unpack(">HH", data[i + 5:i + 9])
      return w, h
    i += 2 + seg
  return None


def hazard_figure(d: dict) -> str:
  b = [T(X0, 32, "Follow one hazard", "h"),
       *(T(X0, 54 + 17 * i, ln, "t2") for i, ln in enumerate(wrap(
         f"One thread through the documents: from the steering command on the CAN bus to the requirements that "
         f"limit it, and the scene that shows {CHAIN_HE}.", W - 2 * X0, "t2")))]
  y = 54 + 17 * 2 + 16
  RAIL, CX, CWD = X0 + 13, X0 + 34, W - X0 - (X0 + 34)
  inner = CWD - 22
  hz_id, hz_name = d["hazard"]
  fsr_lines = []
  for f in d["fsrs"]:
    fsr_lines.append((f"{f['id']} · ASIL {f['asil']} · {f['alloc']}", "tb"))
    fsr_lines += [(ln, "t2") for ln in wrap(f"{f['label']}; now: {f['impl'].lower()}", inner, "t2")]
  for e, desc in d["elements"].items():
    fsr_lines += [(ln, "t3") for ln in wrap(f"{e}: {desc}", inner, "t3")]
  steps = [
    ("", "The item element", "WP-C-01 §3.4",
     [("EPS torque command over CAN", "tb")] +
     [(ln, "t2") for ln in wrap(f"0x2E4 STEERING_LKA ({d['lka']}), sent on IF-01, {d['if01']}", inner, "t2")]),
    ("", "The operating situation", "WP-C-02 §3.1 · WP-C-03 §3 · WP-C-08 §1",
     [("Highway at up to 110 km/h, supervising driver", "tb")] +
     [(ln, "t2") for ln in wrap(f"{d['situation']}. ODD speed: {d['speed']}. Controllability C2 rests on a "
                                "supervising driver.", inner, "t2")]),
    ("fs", "The hazardous event", "WP-C-03 §5.1, §5.12",
     [(f"{CHAIN_HE}: steering hard-over into the adjacent lane", "tb")] +
     [(ln, "t2") for ln in wrap(f"{d['effect']} ({hz_id} {hz_name.lower()})", inner, "t2")] +
     [(f"{d['s']}  ·  {d['e']}  ·  {d['c']}  →  ASIL {d['asil']}", "tb")] +
     ([(f"ASIL {d['fallback']} if AOU-01/02 are not verified", "t3")] if d["fallback"] else [])),
    ("fs", "The safety goal", "WP-C-03 §6",
     [(f"{CHAIN_SG} · ASIL {d['sg_asil']}", "tb")] +
     [(ln, "t2") for ln in wrap(d["sg_text"], inner, "t2")] +
     [(ln, "t3") for ln in wrap(f"Safe state: {d['safe_state']}. FTTI {d['ftti']} (preliminary). "
                                f"{CHAIN_HE} is its governing event.", inner, "t3")]),
    ("fs", "The requirements that implement it", "WP-C-04 §2, §5.1, §9", fsr_lines),
    ("", "Where it is shown", "sim/blender/dashboards",
     [(f"3D scene {SCENE}", "tb")] +
     [(ln, "t2") for ln in wrap(f"Outcome in the scene: {d['outcome']}. Synthetic: a picture, no evidence credit.",
                                inner, "t2")] +
     [(ln, "t3") for p in ("dashboard: " + Path(d["files"][0]).name, "clip: clips/" + Path(d["files"][1]).name,
                           "loop: clips/previews/" + Path(d["files"][2]).name) for ln in wrap(p, inner, "t3")]),
  ]
  tops = []
  for n, (k, kind, src, lines) in enumerate(steps):
    h = 12 + 16 + 4 + (0 if text_w(kind, 13, True) + text_w(src, 12) + 40 < CWD else 16) + sum(18 if cls == "tb" else 16 if cls == "t2" else 15 for _l, cls in lines) + 8
    if n == len(steps) - 1:
      h += THUMB_SIZE[1] * (inner / THUMB_SIZE[0]) + 10
    b.append(R(CX, y, CWD, h, "box", rx=8))
    if k:
      b.append(el("rect", None, x=float(CX), y=float(y), width=4.0, height=float(h), rx=2, class_=k))
    tx = CX + 12
    b.append(T(tx, y + 20, kind, f"{k}-t" if k else "t3"))
    yy = y + 20 + 6
    if text_w(kind, 13, True) + text_w(src, 12) + 40 < CWD:
      b.append(T(CX + CWD - 10, y + 20, src, "t3", "end"))
    else:
      b.append(T(tx, y + 37, src, "t3"))
      yy += 16
    for ln, cls in lines:
      yy += 18 if cls == "tb" else 16 if cls == "t2" else 15
      b.append(T(tx, yy - 4, ln, cls))
    if n == len(steps) - 1:
      th = THUMB_SIZE[1] * (inner / THUMB_SIZE[0])
      b.append(el("image", None, x=float(tx), y=float(yy + 4), width=float(inner), height=float(th),
                  href=thumb_uri()))
      b.append(el("rect", None, x=float(tx), y=float(yy + 4), width=float(inner), height=float(th), class_="box",
                  style="fill:none"))
    tops.append((y, h))
    y += h + 18
  b.insert(4, el("line", None, x1=float(RAIL), y1=float(tops[0][0] + 20), x2=float(RAIL), y2=float(tops[-1][0] + 20),
                 class_="arr"))
  for n, (top, h) in enumerate(tops):
    b.append(el("circle", None, cx=float(RAIL), cy=float(top + 16), r=10.0, class_="badge"))
    b.append(T(RAIL, top + 20, str(n + 1), "nb", "middle"))
  extra, y = footer(b, y, "fig_c00_overview.py")
  b += extra
  desc = (f"A vertical chain of six steps. 1, the item element (WP-C-01): the EPS torque command over CAN, 0x2E4 "
          f"STEERING_LKA ({d['lka']}). 2, the operating situation (WP-C-02, WP-C-08): {d['situation']}, ODD speed "
          f"{d['speed']}, a supervising driver. 3, the hazardous event {CHAIN_HE} (WP-C-03): {d['effect']}; "
          f"{d['s']}, {d['e']}, {d['c']}, ASIL {d['asil']}" + (f", ASIL {d['fallback']} if AOU-01/02 are not verified"
                                                               if d["fallback"] else "") +
          f". 4, the safety goal {CHAIN_SG}, ASIL {d['sg_asil']}: {d['sg_text']} 5, the requirements (WP-C-04): " +
          "; ".join(f"{f['id']} {f['label']}, ASIL {f['asil']}, allocated to {f['alloc']}, now {f['impl'].lower()}"
                    for f in d["fsrs"]) +
          f". 6, where it is shown: the 3D scene {SCENE} of the gallery, {d['outcome']}, with a still of its 3D view.")
  return svg_doc(y, f"Figure C-0-2. Follow one hazard: {CHAIN_HE} to {CHAIN_SG} and its requirements", desc, b)


# ---------------------------------------------------------------- the page section

def wp_link(wid: str, reg: dict) -> str:
  href = reg[wid]["href"]
  return f"[{wid}]({folder_index.href_in_folder(href, FOLDER)})" if href else wid


def section_md(c: dict, ixs: list[dict], d: dict, reg: dict, acts: dict) -> str:
  end = next(a for a in acts.values() if a["id"] == END_ACTIVITY)
  out = ["## The concept phase at a glance", "",
         f"![The concept phase, top to bottom: the item and its boundary with its models, the ODD, the driver and "
         f"misuse analysis, then four lanes in parallel: functional safety (HARA with {c['HE']} hazardous events and "
         f"{c['SG']} safety goals, then the FSC with {c['FSR']} requirements), SOTIF ({c['SH']} hazards, "
         f"{c['FI']} insufficiencies and {c['TC']} triggering conditions, {c['FM']} functional modifications), "
         f"cybersecurity ({c['TS']} threat scenarios, {c['CSG']} cybersecurity goals) and AI ({c['AIR']} AI safety "
         f"requirements). All four feed the hazard log and argument structure, then gate G1, then system design. "
         f"Dashed lines join the {len(ixs)} places where one lane depends on another](figures/{OUT_A})", "",
         f"*Figure C-0-1. One box per work product, in the order of the activities CON-01 to CON-15 of "
         f"[`concept.yaml`](../process/model/concept.yaml); the dashed links are its G1 rows of "
         f"[`interfaces.yaml`](../process/model/interfaces.yaml). Counts are the defined rows of each document's "
         f"table and the chips the WP-M-00 §3 status, both read at build time by "
         f"[`fig_c00_overview.py`](figures/fig_c00_overview.py) (CI fails if stale).*", "",
         "Each box, and where it is:", ""]
  for row in TOP:
    out.append("- " + " · ".join(f"{TITLE[w]}: {wp_link(w, reg)}" for w in row))
  for _k, name, _s, wps in LANES:
    out.append(f"- {name}: " + " → ".join(
      f"{TITLE[w]} ({', '.join(count_lines(w, c)) + ', ' if count_lines(w, c) else ''}{wp_link(w, reg)})" for w in wps))
  out.append("- Hazard log and argument structure: " + ", ".join(wp_link(w, reg) for w in end["produces"]) +
             "; then gate G1 ([WP-M-00 §2](../01-management/WP-M-00-work-product-register.md)) and "
             "[system design](../03-system/README.md) (G2)")
  out += ["", "The dashed links:", ""]
  for n, i in enumerate(ixs):
    a, z = i["between"]
    out.append(f"{n + 1}. {TITLE[a]} ↔ {TITLE[z]}: {IX_LABEL[i['id']]} ({i['id']}, {wp_link(a, reg)} ↔ {wp_link(z, reg)})")
  f = d["files"]
  out += ["", "## Follow one hazard", "",
          f"![A chain of six steps: the EPS torque command 0x2E4 on the vehicle CAN; a highway at up to 110 km/h with a "
          f"supervising driver; the hazardous event {CHAIN_HE}, {d['effect'].lower()}, {d['s']} {d['e']} {d['c']}, "
          f"ASIL {d['asil']}; the safety goal {CHAIN_SG}, ASIL {d['sg_asil']}; the requirements "
          f"{', '.join(x['id'] for x in d['fsrs'])} that limit the torque on {', '.join(d['elements'])}; and the 3D "
          f"scene that shows it, with a still of its 3D view](figures/{OUT_D})", "",
          f"*Figure C-0-2. Every value is read from the documents at build time by "
          f"[`fig_c00_overview.py`](figures/fig_c00_overview.py): the build fails if {CHAIN_HE} no longer rolls up to "
          f"{CHAIN_SG}, or if a drawn requirement no longer serves it.*", "",
          f"The steps: [IF-01 in WP-C-01 §3.4]({DOC['WP-C-01']}) · [the ODD in WP-C-02 §3.1]({DOC['WP-C-02']}) · "
          f"[{CHAIN_HE} in WP-C-03 §5.1]({DOC['WP-C-03']}) · [{CHAIN_SG} in WP-C-03 §6]({DOC['WP-C-03']}) · "
          f"[the FSRs in WP-C-04 §5.1]({DOC['WP-C-04']}) · the scene: "
          f"[dashboard](../{f[0]}), [clip](../{f[1]}), [3 s loop](../{f[2]}) "
          f"([all scenes](../sim/blender/dashboards/README.md))."]
  return "\n".join(out) + "\n"


# ---------------------------------------------------------------- build

def problems() -> list[str]:
  out = []
  if not THUMB.exists():
    out.append(f"{THUMB.name} missing; run fig_c00_overview.py with Pillow installed")
  else:
    if THUMB.stat().st_size > THUMB_MAX_BYTES:
      out.append(f"{THUMB.name} is {THUMB.stat().st_size} bytes, over {THUMB_MAX_BYTES}")
    if jpeg_size(THUMB) != THUMB_SIZE:
      out.append(f"{THUMB.name} is {jpeg_size(THUMB)}, expected {THUMB_SIZE}")
  return out


def build() -> dict[Path, str]:
  acts, ixs = activities(), interfaces()
  errs = flow_problems(acts, ixs) + problems()
  if errs:
    raise OverviewError("; ".join(errs))
  reg, names, regobj = register()
  c, d = counts(), chain()
  text = folder_index.rebase_from(section_md(c, ixs, d, reg, acts), HERE.parent, HERE)
  return {HERE / OUT_A: flow_figure(c, acts, ixs, reg, names, regobj.gates), HERE / OUT_D: hazard_figure(d),
          HERE / SECTION: text}


def main(argv: list[str]) -> int:
  if "--check" not in argv and not THUMB.exists() or "--thumb" in argv:
    build_thumb()
  try:
    outputs = build()
  except FigureError as e:
    print(f"fig_c00_overview: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [p for p, c in outputs.items() if not p.exists() or p.read_text(encoding="utf-8") != c]
    for p in stale:
      print(f"stale: {p.relative_to(ASSURANCE).as_posix()}; run: python3 assurance/02-concept/figures/fig_c00_overview.py",
            file=sys.stderr)
    if not stale:
      print(f"fig_c00_overview: {len(outputs)} outputs current")
    return 1 if stale else 0
  for p, c in outputs.items():
    p.write_text(c, encoding="utf-8")
  print(f"fig_c00_overview: wrote {OUT_A}, {OUT_D} and {SECTION}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
