#!/usr/bin/env python3
"""Draw WP-A-02 Figure 3-1: coexistence and interference map with the FFI verdicts.

The source of record is `../WP-A-02-coexistence-freedom-from-interference.md`. This script parses
  * the §2 table (one row per firmware sub-element and its coexistence decision),
  * the channel tables of §4 (FFI-SP), §5.1 / §5.2 (FFI-TM) and §6.1–§6.4 (FFI-CM),
  * the §7 table (measure, interference addressed, TSR references), and
  * the §8 table (one verdict per level),
and draws them on a fixed layout: the QM SoC, the panda firmware partitions, the channels between
them by type, and one card per §8 verdict with the TSRs §7 gives for that card's channels.

What is read from the document and what is drawing:
  * Channel tags, verdict chips (including a dated change of verdict) and the TSR lines are read.
  * The partition boxes are drawing; every §2 row must match one box with the same decision
    (PARTITIONS), so a changed or new §2 row fails the build.
  * The two short lines of reason on each card are drawing (CARD_TEXT), condensed from the §8
    row. Each carries a fingerprint of that row: when the row changes, the build fails until the
    card text is reviewed and the fingerprint updated (`--fingerprints` prints the current ones).
  * The channels drawn from the QM housekeeping partition into the ASIL core (HOUSEKEEPING) are a
    drawing choice; they must exist in §4 / §5.1.

    python3 fig_a02_interference_map.py                 # regenerate the SVG
    python3 fig_a02_interference_map.py --check         # fail if the committed SVG is stale
    python3 fig_a02_interference_map.py --fingerprints  # print the §8 row fingerprints

Standard library only. Output is deterministic.
"""

from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "WP-A-02-coexistence-freedom-from-interference.md"
OUTPUT = "fig-a02-3-1-interference-map.svg"
FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"

RED, AMBER, GREEN = "#D2553F", "#D97706", "#2E9E6A"
SPATIAL, TEMPORAL, COMMS = "#7C3AED", "#A16207", "#0F766E"

# §2 rows -> partition box. Key: a substring of the §2 "Sub-element" cell; value: the decision the
# box shows (bold text of the "Decision" cell).
PARTITIONS = {
  "opendbc safety core": "ASIL C (B after re-rating)",
  "Tick handler": "ASIL C",
  "CAN driver RX/TX": "ASIL C",
  "Relay and harness drivers": "ASIL C/B",
  "`set_safety_mode`": "ASIL C",
  "Fault handling": "ASIL C",
  "Host command dispatcher": "ASIL C for the commands that touch safety state; others shown non-interfering",
  "SPI/USB transport": "ASIL C (integrity checks) / FFI for the rest",
  "Fan, sound, LED": "QM with FFI",
  "Bootstub / softloader": "ASIL C for signature check and relay-safe start; cybersecurity scope",
}

# Channels drawn from the QM housekeeping partition into the ASIL core.
HOUSEKEEPING = ["FFI-SP-01", "FFI-SP-04", "FFI-TM-01", "FFI-TM-02"]

# §8 level -> (card colour, condensed reason, fingerprint of the §8 row).
CARD_TEXT = {
  "L-MCU spatial": (SPATIAL, ["No MPU; QM paths share the address space; SPI",
                              "length unbounded (bank separation unconfirmed)"], "48e048f9c4a5"),
  "L-MCU temporal": (TEMPORAL, ["IWDG (≈ 90 ms) and 100 Hz safety task implemented,",
                                "priorities explicit; no WCET; rate faults report-only"], "19f3df35d829"),
  "L-DEV communication (data)": (COMMS, ["TX hook limits every frame; no freshness or",
                                         "sequence counter; weak 8-bit XOR checksum"], "ed889cf14863"),
  "L-DEV communication (commands)": (COMMS, ["Reference build: mode lock and car-mode request",
                                             "gating; boot control open; other builds unchanged"], "ac480a264408"),
  "L-DEV boot control": (COMMS, ["SoC drives BOOT0/RST; no RDP/WRP; development",
                                 "bootstub in the recovery path (GAP-38, GAP-24)"], "d097061b5ca3"),
}

