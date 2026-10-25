#!/usr/bin/env python3
"""Draw WP-C-04 Figure 10-1, the item boundary in the safety view (`figures/fig-c04-10-1-safety-view.svg`).

The layout follows WP-C-01 Figure 3-2 (the item boundary): driver on the left, the comma device E-04 with the SoC
software E-01 and the panda safety MCU E-03 inside the boundary, the harness E-05 below, the vehicle ECUs on the
vehicle CAN. Each element carries what the functional safety concept puts on it:

  - the FSRs of §5 whose Alloc column names it, how many, and the highest ASIL among them;
  - the safety goals those FSRs serve (the §9 trace);
  - the integrity the element itself can carry today (§2), and a red outline where a QM element carries ASIL FSRs;
  - for the driver, the assumptions of use of the §10 Driver row.

WP-C-04 is the source of record. Run through `fsc_figures.py`, which writes and checks every fig-c04-<n> figure.
It fails if §5 allocates to an element that has no box here or §2 has no row for a drawn element.

Standard library only. Drawing helpers and palette are shared with ../hara/hara_figures.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "hara"))
import hara_figures as hf  # noqa: E402
from hara_figures import INK, MUTED, HAIR, ASIL_FILL, ASIL_TEXT, ASIL_STROKE, t, wrap, svg_doc, header  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)

NAME = "fig-c04-10-1-safety-view.svg"
# §5 allocates HMI functions to E-01/HMI; §2 describes the HMI hardware and software as E-04/HMI.
INTEGRITY_ROW = {"E-01/HMI": "E-04/HMI"}
RANK = {"QM": 0, "A": 1, "B": 2, "C": 3, "D": 4}
RED = "#D2553F"
# Element boxes: id -> (x, y, w, h, title). Positions follow WP-C-01 Figure 3-2.
BOXES = {
  "E-01": (282, 262, 446, 92, "SoC software · openpilot"),
  "E-01/DM": (282, 364, 142, 140, "Driver monitoring chain"),
  "E-01/HMI": (434, 364, 142, 140, "HMI · display, sound"),
  "E-02": (586, 364, 142, 140, "ML models"),
  "E-03": (752, 262, 226, 242, "Panda safety MCU · envelope"),
  "E-05": (560, 540, 418, 96, "Harness with intercept relay"),
  "EXT-EPS": (240, 752, 190, 126, "Toyota EPS"),
  "EXT-PCM": (446, 752, 190, 126, "ECM / PCM and brake"),
  "EXT-CLU": (652, 752, 190, 126, "Instrument cluster"),
}


class SafetyViewError(ValueError):
  pass


def _cells(line: str) -> list[str]:
  return [c.strip() for c in line.strip()[1:-1].split("|")]


def element_integrity(md: str) -> dict[str, str]:
  m = re.search(r"^## 2\. .*?$(.*?)(?=^## \d+\. )", md, re.M | re.S)
  out = {}
  for ln in (m.group(1) if m else "").splitlines():
    if re.match(r"^\| (E-0|EXT-)", ln):
      c = _cells(ln)
      out[c[0]] = c[2]
  return out


def driver_aous(md: str) -> list[str]:
  m = re.search(r"^## 10\. .*?$(.*?)(?=^## \d+\. )", md, re.M | re.S)
  for ln in (m.group(1) if m else "").splitlines():
    if ln.startswith("| Driver |"):
      return re.findall(r"AOU-\d\dR?", ln)
  raise SafetyViewError("§10 has no Driver row")


def model(goals, md: str) -> dict[str, dict]:
  integ = element_integrity(md)
  view: dict[str, dict] = {e: {"fsrs": [], "goals": set()} for e in BOXES}
  for g in goals:
    for f in g.fsrs:
      for e in f.elements:
        if e not in view:
          raise SafetyViewError(f"{f.ident}: element {e} has no box in the safety view")
        view[e]["fsrs"].append(f)
        view[e]["goals"].update(f.serves)
  for e, v in view.items():
    row = INTEGRITY_ROW.get(e, e)
    if row not in integ:
      raise SafetyViewError(f"§2 has no row for {row}")
    asils = [f.asil for f in v["fsrs"] if f.asil in RANK]
    v["top"] = max(asils, key=RANK.get) if asils else ("ext" if v["fsrs"] else None)
    v["integrity"] = integ[row]
    v["qm_carries"] = integ[row].startswith("QM") and v["top"] in ("A", "B", "C", "D")
  return view


def _style(e: str, v: dict) -> tuple[str, str, float, str]:
  """fill, stroke, stroke width, dash."""
  if e.startswith("EXT"):
    return "url(#sv-hatch)", "#64748B", 1.3, "5 4"
  top = v["top"]
  fill = {"C": "#FFF7ED", "B": "#FFF7ED", "A": "#FFFBEB"}.get(top, "#F8FAFC")
  if v["qm_carries"]:
    return fill, RED, 2.4, ""
  return fill, ASIL_STROKE.get(top, "#CBD5E1"), 1.8, ""


def _box(e: str, v: dict, body: list[str]) -> None:
  x, y, w, h, title = BOXES[e]
  fill, stroke, sw, dash = _style(e, v)
  d = f' stroke-dasharray="{dash}"' if dash else ""
  body.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')
  body.append(t(x + 10, y + 19, e, 12, INK, 700))
  tw = hf.text_w(e, 12, True)
  wide = w > 300
  if wide:
    body.append(t(x + 18 + tw, y + 19, title, 11, MUTED))
    ty = y + 19
  else:
    ty = y + 19
    for ln in wrap(title, w - 20, 10.5):
      ty += 14
      body.append(t(x + 10, ty, ln, 10.5, MUTED))
  n = len(v["fsrs"])
  ty += 10
  if n:
    top = v["top"]
    label = f"{n} FSR" + ("s" if n > 1 else "")
    body.append(t(x + 10, ty + 13, label, 12, INK, 700))
    px = x + 16 + hf.text_w(label, 12, True)
    if top in ASIL_FILL:
      pl = f"up to ASIL {top}" if top != "QM" else "QM"
      pw = hf.text_w(pl, 10, True) + 14
      body.append(f'<rect x="{px:g}" y="{ty:g}" width="{pw:.1f}" height="17" rx="8.5" fill="{ASIL_FILL[top]}" stroke="{ASIL_STROKE[top]}"/>')
      body.append(t(px + pw / 2, ty + 12.5, pl, 10, ASIL_TEXT[top], 700, "middle"))
    else:
      pl = "AoU"
      pw = hf.text_w(pl, 10, True) + 14
      body.append(f'<rect x="{px:g}" y="{ty:g}" width="{pw:.1f}" height="17" rx="8.5" fill="#FFFFFF" stroke="#64748B"/>')
      body.append(t(px + pw / 2, ty + 12.5, pl, 10, MUTED, 700, "middle"))
    ty += 24
    gx = x + 10
    for sg in sorted(v["goals"]):
      lab = sg
      if gx + 40 > x + w - 6:
        gx = x + 10
        ty += 19
      body.append(f'<rect x="{gx}" y="{ty}" width="38" height="15" rx="4" fill="#FFFFFF" stroke="#CBD5E1"/>')
      body.append(t(gx + 19, ty + 11.5, lab, 9.5, INK, 600, "middle"))
      gx += 41
    ty += 15
  else:
    body.append(t(x + 10, ty + 13, "no FSR", 11, MUTED))
    ty += 18
  integ = re.sub(r"\s*\(.*?\)", "", v["integrity"]).replace("`", "")
  lines = wrap("QM element, carries ASIL FSRs", w - 20, 10, True) if v["qm_carries"] else wrap("Element: " + integ, w - 20, 10)
  col = RED if v["qm_carries"] else MUTED
  for i, ln in enumerate(lines[:3]):
    if ty + 18 + i * 13 < y + h:
      body.append(t(x + 10, ty + 16 + i * 13, ln, 10, col, 700 if v["qm_carries"] else None))


def figure(goals, md: str) -> str:
  view = model(goals, md)
  aous = driver_aous(md)
  w, h = 1280, 0
  body = header(w, "Figure 10-1 · The item boundary in the safety view",
                "WP-C-01 Figure 3-2 with the functional safety concept on it: the FSRs each element carries, their highest "
                "ASIL and the safety goals they serve", "WP-C-04 §2, §5, §9, §10", "layout: WP-C-01 Figure 3-2")
  body.insert(0, '<defs><pattern id="sv-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
              '<rect width="6" height="6" fill="#F8FAFC"/><line x1="0" y1="0" x2="0" y2="6" stroke="#E2E8F0" stroke-width="2"/></pattern>'
              f'<marker id="sv-a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
              f'<path d="M0,0 L10,5 L0,10 z" fill="#C2410C"/></marker>'
              f'<marker id="sv-m" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
              f'<path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/></marker></defs>')
  body.append('<g transform="translate(0,-64)">')
  # item boundary and device
  body.append('<rect x="244" y="190" width="764" height="470" rx="16" fill="#FFFDF7" stroke="#C2410C" stroke-width="1.6" stroke-dasharray="7 5"/>')
  body.append('<rect x="262" y="176" width="190" height="26" rx="13" fill="#C2410C"/>')
  body.append(t(357, 193.5, "ITEM BOUNDARY · LD-SDA", 11, "#FFFFFF", 700, "middle"))
  body.append('<rect x="266" y="216" width="726" height="296" rx="11" fill="#FFFFFF" stroke="#94A3B8" stroke-width="1.2"/>')
  body.append(t(280, 240, "E-04 comma device", 12.5, INK, 700))
  body.append(t(410, 240, "SoC, panda MCU, shared supply and clocks; no FSR of its own (§2: integrity of E-03 depends on it)", 10.5, MUTED))
  # flows under the boxes
  body.append(f'<line x1="728" y1="300" x2="750" y2="300" stroke="#C2410C" stroke-width="2.4" marker-end="url(#sv-a)"/>')
  body.append(t(739, 286, "SPI", 9.5, "#C2410C", 700, "middle"))
  body.append('<line x1="865" y1="504" x2="865" y2="538" stroke="#C2410C" stroke-width="2.4" marker-end="url(#sv-a)"/>')
  body.append('<line x1="700" y1="636" x2="700" y2="712" stroke="#C2410C" stroke-width="2.4" marker-end="url(#sv-a)"/>')
  body.append(t(708, 690, "actuation · IF-01", 10, "#C2410C", 700))
  body.append('<line x1="240" y1="716" x2="1000" y2="716" stroke="#0F172A" stroke-width="4"/>')
  body.append(t(240, 706, "Vehicle CAN · car side", 11.5, INK, 700))
  for e in ("EXT-EPS", "EXT-PCM", "EXT-CLU"):
    x, y, bw, _, _ = BOXES[e]
    body.append(f'<line x1="{x + bw / 2}" y1="716" x2="{x + bw / 2}" y2="{y}" stroke="#0F172A" stroke-width="1.6"/>')
  for e in BOXES:
    _box(e, view[e], body)
  # forward camera: context, no FSR; SG-07 keeps its PCS path
  body.append('<rect x="1046" y="540" width="194" height="96" rx="9" fill="#F8FAFC" stroke="#CBD5E1"/>')
  body.append(t(1058, 560, "Toyota forward camera", 12, INK, 700))
  for i, ln in enumerate(wrap("Outside the item. Its PCS/AEB path is kept by SG-07 (E-03, E-05, PCM)", 172, 10.5)):
    body.append(t(1058, 578 + i * 13.5, ln, 10.5, MUTED))
  body.append('<line x1="978" y1="588" x2="1044" y2="588" stroke="#0F766E" stroke-width="2" marker-end="url(#sv-m)" marker-start="url(#sv-m)"/>')
  # driver
  body.append('<rect x="40" y="262" width="176" height="234" rx="10" fill="url(#sv-hatch)" stroke="#64748B" stroke-width="1.3" stroke-dasharray="5 4"/>')
  body.append(t(52, 282, "DRV · Driver", 12, INK, 700))
  dy = 300
  for ln in wrap("Not an E/E element: no FSR. Credited through assumptions of use only:", 152, 10.5):
    body.append(t(52, dy, ln, 10.5, MUTED))
    dy += 13.5
  dy += 6
  for a in aous:
    pw = hf.text_w(a, 10, True) + 14
    body.append(f'<rect x="52" y="{dy}" width="{pw:.1f}" height="17" rx="8.5" fill="#FFFFFF" stroke="#64748B"/>')
    body.append(t(52 + pw / 2, dy + 12.5, a, 10, MUTED, 700, "middle"))
    dy += 22
  for ln in wrap("Supervises, overrides with brake, cancel and steering, responds to warnings (§11)", 152, 10.5):
    body.append(t(52, dy + 10, ln, 10.5, INK))
    dy += 13.5
  body.append(f'<line x1="216" y1="430" x2="280" y2="430" stroke="{MUTED}" stroke-width="1.6" marker-end="url(#sv-m)" marker-start="url(#sv-m)"/>')
  body.append(f'<path d="M128 496 V 808 H 238" fill="none" stroke="{MUTED}" stroke-width="1.4" stroke-dasharray="4 4" marker-end="url(#sv-m)"/>')
  body.append(t(136, 790, "wheel, pedals, stalk", 10, MUTED))
  # key on the right
  kx, ky = 1046, 262
  body.append(t(kx, ky, "HOW TO READ", 10.5, MUTED, 700, extra=' letter-spacing=".04em"'))
  key = [
    ("Box colour", "the highest ASIL among the FSRs allocated to the element (§5 Alloc)"),
    ("SG chips", "the safety goals the FSRs of that element serve (§9)"),
    ("Red outline", "a QM element (§2) that carries ASIL FSRs; §10 backs them by E-03 or leaves them open (OI-9, OI-11)"),
    ("Hatched", "external measure or driver, credited through an AoU (§11), no ASIL"),
  ]
  ky += 8
  for head, txt in key:
    ky += 16
    body.append(t(kx, ky, head, 11, INK, 700))
    for ln in wrap(txt, 194, 10.5):
      ky += 13.5
      body.append(t(kx, ky, ln, 10.5, MUTED))
    ky += 4
  body.append("</g>")
  y = 846
  body.append(f'<line x1="40" y1="{y}" x2="{w - 40}" y2="{y}" stroke="{HAIR}"/>')
  y += 24
  lx = 40
  for a in ("C", "B", "A"):
    lab = f"ASIL {a}"
    body.append(f'<rect x="{lx}" y="{y - 12}" width="28" height="16" rx="8" fill="{ASIL_FILL[a]}" stroke="{ASIL_STROKE[a]}"/>')
    body.append(t(lx + 36, y, lab, 11))
    lx += 36 + hf.text_w(lab, 11) + 22
  body.append(f'<rect x="{lx}" y="{y - 12}" width="28" height="16" rx="4" fill="#FFFFFF" stroke="{RED}" stroke-width="2.4"/>')
  body.append(t(lx + 36, y, "QM element carrying ASIL FSRs", 11))
  lx += 36 + hf.text_w("QM element carrying ASIL FSRs", 11) + 22
  body.append(f'<line x1="{lx}" y1="{y - 4}" x2="{lx + 30}" y2="{y - 4}" stroke="#C2410C" stroke-width="2.4"/>')
  body.append(t(lx + 38, y, "Actuation path through the envelope", 11))
  y += 20
  body.append(t(40, y, "Every FSR is Proposed: a box shows allocation, not implementation (§5 Impl). FSR-06.05 is allocated "
                "as the FSRs it references and is not counted. ASILs are those of the HARA, not yet confirmed (I3).", 11, MUTED))
  extra, y = terms.svg_footer(body, 40, y + 20, w - 80)
  body += extra
  body.append(t(w - 40, y + 6, "Generated by fsc_safety_view.py", 10, MUTED, None, "end"))
  h = y + 20
  desc = ("The item boundary of WP-C-01 Figure 3-2 with the WP-C-04 allocation on each element. "
          + " ".join(f"{e}: {len(v['fsrs'])} FSRs, highest {v['top'] or 'none'}, serving {', '.join(sorted(v['goals'])) or 'no goal'}"
                     + ("; QM element carrying ASIL FSRs" if v["qm_carries"] else "") + "."
                     for e, v in view.items())
          + f" Driver: no FSR, assumptions {', '.join(aous)}.")
  return svg_doc(w, h, "Figure 10-1. The item boundary in the safety view (WP-C-04 §2, §5, §9, §10)", desc, body)


def build(goals, md: str) -> dict[str, str]:
  return {NAME: figure(goals, md)}
