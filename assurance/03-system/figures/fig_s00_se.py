#!/usr/bin/env python3
"""Draw the systems-engineering Vee of the system folder (fig-s00-1-se-vee.svg) and write the folder's README section
(index-section.md), both from se_alignment.yaml.

The section aligns 03-system with the INCOSE Systems Engineering Handbook (ISO/IEC/IEEE 15288 processes) and the NASA
Systems Engineering Handbook (NPR 7123.1 SE engine). It is informative: ISO 26262 and ASPICE govern LionDriver. The N2
chart and the VCRM in it are the SysML views V-08 and V-09 (assurance/models/sysml), not drawn here.
folder_index.py places index-section.md in 03-system/README.md after the work-products table, its links rebased.

Checks: every WP ID in the YAML is a row of the WP-M-00 register, every folder and path exists, every pair and NASA
process number is known, and NASA processes 1 to 17 each appear once.

    python3 fig_s00_se.py            # write the SVG and index-section.md
    python3 fig_s00_se.py --check    # fail if either is stale or the YAML names something that does not exist

Output is deterministic. Needs PyYAML.
"""
from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

HERE = Path(__file__).resolve().parent
ASSURANCE = HERE.parents[1]
FOLDER = "03-system"
SOURCE = HERE / "se_alignment.yaml"
OUT = "fig-s00-1-se-vee.svg"
SECTION = "index-section.md"
sys.path.insert(0, str(ASSURANCE / "01-management" / "figures"))
import folder_index  # noqa: E402

FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
INK, MUTED, FAINT, LINE, HAIR = "#0F172A", "#475569", "#94A3B8", "#CBD5E1", "#E2E8F0"
OR, OR_BG, BLUE, GREY_BG = "#C2410C", "#FFF7ED", "#2563EB", "#F1F5F9"
NASA = {1: "Stakeholder expectations definition", 2: "Technical requirements definition", 3: "Logical decomposition",
        4: "Design solution definition", 5: "Product implementation", 6: "Product integration",
        7: "Product verification", 8: "Product validation", 9: "Product transition", 10: "Technical planning",
        11: "Requirements management", 12: "Interface management", 13: "Technical risk management",
        14: "Configuration management", 15: "Technical data management", 16: "Technical assessment",
        17: "Decision analysis"}
# Vee placement: box x, y; left arm top-down, bottom, right arm bottom-up, transition above validation
POS = {"needs": (40, 168), "sysreq": (110, 285), "arch": (180, 420), "impl": (450, 560), "integ": (720, 420),
       "verif": (790, 285), "valid": (860, 168), "transition": (860, 44)}
BW, BH, W, H = 340, 112, 1240, 900
N2 = "../models/sysml/generated/fig-sysml-v08-n2-chart.svg"
VCRM = "../models/sysml/generated/fig-sysml-v09-vcrm.svg"


class SeError(Exception):
  pass


def load(path: Path = SOURCE) -> dict:
  return yaml.safe_load(path.read_text(encoding="utf-8"))


def wp_hrefs() -> dict[str, str]:
  """{WP ID: link from the 03-system README} for every row of the WP-M-00 register."""
  regs, _ = folder_index.register_rows()
  return {it["id"]: folder_index.href_in_folder(it["href"], FOLDER) if it["href"] else ""
          for _t, items in regs.values() for it in items}