VERDICTS = [  # longest first
  ("partially shown in the reference build", "PARTIAL (REF)", AMBER),
  ("partially shown", "PARTIALLY SHOWN", AMBER),
  ("not shown", "NOT SHOWN", RED),
  ("shown", "SHOWN", GREEN),
]


class ParseError(Exception):
  pass


@dataclass
class Verdict:
  level: str
  base: str                  # verdict key at the first state
  base_at: str | None        # commit the first state is dated at, if any
  latest: str                # verdict key after the last dated change
  not_verified: bool
  fingerprint: str


@dataclass
class Model:
  version: str
  sections: dict[str, list[str]] = field(default_factory=dict)   # "4", "5.1", ... -> channel IDs
  measures: list[tuple[list[str], list[str], str]] = field(default_factory=list)  # (addressed, TSRs, measure)
  verdicts: list[Verdict] = field(default_factory=list)


def cells(line: str) -> list[str]:
  return [c.strip() for c in line.strip().strip("|").split("|")]


def id_list(text: str) -> list[str]:
  """'FFI-CM-01, -02, -11, FFI-TM-06' / 'FFI-CM-06…10' / 'FFI-CM-17…-19' -> expanded IDs."""
  out: list[str] = []
  prefix = None
  for tok in re.split(r",\s*", text):
    m = re.match(r"(FFI-(?:SP|TM|CM))-(\d+)(?:\s*…\s*-?(\d+))?", tok.strip())
    if m:
      prefix, a, b = m.group(1), int(m.group(2)), m.group(3)
    else:
      m = re.match(r"-(\d+)(?:\s*…\s*-?(\d+))?", tok.strip())
      if not m or prefix is None:
        continue
      a, b = int(m.group(1)), m.group(2)
    for n in range(a, int(b) + 1 if b else a + 1):
      out.append(f"{prefix}-{n:02d}")
  return out


def compress(ids: list[str]) -> str:
  """['FFI-CM-06', ..., 'FFI-CM-11', 'FFI-CM-13', 'FFI-CM-14'] -> 'CM-06…11, 13, 14'."""
  if not ids:
    raise ParseError("empty channel group")
  kind = ids[0].split("-")[1]
  nums = sorted(int(i.split("-")[2]) for i in ids)
  runs: list[list[int]] = []
  for n in nums:
    if runs and n == runs[-1][-1] + 1:
      runs[-1].append(n)
    else:
      runs.append([n])
  parts: list[str] = []
  for r in runs:
    parts.extend([f"{r[0]:02d}…{r[-1]:02d}"] if len(r) >= 3 else [f"{n:02d}" for n in r])
  first = parts[0]
  rest = [p if "…" in first else f"-{p}" for p in parts[1:]]
  return ", ".join([f"{kind}-{first}"] + rest)


def verdict_key(text: str) -> str:
  low = re.sub(r"[*`]", "", text).strip().lower()
  for key, _, _ in VERDICTS:
    if low.startswith(key):
      return key
  raise ParseError(f"unknown verdict: {text[:60]}")


def fingerprint(verdict_cell: str, reason_cell: str) -> str:
  return hashlib.sha256(f"{verdict_cell}\n{reason_cell}".encode()).hexdigest()[:12]


