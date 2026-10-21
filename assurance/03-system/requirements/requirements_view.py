#!/usr/bin/env python3
"""Write the requirements view of the FSC and TSC: README.md, the FSR and TSR lists and their figures.

Everything is drawn from assurance/trace/items (fsr.yaml, tsr.yaml, goals.yaml), the copies of WP-C-04 §5/§9 and
WP-S-02 §3–§12 / WP-S-06 that sync_requirements.py regenerates and CI keeps in step with the documents:

  README.md                         counts, coverage findings, links to everything below
  figures/fig-req-0-status.svg      status of the FSRs and the TSRs as two bars
  figures/fig-req-1-sg-0N-tree.svg  one tree per safety goal: SG → its FSRs → their TSRs
  figures/fig-req-2-matrix.svg      FSR × TSR matrix of every parent link
  fsr-list.md, tsr-list.md          one line per requirement: ID, parents, ASIL, allocation, status, first sentence

Status per requirement is the rule of WP-S-03 Figure 6-1 (fig_s03_defence_in_depth.classify), read from the Impl
column: implemented, partly, not implemented, assumed. Nothing is verified on hardware, so implemented is blue.

    python3 requirements_view.py            # write all outputs
    python3 requirements_view.py --check    # fail if an output is stale

Standard library only. Output is deterministic.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "assurance" / "03-system" / "figures"))
import fig_s03_defence_in_depth as dd  # noqa: E402  (status rule and YAML loader)

ITEMS = REPO / "assurance" / "trace" / "items"
WP_C04 = REPO / "assurance" / "02-concept" / "WP-C-04-functional-safety-concept.md"
WP_S02 = REPO / "assurance" / "03-system" / "WP-S-02-technical-safety-requirements.md"

FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SFMono-Regular', Menlo, Consolas, monospace"
INK, MUTED, FAINT, HAIR, LINE = "#0F172A", "#475569", "#94A3B8", "#E2E8F0", "#CBD5E1"
SAFETY, SAFETY_BG, ALSO = "#C2410C", "#FFF7ED", "#7C3AED"
STATES = ("implemented", "partly", "not", "assumed")
COL = {"implemented": "#1D4ED8", "partly": "#D97706", "not": "#D2553F", "assumed": "#94A3B8"}
BG = {"implemented": "#EFF6FF", "partly": "#FFFBEB", "not": "#FEF2F2", "assumed": "#F1F5F9"}
LABEL = {"implemented": "implemented", "partly": "partly", "not": "not implemented", "assumed": "assumed (EXT / AoU)"}
BLOCKS = {"1": "Lateral", "2": "Longit.", "3": "Engagement", "4": "Comms", "5": "MCU platform", "6": "Host / SoC",
          "7": "PCS, harness", "8": "Operation"}
W, M = 1280, 40


# ---------------------------------------------------------------- data

def load() -> tuple[list[dict], list[dict], dict[str, dict]]:
  fs = sorted(dd.ct.load_yaml(ITEMS / "fsr.yaml"), key=lambda f: f["id"])
  ts = sorted(dd.ct.load_yaml(ITEMS / "tsr.yaml"), key=lambda t: int(t["id"][4:]))
  goals = {g["id"]: g for g in dd.ct.load_yaml(ITEMS / "goals.yaml")}
  return fs, ts, goals


def fsr_parents(tsr: dict) -> list[str]:
  return [p for p in tsr.get("parents", []) if str(p).startswith("FSR")]


def children(fs: list[dict], ts: list[dict]) -> dict[str, list[dict]]:
  out = {f["id"]: [] for f in fs}
  for t in ts:
    for p in fsr_parents(t):
      out.setdefault(p, []).append(t)
  return out


def by_reference(f: dict) -> bool:
  """An FSR that applies other FSRs' mechanisms (WP-C-04: verification "as referenced") has no TSR of its own."""
  return "referenced" in str(f.get("verification", ""))


