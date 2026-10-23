#!/usr/bin/env python3
"""Build the interactive 3D pages (Machine Skill, tool TL-56) from the committed results of the simulation track.

Each page is one self-contained HTML file: `page.html` with the vendored kit
(`.claude/skills/machine/kit/lab-kit.js`) pasted in, the page's own script (`<name>.js`) and the data it shows,
read here from committed, CI-checked results. The page interpolates and animates that data; it computes no physics
of its own, so a page cannot disagree with the evidence it illustrates. three.js 0.170 and the fonts come from their
CDNs when the page is opened.

    python3 build_pages.py           # write every page
    python3 build_pages.py --check   # CI: the pages are current and the vendored skill is unchanged

Synthetic (DSR-12), design aid, no evidence credit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
ROOT = SIM.parents[1]
SKILL = ROOT / ".claude" / "skills" / "machine"
RESULTS = SIM / "results"


def comma3x() -> dict:
  r = json.loads((RESULTS / "mcu-heat.json").read_text(encoding="utf-8"))
  p = yaml.safe_load((SIM / "thermal" / "params.yaml").read_text(encoding="utf-8"))
  grade = r["tsr509"]["grades"]["industrial"]
  return {"air": r["air"], "setups": {k: r["setups"][k] for k in ("as_built", "fan_stalled")},
          "rise": r["junction_rise_k"], "soc_limit": r["soc_limit"], "trip": grade["trip_at_most"],
          "tj_max": grade["tj_max"],
          "sources": {k: {"centre": p["sources"][k]["centre"], "size": p["sources"][k]["size"]} for k in ("soc", "mcu")}}


# name -> (title, description, stamp, data sources, data function)
PAGES = {
  "comma3x": ("comma 3X behind the windshield",
              "The comma 3X behind a sun-loaded windshield and the safety MCU next to its SoC, on LionDriver's device heat model.",
              "estimated inputs until T1",
              ["assurance/sim/results/mcu-heat.json", "assurance/sim/thermal/params.yaml"], comma3x),
}


def kit() -> str:
  return (SKILL / "kit" / "lab-kit.js").read_text(encoding="utf-8")


def build(name: str) -> str:
  title, desc, stamp, sources, data = PAGES[name]
  page = (HERE / "page.html").read_text(encoding="utf-8")
  script = (HERE / f"{name}.js").read_text(encoding="utf-8")
  subs = {"__TITLE__": title, "__DESCRIPTION__": desc, "__STAMP__": stamp, "__SOURCE__": f"assurance/sim/interactive/{name}.js",
          "__DATA_SOURCES__": ", ".join(sources), "__DATA__": json.dumps(data(), separators=(",", ":")),
          "__KIT__": re.sub(r"</script", r"<\\/script", kit(), flags=re.I), "__SCRIPT__": script}
  # one pass, so text inside the kit or the script is never substituted again
  return re.sub("|".join(map(re.escape, subs)), lambda m: subs[m.group(0)], page)


def vendored_errors() -> list[str]:
  errs = []
  for line in (SKILL / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
    digest, rel = line.split(maxsplit=1)
    f = SKILL / rel
    if not f.exists():
      errs.append(f"vendored skill: {rel} is missing")
    elif hashlib.sha256(f.read_bytes()).hexdigest() != digest:
      errs.append(f"vendored skill: {rel} differs from upstream e0bd066 (VENDORED.md)")
  return errs


def main(argv):
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("--check", action="store_true")
  a = ap.parse_args(argv[1:])
  errs = vendored_errors()
  for name in PAGES:
    html, out = build(name), HERE / f"{name}.html"
    if "SYNTHETIC (DSR-12)" not in html:
      errs.append(f"{name}: no synthetic stamp")
    if a.check:
      if not out.exists() or out.read_text(encoding="utf-8") != html:
        errs.append(f"{out.name} is stale: run build_pages.py")
    else:
      out.write_text(html, encoding="utf-8")
      print(f"wrote {out.name} ({len(html) // 1024} KB)")
  for e in errs:
    print("FAIL", e)
  if a.check:
    print("interactive pages:", "OK" if not errs else f"{len(errs)} problem(s)")
  return 1 if errs else 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