def parse(md: str) -> Model:
  m = re.search(r"^\| Version \| ([0-9.]+) ", md, re.M)
  if not m:
    raise ParseError("no version row")
  model = Model(version=m.group(1))
  section = None
  in_s2 = in_s7 = in_s8 = False
  s2_seen: dict[str, int] = {k: 0 for k in PARTITIONS}
  for line in md.splitlines():
    h = re.match(r"^(#{2,3}) (\d+(?:\.\d+)?)\.? ", line)
    if h:
      section = h.group(2)
      in_s2, in_s7, in_s8 = section == "2", section == "7", section == "8"
      continue
    if not line.startswith("|") or line.startswith("|---"):
      continue
    c = cells(line)
    if in_s2 and c[0] != "Sub-element (panda firmware)":
      keys = [k for k in PARTITIONS if k in c[0]]
      if len(keys) != 1:
        raise ParseError(f"§2 row matches {len(keys)} partition boxes, update PARTITIONS: {c[0][:60]}")
      decision = re.sub(r"\*\*", "", c[3])
      if decision != PARTITIONS[keys[0]]:
        raise ParseError(f"§2 decision changed for {keys[0]!r}: {decision!r}; update the partition box")
      s2_seen[keys[0]] += 1
    elif in_s7 and c[0] != "Measure":
      model.measures.append((id_list(c[1]), [t.strip() for t in re.split(r"[,;]", c[2]) if t.strip()], c[0]))
    elif in_s8 and c[0] != "Level":
      parts = re.split(r"\*\d{4}-\d{2}-\d{2}:\*", c[1])
      at = re.search(r"at `([0-9a-f]{7,})`", parts[0])
      model.verdicts.append(Verdict(
        level=c[0], base=verdict_key(parts[0]), base_at=at.group(1) if at and len(parts) > 1 else None,
        latest=verdict_key(parts[-1]), not_verified="not verified on hardware" in c[2].split("*")[-1],
        fingerprint=fingerprint(c[1], c[2])))
    elif section and re.match(r"FFI-(SP|TM|CM)-\d+$", c[0]):
      model.sections.setdefault(section, []).append(c[0])
  missing = [k for k, n in s2_seen.items() if n != 1]
  if missing:
    raise ParseError(f"partition boxes without a §2 row: {missing}")
  for sec in ("4", "5.1", "5.2", "6.1", "6.2", "6.3", "6.4"):
    if not model.sections.get(sec):
      raise ParseError(f"no channels parsed in §{sec}")
  if [v.level for v in model.verdicts] != list(CARD_TEXT):
    raise ParseError(f"§8 levels changed: {[v.level for v in model.verdicts]}; update CARD_TEXT")
  for v in model.verdicts:
    if v.fingerprint != CARD_TEXT[v.level][2]:
      raise ParseError(f"§8 row {v.level!r} changed (fingerprint {v.fingerprint}); review its card text in "
                       f"CARD_TEXT, then update the fingerprint")
  known = {i for ids in model.sections.values() for i in ids}
  for i in HOUSEKEEPING:
    if i not in model.sections["4"] + model.sections["5.1"]:
      raise ParseError(f"housekeeping channel {i} not in §4 / §5.1")
  for addressed, _, measure in model.measures:
    if not set(addressed) <= known:
      raise ParseError(f"§7 row {measure[:40]!r} names unknown channels {sorted(set(addressed) - known)}")
  return model


def groups(model: Model) -> dict[str, list[str]]:
  boot = [i for addressed, _, measure in model.measures if "RDP" in measure
          for i in addressed if i in model.sections["6.2"]]
  if not boot:
    raise ParseError("no boot-control channel: no §7 RDP/WRP row addresses a §6.2 channel")
  return {
    "sp": model.sections["4"],
    "tm_mcu": model.sections["5.1"],
    "tm_dev": model.sections["5.2"],
    "data": model.sections["6.1"],
    "cmds": [i for i in model.sections["6.2"] if i not in boot],
    "boot": boot,
    "rx": model.sections["6.3"],
    "hmi": model.sections["6.4"],
  }


def card_channels(g: dict[str, list[str]]) -> dict[str, list[str]]:
  return {
    "L-MCU spatial": g["sp"],
    "L-MCU temporal": g["tm_mcu"],
    "L-DEV communication (data)": g["data"] + g["tm_dev"],
    "L-DEV communication (commands)": g["cmds"],
    "L-DEV boot control": g["boot"],
  }


def card_tsrs(model: Model, channels: list[str]) -> list[str]:
  out: list[str] = []
  for addressed, tsrs, _ in model.measures:
    if set(addressed) & set(channels):
      out.extend(t for t in tsrs if t not in out)
  return out


def t(x, y, s, size, fill="#0F172A", weight=None, anchor=None, extra=""):
  w = f' font-weight="{weight}"' if weight else ""
  a = f' text-anchor="{anchor}"' if anchor else ""
  return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}"{w}{a}{extra}>{escape(s)}</text>'


