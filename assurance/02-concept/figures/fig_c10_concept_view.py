#!/usr/bin/env python3
"""Draw WP-C-10 Figure 6-1, the cybersecurity concept on the item (fig-c10-6-1-concept-view.svg).

The concept-level cybersecurity requirements CSR-C-nn of WP-C-10 §7 on the places §6 allocates them to: the panda
safety firmware (E-03) and the SoC (E-01/E-02) inside the item, the comma.ai back end and the owner or installer
outside it. Each requirement row shows the goal it serves (§4) with its CAL, a short statement and its status at the
baseline. A requirement allocated to several places is drawn in each, marked "shared".

Status, from the §7 "Status / evidence" column (the latest dated update when there is one):
  implemented  "Implemented …" (the reference build, not verified)
  partly       "Partial …", "Partially …"
  not yet      "Not implemented", "Not met", "Not confirmed"

    python3 fig_c10_concept_view.py            # write the SVG
    python3 fig_c10_concept_view.py --check    # fail if an allocation or status cannot be read, or the SVG is stale

Standard library only. Drawing helpers come from ../hara/hara_figures.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "WP-C-10-cybersecurity-goals-and-concept.md"
OUT = "fig-c10-6-1-concept-view.svg"
sys.path.insert(0, str(HERE.parent / "hara"))
import hara_figures as hf  # noqa: E402
from hara_figures import INK, MUTED, HAIR, t, wrap, header, svg_doc  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)

# Places and the words of the §7 Allocation column that put a requirement there.
PLACES = [
  ("E-03", "E-03 panda safety firmware", "the envelope: safety mode, boot chain, CAN checks", ("panda FW",), True),
  ("E-01", "E-01/E-02 SoC software and models", "openpilot, params and IPC, updater, SSH, remote access", ("SoC",), True),
  ("BACKEND", "comma.ai back end", "update signing, transport; outside the item (CA-01)", ("back end",), False),
  ("USER", "Owner, installer and operation", "provisioning, opt-in, decommissioning, incident response", ("user",), False),
]
STATUS = {"impl": ("implemented", "#1D4ED8", "#EFF6FF"), "partial": ("partly", "#B45309", "#FFFBEB"),
          "not": ("not yet", "#B42318", "#FEF2F2")}


class ConceptError(ValueError):
  pass


def _cells(ln: str) -> list[str]:
  return [c.strip() for c in ln.strip()[1:-1].split("|")]


def classify(status: str) -> str:
  s = status.replace("`", "")
  dated = re.findall(r"\*\*\d{4}-\d\d-\d\d: ([^*]+)\*\*", s)
  head = (dated[-1] if dated else s).strip().lower()
  if head.startswith("implemented"):
    return "impl"
  if head.startswith("partial"):
    return "partial"
  if head.startswith("not "):
    return "not"
  raise ConceptError(f"cannot read status {status[:60]!r}")


def parse(md: str) -> dict:
  goals = {}
  for ln in md.splitlines():
    if ln.startswith("| **CSG-"):
      c = _cells(ln)
      cal = re.search(r"CAL (\d)", c[3])
      goals[c[0].strip("*")] = cal.group(1) if cal else "?"
  reqs = []
  for ln in md.splitlines():
    if ln.startswith("| CSR-C-"):
      c = _cells(ln)
      places = [p for p, _, _, words, _ in PLACES if any(w in c[4] for w in words)]
      if not places:
        raise ConceptError(f"{c[0]}: allocation {c[4]!r} names no place")
      parents = re.findall(r"CSG-\d\d", c[2])
      for g in parents:
        if g not in goals:
          raise ConceptError(f"{c[0]}: parent {g} is not a goal of §4")
      reqs.append({"id": c[0], "text": re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", c[1]).replace("`", ""),
                   "goals": parents, "cal": c[3], "places": places, "status": classify(c[6])})
  if not goals or not reqs:
    raise ConceptError("WP-C-10 §4 or §7 table not found")
  return {"goals": goals, "reqs": reqs}


def figure(d: dict) -> str:
  W = 1280
  body = header(W, "Figure 6-1 · The cybersecurity concept on the item",
                "The concept-level requirements of §7 on the places §6 allocates them to, with the goal each serves, its "
                "CAL and its status at the baseline", "WP-C-10 §4, §6, §7", "item: WP-C-01 §3")
  col = {"E-03": (40, 600), "E-01": (40, 600), "BACKEND": (660, 580), "USER": (660, 580)}
  ys = {"left": 116, "right": 116}
  inside_top = None
  boxes = []
  for key, title, sub, _, inside in PLACES:
    x, w = col[key]
    side = "left" if inside else "right"
    y0 = ys[side]
    rows = [r for r in d["reqs"] if key in r["places"]]
    rh = []
    for r in rows:
      lines = wrap(r["text"], w - 372, 10.5)[:2]
      rh.append(max(38, 12 + 13.5 * len(lines)))
    h = 52 + sum(rh) + 8
    boxes.append((key, title, sub, inside, x, y0, w, h, rows, rh))
    ys[side] = y0 + h + 14
    if inside and inside_top is None:
      inside_top = y0
  # item boundary around the two inside places
  bottom_inside = max(b[5] + b[7] for b in boxes if b[3])
  body.append(f'<rect x="28" y="{inside_top - 22}" width="624" height="{bottom_inside - inside_top + 36}" rx="14" '
              'fill="#FFFDF7" stroke="#C2410C" stroke-width="1.5" stroke-dasharray="7 5"/>')
  body.append(t(44, inside_top - 6, "ITEM BOUNDARY · LD-SDA", 10.5, "#C2410C", 700))
  for key, title, sub, inside, x, y0, w, h, rows, rh in boxes:
    y0 += 10 if inside else 0
    dash = "" if inside else ' stroke-dasharray="5 4"'
    body.append(f'<rect x="{x}" y="{y0}" width="{w}" height="{h}" rx="10" fill="{"#FFFFFF" if inside else "#F8FAFC"}" '
                f'stroke="#94A3B8" stroke-width="1.3"{dash}/>')
    body.append(t(x + 12, y0 + 21, title, 12.5, INK, 700))
    body.append(t(x + 12, y0 + 37, sub, 10, MUTED))
    ry = y0 + 50
    for r, hh in zip(rows, rh):
      lab, stroke, fill = STATUS[r["status"]]
      body.append(f'<rect x="{x + 8}" y="{ry}" width="{w - 16}" height="{hh - 4}" rx="6" fill="{fill}" stroke="{stroke}" stroke-opacity=".35"/>')
      body.append(f'<rect x="{x + 8}" y="{ry}" width="4" height="{hh - 4}" rx="2" fill="{stroke}"/>')
      body.append(t(x + 20, ry + 17, r["id"], 11, INK, 700))
      gx = x + 92
      for g in r["goals"] or ["(all)"]:
        gl = g if g.startswith("CSG") else "supports all"
        gw = hf.text_w(gl, 9.5, True) + 10
        body.append(f'<rect x="{gx}" y="{ry + 6}" width="{gw:.1f}" height="16" rx="4" fill="#FFFFFF" stroke="#7C3AED"/>')
        body.append(t(gx + gw / 2, ry + 17.5, gl, 9.5, "#5B21B6", 700, "middle"))
        gx += gw + 4
      body.append(t(x + 214, ry + 17, f"CAL {r['cal']}", 10, INK, 700))
      for j, ln in enumerate(wrap(r["text"], w - 372, 10.5)[:2]):
        body.append(t(x + 262, ry + 17 + 13.5 * j, ln + ("…" if j == 1 and len(wrap(r["text"], w - 372, 10.5)) > 2 else ""), 10.5, INK))
      sw = hf.text_w(lab, 9.5, True) + 12
      body.append(f'<rect x="{x + w - 16 - sw}" y="{ry + 6}" width="{sw:.1f}" height="16" rx="8" fill="#FFFFFF" stroke="{stroke}"/>')
      body.append(t(x + w - 16 - sw / 2, ry + 17.5, lab, 9.5, stroke, 700, "middle"))
      if len(r["places"]) > 1:
        body.append(t(x + 214, ry + 30, "shared", 9.5, MUTED, None, None, ' font-style="italic"'))
      ry += hh
  y = max(b[5] + b[7] for b in boxes) + 30
  counts = {k: sum(1 for r in d["reqs"] if r["status"] == k) for k in STATUS}
  lx = 40
  for k, (lab, stroke, fill) in STATUS.items():
    s = f"{lab} ({counts[k]})"
    body.append(f'<rect x="{lx}" y="{y - 11}" width="30" height="15" rx="4" fill="{fill}" stroke="{stroke}"/>')
    body.append(t(lx + 38, y, s, 11))
    lx += 38 + hf.text_w(s, 11) + 22
  body.append(f'<rect x="{lx}" y="{y - 12}" width="52" height="16" rx="4" fill="#FFFFFF" stroke="#7C3AED"/>')
  body.append(t(lx + 26, y, "CSG-nn", 9.5, "#5B21B6", 700, "middle"))
  body.append(t(lx + 60, y, "the goal it serves (§4)", 11))
  y += 20
  body.append(t(40, y, "Implemented means in the reference build and not verified; no requirement is verified yet. CAL "
                "values are proposals for the assessor (§3). Each requirement is refined in WP-S-07.", 11, MUTED))
  extra, y = terms.svg_footer(body, 40, y + 20, W - 80)
  body += extra
  body.append(t(W - 40, y + 6, "Generated by fig_c10_concept_view.py", 10, MUTED, None, "end"))
  h = y + 20
  desc = ("The concept-level cybersecurity requirements of WP-C-10 §7 by place. " + " ".join(
    f"{title}: " + ", ".join(f"{r['id']} ({STATUS[r['status']][0]})" for r in d["reqs"] if key in r["places"]) + "."
    for key, title, *_ in PLACES))
  return svg_doc(W, h, "Figure 6-1. The cybersecurity concept on the item (WP-C-10 §4, §6, §7)", desc, body)


def build() -> dict[str, str]:
  return {OUT: figure(parse(SOURCE.read_text(encoding="utf-8")))}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except ConceptError as e:
    print(f"fig_c10_concept_view: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"assurance/02-concept/figures/{n} is stale; run fig_c10_concept_view.py", file=sys.stderr)
    if not stale:
      print(f"fig_c10_concept_view: {len(outputs)} figure current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote assurance/02-concept/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
