#!/usr/bin/env python3
"""Draw WP-S-04 Figure 5-3, where each timing requirement stands (fig-s04-5-3-verdicts.svg).

One tile per row of the WP-S-04 §5 comparison table: the fault class, its budget, the time in its Baseline column,
the latest verdict and the TSR. The rows are sorted into five verdicts:

  met            met by the code as derived, envelope side (nothing is measured)
  design         met by design in the reference build, not verified
  partly         part of the requirement met by design, or just over its budget
  not            not met
  verify         no derived time yet; to be measured
The Verdict cells are free text that grows a dated note per change, so the sorting is hand-listed in VERDICT, each
with a phrase quoted from the cell. The build fails when a row has no entry, an entry has no row, or the phrase is no
longer in the cell, so a changed verdict is re-sorted on purpose.

    python3 fig_s04_verdicts.py            # write the SVG
    python3 fig_s04_verdicts.py --check    # fail if §5 and VERDICT disagree or the SVG is stale

Standard library only. Output is deterministic.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fig_s03_defence_in_depth import (INK, MUTED, FAINT, LINE, AMBER, AMBER_BG, RED, RED_BG, BLUE, BLUE_BG,  # noqa: E402
                                      GREY_BG, text, rect, svg, header)
sys.path.insert(0, str(HERE.parents[1] / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)
sys.path.insert(0, str(HERE.parents[1] / "02-concept" / "hara"))
from hara_figures import wrap  # noqa: E402

SOURCE = HERE.parent / "WP-S-04-timing-ftti-budget.md"
OUT = "fig-s04-5-3-verdicts.svg"
W = 1280

# Fault class (first cell, without "(added …)") → (verdict, phrase quoted from the Verdict cell, what the tile says).
VERDICT = {
  "RX loss": ("design", "Met by design for the Toyota RX set", "≤ 0.2 s by design; 0x262 marginal at ≈ 0.21 s"),
  "RX stuck/inserted": ("not", "**Not met**", "rate, frozen-content and cross-checks not built"),
  "SoC heartbeat loss": ("partly", "SILENT ≤ 2 s not met", "revoke by design ≤ 0.31 s; SILENT still 4–5 s"),
  "SoC heartbeat loss → warning": ("design", "Met by design in all builds", "siren ≤ 0.56 s when authority was granted"),
  "Host/panda mismatch": ("design", "met by design in the reference build", "revoked ≤ 0.31 s (was 2–3 s)"),
  "SoC command stall": ("partly", "up to one 10 ms task period over the budget", "≤ 0.06 s against 0.05 s: one task period over"),
  "MCU hang": ("design", "Met by design if the LSI tolerance holds", "≈ 90 ms watchdog, if the clock tolerance holds"),
  "Relay stuck released": ("not", "**Not met**", "no relay read-back"),
  "Brake / cancel": ("met", "Met (envelope side)", "25–30 ms; EPS and PCM response to verify"),
  "Steering override": ("not", "**Not met**", "no driver-torque monitor in the envelope"),
  "Stale SoC inputs": ("not", "**Not met**", "3–3.5 s of actuation on a failed input"),
  "Diagnostic masking": ("not", "**Not met**", "up to 5 s blind while the big model loads"),
  "Cruise mismatch": ("not", "**Not met**", "6 s, no reaction"),
  "`sendcan` age": ("not", "**Not met**", "1 s against 20 ms"),
  "Take-over request": ("verify", "To verify", "alerts immediate; latency not measured"),
  "Cruise active with main off": ("design", "Met by design (reference build)", "refused at once; revoked after 150 ms"),
  "SoC TX rate above budget": ("design", "Met by design (reference build)", "revoked ≤ 0.1 s after the first rejected frame"),
  "EPS fault": ("design", "warning latency within the 1 s budget by design", "torque refused at once; siren ≤ 0.96 s"),
  "Full SoC stall → warning": ("design", "**Met, code-derived**", "siren ≤ 0.31 s after the last command frame"),
}
STATUS = [("met", "met (code-derived, envelope side)", BLUE, BLUE_BG),
          ("design", "met by design in the reference build, not verified", BLUE, "#FFFFFF"),
          ("partly", "partly, or just over the budget", AMBER, AMBER_BG),
          ("not", "not met", RED, RED_BG),
          ("verify", "no derived time yet", MUTED, GREY_BG)]


class VerdictError(ValueError):
  pass


def _plain(s: str) -> str:
  s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
  return s.replace("`", "").strip()


def parse(md: str) -> list[dict]:
  m = re.search(r"^## 5\. .*?$(.*?)(?=^!\[Figure 5-1)", md, re.M | re.S)
  if not m:
    raise VerdictError("WP-S-04 §5 table not found")
  rows, seen = [], set()
  for ln in m.group(1).splitlines():
    if not ln.startswith("| ") or ln.startswith("| Fault class") or ln.startswith("|---"):
      continue
    c = [x.strip() for x in ln.strip()[1:-1].split("|")]
    if len(c) != 6:
      raise VerdictError(f"{c[0]}: {len(c)} cells, expected 6")
    key = re.sub(r"\s*\(added [^)]*\)", "", c[0]).strip()
    if key not in VERDICT:
      raise VerdictError(f"§5 row {key!r} has no entry in VERDICT; sort it")
    verdict, phrase, says = VERDICT[key]
    if phrase not in c[3]:
      raise VerdictError(f"{key}: phrase {phrase!r} is no longer in its Verdict cell; re-sort the row")
    seen.add(key)
    rows.append({"name": _plain(key), "budget": _plain(c[1]), "baseline": _plain(c[2]), "verdict": verdict,
                 "says": says, "tsr": _plain(c[5])})
  missing = set(VERDICT) - seen
  if missing:
    raise VerdictError(f"VERDICT entries without a §5 row: {sorted(missing)}")
  return rows


def figure(rows: list[dict]) -> str:
  counts = {k: sum(1 for r in rows if r["verdict"] == k) for k, *_ in STATUS}
  out = header(W, "5-3", "Where each timing requirement stands",
               f"The {len(rows)} fault classes of §5 by verdict, each with its budget, the time in its Baseline column "
               f"and the latest status: {counts['not']} not met, {counts['partly']} partly, "
               f"{counts['met'] + counts['design']} met in code or by design, none measured", "WP-S-04 §5")
  COLS, GAP, TH = 3, 12, 96
  tw = (W - 80 - (COLS - 1) * GAP) / COLS
  y = 104
  for k, title, col, bg in STATUS:
    mine = [r for r in rows if r["verdict"] == k]
    if not mine:
      continue
    nrow = (len(mine) + COLS - 1) // COLS
    bh = 40 + nrow * (TH + GAP)
    out.append(rect(30, y, W - 60, bh, fill="#F8FAFC", stroke=LINE, sw=1, rx=12))
    out.append(text(46, y + 25, f"{title[0].upper() + title[1:]} ({len(mine)})", size=14,
                    fill=col if k != "verify" else INK, weight=700))
    for i, r in enumerate(mine):
      x = 40 + (i % COLS) * (tw + GAP)
      ty = y + 36 + (i // COLS) * (TH + GAP)
      out.append(rect(x, ty, tw, TH, fill=bg, stroke=col, sw=1.4, rx=8, dash="5 3" if k == "verify" else ""))
      out.append(text(x + 12, ty + 20, r["name"], size=12, weight=700))
      tsr = r["tsr"] if r["tsr"] not in ("—", "") else ""
      if tsr:
        out.append(text(x + tw - 10, ty + 20, "TSR " + tsr.replace("TSR-", ""), size=9.5, fill=MUTED, anchor="end"))
      yy = ty + 38
      for ln in wrap(r["says"], tw - 24, 10.5)[:2]:
        out.append(text(x + 12, yy, ln, size=10.5, fill=col if k in ("not", "partly") else INK, weight=600))
        yy += 14
      foot = f"budget {r['budget']} · baseline: {r['baseline']}"
      fl = wrap(foot, tw - 24, 9.5)
      for j, ln in enumerate(fl[:2]):
        out.append(text(x + 12, ty + TH - 22 + j * 12 + (12 if len(fl) == 1 else 0),
                        ln + ("…" if j == 1 and len(fl) > 2 else ""), size=9.5, fill=MUTED))
    y += bh + 14
  y += 4
  out.append(text(40, y, "Nothing in this figure is measured: “met” is derived from the code, “by design” is implemented in "
                  "the reference build and simulated at most. The measurements are §6 (M-01…M-12).", size=11, fill=MUTED))
  y += 18
  out.append(text(40, y, "Generated by fig_s04_verdicts.py from WP-S-04 §5; each row's verdict is listed in the script with a "
                  "phrase from its cell, and CI fails when the cell changes.", size=11, fill=MUTED))
  extra, y = terms.svg_footer(out, 40, y + 22, W - 80)
  out += extra
  h = int(y + 12)
  desc = (f"{len(rows)} timing requirements of WP-S-04 §5. " +
          " ".join(f"{r['name']}: {dict((k, t) for k, t, *_ in STATUS)[r['verdict']]}; {r['says']}." for r in rows))
  return svg(W, h, "Figure 5-3. Where each timing requirement stands (WP-S-04 §5)", desc, out)


def build() -> dict[str, str]:
  return {OUT: figure(parse(SOURCE.read_text(encoding="utf-8")))}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except VerdictError as e:
    print(f"fig_s04_verdicts: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"assurance/03-system/figures/{n} is stale; run fig_s04_verdicts.py", file=sys.stderr)
    if not stale:
      print(f"fig_s04_verdicts: {len(outputs)} figure current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote assurance/03-system/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