def tag(x, y, w, label, fill):
  return (f'<rect x="{x}" y="{y}" width="{w}" height="16" rx="8" fill="{fill}"/>'
          f'<text x="{x + w / 2:g}" y="{y + 12}" class="tag" text-anchor="middle">{escape(label)}</text>')


def tag_w(label: str) -> int:
  return int(len(label) * 5.6 + 18)


def verdict_style(key: str) -> tuple[str, str]:
  for k, label, colour in VERDICTS:
    if k == key:
      return label, colour
  raise ParseError(key)


def wrap_items(items: list[str], prefix: str, width: int) -> list[str]:
  lines, cur = [], prefix
  for it in items:
    nxt = it if cur == prefix else f"{cur} · {it}"
    if cur != prefix and len(nxt) > width:
      lines.append(cur)
      cur = it
    else:
      cur = f"{prefix}{it}" if cur == prefix else nxt
  lines.append(cur)
  return lines


def draw(model: Model) -> str:
  g = groups(model)
  cc = card_channels(g)
  hk_sp = [i for i in HOUSEKEEPING if i.startswith("FFI-SP")]
  hk_tm = [i for i in HOUSEKEEPING if i.startswith("FFI-TM")]
  all_ids = sorted(i for ids in model.sections.values() for i in ids)
  latest = {v.level: verdict_style(v.latest)[0].lower() for v in model.verdicts}
  desc = (f"Generated from WP-A-02 v{model.version}. The comma device (L-DEV) holds the QM SoC software and the "
          f"panda STM32H7 firmware (L-MCU), one image without MPU partitioning: SoC-facing code (SPI/USB "
          f"transport, command dispatcher, bootstub and softloader) is ASIL C where it touches safety state and "
          f"FFI otherwise; the envelope core, tick handler, CAN driver, relay drivers, mode setting and fault "
          f"handling are the ASIL partition; housekeeping is QM with FFI. Interference channels: "
          f"{compress([i for i in all_ids if '-SP-' in i])} spatial, {compress([i for i in all_ids if '-TM-' in i])} "
          f"temporal, {compress([i for i in all_ids if '-CM-' in i])} communication. Verdicts of §8: "
          + "; ".join(f"{k} {v}" for k, v in latest.items()) + ".")
  o: list[str] = []
  a = o.append
  a(f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="800" viewBox="0 0 1280 800" font-family="{FONT}" role="img" aria-labelledby="t d">')
  a('  <title id="t">Figure 3-1. Coexistence and interference map: QM SoC, panda firmware partitions, interference channels and FFI verdicts (WP-A-02 §2–§8)</title>')
  a(f'  <desc id="d">{escape(desc)}</desc>')
  a('  <defs>')
  for mid, col in (("aT", COMMS), ("aP", SPATIAL), ("aY", TEMPORAL), ("aG", "#475569")):
    a(f'    <marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{col}"/></marker>')
  a('    <style>')
  a('      .t{fill:#0F172A}.m{fill:#475569}.s{font-size:11px}.xs{font-size:10px}.b{font-weight:700}.sb{font-weight:600}')
  a('      .ml{fill:#EEF2FF;stroke:#A5B4FC;stroke-width:1}')
  a('      .asilc{fill:#FFFFFF;stroke:#FDBA74;stroke-width:1}')
  a('      .tag{font-size:9.5px;font-weight:700;fill:#FFFFFF}')
  a('    </style>')
  a('  </defs>')
  a('  <rect width="1280" height="800" fill="#FFFFFF"/>')

  # header
  a('  <text x="40" y="44" class="t b" font-size="20">Figure 3-1 · Coexistence and interference map with FFI verdicts</text>')
  a(f'  <text x="40" y="66" class="m" font-size="12.5">QM SoC and ASIL-allocated panda firmware on one device · interference channels by type · verdicts of WP-A-02 v{escape(model.version)} §8</text>')
  a('  <text x="1240" y="44" class="m s" text-anchor="end">WP-A-02 §3</text>')
  a('  <text x="1240" y="62" class="m s" text-anchor="end">decisions §2 · channels §4–§6 · verdicts §8</text>')
  a('  <line x1="40" y1="82" x2="1240" y2="82" stroke="#E2E8F0"/>')

  # L-DEV container and SoC
  a('  <rect x="40" y="100" width="812" height="548" rx="14" fill="#FFFFFF" stroke="#64748B" stroke-width="1.4"/>')
  a('  <text x="56" y="122" class="t b" font-size="13">L-DEV · E-04 comma device</text>')
  a('  <text x="250" y="122" class="m s">SoC and MCU: separate memories, shared PCB and power (WP-A-03)</text>')
  a('  <rect x="56" y="136" width="234" height="496" rx="10" fill="#F8FAFC" stroke="#334155" stroke-width="1.4"/>')
  a('  <text x="70" y="158" class="t b" font-size="12.5">E-01 · E-02 SoC</text>')
  a('  <rect x="234" y="146" width="44" height="18" rx="9" fill="#64748B"/><text x="256" y="159" class="tag" text-anchor="middle">QM</text>')
  soc = [
    (222, 54, None, "pandad · card · controlsd", ["selfdrived · CAN TX, heartbeat 0xf3", "configuration requests"]),
    (286, 40, None, "hardware.py · recovery", ["STM_BOOT0, STM_RST_N lines"]),
    (336, 40, "ml", "E-02 models", ["modeld, dmonitoringmodeld"]),
    (386, 40, None, "AGNOS Linux · scheduler", ["overload, GC pause, crash, freeze"]),
    (456, 40, None, "ui · soundd", ["alerts, take-over requests"]),
    (532, 40, None, "logging · encoding · upload", ["streaming, athena"]),
  ]
  for y, h, cls, title, subs in soc:
    style = 'class="ml"' if cls else 'fill="#FFFFFF" stroke="#CBD5E1"'
    a(f'  <rect x="70" y="{y}" width="206" height="{h}" rx="7" {style}/>')
    a(f'  <text x="173" y="{y + 17}" class="t sb" font-size="11.5" text-anchor="middle">{escape(title)}</text>')
    for k, s in enumerate(subs):
      a(f'  <text x="173" y="{y + 31 + 12 * k}" class="m xs" text-anchor="middle">{escape(s)}</text>')
  hmi = compress(g["hmi"])
  a(f'  <path d="M120 532V498" stroke="{COMMS}" stroke-width="1.6" fill="none" marker-end="url(#aT)"/>')
  a('  ' + tag(173 - tag_w(hmi) / 2, 506, tag_w(hmi), hmi, COMMS))
  a('  <text x="70" y="592" class="m xs">QM-to-QM on the HMI and status path</text>')
  a('  <text x="70" y="605" class="m xs">(§6.4): starved ui/soundd, low volume,</text>')
  a('  <text x="70" y="618" class="m xs">stale pandaStates</text>')

  # panda MCU
  a('  <rect x="440" y="136" width="396" height="496" rx="10" fill="#FFFFFF" stroke="#334155" stroke-width="1.4"/>')
  a('  <text x="456" y="158" class="t b" font-size="12.5">L-MCU · E-03 panda STM32H7 firmware</text>')
  a('  <text x="456" y="174" class="m xs">one binary, one CPU, one address space · no MPU (GAP-11)</text>')
  a('  <rect x="456" y="186" width="364" height="140" rx="9" fill="#FFFFFF" stroke="#C2410C" stroke-width="1.3" stroke-dasharray="5 3"/>')
  a('  <text x="468" y="202" class="m xs" font-weight="600">SoC-facing code · ASIL C where it touches safety state, FFI otherwise</text>')
  a('  <rect x="468" y="222" width="152" height="54" rx="7" class="asilc"/>')
  a('  <text x="544" y="243" class="t sb" font-size="11.5" text-anchor="middle">SPI/USB transport</text>')
  a('  <text x="544" y="258" class="m xs" text-anchor="middle">C: integrity checks</text>')
  a('  <text x="544" y="270" class="m xs" text-anchor="middle">FFI: rest (DMA, buffers)</text>')
  a('  <path d="M620 249H642" stroke="#475569" stroke-width="1.4" fill="none" marker-end="url(#aG)"/>')
  a('  <rect x="644" y="222" width="164" height="54" rx="7" class="asilc"/>')
  a('  <text x="726" y="243" class="t sb" font-size="11.5" text-anchor="middle">command dispatcher</text>')
  a('  <text x="726" y="258" class="m xs" text-anchor="middle">C: commands that touch</text>')
  a('  <text x="726" y="270" class="m xs" text-anchor="middle">safety state · FFI: others</text>')
  a('  <rect x="468" y="286" width="340" height="32" rx="7" class="asilc"/>')
  a('  <text x="480" y="306" class="t sb" font-size="11.5">bootstub · softloader</text>')
  a('  <text x="610" y="306" class="m xs">C: signature check, relay-safe start</text>')
  sp, tm = compress(g["sp"]), compress(g["tm_mcu"])
  a(f'  <path d="M540 326V354" stroke="{SPATIAL}" stroke-width="2" fill="none" marker-end="url(#aP)"/>')
  a('  ' + tag(548, 332, tag_w(sp), sp, SPATIAL))
  a(f'  <path d="M700 326V354" stroke="{TEMPORAL}" stroke-width="2" stroke-dasharray="5 3" fill="none" marker-end="url(#aY)"/>')
  a('  ' + tag(708, 332, tag_w(tm), tm, TEMPORAL))
  a('  <rect x="456" y="356" width="364" height="164" rx="9" fill="#FFF7ED" stroke="#C2410C" stroke-width="1.8"/>')
  a('  <rect x="468" y="366" width="170" height="18" rx="9" fill="#C2410C"/>')
  a(f'  <text x="553" y="379" fill="#FFFFFF" font-size="10" font-weight="700" text-anchor="middle">{escape(PARTITIONS["opendbc safety core"])}</text>')
  a('  <text x="648" y="379" class="m xs">envelope state in DTCM</text>')
  core = [
    (468, 392, "tick · supervision", "heartbeat, siren, safety_tick"),
    (644, 392, "safety core · Toyota mode", "RX/TX/FWD hooks, limits"),
    (468, 434, "set_safety_mode", "mode bookkeeping"),
    (644, 434, "fault handling", "exceptions, early init"),
    (468, 476, "CAN driver RX/TX", "FDCAN ISR, queues"),
    (644, 476, "relay · harness drivers", f"{PARTITIONS['Relay and harness drivers']} · safe-state actuation"),
  ]
  for x, y, title, sub in core:
    a(f'  <rect x="{x}" y="{y}" width="164" height="36" rx="7" class="asilc"/>')
    a(f'  <text x="{x + 82}" y="{y + 16}" class="t sb" font-size="11" text-anchor="middle">{escape(title)}</text>')
    a(f'  <text x="{x + 82}" y="{y + 29}" class="m" font-size="9.5" text-anchor="middle">{escape(sub)}</text>')
  hsp, htm = compress(hk_sp), compress(hk_tm)
  a(f'  <path d="M540 556V524" stroke="{SPATIAL}" stroke-width="2" fill="none" marker-end="url(#aP)"/>')
  a('  ' + tag(548, 530, tag_w(hsp), hsp, SPATIAL))
  a(f'  <path d="M700 556V524" stroke="{TEMPORAL}" stroke-width="2" stroke-dasharray="5 3" fill="none" marker-end="url(#aY)"/>')
  a('  ' + tag(708, 530, tag_w(htm), htm, TEMPORAL))
  a('  <rect x="456" y="556" width="364" height="62" rx="9" fill="#F1F5F9" stroke="#94A3B8" stroke-width="1.2"/>')
  a('  <rect x="468" y="566" width="86" height="18" rx="9" fill="#64748B"/>')
  a(f'  <text x="511" y="579" fill="#FFFFFF" font-size="10" font-weight="700" text-anchor="middle">{escape(PARTITIONS["Fan, sound, LED"])}</text>')
  a('  <text x="564" y="579" class="m xs">housekeeping, must not block or corrupt</text>')
  a('  <text x="468" y="604" class="t" font-size="10.5">fan · sound · LED · IR · DTS/ADC · debug print</text>')

  # channels SoC -> MCU
  data, cmds, boot, tdev = (f"data · {compress(g['data'])}", f"cmds · {compress(g['cmds'])}",
                            f"boot/reset · {compress(g['boot'])}", f"timing · {compress(g['tm_dev'])}")
  a(f'  <path d="M276 240H466" stroke="{COMMS}" stroke-width="2" fill="none" marker-end="url(#aT)"/>')
  a('  ' + tag(300, 222, tag_w(data), data, COMMS))
  a(f'  <path d="M276 260H466" stroke="{COMMS}" stroke-width="2" fill="none" marker-end="url(#aT)"/>')
  a('  ' + tag(296, 264, tag_w(cmds), cmds, COMMS))
  a(f'  <text x="300" y="214" fill="{COMMS}" font-size="9.5" font-weight="600">IF-04 SPI</text>')
  a(f'  <path d="M276 304H372V302H466" stroke="{COMMS}" stroke-width="2" stroke-dasharray="2 3" fill="none" marker-end="url(#aT)"/>')
  a('  ' + tag(300, 308, tag_w(boot), boot, COMMS))
  a(f'  <path d="M276 406H466" stroke="{TEMPORAL}" stroke-width="2" stroke-dasharray="5 3" fill="none" marker-end="url(#aY)"/>')
  a('  ' + tag(300, 386, tag_w(tdev), tdev, TEMPORAL))

  # vehicle CAN
  rx = f"RX, forwarding · {compress(g['rx'])}"
  a('  <line x1="40" y1="684" x2="852" y2="684" stroke="#0F172A" stroke-width="4" stroke-linecap="round"/>')
  a('  <text x="40" y="672" class="t b" font-size="12">Vehicle CAN · IF-01, IF-02, IF-03</text>')
  a(f'  <path d="M448 682V494H466" stroke="{COMMS}" stroke-width="2" fill="none" marker-end="url(#aT)" marker-start="url(#aT)"/>')
  a('  ' + tag(458, 660, tag_w(rx), rx, COMMS))

  # verdict cards
  a('  <text x="876" y="112" class="m b" font-size="10" letter-spacing=".06em">FFI VERDICT (§8) · TSRS OF ITS CHANNELS (§7)</text>')
  for k, v in enumerate(model.verdicts):
    colour, lines, _ = CARD_TEXT[v.level]
    y = 122 + 102 * k
    a(f'  <rect x="876" y="{y}" width="364" height="94" rx="9" fill="#FFFFFF" stroke="#CBD5E1"/>')
    a(f'  <rect x="876" y="{y}" width="6" height="94" rx="3" fill="{colour}"/>')
    title = v.level.replace("communication (", "comms (").replace("(commands)", "(cmds)")
    a('  ' + t(894, y + 20, title.replace(" (", " · ").rstrip(")"), 12, weight=700))
    label, fill = verdict_style(v.latest)
    w = tag_w(label) + 8
    a(f'  <rect x="{1228 - w}" y="{y + 8}" width="{w}" height="18" rx="9" fill="{fill}"/>'
      f'<text x="{1228 - w / 2:g}" y="{y + 21}" class="tag" text-anchor="middle">{escape(label)}</text>')
    if v.base_at and v.base != v.latest:
      blabel, bfill = verdict_style(v.base)
      short = f"{v.base_at}: {blabel.split()[0]}"
      bw = int(len(short) * 5.2 + 14)
      x0 = 1228 - w - 16 - bw
      a(f'  <rect x="{x0}" y="{y + 8}" width="{bw}" height="18" rx="9" fill="#FFFFFF" stroke="{bfill}"/>'
        f'<text x="{x0 + bw / 2:g}" y="{y + 21}" font-size="9" font-weight="700" fill="{bfill}" text-anchor="middle">{escape(short)}</text>')
      a(f'  <text x="{1228 - w - 8}" y="{y + 21}" class="m" font-size="11" text-anchor="middle">→</text>')
    for j, ln in enumerate(lines):
      a('  ' + t(894, y + 40 + 14 * j, ln, 10.5))
    tsrs = card_tsrs(model, cc[v.level])
    if v.not_verified:
      tsrs = tsrs + ["not verified on hardware"]
    tl = wrap_items(tsrs, "§7: ", 62)
    if len(tl) > 2:
      raise ParseError(f"card {v.level!r} has {len(tl)} TSR lines; widen the card layout")
    for j, ln in enumerate(tl):
      a(f'  <text x="894" y="{y + 70 + 13 * j}" class="m xs">{escape(ln)}</text>')

  # legend
  a('  <line x1="40" y1="712" x2="1240" y2="712" stroke="#E2E8F0"/>')
  a('  <g transform="translate(40,736)" font-size="10.5">')
  a(f'    <line x1="0" y1="0" x2="28" y2="0" stroke="{SPATIAL}" stroke-width="2"/><text x="36" y="4" class="t">Spatial (memory) FFI-SP</text>')
  a(f'    <line x1="200" y1="0" x2="228" y2="0" stroke="{TEMPORAL}" stroke-width="2" stroke-dasharray="5 3"/><text x="236" y="4" class="t">Temporal FFI-TM</text>')
  a(f'    <line x1="360" y1="0" x2="388" y2="0" stroke="{COMMS}" stroke-width="2"/><text x="396" y="4" class="t">Communication FFI-CM</text>')
  a(f'    <line x1="550" y1="0" x2="578" y2="0" stroke="{COMMS}" stroke-width="2" stroke-dasharray="2 3"/><text x="586" y="4" class="t">Boot/reset GPIO</text>')
  a('    <rect x="700" y="-8" width="28" height="16" rx="4" fill="#FFF7ED" stroke="#C2410C" stroke-width="1.6"/><text x="736" y="4" class="t">ASIL partition</text>')
  a('    <rect x="846" y="-8" width="28" height="16" rx="4" fill="#FFFFFF" stroke="#C2410C" stroke-dasharray="5 3"/><text x="882" y="4" class="t">ASIL C in part, FFI for the rest</text>')
  a('    <rect x="1080" y="-8" width="28" height="16" rx="4" fill="#F1F5F9" stroke="#94A3B8"/><text x="1116" y="4" class="t">QM with FFI</text>')
  a('  </g>')
  a('  <g transform="translate(40,764)" font-size="10.5">')
  a(f'    <rect x="0" y="-8" width="28" height="16" rx="8" fill="{RED}"/><text x="36" y="4" class="t">Not shown</text>')
  a(f'    <rect x="130" y="-8" width="28" height="16" rx="8" fill="{AMBER}"/><text x="166" y="4" class="t">Partially shown (implemented in part)</text>')
  note = (f"IDs abbreviated: SP-01 = FFI-SP-01 etc. Vehicle RX ({compress(g['rx'])}) and the HMI path "
          f"({compress(g['hmi'])}) have no §8 verdict row.")
  a(f'    <text x="1200" y="4" class="m" text-anchor="end">{escape(note)}</text>')
  a('  </g>')
  a('</svg>')
  return "\n".join(o) + "\n"


def build() -> str:
  return draw(parse(SOURCE.read_text(encoding="utf-8")))


def main(argv: list[str]) -> int:
  if "--fingerprints" in argv:
    md = SOURCE.read_text(encoding="utf-8")
    for line in md[md.index("## 8."):].splitlines():
      if line.startswith("| L-"):
        c = cells(line)
        print(f"{c[0]}: {fingerprint(c[1], c[2])}")
    return 0
  try:
    content = build()
  except ParseError as e:
    print(f"fig_a02_interference_map: {e}", file=sys.stderr)
    return 1
  path = HERE / OUTPUT
  if "--check" in argv:
    if not path.exists() or path.read_text(encoding="utf-8") != content:
      print(f"stale: {OUTPUT}", file=sys.stderr)
      print("run: python3 assurance/08-analyses/figures/fig_a02_interference_map.py", file=sys.stderr)
      return 1
    print("fig_a02_interference_map: figure current")
    return 0
  path.write_text(content, encoding="utf-8")
  print(f"fig_a02_interference_map: wrote {OUTPUT}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
