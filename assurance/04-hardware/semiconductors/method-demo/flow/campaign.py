#!/usr/bin/env python3
"""Fault campaign on the PicoRV32 gate netlist running the self-test.

Faults: stuck-at-0 and stuck-at-1 on every cell output, and one bit flip (SEU) in every flip-flop at a random
cycle of the test. A fault counts as DETECTED when the faulty core's memory-bus behaviour differs from the
fault-free core while the self-test runs (a wrong value written, a wrong address, a missing or extra access,
or a trap). Because the test writes every result to memory, a software compare against the known-good
results plus a watchdog on the run time would catch exactly these. Anything else is UNDETECTED.

usage: campaign.py golden            run the fault-free core, check against the ISS
       campaign.py run WORKERS OUT   run the whole fault list, one chunk per worker process
The netlist is netlist.json in the working directory, or $NETLIST.
"""
import json
import random
import sys
import time

import gatesim
import selftest

import os
NET = gatesim.Netlist(os.environ.get("NETLIST", "netlist.json"), "tt.lib")
PROG = selftest.build()
WORDS = PROG.assemble()


def bits(v, idxs, M):
  return [M if (v >> k) & 1 else 0 for k in range(len(idxs))]


def simulate(lanes, stuck=None, seu=None, max_cycles=None, golden_ref=None, trace=False):
  """lanes: number of faulty machines (lane 0 is golden). stuck: {net: (sa0_mask, sa1_mask)}.
  seu: {cycle: [(ff_index, mask)]}. Returns (detected_mask, golden_cycles, golden_stores)."""
  stuck = stuck or {}
  seu = seu or {}
  M = (1 << (lanes + 1)) - 1
  load, comb, clock = NET.compile(stuck.keys())
  K0 = [M] * NET.nnets
  K1 = [0] * NET.nnets
  for n, (m0, m1) in stuck.items():
    K0[n] = M & ~(m0 | m1)
    K1[n] = m1
  v = [0] * NET.nnets
  st = [0] * len(NET.ffs)
  mem = {4 * k: w for k, w in enumerate(WORDS)}
  mem.update(PROG.extra)
  irq_next = 0
  ready, rdata = 0, 0
  I, O = NET.inputs, NET.outputs
  out_valid, out_instr, out_addr, out_wdata, out_wstrb, out_trap = (O["mem_valid"][0], O["mem_instr"][0], O["mem_addr"],
                                                                     O["mem_wdata"], O["mem_wstrb"], O["trap"][0])
  const_zero = [i for pn in ("pcpi_rd", "pcpi_ready", "pcpi_wait", "pcpi_wr", "clk") for i in I[pn]]
  detected = 0
  ecc_c, ecc_e = O.get("ecc_corrected", [None])[0], O.get("ecc_error", [None])[0]
  seen_c = seen_e = 0
  stores, cyc, end = [], 0, None
  limit = max_cycles or 10 ** 7
  while cyc < limit:
    for k, m in seu.get(cyc, ()):
      st[k] ^= m
    for i in const_zero:
      v[i] = 0
    for k, i in enumerate(I["irq"]):
      v[i] = M if (irq_next >> k) & 1 else 0
    irq_next = 0
    v[I["resetn"][0]] = M if cyc >= 4 else 0
    v[I["mem_ready"][0]] = M if ready else 0
    for k, i in enumerate(I["mem_rdata"]):
      v[i] = M if (rdata >> k) & 1 else 0
    load(v, M, st)
    comb(v, M, K0, K1)
    g = lambda i: (v[i] & 1) if isinstance(i, int) else int(i == "1")
    lane = lambda i: v[i] if isinstance(i, int) else (M if i == "1" else 0)
    gv = g(out_valid)
    diff = v[out_valid] ^ (M if gv else 0)
    diff |= v[out_trap] ^ (M if g(out_trap) else 0)
    if gv:
      addr = sum(g(i) << k for k, i in enumerate(out_addr))
      wstrb = sum(g(i) << k for k, i in enumerate(out_wstrb))
      for i in out_addr + out_wstrb + [out_instr]:
        diff |= lane(i) ^ (M if g(i) else 0)
      if wstrb:
        wdata = sum(g(i) << k for k, i in enumerate(out_wdata))
        for k, i in enumerate(out_wdata):
          if (wstrb >> (k // 8)) & 1:
            diff |= lane(i) ^ (M if (wdata >> k) & 1 else 0)
    if cyc >= 4:
      detected |= diff
      if isinstance(ecc_c, int):
        seen_c |= v[ecc_c]
      if isinstance(ecc_e, int):
        seen_e |= v[ecc_e]
    # memory responds one cycle after a request, like the PicoRV32 reference testbench
    if gv and not ready:
      if wstrb:
        w = mem.get(addr, 0)
        for k in range(4):
          if (wstrb >> k) & 1:
            w = (w & ~(0xFF << 8 * k)) | (wdata & (0xFF << 8 * k))
        if addr == selftest.IRQ_TRIG:
          irq_next = wdata
        else:
          mem[addr] = w
        stores.append((addr, w))
        rdata = 0
      else:
        rdata = mem.get(addr, 0)
      ready = 1
    else:
      ready = 0
    st = clock(v, M, st)
    cyc += 1
    if end is None and g(out_trap):
      end = cyc + 4
    if end is not None and cyc >= end:
      break
    if lanes and (detected | 1) == M:
      break
  simulate.ecc = (seen_c, seen_e)
  return detected & ~1, cyc, stores


def golden():
  t = time.monotonic()
  _, cycles, stores = simulate(0)
  dt = time.monotonic() - t
  ref = selftest.iss(WORDS, PROG.labels["iss_stop"], PROG.extra)
  ok = stores[:len(ref)] == ref
  print(f"golden: {cycles} cycles, {len(stores)} stores, {dt:.1f} s ({dt / cycles * 1e3:.2f} ms/cycle)")
  print("ISS check:", "PASS" if ok else "FAIL", f"({len(ref)} deterministic stores compared)")
  if not ok:
    for k, (a, b) in enumerate(zip(stores, ref)):
      if a != b:
        print("first mismatch at store", k, [hex(x) for x in a], [hex(x) for x in b])
        break
  print("end marker:", hex(stores[-1][1]) if stores else None)
  return cycles


def fault_list(seed=7, cycles=None):
  faults = []
  for cn, t, ins, outs in NET.comb + NET.ffs:
    o = list(outs.values())[0]
    faults.append(("sa0", cn, o))
    faults.append(("sa1", cn, o))
  rng = random.Random(seed)
  for k, (cn, t, ins, outs) in enumerate(NET.ffs):
    faults.append(("seu", cn, (k, rng.randrange(8, cycles - 8))))
  return faults


def run_chunk(args):
  idx, chunk, cycles = args
  stuck, seu = {}, {}
  for j, (kind, cn, where) in enumerate(chunk):
    m = 1 << (j + 1)
    if kind == "seu":
      k, c = where
      seu.setdefault(c, []).append((k, m))
    else:
      m0, m1 = stuck.get(where, (0, 0))
      stuck[where] = (m0 | m, m1) if kind == "sa0" else (m0, m1 | m)
  t = time.monotonic()
  det, cyc, _ = simulate(len(chunk), stuck, seu, max_cycles=cycles + 8)
  res = [{"kind": kind, "cell": cn, "detected": bool((det >> (j + 1)) & 1)} for j, (kind, cn, where) in enumerate(chunk)]
  print(f"chunk {idx}: {len(chunk)} faults, {sum(r['detected'] for r in res)} detected, {cyc} cycles, "
        f"{time.monotonic() - t:.0f} s", flush=True)
  return idx, res


def run(workers, out):
  """Split the fault list into one chunk per CPU and simulate the chunks in parallel."""
  from multiprocessing import Pool
  _, cycles, _ = simulate(0)
  faults = fault_list(cycles=cycles)
  n = -(-len(faults) // workers)
  chunks = [(i, faults[i * n:(i + 1) * n], cycles) for i in range(workers)]
  t0 = time.monotonic()
  with Pool(workers) as pool:
    done = dict(pool.imap_unordered(run_chunk, chunks))
  results = [r for i in range(workers) for r in done[i]]
  json.dump({"cycles": cycles, "workers": workers, "seconds": round(time.monotonic() - t0), "faults": results}, open(out, "w"))
  print("done", len(results), "faults in", round(time.monotonic() - t0), "s", flush=True)


if __name__ == "__main__":
  if sys.argv[1] == "golden":
    golden()
  else:
    run(int(sys.argv[2]), sys.argv[3])
