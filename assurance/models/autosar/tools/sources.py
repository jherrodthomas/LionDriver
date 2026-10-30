#!/usr/bin/env python3
"""Readers for the sources the AUTOSAR description is generated from. Standard library only.

  vehicle register   docs/liondriver/vehicles/vehicles.yaml        reference configuration CFG-001 and its opendbc platform
  opendbc platform   opendbc_repo/opendbc/car/toyota/values.py     which DBC the platform uses
  DBC                opendbc_repo/opendbc/dbc/generator/toyota/    frames and signals, imports resolved as opendbc's generator does
  safety mode        opendbc_repo/opendbc/safety/modes/toyota.h    TX allow-list, forwarding blocks, RX checks, timeouts, rate checks
  WP-S-05            assurance/03-system/WP-S-05-hsi-specification.md   §4.2 control requests, §5 RX set
  trace data         assurance/trace/items/tsr.yaml, aou.yaml      the TSR and AOU identifiers cited

Every reader fails with SourceError when its source no longer has the shape it expects, so that a change upstream
shows up as a failing CI job, not as a silently thinner description.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
OPENDBC = REPO / "opendbc_repo" / "opendbc"
VEHICLES = REPO / "docs" / "liondriver" / "vehicles" / "vehicles.yaml"
WP_S05 = REPO / "assurance" / "03-system" / "WP-S-05-hsi-specification.md"
TRACE_ITEMS = REPO / "assurance" / "trace" / "items"


class SourceError(Exception):
  pass


def rel(p: Path) -> str:
  return p.resolve().relative_to(REPO).as_posix()


# ------------------------------------------------------------------ vehicle register and platform

@dataclass
class Reference:
  config_id: str
  codename: str
  platform: str
  safety_mode: str
  adas: str
  dbc: str           # DBC template name, without "_generated"


def reference(config_id: str = "CFG-001") -> Reference:
  text = VEHICLES.read_text(encoding="utf-8")
  m = re.search(rf"^  - id: {re.escape(config_id)}\n((?:    .*\n)+)", text, re.M)
  if not m:
    raise SourceError(f"{rel(VEHICLES)}: no configuration {config_id}")
  block = m.group(1)

  def field_(name: str) -> str:
    f = re.search(rf"^    {name}: (.+)$", block, re.M)
    if not f:
      raise SourceError(f"{rel(VEHICLES)}: {config_id} has no {name}")
    return f.group(1).strip()

  platform = field_("opendbc_platform")
  values = (OPENDBC / "car" / "toyota" / "values.py").read_text(encoding="utf-8")
  pm = re.search(rf"^\s+{platform} = (\w+)PlatformConfig\(", values, re.M)
  if not pm:
    raise SourceError(f"values.py: no platform {platform}")
  cm = re.search(rf"^class {pm.group(1)}PlatformConfig\(.*?\n(.*?)(?=^class |\Z)", values, re.M | re.S)
  dm = cm and re.search(r"dbc_dict\('(\w+)_generated'", cm.group(1))
  if not dm:
    raise SourceError(f"values.py: no DBC for {pm.group(1)}PlatformConfig")
  return Reference(config_id, field_("codename"), platform, field_("safety_mode"), field_("adas"), dm.group(1))


# ------------------------------------------------------------------ DBC

@dataclass
class Signal:
  name: str
  start: int            # DBC start bit (Intel: LSB; Motorola: MSB, sawtooth numbering)
  length: int
  little_endian: bool
  signed: bool
  factor: float
  offset: float
  minimum: float
  maximum: float
  unit: str

  def lsb_position(self) -> int:
    """Position of the least significant bit in AUTOSAR's linear numbering (byte * 8 + bit, bit 0 = LSB of byte 0),
    which is what ISignalToIPduMapping.startPosition gives for both byte orders."""
    if self.little_endian:
      return self.start
    pos = self.start
    for _ in range(self.length - 1):
      pos = pos + 15 if pos % 8 == 0 else pos - 1
    return pos


@dataclass
class Message:
  address: int
  name: str
  length: int
  transmitter: str
  source: str           # DBC file it is defined in
  signals: list[Signal] = field(default_factory=list)

  def signal(self, name: str) -> Signal | None:
    return next((s for s in self.signals if s.name == name), None)


_BO = re.compile(r"^BO_ (\d+) (\w+)\s*: (\d+) (\w+)")
_SG = re.compile(r'^ SG_ (\w+)\s*(M|m\d+)?\s*: (\d+)\|(\d+)@([01])([+-]) \(([^,]+),([^)]+)\) \[([^|]*)\|([^\]]*)\] "([^"]*)"')
_IMPORT = re.compile(r'^CM_ "IMPORT (.*?)";', re.M)


def read_dbc(name: str) -> dict[int, Message]:
  """The DBC as opendbc's generator builds `<name>_generated.dbc`: the imported files first, then the file itself."""
  src_dir = OPENDBC / "dbc" / "generator" / "toyota"
  main = src_dir / f"{name}.dbc"
  if not main.exists():
    raise SourceError(f"no DBC template {rel(main)}")
  files = [src_dir / f for f in _IMPORT.findall(main.read_text(encoding="utf-8"))] + [main]
  msgs: dict[int, Message] = {}
  for f in files:
    cur = None
    for line in f.read_text(encoding="utf-8").splitlines():
      if m := _BO.match(line):
        addr = int(m.group(1))
        if addr in msgs:
          raise SourceError(f"{rel(f)}: frame {addr:#x} defined twice")
        cur = msgs[addr] = Message(addr, m.group(2), int(m.group(3)), m.group(4), rel(f))
      elif line.startswith(" SG_"):
        m = _SG.match(line)
        if not m or cur is None:
          raise SourceError(f"{rel(f)}: unreadable signal line {line!r}")
        if m.group(2):
          raise SourceError(f"{rel(f)}: multiplexed signal {m.group(1)} is not supported")
        cur.signals.append(Signal(m.group(1), int(m.group(3)), int(m.group(4)), m.group(5) == "1", m.group(6) == "-",
                                  float(m.group(7)), float(m.group(8)), float(m.group(9) or 0), float(m.group(10) or 0),
                                  m.group(11)))
      elif not line.strip():
        cur = None
  return msgs


