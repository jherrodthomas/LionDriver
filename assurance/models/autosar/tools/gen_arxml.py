#!/usr/bin/env python3
"""Generate the AUTOSAR description of LionDriver (ARXML) from the sources of truth.

  SysML model        assurance/models/sysml/model/           elements E-01..E-05, the cereal services (DataFlow), the
                                                               external ECUs, the HSI signals S-nn and the hardware/software
                                                               responsibilities HSI-nn of V-19/V-20 (generated from WP-S-05 §11)
  WP-S-05            §4.2 control requests (SoC -> safety MCU), §5 RX set (cross-checked against toyota.h)
  opendbc            the DBC of the reference platform (frames, signals, layout); the Toyota safety mode (TX allow-list,
                     forwarding blocks, RX checks and their timeout, rate and arrival checks)
  trace data         every TSR and AOU cited must exist in assurance/trace/items

What it writes:

  generated/liondriver-reference.arxml   AUTOSAR Classic R22-11 (schema AUTOSAR_00051), one file
  generated/summary.md                   what the file holds, per element, with where each came from

The file DESCRIBES the existing system in AUTOSAR terms for OEM/Tier-1 integration. Neither the panda firmware
(bare-metal STM32) nor openpilot (Linux processes) is an AUTOSAR stack, and nothing here is evidence (README).

    python3 tools/gen_arxml.py            # write both files
    python3 tools/gen_arxml.py --check    # fail if either differs from what the sources give today

Needs the opendbc submodule (git submodule update --init opendbc_repo). Standard library only; output deterministic.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sources as src  # noqa: E402

ROOT = HERE.parent
REPO = src.REPO
sys.path.insert(0, str(REPO / "assurance" / "models" / "sysml" / "tools"))
import sysml_lite  # noqa: E402

OUT = ROOT / "generated" / "liondriver-reference.arxml"
SUMMARY = ROOT / "generated" / "summary.md"

RELEASE = "R22-11"
SCHEMA = "AUTOSAR_00051.xsd"
NS = "http://autosar.org/schema/r4.0"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
TOP = "LionDriver"
NATURE = ("Description of the existing LionDriver system in AUTOSAR terms, for OEM/Tier-1 integration. Neither the "
          "panda safety firmware (bare-metal STM32) nor openpilot (Linux processes) is an AUTOSAR stack. This file "
          "is not an AUTOSAR implementation and not a compliance claim; it carries no evidence credit.")

# The reference configuration's safety-mode flags (toyota_init). The item sends ACC_CONTROL (WP-S-05 §11.1 S-03),
# so openpilot longitudinal: not stock longitudinal; camera ACC TSS2 without SecOC, LTA or the alternative brake.
CONFIG_FLAGS = dict(secoc=False, lta=False, alt_brake=False, stock_longitudinal=False)

# Who is at the other end of each vehicle frame. The DBC names no real transmitter (XXX/DSU), so the peer comes
# from what the SysML model's external element says it exchanges (Architecture.sysml, OperationalContext docs) and,
# for the PCS frames, WP-S-05 §12.3 H4 ("the brake ECU checks them").
PEERS = {
  0x0AA: ("absVsc", "wheel speeds (absVsc: 'wheel speeds and brake-pedal state')"),
  0x0B4: ("absVsc", "vehicle speed (absVsc)"),
  0x226: ("absVsc", "brake-pedal state (absVsc)"),
  0x260: ("EXT-EPS", "driver and EPS torque (EXT-EPS: 'reports driver torque, EPS torque and LKA state')"),
  0x262: ("EXT-EPS", "LKA state (EXT-EPS)"),
  0x2E4: ("EXT-EPS", "LKA torque request (EXT-EPS: 'receives LKA torque requests')"),
  0x191: ("EXT-EPS", "LTA request (EXT-EPS)"),
  0x343: ("EXT-PCM", "ACC acceleration (EXT-PCM: 'ACC acceleration, permit-braking')"),
  0x1D2: ("EXT-PCM", "cruise state (EXT-PCM: 'cruise state')"),
  0x1D3: ("EXT-PCM", "cruise main and faults (EXT-PCM)"),
  0x412: ("EXT-CLU", "LKA HUD (EXT-CLU: 'LKA HUD')"),
  0x411: ("EXT-CLU", "PCS HUD (EXT-CLU)"),
  0x283: ("absVsc", "PCS brake request (WP-S-05 §12.3 H4: the brake ECU checks it)"),
  0x344: ("absVsc", "PCS brake triggers (WP-S-05 §12.3 H4)"),
}
EXT_SWC = {"EXT-EPS": "Ext_EPS", "EXT-PCM": "Ext_PCM", "absVsc": "Ext_AbsVsc", "EXT-CLU": "Ext_Cluster",
           "forwardCamera": "Ext_ForwardCamera"}

# HSI responsibilities (V-20) and the AUTOSAR Classic basic-software module that does the same job on an AUTOSAR ECU.
# An analogy for the reader, not a claim that the panda has such a module.
BSW_ANALOGUE = {
  "HSI-01": "Spi driver (MCAL)", "HSI-02": "Com/Dcm-like request handling (no AUTOSAR module)",
  "HSI-03": "PduR/CanIf routing", "HSI-04": "Can driver, CanIf, CanSM (bus-off)", "HSI-05": "Dio driver",
  "HSI-06": "Adc driver", "HSI-07": "EcuM wake-up / Dio", "HSI-08": "external reset (no AUTOSAR module)",
  "HSI-09": "Wdg driver, WdgIf, WdgM", "HSI-10": "Dem, Det", "HSI-11": "Dio, I2c (complex driver)",
  "HSI-12": "Fls, bootloader (outside AUTOSAR)", "HSI-13": "Adc driver", "HSI-14": "Os memory protection, MemIf/ECC",
}

DESCRIPTION_VERSION = "0.1.0"
DESCRIPTION_STATUS = "descriptive; generated; I0 (AI-authored, Claude); not reviewed"


# ====================================================================== small XML builder

def E(tag: str, *children, text: str | None = None, **attrs) -> ET.Element:
  el = ET.Element(tag, {k.replace("_", "-"): v for k, v in attrs.items()})
  if text is not None:
    el.text = text
  for c in children:
    if c is not None:
      el.append(c)
  return el


def ident(s: str) -> str:
  s = re.sub(r"[^A-Za-z0-9_]", "_", s)
  s = re.sub(r"_+", "_", s).strip("_")
  if not s or not s[0].isalpha():
    s = "X" + s
  return s[:128]


def desc(text: str | None):
  return E("DESC", E("L-2", text=text, L="EN")) if text else None


def longname(text: str | None):
  return E("LONG-NAME", E("L-4", text=text, L="EN")) if text else None


def sdgs(groups: list[tuple[str, list[tuple[str, str]]]]):
  """ADMIN-DATA with special data groups: [(gid, [(sd gid, value), ...]), ...]. The AUTOSAR way to carry data the
  meta-model has no place for; here the traceability to the work products."""
  groups = [(g, [(k, v) for k, v in sds if v not in (None, "")]) for g, sds in groups]
  groups = [(g, sds) for g, sds in groups if sds]
  if not groups:
    return None
  return E("ADMIN-DATA", E("SDGS", *[E("SDG", *[E("SD", text=str(v), GID=k) for k, v in sds], GID=g)
                                     for g, sds in groups]))


def ref(tag: str, dest: str, path: str) -> ET.Element:
  return E(tag, text=path, DEST=dest)


def identifiable(tag: str, name: str, *children, long_name=None, description=None, category=None, admin=None):
  return E(tag, E("SHORT-NAME", text=name), longname(long_name), desc(description),
           E("CATEGORY", text=category) if category else None, admin, *children)


def expand_names(doc: str) -> str:
  """WHEEL_SPEED_FR/FL/RR/RL -> WHEEL_SPEED_FR WHEEL_SPEED_FL WHEEL_SPEED_RR WHEEL_SPEED_RL."""
  def sub(m: re.Match) -> str:
    return " ".join(f"{m.group(1)}_{x}" for x in [m.group(2)] + m.group(3).strip("/").split("/"))
  return re.sub(r"\b([A-Z][A-Z0-9_]*)_([A-Z0-9]+)((?:/[A-Z0-9]+)+)\b", sub, doc)


def request_codes(doc: str) -> set[int]:
  """Control request codes a signal names: 0xc5, 0xd1 and ranges written 0xe5…0xe8."""
  codes = {int(x, 16) for x in re.findall(r"0x([0-9a-f]{2})\b", doc)}
  for lo, hi in re.findall(r"0x([0-9a-f]{2})\s*(?:…|\.\.\.)\s*0x([0-9a-f]{2})", doc):
    codes |= set(range(int(lo, 16), int(hi, 16) + 1))
  return codes


def fmt(v: float) -> str:
  return repr(int(v)) if float(v).is_integer() else repr(float(v))


def seconds(v: float) -> str:
  return f"{v:.6f}".rstrip("0").rstrip(".")


class Package:
  def __init__(self, path: str):
    self.path = path
    self.elements: list[ET.Element] = []

  def add(self, el: ET.Element) -> str:
    self.elements.append(el)
    return f"{self.path}/{el.findtext('SHORT-NAME')}"


# ====================================================================== the description

@dataclass
class Port:
  name: str
  direction: str          # P or R
  kind: str               # SENDER-RECEIVER-INTERFACE or CLIENT-SERVER-INTERFACE
  interface: str          # path
  doc: str = ""
  trace: list = field(default_factory=list)


@dataclass
class Swc:
  name: str
  kind: str               # APPLICATION-SW-COMPONENT-TYPE, COMPLEX-DEVICE-DRIVER-SW-COMPONENT-TYPE, COMPOSITION-SW-COMPONENT-TYPE
  long_name: str
  doc: str
  trace: list
  ports: dict[str, Port] = field(default_factory=dict)
  ecu: str | None = None
  # compositions only
  parts: list[tuple[str, "Swc"]] = field(default_factory=list)        # (prototype name, type)
  assemblies: list[tuple[str, str, str, str]] = field(default_factory=list)   # (provider proto, P port, requester proto, R port)
  delegations: list[tuple[str, str, str]] = field(default_factory=list)       # (inner proto, inner port, outer port)

  def port(self, name: str, direction: str, kind: str, interface: str, doc: str = "", trace=None) -> Port:
    p = self.ports.get(name)
    if p:
      if (p.direction, p.interface) != (direction, interface):
        raise src.SourceError(f"{self.name}: port {name} used twice with different meanings")
      return p
    p = self.ports[name] = Port(name, direction, kind, interface, doc, trace or [])
    return p

  def proto(self, name: str) -> "Swc":
    return next(t for n, t in self.parts if n == name)


class Builder:
  def __init__(self):
    self.m = sysml_lite.load()
    self.ref = src.reference()
    self.dbc = src.read_dbc(self.ref.dbc)
    self.mode = src.safety_mode(**CONFIG_FLAGS)
    self.requests = src.control_requests()
    self.tsr_ids = src.trace_ids("tsr")
    self.aou_ids = src.trace_ids("aou")
    self.opendbc = src.opendbc_commit()
    self.used_signals: dict[str, list[str]] = defaultdict(list)    # S-nn -> where it was placed
    self.used_hsi: set[str] = set()
    self.cited: set[str] = set()
    p = f"/{TOP}"
    self.pk = {k: Package(f"{p}/{k}") for k in (
      "BaseTypes", "ImplementationDataTypes", "Units", "CompuMethods", "PortInterfaces", "SwComponentTypes",
      "SystemSignals", "Communication", "EcuInstances", "System")}
    self.summary: list[str] = []

  # ------------------------------------------------------------------ helpers
  def trace_sdg(self, *, wp: str = "", clause: str = "", paths=(), tsr=(), aou=(), signals=(), hsi=(), integrity="",
                sysml="", extra=()):
    for t in tsr:
      if t.startswith("TSR-") and re.fullmatch(r"TSR-\d{3}[a-z]?", t):
        if t not in self.tsr_ids:
          raise src.SourceError(f"{t} is cited but not in assurance/trace/items/tsr.yaml")
        self.cited.add(t)
    for a in aou:
      if a not in self.aou_ids:
        raise src.SourceError(f"{a} is cited but not in assurance/trace/items/aou.yaml")
      self.cited.add(a)
    source = [("workProduct", wp), ("clause", clause), ("sysmlElement", sysml)] + [("path", x) for x in paths]
    tr = ([("integrity", integrity)] + [("signal", s) for s in signals] + [("hsi", h) for h in hsi]
          + [("tsr", t) for t in tsr] + [("aou", a) for a in aou] + list(extra))
    return [("LionDriver.Source", source), ("LionDriver.Trace", tr)]

  # ------------------------------------------------------------------ data types
  def data_types(self):
    bt, idt = self.pk["BaseTypes"], self.pk["ImplementationDataTypes"]
    self.base: dict[str, str] = {}
    self.idt: dict[str, str] = {}
    specs = [("boolean", 8, "BOOLEAN", "boolean"), ("uint8", 8, "NONE", "uint8"), ("uint16", 16, "NONE", "uint16"),
             ("uint32", 32, "NONE", "uint32"), ("uint64", 64, "NONE", "uint64"), ("sint8", 8, "2C", "sint8"),
             ("sint16", 16, "2C", "sint16"), ("sint32", 32, "2C", "sint32")]
    for name, size, enc, native in specs:
      self.base[name] = bt.add(identifiable("SW-BASE-TYPE", name, E("BASE-TYPE-SIZE", text=str(size)),
                                            E("BASE-TYPE-ENCODING", text=enc), E("NATIVE-DECLARATION", text=native),
                                            category="FIXED_LENGTH"))
      self.idt[name] = idt.add(identifiable("IMPLEMENTATION-DATA-TYPE", name, self._props(base=self.base[name]),
                                            category="VALUE"))
    for name, size, doc in (
        ("ByteBuffer", 65535, "Opaque bytes of variable length: a serialised cereal (Cap'n Proto) message, or the "
                              "response of a control request. The bound is the 16-bit length field of a control "
                              "request (WP-S-05 §4.2), used as an upper bound for the description only"),
        ("CanPacket", 70, "One CAN packet of the SPI stream (WP-S-05 §4.3): 6 header bytes and up to 64 payload "
                          "bytes, with the 8-bit XOR checksum in byte 5")):
      self.idt[name] = idt.add(identifiable(
        "IMPLEMENTATION-DATA-TYPE", name,
        E("SUB-ELEMENTS", identifiable(
          "IMPLEMENTATION-DATA-TYPE-ELEMENT", "byte", E("ARRAY-SIZE", text=str(size)),
          E("ARRAY-SIZE-SEMANTICS", text="VARIABLE-SIZE"),
          self._props(idt=self.idt["uint8"]), category="TYPE_REFERENCE")),
        description=doc, category="ARRAY"))

  def _props(self, *, base=None, compu=None, idt=None, unit=None, tag="SW-DATA-DEF-PROPS"):
    kids = [ref("BASE-TYPE-REF", "SW-BASE-TYPE", base) if base else None,
            ref("COMPU-METHOD-REF", "COMPU-METHOD", compu) if compu else None,
            ref("IMPLEMENTATION-DATA-TYPE-REF", "IMPLEMENTATION-DATA-TYPE", idt) if idt else None,
            ref("UNIT-REF", "UNIT", unit) if unit else None]
    return E(tag, E("SW-DATA-DEF-PROPS-VARIANTS", E("SW-DATA-DEF-PROPS-CONDITIONAL", *kids)))

  def type_for(self, s: src.Signal) -> str:
    if s.length == 1 and not s.signed:
      return "boolean"
    for n in (8, 16, 32, 64):
      if s.length <= n:
        return f"{'sint' if s.signed else 'uint'}{n}" if not (s.signed and n == 64) else "sint32"
    raise src.SourceError(f"signal {s.name} longer than 64 bits")

  def unit(self, u: str) -> str | None:
    if not u:
      return None
    name = ident(u.replace("/", "_per_").replace("%", "percent").replace("^2", "2").replace("°", "deg"))
    path = f"{self.pk['Units'].path}/{name}"
    if not any(e.findtext("SHORT-NAME") == name for e in self.pk["Units"].elements):
      self.pk["Units"].add(identifiable("UNIT", name, E("DISPLAY-NAME", text=u)))
    return path

  def compu(self, frame: str, s: src.Signal) -> str | None:
    if s.factor == 1 and s.offset == 0 and not s.unit:
      return None
    name = ident(f"{frame}_{s.name}")
    unit = self.unit(s.unit)
    return self.pk["CompuMethods"].add(identifiable(
      "COMPU-METHOD", name, ref("UNIT-REF", "UNIT", unit) if unit else None,
      E("COMPU-INTERNAL-TO-PHYS", E("COMPU-SCALES", E("COMPU-SCALE", E("COMPU-RATIONAL-COEFFS",
        E("COMPU-NUMERATOR", E("V", text=fmt(s.offset)), E("V", text=fmt(s.factor))),
        E("COMPU-DENOMINATOR", E("V", text="1")))))),
      category="LINEAR", description="phys = offset + factor × raw, from the DBC"))

  # ------------------------------------------------------------------ CAN frames on the vehicle side
  def frames(self):
    """Which frames are described, on which bus, sent and received by whom."""
    mode, dbc = self.mode, self.dbc
    tx = {t.address for t in mode.tx if t.bus == 0}
    rx = {r.address: r for r in mode.rx if r.bus == 0}
    blocked = mode.blocked_from_camera()

    # WP-S-05 §5 RX set and toyota.h must agree (the WP names the code as its source)
    table = src.rx_set_table()
    proposed = {a for a, use in table.items() if use.startswith("proposed")}
    if set(table) - proposed != set(rx):
      raise src.SourceError(f"WP-S-05 §5 RX set {sorted(map(hex, set(table) - proposed))} differs from toyota.h "
                            f"{sorted(map(hex, rx))}")

    # the frames of the vehicle CAN signals S-01..S-15
    sig_frames: dict[int, list[str]] = defaultdict(list)
    for sid, rec in self.m.signals.items():
      if rec.values.get("group") != "Vehicle CAN signals":
        continue
      for a in re.findall(r"0x([0-9A-Fa-f]+)", rec.doc):
        sig_frames[int(a, 16)].append(sid)
    camera_fwd = {a for a, sids in sig_frames.items() if any("camera" in self.m.signals[s].values["direction"]
                                                            for s in sids)}

    # not sent by the reference car although allowed: the rate-check note in toyota.h says so
    not_sent = {a for a, (_, _, note) in mode.tx_rate.items() if "not sent" in note or " only" in note}
    self.not_sent = {a: mode.tx_rate[a][2] for a in not_sent}

    self.bus0: dict[int, dict] = {}
    self.bus2: dict[int, dict] = {}
    self.skipped: dict[int, str] = {}
    for a in sorted(tx | set(rx) | set(sig_frames) | set(blocked)):
      if a not in dbc:
        self.skipped[a] = "not in the DBC" + (f" ({self.not_sent[a]})" if a in self.not_sent else "")
        continue
    for a in sorted(tx | set(rx) | set(sig_frames)):
      if a not in dbc:
        continue
      forwarded = a in camera_fwd
      item_sends = (a in tx and a not in not_sent) or forwarded
      peer = PEERS.get(a)
      if not peer:
        raise src.SourceError(f"frame {a:#x} ({dbc[a].name}) has no peer in PEERS")
      self.bus0[a] = dict(
        item_sends=item_sends, forwarded=forwarded, rx_check=rx.get(a), signals=sig_frames.get(a, []),
        allowed=a in tx, peer=peer[0], basis=peer[1],
        rate=mode.tx_rate.get(a), arrival=mode.tx_arrival.get(a), wp_use=table.get(a, ""))
    for a in sorted(set(blocked) | camera_fwd):
      if a in dbc:
        self.bus2[a] = dict(blocked=a in blocked, forwarded=a in camera_fwd)

  def can_layer(self):
    """Units, compu methods, system signals, I-signals, PDUs and frames for every described frame."""
    com = self.pk["Communication"]
    self.isig: dict[tuple[int, str], str] = {}
    self.syssig: dict[tuple[int, str], str] = {}
    self.pdu: dict[int, str] = {}
    self.frame: dict[int, str] = {}
    self.group: dict[int, str] = {}
    self.sr_if: dict[int, str] = {}
    pi = self.pk["PortInterfaces"]
    for a in sorted(set(self.bus0) | set(self.bus2)):
      msg = self.dbc[a]
      info = self.bus0.get(a, {})
      sids = info.get("signals", [])
      elements = []
      for s in msg.signals:
        cm = self.compu(msg.name, s)
        t = self.type_for(s)
        name = ident(f"{msg.name}_{s.name}")
        s_ids = [sid for sid in sids if re.search(rf"\b{re.escape(s.name)}\b", expand_names(self.m.signals[sid].doc))]
        trace = []
        for sid in s_ids:
          v = self.m.signals[sid].values
          self.used_signals[sid].append(f"{msg.name}.{s.name}")
          trace += self.trace_sdg(wp="WP-S-05", clause="§11.1", signals=[sid], tsr=v.get("tsr", []),
                                  integrity=f"{v.get('asil')}; checksum: {v.get('integrity')}; "
                                            f"validity: {v.get('validity')}",
                                  extra=[("rate", v.get("rate")), ("reaction", v.get("reaction"))])
        self.syssig[(a, s.name)] = self.pk["SystemSignals"].add(identifiable(
          "SYSTEM-SIGNAL", name, E("DYNAMIC-LENGTH", text="false"),
          self._props(compu=cm, tag="PHYSICAL-PROPS") if cm else None, admin=sdgs(trace) if trace else None))
        self.isig[(a, s.name)] = com.add(identifiable(
          "I-SIGNAL", name, E("DATA-TYPE-POLICY", text="LEGACY"), E("LENGTH", text=str(s.length)),
          self._props(base=self.base[t], compu=cm, tag="NETWORK-REPRESENTATION-PROPS"),
          ref("SYSTEM-SIGNAL-REF", "SYSTEM-SIGNAL", self.syssig[(a, s.name)])))
        elements.append(identifiable(
          "VARIABLE-DATA-PROTOTYPE", ident(s.name), self._props(compu=cm) if cm else None,
          ref("TYPE-TREF", "IMPLEMENTATION-DATA-TYPE", self.idt[t])))
      # a signal of WP-S-05 §11 that names the frame but none of its signals describes the whole frame
      frame_sids = [sid for sid in sids if not any(re.search(rf"\b{re.escape(x.name)}\b",
                                                             expand_names(self.m.signals[sid].doc))
                                                   for x in msg.signals)]
      frame_trace = []
      for sid in frame_sids:
        v = self.m.signals[sid].values
        self.used_signals[sid].append(f"{msg.name} (whole frame)")
        frame_trace += self.trace_sdg(wp="WP-S-05", clause="§11.1", signals=[sid], tsr=v.get("tsr", []),
                                      integrity=f"{v.get('asil')}; checksum: {v.get('integrity')}; "
                                                f"validity: {v.get('validity')}",
                                      extra=[("rate", v.get("rate")), ("reaction", v.get("reaction"))])
      # signal group (needed to describe the checksum/counter protection of the PDU)
      sysgrp = self.pk["SystemSignals"].add(identifiable("SYSTEM-SIGNAL-GROUP", ident(f"{msg.name}_Group"), E("SYSTEM-SIGNAL-REFS", *[
        ref("SYSTEM-SIGNAL-REF", "SYSTEM-SIGNAL", self.syssig[(a, s.name)]) for s in msg.signals])))
      self.group[a] = com.add(identifiable("I-SIGNAL-GROUP", ident(f"{msg.name}_Group"), E("I-SIGNAL-REFS", *[
        ref("I-SIGNAL-REF", "I-SIGNAL", self.isig[(a, s.name)]) for s in msg.signals]),
        ref("SYSTEM-SIGNAL-GROUP-REF", "SYSTEM-SIGNAL-GROUP", sysgrp)))
      maps = [identifiable("I-SIGNAL-TO-I-PDU-MAPPING", ident(s.name),
                           ref("I-SIGNAL-REF", "I-SIGNAL", self.isig[(a, s.name)]),
                           E("PACKING-BYTE-ORDER", text="MOST-SIGNIFICANT-BYTE-LAST" if s.little_endian
                             else "MOST-SIGNIFICANT-BYTE-FIRST"),
                           E("START-POSITION", text=str(s.lsb_position())),
                           E("TRANSFER-PROPERTY", text="PENDING")) for s in msg.signals]
      maps.append(identifiable("I-SIGNAL-TO-I-PDU-MAPPING", "Group",
                               ref("I-SIGNAL-GROUP-REF", "I-SIGNAL-GROUP", self.group[a])))
      period = None
      if info.get("rx_check"):
        period = 1.0 / info["rx_check"].frequency
      elif info.get("rate") and info.get("item_sends") and not info.get("forwarded"):
        period = 1.0 / info["rate"][0]
      timing = None
      if period:
        timing = E("I-PDU-TIMING-SPECIFICATIONS", E("I-PDU-TIMING", E("TRANSMISSION-MODE-DECLARATION", E(
          "TRANSMISSION-MODE-TRUE-TIMING", E("CYCLIC-TIMING", E("TIME-PERIOD", E("VALUE", text=seconds(period))))))))
      pdu_admin = sdgs([("LionDriver.Source", [("path", msg.source), ("path", self.mode.path),
                                               ("opendbcCommit", self.opendbc)]),
                        ("LionDriver.Security", [("secOC", "none: the reference car's frames are not authenticated "
                                                  "(the toyota_secoc path of toyota.h is not this configuration; "
                                                  "WP-S-05 §12.1, AOU-18)")])] + frame_trace)
      self.cited.add("AOU-18")
      self.pdu[a] = com.add(identifiable(
        "I-SIGNAL-I-PDU", ident(f"{msg.name}_IPdu"), E("LENGTH", text=str(msg.length)), timing,
        E("I-SIGNAL-TO-PDU-MAPPINGS", *maps), E("UNUSED-BIT-PATTERN", text="0"), admin=pdu_admin))
      self.frame[a] = com.add(identifiable(
        "CAN-FRAME", ident(msg.name), E("FRAME-LENGTH", text=str(msg.length)),
        E("PDU-TO-FRAME-MAPPINGS", identifiable(
          "PDU-TO-FRAME-MAPPING", ident(f"{msg.name}_IPdu"), E("PACKING-BYTE-ORDER", text="MOST-SIGNIFICANT-BYTE-LAST"),
          ref("PDU-REF", "I-SIGNAL-I-PDU", self.pdu[a]), E("START-POSITION", text="0"))),
        long_name=f"{a:#05x} {msg.name}"))
      self.sr_if[a] = pi.add(identifiable(
        "SENDER-RECEIVER-INTERFACE", ident(f"If_{msg.name}"), E("IS-SERVICE", text="false"),
        E("DATA-ELEMENTS", *elements),
        description=f"The signals of CAN frame {a:#05x} {msg.name}, one data element each (DBC {msg.source})"))

  # ------------------------------------------------------------------ end-to-end style protection
  def e2e(self):
    prots = []
    self.e2e_rows = []
    for a in sorted(self.bus0):
      msg, info = self.dbc[a], self.bus0[a]
      cks = msg.signal("CHECKSUM")
      ctr = msg.signal("COUNTER") or msg.signal("_COUNTER")
      if not cks:
        self.e2e_rows.append((a, msg.name, "none", "none", self._checked_by(info, False)))
        continue
      rxc = info.get("rx_check")
      checked = self._checked_by(info, True)
      profile = [E("CATEGORY", text="LIONDRIVER_TOYOTA_CHECKSUM8"),
                 E("DATA-IDS", E("DATA-ID", text=str(a))),
                 E("DATA-LENGTH", text=str(msg.length * 8)),
                 E("CRC-OFFSET", text=str(cks.lsb_position()))]
      if ctr:
        profile.append(E("COUNTER-OFFSET", text=str(ctr.lsb_position())))
      text = ("Not an AUTOSAR E2E profile. Toyota 8-bit additive checksum: the low byte of the sum of the identifier "
              "bytes, the length and the data bytes (toyota.h toyota_compute_checksum), in the last byte; the "
              "identifier enters the sum like an AUTOSAR data ID. "
              + (f"{ctr.length}-bit counter {ctr.name}. " if ctr else "No counter. ")
              + f"Checked by: {checked}.")
      if rxc:
        text += (f" Reception supervised by the panda: absence for {self.mode.rx_timeout_periods} periods of "
                 f"{rxc.frequency} Hz revokes authority (TSR-401).")
      self.e2e_rows.append((a, msg.name, f"8-bit checksum (bit {cks.lsb_position()})",
                            f"{ctr.length}-bit (bit {ctr.lsb_position()})" if ctr else "none", checked))
      prots.append(identifiable(
        "END-TO-END-PROTECTION", ident(msg.name), E("END-TO-END-PROFILE", *profile),
        E("END-TO-END-PROTECTION-I-SIGNAL-I-PDUS", E("END-TO-END-PROTECTION-I-SIGNAL-I-PDU",
          E("DATA-OFFSET", text="0"), ref("I-SIGNAL-GROUP-REF", "I-SIGNAL-GROUP", self.group[a]),
          ref("I-SIGNAL-I-PDU-REF", "I-SIGNAL-I-PDU", self.pdu[a]))),
        description=text,
        admin=sdgs(self.trace_sdg(wp="WP-S-05", clause="§5, §12.3, §12.5", paths=[self.mode.path],
                                  tsr=["TSR-401", "TSR-402"] if rxc else []))))
    self.pk["Communication"].add(identifiable(
      "END-TO-END-PROTECTION-SET", "ReferenceCar_ChecksumCounter", E("END-TO-END-PROTECTIONS", *prots),
      description=("The checksum and counter protection of the reference car's frames, written in AUTOSAR's "
                   "end-to-end vocabulary. None of it is an AUTOSAR E2E profile (category "
                   "LIONDRIVER_TOYOTA_CHECKSUM8 is not a standard category). WP-S-05 §12.3: on the reference car "
                   "end-to-end protection in the usual sense (checksum, counter and timeout together) exists only on "
                   "the camera's PCS frames. For comparison, WP-S-05 §12.5: Volkswagen MQB uses CRC-8H2F with a "
                   "data ID per counter value, the AUTOSAR E2E profile 2 pattern; no such vehicle is configured")))

  def _checked_by(self, info: dict, has_checksum: bool) -> str:
    rxc = info.get("rx_check")
    parts = []
    if rxc:
      parts.append("panda RX check" + ("" if rxc.check_checksum else " (timeout only, checksum not checked)"))
    elif info.get("item_sends") and not info.get("forwarded"):
      parts.append("written by openpilot on the SoC; not checked by the panda (WP-S-05 §12.3 H2)")
    if info.get("forwarded"):
      parts.append("forwarded byte for byte, checked by the receiving ECU (WP-S-05 §12.3 H4)")
    if info.get("peer") == "EXT-EPS" and info.get("item_sends") and has_checksum:
      parts.append("the EPS, assumed (WP-S-05 OI-9)")
    return "; ".join(parts) or "not checked by the item"

  # ------------------------------------------------------------------ software components
  def components(self):
    m = self.m
    pi = self.pk["PortInterfaces"]
    swcs: dict[str, Swc] = {}

    def from_element(e, name, kind, extra_doc=""):
      cat = e.meta.get("Catalogue") or {}
      src_meta = e.meta.get("Source") or {}
      return Swc(name, kind, f"{e.short or e.name} {cat.get('name') or ''}".strip(),
                 " ".join(x for x in (cat.get("description") or e.doc, extra_doc) if x),
                 self.trace_sdg(wp=src_meta.get("workProduct", ""), clause=src_meta.get("clause", ""),
                                sysml=e.path, integrity=(e.meta.get("Safety") or {}).get("label", e.integrity() or "")))

    # E-01 processes: one application SWC per openpilot process the model names (host.*), and the rest
    e01 = m.find("E-01")
    procs = [c for c in e01.children]
    for c in procs:
      extra = ""
      if c.short in ("host.modeld", "host.dm"):
        extra = "Runs the ML model of E-02 (allocated to this process in the SysML model); E-02 is not a separate SWC."
      swcs[c.path] = from_element(c, ident(f"Proc_{(c.short or c.name).split('.')[-1]}"),
                                  "APPLICATION-SW-COMPONENT-TYPE", "A Linux process of openpilot, not an AUTOSAR SWC. "
                                  + extra)
      swcs[c.path].ecu = "LD_SoC"
    e03a, e03b = m.find("E-03a"), m.find("E-03b")
    sl = swcs[e03a.path] = from_element(e03a, "SafetyLayer", "APPLICATION-SW-COMPONENT-TYPE",
                                        "Bare-metal C in the panda firmware, not an AUTOSAR SWC. Units: " + ", ".join(
                                          c.short or c.name for c in e03a.walk() if c is not e03a and c.kind == "part"))
    pf = swcs[e03b.path] = from_element(e03b, "PlatformFirmware", "COMPLEX-DEVICE-DRIVER-SW-COMPONENT-TYPE",
                                        "Bare-metal C (panda board firmware), described as a complex device driver "
                                        "because it owns the SPI, FDCAN, GPIO and audio hardware directly. Units: "
                                        + ", ".join(c.short or c.name for c in e03b.walk()
                                                    if c is not e03b and c.kind == "part"))
    sl.ecu = pf.ecu = "LD_SafetyMcu"

    # cereal services between processes (WP-S-03 §9 via the model's DataFlow connections)
    flows = [c for c in m.connections if c.definition == "DataFlow"]
    cereal_if: dict[str, str] = {}
    e01_comp_conn = []
    for c in sorted(flows, key=lambda c: (c.values["service"], c.ends)):
      svc = c.values["service"]
      if svc not in cereal_if:
        cereal_if[svc] = pi.add(identifiable(
          "SENDER-RECEIVER-INTERFACE", ident(f"If_Cereal_{svc}"), E("IS-SERVICE", text="false"),
          E("DATA-ELEMENTS", identifiable("VARIABLE-DATA-PROTOTYPE", ident(svc),
                                          ref("TYPE-TREF", "IMPLEMENTATION-DATA-TYPE", self.idt["ByteBuffer"]))),
          description=f"cereal service '{svc}' (msgq publish/subscribe on the SoC; Cap'n Proto schema in cereal/)"))
      pub, sub = swcs[c.ends[0]], swcs[c.ends[1]]
      rate = c.values.get("rateHz")
      doc = f"cereal '{svc}' at {fmt(rate)} Hz (WP-S-03 §9)" if rate else f"cereal '{svc}' (WP-S-03 §9)"
      pub.port(ident(svc), "P", "SENDER-RECEIVER-INTERFACE", cereal_if[svc], doc)
      sub.port(ident(svc), "R", "SENDER-RECEIVER-INTERFACE", cereal_if[svc], doc)
      e01_comp_conn.append((pub.name, ident(svc), sub.name, ident(svc)))
    self.n_flows = len(flows)

    # SoC <-> safety MCU over SPI (HSI-01..03, WP-S-05 §4)
    ops = []
    for r in self.requests:
      sig = [sid for sid, rec in m.signals.items() if rec.values.get("group") == "SoC ↔ safety MCU signals"
             and r.code in request_codes(rec.doc)]
      for sid in sig:
        self.used_signals[sid].append(f"PandaControl.Req_{r.code:02X}")
      ops.append(identifiable(
        "CLIENT-SERVER-OPERATION", f"Req_{r.code:02X}",
        E("ARGUMENTS", *[identifiable("ARGUMENT-DATA-PROTOTYPE", n, ref("TYPE-TREF", "IMPLEMENTATION-DATA-TYPE",
                                                                         self.idt[t]), E("DIRECTION", text=d))
                         for n, t, d in (("param1", "uint16", "IN"), ("param2", "uint16", "IN"),
                                         ("response", "ByteBuffer", "OUT"))]),
        long_name=f"0x{r.code:02x} {r.function}",
        description=f"Effect on safety: {r.effect}. Gating at the baseline: {r.gating}. Required in a car mode: "
                    f"{r.required}.",
        admin=sdgs(self.trace_sdg(wp="WP-S-05", clause="§4.2", tsr=r.tsr, signals=sig))))
    ctrl_if = pi.add(identifiable(
      "CLIENT-SERVER-INTERFACE", "If_PandaControl", E("IS-SERVICE", text="false"), E("OPERATIONS", *ops),
      description="Control requests of SPI endpoint 0 (ControlPacket_t: request, param1, param2, length; handler "
                  "comms_control_handler). One operation per request code of WP-S-05 §4.2",
      admin=sdgs(self.trace_sdg(wp="WP-S-05", clause="§4.1, §4.2", hsi=["HSI-01", "HSI-02"]))))
    spi_ifs = {}
    for name, d in (("CanPacketsToMcu", "SoC → MCU, SPI endpoint 3: CAN frames to transmit; each passes the TX hook"),
                    ("CanPacketsToSoc", "MCU → SoC, SPI endpoint 1/0x81: received CAN frames and rejected TX "
                                        "frames returned with rejected = 1")):
      spi_ifs[name] = pi.add(identifiable(
        "SENDER-RECEIVER-INTERFACE", f"If_{name}", E("IS-SERVICE", text="false"),
        E("DATA-ELEMENTS", identifiable("VARIABLE-DATA-PROTOTYPE", "packet",
                                        ref("TYPE-TREF", "IMPLEMENTATION-DATA-TYPE", self.idt["CanPacket"]))),
        description=d + " (WP-S-05 §4.3)",
        admin=sdgs(self.trace_sdg(wp="WP-S-05", clause="§4.3", hsi=["HSI-01", "HSI-03"]))))
    for sid, rec in m.signals.items():
      if rec.values.get("group") != "SoC ↔ safety MCU signals":
        continue
      if rec.doc.startswith("SPI transfer"):
        self.used_signals[sid] += ["If_PandaControl", "If_CanPacketsToMcu", "If_CanPacketsToSoc"]
      elif "CAN TX packet" in rec.doc:
        self.used_signals[sid].append("If_CanPacketsToMcu")
    self.used_hsi |= {"HSI-01", "HSI-02", "HSI-03"}
    pandad = next(s for p, s in swcs.items() if p.endswith(".pandad"))
    pandad.port("PandaControl", "R", "CLIENT-SERVER-INTERFACE", ctrl_if, "SPI endpoint 0")
    pandad.port("CanTx", "P", "SENDER-RECEIVER-INTERFACE", spi_ifs["CanPacketsToMcu"], "SPI endpoint 3")
    pandad.port("CanRx", "R", "SENDER-RECEIVER-INTERFACE", spi_ifs["CanPacketsToSoc"], "SPI endpoint 1")
    pf.port("Control", "P", "CLIENT-SERVER-INTERFACE", ctrl_if, "SPI endpoint 0 (comms_control_handler)")
    pf.port("SpiCanTx", "R", "SENDER-RECEIVER-INTERFACE", spi_ifs["CanPacketsToMcu"], "SPI endpoint 3")
    pf.port("SpiCanRx", "P", "SENDER-RECEIVER-INTERFACE", spi_ifs["CanPacketsToSoc"], "SPI endpoint 1")

    # safety hooks: the platform firmware calls the safety layer for every frame (opendbc safety.h)
    hooks = pi.add(identifiable(
      "CLIENT-SERVER-INTERFACE", "If_SafetyHooks", E("IS-SERVICE", text="false"), E("OPERATIONS", *[
        identifiable("CLIENT-SERVER-OPERATION", n, E("ARGUMENTS", *[
          identifiable("ARGUMENT-DATA-PROTOTYPE", an, ref("TYPE-TREF", "IMPLEMENTATION-DATA-TYPE", self.idt[at]),
                       E("DIRECTION", text=ad)) for an, at, ad in args]), description=d)
        for n, d, args in (
          ("RxHook", "safety_rx_hook: every received frame; RX checks (checksum, counter, timeout) and the state "
                     "the envelope keeps", (("packet", "CanPacket", "IN"), ("valid", "boolean", "OUT"))),
          ("TxHook", "safety_tx_hook: every frame the SoC asks to send; allow-list, envelope limits, rate checks",
           (("packet", "CanPacket", "INOUT"), ("allowed", "boolean", "OUT"))),
          ("FwdHook", "safety_fwd_hook: bus-to-bus forwarding decision (bus 2 → 0 and 0 → 2); a TX message on bus 0 "
                      "with check_relay is never forwarded from the camera",
           (("bus", "uint8", "IN"), ("address", "uint32", "IN"), ("destination", "sint32", "OUT"))))]),
      description="The safety hooks of opendbc's safety layer (opendbc/safety/safety.h), called by the panda "
                  "firmware; a C function-pointer table, described here as a client-server interface",
      admin=sdgs(self.trace_sdg(wp="WP-S-03", clause="§3.3", paths=["opendbc_repo/opendbc/safety/safety.h"],
                                hsi=["HSI-03", "HSI-04"], tsr=["TSR-704"]))))
    sl.port("SafetyHooks", "P", "CLIENT-SERVER-INTERFACE", hooks)
    pf.port("SafetyHooks", "R", "CLIENT-SERVER-INTERFACE", hooks)

    # CAN ports: the panda transmits on bus 0 and receives on buses 0 and 2; the safety layer consumes the RX set
    ext: dict[str, Swc] = {}
    ctx = m.elements["context"]
    for key, name in EXT_SWC.items():
      e = m.find(key) if key.startswith("EXT-") else m.elements[f"context.{key}"]
      label = (e.meta.get("Safety") or {}).get("label", "")
      aous = re.findall(r"AOU-\d+", label)
      ext[key] = Swc(name, "APPLICATION-SW-COMPONENT-TYPE", f"{e.short or e.name} (vehicle ECU)",
                     f"Vehicle ECU at the item boundary, outside the item: {e.doc} Only its CAN interface to the "
                     "item is described.",
                     self.trace_sdg(wp="WP-C-01", clause="§3.2–§3.4", sysml=e.path, aou=aous, integrity=label))
      ext[key].ecu = f"Ext_{name.split('_', 1)[1]}"
    del ctx
    for a, info in self.bus0.items():
      n = self.dbc[a].name
      peer = ext[info["peer"]]
      if info["item_sends"]:
        pf.port(f"Tx_{n}", "P", "SENDER-RECEIVER-INTERFACE", self.sr_if[a], "bus 0")
        peer.port(f"Rx_{n}", "R", "SENDER-RECEIVER-INTERFACE", self.sr_if[a])
      else:
        peer.port(f"Tx_{n}", "P", "SENDER-RECEIVER-INTERFACE", self.sr_if[a])
        pf.port(f"Rx_{n}", "R", "SENDER-RECEIVER-INTERFACE", self.sr_if[a], "bus 0, queued to the SoC")
        if info["rx_check"]:
          sl.port(f"Rx_{n}", "R", "SENDER-RECEIVER-INTERFACE", self.sr_if[a], "bus 0, RX check and envelope inputs")
    cam = ext["forwardCamera"]
    for a, info in self.bus2.items():
      n = self.dbc[a].name
      cam.port(f"Tx_{n}", "P", "SENDER-RECEIVER-INTERFACE", self.sr_if[a])
      pf.port(f"RxCam_{n}", "R", "SENDER-RECEIVER-INTERFACE", self.sr_if[a],
              "bus 2 (camera side); " + ("blocked: the item sends its own on bus 0" if info["blocked"]
                                          else "forwarded unchanged to bus 0"))

    # hardware/software responsibilities (V-20) and the hardware signals: on the CDD, below where an RTE would be
    for hid, rec in sorted(m.responsibilities.items()):
      v = rec.values
      self.used_hsi.add(hid)
      pf.trace.append((f"LionDriver.HSI.{hid}", [
        ("interface", rec.doc), ("hardware", v.get("hardware")), ("software", v.get("software")),
        ("detection", v.get("detection")), ("reaction", v.get("reaction")), ("status", v.get("status")),
        ("hwOwner", v.get("hwOwnerText")), ("swOwner", v.get("swOwnerText")), ("hwResource", v.get("hwResource")),
        ("autosarAnalogue", BSW_ANALOGUE.get(hid, ""))] + [("tsr", t) for t in v.get("tsr", [])]))
      for t in v.get("tsr", []):
        if t not in self.tsr_ids:
          raise src.SourceError(f"{hid} cites {t}, not in the trace data")
        self.cited.add(t)
    for sid, rec in m.signals.items():
      if rec.values.get("group") == "Safety MCU hardware signals":
        v = rec.values
        self.used_signals[sid].append("PlatformFirmware (hardware signal)")
        pf.trace.append((f"LionDriver.HwSignal.{sid}", [
          ("signal", rec.doc), ("direction", v.get("direction")), ("hsi", ", ".join(v.get("hsi", []))),
          ("validity", v.get("validity")), ("asil", v.get("asil"))] + [("tsr", t) for t in v.get("tsr", [])]))

    # compositions: E-01 SoC software, E-03 safety MCU firmware, LD-SDA, and the vehicle context
    e01c = Swc("SocSoftware", "COMPOSITION-SW-COMPONENT-TYPE", "E-01 SoC software", "", [])
    from_e01 = from_element(e01, "x", "x")
    e01c.doc, e01c.trace = from_e01.doc + " openpilot processes on Linux; none of them is an AUTOSAR SWC.", from_e01.trace
    e01c.parts = [(s.name, s) for p, s in swcs.items() if p.startswith(e01.path + ".")]
    e01c.assemblies = e01_comp_conn
    e03 = m.find("E-03")
    e03c = Swc("SafetyMcuFirmware", "COMPOSITION-SW-COMPONENT-TYPE", "E-03 safety MCU firmware",
               "The panda firmware on the STM32H7 safety MCU: bare metal, no AUTOSAR stack.",
               self.trace_sdg(wp="WP-W-03", clause="§3.1", sysml=e03.path, integrity="C"))
    e03c.parts = [("SafetyLayer", sl), ("PlatformFirmware", pf)]
    e03c.assemblies = [("SafetyLayer", "SafetyHooks", "PlatformFirmware", "SafetyHooks")]
    ld = Swc("LdSda", "COMPOSITION-SW-COMPONENT-TYPE", "LD-SDA (the item)",
             "LD-SDA, the item: openpilot on the SoC and the panda safety firmware. E-02 runs inside modeld and dm; "
             "E-04 hardware and E-05 harness are ECU-level and physical and appear as ECU instances and buses.",
             self.trace_sdg(wp="WP-C-01", clause="§1, §3.1", sysml="context.ldsda"))
    ld.parts = [("SocSoftware", e01c), ("SafetyMcuFirmware", e03c)]
    ld.assemblies = [("SafetyMcuFirmware", "Control", "SocSoftware", "PandaControl"),
                     ("SocSoftware", "CanTx", "SafetyMcuFirmware", "SpiCanTx"),
                     ("SafetyMcuFirmware", "SpiCanRx", "SocSoftware", "CanRx")]
    self.delegate(e01c, ["PandaControl", "CanTx", "CanRx"])
    self.delegate(e03c, ["Control", "SpiCanTx", "SpiCanRx"] + [p for p in pf.ports if p.startswith(("Tx_", "Rx_", "RxCam_"))]
                  + [p for p in sl.ports if p.startswith("Rx_")])
    self.delegate(ld, [p for p in e03c.ports if p.startswith(("Tx_", "Rx_", "RxCam_"))])
    top = Swc("VehicleContext", "COMPOSITION-SW-COMPONENT-TYPE", "LD-SDA in the reference vehicle",
              f"The item in the reference vehicle {self.ref.config_id} ({self.ref.codename}, {self.ref.adas}) with "
              "the ECUs it exchanges CAN frames with.",
              self.trace_sdg(wp="WP-C-01", clause="§3.2, §3.3", sysml="context"))
    top.parts = [("LdSda", ld)] + [(s.name, s) for s in ext.values()]
    for p in ld.ports.values():
      n = p.name
      frame = n.split("_", 1)[1]
      if n.startswith("Tx_"):
        peer = next(s for s in ext.values() if f"Rx_{frame}" in s.ports and s is not cam)
        top.assemblies.append(("LdSda", n, peer.name, f"Rx_{frame}"))
      elif n.startswith("RxCam_"):
        top.assemblies.append((cam.name, f"Tx_{frame}", "LdSda", n))
      else:
        peer = next(s for s in ext.values() if f"Tx_{frame}" in s.ports and s is not cam)
        top.assemblies.append((peer.name, f"Tx_{frame}", "LdSda", n))
    self.swcs = [*swcs.values(), *ext.values()]
    self.compositions = [e01c, e03c, ld, top]
    self.top = top

    # write the types
    pk = self.pk["SwComponentTypes"]
    for s in [*self.swcs, *self.compositions]:
      self.write_swc(pk, s)

  def delegate(self, comp: Swc, names: list[str]):
    """Outer ports of a composition: one per inner port name, delegated to every inner part that has it."""
    for n in dict.fromkeys(names):
      inner = [(pn, t) for pn, t in comp.parts if n in t.ports]
      if not inner:
        raise src.SourceError(f"{comp.name}: no inner port {n}")
      kinds = {(t.ports[n].direction, t.ports[n].interface) for _, t in inner}
      if len(kinds) != 1:
        raise src.SourceError(f"{comp.name}: inner ports {n} differ")
      d, i = kinds.pop()
      comp.port(n, d, inner[0][1].ports[n].kind, i)
      for pn, _ in inner:
        comp.delegations.append((pn, n, n))

  def swc_path(self, s: Swc) -> str:
    return f"{self.pk['SwComponentTypes'].path}/{s.name}"

  def write_swc(self, pk: Package, s: Swc):
    ports = []
    for p in sorted(s.ports.values(), key=lambda p: p.name):
      if p.direction == "P":
        ports.append(identifiable("P-PORT-PROTOTYPE", p.name, ref("PROVIDED-INTERFACE-TREF", p.kind, p.interface),
                                  description=p.doc or None))
      else:
        ports.append(identifiable("R-PORT-PROTOTYPE", p.name, ref("REQUIRED-INTERFACE-TREF", p.kind, p.interface),
                                  description=p.doc or None))
    kids = [E("PORTS", *ports) if ports else None]
    if s.kind == "COMPOSITION-SW-COMPONENT-TYPE":
      kids.append(E("COMPONENTS", *[identifiable("SW-COMPONENT-PROTOTYPE", n, ref("TYPE-TREF", t.kind,
                                                                                   self.swc_path(t)))
                                    for n, t in s.parts]))
      conns = []
      for prov, pp, req, rp in s.assemblies:
        pt, rt = s.proto(prov), s.proto(req)
        if pt.ports[pp].interface != rt.ports[rp].interface or pt.ports[pp].direction != "P" or rt.ports[rp].direction != "R":
          raise src.SourceError(f"{s.name}: cannot connect {prov}.{pp} to {req}.{rp}")
        conns.append(identifiable(
          "ASSEMBLY-SW-CONNECTOR", ident(f"{prov}_{pp}_to_{req}_{rp}"),
          E("PROVIDER-IREF", ref("CONTEXT-COMPONENT-REF", "SW-COMPONENT-PROTOTYPE", f"{self.swc_path(s)}/{prov}"),
            ref("TARGET-P-PORT-REF", "P-PORT-PROTOTYPE", f"{self.swc_path(pt)}/{pp}")),
          E("REQUESTER-IREF", ref("CONTEXT-COMPONENT-REF", "SW-COMPONENT-PROTOTYPE", f"{self.swc_path(s)}/{req}"),
            ref("TARGET-R-PORT-REF", "R-PORT-PROTOTYPE", f"{self.swc_path(rt)}/{rp}"))))
      for inner, ip, outer in s.delegations:
        it = s.proto(inner)
        d = it.ports[ip].direction
        tag = "P-PORT-IN-COMPOSITION-INSTANCE-REF" if d == "P" else "R-PORT-IN-COMPOSITION-INSTANCE-REF"
        tgt = "TARGET-P-PORT-REF" if d == "P" else "TARGET-R-PORT-REF"
        ptag = "P-PORT-PROTOTYPE" if d == "P" else "R-PORT-PROTOTYPE"
        conns.append(identifiable(
          "DELEGATION-SW-CONNECTOR", ident(f"{inner}_{ip}"),
          E("INNER-PORT-IREF", E(tag, ref("CONTEXT-COMPONENT-REF", "SW-COMPONENT-PROTOTYPE",
                                          f"{self.swc_path(s)}/{inner}"),
                                 ref(tgt, ptag, f"{self.swc_path(it)}/{ip}"))),
          ref("OUTER-PORT-REF", ptag, f"{self.swc_path(s)}/{outer}")))
      kids.append(E("CONNECTORS", *conns) if conns else None)
    pk.add(identifiable(s.kind, s.name, *kids, long_name=s.long_name, description=s.doc,
                        admin=sdgs(s.trace) if s.trace else None))

  # ------------------------------------------------------------------ ECUs, clusters, system
  def topology(self):
    com, ecus = self.pk["Communication"], self.pk["EcuInstances"]
    ecu_names = sorted({s.ecu for s in self.swcs})
    # ports per ECU per cluster: (ecu, bus) -> list of port elements
    ports: dict[tuple[str, int], list] = defaultdict(list)
    trig: dict[int, dict] = {0: {}, 2: {}}       # bus -> address -> (frame ports, pdu ports, {signal: ports})

    def add_ports(ecu: str, bus: int, a: int, direction: str, timeout: float | None = None):
      msg = self.dbc[a]
      conn = f"{ecus.path}/{ecu}/{ident(f'Bus{bus}')}"
      fp = identifiable("FRAME-PORT", ident(f"{msg.name}_{direction}"), E("COMMUNICATION-DIRECTION", text=direction))
      pp = identifiable("I-PDU-PORT", ident(f"{msg.name}_IPdu_{direction}"),
                        E("COMMUNICATION-DIRECTION", text=direction))
      sp = []
      for s in msg.signals:
        kids = [E("COMMUNICATION-DIRECTION", text=direction)]
        if timeout:
          kids.append(E("TIMEOUT", text=seconds(timeout)))
        sp.append((s.name, identifiable("I-SIGNAL-PORT", ident(f"{msg.name}_{s.name}_{direction}"), *kids)))
      ports[(ecu, bus)] += [fp, pp] + [p for _, p in sp]
      t = trig[bus].setdefault(a, ([], [], defaultdict(list)))
      t[0].append(f"{conn}/{fp.findtext('SHORT-NAME')}")
      t[1].append(f"{conn}/{pp.findtext('SHORT-NAME')}")
      for n, p in sp:
        t[2][n].append(f"{conn}/{p.findtext('SHORT-NAME')}")

    rx_timeout = {a: self.mode.rx_timeout_periods / i["rx_check"].frequency
                  for a, i in self.bus0.items() if i["rx_check"]}
    ext_ecu = {k: f"Ext_{v.split('_', 1)[1]}" for k, v in EXT_SWC.items()}
    for a, info in self.bus0.items():
      peer = ext_ecu[info["peer"]]
      if info["item_sends"]:
        add_ports("LD_SafetyMcu", 0, a, "OUT")
        add_ports(peer, 0, a, "IN")
      else:
        add_ports(peer, 0, a, "OUT")
        add_ports("LD_SafetyMcu", 0, a, "IN", rx_timeout.get(a))
    for a in self.bus2:
      add_ports(ext_ecu["forwardCamera"], 2, a, "OUT")
      add_ports("LD_SafetyMcu", 2, a, "IN")

    clusters = {0: ("VehicleCan_Bus0", "Vehicle side of the harness (panda bus 0, FDCAN1 or FDCAN3 when flipped): "
                                       "actuation TX and the envelope's RX set (WP-S-05 §5)", "IF-01, IF-02"),
                2: ("CameraCan_Bus2", "Camera side of the harness (panda bus 2): the forward camera's frames, "
                                      "forwarded to bus 0 except those the item replaces (WP-S-05 §5)", "IF-03")}
    self.cluster_path = {}
    for bus, (cname, cdesc, ifs) in clusters.items():
      channel = f"{com.path}/{cname}/Channel"
      ft, pt, st = [], [], []
      for a in sorted(trig[bus]):
        msg = self.dbc[a]
        fports, pports, sports = trig[bus][a]
        sigtrigs = []
        for s in msg.signals:
          st.append(identifiable("I-SIGNAL-TRIGGERING", ident(f"{msg.name}_{s.name}"),
                                 E("I-SIGNAL-PORT-REFS", *[ref("I-SIGNAL-PORT-REF", "I-SIGNAL-PORT", p)
                                                           for p in sports[s.name]]),
                                 ref("I-SIGNAL-REF", "I-SIGNAL", self.isig[(a, s.name)])))
          sigtrigs.append(f"{channel}/{ident(f'{msg.name}_{s.name}')}")
        st.append(identifiable("I-SIGNAL-TRIGGERING", ident(f"{msg.name}_Group"),
                               ref("I-SIGNAL-GROUP-REF", "I-SIGNAL-GROUP", self.group[a])))
        sigtrigs.append(f"{channel}/{ident(f'{msg.name}_Group')}")
        pt.append(identifiable("PDU-TRIGGERING", ident(f"{msg.name}_IPdu"),
                               E("I-PDU-PORT-REFS", *[ref("I-PDU-PORT-REF", "I-PDU-PORT", p) for p in pports]),
                               ref("I-PDU-REF", "I-SIGNAL-I-PDU", self.pdu[a]),
                               E("I-SIGNAL-TRIGGERINGS", *[E("I-SIGNAL-TRIGGERING-REF-CONDITIONAL",
                                                             ref("I-SIGNAL-TRIGGERING-REF", "I-SIGNAL-TRIGGERING", x))
                                                           for x in sigtrigs])))
        ft.append(identifiable("CAN-FRAME-TRIGGERING", ident(msg.name),
                               E("FRAME-PORT-REFS", *[ref("FRAME-PORT-REF", "FRAME-PORT", p) for p in fports]),
                               ref("FRAME-REF", "CAN-FRAME", self.frame[a]),
                               E("PDU-TRIGGERINGS", E("PDU-TRIGGERING-REF-CONDITIONAL", ref(
                                 "PDU-TRIGGERING-REF", "PDU-TRIGGERING", f"{channel}/{ident(f'{msg.name}_IPdu')}"))),
                               E("CAN-ADDRESSING-MODE", text="STANDARD"), E("CAN-FD-FRAME-SUPPORT", text="false"),
                               E("IDENTIFIER", text=str(a))))
      ecus_here = sorted({e for (e, b) in ports if b == bus})
      self.cluster_path[bus] = com.add(identifiable(
        "CAN-CLUSTER", cname, E("CAN-CLUSTER-VARIANTS", E("CAN-CLUSTER-CONDITIONAL",
          E("BAUDRATE", text="500000"),
          E("PHYSICAL-CHANNELS", identifiable(
            "CAN-PHYSICAL-CHANNEL", "Channel",
            E("COMM-CONNECTORS", *[E("COMMUNICATION-CONNECTOR-REF-CONDITIONAL", ref(
              "COMMUNICATION-CONNECTOR-REF", "CAN-COMMUNICATION-CONNECTOR", f"{ecus.path}/{e}/Bus{bus}"))
              for e in ecus_here]),
            E("FRAME-TRIGGERINGS", *ft), E("I-SIGNAL-TRIGGERINGS", *st), E("PDU-TRIGGERINGS", *pt))),
          E("PROTOCOL-NAME", text="CAN"), E("PROTOCOL-VERSION", text="ISO 11898-1 classical CAN"))),
        description=cdesc + ". 500 kbit/s (WP-S-05 §3, §12.1)",
        admin=sdgs(self.trace_sdg(wp="WP-S-05", clause="§5", hsi=["HSI-04"], extra=[("interface", ifs)]))))
    self.used_hsi.add("HSI-04")

    ecu_doc = {
      "LD_SoC": ("E-04b comma device SoC", "Qualcomm SoC running AGNOS Linux: the openpilot processes (E-01, E-02). "
                 "Not an AUTOSAR ECU. Its link to the safety MCU is SPI (HSI-01), which AUTOSAR's system template has no "
                 "bus type for; the link is described by the client-server and sender-receiver interfaces between the "
                 "two compositions."),
      "LD_SafetyMcu": ("E-04a safety MCU (panda, STM32H7)", "The safety MCU running the panda firmware (E-03), bare "
                       "metal. Not an AUTOSAR ECU. Its CAN controllers sit behind the harness (E-05)."),
    }
    for e in ecu_names:
      conns = []
      for bus in (0, 2):
        if (e, bus) in ports:
          conns.append(identifiable("CAN-COMMUNICATION-CONNECTOR", f"Bus{bus}",
                                    E("ECU-COMM-PORT-INSTANCES", *ports[(e, bus)])))
      ln, d = ecu_doc.get(e, (None, None))
      if d is None:
        s = next(s for s in self.swcs if s.ecu == e)
        ln, d = s.long_name, s.doc
      ecus.add(identifiable("ECU-INSTANCE", e, E("CONNECTORS", *conns) if conns else None, long_name=ln,
                            description=d))

    # the gateway: frames the panda copies from the camera bus to the vehicle bus unchanged
    fwd = [a for a, i in self.bus2.items() if i["forwarded"]]
    com.add(identifiable(
      "GATEWAY", "Panda_CameraForwarding", ref("ECU-REF", "ECU-INSTANCE", f"{ecus.path}/LD_SafetyMcu"),
      E("I-PDU-MAPPINGS", *[E("I-PDU-MAPPING",
        ref("SOURCE-I-PDU-REF", "PDU-TRIGGERING", f"{self.cluster_path[2]}/Channel/{ident(self.dbc[a].name + '_IPdu')}"),
        E("TARGET-I-PDU", ref("TARGET-I-PDU-REF", "PDU-TRIGGERING",
                              f"{self.cluster_path[0]}/Channel/{ident(self.dbc[a].name + '_IPdu')}")))
        for a in fwd]),
      description=("safety_fwd_hook copies every camera-bus frame to bus 0 unchanged except the TX messages with "
                    "check_relay, which the item replaces (" + ", ".join(f"{a:#05x}" for a in
                                                                          self.mode.blocked_from_camera())
                    + "). Only the described frames are listed; every other camera frame is forwarded the same way."),
      admin=sdgs(self.trace_sdg(wp="WP-S-02", clause="TSR-704, TSR-707", tsr=["TSR-704", "TSR-707"],
                                paths=["opendbc_repo/opendbc/safety/safety.h"]))))

  def system(self):
    sysp = self.pk["System"].path
    sysname = "LionDriver_ReferenceCar"
    root = f"{sysp}/{sysname}/{self.top.name}"
    comp_path = {}

    def walk(c: Swc, chain: list[str]):
      for n, t in c.parts:
        if t.kind == "COMPOSITION-SW-COMPONENT-TYPE":
          walk(t, chain + [f"{self.swc_path(c)}/{n}"])
        else:
          comp_path[id(t)] = (chain + [f"{self.swc_path(c)}/{n}"], t)
    walk(self.top, [])
    mappings = []
    by_ecu = defaultdict(list)
    for chain, t in comp_path.values():
      by_ecu[t.ecu].append(chain)
    sw = []
    for ecu in sorted(by_ecu):
      sw.append(identifiable("SWC-TO-ECU-MAPPING", ident(f"To_{ecu}"), E("COMPONENT-IREFS", *[
        E("COMPONENT-IREF", ref("CONTEXT-COMPOSITION-REF", "ROOT-SW-COMPOSITION-PROTOTYPE", root),
          *[ref("CONTEXT-COMPONENT-REF", "SW-COMPONENT-PROTOTYPE", x) for x in ch[:-1]],
          ref("TARGET-COMPONENT-REF", "SW-COMPONENT-PROTOTYPE", ch[-1])) for ch in sorted(by_ecu[ecu])]),
        ref("ECU-INSTANCE-REF", "ECU-INSTANCE", f"{self.pk['EcuInstances'].path}/{ecu}")))
    # data mappings: every CAN data element of an atomic SWC to its system signal
    for chain, t in sorted(comp_path.values(), key=lambda x: x[0]):
      for p in sorted(t.ports.values(), key=lambda p: p.name):
        if not p.name.startswith(("Tx_", "Rx_", "RxCam_")):
          continue
        frame = p.name.split("_", 1)[1]
        a = next(a for a, msg in self.dbc.items() if msg.name == frame)
        for s in self.dbc[a].signals:
          mappings.append(E("SENDER-RECEIVER-TO-SIGNAL-MAPPING", E("DATA-ELEMENT-IREF",
            *[ref("CONTEXT-COMPONENT-REF", "SW-COMPONENT-PROTOTYPE", x) for x in chain],
            ref("CONTEXT-COMPOSITION-REF", "ROOT-SW-COMPOSITION-PROTOTYPE", root),
            ref("CONTEXT-PORT-REF", "P-PORT-PROTOTYPE" if p.direction == "P" else "R-PORT-PROTOTYPE",
                f"{self.swc_path(t)}/{p.name}"),
            ref("TARGET-DATA-PROTOTYPE-REF", "VARIABLE-DATA-PROTOTYPE", f"{p.interface}/{ident(s.name)}")),
            ref("SYSTEM-SIGNAL-REF", "SYSTEM-SIGNAL", self.syssig[(a, s.name)])))
    com = self.pk["Communication"]
    fibex = ([("CAN-CLUSTER", p) for p in self.cluster_path.values()]
             + [("ECU-INSTANCE", f"{self.pk['EcuInstances'].path}/{e.findtext('SHORT-NAME')}")
                for e in self.pk["EcuInstances"].elements]
             + [(e.tag, f"{com.path}/{e.findtext('SHORT-NAME')}") for e in com.elements
                if e.tag in ("CAN-FRAME", "I-SIGNAL-I-PDU", "I-SIGNAL", "I-SIGNAL-GROUP", "GATEWAY")])
    self.n_data_mappings = len(mappings)
    self.pk["System"].add(identifiable(
      "SYSTEM", sysname,
      E("FIBEX-ELEMENTS", *[E("FIBEX-ELEMENT-REF-CONDITIONAL", ref("FIBEX-ELEMENT-REF", t, p)) for t, p in fibex]),
      E("MAPPINGS", identifiable("SYSTEM-MAPPING", "Mapping", E("DATA-MAPPINGS", *mappings), E("SW-MAPPINGS", *sw))),
      E("ROOT-SOFTWARE-COMPOSITIONS", identifiable(
        "ROOT-SW-COMPOSITION-PROTOTYPE", self.top.name,
        ref("SOFTWARE-COMPOSITION-TREF", "COMPOSITION-SW-COMPONENT-TYPE", self.swc_path(self.top)))),
      E("SYSTEM-VERSION", text=f"{DESCRIPTION_VERSION};opendbc_{self.opendbc[:12]}"),
      long_name=f"LD-SDA on {self.ref.config_id} {self.ref.codename}",
      description=f"Reference configuration {self.ref.config_id} ({self.ref.platform}, safety mode "
                  f"{self.ref.safety_mode}, DBC {self.ref.dbc}_generated). SYSTEM-VERSION is the description version and the opendbc commit.",
      category="SYSTEM_DESCRIPTION"))

  # ------------------------------------------------------------------ completeness
  def complete(self):
    missing = sorted(set(self.m.signals) - set(self.used_signals), key=sysml_lite.__dict__.get("natural", str))
    if missing:
      raise src.SourceError(f"HSI signals not placed in the description: {missing}")
    hsi = set(self.m.responsibilities) - self.used_hsi
    if hsi:
      raise src.SourceError(f"HSI responsibilities not placed: {sorted(hsi)}")
    for a, info in self.bus0.items():
      if info["rx_check"] and a not in self.dbc:
        raise src.SourceError(f"RX-checked frame {a:#x} missing from the DBC")

  # ------------------------------------------------------------------ output
  def build(self) -> tuple[str, str]:
    self.data_types()
    self.frames()
    self.can_layer()
    self.e2e()
    self.components()
    self.topology()
    self.system()
    self.complete()
    order = ["BaseTypes", "ImplementationDataTypes", "Units", "CompuMethods", "PortInterfaces", "SwComponentTypes",
             "SystemSignals", "Communication", "EcuInstances", "System"]
    pkgs = [identifiable("AR-PACKAGE", k, E("ELEMENTS", *self.pk[k].elements)) for k in order if self.pk[k].elements]
    top_admin = sdgs([("LionDriver.Nature", [("statement", NATURE), ("status", DESCRIPTION_STATUS),
                                             ("autosarRelease", f"Classic Platform {RELEASE} (schema {SCHEMA})"),
                                             ("generator", "assurance/models/autosar/tools/gen_arxml.py"),
                                             ("readme", "assurance/models/autosar/README.md")]),
                      ("LionDriver.Sources", [("vehicleRegister", f"{src.rel(src.VEHICLES)} {self.ref.config_id}"),
                                              ("sysmlModel", "assurance/models/sysml/model"),
                                              ("hsiSpecification", src.rel(src.WP_S05)),
                                              ("traceData", "assurance/trace/items"),
                                              ("dbc", f"{self.ref.dbc}_generated (opendbc {self.opendbc})"),
                                              ("safetyMode", f"{self.mode.path} with {', '.join(self.mode.defines)}")])])
    root = E("AUTOSAR", E("AR-PACKAGES", identifiable(
      "AR-PACKAGE", TOP, E("AR-PACKAGES", *pkgs), description=NATURE, admin=top_admin)))
    root.set("xmlns", NS)
    root.set("xmlns:xsi", XSI)
    root.set("xsi:schemaLocation", f"{NS} {SCHEMA}")
    ET.indent(root, space="  ")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           "<!-- GENERATED by assurance/models/autosar/tools/gen_arxml.py from the SysML model, WP-S-05, the trace "
           "data and opendbc. Do not edit; regenerate. A description in AUTOSAR terms, not an AUTOSAR "
           "implementation; no evidence credit (README). -->\n"
           + ET.tostring(root, encoding="unicode") + "\n")
    return xml, self.render_summary()

  def render_summary(self) -> str:
    L = ["<!-- GENERATED by tools/gen_arxml.py; do not edit. -->", "",
         "# What the AUTOSAR description holds", "",
         f"Reference configuration **{self.ref.config_id}** ({self.ref.codename}, {self.ref.adas}), opendbc "
         f"platform `{self.ref.platform}`, DBC `{self.ref.dbc}_generated`, safety mode `{self.ref.safety_mode}` "
         f"built with `{', '.join(self.mode.defines)}`, opendbc `{self.opendbc[:12]}`. AUTOSAR Classic {RELEASE} "
         f"(`{SCHEMA}`). A description, not an AUTOSAR implementation; no evidence credit.", "",
         "## Software components", "",
         "| SWC | AUTOSAR kind | From | Mapped to ECU | Ports |", "|---|---|---|---|---|"]
    for s in self.swcs:
      src_ = next((v for g, sds in s.trace if g == "LionDriver.Source" for k, v in sds if k == "sysmlElement"), "")
      L.append(f"| {s.name} | {s.kind.replace('-SW-COMPONENT-TYPE', '').lower()} | `{src_}` | {s.ecu} | "
               f"{len(s.ports)} |")
    L += ["", "Compositions: " + ", ".join(f"{c.name} ({len(c.parts)} parts, {len(c.assemblies)} assembly and "
                                           f"{len(c.delegations)} delegation connectors)" for c in self.compositions)
          + f". Cereal services: {self.n_flows} publisher-to-subscriber flows of the SysML model as sender-receiver "
          f"connectors. Control requests: {len(self.requests)} operations of `If_PandaControl` (WP-S-05 §4.2).", "",
          "## CAN frames", "",
          "| ID | Frame | Bus | Sender | Receiver | Period | RX timeout | Checksum | Counter | Checked by | Signals (WP-S-05 §11) |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    e2e = {a: r for a, *r in self.e2e_rows}
    for a, i in self.bus0.items():
      n = self.dbc[a].name
      snd, rcv = ("LD_SafetyMcu" + (" (forwarded)" if i["forwarded"] else ""), EXT_SWC[i["peer"]]) if i["item_sends"] \
        else (EXT_SWC[i["peer"]], "LD_SafetyMcu" + (" + SafetyLayer" if i["rx_check"] else ""))
      per = (f"{1000 / i['rx_check'].frequency:.1f} ms" if i["rx_check"] else
             f"{1000 / i['rate'][0]:.1f} ms" if i["rate"] and i["item_sends"] and not i["forwarded"] else "—")
      to = f"{self.mode.rx_timeout_periods * 1000 / i['rx_check'].frequency:.0f} ms" if i["rx_check"] else (
        f"TX arrival {i['arrival'] // 1000} ms" if i["arrival"] else "—")
      _, cks, ctr, by = e2e[a]
      L.append(f"| `{a:#05x}` | {n} | 0 | {snd} | {rcv} | {per} | {to} | {cks} | {ctr} | {by} | "
               f"{', '.join(i['signals']) or '—'} |")
    for a, i in self.bus2.items():
      L.append(f"| `{a:#05x}` | {self.dbc[a].name} | 2 | Ext_ForwardCamera | LD_SafetyMcu | — | — | — | — | "
               f"{'blocked, replaced by the item' if i['blocked'] else 'forwarded to bus 0 (gateway)'} | — |")
    L += ["", "Allowed by the TX hook but not described: " + (", ".join(f"`{a:#05x}` ({why})"
                                                                         for a, why in sorted(self.skipped.items())) or "none")
          + ". Allowed by the TX hook but not sent by the reference car (toyota.h rate-check notes), so the item is "
          "not described as their sender: " + ", ".join(f"`{a:#05x}` ({why})" for a, why in sorted(self.not_sent.items())
                                                       if a in self.dbc) + ".", "",
          f"System: {self.n_data_mappings} sender-receiver-to-signal mappings, one per CAN data element of each "
          "atomic SWC. Every safety-relevant signal S-01…S-29 of WP-S-05 §11 and every responsibility HSI-01…HSI-14 "
          "(V-20) is placed in the file, or the generator fails:", "",
          "| Signal | Placed at |", "|---|---|"]
    for sid in sorted(self.used_signals, key=lambda s: int(s[2:])):
      L.append(f"| {sid} | {', '.join(dict.fromkeys(self.used_signals[sid]))} |")
    L += ["", f"Trace identifiers cited and found in `assurance/trace/items`: {len(self.cited)}.", ""]
    return "\n".join(L)


def main() -> int:
  check = "--check" in sys.argv[1:]
  try:
    xml, summary = Builder().build()
  except src.SourceError as e:
    print(f"gen_arxml: {e}", file=sys.stderr)
    return 2
  stale = []
  for path, text in ((OUT, xml), (SUMMARY, summary)):
    if check:
      if not path.exists() or path.read_text(encoding="utf-8") != text:
        stale.append(path.relative_to(REPO).as_posix())
    else:
      path.parent.mkdir(parents=True, exist_ok=True)
      path.write_text(text, encoding="utf-8")
  if stale:
    print("gen_arxml: stale, run python3 assurance/models/autosar/tools/gen_arxml.py: " + ", ".join(stale),
          file=sys.stderr)
    return 1
  if not check:
    print(f"wrote {OUT.relative_to(REPO)} and {SUMMARY.relative_to(REPO)}")
  else:
    print("gen_arxml: up to date")
  return 0


if __name__ == "__main__":
  sys.exit(main())
