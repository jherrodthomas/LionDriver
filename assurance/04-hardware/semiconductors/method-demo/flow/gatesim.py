#!/usr/bin/env python3
"""Bit-parallel gate-level simulator for a Yosys JSON netlist mapped to liberty cells.

Each net holds a Python int; bit k is the value in machine k. Bit 0 is the fault-free (golden) machine and
the other bits are faulty copies, so one pass simulates up to LANES machines. Cell logic comes from the
liberty `function` and `ff next_state` strings, compiled to Python. Single clock, two-valued (0/1) logic.
"""
import json
import re


# ---------------------------------------------------------------- liberty
def liberty_cells(path, wanted):
  txt = open(path).read()
  out = {}
  for name in wanted:
    i = txt.index(f'cell ("{name}")')
    j = txt.find('\n    cell (', i + 10)
    body = txt[i:j if j > 0 else len(txt)]
    pins, ff = {}, None
    for m in re.finditer(r'pin \("(\w+)"\) \{(.*?)\n        \}', body, re.S):
      pn, pb = m.group(1), m.group(2)
      d = re.search(r'direction : "(\w+)"', pb)
      f = re.search(r'\bfunction : "([^"]*)"', pb)
      pins[pn] = (d.group(1) if d else None, f.group(1) if f else None)
    m = re.search(r'ff \("(\w+)",\s*"(\w+)"\) \{(.*?)\}', body, re.S)
    if m:
      ns = re.search(r'next_state : "([^"]*)"', m.group(3))
      ff = (m.group(1), ns.group(1))
    out[name] = {"pins": pins, "ff": ff}
  return out


def compile_expr(expr, env):
  """Liberty boolean expression -> Python expression. env maps pin names to Python operands; M is all lanes set."""
  toks = re.findall(r"\w+|[!&|^()'*+]", expr)
  pos = 0

  def peek():
    return toks[pos] if pos < len(toks) else None

  def take():
    nonlocal pos
    pos += 1
    return toks[pos - 1]

  def prim():
    t = take()
    if t == "!":
      return f"(M^{prim()})"
    if t == "(":
      e = orx()
      take()
      r = e
    elif t in ("1", "0"):
      r = "M" if t == "1" else "0"
    else:
      r = env[t]
    while peek() == "'":
      take()
      r = f"(M^{r})"
    return r

  def andx():
    a = prim()
    while peek() is not None and (peek() in ("&", "*") or re.match(r"\w|!|\(", peek())):
      if peek() in ("&", "*"):
        take()
      a = f"({a}&{prim()})"
    return a

  def xorx():
    a = andx()
    while peek() == "^":
      take()
      a = f"({a}^{andx()})"
    return a

  def orx():
    a = xorx()
    while peek() in ("|", "+"):
      take()
      a = f"({a}|{xorx()})"
    return a

  r = orx()
  assert pos == len(toks), (expr, toks)
  return r


# ---------------------------------------------------------------- netlist
class Netlist:
  def __init__(self, netlist_json, lib_path, top="picorv32"):
    mod = json.load(open(netlist_json))["modules"][top]
    self.cells, self.ports = mod["cells"], mod["ports"]
    self.lib = liberty_cells(lib_path, sorted({c["type"] for c in self.cells.values()}))
    self.bitidx = {}

    def idx(b):
      if b in ("0", "1", "x", "z"):
        return b
      if b not in self.bitidx:
        self.bitidx[b] = len(self.bitidx)
      return self.bitidx[b]

    self.ffs, comb = [], []
    for cn, c in self.cells.items():
      L = self.lib[c["type"]]
      ins = {p: idx(c["connections"][p][0]) for p, (d, _) in L["pins"].items() if d == "input" and p in c["connections"]}
      outs = {p: idx(c["connections"][p][0]) for p, (d, _) in L["pins"].items() if d == "output" and p in c["connections"]}
      if L["ff"]:
        self.ffs.append((cn, c["type"], ins, outs))
      else:
        comb.append((cn, c["type"], ins, outs))
    self.inputs = {pn: [idx(b) for b in p["bits"]] for pn, p in self.ports.items() if p["direction"] == "input"}
    self.outputs = {pn: [idx(b) for b in p["bits"]] for pn, p in self.ports.items() if p["direction"] == "output"}
    # levelize combinational cells
    driver = {}
    for k, (cn, t, ins, outs) in enumerate(comb):
      for o in outs.values():
        driver[o] = k
    order, state = [], {}

    def visit(k):
      st = state.get(k)
      if st == 2:
        return
      assert st != 1, "combinational loop"
      state[k] = 1
      for i in comb[k][2].values():
        if i in driver:
          visit(driver[i])
      state[k] = 2
      order.append(k)

    import sys
    sys.setrecursionlimit(100000)
    for k in range(len(comb)):
      visit(k)
    self.comb = [comb[k] for k in order]
    self.nnets = len(self.bitidx)
    self.cell_out = {}  # cell name -> output net index (first output)
    for cn, t, ins, outs in self.comb + self.ffs:
      self.cell_out[cn] = list(outs.values())[0]

  def operand(self, i):
    return {"0": "0", "1": "M", "x": "0", "z": "0"}[i] if isinstance(i, str) else f"v[{i}]"

  def build_step(self, stuck_nets=()):
    """Source of step(v, M, K0, K1): evaluate all combinational cells, forcing stuck nets (K0 keeps, K1 sets)."""
    stuck = set(stuck_nets)
    lines = ["def comb(v, M, K0, K1):"]
    for cn, n in ((cn, outs) for cn, t, ins, outs in self.ffs for _ in [0]):
      pass
    # flip-flop outputs can be stuck too: force them at the start of each cycle
    for cn, t, ins, outs in self.ffs:
      for o in outs.values():
        if o in stuck:
          lines.append(f" v[{o}]=(v[{o}]&K0[{o}])|K1[{o}]")
    for cn, t, ins, outs in self.comb:
      L = self.lib[t]
      env = {p: self.operand(i) for p, i in ins.items()}
      for p, o in outs.items():
        e = compile_expr(L["pins"][p][1], env)
        lines.append(f" v[{o}]={e}")
        if o in stuck:
          lines.append(f" v[{o}]=(v[{o}]&K0[{o}])|K1[{o}]")
    lines.append(" return v")
    lines.append("def clock(v, M, st):")
    for k, (cn, t, ins, outs) in enumerate(self.ffs):
      L = self.lib[t]
      iq, ns = L["ff"]
      env = {p: self.operand(i) for p, i in ins.items()}
      env[iq] = f"st[{k}]"
      lines.append(f" n{k}={compile_expr(ns, env)}")
    for k in range(len(self.ffs)):
      lines.append(f" st[{k}]=n{k}")
    lines.append(" return st")
    lines.append("def load(v, M, st):")
    for k, (cn, t, ins, outs) in enumerate(self.ffs):
      L = self.lib[t]
      iq, _ = L["ff"]
      for p, o in outs.items():
        f = L["pins"][p][1]
        lines.append(f" v[{o}]={compile_expr(f, {iq: f'st[{k}]', iq + '_N': f'(M^st[{k}])'})}")
    lines.append(" return v")
    return "\n".join(lines)

  def compile(self, stuck_nets=()):
    ns = {}
    exec(compile(self.build_step(stuck_nets), "<netlist>", "exec"), ns)
    return ns["load"], ns["comb"], ns["clock"]