# ------------------------------------------------------------------ the Toyota safety mode

@dataclass
class TxMsg:
  address: int
  bus: int
  length: int
  check_relay: bool


@dataclass
class RxCheck:
  address: int
  bus: int
  length: int
  frequency: int
  check_checksum: bool
  check_counter: bool
  check_quality: bool


@dataclass
class SafetyMode:
  path: str
  defines: tuple[str, ...]
  tx: list[TxMsg]
  rx: list[RxCheck]
  rx_timeout_periods: int
  tx_rate: dict[int, tuple[int, int, str]]      # address -> (frequency Hz, burst, comment)
  tx_arrival: dict[int, int]                     # address -> timeout µs

  def blocked_from_camera(self) -> list[int]:
    """Addresses the forwarding hook never copies from bus 2 to bus 0 (safety.h safety_fwd_hook: a TX message on
    bus 0 with check_relay is statically blocked)."""
    return sorted({t.address for t in self.tx if t.bus == 0 and t.check_relay})


def _preprocess(text: str, defined: set[str]) -> str:
  out, stack = [], []
  for line in text.splitlines():
    s = line.strip()
    if m := re.match(r"#\s*ifn?def\s+(\w+)", s):
      cond = (m.group(1) in defined) != s.startswith("#ifndef")
      stack.append([cond, cond])
      continue
    if re.match(r"#\s*(if|elif)\b", s):
      raise SourceError(f"toyota.h: unsupported conditional {s!r}")
    if re.match(r"#\s*else\b", s):
      stack[-1][1] = not stack[-1][0]
      continue
    if re.match(r"#\s*endif\b", s):
      stack.pop()
      continue
    if all(active for _, active in stack):
      out.append(line)
  return "\n".join(out)


def _macros(text: str) -> dict[str, tuple[list[str], str]]:
  joined = re.sub(r"\\\n", " ", text)
  macros = {}
  for m in re.finditer(r"^#define (\w+)(\(([^)]*)\))?(.*)$", joined, re.M):
    params = [p.strip() for p in (m.group(3) or "").split(",") if p.strip()]
    macros[m.group(1)] = (params, re.sub(r"/\*.*?\*/", " ", m.group(4)))
  return macros