def asil(s) -> str:
  s = str(s)
  if s.startswith("—") or s.startswith("ext"):
    return "ext"
  if s.startswith("as ref"):
    return "ref"
  m = re.search(r"\b(QM|[ABCD])(‡)?", s)
  return (m.group(1) + (m.group(2) or "")) if m else "·"


def plain(s) -> str:
  return re.sub(r"[`*]", "", str(s)).replace("|", "/")


def short_alloc(s) -> str:
  """Allocation without its parenthetical detail (kept in the work product)."""
  s = plain(s)
  while re.search(r"\s*\([^()]*\)", s):
    s = re.sub(r"\s*\([^()]*\)", "", s)
  return s.strip()


def first_sentence(s, n: int) -> str:
  s = plain(s)
  s = re.split(r"(?<=[a-z0-9)])\. ", s, maxsplit=1)[0].rstrip(".")
  return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + " …"


def slug(heading: str) -> str:
  """GitHub's anchor for a Markdown heading."""
  s = heading.strip().lower()
  s = re.sub(r"[^\w\- ]", "", s, flags=re.UNICODE)
  return s.replace(" ", "-")


def heading_anchors(path: Path) -> list[tuple[str, str]]:
  return [(h, slug(h)) for h in re.findall(r"^#{2,3} (.+)$", path.read_text(encoding="utf-8"), re.M)]


def tsr_link(t: dict, s02: list[tuple[str, str]]) -> str:
  if t.get("source") == "WP-S-06":
    return "../WP-S-06-requirements-production-operation.md"
  block = t["id"][4] + "xx"
  for h, a in s02:
    if f"TSR-{block}" in h:
      return f"../WP-S-02-technical-safety-requirements.md#{a}"
  return "../WP-S-02-technical-safety-requirements.md"


def fsr_link(c04: list[tuple[str, str]]) -> str:
  for h, a in c04:
    if h.startswith("5. "):
      return f"../../02-concept/WP-C-04-functional-safety-concept.md#{a}"
  return "../../02-concept/WP-C-04-functional-safety-concept.md"


# ---------------------------------------------------------------- SVG helpers

def text(x, y, s, size=11, fill=INK, weight="", anchor="", mono=False) -> str:
  w = f' font-weight="{weight}"' if weight else ""
  a = f' text-anchor="{anchor}"' if anchor else ""
  f = f' font-family="{MONO}"' if mono else ""
  return f'<text x="{x}" y="{y}" font-size="{size:g}" fill="{fill}"{w}{a}{f}>{escape(str(s))}</text>'


def wrap(s: str, chars: int, lines: int) -> list[str]:
  out, cur = [], ""
  for word in s.split():
    if cur and len(cur) + 1 + len(word) > chars:
      out.append(cur)
      cur = word
    else:
      cur = f"{cur} {word}".strip()
  if cur:
    out.append(cur)
  if len(out) > lines:
    out = out[:lines]
    out[-1] = out[-1][: max(1, chars - 2)].rstrip() + " …"
  return out


def svg(title: str, desc: str, height: float, body: list[str]) -> str:
  h = int(height)
  return "\n".join([
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" font-family="{FONT}" '
    'role="img" aria-labelledby="t d">',
    f'<title id="t">{escape(title)}</title>', f'<desc id="d">{escape(desc)}</desc>',
    f'<rect width="{W}" height="{h}" fill="#FFFFFF"/>', *body, "</svg>"]) + "\n"


def legend(y: float, extra: list[tuple[str, str]] = ()) -> list[str]:
  out = [f'<line x1="{M}" y1="{y - 22}" x2="{W - M}" y2="{y - 22}" stroke="{HAIR}"/>']
  x = M
  for k in STATES:
    out.append(f'<rect x="{x}" y="{y - 10}" width="22" height="13" rx="3" fill="{BG[k]}" stroke="{COL[k]}"/>')
    out.append(text(x + 30, y, LABEL[k], 10.5))
    x += 190
  for dash, label in extra:
    out.append(f'<rect x="{x}" y="{y - 10}" width="22" height="13" rx="3" fill="#FFFFFF" stroke="{MUTED}"'
               f' stroke-dasharray="{dash}"/>')
    out.append(text(x + 30, y, label, 10.5))
    x += 330
  out.append(text(M, y + 24, "Status from each requirement's Impl column by the rule of WP-S-03 Figure 6-1 (a qualified "
                  "“Implemented” counts as partly). Nothing is verified on hardware yet, so implemented is blue, never "
                  "green.", 9.5, MUTED))
  return out


