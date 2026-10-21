#!/usr/bin/env python3
"""Check the TE-03 FRETish restatements of panda TSRs and write their review page.

The source of record is `tsr-fretish.yaml` next to this script. For each requirement it checks
  * that the TSR exists in WP-S-02 and that the quoted `source` text is still in its row (verbatim,
    whitespace folded), so a reworded TSR fails the build until its FRETish is reviewed;
  * that the FRETish sentence has the shape of FRET's `nasa` rule (Requirement.g4 at FRET cf0f913):
    optional scope, optional condition, `the envelope shall`, optional timing, `satisfy` response,
    with balanced, well-formed expressions;
  * that every variable is in the glossary, no glossary entry is unused, and no variable is a FRET
    keyword or reserved word;
  * that every finding a requirement cites exists, and every finding is cited;
  * that `fretish-formalizations.json` holds FRET's formulas for exactly the current sentences.
It does not formalise: `fret_formalize.py` runs FRET for that. It then writes `fretish-requirements.md`.

    python3 check_fretish.py           # check and regenerate the page
    python3 check_fretish.py --check   # check; fail if the committed page is stale

Needs PyYAML. Output is deterministic.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "tsr-fretish.yaml"
OUTPUT = HERE / "fretish-requirements.md"
FORMULAS = HERE / "fretish-formalizations.json"
WP_S_02 = HERE.parent.parent / "03-system" / "WP-S-02-technical-safety-requirements.md"
COMPONENT = "envelope"

# Requirement.g4 keywords (case-insensitive) and the reserved words of FRET's "Writing requirements" page.
KEYWORDS = set("""after always and at before during eventually except false finally first for hour hours if
immediately in initially is last microsec microsecs microsecond microseconds millisec millisecs millisecond
milliseconds minute minutes mod mode never next not occurrence of only or previous probability same satisfy sec
secs second seconds shall the then tick ticks timepoint true unless until upon what when whenever where while with
within xor""".split())
RESERVED = set("""A ABF ABG AF AG ASSIGN AX BU COMPASSION COMPUTE COMPWFF CONSTANTS CONSTRAINT CTLSPEC CTLWFF DEFINE E
EBF EBG EF EG EX F FAIRNESS FROZENVAR G H IN INIT INVAR INVARSPEC ISA IVAR JUSTICE LTLSPEC LTLWFF MAX MDEFINE MIN
MIRROR MODULE NAME O PRED PREDICATES PSLSPEC PSLWFF S SIMPWFF SPEC T TRANS U V VAR X Y Z abs array bool boolean case
count esac extend in init integer max min mod next of process real resize self signed sizeof swconst union unsigned
uwconst word word1 xnor xor""".split())
FUNCTIONS = {"absReal", "maxReal", "minReal", "preBool", "preInt", "preReal", "persisted", "occurred", "persists",
             "occurs", "prevOcc", "nextOcc"}
QUALIFIERS = ("upon", "whenever", "when", "where", "if", "unless")
UNITS = r"(?:ticks?|millisec(?:ond)?s?|sec(?:ond)?s?)"
TIMING = re.compile(r"^(?:(?:within|for|after) \d+ " + UNITS + r"|immediately|initially|always|never|eventually|"
                    r"finally|at the (?:first|same|next|last) timepoint)$", re.I)
TOKEN = re.compile(r"\s*(<->|<=>|->|=>|<=|>=|!=|[()!~&|<>=+\-*/^,]|\d+(?:\.\d+)?|[A-Za-z][A-Za-z0-9_.%]*)")
RELATIONAL = {"<", "<=", ">", ">=", "=", "!="}


class CheckError(Exception):
  pass


def tokens(text: str) -> list[str]:
  out, pos = [], 0
  text = text.strip()
  while pos < len(text):
    m = TOKEN.match(text, pos)
    if not m:
      raise CheckError(f"cannot read {text[pos:]!r}")
    out.append(m.group(1))
    pos = m.end()
  return out


class Expr:
  """Precedence parser for the bool_expr / numeric_expr rules; collects identifiers."""

  BINARY = [({"<->", "<=>", "->", "=>"}, False), ({"|", "xor"}, False), ({"&"}, False), (RELATIONAL, False),
            ({"+", "-"}, False), ({"*", "/", "mod"}, False), ({"^"}, True)]

  def __init__(self, text: str):
    self.toks = tokens(text)
    self.pos = 0
    self.names: set[str] = set()
    self.calls: set[str] = set()
    if not self.toks:
      raise CheckError("empty expression")
    self.level(0)
    if self.pos != len(self.toks):
      raise CheckError(f"unexpected {self.toks[self.pos]!r} in {text!r}")

  def peek(self) -> str | None:
    return self.toks[self.pos] if self.pos < len(self.toks) else None

  def take(self, want: str | None = None) -> str:
    tok = self.peek()
    if tok is None or (want is not None and tok.lower() != want):
      raise CheckError(f"expected {want or 'a term'}, found {tok!r}")
    self.pos += 1
    return tok

  def level(self, n: int) -> None:
    if n == len(self.BINARY):
      self.unary()
      return
    ops, right = self.BINARY[n]
    self.level(n + 1)
    while (tok := self.peek()) is not None and tok.lower() in ops:
      self.take()
      self.level(n if right else n + 1)

  def unary(self) -> None:
    tok = self.peek()
    if tok in ("!", "~", "-"):
      self.take()
      self.unary()
    elif tok == "(":
      self.take()
      self.level(0)
      self.take(")")
    elif tok is not None and re.fullmatch(r"\d+(?:\.\d+)?", tok):
      self.take()
    elif tok is not None and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.%]*", tok):
      self.take()
      if tok in ("true", "false"):
        return
      if self.peek() == "(":
        self.calls.add(tok)
        self.take()
        if self.peek() != ")":
          self.level(0)
          while self.peek() == ",":
            self.take()
            self.level(0)
        self.take(")")
      else:
        self.names.add(tok)
    else:
      raise CheckError(f"unexpected {tok!r}")


def parse_fretish(sentence: str) -> tuple[set[str], set[str]]:
  """Split a sentence by the `nasa` rule; return its variables and mode names."""
  m = re.fullmatch(r"(?P<pre>.*?)\bthe " + COMPONENT + r" shall (?P<post>.*)", sentence.strip().rstrip("."), re.I)
  if not m:
    raise CheckError(f"no 'the {COMPONENT} shall'")
  pre, post = m.group("pre").strip(), m.group("post").strip()
  modes: set[str] = set()
  sm = re.match(r"in (?P<mode>[A-Za-z][A-Za-z0-9_]*) mode,?\s*", pre, re.I)
  if sm:
    modes.add(sm.group("mode"))
    pre = pre[sm.end():]
  names: set[str] = set()
  calls: set[str] = set()
  if pre:
    qm = re.match(r"(?P<q>" + "|".join(QUALIFIERS) + r")\s+(?P<cond>.+)$", pre, re.I)
    if not qm:
      raise CheckError(f"condition must start with one of {', '.join(QUALIFIERS)}: {pre!r}")
    e = Expr(qm.group("cond"))
    names |= e.names
    calls |= e.calls
  rm = re.fullmatch(r"(?P<timing>.*?)\s*\bsatisfy\s+(?P<resp>.+)", post, re.I)
  if not rm:
    raise CheckError("no 'satisfy' response")
  timing = rm.group("timing").strip().rstrip(",")
  if timing and not TIMING.match(timing):
    raise CheckError(f"timing {timing!r} is not one of FRET's timings (or uses another time unit)")
  e = Expr(rm.group("resp"))
  names |= e.names
  calls |= e.calls
  unknown = calls - FUNCTIONS
  if unknown:
    raise CheckError(f"unknown function(s) {', '.join(sorted(unknown))}")
  return names, modes


def fold(text: str) -> str:
  return " ".join(text.split())


def tsr_rows(md: str) -> dict[str, str]:
  rows = {}
  for line in md.splitlines():
    m = re.match(r"\| (TSR-\d+) \| (.*)", line)
    if m and m.group(1) not in rows:
      rows[m.group(1)] = fold(m.group(2))
  return rows


def check_formulas(data: dict, formulas: dict) -> list[str]:
  errors = []
  stored = formulas.get("requirements", {})
  for r in data["requirements"]:
    entry = stored.get(r["id"])
    if entry is None or entry.get("fretish") != r["fretish"]:
      errors.append(f"{r['id']}: no FRET formula for the current sentence; run fret_formalize.py")
  for rid in sorted(set(stored) - {r["id"] for r in data["requirements"]}):
    errors.append(f"{rid}: formula stored for a requirement that no longer exists; run fret_formalize.py")
  return errors


def check(data: dict, wp_s_02: str) -> list[str]:
  errors: list[str] = []
  glossary = {g["name"]: g for g in data["glossary"]}
  findings = {f["id"]: f for f in data["findings"]}
  rows = tsr_rows(wp_s_02)
  used: set[str] = set()
  cited: set[str] = set()
  seen: set[str] = set()
  for name in glossary:
    if name.lower() in KEYWORDS or name in RESERVED:
      errors.append(f"glossary: {name} is a FRET keyword or reserved word")
  for r in data["requirements"]:
    rid = r["id"]
    if rid in seen:
      errors.append(f"{rid}: duplicate id")
    seen.add(rid)
    row = rows.get(r["tsr"])
    if row is None:
      errors.append(f"{rid}: {r['tsr']} not found in WP-S-02")
    elif fold(r["source"]) not in row:
      errors.append(f"{rid}: the quoted source is no longer in {r['tsr']}; review the FRETish against the new text")
    try:
      names, modes = parse_fretish(r["fretish"])
    except CheckError as exc:
      errors.append(f"{rid}: {exc}")
      continue
    for name in sorted(names | modes):
      if name not in glossary:
        errors.append(f"{rid}: {name} is not in the glossary")
    for mode in modes:
      if mode in glossary and glossary[mode]["type"] != "mode":
        errors.append(f"{rid}: {mode} is used as a mode but typed {glossary[mode]['type']}")
    used |= names | modes
    for fid in r.get("findings", []):
      if fid not in findings:
        errors.append(f"{rid}: finding {fid} does not exist")
      cited.add(fid)
  for name in sorted(set(glossary) - used):
    errors.append(f"glossary: {name} is not used")
  for fid in sorted(set(findings) - cited):
    errors.append(f"finding {fid} is not cited by any requirement")
  return errors


def cell(text: str) -> str:
  return fold(str(text)).replace("|", "\\|")


def build(data: dict, formulas: dict) -> str:
  reqs, findings = data["requirements"], data["findings"]
  tsrs = sorted({r["tsr"] for r in reqs}, key=lambda t: int(t.split("-")[1]))
  lines = [
    "# Panda TSRs in FRETish (TE-03 pilot)",
    "",
    "> Generated by [`check_fretish.py`](check_fretish.py) from [`tsr-fretish.yaml`](tsr-fretish.yaml); do not edit by hand.",
    f"> AI-drafted, not reviewed. Formalised by FRET `{formulas['fret_commit']}` ([`fret_formalize.py`](fret_formalize.py), [TE-03](../../07-supporting/tool-evaluations/TE-03-fret-requirements.md) P2). No evidence credit.",
    "",
    f"{len(reqs)} FRETish requirements restate {len(tsrs)} TSRs of [WP-S-02](../../03-system/WP-S-02-technical-safety-requirements.md) "
    f"({', '.join(tsrs)}). Time is in ticks of the panda safety task (1 tick = 10 ms). "
    f"Writing them found {len(findings)} points where a TSR differs from the code, contradicts itself or cannot be checked as written.",
    "",
    "## Requirements",
    "",
    "| ID | TSR | Restates | FRETish | Findings |",
    "|---|---|---|---|---|",
  ]
  for r in reqs:
    lines.append(f"| {r['id']} | {r['tsr']} | {cell(r['source'])} | `{cell(r['fretish'])}` | {', '.join(r.get('findings', [])) or '—'} |")
  lines += ["", "## Findings", "", "| ID | TSR | Kind | Finding | Evidence | For |", "|---|---|---|---|---|---|"]
  for f in findings:
    lines.append(f"| {f['id']} | {f['tsr']} | {cell(f['kind'])} | {cell(f['summary'])} | {cell(f['evidence'])} | {cell(f['route'])} |")
  lines += ["", "## Formal meaning (FRET)", "",
            "FRET's future-time formula (infinite trace) for each requirement: `G` always, `F[a,b]` within a to b ticks, "
            "`X` next tick, `V` release. The past-time formulas, the ones a runtime monitor uses, are in "
            "[`fretish-formalizations.json`](fretish-formalizations.json).", "",
            "| ID | Future-time formula |", "|---|---|"]
  for r in reqs:
    lines.append(f"| {r['id']} | `{cell(formulas['requirements'][r['id']]['ft'])}` |")
  lines += ["", "## Glossary", "", "| Variable | Type | Meaning | In the code |", "|---|---|---|---|"]
  for g in data["glossary"]:
    kind = g["type"] + (f", {g['unit']}" if g.get("unit") else "")
    lines.append(f"| `{g['name']}` | {kind} | {cell(g['meaning'])} | {cell(g['code'])} |")
  return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
  data = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
  formulas = json.loads(FORMULAS.read_text(encoding="utf-8")) if FORMULAS.exists() else {}
  errors = check(data, WP_S_02.read_text(encoding="utf-8")) + check_formulas(data, formulas)
  for e in errors:
    print(f"check_fretish: {e}", file=sys.stderr)
  if errors:
    return 1
  page = build(data, formulas)
  if "--check" in argv:
    if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != page:
      print(f"check_fretish: {OUTPUT.name} is stale; run check_fretish.py", file=sys.stderr)
      return 1
    print(f"check_fretish: {len(data['requirements'])} requirements, {len(data['findings'])} findings; page current")
    return 0
  OUTPUT.write_text(page, encoding="utf-8")
  print(f"check_fretish: wrote {OUTPUT.name}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