def _expand(body: str, macros: dict, depth: int = 0) -> str:
  if depth > 10:
    raise SourceError("toyota.h: macro expansion too deep")

  def sub(m: re.Match) -> str:
    name, args = m.group(1), m.group(3)
    params, mbody = macros[name]
    if params:
      vals = [a.strip() for a in (args or "").split(",")]
      for p, v in zip(params, vals):
        mbody = re.sub(rf"\b{p}\b", v, mbody)
    return _expand(mbody, macros, depth + 1)

  names = "|".join(sorted((re.escape(n) for n in macros), key=len, reverse=True))
  return re.sub(rf"\b({names})\b(\(([^)]*)\))?", sub, body) if names else body


def _flag(text: str, name: str) -> bool:
  m = re.search(rf"\.{name}\s*=\s*([^,}}]+)", text)
  if not m:
    return False
  v = m.group(1).replace(" ", "")
  table = {"true": True, "false": False, "!(true)": False, "!(false)": True}
  if v not in table:
    raise SourceError(f"toyota.h: cannot evaluate .{name} = {v}")
  return table[v]


def safety_mode(*, secoc: bool = False, lta: bool = False, alt_brake: bool = False,
                stock_longitudinal: bool = False) -> SafetyMode:
  """The Toyota safety mode as built for the LionDriver reference (LIONDRIVER_REFERENCE defined, ALLOW_DEBUG not),
  in the configuration the flags name. Only the reference configuration (all flags false) is used."""
  path = OPENDBC / "safety" / "modes" / "toyota.h"
  defines = ("LIONDRIVER_REFERENCE",)
  text = re.sub(r"//[^\n]*", "", _preprocess(path.read_text(encoding="utf-8"), set(defines)))
  macros = _macros(text)
  init = re.search(r"static safety_config toyota_init\(.*?\n}\n", text, re.S)
  if not init:
    raise SourceError("toyota.h: no toyota_init")
  init = init.group(0)

  tx_name = ("TOYOTA_SECOC" if secoc else "TOYOTA") + ("_TX_MSGS" if stock_longitudinal else "_LONG_TX_MSGS")
  tx_decl = re.search(rf"static const CanMsg {tx_name}\[\] = \{{(.*?)\}};", init, re.S)
  if not tx_decl or f"SET_TX_MSGS({tx_name}, ret)" not in init:
    raise SourceError(f"toyota.h: toyota_init no longer selects {tx_name}")
  tx_text = _expand(tx_decl.group(1), macros)
  tx = [TxMsg(int(a, 16), int(b), int(n), r == "true") for a, b, n, r in
        re.findall(r"\{\s*(0x[0-9A-Fa-f]+),\s*(\d+),\s*(\d+),\s*\.check_relay\s*=\s*(true|false)\s*\}", tx_text)]

  if secoc or lta or alt_brake:
    raise SourceError("only the reference configuration (no SecOC, no LTA, no alternative brake) is described")
  rx_decl = re.search(r"static RxCheck toyota_lka_rx_checks\[\] = \{(.*?)\};", init, re.S)
  if not rx_decl or "SET_RX_CHECKS(toyota_lka_rx_checks, ret)" not in init:
    raise SourceError("toyota.h: toyota_init no longer selects toyota_lka_rx_checks")
  rx_text = _expand(rx_decl.group(1), macros)
  rx = []
  for m in re.finditer(r"\{\.msg = \{\{\s*(0x[0-9A-Fa-f]+),\s*(\d+),\s*(\d+),\s*(\d+)U([^}]*)\}", rx_text):
    rest = m.group(5)
    rx.append(RxCheck(int(m.group(1), 16), int(m.group(2)), int(m.group(3)), int(m.group(4)),
                      not _flag(rest, "ignore_checksum"), not _flag(rest, "ignore_counter"),
                      not _flag(rest, "ignore_quality_flag")))
  if not tx or not rx:
    raise SourceError("toyota.h: empty TX or RX set")

  periods = re.search(r"#define TOYOTA_RX_TIMEOUT_PERIODS (\d+)U", text)
  if not periods or "ret.rx_timeout_periods = TOYOTA_RX_TIMEOUT_PERIODS" not in init:
    raise SourceError("toyota.h: no RX timeout in periods")
  raw = path.read_text(encoding="utf-8")   # comments kept, for the rate-check notes
  rate = {int(a, 16): (int(f), int(b), c.strip()) for a, f, b, c in re.findall(
    r"\{\.addr = (0x[0-9A-Fa-f]+)U, \.bus = 0U, \.frequency = (\d+)U, \.burst = (\d+)U\},\s*//\s*([^\n]*)", raw)}
  arrival = {int(a, 16): int(t) for a, t in re.findall(
    r"\{\.addr = (0x[0-9A-Fa-f]+)U, \.bus = 0U, \.timeout_us = (\d+)U", init)}
  if not stock_longitudinal and "toyota_stock_longitudinal ? 1 : 2" not in init:
    raise SourceError("toyota.h: TX arrival check count changed")
  return SafetyMode(rel(path), defines, tx, rx, int(periods.group(1)), rate, arrival)


