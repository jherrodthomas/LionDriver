#!/usr/bin/env python3
"""Check an ARXML file without the AUTOSAR schema (A1-A8), and against it when one is given (A0).

The AUTOSAR XML schema may be used for informational purposes only under its licence and is not committed here
(README §4, decision register). CI therefore runs A1-A8, a documented structural check written for this project:

  A1  well-formed XML, root AUTOSAR in the r4.0 namespace, schemaLocation names the target schema
  A2  every SHORT-NAME is an AUTOSAR identifier ([a-zA-Z][a-zA-Z0-9_]*, at most 128 characters)
  A3  SHORT-NAMEs are unique among the identifiables of one parent (AUTOSAR's name space rule)
  A4  every reference (an element with DEST) resolves to an element of the type DEST names
  A5  every port is typed by an interface of the kind it names; an assembly connector joins a P-port and an R-port
      of the same interface; a delegation connector joins ports of the same direction and interface
  A6  every atomic SWC prototype in the root composition is mapped to exactly one ECU instance
  A7  every frame triggering has exactly one sending frame port and at least one receiving one
  A8  the file says what it is: the LionDriver.Nature statement is present (a description, not an implementation)

  A0  (only with --xsd PATH, needs lxml) validation against the AUTOSAR XML schema at PATH

    python3 tools/check_arxml.py [FILE] [--xsd AUTOSAR_00051.xsd]

Standard library only, except A0.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "generated" / "liondriver-reference.arxml"
NS = "http://autosar.org/schema/r4.0"
SCHEMA = "AUTOSAR_00051.xsd"
IDENT = re.compile(r"[a-zA-Z][a-zA-Z0-9_]{0,127}")
Q = f"{{{NS}}}"


def local(tag: str) -> str:
  return tag.split("}", 1)[-1]


def index(root: ET.Element) -> tuple[dict[str, ET.Element], list[str], dict[ET.Element, ET.Element]]:
  """Path -> element for every identifiable; problems found on the way (A2, A3); child -> parent."""
  paths, problems, parent = {}, [], {}
  for p in root.iter():
    for c in p:
      parent[c] = p

  def walk(el: ET.Element, prefix: str):
    seen = Counter()
    stack = list(el)
    while stack:
      c = stack.pop(0)
      sn = c.find(f"{Q}SHORT-NAME")
      if sn is not None:
        name = sn.text or ""
        if not IDENT.fullmatch(name):
          problems.append(f"A2 {prefix}/{name}: not an AUTOSAR identifier")
        seen[name] += 1
        if seen[name] == 2:
          problems.append(f"A3 {prefix}/{name}: SHORT-NAME used twice in one parent")
        paths[f"{prefix}/{name}"] = c
        walk(c, f"{prefix}/{name}")
      else:
        stack[0:0] = list(c)
  walk(root, "")
  return paths, problems, parent


def check(path: Path, xsd: Path | None = None) -> list[str]:
  problems = []
  try:
    root = ET.parse(path).getroot()
  except ET.ParseError as e:
    return [f"A1 not well-formed: {e}"]
  if root.tag != f"{Q}AUTOSAR":
    problems.append(f"A1 root is {root.tag}, not AUTOSAR in {NS}")
  loc = root.get("{http://www.w3.org/2001/XMLSchema-instance}schemaLocation", "")
  if SCHEMA not in loc:
    problems.append(f"A1 schemaLocation does not name {SCHEMA}")

  paths, idx_problems, parent = index(root)
  problems += idx_problems

  # A4 references
  refs = [el for el in root.iter() if el.get("DEST") is not None]
  for r in refs:
    target = paths.get((r.text or "").strip())
    if target is None:
      problems.append(f"A4 {local(r.tag)} -> {r.text}: no such element")
    elif local(target.tag) != r.get("DEST"):
      problems.append(f"A4 {local(r.tag)} -> {r.text}: is {local(target.tag)}, DEST says {r.get('DEST')}")
  if any(p.startswith("A4") for p in problems):
    return problems   # the semantic checks below assume resolvable references

  def deref(el: ET.Element | None) -> ET.Element | None:
    return paths.get(el.text.strip()) if el is not None and el.text else None

  def port_if(port: ET.Element) -> tuple[str, str]:
    t = port.find(f"{Q}PROVIDED-INTERFACE-TREF")
    d = "P"
    if t is None:
      t, d = port.find(f"{Q}REQUIRED-INTERFACE-TREF"), "R"
    return d, (t.text or "").strip()

  # A5 ports and connectors
  for path_, el in paths.items():
    tag = local(el.tag)
    if tag in ("P-PORT-PROTOTYPE", "R-PORT-PROTOTYPE"):
      t = el.find(f"{Q}PROVIDED-INTERFACE-TREF" if tag[0] == "P" else f"{Q}REQUIRED-INTERFACE-TREF")
      if t is None:
        problems.append(f"A5 {path_}: port without interface")
    elif tag == "ASSEMBLY-SW-CONNECTOR":
      p = deref(el.find(f"{Q}PROVIDER-IREF/{Q}TARGET-P-PORT-REF"))
      r = deref(el.find(f"{Q}REQUESTER-IREF/{Q}TARGET-R-PORT-REF"))
      if p is None or r is None:
        problems.append(f"A5 {path_}: incomplete assembly connector")
      elif port_if(p)[1] != port_if(r)[1]:
        problems.append(f"A5 {path_}: joins {port_if(p)[1]} to {port_if(r)[1]}")
    elif tag == "DELEGATION-SW-CONNECTOR":
      inner = el.find(f"{Q}INNER-PORT-IREF")
      ip = None
      for t in ("TARGET-P-PORT-REF", "TARGET-R-PORT-REF"):
        x = inner.find(f".//{Q}{t}") if inner is not None else None
        if ip is None:
          ip = deref(x)
      op = deref(el.find(f"{Q}OUTER-PORT-REF"))
      if ip is None or op is None:
        problems.append(f"A5 {path_}: incomplete delegation connector")
      elif port_if(ip) != port_if(op):
        problems.append(f"A5 {path_}: inner {port_if(ip)} and outer {port_if(op)} differ")

  # A6 every atomic SWC prototype under the root composition is mapped to one ECU
  for system in root.iter(f"{Q}SYSTEM"):
    rootproto = system.find(f".//{Q}ROOT-SW-COMPOSITION-PROTOTYPE")
    comp = deref(rootproto.find(f"{Q}SOFTWARE-COMPOSITION-TREF")) if rootproto is not None else None
    if comp is None:
      problems.append("A6 the system has no root composition")
      continue
    atomic = set()

    def walk(c: ET.Element, chain: tuple):
      for proto in c.iter(f"{Q}SW-COMPONENT-PROTOTYPE"):
        if parent.get(parent.get(proto)) is not c:
          continue
        t = deref(proto.find(f"{Q}TYPE-TREF"))
        pp = next(k for k, v in paths.items() if v is proto)
        if local(t.tag) == "COMPOSITION-SW-COMPONENT-TYPE":
          walk(t, chain + (pp,))
        else:
          atomic.add(chain + (pp,))
    walk(comp, ())
    mapped = Counter()
    for iref in system.iter(f"{Q}COMPONENT-IREF"):
      chain = tuple(x.text for x in iref.findall(f"{Q}CONTEXT-COMPONENT-REF")) + (
        iref.findtext(f"{Q}TARGET-COMPONENT-REF"),)
      mapped[chain] += 1
    for a in sorted(atomic):
      if mapped[a] != 1:
        problems.append(f"A6 {a[-1]}: mapped to {mapped[a]} ECU instances")
    for m in mapped:
      if m not in atomic:
        problems.append(f"A6 mapping names {m[-1]}, which is not an atomic prototype of the root composition")

  # A7 one sender per frame triggering
  for path_, el in paths.items():
    if local(el.tag) == "CAN-FRAME-TRIGGERING":
      dirs = Counter(deref(r).findtext(f"{Q}COMMUNICATION-DIRECTION") for r in el.iter(f"{Q}FRAME-PORT-REF"))
      if dirs["OUT"] != 1 or dirs["IN"] < 1:
        problems.append(f"A7 {path_}: {dirs['OUT']} senders, {dirs['IN']} receivers")

  # A8 the nature statement
  if not any(sdg.get("GID") == "LionDriver.Nature" and any("not an AUTOSAR implementation" in (sd.text or "")
                                                          for sd in sdg.iter(f"{Q}SD"))
             for sdg in root.iter(f"{Q}SDG")):
    problems.append("A8 the LionDriver.Nature statement is missing")

  if xsd is not None:
    try:
      from lxml import etree
    except ImportError:
      problems.append("A0 lxml is needed for --xsd")
    else:
      schema = etree.XMLSchema(etree.parse(str(xsd)))
      if not schema.validate(etree.parse(str(path))):
        problems += [f"A0 line {e.line}: {e.message}" for e in list(schema.error_log)[:50]]
  return problems


def main() -> int:
  args = sys.argv[1:]
  xsd = None
  if "--xsd" in args:
    i = args.index("--xsd")
    xsd = Path(args[i + 1])
    del args[i:i + 2]
  path = Path(args[0]) if args else DEFAULT
  problems = check(path, xsd)
  for p in problems:
    print(p)
  name = path.name
  if problems:
    print(f"check_arxml: {len(problems)} problem(s) in {name}", file=sys.stderr)
    return 1
  print(f"check_arxml: {name} passes A1-A8" + (f" and A0 ({xsd.name})" if xsd else " (A0 not run: no schema given)"))
  return 0


if __name__ == "__main__":
  sys.exit(main())