# ---------------------------------------------------------------- figures

def status_figure(fs: list[dict], ts: list[dict]) -> str:
  body = [text(M, 34, "Requirement status", 18, INK, "700"),
          text(W - M, 34, "WP-C-04 §5 · WP-S-02 · WP-S-06", 11, MUTED, anchor="end")]
  y = 66
  for name, items, src in (("FSR", fs, "functional safety requirements"), ("TSR", ts, "technical safety requirements")):
    c = Counter(dd.classify(i) for i in items)
    body.append(text(M, y + 15, f"{len(items)}", 22, INK, "700"))
    body.append(text(M + 56, y + 6, name, 12, INK, "700"))
    body.append(text(M + 56, y + 21, src, 10, MUTED))
    x, bw = 300.0, W - M - 300
    for k in STATES:
      if c[k]:
        w = bw * c[k] / len(items)
        body.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="22" fill="{COL[k]}"/>')
        if w > 34:
          body.append(text(f"{x + w / 2:.1f}", y + 15, c[k], 11, "#FFFFFF", "700", "middle"))
        x += w
    y += 44
  x = 300
  for k in STATES:
    body.append(f'<rect x="{x}" y="{y - 9}" width="12" height="12" rx="2" fill="{COL[k]}"/>')
    body.append(text(x + 18, y + 1, LABEL[k], 10.5, MUTED))
    x += 170
  desc = "; ".join(f"{n}: {len(i)}, " + ", ".join(f"{Counter(dd.classify(x) for x in i)[k]} {LABEL[k]}" for k in STATES)
                   for n, i in (("FSRs", fs), ("TSRs", ts)))
  return svg("Requirement status: FSRs and TSRs", desc, y + 20, body)


