#!/usr/bin/env python3
"""HATARA: where the HARA (WP-C-03) and the TARA (WP-C-09) meet, and where a measure on one side changes the other's risk.

The interactions below are the source of truth for this folder. Each one has a type after Kriaa et al. (conditional
dependency, mutual reinforcement, antagonism; independent pairs are not listed), a direction, what it is on the safety
side and on the security side, what follows, and the records it ties to. The model checks them against the analyses:

- every ID an interaction ties to exists in the assurance records outside this folder;
- a conditional dependency that names a threat scenario and a hazard which WP-C-09 §3 does not link must be marked as a
  gap; its status is derived, so it reads "closed" as soon as WP-C-09 §3 carries the link (the generated table and
  figures then need regenerating, like every figure that reads another work product's tables);
- the requirement statuses on the cards are read from WP-C-10 §7, never typed here.

    python3 hatara_model.py            # write hatara-interactions.md
    python3 hatara_model.py --check    # fail if a check fails or the table is stale

Standard library only. Output is deterministic.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONCEPT = HERE.parent
ASSURANCE = CONCEPT.parent
sys.path.insert(0, str(CONCEPT / "figures"))
import fig_c09_scenes as fc  # WP-C-09 threats, damage and risk, checked against §3, §6 and §7
import fig_c10_goals as fg  # WP-C-10 §7 requirement statuses

ParseError = fc.ParseError
HARA = CONCEPT / "WP-C-03-hara.md"
TABLE = HERE / "hatara-interactions.md"
KINDS = {"dep": "Conditional dependency", "reinf": "Mutual reinforcement", "anta": "Antagonism"}
DIRS = ("safety → security", "security → safety", "both")
ID = r"(?:TS|DS|H|SG|CSG|CSR-C|FSR|TSR|LS|GAP|FM)-\d+(?:\.\d+)?"

# id, title, kind, direction, safety side, security side, what follows, ties, own status (cards with no CSR), gap
INTERACTIONS = [
  dict(id="IX-01", title="A recovery path is also an attack path", kind="anta", dir="safety → security",
       safety="If the panda fails to boot, pandad flashes the development bootstub to bring it back",
       security="The same path flashes unauthenticated firmware onto the safety MCU (TS-03, risk 5)",
       follows="The envelope's availability was bought with a route around its authenticity. Authenticate the recovery or remove it.",
       ties=["TS-03", "CSR-C-05", "GAP-38"]),
  dict(id="IX-02", title="Test modes become a back door", kind="anta", dir="safety → security",
       safety="Debug, maneuver and joystick modes exist to validate control on the bench and the road",
       security="They replace the control processes, so a local attacker gets actuation through them (TS-04)",
       follows="Validation aids must be absent from reference builds, not merely unused.",
       ties=["TS-04", "CSR-C-07", "FM-06"]),
  dict(id="IX-03", title="A rejected frame is a lost function", kind="anta", dir="security → safety",
       safety="If the item stops controlling without telling the driver, that is silent loss (H-02, H-06)",
       security="Counter and CRC checks on received frames will reject forged and damaged frames",
       follows="A security rejection must end in the safety reaction: an announced take-over request, never a silent stop.",
       ties=["CSR-C-09", "FSR-02.10", "H-02", "H-06"]),
  dict(id="IX-04", title="One lock serves both", kind="reinf", dir="both",
       safety="The envelope must run the Toyota safety mode with its limits (SG-01 to SG-07)",
       security="No SoC command may change the safety mode or parameter (CSG-01, TS-02)",
       follows="The reference lock closes a hazard and a threat with one mechanism. Verify it once, for both.",
       ties=["TSR-512", "TSR-513", "CSR-C-01", "TS-02"]),
  dict(id="IX-05", title="A rejected image must leave the stock car", kind="anta", dir="security → safety",
       safety="Stock PCS must keep working whatever the item does (SG-07, H-08)",
       security="Verified boot leaves the panda unable to run firmware that fails its check",
       follows="The item may stop, but the stock path must stay: the switches fall back to pass-through only while the pull-down holds (LS-33).",
       ties=["CSR-C-03", "SG-07", "H-08", "LS-33"]),
  dict(id="IX-06", title="A fault reaction is a DoS lever", kind="anta", dir="safety → security",
       safety="Heartbeat loss or a controls mismatch withdraws authority at once, with an alert (LS-24)",
       security="An attacker who stalls SoC processes (TS-12) can trigger that withdrawal at will",
       follows="It stays safe only while the alert path survives the same attack; otherwise it is the silent loss of H-02 and H-06.",
       ties=["TS-12", "LS-24", "TSR-615", "H-02", "H-06"], status="Alert path under the same attack not analysed"),
  dict(id="IX-07", title="The service mode trusts the ignition line", kind="anta", dir="safety → security",
       safety="Diagnostics over the OBD port are allowed only with the ignition off, for service",
       security="An open ignition branch reads as ignition off while driving and releases that lock (LS-28)",
       follows="The lock needs an ignition signal the harness cannot fake. Until then it is a known gap.",
       ties=["LS-28"], status="Known gap (LS-28)"),
  dict(id="IX-08", title="One counter serves both", kind="reinf", dir="both",
       safety="The brake frame has no counter or checksum, so a stuck value passes (LS-21)",
       security="CAN integrity adds a counter and CRC against injected frames (GAP-01)",
       follows="One counter and CRC closes a stuck-frame fault and an injected frame. Specify it once, for both.",
       ties=["CSR-C-09", "GAP-01", "LS-21", "H-05", "H-03"]),
  dict(id="IX-09", title="The driver camera is also a privacy asset", kind="anta", dir="safety → security",
       safety="Driver monitoring needs a cabin camera to catch inattention (H-09)",
       security="Its video is personal data that an attacker or a thief can take (TS-11, DS-08)",
       follows="Every frame the safety function keeps is a privacy exposure. Keep and upload only what it needs (CSG-08).",
       ties=["TS-11", "DS-08", "CSG-08", "H-09", "CSR-C-14"]),
  dict(id="IX-10", title="Firmware integrity holds up SG-01…SG-07", kind="dep", dir="security → safety",
       safety="SG-01 to SG-07 rest on the envelope firmware; SG-08 rests on DM on the SoC (WP-C-04)",
       security="Safety-mode integrity (CSG-01) and firmware authenticity (CSG-02) protect that firmware",
       follows="Until both are met, SG-01 to SG-07 do not hold against an attacker on the SoC. SG-08 needs CSG-03 instead (IX-11).",
       ties=["CSG-01", "CSG-02", "SG-01", "SG-07", "SG-08", "CSG-03", "TS-02", "TS-03"], status="Recorded in WP-C-10 §8"),
  dict(id="IX-11", title="Screen and DM attacks reach H-07, H-09", kind="dep", dir="security → safety", gap=True,
       safety="WP-C-03 names spoofed HMI state for mode confusion (H-07); missed inattention is H-09",
       security="TS-04 can alter DM behaviour; WP-C-09 v0.8 adds DS-13 and DS-14 so it reaches H-07 and H-09",
       follows="Found by this analysis, closed in WP-C-09 v0.8. The derived status reopens it if a link is dropped.",
       ties=["TS-04", "H-07", "H-09", "CSG-03", "DS-13", "DS-14"]),
  dict(id="IX-12", title="An attacker picks the moment", kind="anta", dir="security → safety",
       safety="The HARA's exposure E assumes a random fault, striking a situation as often as it occurs",
       security="An attacker on the SoC waits for the worst situation; the TARA rates safety impact without E",
       follows="For an attacker-triggered event E does not apply: the TARA's safety impact governs. No rating changes (DQ-420 A).",
       ties=["TS-04", "SG-01"], status="Recorded in WP-C-03 §2 (DQ-420 A)"),
]


def hazards() -> dict[str, str]:
  """{H-nn: name} from the WP-C-03 hazard list."""
  out = dict(re.findall(r"^\| \*\*(H-\d+)\*\* ([^|]+?) \|", HARA.read_text(encoding="utf-8"), re.M))
  if not out:
    raise ParseError("WP-C-03 hazard list (| **H-nn** name | …) not found")
  return out


def known_ids() -> set[str]:
  """Every ID mentioned in the assurance records outside this folder."""
  seen = set()
  for p in ASSURANCE.rglob("*"):
    if p.suffix in (".md", ".yaml", ".yml", ".csv") and HERE not in p.parents:
      seen.update(re.findall(ID, p.read_text(encoding="utf-8", errors="ignore")))
  return seen


def links(tara) -> set[tuple[str, str]]:
  """(hazard, threat) pairs that WP-C-09 §3 links through a damage scenario; 'H-01…H-08' cells expand."""
  out = set()
  for ts, v in tara.ts.items():
    for d in v["damage"]:
      cell = tara.ds[d]["hara"]
      for a, b in re.findall(r"H-(\d+)\s*(?:…\s*H-(\d+))?", cell):
        out.update((f"H-{n:02d}", ts) for n in range(int(a), int(b or a) + 1))
  return out


class Model:
  def __init__(self, tara=None, goals=None, interactions=None, ids=None):
    self.tara = tara or fc.load()
    self.goals = goals or fg.load(self.tara)
    self.ix = INTERACTIONS if interactions is None else interactions
    self.hz = hazards()
    self.links = links(self.tara)
    self.check(known_ids() if ids is None else ids)

  def gaps(self, ix) -> list[tuple[str, str]]:
    """(hazard, threat) pairs a conditional dependency names but WP-C-09 §3 does not link."""
    hs = [i for i in ix["ties"] if i.startswith("H-")]
    tss = [i for i in ix["ties"] if i.startswith("TS-")]
    return [(h, t) for h in hs for t in tss if (h, t) not in self.links]

  def check(self, ids):
    seen = set()
    for ix in self.ix:
      i = ix["id"]
      if i in seen or not re.fullmatch(r"IX-\d{2}", i):
        raise ParseError(f"{i}: interaction IDs must be IX-nn and unique")
      seen.add(i)
      if ix["kind"] not in KINDS or ix["dir"] not in DIRS:
        raise ParseError(f"{i}: type must be one of {list(KINDS)} and direction one of {list(DIRS)}")
      for t in ix["ties"]:
        if not re.fullmatch(ID, t):
          raise ParseError(f"{i}: '{t}' is not an ID this model knows how to check")
        if t not in ids:
          raise ParseError(f"{i}: {t} is not in the assurance records")
        if t.startswith("H-") and t not in self.hz:
          raise ParseError(f"{i}: {t} is not a WP-C-03 hazard")
        if t.startswith("TS-") and t not in self.tara.ts:
          raise ParseError(f"{i}: {t} is not a WP-C-09 threat scenario")
        if t.startswith("CSR-C-") and t not in self.goals.csr:
          raise ParseError(f"{i}: {t} is not a WP-C-10 §7 requirement")
      if not [t for t in ix["ties"] if t.startswith("CSR-C-")] and not ix.get("status") and not ix.get("gap"):
        raise ParseError(f"{i}: no requirement to read a status from, so it needs its own status")
      g = self.gaps(ix) if ix["kind"] == "dep" else []
      if g and not ix.get("gap"):
        raise ParseError(f"{i}: WP-C-09 §3 does not link {', '.join(f'{h}/{t}' for h, t in g)}; mark it as a gap")

  def status(self, ix) -> list[tuple[str, str]]:
    """(label, CSR_ST key or '') per line of the card's status: one per tied requirement, else the row's own."""
    if ix.get("gap"):  # derived, so the TARA owner's damage scenarios close it without an edit here
      g = self.gaps(ix)
      return [(f"Open: WP-C-09 lacks {', '.join(f'{h}/{t}' for h, t in g)}", "open")] if g else \
             [("Closed: WP-C-09 §3 links them now", "done")]
    csrs = [t for t in ix["ties"] if t.startswith("CSR-C-")]
    return [(f"{r} {fg.CSR_ST[self.goals.csr[r]['status']][2].lower()}", self.goals.csr[r]["status"]) for r in csrs] or \
           [(ix["status"], "")]

  def table(self) -> str:
    rows = ["# HATARA interactions", "", "<!-- Generated by hatara_model.py from its INTERACTIONS; do not edit by hand. -->", "",
            "| ID | Interaction | Type | Direction | Safety side | Security side | What follows | Ties | Status |",
            "|---|---|---|---|---|---|---|---|---|"]
    for ix in self.ix:
      st = "; ".join(s for s, _ in self.status(ix))
      rows.append(f"| {ix['id']} | {ix['title']} | {KINDS[ix['kind']]} | {ix['dir']} | {ix['safety']} | {ix['security']} | "
                  f"{ix['follows']} | {', '.join(ix['ties'])} | {st} |")
    by = {k: sum(ix["kind"] == k for ix in self.ix) for k in KINDS}
    rows += ["", f"{len(self.ix)} interactions: " + ", ".join(f"{n} {KINDS[k].lower()}" for k, n in by.items()) + ". "
             f"Gaps between WP-C-03 and WP-C-09 §3: " +
             (", ".join(f"{h}/{t}" for ix in self.ix for h, t in self.gaps(ix) if ix["kind"] == "dep") or "none") + ".", ""]
    return "\n".join(rows)


def main(argv: list[str]) -> int:
  check = "--check" in argv
  try:
    text = Model().table()
  except ParseError as e:
    print(f"hatara_model: {e}", file=sys.stderr)
    return 1
  if check:
    if not TABLE.exists() or TABLE.read_text(encoding="utf-8") != text:
      print("stale hatara-interactions.md; run hatara_model.py", file=sys.stderr)
      return 1
  else:
    TABLE.write_text(text, encoding="utf-8")
  print(f"hatara_model: {len(INTERACTIONS)} interactions checked, table {'current' if check else 'written'}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
