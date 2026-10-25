#!/usr/bin/env python3
"""Draw WP-S-03 Figure 7-1, freedom from interference and independence (fig-s03-7-1-ffi.svg).

One row per claim of the WP-S-03 §7 table: what the QM side could do to the ASIL C envelope (FFI-n), the causes the two
share (DFA-n) and the fallback independence claim (IND-1). Each row has the interference path, the mechanisms required
to stop it and its status.

Status, from the Baseline cell: when it carries dated updates ("2026-10-12: ...") the text after the last date counts,
otherwise the whole cell; its first word gives the status:
  Not met            not met        Partial   partly
  Open, Unknown      not analysed   —         not present (IND-1, a fallback)
Any other first word fails the build, so a new status is classified on purpose.

    python3 fig_s03_ffi.py            # write the SVG
    python3 fig_s03_ffi.py --check    # fail if §7 cannot be read or the SVG is stale

Standard library only. Output is deterministic.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fig_s03_defence_in_depth import (INK, MUTED, FAINT, LINE, SAFETY, SAFETY_BG, AMBER, AMBER_BG,  # noqa: E402
                                      RED, RED_BG, GREY_BG, text, rect, svg, header, el, fmt)
sys.path.insert(0, str(HERE.parents[1] / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)
sys.path.insert(0, str(HERE.parents[1] / "02-concept" / "hara"))
from hara_figures import wrap  # noqa: E402

SOURCE = HERE.parent / "WP-S-03-technical-safety-concept-architecture.md"
OUT = "fig-s03-7-1-ffi.svg"
W = 1280

STATUS = {"not": ("not met", RED, RED_BG), "partial": ("partly", AMBER, AMBER_BG),
          "open": ("not analysed", MUTED, GREY_BG), "absent": ("not present", FAINT, "#FFFFFF")}
GROUPS = [("FFI", "What the QM side could do to the envelope", "the SoC (E-01) and its models (E-02) against the panda MCU (E-03, E-04a)"),
          ("DFA", "What the two share", "common causes that could defeat both at once"),
          ("IND", "A second, independent limiter", "the fallback of FSC §4.3, if the envelope alone is not enough")]


class FfiError(ValueError):
  pass


def _plain(s: str) -> str:
  s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
  return s.replace("**", "").replace("`", "").strip()


def classify(baseline: str) -> tuple[str, str]:
  """(status, the text it was read from)."""
  s = _plain(baseline)
  parts = re.split(r"\b20\d\d-\d\d-\d\d:\s*", s)
  latest = parts[-1].strip()
  for prefix, k in (("Not met", "not"), ("Partial", "partial"), ("Open", "open"), ("Unknown", "open"), ("—", "absent")):
    if latest.startswith(prefix):
      return k, latest
  raise FfiError(f"cannot classify baseline {latest[:60]!r}; extend classify()")


def parse(md: str) -> list[dict]:
  m = re.search(r"^## 7\. .*?$(.*?)(?=^## \d+\. )", md, re.M | re.S)
  if not m:
    raise FfiError("WP-S-03 §7 not found")
  rows = []
  for ln in m.group(1).splitlines():
    mm = re.match(r"^\| ((?:FFI|DFA|IND)-\d+) \|", ln)
    if not mm:
      continue
    c = [x.strip() for x in ln.strip()[1:-1].split("|")]
    if len(c) != 5:
      raise FfiError(f"{c[0]}: {len(c)} cells, expected 5")
    status, latest = classify(c[3])
    rows.append({"id": c[0], "path": _plain(c[1]), "mech": _plain(c[2]), "status": status, "latest": latest,
                 "group": c[0].split("-")[0]})
  if not rows:
    raise FfiError("§7 has no FFI/DFA/IND rows")
  return rows


def figure(rows: list[dict]) -> str:
  out = header(W, "7-1", "Freedom from interference and independence",
               "Each way the QM side could interfere with the ASIL C envelope, each cause they share, and what is "
               "required to stop it, with its status at the reference build", "WP-S-03 §7")
  RH, y = 58, 104
  for g, title, sub in GROUPS:
    mine = [r for r in rows if r["group"] == g]
    if not mine:
      continue
    bh = 44 + len(mine) * RH
    out.append(rect(30, y, W - 60, bh, fill="#F8FAFC", stroke=LINE, sw=1, rx=12))
    out.append(text(46, y + 25, title, size=14, weight=700))
    out.append(text(46 + len(title) * 8.2 + 12, y + 25, sub, size=11, fill=MUTED))
    for i, r in enumerate(mine):
      ry = y + 38 + i * RH
      lab, col, bg = STATUS[r["status"]]
      # the path, on the QM side
      out.append(rect(46, ry, 404, RH - 10, fill="#FFFFFF", stroke=FAINT, sw=1.2, rx=8))
      out.append(text(58, ry + 18, r["id"], size=11.5, weight=700))
      for j, ln in enumerate(wrap(r["path"], 320, 10.5)[:2]):
        out.append(text(116, ry + 18 + j * 14, ln, size=10.5))
      # the barrier: required mechanisms, drawn on the envelope's side
      out.append(el("line", None, x1=450, y1=fmt(ry + (RH - 10) / 2), x2=488, y2=fmt(ry + (RH - 10) / 2),
                    stroke=MUTED, stroke_width=1.4, marker_end="url(#muted)"))
      out.append(rect(490, ry, 330, RH - 10, fill=SAFETY_BG, stroke=SAFETY, sw=1.2, rx=8,
                      dash="5 3" if r["status"] == "absent" else ""))
      out.append(text(502, ry + 16, "required", size=9.5, fill=SAFETY, weight=700))
      for j, ln in enumerate(wrap(r["mech"], 306, 10.5)[:2]):
        out.append(text(502, ry + 30 + j * 13, ln, size=10.5))
      # status
      cw = len(lab) * 6.6 + 18
      out.append(rect(838, ry + 6, cw, 20, fill=bg, stroke=col, sw=1.2, rx=10,
                      dash="4 3" if r["status"] in ("open", "absent") else ""))
      out.append(text(838 + cw / 2, ry + 20, lab, size=10.5, fill=col, weight=700, anchor="middle"))
      rest = re.sub(r"^(Not met|Partial|Open|Unknown|—)\s*", "", r["latest"]).strip()
      rest = rest[1:-1] if rest.startswith("(") and rest.endswith(")") else rest
      note = wrap(rest, W - 60 - 838 - cw - 24, 10) if rest else []
      for j, ln in enumerate(note[:3]):
        out.append(text(838 + cw + 10, ry + 14 + j * 13, ln + ("…" if j == 2 and len(note) > 3 else ""), size=10, fill=MUTED))
    y += bh + 14
  y += 6
  counts = {k: sum(1 for r in rows if r["status"] == k) for k in STATUS}
  lx = 40
  for k, (lab, col, bg) in STATUS.items():
    s = f"{lab} ({counts[k]})"
    out.append(rect(lx, y - 12, 30, 16, fill=bg, stroke=col, sw=1.2, rx=8, dash="4 3" if k in ("open", "absent") else ""))
    out.append(text(lx + 38, y, s, size=11))
    lx += 38 + len(s) * 6.3 + 22
  out.append(text(lx, y, "Nothing here is verified. The analyses are WP-A-02 (interference) and WP-A-03 (dependent failures).",
                  size=11, fill=MUTED))
  y += 18
  out.append(text(40, y, "Status is the latest dated note of the §7 Baseline cell (the reference build where one is given). "
                  "Generated by fig_s03_ffi.py from WP-S-03 §7.", size=11, fill=MUTED))
  extra, y = terms.svg_footer(out, 40, y + 22, W - 80)
  out += extra
  h = int(y + 12)
  desc = "WP-S-03 §7 claims. " + " ".join(f"{r['id']}: {r['path']}; required {r['mech']} ({STATUS[r['status']][0]})."
                                          for r in rows)
  return svg(W, h, "Figure 7-1. Freedom from interference and independence (WP-S-03 §7)", desc, out)


def build() -> dict[str, str]:
  return {OUT: figure(parse(SOURCE.read_text(encoding="utf-8")))}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except FfiError as e:
    print(f"fig_s03_ffi: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"assurance/03-system/figures/{n} is stale; run fig_s03_ffi.py", file=sys.stderr)
    if not stale:
      print(f"fig_s03_ffi: {len(outputs)} figure current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote assurance/03-system/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
