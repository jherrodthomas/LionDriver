#!/usr/bin/env python3
"""Bit flips in the register file, with and without SECDED ECC, while the self-test runs.

The same single flips (register, data bit, cycle) and the same double flips are injected in both cores; the ECC core
also gets single flips in its 7 check bits. x0 is left out (it is never read). Each flip is scored as:
  wrong result  - the core's bus traffic changed and no ECC flag was raised
  flagged       - the ECC error flag was raised (a double error: the core knows its data is bad)
  corrected     - the ECC corrected a read of the bad word and nothing changed
  no effect     - nothing changed and the word was never read before it was overwritten
usage: NETLIST=<netlist> ecc_campaign.py base|ecc PART NPARTS OUT
"""
import json
import random
import re
import sys
import time

import campaign as C

which, part, nparts, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
CYCLES = C.simulate(0)[1]  # length of the fault-free self-test run
pat = re.compile(r"^cpuregs\[(\d+)\]$" if which == "base" else r"^cpuregs\.regs\[(\d+)\]$")
mod = json.load(open(C.os.environ.get("NETLIST", "netlist.json")))["modules"]["picorv32"]
b2n = {}
for n, v in sorted(mod["netnames"].items(), key=lambda kv: kv[1].get("hide_name", 0)):
  for i, b in enumerate(v["bits"]):
    if isinstance(b, int):
      b2n.setdefault(b, (n, i))
store = {}
for k, (cn, t, ins, outs) in enumerate(C.NET.ffs):
  n, i = b2n[mod["cells"][cn]["connections"]["Q"][0]]
  m = pat.match(n)
  if m:
    store[(int(m.group(1)), i)] = k
nbits = 32 if which == "base" else 39
faults = []
for r in range(1, 36):
  for b in range(nbits):
    faults.append(("single", r, (b,), random.Random(f"{r}-{b}").randrange(8, CYCLES - 8)))
rng = random.Random(99)
for _ in range(600):
  r = rng.randrange(1, 36)
  b1, b2 = sorted(rng.sample(range(32), 2))
  faults.append(("double", r, (b1, b2), rng.randrange(8, CYCLES - 8)))
faults = faults[part::nparts]
seu = {}
for j, (kind, r, bits, cyc) in enumerate(faults):
  for b in bits:
    seu.setdefault(cyc, []).append((store[(r, b)], 1 << (j + 1)))
t = time.monotonic()
det, cyc, _ = C.simulate(len(faults), None, seu, max_cycles=CYCLES + 8)
sc, se = C.simulate.ecc
res = [{"kind": k, "reg": r, "bits": list(bits), "cycle": c, "visible": bool((det >> (j + 1)) & 1),
        "corr": bool((sc >> (j + 1)) & 1), "err": bool((se >> (j + 1)) & 1)} for j, (k, r, bits, c) in enumerate(faults)]
json.dump(res, open(out, "w"))
print(which, part, len(faults), "flips", round(time.monotonic() - t), "s", flush=True)
