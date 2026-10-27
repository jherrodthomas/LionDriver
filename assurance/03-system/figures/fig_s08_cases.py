#!/usr/bin/env python3
"""Draw WP-S-08 Figure 6-1, the integration test cases, where each runs and what is expected (fig-s08-6-1-cases.svg).

One row per test case VS-SI-nn of WP-S-08 §6, in its §6.x group: the integration steps it runs at (I-1 bench with a
test host, I-2 with openpilot, I-3 closed loop with a plant model, I-4 stationary in the car), read from the Step
column, and the result the code is expected to give, read from the Expected-baseline column:

  meets     the code is expected to meet the pass criteria
  design    meets by design in the reference build, not verified on hardware
  partly    part of the criteria expected to pass, part a known gap or unknown
  gap       expected to fail on a known gap (GAP-nn)
  open      cannot be judged: the code changed since, or references are missing
The Expected-baseline cells are free text, so each case is hand-listed in EXPECTED with a phrase quoted from its cell
and a short reading. The build fails when a case has no entry, an entry has no case, or the phrase leaves its cell.
No case has been executed; the figure shows the plan and the expectation, not results.

    python3 fig_s08_cases.py            # write the SVG
    python3 fig_s08_cases.py --check    # fail if §6 and EXPECTED disagree or the SVG is stale

Standard library only. Output is deterministic.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fig_s03_defence_in_depth import (INK, MUTED, FAINT, LINE, AMBER, AMBER_BG, RED, RED_BG, BLUE, BLUE_BG,  # noqa: E402
                                      GREY_BG, SAFETY, text, rect, svg, header, el, line)
sys.path.insert(0, str(HERE.parents[1] / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)
sys.path.insert(0, str(HERE.parents[1] / "02-concept" / "hara"))
from hara_figures import wrap  # noqa: E402

SOURCE = HERE.parent / "WP-S-08-system-integration-test.md"
OUT = "fig-s08-6-1-cases.svg"
W = 1280
STEPS = [("I-1", "bench, test host"), ("I-2", "+ openpilot"), ("I-3", "+ plant model"), ("I-4", "in the car")]

# Case → (expected result, phrase quoted from its Expected-baseline cell, short reading).
EXPECTED = {
  "VS-SI-01": ("meets", "Meets (", "authority only on the cruise edge"),
  "VS-SI-02": ("meets", "Meets for (1)–(3) logic", "logic meets; timing to be measured"),
  "VS-SI-03": ("gap", "Fail (known GAP-02)", "no driver-torque check in the envelope"),
  "VS-SI-04": ("meets", "Meets (", "gas blocks longitudinal; restricted commands ignored"),
  "VS-SI-05": ("partly", "SILENT 5 s still **Fail (known GAP-06)**", "revoke at 0.3 s; SILENT still after 5 s"),
  "VS-SI-06": ("gap", "Fail (known GAP-06)", "mismatch takes 3 ticks at 1 Hz"),
  "VS-SI-07": ("design", "Reference build (`LIONDRIVER_REFERENCE=1`): Meets by design", "mode lock in the reference build"),
  "VS-SI-08": ("design", "Reference build: Meets by design", "command gating in the reference build"),
  "VS-SI-09": ("partly", "8-bit XOR residual error not quantified", "no corrupted frame expected; XOR not quantified"),
  "VS-SI-10": ("gap", "Fail (known GAP-10)", "no sequence counter"),
  "VS-SI-11": ("partly", "interrupt-rate fault reaction absent", "rate limit by design; no interrupt-rate reaction"),
  "VS-SI-12": ("design", "5 nominal periods, ≤ 0.162 s, implemented", "timeout ≤ 0.162 s, not on hardware"),
  "VS-SI-13": ("gap", "Fail (known GAP-01)", "only silence is detected"),
  "VS-SI-14": ("meets", "Meets for checksummed messages", "checksum and wheel fault bits revoke"),
  "VS-SI-15": ("partly", "TX violation alone does not revoke", "limits hold; a violation does not revoke"),
  "VS-SI-16": ("partly", "**Fail (known GAP-04)** for jerk", "bounds hold; jerk not limited"),
  "VS-SI-17": ("partly", "NaN **Fail (known GAP-19)**", "latch meets; NaN clamped to 0"),
  "VS-SI-18": ("partly", "power-loss state unknown (AOU-13)", "released by mode; power-loss state unknown"),
  "VS-SI-19": ("gap", "Fail (known GAP-12)", "relay fault found after 1–2 s"),
  "VS-SI-20": ("meets", "Expected to meet in all modes", "static block list"),
  "VS-SI-21": ("design", "reference build also blocks `0x411`", "all PCS IDs blocked in the reference build"),
  "VS-SI-22": ("gap", "Fail (known GAP-16)", "up to 3.5 s on stale inputs"),
  "VS-SI-23": ("partly", "revocation at 0.3 s and siren", "0.3 s where the heartbeat stops; 3–5 s otherwise"),
  "VS-SI-24": ("open", "test not re-run", "code changed since the run (1 s prompt)"),
  "VS-SI-25": ("meets", "Expected to meet", "restarts in SILENT; relay reset state unconfirmed"),
  "VS-SI-26": ("open", "No fork-owned references (GAP-30)", "needs LionDriver's own drive logs"),
  "VS-SI-27": ("open", "Not run.", "host reaction to envelope reports"),
}
STATUS = {"meets": ("expected to meet", BLUE, BLUE_BG, ""), "design": ("by design, reference build", BLUE, "#FFFFFF", ""),
          "partly": ("partly", AMBER, AMBER_BG, ""), "gap": ("known gap", RED, RED_BG, ""),
          "open": ("cannot judge yet", MUTED, GREY_BG, "4 3")}


class CaseError(ValueError):
  pass


def _plain(s: str) -> str:
  s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
  return s.replace("`", "").replace("**", "").strip()


def parse(md: str) -> list[tuple[str, list[dict]]]:
  m = re.search(r"^## 6\. .*?$(.*?)(?=^## 7\. )", md, re.M | re.S)
  if not m:
    raise CaseError("WP-S-08 §6 not found")
  groups, seen = [], set()
  for block in re.split(r"^### ", m.group(1), flags=re.M)[1:]:
    title = re.sub(r"^6\.\d+ ", "", block.splitlines()[0].strip())
    cases = []
    for ln in block.splitlines():
      if not ln.startswith("| VS-SI-"):
        continue
      c = [x.strip() for x in ln.strip()[1:-1].split("|")]
      if len(c) != 8:
        raise CaseError(f"{c[0]}: {len(c)} cells, expected 8")
      if c[0] not in EXPECTED:
        raise CaseError(f"{c[0]} has no entry in EXPECTED; sort it")
      st, phrase, says = EXPECTED[c[0]]
      if phrase not in c[7]:
        raise CaseError(f"{c[0]}: phrase {phrase!r} is no longer in its Expected-baseline cell; re-sort it")
      steps = [s.strip() for s in c[3].split(",")]
      bad = [s for s in steps if s not in dict(STEPS)]
      if bad:
        raise CaseError(f"{c[0]}: unknown step {bad}")
      seen.add(c[0])
      cases.append({"id": c[0], "title": _plain(c[1]), "steps": steps, "status": st, "says": says})
    groups.append((title, cases))
  extra = set(EXPECTED) - seen
  if extra:
    raise CaseError(f"EXPECTED entries without a case in §6: {sorted(extra)}")
  return groups


def figure(groups) -> str:
  allc = [c for _, cs in groups for c in cs]
  counts = {k: sum(1 for c in allc if c["status"] == k) for k in STATUS}
  out = header(W, "6-1", "The integration test cases, where each runs and what is expected",
               f"The {len(allc)} cases of §6 by integration step, with the result the code is expected to give: "
               f"{counts['meets'] + counts['design']} meet, {counts['partly']} partly, {counts['gap']} known gap, "
               f"{counts['open']} cannot be judged; none executed", "WP-S-08 §3.1, §6")
  X_STEP = [560, 625, 690, 755]
  X_RES = 815
  y = 104
  # column heads
  for (s, d), x in zip(STEPS, X_STEP):
    out.append(text(x, y + 12, s, size=12, weight=700, anchor="middle"))
    out.append(text(x, y + 27, d, size=9, fill=MUTED, anchor="middle"))
  out.append(text(X_RES, y + 12, "Expected at the baseline", size=12, weight=700))
  out.append(text(X_RES, y + 27, "from the code; nothing measured", size=9, fill=MUTED))
  y += 40
  RH = 26
  for title, cases in groups:
    out.append(rect(30, y, W - 60, 26 + len(cases) * RH + 6, fill="#F8FAFC", stroke=LINE, sw=1, rx=10))
    out.append(text(44, y + 18, title, size=12.5, weight=700))
    y += 26
    for c in cases:
      cy = y + RH / 2
      out.append(line(40, y + RH, W - 40, y + RH, stroke="#EEF2F6", sw=1))
      out.append(text(44, cy + 4, c["id"], size=11, weight=700))
      t = wrap(c["title"], 400, 11)
      out.append(text(118, cy + 4, t[0] + ("…" if len(t) > 1 else ""), size=11))
      for (s, _), x in zip(STEPS, X_STEP):
        if s in c["steps"]:
          out.append(el("circle", None, cx=x, cy=f"{cy:.1f}", r=6, fill=SAFETY))
        else:
          out.append(el("circle", None, cx=x, cy=f"{cy:.1f}", r=2.5, fill=FAINT))
      lab, col, bg, dash = STATUS[c["status"]]
      cw = len(lab) * 6.0 + 16
      out.append(rect(X_RES, cy - 9, cw, 18, fill=bg, stroke=col, sw=1.2, rx=9, dash=dash))
      out.append(text(X_RES + cw / 2, cy + 4, lab, size=9.5, fill=col, weight=700, anchor="middle"))
      out.append(text(X_RES + cw + 8, cy + 4, wrap(c["says"], W - 50 - X_RES - cw - 8, 10)[0], size=10, fill=MUTED))
      y += RH
    y += 14
  y += 14
  lx = 40
  for k, (lab, col, bg, dash) in STATUS.items():
    s = f"{lab} ({counts[k]})"
    out.append(rect(lx, y - 12, 30, 16, fill=bg, stroke=col, sw=1.2, rx=8, dash=dash))
    out.append(text(lx + 38, y, s, size=11))
    lx += 38 + len(s) * 6.3 + 22
  out.append(el("circle", None, cx=lx + 6, cy=y - 4, r=6, fill=SAFETY))
  out.append(text(lx + 18, y, "runs at this step", size=11))
  y += 18
  out.append(text(40, y, "No case has been executed: the HIL bench (D-04) and LionDriver's own drive logs do not exist yet. "
                  "A case WP-W-08 already covers at I-1 is taken from its report.", size=11, fill=MUTED))
  y += 18
  out.append(text(40, y, "Generated by fig_s08_cases.py from WP-S-08 §6; each expected result is listed in the script with a "
                  "phrase from its cell, and CI fails when the cell changes.", size=11, fill=MUTED))
  extra, y = terms.svg_footer(out, 40, y + 22, W - 80)
  out += extra
  h = int(y + 12)
  desc = (f"{len(allc)} integration test cases of WP-S-08 §6. " +
          " ".join(f"{c['id']} {c['title']}: steps {', '.join(c['steps'])}; {STATUS[c['status']][0]}, {c['says']}."
                   for c in allc))
  return svg(W, h, "Figure 6-1. The integration test cases (WP-S-08 §6)", desc, out)


def build() -> dict[str, str]:
  return {OUT: figure(parse(SOURCE.read_text(encoding="utf-8")))}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except CaseError as e:
    print(f"fig_s08_cases: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"assurance/03-system/figures/{n} is stale; run fig_s08_cases.py", file=sys.stderr)
    if not stale:
      print(f"fig_s08_cases: {len(outputs)} figure current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote assurance/03-system/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
