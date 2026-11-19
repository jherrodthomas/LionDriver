#!/usr/bin/env python3
"""A software self-test for PicoRV32 (RV32IM + its IRQ extension), a tiny assembler for it, and an
instruction-set model (ISS) used to check that the gate-level netlist runs the program correctly.

The test stores every result to memory, so a wrong result shows up as a wrong write on the memory bus.
"""
import random

M32 = 0xFFFFFFFF
REG = {f"x{i}": i for i in range(32)}


def sx(v, bits):
  v &= (1 << bits) - 1
  return v - (1 << bits) if v >> (bits - 1) else v


# ---------------------------------------------------------------- assembler
class Asm:
  def __init__(self):
    self.items = []  # (kind, args)
    self.labels = {}
    self.extra = {}  # address -> word, placed outside the code area

  def pc(self):
    return 4 * len(self.items)

  def label(self, name):
    self.labels[name] = self.pc()

  def raw(self, fn):
    self.items.append(fn)

  def word(self, w):
    self.items.append(lambda pc, L: w & M32)

  # encoders
  def r(self, f7, rs2, rs1, f3, rd, op):
    self.word((f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op)

  def i(self, imm, rs1, f3, rd, op):
    self.word(((imm & 0xFFF) << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op)

  def s(self, imm, rs2, rs1, f3):
    self.word((((imm >> 5) & 0x7F) << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | ((imm & 0x1F) << 7) | 0x23)

  def b(self, f3, rs1, rs2, label):
    def enc(pc, L):
      off = L[label] - pc
      return ((((off >> 12) & 1) << 31) | (((off >> 5) & 0x3F) << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) |
              (((off >> 1) & 0xF) << 8) | (((off >> 11) & 1) << 7) | 0x63)
    self.raw(enc)

  def jal(self, rd, label):
    def enc(pc, L):
      off = L[label] - pc
      return ((((off >> 20) & 1) << 31) | (((off >> 1) & 0x3FF) << 21) | (((off >> 11) & 1) << 20) |
              (((off >> 12) & 0xFF) << 12) | (rd << 7) | 0x6F)
    self.raw(enc)

  def jalr(self, rd, rs1, imm):
    self.i(imm, rs1, 0, rd, 0x67)

  def lui(self, rd, imm20):
    self.word(((imm20 & 0xFFFFF) << 12) | (rd << 7) | 0x37)

  def auipc(self, rd, imm20):
    self.word(((imm20 & 0xFFFFF) << 12) | (rd << 7) | 0x17)

  def li(self, rd, v):
    v &= M32
    lo = sx(v, 12)
    hi = ((v - lo) >> 12) & 0xFFFFF
    if hi:
      self.lui(rd, hi)
      if lo:
        self.i(lo, rd, 0, rd, 0x13)
    else:
      self.i(lo, 0, 0, rd, 0x13)

  def custom(self, f7, f3, rd, rs1, rs2=0):
    self.r(f7, rs2, rs1, f3, rd, 0x0B)

  def assemble(self):
    return [fn(4 * k, self.labels) for k, fn in enumerate(self.items)]


ALU_R = {"add": (0, 0), "sub": (0x20, 0), "sll": (0, 1), "slt": (0, 2), "sltu": (0, 3), "xor": (0, 4),
         "srl": (0, 5), "sra": (0x20, 5), "or": (0, 6), "and": (0, 7)}
MUL_R = {"mul": 0, "mulh": 1, "mulhsu": 2, "mulhu": 3, "div": 4, "divu": 5, "rem": 6, "remu": 7}
ALU_I = {"addi": 0, "slti": 2, "sltiu": 3, "xori": 4, "ori": 6, "andi": 7}
BR = {"beq": 0, "bne": 1, "blt": 4, "bge": 5, "bltu": 6, "bgeu": 7}
IRQLOG = -16  # irq handler writes here, via x0 (address 0xFFFFFFF0)
RESULTS = 0xA000
SCRATCH = 0xE000
X31BUF = 0xC800
IRQ_TRIG = 0x30000000  # testbench device: a write pulses the irq input lines with the written value
STUB_BITS = range(15, 32)


def build():
  rng = random.Random(2026)
  a = Asm()
  RP = 31  # results pointer
  off = [0]

  def store(rs):
    a.s(off[0], rs, RP, 2)
    off[0] += 4
    if off[0] >= 2040:
      a.i(off[0], RP, 0, RP, 0x13)
      off[0] = 0

  # reset vector and IRQ handler (PROGADDR_IRQ = 0x10)
  a.jal(0, "start")
  for _ in range(3):
    a.i(0, 0, 0, 0, 0x13)
  a.custom(1, 2, 2, 1)          # setq q2, x1     (save x1)
  a.custom(1, 2, 3, 2)          # setq q3, x2     (save x2)
  a.custom(0, 4, 1, 1)          # getq x1, q1     (pending irq bits)
  a.s(IRQLOG, 1, 0, 2)          # sw x1, IRQLOG(x0)
  a.i(2, 1, 7, 2, 0x13)         # andi x2, x1, 2  (irq 1: ebreak, ecall or illegal instruction)
  a.custom(0, 4, 1, 0)          # getq x1, q0     (return address)
  a.s(IRQLOG + 4, 1, 0, 2)      # sw x1, IRQLOG+4(x0)
  a.b(0, 2, 0, "irq_ret")       # beqz x2, irq_ret
  a.i(4, 1, 0, 1, 0x13)         # addi x1, x1, 4  (skip the offending instruction)
  a.custom(1, 2, 0, 1)          # setq q0, x1
  a.label("irq_ret")
  a.custom(0, 4, 2, 3)          # getq x2, q3     (restore x2)
  a.custom(0, 4, 1, 2)          # getq x1, q2     (restore x1)
  a.custom(2, 0, 0, 0)          # retirq
  a.label("start")
  # 0. x31 is the results pointer later, so test it first, stored through x30
  a.li(30, X31BUF)
  x31pats = [0x9E3779B1 * 31 & M32, 0x55555555, 0xAAAAAAAA, 0, M32] + [1 << k for k in range(32)] + [M32 ^ (1 << k) for k in range(32)]
  for k, v in enumerate(x31pats):
    a.li(31, v)
    a.s(4 * k, 31, 30, 2)
  a.li(RP, RESULTS)

  # 1. register file: unique value in every register, read all back; then the complement
  pats = [{r: ((r * 0x9E3779B1) ^ p ^ (r << 27)) & M32 for r in range(1, 31)} for p in (0, M32)]
  pats += [{r: (0x55555555 if r % 2 else 0xAAAAAAAA) for r in range(1, 31)},
           {r: (0xAAAAAAAA if r % 2 else 0x55555555) for r in range(1, 31)}]
  for vals in pats:
    for r, v in vals.items():
      a.li(r, v)
    for r in range(0, 31):
      store(r)
  # walking ones through x5
  for k in range(32):
    a.li(5, 1 << k)
    store(5)
  # q registers (part of the register file in this configuration): five patterns
  for pset in ([0x55555555] * 4, [0xAAAAAAAA] * 4, [0] * 4, [M32] * 4, [0xA5A50000 | q for q in range(4)],
               [0x0F0F0F0F, 0xF0F0F0F0, 0x33333333, 0xCCCCCCCC]):
    for q in range(4):
      a.li(5, pset[q])
      a.custom(1, 2, q, 5)        # setq qq, x5
    for q in range(4):
      a.custom(0, 4, 6, q)        # getq x6, qq
      store(6)

  # 2. ALU, register-register and immediate
  edge = [0, 1, M32, 0x80000000, 0x7FFFFFFF, 0x55555555, 0xAAAAAAAA, 0x0000FFFF]
  pairs = [(x, y) for x in edge for y in edge[::3]] + [(rng.getrandbits(32), rng.getrandbits(32)) for _ in range(12)]
  for x, y in pairs:
    a.li(10, x)
    a.li(11, y)
    for op, (f7, f3) in ALU_R.items():
      a.r(f7, 11, 10, f3, 12, 0x33)
      store(12)
  for x in edge + [rng.getrandbits(32) for _ in range(4)]:
    a.li(10, x)
    for op, f3 in ALU_I.items():
      for imm in (0, 1, -1, 0x7FF, -0x800, 0x555):
        a.i(imm, 10, f3, 12, 0x13)
        store(12)
    for sh in (0, 1, 7, 15, 16, 31):
      a.i(sh, 10, 1, 12, 0x13); store(12)
      a.i(sh, 10, 5, 12, 0x13); store(12)
      a.i(sh | 0x400, 10, 5, 12, 0x13); store(12)
  for imm in (0, 1, 0x80000, 0xFFFFF, 0x12345):
    a.lui(12, imm); store(12)
    a.auipc(12, imm); store(12)

  # 3. multiply and divide
  mpairs = [(x, y) for x in (0, 1, M32, 0x80000000, 0x7FFFFFFF, 3) for y in (0, 1, M32, 0x80000000, 7)]
  mpairs += [(rng.getrandbits(32), rng.getrandbits(32)) for _ in range(6)]
  for x, y in mpairs:
    a.li(10, x)
    a.li(11, y)
    for op, f3 in MUL_R.items():
      a.r(1, 11, 10, f3, 12, 0x33)
      store(12)

  # 4. branches, taken and not taken
  bvals = [0, 1, M32, 0x80000000, 0x7FFFFFFF]
  n = 0
  for x in bvals:
    for y in bvals:
      a.li(10, x)
      a.li(11, y)
      for op, f3 in BR.items():
        lab = f"b{n}"
        n += 1
        a.i(0, 0, 0, 12, 0x13)          # li x12, 0
        a.b(f3, 10, 11, lab)
        a.i(1, 12, 0, 12, 0x13)          # not taken: +1
        a.label(lab)
        a.i(2, 12, 0, 12, 0x13)          # always: +2
        store(12)

  # 5. jumps
  for k in range(4):
    a.jal(13, f"j{k}")
    a.i(0, 0, 0, 0, 0x13)
    a.label(f"j{k}")
    store(13)
  a.jal(13, "jr")
  a.label("jr_back")
  store(14)
  a.jal(0, "jr_done")
  a.label("jr")
  a.jalr(14, 13, 0)                       # x14 = link, jump back to jr_back
  a.label("jr_done")

  # 5b. far jumps: a return stub at every address 1<<k, so every upper PC bit becomes 1
  for k in STUB_BITS:
    a.extra[1 << k] = 0x00068767          # jalr x14, 0(x13): x14 = stub address + 4
    a.labels[f"stub{k}"] = 1 << k
  for k in STUB_BITS:
    a.li(10, 1 << k)
    a.jalr(13, 10, 0)                     # x13 = link
    store(13)
    store(14)                             # link written at the stub: carries the upper PC bits
  for k in range(15, 21):                 # long forward jal: large J immediates
    a.jal(13, f"stub{k}")
    store(13)
    store(14)
  for d in (1, 3, 9, 27, 81):             # backward jal: negative J immediates
    a.jal(0, f"bf{d}")
    a.label(f"bb{d}")
    a.i(d, 0, 0, 12, 0x13)
    store(12)
    a.jal(0, f"bd{d}")
    for _ in range(d):
      a.i(0, 0, 0, 0, 0x13)
    a.label(f"bf{d}")
    a.jal(0, f"bb{d}")
    a.label(f"bd{d}")

  # 6. loads and stores of every width and alignment
  a.li(20, SCRATCH)
  for k, v in enumerate([0x01234567, 0x89ABCDEF, 0xF0F0F0F0, 0x0F0F0F0F]):
    a.li(10, v)
    a.s(0, 10, 20, 2)
    for o in range(4):
      a.i(o, 20, 0, 12, 0x03); store(12)  # lb
      a.i(o, 20, 4, 12, 0x03); store(12)  # lbu
    for o in (0, 2):
      a.i(o, 20, 1, 12, 0x03); store(12)  # lh
      a.i(o, 20, 5, 12, 0x03); store(12)  # lhu
    a.i(0, 20, 2, 12, 0x03); store(12)    # lw
    a.li(11, 0x5A5A5A5A ^ v)
    for o in range(4):
      a.s(o, 11, 20, 0)                   # sb
      a.i(0, 20, 2, 12, 0x03); store(12)
    for o in (0, 2):
      a.s(o, 10, 20, 1)                   # sh
      a.i(0, 20, 2, 12, 0x03); store(12)
  a.label("iss_stop")                     # the ISS model stops here; what follows is timing dependent

  # 7. counters
  for csr in (0xC00, 0xC80, 0xC02, 0xC82):
    a.i(csr, 0, 2, 12, 0x73)              # csrrs x12, csr, x0
    store(12)

  # 8. interrupts: unmask, arm the timer, wait for the handler to log the timer irq
  a.li(5, 0)
  a.custom(3, 6, 6, 5)                    # maskirq x6, x5 (x6 = old mask)
  store(6)
  a.s(IRQLOG, 0, 0, 2)                    # clear the log
  a.li(5, 40)
  a.custom(5, 6, 7, 5)                    # timer x7, x5
  store(7)
  a.i(0, 0, 0, 8, 0x13)                   # x8 = loop count
  a.label("wait")
  a.i(1, 8, 0, 8, 0x13)
  a.i(IRQLOG, 0, 2, 9, 0x03)              # lw x9, IRQLOG(x0)
  a.b(0, 9, 0, "wait")                    # beqz x9, wait
  store(9)
  a.i(IRQLOG + 4, 0, 2, 9, 0x03)
  store(9)
  # 8b. every irq line through the trigger device (lines 0-2 are also internal sources)
  a.li(21, IRQ_TRIG)
  for k in range(32):
    a.s(IRQLOG, 0, 0, 2)
    a.li(5, 1 << k)
    a.s(0, 5, 21, 2)
    a.label(f"wi{k}")
    a.i(IRQLOG, 0, 2, 9, 0x03)
    a.b(0, 9, 0, f"wi{k}")
    store(9)
  # 8c. masking: a masked line must not interrupt until it is unmasked
  for k in (3, 9, 14, 20, 26, 31):
    a.s(IRQLOG, 0, 0, 2)
    a.li(5, 1 << k)
    a.custom(3, 6, 6, 5)                  # maskirq: mask only line k
    a.s(0, 5, 21, 2)                      # trigger line k
    for _ in range(8):
      a.i(0, 0, 0, 0, 0x13)
    a.i(IRQLOG, 0, 2, 9, 0x03)
    store(9)                              # must still be 0
    a.custom(3, 6, 6, 0)                  # unmask all
    a.label(f"wm{k}")
    a.i(IRQLOG, 0, 2, 9, 0x03)
    a.b(0, 9, 0, f"wm{k}")
    store(9)
  # 8e. traps as interrupts: illegal instruction (via the coprocessor time-out), ebreak, ecall
  for word in (0x00000000, 0xFFFFFFFF, 0x0200000B, 0x00100073, 0x00000073, 0x0000007F):
    a.s(IRQLOG, 0, 0, 2)
    a.word(word)
    a.i(IRQLOG, 0, 2, 9, 0x03)
    store(9)
    a.i(IRQLOG + 4, 0, 2, 9, 0x03)
    store(9)
  # 8d. timer register: load patterns and read them back (the timer instruction returns the old value)
  for v in [0x55555555, 0xAAAAAAAA, M32, 0x80000000] + [3 << k for k in range(0, 31, 2)]:
    a.li(5, v)
    a.custom(5, 6, 0, 5)                  # timer x0, x5
    a.custom(5, 6, 7, 0)                  # timer x7, x0 (read, stop)
    store(7)
  a.li(5, M32)
  a.custom(3, 6, 6, 5)                    # maskirq x6, ~0: mask all again
  store(6)

  # 9. end marker, then ebreak (masked, so it traps)
  a.li(12, 0x600DC0DE)
  store(12)
  a.word(0x00100073)
  return a


# ---------------------------------------------------------------- ISS (deterministic part only)
def iss(words, stop_pc, extra=None):
  mem = {4 * k: w for k, w in enumerate(words)}
  mem.update(extra or {})
  x = [0] * 32
  q = [0] * 4
  pc, stores = 0, []

  def ld(addr, n, signed):
    w = mem.get(addr & ~3, 0)
    v = (w >> (8 * (addr & 3))) & ((1 << (8 * n)) - 1)
    return sx(v, 8 * n) & M32 if signed else v

  def st(addr, n, v):
    w = mem.get(addr & ~3, 0)
    sh = 8 * (addr & 3)
    msk = ((1 << (8 * n)) - 1) << sh
    mem[addr & ~3] = (w & ~msk) | ((v << sh) & msk)
    stores.append((addr & ~3 & M32, mem[addr & ~3]))

  steps = 0
  while pc != stop_pc:
    steps += 1
    assert steps < 200000
    ins = mem[pc]
    op, rd, f3, rs1, rs2, f7 = ins & 0x7F, (ins >> 7) & 31, (ins >> 12) & 7, (ins >> 15) & 31, (ins >> 20) & 31, ins >> 25
    a, b = x[rs1], x[rs2]
    ii = sx(ins >> 20, 12)
    npc, res = pc + 4, None
    if op == 0x37:
      res = ins & 0xFFFFF000
    elif op == 0x17:
      res = (pc + (ins & 0xFFFFF000)) & M32
    elif op == 0x6F:
      off = sx((((ins >> 31) & 1) << 20) | (((ins >> 12) & 0xFF) << 12) | (((ins >> 20) & 1) << 11) | (((ins >> 21) & 0x3FF) << 1), 21)
      res, npc = pc + 4, (pc + off) & M32
    elif op == 0x67:
      res, npc = pc + 4, (a + ii) & ~1 & M32
    elif op == 0x63:
      off = sx((((ins >> 31) & 1) << 12) | (((ins >> 7) & 1) << 11) | (((ins >> 25) & 0x3F) << 5) | (((ins >> 8) & 0xF) << 1), 13)
      sa, sb = sx(a, 32), sx(b, 32)
      t = {0: a == b, 1: a != b, 4: sa < sb, 5: sa >= sb, 6: a < b, 7: a >= b}[f3]
      if t:
        npc = (pc + off) & M32
    elif op == 0x03:
      addr = (a + ii) & M32
      res = {0: ld(addr, 1, 1), 1: ld(addr, 2, 1), 2: ld(addr, 4, 0), 4: ld(addr, 1, 0), 5: ld(addr, 2, 0)}[f3]
    elif op == 0x23:
      addr = (a + sx(((ins >> 25) << 5) | ((ins >> 7) & 31), 12)) & M32
      st(addr, 1 << f3, b)
    elif op in (0x13, 0x33):
      if op == 0x33 and f7 == 1:
        sa, sb = sx(a, 32), sx(b, 32)
        if f3 == 0: res = (a * b) & M32
        elif f3 == 1: res = ((sa * sb) >> 32) & M32
        elif f3 == 2: res = ((sa * b) >> 32) & M32
        elif f3 == 3: res = ((a * b) >> 32) & M32
        elif f3 == 4: res = M32 if b == 0 else (a if (sa == -2**31 and sb == -1) else int(abs(sa) // abs(sb)) * (1 if (sa < 0) == (sb < 0) else -1)) & M32
        elif f3 == 5: res = M32 if b == 0 else a // b
        elif f3 == 6: res = a if b == 0 else (0 if (sa == -2**31 and sb == -1) else (abs(sa) % abs(sb)) * (-1 if sa < 0 else 1)) & M32
        else: res = a if b == 0 else a % b
      else:
        bb = b if op == 0x33 else ii & M32
        sh = bb & 31
        alt = (f7 == 0x20)
        if f3 == 0: res = (a - bb if (op == 0x33 and alt) else a + bb) & M32
        elif f3 == 1: res = (a << sh) & M32
        elif f3 == 2: res = int(sx(a, 32) < sx(bb, 32))
        elif f3 == 3: res = int(a < (bb & M32))
        elif f3 == 4: res = a ^ bb
        elif f3 == 5: res = (sx(a, 32) >> sh) & M32 if alt else a >> sh
        elif f3 == 6: res = a | bb
        else: res = a & bb
    elif op == 0x0B:
      if f7 == 1: q[rd] = a
      elif f7 == 0: res = q[rs1]
      else: raise ValueError("custom op in deterministic part")
    else:
      raise ValueError(hex(ins))
    if res is not None and rd:
      x[rd] = res & M32
    pc = npc
  return stores


if __name__ == "__main__":
  a = build()
  w = a.assemble()
  print(len(w), "instructions; iss_stop at", hex(a.labels["iss_stop"]))
  s = iss(w, a.labels["iss_stop"], a.extra)
  print(len(s), "stores in the deterministic part")
