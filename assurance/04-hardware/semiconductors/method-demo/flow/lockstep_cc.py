#!/usr/bin/env python3
"""Common-cause glitch: the same flip-flop flips in both cores. Same cycle (plain lockstep) or 2 cycles apart in program
time (delayed lockstep, checker 2 cycles behind). Lane pairs: (flip at t) and (flip at t-2), same flip-flop."""
import json
import random
import campaign
import lockstep as L

cyc0 = L.simulate(0)[2]
rng = random.Random(7)
glitches = [(k, rng.randrange(10, cyc0 - 8)) for k in range(len(L.NET.ffs))]
seu = {}
for j, (k, t) in enumerate(glitches):
  seu.setdefault(t, []).append((k, 1 << (2 * j + 1)))
  seu.setdefault(t - 2, []).append((k, 1 << (2 * j + 2)))
ls, cmd, cyc, _ = L.simulate(2 * len(glitches), None, seu, max_cycles=cyc0 + 8, pairs=True)
P = L.simulate.pairs
res = [{"ff": k, "t": t, "vis_t": (2 * j) in ls, "vis_t2": (2 * j + 1) in ls,
        "cmd_t": (2 * j) in cmd, "cmd_t2": (2 * j + 1) in cmd, "delayed_caught": bool((P >> (2 * j + 1)) & 1)} for j, (k, t) in enumerate(glitches)]
json.dump(res, open("lockstep_cc.json", "w"))
print("cc done", len(res))
