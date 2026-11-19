#!/usr/bin/env python3
"""Lockstep on PicoRV32: does a second core, compared every cycle, catch the faults that would send a wrong command?

Workload: a small torque-request limiter (clamp to +/-LIMIT, rate-limit by RATE per sample, apply a gain) over 64 samples,
one actuator command written per sample. In simulation the checker core is the fault-free lane: a lockstep comparator sees
exactly the cycles where the faulty core's outputs differ from it.

For each fault we record:
  ls_cycle   first cycle any core output differs (when lockstep would flag it), or None
  cmd_cycle  first cycle a wrong actuator command is written to the OUT area, or None
usage: lockstep.py golden | run PART NPARTS OUT
"""
import json
import random
import sys
import time

import gatesim
import selftest

NET = gatesim.Netlist("netlist.json", "tt.lib")
IN, OUT, LIMIT, RATE, GAIN, NS = 0x9000, 0x9800, 1500, 200, 300, 64


def build_app():
  a = selftest.Asm()
  rng = random.Random(11)
  samples = [rng.randint(-2500, 2500) for _ in range(NS)]
  for k, v in enumerate(samples):
    a.extra[IN + 4 * k] = v & selftest.M32
  a.jal(0, "start")
  a.label("start")
  a.li(1, IN); a.li(2, OUT); a.li(3, NS)        # x1 in, x2 out, x3 count
  a.li(4, 0)                                     # x4 previous command
  a.li(5, LIMIT); a.li(6, -LIMIT); a.li(7, RATE); a.li(8, -RATE); a.li(9, GAIN)
  a.li(15, 0)                                    # x15 checksum
  a.label("loop")
  a.i(0, 1, 2, 10, 0x03)                         # lw x10, 0(x1)   request
  a.b(4, 10, 5, "c1"); a.i(0, 5, 0, 10, 0x13)   # if !(x10 < LIMIT) x10 = LIMIT
  a.label("c1")
  a.b(5, 10, 6, "c2"); a.i(0, 6, 0, 10, 0x13)   # if !(x10 >= -LIMIT) x10 = -LIMIT
  a.label("c2")
  a.r(0x20, 4, 10, 0, 11, 0x33)                  # x11 = x10 - x4 (delta)
  a.b(4, 7, 11, "r1")                            # if RATE < delta: x10 = x4 + RATE
  a.jal(0, "r1d")
  a.label("r1")
  a.r(0, 7, 4, 0, 10, 0x33)
  a.label("r1d")
  a.b(4, 11, 8, "r2")                            # if delta < -RATE: x10 = x4 - RATE
  a.jal(0, "r2d")
  a.label("r2")
  a.r(0x20, 7, 4, 0, 10, 0x33)
  a.label("r2d")
  a.i(0, 10, 0, 4, 0x13)                         # prev = x10
  a.r(1, 9, 10, 0, 12, 0x33)                     # x12 = x10 * GAIN
  a.i(8 | 0x400, 12, 5, 12, 0x13)                # srai x12, x12, 8
  a.s(0, 12, 2, 2)                               # sw x12, 0(x2)   actuator command
  a.r(0, 12, 15, 4, 15, 0x33)                    # checksum ^= command
  a.i(4, 1, 0, 1, 0x13); a.i(4, 2, 0, 2, 0x13); a.i(-1, 3, 0, 3, 0x13)
  a.b(1, 3, 0, "loop")                           # bnez x3, loop
  a.s(0, 15, 2, 2)                               # store checksum after the commands
  a.word(0x00100073)                             # ebreak (irqs masked after reset: trap)
  return a, samples


def model(samples):
  prev, out = 0, []
  for v in samples:
    v = max(-LIMIT, min(LIMIT - 0, v)) if v >= LIMIT or v < -LIMIT else v
    d = v - prev
    if d > RATE:
      v = prev + RATE
    if d < -RATE:
      v = prev - RATE
    prev = v
    out.append(((v * GAIN) >> 8) & selftest.M32)
  return out


APP, SAMPLES = build_app()
WORDS = APP.assemble()


