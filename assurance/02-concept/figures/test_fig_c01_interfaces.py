#!/usr/bin/env python3
"""Tests for fig_c01_interfaces.py: source texts still present, SVGs current, numbers drawn equal WP-C-01.

The last test class compares the hand-listed safety-mode facts with opendbc's toyota.h. CI does not check out the
opendbc submodule, so it runs only where `opendbc_repo/opendbc/safety/modes/toyota.h` exists (locally).
"""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_c01_interfaces as fc

NS = "{http://www.w3.org/2000/svg}"
MAP = "fig-c01-3-3-can-interface-map.svg"
STOCK = "fig-c01-2-1-stock-functions.svg"
ENVELOPE = "fig-c01-8-1-actuation-envelope.svg"


class TestInterfaceFigures(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fc.SOURCE.read_text(encoding="utf-8")
    cls.out = fc.build(cls.md)

  def test_no_source_problems(self):
    self.assertEqual(fc.problems(self.md), [])

  def test_committed_outputs_current(self):
    for name, content in self.out.items():
      path = fc.HERE / name
      self.assertTrue(path.exists(), name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{name} is stale; run fig_c01_interfaces.py")

  def test_build_is_deterministic(self):
    self.assertEqual(fc.build(self.md), self.out)

  def test_svgs_valid_with_role_title_desc(self):
    for name, content in self.out.items():
      root = ET.fromstring(content)
      self.assertEqual(root.get("role"), "img", name)
      self.assertEqual(root.get("width"), "1280", name)
      self.assertTrue(root.find(f"{NS}title").text.startswith("Figure "), name)
      self.assertTrue(root.find(f"{NS}desc").text, name)

  def test_map_draws_every_message_of_3_4(self):
    svg = self.out[MAP]
    rows = fc.can_rows(self.md)
    self.assertEqual([r["id"] for r in rows["IF-01"]], ["0x2E4", "0x191", "0x343", "0x412", "0x1D2", "0x283", "0x750"])
    self.assertEqual([r["id"] for r in rows["IF-02"]], ["0xAA", "0x260", "0x1D2", "0x226", "0x262", "0x1D3", "0x180"])
    for key in ("IF-01", "IF-02"):
      for r in rows[key]:
        label = r["id"] if not r["end"] else f"{r['id']}–{r['end']}"
        self.assertIn(f">{label}<", svg)
        self.assertIn(f">{r['name']}<", svg)
    # rates and checksum flags as listed; the reference-build checks are drawn as such, not as every-build checks
    for addr, f in fc.RX.items():
      self.assertIn(f">rate {f['rate']} Hz" + (" · checksum" if f["checksum"] else "") + "<", svg, addr)
    self.assertEqual(svg.count(">reference build only;<"), 2)
    self.assertIn(">0x2E4 0x191 0x412 0x343<", svg)

  def test_3_4_states_the_reference_build_checks(self):
    # the corrected wording of §3.4 (0x262, 0x1D3) and the openpilot-longitudinal TX messages
    body = fc.section(self.md, "### 3.4 Interfaces")
    self.assertNotIn("not monitored by the safety mode", body)
    self.assertEqual(body.count("checked for presence, checksum and rate in the reference build only"), 2)
    self.assertIn("`0x283` PRE_COLLISION (zero payload only)", body)

  def test_envelope_numbers_equal_section_8(self):
    svg = self.out[ENVELOPE]
    e = fc.envelope(self.md)
    self.assertEqual((e["torque"]["max"], e["rate"]["up"], e["rate"]["down"], e["rate"]["window"]), (1500, 15, 25, 450))
    self.assertEqual((e["lat"]["accel"], e["lat"]["jerk"], e["accel"]["min"], e["accel"]["max"]), (3.0, 5.0, -3.5, 2.0))
    for s in ("|request| ≤ 1500 raw", "+15 up", "−25 down", "≤ 450 raw", "≤ 3.0 m/s²", "≤ 5 m/s³", "−3.5 m/s²", "+2.0 m/s²",
              "≈ 149 km/h: warning"):
      self.assertIn(f">{s}<", svg)
    # the physical torque is a placeholder: hatched, never a number
    self.assertIn(">N·m at the wheel: to be determined (GAP-04)<", svg)
    self.assertEqual(svg.count(">inherited · not verified<"), 6)  # five panels + legend

  def test_stock_functions_rows_and_status(self):
    rows = fc.stock_functions(self.md)
    self.assertEqual([r["status"] for r in rows], ["replaced", "replaced", "preserved", "assumed", "unmodified"])
    svg = self.out[STOCK]
    for r in rows:
      self.assertIn(f">{fc.STATUS[r['status']][0]}<", svg)
    self.assertIn(">AOU-04 · unverified<", svg)

  def test_nothing_drawn_as_verified(self):
    for name, content in self.out.items():
      self.assertNotIn("#2E9E6A", content.upper(), name)
      self.assertNotIn(">verified<", content, name)

  def test_boundary_and_hierarchy_figures_carry_every_id(self):
    boundary = (fc.HERE / "fig-3-2-item-boundary.svg").read_text(encoding="utf-8")
    for i in fc.interfaces(self.md):
      self.assertIn(i["id"], boundary, f"{i['id']} of §3.4 missing from Figure 3-2")
    hierarchy = (fc.HERE / "fig-3-1-element-hierarchy.svg").read_text(encoding="utf-8")
    body = fc.section(self.md, "### 3.1 Elements inside the item")
    elements = [m.group(0) for r in fc.table(body, ["Element", "Description"], "§3.1") for m in [re.match(r"E-\d\d", r[0])] if m]
    self.assertEqual(elements, ["E-01", "E-02", "E-03", "E-04", "E-05", "E-06"])
    for e in elements:
      self.assertIn(e, hierarchy, f"{e} of §3.1 missing from Figure 3-1")


# ---------------------------------------------------------------- local only: hand-listed facts vs toyota.h


def preprocess(src: str, defines: set[str]) -> str:
  """Drop comments and resolve #ifdef/#else/#endif for the given defines (no nesting in toyota.h's macro region)."""
  src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
  src = re.sub(r"//[^\n]*", "", src)
  out, keep = [], [True]
  for ln in src.splitlines():
    s = ln.strip()
    if s.startswith("#ifdef "):
      keep.append(keep[-1] and s.split()[1] in defines)
    elif s.startswith("#ifndef "):
      keep.append(keep[-1] and s.split()[1] not in defines)
    elif s.startswith("#else"):
      top = keep.pop()
      keep.append(keep[-1] and not top)
    elif s.startswith("#endif"):
      keep.pop()
    elif keep[-1]:
      out.append(ln)
  return "\n".join(out)


def macros(src: str) -> dict[str, str]:
  src = src.replace("\\\n", " ")
  out = {}
  for m in re.finditer(r"^\s*#define\s+([A-Z0-9_]+)(\([^)]*\))?[ \t]*(.*)$", src, flags=re.M):
    out[m.group(1)] = m.group(3)
  return out


def expand(name: str, defs: dict[str, str], depth=0) -> str:
  body = defs[name]
  if depth > 10:
    raise RecursionError(name)
  return re.sub(r"\b([A-Z][A-Z0-9_]+)\b(?:\([^)]*\))?",
                lambda m: expand(m.group(1), defs, depth + 1) if m.group(1) in defs and m.group(1).startswith("TOYOTA_") else m.group(0),
                body)


def tx_set(defs) -> dict[str, list[bool]]:
  out: dict[str, list[bool]] = {}
  for m in re.finditer(r"\{(0x[0-9A-Fa-f]+),\s*(\d),\s*\d+,\s*\.check_relay\s*=\s*(true|false)\}", expand("TOYOTA_COMMON_LONG_TX_MSGS", defs)):
    self_bus = int(m.group(2))
    if self_bus == 0:
      out.setdefault(norm(m.group(1)), []).append(m.group(3) == "true")
  return out


def rx_set(defs) -> dict[str, dict]:
  out = {}
  for m in re.finditer(r"\{\s*(0x[0-9A-Fa-f]+),\s*(\d),\s*\d+,\s*(\d+)U,([^}]*)\}", expand("TOYOTA_RX_CHECKS", defs)):
    out[norm(m.group(1))] = {"rate": int(m.group(3)), "checksum": "ignore_checksum" not in m.group(4)}
  return out


def norm(h: str) -> str:
  return "0x" + h[2:].upper()


@unittest.skipUnless(fc.TOYOTA_H.exists(), "opendbc submodule not checked out (CI); run locally")
class TestFactsAgainstToyotaH(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    src = fc.TOYOTA_H.read_text(encoding="utf-8")
    cls.raw = src
    cls.ref = macros(preprocess(src, {"LIONDRIVER_REFERENCE"}))
    cls.up = macros(preprocess(src, set()))

  def test_tx_whitelist_and_relay_flags(self):
    tx = tx_set(self.ref)
    self.assertEqual(sorted(tx), sorted(fc.TX))
    for addr, f in fc.TX.items():
      self.assertEqual(any(tx[addr]), f["relay"], addr)
    self.assertNotIn("0x411", tx)
    self.assertIn("0x411", tx_set(self.up))  # upstream builds keep PCS_HUD
    # 0x283 and 0x750 are on the openpilot-longitudinal list only
    stock = set(re.findall(r"\{(0x[0-9A-Fa-f]+),", expand("TOYOTA_COMMON_TX_MSGS", self.ref)))
    self.assertEqual({norm(h) for h in stock} & fc.LONG_ONLY, set())

  def test_rx_checks(self):
    rx = rx_set(self.ref)
    self.assertEqual(sorted(rx), sorted(fc.RX))
    for addr, f in fc.RX.items():
      self.assertEqual((rx[addr]["rate"], rx[addr]["checksum"]), (f["rate"], f["checksum"]), addr)
    up = rx_set(self.up)
    self.assertEqual(sorted(up), sorted(a for a, f in fc.RX.items() if not f["ref_only"]))
    for a in ("0x180", "0x19F"):
      self.assertNotIn(a, rx)

  def test_forwarding_block_is_the_relay_set(self):
    tx = tx_set(self.ref)
    self.assertEqual(sorted(a for a, flags in tx.items() if any(flags)), sorted(fc.FORWARD_BLOCKED["ids"]))

  def test_content_checks(self):
    self.assertRegex(self.raw, r"msg_matches\(msg, 0x283U, 0U\)\)\s*\{[^}]*GET_BYTES_64_LE\(msg, 0, 6\) != 0U")
    self.assertRegex(self.raw, r"0x750U\)\s*\{[^}]*0x00000000003E020FULL")

  def test_section_8_limits(self):
    e = fc.envelope(fc.SOURCE.read_text(encoding="utf-8"))
    for field, value in ((".max_torque", e["torque"]["max"]), (".max_rate_up", e["rate"]["up"]),
                         (".max_rate_down", e["rate"]["down"]), (".max_rt_delta", e["rate"]["window"]),
                         (".max_accel", round(e["accel"]["max"] * 1000)), (".min_accel", round(e["accel"]["min"] * 1000))):
      self.assertRegex(self.raw, re.escape(field) + r"\s*=\s*" + re.escape(str(value)) + r",", field)


if __name__ == "__main__":
  unittest.main()