def problems(d: dict, hrefs: dict[str, str]) -> list[str]:
  out = []
  ids = [s["id"] for s in d["stages"]]
  if [k for k in POS if k not in ids] or [k for k in ids if k not in POS]:
    out.append(f"stages {ids} do not match the Vee placement {list(POS)}")
  for a, b, _ in d["pairs"]:
    if a not in ids or b not in ids:
      out.append(f"pair {a} → {b} names an unknown stage")
  nasa = [n for s in d["stages"] for n in s["nasa"]] + [m["nasa"] for m in d["management"]]
  if sorted(nasa) != list(range(1, 18)):
    out.append(f"NASA processes 1-17 must each appear once, got {sorted(nasa)}")
  for m in d["incose_management"]:
    for n in m.get("nasa", []):
      if n not in NASA:
        out.append(f"{m['name']}: unknown NASA process {n}")
  wps = [w for s in d["stages"] for w in s["wps"]] + [w for m in d["management"] + d["incose_management"]
                                                       for w in m.get("wps", [])]
  for w in wps:
    if w.startswith("folder:"):
      if not (ASSURANCE / w[7:]).is_dir():
        out.append(f"{w}: no such folder")
    elif w not in hrefs:
      out.append(f"{w}: not in the WP-M-00 register")
  paths = [p for m in d["management"] for p in m.get("paths", [])] + [w["path"] for v in d["views"] for w in v["where"]]
  for p in paths:
    if p != f"{FOLDER}/figures/{OUT}" and not (ASSURANCE / p).exists():
      out.append(f"{p}: does not exist")
  for v in d["views"]:
    if v["status"] not in ("present", "partial", "missing"):
      out.append(f"{v['name']}: status {v['status']!r}")
    if v["status"] != "present" and not v.get("gap"):
      out.append(f"{v['name']}: a {v['status']} view needs a gap")
  return out


# ---------------------------------------------------------------- the Vee

def t(x, y, s, size=12, fill=INK, w="", a="", it=False) -> str:
  return (f'<text x="{x:g}" y="{y:g}" font-family="{FONT}" font-size="{size}" fill="{fill}"'
          + (f' font-weight="{w}"' if w else "") + (f' text-anchor="{a}"' if a else "")
          + (' font-style="italic"' if it else "") + f">{escape(str(s))}</text>")


def wrap(s: str, n: int) -> list[str]:
  out, cur = [], ""
  for wd in s.split():
    if len(cur) + len(wd) + 1 > n and cur:
      out.append(cur)
      cur = wd
    else:
      cur = (cur + " " + wd).strip()
  return out + ([cur] if cur else [])


def chip(x, y, n) -> str:
  return f'<circle cx="{x:g}" cy="{y:g}" r="9" fill="{INK}"/>' + t(x, y + 4, n, 10, "#FFFFFF", "700", "middle")


def mine(wps: list[str]) -> list[str]:
  return [w for w in wps if w.startswith("WP-S-")]


