#!/usr/bin/env python3
"""Split the synthesised PicoRV32 netlist (sky130 cells) into FMEDA sub-parts.

Flip-flops are grouped by the register they implement (name rules below). Every combinational cell is
attributed to the groups whose flip-flop inputs it feeds (backward logic cone); a cell feeding several
groups is shared out equally and also counted as shared. Area is the liberty cell area in um^2.
"""
import json
import re
import sys
from collections import defaultdict, deque

NETLIST, LIB, OUT = sys.argv[1], sys.argv[2], sys.argv[3]

RULES = [
  ("Register file", r"^(cpuregs|\$\\cpuregs)"),
  ("Multiplier", r"pcpi_mul\."),
  ("Divider", r"pcpi_div\."),
  ("Counters", r"^count_"),
  ("IRQ + timer", r"^(irq_|eoi$|timer$|instr_(timer|waitirq|maskirq|retirq|setq|getq)$)"),
  ("Decoder", r"^(instr_|is_|decoded_|decoder_|pcpi_insn$|compressed_instr)"),
  ("Fetch + PC", r"^(reg_pc$|reg_next_pc$|mem_do_prefetch$|mem_do_rinst$|latched_branch$)"),
  ("Load / store", r"^(mem_|latched_is_l|latched_store$)"),
  ("ALU + execute", r"^(alu_out|reg_op|reg_sh$|reg_out$|is_compare$|latched_stalu$)"),
  ("Control", r".*"),
]


def group_of(name):
  base = re.sub(r"\[.*", "", name)
  for g, rx in RULES:
    if re.search(rx, base):
      return g
  return "Control"


def lib_areas(path):
  areas, cur = {}, None
  with open(path) as f:
    for ln in f:
      m = re.match(r'\s*cell\s*\(\s*"?([\w]+)"?\s*\)', ln)
      if m:
        cur = m.group(1)
        continue
      m = re.match(r"\s*area\s*:\s*([\d.]+)", ln)
      if m and cur and cur not in areas:
        areas[cur] = float(m.group(1))
  return areas


mod = json.load(open(NETLIST))["modules"]["picorv32"]
cells, nets, ports = mod["cells"], mod["netnames"], mod["ports"]
area = lib_areas(LIB)
bit2name = {}
for name, v in sorted(nets.items(), key=lambda kv: kv[1].get("hide_name", 0)):
  for b in v["bits"]:
    if isinstance(b, int):
      bit2name.setdefault(b, name)

is_ff = lambda t: "df" in t
OUTPINS = {"Q", "Q_N", "X", "Y", "COUT", "SUM", "HI", "LO"}
for c in cells.values():
  c["port_directions"] = {p: ("output" if p in OUTPINS else "input") for p in c["connections"]}
driver = {}
for cn, c in cells.items():
  for p, d in c["port_directions"].items():
    if d == "output":
      for b in c["connections"][p]:
        if isinstance(b, int):
          driver[b] = cn

ffgroup = {}
for cn, c in cells.items():
  if is_ff(c["type"]):
    q = c["connections"]["Q"][0]
    ffgroup[cn] = group_of(bit2name.get(q, "?"))

reach = defaultdict(set)


def walk(start_bits, g):
  dq, seen = deque(start_bits), set()
  while dq:
    b = dq.popleft()
    cn = driver.get(b)
    if cn is None or cn in seen or is_ff(cells[cn]["type"]):
      continue
    seen.add(cn)
    reach[cn].add(g)
    c = cells[cn]
    for p, d in c["port_directions"].items():
      if d == "input":
        dq.extend(x for x in c["connections"][p] if isinstance(x, int))


for cn, g in ffgroup.items():
  c = cells[cn]
  walk([x for p, d in c["port_directions"].items() if d == "input" and p != "CLK"
        for x in c["connections"][p] if isinstance(x, int)], g)