def tree_figure(sg: str, goal: dict, fs: list[dict], kids: dict[str, list[dict]]) -> str:
  mine = [f for f in fs if sg in f.get("parents", [])]
  RX, RW, FX, FW, TX, CW, CH, CG = M, 230, 300, 380, 712, 82, 20, 6
  per = int((W - M - TX + CG) // (CW + CG))
  rows, y = [], 100
  for f in mine:
    n = len(kids[f["id"]])
    h = max(58, -(-n // per) * (CH + CG) + 18)
    rows.append((f, y, h))
    y += h + 10
  bottom = y if rows else 160
  body = []
  rh = 150
  ry = max(100, (100 + bottom - 10) / 2 - rh / 2)
  body.append(f'<rect x="{RX}" y="{ry:.1f}" width="{RW}" height="{rh}" rx="12" fill="{SAFETY_BG}" stroke="{SAFETY}" '
              'stroke-width="1.8"/>')
  body.append(text(RX + 16, f"{ry + 26:.1f}", sg, 16, INK, "700"))
  body.append(f'<rect x="{RX + RW - 80}" y="{ry + 12:.1f}" width="66" height="20" rx="10" fill="{SAFETY}"/>')
  body.append(text(RX + RW - 47, f"{ry + 26:.1f}", f"ASIL {asil(goal.get('asil'))}", 10.5, "#FFFFFF", "700", "middle"))
  for k, line in enumerate(wrap(first_sentence(goal.get("text", ""), 200), 36, 6)):
    body.append(text(RX + 16, f"{ry + 48 + 15 * k:.1f}", line, 11))
  if rows:
    bx = RX + RW + 30
    body.append(f'<line x1="{RX + RW}" y1="{ry + rh / 2:.1f}" x2="{bx}" y2="{ry + rh / 2:.1f}" stroke="{MUTED}" '
                'stroke-width="1.4"/>')
    body.append(f'<line x1="{bx}" y1="{rows[0][1] + rows[0][2] / 2:.1f}" x2="{bx}" '
                f'y2="{rows[-1][1] + rows[-1][2] / 2:.1f}" stroke="{MUTED}" stroke-width="1.4"/>')
  for f, fy, fh in rows:
    s = dd.classify(f)
    cy = fy + fh / 2
    body.append(f'<line x1="{RX + RW + 30}" y1="{cy:.1f}" x2="{FX}" y2="{cy:.1f}" stroke="{MUTED}" stroke-width="1.4"/>')
    body.append(f'<rect x="{FX}" y="{fy}" width="{FW}" height="{fh}" rx="8" fill="#FFFFFF" stroke="{COL[s]}" '
                'stroke-width="1.5"/>')
    body.append(f'<rect x="{FX}" y="{fy}" width="5" height="{fh}" rx="2" fill="{COL[s]}"/>')
    body.append(text(FX + 14, fy + 18, f["id"], 11.5, INK, "700", mono=True))
    body.append(text(FX + 100, fy + 18, f"ASIL {asil(f.get('asil'))}", 10, MUTED, "700"))
    others = [p for p in f.get("parents", []) if p != sg]
    if others:
      also = "also " + ", ".join(others) if len(others) <= 3 else "also SG-" + ", ".join(o[3:] for o in others)
      body.append(text(FX + FW - 10, fy + 18, also, 9.5, ALSO, "600", "end"))
    for k, line in enumerate(wrap(first_sentence(f.get("text", ""), 150), 66, max(1, int((fh - 26) // 13)))):
      body.append(text(FX + 14, fy + 35 + 13 * k, line, 10, MUTED))
    k = kids[f["id"]]
    if not k:
      body.append(text(TX, f"{cy + 4:.1f}", "by reference: the shared TSRs of the FSRs it names" if by_reference(f)
                       else "no TSR", 10.5, MUTED if by_reference(f) else COL["not"], "700"))
      continue
    body.append(f'<line x1="{FX + FW}" y1="{cy:.1f}" x2="{TX - 6}" y2="{cy:.1f}" stroke="{LINE}" stroke-width="1.4"/>')
    top = fy + (fh - (-(-len(k) // per)) * (CH + CG) + CG) / 2
    for i, t in enumerate(k):
      cx = TX + (i % per) * (CW + CG)
      yy = top + (i // per) * (CH + CG)
      st = dd.classify(t)
      dash = ' stroke-dasharray="3 2"' if len(fsr_parents(t)) > 1 else ""
      body.append(f'<rect x="{cx}" y="{yy:.1f}" width="{CW}" height="{CH}" rx="5" fill="{BG[st]}" stroke="{COL[st]}" '
                  f'stroke-width="1.1"{dash}/>')
      body.append(text(cx + CW / 2, f"{yy + 14:.1f}", t["id"], 10, INK, "600", "middle", mono=True))
  n_t = len({t["id"] for f in mine for t in kids[f["id"]]})
  head = [text(M, 44, f"{sg} requirement tree", 20, INK, "700"),
          text(M, 66, f"{sg} → {len(mine)} FSRs (WP-C-04 §5, §9) → {n_t} TSRs (WP-S-02 §12.1) · coloured by status",
               12, MUTED),
          text(W - M, 44, "generated from trace/items", 11, MUTED, anchor="end")]
  height = bottom + 90
  leg = legend(height - 60, [("3 2", "TSR shared with another FSR (drawn under each)")])
  desc = (f"{sg} (ASIL {asil(goal.get('asil'))}): " + "; ".join(
    f"{f['id']} ({LABEL[dd.classify(f)]}) → " + (", ".join(f"{t['id']} ({LABEL[dd.classify(t)]})" for t in kids[f["id"]])
                                                 or ("by reference" if by_reference(f) else "no TSR"))
    for f in mine) + ".")
  return svg(f"{sg} requirement tree: FSRs and TSRs", desc, height, head + body + leg)


def matrix_figure(fs: list[dict], ts: list[dict], goals: dict[str, dict], kids: dict[str, list[dict]]) -> str:
  L, TOP, RH = 250, 190, 13
  pitch = (W - M - L) / len(ts)
  xs = {t["id"]: L + i * pitch for i, t in enumerate(ts)}
  status_t = {t["id"]: dd.classify(t) for t in ts}
  fg, body, y, group, row_y = [], [], TOP, None, {}
  for f in fs:
    g = "SG-" + f["id"][4:6]
    if g != group:
      y += 20 if group else 6
      body.append(text(M, y - 4, f"{g} · ASIL {asil(goals.get(g, {}).get('asil'))}", 10.5, MUTED, "700"))
      body.append(f'<line x1="{M}" y1="{y}" x2="{W - M}" y2="{y}" stroke="{HAIR}"/>')
      y += 4
      group = g
    y += RH
    row_y[f["id"]] = y
  yb = y + 22
  for b, name in BLOCKS.items():
    cs = [t for t in ts if t["id"][4] == b]
    if not cs:
      continue
    x0, x1 = xs[cs[0]["id"]] - 1, xs[cs[-1]["id"]] + pitch - 1
    if int(b) % 2:
      fg.append(f'<rect x="{x0:.1f}" y="{TOP - 58}" width="{x1 - x0:.1f}" height="{yb - TOP + 66}" fill="#F8FAFC"/>')
    body.append(text(f"{(x0 + x1) / 2:.1f}", TOP - 44, f"{b}xx", 10.5, INK, "700", "middle"))
    body.append(text(f"{(x0 + x1) / 2:.1f}", TOP - 31, name, 9, MUTED, anchor="middle"))
  for t in ts:
    body.append(f'<rect x="{xs[t["id"]] + 0.8:.1f}" y="{TOP - 22}" width="{pitch - 1.6:.1f}" height="5" '
                f'fill="{COL[status_t[t["id"]]]}"/>')
  for t in ts[::5]:
    body.append(text(f"{xs[t['id']] + pitch / 2:.1f}", TOP - 8, t["id"][4:], 7.5, MUTED, anchor="middle"))
  for f in fs:
    yy = row_y[f["id"]]
    n = len(kids[f["id"]])
    body.append(f'<line x1="{L - 2}" y1="{yy - 4}" x2="{W - M}" y2="{yy - 4}" stroke="#F1F5F9"/>')
    body.append(f'<circle cx="{M + 6}" cy="{yy - 4}" r="3.5" fill="{COL[dd.classify(f)]}"/>')
    body.append(text(M + 16, yy, f["id"], 10.5, INK, "600", mono=True))
    body.append(text(M + 98, yy, asil(f.get("asil")), 9.5, MUTED, "700"))
    if n:
      body.append(text(L - 12, yy, n, 9.5, MUTED, anchor="end"))
    else:
      body.append(text(L - 12, yy, "by ref." if by_reference(f) else "no TSR", 9.5,
                       MUTED if by_reference(f) else COL["not"], "700", "end"))
    for t in kids[f["id"]]:
      body.append(f'<rect x="{xs[t["id"]] + 0.6:.1f}" y="{yy - 9}" width="{pitch - 1.2:.1f}" height="10" rx="1.5" '
                  f'fill="{COL[status_t[t["id"]]]}"/>')
  orphans = [t for t in ts if not fsr_parents(t)]
  body.append(text(M + 16, yb, "no FSR parent", 10, MUTED, "600"))
  body.append(text(L - 12, yb, len(orphans), 9.5, MUTED, anchor="end"))
  for t in orphans:
    body.append(f'<rect x="{xs[t["id"]] + 0.6:.1f}" y="{yb - 9}" width="{pitch - 1.2:.1f}" height="10" rx="1.5" '
                f'fill="none" stroke="{COL[status_t[t["id"]]]}" stroke-width="1.2"/>')
  head = [text(M, 44, "FSR × TSR traceability matrix", 20, INK, "700"),
          text(M, 66, f"{len(fs)} FSRs (rows, by safety goal) × {len(ts)} TSRs (columns, by WP-S-02 block) · a cell is a "
               "parent link (WP-S-02 §12.1), coloured by the TSR's status", 12, MUTED),
          text(W - M, 44, "generated from trace/items", 11, MUTED, anchor="end"),
          text(M, TOP - 44, "FSR", 10, MUTED, "700"), text(M + 98, TOP - 44, "ASIL", 10, MUTED, "700"),
          text(L - 12, TOP - 44, "TSRs", 10, MUTED, "700", "end"), text(M, TOP - 18, "TSR status ▸", 9, MUTED)]
  height = yb + 110
  leg = legend(height - 60)
  leg.append(text(M, height - 20, "Row dot: the FSR's own status. “by ref.”: the FSR applies the TSRs of the FSRs it names. "
                  "Bottom row: TSRs whose parent is a goal or another requirement, not an FSR (outlined).", 9.5, MUTED))
  desc = "; ".join(f"{f['id']}: " + (", ".join(t["id"] for t in kids[f["id"]]) or "none") for f in fs)
  return svg("FSR × TSR traceability matrix", "Parent links. " + desc + ".", height, fg + head + body + leg)


# ---------------------------------------------------------------- pages

def list_page(kind: str, items: list[dict], link) -> str:
  title = "FSR list" if kind == "fsr" else "TSR list"
  src = ("[WP-C-04 §5](../../02-concept/WP-C-04-functional-safety-concept.md)" if kind == "fsr" else
         "[WP-S-02 §3–§10](../WP-S-02-technical-safety-requirements.md) and "
         "[WP-S-06](../WP-S-06-requirements-production-operation.md)")
  c = Counter(dd.classify(i) for i in items)
  out = ["<!-- Generated by assurance/03-system/requirements/requirements_view.py; do not edit by hand. -->", "",
         f"# {title}", "",
         f"All {len(items)} {'functional' if kind == 'fsr' else 'technical'} safety requirements of {src}, one line each. "
         "The work product holds the full text and is the source of truth; the ID links to its section.", "",
         "Status: " + " · ".join(f"{c[k]} {LABEL[k]}" for k in STATES) + ". The rule is that of WP-S-03 Figure 6-1; "
         "nothing is verified on hardware yet.", "",
         "| ID | Parents | ASIL | Allocated to | Status | Requirement (first sentence) |", "|---|---|---|---|---|---|"]
  for i in items:
    out.append(f"| [{i['id']}]({link(i)}) | {', '.join(i.get('parents', []))} | {asil(i.get('asil'))} | "
               f"{short_alloc(i.get('allocated_to', ''))} | {LABEL[dd.classify(i)]} | {first_sentence(i.get('text', ''), 160)} |")
  return "\n".join(out) + "\n"


def readme(fs: list[dict], ts: list[dict], goals: dict[str, dict], kids: dict[str, list[dict]]) -> str:
  gaps = [f["id"] for f in fs if not kids[f["id"]] and not by_reference(f)]
  refs = [f["id"] for f in fs if not kids[f["id"]] and by_reference(f)]
  orphans = [t["id"] for t in ts if not fsr_parents(t)]
  out = ["<!-- Generated by assurance/03-system/requirements/requirements_view.py; do not edit by hand. -->", "",
         "# Requirements at a glance", "",
         f"The {len(fs)} functional safety requirements of [WP-C-04](../../02-concept/WP-C-04-functional-safety-concept.md) "
         f"and the {len(ts)} technical safety requirements of [WP-S-02](../WP-S-02-technical-safety-requirements.md) and "
         "[WP-S-06](../WP-S-06-requirements-production-operation.md), drawn from their copies in "
         "[`trace/items`](../../trace/items/). The documents stay the source of truth.", "",
         f"![Status bars: {len(fs)} FSRs and {len(ts)} TSRs by implementation status](figures/fig-req-0-status.svg)", "",
         "## Coverage", ""]
  out.append(f"- FSRs without a TSR: {', '.join(gaps) if gaps else 'none'}.")
  if refs:
    out.append(f"- FSRs covered by reference to other FSRs' TSRs: {', '.join(refs)}.")
  out.append(f"- TSRs without an FSR parent: {len(orphans)} ({', '.join(orphans)}); they trace to a safety goal or "
             "to another requirement (WP-S-02 §10, WP-S-06).")
  out += ["", "## Requirement tree per safety goal", "",
          "Each goal with the FSRs that serve it and the TSRs that refine them. An FSR that serves several goals is "
          "drawn in each of their trees; a TSR with several parent FSRs is drawn under each, dashed.", ""]
  for sg in sorted(goals):
    g = goals[sg]
    out += [f"### {sg} · ASIL {asil(g.get('asil'))}", "",
            f"![{sg} requirement tree: the FSRs that serve it and their TSRs](figures/fig-req-1-{sg.lower()}-tree.svg)", ""]
  out += ["## FSR × TSR matrix", "",
          "Every parent link of WP-S-02 §12.1 as a cell: rows are FSRs by safety goal, columns are TSRs by WP-S-02 block.", "",
          "![FSR × TSR matrix: one row per FSR, one column per TSR, a cell for each parent link](figures/fig-req-2-matrix.svg)",
          "", "## Lists", "",
          f"- [FSR list](fsr-list.md): all {len(fs)} FSRs, one line each.",
          f"- [TSR list](tsr-list.md): all {len(ts)} TSRs, one line each.", "",
          "## One requirement, six routes", "",
          "[TSR-516, the SoC-independent siren](../../02-concept/fsc/requirement-routes.md), reached by six analysis "
          "methods (fault tree, FMEA, STPA, guide words, plant scenario, trace) and split into the six slots of a "
          "requirement's anatomy: TRIGGER, AGENT, MODAL, ACTION, OBJECT, CONSTRAINT.", "",
          "## Regenerating", "",
          "```bash", "python3 assurance/03-system/requirements/requirements_view.py", "```", "",
          "CI runs it with `--check` after `sync_requirements.py`, so the view follows every change to WP-C-04 §5, §9 and "
          "WP-S-02 §3–§12. The status rule and colours are those of WP-S-03 Figure 6-1."]
  return "\n".join(out) + "\n"


def build() -> dict[str, str]:
  fs, ts, goals = load()
  kids = children(fs, ts)
  s02, c04 = heading_anchors(WP_S02), heading_anchors(WP_C04)
  out = {"README.md": readme(fs, ts, goals, kids),
         "fsr-list.md": list_page("fsr", fs, lambda f: fsr_link(c04)),
         "tsr-list.md": list_page("tsr", ts, lambda t: tsr_link(t, s02)),
         "figures/fig-req-0-status.svg": status_figure(fs, ts),
         "figures/fig-req-2-matrix.svg": matrix_figure(fs, ts, goals, kids)}
  for sg in sorted(goals):
    out[f"figures/fig-req-1-{sg.lower()}-tree.svg"] = tree_figure(sg, goals[sg], fs, kids)
  return out


def main(argv: list[str]) -> int:
  outputs = build()
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    extra = sorted(p.name for p in (HERE / "figures").glob("*.svg") if f"figures/{p.name}" not in outputs)
    for n in stale:
      print(f"stale: {n}", file=sys.stderr)
    for n in extra:
      print(f"not generated (remove it): figures/{n}", file=sys.stderr)
    if stale or extra:
      print("run: python3 assurance/03-system/requirements/requirements_view.py", file=sys.stderr)
      return 1
    print(f"requirements_view: {len(outputs)} outputs current")
    return 0
  (HERE / "figures").mkdir(exist_ok=True)
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