def simulate(lanes, stuck=None, seu=None, max_cycles=10 ** 6, pairs=False):
  stuck, seu = stuck or {}, seu or {}
  M = (1 << (lanes + 1)) - 1
  load, comb, clock = NET.compile(stuck.keys())
  K0, K1 = [M] * NET.nnets, [0] * NET.nnets
  for n, (m0, m1) in stuck.items():
    K0[n] = M & ~(m0 | m1)
    K1[n] = m1
  v, st = [0] * NET.nnets, [0] * len(NET.ffs)
  mem = {4 * k: w for k, w in enumerate(WORDS)}
  mem.update(APP.extra)
  ready = rdata = 0
  I, O = NET.inputs, NET.outputs
  zero_in = [i for pn in ("irq", "pcpi_rd", "pcpi_ready", "pcpi_wait", "pcpi_wr", "clk") for i in I[pn]]
  all_out = [i for pn in sorted(O) for i in O[pn] if isinstance(i, int)]
  ov, oa, ow, os_ = O["mem_valid"][0], O["mem_addr"], O["mem_wdata"], O["mem_wstrb"]
  ls_seen = cmd_seen = 0
  pair_seen = 0
  odd = sum(1 << (2 * j + 1) for j in range(lanes // 2))
  ls_first, cmd_first = {}, {}
  stores, cyc, end = [], 0, None
  while cyc < max_cycles:
    for k, m in seu.get(cyc, ()):
      st[k] ^= m
    for i in zero_in:
      v[i] = 0
    v[I["resetn"][0]] = M if cyc >= 4 else 0
    v[I["mem_ready"][0]] = M if ready else 0
    for k, i in enumerate(I["mem_rdata"]):
      v[i] = M if (rdata >> k) & 1 else 0
    load(v, M, st)
    comb(v, M, K0, K1)
    g = lambda i: (v[i] & 1) if isinstance(i, int) else int(i == "1")
    if cyc >= 4:
      diff = 0
      for i in all_out:                         # lockstep: every output bit, every cycle
        diff |= v[i] ^ (M if v[i] & 1 else 0)
      new = diff & ~ls_seen & ~1
      while new:
        lb = new & -new
        ls_first[lb.bit_length() - 2] = cyc
        new ^= lb
      ls_seen |= diff
      if pairs:                                  # lane 2j+1 against lane 2j+2: core A against the delayed checker
        for i in all_out:
          pair_seen |= (v[i] ^ (v[i] >> 1)) & odd
    gv = g(ov)
    addr = sum(g(i) << k for k, i in enumerate(oa))
    wstrb = sum(g(i) << k for k, i in enumerate(os_))
    wdata = sum(g(i) << k for k, i in enumerate(ow))
    # wrong actuator command: a faulty lane writes to OUT.. with a different address, data or presence than golden
    lane_valid = v[ov] if isinstance(ov, int) else 0
    if cyc >= 4:
      cd = 0
      golden_cmd = gv and wstrb and OUT <= addr < OUT + 4 * (NS + 1)
      if golden_cmd:
        for k, i in enumerate(ow):
          cd |= v[i] ^ (M if (wdata >> k) & 1 else 0)
        for k, i in enumerate(oa):
          if isinstance(i, int):
            cd |= v[i] ^ (M if (addr >> k) & 1 else 0)
        cd |= v[ov] ^ M
      new = cd & ~cmd_seen & ~1
      while new:
        lb = new & -new
        cmd_first[lb.bit_length() - 2] = cyc
        new ^= lb
      cmd_seen |= cd
    if gv and not ready:
      if wstrb:
        mem[addr] = wdata
        stores.append((addr, wdata))
        rdata = 0
      else:
        rdata = mem.get(addr, 0)
      ready = 1
    else:
      ready = 0
    st = clock(v, M, st)
    cyc += 1
    if end is None and g(O["trap"][0]):
      end = cyc + 4
    if end is not None and cyc >= end:
      break
  simulate.pairs = pair_seen
  return ls_first, cmd_first, cyc, stores


def golden():
  t = time.monotonic()
  _, _, cyc, stores = simulate(0)
  want = model(SAMPLES)
  got = [w for a, w in stores if OUT <= a < OUT + 4 * NS]
  print(f"golden: {cyc} cycles, {len(stores)} stores, {time.monotonic() - t:.1f} s; commands match the Python model: {got == want}")
  return cyc


def run(part, nparts, out):
  import campaign
  _, cycles, _ = simulate(0)[1:] if False else (None, None, None)
  cyc0 = simulate(0)[2]
  faults = [f for f in campaign.fault_list(seed=7, cycles=cyc0)]
  faults = faults[part::nparts]
  stuck, seu = {}, {}
  for j, (kind, cn, where) in enumerate(faults):
    m = 1 << (j + 1)
    if kind == "seu":
      k, c = where
      seu.setdefault(c, []).append((k, m))
    else:
      m0, m1 = stuck.get(where, (0, 0))
      stuck[where] = (m0 | m, m1) if kind == "sa0" else (m0, m1 | m)
  t = time.monotonic()
  ls, cmd, cyc, _ = simulate(len(faults), stuck, seu, max_cycles=cyc0 + 8)
  res = [{"kind": kind, "cell": cn, "ls": ls.get(j), "cmd": cmd.get(j),
          "inject": (where[1] if kind == "seu" else 4)} for j, (kind, cn, where) in enumerate(faults)]
  json.dump({"cycles": cyc0, "faults": res}, open(out, "w"))
  print(f"part {part}: {len(faults)} faults, {round(time.monotonic() - t)} s", flush=True)


if __name__ == "__main__":
  if sys.argv[1] == "golden":
    golden()
  else:
    run(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
