#!/usr/bin/env python3
"""Score the register-file flip campaigns (ecc_base_*.json, ecc_ecc_*.json) and the two synthesis areas."""
import json
import re
import sys


def area(stat):
  return float(re.search(r"Chip area for module '\\picorv32': ([\d.]+)", open(stat).read()).group(1))


def classify(r):
  return "flagged" if r["err"] else "wrong" if r["visible"] else "corrected" if r["corr"] else "none"


out = {}
for which in ("base", "ecc"):
  rs = [r for p in (0, 1) for r in json.load(open(f"ecc_{which}_{p}.json"))]
  for kind in ("single", "double"):
    sel = [classify(r) for r in rs if r["kind"] == kind]
    out[f"{which}_{kind}"] = {k: sel.count(k) for k in ("wrong", "flagged", "corrected", "none")} | {"n": len(sel)}
out["area_um2"] = {"base": area(sys.argv[1]), "ecc": area(sys.argv[2])}
json.dump(out, open("ecc_summary.json", "w"), indent=1)
print(json.dumps(out))
