#!/usr/bin/env python3
"""Score the self-test fault campaign (faults.json) per sub-part.

Diagnostic coverage for permanent faults = stuck-at faults the self-test made visible / all stuck-at faults (conservative).
A second figure leaves out the faults that provably can never matter in this core, by rule, not by hand:
  - x0's storage (cpuregs[0]): x0 is never written and reads of x0 are forced to zero
  - the rd, rs1 and rs2 fields (bits 7-11, 15-24) of pcpi_insn: the internal multiplier and divider decode only the
    opcode, funct3 and funct7 fields, and no external coprocessor is attached
Faults the test cannot reach in time (counter high bits) and outputs software cannot see (eoi) stay in the denominator.
usage: analyze.py netlist.json subparts.json subparts-cells.json faults.json coverage.json
"""
import json
import sys
from collections import defaultdict

netlist, subparts, cellmap, faults_p, out = sys.argv[1:6]
mod = json.load(open(netlist))["modules"]["picorv32"]
b2n = {}
for n, v in sorted(mod["netnames"].items(), key=lambda kv: kv[1].get("hide_name", 0)):
  for i, b in enumerate(v["bits"]):
    if isinstance(b, int):
      b2n.setdefault(b, (n, i))


def safe(cell):
  c = mod["cells"][cell]
  if "df" not in c["type"]:
    return None
  n, i = b2n[c["connections"]["Q"][0]]
  if n == "cpuregs[0]":
    return "x0 storage"
  if n == "pcpi_insn" and (7 <= i <= 11 or 15 <= i <= 24):
    return "unused coprocessor-interface fields"
  return None


F = json.load(open(faults_p))
CG = json.load(open(cellmap))
order = [s["sub_part"] for s in json.load(open(subparts))["sub_parts"]]
acc = defaultdict(lambda: defaultdict(float))
safe_n = defaultdict(int)
for f in F["faults"]:
  gs = CG[f["cell"]]
  cls = "perm" if f["kind"] in ("sa0", "sa1") else "seu"
  if cls == "perm":
    why = safe(f["cell"])
    if why:
      safe_n[why] += 1
  for g in gs:
    acc[g][cls + "_n"] += 1 / len(gs)
    acc[g][cls + "_d"] += f["detected"] / len(gs)
rows, tot = [], defaultdict(float)
for g in order:
  a = acc[g]
  for k, v in a.items():
    tot[k] += v
  rows.append({"sub_part": g, "perm_faults": round(a["perm_n"]), "perm_detected": round(a["perm_d"]),
               "perm_dc": round(a["perm_d"] / a["perm_n"], 4), "seu_faults": round(a["seu_n"]), "seu_detected": round(a["seu_d"]),
               "seu_dc": round(a["seu_d"] / a["seu_n"], 4) if a["seu_n"] else None})
n_safe = sum(safe_n.values())
res = {"cycles": F["cycles"], "seconds": F["seconds"], "faults": len(F["faults"]),
       "perm_faults": round(tot["perm_n"]), "perm_detected": round(tot["perm_d"]), "perm_dc": round(tot["perm_d"] / tot["perm_n"], 4),
       "safe_faults": dict(sorted(safe_n.items())), "perm_dc_excl_safe": round(tot["perm_d"] / (tot["perm_n"] - n_safe), 4),
       "seu_faults": round(tot["seu_n"]), "seu_detected": round(tot["seu_d"]), "seu_dc": round(tot["seu_d"] / tot["seu_n"], 4),
       "sub_parts": rows}
json.dump(res, open(out, "w"), indent=1)
print(f"{'sub-part':16}{'stuck-at':>10}{'DC':>8}{'SEU':>7}{'DC':>8}")
for r in rows:
  s = f"{r['seu_dc'] * 100:7.1f}%" if r["seu_dc"] is not None else "      -"
  print(f"{r['sub_part']:16}{r['perm_faults']:>10}{r['perm_dc'] * 100:7.1f}%{r['seu_faults']:>7}{s}")
print(f"whole core: {res['perm_dc'] * 100:.1f} % ({res['perm_dc_excl_safe'] * 100:.1f} % without {n_safe} provably safe faults)")