for pn, p in ports.items():
  if p["direction"] == "output":
    g = "Load / store" if pn.startswith("mem_") else "Control"
    walk([x for x in p["bits"] if isinstance(x, int)], g)

# Register-file read ports: a mux cell whose data inputs all come from register-file flip-flops, or from
# such mux cells, belongs to the register file (its read port), whichever stage latches the result.
rf_bits = {cells[cn]["connections"]["Q"][0] for cn, g in ffgroup.items() if g == "Register file"}
read_port = set()
changed = True
while changed:
  changed = False
  for cn, c in cells.items():
    if cn in read_port or not re.search(r"__mux[24]", c["type"]):
      continue
    data = [x for p in ("A0", "A1", "A2", "A3") for x in c["connections"].get(p, []) if isinstance(x, int)]
    if data and all(x in rf_bits for x in data) and "mux2i" not in c["type"]:
      read_port.add(cn)
      rf_bits.update(x for p in ("X", "Y") for x in c["connections"].get(p, []) if isinstance(x, int))
      changed = True
for cn in read_port:
  reach[cn] = {"Register file"}

groups = [g for g, _ in RULES]
res = {g: {"ff": 0, "ff_area": 0.0, "logic_cells": 0.0, "logic_area": 0.0, "shared_area": 0.0} for g in groups}
unattributed = 0
for cn, c in cells.items():
  a = area[c["type"]]
  if is_ff(c["type"]):
    r = res[ffgroup[cn]]
    r["ff"] += 1
    r["ff_area"] += a
  else:
    gs = reach.get(cn)
    if not gs:
      unattributed += 1
      continue
    for g in gs:
      res[g]["logic_cells"] += 1 / len(gs)
      res[g]["logic_area"] += a / len(gs)
      if len(gs) > 1:
        res[g]["shared_area"] += a / len(gs)

total_area = sum(area[c["type"]] for c in cells.values())
rows = []
for g in groups:
  r = res[g]
  a = r["ff_area"] + r["logic_area"]
  rows.append({"sub_part": g, "flip_flops": r["ff"], "logic_cells": round(r["logic_cells"]),
               "area_um2": round(a, 1), "area_share": round(a / total_area, 4),
               "shared_logic_area_um2": round(r["shared_area"], 1)})
rows.sort(key=lambda r: -r["area_um2"])
out = {"core": "PicoRV32 (YosysHQ, ISC licence)",
       "config": "RV32I + MUL + DIV + IRQ (q-regs) + counters",
       "library": "sky130_fd_sc_hd, tt_025C_1v80",
       "tool": "Yosys (yowasp-yosys), synth -flatten, dfflibmap + abc to liberty",
       "cells": len(cells), "register_file_read_port_cells": len(read_port), "flip_flops": sum(r["flip_flops"] for r in rows),
       "area_um2": round(total_area, 1), "unattributed_cells": unattributed,
       "cell_types": {}, "sub_parts": rows}
for c in cells.values():
  out["cell_types"][c["type"]] = out["cell_types"].get(c["type"], 0) + 1
json.dump(out, open(OUT, "w"), indent=1)
print(f"{'sub-part':16}{'FF':>6}{'logic':>8}{'area um2':>11}{'share':>8}{'shared':>9}")
for r in rows:
  print(f"{r['sub_part']:16}{r['flip_flops']:>6}{r['logic_cells']:>8}{r['area_um2']:>11.0f}{r['area_share'] * 100:>7.1f}%"
        f"{r['shared_logic_area_um2']:>9.0f}")
print("cells", len(cells), "area", round(total_area), "unattributed", unattributed)

# cell -> sub-parts it belongs to (for scoring faults per sub-part)
cg = {cn: [ffgroup[cn]] for cn in ffgroup}
cg.update({cn: sorted(gs) for cn, gs in reach.items() if cn not in cg})
json.dump(cg, open(OUT.replace(".json", "-cells.json"), "w"))
