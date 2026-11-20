#!/usr/bin/env python3
"""Score the lockstep campaign (ls_*.json), the common-cause run (lockstep_cc.json) and the synthesis areas."""
import json
import re
import statistics
import sys
from collections import defaultdict

F = [f for p in range(4) for f in json.load(open(f"ls_{p}.json"))["faults"]]
cycles = json.load(open("ls_0.json"))["cycles"]
CG = json.load(open("subparts-cells.json"))
cc = json.load(open("lockstep_cc.json"))
wrong = [f for f in F if f["cmd"] is not None]
first = [f for f in wrong if f["ls"] is not None and f["ls"] <= f["cmd"]]
seu = [f for f in F if f["kind"] == "seu" and f["ls"] is not None]
per = defaultdict(lambda: [0.0, 0.0])
for f in F:
  if f["kind"] != "seu":
    for g in CG[f["cell"]]:
      w = 1 / len(CG[f["cell"]])
      per[g][0] += w
      per[g][1] += w * (f["ls"] is not None)
ccw = [g for g in cc if g["cmd_t"]]
area = lambda p, m: float(re.search(rf"Chip area for module '\\{m}': ([\d.]+)", open(p).read()).group(1))
S = {"app_cycles": cycles, "faults": len(F), "wrong_cmd": len(wrong), "caught_first": len(first),
     "lead_median": statistics.median([f["cmd"] - f["ls"] for f in first]),
     "seu_seen": len(seu), "seu_latency_median": statistics.median([f["ls"] - f["inject"] for f in seu]),
     "stuck_n": sum(f["kind"] != "seu" for f in F), "stuck_seen": sum(f["kind"] != "seu" and f["ls"] is not None for f in F),
     "per_sub_part": {g: round(v[1] / v[0], 4) for g, v in sorted(per.items())},
     "cc_glitches": len(cc), "cc_wrong_cmd": len(ccw), "cc_visible": sum(g["vis_t"] for g in cc),
     "cc_delayed_caught": sum(g["delayed_caught"] for g in cc), "cc_wrong_cmd_delayed_caught": sum(g["delayed_caught"] for g in ccw),
     "area_um2": {"single": area(sys.argv[1], "picorv32"), "lockstep": area(sys.argv[2], "lockstep_top")}}
json.dump(S, open("lockstep_summary.json", "w"), indent=1)
print(json.dumps(S))
