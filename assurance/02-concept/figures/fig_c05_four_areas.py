#!/usr/bin/env python3
"""Draw WP-C-05 Figure 2-1: the ISO 21448 four-area chart, filled with what WP-C-05 and WP-C-06 state today.

The layout and wording are a drawing; every count in it is read from the records:

- the SOTIF hazards from the WP-C-05 §3 table (SH-07 is a placeholder row and is not counted);
- the functional insufficiencies and triggering conditions from the WP-C-06 §3 and §4 tables, with the last ID of each;
- the evaluation rows of WP-C-06 §5, by the outcome each row's Evaluation cell starts with (needs modification, needs
  validation, acceptable). Area 1 names the acceptable rows (TC-19, TC-21, TC-28); the build fails if that set changes,
  so the text is redrawn with it.

    python3 fig_c05_four_areas.py            # regenerate the SVG
    python3 fig_c05_four_areas.py --check    # fail if a table cannot be read or the SVG is stale

Standard library only. Output is deterministic. sotif_counts() is also used by the wiki page "SOTIF and ISO 26262"
(tools/wiki/sotif_animations.py).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from string import Template

HERE = Path(__file__).resolve().parent
CONCEPT = HERE.parent
C05 = CONCEPT / "WP-C-05-sotif-hazard-identification.md"
C06 = CONCEPT / "WP-C-06-sotif-insufficiencies-triggering-conditions.md"
OUT = "fig-c05-2-1-sotif-four-areas.svg"
ACCEPTABLE_DRAWN = ["TC-19", "TC-21", "TC-28"]   # Area 1 names these rows
WORDS = {3: "three", 4: "four", 5: "five", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen"}


class ParseError(Exception):
  pass


def section(text: str, start: str, end: str) -> str:
  i = text.find(start)
  if i < 0:
    raise ParseError(f"heading {start!r} not found")
  j = text.find(end, i + len(start))
  return text[i:j if j > 0 else None]


def ids(block: str, prefix: str) -> list[str]:
  return re.findall(rf"^\| ({prefix}-\d+) \|", block, re.M)


def sotif_counts(c05: Path = C05, c06: Path = C06) -> dict:
  """Counts of WP-C-05 §3 and WP-C-06 §3-§5, and the TCs of the rows evaluated acceptable."""
  t5, t6 = c05.read_text(encoding="utf-8"), c06.read_text(encoding="utf-8")
  sh = [r for r in re.findall(r"^\| (SH-\d+) \| (.*)$", section(t5, "## 3. SOTIF hazards", "\n## 4."), re.M)
        if not r[1].startswith("—")]
  fi = ids(section(t6, "## 3. Functional insufficiencies", "\n## 4."), "FI")
  tc = ids(section(t6, "## 4. Triggering conditions", "\n## 5."), "TC")
  ev = {"mod": 0, "val": 0, "acc": 0}
  acc_tcs: list[str] = []
  rows = [r for r in section(t6, "## 5. TC → FI → SH evaluation", "![Figure 5-1").splitlines() if r.startswith("| TC-")]
  for r in rows:
    cells = [c.strip() for c in r.strip("|").split("|")]
    outcome = cells[4]
    if outcome.startswith("Needs modification"):
      ev["mod"] += 1
    elif outcome.startswith("Needs validation"):
      ev["val"] += 1
    elif outcome.startswith("Acceptable"):
      ev["acc"] += 1
      acc_tcs += re.findall(r"TC-\d+", cells[0])
    else:
      raise ParseError(f"WP-C-06 §5: evaluation not recognised: {outcome[:40]!r}")
  if not (sh and fi and tc and rows):
    raise ParseError("a SOTIF table is empty or its heading moved")
  return {"sh": len(sh), "sh_last": sorted(sh)[-1][0], "fi": len(fi), "fi_last": fi[-1], "tc": len(tc), "tc_last": tc[-1], "rows": len(rows),
          **ev, "acc_tcs": acc_tcs}


def build() -> dict[str, str]:
  c = sotif_counts()
  if c["acc_tcs"] != ACCEPTABLE_DRAWN:
    raise ParseError(f"WP-C-06 §5: the acceptable rows are now {c['acc_tcs']}, Area 1 names {ACCEPTABLE_DRAWN}; redraw it")
  for k in ("sh", "acc"):
    if c[k] not in WORDS:
      raise ParseError(f"no word for {c[k]}; extend WORDS")
  return {OUT: Template(TEMPLATE).substitute(**{k: v for k, v in c.items() if k != "acc_tcs"},
                                              sh_word=WORDS[c["sh"]], acc_word=WORDS[c["acc"]])}


def main(argv: list[str]) -> int:
  check = "--check" in argv
  try:
    out = build()
  except ParseError as e:
    print(f"fig_c05_four_areas: {e}", file=sys.stderr)
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
    print("stale four-area chart; run fig_c05_four_areas.py: " + ", ".join(stale), file=sys.stderr)
    return 1
  print(f"fig_c05_four_areas: {len(out)} figure {'current' if check else 'written'}")
  return 0


TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="830" viewBox="0 0 1280 830" font-family="Inter, 'Segoe UI', Helvetica, Arial, sans-serif" role="img" aria-labelledby="t d">
  <title id="t">Figure 2-1. ISO 21448 scenario areas as covered by WP-C-05 and WP-C-06</title>
  <desc id="d">Two-by-two chart of known and unknown scenarios against hazardous and not hazardous behaviour. Area 2, known hazardous: the $sh_word SOTIF hazards SH-01 to SH-06 and SH-08 to $sh_last, all needing further treatment, with $fi functional insufficiencies and $tc triggering conditions in WP-C-06, whose $rows evaluation rows are $mod needs modification, $val needs validation and $acc acceptable with a condition. Area 1, known not hazardous: hazards rated S0 or C0 need no treatment, but none qualifies; $acc_word triggering-condition rows are acceptable only with a condition; acceptance criteria AC-01 to AC-06 are not yet met. Area 3, unknown hazardous: the driving model is a black box with unknown training data, with no out-of-distribution supervision; addressed by unknown-scenario exploration in WP-V-04 and acceptance criterion AC-07. Area 4, unknown not hazardous, is not addressed. Arrows show Area 3 to Area 2 by exploration and Area 2 to Area 1 by functional modification, ODD restriction, user information and validation.</desc>
  <defs>
    <marker id="aR" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#C2410C"/></marker>
    <marker id="aG" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#475569"/></marker>
    <pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="8" stroke="#E2E8F0" stroke-width="2"/></pattern>
    <style>
      .t{fill:#0F172A}.m{fill:#475569}.b{font-weight:700}.sb{font-weight:600}
      .ax{font-size:11px;font-weight:700;letter-spacing:.08em;fill:#475569}
    </style>
  </defs>

  <rect width="1280" height="830" fill="#FFFFFF"/>

  <!-- header -->
  <text x="40" y="44" class="t b" font-size="20">Figure 2-1 · SOTIF scenario areas for LD-SDA</text>
  <text x="40" y="66" class="m" font-size="12.5">ISO 21448:2022 four-area model, filled with what WP-C-05 and WP-C-06 state today · the goal is to move scenarios out of Areas 2 and 3 into Area 1</text>
  <text x="1240" y="44" class="m" font-size="11" text-anchor="end">WP-C-05 §2, §3, §5, §6</text>
  <text x="1240" y="62" class="m" font-size="11" text-anchor="end">WP-C-06 §1, §5</text>
  <line x1="40" y1="82" x2="1240" y2="82" stroke="#E2E8F0"/>

  <!-- axis headers -->
  <text x="400" y="114" class="ax" text-anchor="middle">KNOWN SCENARIOS</text>
  <text x="995" y="114" class="ax" text-anchor="middle">UNKNOWN SCENARIOS</text>
  <rect x="40" y="128" width="104" height="300" rx="8" fill="#F1F5F9"/>
  <text x="92" y="272" class="ax" text-anchor="middle">HAZARDOUS</text>
  <text x="92" y="290" class="m" font-size="10" text-anchor="middle">behaviour</text>
  <rect x="40" y="508" width="104" height="236" rx="8" fill="#F1F5F9"/>
  <text x="92" y="620" class="ax" text-anchor="middle">NOT</text>
  <text x="92" y="636" class="ax" text-anchor="middle">HAZARDOUS</text>

  <!-- ===== Area 2: known hazardous ===== -->
  <rect x="160" y="128" width="480" height="300" rx="12" fill="#FFF7ED" stroke="#C2410C" stroke-width="1.8"/>
  <rect x="176" y="142" width="64" height="22" rx="11" fill="#C2410C"/>
  <text x="208" y="157" fill="#FFFFFF" font-size="11" font-weight="700" text-anchor="middle">Area 2</text>
  <text x="252" y="158" class="t b" font-size="14">Known, hazardous</text>
  <text x="178" y="192" class="t sb" font-size="12">$sh SOTIF hazards (WP-C-05 §3)</text>
  <text x="178" y="209" class="m" font-size="11">SH-01…SH-06, SH-08…$sh_last · SH-07 not used</text>
  <text x="178" y="224" class="m" font-size="11">All $sh need further SOTIF treatment (§6; SH-09 only if</text>
  <text x="178" y="239" class="m" font-size="11">Experimental Mode is kept) · misuse raises C (§4, WP-C-08)</text>
  <text x="178" y="268" class="t sb" font-size="12">Causes analysed in WP-C-06</text>
  <text x="178" y="285" class="m" font-size="11">$fi functional insufficiencies FI-01…$fi_last (§3)</text>
  <text x="178" y="300" class="m" font-size="11">$tc triggering conditions TC-01…$tc_last (§4)</text>
  <text x="178" y="329" class="t sb" font-size="12">Evaluation of the $rows rows of WP-C-06 §5</text>
  <rect x="178" y="341" width="206" height="20" rx="10" fill="#D2553F"/>
  <text x="281" y="355" fill="#FFFFFF" font-size="10.5" font-weight="700" text-anchor="middle">$mod · needs modification</text>
  <rect x="392" y="341" width="186" height="20" rx="10" fill="#D97706"/>
  <text x="485" y="355" fill="#FFFFFF" font-size="10.5" font-weight="700" text-anchor="middle">$val · needs validation</text>
  <rect x="178" y="367" width="250" height="20" rx="10" fill="#FFFFFF" stroke="#64748B"/>
  <text x="303" y="381" fill="#475569" font-size="10.5" font-weight="700" text-anchor="middle">$acc · acceptable, with a condition</text>
  <text x="178" y="410" class="m" font-size="10.5">Acceptance criteria AC-01…AC-06 (§5.3); quantitative targets deferred to WP-V-02</text>

  <!-- ===== Area 3: unknown hazardous ===== -->
  <rect x="760" y="128" width="480" height="300" rx="12" fill="#FEF2F2" stroke="#D2553F" stroke-width="1.6" stroke-dasharray="7 4"/>
  <rect x="776" y="142" width="64" height="22" rx="11" fill="#D2553F"/>
  <text x="808" y="157" fill="#FFFFFF" font-size="11" font-weight="700" text-anchor="middle">Area 3</text>
  <text x="852" y="158" class="t b" font-size="14">Unknown, hazardous</text>
  <text x="778" y="192" class="t sb" font-size="12">Why this area is large for LD-SDA</text>
  <text x="778" y="209" class="m" font-size="11">The driving model is a black box: its training data and</text>
  <text x="778" y="224" class="m" font-size="11">training ODD are not available (WP-C-06 §1, GAP-22)</text>
  <text x="778" y="241" class="m" font-size="11">No uncertainty or out-of-distribution supervision of the</text>
  <text x="778" y="256" class="m" font-size="11">control action (FI-03; WP-C-06 §6)</text>
  <text x="778" y="285" class="t sb" font-size="12">How it is reduced</text>
  <text x="778" y="302" class="m" font-size="11">Unknown-scenario exploration in WP-V-04; the TC list is</text>
  <text x="778" y="317" class="m" font-size="11">reviewed against that plan (WP-C-06 OI-4)</text>
  <text x="778" y="334" class="m" font-size="11">AC-07: the final campaign finds no new hazardous</text>
  <text x="778" y="349" class="m" font-size="11">scenario class, or each one found is addressed</text>
  <text x="778" y="378" font-size="10.5" font-weight="700" fill="#D2553F">Size of this area is not estimated in WP-C-05 / WP-C-06</text>

  <!-- ===== Area 1: known not hazardous ===== -->
  <rect x="160" y="508" width="480" height="236" rx="12" fill="#F8FAFC" stroke="#64748B" stroke-width="1.6"/>
  <rect x="176" y="522" width="64" height="22" rx="11" fill="#475569"/>
  <text x="208" y="537" fill="#FFFFFF" font-size="11" font-weight="700" text-anchor="middle">Area 1</text>
  <text x="252" y="538" class="t b" font-size="14">Known, not hazardous</text>
  <text x="178" y="571" class="m" font-size="11">Hazards rated S0 or C0 need no further treatment (WP-C-05 §2</text>
  <text x="178" y="586" class="m" font-size="11">step 5) · none of SH-01…$sh_last is rated so (§6)</text>
  <text x="178" y="610" class="m" font-size="11">Acceptable only with a condition (WP-C-06 §5): TC-19 large</text>
  <text x="178" y="625" class="m" font-size="11">calibration errors · TC-21 after FM-03 · TC-28 with user</text>
  <text x="178" y="640" class="m" font-size="11">information, abort controllability still to be validated</text>
  <rect x="178" y="660" width="444" height="66" rx="8" fill="#FFFBEB" stroke="#D97706"/>
  <text x="192" y="682" font-size="11" font-weight="700" fill="#B45309">No scenario is in Area 1 by evidence yet</text>
  <text x="192" y="699" class="m" font-size="11">AC-01…AC-07 and the WP-V-02 validation targets are still</text>
  <text x="192" y="714" class="m" font-size="11">to be met; no row of WP-C-06 §5 is closed by evidence</text>

  <!-- ===== Area 4: unknown not hazardous ===== -->
  <rect x="760" y="508" width="480" height="236" rx="12" fill="url(#hatch)" stroke="#94A3B8" stroke-dasharray="4 3"/>
  <rect x="776" y="522" width="64" height="22" rx="11" fill="#94A3B8"/>
  <text x="808" y="537" fill="#FFFFFF" font-size="11" font-weight="700" text-anchor="middle">Area 4</text>
  <rect x="848" y="522" width="190" height="22" rx="4" fill="#FFFFFF" fill-opacity=".92"/>
  <text x="852" y="538" class="t b" font-size="14">Unknown, not hazardous</text>
  <rect x="776" y="598" width="448" height="56" rx="8" fill="#FFFFFF" fill-opacity=".94"/>
  <text x="1000" y="622" class="m" font-size="11.5" font-weight="600" text-anchor="middle">Not addressed in WP-C-05 or WP-C-06</text>
  <text x="1000" y="640" class="m" font-size="11" text-anchor="middle">no SOTIF activity targets this area</text>

  <!-- ===== transitions ===== -->
  <!-- Area 3 -> Area 2: discovery -->
  <path d="M758 278 H644" fill="none" stroke="#475569" stroke-width="2" marker-end="url(#aG)"/>
  <text x="700" y="256" class="t" font-size="10.5" font-weight="700" text-anchor="middle">explore</text>
  <text x="700" y="300" class="m" font-size="10" text-anchor="middle">WP-V-04,</text>
  <text x="700" y="313" class="m" font-size="10" text-anchor="middle">AC-07</text>
  <!-- Area 2 -> Area 1: treatment -->
  <path d="M400 430 V504" fill="none" stroke="#C2410C" stroke-width="2.4" marker-end="url(#aR)"/>
  <text x="414" y="454" class="t" font-size="10.5" font-weight="700">modify · restrict · inform · validate</text>
  <text x="414" y="469" class="m" font-size="10">WP-C-07 FM-01…FM-11 · ODD restriction (WP-C-02) · user</text>
  <text x="414" y="482" class="m" font-size="10">information (WP-O-03) · scenario tests WP-V-03 (AC-01…AC-06)</text>

  <!-- ===== legend ===== -->
  <line x1="40" y1="770" x2="1240" y2="770" stroke="#E2E8F0"/>
  <g transform="translate(40,796)" font-size="10.5">
    <line x1="0" y1="-4" x2="28" y2="-4" stroke="#C2410C" stroke-width="2.4"/><text x="36" y="0" class="t">Treatment of known hazards</text>
    <line x1="210" y1="-4" x2="238" y2="-4" stroke="#475569" stroke-width="2"/><text x="246" y="0" class="t">Discovery of unknown scenarios</text>
    <rect x="440" y="-12" width="28" height="16" rx="8" fill="#D2553F"/><text x="476" y="0" class="t">Needs modification</text>
    <rect x="590" y="-12" width="28" height="16" rx="8" fill="#D97706"/><text x="626" y="0" class="t">Needs validation</text>
    <rect x="730" y="-12" width="28" height="16" rx="8" fill="#FFFFFF" stroke="#64748B"/><text x="766" y="0" class="t">Acceptable, with a condition</text>
    <rect x="930" y="-12" width="28" height="16" rx="4" fill="url(#hatch)" stroke="#94A3B8" stroke-dasharray="4 3"/><text x="966" y="0" class="t">Not addressed</text>
    <text x="1200" y="0" class="m" text-anchor="end">Area sizes are not to scale</text>
  </g>
</svg>
"""

if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