# ------------------------------------------------------------------ WP-S-05

def _md_table_after(text: str, heading: str) -> list[list[str]]:
  i = text.find(heading)
  if i < 0:
    raise SourceError(f"WP-S-05: no section {heading!r}")
  rows, started = [], False
  for line in text[i:].splitlines()[1:]:
    if line.startswith("|"):
      started = True
      cells = [c.strip() for c in line.strip().strip("|").split("|")]
      if not set("".join(cells)) <= set("-: "):
        rows.append(cells)
    elif started:
      break
  return rows


@dataclass
class ControlRequest:
  code: int
  function: str
  effect: str
  gating: str
  required: str
  tsr: list[str]


def control_requests() -> list[ControlRequest]:
  """WP-S-05 §4.2: one entry per request code; a row naming several codes gives one entry each."""
  rows = _md_table_after(WP_S05.read_text(encoding="utf-8"), "### 4.2 Control requests")
  if not rows or rows[0][0] != "Req":
    raise SourceError("WP-S-05 §4.2: table header changed")
  out = []
  for cells in rows[1:]:
    req, func, effect, gating, required, tsr = cells
    plain = lambda s: re.sub(r"\*\*|`", "", s)  # noqa: E731
    tsrs = [f"TSR-{n}" for n in re.findall(r"\b(\d{3})\b", tsr)]
    for code in re.findall(r"0x([0-9a-f]{2})", req):
      out.append(ControlRequest(int(code, 16), plain(func), plain(effect), plain(gating), plain(required), tsrs))
  if len(out) < 20:
    raise SourceError("WP-S-05 §4.2: fewer requests than expected")
  return out


def rx_set_table() -> dict[int, str]:
  """WP-S-05 §5, 'Reference-configuration RX set used by the envelope': address -> envelope use."""
  rows = _md_table_after(WP_S05.read_text(encoding="utf-8"), "Reference-configuration RX set used by the envelope")
  out = {}
  for cells in rows[1:]:
    for a in re.findall(r"0x([0-9A-Fa-f]+)", cells[0]):
      out[int(a, 16)] = cells[5]
  return out


# ------------------------------------------------------------------ trace data

def trace_ids(kind: str) -> set[str]:
  return set(re.findall(r"^- id: (\S+)", (TRACE_ITEMS / f"{kind}.yaml").read_text(encoding="utf-8"), re.M))


def opendbc_commit() -> str:
  """The opendbc pin recorded in the superproject (the gitlink), read without git."""
  head = OPENDBC.parent / ".git"
  if head.is_file():   # a submodule checkout: .git points at the module directory
    gitdir = (OPENDBC.parent / head.read_text(encoding="utf-8").split(":", 1)[1].strip()).resolve()
    h = (gitdir / "HEAD").read_text(encoding="utf-8").strip()
    if re.fullmatch(r"[0-9a-f]{40}", h):
      return h
  raise SourceError("cannot read the opendbc commit; check out the submodule (git submodule update --init opendbc_repo)")