def render(d: dict) -> str:
  st = {s["id"]: s for s in d["stages"]}
  b = ['<defs><marker id="ar" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">'
       f'<path d="M0,0 L8,4 L0,8 z" fill="{MUTED}"/></marker></defs>',
       f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
       t(28, 34, "Figure S-0-1. The system folder on the systems-engineering Vee", 18, INK, "600"),
       t(40, 58, "Circles: NASA SE-engine process (NPR 7123.1). Orange: work products in this folder. "
             "Dashed: the right stage checks the left.", 11.5, MUTED),
       t(40, 75, "Informative alignment with the INCOSE SE Handbook (5th ed.) and NASA/SP-2016-6105 Rev 2; "
             "ISO 26262 and ASPICE govern.", 11.5, MUTED, it=True),
       f'<path d="M 60 170 L 520 700 L 1180 170" fill="none" stroke="{HAIR}" stroke-width="44" stroke-linejoin="round"/>']
  for a, c, lab in d["pairs"]:
    (x1, y1), (x2, _) = POS[a], POS[c]
    y = y1 + BH / 2
    b.append(f'<line x1="{x1 + BW}" y1="{y:g}" x2="{x2}" y2="{y:g}" stroke="{BLUE}" stroke-width="1.6" stroke-dasharray="6 4"/>')
    b.append(t((x1 + BW + x2) / 2, y - 6, lab, 11, BLUE, "600", "middle"))
  vx = POS["valid"][0] + BW / 2
  b.append(f'<line x1="{vx:g}" y1="{POS["valid"][1]}" x2="{vx:g}" y2="{POS["transition"][1] + 100}" stroke="{MUTED}" '
           'stroke-width="1.4" marker-end="url(#ar)"/>')
  for sid, (x, y) in POS.items():
    s = st[sid]
    h = 100 if sid == "transition" else BH
    here = mine(s["wps"])
    b.append(f'<rect x="{x}" y="{y}" width="{BW}" height="{h}" rx="8" fill="{OR_BG if here else "#FFFFFF"}" '
             f'stroke="{OR if here else LINE}" stroke-width="{1.8 if here else 1.2}"/>')
    b.append(t(x + 12, y + 20, s["title"], 13, INK, "700"))
    if s["aspice"] != "—":
      b.append(t(x + BW - 10, y + 20, s["aspice"], 10, FAINT, "", "end"))
    cx = x + 12
    for n in s["nasa"]:
      b.append(chip(cx + 9, y + 36, n))
      cx += 22
    yy = y + 40
    for ln in wrap("INCOSE · 15288: " + ", ".join(s["incose"]), 50)[:2]:
      b.append(t(cx + 4, yy, ln, 10.5, MUTED))
      yy += 13
    if sid != "transition":
      yy = max(yy, y + 64)
    other = [w[7:] + "/" if w.startswith("folder:") else w for w in s["wps"] if not w.startswith("WP-S-")]
    if here:
      b.append(t(x + 12, yy + 6, "This folder: " + ", ".join(here), 11, OR, "700"))
      yy += 15
    for ln in wrap("Elsewhere: " + ", ".join(other), 54)[:2] if other else []:
      b.append(t(x + 12, yy + 6, ln, 10.5, MUTED))
      yy += 13
  y0 = 715
  b.append(t(40, y0 - 10, "Technical management (NASA SE engine 10–17; ISO/IEC/IEEE 15288 technical management)",
             12.5, INK, "700"))
  cw = (W - 80) / len(d["management"])
  for i, m in enumerate(d["management"]):
    x = 40 + i * cw
    here = mine(m.get("wps", []))
    b.append(f'<rect x="{x + 3:g}" y="{y0}" width="{cw - 6:g}" height="74" rx="6" fill="{OR_BG if here else GREY_BG}" '
             f'stroke="{OR if here else LINE}"/>')
    b.append(chip(x + 17, y0 + 16, m["nasa"]))
    for k, ln in enumerate(wrap(m["name"], 16)[:2]):
      b.append(t(x + 31, y0 + 20 + k * 13, ln, 11, INK, "600"))
    where = ", ".join(m.get("wps", []) + [Path(p).parent.name + "/" if p.endswith("README.md") else p
                                          for p in m.get("paths", [])])
    for k, ln in enumerate(wrap(where, 22)[:2]):
      b.append(t(x + 10, y0 + 50 + k * 12, ln, 10, OR if here else MUTED))
  y1 = 818
  b.append(t(40, y1 - 8, "LionDriver gates (WP-M-00 §2) and the nearest NASA life-cycle review (informative)",
             12.5, INK, "700"))
  gw = (W - 80) / len(d["gates"])
  for i, g in enumerate(d["gates"]):
    x = 40 + i * gw
    b.append(f'<rect x="{x + 3:g}" y="{y1}" width="{gw - 6:g}" height="40" rx="6" fill="#FFFFFF" stroke="{LINE}"/>')
    b.append(t(x + 14, y1 + 25, g["gate"], 13, INK, "700"))
    b.append(t(x + gw - 12, y1 + 25, g["review"], 12, BLUE, "600", "end"))
  desc = ("The system folder's work products placed on the systems-engineering Vee: " + "; ".join(
    f"{s['title']} (NASA {', '.join(map(str, s['nasa']))}): {', '.join(s['wps'])}" for s in d["stages"]) + ".")
  return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">'
          f"<title>Figure S-0-1. The system folder on the systems-engineering Vee</title><desc>{escape(desc)}</desc>"
          + "\n".join(b) + "\n</svg>\n")


# ---------------------------------------------------------------- README section

def link(w: str, hrefs: dict[str, str]) -> str:
  if w.startswith("folder:"):
    return f"[`{w[7:]}/`](../{w[7:]}/README.md)"
  return f"[{w}]({hrefs[w]})" if hrefs.get(w) else w


def rel(p: str) -> str:
  return p[len(FOLDER) + 1:] if p.startswith(FOLDER + "/") else "../" + p


def section_md(d: dict, hrefs: dict[str, str]) -> str:
  out = ["## Systems engineering alignment", "",
         "Where this folder sits in the systems-engineering processes of the INCOSE Systems Engineering Handbook "
         "(5th ed., 2023; the technical processes of ISO/IEC/IEEE 15288) and the NASA Systems Engineering Handbook "
         "(NASA/SP-2016-6105 Rev 2; the 17 processes of the NPR 7123.1 SE engine). The alignment is informative: "
         "ISO 26262 and ASPICE govern LionDriver, and nothing here claims compliance with either handbook. "
         "The N2 chart and the VCRM are views of the [SysML model](../models/sysml/README.md), drawn from it on every build.", "",
         f"![The system folder on the systems-engineering Vee: stakeholder needs, system requirements and architecture "
         f"down the left arm, implementation at the bottom, integration, verification and validation up the right arm, "
         f"each with its NASA process numbers and work products; technical management processes 10 to 17 and the gates "
         f"G0 to G6 with the nearest NASA reviews below](figures/{OUT})", "",
         "| Stage | INCOSE / ISO/IEC/IEEE 15288 | NASA | ASPICE | Work products |", "|---|---|---|---|---|"]
  for s in d["stages"]:
    nasa = ", ".join(f"{n} {NASA[n].lower()}" for n in s["nasa"])
    out.append(f"| {s['title']} | {', '.join(s['incose'])} | {nasa} | {s['aspice']} | "
               f"{', '.join(link(w, hrefs) for w in s['wps'])} |")
  out += ["", "| NASA technical management | Where LionDriver keeps it |", "|---|---|"]
  for m in d["management"]:
    where = [link(w, hrefs) for w in m.get("wps", [])] + [f"[`{Path(p).parent.as_posix()}/`]({rel(p)})"
                                                          for p in m.get("paths", [])]
    out.append(f"| {m['nasa']} {m['name'].lower()} | {', '.join(where)} |")
  im = "; ".join(f"{m['name'].lower()} ({'NASA ' + ', '.join(map(str, m['nasa'])) if m.get('nasa') else ', '.join(link(w, hrefs) for w in m['wps'])})"
                 for m in d["incose_management"])
  gates = ", ".join(f"{g['gate']} {g['review']}" for g in d["gates"])
  out += ["", f"The 15288 technical management processes map onto these: {im}. Nearest NASA life-cycle review per gate "
          f"(informative): {gates}.", "",
          "### Interfaces: N2 chart", "",
          "Generated from the SysML model (view V-08). A row sends to a column over the interfaces in the cell.", "",
          f"![V-08: N2 chart of the components E-01 to E-05 and the elements outside the item, generated from the SysML "
          f"model]({N2})", "",
          "### Verification: VCRM", "",
          "Generated from the SysML model (view V-09): requirements by verification method, grouped as NASA analysis, "
          "inspection, demonstration and test, and by the level of their verification cases. One row per requirement: "
          "[`vcrm.md`](../models/sysml/generated/vcrm.md).", "",
          f"![V-09: verification matrix of the SYS, TSR and CSR requirements, generated from the SysML model]({VCRM})", "",
          "### Views the handbooks expect", "",
          "| View | Status | Where | Gap |", "|---|---|---|---|"]
  for v in d["views"]:
    where = ", ".join(f"[{w['label']}]({rel(w['path'])})" for w in v["where"])
    out.append(f"| {v['name']} | {v['status']} | {where} | {v.get('gap', '—')} |")
  return "\n".join(out) + "\n"


def build() -> dict[Path, str]:
  d = load()
  hrefs = wp_hrefs()
  errs = problems(d, hrefs)
  if errs:
    raise SeError("; ".join(errs))
  # the section is written for the folder README; the file lives in figures/, so its links are stored from there
  text = folder_index.rebase_from(section_md(d, hrefs), HERE.parent, HERE)
  return {HERE / OUT: render(d), HERE / SECTION: text}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except SeError as e:
    print(f"fig_s00_se: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [p for p, c in outputs.items() if not p.exists() or p.read_text(encoding="utf-8") != c]
    for p in stale:
      print(f"stale: {p.relative_to(ASSURANCE).as_posix()}; run: python3 assurance/03-system/figures/fig_s00_se.py",
            file=sys.stderr)
    return 1 if stale else 0
  for p, c in outputs.items():
    p.write_text(c, encoding="utf-8")
  print(f"fig_s00_se: wrote {OUT} and {SECTION}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
